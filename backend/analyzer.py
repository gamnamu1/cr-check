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
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️  ArticleAnalyzer: ANTHROPIC_API_KEY가 설정되지 않았습니다. 분석 요청 시 에러가 발생합니다.")

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

        if not self.client:
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. 서버 로그를 확인하거나 .env 파일을 구성해주세요."
            )

        # Phase 1: 문제 카테고리 식별 및 평가 대상 여부 확인 (Haiku)
        print(f"📊 Phase 1 (Haiku): 평가 대상 여부 확인 및 문제 카테고리 식별 중...")
        phase1_result = await self._identify_categories(article_content)
        
        # 평가 대상이 아닌 경우 즉시 중단
        if not phase1_result.get("is_evaluable", True):
            reason = phase1_result.get("non_evaluable_reason", "평가 대상이 아닙니다.")
            print(f"⛔ 평가 중단: {reason}")
            raise ValueError(reason)

        identified_categories = phase1_result.get("categories", [])
        phase1_time = time.time() - start_time
        print(f"✅ Phase 1 완료 ({phase1_time:.1f}초): {len(identified_categories)}개 카테고리 발견")

        # Phase 2: 상세 분석 및 3개 리포트 생성 (Sonnet)
        print(f"📝 Phase 2 (Sonnet): 3가지 리포트 생성 중...")
        detailed_result = await self._generate_detailed_reports(article_content, identified_categories)
        reports = detailed_result["reports"]
        article_analysis = detailed_result.get("article_analysis", {})
        
        phase2_time = time.time() - start_time - phase1_time
        print(f"✅ Phase 2 완료 ({phase2_time:.1f}초)")

        total_time = time.time() - start_time
        print(f"🎉 전체 분석 완료 (총 {total_time:.1f}초)")

        # 기본 정보와 분석된 상세 정보 병합
        final_article_info = {
            "title": article_content["title"],
            "url": article_content["url"],
            **article_analysis  # AI가 분석한 메타데이터 (기본값)
        }

        # 스크래퍼가 추출한 메타데이터가 있다면 덮어쓰기 (더 정확함)
        if article_content.get("publisher") and article_content["publisher"] != "미확인":
            final_article_info["publisher"] = article_content["publisher"]
            
        if article_content.get("publish_date") and article_content["publish_date"] != "미확인":
            final_article_info["publishDate"] = article_content["publish_date"]

        if article_content.get("journalist") and article_content["journalist"] != "미확인":
            final_article_info["journalist"] = article_content["journalist"]

        return {
            "article_info": final_article_info,
            "reports": reports
        }

    async def _identify_categories(self, article_content: dict) -> Dict:
        """
        Phase 1: 기사 평가 적합성 확인 및 카테고리 식별 (Haiku 사용)
        프롬프트 크기: 120KB → 2KB (카테고리 목록만)
        """
        # 카테고리 목록만 가져오기
        categories_list = self.criteria.get_phase1_prompt()

        prompt = f"""당신은 한국신문윤리위원회의 1차 심사 담당자입니다.
아래 글을 분석하여 '평가 대상 여부'를 먼저 판단하고, 평가 대상일 경우에만 문제가 될 만한 카테고리를 식별하세요.

## 평가 카테고리 (8개)
{categories_list}

## 기사
제목: {article_content['title']}
본문: {article_content['content']}

## 작업 지시

1. **평가 대상 여부 판단 (Eligibility Check)**:
   - 이 글이 객관적 사실을 다루는 **'뉴스 보도(News Report)'**인지 확인하세요.
   - **평가 제외 대상**:
     - 사설 (Editorial)
     - 칼럼 (Column) / 오피니언 (Opinion)
     - 서평 / 영화 리뷰 / 제품 리뷰
     - 에세이 / 수필 / 소설
     - 단순 공지사항 / 인사 / 부고
   - 위 제외 대상에 해당하면 `is_evaluable: false`로 설정하고 이유를 적으세요.

2. **문제 카테고리 식별 (평가 대상인 경우)**:
   - 기사를 읽고 위 8개 카테고리 중 **문제가 발견되는 카테고리만** 식별하세요.
   - 카테고리 전체 이름으로 응답 (예: "1. 진실성과 정확성")
   - 문제가 없으면 빈 배열 반환

## 응답 형식 (JSON만 출력)

**Case 1: 평가 대상이 아닌 경우**
{{
  "is_evaluable": false,
  "non_evaluable_reason": "사설/칼럼과 같은 오피니언 글, 서평이나 제품 평가와 같은 각종 리뷰 기사는 평가 대상이 아닙니다.",
  "categories": []
}}

**Case 2: 평가 대상인 경우 (문제 있음)**
{{
  "is_evaluable": true,
  "non_evaluable_reason": null,
  "categories": [
    "1. 진실성과 정확성",
    "2. 투명성과 책임성"
  ]
}}

**Case 3: 평가 대상인 경우 (문제 없음)**
{{
  "is_evaluable": true,
  "non_evaluable_reason": null,
  "categories": []
}}

**필수 사항**:
- 반드시 JSON 형식으로만 응답하세요
- 마크다운 코드 블록(```) 사용 금지
- JSON 외 설명 문구 금지
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

            return result

        except Exception as e:
            print(f"⚠️ Phase 1 오류: {e}")
            # 오류 발생 시 안전하게 진행 (평가 가능한 것으로 간주하되 카테고리는 전체 분석)
            return {
                "is_evaluable": True,
                "non_evaluable_reason": None,
                "categories": ["전체 카테고리 분석 필요"]
            }

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
        # 관련 내용만 추출 (+ 키워드 기반 별도 준칙 자동 포함)
        article_text = f"{article_content['title']} {article_content['content']}"
        relevant_content = self.criteria.get_relevant_content(identified_categories, article_text)

        # 카테고리 목록 텍스트화
        categories_text = '\n'.join(f"- {cat}" for cat in identified_categories) if identified_categories else "특이사항 없음"

        prompt = f"""당신은 한국신문윤리위원회의 심의 위원입니다.
