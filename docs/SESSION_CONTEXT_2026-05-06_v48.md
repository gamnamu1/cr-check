# 세션 컨텍스트 — 2026-05-06 v48

## 프로젝트 한줄 요약

CR-Check: 한국 뉴스 기사의 언론 윤리 위반 여부를 AI가 진단하는 공익 도구. 프로덕션 가동 중 (Railway + Vercel + Supabase).

---

## 현 위치 한눈에

**MASTER_EXECUTION_PLAN_v1.0.md 기준: STEP 4 완전 완료 (승인 게이트 통과) → STEP 5 진입 대기.**

```
✅ STEP 0-B  윤리규범 DB 정리 (Phase 1~3 전체)
✅ STEP 2    DB 마이그레이션 + 107개 패턴 INSERT + 감리 + 후속 수정
✅ STEP 3    pattern_ethics_relations 재배분 (Phase 1~4 전체)
✅ STEP 4   코드 품질 개선 (4-A/4-B/4-C 전체)
🔲 STEP 5   Sonnet 프롬프트 재설계  ← 다음 작업
🔲 STEP 6   임베딩 재생성
🔲 STEP 7   골든셋 재정비 + R8 벤치마크 + threshold 재조정
```

---

## 오늘(2026-05-06) 완료된 전체 작업

### STEP 4-A: _build_ethics_context() 구조화

- `backend/core/report_generator.py`의 `_build_ethics_context()` 함수 재작성
- primary(violates + strong/moderate) / reference(related_to + strong/moderate) 두 그룹 분리
- 중복 제거: primary 먼저 완성 후 seen set 공유로 reference 필터링 (순서 보장)
- weak / exception_of 항목 전부 무시
- primary 0건 시 헤더·구분선 생략, reference만 출력
- 출력 형식: `### {ethics_title} (코드: {ethics_code}, Tier {ethics_tier})` — Sonnet 환각 방지
- 6인 감리 완료 (Antigravity·Gemini·Manus·NotebookLM·Perplexity·Codex)

### STEP 4-B: analysis_ethics_snapshot 재활성화

- `backend/core/storage.py`: `_insert_ethics_snapshot()` 헬퍼 추가, `save_analysis_result()` 수정
  - analysis_results INSERT 직후 analysis_id 추출
  - 스냅샷 대상: primary(violates + strong/moderate) 우선, 0건이면 reference fallback
  - ethics_codes 배치 SELECT로 code → (id, version) 매핑
  - graceful degradation (실패 시 logger.warning, share_id 반환 정상)
- `backend/main.py`: save_analysis_result() 호출부에 ethics_refs 인자 추가
- 5인 감리 완료

### STEP 4-C: get_ethics_for_patterns RPC 수정

**SQL 마이그레이션** (`supabase/migrations/20260505231952_rpc_ethics_context_filter.sql`)
- DROP + CREATE OR REPLACE로 기존 1-arg 함수 교체
- article_context TEXT DEFAULT 'general' 파라미터 추가
- direct_codes CTE: 필터 A(applicable_contexts) + 필터 B(strength != 'weak' AND relation_type != 'exception_of')
- parent_chain CTE 재귀 SELECT: 필터 A만 적용 (per 테이블 없으므로 필터 B 제외)
- DB 실행 완료 ✅
- active_ethics_codes 뷰 재생성 (applicable_contexts 컬럼 인식 누락 수정) ✅

**Python 코드**
- `backend/core/pipeline.py`: `_infer_article_context()` 함수 추가 (9개 컨텍스트, 복합 키워드 사전)
  - TODO (STEP 7): pattern_codes 기반 추론 로직 추가 예정, 현재 미사용
- `backend/core/report_generator.py`:
  - `_rpc_get_ethics()`, `fetch_ethics_for_patterns()`, `generate_report()` 시그니처에 article_context 추가
  - _rpc_get_ethics 3곳(1차·재시도·0건 재시도) 모두 article_context 전달
  - REST fallback: select에 applicable_contexts 추가, for 루프 안에서 필터링
- 6인 감리 완료 (Antigravity·Gemini·Manus·NotebookLM·Perplexity + 추가 라운드)

### STEP 4 승인 게이트

| 게이트 | 항목 | 결과 |
|---|---|---|
| RPC 등록 | pronargs=2, 1행만 존재 (구버전 잔존 없음) | ✅ PASS |
| 게이트 2 | weak/exception_of 0건 확인 | ✅ PASS |
| 게이트 3 | applicable_contexts 필터 정상 동작 | ✅ PASS |
| 게이트 1 | snapshot 로직 코드 검증 완료 | ✅ 조건부 PASS |

