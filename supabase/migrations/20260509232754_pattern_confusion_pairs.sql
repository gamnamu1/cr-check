-- STEP 5-B: 패턴 혼동 쌍 테이블
-- _SONNET_SOLO_PROMPT의 하드코딩된 혼동 쌍을 DB로 분리하여
-- 관리성·확장성을 확보한다. 시드 데이터는 supabase/seeds/pattern_confusion_pairs_seed.sql.

CREATE TABLE IF NOT EXISTS public.pattern_confusion_pairs (
  id            BIGSERIAL PRIMARY KEY,
  code_a        TEXT NOT NULL,
  code_b        TEXT NOT NULL,
  distinction_guide TEXT NOT NULL,
  is_active     BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT pattern_confusion_pairs_unique_pair UNIQUE (code_a, code_b),
  CONSTRAINT pattern_confusion_pairs_distinct_codes CHECK (code_a <> code_b)
);
