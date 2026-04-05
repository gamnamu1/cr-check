# 세션 컨텍스트 — 2026-03-28 v14

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 전환을 위한 **Week 1 M1(스키마) + M2(시드 데이터)가 모두 완료**되었다.
Supabase Migration 2개 파일로 전체 스키마 생성 + 394개 규범·38개 패턴·70개 관계 데이터를 적재.
로컬 Docker DB 테스트 + 클라우드 배포 완료. get_ethics_for_patterns() 재귀 CTE 함수 동작 검증 완료.
다음 작업은 **Week 1 M3(임베딩 생성 + 벤치마크)**.

### v13→v14 변경 사항 (2026-03-28)

**M2 완료 (시드 데이터 입력):**
- 날짜: 2026-03-28
- Migration 파일: `supabase/migrations/20260328100000_seed_data.sql` (1,257줄, 156KB)
- Python 생성 스크립트: `scripts/generate_m2_seed.py`

**M2 적재 결과:**

| 테이블 | 레코드 수 | 비고 |
|--------|-----------|------|
| ethics_codes | 394 | 14개 규범 문서, 2-패스 삽입 |
| patterns | 38 | 대분류 8 + 소분류 30 (1-7-2 수동 추가) |
| ethics_code_hierarchy | 42 | junction 배열에서 추출 |
| pattern_ethics_relations | 70 | 골든 데이터셋 레이블 기반 |
| pattern_relations | 10 | criteria 파일 교차참조 + 메타 패턴 지표 |

**2-패스 삽입 결과:**
- 384건 parent_code_id 매핑 성공 (394 전체 - 10 JEC Tier 1 루트 = 384)
- CASE-WHEN 구문으로 code→id 일괄 UPDATE

**is_citable = FALSE 확정 21건:**
- 서문/총강 16건: JEC-P, JCE-P, JCP-P, PCE-P, PCP-P, HRG-P, SRE-P, SPG-P, DRG-P, IRG-P, EPG-P, PRG-P, MRG-P, HSD-P, PRG-T1, PRG-T2
- 부칙/운영 5건: DRG-40, DRG-41, DRG-42, EPG-27, EPG-28

**relation_type 매핑 규칙 확정:**

| 레이블 접두사 | DB relation_type | DB strength | 비고 |
|---------------|------------------|-------------|------|
| 직접 적용 | violates | strong | 1:1 대응 |
| 보조 적용 | related_to | moderate | 관련 측면 포착 |
| 유추 적용 | related_to | weak | 대안 매핑 (전용 코드 부재) |
| 상위 규범 | (미저장) | — | parent_chain CTE 롤업으로 처리 |
| 최상위 원칙 | (미저장) | — | parent_chain CTE 롤업으로 처리 |

**M2 감리 과정:**

| # | 감리자 | 결과 | 수정 사항 |
|---|--------|------|----------|
| 1 | Claude.ai (1차) | 조건부 승인 | BEGIN/COMMIT 트랜잭션 래핑 + ON CONFLICT idempotency 보완 2건 |
| 2 | Antigravity (2차) | PASS | SQL 파일 기준 승인 |
| — | (참고) | MCP 0건 에피소드 | Antigravity MCP가 클라우드 DB를 조회 → 아직 push 전이라 0건. 로컬 Docker DB에는 정상 적재 |

**patterns 38개 vs 119개 판단 보류:**
- criteria 파일의 1-X-Y 코드 레벨로 38개(대분류 8 + 소분류 30) 삽입
- 119개는 소분류 내 세부 항목(bullet point)까지 포함한 수
- M3 벤치마크에서 Recall@10 확인 후 세분화 여부 결정
- 골든 데이터셋이 1-X-Y 코드 레벨만 사용하므로 현재 38개로 충분할 가능성 높음

---

## M1 완료 이력 (v13에서 계승)

- Migration: `supabase/migrations/20260328000000_create_cr_check_schema.sql` (407줄)
- DB 객체: 테이블 9개, 뷰 2개, RPC 함수 5개, 트리거 함수 1개, 트리거 2개
- M1 감리 수정 5건: WITH RECURSIVE, CROSS JOIN 버그, depth 제한, updated_at 트리거, ENUM 기술부채

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

