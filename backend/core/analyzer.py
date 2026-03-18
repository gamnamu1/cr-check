# backend/core/analyzer.py
"""
CR 프로젝트 - 기사 분석기 (Two-Layer 아키텍처)

3단계 파이프라인으로 기사를 분석합니다:
- Phase 0: Red Flag 사전 스크리닝 (코드 레벨, API 호출 없음)
- Phase 1: 정밀 진단 (Haiku) - 체크리스트 기반 문제 탐지
- Phase 2: 근거 매핑 및 리포트 생성 (Sonnet)

핵심 원칙:
- AI 환각 방지: 윤리규범은 시스템이 제공한 텍스트만 인용
- 비용 최적화: 프롬프트 캐싱, 단계별 모델 분리
- 완전성 보장: 탐지된 모든 문제를 빠짐없이 분석
"""

from anthropic import AsyncAnthropic
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

# 상대 임포트 (패키지 구조에 따라 조정)
try:
    from .criteria_manager import CriteriaManager
    from .prompt_builder import PromptBuilder
except ImportError:
    from criteria_manager import CriteriaManager
    from prompt_builder import PromptBuilder

# 별도의 json_parser 모듈이 있다면 임포트
try:
    from json_parser import robust_json_parse
except ImportError:
    # 기본 JSON 파서 사용
    import re
    def robust_json_parse(text: str) -> dict:
        """기본 JSON 파서"""
        # 마크다운 코드 블록 제거
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # JSON 객체 추출
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end + 1]
        
        return json.loads(text)


