# backend/core/storage.py
"""
CR-Check — Phase D 분석 결과 아카이빙 모듈

- get_cached_analysis(url): URL 정규화 → articles + analysis_results 조회 → 캐시 응답
- save_analysis_result(...): articles UPSERT → share_id 생성 → analysis_results INSERT
- normalize_url(url): 트래킹 파라미터 제거로 캐시 키 안정화

설계 원칙:
- 모든 DB 호출 실패는 logger.error로만 남기고 None 반환 (graceful degradation).
  파이프라인을 막지 않는다.
- httpx.HTTPStatusError와 일반 Exception을 분리하여 로그 정보량 확보.
"""

import logging
import secrets
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import httpx

from .db import _get_supabase_config

logger = logging.getLogger(__name__)


# ── URL 정규화 유틸 ─────────────────────────────────────────────

def normalize_url(url: str) -> str:
    """URL에서 트래킹 파라미터를 제거하여 캐시 키로 사용."""
    parsed = urlparse(url)
    # 제거할 파라미터 접두어
    remove_prefixes = ('utm_', 'fbclid', 'gclid', 'mc_', 'ref', 'source')
    params = parse_qs(parsed.query)
    cleaned = {
        k: v for k, v in params.items()
        if not any(k.startswith(p) for p in remove_prefixes)
    }
    clean_query = urlencode(cleaned, doseq=True)
    return urlunparse(parsed._replace(query=clean_query, fragment=''))


# ── 캐시 조회 ───────────────────────────────────────────────────

def get_cached_analysis(url: str) -> dict | None:
    """URL로 기존 분석 결과를 조회한다. 없거나 실패하면 None."""
    normalized = normalize_url(url)
    sb_url, sb_key = _get_supabase_config()
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }

    # 1. articles 테이블에서 조회
    try:
        r = httpx.get(
            f"{sb_url}/rest/v1/articles",
            headers=headers,
            params={
                "url": f"eq.{normalized}",
                "select": "id,title,publisher,journalist,publish_date",
            },
            timeout=10,
        )
        r.raise_for_status()
        articles = r.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"캐시 조회(articles) 실패: HTTP {e.response.status_code} - {e.response.text[:300]}"
        )
        return None
    except Exception as e:
        logger.error(f"캐시 조회(articles) 중 예기치 못한 에러 [{type(e).__name__}]: {e}")
        return None

    if not articles:
        return None

    article = articles[0]
    article_id = article["id"]

    # 2. analysis_results에서 최신 1건 조회
    try:
        r = httpx.get(
            f"{sb_url}/rest/v1/analysis_results",
            headers=headers,
            params={
                "article_id": f"eq.{article_id}",
                "order": "created_at.desc",
                "limit": "1",
                "select": "*",
            },
            timeout=10,
        )
        r.raise_for_status()
        rows = r.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"캐시 조회(analysis_results) 실패: HTTP {e.response.status_code} - {e.response.text[:300]}"
        )
        return None
    except Exception as e:
        logger.error(
            f"캐시 조회(analysis_results) 중 예기치 못한 에러 [{type(e).__name__}]: {e}"
        )
        return None

    if not rows:
        return None

    ar = rows[0]
    article_analysis = ar.get("article_analysis") or {}

    # 3. 두 출처 메타를 병합
    article_info = {
        "title": article.get("title", ""),
        "url": normalized,
        "publisher": article.get("publisher"),
        "publishDate": article.get("publish_date"),
        "journalist": article.get("journalist"),
    }
    # JSONB 안의 Sonnet 분석 메타 병합
    for key in ("articleType", "articleElements", "editStructure", "reportingMethod", "contentFlow"):
        if article_analysis.get(key):
            article_info[key] = article_analysis[key]

    return {
        "article_info": article_info,
        "reports": {
            "comprehensive": ar.get("comprehensive_report") or "",
            "journalist": ar.get("journalist_report") or "",
            "student": ar.get("student_report") or "",
        },
        "share_id": ar.get("share_id"),
        "analyzed_at": ar.get("created_at"),
        "is_cached": True,
    }


