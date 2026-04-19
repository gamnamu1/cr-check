# 세션 컨텍스트 — 2026-04-19 v33

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M6 Phase γ + Phase D·E·F 완료**.
**Phase G STEP 0·0.5·1·2 완료** + **Layer 2 교차 감리 전체 완결**.
관련 공식 문서 모두 main 브랜치에 머지 완료 (PR #38, 머지 커밋 `698cf99`).
프로덕션(https://cr-check.vercel.app) 자동 배포 완료.

`pattern_ethics_relations` **111건** (프로덕션 DB).
PCP **50.0%** (Phase F 82.5% 대비 △32.5%p 완화).
JEC 직접 매핑 **23건 (20.9%)**.
잔존 공백 말단 패턴 2건(1-2-3 무매핑, 1-6-3 단일 매핑) — STEP 4 이관.

다음 진입점: **Phase G STEP 3 §9.1 (M3 Recall 재측정)**.

---

## v32 → v33 변경 사항 (2026-04-19)

### Layer 2 감리 공식 문서화 완료

4개 독립 감리자(Antigravity · Gemini · Manus · Perplexity) 결과를 §12.2 양식으로 통합한 `LAYER2_AUDIT_REPORT.md` 작성(331줄, 10개 섹션). 확정 발견 7건 + 추가 발견 1건의 반영 상태 기록. 잠정 발견 21건(Manus 6 + Perplexity 15)을 우선순위 P1/P2/P3로 분류하여 STEP 4 이관 백로그 확정.

### 문서 체계 정비 + git 이력 정리

구버전 8건 삭제 + 참고자료 3건 `docs/_reference/`로 이동. `.gitignore`에 아카이브·진단 로그 공간 규칙 추가. 위 변경을 4개 의미 단위 커밋(`.gitignore` → 문서 정리 → STEP 2 공식 문서화 → POST_V4_0_AUDIT 기록)으로 분리하여 PR #38 생성·머지. `feature/phase-g-step0` 브랜치 삭제 완료.

### 개인 스크래치 공간 신설

`docs/_scratch/` 폴더를 `.gitignore`에 등록. 일회성 메모·초안·실험 기록의 자유 작성 영역 확보. Git 관리 대상에서 제외되어 작성·편집·삭제 시 이력이 남지 않음. 공식화 가치 있는 문서는 `docs/` 직속으로 이동하면서 Git 관리 편입.

---

## Phase G 진행 현황 체크리스트

- [x] Phase A~γ ✅
- [x] Phase D: 아카이빙 + 링크 공유 통합 ✅
- [x] Phase E: 클라우드 배포 ✅
- [x] Phase 2 Bugfix ✅
- [x] Phase F: Reserved Test Set 검증 ✅
- [x] Phase G STEP 0·0.5·1·2 완료 + Layer 2 감리 전체 완결 ✅
- [x] Layer 2 감리 공식 문서화 + main 머지 ✅ ← v33 완료
- [ ] **Phase G STEP 3 §9.1 — M3 Recall 재측정** ← 다음 세션 최우선
- [ ] Phase G STEP 3 §9.2 — threshold 사전 검증
- [ ] Phase G STEP 3 §9.2 — 조건부 벡터 안전망 구현 (pipeline.py)
- [ ] Phase G STEP 3 완료 게이트: Antigravity 코드 감리 + 골든셋 재검증 + PR 머지
- [ ] Phase G STEP 4: 배치 큐레이션 (잠정 21건 + Q18 공백 해소)
- [ ] Phase H 또는 베타 공개 (M3 Recall 결과에 따라 분기)

---

## 다음 세션 작업

### 🎯 최우선 — STEP 3 §9.1 M3 Recall 재측정

**목적**: M2 당시 "119 → 38 압축"은 조건부 통과된 결정이었고, 그 재검토 게이트가 트리거 조건 없이 분실된 채 남아 있었다. 이번 측정이 그 게이트를 공식적으로 다시 여는 절차다. 결과에 따라 Phase H(38→119 세분화) 진입 여부가 결정된다.

**실행 명령 (후보)**:
```bash
cd /Users/gamnamu/Documents/cr-check
python backend/scripts/benchmark_recall_v2.py
# 실제 스크립트 경로·이름은 세션 시작 시 backend/scripts/ 하위 확인 필요
```

**측정 지표**:
- Recall@10 (핵심 판정 지표)
- Candidate Recall
- Final Precision / F1 (보조 지표)

**판정 분기**:

| Recall@10 | 조치 |
|---|---|
| ≥ 기획자 기준선 | "38 패턴 유지"를 **기록된 판단**으로 확정. Phase H는 STEP 4 배치 큐레이션 지속으로 대체. |
| < 기획자 기준선 | 38 → 119 패턴 세분화 마이그레이션 설계 착수. Phase H 본격 진입. |

**선결 사항 (★)**: **기획자 기준선 수치 확정이 선행 필요**. 세션 시작 시 감독·감리와 기획자가 협의하여 정하고, 결과 기록 시 "기준선 X를 근거로 판정했다"는 이력을 반드시 남김. 과거 "M3에서 재검토" 약속이 트리거 조건 없이 분실된 교훈을 반복하지 않기 위함.

**비용**: 로컬 벤치마크이므로 약 0원.

---

### 🔧 차순위 — STEP 3 §9.2 threshold 사전 검증

**목적**: 조건부 벡터 안전망을 코드에 얹기 전, 적정 threshold 값을 실험으로 도출. 기존 파이프라인의 0.2 threshold는 너무 낮아 TN 케이스 오매칭 위험이 컸음.

**작업 내용**:
1. 패턴 description ↔ `ethics_codes.full_text` 간 코사인 유사도 매트릭스 생성
2. 골든셋 정답 패턴-규범 쌍의 유사도 분포 확인
3. TN 케이스에서 잘못 매칭될 수 있는 규범의 유사도 상한 확인
4. 최종 권장값 도출 (v2.3 §9.2 지침 기준 **0.5 이상 예상**)

**실행 담당**: CLI가 매트릭스 계산 코드 작성, 기획자 검토 후 값 확정.

**STEP 1·2 완료 효과**: 데이터 층 편중이 해소되었으므로 벡터 안전망의 trigger 빈도가 감소할 것으로 예상. 그럼에도 장기 안전망으로 구현한다.

---

### 🛠️ 본작업 — pipeline.py 수정 + PR 사이클

§9.1·§9.2 결과에 따라 `pipeline.py`에 조건부 벡터 안전망 로직을 추가한다. **Phase G 들어 처음으로 코드가 바뀌는 단계**이므로 신중한 감리 절차가 필요.

**작업 흐름**:
1. 기획자가 새 feature 브랜치 생성 지시 (예: `feature/phase-g-step3-vector-fallback`)
2. CLI가 코드 변경 → **diff 선제시** → 기획자 승인 → 커밋
3. 단위 테스트 작성 + 로컬 실행
4. PR 생성 → **Antigravity 코드 감리**
5. 감리 피드백 반영 → 골든셋 재검증 (TN 6/6 유지 필수)
6. 기획자 최종 승인 → main 머지

**엄수 사항**:
- CLI 자동 git add/commit 금지 (diff 선제시 원칙)
- `main` 직접 push 금지 — PR 경유
- 골든셋 TN 100% 유지 (경계 사례 정책은 v32 TN 재정립 원칙 적용)

---

## 다음 세션 시작 프롬프트

```
CR-Check Phase G v2.3 작업을 이어갑니다.

## 읽어야 할 문서 (우선순위 순)
1. /Users/gamnamu/Documents/cr-check/docs/SESSION_CONTEXT_2026-04-19_v33.md
2. /Users/gamnamu/Documents/cr-check/docs/PHASE_G_EXECUTION_PLAN_v2.3.md (§9 STEP 3)

## 현재 상태
- Phase G STEP 0·0.5·1·2 완료 + Layer 2 감리 공식 문서화 완결 + main 머지
- pattern_ethics_relations 111건, PCP 50.0%, JEC 20.9%
- 다음 진입점: STEP 3 §9.1 M3 Recall 재측정

## 이번 세션 목표
- STEP 3 §9.1 Recall 기준선 협의 및 측정 실행
- 결과에 따라 §9.2 threshold 검증 진입 여부 결정

## 절대 원칙 (v32 승계 + v33 신규)
- TN 판정: 경계 사례는 오탐 아님 (v32 재정립 원칙)
- CLI 자동 INSERT/UPDATE 금지 — 기획자 SQL Editor 직접 실행
- CLI 코드 변경 시 diff 먼저 → 기획자 승인 → 커밋
- STEP 단위 승인 게이트 준수
- STEP 3는 코드 변경 단계 — Antigravity 감리 필수
- main 직접 push 금지 — PR 경유
- ON CONFLICT DO NOTHING만 허용 (UPSERT 금지)
- M3 Recall 기획자 기준선은 세션 시작 시 협의 후 확정
- docs/_scratch/ 는 Git 미관리 — 자유 작성 가능
- GitHub PAT 만료일 2026-05-05 (15일 남음)
```

---

## 절대 원칙 (v32 승계 + v33 신규)

**v32에서 승계하는 원칙들:**

22. **TN 판정 원칙 재정립** — 경계 사례는 오탐 아님. 오탐 판정 기준: (1) 논리적 연결 명백 부재 AND (2) (가)>(나)임에도 탐지된 경우.
23. **Layer 2 감리에서 M2 데이터 일부 오연결이 DB에 애초 없었음 확인** — JSON만의 오연결이었으며 동기화 완료.
24. **`ethics_to_pattern_map.json`은 프로덕션 DB 기준으로 재생성해야 한다** — 로컬 DB(63건)로 실행하면 stale 맵 생성.
25. **잠정 발견 21건은 STEP 4 배치 큐레이션에서 처리** — 이번 세션 범위 외.

**v33 신규 원칙:**

26. **STEP 3는 Phase G 최초의 코드 변경 단계** — Antigravity 코드 감리 필수. diff 선제시 → 기획자 승인 → 커밋 순서 엄수.
27. **M3 Recall 기획자 기준선은 미정** — 세션 시작 시 협의하여 확정하고 판정 이력에 근거로 기록. "M3에서 재검토" 약속이 트리거 없이 분실된 교훈 반복 방지.
28. **`docs/_scratch/` 신설** — Git 관리 대상 외 개인 작업공간. 일회성 메모·초안·실험 기록 용도. 공식화 가치 있는 문서는 `docs/` 직속으로 이동하면서 Git 관리 편입.

---

## 주요 산출물 경로 (v33 갱신)

### 활성 문서
```
docs/
├── SESSION_CONTEXT_2026-04-19_v33.md       ← ★ 이 문서
├── PHASE_G_EXECUTION_PLAN_v2.3.md          ← ★ 실행 기준 문서
├── LAYER2_AUDIT_REPORT.md                  ← Phase G STEP 2 공식 감리 기록
├── LAYER2_AUDIT_REPORT_Antigravity.md      ← 감리 원본 4건 (추적용 보존)
├── LAYER2_AUDIT_REPORT_Gemini.md
├── LAYER2_AUDIT_REPORT_Manus.md
├── LAYER2_AUDIT_REPORT_Perplexity.md
├── M6_BENCHMARK_RESULTS.md                 ← TN 재검증 결과
├── DB_AND_RAG_POST_V4_0_AUDIT_v1.md        ← 롤업 표현 문제 사후 감리
├── STEP05_DELTA_ANALYSIS.md                ← Phase γ 삭제 7건 역추적
├── current-criteria_v2_active.md           ← 패턴 정의 원본
└── _reference/
    ├── DB_AND_RAG_MASTER_PLAN_v4.0.md
    ├── PHASE_F_FINAL_REPORT.md
    └── ethics_codes_mapping.json
```

### 아카이브 이관 권장
```
docs/_archive_superseded/
└── SESSION_CONTEXT_2026-04-15_v32.md       ← v33 갱신으로 이관 권장
```

### 개인 작업공간 (Git 미관리)
```
docs/_scratch/           ← 일회성 메모·초안·실험 (새 세션에서 자유 활용)
```

### 원본 층 (변경 없음)
```
backend/data/criteria_checklist.json        ← Layer 2 반영 완료
backend/scripts/ethics_to_pattern_map.json  ← 프로덕션 111건 기준
```

### Git 상태
- main 브랜치: 최신 커밋 `698cf99` (PR #38 머지) + v33 갱신 커밋 예정
- `feature/phase-g-step0` 브랜치 삭제 완료
- 다음 작업용 브랜치: 세션 시작 시 `feature/phase-g-step3-*` 형태로 신규 생성

### Reserved Test Set (불변)
```
/Users/gamnamu/Documents/Golden_Data_Set_Pool/
└── golden_dataset_reserved_test_set.json  ← 63건, 리포 외부 격리
```

---

## 주의사항 (v33)

- **GitHub PAT 만료일 2026-05-05 (15일 남음)**. STEP 3 진행 중 만료 가능성 있음 — 세션 초반 갱신 권장.
- **STEP 3 §9.1 Recall 기준선 미정** — 세션 시작 시 기획자와 협의 필요.
- **잠정 발견 21건은 STEP 4 범위** — 이번 세션에서는 다루지 않음.
- **`ethics_codes.source`는 한국어 전체 이름으로 저장됨** (`'JEC'` ❌ → `'언론윤리헌장'` ✅).
- **`pattern_ethics_relations`에 `source_version` 컬럼 없음** 주의.
- **STEP 3 코드 변경은 feature 브랜치 경유 의무** — main 직접 push 금지.
- **`docs/_scratch/`는 Git 미관리** — CLI가 참조·편집·삭제해도 이력 무영향. 단 `git add -f`로 강제 추가 시 예외 발생.

---

*이 세션 컨텍스트는 2026-04-19에 v32→v33으로 갱신되었다.*
*Phase G STEP 2 완결 + Layer 2 감리 공식 문서화 + main 머지 완료.*
*pattern_ethics_relations 111건, JEC 직접 매핑 23건(20.9%), PCP 50.0%.*
*다음 작업: Phase G STEP 3 §9.1 (M3 Recall 재측정) 착수.*
