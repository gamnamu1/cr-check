-- Phase 2 Bugfix: inference_role 컬럼 추가
-- meta_pattern_inference.py의 REST API 쿼리가 이 컬럼을 참조함
-- 프로덕션 DB에는 이미 SQL Editor로 적용 완료 (2026-04-08)
ALTER TABLE public.pattern_relations
ADD COLUMN IF NOT EXISTS inference_role TEXT
CHECK (inference_role IN ('required', 'supporting'));

COMMENT ON COLUMN public.pattern_relations.inference_role IS
  'inferred_by 관계에서 해당 패턴의 역할: required(필수 지표) / supporting(보강 지표)';
