-- =====================================================================
-- [S2 이력 기록] schema_migrations에 이번 1건만 정확히 기록
-- 게이트: Wave 1 · S2 (DB 계약 변경)
-- [실행 방식 경고 — 반드시 준수]
--   마이그레이션 본문(20260622000000_...sql)을 SQL Editor에서 수동 실행해 성공한
--   "직후"에만 이 INSERT를 실행한다. 본문 적용 전에 먼저 실행하지 말 것.
--   schema_migrations(운영 3건)와 저장소 파일(11+개)이 이미 drift 상태이므로,
--   db push로 일괄 적용하지 말고 이 1건만 수동 기록한다.
-- 전제: 자동 INSERT 절대 금지 — 기획자가 Supabase SQL Editor에서 직접 실행.
-- =====================================================================

-- statements 배열에는 본문에서 "실행한 트랜잭션 구간(BEGIN…COMMIT)"만 기록한다.
-- NOTIFY pgrst 는 트랜잭션 밖 부수효과이므로 이력 statements에서 제외한다.
INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
VALUES (
  '20260622000000',
  'rpc_source_article_number_and_citation_audit',
  ARRAY[
$migration$
BEGIN;

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
  ethics_source text,
  ethics_article_number text,
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
           ec.source, ec.article_number,
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
           ec.source, ec.article_number,
           ec.full_text, ec.tier, ec.parent_code_id,
           1 AS depth
    FROM public.ethics_codes ec
    JOIN direct_codes dc ON ec.id = dc.ec_id
    WHERE ec.is_active = TRUE
    UNION
    SELECT child.pattern_id, child.p_code,
           parent.id, parent.code, parent.title,
           parent.source, parent.article_number,
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
         dc.source, dc.article_number,
         dc.full_text, dc.tier,
         dc.relation_type, dc.strength, dc.reasoning
  FROM direct_codes dc
  UNION
  SELECT DISTINCT pc.pattern_id, pc.p_code,
         pc.id, pc.code, pc.title,
         pc.source, pc.article_number,
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

ALTER TABLE public.analysis_results
  ADD COLUMN IF NOT EXISTS citation_audit JSONB;

COMMIT;
$migration$
  ]
);
