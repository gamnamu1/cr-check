# CR-Check M6 — 로컬 E2E 검증 + 메타 패턴 추론 + 아카이빙 + 배포 + 검증 플레이북

> 작성일: 2026-03-30 (Claude.ai 초안)  
> 상태: **v4 — WIP 브랜치 전환 + STEP 요약 정합 (2026-03-31)**  
> 목적: M6 작업의 삼각편대 운영 절차를 STEP 단위로 정리  
> 역할: Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Manus(2차 독립 감리) → Gamnamu(승인)  
> 선행 완료: M1(스키마) + M2(시드) + M3(임베딩) + M4(RAG 파이프라인) + M5(프롬프트 고도화 + 결정론적 인용) + M5.5(종합 감리) ✅

---

## 공통 원칙 (M1~M5에서 계승)

- **Claude Code CLI 세션 시작 시 반드시**: `/effort max` 설정 → Plan Mode로 문서 숙지 후 Normal Mode 전환
- **컨텍스트 관리**: 50%에서 `/compact` 선제 실행. 변경 전 `/diff`로 사전 확인
- **쓰기 작업은 반드시 Migration 파일로만**. MCP는 읽기 전용 조회 전용
- **KJA 접두어 절대 사용 금지** → DB에는 JEC, JCE, JCP, PCE, PCP 등 다양한 접두어 존재 (모두 정상)
- **API 키**: 환경변수(`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)로 관리. 코드에 하드코딩 금지
- **⚠️ STEP 단위 실행 원칙**: STEP 1개 완료 → 보고 → STOP. 다음 STEP은 Gamnamu 지시 후에만 착수
- **⚠️ 감리 STEP 절대 건너뛰기 금지**: Phase는 논리적 그룹핑일 뿐
- **⚠️ 3건 테스트 → 승인 → 전체 실행**: 전체 벤치마크 전 반드시 선별 테스트
- **⚠️ CLI 보고 vs 파일 교차 검증**: CLI가 보고한 수치를 실제 파일과 반드시 대조
- **⚠️ FAIL 대응 원칙**: FAIL 시 같은 세션에서 즉시 대안 실행하지 않고 감리 의견 먼저 취합
- **⚠️ 깃 커밋 정책 (v4 — WIP 브랜치 방식)**:
  - **Phase A+B+C**: `feature/m6-wip` 브랜치에서 작업. 각 Phase 감리 통과 시 WIP 커밋으로 롤백 포인트 확보. **종합 E2E 검증(STEP 86) 통과 후**, WIP 이력을 Phase별 분리 커밋으로 정리하여 main에 반영 (A→기동확인→B→기동확인→C→기동확인). Gamnamu 직접 커밋 (CLI Deny List 항목)
  - **Phase D 이후**: 각 Phase 로컬 기동 확인 + 감리 통과 직후 Gamnamu 직접 커밋 (현행 유지)

---

## M6 작업 개요

| 항목 | 내용 |
|------|------|
| **목표** | CR-Check를 "로컬 프로토타입"에서 "배포 가능한 검증된 도구"로 전환 |
| **포지셔닝** | 재확인 — CR-Check는 저널리즘 비평의 **관점을 제시하는 도구** |
| **M5 성능 기준선** | TN FP 33% \| FR 36.7% \| FP 30.4% \| Cat R 54.2% \| CR 50.8% (Sonnet Solo 26건) |
| **모델** | claude-sonnet-4-6 (Sonnet Solo 1-Call, 게이트 없음) |
| **예상 일정** | 6~10 세션 (체크포인트별 분할) |
| **비용 추정** | 벤치마크 ~$0.50/회, Reserved Test ~$1.50, 배포 무료 티어 활용, 총 ~$5~8 |

### M6 핵심 과제 6가지

| # | Phase | 과제 | 핵심 가치 | 품질 영향 |
|---|-------|------|-----------|-----------|
| 1 | A | 로컬 E2E 연결 | main.py를 pipeline.py 기반으로 교체. 파이프라인↔프론트 연결 | ✅ 있음 |
| 2 | B | 코드베이스 위생 | M5.5 이관 기술 부채 해소. 벤치마크 Solo 리팩토링, 전역 에러 핸들링 | ❌ 거의 없음 |
| 3 | C | 메타 패턴 추론 | 1-4-1(외부 압력), 1-4-2(상업적 동기) 조합 추론 로직 완전 구현 | ✅ 있음 (큼) |
| 4 | ★ | 종합 E2E 검증 | 품질 영향 있는 모든 작업(A+C) 완료 후 한 번에 품질 체감 | — 평가 |
| 5 | D | Phase 1 아카이빙 | 분석 결과 DB 저장 + 공개 URL(`/report/{id}`) 공유 | ❌ 없음 |
| 6 | E | 클라우드 배포 | Railway(BE) + Vercel(FE) 일괄 배포 | ❌ 없음 |
| 7 | F | Reserved Test Set 검증 | 73건 중 선별하여 일반화 성능 확인 | — 평가 |

> **E2E 검증 원칙**: 품질에 0.01%라도 영향을 주는 수정(Phase A, C)을 모두 완료한 후,
> 종합 E2E 검증을 **한 번에** 실행한다. 불완전한 상태에서 중간 평가를 반복하지 않는다.
> 이렇게 해야 품질 누수의 원인을 명확히 추적할 수 있다.

### M5.5에서 M6로 이관된 사항

- [ ] 벤치마크 스크립트 Solo 전용 리팩토링 → Phase B
- [ ] pipeline.py 전역 에러 핸들링 강화 → Phase B
- [ ] main.py → pipeline.py 기반 교체 → Phase A
- [ ] analysis_results 스키마 갱신 → Phase D
- [ ] 벡터 검색 async 병렬화 → Phase B (선택)
- [ ] JEC/JCE 접두어 불일치 점검 → Phase A (E2E 중 확인)

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase A: 로컬 E2E 연결 (파이프라인↔프론트 기술적 연결)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> main.py를 M5 파이프라인(pipeline.py) 기반으로 교체하고,
> localhost에서 기술적으로 기동되는 것까지 확인한다.
> **품질 체감 평가는 Phase C 완료 후 종합 E2E에서 수행.** 여기서는 연결만.

### STEP 71. Claude.ai — main.py 교체 설계

**[배경]** 현재 main.py는 `core.analyzer`(구 MVP)를 사용한다.
M5에서 완성된 `core.pipeline`(Sonnet Solo + CitationResolver)로 교체해야 한다.
핵심: 분석 엔진(패턴 식별)은 M5로 교체하되, 3종 리포트와 프론트엔드는 그대로 유지한다.

**[설계 원칙 — CLAUDE.md "리포트 설계 원칙" 참조]**
- 3종 리포트(comprehensive/journalist/student) 유지. 단일 리포트로 통합 금지.
- 프론트엔드 무변경 (탭, 디자인, 폰트, TXT, SNS 공유 모두 유지).
- 규범 인용은 롤업 선택적 적용 원칙을 따른다.

**[아키텍처 변경]**

```
AS-IS: main.py → core/analyzer.py
  scraper → Phase 0(Red Flag) → Phase 1(Haiku) → Phase 2(Sonnet, 규범 직접 타이핑)
  → { article_info, reports: { comprehensive, journalist, student } }
  문제: Sonnet이 규범 원문을 직접 작성 → 환각 인용 발생

TO-BE: main.py → core/pipeline.py (수정)
  scraper → 청킹 → 벡터검색 → Sonnet Solo(패턴 식별 + Devil's Advocate CoT)
  → 규범 조회(get_ethics_for_patterns RPC, DB 기반)
  → Sonnet(3종 리포트, cite 태그 사용)
  → CitationResolver(cite → 규범 원문 치환, 3종 각각 적용)
  → { article_info, reports: { comprehensive, journalist, student } }
  개선: 규범 인용이 DB 기반 결정론적 — 환각 불가능
```

**[수정 대상]**

1. **report_generator.py**: 단일 report_text → 3종 리포트(dict) 반환으로 확장
   - Sonnet 프롬프트에 3종 JSON 반환 지시 (기존 analyzer.py Phase 2 방식 계승)
   - cite 태그 기반 결정론적 인용 + 롤업 선택적 적용 원칙 프롬프트 명시
   - article_analysis(기사 유형, 취재 방식 등) 생성도 포함
   - JSON 파싱 실패 시 재시도 로직 (analyzer.py의 max_retries=3 계승)
   - ReportResult.report_text → ReportResult.reports: dict 변경

2. **pipeline.py**: CitationResolver를 3종 리포트 각각에 적용
   - AnalysisResult.report_result 구조 조정

3. **main.py**: analyzer → pipeline 교체
   - 응답 구조 { article_info, reports } 유지 (프론트엔드 호환)
   - 추가 필드(overall_assessment, detections, meta)는 optional로 포함 (Phase D 활용)
   - /export-pdf 주석 처리 (Phase D에서 재설계)

4. **프론트엔드**: types/index.ts에 optional 필드 추가만. 기존 인터페이스 변경 없음.

**[규범 인용 프롬프트 핵심]**

```
## 규범 인용 원칙
- 각 문제점에 대해 가장 직접적으로 관련된 구체적 조항 하나를 인용하세요.
- 매 문제마다 하위→중위→상위 규범을 나열하지 마세요.
- 단, 여러 문제점이 하나의 상위 원칙으로 수렴하는 경우에 한해,
  종합 평가에서 "구체적 규범 → 포괄적 원칙" 순서로 계층 인용을 사용하세요.
- 인용 시 <cite ref="{ethics_code}"/> 태그만 삽입하세요. 원문을 직접 쓰지 마세요.
```

**[감리 판정 기준]**
- ✅ 3종 리포트 구조가 보존되는가 (reports: { comprehensive, journalist, student })
- ✅ 프론트엔드가 코드 변경 없이 동작하는가
- ✅ 3종 리포트 각각에 CitationResolver가 적용되는가
- ✅ 롤업 선택적 적용 원칙이 프롬프트에 명시되었는가
- ✅ article_info의 기존 메타데이터(기사 유형, 취재 방식 등)가 유지되는가
- ✅ scraper.py가 변경 없이 유지되는가

**[Gamnamu 판단 요청]**
- overall_assessment 처리: 리포트 본문(종합 평가 섹션)에 자연스럽게 녹이는 방향을
  CLI가 시도하되 종합 E2E(STEP 86)에서 체감 판단 — 이 방향으로 진행할지

---

### STEP 72. Gamnamu — E2E 교체 설계 승인

**[시점]** STEP 71 설계안 검토.

**[체크리스트]**
- [ ] 3종 리포트 유지 + 분석 엔진 교체 방향 → 승인/수정
- [ ] 규범 인용 롤업 선택적 적용 원칙 → 확인
- [ ] overall_assessment를 리포트 본문에 녹이는 방향 → 승인/수정
- [ ] 프론트엔드 무변경 원칙 → 확인

**[결과]** __ (Gamnamu 기입)

---

### STEP 73. Claude Code CLI — main.py 교체 + 프론트엔드 수정

**[시점]** STEP 72 승인 후. CLI 새 세션 시작.

**[프롬프트 — Claude Code CLI에게]**

```
/effort max

⚠️ 이 STEP(73)만 수행하라. 완료 후 결과를 보고하고 STOP.
다음 STEP(74: Claude.ai 감리)은 건너뛰지 마라. Gamnamu 지시 전까지 다음 작업에 착수하지 마라.

M5 완료, M6 Phase A(로컬 E2E 연결) 작업을 시작한다.

■ 사전 숙지 (Plan Mode로 먼저 읽을 것)
1. docs/SESSION_CONTEXT (최신 버전)
2. docs/CR_CHECK_M6_PLAYBOOK.md — 이 플레이북, STEP 73
3. backend/main.py — 현재 구조
4. backend/core/pipeline.py — M5 파이프라인
5. frontend/app/result/ — 현재 결과 페이지 구조
6. frontend/components/ResultViewer.tsx — 현재 리포트 뷰어
7. CLAUDE.md

■ 작업 1: backend/main.py 교체

1. `from core.analyzer import ArticleAnalyzer` → `from core.pipeline import analyze_article` 교체
2. `/analyze` 엔드포인트를 pipeline.py 기반으로 재작성:
   - scraper.scrape(url) → article_text 추출
   - analyze_article(article_text) → AnalysisResult
   - AnalysisResult를 응답 스키마로 변환
3. 응답 모델을 STEP 71에서 확정된 스키마로 교체
4. 기존 analyzer 인스턴스와 관련 코드 제거 (analyzer.py import만 제거, 파일 자체는 보존)
5. `/export-pdf` 엔드포인트는 일단 주석 처리 (Phase D에서 재설계)

■ 작업 2: 프론트엔드 최소 수정 (기존 구조 보존)

1. types/index.ts에 optional 필드 추가 (overall_assessment?, detections?, meta?)
   - 기존 AnalysisResult, AnalysisReport 인터페이스는 일절 변경 금지
2. ResultViewer.tsx, TxtPreviewModal.tsx — 변경 없음 (3종 탭, 디자인, 폰트 모두 유지)
3. API 응답이 기존 { article_info, reports } 구조를 유지하는지 확인

■ 작업 3: 로컬 기동 테스트

1. supabase start (Docker 확인)
2. backend: SUPABASE_LOCAL=1 uvicorn main:app --reload
3. frontend: npm run dev
4. localhost:3000에서 정상 로딩 확인
5. localhost:8000/docs에서 새 /analyze 스키마 확인

⚠️ 여기서는 "기술적으로 기동되는가"만 확인한다.
   품질 체감 평가는 Phase C 완료 후 종합 E2E(STEP 86)에서 수행.

■ 주의사항
- core/analyzer.py 파일 자체는 삭제하지 말 것 (기존 MVP 참조용)
- scraper.py는 변경하지 말 것
- 환경변수 확인: ANTHROPIC_API_KEY, OPENAI_API_KEY, SUPABASE_LOCAL
```

**[완료 기준]**
- [ ] main.py가 pipeline.py 기반으로 교체됨
- [ ] 프론트엔드 응답 타입이 새 스키마와 일치함
- [ ] `localhost:3000`이 정상 로딩됨 (에러 없음)
- [ ] `localhost:8000/docs`에서 새 /analyze 스키마 확인 가능

---

### STEP 74. Claude.ai — main.py 교체 1차 감리

**[감리 대상]** backend/main.py 변경분 + 프론트엔드 변경분

**[체크리스트]**

백엔드:
- [ ] pipeline.py의 analyze_article() 호출이 정확한가
- [ ] scraper 결과에서 article_text를 올바르게 추출하는가
- [ ] AnalysisResult → 응답 스키마 변환이 정보 손실 없는가
- [ ] 에러 핸들링이 기존 수준 이상인가 (pipeline 내부 에러 전파)
- [ ] CORS 설정이 유지되는가
- [ ] `/health` 엔드포인트가 유지되는가

프론트엔드:
- [ ] 새 응답 타입에 맞는 TypeScript 인터페이스가 정의되었는가
- [ ] 리포트 렌더링이 마크다운/HTML을 올바르게 처리하는가
- [ ] 로딩 상태, 에러 상태 UI가 유지되는가

**[판정]** ✅ PASS / ❌ FAIL (수정사항 명시)

**[감리 통과 시]** Phase A 작업분을 보존한 채 Phase B로 진행. ✦ `feature/m6-wip` 브랜치에 WIP 커밋 (롤백 포인트 확보). 최종 깃 커밋은 종합 E2E(STEP 86) 통과 후 Phase별 분리 커밋 시 수행.

---


---

### STEP 75. Antigravity/Manus — Phase A 독립 감리 (파이프라인 교체)

**[감리 범위]** Phase A 전체 — main.py 교체 + report_generator.py 3종 리포트 확장 + 프론트엔드 수정

**[감리 배경]**
M6 착수 전 점검 세션에서, 플레이북 초안이 3종 리포트를 단일 리포트로 통합하는 설계 오류를 포함한 사례가 발생했다.
이 독립 감리는 해당 설계 원칙(CLAUDE.md "리포트 설계 원칙")이 코드 레벨에서 올바르게 구현되었는지를
Claude 이외의 독립적 관점에서 검증하는 것이 목적이다.

**[감리 축]**

축 1 — 3종 리포트 구조 보존:
- report_generator.py가 { comprehensive, journalist, student } 3종 딕셔너리를 반환하는가
- main.py의 응답 스키마가 { article_info, reports: { comprehensive, journalist, student } } 구조인가
- CitationResolver가 3종 리포트 각각에 독립적으로 적용되는가
- 기존 프론트엔드의 3종 탭이 코드 변경 없이 동작하는가

축 2 — 규범 인용 원칙:
- 프롬프트에 롤업 선택적 적용 원칙이 명시되었는가
- cite 태그 기반 결정론적 인용이 유지되는가 (Sonnet이 규범 원문을 직접 쓰지 않음)
- CitationResolver의 in-memory 원칙이 유지되는가 (DB fallback 없음)

축 3 — 데이터 흐름 무결성:
- pipeline.py → report_generator.py → CitationResolver 흐름에서 정보 손실 없는가
- overall_assessment가 리포트에 자연스럽게 통합되었는가
- scraper.py가 변경 없이 유지되는가

**[Antigravity 프롬프트]**

```
CR-Check M6 Phase A 독립 감리를 수행하라.

■ 역할
너는 독립 감리자다. Claude.ai(1차 감리)와 다른 관점에서 코드를 검토한다.

■ 감리 대상 파일 (로컬 경로)
1. /Users/gamnamu/Documents/cr-check/backend/main.py
2. /Users/gamnamu/Documents/cr-check/backend/core/report_generator.py
3. /Users/gamnamu/Documents/cr-check/backend/core/pipeline.py
4. /Users/gamnamu/Documents/cr-check/backend/core/citation_resolver.py
5. /Users/gamnamu/Documents/cr-check/frontend/types/index.ts
6. /Users/gamnamu/Documents/cr-check/CLAUDE.md — "리포트 설계 원칙" 섹션

■ 핵심 검증 질문
1. report_generator.py가 3종 리포트(comprehensive, journalist, student)를 딕셔너리로 반환하는가?
   단일 report_text를 반환하면 CRITICAL.
2. CitationResolver가 3종 리포트 각각에 적용되는가?
   1종에만 적용되면 CRITICAL.
3. 프론트엔드 타입(types/index.ts)이 기존 3종 탭 구조와 호환되는가?
4. 롤업 선택적 적용 원칙이 Sonnet 프롬프트에 명시되어 있는가?
5. Sonnet이 규범 원문을 직접 생성하지 않고 cite 태그만 삽입하는가?

■ 출력 형식
[CRITICAL] / [MAJOR] / [MINOR] / [PASS] + 근거
```

**[Manus 프롬프트]** (파일 첨부 방식)

```
CR-Check M6 Phase A 독립 감리.

첨부 파일: main.py, report_generator.py, pipeline.py, citation_resolver.py, CLAUDE.md

핵심 질문:
1. 3종 리포트(comprehensive, journalist, student)가 코드에서 분리 유지되는가?
2. CitationResolver가 3종 각각에 적용되는가?
3. 프론트엔드 호환성이 유지되는가?
4. 규범 인용이 결정론적(cite 태그 → DB 조회 치환)인가?

[CRITICAL] / [MAJOR] / [MINOR] / [PASS]로 판정해줘.
```

**[판정]** ✅ PASS / ❌ FAIL (수정사항 명시)

**[FAIL 시]** 수정사항을 Claude.ai가 정리 → CLI 새 세션에서 수정 → Claude.ai 재감리 → 재커밋

**[감리 통과 시]** 수정분이 있으면 WIP 커밋에 amend, 없으면 그대로 Phase B로 진행.


---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase B: 코드베이스 위생 (M5.5 이관 사항)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> ⚠️ **체크포인트**: Phase A 감리 통과 + WIP 커밋 후 시작. CLI 컨텍스트 50% 이상이면 `/compact` 실행.
> 품질에 영향을 주지 않는 구조 정비. 새 기능을 얹기 전에 기존 코드를 정리한다.

### STEP 76. Claude Code CLI — 벤치마크 Solo 리팩토링 + 전역 에러 핸들링

**[프롬프트 — Claude Code CLI에게]**

```
/effort max

⚠️ 이 STEP (76P)만 수행하라. 완료 후 결과를 보고하고 STOP.

M6 Phase B — 코드베이스 위생 작업.

■ 사전 숙지
1. docs/SESSION_CONTEXT (최신 버전)
2. docs/CR_CHECK_M6_PLAYBOOK.md — STEP 76
3. scripts/benchmark_pipeline_v3.py — 현재 벤치마크
4. backend/core/pipeline.py — 현재 파이프라인
5. CLAUDE.md

■ 작업 1: 벤치마크 Solo 리팩토링

benchmark_pipeline_v3.py에서:
1. deprecated 2-Call / 1-Call 경로 코드를 제거하지 말고 "LEGACY" 블록으로 분리
2. 기본 실행 경로를 match_patterns_solo()로 고정
3. --legacy 플래그로 구 경로 실행 가능하게 유지 (비교 실험용)
4. 결과 출력에 "Sonnet Solo" 아키텍처 명시
5. overall_assessment를 결과 파일에 기록하는 로직 검증 (M5 STEP 변경분 확인)

■ 작업 2: pipeline.py 전역 에러 핸들링 강화

1. 각 단계(청킹, 임베딩, 벡터검색, 패턴매칭, 리포트, 인용해석)에 개별 try/except 추가
2. 각 단계 실패 시 어디서 실패했는지 명확한 에러 메시지 + 로깅
3. 중간 실패 시 부분 결과라도 반환하는 graceful degradation:
   - 벡터검색 실패 → 빈 후보로 패턴매칭 시도 (프롬프트만으로 판단)
   - 리포트 생성 실패 → 패턴 목록만 반환
   - 인용 해석 실패 → cite 태그 제거 후 리포트 반환 (이미 구현됨, 확인)
4. 최상위 에러는 main.py에서 HTTPException으로 변환

■ 주의사항
- deprecated 코드 삭제 금지
- 벤치마크 결과 파일(M4, M5) 삭제 금지
- 기능 변경 없음. 구조 정비만.
```

**[완료 기준]**
- [ ] 벤치마크 기본 경로가 Solo로 고정됨
- [ ] --legacy 플래그로 구 경로 접근 가능
- [ ] pipeline.py 각 단계에 개별 에러 핸들링 추가됨
- [ ] 기존 벤치마크(26건)가 동일 결과로 재현됨 (리팩토링 전후 결과 일치 확인)

---

### STEP 77. Claude.ai — 코드 위생 1차 감리

**[감리 대상]** benchmark_pipeline_v3.py + pipeline.py 변경분

**[체크리스트]**

벤치마크:
- [ ] Solo 기본 경로가 정확한가
- [ ] Legacy 경로가 보존되었는가
- [ ] 기존 결과 재현성이 확인되었는가

에러 핸들링:
- [ ] 각 단계별 try/except가 적절한 범위인가 (너무 넓지도, 좁지도 않은)
- [ ] 에러 메시지가 디버깅에 충분한 정보를 담는가
- [ ] graceful degradation이 올바르게 동작하는가
- [ ] 로깅 레벨이 적절한가 (ERROR vs WARNING vs INFO)

**[판정]** ✅ PASS / ❌ FAIL

**[감리 통과 시]** Phase B 작업분을 보존한 채 Phase C로 진행. ✦ `feature/m6-wip` 브랜치에 WIP 커밋 (롤백 포인트 확보). 최종 깃 커밋은 종합 E2E(STEP 86) 통과 후 Phase별 분리 커밋 시 수행.

---

### STEP 78. (선택) Claude Code CLI — 벡터 검색 async 병렬화

**[트리거]** Phase A 기동 테스트에서 응답 시간이 15초를 초과하는 경우에만 실행.

**[작업]**
- 청크별 임베딩 생성을 `asyncio.gather`로 병렬화
- 벡터 검색 호출을 병렬화
- 성능 개선 측정 (전후 비교)

**[생략 조건]** 15초 이내 응답이면 이 STEP은 건너뛴다. Gamnamu 확인 후 진행.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase C: 메타 패턴 추론 (완전 구현)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> ⚠️ **체크포인트**: Phase B 감리 통과 + WIP 커밋 후 시작.
> 마스터 플랜 섹션 8의 메타 패턴 추론 설계를 완전 구현한다.
> 1-4-1(외부 압력)과 1-4-2(상업적 동기)는 직접 감지 불가 → 다른 패턴의 조합으로 추론.
> **Phase C는 품질에 직접 영향을 주는 마지막 Phase.** 완료 후 종합 E2E 검증 진행.

### STEP 79. Claude.ai — 메타 패턴 추론 상세 설계

**[배경]** 마스터 플랜 섹션 8에 설계 프레임이 있으나, 구현 수준의 상세 설계가 필요하다.

**[설계 항목]**

1. **추론 규칙 데이터 소스**: `pattern_relations` 테이블의 `inferred_by` 관계
   - 현재 DB에 inferred_by 관계가 몇 건 존재하는지 확인 필요
   - 부족하면 Migration으로 추가 시드 INSERT 필요

2. **모듈 구조**: `backend/core/meta_pattern_inference.py` 신설
   - `check_meta_patterns(detections, article_text)` → MetaPatternResult
   - 입력: Sonnet Solo가 식별한 패턴 목록 + 기사 전문
   - 출력: 메타 패턴 추론 결과 (해당/미해당 + 확신도 + 근거 패턴)

3. **3단계 파이프라인**:
   ```
   Step 1: 규칙 기반 사전 필터링 (Deterministic)
     - pattern_relations에서 inferred_by 관계 동적 조회
     - 관련 지표 2개 미만 → 메타 패턴 추론 건너뜀
     - 관련 지표 2개 이상 → Step 2로 전달
   
   Step 2: LLM 기반 종합 판단 (Probabilistic)
     - Sonnet에 메타 패턴 추론 프롬프트 주입
     - 확신도(낮음/중간/높음) + 근거 생성
     - ⚠️ 추가 API 호출 1회 발생 (비용 고려)
   
   Step 3: 표현 수위 가드레일
     - 확신도에 따른 문구 강도 조절
     - 단정적 표현 금지
   ```

4. **리포트 통합**: report_generator.py 수정
   - 메타 패턴 추론 결과를 리포트 끝에 "구조적 문제 분석" 별도 섹션으로 추가
   - 직접 탐지된 패턴과 추론된 패턴의 구분을 시각적으로 명확히

5. **비용 최적화 옵션**:
   - Step 2의 LLM 호출을 리포트 생성 Sonnet 호출에 통합할 수 있는가?
   - 즉, 리포트 생성 프롬프트에 메타 패턴 추론 지시를 함께 넣으면 추가 호출 불필요
   - 트레이드오프: 프롬프트 복잡도 증가 vs API 비용 절감

6. **검증 전략**:
   - 골든 데이터셋 26건 중 메타 패턴 해당 케이스 식별 필요
   - 1-4 독립성 대분류: A2-13(구조적 상업적 동기), B-15(광고성 정보 전달)
   - 추가로 다른 TP 중 메타 패턴 의심 케이스가 있는지 레이블 재확인

**[감리 판정 기준]**
- ✅ 3단계 구조가 마스터 플랜 섹션 8과 일치하는가
- ✅ 추론 규칙이 코드에 하드코딩되지 않고 DB 동적 조회인가
- ✅ 표현 수위 가드레일이 명확한가 (단정 금지)
- ✅ 비용 최적화 옵션이 검토되었는가
- ✅ 검증 가능한 테스트 케이스가 식별되었는가

**[Gamnamu 판단 요청]**
- Step 2 LLM 호출: 별도 호출 vs 리포트 생성에 통합?
- 메타 패턴 추론 결과를 리포트의 어느 위치에 배치할지?

---

### STEP 80. Gamnamu — 메타 패턴 설계 승인

**[체크리스트]**
- [ ] 3단계 추론 구조 → 승인/수정
- [ ] Step 2 LLM 호출 방식 → 결정 (별도/통합)
- [ ] 리포트 배치 위치 → 결정
- [ ] 검증 케이스 → 확인

**[결과]** __ (Gamnamu 기입)

---

### STEP 81. Claude Code CLI — 메타 패턴 추론 DB 시드 확인 + 모듈 구현

**[프롬프트 — Claude Code CLI에게]**

```
/effort max

⚠️ 이 STEP 81P)만 수행하라. 완료 후 결과를 보고하고 STOP.

M6 Phase C — 메타 패턴 추론 구현.

■ 사전 숙지
1. docs/SESSION_CONTEXT (최신 버전)
2. docs/CR_CHECK_M6_PLAYBOOK.md — STEP 81
3. docs/DB_AND_RAG_MASTER_PLAN_v4.0.md — 섹션 8 (메타 패턴 추론)
4. backend/core/pipeline.py
5. backend/core/report_generator.py
6. CLAUDE.md

■ 사전 확인: pattern_relations 테이블의 inferred_by 관계 현황

supabase start 후 로컬 DB에서:
SELECT * FROM pattern_relations WHERE relation_type = 'inferred_by';

결과를 보고하라. inferred_by 관계가 부족하면 Migration 파일로 추가 INSERT.
마스터 플랜 섹션 8.2의 추론 규칙에 따라:
- 1-4-1(외부 압력): 필수(1-1-1, 1-1-2) + 보강(1-3-2, 1-3-1)
- 1-4-2(상업적 동기): 필수(1-7-3, 1-7-4) + 보강(1-1-1, 1-8-2, 1-6-1)

■ 작업: meta_pattern_inference.py 구현

backend/core/meta_pattern_inference.py를 생성하라.
STEP 80에서 확정된 설계를 따른다.

1. DB에서 inferred_by 관계 동적 조회 (하드코딩 금지)
2. 규칙 기반 사전 필터링 (관련 지표 카운트)
3. LLM 종합 판단 (STEP 80 결정에 따라 별도/통합)
4. 표현 수위 가드레일 (확신도별 문구 강도)
5. 결과 데이터 구조: MetaPatternResult

■ 통합: pipeline.py + report_generator.py

1. pipeline.py의 analyze_article()에 메타 패턴 추론 단계 추가
   - 위치: 패턴 매칭 완료 후, 리포트 생성 전 (또는 STEP 80 결정에 따라)
2. report_generator.py의 리포트 프롬프트에 메타 패턴 섹션 추가
   - "구조적 문제 분석" 별도 섹션

■ 주의사항
- inferred_by 관계 INSERT 시 반드시 Migration 파일로
- 메타 패턴 추론이 없어도(관련 지표 < 2개) 파이프라인이 정상 동작해야 함
- 추론 결과의 확신도는 반드시 표현 수위 가드레일을 거쳐야 함
```

**[완료 기준]**
- [ ] inferred_by 관계 현황 보고됨
- [ ] 부족한 관계가 있으면 Migration 파일로 추가됨
- [ ] `backend/core/meta_pattern_inference.py` 생성됨
- [ ] pipeline.py에 통합됨
- [ ] 메타 패턴 미해당 케이스에서도 파이프라인 정상 동작 확인

---

### STEP 82. Claude.ai — 메타 패턴 추론 1차 감리

**[감리 대상]** meta_pattern_inference.py + pipeline.py 변경분 + report_generator.py 변경분

**[체크리스트]**

추론 로직:
- [ ] inferred_by 관계가 DB에서 동적 조회되는가 (하드코딩 없음)
- [ ] 사전 필터링 로직이 마스터 플랜 섹션 8.2와 일치하는가
- [ ] "필수 1개 + 보강 1개 이상" 트리거 조건이 정확한가
- [ ] LLM 프롬프트가 메타 패턴의 본질(간접 추론)을 정확히 전달하는가

가드레일:
- [ ] 확신도별 문구 강도가 마스터 플랜 섹션 8.1 Step 3과 일치하는가
- [ ] 단정적 표현("외부 압력이 있었다") 금지가 코드 레벨에서 강제되는가

통합:
- [ ] 파이프라인 흐름에서 메타 패턴이 자연스러운 위치에 있는가
- [ ] 메타 패턴 미해당 시 graceful하게 건너뛰는가
- [ ] 리포트의 "구조적 문제 분석" 섹션이 직접 탐지와 시각적으로 구분되는가

**[판정]** ✅ PASS / ❌ FAIL

---

### STEP 83. Claude Code CLI — 메타 패턴 3건 선별 테스트

**[프롬프트 — Claude Code CLI에게]**

```
메타 패턴 추론 감리 통과. 3건 선별 테스트를 실행한다.

⚠️ 이 STEP 83P)만 수행하라. 결과를 보고하고 STOP.

