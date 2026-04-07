# backend/core/citation_resolver.py
"""
CR-Check — 결정론적 인용 후처리 모듈

Sonnet 리포트의 <cite ref="..."/> 태그를 규범 원문으로 치환한다.
매칭은 ReportResult.ethics_refs (in-memory)에서만 수행한다.
DB fallback 조회를 하지 않는다 (옵션 B — Gamnamu 승인).

근거: Sonnet에게 제공되지 않은 규범 코드를 DB에서 찾아 치환하면,
pattern_ethics_relations에서 검증되지 않은 관계가 리포트에 포함된다.
in-memory에 없는 ref는 환각으로 간주하여 제거한다.
"""

import re
import logging

from .report_generator import EthicsReference

logger = logging.getLogger(__name__)

# cite 태그 패턴: <cite ref="..."/>, <cite ref="..." />, <cite ref="..."></cite>
_CITE_PATTERN = re.compile(
    r'<cite\s+ref="([^"]+)"\s*(?:/>|>\s*</cite>)'
)


def _truncate_text(text: str, max_len: int = 200) -> str:
    """텍스트를 max_len 이하로 절단. 어절/마침표 경계에서 끊는다."""
    if len(text) <= max_len:
        return text

    # max_len 이하의 마지막 공백 또는 마침표 위치를 찾는다
    truncated = text[:max_len]
    last_break = -1
    for i in range(len(truncated) - 1, -1, -1):
        if truncated[i] in (' ', '.', '。', ',', '\n'):
            last_break = i
            break

    if last_break > 0:
        return truncated[:last_break + 1].rstrip() + "..."
    # 공백/마침표가 없으면 max_len에서 그냥 자름
    return truncated + "..."


def _format_citation(ref: EthicsReference, is_first: bool) -> str:
    """규범 인용 문자열을 생성한다.

    Args:
        ref: 규범 참조 정보
        is_first: 이 코드의 첫 출현 여부

    Returns:
        첫 출현: 「{title}: {원문 발취}」
        이후 출현: 「{title} 참조」
    """
    if not is_first:
        return f"「{ref.ethics_title} 참조」"

    full_text = _truncate_text(ref.ethics_full_text)
    return f"「{ref.ethics_title}: {full_text}」"


def resolve_citations(
    report_text: str,
    ethics_refs: list[EthicsReference],
) -> tuple[str, list[str]]:
    """Sonnet 리포트의 <cite ref="..."/> 태그를 규범 원문으로 치환.

    Args:
        report_text: Sonnet이 생성한 리포트 (cite 태그 포함)
        ethics_refs: generate_report()에서 반환된 규범 참조 목록
                     (Sonnet에게 제공된 컨텍스트와 동일)

    Returns:
        (resolved_report, hallucinated_refs)
        - resolved_report: cite 태그가 원문으로 치환된 최종 리포트
        - hallucinated_refs: 매칭 실패하여 제거된 ref 코드 리스트
    """
    if not report_text:
        return report_text, []

    # ethics_refs를 code → EthicsReference 매핑으로 변환
    # 동일 코드가 여러 패턴에서 올 수 있으므로 첫 번째만 사용
    ref_map: dict[str, EthicsReference] = {}
    for ref in ethics_refs:
        if ref.ethics_code not in ref_map:
            ref_map[ref.ethics_code] = ref

    original_length = len(report_text)
    hallucinated_refs: list[str] = []
    seen_codes: set[str] = set()  # 중복 인용 추적
    cite_count = 0

    def _replace_cite(match: re.Match) -> str:
        nonlocal cite_count
        cite_count += 1
        ref_code = match.group(1)

        if ref_code not in ref_map:
            hallucinated_refs.append(ref_code)
            return ""  # 환각 — 태그 제거

        is_first = ref_code not in seen_codes
        seen_codes.add(ref_code)
        return _format_citation(ref_map[ref_code], is_first)

    resolved = _CITE_PATTERN.sub(_replace_cite, report_text)

    # 환각 태그 제거 후 발생할 수 있는 이중 공백 정리
    resolved = re.sub(r' {2,}', ' ', resolved)

    # 가드레일: 치환 후 길이 검증
    resolved_length = len(resolved)
    if original_length > 0 and resolved_length > original_length * 3:
        logger.warning(
            f"치환 후 리포트 길이 비정상 팡창: "
            f"{original_length}자 → {resolved_length}자 ({resolved_length / original_length:.1f}배)"
        )

    # 환각 ref 로그
    if hallucinated_refs:
        logger.warning(f"환각 ref 제거됨: {hallucinated_refs}")

    logger.info(
        f"CitationResolver: {cite_count}개 cite 태그 처리 "
        f"(치환 {cite_count - len(hallucinated_refs)}, 환각 제거 {len(hallucinated_refs)})"
    )

    return resolved, hallucinated_refs
