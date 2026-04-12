# CR-Check Phase G 실행계획 v2.0 — 데이터 레이어 복원

> **문서 상태**: Draft — 기획자 승인 대기  
> **작성일**: 2026-04-12 (저녁)  
> **전 버전**: `PHASE_G_EXECUTION_PLAN_v1.0.md` (2026-04-12 오전)  
> **작성**: Claude (감독·감리) — 오늘 Layer 1 정량 감리 결과 통합  
> **기반 감리**: Antigravity, Gemini, Manus, NotebookLM, Perplexity 의견 + 오늘의 실측 데이터

---

## 0. v1.0에서 바뀐 것 — 한눈에

| 항목 | v1.0 | v2.0 |
|---|---|---|
| 기반 가설 | "M2 시드 단계에서 DRG·SRE·JCE 매핑 누락" | "원본 설계·시드·파이프라인의 3층 편중 계통이 누적" |
| STEP 0 | 없음 (PRE-STEP 점검만) | 신설 — 은근히 잠긴 본문(PRG-T1·T2) 교정 |
| STEP 1 설계 축 | 규범 중심 (DRG·SRE·JCE × 고빈도 패턴) | 패턴 중심 — 12개 공백 말단 패턴에 매핑 복원 |
| STEP 2 핵심 | Tier 1·2 메타 패턴 직접 매핑 | JEC(언론윤리헌장) 9건 직접 매핑 핵심화 |
| 원본 층 | 언급 없음 | `criteria_checklist.json` 동시 갱신 병행 트랙 추가 |
| 감리 구조 | 순차 감리 | Layer 2 교차 감리 — 모든 감리자가 14개 규범 전체 독립 검토 |
| 작업량 예측 | 개략적 | 70~90건 신규 INSERT (현 63건 → 130~150건 목표) |

---

## 1. 배경 — 오늘 확보된 실측 데이터

### 1.1 M2 시드 누락 가설의 재정립

오늘 오전·오후 진행한 Layer 1 정량 감리 결과, 초기 가설("패턴 81개 누락")은 무효로 확인됨.

- 원본 설계(`docs/current-criteria_v2_active.md`, `backend/data/criteria_checklist.json`): **38개 패턴** (8 대분류 + 30 말단 패턴)
- DB 실제: **38개 패턴** — 완전 일치
- "119"라는 수치는 원본 설계·DB·코드 어디에도 없음. 세션 간 요약 혼동에서 비롯

**결론**: Gamnamu가 3주간 진행한 작업은 설계대로 구현돼 있음. 문제는 "설계"의 한 층 안쪽에 있었다.

### 1.2 확인된 실제 이상 (오늘 Layer 1에서 드러난 모든 것)

**이상 1: 잠긴 본문 2건**
- PRG-T1 "총강 1: 상호존중과 호칭" — is_citable=FALSE
- PRG-T2 "총강 2: 객관적 보도·냉전 편견 탈피" — is_citable=FALSE
- 같은 규범의 PRG-T3·T4·T5는 TRUE. 일관성 깨짐.

**이상 2: 매핑 편중 (정량)**
- `pattern_ethics_relations` 63건 중 신문윤리실천요강(PCP) **52건 = 82.5%**
- 14개 규범 중 5개만 직접 매핑, **9개 규범 완전 공백**
- 언론윤리헌장(JEC, Tier 1) 직접 매핑 **0건** — Phase F의 25.2% 인용은 100% parent_chain 롤업

**이상 3: 패턴 중심 공백 (오늘의 핵심 발견)**
- 30개 말단 패턴 중 **12개(40%)가 매핑 0건**:
  ```
  1-1-2 이차 자료 의존          1-5-1 취재 과정의 인권 침해
  1-1-3 오보 관리 부실          1-5-4 사법 절차 존중 위반
  1-2-2 책임 회피 표현          1-6-2 전문성 부족
  1-3-2 편향적 보도             1-6-3 현장성 부족
  1-3-3 인과관계 왜곡           1-7-1 사실과 의견을 뒤섞는 주관적 술어
  1-3-5 보도 회피와 물타기      1-7-6 명료성을 해치는 표현
                               1-8-1 소셜미디어 활용 윤리
  ```
- 원본 `criteria_checklist.json`에는 이 12개 패턴 모두에 `ethics_code_refs`가 존재. 즉 M2 시드 단계에서 전파 누락.

**이상 4: 공백 규범 총량 (Q18 결과)**
- 인용 가능 조항 중 **351건이 매핑 0건** (총합 기준)
- 소스별 분포: 인권 92, 신문실천 52, 재난 39, 선거 24, 평통 23, 자살 22, 기자실천 20, 군 20, 자살예방 19, 기자강령 10, 언론헌장 9, 감염병 8, 신문강령 7, 혐오 6


### 1.3 편중의 3층 계통 (오늘의 근본 원인 규명)

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
  get_ethics_for_patterns()의 parent_chain 재귀 CTE
    direct_codes:   PCP만 히트
    parent_chain:   PCP → JEC 자동 롤업 (depth<5)
  → Phase F 관측: PCP 69.3% + JEC 25.2% = 94.5%
