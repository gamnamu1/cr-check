"""Wave 1 · S6 단위 테스트 — citation audit 순수 모듈 (DB/API 불요).

실행: backend/ 디렉터리에서  python3 -m unittest test_wave1_s6 -v
"""
import unittest
from dataclasses import dataclass

from core.verify_citations import (
    extract_citation_labels,
    normalize_citation_label,
    build_allowed_citations,
    verify_report_citations,
)


# EthicsReference를 직접 import하지 않고 덕타이핑으로 stub 객체 사용
# (verify_citations.py가 덕타이핑으로 동작하는지 자체 검증)
@dataclass
class StubRef:
    ethics_source: str
    ethics_article_number: str
    ethics_title: str = ""
    ethics_tier: int = 3
    relation_type: str = "violates"
    strength: str = "strong"
    reasoning: str = ""
    ethics_code: str = "JEC-STUB"


def mk(src, art, **kw):
    return StubRef(ethics_source=src, ethics_article_number=art, **kw)


class TestExtractAndNormalize(unittest.TestCase):
    def test_extract_simple(self):
        self.assertEqual(
            extract_citation_labels("본문 〔A 제1조〕 추가 〔B 제2조〕"),
            ["A 제1조", "B 제2조"],
        )

    def test_extract_empty_text(self):
        self.assertEqual(extract_citation_labels(""), [])
        self.assertEqual(extract_citation_labels(None), [])  # type: ignore

    def test_extract_skips_blank_label(self):
        # 빈 라벨(〔〕, 〔  〕)은 추출에서 제외
        self.assertEqual(extract_citation_labels("〔〕"), [])
        self.assertEqual(extract_citation_labels("〔   〕"), [])

    def test_extract_other_brackets_ignored(self):
        # 일반 대괄호·괄호·낫표는 인용으로 보지 않음
        self.assertEqual(
            extract_citation_labels("[A 제1조] (B 제2조) 「C 제3조」"),
            [],
        )

    def test_normalize_basic(self):
        self.assertEqual(normalize_citation_label("  신문윤리실천요강 제3조 1항  "),
                         "신문윤리실천요강 제3조 1항")
        self.assertEqual(normalize_citation_label("A\t제1조\n2항"), "A 제1조 2항")

    def test_normalize_fullwidth_digits(self):
        self.assertEqual(normalize_citation_label("A 제３조 １항"), "A 제3조 1항")

    def test_normalize_preserves_separator_and_digits(self):
        # 숫자, 조/항 구분자, 토큰 모두 보존
        self.assertEqual(normalize_citation_label("A 제3조"),  "A 제3조")
        self.assertEqual(normalize_citation_label("A 제3조 1항"), "A 제3조 1항")
        self.assertNotEqual(normalize_citation_label("A 제3조"),
                            normalize_citation_label("A 제3조 1항"))


class TestBuildAllowed(unittest.TestCase):
    def test_basic_canonical(self):
        refs = [mk("신문윤리실천요강", "제3조 1항", ethics_title="사실의견 구분")]
        allowed = build_allowed_citations(refs)
        self.assertEqual(len(allowed), 1)
        a = allowed[0]
        self.assertEqual(a["label"], "신문윤리실천요강 제3조 1항")
        self.assertEqual(a["normalized"], "신문윤리실천요강 제3조 1항")
        self.assertEqual(a["source"], "신문윤리실천요강")
        self.assertEqual(a["article_number"], "제3조 1항")
        self.assertEqual(a["title"], "사실의견 구분")

    def test_excludes_both_missing(self):
        # source/article 모두 비면 allowed에서 제외
        refs = [mk("", "")]
        self.assertEqual(build_allowed_citations(refs), [])

    def test_includes_one_missing(self):
        # 한쪽만 있어도 canonical citation은 만들 수 있음
        refs = [mk("언론윤리헌장", "")]
        allowed = build_allowed_citations(refs)
        self.assertEqual(len(allowed), 1)
        self.assertEqual(allowed[0]["label"], "언론윤리헌장")

    def test_does_not_parse_title(self):
        # title에 조항이 박혀 있어도 source/article 둘 다 없으면 제외 (title 파싱 금지)
        refs = [mk("", "", ethics_title="언론윤리헌장 제1조 진실 보도")]
        self.assertEqual(build_allowed_citations(refs), [])

    def test_no_internal_code_in_label(self):
        refs = [mk("신문윤리실천요강", "제3조 1항", ethics_code="JEC-4")]
        allowed = build_allowed_citations(refs)
        self.assertNotIn("JEC-", allowed[0]["label"])
        self.assertNotIn("JEC-", allowed[0]["normalized"])
        # ethics_code는 디버깅용으로만 보관
        self.assertEqual(allowed[0]["ethics_code"], "JEC-4")


