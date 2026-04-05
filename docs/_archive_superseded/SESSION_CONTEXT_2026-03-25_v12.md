# 세션 컨텍스트 — 2026-03-25 v12

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 전환을 위한 **Week 0 사전 준비가 모두 완료**되었다.
골든 데이터셋 **26건(TP 20 + TN 6)** 확정, 레이블링·원문 아카이빙·Data Leakage 점검 완료.
**앙상블 검증(5AI 교차검수)** 완료 → 반영 4건을 마스터 플랜 v4.0 및 실행 가이드에 직접 반영 완료.
**Supabase 인프라** 세팅 완료 (.env, CLI, MCP 읽기 전용 연결).
다음 작업은 **Week 1 M1(전체 스키마 생성)** — Claude Code CLI가 코딩 실행, Claude.ai가 1차 감리, Antigravity(Gemini)가 2차 더블체크.

### v11→v12 변경 사항 (2026-03-25)

**앙상블 검증 완료 (DB 구축 사전 검수):**
- 5개 리뷰어(제미니, 마누스, 퍼플렉시티, 노트북LM, Claude Code CLI) 교차 검증
- 결과: 반영 4건, 보류 4건, 불채택 2건
- 검증 결과 파일: `docs/_reference/앙상블_검증_결과_{리뷰어}.md`

**마스터 플랜 v4.0 직접 수정 (4건 반영):**
1. **ivfflat 인덱스 제거** (5/5 합의): patterns·ethics_codes 양쪽의 ivfflat 인덱스 삭제. 262개 규모에서 sequential scan이 100% recall + 1ms 미만으로 우수. 1만 건 이상 확장 시 HNSW 도입 검토.
2. **`is_citable` 컬럼 추가** (5/5 합의): `ethics_codes` 테이블에 `BOOLEAN NOT NULL DEFAULT TRUE` 추가. 서문/부칙 등 인용 부적합 조항을 벡터 검색·규범 조회에서 필터링.
3. **`get_ethics_for_patterns()` 재귀 CTE 롤업** (2/5): 직접 관계 규범 + parent chain 상위 규범을 함께 반환. 최대 2-hop, 비용 미미. `is_citable` 필터도 함수 내 적용.
4. **KJA→JCE 접두어 수정**: 결정 F의 cite 예시에서 `<cite ref="KJA-3"/>` → `<cite ref="JCE-3"/>` 수정.

**실행 가이드 수정 (1건):**
5. **시드 스크립트 2-패스 삽입 패턴**: JSON의 `parent_code_id`가 문자열("JEC-8")이지만 DB는 BIGINT. 1차 NULL 삽입 → 2차 code→id 매핑 UPDATE. `is_citable` 필드도 추가.

**마스터 플랜 섹션 13 현행화:**
- 작업 B(규범 매핑), 골든 데이터셋, 레이블링, Data Leakage, 앙상블 검증 모두 ✅ 반영.

**Supabase 인프라 세팅 완료:**
- 작업 방식: **Supabase CLI + Migration 파일** 기반. `supabase/migrations/` 폴더에 SQL 파일 생성 → Claude Code CLI 감리 → 로컬 테스트(`supabase start`) → 클라우드 배포(`supabase db push`).
- MCP 연결: **읽기 전용(Read-only)**으로 설정. 로컬 MCP 서버 프로세스 방식(`npx @supabase/mcp-server-supabase`), PAT 인증. OAuth는 redirect_uri 문제로 불가 → PAT 방식으로 전환.
- MCP 역할: 스키마 생성 후 테이블 구조 확인, 시드 데이터 입력 후 데이터 정합성 조회, RPC 함수 호출 테스트. **쓰기 작업은 반드시 Migration 파일로만.**
- .env: Supabase URL, ANON_KEY, SERVICE_ROLE_KEY, OpenAI API Key 설정 완료.

