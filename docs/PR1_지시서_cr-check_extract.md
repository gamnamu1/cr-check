# [PR 1 지시서] cr-check — 기사 추출 엔드포인트 `POST /extract`

- 대상 저장소: `gamnamu1/cr-check` · 브랜치: `feat/extract-endpoint` (기획자가 생성)
- 근거 문서: 「기사분석하기 작업설계서 v3.2」. 이 지시서와 설계서가 어긋나면 이 지시서가 우선.
- 지시서 버전: v1.4 (4차 감리 반영: 규칙 4 범위 한정, parse_url 의미 정정, status 판정 규칙, 503 테스트) — v1.3: 인터페이스 문구 통일, scrape() 분기 기준 보존, DNS 판정 논리, 요청·오류 모델 명시) — v1.2: 어댑터 기본값·rate limit 정리 / v1.1: GPT·Kimi K3·Perplexity의 조건부 승인 감리를 반영(어댑터 방식, 전체 시간 상한 구현, 503 계약, CGNAT 대역, 상대경로 리디렉션, meta refresh 불추적)
- 이 문서는 Claude Code CLI에 그대로 전달되는 작업 명령서다.

---

## 0. 절대 규칙 (가장 먼저 읽을 것)

1. **git commit·push·merge·branch 생성을 하지 않는다.** 파일 수정까지만 하고 멈춘다. 깃 조작은 기획자가 직접 한다.
2. **기존 `/analyze` 경로의 동작을 바꾸지 않는다.** `ArticleScraper.scrape(url)`의 외부 동작(입력·출력·네트워크 방식·인코딩 결과)은 리팩터링 전후 동일해야 한다.
3. 새 `/extract` 경로에서 **Anthropic API·RAG·임베딩·Supabase 저장 함수를 호출하지 않는다.** (`run_pipeline`, `get_cached_analysis`, `save_analysis_result` 등 금지)
4. **새 `/extract` 경로에서는 기사 URL·본문을 어떤 저장소·로그에도 남기지 않는다.** 로그는 도메인·오류 코드·소요 시간·status만. (기존 `/analyze`의 로깅·DB 저장은 규칙 2에 따라 그대로 둔다 — 이 규칙을 근거로 기존 경로를 손대지 말 것.)
5. 새 pip 의존성을 추가하지 않는다(표준 라이브러리 + 기존 requirements 범위 내).
6. 이 지시서의 파일 경로·행 번호는 참고치다. **작업 전 실제 파일을 읽고 현재 구조를 확인한 뒤 진행한다.**

---

## 1. 만드는 것 (한 문단 요약)

cr-check 백엔드(FastAPI, Railway)에 창구 하나를 새로 낸다. `POST /extract`는 기사 URL을 받아 **기사 6요소(제목·본문·URL·매체·게재일·기자)를 JSON으로 돌려준다.** 분석은 하지 않는다. 기존 `backend/scraper.py`의 매체별 파싱 규칙을 재사용하되, 네트워크 요청만은 SSRF 방어가 적용된 새 안전 계층(safe fetch)이 수행한다. 이 창구는 cr-report 서버(프록시)만 호출하며, 헤더 비밀키로 보호된다.

---

## 2. API 계약 (동결 — 필드명·구조를 임의로 바꾸지 말 것)

요청:
```http
POST /extract
Content-Type: application/json
X-CR-Extract-Key: <환경변수 EXTRACT_API_KEY 값>

{ "url": "https://n.news.naver.com/article/001/0011122334" }
```

### 계약 JSON ① — 성공 (HTTP 200)
```json
{
  "ok": true,
  "status": "success",
  "article": {
    "title": "검찰 보완수사권 축소 1년…\"수사 공백\" 현실화되나",
    "content": "기사 본문 전문…",
    "url": "https://n.news.naver.com/article/001/0011122334",
    "publisher": "한국시사신문",
    "journalist": "김민준 기자",
    "publish_date": "2026-08-28",
    "source_kind": "portal"
  },
  "warnings": [],
  "content_chars": 2340,
  "extractor_version": "2026.09.1"
}
```

