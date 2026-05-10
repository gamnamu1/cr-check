# STEP 6 임베딩 재작성 계획 문서_보강(10차 의견 반영)

# STEP 6 임베딩 재생성 실행 계획 v9

> 10차 교차 감리 완료 기준. CLI 지시문 초안 작성용 마스터 플랜.
> 

---

## 확정된 핵심 결정 4가지

| 결정 | 내용 |
| --- | --- |
| 부모 패턴 격리 | 옵션 A — `search_pattern_candidates` RPC 필터 추가 (부모 행 데이터 변경 없음) |
| 임베딩 입력 | `search_text` 단독. wrapping은 STEP 7 실험 후보로 보류 |
| `search_text` NULL/공백 | 폴백 없이 명시적 실패 처리 |
| RPC 수정 | STEP 6 안에 합산 |

---

## Phase A — 진입 전 사전 점검

**A-0. `step6_start_ts` 기록** *(Phase A 전체의 최초 첫 번째 단계)*

```sql
-- SQL Editor에서 실행 후 반환값을 메모해둔다.
-- 이후 D-18, D-19 검증 쿼리의 <step6_start_ts> 자리에 복붙.
-- 절대 이후 단계에서 NOW()로 대체하지 않는다.
SELECT now() AS step6_start_ts;
```

---

**A-1. leaf/parent/structural × vector 분포 쿼리**

```sql
SELECT
  is_active,
  detection_strategy,
  CASE
    WHEN code ~ '^[0-9]+-[0-9]+-[a-z]+$' THEN 'leaf'
    WHEN code ~ '^[0-9]+-[0-9]+$'         THEN 'parent'
    ELSE 'other'
  END AS code_type,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE description_embedding IS NOT NULL) AS has_embedding,
  COUNT(*) FILTER (WHERE description_embedding IS NULL)     AS no_embedding
FROM patterns
GROUP BY is_active, detection_strategy, code_type
ORDER BY is_active DESC, detection_strategy, code_type;
```

기대: active·vector·leaf ≈ 64~75건. 이 분포를 기준으로 이후 전 단계의 기준 건수를 확정한다.

---

**A-2. `search_text` 품질 감사**

```sql
-- NULL/공백
SELECT code, name FROM patterns
WHERE is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
  AND (search_text IS NULL OR btrim(search_text) = '');
-- 기대: 0건. 0건 아니면 STEP 6 중단 → search_text 보정 후 재진입.

-- 길이 20자 미만 (의미 빈약 경고)
SELECT code, name, length(search_text) AS len FROM patterns
WHERE is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
  AND length(search_text) < 20;

-- 혼동 쌍 5쌍 search_text 육안 비교
SELECT p.code, p.name, p.search_text
FROM patterns p
WHERE p.code IN (
  SELECT code_a FROM pattern_confusion_pairs WHERE is_active = TRUE
  UNION
  SELECT code_b FROM pattern_confusion_pairs WHERE is_active = TRUE
)
ORDER BY p.code;
```

---

**A-3. `search_pattern_candidates` RPC 정의 확인**

PostgreSQL에서 `FLOAT`가 `double precision`으로 등록될 수 있어 직접 시그니처를 지정하면 조회 실패 가능. 아래 순서로 진행한다.

```sql
-- 1순위: pg_proc으로 실제 등록된 시그니처 확인
SELECT oid::regprocedure
FROM pg_proc
WHERE proname = 'search_pattern_candidates';
-- 반환 예: public.search_pattern_candidates(vector,double precision,integer)
```

```sql
-- 2순위: 확인된 시그니처로 함수 정의 조회 (위 결과를 그대로 사용)
SELECT pg_get_functiondef(
  'public.search_pattern_candidates(vector,double precision,integer)'::regprocedure
);
-- 실제 등록 시그니처에 따라 타입명 조정 (float, double precision, integer 중 하나)
```

확인 항목:

- `is_active = TRUE` 필터 유무
- `detection_strategy = 'vector'` 필터 유무
- `code ~ '^[0-9]+-[0-9]+-[a-z]+$'` 필터 유무
- `description_embedding IS NOT NULL` 필터 유무

위 4개가 없으면 Phase B에서 반드시 추가한다.

