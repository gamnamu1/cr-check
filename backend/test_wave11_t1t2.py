"""Wave 1.1 · T1+T2 단위 테스트 (DB·API 불요).

대상:
  1. mandatory_review_codes 파생 로직 (교집합: 일부/전부/없음)
  2. 필수 검토 블록 존재 + 블록 내 7-2·7-5 미포함
  3. 예시 3-1 삽입 확인
  4. 기존 예시 1·2·4~7 보존 + 순서 유지
  5. 탐지 개수 상한 제거(2026-07-13) — 숫자 상한 부재 + 중복 금지 원칙 보존
  6. phase1_forensic 배선 (mandatory_review_codes 실값 전달)

실행: backend/ 디렉터리에서  python3 -m unittest test_wave11_t1t2 -v
"""

import unittest

from core import pipeline
from core.pattern_matcher import (
    _SONNET_SOLO_PROMPT,
    _MANDATORY_REVIEW_TARGET_CODES,
    PatternMatchResult,
)


def _compiled_prompt() -> str:
    # _build_sonnet_solo_prompt와 동일한 치환 (DB 없이 빈 섹션으로 컴파일)
    return _SONNET_SOLO_PROMPT.replace("{confusion_pairs_section}", "")


def _derive(valid_codes: list[str]) -> list[str]:
    # match_patterns_solo 내부 파생식과 동일
    return sorted(_MANDATORY_REVIEW_TARGET_CODES & set(valid_codes))


class TestMandatoryReviewDerivation(unittest.TestCase):
    """1. 파생 로직: 교집합 정확성."""

    def test_target_codes_frozen(self):
        self.assertEqual(
            _MANDATORY_REVIEW_TARGET_CODES,
            {"4-3-b", "3-4-a", "3-4-b", "6-2-d"},
        )
        # 유령 패턴 7-2·7-5 미포함
        self.assertNotIn("7-2", _MANDATORY_REVIEW_TARGET_CODES)
        self.assertNotIn("7-5", _MANDATORY_REVIEW_TARGET_CODES)

    def test_partial_overlap(self):
        self.assertEqual(
            _derive(["4-3-b", "1-5-h", "6-2-d"]), ["4-3-b", "6-2-d"]
        )

    def test_full_overlap_sorted(self):
        self.assertEqual(
            _derive(["6-2-d", "4-3-b", "3-4-b", "3-4-a"]),
            ["3-4-a", "3-4-b", "4-3-b", "6-2-d"],
        )

    def test_no_overlap(self):
        self.assertEqual(_derive(["1-5-h", "6-2-c"]), [])
        self.assertEqual(_derive([]), [])


class TestMandatoryReviewBlock(unittest.TestCase):
    """2. 필수 검토 블록 존재 + 7-2·7-5 미포함."""

    HEADER = "## 사회적 약자·소수자 보도 필수 검토 (★ 표시와 무관)"

    def _block(self) -> str:
        text = _compiled_prompt()
        start = text.index(self.HEADER)
        end = text.index("\n## ", start + 1)  # 다음 ## 섹션까지
        return text[start:end]

    def test_block_exists(self):
        self.assertIn(self.HEADER, _compiled_prompt())

    def test_block_content(self):
        block = self._block()
        for expected in [
            "장애인, 이주민, 성소수자, 노인, 여성, 노동자",
            "집회·시위·파업·농성",
            "명시적 낙인 관용구·비하 어휘",
            "'강성 노조', '귀족 노조'",
            "→ 4-3-b",
            "→ 3-4-a, 3-4-b",
            "→ 6-2-d",
            "6-2-a/b/c 제목-본문 대조",
            "검토는 의무이되 선택은 아닙니다",
        ]:
            self.assertIn(expected, block)

    def test_block_excludes_ghost_patterns(self):
        block = self._block()
        self.assertNotIn("7-2", block)
        self.assertNotIn("7-5", block)

    def test_block_position(self):
        # ★ 후보 패턴 활용 직후, 길이별 가이드 이전
        text = _compiled_prompt()
        star_idx = text.index("## ★ 후보 패턴 활용")
        block_idx = text.index(self.HEADER)
        length_idx = text.index("## 기사 길이별 가이드")
        self.assertLess(star_idx, block_idx)
        self.assertLess(block_idx, length_idx)


