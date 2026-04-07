#!/usr/bin/env python3
"""
M3 Recall@10 Benchmark for CR-Check Hybrid RAG.

Measures how well search_pattern_candidates() retrieves expected patterns
from the golden dataset using vector similarity search.
"""

import json
import os
import sys

import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

EMBEDDING_MODEL = "text-embedding-3-small"
ARTICLE_TEXTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "Golden_Data_Set_Pool", "article_texts"
)
META_PATTERNS = {"1-4-1", "1-4-2"}
TN_IDS = {"C-02", "C-04", "C2-01", "C2-07", "E-17", "E-19"}

CATEGORY_NAMES = {
    "1-1": "진실성", "1-2": "투명성", "1-3": "균형성", "1-4": "독립성",
    "1-5": "인권", "1-6": "전문성", "1-7": "언어", "1-8": "디지털",
}


def load_golden_data(base_dir):
    """Load golden dataset labels and article texts."""
    with open(os.path.join(base_dir, "docs/golden_dataset_labels.json")) as f:
        labels = json.load(f)

    cases = []
    for label in labels["labels"]:
        cid = label["candidate_id"]
        expected = [p["pattern_id"] for p in label.get("expected_patterns", [])]

        # Load article text
        text_path = os.path.join(ARTICLE_TEXTS_DIR, f"{cid}_article.txt")
        article_text = ""
        if os.path.exists(text_path):
            with open(text_path, encoding="utf-8") as f:
                article_text = f.read().strip()

        cases.append({
            "id": cid,
            "expected_patterns": expected,
            "expected_no_meta": [p for p in expected if p not in META_PATTERNS],
            "is_tn": cid in TN_IDS,
            "article_text": article_text,
        })

    return cases


def generate_query_embeddings(client, cases):
    """Generate embeddings for article texts."""
    texts = []
    valid_indices = []

    for i, case in enumerate(cases):
        if case["article_text"]:
            # Truncate to ~8000 chars to stay within token limits
            texts.append(case["article_text"][:8000])
            valid_indices.append(i)

    print(f"  Generating embeddings for {len(texts)} articles...")
    response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)

    for idx, emb_item in zip(valid_indices, response.data):
        cases[idx]["query_embedding"] = emb_item.embedding

    missing = [c["id"] for c in cases if "query_embedding" not in c]
    if missing:
        print(f"  WARNING: No article text for: {missing}")

    return cases


def search_patterns(conn, query_embedding, threshold=0.5, match_count=10):
    """Call search_pattern_candidates RPC."""
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pattern_code, similarity FROM search_pattern_candidates(%s::vector, %s, %s)",
            (embedding_str, threshold, match_count),
        )
        return [(row[0], round(row[1], 4)) for row in cur.fetchall()]


def compute_recall(expected, retrieved_codes, exclude_meta=True):
    """Compute Recall@K."""
    if exclude_meta:
        expected_filtered = [p for p in expected if p not in META_PATTERNS]
    else:
        expected_filtered = expected

    if not expected_filtered:
        return 1.0  # TN or empty expected = perfect

    hits = len(set(expected_filtered) & set(retrieved_codes))
    return hits / len(expected_filtered)


def run_benchmark(conn, client, cases, threshold=0.5):
    """Run benchmark at a given threshold."""
    results = []

    for case in cases:
        if "query_embedding" not in case:
            results.append({**case, "retrieved": [], "recall": 0.0, "recall_raw": 0.0, "skipped": True})
            continue

        retrieved = search_patterns(conn, case["query_embedding"], threshold)
        retrieved_codes = [r[0] for r in retrieved]

        recall = compute_recall(case["expected_no_meta"], retrieved_codes, exclude_meta=False)
        recall_raw = compute_recall(case["expected_patterns"], retrieved_codes, exclude_meta=False)

        results.append({
            **case,
            "retrieved": retrieved,
            "retrieved_codes": retrieved_codes,
            "recall": recall,
            "recall_raw": recall_raw,
            "skipped": False,
        })

    return results


