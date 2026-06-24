-- =====================================================================
-- [실행 방식 경고 — 반드시 준수]
-- 이 파일은 Supabase SQL Editor에서 기획자가 "수동" 실행하는 마이그레이션이다.
-- `supabase db push` / `supabase migration up` 으로 실행하지 말 것.
--   이유: 운영 DB의 schema_migrations(3건)와 저장소 마이그레이션 파일(11개)이
--         이미 drift 상태다. db push는 미기록 마이그레이션까지 일괄 적용하려 하여
--         예측 불가한 변경을 일으킬 수 있다.
-- 전제: 수동 실행 + schema_migrations 수동 INSERT(별도 파일)로 이력을 1건만 정확히 기록한다.
-- =====================================================================
BEGIN;

-- RETURNS TABLE 시그니처(컬럼 추가)는 CREATE OR REPLACE로 변경 불가 → DROP 필수.
-- 같은 트랜잭션 안에서 DROP→CREATE하므로 CREATE 실패 시 DROP도 롤백되어 구 함수가 보존된다.
DROP FUNCTION IF EXISTS public.get_ethics_for_patterns(BIGINT[], TEXT);

CREATE OR REPLACE FUNCTION public.get_ethics_for_patterns(
  confirmed_pattern_ids bigint[],
  article_context text DEFAULT 'general'::text
)
RETURNS TABLE(
  pattern_id bigint,
  pattern_code text,
  ethics_code_id bigint,
  ethics_code text,
  ethics_title text,
  ethics_source text,            -- ★ 신규 (RETURNS TABLE)
  ethics_article_number text,    -- ★ 신규 (RETURNS TABLE)
  ethics_full_text text,
  ethics_tier integer,
  relation_type text,
  strength text,
  reasoning text
)
LANGUAGE plpgsql
STABLE
AS $function$
BEGIN
  RETURN QUERY
  WITH RECURSIVE direct_codes AS (
    SELECT per.pattern_id, p.code AS p_code,
           ec.id AS ec_id, ec.code AS ec_code, ec.title,
           ec.source, ec.article_number,           -- ★ 신규 (edit 1: direct_codes)
           ec.full_text, ec.tier,
           per.relation_type, per.strength, per.reasoning
    FROM public.pattern_ethics_relations per
    JOIN public.patterns p ON per.pattern_id = p.id
    JOIN public.active_ethics_codes ec ON per.ethics_code_id = ec.id
    WHERE per.pattern_id = ANY(confirmed_pattern_ids)
      AND ec.is_citable = TRUE
      AND (
        ec.applicable_contexts IS NULL
        OR 'all' = ANY(ec.applicable_contexts)
        OR article_context = ANY(ec.applicable_contexts)
      )
      AND per.strength != 'weak'
      AND per.relation_type != 'exception_of'
  ),
  parent_chain AS (
    SELECT dc.pattern_id, dc.p_code,
           ec.id, ec.code, ec.title,
           ec.source, ec.article_number,           -- ★ 신규 (edit 2: parent_chain base arm)
           ec.full_text, ec.tier, ec.parent_code_id,
           1 AS depth
    FROM public.ethics_codes ec
    JOIN direct_codes dc ON ec.id = dc.ec_id
    WHERE ec.is_active = TRUE
    UNION
    SELECT child.pattern_id, child.p_code,
           parent.id, parent.code, parent.title,
           parent.source, parent.article_number,   -- ★ 신규 (edit 3: parent_chain recursive arm)
           parent.full_text, parent.tier, parent.parent_code_id,
           child.depth + 1
    FROM public.ethics_codes parent
    JOIN parent_chain child ON parent.id = child.parent_code_id
    WHERE parent.is_active = TRUE
      AND parent.is_citable = TRUE
      AND child.depth < 5
      AND (
        parent.applicable_contexts IS NULL
        OR 'all' = ANY(parent.applicable_contexts)
        OR article_context = ANY(parent.applicable_contexts)
      )
  )
  SELECT dc.pattern_id, dc.p_code,
         dc.ec_id, dc.ec_code, dc.title,
         dc.source, dc.article_number,             -- ★ 신규 (edit 4: 최종 직접 분기)
         dc.full_text, dc.tier,
         dc.relation_type, dc.strength, dc.reasoning
  FROM direct_codes dc
  UNION
  SELECT DISTINCT pc.pattern_id, pc.p_code,
         pc.id, pc.code, pc.title,
         pc.source, pc.article_number,             -- ★ 신규 (edit 5: 최종 롤업 분기)
         pc.full_text, pc.tier,
         'related_to'::TEXT, 'moderate'::TEXT, 'parent chain rollup'::TEXT
  FROM parent_chain pc
  WHERE NOT EXISTS (
    SELECT 1 FROM direct_codes dc
    WHERE dc.ec_id = pc.id
      AND dc.pattern_id = pc.pattern_id
  )
  ORDER BY tier;
END;
$function$;

-- 인용 감사 로그 적재 컬럼 (S6에서 사용, 여기서 동봉)
ALTER TABLE public.analysis_results
  ADD COLUMN IF NOT EXISTS citation_audit JSONB;

COMMIT;

NOTIFY pgrst, 'reload schema';
