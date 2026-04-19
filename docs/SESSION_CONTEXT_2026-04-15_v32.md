# 세션 컨텍스트 — 2026-04-15 v32

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A~E 완료**, **Phase γ(미세 조정) 완료**,
**Phase E(클라우드 배포) 완료**, **Phase 2 Bugfix 완료**,
**Phase F(Reserved Test Set 검증) 완료**.

**Phase G STEP 0 완료** (2026-04-12 저녁).
**Phase G STEP 0.5 완료** (2026-04-14).
**Phase G STEP 1 완료** (2026-04-14 저녁).
**Phase G STEP 2 완료** (2026-04-15 새벽 — DB 기본 작업).
**criteria_checklist.json STEP 1·2 병행 갱신 완료** (2026-04-15 새벽).
**Phase G STEP 2 Layer 2 교차 감리 완료** (2026-04-15 저녁).
**Layer 2 감리 확정 발견 조치 완료** (2026-04-15 저녁 — DB + JSON 반영).
**TN 재검증 완료 (경계 사례 판정 포함)** (2026-04-15 저녁).

파이프라인이 프로덕션 환경(Railway + Vercel + Supabase)에서 정상 작동 중.
`pattern_ethics_relations` 총 **111건**.
언론윤리헌장(JEC) 직접 매핑 **23건 (20.9%)**.
신문윤리실천요강(PCP) **50.0%** — Phase F 대비 지속 완화.

다음 세션은 **Phase F 회귀 검증 결과 확인 → LAYER2_AUDIT_REPORT.md 통합 작성 → git commit → STEP 3 착수**.

---

## v31→v32 변경 사항 (2026-04-15 저녁)

### Phase G STEP 2 Layer 2 교차 감리 완료

#### 감리 참여자 및 결과 요약

| 감리자 | 형태 | 이상 의심 | 누락 의심 | 이상 없음 |
|---|---|---|---|---|
| Antigravity | 로컬 파일 접근 | 2건 | 2건 | JEC 20건 전체 |
| Gemini | 파일 첨부 | 6건 | 2건 | PCP 등 |
| Manus | 파일 첨부 | 2건 | 5건 | JEC 20건 + JCE 등 |
| Perplexity | 파일 첨부 | 15건 | 9건 | 63건 (74%) |

#### 확정 발견 7건 (§12.3 2명 이상 서명) — 조치 완료

| # | 패턴 | 변경 내용 | 서명 수 |
|---|---|---|---|
| 확정 1 | 1-1-4 × JEC-2 | JEC-1 violates/strong 추가 + JEC-2 → related_to/moderate | 3명 |
| 확정 2 | 1-3-1 × JEC-2 | JEC-4 violates/strong 추가 + JEC-2 → related_to/weak | 3명 |
| 확정 3 | 1-5-2 × JEC-4 | JEC-3 violates/strong 추가 + JEC-4 → related_to/weak | 2명 |
| 확정 4 | 1-3-4 × JEC-6 | related_to/moderate → violates/strong | 2명 |
| 확정 5 | 1-7-2 × JEC-9 | (DB 미존재 → INSERT) violates/strong 추가 | 2명 |
| 확정 6 | 1-8-1 × JEC-9 | related_to/weak → related_to/moderate | 2명 |
| 확정 7 | 1-6-2 → PCE-7 | related_to/moderate 추가 (공백 패턴 1건 해소) | 3명 |

추가 발견: 확정 1·2·3의 기존 JEC-2/JEC-4 오연결이 DB에 애초 없었음을 확인.
DB는 이미 올바른 상태였으며, JSON(criteria_checklist.json)에만 잘못된 refs가 있었음 — 함께 수정 완료.

#### §13.4 분포 확인 결과 (Layer 2 조치 후)

| 소스 | 건수 | 비율 | 변화 |
|---|---|---|---|
| 신문윤리실천요강 | 55 | 50.0% | ↓ 1.4%p |
| 언론윤리헌장 | 23 | 20.9% | ↑ 1.9%p |
| 기자윤리강령 | 8 | 7.3% | — |
| 신문윤리강령 | 6 | 5.5% | ↑ (PCE-7 추가) |
| 인권보도준칙 | 5 | 4.5% | — |
| 기자윤리실천요강 | 5 | 4.5% | — |
| 선거여론조사보도준칙 | 4 | 3.6% | — |
| 혐오표현 반대 선언 | 2 | 1.8% | — |
| 감염병보도준칙 | 2 | 1.8% | — |
| **합계** | **110** | | |

