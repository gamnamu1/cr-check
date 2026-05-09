# 세션 컨텍스트 — 2026-05-09 v52

## 프로젝트 한줄 요약

CR-Check: 한국 뉴스 기사의 언론 윤리 위반 여부를 AI가 진단하는 공익 도구. 프로덕션 가동 중 (Railway + Vercel + Supabase).

---

## 현 위치 한눈에

**MASTER_EXECUTION_PLAN_v1.0.md 기준: STEP 5-B 혼동 쌍 선택 완료 → CLI 실행 대기.**

```
✅ STEP 0-B  윤리규범 DB 정리 (Phase 1~3 전체)
✅ STEP 2    DB 마이그레이션 + 107개 패턴 INSERT + 감리 + 후속 수정
✅ STEP 3    pattern_ethics_relations 재배분 (Phase 1~4 전체)
✅ STEP 4    코드 품질 개선 (4-A/4-B/4-C 전체)
🔄 STEP 5   Sonnet 프롬프트 재설계
            ↳ v3 프롬프트 확정 (v49, 2026-05-06)
            ↳ 3블록 분할 완료 (v50, 2026-05-07)
            ↳ 5-A: 블록1·2·3 CLI 실행 완료 (v51, 2026-05-08) ✅
            ↳ 5-B: 혼동 쌍 5개 선택 확정 (v52, 2026-05-09) ✅
                   → CLI 실행 대기 (실행 패키지: docs/_scratch/STEP 5-B_EXECUTION_PACKAGE.md)
            ↳ 5-C: 메타패턴 코드 DEPRECATED 처리 (5-B 완료 직후)
            ↳ 로컬 커밋 완료(5-A분). 푸시는 STEP 7 완료 후 예정.
🔲 STEP 6   임베딩 재생성
🔲 STEP 7   골든셋 재정비 + R8 벤치마크 + threshold 재조정
```

---

## 2026-05-09 완료된 전체 작업 (STEP 5-B 혼동 쌍 선택)

### 혼동 쌍 5개 확정 결과

구버전 DEPRECATED 주석(line 364-372, `pattern_matcher.py`)의 5개 혼동 쌍을
active v3 leaf 코드로 번역하는 감리를 완료했다.
감리자 7인(Claude·GPT·Manus·Gemini·Perplexity·NotebookLM·Antigravity) 참여.

| 쌍 | 구버전 | 확정 v3 leaf 코드 |
|----|--------|-------------------|
| 쌍 1 | 1-1 vs 1-4 | `1-1-e` vs `1-4-d` |
| 쌍 2 | 3-1 vs 3-2 | `3-1-b` vs `3-2-b` |
| 쌍 3 | 3-1 vs 3-4 | `3-1-a` vs `3-4-a` |
| 쌍 4 | 7-2 vs 7-5 | `3-2-a` vs `6-4-a` |
| 쌍 5 | 7-3 vs 7-4 | `6-3-a` vs `6-2-c` |

**주요 확인 사항:**
- 구버전 7-2 그룹 leaf 전부 is_active=FALSE → 3-2-a로 재배치
- 구버전 7-5 → 6-4-a 직접 대응 (search_text에 '충격·경악·발칵' 포함)
- 구버전 3-4는 v3에서 "갈등 조장 프레이밍" 계승 (3-4-a/b/c)
  구버전 혼동 주석 "배경·맥락 생략"은 3-4의 부정확한 부수 설명이었음

### distinction_guide v4 확정

감리자 3인(Claude·GPT·Perplexity) 양식 비교 후 최적 조합(Claude v3 기반):
- **쌍 1**: 혼재 처리 추가 ("양쪽 요소가 혼재할 때는 더 구체적 근거가 있는 쪽")
- **쌍 2**: 1-1-j 구분 제거 (Sonnet attention 분산 리스크)
- **쌍 3**: 변경 없음
- **쌍 4**: "둘 다 명확히 해당하면 각각 별도로 선택" 추가 / '종북'·'대반전' 예시 추가
- **쌍 5**: 시작 지점 "제목만 보지 말고 본문을 먼저 읽어라" / 6-2-c 구체 예시 추가

전문: `docs/_scratch/STEP 5-B_EXECUTION_PACKAGE.md` §1 참조

### 후속 후보 혼동 쌍 아카이빙

감리 과정에서 제안된 후속 후보 10건을 별도 문서로 보존.
저장 위치: `docs/_scratch/STEP5B_FUTURE_CONFUSION_PAIRS.md`
(추후 STEP 7 R8 벤치마크 결과에 따라 추가 채택 검토)

---

## STEP 5-B 다음 작업 — CLI 실행 지시 상세

> 실행 패키지 전문: `docs/_scratch/STEP 5-B_EXECUTION_PACKAGE.md` §2
> 절대 원칙: CLI 파일 작성만, DB INSERT는 기획자 SQL Editor 직접 실행

### CLI가 수행할 4단계 작업

1. `supabase/migrations/{timestamp}_pattern_confusion_pairs.sql` 작성
   (CREATE TABLE 구문)