# ── share_id 기반 조회 ──────────────────────────────────────────

def get_analysis_by_share_id(share_id: str) -> dict | None:
    """share_id로 분석 결과를 조회한다 (공유 URL 엔드포인트용).

    PostgREST의 외래키 자동 JOIN(`select=*,articles(*)`)을 활용하여
    analysis_results + articles를 한 번에 가져온다.
    """
    sb_url, sb_key = _get_supabase_config()
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }

    try:
        r = httpx.get(
            f"{sb_url}/rest/v1/analysis_results",
            headers=headers,
            params={
                "share_id": f"eq.{share_id}",
                "select": "*,articles(*)",
                "limit": "1",
            },
            timeout=10,
        )
        r.raise_for_status()
        rows = r.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"share_id 조회 실패: HTTP {e.response.status_code} - {e.response.text[:300]}"
        )
        return None
    except Exception as e:
        logger.error(f"share_id 조회 중 예기치 못한 에러 [{type(e).__name__}]: {e}")
        return None

    if not rows:
        return None

    row = rows[0]
    article = row.get("articles") or {}
    article_analysis = row.get("article_analysis") or {}

    # 두 출처 메타 병합
    article_info = {
        "title": article.get("title", ""),
        "url": article.get("url", ""),
        "publisher": article.get("publisher"),
        "publishDate": article.get("publish_date"),
        "journalist": article.get("journalist"),
        **article_analysis,  # JSONB 안의 Sonnet 분석 메타
    }

    return {
        "article_info": article_info,
        "reports": {
            "comprehensive": row.get("comprehensive_report") or "",
            "journalist": row.get("journalist_report") or "",
            "student": row.get("student_report") or "",
        },
        "share_id": share_id,
        "analyzed_at": row.get("created_at"),
        "is_cached": True,
    }


# ── 결과 저장 ───────────────────────────────────────────────────

def _normalize_publish_date(s: str | None) -> str | None:
    """publish_date 문자열을 PostgreSQL TIMESTAMPTZ 호환 형식으로 정규화.

    스크래퍼가 사이트마다 다른 형식을 반환하므로(ISO 8601, 한국어 등),
    파싱 가능한 경우 ISO 형식으로 변환하고, 실패하면 None을 반환한다.
    """
    if not s:
        return None
    from datetime import datetime
    s = s.strip()
    # 1. 이미 ISO 8601 형식
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return s
    except (ValueError, TypeError):
        pass
    # 2. 한국어 점-구분 형식: "2023. 5. 15. 11:01" 또는 "2023.05.15 11:01:00"
    import re
    m = re.match(
        r"(\d{4})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})[.\s]*(?:(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?",
        s,
    )
    if m:
        try:
            year = int(m.group(1))
            month = int(m.group(2))
            day = int(m.group(3))
            hour = int(m.group(4) or 0)
            minute = int(m.group(5) or 0)
            second = int(m.group(6) or 0)
            return (
                f"{year:04d}-{month:02d}-{day:02d}T"
                f"{hour:02d}:{minute:02d}:{second:02d}+09:00"
            )
        except (ValueError, TypeError):
            pass
    # 3. 파싱 실패 → 폴백
    logger.warning(f"publish_date 파싱 실패, None으로 폴백: {s!r}")
    return None


