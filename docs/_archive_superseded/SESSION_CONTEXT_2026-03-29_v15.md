# 세션 컨텍스트 — 2026-03-29 v15

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 전환을 위한 **Week 1 M1(스키마) + M2(시드 데이터) + M3(임베딩+벤치마크)가 모두 완료**되었다.
M3 벤치마크에서 벡터 검색 단독의 구조적 한계를 실증 확인 (Recall@10 = 0.33 at t=0.3, key_text 기준).
**핵심 결론: 기사↔패턴 매칭은 "검색"이 아닌 "추론" 문제** — LLM 통합이 필수.
다음 작업은 **Week 2 M4(RAG 파이프라인 구현)** — 1.5회 호출 구조(벡터→Haiku→규범조회→Sonnet).

### v14→v15 변경 사항 (2026-03-29)

**M3 완료 (임베딩 생성 + 벤치마크):**
- 날짜: 2026-03-28~29
- 임베딩 모델: OpenAI text-embedding-3-small (1536차원) — 확정 (M5에서 재평가 가능)
- 임베딩 적재: patterns 28건 + ethics_codes 373건 = **401개** (로컬 DB)
- 초단문 처리: 26건 `title + " — " + full_text` 결합
- article_key_text 추출: GPT-4o로 TP 20건에서 핵심 문장 57건 추출 (평균 74자)
- 클라우드 배포: **M4 완료 후 일괄 수행** (M3 임베딩은 로컬 DB에만 적재)

**벤치마크 결과:**

| 벤치마크 | 쿼리 | t=0.3 | t=0.5 | 판정 |
|----------|------|-------|-------|------|
| 1차 | 기사 전문 (8000자) | 0.583 | 0.308 | FAIL |
| 2차 | key_text (74자) | 0.333 | 0.269 | FAIL |

- 1차의 0.583은 어휘적 우연에 의한 부풀려진 수치 (false positive 포함)
- 2차의 0.333이 벡터 검색의 실제 성능
- **근본 원인**: 도메인 갭(뉴스 문체 vs 윤리 기준 문체) + 추론 갭(의미적 매칭에 LLM 추론 필요)
- **Recall@10 ≥ 80% 목표는 M4(LLM 통합 파이프라인)로 이관**

**M3 재정의된 완료 기준 (모두 달성):**
- [x] 패턴 28개 description_embedding 적재
- [x] 규범 373개 text_embedding 적재
- [x] 메타 패턴 2개 + is_citable=FALSE 21건 임베딩 제외 확인
- [x] 초단문 26건 결합 텍스트 임베딩
- [x] search_pattern_candidates() RPC 정상 작동
- [x] 벡터 검색 한계 실증 확인 (1차+2차 벤치마크 데이터 확보)
- [x] 벤치마크 결과 문서화 (docs/M3_BENCHMARK_RESULTS.md)

**M3 감리 이력:**

| # | 감리자 | 결과 | 내용 |
|---|--------|------|------|
| 1 | Claude.ai (1차) | 수정 1건 | generate_embeddings.py rollback() 추가 |
| 2 | Antigravity (2차) | PASS | 메타 패턴/is_citable 제외 검증 쿼리 2건 통과 |
| 3 | 3자 합동 감리 | 합의 | 벡터 검색 한계 확인, M4 전환 승인 |

**patterns 38개 vs 119개 — 최종 판단:**
- 벤치마크 결과 세분화(E안)는 비권고 (오탐 증가 + 추론 갭 미해결)
- 38개 유지. Haiku LLM이 패턴 식별을 전담하는 구조에서는 벡터 검색 세분화의 실익 없음

**threshold — 미확정:**
- M4에서 0.2~0.25로 시작하여 튜닝 (벡터 검색을 느슨한 후보 선정으로 활용)

---

## M1+M2 완료 이력 (v14에서 계승)

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

### article_key_text 추출 완료 (2026-03-28)
- GPT-4o로 TP 20건에서 핵심 문장 57건 추출
- golden_dataset_final.json에 article_key_text 필드 업데이트
- 원본 백업: golden_dataset_final_backup.json

---

## 다음 세션에서 할 일

### Week 2 M4: RAG 파이프라인 구현 (Day 6~7)

