# 세션 컨텍스트 — 2026-03-29 v17

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M4가 완료**, **M5 Phase A~C가 완료**되었다.
M5에서 3가지 아키텍처를 순차적으로 시도하여, 최종적으로 **Sonnet Solo 1-Call (게이트 없음 + Devil's Advocate CoT)**으로 수렴했다.

**M5 핵심 결론:**
1. "게이트" 개념 자체의 구조적 한계 — 이진 판정(양질→즉시[], 문제→패턴검색)은 TP/TN 트레이드오프를 해결 불가
2. Devil's Advocate CoT가 TN 보호에 유효 — TN FP Rate 67% → 33% (1순위 목표 달성)
3. FR/Precision도 M4 대비 유의미 개선 — FR +8.4%p, FP +2.9%p
4. Haiku는 대분류 수준 판단조차 불가 — 2-Call 파이프라인 실패로 실증
5. **포지셔닝 재확인**: "도구는 촘촘하게, 판단은 사람에게" — 오탐(FP)은 사용자의 선의에 의한 판단에 맡김

다음 작업은 **M5 Phase D (결정론적 인용 후처리)** + **Phase E (마무리)**.

### v16→v17 변경 사항 (2026-03-29)

**M5 Phase A~C 완료 (프롬프트 고도화 + 성능 벤치마크):**

아키텍처 시도 이력 (3회):
1. M4 기존 1-Call + 1단계 이진 게이트 + few-shot 9건 → FAIL (TP 양질 오판 + TN 보호 실패)
2. 2-Call (Haiku 대분류 의심 → Sonnet 소분류 검증) → FAIL (Haiku가 대분류조차 정반대로 판단)
3. **Sonnet Solo 1-Call (게이트 없음 + Devil's Advocate CoT)** → 부분 성공 (1순위 달성)

최종 아키텍처 — Sonnet Solo:
- 모델: claude-sonnet-4-6 (1회 호출)
- 게이트: 없음. 모든 기사가 패턴 매칭까지 도달
- CoT: Devil's Advocate — overall_assessment에서 (가)양질근거 + (나)문제근거를 모두 기술 후 종합 판단
- Few-shot: 9건 (TP 7 + TN 2), 심의자료+수상작 기반
- TN 보호: few-shot TN 예시의 overall_assessment 내부에서만 처리 (일반 문구 제거)
- 출력: JSON 객체 { overall_assessment, detections }
- 프롬프트: _SONNET_SOLO_PROMPT (6,926자, ~3,463 토큰)

**M5 벤치마크 결과 — M4 대비:**

| 지표 | M4 Sonnet v2 | M5 Sonnet Solo | 변화 | M5 목표 | 달성 |
|------|-------------|---------------|------|---------|------|
| TN FP Rate (1순위) | 67% (4/6) | 33% (2/6) | -34%p | ≤ 33% | ✅ |
| Category Recall (2순위) | 46.7% | 54.2% | +7.5%p | ≥ 60% | ❌ 근접 |
| Final Recall (3순위) | 28.3% | 36.7% | +8.4%p | ≥ 40% | ❌ 근접 |
| Final Precision | 27.5% | 30.4% | +2.9%p | ≥ 30% | ✅ |
| Candidate Recall | 50.8% | 50.8% | 동일 | — | — |

TN 상세:
- M4 FP → M5 TN 성공: C-04 (성 착취 보도), E-19 (국가 비상금 탐사)
- M4 TN → M5 TN 유지: C2-01, C2-07
- M5 여전히 FP: C-02 (트랜스젠더 보고서, 1-1-5+1-7-2), E-17 (AI 이루다, 1-7-3+1-1-4)

TP 주요 개선:
- FR 1.00 달성 4건: B2-14, B-01, A-11, D-01 (M4에서 모두 FR 0.00~0.50)
- 양질 오판 지속 4건: A-01, A-06, B2-10, A-17 (형식적 근거가 탄탄한 기사 유형)

**M5 감리 이력:**

| # | 감리자 | STEP | 결과 | 내용 |
|---|--------|------|------|------|
| 1 | Claude.ai | STEP 58 | PASS | 2-Call 파이프라인 코드/프롬프트 감리 |
| 2 | Claude.ai | STEP 58-b | PASS | Data Implant + 벤치마크 스크립트 감리 |
| 3 | Claude.ai | STEP 61 | 0건 개선 | 2-Call 3건 테스트 → STEP 68 진입 |
| 4 | Antigravity | 독립 감리 | C안 강력 찬성 | 1단계 제거 + 강제 CoT 제안 |
| 5 | Manus | 독립 감리 | 2-Call 제안 | 의심-검증 파이프라인 (채택→실패) |
| 6 | Claude.ai | STEP 61 (2차) | 0건 개선 | 2-Call 재테스트 → 전면 실패 |
| 7 | Manus | 실패 분석 | 게이트 한계 인정 | Sonnet Solo 동의 + 멀티페르소나 제안 |
| 8 | Claude.ai | STEP 58-S | PASS | Sonnet Solo 코드/프롬프트 감리 |
| 9 | Claude.ai | STEP 63 | 부분 성공 | 26건 벤치마크 → 1순위 달성, 2·3순위 근접 |

**M5에서 확립된 핵심 교훈:**

17. **"도구는 촘촘하게, 판단은 사람에게"**: CR-Check는 촘촘한 그물. 오탐(FP)은 사용자의 선의에 의한 판단에 맡김. 양질의 기사를 문제삼는 것보다, 문제 기사를 놓치는 것이 더 위험. 도구 바깥에서 저널리즘과 비평에 대한 논의가 시작되어야 할 지점.
18. **게이트(이진 판정)의 구조적 한계**: "양질이면 즉시 []"는 TP/TN 트레이드오프를 해결 불가. 1-Call 게이트도, 2-Call Haiku 게이트도 동일 실패.
19. **Haiku의 분류 능력 한계**: 대분류 수준의 의심 식별조차 정반대로 판단. 비용 절약을 위한 Haiku 활용은 패턴 식별 작업에 부적합.
20. **Devil's Advocate CoT의 유효성**: 찬반 양론을 강제로 기술하게 하면, Sonnet 수준에서 CoT가 결론을 실제로 구속. TN 보호에 가장 효과적.
21. **TN 보호 문구의 역효과**: 일반 문구("탐사보도는 양질")가 TP에도 적용되어 과잉 보호. few-shot 예시 내부에서만 TN 보호를 기술하는 것이 정밀.
22. **Data Implant의 한계**: 패턴 description에 키워드를 추가해도 임베딩 벡터 방향이 유의미하게 바뀌지 않음. 벡터 검색 CR 개선은 임베딩 모델 교체가 필요.

---

## M1~M4 완료 이력 (v16에서 계승)

- M1 Migration: `20260328000000_create_cr_check_schema.sql` (407줄)
- M2 Migration: `20260328100000_seed_data.sql` (1,257줄)
- M3 Migration: `20260329000000_data_implant_pattern_desc.sql` (19줄) — 1-7-5, 1-7-2 description 보강
- DB 객체: 테이블 9개, 뷰 2개, RPC 함수 5개, 트리거 함수 1개, 트리거 2개
- 시드: ethics_codes 394, patterns 38, hierarchy 42, relations 70+10

---

## 골든 데이터셋 최종 현황

### 확정 Dev Set (26건 = TP 20 + TN 6) — 변경 없음

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

## M5 Phase D 방향 — 다음 세션에서 실행

### Phase D: 결정론적 인용 후처리 구현

마스터 플랜 결정 F의 완성. Sonnet 리포트의 `<cite ref="JCE-03"/>` 태그를 DB 원문으로 치환.

플레이북 STEP 65~66을 실행:
- STEP 65: CLI — CitationResolver 모듈 구현 (citation_resolver.py)
- STEP 66: Claude.ai — CitationResolver 1차 감리

### Phase E: 마무리

- STEP 67: Antigravity/Manus — M5 종합 2차 독립 감리
- STEP 69: CLI — SESSION_CONTEXT v18 갱신
- STEP 70: Gamnamu — M5 최종 승인

---

## 주요 파일 경로

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-29_v17.md      <- ★ 이 문서
├── CR_CHECK_M5_PLAYBOOK.md                <- M5 플레이북 (STEP 65~70 참조)
├── M5_BENCHMARK_RESULTS.md                <- ★ M5 Sonnet Solo 26건 벤치마크
├── M5_STEP57_SONNET_SOLO_CLI_PROMPT.md    <- Sonnet Solo CLI 프롬프트 (참조용)
├── M4_BENCHMARK_RESULTS_sonnet46.md       <- M4 Sonnet v2 벤치마크 (비교 기준선)
├── M4_BENCHMARK_RESULTS.md                <- M4 Haiku 벤치마크
├── M4_BENCHMARK_RESULTS_opus46.md         <- M4 Opus 오라클 테스트
├── M3_BENCHMARK_RESULTS.md                <- M3 벤치마크
├── golden_dataset_final.json              <- ★ Dev Set 26건
├── golden_dataset_labels.json             <- ★ 레이블링 v3
├── ethics_codes_mapping.json              <- 윤리 규범 394개
├── current-criteria_v2_active.md          <- 패턴 119개 (28개 소분류 활성)
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- ★ RAG 마스터 플랜 (섹션 7.3: 결정론적 인용)
├── M5_FEWSHOT_RAW_MATERIALS.md            <- Few-shot 소재 원본
├── M5_ETHICS_REVIEW_ANALYSIS.md           <- 윤리 심의 분석
├── [감리 리포트] *.md                      <- 외부 감리 리포트 3건
└── _archive_superseded/                   <- v14, v15, v16 포함
```

### 백엔드 (backend/core/) — M5에서 변경
```
/Users/gamnamu/Documents/cr-check/backend/core/
├── db.py                  <- M4: Supabase 연결
├── chunker.py             <- M4: 기사 청킹
├── pattern_matcher.py     <- ★ M5 변경: Sonnet Solo 활성, 2-Call/1-Call deprecated
│   ├── match_patterns_solo()     ← 활성 (게이트 없음 + Devil's Advocate)
│   ├── _SONNET_SOLO_PROMPT       ← 활성 프롬프트 (6,926자)
│   ├── _parse_solo_response()    ← 객체 파싱 ({overall_assessment, detections})
│   ├── match_patterns_2call()    ← [DEPRECATED] 2-Call
│   ├── match_patterns()          ← [DEPRECATED] 1-Call
│   └── _HAIKU_SYSTEM_PROMPT      ← [DEPRECATED]
├── report_generator.py    <- M4: Sonnet 리포트 (결정론적 인용 태그 출력)
├── pipeline.py            <- ★ M5 변경: match_patterns_solo() 사용
├── analyzer.py            <- 기존 MVP
├── criteria_manager.py    <- 기존
└── prompt_builder.py      <- 기존
```

### 벤치마크 스크립트
```
/Users/gamnamu/Documents/cr-check/scripts/
├── benchmark_pipeline_v3.py   <- ★ M5 변경: Solo 경로 + overall_assessment 기록
└── generate_embeddings.py     <- 임베딩 생성
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **M5 Phase A~C 완료.** Sonnet Solo 1-Call 아키텍처 확정. 벤치마크 1순위(TN FP ≤ 33%) 달성.
2. **Phase D(결정론적 인용 후처리)가 다음 작업.** 플레이북 STEP 65~66 참조.
3. **모델은 Sonnet 4.6 단독.** Haiku 호출 없음. pattern_matcher.py의 match_patterns_solo() 활성.
4. **프롬프트는 Devil's Advocate CoT 구조.** 게이트 없음. 1단계/2단계 구분 없음. 이전으로 되돌리지 말 것.
5. **출력 형식은 JSON 객체** {overall_assessment, detections}. 배열이 아님.
6. **v7~v16의 모든 지침 유효.** 교훈 1~16(v16) + 17~22(v17) 모두 적용.
7. **CLI 자율 진행 제한.** 플레이북 단계별 승인 게이트 엄격 적용.
8. **클라우드 배포는 M5 완료 후.**
9. **역할 체계 유지.** Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Manus(2차) → Gamnamu(승인).

### M5 미해결 과제 (Phase D 이후 또는 M6에서)

- **양질 오판 TP 4건** (A-01, A-06, B2-10, A-17): "형식적 근거가 탄탄한" 기사에서 LLM이 내용 결함을 감지하지 못함. few-shot 보강 또는 레이블 재검토 가능. 단, 교훈 17("도구는 촘촘하게, 판단은 사람에게")에 의해 현 수준 수용 가능.
- **TN FP 2건** (C-02, E-17): 인권/AI 윤리 관련 기사에서 오탐 지속. TN few-shot 추가(현재 2건→3~4건)로 개선 가능성.
- **벡터 검색 CR 50.8% 천장**: 임베딩 모델 교체 또는 패턴 description 전면 재작성이 필요. M6 범위.

### 주의사항

- **KJA 접두어 절대 금지.** JCE가 올바른 접두어.
- **Supabase Legacy JWT 키 사용 중.**
- **GitHub PAT 만료일: 2026-04-16.**
- **supabase start → Docker 필요.** 로컬 DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Reserved Test Set 73건은 참조 금지.**
- **벤치마크 결과 파일 삭제 금지.**
- **deprecated 코드(1-Call, 2-Call) 삭제 금지.** 비교 실험용 보존.
- **v16을 _archive_superseded/로 이동할 것.**

---

*이 세션 컨텍스트는 2026-03-29에 v16→v17로 갱신되었다.*
*M5 Phase A~C 완료 (3회 아키텍처 시도 → Sonnet Solo 확정).*
*Phase D (결정론적 인용 후처리)를 다음 세션에서 진행.*
