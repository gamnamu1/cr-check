# 세션 컨텍스트 — 2026-05-03 v47

## 프로젝트 한줄 요약

CR-Check: 한국 뉴스 기사의 언론 윤리 위반 여부를 AI가 진단하는 공익 도구. 프로덕션 가동 중 (Railway + Vercel + Supabase).

---

## 현 위치 한눈에

**MASTER_EXECUTION_PLAN_v1.0.md 기준: STEP 3 완전 완료 (Phase 4 검증 게이트 통과) → STEP 4 진입 대기.**

```
✅ STEP 0-B  윤리규범 DB 정리 (Phase 1~3 전체)
✅ STEP 2    DB 마이그레이션 + 107개 패턴 INSERT + 감리 + 후속 수정
✅ STEP 3    pattern_ethics_relations 재배분 (Phase 1~4 전체)
🔲 STEP 4   코드 품질 개선  ← 다음 작업
🔲 STEP 5   Sonnet 프롬프트 재설계
🔲 STEP 6   임베딩 재생성
🔲 STEP 7   골든셋 재정비 + R8 벤치마크 + threshold 재조정
```

---

## 오늘(2026-05-03) 완료된 전체 작업

### STEP 3 Phase 1 — 현황 파악

- CLI가 `STEP3_DISCOVERY_REPORT.md` 생성
- **핵심 발견**: 계획 기준 63건 → 실제 DB 111건 (+48건)
- DB 전용 소분류 7건 (v3 체계 미정의): `5-4`, `7-3`, `7-4`, `7-5`, `7-6`, `8-1`, `8-2`
- DB·v3 의미 충돌 소분류 9건 확인
- inactive 부모 2건(`4-1`, `4-2`) 매핑 7건 잔존
- `hierarchy_level=2` 비어 있음 → leaf 필터는 정규식 사용 필요

### STEP 3 Phase 2 — 내려보내기

**Batch 1** — 오연결·메타 선언 조항 삭제
- 4-1 ↔ {JEC-5, PCP-3-2, PCP-1-1}, 4-2 ↔ {JEC-5, JEC-8, PCP-1-2}: **6건 DELETE**
- 산출물: `STEP3_BATCH1_DELETE.sql`

**Batch 2** — DB 전용 소분류 7건 → v3 leaf 귀속
- 27건 INSERT (신규 22건, ON CONFLICT skip 5건)
- 5-4→4-4계열 / 7-3→6-3계열 / 7-4→6-4계열 / 7-5→4-3-b / 7-6→6-6계열 / 8-1→7-1-b·c / 8-2→6-4-c·6-2-d·7-1-b
- 산출물: `STEP3_BATCH2_INSERT.sql`, `STEP3_BATCH2_MEMO.md`

**Batch 3** — 의미 충돌 소분류 6건 → v3 leaf 귀속
- 20건 INSERT (신규 14건, ON CONFLICT skip 6건)
- 5-2→4-2계열 / 5-3→4-3-a / 6-1→6-1-b·6-2-d(과거오연결소멸) / 6-2→5-2-a / 7-1→6-1계열 / 7-2→6-2계열
- 산출물: `STEP3_BATCH3_INSERT.sql`, `STEP3_BATCH3_MEMO.md`

### STEP 3 Phase 3 — 빈 leaf 채우기

**사전 조회 3종**
- `STEP3_EMPTY_LEAVES.md`: 활성 leaf 76개 중 58개 매핑 0건 확인
- `STEP3_PREDISCOVERY.md`: EPG 29건·PCP-3 10건·PCP-5 4건·PCP-7 5건·재난 43건·자살 43건 = 134건 특화 조항 원문 조회
- `STEP3_ETHICS_CODES_LOOKUP.md`, `STEP3_PCP3_2_LOOKUP.md`: 개별 조항 원문 확인

**Batch 4** — 1-1·1-4·1-5 계열 21개 leaf
- 49건 INSERT (신규 전부)
- 핵심 특화 조항: PCP-3-3(반론기회)·PCP-5-2(취재원명시)·PCP-5-3(익명보도금지)·PCP-3-4(미확인보도)·EPG-7·EPG-8·EPG-16·EPG-23
- 산출물: `STEP3_BATCH4_INSERT.sql`

**Batch 5** — 2-1·2-2·3-1·3-2·3-3·3-4 계열 16개 leaf
- 34건 INSERT
- 핵심 특화 조항: PCP-5-2·PCP-5-3·JEC-8(품격있는언어)·JEC-6(갈등극대화지양)
- 산출물: `STEP3_BATCH5_INSERT.sql`

**Batch 6** — 4-2·4-4·5-1·6-1·6-2·6-3·6-4·6-6·7-1 계열 21개 leaf
- 43건 INSERT
- 핵심 특화 조항: PCP-7-3(무관가족보호)·PCP-3-9(피의사실)·PCP-7-1(무죄추정)·PCP-7-5(미성년피의자)·DRG-15·DRG-16·JEC-8·EPG-21
- 산출물: `STEP3_BATCH6_INSERT.sql`, `STEP3_PHASE3_MEMO.md`

### STEP 3 Phase 4 — 검증 게이트 통과

| 검증 항목 | 목표 | 결과 |
|---|---|---|
| 활성 leaf 전원 매핑 | cnt ≥ 1 | **76/76 전부 ≥ 1** ✅ |
| PCP 편중 완화 | 60% 이하 | **44.6%** ✅ |

---

## DB 현황 (2026-05-03 기준)

