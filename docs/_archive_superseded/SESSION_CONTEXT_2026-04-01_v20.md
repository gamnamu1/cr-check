# 세션 컨텍스트 — 2026-04-01 v20

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A+B+C 완료**, 현재 **STEP 86(종합 E2E 품질 체감) 진행 중**이다.

M6 Phase C에서 메타 패턴 추론(1-4-1 외부 압력, 1-4-2 상업적 동기)을 완전 구현했다.
종합 E2E 테스트에서 리포트 품질 개선이 필요한 것으로 확인되어,
STEP 87(프롬프트/리포트 형식 개선 루프)을 다음 세션부터 본격 진행한다.

### v19→v20 변경 사항 (2026-04-01)

**M6 Phase C 완료 (메타 패턴 추론):**

1. STEP 79: Claude.ai 상세 설계 — 5개 판단 포인트 확정
   - 옵션 B: inference_role 컬럼 추가 (구조적 필수/보강 구분)
   - 옵션 Y: 리포트 생성 Sonnet 호출에 통합 (별도 호출 아님)
   - 옵션 ②: 종합 평가 직전 배치 (발동 시에만 섹션 생성)
   - 층위 1만: 프롬프트 가드레일만 (코드 후처리 없음)
   - STEP 81에 사전 확인 단계 포함
   - 설계 문서: `docs/META_PATTERN_DESIGN_v1.md` (393줄)

2. STEP 81: CLI 구현 완료
   - `supabase/migrations/20260401000000_meta_pattern_inference.sql` (81줄)
   - `backend/core/meta_pattern_inference.py` (160줄, 신규)
   - `backend/core/pipeline.py` 수정 (메타 패턴 체크 삽입)
   - `backend/core/report_generator.py` 수정 (조건부 프롬프트 주입)
   - 사전 확인: B-15 → Solo [1-1-1, 1-3-1] 탐지, A2-13 → 필수 미충족

3. STEP 82: Claude.ai 1차 감리 PASS
4. STEP 83: 3건 테스트 — B-15 미발동(Solo 비결정성), A2-13 미발동, C2-07 미발동
5. STEP 84: 테스트 분석 PASS — 보수적 동작이 올바른 방향
6. STEP 85: 독립 감리 PASS
   - Antigravity: PASS + MINOR 2건 (확신도 산식 엣지, 메타 패턴 규범 인용) → M7 검토
   - Manus: 전항목 PASS
   - 감리 리포트: `docs/CR-Check M6 Phase C 독립 감리 리포트 (Antigravity).md`
   - 감리 리포트: `docs/CR-Check M6 Phase C 독립 감리 리포트 (Manus).md`


**STEP 86 종합 E2E 진행 중:**

- 로컬 환경 기동 확인 (supabase + backend + frontend)
- OPENAI_API_KEY 환경변수 누락 → backend/.env에 추가하여 해결
- 모델 버전 오류 발견: report_generator.py의 SONNET_MODEL이 `claude-sonnet-4-20250514`(Sonnet 4)로 설정되어 있었음 → `claude-sonnet-4-6`(Sonnet 4.6)으로 수정
- 기사 2건 테스트 완료. 리포트 표현 방식·톤에서 개선 필요 확인
- Phase D로 바로 넘어가지 않고, STEP 87(개선 루프)에서 리포트 품질을 다듬기로 결정

**Phase C WIP 커밋 완료** (`feature/m6-wip` 브랜치)

---

## 다음 세션 작업: STEP 87 — 리포트 품질 개선 루프

### 작업 방향

여러 유형의 기사를 테스트하면서 평가 품질을 면밀히 확인한다.
주요 개선 대상은 **리포트의 표현 방식, 톤, 서술 구조**이다.
분석 엔진(패턴 식별 로직)이나 파이프라인 구조는 변경하지 않고,
**리포트 생성 프롬프트(`report_generator.py`의 `_SONNET_SYSTEM_PROMPT`)와
프론트엔드 UI**에 한정한 조정을 수행한다.

### 진행 방식

1. Gamnamu가 다양한 기사를 localhost:3000에서 테스트
2. 개선 필요 사항을 구체적으로 기술 (어떤 표현이, 왜 부적절한지)
3. Claude.ai가 프롬프트 수정안 설계
4. CLI가 코드 수정
5. 재테스트 → 반복 (최대 3회, 플레이북 기준)

