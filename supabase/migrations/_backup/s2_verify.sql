-- =====================================================================
-- [검증 레벨 분리 원칙]
-- 이 파일은 기획자가 S2 마이그레이션을 Supabase SQL Editor에서 수동 실행한 뒤
-- 검증할 때 사용하는 절차 파일이다.
--
-- CLI는 이 파일을 작성만 하며, SQL/REST/PostgREST 호출을 직접 실행하지 않는다.
--
-- SQL Editor에서 실행 가능한 검증:
--   1. 함수 ACL/owner/security_definer 확인
--   2. RETURNS 시그니처 12컬럼 확인
--   3. active leaf + 실제 매핑 패턴 선택
--   4. RPC SQL sanity
--   5. citation_audit 컬럼 확인
--
-- 환경 의존 검증:
--   PostgREST 실호출은 CLI 작성 단계에서는 실행하지 않는다.
--   그러나 운영 DB에 S2 마이그레이션을 실제 적용한 뒤에는
--   S2 최종 승인 전 필수 확인 항목으로 본다.
--
-- PostgREST 호출 환경이 준비되지 않았다면 S2를 PASS로 처리하지 말고
-- "검증 보류"로 남긴다.
-- =====================================================================
-- 게이트: Wave 1 · S2 (DB 계약 변경) — 검증 전용.
-- 기대값 요약: (1) 반환 컬럼 12개, (2) ethics_source/ethics_article_number 포함,
--             (3) analysis_results.citation_audit(jsonb) 존재.

-- ---------------------------------------------------------------------
-- 0. 함수 ACL / owner / security_definer / 주요 role EXECUTE 권한 확인
-- ---------------------------------------------------------------------
-- 권장 사용:
--   마이그레이션 실행 "전" 이 쿼리 결과를 캡처한다.
--   마이그레이션 실행 "후" 같은 쿼리를 다시 실행해 비교한다.
--
-- 이유:
--   DROP FUNCTION → CREATE FUNCTION은 함수 권한/GRANT 상태에 영향을 줄 수 있다.
--   information_schema.routine_privileges는 함수 오버로드/PUBLIC 권한 표현에서
--   해석이 애매할 수 있으므로, 신뢰 기준은 pg_proc.proacl과 has_function_privilege()로 둔다.
--
-- 해석:
--   proacl = NULL은 곧바로 "권한 없음"을 뜻하지 않는다. default privilege 상태일 수 있다.
--   따라서 anon/authenticated/service_role의 has_function_privilege 결과를 함께 본다.
--
-- 주의:
--   이 쿼리는 권한을 변경하지 않는다. 확인만 한다.
--   권한 차이가 발견되면 임의 GRANT를 추가하지 말고 감리자에게 공유한다.
--   PostgREST 실호출이 성공하면 실사용 RPC 권한은 통과로 본다.
SELECT
  p.oid::regprocedure::text AS function_signature,
  pg_get_userbyid(p.proowner) AS owner,
  p.prosecdef AS security_definer,
  COALESCE(p.proacl::text, '<NULL: default privileges>') AS acl,
  has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_execute,
  has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated_execute,
  has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_role_execute
FROM pg_proc p
WHERE p.oid = 'public.get_ethics_for_patterns(bigint[], text)'::regprocedure;

-- 보조 참고용: information_schema routine privileges
-- 주의: PUBLIC 권한/오버로드 표현에서 pg_proc.proacl보다 덜 직접적이므로 참고용으로만 본다.
SELECT grantee, privilege_type
FROM information_schema.routine_privileges
WHERE routine_schema = 'public'
  AND routine_name = 'get_ethics_for_patterns'
ORDER BY grantee, privilege_type;

-- ---------------------------------------------------------------------
-- 1. SQL 층위: RETURNS 시그니처 12컬럼 + 신규 2컬럼 포함 확인
-- ---------------------------------------------------------------------
SELECT pg_get_function_result(
  'public.get_ethics_for_patterns(bigint[], text)'::regprocedure
) AS rpc_return_signature;

-- 기대:
-- TABLE(
--   pattern_id bigint,
--   pattern_code text,
--   ethics_code_id bigint,
--   ethics_code text,
--   ethics_title text,
--   ethics_source text,
--   ethics_article_number text,
--   ethics_full_text text,
--   ethics_tier integer,
--   relation_type text,
--   strength text,
--   reasoning text
-- )