---

**A-4. 스크립트 구조 사전 진단** *(CLI가 보고)*

`generate_embeddings.py`를 열어 다음 두 가지를 보고한다:

1. `fetch_ethics_codes` 또는 `ethics_codes` UPDATE 로직 존재 여부 → 있으면 Phase C-11에서 `--patterns-only`로 우회
2. `_LEAF_CODE_RE` 상수 존재 여부 → 있으면 동일 정규식을 SQL에서도 사용 / 없으면 STEP 6에서 새 상수 추가 없이 SQL과 스크립트 양쪽에 `^[0-9]+-[0-9]+-[a-z]+$` 명시

---

**A-5. `get_ethics_for_patterns` RPC 정의 확인**

```sql
SELECT pg_get_functiondef(
  'public.get_ethics_for_patterns(bigint[])'::regprocedure
);
```

확인 목적 (vector 필터 점검이 아님):

1. `strength='weak' AND relation_type='related_to'` 제외 로직 유지 여부
2. `exception_of` 관계 처리 방식 유지 여부
3. `applicable_contexts` 필터 동작 여부
4. parent chain rollup 동작 여부

*이 함수에 vector/leaf 필터는 추가하지 않는다. structural leaf 확정 패턴도 규범 조회 대상이므로.*

---

**A-6. 이진 게이트 잔존 확인** *(5분)*

`pattern_matcher.py`의 `_SONNET_SOLO_PROMPT`에 "(가) 양질 근거 우세 → `detections=[]`" 패턴이 잔존하는지 확인. STEP 5-A v3에서 제거됐을 가능성 높으나, 5분 확인으로 조기 차단.

---

## Phase B — RPC 보강

**B-7. `search_pattern_candidates` 마이그레이션 작성** *(CLI 작업)*

CLI가 마이그레이션 파일 초안 작성:

```
파일명: supabase/migrations/{timestamp}_restrict_search_pattern_candidates_to_vector_leaf.sql
```

```sql
CREATE OR REPLACE FUNCTION public.search_pattern_candidates(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.2,
  match_count INT DEFAULT 7
)
RETURNS TABLE (
  pattern_id BIGINT,
  pattern_code TEXT,
  pattern_name TEXT,
  pattern_description TEXT,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.code, p.name, p.description,
         1 - (p.description_embedding <=> query_embedding) AS similarity
  FROM public.patterns p
  WHERE p.is_active = TRUE
    AND p.detection_strategy = 'vector'
    AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
    AND p.description_embedding IS NOT NULL
    AND 1 - (p.description_embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;
```

diff 선제시 → 기획자 승인.

---

**B-8. 기획자 SQL Editor 실행**

직접 실행. CLI 자동 실행 금지.

---

**B-9. PostgREST 스키마 캐시 리로드**

```sql
NOTIFY pgrst, 'reload schema';
```

---

**B-10. 함수 정의 재확인**

A-3과 동일하게 2단계로 진행한다. 예시 쿼리를 그대로 복사하지 말 것.

```sql
-- 1단계: pg_proc으로 마이그레이션 반영 후 실제 등록 시그니처 확인
SELECT oid::regprocedure
FROM pg_proc
WHERE proname = 'search_pattern_candidates';
-- 반환 예: public.search_pattern_candidates(vector,double precision,integer)
```

```sql
-- 2단계: 확인된 시그니처 그대로 대입하여 함수 정의 조회
SELECT pg_get_functiondef(
  'public.search_pattern_candidates(vector,double precision,integer)'::regprocedure
);
-- ⚠️ 위 타입명은 예시. 1단계 반환값과 반드시 일치시킬 것.
```

A-3에서 확인한 원본과 비교. 4개 필터 모두 반영됐는지 확인.

*Phase B에서는 함수 정의 반영 확인까지만. 실제 RPC 결과 검증(반환 코드 leaf 여부)은 임베딩 재생성 후 Phase D에서 수행한다.*

---

## Phase C — 스크립트 수정 *(CLI 작업, diff 선제시 필수)*

**C-11. `--patterns-only` + `--dry-run` 플래그 도입**

두 플래그를 Phase C에서 함께 구현한다.

