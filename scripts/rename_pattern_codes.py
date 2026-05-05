"""
CR-Check — pattern_id 코드 체계 정리 스크립트
목적: golden_dataset_labels.json 내 pattern_id 값을 새 코드 체계로 일괄 변환
      1-1-1 → 1-1 / 1-7-5 → 7-5 등
실행: python rename_pattern_codes.py
작성일: 2026-04-26
"""

import json
from pathlib import Path

# ── 매핑 테이블 (구 코드 → 신 코드) ──────────────────────────────
CODE_MAP = {
    # 1계열 (진실성과 정확성)
    "1-1-1": "1-1",
    "1-1-2": "1-2",
    "1-1-3": "1-3",
    "1-1-4": "1-4",
    "1-1-5": "1-5",
    # 2계열 (투명성과 책임성)
    "1-2-1": "2-1",
    "1-2-2": "2-2",
    "1-2-3": "2-3",
    # 3계열 (균형성과 공정성)
    "1-3-1": "3-1",
    "1-3-2": "3-2",
    "1-3-3": "3-3",
    "1-3-4": "3-4",
    "1-3-5": "3-5",
    # 4계열 (독립성과 자율성 — 메타패턴)
    "1-4-1": "4-1",
    "1-4-2": "4-2",
    # 5계열 (인권과 프라이버시)
    "1-5-1": "5-1",
    "1-5-2": "5-2",
    "1-5-3": "5-3",
    "1-5-4": "5-4",
    # 6계열 (전문성과 심층성)
    "1-6-1": "6-1",
    "1-6-2": "6-2",
    "1-6-3": "6-3",
    # 7계열 (언어와 표현의 윤리)
    "1-7-1": "7-1",
    "1-7-2": "7-2",
    "1-7-3": "7-3",
    "1-7-4": "7-4",
    "1-7-5": "7-5",
    "1-7-6": "7-6",
    # 8계열 (디지털 환경의 윤리)
    "1-8-1": "8-1",
    "1-8-2": "8-2",
}

# ── 파일 경로 ─────────────────────────────────────────────────────
INPUT_PATH = Path(__file__).parent.parent / "docs" / "golden_dataset_labels.json"
# 원본 보존 후 덮어쓰기
BACKUP_PATH = INPUT_PATH.with_suffix(".json.bak")


def rename_codes(data: dict) -> tuple[dict, list[str]]:
    """JSON 데이터 내 pattern_id 필드를 새 코드 체계로 변환.
    변경 로그를 함께 반환."""
    log = []

    for label in data.get("labels", []):
        cid = label.get("candidate_id", "")
        for pattern in label.get("expected_patterns", []):
            old = pattern.get("pattern_id", "")
            if old in CODE_MAP:
                new = CODE_MAP[old]
                pattern["pattern_id"] = new
                log.append(f"  [{cid}] pattern_id: {old} → {new}")
            elif old:
                log.append(f"  [{cid}] ⚠️  매핑 없음: {old} (변경 안 됨)")

    return data, log


def main():
    if not INPUT_PATH.exists():
        print(f"❌ 파일을 찾을 수 없음: {INPUT_PATH}")
        return

    # 원본 읽기
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"✅ 파일 로드: {INPUT_PATH}")
    print(f"   레이블 수: {len(data.get('labels', []))}건\n")

    # 변환
    data, log = rename_codes(data)

    # 변경 내역 출력
    print("── 변경 내역 ───────────────────────────────")
    for line in log:
        print(line)
    print(f"\n총 {len([l for l in log if '→' in l])}건 변경, "
          f"{len([l for l in log if '⚠️' in l])}건 미매핑\n")

    # 미매핑 항목이 있으면 중단
    unmapped = [l for l in log if "⚠️" in l]
    if unmapped:
        print("❌ 미매핑 항목이 있습니다. CODE_MAP을 확인하세요.")
        print("   변경 사항이 저장되지 않았습니다.")
        return

    # 백업 후 저장
    import shutil
    shutil.copy(INPUT_PATH, BACKUP_PATH)
    print(f"📦 원본 백업: {BACKUP_PATH}")

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 저장 완료: {INPUT_PATH}")
    print("\n다음 단계: pattern_matcher.py 하드코딩 코드 교체")


if __name__ == "__main__":
    main()