### patterns 테이블

| 구분 | 건수 | 비고 |
|---|---|---|
| 대분류 (hierarchy_level=1) | 8 | 레거시 체계 |
| 소분류·부모 (level=3, 2-segment) | 34 | 기존 30 + 신규 부모 4 (4-3·4-4·6-4·6-6) |
| leaf (level=3, 3-segment) | 107 | STEP 2에서 INSERT |
| **합계** | **149** | |

- `is_active=TRUE, structural`: 17건 (leaf 12 + 부모 5)
- `is_active=TRUE, vector`: 87건
- `is_active=FALSE`: 33건 (I-트랙 31 + 메타패턴 2)

**⚠️ 스키마 주의**: `hierarchy_level=2`가 비어 있음. 부모·leaf 모두 level=3에 저장.
leaf 필터 쿼리는 반드시 정규식 `p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'` 사용.

### ethics_codes 테이블

- 총 394건, applicable_contexts 배정 완료
- is_citable=TRUE: 225건

### pattern_ethics_relations 테이블

- **최종 상태**: 활성 leaf 76개 전원 매핑 완료 (cnt ≥ 1)
- source별 분포: PCP 44.6% / JEC 30.7% / PCE 7.5% / EPG 4.9% / 기타 12.3%
- 주요 사용 특화 조항: PCP-3-3·3-4·3-9, PCP-5-2·5-3, PCP-7-1·7-3·7-5, EPG-7·8·16·21·23, DRG-15·16, JEC-6·8

---

## STEP 4 상세: 코드 품질 개선

> 선행 조건: STEP 3 완료 ✅
> 실행 환경: Claude Code CLI
> 마스터 플랜 §10 참조

### STEP 4-A: _build_ethics_context() 구조화

primary(violates, strong+moderate) / reference(related_to, moderate) 두 그룹 분리.
reference가 비어 있으면 섹션 생략.

### STEP 4-B: analysis_ethics_snapshot 재활성화

리포트 본문 문자열 검색으로 인용 ethics_code 추출 → snapshot 테이블 INSERT.
CitationResolver 없이 구현.

### STEP 4-C: get_ethics_for_patterns RPC 수정

article_context 파라미터 추가 + applicable_contexts 필터 + weak/related_to 제외.
_infer_article_context() 함수: 9개 컨텍스트 (health/disaster/crisis/crime/election/military/unification/general).

---

## STEP 6 이전에 처리할 항목 (대기 중)

아래 3건은 임베딩 재생성(STEP 6) 직전까지만 처리하면 됩니다:

- `4-3-b` 혐오 어휘 현실화 (구식 밈 제거, 최신 표현 추가)
- `3-3-a` description 재작성 (4개 인과 오류 압축 과부하)
- `5-2-a` vs `6-6-b` 전문용어 어휘 중복 해소

---

## 현재 파이프라인 상태 (프로덕션, R5)

```
기사 URL
  → 캐시 조회 (storage.py)
  → 스크래핑 (scraper.py · 59개 전용 파서)
  → 청킹 + 임베딩 + 벡터 검색
       text-embedding-3-small / threshold=0.2, Top-7
  → Sonnet Solo 패턴 감지 (Phase 1)
       claude-sonnet-4-5-20250929, temp=0.0
       패턴 카탈로그 28개 + structural 4개 고정 (← STEP 5에서 107개로 확장 예정)
       미감지 → TN (_TN_MESSAGE)
  → 메타패턴 추론 — 비활성
  → 윤리규범 조회 (fetch_ethics_for_patterns)  ← STEP 4-C에서 개선 예정
  → Sonnet 리포트 생성 (Phase 2) — 3종 JSON
  → DB 저장 + share_id 발급
```

---

## 벤치마크 이력 및 목표

| 버전 | FR | Precision | TN FP |
|---|---|---|---|
| R5 (현 프로덕션) | 36.7% | 44.2% | 6/6 |
| STEP 4 후 목표 | 45% | 55% | 5/6 이하 |
| STEP 5 후 목표 | 60% | 70% | 4/6 이하 |
| **R8 목표 (STEP 7)** | **75%** | **80%** | **3/6 이하** |

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
| `docs/_scratch/STEP3_DISCOVERY_REPORT.md` | Phase 1 현황 파악 | 참조용 |
| `docs/_scratch/STEP3_PREDISCOVERY.md` | 특화 준칙 134건 원문 | 참조용 |
| `docs/_scratch/STEP3_BATCH1_DELETE.sql` | 오연결 6건 삭제 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH2_INSERT.sql` | DB전용소분류 27건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH3_INSERT.sql` | 의미충돌소분류 20건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH4_INSERT.sql` | 빈leaf 1-1·1-4·1-5 49건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH5_INSERT.sql` | 빈leaf 2-1~3-4 34건 | DB 실행 완료 |
| `docs/_scratch/STEP3_BATCH6_INSERT.sql` | 빈leaf 4-2~7-1 43건 | DB 실행 완료 |
| `docs/_scratch/STEP3_PHASE3_MEMO.md` | Phase 3 작업 메모 | 참조용 |
| `docs/_scratch/step1_output_v3.md` | 107개 leaf 코드 체계 기준표 | STEP 4 이후도 참조 |

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v41~v46 | 2026-04-28~05-02 | STEP 0~2 완료 과정 |
| **v47** | **2026-05-03** | **STEP 3 완전 완료 (Phase 1~4). STEP 4 진입 대기.** |