> ⚠️ **이번 STEP 6에서 `--dry-run`은 반드시 `--patterns-only`와 함께 사용한다.**
> 단독 실행 시 ethics_codes 로직이 살아있는 상태에서 dry-run이 돌 수 있으므로 금지.
> **코드 레벨 강제 종료** — 아래 구문을 `main()` 초반에 반드시 구현한다:
> ```python
> if args.dry_run and not args.patterns_only:
>     print("ERROR: --dry-run must be used with --patterns-only in STEP 6")
>     sys.exit(1)
> ```

- `--patterns-only`:
  - `fetch_ethics_codes()` 및 관련 UPDATE 로직 skip
  - `verify_embeddings()`의 ethics_codes 검증 로직(`all_ok` 변수의 ethics 카운트 비교) skip
- `--dry-run` *(새 플래그)*:
  1. DB 연결
  2. `fetch_patterns()` 실행 → 대상 `code` 목록과 건수 출력
  3. `search_text` NULL/공백 발견 시 즉시 abort
  4. leaf 정규식(`^[0-9]+-[0-9]+-[a-z]+$`) 외 코드 발견 시 즉시 abort
  5. OpenAI API 호출 없음
  6. DB UPDATE 없음
  7. ethics_codes 조회/검증 없음 (`--patterns-only`와 함께 사용)
  8. **`verify_embeddings()` 호출 없음** — dry-run은 아직 아무것도 업데이트하지 않았으므로 임베딩 저장 검증 자체가 무의미. `fetch_patterns()` 대상 행 검사까지만 수행한다.

**`--dry-run` 성공 조건 (exit 0)**:
- 대상 건수 > 0
- 전원 `is_active=TRUE AND detection_strategy='vector'` AND leaf 정규식 통과
- 전원 `search_text` 비어있지 않음
위 조건 중 하나라도 미달이면 exit 1 (STEP 6 중단).

> **`--dry-run` API key 정책**: dry-run은 DB 대상 검증 목적이므로 `OPENAI_API_KEY` 검사와
> OpenAI client 생성을 **건너뛴다**. 실제 임베딩 실행 모드에서만 API key를 요구한다.
> 기존 스크립트의 `main()` 초반 API key 검사 블록을 dry-run 분기 이후로 이동해야 한다.

```bash
# 실행 순서
python scripts/generate_embeddings.py --db-url "$DATABASE_URL" --patterns-only --dry-run
# exit 0 확인 후
python scripts/generate_embeddings.py --db-url "$DATABASE_URL" --patterns-only
```

*`--dry-run`은 스크립트 대상 행 검증 목적. `search_pattern_candidates` RPC의 런타임 결과 검증은 대체하지 않는다. RPC 검증은 Phase D-24 스모크 테스트에서 실제 임베딩으로 수행한다.*

---

**C-12. `fetch_patterns()` 수정**

```sql
-- active vector leaf 전체를 가져온다 (search_text 조건 제거)
-- search_text NULL/공백 검증은 Python에서 수행 (아래 참조)
SELECT id, code, name, search_text, detection_strategy
FROM public.patterns
WHERE is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$';
-- description_embedding IS NULL 조건 삭제 (직접 덮어쓰기)
```

**Python 레이어 NULL/공백 검증 (SQL에서 하지 않는 이유)**:
SQL에서 미리 걸러내면 결함 행이 조용히 제외되어 `--dry-run`이 오통과할 수 있다.
Python에서 명시적으로 검사해야 결함이 가시화된다.

`generate_embeddings.py`는 `psycopg2` 기본 cursor를 사용하여 tuple을 반환하므로,
dict 접근(`row["search_text"]`)이 아니라 **tuple unpacking** 방식으로 구현해야 한다.

```python
# psycopg2 기본 cursor → tuple 반환
for pid, code, name, search_text, detection_strategy in patterns:
    if not search_text or not search_text.strip():
        print(f"ERROR: search_text 결함: {code} — 즉시 중단")
        sys.exit(1)
```

---

**C-13. 임베딩 입력 및 실패 처리**

- 임베딩 소스: `search_text` 단독 (description 혼합 없음)
- `search_text` NULL/공백: 폴백 없이 즉시 raise

---

**C-14. `verify_embeddings()` 동일 필터 적용**

