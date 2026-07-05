-- =====================================================================
-- [실행 방식 경고] 기획자가 SQL Editor에서 수동 실행. CLI(db push 등)로 실행 금지.
-- T1: 4-3-b/3-4-a/3-4-b/6-2-d/6-2-c 의미 공간 확장 (프레이밍형 차별 탐지 보강)
--
-- 설계:
--   - 기존 description·search_text를 지우지 않고 `||` 연결로 확장한다
--     (명시적 슬러 탐지는 유지, 프레이밍 탐지 범위만 추가 — 전면 교체 아님).
--   - 각 UPDATE에 NOT LIKE 가드를 두어 중복 실행 시 이중 append를 방지한다.
--   - 어휘 역할 분배: 낙인 자체 = 4-3-b / 대결 구도 = 3-4-a /
--     제로섬 논리 = 3-4-b / 제목 증폭 = 6-2-d (과검출 방지).
--   - 7-2·7-5는 어떤 형태로도 건드리지 않는다.
--   - 실행 후 기획자 본인 터미널에서 임베딩 재생성 필요
--     (docs/_reference/T1_EMBEDDING_REGEN_STEPS.md 참조).
-- =====================================================================

BEGIN;

-- 4-3-b: 차별·혐오 표현 — 프레이밍형(명시적 비하어 없음) 낙인 추가
UPDATE public.patterns SET
  description = description
    || ' 명시적 비하어가 없더라도 특정 집단을 공공질서 파괴자·시민의 적·사회적'
    || ' 부담·가해자로 위치시키는 프레이밍(예: 권리 요구 집단을 시민 피해의'
    || ' 원인 제공자로만 배치)을 포함한다.',
  search_text = search_text
    || ', 볼모, 인질, 독선, 아집, 떼쓰기, 무리한 요구, 시민의 적,'
    || ' 공공질서 파괴자, 사회적 부담, 집단 낙인'
WHERE code = '4-3-b'
  AND description NOT LIKE '%공공질서 파괴자·시민의 적%';

-- 3-4-a: 단순 이분법 프레임 — 약자·소수자 대 시민 대결 구도 추가
UPDATE public.patterns SET
  description = description
    || ' 정치 진영 간 대립뿐 아니라, 약자·소수자의 권리 요구를 일반 시민과의'
    || ' 대결 구도(예: 시민 불편 대 장애인 시위)로 환원하는 프레임도 포함한다.',
  search_text = search_text
    || ', 시민 대 장애인, 권리 요구 vs 시민 불편, 출근길 시민 피해 부각,'
    || ' 시위로 발 묶인 시민, 약자 대 시민 대결 구도'
WHERE code = '3-4-a'
  AND description NOT LIKE '%일반 시민과의 대결 구도%';

-- 3-4-b: 제로섬 프레임 — 약자 권리 요구를 시민 손해로만 제시하는 서술 추가
UPDATE public.patterns SET
  description = description
    || ' 약자의 권리 요구나 복지 확대를 일반 시민의 손해·비용 부담으로만'
    || ' 제시하는 서술도 포함한다.',
  search_text = search_text
    || ', 약자의 권리 요구를 일반 시민의 손해로만 제시, 권리 보장 곧 시민 부담,'
    || ' 배려가 곧 역차별'
WHERE code = '3-4-b'
  AND description NOT LIKE '%일반 시민의 손해·비용 부담%';

-- 6-2-d: 자극적 제목 — 공격 발언의 거리두기 없는 제목 인용·증폭 추가
UPDATE public.patterns SET
  description = description
    || ' 공격적·혐오적 발언을 거리두기 없이 제목에 직접 인용해 집단 갈등을'
    || ' 증폭하는 따옴표 제목도 포함한다.',
  search_text = search_text
    || ', 제목에 공격적 발언 직접 인용, 발언 따옴표를 거리두기 없이 제목화,'
    || ' 집단 갈등을 자극하는 제목'
WHERE code = '6-2-d'
  AND description NOT LIKE '%거리두기 없이 제목에 직접 인용%';

-- 6-2-c: 제목-본문 침소봉대 (structural — 임베딩 대상 아님, description만 보강)
UPDATE public.patterns SET
  description = description
    || ' 제목이 특정 집단에 대한 공격 발언을 본문 근거 이상으로 부각하는'
    || ' 경우도 제목-본문 대조 시 검토한다.'
WHERE code = '6-2-c'
  AND description NOT LIKE '%공격 발언을 본문 근거 이상으로 부각%';

COMMIT;

-- [검증 SELECT — 기획자용]
-- SELECT code, description, search_text FROM public.patterns
-- WHERE code IN ('4-3-b','3-4-a','3-4-b','6-2-d','6-2-c') ORDER BY code;

-- [기획자 수동 실행 — 이력 동기화]
-- INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
-- VALUES ('20260706000000', 'wave11_t1_pattern_enrichment',
--         ARRAY['UPDATE public.patterns description/search_text enrichment WHERE code IN (''4-3-b'',''3-4-a'',''3-4-b'',''6-2-d'',''6-2-c'')']);

-- [임베딩 재생성 후 검증 — 기획자용]
-- SELECT code, detection_strategy, description_embedding IS NOT NULL AS has_embedding
-- FROM public.patterns WHERE code IN ('4-3-b','3-4-a','3-4-b','6-2-d');
