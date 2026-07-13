"""Phase 1 탐지 상한 제거 + validator 분리(active strict / legacy 보존) 단위 테스트 (DB·API 불요).

대상:
  A. validate_runtime_pattern_codes — 활성 경로 전용 strict validator
     · 전달된 catalog만으로 검증 (DB URL·키 불요)
     · 정상 활성 leaf 통과 (id 변환 포함)
     · 부모 코드(1-1, 2-3, 3-1) / 미존재 / 카탈로그 외 코드 거부
     · 오염된 catalog 방어: 비활성 leaf row·메타 leaf row·비-leaf row는
       허용 맵에서 배제 (row 자체 재검증)
     · 중복·순서 계약 유지, 빈 detections → ([], [], [])
     · 거부 발생 경로 포함 어디서도 DB 조회 없음
  B. validate_pattern_codes — legacy DB 존재 여부 검증 의미 보존
     · 숫자형 3세그먼트 구코드(예: 1-1-1, 1-7-2)가 (모킹된) DB에 존재하면
       기존 계약대로 통과 — 현행 프로덕션 DB 존재 여부를 주장하지 않으며,
       "DB에 존재하면 통과"라는 함수 계약의 보존만 검증한다
     · DB 미존재 코드만 hallucinated로 거부
     · 런타임 카탈로그(_load_pattern_catalog)와 무결합
     · 3-인자 시그니처 유지 (pattern_matcher_legacy.py 위치 인자 호출 호환)
  C. _SONNET_SOLO_PROMPT
     · 길이별 숫자 상한·완화형 앵커 부재 + 상한 미설정 원칙 존재
     · 중복 정리 범위 명확화: 대체 후보만 하나로 정리, 서로 다른 문제는 각각 기록
     · 동일 패턴 반복 금지 정확히 1회 + 기존 원칙 보존

실행: backend/ 디렉터리에서  python3 -m unittest test_p1_cap_removal_validator -v
패턴 코드는 실제 데이터와 무관한 합성값(9-9-*, 8-8-*)을 우선 사용한다.
네트워크·DB 접근은 전부 모킹 — sb_url은 의도적으로 무효 호스트를 쓴다.
"""

import inspect
import re
import unittest
from unittest.mock import patch

from core import pattern_matcher
from core.pattern_matcher import (
    _SONNET_SOLO_PROMPT,
    HaikuDetection,
    validate_pattern_codes,
    validate_runtime_pattern_codes,
)


def _det(code: str) -> HaikuDetection:
    return HaikuDetection(
        pattern_code=code, matched_text="t", severity="low", reasoning="r"
    )


# 런타임 카탈로그 정상 형태 재현: _load_pattern_catalog 반환은 활성 v3 leaf만 담는다.
_CATALOG = [
    {"id": 901, "code": "9-9-a", "name": "합성 A",
     "is_active": True, "is_meta_pattern": False},
    {"id": 902, "code": "9-9-b", "name": "합성 B",
     "is_active": True, "is_meta_pattern": False},
]

# 오염된 catalog row들 — strict validator는 row 자체를 재검증해 전부 배제해야 한다.
_POLLUTED_ROWS = [
    {"id": 903, "code": "9-9-c", "name": "합성 비활성 leaf",
     "is_active": False, "is_meta_pattern": False},
    {"id": 904, "code": "9-9-d", "name": "합성 메타 leaf",
     "is_active": True, "is_meta_pattern": True},
    {"id": 905, "code": "9-9", "name": "합성 부모 (비-leaf)",
     "is_active": True, "is_meta_pattern": False},
]

_SB = ("http://sb.invalid", "dummy-key")  # 실수로 네트워크를 타면 즉시 실패하도록


class _FakeResp:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return self._rows


class TestRuntimeValidatorPass(unittest.TestCase):
    """A-1. 정상 활성 v3 leaf 통과."""

    def test_active_leaf_passes(self):
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9-a"), _det("9-9-b")], _CATALOG
        )
        self.assertEqual(ids, [901, 902])
        self.assertEqual(codes, ["9-9-a", "9-9-b"])
        self.assertEqual(rejected, [])

    def test_return_contract_three_lists(self):
        result = validate_runtime_pattern_codes([_det("9-9-a")], _CATALOG)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for part in result:
            self.assertIsInstance(part, list)


