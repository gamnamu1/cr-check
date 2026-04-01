# backend/core/report_generator.py
"""
CR-Check — Sonnet 3종 리포트 생성 모듈

파이프라인 후반부 (M6):
1. 확정 패턴 ID → get_ethics_for_patterns() RPC → 규범 원문 조회
2. Sonnet 호출 — 3종 리포트(comprehensive, journalist, student) + article_analysis
3. 결정론적 인용 (<cite ref="{code}"/> 태그 → CitationResolver에서 원문 치환)
"""

import os
import re
import json
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

from .db import _get_supabase_config

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

SONNET_MODEL = "claude-sonnet-4-20250514"


# ── 데이터 구조 ──────────────────────────────────────────────────

@dataclass
class EthicsReference:
    """규범 참조 정보."""
    pattern_code: str
    ethics_code: str
    ethics_title: str
    ethics_full_text: str
    ethics_tier: int
    relation_type: str
    strength: str
    reasoning: str


@dataclass
class ReportResult:
    """리포트 생성 결과."""
    reports: dict[str, str] = field(default_factory=dict)
    # { "comprehensive": "...", "journalist": "...", "student": "..." }
    article_analysis: dict = field(default_factory=dict)
    # { "articleType": "...", "articleElements": "...", ... }
    ethics_refs: list[EthicsReference] = field(default_factory=list)
    sonnet_raw_response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


# ── 규범 조회 ────────────────────────────────────────────────────

def fetch_ethics_for_patterns(
    pattern_ids: list[int],
    sb_url: str,
    sb_key: str,
) -> list[EthicsReference]:
    """get_ethics_for_patterns() RPC 호출."""
    if not pattern_ids:
        return []

    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }

    r = httpx.post(
        f"{sb_url}/rest/v1/rpc/get_ethics_for_patterns",
        headers=headers,
        json={"confirmed_pattern_ids": pattern_ids},
        timeout=30,
    )
    r.raise_for_status()

    refs = []
    for row in r.json():
        refs.append(EthicsReference(
            pattern_code=row.get("pattern_code", ""),
            ethics_code=row.get("ethics_code", ""),
            ethics_title=row.get("ethics_title", ""),
            ethics_full_text=row.get("ethics_full_text", ""),
            ethics_tier=row.get("ethics_tier", 0),
            relation_type=row.get("relation_type", ""),
            strength=row.get("strength", ""),
            reasoning=row.get("reasoning", ""),
        ))

    # 방어적 로깅: 패턴이 있는데 규범이 없으면 경고
    if not refs and pattern_ids:
        logger.warning(
            f"확정 패턴 {pattern_ids}에 연결된 규범이 없음. "
            f"pattern_ethics_relations 또는 is_citable/is_active 확인 필요."
        )

    return refs


def _build_ethics_context(refs: list[EthicsReference]) -> str:
    """규범 컨텍스트를 tier 역순(구체→포괄)으로 정렬하여 텍스트 생성."""
    sorted_refs = sorted(refs, key=lambda x: (-x.ethics_tier, x.ethics_code))

    seen = set()
    lines = []
    for ref in sorted_refs:
        if ref.ethics_code in seen:
            continue
        seen.add(ref.ethics_code)
        lines.append(
            f"[코드: {ref.ethics_code}] [Tier {ref.ethics_tier}] {ref.ethics_title}\n"
            f"원문: {ref.ethics_full_text}"
        )

    return "\n\n".join(lines)


# ── Sonnet 프롬프트 (M6 — 3종 리포트) ──────────────────────────