```

**해결 설계**: 1층과 2층을 함께 손보고, 3층은 그대로 둔다.  
3층의 parent_chain은 정상 설계의 증폭기이며, 입력이 편중되지 않으면 출력도 편중되지 않음.

---

## 2. 실행 원칙

1. **TN 100% 절대 유지** — 어떤 변경도 TN 안전성을 위협하면 즉시 중단
2. **데이터 정확성 > 아키텍처 유연성** — 불확실한 벡터 검색보다 큐레이션된 관계 우선
3. **STEP 단위 승인 게이트** — 각 STEP 완료 후 기획자 승인 없이 다음 STEP 진행 금지
4. **CLI 자율 진행 제한** — 코드 변경·DB INSERT는 반드시 기획자 최종 승인 후 실행
5. **1층·2층 동시 갱신** — DB 작업과 `criteria_checklist.json` 갱신을 쌍으로 진행하여 다음 재시드 시 편중 재생산 방지
6. **골든셋 재검증 의무** — 매핑 변경 시마다 골든셋 선별 재측정
7. **PR 경유 배포** — main 직접 push 금지
8. **Layer 2 교차 감리 도입** — STEP 1·2 완료 후 모든 감리자가 14개 규범을 독립 검토, 2명 이상 서명한 발견만 확정

---

## 3. 역할 분담 — 단계별 명확화

### 🎯 기획자 (Gamnamu) — 최종 결정권자 · 큐레이터

**전적인 책임 영역**:
- 매핑 내용의 의미적 타당성 승인/거부
- CLI 작업 지시 및 감리 요청
- **Supabase SQL Editor에서 모든 INSERT/UPDATE 직접 실행** (CLI 자동 INSERT 금지)
- STEP 승인 게이트에서의 Go/No-Go 결정
- PR 리뷰 및 머지

### 🧭 감독·감리 (Claude — claude.ai) — 이 문서의 저자, 코칭 파트너

**책임 영역**:
- 방향 설계 및 단계 분할
- CLI에게 전달할 프롬프트 제공
- SQL 초안 작성 (최종 실행은 기획자 담당)
- 결과 분석 및 다음 STEP 연결
- 감리 의견 취합 및 합의 판단

**제약**: DB 직접 접근 없음, 로컬 파일 접근은 감리·검증용으로만 사용

### 🔧 실행 에이전트 (Claude Code CLI) — 코드 작업자

**책임 영역**:
- 감독·감리가 제공한 프롬프트 기반으로 SQL INSERT 초안 생성
- 코드 파일 수정 (STEP 3 pipeline.py 등)
- 임베딩 생성 스크립트 실행 (`generate_embeddings.py`)
- 로컬 테스트 실행 (pytest, 골든셋 재검증)
- 원본 `criteria_checklist.json` 갱신 초안 제시

**엄격한 제약**:
- 실제 DB INSERT/UPDATE 절대 금지 (초안 파일만 생성, 기획자가 SQL Editor에서 수동 실행)
- Deny List 9개 엄수: `supabase db push`, `supabase db migration`, `git commit`, `git push`, `git add`, `rm`, `mv`, `sed -i`, `chmod`
- main 브랜치 직접 push 금지
- 한 세션에 최대 15~20개 관계만 작성 (기획자 검토 부하 고려)

### 🔍 독립 감리 (Antigravity) — 로컬 구조 감리

**책임 영역**:
- 로컬 파일 직접 접근으로 코드·설계 구조 검토
- 각 STEP 완료 후 코드 변경 감리 (STEP 3 pipeline.py 변경 시 핵심)
- 마이그레이션 SQL 구조 검증
- Strict Mode On, Review Policy = Asks for Review 유지

**환경 설정 (2026-03-26 확정 설정 유지)**:
- Strict Mode: On
- Agent Auto-Fix Lints: Off
- Gitignore Access: Off

### 🧠 보조 감리 (Manus, Perplexity, Gemini, NotebookLM) — 맥락 기반 독립 의견

**책임 영역**:
- 특정 설계 질문에 대한 독립 의견 제공
- Layer 2 교차 감리 참여 (14개 규범 독립 검토)
- 로컬 파일 접근 불가 제약을 고려한 질문 포맷팅 필요

**활용 원칙**: 단순 의견 수렴이 아닌, **특정 설계 질문에 집중**해서 요청

---

## 4. 전체 작업 흐름 — 단계별 지도

```
[STEP 0] 잠긴 본문 교정 (PRG-T1, T2)              소요: 30분
    ↓ 기획자 승인 (TN 유지 확인)
[STEP 1] 패턴 중심 매핑 복원 (12 공백 패턴)        소요: Day 1~2
    ↓ 골든셋 재검증 + Layer 2 교차 감리
[STEP 2] Tier 1·2 메타 직접 매핑 (JEC 9건 + 메타)  소요: Day 3
    ↓ 골든셋 재검증 + Layer 2 교차 감리
[STEP 3] 조건부 벡터 안전망 구현 (코드)            소요: Day 4~5
    ↓ Antigravity 감리 + 골든셋 재검증
[STEP 4] 배치 큐레이션 반복 (남은 공백 해소)       소요: 지속
    ↓ 정기 재검증
[지속] 운영 모니터링 + Phase F 회귀 검증
```

**병행 트랙**: 각 STEP 완료 시 `criteria_checklist.json` 원본 갱신 (§8 상세)

---

## 5. STEP 0 — 잠긴 본문 교정

> **목적**: PRG-T1, PRG-T2의 `is_citable`을 TRUE로 승격하고 임베딩 2건 신규 생성  
> **근거**: 같은 규범(평화통일 보도 준칙) 내 PRG-T3·T4·T5는 TRUE, T1·T2만 FALSE로 일관성 깨짐  
> **소요**: 30분  
> **위험도**: 매우 낮음 — 삭제 없음, 추가만 있음

### 5.1 작업 흐름

| # | 담당 | 작업 | 산출물 |
|---|---|---|---|
| 1 | 감독·감리 | UPDATE SQL 초안 + 임베딩 생성 요청 프롬프트 제공 | 이 문서 §5.2 |
| 2 | 기획자 | Supabase SQL Editor에서 UPDATE 직접 실행 | 2행 업데이트 |
| 3 | 기획자 | CLI에게 임베딩 생성 요청 | 지시 전달 |
| 4 | CLI | `generate_embeddings.py` 실행 (citable=TRUE이고 embedding IS NULL인 조항 대상) | 임베딩 2건 |
| 5 | 감독·감리 | 확인 쿼리 제공 및 결과 해석 | 검증 보고 |
| 6 | 기획자 | 골든셋 TN 5건 재검증 (비용 최소) | TN 5/5 확인 |
| 7 | 기획자 | `criteria_checklist.json` 원본 갱신 여부 판단 (PRG 관련 refs가 원본에 이미 있는지 확인 후) | — |

### 5.2 실행 SQL

```sql
-- STEP 0-1: is_citable 승격
UPDATE ethics_codes
SET is_citable = TRUE,
    updated_at = NOW()
