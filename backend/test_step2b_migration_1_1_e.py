"""STEP 2-B · 1-1-e → PCP-3-1 매핑 마이그레이션 SQL 정적 검증 (DB·API 불요).

대상: supabase/migrations/20260714042904_step2b_1_1_e_pcp_3_1_mapping.sql

검증 항목(승인 지침 §11):
  1. 1-1-e와 PCP-3-1이 정확히 포함
  2. relation_type = violates
  3. strength = strong
  4. PCP-3-4 INSERT 없음
  5. JEC-1 direct INSERT 없음
  6. 6-6-c/d UPDATE·INSERT 없음
  7. 기존 PCP-3-5 관계를 삭제·갱신하는 SQL 없음
  8. rollback이 신규 PCP-3-1 관계만 대상
  9. 중복 적용 방지 장치(NOT EXISTS) 존재
 10. 대상 pattern·ethics code 존재성 검증(DO 블록) 존재

주의: 이 테스트는 SQL 텍스트의 정적 계약만 검증한다. 실제 DB 적용 결과는
기획자가 SQL Editor에서 검증 SQL로 확인한다 (로컬 Supabase 미가용 환경).

실행: backend/ 디렉터리에서  python3 -m unittest test_step2b_migration_1_1_e -v
"""

import re
import unittest
from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "supabase" / "migrations"
    / "20260714042904_step2b_1_1_e_pcp_3_1_mapping.sql"
)


def _sql() -> str:
    return _MIGRATION.read_text(encoding="utf-8")


def _executable_sql() -> str:
    """주석(-- 라인)을 제거한 실행 대상 SQL만 남긴다."""
    lines = [
        ln for ln in _sql().splitlines()
        if not ln.lstrip().startswith("--")
    ]
    return "\n".join(lines)


class TestTargetRelation(unittest.TestCase):
    """1~3. 승인된 관계 1건의 정확성."""

    def test_file_exists(self):
        self.assertTrue(_MIGRATION.is_file(), _MIGRATION)

    def test_codes_present(self):
        body = _executable_sql()
        self.assertIn("'1-1-e'", body)
        self.assertIn("'PCP-3-1'", body)

    def test_relation_type_violates(self):
        self.assertIn("'violates'", _executable_sql())

    def test_strength_strong(self):
        self.assertIn("'strong'", _executable_sql())

    def test_single_insert_statement(self):
        body = _executable_sql()
        self.assertEqual(
            len(re.findall(r"INSERT\s+INTO", body, re.IGNORECASE)), 1
        )

    def test_reasoning_core_elements(self):
        # 승인 지침: 취재원 주장 사실화 / 사실·의견 구분 / 직접 대응 / 유추 아님
        body = _sql()
        for needle in [
            "취재원의 주장·의견·전망·평가",
            "사실과 의견을 명확히 구분",
            "직접 대응",
            "유추가 아니",
        ]:
            self.assertIn(needle, body)


class TestScopeExclusions(unittest.TestCase):
    """4~7. 승인 범위 밖 변경 부재."""

    def test_no_pcp_3_4(self):
        self.assertNotIn("PCP-3-4", _executable_sql())

    def test_no_jec_1_direct(self):
        self.assertNotIn("JEC-1", _executable_sql())

    def test_no_6_6_c_d(self):
        body = _executable_sql()
        self.assertNotIn("6-6-c", body)
        self.assertNotIn("6-6-d", body)
        self.assertNotIn("JEC-8", body)
        self.assertNotIn("report_framing", body)

    def test_no_update_or_uncommented_delete(self):
        body = _executable_sql()
        self.assertNotRegex(body, re.compile(r"\bUPDATE\b", re.IGNORECASE))
        # DELETE는 주석 처리된 rollback에만 존재해야 한다.
        self.assertNotRegex(body, re.compile(r"\bDELETE\b", re.IGNORECASE))

    def test_pcp_3_5_untouched(self):
        # PCP-3-5는 실행 SQL에 등장하지 않아야 한다.
        self.assertNotIn("PCP-3-5", _executable_sql())
        # rollback DELETE 문 자체에도 없음 ("건드리지 않는다" 보호 주석은 허용)
        rollback = _sql().split("[ROLLBACK]")[1]
        delete_stmt = rollback[rollback.index("DELETE FROM"):]
        self.assertNotIn("PCP-3-5", delete_stmt)


class TestRollback(unittest.TestCase):
    """8. rollback이 신규 관계만 대상."""

    def _rollback(self) -> str:
        return _sql().split("[ROLLBACK]")[1]

    def test_rollback_present_and_scoped(self):
        rb = self._rollback()
        self.assertIn("DELETE FROM public.pattern_ethics_relations", rb)
        self.assertIn("code = '1-1-e'", rb)
        self.assertIn("code = 'PCP-3-1'", rb)
        self.assertIn("relation_type = 'violates'", rb)
        self.assertIn("strength = 'strong'", rb)

    def test_rollback_single_delete(self):
        self.assertEqual(len(re.findall(r"DELETE\s+FROM", self._rollback())), 1)


class TestSafetyGuards(unittest.TestCase):
    """9~10. 멱등성 가드 + 존재성 검증."""

    def test_not_exists_guard(self):
        self.assertRegex(
            _executable_sql(), re.compile(r"NOT\s+EXISTS", re.IGNORECASE)
        )

    def test_do_block_existence_checks(self):
        body = _executable_sql()
        self.assertRegex(body, re.compile(r"DO\s+\$\$"))
        self.assertIn("RAISE EXCEPTION", body)
        # pattern·ethics 각각의 유일성(=1행) 검증
        self.assertRegex(body, re.compile(r"n_pattern\s*<>\s*1"))
        self.assertRegex(body, re.compile(r"n_ethics\s*<>\s*1"))

    def test_post_apply_assertion(self):
        # 적용 후 정확히 1건 검증하는 사후 DO 블록
        self.assertRegex(_executable_sql(), re.compile(r"n_rel\s*<>\s*1"))

    def test_transaction_wrapped(self):
        body = _executable_sql()
        self.assertRegex(body, re.compile(r"^\s*BEGIN\s*;", re.MULTILINE))
        self.assertRegex(body, re.compile(r"^\s*COMMIT\s*;", re.MULTILINE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
