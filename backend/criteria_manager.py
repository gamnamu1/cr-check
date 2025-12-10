# backend/criteria_manager.py

from pathlib import Path
from typing import List, Dict, Set
import re

# 특수 보도 준칙 키워드 매핑
SPECIAL_GUIDELINES_KEYWORDS = {
    "9-1": {  # 자살보도 권고기준
        "keywords": ["자살", "극단적 선택", "스스로 목숨", "투신", "음독", "자해"],
        "section_name": "자살보도 권고기준"
    },
    "9-2": {  # 재난보도준칙
        "keywords": ["재난", "사고", "참사", "붕괴", "화재", "폭발", "침몰", "지진", "태풍", "홍수"],
        "section_name": "재난보도준칙"
    },
    "9-3": {  # 인권보도준칙
        "keywords": ["장애인", "장애", "이주민", "외국인", "난민", "다문화", "이민자", "불법체류", 
                    "성소수자", "동성애", "트랜스젠더", "LGBT", "퀴어"],
        "section_name": "인권보도준칙"
    },
    "9-4": {  # 성폭력 범죄 보도
        "keywords": ["성폭력", "성폭행", "성추행", "강간", "미투", "성범죄", "성희롱"],
        "section_name": "성폭력 범죄 보도 세부 권고 기준"
    }
}