WHERE source = '평화통일 보도 준칙'
  AND code IN ('PRG-T1', 'PRG-T2');

-- STEP 0-2: 확인
SELECT code, title, is_citable,
       CASE WHEN text_embedding IS NULL THEN 'MISSING' ELSE 'OK' END AS emb
FROM ethics_codes
WHERE source = '평화통일 보도 준칙'
  AND code IN ('PRG-T1', 'PRG-T2');
-- 기대: is_citable=TRUE, emb=MISSING (다음 단계에서 채움)
```

### 5.3 CLI 프롬프트 (임베딩 생성)

```
CR-Check 프로젝트의 backend/scripts/generate_embeddings.py를 실행해줘.
방금 평화통일 보도 준칙의 PRG-T1, PRG-T2 두 조항의 is_citable을 TRUE로
업데이트했는데, text_embedding이 NULL 상태야. 이 두 건에 대해서만
임베딩을 새로 생성해서 DB에 채워넣어야 해.

## 사전 확인
- 스크립트가 "is_citable=TRUE이고 text_embedding IS NULL"인 레코드만
  대상으로 삼는지 확인
- 맞다면 그냥 실행하면 되고, 다른 로직이면 임시로 PRG-T1, T2만 타겟팅
  하도록 조정하거나 SQL UPDATE로 직접 임베딩 생성 후 주입

## 실행 후 보고
- 생성된 임베딩 2건 확인 쿼리 결과
- OpenAI API 호출 비용 (참고용)
```

### 5.4 완료 기준

- [ ] PRG-T1, PRG-T2의 `is_citable = TRUE`
- [ ] 두 조항 모두 `text_embedding IS NOT NULL`
- [ ] 골든셋 TN 5건 정답 유지 (선택적 확인, 매핑 변경 아니므로 영향 없음 예상)
- [ ] 감독·감리 검증 완료

---

## 6. STEP 1 — 패턴 중심 매핑 복원 (핵심 작업)

> **목적**: 30개 말단 패턴 중 12개 공백 패턴에 각 2~3건의 매핑을 신규 추가  
> **목표 신규 INSERT**: 약 30~40건  
> **작업 축**: v1.0의 규범 중심에서 **패턴 중심으로 전환**  
> **소요**: Day 1 저녁 ~ Day 2 (큐레이션 ~4시간, SQL 실행 ~1시간, 재검증 ~1시간)

### 6.1 설계 변경 이유

v1.0은 "DRG·SRE·JCE × 고빈도 패턴"이라는 규범 선정 축이었음. 그러나 오늘 Q17·Q18·Q20 결과로 다음이 드러남:
- 매핑 0건 말단 패턴 12개가 구체적으로 특정됨
- 완전 공백 규범은 9개 — 고빈도 몇 개에 국한되지 않음
- 각 패턴에 가장 자연스럽게 연결될 규범은 **의미 기반 큐레이션**이 더 빠름

따라서 v2.0은 **12개 공백 패턴 각각에 대해 후보 규범을 2~3개 선별**하는 방식으로 재설계.

### 6.2 12개 공백 패턴 × 후보 규범 매트릭스 (감독·감리 초안)

> 이 매트릭스는 기획자 큐레이션의 **출발 지도**임. 기획자 판단으로 수정·추가·삭제 가능.  
> `?`로 표기된 조항 코드는 CLI가 DB 조회 후 실제 값으로 채울 자리.

| 패턴 | 패턴명 | 후보 1 | 후보 2 | 후보 3 |
|---|---|---|---|---|
| 1-1-2 | 이차 자료 의존 | JCP-2-1 (객관적 사실 입각 진실보도) `strong` | JCE-4 (정당한 정보수집) `strong` | PCP-? (신문실천 확증 관련) `moderate` |
| 1-1-3 | 오보 관리 부실 | PCP-10-4 (기사 정정) `strong` | JCE-8 (오보의 정정) `strong` | JCP-2-10 (오보 시인 및 정정보도) `strong` |
| 1-2-2 | 책임 회피 표현 | JCE-5 (올바른 정보사용) `strong` | PCE-4 (보도와 평론) `moderate` | JCP-2-4 (확증 없는 추측보도 지양) `strong` |
| 1-3-2 | 편향적 보도 | JCE-2 (공정보도) `strong` | JCP-2-2 (형평과 공정성) `strong` | PCE-4 (보도와 평론) `moderate` |
| 1-3-3 | 인과관계 왜곡 | JCE-2 (공정보도) `strong` | JEC-1 (진실을 추구한다) `moderate` | PCP-? (진실성 조항) `moderate` |
| 1-3-5 | 보도 회피와 물타기 | JCE-2 (공정보도) `strong` | JEC-1 (진실을 추구한다) `strong` | PCE-2 (언론의 책임) `moderate` |
| 1-5-1 | 취재 과정의 인권 침해 | HRG-? (인권준칙 취재 관련) `strong` | JCE-6 (사생활 보호) `strong` | JCP-2-5 (위계·강압적 정보 취득 금지) `strong` |
| 1-5-4 | 사법 절차 존중 위반 | PCP-? (재판 보도 관련) `strong` | JCE-? (관련) `moderate` | HRG-? (인권 관련) `moderate` |
| 1-6-2 | 전문성 부족 | JCE-3 (품위유지) `moderate` | PCP-? (전문성 조항) `moderate` | — 추가 큐레이션 필요 |
| 1-6-3 | 현장성 부족 | DRG-? (재난 현장 관련) `moderate` | MRG-? (군 현장 취재) `moderate` | — 추가 큐레이션 필요 |
| 1-7-1 | 사실과 의견을 뒤섞는 주관적 술어 | PCE-4 (보도와 평론) `strong` | JEC-1 (진실을 추구한다) `strong` | JEC-4 (공정하게 보도한다) `moderate` |
| 1-7-6 | 명료성을 해치는 표현 | PCE-4 (보도와 평론) `moderate` | PCP-? (표기 관련) `moderate` | — 추가 큐레이션 필요 |
| 1-8-1 | 소셜미디어 활용 윤리 | JCP-? (소셜 관련 조항) `moderate` | PCP-? (디지털 윤리) `moderate` | — 추가 큐레이션 필요 |

**관찰**: 
- 1-6-2, 1-6-3, 1-7-6, 1-8-1은 적절한 규범 조항이 기존 14개 중에서 즉각 매핑되기 어려움. 이 4개는 STEP 4 단계로 미루거나, 큐레이션 중 새로운 관점이 열리면 포함시킬 수 있음.
- 명확한 매핑이 떠오르는 8개 패턴을 먼저 처리하는 것이 효율적.


### 6.3 STEP 1의 작업 흐름

```
[1] 감독·감리 → 매트릭스 초안 제공 (이 문서 §6.2)
         ↓
