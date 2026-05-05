# STEP 0-B 윤리규범(ethics_codes) 정리 계획 v1.0

> 문서 상태: Active
> 작성일: 2026-04-29
> 선행 조건: STEP 1 승인 완료 ✓
> 후행 작업: STEP 2 §8.4 (ethics_codes_context_seed.sql 생성)

---

## 1. 목적과 문제 진단

### 왜 이 작업이 필요한가

현재 파이프라인의 Phase 2(Sonnet 리포트 생성)에서 윤리규범 조회 함수
`fetch_ethics_for_patterns`가 패턴과 관련된 모든 규범을 Sonnet 컨텍스트에
포함시킨다. 이때 세 가지 노이즈가 발생한다:

1. **맥락 불일치 노이즈**: 감염병보도준칙, 재난보도준칙 등 특수 맥락 준칙이
   일반 정치·경제 기사 분석에도 발동됨.
2. **관계 강도 노이즈**: `related_to/weak` 관계 규범이 무조건 컨텍스트에 포함됨.
   → 이 문제는 STEP 4 RPC 개선에서 필터링 정책으로 해결 예정 (아래 §2 참조).
3. **선언적 조항 노이즈**: 실제 기사에 적용할 수 없는 추상적 선언 조항이
   is_citable=true 상태로 방치됨.

### DB 현황 (2026-04-29 기준)

- is_active=true 기준 총 394건
- is_citable=true: 380건 (과잉 가능성 높음)
- is_citable=false: 14건

| Tier | 출처 | 건수 | 성격 |
|---|---|---|---|
| 1 | 언론윤리헌장 | 10 | 범용 — 모든 기사 |
| 2 | 기자윤리강령 | 11 | 범용 |
| 2 | 기자윤리실천요강 | 21 | 범용 |
| 2 | 신문윤리강령 | 8 | 범용 |
| 2 | 신문윤리실천요강 | 69 | 범용 |
| 3 | 감염병보도준칙 | 10 | **특수 — health** |
| 3 | 군 취재·보도 기준 | 21 | **특수 — military** |
| 3 | 선거여론조사보도준칙 | 29 | **특수 — election** |
| 3 | 인권보도준칙 | 95 | 준범용 — 개별 검토 필요 |
| 3 | 자살보도 윤리강령 | 23 | **특수 — crisis** |
| 3 | 자살예방 보도준칙 4.0 | 20 | **특수 — crisis** |
| 3 | 재난보도준칙 | 43 | **특수 — disaster** |
| 3 | 평화통일 보도 준칙 | 26 | **특수 — unification** |
| 4 | 혐오표현 반대 미디어 실천 선언 | 8 | 준범용 |

---

## 2. 이번 작업의 범위와 범위 밖

### 이번 STEP 0-B에서 하는 것

- **applicable_contexts 컬럼 값 확정** (Phase 1·2)
- **is_citable 재조정 목록 확정** (Phase 2)
- **시드 SQL 초안 생성** (Phase 3, CLI 실행)

### 이번 STEP 0-B에서 하지 않는 것

- `related_to/weak` 필터링 정책 적용 → STEP 4 RPC 개선에서 처리
- strength 컬럼 신설 또는 수정 → STEP 4에서 처리
- applicable_contexts 기반 실시간 컨텍스트 매칭 로직 → STEP 4에서 처리

---

## 3. applicable_contexts 컬럼 설계

```sql
-- STEP 2 마이그레이션에서 추가 (MASTER_EXECUTION_PLAN §8.1)
ALTER TABLE public.ethics_codes
  ADD COLUMN IF NOT EXISTS applicable_contexts TEXT[];

-- NULL = 'all' 컨텍스트로 간주 (하위 호환)
-- 예: '{general}', '{health,disaster}', '{election}'
```

### 확정된 컨텍스트 값 목록