■ 실행

SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids A2-13,B-15,C2-07

테스트 대상:
- A2-13 (TP, 1-4 독립성): 메타 패턴(1-4-2 상업적 동기) 해당 예상 → 추론 발동 확인
- B-15 (TP, 1-4 독립성): 메타 패턴 해당 예상 → 추론 발동 확인
- C2-07 (TN): 메타 패턴 추론이 발동하지 않아야 함 → 건너뜀 확인

■ 확인 사항 (각 건별 보고)
1. 메타 패턴 사전 필터링 결과 (관련 지표 수, 트리거 여부)
2. LLM 추론 결과 (발동된 경우: 확신도, 근거 패턴)
3. 리포트에 "구조적 문제 분석" 섹션 존재 여부
4. 표현 수위가 가드레일 내인지 확인
```

**[완료 기준]**
- [ ] A2-13: 메타 패턴 추론 발동 + 적절한 표현 수위
- [ ] B-15: 메타 패턴 추론 발동 + 적절한 표현 수위
- [ ] C2-07: 메타 패턴 추론 미발동 (건너뜀)

---

### STEP 84. Claude.ai — 메타 패턴 테스트 분석 + 판정

**[분석 대상]** STEP 83의 3건 테스트 결과

**[판정 기준]**

| 케이스 | 기대 | 판정 |
|--------|------|------|
| A2-13 (TP, 1-4) | 메타 패턴 추론 발동 | ✅ 발동 / ❌ 미발동 |
| B-15 (TP, 1-4) | 메타 패턴 추론 발동 | ✅ 발동 / ❌ 미발동 |
| C2-07 (TN) | 메타 패턴 추론 미발동 | ✅ 미발동 / ❌ 오발동 |

추가 분석:
- 표현 수위가 적절한가 (과소 vs 과다)
- 추론 근거가 논리적인가
- 리포트 전체 품질이 M5 대비 유지/개선되는가

**[분기]**
- 3건 모두 기대 충족 → 종합 E2E 검증(STEP 86)으로 진행
- 1~2건 미충족 → STEP 80으로 복귀 (추론 규칙 또는 프롬프트 조정)
- TN 오발동 → STEP 106(감리 협의)으로

**[판정]** __ (분석 후 기입)

**[감리 통과 시]** Phase C 독립 감리(STEP 85)로 진행. ✦ `feature/m6-wip` 브랜치에 WIP 커밋 (롤백 포인트 확보). 최종 깃 커밋은 종합 E2E(STEP 86) 통과 후 Phase별 분리 커밋 시 수행.

---


---

### STEP 85. Antigravity/Manus — Phase C 독립 감리 (메타 패턴 추론)

**[감리 범위]** Phase C 전체 — meta_pattern_inference.py + pipeline.py 통합 + report_generator.py 변경분

**[감리 배경]**
메타 패턴 추론은 M6에서 완전히 새로 구현하는 기능이다.
직접 탐지가 아닌 간접 추론이므로, 오발동(양질 기사에 "외부 압력 의심" 붙이기)의 위험이
다른 기능보다 구조적으로 높다. Claude.ai 감리만으로는 추론 로직의 논리적 결함을
충분히 잡아내기 어렵다는 판단 하에, 종합 E2E 진입 전 독립 검증을 수행한다.

**[감리 축]**

축 1 — 추론 로직 정합성:
- pattern_relations 테이블의 inferred_by 관계가 마스터 플랜 섹션 8.2와 일치하는가
- 사전 필터링 조건("필수 1개 + 보강 1개 이상")이 코드에 정확히 반영되었는가
- inferred_by 관계가 DB 동적 조회인가 (하드코딩이면 CRITICAL)
- LLM 프롬프트가 메타 패턴의 본질(간접 추론, 확정 불가)을 정확히 전달하는가

축 2 — 표현 수위 가드레일:
- 확신도별 문구 강도가 마스터 플랜 섹션 8.1 Step 3과 일치하는가
- 단정적 표현 차단이 코드 레벨에서 강제되는가
  (예: "외부 압력이 있었다" → CRITICAL, "외부 압력의 가능성이 시사된다" → OK)
- 확신도 '낮음'일 때 리포트에서 충분히 약한 톤으로 표현되는가

축 3 — 안전한 비활성:
- 메타 패턴 해당 지표가 2개 미만인 기사에서 추론이 완전히 건너뛰어지는가
- 건너뛸 때 에러 없이 정상 파이프라인이 이어지는가
- TN 기사(C2-07 등)에서 STEP 83 테스트 결과가 실제로 미발동인지 독립 확인

축 4 — 리포트 통합:
- "구조적 문제 분석" 섹션이 직접 탐지 패턴과 시각적으로 구분되는가
- 3종 리포트 각각에서 메타 패턴 섹션이 적절한 톤으로 조정되는가
  (시민용은 이해하기 쉽게, 기자용은 전문적으로, 학생용은 교육적으로)

**[Antigravity 프롬프트]**

```
CR-Check M6 Phase C 독립 감리를 수행하라.

