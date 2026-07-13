-- ============================================================================
-- STEP 2-B: 1-1-e(취재원 주장의 사실화) → PCP-3-1 직접 규범 매핑 1건 추가
-- ============================================================================
-- 이력 version: 20260714042904
--
-- [실행 방식 경고 — 반드시 준수]
-- 이 파일은 Supabase SQL Editor에서 기획자가 "수동" 실행하는 마이그레이션이다.
-- `supabase db push` / `supabase migration up` 으로 운영 DB에 실행하지 말 것.
-- (운영 schema_migrations와 저장소 마이그레이션 파일이 drift 상태 — 20260622 파일 주석 참조)
--
-- [배경] STEP 2-A 진단(2026-07-14): 런타임 활성 v3 leaf 76개 중 usable ethics
--   mapping(strong/moderate·citable·비 exception_of)이 전 맥락에서 0건인 패턴이
--   1-1-e / 6-6-c / 6-6-d 3개로 확인됨. weak-only 패턴은 parent rollup도
--   발동하지 않아(롤업 시드는 direct usable mapping) Phase 2에 규범이 공급되지
--   않고, 다른 탐지 패턴의 규범이 1-1-e 서술에 차용되는 사례가 관측됨.
--   승인 범위(2026-07-14): 1-1-e → PCP-3-1 violates/strong 1건만 추가.
--   PCP-3-4·JEC-1 추가와 6-6-c/d 일체 변경은 이번 범위에서 명시적으로 제외.
--   기존 1-1-e → PCP-3-5 related_to/weak 관계는 유지(상향·삭제 금지).
--
-- [근거] 분석 사례가 아니라 패턴 정의와 조문 원문의 직접 대응:
--   1-1-e는 취재원의 주장·의견·전망·평가를 객관적으로 확인된 사실처럼 제시하는
--   패턴이고, PCP-3-1(신문윤리실천요강 제3조 ① 보도기사의 사실과 의견 구분)은
--   '보도기사는 사실과 의견을 명확히 구분하여 작성해야 한다'고 직접 규정한다.
--
-- [멱등성] 대상 존재성·유일성은 DO 블록에서 검증(실패 시 예외로 중단),
--   INSERT는 NOT EXISTS 가드(pattern_id, ethics_code_id 기준) — 재실행 안전.
--   참고: unique_pattern_ethics UNIQUE(pattern_id, ethics_code_id, relation_type)
--   제약이 있으나, relation_type이 다른 중복 연결도 막기 위해 가드는 더 넓게 잡는다.
-- ============================================================================

BEGIN;

-- 1) 대상 식별 검증: 없거나 중복이면 즉시 실패 (조용한 오적용 방지)
DO $$
DECLARE
  n_pattern INT;
  n_ethics  INT;
BEGIN
  SELECT count(*) INTO n_pattern FROM public.patterns WHERE code = '1-1-e';
  IF n_pattern <> 1 THEN
    RAISE EXCEPTION 'patterns.code=1-1-e must match exactly 1 row, found %', n_pattern;
  END IF;

  SELECT count(*) INTO n_ethics FROM public.ethics_codes WHERE code = 'PCP-3-1';
  IF n_ethics <> 1 THEN
    RAISE EXCEPTION 'ethics_codes.code=PCP-3-1 must match exactly 1 row, found %', n_ethics;
  END IF;
END $$;

-- 2) 신규 관계 1건 추가 (이미 있으면 0건 삽입 — 멱등)
INSERT INTO public.pattern_ethics_relations
  (pattern_id, ethics_code_id, relation_type, strength, reasoning)
SELECT p.id, ec.id, 'violates', 'strong',
  'step2b: 1-1-e는 취재원의 주장·의견·전망·평가를 객관적으로 확인된 사실처럼 '
  || '제시하는 패턴이다. PCP-3-1은 보도기사에서 사실과 의견을 명확히 구분하도록 '
  || '직접 요구하므로, 의견의 주체가 기자인지 취재원인지와 무관하게 패턴 정의와 '
  || '조문이 직접 대응한다. 상위 원칙의 유추가 아니라 조문 원문에 근거한 직접 매핑이다.'
FROM public.patterns p, public.ethics_codes ec
WHERE p.code = '1-1-e' AND ec.code = 'PCP-3-1'
  AND NOT EXISTS (
    SELECT 1 FROM public.pattern_ethics_relations r
    WHERE r.pattern_id = p.id AND r.ethics_code_id = ec.id
  );

-- 3) 사후 검증: 신규 관계가 정확히 1건이어야 커밋
DO $$
DECLARE
  n_rel INT;
BEGIN
  SELECT count(*) INTO n_rel
  FROM public.pattern_ethics_relations r
  JOIN public.patterns p      ON p.id  = r.pattern_id
  JOIN public.ethics_codes ec ON ec.id = r.ethics_code_id
  WHERE p.code = '1-1-e' AND ec.code = 'PCP-3-1'
    AND r.relation_type = 'violates' AND r.strength = 'strong';
  IF n_rel <> 1 THEN
    RAISE EXCEPTION '1-1-e -> PCP-3-1 violates/strong must be exactly 1 row after apply, found %', n_rel;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- [ROLLBACK] 이번 마이그레이션이 추가한 관계만 정확히 삭제.
-- 기존 1-1-e → PCP-3-5 related_to/weak 관계는 절대 건드리지 않는다.
-- ----------------------------------------------------------------------------
-- DELETE FROM public.pattern_ethics_relations
-- WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-1-e')
--   AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-3-1')
--   AND relation_type = 'violates'
--   AND strength = 'strong';
-- ============================================================================