class TestExample31(unittest.TestCase):
    """3. 예시 3-1 삽입."""

    def test_example_31_exists(self):
        text = _compiled_prompt()
        self.assertIn(
            "### 예시 3-1 — [TP] 4-3-b: 차별·혐오 표현 (프레이밍형 — 명시적 비하어 없음)",
            text,
        )
        self.assertIn("'볼모' 잡힌 출근길", text)
        self.assertIn("시민을 볼모로 잡는 독선", text)

    def test_example_31_between_3_and_4(self):
        text = _compiled_prompt()
        i3 = text.index("### 예시 3 —")
        i31 = text.index("### 예시 3-1 —")
        i4 = text.index("### 예시 4 —")
        self.assertLess(i3, i31)
        self.assertLess(i31, i4)


class TestExistingExamplesPreserved(unittest.TestCase):
    """4. 기존 예시 1·2·4~7 보존 + 순서 유지."""

    SIGNATURES = [
        ("### 예시 1 — [TP] 1-5-h: 통계 맥락 무시 (코로나 데이터)",
         "10만 명당 확진자 수가 80% 늘어"),
        ("### 예시 2 — [TP] 3-2-c + 6-2-c: 사례 일반화 + 제목 침소봉대",
         "2030 '접종 보이콧'"),
        ("### 예시 3 — [TP] 4-3-b: 차별·혐오 표현 ('눈먼 돈')",
         "'눈먼 돈' 청년 전세대출"),
        ("### 예시 4 — [TP] 1-4-d: 의견의 사실화 (한화 리스크)",
         "'한화 리스크' 진행형"),
        ("### 예시 5 — [TP] 6-2-c: 제목-본문 침소봉대 (해고자 일반화)",
         "공장 세우고 동료 때린"),
        ("### 예시 6 — [TN] 탐사보도: 양질의 보도",
         "목포 '옛 동명원' 피해자들의 증언"),
        ("### 예시 7 — [TN] 환경 탐사보도: 양질의 보도",
         "추적: 지옥이 된 바다"),
    ]

    def test_all_examples_present_in_order(self):
        text = _compiled_prompt()
        last_idx = -1
        for header, signature in self.SIGNATURES:
            self.assertIn(header, text)
            self.assertIn(signature, text)
            idx = text.index(header)
            self.assertGreater(idx, last_idx, f"순서 어긋남: {header}")
            last_idx = idx

    def test_structural_example_preserved(self):
        text = _compiled_prompt()
        self.assertIn("## 구조적 패턴 감지 예시", text)
        self.assertIn("### [structural] 3-1-b: 편향된 취재원 구성", text)


class TestDetectionCapRemoved(unittest.TestCase):
    """5. 기사 길이별 탐지 개수 상한 제거(2026-07-13) + 중복 금지 보존.

    구 TestLengthGuideUnchanged를 대체 — 길이별 숫자 상한은 제거가 확정
    계약이며, 동일 패턴 반복 금지 원칙은 반드시 살아 있어야 한다.
    """

    def test_numeric_caps_absent(self):
        text = _compiled_prompt()
        for stale in [
            "- 200자 미만: 최대 1~2개",
            "- 200~500자: 최대 2~3개",
            "- 500~2000자: 최대 3~4개",
            "- 2000자 이상: 최대 4~5개. 근거가 매우 명확한 경우에만.",
            "## 기사 길이별 가이드",
        ]:
            self.assertNotIn(stale, text)

    def test_no_cap_principle_present(self):
        text = _compiled_prompt()
        self.assertIn("탐지 개수에 임의의 상한을 두지 마세요", text)
        self.assertIn("독립적인 근거가 확인되는 패턴은 모두 기록", text)

    def test_duplicate_ban_preserved(self):
        self.assertIn("같은 패턴을 여러 번 선택하지 마세요", _compiled_prompt())


class TestForensicWiring(unittest.TestCase):
    """6. phase1_forensic에 mandatory_review_codes 실값 배선."""

    def test_payload_uses_pm_value(self):
        pm = PatternMatchResult(
            validated_pattern_codes=["4-3-b", "1-5-h"],
            mandatory_review_codes=["4-3-b"],
        )
        payload = pipeline._build_phase1_forensic(pm, "general", [])
        self.assertEqual(payload["mandatory_review_codes"], ["4-3-b"])

    def test_payload_empty_when_no_targets(self):
        pm = PatternMatchResult(validated_pattern_codes=["1-5-h"])
        payload = pipeline._build_phase1_forensic(pm, "general", [])
        self.assertEqual(payload["mandatory_review_codes"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
