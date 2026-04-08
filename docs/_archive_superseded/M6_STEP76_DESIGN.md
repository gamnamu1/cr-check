# M6 STEP 76 — 벤치마크 Solo 리팩토링 + 전역 에러 핸들링 + 감리 이관 사항

> 작성: Claude.ai (STEP 76 설계)
> 작성일: 2026-04-01
> 대상: Claude Code CLI (STEP 76 실행용)

---

## 0. 사전 숙지 파일

```
1. 이 파일 (M6_STEP76_DESIGN.md)
2. scripts/benchmark_pipeline_v3.py          ← 리팩토링 대상
3. backend/core/pipeline.py                  ← 에러 핸들링 강화
4. backend/core/report_generator.py          ← 재시도 예외 범위 확대
5. backend/main.py                           ← article_info 방어 로직
6. backend/core/citation_resolver.py         ← 정규식 개선 (MINOR)
7. CLAUDE.md
```

---

## 1. 작업 개요

Phase B는 **품질에 영향을 주지 않는 구조 정비**. 3가지 작업으로 구성:

| # | 작업 | 규모 |
|---|------|------|
| A | 벤치마크 Solo 리팩토링 | 중 |
| B | pipeline.py 전역 에러 핸들링 강화 | 중 |
| C | Phase A 독립 감리 이관 사항 3건 반영 | 소 |

---

## 2. 작업 A: 벤치마크 Solo 리팩토링

### 현재 문제

`benchmark_pipeline_v3.py`는 M4(2-Call) 시절에 작성되었고, M5에서 `match_patterns_solo()`가
추가되면서 실제로는 Solo 경로를 타지만, 코드의 언어(독스트링, 변수명, 출력, 리포트 제목)가
여전히 "2-Call", "Haiku" 기반이다.

### 변경 원칙

- **deprecated 2-Call / 1-Call 코드를 삭제하지 말 것**. 비교 실험용 보존.
- 기본 실행 경로를 Solo로 명확히 고정.
- `--legacy` 플래그로 구 경로 실행 가능하게 유지.

### 구체적 변경

1. **독스트링 갱신**:
   - "M5 벤치마크 — 2-Call 파이프라인" → "M6 벤치마크 — Sonnet Solo 파이프라인"
   - 지표 설명에서 Haiku 관련 지표를 "legacy" 표시

2. **`--legacy` 플래그 추가**:
   ```python
   parser.add_argument("--legacy", action="store_true", help="Legacy 2-Call 모드로 실행")
   ```

3. **main() 분기**:
   ```python
   if args.legacy:
       print("Legacy 2-Call 모드")
       # 기존 로직 그대로 (현재 코드가 이미 Solo를 타지만, 명시적 분기)
   else:
       print("Sonnet Solo 모드")
   ```
   실질적으로 analyze_article()은 이미 match_patterns_solo()를 호출하므로,
   분기의 핵심은 **리포트 출력 형식**이다:
   - Solo 모드: "Haiku Suspect Accuracy", "Haiku TN Pass Rate" 제거, 리포트 제목 갱신
   - Legacy 모드: 기존 출력 유지

4. **generate_report() 갱신** (Solo 모드):
   - 리포트 제목: "M6 벤치마크 결과 — Sonnet Solo"
   - 파이프라인 설명: "청킹→벡터검색→Sonnet Solo(Devil's Advocate CoT)"
   - 모델: "Sonnet 4.6 (Solo 1-Call)"
   - Haiku 관련 열(Suspect Acc, TN Pass Rate) 제거
   - 비용 추정: Sonnet 1회 기준으로 변경
   - 건별 상세에서 "Haiku 의심", "Haiku 총평" → "overall_assessment" (Solo는 suspect_categories가 항상 [])

5. **콘솔 출력 갱신**:
   - 배너: "M6 벤치마크 — Sonnet Solo"
   - 요약: Haiku Suspect Acc 줄 제거

