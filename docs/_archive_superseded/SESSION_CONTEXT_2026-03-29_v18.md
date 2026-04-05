# 세션 컨텍스트 — 2026-03-29 v18

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M4가 완료**, **M5 Phase A~E 완료 (M5 전체 완료)**되었다.
M5에서 3가지 아키텍처를 순차적으로 시도하여, 최종적으로 **Sonnet Solo 1-Call (게이트 없음 + Devil's Advocate CoT)**으로 수렴했다.
결정론적 인용 후처리(CitationResolver)를 구현하여 마스터 플랜 결정 F를 완성했다.

**M5 최종 결론:**
1. "게이트" 개념 자체의 구조적 한계 — 이진 판정(양질→즉시[], 문제→패턴검색)은 TP/TN 트레이드오프를 해결 불가
2. Devil's Advocate CoT가 TN 보호에 유효 — TN FP Rate 67% → 33% (1순위 목표 달성)
3. FR/Precision도 M4 대비 유의미 개선 — FR +8.4%p, FP +2.9%p
4. Haiku는 대분류 수준 판단조차 불가 — 2-Call 파이프라인 실패로 실증
5. **포지셔닝 재확인**: "도구는 촘촘하게, 판단은 사람에게" — 오탐(FP)은 사용자의 선의에 의한 판단에 맡김
6. **결정론적 인용 완성**: cite 태그 → in-memory 매칭 → 규범 원문 치환. 환각 원천 차단.

**M5.5 (배포 전 종합 감리)** 완료. 4자 크로스체크(Claude.ai + Antigravity + Manus + Manus-Max)에서 CRITICAL 1건(few-shot 메타 패턴 모순) + MAJOR 6건 + MINOR 8건 발견. 즉시 수정 7건 반영 완료.

다음 작업은 **M6 (메타 패턴 추론 + Phase 1 아카이빙 통합 + 클라우드 배포)**.

### v17→v18 변경 사항 (2026-03-29)

**M5 Phase D 완료 — 결정론적 인용 후처리:**

- `citation_resolver.py` 신규 모듈 (132줄)
- 설계 결정: **옵션 B** (in-memory 매칭 전용, DB fallback 없음)
  - 근거: Sonnet에게 제공되지 않은 규범을 DB에서 찾아 치환하면 검증되지 않은 관계가 포함됨
  - in-memory에 없는 ref는 환각으로 간주하여 제거
- 치환 형식: `「{ethics_title}: {full_text 발췌}」` (200자 초과 시 어절 경계 절단 + "...")
- 중복 인용: 첫 출현=정상 치환, 이후 출현=`「{title} 참조」`
- 가드레일: 환각 ref 제거 + WARNING 로그, 이중 공백 정리, 길이 3배 초과 경고
- pipeline.py 통합: `generate_report()` → `resolve_citations()` → 최종 리포트
- try/except로 감싸서 CitationResolver 실패 시 원본 리포트 보존

**M5 Phase E 완료 — 감리 + 마무리:**

- STEP 66 Claude.ai 1차 감리: PASS
- STEP 67 독립 감리:
  - Antigravity: CRITICAL 1건 + MINOR 2건
  - Manus: MAJOR 1건 + MINOR 2건
- STEP 67-R 수정 3건 반영:
  1. pipeline.py 조건문 버그: `if rr.report_text and rr.ethics_refs:` → `if rr.report_text:` (빈 ethics_refs 시 CitationResolver 스킵 방지)
  2. citation_resolver.py 이중 공백 후처리: 환각 태그 제거 후 `re.sub(r' {2,}', ' ', resolved)` 추가
  3. citation_resolver.py 절단 경계 문자 확장: `(' ', '.', '。')` → `(' ', '.', '。', ',', '\n')`

**M5.5 완료 — 배포 전 종합 감리 (4자 크로스체크):**

감리자: Claude.ai + Antigravity + Manus + Manus-Max
방식: 동일 전체 범위를 4자가 독립 크로스체크 (축 1 수직 정합성 + 축 2 수평 정합성 + 축 3 코드베이스 위생)

주요 발견 및 수정 반영:
1. [CRITICAL→수정 완료] few-shot 예시 3의 1-4-2(메타 패턴)가 카탈로그에서 제외된 코드 → 1-3-1(균형성)로 교체 (Antigravity 발견)
2. [MAJOR→수정 완료] HAIKU_MODEL 변수명 → SONNET_MODEL로 통일 (4자 공통)
3. [MINOR→수정 완료] pattern_matcher.py 상단 주석 "Haiku" → "Sonnet Solo" (4자 공통)
4. [MAJOR→수정 완료] CitationResolver 실패 시 cite 태그 제거 fallback 추가 (Manus 발견)
5. [MINOR→수정 완료] report_generator.py에 빈 ethics_refs 경고 로그 추가 (Manus 제안)
6. [MAJOR→수정 완료] CLAUDE.md를 M5 완료 상태로 전면 갱신 (4자 공통)
7. [MINOR→수정 완료] JEC/JCE 접두어 문서 명확화 — DB의 다양한 접두어 체계 설명 추가 (Claude.ai)

M6로 이관된 사항:
- 벤치마크 스크립트 Solo 전용 리팩토링
- pipeline.py 전역 에러 핸들링 강화
- main.py → pipeline.py 기반 교체
- analysis_results 스키마 갱신
- 벡터 검색 async 병렬화 (선택)

---

## M5 벤치마크 결과 — M4 대비

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

---

## M5 아키텍처 최종 확정

최종 아키텍처 — Sonnet Solo:
- 모델: claude-sonnet-4-6 (1회 호출)
- 게이트: 없음. 모든 기사가 패턴 매칭까지 도달
- CoT: Devil's Advocate — overall_assessment에서 (가)양질근거 + (나)문제근거를 모두 기술 후 종합 판단
- Few-shot: 9건 (TP 7 + TN 2), 심의자료+수상작 기반
- TN 보호: few-shot TN 예시의 overall_assessment 내부에서만 처리 (일반 문구 제거)
- 출력: JSON 객체 { overall_assessment, detections }
- 프롬프트: _SONNET_SOLO_PROMPT (6,926자, ~3,463 토큰)

파이프라인 최종 흐름:
```
기사 → 청킹 → 벡터검색 → Sonnet Solo(패턴 식별)
    → 규범 조회(get_ethics_for_patterns) → Sonnet(리포트, cite 태그)
    → CitationResolver(cite → 원문 치환) → 최종 리포트
```

아키텍처 시도 이력 (3회):
1. M4 기존 1-Call + 1단계 이진 게이트 + few-shot 9건 → FAIL (TP 양질 오판 + TN 보호 실패)
2. 2-Call (Haiku 대분류 의심 → Sonnet 소분류 검증) → FAIL (Haiku가 대분류조차 정반대로 판단)
3. **Sonnet Solo 1-Call (게이트 없음 + Devil's Advocate CoT)** → 부분 성공 (1순위 달성)

---

## M5 감리 이력

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
| 10 | Claude.ai | STEP 66 | PASS | CitationResolver 1차 감리 |
| 11 | Antigravity | STEP 67 | 조건부 FAIL | CRITICAL 1건 + MINOR 2건 발견 |
| 12 | Manus | STEP 67 | 조건부 승인 | MAJOR 1건 + MINOR 2건 발견 |
| 13 | Claude.ai | STEP 67-R | PASS | 독립 감리 수정 3건 반영 확인 |

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

## M5에서 확립된 핵심 교훈

17. **"도구는 촘촘하게, 판단은 사람에게"**: CR-Check는 촘촘한 그물. 오탐(FP)은 사용자의 선의에 의한 판단에 맡김. 양질의 기사를 문제삼는 것보다, 문제 기사를 놓치는 것이 더 위험. 도구 바깥에서 저널리즘과 비평에 대한 논의가 시작되어야 할 지점.
18. **게이트(이진 판정)의 구조적 한계**: "양질이면 즉시 []"는 TP/TN 트레이드오프를 해결 불가. 1-Call 게이트도, 2-Call Haiku 게이트도 동일 실패.
19. **Haiku의 분류 능력 한계**: 대분류 수준의 의심 식별조차 정반대로 판단. 비용 절약을 위한 Haiku 활용은 패턴 식별 작업에 부적합.
20. **Devil's Advocate CoT의 유효성**: 찬반 양론을 강제로 기술하게 하면, Sonnet 수준에서 CoT가 결론을 실제로 구속. TN 보호에 가장 효과적.
21. **TN 보호 문구의 역효과**: 일반 문구("탐사보도는 양질")가 TP에도 적용되어 과잉 보호. few-shot 예시 내부에서만 TN 보호를 기술하는 것이 정밀.
22. **Data Implant의 한계**: 패턴 description에 키워드를 추가해도 임베딩 벡터 방향이 유의미하게 바뀌지 않음. 벡터 검색 CR 개선은 임베딩 모델 교체가 필요.
23. **결정론적 인용의 in-memory 원칙**: LLM에게 제공되지 않은 규범을 DB에서 찾아 치환하면 검증되지 않은 관계가 리포트에 포함된다. "환각보다 위험한 그럴듯한 오류." in-memory 매칭만 허용하고, 매칭 실패는 환각으로 처리한다.
24. **방어적 조건문의 중요성**: Python에서 빈 리스트([])는 falsy. `if a and b:`에서 b가 빈 리스트이면 전체가 스킵된다. 방어 코드를 사전에 고려하지 않으면 독립 감리에서 CRITICAL로 발견된다.
25. **독립 감리의 가치**: 1차 감리(Claude.ai)가 놓친 CRITICAL 버그를 Antigravity가 발견했다. 삼각편대 감리 체계의 유효성이 재확인되었다.
26. **크로스체크의 위력**: M5.5에서 4자가 동일 범위를 독립 검토한 결과, Antigravity만 발견한 메타 패턴 모순(CRITICAL), Manus만 제기한 fallback UX 문제 등 단일 감리로는 포착 불가능한 이슈가 발견되었다. 동시에 Manus의 CRITICAL 판정 2건 중 1건은 오해(is_active 혼동)로 판명 — 감리 결과도 교차 검증이 필요하다.
27. **JEC ≠ JCE**: DB에는 JEC(언론윤리헌장), JCE(기자윤리강령), JCP, PCE, PCP 등 다양한 접두어가 존재하며 모두 정상이다. "KJA 금지"라는 역사적 맥락이 "JCE만 사용"으로 오해되지 않도록 문서를 명확히 해야 한다.

---

## 주요 파일 경로

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-29_v18.md      <- ★ 이 문서
├── CR_CHECK_M5_PLAYBOOK.md                <- M5 플레이북 (STEP 51~70)
├── M5_BENCHMARK_RESULTS.md                <- ★ M5 Sonnet Solo 26건 벤치마크
├── M5_STEP57_SONNET_SOLO_CLI_PROMPT.md    <- Sonnet Solo CLI 프롬프트 (참조용)
├── M5_STEP65_CLI_PROMPT.md                <- CitationResolver CLI 프롬프트
├── M5_STEP67_AUDIT_PROMPTS.md             <- 독립 감리 프롬프트
├── M5_STEP67R_CLI_PROMPT.md               <- 독립 감리 수정 CLI 프롬프트
├── M5_STEP69_CLI_PROMPT.md                <- SESSION_CONTEXT 갱신 프롬프트
├── [감리 리포트] 2차 독립 감리 리포트 (Antigravity).md
├── [감리 리포트] 2차 독립 감리 리포트 (Manus).md
├── M4_BENCHMARK_RESULTS_sonnet46.md       <- M4 Sonnet v2 벤치마크 (비교 기준선)
├── M4_BENCHMARK_RESULTS.md                <- M4 Haiku 벤치마크
├── M4_BENCHMARK_RESULTS_opus46.md         <- M4 Opus 오라클 테스트
├── M3_BENCHMARK_RESULTS.md                <- M3 벤치마크
├── golden_dataset_final.json              <- ★ Dev Set 26건
├── golden_dataset_labels.json             <- ★ 레이블링 v3
├── ethics_codes_mapping.json              <- 윤리 규범 394개
├── current-criteria_v2_active.md          <- 패턴 119개 (28개 소분류 활성)
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- ★ RAG 마스터 플랜
├── M5_FEWSHOT_RAW_MATERIALS.md            <- Few-shot 소재 원본
├── M5_ETHICS_REVIEW_ANALYSIS.md           <- 윤리 심의 분석
└── _archive_superseded/                   <- v14, v15, v16, v17 포함
```

### 백엔드 (backend/core/) — M5 최종
```
/Users/gamnamu/Documents/cr-check/backend/core/
├── db.py                  <- M4: Supabase 연결
├── chunker.py             <- M4: 기사 청킹
├── pattern_matcher.py     <- ★ M5 변경 (Phase C): Sonnet Solo 활성
│   ├── match_patterns_solo()     ← 활성 (게이트 없음 + Devil's Advocate)
│   ├── _SONNET_SOLO_PROMPT       ← 활성 프롬프트 (6,926자)
│   ├── _parse_solo_response()    ← 객체 파싱 ({overall_assessment, detections})
│   ├── match_patterns_2call()    ← [DEPRECATED] 2-Call
│   ├── match_patterns()          ← [DEPRECATED] 1-Call
│   └── _HAIKU_SYSTEM_PROMPT      ← [DEPRECATED]
├── report_generator.py    <- M4: Sonnet 리포트 (미수정, cite 태그 출력)
├── citation_resolver.py   <- ★ M5 신규 (Phase D): 결정론적 인용 후처리
│   ├── resolve_citations()       ← 메인 함수 (in-memory 매칭, DB 조회 없음)
│   ├── _truncate_text()          ← 200자 절단 (어절/쉼표/줄바꿈 경계)
│   ├── _format_citation()        ← 치환 형식 생성 (첫출현=원문, 이후=참조)
│   └── _CITE_PATTERN             ← cite 태그 정규식 (3종 변형 대응)
├── pipeline.py            <- ★ M5 변경 (Phase D): resolve_citations() 통합
│   └── analyze_article()         ← 최종 흐름: Solo → report → resolve → 결과
├── analyzer.py            <- 기존 MVP
├── criteria_manager.py    <- 기존
└── prompt_builder.py      <- 기존
```

### 벤치마크 스크립트
```
/Users/gamnamu/Documents/cr-check/scripts/
├── benchmark_pipeline_v3.py   <- ★ M5 변경: Solo 경로 + overall_assessment 기록
├── test_citation_resolver.py  <- ★ M5 신규: CitationResolver 테스트
└── generate_embeddings.py     <- 임베딩 생성
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **M5 Phase A~E 전체 완료.** Sonnet Solo + CitationResolver 확정. 벤치마크 1순위(TN FP ≤ 33%) 달성.
2. **다음 작업은 M6.** 진행 순서 (★ 로컬 E2E 검증 우선):
   **Step 0 (최우선)**: main.py의 /analyze 엔드포인트를 pipeline.py 기반으로 교체
     → localhost에서 실제 기사 URL 입력 → M5 파이프라인(Sonnet Solo + CitationResolver) 실행
     → 프론트엔드(localhost:3000)에서 리포트 화면 렌더링 확인
     → 이 시점에서 품질 체감 + 프롬프트/리포트 형식 추가 개선 판단
     → 로컬 E2E 검증이 만족스러울 때까지 반복 후 다음 단계로 진행
   (a) 메타 패턴 추론 로직 (마스터 플랜 섹션 8)
   (b) Phase 1 아카이빙 통합 (articles, analysis_results 스키마 갱신 + 공개 URL)
   (c) 클라우드 배포 (Railway + Vercel)
   (d) Reserved Test Set 검증 (73건 중 일부)
   (e) 벡터 검색 개선 (선택, CR 50.8% 천장)
   ※ M5.5 감리에서 M6로 이관된 사항: 벤치마크 Solo 리팩토링, 전역 에러 핸들링, analysis_results 스키마 갱신, 벡터 검색 async 병렬화
3. **모델은 Sonnet 4.6 단독.** Haiku 호출 없음. pattern_matcher.py의 match_patterns_solo() 활성.
4. **프롬프트는 Devil's Advocate CoT 구조.** 게이트 없음. 1단계/2단계 구분 없음. 이전으로 되돌리지 말 것.
5. **출력 형식은 JSON 객체** {overall_assessment, detections}. 배열이 아님.
6. **파이프라인 최종 흐름**: 청킹 → 벡터검색 → Sonnet Solo(패턴 식별) → 규범 조회 → Sonnet(리포트) → CitationResolver → 최종 리포트
7. **v7~v17의 모든 지침 유효.** 교훈 1~25 모두 적용.
8. **CLI 자율 진행 제한.** 플레이북 단계별 승인 게이트 엄격 적용.
9. **클라우드 배포는 M6에서.**
10. **역할 체계 유지.** Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Manus(2차) → Gamnamu(승인).

### M6로 이관된 미해결 과제

- **양질 오판 TP 4건** (A-01, A-06, B2-10, A-17): "형식적 근거가 탄탄한" 기사에서 LLM이 내용 결함을 감지하지 못함. few-shot 보강 또는 레이블 재검토 가능. 단, 교훈 17("도구는 촘촘하게, 판단은 사람에게")에 의해 현 수준 수용 가능.
- **TN FP 2건** (C-02, E-17): 인권/AI 윤리 관련 기사에서 오탐 지속. TN few-shot 추가(현재 2건→3~4건)로 개선 가능성.
- **벡터 검색 CR 50.8% 천장**: 임베딩 모델 교체 또는 패턴 description 전면 재작성이 필요.
- **메타 패턴 추론**: 1-4-1(외부 압력), 1-4-2(상업적 동기)의 조합 추론 로직 미구현.

### 주의사항

- **KJA 접두어 절대 금지** (구버전, 완전 폐기됨). DB에는 다양한 접두어가 존재하며, 모두 정상:
  JEC(언론윤리헌장), JCE(기자윤리강령), JCP(기자윤리실천요강),
  PCE(신문윤리강령), PCP(신문윤리실천요강),
  기타: DRG, EPG, HSD, IRG, MRG, PRG, SPG, SRE 등
- **JEC/JCE 접두어 불일치 확인 필요**: DB 실제 코드(JEC-1 등) vs 문서 표기 차이 존재 가능. M6에서 점검.
- **Supabase Legacy JWT 키 사용 중.**
- **GitHub PAT 만료일: 2026-04-16.**
- **supabase start → Docker 필요.** 로컬 DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Reserved Test Set 73건은 참조 금지.**
- **벤치마크 결과 파일 삭제 금지.**
- **deprecated 코드(1-Call, 2-Call) 삭제 금지.** 비교 실험용 보존.

---

*이 세션 컨텍스트는 2026-03-29에 v17→v18로 갱신되었다.*
*M5 Phase A~E 전체 완료 (Sonnet Solo 확정 + CitationResolver 구현 + 독립 감리 수정 반영).*
*다음 마일스톤: M6 (메타 패턴 추론 + Phase 1 아카이빙 + 클라우드 배포).*
