-- Phase D: analysis_results 테이블 확장
-- 작성일: 2026-04-06
-- 목적:
--   1. URL 공유용 share_id 추가
--   2. 리포트 메타 정보 컬럼 추가 (article_analysis, overall_assessment, meta_patterns)
--   3. phase1_model 기본값을 Sonnet 4.5로 변경 (현재 활성 모델)
--   4. detected_categories → detected_patterns RENAME (기존 데이터 0건 확인 완료)

BEGIN;

-- ============================================
-- 1. 신규 컬럼 추가
-- ============================================

-- 1-1. share_id: URL 공유용 12자 토큰 (secrets.token_urlsafe(9))
ALTER TABLE public.analysis_results
  ADD COLUMN share_id TEXT;

-- 기존 행이 0건이라는 전제 하에 NOT NULL + UNIQUE 제약을 바로 적용
ALTER TABLE public.analysis_results
  ALTER COLUMN share_id SET NOT NULL;

ALTER TABLE public.analysis_results
  ADD CONSTRAINT analysis_results_share_id_key UNIQUE (share_id);

-- 1-2. article_analysis: 기사 메타분석 (기사 유형, 구성 요소, 편집 구조 등)
ALTER TABLE public.analysis_results
  ADD COLUMN article_analysis JSONB;

-- 1-3. overall_assessment: Sonnet Solo의 Devil's Advocate CoT 판단 근거 (아카이빙용)
ALTER TABLE public.analysis_results
  ADD COLUMN overall_assessment TEXT;

-- 1-4. meta_patterns: 메타 패턴 추론 결과 (1-4-1 외부 압력, 1-4-2 상업적 동기)
ALTER TABLE public.analysis_results
  ADD COLUMN meta_patterns JSONB;

-- ============================================
-- 2. phase1_model 기본값 변경 (Haiku → Sonnet 4.5)
-- ============================================

ALTER TABLE public.analysis_results
  ALTER COLUMN phase1_model SET DEFAULT 'claude-sonnet-4-5-20250929';

-- ============================================
-- 3. detected_categories → detected_patterns RENAME
--    (기존 데이터 0건 확인 완료, 안전한 RENAME)
-- ============================================

ALTER TABLE public.analysis_results
  RENAME COLUMN detected_categories TO detected_patterns;

-- ============================================
-- 4. share_id 유니크 인덱스 (UNIQUE 제약과 별도 명시적 인덱스)
-- ============================================

CREATE UNIQUE INDEX idx_analysis_share_id
  ON public.analysis_results(share_id);

-- ============================================
-- 5. 컬럼 주석 갱신
-- ============================================

COMMENT ON COLUMN public.analysis_results.detected_patterns IS
  'Phase 1에서 탐지된 문제 패턴 목록 (pattern_code, matched_text, severity, reasoning)';

COMMENT ON COLUMN public.analysis_results.share_id IS
  'URL 공유용 12자 토큰 (secrets.token_urlsafe(9))';

COMMENT ON COLUMN public.analysis_results.article_analysis IS
  '기사 메타분석 (articleType, articleElements, editStructure, reportingMethod, contentFlow)';

COMMENT ON COLUMN public.analysis_results.overall_assessment IS
  'Sonnet Solo의 Devil''s Advocate CoT 판단 근거 (양질/문제 양면 검토)';

COMMENT ON COLUMN public.analysis_results.meta_patterns IS
  '메타 패턴 추론 결과 (1-4-1 외부 압력, 1-4-2 상업적 동기 등)';

COMMIT;
