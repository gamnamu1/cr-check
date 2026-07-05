-- =====================================================================
-- [실행 방식 경고 — 반드시 준수]
-- 이 파일은 Supabase SQL Editor에서 기획자가 "수동" 실행하는 마이그레이션이다.
-- `supabase db push` / `supabase migration up` 으로 실행하지 말 것.
--   이유: 운영 DB의 schema_migrations(4건)와 저장소 마이그레이션 파일(12개)이
--         이미 drift 상태다. db push는 미기록 마이그레이션까지 일괄 적용하려 하여
--         예측 불가한 변경을 일으킬 수 있다.
-- 전제: 수동 실행 + schema_migrations 수동 INSERT(아래 주석)로 이력을 1건만 정확히 기록한다.
-- =====================================================================

-- T0: Phase 1 포렌식 축약본 저장 컬럼.
-- 관측 전용(JSONB) — 프런트엔드·API 응답에 노출 금지.

BEGIN;

ALTER TABLE public.analysis_results
  ADD COLUMN IF NOT EXISTS phase1_forensic JSONB;

COMMIT;

NOTIFY pgrst, 'reload schema';

-- [기획자 수동 실행 — 이력 동기화]
-- INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
-- VALUES ('20260705000000', 'phase1_forensic',
--         ARRAY['ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS phase1_forensic JSONB;']);

-- [적용 검증]
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_schema='public' AND table_name='analysis_results' AND column_name='phase1_forensic';