### 개선 범위 (STEP 87 한정)

- ✅ 3종 리포트(시민/기자/학생) 톤 차이 조정
- ✅ 규범 인용 표현 방식 개선
- ✅ overall_assessment 활용 방식 조정
- ✅ 메타 패턴 "구조적 문제 분석" 섹션 표현 (발동 시)
- ✅ 프론트엔드 레이아웃/가독성 미세 조정
- ❌ 파이프라인 구조 변경 금지 (Sonnet Solo, CitationResolver 등)
- ❌ 벤치마크 지표 변경 금지

### STEP 87 반복 상한

최대 3회. 3회 후에도 불만족 시 STEP 106(감리 협의)으로.


---

## M6 진행 현황 체크리스트

- [x] Phase A: 로컬 E2E 연결 (main.py → pipeline.py 교체, 3종 리포트) ✅
- [x] Phase B: 코드베이스 위생 (벤치마크 Solo 리팩토링, 에러 핸들링) ✅
- [x] Phase C: 메타 패턴 추론 (완전 구현, 독립 감리 PASS) ✅
- [x] Phase C WIP 커밋 ✅
- [ ] **★ STEP 86: 종합 E2E 품질 체감 — 진행 중 (리포트 개선 필요)**
- [ ] STEP 87: 프롬프트/리포트 형식 개선 루프 — 다음 세션
- [ ] WIP→main 분리 커밋 (STEP 86 PASS 후)
- [ ] Phase D: 아카이빙 통합
- [ ] Phase E: 클라우드 배포
- [ ] Phase F: Reserved Test Set 검증
- [ ] Phase G: 마무리

---

## 파이프라인 최종 흐름 (Phase C 완료 후)

```
기사 → 청킹 → 벡터검색(OpenAI 임베딩) → ❶ Sonnet 4.6 Solo(패턴 식별 + Devil's Advocate CoT)
  → check_meta_patterns(탐지된 패턴, DB inferred_by 동적 조회)
  → 규범 조회(get_ethics_for_patterns RPC, DB 기반)
  → ❷ Sonnet 4.6(3종 리포트 + [조건부] 메타 패턴 추론 지시)
  → CitationResolver(cite → 규범 원문 치환, 3종 각각 적용)
  → 최종 리포트
```

---

