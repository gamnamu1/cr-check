# 세션 컨텍스트 — 2026-04-12 v27

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A~E 완료**, **Phase γ(미세 조정) 완료**,
**Phase E(클라우드 배포) 완료**, **Phase 2 Bugfix 완료**,
**Phase F(Reserved Test Set 검증) 완료**.

2026-04-12 오전~저녁에 걸쳐 **Phase G 사전 진단(Layer 1 정량 감리) 완료**,
**Phase G 실행계획 v2.0 작성 완료**. 다음 세션은 **STEP 0 착수**부터.

파이프라인이 프로덕션 환경(Railway + Vercel + Supabase)에서 정상 작동 중이며,
TN 100% 정확, 정직한 침묵 패턴 확인. **베타 공개 가능한 안전 프로파일** 유지.

### v26→v27 변경 사항 (2026-04-12)

**Phase G 사전 진단 — Layer 1 정량 감리 완료 및 v2.0 재설계**

하루 동안 PRE-STEP → Q0 스키마 → 원본 파일 대조 → Q17·Q18·Q20 실측까지
진행하며, Phase G의 작업 대상과 원인 계통을 정량 데이터로 확정.
v1.0 실행계획을 v2.0으로 재작성.


**1. PRE-STEP — ethics_codes 누락 임베딩 점검 (2026-04-12 오전):**

- Supabase SQL 쿼리로 is_active=TRUE이고 text_embedding IS NULL인 조항
  21건 확인
- 분류: 서문/전문 14건 + 부칙·운영 조항 5건 + 평화통일 보도 준칙 총강 2건
- 서문·부칙 19건은 의도된 비인용 처리로 타당
- 평화통일 보도 준칙 PRG-T1, PRG-T2만 일관성 깨짐 식별
  (같은 규범의 PRG-T3·T4·T5는 is_citable=TRUE)

**2. M2 시드 누락 감리 설계 (2026-04-12 오후):**

기획자 제안으로 M2 시드 고고학(seed archaeology) 감리 3계층 설계 합의:
- Layer 1: 정량 무결성 감리 (기계적, SQL 쿼리)
- Layer 2: 원본 대조 감리 (정성적, 모든 감리자가 14개 규범 독립 검토 후 교차)
- Layer 3: 시드 스크립트 감리 (코드 고고학, Antigravity 담당)

**3. Layer 1 정량 감리 실행 및 결과 (2026-04-12 오후~저녁):**

Q0 스키마 확인 → 컬럼명 보정 (parent_code → parent_code_id,
patterns에는 is_active 컬럼 없음 등)

Q16 패턴 카운트 → **38개** (초기 가설 "119개"는 세션 간 요약 혼동에서 비롯).
원본 파일 직접 확인(docs/current-criteria_v2_active.md,
backend/data/criteria_checklist.json 등) 결과, 38개 = 8 대분류 + 30 말단
패턴이 설계 그 자체임을 확증.

**→ "81개 누락" 가설 완전 무효. Gamnamu 작업은 설계대로 구현돼 있음.**

Q2 (citable=TRUE인데 임베딩 없음) → 0건. 임베딩 측면 클린.

Q5 (은근히 잠긴 본문) → 7건 중 EPG-27·28·DRG-40~42는 부칙성 타당.
**실제 이상은 PRG-T1·T2 2건뿐** (오전 발견 재확증).

Q16-추가 (patterns 임베딩) → 38개 중 10개 MISSING.
Level 1 대분류 8개 + 메타 패턴 2개(1-4-1, 1-4-2)는 설계상 임베딩 불필요로 판단.

Q17 (매핑 0건 패턴) → 20건. Level 1 대분류 8개 제외 시
**실제 공백 말단 패턴 12개** 특정:
```
1-1-2 이차 자료 의존          1-5-1 취재 과정의 인권 침해
1-1-3 오보 관리 부실          1-5-4 사법 절차 존중 위반
1-2-2 책임 회피 표현          1-6-2 전문성 부족
1-3-2 편향적 보도             1-6-3 현장성 부족
1-3-3 인과관계 왜곡           1-7-1 사실과 의견을 뒤섞는 주관적 술어
1-3-5 보도 회피와 물타기      1-7-6 명료성을 해치는 표현
                              1-8-1 소셜미디어 활용 윤리
```