6. **결과 파일명 분리** (선택):
   - Solo: `docs/M6_BENCHMARK_RESULTS.md` (M5 결과 파일 덮어쓰지 않음)
   - Legacy: `docs/M5_BENCHMARK_RESULTS.md` (기존)
   - 주의: 기존 결과 파일 삭제 금지

7. **overall_assessment 결과 파일 기록**:
   - 건별 상세에 Sonnet Solo의 overall_assessment 전체 기록 (현재 80자 잘림)

### 검증: 리팩토링 전후 결과 일치 확인

`--ids A-01 C-02` 등 2~3건으로 Solo 모드 실행하여,
기존 결과와 동일한 패턴 탐지 결과가 나오는지 확인.
(리포트 형식만 바뀌고, 분석 결과 자체는 동일해야 함)

---

## 3. 작업 B: pipeline.py 전역 에러 핸들링 강화

### 변경 대상

`pipeline.py`의 `analyze_article()` 함수 내부.

### 현재 상태

각 단계(청킹, 벡터검색, 패턴매칭, 리포트, 인용해석)에 개별 에러 핸들링이 없다.
한 단계에서 에러가 발생하면 전체 파이프라인이 즉시 중단된다.

### 변경 사항

각 단계에 개별 try/except를 추가하되, **과도하지 않게**:

```python
# 1. 청킹 — 실패 시 전체 텍스트를 단일 청크로 취급
try:
    chunks = chunk_article(article_text)
except Exception as e:
    logger.error(f"청킹 실패, 전체 텍스트를 단일 청크로 사용: {e}")
    chunks = [Chunk(text=article_text, start=0, end=len(article_text), length=len(article_text))]

# 2. 패턴 매칭 — 실패 시 빈 결과 반환 (치명적이므로 에러 메시지 상세히)
try:
    pm = match_patterns_solo(chunk_texts, article_text, threshold=vector_threshold)
except Exception as e:
    logger.error(f"패턴 매칭 실패: {e}", exc_info=True)
    raise  # 패턴 매칭 실패는 복구 불가, main.py에서 500으로 처리

# 3. 리포트 생성 — 실패 시 패턴 목록만 반환
# (이미 generate_report 내부에 재시도 로직이 있으므로, 여기서는 최종 실패만 잡음)
try:
    rr = generate_report(...)
except Exception as e:
    logger.error(f"리포트 생성 최종 실패, 패턴 목록만 반환: {e}")
    rr = ReportResult(
        reports={
            "comprehensive": "리포트 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "journalist": "리포트 생성 중 오류가 발생했습니다.",
            "student": "리포트 생성 중 오류가 발생했습니다.",
        }
    )

# 4. CitationResolver — 이미 개별 에러 핸들링 완료 (Phase A 독립 감리 수정)
```

### 로깅 레벨 가이드

- `logger.error()`: 복구 불가 또는 사용자에게 영향이 있는 에러
- `logger.warning()`: 복구 가능한 에러 (graceful degradation 발동)
- `logger.info()`: 정상 흐름 정보 (단계 시작/완료)

### 주의

- 패턴 매칭 실패는 raise (복구 불가). 기사 분석의 핵심이므로.
- 청킹 실패는 graceful (단일 청크로 fallback)
- 리포트 실패는 에러 메시지 리포트로 대체 (프론트엔드가 빈 화면 안 보이게)


---

## 4. 작업 C: Phase A 독립 감리 이관 사항 3건

### C-1. report_generator.py — 재시도 예외 범위 확대 [MAJOR → Phase B]

**출처**: Antigravity 독립 감리 #2

**현재**:
```python
except (ValueError, json.JSONDecodeError) as e:
```

**변경**:
```python
except Exception as e:
```

Anthropic API 통신 오류(529 Overload, 타임아웃, 커넥션 에러)도 재시도 대상에 포함.
모든 예외를 잡되, 로그에서 예외 타입을 명시하여 디버깅 가능하게:
```python
logger.warning(f"리포트 생성 시도 {attempt+1}/{max_retries} 실패 ({type(e).__name__}): {e}")
```

