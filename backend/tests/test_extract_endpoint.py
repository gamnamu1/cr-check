# backend/tests/test_extract_endpoint.py
"""POST /extract 계약 검증. safe_fetch는 모킹하므로 네트워크를 쓰지 않는다."""

import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

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
            content_type="text/html; charset=utf-8", env_key=KEY, fetcher=None, reset=True):
    if reset:
        extract_api._reset_rate_limit()
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


# --- 레이트 리밋 ------------------------------------------------------------

def test_rate_limit_blocks_request_over_the_limit():
    with stubbed("generic_utf8.html", GENERIC_URL):
        for i in range(extract_api.RATE_LIMIT_PER_MINUTE):
            ok = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
            assert ok.status_code == 200, f"{i + 1}번째 요청이 실패했다"
        blocked = client.post("/extract", json={"url": GENERIC_URL}, headers=HEADERS)
    assert blocked.status_code == 429
    assert_error_body(blocked.json(), "RATE_LIMITED")
    extract_api._reset_rate_limit()


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
