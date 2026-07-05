-- =====================================================================
-- [실행 방식 경고] 기획자가 SQL Editor에서 수동 실행. CLI(db push 등)로 실행 금지.
-- T3: HRG-8-1c 오염 차단 — 방안 B (Wave 1.1)
--
-- 4-3-b → HRG-8-1c 관계의 strength만 'weak'로 강등한다.
-- 4-2-a(violates/strong)·7-1-c(related_to/moderate) 경로는 활성 유지 —
-- 조항 자체는 계속 공급된다 (실측 확인됨).
-- 신규 매핑(wave11_t3_curated_mapping.sql)과 롤백 단위를 분리하기 위한 별도 파일.
-- =====================================================================

BEGIN;

UPDATE public.pattern_ethics_relations per
SET strength = 'weak'
FROM public.patterns p, public.ethics_codes ec
WHERE per.pattern_id = p.id AND per.ethics_code_id = ec.id
  AND p.code = '4-3-b' AND ec.code = 'HRG-8-1c'
  AND per.strength != 'weak';

COMMIT;

-- [검증 SELECT — 기획자용]
-- SELECT p.code, ec.code, per.relation_type, per.strength
-- FROM pattern_ethics_relations per
-- JOIN patterns p ON p.id=per.pattern_id JOIN ethics_codes ec ON ec.id=per.ethics_code_id
-- WHERE ec.code = 'HRG-8-1c' ORDER BY p.code;
-- (4-3-b만 weak, 4-2-a·7-1-c는 원래 strength 유지되어야 함)