### C-2. main.py — article_info 방어 로직 강화 [MINOR → Phase B]

**출처**: Manus 독립 감리 #3

**현재**: `article_data.get("publisher")` — None이면 조건 통과 안 하지만, 빈 문자열("")이면 통과.

**변경**: 각 필드에 truthiness 검증 추가.
```python
# 현재 (이미 충분히 방어적이나, 빈 문자열 방어 추가)
if article_data.get("publisher") and article_data["publisher"] not in ("미확인", ""):
    article_info["publisher"] = article_data["publisher"]
```

실제로 현재 코드의 `article_data.get("publisher") and article_data["publisher"] != "미확인"`은
빈 문자열일 때 `""` → falsy → 조건 통과 안 하므로 이미 안전하다.
하지만 `"미확인"` 외에 스크래퍼가 반환할 수 있는 무의미한 값(`"N/A"`, `"unknown"` 등)을 방어하려면:
```python
_INVALID_META = {"미확인", "", "N/A", "unknown", "Unknown"}

if article_data.get("publisher") and article_data["publisher"] not in _INVALID_META:
    article_info["publisher"] = article_data["publisher"]
```

### C-3. citation_resolver.py — 정규식 개선 [MINOR → Phase B]

**출처**: Manus 독립 감리 #4

**현재**: 두 가지 패턴을 `|`로 결합, `match.group(1) or match.group(2)` 필요.
**변경**: 비캡처 그룹 `(?:...)` 사용으로 통합.

```python
# 현재 (확인 필요 — citation_resolver.py의 실제 정규식 패턴을 읽고 수정)
# 변경: r'<cite\s+ref="([^"]+)"\s*(?:/>|>\s*</cite>)' 형태로 통합
```

⚠️ 이 수정은 citation_resolver.py의 실제 코드를 확인한 후 적용.
정규식 변경이므로 기존 테스트(test_citation_resolver.py)로 검증 필수.

---

## 5. 검증 절차

### 5-1. 벤치마크 리팩토링 검증

```bash
SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids A-01 C-02
```

- Solo 모드 기본 동작 확인
- 리포트 제목이 "Sonnet Solo"인지 확인
- 분석 결과(패턴 탐지)가 기존과 동일한지 확인

```bash
SUPABASE_LOCAL=1 python scripts/benchmark_pipeline_v3.py --ids A-01 C-02 --legacy
```

- Legacy 모드 동작 확인 (기존 출력 형식)

### 5-2. 에러 핸들링 검증

import 검증 + 파이프라인 구조 확인:
```python
from core.pipeline import analyze_article
# 빈 텍스트로 호출 → 에러 메시지 확인 (main.py에서 50자 미만 차단하지만, pipeline 자체 방어도 확인)
```

### 5-3. 이관 사항 검증

- report_generator.py: 재시도 로직에서 `Exception` 캐치 확인
- main.py: `_INVALID_META` 상수 존재 확인
- citation_resolver.py: 정규식 변경 후 test_citation_resolver.py 실행

---

## 6. 주의사항

- [ ] deprecated 코드 삭제 금지
- [ ] 벤치마크 결과 파일(M4, M5) 삭제 금지
- [ ] 기능 변경 없음 — 구조 정비만
- [ ] citation_resolver.py 정규식 변경 시 test_citation_resolver.py 실행 필수
- [ ] git commit/push 실행 금지

---

## 7. 완료 보고 형식

```
## STEP 76 완료 보고

### 작업 A: 벤치마크 리팩토링
- (변경 요약)
- Solo 모드 기본 동작: (결과)
- --legacy 플래그: (결과)

### 작업 B: 전역 에러 핸들링
- (변경 요약)

### 작업 C: 감리 이관 사항
- C-1 재시도 예외 범위: (결과)
- C-2 article_info 방어: (결과)
- C-3 정규식 개선: (결과)

### 미해결 사항
- (있으면 기술)
```

---

*이 설계서는 2026-04-01 Claude.ai가 작성했다.*