1차 심사에서 식별된 문제 카테고리를 바탕으로 기사를 분석하고 3가지 버전의 상세한 서술형 리포트를 작성하세요.

## 1차 심사 결과
{categories_text}

## 해당 카테고리 평가 기준 및 윤리규범
{relevant_content}

## 기사
제목: {article_content['title']}
본문: {article_content['content'][:3000]}...

## 🟢 평가 원칙 (필수 준수)
1. **구체적 준칙 우선 적용 (Build-up 인용 방식)**:
   - 기사가 자살, 재난, 인권(장애인/이주민/성소수자), 성폭력 등 특정 주제와 관련된 경우, 반드시 **'9. 별도 보도 준칙'**의 해당 항목을 **가장 먼저** 인용하여 구체적인 위반 사항을 지적하십시오.
   - 그 다음, 관련된 **'언론윤리헌장'**이나 **'신문윤리강령'**의 상위 원칙을 인용하여 논리를 강화하십시오. (예: "이 보도는 '자살보도 권고기준'의 구체적 묘사 금지 조항을 위반했습니다. 이는 더 나아가 '언론윤리헌장'의 인권 보호 원칙에도 어긋나는 것입니다.")
2. **객관적 어조 유지**: 감정적 비난을 배제하고 차분하고 논리적인 톤을 유지하십시오.
3. **건설적 대안 제시**: 단순한 비판을 넘어, "어떻게 썼어야 했는지"에 대한 구체적인 대안을 제시하십시오.
4. **칭찬 요소 발굴**: 기사에 긍정적인 부분(예: 정확한 사실 확인, 피해자 보호 노력 등)이 있다면 반드시 언급하여 균형을 맞추십시오.
5. **서술형 표현 (점수화 금지)**
   - 점수, 등급, 백분율 등 정량적 수치 사용 금지
   - 구체적 설명과 사례로 평가 제공
6. **구체적 인용**
   - 기사에서 문제가 되는 부분을 직접 인용
   - 인용문을 분석하고 윤리규범과 연결

4. **건설적 피드백**
   - 문제 지적과 함께 개선 방향 제안
   - 부정적 판단보다 발전적 제안 중심

## 3가지 리포트 버전

### 1. comprehensive (일반 시민용 종합 리포트, 1000-1500자)
**톤**: 객관적, 체계적, 교육적
**어투**: "~입니다", "~있습니다" (격식체), "독자", "시민" (3인칭)
**구조**:
1. **문제점 분석** (700-1000자):
   - 주요 문제점 2-3가지를 윤리규범 근거와 함께 제시
   - 각 문제점마다 "언론윤리헌장 제X조는..." 형식으로 윤리규범 인용
   - 기사에서 문제가 되는 부분을 직접 인용

