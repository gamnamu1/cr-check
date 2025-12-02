#!/usr/bin/env python3
# Test script for Nate and Zum news scrapers

import sys
sys.path.insert(0, '/Users/gamnamu/Documents/cr-check/backend')

from scraper import ArticleScraper
import json

# Test URLs
test_urls = {
    "nate": "https://news.nate.com/view/20250320n03718",
    "zum": "https://news.zum.com/articles/102573421/%EC%9D%B4%EC%A4%80%EC%84%9D-%EC%9C%A0%EC%B6%9C%EC%9E%90-%EC%A4%91%EA%B5%AD%EC%9D%B8%EC%9D%B4%EB%83%90-%EC%A1%B0%EC%84%A0%EC%A1%B1%EC%9D%B4%EB%83%90-%EC%BF%A0%ED%8C%A1-%EC%88%98%EC%82%AC-%EC%A4%91?cm=news_home_politics&r=6&thumb=0"
}

scraper = ArticleScraper()
results = {}

for portal, url in test_urls.items():
    print(f"\\n{'='*60}")
    print(f"Testing {portal.upper()} news scraper...")
    print(f"{'='*60}")
    
    try:
        result = scraper.scrape(url)
        results[portal] = {
            "status": "success",
            "title": result.get("title", "")[:100],  # First 100 chars
            "content_length": len(result.get("content", "")),
            "content_preview": result.get("content", "")[:200]  # First 200 chars
        }
        print(f"✅ SUCCESS")
        print(f"Title: {result['title'][:80]}...")
        print(f"Content length: {len(result['content'])} characters")
        print(f"Preview: {result['content'][:150]}...")
        
        # Save full content to file for inspection
        with open(f'/Users/gamnamu/Documents/cr-check/backend/debug_{portal}.txt', 'w', encoding='utf-8') as f:
            f.write(f"Title: {result['title']}\n\nContent:\n{result['content']}")

    except Exception as e:
        results[portal] = {
            "status": "failed",
            "error": str(e)
        }
        print(f"❌ FAILED: {e}")

# Save results
with open('/Users/gamnamu/Documents/cr-check/backend/test_result.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\\n{'='*60}")
print("Test results saved to test_result.json")
print(f"{'='*60}")
