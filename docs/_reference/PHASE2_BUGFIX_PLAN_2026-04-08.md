# Phase 2 버그픽스 실행 계획

> **작성일**: 2026-04-08
> **상태**: 실행 대기
> **영향 파일**: `backend/core/report_generator.py`, `backend/core/meta_pattern_inference.py`
> **배포 대상**: Railway (main 브랜치 push 시 자동 배포)
> **작업 브랜치**: `fix/phase2-reliability` (main에서 분기)

---

## 배경

Phase E(클라우드 배포) 완료 후, 프로덕션에서 TP 기사 분석 7건 중 4건이 실패.
원인 분석(앙상블 4인 진단 교차검증)으로 3개의 독립 버그를 확정했다.

### 확정 진단

| # | 버그 | 발생 위치 | 영향 | 긴급도 |
|---|------|-----------|------|--------|
| 1 | Phase 2 `_robust_json_parse`가 Sonnet 4.6의 깨진 JSON을 복구하지 못함 | `report_generator.py` L311-320 | id=2 (JSONDecodeError 3/3 실패) | 🔴 |
| 2 | 529 OverloadedError 재시도 백오프가 너무 짧음 (1s→2s→4s, 3회) | `report_generator.py` L450-478 | id=4, 5, 7 (529 3/3 실패) | 🔴 |
| 3 | `inference_role` 컬럼이 프로덕션 DB에 없어 메타 패턴 조회 400 | `meta_pattern_inference.py` L98-103 | 전체 TP 분석 시 메타 패턴 비활성 | 🟡 |


---

## STEP 0: 작업 브랜치 생성

**지시**: main에서 `fix/phase2-reliability` 브랜치를 생성하고 체크아웃하라.

```bash
cd /Users/gamnamu/Documents/cr-check
git checkout main
git pull origin main
git checkout -b fix/phase2-reliability
```

**검증**: `git branch --show-current` → `fix/phase2-reliability`

---

## STEP 1: `_robust_json_parse` 강화 (report_generator.py)

**파일**: `backend/core/report_generator.py`
**위치**: L311-320 (`_robust_json_parse` 함수)

### 현재 코드 (L311-320)

```python
def _robust_json_parse(text: str) -> dict:
    """마크다운 코드블록 제거 + JSON 추출."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON 객체를 찾을 수 없음")

    return json.loads(text[start : end + 1])
```

### 수정 지시

이 함수를 아래의 4단계 폴백 구조로 교체하라.
함수 시그니처와 docstring은 유지하되 내부 로직을 확장한다.

### 교체 코드

```python
def _robust_json_parse(text: str) -> dict:
    """마크다운 코드블록 제거 + 4단계 폴백 JSON 추출.

    Phase 2(Sonnet 4.6)의 한국어 리포트 JSON에서 발생하는
    이스케이프 오류, 후행 쉼표, 마크다운 잔존 등을 처리한다.
    """
    # 전처리: 마크다운 코드블록 제거
    cleaned = re.sub(r"```json\s*", "", text)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()

    # 1차: 직접 파싱 (가장 빠름)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2차: { } 바운더리 추출 후 파싱
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_block = cleaned[start : end + 1]
        try:
            return json.loads(json_block)
        except json.JSONDecodeError:
            pass

        # 3차: 흔한 LLM JSON 오류 정규화 후 재시도
        fixed = json_block
        # 3a: 후행 쉼표 제거 (}, → } / ,] → ])
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
        # 3b: 이스케이프 안 된 줄바꿈을 \\n으로 치환
        #     JSON 문자열 값 내부의 실제 개행문자 처리
        fixed = re.sub(r'(?<=": ")(.*?)(?="[,}\s])',
                       lambda m: m.group(0).replace("\n", "\\n"),
                       fixed, flags=re.DOTALL)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    # 4차: 최후의 수단 — reports 키별로 정규식 추출
    #   comprehensive, journalist, student 리포트 텍스트를 개별 추출
    reports = {}
    for key in ["comprehensive", "journalist", "student"]:
        pattern = rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            reports[key] = match.group(1).replace("\\n", "\n").replace('\\"', '"')

    if len(reports) == 3:
        # article_analysis도 추출 시도
        aa_match = re.search(
            r'"article_analysis"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})', text
        )
        article_analysis = {}
        if aa_match:
            try:
                article_analysis = json.loads(aa_match.group(1))
            except json.JSONDecodeError:
                pass
        logger.warning("_robust_json_parse: 4차 정규식 추출 사용")
        return {"reports": reports, "article_analysis": article_analysis}

    raise ValueError(f"JSON 파싱 4단계 모두 실패: {text[:200]}...")
