# CR-Check OpenRouter 도입 플레이북 v2.2

> **문서 상태**: 실행 준비 완료 — Phase F 완료 후 착수
> **작성일**: 2026-04-10
> **근거**: Claude 설계 + 감리자 5인 + 재감리 3인 + 실제 코드 확인(2026-04-10)
> **선행 조건**: Phase F(Reserved Test Set 73건 벤치마크) 완료 필수
> **PR 브랜치**: `feature/openrouter-phase1`

---

## 0. 다음 세션의 Claude에게

### 이 문서의 역할

이 문서는 CR-Check Phase 1 모델을 비용 효율적으로 교체하기 위한
**OpenRouter 도입 플레이북**이다.

OpenRouter는 "모델 오디션 플랫폼" 겸 "상시 대기 교환대"이다.
오디션(벤치마크)이 끝나면 확정 모델의 직접 API로 전환하고,
교환대 코드는 비활성 상태로 보존한다.
새 모델 출시 시 환경변수 하나로 다시 활성화할 수 있다.

```
현재 상태         오디션 기간                확정 후
───────────      ─────────────────       ──────────────────────
코드 → Anthropic    코드 → OpenRouter → 다중 모델    코드 → 확정 모델 직접 API
(직통)            (교환대 경유, 비교 테스트)       (다시 직통, 교환대 대기)
```

### 핵심 원칙

1. **Phase 2(`report_generator.py`)는 일체 변경하지 않는다.** Sonnet 4.6 고정.
2. **Phase 1(`pattern_matcher.py`)의 API 호출 부분만 PHASE1_PROVIDER 분기로 감싼다.**
3. **기존 함수 구조를 유지한다.** 함수형 + 동기. 클래스 전환 금지.
4. **STEP 단위 실행.** 각 STEP 완료 후 반드시 Gamnamu 승인을 받고 다음으로 넘어간다.

### 선행 조건 확인

- [ ] Phase F(Reserved Test Set 73건) 벤치마크 완료
- [ ] Sonnet 4.5 기준선(Recall, Precision, F1, JSON 파싱 성공률) 확립
- [ ] OpenRouter 계정 생성 + 크레딧 $10 충전

---

## 1. 실제 코드 구조 (2026-04-10 확인)

### 1.1 `pattern_matcher.py` (657줄)

```python
# 구조: 함수형 + 동기
from anthropic import Anthropic    # 동기 SDK
from openai import OpenAI          # 동기 SDK (이미 import됨, 임베딩용)

SONNET_MODEL = "claude-sonnet-4-5-20250929"   # 모듈 상수 (줄 35)
_SONNET_SOLO_PROMPT = """..."""               # 657줄 시스템 프롬프트 (줄 208~)

def match_patterns_solo(chunks, article_text, threshold=None):
    # ...벡터 검색, ★ 마크 적용...
    # ▼ 교체 대상: 줄 575~585
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2048,
        system=_SONNET_SOLO_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
    )
    raw = response.content[0].text
    # ...파싱, 밸리데이션...
```

**핵심**: 줄 575~585의 `Anthropic()` 클라이언트 생성 + `client.messages.create()` 호출
부분만 `PHASE1_PROVIDER` 분기로 감싸면 된다.
나머지(벡터 검색, ★ 마크 적용, `_parse_solo_response()`, `validate_pattern_codes()`)는
모델에 무관하므로 그대로 유지.

### 1.2 `storage.py` (408줄)

```python
# 줄 370~371 — 하드코딩된 모델 ID (교체 대상)
"phase1_model": "claude-sonnet-4-5-20250929",
"phase2_model": "claude-sonnet-4-6",
```

### 1.3 `pipeline.py` (288줄)

```python
# 줄 22 — 함수 import
from .pattern_matcher import match_patterns_solo, PatternMatchResult

# 줄 96 — 동기 함수 호출
pm = match_patterns_solo(chunk_texts, article_text, threshold=vector_threshold)
```

### 1.4 `report_generator.py` (697줄)

변경 없음. `from anthropic import Anthropic` + `import anthropic`
(529/429 에러 분기용)로 Anthropic SDK에 강하게 결합. 건드리지 않는다.

### 1.5 `benchmark_pipeline_v3.py` (545줄)

