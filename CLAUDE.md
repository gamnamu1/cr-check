# CR-Check — Hybrid RAG 파이프라인

## 프로젝트 개요

AI 기반 한국 뉴스 기사 품질 분석 웹앱(CR-Check)의 Hybrid RAG 파이프라인. Supabase(PostgreSQL 15+, pgvector) + FastAPI + Next.js. M1\~M6 + Phase F\~G 완료. 프로덕션 가동 중 (Railway + Vercel + Supabase).

## 기술 스택

- Database: Supabase (PostgreSQL 15+, pgvector)
- Backend: FastAPI + httpx + supabase-py
- Frontend: Next.js 15 (App Router)
- 배포: Railway (BE) + Vercel (FE) — main push 시 자동 배포
- Phase 1 모델: claude-sonnet-4-5-20250929 (Sonnet Solo, Devil's Advocate CoT)
- Phase 2 모델: claude-sonnet-4-6 (3종 리포트 생성)
- 임베딩: OpenAI text-embedding-3-small (1536차원)

## 프로덕션 URL

- 백엔드: <https://cr-check-production.up.railway.app>
- 프런트엔드: <https://cr-check.vercel.app>
- 공유 URL: [https://cr-check.vercel.app/report/{share_id}](https://cr-check.vercel.app/report/%7Bshare_id%7D)

## 핵심 명령어

- Supabase 로컬: `supabase start` (Docker 필요)
- Supabase Studio: `http://localhost:54323`
- 로컬 DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- 벤치마크: `SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py`
- 선별 테스트: `SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids B-11 E-12 C2-07`

## 파이프라인 흐름

```
POST /analyze { url }
  ① URL 정규화 → DB 캐시 조회 → 히트 시 즉시 반환
  ② 스크래핑 → 청킹 → 벡터검색(OpenAI 임베딩, 힌트)
  → Phase 1: Sonnet 4.5 Solo (패턴 식별 + Devil's Advocate CoT, 패턴별 독립 평가)
  → 규범 조회(get_ethics_for_patterns RPC + REST fallback) [메타패턴 추론: 비활성화 확정]
  → Phase 2: Sonnet 4.6 (3종 리포트, 〔〕마커 자연 인용)
  ③ DB 저장 (articles UPSERT + analysis_results INSERT + share_id)

GET /report/{share_id}
  → PostgREST JOIN → Cache-Control: public, max-age=86400
```

## 리포트 설계 원칙 — 변경 시 Gamnamu 승인 필요

1. **3종 리포트 유지**: 시민용(comprehensive), 기자용(journalist), 학생용(student). 3종의 톤·깊이·관점 차이가 CR-Check의 핵심 가치.

2. **프런트엔드 보존**: ResultViewer 3종 탭, TXT 내보내기, SNS 공유, 기사 정보 카드. 추가는 허용하되 기존 요소의 제거·변경은 승인 필요.

3. **규범 인용 — 〔〕마커 방식**: cite 태그 폐기됨. 규범 조항명은 〔 〕로, 원문 인용은 ' '로. 롤업은 복수 위반이 상위 원칙으로 수렴하는 결정적 경우에만 선택적 적용.

4. **리포트 톤 보존**: 서술의 깊이, 논리적 연결, 건설적 피드백 톤 유지.

## 작업 방식 — CRITICAL

### ★★★ STEP 단위 실행 원칙 (최우선 규칙) ★★★

**STEP 하나를 완료하면 멈추고, 결과를 보고하고, 다음 지시를 기다려라.**

1. STEP **1개만** 수행한다.
2. 완료 즉시 **STOP**. 결과를 보고한다.
3. 다음 STEP이 자신에게 할당된 것이더라도 **Gamnamu의 명시적 진행 지시가 있을 때까지** 착수하지 않는다.
4. "이어서 다음 STEP도 진행하겠습니다" → **금지**.
5. 감리 STEP을 건너뛰고 다음 작업 STEP으로 넘어가는 것은 **절대 금지**.

### DB 작업 규칙

- Migration 파일은 `supabase/migrations/`에 SQL 파일로 생성
- 쓰기 작업은 반드시 Migration 파일로만 수행
- Supabase MCP나 직접 SQL로 스키마 변경 금지

### 코드 작업 규칙

- `backend/core/`가 활성 코드. `backend/analyzer.py`는 미사용.
- deprecated 코드(legacy 파일) 삭제 금지 — 비교용 보존
- 벤치마크 결과 파일 삭제 금지

## 설계 문서

문서역할`docs/SESSION_CONTEXT_2026-04-25_v39.md`세션 컨텍스트 (최신)`docs/PHASE_H_EXECUTION_PLAN_v1.0.md`Phase H 실행 기준 (SSoT)`docs/PIPELINE_IMPROVEMENT_PLAN_v1.1.md`파이프라인 개선 계획`docs/DB_AND_RAG_MASTER_PLAN_v4.0.md`마스터 플랜 참조`docs/current-criteria_v2_active.md`패턴 원문 (119개)`docs/Code of Ethics for the Press.md`윤리규범 원문`docs/ethics_codes_mapping.json`규범 매핑 (394개 코드)`docs/golden_dataset_final.json`골든 데이터셋 (26건, TP21+TN5)`docs/golden_dataset_labels.json`레이블링 (v38 기준 확정)

## 현재 상태: M6 + Phase F\~G 완료, Phase H 착수 직전

- M1\~M5: DB 구축, 시드 데이터, 벡터 검색, RAG 파이프라인, 프롬프트 최적화
- M6 Phase A\~E: 로컬 E2E, 코드 위생, 메타패턴, 아카이빙, 클라우드 배포
- Phase F\~G: Reserved Test Set 검증, 이진 게이트 제거 실험(R4\~R7), R5 고정
- 현재 프로덕션: R5 고정 (커밋 1795eb0, 이진 게이트 제거 + 패턴 독립 평가)
- 다음 작업: Phase H STEP 1 (38→119 패턴 코드 체계 표 생성)

### 핵심 아키텍처 결정

- 벡터 검색은 매처가 아닌 느슨한 필터 (threshold=0.2, 사전필터 역할만)
- Phase 1 모델 Sonnet 4.5 확정 (Sonnet 4.6 대비 28% 비용절감, A/B 검증)
- 〔〕브래킷 인용 방식 (cite 태그 후치환 폐기)
- 캐시 우선 정책: 동일 URL 재분석 시 DB에서 즉시 반환
- 이진 게이트 제거 확정 (R5, 패턴별 독립 평가)
- 메타패턴 추론 비활성화 확정 (inferred_by 0건, 데이터 없음)
- 규범 매핑 111건 (pattern_ethics_relations 프로덕션 기준)
- 임베딩 403건 (patterns 28 + ethics_codes 375)

## 접두어 규칙

- KJA 접두어 절대 금지 (구버전, 완전 폐기)
- 유효 접두어: JEC, JCE, JCP, PCE, PCP, DRG, EPG, HSD, IRG, MRG, PRG, SPG, SRE

## 역할 체계

- Claude Code CLI: 코딩 실행. STEP 1개 → 보고 → STOP.
- [Claude.ai](http://Claude.ai): 1차 감리 (설계 정합성, 아키텍처 리뷰)
- Antigravity/Manus: 독립 감리
- Gamnamu: 최종 승인, STEP 진행의 유일한 결정권자.

## Gotchas

- main 브랜치 push = 프로덕션 자동 배포. 반드시 PR 경유.
- Supabase Legacy JWT 키 사용 중. "Disable JWT-based API keys" 금지.
- GitHub PAT 만료일: 2026년 7월 (만료 전 갱신 필요)
- golden_dataset_final.json이 최신 (26건, TP21+TN5). 27건짜리는 구버전.
- backend/analyzer.py는 미사용. backend/core/가 활성.
- frontend App Router 사용 중. Pages Router 코드 생성 금지.
- Supabase 비밀번호에 특수문자 (#, /) 포함 시 connection string URL escape 필요.
- Railway 환경변수는 escape 불필요.
- RLS 전테이블 DISABLED (활성화 계획 미확정)
