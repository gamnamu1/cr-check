# backend/scraper.py

import requests
from bs4 import BeautifulSoup
import re
import json
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
            
            # 인코딩 처리
            if any(domain in url for domain in ['news.nate.com', 'kmib.co.kr']):
                response.encoding = 'euc-kr'
            elif any(domain in url for domain in ['seoul.co.kr', 'hankookilbo.com', 'munhwa.com', 'segye.com', 'khan.co.kr', 'naeil.com', 'asiatoday.co.kr', 'edaily.co.kr', 'ekn.kr', 'asiae.co.kr', 'sedaily.com', 'viva100.com', 'mk.co.kr', 'dnews.co.kr', 'biz.heraldcorp.com', 'fnnews.com', 'etoday.co.kr']):
                response.encoding = 'utf-8'
            elif response.encoding == 'ISO-8859-1':
                # 헤더에 charset이 없어서 기본값(ISO-8859-1)으로 설정된 경우, 내용 기반 추측 사용
                response.encoding = response.apparent_encoding

            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')

            # 네이버 뉴스 감지
            if 'news.naver.com' in url:
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

        except requests.RequestException as e:
            raise ValueError(f"기사를 가져올 수 없습니다: {str(e)}")
        except Exception as e:
            raise ValueError(f"기사 파싱 중 오류 발생: {str(e)}")

    def _scrape_naver(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """네이버 뉴스 스크래핑"""
        # 제목 추출
        title_elem = soup.select_one('#title_area span, #articleTitle, .media_end_head_headline')
        if not title_elem:
            title_elem = soup.find('h2', class_='media_end_head_headline') or soup.find('h3', id='articleTitle')

        # 본문 추출
        content_elem = soup.select_one('#dic_area, #articleBodyContents, .newsct_article, article')
        if not content_elem:
            content_elem = soup.find('div', id='articeBody') or soup.find('div', class_='article_body')

        if not title_elem or not content_elem:
            raise ValueError("네이버 뉴스 형식을 파싱할 수 없습니다.")

        # 텍스트 정제
        title = self._clean_text(title_elem.get_text())

        # 메타데이터 추출 (Publisher, Date, Journalist)
        publisher = "미확인"
        publisher_elem = soup.select_one('.media_end_head_top_logo img')
        if publisher_elem and publisher_elem.get('alt'):
            publisher = publisher_elem.get('alt')
        
        publish_date = "미확인"
        date_elem = soup.select_one('.media_end_head_info_datestamp_time')
        if date_elem:
            publish_date = self._clean_text(date_elem.get_text())

        journalist = "미확인"
        journalist_elem = soup.select_one('.media_end_head_journalist_name') or soup.select_one('.media_end_head_journalist_box em')
        if journalist_elem:
            journalist = self._clean_text(journalist_elem.get_text())

        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, .copyright, .reporter, .media_end_head_journalist_box'):
            tag.decompose()

        content = self._clean_text(content_elem.get_text())

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
                title = self._clean_text(title_elem.get_text())
        
        if not title:
             raise ValueError("다음 뉴스 제목을 찾을 수 없습니다.")

        # 본문 추출
        content_elem = soup.select_one('div.article_view') or soup.select_one('section[dmcf-sid]')
        if not content_elem:
            raise ValueError("다음 뉴스 본문을 찾을 수 없습니다.")

        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, .link_news, .box_europe, .recomm_vod, .btn_relation'):
            tag.decompose()

        content = self._clean_text(content_elem.get_text())

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
                title = self._clean_text(title_elem.get_text())
                title = title.replace(' : 네이트 뉴스', '').strip()
            else:
                raise ValueError("네이트 뉴스 제목을 찾을 수 없습니다.")
        
        # 본문 추출
        content_elem = soup.select_one('#realArtcContents')
        
        if not content_elem:
            raise ValueError("네이트 뉴스 본문을 찾을 수 없습니다.")
        
        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, .advertisement, .relation'):
            tag.decompose()
            
        # 하단 링크 모음 등 불필요한 p 태그 제거
        for p in content_elem.select('p'):
            # 링크가 포함되어 있거나 '인/기/기/사' 같은 텍스트가 있는 경우 제거
            if p.find('a') or '인/기/기/사' in p.get_text():
                p.decompose()
        
        content = self._clean_text(content_elem.get_text())
        
        return {
            "title": title,
            "content": content,
            "url": url
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
                title = self._clean_text(title_elem.get_text())
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
        
        content = self._clean_text(content_elem.get_text())
        
        return {
            "title": title,
            "content": content,
            "url": url
        }

    def _scrape_yonhap(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """연합뉴스 스크래핑"""
        # 제목: og:title 메타 태그 우선
        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            title = title_elem.get('content', '')
        else:
            title_elem = soup.find('h1')
            if not title_elem:
                raise ValueError("연합뉴스 제목을 찾을 수 없습니다.")
            title = self._clean_text(title_elem.get_text())
        
        # 기자명: 전체 HTML에서 "(서울=연합뉴스) 안용수 기자 =" 패턴 찾기
        # article 태그 밖의 <p> 태그에 있을 수 있음
        journalist = "미확인"
        
        # 방법 1: <p> 태그들에서 찾기
        for p_tag in soup.find_all('p'):
            p_text = p_tag.get_text()
            journalist_pattern = re.search(r'=연합뉴스\)\s*([가-힣]{2,4})\s*기자', p_text)
            if journalist_pattern:
                journalist = journalist_pattern.group(1) + " 기자"
                break
        
        # 방법 2: 전체 HTML에서 찾기 (방법 1 실패 시)
        if journalist == "미확인":
            full_text = soup.get_text()
            journalist_pattern = re.search(r'=연합뉴스\)\s*([가-힣]{2,4})\s*기자', full_text)
            if journalist_pattern:
                journalist = journalist_pattern.group(1) + " 기자"
        
        # 본문: article 태그
        content_elem = soup.find('article')
        if not content_elem:
            raise ValueError("연합뉴스 본문을 찾을 수 없습니다.")
        
        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, .relation-news'):
            tag.decompose()
        
        content = self._clean_text(content_elem.get_text())
        
        # 메타데이터 추출
        publisher = "연합뉴스"
        
        # 게재일: article:published_time 메타 태그
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
            title = self._clean_text(title_elem.get_text())
        
        # 본문: article 태그
        content_elem = soup.find('article')
        if not content_elem:
            raise ValueError("뉴시스 본문을 찾을 수 없습니다.")
        
        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        
        content = self._clean_text(content_elem.get_text())
        
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
            title = self._clean_text(title_elem.get_text())
        
        # 본문: article 태그
        content_elem = soup.find('article')
        if not content_elem:
            raise ValueError("뉴스1 본문을 찾을 수 없습니다.")
        
        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        
        content = self._clean_text(content_elem.get_text())
        
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
            title = self._clean_text(title_elem.get_text())
        
        # 본문: article 태그 또는 div#news-contents
        # 본문: div#news-contents 우선 검색 후 article 태그 검색
        content_elem = soup.select_one('div#news-contents') or soup.select_one('div.news-con') or soup.find('article')
        
        if not content_elem:
            # 본문이 여러 p 태그로 구성된 경우
            paragraphs = soup.find_all('p')
            if paragraphs:
                content = '\n\n'.join([self._clean_text(p.get_text()) for p in paragraphs if len(p.get_text().strip()) > 30])
            else:
                raise ValueError("뉴스핌 본문을 찾을 수 없습니다.")
        else:
            # 불필요한 요소 제거
            for tag in content_elem.select('script, style, .ad, figure, img, .relation-news'):
                tag.decompose()
            content = self._clean_text(content_elem.get_text())
        
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

    def _scrape_generic(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """일반 뉴스 사이트 스크래핑"""
        # 제목 추출 시도 (여러 패턴)
        title_elem = (
            soup.find('h1') or
            soup.find('h2') or
            soup.select_one('meta[property="og:title"]') or
            soup.select_one('title')
        )

        if not title_elem:
            raise ValueError("기사 제목을 찾을 수 없습니다.")

        # meta 태그의 경우 content 속성 사용
        if title_elem.name == 'meta':
            title = title_elem.get('content', '')
        else:
            title = self._clean_text(title_elem.get_text())

        # 본문 추출 시도 (여러 패턴)
        content_elem = (
            soup.find('article') or
            soup.find('div', class_=re.compile(r'article|content|body', re.I)) or
            soup.find('div', id=re.compile(r'article|content|body', re.I))
        )

        if not content_elem:
            # p 태그들을 모아서 본문 구성
            paragraphs = soup.find_all('p')
            if len(paragraphs) < 3:
                raise ValueError("기사 본문을 찾을 수 없습니다.")
            content = '\n\n'.join([self._clean_text(p.get_text()) for p in paragraphs if len(p.get_text().strip()) > 50])
        else:
            # 불필요한 요소 제거
            for tag in content_elem.select('script, style, .ad, .advertisement'):
                tag.decompose()
            content = self._clean_text(content_elem.get_text())

        if not content or len(content) < 100:
            raise ValueError("기사 본문이 너무 짧습니다.")
        
        # Extract publisher from URL or meta tags
        publisher = "미확인"
        og_site = soup.find('meta', property='og:site_name')
        if og_site:
            publisher = og_site.get('content', '미확인')
        elif 'mt.co.kr' in url:
            publisher = "머니투데이"
        elif 'ajunews.com' in url:
            publisher = "아주경제"

        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": publisher,
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup)
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
        content = self._clean_text(content_elem.get_text())
        
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
        
        content_elem = soup.find('article') or soup.select_one('div.article-text')
        if not content_elem:
            raise ValueError("한겨레 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._clean_text(content_elem.get_text())
        
        publish_date = "미확인"
        date_elem = soup.select_one('li.ArticleDetailView_dateListItem__mRc3d')
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            if '등록' in date_text:
                publish_date = date_text.replace('등록', '').strip()
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "한겨레",
            "publish_date": publish_date,
            "journalist": self._extract_journalist(soup)
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
                title = self._clean_text(h1_tags[1].get_text())
            elif h1_tags:
                title = self._clean_text(h1_tags[0].get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "한국경제",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='.author')
        }

    def _scrape_hankook(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """한국일보 스크래핑"""
        title = self._extract_title(soup, 'h1.title')
        if title:
            title = title.replace(' | 한국일보', '')
        else:
            raise ValueError("한국일보 제목을 찾을 수 없습니다.")
        
        content_elem = soup.find('article') or soup.select_one('div.article-body')
        content = ''
        if content_elem:
            for tag in content_elem.select('script, style, .ad, figure, img'):
                tag.decompose()
            content = self._clean_text(content_elem.get_text())
        
        if not content or len(content) < 100:
            content = self._extract_content_from_paragraphs(soup)
        
        if not content or len(content) < 100:
            raise ValueError("한국일보 본문을 찾을 수 없습니다.")
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "한국일보",
            "publish_date": self._extract_publish_date(soup),
            "journalist": self._extract_journalist(soup, selector='div.reporter-info-wrap', pattern=r'([가-힣]{2,4})기자')
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
        content = self._clean_text(content_elem.get_text())
        
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
        
        content_elem = soup.find('article') or soup.select_one('div.article_view')
        if not content_elem:
            raise ValueError("서울신문 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._clean_text(content_elem.get_text())
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "publisher": "서울신문",
            "publish_date": self._extract_publish_date(soup, 'time'),
            "journalist": self._extract_journalist(soup, pattern=r'([가-힣]{2,4})\s*기자')
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
            content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
            content = self._clean_text(content_elem.get_text())
        
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
            content = self._clean_text(content_elem.get_text())
        
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
            content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
                content = self._clean_text(content_elem.get_text())
            
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
        """제목 추출 헬퍼: og:title 우선, 실패 시 fallback_selector 사용"""
        title_elem = soup.select_one('meta[property="og:title"]')
        if title_elem:
            return title_elem.get('content', '')
        
        title_elem = soup.select_one(fallback_selector) or soup.find('h1')
        if title_elem:
            return self._clean_text(title_elem.get_text())
        return ""

    def _extract_content_from_paragraphs(self, soup: BeautifulSoup, min_content_len: int = 100, min_p_len: int = 30) -> str:
        """본문 추출 헬퍼: p 태그들을 모아서 본문 구성 (Fallback)"""
        paragraphs = soup.find_all('p')
        if paragraphs:
            return '\n\n'.join([self._clean_text(p.get_text()) for p in paragraphs if len(p.get_text().strip()) > min_p_len])
        return ""

    def _extract_journalist(self, soup: BeautifulSoup, selector: Optional[str] = None, pattern: Optional[str] = None) -> str:
        """
        기자명 추출 헬퍼 (개선된 범용 버전)
        - 띄어쓰기 유무 자동 처리: "이름 기자", "이름기자" 모두 인식
        - 범용 블랙리스트로 일반적인 오탐 자동 필터링
        """
        # 범용 블랙리스트: 다양한 언론사에서 공통적으로 발견되는 오탐 단어들
        COMMON_BLACKLIST = [
            # 자주 나오는 메뉴/UI 텍스트
            '로그인', '구독', '회원가입', '팔로우', '스크랩',
            # 칼럼/섹션 이름
            '칼럼', '기획', '특집', '연재', '인터뷰',
            # 기타 일반 텍스트
            '뉴스레터', '이메일', '페이스북', '트위터', '카카오',
            '스타', '견습', '경력', '모집', '전체', '이데일리'
        ]
        
        def is_valid_name(name: str) -> bool:
            """기자명이 유효한지 검증"""
            if not name or len(name) < 2 or len(name) > 4:
                return False
            # 블랙리스트 필터링 (부분 일치 포함)
            for blacklisted in COMMON_BLACKLIST:
                if blacklisted in name or name in blacklisted:
                    return False
            return True
        
        # 1. 메타 태그 (author, og:article:author, dable:author)
        meta_names = ['author', 'og:article:author', 'dable:author', 'byl']
        for name in meta_names:
            author_tag = soup.find('meta', property=name) or soup.find('meta', attrs={'name': name})
            if author_tag:
                content = author_tag.get('content', '')
                if not content: continue
                
                # 메타 태그에서 이름 추출 (기자, 에디터)
                # 1. "OOO 기자" 패턴
                match = re.search(r'([가-힣]{2,4})\s*기자', content)
                if match and is_valid_name(match.group(1)):
                    return match.group(1) + " 기자"
                
                # 2. "OOO 에디터" 패턴
                match = re.search(r'([가-힣]{2,4})\s*에디터', content)
                if match and is_valid_name(match.group(1)):
                    return match.group(1) + " 기자"

                # 3. 이름만 있는 경우 (검증 후 사용)
                clean_name = content.strip()
                if is_valid_name(clean_name):
                    return clean_name + " 기자"
        
        # 2. Selector 방식
        if selector:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text()
                # 띄어쓰기 유무 상관없이 매칭
                match = re.search(r'([가-힣]{2,4})\s*기자', text)
                if match and is_valid_name(match.group(1)):
                    return match.group(1) + " 기자"
                
                # 에디터 패턴 추가
                match = re.search(r'([가-힣]{2,4})\s*에디터', text)
                if match and is_valid_name(match.group(1)):
                    return match.group(1) + " 기자"

                if pattern:
                    match = re.search(pattern, text)
                    if match and is_valid_name(match.group(1)):
                        return match.group(1) + " 기자"
        
        # 3. 전체 텍스트에서 패턴 검색
        full_text = soup.get_text()
        search_pattern = pattern if pattern else r'([가-힣]{2,4})\s*기자'
        # 에디터 패턴도 검색? (일단 기자 패턴만 유지하되, 필요시 확장)

        full_text = soup.get_text()
        
        # 기본 패턴 또는 사용자 제공 패턴 사용
        search_pattern = pattern if pattern else r'([가-힣]{2,4})\s*기자'
        
        # 모든 매칭 후보 찾기
        matches = re.findall(search_pattern, full_text)
        
        # 첫 번째 유효한 이름 반환
        for name in matches:
            if is_valid_name(name):
                return name + " 기자"
        
        return "미확인"

    def _extract_publish_date(self, soup: BeautifulSoup, selector: Optional[str] = None, attr: Optional[str] = None) -> str:
        """게재일 추출 헬퍼"""
        # 1. 메타 태그 (article:published_time)
        date_tag = soup.select_one('meta[property="article:published_time"]')
        if date_tag:
            return date_tag.get('content', '미확인')
            
        # 2. Selector
        if selector:
            elem = soup.select_one(selector)
            if elem:
                if attr:
                    return elem.get(attr, '미확인')
                return self._clean_text(elem.get_text())
                
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
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        content_elem = (soup.find('div', class_='article_body') or 
                       soup.find('div', id='article_body') or
                       soup.find('div', class_='article_view') or
                       soup.find('div', id='articleBody'))
        if not content_elem:
            raise ValueError("서울경제 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
                title = self._clean_text(title_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        
        content_elem = soup.find('div', id='article_content') or soup.find('div', class_='article_content')
        if not content_elem:
            raise ValueError("파이낸셜뉴스 본문을 찾을 수 없습니다.")
        
        for tag in content_elem.select('script, style, .ad, figure, img'):
            tag.decompose()
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
           content = self._clean_text(content_elem.get_text())
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
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        content = self._clean_text(content_elem.get_text())
        
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
        
        content = self._clean_text(content_elem.get_text())

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
        """경기일보 스크래핑"""
        return self._scrape_basic(soup, url, "경기일보", 
            title_selector='.article_head .title', 
            content_selector='.article_view')

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
        
        content = self._clean_text(content_elem.get_text())

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
        """강원일보 스크래핑"""
        return self._scrape_basic(soup, url, "강원일보", 
            title_selector='div.article_head h2.title', 
            content_selector='div.article_content')

    def _scrape_basic(self, soup: BeautifulSoup, url: str, publisher: str, title_selector: str, content_selector: str) -> Dict[str, str]:
        """기본 스크래퍼 패턴"""
        title = self._extract_title(soup, title_selector)
        if not title:
            # Fallback
            title_elem = soup.select_one(title_selector)
            if title_elem: 
                title = self._clean_text(title_elem.get_text())
            if not title:
                raise ValueError(f"{publisher} 제목을 찾을 수 없습니다.")

        content_elem = soup.select_one(content_selector)
        if not content_elem:
            raise ValueError(f"{publisher} 본문을 찾을 수 없습니다.")

        for tag in content_elem.select('script, style, .ad, figure, img, .caption'):
            tag.decompose()
        
        content = self._clean_text(content_elem.get_text())

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
        content = self._clean_text(content_elem.get_text())
        
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
        """텍스트 정제"""
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        # 여러 줄바꿈을 두 개로
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # 앞뒤 공백 제거
        text = text.strip()
        return text
