# backend/json_parser.py

import json
import re
from typing import Optional

def extract_balanced_json(text: str) -> Optional[str]:
    """
    중첩된 괄호와 문자열 이스케이프를 고려한 완전한 JSON 객체 추출

    기존 정규식 r'\{[^{}]*\}' 의 한계:
    - 중첩 객체 미지원: {"a": {"b": "c"}} → 실패
    - 문자열 내 괄호 오인: {"text": "a{b}c"} → 오작동

    개선점:
    - 재귀적 괄호 매칭으로 중첩 구조 지원
    - 문자열 경계 추적으로 괄호 오인 방지
    - 이스케이프 시퀀스 올바른 처리
    """
    start_idx = text.find('{')
    if start_idx == -1:
        return None

    stack = []
    in_string = False
    escape_next = False

    for i in range(start_idx, len(text)):
        char = text[i]

        # 이스케이프 처리
        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        # 문자열 경계 추적
        if char == '"':
            in_string = not in_string
            continue

        # 문자열 내부의 괄호는 무시
        if in_string:
            continue

        # 괄호 균형 추적
        if char == '{':
            stack.append(i)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack:  # 완전히 균형 잡힌 JSON 발견
                    return text[start_idx:i+1]

    return None


def robust_json_parse(text: str) -> dict:
    """
    안전한 JSON 파싱 - 3단계 fallback 전략

    1차 시도: 원본 텍스트 그대로 파싱
    2차 시도: 마크다운 코드 블록 제거 후 파싱
    3차 시도: 재귀적 괄호 매칭으로 JSON 추출 후 파싱
    """
    # 1차: 원본 그대로
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2차: 마크다운 코드 블록 제거
    cleaned = re.sub(r'```(?:json)?', '', text)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3차: 재귀적 괄호 매칭
    json_str = extract_balanced_json(cleaned)

    if json_str:
        try:
            # 문자열 외부의 제어 문자만 정리
            # (?<!\\)\n: 이스케이프되지 않은 개행만 매칭
            json_str = re.sub(r'(?<!\\)\n', ' ', json_str)
            json_str = re.sub(r'\s+', ' ', json_str)

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # 디버깅 정보 출력
            print(f"❌ JSON 파싱 최종 실패: {e}")
            print(f"추출된 JSON (처음 500자): {json_str[:500]}")
            raise ValueError(f"JSON 파싱 실패: {str(e)}")
    else:
        raise ValueError("텍스트에서 유효한 JSON 객체를 찾을 수 없습니다")
