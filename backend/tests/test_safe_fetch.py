# backend/tests/test_safe_fetch.py
"""safe_fetch의 SSRF 방어와 응답 상한 검증. 네트워크는 전부 모킹한다."""

from unittest.mock import patch

from _support import SequenceGet, fake_dns, dns_failure, make_response, redirect_response

import safe_fetch
from safe_fetch import SafeFetchError, safe_fetch as fetch

PUBLIC_IP = "8.8.8.8"           # 공개 대역 (203.0.113.0/24 등 문서용 대역은 is_private로 차단된다)
HTML = "<html><body><p>본문</p></body></html>".encode("utf-8")


def assert_error(url, expected_code, get=None, dns=None):
    """safe_fetch가 지정한 코드로 실패하는지 확인하고 예외를 돌려준다."""
    resolver = dns if dns is not None else fake_dns("8.8.8.8")
    getter = get if get is not None else SequenceGet(make_response(HTML))
    with patch.object(safe_fetch.socket, "getaddrinfo", resolver), \
            patch.object(safe_fetch.requests, "get", getter):
        try:
            fetch(url)
        except SafeFetchError as exc:
            assert exc.code == expected_code, f"{url}: {expected_code} 기대, {exc.code} 발생"
            return exc
    raise AssertionError(f"{url}: SafeFetchError({expected_code})가 발생하지 않았습니다.")


def run_fetch(url, get, dns=None):
    resolver = dns if dns is not None else fake_dns("8.8.8.8")
    with patch.object(safe_fetch.socket, "getaddrinfo", resolver), \
            patch.object(safe_fetch.requests, "get", get):
        return fetch(url)


# --- URL·호스트 단계 차단 ---------------------------------------------------

def test_rejects_localhost_hostname():
    assert_error("http://localhost/x", "UNSAFE_URL")


def test_rejects_dot_local_hostname():
    assert_error("http://printer.local/x", "UNSAFE_URL")


def test_rejects_loopback_ipv4():
    assert_error("http://127.0.0.1/x", "UNSAFE_URL")


def test_rejects_private_ipv4():
    assert_error("http://10.0.0.5/x", "UNSAFE_URL")


def test_rejects_link_local_ipv4():
    assert_error("http://169.254.169.254/x", "UNSAFE_URL")


def test_rejects_cgnat_ipv4():
    assert_error("http://100.64.0.1/x", "UNSAFE_URL")


def test_rejects_ipv6_loopback():
    assert_error("http://[::1]/x", "UNSAFE_URL")


def test_rejects_ipv6_unique_local():
    assert_error("http://[fd00::1]/x", "UNSAFE_URL")


def test_rejects_ipv4_mapped_ipv6():
    assert_error("http://[::ffff:10.0.0.5]/x", "UNSAFE_URL")


def test_rejects_userinfo():
    assert_error("http://user:pw@example-news.co.kr/x", "INVALID_URL")


def test_rejects_non_http_scheme():
    assert_error("ftp://example-news.co.kr/x", "INVALID_URL")


def test_rejects_missing_host():
    assert_error("https:///x", "INVALID_URL")


def test_rejects_disallowed_port():
    assert_error("http://example-news.co.kr:8080/x", "UNSAFE_URL", dns=fake_dns(PUBLIC_IP))


def test_allows_explicit_default_ports():
    getter = SequenceGet(make_response(HTML))
    result = run_fetch("https://example-news.co.kr:443/x", getter, dns=fake_dns(PUBLIC_IP))
    assert result.final_url == "https://example-news.co.kr:443/x"


# --- DNS 단계 ---------------------------------------------------------------

def test_rejects_host_resolving_to_private_ip():
    assert_error("http://sneaky.example/x", "UNSAFE_URL", dns=fake_dns("10.1.2.3"))


def test_rejects_when_any_resolved_address_is_private():
    # 공개 IP와 사설 IP를 함께 돌려주는 우회 시도
    assert_error("http://sneaky.example/x", "UNSAFE_URL", dns=fake_dns(PUBLIC_IP, "192.168.0.9"))


def test_dns_failure_maps_to_source_fetch_failed():
    assert_error("http://nx.example/x", "SOURCE_FETCH_FAILED", dns=dns_failure)


# --- 리디렉션 ---------------------------------------------------------------

def test_rejects_redirect_to_private_host():
    getter = SequenceGet(redirect_response("http://10.0.0.5/internal"))
    assert_error("http://example-news.co.kr/a", "UNSAFE_URL", get=getter, dns=fake_dns(PUBLIC_IP))


def test_rejects_more_than_three_redirects():
    getter = SequenceGet(*[redirect_response(f"https://example-news.co.kr/hop{i}") for i in range(4)])
    assert_error("https://example-news.co.kr/a", "SOURCE_FETCH_FAILED", get=getter,
                 dns=fake_dns(PUBLIC_IP))


def test_rejects_redirect_loop():
    getter = SequenceGet(
        redirect_response("https://example-news.co.kr/b"),
        redirect_response("https://example-news.co.kr/a"),
    )
    assert_error("https://example-news.co.kr/a", "SOURCE_FETCH_FAILED", get=getter,
                 dns=fake_dns(PUBLIC_IP))


def test_rejects_redirect_without_location():
    getter = SequenceGet(make_response(b"", status=302))
    assert_error("https://example-news.co.kr/a", "SOURCE_FETCH_FAILED", get=getter,
                 dns=fake_dns(PUBLIC_IP))


def test_follows_single_redirect():
    getter = SequenceGet(
        redirect_response("https://example-news.co.kr/final"),
        make_response(HTML, url="https://example-news.co.kr/final"),
    )
    result = run_fetch("https://example-news.co.kr/a", getter, dns=fake_dns(PUBLIC_IP))
    assert result.final_url == "https://example-news.co.kr/final"
    assert getter.requested_urls == ["https://example-news.co.kr/a", "https://example-news.co.kr/final"]


