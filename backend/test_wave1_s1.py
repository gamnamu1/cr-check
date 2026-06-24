"""Wave 1 · S1 단위 테스트 (DB·API 불요).

대상:
  - 1-1: Chunk fallback 생성이 TypeError 없이 단일 청크를 만든다.
  - 1-6: _build_haiku_dicts가 pattern_catalog_meta를 방어적으로 조회해
         pattern_name·report_framing 2필드를 전달한다 (메타 있음/없음/KeyError 미발생).

실행: backend/ 디렉터리에서  python3 -m unittest test_wave1_s1 -v
패턴 코드는 실제 데이터와 무관한 합성값(9-9-*)만 사용한다.
"""

import unittest

from core.chunker import Chunk
from core.pipeline import _build_haiku_dicts
from core.pattern_matcher import PatternMatchResult, HaikuDetection


class TestChunkFallback(unittest.TestCase):
    """1-1: pipeline 청킹 실패 시 fallback 생성 검증."""

    def test_fallback_construction_no_typeerror(self):
        # pipeline.py fallback과 동일한 인자 형태
        text = "기사 전문 텍스트"
        chunks = [Chunk(text=text, start_idx=0, end_idx=len(text))]
        self.assertEqual(len(chunks), 1)
        c = chunks[0]
        self.assertEqual(c.text, text)
        self.assertEqual(c.start_idx, 0)
        self.assertEqual(c.end_idx, len(text))
        # length는 @property → 텍스트 길이와 일치
        self.assertEqual(c.length, len(text))

    def test_old_invalid_kwargs_would_raise(self):
        # 수정 전 버그(start/end/length kwarg)는 TypeError를 일으킨다 — 회귀 가드
        with self.assertRaises(TypeError):
            Chunk(text="x", start=0, end=1, length=1)  # type: ignore[call-arg]

    def test_length_is_readonly_property(self):
        c = Chunk(text="abcd", start_idx=0, end_idx=4)
        with self.assertRaises(AttributeError):
            c.length = 99  # type: ignore[misc]


def _make_pm(detections, validated_codes, catalog_meta):
    return PatternMatchResult(
        haiku_detections=detections,
        validated_pattern_codes=validated_codes,
        pattern_catalog_meta=catalog_meta,
    )


_BASE_KEYS = {"pattern_code", "matched_text", "severity", "reasoning"}


class TestBuildHaikuDicts(unittest.TestCase):
    """1-6 + S1 보정: include_report_meta 플래그 동작 검증."""

    # ── 기본값 False: 기존 4필드만 (Phase 2 입력 불변 정적 증명) ──
    def test_default_false_only_four_keys(self):
        d = HaikuDetection(pattern_code="9-9-a", matched_text="m", severity="high", reasoning="r")
        pm = _make_pm(
            [d],
            ["9-9-a"],
            {"9-9-a": {"name": "합성 패턴명", "report_framing": "서술 방향 텍스트"}},
        )
        # 인자 생략(기본값) / 명시 False 둘 다 4필드만
        for out in (_build_haiku_dicts(pm), _build_haiku_dicts(pm, include_report_meta=False)):
            self.assertEqual(len(out), 1)
            self.assertEqual(set(out[0].keys()), _BASE_KEYS)
            self.assertNotIn("pattern_name", out[0])
            self.assertNotIn("report_framing", out[0])
        # 기존 4필드 값 보존
        row = _build_haiku_dicts(pm)[0]
        self.assertEqual(row["pattern_code"], "9-9-a")
        self.assertEqual(row["matched_text"], "m")
        self.assertEqual(row["severity"], "high")
        self.assertEqual(row["reasoning"], "r")

    # ── True 경로: 6필드 부착 ──
    def test_a_meta_present(self):
        d = HaikuDetection(pattern_code="9-9-a", matched_text="m", severity="high", reasoning="r")
        pm = _make_pm(
            [d],
            ["9-9-a"],
            {"9-9-a": {"name": "합성 패턴명", "report_framing": "서술 방향 텍스트"}},
        )
        out = _build_haiku_dicts(pm, include_report_meta=True)
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertEqual(set(row.keys()), _BASE_KEYS | {"pattern_name", "report_framing"})
        self.assertEqual(row["pattern_name"], "합성 패턴명")
        self.assertEqual(row["report_framing"], "서술 방향 텍스트")

    def test_b_meta_absent_fallback(self):
        d = HaikuDetection(pattern_code="9-9-b", matched_text="m2", severity="low", reasoning="r2")
        pm = _make_pm([d], ["9-9-b"], {})  # 메타 맵 비어 있음
        out = _build_haiku_dicts(pm, include_report_meta=True)
        self.assertEqual(len(out), 1)
        row = out[0]
        # fallback: name=pattern_code, report_framing=""
        self.assertEqual(row["pattern_name"], "9-9-b")
        self.assertEqual(row["report_framing"], "")

    # ── 부분 키 메타: key-level fallback, KeyError 미발생 ──
    def test_partial_meta_name_only(self):
        d = HaikuDetection(pattern_code="1-1-a", matched_text="m", severity="high", reasoning="r")
        pm = _make_pm([d], ["1-1-a"], {"1-1-a": {"name": "X"}})  # report_framing 키 없음
        try:
            out = _build_haiku_dicts(pm, include_report_meta=True)
        except KeyError as e:
            self.fail(f"KeyError 발생: {e}")
        self.assertEqual(out[0]["pattern_name"], "X")
        self.assertEqual(out[0]["report_framing"], "")

    def test_partial_meta_framing_only(self):
        d = HaikuDetection(pattern_code="1-1-a", matched_text="m", severity="high", reasoning="r")
        pm = _make_pm([d], ["1-1-a"], {"1-1-a": {"report_framing": "Y"}})  # name 키 없음
        try:
            out = _build_haiku_dicts(pm, include_report_meta=True)
        except KeyError as e:
            self.fail(f"KeyError 발생: {e}")
        self.assertEqual(out[0]["pattern_name"], "1-1-a")  # name 없으면 코드로 fallback
        self.assertEqual(out[0]["report_framing"], "Y")

    def test_c_no_keyerror_mixed_and_filtered(self):
        d_present = HaikuDetection(pattern_code="9-9-a", matched_text="m", severity="high", reasoning="r")
        d_absent = HaikuDetection(pattern_code="9-9-b", matched_text="m", severity="medium", reasoning="r")
        d_unvalidated = HaikuDetection(pattern_code="9-9-z", matched_text="m", severity="low", reasoning="r")
        pm = _make_pm(
            [d_present, d_absent, d_unvalidated],
            ["9-9-a", "9-9-b"],  # 9-9-z는 미검증 → 제외되어야
            {"9-9-a": {"name": "있음", "report_framing": "프레이밍"}},
        )
        try:
            out = _build_haiku_dicts(pm, include_report_meta=True)
        except KeyError as e:
            self.fail(f"KeyError 발생: {e}")
        # 검증 통과 코드 2건만 (미검증 9-9-z 제외)
        self.assertEqual([r["pattern_code"] for r in out], ["9-9-a", "9-9-b"])
        # 없는 코드는 fallback
        self.assertEqual(out[1]["pattern_name"], "9-9-b")
        self.assertEqual(out[1]["report_framing"], "")

    def test_d_empty_detections(self):
        pm = _make_pm([], [], {})
        self.assertEqual(_build_haiku_dicts(pm), [])
        self.assertEqual(_build_haiku_dicts(pm, include_report_meta=True), [])


if __name__ == "__main__":
    unittest.main()