| 값 | 적용 대상 |
|---|---|
| NULL (= all) | Tier 1·2 범용 준칙, 혐오표현 선언 |
| `{general}` | 인권보도준칙 중 범용 조항 (보편 인권) |
| `{health}` | 감염병보도준칙 |
| `{military}` | 군 취재·보도 기준 |
| `{election}` | 선거여론조사보도준칙 |
| `{crisis}` | 자살보도 윤리강령, 자살예방 보도준칙 4.0 |
| `{disaster}` | 재난보도준칙 |
| `{unification}` | 평화통일 보도 준칙 |
| `{crime}` | 범죄·수사·재판 관련 보도 (인권보도준칙 2장, 신문윤리실천요강 7조 등) |

> **`{crime}` 추가 근거 (2026-05-01 교차 감리 합의):** 한국 언론 윤리 위반의 상당수가
> 수사·재판 과정의 피의자 인권 침해 및 반론권 미보장에서 발생한다. 인권보도준칙 2장
> (범죄 사건), 신문윤리실천요강 7조(피의자 인격권)가 이 컨텍스트의 핵심 조항이며,
> 이를 담을 컨텍스트가 없으면 해당 조항들이 `{general}`에 뭉뚱그려져 정밀도가 낮아진다.

---

### Tier 2 내 특수 맥락 조항의 applicable_contexts 처리 방침

Tier 2(범용 준칙) 안에도 특수 맥락(자살·재난·범죄 등)을 다루는 조항이 존재한다.
이런 조항을 NULL(all)로 두면 특수 준칙(Tier 3)과 중복 발동되어 노이즈가 생긴다.

**원칙: 구체성 우선(Rule of Specificity)**

Tier 2 조항이 아래 조건을 모두 충족하면 특수 컨텍스트로 좁힌다:
1. 조항의 내용이 특정 맥락(자살·재난·범죄 등)에 국한되는가
2. 해당 맥락에 더 구체적인 Tier 3 특수 준칙이 존재하는가
3. Tier 3 준칙이 발동될 때 이 조항이 중복 인용되면 노이즈가 되는가

**적용 예시 (Phase 2-A에서 처리):**

| 조항 | 현재 처리 | 변경 처리 | 이유 |
|---|---|---|---|
| 신문윤리실천요강 제3조⑧ (자살보도 신중) | NULL | `{crisis}` | 자살보도 윤리강령과 중복 |
| 신문윤리실천요강 제3조⑦ (재난 보도 흥미 위주 지양) | NULL | `{disaster}` | 재난보도준칙과 중복 |
| 신문윤리실천요강 제7조①~⑤ (피의자 인격권) | NULL | `{crime}` | 인권보도준칙 2장과 중복 |

---

## 4. 작업 3단계 구성

---

### Phase 1 — 출처 단위 컨텍스트 일괄 확정

> **소요 예상**: 30분 이내

#### Phase 1 작업 내용

출처별로 applicable_contexts 값을 일괄 확정한다.
Tier 1·2 범용 준칙 5개는 NULL(all) 처리로 빠르게 통과.
Tier 3·4 특수 맥락 준칙 9개는 초안을 제시하고 기획자가 승인.

예외 처리 기준:
- 같은 출처 내에서도 일부 조항이 다른 컨텍스트에 속한다고 판단되면
  그 조항만 개별 지정 (Phase 2에서 처리)
- 인권보도준칙(95건)은 출처 단위 일괄 처리가 어렵고 개별 검토 필요
  → Phase 2로 이관

#### Phase 1 승인 게이트

기획자 확인 포인트:
- (A) 출처-컨텍스트 매핑이 실제 준칙 내용과 일치하는가
- (B) 누락된 출처가 없는가
- (C) 컨텍스트 값 명칭이 향후 파이프라인 확장에 적합한가
- (D) **STEP 4 동기화 체크**: 확정된 컨텍스트 값 9개(`{health}`, `{military}`, `{election}`,
  `{crisis}`, `{disaster}`, `{unification}`, `{crime}`, `{general}`, NULL)가
  STEP 4-C `_infer_article_context()` 함수의 반환값 목록과 1:1 대응되는지 확인.
  현재 MASTER_EXECUTION_PLAN §10의 함수 코드에는 `health`, `disaster`, `court`, `general`
  4개만 정의되어 있어 `military`, `election`, `crisis`, `unification`, `crime` 5개가 누락 상태.
  Phase 1 승인 시점에 STEP 4 담당자에게 보강 예약을 통보한다.