### 계약 JSON ② — 부분 성공 (HTTP 200)
제목과 본문이 있으면 나머지 메타데이터가 없어도 200으로 응답한다.
```json
{
  "ok": true,
  "status": "partial",
  "article": {
    "title": "검찰 보완수사권 축소 1년…\"수사 공백\" 현실화되나",
    "content": "기사 본문 전문…",
    "url": "https://example-news.co.kr/article/1234",
    "publisher": "한국시사신문",
    "journalist": null,
    "publish_date": null,
    "source_kind": "generic"
  },
  "warnings": [
    { "code": "JOURNALIST_NOT_FOUND", "message": "기자명을 확인하지 못했습니다." },
    { "code": "PUBLISH_DATE_NOT_FOUND", "message": "게재일을 확인하지 못했습니다." }
  ],
  "content_chars": 1980,
  "extractor_version": "2026.09.1"
}
```

### 계약 JSON ③ — 오류 (HTTP는 아래 표)
```json
{
  "ok": false,
  "code": "ARTICLE_NOT_FOUND",
  "message": "기사 제목 또는 본문을 추출하지 못했습니다."
}
```

### 오류 코드 표 (전체·확정)

| HTTP | code | 발생 조건 |
|---|---|---|
| 400 | `INVALID_URL` | URL 형식 오류, http/https 외 스킴, userinfo 포함 |
| 400 | `UNSAFE_URL` | 호스트가 금지 대상(내부망·금지 IP 대역), DNS가 금지 대역으로 해석, 비허용 포트 |
| 401 | `UNAUTHORIZED_CALLER` | `X-CR-Extract-Key` 누락·불일치 |
| 413 | `RESPONSE_TOO_LARGE` | 압축 해제 기준 2MB 초과 |
| 415 | `UNSUPPORTED_CONTENT_TYPE` | Content-Type이 text/html 계열이 아님(PDF·이미지 등) |
| 422 | `ARTICLE_NOT_FOUND` | 제목 또는 본문 추출 실패, 본문이 기존 스크레이퍼의 최소 길이 기준 미달(로그인 화면형 200 포함) |
| 429 | `RATE_LIMITED` | IP별 분당 20회 초과 |
| 502 | `SOURCE_FETCH_FAILED` | 원격 4xx/5xx, DNS 해석 실패, 리디렉션 3회 초과·순환 |
| 504 | `SOURCE_TIMEOUT` | 연결·읽기·전체 시간 상한 초과 |
| 500 | `EXTRACTOR_ERROR` | 내부 파서 예외 (예외 문자열·스택·내부 경로를 message에 넣지 말 것) |
| 503 | `EXTRACTOR_DISABLED` | 환경변수 `EXTRACT_API_KEY` 미설정 상태(엔드포인트 잠금) |

### 계약 부속 규칙
- `status`는 `warnings`가 비어 있으면 `"success"`, 하나라도 있으면 `"partial"`로 정한다. (제목·본문이 없거나 최소 길이 미달이면 422이므로 이 판정 자체가 성립하지 않는다.)
- `article.url`은 **앞뒤 공백 제거와 `https://` 보정까지 마친 요청 URL**을 반환한다(리디렉션 최종 URL로 대체하지 않는다). 리디렉션으로 도달한 최종 URL은 응답에 포함하지 않고, **매체별 파서 분기에만 사용**하며 로그에는 도메인만 남긴다.
- `journalist`·`publish_date`·`publisher` 누락은 **null**(빈 문자열 금지) + 해당 `warnings` 항목 추가. warnings 코드: `JOURNALIST_NOT_FOUND` / `PUBLISH_DATE_NOT_FOUND` / `PUBLISHER_NOT_FOUND`.
- `publish_date`는 가능하면 `YYYY-MM-DD`, 정규화 실패 시 원문 표기 그대로, 그것도 없으면 null.
- `content_chars`는 `len(content)` (한글 글자 수 기준, 파이썬 문자열 길이).
- `source_kind`: 포털(네이버·다음·네이트) = `"portal"`, 매체별 전용 파서 = `"outlet"`, 범용 폴백 = `"generic"`.
- `extractor_version`: 상수 `"2026.09.1"` (backend에 상수로 정의).
- `message`는 내부·운영용 한국어 한 문장. **시민에게 보이는 문구는 cr-report 쪽 책임**이므로 여기서 다듬지 않는다.

---

## 3. 구현 명세

### 3-1. `backend/safe_fetch.py` (신규)

SSRF 방어가 적용된 fetch 계층. 공개 함수 하나:

```python
def safe_fetch(url: str) -> SafeFetchResult:
    # SafeFetchResult: response(requests.Response 또는 동등 어댑터), final_url(str)
    # 실패 시 코드가 담긴 전용 예외(SafeFetchError(code, message)) 발생
```