Q18 (미인용 조항) → **351건 전체**, 소스별 분포:
```
인권보도준칙       92  자살예방 보도준칙 4.0  19
신문윤리실천요강   52  기자윤리강령           10
재난보도준칙       39  언론윤리헌장            9  ← Tier 1 완전 공백
선거여론조사준칙   24  감염병보도준칙          8
평화통일 보도 준칙 23  신문윤리강령            7
자살보도 윤리강령  22  혐오표현 반대 선언      6
기자윤리실천요강   20
군 취재·보도 기준  20
```

Q20 (strength × 소스) → 현재 매핑 63건의 분포:
```
신문윤리실천요강   strong 44 + moderate 6 + weak 2 = 52  (82.5%)
신문윤리실천요강 외 소스들   11  (17.5%)
언론윤리헌장(JEC) 직접 매핑   0
```

**→ Phase F 관측 PCP 69.3% + JEC 25.2%의 실체 규명:**
- PCP 82.5% 집중은 매핑 층의 실측
- JEC 25.2%는 전부 parent_chain 재귀 CTE의 자동 롤업 결과
- weak 매핑은 단 2건 → 편중 원인은 "약한 매핑으로 밀림"이 아니라 **완전 공백**


**4. 편중의 3층 계통 규명:**

```
[1층: 원본 설계]
  criteria_checklist.json의 ethics_code_refs
  → 38 refs 분포: JEC 65.8% / PCP 28.9% / JCE 5.3%
  → 14개 규범 중 단 3개만 참조, 11개 규범 원천 부재
       ↓
[2층: M2 시드 전파]
  seed 스크립트가 원본 refs 중 일부 누락 + PCP 쪽 별도 확장
  → pattern_ethics_relations 63건, PCP 82.5% 집중
       ↓
[3층: 파이프라인 증폭]
  get_ethics_for_patterns()의 parent_chain 재귀 CTE (depth<5)
    direct_codes: PCP만 히트
    parent_chain: PCP → JEC 자동 롤업
  → Phase F 관측: PCP 69.3% + JEC 25.2% = 94.5%
```

**해결 설계**: 1층과 2층을 함께 손본다. 3층(코드)은 그대로 둔다.
parent_chain은 정상 증폭기이며, 입력이 편중되지 않으면 출력도 편중되지 않음.

**5. 감리자 교차 피드백 확증:**

친구 감리자(Manus/Perplexity/Gemini 등)의 진단 두 건 모두 코드·데이터로 확증됨:
- `get_ethics_for_patterns()` SQL 함수 실제 로직 확인 완료
  (supabase/migrations/20260328000000_create_cr_check_schema.sql, line 254~320)
- direct_codes CTE + parent_chain 재귀 CTE 구조 그대로 작동 확인

또한 친구 감리자의 쿼리 세트 검토 의견(Q7 컬럼명, Q15 is_active, Q19·Q20 추가)
모두 반영하여 진단 정확도 향상.

**6. Phase G 실행계획 v2.0 작성 완료:**

docs/PHASE_G_EXECUTION_PLAN_v2.0.md (17 섹션, 약 460줄).
v1.0의 규범 중심 설계를 패턴 중심으로 전환.

주요 변경:
- STEP 0 신설 (PRG-T1·T2 교정)
- STEP 1 패턴 중심 재설계 (12개 공백 패턴 × 후보 규범 매트릭스 §6.2)
- STEP 2 JEC 9건 직접 매핑 핵심화 (§7.2)
- 병행 트랙 추가: criteria_checklist.json 원본 층 동시 갱신 (§8)
- Layer 2 교차 감리 구조화: 모든 감리자가 14개 규범 독립 검토, 2명 이상 서명
  필요 (§11)