교차 감리: 2인 이상 독립 감리 (언론 맥락 이해도가 높은 감리자 우선)

---

### Phase 2 — 개별 조항 검토 (is_citable + 예외 컨텍스트)

> **소요 예상**: 1~2 세션

#### Phase 2 작업 내용

아래 세 가지를 순서대로 진행한다.

---

**[2-Pre] 인권보도준칙 95건 사전 분류 프레임 확정 (Phase 2 착수 전 필수)**

95건 개별 검토에 앞서 챕터 단위로 먼저 컨텍스트를 맵핑하고 기획자 승인 후 진행한다.

**3단계 사전 분류 기준:**

| 분류 | 대상 조항 성격 | applicable_contexts | 해당 챕터 |
|---|---|---|---|
| A. 보편 인권 | 모든 취재 대상에게 적용 | `{general}` 또는 NULL | 총강, 제1장 |
| B. 상황적 인권 | 특정 피해자 속성(소수자·약자) 등장 시 | `{general}` | 제3~8장 |
| C. 사법 인권 | 범죄·수사·재판 보도 시 적용 | `{crime}` | 제2장 |

> 제9장(북한이탈주민)은 `{crime}` / `{unification}` / `{general}` 중 선택 — 개별 검토.

**조항 단위 판단 질문:**
1. 이 조항이 모든 취재 대상에게 적용되는가? → `{general}` 또는 NULL
2. 특정 피해자 속성(이주민·장애인·성소수자 등)이 전제되는가? → `{general}`
3. 특정 사건 유형(범죄·재판)이 전제되는가? → `{crime}`

---

**[2-A] is_citable 재조정**

다음 기준으로 각 조항을 검토하여 is_citable=false 후보를 선별한다:

1. **실용 판단 기준 (2026-05-01 채택):**
   *"Sonnet이 〔 〕 마커 안에 직접 넣어도 어색하지 않은 구체성을 가졌는가?"*
   구체적인 행위 금지·의무가 담겨 있어야 한다. "~해야 한다" 수준의 선언이면 false.
2. 이 조항을 실제 기사 분석 리포트에서 인용할 수 있는가?
3. 상위 조항과 내용이 완전히 중복되는가?

우선 검토 대상 (건수가 많거나 선언적 조항 가능성 높은 곳):
- 신문윤리실천요강 69건 — Tier 2 중 가장 많음
- 인권보도준칙 95건 — Tier 3 중 가장 많음
- 재난보도준칙 43건

**[2-B] 인권보도준칙 개별 컨텍스트 지정**

[2-Pre] 사전 프레임 적용 후, 챕터 기준에서 벗어나는 예외 조항만 개별 조정한다.
나머지 조항은 사전 프레임에 따라 일괄 처리한다.

#### Phase 2 진행 방식

DB에서 조항 내용을 직접 조회하여 초안을 작성하고,
기획자가 조항 단위로 승인·수정한다.
전체를 한 번에 하지 않고 **출처 단위로 나눠서** 진행한다.

#### Phase 2 승인 게이트

기획자 확인 포인트:
- (A) is_citable=false로 내린 조항 중 실제로 인용이 필요한 것이 없는가
- (B) is_citable=true로 유지한 조항이 실제 인용 가능한 수준인가
- (C) 인권보도준칙 컨텍스트 지정이 내용과 일치하는가

교차 감리: 3인 이상 독립 감리 권장 (is_citable 변경은 리포트 품질에 직접 영향)

---

### Phase 3 — 시드 SQL 초안 생성

> **선행 조건**: Phase 1·2 기획자 승인 완료

#### Phase 3 CLI 실행 지시 (Phase 1·2 완료 후 전달)

