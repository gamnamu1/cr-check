-- ============================================================================
-- Migration A · 보안 하드닝: 뷰 invoker 전환 + 함수 search_path 고정
-- ============================================================================
-- 이력 version: 20260714051150
--
-- [실행 방식 경고 — 반드시 준수]
-- Supabase SQL Editor에서 기획자가 "수동" 실행하는 마이그레이션이다.
-- `supabase db push` / `supabase migration up` 으로 운영 DB에 실행하지 말 것.
-- (schema_migrations drift — 20260622 관례 준수. 이력은 수동 INSERT.)
--
-- [배경] Supabase Advisor 경고 해소:
--   1. active_ethics_codes 뷰가 SECURITY DEFINER로 동작(reloptions=None) →
--      호출자 권한을 우회하여 하위 테이블 정책을 무력화할 수 있음.
--   2. public 함수 6개의 proconfig=None → search_path 미고정으로
--      악성 스키마 주입에 노출될 수 있음(function search_path mutable).
--
-- [내용]
--   A-1) active_ethics_codes → security_invoker=on
--        (기존 ethics_codes_history와 동일 방식. 컬럼·필터·반환 행 불변.)
--   A-2) 6개 함수에 search_path = public, pg_temp 고정
--        - 함수 본문 재작성 없음 (identity args만 참조).
--        - owner/execute grants/security mode/volatility/parallel/반환 타입 불변.
--        - vector extension은 public 스키마에 설치되어 있어(<=> 연산자 포함)
--          search_pattern_candidates가 정상 해석된다(정합 확인 완료).
--
-- [멱등성] SET (security_invoker = on)과 ALTER FUNCTION ... SET search_path는
--   반복 실행에 안전하다. 재실행 시 상태 그대로.
-- ============================================================================

BEGIN;

-- ─── A-1. active_ethics_codes 뷰: security_invoker=on ─────────────────────
-- 정의(SELECT ... FROM ethics_codes WHERE is_active=true)와 22개 컬럼은 유지.
-- 반환 행 = ethics_codes.is_active=true 인 394행. Migration 전후 동일해야 한다.
ALTER VIEW public.active_ethics_codes SET (security_invoker = on);

-- ─── A-2. 6개 함수 search_path 고정 ───────────────────────────────────────
-- identity_args는 pg_get_function_identity_arguments()로 사전 확인:
--   search_pattern_candidates(vector, double precision, integer)
--   get_ethics_for_patterns(bigint[], text)
--   get_trending_articles(integer)
--   get_publisher_stats()
--   get_overall_stats()
--   handle_updated_at()

ALTER FUNCTION public.search_pattern_candidates(vector, double precision, integer)
  SET search_path = public, pg_temp;

ALTER FUNCTION public.get_ethics_for_patterns(bigint[], text)
  SET search_path = public, pg_temp;

ALTER FUNCTION public.get_trending_articles(integer)
  SET search_path = public, pg_temp;

ALTER FUNCTION public.get_publisher_stats()
  SET search_path = public, pg_temp;

ALTER FUNCTION public.get_overall_stats()
  SET search_path = public, pg_temp;

ALTER FUNCTION public.handle_updated_at()
  SET search_path = public, pg_temp;

-- ─── 사후 검증(같은 트랜잭션): 6개 함수 모두 proconfig에 search_path 존재 ─
DO $$
DECLARE
  n_missing INT;
BEGIN
  SELECT count(*) INTO n_missing
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'public'
    AND p.proname IN (
      'search_pattern_candidates','get_ethics_for_patterns',
      'get_trending_articles','get_publisher_stats',
      'get_overall_stats','handle_updated_at'
    )
    AND NOT EXISTS (
      SELECT 1 FROM unnest(coalesce(p.proconfig, ARRAY[]::text[])) cfg
      WHERE cfg LIKE 'search_path=%'
    );
  IF n_missing > 0 THEN
    RAISE EXCEPTION 'search_path missing on % target function(s)', n_missing;
  END IF;
END $$;

-- ─── 사후 검증: active_ethics_codes reloptions에 security_invoker=on 존재 ─
DO $$
DECLARE
  ok BOOLEAN;
BEGIN
  SELECT 'security_invoker=on' = ANY(coalesce(c.reloptions, ARRAY[]::text[]))
    INTO ok
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relname = 'active_ethics_codes';
  IF NOT ok THEN
    RAISE EXCEPTION 'active_ethics_codes.security_invoker=on not applied';
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';

-- ============================================================================
-- [ROLLBACK] Migration A 원복 — 각 변경 역방향 1개씩.
-- 되돌리려면 아래 SQL을 순차 실행.
-- ----------------------------------------------------------------------------
-- ALTER VIEW public.active_ethics_codes RESET (security_invoker);
-- ALTER FUNCTION public.search_pattern_candidates(vector, double precision, integer) RESET search_path;
-- ALTER FUNCTION public.get_ethics_for_patterns(bigint[], text)                       RESET search_path;
-- ALTER FUNCTION public.get_trending_articles(integer)                                RESET search_path;
-- ALTER FUNCTION public.get_publisher_stats()                                         RESET search_path;
-- ALTER FUNCTION public.get_overall_stats()                                           RESET search_path;
-- ALTER FUNCTION public.handle_updated_at()                                           RESET search_path;
-- NOTIFY pgrst, 'reload schema';
-- ============================================================================
