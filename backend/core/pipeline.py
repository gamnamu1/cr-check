# backend/core/pipeline.py
"""
CR-Check — RAG 파이프라인 오케스트레이션

Sonnet Solo 1-Call 아키텍처:
기사 → 청킹 → 임베딩 → 벡터검색
  → Sonnet Solo(패턴 식별 + Devil's Advocate CoT)
  → 규범 조회(get_ethics_for_patterns RPC)
  → Sonnet(3종 리포트 + article_analysis, cite 태그)
  → CitationResolver(cite → 규범 원문 치환, 3종 각각 적용)
  → 최종 결과: { reports: {comprehensive, journalist, student}, article_analysis }
"""

import re
import time
import logging
from dataclasses import dataclass, field

from .chunker import chunk_article, Chunk
from .pattern_matcher import (
    match_patterns_solo,
    match_patterns_2call,  # deprecated 2-Call (비교용)
    match_patterns,  # deprecated 1-Call (비교용)
    PatternMatchResult,
)
from .report_generator import generate_report, ReportResult
from .citation_resolver import resolve_citations
from .meta_pattern_inference import check_meta_patterns
from .db import _get_supabase_config

logger = logging.getLogger(__name__)

_TN_MESSAGE = "분석 결과 문제적 보도관행이 발견되지 않았습니다."


@dataclass
class AnalysisResult:
    """전체 파이프라인 분석 결과."""
    # 청킹
    chunks: list[Chunk] = field(default_factory=list)
    chunk_count: int = 0
    avg_chunk_length: float = 0.0

    # 패턴 매칭
    pattern_result: PatternMatchResult = field(default_factory=PatternMatchResult)

    # 리포트
    report_result: ReportResult = field(default_factory=ReportResult)

    # 메타
    total_seconds: float = 0.0
    embedding_tokens: int = 0
    sonnet_input_tokens: int = 0
    sonnet_output_tokens: int = 0
    overall_assessment: str = ""  # Sonnet Solo 판단 근거 (아카이빙용 보존)
    meta_patterns: list = field(default_factory=list)  # MetaPatternResult 리스트