반환하는 `response`는 기존 스크레이퍼의 인코딩 로직이 그대로 동작해야 하므로 `encoding`·`apparent_encoding`·`text`·`content` 속성을 제공해야 한다. 구현은 **(b) 같은 속성(`encoding`·`apparent_encoding`·`text`·`content`)을 구현한 최소 어댑터 객체를 기본값**으로 한다. 실제 코드 확인 후 (a) `_content` 주입 방식이 명백히 더 단순하다고 판단되면 근거와 함께 (a)를 선택해도 되며, 선택과 근거를 완료 보고에 기록한다.

검증 순서(각 단계 실패 시 해당 오류 코드):
1. URL 파싱: 스킴 `http`/`https`만, userinfo(`user:pass@`) 거부, 빈 호스트 거부 → `INVALID_URL`
2. 호스트 문자열 검사: `localhost`, `.local` 등 내부 전용 이름 거부 → `UNSAFE_URL`
3. DNS 해석: **해석 결과 중 하나라도** 다음 대역에 속하면 거부 → `UNSAFE_URL`. IPv4·IPv6·IPv4-mapped IPv6를 동일 기준으로 검사하며, 복수 주소 중 하나라도 허용 불가면 호스트 전체를 거부한다(공개 IP와 사설 IP를 함께 반환하는 우회 차단).
   - IPv4: loopback(127/8), private(10/8, 172.16/12, 192.168/16), link-local(169.254/16), multicast(224/4), reserved(240/4), 0.0.0.0/8, **CGNAT(100.64.0.0/10)**
   - IPv6: loopback(::1), ULA(fc00::/7), link-local(fe80::/10), v4-mapped 중 위 대역
   - 해석 자체 실패 → `SOURCE_FETCH_FAILED`
4. 포트: `None` 또는 `{80, 443}`만 허용 → 그 외 `UNSAFE_URL`
   - **잔여 위험 기록**: DNS 검증 시점과 실제 연결 시점 사이에 주소가 재해석될 가능성(DNS rebinding)은 잔여 위험으로 인지한다. 기존 의존성 범위 안에서 단순·안전하게 방지할 수 있으면 적용하되, **과도한 네트워크 계층 재구현(커스텀 소켓·TLS/SNI 처리 등)은 하지 않는다.** 채택 여부와 근거를 완료 보고에 적는다.
5. 요청: `requests.get(..., allow_redirects=False, stream=True, timeout=(5, 10))`. User-Agent는 기존 스크레이퍼의 것을 재사용. **주의: `timeout=(5,10)`은 연결 5초·청크 간 10초일 뿐 전체 상한이 아니다.** 전체 15초 상한은 8항의 스트리밍 루프에서 요청 시작 시각 기준으로 매 청크마다 수동 검사한다(천천히 흘려보내는 서버 방어).
6. 리디렉션: **HTTP 3xx만 추적한다.** Location이 상대경로면 `urllib.parse.urljoin`으로 절대화한 뒤 **1~4를 전부 다시 검사** 후 재요청. 최대 3회, 초과·순환 → `SOURCE_FETCH_FAILED`. **HTML 내부의 meta refresh·JavaScript 리디렉션은 따라가지 않는다**(검증 우회 경로가 되므로).
7. Content-Type: MIME 파싱(charset 파라미터 허용)해 `text/html` 계열만 → 그 외 `UNSUPPORTED_CONTENT_TYPE`
8. 본문 수신: 스트리밍으로 읽되 누적 2MB 초과 시 중단 → `RESPONSE_TOO_LARGE`. 요청 시작부터 전체 15초 경과 시 중단 → `SOURCE_TIMEOUT`
9. 원격이 4xx/5xx → `SOURCE_FETCH_FAILED` (원격 429도 동일, 로그에는 원 상태코드 기록)

**디코딩하지 않는다.** response 객체(또는 동등 어댑터)와 final_url을 반환한다.

### 3-2. `backend/scraper.py` 리팩터링 (최소 침습)

현재 `scrape(url)`은 내부에서 `requests.get`을 한 번 호출(약 56행)하고 이후 인코딩 판별 → soup 생성 → 매체별 파싱으로 이어진다. 이 fetch 이후 부분을 함수로 추출한다:

```python
def scrape(self, url):                    # 기존 시그니처·동작 유지
    response = requests.get(...)           # 기존 그대로 (기본 리디렉션 추적 포함)
    response.raise_for_status()
    return self._parse_response(response, parse_url=url,      # 기존 분기 기준 유지
                                original_url=url)

def _parse_response(self, response, parse_url, original_url):
    # 기존 인코딩 판별(response.encoding / apparent_encoding 분기 포함)과
    # soup 생성 코드를 '그대로 이동' — response 객체를 받으므로 무변경 이동 가능
    # 단, 인코딩·파서 분기의 도메인 검사(`domain in url`)는 parse_url을 사용
    # 반환 dict의 "url" 값은 original_url을 사용
```