_SONNET_SYSTEM_PROMPT = """\
당신은 한국 신문윤리위원회 수준의 저널리즘 비평 전문가입니다.
주어진 기사를 분석하여 3가지 독자 유형에 맞는 평가 리포트와 기사 메타분석을 작성합니다.

## 핵심 원칙

### 1. CR-Check 포지셔닝
CR-Check는 저널리즘 비평의 **관점을 제시하는 도구**입니다.
점수, 등급, 순위를 부여하지 않습니다. 서술형으로만 분석합니다.

### 2. 결정론적 인용 (절대 규칙)
윤리규범을 인용할 때 **원문을 직접 타이핑하지 마세요**.
대신 <cite ref="{ethics_code}"/> 태그만 삽입하세요.
시스템이 자동으로 DB에서 정확한 원문을 삽입합니다.

예시:
- ✅ 올바름: 언론윤리헌장 제4조는 <cite ref="JEC-0401"/>고 명시합니다.
- ❌ 금지: 언론윤리헌장 제4조는 "사회적으로 중요한 사안이나..."고 명시합니다.
- ✅ 올바름: 신문윤리실천요강 제3조 2항은 <cite ref="JCE-0302"/>고 규정합니다.

### 3. 규범 인용 롤업 선택적 적용 원칙
- 각 문제점에 대해 **가장 직접적으로 관련된 구체적 조항 하나**를 인용하세요.
- 매 문제마다 하위→중위→상위 규범을 나열하지 마세요.
- 단, 여러 문제점이 하나의 상위 원칙으로 수렴하는 경우에 한해,
  종합 평가에서 "구체적 규범 → 포괄적 원칙" 순서로 계층 인용을 사용하세요.

### 4. 3종 리포트 톤 차이
동일한 분석 내용을 **독자에 맞는 톤과 깊이**로 작성합니다:

- **comprehensive** (시민용): 일반 시민이 이해할 수 있는 친근한 어투. 왜 이것이 문제인지를 일상적 비유나 구체적 예시로 설명. 종합 평가와 개선 제안 포함.
- **journalist** (기자용): 동료 전문가에게 말하듯 전문적이면서도 건설적인 어투. "시민 주도 CR 프로젝트를 통해 기자님의 기사를 평가했습니다"로 시작. 구체적 개선안 제시. 기자의 노력을 인정하되 정확한 비판.
- **student** (학생용): 교육적 목적. 쉬운 비유("학교에서 친구와 싸웠을 때..."), 질문 형식 유도, 비판적 읽기 연습 안내. "여러분"이라는 호칭.

### 5. 1차 분석 결과 활용
아래에 제공되는 "1차 분석 결과"에는 overall_assessment(양질 근거와 문제 근거를 모두 검토한 판단)가 포함되어 있습니다.
이 판단을 참고하여 리포트의 톤과 종합 평가를 자연스럽게 결정하세요.
리포트에 overall_assessment를 그대로 인용하지 말고, 내용을 자연스럽게 녹이거나 불필요하면 제외하세요.

## 출력 형식

반드시 아래 JSON 형식으로만 응답하세요. JSON 외 다른 텍스트를 포함하지 마세요.

```json
{
  "article_analysis": {
    "articleType": "기사 유형 (예: 정치인 발언 보도, 정치 심층보도, 사건사고 보도 등)",
    "articleElements": "기사 구성 요소 (예: 정치인 SNS 발언 중심, 사건 배경 설명, 기자 서술 등)",
    "editStructure": "편집 구조 (예: 역피라미드, 서사형 등)",
    "reportingMethod": "취재 방식 (예: SNS 발언 재인용, 현장 취재, 당사자 미취재 등)",
    "contentFlow": "내용 흐름 (예: 발언 전면 배치 → 배경 → 추가 발언 등)"
  },
  "reports": {
    "comprehensive": "시민을 위한 종합 리포트 전문 (마크다운 가능)",
    "journalist": "기자를 위한 전문 리포트 전문 (마크다운 가능)",
    "student": "학생을 위한 교육 리포트 전문 (마크다운 가능)"
  }
}
```

## 주의사항
- 제공된 규범 컨텍스트에 있는 코드만 cite 태그로 인용하세요. 없는 코드를 만들지 마세요.
- 점수, 등급, 순위 부여 절대 금지. 서술형 평가만.
- 한국어로 작성하세요.
- article_analysis의 각 필드를 반드시 채우세요.
- 3종 리포트 모두 반드시 포함하세요. 누락 시 재시도됩니다.
"""


# ── [LEGACY] M4 프롬프트 (비교용 보존) ──────────────────────────

_SONNET_SYSTEM_PROMPT_LEGACY = """\
당신은 한국 신문윤리위원회 수준의 상세 분석 보고서를 작성하는 전문가입니다.

## 핵심 규칙: 결정론적 인용
규범을 인용할 때 원문을 직접 작성하지 마세요.
대신 <cite ref="{ethics_code}"/> 태그만 삽입하세요.
시스템이 자동으로 정확한 원문을 삽입합니다.

## 보고서 구조
각 위반 사항에 대해:
1. 구체적 문장 인용 + 문제점 설명
2. 관련 규범: <cite ref="{ethics_code}"/> 태그로 삽입 (구체적 규범→포괄적 원칙 순)
3. 종합 평가 및 개선 제안

## 주의사항
- 제공된 규범 컨텍스트에 있는 코드만 인용하세요
- 규범 원문을 직접 타이핑하지 마세요 — cite 태그만 사용
- 한국어로 작성하세요"""


# ── JSON 파싱 유틸 ──────────────────────────────────────────────

def _robust_json_parse(text: str) -> dict:
    """마크다운 코드블록 제거 + JSON 추출."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON 객체를 찾을 수 없음")

    return json.loads(text[start : end + 1])


# ── Sonnet 호출 ──────────────────────────────────────────────────

def call_sonnet(
    article_text: str,
    detections_json: str,
    overall_assessment: str,
    ethics_context: str,
    meta_pattern_block: str = "",
) -> tuple[str, int, int]:
    """Sonnet을 호출하여 3종 리포트 생성. (raw_text, input_tokens, output_tokens)."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_message = f"""## 1차 분석 결과 (Sonnet Solo 패턴 식별)

