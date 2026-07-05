-- =====================================================================
-- [실행 방식 경고] 기획자가 SQL Editor에서 수동 실행. CLI(db push 등)로 실행 금지.
-- T3: 장애·집회·계층 매핑 큐레이션 (Wave 1.1)
--
-- 검수 방식: 기획자가 원치 않는 행을 아래 VALUES에서 직접 지우고 실행한다.
-- ON CONFLICT DO NOTHING — 기존 검수 관계는 절대 덮어쓰지 않는다
--   (유니크 제약 실측: UNIQUE (pattern_id, ethics_code_id, relation_type)).
-- HRG-3-2(적극 보도 의무)는 직접 연결하지 않음 — T5 리포트 서술 재료로 보류.
-- HRG-5-2b는 방안 C(T4까지 유보) — 매핑 변경 없음.
-- =====================================================================

BEGIN;

WITH candidates(pattern_code, ethics_code, relation_type, strength, reasoning) AS (
  VALUES
    ('4-3-b', 'HRG-3-1',  'violates',   'strong',   'wave1.1 curated: 장애인 존엄성·인격권'),
    ('4-3-b', 'HRG-3-1a', 'violates',   'strong',   'wave1.1 curated: 장애인 비하·차별 표현'),
    ('4-3-b', 'HRG-3-1b', 'violates',   'strong',   'wave1.1 curated: 부정적 관용구 — 4-3-b 정의와 정합'),
    ('4-3-b', 'HRG-3-2a', 'violates',   'strong',   'wave1.1 curated: 고정관념·편견 강화'),
    ('4-3-b', 'HRG-2-1f', 'violates',   'strong',   'wave1.1 curated: 인용 경유 차별 조장'),
    ('4-3-b', 'PCP-1-5',  'violates',   'strong',   'wave1.1 curated: 사회적 약자 보호'),
    ('4-3-b', 'HSD-3',    'related_to', 'moderate', 'wave1.1 curated: 소수자 배제 혐오표현'),
    ('4-3-b', 'HSD-4',    'related_to', 'moderate', 'wave1.1 curated: 영향력자 혐오표현 증폭'),
    ('3-4-a', 'HRG-1-1c', 'violates',   'moderate', 'wave1.1 curated: 집회·시위 부정 묘사(이분법)'),
    ('3-4-b', 'HRG-1-1c', 'violates',   'strong',   'wave1.1 curated: 집회·시위 제로섬 프레임'),
    ('3-4-a', 'HRG-3-2a', 'related_to', 'moderate', 'wave1.1 curated: 대립 구도의 편견 강화'),
    ('3-4-b', 'PCP-1-5',  'related_to', 'moderate', 'wave1.1 curated: 제로섬 구도와 약자 보호'),
    ('3-4-a', 'HRG-1-2c', 'related_to', 'moderate', 'wave1.1 curated: 계층 갈등 조장'),
    ('3-4-b', 'HRG-1-2c', 'related_to', 'moderate', 'wave1.1 curated: 계층 갈등 조장'),
    ('3-1-c', 'HRG-3-2c', 'violates',   'moderate', 'wave1.1 curated: 당사자 입장 배제'),
    ('3-1-c', 'HRG-3-2d', 'related_to', 'moderate', 'wave1.1 curated: 개선 노력 부재'),
    ('6-2-d', 'HSD-4',    'related_to', 'moderate', 'wave1.1 curated: 제목의 혐오 발언 증폭')
    -- 6-2-d/PCP-10-1 제외: 실측 결과 이미 violates/strong으로 존재 (중복 방지)
)
INSERT INTO public.pattern_ethics_relations
  (pattern_id, ethics_code_id, relation_type, strength, reasoning)
SELECT p.id, ec.id, c.relation_type, c.strength, c.reasoning
FROM candidates c
JOIN public.patterns p ON p.code = c.pattern_code
JOIN public.ethics_codes ec ON ec.code = c.ethics_code
ON CONFLICT (pattern_id, ethics_code_id, relation_type) DO NOTHING;

COMMIT;

-- [검증 SELECT — 기획자용]
-- SELECT p.code AS pattern, ec.code AS ethics, per.relation_type, per.strength
-- FROM pattern_ethics_relations per
-- JOIN patterns p ON p.id = per.pattern_id
-- JOIN ethics_codes ec ON ec.id = per.ethics_code_id
-- WHERE per.reasoning LIKE 'wave1.1 curated%' ORDER BY p.code, ec.code;

-- [기획자 수동 실행 — 이력 동기화 (본 파일 + wave11_t3_hrg81c_downgrade.sql 합산 1건)]
-- INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
-- VALUES ('20260707000000', 'wave11_t3_mapping',
--         ARRAY[
--           'INSERT pattern_ethics_relations wave1.1 curated mapping (17 candidates, ON CONFLICT DO NOTHING)',
--           'UPDATE pattern_ethics_relations SET strength=weak WHERE 4-3-b -> HRG-8-1c'
--         ]);
