# 세션 컨텍스트 — 2026-04-05 v21

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A+B+C 완료**, **STEP 87(리포트 품질 개선) 실질 완료**.
파이프라인 전체가 정상 작동하며, 리포트 품질이 기존 시스템(DB 구축 전) 수준으로 회복되었다.
다음은 **Phase γ(미세 조정) + WIP→main 분리 커밋**이다.

### v20→v21 변경 사항 (2026-04-05)

**STEP 87 리포트 품질 개선 — 실질 완료:**

이 세션에서 5개 AI 감리 진단서 교차 분석 → 진단용 JSON 덤프 코드 삽입 → 3단계(Phase α·β + 임베딩 생성)에 걸친 수정을 수행했다. 리포트 품질이 기존 시스템 수준으로 회복되었고, Bug A·B·C가 모두 해결되었다.

**Phase α — 버그 수정 (3건):**

1. **Bug A — 벡터 검색 0건**: `pattern_matcher.py`의 `search_vectors()`와 `generate_embeddings()`에 상세 로깅 추가. 원인은 patterns 테이블에 임베딩 벡터 미삽입이었음 (아래 임베딩 생성에서 해결).
2. **Bug B — JSON 파싱 전체 실패**: `_parse_solo_response()`에 3단계 fallback 구현 (정상 파싱 → `_fix_llm_json()` 복구 → 정규식 추출). Sonnet Solo 프롬프트에 matched_text 형식 경고 추가.
3. **Bug C — 규범 조회 간헐적 0건**: `fetch_ethics_for_patterns()`에 2초 대기 재시도 + REST API 직접 JOIN 조회 fallback 추가. 리포트 생성 재시도 루프에 API 에러 상세 로깅 강화.

**Phase β — 인용 구조 전환 + 프롬프트 정비 (핵심 변경):**

1. **cite 태그 방식 완전 폐기**: `_SONNET_SYSTEM_PROMPT`를 전면 교체. Sonnet이 규범 원문을 알고 있는 상태에서 자연스럽게 녹여 쓰도록 변경. `<cite ref="..."/>` 태그 → 조항 번호 명시 + 핵심 문구 발췌 인용.
2. **citation_resolver 비활성화**: `pipeline.py`의 `resolve_citations` 호출 루프를 주석 처리. `citation_resolver.py` 파일 자체는 보존 (복원 가능).
3. **_build_ethics_context() 형식 변경**: `### 제목 (코드: X, Tier N)` 형식으로 Sonnet이 조항 번호를 쉽게 참조할 수 있게 수정.
4. **프롬프트 정비**: 롤업 지시 정정 (1~2회 구체→상위 확장), 3종 톤 재설계 (시민: 함께 살펴보는 관점, 학생: 함께 탐구), 서술 스타일 가이드 추가 (중간제목 제한, "문제" 반복 금지, 제목 중복 방지).

**임베딩 생성:**

- `scripts/generate_embeddings.py` 실행: patterns 28건 + ethics_codes 373건 = 401건 임베딩 생성 완료
- 모델: text-embedding-3-small (1536차원), 비용 ~$0.003
- 벡터 검색 정상화 확인: `candidate_count: 11` (이전 0건)

**진단 체계 구축:**

- `pipeline.py`의 `analyze_article()` 끝에 진단용 JSON 덤프 코드 추가
- `backend/diagnostics/` 디렉토리에 기사별 5개 관문(청킹/벡터검색/패턴식별/규범조회/리포트) 데이터 자동 저장
- 다중 AI 감리 체계 활용: Claude.ai(설계·1차 감리) + Antigravity(독립 2차 감리) + Manus(독립 2차 감리) + Claude Code CLI(구현)

**최종 테스트 결과 (4건 기사):**

