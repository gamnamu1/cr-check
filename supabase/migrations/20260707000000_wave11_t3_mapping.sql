-- ============================================================================
-- Wave 1.1 / T3: 패턴-윤리 관계 큐레이션 — 장애·집회·계층 매핑 17건 + HRG-8-1c 강등
-- ============================================================================
-- 이력 version: 20260707000000 (supabase_migrations.schema_migrations 정합)
--
-- [회수 경위] 2026-07-05 세션에서 DB에 직접 적용된 변경의 역생성본(2026-07-07).
--   원본 SQL은 파일로 저장되지 않았으며, 프로덕션 DB 실측값에서 재구성했다.
--
-- [구성]
--   Part 1 — 큐레이션 매핑 17건 INSERT (자연키 기반, NOT EXISTS 가드로 멱등)
--     · 4-3-b(8건): 프레이밍 기반 차별 탐지 시 인용할 인권보도준칙(HRG)·
--       혐오표현 반대 선언(HSD)·평화통일 준칙(PCP) 조항 공급
--     · 3-4-a(3건)·3-4-b(3건): 대결 구도·제로섬 프레임의 규범 근거
--     · 3-1-c(2건)·6-2-d(1건): 당사자 배제·제목의 혐오 증폭
--   Part 2 — 4-3-b → HRG-8-1c 관계 strength 강등 (strong → weak)
--     · 노조 기사 등 무관 맥락에 이민 관련 조항이 공급되던 오염 차단
--     · 참고: 최초 적용 시 updated_at 트리거 버그(컬럼 부재)로 실패 후
--       트리거 수정을 거쳐 반영됨. 관련 잔존 리스크(HRG-5-2b, 방안 C 유보)는
--       docs/_reference/WAVE11_VERIFICATION_TABLE_v1.md V5 항목 참조.
--
-- [멱등성] 재실행 안전 — INSERT는 기존 관계 존재 시 건너뛰고,
--   UPDATE는 이미 weak인 경우 no-op.
-- ============================================================================

-- Part 1: 큐레이션 매핑 17건 -------------------------------------------------
INSERT INTO public.pattern_ethics_relations
  (pattern_id, ethics_code_id, relation_type, strength, reasoning)
SELECT p.id, ec.id, v.relation_type, v.strength, v.reasoning
FROM (VALUES
  -- 3-1-c 당사자 취재 관련 (2건)
  ('3-1-c', 'HRG-3-2c', 'violates',   'moderate', 'wave1.1 curated: 당사자 입장 배제'),
  ('3-1-c', 'HRG-3-2d', 'related_to', 'moderate', 'wave1.1 curated: 개선 노력 부재'),
  -- 3-4-a 이분법 대결 구도 (3건)
  ('3-4-a', 'HRG-1-1c', 'violates',   'moderate', 'wave1.1 curated: 집회·시위 부정 묘사(이분법)'),
  ('3-4-a', 'HRG-1-2c', 'related_to', 'moderate', 'wave1.1 curated: 계층 갈등 조장'),
  ('3-4-a', 'HRG-3-2a', 'related_to', 'moderate', 'wave1.1 curated: 대립 구도의 편견 강화'),
  -- 3-4-b 제로섬 프레임 (3건)
  ('3-4-b', 'HRG-1-1c', 'violates',   'strong',   'wave1.1 curated: 집회·시위 제로섬 프레임'),
  ('3-4-b', 'HRG-1-2c', 'related_to', 'moderate', 'wave1.1 curated: 계층 갈등 조장'),
  ('3-4-b', 'PCP-1-5',  'related_to', 'moderate', 'wave1.1 curated: 제로섬 구도와 약자 보호'),
  -- 4-3-b 차별·혐오·인권침해 표현 (8건) — Wave 1.1 핵심
  ('4-3-b', 'HRG-2-1f', 'violates',   'strong',   'wave1.1 curated: 인용 경유 차별 조장'),
  ('4-3-b', 'HRG-3-1',  'violates',   'strong',   'wave1.1 curated: 장애인 존엄성·인격권'),
  ('4-3-b', 'HRG-3-1a', 'violates',   'strong',   'wave1.1 curated: 장애인 비하·차별 표현'),
  ('4-3-b', 'HRG-3-1b', 'violates',   'strong',   'wave1.1 curated: 부정적 관용구 — 4-3-b 정의와 정합'),
  ('4-3-b', 'HRG-3-2a', 'violates',   'strong',   'wave1.1 curated: 고정관념·편견 강화'),
  ('4-3-b', 'HSD-3',    'related_to', 'moderate', 'wave1.1 curated: 소수자 배제 혐오표현'),
  ('4-3-b', 'HSD-4',    'related_to', 'moderate', 'wave1.1 curated: 영향력자 혐오표현 증폭'),
  ('4-3-b', 'PCP-1-5',  'violates',   'strong',   'wave1.1 curated: 사회적 약자 보호'),
  -- 6-2-d 헤드라인 낚시성 제목 (1건)
  ('6-2-d', 'HSD-4',    'related_to', 'moderate', 'wave1.1 curated: 제목의 혐오 발언 증폭')
) AS v(pattern_code, ethics_code, relation_type, strength, reasoning)
JOIN public.patterns     p  ON p.code  = v.pattern_code
JOIN public.ethics_codes ec ON ec.code = v.ethics_code
WHERE NOT EXISTS (
  SELECT 1 FROM public.pattern_ethics_relations r
  WHERE r.pattern_id = p.id AND r.ethics_code_id = ec.id
);

-- Part 2: 4-3-b → HRG-8-1c 강등 (strong → weak) -------------------------------
UPDATE public.pattern_ethics_relations r
SET strength = 'weak'
FROM public.patterns p, public.ethics_codes ec
WHERE r.pattern_id     = p.id
  AND r.ethics_code_id = ec.id
  AND p.code  = '4-3-b'
  AND ec.code = 'HRG-8-1c'
  AND r.strength <> 'weak';
