-- ============================================================================
-- Adoption G: 6-2-a(제목-본문 불일치/맥락 삭제) 윤리규범 매핑 보강
-- ============================================================================
-- 이력 version: 20260709115231 (apply_migration 기록과 정합)
--
-- [배경] v2 '질문 생성형' 프롬프트 채택 패키지 검증(2026-07-08) 중 발견:
--   6-2-a는 JEC-9(언론윤리헌장 제9조, is_citable=false)에만 연결되어 있어
--   인용 가능한 규범이 0건. 6-2-a 단독 탐지 시 Phase 2 리포트가 제목 원칙
--   규범을 인용할 수 없는 구조적 공백. (형제 패턴 6-2-b/c/d는 모두
--   PCP-10-1 '신문윤리실천요강 제10조 ① 제목의 원칙'에 violates/strong 연결)
--   감리자GPT 지적 → DB 실측 검증 → 채택 패키지 필수 조건으로 반영.
--
-- [내용]
--   1) 6-2-a → PCP-10-1 (violates/strong): 형제 패턴과 동형의 핵심 근거
--   2) 6-2-a → JEC-1  (related_to/moderate): '종합적 맥락 전달' 보조 근거
--
-- [멱등성] NOT EXISTS 가드 — 재실행 안전.
-- ============================================================================

INSERT INTO public.pattern_ethics_relations
  (pattern_id, ethics_code_id, relation_type, strength, reasoning)
SELECT p.id, ec.id, v.relation_type, v.strength, v.reasoning
FROM (VALUES
  ('6-2-a', 'PCP-10-1', 'violates',   'strong',
   'adoption G: 제목이 본문의 조건·맥락을 삭제하는 유형의 표제 원칙 근거'),
  ('6-2-a', 'JEC-1',    'related_to', 'moderate',
   'adoption G: 종합적·포괄적 맥락 전달 원칙의 보조 근거')
) AS v(pattern_code, ethics_code, relation_type, strength, reasoning)
JOIN public.patterns     p  ON p.code  = v.pattern_code
JOIN public.ethics_codes ec ON ec.code = v.ethics_code
WHERE NOT EXISTS (
  SELECT 1 FROM public.pattern_ethics_relations r
  WHERE r.pattern_id = p.id AND r.ethics_code_id = ec.id
);
