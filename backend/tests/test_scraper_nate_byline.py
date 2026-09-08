# backend/tests/test_scraper_nate_byline.py
"""네이트 바이라인 추출·제거 회귀 테스트.

fixture 는 EUC-KR 바이트다 — _parse_response() 가 news.nate.com 응답의 encoding 을
무조건 euc-kr 로 지정하기 때문에, UTF-8 fixture 를 네이트 URL 에 넣으면 실제 파싱
입력이 재현되지 않는다.

본문은 `#realArtcContents` 직계 text node + <br> 구조다. 이번에 고치는 실패가 바로
그 구조에서 발생하며, <p> 구조 fixture 로는 회귀를 잡지 못한다.

검증은 제품 경로 그대로 태운다(scrape() → _parse_response() → _scrape_nate()).
인코딩을 피하려고 _scrape_nate() 를 직접 부르지 않는다.
"""

from unittest.mock import patch

from _support import load_fixture, make_response

import scraper as scraper_mod
from scraper import ArticleScraper

NATE_URL = "https://news.nate.com/view/20260908n00001"

# fixture 본문의 합성 문장. 실제 기사 본문이 아니다.
P1 = "시험용 첫 문단이다. 회귀 테스트를 위해 만든 합성 문장이며 실제 기사 본문이 아니다."
P2 = "시험용 둘째 문단이다. 바이라인 탐색 범위를 확인하기 위한 채움 문장이다."
P3 = "시험용 셋째 문단이다. 바이라인 줄을 빼고도 본문이 길이 게이트를 넘도록 두는 채움 문장이다."
SHORT = "짧은 시험 기사다. 바이라인 줄을 빼면 본문이 길이 게이트에 못 미치게 되는 경우를 만들기 위한 합성 문장이며 실제 기사가 아니다."
NOTICE = "이 기사는 자동 번역을 바탕으로 만든 합성 안내 문장이다."

# extract_api.MIN_CONTENT_CHARS 와 같은 기준. 미달이면 /extract 가 ARTICLE_NOT_FOUND 로
# 전체 실패를 돌려주므로, 바이라인 제거가 이 선을 깨지 않는지 확인한다.
MIN_CONTENT_CHARS = 100


def joined(*lines):
    """파서가 논리 줄 사이에 빈 줄을 하나 두는 것과 같은 모양으로 잇는다."""
    return "\n\n".join(lines)


def scrape_nate(fixture, content_type="text/html"):
    """charset 없는 헤더로 오는 실제 네이트 응답 경로를 재현한다."""
    response = make_response(load_fixture(fixture), content_type=content_type, url=NATE_URL)
    scraper = ArticleScraper()
    with patch.object(scraper_mod.requests, "get", lambda *args, **kwargs: response):
        return scraper.scrape(NATE_URL)


# --- A형: 이름 앞 프리픽스 --------------------------------------------------

def test_nate_region_prefix_byline_is_extracted_and_line_removed():
    result = scrape_nate("nate_a_prefix_euckr.html")
    assert result["journalist"] == "김민준 기자"
    # 추출에 쓴 그 줄만 빠지고 나머지는 그대로다.
    assert result["content"] == joined(P1, P2, "ⓒ 예시일보, 무단 전재 및 재배포 금지")
    assert "포항=김민준 기자" not in result["content"]


def test_nate_media_prefix_byline_with_parenthesized_email():
    # '데일리안 이정희 기자 (jh9999@dailian.co.kr)' 실측 형태.
    # 구분자가 없어 publisher 와 정확히 일치할 때만 프리픽스로 인정한다.
    result = scrape_nate("nate_a_media_prefix_euckr.html")
    assert result["journalist"] == "서지우 기자"
    assert result["content"] == joined(P1, P2, "- Copyrights ⓒ 예시일보, 무단 전재-재배포 금지 -")
    assert "예시일보 서지우 기자" not in result["content"]


# --- B형: 바이라인 뒤 비기사성 후미 줄 --------------------------------------

def test_nate_byline_behind_promo_and_copyright_lines():
    result = scrape_nate("nate_b_tail_noise_euckr.html")
    assert result["journalist"] == "서지우 기자"
    # 건너뛴 후미 줄들은 본문에 그대로 남는다. 바이라인 줄만 빠진다.
    assert result["content"] == joined(
        P1, P2, "이 시각 많이 본 뉴스", "▶", "▶", "▶ /",
        "ⓒ 예시일보, 무단 전재 및 재배포 금지")
    assert "서지우 기자 seo@example-news.co.kr" not in result["content"]


