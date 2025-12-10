# backend/core/criteria_manager.py
"""
CR 프로젝트 - 평가 기준 및 윤리규범 관리자

Two-Layer 아키텍처에서 '진단(Diagnosis)'과 '근거(Evidence)'를 
구조적으로 분리하여 관리하는 핵심 모듈입니다.

역할:
1. criteria_checklist.json 로드 및 관리 (진단용)
2. ethics_library.json 로드 및 관리 (인용용)
3. Phase 1/2용 프롬프트 데이터 제공
4. 키워드 기반 별도 보도 준칙 자동 포함 (v2.0)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

# 별도 보도 준칙 키워드 매핑 (v2.0 추가)
SPECIAL_GUIDELINES_KEYWORDS = {
    "suicide_reporting": {  # 자살보도 권고기준
        "keywords": ["자살", "극단적 선택", "스스로 목숨", "투신", "음독", "자해"],
        "ethics_ids": ["special_suicide_1", "special_suicide_2"],
        "guideline_name": "자살보도 권고기준 3.0",
        "guideline_text": """### 자살보도 권고기준 3.0
- **기본 원칙**: 자살 보도가 모방 자살을 유발할 수 있음을 유의해야 한다.
- **제목 제한**: 기사 제목에 '자살'이라는 표현을 쓰지 않고, 선정적인 표현을 피한다.
- **구체적 묘사 금지**: 자살의 수단, 방법, 장소, 동기 등을 구체적으로 묘사하지 않는다.
- **미화/합리화 금지**: 자살을 미화하거나 합리화하지 않고, 고통을 해결하는 방법으로 묘사하지 않는다."""
    },
    "disaster_reporting": {  # 재난보도준칙
        "keywords": ["재난", "사고", "참사", "붕괴", "화재", "폭발", "침몰", "지진", "태풍", "홍수"],
        "ethics_ids": ["special_disaster_1"],
        "guideline_name": "재난보도준칙",
        "guideline_text": """### 재난보도준칙
- **피해자 중심**: 재난 보도는 피해자와 그 가족의 인권을 침해하지 않도록 각별히 유의해야 한다.
- **선정성 지양**: 피해의 참상을 지나치게 상세하게 묘사하거나, 자극적인 영상을 반복적으로 사용하지 않는다.
- **정확성 우선**: 확인되지 않은 정보나 유언비어의 확산을 경계하고, 공식적인 발표와 전문가의 의견을 중시한다."""
    },
    "human_rights_reporting": {  # 인권보도준칙
        "keywords": ["장애인", "장애", "이주민", "외국인", "난민", "다문화", "이민자", "불법체류", 
                    "성소수자", "동성애", "트랜스젠더", "LGBT", "퀴어", "외국인보호소"],
        "ethics_ids": ["special_hr_1", "special_hr_2", "special_hr_3"],
        "guideline_name": "인권보도준칙",
        "guideline_text": """### 인권보도준칙
- **장애인 인권**: 장애인을 시혜나 동정의 대상으로 묘사하지 않으며, 장애를 극복해야 할 대상이나 불행의 원인으로 그리지 않는다.
- **이주민/외국인 인권**: 이주민과 외국인을 잠재적 범죄자나 사회 문제의 원인으로 묘사하지 않으며, 그들의 문화적 차이를 존중한다.
- **성소수자 인권**: 성적 지향이나 성별 정체성을 이유로 차별하거나 혐오하는 표현을 사용하지 않는다."""
    },
    "sexual_violence_reporting": {  # 성폭력 범죄 보도
        "keywords": ["성폭력", "성폭행", "성추행", "강간", "미투", "성범죄", "성희롱"],
        "ethics_ids": ["special_sv_1", "special_sv_2"],
        "guideline_name": "성폭력 범죄 보도 세부 권고 기준",
        "guideline_text": """### 성폭력 범죄 보도 세부 권고 기준