class CriteriaManager:
    """
    통합 평가 기준 관리 및 프롬프트 최적화
    147KB → 120KB 통합 후 → Phase별 최적화
    Singleton 패턴 적용: 파일 로딩 반복 방지
    
    v2.0 개선사항:
    - 키워드 기반 별도 보도 준칙 자동 포함 (Option A)
    - Phase 1 하위 준칙 명시 (Option B)
    - 카테고리 키 부분 매칭 지원
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CriteriaManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
            
        references_dir = Path(__file__).parent / 'references'

        # 통합 평가 기준 로드
        with open(references_dir / 'unified-criteria.md', 'r', encoding='utf-8') as f:
            self.full_criteria = f.read()

        # 카테고리 인덱스 구축
        self.category_index = self._build_category_index()
        self._initialized = True

    def _build_category_index(self) -> Dict[str, int]:
        """
        카테고리별 시작 위치 인덱싱
        빠른 검색을 위한 매핑 테이블
        """
        index = {}
        lines = self.full_criteria.split('\n')

        for i, line in enumerate(lines):
            if line.startswith('## ') and any(char.isdigit() for char in line[:10]):
                # "## 1. 진실성과 정확성" 형식 감지
                category = line.strip('# ').strip()
                index[category] = i

        return index

    def get_phase1_prompt(self) -> str:
        """
        Phase 1용: 카테고리 목록 + 별도 보도 준칙 하위 항목 포함
        Option B: Haiku가 하위 준칙을 정확히 식별할 수 있도록 명시
        """
        categories = []
        for line in self.full_criteria.split('\n'):
            if line.startswith('## ') and any(char.isdigit() for char in line[:10]):
                categories.append(line.strip('# ').strip())

        # 기본 카테고리 목록 생성
        result = []
        for i, cat in enumerate(categories):
            result.append(f"{i+1}. {cat}")
            
            # "9. 별도 보도 준칙"인 경우 하위 항목 추가
            if cat.startswith("9."):
                result.append("   - 9-1. 자살보도 권고기준 (자살, 극단적 선택 관련)")
                result.append("   - 9-2. 재난보도준칙 (재난, 사고, 참사 관련)")
                result.append("   - 9-3. 인권보도준칙 (장애인, 이주민/외국인, 성소수자 인권)")
                result.append("   - 9-4. 성폭력 범죄 보도 세부 권고 기준")

        return '\n'.join(result)

    def _find_category_key(self, category: str) -> str:
        """
        부분 매칭으로 카테고리 키 찾기
        예: "9. 별도 보도 준칙" → "9. 별도 보도 준칙 (Special Reporting Guidelines)"
        """
        # 정확히 일치하면 그대로 반환
        if category in self.category_index:
            return category
        
        # 카테고리 번호 추출 (예: "1.", "9.")
        match = re.match(r'^(\d+\.)', category)
        if match:
            prefix = match.group(1)
            for key in self.category_index.keys():
                if key.startswith(prefix):
                    return key
        
        return None

    def detect_special_topics(self, article_content: str) -> Set[str]:
        """
        Option A: 기사 내용에서 특수 주제 감지
        
        Args:
            article_content: 기사 제목 + 본문
            
        Returns:
            감지된 특수 준칙 ID 집합 (예: {"9-3", "9-4"})
        """
        detected = set()
        content_lower = article_content.lower()
        
        for guideline_id, config in SPECIAL_GUIDELINES_KEYWORDS.items():
            for keyword in config["keywords"]:
                if keyword in content_lower or keyword in article_content:
                    detected.add(guideline_id)
                    break  # 해당 준칙은 이미 감지됨
        
        return detected

    def _get_special_guidelines_section(self, guideline_id: str) -> str:
        """
        특정 별도 보도 준칙 섹션 추출
        
        Args:
            guideline_id: "9-1", "9-2", "9-3", "9-4"
            
        Returns:
            해당 준칙의 전체 내용
        """
        lines = self.full_criteria.split('\n')
        
        # 해당 섹션 헤더 찾기 (예: "### 9-3. 인권보도준칙")
        section_pattern = f"### {guideline_id}"
        start_idx = None
        
        for i, line in enumerate(lines):
            if line.startswith(section_pattern):
                start_idx = i
                break
        
        if start_idx is None:
            return ""
        
        # 다음 ### 또는 ## 까지 추출
        end_idx = len(lines)
        for i in range(start_idx + 1, len(lines)):
            if lines[i].startswith('### ') or lines[i].startswith('## '):
                end_idx = i
                break
        
        return '\n'.join(lines[start_idx:end_idx])

    def get_relevant_content(self, identified_categories: List[str], article_content: str = "") -> str:
        """
        Phase 2용: 식별된 카테고리 관련 내용 + 키워드 기반 별도 준칙 자동 포함

        Args:
            identified_categories: ["1. 진실성과 정확성", "2. 투명성과 책임성"]
            article_content: 기사 제목 + 본문 (키워드 감지용)

        Returns:
            해당 카테고리의 상세 내용 + 윤리규범 근거 + 관련 별도 준칙
        """
        if not identified_categories:
            return self._get_summary()

        lines = self.full_criteria.split('\n')
        relevant_sections = []

        for category in identified_categories:
            # 부분 매칭으로 실제 키 찾기
            actual_key = self._find_category_key(category)
            if actual_key is None:
                continue

            start_idx = self.category_index[actual_key]

            # 다음 카테고리까지 추출
            end_idx = len(lines)
            for other_cat, idx in self.category_index.items():
                if idx > start_idx and idx < end_idx:
                    end_idx = idx

            section = '\n'.join(lines[start_idx:end_idx])
            relevant_sections.append(section)

        # Option A: 키워드 기반 별도 준칙 자동 포함
        if article_content:
            detected_topics = self.detect_special_topics(article_content)
            
            for topic_id in detected_topics:
                special_section = self._get_special_guidelines_section(topic_id)
                if special_section and special_section not in '\n\n'.join(relevant_sections):
                    config = SPECIAL_GUIDELINES_KEYWORDS.get(topic_id, {})
                    section_name = config.get("section_name", topic_id)
                    
                    # 별도 준칙임을 명시
                    header = f"\n\n---\n### ⚠️ 자동 감지된 별도 보도 준칙: {section_name}\n(기사 내용에서 관련 키워드가 감지되어 자동 포함됨)\n\n"
                    relevant_sections.append(header + special_section)

        return '\n\n'.join(relevant_sections)[:18000]  # 확장된 최대 크기

    def _get_summary(self) -> str:
        """전체 평가 기준 요약 (이슈 없을 때 사용)"""
        lines = self.full_criteria.split('\n')
        summary_lines = []

        for line in lines:
            if line.startswith('##') or line.startswith('###'):
                summary_lines.append(line)

        return '\n'.join(summary_lines)[:5000]