**역할 재편 (코딩 실행 주체 변경):**
- Antigravity의 성능·레이트 리밋 이슈(2026년 3월 기준, Pro 플랜 주간 토큰 제한 심화)로 코딩 실행 주체를 변경.
- **Claude Code CLI** → 코딩 실행 (Opus 4.6, 200K 컨텍스트, 안정적 자율 코딩)
- **Claude.ai** → 1차 감리 (Opus 4.6, 설계 정합성·아키텍처 리뷰)
- **Antigravity** → 2차 더블체크 (Gemini 3.1 Pro, 비-Anthropic 계열의 독립적 관점)
- Antigravity는 Pro 플랜($20)으로 충분 (리뷰는 토큰 소비 적음). Ultra 업그레이드 불필요.

**파일명 정정 (v11 오류 수정):**
- `golden_dataset_final_26.json` → `golden_dataset_final.json` (실제 파일명)
- `golden_dataset_labels_v3.json` → `golden_dataset_labels.json` (실제 파일명)

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

### 1-2 투명성 처리 방침
텍스트 분석만으로는 "출처 미표시/저작권 침해"를 감지할 수 없다 (빠진 정보를 탐지해야 하는 유형).
Phase 1에서 메타데이터 비교 모듈(원문 vs 통신사 기사 유사도, 출처 표기 유무 체크 등)로 별도 구현 예정.

### Reserved Test Set
73건 (A-07, A-09 포함). `Golden_Data_Set_Pool/golden_dataset_reserved_test_set.json`에 프로젝트 외부 격리 보존.
프롬프트 튜닝 과정에서 참조 금지. 최종 성능 평가 시에만 사용.

---

## 다음 세션에서 할 일

### Week 1 M1: 전체 스키마 생성 (Day 1)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Gamnamu** | Claude Code CLI 터미널에서 M1 작업 지시 |
| 2 | **Claude Code CLI** | `supabase/migrations/` 폴더에 Migration SQL 파일 생성 (마스터 플랜 섹션 6 기반) |
| 3 | **Claude.ai (1차 감리)** | Migration 파일 리뷰 — SQL 정합성, 컬럼 누락, FK 순서, is_citable 반영 확인 |
| 4 | **Antigravity (2차 더블체크)** | 같은 파일을 Gemini 관점에서 독립 리뷰 |
| 5 | **Gamnamu** | 두 감리 결과 비교, 불일치 시 판단, 승인 |
| 6 | **Claude Code CLI** | `supabase start` → 로컬 Docker DB에서 Migration 자동 적용 |
| 7 | **Antigravity (MCP)** | `list_tables`로 테이블 구조 확인 (읽기 전용 조회) |
| 8 | **Gamnamu** | Supabase Studio (localhost:54323)에서 눈으로 확인, 배포 승인 |
| 9 | **Claude Code CLI** | `supabase link` + `supabase db push` → 클라우드 배포 |

### Week 1 M2: 시드 데이터 입력 (Day 2)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | 패턴·규범 데이터 입력 스크립트 구현 (2-패스 삽입: NULL → code→id UPDATE) |
| 2 | **Claude.ai (1차 감리)** | 스크립트 리뷰 + 데이터 정확성 검증 (tier 분류, parent 매핑, is_citable) |
| 3 | **Antigravity (2차 더블체크)** | 삽입 스크립트 독립 리뷰 + MCP로 DB 조회하여 결과 확인 |
| 4 | **Gamnamu** | tier 분류 최종 확인 |

> **Week 0 사전 준비 + 앙상블 검증 + 인프라 세팅이 모두 완료되었으므로 Week 1 삼각편대 질주 진입 가능.**

---

