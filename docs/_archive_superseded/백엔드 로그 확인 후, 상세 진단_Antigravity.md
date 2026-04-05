# CR-Check M6 Phase C 심층 감리 진단서 (Test 1~3 분석)

> [!IMPORTANT]
> **작성자**: 독립 감리자 (Antigravity)
> **대상**: 제공해주신 3분류 테스트 로그(`diagnostic_....json` 3건) 및 생성 리포트 샘플
> **목적**: 오작동 원인의 기술적 근본 원인을 파악하고, 명확한 코드 단위의 수정 지침을 제공합니다.

---

## 1. Test 1: (TN 판정 오류) '문제적 보도 관행이 발견되지 않음' 
### 📌 현상 및 로그 요약
- **발생한 문제**: 기사 내 분명히 문제 패턴(1-1-4, 1-3-1, 1-7-5)이 내포되어 있었음에도 파이프라인이 이를 무시하고 "문제 없음"으로 통과처리함.
- **진단 로그 확인**: `diagnostic_20260404_223514.json`
  - `haiku_raw_response`에는 분명히 `detections` 배열이 생성되어 있음.
  - 그러나 `haiku_detections: []`, `validated_pattern_codes: []` 등 사후 파싱된 객체 배열이 모두 비어 있음.
- **근본 원인**: **Sonnet의 JSON 문법 오류 (Syntax Error)**
  - Sonnet이 생성한 JSON 내부 문자열: `"matched_text": "수백만 서울시민의 아침을 볼모로 잡는 부조리", "승객이 특정단체의 인질이 되지 않도록",`
  - 위와 같이 하나의 필드(`matched_text`)에 따옴표 문자열 두 개를 쉼표만으로 나열했습니다. 이는 JSON 표준 위반입니다.
  - `pattern_matcher.py`의 `_parse_solo_response`가 `json.loads` 과정에서 의도치 않게 에러 처리를 하며 빈 배열 `[]`을 반환, 이로 인해 전체 결과가 "탐지 없음"으로 폴백되었습니다.

### 🛠 수정 지침
1. **`pattern_matcher.py` 프롬프트 수정**:
   `_SONNET_SOLO_PROMPT` 하단의 출력 형식 및 규칙에 다음 문구를 강조형으로 추가하십시오.
   ```text
   - ❌ 주의: "matched_text"에 여러 문구를 넣을 때 쉼표(,)로 독립적인 문자열을 나열하지 마세요. 
     (틀린 예: "matched_text": "첫번째 문장", "두번째 문장")
   - 반드시 하나의 문자열 안에서 합쳐서 서술하세요. JSON 문법 에러가 발생하면 리포트가 중단됩니다.
   ```
2. **(선택적) `_parse_solo_response` 안정성 보강**: 
   `try...except json.JSONDecodeError:` 로직 내에서 경고만 남기지 않고, 필요시 `pipeline` 쪽에 파싱 에러 상태를 알려서 조기 종료(Fail-fast)시키는 방 방안도 고민해 보세요.

---

## 2. Test 2: (에러루프) '리포트 생성 중 오류 발생'
### 📌 현상 및 로그 요약
- **발생한 문제**: 리포트가 최종적으로 생성되지 못하고 3종 모두 에러 폴백 메시지로 대체됨.
- **진단 로그 확인**: `diagnostic_20260404_224117.json`
  - `total_seconds`: **258.07초 (약 4.3분)**
  - `sonnet_raw_response`: `""` (공백)
- **근본 원인**: **Anthropic API 통신 타임아웃 / `max_tokens` 하드 리밋 제한 위반 누적**
  - 타임아웃 4.3분은 `report_generator.py` 내부에 설정된 재시도 백오프(`time.sleep(2**attempt)`, 3회 재시도)가 전부 만료되었음을 의미합니다.
  - M5 종합 감리에서 지적되었던 `max_tokens=10000` 설정이 Claude 3.5 모델의 한도(8,192 토큰)를 초과하여 Anthropic API로부터 `400 Invalid RequestError` 혹은 응답 지연을 야기했을 소지가 다분합니다.

