# [M6 Phase A] 2차 독립 감리 리포트 (Antigravity)

### 📋 [M6 Phase A] 2차 독립 감리 리포트 (Antigravity)

지시하신 M6 Phase A (3종 리포트 통합 및 로컬 E2E 교체)에 대한 독립 감리 결과를 보고합니다.
Gamnamu님께서 과거 플레이북 초안에서 발생했던 **"리포트 구조 통합/누락 버그"**를 완벽하게 방어하기 위해 내리신 "설계 원칙 유지" 지시가 코드에 훌륭하게 반영되었습니다.
**전반적인 비즈니스 로직(축 1, 2, 3)은 완벽합니다.** 그러나, **서버 코드로 전환되면서 발생한 심각한 아키텍처 레벨의 함정(CRITICAL)** 하나를 백엔드 전문가 관점에서 발견했습니다.

---

### [축 1] 3종 리포트 구조 보존

**판정: ✅ PASS**

1. `report_generator.py`: Sonnet 프롬프트에서 `{ "reports": { "comprehensive": "...", "journalist": "...", "student": "..." } }` JSON 스키마를 명시적으로 요구하고 유효성 검사를 수행하여 안정적으로 추출.
2. `pipeline.py`: 3종의 리포트에 대해 `CitationResolver`를 반복문으로 각각 개별 독립 적용 (`seen_codes`가 각 함수 호출 시마다 초기화되므로 학생용 리포트 첫 인용에서도 축약되지 않고 정상 확장됨). 완벽한 격리.
3. `main.py` & `types/index.ts`: 응답 스키마와 프론트엔드 인터페이스가 완전히 일치하여 단 1줄의 프론트엔드 코드 수정 없이도 기존 탭 UI가 호환 가능.

### [축 2] 규범 인용 원칙

**판정: ✅ PASS**

1. 프롬프트에 **롤업 선택적 적용 원칙**이 명확히 명시되었습니다 ("가장 직접적으로 관련된 구체적 조항 하나만 인용", "서로 다른 문제가 상위 원칙으로 수렴할 때만 롤업 인용").
2. "원문을 직접 타이핑하지 마세요. 대신 `<cite ref="..."/>` 태그만 삽입하세요"라는 금지/허용 예시가 견고합니다.
3. `citation_resolver.py`는 오직 DB 조회를 거친 `ethics_refs`를 참조(`ref_map`)하며, 여기에 없는 코드(환각)는 regex를 통해 빈 텍스트로 치환하고 경고 로그를 남깁니다 (DB fallback 완벽 차단).

### [축 3] 데이터 흐름 무결성

**판정: ✅ PASS**

1. `match_patterns_solo`에서 산출된 `overall_assessment` (Devil's Advocate 평가)가 버려지지 않고 `pipeline.py`를 거쳐 `generate_report`의 프롬프트로 자연스럽게 전달되는 흐름을 확인했습니다.
2. `scraper.py`는 교체되거나 수정되지 않고 URL을 통한 기사 메타데이터(퍼블리셔, 바이라인 등)를 온전히 보존하여 `main.py`에서 응답의 `article_info`로 덮어쓰기(병합) 처리되어 프론트엔드로 넘어갑니다.

---

### 🚨 [숨은 버그 - 아키텍처 관점]

비즈니스 로직은 합격점이지만, 이를 지탱하는 **웹 서버 로직** 영역에서 M6 클라우드 배포 시 **"병목으로 인한 서버 다운"**을 유발할 핵심 버그가 남겨져 있습니다.

### 1. [CRITICAL] FastAPI Event Loop 블로킹 (동기/비동기 오용)

- **위치**: `main.py` 라인 107
`async def analyze_article(request: AnalyzeRequest):`
- **원인**: Python 파이프라인 모듈(`chunker`, `httpx`, `Anthropic` 객체)은 블로킹 형태의 **동기식(Sync)** I/O로 구현되어 있습니다. 이를 `async def`로 선언된 라우터 핸들러에서 실행하면 FastAPI의 메인 이벤트 루프 자체가 차단(Blocking)됩니다.
- **리스크**: 배포 환경에서 한 명의 일반 사용자가 분석을 요청하여 20초간 Sonnet을 대기하는 동안, **서버가 프리징(Freeze)되어 다른 모든 사용자의 요청이나 헬스체크를 완전히 무시**해 버립니다.
- **조치 권고**: `main.py`의 라우터 선언부에서 `async` 키워드를 제거하십시오.
*수정 전:* `async def analyze_article(request: AnalyzeRequest):`*수정 후:* `def analyze_article(request: AnalyzeRequest):`
(이 간단한 수정만으로 FastAPI 내부 스레드 풀로 파이프라인이 자동 할당되어 비동기 논블로킹 처리가 안전하게 이뤄집니다.)

### 2. [MAJOR] LLM 재시도 로직의 블라인드 스팟 (Blind Spot)

- **위치**: `report_generator.py` 라인 331
`except (ValueError, json.JSONDecodeError) as e:`
- **원인**: 이 시도(retry) 블록은 모델의 JSON 포맷 오류만을 잡아내어 재시도합니다. 만약Anthropic API 일시 과부하(529 Overload), 타임아웃, 커넥션 에러 등 **LLM API 자체 통신 오류(`anthropic.APIError`)**가 발생하면 이 except 블록은 무시되고 즉각 500 에러를 뿜으며 파이프라인이 종료됩니다.
- **조치 권고**: 예외 처리를 광범위하게 수정하여 재시도 견고성을 높이십시오.
`except Exception as e:` 로 변경하거나 `anthropic.APIError`를 예외 튜플에 추가해야 합니다.

### 3. [MAJOR] max_tokens 10,000 초과 위험

- **위치**: `report_generator.py` 라인 263
`max_tokens=10000`
- **원인**: 현재 Anthropic의 Claude 3.5 Sonnet 계열은 하드 최대 출력 제한이 **8192 토큰**입니다.
- **리스크**: 모델이 "10000"이란 값을 받으면 즉각 `400 BadRequest`를 날리며 위 2번 문제와 겹쳐 1차 시도에서 영구 실패해버릴 위험이 높습니다 (설령 가상의 2025 모델이라 하더라도 안전을 기하는 것이 좋습니다).
- **조치 권고**: `max_tokens=8192`로 하향 조정하십시오.

---

### ■ 최종 판정

의도한 비즈니스 규칙과 3종 리포트 매커니즘은 매우 견고하여 **✅ 합격점 (PASS)**입니다.
단, 백엔드 안정성 이슈 3건(CRITICAL 1건, MAJOR 2건)은 M6 Phase B 이후에 클라우드로 올리기 전 반드시 수정해야 서버가 마비되지 않습니다. Gamnamu님께서 코더에게 해당 사항 반영을 지시해 주시면 완벽하겠습니다.