-- 보조: 반환 OUT 컬럼을 행으로 펼쳐 개수/이름/순서 확인 (기대: 12행)
SELECT
  p.ordinality        AS col_pos,
  p.proargname        AS col_name,
  format_type(p.proargtype, NULL) AS col_type
FROM pg_proc pr
CROSS JOIN LATERAL unnest(pr.proallargtypes, pr.proargnames, pr.proargmodes)
     WITH ORDINALITY AS p(proargtype, proargname, proargmode, ordinality)
WHERE pr.oid = 'public.get_ethics_for_patterns(bigint[], text)'::regprocedure
  AND p.proargmode = 't'   -- TABLE(...) OUT 컬럼만
ORDER BY p.ordinality;

-- ---------------------------------------------------------------------
-- 2. sanity에 사용할 active leaf + article_number 실값 있는 직접 매핑 패턴 선택
-- ---------------------------------------------------------------------
-- 목적:
--   ethics_source / ethics_article_number 신규 컬럼에 실제 값이 흐르는지 확인하기 위해,
--   article_number가 NULL이 아닌 직접 매핑 패턴을 우선 선택한다.
--
-- 주의:
--   이 쿼리가 0행이면 article_number 실값 보장 조건이 너무 엄격한 것이다.
--   그 경우 임의로 조건을 바꾸지 말고 감리자에게 공유한다.
--   필요 시 article_number IS NOT NULL 조건을 완화한 fallback sanity 쿼리를 별도 승인 후 사용한다.
WITH chosen_pattern AS (
  SELECT
    per.pattern_id,
    p.code AS pattern_code,
    ec.code AS ethics_code,
    ec.source AS ethics_source,
    ec.article_number AS ethics_article_number,
    per.relation_type,
    per.strength
  FROM public.pattern_ethics_relations per
  JOIN public.patterns p ON p.id = per.pattern_id
  JOIN public.active_ethics_codes ec ON ec.id = per.ethics_code_id
  WHERE p.is_active = true
    AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
    AND ec.is_citable = true
    AND ec.article_number IS NOT NULL
    AND (
      ec.applicable_contexts IS NULL
      OR 'all' = ANY(ec.applicable_contexts)
      OR 'general' = ANY(ec.applicable_contexts)
    )
    AND per.strength != 'weak'
    AND per.relation_type = 'violates'
  ORDER BY per.pattern_id
  LIMIT 1
)
SELECT *
FROM chosen_pattern;

-- 기대:
-- 1행 반환.
-- ethics_source가 채워져 있고 ethics_article_number가 NULL이 아님.

-- ---------------------------------------------------------------------
-- 3. SQL 층위 RPC 실값 sanity
-- ---------------------------------------------------------------------
-- 목적:
--   public.get_ethics_for_patterns(..., 'general') 호출 결과에
--   ethics_source / ethics_article_number 컬럼이 존재하고,
--   가능한 경우 실제 값이 흘러오는지 확인한다.
WITH chosen_pattern AS (
  SELECT per.pattern_id
  FROM public.pattern_ethics_relations per
  JOIN public.patterns p ON p.id = per.pattern_id
  JOIN public.active_ethics_codes ec ON ec.id = per.ethics_code_id
  WHERE p.is_active = true
    AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
    AND ec.is_citable = true
    AND ec.article_number IS NOT NULL
    AND (
      ec.applicable_contexts IS NULL
      OR 'all' = ANY(ec.applicable_contexts)
      OR 'general' = ANY(ec.applicable_contexts)
    )
    AND per.strength != 'weak'
    AND per.relation_type = 'violates'
  ORDER BY per.pattern_id
  LIMIT 1
)
SELECT
  pattern_code,
  ethics_code,
  ethics_source,
  ethics_article_number,
  ethics_tier,
  relation_type
FROM public.get_ethics_for_patterns(
  ARRAY[(SELECT pattern_id FROM chosen_pattern)]::bigint[],
  'general'
)
ORDER BY ethics_tier
LIMIT 10;

-- 기대:
-- 1행 이상 반환.
-- ethics_source 컬럼 존재 및 값 확인.
-- ethics_article_number 컬럼 존재 및 가능하면 실값 확인.
-- chosen_pattern이 0행이면 이 쿼리도 유의미하지 않으므로, 감리자에게 공유한다.

