# 메타 패턴 추론 상세 설계 — v1

> 작성일: 2026-04-01 (Claude.ai STEP 79)
> 상태: **Gamnamu 승인 완료** — STEP 81 CLI 작업 기준 문서
> 선행: M6 Phase A+B 완료, STEP 79 설계 세션에서 5개 판단 포인트 확정
> 참조: `DB_AND_RAG_MASTER_PLAN_v4.0.md` 섹션 8, `CR_CHECK_M6_PLAYBOOK.md` STEP 79~85

---

## 1. 확정된 설계 결정 요약

| # | 판단 포인트 | 결정 | 근거 |
|---|---|---|---|
| 1 | 필수/보강 DB 표현 | **옵션 B** — `inference_role` 컬럼 추가 | 구조적 강제로 추론 정확성 보장. 문자열 파싱 의존 제거 |
| 2 | LLM 호출 방식 | **옵션 Y** — 리포트 생성(❷ Sonnet)에 통합 | 발동 빈도 ~10%. 미발동 시 기존 프롬프트와 100% 동일 |
| 3 | 리포트 배치 | **옵션 ②** — 종합 평가 직전 | "개별→구조→종합" 서사 흐름. 발동 시에만 섹션 생성 |
| 4 | 표현 수위 가드레일 | **층위 1만** — 프롬프트 가드레일 | 코드 후처리는 과잉 엔지니어링. STEP 83 벤치마크에서 확인 |
| 5 | 검증 케이스 | **STEP 81에 사전 확인 포함** | 하위 패턴 탐지 여부 먼저 확인 후 테스트 케이스 확정 |


## 2. 파이프라인 최종 흐름

```
기사 → 청킹 → 벡터검색 → ❶ Sonnet Solo(패턴 식별)
  → check_meta_patterns(탐지된 패턴 코드, DB)  ← 새로 추가
  → 규범 조회(get_ethics_for_patterns RPC)
  → ❷ Sonnet(3종 리포트 + [조건부] 메타 패턴 추론 지시 주입)
  → CitationResolver(cite → 규범 원문 치환, 3종 각각 적용)
  → 최종 결과
```

- 메타 패턴 발동 시: ❷ Sonnet 프롬프트에 메타 패턴 추론 블록이 추가됨
- 메타 패턴 미발동 시: ❷ Sonnet 프롬프트는 기존과 100% 동일
- 추가 API 호출 없음. ❷ Sonnet 호출 1회에 통합

---

## 3. DB 변경 — Migration 파일

### 3.1 스키마 변경

`pattern_relations` 테이블에 `inference_role` 컬럼을 추가한다.

```sql
ALTER TABLE public.pattern_relations
ADD COLUMN inference_role TEXT
CHECK (inference_role IN ('required', 'supporting'));
```

- 기존 `variant_of` 관계 10건은 `inference_role = NULL` (해당 없음)
- `inferred_by` 관계에서만 `required` 또는 `supporting` 값 사용

### 3.2 inferred_by 관계 시드 INSERT

마스터 플랜 섹션 8.2 기반. 총 9건.

관계 방향: `source_pattern_id` = 하위 지표, `target_pattern_id` = 메타 패턴.
즉 `(1-1-1) --inferred_by-→ (1-4-1)` = "1-1-1이 탐지되면 1-4-1을 추론할 수 있다"

**1-4-1 (외부 압력에 의한 왜곡)**:

| source (하위 지표) | target (메타) | inference_role | 설명 |
|---|---|---|---|
| 1-1-1 (사실 검증 부실) | 1-4-1 | required | 익명 단일 취재원, 무검증 인용 |
| 1-1-2 (이차 자료 의존) | 1-4-1 | required | 보도자료 받아쓰기 |
| 1-3-2 (선별적 사실 제시) | 1-4-1 | supporting | 이념 편향, 선별적 사실 |
| 1-3-1 (관점 다양성 부족) | 1-4-1 | supporting | 관점 다양성 부족 |

**1-4-2 (상업적 동기에 의한 왜곡)**:

| source (하위 지표) | target (메타) | inference_role | 설명 |
|---|---|---|---|
| 1-7-3 (과장과 맥락 왜곡) | 1-4-2 | required | 낚시성 제목, 과장 |
| 1-7-4 (자극적·선정적 표현) | 1-4-2 | required | 자극적 표현 |
| 1-1-1 (사실 검증 부실) | 1-4-2 | supporting | 무검증 인용 |
| 1-8-2 (디지털 플랫폼 특유 문제) | 1-4-2 | supporting | 뉴스 어뷰징 |
| 1-6-1 (기사의 심층성 부족) | 1-4-2 | supporting | 심층성 부족 |