- **피해자 신원 보호**: 피해자의 신원이 노출될 수 있는 정보(이름, 나이, 주소, 학교, 직장 등)를 보도하지 않는다.
- **2차 피해 방지**: 피해자의 행실이나 옷차림 등을 문제 삼아 범죄의 원인을 피해자에게 돌리는 듯한 보도를 하지 않는다.
- **자극적 묘사 금지**: 범행 과정을 지나치게 상세하게 묘사하거나, 선정적인 제목을 사용하여 대중의 호기심을 자극하지 않는다."""
    }
}


class CriteriaManager:
    """평가 기준 및 윤리규범 관리 클래스"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Args:
            data_dir: JSON 파일이 위치한 디렉토리 경로
                      None이면 backend/data/ 사용
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        
        self.data_dir = data_dir
        self.checklist: Dict = {}
        self.ethics_library: Dict = {}
        
        # 데이터 로드
        self._load_data()
    
    def _load_data(self) -> None:
        """JSON 파일들 로드"""
        checklist_path = self.data_dir / "criteria_checklist.json"
        ethics_path = self.data_dir / "ethics_library.json"
        
        if checklist_path.exists():
            with open(checklist_path, 'r', encoding='utf-8') as f:
                self.checklist = json.load(f)
            print(f"✅ 체크리스트 로드 완료: {len(self.checklist.get('categories', []))}개 카테고리")
        else:
            print(f"⚠️ 체크리스트 파일을 찾을 수 없습니다: {checklist_path}")
        
        if ethics_path.exists():
            with open(ethics_path, 'r', encoding='utf-8') as f:
                self.ethics_library = json.load(f)
            print(f"✅ 윤리규범 라이브러리 로드 완료: {len(self.ethics_library.get('codes', {}))}개 규범")
        else:
            print(f"⚠️ 윤리규범 파일을 찾을 수 없습니다: {ethics_path}")
    
    # ==================== Phase 0: Red Flag 스크리닝 ====================
    
    def get_red_flags(self) -> List[Dict[str, Any]]:
        """
        Phase 0용 Red Flag 패턴 목록 반환
        
        Returns:
            List of {pattern, criteria_id, q_id, severity}
        """
        flags = []
        for category in self.checklist.get('categories', []):
            for sub in category.get('subcategories', []):
                for flag in sub.get('red_flags', []):
                    flags.append({
                        'pattern': flag,
                        'criteria_id': sub['id'],
                        'severity': sub.get('severity', 'major')
                    })
        return flags
    
    def pre_screen_red_flags(self, article_text: str) -> Dict[str, Any]:
        """
        Phase 0: Red Flag 사전 스크리닝 (API 호출 없음)
        
        Args:
            article_text: 기사 본문
            
        Returns:
            {
                'flagged_items': [{'pattern': ..., 'criteria_id': ..., 'severity': ...}],
                'flagged_ids': ['1-1-1', '1-2-1', ...]
            }
        """
        detected = []
        red_flags = self.get_red_flags()
        
        for flag in red_flags:
            if flag['pattern'] in article_text:
                detected.append(flag)
        
        # 중복 ID 제거
        flagged_ids = list(set(d['criteria_id'] for d in detected))
        
        return {
            'flagged_items': detected,
            'flagged_ids': flagged_ids
        }
    
    # ==================== Phase 1: 진단 체크리스트 ====================
    
    def get_diagnostic_checklist(self) -> str:
        """
        Phase 1용 진단 질문 체크리스트 (텍스트 형식)
        
        Returns:
            마크다운 형식의 체크리스트 문자열
        """
        lines = []
        
        for category in self.checklist.get('categories', []):
            lines.append(f"## {category['id']}. {category['name']}")
            
            for sub in category.get('subcategories', []):
                lines.append(f"\n### {sub['id']}. {sub['name']}")
                
                if sub.get('definition'):
                    # 정의는 간략하게 (200자 제한)
                    definition = sub['definition'][:200]
                    if len(sub['definition']) > 200:
                        definition += "..."
                    lines.append(f"정의: {definition}")
                
                lines.append("진단 질문:")
                for q in sub.get('diagnostic_questions', []):
                    lines.append(f"  - [{q['q_id']}] {q['question']}")
        
        return "\n".join(lines)
    
    def get_category_list(self) -> str:
        """
        Phase 1용 카테고리 목록만 반환 (간단 버전)
        """
        lines = []
        for category in self.checklist.get('categories', []):
            lines.append(f"{category['id']}. {category['name']}")
            for sub in category.get('subcategories', []):
                lines.append(f"  - {sub['id']}. {sub['name']}")
        return "\n".join(lines)
    
    def get_phase1_prompt(self) -> str:
        """
        기존 호환성을 위한 Phase 1 프롬프트 (카테고리 목록)
        """
        return self.get_category_list()
    
    # ==================== Phase 2: 근거 매핑 및 리포트 ====================
    
    def get_criteria_by_ids(self, issue_ids: List[str]) -> str:
        """
        Phase 2용: 탐지된 이슈 ID에 해당하는 평가 기준 상세 반환
        
        Args:
            issue_ids: 탐지된 문제 ID 목록 (예: ['1-1-1', '1-7-3'])
            
        Returns:
            마크다운 형식의 평가 기준 상세 문자열
        """
        result = []
        
        for category in self.checklist.get('categories', []):
            for sub in category.get('subcategories', []):
                if sub['id'] in issue_ids:
                    result.append(f"### {sub['id']}. {sub['name']}")
                    if sub.get('definition'):
                        result.append(f"정의: {sub['definition']}")
                    result.append("진단 질문:")
                    for q in sub.get('diagnostic_questions', []):
                        result.append(f"  - {q['question']}")
                    result.append("")
        
        return "\n".join(result)
    
    def get_ethics_context(self, issue_ids: List[str]) -> str:
        """
        Phase 2용: 탐지된 이슈 ID에 연결된 윤리규범 텍스트 반환
        
        이슈 ID → ethics_code_refs → ethics_library.json에서 원문 조회
        
        Args:
            issue_ids: 탐지된 문제 ID 목록
            
        Returns:
            마크다운 형식의 윤리규범 텍스트
        """
        ethics_ids: Set[str] = set()
        
        # 탐지된 이슈에 연결된 규범 ID 수집
        for category in self.checklist.get('categories', []):
            for sub in category.get('subcategories', []):
                if sub['id'] in issue_ids:
                    ethics_ids.update(sub.get('ethics_code_refs', []))
        
        # 규범 원문 조회 및 포맷팅
        result = []
        codes = self.ethics_library.get('codes', {})
        
        for ethics_id in sorted(ethics_ids):
            code = codes.get(ethics_id)
            if code:
                clause = f" {code['clause']}" if code.get('clause') else ""
                result.append(
                    f"**{code['source']} {code['article']}{clause} '{code['title']}'**\n"
                    f"> {code['full_text']}"
                )
        
        return "\n\n".join(result) if result else "관련 윤리규범 없음"
    
    # ==================== 기존 호환성 메서드 ====================
    
    def detect_special_topics(self, article_content: str) -> Set[str]:
        """
        v2.0: 기사 내용에서 특수 주제 감지
        
        Args:
            article_content: 기사 제목 + 본문
            
        Returns:
            감지된 특수 준칙 키 집합 (예: {"human_rights_reporting", "disaster_reporting"})
        """
        detected = set()
        
        for guideline_key, config in SPECIAL_GUIDELINES_KEYWORDS.items():
            for keyword in config["keywords"]:
                if keyword in article_content:
                    detected.add(guideline_key)
                    break  # 해당 준칙은 이미 감지됨
        
        return detected
    
    def get_special_guidelines_text(self, detected_topics: Set[str]) -> str:
        """
        v2.0: 감지된 특수 주제에 해당하는 별도 보도 준칙 텍스트 반환
        
        Args:
            detected_topics: 감지된 주제 키 집합
            
        Returns:
            마크다운 형식의 별도 보도 준칙 텍스트
        """
        result = []
        
        for topic_key in detected_topics:
            config = SPECIAL_GUIDELINES_KEYWORDS.get(topic_key)
            if config:
                header = f"\n\n---\n## ⚠️ 자동 감지된 별도 보도 준칙: {config['guideline_name']}\n(기사 내용에서 관련 키워드가 감지되어 자동 포함됨)\n"
                result.append(header + config['guideline_text'])
        
        return "\n".join(result)

    def get_relevant_content(self, categories: List[str], article_content: str = "") -> str:
        """
        기존 analyzer.py 호환용 메서드 (v2.0: 키워드 기반 별도 준칙 자동 포함)
        
        Args:
            categories: 카테고리 이름 목록 (예: ["1. 진실성과 정확성"])
            article_content: 기사 제목 + 본문 (키워드 감지용, v2.0 추가)
            
        Returns:
            관련 평가 기준 및 윤리규범 텍스트 + 별도 보도 준칙
        """
        # 카테고리 이름에서 ID 추출
        issue_ids = []
        for cat_name in categories:
            # "1. 진실성과 정확성" → "1-1", "1-2", ... 형태의 ID 추출
            for category in self.checklist.get('categories', []):
                if category['name'] in cat_name or cat_name.startswith(category['id']):
                    for sub in category.get('subcategories', []):
                        issue_ids.append(sub['id'])
        
        if not issue_ids:
            # 전체 카테고리 분석 요청인 경우
            base_text = self._get_full_criteria_text()
        else:
            criteria_text = self.get_criteria_by_ids(issue_ids)
            ethics_text = self.get_ethics_context(issue_ids)
            base_text = f"## 평가 기준\n{criteria_text}\n\n## 관련 윤리규범\n{ethics_text}"
        
        # v2.0: 키워드 기반 별도 보도 준칙 자동 포함
        if article_content:
            detected_topics = self.detect_special_topics(article_content)
            if detected_topics:
                special_text = self.get_special_guidelines_text(detected_topics)
                base_text += special_text
        
        return base_text
    
    def _get_full_criteria_text(self) -> str:
        """전체 평가 기준 텍스트 반환 (간략 버전)"""
        lines = ["## 전체 평가 기준"]
        
        for category in self.checklist.get('categories', []):
            lines.append(f"\n### {category['id']}. {category['name']}")
            for sub in category.get('subcategories', []):
                lines.append(f"- {sub['id']}. {sub['name']}")
        
        return "\n".join(lines)


# 테스트용
if __name__ == "__main__":
    cm = CriteriaManager()
    
    print("\n=== Red Flag 스크리닝 테스트 ===")
    test_text = "정부 고위 관계자에 따르면 이번 정책은 실패한 것으로 알려졌다."
    result = cm.pre_screen_red_flags(test_text)
    print(f"탐지된 Red Flag: {len(result['flagged_items'])}개")
    print(f"관련 카테고리: {result['flagged_ids']}")
    
    print("\n=== 진단 체크리스트 (일부) ===")
    checklist = cm.get_diagnostic_checklist()
    print(checklist[:1000] + "...")
    
    print("\n=== 윤리규범 컨텍스트 ===")
    ethics = cm.get_ethics_context(['1-1-1', '1-2-1'])
    print(ethics[:500] + "...")
