# backend/tests/test_extract_endpoint.py
"""POST /extract 계약 검증. safe_fetch는 모킹하므로 네트워크를 쓰지 않는다."""

import asyncio
import os
import threading
import time
from importlib.metadata import version
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import MagicMock, patch

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient

from _support import load_fixture, make_parsed_response

import extract_api
import main
from safe_fetch import SafeFetchError, SafeFetchResult

KEY = "test-extract-key-0123456789abcdef"
HEADERS = {"X-CR-Extract-Key": KEY}

NAVER_URL = "https://n.news.naver.com/mnews/article/001/0011122334"
GENERIC_URL = "https://example-news.co.kr/article/1234"
PARTIAL_URL = "https://example-news.co.kr/article/5678"
LOGIN_WALL_URL = "https://example-news.co.kr/article/9999"

EXPECTED_TITLE = "내년 예산안 국무회의 통과…의료·상수도 예산 신설"

client = TestClient(main.app)


def fetch_stub(fixture, final_url, content_type="text/html; charset=utf-8"):
    def _stub(url):
        return SafeFetchResult(
            response=make_parsed_response(load_fixture(fixture), content_type=content_type,
                                          url=final_url),
            final_url=final_url,
        )
    return _stub


def failing_stub(code, message="실패"):
    def _stub(url):
        raise SafeFetchError(code, message)
    return _stub


@contextmanager
def extract_key_env(value):
    with patch.dict(os.environ, {}, clear=False):
        if value is None:
            os.environ.pop("EXTRACT_API_KEY", None)
        else:
            os.environ["EXTRACT_API_KEY"] = value
        yield


@contextmanager
def stubbed(fixture="generic_utf8.html", final_url=GENERIC_URL,
            content_type="text/html; charset=utf-8", env_key=KEY, fetcher=None):
    # IP별 레이트리미터가 사라지면서 요청 간 리셋할 상태가 없어졌다. 동시 제한
    # 카운터는 의도적으로 리셋하지 않는다 — 누수가 있으면 드러나야 한다.
    stub = fetcher if fetcher is not None else fetch_stub(fixture, final_url, content_type)
    with extract_key_env(env_key), patch.object(extract_api, "safe_fetch", stub):
        yield


def assert_error_body(body, code):
    assert body == {"ok": False, "code": code, "message": body.get("message")}, body
    assert isinstance(body["message"], str) and body["message"]
    assert "detail" not in body


# --- 인증 · 잠금 ------------------------------------------------------------

def test_missing_key_returns_401():
    with stubbed():
        response = client.post("/extract", json={"url": GENERIC_URL})
    assert response.status_code == 401
    assert_error_body(response.json(), "UNAUTHORIZED_CALLER")


def test_wrong_key_returns_401():
    with stubbed():
        response = client.post("/extract", json={"url": GENERIC_URL},
                               headers={"X-CR-Extract-Key": "wrong-key"})
    assert response.status_code == 401
    assert_error_body(response.json(), "UNAUTHORIZED_CALLER")


def test_unset_env_key_returns_503():
    with stubbed(env_key=None):
        response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
    assert response.status_code == 503
    assert_error_body(response.json(), "EXTRACTOR_DISABLED")


# --- 계약 ① 성공 ------------------------------------------------------------