⚠️ 기존 `variant_of` 관계(10건)는 건드리지 않는다. 새 `inferred_by` 관계만 추가.

⚠️ `1-1-1 → 1-4-1` 과 `1-1-1 → 1-4-2` — 1-1-1은 두 메타 패턴 모두에 관여.
전자에서는 `required`, 후자에서는 `supporting`. `inference_role`이 관계별로 독립적이므로 문제 없음.

---

## 4. 모듈 구조 — `backend/core/meta_pattern_inference.py`

### 4.1 데이터 구조

```python
@dataclass
class MetaPatternResult:
    triggered: bool                    # 추론 발동 여부
    meta_pattern_code: str             # "1-4-1" 또는 "1-4-2"
    meta_pattern_name: str             # "외부 압력에 의한 왜곡"
    confidence: str                    # "low" / "medium" / "high"
    required_matches: list[str]        # 충족된 필수 지표 코드들
    supporting_matches: list[str]      # 충족된 보강 지표 코드들
    reasoning: str                     # 빈 문자열 (Sonnet이 리포트에서 직접 생성)
```

### 4.2 핵심 함수

```python
def check_meta_patterns(
    detected_pattern_codes: list[str],
    sb_url: str,
    sb_key: str,
) -> list[MetaPatternResult]:
```


### 4.3 처리 로직 (Step 1 — Deterministic)

```
1. DB에서 relation_type = 'inferred_by' 인 관계 전체 조회
   SELECT sp.code AS source_code, tp.code AS target_code, pr.inference_role
   FROM pattern_relations pr
   JOIN patterns sp ON sp.id = pr.source_pattern_id
   JOIN patterns tp ON tp.id = pr.target_pattern_id
   WHERE pr.relation_type = 'inferred_by';

2. 메타 패턴별로 그룹화
   예: 1-4-1 → { required: [1-1-1, 1-1-2], supporting: [1-3-2, 1-3-1] }

3. 탐지된 패턴 코드와 대조
   required_matches = detected ∩ required
   supporting_matches = detected ∩ supporting

4. 트리거 조건 확인
   len(required_matches) >= 1 AND len(supporting_matches) >= 1
   → triggered = True

5. 확신도(confidence) 사전 계산
   - required 1개 + supporting 1개 = "low"
   - required 1개 + supporting 2개+ = "medium"
   - required 2개+ + supporting 2개+ = "high"

6. 미충족 → MetaPatternResult(triggered=False) 반환 (에러 없이)
```

### 4.4 안전한 비활성 (Graceful Skip)

- DB에 inferred_by 관계가 0건이어도 에러 없이 빈 리스트 반환
- 탐지된 패턴이 0건이어도 에러 없이 빈 리스트 반환
- DB 조회 실패 시 WARNING 로그 후 빈 리스트 반환 (파이프라인 중단 없음)


---

## 5. 파이프라인 통합 — `pipeline.py` 수정

### 5.1 위치

`analyze_article()` 함수 내, 패턴 매칭(❶) 완료 후, 리포트 생성(❷) 전에 삽입:

```python
# 2. 패턴 매칭 (기존)
pm = match_patterns_solo(chunk_texts, article_text, threshold=vector_threshold)

# 2.5 메타 패턴 추론 (NEW)
from .meta_pattern_inference import check_meta_patterns
meta_results = check_meta_patterns(
    detected_pattern_codes=pm.validated_pattern_codes,
    sb_url=sb_url,
    sb_key=sb_key,
)
triggered_meta = [m for m in meta_results if m.triggered]

# 3. 리포트 생성 (기존, 확장)
rr = generate_report(
    article_text,
    pm.validated_pattern_ids,
    haiku_dicts,
    overall_assessment=result.overall_assessment,
    meta_patterns=triggered_meta,  # NEW — 조건부 전달
)
```

### 5.2 AnalysisResult 확장

```python
@dataclass
class AnalysisResult:
    # ... 기존 필드 ...
    meta_patterns: list = field(default_factory=list)  # MetaPatternResult 리스트
```


---

