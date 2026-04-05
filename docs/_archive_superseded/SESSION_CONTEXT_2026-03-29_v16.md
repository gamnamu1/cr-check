# 세션 컨텍스트 — 2026-03-29 v16

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M4가 모두 완료**되었다.
M4에서 파이프라인 구조(청킹→벡터검색→LLM패턴식별→밸리데이션→리포트)를 구현하고,
6회의 체계적 벤치마크를 통해 **현 파이프라인의 성능 상한과 구조적 한계를 정밀 실증**했다.

**M4 핵심 결론:**
1. 모델 교체(Haiku→Sonnet→Opus)만으로는 목표 달성 불가
2. 프롬프트 재설계(2단계 품질평가+few-shot)는 TN 구분과 Precision에서 부분적 효과
3. 벡터 검색 Candidate Recall 50.8%가 모델과 독립적인 구조적 천장
4. 저널리즘 비평의 본질적 주관성을 감안하면, 현재 도달한 수준도 허용 범위 안에 있음

다음 작업은 **M5(프롬프트 고도화 + 결정론적 인용 + 성능 최적화)**.

### v15→v16 변경 사항 (2026-03-29)

**M4 완료 (RAG 파이프라인 구현 + 성능 실증):**

파이프라인 구현:
- 날짜: 2026-03-29
- 구현 파일: chunker.py(277줄), pattern_matcher.py(404줄), report_generator.py(215줄), pipeline.py(96줄), db.py(45줄)
- 벤치마크: benchmark_pipeline_v3.py(415줄) — --model/--ids 옵션, Category Recall 보조지표 포함
- 입력 전환: article_key_text(74자) → 기사 전문(평균 ~2000자) — Golden_Data_Set_Pool/article_texts/에서 로드
- 모델: claude-sonnet-4-6 (최종 확정)
- 벡터 검색: VECTOR_MATCH_COUNT=7, threshold=0.2

프롬프트 최종 상태 (_HAIKU_SYSTEM_PROMPT):
- 2단계 구조: 품질 평가(양질의 보도면 [] 반환) → 패턴 식별
- Few-shot 예시: TP 1건(B-01, 1-5-2+1-7-5) + TN 1건(C2-07, [])
- JSON CoT 순서: matched_text → reasoning → severity → pattern_code
- 혼동 패턴 쌍 구분 가이드 5쌍
- ★ 후보 비중 완화: "동등하게 선택"
- 기사 길이별 상한: 200자 미만 1~2개 ~ 2000자 이상 4~5개
- 중복 pattern_code 제거 (call_haiku 내 seen_codes)

**M4 벤치마크 결과 — 6회 실험 비교:**

| 실험 | 모델 | 입력 | FR | FP | Cat R | TN FP | 비고 |
|------|------|------|----|----|-------|-------|------|
| 1. Haiku key_text | Haiku 4.5 | key_text 74자 | 23.3% | 17.4% | — | N/A | 최초 벤치마크 |
| 2. Haiku full | Haiku 4.5 | 기사 전문 | 20.0% | 16.4% | 30.0% | 100% | 기사 전문 전환 |
| 3. Sonnet v1 | Sonnet 4.6 | 기사 전문 | 35.0% | 22.9% | 64.2% | 100% | 오라클 테스트 |
| 4. Opus v1 | Opus 4.6 | 기사 전문 | 39.2% | 25.7% | 64.2% | 100% | 오라클 테스트 |
| 5. **Sonnet v2** | **Sonnet 4.6** | **기사 전문** | **28.3%** | **27.5%** | **46.7%** | **67%** | **최종 (2단계+few-shot)** |

- Candidate Recall: 전 실험 50.8% 동일 (벡터 검색은 모델과 독립적)
- 목표 기준: CR≥70%, FR≥80%, FP≥60%, TN FP<30%
- 벤치마크 결과 파일: docs/M4_BENCHMARK_RESULTS.md (Haiku), _sonnet46.md (Sonnet v2), _opus46.md (Opus)

**M4 감리 이력:**

| # | 감리자 | 결과 | 내용 |
|---|--------|------|------|
| 1 | Claude.ai (1차) | STEP 37~47 감리 | chunker/pattern_matcher/report_generator/pipeline/benchmark 코드 리뷰 |
| 2 | Antigravity (2차) | 독립 감리 | JSON CoT 순서 변경 제안(채택), 청크 합산 유니크 셋 제안 |
| 3 | Manus (3차) | 독립 감리 | 2단계 파이프라인 제안(M5 검토 사항), 의미론적 임피던스 불일치 진단 |
| 4 | 3자 합동 | 합의 | 기사 전문 전환(즉시), 혼동 쌍 가이드(즉시), M5 방향 설정 |