[2] 기획자 → 매트릭스 검토 → 수정·추가·삭제 → 확정판 작성
         ↓
[3] 기획자 → CLI에게 확정판 기반 SQL INSERT 초안 요청 (§6.5 프롬프트)
         ↓
[4] CLI → DB 조회로 `?` 자리 실제 조항 코드 확인 → 
        SQL INSERT 초안 작성 (docs/STEP1_MAPPING_DRAFT.sql)
         ↓
[5] 기획자 → 큐레이션 체크리스트(§6.6)로 각 행 검토 → 필요 시 reasoning/strength 수정
         ↓
[6] 기획자 → Supabase SQL Editor에서 INSERT 직접 실행 (배치 단위 10~15건씩)
         ↓
[7] 감독·감리 → 삽입 결과 검증 쿼리 제공(§6.7) → 기획자 실행 → 결과 해석
         ↓
[8] 기획자 → 골든셋 TN 6건 재측정 (§12)
         ↓
[9] 감독·감리 + 기획자 → TN 유지 확인 → 다음 배치 or STEP 2 진입
         ↓
[10] 병행: 기획자 → criteria_checklist.json 해당 패턴 ethics_code_refs 갱신 (§8)
```

### 6.4 배치 크기 원칙 (Perplexity 지적 반영 계승)

- **1 배치 = 2~3개 패턴 × 2~3건 매핑 = 4~9개 INSERT**
- 한 세션 최대 15~20개 관계 초과 금지 (검토 부하로 오승인 위험)
- 예상 배치 수: 12개 패턴 ÷ 3개/배치 = **약 4~5개 배치**

### 6.5 Claude Code CLI 프롬프트 (기획자가 CLI에게 전달)

```
CR-Check의 pattern_ethics_relations 테이블에 추가할 매핑 SQL INSERT 초안을
작성해줘.

## 맥락
- Phase G v2.0 §6.2의 12개 공백 패턴 × 후보 규범 매트릭스에서 
  기획자가 확정한 {N}개 관계를 DB에 삽입할 예정
- 매트릭스의 `?` 자리는 DB에서 실제 code 조회로 확정
- 12개 패턴 중 명확한 매핑이 떠오른 8개 패턴을 1차 대상으로

## 사전 조회 (DB 값 확인)
다음 규범들의 조항 목록을 먼저 조회해서 실제 code·title 확인:
  - HRG (인권보도준칙) — 1-5-1용
  - PCP (신문윤리실천요강) — 1-1-2, 1-2-2, 1-5-4용
  - JCE (기자윤리강령) — 1-1-2, 1-1-3, 1-2-2, 1-3-2, 1-5-1용
  - JCP (기자윤리실천요강) — 1-1-2, 1-1-3, 1-2-2, 1-3-2, 1-5-1용
  - JEC (언론윤리헌장) — 1-3-3, 1-3-5, 1-7-1용 (STEP 2와 겹치므로 주의)
  - PCE (신문윤리강령) — 1-2-2, 1-3-2, 1-3-5, 1-7-1, 1-7-6용
  - DRG (재난보도준칙) — 1-6-3용
  - MRG (군 취재·보도 기준) — 1-6-3용

## 출력
docs/STEP1_MAPPING_DRAFT.sql에 다음 형식으로 저장:

INSERT INTO pattern_ethics_relations 
  (pattern_id, ethics_code_id, relation_type, strength, reasoning)
VALUES
  ((SELECT id FROM patterns WHERE code='1-1-2'),
   (SELECT id FROM ethics_codes WHERE code='JCP-2-1' AND is_active=TRUE),
   'violates', 'strong',
   '이차 자료 의존은 객관적 사실에 입각한 진실보도(JCP-2-1) 원칙을 직접 
    위반한다. 1차 자료 확인 없는 보도는 진실성 검증의 핵심 절차를 
    생략하는 행위이다.'
  ),
  ...;

