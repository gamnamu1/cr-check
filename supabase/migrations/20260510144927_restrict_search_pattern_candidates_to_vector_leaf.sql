-- STEP 6 Phase B-7: search_pattern_candidates RPC 4개 필터 적용
-- 현재 함수는 is_meta_pattern=FALSE 단일 필터만 적용되어 있어,
-- 구버전 코드·부모 코드·inactive 패턴·structural 패턴까지 후보로 반환된다.
-- 4개 필터(active, vector, leaf 정규식, description_embedding NOT NULL)를 추가하여
-- STEP 5-A에서 정합화된 active vector leaf 64건만 후보로 반환되도록 제한한다.
--
-- 적용은 기획자가 SQL Editor에서 직접 수행한다.
-- 적용 후 NOTIFY pgrst, 'reload schema'; 와 pg_get_functiondef 확인 필수 (Phase B-9, B-10).

CREATE OR REPLACE FUNCTION public.search_pattern_candidates(
  query_embedding vector,
  match_threshold double precision DEFAULT 0.2,
  match_count integer DEFAULT 7
)
RETURNS TABLE (
  pattern_id BIGINT,
  pattern_code TEXT,
  pattern_name TEXT,
  pattern_description TEXT,
  similarity double precision
) AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.code, p.name, p.description,
         1 - (p.description_embedding <=> query_embedding) AS similarity
  FROM public.patterns p
  WHERE p.is_meta_pattern = FALSE
    AND p.is_active = TRUE
    AND p.detection_strategy = 'vector'
    AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
    AND p.description_embedding IS NOT NULL
    AND 1 - (p.description_embedding <=> query_embedding) > match_threshold
  ORDER BY (1 - (p.description_embedding <=> query_embedding)) DESC
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;