## 6. 리포트 생성 프롬프트 확장 — `report_generator.py`

### 6.1 generate_report() 시그니처 확장

```python
def generate_report(
    article_text: str,
    pattern_ids: list[int],
    detections: list[dict],
    overall_assessment: str = "",
    meta_patterns: list = None,  # NEW — MetaPatternResult 리스트
) -> ReportResult:
```

### 6.2 조건부 프롬프트 주입

`meta_patterns`가 비어있지 않으면(triggered=True인 건이 있으면),
user_message에 아래 블록을 추가한다:

```
## 구조적 문제 분석 지시 (메타 패턴 추론)

아래 패턴들이 이 기사에서 탐지되어, 메타 패턴 추론 조건이 충족되었습니다.

메타 패턴: {meta_pattern_name} ({meta_pattern_code})
- 충족된 필수 지표: {required_matches}
- 충족된 보강 지표: {supporting_matches}
- 사전 확신도: {confidence}

3종 리포트 각각에서, 종합 평가 직전에 "구조적 문제 분석" 섹션을 작성하세요.

### 표현 수위 가이드라인 (절대 준수)
- 확신도 low → "일부 징후가 관찰됩니다"
- 확신도 medium → "구조적 문제의 가능성이 있습니다"
- 확신도 high → "강한 의심이 됩니다"
- ❌ 절대 금지: "외부 압력이 있었다", "상업적 동기로 작성되었다" 등 단정적 표현
  → CR-Check는 "관점을 제시하는 도구"입니다. 확정 판단을 내리지 않습니다.
```


### 6.3 3종 리포트 톤 차이 (메타 패턴 섹션)

```
- comprehensive(시민용): "이런 징후가 보입니다" — 쉬운 비유로 설명
- journalist(기자용): "구조적 관점에서 검토가 필요합니다" — 건설적 제안
- student(학생용): "이런 점을 생각해볼까요?" — 질문 형식 유도
```

### 6.4 리포트 구조 (메타 패턴 발동 시)

```
## 분석 결과
(직접 탐지된 패턴들에 대한 서술...)

## 구조적 문제 분석        ← 메타 패턴 발동 시에만 존재
(메타 패턴 추론 결과...)

## 종합 평가
(전체를 아우르는 종합 평가...)
```

미발동 시에는 "구조적 문제 분석" 섹션이 아예 없고,
리포트는 기존과 동일하게 "분석 결과 → 종합 평가" 구조.

### 6.5 출력 JSON 확장

```json
{
  "article_analysis": { ... },
  "reports": {
    "comprehensive": "...",
    "journalist": "...",
    "student": "..."
  },
  "meta_patterns": [
    {
      "code": "1-4-2",
      "confidence": "medium",
      "triggered": true
    }
  ]
}
```

`meta_patterns` 필드는 Phase D 아카이빙용. 프론트엔드에서는 당장 사용하지 않음.


---

## 7. STEP 81 CLI 작업 지시

### 7.1 사전 확인 — 하위 패턴 탐지 현황

메타 패턴 모듈 구현 **전에** 먼저 실행:

```bash
SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids A2-13,B-15 --no-report
```

`--no-report` (run_sonnet=False)로 패턴 식별 단계만 실행.
A2-13과 B-15에서 Sonnet Solo가 어떤 하위 패턴을 탐지하는지 확인.

**기대하는 결과**:

| 기사 | 메타 패턴 | 필수 지표 탐지 필요 | 보강 지표 탐지 필요 |
|------|-----------|---------------------|---------------------|
| A2-13 | 1-4-2 (상업적 동기) | 1-7-3 또는 1-7-4 중 1개+ | 1-1-1, 1-8-2, 1-6-1 중 1개+ |
| B-15 | 1-4-1 (외부 압력) | 1-1-1 또는 1-1-2 중 1개+ | 1-3-2, 1-3-1 중 1개+ |

**분기**:
- 필수+보강 모두 탐지 → STEP 83 테스트 케이스 유지
- 필수 미탐지 → 다른 TP 중 메타 패턴 의심 케이스 재선별 (Gamnamu 협의)
- 결과를 보고하고 STOP. STEP 82(Claude.ai 감리) 전까지 다음 작업 금지.

### 7.2 Migration 파일 생성

파일명 패턴: `20260401000000_meta_pattern_inference.sql` (기존 패턴 따를 것)