# .env 파일 로드
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class ArticleAnalyzer:
    """
    기사를 분석하여 3가지 서술형 리포트를 생성하는 핵심 클래스
    
    Two-Layer 아키텍처:
    - 진단 레이어: 문제 탐지 (Phase 0 + Phase 1)
    - 근거 레이어: 윤리규범 매핑 및 리포트 생성 (Phase 2)
    """
    
    def __init__(self):
        """분석기 초기화"""
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️  ArticleAnalyzer: ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        
        # 모델 설정 (Sonnet 4.6으로 업데이트됨)
        self.phase1_model = "claude-haiku-4-5-20251001"
        self.phase2_model = "claude-sonnet-4-6"
        
        # 핵심 모듈 초기화
        self.criteria = CriteriaManager()
        self.prompt_builder = PromptBuilder()
    
    async def analyze(self, article_content: dict) -> dict:
        """
        기사를 3단계로 분석하여 3가지 리포트 생성
        
        Args:
            article_content: {
                "title": 기사 제목,
                "content": 기사 본문,
                "url": 기사 URL,
                "publisher": (선택) 매체명,
                "publish_date": (선택) 게재일,
                "journalist": (선택) 기자명
            }
        
        Returns:
            dict: {
                "article_info": {...},
                "reports": {
                    "comprehensive": 종합 리포트,
                    "journalist": 기자용 리포트,
                    "student": 학생용 리포트
                }
            }
        """
        start_time = time.time()
        
        if not self.client:
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. "
                "서버 로그를 확인하거나 .env 파일을 구성해주세요."
            )
        
        article_text = article_content.get("content", "")
        article_title = article_content.get("title", "")
        article_url = article_content.get("url", "")
        
        # ==================== Phase 0: Red Flag 사전 스크리닝 ====================
        print(f"🔍 Phase 0: Red Flag 사전 스크리닝...")
        pre_screen_result = self.criteria.pre_screen_red_flags(article_text)
        flagged_count = len(pre_screen_result.get('flagged_items', []))
        print(f"   → {flagged_count}개 Red Flag 패턴 탐지")
        
        # ==================== Phase 1: 문제 카테고리 식별 ====================
        print(f"📊 Phase 1 (Haiku): 평가 대상 여부 확인 및 문제 카테고리 식별...")
        phase1_result = await self._run_phase1(
            article_title=article_title,
            article_content=article_text,
            flagged_hints=pre_screen_result.get('flagged_ids', [])
        )
        
        # 평가 대상이 아닌 경우 즉시 중단
        if not phase1_result.get("is_evaluable", True):
            reason = phase1_result.get("non_evaluable_reason", "평가 대상이 아닙니다.")
            print(f"⛔ 평가 중단: {reason}")
            raise ValueError(reason)
        
        identified_categories = phase1_result.get("categories", [])
        phase1_time = time.time() - start_time
        print(f"✅ Phase 1 완료 ({phase1_time:.1f}초): {len(identified_categories)}개 카테고리 발견")
        
        # ==================== Phase 2: 상세 리포트 생성 ====================
        print(f"📝 Phase 2 (Sonnet): 3가지 리포트 생성...")
        phase2_start = time.time()
        
        detailed_result = await self._run_phase2(
            article_url=article_url,
            article_title=article_title,
            article_content=article_text,
            identified_categories=identified_categories
        )
        
        reports = detailed_result.get("reports", {})
        article_analysis = detailed_result.get("article_analysis", {})
        
        phase2_time = time.time() - phase2_start
        print(f"✅ Phase 2 완료 ({phase2_time:.1f}초)")
        
        total_time = time.time() - start_time
        print(f"🎉 전체 분석 완료 (총 {total_time:.1f}초)")
        
        # 최종 결과 구성
        final_article_info = {
            "title": article_title,
            "url": article_url,
            **article_analysis
        }
        
        # 스크래퍼가 추출한 메타데이터가 있다면 덮어쓰기
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
    
    async def _run_phase1(
        self,
        article_title: str,
        article_content: str,
        flagged_hints: List[str] = None
    ) -> Dict:
        """
        Phase 1: 문제 카테고리 식별 (Haiku)
        """
        category_list = self.criteria.get_category_list()
        
        prompt = self.prompt_builder.build_phase1_prompt(
            article_title=article_title,
            article_content=article_content,
            category_list=category_list,
            flagged_hints=flagged_hints
        )
        
        try:
            message = await self.client.messages.create(
                model=self.phase1_model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            result = robust_json_parse(response_text)
            
            return result
            
        except Exception as e:
            print(f"⚠️ Phase 1 오류: {e}")
            # 오류 시 안전하게 진행
            return {
                "is_evaluable": True,
                "non_evaluable_reason": None,
                "categories": ["1-1", "1-2", "1-3"]  # 기본 카테고리
            }
    
    async def _run_phase2(
        self,
        article_url: str,
        article_title: str,
        article_content: str,
        identified_categories: List[str]
    ) -> Dict:
        """
        Phase 2: 상세 리포트 생성 (Sonnet)
        
        탐지된 문제에 대해서만 관련 윤리규범을 매핑하여 리포트 생성
        """
        # 카테고리 ID에서 서브카테고리 ID 추출
        issue_ids = self._expand_category_ids(identified_categories)
        
        # 관련 평가 기준 및 윤리규범 컨텍스트 생성
        criteria_context = self.criteria.get_criteria_by_ids(issue_ids)
        ethics_context = self.criteria.get_ethics_context(issue_ids)
        
        # v2.0: 키워드 기반 별도 보도 준칙 자동 감지 및 추가
        full_article_text = f"{article_title} {article_content}"
        detected_topics = self.criteria.detect_special_topics(full_article_text)
        if detected_topics:
            special_guidelines = self.criteria.get_special_guidelines_text(detected_topics)
            ethics_context += f"\n\n{special_guidelines}"
            print(f"   → 특수 보도 준칙 자동 감지: {detected_topics}")
        
        # 프롬프트 생성
        system_prompt = self.prompt_builder.build_phase2_system_prompt()
        user_prompt = self.prompt_builder.build_phase2_user_prompt(
            article_url=article_url,
            article_title=article_title,
            article_content=article_content,
            criteria_context=criteria_context,
            ethics_context=ethics_context
        )
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                message = await self.client.messages.create(
                    model=self.phase2_model,
                    max_tokens=10000,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"}  # 프롬프트 캐싱
                        }
                    ],
                    messages=[{"role": "user", "content": user_prompt}]
                )
                
                response_text = message.content[0].text.strip()
                result_json = robust_json_parse(response_text)
                
                # 구조 검증
                if "reports" in result_json:
                    reports = result_json["reports"]
                    article_analysis = result_json.get("article_analysis", {})
                else:
                    reports = result_json
                    article_analysis = {}
                
                # 필수 필드 검증
                required_fields = ["comprehensive", "journalist", "student"]
                for field in required_fields:
                    if field not in reports:
                        raise ValueError(f"필수 리포트 '{field}'가 누락되었습니다.")
                
                # 서술형 평가 원칙 검증
                self._validate_descriptive_evaluation(reports)
                
                return {
                    "reports": reports,
                    "article_analysis": article_analysis
                }
                
            except ValueError as ve:
                print(f"⚠️ Phase 2 검증 실패 ({attempt + 1}/{max_retries}): {ve}")
                
                if attempt == max_retries - 1:
                    raise ValueError(f"리포트 생성 실패: {str(ve)}")
                    
                await self._wait_for_retry(attempt)
                
            except Exception as e:
                print(f"⚠️ Phase 2 오류 ({attempt + 1}/{max_retries}): {e}")
                
                if attempt == max_retries - 1:
                    raise ValueError(f"리포트 생성 실패: {str(e)}")
                    
                await self._wait_for_retry(attempt)
    
    def _expand_category_ids(self, categories: List[str]) -> List[str]:
        """
        카테고리 ID를 서브카테고리 ID로 확장
        
        예: ["1-1", "1-3"] → ["1-1-1", "1-1-2", ..., "1-3-1", "1-3-2", ...]
        """
        issue_ids = []
        
        for cat_id in categories:
            # 이미 서브카테고리 ID인 경우 (예: "1-1-1")
            if cat_id.count('-') >= 2:
                issue_ids.append(cat_id)
                continue
            
            # 카테고리 ID인 경우 (예: "1-1") → 하위 서브카테고리 모두 추가
            for category in self.criteria.checklist.get('categories', []):
                if category['id'] == cat_id:
                    for sub in category.get('subcategories', []):
                        issue_ids.append(sub['id'])
                    break
        
        return issue_ids if issue_ids else ["1-1-1", "1-2-1"]  # 기본값
    
    def _validate_descriptive_evaluation(self, reports: dict):
        """서술형 평가 원칙 검증 (점수화 패턴 감지)"""
        import re
        
        strict_score_patterns = [
            r'\d+(?:\.\d+)?/\d+',           # 6.4/10, 8/10
            r'\d+(?:\.\d+)?점\s*(?:만점|입니다|이다)',
            r'등급\s*[:：]\s*[A-F]',
            r'[A-F]등급\s*(?:입니다|이다)',
            r'점수\s*[:：]\s*\d+',
        ]
        
        for report_type, content in reports.items():
            if not isinstance(content, str):
                continue
            
            for pattern in strict_score_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    raise ValueError(
                        f"점수화 패턴 감지: '{report_type}' 리포트에서 "
                        f"금지된 표현 '{matches[0]}' 발견"
                    )
    
    async def _wait_for_retry(self, attempt: int):
        """재시도 전 exponential backoff"""
        import asyncio
        wait_time = (2 ** attempt) * 1
        print(f"⏳ {wait_time}초 후 재시도...")
        await asyncio.sleep(wait_time)


# 테스트용
if __name__ == "__main__":
    import asyncio
    
    async def test():
        analyzer = ArticleAnalyzer()
        print(f"Phase 1 Model: {analyzer.phase1_model}")
        print(f"Phase 2 Model: {analyzer.phase2_model}")
        print(f"Criteria loaded: {len(analyzer.criteria.checklist.get('categories', []))} categories")
    
    asyncio.run(test())