```python
# 이미 model_override 기능 존재 (줄 95~97)
if model_override:
    import core.pattern_matcher as pm_module
    pm_module.SONNET_MODEL = model_override  # monkey-patching

# Phase 1만 실행 (줄 125)
result = analyze_article(article_text, run_sonnet=False)
```

### 1.6 `requirements.txt` (11줄)

```
openai>=1.0.0,<2.0.0    # 이미 존재 — 신규 의존성 추가 불필요
anthropic>=0.49.0,<1.0.0  # Phase 2 + Phase 1 기본 경로
```

---

## 2. 환경변수 설계

### 프로덕션 (Railway)

```bash
# ─── 기존 유지 (4개) ───
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...

# ─── 신규 추가 ───
PHASE1_PROVIDER=anthropic          # "anthropic" | "openrouter" | "direct"
PHASE1_MODEL=                      # 비워두면 기본값 (SONNET_MODEL 상수)

# ─── OpenRouter 모드 시에만 ───
OPENROUTER_API_KEY=sk-or-...
PHASE1_FALLBACK_MODEL=             # 폴백 모델 (선택)

# ─── Direct 모드 시에만 ───
PHASE1_DIRECT_PROVIDER=deepseek    # "deepseek" | "google" | "qwen"
PHASE1_API_KEY=sk-...
```

### 시나리오별 설정

```
A) 기본값 (현재와 동일):
   PHASE1_PROVIDER=anthropic  →  Anthropic SDK 직접 호출

B) OpenRouter 오디션:
   PHASE1_PROVIDER=openrouter
   PHASE1_MODEL=haiku-4.5     →  레지스트리에서 full ID로 매핑

C) 확정 후 직통 연결:
   PHASE1_PROVIDER=direct
   PHASE1_DIRECT_PROVIDER=deepseek
   PHASE1_API_KEY=sk-deepseek-...

D) 상시 대기 교환대 재활성화:
   PHASE1_PROVIDER=openrouter  →  새 모델 테스트 후 C로 복귀
```

---

## 3. STEP 단위 실행 계획

### Phase α: 로컬 검증 (반나절)

---

#### STEP 1: 브랜치 생성

**설명**: main에서 feature 브랜치를 분기한다.

**CLI 프롬프트**:
```
git checkout main
git pull origin main
git checkout -b feature/openrouter-phase1
```

**완료 기준**: `feature/openrouter-phase1` 브랜치에서 작업 시작.

---

#### STEP 2: pattern_matcher.py 수정 — PHASE1_PROVIDER 삼중 분기

**설명**: `match_patterns_solo()` 함수 내부의 Anthropic API 호출 부분(줄 575~585)을
`PHASE1_PROVIDER` 환경변수에 따라 분기하는 래퍼 함수로 교체한다.
기존 함수 구조(함수형 + 동기)를 유지한다.

**수정 대상**: `backend/core/pattern_matcher.py`

**수정 내용**:

(A) 파일 상단(줄 35 부근)에 모듈 상수 추가:

```python
# ── OpenRouter 설정 (Phase 1 모델 교체 지원) ──────────────────

PHASE1_PROVIDER = os.environ.get("PHASE1_PROVIDER", "anthropic")

OPENROUTER_MODEL_REGISTRY = {
    "haiku-4.5":        "anthropic/claude-haiku-4-5-20251001",
    "sonnet-4.5":       "anthropic/claude-sonnet-4-5-20250929",
    "gemini-2.5-pro":   "google/gemini-2.5-pro-preview",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "deepseek-v3.2":    "deepseek/deepseek-chat",
    "deepseek-r1":      "deepseek/deepseek-r1-0528",
    "qwen3-235b":       "qwen/qwen3-235b-a22b",
    "glm-5":            "z-ai/glm-5",
}

THINKING_MODELS = {
    "deepseek/deepseek-r1-0528",
    "qwen/qwen3-235b-a22b",
    "qwen/qwen3-235b-a22b:thinking",
}

DIRECT_API_ENDPOINTS = {
    "deepseek":  "https://api.deepseek.com",
    "google":    "https://generativelanguage.googleapis.com/v1beta/openai/",
    "qwen":      "https://dashscope.aliyuncs.com/compatible-mode/v1",
}
```

(B) `match_patterns_solo()` 내부의 줄 575~585 교체:

```python
    # 3. Phase 1 모델 호출 — PHASE1_PROVIDER 분기
    raw, actual_model = _call_phase1(user_message)
```