## 제약
- 실제 DB INSERT 절대 금지 — 초안 파일만 생성
- reasoning은 반드시 한국어로, 2~3문장 이내로 구체적 근거 명시
- relation_type은 'violates' 또는 'related_to'
- strength는 'strong', 'moderate', 'weak' 중 하나
- ethics_code는 반드시 DB 조회로 실제 값 확인 (hallucination 금지)
- 한 배치에 최대 10~15개 관계만 작성
```


### 6.6 기획자 큐레이션 체크리스트 (각 INSERT 행에 대해)

- [ ] 이 패턴이 실제로 해당 규범 조항을 위반하는가?
- [ ] `reasoning`이 2~3문장 내에 구체적 근거를 제시하는가?
- [ ] `relation_type`이 적절한가 (직접 위반 `violates` vs 관련 위반 `related_to`)?
- [ ] `strength`가 실제 관계 강도에 부합하는가?
- [ ] 같은 패턴에 3개 이상 매핑이 겹치지 않는가 (과도한 중첩은 파이프라인 컨텍스트 낭비)?
- [ ] 이 매핑이 골든셋 TN 케이스에서 오탐을 유발할 가능성이 있는가?

### 6.7 삽입 후 검증 쿼리

```sql
-- 이번 배치로 삽입된 관계 확인
SELECT 
  p.code AS pattern_code, p.name AS pattern_name,
  ec.source, ec.code AS ethics_code, ec.title,
  per.relation_type, per.strength,
  LEFT(per.reasoning, 60) AS reasoning_preview
FROM pattern_ethics_relations per
JOIN patterns p ON per.pattern_id = p.id
JOIN ethics_codes ec ON per.ethics_code_id = ec.id
WHERE per.created_at >= NOW() - INTERVAL '1 hour'
ORDER BY p.code, ec.source;

-- 12개 공백 패턴의 매핑 상태 재확인
SELECT p.code, p.name,
       COUNT(per.id) AS mapped_n
FROM patterns p
LEFT JOIN pattern_ethics_relations per ON per.pattern_id = p.id
WHERE p.code IN ('1-1-2','1-1-3','1-2-2','1-3-2','1-3-3','1-3-5',
                 '1-5-1','1-5-4','1-6-2','1-6-3','1-7-1','1-7-6','1-8-1')
