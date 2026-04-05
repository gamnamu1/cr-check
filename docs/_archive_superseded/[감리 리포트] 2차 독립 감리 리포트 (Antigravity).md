# [감리 리포트] 2차 독립 감리 리포트 (Antigravity)

### 📋 [M5 Phase D] 2차 독립 감리 리포트 (Antigravity)

[Claude.ai](http://claude.ai/) 파트너의 1차 감리에서 눈치채지 못한 **3가지 중요한 맹점(치명적 논리 오류 1건, 한국어 텍스트 특성 2건)**을 발견했습니다. 이를 수정하기 전까지는 최종 PASS를 줄 수 없습니다.

---

### 🚨 [CRITICAL] pipeline.py의 통합 로직 에러 (환각 태그 노출 위험)

`pipeline.py` 98번 라인 부근의 조건문이 치명적인 버그를 내포하고 있습니다.

- **발견된 문제:**
이 조건문은 `ethics_refs`가 비어있을 경우 `resolve_citations()` 호출 자체를 **스킵(Skip)**합니다.
만약 Sonnet이 환각을 일으켜 제공되지도 않은 윤리 규범(예: `<cite ref="JCE-99"/>`)을 독단적으로 리포트에 적어냈고, 우연히 `ethics_refs` 빈 리스트가 전달되었다면 어떻게 될까요?
`citation_resolver`가 스킵되므로 환각 태그 `<cite ref="JCE-99"/>`가 **사용자 화면(최종 리포트)에 그대로 노출되는 끔찍한 결과**를 초래합니다.
    
    ```python
    if rr.report_text and rr.ethics_refs:
        resolved_text, hallucinated = resolve_citations(...)
    ```
    
- **해결 방안:**
CitationResolver는 환각 태그를 청소(Clean-up)하는 기능도 하므로, `ethics_refs`가 비어 있더라도 반드시 실행되어야 합니다.
*수정 전:* `if rr.report_text and rr.ethics_refs:`*수정 후:* `if rr.report_text:` (단일 조건으로 변경. `rr.ethics_refs`가 `None`일 경우를 대비해 함수 호출 시 `rr.ethics_refs or []` 기법 권장)

### ⚠️ [MINOR] 환각 태그 제거 시 발생하는 이중 공백 (UX 결함)

`citation_resolver.py`의 `_replace_cite` 함수.

- **발견된 문제:**
환각 ref 일 경우 `return ""`을 통해 빈 문자열로 치환합니다.
이 경우 `위반입니다. <cite ref="JCE-99"/> 따라서` 라는 텍스트가 `위반입니다. 따라서` 로 **이중 공백**을 유발하거나, 띄어쓰기가 어색해집니다.
- **해결 방안:**`_CITE_PATTERN` 정규식 앞뒤로 선택적 공백(Whitespace) 매칭을 추가하거나, 치환이 끝난 후 정규식을 통해 이중 공백(`" "`)을 단일 공백(`" "`)으로 치환하는 클리닝 로직을 한 번 더 수행하는 것이 좋습니다.

### ⚠️ [MINOR] 한국어 200자 텍스트 절단 로직의 경계 조건

`citation_resolver.py`의 `_truncate_text()` 함수.

- **발견된 문제:**
현재 공백과 마침표 단위로만 어절을 끊고 있습니다. 한국어 및 실제 DB 규범 텍스트 특성상, 쉼표(`,`)나 줄바꿈 문자(`\\n`)에서 끊는 것이 자연스러울 때가 많습니다. 200자의 마지막이 긴 숫자의 쉼표나 개행문자로 끝날 경우 글자가 단어 중간에서 잘릴 수 있습니다.
    
    ```python
    if truncated[i] in (' ', '.', '。'):
    ```
    
- **해결 방안:**`(' ', '.', '。', ',', '\\n')` 로 튜플을 확장하여 안전을 기하십시오.

### ✅ [PASS] 성능 및 보안 (ReDoS 등)

- `_CITE_PATTERN` 정규식에 사용된 `([^"]+)` 패턴은 백트래킹 지옥(Catastrophic Backtracking)을 유발하지 않는 매우 안전하고 효율적인 정규식입니다.
- 데이터베이스 조회를 일절 막고 In-memory 방식으로 격리(옵션 B)한 부분 또한 파이프라인의 견고성을 높이는 강력한 설계입니다.

---

### ■ 최종 판정

**❌ FAIL (수정 승인부 조건부 PASS)**

**[Claude Code CLI를 위한 조치 사항]**
Gamnamu님, 클로드 코드 CLI에게 다음 **3가지 수정 사항**을 지시하여 주시기 바랍니다.

1. `pipeline.py`에서 `if rr.report_text and rr.ethics_refs:`를 `if rr.report_text:`로 수정하고 파라미터 방어(`rr.ethics_refs or []`) 처리할 것.
2. `citation_resolver.py`의 `_truncate_text` 경계 문자에 `,` 단어와 `\\n` 추가.
3. `citation_resolver.py`의 `resolve_citations` 맨 마지막 반환 직전에 `resolved = resolved.replace(" ", " ")` 를 추가하여 중복 공백 현상 예방 (가장 간단한 우회책).