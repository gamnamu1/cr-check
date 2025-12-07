# backend/core/__init__.py
"""
CR 프로젝트 - 코어 모듈 패키지

Two-Layer 아키텍처의 핵심 컴포넌트들을 제공합니다.
"""

from .criteria_manager import CriteriaManager
from .prompt_builder import PromptBuilder
from .analyzer import ArticleAnalyzer

__all__ = [
    'CriteriaManager',
    'PromptBuilder',
    'ArticleAnalyzer',
]