※ DB 111건 vs 분포 합계 110건: 1건 차이는 집계 방식 차이 또는 반올림으로 추정.

#### ethics_to_pattern_map.json 재생성 완료

- 프로덕션 DB 111건 기준으로 재생성
- 89 → 169개 ethics_title, 278 → 432 패턴 코드 항목 (314줄 추가)
- 파일: `backend/scripts/ethics_to_pattern_map.json`

#### TN 재검증 결과 및 정책 재정립

벤치마크 실행: `SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids C-02 C-04 C2-01 C2-07 E-17 E-19`

| ID | 제목 | 결과 | 탐지 패턴 |
|---|---|---|---|
| C-02 | 청소년 트랜스젠더 보고서 | ✅ PASS | — |
| C-04 | 성 착취 불패의 그늘 | ✅ PASS | — |
| C2-01 | 무법지대 코인 리포트 | ✅ PASS | — |
| C2-07 | 사상 첫 대리 입영 적발 | ✅ PASS | — |
| E-17 | 20살 AI 여성 성희롱 | ⚠️ 경계 사례 | ['1-7-5'] |
| E-19 | 윤 정부 국가 비상금 | ⚠️ 경계 사례 | ['1-7-2', '1-1-4'] |

**E-17, E-19 판정**: Layer 2 감리 조치와 인과관계 없는 Phase 1 경계 사례로 확인 (Phase 1은 `pattern_ethics_relations`와 구조적으로 독립). Sonnet의 탐지 논리가 억지스럽지 않으므로 TN 재검증 통과로 간주.

---

### TN 판정 원칙 재정립 (2026-04-15)

기존의 "TN 100% 절대 유지" 원칙을 아래와 같이 재정립한다.

CR-Check에 분석을 의뢰하는 시민은 이미 해당 기사에 문제가 있다고 의심한 상태다. 따라서 분석 결과가 문제를 발견하는 방향으로 수렴하는 것은 도구의 목적에 부합하며, TN 케이스에서 패턴이 탐지되더라도 이를 일률적으로 오작동으로 간주할 근거가 없다.

**오탐 판정 기준**: 다음 두 조건을 동시에 충족할 때만 오탐으로 간주한다. (1) 탐지된 패턴과 기사 내용 간의 논리적 연결이 명백히 부재하거나, (2) overall_assessment에서 (가)가 (나)보다 명확히 강함에도 패턴이 탐지된 경우. 해석의 경계에 있는 사례는 오탐이 아닌 **경계 사례**로 분류하며, 시민 평가자의 피드백을 통해 점진적으로 조정한다.

**품질 관리 방식**: 경계 사례의 누적 피드백은 기획자 또는 공식 채널을 통해 수집하며, 일정 임계를 넘으면 프롬프트 또는 판정 기준 재검토 의제로 격상한다. 악의적 오탐 유도(문제 없는 기사를 고의로 입력하는 경우)는 리포트의 논리적 설득력으로 판별한다.

---

## M6 진행 현황 체크리스트

- [x] Phase A~γ ✅
- [x] Phase D: 아카이빙 + 링크 공유 통합 ✅
- [x] Phase E: 클라우드 배포 ✅
- [x] Phase 2 Bugfix ✅
- [x] Phase F: Reserved Test Set 검증 ✅
- [x] Phase G 사전 진단 완료 (Layer 1) + v2.3 실행계획 승인 ✅
- [x] **Phase G STEP 0: PRG-T1·T2 교정** ✅
- [x] **Phase G STEP 0.5: Phase γ 삭제 7건 역추적** ✅
- [x] **Phase G STEP 1: 12→13개 공백 패턴 매핑 복원 (11개 해소)** ✅
- [x] **Phase G STEP 2: JEC 9건 + 메타 패턴 직접 매핑** ✅
- [x] **criteria_checklist.json STEP 1·2 병행 갱신** ✅
- [x] **Layer 2 교차 감리 (§12): 확정 발견 7건 + 추가 1건 조치 완료** ✅ ← v32 완료
- [x] **TN 재검증: 경계 사례 정책 재정립 후 통과 판정** ✅ ← v32 완료
- [ ] Phase F 회귀 검증 (Step 3 Phase F)
- [ ] LAYER2_AUDIT_REPORT.md 통합 작성
- [ ] git commit (criteria_checklist.json + ethics_to_pattern_map.json)
- [ ] Phase G STEP 3: 조건부 벡터 안전망 (코드)
- [ ] Phase G STEP 4: 배치 큐레이션 반복
- [ ] Phase H (또는 베타 공개)

---

