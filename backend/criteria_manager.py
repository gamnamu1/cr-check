# backend/criteria_manager.py

from pathlib import Path
from typing import List, Dict

class CriteriaManager:
    """
    통합 평가 기준 관리 및 프롬프트 최적화
    147KB → 120KB 통합 후 → Phase별 최적화
    Singleton 패턴 적용: 파일 로딩 반복 방지
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
        Phase 1용: 카테고리 목록만 (120KB → 2KB)
        """
        categories = []
        for line in self.full_criteria.split('\n'):
            if line.startswith('## ') and any(char.isdigit() for char in line[:10]):
                categories.append(line.strip('# ').strip())

        return '\n'.join(f"{i+1}. {cat}" for i, cat in enumerate(categories))

    def get_relevant_content(self, identified_categories: List[str]) -> str:
        """
        Phase 2용: 식별된 카테고리 관련 내용만 추출 (120KB → 8-15KB)

        Args:
            identified_categories: ["1. 진실성과 정확성", "2. 투명성과 책임성"]

        Returns:
            해당 카테고리의 상세 내용 + 윤리규범 근거
        """
        if not identified_categories:
            # 이슈가 없으면 전체 요약만
            return self._get_summary()

        lines = self.full_criteria.split('\n')
        relevant_sections = []

        for category in identified_categories:
            if category not in self.category_index:
                continue

            start_idx = self.category_index[category]

            # 다음 카테고리까지 추출
            end_idx = len(lines)
            for other_cat, idx in self.category_index.items():
                if idx > start_idx and idx < end_idx:
                    end_idx = idx

            section = '\n'.join(lines[start_idx:end_idx])
            relevant_sections.append(section)

        return '\n\n'.join(relevant_sections)[:15000]  # 최대 15KB

    def _get_summary(self) -> str:
        """전체 평가 기준 요약 (이슈 없을 때 사용)"""
        lines = self.full_criteria.split('\n')
        summary_lines = []

        for line in lines:
            if line.startswith('##') or line.startswith('###'):
                summary_lines.append(line)

        return '\n'.join(summary_lines)[:5000]
