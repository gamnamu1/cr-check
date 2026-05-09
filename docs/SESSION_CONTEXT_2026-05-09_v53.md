# 세션 컨텍스트 — 2026-05-09 v53

## 프로젝트 한줄 요약

CR-Check: 한국 뉴스 기사의 언론 윤리 위반 여부를 AI가 진단하는 공익 도구. 프로덕션 가동 중 (Railway + Vercel + Supabase).

---

## 현 위치 한눈에

**MASTER_EXECUTION_PLAN_v1.0.md 기준: STEP 5 전체 완료 → STEP 6 대기.**

```
✅ STEP 0-B  윤리규범 DB 정리 (Phase 1~3 전체)
✅ STEP 2    DB 마이그레이션 + 107개 패턴 INSERT + 감리 + 후속 수정
✅ STEP 3    pattern_ethics_relations 재배분 (Phase 1~4 전체)
✅ STEP 4    코드 품질 개선 (4-A/4-B/4-C 전체)
✅ STEP 5   Sonnet 프롬프트 재설계 — 전체 완료
            ↳ 5-A: 블록1·2·3 CLI 실행 완료 (v51, 2026-05-08) ✅
            ↳ 5-B: 혼동 쌍 DB화 완료 (v53, 2026-05-09) ✅
                   pattern_confusion_pairs 테이블 생성·시드 삽입
                   pattern_matcher.py 수정 완료
            ↳ 5-C: 메타패턴 DEPRECATED 처리 완료 (v53, 2026-05-09) ✅
                   pipeline.py / report_generator.py / meta_pattern_inference.py
            ↳ 로컬 커밋 대기 (STEP 5-B/C 분량, 푸시는 STEP 7 완료 후)
🔲 STEP 6   임베딩 재생성
🔲 STEP 7   골든셋 재정비 + R8 벤치마크 + threshold 재조정
```

---

## 2026-05-09 완료된 전체 작업 (v52 → v53)

### STEP 5-B: pattern_confusion_pairs DB화

- **migration**: `supabase/migrations/20260509232754_pattern_confusion_pairs.sql` 생성·실행
- **seed**: `supabase/seeds/pattern_confusion_pairs_seed.sql` 생성·실행
  - 5개 v3 leaf 혼동 쌍 INSERT (dollar-quoted string, ON CONFLICT (code_a, code_b) DO NOTHING)
  - UNIQUE + CHECK 제약 포함
- **pattern_matcher.py** 수정 (6건):
  - `_confusion_pairs_cache` 전역 캐시 변수 추가
  - `_load_confusion_pairs(sb_url, sb_key)` 함수 추가
    - httpx REST, is_active=true, order=id
    - **성공 시에만 캐싱** (실패 시 빈 리스트 반환 + logger.warning, 재시도 가능)
  - `_build_sonnet_solo_prompt(sb_url, sb_key)` 함수 추가
    - `.replace()` 방식 (`.format()` 절대 금지 — JSON 중괄호 충돌 위험)
    - 혼동 쌍 없으면 `\n{3,}` → `\n\n` 정리
  - `_SONNET_SOLO_PROMPT` 내 DEPRECATED 주석 블록 삭제
  - `{confusion_pairs_section}` placeholder 삽입 ("★ 후보 패턴 활용" 뒤, "기사 길이별 가이드" 앞)
  - `match_patterns_solo()` system= → `_build_sonnet_solo_prompt()` 호출로 교체
- **DB 확인**: 5개 행, is_active=true 전부, id 오름차순 정상

### STEP 5-C: 메타패턴 DEPRECATED 처리

- **pipeline.py**:
  - `from .meta_pattern_inference import check_meta_patterns` → 주석 처리
  - `check_meta_patterns()` 호출 블록 전체(try/except 포함) → 주석 처리
  - `triggered_meta = []` 활성 코드로 유지 (generate_report 호출부 보호)
- **report_generator.py**:
  - `_build_meta_pattern_block()` def 바로 다음 주석 1줄 삽입
  - 함수 본체 및 line 694 호출 보존 (pipeline에서 `[]` 전달 → 실질 비활성화)
