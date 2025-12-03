#!/usr/bin/env python3
"""
스크래핑 가능 여부만 테스트 (AI 분석 없이)
토큰 소모 없이 기사 추출 가능 여부만 확인합니다.
"""

import sys
sys.path.insert(0, '/Users/gamnamu/Documents/cr-check/backend')

from scraper import ArticleScraper
import json
from datetime import datetime

def test_url(scraper, url, name=""):
    """단일 URL 스크래핑 테스트"""
    print(f"\n{'='*70}")
    print(f"📰 테스트: {name if name else url}")
    print(f"{'='*70}")
    
    try:
        result = scraper.scrape(url)
        
        # 결과 검증
        title = result.get("title", "")
        content = result.get("content", "")
        publisher = result.get("publisher", "미확인")
        journalist = result.get("journalist", "미확인")
        publish_date = result.get("publish_date", "미확인")
        
        # 성공 여부 판단
        is_valid = len(title) > 5 and len(content) > 100
        
        if is_valid:
            print(f"✅ 스크래핑 성공")
            print(f"   제목: {title[:80]}{'...' if len(title) > 80 else ''}")
            print(f"   본문 길이: {len(content):,}자")
            print(f"   매체명: {publisher}")
            print(f"   기자명: {journalist}")
            print(f"   게재일: {publish_date}")
            
            return {
                "status": "success",
                "url": url,
                "name": name,
                "title": title,
                "content_length": len(content),
                "publisher": publisher,
                "journalist": journalist,
                "publish_date": publish_date,
                "content_preview": content[:200]
            }
        else:
            print(f"⚠️  스크래핑 실패 (제목 또는 본문이 너무 짧음)")
            print(f"   제목 길이: {len(title)}자")
            print(f"   본문 길이: {len(content)}자")
            
            return {
                "status": "failed",
                "url": url,
                "name": name,
                "error": "제목 또는 본문이 너무 짧음",
                "title_length": len(title),
                "content_length": len(content)
            }
            
    except Exception as e:
        print(f"❌ 스크래핑 실패")
        print(f"   에러: {str(e)}")
        
        return {
            "status": "error",
            "url": url,
            "name": name,
            "error": str(e)
        }

def main():
    """메인 테스트 함수"""
    scraper = ArticleScraper()
    
    # 테스트할 URL 리스트
    # 형식: (언론사명, URL)
    test_cases = [
        # 중앙일간지 12곳
        ("경향신문", "https://www.khan.co.kr/article/202512031831001"),
        ("국민일보", "https://www.kmib.co.kr/article/view.asp?arcid=0029062500&code=61111611&sid1=pol"),
        ("내일신문", "https://www.naeil.com/news/read/569720"),
        ("동아일보", "https://www.donga.com/news/Economy/article/all/20251203/132892988/1"),
        ("문화일보", "https://www.munhwa.com/article/11551636"),
        ("서울신문", "https://www.seoul.co.kr/news/economy/distribution/2025/12/04/20251204008005"),
        ("세계일보", "https://www.segye.com/newsView/20251202516380"),
        ("아시아투데이", "https://www.asiatoday.co.kr/kn/view.php?key=20251203010001955&ref=main_midtop&ref=section_topnews"),
        ("조선일보", "https://www.chosun.com/economy/industry-company/2025/12/03/3H7ED2VJFZH4DPFQVODQP6QDOE/"),
        ("중앙일보", "https://www.joongang.co.kr/article/25387257"),
        ("한겨레", "https://www.hani.co.kr/arti/society/society_general/1232666.html"),
        ("한국일보", "https://www.hankookilbo.com/News/Read/A2025120113540002855"),
    ]
    
    print("\n" + "="*70)
    print("🔍 스크래핑 가능 여부 테스트 시작")
    print(f"   총 {len(test_cases)}개 URL 테스트")
    print("="*70)
    
    results = []
    success_count = 0
    
    for name, url in test_cases:
        result = test_url(scraper, url, name)
        results.append(result)
        
        if result["status"] == "success":
            success_count += 1
    
    # 최종 결과 요약
    print("\n" + "="*70)
    print("📊 테스트 결과 요약")
    print("="*70)
    print(f"✅ 성공: {success_count}/{len(test_cases)}")
    print(f"❌ 실패: {len(test_cases) - success_count}/{len(test_cases)}")
    
    # 성공/실패 목록
    print("\n[성공한 언론사]")
    for r in results:
        if r["status"] == "success":
            print(f"  ✅ {r['name']}")
    
    print("\n[실패한 언론사]")
    for r in results:
        if r["status"] != "success":
            print(f"  ❌ {r['name']}: {r.get('error', '알 수 없는 오류')}")
    
    # JSON 파일로 저장
    output_file = f'/Users/gamnamu/Documents/cr-check/backend/scraping_test_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "total_tests": len(test_cases),
            "success_count": success_count,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 상세 결과가 저장되었습니다: {output_file}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
