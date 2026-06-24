-- [S0 기준선 확인] 6/22 구조 지표 일괄 조회
-- 게이트: Wave 1 · S0 (코드 변경 0, SELECT 전용)
-- 기획자가 Supabase SQL Editor에서 ①~⑥을 실행하고, 결과를 기준값과 대조한다.
-- 하나라도 어긋나면 즉시 작업 중단 → 기획자 보고 → S1 진행 금지.
--
-- ※ 이 파일은 조회 전용. INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/NOTIFY 포함 금지.
-- ※ 운영 DB(vwaelliqpoqzeoggrfew.supabase.co) 실행은 기획자 수동 수행.

-- ① Tier 분포 (기대: T1=82, T2=153, T3=28, T4=4)
SELECT ec.tier, COUNT(*) AS cnt
FROM pattern_ethics_relations per
JOIN ethics_codes ec ON per.ethics_code_id = ec.id
GROUP BY ec.tier ORDER BY ec.tier;

-- ② 활성 leaf 패턴 (기대: vector=64, structural=12, 합계 76)
SELECT detection_strategy, COUNT(*) AS cnt
FROM patterns
WHERE is_active = true AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
GROUP BY detection_strategy;

-- ③ Tier 3 violates 0건 패턴 수 (기대: 70, 전체 76개 중 92.1%)
WITH active_leaf AS (
  SELECT id FROM patterns
  WHERE is_active = true AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
),
tier3_v AS (
  SELECT DISTINCT per.pattern_id
  FROM pattern_ethics_relations per
  JOIN ethics_codes ec ON per.ethics_code_id = ec.id
  WHERE ec.tier = 3 AND per.relation_type = 'violates'
)
SELECT COUNT(*) FILTER (WHERE t.pattern_id IS NULL) AS no_tier3_violates
FROM active_leaf al LEFT JOIN tier3_v t ON al.id = t.pattern_id;

-- ④ RPC 반환 컬럼 시그니처 (기대: 10컬럼, source/article_number 없음)
SELECT pg_get_function_result(
  'public.get_ethics_for_patterns(bigint[], text)'::regprocedure
);

-- ⑤ schema_migrations 건수 (기대: 3)
SELECT COUNT(*) FROM supabase_migrations.schema_migrations;

-- ⑥ citation_audit 컬럼 부재 확인 (기대: 0)
SELECT COUNT(*) FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'analysis_results'
  AND column_name = 'citation_audit';
