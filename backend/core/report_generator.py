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

SONNET_MODEL = "claude-sonnet-4-6"


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

def _parse_ethics_rows(rows: list[dict]) -> list[EthicsReference]:
    """RPC 응답 row 리스트를 EthicsReference 리스트로 변환."""
    return [
        EthicsReference(
            pattern_code=row.get("pattern_code", ""),
            ethics_code=row.get("ethics_code", ""),
            ethics_title=row.get("ethics_title", ""),
            ethics_full_text=row.get("ethics_full_text", ""),
            ethics_tier=row.get("ethics_tier", 0),
            relation_type=row.get("relation_type", ""),
            strength=row.get("strength", ""),
            reasoning=row.get("reasoning", ""),
        )
        for row in rows
    ]


def _rpc_get_ethics(
    pattern_ids: list[int], sb_url: str, headers: dict, timeout: int = 30,
) -> tuple[list[dict], int]:
    """RPC 호출 1회 실행. (rows, http_status) 반환."""
    r = httpx.post(
        f"{sb_url}/rest/v1/rpc/get_ethics_for_patterns",
        headers=headers,
        json={"confirmed_pattern_ids": pattern_ids},
        timeout=timeout,
    )
    r.raise_for_status()
    rows = r.json()
    return rows, r.status_code


def fetch_ethics_for_patterns(
    pattern_ids: list[int],
    sb_url: str,
    sb_key: str,
) -> list[EthicsReference]:
    """get_ethics_for_patterns() RPC 호출 (1회 재시도 + 진단 쿼리)."""
    if not pattern_ids:
        return []

    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }

    logger.info(f"규범 조회 요청: pattern_ids={pattern_ids}")

    # 1차 시도
    try:
        rows, status = _rpc_get_ethics(pattern_ids, sb_url, headers)
        logger.info(f"규범 조회 응답: HTTP {status}, {len(rows)}건")
    except Exception as e:
        logger.error(f"규범 조회 1차 실패 [{type(e).__name__}]: {e}")
        # 네트워크 에러 시 2초 대기 후 1회 재시도
        time.sleep(2)
        try:
            rows, status = _rpc_get_ethics(pattern_ids, sb_url, headers)
            logger.info(f"규범 조회 재시도 성공: HTTP {status}, {len(rows)}건")
        except Exception as e2:
            logger.error(f"규범 조회 재시도도 실패 [{type(e2).__name__}]: {e2}")
            return []

    # 200이지만 0건인 경우: 재시도
    if not rows and pattern_ids:
        logger.warning(
            f"규범 조회 0건 (pattern_ids={pattern_ids}), 2초 후 재시도"
        )
        time.sleep(2)
        try:
            rows, status = _rpc_get_ethics(pattern_ids, sb_url, headers)
            logger.info(f"규범 조회 재시도 응답: HTTP {status}, {len(rows)}건")
        except Exception as e:
            logger.error(f"규범 조회 재시도 실패 [{type(e).__name__}]: {e}")

    # 재시도까지 0건이면 REST API 직접 조회 fallback
    if not rows and pattern_ids:
        logger.warning(f"RPC 0건, REST API fallback 시도: pattern_ids={pattern_ids}")
        ids_csv = ",".join(str(pid) for pid in pattern_ids)
        try:
            # pattern_ethics_relations + ethics_codes를 직접 JOIN 조회
            fb_r = httpx.get(
                f"{sb_url}/rest/v1/pattern_ethics_relations"
                f"?select="
                f"pattern_id,"
                f"patterns!inner(code),"
                f"ethics_code_id,"
                f"ethics_codes!inner(code,title,full_text,tier,is_active,is_citable),"
                f"relation_type,strength,reasoning"
                f"&pattern_id=in.({ids_csv})"
                f"&ethics_codes.is_active=eq.true"
                f"&ethics_codes.is_citable=eq.true",
                headers=headers,
                timeout=30,
            )
            fb_r.raise_for_status()
            fb_data = fb_r.json()
            if fb_data:
                logger.info(f"REST API fallback 성공: {len(fb_data)}건")
                rows = []
                for item in fb_data:
                    ec = item.get("ethics_codes", {})
                    p = item.get("patterns", {})
                    rows.append({
                        "pattern_code": p.get("code", ""),
                        "ethics_code": ec.get("code", ""),
                        "ethics_title": ec.get("title", ""),
                        "ethics_full_text": ec.get("full_text", ""),
                        "ethics_tier": ec.get("tier", 0),
                        "relation_type": item.get("relation_type", ""),
                        "strength": item.get("strength", ""),
                        "reasoning": item.get("reasoning", ""),
                    })
            else:
                logger.warning(f"REST API fallback도 0건: pattern_ids={pattern_ids}")
        except Exception as fb_e:
            logger.error(f"REST API fallback 실패 [{type(fb_e).__name__}]: {fb_e}")

    return _parse_ethics_rows(rows)


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
            f"### {ref.ethics_title} (코드: {ref.ethics_code}, Tier {ref.ethics_tier})\n"
            f"{ref.ethics_full_text}"
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