■ 역할
너는 독립 감리자다. 메타 패턴 추론 로직의 논리적 결함과 오발동 위험을 검증한다.

■ 감리 대상 파일 (로컬 경로)
1. /Users/gamnamu/Documents/cr-check/backend/core/meta_pattern_inference.py
2. /Users/gamnamu/Documents/cr-check/backend/core/pipeline.py (변경분)
3. /Users/gamnamu/Documents/cr-check/backend/core/report_generator.py (변경분)
4. /Users/gamnamu/Documents/cr-check/docs/DB_AND_RAG_MASTER_PLAN_v4.0.md — 섹션 8
5. /Users/gamnamu/Documents/cr-check/CLAUDE.md

■ 핵심 검증 질문
1. inferred_by 관계가 DB에서 동적 조회되는가? 코드에 하드코딩되어 있으면 CRITICAL.
2. 사전 필터링 조건이 "관련 지표 2개 이상"인가? 1개만으로도 발동하면 CRITICAL.
3. 단정적 표현이 가드레일에서 차단되는가?
4. 메타 패턴 미해당 기사에서 파이프라인이 에러 없이 정상 동작하는가?
5. STEP 83의 3건 테스트 결과(A2-13 발동, B-15 발동, C2-07 미발동)를 독립적으로 확인할 수 있는가?