-- ---------------------------------------------------------------------
-- 3-A. fallback sanity 후보 — 감리자 승인 후 사용
-- ---------------------------------------------------------------------
-- 위 chosen_pattern이 0행인 경우에만 검토한다.
-- article_number 실값 보장은 포기하되, 실제 매핑 active leaf 패턴으로
-- ethics_source / ethics_article_number 컬럼 존재 여부를 확인한다.
--
-- 감리자 승인 전에는 아래 조건 완화 쿼리를 S2 PASS 근거로 사용하지 않는다.
--
-- WITH chosen_pattern AS (
--   SELECT per.pattern_id
--   FROM public.pattern_ethics_relations per
--   JOIN public.patterns p ON p.id = per.pattern_id
--   JOIN public.active_ethics_codes ec ON ec.id = per.ethics_code_id
--   WHERE p.is_active = true
--     AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
--     AND ec.is_citable = true
--     AND (
--       ec.applicable_contexts IS NULL
--       OR 'all' = ANY(ec.applicable_contexts)
--       OR 'general' = ANY(ec.applicable_contexts)
--     )
--     AND per.strength != 'weak'
--   ORDER BY per.pattern_id
--   LIMIT 1
-- )
-- SELECT pattern_code, ethics_code, ethics_source, ethics_article_number, ethics_tier, relation_type
-- FROM public.get_ethics_for_patterns(
--   ARRAY[(SELECT pattern_id FROM chosen_pattern)]::bigint[],
--   'general'
-- )
-- ORDER BY ethics_tier
-- LIMIT 10;

-- ---------------------------------------------------------------------
-- 4. citation_audit 컬럼 추가 확인
-- ---------------------------------------------------------------------
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'analysis_results'
  AND column_name = 'citation_audit';

-- 기대:
-- citation_audit | jsonb

-- ---------------------------------------------------------------------
-- 5. PostgREST 층위 검증 절차 — S2 최종 승인 전 필수
-- ---------------------------------------------------------------------
-- SQL Editor만으로는 충분하지 않다.
-- 이번 변경은 PostgREST RPC 응답 JSON 계약을 바꾸는 작업이므로,
-- 운영 DB에 마이그레이션을 실제 적용한 뒤에는 S2 최종 승인 전
-- PostgREST 실호출을 반드시 확인한다.
--
-- 단, CLI 산출물 작성 단계에서는 이 호출을 실행하지 않는다.
-- CLI는 이 절차를 주석으로 남기기만 한다.
--
-- 절차:
-- 1. 마이그레이션 파일 실행 완료
-- 2. NOTIFY pgrst, 'reload schema'; 실행 완료
-- 3. 수 초 대기
-- 4. 위 2번 chosen_pattern에서 확인한 pattern_id로 REST 또는 supabase-py 호출
--
-- REST 예시:
-- POST {SUPABASE_URL}/rest/v1/rpc/get_ethics_for_patterns
-- Content-Type: application/json
-- apikey: <anon 또는 service role key>
-- Authorization: Bearer <동일 key 또는 세션 토큰>
--
-- body:
-- {
--   "confirmed_pattern_ids": [<chosen_pattern.pattern_id>],
--   "article_context": "general"
-- }
--
-- 기대:
-- 응답 JSON 객체에 아래 두 키가 존재한다.
-- - "ethics_source"
-- - "ethics_article_number"
--
-- supabase-py 예시:
-- supabase.rpc(
--     "get_ethics_for_patterns",
--     {
--         "confirmed_pattern_ids": [pattern_id],
--         "article_context": "general",
--     },
-- ).execute()
--
-- 주의:
-- 실제 key 값은 이 파일에 기록하지 않는다.
--
-- 실패 시:
-- 1. 응답에 ethics_source / ethics_article_number가 없으면
--    스키마 캐시 미리로드 가능성이 있다.
--    NOTIFY pgrst, 'reload schema'; 재실행 후 수 초 대기하고 재확인한다.
--
-- 2. 권한 오류가 발생하면
--    위 0번 ACL 쿼리의 마이그레이션 전/후 결과를 비교해 감리자에게 공유한다.
--    임의 GRANT를 추가하지 않는다.
--
-- 3. PostgREST 호출 환경이 준비되지 않았다면
--    S2를 PASS로 처리하지 말고 "검증 보류"로 남긴다.
