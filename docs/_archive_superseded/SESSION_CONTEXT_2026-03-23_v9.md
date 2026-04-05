# 세션 컨텍스트 — 2026-03-23 v9

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 전환을 위한 **골든 데이터셋 구축이 거의 완료**되었다.
1차·2차·외부·디지털 보강 라운드를 거쳐 **총 109건의 후보 풀**이 확보되었으며,
방송/영상 콘텐츠 제외 정책 적용 후 **유효 후보는 약 100건**이다.
8대분류 전 영역에서 목표를 충족하며, **1-8 디지털도 7건으로 초과 달성**되었다.
다음 작업은 **전체 풀 통합 마스터 뷰 생성 → 최종 20~30건 선별**이다.

### v8→v9 변경 사항 (2026-03-23)

**역추적 리드 확인 완료:**
- 리드 E (트럼프 AI 오보): EBN 메타 기사 확인. 개별 오보 기사는 디지털 보강에서 해결
- 리드 F (여론조사 무더기 주의): 대표 2건 특정 — 아시아투데이(3/31), 문화일보(4/24). 개별 결정번호는 ikpec.or.kr 수동 확인 필요
- 리드 C (KBS AI 영상): KBS 뉴스9 북중러 정상 AI 영상 (2025.09.01). **방송 콘텐츠 → 제외**
- 리드 B (조선일보 AI 어시스턴트): 101건 AI 기사 보도. 투명성 표기 양호 → 문제 사례로는 약함
- 리드 A, D: 미착수 (시간 대비 효율 낮아 중단)

**1-8 디지털 보강 완료 (4건 편입):**
- D-01: 뉴스핌 AI MY뉴스 트럼프 오보 (AI 표기有, 퍼플렉시티)
- D-02: 글로벌이코노믹 트럼프 오보 (AI 표기無, 미정정)
- D-03: 대구신문 제목 어뷰징 (신윤위 '주의' 제재)
- D-04: 위키트리 낚시 썸네일 (안세영 기사)

**디렉토리 정리:**
- `[추가]` 원본 리서치 3파일 → `_raw_research/`로 이동
- 외부 리서치 원본(Manus, NotebookLM, Perplexity) → 이전에 정리됨

**새로 생성된 문서:**
- `docs/GOLDEN_DATASET_DIGITAL_RESEARCH_BRIEF.md` — 1-8 보강 리서치 브리프
- `Golden_Data_Set_Pool/golden_dataset_candidates_digital.json` — 디지털 보강 4건
- `Golden_Data_Set_Pool/golden_dataset_candidates_digital.md` — 디지털 보강 요약

---

## 골든 데이터셋 후보 풀 현황

### 수량 요약

| 소스 | 전체 | 제외 | 유효 |
|------|------|------|------|
| 1차 라운드 (Claude Code CLI) | 44건 | 3건 | **41건** |
| 2차 라운드 (Claude Code CLI) | 41건 | 2건 | **39건** |
| 외부 리서치 정리 | 20건 | 4건 | **16건** |
| 디지털 보강 | 4건 | 0건 | **4건** |
| **합계** | **109건** | **9건** | **100건** |

### 합산 커버리지 (유효 100건 기준)

| 대분류 | 합산 | 목표 | 상태 |
|--------|------|------|------|
| 1-1 진실성 | ~16건 | 9~10 | ✅ 충분 |
| 1-2 투명성 | ~8건 | 5~6 | ✅ 충분 |
| 1-3 균형성 | ~14건 | 10~11 | ✅ 충분 |
| 1-4 독립성 | ~12건 | 6~7 | ✅ 충분 |
| 1-5 인권 | ~22건 | 14~15 | ✅ 충분 |
| 1-6 전문성 | ~11건 | 5~6 | ✅ 충분 |
| 1-7 언어 | ~14건 | 7~8 | ✅ 충분 |
| 1-8 디지털 | **7건** | 4+ | ✅ **초과 달성** |
| True Negative | ~18건 | 13~16 | ✅ 충분 |

---

## 방송/영상 콘텐츠 제외 정책

변경 없음. `GOLDEN_DATASET_BROADCAST_EXCLUSION_POLICY.md`와 `exclusion_flags.json` 참조.
**제외 9건**: C-01, C-07, C-08, C2-04, C2-05, E-10, E-13, E-16, E-20

---

## 다음 세션에서 할 일

### 작업 ⑤: 전체 후보 풀 통합 마스터 뷰 생성

4개 소스 파일을 하나의 통합 뷰로 병합:
- `golden_dataset_candidates.json` (1차, 44건)
- `golden_dataset_candidates_round2.json` (2차, 41건)
- `golden_dataset_candidates_external.json` (외부, 20건)
- `golden_dataset_candidates_digital.json` (디지털 보강, 4건)

