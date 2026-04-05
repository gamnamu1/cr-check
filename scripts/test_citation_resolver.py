#!/usr/bin/env python3
"""
CitationResolver E2E 테스트

(a) TP 건 1건 (D-01): 전체 파이프라인 실행 → cite 태그 치환 검증
(b) TN 건 1건 (C2-01): 파이프라인 실행 → 무해 통과 검증
(c) 환각 ref 테스트: 임의 코드 삽입 → 제거 검증
(d) 200자 초과 절단 테스트
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / "backend" / ".env")

os.environ["SUPABASE_LOCAL"] = "1"

logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from backend.core.citation_resolver import resolve_citations, _truncate_text
from backend.core.report_generator import EthicsReference


def test_truncate():
    """(d) 200자 초과 규범 절단 테스트."""
    print("\n" + "=" * 60)
    print("테스트 (d): 200자 초과 규범 절단")
    print("=" * 60)

    short = "짧은 텍스트입니다."
    assert _truncate_text(short) == short, "200자 이하는 그대로 반환"
    print(f"  200자 이하: PASS ('{short}')")

    # 300자 텍스트 생성
    long_text = "윤리적 언론은 진실을 보도한다. " * 15  # ~210자+
    result = _truncate_text(long_text, 200)
    assert len(result) <= 203, f"절단 후 길이 초과: {len(result)}"  # 200 + "..." = 203 max
    assert result.endswith("..."), "말줄임표 누락"
    # 공백/마침표 경계 확인
    before_ellipsis = result[:-3]
    assert before_ellipsis[-1] in (' ', '.', '。') or before_ellipsis.rstrip()[-1] in (' ', '.', '。'), \
        f"어절 경계 아닌 위치에서 절단: '{before_ellipsis[-5:]}'"
    print(f"  300자 → {len(result)}자: PASS")
    print(f"  절단 결과 끝부분: '...{result[-30:]}'")

    # 공백 없는 텍스트
    no_space = "가" * 250
    result2 = _truncate_text(no_space, 200)
    assert result2 == "가" * 200 + "...", "공백 없으면 200자에서 절단"
    print(f"  공백 없는 250자 → {len(result2)}자: PASS")


def test_hallucinated_ref():
    """(c) 환각 ref 테스트."""
    print("\n" + "=" * 60)
    print("테스트 (c): 환각 ref 제거")
    print("=" * 60)

    # 가상 리포트 + ethics_refs
    report = (
        '이 기사는 <cite ref="JCE-1"/> 원칙을 위반하고 있습니다. '
        '또한 <cite ref="JCE-99"/> 규정에도 저촉됩니다. '
        '참고로 <cite ref="PCP-3-1"/>도 관련됩니다.'
    )

    ethics_refs = [
        EthicsReference(
            pattern_code="1-1-1",
            ethics_code="JCE-1",
            ethics_title="진실을 추구한다",
            ethics_full_text="윤리적 언론은 진실을 보도한다.",
            ethics_tier=1,
            relation_type="violates",
            strength="strong",
            reasoning="test",
        ),
        EthicsReference(
            pattern_code="1-1-1",
            ethics_code="PCP-3-1",
            ethics_title="보도기사의 사실과 의견 구분",
            ethics_full_text="보도기사는 사실과 의견을 명확히 구분하여 작성해야 한다.",
            ethics_tier=2,
            relation_type="violates",
            strength="moderate",
            reasoning="test",
        ),
    ]

    resolved, hallucinated = resolve_citations(report, ethics_refs)

    print(f"\n  원본: {report}")
    print(f"\n  치환 결과: {resolved}")
    print(f"\n  환각 ref: {hallucinated}")

    assert "JCE-99" in hallucinated, "JCE-99가 환각 목록에 없음"
    assert "<cite" not in resolved, "cite 태그가 남아있음"
    assert "「진실을 추구한다:" in resolved, "JCE-1 치환 실패"
    assert "「보도기사의 사실과 의견 구분:" in resolved, "PCP-3-1 치환 실패"
    print("\n  PASS: 환각 ref 제거 + 정상 치환 확인")


def test_duplicate_citation():
    """중복 인용 테스트."""
    print("\n" + "=" * 60)
    print("테스트: 중복 인용 축약")
    print("=" * 60)

    report = (
        '첫 번째 위반: <cite ref="JCE-1"/>. '
        '두 번째에서도 같은 규범: <cite ref="JCE-1"/>.'
    )

    ethics_refs = [
        EthicsReference(
            pattern_code="1-1-1",
            ethics_code="JCE-1",
            ethics_title="진실을 추구한다",
            ethics_full_text="윤리적 언론은 진실을 보도한다.",
            ethics_tier=1,
            relation_type="violates",
            strength="strong",
            reasoning="test",
        ),
    ]

    resolved, hallucinated = resolve_citations(report, ethics_refs)

    print(f"\n  원본: {report}")
    print(f"\n  치환 결과: {resolved}")

    assert "「진실을 추구한다:" in resolved, "첫 출현 정상 치환 실패"
    assert "「진실을 추구한다 참조」" in resolved, "중복 축약 실패"
    assert len(hallucinated) == 0, "환각이 없어야 함"
    print("\n  PASS: 첫 출현=원문, 이후=참조")


def test_e2e_tp(article_id: str = "D-01"):
    """(a) TP 건 E2E 테스트 — 전체 파이프라인 실행."""
    print("\n" + "=" * 60)
    print(f"테스트 (a): E2E TP건 ({article_id})")
    print("=" * 60)

    article_path = Path("/Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts") / f"{article_id}_article.txt"
    if not article_path.exists():
        print(f"  SKIP: {article_path} 없음")
        return

    article_text = article_path.read_text(encoding="utf-8")
    print(f"  기사 길이: {len(article_text)}자")

    from backend.core.pipeline import analyze_article
    result = analyze_article(article_text, run_sonnet=True)

    report = result.report_result.report_text
    print(f"\n  === 최종 리포트 (치환 후) ===")
    print(report[:2000] if len(report) > 2000 else report)

    has_cite = "<cite" in report
    print(f"\n  cite 태그 잔존: {'YES ❌' if has_cite else 'NO ✅'}")
    has_citation = "「" in report
    print(f"  규범 인용 포함: {'YES ✅' if has_citation else 'NO (패턴 미감지)'}")

    if result.report_result.ethics_refs:
        print(f"  ethics_refs 수: {len(result.report_result.ethics_refs)}")
    print(f"  소요: {result.total_seconds:.1f}초")


def test_e2e_tn(article_id: str = "C2-01"):
    """(b) TN 건 E2E 테스트 — 양질 보도 무해 통과."""
    print("\n" + "=" * 60)
    print(f"테스트 (b): E2E TN건 ({article_id})")
    print("=" * 60)

    article_path = Path("/Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts") / f"{article_id}_article.txt"
    if not article_path.exists():
        print(f"  SKIP: {article_path} 없음")
        return

    article_text = article_path.read_text(encoding="utf-8")
    print(f"  기사 길이: {len(article_text)}자")

    from backend.core.pipeline import analyze_article
    result = analyze_article(article_text, run_sonnet=True)

    report = result.report_result.report_text
    print(f"\n  리포트: {report[:500]}")

    has_cite = "<cite" in report
    print(f"\n  cite 태그 잔존: {'YES ❌' if has_cite else 'NO ✅'}")
    print(f"  소요: {result.total_seconds:.1f}초")


if __name__ == "__main__":
    # 유닛 테스트 먼저 (API 호출 없음)
    test_truncate()
    test_hallucinated_ref()
    test_duplicate_citation()

    # E2E 테스트 (API 호출 필요)
    print("\n\n" + "#" * 60)
    print("# E2E 테스트 — API 호출 포함")
    print("#" * 60)

    test_e2e_tp("D-01")
    test_e2e_tn("C2-01")

    print("\n\n=== 전체 테스트 완료 ===")
