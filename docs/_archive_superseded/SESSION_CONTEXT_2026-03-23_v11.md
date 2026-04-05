# 세션 컨텍스트 — 2026-03-23 v11

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 전환을 위한 **작업 ⑦⑧⑨가 모두 완료**되었다.
골든 데이터셋은 27건에서 **26건(TP 20 + TN 6)**으로 확정되었으며, 전 건의 레이블링·원문 아카이빙·Data Leakage 점검이 완료되었다.
다음 작업은 **Week 1 M1(전체 스키마 생성)** — Antigravity가 코딩 실행, Claude Code CLI가 감리.

### v10→v11 변경 사항 (2026-03-23)

**작업 ⑦ 완료 — 레이블링:**
- 26건 전체에 대해 `expected_patterns`(sub_types 배열), `expected_ethics_codes`(tier+weight), TN `expected_false_positive_risks` 작성
- v1 → v2: Gamnamu 피드백 11건 반영 (롤업 경로 수정, weight 필드, metadata 보강, 유추 적용 표시 등)
- v2 → v3: TN 3건 대체 + A-07 제거 + A-09→A2-13 대체 반영
- 33개 고유 ethics codes 사용 (14개 규범 중 8개 규범에서 인용)
- ethics_codes_mapping.json 394개 코드 전수 교차 검증: 에러 0건

**작업 ⑧ 완료 — Data Leakage 점검:**
- A 시리즈 심의자료 원문에 결정문(신문윤리위원회, 주의/경고 조처, 위반 판정 등) 혼입 확인
- 유형 1(기사 원문 있으나 결정문에 임베딩): A-01, A-06, A-11 → 포털 전재본으로 교체하여 해결
- 유형 2(기사 원문 없음, 결정문만 존재): A-07, A-09 → A-07 제외, A-09 대체
- **최종 결과: 26건 전부 CLEAN** (심의 관련 용어 0건)

**작업 ⑨ 완료 — 기사 원문 아카이빙:**
- 26건 전체 원문 텍스트를 `Golden_Data_Set_Pool/article_texts/{ID}_article.txt`로 로컬 아카이빙
- 총 124KB, 다음(Daum) 포털 전재본 + 언론사 직접 스크래핑 혼용
- URL Rot 대비 완료

**Dev Set 구조 변경 (27건→26건):**
- A-07 제외: 1-2 투명성(사진 출처 미표시)은 텍스트 분석 불가 → Phase 1 메타데이터 비교 모듈로 이관
- A-09 → A2-13 대체: 매경닷컴 편집 레이아웃(시각 사안) → 세계일보 기사형 광고(텍스트 분석 가능)
- TN 3건 대체: C2-01(KBS 스크립트→한국일보 코인), E-17(뉴스타파 영상→연합뉴스 AI이루다), E-19(뉴스타파 시리즈→한국일보 예비비)

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
73건 (A-07, A-09 포함). `golden_dataset_reserved_test_set.json`에 격리 보존.
프롬프트 튜닝 과정에서 참조 금지. 최종 성능 평가 시에만 사용.

---

## 다음 세션에서 할 일

### Week 1 M1: 전체 스키마 생성 (Day 1)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Antigravity** | RAG 테이블 + 기본 테이블 + 뷰 + 함수 SQL 작성·실행 |
| 2 | **Claude Code CLI** | SQL 정합성, 컬럼 누락, 인덱스 감리 |

### Week 1 M2: 시드 데이터 입력 (Day 2)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Antigravity** | 패턴·규범 데이터 입력 스크립트 구현 (`ethics_codes_mapping.json` 기반) |
| 2 | **Claude Code CLI** | 데이터 정확성 검증 (tier 분류, parent 매핑) |
| 3 | **Gamnamu** | tier 분류 최종 확인 |

> **Week 0 사전 준비가 모두 완료되었으므로 Week 1 삼각편대 질주 진입 가능.**

---