- **meta_pattern_inference.py**: 파일 최상단 3줄 DEPRECATED MODULE 주석 삽입
- **검증**: AST OK (3개 파일) / 활성 check_meta_patterns 호출 0건

---

## 다음 세션: STEP 6 (임베딩 재생성)

### 로컬 커밋 먼저 (세션 시작 전 감나무 직접)

```bash
git add backend/core/pipeline.py \
        backend/core/report_generator.py \
        backend/core/meta_pattern_inference.py \
        backend/core/pattern_matcher.py \
        supabase/migrations/20260509232754_pattern_confusion_pairs.sql \
        supabase/seeds/pattern_confusion_pairs_seed.sql

git commit -m "STEP 5-B/C: pattern_confusion_pairs DB화 + 메타패턴 DEPRECATED 처리"
```

### STEP 6 목표

`scripts/generate_embeddings.py` 수정:
- 임베딩 소스: `description` → `search_text`
- 임베딩 대상 필터: `is_active=TRUE AND detection_strategy='vector'` (structural 제외)
- 신규 119 leaf 패턴 대상 실행 (기존 38개 상위 패턴 임베딩 유지)

---

## DB 현황 (2026-05-09 기준)

### patterns 테이블

| 구분 | 건수 |
|---|---|
| 대분류 (hierarchy_level=1) | 8 |
| 소분류·부모 (level=3, 2-segment) | 34 |
| leaf (level=3, 3-segment) | 107 |
| **합계** | **149** |

- `is_active=TRUE, structural`: 17건 (leaf 12 + 부모 5)
- `is_active=TRUE, vector`: 87건
- `is_active=FALSE`: 33건 (I-트랙 31 + 메타패턴 2)

### pattern_confusion_pairs 테이블 (신규)

| id | code_a | code_b | is_active |
|---|---|---|---|
| 1 | 1-1-e | 1-4-d | true |
| 2 | 3-1-b | 3-2-b | true |
| 3 | 3-1-a | 3-4-a | true |
| 4 | 3-2-a | 6-4-a | true |
| 5 | 6-3-a | 6-2-c | true |

### ethics_codes 테이블

- 총 394건, applicable_contexts 배정 완료, is_citable=TRUE: 225건

### pattern_ethics_relations 테이블

- 활성 leaf 76개 전원 매핑 완료 (cnt ≥ 1)
- source별 분포: PCP 44.6% / JEC 30.7% / PCE 7.5% / EPG 4.9% / 기타 12.3%

---

## 벤치마크 이력 및 목표

| 버전 | FR | Precision | TN FP |
|---|---|---|---|
| R5 (현 프로덕션) | 36.7% | 44.2% | 6/6 |
| STEP 5 후 목표 | 60% | 70% | 4/6 이하 |
| R8 목표 (STEP 7) | 75% | 80% | 3/6 이하 |

※ STEP 4·5 벤치마크는 STEP 6(임베딩 재생성) 완료 후 R8과 통합 측정 예정.

---

## 현재 파이프라인 상태 (STEP 5 전체 반영)

```
기사 URL
  → 캐시 조회 (storage.py)
  → 스크래핑 (scraper.py · 59개 전용 파서)
  → 청킹 + 임베딩 + 벡터 검색
       text-embedding-3-small / threshold=0.2, Top-7
       ※ 임베딩 소스: 구버전 기준 (STEP 6에서 search_text 기준으로 전환 예정)
  → Sonnet Solo 패턴 감지 (Phase 1)
       claude-sonnet-4-5-20250929, temp=0.0
       패턴 카탈로그: v3 leaf 76건 (vector 64 + structural 12) — 3섹션 동적 구성
       few-shot 예시: v3 leaf 기준 7건 + structural 예시 1건
       혼동 쌍: pattern_confusion_pairs DB 동적 로드 (5쌍, _build_sonnet_solo_prompt)
       미감지 → TN (_TN_MESSAGE)
  → 메타패턴 추론 — 완전 비활성화 (STEP 5-C)
       pipeline.py: import + 호출 블록 주석 처리, triggered_meta=[] 고정
  → 윤리규범 조회 (fetch_ethics_for_patterns)
       ✅ article_context 필터 적용 (STEP 4-C)
       ✅ weak/exception_of 제외 (STEP 4-C)
  → _build_ethics_context() — primary/reference 분리 출력 (STEP 4-A)
  → Sonnet 리포트 생성 (Phase 2) — 3종 JSON
  → DB 저장 + share_id 발급
       ✅ analysis_ethics_snapshot INSERT (STEP 4-B, TP 시 작동)
```