※ 게이트 1: 임베딩이 구버전(1-6-1 등 구코드 체계)이라 TP 기사 분석 불가. STEP 6 임베딩 재생성 후 재검증.

---

## DB 현황 (2026-05-06 기준)

### patterns 테이블

| 구분 | 건수 | 비고 |
|---|---|---|
| 대분류 (hierarchy_level=1) | 8 | 레거시 체계 |
| 소분류·부모 (level=3, 2-segment) | 34 | 기존 30 + 신규 부모 4 |
| leaf (level=3, 3-segment) | 107 | STEP 2에서 INSERT |
| **합계** | **149** | |

- `is_active=TRUE, structural`: 17건 (leaf 12 + 부모 5)
- `is_active=TRUE, vector`: 87건
- `is_active=FALSE`: 33건 (I-트랙 31 + 메타패턴 2)

**⚠️ 스키마 주의**: `hierarchy_level=2`가 비어 있음. 부모·leaf 모두 level=3에 저장.
leaf 필터 쿼리는 반드시 정규식 `p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'` 사용.

### ethics_codes 테이블

- 총 394건, applicable_contexts 배정 완료 (즉시 필터 작동)
- is_citable=TRUE: 225건

### pattern_ethics_relations 테이블

- 활성 leaf 76개 전원 매핑 완료 (cnt ≥ 1)
- source별 분포: PCP 44.6% / JEC 30.7% / PCE 7.5% / EPG 4.9% / 기타 12.3%

---

## STEP 5 상세 (다음 작업)

> 선행 조건: STEP 4 완료 ✅
> 실행 환경: Claude Code CLI
> 마스터 플랜 §11 참조

### STEP 5-A: 패턴 카탈로그 형식 재설계

- 119개 패턴을 계층 경로 + report_framing 힌트 포함 형식으로 재설계
- structural 패턴 별도 섹션 분리 (하드코딩 → DB 동적 로드)

### STEP 5-B: 혼동 쌍 DB화

- 현재 5개 혼동 쌍을 `_SONNET_SOLO_PROMPT`에서 `pattern_confusion_pairs` 테이블로 분리

### STEP 5-C: 메타패턴 코드 DEPRECATED 처리

- pipeline.py, report_generator.py, meta_pattern_inference.py에 DEPRECATED 주석 추가 (삭제 금지)

---

## STEP 6 이전에 처리할 항목 (대기 중)

- `4-3-b` 혐오 어휘 현실화 (구식 밈 제거, 최신 표현 추가)
- `3-3-a` description 재작성 (4개 인과 오류 압축 과부하)
- `5-2-a` vs `6-6-b` 전문용어 어휘 중복 해소

---

## 현재 파이프라인 상태 (STEP 4 반영)

```
기사 URL
  → 캐시 조회 (storage.py)
  → 스크래핑 (scraper.py · 59개 전용 파서)
  → 청킹 + 임베딩 + 벡터 검색
       text-embedding-3-small / threshold=0.2, Top-7
       ※ 임베딩 소스: 구버전 기준 (STEP 6에서 search_text 기준으로 전환 예정)
  → Sonnet Solo 패턴 감지 (Phase 1)
       claude-sonnet-4-5-20250929, temp=0.0
       패턴 카탈로그 28개 + structural 4개 고정 (← STEP 5에서 107개로 확장 예정)
       미감지 → TN (_TN_MESSAGE)
  → 메타패턴 추론 — 비활성
  → 윤리규범 조회 (fetch_ethics_for_patterns)
       ✅ article_context 필터 적용 (STEP 4-C)
       ✅ weak/exception_of 제외 (STEP 4-C)
  → _build_ethics_context() — primary/reference 분리 출력 (STEP 4-A)
  → Sonnet 리포트 생성 (Phase 2) — 3종 JSON
  → DB 저장 + share_id 발급
       ✅ analysis_ethics_snapshot INSERT (STEP 4-B, TP 시 작동)
```

---

## 벤치마크 이력 및 목표

| 버전 | FR | Precision | TN FP |
|---|---|---|---|
| R5 (현 프로덕션) | 36.7% | 44.2% | 6/6 |
| **STEP 4 후 목표** | **45%** | **55%** | **5/6 이하** |
| STEP 5 후 목표 | 60% | 70% | 4/6 이하 |
| R8 목표 (STEP 7) | 75% | 80% | 3/6 이하 |