메인 쿼리와 동일한 `is_active=TRUE AND detection_strategy='vector' AND code ~ leaf 정규식` 필터. `is_meta_pattern=FALSE` 또는 `hierarchy_level=3` 단독 조건 사용 금지.

---

**C-15. CLI는 NULL 초기화 SQL 작성하지 않음**

active vector leaf를 NULL로 먼저 비우지 않고 직접 UPDATE 덮어쓰기. 초기화와 재생성 사이 검색 공백 발생 위험 제거.

*ethics_codes 쪽 IS NULL 조건은 기존 NULL 보충 로직 유지 (--patterns-only로 이미 우회되나, 혹여 실행될 경우 기존 임베딩 재생성 차단).*

---

## Phase C-2 — 실행 직전 백업

기획자가 SQL Editor에서 직접 실행. CLI 자동 실행 금지.

```sql
-- 1순위: private 스키마 백업 테이블 (실제 벡터 값 포함, 롤백 가능)
-- 테이블명 YYYYMMDD_HHMM: 실행 시각으로 직접 채울 것 (같은 날 재실행 시 충돌 방지)
-- 예: 2026년 5월 10일 10:30 실행 시 → private._backup_patterns_embeddings_step6_20260510_1030
-- 삭제는 STEP 7 완료 후 별도 승인으로 처리한다.
CREATE SCHEMA IF NOT EXISTS private;

CREATE TABLE private._backup_patterns_embeddings_step6_YYYYMMDD_HHMM AS
SELECT
  id, code, name, detection_strategy,
  description_embedding,  -- 실제 벡터 값 (롤백용)
  updated_at
FROM public.patterns
WHERE is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
ORDER BY code;
-- 테이블명 HHMM: 같은 날 재실행 시 충돌 방지
```

```sql
-- 2순위 (백업 테이블 생성 불가 시): 대상 행 스냅샷 SELECT → CSV 저장
SELECT id, code, name, detection_strategy,
       description_embedding IS NOT NULL AS had_embedding,
       description_embedding::text AS old_vector,  -- 복원 가능
       updated_at
FROM public.patterns
WHERE is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
ORDER BY code;
```

---

## Phase D — 실행 및 사후 검증

**D-17. 스크립트 실행**

```bash
python scripts/generate_embeddings.py --db-url "$DATABASE_URL" --patterns-only
```

---

**D-18. STEP 6 대상 외 patterns 변경 없음 확인**

```sql
-- "STEP 6 대상 조건의 부정"으로 확인
-- structural / parent / inactive / 대분류 / 기타 모두 포괄
SELECT code, name, detection_strategy, is_active, updated_at
FROM public.patterns
WHERE NOT (
  is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
)
AND updated_at > TIMESTAMPTZ '<step6_start_ts>';  -- A-0에서 기록한 값 대입
-- 기대: 0건
```

---

**D-19. `ethics_codes` 변경 없음 확인**

```sql
SELECT COUNT(*) AS changed_ethics_codes
FROM public.ethics_codes
WHERE updated_at > TIMESTAMPTZ '<step6_start_ts>';  -- A-0에서 기록한 값 대입
-- 기대: 0
```

---

**D-20. active vector leaf 임베딩 누락 0건**

```sql
SELECT code, name FROM public.patterns
WHERE is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
  AND description_embedding IS NULL;
-- 기대: 0건
```

---

**D-21. 벡터 차원 확인**

```sql
-- STEP 6 대상(active vector leaf)에 한정하여 차원 확인
SELECT DISTINCT vector_dims(description_embedding) AS dims
FROM public.patterns
WHERE is_active = TRUE
  AND detection_strategy = 'vector'
  AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
  AND description_embedding IS NOT NULL;
-- 기대: 1536 단일값
```

---

**D-22. active leaf 중 규범 매핑 0건 없음 확인**

```sql
-- 1순위: STEP 6 직접 대상 — active vector leaf
SELECT p.code, p.name, COUNT(per.id) AS relation_count
FROM patterns p
LEFT JOIN pattern_ethics_relations per ON per.pattern_id = p.id
WHERE p.is_active = TRUE
  AND p.detection_strategy = 'vector'
  AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
GROUP BY p.id, p.code, p.name
HAVING COUNT(per.id) = 0
ORDER BY p.code;
-- 기대: 0건 (STEP 3에서 76개 전원 매핑 완료)
```

