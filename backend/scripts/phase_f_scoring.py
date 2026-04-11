#!/usr/bin/env python3
"""Phase F 집계기 — 실행 결과 + 레이블 사후 조인.

phase_f_validation.py가 완료한 블라인드 실행 결과 디렉토리와, 주입 파일의
label 필드를 사후에 조인하여 건별 정밀도/재현율과 오분류 사례를 추출한다.

실행과 채점을 **별도 스크립트**로 분리한 이유:
    - 실행기는 label을 메모리에 올리지 않음 (블라인드 원칙)
    - 집계기만 label을 로드하여 사후 조인 — 두 관심사를 코드 레벨에서 분리

사용:
    python backend/scripts/phase_f_scoring.py \\
        --run-dir backend/diagnostics/phase_f/run_20260411_120000 \\
        --inject-path backend/diagnostics/phase_f/injected/reserved_subset_20.json

출력:
    <run-dir>/_scoring.json  — 건별 지표 + 집계치
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

# 〔규범 마커〕 정규식 — 〔 와 〕 사이의 모든 문자 (줄바꿈 제외)
ETHICS_MARKER_RE = re.compile(r"〔([^〕]+)〕")

# 매핑 사전 경로 — generate_ethics_to_pattern_map.py가 생성
ETHICS_MAP_PATH = Path(__file__).resolve().parent / "ethics_to_pattern_map.json"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("phase_f_scoring")


# ── 로더 ─────────────────────────────────────────────────────────
def load_run_results(run_dir: Path) -> list[dict]:
    """실행 결과 JSON 파일들을 로드 (`result_<id>.json`)."""
    if not run_dir.exists():
        raise FileNotFoundError(f"실행 디렉토리 없음: {run_dir}")
    results: list[dict] = []
    for result_file in sorted(run_dir.glob("result_*.json")):
        data = json.loads(result_file.read_text(encoding="utf-8"))
        results.append(data)
    logger.info(f"실행 결과 로드: {len(results)}건 — {run_dir}")
    return results


def load_injected_with_labels(path: Path) -> dict[str, dict]:
    """주입 파일 전체(label 포함) 로드. id → item dict 반환.

    이 함수는 의도적으로 label 필드를 포함한 전체 객체를 로드한다.
    집계 단계에서만 호출되며, 실행 단계에서는 이 함수를 사용하지 않는다.

    Reserved Test Set v2 스키마: id 필드가 없으면 candidate_id 폴백.
    label 필드들(cr_category_*, is_true_negative, 등)은 최상위에 flat.
    """
    if not path.exists():
        raise FileNotFoundError(f"주입 파일 없음: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    # 최상위 형식 정규화: list 또는 {"candidates": [...]} 둘 다 허용
    # (metadata 등 기타 wrapper 필드는 무시)
    if isinstance(raw, dict):
        if "candidates" in raw and isinstance(raw["candidates"], list):
            raw = raw["candidates"]
        else:
            raise ValueError(
                "주입 파일이 dict이지만 'candidates' 리스트를 찾을 수 없습니다"
            )
    if not isinstance(raw, list):
        raise ValueError(
            f"주입 파일 최상위는 리스트 또는 candidates 키를 포함한 dict여야 "
            f"합니다 (받음: {type(raw).__name__})"
        )
    by_id: dict[str, dict] = {}
    for item in raw:
        key = item.get("id") or item.get("candidate_id")
        if key is None:
            continue
        by_id[str(key)] = item
    logger.info(f"주입 파일 로드 (label 포함): {len(by_id)}건 — {path}")
    return by_id


# ── 조인 + 지표 ──────────────────────────────────────────────────
def join_results_with_labels(
    results: list[dict], injected_by_id: dict[str, dict]
) -> list[dict]:
    """실행 결과와 주입 파일 label을 id로 조인.

    Reserved Test Set v2 스키마는 label 필드가 flat top-level이므로 injected
    전체를 label로 취급한다. source/difficulty_estimate/is_true_negative를
    joined dict의 top-level에도 노출하여 compute_metrics의 그룹화 집계를 단순화.
    """
    joined: list[dict] = []
    missing: list[str] = []
    for result in results:
        item_id = result.get("id")
        if item_id is None or item_id not in injected_by_id:
            missing.append(str(item_id))
            continue
        injected = injected_by_id[item_id]
        joined.append(
            {
                "id": item_id,
                "url": result.get("url"),
                "label": injected,  # v2: flat — injected 전체가 label 맥락
                "analysis": result.get("analysis", {}),
                "source": injected.get("source"),
                "difficulty": injected.get("difficulty_estimate"),
                "is_tn": bool(injected.get("is_true_negative")),
            }
        )
    if missing:
        logger.warning(f"레이블 없는 실행 결과: {len(missing)}건 — {missing}")
    return joined


def _to_category_level(code: str) -> str:
    """소분류 코드(1-1-1)를 대분류 코드(1-1)로 축소.

    Reserved Test Set v2의 cr_category_primary/secondary는 2-level
    ("1-1" 형식)이지만, DB의 patterns.code는 소분류 3-level("1-1-1" 형식)이다.
    비교 시 같은 계층으로 맞춘다.

    예:
        "1-1-1" → "1-1"
        "1-3-4" → "1-3"
        "1-1"   → "1-1"  (이미 2-level이면 그대로)
    """
    parts = code.split("-")
    if len(parts) >= 3:
        return "-".join(parts[:2])
    return code


@lru_cache(maxsize=1)
def _load_ethics_map() -> dict[str, list[str]]:
    """generate_ethics_to_pattern_map.py가 만든 정적 사전을 로드 (1회 캐시)."""
    if not ETHICS_MAP_PATH.exists():
        logger.warning(f"ethics_to_pattern_map.json 없음: {ETHICS_MAP_PATH}")
        return {}
    return json.loads(ETHICS_MAP_PATH.read_text(encoding="utf-8"))


def _extract_detected_codes(analysis: dict) -> tuple[set[str], set[str]]:
    """v25 아키텍처: reports 본문의 〔규범 마커〕 → 패턴 코드 집합 변환.

    `/analyze` 응답 JSON에는 detected_patterns 구조 필드가 없다.
    대신 Sonnet 4.6이 3종 리포트 본문에 〔규범명 제N조 M항〕 결정론적 마커로
    인용을 삽입한다 (report_generator.py _SONNET_SYSTEM_PROMPT L221-235).

    3종 리포트 본문을 합친 뒤 정규식으로 마커를 추출하고, 정적 매핑 사전
    (`ethics_to_pattern_map.json`)을 통해 패턴 코드 set으로 변환한다.

    Returns:
        (matched_codes, unmapped_markers) — 매핑 성공한 코드 집합과
        사전에 없는 마커 문자열 집합. 후자는 compute_metrics에서 집계.
    """
    reports = analysis.get("reports", {})
    if not isinstance(reports, dict):
        return set(), set()

    # 3종 리포트 본문을 합쳐 마커 추출 — 중복은 set이 흡수
    combined = "\n".join(
        str(reports.get(k, "") or "")
        for k in ("comprehensive", "journalist", "student")
    )
    markers = ETHICS_MARKER_RE.findall(combined)
    if not markers:
        return set(), set()

    ethics_map = _load_ethics_map()
    codes: set[str] = set()
    unmapped: set[str] = set()
    for marker in markers:
        # 공백 정규화: 연속 공백/탭/개행 → 단일 공백
        normalized = " ".join(marker.strip().split())
        if normalized in ethics_map:
            for code in ethics_map[normalized]:
                codes.add(str(code))
        else:
            unmapped.add(normalized)
    return codes, unmapped


def _extract_expected_codes(label: dict) -> set[str]:
    """Reserved Test Set v2 스키마 대응.

    - cr_category_primary + cr_category_secondary를 합쳐 기대 코드 집합 생성
    - is_true_negative == True인 경우 빈 set 반환 (TN 기대: 탐지 0건)
    """
    if label.get("is_true_negative") is True:
        return set()
    codes: set[str] = set()
    primary = label.get("cr_category_primary")
    if primary:
        codes.add(str(primary))
    secondary = label.get("cr_category_secondary") or []
    for c in secondary:
        if c:
            codes.add(str(c))
    return codes


def _bucket_by(
    per_item: list[dict], key: str
) -> dict[str, dict]:
    """per_item을 특정 키로 그룹화."""
    bucket: dict[str, dict] = {}
    for m in per_item:
        bucket_key = m.get(key) or "unknown"
        if bucket_key not in bucket:
            bucket[bucket_key] = {
                "count": 0,
                "tp_total": 0,
                "fp_total": 0,
                "fn_total": 0,
                "ids": [],
            }
        bucket[bucket_key]["count"] += 1
        bucket[bucket_key]["tp_total"] += m["tp"]
        bucket[bucket_key]["fp_total"] += m["fp"]
        bucket[bucket_key]["fn_total"] += m["fn"]
        bucket[bucket_key]["ids"].append(m["id"])
    return bucket


def compute_metrics(joined: list[dict]) -> dict:
    """건별 정밀도/재현율 + 매크로 평균 + 카테고리 분류 집계.

    Reserved Test Set v2 대응:
    - TN(is_true_negative=True)은 기대 set이 비어있으므로 precision/recall 정의 불가.
      별도의 tn_correct 플래그로 "탐지 0건 여부"를 기록.
    - TP 건만 precision/recall 매크로 평균에 포함.
    - by_source / by_difficulty / tn_analysis 카테고리 집계 추가.
    """
    per_item: list[dict] = []
    all_unmapped: set[str] = set()
    for entry in joined:
        expected = _extract_expected_codes(entry["label"])
        detected_raw, unmapped = _extract_detected_codes(entry["analysis"])
        all_unmapped.update(unmapped)
        # 3-level 소분류(1-1-1) → 2-level 대분류(1-1)로 정규화
        # expected는 이미 2-level이므로 detected만 축소하면 set 연산 가능
        detected = {_to_category_level(c) for c in detected_raw}
        is_tn = entry.get("is_tn", False)
        tp = len(expected & detected)
        fp = len(detected - expected)
        fn = len(expected - detected)

        if is_tn:
            # TN: 기대는 빈 set, 탐지 0건이 정상. precision/recall 정의 불가.
            precision: float | None = None
            recall: float | None = None
            tn_correct: bool | None = len(detected) == 0
            misclassified = False  # TP 관점의 오분류와 구분
        else:
            precision = tp / (tp + fp) if (tp + fp) > 0 else None
            recall = tp / (tp + fn) if (tp + fn) > 0 else None
            tn_correct = None
            misclassified = tp == 0 and (fp + fn) > 0

        per_item.append(
            {
                "id": entry["id"],
                "url": entry["url"],
                "source": entry.get("source"),
                "difficulty": entry.get("difficulty"),
                "is_tn": is_tn,
                "expected": sorted(expected),
                "detected": sorted(detected),
                "detected_raw": sorted(detected_raw),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "tn_correct": tn_correct,
                "misclassified": misclassified,
            }
        )

    # 매크로 평균 (TP만, TN 제외)
    tp_items = [m for m in per_item if not m["is_tn"]]
    tn_items = [m for m in per_item if m["is_tn"]]
    valid_p = [m["precision"] for m in tp_items if m["precision"] is not None]
    valid_r = [m["recall"] for m in tp_items if m["recall"] is not None]
    avg_precision = sum(valid_p) / len(valid_p) if valid_p else None
    avg_recall = sum(valid_r) / len(valid_r) if valid_r else None
    f1 = (
        2 * avg_precision * avg_recall / (avg_precision + avg_recall)
        if avg_precision and avg_recall
        else None
    )

    # 카테고리 분류 집계
    by_source = _bucket_by(per_item, "source")
    by_difficulty = _bucket_by(per_item, "difficulty")

    # TN 분석: 탐지 0건이 정답. 어떤 TN이 오탐되었는지 별도 리포트.
    tn_analysis: dict = {
        "total_tn": len(tn_items),
        "correct_tn": sum(1 for m in tn_items if m["tn_correct"] is True),
        "fp_tn_count": sum(1 for m in tn_items if m["tn_correct"] is False),
        "fp_tn_details": [
            {
                "id": m["id"],
                "detected": m["detected"],
                "fp_count": len(m["detected"]),
            }
            for m in tn_items
            if m["tn_correct"] is False
        ],
    }

    return {
        "interpretation_note": (
            "이 집계 결과는 파이프라인의 절대 성능 지표가 아닌, 프로덕션 동작 관찰 "
            "일지이다. Reserved Test Set의 label은 신문윤리위 결정과 Gamnamu 큐레이션 "
            "판단을 반영하며, 모델의 상이한 판단이 반드시 오류를 의미하지 않는다. "
            "시민 사용자의 비판적 독해가 최종 판단 레이어임을 전제한다."
        ),
        "total": len(per_item),
        "tp_count": len(tp_items),
        "tn_count": len(tn_items),
        "valid_precision_count": len(valid_p),
        "valid_recall_count": len(valid_r),
        "aggregate": {
            "precision_macro": avg_precision,
            "recall_macro": avg_recall,
            "f1_macro": f1,
        },
        "by_source": by_source,
        "by_difficulty": by_difficulty,
        "tn_analysis": tn_analysis,
        "unmapped_markers": sorted(all_unmapped),
        "per_item": per_item,
        "misclassified_ids": [m["id"] for m in per_item if m["misclassified"]],
    }


# ── 메인 ────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Phase F 결과 집계기")
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="phase_f_validation.py가 생성한 run_<timestamp> 디렉토리",
    )
    parser.add_argument(
        "--inject-path",
        type=Path,
        required=True,
        help="주입 파일 경로 (label 포함, 집계 단계에서만 로드)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="집계 결과 저장 경로 (기본: <run-dir>/_scoring.json)",
    )
    args = parser.parse_args()

    results = load_run_results(args.run_dir)
    injected = load_injected_with_labels(args.inject_path)
    joined = join_results_with_labels(results, injected)
    logger.info(f"조인 완료: {len(joined)}건")

    metrics = compute_metrics(joined)
    output_path = args.output or (args.run_dir / "_scoring.json")
    output_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"집계 결과 저장: {output_path}")

    agg = metrics["aggregate"]
    logger.info(
        "Aggregate — precision_macro: %s, recall_macro: %s, f1_macro: %s",
        agg["precision_macro"],
        agg["recall_macro"],
        agg["f1_macro"],
    )
    if metrics["misclassified_ids"]:
        logger.info(
            f"오분류 {len(metrics['misclassified_ids'])}건: "
            f"{metrics['misclassified_ids']}"
        )


if __name__ == "__main__":
    main()