예상 효과 (STEP 1·2 완료 시점):
- pattern_ethics_relations: 63 → 110~130건
- 매핑 소스 수: 5 → 9~11개
- 매핑 0건 말단 패턴: 12 → 4 이하
- PCP 인용 비율: 69.3% → 45~55% 예상

**7. 기획자 승인:**
v2.0 문서 전체 검토 후 승인. STEP 0부터 착수 결정.

---

## M6 진행 현황 체크리스트

- [x] Phase A~γ ✅
- [x] Phase D: 아카이빙 + 링크 공유 통합 ✅
- [x] Phase E: 클라우드 배포 ✅
- [x] Phase 2 Bugfix ✅
- [x] Phase F: Reserved Test Set 검증 ✅
- [x] **Phase G 사전 진단 완료 (Layer 1) + v2.0 실행계획 승인** ← v27 완료
- [ ] **Phase G STEP 0: PRG-T1·T2 교정** ← 다음 세션 첫 작업
- [ ] Phase G STEP 1: 12 공백 패턴 매핑 복원
- [ ] Phase G STEP 2: JEC 9건 + 메타 패턴 직접 매핑
- [ ] Phase G STEP 3: 조건부 벡터 안전망 (코드)
- [ ] Phase G STEP 4: 배치 큐레이션 반복
- [ ] Phase H (또는 베타 공개): 기타 마무리

---

## 다음 세션 작업 (Phase G STEP 0)

### STEP 0 목표 (소요 30분, 위험도 매우 낮음)

PRG-T1, PRG-T2의 `is_citable`을 TRUE로 승격하고 임베딩 2건 신규 생성.
PHASE_G_EXECUTION_PLAN_v2.0.md §5 전체 참조.

### STEP 0 실행 절차

**[1단계] 기획자 → Supabase SQL Editor 직접 실행:**
```sql
UPDATE ethics_codes
SET is_citable = TRUE,
    updated_at = NOW()
WHERE source = '평화통일 보도 준칙'
  AND code IN ('PRG-T1', 'PRG-T2');

-- 확인
SELECT code, title, is_citable,
       CASE WHEN text_embedding IS NULL THEN 'MISSING' ELSE 'OK' END AS emb
FROM ethics_codes
WHERE source = '평화통일 보도 준칙'
  AND code IN ('PRG-T1', 'PRG-T2');
```

**[2단계] 기획자 → CLI에게 임베딩 생성 요청 (v2.0 §5.3 프롬프트 사용)**

backend/scripts/generate_embeddings.py가 is_citable=TRUE이고
text_embedding IS NULL인 조항만 대상으로 하는지 사전 확인 후 실행.

**[3단계] Claude 감독·감리 → 결과 검증:**
```sql
SELECT code, title, is_citable,
       CASE WHEN text_embedding IS NULL THEN 'MISSING' ELSE 'OK' END AS emb
FROM ethics_codes
WHERE source = '평화통일 보도 준칙'
ORDER BY code;
```
기대: PRG-T1·T2 모두 is_citable=TRUE, emb=OK.

**[4단계] 기획자 → 골든셋 TN 5건 선택적 재측정:**
매핑 변경이 아니라 임베딩 추가만 있으므로 TN 영향 거의 없음 예상.
다만 확인 차원에서 선별 재측정 권장 (§12).

**[5단계] STEP 0 완료 게이트 → STEP 1 진입 결정**

### STEP 0 완료 기준 체크리스트

- [ ] PRG-T1, PRG-T2의 `is_citable = TRUE`
- [ ] 두 조항 모두 `text_embedding IS NOT NULL`
- [ ] 골든셋 TN 5건 정답 유지 확인
- [ ] `criteria_checklist.json` PRG 관련 refs 존재 여부 점검
  (원본에 이미 refs가 있는지 확인 후 필요 시 갱신)

---

## 다음 세션 시작 프롬프트

