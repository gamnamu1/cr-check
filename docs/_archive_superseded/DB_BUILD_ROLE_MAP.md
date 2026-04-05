# CR-Check DB 구축 — 역할 분담 맵

> **최종 수정**: 2026-03-25 (역할 재편: 코딩 실행 → Claude Code CLI, 감리 이중화)
> **참조 문서**: `DB_AND_RAG_MASTER_PLAN_v4.0.md`, `SESSION_CONTEXT_2026-03-25_v12.md`

---

## 참여 주체

| 주체 | 역할 | 핵심 책임 |
|------|------|-----------|
| **Gamnamu** | 전체 기획자 | 설계 의사결정, 최종 승인, 데이터 품질 판단 |
| **Claude Code CLI** | 코딩 실행자 | SQL 작성, 스크립트 구현, 파이프라인 코딩, supabase CLI 실행 |
| **Claude (claude.ai)** | 1차 감리자 | 설계 정합성, 아키텍처 리뷰, 매핑 합의 파트너 |
| **Antigravity (Gemini)** | 2차 더블체크 | 비-Anthropic 계열 독립 리뷰, MCP로 DB 조회 검증 |

---

## Week 0 — 사전 준비 ✅ 완료

### 작업 A: 추가 규범 6개 원문 수집 ✅ 완료

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Gamnamu** | 한국기자협회 사이트에서 6개 규범 전문 수집 |
| 2 | **Gamnamu** ↔ **Claude** | Code of Ethics 파일에 추가, 원문 대조 교정 |

### 작업 B: `ethics_codes_mapping.json` 작성 ✅ 완료

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude** | 14개 규범 394개 조항에 대한 tier/parent/domain 매핑 초안 제시, 분류 근거 분석 |
| 2 | **Gamnamu** | 조항별 합의, 경계 모호 케이스 최종 판단·승인 |
| 3 | **4개 AI 리뷰어** | 교차 검수 (Gemini, Manus, Perplexity, NotebookLM) |

**산출물**: `/Users/gamnamu/Documents/cr-check/docs/ethics_codes_mapping.json` (394개 엔트리 확정)

### 준비 4·5: Supabase + OpenAI API 환경 구축 ✅ 완료

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Gamnamu** (단독) | Supabase 프로젝트 생성 (`cr-check-db`, Seoul, pgvector v0.8.0) |
| 2 | **Gamnamu** (단독) | 환경변수 4개 `.env` 저장, OpenAI API 연결 테스트 통과 |

### 골든 데이터셋 구축 ✅ 완료

26건(TP 20 + TN 6) 확정. 레이블링 v3 완료. Data Leakage 점검·원문 아카이빙 완료.
앙상블 검증(5AI) 완료 → 마스터 플랜·실행 가이드에 4건 직접 반영.

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Gamnamu** ↔ **Claude** | 선별·레이블링·Data Leakage 점검·원문 아카이빙 |
| 2 | **5개 AI 리뷰어** | 앙상블 교차 검증 2회 (골든 데이터셋 + DB 구축 사전 검수) |

> **Week 0 사전 준비가 모두 완료되었으므로 Week 1 사각편대 질주 진입 가능.**

---

## Week 1 — 기반 구축 (사각편대 질주)

### M1: 전체 스키마 생성 (Day 1)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | `supabase/migrations/` 폴더에 Migration SQL 파일 생성 (마스터 플랜 섹션 6 기반) |
| 2 | **Claude.ai (1차 감리)** | SQL 정합성, 컬럼 누락, FK 순서, is_citable 반영 확인 |
| 3 | **Antigravity (2차 더블체크)** | Gemini 관점에서 독립 리뷰 |
| 4 | **Gamnamu** | 두 감리 결과 비교, 승인 |
| 5 | **Claude Code CLI** | `supabase start` → 로컬 테스트 → `supabase db push` → 클라우드 배포 |

### M2: 시드 데이터 입력 (Day 2)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | 패턴·규범 데이터 입력 스크립트 구현 (2-패스 삽입: NULL → code→id UPDATE) |
| 2 | **Claude.ai (1차 감리)** | 스크립트 리뷰 + 데이터 정확성 검증 |
| 3 | **Antigravity (2차 더블체크)** | 삽입 스크립트 독립 리뷰 + MCP로 DB 조회 확인 |
| 4 | **Gamnamu** | tier 분류 최종 확인 |

### 관계 데이터 구축 — Stage 1 (Day 3)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | 102개 패턴 임베딩 유사도 매트릭스 생성 |
| 2 | **Claude.ai** | LLM 기반 구조화된 관계 추출 (102개 패턴 전문 분석) |
| 3 | **Gamnamu** | 교집합(높은 확신) + 합집합(검수 대상) 수동 검수 → 30~40건 초기 관계 확보 |

