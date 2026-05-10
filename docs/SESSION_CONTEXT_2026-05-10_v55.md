# 세션 컨텍스트 — 2026-05-10 v55

## 프로젝트 한줄 요약

CR-Check: 한국 뉴스 기사의 언론 윤리 위반 여부를 AI가 진단하는 공익 도구. 프로덕션 가동 중 (Railway + Vercel + Supabase).

---

## 현 위치 한눈에

**MASTER_EXECUTION_PLAN_v1.0.md 기준: STEP 6 전체 완료 → STEP 7 진입 대기.**

```
✅ STEP 0~5 (이전 세션 완료)
✅ STEP 6   임베딩 재생성 — Phase A~E 전체 완료 (2026-05-10) ← 본 세션
🔲 STEP 7   골든셋 재정비 + R8 벤치마크 + threshold 재조정
```

---

## 2026-05-10 완료된 작업 (v54 → v55)

### Phase A — 사전 점검 (기획자 SQL Editor)
- active·vector·leaf 패턴: **64건**
- `search_text` NULL/공백: **0건**
- `search_pattern_candidates` 실제 시그니처: `(vector, double precision, integer)`
- 기존 RPC 필터: `is_meta_pattern=FALSE` 단독 → B-7 마이그레이션 필수 확인

### Phase B-7 — RPC 4-필터 마이그레이션
- 파일: `supabase/migrations/20260510144927_restrict_search_pattern_candidates_to_vector_leaf.sql`
- 4개 필터 적용: `is_active=TRUE` / `detection_strategy='vector'` / `code ~ '^[0-9]+-[0-9]+-[a-z]+$'` / `description_embedding IS NOT NULL`
- 적용은 기획자가 SQL Editor에서 직접 + `NOTIFY pgrst, 'reload schema'` + `pg_get_functiondef` 검증 통과

### Phase C — `generate_embeddings.py` 8건 변경
- C-12-a: `_LEAF_CODE_RE` 모듈 상수
- C-11: `--patterns-only` / `--dry-run` 플래그 + dry-run 단독 차단 + API key 분기 이후 이동
- C-12-b: `fetch_patterns()` 4-필터 SQL + NULL/공백/leaf 정규식 즉시 중단
- C-12-c: `prepare_texts()` 5컬럼 언패킹
- C-14: `verify_embeddings()` patterns 쿼리 3건 전면 교체 (보충 지시: 병기 금지) + `pattern_dims` DISTINCT 리스트
- C-11 분기: ethics_codes UPDATE skip / Verify 출력 분기 / `all_ok == [EMBEDDING_DIM]`
- AST OK, 4-필터 SQL 4회, 신규 플래그 정상, 388라인

### Phase C-2 백업 + dry-run + 본 실행
- Phase C-2 백업: 기획자 SQL Editor 직접 (64건)
- dry-run: exit 0, leaf 정규식·search_text 검증 통과
- 본 실행: **64/64 임베딩 재생성** (1배치, ~22,400 tokens × $0.02/1M = **~$0.0004**)
- Verification: 64/64 with embedding, **`pattern_dims=[1536]`**, all_ok 통과

### Phase D-24 [1단계] — RPC 격리 검증 SQL 제시
- candidate_count 확인 + 이상 코드 유입 0건 확인 두 쿼리를 SQL Editor용 초안으로 제시
- 기획자가 SQL Editor에서 직접 실행

### Phase D-24 [2단계] — STEP 7로 위임
- `golden_dataset_labels.json`의 `pattern_id`가 **모두 부모(2-segment) 형식 43건 전수**
- v3 leaf 형식 0건 → "vector-test 대상 expected" 0건 → 케이스 선택 불가
- `article_key_text` 평균 174자, 최대 426자 — chunker `SHORT_ARTICLE=500` 미만 (단일 청크 처리)
- `article_texts/` 실제 위치: `/Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts/` (프로젝트 외부)
- 결정: **옵션 C (STEP 7 골든셋 재정비 후 본격 D-24 수행)**

### Phase E — 캐시 우회 정책 확인