```
다음 작업을 수행하라.

1. 아래 파일을 순서대로 읽어라:
   - docs/STEP0B_ETHICS_PLAN_v1.0.md
   - docs/_scratch/step0b_contexts_draft.md    (Phase 1 산출물)
   - docs/_scratch/step0b_citable_review.md    (Phase 2 산출물)

2. 아래 경로에 시드 파일을 작성하라:
   supabase/seeds/ethics_codes_context_seed.sql

3. 파일 내용:
   - applicable_contexts UPDATE SQL (출처 단위 일괄 + 개별 예외)
   - is_citable UPDATE SQL (is_citable=false 재조정 목록)
   - 형식: ON CONFLICT DO NOTHING 사용 불가. UPDATE 방식으로 작성.
   - 각 UPDATE 블록 앞에 출처명·건수 주석 필수.

4. 파일 작성 후 다음을 보고하라:
   - applicable_contexts 변경 건수 (출처별)
   - is_citable=false 변경 건수 (출처별)
   - NULL(all) 유지 건수

5. 파일 작성만 하고 DB 실행하지 마라.
   기획자 승인을 기다려라.
```

#### Phase 3 승인 게이트

기획자 확인 포인트:
- (A) UPDATE SQL의 WHERE 조건이 의도한 조항만 정확히 타겟하는가
- (B) 건수가 Phase 1·2 확정 목록과 일치하는가
- (C) NULL 유지 건수가 예상 범위인가

교차 감리: 2인 이상 독립 감리 (SQL 구조 검증 가능한 감리자 포함 권장)

---

## 5. 전체 진행 흐름

```
Phase 1 — 출처 단위 컨텍스트 확정
    ↓
Phase 1 승인 게이트 ─────────→ 2인 이상 독립 감리
    ↓ 승인
Phase 2-Pre — 인권보도준칙 사전 분류 프레임 확정
    ↓ 승인
Phase 2-A — is_citable 재조정
Phase 2-B — 인권보도준칙 컨텍스트 지정
    ↓
Phase 2 승인 게이트 ─────────→ 3인 이상 독립 감리
    ↓ 승인
Phase 3 — SQL 초안 생성 (CLI)
    ↓
Phase 3 승인 게이트 ─────────→ 2인 이상 독립 감리 (SQL 구조 검증)
    ↓ 승인
STEP 2 §8.4 진행 가능
```

---

## 6. 절대 원칙 (MASTER_EXECUTION_PLAN 준용)

1. CLI 자동 UPDATE 금지 — 모든 DB 변경은 기획자가 SQL Editor에서 직접 실행
2. is_citable 일괄 변경 금지 — 실질 내용 확인 후 개별·출처 단위 판단
3. Phase 단위 승인 게이트 — 승인 없이 다음 Phase 진행 금지
4. applicable_contexts NULL = all 원칙 — 범용 조항은 NULL 유지 (빈 배열 사용 금지)

---

## 7. STEP 4 연동 인터페이스 명세 (계약서)

> **목적**: STEP 0-B에서 확정한 applicable_contexts 레이블이 STEP 4에서
> 올바르게 소비될 수 있도록 인터페이스를 미리 명문화한다.
> STEP 4 착수 전에 이 명세를 기준으로 RPC 구현을 검증한다.

### 7.1 컨텍스트 레이블별 RPC 필터링 조건

STEP 4-C에서 구현할 `get_ethics_for_patterns` RPC의 `article_context` 파라미터
기준으로, 각 레이블이 받았을 때 어떤 조항이 포함·제외되어야 하는지 정의한다.

```sql
-- applicable_contexts 필터링 의사코드
-- article_context = _infer_article_context()의 반환값

WHERE (
  applicable_contexts IS NULL                          -- NULL = all 컨텍스트 포함
  OR 'all' = ANY(applicable_contexts)                  -- 명시적 all 태그
  OR article_context = ANY(applicable_contexts)        -- 기사 맥락 일치
)
```

| article_context 반환값 | 포함되는 조항 | 제외되는 조항 |
|---|---|---|
| `'general'` (기본값) | NULL, `{general}` | `{health}`, `{military}`, `{election}`, `{crisis}`, `{disaster}`, `{unification}`, `{crime}` |
| `'health'` | NULL, `{general}`, `{health}` | 나머지 특수 컨텍스트 |
| `'disaster'` | NULL, `{general}`, `{disaster}` | 나머지 특수 컨텍스트 |
| `'crisis'` | NULL, `{general}`, `{crisis}` | 나머지 특수 컨텍스트 |
| `'crime'` | NULL, `{general}`, `{crime}` | 나머지 특수 컨텍스트 |
| `'election'` | NULL, `{general}`, `{election}` | 나머지 특수 컨텍스트 |
| `'military'` | NULL, `{general}`, `{military}` | 나머지 특수 컨텍스트 |
| `'unification'` | NULL, `{general}`, `{unification}` | 나머지 특수 컨텍스트 |