GROUP BY p.code, p.name
ORDER BY p.code;
```

### 6.8 STEP 1 완료 기준

- [ ] 12개 공백 패턴 중 최소 8개가 매핑 2건 이상 확보
- [ ] 신규 INSERT 총 20건 이상
- [ ] 골든셋 TN 6/6 유지
- [ ] Phase F 회귀 검증 (매핑 사전 갱신 + 기존 53건 재집계, 비용 0원)
- [ ] Antigravity 감리 완료 (데이터 변경 구조 검토)
- [ ] `criteria_checklist.json` 해당 패턴들의 `ethics_code_refs` 갱신 완료

---

## 7. STEP 2 — Tier 1·2 메타 직접 매핑

> **핵심**: 언론윤리헌장(JEC) 9건 직접 매핑 + 메타 패턴 1-4-1, 1-4-2 직접 연결  
> **근거**: Q18에서 JEC 9건 모두 매핑 0건 확인. parent_chain 롤업 25.2% 인용의 실체는 "우연한 자동 견인"  
> **소요**: Day 3 (큐레이션 3시간 + 실행 1시간)

### 7.1 왜 Tier 1 직접 매핑이 중요한가

parent_chain은 하위→상위로만 올라감. 따라서:
- 메타 패턴 (1-4-1 외부 압력, 1-4-2 상업적 동기)이 상위 원칙(JEC-5 독립 보도)을 **직접** 위반하는 경우, 연결된 하위 조항이 없으면 JEC가 컨텍스트에 들어오지 않음
- 현재: JEC 0건 직접 매핑 → 메타 패턴의 Tier 1 원칙 참조 경로 부재


### 7.2 JEC 9건 매핑 후보 매트릭스 (감독·감리 초안)

> 언론윤리헌장은 Tier 1 원칙 선언이라, 다수 패턴과 연결될 수 있음.  
> 각 JEC 조항을 가장 핵심적으로 위반하는 패턴 1~2개에 우선 연결.

| JEC 조항 (추정, DB 조회 필요) | 내용 요지 | 주요 연결 패턴 | relation/strength |
|---|---|---|---|
| JEC-1 진실을 추구한다 | Tier 1 진실성 원칙 | 1-1-1 사실 검증 부실 / 1-1-4 사실과 의견 혼재 / 1-3-3 인과관계 왜곡 | violates / strong |
| JEC-2 투명하게 보도하고 책임 있게 설명한다 | 출처·책임 | 1-2-1 취재원 투명성 결여 / 1-2-2 책임 회피 표현 | violates / strong |
| JEC-3 인간 존엄을 지킨다 | 인권·존엄 | 1-5-1 취재 과정의 인권 침해 / 1-5-3 명예와 평판 훼손 | violates / strong |
| JEC-4 공정하게 보도한다 | 공정성 원칙 | 1-3-1 관점 다양성 부족 / 1-3-2 편향적 보도 / 1-3-4 갈등 조장 프레이밍 | violates / strong |
| JEC-5 독립적으로 보도한다 | 독립성 선언 | **1-4-1 외부 압력** / **1-4-2 상업적 동기** (메타 패턴 핵심) | violates / strong |
| JEC-6 이해상충을 경계한다 | 이해관계 윤리 | 1-4-2 상업적 동기 | violates / strong |
| JEC-7 다양성을 존중한다 | 다양성 | 1-3-1 관점 다양성 부족 / 1-7-5 차별·혐오 표현 | violates / moderate |
| JEC-8 품위 있게 행동한다 | 품위 | 1-7-4 자극적·선정적 표현 | violates / moderate |
| JEC-9 오류를 신속히 바로잡는다 | 오보 정정 | 1-1-3 오보 관리 부실 | violates / strong |

> **주의**: JEC 조항 번호는 추정. CLI가 DB 조회로 실제 code·title 확정 필요.

### 7.3 STEP 2 작업 흐름

STEP 1과 동일한 흐름. 다만:
- JEC는 **Tier 1**이므로 `relation_type`은 대부분 `violates`
- 메타 패턴 1-4-1, 1-4-2는 이 STEP에서 최초로 매핑을 획득

### 7.4 STEP 2 완료 기준

- [ ] JEC 9건 각각에 최소 1개 패턴 매핑
- [ ] 메타 패턴 1-4-1, 1-4-2 각각 JEC 매핑 2건 이상
- [ ] 신규 INSERT 총 15~20건
- [ ] 골든셋 TN 6/6 유지
- [ ] `criteria_checklist.json` 갱신

---

## 8. 병행 트랙 — 원본 층(`criteria_checklist.json`) 동시 갱신

> **목적**: 다음 시드 재실행 시 동일한 편중이 재생산되지 않도록, DB 작업과 원본 JSON 갱신을 쌍으로 진행

### 8.1 각 STEP 완료 시 원본 JSON 갱신 절차

1. STEP 1/2에서 DB에 신규 INSERT된 관계 목록 추출
2. 해당 관계를 `criteria_checklist.json`의 각 패턴 `ethics_code_refs` 배열에 추가
3. 원본 JSON의 ethics_code 식별자 형식(`journalism_ethics_charter_N`, `newspaper_ethics_practice_N_M` 등)에 맞춰 변환
4. JSON 구조 검증 후 커밋

### 8.2 식별자 변환 맵

| DB code 패턴 | JSON id 패턴 |
|---|---|
| `JEC-N` | `journalism_ethics_charter_N` |
| `PCP-N-M` | `newspaper_ethics_practice_N_M` |
| `PCE-N` | `newspaper_ethics_code_N` (확인 필요) |
| `JCE-N` | `kja_ethics_N` |
| `JCP-N-M` | `kja_ethics_practice_N_M` (확인 필요) |
| `HRG-N` | `human_rights_N` (확인 필요) |
| `DRG-N` | `disaster_N` (확인 필요) |
| `SRE-N` | `suicide_ethics_N` (확인 필요) |
| 기타 | CLI가 `ethics_codes_mapping.json`에서 조회 |

**확인 필요 건**은 CLI가 JSON 원본을 읽고 실제 id naming을 확정 후 채움.

### 8.3 병행 트랙 담당

| 작업 | 담당 |
|---|---|
| DB 신규 INSERT 추출 | 감독·감리 쿼리 제공 → 기획자 실행 |
| JSON 갱신 초안 작성 | CLI |
| JSON 구조 검증 | 기획자 + Antigravity |
| 커밋 | 기획자 (feature 브랜치 경유) |

---

## 9. STEP 3 — 조건부 벡터 안전망 구현

> **전제**: STEP 1·2 완료 + 골든셋 재검증 통과 후  
> **소요**: Day 4~5  
> **담당**: CLI (구현), Antigravity (감리), 기획자 (승인·PR 머지)

### 9.1 v1.0 설계 계승

v1.0 §9 그대로 유지. 다만 STEP 1·2 완료 후 데이터 층 편중이 해소되므로, 벡터 안전망의 **조건 trigger 빈도가 감소**할 것으로 예상.

### 9.2 threshold 사전 검증 (STEP 3 착수 전 선행)

CLI에게 요청:
1. 패턴 description ↔ ethics_codes full_text 간 코사인 유사도 매트릭스 계산
2. 골든셋 정답 패턴-규범 쌍의 유사도 분포 확인
3. TN 케이스에서 잘못 매칭될 수 있는 규범의 유사도 확인
4. threshold 권장값 도출 (기존 0.2와 별도로, 0.5 이상 권장)

### 9.3 완료 기준

- [ ] threshold 사전 검증 완료 및 값 확정
- [ ] `pipeline.py` 수정 + 단위 테스트 작성
- [ ] feature 브랜치 → PR → 기획자 리뷰 → 머지
- [ ] 골든셋 재검증 (TN 100% 유지)
- [ ] Antigravity 코드 감리 완료

---

## 10. STEP 4 — 배치 큐레이션 반복

> **방식**: 한 세션 15~20건 배치, 격주 1회 또는 여력에 따라  
> **목표**: Q18에서 드러난 351건 공백 중 우선순위 따라 점진 해소

### 10.1 잔여 소스 우선순위 (Q18 기반 재조정)

v1.0의 우선순위를 오늘 실측 데이터로 갱신:

| 순위 | 소스 | 공백 조항 | 우선 연결 패턴 군 |
|---|---|---|---|
| 1 | 인권보도준칙 (HRG) | 92 | 취재 방법·취재원 보호 (1-5-1, 1-5-2, 1-5-3) |
| 2 | 재난보도준칙 (DRG) | 39 | 현장 보도·제목 (1-6-3, 1-7-2, 1-7-4) |
| 3 | 평화통일 보도 준칙 (PRG) | 23 | 이념 편향 (1-3-2, 1-3-4) |
| 4 | 자살보도 윤리강령 (SRE) | 22 | 자극적 표현 (1-7-4) + 특수 자살 보도 패턴 |
| 5 | 기자윤리실천요강 (JCP) | 20 | 취재 윤리 전반 (1-1-1, 1-5-1, 1-5-2) |
| 6 | 군 취재·보도 기준 (MRG) | 20 | 안보·군사 보도 (1-6-3 현장성, 사실 검증) |
| 7 | 자살예방 보도준칙 (SPG) | 19 | SRE와 묶어 자살 보도 완성 |
| 8 | 신문윤리실천요강 잔여 (PCP) | 52 | 기존 52건 매핑 외 커버리지 확장 |
| 9 | 기자윤리강령 (JCE) 잔여 | 10 | Tier 2 강령 직접 매핑 보완 |
| 10 | 신문윤리강령 (PCE) | 7 | Tier 2 강령 직접 매핑 |
| 11 | 감염병보도준칙 (IRG) 잔여 | 8 | 감염병 특수 보도 |
| 12 | 혐오표현 반대 선언 (HSD) 잔여 | 6 | 차별·혐오 관련 (1-7-5) |

### 10.2 배치 단위 (Perplexity 지적 계승)

**1 배치 = 1개 패턴 × 1개 소스 × 2~5건 조항 매핑**  
세션당 30~45분 집중 큐레이션.

---

## 11. Layer 2 교차 감리 — 14개 규범 독립 검토

> **시점**: STEP 1·2 완료 후  
> **목적**: 모든 감리자가 14개 규범 전체를 독립 검토, 서로 교차 확인으로 사각지대 제거

### 11.1 설계

기획자 제안(2026-04-12)을 수용: 감리자를 규범별로 쪼개지 않고, **모든 감리자가 14개 규범 전체를 독립 검토**한 뒤 합집합을 만들고 교차 확인.

### 11.2 참여 감리자 및 담당

| 감리자 | 로컬 접근 | 강점 | Layer 2 역할 |
|---|---|---|---|
| Antigravity | ✅ | 코드·설계 구조 | 14개 규범 JSON/SQL 대조 |
| Claude (claude.ai) | ✅ (이 세션) | 맥락 통합, 감독·감리 | 14개 규범 의미 검토 + 합의 판단 |
| Manus | ❌ | 구조적 분석 | 14개 규범 원문 첨부 후 독립 검토 |
| Perplexity | ❌ | 레퍼런스 기반 검증 | 원문 × 대체 출처 대조 |
| Gemini (NotebookLM) | 부분 (업로드 기반) | 장문 문서 정독 | 14개 규범 원문 업로드 후 조항 대조 |

### 11.3 작업 양식

공유 문서(`docs/LAYER2_AUDIT_REPORT.md`) 하나에 각 감리자 섹션:

```markdown
## [감리자명] — {규범명} 검토