### 🛠 수정 지침
1. **`report_generator.py` 토큰 제한 하향 조정**:
   ```python
   # 수정 전
   max_tokens=10000,
   
   # 수정 후
   max_tokens=8192,
   ```
2. **에러 로깅 가시성 확보**:
   `generate_report`의 except 블록에서 예외 문자열을 보다 명시적으로 픽업할 수 있도록 로직을 고도화하여, 실제 콘솔 창이나 디버그 로그에 Anthropic API의 원문 에러 내용(`e`)이 직접 노출되도록 보강하세요.

---

## 3. Test 3: (UX 붕괴) '인용 후처리 시 가독성 파괴'
### 📌 현상 및 로그 요약
- **발생한 문제**: 문장 중간에 위치한 `<cite ref="JEC-4"/>` 태그가 무려 200글자에 가까운 규범 원문 덩어리로 치환됨. 
  *(예: 언론윤리헌장은 「공정하게 보도한다: 윤리적 언론은 특정 집단, 세력, 견해에... (중략) ...고려해 보도 내용의 양적·질적 균형을...」고 명시합니다.)*
- **근본 원인**: **CitationResolver의 `_truncate_text` 길이 설정과 인라인 치환의 부적합성**
  - Sonnet은 문맥을 이어가는 구조(`...헌장은 <X>라고 규정합니다.`)로 리포트를 썼지만, `citation_resolver.py`는 `_truncate_text(max_len=200)`을 적용해 통문장을 인라인(inline)으로 밀어넣고 있습니다.

### 🛠 수정 지침
**`citation_resolver.py` 구조 혁신 (인라인 + 풋노트 방식 분리)**
문장 중간에는 규범의 "제목(Title)"만 남기고, 구체적인 원문 내용은 리포트 최하단에 주석 형태로 묶어서 빼내야 합니다.
1. `_format_citation` 함수 수정:
   ```python
   def _format_citation(ref: EthicsReference, is_first: bool) -> str:
       # 원문(full_text)은 본문에 삽입하지 않고 제목과 번호만 삽입
       return f"「{ref.ethics_code} {ref.ethics_title}」"
   ```
2. `resolve_citations` 함수 수정:
   본문 Regex 치환이 끝난 뒤, 사용된 규범(`seen_codes`에 모인 `EthicsReference`)의 원문을 모아 리포트 문자열(`resolved`) 끝단에 부록처럼 덧붙이세요.
   ```python
   # ... (CITE_PATTERN 치환 이후) ...
   if seen_codes:
       appendix = "\n\n---\n**[참고 윤리 규범]**\n"
       for code in seen_codes:
           ref = ref_map[code]
           appendix += f"- **{ref.ethics_code} {ref.ethics_title}**: {ref.ethics_full_text}\n"
       resolved += appendix
   ```

---

## 4. (부가 진단) 이전 감리 피드백: 메타 패턴 논리 구멍 
이슈 3가지를 정리하는 김에 앞서 언급된 마이너 결함 구체화 수정 지침도 드립니다.

### 🛠 메타 패턴 확신도 산식 수정
- **위치**: `meta_pattern_inference.py`의 `_compute_confidence`
- **수정 지침**:
  ```python
  def _compute_confidence(required_count: int, supporting_count: int) -> str:
      if required_count >= 2 and supporting_count >= 2:
          return "high"
      elif (required_count >= 2 and supporting_count >= 1) or (required_count >= 1 and supporting_count >= 2):
          return "medium"
      else:
          return "low"
  ```
  *(R=2, S=1 인 경우 low로 떨어지던 논리 모순을 해결)*

### 🛠 메타 패턴용 윤리 강령 매핑 누락
- **위치**: `pipeline.py` (메타 패턴 추론 직후)
- **수정 지침**: 메타 패턴(`1-4-1`, `1-4-2`)도 Sonnet이 인용(`<cite>`)할 수 있게 하려면, DB에서 해당 패턴의 정수 ID를 같이 가져와 `generate_report()`의 `pattern_ids` 인자에 병합(`extend`) 해주어야 합니다. 현재는 1차 식별된 패턴의 ID 위주로만 넘기고 있습니다.