### 7.2 `_infer_article_context()` 확장 명세

STEP 4-C에서 현재 4개(`health`, `disaster`, `court`, `general`)만 정의된
`_infer_article_context()` 함수를 아래 9개 반환값으로 확장해야 한다.
STEP 0-B Phase 1 승인 직후 STEP 4 담당자에게 보강 예약을 통보한다.

```python
def _infer_article_context(article_text: str, pattern_codes: set) -> str:
    """
    기사 원문 키워드 + 확정 패턴 코드로 기사 맥락을 사전 추정.
    반환값: 'health' | 'disaster' | 'crisis' | 'crime' |
            'election' | 'military' | 'unification' | 'general'
    """
    text_sample = article_text[:500]

    # 특수 맥락 키워드 사전 (STEP 0-B Phase 1 확정 컨텍스트와 1:1 대응)
    health_keywords    = ['감염병', '코로나', '백신', '의료', '병원', '질병', '바이러스']
    disaster_keywords  = ['재난', '지진', '화재', '홍수', '사고', '피해', '구조']
    crisis_keywords    = ['자살', '극단적 선택', '자해', '유서', '투신']
    crime_keywords     = ['재판', '판결', '검찰', '기소', '법원', '피의자', '피고인', '수사']
    election_keywords  = ['선거', '여론조사', '후보', '투표', '당선', '공약']
    military_keywords  = ['군사', '작전', '국방', '군대', '병력', '북한 도발']
    unification_keywords = ['남북', '통일', '북한', '조선민주주의인민공화국', '평화통일']

    if any(kw in text_sample for kw in health_keywords):    return 'health'
    if any(kw in text_sample for kw in disaster_keywords):  return 'disaster'
    if any(kw in text_sample for kw in crisis_keywords):    return 'crisis'
    if any(kw in text_sample for kw in crime_keywords):     return 'crime'
    if any(kw in text_sample for kw in election_keywords):  return 'election'
    if any(kw in text_sample for kw in military_keywords):  return 'military'
    if any(kw in text_sample for kw in unification_keywords): return 'unification'
    return 'general'
```

> **주의**: `court`는 STEP 0-B 확정 목록에 없으므로 삭제. `crime`으로 대체한다.
> 키워드 사전은 STEP 7 골든셋 재정비 시점에 성능 기반으로 재조정한다.

### 7.3 Fallback 정책

키워드 휴리스틱이 실패하거나 모호한 경우:
- 기본값 `'general'`을 반환한다.
- `'general'`일 때는 NULL + `{general}` 조항만 포함되므로,
  특수 준칙이 과잉 발동하는 노이즈 없이 안전하게 동작한다.
- 이 fallback은 STEP 0-B의 "NULL = all 원칙"과 함께 안전망 역할을 한다.

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1.0 | 2026-04-29 | 최초 작성. DB 현황 394건 반영. 3 Phase 구조 확정. |
| v1.1 | 2026-05-01 | 5인 교차 감리 반영. `{crime}` 컨텍스트 추가. Tier 2 내 특수 맥락 조항 처리 방침 신설. Phase 1 승인 게이트 (D) 동기화 체크 추가. Phase 2 [2-Pre] 인권보도준칙 사전 분류 프레임 신설. is_citable 실용 판단 기준 명문화. §7 STEP 4 연동 인터페이스 명세 신설. |
| v1.2 | 2026-05-01 | 다중 작업자 운영 체계 반영. Phase별 성격·산출물 경로 제거. 교차 감리 주체 중립화(도구명 → 역할·인원 기준). 진행 방식 주체 특정 표현 제거. 흐름도 단순화. |