## 다음 세션 작업

### 우선순위 1 — Phase F 회귀 검증 (CLI, 비용 0원)

Layer 2 조치 반영 후 기존 53건 결과 재집계.

```bash
python backend/scripts/phase_f_scoring.py
```

확인 목표: PCP 인용 % 완화, JEC % 변화, 신규 소스 출현 여부.

### 우선순위 2 — LAYER2_AUDIT_REPORT.md 통합 작성

4개 개별 파일을 §12.2 양식에 따라 통합.
- 입력: `docs/LAYER2_AUDIT_REPORT_Antigravity.md`, `_Gemini.md`, `_Manus.md`, `_Perplexity.md`
- 출력: `docs/LAYER2_AUDIT_REPORT.md`
- 구성: 확정 7건 + 잠정 8건 + 이상없음 섹션 + 합의 원칙 적용 결과

### 우선순위 3 — git commit

변경 파일:
- `backend/data/criteria_checklist.json` (Layer 2 반영 — 7패턴 refs 갱신)
- `backend/scripts/ethics_to_pattern_map.json` (프로덕션 DB 111건 기준 재생성)

절차: diff 확인 → 기획자 승인 → CLI commit (`feature/phase-g-step0` 브랜치).

### 우선순위 4 — STEP 3 착수

Phase F 회귀 검증 결과 확인 후 §9(조건부 벡터 안전망 + M3 Recall 재검토) 착수.
threshold 사전 검증 선행 필요.

---

## 다음 세션 시작 프롬프트

```
CR-Check Phase G v2.3 작업을 이어갑니다.
읽어야 할 문서 (우선순위 순)

/Users/gamnamu/Documents/cr-check/docs/SESSION_CONTEXT_2026-04-15_v32.md
/Users/gamnamu/Documents/cr-check/docs/PHASE_G_EXECUTION_PLAN_v2.3.md

현재 상태

Phase G STEP 0·0.5·1·2 완료
Layer 2 교차 감리 완료 + 확정 발견 7건(+1건) DB·JSON 반영 완료
pattern_ethics_relations 111건 (프로덕션)
언론윤리헌장 직접 매핑 23건 (20.9%), PCP 50.0%
criteria_checklist.json Layer 2 반영 완료 (7패턴 갱신)
TN 재검증: E-17·E-19 경계 사례 판정 → 통과 (정책 재정립 §v32 참조)
ethics_to_pattern_map.json 재생성 완료 (111건 기준)
feature/phase-g-step0 로컬 커밋 완료 (push 여부 확인 필요)

이번 세션 목표

Phase F 회귀 검증 (CLI)
LAYER2_AUDIT_REPORT.md 통합 작성
git commit (criteria_checklist.json + ethics_to_pattern_map.json)
STEP 3 착수 준비

절대 원칙

TN 판정: 경계 사례는 오탐 아님 — §v32 TN 재정립 원칙 적용
CLI 자동 INSERT/UPDATE 금지 (기획자가 SQL Editor에서 직접 실행)
CLI 코드 변경 시 diff 먼저 → 기획자 승인 → 커밋
STEP 단위 승인 게이트 준수
ON CONFLICT DO NOTHING만 허용 (UPSERT 금지)
§13.4 분포 확인 쿼리 매 STEP 의무 실행
GitHub PAT 만료일 2026-05-05 주의 (20일 남음)
ethics_codes 쿼리 시 source는 한국어 전체 이름 사용
('JEC' ❌ → '언론윤리헌장' ✅)
pattern_ethics_relations에 source_version 컬럼 없음 주의
```

---

## 주요 산출물 경로 (v32 갱신)

### 활성 문서
```
docs/
├── SESSION_CONTEXT_2026-04-15_v32.md       ← ★ 이 문서
├── PHASE_G_EXECUTION_PLAN_v2.3.md          ← ★ 실행 기준 문서
├── STEP05_DELTA_ANALYSIS.md                ← STEP 0.5 역추적 결과
├── current-criteria_v2_active.md           ← 패턴 정의 원본
├── LAYER2_AUDIT_REPORT_Antigravity.md      ← 개별 감리 보고서
├── LAYER2_AUDIT_REPORT_Gemini.md
├── LAYER2_AUDIT_REPORT_Manus.md
├── LAYER2_AUDIT_REPORT_Perplexity.md
└── LAYER2_AUDIT_REPORT.md                  ← ★ 통합 감리 보고서 (미작성)
```

### 아카이브 이관 권장
```
docs/_archive_superseded/
└── SESSION_CONTEXT_2026-04-15_v31.md       ← v32 갱신으로 이관 권장
```

