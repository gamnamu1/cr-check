# backend/extract_api.py
"""[PR1] POST /extract — 기사 6요소 추출 전용 엔드포인트.

분석은 하지 않는다. Anthropic API·RAG·임베딩·Supabase 저장 함수를 호출하지 않으며,
기사 URL·본문을 어떤 저장소·로그에도 남기지 않는다(로그는 도메인·상태·코드·소요시간만).

기존 `/analyze` 경로와는 fetch 계층부터 분리돼 있다.
- `/analyze` : ArticleScraper.scrape() → requests.get (기존 그대로)
- `/extract` : safe_fetch() → ArticleScraper._parse_response()
"""

import hmac
import os
import re
import threading
import time
from datetime import date
from typing import Dict, List, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from safe_fetch import SafeFetchError, safe_fetch
from scraper import ArticleScraper

EXTRACTOR_VERSION = "2026.09.1"

# 기존 스크레이퍼(_scrape_generic 등)가 쓰는 최소 본문 길이 기준.
# 로그인 화면처럼 200으로 오지만 본문이 없는 페이지를 걸러낸다.
MIN_CONTENT_CHARS = 100

# 프록시 뒤에서는 사실상 전역 상한이므로, 시민별 제한은 cr-report 프록시가 담당한다.
RATE_LIMIT_PER_MINUTE = 120
RATE_LIMIT_WINDOW_SECONDS = 60

# 스크레이퍼가 메타데이터를 찾지 못했을 때 쓰는 자리표시자.
# main.py의 동명 상수와 같은 기준이며, /extract에서는 이 값을 null + warning으로 바꾼다.
_INVALID_META = {"미확인", "", "N/A", "unknown", "Unknown"}

# 오류 코드 → HTTP 상태 (지시서 2절 오류 코드 표)
_ERROR_STATUS = {
    "INVALID_URL": 400,
    "UNSAFE_URL": 400,
    "UNAUTHORIZED_CALLER": 401,
    "RESPONSE_TOO_LARGE": 413,
    "UNSUPPORTED_CONTENT_TYPE": 415,
    "ARTICLE_NOT_FOUND": 422,
    "RATE_LIMITED": 429,
    "EXTRACTOR_ERROR": 500,
    "EXTRACTOR_DISABLED": 503,
    "SOURCE_FETCH_FAILED": 502,
    "SOURCE_TIMEOUT": 504,
}

# source_kind 판정용 도메인 표. 매칭은 URL 부분 문자열이 아니라 호스트 경계 기준이다
# (_source_kind 참조). 줌은 원 scraper.py에서 네이버·다음·네이트와 같은 포털 블록에 있다.
# ArticleScraper._dispatch_parser의 분기 도메인에서 뽑아낸 목록이므로,
# 스크레이퍼에 매체를 추가·삭제할 때 이 표도 함께 손봐야 한다
# (어긋나도 source_kind 라벨만 달라질 뿐 추출 결과에는 영향이 없다).
_PORTAL_DOMAINS = ("news.naver.com", "news.daum.net", "v.daum.net", "news.nate.com",
                   "news.zum.com")
_OUTLET_DOMAINS = (
    "yna.co.kr", "newsis.com", "news1.kr",
    "newspim.com", "khan.co.kr", "kmib.co.kr", "naeil.com",
    "donga.com", "munhwa.com", "seoul.co.kr", "segye.com",
    "asiatoday.co.kr", "chosun.com", "joongang.co.kr", "hani.co.kr",
    "hankookilbo.com", "edaily.co.kr", "ekn.kr", "asiae.co.kr",
    "sedaily.com", "viva100.com", "mk.co.kr", "hankyung.com",
    "dnews.co.kr", "biz.heraldcorp.com", "fnnews.com", "etoday.co.kr",
    "dt.co.kr", "mediatoday.co.kr", "mediaus.co.kr", "journalist.or.kr",
    "pennmike.com", "pressian.com", "mindlenews.com", "ohmynews.com",
    "dailian.co.kr", "kado.net", "jbnews.com", "ccdailynews.com",
    "hidomin.com", "idomin.com", "kihoilbo.co.kr", "incheonilbo.com",
    "kyongbuk.co.kr", "daejonilbo.com", "idaegu.com", "jnilbo.com",
    "jejudomin.co.kr", "imaeil.com", "yeongnam.com", "kgnews.co.kr",
    "kyeonggi.com", "busan.com", "kookje.co.kr", "kwnews.co.kr",
)

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")
_DATE_PATTERNS = (
    re.compile(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})"),
    re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일"),
)