**M4에서 확립된 핵심 교훈:**

10. **모델 교체 ≠ 해결**: Haiku→Opus 5배 비용에도 FR +19%p, TN FP 여전 100%.
11. **확인 편향 프레이밍**: "문제를 찾아라"는 지시가 LLM에게 강력한 확인 편향을 유발. 2단계 품질 평가로 부분 해결.
12. **Few-shot이 캘리브레이션의 핵심**: E-12가 3건 테스트에서 FR 1.00을 기록한 것이 증거. 확대 시 성능 향상 가능성 높음.
13. **벡터 검색은 보조, LLM이 주역**: Opus가 CR 0%인 케이스에서도 정답을 찾아냄. ★ 강조가 오히려 방해가 될 수 있음.
14. **Recall-Precision 트레이드오프**: 2단계 품질평가로 Precision 최고치(27.5%)였으나 Recall 하락(28.3%).
15. **저널리즘 비평의 본질적 주관성**: 기사 품질 판단은 주관적·정파적. CR-Check는 "관점을 제시하는 도구"로 위치.
16. **CLI 자율 진행의 리스크**: 플레이북 단계를 CLI가 자의적으로 뛰어넘으면 감리 에너지가 분산됨. M5에서 단계별 승인 게이트 엄격 적용.

---

## M1~M3 완료 이력 (v15에서 계승)

- M1 Migration: `20260328000000_create_cr_check_schema.sql` (407줄)
- M2 Migration: `20260328100000_seed_data.sql` (1,257줄)
- DB 객체: 테이블 9개, 뷰 2개, RPC 함수 5개, 트리거 함수 1개, 트리거 2개
- 시드: ethics_codes 394, patterns 38, hierarchy 42, relations 70+10
- M1 감리 수정 5건, M2 감리 수정 2건 (v14 참조)

---

## 골든 데이터셋 최종 현황

### 확정 Dev Set (26건 = TP 20 + TN 6)

| 대분류 | 선별 수 | 대표 ID |
|--------|---------|---------|
| 1-1 진실성 | 3건 | A-01, A-06, B2-10 |
| 1-2 투명성 | 0건 | (Phase 1 메타데이터 모듈로 이관) |
| 1-3 균형성 | 3건 | B-11, B2-14, E-11 |
| 1-4 독립성 | 2건 | A2-13, B-15 |
| 1-5 인권 | 4건 | B-01, A-11, A-17, E-12 |
| 1-6 전문성 | 2건 | A2-03, B2-09 |
| 1-7 언어 | 3건 | A2-05, E-15, B-08 |
| 1-8 디지털 | 3건 | D-01, D-02, D-04 |
| True Negative | 6건 | C-02, C-04, C2-01, C2-07, E-17, E-19 |

### 기사 전문 텍스트 (M4에서 전환)
- 경로: /Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts/
- 파일 형식: {candidate_id}_article.txt (26건 전부 존재)
- 평균 길이: ~2000자, 청크 ~4개

---

## M5 방향 — 다음 세션에서 플레이북 작성

### M5 목표 재정의

M4의 교훈을 반영하여, M5의 목표를 **"80% 정확도 달성"에서 "실용적 품질의 분석 도구 완성"**으로 재정의.
CR-Check는 저널리즘 비평의 **관점을 제시하는 도구**이지, 절대적 판정을 내리는 시스템이 아니다.
성능 목표는 "양질의 보도를 문제 기사로 오판하지 않는 것(TN 정확도)"에 우선순위를 둔다.

### M5에서 다뤄야 할 과제 (우선순위순)

1. **Few-shot 확대**: 현재 2건(TP 1 + TN 1) → 대분류별 1건씩 8~10건으로 확대.
2. **TN 구분 강화**: 인권·차별·정치 주제의 양질의 보도를 오판하지 않도록. 추가 TN few-shot 또는 사전 분류 단계 검토.
3. **결정론적 인용 후처리** (마스터 플랜 원래 범위): cite 태그 → 원문 치환. chunker.py 위치 매칭 보강 필요.
4. **벡터 검색 개선**: CR 50.8% 천장 타파. 임베딩 모델 교체, 패턴 description 보강, 또는 벡터 검색 역할 축소.
5. **메타 패턴 추론** (마스터 플랜 원래 범위): 1-4-1, 1-4-2 등 메타 패턴의 하위 패턴 조합 추론.
6. **골든 데이터셋 레이블 재검토**: 일부 경계 케이스(B2-10 등)의 기대 패턴이 과도할 수 있음.
7. **클라우드 배포**: M5 성능 확정 후 일괄 수행.