## 주요 파일 경로 (★ v20 갱신)

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-04-01_v20.md      <- ★ 이 문서 (v20)
├── META_PATTERN_DESIGN_v1.md              <- ★ 메타 패턴 상세 설계 [NEW]
├── CR_CHECK_M6_PLAYBOOK.md                <- M6 플레이북 (STEP 71~104)
├── CR-Check M6 Phase C 독립 감리 리포트 (Antigravity).md  <- [NEW]
├── CR-Check M6 Phase C 독립 감리 리포트 (Manus).md        <- [NEW]
├── M5_BENCHMARK_RESULTS.md                <- M5 Sonnet Solo 26건 벤치마크
├── golden_dataset_final.json              <- Dev Set 26건
├── golden_dataset_labels.json             <- 레이블링 v3
├── ethics_codes_mapping.json              <- 윤리 규범 394개
├── current-criteria_v2_active.md          <- 패턴 119개 (28개 소분류 활성)
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- RAG 마스터 플랜
├── Code of Ethics for the Press.md        <- 규범 원문
└── _archive_superseded/                   <- v14~v19, M3~M5 플레이북 등
```


### 백엔드 (backend/core/) — M6 Phase C 완료
```
/Users/gamnamu/Documents/cr-check/backend/core/
├── db.py                         <- M4: Supabase 연결
├── chunker.py                    <- M4: 기사 청킹
├── pattern_matcher.py            <- M5: Sonnet Solo (claude-sonnet-4-6)
├── meta_pattern_inference.py     <- ★ M6: 메타 패턴 추론 [NEW]
├── report_generator.py           <- M6: 3종 리포트 (claude-sonnet-4-6, 수정 완료)
├── citation_resolver.py          <- M5: 결정론적 인용 후처리
├── pipeline.py                   <- M6: 전체 파이프라인 (메타 패턴 통합)
├── analyzer.py                   <- 기존 MVP (참조용 보존)
├── criteria_manager.py           <- 기존
└── prompt_builder.py             <- 기존
```

### Migration 파일
```
/Users/gamnamu/Documents/cr-check/supabase/migrations/
├── 20260328000000_create_cr_check_schema.sql    <- M1
├── 20260328100000_seed_data.sql                 <- M2
├── 20260329000000_data_implant_pattern_desc.sql <- M3
└── 20260401000000_meta_pattern_inference.sql    <- ★ M6 Phase C [NEW]
```

---

## 오늘 확인된 기술 사항

### 모델 버전

- pattern_matcher.py: `claude-sonnet-4-6` (Sonnet 4.6) ✅
- report_generator.py: `claude-sonnet-4-6` (Sonnet 4.6) ✅ ← 오늘 수정 (기존 claude-sonnet-4-20250514 = Sonnet 4)

### API 키 (backend/.env)

- ANTHROPIC_API_KEY: Sonnet Solo + 리포트 생성 (매 분석마다 2회 호출)
- OPENAI_API_KEY: 기사 청크 임베딩 생성 (매 분석마다 호출, 비용 미미)

### Solo 비결정성

temperature=0이더라도 Sonnet Solo의 패턴 탐지 결과가 실행마다 미세하게 달라질 수 있음.
B-15에서 확인됨: STEP 81 사전 확인 시 [1-1-1, 1-3-1] → STEP 83 본 실행 시 0건.
LLM의 알려진 특성이며, 메타 패턴 모듈의 문제가 아님.


---

## 다음 세션의 Claude에게

### 핵심 지침

1. **M6 Phase A+B+C 완료. 현재 STEP 86(종합 E2E) 진행 중.** 리포트 품질 개선 필요.
2. **다음 작업: STEP 87(리포트 개선 루프).** Gamnamu가 기사별 개선 요청 → 프롬프트 수정 → 재테스트.
3. **개선 범위는 리포트 프롬프트 + 프론트엔드 UI에 한정.** 파이프라인 구조 변경 금지.
4. **모든 모델은 Sonnet 4.6 (`claude-sonnet-4-6`).** 구 모델 사용하지 말 것.
5. **메타 패턴 추론 설계 문서**: `docs/META_PATTERN_DESIGN_v1.md` — 구현 기준선.
6. **메타 패턴은 보수적으로 동작하는 게 정상.** 자주 발동하면 안 됨. 설계 의도.
7. **STEP 86 PASS 후**: WIP→main 분리 커밋 (A→기동확인→B→기동확인→C→기동확인) → Phase D.
8. **v19까지의 모든 지침 유효.** 교훈 1~27 모두 적용.
9. **CLI 자율 진행 제한.** 플레이북 STEP 단위 승인 게이트 엄격 적용.

### M6로 이관된 미해결 과제 (v19에서 계승)

- **양질 오판 TP 4건** (A-01, A-06, B2-10, A-17): 교훈 17에 의해 현 수준 수용 가능
- **TN FP 2건** (C-02, E-17): 인권/AI 윤리 관련 기사에서 오탐 지속
- **벡터 검색 CR 50.8% 천장**: 임베딩 모델 교체 필요 (M7)

### 독립 감리 MINOR 사항 (M7 검토)

- Antigravity MINOR 1: 확신도 산식 (R=2, S=1 → low) — 현재 보수적 동작이 의도된 것
- Antigravity MINOR 2: 메타 패턴 전용 규범 인용 미포함 — 추론적 서술이므로 cite 불필요

### 주의사항 (v19에서 계승)

- **KJA 접두어 절대 금지**
- **Supabase Legacy JWT 키 사용 중**
- **GitHub PAT 만료일: 2026-04-16**
- **Reserved Test Set 73건은 참조 금지** (Phase F 전까지)
- **벤치마크 결과 파일 삭제 금지**
- **deprecated 코드 삭제 금지** (비교 실험용 보존)

---

*이 세션 컨텍스트는 2026-04-01에 v19→v20으로 갱신되었다.*
*M6 Phase C(메타 패턴 추론) 완료. 독립 감리(Antigravity+Manus) PASS.*
*STEP 86 종합 E2E 진행 중. 리포트 품질 개선(STEP 87) 예정.*
*다음 작업: STEP 87 리포트 개선 루프 착수.*

