-- ============================================================
-- ethics_codes_context_seed.sql
-- STEP 0-B Phase 3: applicable_contexts 컬럼 추가 + 출처별 배정
-- ============================================================
-- 작성일: 2026-05-02
-- 작성자: Claude Code CLI
-- 입력 문서:
--   - docs/STEP0B_ETHICS_PLAN_v1.0.md (§3 컨텍스트 설계, §4 Phase 3)
--   - docs/SESSION_CONTEXT_2026-05-02_v44.md (§v43→v44 변경 (1)·(2)·(4))
--   - docs/_scratch/STEP2A_ISCITABLE_CHANGES.md (§Phase 2-B SQL 초안)
-- 적용 대상: public.ethics_codes (활성 394건)
-- 절대 원칙:
--   - ON CONFLICT DO NOTHING 사용 금지. UPDATE 방식만 허용.
--   - DDL은 IF NOT EXISTS로 idempotent 보장.
--   - 본 시드는 DB 실행 전 단계. SQL Editor에서 기획자가 직접 실행 예정.
-- ============================================================

-- ------------------------------------------------------------
-- §0. DDL — applicable_contexts 컬럼 추가
-- ------------------------------------------------------------

ALTER TABLE public.ethics_codes
  ADD COLUMN IF NOT EXISTS applicable_contexts text[];


-- ------------------------------------------------------------
-- §1. NULL(all) 유지 — 6개 출처 / 127건
-- 별도 UPDATE 불필요. 컬럼 기본값 NULL이 'all' 컨텍스트로 해석됨.
-- (단, 신문윤리실천요강 특수 조항 10건은 §4에서 개별 배정 → 실제 NULL 유지: 117건)
-- ------------------------------------------------------------
-- 출처:
--   - 언론윤리헌장 (10건)
--   - 기자윤리강령 (11건)
--   - 기자윤리실천요강 (21건)
--   - 신문윤리강령 (8건)
--   - 신문윤리실천요강 (69건) ※ 출처 단위 NULL, 단 10건은 §4에서 특수 컨텍스트로 변경
--   - 혐오표현 반대 미디어 실천 선언 (8건)


-- ------------------------------------------------------------
-- §2. 특수 컨텍스트 출처 단위 일괄 배정 — 7개 출처 / 172건
-- ------------------------------------------------------------

-- §2.1 감염병보도준칙 → {health} (10건)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['health']
WHERE source = '감염병보도준칙' AND is_active = TRUE;

-- §2.2 군 취재·보도 기준 → {military} (21건)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['military']
WHERE source = '군 취재·보도 기준' AND is_active = TRUE;

-- §2.3 선거여론조사보도준칙 → {election} (29건)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['election']
WHERE source = '선거여론조사보도준칙' AND is_active = TRUE;

-- §2.4 자살보도 윤리강령 → {crisis} (23건)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['crisis']
WHERE source = '자살보도 윤리강령' AND is_active = TRUE;

-- §2.5 자살예방 보도준칙 4.0 → {crisis} (20건)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['crisis']
WHERE source = '자살예방 보도준칙 4.0' AND is_active = TRUE;

-- §2.6 재난보도준칙 → {disaster} (43건)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['disaster']
WHERE source = '재난보도준칙' AND is_active = TRUE;

-- §2.7 평화통일 보도 준칙 → {unification} (26건)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['unification']
WHERE source = '평화통일 보도 준칙' AND is_active = TRUE;


-- ------------------------------------------------------------
-- §3. 인권보도준칙 개별 컨텍스트 배정 — 95건
-- (Phase 2-B 확정 분류 / STEP2A_ISCITABLE_CHANGES.md §Phase 2-B 그대로 반영)
-- ------------------------------------------------------------

