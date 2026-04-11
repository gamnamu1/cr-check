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
from pathlib import Path

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
    """
    if not path.exists():
        raise FileNotFoundError(f"주입 파일 없음: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in raw}
    logger.info(f"주입 파일 로드 (label 포함): {len(by_id)}건 — {path}")
    return by_id


# ── 조인 + 지표 ──────────────────────────────────────────────────
def join_results_with_labels(
    results: list[dict], injected_by_id: dict[str, dict]
) -> list[dict]:
    """실행 결과와 주입 파일 label을 id로 조인."""
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
                "label": injected.get("label", {}),
                "analysis": result.get("analysis", {}),
            }
        )
    if missing:
        logger.warning(f"레이블 없는 실행 결과: {len(missing)}건 — {missing}")
    return joined


def _extract_detected_codes(analysis: dict) -> set[str]:
    """analysis 응답에서 탐지된 패턴 코드 집합을 추출.

    analysis_results 스키마는 detected_patterns 필드를 가짐 (v25 기준).
    항목은 dict 또는 str 양쪽 형식을 허용.
    """
    detected = analysis.get("detected_patterns") or analysis.get(
        "detected_categories"
    )
    if not detected:
        return set()
    codes: set[str] = set()
    for p in detected:
        if isinstance(p, dict):
            code = p.get("pattern_code") or p.get("code")
            if code:
                codes.add(str(code))
        elif isinstance(p, str):
            codes.add(p)
    return codes


def _extract_expected_codes(label: dict) -> set[str]:
    """label dict에서 기대 패턴 코드 집합을 추출.

    주입 파일 스키마가 확정되지 않았으므로 여러 키 이름을 허용.
    """
    for key in ("expected_patterns", "expected_codes", "gold_patterns", "patterns"):
        value = label.get(key)
        if value:
            if isinstance(value, list):
                return {
                    str(p["code"] if isinstance(p, dict) and "code" in p else p)
                    for p in value
                }
    return set()


def compute_metrics(joined: list[dict]) -> dict:
    """건별 정밀도/재현율 + 매크로 평균 계산.

    주입 파일의 label 스키마가 확정되지 않은 단계이므로, expected 필드명은
    `_extract_expected_codes`가 여러 후보를 시도한다. 실제 스키마 확정 후
    필요 시 이 함수를 미세 조정.
    """
    per_item: list[dict] = []
    for entry in joined:
        expected = _extract_expected_codes(entry["label"])
        detected = _extract_detected_codes(entry["analysis"])
        tp = len(expected & detected)
        fp = len(detected - expected)
        fn = len(expected - detected)
        precision = tp / (tp + fp) if (tp + fp) > 0 else None
        recall = tp / (tp + fn) if (tp + fn) > 0 else None
        per_item.append(
            {
                "id": entry["id"],
                "url": entry["url"],
                "expected": sorted(expected),
                "detected": sorted(detected),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "misclassified": tp == 0 and (fp + fn) > 0,
            }
        )

    # 매크로 평균 (per-item 평균)
    valid_p = [m["precision"] for m in per_item if m["precision"] is not None]
    valid_r = [m["recall"] for m in per_item if m["recall"] is not None]
    avg_precision = sum(valid_p) / len(valid_p) if valid_p else None
    avg_recall = sum(valid_r) / len(valid_r) if valid_r else None
    f1 = (
        2 * avg_precision * avg_recall / (avg_precision + avg_recall)
        if avg_precision and avg_recall
        else None
    )

    return {
        "total": len(per_item),
        "valid_precision_count": len(valid_p),
        "valid_recall_count": len(valid_r),
        "aggregate": {
            "precision_macro": avg_precision,
            "recall_macro": avg_recall,
            "f1_macro": f1,
        },
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