### 2. 윤리규범 인용 방식 (절대 규칙)
아래 "관련 윤리규범" 섹션에 제공된 규범 원문을 읽고, 리포트에 자연스럽게 녹여 쓰세요.

## 규범 인용 표기 규칙

윤리규범을 인용할 때 반드시 아래 형식을 따르세요:

1. 규범 조항명은 〔 〕(꺾은 대괄호)로 감싸세요.
   - 예: 〔신문윤리실천요강 제3조 1항〕, 〔언론윤리헌장 제7조〕, 〔인권보도준칙 제5조 2항〕
   - JEC-7, PCP-3-1 같은 내부 코드는 절대 사용하지 마세요.
   - 반드시 한국어 조항 표현으로 변환하세요.

2. 규범의 실제 내용을 인용할 때는 작은따옴표 ' '로 감싸세요.
   - 예: '보도기사는 사실과 의견을 명확히 구분하여 작성해야 한다'

3. 완성된 인용 형식:
   〔신문윤리실천요강 제3조 1항〕은 '보도기사는 사실과 의견을 명확히 구분하여 작성해야 한다'고 규정합니다.

4. 〔 〕 괄호는 규범 조항명에만 사용하세요. 다른 용도로 사용하지 마세요.

**추가 규칙:**
- 제공된 규범 외의 내용을 지어내지 마세요. 제공된 원문에서만 인용하세요.
- <cite> 태그를 사용하지 마세요. 모든 인용은 직접 텍스트로 작성합니다.

### 3. 규범 인용의 깊이
- 각 지적 사항에 대해 가장 직접 관련된 구체적 조항(Tier 3~4)을 인용하세요.
- 리포트 전체에서 **1~2회 정도**는 구체적 조항에서 상위 원칙(Tier 1~2)으로 의미를 확장하는 서술을 넣으세요.
  예: "이는 단순히 〔신문윤리실천요강 제3조 2항〕의 위반을 넘어, 〔언론윤리헌장 제4조〕가 천명하는 '다양한 입장을 두루 담아 균형 잡힌 시각을 보여준다'는 근본 원칙에 어긋납니다."
- 매 지적마다 하위→상위를 반복하지는 마세요. 종합 평가에서 한두 번 자연스럽게 사용하세요.

### 4. 3종 리포트 톤 차이

