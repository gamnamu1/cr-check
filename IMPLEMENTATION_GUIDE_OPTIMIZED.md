# CR-Check 프로토타입 구현 전략 (최적화 버전 v2)

> **실전 배포 검증 기반 개선 설계도**
> 초기 구현에서 발생한 문제점(프롬프트 크기, JSON 파싱, 배포 환경, 성능)을 근본적으로 해결하고, 언론윤리규범 기반 평가 원칙을 명확히 한 최적화 버전입니다.

---

## 📋 목차

1. [개요 및 핵심 철학](#1-개요-및-핵심-철학)
2. [실전 배포에서 발견된 문제점 및 해결 방안](#2-실전-배포에서-발견된-문제점-및-해결-방안)
3. [최적화된 아키텍처 설계](#3-최적화된-아키텍처-설계)
4. [핵심: 프롬프트 최적화 전략](#4-핵심-프롬프트-최적화-전략)
5. [평가 로직 완전한 구현 코드](#5-평가-로직-완전한-구현-코드)
6. [리포트 형식 및 구조 가이드](#6-리포트-형식-및-구조-가이드)
7. [배포 환경별 최적화](#7-배포-환경별-최적화)
8. [단계별 구현 로드맵](#8-단계별-구현-로드맵)
9. [품질 관리 및 테스트](#9-품질-관리-및-테스트)

---

## 1. 개요 및 핵심 철학

### 1.1 프로젝트 목적

CR-Check는 한국 언론 기사의 저널리즘 윤리 준수 여부를 **한국신문윤리위원회 윤리규범을 근거로** 정성적으로 분석하는 자동화 도구입니다.

**핵심 가치**:

- 📜 **윤리규범 기반**: 한국기자협회 윤리강령, 신문윤리실천요강 등 **공인된 윤리규범을 근거**로 평가
- 🎯 **평가 품질 최우선**: 정확하고 신뢰할 수 있는 기사 분석
- 💬 **서술형 평가**: 점수나 등급 없이 구체적 근거와 개선 방안 제시
- 👥 **3가지 관점**: 일반 시민, 기자, 학생을 위한 맞춤형 리포트
- 📄 **편리한 공유**: PDF 다운로드 및 저장 기능
- 🔒 **저작권 보호**: 기사 URL만 표시, 원문 미게재

### 1.2 평가 원칙

> 🟢 **권장: 윤리규범 기반 서술형 평가**
>
> CR-Check는 다음 원칙을 따릅니다:
>
> 1. **근거 중심**: 모든 지적 사항은 한국신문윤리위원회 윤리규범을 근거로 제시합니다.
> 2. **서술형 표현**: 점수, 등급, 백분율 등 정량적 수치 대신 구체적 설명과 사례를 제공합니다.
> 3. **건설적 피드백**: 문제점 지적과 함께 개선 방향을 제안합니다.
> 4. **투명한 인용**: 기사에서 문제가 되는 부분을 직접 인용하고 분석합니다.
> 5. **맥락 고려**: 기사 유형과 취재 환경을 고려한 종합적 판단을 제공합니다.

**피해야 할 표현 예시**:
- ❌ "이 기사는 6.4/10점입니다"
- ❌ "윤리성 B등급"
- ❌ "80%의 문제가 발견되었습니다"

**권장 표현 예시**:
- ✅ "이 기사는 한국기자협회 윤리강령 제1조(진실 보도)를 위반하여..."
- ✅ "신문윤리실천요강 제2조(출처 명시)에 따르면, 취재원의 신원을 밝혀야 하나..."
- ✅ "기사에서 '~로 알려졌다'는 무주체 피동형 표현이 3회 사용되었으며, 이는..."

### 1.3 최종 결과물 표준

> 🟢 **리포트 형식 표준**
>
> 모든 리포트의 구조와 스타일은 **`docs/[샘플]평가리포트.html`** 파일을 따릅니다:
>
> **구조**:
> 1. 기사 개요 (제목, 출처, 기자, 유형, 구조)
> 2. 문제점 분석 (카테고리별 구체적 지적)
> 3. 윤리규범 위반 근거 (조항 직접 인용)
> 4. 개선 방안 (건설적 제안)
>
> **스타일**:
> - 일반 문자열로만 작성 (HTML 태그, 마크다운 문법 사용 금지)
> - 각 리포트 800-1500자 분량
> - 구체적 인용구와 함께 설명
> - 전문 용어 사용 시 쉬운 설명 병기

### 1.4 MVP 핵심 철학

**"Ethics First, Technology Second"**

기술적 편의성보다 **윤리규범 기반 평가의 정확성**을 최우선으로 합니다. AI 분석은 도구일 뿐, 근거는 항상 공인된 윤리규범에서 가져와야 합니다.

---

## 2. 실전 배포에서 발견된 문제점 및 해결 방안

### 2.1 문제점 요약

| 문제 | 원인 | 기존 해결 시도 | ❌ 결과 | ✅ 올바른 해결책 |
|------|------|---------------|--------|---------------|
| **분석 시간 3분 초과** | 147KB 프롬프트 전송 | 타임아웃만 증가 (60초→180초) | 여전히 타임아웃 빈발 | **파일 병합 + 관련 부분만 추출 (RAG)** |
| **JSON 파싱 실패** | Claude 응답 불안정 | 정규식 수정 반복 | 계속 실패 | **재귀적 괄호 매칭 파서** |
| **WeasyPrint 설치 실패** | Railway 환경 제약 | PDF 기능 완전 포기 | 기능 축소 | **Docker 이미지** |
| **리포트 품질 저하** | max_tokens 축소 (3000) | 500자 제한 추가 | 내용 부실 | **충분한 토큰 (8000+)** |
| **3개→1개 리포트** | JSON 파싱 불안정 | 기능 포기 | 설계 목표 미달성 | **안정적 파싱 + 명확한 프롬프트** |

### 2.2 핵심 개선 전략

#### ✅ 전략 1: 평가 기준 파일 통합 및 최적화

**문제**: template.md(114KB) + current-criteria.md(32KB)를 별도로 유지하여 중복 발생

**해결책**:
```python
# 1. 두 파일 병합: template.md 기준으로 current-criteria.md의 고유 내용 추가
# 2. 통합 파일 생성: unified-criteria.md (약 120KB)
# 3. 카테고리별 인덱스 생성: 빠른 검색을 위한 매핑 테이블

# backend/references/unified-criteria.md
"""
## 1. 진실성과 정확성

### 1-1. 사실 검증 부실
[current-criteria.md의 상세 내용]
- 검증 절차 생략
- 크로스 체크 부재
...

### 윤리규범 근거
[template.md의 윤리규범 조항]
- 한국기자협회 윤리강령 제1조: "진실을 추구한다..."
- 신문윤리실천요강 제1조: "신문은 진실한 보도..."
"""

# Phase 1: 카테고리 목록만 전송 (120KB → 2KB)
categories = """
1. 진실성과 정확성
2. 투명성과 책임성
3. 균형성과 공정성
...
"""

# Phase 2: 식별된 카테고리 관련 내용만 추출 (120KB → 8-15KB)
relevant_content = extract_by_category(identified_categories)
```

**효과**:
- 파일 관리 단순화 (2개 → 1개)
- 중복 제거로 실제 크기 축소 (147KB → 120KB)
- Phase 1 프롬프트: 13,000 토큰 → **800 토큰** (94% 감소)
- Phase 2 프롬프트: 관련 부분만 추출하여 효율적

#### ✅ 전략 2: 재귀적 JSON 파싱 알고리즘

**문제**: Claude가 마크다운, 설명문 포함하여 JSON 파싱 실패

**해결책**:
```python
# 1. 명확한 프롬프트 지시
prompt = f"""
## 🔴 필수 출력 형식
아래 JSON 형식으로만 응답하세요. 설명이나 마크다운 코드 블록 없이 순수 JSON만 출력하세요.

{{"comprehensive": "...", "journalist": "...", "student": "..."}}

**금지 사항**:
- 마크다운 코드 블록 (```) 사용 금지
- JSON 외 설명 문구 금지
- JSON 내부에 마크다운 문법 (#, *, _, -, 등) 사용 금지
"""

# 2. 재귀적 괄호 매칭 파서
def extract_balanced_json(text: str) -> str:
    """
    중첩된 괄호와 문자열 이스케이프를 고려한 완전한 JSON 추출
    기존 정규식의 한계 (중첩 객체 미지원) 극복
    """
    stack = []
    in_string = False
    escape_next = False
    start_idx = text.find('{')

    if start_idx == -1:
        return None

    for i in range(start_idx, len(text)):
        char = text[i]

        # 이스케이프 처리
        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        # 문자열 내부 추적
        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        # 괄호 균형 추적
        if char == '{':
            stack.append(i)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack:  # 완전한 JSON 발견
                    return text[start_idx:i+1]

    return None

# 3. 다단계 fallback
def robust_json_parse(text: str) -> dict:
    """안전한 JSON 파싱 - 3단계 시도"""
    # 1차: 원본 그대로
    try:
        return json.loads(text.strip())
    except:
        pass

    # 2차: 마크다운 제거
    cleaned = re.sub(r'```(?:json)?', '', text).strip()
    try:
        return json.loads(cleaned)
    except:
        pass

    # 3차: 재귀적 추출
    json_str = extract_balanced_json(cleaned)
    if json_str:
        # 제어 문자 정리 (문자열 내부 개행은 보존)
        json_str = re.sub(r'(?<!\\)\n', ' ', json_str)
        return json.loads(json_str)

    raise ValueError("유효한 JSON을 찾을 수 없습니다")
```

#### ✅ 전략 3: Docker 기반 배포

**문제**: WeasyPrint가 Railway 환경에서 시스템 라이브러리 부족으로 실패

**해결책 (권장): Docker 이미지**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# WeasyPrint 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**대안 A: 클라이언트 사이드 PDF**
```typescript
// frontend에서 jsPDF 사용 (서버 부담 없음)
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

async function downloadPDF(reportElement: HTMLElement) {
    const canvas = await html2canvas(reportElement);
    const pdf = new jsPDF();
    pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0);
    pdf.save('cr-check-report.pdf');
}
```

#### ✅ 전략 4: 충분한 토큰 할당

**문제**: max_tokens=3000으로 축소하여 리포트가 중간에 끊김

**해결책**:
```python
# Phase 1 (Haiku): 카테고리 목록만 출력
max_tokens=1000  # 충분함

# Phase 2 (Sonnet): 3개 리포트 + 윤리규범 인용
max_tokens=10000  # 한글 약 4000-5000자
# 각 리포트 1200-1500자 목표
```

---

## 3. 최적화된 아키텍처 설계

### 3.1 기술 스택

**Backend**:
- FastAPI (Python 3.11+)
- Anthropic Claude API
  - **Phase 1**: claude-haiku-4-5-20251001 (빠른 카테고리 식별)
  - **Phase 2**: claude-sonnet-4-5-20250929 (상세 리포트 생성)
- BeautifulSoup4 (스크래핑)
- **PDF 생성**: Docker + WeasyPrint (권장) 또는 클라이언트 사이드 jsPDF

**Frontend**:
- Next.js 14 (App Router)
- TailwindCSS
- jsPDF (PDF 생성 옵션)

**Infrastructure**:
- Vercel (Frontend)
- Railway (Docker) 또는 Render (Backend)

### 3.2 프로젝트 구조

```
cr-check/
├── backend/
│   ├── main.py                     # FastAPI 엔트리포인트
│   ├── scraper.py                  # 기사 스크래핑
│   ├── classifier.py               # 기사 유형 판단
│   ├── analyzer.py                 # ⭐ 핵심: 평가 로직
│   ├── export.py                   # PDF 생성 (WeasyPrint)
│   ├── criteria_manager.py         # 🆕 통합 평가 기준 관리
│   ├── json_parser.py              # 🆕 강화된 JSON 파싱
│   ├── requirements.txt
│   ├── Dockerfile                  # 🆕 Docker 이미지
│   └── references/
│       └── unified-criteria.md     # 🆕 통합 평가 기준 (template + current)
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── result/page.tsx
│   ├── components/
│   │   ├── ArticleInput.tsx
│   │   ├── ReportDisplay.tsx       # 3가지 리포트 아코디언
│   │   └── ActionButtons.tsx       # PDF/SNS 공유
│   └── package.json
└── docs/
    └── [샘플]평가리포트.html        # ★★★ 리포트 형식 표준
```

---

## 4. 핵심: 프롬프트 최적화 전략

### 4.1 평가 기준 파일 통합

#### 통합 프로세스

1. **template.md 분석**: 평가 절차 + 문제적 보도 관행 + 윤리규범 (1046줄)
2. **current-criteria.md 분석**: 문제적 보도 관행 상세 (257줄)
3. **중복 제거**: template.md의 "문제적 보도 관행" 섹션을 current-criteria.md의 상세 내용으로 교체
4. **윤리규범 매핑**: 각 문제 패턴에 해당하는 윤리규범 조항 연결

#### unified-criteria.md 구조

```markdown
# CR 기사 품질 평가 통합 기준

## 평가 절차
[template.md의 평가 절차 유지]

## 1. 진실성과 정확성

### 1-1. 사실 검증 부실
[current-criteria.md의 상세 내용]
- 검증 절차 생략: 정보의 정확성을 충분히 확인하지 않고 보도
- 크로스 체크 부재: ...
- 투 소스 룰 무시: ...

#### 윤리규범 근거
[template.md의 해당 조항]
- **한국기자협회 윤리강령 제1조 (진실 보도)**: "언론인은 진실을 추구하고..."
- **신문윤리실천요강 제1조**: "신문은 진실한 보도로써..."

### 1-2. 이차 자료 의존
[current-criteria.md의 상세 내용]

#### 윤리규범 근거
[template.md의 해당 조항]

...
```

### 4.2 `criteria_manager.py` 구현

```python
# backend/criteria_manager.py

from pathlib import Path
from typing import List, Dict

class CriteriaManager:
    """
    통합 평가 기준 관리 및 프롬프트 최적화
    147KB → 120KB 통합 후 → Phase별 최적화
    """

    def __init__(self):
        references_dir = Path(__file__).parent / 'references'

        # 통합 평가 기준 로드
        with open(references_dir / 'unified-criteria.md', 'r', encoding='utf-8') as f:
            self.full_criteria = f.read()

        # 카테고리 인덱스 구축
        self.category_index = self._build_category_index()

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
```

---

## 5. 평가 로직 완전한 구현 코드

### 5.1 `json_parser.py` - 재귀적 JSON 파싱

```python
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
```

### 5.2 `analyzer.py` - 최적화된 분석 로직

```python
# backend/analyzer.py

from anthropic import AsyncAnthropic
import os
from typing import Dict, List
import time
from criteria_manager import CriteriaManager
from json_parser import robust_json_parse

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

## 3가지 리포트 버전 (각 1200-1500자)

1. **comprehensive** (일반 시민용 종합 리포트)
   - 누구나 이해할 수 있는 쉬운 언어
   - 기사 개요 → 주요 문제점 → 윤리규범 위반 → 사회적 영향
   - 전문 용어 사용 시 쉬운 설명 병기

2. **journalist** (기자/작성자용 전문 리포트)
   - 전문적이고 상세한 분석
   - 구체적 개선 방안과 대안 제시
   - 유사 사례나 모범 사례 참고
   - 취재 과정 개선 제안

3. **student** (학생용 교육 리포트)
   - 학습 목적의 설명
   - "왜 문제인가?" 이유 중심 설명
   - 좋은 저널리즘의 사례 제시
   - 언론의 사회적 책임 강조

## 작성 지침

- 일반 문자열로만 작성 (HTML 태그, 마크다운 문법 금지)
- 각 리포트 1200-1500자 분량
- 문단 구분은 개행(\\n\\n) 두 번으로
- 구체적 인용구는 큰따옴표("")로 표시

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
```

---

## 6. 리포트 형식 및 구조 가이드

### 6.1 샘플 리포트 구조 분석

**docs/[샘플]평가리포트.html**의 구조:

```
1. 기사 개요
   - 제목, 출처, 기자, 기사 유형
   - 기사 요소 (분량, 단락, 사진)
   - 편집 구조, 취재 방식

2. 문제점 분석 (카테고리별)
   - 카테고리명 (예: "진실성과 정확성")
   - 구체적 문제 지적
   - 기사 원문 인용 ("")
   - 문제의 본질 설명

3. 윤리규범 위반 근거
   - 해당 조항 명시
   - 조항 원문 인용
   - 위반 사항과 연결

4. 개선 방안
   - 건설적 제안
   - 대안 제시
   - 모범 사례 참고
```

### 6.2 리포트 작성 가이드

**comprehensive (일반 시민용)**:
```
[기사 개요]
"{기사 제목}" 기사 분석

기사 개요
- 제목: ...
- 출처: ...
- 기사 유형: ...

[문제점 분석]
이 기사는 한국기자협회 윤리강령 제1조(진실 보도)와 관련하여 다음과 같은 문제가 발견되었습니다.

첫째, 사실 검증 부실 문제입니다. 기사에서 "~로 알려졌다"는 표현이 사용되었으나, 정보의 출처나 검증 과정이 명시되지 않았습니다. 신문윤리실천요강 제1조는 "신문은 진실한 보도로써 국민의 알 권리를 충족시켜야 한다"고 규정하고 있습니다.

[구체적 인용]
기사 원문: "정부 관계자에 따르면 이번 정책이 효과를 볼 것으로 예상된다"

이 문장은 두 가지 문제가 있습니다. 첫째, "정부 관계자"라는 익명 취재원을 사용하면서 그 이유나 소속을 밝히지 않았습니다. 둘째, "예상된다"는 추측성 표현으로 확인된 사실과 추측을 구분하지 않았습니다.

[개선 방안]
이러한 문제를 개선하기 위해서는...
```

**journalist (기자용)**:
```
전문적 분석과 개선 방안을 중심으로...

[취재 과정 분석]
이 기사의 취재 과정에서 복수 취재원 원칙(Two-Source Rule)이 지켜지지 않은 것으로 보입니다...

[구체적 개선안]
1. 취재원 다각화: ...
2. 크로스 체크: ...
3. 프레임 다양화: ...

[참고 사례]
뉴욕타임스의 경우 익명 취재원 사용 시 다음 원칙을 따릅니다...
```

**student (학생용)**:
```
학습 목적의 설명...

[왜 문제인가?]
언론이 "~로 알려졌다"는 표현을 사용하는 이유는 무엇일까요? ...

[좋은 저널리즘이란?]
좋은 저널리즘은 다음과 같은 특징을 갖습니다...

[언론의 사회적 책임]
언론은 단순히 정보를 전달하는 것을 넘어...
```

---

## 7. 배포 환경별 최적화

### 7.1 Docker를 사용한 Railway 배포 (권장)

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# WeasyPrint 시스템 의존성
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**railway.json**:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

### 7.2 requirements.txt (완전 버전)

```
# backend/requirements.txt
fastapi>=0.104.1,<0.120.0
anthropic>=0.18.0,<1.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
weasyprint>=60.0.0
python-multipart>=0.0.6
uvicorn>=0.24.0
```

### 7.3 Frontend 타임아웃 설정

```typescript
// frontend/components/ArticleInput.tsx

// 충분한 타임아웃 (2분)
const timeoutId = setTimeout(() => controller.abort(), 120000);

// 정확한 로딩 메시지
{isLoading && (
  <div className="mt-4 p-3 bg-blue-50 rounded-lg">
    <p className="text-sm text-blue-800 text-center">
      ⏱️ 2단계 분석 프로세스로 약 40-60초 정도 소요됩니다.
    </p>
    <p className="text-xs text-blue-600 text-center mt-1">
      Phase 1: 카테고리 식별 (5-10초) → Phase 2: 3가지 리포트 생성 (30-50초)
    </p>
  </div>
)}
```

---

## 8. 단계별 구현 로드맵

### Week 1: 백엔드 최적화

**Day 1-2: 평가 기준 통합**
- [ ] template.md와 current-criteria.md 분석
- [ ] unified-criteria.md 생성 (중복 제거, 윤리규범 매핑)
- [ ] 통합 파일 검증 (120KB 이내)

**Day 3-4: 프롬프트 최적화 모듈**
- [ ] `criteria_manager.py` 구현
- [ ] 카테고리 인덱스 구축
- [ ] Phase 1/2 프롬프트 생성 테스트

**Day 5-6: JSON 파싱 강화**
- [ ] `json_parser.py` 구현
- [ ] 재귀적 괄호 매칭 알고리즘 테스트
- [ ] 엣지 케이스 검증 (중첩 객체, 문자열 내 괄호)

**Day 7: analyzer.py 구현**
- [ ] 2단계 하이브리드 전략 통합
- [ ] 3가지 리포트 생성 검증
- [ ] 윤리규범 기반 평가 원칙 적용

### Week 2: 배포 및 프론트엔드

**Day 8-9: Docker 설정**
- [ ] Dockerfile 작성
- [ ] 로컬 Docker 빌드 테스트
- [ ] WeasyPrint 동작 확인

**Day 10-12: 프론트엔드**
- [ ] 3가지 리포트 아코디언 UI
- [ ] PDF 다운로드 버튼
- [ ] 타임아웃 120초 설정

**Day 13-14: 배포 및 테스트**
- [ ] Railway Docker 배포
- [ ] Vercel 프론트엔드 배포
- [ ] 통합 테스트 (10개 이상 실제 기사)

---

## 9. 품질 관리 및 테스트

### 9.1 성능 목표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| Phase 1 시간 | 5-10초 | 로그 타임스탬프 |
| Phase 2 시간 | 30-50초 | 로그 타임스탬프 |
| **총 분석 시간** | **40-60초** | 전체 타이머 |
| JSON 파싱 성공률 | 95% 이상 | 100회 테스트 |
| 3개 리포트 생성률 | 100% | 필수 필드 검증 |
| 타임아웃 발생률 | 5% 이하 | 프론트엔드 로그 |
| PDF 생성 성공률 | 100% | 배포 환경 테스트 |

### 9.2 통합 테스트 체크리스트

- [ ] 10개 이상의 실제 기사로 테스트
- [ ] 다양한 언론사 (네이버, 다음, 조선, 중앙, 한겨레, 경향 등)
- [ ] 다양한 기사 유형 (스트레이트, 해설, 칼럼-거부 확인)
- [ ] 다양한 길이 (500자~5000자)
- [ ] 평균 분석 시간 측정
- [ ] JSON 파싱 성공률 측정
- [ ] 3개 리포트 모두 생성 확인
- [ ] 윤리규범 인용 확인
- [ ] 점수화 패턴 없음 확인
- [ ] PDF 생성 성공 확인

---

## 10. 핵심 개선 사항 요약

### ✅ 해결된 문제

| 기존 문제 | 해결 방법 | 효과 |
|----------|----------|------|
| 분석 시간 3분 초과 | 파일 통합 + 카테고리별 추출 | **40-60초로 단축** |
| JSON 파싱 실패 | 재귀적 괄호 매칭 파서 | **95% 이상 성공률** |
| WeasyPrint 실패 | Docker 배포 | **PDF 기능 유지** |
| 리포트 품질 저하 | max_tokens=10000 | **상세 리포트 (1200-1500자)** |
| 3개→1개 리포트 축소 | 안정적 파싱 + 명확한 프롬프트 | **3개 리포트 유지** |
| 경직된 제약 조건 | 권장 사항 중심 재구성 | **유연한 평가 원칙** |
| 윤리규범 근거 부족 | 통합 파일에 조항 매핑 | **명확한 근거 제시** |

### 🎯 최종 목표 달성

- ✅ **3가지 리포트**: comprehensive, journalist, student 각 1200-1500자
- ✅ **윤리규범 기반**: 모든 평가는 한국신문윤리위원회 규범을 근거로
- ✅ **서술형 평가**: 점수/등급 없이 구체적 설명과 개선 방안
- ✅ **PDF 다운로드**: Docker로 WeasyPrint 환경 문제 해결
- ✅ **분석 시간**: 40-60초 (타임아웃 2분 이내 안정적 완료)
- ✅ **JSON 파싱**: 재귀적 파서로 95% 이상 성공률
- ✅ **파일 관리**: 2개 파일 통합으로 중복 제거 및 유지보수 용이

---

## 결론

이 최적화 버전은 **실전 배포에서 발견된 모든 문제를 근본적으로 해결**하며, **윤리규범 기반 평가 원칙을 명확히** 합니다:

### 🟢 핵심 가치

1. **윤리규범 우선**: 모든 평가는 공인된 윤리규범을 근거로
2. **서술형 평가**: 점수화 대신 구체적 설명과 건설적 피드백
3. **기술적 안정성**: 프롬프트 최적화, 강화된 파싱, Docker 배포
4. **사용자 경험**: 빠른 분석 시간 (40-60초), 3가지 관점 리포트, PDF 다운로드

### 🚀 다음 단계

이 설계도를 따라 구현하면 **기능 축소 없이** 안정적으로 작동하며, **윤리규범 기반 평가**라는 본래 목적에 충실한 CR-Check 시스템을 완성할 수 있습니다.

**"Ethics First, Technology Second"** - 기술은 도구일 뿐, 진정한 가치는 윤리규범 기반 평가에 있습니다.
