"""Wave 1 · S6 — 인용 감사(citation audit) 순수 모듈.

Sonnet 리포트 본문에서 〔...〕 형태의 인용 라벨을 추출하고,
Phase 2에 제공된 규범 컨텍스트의 정식 인용명 목록과 normalized exact match로 대조한다.

설계 원칙:
- 관측·로깅 전용. 재시도/차단/사용자 경고 없음.
- DB/Anthropic/Supabase client import 금지 (순수 함수).
- 순환 import 회피: EthicsReference를 import하지 않고 덕타이핑으로 접근.
- 부분/접두/유사도 매칭 금지 — normalized exact match만.
- 보수적 정규화: 공백·전각 숫자 정리만, 숫자·조항 구분자 보존.
- title에서 source/article_number 파싱 금지.
- 내부 코드(JEC-/PCP- 등)는 canonical citation으로 사용하지 않음.
"""
import re
from typing import Any

_VERSION = "wave1_s6_v1"

# 〔...〕 라벨 추출 — 동일 줄 안에서만 매칭(〕가 줄을 넘지 않는다 가정).
_BRACKET_PATTERN = re.compile(r"〔([^〕]+)〕")

# 전각 숫자 0~9 → 반각. NFKC 같은 광범위 정규화는 토큰 변형 위험으로 회피.
_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def extract_citation_labels(text: str) -> list[str]:
    """텍스트에서 〔...〕 형태의 인용 라벨을 등장 순서대로 추출. 빈 라벨은 제외."""
    if not text:
        return []
    return [m for m in _BRACKET_PATTERN.findall(text) if m.strip()]


def normalize_citation_label(label: str) -> str:
    """비교용 정규화 — 보수적.

    허용: 앞뒤 공백 제거, 개행/탭 → 공백, 연속 공백 1칸 축소, 전각 숫자 → 반각.
    금지: 숫자 제거, 조/항/호 구분자 제거, 문서명 토큰 제거.
    """
    if not label:
        return ""
    s = label.translate(_FULLWIDTH_DIGITS)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _safe_str(value: Any) -> str:
    """None은 빈 문자열로, 그 외는 str."""
    return "" if value is None else str(value)


def build_allowed_citations(refs: list[Any]) -> list[dict[str, Any]]:
    """EthicsReference 목록 → canonical 정식 인용명 dict 리스트.

    덕타이핑(getattr)으로 ethics_source / ethics_article_number를 읽어
    `source + " " + article_number`를 label로 만든다.
    둘 다 비어 있으면 canonical citation 생성 불가 → allowed에서 제외.
    title에서 파싱하지 않는다.
    """
    allowed: list[dict[str, Any]] = []
    for r in refs or []:
        source = _safe_str(getattr(r, "ethics_source", "")).strip()
        article = _safe_str(getattr(r, "ethics_article_number", "")).strip()
        if not source and not article:
            continue
        label_parts = [p for p in (source, article) if p]
        label = " ".join(label_parts)
        allowed.append({
            "label": label,
            "normalized": normalize_citation_label(label),
            "source": source,
            "article_number": article,
            "title": _safe_str(getattr(r, "ethics_title", "")),
            "tier": getattr(r, "ethics_tier", None),
            "relation_type": _safe_str(getattr(r, "relation_type", "")) or None,
            "strength": _safe_str(getattr(r, "strength", "")) or None,
            "reasoning": getattr(r, "reasoning", None),
            # 내부 ethics_code: 디버깅용 metadata. 사용자-facing 노출 금지.
            "ethics_code": _safe_str(getattr(r, "ethics_code", "")) or None,
        })
    return allowed


def _coerce_report_text(value: Any) -> str:
    """리포트 값이 문자열이면 그대로, dict면 body/text/content/report 키 우선 추출."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("body", "text", "content", "report"):
            v = value.get(key)
            if isinstance(v, str):
                return v
    return ""


def _audit_one_report(text: str, allowed_norm: set[str]) -> dict[str, Any]:
    used = extract_citation_labels(text)
    matched: list[str] = []
    unmatched: list[str] = []
    seen: set[str] = set()
    used_unique: list[str] = []
    for raw in used:
        norm = normalize_citation_label(raw)
        if norm not in seen:
            seen.add(norm)
            used_unique.append(raw)
        if norm in allowed_norm:
            matched.append(raw)
        else:
            unmatched.append(raw)
    return {
        "used": used,
        "used_unique": used_unique,
        "matched": matched,
        "unmatched": unmatched,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "allowed_count": 0,
        "used_total": 0,
        "used_unique_count": 0,
        "matched_total": 0,
        "unmatched_total": 0,
        "match_rate": None,
    }


def verify_report_citations(
    reports: dict[str, Any],
    refs: list[Any],
) -> dict[str, Any]:
    """3종 리포트 인용 감사. JSON 직렬화 가능한 dict 반환.

    호출자가 별도 try/except로 감싸지 않더라도 안전하게 동작하도록
    내부 예외를 흡수해 status='error' 객체를 돌려준다.
    리포트 생성·저장 자체는 호출 측에서 그대로 진행되어야 한다.
    """
    notes: list[str] = []
    try:
        allowed = build_allowed_citations(refs)

        # source/article_number가 둘 다 비어 allowed에서 제외된 ref 카운트
        excluded = 0
        for r in (refs or []):
            src = _safe_str(getattr(r, "ethics_source", "")).strip()
            art = _safe_str(getattr(r, "ethics_article_number", "")).strip()
            if not src and not art:
                excluded += 1
        if excluded:
            notes.append(
                f"{excluded} ref(s) excluded from allowed: "
                "missing both ethics_source and ethics_article_number"
            )

        allowed_norm = {a["normalized"] for a in allowed}

        report_audits: dict[str, dict[str, Any]] = {}
        used_total = 0
        used_unique_norms: set[str] = set()
        matched_total = 0
        unmatched_total = 0

        for report_key, value in (reports or {}).items():
            text = _coerce_report_text(value)
            if not isinstance(value, str) and not text:
                notes.append(f"report '{report_key}': body field 없음 또는 비문자열")
            audit = _audit_one_report(text, allowed_norm)
            report_audits[report_key] = audit
            used_total += len(audit["used"])
            matched_total += audit["matched_count"]
            unmatched_total += audit["unmatched_count"]
            for raw in audit["used_unique"]:
                used_unique_norms.add(normalize_citation_label(raw))

        match_rate = (matched_total / used_total) if used_total > 0 else None

        return {
            "version": _VERSION,
            "status": "ok",
            "summary": {
                "allowed_count": len(allowed),
                "used_total": used_total,
                "used_unique_count": len(used_unique_norms),
                "matched_total": matched_total,
                "unmatched_total": unmatched_total,
                "match_rate": match_rate,
            },
            "allowed_citations": allowed,
            "reports": report_audits,
            "notes": notes,
        }
    except Exception as e:
        return {
            "version": _VERSION,
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
            "summary": _empty_summary(),
            "allowed_citations": [],
            "reports": {},
            "notes": ["citation audit failed; report generation preserved"],
        }
