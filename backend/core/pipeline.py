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

    # 1. 청킹
    chunks = chunk_article(article_text)
    result.chunks = chunks
    result.chunk_count = len(chunks)
    if chunks:
        result.avg_chunk_length = sum(c.length for c in chunks) / len(chunks)

    chunk_texts = [c.text for c in chunks]

    # 2. 패턴 매칭 (Sonnet Solo: 게이트 없음 + Devil's Advocate CoT)
    pm = match_patterns_solo(chunk_texts, article_text, threshold=vector_threshold)
    result.pattern_result = pm
    result.embedding_tokens = pm.embedding_tokens

    # overall_assessment 보존 (Phase D 아카이빙용)
    result.overall_assessment = pm.suspect_result.overall_assessment if pm.suspect_result else ""

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
        rr = generate_report(
            article_text,
            pm.validated_pattern_ids,
            haiku_dicts,
            overall_assessment=result.overall_assessment,
        )

        # 결정론적 인용 후처리: cite 태그 → 규범 원문 치환 (3종 각각)
        for report_type in ["comprehensive", "journalist", "student"]:
            text = rr.reports.get(report_type, "")
            if text:
                try:
                    resolved, hallucinated = resolve_citations(text, rr.ethics_refs or [])
                    rr.reports[report_type] = resolved
                    if hallucinated:
                        logger.warning(f"[{report_type}] 환각 ref 제거: {hallucinated}")
                except Exception as e:
                    logger.error(f"[{report_type}] CitationResolver 실패, cite 태그 제거: {e}")
                    text = re.sub(r'<cite\s+ref="[^"]*"\s*/>', '', text)
                    text = re.sub(r'<cite\s+ref="[^"]*"\s*>\s*</cite>', '', text)
                    text = re.sub(r' {2,}', ' ', text)
                    rr.reports[report_type] = text

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
    return result