```sql
-- 2순위 (보조): active leaf 전체 — vector + structural 합산
-- structural leaf도 Sonnet 확정 후 규범 조회 대상이므로 최종 방어선으로 확인
SELECT p.code, p.name, p.detection_strategy, COUNT(per.id) AS relation_count
FROM public.patterns p
LEFT JOIN public.pattern_ethics_relations per ON per.pattern_id = p.id
WHERE p.is_active = TRUE
  AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
GROUP BY p.id, p.code, p.name, p.detection_strategy
HAVING COUNT(per.id) = 0
ORDER BY p.detection_strategy, p.code;
-- 기대: 0건
```

---

**D-23. 통계 갱신**

```sql
ANALYZE public.patterns;
-- 참고: 현재 패턴 테이블에 벡터 인덱스 없음 (150건 미만 → sequential scan 유지).
-- 이 명령은 인덱스 재생성이 아니라 쿼리 플래너용 통계 정보 갱신 목적.
```

---

**D-24. 스모크 테스트 2단계** *(RPC 검증 포함)*

**1단계 — 벡터 후보 검증** *(5~10건, 골든셋 TP 케이스)*

CLI가 실제 기사 청크 임베딩을 생성하여 `search_pattern_candidates` RPC를 직접 호출하고, 반환된 모든 후보를 로그로 출력:

- 정답 leaf 코드가 Top-7에 포함되는가
- similarity 분포(min/median/max) 출력 — `search_text` 기반이라 유사도 절대값이 description 기반보다 낮을 수 있음. 정답이 Top-7에 있으나 threshold=0.2 근처면 STEP 7에서 threshold 재튜닝 과제로 남김 (임베딩 실패가 아님)
- **parent 코드 / structural 코드 / inactive 코드 유입 여부 0건 확인** (RPC 보강의 효과 검증)

*이 단계는 `--dry-run`으로 대체하지 않는다.*

> **CTE 격리 검증과 골든셋 TP 검증은 별개 단계다.**
> - 아래 CTE 쿼리: DB에 저장된 임베딩 1건(`LIMIT 1`)으로 RPC 필터 격리 효과를 검증. 저장 임베딩 재활용 목적.
> - 골든셋 TP 검증(1단계 로그 출력): 실제 기사 청크 임베딩을 새로 생성하여 정답 코드 Top-7 포함 여부 확인.
> - CTE 쿼리를 골든셋 임베딩으로 대체하지 않는다.

**RPC 격리 검증 — 2단계 순서로 실행**

```sql
-- [1단계] RPC 결과 건수 확인 (0건이면 임베딩 미반영 또는 필터 오류)
WITH rpc_result AS (
  SELECT * FROM public.search_pattern_candidates(
    (
      SELECT description_embedding
      FROM public.patterns
      WHERE is_active = TRUE
        AND detection_strategy = 'vector'
        AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
        AND description_embedding IS NOT NULL
      LIMIT 1
    ),
    -1.0,   -- threshold=-1.0: 코사인 유사도 최솟값, 전체 반환 유도
    500     -- match_count 500: 전체 패턴 수 이상
  )
)
SELECT COUNT(*) AS candidate_count FROM rpc_result;
-- 기대: 1 이상. 0건이면 STEP 6 즉시 중단 — 임베딩 재생성 실패 또는 RPC 오류 의심.
```

```sql
-- [2단계] 이상 코드 유입 여부 확인 (parent/structural/inactive)
-- ⚠️ A-3에서 확인한 실제 반환 컬럼명으로 pattern_id / pattern_code를 맞춰 수정할 것
WITH rpc_result AS (
  SELECT * FROM public.search_pattern_candidates(
    (
      SELECT description_embedding
      FROM public.patterns
      WHERE is_active = TRUE
        AND detection_strategy = 'vector'
        AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
        AND description_embedding IS NOT NULL
      LIMIT 1
    ),
    -1.0,
    500
  )
)
SELECT r.pattern_code, p.is_active, p.detection_strategy
FROM rpc_result r
JOIN public.patterns p ON p.id = r.pattern_id
WHERE NOT (
  p.is_active = TRUE
  AND p.detection_strategy = 'vector'
  AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
);
-- 기대: 0건 (parent/structural/inactive 유입 없음)
```