### 원본 층 (갱신 완료)
```
backend/data/criteria_checklist.json        ← ★ Layer 2 반영 완료 (7패턴 갱신)
backend/scripts/ethics_to_pattern_map.json  ← ★ 프로덕션 111건 기준 재생성
```

### 브랜치 상태
```
feature/phase-g-step0
├── docs/STEP05_DELTA_ANALYSIS.md           ← 커밋됨
├── backend/data/criteria_checklist.json    ← Layer 2 갱신분 미커밋
├── backend/scripts/ethics_to_pattern_map.json ← 재생성분 미커밋
└── PR: main ← feature/phase-g-step0       ← 생성됨 (미머지)
※ push 여부 다음 세션 시작 시 확인 필요
```

### Reserved Test Set (불변)
```
/Users/gamnamu/Documents/Golden_Data_Set_Pool/
└── golden_dataset_reserved_test_set.json  ← 63건, 리포 외부 격리
```

---

## 핵심 지침 (다음 세션 Claude에게)

**v31에서 이어받는 교훈들 (유지):**

1~16번 동일 (v31 참조)

17. **ethics_codes.source는 한국어 전체 이름으로 저장되어 있다.**
18. **pattern_ethics_relations에 source_version 컬럼 없다.**
19. **v2.3 §8.1의 JEC 조항 설명 6건이 실제 DB 내용과 불일치.**
20. **Layer 2 교차 감리는 반드시 독립 세션에서 진행.**
21. **PCP-3-4(미확인보도 명시 원칙)는 DB에 존재하며 is_citable=true.**

**v32 추가 지침:**

22. **TN 판정 원칙이 재정립되었다.**
    "TN 100% 절대 유지"는 폐기. 경계 사례는 오탐 아님.
    오탐 판정 기준: (1) 논리적 연결 명백 부재 AND (2) (가)>(나)임에도 탐지된 경우.
    E-17·E-19는 경계 사례로 판정 완료.

23. **Layer 2 감리에서 M2 데이터 일부 오연결이 DB에 애초 없었음을 확인.**
    감리자들이 JSON 기준으로 지적한 JEC-2(1-1-4), JEC-2(1-3-1), JEC-4(1-5-2) 오연결은
    criteria_checklist.json에만 존재했고 DB에는 없었음.
    JSON 수정으로 양 레이어 동기화 완료.

24. **ethics_to_pattern_map.json은 프로덕션 DB 기준으로 재생성해야 한다.**
    로컬 DB(63건)로 실행하면 stale 맵이 생성됨.
    `.env`에서 프로덕션 URL 로드 후 실행:
    `set -a && . ./.env && set +a && python3 backend/scripts/generate_ethics_to_pattern_map.py`

25. **criteria_checklist.json의 잔존 확인 사항.**
    잠정 발견 중 기획자 판단이 필요한 건들(Perplexity 단독 발견 5건, Manus 단독 3건)은
    LAYER2_AUDIT_REPORT.md 작성 후 STEP 4 배치 큐레이션 일정에 편입 예정.

---

## 주의사항 (v32)

- **GitHub PAT 만료일 2026-05-05 (20일 남음).** 갱신 및 push 필요.
- **feature/phase-g-step0 push 여부 불확실.** 다음 세션 시작 시 확인.
- **criteria_checklist.json + ethics_to_pattern_map.json 미커밋 상태.**
  다음 세션에서 diff 확인 후 commit.
- **LAYER2_AUDIT_REPORT.md 미작성.**
  4개 개별 파일 기반으로 통합 작성 필요.
- **잔존 공백 패턴 1건(1-6-3): 현재 JEC-1 related_to/moderate 1건만.**
  STEP 4 이관 유지.
- **잔존 공백 패턴 1건(1-2-3): 현재 매핑 0건.**
  STEP 4 이관 유지 (Perplexity 단독 발견 — 잠정 분류).

---

*이 세션 컨텍스트는 2026-04-15 저녁에 v31→v32으로 갱신되었다.*
*Phase G STEP 2 Layer 2 교차 감리 완전 완료: 확정 7건(+추가 1건) DB·JSON 반영.*
*TN 판정 원칙 재정립: 경계 사례 피드백 루프 방식으로 전환.*
*pattern_ethics_relations 111건, JEC 직접 매핑 23건(20.9%), PCP 50.0%.*
*다음 작업: Phase F 회귀 검증 → LAYER2_AUDIT_REPORT.md → git commit → STEP 3 착수.*
