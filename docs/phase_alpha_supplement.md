# 보충 지시: Phase α 추가 수정 2건

이 문서는 `phase_alpha_cli_prompt.md`와 함께 적용한다. 기존 Bug A·B·C 수정에 더해 아래 2건을 추가한다.

---

## 추가 수정 1: Sonnet Solo 프롬프트에 JSON 형식 경고 추가 (Bug B 예방)

### 대상 파일
`backend/core/pattern_matcher.py` — `_SONNET_SOLO_PROMPT` 문자열

### 수정 내용

프롬프트 하단의 `## 출력 형식` 섹션, `"matched_text"` 필드 설명 바로 아래에 다음 경고 문구를 추가한다:

```text
⚠️ JSON 형식 주의:
- "matched_text" 값은 반드시 하나의 문자열이어야 합니다.
- 여러 문구를 포함하려면 하나의 문자열 안에서 ' / '로 구분하세요.
- ❌ 틀린 예: "matched_text": "첫번째 문장", "두번째 문장"
- ✅ 올바른 예: "matched_text": "첫번째 문장 / 두번째 문장"
- JSON 문법 오류가 발생하면 분석 결과 전체가 유실됩니다.
```

### 삽입 위치
프롬프트 끝부분의 출력 형식 JSON 예시 직전에 삽입한다. 기존 프롬프트의 다른 부분은 수정하지 않는다.

---

## 추가 수정 2: 리포트 생성 재시도 루프에 API 에러 상세 로깅 추가

### 대상 파일
`backend/core/report_generator.py` — `generate_report()` 함수의 재시도 루프

### 증상
테스트 2에서 리포트 생성이 258초 만에 실패했으나(`sonnet_raw_response: ""`), 실패 원인이 로그에 남지 않아 API 에러인지, 타임아웃인지, JSON 파싱 실패인지 구분할 수 없다.

### 수정 내용

`generate_report()` 함수의 `for attempt in range(max_retries):` 루프 안에 있는 except 블록에서, 예외의 타입과 메시지를 상세히 로깅한다:

```python
except Exception as e:
    logger.error(
        f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
        f"[{type(e).__name__}] {e}"
    )
    if attempt < max_retries - 1:
        import time
        time.sleep(2 ** attempt)
    else:
        raise
```

기존 except 블록이 위와 다른 형태라면, 최소한 `type(e).__name__`과 `str(e)`가 로그에 포함되도록 수정한다. 기존의 재시도 간격(`time.sleep`)이 이미 있다면 그대로 유지한다.

### 목적
이 로깅을 통해, 다음 테스트에서 리포트 생성 실패가 발생할 경우 터미널 로그에서 즉시 원인을 파악할 수 있다.

---

## 금지 사항
- `_SONNET_SOLO_PROMPT`의 기존 내용을 삭제하거나 재배치하지 않는다. 경고 문구만 추가한다.
- `generate_report()`의 기존 재시도 횟수와 간격을 변경하지 않는다. 로깅만 강화한다.
