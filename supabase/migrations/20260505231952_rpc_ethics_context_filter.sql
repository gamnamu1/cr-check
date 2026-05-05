-- 작성일: 2026-05-05
-- 작성자: Claude Code CLI
-- 변경 내용: get_ethics_for_patterns에 article_context 파라미터 추가,
--            applicable_contexts 필터 + weak/exception_of 제외 필터 적용

-- 함수 시그니처 변경(파라미터 추가)이므로 기존 함수를 명시적으로 DROP한 후 재생성.
-- (CREATE OR REPLACE FUNCTION은 동일 시그니처에서만 동작하므로,
--  파라미터를 추가하면 별개 함수로 인식되어 기존 1-arg 함수가 잔존하게 됨.)
DROP FUNCTION IF EXISTS public.get_ethics_for_patterns(BIGINT[]);

CREATE OR REPLACE FUNCTION public.get_ethics_for_patterns(
  confirmed_pattern_ids BIGINT[],
  article_context TEXT DEFAULT 'general'
)
RETURNS TABLE (
  pattern_id BIGINT,
  pattern_code TEXT,
  ethics_code_id BIGINT,
  ethics_code TEXT,
  ethics_title TEXT,
  ethics_full_text TEXT,
  ethics_tier INT,
  relation_type TEXT,
  strength TEXT,
  reasoning TEXT
) AS $$
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
$$ LANGUAGE plpgsql STABLE;
