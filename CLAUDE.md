# CR-Check — Hybrid RAG 파이프라인

## 프로젝트 개요
AI 기반 한국 뉴스 기사 품질 분석 웹앱(CR-Check)의 Hybrid RAG 파이프라인.
Supabase(PostgreSQL 15+, pgvector) + FastAPI + Next.js.
M1~M5 완료. M6(메타 패턴 추론 + Phase 1 아카이빙 통합 + 클라우드 배포) 준비 중.

## 기술 스택
- Database: Supabase (PostgreSQL 15+, pgvector)
- Backend: FastAPI + supabase-py
- Frontend: Next.js 15
- 배포: Railway (BE) + Vercel (FE) — M6에서 일괄 배포
- 패턴 식별 모델: claude-sonnet-4-6 (Sonnet Solo 1-Call, 게이트 없음)
- 리포트 생성 모델: claude-sonnet-4-20250514
- 임베딩: OpenAI text-embedding-3-small (1536차원)

## 핵심 명령어
- Supabase 로컬 시작: `supabase start` (Docker 필요)
- Supabase Studio: `http://localhost:54323`
- 로컬 DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- 벤치마크: `SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py`
- 선별 테스트: `SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids B-11 E-12 C2-07`
- 모델 오버라이드: `--model claude-opus-4-6`

## 리포트 설계 원칙 — 변경 시 Gamnamu 승인 필요

CR-Check의 DB 구축(394개 윤리규범 계층화, 벡터 검색, CitationResolver)은
기존 리포트의 품질을 유지하면서 규범 인용의 정확성을 높이기 위한 작업이다.
파이프라인이 바뀌더라도 사용자에게 보이는 결과물은 아래를 유지한다.

1. **3종 리포트 유지**: 시민용(comprehensive), 기자용(journalist), 학생용(student).
   단일 리포트로 통합하지 않는다. 3종의 톤·깊이·관점 차이가 CR-Check의 핵심 가치.

2. **프론트엔드 보존**: ResultViewer의 3종 탭, 디자인, 폰트, TXT 내보내기,
   SNS 공유, 기사 정보 카드, 윤리규범 하이라이팅을 그대로 유지한다.
   추가(예: 공유 URL 버튼)는 허용하되, 기존 요소의 제거·변경은 승인 필요.

3. **규범 인용 — 롤업 선택적 적용**:
   - 일반 위반: 해당 조항 하나만 인용. 매번 하위→상위를 나열하지 않는다.
   - 선택적 롤업: 복수 위반이 하나의 상위 원칙으로 수렴하는 결정적 경우에만,
     구체적 규범(하위) → 포괄적 원칙(상위) 순서로 계층 인용을 적용한다.
   - 롤업은 "패턴을 드러내는 분석적 도구"이지 "형식적 나열"이 아니다.
   (2026-03-21 PCP 매핑 세션에서 합의)

4. **리포트 톤 보존**: 서술의 깊이, 논리적 연결, 건설적 피드백의 톤을 유지한다.
   프롬프트 변경 시 기존 리포트 품질과 반드시 비교 검증할 것.

## 작업 방식 — CRITICAL

### ★★★ STEP 단위 실행 원칙 (최우선 규칙) ★★★

**플레이북의 실행 단위는 "Phase"가 아니라 "STEP"이다.**

Phase는 논리적 그룹핑일 뿐이다. 절대로 Phase를 하나의 작업 묶음으로 실행하지 마라.
반드시 STEP 하나를 완료하면 멈추고, 결과를 보고하고, 다음 지시를 기다려라.

**구체적 행동 규칙:**
1. 플레이북에서 자신에게 할당된 STEP **1개만** 수행한다.
2. 해당 STEP 완료 즉시 **STOP**. 결과를 보고한다.
3. 다음 STEP이 자신에게 할당된 것이더라도 **Gamnamu의 명시적 진행 지시가 있을 때까지** 착수하지 않는다.
4. "이어서 다음 STEP도 진행하겠습니다", "효율을 위해 함께 처리하겠습니다" → **금지**.
5. 감리 STEP(Claude.ai/Antigravity 감리)을 건너뛰고 다음 작업 STEP으로 넘어가는 것은 **절대 금지**.