(C) 새 함수 `_call_phase1()` 추가 (match_patterns_solo 위에):

```python
def _call_phase1(user_message: str) -> tuple[str, str]:
    """Phase 1 모델 호출 래퍼. PHASE1_PROVIDER에 따라 분기.
    반환: (raw_text, actual_model_id)
    """
    provider = PHASE1_PROVIDER
    model_env = os.environ.get("PHASE1_MODEL")

    if provider == "openrouter":
        model_key = model_env or "haiku-4.5"
        model_id = OPENROUTER_MODEL_REGISTRY.get(model_key, model_key)
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            default_headers={
                "HTTP-Referer": "https://cr-check.vercel.app",
                "X-Title": "CR-Check",
            },
        )
        return _call_openai_compat(client, model_id, user_message, provider)

    elif provider == "direct":
        direct_prov = os.environ.get("PHASE1_DIRECT_PROVIDER", "deepseek")
        model_id = model_env or "deepseek-chat"
        client = OpenAI(
            base_url=DIRECT_API_ENDPOINTS[direct_prov],
            api_key=os.environ["PHASE1_API_KEY"],
        )
        return _call_openai_compat(client, model_id, user_message, provider)

    else:  # anthropic (기본값)
        model_id = model_env or SONNET_MODEL
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=model_id,
            max_tokens=2048,
            system=_SONNET_SOLO_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.0,
        )
        raw = response.content[0].text
        logger.info(
            f"[Phase1] provider=anthropic | model={model_id} | "
            f"in={response.usage.input_tokens} out={response.usage.output_tokens}"
        )
        return raw, model_id


def _call_openai_compat(client: OpenAI, model_id: str,
                         user_message: str, provider: str) -> tuple[str, str]:
    """OpenAI 호환 API 호출 (OpenRouter / Direct 공용)."""
    kwargs = dict(
        model=model_id,
        max_tokens=2048,
        temperature=0.0,
        messages=[
            {"role": "system", "content": _SONNET_SOLO_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    # extra_body 안전 조립
    extra_body = {}

    if model_id in THINKING_MODELS:
        extra_body["thinking"] = {"type": "enabled", "budget_tokens": 1024}
        kwargs["temperature"] = 1  # Thinking 모드 API 요구사항

    fallback = os.environ.get("PHASE1_FALLBACK_MODEL")
    if fallback and provider == "openrouter":
        extra_body["models"] = [fallback]

    if extra_body:
        kwargs["extra_body"] = extra_body

    response = client.chat.completions.create(**kwargs)

    raw = response.choices[0].message.content
    actual_model = getattr(response, "model", model_id)

    # 비용 로깅
    usage = response.usage
    cost = getattr(usage, "cost", None) if usage else None
    cost_str = f" | cost=${cost:.6f}" if cost else ""
    logger.info(
        f"[Phase1] provider={provider} | model={actual_model} | "
        f"in={usage.prompt_tokens if usage else '?'} "
        f"out={usage.completion_tokens if usage else '?'}{cost_str}"
    )

    return raw, actual_model
```

(D) `_parse_solo_response()` 앞에 `<think>` 태그 전처리 추가:

```python
def _clean_thinking_tags(text: str) -> str:
    """Thinking 모델의 <think> 블록 제거."""
    return re.sub(r'<think>.*?(?:</think>|$)', '', text, flags=re.DOTALL).strip()
```

그리고 `_parse_solo_response()` 첫 줄에:
```python
    text = _clean_thinking_tags(text)   # 0차 전처리
    text = re.sub(r"```json\s*", "", text)  # 기존 1차
    ...
```

(E) `match_patterns_solo()`의 반환부에서 `actual_model`을
`PatternMatchResult`에 전달할 필드가 필요하면 추가.
(또는 pipeline.py에서 별도 반환값으로 처리.)

**완료 기준**: `PHASE1_PROVIDER=anthropic`(기본값)일 때 기존과 동일하게 동작.

---

#### STEP 3: storage.py 수정 — 모델 ID 동적 기록

**설명**: 하드코딩된 모델 ID를 파이프라인에서 전달받는 인자로 교체한다.

**수정 대상**: `backend/core/storage.py` 줄 370~371

**수정 내용**:

(A) `save_analysis_result()` 시그니처에 `phase1_model`, `phase2_model` 인자 추가
(기존 `result` 인자 뒤에):

```python
def save_analysis_result(
    url, title, publisher, journalist, publish_date,
    result,
    phase1_model: str = "claude-sonnet-4-5-20250929",  # 기본값 = 기존 하드코딩
    phase2_model: str = "claude-sonnet-4-6",
) -> str | None:
```

(B) 줄 370~371의 하드코딩을 인자로 교체:

```python
    # 기존:
    "phase1_model": "claude-sonnet-4-5-20250929",
    "phase2_model": "claude-sonnet-4-6",

    # 변경:
    "phase1_model": phase1_model,
    "phase2_model": phase2_model,