## 주요 파일 경로

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-23_v11.md      <- 이 문서
├── golden_dataset_final.json           <- ★ 최종 확정 Dev Set (26건)
├── golden_dataset_labels.json          <- ★ 레이블링 (26건, 패턴+윤리코드+weight)
├── golden_dataset_reserved_test_set.json  <- 격리 테스트셋 (열람 금지)
├── ethics_codes_mapping.json              <- 윤리 규범 참조 (394개)
├── current-criteria_v2_active.md          <- 패턴 참조 (119개)
├── Code of Ethics for the Press.md        <- 14개 규범 원문 전문
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- RAG 마스터 플랜
├── DB_BUILD_EXECUTION_GUIDE.md            <- Week 1 Antigravity 실행용
├── DB_BUILD_ROLE_MAP.md                   <- Week 1 역할 분담 (v10 기준, stale 부분 있음)
├── _reference/
│   ├── cr_check_db_role_map.html          <- 역할 분담표 (비주얼)
│   └── cr_check_db_role_map.md            <- 역할 분담표 (텍스트)
└── _archive_superseded/                   <- 완료된 문서 아카이브 (v10 포함)
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

1. **골든 데이터셋 최종 확정 26건.** `golden_dataset_final_26.json` 참조. (27이 아니라 26건임에 주의)
2. **레이블링은 `golden_dataset_labels_v3.json`.** weight 필드 포함 (tier 3-4→1.0, tier 2→0.5, tier 1→0.2).
3. **기사 원문은 `Golden_Data_Set_Pool/article_texts/`.** 포털 전재본으로 Data Leakage 해결 완료.
4. **Reserved Test Set 73건은 열람 금지.** `golden_dataset_reserved_test_set.json`은 프롬프트 튜닝 중 참조하지 말 것.
5. **1-2 투명성(출처 미표시/저작권)은 Dev Set에 없음.** Phase 1 메타데이터 비교 모듈로 별도 처리.
6. **v7~v10의 모든 지침(환경변수, Supabase, 코드 접두어, 매핑 패턴 등)은 그대로 유효.**
7. **다음 작업은 Week 1 M1(스키마 생성).** Antigravity가 코딩, Claude Code CLI가 감리.

### 이전 세션에서 확립된 패턴 (v7에서 이어짐)

v7의 9개 매핑 패턴(context_hint, 상호참조, 수단/목적 분리, PCE 계층 우회, 보호 법익 기반, JEC-3 vs JEC-7, 행위 유형 기반, 절차 윤리, 약한 연결 기각)은 모두 유효.

### 레이블링에서 발견된 추가 패턴 (v11에서 신규)

1. **유추 적용 패턴**: 현행 규범에 AI 콘텐츠 전용 코드 부재. PCP-3-5(보도자료 검증)를 AI 생성 콘텐츠 검증에 유추 적용 (D-01, D-02).
2. **PCP-10-7→JEC-5 경로**: DB Junction Table에서 PCP-10-7(기사-광고 구분)이 JEC-5(독립적 보도)로 롤업되는 경로가 누락되어 있을 수 있음. 별도 이슈로 추적 필요 (A-09/A2-13).
3. **텍스트 분석 한계 유형 식별**: 1-2 출처 미표시, 편집 레이아웃, 사진/영상 사안은 텍스트 분석 불가 → 메타데이터·시각 모듈 필요.

### 앙상블 리뷰에서 채택된 구조적 제안 (실행 현황)

1. **Dev/Test 분리** (제미니): ~~27건=Dev~~ 26건=Dev, 73건=Test. ✅ 완료
2. **Data Leakage 점검** (제미니): 심의자료 결정문 혼입 확인 → 포털 전재본으로 해결. ✅ 완료
3. **기사 원문 아카이빙** (노트북LM): `article_texts/` 26건 로컬 아카이빙. ✅ 완료
4. **복합 위반 의도적 배치** (마누스): 다중 규범 조항 검색 테스트. ✅ 레이블링에 반영
5. **시대적 맥락(시간적 다양성)** (퍼플렉시티): 2020~2025 데이터 균형. ✅ 확인

### 주의사항
- 로컬 파일은 Desktop Commander(MCP)를 통해 읽고 쓸 수 있다.
- **KJA 접두어를 사용하지 마세요.** 기자윤리강령은 `JCE`이다.
- **Supabase Legacy JWT 키 사용 중.** "Disable JWT-based API keys" 누르지 말 것.
- **PAT 다음 만료일: 2026년 4월 16일.**
- **golden_dataset_final_27.json은 v1(구버전).** 26.json이 최신. 혼동 주의.
- **golden_dataset_labels_v1/v2는 구버전.** v3가 최신.

---

*이 세션 컨텍스트는 2026-03-23에 v10→v11으로 갱신되었다.*
