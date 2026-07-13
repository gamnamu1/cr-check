"""보안 하드닝 Migration A/B 정적 계약 검증 (DB·API 불요).

대상 파일:
  supabase/migrations/20260714051150_security_A_view_and_function_hardening.sql
  supabase/migrations/20260714051151_security_B_private_table_rls.sql

Migration A 계약:
  1. active_ethics_codes 뷰에 security_invoker=on 설정
  2. 6개 함수 각각에 정확한 identity args로 search_path 설정
  3. 함수 본문 재작성·grants 변경 없음(ALTER FUNCTION SET search_path만)
  4. 되돌리는 rollback 절이 파일에 문서화되어 있음

Migration B 계약:
  1. 3개 사설 테이블 정책만 DROP POLICY IF EXISTS
  2. 유지 대상 5개 공개 데이터 정책은 이 파일에 등장하지 않음
  3. RLS DISABLE / ENABLE / FORCE 문 부재
  4. CREATE/ALTER POLICY 문 부재 (drop-only)
  5. 되돌리는 rollback 절이 파일에 문서화되어 있음

실행: backend/ 디렉터리에서
  python3 -m unittest test_security_hardening_migrations -v
"""

import re
import unittest
from pathlib import Path

_MIG_DIR = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
_A = _MIG_DIR / "20260714051150_security_A_view_and_function_hardening.sql"
_B = _MIG_DIR / "20260714051151_security_B_private_table_rls.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _executable(sql: str) -> str:
    return "\n".join(
        ln for ln in sql.splitlines() if not ln.lstrip().startswith("--")
    )


class TestMigrationAContract(unittest.TestCase):
    """Migration A: 뷰 invoker + 6개 함수 search_path."""

    def setUp(self):
        self.sql = _read(_A)
        self.body = _executable(self.sql)

    def test_file_exists(self):
        self.assertTrue(_A.is_file(), _A)

    def test_view_security_invoker(self):
        self.assertIn(
            "ALTER VIEW public.active_ethics_codes SET (security_invoker = on)",
            self.body,
        )

    def test_all_six_functions_altered(self):
        expected = [
            "ALTER FUNCTION public.search_pattern_candidates("
            "vector, double precision, integer)",
            "ALTER FUNCTION public.get_ethics_for_patterns(bigint[], text)",
            "ALTER FUNCTION public.get_trending_articles(integer)",
            "ALTER FUNCTION public.get_publisher_stats()",
            "ALTER FUNCTION public.get_overall_stats()",
            "ALTER FUNCTION public.handle_updated_at()",
        ]
        for sig in expected:
            self.assertIn(sig, self.body, f"missing ALTER for {sig}")

    def test_search_path_value(self):
        self.assertEqual(
            len(re.findall(r"SET search_path = public, pg_temp", self.body)),
            6,
        )

    def test_no_function_body_rewrite(self):
        # SET search_path만 허용 — CREATE OR REPLACE FUNCTION 금지
        self.assertNotRegex(self.body, re.compile(
            r"CREATE\s+(OR\s+REPLACE\s+)?FUNCTION", re.IGNORECASE
        ))
        # DROP FUNCTION도 금지
        self.assertNotRegex(self.body, re.compile(
            r"\bDROP\s+FUNCTION\b", re.IGNORECASE
        ))
        # 권한 변경 금지
        self.assertNotRegex(self.body, re.compile(
            r"\bGRANT\b|\bREVOKE\b", re.IGNORECASE
        ))

    def test_no_view_recreate(self):
        # 뷰 정의 변경 없음
        self.assertNotRegex(self.body, re.compile(
            r"CREATE\s+(OR\s+REPLACE\s+)?VIEW", re.IGNORECASE
        ))
        self.assertNotRegex(self.body, re.compile(
            r"\bDROP\s+VIEW\b", re.IGNORECASE
        ))

    def test_transaction_and_pgrst_reload(self):
        self.assertRegex(self.body, re.compile(r"^\s*BEGIN\s*;", re.MULTILINE))
        self.assertRegex(self.body, re.compile(r"^\s*COMMIT\s*;", re.MULTILINE))
        self.assertIn("NOTIFY pgrst, 'reload schema'", self.body)

    def test_post_apply_assertions(self):
        # 함수 6개 모두 proconfig에 search_path 있는지, 뷰 옵션 있는지 사후 검증
        self.assertRegex(self.body, re.compile(r"DO\s+\$\$"))
        self.assertIn("search_path missing", self.sql)
        self.assertIn("security_invoker=on not applied", self.sql)

    def test_rollback_documented(self):
        self.assertIn("[ROLLBACK]", self.sql)
        rb = self.sql.split("[ROLLBACK]")[1]
        # 6개 함수 RESET + 뷰 RESET
        self.assertEqual(len(re.findall(r"RESET\s+search_path", rb)), 6)
        self.assertIn("RESET (security_invoker)", rb)


