# 작업 지시: Phase α — 3건의 버그 동시 수정

## 배경

E2E 테스트 3건의 진단 결과, 파이프라인에서 3건의 독립적인 버그가 확인되었다. 기존 로직의 의도를 유지하면서 각 버그를 수정한다.

진단 데이터: `backend/diagnostics/` 디렉토리의 JSON 파일 3건 참조.

---

## Bug A: 벡터 검색이 항상 0건을 반환한다

### 증상
- 3건의 테스트 전부 `checkpoint_2_vector.candidate_count: 0`
- `search_vectors()` 함수가 빈 리스트를 반환한다.
- Sonnet Solo가 ★ 힌트 없이 전체 102개 패턴 목록만으로 판단하고 있다.

### 대상 파일
`backend/core/pattern_matcher.py` — `search_vectors()` 함수 (약 130행 부근)

### 수정 방향

1. `search_vectors()` 함수에 진단 로깅을 추가한다:
   - 임베딩 입력 개수와 각 임베딩의 차원(길이)
   - 각 청크별 Supabase RPC 호출의 HTTP 응답 상태 코드
   - 각 청크별 RPC 응답의 row 수 (0건이면 WARNING 레벨)
   - RPC 요청 JSON의 `match_threshold`와 `match_count` 값

2. RPC 호출이 200이지만 결과가 0건인 경우를 구분하여 로깅한다:
   - "RPC 성공, 결과 0건 — threshold={t}, match_count={mc}" 형태

3. RPC 호출에서 예외가 발생할 경우 현재는 `r.raise_for_status()`로 즉시 실패하는데, 여기에 상세한 에러 메시지를 로깅한 후 raise하도록 한다.

4. 임베딩 생성(`generate_embeddings`) 함수에서도 반환된 임베딩의 차원 수를 로깅한다. Supabase의 벡터 컬럼과 차원이 불일치하면 검색 결과가 0건이 될 수 있다.

### 검증
수정 후 테스트를 실행하고, 터미널 로그에서 어느 단계에서 0건이 발생하는지 확인한다. 로그를 통해 원인이 파악되면 추가 수정이 필요할 수 있다.

---

## Bug B: Sonnet Solo의 비정형 JSON 응답이 전체 파싱 실패를 유발한다

### 증상
- 테스트 1에서 Sonnet Solo가 패턴 3개를 올바르게 식별했으나(`haiku_raw_response`에 정상적인 분석이 있음), `haiku_detections`와 `validated_pattern_codes`가 모두 빈 배열이 되어 "문제적 보도관행이 발견되지 않았습니다"로 최종 판정됨.
- 원인: 세 번째 detection의 `matched_text` 필드가 이렇게 생성됨:
  ```
  "matched_text": "수백만 서울시민의 아침을 볼모로 잡는 부조리", "승객이 특정단체의 인질이 되지 않도록",
  ```
  JSON 값 위치에 문자열 두 개가 쉼표로 나열되어 유효하지 않은 JSON이 됨.
- `_parse_solo_response()`의 `json.loads()`가 이 에러로 전체 파싱을 실패하고 빈 결과를 반환함.

### 대상 파일
`backend/core/pattern_matcher.py` — `_parse_solo_response()` 함수 (약 395행 부근)

### 수정 방향

`json.loads()` 실패 시, JSON 복구를 시도하는 fallback 로직을 추가한다.

1. **1차 시도**: 기존대로 `json.loads()` 실행.

2. **2차 시도 (1차 실패 시)**: 일반적인 LLM JSON 오류를 정규식으로 수정한 후 재시도:
   - 값 위치에서 `", "` 패턴으로 분리된 복수 문자열을 하나로 합친다. 예: `"text1", "text2"` → `"text1 / text2"` (단, 이 패턴이 JSON 객체의 키-값 구분자 `,`와 구별되어야 하므로, `": "` 뒤에 오는 `"...", "..."` 패턴에만 적용)
   - trailing comma 제거 (배열/객체 마지막 요소 뒤의 쉼표)

3. **3차 시도 (2차도 실패 시)**: `haiku_raw_response`에서 `"pattern_code": "..."` 패턴만 정규식으로 추출하여 최소한의 HaikuDetection 리스트를 구성한다. 이 경우 `matched_text`와 `reasoning`은 빈 문자열, `severity`는 "medium"으로 설정한다.