```

**완료 기준**: 기본값이 있으므로, 기존 호출부를 수정하지 않아도 동작.

---

#### STEP 4: pipeline.py 수정 — actual_model 전달

**설명**: `match_patterns_solo()`에서 반환된 `actual_model`을
`save_analysis_result()`로 전달하는 경로를 만든다.

**수정 방법** (두 가지 중 택 1):

*방법 A*: `PatternMatchResult`에 `actual_model` 필드 추가 → pipeline.py에서 꺼내서 storage로 전달.

*방법 B*: `match_patterns_solo()`가 `(PatternMatchResult, str)` 튜플을 반환하도록 변경 → pipeline.py에서 분해.

**권장**: 방법 A가 기존 코드 변경 범위가 적다.
`PatternMatchResult` dataclass에 `phase1_model: str = ""` 필드 추가 후,
`match_patterns_solo()` 끝에서 `result.phase1_model = actual_model` 설정.

**완료 기준**: pipeline.py에서 `pm.phase1_model`을 storage에 전달.

---

#### STEP 5: main.py 수정 — storage 호출부

**설명**: `main.py`에서 `save_analysis_result()`를 호출하는 부분에
`phase1_model` 인자를 전달한다.

**수정 내용**: pipeline 결과에서 `phase1_model`을 꺼내 storage로 넘기는 경로 확인.
(pipeline.py가 storage를 직접 호출하는 구조라면 pipeline.py에서 처리되므로
main.py 수정은 불필요할 수 있음 — 실제 호출 경로 확인 후 결정.)

**완료 기준**: DB에 실제 사용된 모델 ID가 기록됨.

---

#### STEP 6: 로컬 E2E 테스트

**설명**: 기본값(`PHASE1_PROVIDER=anthropic`)에서 기존과 동일하게 동작하는지 확인.

**테스트 1 — Anthropic 경로 (기존 동작 확인)**:
```bash
cd /Users/gamnamu/Documents/cr-check
SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids B-11 C2-07
```

**테스트 2 — OpenRouter 경로 (Haiku 4.5)**:
```bash
SUPABASE_LOCAL=1 PHASE1_PROVIDER=openrouter PHASE1_MODEL=haiku-4.5 \
  OPENROUTER_API_KEY=sk-or-... \
  python scripts/benchmark_pipeline_v3.py --ids B-11 C2-07
```

**테스트 3 — <think> 태그 전처리 스모크 테스트**:
```python
# Python REPL에서
from backend.core.pattern_matcher import _clean_thinking_tags

sample = '<think>분석 중...</think>{"patterns": []}'
assert '"patterns"' in _clean_thinking_tags(sample)

truncated = '<think>분석 중...'
assert _clean_thinking_tags(truncated) == ''