내용:
1. `ALTER TABLE pattern_relations ADD COLUMN inference_role ...` (섹션 3.1)
2. `INSERT INTO pattern_relations ... inferred_by ...` (섹션 3.2, 9건)
3. `supabase start → supabase db reset` 으로 검증


### 7.3 모듈 구현

`backend/core/meta_pattern_inference.py` 신규 생성.
섹션 4의 데이터 구조, 함수 시그니처, 처리 로직을 그대로 구현.

핵심 원칙:
- inferred_by 관계를 **DB에서 동적 조회**. 코드에 하드코딩 절대 금지.
- DB 조회 실패 시 WARNING 로그 후 빈 리스트 반환 (파이프라인 중단 없음)
- 메타 패턴이 0건 발동이어도 정상 흐름 유지

### 7.4 파이프라인 통합

`pipeline.py` 수정 — 섹션 5 참조.
`report_generator.py` 수정 — 섹션 6 참조.

⚠️ `generate_report()`의 `meta_patterns` 파라미터는 optional.
빈 리스트이거나 None이면 기존과 100% 동일 동작 보장.

### 7.5 기본 동작 확인

구현 완료 후:
1. 메타 패턴 미해당 기사(C2-07)로 파이프라인 실행 → 에러 없이 정상 동작 확인
2. 리포트에 "구조적 문제 분석" 섹션이 **없는** 것 확인
3. 결과 보고 후 STOP

---

## 8. STEP 83 테스트 케이스 (STEP 81 사전 확인 후 확정)

### 잠정 케이스 (플레이북 원안)

| ID | 분류 | 기대 | 확인 사항 |
|---|---|---|---|
| A2-13 | TP, 1-4-2 | 메타 패턴 발동 | 확신도, 표현 수위, 구조적 문제 분석 섹션 |
| B-15 | TP, 1-4-1 | 메타 패턴 발동 | 확신도, 표현 수위, 구조적 문제 분석 섹션 |
| C2-07 | TN | 메타 패턴 미발동 | 구조적 문제 분석 섹션 없음, 에러 없음 |


### 재선별 기준 (사전 확인에서 하위 패턴 미탐지 시)

Dev Set 20건(TP) 중 다음 조건을 충족하는 기사를 대체 후보로 검토:

- 1-4-2 대체: 기대 패턴에 1-7-3 또는 1-7-4가 포함된 기사 (예: B-08, B2-09)
- 1-4-1 대체: 기대 패턴에 1-1-1 또는 1-1-2가 포함된 기사 (예: A-06, B2-10)

---

## 9. 감리 체크리스트 (STEP 82 Claude.ai 감리용)

### 추론 로직
- [ ] inferred_by 관계가 DB에서 동적 조회되는가 (하드코딩 없음)
- [ ] inference_role 컬럼이 required/supporting으로 정확히 구분되는가
- [ ] 트리거 조건 "필수 1개 + 보강 1개 이상"이 코드에 정확히 반영되었는가
- [ ] 확신도 계산 로직이 섹션 4.3의 규칙과 일치하는가

### 통합
- [ ] pipeline.py에서 메타 패턴 체크 위치가 올바른가 (패턴매칭 후, 리포트 전)
- [ ] report_generator.py에 meta_patterns 파라미터가 optional로 추가되었는가
- [ ] 조건부 프롬프트 주입이 섹션 6.2와 일치하는가
- [ ] 표현 수위 가이드라인이 프롬프트에 명시되어 있는가

### 안전한 비활성
- [ ] 메타 패턴 미해당 시 파이프라인이 에러 없이 정상 동작하는가
- [ ] DB 조회 실패 시 graceful하게 빈 리스트를 반환하는가
- [ ] meta_patterns가 None 또는 빈 리스트일 때 기존 리포트와 100% 동일한가

### DB
- [ ] Migration 파일이 기존 패턴(날짜+시퀀스)을 따르는가
- [ ] inference_role CHECK 제약이 정확한가
- [ ] inferred_by 9건이 마스터 플랜 8.2와 일치하는가
- [ ] 기존 variant_of 10건이 영향받지 않는가

---

*이 문서는 2026-04-01 Claude.ai STEP 79에서 작성되었다.*
*Gamnamu 승인 완료. CLI는 이 문서를 Plan Mode에서 먼저 읽은 후 STEP 81 작업에 착수할 것.*