4. 모든 시도가 실패한 경우에만 현재처럼 빈 리스트를 반환한다.

5. 어떤 단계에서 성공/실패했는지를 반드시 로깅한다:
   - "Solo JSON 1차 파싱 성공" / "Solo JSON 1차 실패, 2차 복구 시도" / "Solo JSON 2차 복구 성공" / "Solo JSON 3차 정규식 추출 사용"

### 주의사항
- `_parse_solo_response()`의 반환 타입 `tuple[str, list[HaikuDetection]]`은 변경하지 않는다.
- 기존에 정상 파싱되는 JSON에 대해서는 동작이 달라지지 않아야 한다.

---

## Bug C: 규범 조회(get_ethics_for_patterns RPC)가 간헐적으로 0건을 반환한다

### 증상
- 테스트 2: 패턴 `1-3-1`, `1-1-1`이 정상 식별·검증되었으나 `ethics_ref_count: 0`, `patterns_without_ethics: ["1-3-1", "1-1-1"]`.
- 테스트 3: 같은 패턴 `1-3-1`에 대해 규범 10건 이상 정상 반환.
- 같은 패턴인데 결과가 다른 것은 RPC 호출 자체가 간헐적으로 실패하고 있음을 시사한다.
- 규범이 0건이면 리포트 생성 Sonnet에게 빈 컨텍스트가 전달되어 "리포트 생성 중 오류"가 발생한다.

### 대상 파일
`backend/core/report_generator.py` — `fetch_ethics_for_patterns()` 함수 (약 63행 부근)

### 수정 방향

1. **RPC 호출에 상세 로깅 추가**:
   - 요청 전: `logger.info(f"규범 조회 요청: pattern_ids={pattern_ids}")`
   - 응답 후: HTTP 상태 코드, 응답 body 길이, 반환된 row 수
   - 0건인 경우: 현재 WARNING 메시지에 추가로 요청한 `pattern_ids` 값과 HTTP 응답 전문(body[:500])을 포함

2. **재시도(retry) 로직 추가**:
   - RPC가 200이지만 결과가 0건이고, `pattern_ids`가 비어있지 않은 경우: 2초 대기 후 1회 재시도
   - 재시도에서도 0건이면 WARNING 로깅 후 빈 리스트 반환 (현재 동작 유지)
   - 네트워크 에러(httpx 예외) 시에도 2초 대기 후 1회 재시도

3. **0건 결과의 원인을 구분하기 위한 fallback 진단 쿼리 추가**:
   - 재시도까지 0건인 경우, `pattern_ethics_relations` 테이블을 직접 조회하여 해당 pattern_ids에 연결된 relation 수를 확인한다:
     ```
     GET {sb_url}/rest/v1/pattern_ethics_relations?select=id&pattern_id=in.({ids_csv})
     ```
   - 이 쿼리 결과도 0건이면 → "DB 매핑 자체가 없음" (데이터 문제)
   - 이 쿼리에는 결과가 있는데 RPC가 0건이면 → "RPC 함수 로직에 필터 조건 문제" (함수 문제)
   - 이 구분을 로그에 명확히 남긴다.

### 주의사항
- `fetch_ethics_for_patterns()`의 반환 타입 `list[EthicsReference]`는 변경하지 않는다.
- 재시도는 최대 1회만. 무한 재시도는 금지.
- 재시도 로직이 전체 파이프라인 실행 시간에 최대 2초만 추가하도록 한다.

---

## 수정 후 테스트

3건의 수정을 모두 적용한 후, 다음 명령으로 로컬 서버를 실행하고 기사 1건을 분석한다:

```bash
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

터미널 로그에서 다음을 확인한다:
- Bug A: 벡터 검색 관련 로그가 출력되는지, 0건의 원인이 무엇인지
- Bug B: "Solo JSON 1차 파싱 성공" 또는 복구 관련 로그가 정상 출력되는지
- Bug C: 규범 조회 관련 로그가 출력되는지, 재시도 발생 여부

## 금지 사항
- 위 3개 함수 외의 코드를 수정하지 않는다.
- 기존 함수의 시그니처(매개변수, 반환 타입)를 변경하지 않는다.
- import 문은 필요한 경우 파일 상단에 추가해도 된다 (예: `time`).
- 프롬프트(`_SONNET_SOLO_PROMPT`, `_SONNET_SYSTEM_PROMPT` 등)는 수정하지 않는다.
