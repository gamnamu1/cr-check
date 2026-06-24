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


def _insert_ethics_snapshot(
    sb_url: str,
    headers: dict,
    analysis_id: int,
    ethics_refs: list,
) -> None:
    """analysis_ethics_snapshot에 핵심 규범 스냅샷을 배치 INSERT.

    1차: violates + (strong|moderate). 1건 이상이면 이를 사용.
    2차: 1차가 0건이면 related_to + (strong|moderate)로 fallback.
    둘 다 0건이면 건너뜀. 실패해도 logger.warning만 남기고 반환.
    """
    # 1. 스냅샷 대상 필터 (primary 우선, fallback reference)
    primary = [
        r for r in ethics_refs
        if getattr(r, "relation_type", "") == "violates"
        and getattr(r, "strength", "") in ("strong", "moderate")
    ]
    if primary:
        targets = primary
    else:
        targets = [
            r for r in ethics_refs
            if getattr(r, "relation_type", "") == "related_to"
            and getattr(r, "strength", "") in ("strong", "moderate")
        ]

    if not targets:
        logger.info("스냅샷 대상 규범 0건, 건너뜀")
        return

    # 2. ethics_code 기준 중복 제거 (등장 순서 유지)
    seen: set[str] = set()
    unique_targets: list = []
    for r in targets:
        code = getattr(r, "ethics_code", "")
        if not code or code in seen:
            continue
        seen.add(code)
        unique_targets.append(r)

    if not unique_targets:
        logger.info("스냅샷 대상 규범 0건, 건너뜀")
        return

    codes = [getattr(r, "ethics_code") for r in unique_targets]

    # 3. ethics_codes 배치 SELECT — code → (id, version) 조회
    try:
        select_r = httpx.get(
            f"{sb_url}/rest/v1/ethics_codes",
            headers=headers,
            params={
                "code": f"in.({','.join(codes)})",
                "select": "id,code,version",
            },
            timeout=10,
        )
        select_r.raise_for_status()
        ec_rows = select_r.json()
    except httpx.HTTPStatusError as e:
        logger.warning(
            f"스냅샷 ethics_codes 조회 실패: HTTP {e.response.status_code} - "
            f"{e.response.text[:300]}"
        )
        return
    except Exception as e:
        logger.warning(
            f"스냅샷 ethics_codes 조회 중 예기치 못한 에러 "
            f"[{type(e).__name__}]: {e}"
        )
        return

    if not ec_rows:
        logger.warning(f"스냅샷 ethics_codes 응답 0건: codes={codes}")
        return

    # 4. code → (id, version) 매핑
    code_map: dict[str, tuple[int, int]] = {}
    for row in ec_rows:
        code = row.get("code")
        ec_id = row.get("id")
        ec_version = row.get("version")
        if code and ec_id is not None and ec_version is not None:
            code_map[code] = (ec_id, ec_version)

    # 5. 스냅샷 rows 구성
    snapshot_rows: list[dict] = []
    for r in unique_targets:
        code = getattr(r, "ethics_code", "")
        if code not in code_map:
            logger.warning(f"스냅샷 매핑 누락, 건너뜀: code={code}")
            continue
        ec_id, ec_version = code_map[code]
        snapshot_rows.append({
            "analysis_id": analysis_id,
            "ethics_code_id": ec_id,
            "snapshot_full_text": getattr(r, "ethics_full_text", "") or "",
            "snapshot_version": ec_version,
        })

    if not snapshot_rows:
        logger.warning("스냅샷 rows 0건 (모두 매핑 실패), 건너뜀")
        return

    # 6. 배치 INSERT (Prefer: return=minimal)
    try:
        insert_headers = {**headers, "Prefer": "return=minimal"}
        ins_r = httpx.post(
            f"{sb_url}/rest/v1/analysis_ethics_snapshot",
            headers=insert_headers,
            json=snapshot_rows,
            timeout=15,
        )
        ins_r.raise_for_status()
        logger.info(
            f"스냅샷 INSERT 완료: analysis_id={analysis_id}, "
            f"count={len(snapshot_rows)}"
        )
    except httpx.HTTPStatusError as e:
        logger.warning(
            f"스냅샷 INSERT 실패: HTTP {e.response.status_code} - "
            f"{e.response.text[:300]}"
        )
    except Exception as e:
        logger.warning(
            f"스냅샷 INSERT 중 예기치 못한 에러 [{type(e).__name__}]: {e}"
        )


def save_analysis_result(
    url: str,
    title: str,
    publisher: str | None,
    journalist: str | None,
    publish_date: str | None,
    result,  # pipeline.AnalysisResult — 순환 import 회피용 untyped
    ethics_refs: list | None = None,  # report_generator.EthicsReference 리스트 (순환 import 회피)
    citation_audit: dict | None = None,  # S6: 관측 전용 metadata. 사용자-facing 노출 금지.
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
        # S6: 관측 전용 metadata. detected_patterns와 별도 컬럼으로 분리 저장된다.
        "citation_audit": citation_audit,
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
            # Prefer: return=representation 응답에서 analysis_id 추출 (스냅샷 INSERT용)
            analysis_id: int | None = None
            try:
                inserted_rows = r.json()
                if inserted_rows and isinstance(inserted_rows, list):
                    analysis_id = inserted_rows[0].get("id")
            except Exception as e_parse:
                logger.warning(
                    f"analysis_id 파싱 실패 (스냅샷 건너뜀) "
                    f"[{type(e_parse).__name__}]: {e_parse}"
                )
            # 스냅샷 INSERT — 실패해도 share_id 반환에 영향 없음
            if analysis_id is not None and ethics_refs:
                try:
                    _insert_ethics_snapshot(
                        sb_url, headers, analysis_id, ethics_refs,
                    )
                except Exception as e_snap:
                    logger.warning(
                        f"스냅샷 INSERT 외부 예외 (무시) "
                        f"[{type(e_snap).__name__}]: {e_snap}"
                    )
            logger.info(
                f"분석 결과 저장 완료: share_id={share_id}, article_id={article_id}"
            )
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