class TestRuntimeValidatorReject(unittest.TestCase):
    """A-2. 부모·미존재·카탈로그 외 코드 거부 + 오염 catalog 방어."""

    def test_parent_codes_rejected(self):
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("1-1"), _det("2-3"), _det("3-1")], _CATALOG
        )
        self.assertEqual((ids, codes), ([], []))
        self.assertEqual(rejected, ["1-1", "2-3", "3-1"])

    def test_nonexistent_code_rejected(self):
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9-z")], _CATALOG
        )
        self.assertEqual((ids, codes), ([], []))
        self.assertEqual(rejected, ["9-9-z"])

    def test_leaf_shaped_but_not_in_catalog_rejected(self):
        # DB에 존재하더라도 런타임 카탈로그에 없으면 거부
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("8-8-a")], _CATALOG
        )
        self.assertEqual((ids, codes), ([], []))
        self.assertEqual(rejected, ["8-8-a"])

    def test_polluted_inactive_leaf_row_rejected(self):
        # leaf 형태지만 is_active=False인 row가 catalog에 섞여 들어와도 거부
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9-c")], _CATALOG + _POLLUTED_ROWS
        )
        self.assertEqual((ids, codes), ([], []))
        self.assertEqual(rejected, ["9-9-c"])

    def test_polluted_meta_leaf_row_rejected(self):
        # leaf 형태지만 is_meta_pattern=True인 row가 섞여 들어와도 거부
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9-d")], _CATALOG + _POLLUTED_ROWS
        )
        self.assertEqual((ids, codes), ([], []))
        self.assertEqual(rejected, ["9-9-d"])

    def test_polluted_non_leaf_row_rejected(self):
        # 활성·비메타라도 code가 leaf 형식이 아닌 row(부모 등)는 거부
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9")], _CATALOG + _POLLUTED_ROWS
        )
        self.assertEqual((ids, codes), ([], []))
        self.assertEqual(rejected, ["9-9"])

    def test_clean_codes_still_pass_with_polluted_catalog(self):
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9-a"), _det("9-9-c"), _det("9-9-d"), _det("9-9")],
            _CATALOG + _POLLUTED_ROWS,
        )
        self.assertEqual(ids, [901])
        self.assertEqual(codes, ["9-9-a"])
        self.assertEqual(rejected, ["9-9-c", "9-9-d", "9-9"])


class TestRuntimeValidatorContract(unittest.TestCase):
    """A-3. 반환 계약 유지: 중복·순서·빈 입력."""

    def test_duplicate_valid_codes_preserved(self):
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9-a"), _det("9-9-a")], _CATALOG
        )
        self.assertEqual(ids, [901, 901])
        self.assertEqual(codes, ["9-9-a", "9-9-a"])
        self.assertEqual(rejected, [])

    def test_duplicate_rejected_codes_preserved(self):
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("1-1"), _det("1-1")], _CATALOG
        )
        self.assertEqual((ids, codes), ([], []))
        self.assertEqual(rejected, ["1-1", "1-1"])

    def test_mixed_input_order_preserved(self):
        ids, codes, rejected = validate_runtime_pattern_codes(
            [_det("9-9-b"), _det("1-1"), _det("9-9-a")], _CATALOG
        )
        self.assertEqual(ids, [902, 901])
        self.assertEqual(codes, ["9-9-b", "9-9-a"])
        self.assertEqual(rejected, ["1-1"])

    def test_empty_detections_early_return(self):
        self.assertEqual(
            validate_runtime_pattern_codes([], _CATALOG), ([], [], [])
        )


class TestRuntimeValidatorNoDb(unittest.TestCase):
    """A-4. 활성 경로 DB 조회 0회 — 거부 발생 경로 포함."""

    def test_no_db_access_even_on_rejection(self):
        with patch.object(
            pattern_matcher.httpx, "get",
            side_effect=AssertionError("활성 validator가 DB를 조회했다"),
        ), patch.object(
            pattern_matcher, "_load_pattern_catalog",
            side_effect=AssertionError("활성 validator가 카탈로그를 로드했다"),
        ):
            ids, codes, rejected = validate_runtime_pattern_codes(
                [_det("9-9-a"), _det("1-1"), _det("9-9-z")], _CATALOG
            )
        self.assertEqual(ids, [901])
        self.assertEqual(codes, ["9-9-a"])
        self.assertEqual(rejected, ["1-1", "9-9-z"])