def analyze_article(
    article_text: str,
    run_sonnet: bool = True,
    vector_threshold: float = None,
) -> AnalysisResult:
    """기사 전문을 입력받아 Sonnet Solo 파이프라인을 실행.

    Args:
        article_text: 기사 원문 텍스트
        run_sonnet: False이면 패턴 식별 단계까지만 실행 (벤치마크용)
        vector_threshold: 벡터 검색 threshold (None이면 기본값)

    Returns:
        AnalysisResult
    """
    start = time.time()
    result = AnalysisResult()

    # 1. 청킹 — 실패 시 전체 텍스트를 단일 청크로 취급
    try:
        chunks = chunk_article(article_text)
    except Exception as e:
        logger.warning(f"청킹 실패, 전체 텍스트를 단일 청크로 사용: {e}")
        chunks = [Chunk(text=article_text, start=0, end=len(article_text), length=len(article_text))]

    result.chunks = chunks
    result.chunk_count = len(chunks)
    if chunks:
        result.avg_chunk_length = sum(c.length for c in chunks) / len(chunks)

    chunk_texts = [c.text for c in chunks]

    # 2. 패턴 매칭 — 실패 시 복구 불가 (main.py에서 500으로 처리)
    try:
        pm = match_patterns_solo(chunk_texts, article_text, threshold=vector_threshold)
    except Exception as e:
        logger.error(f"패턴 매칭 실패: {e}", exc_info=True)
        raise

    result.pattern_result = pm
    result.embedding_tokens = pm.embedding_tokens

    # overall_assessment 보존 (Phase D 아카이빙용)
    result.overall_assessment = pm.suspect_result.overall_assessment if pm.suspect_result else ""

    # 2.5 메타 패턴 추론 (Deterministic — DB 동적 조회)
    triggered_meta = []
    if pm.validated_pattern_codes:
        try:
            sb_url, sb_key = _get_supabase_config()
            meta_results = check_meta_patterns(
                detected_pattern_codes=list(pm.validated_pattern_codes),
                sb_url=sb_url,
                sb_key=sb_key,
            )
            triggered_meta = [m for m in meta_results if m.triggered]
            result.meta_patterns = meta_results
        except Exception as e:
            logger.warning(f"메타 패턴 추론 실패, 건너뜀: {e}")

    # 3. 리포트 생성 (Sonnet) — 선택적
    if run_sonnet and pm.validated_pattern_ids:
        haiku_dicts = [
            {
                "pattern_code": d.pattern_code,
                "matched_text": d.matched_text,
                "severity": d.severity,
                "reasoning": d.reasoning,
            }
            for d in pm.haiku_detections
            if d.pattern_code in pm.validated_pattern_codes
        ]
        try:
            rr = generate_report(
                article_text,
                pm.validated_pattern_ids,
                haiku_dicts,
                overall_assessment=result.overall_assessment,
                meta_patterns=triggered_meta,
            )
        except Exception as e:
            logger.error(f"리포트 생성 최종 실패, 에러 메시지 리포트 반환: {e}")
            rr = ReportResult(
                reports={
                    "comprehensive": "리포트 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    "journalist": "리포트 생성 중 오류가 발생했습니다.",
                    "student": "리포트 생성 중 오류가 발생했습니다.",
                }
            )

        # [Phase β] cite 태그 후치환 비활성화 — Sonnet이 규범을 직접 서술하므로 불필요
        # 복원이 필요하면 아래 주석을 해제하세요.
        # --- 결정론적 인용 후처리 (비활성화) ---
        # pre_citation_reports = {rt: rr.reports.get(rt, "") for rt in ["comprehensive", "journalist", "student"]}
        # hallucinated_refs_log = {}
        # for report_type in ["comprehensive", "journalist", "student"]:
        #     text = rr.reports.get(report_type, "")
        #     if text:
        #         try:
        #             resolved, hallucinated = resolve_citations(text, rr.ethics_refs or [])
        #             rr.reports[report_type] = resolved
        #             hallucinated_refs_log[report_type] = hallucinated if hallucinated else []
        #             if hallucinated:
        #                 logger.warning(f"[{report_type}] 환각 ref 제거: {hallucinated}")
        #         except Exception as e:
        #             logger.error(f"[{report_type}] CitationResolver 실패, cite 태그 제거: {e}")
        #             hallucinated_refs_log[report_type] = []
        #             text = re.sub(r'<cite\s+ref="[^"]*"\s*/>', '', text)
        #             text = re.sub(r'<cite\s+ref="[^"]*"\s*>\s*</cite>', '', text)
        #             text = re.sub(r' {2,}', ' ', text)
        #             rr.reports[report_type] = text

        result.report_result = rr
        result.sonnet_input_tokens = rr.input_tokens
        result.sonnet_output_tokens = rr.output_tokens
    elif run_sonnet and not pm.validated_pattern_ids:
        result.report_result = ReportResult(
            reports={
                "comprehensive": _TN_MESSAGE,
                "journalist": _TN_MESSAGE,
                "student": _TN_MESSAGE,
            }
        )

    result.total_seconds = time.time() - start

    # ── 진단용 JSON 덤프 ────────────────────────────────────────
    try:
        import json as _json
        from datetime import datetime as _dt
        from pathlib import Path as _Path

        _diag_dir = _Path(__file__).parent.parent / "diagnostics"
        _diag_dir.mkdir(exist_ok=True)
        _ts = _dt.now().strftime("%Y%m%d_%H%M%S")

        # Checkpoint 1: 청킹
        _cp1 = {
            "chunk_count": result.chunk_count,
            "avg_chunk_length": round(result.avg_chunk_length, 1),
            "chunks_preview": [
                {"index": i, "length": c.length, "preview": c.text[:80]}
                for i, c in enumerate(result.chunks)
            ],
        }

        # Checkpoint 2: 벡터 검색
        _cp2 = {
            "candidate_count": len(pm.vector_candidates),
            "vector_candidates": [
                {"pattern_code": vc.pattern_code, "pattern_name": vc.pattern_name, "similarity": round(vc.similarity, 4)}
                for vc in pm.vector_candidates
            ],
        }

        # Checkpoint 3: 패턴 식별
        _cp3 = {
            "overall_assessment": result.overall_assessment,
            "haiku_detections": [
                {"pattern_code": d.pattern_code, "matched_text": d.matched_text, "severity": d.severity, "reasoning": d.reasoning}
                for d in pm.haiku_detections
            ],
            "validated_pattern_codes": list(pm.validated_pattern_codes),
            "hallucinated_codes": list(pm.hallucinated_codes),
            "haiku_raw_response": pm.haiku_raw_response,
        }

        # Checkpoint 4, 5: 리포트 관련 (run_sonnet=True이고 패턴이 확정된 경우에만)
        _cp4 = {}
        _cp5 = {}
        if run_sonnet and pm.validated_pattern_ids:
            # CP4: 규범 조회
            _ethics = rr.ethics_refs or []
            _patterns_with_ethics = set(er.pattern_code for er in _ethics)
            _patterns_without = [pc for pc in pm.validated_pattern_codes if pc not in _patterns_with_ethics]
            _cp4 = {
                "ethics_ref_count": len(_ethics),
                "patterns_without_ethics": _patterns_without,
                "ethics_refs": [
                    {
                        "pattern_code": er.pattern_code,
                        "ethics_code": er.ethics_code,
                        "ethics_title": er.ethics_title,
                        "ethics_tier": er.ethics_tier,
                        "full_text_length": len(er.ethics_full_text),
                        "full_text_preview": er.ethics_full_text[:300],
                        "relation_type": er.relation_type,
                        "strength": er.strength,
                    }
                    for er in _ethics
                ],
            }

            # CP5: 리포트 (cite 태그 후치환 비활성화 상태에서는 pre/post가 동일)
            _cp5 = {
                "pre_citation_reports": {rt: rr.reports.get(rt, "") for rt in ["comprehensive", "journalist", "student"]},
                "post_citation_reports": {rt: rr.reports.get(rt, "") for rt in ["comprehensive", "journalist", "student"]},
                "hallucinated_refs_per_report": {},
                "sonnet_raw_response": rr.sonnet_raw_response,
            }

        _diag = {
            "timestamp": _ts,
            "total_seconds": round(result.total_seconds, 2),
            "checkpoint_1_chunks": _cp1,
            "checkpoint_2_vector": _cp2,
            "checkpoint_3_pattern": _cp3,
            "checkpoint_4_ethics": _cp4,
            "checkpoint_5_report": _cp5,
        }

        _diag_path = _diag_dir / f"diagnostic_{_ts}.json"
        _diag_path.write_text(_json.dumps(_diag, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"진단 덤프 저장: {_diag_path}")

    except Exception as _diag_err:
        logger.warning(f"진단 덤프 실패 (파이프라인에 영향 없음): {_diag_err}")
    # ── 진단용 JSON 덤프 끝 ─────────────────────────────────────

    return result
