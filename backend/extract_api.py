# backend/extract_api.py
"""[PR1] POST /extract — 기사 6요소 추출 전용 엔드포인트.

분석은 하지 않는다. Anthropic API·RAG·임베딩·Supabase 저장 함수를 호출하지 않으며,
기사 URL·본문을 어떤 저장소·로그에도 남기지 않는다(로그는 도메인·상태·코드·소요시간만).

기존 `/analyze` 경로와는 fetch 계층부터 분리돼 있다.
- `/analyze` : ArticleScraper.scrape() → requests.get (기존 그대로)
- `/extract` : safe_fetch() → ArticleScraper._parse_response()

가져오기와 파싱은 워커 스레드 하나에서 연속으로 돌고(`_extract_blocking`),
그 구간은 워커 프로세스별 동시 추출 상한(`MAX_CONCURRENT_EXTRACTIONS`)이 지킨다.
상한을 넘는 요청은 대기열에 쌓지 않고 그 자리에서 503 EXTRACTOR_BUSY로 돌려보낸다.
"""

import hmac
import os
import re
import threading
import time
from datetime import date
from typing import List, Optional
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
    "EXTRACTOR_ERROR": 500,
    # 503이 둘이다 — 키 미설정으로 엔드포인트가 잠긴 상태(DISABLED)와
    # 동시 추출 상한이 찬 일시적 혼잡(BUSY). 호출 측은 code로만 분기한다.
    "EXTRACTOR_DISABLED": 503,
    "EXTRACTOR_BUSY": 503,
    "SOURCE_FETCH_FAILED": 502,
    "SOURCE_TIMEOUT": 504,
}

# source_kind 판정용 도메인 표. 매칭은 URL 부분 문자열이 아니라 호스트 경계 기준이다
# (_source_kind 참조). 줌은 원 scraper.py에서 네이버·다음·네이트와 같은 포털 블록에 있다.
# ArticleScraper._dispatch_parser의 분기 도메인에서 뽑아낸 목록이므로,
# 스크레이퍼에 매체를 추가·삭제할 때 이 표도 함께 손봐야 한다
# (어긋나도 source_kind 라벨만 달라질 뿐 추출 결과에는 영향이 없다).
_PORTAL_DOMAINS = ("news.naver.com", "entertain.naver.com", "news.daum.net", "v.daum.net",
                   "news.nate.com", "news.zum.com")
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
    "metroseoul.co.kr", "mediapen.com",
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
# 동시 추출 제한 · 슬롯 수명 (인메모리, 워커 프로세스별)
# ---------------------------------------------------------------------------
#
# 중계 환경의 IP별 요청 빈도 제한은 실제 실행 중인 추출 작업량을 직접 제어하지
# 못한다. 이를 워커별 동시 작업 제한으로 교체하고, 혼잡 시 503 EXTRACTOR_BUSY를
# 반환한다. 시민별 429 RATE_LIMITED는 cr-report 프록시(IP당 20회/분)가 계속 담당한다.

# 워커 프로세스별 동시 추출 상한. uvicorn 워커가 2개이므로 서비스 전체 상한은 2배가 된다.
# 이 값은 동시에 받아들일 추출 작업의 설정 상한이며, 초당·분당 처리량을 보장하는 수치가 아니다.
MAX_CONCURRENT_EXTRACTIONS = 20

# 예약 상태. pending → running → released, 또는 pending → released(취소)로만 전이한다.
_PENDING = "pending"
_RUNNING = "running"
_RELEASED = "released"

# 상태 전이와 점유 수 갱신은 전부 이 락 아래에서만 한다. 점유 수 감소는
# released 전이 한 곳에만 묶여 있어, 확보한 슬롯은 정확히 한 번만 반환된다.
_slot_lock = threading.Lock()
_active_extractions = 0


class _Reservation:
    """추출 슬롯 1개의 예약. `state`는 `_slot_lock` 아래에서만 읽고 쓴다."""

    __slots__ = ("state",)

    def __init__(self) -> None:
        self.state = _PENDING


def _reserve() -> Optional["_Reservation"]:
    """라우트에서 `run_in_threadpool` 진입 *전에* 호출한다.

    점유 수가 상한 미만이면 pending 예약을 만들고 점유 수를 1 늘린다. 상한이면
    None이고, 라우트는 대기열이나 스레드 자리를 기다리지 않고 그 자리에서 거절한다.

    아직 시작하지 않은 예약도 점유 수에 포함된다 — 스레드 자리를 기다리는 요청이
    상한을 차지하므로, 극단적으로는 전부 대기 중인데 503만 나가는 구간이 생길 수
    있다. 시민이 타임아웃까지 기다리는 것보다 즉시 안내를 받는 편이 낫다고 보고
    택한 보수적 동작이다.
    """
    global _active_extractions
    with _slot_lock:
        if _active_extractions >= MAX_CONCURRENT_EXTRACTIONS:
            return None
        _active_extractions += 1
        return _Reservation()


def _mark_started(reservation: "_Reservation") -> bool:
    """동기 함수 첫 줄. pending이면 running으로 전이하고 True.

    이미 released면 False — 취소로 예약이 반환된 뒤 뒤늦게 스레드 자리가 난
    경우이므로, 가져오기·파싱을 시작하지 않는다.
    """
    with _slot_lock:
        if reservation.state != _PENDING:
            return False
        reservation.state = _RUNNING
        return True