### M5에서 적용할 프로세스 교훈

- **CLI 단계별 승인 게이트**: 플레이북 각 STEP에서 CLI가 자의적으로 다음 단계로 넘어가지 못하도록 엄격 적용.
- **3건 테스트 → 승인 → 26건 실행**: 전체 벤치마크 전 반드시 선별 테스트 (M4에서 확립).
- **벤치마크 결과 파일 분리**: 각 실험 결과를 별도 파일로 보존 (M4에서 확립).
- **CLI 보고 vs 파일 교차 검증**: CLI가 보고한 수치를 실제 파일과 반드시 대조 (M4에서 불일치 발견됨).

---

## 주요 파일 경로

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-29_v16.md      <- ★ 이 문서
├── M4_BENCHMARK_RESULTS.md                <- Haiku 벤치마크 (기사 전문)
├── M4_BENCHMARK_RESULTS_sonnet46.md       <- ★ Sonnet v2 최종 벤치마크
├── M4_BENCHMARK_RESULTS_opus46.md         <- Opus 오라클 테스트
├── M3_BENCHMARK_RESULTS.md                <- M3 벤치마크 (벡터 검색 단독)
├── golden_dataset_final.json              <- ★ Dev Set 26건
├── golden_dataset_labels.json             <- ★ 레이블링 v3
├── ethics_codes_mapping.json              <- 윤리 규범 394개
├── current-criteria_v2_active.md          <- 패턴 119개
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- ★ RAG 마스터 플랜
└── _archive_superseded/                   <- v14, v15 포함
```

### 백엔드 (backend/core/) — M4에서 구현/수정
```
/Users/gamnamu/Documents/cr-check/backend/core/
├── db.py                  <- M4 신규: Supabase 연결 공통 모듈
├── chunker.py             <- M4 신규: 기사 청킹 (300~500자 의미 기반 병합)
├── pattern_matcher.py     <- M4 신규: 벡터 검색 + LLM 패턴 식별 (Sonnet 4.6)
├── report_generator.py    <- M4 신규: Sonnet 리포트 생성 (결정론적 인용)
├── pipeline.py            <- M4 신규: 파이프라인 오케스트레이션
├── analyzer.py            <- 기존: MVP 분석기
├── criteria_manager.py    <- 기존: 평가 기준 관리
└── prompt_builder.py      <- 기존: 프롬프트 빌더
```

### 기사 전문
```
/Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts/
├── A-01_article.txt ~ E-19_article.txt  (26건)
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **M4 완료.** 파이프라인 구조 PASS, 성능 기준 FAIL → Haiku 단독 한계 실증 → Sonnet 4.6 전환 완료.
2. **M5 플레이북을 작성하는 것이 첫 번째 작업.** 위 "M5 방향" 섹션을 기반으로 Gamnamu님과 협의하여 확정.
3. **모델은 Sonnet 4.6으로 확정.** pattern_matcher.py의 HAIKU_MODEL이 claude-sonnet-4-6으로 변경된 상태.
4. **프롬프트는 2단계 구조 + few-shot이 최종 상태.** 이전으로 되돌리지 말 것.
5. **기사 전문 26건 파일 있음.** benchmark_pipeline_v3.py가 Golden_Data_Set_Pool/article_texts/에서 자동 로드.
6. **TN 6건 중 2건(C2-01, C2-07) 정상 판정, 4건 여전히 FP.** M5에서 TN 구분 강화 필요.
7. **v7~v15의 모든 지침은 그대로 유효.** 교훈 1~9(v15) + 10~16(v16) 모두 적용.
8. **CLI 자율 진행 제한.** 플레이북 단계별 승인 게이트 엄격 적용.
9. **클라우드 배포는 M5 성능 확정 후.**
10. **역할 체계 유지.** Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Gemini(2차) → Gamnamu(승인).

### 주의사항
- **KJA 접두어 절대 금지.** JCE가 올바른 접두어.
- **Supabase Legacy JWT 키 사용 중.**
- **GitHub PAT 만료일: 2026-04-16.**
- **supabase start → Docker 필요.** 로컬 DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Reserved Test Set 73건은 참조 금지.**
- **벤치마크 결과 파일(M4_BENCHMARK_RESULTS*.md) 삭제 금지.**
- **Few-shot 예시 2건(B-01, C2-07)은 벤치마크 대상이므로** 성능 과대평가 가능성에 유의.

---

*이 세션 컨텍스트는 2026-03-29에 v15→v16으로 갱신되었다.*
*v15는 `_archive_superseded/`로 이동할 것.*