2. `supabase/seeds/pattern_confusion_pairs_seed.sql` 작성
   (5개 쌍 INSERT, ON CONFLICT DO NOTHING)
   ⚠️ v3 leaf 코드만 사용. 구버전 코드(1-1, 3-1 등) 절대 금지.

3. `pattern_matcher.py`에 `_load_confusion_pairs()` 함수 추가
   (Supabase에서 is_active=TRUE 행 조회, 실패 시 빈 리스트 + logger.warning)

4. `_SONNET_SOLO_PROMPT`의 DEPRECATED 주석 블록(line 364~372)을
   `_load_confusion_pairs()` 동적 로드로 교체
   (섹션 형식: "## 자주 혼동되는 패턴 쌍" / 빈 쌍이면 섹션 전체 생략)

### STEP 5-C (5-B 완료 직후 연속 실행)

메타패턴 관련 3개 파일 DEPRECATED 처리:
- `pipeline.py`: `check_meta_patterns()` 호출 블록
- `report_generator.py`: `_build_meta_pattern_block()` 함수
- `meta_pattern_inference.py`: 파일 상단 전체

### STEP 6 전 처리 권고 항목

- `scripts/benchmark_pipeline_v3.py`에 `unmatched_vector_candidates` 출력 추가
  (STEP 7 벤치마크에서 구버전 코드 추적 가능하게)

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

⚠️ **스키마 주의**: `hierarchy_level=2` 비어 있음. leaf 필터는 정규식 `^[0-9]+-[0-9]+-[a-z]+$` 사용.

### pattern_confusion_pairs 테이블

- 아직 미생성. STEP 5-B CLI 실행 후 생성 예정.

### ethics_codes 테이블

- 총 394건, applicable_contexts 배정 완료
- is_citable=TRUE: 225건

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

## 현재 파이프라인 상태 (STEP 5-A 반영 완료)

```
기사 URL
  → 캐시 조회 (storage.py)
  → 스크래핑 (scraper.py · 59개 전용 파서)
  → 청킹 + 임베딩 + 벡터 검색
       text-embedding-3-small / threshold=0.2, Top-7
       ※ 임베딩 소스: 구버전 기준 (STEP 6에서 search_text 기준으로 전환 예정)
       ※ unmatched_vector_candidates 로깅 활성 (구버전 코드 추적 중)
  → Sonnet Solo 패턴 감지 (Phase 1)
       claude-sonnet-4-5-20250929, temp=0.0
       패턴 카탈로그: v3 leaf 76건 (vector 64 + structural 12) — 3섹션 동적 구성
       few-shot 예시: v3 leaf 기준 7건 (TP 5 + TN 2) + structural 예시 1건
       혼동 쌍: DEPRECATED 주석 상태 (STEP 5-B CLI 실행 후 동적 로드로 전환)
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

## 핵심 설계 결정 (변경 불가)

- Sonnet Solo 1-Call 구조 유지
- TN 케이스: `pipeline.py`의 `_TN_MESSAGE` 정적 메시지
- 인용 방식: 〔규범 원문〕 마커 직접 출력
- 이진 게이트: 제거 확정 (R5)
- 임베딩 소스: STEP 6에서 `search_text` 기준으로 전환 예정
- 메타패턴 추론: 완전 비활성화 확정
- GitHub 커밋: 사람이 직접 수행. 푸시는 STEP 7 완료 후.
- applicable_contexts: `text[]` 타입, `ARRAY['context']` 형태로 저장
- 교차 감리 원칙: 모든 감리자 동일 프롬프트·역할 분리 금지
- 혼동 쌍 distinction_guide: v4 확정 (2026-05-09)
  판별 기준을 bullet과 독립된 마지막 줄로 배치
  마크다운 서식 없는 순수 텍스트

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
| `docs/_scratch/STEP3_BATCH*.sql` | STEP 3 Batch 1~6 | DB 실행 완료 |
| `supabase/migrations/20260505231952_rpc_ethics_context_filter.sql` | STEP 4-C RPC 수정 | DB 실행 완료 |
| `backend/core/report_generator.py` | STEP 4-A/4-C 반영 | 로컬 커밋 예정 |
| `backend/core/pipeline.py` | STEP 4-C 반영 | 로컬 커밋 예정 |
| `backend/core/storage.py` | STEP 4-B 반영 | 로컬 커밋 예정 |
| `backend/main.py` | STEP 4-B 반영 | 로컬 커밋 예정 |
| `backend/core/pattern_matcher.py` | STEP 5-A 전체 반영 | 로컬 커밋 완료 |
| `docs/_scratch/step1_output_v3.md` | 107개 leaf 코드 체계 기준표 | STEP 6 이후도 참조 |
| `docs/_scratch/STEP 5-B_EXECUTION_PACKAGE.md` | STEP 5-B CLI 실행 패키지 (distinction_guide v4 + CLI 지시) | CLI 전달 대기 |
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
| v51 | 2026-05-08 | STEP 5-A 블록1·2·3 전체 완료. pattern_matcher.py 전면 재작성. 로컬 커밋 완료. STEP 5-B 진입 대기. |
| **v52** | **2026-05-09** | **STEP 5-B 혼동 쌍 5개 확정 완료. distinction_guide v4 확정. 실행 패키지 저장. STEP 5-B CLI 실행 대기.** |
