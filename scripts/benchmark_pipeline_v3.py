#!/usr/bin/env python3
"""
M6 벤치마크 — Sonnet Solo 파이프라인.

지표:
- Candidate Recall: 벡터 검색이 정답 패턴을 후보에 포함시켰는가
- Final Recall: Sonnet Solo 최종 확정 패턴이 정답과 일치하는가
- Final Precision: Sonnet Solo 확정 패턴 중 실제 정답 비율
- Category Recall: 대분류 수준 일치율
- TN FP Rate: True Negative에서 False Positive 발생 비율

Legacy 지표 (--legacy 모드에서만 표시):
- Haiku Suspect Accuracy: Haiku 의심 대분류가 기대 패턴 대분류를 포함하는 비율
- Haiku TN Pass Rate: TN에서 Haiku가 []를 반환한 비율

사용법:
  SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py
  SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids B-11 A-06 E-11
  SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --legacy  # 2-Call 출력 형식
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from datetime import date
from dotenv import load_dotenv

# .env 로드
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.pipeline import analyze_article

logger = logging.getLogger(__name__)

ARTICLE_TEXTS_DIR = Path(__file__).parent.parent.parent / "Golden_Data_Set_Pool" / "article_texts"


# ── 데이터 로드 ──────────────────────────────────────────────────

def load_golden_dataset() -> dict:
    p = Path(__file__).parent.parent / "docs" / "golden_dataset_final.json"
    with open(p) as f:
        return json.load(f)


def load_labels() -> dict:
    p = Path(__file__).parent.parent / "docs" / "golden_dataset_labels.json"
    with open(p) as f:
        return json.load(f)


def get_expected(labels: dict, cid: str) -> list[str]:
    for lb in labels.get("labels", []):
        if lb["candidate_id"] == cid:
            return [p["pattern_id"] for p in lb.get("expected_patterns", [])]
    return []


# ── 결과 구조 ──────────────────────────────────────────────────

@dataclass
class CaseResult:
    candidate_id: str
    title: str
    is_tn: bool
    expected_patterns: list[str]
    vector_candidate_codes: list[str] = field(default_factory=list)
    haiku_confirmed_codes: list[str] = field(default_factory=list)
    hallucinated_codes: list[str] = field(default_factory=list)
    candidate_recall: float | None = None
    final_recall: float | None = None
    final_precision: float | None = None
    category_recall: float | None = None
    is_false_positive: bool = False
    seconds: float = 0.0
    embedding_tokens: int = 0
    article_chars: int = 0
    article_source: str = ""
    chunk_count: int = 0
    skipped: bool = False
    skip_reason: str = ""
    # Solo / Legacy 공용
    suspect_categories: list[str] = field(default_factory=list)
    suspect_assessment: str = ""
    suspect_accuracy: float | None = None  # Legacy: Haiku 의심 대분류 정확도
    pipeline_path: str = ""  # "sonnet_solo_empty" / "sonnet_solo_detect" / legacy paths


# ── 벤치마크 실행 ──────────────────────────────────────────────

def run_benchmark(filter_ids: list[str] | None = None, model_override: str | None = None):
    gd = load_golden_dataset()
    labels = load_labels()
    candidates = gd["candidates"]

    if filter_ids:
        candidates = [c for c in candidates if c["candidate_id"] in filter_ids]

    if model_override:
        import core.pattern_matcher as pm_module
        pm_module.SONNET_MODEL = model_override
        print(f"  ⚠️ 모델 오버라이드: {model_override}")

    results: list[CaseResult] = []
    total_start = time.time()

    for c in candidates:
        cid = c["candidate_id"]
        title = c.get("title", "")[:50]
        is_tn = c.get("is_true_negative", False)
        expected = get_expected(labels, cid)

        cr = CaseResult(
            candidate_id=cid, title=title, is_tn=is_tn, expected_patterns=expected,
        )

        article_file = ARTICLE_TEXTS_DIR / f"{cid}_article.txt"
        if article_file.exists():
            article_text = article_file.read_text(encoding="utf-8").strip()
            cr.article_source = "full"
        else:
            article_text = c.get("article_key_text", "")
            cr.article_source = "key_text" if article_text else ""

        if not article_text:
            cr.skipped = True
            cr.skip_reason = "기사 텍스트 없음"
            results.append(cr)
            print(f"  [{cid}] SKIP: {cr.skip_reason}")
            continue

        cr.article_chars = len(article_text)
        print(f"  [{cid}] 분석 중... ({cr.article_chars}자)", end="", flush=True)

        try:
            result = analyze_article(article_text, run_sonnet=False)
        except Exception as e:
            cr.skipped = True
            cr.skip_reason = f"오류: {e}"
            results.append(cr)
            print(f" ERROR: {e}")
            continue

        pm = result.pattern_result
        cr.vector_candidate_codes = [vc.pattern_code for vc in pm.vector_candidates]
        cr.haiku_confirmed_codes = list(pm.validated_pattern_codes)
        cr.hallucinated_codes = list(pm.hallucinated_codes)
        cr.seconds = result.total_seconds
        cr.embedding_tokens = result.embedding_tokens
        cr.chunk_count = result.chunk_count

        # overall_assessment 추출
        suspect = pm.suspect_result
        if suspect:
            cr.suspect_categories = suspect.suspect_categories
            cr.suspect_assessment = suspect.overall_assessment  # 전체 기록

        # 파이프라인 경로
        cr.pipeline_path = "sonnet_solo_detect" if cr.haiku_confirmed_codes else "sonnet_solo_empty"

        if is_tn:
            cr.is_false_positive = len(cr.haiku_confirmed_codes) > 0
            cr.candidate_recall = None
            cr.final_recall = None
            cr.final_precision = None
            cr.category_recall = None
            cr.suspect_accuracy = None
        else:
            expected_set = set(expected)
            vec_set = set(cr.vector_candidate_codes)
            haiku_set = set(cr.haiku_confirmed_codes)

            if expected_set:
                cr.candidate_recall = len(expected_set & vec_set) / len(expected_set)
                cr.final_recall = len(expected_set & haiku_set) / len(expected_set)
            else:
                cr.candidate_recall = 1.0
                cr.final_recall = 1.0

            if haiku_set:
                cr.final_precision = len(expected_set & haiku_set) / len(haiku_set)
            else:
                cr.final_precision = 1.0 if not expected_set else 0.0

            # Category Recall
            expected_majors = set()
            for p in expected:
                parts = p.split("-")
                if len(parts) >= 2:
                    expected_majors.add(f"{parts[0]}-{parts[1]}")

            haiku_majors = set()
            for p in cr.haiku_confirmed_codes:
                parts = p.split("-")
                if len(parts) >= 2:
                    haiku_majors.add(f"{parts[0]}-{parts[1]}")

            if expected_majors:
                cr.category_recall = len(expected_majors & haiku_majors) / len(expected_majors)
            else:
                cr.category_recall = 1.0

            # Suspect Accuracy (legacy 호환)
            suspect_set = set(cr.suspect_categories)
            if expected_majors:
                cr.suspect_accuracy = len(expected_majors & suspect_set) / len(expected_majors)
            else:
                cr.suspect_accuracy = 1.0

        results.append(cr)
        if cr.is_tn:
            status = f"TN-Solo:{'FP!' if cr.is_false_positive else '[]'}"
        else:
            status = f"CR={cr.candidate_recall:.2f} FR={cr.final_recall:.2f} FP={cr.final_precision:.2f}"
        print(f" {cr.seconds:.1f}s {cr.chunk_count}ch | {status}")

        time.sleep(1)

    total_seconds = time.time() - total_start
    return results, total_seconds


# ── 결과 출력 (Solo 모드) ──────────────────────────────────────

def generate_report_solo(results: list[CaseResult], total_seconds: float):
    """소넷 Solo 모드 리포트 생성."""
    tp_results = [r for r in results if not r.is_tn and not r.skipped]
    tn_results = [r for r in results if r.is_tn and not r.skipped]
    skipped = [r for r in results if r.skipped]

    cr_vals = [r.candidate_recall for r in tp_results if r.candidate_recall is not None]
    fr_vals = [r.final_recall for r in tp_results if r.final_recall is not None]
    fp_vals = [r.final_precision for r in tp_results if r.final_precision is not None]
    cat_vals = [r.category_recall for r in tp_results if r.category_recall is not None]
    avg_cr = sum(cr_vals) / len(cr_vals) if cr_vals else 0
    avg_fr = sum(fr_vals) / len(fr_vals) if fr_vals else 0
    avg_fp = sum(fp_vals) / len(fp_vals) if fp_vals else 0
    avg_cat = sum(cat_vals) / len(cat_vals) if cat_vals else 0

    tn_fp_count = sum(1 for r in tn_results if r.is_false_positive)
    tn_fp_rate = tn_fp_count / len(tn_results) if tn_results else 0

    # 비용 추정 (Solo: Sonnet 1회만)
    sonnet_calls = sum(1 for r in results if not r.skipped)
    sonnet_cost = sonnet_calls * 0.03
    total_emb_tokens = sum(r.embedding_tokens for r in results if not r.skipped)

    # 대분류별 집계
    category_stats = {}
    for r in tp_results:
        if r.expected_patterns:
            parts = r.expected_patterns[0].split("-")
            major = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else parts[0]
        else:
            major = "unknown"
        if major not in category_stats:
            category_stats[major] = {"cr": [], "fr": [], "fp": [], "cat": [], "count": 0}
        if r.candidate_recall is not None: category_stats[major]["cr"].append(r.candidate_recall)
        if r.final_recall is not None: category_stats[major]["fr"].append(r.final_recall)
        if r.final_precision is not None: category_stats[major]["fp"].append(r.final_precision)
        if r.category_recall is not None: category_stats[major]["cat"].append(r.category_recall)
        category_stats[major]["count"] += 1

    lines = []
    lines.append("# M6 벤치마크 결과 — Sonnet Solo")
    lines.append("")
    lines.append(f"> 실행일: {date.today()}")
    lines.append(f"> 파이프라인: 청킹→벡터검색→Sonnet Solo(Devil's Advocate CoT)")
    lines.append(f"> 모델: Sonnet 4.6 (Solo 1-Call)")
    lines.append(f"> 입력: article_full_text (기사 전문)")
    lines.append("")

    lines.append("## 전체 요약")
    lines.append("")
    lines.append("| 지표 | 결과 | 판정 |")
    lines.append("|------|------|------|")
    lines.append(f"| Candidate Recall | {avg_cr:.1%} | — |")
    lines.append(f"| Final Recall | {avg_fr:.1%} | — |")
    lines.append(f"| Final Precision | {avg_fp:.1%} | — |")
    lines.append(f"| Category Recall | {avg_cat:.1%} | — |")
    if tn_results:
        lines.append(f"| TN FP Rate | {tn_fp_rate:.1%} ({tn_fp_count}/{len(tn_results)}) | {'✅' if tn_fp_rate <= 0.33 else '⚠️'} |")
    lines.append("")

    lines.append(f"- TP: {len(tp_results)}, TN: {len(tn_results)}, SKIP: {len(skipped)}")
    lines.append(f"- 소요: {total_seconds:.1f}초, 임베딩 토큰: {total_emb_tokens}")
    lines.append(f"- 비용 추정: Sonnet {sonnet_calls}건 ~${sonnet_cost:.3f}")
    lines.append("")

    # 대분류별
    lines.append("## 대분류별 성능")
    lines.append("")
    lines.append("| 대분류 | 건수 | CR | FR | FP | Cat R |")
    lines.append("|--------|------|-----|-----|-----|-------|")
    for cat in sorted(category_stats.keys()):
        s = category_stats[cat]
        n = s["count"]
        cr = sum(s["cr"]) / len(s["cr"]) if s["cr"] else 0
        fr = sum(s["fr"]) / len(s["fr"]) if s["fr"] else 0
        fp = sum(s["fp"]) / len(s["fp"]) if s["fp"] else 0
        ct = sum(s["cat"]) / len(s["cat"]) if s["cat"] else 0
        lines.append(f"| {cat} | {n} | {cr:.0%} | {fr:.0%} | {fp:.0%} | {ct:.0%} |")
    lines.append("")

    # 건별 상세
    lines.append("## 건별 상세")
    lines.append("")
    for r in results:
        if r.skipped:
            lines.append(f"### {r.candidate_id} — SKIP ({r.skip_reason})")
            lines.append("")
            continue

        status = "TN" if r.is_tn else "TP"
        fp_flag = " ⚠️ FP" if r.is_false_positive else ""
        lines.append(f"### {r.candidate_id} ({status}{fp_flag})")
        lines.append(f"- **제목**: {r.title}")
        lines.append(f"- **입력**: {r.article_chars}자 ({r.article_source}), {r.chunk_count} 청크")
        lines.append(f"- **overall_assessment**: {r.suspect_assessment}")
        path_desc = {
            "sonnet_solo_empty": "Sonnet Solo → 양질 판정 (detections=[])",
            "sonnet_solo_detect": "Sonnet Solo → 패턴 발견",
        }
        lines.append(f"- **경로**: {path_desc.get(r.pipeline_path, r.pipeline_path)}")
        if not r.is_tn:
            lines.append(f"- **기대**: {r.expected_patterns}")
            lines.append(f"- **벡터 후보**: {r.vector_candidate_codes}")
            lines.append(f"- **최종 확정**: {r.haiku_confirmed_codes}")
            if r.hallucinated_codes:
                lines.append(f"- **환각 제거**: {r.hallucinated_codes}")
            lines.append(f"- CR={r.candidate_recall:.2f} FR={r.final_recall:.2f} FP={r.final_precision:.2f} Cat={r.category_recall:.2f}")
            expected_set = set(r.expected_patterns)
            haiku_set = set(r.haiku_confirmed_codes)
            hits = expected_set & haiku_set
            misses = expected_set - haiku_set
            fps = haiku_set - expected_set
            if hits: lines.append(f"- HIT: {sorted(hits)}")
            if misses: lines.append(f"- MISS: {sorted(misses)}")
            if fps: lines.append(f"- FP: {sorted(fps)}")
        else:
            lines.append(f"- **최종 감지**: {r.haiku_confirmed_codes if r.haiku_confirmed_codes else '없음 (정상)'}")
        lines.append(f"- 소요: {r.seconds:.1f}초")
        lines.append("")

    report = "\n".join(lines)
    out_path = Path(__file__).parent.parent / "docs" / "M6_BENCHMARK_RESULTS.md"
    with open(out_path, "w") as f:
        f.write(report)
    return report, str(out_path)


# ── 결과 출력 (Legacy 모드) ──────────────────────────────────

def generate_report_legacy(results: list[CaseResult], total_seconds: float):
    """Legacy 2-Call 출력 형식. M5 결과 파일에 저장."""
    tp_results = [r for r in results if not r.is_tn and not r.skipped]
    tn_results = [r for r in results if r.is_tn and not r.skipped]
    skipped = [r for r in results if r.skipped]

    cr_vals = [r.candidate_recall for r in tp_results if r.candidate_recall is not None]
    fr_vals = [r.final_recall for r in tp_results if r.final_recall is not None]
    fp_vals = [r.final_precision for r in tp_results if r.final_precision is not None]
    cat_vals = [r.category_recall for r in tp_results if r.category_recall is not None]
    sus_vals = [r.suspect_accuracy for r in tp_results if r.suspect_accuracy is not None]
    avg_cr = sum(cr_vals) / len(cr_vals) if cr_vals else 0
    avg_fr = sum(fr_vals) / len(fr_vals) if fr_vals else 0
    avg_fp = sum(fp_vals) / len(fp_vals) if fp_vals else 0
    avg_cat = sum(cat_vals) / len(cat_vals) if cat_vals else 0
    avg_sus = sum(sus_vals) / len(sus_vals) if sus_vals else 0

    tn_fp_count = sum(1 for r in tn_results if r.is_false_positive)
    tn_fp_rate = tn_fp_count / len(tn_results) if tn_results else 0
    tn_haiku_pass = sum(1 for r in tn_results if r.pipeline_path == "sonnet_solo_empty")
    tn_haiku_pass_rate = tn_haiku_pass / len(tn_results) if tn_results else 0

    haiku_calls = sum(1 for r in results if not r.skipped)
    sonnet_calls = sum(1 for r in results if not r.skipped and r.pipeline_path != "haiku_pass")
    haiku_cost = haiku_calls * 0.004
    sonnet_cost = sonnet_calls * 0.03
    total_cost = haiku_cost + sonnet_cost
    total_emb_tokens = sum(r.embedding_tokens for r in results if not r.skipped)

    # 대분류별 집계
    category_stats = {}
    for r in tp_results:
        if r.expected_patterns:
            parts = r.expected_patterns[0].split("-")
            major = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else parts[0]
        else:
            major = "unknown"
        if major not in category_stats:
            category_stats[major] = {"cr": [], "fr": [], "fp": [], "cat": [], "sus": [], "count": 0}
        if r.candidate_recall is not None: category_stats[major]["cr"].append(r.candidate_recall)
        if r.final_recall is not None: category_stats[major]["fr"].append(r.final_recall)
        if r.final_precision is not None: category_stats[major]["fp"].append(r.final_precision)
        if r.category_recall is not None: category_stats[major]["cat"].append(r.category_recall)
        if r.suspect_accuracy is not None: category_stats[major]["sus"].append(r.suspect_accuracy)
        category_stats[major]["count"] += 1

    lines = []
    lines.append("# M5 벤치마크 결과 — 2-Call 파이프라인")
    lines.append("")
    lines.append(f"> 실행일: {date.today()}")
    lines.append(f"> 파이프라인: 청킹→벡터검색→Haiku(대분류 의심)→Sonnet(소분류 검증)")
    lines.append(f"> 모델: Haiku 4.5 (1st) + Sonnet 4.6 (2nd)")
    lines.append(f"> 입력: article_full_text (기사 전문)")
    lines.append("")

    lines.append("## 전체 요약")
    lines.append("")
    lines.append("| 지표 | 목표 | 결과 | 판정 |")
    lines.append("|------|------|------|------|")
    lines.append(f"| Candidate Recall | ≥ 70% | {avg_cr:.1%} | {'✅' if avg_cr >= 0.70 else '❌'} |")
    lines.append(f"| Final Recall | ≥ 80% | {avg_fr:.1%} | {'✅' if avg_fr >= 0.80 else '❌'} |")
    lines.append(f"| Final Precision | ≥ 60% | {avg_fp:.1%} | {'✅' if avg_fp >= 0.60 else '❌'} |")
    lines.append(f"| Category Recall | 참고 | {avg_cat:.1%} | — |")
    lines.append(f"| **Haiku Suspect Accuracy** | 참고 | {avg_sus:.1%} | — |")
    if tn_results:
        lines.append(f"| TN FP Rate | < 30% | {tn_fp_rate:.1%} ({tn_fp_count}/{len(tn_results)}) | {'✅' if tn_fp_rate < 0.30 else '⚠️'} |")
        lines.append(f"| **Haiku TN Pass Rate** | 참고 | {tn_haiku_pass_rate:.1%} ({tn_haiku_pass}/{len(tn_results)}) | — |")
    lines.append("")

    lines.append(f"- TP: {len(tp_results)}, TN: {len(tn_results)}, SKIP: {len(skipped)}")
    lines.append(f"- 소요: {total_seconds:.1f}초, 임베딩 토큰: {total_emb_tokens}")
    lines.append(f"- 비용 추정: Haiku {haiku_calls}건 ~${haiku_cost:.3f} + Sonnet {sonnet_calls}건 ~${sonnet_cost:.3f} = **~${total_cost:.3f}**")
    lines.append("")

    # 대분류별
    lines.append("## 대분류별 성능")
    lines.append("")
    lines.append("| 대분류 | 건수 | CR | FR | FP | Cat R | Suspect Acc |")
    lines.append("|--------|------|-----|-----|-----|-------|------------|")
    for cat in sorted(category_stats.keys()):
        s = category_stats[cat]
        n = s["count"]
        cr = sum(s["cr"]) / len(s["cr"]) if s["cr"] else 0
        fr = sum(s["fr"]) / len(s["fr"]) if s["fr"] else 0
        fp = sum(s["fp"]) / len(s["fp"]) if s["fp"] else 0
        ct = sum(s["cat"]) / len(s["cat"]) if s["cat"] else 0
        su = sum(s["sus"]) / len(s["sus"]) if s["sus"] else 0
        lines.append(f"| {cat} | {n} | {cr:.0%} | {fr:.0%} | {fp:.0%} | {ct:.0%} | {su:.0%} |")
    lines.append("")

    # 건별 상세
    lines.append("## 건별 상세")
    lines.append("")
    for r in results:
        if r.skipped:
            lines.append(f"### {r.candidate_id} — SKIP ({r.skip_reason})")
            lines.append("")
            continue

        status = "TN" if r.is_tn else "TP"
        fp_flag = " ⚠️ FP" if r.is_false_positive else ""
        lines.append(f"### {r.candidate_id} ({status}{fp_flag})")
        lines.append(f"- **제목**: {r.title}")
        lines.append(f"- **입력**: {r.article_chars}자 ({r.article_source}), {r.chunk_count} 청크")
        lines.append(f"- **Haiku 의심**: {r.suspect_categories if r.suspect_categories else '[] (양질 판정)'}")
        lines.append(f"- **Haiku 총평**: {r.suspect_assessment[:80]}")
        path_desc = {"haiku_pass": "Haiku 양질 판정 → Sonnet 미호출",
                     "sonnet_empty": "Haiku 의심 → Sonnet 검증 → 문제 없음",
                     "sonnet_detect": "Haiku 의심 → Sonnet 검증 → 패턴 발견",
                     "sonnet_solo_empty": "Sonnet Solo → 양질 판정 (detections=[])",
                     "sonnet_solo_detect": "Sonnet Solo → 패턴 발견"}
        lines.append(f"- **경로**: {path_desc.get(r.pipeline_path, r.pipeline_path)}")
        if not r.is_tn:
            lines.append(f"- **기대**: {r.expected_patterns}")
            lines.append(f"- **벡터 후보**: {r.vector_candidate_codes}")
            lines.append(f"- **최종 확정**: {r.haiku_confirmed_codes}")
            if r.hallucinated_codes:
                lines.append(f"- **환각 제거**: {r.hallucinated_codes}")
            lines.append(f"- CR={r.candidate_recall:.2f} FR={r.final_recall:.2f} FP={r.final_precision:.2f} Cat={r.category_recall:.2f} SusAcc={r.suspect_accuracy:.2f}")
            expected_set = set(r.expected_patterns)
            haiku_set = set(r.haiku_confirmed_codes)
            hits = expected_set & haiku_set
            misses = expected_set - haiku_set
            fps = haiku_set - expected_set
            if hits: lines.append(f"- HIT: {sorted(hits)}")
            if misses: lines.append(f"- MISS: {sorted(misses)}")
            if fps: lines.append(f"- FP: {sorted(fps)}")
        else:
            lines.append(f"- **최종 감지**: {r.haiku_confirmed_codes if r.haiku_confirmed_codes else '없음 (정상)'}")
        lines.append(f"- 소요: {r.seconds:.1f}초")
        lines.append("")

    report = "\n".join(lines)
    out_path = Path(__file__).parent.parent / "docs" / "M5_BENCHMARK_RESULTS.md"
    with open(out_path, "w") as f:
        f.write(report)
    return report, str(out_path)


# ── 메인 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="M6 벤치마크 — Sonnet Solo 파이프라인")
    parser.add_argument("--ids", nargs="*", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--legacy", action="store_true", help="Legacy 2-Call 출력 형식")
    args = parser.parse_args()

    filter_label = f" (필터: {args.ids})" if args.ids else " (전체 26건)"
    mode_label = "Legacy 2-Call" if args.legacy else "Sonnet Solo"
    print("=" * 60)
    print(f"M6 벤치마크 — {mode_label}{filter_label}")
    print("=" * 60)

    results, total_seconds = run_benchmark(filter_ids=args.ids, model_override=args.model)

    if args.legacy:
        report, out_path = generate_report_legacy(results, total_seconds)
    else:
        report, out_path = generate_report_solo(results, total_seconds)

    print("\n" + "=" * 60)
    print("벤치마크 완료:")
    print("=" * 60)

    tp_results = [r for r in results if not r.is_tn and not r.skipped]
    tn_results = [r for r in results if r.is_tn and not r.skipped]

    if tp_results:
        cr_vals = [r.candidate_recall for r in tp_results if r.candidate_recall is not None]
        fr_vals = [r.final_recall for r in tp_results if r.final_recall is not None]
        fp_vals = [r.final_precision for r in tp_results if r.final_precision is not None]
        print(f"\n  Candidate Recall:      {sum(cr_vals)/len(cr_vals):.1%}" if cr_vals else "")
        print(f"  Final Recall:          {sum(fr_vals)/len(fr_vals):.1%}" if fr_vals else "")
        print(f"  Final Precision:       {sum(fp_vals)/len(fp_vals):.1%}" if fp_vals else "")

    if tn_results:
        tn_fp = sum(1 for r in tn_results if r.is_false_positive)
        print(f"  TN FP Rate:            {tn_fp}/{len(tn_results)}")

    print(f"\n  총 소요: {total_seconds:.1f}초")
    print(f"  결과 저장: {out_path}")


if __name__ == "__main__":
    main()
