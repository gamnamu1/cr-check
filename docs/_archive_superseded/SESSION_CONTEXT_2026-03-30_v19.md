# 세션 컨텍스트 — 2026-03-30 v19

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M4가 완료**, **M5 전체 완료**, **M5.5(배포 전 종합 감리) 완료**되었다.
M5에서 3가지 아키텍처를 순차적으로 시도하여, 최종적으로 **Sonnet Solo 1-Call (게이트 없음 + Devil's Advocate CoT)**으로 수렴했다.
결정론적 인용 후처리(CitationResolver)를 구현하여 마스터 플랜 결정 F를 완성했다.

**M6 플레이북 설계 완료 (2026-03-30).** 다음 작업은 M6 Phase A(STEP 71)부터 착수.

### v18→v19 변경 사항 (2026-03-30)

**M6 플레이북 설계 완료:**

- `docs/CR_CHECK_M6_PLAYBOOK.md` 신규 (1,358줄, STEP 71~104)
- Phase 구성: A(로컬 E2E 연결) → B(코드 위생) → C(메타 패턴 추론) → ★종합 E2E 검증 → D(아카이빙) → E(배포) → F(Reserved Test 검증) → G(마무리)
- 핵심 설계 결정:
  1. E2E 검증 타이밍: 품질에 영향을 주는 모든 작업(Phase A + C) 완료 후 한 번에 평가 (STEP 84)
  2. 깃 커밋 시점: 각 Phase 감리 통과 직후 Gamnamu 직접 커밋 (총 7회 명시)
  3. Phase B(코드 위생) → C(메타 패턴) 순서: 벤치마크 인프라 정비 후 새 기능 추가
  4. Reserved Test Set 검증을 M6에 포함 (M7 분리 안 함) — "검증된 도구" 지향
  5. 메타 패턴 추론: 마스터 플랜 섹션 8 완전 구현 (기본 프레임이 아닌 완전 구현)

**코드 변경 없음.** 이번 세션은 플레이북 설계(docs 파일 생성)만 수행.

---

## M5 벤치마크 결과 — M4 대비 (v18에서 계승, 변경 없음)

| 지표 | M4 Sonnet v2 | M5 Sonnet Solo | 변화 | M5 목표 | 달성 |
|------|-------------|---------------|------|---------|------|
| TN FP Rate (1순위) | 67% (4/6) | 33% (2/6) | -34%p | ≤ 33% | ✅ |
| Category Recall (2순위) | 46.7% | 54.2% | +7.5%p | ≥ 60% | ❌ 근접 |
| Final Recall (3순위) | 28.3% | 36.7% | +8.4%p | ≥ 40% | ❌ 근접 |
| Final Precision | 27.5% | 30.4% | +2.9%p | ≥ 30% | ✅ |
| Candidate Recall | 50.8% | 50.8% | 동일 | — | — |

---

## M5 아키텍처 최종 확정 (v18에서 계승, 변경 없음)

최종 아키텍처 — Sonnet Solo:
- 모델: claude-sonnet-4-6 (1회 호출)
- 게이트: 없음. 모든 기사가 패턴 매칭까지 도달
- CoT: Devil's Advocate — overall_assessment에서 (가)양질근거 + (나)문제근거를 모두 기술 후 종합 판단
- Few-shot: 9건 (TP 7 + TN 2), 심의자료+수상작 기반
- 출력: JSON 객체 { overall_assessment, detections }

파이프라인 최종 흐름:
```
기사 → 청킹 → 벡터검색 → Sonnet Solo(패턴 식별)
    → 규범 조회(get_ethics_for_patterns) → Sonnet(리포트, cite 태그)
    → CitationResolver(cite → 원문 치환) → 최종 리포트
```

---

## M1~M4 완료 이력 (v16에서 계승, 변경 없음)

- M1 Migration: `20260328000000_create_cr_check_schema.sql` (407줄)
- M2 Migration: `20260328100000_seed_data.sql` (1,257줄)
- M3 Migration: `20260329000000_data_implant_pattern_desc.sql` (19줄)
- DB 객체: 테이블 9개, 뷰 2개, RPC 함수 5개, 트리거 함수 1개, 트리거 2개
- 시드: ethics_codes 394, patterns 38, hierarchy 42, relations 70+10

---

## 골든 데이터셋 최종 현황 (v18에서 계승, 변경 없음)

### 확정 Dev Set (26건 = TP 20 + TN 6)

| 대분류 | 선별 수 | 대표 ID |
|--------|---------|---------|
| 1-1 진실성 | 3건 | A-01, A-06, B2-10 |
| 1-3 균형성 | 3건 | B-11, B2-14, E-11 |
| 1-4 독립성 | 2건 | A2-13, B-15 |
| 1-5 인권 | 4건 | B-01, A-11, A-17, E-12 |
| 1-6 전문성 | 2건 | A2-03, B2-09 |
| 1-7 언어 | 3건 | A2-05, E-15, B-08 |
| 1-8 디지털 | 3건 | D-01, D-02, D-04 |
| True Negative | 6건 | C-02, C-04, C2-01, C2-07, E-17, E-19 |

### 기사 전문 텍스트
- 경로: /Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts/
- 26건 전부 존재

---

## M5에서 확립된 핵심 교훈 (v18에서 계승, 변경 없음)

17~27번 교훈은 v18 참조. 핵심만 재기술:
- 17: "도구는 촘촘하게, 판단은 사람에게"
- 18: 게이트(이진 판정)의 구조적 한계
- 19: Haiku의 분류 능력 한계
- 20: Devil's Advocate CoT의 유효성
- 21: TN 보호 문구의 역효과 — few-shot 내부에서만 처리
- 22: Data Implant의 한계 — 벡터 검색 CR 개선은 임베딩 모델 교체 필요
- 23: 결정론적 인용의 in-memory 원칙
- 24: 방어적 조건문의 중요성
- 25: 독립 감리의 가치
- 26: 크로스체크의 위력
- 27: JEC ≠ JCE — DB의 다양한 접두어 체계

---

## 주요 파일 경로 (★ v19 갱신)

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-30_v19.md      <- ★ 이 문서 (v19)
├── CR_CHECK_M6_PLAYBOOK.md                <- ★ M6 플레이북 (STEP 71~104) [NEW]
├── M5_BENCHMARK_RESULTS.md                <- M5 Sonnet Solo 26건 벤치마크
├── golden_dataset_final.json              <- Dev Set 26건
├── golden_dataset_labels.json             <- 레이블링 v3
├── ethics_codes_mapping.json              <- 윤리 규범 394개
├── current-criteria_v2_active.md          <- 패턴 119개 (28개 소분류 활성)
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- RAG 마스터 플랜
├── Code of Ethics for the Press.md        <- 규범 원문
└── _archive_superseded/                   <- v14~v18, M3~M5 플레이북 등
```

### 백엔드 (backend/core/) — M5 최종 (변경 없음)
```
/Users/gamnamu/Documents/cr-check/backend/core/
├── db.py                  <- M4: Supabase 연결
├── chunker.py             <- M4: 기사 청킹
├── pattern_matcher.py     <- M5: Sonnet Solo 활성
├── report_generator.py    <- M4: Sonnet 리포트
├── citation_resolver.py   <- M5: 결정론적 인용 후처리
├── pipeline.py            <- M5: 전체 파이프라인 오케스트레이션
├── analyzer.py            <- 기존 MVP (M6에서 교체 대상)
├── criteria_manager.py    <- 기존
└── prompt_builder.py      <- 기존
```

### 벤치마크 스크립트
```
/Users/gamnamu/Documents/cr-check/scripts/
├── benchmark_pipeline_v3.py   <- M5: Solo 경로
├── test_citation_resolver.py  <- M5: CitationResolver 테스트
└── generate_embeddings.py     <- 임베딩 생성
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **M5 전체 완료. M6 플레이북 설계 완료.** 다음 작업은 **M6 Phase A, STEP 71**부터 착수.
2. **M6 플레이북**: `docs/CR_CHECK_M6_PLAYBOOK.md` — STEP 71~104 (34개). 반드시 숙지 후 착수.
3. **M6 Phase 순서**: A(로컬 E2E 연결) → B(코드 위생) → C(메타 패턴 추론) → ★종합 E2E 검증 → D(아카이빙) → E(배포) → F(Reserved Test 검증) → G(마무리)
4. **E2E 검증 원칙**: 품질에 영향을 주는 모든 작업(Phase A + C)을 완료한 후 **STEP 84에서 한 번에** 종합 평가. 중간 평가 없음.
5. **깃 커밋 시점**: 각 Phase 감리 통과 직후 Gamnamu 직접 커밋 (총 7회, 플레이북에 명시).
6. **모델은 Sonnet 4.6 단독.** Haiku 호출 없음. pattern_matcher.py의 match_patterns_solo() 활성.
7. **프롬프트는 Devil's Advocate CoT 구조.** 게이트 없음. 이전으로 되돌리지 말 것.
8. **출력 형식은 JSON 객체** {overall_assessment, detections}. 배열이 아님.
9. **파이프라인 최종 흐름**: 청킹 → 벡터검색 → Sonnet Solo(패턴 식별) → 규범 조회 → Sonnet(리포트) → CitationResolver → 최종 리포트
10. **v7~v18의 모든 지침 유효.** 교훈 1~27 모두 적용.
11. **CLI 자율 진행 제한.** 플레이북 STEP 단위 승인 게이트 엄격 적용.
12. **역할 체계 유지.** Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Manus(2차) → Gamnamu(승인).

### M6 Phase A — STEP 71에서 시작

STEP 71은 Claude.ai가 main.py 교체 설계를 수행하는 단계.
현재 main.py는 `core.analyzer`(구 MVP)를 사용하며, `core.pipeline`(Sonnet Solo + CitationResolver)으로 교체해야 한다.
핵심 설계 판단: 응답 스키마 재설계(3종 리포트 → 단일 리포트), overall_assessment 노출 여부.
Gamnamu의 STEP 72 승인 후 CLI가 STEP 73에서 코드 작업 착수.

### M6로 이관된 미해결 과제 (v18에서 계승)

- **양질 오판 TP 4건** (A-01, A-06, B2-10, A-17): 교훈 17에 의해 현 수준 수용 가능
- **TN FP 2건** (C-02, E-17): 인권/AI 윤리 관련 기사에서 오탐 지속
- **벡터 검색 CR 50.8% 천장**: 임베딩 모델 교체 필요
- **메타 패턴 추론**: M6 Phase C에서 완전 구현 예정

### M5.5에서 M6로 이관된 사항

- 벤치마크 스크립트 Solo 전용 리팩토링 → M6 Phase B
- pipeline.py 전역 에러 핸들링 강화 → M6 Phase B
- main.py → pipeline.py 기반 교체 → M6 Phase A
- analysis_results 스키마 갱신 → M6 Phase D
- 벡터 검색 async 병렬화 → M6 Phase B (선택)
- JEC/JCE 접두어 불일치 점검 → M6 Phase A

### 주의사항

- **KJA 접두어 절대 금지**. DB 접두어 체계: JEC, JCE, JCP, PCE, PCP, DRG, EPG, HSD, IRG, MRG, PRG, SPG, SRE
- **Supabase Legacy JWT 키 사용 중.**
- **GitHub PAT 만료일: 2026-04-16.**
- **supabase start → Docker 필요.** 로컬 DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Reserved Test Set 73건은 참조 금지** (Phase F 벤치마크 전까지).
- **벤치마크 결과 파일 삭제 금지.**
- **deprecated 코드(1-Call, 2-Call) 삭제 금지.** 비교 실험용 보존.

---

*이 세션 컨텍스트는 2026-03-30에 v18→v19로 갱신되었다.*
*M6 플레이북 설계 완료 (CR_CHECK_M6_PLAYBOOK.md, STEP 71~104).*
*코드 변경 없음. 다음 작업: M6 Phase A (STEP 71) 착수.*