### Week 1 M3: 임베딩 생성 + 벤치마크 (Day 3)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | OpenAI text-embedding-3-small로 패턴(30개) + 규범(373개 citable) 임베딩 생성 |
| 2 | **Claude Code CLI** | 초단문 엔트리(30자 미만 26개): `title + " — " + full_text` 결합 텍스트로 임베딩 |
| 3 | **Claude Code CLI** | DB에 description_embedding / text_embedding 컬럼 UPDATE |
| 4 | **Claude Code CLI** | 골든 데이터셋 26건의 article_key_text로 search_pattern_candidates() Recall@10 측정 |
| 5 | **Claude.ai (1차 감리)** | Recall@10 결과 리뷰, threshold(0.5) 적정성 판단 |
| 6 | **Gamnamu** | 벤치마크 결과 확인, 임베딩 모델 최종 확정 또는 대안 모델 테스트 결정 |

**M3 핵심 체크포인트:**
- 배치 임베딩: OpenAI 배치 API로 한 번에 처리 (~$0.01)
- 벤치마크 기준: Recall@10 ≥ 80% (마스터 플랜 섹션 11.3)
- threshold 튜닝: 0.5 기본값에서 시작, Recall이 낮으면 0.4로, 노이즈 많으면 match_count 조정
- patterns 세분화 판단: Recall이 낮으면 38개 → 소분류 세분화 검토

### Week 1 M4 이후 (Day 4~5)

| 마일스톤 | 작업 내용 |
|----------|----------|
| M4 | RAG 파이프라인 구현 (1.5회 호출) |
| M5 | 결정론적 인용 + 메타 패턴 추론 |
| M6 | Phase 1 아카이빙 통합 |

---

## 주요 파일 경로

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-28_v14.md      <- ★ 이 문서
├── golden_dataset_final.json              <- ★ 최종 확정 Dev Set (26건)
├── golden_dataset_labels.json             <- ★ 레이블링 (26건, 패턴+윤리코드+weight, v3)
├── ethics_codes_mapping.json              <- 윤리 규범 참조 (394개)
├── current-criteria_v2_active.md          <- 패턴 참조 (119개)
├── Code of Ethics for the Press.md        <- 14개 규범 원문 전문
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- ★ RAG 마스터 플랜 (2026-03-25 수정: 앙상블 4건 반영)
├── DB_BUILD_EXECUTION_GUIDE.md            <- ★ Week 1 실행 가이드 (2026-03-25 수정: 2-패스 삽입)
├── DB_BUILD_ROLE_MAP.md                   <- Week 1 역할 분담 (v7 기준, stale — 마스터 플랜 우선)
├── _reference/
│   ├── 앙상블_검증_결과_{리뷰어}.md        <- 5개 검증 결과 (2026-03-25)
│   ├── cr_check_db_role_map.html          <- 역할 분담표 (비주얼)
│   └── cr_check_db_role_map.md            <- 역할 분담표 (텍스트)
└── _archive_superseded/                   <- 완료된 문서 아카이브 (v13 포함)
```

### Supabase
```
/Users/gamnamu/Documents/cr-check/supabase/
├── config.toml
└── migrations/
    ├── 20260328000000_create_cr_check_schema.sql  <- ★ M1 스키마 (407줄)
    └── 20260328100000_seed_data.sql               <- ★ M2 시드 (1,257줄)
```

### 스크립트
```
/Users/gamnamu/Documents/cr-check/scripts/
└── generate_m2_seed.py                            <- M2 시드 SQL 생성기
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
6. **v7~v13의 모든 지침(환경변수, Supabase, 코드 접두어, 매핑 패턴 등)은 그대로 유효.**
7. **M1+M2 완료 (2026-03-28).** DB에 394 규범 + 38 패턴 + 70 관계 적재 완료. 다음은 M3(임베딩+벤치마크).
8. **마스터 플랜 v4.0은 2026-03-25에 앙상블 검증 4건이 직접 반영된 최신 상태.**
9. **작업 방식: Supabase CLI + Migration 파일 기반.** MCP는 읽기 전용 조회 전용. 쓰기는 반드시 Migration으로만.
10. **역할 체계: Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Gemini(2차 더블체크) → Gamnamu(승인).** Antigravity는 Pro 플랜으로 리뷰 전용.

### M1+M2 감리에서 확립된 교훈