## 주요 파일 경로

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-25_v12.md      <- ★ 이 문서
├── golden_dataset_final.json              <- ★ 최종 확정 Dev Set (26건)
├── golden_dataset_labels.json             <- ★ 레이블링 (26건, 패턴+윤리코드+weight, v3)
├── ethics_codes_mapping.json              <- 윤리 규범 참조 (394개)
├── current-criteria_v2_active.md          <- 패턴 참조 (119개)
├── Code of Ethics for the Press.md        <- 14개 규범 원문 전문
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- ★ RAG 마스터 플랜 (2026-03-25 수정: 앙상블 4건 반영)
├── DB_BUILD_EXECUTION_GUIDE.md            <- ★ Week 1 Antigravity 실행용 (2026-03-25 수정: 2-패스 삽입)
├── DB_BUILD_ROLE_MAP.md                   <- Week 1 역할 분담 (v7 기준, stale — 마스터 플랜 우선)
├── _reference/
│   ├── 앙상블_검증_결과_{리뷰어}.md        <- 5개 검증 결과 (2026-03-25)
│   ├── cr_check_db_role_map.html          <- 역할 분담표 (비주얼)
│   └── cr_check_db_role_map.md            <- 역할 분담표 (텍스트)
└── _archive_superseded/                   <- 완료된 문서 아카이브 (v11 포함)
```

### 데이터 (Golden_Data_Set_Pool/)
```
/Users/gamnamu/Documents/Golden_Data_Set_Pool/
├── article_texts/             <- ★ 26건 원문 텍스트 (파이프라인 입력용)
├── [문제 기사]/                <- PDF 원본 103건
├── [이달의 기자상 수상작]/     <- True Negative 원본
├── yearly_data/               <- 심의자료 2021~2024 (Data Leakage 원본)
├── _source_rounds/            <- 개별 라운드 JSON/MD (아카이브)
└── _raw_research/             <- 처리 완료된 원본 리서치 (아카이브)
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **골든 데이터셋 최종 확정 26건.** `golden_dataset_final.json` 참조. (27이 아니라 26건임에 주의)
2. **레이블링은 `golden_dataset_labels.json`.** version="labeling_v3", weight 필드 포함 (tier 3-4→1.0, tier 2→0.5, tier 1→0.2).
3. **기사 원문은 `Golden_Data_Set_Pool/article_texts/`.** 포털 전재본으로 Data Leakage 해결 완료.
4. **Reserved Test Set 73건은 프로젝트 외부로 격리 완료.** `Golden_Data_Set_Pool/golden_dataset_reserved_test_set.json`으로 이동 (2026-03-28). docs/ 내에 존재하지 않음.
5. **1-2 투명성(출처 미표시/저작권)은 Dev Set에 없음.** Phase 1 메타데이터 비교 모듈로 별도 처리.
6. **v7~v11의 모든 지침(환경변수, Supabase, 코드 접두어, 매핑 패턴 등)은 그대로 유효.**
7. **다음 작업은 Week 1 M1(스키마 생성).** Claude Code CLI가 코딩 실행, Claude.ai가 1차 감리, Antigravity(Gemini)가 2차 더블체크.
8. **마스터 플랜 v4.0은 2026-03-25에 앙상블 검증 4건이 직접 반영된 최신 상태.** 섹션 6.1 SQL을 그대로 사용 가능.
9. **작업 방식: Supabase CLI + Migration 파일 기반.** MCP는 읽기 전용 조회 전용. 쓰기는 반드시 Migration으로만.
10. **역할 체계: Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Gemini(2차 더블체크) → Gamnamu(승인).** Antigravity는 Pro 플랜으로 리뷰 전용.

### 이전 세션에서 확립된 패턴 (v7에서 이어짐)

v7의 9개 매핑 패턴(context_hint, 상호참조, 수단/목적 분리, PCE 계층 우회, 보호 법익 기반, JEC-3 vs JEC-7, 행위 유형 기반, 절차 윤리, 약한 연결 기각)은 모두 유효.

### 레이블링에서 발견된 추가 패턴 (v11에서 신규)

1. **유추 적용 패턴**: 현행 규범에 AI 콘텐츠 전용 코드 부재. PCP-3-5(보도자료 검증)를 AI 생성 콘텐츠 검증에 유추 적용 (D-01, D-02).
2. **PCP-10-7→JEC-5 경로**: DB Junction Table에서 PCP-10-7(기사-광고 구분)이 JEC-5(독립적 보도)로 롤업되는 경로가 누락되어 있을 수 있음. 별도 이슈로 추적 필요 (A-09/A2-13).
3. **텍스트 분석 한계 유형 식별**: 1-2 출처 미표시, 편집 레이아웃, 사진/영상 사안은 텍스트 분석 불가 → 메타데이터·시각 모듈 필요.

### 앙상블 리뷰에서 채택된 구조적 제안 (실행 현황)