class TestLegacyValidatorPreserved(unittest.TestCase):
    """B. legacy validate_pattern_codes — DB 존재 여부 검증 의미 보존."""

    def test_numeric_legacy_codes_pass_if_in_db(self):
        # legacy 숫자형 3세그먼트 구코드 — strict 기준이면 전부 거부될 형식.
        # 현행 프로덕션 DB에 이 코드가 실존한다는 주장이 아니라, 모킹된 DB를
        # 기준으로 "DB에 존재하면 통과"라는 기존 함수 계약의 보존을 검증한다.
        rows = [{"id": 11, "code": "1-1-1"}, {"id": 72, "code": "1-7-2"}]
        with patch.object(
            pattern_matcher.httpx, "get", return_value=_FakeResp(rows)
        ):
            ids, codes, halluc = validate_pattern_codes(
                [_det("1-1-1"), _det("1-7-2")], *_SB
            )
        self.assertEqual(ids, [11, 72])
        self.assertEqual(codes, ["1-1-1", "1-7-2"])
        self.assertEqual(halluc, [])

    def test_db_missing_code_hallucinated(self):
        rows = [{"id": 11, "code": "1-1-1"}]
        with patch.object(
            pattern_matcher.httpx, "get", return_value=_FakeResp(rows)
        ):
            ids, codes, halluc = validate_pattern_codes(
                [_det("1-1-1"), _det("9-9-z")], *_SB
            )
        self.assertEqual(ids, [11])
        self.assertEqual(codes, ["1-1-1"])
        self.assertEqual(halluc, ["9-9-z"])

    def test_no_runtime_catalog_coupling(self):
        # legacy 경로는 런타임 카탈로그와 무관해야 한다 (strict 변경 영향 차단)
        rows = [{"id": 11, "code": "1-1-1"}]
        with patch.object(
            pattern_matcher, "_load_pattern_catalog",
            side_effect=AssertionError("legacy validator가 카탈로그를 로드했다"),
        ), patch.object(
            pattern_matcher.httpx, "get", return_value=_FakeResp(rows)
        ):
            out = validate_pattern_codes([_det("1-1-1")], *_SB)
        self.assertEqual(out, ([11], ["1-1-1"], []))

    def test_empty_detections_early_return_without_network(self):
        # 빈 입력은 네트워크 없이 즉시 반환 (모킹 불필요)
        self.assertEqual(validate_pattern_codes([], *_SB), ([], [], []))

    def test_signature_three_positional_params(self):
        # pattern_matcher_legacy.py의 위치 인자 3개 호출 호환
        params = list(inspect.signature(validate_pattern_codes).parameters)
        self.assertEqual(params, ["detections", "sb_url", "sb_key"])


def _compiled_prompt() -> str:
    # _build_sonnet_solo_prompt와 동일한 치환 (DB 없이 빈 섹션으로 컴파일)
    return _SONNET_SOLO_PROMPT.replace("{confusion_pairs_section}", "")


class TestPromptCapRemoval(unittest.TestCase):
    """C. Phase 1 프롬프트 — 상한 제거 + 중복 정리 범위 명확화 + 원칙 보존."""

    def test_length_based_numeric_caps_absent(self):
        text = _compiled_prompt()
        for stale in [
            "200자 미만: 최대 1~2개",
            "200~500자: 최대 2~3개",
            "500~2000자: 최대 3~4개",
            "2000자 이상: 최대 4~5개",
            "## 기사 길이별 가이드",
        ]:
            self.assertNotIn(stale, text)
        # 어떤 표현이든 "최대 N(~M)개"류 숫자 상한 앵커 부재
        self.assertIsNone(re.search(r"최대\s*\d+\s*[~∼]?\s*\d*\s*개", text))

    def test_no_softened_count_anchors(self):
        text = _compiled_prompt()
        self.assertIsNone(
            re.search(r"(통상|대체로|평균|보통)\s*\d+\s*[~∼]?\s*\d*\s*개", text)
        )
        self.assertNotIn("가능하면 적은 수", text)
        self.assertNotIn("기사 길이에 비례", text)

    def test_no_cap_principle_present(self):
        text = _compiled_prompt()
        self.assertIn("탐지 개수에 임의의 상한을 두지 마세요", text)
        self.assertIn("독립적인 근거가 확인되는 패턴은 모두 기록", text)

    def test_dedup_scope_clarified(self):
        # 정리 대상은 '정의상 중복되는 대체 후보'로 한정하고,
        # 서로 다른 문제를 설명하는 패턴은 각각 기록한다는 취지가 명시돼야 한다
        text = _compiled_prompt()
        self.assertIn("정의상 중복되는 대체 후보 패턴은 가장 정확한 leaf 하나로 정리", text)
        self.assertIn("서로 다른 문제를 설명하는 패턴은 각각 기록", text)
        # 서로 다른 문제까지 하나로 축소할 수 있던 구 문구는 제거
        self.assertNotIn("같은 현상을 가리키는 유사 패턴", text)

    def test_same_pattern_repeat_ban_preserved_exactly_once(self):
        text = _compiled_prompt()
        self.assertEqual(text.count("같은 패턴을 여러 번 선택하지 마세요"), 1)

    def test_existing_principles_preserved(self):
        text = _compiled_prompt()
        # 실제 근거 원칙
        self.assertIn("**실제로 확인되는** 문제만 선택하세요", text)
        # 유사 패턴 중 정확한 쪽 선택 (중복 금지와는 별개 원칙)
        self.assertIn("유사 패턴 중 더 정확한 쪽을 선택하세요", text)
        # 빈 detections 허용
        self.assertIn("detections를 빈 배열 []로 두세요", text)
        # v3 leaf-only 출력 + 부모 코드 금지
        self.assertIn("v3 leaf 코드만 사용하라", text)
        self.assertIn("부모 코드(예: 1-1, 3-1) 또는 카탈로그에 없는 코드는 출력하지 마라", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
