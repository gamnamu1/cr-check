-- Phase γ: 규범 매핑 정비 — 관련성 낮은 매핑 제거/수정
-- 작성일: 2026-04-05
-- 목적: pattern_ethics_relations에서 패턴과 무관한 규범 매핑 7건 삭제, 2건 strength 하향

BEGIN;

-- ============================================
-- DELETE 7건: 패턴과 무관한 규범 매핑 제거
-- ============================================

-- 1. 1-7-2 (헤드라인 윤리) ↔ HRG-5-2b: 차별 표현 규범은 1-7-5에 이미 매핑됨
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-7-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'HRG-5-2b' AND version = 1);

-- 2. 1-7-2 (헤드라인 윤리) ↔ PCP-1-4: 편견 조장은 1-7-5의 영역
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-7-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-1-4' AND version = 1);

-- 3. 1-7-2 (헤드라인 윤리) ↔ PCP-3-3: 반론권 부여는 균형성(1-3-1) 영역
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-7-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-3-3' AND version = 1);

-- 4. 1-5-2 (개인정보 보호) ↔ PCP-13-3: 청소년 유해환경은 개인정보 보호와 직접 무관
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-5-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-13-3' AND version = 1);

-- 5. 1-5-2 (개인정보 보호) ↔ PCP-3-6: 선정성은 1-7-4의 영역
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-5-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-3-6' AND version = 1);

-- 6. 1-6-1 (심층성 부족) ↔ PCP-3-6: 선정적 묘사는 심층성 부족과 무관
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-6-1')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-3-6' AND version = 1);

-- 7. 1-6-1 (심층성 부족) ↔ PCP-3-7: 참혹 장면 보도는 심층성 부족과 무관
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-6-1')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-3-7' AND version = 1);

-- ============================================
-- UPDATE 2건: strength를 'strong' → 'moderate'로 하향
-- ============================================

-- 1. 1-7-2 (헤드라인 윤리) ↔ PCP-3-6: 간접 관련이나 원래 맥락은 본문 내 선정적 묘사
UPDATE public.pattern_ethics_relations
SET strength = 'moderate'
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-7-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-3-6' AND version = 1);

-- 2. 1-7-4 (자극적·선정적 표현) ↔ PCP-13-3: 핵심은 청소년 보호이지 선정적 표현 자체가 아님
UPDATE public.pattern_ethics_relations
SET strength = 'moderate'
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-7-4')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-13-3' AND version = 1);

COMMIT;