■ 특별 주의
- 메타 패턴은 "가능성 시사"이지 "확정 판단"이 아니다.
  확정적 어조가 발견되면 CRITICAL로 판정하라.
- 3종 리포트 각각에서 메타 패턴 섹션의 톤이 대상 독자에 맞게 차별화되는지 확인하라.

■ 출력 형식
[CRITICAL] / [MAJOR] / [MINOR] / [PASS] + 근거
```

**[Manus 프롬프트]** (파일 첨부 방식)

```
CR-Check M6 Phase C 독립 감리 — 메타 패턴 추론.

첨부 파일: meta_pattern_inference.py, pipeline.py, report_generator.py,
         DB_AND_RAG_MASTER_PLAN_v4.0.md (섹션 8), CLAUDE.md

핵심 질문:
1. 추론 규칙이 DB 동적 조회인가, 하드코딩인가?
2. 단정적 표현이 가드레일에서 차단되는가?
3. TN 기사에서 오발동하지 않는가?
4. 메타 패턴 미해당 시 파이프라인이 정상 동작하는가?

[CRITICAL] / [MAJOR] / [MINOR] / [PASS]로 판정해줘.
```

**[판정]** ✅ PASS / ❌ FAIL (수정사항 명시)

**[FAIL 시]** 수정사항을 Claude.ai가 정리 → CLI 새 세션에서 수정 → Claude.ai 재감리.

**[감리 통과 시]** 종합 E2E 검증(STEP 86)으로 진행.


---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ★ 종합 E2E 검증 (품질 영향 작업 전부 완료 후)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> **원칙**: Phase A(파이프라인↔프론트 연결)와 Phase C(메타 패턴 추론) —
> 분석 도구의 품질에 영향을 주는 모든 작업이 완료된 상태에서, 한 번에 종합 평가한다.
> 불완전한 상태에서 중간 평가를 반복하지 않는다.
> 문제가 발견되면 Phase A와 C 중 어디서 누수가 발생했는지 추적할 수 있다.

### STEP 86. Gamnamu — 종합 E2E 품질 체감

**[시점]** Phase A(기술적 연결) + Phase B(코드 위생) + Phase C(메타 패턴) 모두 완료 후.

**[작업]** Gamnamu가 직접 로컬 환경에서 종합 테스트한다.

1. `localhost:3000` 접속
2. 실제 뉴스 기사 URL 3~4건 입력:
   - TP 성격 1건 (문제 기사)
   - TN 성격 1건 (양질 기사)
   - 메타 패턴 의심 1건 (독립성/상업적 동기 관련)
   - 경계 케이스 1건 (판단이 어려운 기사)
3. 리포트 화면 확인:
   - 리포트 내용이 읽기 좋은가
   - 규범 인용(결정론적 인용)이 자연스럽게 보이는가
   - overall_assessment가 유용한가
   - 메타 패턴 "구조적 문제 분석" 섹션이 자연스러운가
   - 레이아웃, 가독성, 정보 구조가 적절한가
4. 누수 추적: 문제 발견 시 Phase A(연결) 문제인지 Phase C(메타 패턴) 문제인지 식별

**[판정 기준]**
- ✅ "이 리포트를 시민에게 보여줄 수 있다" → ✦ WIP→main 분리 커밋 후 Phase D로 진행
  - `git checkout main`
  - Phase A 분리 커밋 → 기동 확인 → Phase B 분리 커밋 → 기동 확인 → Phase C 분리 커밋 → 기동 확인
  - `feature/m6-wip` 브랜치 삭제
- ⚠️ "프롬프트/리포트 형식 개선이 필요하다" → STEP 87로
- ❌ "파이프라인 자체에 구조적 문제가 있다" → STEP 106(감리 협의)으로

**[결과]** __ (Gamnamu 기입)

---

### STEP 87. (반복 가능) CC CLI + Claude.ai — 프롬프트/리포트 형식 개선

**[트리거]** STEP 86에서 개선이 필요하다고 판정된 경우.

**[작업 흐름]**
1. Gamnamu가 개선 요청사항을 구체적으로 기술 + 누수 원인 Phase 명시
2. CC CLI가 해당 Phase의 코드 수정 (프롬프트, 프론트엔드 UI 등)
3. Claude.ai가 수정분 감리
4. STEP 86로 복귀 (Gamnamu 재확인)

**[반복 상한]** 최대 3회. 3회 반복 후에도 만족스럽지 않으면 STEP 106(감리 협의)로.

**[주의]** 이 루프에서의 수정은 리포트 형식·프롬프트 문구·프론트엔드 UI에 한정한다.
파이프라인 구조(Sonnet Solo, CitationResolver 등)는 변경하지 않는다.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase D: Phase 1 아카이빙 통합
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> ⚠️ **체크포인트**: 종합 E2E 검증 PASS 후 시작.
> 마스터 플랜의 Phase 1에 해당. 분석 결과를 DB에 저장하고 공개 URL로 공유.
> 전 Phase 익명 운영. Auth 없음. 품질에 영향 없는 인프라 작업.

### STEP 88. Claude.ai — 아카이빙 스키마 + API 설계

**[배경]** 마스터 플랜 섹션 6.2 + Phase 1 설계를 구현 수준으로 구체화.

**[설계 항목]**

1. **articles 테이블**: 기사 메타데이터 (URL 중복 방지)
   ```sql
   CREATE TABLE public.articles (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     url TEXT NOT NULL UNIQUE,
     title TEXT,
     source TEXT,          -- 매체명
     scraped_at TIMESTAMPTZ DEFAULT now(),
     article_hash TEXT,    -- 본문 해시 (변경 감지)
     created_at TIMESTAMPTZ DEFAULT now()
   );
   ```

2. **analysis_results 테이블**: 분석 결과 저장
   ```sql
   CREATE TABLE public.analysis_results (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     article_id UUID REFERENCES public.articles(id),
     report_text TEXT NOT NULL,
     overall_assessment TEXT,
     detections JSONB,         -- [{pattern_code, matched_text, reasoning, severity}]
     meta_patterns JSONB,      -- 메타 패턴 추론 결과
     model_version TEXT,       -- 'sonnet-solo-v1'
     pipeline_version TEXT,    -- 'M6'
     embedding_tokens INT,
     sonnet_input_tokens INT,
     sonnet_output_tokens INT,
     total_seconds FLOAT,
     created_at TIMESTAMPTZ DEFAULT now()
   );
   ```

3. **analysis_ethics_snapshot 활성화**: 이미 스키마 존재. CitationResolver가 cite 태그 파싱 시 실제 스냅샷 INSERT 로직 추가.

4. **API 엔드포인트**:
   - `POST /analyze`: 기존 + DB 저장 + 결과 ID 반환
   - `GET /report/{id}`: 공개 URL로 리포트 조회
   - `GET /report/{id}/json`: API용 JSON 응답

5. **프론트엔드**: `/report/{id}` 페이지 추가 (공유 가능한 퍼머링크)

**[설계 원칙]**
- UUID 기반 ID (순차 ID는 열거 공격 가능)
- 기사 본문은 DB에 저장하지 않음 (저작권 원칙)
- 익명 운영: user_id 없음
- 동일 URL 재분석 시: 새 analysis_results 레코드 생성 (이력 보존)

**[감리 판정 기준]**
- ✅ 스키마가 마스터 플랜 섹션 6.2와 일치하는가
- ✅ UUID 기반 공개 URL이 열거 공격에 안전한가
- ✅ 기사 본문 미저장 원칙이 지켜지는가
- ✅ analysis_ethics_snapshot 연동이 설계에 포함되었는가

**[Gamnamu 판단 요청]** 스키마 승인/수정

---

### STEP 89. Gamnamu — 아카이빙 설계 승인

**[체크리스트]**
- [ ] articles + analysis_results 스키마 → 승인/수정
- [ ] 공개 URL 형식 → 확인 (`/report/{uuid}`)
- [ ] 동일 URL 재분석 정책 → 확인

**[결과]** __ (Gamnamu 기입)

---

### STEP 90. Claude Code CLI — 아카이빙 Migration + API 구현

**[프롬프트 — Claude Code CLI에게]**

```
/effort max