**위반 시나리오 예시 (하지 말 것):**
- ❌ STEP 완료 후, 감리를 건너뛰고 다음 작업 STEP까지 진행
- ❌ "Phase 전체를 한 세션에서 완료하겠습니다"
- ❌ 감리 STEP에서 스스로 PASS를 판정하고 다음으로 넘어감

**올바른 흐름 예시:**
- ✅ STEP 완료 → "변경사항: [상세]. 다음은 감리 STEP입니다." → STOP
- ✅ Gamnamu가 "다음 STEP 진행해" → 해당 STEP만 수행 → 결과 보고 → STOP

### DB 작업 규칙
- MUST: Migration 파일은 `supabase/migrations/` 폴더에 SQL 파일로 생성
- MUST: 쓰기 작업은 반드시 Migration 파일로만 수행
- MUST NOT: Supabase MCP나 직접 SQL 실행으로 스키마를 변경하지 마세요
- MUST: 작업 완료 후 반드시 `supabase start`로 로컬 테스트 실행

### 코드 작업 규칙
- MUST: `main.py` import 경로를 먼저 추적해 활성 파일 확인 (`backend/core/`가 실제 활성)
- MUST: 벤치마크 실행 전 3건 선별 테스트 → 감리 승인 → 전체 실행 순서 준수
- MUST: CLI가 보고한 수치를 실제 파일과 반드시 교차 검증할 것

## 설계 문서 (Single Source of Truth)
- 세션 컨텍스트: @docs/SESSION_CONTEXT_2026-03-30_v19.md ← ★ 최신
- 마스터 플랜: @docs/DB_AND_RAG_MASTER_PLAN_v4.0.md
- 규범 매핑: @docs/ethics_codes_mapping.json (394개 코드)
- 골든 데이터셋: @docs/golden_dataset_final.json (26건, TP20+TN6)
- 레이블링: @docs/golden_dataset_labels.json (v3, weight 포함)
- M5 벤치마크: @docs/M5_BENCHMARK_RESULTS.md ← ★ 최신
- M4 벤치마크: @docs/M4_BENCHMARK_RESULTS_sonnet46.md (비교 기준선)
- M6 플레이북: @docs/CR_CHECK_M6_PLAYBOOK.md ← ★ M6 작업 절차 (STEP 71~104)
- 기사 전문: Golden_Data_Set_Pool/article_texts/ (26건, {id}_article.txt)

## 현재 상태: M5 완료 → M6 착수 대기 (플레이북 설계 완료)

