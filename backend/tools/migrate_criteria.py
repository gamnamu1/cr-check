#!/usr/bin/env python3
"""
CR 프로젝트 - 평가 기준 마이그레이션 스크립트

이 스크립트는 `current-criteria_v2_active.md` 마크다운 파일을 파싱하여
Two-Layer 아키텍처에 필요한 두 개의 JSON 파일을 생성합니다:
1. criteria_checklist.json: 진단용 체크리스트 (질문 + Red Flag)
2. ethics_library.json: 윤리규범 원문 라이브러리 (인용 전용)

Usage:
    python migrate_criteria.py

Output:
    ../data/criteria_checklist.json
    ../data/ethics_library.json
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


def parse_criteria_markdown(md_content: str) -> Dict[str, Any]:
    """
    마크다운 파일을 파싱하여 구조화된 데이터로 변환
    """
    result = {
        "version": "2.0",
        "categories": []
    }
    
    lines = md_content.split('\n')
    
    current_category = None
    current_subcategory = None
    current_item = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # ## **1-1. 진실성과 정확성** 형태의 카테고리 헤더
        category_match = re.match(r'^##\s*\*\*(\d+-\d+)\.\s*(.+?)\*\*', line)
        if category_match:
            category_id = category_match.group(1)
            category_name = category_match.group(2).strip()
            current_category = {
                "id": category_id,
                "name": category_name,
                "subcategories": []
            }
            result["categories"].append(current_category)
            i += 1
            continue
        
        # ### **1-1-1. 사실 검증 부실** 형태의 서브카테고리 헤더
        subcategory_match = re.match(r'^###\s*\*\*(\d+-\d+-\d+)\.\s*(.+?)\*\*', line)
        if subcategory_match and current_category:
            subcategory_id = subcategory_match.group(1)
            subcategory_name = subcategory_match.group(2).strip()
            current_subcategory = {
                "id": subcategory_id,
                "name": subcategory_name,
                "definition": "",
                "severity": "major",  # 기본값
                "diagnostic_questions": [],
                "red_flags": [],
                "ethics_code_refs": []
            }
            current_category["subcategories"].append(current_subcategory)
            current_item = None
            i += 1
            continue
        
        # - **항목명** : 설명 형태의 항목
        item_match = re.match(r'^-\s*\*\*(.+?)\*\*\s*[:：]?\s*(.*)$', line)
        if item_match and current_subcategory:
            item_name = item_match.group(1).strip()
            item_desc = item_match.group(2).strip()
            
            # 이 항목을 진단 질문으로 변환
            question = generate_diagnostic_question(item_name, item_desc)
            if question:
                current_subcategory["diagnostic_questions"].append({
                    "q_id": f"{current_subcategory['id']}-{len(current_subcategory['diagnostic_questions']) + 1}",
                    "question": question,
                    "weight": 0.5
                })
            
            # Red Flag 키워드 추출
            red_flags = extract_red_flags(item_name, item_desc)
            current_subcategory["red_flags"].extend(red_flags)
            
            # definition이 비어있으면 첫 항목 설명으로 설정
            if not current_subcategory["definition"] and item_desc:
                current_subcategory["definition"] = item_desc[:200]
            
            i += 1
            continue
        
        # 심각도 설정 (critical 키워드가 포함된 경우)
        if current_subcategory and any(kw in line.lower() for kw in ['critical', '심각', '중대']):
            current_subcategory["severity"] = "critical"
        
        i += 1
    
    # Red Flag 중복 제거
    for category in result["categories"]:
        for sub in category["subcategories"]:
            sub["red_flags"] = list(set(sub["red_flags"]))[:10]  # 상위 10개만 유지
    
    return result


def generate_diagnostic_question(item_name: str, item_desc: str) -> str:
    """
    항목명과 설명에서 진단 질문 생성
    """
    # 질문 형태로 변환
    question_patterns = {
        "익명": "익명 취재원을 남용하거나 설명 없이 사용했는가?",
        "단일 취재원": "단일 취재원에만 의존하여 보도했는가?",
        "반론": "비판 대상에게 반론 기회를 충분히 제공했는가?",
        "따옴표": "취재원 발언을 무비판적으로 인용(따옴표 저널리즘)했는가?",
        "보도자료": "보도자료를 검증 없이 받아쓰기했는가?",
        "추측": "추측이나 의견을 사실처럼 표현했는가?",
        "과장": "사실을 과장하거나 왜곡했는가?",
        "편향": "특정 입장만 일방적으로 대변했는가?",
        "낚시": "본문과 다른 자극적인 제목을 사용했는가?",
        "통계": "통계나 데이터를 오용하거나 왜곡했는가?",
        "피해자": "피해자의 인권이나 프라이버시를 침해했는가?",
        "무죄추정": "무죄추정의 원칙을 위반했는가?",
        "차별": "차별적이거나 혐오적인 표현을 사용했는가?",
    }
    
    for keyword, question in question_patterns.items():
        if keyword in item_name or keyword in item_desc:
            return question
    
    # 기본 질문 생성
    if item_name:
        return f"'{item_name}' 문제가 있는가?"
    return None


def extract_red_flags(item_name: str, item_desc: str) -> List[str]:
    """
    항목에서 Red Flag 키워드 추출
    """
    red_flags = []
    combined = f"{item_name} {item_desc}"
    
    # 따옴표 안의 예시 표현 추출
    quoted_patterns = re.findall(r'["\'\u201c\u201d\u2018\u2019]([^"\'\u201c\u201d\u2018\u2019]+)["\'\u201c\u201d\u2018\u2019]', combined)
    for pattern in quoted_patterns:
        if len(pattern) < 30 and len(pattern) > 3:  # 적당한 길이의 표현만
            red_flags.append(pattern.strip())
    
    # 일반적인 Red Flag 패턴
    common_flags = [
        "관계자에 따르면",
        "로 알려졌다",
        "로 전해졌다",
        "로 전망된다",
        "로 관측된다",
        "라는 후문이다",
        "소식통에 의하면",
        "것으로 보인다",
        "연락이 닿지 않았다",
        "답변을 거부했다",
        "충격",
        "경악",
        "발칵",
        "분노",
        "폭탄 선언",
    ]
    
    for flag in common_flags:
        if flag in combined:
            red_flags.append(flag)
    
    return red_flags


def create_ethics_library() -> Dict[str, Any]:
    """
    기본 윤리규범 라이브러리 생성
    (실제 규범 전문은 별도로 수집 필요)
    """
    return {
        "codes": {
            # 신문윤리실천요강
            "newspaper_ethics_practice_3_1": {
                "source": "신문윤리실천요강",
                "article": "제3조",
                "clause": "1항",
                "title": "사실의 보도",
                "full_text": "기자는 취재에 임해 항상성실하게 사실을 파악해야 하며, 그 결과를 정확히 보도해야 한다.",
                "keywords": ["사실", "정확", "보도"]
            },
            "newspaper_ethics_practice_3_2": {
                "source": "신문윤리실천요강",
                "article": "제3조",
                "clause": "2항",
                "title": "확인보도 원칙",
                "full_text": "보도 기사의 사실 여부는 확인되어야 하며, 확인되지 않은 사실을 보도할 때는 그러한 사정을 밝혀야 한다.",
                "keywords": ["확인", "사실", "검증"]
            },
            "newspaper_ethics_practice_3_4": {
                "source": "신문윤리실천요강",
                "article": "제3조",
                "clause": "4항",
                "title": "미확인보도 명시",
                "full_text": "출처가 분명하지 않거나 확인되지 않은 사실을 부득이 보도할 때는 그 사유를 분명히 밝혀야 한다.",
                "keywords": ["출처", "확인", "명시"]
            },
            "newspaper_ethics_practice_3_9": {
                "source": "신문윤리실천요강",
                "article": "제3조",
                "clause": "9항",
                "title": "피의사실 보도",
                "full_text": "신문은 범죄의 피의자 또는 피고인에 대한 보도를 할 때 무죄추정의 원칙을 존중해야 하며, 피의자 측에게 해명의 기회를 주기 위해 최선을 다해야 한다.",
                "keywords": ["무죄추정", "피의자", "해명기회"]
            },
            "newspaper_ethics_practice_10_1": {
                "source": "신문윤리실천요강",
                "article": "제10조",
                "clause": "1항",
                "title": "제목의 정확성",
                "full_text": "기사의 제목은 기사 내용을 정확하게 반영해야 하며, 과장하거나 왜곡해서는 안 된다.",
                "keywords": ["제목", "정확", "과장"]
            },
            # 언론윤리헌장
            "journalism_ethics_charter_1": {
                "source": "언론윤리헌장",
                "article": "제1조",
                "clause": None,
                "title": "진실 보도",
                "full_text": "언론인은 모든 정보를 성실하게 검증하고 명확한 근거를 바탕으로 보도한다.",
                "keywords": ["검증", "근거", "진실"]
            },
            "journalism_ethics_charter_2": {
                "source": "언론윤리헌장",
                "article": "제2조",
                "clause": None,
                "title": "공정한 보도",
                "full_text": "언론인은 뉴스와 사실에 근거한 해설을 의견과 명백하게 분리하여 보도한다.",
                "keywords": ["공정", "사실", "의견분리"]
            },
            "journalism_ethics_charter_4": {
                "source": "언론윤리헌장",
                "article": "제4조",
                "clause": None,
                "title": "인권 보호",
                "full_text": "언론인은 인간의 존엄성과 개인의 명예를 존중하고 취재보도 과정에서 사생활의 자유와 비밀을 침해하지 않는다.",
                "keywords": ["인권", "명예", "사생활"]
            },
            "journalism_ethics_charter_9": {
                "source": "언론윤리헌장",
                "article": "제9조",
                "clause": None,
                "title": "디지털 환경의 책임",
                "full_text": "언론인은 디지털 환경에서 클릭 유도를 위한 선정적 제목이나 과장된 표현을 자제한다.",
                "keywords": ["디지털", "클릭", "선정적"]
            },
            # 한국기자협회 윤리강령
            "kja_ethics_1": {
                "source": "한국기자협회 윤리강령",
                "article": "제1조",
                "clause": None,
                "title": "진실 추구",
                "full_text": "기자는 진실을 추구하며, 정확하고 공정하게 보도해야 한다.",
                "keywords": ["진실", "정확", "공정"]
            },
            "kja_ethics_3": {
                "source": "한국기자협회 윤리강령",
                "article": "제3조",
                "clause": None,
                "title": "취재원 보호",
                "full_text": "기자는 취재원의 신뢰를 저버려서는 안 되며, 익명 보도 시에도 최소한의 정보를 제공해야 한다.",
                "keywords": ["취재원", "익명", "보호"]
            },
        }
    }


def map_ethics_codes(subcategory_id: str) -> List[str]:
    """
    서브카테고리 ID에 따라 관련 윤리규범 ID 매핑
    """
    mappings = {
        "1-1-1": ["newspaper_ethics_practice_3_2", "newspaper_ethics_practice_3_4", "journalism_ethics_charter_1"],
        "1-1-2": ["newspaper_ethics_practice_3_1", "newspaper_ethics_practice_3_2"],
        "1-1-3": ["newspaper_ethics_practice_3_1"],
        "1-1-4": ["journalism_ethics_charter_2"],
        "1-1-5": ["newspaper_ethics_practice_3_1", "journalism_ethics_charter_1"],
        "1-2-1": ["kja_ethics_3", "newspaper_ethics_practice_3_4"],
        "1-2-2": ["journalism_ethics_charter_2"],
        "1-2-3": ["kja_ethics_1"],
        "1-3-1": ["journalism_ethics_charter_2"],
        "1-3-2": ["journalism_ethics_charter_2"],
        "1-3-3": ["journalism_ethics_charter_1"],
        "1-3-4": ["journalism_ethics_charter_2"],
        "1-3-5": ["journalism_ethics_charter_2"],
        "1-5-1": ["journalism_ethics_charter_4"],
        "1-5-2": ["journalism_ethics_charter_4"],
        "1-5-3": ["journalism_ethics_charter_4"],
        "1-5-4": ["newspaper_ethics_practice_3_9", "journalism_ethics_charter_4"],
        "1-7-1": ["journalism_ethics_charter_2"],
        "1-7-2": ["newspaper_ethics_practice_10_1", "journalism_ethics_charter_9"],
        "1-7-3": ["newspaper_ethics_practice_10_1", "journalism_ethics_charter_9"],
        "1-7-4": ["newspaper_ethics_practice_10_1"],
        "1-7-5": ["journalism_ethics_charter_4"],
        "1-7-6": ["journalism_ethics_charter_1"],
        "1-8-1": ["journalism_ethics_charter_9"],
        "1-8-2": ["journalism_ethics_charter_9"],
    }
    return mappings.get(subcategory_id, ["journalism_ethics_charter_1"])


def main():
    """메인 실행 함수"""
    # 경로 설정
    script_dir = Path(__file__).parent
    docs_dir = script_dir.parent.parent / "docs"
    data_dir = script_dir.parent / "data"
    
    # 입력 파일 경로
    criteria_md_path = docs_dir / "current-criteria_v2_active.md"
    
    # 출력 파일 경로
    checklist_json_path = data_dir / "criteria_checklist.json"
    ethics_json_path = data_dir / "ethics_library.json"
    
    print(f"📂 입력 파일: {criteria_md_path}")
    print(f"📂 출력 디렉토리: {data_dir}")
    
    # 마크다운 파일 읽기
    if not criteria_md_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {criteria_md_path}")
        return
    
    with open(criteria_md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print(f"✅ 마크다운 파일 로드 완료 ({len(md_content):,} bytes)")
    
    # 1. 평가 기준 체크리스트 생성
    print("\n🔄 평가 기준 체크리스트 생성 중...")
    checklist = parse_criteria_markdown(md_content)
    
    # 윤리규범 ID 매핑 추가
    for category in checklist["categories"]:
        for sub in category["subcategories"]:
            sub["ethics_code_refs"] = map_ethics_codes(sub["id"])
    
    with open(checklist_json_path, 'w', encoding='utf-8') as f:
        json.dump(checklist, f, ensure_ascii=False, indent=2)
    
    # 통계 출력
    total_categories = len(checklist["categories"])
    total_subcategories = sum(len(cat["subcategories"]) for cat in checklist["categories"])
    total_questions = sum(
        len(sub["diagnostic_questions"])
        for cat in checklist["categories"]
        for sub in cat["subcategories"]
    )
    
    print(f"✅ 체크리스트 생성 완료:")
    print(f"   - 대분류: {total_categories}개")
    print(f"   - 소분류: {total_subcategories}개")
    print(f"   - 진단 질문: {total_questions}개")
    print(f"   - 저장 위치: {checklist_json_path}")
    
    # 2. 윤리규범 라이브러리 생성
    print("\n🔄 윤리규범 라이브러리 생성 중...")
    ethics_library = create_ethics_library()
    
    with open(ethics_json_path, 'w', encoding='utf-8') as f:
        json.dump(ethics_library, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 윤리규범 라이브러리 생성 완료:")
    print(f"   - 규범 조항: {len(ethics_library['codes'])}개")
    print(f"   - 저장 위치: {ethics_json_path}")
    
    print("\n🎉 마이그레이션 완료!")


if __name__ == "__main__":
    main()