⚠️ 이 STEP 90P)만 수행하라. 완료 후 결과를 보고하고 STOP.

M6 Phase D — 아카이빙 통합.

■ 사전 숙지
1. docs/SESSION_CONTEXT (최신 버전)
2. docs/CR_CHECK_M6_PLAYBOOK.md — STEP 90
3. docs/DB_AND_RAG_MASTER_PLAN_v4.0.md — 섹션 6.2
4. supabase/migrations/ — 기존 Migration 파일 확인
5. CLAUDE.md

■ 작업 1: Migration 파일 생성

supabase/migrations/ 에 새 SQL 파일 생성:
- articles 테이블
- analysis_results 테이블 (STEP 88 확정 스키마)
- analysis_ethics_snapshot이 이미 존재하면 확인만, 없으면 생성

supabase start → supabase db reset으로 검증.

■ 작업 2: 백엔드 API

1. main.py의 /analyze 엔드포인트 수정:
   - 분석 완료 후 articles 테이블에 기사 메타 upsert
   - analysis_results 테이블에 결과 INSERT
   - 응답에 result_id(UUID) 포함
2. GET /report/{id} 엔드포인트 추가:
   - analysis_results에서 조회
   - 없으면 404
3. CitationResolver에서 cite 태그 파싱 시 analysis_ethics_snapshot INSERT 로직 추가

■ 작업 3: supabase start 후 E2E 테스트

1. /analyze로 기사 분석 → DB 저장 확인
2. /report/{id}로 조회 → 저장된 리포트 반환 확인
3. analysis_ethics_snapshot에 스냅샷 저장 확인