class TestVerifyReportCitations(unittest.TestCase):
    """케이스 A~G + 3종 통합 검증."""

    def _build_reports(self, comp="", journ="", stud=""):
        return {"comprehensive": comp, "journalist": journ, "student": stud}

    # ── 케이스 A: 완전 매칭 ──
    def test_case_a_exact_match(self):
        refs = [mk("신문윤리실천요강", "제3조 1항")]
        reports = self._build_reports(comp="본문 〔신문윤리실천요강 제3조 1항〕 추가 설명.")
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["status"], "ok")
        s = audit["summary"]
        self.assertEqual(s["allowed_count"], 1)
        self.assertEqual(s["used_total"], 1)
        self.assertEqual(s["matched_total"], 1)
        self.assertEqual(s["unmatched_total"], 0)
        self.assertEqual(s["match_rate"], 1.0)

    # ── 케이스 B: unmatched (status 여전히 ok) ──
    def test_case_b_unmatched_status_ok(self):
        refs = [mk("신문윤리실천요강", "제3조 1항")]
        reports = self._build_reports(comp="본문 〔존재하지 않는 규범 제99조〕.")
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["status"], "ok")  # unmatched가 있어도 ok
        s = audit["summary"]
        self.assertEqual(s["used_total"], 1)
        self.assertEqual(s["matched_total"], 0)
        self.assertEqual(s["unmatched_total"], 1)
        self.assertEqual(s["match_rate"], 0.0)

    # ── 케이스 C: 중복 인용 (used_total은 중복 포함, used_unique는 1) ──
    def test_case_c_duplicate_citations(self):
        refs = [mk("신문윤리실천요강", "제3조 1항")]
        reports = self._build_reports(
            comp="〔신문윤리실천요강 제3조 1항〕 ... 〔신문윤리실천요강 제3조 1항〕"
        )
        audit = verify_report_citations(reports, refs)
        s = audit["summary"]
        self.assertEqual(s["used_total"], 2)
        self.assertEqual(s["used_unique_count"], 1)
        self.assertEqual(s["matched_total"], 2)
        ra = audit["reports"]["comprehensive"]
        self.assertEqual(len(ra["matched"]), 2)
        self.assertEqual(len(ra["used_unique"]), 1)

    # ── 케이스 D: 인용 없음 → match_rate = None, 예외 없음 ──
    def test_case_d_no_citations(self):
        refs = [mk("A", "제1조")]
        reports = self._build_reports(comp="인용 표기 없는 리포트입니다.")
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["status"], "ok")
        s = audit["summary"]
        self.assertEqual(s["used_total"], 0)
        self.assertIsNone(s["match_rate"])

    # ── 케이스 E: source/article 누락 ref 포함 → allowed 제외 + notes 기록 ──
    def test_case_e_missing_source_article(self):
        refs = [
            mk("신문윤리실천요강", "제3조 1항"),
            mk("", "", ethics_title="언론윤리헌장 제1조 진실 보도"),  # title 파싱 금지
        ]
        reports = self._build_reports(comp="〔신문윤리실천요강 제3조 1항〕")
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["status"], "ok")
        self.assertEqual(audit["summary"]["allowed_count"], 1)  # title 파싱 미수행
        self.assertTrue(any("excluded" in n for n in audit["notes"]))
        # title의 "언론윤리헌장 제1조"가 allowed에 절대 들어가지 않음
        all_labels = [a["label"] for a in audit["allowed_citations"]]
        self.assertNotIn("언론윤리헌장 제1조", all_labels)

    # ── 케이스 F: 부분 매칭 비매칭 ──
    def test_case_f_partial_match_unmatched(self):
        refs = [mk("신문윤리실천요강", "제3조 1항")]
        reports = self._build_reports(comp="본문 〔신문윤리실천요강 제3조〕")
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["summary"]["matched_total"], 0)
        self.assertEqual(audit["summary"]["unmatched_total"], 1)

    # ── 케이스 G: 정규화 과잉 방지 — 1항/2항 분리 ──
    def test_case_g_normalization_does_not_merge_subarticles(self):
        refs = [
            mk("신문윤리실천요강", "제3조 1항"),
            mk("신문윤리실천요강", "제3조 2항"),
        ]
        reports = self._build_reports(comp="본문 〔신문윤리실천요강 제3조 1항〕")
        audit = verify_report_citations(reports, refs)
        s = audit["summary"]
        self.assertEqual(s["allowed_count"], 2)
        self.assertEqual(s["matched_total"], 1)
        # 1항만 matched, 2항은 used에 등장하지 않음 (matched 라벨에 2항 미포함)
        matched_labels = audit["reports"]["comprehensive"]["matched"]
        self.assertEqual(matched_labels, ["신문윤리실천요강 제3조 1항"])
        self.assertNotIn("신문윤리실천요강 제3조 2항", matched_labels)