### M5 완료 사항 (Sonnet Solo 아키텍처 확정)
- 파이프라인: chunker.py → pattern_matcher.py → report_generator.py → citation_resolver.py → pipeline.py
- 모델: Sonnet 4.6 (SONNET_MODEL 상수)
- 아키텍처: **Sonnet Solo 1-Call** (게이트 없음 + Devil's Advocate CoT)
- Few-shot: 9건 (TP 7 + TN 2), 심의자료 + 수상작 기반
- 결정론적 인용: CitationResolver (in-memory 매칭, 옵션 B)
  - cite 태그 → 「규범 제목: 원문 발췌」 치환
  - 환각 ref 제거 + 로그
- 벡터 검색: VECTOR_MATCH_COUNT=7, threshold=0.2
- 벤치마크 (M5): TN FP 33% | FR 36.7% | FP 30.4% | Cat R 54.2% | CR 50.8%

### M6 예정 작업 (★ 플레이북 확정: CR_CHECK_M6_PLAYBOOK.md)
0. **[최우선] Phase A — main.py 교체 → 로컬 E2E 연결**: /analyze 엔드포인트를 pipeline.py 기반으로 교체. localhost에서 기술적 기동 확인. (STEP 71~74)
1. Phase B — 코드베이스 위생: 벤치마크 Solo 리팩토링, 전역 에러 핸들링 (STEP 75~77)
2. Phase C — 메타 패턴 추론: 1-4-1, 1-4-2 완전 구현 (STEP 78~83)
3. ★ 종합 E2E 검증: 품질 영향 작업 전부 완료 후 한 번에 품질 체감 (STEP 84~85)
4. Phase D — Phase 1 아카이빙 통합 (STEP 86~91)
5. Phase E — 클라우드 배포 Railway + Vercel (STEP 92~95)
6. Phase F — Reserved Test Set 검증 + 독립 감리 (STEP 96~101)

## 코드 규칙
- Python: FastAPI + async/await, supabase-py 클라이언트
- SQL: PostgreSQL 15+ 문법, pgvector extension
- 임베딩: OpenAI text-embedding-3-small (1536차원)
- MUST NOT: ivfflat 인덱스 사용 금지 (262개 규모에서 sequential scan 우수)

## 접두어 주의 — IMPORTANT
- MUST NOT: KJA 접두어를 사용하지 마세요 (구버전, 완전 폐기됨)
- DB에는 다양한 접두어가 존재하며, 모두 정상이다:
  JEC: 언론윤리헌장 (Journalism Ethics Charter)
  JCE: 기자윤리강령 (Journalists' Code of Ethics)
  JCP: 기자윤리실천요강
  PCE: 신문윤리강령 (Press Code of Ethics)
  PCP: 신문윤리실천요강
  기타: DRG, EPG, HSD, IRG, MRG, PRG, SPG, SRE 등

## 역할 체계
- Claude Code CLI (당신): 코딩 실행. **STEP 1개 완료 → 보고 → STOP. 다음 STEP은 Gamnamu 지시 후에만 착수.** 감리 STEP을 건너뛰거나 자의적으로 다음 작업으로 넘어가는 것은 금지.
- Claude.ai: 1차 감리 (설계 정합성, 아키텍처 리뷰, 체크리스트 판정)
- Antigravity(Gemini)와 Manus: 2차 더블체크 (독립적 관점 리뷰)
- Gamnamu: 최종 승인. **STEP 진행 여부의 유일한 결정권자.**

## M1~M5에서 확립된 핵심 교훈
- 모델 교체만으로는 안 됨 (Opus에서도 FR 39%, TN FP 100%)
- 프롬프트 재설계(2단계+few-shot)는 TN 구분과 Precision에서 부분적 효과
- 벡터 검색 CR 50.8%가 구조적 천장 — 모델과 독립적
- Few-shot이 캘리브레이션의 핵심 (E-12 케이스가 실증)
- CLI 보고 vs 파일 교차 검증 필수 (M4에서 불일치 발견됨)
- 저널리즘 비평은 본질적으로 주관적 — CR-Check는 "관점을 제시하는 도구"
- CLI가 Phase 단위로 STEP을 묶어 감리를 건너뛴 사례 발생 → STEP 단위 실행 원칙 도입
- "도구는 촘촘하게, 판단은 사람에게" — 오탐(FP)은 사용자의 선의에 의한 판단에 맡김
- 게이트(이진 판정)의 구조적 한계 — 1-Call/2-Call 게이트 모두 TP/TN 트레이드오프 해결 불가
- Haiku의 분류 능력 한계 — 대분류 수준 판단조차 정반대로 판단
- Devil's Advocate CoT의 유효성 — TN 보호에 가장 효과적
- TN 보호 문구의 역효과 — few-shot 내부에서만 TN 보호를 기술하는 것이 정밀
- 결정론적 인용의 in-memory 원칙 — LLM에게 제공되지 않은 규범은 환각으로 처리
- 방어적 조건문의 중요성 — 빈 리스트는 falsy, 독립 감리에서 CRITICAL 발견
- 독립 감리(삼각편대)의 가치 — 1차 감리가 놓친 CRITICAL 버그를 2차 감리가 발견

## Gotchas
- golden_dataset_final.json이 최신 (26건). 27건짜리는 구버전 (_archive_superseded/)
- backend/analyzer.py는 미사용 파일. backend/core/analyzer.py가 활성
- Supabase Legacy JWT 키 사용 중. "Disable JWT-based API keys" 누르지 말 것
- GitHub PAT 만료일: 2026-04-16
- Reserved Test Set 73건은 참조 금지
- 벤치마크 결과 파일(M4_BENCHMARK_RESULTS*.md, M5_BENCHMARK_RESULTS.md) 삭제 금지
- Few-shot 예시 9건(TP 7 + TN 2)은 벤치마크 대상 포함 — 해당 케이스 성능 과대평가 가능성 유의
- deprecated 코드(1-Call, 2-Call) 삭제 금지 — 비교 실험용 보존
- JEC/JCE 접두어 불일치: DB 코드(JEC-1 등)와 문서 표기에 차이 존재 가능. M6에서 점검.
