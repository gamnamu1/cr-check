# backend/tests/test_scraper_regression.py
"""_parse_response 분리 이후에도 기존 scrape(url) 경로가 그대로 동작하는지 확인.

네트워크는 쓰지 않는다 — backend/tests/fixtures의 정적 HTML을 requests.get 자리에 끼운다.
"""

from unittest.mock import patch

from _support import load_fixture, make_response

import scraper as scraper_mod
from scraper import ArticleScraper

NAVER_URL = "https://n.news.naver.com/mnews/article/001/0011122334"
NATE_URL = "https://news.nate.com/view/20260828n01234"
GENERIC_URL = "https://example-news.co.kr/article/1234"
LOGIN_WALL_URL = "https://example-news.co.kr/article/9999"

CASES = [
    ("naver_utf8.html", NAVER_URL, "text/html; charset=utf-8"),
    ("nate_euckr.html", NATE_URL, "text/html"),
    ("generic_utf8.html", GENERIC_URL, "text/html; charset=utf-8"),
    ("generic_no_meta.html", "https://example-news.co.kr/article/5678", "text/html; charset=utf-8"),
]

EXPECTED_TITLE = "내년 예산안 국무회의 통과…의료·상수도 예산 신설"
EXPECTED_CONTENT_HEAD = "정부는 3일 국무회의를 열고 내년도 예산안의 세부 편성 방향을 확정했다고 밝혔다."


def scrape_fixture(fixture, url, content_type="text/html; charset=utf-8"):
    response = make_response(load_fixture(fixture), content_type=content_type, url=url)
    scraper = ArticleScraper()
    with patch.object(scraper_mod.requests, "get", lambda *args, **kwargs: response) as _:
        return scraper.scrape(url)


# --- 매체별 결과 고정 -------------------------------------------------------

def test_scrape_naver_fixture():
    result = scrape_fixture("naver_utf8.html", NAVER_URL)
    assert result["title"] == EXPECTED_TITLE
    assert result["content"].startswith(EXPECTED_CONTENT_HEAD)
    assert result["url"] == NAVER_URL
    assert result["publisher"] == "한국시사신문"
    assert result["journalist"] == "김민준 기자"
    assert result["publish_date"] == "2026.08.28. 오후 3:12"


def test_scrape_nate_euckr_fixture_decodes_korean():
    # EUC-KR 매체: charset 없는 헤더로 와도 도메인 기준으로 euc-kr을 강제해야 한다.
    # 인코딩 처리가 깨지면 제목·본문이 모지바케가 되므로 아래 비교에서 잡힌다.
    result = scrape_fixture("nate_euckr.html", NATE_URL, content_type="text/html")
    assert result["title"] == EXPECTED_TITLE
    assert result["content"].startswith(EXPECTED_CONTENT_HEAD)
    assert "�" not in result["content"]
    assert result["url"] == NATE_URL


def test_scrape_generic_fixture():
    result = scrape_fixture("generic_utf8.html", GENERIC_URL)
    assert result["title"] == EXPECTED_TITLE
    assert result["publisher"] == "한국시사신문"
    assert result["journalist"] == "김민준 기자"
    assert result["publish_date"] == "2026-08-28T15:12:00+09:00"
    assert result["url"] == GENERIC_URL


def test_scrape_raises_value_error_on_short_content():
    # 로그인 화면처럼 200이지만 본문이 없는 페이지
    try:
        scrape_fixture("login_wall.html", LOGIN_WALL_URL)
    except ValueError:
        return
    raise AssertionError("ValueError가 발생하지 않았습니다.")


# --- 리팩터링 동일성 --------------------------------------------------------

def test_scrape_matches_parse_response_for_every_fixture():
    """scrape()는 _parse_response에 parse_url·original_url을 모두 입력 URL로 넘길 뿐이다."""
    scraper = ArticleScraper()
    for fixture, url, content_type in CASES:
        via_scrape = scrape_fixture(fixture, url, content_type)
        direct = scraper._parse_response(
            make_response(load_fixture(fixture), content_type=content_type, url=url),
            parse_url=url,
            original_url=url,
        )
        assert via_scrape == direct, f"{fixture}: scrape()와 _parse_response() 결과가 다르다"


def test_scrape_keeps_original_request_settings():
    """fetch 방식(헤더·타임아웃·리디렉션 자동 추적)은 리팩터링 전과 같아야 한다."""
    calls = {}

    def recording_get(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return make_response(load_fixture("generic_utf8.html"), url=url)

    scraper = ArticleScraper()
    with patch.object(scraper_mod.requests, "get", recording_get):
        scraper.scrape(GENERIC_URL)

    assert calls["url"] == GENERIC_URL
    assert calls["kwargs"]["headers"] == scraper.headers
    assert calls["kwargs"]["timeout"] == 10
    # allow_redirects를 넘기지 않는다 = requests 기본값(자동 추적) 유지
    assert "allow_redirects" not in calls["kwargs"]
    assert "stream" not in calls["kwargs"]


def test_scrape_normalizes_scheme_less_url():
    response = make_response(load_fixture("generic_utf8.html"), url="https://example-news.co.kr/a")
    seen = {}

    def recording_get(url, **kwargs):
        seen["url"] = url
        return response

    scraper = ArticleScraper()
    with patch.object(scraper_mod.requests, "get", recording_get):
        result = scraper.scrape("example-news.co.kr/article/1234")

    assert seen["url"] == "https://example-news.co.kr/article/1234"
    assert result["url"] == "https://example-news.co.kr/article/1234"


# --- /extract 전용 경로 -----------------------------------------------------

def test_parse_response_splits_parse_url_and_original_url():
    """분기는 parse_url(최종 URL) 기준, 반환 dict의 url은 original_url."""
    scraper = ArticleScraper()
    result = scraper._parse_response(
        make_response(load_fixture("nate_euckr.html"), content_type="text/html", url=NATE_URL),
        parse_url=NATE_URL,                                   # 네이트 파서 + euc-kr 강제
        original_url="https://news.nate.com/short/abc",       # 요청 시점 URL
    )
    assert result["title"] == EXPECTED_TITLE                  # 네이트 파서가 돌았다
    assert result["url"] == "https://news.nate.com/short/abc"  # 응답 url은 요청 URL