class TestThreeReportAudit(unittest.TestCase):
    """3종 리포트 통합 — 게이트 §5-3."""

    def test_three_reports_combined(self):
        refs = [
            mk("신문윤리실천요강", "제3조 1항"),
            mk("언론윤리헌장", "제1조"),
        ]
        reports = {
            "comprehensive": "본문 〔신문윤리실천요강 제3조 1항〕",
            "journalist": "본문 〔언론윤리헌장 제1조〕",
            "student": "본문 〔없는 규범 제9조〕",
        }
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["status"], "ok")
        ra = audit["reports"]
        self.assertEqual(ra["comprehensive"]["matched_count"], 1)
        self.assertEqual(ra["journalist"]["matched_count"], 1)
        self.assertEqual(ra["student"]["matched_count"], 0)
        self.assertEqual(ra["student"]["unmatched_count"], 1)
        s = audit["summary"]
        self.assertEqual(s["used_total"], 3)
        self.assertEqual(s["matched_total"], 2)
        self.assertEqual(s["unmatched_total"], 1)


class TestSafetyAndShape(unittest.TestCase):
    """JSON 직렬화 가능성 / 필수 키 / 예외 흡수."""

    def test_required_summary_keys(self):
        audit = verify_report_citations({}, [])
        for k in ("allowed_count", "used_total", "used_unique_count",
                  "matched_total", "unmatched_total", "match_rate"):
            self.assertIn(k, audit["summary"])
        self.assertEqual(audit["version"], "wave1_s6_v1")

    def test_json_serializable(self):
        import json
        refs = [mk("A", "제1조")]
        reports = {"comprehensive": "본문 〔A 제1조〕"}
        audit = verify_report_citations(reports, refs)
        # raise 없이 직렬화되어야
        s = json.dumps(audit, ensure_ascii=False)
        self.assertIn("wave1_s6_v1", s)

    def test_dict_value_with_body_field(self):
        # report value가 dict인 경우 body/text/content/report 키 추출
        refs = [mk("A", "제1조")]
        reports = {"comprehensive": {"body": "본문 〔A 제1조〕"}}
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["summary"]["matched_total"], 1)

    def test_dict_value_without_known_field(self):
        # body/text/content/report 키 없음 → 빈 텍스트로 처리, 예외 없음, notes 기록
        refs = [mk("A", "제1조")]
        reports = {"comprehensive": {"unknown_key": "본문 〔A 제1조〕"}}
        audit = verify_report_citations(reports, refs)
        self.assertEqual(audit["status"], "ok")
        self.assertEqual(audit["summary"]["used_total"], 0)
        self.assertTrue(any("comprehensive" in n for n in audit["notes"]))


if __name__ == "__main__":
    unittest.main()