router = APIRouter()
_scraper = ArticleScraper()


# ---------------------------------------------------------------------------
# 요청·응답 모델 (지시서 2절 계약)
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    # HttpUrl이 아니라 str이다. 스킴 없는 입력('example.com/news/1')을 라우트 진입
    # 전에 거부하면 https:// 보정 규칙이 무력화되기 때문이다.
    url: str


class ExtractArticle(BaseModel):
    title: str
    content: str
    url: str
    publisher: Optional[str] = None
    journalist: Optional[str] = None
    publish_date: Optional[str] = None
    source_kind: str


class ExtractWarning(BaseModel):
    code: str
    message: str


class ExtractSuccessResponse(BaseModel):
    ok: bool = True
    status: str
    article: ExtractArticle
    warnings: List[ExtractWarning] = []
    content_chars: int
    extractor_version: str = EXTRACTOR_VERSION


class ExtractErrorResponse(BaseModel):
    ok: bool = False
    code: str
    message: str


# ---------------------------------------------------------------------------
# 레이트 리밋 (인메모리, 베스트에포트)
# ---------------------------------------------------------------------------

_rate_lock = threading.Lock()
_rate_hits: Dict[str, List[float]] = {}


def _allow_request(client_ip: str, now: float) -> bool:
    """IP별 분당 요청 수 제한.

    서버 전체가 감당할 방어 상한이다. 시민 단위 제한은 cr-report 프록시 소관.

    베스트에포트임에 유의: 인메모리라 프로세스가 재시작하면 초기화되고,
    워커가 여러 개면 워커별로 따로 센다(전체 상한은 워커 수만큼 늘어난다).
    외부 저장소(Redis 등)는 도입하지 않는다.
    """
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    with _rate_lock:
        # 1분이 지난 항목을 매 요청마다 정리해 dict가 무한히 자라지 않게 한다.
        for ip in list(_rate_hits):
            fresh = [t for t in _rate_hits[ip] if t > cutoff]
            if fresh:
                _rate_hits[ip] = fresh
            else:
                del _rate_hits[ip]

        hits = _rate_hits.setdefault(client_ip, [])
        if len(hits) >= RATE_LIMIT_PER_MINUTE:
            return False
        hits.append(now)
        return True


def _reset_rate_limit() -> None:
    """테스트 전용 — 카운터 초기화."""
    with _rate_lock:
        _rate_hits.clear()


# ---------------------------------------------------------------------------
# 라우트
# ---------------------------------------------------------------------------