print("✓ think 태그 전처리 통과")
```

**완료 기준**:
- 테스트 1: 기존 Sonnet 4.5와 동일한 결과
- 테스트 2: Haiku 4.5 경유로 JSON 파싱 성공, 패턴 코드 반환
- 테스트 3: 스모크 테스트 통과

---

### Phase β: 다중 모델 벤치마크 (1~2일)

---

#### STEP 7: 벤치마크 스크립트 확장

**설명**: 기존 `benchmark_pipeline_v3.py`의 `model_override` 기능을
`PHASE1_PROVIDER` 환경변수 분기와 연동한다.
기존 스크립트 확장이 어려우면 별도 `scripts/benchmark_openrouter.py`를 작성한다.

**핵심 로직**:
```python
# 기존 monkey-patching 대신, 환경변수로 제어
# 실행 예시:
# PHASE1_PROVIDER=openrouter PHASE1_MODEL=haiku-4.5 python scripts/benchmark_pipeline_v3.py
```

**벤치마크 시 user_prompt 동적 생성 주의**:
`golden_dataset_final.json`에는 `prompt` 필드가 없다.
기사 텍스트 로드 + 벡터 검색 + ★ 마크 적용 → user_prompt 동적 생성 경로를
스크립트가 `match_patterns_solo()` 전체를 호출하는 구조로 유지한다.
(기존 스크립트가 `analyze_article(run_sonnet=False)` 호출하는 방식 그대로.)

**완료 기준**: 환경변수 변경만으로 다른 모델 벤치마크 실행 가능.

---

#### STEP 8: Reserved Test Set 73건 멀티모델 벤치마크

**설명**: Phase F에서 확립한 Sonnet 4.5 기준선 대비, 5개 모델의 성능을 비교.

**실행 순서**:
```bash
# 기준선 (Phase F 결과 재사용 또는 재실행)
SUPABASE_LOCAL=1 PHASE1_PROVIDER=anthropic \
  python scripts/benchmark_pipeline_v3.py > results_sonnet45.txt

# 실험 1: Haiku 4.5
SUPABASE_LOCAL=1 PHASE1_PROVIDER=openrouter PHASE1_MODEL=haiku-4.5 \
  OPENROUTER_API_KEY=sk-or-... \
  python scripts/benchmark_pipeline_v3.py > results_haiku45.txt

# 실험 2: Gemini 2.5 Pro
SUPABASE_LOCAL=1 PHASE1_PROVIDER=openrouter PHASE1_MODEL=gemini-2.5-pro \
  OPENROUTER_API_KEY=sk-or-... \
  python scripts/benchmark_pipeline_v3.py > results_gemini25pro.txt

# 실험 3: DeepSeek V3.2
SUPABASE_LOCAL=1 PHASE1_PROVIDER=openrouter PHASE1_MODEL=deepseek-v3.2 \
  OPENROUTER_API_KEY=sk-or-... \
  python scripts/benchmark_pipeline_v3.py > results_deepseek.txt

# 실험 4: Qwen3 235B
SUPABASE_LOCAL=1 PHASE1_PROVIDER=openrouter PHASE1_MODEL=qwen3-235b \
  OPENROUTER_API_KEY=sk-or-... \
  python scripts/benchmark_pipeline_v3.py > results_qwen3.txt
```

**예상 비용**: 73건 × 5모델 = 365회 → 약 $7~10
**예상 시간**: 모델당 약 60분 → 총 약 5시간 (순차 실행)

**완료 기준**: 5개 결과 파일 생성.

---

#### STEP 9: 비교 리포트 작성

**설명**: 벤치마크 결과를 `docs/PHASE1_MODEL_BENCHMARK.md`로 정리.

**비교 항목**:
- Pattern Recall / Precision / F1
- JSON 파싱 성공률 (%)
- 평균 레이턴시 (초)
- 1건당 실측 비용 (Railway 로그 또는 OpenRouter usage.cost)
- TN False Positive 비율

**완료 기준**: 최적 모델 확정 근거 문서화.

---

### Phase γ: 프로덕션 전환 (10분 ~ 반나절)

---

#### STEP 10: 최적 모델 확정

**기준**: Sonnet 4.5 대비 Recall 90% 이상 유지 + 비용 50%+ 절감.
만족하는 모델이 없으면 Sonnet 4.5 유지 (코드는 보존, 비활성).

---

#### STEP 11: Railway 환경변수 설정

**시나리오별**:
- 최적 모델이 Haiku 4.5이면 → `PHASE1_PROVIDER=anthropic`, `PHASE1_MODEL=claude-haiku-4-5-20251001`
  (같은 Anthropic이므로 OpenRouter 불필요, 직접 API 유지)
- 최적 모델이 타사이면 → `PHASE1_PROVIDER=direct`, `PHASE1_DIRECT_PROVIDER=...`, `PHASE1_API_KEY=...`

---

#### STEP 12: PR 생성 + 코드 리뷰

```
git add -A
git commit -m "feat: OpenRouter Phase 1 모델 교체 지원 (PHASE1_PROVIDER 삼중 분기)"
git push origin feature/openrouter-phase1
# → GitHub에서 PR 생성 → main 병합
```

---

#### STEP 13: 프로덕션 재검증

TP 3건 + TN 3건을 프로덕션 URL(`https://cr-check.vercel.app`)에서 실제 분석 실행.
Railway 로그에서 `[Phase1]` 키워드로 모델명·비용 확인.

