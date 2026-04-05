#!/usr/bin/env python3
"""
M4 E2E 파이프라인 테스트 — 골든 데이터셋 기사 3건.

사용법:
  python scripts/test_pipeline.py [--no-sonnet]
"""

import json
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# .env 로드 (프로젝트 루트)
load_dotenv(Path(__file__).parent.parent / ".env")

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.pipeline import analyze_article


def load_golden_dataset():
    gd_path = Path(__file__).parent.parent / "docs" / "golden_dataset_final.json"
    with open(gd_path) as f:
        return json.load(f)


def load_labels():
    lb_path = Path(__file__).parent.parent / "docs" / "golden_dataset_labels.json"
    with open(lb_path) as f:
        return json.load(f)


def get_expected_patterns(labels, candidate_id):
    for lb in labels.get("labels", []):
        if lb["candidate_id"] == candidate_id:
            return [p["pattern_id"] for p in lb.get("expected_patterns", [])]
    return []


def run_test(candidate, expected_patterns, run_sonnet=True):
    cid = candidate["candidate_id"]
    title = candidate.get("title", "")[:50]
    article_text = candidate.get("article_key_text", "")

    if not article_text:
        print(f"\n{'='*60}")
        print(f"[{cid}] {title}")
        print(f"  SKIP: article_key_text가 비어있음")
        return

    print(f"\n{'='*60}")
    print(f"[{cid}] {title}")
    print(f"  기사 길이: {len(article_text)}자")
    print(f"  기대 패턴: {expected_patterns}")
    print(f"  Sonnet: {'ON' if run_sonnet else 'OFF'}")
    print(f"-" * 60)

    result = analyze_article(article_text, run_sonnet=run_sonnet)

    # 청킹 결과
    print(f"\n  [청킹] 청크 수: {result.chunk_count}, 평균 길이: {result.avg_chunk_length:.0f}자")
    for i, ch in enumerate(result.chunks):
        print(f"    [{i}] {ch.length}자: {ch.text[:60]}...")

    # 벡터 검색 결과
    pm = result.pattern_result
    print(f"\n  [벡터검색] 후보 {len(pm.vector_candidates)}건")
    for vc in pm.vector_candidates[:10]:
        hit = "✓" if vc.pattern_code in expected_patterns else " "
        print(f"    {hit} {vc.pattern_code:8s} sim={vc.similarity:.3f} | {vc.pattern_name}")

    # Haiku 결과
    print(f"\n  [Haiku] 확정 {len(pm.haiku_detections)}건 → 검증통과 {len(pm.validated_pattern_codes)}건")
    if pm.hallucinated_codes:
        print(f"    환각 제거: {pm.hallucinated_codes}")
    for d in pm.haiku_detections:
        valid = "✓" if d.pattern_code in pm.validated_pattern_codes else "✗"
        hit = "HIT" if d.pattern_code in expected_patterns else "   "
        print(f"    {valid} {hit} {d.pattern_code:8s} [{d.severity}] {d.reasoning[:60]}")

    # 매칭 분석
    haiku_codes = set(pm.validated_pattern_codes)
    expected_set = set(expected_patterns)
    tp = haiku_codes & expected_set
    fn = expected_set - haiku_codes
    fp = haiku_codes - expected_set
    recall = len(tp) / len(expected_set) if expected_set else 1.0
    precision = len(tp) / len(haiku_codes) if haiku_codes else (1.0 if not expected_set else 0.0)

    print(f"\n  [성능] Recall={recall:.2f} Precision={precision:.2f}")
    if fn:
        print(f"    MISS: {fn}")
    if fp:
        print(f"    FP:   {fp}")

    # Sonnet 결과
    if run_sonnet and result.report_result.report_text:
        report = result.report_result.report_text
        cite_count = report.count("<cite ref=")
        print(f"\n  [Sonnet] 리포트 길이: {len(report)}자, cite 태그: {cite_count}개")
        print(f"    입력 토큰: {result.sonnet_input_tokens}, 출력 토큰: {result.sonnet_output_tokens}")
        # 처음 200자 미리보기
        print(f"    미리보기: {report[:200]}...")

    print(f"\n  [메타] 총 {result.total_seconds:.1f}초, 임베딩 토큰: {result.embedding_tokens}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-sonnet", action="store_true", help="Sonnet 호출 건너뛰기")
    parser.add_argument("--ids", nargs="*", default=["A-01", "B-11", "D-01"],
                        help="테스트할 candidate_id 목록")
    args = parser.parse_args()

    gd = load_golden_dataset()
    labels = load_labels()
    candidates = gd["candidates"]

    print("=" * 60)
    print("M4 E2E 파이프라인 테스트")
    print(f"대상: {args.ids}")
    print(f"Sonnet: {'OFF' if args.no_sonnet else 'ON'}")
    print("=" * 60)

    for cid in args.ids:
        c = next((x for x in candidates if x["candidate_id"] == cid), None)
        if not c:
            print(f"\n[{cid}] NOT FOUND in golden dataset")
            continue
        expected = get_expected_patterns(labels, cid)
        run_test(c, expected, run_sonnet=not args.no_sonnet)


if __name__ == "__main__":
    main()