```
CR-Check Phase G STEP 0 작업을 시작합니다.

## 읽어야 할 문서 (우선순위 순)
1. /Users/gamnamu/Documents/cr-check/docs/SESSION_CONTEXT_2026-04-12_v27.md
2. /Users/gamnamu/Documents/cr-check/docs/PHASE_G_EXECUTION_PLAN_v2.0.md
   → 이 문서의 §5(STEP 0 상세)를 기준으로 진행

## 현재 상태
- Phase F까지 완료, 프로덕션 정상 가동 중
- Phase G v2.0 실행계획 작성 및 기획자 승인 완료
- Layer 1 정량 감리로 작업 대상 확정:
  · 실제 이상 1건: PRG-T1, PRG-T2 (is_citable=FALSE 일관성 깨짐)
  · 공백 말단 패턴 12개 특정 (STEP 1 대상)
  · 매핑 공백 351건, 9개 규범 완전 공백 (STEP 1~4 대상)
  · 편중의 3층 계통 규명 (원본-시드-파이프라인)

## 이번 세션 목표
STEP 0 실행 (v2.0 §5 전체 참조):
- PRG-T1, PRG-T2의 is_citable=TRUE 승격
- 임베딩 2건 신규 생성
- 검증 → STEP 1 진입 준비

## 절대 원칙
- TN 100% 유지
- CLI 자동 INSERT/UPDATE 금지 (기획자가 SQL Editor에서 직접 실행)
- STEP 단위 승인 게이트 준수
- GitHub PAT 만료일 2026-05-05 주의 (23일 남음)
```

---

## 핵심 지침 (다음 세션 Claude에게)

**오늘 세션의 가장 중요한 교훈**: 감독·감리(Claude)는 자신의 메모리 요약에
의존하지 말고, **반드시 원본 파일을 먼저 확인한 뒤 진단한다.** 오늘 오후
"81개 패턴 누락" 오경보가 발생한 원인은 "119개"라는 메모리 요약치가
원본 확인 없이 사용된 것이었음. Gamnamu의 의구심 덕에 바로잡혔으나,
반복되지 않도록 주의.

1. **Layer 1 정량 감리 완료. 실제 이상은 PRG-T1·T2 1건.**
   나머지는 모두 설계대로 구현된 상태의 자연스러운 분포이거나
   의도된 비인용 처리. STEP 0의 범위는 정확히 2건.

2. **편중은 3층 계통. 1층·2층을 함께 손보면 3층은 저절로 풀린다.**
   get_ethics_for_patterns()의 parent_chain은 정상 증폭기이므로
   건드리지 않는다. STEP 3 벡터 안전망 구현 시에도 이 함수는 유지.

3. **매핑은 패턴 중심으로 복원한다.** 12개 공백 말단 패턴이 v2.0 §6.2에
   매트릭스로 정리돼 있음. 기획자 큐레이션의 출발 지도로 사용.

4. **원본 층 병행 갱신 잊지 말 것.** DB에 INSERT할 때마다
   criteria_checklist.json의 해당 패턴 ethics_code_refs도 갱신해야
   다음 시드 재실행 시 편중이 재생산되지 않음. v2.0 §8 참조.

5. **STEP 단위 승인 게이트 엄격 적용.** CLI는 INSERT 초안만 생성,
   실제 DB 변경은 기획자가 SQL Editor에서 직접 실행.

6. **친구 감리자들(Manus, Perplexity, Gemini, Antigravity)의 의견은
   교차 확증 수단으로 활용한다.** 오늘 친구 감리자의 쿼리 검토 의견
   (Q7 컬럼명, Q15 is_active, Q19·Q20 추가)이 진단 정확도를 크게
   높였음. 이런 교차가 Layer 2 감리의 핵심 방식이 됨.

7. **감정적 페이싱도 중요.** 오늘 Gamnamu는 PRG-T1·T2 발견 → "3주의 작업이
   32% 기반 위에 있었다"는 오경보 → 원본 확인으로 무효화 → v2.0 재작성까지
   큰 감정의 파고를 통과했음. STEP 진행 시 무리하지 않는 페이스 유지.

---

## 주요 산출물 경로 (v27 갱신)