class TestMigrationBContract(unittest.TestCase):
    """Migration B: 3개 사설 테이블 정책 drop-only."""

    def setUp(self):
        self.sql = _read(_B)
        self.body = _executable(self.sql)

    def test_file_exists(self):
        self.assertTrue(_B.is_file(), _B)

    def test_three_drop_policy_statements(self):
        drops = re.findall(
            r"DROP\s+POLICY\s+IF\s+EXISTS\s+(\w+)\s+ON\s+public\.(\w+)",
            self.body, re.IGNORECASE
        )
        self.assertEqual(
            sorted(drops),
            sorted([
                ("anon_read_analysis_ethics_snapshot", "analysis_ethics_snapshot"),
                ("anon_read_analysis_results",         "analysis_results"),
                ("anon_read_articles",                 "articles"),
            ]),
        )

    def test_no_public_data_policies_touched(self):
        # 유지 대상 5개 정책명은 파괴적 문장의 대상이 되면 안 된다.
        # (DO 블록의 pg_policies 조회에서 사후 검증용으로 언급되는 것은 허용.)
        destructive = re.compile(
            r"(DROP|CREATE|ALTER)\s+POLICY[^;]*?(\w+)", re.IGNORECASE | re.DOTALL
        )
        touched = {m.group(2) for m in destructive.finditer(self.body)}
        for kept in [
            "anon_read_patterns",
            "anon_read_ethics_codes",
            "anon_read_ethics_code_hierarchy",
            "anon_read_pattern_ethics_relations",
            "anon_read_pattern_relations",
        ]:
            self.assertNotIn(kept, touched, f"{kept} touched by destructive stmt")

    def test_only_drop_policy_no_creates_or_alters(self):
        # CREATE/ALTER POLICY 금지, ENABLE/DISABLE/FORCE RLS 금지
        self.assertNotRegex(self.body, re.compile(
            r"CREATE\s+POLICY|ALTER\s+POLICY", re.IGNORECASE
        ))
        self.assertNotRegex(self.body, re.compile(
            r"ENABLE\s+ROW\s+LEVEL\s+SECURITY|DISABLE\s+ROW\s+LEVEL\s+SECURITY"
            r"|FORCE\s+ROW\s+LEVEL\s+SECURITY", re.IGNORECASE
        ))

    def test_out_of_scope_tables_untouched(self):
        for oos in [
            "feedbacks",
            "pattern_confusion_pairs",
            "phase1_forensic",
        ]:
            self.assertNotIn(oos, self.body, f"{oos} unexpectedly in executable")

    def test_transaction_and_reload(self):
        self.assertRegex(self.body, re.compile(r"^\s*BEGIN\s*;", re.MULTILINE))
        self.assertRegex(self.body, re.compile(r"^\s*COMMIT\s*;", re.MULTILINE))
        self.assertIn("NOTIFY pgrst, 'reload schema'", self.body)

    def test_post_apply_assertions(self):
        # 3건 제거 + 5건 유지 + RLS 활성 상태 검증하는 DO 블록
        self.assertIn("expected 3 target policies removed", self.sql)
        self.assertIn("expected 5 public-data policies preserved", self.sql)
        self.assertIn("RLS unexpectedly disabled", self.sql)

    def test_rollback_documented(self):
        self.assertIn("[ROLLBACK]", self.sql)
        rb = self.sql.split("[ROLLBACK]")[1]
        # 3개 정책 재생성
        self.assertEqual(len(re.findall(r"CREATE\s+POLICY", rb)), 3)
        self.assertIn("USING (true)", rb)
        self.assertIn("TO public", rb)