| 기사 | 패턴 식별 | 벡터 후보 | 규범 조회 | 리포트 | 시간 |
|------|----------|----------|----------|--------|------|
| 세계일보 이준석 | 3건 ✅ | 11건 ✅ | 28건 ✅ | 3종 ✅ | 100초 |
| 조선일보 이준석 | 2건 ✅ | — | 19건 ✅ | 3종 ✅ | 97초 |
| 연합뉴스 노동생산성 | 2건 ✅ | — | 11건 ✅ | 3종 ✅ | — |
| 나일 외국인 범죄 | 4건 ✅ | 11건 ✅ | 38건 ✅ | 3종 ✅ | 133초 |

---

## 다음 세션 작업: Phase γ — 미세 조정 + 커밋

### 작업 1: 조항 번호 표시 통일 (프롬프트 보완)

현재 리포트에서 일부 규범이 "제3조 2항"처럼 자연스러운 한국어 조항 번호로 표시되지만,
다른 곳에서는 "JEC-7", "HSD-1", "HRG-5-2b" 같은 내부 코드가 그대로 노출된다.
Sonnet이 `ethics_code`를 한국어 조항 번호로 변환해서 쓰도록 프롬프트를 보완해야 한다.

### 작업 2: 무관한 규범 매핑 정비 (DB 데이터)

`pattern_ethics_relations` 테이블에 관련성 낮은 규범이 다수 포함되어 있다.
예: 1-7-5(감정 자극 과장)에 "이주노동자 잠재적 범죄자 표현 금지(HRG-5-2b)" 매핑.
Sonnet이 알아서 걸러 쓰고 있지만, 매핑을 정비하면 컨텍스트 노이즈가 줄고 비용도 절감된다.

### 작업 3: WIP→main 분리 커밋

STEP 86 PASS 확정 후, `feature/m6-wip` 브랜치에서 main으로 분리 커밋:
A(기동확인) → B(기동확인) → C(기동확인) → STEP 87 수정사항(기동확인)

### 작업 4 (선택): Phase 1 모델 교체 실험

Phase 1(패턴 식별)에 Opus 4.6 또는 Sonnet 4.5를 투입하여 A/B 비교.
비용 대비 품질 향상 효과 측정. 현재 Sonnet 4.6이 Phase 1·2 모두 담당 중.

---

## M6 진행 현황 체크리스트

- [x] Phase A: 로컬 E2E 연결 ✅
- [x] Phase B: 코드베이스 위생 ✅
- [x] Phase C: 메타 패턴 추론 ✅
- [x] Phase C WIP 커밋 ✅
- [x] **★ STEP 86: 종합 E2E 품질 체감 ✅** ← v21 PASS
- [x] **★ STEP 87: 리포트 품질 개선 ✅** ← v21 완료 (Phase α·β + 임베딩)
- [ ] Phase γ: 미세 조정 (조항 번호 통일, 매핑 정비)
- [ ] WIP→main 분리 커밋
- [ ] Phase D: 아카이빙 통합
- [ ] Phase E: 클라우드 배포 (프로덕션 DB 임베딩 실행 필요)
- [ ] Phase F: Reserved Test Set 검증
- [ ] Phase G: 마무리

---

## 파이프라인 최종 흐름 (Phase β 완료 후) ★ v21 갱신

```
기사 → 청킹 → 벡터검색(OpenAI 임베딩, ★ 힌트) → ❶ Sonnet 4.6 Solo(패턴 식별 + Devil's Advocate CoT)
  → check_meta_patterns(탐지된 패턴, DB inferred_by 동적 조회)
  → 규범 조회(get_ethics_for_patterns RPC + REST API fallback)
  → ❷ Sonnet 4.6(3종 리포트: 규범 원문 직접 인용, cite 태그 미사용)
  → 최종 리포트 (citation_resolver 비활성화)
```

**v20 대비 변경점:**
- 벡터 검색: 임베딩 생성 완료, ★ 힌트 정상 작동
- 규범 조회: RPC 실패 시 REST API fallback 추가
- 리포트 생성: cite 태그 → 자연 인용 방식으로 전환
- CitationResolver: 비활성화 (코드 보존, pipeline.py에서 주석 처리)