@router.post("/extract")
async def extract_article(request: Request):
    """기사 URL에서 6요소(제목·본문·URL·매체·게재일·기자)만 뽑아 돌려준다."""
    started = time.monotonic()

    expected_key = os.environ.get("EXTRACT_API_KEY") or ""
    if not expected_key:
        # 키가 없으면 엔드포인트 자체를 잠근다.
        return _error("EXTRACTOR_DISABLED", "추출 엔드포인트가 비활성화되어 있습니다.", "-", started)

    provided_key = request.headers.get("X-CR-Extract-Key") or ""
    if not hmac.compare_digest(provided_key, expected_key):
        return _error("UNAUTHORIZED_CALLER", "호출 권한을 확인하지 못했습니다.", "-", started)

    client_ip = request.client.host if request.client else "unknown"
    if not _allow_request(client_ip, time.monotonic()):
        return _error("RATE_LIMITED", "요청 빈도 상한을 넘었습니다.", "-", started)

    try:
        payload = await request.json()
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        return _error("INVALID_URL", "요청 본문을 해석하지 못했습니다.", "-", started)
    try:
        body = ExtractRequest.model_validate(payload)
    except ValidationError:
        return _error("INVALID_URL", "요청 본문에 url이 없습니다.", "-", started)

    url = (body.url or "").strip()
    if not url:
        return _error("INVALID_URL", "URL이 비어 있습니다.", "-", started)
    if not _SCHEME_RE.match(url):
        url = "https://" + url

    domain = _domain_of(url)

    try:
        fetch_result = await run_in_threadpool(safe_fetch, url)
    except SafeFetchError as exc:
        return _error(exc.code, exc.message, domain, started)
    except Exception:
        return _error("EXTRACTOR_ERROR", "기사를 가져오는 중 오류가 발생했습니다.", domain, started)

    try:
        article_data = await run_in_threadpool(
            _scraper._parse_response,
            fetch_result.response,
            parse_url=fetch_result.final_url,   # /extract만 최종 URL 기준
            original_url=url,                   # 정규화된 요청 URL
        )
    except ValueError:
        return _error("ARTICLE_NOT_FOUND", "기사 제목 또는 본문을 추출하지 못했습니다.", domain, started)
    except Exception:
        # 예외 문자열·스택·내부 경로는 응답에 담지 않는다.
        return _error("EXTRACTOR_ERROR", "기사 파싱 중 오류가 발생했습니다.", domain, started)

    title = article_data.get("title") or ""
    content = article_data.get("content") or ""
    if not title.strip() or len(content.strip()) < MIN_CONTENT_CHARS:
        return _error("ARTICLE_NOT_FOUND", "기사 제목 또는 본문을 추출하지 못했습니다.", domain, started)

    warnings: List[ExtractWarning] = []

    publisher = _clean_meta(article_data.get("publisher"))
    if publisher is None:
        warnings.append(ExtractWarning(code="PUBLISHER_NOT_FOUND", message="언론사명을 확인하지 못했습니다."))

    journalist = _clean_meta(article_data.get("journalist"))
    if journalist is None:
        warnings.append(ExtractWarning(code="JOURNALIST_NOT_FOUND", message="기자명을 확인하지 못했습니다."))

    publish_date = _normalize_publish_date(_clean_meta(article_data.get("publish_date")))
    if publish_date is None:
        warnings.append(ExtractWarning(code="PUBLISH_DATE_NOT_FOUND", message="게재일을 확인하지 못했습니다."))

    status = "success" if not warnings else "partial"
    payload_out = ExtractSuccessResponse(
        status=status,
        article=ExtractArticle(
            title=title,
            content=content,
            url=url,
            publisher=publisher,
            journalist=journalist,
            publish_date=publish_date,
            source_kind=_source_kind(fetch_result.final_url),
        ),
        warnings=warnings,
        content_chars=len(content),
    )

    _log(domain, 200, status, started)
    return JSONResponse(status_code=200, content=payload_out.model_dump())


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _error(code: str, message: str, domain: str, started: float) -> JSONResponse:
    """계약 JSON ③ 형태({ok, code, message})로만 오류를 돌려준다.

    FastAPI 기본 HTTPException의 {"detail": ...} 래퍼는 쓰지 않는다.
    """
    http_status = _ERROR_STATUS.get(code, 500)
    _log(domain, http_status, code, started)
    return JSONResponse(
        status_code=http_status,
        content=ExtractErrorResponse(code=code, message=message).model_dump(),
    )


def _log(domain: str, http_status: int, outcome: str, started: float) -> None:
    """도메인·상태·코드·소요시간만 남긴다. URL 전체·쿼리스트링·본문은 남기지 않는다."""
    elapsed_ms = int((time.monotonic() - started) * 1000)
    print(f"[extract] {domain} · {http_status} · {outcome} · {elapsed_ms}ms", flush=True)


def _domain_of(url: str) -> str:
    try:
        return urlsplit(url).hostname or "-"
    except ValueError:
        return "-"


def _clean_meta(value) -> Optional[str]:
    """스크레이퍼의 '미확인' 자리표시자를 None으로 바꾼다(빈 문자열 반환 금지)."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in _INVALID_META else text


def _normalize_publish_date(raw: Optional[str]) -> Optional[str]:
    """가능하면 YYYY-MM-DD로, 정규화에 실패하면 원문 표기 그대로 돌려준다."""
    if raw is None:
        return None
    for pattern in _DATE_PATTERNS:
        match = pattern.search(raw)
        if not match:
            continue
        year, month, day = (int(g) for g in match.groups())
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    return raw


def _source_kind(parse_url: str) -> str:
    """리디렉션까지 마친 최종 URL의 호스트명으로 판정한다.

    URL 전체를 부분 문자열로 훑지 않는다 — 쿼리스트링에 도메인이 섞여 있거나
    (`https://example.com/a?ref=news.naver.com`) 다른 도메인의 꼬리에 우연히
    포함되는 경우(`not-hani.co.kr`)를 포털·매체로 잘못 잡지 않기 위해서다.
    """
    try:
        host = urlsplit(parse_url).hostname
    except ValueError:
        host = None
    if not host:
        return "generic"
    host = host.lower().rstrip(".")

    if _host_matches(host, _PORTAL_DOMAINS):
        return "portal"
    if _host_matches(host, _OUTLET_DOMAINS):
        return "outlet"
    return "generic"


def _host_matches(host: str, domains) -> bool:
    """host가 domain 자신이거나 그 하위 도메인일 때만 참."""
    return any(host == domain or host.endswith("." + domain) for domain in domains)
