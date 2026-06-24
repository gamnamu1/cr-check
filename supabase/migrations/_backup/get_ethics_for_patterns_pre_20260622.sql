-- [S0 백업] get_ethics_for_patterns 현행 정의 캡처
-- 게이트: Wave 1 · S0 (코드 변경 0, 조회 전용)
-- 기획자가 아래 쿼리를 Supabase SQL Editor에서 실행 후 결과를 === 안에 붙여넣으세요.
-- ※ CLI 직접 실행 금지 — 운영 DB DML/DDL/조회 실행은 기획자 수동 수행 원칙.

SELECT pg_get_functiondef(
  'public.get_ethics_for_patterns(bigint[], text)'::regprocedure
);

-- === 기획자 실행 결과 (2026-06-22 캡처) ===
-- ⚠ 아래는 백업 보관용 캡처 정의다. 실행 가능한 SQL로 남기지 않기 위해
--   블록 주석 /* ... */ 안에 비활성 상태로 보관한다 (S0 = SELECT 전용).
/*
CREATE OR REPLACE FUNCTION public.get_ethics_for_patterns(confirmed_pattern_ids bigint[], article_context text DEFAULT 'general'::text)
 RETURNS TABLE(pattern_id bigint, pattern_code text, ethics_code_id bigint, ethics_code text, ethics_title text, ethics_full_text text, ethics_tier integer, relation_type text, strength text, reasoning text)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  RETURN QUERY
  WITH RECURSIVE direct_codes AS (
    -- 1단계: pattern_ethics_relations에서 직접 연결된 규범
    -- [STEP 4-C] applicable_contexts 필터(A) + weak/exception_of 제외 필터(B) 추가
    SELECT per.pattern_id, p.code AS p_code,
           ec.id AS ec_id, ec.code AS ec_code, ec.title, ec.full_text, ec.tier,
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
    -- 2단계: 직접 규범의 parent chain을 재귀적으로 수집 (구체→포괄 롤업)
    -- [C-01 fix] pattern_id를 base case에서 상속하여 CROSS JOIN 제거
    -- [W-01 fix] depth 카운터로 무한 루프 방지 (최대 5)
    -- [STEP 4-C] 재귀 SELECT(UNION 하단)에 applicable_contexts 필터(A) 추가.
    --            parent_chain에는 per가 없으므로 필터 B(strength/relation_type)는 적용하지 않음.
    --            롤업 행은 마지막 SELECT에서 'related_to'/'moderate'로 강제 주입되어 충돌 없음.
    SELECT dc.pattern_id, dc.p_code,
           ec.id, ec.code, ec.title, ec.full_text, ec.tier, ec.parent_code_id,
           1 AS depth
    FROM public.ethics_codes ec
    JOIN direct_codes dc ON ec.id = dc.ec_id
    WHERE ec.is_active = TRUE
    UNION
    SELECT child.pattern_id, child.p_code,
           parent.id, parent.code, parent.title, parent.full_text, parent.tier, parent.parent_code_id,
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
  -- 직접 관계 규범 반환
  SELECT dc.pattern_id, dc.p_code,
         dc.ec_id, dc.ec_code, dc.title, dc.full_text, dc.tier,
         dc.relation_type, dc.strength, dc.reasoning
  FROM direct_codes dc
  UNION
  -- 롤업 상위 규범 반환 (직접 관계에 없는 parent만, 패턴별 범위 대조)
  SELECT DISTINCT pc.pattern_id, pc.p_code,
         pc.id, pc.code, pc.title, pc.full_text, pc.tier,
         'related_to'::TEXT, 'moderate'::TEXT, 'parent chain rollup'::TEXT
  FROM parent_chain pc
  WHERE NOT EXISTS (
    SELECT 1 FROM direct_codes dc
    WHERE dc.ec_id = pc.id
      AND dc.pattern_id = pc.pattern_id
  )
  ORDER BY tier;
END;
$function$
*/
-- === 끝 ===
