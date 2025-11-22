# backend/analyzer.py

from anthropic import AsyncAnthropic
import os
from typing import Dict, List
import time
from pathlib import Path
from dotenv import load_dotenv
from criteria_manager import CriteriaManager
from json_parser import robust_json_parse

# .env 파일 로드 (backend 디렉토리에서)
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class ArticleAnalyzer:
    """
    기사를 분석하여 3가지 서술형 리포트를 생성하는 핵심 클래스

    원칙:
    - 윤리규범 기반: 모든 평가는 한국신문윤리위원회 규범을 근거로
    - 서술형 평가: 점수/등급 없이 구체적 분석 제공
    - 3가지 관점: 일반 시민, 기자, 학생을 위한 맞춤형 리포트

    최적화:
    - 2단계 하이브리드 전략: Phase 1(Haiku), Phase 2(Sonnet)
    - 프롬프트 최적화: 147KB → 통합 120KB → Phase별 2-15KB
    - 강화된 JSON 파싱: 재귀적 괄호 매칭
    """

    def __init__(self):
        """분석기 초기화"""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.\n\n"
                "설정 방법:\n"
                "  1. https://console.anthropic.com/account/keys 에서 API 키 발급\n"
                "  2. 터미널에서 실행: export ANTHROPIC_API_KEY='your-key-here'\n"
                "  3. 또는 backend/.env 파일에 저장"
            )

        self.client = AsyncAnthropic(api_key=api_key)

        # 하이브리드 모델 전략
        self.phase1_model = "claude-haiku-4-5-20251001"
        self.phase2_model = "claude-sonnet-4-5-20250929"

        # 통합 평가 기준 관리자
        self.criteria = CriteriaManager()

    async def analyze(self, article_content: dict) -> dict:
        """
        기사를 2단계로 분석하여 3가지 리포트 생성

        Args:
            article_content: {
                "title": 기사 제목,
                "content": 기사 본문,
                "url": 기사 URL
            }

        Returns:
            dict: {
                "article_info": {...},
                "reports": {
                    "comprehensive": 종합 리포트 (일반 시민용),
                    "journalist": 기자용 리포트,
                    "student": 학생용 리포트
                }
            }
        """
        start_time = time.time()

        # Phase 1: 문제 카테고리 식별 (Haiku)
        print(f"📊 Phase 1 (Haiku): 문제 카테고리 식별 중...")
        identified_categories = await self._identify_categories(article_content)
        phase1_time = time.time() - start_time
        print(f"✅ Phase 1 완료 ({phase1_time:.1f}초): {len(identified_categories)}개 카테고리 발견")

        # Phase 2: 상세 분석 및 3개 리포트 생성 (Sonnet)
        print(f"📝 Phase 2 (Sonnet): 3가지 리포트 생성 중...")
        reports = await self._generate_detailed_reports(article_content, identified_categories)
        phase2_time = time.time() - start_time - phase1_time
        print(f"✅ Phase 2 완료 ({phase2_time:.1f}초)")

        total_time = time.time() - start_time
        print(f"🎉 전체 분석 완료 (총 {total_time:.1f}초)")

        return {
            "article_info": {
                "title": article_content["title"],
                "url": article_content["url"]
            },
            "reports": reports
        }

    async def _identify_categories(self, article_content: dict) -> List[str]:
        """
        Phase 1: 기사에서 문제가 될 만한 카테고리 식별 (Haiku 사용)
        프롬프트 크기: 120KB → 2KB (카테고리 목록만)
        """
        # 카테고리 목록만 가져오기
        categories_list = self.criteria.get_phase1_prompt()

        prompt = f"""당신은 한국신문윤리위원회의 1차 심사 담당자입니다.
아래 기사를 빠르게 스캔하여 문제가 될 만한 카테고리를 식별하세요.

## 평가 카테고리 (8개)
{categories_list}

## 기사
제목: {article_content['title']}
본문: {article_content['content']}

## 작업 지시
1. 기사를 읽고 위 8개 카테고리 중 **문제가 발견되는 카테고리만** 식별
2. 카테고리 전체 이름으로 응답 (예: "1. 진실성과 정확성")
3. 문제가 없으면 빈 배열 반환

## 응답 형식 (JSON만 출력)
{{
  "categories": [
    "1. 진실성과 정확성",
    "2. 투명성과 책임성"
  ]
}}

**필수 사항**:
- 반드시 JSON 형식으로만 응답하세요
- 마크다운 코드 블록(```) 사용 금지
- JSON 외 설명 문구 금지
- 문제가 없다면: {{"categories": []}}
"""

        try:
            message = await self.client.messages.create(
                model=self.phase1_model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()

            # 강화된 JSON 파싱
            result = robust_json_parse(response_text)

            return result.get("categories", [])

        except Exception as e:
            print(f"⚠️ Phase 1 오류: {e}")
            # Phase 1 실패 시에도 Phase 2 진행 (전체 분석)
            return ["전체 카테고리 분석 필요"]

    async def _generate_detailed_reports(
        self,
        article_content: dict,
        identified_categories: List[str]
    ) -> dict:
        """
        Phase 2: 식별된 카테고리를 바탕으로 3가지 상세 리포트 생성 (Sonnet 사용)
        프롬프트 크기: 관련 내용만 8-15KB

        원칙:
        - 윤리규범 기반: 모든 지적은 윤리규범 조항을 근거로
        - 서술형 평가: 점수/등급 사용 금지
        - 구체적 인용: 기사에서 문제 부분 직접 인용
        - 건설적 피드백: 개선 방향 제시
        """
        # 관련 내용만 추출
        relevant_content = self.criteria.get_relevant_content(identified_categories)

        # 카테고리 목록 텍스트화
        categories_text = '\n'.join(f"- {cat}" for cat in identified_categories) if identified_categories else "특이사항 없음"

        prompt = f"""당신은 한국신문윤리위원회의 심의 위원입니다.
1차 심사에서 식별된 문제 카테고리를 바탕으로 3가지 버전의 상세한 서술형 리포트를 작성하세요.

## 1차 심사 결과
{categories_text}

## 해당 카테고리 평가 기준 및 윤리규범
{relevant_content}

## 기사
제목: {article_content['title']}
본문: {article_content['content'][:3000]}...

## 🟢 평가 원칙 (필수 준수)

1. **윤리규범 기반 평가**
   - 모든 지적 사항은 한국기자협회 윤리강령, 신문윤리실천요강 등 공인된 윤리규범을 근거로 제시
   - 윤리규범 조항을 정확히 인용 (예: "한국기자협회 윤리강령 제1조...")

2. **서술형 표현 (점수화 금지)**
   - 점수, 등급, 백분율 등 정량적 수치 사용 금지
   - 구체적 설명과 사례로 평가 제공

3. **구체적 인용**
   - 기사에서 문제가 되는 부분을 직접 인용
   - 인용문을 분석하고 윤리규범과 연결

4. **건설적 피드백**
   - 문제 지적과 함께 개선 방향 제안
   - 부정적 판단보다 발전적 제안 중심

## 3가지 리포트 버전 (각 800-1500자)

### 1. comprehensive (일반 시민용 종합 리포트)
**톤**: 객관적, 체계적, 교육적
**어투**: "~입니다", "~있습니다" (격식체), "독자", "시민" (3인칭)
**구조**:
- 도입: "이 기사는 [주제]에 대해 다루고 있습니다. 그러나 기사는..."
- 본론: 주요 문제점 2-3가지를 윤리규범 근거와 함께 제시
- 각 문제점마다 "언론윤리헌장 제X조는..." 형식으로 윤리규범 인용
- 결론: "이러한 보도는... 우려가 있습니다"
**예시 시작**: "이 기사는 [기사 주제]를 다루고 있습니다. 그러나 기사는 여러 윤리적 문제를 안고 있어 독자 여러분께 균형 잡힌 정보를 제공하지 못하고 있습니다."

### 2. journalist (기사 작성자를 위한 리포트)
**톤**: 직접적, 건설적 비판, 전문가 대 전문가
**어투**: "당신의 기사는..." (2인칭 직접), "~하세요", "~해야 합니다" (권유/명령형)
**구조**:
- 도입: "시민 주도의 CR 프로젝트를 통해 귀하의 기사를 평가했습니다. 이 평가는 함께 더 나은 저널리즘을 만들어가기 위한 목적으로..."
- 본론: "당신의 기사는 [문제점]입니다. 이는 [윤리규범]을 위반하는 것입니다."
- 개선안: "예를 들어, '[구체적 예시]'와 같은 방식으로 표현할 수 있습니다"
- 결론: "이러한 개선은... 언론의 본질적 역할을 수행하기 위해 필요합니다. 이 평가가 더 나은 저널리즘을 위한 소중한 참고 자료가 되기를 바랍니다."
**예시 시작**: "당신의 기사는 [주제]를 다루면서 저널리즘의 핵심 원칙인 [원칙]을 현저히 위반했습니다. 전문 기자로서 반드시 개선해야 할 지점들을 구체적으로 짚어보겠습니다."

### 3. student (학생을 위한 교육용 리포트)
**톤**: 친근하고 대화적, 비유와 예시 풍부
**어투**: "~이에요", "~해요" (친근체), "여러분" (직접 호명), 질문형 "~일까요?"
**구조**:
- 도입: "오늘은 함께 뉴스를 비판적으로 읽는 방법에 대해 알아보려고 해요. 우리가 매일 접하는 뉴스는 정말 믿을 만한 걸까요?"
- 본론: 각 문제점마다 생활 속 비유 사용 ("마치 교실에서 두 친구가 다퉜는데...", "여러분이 친구에게 험담을 전할 때...")
- 질문형 대화: "왜 이것이 문제일까요?", "공정하지 않겠죠?"
- 결론: "여러분의 비판적 읽기 능력이 바로 더 나은 언론과 사회를 만드는 첫걸음입니다!"
**예시 시작**: "여러분, 이 기사를 함께 읽어볼까요? 언론의 역할은 무엇일까요? 단순히 누군가의 말을 전달하는 것이 아니라 국민이 현명한 판단을 내릴 수 있도록 균형 잡힌 정보를 제공하는 것입니다."
**비유 예시**: "이것은 마치 [일상 비유]와 같아요", "만약 여러분이 [상황]이라면..."

## 작성 지침

- 일반 문자열로만 작성 (HTML 태그, 마크다운 문법 금지)
- 각 리포트 800-1500자 분량
- 문단 구분은 개행(\\n\\n) 두 번으로
- 구체적 인용구는 큰따옴표("")로 표시
- **톤과 어투를 철저히 구분**: comprehensive(격식체), journalist(2인칭 직접), student(친근체)

## JSON 형식 (이것만 출력)
{{"comprehensive": "...", "journalist": "...", "student": "..."}}

**필수**:
- JSON만 출력하세요
- 마크다운 코드 블록(```) 사용 금지
- JSON 외 설명 문구 금지
- JSON 내부에 마크다운 문법 (#, *, _, - 등) 사용 금지
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                message = await self.client.messages.create(
                    model=self.phase2_model,
                    max_tokens=10000,  # 충분한 토큰 할당
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = message.content[0].text.strip()

                # 강화된 JSON 파싱
                reports = robust_json_parse(response_text)

                # 필수 필드 검증
                required_fields = ["comprehensive", "journalist", "student"]
                for field in required_fields:
                    if field not in reports:
                        raise ValueError(f"필수 리포트 '{field}'가 누락되었습니다.")

                # 서술형 평가 원칙 검증 (점수화 패턴 감지)
                self.validate_descriptive_evaluation(reports)

                return reports

            except Exception as e:
                print(f"⚠️ Phase 2 시도 {attempt + 1}/{max_retries} 실패: {e}")
                if attempt == max_retries - 1:
                    # 최종 실패 시 에러를 명확히 전달 (숨기지 않음)
                    raise ValueError(
                        f"리포트 생성에 실패했습니다.\n"
                        f"원인: {str(e)}\n"
                        f"식별된 카테고리: {categories_text}"
                    )
                # 재시도 전 대기
                await self._wait_for_retry(attempt)

    async def _wait_for_retry(self, attempt: int):
        """재시도 전 exponential backoff"""
        import asyncio
        wait_time = (2 ** attempt) * 1
        print(f"⏳ {wait_time}초 후 재시도...")
        await asyncio.sleep(wait_time)

    def validate_descriptive_evaluation(self, reports: dict):
        """
        서술형 평가 원칙 검증

        권장하지 않는 표현 패턴 감지:
        - 정량적 수치 (점수, 등급, 백분율)
        - 절대적 판단 (상/중/하)

        단, 맥락이 있는 경우 허용:
        - "80%의 국민이..." (통계 인용)
        - "상황이 심각하다" (일반 표현)
        """
        import re

        # 엄격한 점수화 패턴만 검출
        strict_score_patterns = [
            r'\d+(?:\.\d+)?/\d+',           # 6.4/10, 8/10
            r'\d+(?:\.\d+)?점\s*(?:만점|입니다|이다)',  # "75점입니다", "8.5점이다"
            r'등급\s*[:：]\s*[A-F]',         # 등급: A
            r'[A-F]등급\s*(?:입니다|이다)',    # A등급입니다
            r'점수\s*[:：]\s*\d+',            # 점수: 85
        ]

        for report_type, content in reports.items():
            if not isinstance(content, str):
                continue

            for pattern in strict_score_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    raise ValueError(
                        f"⚠️ 점수화 패턴 감지! '{report_type}' 리포트에서 금지된 표현 발견\n"
                        f"패턴: {pattern}\n"
                        f"발견된 내용: {matches}\n\n"
                        f"권장: 윤리규범 기반 서술형 평가를 사용하세요.\n"
                        f"예시: '한국기자협회 윤리강령 제1조(진실 보도)를 위반하여...'"
                    )
