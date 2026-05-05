-- ============================================================
-- 20260502145125_master_migration.sql
-- STEP 2: DB 마이그레이션 (§8.1 신규 컬럼 + §8.2 트리거)
-- ============================================================
-- 작성일: 2026-05-02
-- 작성자: Claude Code CLI
-- 입력 문서:
--   - docs/MASTER_EXECUTION_PLAN_v1.0.md §8.1, §8.2
--   - docs/_scratch/step1_output_v3.md (107 leaf 코드 체계, structural 12)
--   - docs/STEP0A_PATTERN_DECISIONS_v1.0.md §5 structural 항목 목록
--   - supabase/seeds/ethics_codes_context_seed.sql (Phase 3 시드 — DDL 중복)
-- 적용 대상: public.patterns, public.ethics_codes, public.pattern_ethics_relations
-- 절대 원칙:
--   - DDL은 IF NOT EXISTS / OR REPLACE로 idempotent 보장.
--   - 본 마이그레이션은 DB 실행 전 단계. SQL Editor에서 기획자가 직접 실행 예정.
-- ============================================================

-- ------------------------------------------------------------
-- (A) patterns 테이블 신규 컬럼 추가 (§8.1)
-- ------------------------------------------------------------

ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS search_text TEXT;
ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS detection_strategy TEXT DEFAULT 'vector';
ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS report_framing TEXT;


-- ------------------------------------------------------------
-- (B) 메타 패턴 비활성화 (§8.1)
-- 메타패턴 추론은 비활성화 확정 (CLAUDE.md / SESSION_CONTEXT v44 §핵심 설계 결정)
-- ------------------------------------------------------------

UPDATE public.patterns
SET is_active = FALSE
WHERE is_meta_pattern = TRUE;


-- ------------------------------------------------------------
-- (C) structural 패턴 지정 — 기존 38개 코드 기준
-- step1_output_v3.md의 structural 12 leaves의 부모 코드 5개를 지정.
-- 신규 leaf(1-1-a 등)는 STEP 3 INSERT 이후이므로 본 마이그레이션 단계에서는 제외.
-- 부모 코드 매핑:
--   1-1 (사실 검증 부실)     → 1-1-a/b/d structural
--   3-1 (관점 다양성 부족)   → 3-1-a/b/c structural
--   5-1 (기사의 심층성 부족) → 5-1-a/e structural
--   6-2 (헤드라인 윤리 문제) → 6-2-a/b/c structural
--   6-3 (과장과 맥락 왜곡)   → 6-3-d structural (v3에서 vector→structural 전환)
-- 비고: MASTER §8.1 v1.0 예시(7-2,3-1,6-1,3-4)는 v3 갱신 전 추정값.
--      v3 structural 목록 기준으로 1-1·5-1·6-2 추가, 6-1·7-2·3-4 제외.
-- ------------------------------------------------------------

UPDATE public.patterns
SET detection_strategy = 'structural'
WHERE code IN ('1-1', '3-1', '5-1', '6-2', '6-3');


-- ------------------------------------------------------------
-- (D) ethics_codes 테이블 applicable_contexts 컬럼 추가 (§8.1)
-- 비고: ethics_codes_context_seed.sql §0에 동일 DDL 존재.
--      어느 쪽이든 먼저 실행되어도 IF NOT EXISTS로 idempotent.
-- ------------------------------------------------------------

ALTER TABLE public.ethics_codes
  ADD COLUMN IF NOT EXISTS applicable_contexts TEXT[];


-- ------------------------------------------------------------
-- (E) updated_at 트리거 함수 + 3개 테이블 적용 (§8.2)
-- patterns, ethics_codes, pattern_ethics_relations에 동일 트리거 적용.
-- CREATE OR REPLACE TRIGGER 사용 (PostgreSQL 14+, CR-Check은 PG 15+).
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER handle_updated_at
  BEFORE UPDATE ON public.patterns
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

CREATE OR REPLACE TRIGGER handle_updated_at
  BEFORE UPDATE ON public.ethics_codes
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

CREATE OR REPLACE TRIGGER handle_updated_at
  BEFORE UPDATE ON public.pattern_ethics_relations
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();


-- ============================================================
-- 검증 쿼리 (마이그레이션 적용 후 SQL Editor에서 수동 실행)
-- ============================================================

-- 검증 1: patterns 신규 컬럼 4개 존재
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'patterns'
--   AND column_name IN ('search_text', 'is_active', 'detection_strategy', 'report_framing');
-- 예상: 4행

-- 검증 2: 메타패턴 비활성화 건수
-- SELECT COUNT(*) FROM public.patterns
-- WHERE is_meta_pattern = TRUE AND is_active = FALSE;

-- 검증 3: structural 지정 결과 (5개 부모 코드)
-- SELECT code, detection_strategy FROM public.patterns
-- WHERE code IN ('1-1', '3-1', '5-1', '6-2', '6-3') ORDER BY code;
-- 예상: 모두 detection_strategy='structural'

-- 검증 4: ethics_codes applicable_contexts 컬럼
-- SELECT column_name FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'ethics_codes'
--   AND column_name = 'applicable_contexts';
-- 예상: 1행

-- 검증 5: 트리거 등록 (3개 테이블)
-- SELECT event_object_table, trigger_name FROM information_schema.triggers
-- WHERE trigger_schema = 'public' AND trigger_name = 'handle_updated_at'
-- ORDER BY event_object_table;
-- 예상: ethics_codes, pattern_ethics_relations, patterns