**골든 데이터셋 앙상블 (2026-03-23):**
1. **Dev/Test 분리** (제미니): 26건=Dev, 73건=Test. ✅ 완료
2. **Data Leakage 점검** (제미니): 심의자료 결정문 혼입 → 포털 전재본으로 해결. ✅ 완료
3. **기사 원문 아카이빙** (노트북LM): `article_texts/` 26건 로컬 아카이빙. ✅ 완료
4. **복합 위반 의도적 배치** (마누스): 다중 규범 조항 검색 테스트. ✅ 레이블링에 반영
5. **시대적 맥락(시간적 다양성)** (퍼플렉시티): 2020~2025 데이터 균형. ✅ 확인

**DB 구축 사전 검수 앙상블 (2026-03-25) — 반영 완료 4건:**
1. **ivfflat 인덱스 제거** (5/5 합의): 마스터 플랜 SQL에서 삭제. ✅
2. **is_citable 컬럼 추가** (5/5 합의): ethics_codes 테이블 + get_ethics_for_patterns() WHERE 절. ✅
3. **parent_code_id 2-패스 삽입** (2/5): 실행 가이드 시드 스크립트 수정. ✅
4. **롤업 인용 재귀 CTE** (2/5): get_ethics_for_patterns()에 parent chain 수집 로직 추가. ✅

**DB 구축 사전 검수 앙상블 — 보류 4건 (M4 이후 체크리스트):**
1. **메타 패턴 라우팅** (제미니): M4 RAG 파이프라인 구현 시 메타 패턴(1-4-1, 1-4-2)의 Haiku 전달 방식 확정 필요.
2. **1-2 투명성 패턴 필터링** (퍼플렉시티): Phase 1 메타데이터 모듈 설계 시 결정. is_text_analyzable 플래그 추가 여부.
3. **get_ethics_for_patterns 입력 타입** (퍼플렉시티): 백엔드 코드(M4)에서 코드→ID 변환 처리.
4. **FK 생성 순서** (퍼플렉시티/노트북LM): Migration 파일을 논리 단위로 분리하면 자연 해결.

**DB 구축 사전 검수 앙상블 — 주목할 고유 통찰:**
- **relation_type 매핑 규칙** (Claude Code CLI): 레이블링 v3의 5가지 유형(직접/보조/유추/상위/최상위)을 DB의 3가지(violates/related_to/exception_of) + strength로 매핑하는 규칙이 M2에서 필요.
- **타임아웃 대응** (노트북LM): M6에서 스크래핑+임베딩+LLM 2회 = 40~60초. Vercel/Railway 30초 제한 대비 필요.
- **규범 예외/단서 조항** (마누스): 금지 조항의 예외 조건 처리. M4 프롬프트 설계 시 고려.
- **마일스톤 번호 통일** (Claude Code CLI): 실행 가이드의 "1~6단계"를 마스터 플랜의 "M1~M6"으로 통일 권장.

### 주의사항
- 로컬 파일은 Desktop Commander(MCP)를 통해 읽고 쓸 수 있다.
- **KJA 접두어를 사용하지 마세요.** 기자윤리강령은 `JCE`이다. (마스터 플랜도 수정 완료)
- **Supabase Legacy JWT 키 사용 중.** "Disable JWT-based API keys" 누르지 말 것.
- **GitHub PAT 다음 만료일: 2026년 4월 16일.**
- **Supabase MCP PAT**: 90일 만료 설정. Antigravity의 `mcp_config.json`에 로컬 서버 방식으로 설정됨.
- **golden_dataset_final.json**이 최신 (v2, 26건). `_archive_superseded/golden_dataset_final_27.json`은 구버전.
- **golden_dataset_labels.json**이 최신 (v3, 26건). `_archive_superseded/golden_dataset_labels_v1/v2.json`은 구버전.
- **DB_BUILD_ROLE_MAP.md는 v7 기준으로 stale.** 마스터 플랜과 실행 가이드를 우선 참조할 것.
- **기사 청킹 로직 프로토타이핑**: Week 0에서 미착수. M3(벤치마크) 전까지 검증 필수.

---

*이 세션 컨텍스트는 2026-03-25에 v11→v12로 갱신되었다.*
*v11은 `_archive_superseded/`로 이동 대상.*