### 종합 판단
{overall_assessment}

### 탐지된 패턴
{detections_json}

## 관련 윤리규범 (확정 패턴에 연결된 규범, DB 조회 결과)
{ethics_context}
"""

    # 메타 패턴 발동 시에만 블록 추가
    if meta_pattern_block:
        user_message += f"\n{meta_pattern_block}\n"

    user_message += f"""
## 기사 전문
{article_text}"""

    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=10000,
        system=_SONNET_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
    )

    report = response.content[0].text
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    return report, in_tok, out_tok


# ── 메인 함수 ────────────────────────────────────────────────────

def _build_meta_pattern_block(meta_patterns: list) -> str:
    """메타 패턴 발동 시 Sonnet 프롬프트에 주입할 블록을 생성."""
    if not meta_patterns:
        return ""

    blocks = []
    for mp in meta_patterns:
        blocks.append(f"""메타 패턴: {mp.meta_pattern_name} ({mp.meta_pattern_code})
- 충족된 필수 지표: {mp.required_matches}
- 충족된 보강 지표: {mp.supporting_matches}
- 사전 확신도: {mp.confidence}""")

    return f"""## 구조적 문제 분석 지시 (메타 패턴 추론)

아래 패턴들이 이 기사에서 탐지되어, 메타 패턴 추론 조건이 충족되었습니다.

{chr(10).join(blocks)}

3종 리포트 각각에서, 종합 평가 직전에 "구조적 문제 분석" 섹션을 작성하세요.

### 표현 수위 가이드라인 (절대 준수)
- 확신도 low → "일부 징후가 관찰됩니다"
- 확신도 medium → "구조적 문제의 가능성이 있습니다"
- 확신도 high → "강한 의심이 됩니다"
- ❌ 절대 금지: "외부 압력이 있었다", "상업적 동기로 작성되었다" 등 단정적 표현
  → CR-Check는 "관점을 제시하는 도구"입니다. 확정 판단을 내리지 않습니다.

### 3종 톤 차이
- comprehensive(시민용): "이런 징후가 보입니다" — 쉬운 비유로 설명
- journalist(기자용): "구조적 관점에서 검토가 필요합니다" — 건설적 제안
- student(학생용): "이런 점을 생각해볼까요?" — 질문 형식 유도"""


def generate_report(
    article_text: str,
    pattern_ids: list[int],
    detections: list[dict],
    overall_assessment: str = "",
    meta_patterns: list = None,
) -> ReportResult:
    """확정 패턴으로 규범 조회 후 Sonnet 3종 리포트 생성.

    Args:
        article_text: 기사 전문
        pattern_ids: 밸리데이션 통과한 패턴 ID 리스트
        detections: Sonnet Solo 확정 결과 (dict 리스트)
        overall_assessment: Devil's Advocate CoT 판단 (컨텍스트용)
        meta_patterns: 발동된 MetaPatternResult 리스트 (optional)

    Returns:
        ReportResult (3종 리포트 + article_analysis)
    """
    sb_url, sb_key = _get_supabase_config()

    # 1. 규범 조회
    ethics_refs = fetch_ethics_for_patterns(pattern_ids, sb_url, sb_key)
    ethics_context = _build_ethics_context(ethics_refs)

    # 2. detections JSON 문자열
    detections_json = json.dumps(detections, ensure_ascii=False, indent=2)

    # 2.5 메타 패턴 프롬프트 블록 (조건부)
    meta_block = _build_meta_pattern_block(meta_patterns or [])

    # 3. Sonnet 호출 (3종 JSON 반환) + 재시도 로직
    max_retries = 3

    for attempt in range(max_retries):
        try:
            raw_text, in_tok, out_tok = call_sonnet(
                article_text, detections_json, overall_assessment, ethics_context,
                meta_pattern_block=meta_block,
            )
            result_json = _robust_json_parse(raw_text)

            # 구조 검증
            if "reports" not in result_json:
                raise ValueError("'reports' 키 누락")
            reports = result_json["reports"]
            for report_field in ["comprehensive", "journalist", "student"]:
                if report_field not in reports or not reports[report_field]:
                    raise ValueError(f"필수 리포트 '{report_field}' 누락 또는 빈 값")

            article_analysis = result_json.get("article_analysis", {})

            return ReportResult(
                reports=reports,
                article_analysis=article_analysis,
                ethics_refs=ethics_refs,
                sonnet_raw_response=raw_text,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
        except Exception as e:
            logger.warning(f"리포트 생성 시도 {attempt+1}/{max_retries} 실패 ({type(e).__name__}): {e}")
            if attempt == max_retries - 1:
                raise ValueError(f"리포트 생성 최종 실패: {e}")
            time.sleep(2 ** attempt)  # exponential backoff