```

### 검증 방법

수정 후 아래 테스트를 로컬에서 실행하여 기존 동작이 깨지지 않았는지 확인:

```bash
cd /Users/gamnamu/Documents/cr-check
python3 -c "
from backend.core.report_generator import _robust_json_parse
import json

# Case 1: 정상 JSON
r1 = _robust_json_parse('{\"reports\": {\"comprehensive\": \"test\", \"journalist\": \"test\", \"student\": \"test\"}, \"article_analysis\": {}}')
assert 'reports' in r1, 'Case 1 실패'

# Case 2: 마크다운 감싸진 JSON
r2 = _robust_json_parse('\`\`\`json\n{\"reports\": {\"comprehensive\": \"test\", \"journalist\": \"test\", \"student\": \"test\"}, \"article_analysis\": {}}\n\`\`\`')
assert 'reports' in r2, 'Case 2 실패'

# Case 3: 후행 쉼표 포함
r3 = _robust_json_parse('{\"reports\": {\"comprehensive\": \"test\", \"journalist\": \"test\", \"student\": \"test\",}, \"article_analysis\": {},}')
assert 'reports' in r3, 'Case 3 실패'

print('✅ _robust_json_parse 3개 케이스 모두 통과')
"
```

**STEP 1 완료 기준**: 위 테스트가 `✅` 출력으로 통과.


---

## STEP 2: 재시도 로직 개선 — 529 지수 백오프 강화 + 예외 세분화 (report_generator.py)

**파일**: `backend/core/report_generator.py`
**위치**: L435-478 (`generate_report` 함수의 재시도 루프)

### 현재 코드 (L450-478, 재시도 부분)

```python
    # 3. Sonnet 호출 (3종 JSON 반환) + 재시도 로직
    max_retries = 3

    for attempt in range(max_retries):
        try:
            raw_text, in_tok, out_tok = call_sonnet(
                article_text, detections_json, overall_assessment, ethics_context,
                meta_pattern_block=meta_block,
            )
            result_json = _robust_json_parse(raw_text)

            # 구조 검증
            if "reports" not in result_json:
                raise ValueError("'reports' 키 누락")
            reports = result_json["reports"]
            for report_field in ["comprehensive", "journalist", "student"]:
                if report_field not in reports or not reports[report_field]:
                    raise ValueError(f"필수 리포트 '{report_field}' 누락 또는 빈 값")

            article_analysis = result_json.get("article_analysis", {})

            return ReportResult(
                reports=reports,
                article_analysis=article_analysis,
                ethics_refs=ethics_refs,
                sonnet_raw_response=raw_text,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
        except Exception as e:
            logger.error(
                f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
                f"[{type(e).__name__}] {e}"
            )
            if attempt == max_retries - 1:
                raise ValueError(f"리포트 생성 최종 실패: {e}")
            time.sleep(2 ** attempt)  # exponential backoff
```

### 수정 지시

재시도 루프를 아래 코드로 교체하라.
핵심 변경점:
1. `max_retries` 3→5
2. 529(OverloadedError) 전용 긴 백오프 (10s, 20s, 40s, 60s, 60s)
3. 429(RateLimitError) 별도 처리 (즉시 실패, 재시도 무의미)
4. JSON 파싱 실패 시 기존 짧은 백오프 유지 (1s, 2s, 4s...)
5. `import anthropic` 추가 필요 (파일 상단 import 영역에)


### 교체 코드

**import 추가** (파일 상단 `from anthropic import Anthropic` 라인 근처):

```python
import anthropic  # OverloadedError, RateLimitError 등 예외 클래스 접근용
```

**재시도 루프 교체**:

```python
    # 3. Sonnet 호출 (3종 JSON 반환) + 재시도 로직
    max_retries = 5

    for attempt in range(max_retries):
        try:
            raw_text, in_tok, out_tok = call_sonnet(
                article_text, detections_json, overall_assessment, ethics_context,
                meta_pattern_block=meta_block,
            )
            result_json = _robust_json_parse(raw_text)

            # 구조 검증
            if "reports" not in result_json:
                raise ValueError("'reports' 키 누락")
            reports = result_json["reports"]
            for report_field in ["comprehensive", "journalist", "student"]:
                if report_field not in reports or not reports[report_field]:
                    raise ValueError(f"필수 리포트 '{report_field}' 누락 또는 빈 값")

            article_analysis = result_json.get("article_analysis", {})

            return ReportResult(
                reports=reports,
                article_analysis=article_analysis,
                ethics_refs=ethics_refs,
                sonnet_raw_response=raw_text,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )

        except anthropic.APIStatusError as e:
            # 529 Overloaded: 긴 백오프 후 재시도
            if e.status_code == 529:
                wait = min(10 * (2 ** attempt), 60)  # 10, 20, 40, 60, 60
                logger.warning(
                    f"API 과부하(529), {wait}초 후 재시도 "
                    f"({attempt + 1}/{max_retries})"
                )
                if attempt == max_retries - 1:
                    raise ValueError(
                        f"리포트 생성 최종 실패 (API 과부하 {max_retries}회): {e}"
                    )
                time.sleep(wait)
            # 429 Rate Limit: 재시도 무의미, 즉시 실패
            elif e.status_code == 429:
                logger.error(f"API 한도 초과(429): {e}")
                raise ValueError(f"리포트 생성 실패 (API 한도 초과): {e}")
            else:
                logger.error(
                    f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
                    f"[API {e.status_code}] {e}"
                )
                if attempt == max_retries - 1:
                    raise ValueError(f"리포트 생성 최종 실패: {e}")
                time.sleep(2 ** attempt)

        except (json.JSONDecodeError, ValueError) as e:
            # JSON 파싱 실패: 짧은 백오프 후 재시도 (다른 출력을 기대)
            logger.error(
                f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
                f"[{type(e).__name__}] {e}"
            )
            if attempt == max_retries - 1:
                raise ValueError(f"리포트 생성 최종 실패: {e}")
            time.sleep(2 ** attempt)  # 1, 2, 4, 8, 16

        except Exception as e:
            # 기타 예외 (네트워크 등)
            logger.error(
                f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
                f"[{type(e).__name__}] {e}"
            )
            if attempt == max_retries - 1:
                raise ValueError(f"리포트 생성 최종 실패: {e}")
            time.sleep(2 ** attempt)
```

### 검증 방법

수정 후 문법 오류 확인:

```bash
cd /Users/gamnamu/Documents/cr-check
python3 -c "from backend.core.report_generator import generate_report; print('✅ import 성공')"
```

**STEP 2 완료 기준**: import 성공 메시지 확인.


---

## STEP 3: 메타 패턴 `inference_role` 컬럼 추가 (Supabase SQL + 코드 검증)

이 STEP은 두 부분으로 구성된다:
- **STEP 3a**: 프로덕션 Supabase SQL Editor에서 직접 실행 (사람이 수행)
- **STEP 3b**: 로컬 마이그레이션 파일 생성 (CLI가 수행)

### 원인

`meta_pattern_inference.py` L98-103의 REST API 쿼리:
```python
r = httpx.get(
    f"{sb_url}/rest/v1/pattern_relations"
    "?select=source_pattern_id,target_pattern_id,inference_role"
    "&relation_type=eq.inferred_by",
    ...
)
```

이 쿼리가 `inference_role` 컬럼을 SELECT하지만, 프로덕션 DB `pattern_relations` 테이블에는
이 컬럼이 존재하지 않는다 (M6 Phase C에서 코드에 추가했으나 마이그레이션이 누락됨).

### STEP 3a: 프로덕션 DB에 컬럼 추가 (사람이 수행)

프로덕션 Supabase Dashboard → SQL Editor에서 아래 SQL을 실행한다:

```sql
-- 1. inference_role 컬럼 추가
ALTER TABLE public.pattern_relations
ADD COLUMN IF NOT EXISTS inference_role TEXT
CHECK (inference_role IN ('required', 'supporting'));

-- 2. 기존 inferred_by 관계에 inference_role 값 채우기
-- (현재 pattern_relations에 inferred_by 관계가 있다면)
-- 아래는 확인 쿼리:
SELECT id, source_pattern_id, target_pattern_id, relation_type, description
FROM public.pattern_relations
WHERE relation_type = 'inferred_by';
```

> **주의**: CHECK 제약조건의 값이 `required` / `supporting`인지,
> `indicator` / `trigger` / `meta_target`인지 코드와 대조 필요.
> `meta_pattern_inference.py` L138-139를 보면:
> `meta_groups[target_code][role].append(source_code)`
> 여기서 `role`은 `rel.get("inference_role", "")` 값이며,
> L143에서 `group["required"]`, `group["supporting"]`으로 접근하므로
> **값은 `required` / `supporting`이 맞다.**

### STEP 3b: 마이그레이션 파일 생성 (CLI가 수행)

아래 파일을 생성하라:

```
supabase/migrations/20260408000000_add_inference_role.sql
```

내용:

```sql
-- Phase 2 Bugfix: inference_role 컬럼 추가
-- meta_pattern_inference.py의 REST API 쿼리가 이 컬럼을 참조함
ALTER TABLE public.pattern_relations
ADD COLUMN IF NOT EXISTS inference_role TEXT
CHECK (inference_role IN ('required', 'supporting'));

COMMENT ON COLUMN public.pattern_relations.inference_role IS
  'inferred_by 관계에서 해당 패턴의 역할: required(필수 지표) / supporting(보강 지표)';
```

### 검증 방법

STEP 3a 실행 후, 프로덕션에서 확인:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pattern_relations'
ORDER BY ordinal_position;
```

`inference_role` 컬럼이 목록에 나타나면 성공.

또한, 기존 `inferred_by` 레코드가 있다면 `inference_role` 값을 채워야
메타 패턴 추론이 실제로 작동한다. 현재 레코드가 0건이라면 이 STEP은
"조회 실패 → 건너뜀" 에서 "조회 성공 → 0건 → 건너뜀"으로 개선되는 수준이며,
메타 패턴 기능 전체 활성화는 별도 데이터 시딩이 필요하다.

**STEP 3 완료 기준**: 프로덕션 DB에 `inference_role` 컬럼 존재 확인 + 마이그레이션 파일 생성.


---

## STEP 4: 커밋 + PR 생성

### 지시

```bash
cd /Users/gamnamu/Documents/cr-check
git add backend/core/report_generator.py
git add backend/core/meta_pattern_inference.py  # 변경이 있는 경우만
git add supabase/migrations/20260408000000_add_inference_role.sql
git commit -m "fix: Phase 2 reliability — robust JSON parse, 529 backoff, inference_role migration

- _robust_json_parse: 4단계 폴백 (직접→바운더리→정규화→정규식 추출)
- 529 OverloadedError: 재시도 5회, 10-60초 지수 백오프
- 429 RateLimitError: 즉시 실패 (재시도 무의미)
- inference_role 컬럼 마이그레이션 추가

Fixes: id=2 JSONDecodeError, id=4,5,7 OverloadedError, 메타패턴 400"
git push origin fix/phase2-reliability
```

> **주의**: main 직접 push는 자동 배포를 트리거한다.
> 반드시 PR을 통해 병합할 것.

**STEP 4 완료 기준**: GitHub에 `fix/phase2-reliability` 브랜치가 push됨.

---

## STEP 5: 로컬 E2E 검증 (선택, 권장)

배포 전에 로컬에서 TP 기사 1건을 분석해보는 것을 권장한다.
로컬 Supabase가 실행 중이라면:

```bash
cd /Users/gamnamu/Documents/cr-check
python3 -c "
from backend.core.pipeline import analyze_article
result = analyze_article('https://n.news.naver.com/mnews/article/119/0003076017?sid=100')
print('리포트 길이:', len(result.get('comprehensive_report', '')))
print('share_id:', result.get('share_id', 'N/A'))
"
```

로컬 Supabase가 없다면 STEP 6으로 직행 (프로덕션에서 직접 검증).

---

## STEP 6: PR 병합 + 프로덕션 배포

1. GitHub에서 PR `fix/phase2-reliability` → `main` 생성
2. 변경 파일 목록 확인 (report_generator.py, migration 파일)
3. Merge
4. Railway + Vercel 자동 배포 대기

**STEP 6 완료 기준**: Railway 배포 로그에서 "Application startup complete" 확인.

---

## STEP 7: 프로덕션 검증

### 7a. 헬스체크

```
GET https://cr-check-production.up.railway.app/health
→ {"status":"healthy","api_key_configured":true}
```

### 7b. 기존 실패 기사 재검증

아래 기사 중 1건을 프로덕션에서 다시 분석한다.
(캐시가 있으므로, 캐시를 우회하려면 다른 TP 기사 URL을 사용하거나
DB에서 해당 articles 레코드를 삭제해야 함)

### 7c. Railway 로그 확인

- `529` → 긴 백오프 후 재시도 성공 여부
- `JSONDecodeError` → 4단계 폴백으로 복구 여부
- `메타 패턴 DB 조회 실패` → 더 이상 발생하지 않는지 확인

**STEP 7 완료 기준**: TP 기사 1건이 3종 리포트 정상 생성 + share_id 발급.

---

## STEP 8: 세션 컨텍스트 갱신 (v24 → v25)

검증 완료 후, `SESSION_CONTEXT` 문서를 v25로 갱신한다.
아래 내용을 반영:

- Phase 2 Bugfix 완료 (STEP 1~3 내용 요약)
- `_robust_json_parse` 4단계 폴백 적용
- 재시도 로직: 529 최대 5회 / 10-60초 백오프, 429 즉시 실패
- `inference_role` 컬럼 프로덕션 추가
- 주의사항 추가: "`import anthropic` — OverloadedError/RateLimitError 예외 분기에 필요"

---

## 부록: API Tier 확인 (운영 조치)

이 버그픽스와 별도로, Anthropic 콘솔에서 API Tier를 확인할 것을 권장한다.

- **확인 경로**: https://console.anthropic.com → Settings → Limits
- **확인 항목**: 현재 Tier, TPM(분당 토큰), RPM(분당 요청) 한도
- **권장 조치**: Tier 1 이하라면 크레딧 추가로 Tier 2 이상 확보

529 에러가 지속적으로 발생한다면, 코드 수정만으로는 한계가 있으며
API 사용량 한도 자체를 높여야 근본 해결된다.

---

*이 문서는 2026-04-08에 작성되었다.*
*앙상블 진단(Claude + 마누스 + 제미나이 + 퍼플렉시티) 교차검증 결과를 기반으로 한다.*
