-- ============================================================================
-- Migration B · 보안 하드닝: 사설 결과 테이블의 전체 공개 SELECT 정책 제거
-- ============================================================================
-- 이력 version: 20260714051151
--
-- [실행 방식 경고 — 반드시 준수]
-- Supabase SQL Editor에서 기획자가 "수동" 실행하는 마이그레이션이다.
-- `supabase db push` / `supabase migration up` 로 운영 DB에 실행하지 말 것.
--
-- [배경]
--   articles / analysis_results / analysis_ethics_snapshot 세 테이블은
--   RLS가 활성화되어 있으나 `roles=public, cmd=SELECT, qual=true` 형태의
--   전체 공개 정책이 남아 있어 실질적으로 익명 접근이 가능한 상태였다.
--   프론트엔드는 Supabase 클라이언트를 사용하지 않고 FastAPI 백엔드를
--   경유하며(service_role 사용), 백엔드 이외의 접근 경로는 필요하지 않다.
--
-- [내용]
--   B) 아래 3개 정책만 제거. 다른 테이블·다른 정책·RLS 활성 상태는 불변.
--     - anon_read_articles                       ON public.articles
--     - anon_read_analysis_results               ON public.analysis_results
--     - anon_read_analysis_ethics_snapshot       ON public.analysis_ethics_snapshot
--
-- [영향]
--   - service_role(백엔드): RLS bypass — 저장·캐시 조회·share_id 조회
--     모두 그대로 동작.
--   - anon/authenticated: 세 테이블에 대한 SELECT 반환 0행.
--     현재 저장소 전수 검색에서 프론트는 Supabase 직접 조회 경로가 없고,
--     3개 통계 RPC(get_trending_articles / get_publisher_stats /
--     get_overall_stats)는 SECURITY INVOKER이므로 anon 호출 시
--     자체 SELECT가 RLS에 걸려 빈 결과를 반환. 다만 호출처가 코드베이스에
--     한 곳도 없어 실사용 영향은 없다(별도 발견 사항).
--
-- [범위 밖 — 명시적 유지]
--   - patterns / ethics_codes / ethics_code_hierarchy /
--     pattern_ethics_relations / pattern_relations 의 공개 SELECT 정책.
--   - feedbacks / pattern_confusion_pairs / 백업 테이블 정책.
--   - anon 공유 RPC 신설, 프론트 Supabase 직접 연동, 신규 인증 시스템.
--
-- [멱등성] DROP POLICY IF EXISTS — 재실행 안전.
-- ============================================================================

BEGIN;

DROP POLICY IF EXISTS anon_read_articles                 ON public.articles;
DROP POLICY IF EXISTS anon_read_analysis_results         ON public.analysis_results;
DROP POLICY IF EXISTS anon_read_analysis_ethics_snapshot ON public.analysis_ethics_snapshot;

-- ─── 사후 검증(같은 트랜잭션): 3개 정책이 정확히 사라졌는지 확인 ──────
DO $$
DECLARE
  n_remaining INT;
BEGIN
  SELECT count(*) INTO n_remaining
  FROM pg_policies
  WHERE schemaname = 'public'
    AND (
      (tablename = 'articles'                 AND policyname = 'anon_read_articles') OR
      (tablename = 'analysis_results'         AND policyname = 'anon_read_analysis_results') OR
      (tablename = 'analysis_ethics_snapshot' AND policyname = 'anon_read_analysis_ethics_snapshot')
    );
  IF n_remaining <> 0 THEN
    RAISE EXCEPTION 'expected 3 target policies removed, still see %', n_remaining;
  END IF;
END $$;

-- ─── 사후 검증: 유지 대상 공개 데이터 정책이 그대로 살아 있는지 확인 ──
DO $$
DECLARE
  n_kept INT;
BEGIN
  SELECT count(*) INTO n_kept
  FROM pg_policies
  WHERE schemaname = 'public'
    AND (
      (tablename = 'patterns'                  AND policyname = 'anon_read_patterns') OR
      (tablename = 'ethics_codes'              AND policyname = 'anon_read_ethics_codes') OR
      (tablename = 'ethics_code_hierarchy'     AND policyname = 'anon_read_ethics_code_hierarchy') OR
      (tablename = 'pattern_ethics_relations'  AND policyname = 'anon_read_pattern_ethics_relations') OR
      (tablename = 'pattern_relations'         AND policyname = 'anon_read_pattern_relations')
    );
  IF n_kept <> 5 THEN
    RAISE EXCEPTION 'expected 5 public-data policies preserved, found %', n_kept;
  END IF;
END $$;

-- ─── 사후 검증: RLS가 3개 테이블에서 여전히 활성 ─────────────────────
DO $$
DECLARE
  n_off INT;
BEGIN
  SELECT count(*) INTO n_off
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname IN ('articles','analysis_results','analysis_ethics_snapshot')
    AND NOT c.relrowsecurity;
  IF n_off > 0 THEN
    RAISE EXCEPTION 'RLS unexpectedly disabled on % target table(s)', n_off;
  END IF;
END $$;

-- ─── 사후 검증(강화): 이름과 무관한 실질적 노출 여부 ─────────────────
-- 목표 정책 이름 소멸(위 첫 번째 DO 블록)만으로는 훗날 다른 이름의
-- permissive SELECT/ALL 정책이 다시 열릴 가능성을 잡지 못한다.
-- pg_policies.roles 는 name[] 타입이며(운영 DB에서 pg_typeof로 확인), && 배열
-- overlap 연산자를 사용해 public/anon/authenticated 중 하나라도 대상이 되는
-- 정책이 남아 있는지 이름과 무관하게 계약 수준으로 잠근다.
-- service_role은 이 차단 검사 대상에서 제외 — 백엔드가 RLS를 bypass하는
-- 정상 경로이며 permissive 정책 필요 자체가 없다.
DO $$
DECLARE
  n_exposing INT;
BEGIN
  SELECT count(*) INTO n_exposing
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN (
      'articles',
      'analysis_results',
      'analysis_ethics_snapshot'
    )
    AND permissive = 'PERMISSIVE'
    AND cmd IN ('SELECT', 'ALL')
    AND roles && ARRAY[
      'public',
      'anon',
      'authenticated'
    ]::name[];

  IF n_exposing <> 0 THEN
    RAISE EXCEPTION
      'private tables still have % permissive SELECT/ALL policy(s) for public/anon/authenticated',
      n_exposing;
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';

-- ============================================================================
-- [ROLLBACK] Migration B 원복 — 제거한 3개 정책을 정확히 재생성.
-- (원본 정의: PERMISSIVE, roles=public, cmd=SELECT, USING(true))
-- ----------------------------------------------------------------------------
-- CREATE POLICY anon_read_articles
--   ON public.articles FOR SELECT TO public USING (true);
-- CREATE POLICY anon_read_analysis_results
--   ON public.analysis_results FOR SELECT TO public USING (true);
-- CREATE POLICY anon_read_analysis_ethics_snapshot
--   ON public.analysis_ethics_snapshot FOR SELECT TO public USING (true);
-- NOTIFY pgrst, 'reload schema';
-- ============================================================================