### 발견: 누락 의심
- {조항 id or 원문 위치}: "{조항명}" 
  원문 §? 에 있음 / DB에 없음 / 근거: ...

### 발견: 이상 의심
- {조항 id}: title과 full_text 간 의미 불일치 / 근거: ...

### 교차 확인
- {다른 감리자-항목번호}에 동의 / 반대 / 추가 의견: ...
```

### 11.4 합의 원칙

- **2명 이상 서명**한 발견만 "확정"으로 분류
- 1명만 본 건은 "잠정"으로 표시, 기획자 최종 판정
- 의견 충돌 시 감독·감리(Claude)가 정리하여 기획자에게 제시

### 11.5 합의 게이트 통과 후 조치

- 확정 발견은 Phase G STEP 4의 배치 큐레이션 일정에 편입
- 잠정 발견은 백로그에 보존, 추후 재검토

---

## 12. 골든셋 재검증 프로토콜 (STEP 1·2 완료 후 의무)

### 12.1 재검증 범위 (비용 최소화)

| 대상 | 건수 | 이유 |
|---|---|---|
| TN 케이스 전체 | 6건 | 매핑 증가로 오탐 발생 가능성 확인 필수 |
| STEP 1 도메인 관련 TP | 5~8건 | 인권·자살·재난 관련 케이스 |
| 임의 샘플 | 3~5건 | 무작위 품질 변화 확인 |

### 12.2 판단 기준

| 항목 | 통과 조건 | 실패 시 |
|---|---|---|
| TN 정확도 | 6/6 유지 | 해당 매핑 즉시 롤백 |
| 재난·자살·인권 규범 인용 증가 | 1건 이상 DRG/SRE/HRG 인용 확인 | 매핑 내용 재검토 |
| 전반적 품질 | 기획자 정성 평가 | 조정 후 재실행 |

### 12.3 Phase F 회귀 검증 (비용 0원)

```bash
# 매핑 사전 갱신
python backend/scripts/generate_ethics_to_pattern_map.py