def _upsert_article(
    sb_url: str,
    headers: dict,
    normalized_url: str,
    title: str,
    publisher: str | None,
    journalist: str | None,
    publish_date: str | None,
) -> int | None:
    """articles 테이블에 UPSERT 후 article_id 반환."""
    body = {"url": normalized_url, "title": title or ""}
    if publisher:
        body["publisher"] = publisher
    if journalist:
        body["journalist"] = journalist
    normalized_date = _normalize_publish_date(publish_date)
    if normalized_date:
        body["publish_date"] = normalized_date

    upsert_headers = {
        **headers,
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    try:
        r = httpx.post(
            f"{sb_url}/rest/v1/articles",
            headers=upsert_headers,
            params={"on_conflict": "url"},
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json()
        if rows and isinstance(rows, list):
            return rows[0].get("id")
        logger.error(f"articles UPSERT: 응답에 ID 없음 (응답={rows})")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(
            f"articles UPSERT 실패: HTTP {e.response.status_code} - {e.response.text[:300]}"
        )
        return None
    except Exception as e:
        logger.error(f"articles UPSERT 중 예기치 못한 에러 [{type(e).__name__}]: {e}")
        return None


def save_analysis_result(
    url: str,
    title: str,
    publisher: str | None,
    journalist: str | None,
    publish_date: str | None,
    result,  # pipeline.AnalysisResult — 순환 import 회피용 untyped
) -> str | None:
    """분석 결과를 DB에 저장하고 share_id를 반환한다.

    실패 시 None 반환 (파이프라인은 막지 않음).
    """
    normalized = normalize_url(url)
    sb_url, sb_key = _get_supabase_config()
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }

    # 1. articles UPSERT
    article_id = _upsert_article(
        sb_url, headers, normalized, title, publisher, journalist, publish_date,
    )
    if article_id is None:
        return None

    # 2. detected_patterns 직렬화
    pm = result.pattern_result
    validated_codes = pm.validated_pattern_codes if pm else set()
    detected_patterns = [
        {
            "pattern_code": d.pattern_code,
            "matched_text": d.matched_text,
            "severity": d.severity,
            "reasoning": d.reasoning,
        }
        for d in (pm.haiku_detections if pm else [])
        if d.pattern_code in validated_codes
    ]

    # 3. meta_patterns 직렬화 (실제 MetaPatternResult 필드명 사용)
    meta_patterns_payload = [
        {
            "meta_code": m.meta_pattern_code,
            "meta_name": m.meta_pattern_name,
            "triggered": m.triggered,
            "confidence": m.confidence,
            "required_matches": list(m.required_matches),
            "supporting_matches": list(m.supporting_matches),
        }
        for m in (result.meta_patterns or [])
    ]

    # 4. 리포트와 article_analysis 추출
    rr = result.report_result
    reports_dict = rr.reports if rr else {}
    article_analysis_payload = rr.article_analysis if rr else {}

    base_record = {
        "article_id": article_id,
        "comprehensive_report": reports_dict.get("comprehensive", ""),
        "journalist_report": reports_dict.get("journalist", ""),
        "student_report": reports_dict.get("student", ""),
        "article_analysis": article_analysis_payload or None,
        "overall_assessment": result.overall_assessment or None,
        "phase1_model": "claude-sonnet-4-5-20250929",
        "phase2_model": "claude-sonnet-4-6",
        "duration_seconds": result.total_seconds,
        "detected_patterns": detected_patterns or None,
        "meta_patterns": meta_patterns_payload or None,
    }

    # 5. share_id 생성 — 충돌 시 최대 3회 재시도
    insert_headers = {**headers, "Prefer": "return=representation"}
    for attempt in range(3):
        share_id = secrets.token_urlsafe(9)  # 12자
        record = {**base_record, "share_id": share_id}
        try:
            r = httpx.post(
                f"{sb_url}/rest/v1/analysis_results",
                headers=insert_headers,
                json=record,
                timeout=15,
            )
            r.raise_for_status()
            logger.info(f"분석 결과 저장 완료: share_id={share_id}, article_id={article_id}")
            return share_id
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            text = e.response.text[:300]
            # PostgREST: 409 Conflict 또는 23505(unique_violation) → share_id 충돌
            is_conflict = status == 409 or "23505" in text
            if is_conflict and attempt < 2:
                logger.warning(
                    f"share_id 충돌 (attempt {attempt + 1}/3), 재시도: {text[:120]}"
                )
                continue
            if is_conflict:
                logger.error(f"share_id 3회 충돌, 저장 포기: {text[:120]}")
            else:
                logger.error(
                    f"analysis_results INSERT 실패: HTTP {status} - {text}"
                )
            return None
        except Exception as e:
            logger.error(
                f"analysis_results INSERT 중 예기치 못한 에러 [{type(e).__name__}]: {e}"
            )
            return None

    return None
