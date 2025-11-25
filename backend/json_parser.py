# backend/json_parser.py

import json
import re
from typing import Optional, Any, Dict, List, Union
import json_repair

def robust_json_parse(text: str) -> Union[Dict, List]:
    """
    안전한 JSON 파싱 - json_repair 라이브러리 활용
    
    LLM이 생성한 불완전한 JSON(쉼표 누락, 따옴표 오류 등)을 자동으로 복구하여 파싱합니다.
    """
    # 1. 마크다운 코드 블록 제거 (```json ... ```)
    cleaned_text = re.sub(r'```(?:json)?', '', text).strip()
    
    # 2. json_repair를 사용하여 파싱 시도
    try:
        # json_repair.loads는 불완전한 JSON을 복구하여 파싱함
        parsed = json_repair.loads(cleaned_text)
        return parsed
    except Exception as e:
        print(f"❌ json_repair 파싱 실패: {e}")
        print(f"원본 텍스트 (처음 500자): {text[:500]}")
        
        # 3. 최후의 수단: 기존의 재귀적 추출 방식 시도 (혹시 모를 경우 대비)
        # 하지만 json_repair가 대부분 처리하므로 이 단계까지 올 확률은 낮음
        try:
            return _fallback_extraction(cleaned_text)
        except Exception as fallback_error:
            raise ValueError(f"JSON 파싱 최종 실패: {str(e)}") from e

def _fallback_extraction(text: str) -> Union[Dict, List]:
    """
    json_repair도 실패했을 때를 대비한 수동 추출 로직
    """
    start_idx = text.find('{')
    if start_idx == -1:
        raise ValueError("JSON 객체 시작('{')을 찾을 수 없습니다.")
        
    # 단순 추출 시도
    try:
        return json.loads(text[start_idx:])
    except:
        pass
        
    raise ValueError("Fallback 추출 실패")
