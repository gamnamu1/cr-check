
import json
import requests
from scraper import ArticleScraper

URLS = {
    "Digital Times": "https://www.dt.co.kr/article/12021837",
    "Electronic Times (Main)": "https://www.etnews.com/", 
    "Media Today": "https://www.mediatoday.co.kr/news/articleView.html?idxno=330405",
    "MediaUs": "https://www.mediaus.co.kr/news/articleView.html?idxno=315420",
    "Journalist Association": "https://www.journalist.or.kr/news/article.html?no=59702",
    "No Cut News": "https://www.nocutnews.co.kr/news/6439399",
    "Media Pen": "https://www.mediapen.com/news/view/1064347",
    "Dailian": "https://www.dailian.co.kr/news/view/1582863/",
    "The Fact": "https://news.tf.co.kr/read/ptoday/2250617.htm",
    "New Daily": "https://www.newdaily.co.kr/site/data/html/2025/12/05/2025120500188.html",
    "Break News": "https://www.breaknews.com/1167151",
    "PennMike": "https://www.pennmike.com/news/articleView.html?idxno=111778",
    "Pressian": "https://www.pressian.com/pages/articles/2025112316282189713",
    "OhmyNews": "https://www.ohmynews.com/NWS_Web/View/at_pg.aspx?CNTN_CD=A0003102772&CMPT_CD=SEARCH",
    "Mindle": "https://www.mindlenews.com/news/articleView.html?idxno=16835",
    "iNews24": "https://www.inews24.com/view/tp/1856808"
}

def check_urls():
    scraper = ArticleScraper()
    results = {}
    
    # Header
    print(f"{'Media':<25} | {'Status':<10} | {'Title (First 20)':<25} | {'Content Len':<10} | {'Journalist':<15}")
    print("-" * 100)

    for name, url in URLS.items():
        if name == "Electronic Times (Main)":
            print(f"{name:<25} | SKIP       | {'(Homepage)':<25} | {'-':<10} | {'-':<15}")
            continue
            
        try:
            # Synchronous call
            article = scraper.scrape(url)
            
            # article is a dict
            title = article.get('title', '')
            content = article.get('content', '')
            journalist = article.get('journalist', '')
            publish_date = article.get('publish_date', '')
            
            status = "OK" if title and len(content) > 50 else "FAIL"
            if "본문이 너무 짧습니다" in str(article): status = "FAIL (Short)"
            
            title_display = title.strip()[:20] + "..." if title else "None"
            content_len = len(content) if content else 0
            journalist_display = journalist.strip() if journalist else "None"
            
            print(f"{name:<25} | {status:<10} | {title_display:<25} | {content_len:<10} | {journalist_display:<15}")
            
            results[name] = {
                "status": status,
                "url": url,
                "title": title,
                "content_len": content_len,
                "journalist": journalist,
                "published_date": publish_date
            }
        except Exception as e:
            error_msg = str(e)
            print(f"{name:<25} | ERROR      | {error_msg[:25]:<25} | {'0':<10} | {'Error':<15}")
            results[name] = {
                "status": "ERROR",
                "error": error_msg
            }

    with open("check_urls_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    check_urls()