통합 시 수행할 작업:
1. **중복 점검**: 결정번호(decision_no) 기준 중복 제거
2. **방송 제외 반영**: `exclusion_flags.json`의 9건 제외 플래그 적용
3. **커버리지 최종 집계**: 8대분류별 유효 건수 정산
4. **언론사 다양성 점검**: 동일 언론사 편중 여부 확인
5. **난이도 분포 점검**: easy/medium/hard 비율 확인

산출물: `golden_dataset_master_view.json` + `.md`

### 작업 ⑥: 최종 20~30건 선별 (Gamnamu + Claude)

통합된 ~100건 풀에서 최종 20~30건 선별. 기준:
- 8대분류 커버리지 균형
- 난이도 분포 (easy ~40% / medium ~40% / hard ~20%)
- 정치적 균형 (진보/보수 매체)
- 언론사 다양성 (동일 언론사 최대 3건)
- True Negative 최소 5건 (오탐 테스트용)
- 1-8 디지털 최소 2건

선별 후 Gamnamu가 `expected_patterns` / `expected_ethics_codes` 레이블링 진행.

---

## 주요 파일 경로

### 문서 (docs/)
```
/Users/gamnamu/Documents/cr-check/docs/
├── SESSION_CONTEXT_2026-03-23_v9.md            ← 이 문서
├── GOLDEN_DATASET_TASK_INSTRUCTION.md          ← 1차 라운드 지침
├── GOLDEN_DATASET_ROUND2_INSTRUCTION.md        ← 2차 라운드 보충 지침
├── GOLDEN_DATASET_EXTERNAL_RESEARCH_BRIEF.md   ← 외부 리서처 브리프
├── GOLDEN_DATASET_BROADCAST_EXCLUSION_POLICY.md ← 방송 제외 정책
├── GOLDEN_DATASET_ARTICLE_TRACKING_BRIEF.md    ← 역추적 브리프 (리드 A~G)
├── GOLDEN_DATASET_DIGITAL_RESEARCH_BRIEF.md    ← 1-8 보강 리서치 브리프
├── DB_AND_RAG_MASTER_PLAN_v4.0.md              ← RAG 마스터 플랜
└── DB_BUILD_EXECUTION_GUIDE.md                 ← DB 구축 실행 가이드
```

### 데이터 (Golden_Data_Set_Pool/)
```
/Users/gamnamu/Documents/Golden_Data_Set_Pool/
├── golden_dataset_candidates.json          ← 1차 (44건)
├── golden_dataset_candidates.md
├── golden_dataset_candidates_round2.json   ← 2차 (41건)
├── golden_dataset_candidates_round2.md
├── golden_dataset_candidates_external.json ← 외부 정리 (20건)
├── golden_dataset_candidates_digital.json  ← 디지털 보강 (4건) ★신규
├── golden_dataset_candidates_digital.md    ★신규
├── exclusion_flags.json                    ← 방송 제외 플래그
├── problematic_articles_full_catalog.md    ← 문제 기사 전수 분류
├── _raw_research/                          ← 처리 완료된 원본 리서치 (아카이브)
├── [문제 기사]/                            ← PDF 104건
├── [이달의 기자상 수상작]/                 ← CSV + 수집 결과
└── yearly_data/                            ← 심의자료 2021~2024
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **골든 데이터셋 후보 풀은 109건(유효 100건)이다.** 4개 JSON 파일에 분산 저장됨. 작업 ⑤에서 통합해야 함.
2. **1-8 디지털은 7건으로 목표 초과 달성.** 기존 B2-01~03 (3건) + 디지털 보강 D-01~04 (4건).
3. **방송 제외 정책 확정.** 9건 제외. `exclusion_flags.json` 참조.
4. **통합은 제로 베이스에서 수행할 것.** 이전 세션의 판단에 편견 갖지 말고, 데이터 파일 자체만 보고 통합·선별할 것.
5. **v7~v8의 모든 지침(환경변수, Supabase, 코드 접두어 등)은 그대로 유효.** 이 v9는 골든 데이터셋 작업 진척 + 디지털 보강 + 파일 정리만 추가한 것.
6. **로컬 심의자료는 2024년까지만 보유.** 2025년 건은 웹 검색 필수.

### 이전 세션에서 확립된 패턴 (v7에서 이어짐)

v7의 9개 매핑 패턴(context_hint, 상호참조, 수단/목적 분리, PCE 계층 우회, 보호 법익 기반, JEC-3 vs JEC-7, 행위 유형 기반, 절차 윤리, 약한 연결 기각)은 모두 유효.

### 주의사항
- 로컬 파일은 Desktop Commander(MCP)를 통해 읽고 쓸 수 있다.
- **KJA 접두어를 사용하지 마세요.** 기자윤리강령은 `JCE`이다.
- **Supabase Legacy JWT 키 사용 중.** "Disable JWT-based API keys" 누르지 말 것.

---

*이 세션 컨텍스트는 2026-03-23에 갱신되었다.*