# --- C형: 본문 머리 dateline ------------------------------------------------

def test_nate_head_dateline_is_extracted_and_body_kept():
    result = scrape_nate("nate_c_head_euckr.html")
    assert result["journalist"] == "한도윤 기자"
    # 머리 dateline 은 제거하지 않는다 — 기사 출처를 보여주는 검증 대상이다.
    assert result["content"].startswith("[서울=예시통신] 한도윤 기자 = ")
    assert result["content"] == joined(f"[서울=예시통신] 한도윤 기자 = {P1}", P2, "ⓒ 예시통신")


def test_nate_head_dateline_intern_is_not_a_name():
    result = scrape_nate("nate_c_head_intern_euckr.html")
    assert result["journalist"] == "나윤서 기자"
    assert "인턴" not in result["journalist"]
    assert result["content"].startswith("[서울=예시통신]나윤서 인턴 기자 = ")


def test_nate_head_dateline_joint_names_are_joined():
    result = scrape_nate("nate_c_head_joint_euckr.html")
    assert result["journalist"] == "한도윤·서지우·김민준 기자"
    assert result["content"].startswith("(서울=예시통신) 한도윤 서지우 김민준 기자 = ")


# --- 머리·후미 중첩 ----------------------------------------------------------

def test_nate_head_and_tail_same_name_removes_tail_only():
    result = scrape_nate("nate_head_tail_same_euckr.html")
    assert result["journalist"] == "한도윤 기자"
    assert result["content"] == joined(f"[예시스포츠 한도윤 기자] {P1}", P2, "ⓒ 예시스포츠")
    assert "한도윤 기자 han@example-news.co.kr" not in result["content"]


def test_nate_head_and_tail_conflict_leaves_everything_untouched():
    """두 경로가 다른 이름을 주면 자동으로 고르지 않는다 — 미확인이고 본문도 그대로다."""
    before = joined(f"[예시스포츠 한도윤 기자] {P1}", P2,
                    "서지우 기자 seo@example-news.co.kr", "ⓒ 예시스포츠")
    result = scrape_nate("nate_head_tail_conflict_euckr.html")
    assert result["journalist"] == "미확인"
    assert result["content"] == before
    # 두 후보 줄이 모두 남아 있어야 시민이 직접 판단할 수 있다.
    assert "[예시스포츠 한도윤 기자]" in result["content"]
    assert "서지우 기자 seo@example-news.co.kr" in result["content"]


# --- 안전장치 ---------------------------------------------------------------

def test_nate_photo_caption_reporter_is_not_extracted():
    """캡션에만 'OOO 기자'가 있는 기사는 미확인이어야 한다(사진기자 오인 방지)."""
    result = scrape_nate("nate_caption_reporter_euckr.html")
    assert result["journalist"] == "미확인"
    assert "홍효식" not in result["journalist"]
    assert result["content"] == joined(P1, P2, "ⓒ 예시통신")


def test_nate_unknown_journalist_keeps_content_identical():
    """추출 실패 시 본문을 건드리지 않는다 — 시민이 수동으로 채울 근거를 남긴다."""
    before = joined(P1, P2, "ⓒ 예시일보, 무단 전재 및 재배포 금지")
    result = scrape_nate("nate_no_byline_euckr.html")
    assert result["journalist"] == "미확인"
    assert result["content"] == before


def test_nate_plain_last_line_byline_still_works():
    """프리픽스 없이 마지막 줄이 바이라인인 기존 성공 경로가 계속 동작해야 한다."""
    result = scrape_nate("nate_byline_plain_euckr.html")
    assert result["journalist"] == "김민준 기자"
    # 제거 후에도 길이 게이트를 넘으므로 정상 제거 경로를 탄다(가드는 별도 테스트).
    assert result["content"] == joined(P1, P2, P3)
    assert len(result["content"].strip()) >= MIN_CONTENT_CHARS