■ 주의사항
- Migration 파일 이름: 날짜+시퀀스 형식 (기존 패턴 따를 것)
- Supabase MCP로 직접 스키마 변경 금지
- 기사 본문은 DB에 저장하지 않음
```

**[완료 기준]**
- [ ] Migration 파일 생성 + supabase db reset 성공
- [ ] /analyze → DB 저장 확인
- [ ] /report/{id} → 조회 성공
- [ ] analysis_ethics_snapshot 저장 확인

---

### STEP 91. Claude.ai — 아카이빙 1차 감리

**[감리 대상]** Migration SQL + main.py 변경분 + CitationResolver 변경분

**[체크리스트]**

스키마:
- [ ] articles 테이블 스키마가 설계와 일치하는가
- [ ] analysis_results 스키마가 설계와 일치하는가
- [ ] UUID가 gen_random_uuid()로 생성되는가
- [ ] articles.url에 UNIQUE 제약이 있는가
- [ ] analysis_results.article_id FK가 올바른가

API:
- [ ] /analyze가 DB 저장 후 result_id를 응답에 포함하는가
- [ ] /report/{id}가 404를 올바르게 반환하는가
- [ ] SQL injection 방지가 되어 있는가 (parameterized query)

스냅샷:
- [ ] analysis_ethics_snapshot INSERT가 CitationResolver의 올바른 시점에 있는가
- [ ] Sonnet이 실제로 인용한 규범만 스냅샷되는가 (get_ethics_for_patterns 전체가 아님)

**[판정]** ✅ PASS / ❌ FAIL

---

### STEP 92. Claude Code CLI — 프론트엔드 /report/{id} 페이지

**[프롬프트 — Claude Code CLI에게]**

```
⚠️ 이 STEP 92P)만 수행하라. 완료 후 결과를 보고하고 STOP.

■ 작업: /report/{id} 공유 페이지 구현

1. frontend/app/report/[id]/page.tsx 생성
2. GET /report/{id}로 데이터 fetch
3. 리포트 렌더링 (Phase A에서 구현한 ResultViewer 재사용)
4. 공유 메타태그 (og:title, og:description) 추가
5. 리포트가 없을 때 404 페이지 처리
6. 로컬 테스트: /analyze로 분석 → 반환된 result_id로 /report/{id} 접근 확인
```

**[완료 기준]**
- [ ] /report/{uuid} 페이지가 정상 렌더링됨
- [ ] 리포트 내용이 /analyze 결과와 동일함
- [ ] 404 처리가 동작함
- [ ] og 메타태그가 포함됨

---

### STEP 93. Claude.ai — 아카이빙 E2E 감리

**[감리 대상]** Phase D 전체 (Migration + API + 프론트엔드)

**[체크리스트]**
- [ ] /analyze → DB 저장 → /report/{id} 조회의 E2E 흐름이 완전한가
- [ ] 프론트엔드 /report/{id} 페이지가 공유 가능한 형태인가
- [ ] og 메타태그가 적절한가
- [ ] 동일 URL 재분석 시 기존 articles 레코드를 재사용하고 새 analysis_results를 생성하는가
- [ ] 보안: UUID 추측 불가, 개인정보 미포함

**[판정]** ✅ PASS / ❌ FAIL

**[감리 통과 시 Gamnamu 액션]** 깃 커밋: `git add -A && git commit -m "M6 Phase D: 아카이빙 통합 (articles + analysis_results + /report/{id})"`

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase E: 클라우드 배포
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> ⚠️ **체크포인트**: Phase D 아카이빙 감리 통과 + 깃 커밋 후 시작.
> Railway(BE) + Vercel(FE) 배포. Supabase 리모트 DB 연결.
> 품질에 영향 없는 인프라 작업. "배를 띄우는" Phase.

### STEP 94. Claude.ai — 배포 체크리스트 설계

**[설계 항목]**

1. **Railway 백엔드 배포**:
   - Dockerfile 또는 nixpacks 설정
   - 환경변수: ANTHROPIC_API_KEY, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY
   - 포트: 8000
   - 헬스체크: /health
   - 로그 설정

2. **Vercel 프론트엔드 배포**:
   - next.config.js 환경변수: NEXT_PUBLIC_API_URL (Railway URL)
   - 빌드 설정 확인
   - CORS: Railway에서 Vercel 도메인 허용

3. **Supabase 리모트**:
   - 로컬 Migration을 리모트에 push: `supabase db push`
   - ⚠️ CLAUDE.md Deny List에 `supabase db push`가 있으므로 Gamnamu 직접 실행
   - 리모트 DB 연결 문자열 확인
   - RLS(Row Level Security) 설정: 현재 익명 운영이므로 최소 설정

4. **도메인**:
   - Vercel 기본 도메인 (cr-check.vercel.app) 사용
   - 커스텀 도메인은 추후

5. **배포 전 최종 확인**:
   - [ ] 모든 환경변수 목록
   - [ ] CORS 허용 도메인 목록
   - [ ] rate limiting 필요성 검토 (API 남용 방지)
   - [ ] 에러 모니터링 (Railway 로그)

**[Gamnamu 판단 요청]**
- rate limiting 적용 여부 (초기에는 없이 시작?)
- Supabase 리모트 프로젝트 생성 여부 (이미 있는지?)

---

### STEP 95. Gamnamu — 배포 설계 승인 + Supabase 리모트 준비

**[체크리스트]**
- [ ] Railway 배포 설정 → 승인
- [ ] Vercel 배포 설정 → 승인
- [ ] Supabase 리모트 → 준비 완료/생성 필요
- [ ] rate limiting → 결정
- [ ] `supabase db push` → Gamnamu 직접 실행 (Deny List 항목)

**[결과]** __ (Gamnamu 기입)

---

### STEP 96. Claude Code CLI — 배포 준비 (Dockerfile, 환경변수, CORS)

**[프롬프트 — Claude Code CLI에게]**

```
/effort max

⚠️ 이 STEP 96P)만 수행하라. 완료 후 결과를 보고하고 STOP.

M6 Phase E — 클라우드 배포 준비.

■ 사전 숙지
1. docs/CR_CHECK_M6_PLAYBOOK.md — STEP 96
2. CLAUDE.md — 배포 설정
3. DEPLOYMENT_GUIDE.md — 기존 가이드 (있다면)

■ 작업 1: Railway 백엔드 배포 준비

1. Dockerfile 또는 railway.json 생성/수정
2. requirements.txt 최신화
3. 환경변수 설정 가이드 작성 (STEP 95 결정 반영)
4. /health 엔드포인트가 200 반환 확인

■ 작업 2: Vercel 프론트엔드 배포 준비

1. next.config.js에 NEXT_PUBLIC_API_URL 환경변수 설정
2. vercel.json 생성/수정 (필요 시)
3. 빌드 성공 확인: npm run build

■ 작업 3: CORS 설정 최종화

main.py의 allow_origins에 Railway/Vercel 도메인 추가

■ 작업 4: DEPLOYMENT_GUIDE.md 갱신

배포 절차를 단계별로 문서화 (Gamnamu가 직접 실행할 수 있도록)

■ 주의사항
- supabase db push는 실행하지 마라 (Deny List). Gamnamu가 직접 실행.
- git commit/push도 실행하지 마라 (Deny List). 코드 준비만.
- API 키를 코드에 포함하지 마라.
```

**[완료 기준]**
- [ ] Dockerfile/railway.json 준비됨
- [ ] next.config.js 환경변수 설정됨
- [ ] CORS 설정 완료
- [ ] `npm run build` 성공
- [ ] DEPLOYMENT_GUIDE.md 갱신됨

---

### STEP 97. Gamnamu — 배포 실행 + 프로덕션 E2E 검증

**[시점]** STEP 96 완료 후. Gamnamu가 직접 배포한다.

**[작업]**
1. `supabase db push` (리모트 Migration 반영)
2. `git add/commit/push` → Railway 자동 배포 트리거
3. Vercel 배포 (GitHub 연동 또는 수동)
4. 프로덕션 URL에서 E2E 테스트:
   - 기사 URL 입력 → 분석 → 리포트 확인
   - /report/{id} 공유 URL 접근 확인
   - /health 200 확인

**[판정 기준]**
- ✅ 프로덕션에서 E2E 정상 동작 → Phase F로
- ❌ 배포 실패 또는 E2E 실패 → STEP 96로 복귀

**[결과]** __ (Gamnamu 기입)

**[배포 성공 시 Gamnamu 액션]** 깃 커밋 (배포 설정 변경분 포함): `git add -A && git commit -m "M6 Phase E: Railway + Vercel 프로덕션 배포"`

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase F: Reserved Test Set 검증 + 종합 감리
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> ⚠️ **체크포인트**: Phase E 배포 완료 후 시작.
> "검증된 도구"를 지향하므로 배포 후 Reserved Test Set으로 일반화 성능 확인.

### STEP 98. Claude.ai — Reserved Test Set 선별 전략

**[배경]** Reserved Test Set 73건은 개발 과정에서 참조하지 않은 독립 데이터.
이 중 일부를 선별하여 M5 파이프라인의 일반화 성능을 검증한다.

**[설계 포인트]**

1. **선별 수**: 15~20건 (비용 ~$1.50, 통계적 신뢰도와 비용의 균형)
2. **선별 기준**:
   - 8개 대분류에서 각 1~2건 (다양성)
   - TN 후보 3~4건 포함
   - 난이도 분포: easy 5건 / medium 7건 / hard 5건
3. **레이블링**: 선별된 건에 대해 기대 패턴 레이블 작성 필요
   - ⚠️ 이 레이블링은 검증 전에 완료해야 함 (결과 보고 편향 방지)
4. **비교 기준선**: Dev Set 26건의 M5 벤치마크 결과

**[감리 판정 기준]**
- ✅ 대분류별 다양성이 확보되었는가
- ✅ TN이 충분히 포함되었는가
- ✅ 레이블링이 검증 실행 전에 완료되었는가

**[Gamnamu 판단 요청]** 선별 수 + 레이블링 방식 확인

---

### STEP 99. Gamnamu — Reserved Test Set 선별 승인

**[체크리스트]**
- [ ] 선별 건수 → 확인
- [ ] 선별 기준 → 승인
- [ ] 레이블링 방식 → 확인 (누가, 어떻게)

**[결과]** __ (Gamnamu 기입)

---

### STEP 100. Claude Code CLI — Reserved Test Set 벤치마크 실행

**[프롬프트 — Claude Code CLI에게]**

```
⚠️ 이 STEP 100P)만 수행하라. 결과를 보고하고 STOP.