def _release_if_pending(reservation: "_Reservation") -> None:
    """라우트 `finally`. 아직 시작 전인 예약만 반환한다.

    running이면 아무것도 하지 않는다 — 반환 책임은 스레드에 있다. 실행 중인
    작업의 자리를 미리 비우면 실제 동시 작업이 상한을 넘는다.
    """
    global _active_extractions
    with _slot_lock:
        if reservation.state != _PENDING:
            return
        reservation.state = _RELEASED
        _active_extractions -= 1


def _release(reservation: "_Reservation") -> None:
    """동기 함수 `finally`. 실행 중이던 예약만 반환한다."""
    global _active_extractions
    with _slot_lock:
        if reservation.state != _RUNNING:
            return
        reservation.state = _RELEASED
        _active_extractions -= 1


class _ExtractStageError(Exception):
    """가져오기·파싱 단계에서 확정한 오류 코드·메시지를 라우트로 옮기는 내부 전달자.

    두 단계를 한 동기 함수로 묶었으므로, 어느 단계에서 난 오류인지를 여기에 담아
    나른다. 단계별 코드·메시지 대응은 `_extract_blocking`에 그대로 남아 있다.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


# 예약이 이미 반환된 뒤 스레드가 뒤늦게 실행됐을 때의 반환값. 아래 주석 참조.
_CANCELLED = object()


def _extract_blocking(url: str, reservation: "_Reservation"):
    """가져오기와 파싱을 한 슬롯 점유 구간 안에서 연속으로 실행한다.

    두 단계 사이에서 슬롯을 반환했다가 다시 잡으면, 파싱 중인 요청이 새 요청을
    들여보내 실제 동시 작업이 상한을 넘는다. 그래서 스레드 제출을 한 번으로 묶었다.

    `safe_fetch`와 `_scraper`는 모듈 전역으로 참조한다 — 시험이
    `patch.object(extract_api, "safe_fetch", ...)`로 모듈 속성을 패치하기 때문에,
    다른 모듈로 옮기거나 지역 이름에 묶으면 그 패치가 무력해진다.
    """
    if not _mark_started(reservation):
        # 예약이 이미 반환됐다 — 가져오기·파싱에 들어가지 않고 그대로 끝낸다.
        return _CANCELLED
    try:
        try:
            fetch_result = safe_fetch(url)
        except SafeFetchError as exc:
            raise _ExtractStageError(exc.code, exc.message) from None
        except Exception:
            raise _ExtractStageError(
                "EXTRACTOR_ERROR", "기사를 가져오는 중 오류가 발생했습니다.") from None

        try:
            article_data = _scraper._parse_response(
                fetch_result.response,
                parse_url=fetch_result.final_url,   # /extract만 최종 URL 기준
                original_url=url,                   # 정규화된 요청 URL
            )
        except ValueError:
            raise _ExtractStageError(
                "ARTICLE_NOT_FOUND", "기사 제목 또는 본문을 추출하지 못했습니다.") from None
        except Exception:
            # 예외 문자열·스택·내부 경로는 응답에 담지 않는다.
            raise _ExtractStageError(
                "EXTRACTOR_ERROR", "기사 파싱 중 오류가 발생했습니다.") from None

        return fetch_result, article_data
    finally:
        _release(reservation)


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

    # 예약은 스레드풀 진입 *전*이다. 스레드 자리를 얻은 뒤에 상한을 판단하면,
    # 공유 스레드풀이 찼을 때 거절하려고도 기다리게 된다.
    reservation = _reserve()
    if reservation is None:
        return _error("EXTRACTOR_BUSY", "추출 요청이 많아 지금은 처리하지 못했습니다.",
                      domain, started)

    # 예약 성공 직후, 다른 await 없이 try로 들어간다. 예약과 정리 책임 등록 사이에
    # await 지점이 있으면 그 틈에서 취소될 때 아무도 슬롯을 반환하지 않는다.
    try:
        outcome = await run_in_threadpool(_extract_blocking, url, reservation)
    except _ExtractStageError as exc:
        return _error(exc.code, exc.message, domain, started)
    except Exception:
        # 동기 함수가 시작되기 전, 스레드 제출 단계에서 난 예외. 여기서 잡지 않으면
        # 프레임워크 기본 500(text/plain)이 나가 오류 계약이 깨진다.
        # BaseException은 잡지 않는다 — CancelledError가 이 절에 걸리면 안 된다.
        return _error("EXTRACTOR_ERROR", "기사를 가져오는 중 오류가 발생했습니다.", domain, started)
    finally:
        _release_if_pending(reservation)

    if outcome is _CANCELLED:
        # 도달하지 않는 값 — `_mark_started()`가 False인 것은 예약이 취소로 이미
        # 반환된 경우뿐이고, 그때 이 코루틴은 CancelledError로 빠져나가 리턴값을
        # 소비하지 않는다. 방어적으로만 남긴다.
        return _error("EXTRACTOR_ERROR", "기사를 가져오는 중 오류가 발생했습니다.", domain, started)

    fetch_result, article_data = outcome

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