def format_results(results, threshold):
    """Format benchmark results as markdown."""
    lines = []
    lines.append(f"\n=== CR-Check Recall@10 벤치마크 결과 (threshold={threshold}) ===\n")

    # Per-case results
    lines.append("[건별 결과]")
    lines.append("| # | Article ID | Expected (메타제외) | Retrieved (Top 3) | Hit | Recall |")
    lines.append("|---|-----------|---------------------|-------------------|-----|--------|")

    for i, r in enumerate(results):
        if r.get("skipped"):
            lines.append(f"| {i+1} | {r['id']} | (no text) | — | — | — |")
            continue

        expected_str = ", ".join(r["expected_no_meta"]) if r["expected_no_meta"] else "(TN)"
        top3 = ", ".join(r["retrieved_codes"][:3]) if r.get("retrieved_codes") else "(none)"
        hits = set(r["expected_no_meta"]) & set(r.get("retrieved_codes", []))
        hit_mark = "✅" if (r["recall"] >= 1.0) else ("⚠️" if r["recall"] > 0 else "❌")
        if r["is_tn"] and len(r.get("retrieved_codes", [])) == 0:
            hit_mark = "✅"
        elif r["is_tn"]:
            hit_mark = "⚠️"

        lines.append(
            f"| {i+1} | {r['id']} | {expected_str} | {top3} | {hit_mark} | {r['recall']:.2f} |"
        )

    # Category-level recall
    cat_recalls = {}
    for r in results:
        if r.get("skipped"):
            continue
        if r["is_tn"]:
            cat = "TN"
        else:
            first_pat = r["expected_no_meta"][0] if r["expected_no_meta"] else "?"
            cat = "-".join(first_pat.split("-")[:2])
        cat_recalls.setdefault(cat, []).append(r["recall"])

    lines.append("\n[대분류별 Recall]")
    lines.append("| 대분류 | 건수 | 평균 Recall@10 |")
    lines.append("|--------|------|---------------|")
    for cat in sorted(cat_recalls.keys()):
        vals = cat_recalls[cat]
        name = CATEGORY_NAMES.get(cat, cat)
        avg = sum(vals) / len(vals)
        lines.append(f"| {cat} {name} | {len(vals)} | {avg:.2f} |")

    # Overall summary
    valid = [r for r in results if not r.get("skipped")]
    avg_recall = sum(r["recall"] for r in valid) / len(valid) if valid else 0
    avg_recall_raw = sum(r["recall_raw"] for r in valid) / len(valid) if valid else 0
    passed = avg_recall >= 0.80

    lines.append("\n[전체 요약]")
    lines.append(f"- 전체 평균 Recall@10: {avg_recall:.4f}")
    lines.append(f"- 전체 평균 Recall@10 (메타 패턴 미제외, 참고용): {avg_recall_raw:.4f}")
    lines.append(f"- threshold: {threshold}")
    lines.append(f"- 패턴 수: 28개 (is_meta_pattern=FALSE, 대분류 제외)")
    lines.append(f"- 총 임베딩: 401개")
    lines.append(f"- 목표: ≥ 0.80")
    lines.append(f"- 판정: {'PASS ✅' if passed else 'FAIL ❌'}")

    # Low recall details
    low_recall = [r for r in valid if r["recall"] < 0.5 and not r["is_tn"]]
    if low_recall:
        lines.append("\n[상세 분석 — Recall < 0.5인 건]")
        for r in low_recall:
            lines.append(f"\n  {r['id']}:")
            lines.append(f"    Expected (메타제외): {r['expected_no_meta']}")
            lines.append(f"    Retrieved:")
            for code, sim in r.get("retrieved", []):
                hit = "✅" if code in r["expected_no_meta"] else "  "
                lines.append(f"      {hit} {code} (similarity={sim})")

    return "\n".join(lines), avg_recall, passed


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found")
        sys.exit(1)

    db_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    client = OpenAI(api_key=api_key)
    conn = psycopg2.connect(db_url)

    # Load data
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    print("Loading golden dataset...")
    cases = load_golden_data(base_dir)
    print(f"  Total cases: {len(cases)} (TP: {sum(1 for c in cases if not c['is_tn'])}, TN: {sum(1 for c in cases if c['is_tn'])})")

    # Generate query embeddings
    print("\nGenerating query embeddings...")
    cases = generate_query_embeddings(client, cases)

    # Run benchmark at multiple thresholds
    thresholds = [0.3, 0.4, 0.5, 0.6]
    all_outputs = []
    threshold_summary = []

    for t in thresholds:
        print(f"\nRunning benchmark (threshold={t})...")
        results = run_benchmark(conn, client, cases, threshold=t)
        output, avg_recall, passed = format_results(results, t)

        if t == 0.5:
            primary_output = output
            primary_results = results

        threshold_summary.append((t, avg_recall, passed))
        all_outputs.append(output)

    # Print primary results (threshold=0.5)
    print(primary_output)

    # Threshold comparison table
    print("\n\n=== Threshold 비교표 ===")
    print("| Threshold | 평균 Recall@10 | 판정 |")
    print("|-----------|---------------|------|")
    for t, avg, passed in threshold_summary:
        mark = "✅" if passed else "❌"
        star = " ★" if t == 0.5 else ""
        print(f"| {t}{star} | {avg:.4f} | {mark} |")

    # Save results to file
    results_path = os.path.join(base_dir, "docs", "M3_BENCHMARK_RESULTS.md")
    with open(results_path, "w", encoding="utf-8") as f:
        f.write("# M3 Recall@10 벤치마크 결과\n\n")
        f.write(f"> 실행 일시: 2026-03-28\n")
        f.write(f"> 모델: {EMBEDDING_MODEL}\n")
        f.write(f"> 골든 데이터셋: 26건 (TP 20 + TN 6)\n\n")

        f.write("## Threshold 비교표\n\n")
        f.write("| Threshold | 평균 Recall@10 | 판정 |\n")
        f.write("|-----------|---------------|------|\n")
        for t, avg, passed in threshold_summary:
            mark = "PASS" if passed else "FAIL"
            star = " (기본값)" if t == 0.5 else ""
            f.write(f"| {t}{star} | {avg:.4f} | {mark} |\n")

        f.write("\n## 상세 결과 (threshold=0.5)\n")
        f.write(primary_output)

        f.write("\n\n## 기타 threshold 결과\n")
        for output in all_outputs:
            if "threshold=0.5" not in output:
                f.write(output)
                f.write("\n")

    print(f"\n결과 저장: {results_path}")
    conn.close()


if __name__ == "__main__":
    main()