-- §3.1 인권보도준칙 → {general} (81건)
-- 전문·총강(G8 제외)·제1장·제2장 2-1칸(2-1e 제외)·제3~8장·제9장 9-1계열
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['general']
WHERE source = '인권보도준칙'
  AND is_active = TRUE
  AND code NOT IN (
    'HRG-G8', 'HRG-2-1e',
    'HRG-2-2', 'HRG-2-2a', 'HRG-2-2b', 'HRG-2-2c',
    'HRG-2-2d', 'HRG-2-2e', 'HRG-2-2f', 'HRG-2-2g',
    'HRG-9-2', 'HRG-9-2a', 'HRG-9-2b', 'HRG-9-2c'
  );

-- §3.2 인권보도준칙 → {crisis} (2건)
-- HRG-G8(생명권 보장과 자살보도 신중), HRG-2-1e(자살보도 주의)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['crisis']
WHERE code IN ('HRG-G8', 'HRG-2-1e');

-- §3.3 인권보도준칙 → {crime} (8건)
-- HRG-2-2 계열: 범죄 사건 기본권 (무죄추정·신상비공개·재판 영향 등)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['crime']
WHERE code IN (
    'HRG-2-2', 'HRG-2-2a', 'HRG-2-2b', 'HRG-2-2c',
    'HRG-2-2d', 'HRG-2-2e', 'HRG-2-2f', 'HRG-2-2g'
);

-- §3.4 인권보도준칙 → {unification} (4건)
-- HRG-9-2 계열: 북한이탈주민·통일 관점
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['unification']
WHERE code IN ('HRG-9-2', 'HRG-9-2a', 'HRG-9-2b', 'HRG-9-2c');


-- ------------------------------------------------------------
-- §4. 신문윤리실천요강 특수 조항 개별 배정 — 10건
-- (Phase 2-A 처리 대상 / SESSION_CONTEXT v44 §v43→v44 (1) 신문윤리실천요강 특수 조항)
-- ------------------------------------------------------------

-- §4.1 신문윤리실천요강 → {disaster} (2건)
-- 제2조③(재난 및 사고 취재), 제3조⑦(재난보도의 신중)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['disaster']
WHERE code IN ('PCP-2-3', 'PCP-3-7');

-- §4.2 신문윤리실천요강 → {crisis} (1건)
-- 제3조⑧(자살보도의 주의)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['crisis']
WHERE code IN ('PCP-3-8');

-- §4.3 신문윤리실천요강 → {crime} (7건)
-- 제3조⑨(피의사실 보도), 제7조①~⑤(피의자 인격권 5건), 제13조②(청소년·어린이 범죄 보호)
UPDATE public.ethics_codes
SET applicable_contexts = ARRAY['crime']
WHERE code IN (
    'PCP-3-9',
    'PCP-7-1', 'PCP-7-2', 'PCP-7-3', 'PCP-7-4', 'PCP-7-5',
    'PCP-13-2'
);

-- §4.4 비고: 제16조③(범죄의 폭로) PCP-16-3 → 분류 유보
-- STEP 2-A에서 이미 is_citable=false 처리됨. applicable_contexts 미배정.


-- ------------------------------------------------------------
-- §5. 검증 쿼리
-- ------------------------------------------------------------

SELECT applicable_contexts, COUNT(*)
FROM public.ethics_codes
WHERE is_active = TRUE
GROUP BY applicable_contexts
ORDER BY applicable_contexts;

-- 예상 분포 (총 394건):
--   NULL              117  (언론윤리헌장 10 + 기자윤리강령 11 + 기자윤리실천요강 21
--                           + 신문윤리강령 8 + 신문윤리실천요강 59 + 혐오표현 선언 8)
--   {crime}            15  (인권 HRG-2-2 계열 8 + 신문윤리실천요강 특수 7)
--   {crisis}           46  (자살윤리강령 23 + 자살예방 4.0 20 + 인권 2 + 신문윤리실천요강 1)
--   {disaster}         45  (재난보도준칙 43 + 신문윤리실천요강 2)
--   {election}         29  (선거여론조사보도준칙)
--   {general}          81  (인권보도준칙 일괄)
--   {health}           10  (감염병보도준칙)
--   {military}         21  (군 취재·보도 기준)
--   {unification}      30  (평화통일 보도 준칙 26 + 인권 HRG-9-2 계열 4)
--   ───────────────────────
--   합계              394
