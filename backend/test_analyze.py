#!/usr/bin/env python3
# backend/test_analyze.py

"""
실제 기사 분석 테스트 스크립트
"""

import requests
import json
import time

# API 엔드포인트
API_URL = "http://localhost:8000/analyze"

# 테스트용 기사 URL (예시)
# 실제 테스트 시 아래 URL들 중 하나를 사용하거나, 원하는 기사 URL로 변경하세요
TEST_URLS = [
    # 네이버 뉴스 예시 (실제 URL로 교체 필요)
    "https://n.news.naver.com/mnews/article/001/0014918144",

    # 다음 뉴스 예시 (실제 URL로 교체 필요)
    # "https://v.daum.net/v/...",
]

def test_analyze(article_url):
    """기사 분석 테스트"""

    print("\n" + "=" * 80)
    print(f"📰 기사 분석 테스트 시작")
    print("=" * 80)
    print(f"\n기사 URL: {article_url}")
    print("\n⏳ 분석 중... (40-60초 소요 예상)")
    print("   - Phase 1 (Haiku): 카테고리 식별 (5-10초)")
    print("   - Phase 2 (Sonnet): 3가지 리포트 생성 (30-50초)")

    # 요청 데이터
    payload = {
        "url": article_url
    }

    # 시작 시간
    start_time = time.time()

    try:
        # POST 요청
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=180  # 3분 타임아웃
        )

        # 소요 시간
        elapsed_time = time.time() - start_time

        # 응답 확인
        if response.status_code == 200:
            result = response.json()

            print("\n" + "=" * 80)
            print(f"✅ 분석 완료! (소요 시간: {elapsed_time:.1f}초)")
            print("=" * 80)

            # 기사 정보
            print(f"\n📰 기사 정보:")
            print(f"   제목: {result['article_info']['title'][:80]}...")
            print(f"   URL: {result['article_info']['url']}")

            # 리포트 정보
            reports = result['reports']
            print(f"\n📊 생성된 리포트:")

            for report_type, content in reports.items():
                print(f"\n   [{report_type.upper()}]")
                print(f"   길이: {len(content)} 문자")
                print(f"   미리보기: {content[:150]}...")

            # 결과 저장
            output_file = "test_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"\n💾 전체 결과가 '{output_file}'에 저장되었습니다.")

            print("\n" + "=" * 80)
            print("🎉 테스트 성공!")
            print("=" * 80)

            return True

        else:
            print(f"\n❌ 오류 발생 (HTTP {response.status_code})")
            print(f"   메시지: {response.text}")
            return False

    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  타임아웃 발생 ({elapsed_time:.1f}초)")
        print("   분석 시간이 3분을 초과했습니다.")
        return False

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ 예외 발생 ({elapsed_time:.1f}초)")
        print(f"   오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""

    print("\n" + "🧪 CR-Check 기사 분석 테스트".center(80))

    # 서버 상태 확인
    print("\n서버 상태 확인 중...")
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ 서버 실행 중")
            print(f"   API 키 설정: {health_data.get('api_key_configured', False)}")
        else:
            print(f"❌ 서버 응답 오류: {health_response.status_code}")
            print("\n서버를 먼저 실행해주세요:")
            print("   cd /Users/gamnamu/Desktop/cr-check-work/cr-check/backend")
            print("   python3 main.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("\n서버를 먼저 실행해주세요:")
        print("   cd /Users/gamnamu/Desktop/cr-check-work/cr-check/backend")
        print("   python3 main.py")
        return

    # 사용자 입력 받기
    print("\n" + "-" * 80)
    print("테스트할 기사 URL을 입력하세요.")
    print("(엔터를 누르면 기본 테스트 URL 사용)")
    print("-" * 80)

    user_url = input("\n기사 URL: ").strip()

    if not user_url:
        # 기본 URL 사용
        test_url = TEST_URLS[0]
        print(f"\n기본 테스트 URL 사용: {test_url}")
    else:
        test_url = user_url

    # 확인
    print(f"\n다음 기사를 분석합니다:")
    print(f"  {test_url}")
    print("\n⚠️  주의: Claude API 비용이 발생합니다 (약 $0.01-0.05)")

    confirm = input("\n계속하시겠습니까? (y/N): ").strip().lower()

    if confirm != 'y':
        print("\n테스트 취소됨")
        return

    # 테스트 실행
    success = test_analyze(test_url)

    if success:
        print("\n다음 단계:")
        print("  1. test_result.json 파일 확인")
        print("  2. 다른 기사로 추가 테스트")
        print("  3. Docker 설정으로 진행")
    else:
        print("\n문제 해결:")
        print("  1. 서버 로그 확인: tail -f /tmp/cr-check-server.log")
        print("  2. API 키 확인: cat backend/.env")
        print("  3. 기사 URL 확인: 유효한 뉴스 URL인지 확인")


if __name__ == "__main__":
    main()