---

## 핵심 설계 결정 (변경 불가)

- Sonnet Solo 1-Call 구조 유지
- TN 케이스: `pipeline.py`의 `_TN_MESSAGE` 정적 메시지
- 인용 방식: 〔규범 원문〕 마커 직접 출력
- 이진 게이트: 제거 확정 (R5)
- 임베딩 소스: STEP 6에서 `search_text` 기준으로 전환 예정
- 메타패턴 추론: 완전 비활성화 확정 (STEP 5-C)
- 혼동 쌍: pattern_confusion_pairs 테이블 DB 동적 로드 확정 (STEP 5-B)
- GitHub 커밋: 사람이 직접 수행. 푸시는 STEP 7 완료 후.
- applicable_contexts: `text[]` 타입, `ARRAY['context']` 형태로 저장
- 교차 감리 원칙: 모든 감리자 동일 프롬프트·역할 분리 금지

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
- Supabase MCP: supabase-cr-check
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
| `docs/_scratch/STEP3_BATCH*.sql` | STEP 3 Batch 1~6 | DB 실행 완료 |
| `supabase/migrations/20260505231952_rpc_ethics_context_filter.sql` | STEP 4-C RPC 수정 | DB 실행 완료 |
| `supabase/migrations/20260509232754_pattern_confusion_pairs.sql` | STEP 5-B 테이블 생성 | DB 실행 완료 |
| `supabase/seeds/pattern_confusion_pairs_seed.sql` | STEP 5-B 혼동 쌍 5개 | DB 실행 완료 |
| `backend/core/pattern_matcher.py` | STEP 5-A/B 전체 반영 | 로컬 커밋 대기 |
| `backend/core/pipeline.py` | STEP 4-C + 5-C 반영 | 로컬 커밋 대기 |
| `backend/core/report_generator.py` | STEP 4-A/B/C + 5-C 반영 | 로컬 커밋 대기 |
| `backend/core/storage.py` | STEP 4-B 반영 | 로컬 커밋 대기 |
| `backend/main.py` | STEP 4-B 반영 | 로컬 커밋 대기 |
| `backend/core/meta_pattern_inference.py` | STEP 5-C DEPRECATED 처리 | 로컬 커밋 대기 |
| `docs/_scratch/step1_output_v3.md` | 107개 leaf 코드 체계 기준표 | STEP 6 이후도 참조 |
| `docs/_scratch/STEP5B_FUTURE_CONFUSION_PAIRS.md` | 후속 후보 혼동 쌍 10건 아카이브 | 보존용 |

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v41~v46 | 2026-04-28~05-02 | STEP 0~2 완료 과정 |
| v47 | 2026-05-03 | STEP 3 완전 완료 (Phase 1~4). STEP 4 진입 대기. |
| v48 | 2026-05-06 | STEP 4 완전 완료 (4-A/4-B/4-C). STEP 5 진입 대기. |
| v49 | 2026-05-06 | STEP 5-A CLI 실행 프롬프트 v3 확정 (6인 교차 감리 3라운드 완료). |
| v50 | 2026-05-07 | STEP 5-A 프롬프트 v3 → 3블록 분할 완료. 블록별 감리 의견 반영. |
| v51 | 2026-05-08 | STEP 5-A 블록1·2·3 전체 완료. pattern_matcher.py 전면 재작성. 로컬 커밋 완료. |
| v52 | 2026-05-09 | STEP 5-B 혼동 쌍 5개 확정 완료. distinction_guide v4 확정. 실행 패키지 저장. |
| **v53** | **2026-05-09** | **STEP 5-B CLI 실행 완료 (pattern_confusion_pairs DB화, pattern_matcher.py 수정). STEP 5-C 완료 (메타패턴 3개 파일 DEPRECATED 처리). STEP 5 전체 완료. 로컬 커밋 대기.** |