**D-24 성공 조건 (두 쿼리 모두 통과해야 함)**:
- 1단계: `candidate_count` ≥ 1
- 2단계: 이상 코드 0건

**2단계 — 전체 파이프라인** *(1~2건)*

정상 케이스 1건으로 Sonnet 판단까지 전체 파이프라인 실행 확인.

> **골든셋 TP 스모크 테스트 로그 요구사항**
> CLI는 골든셋 TP 케이스(5~10건)를 **운영값 `threshold=0.2`, `match_count=7`** 로도 별도 실행하고,
> 각 케이스별로 아래 항목을 로그로 출력해야 한다:
> - 반환된 후보 코드 목록
> - 각 후보의 similarity 값
> - 정답 leaf 코드의 Top-7 포함 여부 (HIT / MISS)
>
> 목적: "RPC 필터는 정상이지만 운영 Top-7에서 정답이 안 잡히는 경우"를
> STEP 6 임베딩 실패가 아닌 **STEP 7 threshold 재조정 과제**로 명확히 분리하기 위함.
> threshold=0.2 근처에서 정답이 잡히면 STEP 7에서 조정 가능 범위로 간주한다.

---

**D-25. `unmatched_vector_candidates` 확인**

`pattern_matcher.py`에 해당 필드가 존재하면 → 빈 배열인지 확인.

존재하지 않으면 → D-24의 RPC 결과 검증으로 대체 (새 필드 추가 금지).

---

## Phase E — STEP 7 진입 전

**E-26. 캐시 우회 정책 확정**

`storage.py`의 기사 분석 결과 캐시가 골든셋 26건 벤치마크에서 hit되면 새 임베딩·RPC 효과를 측정할 수 없음. 다음 중 하나:

- 벤치마크 스크립트(`benchmark_pipeline_v3.py`)에 `use_cache=False` 파라미터 추가
- 골든셋 URL에 대한 캐시 테이블 레코드 삭제
- 캐시 조회 우회 로그 확인

---

## 의무 완료 쿼리 요약 (감리 기준)

| Phase | 쿼리 목적 | 기대값 |
| --- | --- | --- |
| A-1 | 분포 확인 | active·vector·leaf ≈ 64~75건 |
| A-2 | search_text NULL/공백 | 0건 |
| D-18 | STEP 6 대상 외 변경 없음 | 0건 |
| D-19 | ethics_codes 변경 없음 | 0건 |
| D-20 | leaf 임베딩 누락 | 0건 |
| D-21 | 벡터 차원 | 1536 |
| D-22 | 규범 매핑 없는 leaf | 0건 |
| D-24 | RPC 결과 이상 코드 | 0건 |

---

## 컬럼명 확정

| 테이블 | 임베딩 컬럼 |
| --- | --- |
| `patterns` | `description_embedding` |
| `ethics_codes` | `text_embedding` |

---

## CLI 지시문 작성 시 반드시 포함할 지시

1. Phase A-0에서 `step6_start_ts`를 기록하고, D-18·D-19 쿼리의 `<step6_start_ts>` 자리에 그 값을 대입한다. `NOW()`로 대체하지 않는다.
2. `--patterns-only`와 `--dry-run`을 Phase C-11에서 함께 구현한다.
3. `--dry-run`은 스크립트 대상 행 검증용이며, `search_pattern_candidates` RPC 런타임 검증을 대체하지 않는다. RPC 검증은 Phase D-24 스모크 테스트에서 실제 임베딩으로 수행한다.
4. 백업 테이블은 기획자가 SQL Editor에서 직접 생성한다. CLI 자동 실행 금지.
5. ethics_codes 처리 로직(fetch/update/verify) 전체를 `--patterns-only` 모드에서 skip한다.
6. `description_embedding IS NULL` 조건 삭제는 patterns 쪽만. ethics_codes IS NULL은 유지.
7. 감리자 귀속 주석 포함하지 않는다. 실행 기준만 남긴다.

---