class TestMigrationBExposureAssertion(unittest.TestCase):
    """Migration B 강화 계약: 이름 무관 실질 노출 여부 사후 검증 DO 블록.

    보안 목표는 특정 정책 이름 소멸이 아니라, 세 사설 테이블에 public/anon/
    authenticated 역할이 SELECT/ALL을 얻는 permissive 정책이 남지 않는 것.
    이 계약이 실행 SQL(rollback 주석 아님)에 정확히 실려 있는지 검사한다.
    """

    def setUp(self):
        sql = _read(_B)
        # rollback 주석은 실행되지 않으므로 검사 대상에서 제외.
        pre_rollback = sql.split("[ROLLBACK]")[0]
        # 실행 SQL 내에서 신규 강화 블록만 추출 — 지시문의 정확한 표현으로 고정.
        anchor = "n_exposing INT"
        self.assertIn(anchor, pre_rollback, "n_exposing DO 블록 부재")
        idx = pre_rollback.index(anchor)
        # 블록 종료는 그 뒤 첫 'END $$;'
        end = pre_rollback.index("END $$;", idx) + len("END $$;")
        self.block = pre_rollback[
            pre_rollback.rfind("DO $$", 0, idx):end
        ]

    def test_queries_pg_policies(self):
        self.assertIn("pg_policies", self.block)

    def test_targets_three_private_tables(self):
        # tablename IN (...) 형태로 세 테이블 모두 포함
        for t in ("'articles'", "'analysis_results'", "'analysis_ethics_snapshot'"):
            self.assertIn(t, self.block, f"missing {t}")
        # tablename IN 절 존재
        self.assertRegex(self.block, re.compile(r"tablename\s+IN\s*\(", re.IGNORECASE))

    def test_permissive_and_cmd_filters(self):
        self.assertIn("permissive = 'PERMISSIVE'", self.block)
        # cmd IN ('SELECT', 'ALL')
        self.assertRegex(
            self.block,
            re.compile(
                r"cmd\s+IN\s*\(\s*'SELECT'\s*,\s*'ALL'\s*\)",
                re.IGNORECASE,
            ),
        )

    def test_three_roles_covered(self):
        for role in ("'public'", "'anon'", "'authenticated'"):
            self.assertIn(role, self.block, f"missing role literal {role}")

    def test_service_role_excluded_from_gate(self):
        # service_role은 차단 검사 대상 아님
        self.assertNotIn("'service_role'", self.block)

    def test_roles_overlap_operator(self):
        # roles 배열과 name[] 캐스트에 대한 && overlap 존재
        self.assertRegex(
            self.block,
            re.compile(
                r"roles\s+&&\s+ARRAY\s*\[[^\]]+\]\s*::\s*name\s*\[\s*\]",
                re.IGNORECASE | re.DOTALL,
            ),
        )

    def test_zero_gate_and_raise(self):
        self.assertIn("n_exposing <> 0", self.block)
        self.assertIn("RAISE EXCEPTION", self.block)

    def test_error_message_names_the_risk(self):
        # 실패 시 원인이 리포트에 남도록 문구가 계약된 키워드를 담아야 함
        self.assertIn("permissive", self.block)
        self.assertIn("SELECT/ALL", self.block)
        self.assertIn("public/anon/authenticated", self.block)

    def test_prior_checks_still_present(self):
        # 새 블록 추가가 기존 3개 계약을 대체하지 않음
        sql = _read(_B)
        self.assertIn("expected 3 target policies removed", sql)
        self.assertIn("expected 5 public-data policies preserved", sql)
        self.assertIn("RLS unexpectedly disabled", sql)


if __name__ == "__main__":
    unittest.main(verbosity=2)