■ 작업: Reserved Test Set 벤치마크

1. STEP 99에서 확정된 건들의 기사 전문을 article_texts/에서 읽기
2. 벤치마크 실행 (프로덕션 환경 또는 로컬 — STEP 99 결정에 따라)
3. 결과 저장: docs/M6_RESERVED_TEST_RESULTS.md

■ 결과 포맷
- 건별: 기대 패턴 vs 실제 탐지, FR, FP, Category Match
- 전체: TN FP Rate, Category Recall, Final Recall, Final Precision
- Dev Set(26건) 대비 비교표

■ 주의사항
- Reserved Test Set의 기사 텍스트는 이 검증 이후에도 개발에 재사용하지 않는다
- 레이블은 STEP 99에서 사전 작성된 것을 사용 (결과 보고 편향 방지)
```

**[완료 기준]**
- [ ] 선별 건수 전체 실행 완료
- [ ] docs/M6_RESERVED_TEST_RESULTS.md 저장됨
- [ ] Dev Set 대비 비교표 포함

---

### STEP 101. Claude.ai — Reserved Test Set 결과 분석

**[분석 대상]** docs/M6_RESERVED_TEST_RESULTS.md

**[분석 포인트]**

1. **일반화 성능**: Dev Set 대비 성능 격차
   - 5%p 이내 → 양호 (과적합 없음)
   - 5~15%p → 경미한 과적합 (few-shot 효과가 Dev Set에 집중)
   - 15%p 이상 → 심각한 과적합 (구조적 재검토 필요)

2. **대분류별 분석**: Dev Set에서 약했던 대분류가 Reserved에서도 약한가
3. **TN 성능**: Reserved TN에서의 FP Rate
4. **메타 패턴 추론**: Reserved Set에서 메타 패턴이 적절히 발동/미발동하는가

**[판정 기준]**
- ✅ 일반화 성능 격차 10%p 이내 + TN FP Rate 유지 → Phase F 완료
- ⚠️ 격차 10~15%p → 프롬프트 미세 조정 검토 (M7에서)
- ❌ 격차 15%p 이상 → STEP 106(감리 협의)

**[판정]** __ (분석 후 기입)

---

### STEP 102. Antigravity/Manus — M6 종합 독립 감리

**[감리 범위]** M6 전체 변경사항

**[감리 축]**

축 1 — 수직 정합성:
- 마스터 플랜 → CLAUDE.md → 코드 간 정합
- 메타 패턴 추론이 마스터 플랜 섹션 8과 일치하는가
- 아카이빙 스키마가 마스터 플랜 Phase 1과 일치하는가

축 2 — 수평 정합성:
- pipeline.py → meta_pattern_inference.py → report_generator.py → citation_resolver.py 간 데이터 흐름
- main.py ↔ 프론트엔드 간 API 계약

축 3 — 코드베이스 위생:
- 에러 핸들링 누락
- 보안 취약점 (SQL injection, CORS, API key 노출)
- deprecated 코드 상태

축 4 — 배포 안전성:
- 환경변수 관리
- 에러 모니터링
- 데이터 무결성 (Migration 적용 순서)

**[판정]** ✅ PASS / ❌ FAIL (수정사항 명시)

---

### STEP 103. (조건부) Claude Code CLI — 독립 감리 수정 반영

**[트리거]** STEP 102에서 CRITICAL 또는 MAJOR 발견 시.

**[작업]** 감리 결과의 수정 요청을 반영한다.
- CRITICAL: 즉시 수정
- MAJOR: 즉시 수정
- MINOR: M7로 이관 가능 (Gamnamu 판단)

**[완료 후]** Claude.ai가 수정 반영을 확인 (1차 재감리).

**[감리 통과 시 Gamnamu 액션]** 깃 커밋: `git add -A && git commit -m "M6 Phase F: 독립 감리 수정 반영"`

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase G: 마무리 + 인수인계
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 104. Claude Code CLI — SESSION_CONTEXT v19 갱신 + CLAUDE.md 갱신

**[작업]**
```
M6 완료. SESSION_CONTEXT를 v19로, CLAUDE.md를 최신 상태로 갱신하라.

⚠️ 이 STEP 104P)만 수행하라. 완료 후 결과를 보고하고 STOP.

■ SESSION_CONTEXT v18→v19 변경사항:
- M6 완료 상태 반영
- 메타 패턴 추론 구현 완료
- Phase 1 아카이빙 통합 완료
- 클라우드 배포 완료 (프로덕션 URL 기록)
- Reserved Test Set 검증 결과 요약
- M6에서 확립된 교훈 추가 (28~)
- M5.5 이관 사항 해소 내역
- 다음 작업: M7 (Phase 2 통계 대시보드 + 벡터 검색 개선 + ...)
- v18을 _archive_superseded/로 이동

