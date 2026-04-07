# backend/core/meta_pattern_inference.py
"""
CR-Check — 메타 패턴 추론 모듈

1-4-1(외부 압력)과 1-4-2(상업적 동기)는 직접 감지 불가.
다른 패턴의 조합(inferred_by 관계)으로 추론한다.

Step 1 (Deterministic):
  DB에서 inferred_by 관계 동적 조회 → 필수/보강 지표 매칭 → 트리거 판정
  코드에 추론 규칙을 하드코딩하지 않는다.

Step 2 (Probabilistic):
  리포트 생성 Sonnet 호출에 통합 (report_generator.py에서 조건부 프롬프트 주입)
  이 모듈에서는 Step 1만 담당.
"""

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MetaPatternResult:
    """메타 패턴 추론 결과."""
    triggered: bool = False
    meta_pattern_code: str = ""
    meta_pattern_name: str = ""
    confidence: str = ""         # "low" / "medium" / "high"
    required_matches: list[str] = field(default_factory=list)
    supporting_matches: list[str] = field(default_factory=list)
    reasoning: str = ""          # Sonnet이 리포트에서 직접 생성


# 메타 패턴 코드 → 이름 매핑
_META_PATTERN_NAMES = {
    "1-4-1": "외부 압력에 의한 왜곡",
    "1-4-2": "상업적 동기에 의한 왜곡",
}


def _compute_confidence(required_count: int, supporting_count: int) -> str:
    """확신도 사전 계산."""
    if required_count >= 2 and supporting_count >= 2:
        return "high"
    elif required_count >= 1 and supporting_count >= 2:
        return "medium"
    else:
        return "low"


def check_meta_patterns(
    detected_pattern_codes: list[str],
    sb_url: str,
    sb_key: str,
) -> list[MetaPatternResult]:
    """탐지된 패턴 코드를 기반으로 메타 패턴 추론을 수행한다.

    Args:
        detected_pattern_codes: Sonnet Solo가 확정한 패턴 코드 리스트
        sb_url: Supabase URL
        sb_key: Supabase service role key

    Returns:
        MetaPatternResult 리스트 (triggered=True인 것만 포함하거나,
        모든 메타 패턴에 대한 결과 포함)
    """
    if not detected_pattern_codes:
        return []

    # 1. DB에서 inferred_by 관계 동적 조회
    try:
        headers = {
            "apikey": sb_key,
            "Authorization": f"Bearer {sb_key}",
        }

        # pattern_relations + patterns JOIN으로 코드 가져오기
        # REST API에서는 JOIN이 제한적이므로, RPC 없이 2단계 조회
        # (a) inferred_by 관계 전체
        r = httpx.get(
            f"{sb_url}/rest/v1/pattern_relations"
            "?select=source_pattern_id,target_pattern_id,inference_role"
            "&relation_type=eq.inferred_by",
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        relations = r.json()

        if not relations:
            logger.info("메타 패턴: inferred_by 관계 0건 — 추론 건너뜀")
            return []

        # (b) 관련 패턴 ID → 코드 매핑
        all_ids = set()
        for rel in relations:
            all_ids.add(rel["source_pattern_id"])
            all_ids.add(rel["target_pattern_id"])

        id_list = ",".join(str(i) for i in all_ids)
        r2 = httpx.get(
            f"{sb_url}/rest/v1/patterns"
            f"?select=id,code&id=in.({id_list})",
            headers=headers,
            timeout=10,
        )
        r2.raise_for_status()
        id_to_code = {p["id"]: p["code"] for p in r2.json()}

    except Exception as e:
        logger.warning(f"메타 패턴 DB 조회 실패, 추론 건너뜀: {e}")
        return []

    # 2. 메타 패턴별로 그룹화
    # { "1-4-1": { "required": ["1-1-1", "1-1-2"], "supporting": ["1-3-2", "1-3-1"] } }
    meta_groups: dict[str, dict[str, list[str]]] = {}

    for rel in relations:
        source_code = id_to_code.get(rel["source_pattern_id"], "")
        target_code = id_to_code.get(rel["target_pattern_id"], "")
        role = rel.get("inference_role", "")

        if not source_code or not target_code or not role:
            continue

        if target_code not in meta_groups:
            meta_groups[target_code] = {"required": [], "supporting": []}
        meta_groups[target_code][role].append(source_code)

    # 3. 탐지된 패턴과 대조
    detected_set = set(detected_pattern_codes)
    results = []

    for meta_code, group in meta_groups.items():
        required_matches = [c for c in group["required"] if c in detected_set]
        supporting_matches = [c for c in group["supporting"] if c in detected_set]

        # 4. 트리거 조건: 필수 1개+ AND 보강 1개+
        triggered = len(required_matches) >= 1 and len(supporting_matches) >= 1

        # 5. 확신도
        confidence = _compute_confidence(len(required_matches), len(supporting_matches)) if triggered else ""

        results.append(MetaPatternResult(
            triggered=triggered,
            meta_pattern_code=meta_code,
            meta_pattern_name=_META_PATTERN_NAMES.get(meta_code, meta_code),
            confidence=confidence,
            required_matches=required_matches,
            supporting_matches=supporting_matches,
        ))

    if results:
        triggered_count = sum(1 for r in results if r.triggered)
        logger.info(f"메타 패턴 추론: {len(results)}개 검사, {triggered_count}개 발동")

    return results