def test_nate_short_article_keeps_byline_line_to_stay_above_gate():
    """제거하면 길이 게이트 미달이 되는 짧은 기사는 제거를 취소한다.

    기자명을 얻는 대가로 기사 전체가 ARTICLE_NOT_FOUND 가 되면 남는 것이 없다.
    """
    before = joined(SHORT, "김민준 기자 minjun@example-news.co.kr")
    assert len(before.strip()) >= MIN_CONTENT_CHARS          # 제거 전에는 적격이고
    assert len(SHORT.strip()) < MIN_CONTENT_CHARS            # 제거하면 미달이 되는 fixture

    result = scrape_nate("nate_short_article_guard_euckr.html")
    assert result["journalist"] == "김민준 기자"              # 기자명은 그대로 얻고
    assert result["content"] == before                       # 본문은 제거 전과 완전 동일
    assert len(result["content"].strip()) >= MIN_CONTENT_CHARS


def test_nate_name_email_line_is_skipped_not_read():
    """직함 없는 '이름 이메일' 줄에서는 이름을 읽지 않고 건너뛰기만 한다."""
    result = scrape_nate("nate_s6_skip_to_byline_euckr.html")
    # 마지막 줄의 '서지우'가 아니라, 그 위의 명시적 '김민준 기자'를 읽어야 한다.
    assert result["journalist"] == "김민준 기자"
    assert "서지우" not in result["journalist"]
    assert result["content"] == joined(
        P1, P2, "ⓒ 예시일보, 무단 전재 및 재배포 금지", "서지우 seo@example-news.co.kr")
    # 건너뛴 줄은 본문에 남고, 추출에 쓴 줄만 빠진다.
    assert "김민준 기자" not in result["content"]
    assert "서지우 seo@example-news.co.kr" in result["content"]


def test_nate_head_h2_requires_exact_publisher():
    result = scrape_nate("nate_c_head_h2_euckr.html")
    assert result["journalist"] == "나은정 기자"
    assert result["content"] == joined(f"[예시경제=나은정 기자] {P1}", P2, "ⓒ 예시경제")


def test_nate_head_h3_requires_separator():
    """'[매체이름 기자]' 무구분자 형태는 읽지 않는다(H3 문법이 구분자를 요구한다)."""
    before = joined(f"[예시스포츠한도윤 기자] {P1}", P2, "ⓒ 예시스포츠")
    result = scrape_nate("nate_h3_no_separator_euckr.html")
    assert result["journalist"] == "미확인"
    assert result["content"] == before


def test_nate_head_dateline_on_second_logical_line():
    """첫 줄이 안내 문장이고 둘째 줄에 dateline 이 오는 실측 형태."""
    result = scrape_nate("nate_head_second_line_euckr.html")
    assert result["journalist"] == "한도윤 기자"
    assert result["content"] == joined(
        NOTICE, f"[서울=예시통신] 한도윤 기자 = {P1}", P2, "ⓒ 예시통신")


def test_nate_head_dateline_wrong_publisher_is_ignored():
    """dateline 의 매체 토큰이 publisher 와 다르면 읽지 않는다."""
    before = joined(f"[다른매체=한도윤 기자] {P1}", P2, "ⓒ 예시통신")
    result = scrape_nate("nate_head_wrong_publisher_euckr.html")
    assert result["journalist"] == "미확인"
    assert result["content"] == before


def test_nate_head_english_media_key_is_not_read():
    """'[mdtoday = 최민석 기자]' 류 영문 매체키(H4)는 이번 구현에서 제외한다.

    publisher 와 대조할 수 없어 1건을 위해 매체 특수 분기를 두게 되기 때문이다.
    """
    before = joined(f"[mdtoday = 최민석 기자] {P1}", P2, "ⓒ 메디컬투데이")
    result = scrape_nate("nate_head_h4_english_key_euckr.html")
    assert result["journalist"] == "미확인"
    assert result["content"] == before


def test_nate_charset_header_and_charsetless_agree():
    """실제 네이트 응답 헤더(charset=euc-kr)와 charset 없는 헤더가 같은 결과를 낸다."""
    with_charset = scrape_nate("nate_a_prefix_euckr.html", content_type="text/html; charset=euc-kr")
    without = scrape_nate("nate_a_prefix_euckr.html", content_type="text/html")
    assert with_charset == without
    assert "�" not in with_charset["content"]