- **comprehensive** (시민용): 이웃에게 말하듯 자연스럽고 따뜻한 어투. 왜 이것이 우려되는지를 일상적 비유로 설명. "이 기사를 읽으면서 이런 점을 생각해보시면 좋겠습니다" 같은 톤. 절대 가르치거나 교육하려는 톤이 아닌, 함께 살펴보는 시민의 관점.
- **journalist** (기자용): "시민 주도 CR 프로젝트를 통해 기자님의 기사를 평가했습니다"로 시작. 동료 전문가에게 건설적 피드백을 주듯 구체적 개선안 제시. 기자의 노력을 인정하되 정확한 비판.
- **student** (학생용): 초등학교 4~5학년이 이해할 수 있는 눈높이로 작성.
  "여러분"이라는 호칭, 해요체("~해요", "~이에요", "~거예요", "~까요?")를
  일관되게 사용. "~합니다", "~됩니다", "~입니다" 같은 격식체는 쓰지 마세요.
  윤리규범을 인용할 때도 "~라고 정해놓았어요", "~라고 말하고 있어요"처럼
  해요체를 유지하세요. 어려운 개념은 일상적 비유로 풀어 설명하고,
  질문 형식("어떻게 생각해요?", "한번 찾아볼까요?")으로 참여를 유도하세요.
  이모지를 적절히 활용하되, 내용의 핵심을 흐리지 않을 정도로만 사용하세요.

### 5. 1차 분석 결과 활용
아래 "1차 분석 결과"의 overall_assessment를 참고하여 리포트의 관점과 종합 평가를 자연스럽게 결정하세요.
overall_assessment를 리포트에 그대로 인용하지 말고, 분석의 방향성만 참고하세요.

### 6. 서술 스타일 가이드
- 마크다운 중간제목(###)은 리포트당 최대 3~4개만 사용하세요. 과도한 구조화는 글의 자연스러움을 해칩니다.
- "문제", "문제점", "문제가 있습니다"라는 표현을 반복하지 마세요. 이미 평가를 요청한 독자에게 "문제가 있다"를 반복 강조할 필요가 없습니다. 대신 "이런 점이 눈에 띕니다", "이 부분을 살펴보겠습니다", "아쉬운 지점입니다" 등 다양한 표현을 쓰세요.
- 3종 리포트 모두, 제목(# 또는 ##)으로 시작하지 마세요.
- 곧바로 본문 첫 문장(도입부)으로 시작하세요.
- 탭 UI에 이미 리포트 유형이 표시되므로, 리포트 안에서 유형을 반복할 필요 없습니다.

## 분석 개요 작성 규칙

분석 개요의 각 항목(기사 유형, 기사 요소, 편집 구조, 취재 방식, 내용 흐름)은
시민이 "이 기사가 대략 어떤 기사인지" 파악하는 데 필요한 최소한의 정보만 담으세요.

- 각 항목은 1~2문장, 최대 80자 이내로 작성하세요.
- 나열형 설명이 아니라, 핵심만 짚는 한 줄 요약 형태로 쓰세요.
- 구체적인 인물명이나 사건 경위는 본문 리포트에서 다루면 됩니다.
  개요에서는 "익명 취재원 위주, 비판 측 편중"처럼 특징만 짚으세요.

## 출력 형식

반드시 아래 JSON 형식으로만 응답하세요. JSON 외 다른 텍스트를 포함하지 마세요.

```json
{
  "article_analysis": {
    "articleType": "기사 유형",
    "articleElements": "기사 구성 요소",
    "editStructure": "편집 구조",
    "reportingMethod": "취재 방식",
    "contentFlow": "내용 흐름"
  },
  "reports": {
    "comprehensive": "시민을 위한 종합 리포트 전문 (마크다운 가능)",
    "journalist": "기자를 위한 전문 리포트 전문 (마크다운 가능)",
    "student": "학생을 위한 교육 리포트 전문 (마크다운 가능)"
  }
}
```

## 주의사항
- 제공된 규범 컨텍스트에 있는 규범만 인용하세요. 없는 조항을 만들지 마세요.
- 점수, 등급, 순위 부여 절대 금지. 서술형 평가만.
- 한국어로 작성하세요.
- article_analysis의 각 필드를 반드시 채우세요.
- 3종 리포트 모두 반드시 포함하세요. 누락 시 재시도됩니다.
- <cite> 태그를 절대 사용하지 마세요.
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
            logger.error(
                f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
                f"[{type(e).__name__}] {e}"
            )
            if attempt == max_retries - 1:
                raise ValueError(f"리포트 생성 최종 실패: {e}")
            time.sleep(2 ** attempt)  # exponential backoff