### Phase G v2.0 산출물 (신규)
```
docs/
├── SESSION_CONTEXT_2026-04-12_v27.md        ← ★ 이 문서
├── PHASE_G_EXECUTION_PLAN_v2.0.md           ← ★ 실행 기준 문서
└── PHASE_G_EXECUTION_PLAN_v1.0.md           ← 참고용 보존
```

### Layer 1 정량 감리 CSV 결과 (참고)
오늘 실행한 쿼리 결과 CSV 파일들은 대화 맥락에 첨부된 상태.
핵심 수치는 이 문서 §v26→v27 변경 사항에 인용.

### Phase F 산출물 (v26 계승)
```
backend/scripts/
├── phase_f_validation.py          ← 블라인드 실행기
├── phase_f_scoring.py             ← 사후 집계기
├── generate_ethics_to_pattern_map.py ← DB → 매핑 사전 자동 생성
└── ethics_to_pattern_map.json     ← 89 entries (STEP 1 완료 후 재생성 예정)

backend/diagnostics/phase_f/
├── injected/                      ← gitignore (Reserved Test Set 주입 경로)
├── run_20260411_164820/           ← 파일럿 5건
├── run_20260411_172053/           ← 본실행 58건 + _scoring.json
└── pilot_log.txt / full_log.txt   ← 실행 로그
```

### Reserved Test Set 보관 (불변)
```
/Users/gamnamu/Documents/Golden_Data_Set_Pool/
└── golden_dataset_reserved_test_set.json  ← 63건, v2, 리포 외부 격리
```

### 원본 층 참조 파일 (Phase G에서 갱신 대상)
```
docs/current-criteria_v2_active.md           ← 패턴 정의 원본 (MD)
backend/data/criteria_checklist.json         ← ★ 원본 설계 JSON (1층)
backend/scripts/ethics_to_pattern_map.json   ← 89 entries, STEP 후 재생성
docs/ethics_codes_mapping.json               ← 394 entries ethics_codes 정의
```

---

## 주의사항 (v26 계승 + v27 추가)

(v26의 모든 주의사항 유지)

**v27 추가 주의사항:**

- **"119" 또는 다른 수치 인용 시 반드시 원본 확인 필수.**
  메모리 요약치를 근거로 추론하지 말 것. 오늘 오경보의 원인.

- **원본 파일 위치 숙지:**
  - `docs/current-criteria_v2_active.md` — 패턴 정의 (MD)
  - `backend/data/criteria_checklist.json` — 원본 설계 JSON (1층)
  - `backend/scripts/ethics_to_pattern_map.json` — Phase F 매핑 사전
  - `docs/ethics_codes_mapping.json` — 394 entries ethics_codes

- **get_ethics_for_patterns() 함수는 그대로 둔다.**
  위치: `supabase/migrations/20260328000000_create_cr_check_schema.sql`
  line 254~320. parent_chain 재귀 CTE는 정상 증폭기.

- **DB INSERT 시 criteria_checklist.json 갱신 병행.**
  v2.0 §8 참조. 식별자 변환 맵 확정 필요 건은 CLI가 조회로 확정.

- **ethics_code_hierarchy 테이블 존재 확인됨** (Q0-보완 결과).
  parent_code_id, child_code_id, relation_note 컬럼 구성.
  Layer 2 감리 시점에 무결성 점검(Q19) 실행 예정.

- **Q1 계열·Q19 쿼리는 Layer 2 감리 단계에서 실행.**
  STEP 0·1에는 필요 없음. 미뤄도 안전.

- **메모리 정정 미수행.** 기획자 판단으로 추후 결정.
  향후 세션 초반에 "119 vs 38" 혼동이 재발하면 이때 정정 고려.

---

*이 세션 컨텍스트는 2026-04-12 저녁에 v26→v27로 갱신되었다.*
*Phase G 사전 진단 완료: Layer 1 정량 감리 + v2.0 실행계획 작성.*
*다음 작업: Phase G STEP 0 — PRG-T1·T2 is_citable 승격 + 임베딩 생성.*
*핵심 통찰: 정밀도의 길은 모델이 아닌 데이터 레이어의 3층 계통에 있다.*

---