1. **WITH RECURSIVE 필수**: parent_chain처럼 자기 참조하는 CTE에는 반드시 `WITH RECURSIVE` 키워드가 필요.
2. **CROSS JOIN 주의**: 다중 엔티티 조회 시 CROSS JOIN은 카테시안 곱 버그의 원인. 재귀 CTE 내에서 식별자를 상속하여 스코핑.
3. **재귀 depth 제한**: 데이터 오염 대비 depth 카운터 필수 (현재 최대 5).
4. **트리거 누락 주의**: `updated_at` 컬럼이 있으면 자동 갱신 트리거를 반드시 함께 생성.
5. **트랜잭션 래핑**: 대량 시드 INSERT는 BEGIN/COMMIT으로 감싸서 중간 실패 시 롤백 보장.
6. **ON CONFLICT idempotency**: 재실행 가능하도록 INSERT에 ON CONFLICT DO NOTHING 추가.
7. **MCP 조회 대상 주의**: Antigravity MCP는 클라우드 DB를 조회. 로컬 Docker DB에만 적용된 상태에서 MCP 조회 시 0건 반환됨.

### 이전 세션에서 확립된 패턴 (v7에서 이어짐)

v7의 9개 매핑 패턴(context_hint, 상호참조, 수단/목적 분리, PCE 계층 우회, 보호 법익 기반, JEC-3 vs JEC-7, 행위 유형 기반, 절차 윤리, 약한 연결 기각)은 모두 유효.

### 레이블링에서 발견된 추가 패턴 (v11에서 신규)

1. **유추 적용 패턴**: 현행 규범에 AI 콘텐츠 전용 코드 부재. PCP-3-5(보도자료 검증)를 AI 생성 콘텐츠 검증에 유추 적용 (D-01, D-02).
2. **PCP-10-7→JEC-5 경로**: DB Junction Table에서 PCP-10-7(기사-광고 구분)이 JEC-5(독립적 보도)로 롤업되는 경로가 누락되어 있을 수 있음. 별도 이슈로 추적 필요 (A-09/A2-13).
3. **텍스트 분석 한계 유형 식별**: 1-2 출처 미표시, 편집 레이아웃, 사진/영상 사안은 텍스트 분석 불가 → 메타데이터·시각 모듈 필요.

### 앙상블 리뷰에서 채택된 구조적 제안 (실행 현황)

**골든 데이터셋 앙상블 (2026-03-23):** 5건 모두 ✅ 완료

**DB 구축 사전 검수 앙상블 (2026-03-25) — 반영 완료 4건:** 모두 ✅

**DB 구축 사전 검수 앙상블 — 보류 3건 (M4 이후 체크리스트):**
1. **메타 패턴 라우팅** (제미니): M4 RAG 파이프라인 구현 시 메타 패턴(1-4-1, 1-4-2)의 Haiku 전달 방식 확정 필요.
2. **1-2 투명성 패턴 필터링** (퍼플렉시티): Phase 1 메타데이터 모듈 설계 시 결정. is_text_analyzable 플래그 추가 여부.
3. **get_ethics_for_patterns 입력 타입** (퍼플렉시티): 백엔드 코드(M4)에서 코드→ID 변환 처리.

**DB 구축 사전 검수 앙상블 — 주목할 고유 통찰:**
- **relation_type 매핑 규칙**: ✅ M2에서 확정 및 적용 완료 (직접→violates/strong, 보조→related_to/moderate, 유추→related_to/weak).
- **타임아웃 대응** (노트북LM): M6에서 스크래핑+임베딩+LLM 2회 = 40~60초. Vercel/Railway 30초 제한 대비 필요.
- **규범 예외/단서 조항** (마누스): 금지 조항의 예외 조건 처리. M4 프롬프트 설계 시 고려.
- **ENUM 미사용, URL 길이 제한** (마누스 추가감리): 기술 부채로 기록. Phase 2 이후 검토.

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
- **supabase start 실행 시 Docker 필요.** 로컬 DB URL: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **1-7-2(헤드라인 윤리 문제)**: criteria 파일에 없지만 골든 데이터셋에서 사용. M2에서 수동 추가 완료.

---

*이 세션 컨텍스트는 2026-03-28에 v13→v14로 갱신되었다.*
*v13은 `_archive_superseded/`로 이동 완료.*
