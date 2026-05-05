"""
CR-Check — 문서 파일 패턴 코드 일괄 교체 스크립트
목적: current-criteria_v2_active.md 및 계획 문서 3개의
      헤딩 번호 + 본문 내 코드 언급을 새 체계로 교체
실행: python scripts/rename_docs_pattern_codes.py
작성일: 2026-04-26
"""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent  # cr-check 프로젝트 루트

# ── 대상 파일 목록 ────────────────────────────────────────────────
TARGET_FILES = [
    ROOT / "docs" / "current-criteria_v2_active.md",
    ROOT / "docs" / "PHASE_H_EXECUTION_PLAN_v1.0.md",
    ROOT / "docs" / "PIPELINE_IMPROVEMENT_PLAN_v1.1.md",
    ROOT / "docs" / "SESSION_CONTEXT_2026-04-25_v39.md",
]

# ── 소분류 코드 매핑 (3단계 → 2단계) ─────────────────────────────
CODE_MAP = {
    "1-1-1": "1-1", "1-1-2": "1-2", "1-1-3": "1-3",
    "1-1-4": "1-4", "1-1-5": "1-5",
    "1-2-1": "2-1", "1-2-2": "2-2", "1-2-3": "2-3",
    "1-3-1": "3-1", "1-3-2": "3-2", "1-3-3": "3-3",
    "1-3-4": "3-4", "1-3-5": "3-5",
    "1-4-1": "4-1", "1-4-2": "4-2",
    "1-5-1": "5-1", "1-5-2": "5-2", "1-5-3": "5-3", "1-5-4": "5-4",
    "1-6-1": "6-1", "1-6-2": "6-2", "1-6-3": "6-3",
    "1-7-1": "7-1", "1-7-2": "7-2", "1-7-3": "7-3",
    "1-7-4": "7-4", "1-7-5": "7-5", "1-7-6": "7-6",
    "1-8-1": "8-1", "1-8-2": "8-2",
}

# ── 대분류 헤딩 매핑 (current-criteria 전용) ──────────────────────
CATEGORY_MAP = {
    "1-1": "1", "1-2": "2", "1-3": "3", "1-4": "4",
    "1-5": "5", "1-6": "6", "1-7": "7", "1-8": "8",
}


def replace_codes_in_text(text: str, filename: str) -> tuple[str, list[str]]:
    """텍스트 내 패턴 코드를 새 체계로 교체. 변경 로그 반환."""
    log = []

    # 1. 소분류 헤딩 교체 (current-criteria 전용)
    #    ### **1-1-1. 사실 검증 부실** → ### **1-1. 사실 검증 부실**
    if "current-criteria" in filename:
        for old, new in CODE_MAP.items():
            pattern = rf'(###\s+\*\*){re.escape(old)}\.'
            replacement = rf'\g<1>{new}.'
            new_text, count = re.subn(pattern, replacement, text)
            if count:
                log.append(f"  [헤딩-소] {old}. → {new}. ({count}건)")
                text = new_text

        # 2. 대분류 헤딩 교체
        #    ## **1-1. 진실성과 정확성** → ## **1. 진실성과 정확성**
        for old, new in CATEGORY_MAP.items():
            pattern = rf'(##\s+\*\*){re.escape(old)}\.'
            replacement = rf'\g<1>{new}.'
            new_text, count = re.subn(pattern, replacement, text)
            if count:
                log.append(f"  [헤딩-대] {old}. → {new}. ({count}건)")
                text = new_text

    # 3. 본문 내 코드 언급 교체 (모든 파일)
    #    긴 코드(소분류)부터 처리 — 순서 엄수
    for old, new in CODE_MAP.items():
        # 단어 경계로 정확히 매칭 (숫자-숫자-숫자 형식)
        pattern = rf'(?<![0-9-]){re.escape(old)}(?![0-9-])'
        new_text, count = re.subn(pattern, new, text)
        if count:
            log.append(f"  [본문]   {old} → {new} ({count}건)")
            text = new_text

    return text, log


def process_file(path: Path) -> bool:
    """파일 처리 및 결과 출력. 성공 시 True 반환."""
    if not path.exists():
        print(f"⚠️  파일 없음 (건너뜀): {path.name}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    new_text, log = replace_codes_in_text(original, path.name)

    changed = len([l for l in log if "건)" in l and
                   not l.strip().startswith("  0건")])
    total = sum(
        int(re.search(r'\((\d+)건\)', l).group(1))
        for l in log if re.search(r'\((\d+)건\)', l)
    )

    print(f"\n📄 {path.name}")
    if not log:
        print("   변경 없음")
        return True

    for line in log:
        print(line)
    print(f"   → 총 {total}건 교체")

    # 미매핑 코드 잔존 확인
    remaining = re.findall(r'(?<![0-9-])1-[1-8]-[1-9](?![0-9-])', new_text)
    if remaining:
        print(f"   ⚠️  구버전 코드 잔존: {set(remaining)}")
        print("   변경 사항이 저장되지 않았습니다.")
        return False

    # 백업 후 저장
    shutil.copy(path, path.with_suffix(path.suffix + ".bak"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"   ✅ 저장 완료 (백업: {path.name}.bak)")
    return True


def main():
    print("=" * 55)
    print("CR-Check 문서 파일 패턴 코드 일괄 교체")
    print("=" * 55)

    all_ok = True
    for path in TARGET_FILES:
        ok = process_file(path)
        if not ok:
            all_ok = False

    print("\n" + "=" * 55)
    if all_ok:
        print("✅ 전체 완료. 커밋 후 PR 생성하세요.")
        print("   대상 파일:")
        for p in TARGET_FILES:
            print(f"   - {p.relative_to(ROOT)}")
    else:
        print("❌ 일부 파일에 문제가 있습니다. 위 로그를 확인하세요.")


if __name__ == "__main__":
    main()