2. **종합 평가** (200-300자):
   - "이러한 보도는... 우려가 있습니다"
   - 개선 방향 간략히 제시

### 2. journalist (기사 작성자를 위한 리포트, 1000-1500자)
**톤**: 직접적, 건설적 비판, 전문가 대 전문가
**어투**: "당신의 기사는..." (2인칭 직접), "~하세요", "~해야 합니다" (권유/명령형)
**구조**:
- 도입: "시민 주도 CR 프로젝트를 통해 귀하의 기사를 평가했습니다. 이 평가는 책임 있는 저널리즘을 만들어가기 위한 목적으로 작성되었으며, 건설적 비판을 통해 언론 신뢰도 향상에 기여하고자 합니다."
- 본론: "당신의 기사는 [문제점]입니다. 이는 [윤리규범]을 위반하는 것입니다."
- 개선안: "예를 들어, '[구체적 예시]'와 같은 방식으로 표현할 수 있습니다"
- 결론: "이러한 개선은... 언론의 본질적 역할을 수행하기 위해 필요합니다. 이 평가가 더 나은 저널리즘을 위한 소중한 참고 자료가 되기를 바랍니다."

### 3. student (학생을 위한 교육용 리포트, 1000-1500자)
**톤**: 친근하고 대화적, 비유와 예시 풍부
**어투**: "~이에요", "~해요" (친근체), "여러분" (직접 호명), 질문형 "~일까요?"
**구조**:
- 도입: "오늘은 함께 뉴스를 비판적으로 읽는 방법에 대해 알아보려고 해요. 우리가 매일 접하는 뉴스는 정말 믿을 만한 걸까요?"
- 본론: 각 문제점마다 생활 속 비유 사용 ("마치 교실에서 두 친구가 다퉜는데...", "여러분이 친구에게 험담을 전할 때...")
- 질문형 대화: "왜 이것이 문제일까요?", "공정하지 않겠죠?"
- 결론: "여러분의 비판적 읽기 능력이 바로 더 나은 언론과 사회를 만드는 첫걸음입니다!"

## 작성 지침

- 일반 문자열로만 작성 (HTML 태그, 마크다운 문법 금지)
- **분량**: 각 리포트 1000-1500자 내외
- 문단 구분은 개행(\\n\\n) 두 번으로
- 구체적 인용구는 큰따옴표("")로 표시
- **톤과 어투를 철저히 구분**: comprehensive(격식체), journalist(2인칭 직접), student(친근체)

## JSON 형식 (이것만 출력)
{{
  "article_analysis": {{
    "publisher": "매체명 (기사에서 확인 불가시 '미확인')",
    "publishDate": "게재일시 (기사에서 확인 불가시 '미확인')",
    "journalist": "기자명 (기사에서 확인 불가시 '미확인')",
    "articleType": "기사 유형 (예: 스트레이트, 해설, 인터뷰 등)",
    "articleElements": "기사 요소 (예: 5W1H, 인용문, 통계 등)",
    "editStructure": "편집 구조 (예: 역피라미드, 시간순 등)",
    "reportingMethod": "취재 방식 (예: 단독, 보도자료 등)",
    "contentFlow": "내용 흐름 (한 문장 요약)"
  }},
  "reports": {{
    "comprehensive": "...",
    "journalist": "...",
    "student": "..."
  }}
}}

**필수**:
- JSON만 출력하세요
- 마크다운 코드 블록(```) 사용 금지
- JSON 외 설명 문구 금지
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
                result_json = robust_json_parse(response_text)

                # 구조 검증 및 데이터 추출
                if "reports" in result_json:
                    reports = result_json["reports"]
                    article_analysis = result_json.get("article_analysis", {})
                else:
                    # 구버전 호환성 (혹시 모를 경우)
                    reports = result_json
                    article_analysis = {}

                # 필수 필드 검증
                required_fields = ["comprehensive", "journalist", "student"]
                for field in required_fields:
                    if field not in reports:
                        raise ValueError(f"필수 리포트 '{field}'가 누락되었습니다.")

                # 서술형 평가 원칙 검증 (점수화 패턴 감지)
                self.validate_descriptive_evaluation(reports)

                return {
                    "reports": reports,
                    "article_analysis": article_analysis
                }

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