※ STEP 4 벤치마크는 STEP 6(임베딩 재생성) 완료 후 R8과 통합 측정 예정.

---

## 핵심 설계 결정 (변경 불가)

- Sonnet Solo 1-Call 구조 유지
- TN 케이스: `pipeline.py`의 `_TN_MESSAGE` 정적 메시지
- 인용 방식: 〔규범 원문〕 마커 직접 출력
- 이진 게이트: 제거 확정 (R5)
- 임베딩 소스: STEP 6에서 `search_text` 기준으로 전환 예정
- 메타패턴 추론: 완전 비활성화 확정
- GitHub 커밋: 사람이 직접 수행
- applicable_contexts: `text[]` 타입, `ARRAY['context']` 형태로 저장
- 교차 감리 원칙: 모든 감리자 동일 프롬프트·역할 분리 금지
- 분리 기준: primary(violates + strong/moderate) / reference(related_to + strong/moderate) / 제외(weak, exception_of)

---

## 절대 원칙

1. CLI 자동 INSERT/UPDATE 금지 — DB 변경은 기획자가 SQL Editor에서 직접 실행
2. diff 선제시 → 기획자 승인 → 커밋 순서 엄수
3. STEP 단위 승인 게이트 — 승인 없이 다음 STEP 진행 금지
4. 단계 임의 통합 금지 — CLI는 전달받은 단계 지시만 실행
5. ON CONFLICT DO NOTHING (UPSERT 절대 금지)
6. is_citable 일괄 변경 금지 — 실질 내용 확인 후 개별 판단
7. STEP마다 분포 확인 쿼리 2개 의무 실행 — 총량만으로 PASS 불가

---

## 도구·환경

- 프로덕션 DB: DATABASE_URL in .env (Transaction pooler, port 6543)
- Supabase MCP: supabase-cr-check (Antigravity 접속 가능 여부 매 세션 확인)
- 벤치마크 스크립트: `scripts/benchmark_pipeline_v3.py`
- 골든셋: `docs/golden_dataset_final.json` (26건: TP 21 + TN 5)
- 기사 본문: `Golden_Data_Set_Pool/article_texts/*.txt`
- Antigravity: Strict Mode On, Deny List 9개, Agent Auto-Fix Lints Off

---

## 주요 산출물 (누적)

| 파일 | 내용 | 상태 |
|---|---|---|
| `supabase/migrations/20260502145125_master_migration.sql` | STEP 2 마이그레이션 | DB 실행 완료 |
| `supabase/seeds/patterns_seed.sql` | 107개 패턴 leaf INSERT | DB 실행 완료 |
| `supabase/seeds/step2_audit_fix_critical.sql` | CRITICAL 수정 | DB 실행 완료 |
| `supabase/seeds/step2_audit_fix_content.sql` | content 수정 (5개 패턴) | DB 실행 완료 |
| `supabase/seeds/ethics_codes_context_seed.sql` | applicable_contexts 394건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH1_DELETE.sql` | 오연결 6건 삭제 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH2_INSERT.sql` | DB전용소분류 27건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH3_INSERT.sql` | 의미충돌소분류 20건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH4_INSERT.sql` | 빈leaf 1-1·1-4·1-5 49건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH5_INSERT.sql` | 빈leaf 2-1~3-4 34건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH6_INSERT.sql` | 빈leaf 4-2~7-1 43건 | DB 실행 완료 |
| `supabase/migrations/20260505231952_rpc_ethics_context_filter.sql` | STEP 4-C RPC 수정 | DB 실행 완료 |
| `backend/core/report_generator.py` | STEP 4-A/4-C 반영 | 커밋 완료 예정 |
| `backend/core/pipeline.py` | STEP 4-C 반영 | 커밋 완료 예정 |
| `backend/core/storage.py` | STEP 4-B 반영 | 커밋 완료 예정 |
| `backend/main.py` | STEP 4-B 반영 | 커밋 완료 예정 |
| `docs/_scratch/step1_output_v3.md` | 107개 leaf 코드 체계 기준표 | STEP 5 이후도 참조 |

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v41~v46 | 2026-04-28~05-02 | STEP 0~2 완료 과정 |
| v47 | 2026-05-03 | STEP 3 완전 완료 (Phase 1~4). STEP 4 진입 대기. |
| **v48** | **2026-05-06** | **STEP 4 완전 완료 (4-A/4-B/4-C). STEP 5 진입 대기.** |
