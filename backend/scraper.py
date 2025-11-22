# backend/scraper.py

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re

class ArticleScraper:
    """
    기사 URL에서 제목과 본문을 추출하는 스크래퍼

    주요 언론사 지원:
    - 네이버 뉴스
    - 다음 뉴스
    - 주요 언론사 직접 URL
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
                "url": 원본 URL
            }

        Raises:
            ValueError: 스크래핑 실패 시
        """
        try:
            # URL 유효성 검증
            if not url or not url.startswith('http'):
                raise ValueError("유효하지 않은 URL입니다.")

            # 페이지 가져오기
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')

            # 네이버 뉴스 감지
            if 'news.naver.com' in url:
                return self._scrape_naver(soup, url)
            # 다음 뉴스 감지
            elif 'news.daum.net' in url:
                return self._scrape_daum(soup, url)
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

        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, .copyright, .reporter'):
            tag.decompose()

        content = self._clean_text(content_elem.get_text())

        return {
            "title": title,
            "content": content,
            "url": url
        }

    def _scrape_daum(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """다음 뉴스 스크래핑"""
        # 제목 추출
        title_elem = soup.select_one('h3.tit_view, .article_view .tit_view')
        if not title_elem:
            title_elem = soup.find('h3', class_='tit_view')

        # 본문 추출
        content_elem = soup.select_one('div.article_view, section[dmcf-sid="news"]')
        if not content_elem:
            content_elem = soup.find('div', class_='news_view')

        if not title_elem or not content_elem:
            raise ValueError("다음 뉴스 형식을 파싱할 수 없습니다.")

        # 텍스트 정제
        title = self._clean_text(title_elem.get_text())

        # 불필요한 요소 제거
        for tag in content_elem.select('script, style, .ad, figure, .link_news'):
            tag.decompose()

        content = self._clean_text(content_elem.get_text())

        return {
            "title": title,
            "content": content,
            "url": url
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

        return {
            "title": title,
            "content": content,
            "url": url
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