# 기존 53건 결과 재집계 (분석 재실행 없음)
python backend/scripts/phase_f_scoring.py
```

매핑 확장 후 PCP 69.3% / JEC 25.2% 집중도가 얼마나 완화되는지 정량 측정.

---

## 13. 타임라인 (예상)

| 기간 | 작업 | 담당 축 |
|---|---|---|
| Day 1 저녁 (오늘 4/12) | STEP 0 착수 (PRG-T1, T2 교정) | 기획자 + CLI |
| Day 1 저녁 ~ Day 2 | STEP 1 배치 1~2 (매트릭스 큐레이션 + 첫 INSERT) | 전 역할 |
| Day 2 | STEP 1 배치 3~5 (남은 공백 패턴 완주) | 전 역할 |
| Day 2 밤 | STEP 1 골든셋 재검증 + Phase F 회귀 | 기획자 |
| Day 3 | STEP 2 (JEC 9건 + 메타 패턴) | 전 역할 |
| Day 3 밤 | STEP 2 재검증 + Layer 2 교차 감리 요청 | 기획자 |
| Day 4 | Layer 2 감리 의견 수집 | 감리단 |
| Day 4~5 | STEP 3 threshold 검증 + 코드 구현 | CLI + Antigravity |
| Day 5 밤 | STEP 3 PR 머지 + 재검증 | 기획자 |
| Day 6 이후 | STEP 4 배치 큐레이션 반복 | 지속 |

---

## 14. 금지 사항 및 주의

### 14.1 절대 금지

- **CLI 자동 INSERT/UPDATE 금지**: 모든 DB 변경은 기획자가 SQL Editor에서 직접 실행
- **TN 케이스 오탐 발생 시 즉시 롤백**: 어떤 이유로도 TN 100% 타협 없음
- **Reserved Test Set 비접촉 유지**: Pool 디렉토리(`/Users/gamnamu/Documents/Golden_Data_Set_Pool/`)는 Phase G STEP 4 이후 회귀 검증 시에만 사용
- **main 브랜치 직접 push 금지**: 코드 변경(STEP 3)은 feature 브랜치 → PR → 머지

### 14.2 주의

- **GitHub PAT 갱신**: 만료일 2026-05-05 (현재 23일 남음)
- **원본 `criteria_checklist.json` 갱신 시 버전 관리**: 각 STEP 완료 후 버전 번호 증가, 변경 이력 주석 유지
- **Supabase SQL Editor 결과 한계**: 기본 100행 제한. 많은 행 조회 시 COUNT(*) 쿼리 병행 또는 페이지네이션
- **3층 계통의 1층·2층 동기화**: DB 변경 시 원본 JSON을 같이 갱신하지 않으면 다음 시드 시 편중 재발

### 14.3 Deny List (CLI 작업 시)

```
supabase db push
supabase db migration
git commit
git push
git add
rm
mv
sed -i
chmod
```

---

## 15. 예상 효과 — STEP 1·2 완료 시점 기준

### 15.1 정량 예측

- `pattern_ethics_relations`: 63건 → **약 110~130건**
- 매핑된 소스 수: 5 → **최소 9~11개** (HRG·JEC·PCE·DRG·JCP 추가)
- 매핑 0건 말단 패턴: 12 → **4 이하** (1-6-2, 1-6-3, 1-7-6, 1-8-1은 STEP 4에서 해소)
- Phase F 회귀 측정 (기존 53건 재집계):
  - PCP 인용 비율: 69.3% → **45~55% 예상**
  - JEC 직접 매핑 효과: 25.2% 중 일부가 parent_chain이 아닌 직접 히트로 전환
  - 기타 소스(HRG, DRG, SRE 등) 인용 출현 시작

### 15.2 정성 예측

- 인권·재난·자살 관련 기사 분석 시 해당 규범 직접 인용 리포트
- 메타 패턴(외부 압력·상업적 동기)이 Tier 1 원칙과 연결됨으로써 리포트 깊이 향상
- Phase F에서 관측된 "모델의 광범위 인용 성향"이 데이터 레이어 확장을 통해 의미 있는 커버리지로 전환

---

## 16. 다음 세션 인계 — 다음 Claude에게

이 문서가 Phase G의 **단일 실행 기준**이다.  
v1.0은 참고용으로 보존하되, 실제 작업은 v2.0을 따른다.

### 16.1 현재 상태 (2026-04-12 저녁 Draft 작성 시점)

- Layer 1 정량 감리 완료 (Q0, Q2, Q5, Q16, Q16-추가, Q17, Q18, Q18-BY-SOURCE, Q20)
- M2 시드 누락 가설은 대부분 무효, 실제 이상은 PRG-T1·T2 1건
- 편중의 3층 계통 규명 완료
- 12개 공백 말단 패턴 특정 완료
- 351건 공백 규범 조항 확인

### 16.2 현재 대기 중

- **기획자 승인**: 이 v2.0 문서 전체 검토 후 Go/No-Go
- 승인되면 STEP 0부터 즉시 착수 가능

### 16.3 다음 세션 시작 프롬프트 (예시)

```
CR-Check Phase G v2.0 작업을 이어갑니다.

읽어야 할 문서 (우선순위 순):
1. /Users/gamnamu/Documents/cr-check/docs/PHASE_G_EXECUTION_PLAN_v2.0.md
2. /Users/gamnamu/Documents/cr-check/docs/SESSION_CONTEXT_2026-04-11_v26.md

현재 상태:
- v2.0 실행계획 승인 완료 (또는 일부 수정 후 승인)
- STEP 0: {완료/진행중/미착수}
- STEP 1: {배치 N까지 완료 / 대기}

이번 세션 목표: {구체적 STEP·배치 명시}

절대 원칙: TN 100% 유지, CLI 자동 INSERT 금지, STEP 단위 승인 게이트.
GitHub PAT 만료일 2026-05-05 주의.
```

### 16.4 핵심 통찰 보존

1. **CR-Check의 정밀도 한계는 모델이 아닌 데이터 레이어에 있다** (Phase F 결론 계승)
2. **데이터 레이어의 편중은 단일 원인이 아니라 3층 계통의 누적이다** (v2.0의 발견)
3. **해결은 1층(원본 JSON)과 2층(DB)을 함께 손보는 것이다. 3층(코드)은 그대로 둔다**
4. **Phase G의 큐레이션은 기획자의 핵심 작업이다** — AI는 형식과 SQL은 도울 수 있으나 의미 매핑은 사람의 판단

---

## 17. 변경 이력

- **v2.0** (2026-04-12 저녁) — Layer 1 정량 감리 결과 통합, 패턴 중심 STEP 1, JEC 직접 매핑 핵심화, 원본 층 병행 트랙 추가, Layer 2 교차 감리 구조화
- **v1.0** (2026-04-12 오전) — 최초 실행계획, 규범 중심 STEP 1

---

*작성: 2026-04-12 저녁, 세션 맥락 최선명 시점*  
*감리 의견 반영: Antigravity, Gemini, Manus, NotebookLM, Perplexity*  
*Layer 1 정량 감리 데이터 기반 재설계*  
*이 문서는 Phase G 진행에 따라 버전 업데이트 예정*