| 순서 | 담당 | 작업 내용 |
|------|------|-----------|
| 1 | **Claude Code CLI** | 기사 청킹 로직 구현 (300~500자 의미 기반 병합, 마스터 플랜 섹션 4) |
| 2 | **Claude Code CLI** | 1.5회 호출 파이프라인 구현 (마스터 플랜 섹션 7.2) |
| 3 | **Claude Code CLI** | Haiku 프롬프트 설계 (패턴 후보 식별, 마스터 플랜 섹션 7.3) |
| 4 | **Claude Code CLI** | 벤치마크 v3 (전체 파이프라인 대상 Recall + Precision) |
| 5 | **Claude.ai (1차 감리)** | 파이프라인 정합성, 프롬프트 리뷰 |
| 6 | **Antigravity (2차 더블체크)** | 독립 리뷰 |
| 7 | **Gamnamu** | 벤치마크 v3 결과 확인, M4 완료 승인 |

**M4 핵심 체크포인트 (M3에서 도출):**

1. **청킹 전략 필수 적용**: 기사 전문(수천 자)을 300~500자 의미 기반 블록으로 분할. 한국 뉴스의 한 문장 줄바꿈 관행 대응.
2. **벡터 검색 threshold 대폭 하향**: 0.2~0.25에서 시작. 벡터 검색은 "후보 넓게 뿌리기" 역할.
3. **벤치마크 지표 분리**:
   - Candidate Recall: 벡터 검색이 정답 패턴을 후보에 포함시켰는가 (≥ 70%)
   - Final Recall: Haiku 최종 확정 패턴이 정답과 일치하는가 (≥ 80%)
   - Final Precision: Haiku 확정 패턴 중 실제 정답 비율 (≥ 60%)
4. **Haiku가 패턴 식별 전담**: 벡터 검색은 보조. Haiku 프롬프트에 전체 패턴 목록을 포함하되, 벡터 검색 상위 후보를 강조 표시.
5. **메타 패턴 라우팅**: 1-4-1, 1-4-2는 Haiku에 직접 전달하지 않고, 하위 관련 지표 패턴의 조합으로 추론. 마스터 플랜 섹션 8 참조.
6. **get_ethics_for_patterns 입력 타입**: 백엔드에서 코드→ID 변환 처리.

**M4 파이프라인 구조 (마스터 플랜 섹션 7.2):**
```
기사 URL → 스크래핑 → 전처리(노이즈 제거)
    → 의미 기반 병합 청킹 (300~500자)
    → 청크별 임베딩 → search_pattern_candidates() (t=0.2~0.25)
    → Haiku (패턴 후보 + 기사 → 패턴 확정)
    → 백엔드 밸리데이션 (환각 코드 제거)
    → get_ethics_for_patterns() (규범 정밀 조회)
    → Sonnet (확정 패턴 + 규범 → 결정론적 인용 리포트)
```

### M4 이후 (Day 8~10)

| 마일스톤 | 작업 내용 |
|----------|----------|
| M5 | 결정론적 인용 후처리 + 메타 패턴 추론 + 임베딩 모델 재평가(선택) |
| M6 | Phase 1 아카이빙 통합 (DB 저장 + 공개 URL) |
| 배포 | M4 완료 후 임베딩 + 코드 일괄 클라우드 배포 |

---

## 주요 파일 경로

### 문서 (docs/) — 활성 파일
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-29_v15.md      <- ★ 이 문서
├── M3_BENCHMARK_RESULTS.md                <- ★ M3 벤치마크 결과 (1차+2차+최종 결론)
├── golden_dataset_final.json              <- ★ Dev Set 26건 (article_key_text 포함)
├── golden_dataset_final_backup.json       <- article_key_text 추가 전 백업
├── golden_dataset_labels.json             <- ★ 레이블링 v3
├── ethics_codes_mapping.json              <- 윤리 규범 394개
├── current-criteria_v2_active.md          <- 패턴 119개
├── Code of Ethics for the Press.md        <- 14개 규범 원문
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         <- ★ RAG 마스터 플랜
├── DB_BUILD_EXECUTION_GUIDE.md            <- 실행 가이드
└── _archive_superseded/                   <- v14 포함
```

### Supabase
```
/Users/gamnamu/Documents/cr-check/supabase/
├── config.toml
└── migrations/
    ├── 20260328000000_create_cr_check_schema.sql  <- M1 (407줄)
    └── 20260328100000_seed_data.sql               <- M2 (1,257줄)