### M3: 임베딩 생성 + 모델 벤치마크 (Day 4-5)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | 벤치마크 코드 구현 (OpenAI vs 대안 모델 Recall@10 비교) |
| 2 | **Claude.ai (1차 감리)** | 모델 성능 분석, threshold(0.5) 튜닝 검증 |
| 3 | **Antigravity (2차 더블체크)** | 벤치마크 결과 독립 검증 |
| 4 | **Gamnamu** | 최종 임베딩 모델 선택 결정 |

> **M3는 골든 데이터셋(Week 0 산출물) 기반으로 평가합니다.**

---

## Week 2 — Phase 0 완성 + Phase 1

### M4: 1.5회 RAG 파이프라인 구현 (Day 6-7)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | 벡터검색 → Haiku(패턴 확정) → 규범 정밀조회 → Sonnet(보고서) 파이프라인 코드 구현 |
| 2 | **Claude.ai (1차 감리)** | 흐름 정합성, 토큰 예산, 메타 패턴 라우팅 감리 |
| 3 | **Antigravity (2차 더블체크)** | 파이프라인 독립 리뷰 |

### M5: 결정론적 인용 + 메타 패턴 추론 (Day 8)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | CitationResolver(cite 태그 → DB 원문 치환) + 메타 패턴(1-4-1, 1-4-2) 하이브리드 추론 로직 |
| 2 | **Claude.ai (1차 감리)** | cite 태그 치환 정확성, 가드레일 검증 |
| 3 | **Antigravity (2차 더블체크)** | 인용 로직 독립 리뷰 |
| 4 | **Gamnamu** | 표현 수위 가드레일 최종 검토 ("의심됩니다" vs "있었다" 등) |

### M6: Phase 1 아카이빙 통합 + 배포 (Day 9-10)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | DatabaseManager + main.py 수정, 공개 URL 공유 기능, 통합 구현·배포 |
| 2 | **Claude.ai (1차 감리)** | 엔드투엔드 테스트 감리, 골든셋 기반 평가 |
| 3 | **Antigravity (2차 더블체크)** | 통합 리뷰 + 브라우저 에이전트로 UI 검증 |
| 4 | **Gamnamu** | 최종 승인·배포 결정 |

---

## Week 3 — Phase 2 (통계 대시보드)

### 통계 함수 + API + 대시보드 UI (Day 11-14)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | 분석 통계 집계 함수, API 엔드포인트, 프론트엔드 대시보드 풀스택 구현 |
| 2 | **Claude.ai (1차 감리)** | 코드 감리 |
| 3 | **Antigravity (2차 더블체크)** | 프론트엔드 UI 브라우저 테스트 |
| 4 | **Gamnamu** | UI/UX 검토·승인 |

---

## 역할 패턴 요약

### 단계별 주도권 이동

| 단계 | 주축 | 보조 | 비고 |
|------|------|------|------|
| **Week 0** (사전 준비) | Gamnamu ↔ Claude.ai | — | 코딩 불필요, 설계 의사결정 중심 |
| **Week 1** (기반 구축) | Claude Code CLI → Claude.ai/Antigravity | Gamnamu (검수·결정) | 사각편대: 실행→이중감리→승인 |
| **Week 2** (파이프라인) | Claude Code CLI → Claude.ai/Antigravity | Gamnamu (가드레일·배포) | 핵심 분기점에서 기획자 결정권 |
| **Week 3** (대시보드) | Claude Code CLI → Claude.ai/Antigravity | Gamnamu (UI/UX) | Antigravity 브라우저 테스트 활용 |

### Gamnamu의 핵심 의사결정 포인트

- ~~**작업 B**: ~160개 조항의 tier/parent 매핑 최종 합의~~ ✅ 완료 (394개 확정)
- ~~**골든 데이터셋**: 기사 선정 + expected 레이블 부여~~ ✅ 완료 (26건 확정, 앙상블 검증 2회 통과)
- **M3**: 임베딩 모델 최종 선택 (OpenAI vs 대안)
- **M5**: 메타 패턴 표현 수위 가드레일 검토
- **M6**: 배포 최종 승인

---

*이 문서는 `DB_AND_RAG_MASTER_PLAN_v4.0.md`의 섹션 14(실행 순서)를 참여 주체별 역할 관점에서 재구성한 것입니다.*
*마지막 업데이트: 2026-03-25 — 역할 재편(Claude Code CLI 코딩, Claude.ai 1차 감리, Antigravity 2차 더블체크), Week 0 전체 완료 반영*
