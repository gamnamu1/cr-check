"""Wave 1.1 · T0 단위 테스트 (DB·API 불요).

대상:
  ① phase1_forensic payload 10키 존재 + 타입 일치
  ② 탐지 0건 시나리오에서도 article_context 계산 + payload 조립
  ③ _parse_solo_response의 fallback_used: 1차 성공 False / 2차 경로 True
  ④ 포렌식 조립 실패가 파이프라인 결과를 막지 않음 (예외 격리)

실행: backend/ 디렉터리에서  python3 -m unittest test_t0_forensic -v
패턴 코드는 실제 데이터와 무관한 합성값(9-9-*)만 사용한다.
"""

import unittest
from unittest.mock import patch

from core import pipeline
from core.pattern_matcher import (
    PatternMatchResult,
    VectorCandidate,
    HaikuDetection,
    SuspectResult,
    _parse_solo_response,
)


_FORENSIC_KEYS = {
    "vector_candidates",
    "starred_codes",
    "mandatory_review_codes",
    "validated_codes",
    "hallucinated_codes",
    "unmatched_vector_candidates",
    "patterns_without_ethics",
    "article_context",
    "fallback_used",
    "phase1_model",
}


def _make_pm(
    detections=None,
    validated_ids=None,
    validated_codes=None,
    candidates=None,
    starred=None,
    fallback=False,
):
    return PatternMatchResult(
        vector_candidates=candidates or [],
        haiku_detections=detections or [],
        validated_pattern_ids=validated_ids or [],
        validated_pattern_codes=validated_codes or [],
        hallucinated_codes=["9-9-x"],
        unmatched_vector_candidates=["9-8"],
        suspect_result=SuspectResult(overall_assessment="테스트 판단"),
        parse_fallback_used=fallback,
        starred_codes=starred or [],
    )


class TestForensicPayloadSchema(unittest.TestCase):
    """① 10키 존재 + 타입 일치."""

    def test_ten_keys_and_types(self):
        pm = _make_pm(
            detections=[
                HaikuDetection("9-9-a", "발췌", "high", "근거"),
            ],
            validated_ids=[999],
            validated_codes=["9-9-a"],
            candidates=[VectorCandidate(999, "9-9-a", "합성 패턴", 0.31415926)],
            starred=["9-9-a"],
            fallback=True,
        )
        payload = pipeline._build_phase1_forensic(pm, "general", ["9-9-a"])

        self.assertEqual(set(payload.keys()), _FORENSIC_KEYS)
        self.assertIsInstance(payload["vector_candidates"], list)
        vc = payload["vector_candidates"][0]
        self.assertEqual(set(vc.keys()), {"code", "name", "similarity"})
        self.assertEqual(vc["code"], "9-9-a")
        # similarity 소수 4자리 반올림
        self.assertEqual(vc["similarity"], 0.3142)
        self.assertIsInstance(payload["starred_codes"], list)
        self.assertEqual(payload["starred_codes"], ["9-9-a"])
        # T2 배포 전까지 빈 배열 고정
        self.assertEqual(payload["mandatory_review_codes"], [])
        self.assertEqual(payload["validated_codes"], ["9-9-a"])
        self.assertEqual(payload["hallucinated_codes"], ["9-9-x"])
        self.assertEqual(payload["unmatched_vector_candidates"], ["9-8"])
        self.assertEqual(payload["patterns_without_ethics"], ["9-9-a"])
        self.assertIsInstance(payload["article_context"], str)
        self.assertIsInstance(payload["fallback_used"], bool)
        self.assertTrue(payload["fallback_used"])
        # 상수 참조 (하드코딩 이중화 금지)
        from core import pattern_matcher as pm_mod
        self.assertEqual(payload["phase1_model"], pm_mod.SONNET_MODEL)


class TestZeroDetectionForensic(unittest.TestCase):
    """② 탐지 0건에서도 article_context 계산 + payload 조립."""

    def test_zero_detection_payload_assembled(self):
        pm = _make_pm()  # 탐지 0건, 후보 0건
        with patch.object(pipeline, "match_patterns_solo", return_value=pm):
            result = pipeline.analyze_article(
                "재판부 판결 관련 기사 본문. " * 10, run_sonnet=True,
            )
        self.assertIsNotNone(result.phase1_forensic)
        payload = result.phase1_forensic
        self.assertEqual(set(payload.keys()), _FORENSIC_KEYS)
        # crime_keywords('재판부 판결') 기반 context가 계산되어 적재됨
        self.assertEqual(payload["article_context"], "crime")
        self.assertEqual(payload["validated_codes"], [])
        self.assertEqual(payload["patterns_without_ethics"], [])
        # TN 메시지 경로 동작 불변
        self.assertIn("발견되지 않았습니다", result.report_result.reports["comprehensive"])

    def test_run_sonnet_false_uses_validated_as_without_ethics(self):
        pm = _make_pm(
            detections=[HaikuDetection("9-9-a", "발췌", "high", "근거")],
            validated_ids=[999],
            validated_codes=["9-9-a"],
        )
        with patch.object(pipeline, "match_patterns_solo", return_value=pm):
            result = pipeline.analyze_article("일반 기사 본문", run_sonnet=False)
        payload = result.phase1_forensic
        self.assertIsNotNone(payload)
        # 조건 미충족(run_sonnet=False) 시 validated 전체로 일관 처리
        self.assertEqual(payload["patterns_without_ethics"], ["9-9-a"])
        self.assertEqual(payload["article_context"], "general")


class TestParseFallbackFlag(unittest.TestCase):
    """③ fallback_used: 1차 성공 False / 2차 경로 True."""

    def test_first_pass_success_false(self):
        raw = (
            '{"overall_assessment": "정상", "detections": '
            '[{"pattern_code": "9-9-a", "matched_text": "t", '
            '"severity": "high", "reasoning": "r"}]}'
        )
        assessment, detections, fallback = _parse_solo_response(raw)
        self.assertEqual(assessment, "정상")
        self.assertEqual(len(detections), 1)
        self.assertFalse(fallback)

    def test_second_pass_recovery_true(self):
        # trailing comma → 1차 실패, 2차 _fix_llm_json 복구
        raw = (
            '{"overall_assessment": "복구", "detections": '
            '[{"pattern_code": "9-9-a", "matched_text": "t", '
            '"severity": "high", "reasoning": "r"},]}'
        )
        assessment, detections, fallback = _parse_solo_response(raw)
        self.assertEqual(assessment, "복구")
        self.assertEqual(len(detections), 1)
        self.assertTrue(fallback)

    def test_no_json_object_true(self):
        assessment, detections, fallback = _parse_solo_response("JSON 없음")
        self.assertEqual(detections, [])
        self.assertTrue(fallback)


class TestForensicExceptionIsolation(unittest.TestCase):
    """④ 포렌식 조립 실패가 파이프라인 결과를 막지 않음."""

    def test_forensic_failure_does_not_break_pipeline(self):
        pm = _make_pm()
        with patch.object(pipeline, "match_patterns_solo", return_value=pm), \
             patch.object(
                 pipeline, "_build_phase1_forensic",
                 side_effect=RuntimeError("조립 실패 시뮬레이션"),
             ):
            result = pipeline.analyze_article("일반 기사 본문", run_sonnet=True)
        # 파이프라인 결과는 정상 반환, 포렌식만 None
        self.assertIsNone(result.phase1_forensic)
        self.assertIn("발견되지 않았습니다", result.report_result.reports["comprehensive"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