---

#### STEP 14: 모니터링 체제 전환

- Railway 로그에서 `[Phase1]` 키워드로 모델명 + 응답시간 + 비용 추적
- 월 1회 골든셋 5건 샘플링 → 기준선 대비 성능 드리프트 체크
- 새 모델 출시 시: `PHASE1_PROVIDER=openrouter`로 교환대 재활성화 → 벤치마크 → 재확정

---

## 4. 위험 요소 및 롤백

### 롤백 (3분 이내)

```
Level 1 (즉시): PHASE1_PROVIDER=anthropic으로 환경변수 변경
  → 기존 Sonnet 4.5 직통 연결 복귀

Level 2 (5분): git revert → PR → 자동 배포

Level 3 (비상): OPENROUTER_API_KEY 환경변수 삭제
```

### JSON 파싱 안정성

| 모델 유형 | 예상 문제 | 대응 |
|-----------|----------|------|
| Anthropic 계열 | 마크다운 감싸기 | 기존 2차 폴백 |
| DeepSeek R1 | `<think>` 태그 + JSON | `_clean_thinking_tags` 0차 전처리 |
| Qwen3 | trailing comma | 기존 `_fix_llm_json` 2차 폴백 |
| Gemini | 간헐적 설명문 삽입 | 기존 3차 바운더리 추출 |

### 데이터 보안

- OpenRouter는 "데이터를 학습에 사용하지 않음" 명시
- ZDR(Zero Data Retention) 옵션: `extra_body={"provider": {"zdr": true}}`

---

## 5. 비용 시뮬레이션

### Phase 1 요청 1건당 (Input 12K tok + Output 2K tok)

| 모델 | 1회 비용 | vs 현재 절감률 |
|------|---------|---------------|
| **Sonnet 4.5 (현재)** | **$0.066** | 기준선 |
| Haiku 4.5 | $0.022 | −67% |
| Gemini 2.5 Flash | $0.009 | −87% |
| DeepSeek V3.2 | $0.004 | −94% |
| Qwen3 235B | $0.009 | −86% |

### 오디션 비용

73건 × 5모델 = 365회 → 약 $7~10 (OpenRouter 크레딧)

---

## 6. 전체 수정 파일 요약

| 파일 | 변경 내용 | 줄 수 참조 |
|------|----------|-----------|
| `backend/core/pattern_matcher.py` | 삼중 분기 + `_call_phase1` + `_clean_thinking_tags` + 비용 로깅 | 줄 35, 줄 530~585 |
| `backend/core/storage.py` | 모델 ID 하드코딩 → 함수 인자 | 줄 300, 370~371 |
| `backend/core/pipeline.py` | `actual_model` 전달 경로 | 줄 96 부근 |
| `backend/main.py` | storage 호출부 수정 (필요 시) | 확인 필요 |
| `scripts/benchmark_pipeline_v3.py` | `PHASE1_PROVIDER` 환경변수 연동 (또는 별도 스크립트) | 줄 95~97 |
| Railway 환경변수 | `PHASE1_PROVIDER`, `OPENROUTER_API_KEY` 등 | — |
| `backend/core/report_generator.py` | **변경 없음** | — |
| `backend/requirements.txt` | **변경 없음** (openai 이미 존재) | — |

---

## 7. 감리자 교차검증 이력

| 버전 | 감리 | 반영 사항 |
|------|------|----------|
| v2 | 5인 (DeepSeek·Perplexity·Manus·Gemini·Qwen) | storage.py 동적 기록, Fallbacks, Thinking 모드, 비용 로깅, `<think>` 전처리 |
| v2.1 | 재감리 3인 (Perplexity·Gemini·Manus) | 동기/비동기 정정, 함수형 구조 확인, extra_body 병합 안전화, 벤치마크 방향 조정, main.py 누락 보완 |
| v2.2 | 실제 코드 확인 (2026-04-10) | 줄 번호 확정, 함수명 확정, 시스템 프롬프트 변수명 확정, requirements.txt 확인 |

---

*이 문서는 Phase F 완료 후 실행한다.*
*STEP 단위 감리 원칙을 적용한다.*
*각 STEP 완료 후 반드시 Gamnamu 승인을 받고 다음으로 넘어간다.*