def test_resolves_relative_redirect():
    getter = SequenceGet(
        redirect_response("/section/final"),
        make_response(HTML),
    )
    result = run_fetch("https://example-news.co.kr/a/b", getter, dns=fake_dns(PUBLIC_IP))
    assert result.final_url == "https://example-news.co.kr/section/final"


def test_does_not_follow_meta_refresh():
    body = ('<html><head><meta http-equiv="refresh" content="0; url=http://10.0.0.5/x">'
            "</head><body><p>본문</p></body></html>").encode("utf-8")
    getter = SequenceGet(make_response(body))
    result = run_fetch("https://example-news.co.kr/a", getter, dns=fake_dns(PUBLIC_IP))
    # meta refresh는 따라가지 않으므로 추가 요청이 없어야 한다
    assert getter.requested_urls == ["https://example-news.co.kr/a"]
    assert result.final_url == "https://example-news.co.kr/a"


# --- 응답 검증 --------------------------------------------------------------

def test_rejects_non_html_content_type():
    getter = SequenceGet(make_response(b"%PDF-1.4", content_type="application/pdf"))
    assert_error("https://example-news.co.kr/a.pdf", "UNSUPPORTED_CONTENT_TYPE", get=getter,
                 dns=fake_dns(PUBLIC_IP))


def test_rejects_missing_content_type():
    getter = SequenceGet(make_response(HTML, content_type=None))
    assert_error("https://example-news.co.kr/a", "UNSUPPORTED_CONTENT_TYPE", get=getter,
                 dns=fake_dns(PUBLIC_IP))


def test_rejects_oversized_body():
    oversized = b"a" * (safe_fetch.MAX_RESPONSE_BYTES + 1)
    getter = SequenceGet(make_response(oversized))
    assert_error("https://example-news.co.kr/a", "RESPONSE_TOO_LARGE", get=getter,
                 dns=fake_dns(PUBLIC_IP))


def test_accepts_body_at_size_limit():
    at_limit = b"a" * safe_fetch.MAX_RESPONSE_BYTES
    getter = SequenceGet(make_response(at_limit))
    result = run_fetch("https://example-news.co.kr/a", getter, dns=fake_dns(PUBLIC_IP))
    assert len(result.response.content) == safe_fetch.MAX_RESPONSE_BYTES


def test_rejects_upstream_error_status():
    getter = SequenceGet(make_response(b"nope", status=503))
    exc = assert_error("https://example-news.co.kr/a", "SOURCE_FETCH_FAILED", get=getter,
                       dns=fake_dns(PUBLIC_IP))
    assert "503" in exc.message


def test_rejects_upstream_rate_limit_status():
    getter = SequenceGet(make_response(b"slow down", status=429))
    exc = assert_error("https://example-news.co.kr/a", "SOURCE_FETCH_FAILED", get=getter,
                       dns=fake_dns(PUBLIC_IP))
    assert "429" in exc.message


def test_maps_request_timeout():
    def timeout_get(url, **kwargs):
        raise safe_fetch.requests.exceptions.ConnectTimeout("too slow")
    assert_error("https://example-news.co.kr/a", "SOURCE_TIMEOUT", get=timeout_get,
                 dns=fake_dns(PUBLIC_IP))


def test_maps_connection_error():
    def failing_get(url, **kwargs):
        raise safe_fetch.requests.exceptions.ConnectionError("refused")
    assert_error("https://example-news.co.kr/a", "SOURCE_FETCH_FAILED", get=failing_get,
                 dns=fake_dns(PUBLIC_IP))


# --- 정상 경로 --------------------------------------------------------------

def test_accepts_plain_html():
    getter = SequenceGet(make_response(HTML))
    result = run_fetch("https://example-news.co.kr/a", getter, dns=fake_dns(PUBLIC_IP))
    assert result.final_url == "https://example-news.co.kr/a"
    assert result.response.status_code == 200
    assert result.response.content == HTML


def test_preserves_euckr_charset_header():
    body = "<html><body><p>한글 본문</p></body></html>".encode("euc-kr")
    getter = SequenceGet(make_response(body, content_type="text/html; charset=euc-kr"))
    result = run_fetch("https://news.nate.com/view/1", getter, dns=fake_dns(PUBLIC_IP))
    assert result.response.encoding == "euc-kr"
    assert "한글 본문" in result.response.text


def test_charsetless_html_keeps_requests_default_encoding():
    # charset이 없는 text/html은 requests와 마찬가지로 ISO-8859-1이어야 한다.
    # 스크레이퍼의 apparent_encoding 폴백 분기가 이 값에 의존한다.
    getter = SequenceGet(make_response("<html><p>한글</p></html>".encode("utf-8")))
    result = run_fetch("https://example-news.co.kr/a", getter, dns=fake_dns(PUBLIC_IP))
    assert result.response.encoding == "ISO-8859-1"
    assert result.response.apparent_encoding is not None


def test_uses_scraper_user_agent_and_no_auto_redirect():
    getter = SequenceGet(make_response(HTML))
    run_fetch("https://example-news.co.kr/a", getter, dns=fake_dns(PUBLIC_IP))
    kwargs = getter.kwargs[0]
    assert kwargs["headers"]["User-Agent"] == safe_fetch._DEFAULT_HEADERS["User-Agent"]
    assert kwargs["allow_redirects"] is False
    assert kwargs["stream"] is True
    assert kwargs["timeout"] == (safe_fetch.CONNECT_TIMEOUT, safe_fetch.READ_TIMEOUT)