- 기존 인코딩 로직은 `response.encoding`·`response.apparent_encoding`·`response.text`에 의존함이 확인되어 있다(약 58~69행). **그래서 인자를 bytes가 아니라 response 객체로 받는다** — 이동 시 코드 무변경이 원칙이며, 유일하게 허용되는 수정은 도메인 검사 문자열을 `url`→`parse_url`로 바꾸는 것뿐이다.
- **분기 기준의 경로별 차이(중요)**: 기존 코드는 인코딩·파서 분기를 모두 **입력 `url`** 기준으로 한다. 따라서 기존 `scrape()`는 `parse_url=url`을 넘겨 **동작을 완전히 보존**하고, 신규 `/extract`만 `parse_url=final_url`(검증된 리디렉션 최종 URL)을 넘긴다. `/analyze` 경로의 분기 결과가 리팩터링 전후로 달라져서는 안 된다.
- 매체별 파서 분기는 전달받은 `parse_url`을 기준으로 한다. 그 값은 **기존 `scrape()`에서는 입력 URL, 신규 `/extract`에서는 검증된 리디렉션 최종 URL**이다.

### 3-3. `POST /extract` 라우트 (`backend/main.py` 또는 신규 라우터 파일)

처리 순서:
1. `X-CR-Extract-Key` 검증(환경변수 `EXTRACT_API_KEY`, 미설정 시 503 `EXTRACTOR_DISABLED`로 잠금) → 불일치 401 `UNAUTHORIZED_CALLER`. 키 비교는 `hmac.compare_digest`를 사용한다.
2. IP별 분당 20회 인메모리 제한(단순 dict + 타임스탬프로 충분) → 초과 429. 이 제한은 서버 전체의 방어 상한이다(시민별 제한은 cr-report 프록시 소관). **인메모리 방식은 프로세스 재시작 시 리셋되고 다중 워커에서는 워커별로 따로 세는 베스트에포트임을 코드 주석에 명시**한다. 요청 처리 시 1분 넘게 지난 항목을 함께 정리해 dict가 무한히 자라지 않게 한다. 외부 저장소(Redis 등) 도입 금지.
3. body의 `url` 앞뒤 공백 제거, 스킴 없으면 `https://` 보정
4. `safe_fetch(url)` 호출
5. 파싱 호출 — 3-1·3-2의 인터페이스를 정확히 따른다:
   ```python
   fetch_result = safe_fetch(url)
   article_data = scraper._parse_response(
       fetch_result.response,
       parse_url=fetch_result.final_url,   # /extract만 최종 URL 기준
       original_url=url,                   # 정규화된 요청 URL
   )
   ```
6. 결과 정규화: 제목·본문 있으면 200(`success`/`partial` + warnings), 아니면 422
7. `ValueError`(기존 스크레이퍼의 실패) → 422 `ARTICLE_NOT_FOUND`, 그 외 예외 → 500 `EXTRACTOR_ERROR`
8. 로그: `도메인 · status/code · 소요ms` 한 줄만. URL 전체·본문·쿼리스트링 금지.

Pydantic 모델: `ExtractRequest`, `ExtractArticle`, `ExtractSuccessResponse`, `ExtractErrorResponse` — 2절 계약과 필드명 일치.

- **`ExtractRequest.url`은 `str`로 정의한다.** URL 검증과 `https://` 보정은 `/extract`와 `safe_fetch`가 담당하므로, 기존 `AnalyzeRequest`의 `HttpUrl` 타입을 복사하면 스킴 없는 입력이 라우트 진입 전에 거부되어 보정 규칙이 무력화된다.
- **모든 오류 응답은 계약 JSON ③의 top-level `{ok, code, message}` 구조를 정확히 반환한다.** FastAPI 기본 `HTTPException`의 `{"detail": ...}` 래퍼 형태는 허용하지 않는다(전용 예외 핸들러 또는 `JSONResponse` 직접 반환). 테스트는 HTTP 상태뿐 아니라 JSON body 전체 구조를 검증한다.

### 3-4. 건드리지 않는 것
- 기존 `/analyze` 핸들러, `run_pipeline`, DB·캐시 함수, CORS 설정, 기존 스크레이퍼의 fetch 방식(리디렉션 자동 추적 포함).

