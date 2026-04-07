#!/usr/bin/env python3
"""
M3 Recall@10 Benchmark v2 — article_key_text 기반.

1차(기사 전문) vs 2차(key_text) 비교를 포함.
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


def load_cases(base_dir):
    with open(os.path.join(base_dir, "docs/golden_dataset_labels.json")) as f:
        labels = json.load(f)
    with open(os.path.join(base_dir, "docs/golden_dataset_final.json")) as f:
        gd = json.load(f)

    key_text_map = {c["candidate_id"]: c.get("article_key_text", "") for c in gd["candidates"]}

    cases = []
    for label in labels["labels"]:
        cid = label["candidate_id"]
        expected = [p["pattern_id"] for p in label.get("expected_patterns", [])]
        key_text = key_text_map.get(cid, "")

        # Also load full article for comparison
        full_path = os.path.join(ARTICLE_TEXTS_DIR, f"{cid}_article.txt")
        full_text = ""
        if os.path.exists(full_path):
            with open(full_path, encoding="utf-8") as f:
                full_text = f.read().strip()

        cases.append({
            "id": cid,
            "expected_patterns": expected,
            "expected_no_meta": [p for p in expected if p not in META_PATTERNS],
            "is_tn": cid in TN_IDS,
            "key_text": key_text,
            "full_text": full_text,
        })
    return cases


def embed_texts(client, texts):
    response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    return [item.embedding for item in response.data]


def search_patterns(conn, embedding, threshold=0.5, count=10):
    emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pattern_code, similarity FROM search_pattern_candidates(%s::vector, %s, %s)",
            (emb_str, threshold, count),
        )
        return [(r[0], round(r[1], 4)) for r in cur.fetchall()]


def compute_recall(expected_no_meta, retrieved_codes):
    if not expected_no_meta:
        return 1.0
    hits = len(set(expected_no_meta) & set(retrieved_codes))
    return hits / len(expected_no_meta)


def run_benchmark(conn, cases, embeddings, threshold):
    results = []
    for i, case in enumerate(cases):
        emb = embeddings.get(case["id"])
        if emb is None:
            results.append({**case, "retrieved": [], "retrieved_codes": [], "recall": 1.0 if case["is_tn"] else 0.0})
            continue
        retrieved = search_patterns(conn, emb, threshold)
        codes = [r[0] for r in retrieved]
        recall = compute_recall(case["expected_no_meta"], codes)
        results.append({**case, "retrieved": retrieved, "retrieved_codes": codes, "recall": recall})
    return results


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    base_dir = os.path.join(os.path.dirname(__file__), "..")

    cases = load_cases(base_dir)
    print(f"Loaded {len(cases)} cases (TP: {sum(1 for c in cases if not c['is_tn'])}, TN: {sum(1 for c in cases if c['is_tn'])})")

    # --- Embed key_text ---
    print("\nEmbedding key_texts...")
    kt_texts = []
    kt_ids = []
    for c in cases:
        if c["key_text"]:
            kt_texts.append(c["key_text"])
            kt_ids.append(c["id"])
        elif c["is_tn"]:
            pass  # TN with empty key_text → no embedding needed
    kt_embs = embed_texts(client, kt_texts) if kt_texts else []
    key_embeddings = {cid: emb for cid, emb in zip(kt_ids, kt_embs)}
    # TN cases get no embedding → search returns empty → recall=1.0
    print(f"  Embedded {len(kt_embs)} key_texts")

    # --- Embed full article for comparison ---
    print("Embedding full articles...")
    fa_texts = []
    fa_ids = []
    for c in cases:
        if c["full_text"]:
            fa_texts.append(c["full_text"][:8000])
            fa_ids.append(c["id"])
    fa_embs = embed_texts(client, fa_texts) if fa_texts else []
    full_embeddings = {cid: emb for cid, emb in zip(fa_ids, fa_embs)}
    print(f"  Embedded {len(fa_embs)} full articles")

    # --- Run benchmarks at multiple thresholds ---
    thresholds = [0.3, 0.4, 0.5, 0.6]
    kt_summary = []
    fa_summary = []

    for t in thresholds:
        kt_res = run_benchmark(conn, cases, key_embeddings, t)
        fa_res = run_benchmark(conn, cases, full_embeddings, t)
        kt_avg = sum(r["recall"] for r in kt_res) / len(kt_res)
        fa_avg = sum(r["recall"] for r in fa_res) / len(fa_res)
        kt_summary.append((t, kt_avg, kt_avg >= 0.80))
        fa_summary.append((t, fa_avg, fa_avg >= 0.80))

    # --- Detailed results at threshold=0.5 ---
    kt_results = run_benchmark(conn, cases, key_embeddings, 0.5)
    fa_results = run_benchmark(conn, cases, full_embeddings, 0.5)
    kt_avg_05 = sum(r["recall"] for r in kt_results) / len(kt_results)
    fa_avg_05 = sum(r["recall"] for r in fa_results) / len(fa_results)

    # --- Print results ---
    print(f"\n{'='*70}")
    print(f"=== CR-Check Recall@10 벤치마크 v2 (article_key_text) ===")
    print(f"{'='*70}\n")

    print("[건별 결과 — threshold=0.5]")
    print("| # | Article ID | Expected (메타제외) | Retrieved (Top 3) | Hit | Recall | Δ vs 1차 |")
    print("|---|-----------|---------------------|-------------------|-----|--------|----------|")

    for i, (kt, fa) in enumerate(zip(kt_results, fa_results)):
        exp_str = ", ".join(kt["expected_no_meta"]) if kt["expected_no_meta"] else "(TN)"
        top3 = ", ".join(kt["retrieved_codes"][:3]) if kt["retrieved_codes"] else "(none)"
        hit_mark = "✅" if kt["recall"] >= 1.0 else ("⚠️" if kt["recall"] > 0 else "❌")
        if kt["is_tn"] and not kt["retrieved_codes"]:
            hit_mark = "✅"
        elif kt["is_tn"] and kt["retrieved_codes"]:
            hit_mark = "⚠️"
        delta = kt["recall"] - fa["recall"]
        delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}" if delta < 0 else "0.00"
        print(f"| {i+1} | {kt['id']} | {exp_str} | {top3} | {hit_mark} | {kt['recall']:.2f} | {delta_str} |")

    # Category-level
    cat_recalls = {}
    for r in kt_results:
        if r["is_tn"]:
            cat = "TN"
        else:
            first = r["expected_no_meta"][0] if r["expected_no_meta"] else "?"
            cat = "-".join(first.split("-")[:2])
        cat_recalls.setdefault(cat, []).append(r["recall"])

    print("\n[대분류별 Recall — key_text, threshold=0.5]")
    print("| 대분류 | 건수 | 평균 Recall@10 |")
    print("|--------|------|---------------|")
    for cat in sorted(cat_recalls.keys()):
        vals = cat_recalls[cat]
        name = CATEGORY_NAMES.get(cat, cat)
        print(f"| {cat} {name} | {len(vals)} | {sum(vals)/len(vals):.2f} |")

    # Threshold comparison
    print(f"\n[Threshold 비교표 — 1차(기사 전문) vs 2차(key_text)]")
    print("| Threshold | 1차 (full) | 2차 (key_text) | 개선폭 | 판정 |")
    print("|-----------|-----------|---------------|--------|------|")
    for (t, fa_avg, _), (_, kt_avg, kt_pass) in zip(fa_summary, kt_summary):
        delta = kt_avg - fa_avg
        mark = "✅" if kt_pass else "❌"
        star = " ★" if t == 0.5 else ""
        print(f"| {t}{star} | {fa_avg:.4f} | {kt_avg:.4f} | +{delta:.4f} | {mark} |")

    # Overall summary
    passed = kt_avg_05 >= 0.80
    print(f"\n[전체 요약]")
    print(f"- 전체 평균 Recall@10 (key_text, t=0.5): {kt_avg_05:.4f}")
    print(f"- 전체 평균 Recall@10 (full article, t=0.5): {fa_avg_05:.4f}")
    print(f"- 개선폭: +{kt_avg_05 - fa_avg_05:.4f}")
    print(f"- 목표: ≥ 0.80")
    print(f"- 판정: {'PASS ✅' if passed else 'FAIL ❌'}")

    # Low recall details
    low = [r for r in kt_results if r["recall"] < 0.5 and not r["is_tn"]]
    if low:
        print(f"\n[상세 분석 — Recall < 0.5인 건 (key_text)]")
        for r in low:
            print(f"\n  {r['id']}:")
            print(f"    Expected: {r['expected_no_meta']}")
            print(f"    key_text: {r['key_text'][:100]}...")
            print(f"    Retrieved:")
            for code, sim in r.get("retrieved", []):
                hit = "✅" if code in r["expected_no_meta"] else "  "
                print(f"      {hit} {code} (similarity={sim})")
            if not r.get("retrieved"):
                print(f"      (none)")

    # Best/worst improvements
    deltas = [(kt["id"], kt["recall"] - fa["recall"]) for kt, fa in zip(kt_results, fa_results) if not kt["is_tn"]]
    deltas.sort(key=lambda x: x[1], reverse=True)
    print(f"\n[개선폭 Top 5]")
    for cid, d in deltas[:5]:
        print(f"  {cid}: +{d:.2f}")
    print(f"\n[개선폭 Bottom 5]")
    for cid, d in deltas[-5:]:
        print(f"  {cid}: {'+' if d >= 0 else ''}{d:.2f}")

    # Save to M3_BENCHMARK_RESULTS.md
    results_path = os.path.join(base_dir, "docs", "M3_BENCHMARK_RESULTS.md")
    with open(results_path, "a", encoding="utf-8") as f:
        f.write("\n\n---\n\n## 2차 벤치마크 (article_key_text)\n\n")
        f.write(f"> 실행 일시: 2026-03-28\n")
        f.write(f"> 쿼리: golden_dataset_final.json의 article_key_text (GPT-4o 추출)\n\n")
        f.write("### Threshold 비교 (1차 vs 2차)\n\n")
        f.write("| Threshold | 1차 (full) | 2차 (key_text) | 개선폭 |\n")
        f.write("|-----------|-----------|---------------|--------|\n")
        for (t, fa_avg, _), (_, kt_avg, _) in zip(fa_summary, kt_summary):
            f.write(f"| {t} | {fa_avg:.4f} | {kt_avg:.4f} | +{kt_avg-fa_avg:.4f} |\n")
        f.write(f"\n### 전체 요약\n\n")
        f.write(f"- Recall@10 (key_text, t=0.5): **{kt_avg_05:.4f}**\n")
        f.write(f"- Recall@10 (full, t=0.5): {fa_avg_05:.4f}\n")
        f.write(f"- 판정: {'**PASS**' if passed else '**FAIL**'}\n")

    print(f"\n결과 추가 저장: {results_path}")
    conn.close()


if __name__ == "__main__":
    main()
