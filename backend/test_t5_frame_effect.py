"""Wave 1.1 · T5 단위 테스트 (DB·API 불요, call_sonnet 모킹).

대상:
  1. _build_frame_effect_block 발동: 4개 질문 문구 + 헤더 코드명
  2. target 밖 코드 → 빈 문자열
  3. 빈 집합 → 빈 문자열
  4. generate_report 배선: frame_pattern_block 인자 캡처 (실 API 호출 없음)
  5. _SONNET_SYSTEM_PROMPT 무변경 (프레임 블록 미주입 + 분량·구조 문구 보존)
  6. 유령 패턴 7-2·7-5 미접촉

실행: backend/ 디렉터리에서  python3 -m unittest test_t5_frame_effect -v
"""

import unittest
from unittest.mock import patch

from core import report_generator
from core.report_generator import (
    _SONNET_SYSTEM_PROMPT,
    _build_frame_effect_block,
    generate_report,
)
from core.pattern_matcher import _MANDATORY_REVIEW_TARGET_CODES

_QUESTIONS = [
    "① 누구의 목소리가 중심화되고 누구의 목소리가 배제되는가",
    "② 누가 '시민·정상·공공질서'의 바깥으로 밀려나는가",
    "③ 제목과 인용 배치가 어떤 낙인 효과를 만드는가",
    "④ 어떤 대안 제목·추가 취재 질문이 가능했는가",
]

_HEADER_PREFIX = "## 프레임 효과 서술 지시"

_VALID_SONNET_RAW = (
    '{"reports": {"comprehensive": "a", "journalist": "b", "student": "c"},'
    ' "article_analysis": {}}'
)


class TestFrameEffectBlock(unittest.TestCase):
    """1~3. 블록 생성 로직."""

    def test_triggered_single_code(self):
        block = _build_frame_effect_block({"4-3-b"})
        self.assertTrue(block.startswith(_HEADER_PREFIX))
        self.assertIn("4-3-b", block.splitlines()[0])
        for q in _QUESTIONS:
            self.assertIn(q, block)
        self.assertIn("최소 두 가지", block)
        self.assertIn("「관련 윤리규범」 섹션에 제공된 것만", block)

    def test_triggered_header_sorted_targets_only(self):
        block = _build_frame_effect_block({"6-2-d", "4-3-b", "1-5-h"})
        header = block.splitlines()[0]
        self.assertIn("4-3-b, 6-2-d", header)  # 정렬 + target 교집합만
        self.assertNotIn("1-5-h", header)

    def test_non_target_codes_empty(self):
        self.assertEqual(_build_frame_effect_block({"1-1-b", "5-1-b"}), "")

    def test_empty_set_empty(self):
        self.assertEqual(_build_frame_effect_block(set()), "")

    def test_uses_shared_target_constant(self):
        # 재정의 없이 T2 상수 재사용 — 전체 target 발동 시 헤더에 4개 전부
        block = _build_frame_effect_block(set(_MANDATORY_REVIEW_TARGET_CODES))
        header = block.splitlines()[0]
        for code in _MANDATORY_REVIEW_TARGET_CODES:
            self.assertIn(code, header)

    def test_no_ghost_patterns(self):
        block = _build_frame_effect_block(set(_MANDATORY_REVIEW_TARGET_CODES))
        self.assertNotIn("7-2", block)
        self.assertNotIn("7-5", block)


class TestGenerateReportWiring(unittest.TestCase):
    """4. generate_report → call_sonnet 인자 배선 (모킹)."""

    def _run(self, detections):
        captured = {}

        def fake_call_sonnet(*args, **kwargs):
            captured.update(kwargs)
            return _VALID_SONNET_RAW, 10, 20

        with patch.object(report_generator, "_get_supabase_config",
                          return_value=("http://localhost", "key")), \
             patch.object(report_generator, "fetch_ethics_for_patterns",
                          return_value=[]), \
             patch.object(report_generator, "call_sonnet",
                          side_effect=fake_call_sonnet):
            result = generate_report(
                article_text="본문",
                pattern_ids=[1],
                detections=detections,
            )
        return captured, result

    def test_target_detection_passes_block(self):
        captured, result = self._run(
            [{"pattern_code": "4-3-b"}, {"pattern_code": "1-5-h"}]
        )
        block = captured.get("frame_pattern_block")
        self.assertTrue(block)
        self.assertIn("4-3-b", block.splitlines()[0])
        self.assertEqual(result.reports["comprehensive"], "a")

    def test_non_target_detection_empty_block(self):
        captured, _ = self._run([{"pattern_code": "1-5-h"}])
        self.assertEqual(captured.get("frame_pattern_block"), "")

    def test_missing_pattern_code_key_safe(self):
        captured, _ = self._run([{"description": "코드 없음"}])
        self.assertEqual(captured.get("frame_pattern_block"), "")


class TestSystemPromptUntouched(unittest.TestCase):
    """5. 시스템 프롬프트 무변경 (캐싱 보존)."""

    def test_frame_block_not_in_system_prompt(self):
        self.assertNotIn(_HEADER_PREFIX, _SONNET_SYSTEM_PROMPT)
        for q in _QUESTIONS:
            self.assertNotIn(q, _SONNET_SYSTEM_PROMPT)

    def test_length_structure_section_intact(self):
        self.assertIn("## 분량과 구조", _SONNET_SYSTEM_PROMPT)
        self.assertIn("comprehensive(시민용/종합): 900~1,300자", _SONNET_SYSTEM_PROMPT)
        self.assertIn("journalist(기자용): 900~1,300자", _SONNET_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