Phase E 확인 결과, benchmark_pipeline_v3.py는 URL 기반 /analyze 캐시 경로를
타지 않고 analyze_article(article_text, run_sonnet=False)를 직접 호출한다.
따라서 STEP 7/R8 벤치마크에서 기존 articles / analysis_results 캐시가 새
임베딩·RPC 효과 측정을 왜곡할 가능성은 낮다. production 캐시 삭제는 불필요하며,
골든셋 URL을 production /analyze로 직접 재분석하는 별도 시나리오에서만 검토한다.

---

## 다음 세션: STEP 7 진입

**실행 문서**: `docs/MASTER_EXECUTION_PLAN_v1.0.md` §13 STEP 7 (또는 신규 STEP7_*_PLAN 작성)

### STEP 7 핵심 작업
- **STEP 7-A**: 골든셋 재정비 — `expected_patterns`의 부모 코드 → v3 leaf 매핑 작성, `article_texts/`와 결합 (외부 디렉터리 경로 명시)
- **STEP 7-B**: R8 벤치마크 — 갱신된 골든셋 + 신규 임베딩 + 4-필터 RPC + STEP 5 프롬프트로 측정
- **STEP 7-C**: threshold/match_count 재조정 (운영값 0.2 / 7 기준 vs 보조값 0.15 / 50 비교)
- **STEP 7-D**: 기획자 수동 리포트 품질 평가

### STEP 7 진입 전 권장 검증 (선택)
- **DB count 비교**: 벤치마크 실행 전후 `articles`/`analysis_results` count 측정 → 변동 0건이면 캐시 미경유 + INSERT 미발생 동시 증명 (Phase E §6 SQL)

---

## DB 현황 (2026-05-10 본 실행 후)

### patterns 테이블 — 임베딩
- 임베딩 보유 패턴: **64/64** (active vector leaf 100% 커버)
- 임베딩 차원: 1536 (DISTINCT 1개 — 정확히 [1536])
- 임베딩 모델: `text-embedding-3-small`
- 임베딩 입력: `search_text` 단독 (description 혼합 없음)

### search_pattern_candidates RPC
- 시그니처: `(vector, double precision DEFAULT 0.2, integer DEFAULT 7)`
- 필터: 4개 (is_active, detection_strategy='vector', leaf 정규식, description_embedding NOT NULL)

### 그 외 테이블 (변동 없음 — v54 기준 유지)
- patterns 총 149건 (대분류 8 + 부모 34 + leaf 107)
- pattern_ethics_relations: 활성 leaf 76개 전원 매핑

---

## 핵심 설계 결정 (변경 없음, v54에서 계승)

(생략 — v54와 동일)

---

## 절대 원칙 (변경 없음)

(생략 — v54와 동일)

---

## 도구·환경 (변경 없음)

(생략 — v54와 동일)

---

## 주요 산출물 (누적)

| 파일 | 내용 | 상태 |
|---|---|---|
| `docs/STEP6_EMBEDDING_REGEN_PLAN_v9.md` | STEP 6 세부 실행 계획 | 완료 (실행 종료) |
| `supabase/migrations/20260510144927_restrict_search_pattern_candidates_to_vector_leaf.sql` | RPC 4-필터 | DB 실행 완료 (기획자 직접) |
| `scripts/generate_embeddings.py` | STEP 6 Phase C 반영 | 로컬 커밋 대기 |
| (이전 산출물 — v54와 동일) | | |

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| (v41~v53 — v54와 동일) | | |
| v54 | 2026-05-10 | STEP 6 계획 확정 (`STEP6_EMBEDDING_REGEN_PLAN_v9.md`, 11차 감리 통과). 문서 정리. |
| **v55** | **2026-05-10** | **STEP 6 전체 완료 (Phase A~E). 64건 임베딩 재생성 (~$0.0004, pattern_dims=[1536]). RPC 4-필터 마이그레이션 적용. Phase D-24 [2단계]는 STEP 7 골든셋 재정비로 위임. Phase E: 벤치마크는 URL 캐시 우회 구조 확인 — 별도 캐시 정리 불필요.** |