---

## 4. 테스트 (네트워크는 모킹)

**pytest 사용 전 확인**: 작업 시작 시 `python -m pytest --version`으로 설치 여부를 확인한다. 없으면 **임의로 설치하거나 requirements.txt에 추가하지 말고** 그 사실을 완료 보고에 적는다(테스트 파일은 그대로 작성하되 실행 결과 대신 미실행 사유 기재). 저장소 루트의 기존 `test_*.py`에는 pytest용이 아닌 직접 실행 스크립트가 있으므로, 신규 테스트는 `backend/tests/` 아래에만 두고 실행 범위도 그 디렉터리로 한정한다.

`backend/tests/test_safe_fetch.py`:
- 차단: `http://localhost/x`, `http://127.0.0.1/x`, `http://10.0.0.5/x`, `http://[::1]/x`, `http://user:pw@host/x`, `ftp://…`, 포트 8080, 사설 IP로 해석되는 호스트(모킹), 공개→사설 리디렉션(모킹), 리디렉션 4회, 순환 리디렉션
- 차단: `Content-Type: application/pdf` → 415, 2MB 초과 스트림 → 413
- 통과: 정상 HTML 200, 리디렉션 1회 후 정상, `charset=euc-kr` 헤더

`backend/tests/test_extract_endpoint.py` (FastAPI TestClient + safe_fetch 모킹):
- 키 없음/불일치 → 401, 정상 → 200 계약 ① 형태, 기자·날짜 누락 → 200 계약 ② 형태(warnings 포함 + `status`가 `partial`), 파싱 실패 → 422, 분당 21회째 → 429
- `EXTRACT_API_KEY` 미설정 → 503 `EXTRACTOR_DISABLED`, 응답 body가 계약 JSON ③ 형태
- 스킴 없는 입력(`example.com/news/1`)이 `https://`로 보정되어 `article.url`에 반영되는지
- 모든 오류 응답이 `{ok, code, message}` 구조인지(`detail` 키가 없는지) 확인
- **분리 검증**: `/extract` 한 요청에서 Anthropic 클라이언트·Supabase 저장·RAG 함수가 호출되지 않음(모킹 spy로 0회 확인)
- **회귀**: `_parse_response` 추출 후에도 기존 `scrape(url)` 경로가 리팩터링 이전과 동일 결과를 내는지 — 기존 `test_scrapers.py`(또는 동등 픽스처)를 그대로 통과. EUC-KR 매체 픽스처 1건 이상 포함(깨진 본문이 success로 나오지 않는지).

로컬 픽스처: 대표 매체 HTML 3~4건을 `backend/tests/fixtures/`에 정적 파일로 저장해 사용(실 URL 의존 금지).

---

## 5. 완료 보고 (CLI가 작업 종료 시 출력할 것)

1. 생성·수정한 파일 목록과 각 파일의 역할 한 줄
2. `backend/tests/` 신규 테스트 실행 결과(통과/실패 수)와, 실행 가능한 기존 회귀 테스트의 결과. pytest 미설치로 실행하지 못했다면 그 사실
3. 계약 JSON ①·②·③과 실제 응답 모델의 필드 대조표
4. 리팩터링 전후 `scrape()` 동작 동일성의 근거(어떤 테스트가 이를 보증하는지)
5. safe_fetch의 response 반환 방식 선택((a) `_content` 주입 vs (b) 어댑터)과 그 근거
6. Railway 시작 명령(워커 수)을 저장소에서 확인 가능한지 여부 — 확인 불가라면 "기획자가 Railway 대시보드에서 uvicorn 워커 수 확인 필요"를 보고에 포함
7. 기획자가 이어서 할 일 안내: 브랜치 생성 → 커밋·푸시 → PR → Railway 환경변수 `EXTRACT_API_KEY` 설정(무작위 32자 이상) → 배포 후 스모크(골든셋 기사 URL 1건 + 차단 케이스 1건)

---

## 6. 기획자 메모 (CLI 작업 범위 아님)

- Railway 환경변수 `EXTRACT_API_KEY`는 기획자가 생성·설정한다. 같은 값이 나중에 cr-report(Vercel)의 환경변수로도 들어간다.
- 배포 후 스모크는 curl 또는 브라우저 확장 없이 가능한 방법을 PR 2 단계에서 안내 예정.
- 이 PR이 병합·배포되어도 사용자에게 보이는 변화는 없다(창구만 생기고 아무도 아직 부르지 않음).