■ CLAUDE.md 갱신:
- 현재 상태를 "M6 완료 → M7 준비"로 변경
- 프로덕션 URL 추가
- 파이프라인 흐름에 메타 패턴 추론 단계 추가
- M6 벤치마크 결과 기록
```

---

### STEP 105. Gamnamu — M6 최종 승인

**[체크리스트]**
- [ ] 종합 E2E에서 품질 체감 PASS (STEP 86)
- [ ] 코드베이스 위생이 해소되었는가 (Phase B)
- [ ] 메타 패턴 추론이 올바르게 작동하는가 (Phase C)
- [ ] 아카이빙(DB 저장 + 공개 URL)이 정상인가 (Phase D)
- [ ] 프로덕션 배포가 정상 동작하는가 (Phase E)
- [ ] Reserved Test Set 일반화 성능이 수용 가능한가 (Phase F)
- [ ] 독립 감리 수정사항이 반영되었는가 (STEP 103)
- [ ] SESSION_CONTEXT v19 + CLAUDE.md가 정확한가 (STEP 104)

**[판정]** ✅ M6 완료 승인 / ❌ 추가 작업 필요

**[최종 Gamnamu 액션]** 깃 커밋 + 태그: `git add -A && git commit -m "M6 완료" && git tag m6-complete`

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase X: (조건부) 감리 협의 + 조정
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 106. (조건부) 감리 협의 + 조정

**[트리거]**
- STEP 86(종합 E2E)에서 구조적 문제
- STEP 84(메타 패턴 테스트)에서 TN 오발동
- STEP 101(Reserved Test)에서 심각한 과적합
- STEP 102(독립 감리)에서 아키텍처 수준 문제

**[원칙]**
- 같은 세션에서 즉시 수정하지 않는다
- Claude.ai가 분석 소견 → Gamnamu 검토 → 조정 방향 합의 → CLI 새 세션에서 수정

**[조정 옵션]**

| 실패 영역 | 조정 방향 |
|----------|-----------|
| E2E 리포트 품질 | ① 리포트 프롬프트 구조 변경 ② 프론트엔드 렌더링 개선 ③ 결정론적 인용 형식 조정 |
| 메타 패턴 오발동 | ① 사전 필터링 임계값 조정 (관련 지표 2→3개) ② 표현 수위 가드레일 강화 ③ 특정 패턴 조합을 inferred_by에서 제거 |
| 일반화 성능 격차 | ① few-shot 예시 다양화 ② 패턴 description 보강 ③ 벡터 검색 임계값 조정 ④ M7에서 임베딩 모델 교체 검토 |
| 배포 문제 | ① 환경변수 재확인 ② Railway/Vercel 설정 조정 ③ Supabase 리모트 연결 디버깅 |

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 비상 시나리오 (Emergency Scenarios)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 비상 Q: main.py 교체 후 프론트엔드 호환성 전면 파손

**[상황]** 응답 스키마 변경으로 프론트엔드가 전혀 동작하지 않음
**[대응]**
1. 기존 AnalyzeResponse 형식을 유지하는 어댑터 레이어 삽입
2. pipeline 결과를 구 형식으로 변환하는 중간 함수
3. 프론트엔드 수정은 별도 STEP으로 분리
4. 최악: main.py에서 두 경로 모두 지원 (/analyze/v1, /analyze/v2)

### 비상 R: 메타 패턴 추론이 모든 기사에서 발동 (과잉 추론)

**[상황]** 사전 필터링 임계값이 너무 낮아 대부분의 기사에서 메타 패턴이 추론됨
**[대응]**
1. 관련 지표 임계값 상향 (2개 → 3개)
2. 필수 조건의 정의를 엄격화 (1-1-1 AND 1-1-2 둘 다 필요)
3. LLM 판단의 확신도 임계값 도입 (낮음 → 리포트에 미표시)
4. 극단적: 메타 패턴 추론을 opt-in 기능으로 전환 (기본 비활성)

### 비상 S: Railway 배포 후 API 비용 폭발

**[상황]** 외부에서 /analyze를 반복 호출하여 Anthropic API 비용이 급증
**[대응]**
1. rate limiting 즉시 적용 (IP 기반, 시간당 10회)
2. /analyze에 간단한 CAPTCHA 또는 딜레이 추가
3. 프론트엔드에서만 호출 가능하도록 CORS + Referer 검증 강화
4. 비용 모니터링 알림 설정 (Anthropic 대시보드)

### 비상 T: Supabase 리모트 Migration 실패

**[상황]** `supabase db push`에서 기존 데이터와 스키마 충돌
**[대응]**
1. 리모트 DB가 빈 상태인지 확인 (초기 배포면 충돌 없어야 함)
2. 충돌 시 Migration 파일 순서 확인
3. 수동 SQL 실행으로 우회 (Supabase 대시보드)
4. 최악: 리모트 프로젝트 재생성

### 비상 U: Reserved Test Set에서 Dev Set 대비 20%p+ 성능 격차

**[상황]** 심각한 과적합이 확인됨
**[대응]**
1. few-shot 예시의 "편향" 분석 — 특정 유형에 과도하게 최적화되었는가
2. 벡터 검색 CR이 Reserved Set에서도 50% 수준인지 확인 (검색 문제 vs 추론 문제)
3. 프롬프트의 TN 보호 문구가 새로운 유형의 양질 기사에도 적용되는지 확인
4. M7에서 Reserved Set 일부를 Dev Set에 편입하고 few-shot 교체 검토
5. 근본적 접근: 임베딩 모델 교체 (CR 천장 타파)

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 구조 요약
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
Phase A — 로컬 E2E 연결 (기술적 연결만, 품질 평가 없음)
├─ STEP 71: Claude.ai — main.py 교체 설계 (응답 스키마 재설계)
├─ STEP 72: Gamnamu — E2E 교체 설계 승인
├─ STEP 73: CC CLI — main.py 교체 + 프론트엔드 수정
├─ STEP 74: Claude.ai — main.py 교체 1차 감리 → ✦ WIP 커밋
└─ STEP 75: Antigravity/Manus — Phase A 독립 감리

Phase B — 코드베이스 위생 (품질 영향 없음)
├─ STEP 76: CC CLI — 벤치마크 Solo 리팩토링 + 전역 에러 핸들링
├─ STEP 77: Claude.ai — 코드 위생 1차 감리 → ✦ WIP 커밋
└─ STEP 78: (선택) CC CLI — 벡터 검색 async 병렬화

Phase C — 메타 패턴 추론 (품질 영향 있음, 마지막 품질 변경)
├─ STEP 79: Claude.ai — 메타 패턴 추론 상세 설계
├─ STEP 80: Gamnamu — 설계 승인
├─ STEP 81: CC CLI — DB 시드 확인 + 모듈 구현 + pipeline 통합
├─ STEP 82: Claude.ai — 1차 감리
├─ STEP 83: CC CLI — 3건 선별 테스트
├─ STEP 84: Claude.ai — 테스트 분석 + 판정 → ✦ WIP 커밋
└─ STEP 85: Antigravity/Manus — Phase C 독립 감리

★ 종합 E2E 검증 (품질 영향 작업 전부 완료 후)
├─ STEP 86: Gamnamu — 종합 E2E 품질 체감 (★ 핵심 게이트)
│           → PASS 시: WIP 이력을 Phase별 분리 커밋으로 정리하여 main 반영
└─ STEP 87: (반복) CC CLI + Claude.ai — 프롬프트/리포트 개선 루프

Phase D — Phase 1 아카이빙 통합 (품질 영향 없음)
├─ STEP 88: Claude.ai — 아카이빙 스키마 + API 설계
├─ STEP 89: Gamnamu — 설계 승인
├─ STEP 90: CC CLI — 아카이빙 Migration + API 구현
├─ STEP 91: Claude.ai — 아카이빙 1차 감리
├─ STEP 92: CC CLI — 프론트엔드 /report/{id} 페이지
└─ STEP 93: Claude.ai — 아카이빙 E2E 감리 → ✦ 깃 커밋

Phase E — 클라우드 배포 (배를 띄우는 Phase)
├─ STEP 94: Claude.ai — 배포 체크리스트 설계
├─ STEP 95: Gamnamu — 배포 설계 승인 + Supabase 리모트 준비
├─ STEP 96: CC CLI — 배포 준비 (Dockerfile, 환경변수, CORS)
└─ STEP 97: Gamnamu — 배포 실행 + 프로덕션 E2E 검증 → ✦ 깃 커밋

Phase F — Reserved Test Set 검증 + 종합 감리
├─ STEP 98: Claude.ai — Reserved Test Set 선별 전략
├─ STEP 99: Gamnamu — 선별 승인
├─ STEP 100: CC CLI — Reserved Test Set 벤치마크 실행
├─ STEP 101: Claude.ai — 결과 분석 + 일반화 성능 판정
├─ STEP 102: Antigravity/Manus — M6 종합 독립 감리
└─ STEP 103: (조건부) CC CLI — 독립 감리 수정 반영 → ✦ 깃 커밋

Phase G — 마무리
├─ STEP 104: CC CLI — SESSION_CONTEXT + CLAUDE.md 갱신
└─ STEP 105: Gamnamu — M6 최종 승인 → ✦ 깃 커밋 + 태그

Phase X — (조건부) 감리 협의
└─ STEP 106: (조건부) 감리 협의 + 조정
```

총 STEP: 36개 (조건부 포함)
- CC CLI: 10 STEP
- Claude.ai: 13 STEP (설계 + 감리)
- Gamnamu: 8 STEP (승인 + 판정 + 배포)
- Antigravity/Manus: 3 STEP (독립 감리 — Phase A, Phase C, 종합)
- 조건부: 2 STEP (반복 루프 + 감리 협의)

WIP 커밋 시점 (feature/m6-wip): Phase A(STEP 74), B(STEP 77), C(STEP 84) — 총 3회
최종 깃 커밋 시점: 종합 E2E 통과 후 Phase A+B+C 분리 커밋 3회 + Phase D(STEP 93), E(STEP 97), F(STEP 103), G(STEP 105) — 총 7회
E2E 검증 시점: STEP 86(종합, 로컬), STEP 97(프로덕션) — 총 2회
독립 감리 시점: STEP 75(Phase A), STEP 85(Phase C), STEP 102(종합) — 총 3회

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M5 대비 M6의 구조적 차이점
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 항목 | M5 | M6 |
|------|-----|-----|
| **핵심 산출물** | 재설계 프롬프트 + CitationResolver | E2E 통합 + 메타 패턴 + 아카이빙 + 배포 |
| **주요 작업** | 프롬프트 엔지니어링 | 시스템 통합 + 인프라 |
| **감리 대상** | 프롬프트 + 모듈 1개 | 파이프라인 전체 + DB + 프론트 + 배포 |
| **벤치마크** | Dev Set 26건 | Dev Set 26건 + Reserved Test Set 15~20건 |
| **배포** | 없음 (로컬만) | Railway + Vercel 프로덕션 배포 |
| **E2E 검증** | Phase A 끝(중간 평가) | Phase C 완료 후 1회(종합 평가) |
| **깃 커밋** | 비명시 | WIP 브랜치(A+B+C) + 종합 E2E 후 분리 커밋 + Phase별 커밋(D~G) = 7회 |
| **핵심 리스크** | Recall-Precision 트레이드오프 | 시스템 통합 복잡도 + 배포 안정성 |
| **비용** | ~$3 (벤치마크) | ~$5~8 (벤치마크 + Reserved + 배포) |

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M6 완료 기준 (Definition of Done)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- [ ] main.py가 pipeline.py(Sonnet Solo + CitationResolver) 기반으로 동작
- [ ] 벤치마크 Solo 리팩토링 + 전역 에러 핸들링 완료
- [ ] 메타 패턴 추론(1-4-1, 1-4-2) 구현 + 3건 테스트 통과
- [ ] 리포트에 "구조적 문제 분석" 섹션 정상 출력
- [ ] ★ 종합 E2E에서 Gamnamu가 품질 체감 PASS (STEP 86)
- [ ] articles + analysis_results DB 저장 정상 동작
- [ ] /report/{uuid} 공개 URL로 리포트 공유 가능
- [ ] analysis_ethics_snapshot 시점 스냅샷 저장 정상
- [ ] Railway(BE) + Vercel(FE) 프로덕션 배포 완료
- [ ] 프로덕션 E2E 정상 동작
- [ ] Reserved Test Set 15~20건 벤치마크 완료 + 일반화 성능 수용 가능
- [ ] Antigravity/Manus 종합 독립 감리 통과
- [ ] SESSION_CONTEXT v19 + CLAUDE.md 갱신
- [ ] 깃 커밋 7회 + m6-complete 태그
- [ ] Gamnamu 최종 승인

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M7 예고 (M6 완료 후)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

M7의 예상 범위 (M6 결과에 따라 조정 가능):

1. **Phase 2 통계 대시보드**: 분석 결과 집계 + 시각화 (마스터 플랜 Phase 2)
2. **벡터 검색 개선**: CR 50.8% 천장 타파 — 임베딩 모델 교체 또는 패턴 description 전면 재작성
3. **Phase 3 커뮤니티**: 익명 피드백 수집 (마스터 플랜 Phase 3)
4. **M6 Reserved Test Set 결과 기반 프롬프트 튜닝**: 일반화 성능 개선
5. **PDF 내보내기 재설계**: M6에서 주석 처리한 /export-pdf 재구현
6. **rate limiting + 모니터링**: 프로덕션 운영 안정화

---

*이 플레이북은 2026-03-30 Claude.ai가 초안으로 작성했다.*
*2026-03-31 v2 갱신: Phase A/C 독립 감리 2건 추가 (STEP 75, 85). STEP 번호 전면 재배정 (71~106).*
*2026-03-31 v4 갱신: WIP 브랜치 방식 도입 (feature/m6-wip), STEP 구조 요약을 본문과 정합.*
*M1~M5 플레이북의 삼각편대 감리 흐름과 STEP 구조를 동일하게 적용했다.*
*M5에서 확립된 프로세스 교훈(CLI 승인 게이트, 3건 테스트, 교차 검증, 독립 감리)을 전면 반영했다.*
*Gamnamu 피드백 반영: E2E 검증을 Phase C 완료 후 1회로 통합, WIP 브랜치로 롤백 포인트 확보.*
