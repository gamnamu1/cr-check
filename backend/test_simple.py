#!/usr/bin/env python3
# backend/test_simple.py

"""
간단한 테스트 스크립트
CriteriaManager와 JSON 파싱만 테스트 (API 호출 없음)
"""

import asyncio
from criteria_manager import CriteriaManager
from json_parser import robust_json_parse

def test_criteria_manager():
    """CriteriaManager 테스트"""
    print("=" * 60)
    print("1. CriteriaManager 테스트")
    print("=" * 60)

    cm = CriteriaManager()

    # 카테고리 인덱스 확인
    print(f"\n✅ 카테고리 인덱스: {len(cm.category_index)}개 발견")
    for cat in cm.category_index.keys():
        print(f"   - {cat}")

    # Phase 1 프롬프트
    print(f"\n✅ Phase 1 프롬프트 생성")
    phase1 = cm.get_phase1_prompt()
    print(f"   길이: {len(phase1)} 문자")
    print(f"   미리보기:\n{phase1[:200]}...")

    # Phase 2 프롬프트
    print(f"\n✅ Phase 2 프롬프트 생성")
    test_categories = ["1. 진실성과 정확성", "2. 투명성과 책임성"]
    phase2 = cm.get_relevant_content(test_categories)
    print(f"   카테고리: {test_categories}")
    print(f"   길이: {len(phase2)} 문자")
    print(f"   미리보기:\n{phase2[:200]}...")

    print("\n" + "=" * 60)
    print("CriteriaManager 테스트 완료 ✅")
    print("=" * 60)


def test_json_parser():
    """JSON Parser 테스트"""
    print("\n" + "=" * 60)
    print("2. JSON Parser 테스트")
    print("=" * 60)

    # 테스트 케이스들
    test_cases = [
        {
            "name": "Clean JSON",
            "input": '{"comprehensive": "test1", "journalist": "test2", "student": "test3"}'
        },
        {
            "name": "JSON with markdown",
            "input": '```json\n{"comprehensive": "test1", "journalist": "test2", "student": "test3"}\n```'
        },
        {
            "name": "JSON with extra text",
            "input": 'Here is the result:\n{"comprehensive": "test1", "journalist": "test2", "student": "test3"}\nEnd of result.'
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n테스트 {i}: {test['name']}")
        try:
            result = robust_json_parse(test['input'])
            print(f"   ✅ 파싱 성공")
            print(f"   키: {list(result.keys())}")
        except Exception as e:
            print(f"   ❌ 파싱 실패: {e}")

    print("\n" + "=" * 60)
    print("JSON Parser 테스트 완료 ✅")
    print("=" * 60)


async def test_analyzer_init():
    """Analyzer 초기화 테스트 (API 호출 없음)"""
    print("\n" + "=" * 60)
    print("3. ArticleAnalyzer 초기화 테스트")
    print("=" * 60)

    try:
        from analyzer import ArticleAnalyzer

        print("\n✅ ArticleAnalyzer import 성공")

        analyzer = ArticleAnalyzer()
        print("✅ ArticleAnalyzer 초기화 성공")
        print(f"   Phase 1 모델: {analyzer.phase1_model}")
        print(f"   Phase 2 모델: {analyzer.phase2_model}")
        print(f"   CriteriaManager: {type(analyzer.criteria).__name__}")

    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Analyzer 초기화 테스트 완료 ✅")
    print("=" * 60)


def main():
    """메인 테스트 실행"""
    print("\n" + "🧪 CR-Check 백엔드 간단 테스트".center(60))
    print()

    # 1. CriteriaManager 테스트
    test_criteria_manager()

    # 2. JSON Parser 테스트
    test_json_parser()

    # 3. Analyzer 초기화 테스트
    asyncio.run(test_analyzer_init())

    print("\n" + "=" * 60)
    print("🎉 모든 테스트 완료!".center(60))
    print("=" * 60)
    print()
    print("다음 단계:")
    print("  - 서버 실행: python3 main.py")
    print("  - API 테스트: curl -X POST http://localhost:8000/analyze ...")
    print()


if __name__ == "__main__":
    main()