def test_success_contract():
    with stubbed("naver_utf8.html", NAVER_URL):
        response = client.post("/extract", json={"url": NAVER_URL}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert list(body) == ["ok", "status", "article", "warnings", "content_chars", "extractor_version"]
    assert body["ok"] is True
    assert body["status"] == "success"
    assert body["warnings"] == []
    assert body["extractor_version"] == "2026.09.1"
    assert body["content_chars"] == len(body["article"]["content"])

    article = body["article"]
    assert list(article) == ["title", "content", "url", "publisher", "journalist",
                             "publish_date", "source_kind"]
    assert article["title"] == EXPECTED_TITLE
    assert article["url"] == NAVER_URL
    assert article["publisher"] == "한국시사신문"
    assert article["journalist"] == "김민준 기자"
    assert article["publish_date"] == "2026-08-28"      # 원문 '2026.08.28. 오후 3:12' 정규화
    assert article["source_kind"] == "portal"


def test_iso_publish_date_is_normalized_and_outlet_kind():
    with stubbed("generic_utf8.html", GENERIC_URL):
        response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
    article = response.json()["article"]
    assert article["publish_date"] == "2026-08-28"
    assert article["source_kind"] == "generic"


def test_source_kind_labels():
    # source_kind는 리디렉션까지 마친 최종 URL의 도메인으로 정한다.
    assert extract_api._source_kind("https://n.news.naver.com/mnews/article/1") == "portal"
    assert extract_api._source_kind("https://v.daum.net/v/1") == "portal"
    assert extract_api._source_kind("https://news.nate.com/view/1") == "portal"
    assert extract_api._source_kind("https://news.zum.com/articles/1") == "portal"
    assert extract_api._source_kind("https://www.hani.co.kr/arti/politics/1.html") == "outlet"
    assert extract_api._source_kind("https://unknown-outlet.example/a") == "generic"
    # 호스트 경계로만 비교한다 — 쿼리스트링·유사 도메인에 속지 않는다
    assert extract_api._source_kind("https://example.com/a?ref=news.naver.com") == "generic"
    assert extract_api._source_kind("https://not-hani.co.kr/a") == "generic"


def test_publish_date_normalization_rules():
    assert extract_api._normalize_publish_date("2026년 8월 5일 오후 3시") == "2026-08-05"
    assert extract_api._normalize_publish_date("2026.08.28. 오후 3:12") == "2026-08-28"
    assert extract_api._normalize_publish_date("어제") == "어제"   # 정규화 실패 시 원문 그대로
    assert extract_api._normalize_publish_date(None) is None
    assert extract_api._clean_meta("미확인") is None               # 빈 문자열이 아니라 None


# --- 계약 ② 부분 성공 -------------------------------------------------------

def test_partial_contract():
    with stubbed("generic_no_meta.html", PARTIAL_URL):
        response = client.post("/extract", json={"url": PARTIAL_URL}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "partial"
    article = body["article"]
    assert article["publisher"] == "한국시사신문"
    assert article["journalist"] is None
    assert article["publish_date"] is None
    assert [w["code"] for w in body["warnings"]] == ["JOURNALIST_NOT_FOUND", "PUBLISH_DATE_NOT_FOUND"]
    for warning in body["warnings"]:
        assert list(warning) == ["code", "message"]


# --- 계약 ③ 오류 ------------------------------------------------------------

def test_parse_failure_returns_422():
    with stubbed("login_wall.html", LOGIN_WALL_URL):
        response = client.post("/extract", json={"url": LOGIN_WALL_URL}, headers=HEADERS)
    assert response.status_code == 422
    assert_error_body(response.json(), "ARTICLE_NOT_FOUND")


def test_safe_fetch_errors_map_to_contract_status():
    expected = {
        "INVALID_URL": 400,
        "UNSAFE_URL": 400,
        "RESPONSE_TOO_LARGE": 413,
        "UNSUPPORTED_CONTENT_TYPE": 415,
        "SOURCE_FETCH_FAILED": 502,
        "SOURCE_TIMEOUT": 504,
    }
    for code, status in expected.items():
        with stubbed(fetcher=failing_stub(code)):
            response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
        assert response.status_code == status, code
        assert_error_body(response.json(), code)


def test_unexpected_parser_error_returns_500_without_internals():
    def boom(url):
        raise RuntimeError("/Users/secret/path.py 내부 오류")

    with stubbed(fetcher=boom):
        response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
    assert response.status_code == 500
    body = response.json()
    assert_error_body(body, "EXTRACTOR_ERROR")
    assert "secret" not in body["message"] and "Traceback" not in body["message"]


def test_missing_url_field_uses_contract_shape():
    with stubbed():
        response = client.post("/extract", json={}, headers=HEADERS)
    assert response.status_code == 400
    assert_error_body(response.json(), "INVALID_URL")


def test_blank_url_returns_invalid_url():
    with stubbed():
        response = client.post("/extract", json={"url": "   "}, headers=HEADERS)
    assert response.status_code == 400
    assert_error_body(response.json(), "INVALID_URL")


# --- URL 정규화 -------------------------------------------------------------

def test_scheme_less_url_is_normalized_to_https():
    normalized = "https://example-news.co.kr/news/1"
    with stubbed("generic_utf8.html", normalized):
        response = client.post("/extract", json={"url": "  example-news.co.kr/news/1  "},
                               headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["article"]["url"] == normalized


def test_article_url_is_request_url_not_redirect_target():
    requested = "https://example-news.co.kr/short/abc"
    with stubbed("generic_utf8.html", final_url="https://example-news.co.kr/article/1234"):
        response = client.post("/extract", json={"url": requested}, headers=HEADERS)
    assert response.json()["article"]["url"] == requested


# --- 동시 제한 --------------------------------------------------------------
#
# 비동기 시험은 요청 태스크의 취소 시점을 직접 다뤄야 해서 TestClient(동기) 대신
# httpx.ASGITransport + asyncio.Task를 쓴다. 시험 도구는 anyio의 pytest 플러그인이다
# (anyio가 이미 starlette 의존성으로 들어와 있어 추가 설치가 없고, pytest 설정
# 파일 없이 마커만으로 동작한다). 백엔드는 아래 fixture로 asyncio에 고정한다.

BLOCK_TIMEOUT = 10          # 시험이 매달리지 않게 하는 안전 상한(초)
HOLD_URL = "https://example-news.co.kr/article/hold"
LATE_URL = "https://example-news.co.kr/article/late"


@pytest.fixture
def anyio_backend():
    """asyncio 전용 취소 시험이므로 백엔드를 고정한다.

    anyio 플러그인의 기본값은 같은 시험을 여러 백엔드로 반복 실행하는데,
    여기서는 asyncio.Task.cancel()의 전달 시점을 직접 다루므로 맞지 않는다.
    """
    return "asyncio"


class BlockingFetch:
    """safe_fetch 대역 — 진입 URL을 기록하고, HOLD_URL만 풀어 줄 때까지 붙잡는다."""

    def __init__(self, hold=(HOLD_URL,)):
        self._hold = set(hold)
        self._lock = threading.Lock()
        self._entered = []
        self.release = threading.Event()

    def __call__(self, url):
        with self._lock:
            self._entered.append(url)
        if url in self._hold:
            self.release.wait(BLOCK_TIMEOUT)
        return SafeFetchResult(
            response=make_parsed_response(load_fixture("generic_utf8.html"),
                                          content_type="text/html; charset=utf-8",
                                          url=GENERIC_URL),
            final_url=GENERIC_URL,
        )

    def entered_count(self, url):
        with self._lock:
            return self._entered.count(url)


class FakeParser:
    """_parse_response만 흉내 내는 스크레이퍼 대역."""

    def __init__(self, exc):
        self.exc = exc

    def _parse_response(self, response, parse_url=None, original_url=None):
        raise self.exc


async def wait_until(predicate, message):
    """조건이 참이 될 때까지 이벤트 루프를 돌려 준다."""
    deadline = time.monotonic() + BLOCK_TIMEOUT
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError(message)
        await asyncio.sleep(0.01)


@contextmanager
def concurrency_limit(value):
    """동시 추출 상한만 잠시 낮춘다. 점유 수 카운터는 건드리지 않는다."""
    with patch.object(extract_api, "MAX_CONCURRENT_EXTRACTIONS", value):
        yield


@contextmanager
def thread_limit(value):
    """공유 스레드풀 한도를 시험 동안만 낮추고 반드시 되돌린다.

    운영 코드의 스레드 한도는 건드리지 않는다 — 여기서만 쓰는 시험 장치다.
    """
    limiter = anyio.to_thread.current_default_thread_limiter()
    original = limiter.total_tokens
    limiter.total_tokens = value
    try:
        yield
    finally:
        limiter.total_tokens = original


@asynccontextmanager
async def asgi_client():
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


def post(http, url=GENERIC_URL):
    return http.post("/extract", json={"url": url}, headers=HEADERS)


async def drain_tasks(held):
    """정리 — 등록된 요청 태스크를 BLOCK_TIMEOUT 안에서 회수한다.

    반드시 모킹과 시험용 한도가 **살아 있는 동안** 불러야 한다. 먼저 원복되면
    스레드 자리를 기다리던 태스크가 모킹 밖의 safe_fetch를 타고 실제 언론사로
    요청을 내보낸다.

    완료된 태스크의 결과·예외(CancelledError 포함)를 수거하는 것이 전부다.
    시험 본문의 원래 실패를 대신 삼키지 않는다 — 원래 예외는 그대로 전파되고,
    여기서 난 실패는 그 예외에 체인되어 traceback에 함께 나온다.
    """
    if not held:
        return
    done, pending = await asyncio.wait(held, timeout=BLOCK_TIMEOUT)
    for task in done:
        if not task.cancelled():
            task.exception()    # 수거하지 않으면 미회수 예외 경고가 남는다
    assert not pending, \
        f"정리 시간({BLOCK_TIMEOUT}초) 안에 끝나지 않은 요청 태스크 {len(pending)}건"


@pytest.mark.anyio
async def test_requests_over_the_limit_get_busy_and_slots_return_after_release():
    """상황 1·3 — 상한까지 차면 503 EXTRACTOR_BUSY, 해제 뒤 점유 수 0으로 복귀."""
    blocker = BlockingFetch()
    with concurrency_limit(2), extract_key_env(KEY), \
            patch.object(extract_api, "safe_fetch", blocker):
        async with asgi_client() as http:
            held = []
            try:
                for _ in range(2):      # 만드는 즉시 정리 대상으로 등록한다
                    held.append(asyncio.create_task(post(http, HOLD_URL)))
                await wait_until(lambda: blocker.entered_count(HOLD_URL) == 2,
                                 "모의 작업 2건이 스레드에 진입하지 않았다")
                assert extract_api._active_extractions == 2

                busy = await post(http)
                assert not blocker.release.is_set()     # 아직 아무 작업도 풀지 않았다
                assert busy.status_code == 503
                assert_error_body(busy.json(), "EXTRACTOR_BUSY")

                blocker.release.set()
                for task in held:
                    assert (await task).status_code == 200

                assert extract_api._active_extractions == 0
                assert (await post(http)).status_code == 200
            finally:
                blocker.release.set()
                await drain_tasks(held)
                await wait_until(lambda: extract_api._active_extractions == 0,
                                 "정리 후에도 점유 수가 0으로 돌아오지 않았다")


@pytest.mark.anyio
async def test_busy_is_returned_without_waiting_for_a_thread_slot():
    """상황 2 — 공유 스레드풀까지 찬 상태에서도 다른 작업을 풀기 전에 503이 돌아온다."""
    blocker = BlockingFetch()
    with concurrency_limit(2), thread_limit(2), extract_key_env(KEY), \
            patch.object(extract_api, "safe_fetch", blocker):
        async with asgi_client() as http:
            held = []
            try:
                for _ in range(2):      # 만드는 즉시 정리 대상으로 등록한다
                    held.append(asyncio.create_task(post(http, HOLD_URL)))
                await wait_until(lambda: blocker.entered_count(HOLD_URL) == 2,
                                 "모의 작업 2건이 스레드에 진입하지 않았다")

                # 스레드 토큰 2개가 모두 점유돼 있다. 상한 판단을 스레드 안에서 했다면
                # 거절하려고도 스레드 자리를 기다리게 되어 여기서 매달린다.
                busy = await asyncio.wait_for(post(http), timeout=5)
                assert not blocker.release.is_set()
                assert busy.status_code == 503
                assert_error_body(busy.json(), "EXTRACTOR_BUSY")

                blocker.release.set()
                for task in held:
                    assert (await task).status_code == 200
                assert extract_api._active_extractions == 0
            finally:
                blocker.release.set()
                await drain_tasks(held)
                await wait_until(lambda: extract_api._active_extractions == 0,
                                 "정리 후에도 점유 수가 0으로 돌아오지 않았다")


@pytest.mark.anyio
async def test_running_work_keeps_its_slot_when_the_request_is_cancelled():
    """상황 4 — 실행 중 취소돼도 작업이 끝날 때까지 슬롯을 유지한다(§3.3-a)."""
    blocker = BlockingFetch()
    with concurrency_limit(1), extract_key_env(KEY), \
            patch.object(extract_api, "safe_fetch", blocker):
        async with asgi_client() as http:
            held = []
            try:
                running = asyncio.create_task(post(http, HOLD_URL))
                held.append(running)    # 만드는 즉시 정리 대상으로 등록한다
                await wait_until(lambda: blocker.entered_count(HOLD_URL) == 1,
                                 "모의 작업이 스레드에 진입하지 않았다")

                running.cancel()
                await asyncio.sleep(0.05)

                # 작업이 아직 끝나지 않았다 — 자리를 미리 반환했다면 여기서 200이 난다.
                busy = await post(http)
                assert not blocker.release.is_set()
                assert busy.status_code == 503
                assert_error_body(busy.json(), "EXTRACTOR_BUSY")
                assert extract_api._active_extractions == 1

                blocker.release.set()
                with pytest.raises(asyncio.CancelledError):
                    await running

                await wait_until(lambda: extract_api._active_extractions == 0,
                                 "작업 종료 후 점유 수가 0으로 돌아오지 않았다")
                assert (await post(http)).status_code == 200
            finally:
                blocker.release.set()
                await drain_tasks(held)
                await wait_until(lambda: extract_api._active_extractions == 0,
                                 "정리 후에도 점유 수가 0으로 돌아오지 않았다")


@pytest.mark.anyio
async def test_cancel_before_thread_start_is_observed(capsys):
    """상황 5(관측형) — 예약 후 스레드 시작 전 취소가 실제로 어떻게 처리되는지 관측한다.

    설치된 anyio·starlette의 취소 의미론에 달린 문제라 결과를 기록만 하고,
    취소가 먼저 전달된 경우에만 (b)·(c)를 검증한다. 헬퍼 자체의 결정론적 검증은
    test_reservation_state_machine_releases_exactly_once가 따로 한다.
    """
    blocker = BlockingFetch()
    mark_started_calls = []
    real_mark_started = extract_api._mark_started

    def spy(reservation):
        result = real_mark_started(reservation)
        mark_started_calls.append(result)
        return result

    with concurrency_limit(5), thread_limit(1), extract_key_env(KEY), \
            patch.object(extract_api, "safe_fetch", blocker), \
            patch.object(extract_api, "_mark_started", spy):
        async with asgi_client() as http:
            held = []
            try:
                holding = asyncio.create_task(post(http, HOLD_URL))
                held.append(holding)    # 만드는 즉시 정리 대상으로 등록한다
                await wait_until(lambda: blocker.entered_count(HOLD_URL) == 1,
                                 "선행 작업이 스레드에 진입하지 않았다")

                # 스레드 토큰은 이미 없다. 그런데도 예약은 잡힌다 — 예약이
                # run_in_threadpool 진입 전에 일어난다는 증거이기도 하다.
                late = asyncio.create_task(post(http, LATE_URL))
                held.append(late)
                await wait_until(lambda: extract_api._active_extractions == 2,
                                 "두 번째 요청이 슬롯을 예약하지 않았다")
                assert blocker.entered_count(LATE_URL) == 0

                late.cancel()
                await asyncio.sleep(0.05)

                blocker.release.set()
                assert (await holding).status_code == 200
                try:
                    await late
                    late_outcome = "취소가 전달되지 않고 응답이 반환됨"
                except asyncio.CancelledError:
                    late_outcome = "CancelledError"

                # 스레드 자리가 난 뒤 뒤늦게 실행되지 않는지 확인할 여유를 준다.
                await asyncio.sleep(0.2)

                late_extracted = blocker.entered_count(LATE_URL) > 0
                blocked_late_start = any(result is False for result in mark_started_calls)
                with capsys.disabled():
                    print(f"\n[관측·상황5] late 태스크={late_outcome} · "
                          f"늦은 가져오기 실행={late_extracted} · "
                          f"mark_started False 반환={blocked_late_start} · "
                          f"anyio={version('anyio')} · starlette={version('starlette')}")

                if not late_extracted:
                    # 취소가 시작 전에 전달됐다 — (b) 예약 반환, (c) 늦은 실행 없음.
                    assert extract_api._active_extractions == 0

                await wait_until(lambda: extract_api._active_extractions == 0,
                                 "점유 수가 0으로 돌아오지 않았다")
            finally:
                blocker.release.set()
                await drain_tasks(held)
                await wait_until(lambda: extract_api._active_extractions == 0,
                                 "정리 후에도 점유 수가 0으로 돌아오지 않았다")


def test_fetch_stage_errors_keep_contract_and_release_the_slot():
    """상황 6 — 가져오기 단계 두 갈래의 코드·메시지 유지, 슬롯 반환."""
    with stubbed(fetcher=failing_stub("SOURCE_TIMEOUT", "기사를 가져오지 못했습니다.")):
        response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
    assert response.status_code == 504
    assert_error_body(response.json(), "SOURCE_TIMEOUT")
    assert response.json()["message"] == "기사를 가져오지 못했습니다."   # exc.message 그대로
    assert extract_api._active_extractions == 0

    def boom(url):
        raise RuntimeError("/Users/secret/path.py 내부 오류")

    with stubbed(fetcher=boom):
        response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
    assert response.status_code == 500
    body = response.json()
    assert_error_body(body, "EXTRACTOR_ERROR")
    assert body["message"] == "기사를 가져오는 중 오류가 발생했습니다."
    assert "secret" not in body["message"] and "Traceback" not in body["message"]
    assert extract_api._active_extractions == 0

    with stubbed("generic_utf8.html", GENERIC_URL):
        assert client.post("/extract", json={"url": GENERIC_URL},
                           headers=HEADERS).status_code == 200


def test_parse_stage_errors_keep_contract_and_release_the_slot():
    """상황 7 — 파싱 단계 두 갈래. 기존 시험이 덮지 못한 네 번째 갈래까지 확인한다."""
    cases = (
        (ValueError("본문 없음"), 422, "ARTICLE_NOT_FOUND",
         "기사 제목 또는 본문을 추출하지 못했습니다."),
        (RuntimeError("/Users/secret/path.py 내부 오류"), 500, "EXTRACTOR_ERROR",
         "기사 파싱 중 오류가 발생했습니다."),
    )
    for exc, status, code, message in cases:
        with stubbed("generic_utf8.html", GENERIC_URL), \
                patch.object(extract_api, "_scraper", FakeParser(exc)):
            response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
        assert response.status_code == status, code
        body = response.json()
        assert_error_body(body, code)
        assert body["message"] == message
        assert "secret" not in body["message"] and "Traceback" not in body["message"]
        assert extract_api._active_extractions == 0

    with stubbed("generic_utf8.html", GENERIC_URL):
        assert client.post("/extract", json={"url": GENERIC_URL},
                           headers=HEADERS).status_code == 200


def test_threadpool_dispatch_failure_keeps_the_error_contract():
    """보완 1 — 동기 함수가 시작되기 전 스레드 제출 단계의 예외도 계약 형태로 나간다.

    여기서 잡지 않으면 프레임워크 기본 500(text/plain "Internal Server Error")이
    나가 {ok, code, message} 계약이 깨진다. extract_api가 run_in_threadpool을
    모듈 전역으로 가져오므로 모듈 속성을 패치한다(fastapi.concurrency 쪽은 안 먹는다).
    """
    def boom(func, *args, **kwargs):
        raise RuntimeError("/Users/secret/path.py 내부 오류")

    with stubbed("generic_utf8.html", GENERIC_URL), \
            patch.object(extract_api, "run_in_threadpool", boom):
        response = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)

    assert response.status_code == 500
    body = response.json()
    assert_error_body(body, "EXTRACTOR_ERROR")
    assert body["message"] == "기사를 가져오는 중 오류가 발생했습니다."
    assert "secret" not in body["message"] and "Traceback" not in body["message"]
    # 동기 함수가 시작되기 전에 실패했으므로 예약은 pending에 머물고,
    # 라우트 finally의 _release_if_pending()이 반환한다.
    assert extract_api._active_extractions == 0

    with stubbed("generic_utf8.html", GENERIC_URL):
        assert client.post("/extract", json={"url": GENERIC_URL},
                           headers=HEADERS).status_code == 200


def test_reservation_state_machine_releases_exactly_once():
    """상황 8 — 3상태 예약 헬퍼를 런타임 취소와 무관하게 직접 확인한다.

    (b) 시작 전 반환 · (c) 반환 뒤 늦은 실행 금지 · (d) 이중 반환과 음수 방지.
    """
    assert extract_api._active_extractions == 0

    reservation = extract_api._reserve()
    assert reservation is not None
    assert reservation.state == extract_api._PENDING
    assert extract_api._active_extractions == 1

    extract_api._release_if_pending(reservation)                # (b)
    assert reservation.state == extract_api._RELEASED
    assert extract_api._active_extractions == 0

    assert extract_api._mark_started(reservation) is False      # (c)
    assert reservation.state == extract_api._RELEASED
    assert extract_api._active_extractions == 0

    extract_api._release(reservation)                           # (d)
    extract_api._release_if_pending(reservation)
    assert extract_api._active_extractions == 0

    again = extract_api._reserve()
    assert again is not None and again.state == extract_api._PENDING
    assert extract_api._active_extractions == 1
    assert extract_api._mark_started(again) is True
    assert again.state == extract_api._RUNNING
    extract_api._release_if_pending(again)                      # running이면 no-op
    assert extract_api._active_extractions == 1
    extract_api._release(again)
    assert again.state == extract_api._RELEASED
    assert extract_api._active_extractions == 0


def test_reserve_refuses_past_the_limit():
    """상한에 도달하면 _reserve()가 None을 돌려준다(라우트의 503 분기 조건)."""
    held = []
    try:
        with concurrency_limit(2):
            held = [extract_api._reserve(), extract_api._reserve()]
            assert all(r is not None for r in held)
            assert extract_api._reserve() is None
            assert extract_api._active_extractions == 2
    finally:
        for reservation in held:
            if reservation is not None:
                extract_api._release_if_pending(reservation)
    assert extract_api._active_extractions == 0


# --- 분리 검증 --------------------------------------------------------------

def test_extract_never_touches_pipeline_storage_or_llm_clients():
    """/extract 한 요청에서 RAG·Supabase·LLM 클라이언트가 한 번도 불리지 않는다."""
    import core.pattern_matcher as pattern_matcher
    import core.report_generator as report_generator
    import core.storage as storage

    spies = {
        "run_pipeline": patch.object(main, "run_pipeline", MagicMock()),
        "get_cached_analysis": patch.object(main, "get_cached_analysis", MagicMock()),
        "save_analysis_result": patch.object(main, "save_analysis_result", MagicMock()),
        "pattern_matcher.Anthropic": patch.object(pattern_matcher, "Anthropic", MagicMock()),
        "pattern_matcher.OpenAI": patch.object(pattern_matcher, "OpenAI", MagicMock()),
        "report_generator.Anthropic": patch.object(report_generator, "Anthropic", MagicMock()),
        "storage.httpx": patch.object(storage, "httpx", MagicMock()),
    }
    started = {name: ctx.__enter__() for name, ctx in spies.items()}
    try:
        with stubbed("naver_utf8.html", NAVER_URL):
            response = client.post("/extract", json={"url": NAVER_URL}, headers=HEADERS)
        assert response.status_code == 200
        for name, spy in started.items():
            assert not spy.called, f"{name}이(가) /extract 경로에서 호출됐다"
    finally:
        for ctx in spies.values():
            ctx.__exit__(None, None, None)
