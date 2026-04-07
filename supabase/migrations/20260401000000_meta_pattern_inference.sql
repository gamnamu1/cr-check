-- M6: 메타 패턴 추론 — inference_role 컬럼 추가 + inferred_by 관계 시드
-- 마스터 플랜 섹션 8.2 기반
-- 2026-04-01

-- 1. inference_role 컬럼 추가
ALTER TABLE public.pattern_relations
ADD COLUMN IF NOT EXISTS inference_role TEXT
CHECK (inference_role IN ('required', 'supporting'));

-- 기존 variant_of 10건은 inference_role = NULL (해당 없음)

-- 2. inferred_by 관계 시드 (9건)
-- 관계 방향: source = 하위 지표, target = 메타 패턴
-- "source가 탐지되면 target(메타 패턴)을 추론할 수 있다"

-- ── 1-4-1 (외부 압력에 의한 왜곡) — 4건 ──

-- 필수: 1-1-1 (사실 검증 부실) → 1-4-1
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '익명 단일 취재원, 무검증 인용이 외부 압력 징후', 'manual', 1.0, true, 'required'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-1-1' AND t.code = '1-4-1'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- 필수: 1-1-2 (이차 자료 의존) → 1-4-1
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '보도자료 받아쓰기가 외부 압력 징후', 'manual', 1.0, true, 'required'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-1-2' AND t.code = '1-4-1'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- 보강: 1-3-2 (선별적 사실 제시) → 1-4-1
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '이념 편향/선별적 사실이 외부 압력 보강 지표', 'manual', 1.0, true, 'supporting'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-3-2' AND t.code = '1-4-1'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- 보강: 1-3-1 (관점 다양성 부족) → 1-4-1
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '관점 다양성 부족이 외부 압력 보강 지표', 'manual', 1.0, true, 'supporting'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-3-1' AND t.code = '1-4-1'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- ── 1-4-2 (상업적 동기에 의한 왜곡) — 5건 ──

-- 필수: 1-7-3 (과장과 맥락 왜곡) → 1-4-2
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '낚시성 제목/과장이 상업적 동기 징후', 'manual', 1.0, true, 'required'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-7-3' AND t.code = '1-4-2'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- 필수: 1-7-4 (자극적·선정적 표현) → 1-4-2
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '자극적 표현이 상업적 동기 징후', 'manual', 1.0, true, 'required'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-7-4' AND t.code = '1-4-2'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- 보강: 1-1-1 (사실 검증 부실) → 1-4-2
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '무검증 인용이 상업적 동기 보강 지표', 'manual', 1.0, true, 'supporting'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-1-1' AND t.code = '1-4-2'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- 보강: 1-8-2 (디지털 플랫폼 특유 문제) → 1-4-2
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '뉴스 어뷰징이 상업적 동기 보강 지표', 'manual', 1.0, true, 'supporting'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-8-2' AND t.code = '1-4-2'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;

-- 보강: 1-6-1 (기사의 심층성 부족) → 1-4-2
INSERT INTO public.pattern_relations (source_pattern_id, target_pattern_id, relation_type, description, source, confidence, verified, inference_role)
SELECT s.id, t.id, 'inferred_by', '심층성 부족이 상업적 동기 보강 지표', 'manual', 1.0, true, 'supporting'
FROM public.patterns s, public.patterns t
WHERE s.code = '1-6-1' AND t.code = '1-4-2'
ON CONFLICT (source_pattern_id, target_pattern_id, relation_type) DO NOTHING;
