# backend/scraper.py

import requests
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
import re
import json
import copy
import html as html_mod
from datetime import datetime
from typing import Dict, Optional, List, Union

class ArticleScraper:
    """
    기사 URL에서 제목과 본문을 추출하는 스크래퍼

    주요 언론사 지원:
    - 네이버 뉴스
    - 다음 뉴스
    - 주요 언론사 직접 URL
    - 경제지 (13개사)
    """

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape(self, url: str) -> Dict[str, str]:
        """
        URL에서 기사 추출

        Args:
            url: 기사 URL

        Returns:
            dict: {
                "title": 기사 제목,
                "content": 기사 본문,
                "url": 원본 URL,
                "publisher": 언론사명,
                "publish_date": 게재일,
                "journalist": 기자명
            }

        Raises:
            ValueError: 스크래핑 실패 시
        """
        try:
            # URL 유효성 검증
            if not url or not url.startswith('http'):
                # http/https가 없는 경우 추가 (기본적으로 https 가정)
                if url:
                    url = 'https://' + url
                else:
                    raise ValueError("유효하지 않은 URL입니다.")

            # 페이지 가져오기
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # [PR1] fetch 이후 단계(인코딩 판별 → soup → 매체별 분기)를 _parse_response로 분리.
            #       parse_url·original_url에 모두 입력 url을 넘겨 기존 동작을 그대로 보존한다.
            return self._parse_response(response, parse_url=url, original_url=url)

        except requests.RequestException as e:
            raise ValueError(f"기사를 가져올 수 없습니다: {str(e)}")
        except Exception as e:
            raise ValueError(f"기사 파싱 중 오류 발생: {str(e)}")

    def _parse_response(self, response, parse_url: str, original_url: str) -> Dict[str, str]:
        """fetch를 마친 응답을 기사 dict로 변환한다 (scrape()에서 분리한 단계).

        Args:
            response: 이미 받아 둔 응답 객체. 기존 인코딩 로직이 그대로 동작하도록
                `encoding`·`apparent_encoding`·`text`를 제공해야 한다.
            parse_url: 인코딩·매체별 파서 분기의 기준 URL.
                scrape()는 입력 URL을, /extract는 검증된 리디렉션 최종 URL을 넘긴다.
            original_url: 반환 dict의 "url" 값으로 쓸 원 요청 URL.
        """
        # 인코딩 처리
        if any(domain in parse_url for domain in ['news.nate.com', 'kmib.co.kr']):
            response.encoding = 'euc-kr'
        elif any(domain in parse_url for domain in ['seoul.co.kr', 'hankookilbo.com', 'munhwa.com', 'segye.com', 'khan.co.kr', 'naeil.com', 'asiatoday.co.kr', 'edaily.co.kr', 'ekn.kr', 'asiae.co.kr', 'sedaily.com', 'viva100.com', 'mk.co.kr', 'dnews.co.kr', 'biz.heraldcorp.com', 'fnnews.com', 'etoday.co.kr']):
            response.encoding = 'utf-8'
        elif response.encoding == 'ISO-8859-1':
            # 헤더에 charset이 없어서 기본값(ISO-8859-1)으로 설정된 경우, 내용 기반 추측 사용
            response.encoding = response.apparent_encoding

        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')

        article = self._dispatch_parser(soup, parse_url)
        article["url"] = original_url
        return article

    def _dispatch_parser(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """URL 도메인에 따라 매체별 파서를 고른다 (scrape()에서 그대로 옮긴 분기)."""
        # 네이버 연예 — 'news.naver.com' 판별에 걸리지 않아 generic 으로 떨어지던 호스트.
        # 이번에 실패가 확인된 이 호스트만 대상으로 한다(sports 등은 확인되지 않았다).
        if 'entertain.naver.com' in url:
            return self._scrape_naver_entertain(soup, url)
        # 네이버 뉴스 감지
        elif 'news.naver.com' in url:
            return self._scrape_naver(soup, url)
        # 다음 뉴스 감지
        elif 'news.daum.net' in url or 'v.daum.net' in url:
            return self._scrape_daum(soup, url)
        # 네이트 뉴스 감지
        elif 'news.nate.com' in url:
            return self._scrape_nate(soup, url)
        # 줌 뉴스 감지
        elif 'news.zum.com' in url:
            return self._scrape_zum(soup, url)
        # 통신사 직접 URL
        elif 'yna.co.kr' in url:
            return self._scrape_yonhap(soup, url)
        elif 'newsis.com' in url:
            return self._scrape_newsis(soup, url)
        elif 'news1.kr' in url:
            return self._scrape_news1(soup, url)
        elif 'newspim.com' in url:
            return self._scrape_newspim(soup, url)
        # 중앙일간지 직접 URL
        elif 'khan.co.kr' in url:
            return self._scrape_khan(soup, url)
        elif 'kmib.co.kr' in url:
            return self._scrape_kmib(soup, url)
        elif 'naeil.com' in url:
            return self._scrape_naeil(soup, url)
        elif 'donga.com' in url:
            return self._scrape_donga(soup, url)
        elif 'munhwa.com' in url:
            return self._scrape_munhwa(soup, url)
        elif 'metroseoul.co.kr' in url:
            # 'seoul.co.kr' 을 부분 문자열로 포함해 서울신문 파서로 잘못 가던 도메인.
            # 반드시 seoul.co.kr 분기보다 앞에 둔다.
            return self._scrape_metro(soup, url)
        elif 'seoul.co.kr' in url:
            return self._scrape_seoul(soup, url)
        elif 'segye.com' in url:
            return self._scrape_segye(soup, url)
        elif 'asiatoday.co.kr' in url:
            return self._scrape_asiatoday(soup, url)
        elif 'chosun.com' in url:
            return self._scrape_chosun(soup, url)
        elif 'joongang.co.kr' in url:
            return self._scrape_joongang(soup, url)
        elif 'hani.co.kr' in url:
            return self._scrape_hani(soup, url)
        elif 'hankookilbo.com' in url:
            return self._scrape_hankook(soup, url)
        # 경제지
        elif 'edaily.co.kr' in url:
            return self._scrape_edaily(soup, url)
        elif 'ekn.kr' in url:
            return self._scrape_ekn(soup, url)
        elif 'asiae.co.kr' in url:
            return self._scrape_asiae(soup, url)
        elif 'sedaily.com' in url:
            return self._scrape_sedaily(soup, url)
        elif 'viva100.com' in url:
            return self._scrape_viva100(soup, url)
        elif 'mk.co.kr' in url:
            return self._scrape_mk(soup, url)
        elif 'hankyung.com' in url:
            return self._scrape_hankyung(soup, url)
        elif 'dnews.co.kr' in url:
            return self._scrape_dnews(soup, url)
        elif 'biz.heraldcorp.com' in url:
            return self._scrape_herald(soup, url)
        elif 'fnnews.com' in url:
            return self._scrape_fnnews(soup, url)
        elif 'etoday.co.kr' in url:
            return self._scrape_etoday(soup, url)
        # 전문지
        elif 'dt.co.kr' in url:
            return self._scrape_dt(soup, url)
        elif 'mediatoday.co.kr' in url:
            return self._scrape_mediatoday(soup, url)
        elif 'mediaus.co.kr' in url:
            return self._scrape_mediaus(soup, url)
        elif 'journalist.or.kr' in url:
            return self._scrape_journalist_kr(soup, url)
        # 인터넷신문
        elif 'pennmike.com' in url:
            return self._scrape_pennmike(soup, url)
        elif 'pressian.com' in url:
            return self._scrape_pressian(soup, url)
        elif 'mindlenews.com' in url:
            return self._scrape_mindle(soup, url)
        elif 'ohmynews.com' in url:
            return self._scrape_ohmynews(soup, url)
        elif 'dailian.co.kr' in url:
            return self._scrape_dailian(soup, url)
        elif 'mediapen.com' in url:
            return self._scrape_mediapen(soup, url)
        elif 'newdaily.co.kr' in url:
            return self._scrape_newdaily(soup, url)

        # 지역일반 (NDSoft 기반)
        elif any(x in url for x in ['kado.net', 'jbnews.com', 'ccdailynews.com', 'hidomin.com', 'idomin.com', 'kihoilbo.co.kr', 'incheonilbo.com', 'kyongbuk.co.kr', 'daejonilbo.com', 'idaegu.com', 'jnilbo.com', 'jejudomin.co.kr']):
            publisher_map = {
                'kado.net': '강원도민일보', 'jbnews.com': '중부매일', 'ccdailynews.com': '충청일보',
                'hidomin.com': '경북도민일보', 'idomin.com': '경남도민일보', 'kihoilbo.co.kr': '기호일보',
                'incheonilbo.com': '인천일보', 'kyongbuk.co.kr': '경북일보', 'daejonilbo.com': '대전일보',
                'idaegu.com': '대구일보', 'jnilbo.com': '전남일보', 'jejudomin.co.kr': '제주도민일보'
            }
            publisher = next((v for k, v in publisher_map.items() if k in url), "지역언론")
            return self._scrape_ndsoft_generic(soup, url, publisher)

        # 지역일반 (개별 구현)
        elif 'imaeil.com' in url:
            return self._scrape_imaeil(soup, url)
        elif 'yeongnam.com' in url:
            return self._scrape_yeongnam(soup, url)
        elif 'kgnews.co.kr' in url:
            return self._scrape_kgnews(soup, url)
        elif 'kyeonggi.com' in url:
            return self._scrape_kyeonggi(soup, url)
        elif 'busan.com' in url:
            return self._scrape_busan(soup, url)
        elif 'kookje.co.kr' in url:
            return self._scrape_kookje(soup, url)
        elif 'kwnews.co.kr' in url:
            return self._scrape_kwnews(soup, url)
        # 일반 뉴스 사이트
        else:
            return self._scrape_generic(soup, url)

    def _scrape_naver(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """네이버 뉴스 스크래핑"""
        title_elem = soup.select_one('#title_area span, #articleTitle, .media_end_head_headline')
        if not title_elem:
            title_elem = soup.find('h2', class_='media_end_head_headline') or soup.find('h3', id='articleTitle')

        content_elem = soup.select_one('#dic_area, #articleBodyContents, .newsct_article, article')
        if not content_elem:
            content_elem = soup.find('div', id='articeBody') or soup.find('div', class_='article_body')

        if not title_elem or not content_elem:
            raise ValueError("네이버 뉴스 형식을 파싱할 수 없습니다.")

        title = self._clean_inline(title_elem.get_text())

        publisher = "미확인"
        publisher_elem = soup.select_one('.media_end_head_top_logo img')
        if publisher_elem and publisher_elem.get('alt'):
            publisher = publisher_elem.get('alt')

        publish_date = "미확인"
        date_elem = soup.select_one('.media_end_head_info_datestamp_time')
        if date_elem:
            publish_date = self._clean_inline(date_elem.get_text())

        # 기자: 네이버가 제공하는 바이라인 영역만 본다.
        journalist = "미확인"
        journalist_elem = (soup.select_one('.media_end_head_journalist_name')
                           or soup.select_one('.media_end_head_journalist_box em'))
        if journalist_elem:
            journalist = self._normalize_journalist(
                [self._clean_inline(journalist_elem.get_text())], publisher)
        if journalist == "미확인":
            journalist = self._extract_journalist(soup, publisher=publisher)

        # 부제(strong.media_end_summary)는 본문 위에 한 덩어리로 따로 붙인다.
        # 본문 안에 두면 첫 문단과 붙어 버려 어디까지가 부제인지 알 수 없다.
        subtitle = self._block_text(content_elem.select_one('strong.media_end_summary'))

        # 사진 캡션(.end_photo_org)·기자 박스·광고는 본문에서 뺀다.
        # 본문 문단은 <br><br> 과 직접 text node 로 이루어져 있고 소제목은 <h3> 다.
        drops = (
            'script', 'style', 'table',
            'strong.media_end_summary', '.end_photo_org', 'em.img_desc',
            '.media_end_head_journalist_box', '.ad', '.copyright', '.reporter',
            '.artical-btm', '.media_end_linked_more', '.promotion',
            '.vod_player_wrap', '.nbd_table',
        )
        body = self._block_text(content_elem, drops)
        content = ("%s\n\n%s" % (subtitle, body)).strip() if subtitle else body

        if not content:
            raise ValueError("네이버 뉴스 본문을 찾을 수 없습니다.")

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_daum(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """다음 뉴스 스크래핑"""
        # 제목 추출 (og:title 우선)
        title = ""
        og_title = soup.find('meta', property='og:title')

        if og_title:
            title = og_title.get('content', '')
        
        if not title:
            title_elem = soup.select_one('.head_view h3.tit_view') or soup.select_one('h3.tit_view')
            if title_elem:
                title = self._clean_inline(title_elem.get_text())
        
        if not title:
             raise ValueError("다음 뉴스 제목을 찾을 수 없습니다.")

        # 본문 추출
        content_elem = soup.select_one('div.article_view') or soup.select_one('section[dmcf-sid]')
        if not content_elem:
            raise ValueError("다음 뉴스 본문을 찾을 수 없습니다.")

        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, .link_news, .box_europe, .recomm_vod, .btn_relation'):
            tag.decompose()

        content = self._block_text(content_elem)

        # 매체명 추출
        publisher = "Daum" # Fallback
        
        # 1. og:article:author
        og_author = soup.find('meta', property='og:article:author')
        if og_author:
            publisher = og_author.get('content', '')
        
        # 2. #kakaoServiceLogo (상단 로고)
        if not publisher or publisher == "Daum":
            logo_elem = soup.select_one('#kakaoServiceLogo')
            if logo_elem:
                publisher = logo_elem.get_text(strip=True)

        # 기자명 추출
        journalist = "미확인"
        # .info_view .txt_info 중 날짜(.num_date)가 없는 것이 기자명
        info_view = soup.select_one('.info_view')
        if info_view:
            for txt_info in info_view.select('.txt_info'):
                if not txt_info.select('.num_date'):
                    name = txt_info.get_text(strip=True)
                    if name:
                        journalist = name + " 기자"
                        break
        
        # 게재일 추출
        publish_date = "미확인"
        date_elem = soup.select_one('.num_date')
        if date_elem:
            publish_date = date_elem.get_text(strip=True)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_nate(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """네이트 뉴스 스크래핑"""
        # 제목 추출 - og:title 메타 태그 또는 title 태그
        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            title = title_elem.get('content', '')
            # " : 네이트 뉴스" 제거
            title = title.replace(' : 네이트 뉴스', '').strip()
        else:
            title_elem = soup.find('title')
            if title_elem:
                title = self._clean_inline(title_elem.get_text())
                title = title.replace(' : 네이트 뉴스', '').strip()
            else:
                raise ValueError("네이트 뉴스 제목을 찾을 수 없습니다.")
        
        # 네이트는 다른 언론사 기사를 싣는 포털이다. 원매체를 읽어야 한다.
        publisher = "미확인"
        medium_elem = soup.select_one('a.medium') or soup.select_one('.medium')
        if medium_elem:
            publisher = self._clean_inline(medium_elem.get_text()) or "미확인"

        # 게재일: '기사전송'(발행)만 쓴다. '최종수정'(.lastDate)으로 대체하지 않는다.
        publish_date = "미확인"
        date_elem = soup.select_one('span.firstDate')
        if date_elem:
            publish_date = self._clean_inline(date_elem.get_text()).replace('기사전송', '').strip()
        if not publish_date:
            publish_date = "미확인"

        # 본문 추출
        content_elem = soup.select_one('#realArtcContents')
        
        if not content_elem:
            raise ValueError("네이트 뉴스 본문을 찾을 수 없습니다.")

        # 사진 캡션 상자는 클래스가 없는 직계 div 안에 들어 있어 셀렉터로 집을 수 없다.
        for child in list(content_elem.find_all('div', recursive=False)):
            if child.find(class_='articleMedia'):
                child.decompose()

        # 하단 링크 모음 등 불필요한 p 태그 제거
        for p in content_elem.select('p'):
            # 링크가 포함되어 있거나 '인/기/기/사' 같은 텍스트가 있는 경우 제거
            if p.find('a') or '인/기/기/사' in p.get_text():
                p.decompose()

        # 원매체가 붙인 관련기사 목록(#relnews_list)과 자사 홍보 링크를 걷어낸다.
        drops = ('script', 'style', 'iframe', 'figure', 'img',
                 '#relnews_list', 'a', '.ad', '.advertisement', '.relation')
        content = self._block_text(content_elem, drops)
        # 홍보 링크를 감싸던 대괄호만 빈 껍데기로 남는다.
        content = self._clean_text(
            "\n".join(ln for ln in content.split("\n") if ln.strip() not in ("[]", "[ ]")))
        if not content:
            raise ValueError("네이트 뉴스 본문을 찾을 수 없습니다.")

        # 기자: 본문 마지막 줄이 통째로 바이라인인 경우만 읽는다.
        # 본문 전체를 훑어 'OOO 기자'를 줍지 않는다(사진기자 오인 경로).
        journalist = "미확인"
        last_line = content.rstrip().split("\n")[-1].strip()
        if len(last_line) <= 60:
            match = self._BYLINE_LINE_RE.match(last_line)
            if match:
                journalist = self._normalize_journalist(
                    re.split(r'\s*[·,]\s*', match.group(1)), publisher)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_zum(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """줌 뉴스 스크래핑"""
        # 제목 추출 - og:title 메타 태그
        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            title = title_elem.get('content', '')
            # " : zum 뉴스" 제거
            title = title.replace(' : zum 뉴스', '').strip()
        else:
            title_elem = soup.find('title')
            if title_elem:
                title = self._clean_inline(title_elem.get_text())
                title = title.replace(' : zum 뉴스', '').strip()
            else:
                raise ValueError("줌 뉴스 제목을 찾을 수 없습니다.")
        
        # 본문 추출 - article 태그
        content_elem = soup.find('article')
        
        if not content_elem:
            raise ValueError("줌 뉴스 본문을 찾을 수 없습니다.")
        
        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, .advertisement, figure, img'):
            tag.decompose()
        
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url
        }

    def _scrape_yonhap(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """연합뉴스 스크래핑.

        첫 <article>은 AI 가 만든 '세 줄 요약'(article.story-summary)이라 본문이 아니다.
        실제 본문은 div.story-news.article 이다.
        """
        publisher = "연합뉴스"

        title = self._extract_title(soup, 'h1')
        if not title:
            raise ValueError("연합뉴스 제목을 찾을 수 없습니다.")

        # 기자: JSON-LD author → byline 영역 → 기사 첫 문장의 "(서울=연합뉴스) 홍길동 기자 ="
        journalist = self._extract_journalist(soup, selector='.writer-zone01', publisher=publisher)
        if journalist == "미확인":
            head = soup.select_one('div.story-news.article p')
            if head:
                match = re.search(r'=\s*연합뉴스\)\s*((?:[가-힣]{2,4}\s+)*[가-힣]{2,4})\s*기자',
                                  self._clean_inline(head.get_text()))
                if match:
                    journalist = self._normalize_journalist(match.group(1).split(), publisher)

        drops = (
            'script', 'style', 'aside', 'figure',
            '.story-summary', '.writer-zone01', '.comp-box', '.photo-group',
            '.relation-news', '.ad', '.adsbygoogle', '.txt-copyright',
            '.article-func', '.share-wrap', '.tag-zone',
        )
        candidates = []
        for sel in ('div.story-news.article', 'article#articleWrap', 'div.story-news'):
            elem = soup.select_one(sel)
            if elem is not None:
                candidates.append(self._block_text(elem, drops))
        content = self._pick_content(candidates)
        if not content:
            raise ValueError("연합뉴스 본문을 찾을 수 없습니다.")

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": journalist
        }

    def _scrape_newsis(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """뉴시스 스크래핑"""
        # 제목: og:title 또는 h1.tit.title_area
        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            title = title_elem.get('content', '')
        else:
            title_elem = soup.select_one('h1.tit.title_area') or soup.find('h1')
            if not title_elem:
                raise ValueError("뉴시스 제목을 찾을 수 없습니다.")
            title = self._clean_inline(title_elem.get_text())
        
        # 본문: article 태그
        content_elem = soup.find('article')
        if not content_elem:
            raise ValueError("뉴시스 본문을 찾을 수 없습니다.")
        
        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        
        content = self._block_text(content_elem)
        
        # 매체명
        publisher = "뉴시스"
        
        # 기자명: og:description에서 추출 "[서울=뉴시스]홍연우 기자 ="
        journalist = "미확인"
        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc:
            desc_content = og_desc.get('content', '')
            journalist_pattern = re.search(r'\]([가-힣]{2,4})\s*기자', desc_content)
            if journalist_pattern:
                journalist = journalist_pattern.group(1) + " 기자"
        
        # 게재일: article:published_time
        publish_date = "미확인"
        date_elem = soup.select_one('meta[property="article:published_time"]')
        if date_elem:
            publish_date = date_elem.get('content', '미확인')
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_news1(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """뉴스1 스크래핑"""
        # 제목: og:title
        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            title = title_elem.get('content', '')
        else:
            title_elem = soup.find('h1')
            if not title_elem:
                raise ValueError("뉴스1 제목을 찾을 수 없습니다.")
            title = self._clean_inline(title_elem.get_text())
        
        # 본문: article 태그
        content_elem = soup.find('article')
        if not content_elem:
            raise ValueError("뉴스1 본문을 찾을 수 없습니다.")
        
        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        
        content = self._block_text(content_elem)
        
        # 매체명
        publisher = "뉴스1"
        
        # 기자명: 이미지 캡션에서 추출 "ⓒ News1 강민경 기자"
        journalist = "미확인"
        caption = soup.select_one('.img-caption')
        if caption:
            caption_text = caption.get_text()
            journalist_pattern = re.search(r'News1\s*([가-힣]{2,4})\s*기자', caption_text)
            if journalist_pattern:
                journalist = journalist_pattern.group(1) + " 기자"
        
        # 게재일: time#published
        publish_date = "미확인"
        date_elem = soup.select_one('time#published')
        if date_elem:
            publish_date = date_elem.get_text(strip=True)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_newspim(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """뉴스핌 스크래핑"""
        # 제목: og:title
        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            title = title_elem.get('content', '')
        else:
            title_elem = soup.find('h1')
            if not title_elem:
                raise ValueError("뉴스핌 제목을 찾을 수 없습니다.")
            title = self._clean_inline(title_elem.get_text())
        
        # 본문: article 태그 또는 div#news-contents
        # 본문: div#news-contents 우선 검색 후 article 태그 검색
        content_elem = soup.select_one('div#news-contents') or soup.select_one('div.news-con') or soup.find('article')
        
        if not content_elem:
            # 본문이 여러 p 태그로 구성된 경우
            paragraphs = soup.find_all('p')
            if paragraphs:
                content = '\n\n'.join([self._clean_inline(p.get_text()) for p in paragraphs if len(p.get_text().strip()) > 30])
            else:
                raise ValueError("뉴스핌 본문을 찾을 수 없습니다.")
        else:
            # 불필요한 요소 제거
            for tag in content_elem.select('script, style, .ad, figure, img, .relation-news'):
                tag.decompose()
            content = self._block_text(content_elem)
        
        # 매체명
        publisher = "뉴스핌"
        
        # 기자명: og:description에서 추출 "[서울=뉴스핌] 홍석희 기자"
        journalist = "미확인"
        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc:
            desc_content = og_desc.get('content', '')
            journalist_pattern = re.search(r'\]\s*([가-힣]{2,4})\s*기자', desc_content)
            if journalist_pattern:
                journalist = journalist_pattern.group(1) + " 기자"
        
        # 게재일: span#send-time
        publish_date = "미확인"
        date_elem = soup.select_one('span#send-time')
        if date_elem:
            publish_date = date_elem.get_text(strip=True)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_metro(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """메트로신문 스크래핑 (전용 파서 신설).

        metroseoul.co.kr 이 'seoul.co.kr' 을 부분 문자열로 포함해 서울신문 파서로
        분기했고, 서울신문 셀렉터가 맞지 않아 추출이 실패했다.
        """
        publisher = "메트로신문"
        title = self._extract_title(soup, 'h1')
        if not title:
            raise ValueError("메트로신문 제목을 찾을 수 없습니다.")

        drops = ('script', 'style', 'iframe', 'figure', 'img',
                 '.ad', '.banner', '.sns', '.share', '.copyright',
                 '.relation', '.related', '.reporter')
        candidates = []
        for sel in ('div.article-txt-contents', 'div.left-article-txt', 'div.article-content'):
            elem = soup.select_one(sel)
            if elem is not None:
                candidates.append(self._block_text(elem, drops))
        content = self._pick_content(candidates)
        if not content:
            raise ValueError("메트로신문 본문을 찾을 수 없습니다.")

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, publisher=publisher)
        }

    def _scrape_mediapen(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """미디어펜 스크래핑 (전용 파서 신설).

        generic 이 기사 shell(div.article-content)까지 잡아 앞쪽 UI 와 뒤쪽
        관련기사 목록이 본문에 섞였다. 실제 본문은 div#articleBody 다.
        '/편집자주' 로 끝나는 앞머리 단락은 기사 기획·편집 맥락을 설명하는
        분석 재료이므로 지우지 않고 표지로 감싼다.
        """
        publisher = "미디어펜"
        title = self._extract_title(soup, 'h1')
        if not title:
            raise ValueError("미디어펜 제목을 찾을 수 없습니다.")

        body = soup.select_one('div#articleBody') or soup.select_one('div.article-body')
        if body is None:
            raise ValueError("미디어펜 본문을 찾을 수 없습니다.")

        # 클래스가 없는 덩어리라 셀렉터로 집을 수 없다. 직계 자식만 훑어 표시한다.
        for div in body.find_all('div', recursive=False):
            text = div.get_text(" ", strip=True)
            if not text:
                continue
            if text.endswith('/편집자주'):
                div['class'] = (div.get('class') or []) + ['cr-editor-note']
            elif text.startswith('▲'):
                div['class'] = (div.get('class') or []) + ['cr-drop']   # 사진 캡션
            elif text.startswith('▶'):
                div['class'] = (div.get('class') or []) + ['cr-drop']   # 관련기사 목록

        # 바이라인 줄 끝에 붙는 '▶다른기사보기' 링크 라벨만 뺀다(셀렉터로는 못 집는다).
        for anchor in body.find_all('a'):
            if '다른기사보기' in anchor.get_text():
                anchor.decompose()

        drops = ('script', 'style', 'iframe', 'figure', 'img', '.cr-drop',
                 '.ad', '.sns', '.share', '.copyright', '.relation', '.related')
        content = self._block_text(body, drops, (('.cr-editor-note', '편집자주'),))
        if not content:
            raise ValueError("미디어펜 본문을 찾을 수 없습니다.")

        # 부제(div.subtitle)는 본문 컨테이너 바깥에 있어 따로 앞에 붙인다.
        subtitle = self._block_text(soup.select_one('div.subtitle'))
        if subtitle and subtitle not in content:
            content = "%s\n\n%s" % (subtitle, content)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, publisher=publisher)
        }

    def _scrape_naver_entertain(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """네이버 연예 스크래핑 (전용 파서 신설).

        m.entertain.naver.com 은 'news.naver.com' 판별에 걸리지 않아 generic 으로
        떨어졌고 매체·기자·게재일이 모두 비었다. 네이버 연예는 다른 언론사 기사를
        싣는 포털이라 원매체를 읽어야 하는데, 그 표기는 본문 첫머리의
        `[스타뉴스 | 이경호 기자]` 형태로만 존재한다.
        본문 전체를 훑어 'OOO 기자'를 줍지 않는다 — 첫 줄만 본다.
        """
        title = self._extract_title(soup, 'h2')
        if not title:
            raise ValueError("네이버 연예 제목을 찾을 수 없습니다.")

        body = (soup.select_one('div._article_content')
                or soup.select_one('article#comp_news_article'))
        if body is None:
            raise ValueError("네이버 연예 본문을 찾을 수 없습니다.")

        drops = ('script', 'style', 'iframe', 'figure', 'img', 'table',
                 '.end_photo_org', 'em.img_desc', '.ad', '.promotion',
                 '.copyright', '.artical-btm')
        content = self._block_text(body, drops)
        if not content:
            raise ValueError("네이버 연예 본문을 찾을 수 없습니다.")

        publisher, journalist = "미확인", "미확인"
        head_line = content.split("\n", 1)[0].strip()
        match = re.match(r'^\[\s*([^|\]]{2,20}?)\s*[|｜]\s*([가-힣]{2,4})\s*기자\s*\]', head_line)
        if match:
            publisher = match.group(1).strip()
            journalist = self._normalize_journalist([match.group(2)], publisher)
            # 인식에 성공한 그 byline 표기만 본문 첫머리에서 뺀다.
            content = self._clean_text(content[match.end():])

        # 게재일: '입력' 항목만 쓴다. '수정'을 발행일로 대체하지 않는다.
        publish_date = "미확인"
        for item in soup.select('[class*="DateInfo_info_item"]'):
            if '입력' in item.get_text():
                stamp = item.select_one('em')
                if stamp:
                    publish_date = self._clean_inline(stamp.get_text())
                break
        if publish_date == "미확인":
            publish_date = self._extract_publish_date(soup)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_newdaily(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """뉴데일리 스크래핑.

        전용 파서가 없어 generic 으로 떨어지면 첫 <article class="best">, 곧
        '많이 본 기사' 번호 목록을 본문으로 잡았다. 실제 본문은
        div#article_conent(원문 철자 그대로) 안의 li.par 다.
        """
        publisher = "뉴데일리"

        title = self._extract_title(soup, 'h1')
        if not title:
            raise ValueError("뉴데일리 제목을 찾을 수 없습니다.")

        drops = (
            'script', 'style', 'iframe', 'figure', 'img',
            '.center_img', '.ad', '.sns', '.tag_area',
            '.article_relation', '.relation', '.best', '.copyright',
        )
        candidates = []
        for sel in ('div#article_conent', 'div.article-body', 'section.news_zone_01'):
            elem = soup.select_one(sel)
            if elem is not None:
                candidates.append(self._block_text(elem, drops))
        content = self._pick_content(candidates)
        if not content:
            raise ValueError("뉴데일리 본문을 찾을 수 없습니다.")

        # 부제(div.article-subtitle)는 본문 컨테이너 바깥에 있어 따로 앞에 붙인다.
        subtitle = self._block_text(soup.select_one('div.article-subtitle'))
        if subtitle and subtitle not in content:
            content = "%s\n\n%s" % (subtitle, content)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, publisher=publisher)
        }

    def _scrape_generic(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """일반 뉴스 사이트 스크래핑.

        이번 작업에서 재설계하지 않는다. 문단 보존 추출과 노이즈 제거,
        명백한 오추출 시 다음 후보 시도만 적용했다.
        """
        publisher = "미확인"
        og_site = soup.find('meta', property='og:site_name')
        if og_site:
            publisher = og_site.get('content', '미확인')
        elif 'mt.co.kr' in url:
            publisher = "머니투데이"
        elif 'ajunews.com' in url:
            publisher = "아주경제"

        title = self._extract_title(soup, 'h1')
        if not title:
            raise ValueError("기사 제목을 찾을 수 없습니다.")

        drops = (
            'script', 'style', 'iframe', 'nav', 'header', 'footer', 'aside',
            'figure', 'figcaption', '.ad', '.advertisement', '.banner',
            '.copyright', '.relation', '.related', '.reporter', '.byline',
            '.sns', '.share', '.tag', '.comment', '.best', '.ranking',
        )
        candidates: List[str] = []
        seen: List[int] = []
        for elem in (
            soup.find('article'),
            soup.find('div', class_=re.compile(r'article[-_ ]?(body|content|view|text)', re.I)),
            soup.find('div', id=re.compile(r'article[-_ ]?(body|content|view|text)', re.I)),
            soup.find('div', class_=re.compile(r'article|content|body', re.I)),
            soup.find('div', id=re.compile(r'article|content|body', re.I)),
        ):
            if elem is None or id(elem) in seen:
                continue
            seen.append(id(elem))
            candidates.append(self._block_text(elem, drops))

        # 마지막 후보: 페이지의 <p> 모음
        paragraphs = [self._clean_inline(p.get_text()) for p in soup.find_all('p')]
        paragraphs = [p for p in paragraphs if len(p) > 50]
        if paragraphs:
            candidates.append('\n\n'.join(paragraphs))

        content = self._pick_content(candidates)
        if not content:
            raise ValueError("기사 본문을 찾을 수 없습니다.")
        # 기존 계약 유지: 로그인 월처럼 200 이지만 본문이 없는 페이지를 걸러 낸다.
        # extract_api 의 MIN_CONTENT_CHARS 와 같은 기준이라 /extract 응답은 달라지지 않는다.
        # 오추출 판정에는 길이를 쓰지 않는다(_misextraction_reason 참조).
        if len(content) < 100:
            raise ValueError("기사 본문이 너무 짧습니다.")

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, publisher=publisher)
        }

    # ============================================
    # 중앙일간지 12곳 전용 스크래퍼
    # ============================================

    def _scrape_joongang(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """중앙일보 스크래핑"""
        title = self._extract_title(soup, 'h1.headline')
        if not title:
            raise ValueError("중앙일보 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('article') or soup.select_one('div.article_body')
        if not content_elem:
            raise ValueError("중앙일보 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "중앙일보",
            "publish_date": self._extract_publish_date(soup, 'time', 'datetime'),
            "journalist": self._extract_journalist(soup)
        }

    def _scrape_hani(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """한겨레 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("한겨레 제목을 찾을 수 없습니다.")
        
        # <article> 은 shell(빵부스러기·제목·바이라인·오디오·광고)까지 감싼다.
        # 실제 본문은 div.article-text 다.
        content_elem = soup.select_one('div.article-text') or soup.find('article')
        if not content_elem:
            raise ValueError("한겨레 본문을 찾을 수 없습니다.")

        drops = ('script', 'style', 'iframe', 'figure', 'img',
                 '[class*="imageContainer"]', '[class*="BaseAd"]',
                 '[class*="adWrap"]', '.ad', '[class*="Copyright"]',
                 '[class*="relation"]', '[class*="TagSlider"]')
        content = self._block_text(content_elem, drops)

        # JSON-LD·meta 에 datePublished 와 dateModified 가 함께 있다.
        # 발행일은 datePublished 다 — 수정일로 대체하지 않는다(_extract_publish_date 가 그 순서다).
        publish_date = self._extract_publish_date(soup)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "한겨레",
            "publish_date": publish_date,
            "journalist": self._extract_journalist(soup, publisher="한겨레")
        }

    def _scrape_hankyung(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """한국경제 스크래핑"""
        # Title: use og:title or second h1 (first is "경제")
        title = ""
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content', '')
        else:
            h1_tags = soup.find_all('h1')
            if len(h1_tags) > 1:
                title = self._clean_inline(h1_tags[1].get_text())
            elif h1_tags:
                title = self._clean_inline(h1_tags[0].get_text())
        
        if not title or title == "경제":
            raise ValueError("한국경제 제목을 찾을 수 없습니다.")
        
        # Content: use generic scraper logic
        content_elem = None
        for selector in ['article', '[class*="article"]', '[class*="content"]', '[id*="article"]', '[id*="content"]']:
            content_elem = soup.select_one(selector)
            if content_elem and len(content_elem.get_text(strip=True)) > 100:
                break
        
        if not content_elem:
            raise ValueError("한국경제 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "한국경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='.author')
        }

    def _scrape_hankook(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """한국일보 스크래핑.

        본문은 div#article-view-content 다. <article> 태그가 없어 예전 구현은
        페이지 전체의 <p>를 긁어 카피라이트·푸터까지 본문에 넣었다.
        편집자주와 첨부 성명 전문은 분석 자료라서 지우지 않고 표지로 감싼다.
        """
        publisher = "한국일보"

        title = self._extract_title(soup, 'h1.title')
        if not title:
            raise ValueError("한국일보 제목을 찾을 수 없습니다.")
        # og:title 로 떨어졌을 때 붙는 '-사회ㅣ한국일보' 꼬리 제거
        title = re.sub(r'\s*[-ㅣ|]\s*[가-힣]*\s*ㅣ?\s*한국일보\s*$', '', title).strip()

        drops = (
            'script', 'style', 'iframe', 'button', 'figure', 'img',
            '.no-print', '.ad', '.editor-img-box',
            '.module-series', '.guide-notice', '.module-relation',
            '.copyright', '.copy-info', '.txt-copyright',
            '.article-func', '.sns', '.share', '.tag-group', '.reporter-info-wrap',
        )
        # 본문과 구분해 남길 덩어리. 표지는 [ ]·〔 〕·=== 를 쓰지 않는다.
        marked = (
            ('.editor-note', '편집자주'),
            ('.module-stance', '첨부 자료'),
        )
        candidates = []
        for sel in ('div#article-view-content', 'div.article-view', 'div.article-body', 'article'):
            elem = soup.select_one(sel)
            if elem is not None:
                candidates.append(self._block_text(elem, drops, marked))
        content = self._pick_content(candidates)
        if not content:
            raise ValueError("한국일보 본문을 찾을 수 없습니다.")

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(
                soup, selector='div.reporter-info-wrap', publisher=publisher)
        }

    def _scrape_kmib(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """국민일보 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("국민일보 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('article') or soup.select_one('div.article-body')
        if not content_elem:
            raise ValueError("국민일보 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "국민일보",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_seoul(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """서울신문 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("서울신문 제목을 찾을 수 없습니다.")
        
        # <article> 은 shell 까지 감싸 기사 읽어주기·글자크기 UI 와
        # 기사 반응 MBTI·AI 퀴즈가 본문에 섞였다. 실제 본문은 div.viewContent 다.
        content_elem = (soup.select_one('div#articleContent div.viewContent')
                        or soup.select_one('div.viewContent')
                        or soup.find('article')
                        or soup.select_one('div.article_view'))
        if not content_elem:
            raise ValueError("서울신문 본문을 찾을 수 없습니다.")

        # 부제는 <strong> 이라 블록으로 끊기지 않아 뒤 문장과 붙는다.
        # 공통 _BLOCK_TAGS 를 건드리지 않고, 이 파서에서만 블록 태그로 바꿔 준다.
        # 내용은 그대로 두고 태그 이름만 바꾼다.
        for sub in content_elem.select('strong.subTitle_s0'):
            sub.name = 'p'

        # '세줄 요약'은 서울신문 고유의 shell 요소다. 정상 본문과 함께 들어오므로
        # 공통 오추출 규칙(_misextraction_reason)에 넣지 않고 여기서만 걷어낸다.
        drops = ('script', 'style', 'iframe', 'figure', 'img',
                 'section.article-summary-box', '.v_photoarea',
                 '.mixContainer', '.articleCopyright', '.byline',
                 '.ad', '.relation', '.share', '.sns',
                 'div.viewContent > div:not([class])')
        content = self._block_text(content_elem, drops)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "서울신문",
            "publish_date": self._extract_publish_date(soup, 'time'),
            "journalist": self._extract_journalist(soup, selector='.byline', publisher="서울신문")
        }

    def _scrape_asiatoday(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """아시아투데이 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("아시아투데이 제목을 찾을 수 없습니다.")
        
        content_elem = soup.select_one('div.news_bm') or soup.find('article') or soup.select_one('div#articleBody')
        content = ''
        if content_elem:
            for tag in content_elem.select('script, style, .ad, figure, img'):
                tag.decompose()
            content = self._block_text(content_elem)
        
        if not content or len(content) < 100:
            content = self._extract_content_from_paragraphs(soup)
        
        if not content or len(content) < 100:
            raise ValueError("아시아투데이 본문을 찾을 수 없습니다.")
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "아시아투데이",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    # 실패한 6개 언론사
    
    def _scrape_khan(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """경향신문 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("경향신문 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('article') or soup.select_one('div.art_body')
        if not content_elem:
            raise ValueError("경향신문 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "경향신문",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_naeil(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """내일신문 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("내일신문 제목을 찾을 수 없습니다.")
        
        content_elem = soup.select_one('div#article-view-content-div') or soup.find('article')
        content = ''
        if content_elem:
            for tag in content_elem.select('script, style, .ad, figure, img'):
                tag.decompose()
            content = self._block_text(content_elem)
        
        if not content or len(content) < 100:
            content = self._extract_content_from_paragraphs(soup)
        
        if not content or len(content) < 100:
            raise ValueError("내일신문 본문을 찾을 수 없습니다.")
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "내일신문",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_donga(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """동아일보 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("동아일보 제목을 찾을 수 없습니다.")
        
        content_elem = soup.select_one('section.news_view') or soup.select_one('div.article_txt') or soup.find('article')
        content = ''
        if content_elem:
            for tag in content_elem.select('script, style, .ad, figure, img'):
                tag.decompose()
            content = self._block_text(content_elem)
        
        if not content or len(content) < 100:
            content = self._extract_content_from_paragraphs(soup)
        
        if not content or len(content) < 100:
            raise ValueError("동아일보 본문을 찾을 수 없습니다.")
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "동아일보",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_munhwa(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """문화일보 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("문화일보 제목을 찾을 수 없습니다.")
        
        content_elem = soup.select_one('div#NewsAdContent') or soup.find('article')
        content = ''
        if content_elem:
            for tag in content_elem.select('script, style, .ad, figure, img'):
                tag.decompose()
            content = self._block_text(content_elem)
        
        if not content or len(content) < 100:
            content = self._extract_content_from_paragraphs(soup)
        
        if not content or len(content) < 100:
            raise ValueError("문화일보 본문을 찾을 수 없습니다.")
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "문화일보",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_segye(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """세계일보 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("세계일보 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('article') or soup.select_one('div.view_txt')
        if not content_elem:
            raise ValueError("세계일보 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "세계일보",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_chosun(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """조선일보 스크래핑 (JSON 데이터 파싱)"""
        title = ""
        content = ""
        publisher = "조선일보"
        journalist = "미확인"
        publish_date = "미확인"
        
        # 1. JSON 데이터 찾기 (Fusion.globalContent)
        scripts = soup.find_all('script')
        json_data = None
        
        for s in scripts:
            text = s.get_text()
            if 'Fusion.globalContent=' in text:
                match = re.search(r'Fusion\.globalContent=({.*?});', text)
                if match:
                    try:
                        json_data = json.loads(match.group(1))
                        break
                    except:
                        continue
        
        # 2. JSON에서 데이터 추출
        if json_data:
            # 제목
            headlines = json_data.get('headlines', {})
            title = headlines.get('basic', '')
            
            # 본문
            content_elements = json_data.get('content_elements', [])
            body_text = []
            for elem in content_elements:
                if elem.get('type') == 'text':
                    body_text.append(elem.get('content', ''))
            content = '\n\n'.join(body_text)
            
            # 기자명
            credits = json_data.get('credits', {}).get('by', [])
            journalist_list = []
            if credits:
                for credit in credits:
                    # 1. additional_properties.original.byline 확인 (예: "김희래 기자")
                    byline = credit.get('additional_properties', {}).get('original', {}).get('byline')
                    if byline:
                        journalist_list.append(byline)
                    else:
                        # 2. name 확인 (예: "희래 김") - " 기자" 접미사 추가
                        name = credit.get('name')
                        if name:
                            journalist_list.append(f"{name} 기자")
            
            if journalist_list:
                journalist = " ".join(journalist_list)
            
            # 게재일
            publish_date = json_data.get('created_date', '미확인')
            
        # 3. JSON 파싱 실패 시 Fallback (기존 로직)
        if not title:
            title = self._extract_title(soup)
        
        if not content:
            content_elem = soup.select_one('section.article-body') or soup.find('article')
            if content_elem:
                for tag in content_elem.select('script, style, .ad, figure, img'):
                    tag.decompose()
                content = self._block_text(content_elem)
            
            # p 태그 Fallback
            if not content or len(content) < 100:
                content = self._extract_content_from_paragraphs(soup)
        
        if not title:
             raise ValueError("조선일보 제목을 찾을 수 없습니다.")
             
        if not content or len(content) < 100:
            raise ValueError("조선일보 본문을 찾을 수 없습니다.")
            
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _extract_title(self, soup: BeautifulSoup, fallback_selector: str = 'h1') -> str:
        """제목 추출: JSON-LD headline → og:title → fallback_selector.

        JSON-LD 를 먼저 보는 이유는 og:title 에 '-사회ㅣ한국일보' 같은 섹션·매체
        꼬리가 붙는 매체가 있기 때문이다. script 안 값이라 엔티티를 직접 푼다.
        """
        article = self._jsonld_article(soup)
        if article:
            headline = article.get('headline') or article.get('name')
            if isinstance(headline, str) and headline.strip():
                return self._clean_inline(html_mod.unescape(headline))

        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            # og:title 에 &hellip; 처럼 엔티티가 인코딩된 채 들어 있는 매체가 있다.
            return self._clean_inline(html_mod.unescape(title_elem.get('content', '')))

        title_elem = soup.select_one(fallback_selector) or soup.find('h1')
        if title_elem:
            return self._clean_inline(title_elem.get_text())
        return ""

    def _extract_content_from_paragraphs(self, soup: BeautifulSoup, min_content_len: int = 100, min_p_len: int = 30) -> str:
        """본문 추출 헬퍼: p 태그들을 모아서 본문 구성 (Fallback)"""
        paragraphs = soup.find_all('p')
        if paragraphs:
            return '\n\n'.join([self._clean_inline(p.get_text()) for p in paragraphs if len(p.get_text().strip()) > min_p_len])
        return ""

    def _extract_journalist(self, soup: BeautifulSoup, selector: Optional[str] = None,
                            pattern: Optional[str] = None, publisher: Optional[str] = None) -> str:
        """기자명 추출 — JSON-LD → 신뢰할 수 있는 meta → 매체별 byline DOM.

        기사 본문이나 사진 캡션 전체를 훑어 'OOO 기자'를 찾지 않는다.
        그 방식은 인용문 속 인물이나 사진기자 이름을 작성 기자로 둔갑시켰다.
        찾지 못하면 지어내지 말고 '미확인'을 돌려준다 —
        /extract 가 JOURNALIST_NOT_FOUND 경고로 처리한다.
        """
        # 1. JSON-LD author (가장 신뢰할 수 있는 출처)
        name = self._normalize_journalist(
            self._jsonld_author_names(self._jsonld_article(soup)), publisher)
        if name != "미확인":
            return name

        # 2. 메타 태그
        for key in ('author', 'og:article:author', 'article:author', 'dable:author', 'byl'):
            tag = soup.find('meta', property=key) or soup.find('meta', attrs={'name': key})
            if not tag:
                continue
            content = self._clean_inline(tag.get('content', ''))
            if not content:
                continue
            cands = re.findall(r'([가-힣]{2,4})\s*(?:기자|에디터|특파원)', content) or [content]
            name = self._normalize_journalist(cands, publisher)
            if name != "미확인":
                return name

        # 3. 매체별 byline DOM (호출부가 준 선택자를 먼저 본다)
        selectors = ([selector] if selector else []) + list(self._BYLINE_SELECTORS)
        for sel in selectors:
            try:
                elems = soup.select(sel)
            except Exception:
                continue
            for elem in elems[:4]:
                if self._inside_caption(elem):
                    continue
                text = self._clean_inline(elem.get_text(' '))
                # byline 영역은 짧다. 길면 본문 덩어리를 잘못 잡은 것이다.
                if not text or len(text) > 200:
                    continue
                cands: List[str] = []
                if pattern:
                    cands += re.findall(pattern, text)
                cands += re.findall(r'([가-힣]{2,4})\s*(?:기자|에디터|특파원)', text)
                name = self._normalize_journalist(cands, publisher)
                if name != "미확인":
                    return name

        # 4. 줄 전체가 바이라인인 짧은 줄 (클래스 없는 말미 바이라인 대응)
        name = self._normalize_journalist(self._byline_line_names(soup), publisher)
        if name != "미확인":
            return name

        return "미확인"

    def _extract_publish_date(self, soup: BeautifulSoup, selector: Optional[str] = None, attr: Optional[str] = None) -> str:
        """게재일 추출: JSON-LD → meta → selector."""
        article = self._jsonld_article(soup)
        if article:
            for key in ('datePublished', 'dateCreated'):
                value = article.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        for key in ('article:published_time', 'og:article:published_time',
                    'pubdate', 'sailthru.date', 'date'):
            tag = soup.find('meta', property=key) or soup.find('meta', attrs={'name': key})
            if tag:
                value = (tag.get('content') or '').strip()
                if value:
                    return value

        if selector:
            elem = soup.select_one(selector)
            if elem:
                if attr:
                    return elem.get(attr, '미확인')
                return self._clean_inline(elem.get_text())

        return "미확인"

    # ============================================
    # 경제지 스크래퍼
    # ============================================

    def _scrape_edaily(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """이데일리 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("이데일리 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', class_='news_body') or soup.find('div', id='newsContent')
        if not content_elem:
            raise ValueError("이데일리 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img, .news_domino'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "이데일리",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='[class*="reporter"]')
        }

    def _scrape_ekn(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """에너지경제신문 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("에너지경제신문 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', id='news_body_area_contents') or soup.find('div', class_='view-text') or soup.find('div', class_='article_body')
        if not content_elem:
            raise ValueError("에너지경제신문 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "에너지경제신문",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='[class*="reporter"]')
        }

    def _scrape_asiae(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """아시아경제 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("아시아경제 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', class_='txt_area') or soup.find('div', id='txt_area') or soup.find('div', itemprop='articleBody')
        if not content_elem:
             # Fallback to generic article body
             content_elem = soup.find('div', class_='article_view')
        
        if not content_elem:
            raise ValueError("아시아경제 본문을 찾을 수 없습니다.")
        
        # Remove ad related divs
        for tag in content_elem.select('script, style, .ad, figure, img, .art_ad, .google_ad'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "아시아경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_sedaily(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """서울경제 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("서울경제 제목을 찾을 수 없습니다.")
        
        # Try multiple content selectors
        # 셀렉터 노후: 현재 본문은 div#article-body(.view) 다.
        content_elem = (soup.select_one('div#article-body') or
                        soup.select_one('div.article-body') or
                        soup.select_one('div#ttsBody') or
                        soup.find('div', class_='article_body') or
                        soup.find('div', id='article_body') or
                        soup.find('div', class_='article_view') or
                        soup.find('div', id='articleBody'))
        if not content_elem:
            raise ValueError("서울경제 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "서울경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='[class*="reporter"]')
        }

    def _scrape_viva100(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """브릿지경제 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("브릿지경제 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', class_='news_content') or soup.find('div', class_='article_detail_area') or soup.find('div', class_='view_con')
        if not content_elem:
            raise ValueError("브릿지경제 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "브릿지경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_mk(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """매일경제 스크래핑"""
        title = self._extract_title(soup)
        
        # 매일경제는 종종 h1이 없고 news_title_text 클래스 사용
        if not title:
            title_elem = soup.find('h2', class_='news_title_text') or soup.find('div', class_='news_title_text')
            if title_elem:
                title = self._clean_inline(title_elem.get_text())
        
        if not title:
            raise ValueError("매일경제 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', class_='news_cnt_detail_wrap') or soup.find('div', itemprop='articleBody')
        if not content_elem:
             # Fallback
             content_elem = soup.find('div', class_='art_txt')

        if not content_elem:
            raise ValueError("매일경제 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img, .mapping_group'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "매일경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_dnews(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """e대한경제 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("e대한경제 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', class_='newsCont') or soup.find('div', class_='viewCont') or soup.find('div', id='articleBody')
        if not content_elem:
            raise ValueError("e대한경제 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "e대한경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup)
        }

    def _scrape_herald(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """헤럴드경제 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("헤럴드경제 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', id='article_text') or soup.find('article', id='articleText') or soup.find('div', class_='article_view')
        if not content_elem:
            raise ValueError("헤럴드경제 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "헤럴드경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    def _scrape_fnnews(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """파이낸셜뉴스 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("파이낸셜뉴스 제목을 찾을 수 없습니다.")
        
        # 셀렉터 노후: 현재 본문은 div.article-view__body 다.
        content_elem = (soup.select_one('div.article-view__body') or
                        soup.select_one('article.article-view') or
                        soup.find('div', id='article_content') or
                        soup.find('div', class_='article_content'))
        if not content_elem:
            raise ValueError("파이낸셜뉴스 본문을 찾을 수 없습니다.")
        
        # 본문 뒤에 해시태그 상자와 카피라이트가 붙는다(깨진 마크업이라 <br> 아래에 중첩된다).
        drops = ('script', 'style', '.ad', 'figure', 'img',
                 '.article-view__tags', '.article-view_copyright')
        content = self._block_text(content_elem, drops)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "파이낸셜뉴스",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='.writer')
        }

    def _scrape_etoday(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """이투데이 스크래핑"""
        title = self._extract_title(soup)
        if not title:
            raise ValueError("이투데이 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('div', class_='view_contents') or soup.find('div', class_='articleView') or soup.find('div', class_='article_view')
        if not content_elem:
            raise ValueError("이투데이 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "이투데이",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
        }

    # ============================================
    # 전문지/인터넷신문 스크래퍼
    # ============================================

    def _scrape_dt(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """디지털타임스 스크래핑"""
        title = self._extract_title(soup, 'h1.tit')
        if not title:
            raise ValueError("디지털타임스 제목을 찾을 수 없습니다.")
        
        content_elem = soup.select_one('section.article-body') or soup.find('div', class_='article_txt')
        if not content_elem:
            raise ValueError("디지털타임스 본문을 찾을 수 없습니다.")
            
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "디지털타임스",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='.writer')
        }

    def _scrape_mediatoday(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """미디어오늘 스크래핑"""
        return self._scrape_ndsoft_generic(soup, url, "미디어오늘")

    def _scrape_mediaus(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """미디어스 스크래핑"""
        return self._scrape_ndsoft_generic(soup, url, "미디어스")

    def _scrape_journalist_kr(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """기자협회보 스크래핑"""
        # 제목
        title = self._extract_title(soup, '.heading')
        
        # 본문
        content_elem = soup.select_one('#article_view') or soup.find('div', class_='article_view')
        if content_elem:
           for tag in content_elem.select('script, style, .ad, figure, img'):
               tag.decompose()
           content = self._block_text(content_elem)
        else:
           # Fallback to generic
           return self._scrape_ndsoft_generic(soup, url, "기자협회보")

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "기자협회보",
            "publish_date": self._extract_publish_date(soup, selector='.date_v2'), # Verified selector
            "journalist": self._extract_journalist(soup, selector='.writer') # Verified selector
        }
        
    def _scrape_pennmike(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """펜앤드마이크 스크래핑"""
        return self._scrape_ndsoft_generic(soup, url, "펜앤드마이크")

    def _scrape_pressian(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """프레시안 스크래핑"""
        title = self._extract_title(soup, 'h2')
        if not title:
            raise ValueError("프레시안 제목을 찾을 수 없습니다.")
            
        content_elem = soup.select_one('.article_body') or soup.select_one('#news_body_area')
        if not content_elem:
             raise ValueError("프레시안 본문을 찾을 수 없습니다.")
             
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "프레시안",
            "publish_date": self._extract_publish_date(soup, selector='.date'),
            "journalist": self._extract_journalist(soup, selector='.reporter_name')
        }

    def _scrape_mindle(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """민들레 스크래핑"""
        # _scrape_ndsoft_generic과 유사하지만 기자명 selector를 다르게 설정
        title = self._extract_title(soup, '.heading')
        if not title:
             raise ValueError("민들레 제목을 찾을 수 없습니다.")
        
        content_elem = soup.select_one('#article-view-content-div') or soup.find('div', class_='article-body')
        if not content_elem:
            raise ValueError("민들레 본문을 찾을 수 없습니다.")
            
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "민들레",
            "publish_date": self._extract_publish_date(soup),
            # selector=None으로 하여 메타태그 우선 사용, 실패시 전체 텍스트 검색
            "journalist": self._extract_journalist(soup, selector=None)
        }

    def _scrape_ohmynews(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """오마이뉴스 스크래핑"""
        # 제목
        title = self._extract_title(soup)
        if not title:
            raise ValueError("오마이뉴스 제목을 찾을 수 없습니다.")
            
        # 본문
        content_elem = soup.select_one('.at_contents') or soup.find('div', class_='article_view')
        if not content_elem:
             raise ValueError("오마이뉴스 본문을 찾을 수 없습니다.")
             
        for tag in content_elem.select('script, style, .ad, figure, img, .comment_box'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "오마이뉴스",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup)
        }

    def _scrape_dailian(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """데일리안 스크래핑"""
        # 제목
        title = self._extract_title(soup, 'h1.title')
        if not title:
            raise ValueError("데일리안 제목을 찾을 수 없습니다.")

        # 본문
        content_elem = soup.select_one('div.article') or soup.find('div', class_='news-contents')
        if not content_elem:
            raise ValueError("데일리안 본문을 찾을 수 없습니다.")

        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, img, .contentsBanner, .sh_banner, .article_wing_left, .article_wing_right, .inner-subtitle, .figure'):
            tag.decompose()
        
        content = self._block_text(content_elem)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "데일리안",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='p.reporter')
        }

    def _scrape_imaeil(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """매일신문 스크래핑"""
        return self._scrape_basic(soup, url, "매일신문", 
            title_selector='div.header_article_view h3', 
            content_selector='div.article_content')

    def _scrape_yeongnam(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """영남일보 스크래핑"""
        return self._scrape_basic(soup, url, "영남일보", 
            title_selector='#article-view-content-div h1, .article-news-title', 
            content_selector='.article-news-body')

    def _scrape_kgnews(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """경기신문 스크래핑"""
        return self._scrape_basic(soup, url, "경기신문", 
            title_selector='.article-head-title, .h1', 
            content_selector='#news_body_area')

    def _scrape_kyeonggi(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """경기일보 스크래핑.

        .article_view 는 shell 까지 감싸 '우리동네 소식통'·구글 추천·글자크기·
        태그·카피라이트·댓글 안내가 본문에 섞였다. 실제 본문은 .article_cont_wrap 이다.
        게재일은 shell 의 div.article_date('승인 2025-12-08 18:11')에 있다.
        """
        publisher = "경기일보"
        title = self._extract_title(soup, '.article_head .title')
        if not title:
            raise ValueError("경기일보 제목을 찾을 수 없습니다.")

        content_elem = soup.select_one('div.article_cont_wrap') or soup.select_one('.article_view')
        if not content_elem:
            raise ValueError("경기일보 본문을 찾을 수 없습니다.")

        drops = ('script', 'style', 'input', 'iframe', 'figure', 'img',
                 '.report_box', '.tag_wrap', '.mb30', '.ad', '.center_ad_box01',
                 '.sns', '.share', '.comment')
        content = self._block_text(content_elem, drops)
        if not content:
            raise ValueError("경기일보 본문을 찾을 수 없습니다.")

        publish_date = self._extract_publish_date(soup)
        if publish_date == "미확인":
            date_elem = soup.select_one('div.article_date')
            if date_elem:
                publish_date = self._clean_inline(date_elem.get_text()).replace('승인', '').strip()

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": self._extract_journalist(soup, selector='.report_box', publisher=publisher)
        }

    def _scrape_busan(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """부산일보 스크래핑"""
        return self._scrape_basic(soup, url, "부산일보", 
            title_selector='.title_area h1', 
            content_selector='.article_content')

    def _scrape_kookje(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """국제신문 스크래핑"""
        # 제목
        title = self._extract_title(soup, '.news_title h1')
        if not title:
            raise ValueError("국제신문 제목을 찾을 수 없습니다.")

        # 본문
        content_elem = soup.select_one('.news_article')
        if not content_elem:
             raise ValueError("국제신문 본문을 찾을 수 없습니다.")

        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, img, .caption, table'):
            tag.decompose()
        
        content = self._block_text(content_elem)

        # 기자명
        journalist = "미확인"
        reporter_elem = soup.select_one('li.f_news_repoter')
        if reporter_elem:
            # 텍스트에서 이메일 등 제거하고 이름만 추출
            text = reporter_elem.get_text()
            match = re.search(r'([가-힣]{2,4})\s*기자', text)
            if match:
                journalist = match.group(1) + " 기자"
        
        # 게재일
        publish_date = self._extract_publish_date(soup, '.f_news_date')
        if publish_date:
            # "| 입력 : 2025..." 형식 정리
            publish_date = re.sub(r'[|]|\s*입력\s*:?', '', publish_date).strip()

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "국제신문",
            "publish_date": publish_date,
            "journalist": journalist
        }

    def _scrape_kwnews(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """강원일보 스크래핑. 셀렉터 노후: 현재 본문은 div.post-body-area 다.

        셀렉터를 콤마 그룹으로 넘기면 select_one 이 '문서 순서' 로 골라
        더 바깥의 div#article_view(기사 shell)를 잡는다. 순서대로 하나씩 본다.
        """
        publisher = "강원일보"
        title = self._extract_title(soup, 'div.article_head h2.title')
        if not title:
            raise ValueError("강원일보 제목을 찾을 수 없습니다.")

        content_elem = None
        for sel in ('div.post-body-area', 'div.article_content', 'div#article_view'):
            content_elem = soup.select_one(sel)
            if content_elem is not None:
                break
        if content_elem is None:
            raise ValueError("강원일보 본문을 찾을 수 없습니다.")

        drops = ('script', 'style', 'iframe', 'figure', 'img', '.caption',
                 '.ad', '.date-info', '.sns', '.share', '.copyright',
                 '.relation', '.related', '[class*="reporter"]')
        content = self._block_text(content_elem, drops)
        if not content:
            raise ValueError("강원일보 본문을 찾을 수 없습니다.")

        # 게재일: '입력' 만 쓴다. 같은 상자에 있는 '수정' 으로 대체하지 않는다.
        publish_date = self._extract_publish_date(soup)
        if publish_date == "미확인":
            for box in soup.select('div.date-info'):
                match = re.search(r'입력\s*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2}[^\n]*)', box.get_text("\n"))
                if match:
                    publish_date = self._clean_inline(match.group(1))
                    break

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": publish_date,
            "journalist": self._extract_journalist(soup, publisher=publisher)
        }

    def _scrape_basic(self, soup: BeautifulSoup, url: str, publisher: str, title_selector: str, content_selector: str) -> Dict[str, str]:
        """기본 스크래퍼 패턴"""
        title = self._extract_title(soup, title_selector)
        if not title:
            # Fallback
            title_elem = soup.select_one(title_selector)
            if title_elem: 
                title = self._clean_inline(title_elem.get_text())
            if not title:
                raise ValueError(f"{publisher} 제목을 찾을 수 없습니다.")

        content_elem = soup.select_one(content_selector)
        if not content_elem:
            raise ValueError(f"{publisher} 본문을 찾을 수 없습니다.")

        for tag in content_elem.select('script, style, .ad, figure, img, .caption'):
            tag.decompose()
        
        content = self._block_text(content_elem)

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup)
        }

    def _scrape_ndsoft_generic(self, soup: BeautifulSoup, url: str, publisher: str) -> Dict[str, str]:
        """NDSoft 기반 CMS 공용 스크래퍼"""
        # 제목
        title = self._extract_title(soup, '.heading')
        if not title:
            raise ValueError(f"{publisher} 제목을 찾을 수 없습니다.")
            
        # 본문
        content_elem = (
            soup.select_one('#article-view-content-div') or 
            soup.select_one('.article-body') or
            soup.select_one('#article_view') or
            soup.select_one('.article_view')
        )
        if not content_elem:
            raise ValueError(f"{publisher} 본문을 찾을 수 없습니다.")
            
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._block_text(content_elem)
        
        # 메타데이터
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='ul.art_info li')
        }

    def _clean_text(self, text: str) -> str:
        r"""본문용 정제 — 가로 공백만 정리하고 줄바꿈·문단 경계는 보존한다.

        이전 판은 `\s+`를 공백 하나로 합쳐 문단 구분이 통째로 사라졌고,
        바로 뒤의 줄바꿈 정리 코드는 남은 줄바꿈이 없어 죽은 코드였다.
        문단·소제목 경계는 기사 구조를 읽는 데 필요한 정보라 살린다.
        한 줄이어야 하는 값(제목·날짜 등)은 _clean_inline 을 쓴다.
        """
        if not text:
            return ""
        # 유니코드 공백류만 일반 공백으로 바꾼다. 줄바꿈 문자는 건드리지 않는다.
        for ch in ('\u00a0', '\u2007', '\u202f', '\u3000'):
            text = text.replace(ch, ' ')
        text = text.replace('\u200b', '').replace('\ufeff', '')
        # 가로 공백만 합친다(\n 제외).
        text = re.sub(r'[^\S\n]+', ' ', text)
        # 줄 앞뒤 공백 제거
        text = re.sub(r'[ \t]*\n[ \t]*', '\n', text)
        # 빈 줄이 셋 이상 이어지면 둘로 줄인다(문단 경계 자체는 유지).
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _clean_inline(self, text: str) -> str:
        """제목·날짜·기자명처럼 반드시 한 줄이어야 하는 값 정제."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    # ============================================
    # 구조 보존 본문 추출
    # ============================================

    # 문단 경계를 만드는 블록 태그
    _BLOCK_TAGS = frozenset((
        'p', 'div', 'section', 'article', 'aside', 'header', 'footer', 'main',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'li', 'ul', 'ol', 'dl', 'dt', 'dd',
        'table', 'thead', 'tbody', 'tr', 'figure', 'figcaption',
        'pre', 'address', 'form', 'hr',
    ))
    # 텍스트를 가져오지 않는 태그
    _SKIP_TAGS = frozenset((
        'script', 'style', 'noscript', 'iframe', 'template',
        'button', 'select', 'option', 'svg', 'canvas', 'video', 'audio',
    ))

    # 본문 안에서 성격이 다른 덩어리를 감싸는 표지.
    # `[ ]`·`〔 〕`는 조립 문자열의 자료 헤딩과 규범 인용 표기에 이미 쓰이므로 피한다.
    # `===` 도 예시 격리 표지와 겹치므로 쓰지 않는다.
    MARK_OPEN = "--- %s ---"
    MARK_CLOSE = "--- %s 끝 ---"

    def _collect_text(self, node, out: List[str]) -> None:
        """DOM 을 걸으며 문단·줄바꿈 경계를 살린 텍스트 조각을 모은다.

        - 블록 태그는 앞뒤에 빈 줄을 넣어 문단으로 끊는다
        - <br> 은 줄바꿈 하나. <br><br> 이면 자연히 문단 경계가 된다
        - 태그에 감싸이지 않은 직접 text node 도 빠뜨리지 않는다
        - HTML 주석은 건너뛴다(Comment 가 NavigableString 의 하위형이라 먼저 걸러야 한다)
        """
        for child in node.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                s = str(child)
                if s.strip():
                    out.append(s)
                elif s:
                    out.append(' ')
                continue
            if not isinstance(child, Tag):
                continue
            if child.name in self._SKIP_TAGS:
                continue
            if child.name == 'br':
                out.append('\n')
                # 깨진 HTML 에서 html.parser 가 <br> 아래에 본문을 자식으로 넣는 경우가
                # 있다(기자협회보). 빈 <br> 은 지금까지처럼 줄바꿈 하나로 끝내고,
                # 자식이 실제로 있을 때만 그 텍스트를 이어서 모은다.
                if child.contents:
                    self._collect_text(child, out)
                continue
            if child.name in self._BLOCK_TAGS:
                out.append('\n\n')
                self._collect_text(child, out)
                out.append('\n\n')
            else:
                self._collect_text(child, out)

    def _wrap_marked(self, elem, selector: str, label: str) -> None:
        """편집자주·첨부 성명처럼 본문과 구분해 남길 덩어리에 표지를 붙인다."""
        for box in elem.select(selector):
            parts: List[str] = []
            self._collect_text(box, parts)
            inner = self._clean_text(''.join(parts))
            # 표지와 같은 말이 첫 줄에 또 나오면(예: <h3>편집자주</h3>) 중복이라 지운다.
            lines = inner.split('\n')
            if lines and lines[0].strip() == label:
                inner = '\n'.join(lines[1:]).strip()
            if not inner:
                box.decompose()
                continue
            box.replace_with(NavigableString("\n\n%s\n%s\n%s\n\n" % (
                self.MARK_OPEN % label, inner, self.MARK_CLOSE % label)))

    def _block_text(self, elem, drop_selectors=(), marked=()) -> str:
        """본문 컨테이너에서 문단·소제목·줄바꿈을 보존한 텍스트를 만든다.

        원본 soup 을 건드리지 않도록 복사본에서 작업한다. 본문 후보를 여러 개
        시도할 때 앞 후보의 노이즈 제거가 뒤 후보를 훼손하면 안 되기 때문이다.
        """
        if elem is None:
            return ""
        elem = copy.copy(elem)
        for sel in drop_selectors:
            try:
                targets = elem.select(sel)
            except Exception:
                continue
            for tag in targets:
                tag.decompose()
        for sel, label in marked:
            try:
                self._wrap_marked(elem, sel, label)
            except Exception:
                continue
        out: List[str] = []
        self._collect_text(elem, out)
        return self._clean_text(''.join(out))

    # ============================================
    # 명백한 오추출 감지 (점수화하지 않는다)
    # ============================================

    _AI_SUMMARY_MARKS = ("인공지능이 자동으로 줄인", "세 줄 요약", "AI가 요약한", "AI 요약")

    def _misextraction_reason(self, text: str) -> Optional[str]:
        """본문이 아닌 것이 명백하면 이유를, 아니면 None 을 돌려준다.

        길이는 판정 근거로 쓰지 않는다 — 정상적으로 짧은 기사가 있기 때문이다.
        """
        if not text or not text.strip():
            return "본문이 비어 있음"
        t = text.strip()
        if any(m in t for m in self._AI_SUMMARY_MARKS):
            return "AI 자동 요약 안내문이 들어 있는 요약 박스"
        # '01 … 02 … 03 …' 처럼 번호가 붙어 이어지면 관련기사·많이 본 기사 목록이다.
        numbered = [int(n) for n in re.findall(r'(?:^|\s)(0[1-9]|1[0-9]|20)\s+\S', t)]
        if len(numbered) >= 5 and numbered[:3] == [1, 2, 3]:
            return "번호가 매겨진 기사 목록"
        return None

    def _pick_content(self, candidates: List[str]) -> str:
        """본문 후보를 차례로 보고 명백한 오추출이면 다음 후보로 넘어간다.

        정상 후보가 하나도 없으면 빈 문자열을 돌려준다. 호출부는 이를
        ValueError 로 올려 기존 /extract 오류 계약(ARTICLE_NOT_FOUND)을 태운다.
        새 status 값을 만들지 않는다.
        """
        for text in candidates:
            if text and self._misextraction_reason(text) is None:
                return text
        return ""

    # ============================================
    # JSON-LD
    # ============================================

    def _jsonld_objects(self, soup: BeautifulSoup) -> List[dict]:
        objs: List[dict] = []
        for script in soup.find_all('script', type='application/ld+json'):
            raw = script.string or script.get_text() or ''
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                continue
            stack = [data]
            while stack:
                cur = stack.pop()
                if isinstance(cur, list):
                    stack.extend(cur)
                elif isinstance(cur, dict):
                    objs.append(cur)
                    graph = cur.get('@graph')
                    if isinstance(graph, list):
                        stack.extend(graph)
        return objs

    def _jsonld_article(self, soup: BeautifulSoup) -> Optional[dict]:
        """JSON-LD 에서 기사 객체를 찾는다."""
        for obj in self._jsonld_objects(soup):
            raw = obj.get('@type')
            types = raw if isinstance(raw, list) else [raw]
            for t in types:
                if t and str(t).endswith('Article'):
                    return obj
        return None

    def _jsonld_author_names(self, article: Optional[dict]) -> List[str]:
        if not article:
            return []
        raw = article.get('author') or article.get('creator')
        if not raw:
            return []
        items = raw if isinstance(raw, list) else [raw]
        names: List[str] = []
        for item in items:
            if isinstance(item, dict):
                # 언론사(조직)는 기자명이 아니다.
                if str(item.get('@type', '')).lower().endswith('organization'):
                    continue
                name = item.get('name')
            elif isinstance(item, str):
                name = item
            else:
                name = None
            if name:
                names.append(html_mod.unescape(str(name)).strip())
        return names

    # ============================================
    # 기자명 판별
    # ============================================

    # 언론사 이름이 기자명으로 새어 들어오는 것을 막는다.
    _MEDIA_NAME_TAILS = ('일보', '신문', '방송', '뉴스', '데일리', '타임스', '타임즈',
                         '경제', '투데이', '저널', '미디어', '통신', '기자단')
    _NAME_BLACKLIST = (
        '로그인', '구독', '회원가입', '팔로우', '스크랩',
        '칼럼', '기획', '특집', '연재', '인터뷰',
        '뉴스레터', '이메일', '페이스북', '트위터', '카카오',
        '스타', '견습', '경력', '모집', '전체', '사진', '영상', '편집',
    )

    def _is_person_name(self, name: str, publisher: Optional[str] = None) -> bool:
        if not name:
            return False
        if not re.fullmatch(r'[가-힣]{2,4}', name):
            return False
        if publisher and (name in publisher or publisher in name):
            return False
        if any(name.endswith(tail) for tail in self._MEDIA_NAME_TAILS):
            return False
        for bad in self._NAME_BLACKLIST:
            if bad in name or name in bad:
                return False
        return True

    def _normalize_journalist(self, names, publisher: Optional[str] = None) -> str:
        """이름 후보들을 'OOO 기자' 한 줄로 만든다. 공동 바이라인은 가운뎃점으로 잇는다."""
        cleaned: List[str] = []
        for raw in names or []:
            name = self._clean_inline(str(raw))
            name = re.sub(r'\s*(기자|에디터|특파원|논설위원|선임기자|전문기자)\s*$', '', name).strip()
            if self._is_person_name(name, publisher) and name not in cleaned:
                cleaned.append(name)
        if not cleaned:
            return "미확인"
        return '·'.join(cleaned) + " 기자"

    # byline 으로 볼 수 있는 좁은 영역. 본문·사진 캡션 전체를 훑지 않기 위한 한정이다.
    _BYLINE_SELECTORS = (
        '.reporter-info-wrap', '.reporter', '.byline', '.byline-name',
        '.writer', '.write', '.art_writer', '.author', '.journalist',
        '.news_writer', '.writer-zone01',
        '[class*="byline"]', '[class*="reporter"]', '[class*="writer"]',
        '[id*="byline"]', '[id*="reporter"]', '[id*="writer"]',
    )

    # 그 줄 자체가 바이라인인 경우만 받는다.
    # "김민준 기자 minjun@example-news.co.kr" 처럼 이름+직함으로 시작하는 짧은 줄.
    # 본문 문장이나 사진 캡션은 이 모양이 될 수 없다.
    _BYLINE_LINE_RE = re.compile(
        r'^([가-힣]{2,4}(?:\s*[·,]\s*[가-힣]{2,4})*)\s*(?:기자|에디터|특파원)\b')

    def _byline_line_names(self, soup: BeautifulSoup) -> List[str]:
        """줄 전체가 바이라인인 짧은 요소에서만 이름을 읽는다.

        본문·캡션 전체를 훑는 것과 다르다. 인용문 속 '홍길동 기자가 말했다' 같은
        문장은 줄 시작이 이름이어도 길이가 길어 걸리지 않고, 사진 캡션은
        _inside_caption 으로 걸러진다.
        """
        for elem in soup.find_all(['p', 'div', 'span', 'address', 'em', 'strong']):
            if self._inside_caption(elem):
                continue
            text = self._clean_inline(elem.get_text(' '))
            # 바이라인 줄은 짧다. 이메일이 붙는 정도까지만 허용한다.
            if not text or len(text) > 60:
                continue
            match = self._BYLINE_LINE_RE.match(text)
            if not match:
                continue
            # 이름과 직함 뒤에 남는 것은 이메일·매체명 정도여야 한다.
            tail = text[match.end():].strip()
            if tail and not re.fullmatch(r'[\w.+-]+@[\w.-]+|[=·\-—,\s]*[\w.+-]*@?[\w.-]*', tail):
                continue
            return re.split(r'\s*[·,]\s*', match.group(1))
        return []

    def _inside_caption(self, elem) -> bool:
        """사진 캡션·이미지 상자 안에 있는 요소인지."""
        node = elem
        for _ in range(6):
            if node is None or not isinstance(node, Tag):
                return False
            if node.name in ('figure', 'figcaption'):
                return True
            cls = ' '.join(node.get('class') or [])
            if any(k in cls for k in ('photo', 'caption', 'img', 'comp-box', 'center_img')):
                return True
            node = node.parent
        return False
