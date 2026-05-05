-- ============================================================
-- step2_audit_fix_critical.sql
-- STEP 2 감리 후속: CRITICAL 이슈 해결 (STEP 3 착수 전 필수)
-- ============================================================
-- 작성일: 2026-05-02
-- 작성자: Claude Code CLI
-- 입력 문서:
--   - docs/_scratch/STEP2_AUDIT_REPORT_ClaudeCodeCLI.md (감리 보고서)
--   - docs/_scratch/step1_output_v3.md (107 leaf 코드 체계)
--   - docs/current-criteria_v3_active.md (대분류·소분류 명칭)
-- 적용 대상: public.patterns
-- 절대 원칙: 본 시드는 SQL Editor 기획자 직접 실행 전 단계. CLI 자동 실행 금지.
-- ============================================================
--
-- ⚠️ 사전 확인 — DB 대분류 8건 존재 결과 (hierarchy_level=1)
--
--   '1' 진실성과 정확성
--   '2' 투명성과 책임성
--   '3' 균형성과 공정성
--   '4' 독립성과 자율성        ← current-criteria_v3 4 (인권과 프라이버시)와 의미 불일치
--   '5' 인권과 프라이버시      ← current-criteria_v3 5 (전문성과 심층성)와 의미 불일치
--   '6' 전문성과 심층성        ← current-criteria_v3 6 (언어와 표현의 윤리)와 의미 불일치
--   '7' 언어와 표현의 윤리     ← current-criteria_v3 7 (디지털 환경의 윤리)와 의미 불일치
--   '8' 디지털 환경의 윤리     ← current-criteria_v3에는 없음
--
-- 의미상 옳은 부모 매핑 (current-criteria_v3 기준):
--   4-3 (명예와 평판 훼손)     → 대분류 4 (인권과 프라이버시) → DB의 '5'
--   4-4 (사법 절차 존중 위반)  → 대분류 4 (인권과 프라이버시) → DB의 '5'
--   6-4 (자극적·선정적 표현)   → 대분류 6 (언어와 표현의 윤리) → DB의 '7'
--   6-6 (명료성을 해치는 표현) → 대분류 6 (언어와 표현의 윤리) → DB의 '7'
--
-- 그러나 본 작업 지시문은 부모를 DB의 code='4'와 code='6'으로 매핑할 것을 명시.
-- 지시 그대로 따르되, 위 의미 충돌은 기획자 판단 필요 사항으로 보고.
-- 추후 결정 시 parent_pattern_id 재할당 UPDATE 필요할 수 있음.
-- ============================================================


-- ------------------------------------------------------------
-- (A) 누락된 부모 코드 4건 INSERT
-- 대분류 코드 '4' (id=4), '6' (id=6) 사전 SELECT 확인 완료. 두 코드 모두 존재.
-- 지시문대로 두 코드를 부모로 매핑.
-- ------------------------------------------------------------

-- 4-3: 명예와 평판 훼손 (current-criteria 의미)
INSERT INTO public.patterns
  (code, name, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-3',
  '명예와 평판 훼손',
  3,
  (SELECT id FROM public.patterns WHERE code = '4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-4: 사법 절차 존중 위반
INSERT INTO public.patterns
  (code, name, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-4',
  '사법 절차 존중 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-4: 자극적·선정적 표현
INSERT INTO public.patterns
  (code, name, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-4',
  '자극적·선정적 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-6: 명료성을 해치는 표현
INSERT INTO public.patterns
  (code, name, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-6',
  '명료성을 해치는 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;


-- ------------------------------------------------------------
-- (B) 5-1 부모 name 수정
-- 현행 DB의 5-1 name = '취재 과정의 인권 침해' (구 4-1 의미)
-- step1_output v3 기준 5-1 = '기사의 심층성 부족'으로 정정.
-- ⚠️ 본 변경은 (A)와 동일한 대분류 매핑 모순 맥락이므로 기획자 결정 후 적용 권장.
-- ------------------------------------------------------------

UPDATE public.patterns
SET name = '기사의 심층성 부족'
WHERE code = '5-1' AND name = '취재 과정의 인권 침해';


-- ------------------------------------------------------------
-- (C) 검증 쿼리 (적용 후 SQL Editor에서 수동 실행)
-- ------------------------------------------------------------

-- 검증 1: 신규 부모 4건 확인
SELECT code, name, hierarchy_level
FROM public.patterns
WHERE code IN ('4-3','4-4','6-4','6-6');
-- 예상: 4행, 모두 hierarchy_level=3

-- 검증 2: 5-1 수정 확인
SELECT code, name FROM public.patterns WHERE code = '5-1';
-- 예상: name='기사의 심층성 부족'

-- 검증 3: 14개 고아 leaf parent NULL 해소 확인
SELECT COUNT(*) FROM public.patterns
WHERE hierarchy_level=3 AND parent_pattern_id IS NULL AND is_active=TRUE;
-- 예상: 14건 → 0건 (단, 부모 INSERT만으로는 leaf의 parent_pattern_id가
--                  자동 갱신되지 않음. leaf 별도 UPDATE 필요.)
--
-- 후속 leaf UPDATE 권고 (본 시드에는 미포함):
--   UPDATE public.patterns
--   SET parent_pattern_id = (SELECT id FROM public.patterns WHERE code='4-3')
--   WHERE code IN ('4-3-a','4-3-b');
--   UPDATE public.patterns
--   SET parent_pattern_id = (SELECT id FROM public.patterns WHERE code='4-4')
--   WHERE code IN ('4-4-a','4-4-b','4-4-c','4-4-d','4-4-e');
--   UPDATE public.patterns
--   SET parent_pattern_id = (SELECT id FROM public.patterns WHERE code='6-4')
--   WHERE code IN ('6-4-a','6-4-b','6-4-c');
--   UPDATE public.patterns
--   SET parent_pattern_id = (SELECT id FROM public.patterns WHERE code='6-6')
--   WHERE code IN ('6-6-a','6-6-b','6-6-c','6-6-d');