```

### 스크립트
```
/Users/gamnamu/Documents/cr-check/scripts/
├── generate_m2_seed.py            <- M2 시드 SQL 생성
├── generate_embeddings.py         <- M3 임베딩 생성 (로컬 DB 대상)
├── extract_key_texts.py           <- article_key_text 추출 (GPT-4o)
├── benchmark_recall.py            <- M3 벤치마크 v1 (기사 전문)
└── benchmark_recall_v2.py         <- M3 벤치마크 v2 (key_text)
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **골든 데이터셋 최종 확정 26건.** `golden_dataset_final.json` 참조. article_key_text 포함.
2. **레이블링은 `golden_dataset_labels.json`.** version="labeling_v3", weight 필드 포함.
3. **기사 원문은 `Golden_Data_Set_Pool/article_texts/`.** 포털 전재본으로 Data Leakage 해결 완료.
4. **Reserved Test Set 73건은 프로젝트 외부로 격리 완료.** 참조 금지.
5. **1-2 투명성(출처 미표시/저작권)은 Dev Set에 없음.** Phase 1 메타데이터 모듈로 별도 처리.
6. **v7~v14의 모든 지침은 그대로 유효.**
7. **M1+M2+M3 완료.** DB에 394 규범 + 38 패턴 + 70 관계 + 401 임베딩 적재. 다음은 M4(RAG 파이프라인).
8. **벡터 검색 한계 확인됨.** threshold를 0.2~0.25로 대폭 하향, Haiku LLM이 패턴 식별 전담.
9. **클라우드 배포는 M4 완료 후 일괄 수행.** 현재 임베딩은 로컬 DB에만 적재.
10. **역할 체계 유지.** Claude Code CLI(코딩) → Claude.ai(1차 감리) → Antigravity/Gemini(2차 더블체크) → Gamnamu(승인).

### M1~M3 감리에서 확립된 교훈

1. **WITH RECURSIVE 필수**: 자기 참조 CTE에는 반드시 필요.
2. **CROSS JOIN 주의**: 재귀 CTE 내에서 식별자를 상속하여 스코핑.
3. **재귀 depth 제한**: depth 카운터 필수 (현재 최대 5).
4. **트리거 누락 주의**: updated_at 컬럼 → 자동 갱신 트리거 함께 생성.
5. **트랜잭션 래핑**: 대량 INSERT는 BEGIN/COMMIT으로 감싸기.
6. **ON CONFLICT idempotency**: 재실행 가능하도록 DO NOTHING 추가.
7. **MCP 조회 대상 주의**: Antigravity MCP는 클라우드 DB를 조회.
8. **벡터 검색은 보조 도구**: 기사↔패턴 매칭은 추론 문제. LLM 통합 필수.
9. **기사 전문 임베딩은 비효과적**: 8000자 통째 임베딩 → 청킹 필수.

### 이전 세션에서 확립된 패턴 (v7에서 이어짐)

v7의 9개 매핑 패턴은 모두 유효. v11의 3개 추가 패턴도 유효.

### 앙상블 리뷰 — 보류 체크리스트

**M4 이전 해결 필요 (3건):**
1. **메타 패턴 라우팅** (제미니): Haiku 전달 방식 확정
2. **1-2 투명성 패턴 필터링** (퍼플렉시티): is_text_analyzable 플래그
3. **get_ethics_for_patterns 입력 타입** (퍼플렉시티): 코드→ID 변환

**기술 부채 (Phase 2 이후):**
- ENUM 미사용, URL 길이 제한
- 임베딩 모델 재평가 (M5)
- 타임아웃 대응 (M6)

### 주의사항
- **KJA 접두어 절대 금지.** JCE가 올바른 접두어.
- **Supabase Legacy JWT 키 사용 중.** "Disable JWT-based API keys" 누르지 말 것.
- **GitHub PAT 만료일: 2026-04-16.**
- **golden_dataset_final.json**에 article_key_text가 추가됨 (2026-03-28). 원본 백업 존재.
- **1-7-2(헤드라인 윤리 문제)**: criteria 파일에 없지만 M2에서 수동 추가 완료.
- **supabase start → Docker 필요.** 로컬 DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **임베딩은 로컬 DB에만 적재.** 클라우드에는 M4 후 일괄 배포.

---

*이 세션 컨텍스트는 2026-03-29에 v14→v15로 갱신되었다.*
*v14는 `_archive_superseded/`로 이동 완료.*