---

## 주요 파일 경로 (★ v21 갱신)

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-04-05_v21.md      <- ★ 이 문서 (v21)
├── phase_beta_cli_prompt.md               <- ★ Phase β 수정 지시서 [NEW]
├── phase_beta_request.md                  <- ★ Phase β CLI 요청문 [NEW]
├── META_PATTERN_DESIGN_v1.md              <- 메타 패턴 상세 설계
├── CR_CHECK_M6_PLAYBOOK.md                <- M6 플레이북
├── M5_BENCHMARK_RESULTS.md                <- M5 벤치마크
├── golden_dataset_final.json              <- Dev Set 26건
├── golden_dataset_labels.json             <- 레이블링 v3
├── ethics_codes_mapping.json              <- 윤리 규범 394개
├── current-criteria_v2_active.md          <- 패턴 119개 (28개 소분류 활성)
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- RAG 마스터 플랜
├── Code of Ethics for the Press.md        <- 규범 원문
└── _archive_superseded/                   <- v14~v20 등
```

### 백엔드 (backend/core/) — ★ v21 갱신
```
/Users/gamnamu/Documents/cr-check/backend/core/
├── db.py                         <- M4: Supabase 연결
├── chunker.py                    <- M4: 기사 청킹
├── pattern_matcher.py            <- M5+α: Sonnet Solo (3단계 JSON fallback, 로깅 강화)
├── meta_pattern_inference.py     <- M6: 메타 패턴 추론
├── report_generator.py           <- ★ M6+β: 3종 리포트 (자연 인용, REST fallback)
├── citation_resolver.py          <- M5: 결정론적 인용 (비활성화, 코드 보존)
├── pipeline.py                   <- ★ M6+β: 파이프라인 (citation_resolver 주석, 진단 덤프)
├── analyzer.py                   <- 기존 MVP (참조용 보존)
├── criteria_manager.py           <- 기존
└── prompt_builder.py             <- 기존
```

### 진단 데이터 (backend/diagnostics/) ★ NEW
```
/Users/gamnamu/Documents/cr-check/backend/diagnostics/
└── diagnostic_{timestamp}.json   <- 기사별 5개 관문 데이터 자동 저장
```

---

## 오늘 확인된 핵심 기술 사항 ★ v21

### 인용 대체 아키텍처가 품질 저하의 근본 원인이었다

5개 AI 감리 진단서(Claude, Gemini, Manus, NotebookLM, Perplexity)를 종합한 결과,
Sonnet이 규범 원문 없이 리포트를 작성하고 `<cite>` 태그를 기계적으로 후치환하는 구조가
품질 저하의 근본 원인으로 확인되었다. Phase β에서 이를 전면 전환하여 해결.

### 규범 조회 간헐적 실패의 원인

`get_ethics_for_patterns` RPC가 특정 패턴 ID 조합에서 간헐적으로 0건을 반환.
같은 패턴(1-3-1)이 다른 패턴과 함께일 때는 성공, 단독(또는 1-1-1과만)일 때는 실패.
근본 원인은 RPC 함수 내부 로직(재귀 CTE + is_citable/is_active 필터)의 간헐적 문제로 추정.
REST API 직접 조회 fallback으로 안정적 우회 해결.

### 벡터 검색 0건의 원인

patterns 테이블의 `description_embedding` 컬럼에 벡터 데이터가 한 번도 삽입되지 않았음.
`scripts/generate_embeddings.py` 실행으로 28개 소분류 패턴 + 373개 규범에 임베딩 생성 완료.
**프로덕션 배포 시 같은 스크립트를 프로덕션 DB에도 실행해야 함.**

### 모델 버전

- pattern_matcher.py: `claude-sonnet-4-6` (Sonnet 4.6) ✅
- report_generator.py: `claude-sonnet-4-6` (Sonnet 4.6) ✅

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **STEP 87 실질 완료.** 리포트 품질이 기존 시스템 수준으로 회복됨. Phase γ(미세 조정) 진행.
2. **Phase β에서 cite 태그 방식을 폐기했다.** Sonnet이 규범 원문을 직접 읽고 자연스럽게 인용. citation_resolver.py는 비활성화(코드 보존). 이 구조를 되돌리지 말 것.
3. **벡터 검색이 정상 작동한다.** 임베딩 생성 완료. 프로덕션 배포 시 재실행 필요.
4. **규범 조회에 REST API fallback이 있다.** RPC 실패 시 자동 우회. 안정적 작동 확인됨.
5. **진단용 JSON 덤프가 pipeline.py에 있다.** `backend/diagnostics/`에 기사별 5개 관문 데이터 자동 저장. 문제 발생 시 이 데이터로 단계별 추적 가능.
6. **모든 모델은 Sonnet 4.6 (`claude-sonnet-4-6`).** 구 모델 사용하지 말 것.
7. **STEP 86 PASS 후**: WIP→main 분리 커밋 → Phase D.
8. **v20까지의 모든 지침 유효.** 교훈 1~27 모두 적용.
9. **CLI 자율 진행 제한.** 플레이북 STEP 단위 승인 게이트 엄격 적용.

### Phase γ 작업 목록 (다음 세션 우선순위)

1. **조항 번호 통일**: 프롬프트에 "JEC-7 같은 내부 코드 대신 '언론윤리헌장 제7조'처럼 한국어 조항 표현을 사용하세요" 지시 추가
2. **규범 매핑 정비**: `pattern_ethics_relations` 테이블에서 관련성 낮은 매핑 제거/수정
3. **WIP→main 분리 커밋**: Phase A → B → C → STEP 87 수정사항 순서로 커밋
4. **(선택) Phase 1 모델 실험**: Opus 4.6 또는 Sonnet 4.5 A/B 비교

### M6로 이관된 미해결 과제 (v20에서 계승)

- **양질 오판 TP 4건** (A-01, A-06, B2-10, A-17): 교훈 17에 의해 현 수준 수용 가능
- **TN FP 2건** (C-02, E-17): 인권/AI 윤리 관련 기사에서 오탐 지속
- **벡터 검색 CR 50.8% 천장**: 임베딩 생성 완료로 상황 변경, 재측정 필요

### 독립 감리 MINOR 사항 (M7 검토)

- Antigravity MINOR 1: 확신도 산식 (R=2, S=1 → low) — 현재 보수적 동작이 의도된 것
- Antigravity MINOR 2: 메타 패턴 전용 규범 인용 미포함 — cite 태그 폐기로 상황 변경, 재검토 필요

### 주의사항 (v20에서 계승)

- **KJA 접두어 절대 금지**
- **Supabase Legacy JWT 키 사용 중**
- **GitHub PAT 만료일: 2026-04-16** ← 임박, 갱신 필요
- **Reserved Test Set 73건은 참조 금지** (Phase F 전까지)
- **벤치마크 결과 파일 삭제 금지**
- **deprecated 코드 삭제 금지** (비교 실험용 보존)
- **프로덕션 배포 시 `scripts/generate_embeddings.py` 실행 필수** ★ NEW

---

*이 세션 컨텍스트는 2026-04-05에 v20→v21로 갱신되었다.*
*STEP 87 리포트 품질 개선 실질 완료. Phase α(버그 수정) + Phase β(인용 구조 전환) + 임베딩 생성.*
*전체 파이프라인 정상 작동 확인: 패턴 식별·벡터 검색·규범 조회·리포트 생성 모두 OK.*
*다음 작업: Phase γ(미세 조정) → WIP→main 분리 커밋 → Phase D(아카이빙).*
