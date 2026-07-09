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

import anthropic
import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

from .db import _get_supabase_config
from .pattern_matcher import _MANDATORY_REVIEW_TARGET_CODES

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

SONNET_MODEL = "claude-sonnet-5"


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
    # S2(2026-06-23) DB 계약 확장으로 추가된 정식 인용명 구성 요소.
    # RPC 12컬럼 응답/REST fallback 양쪽에서 채워지며,
    # 10컬럼 응답·키 누락 시에는 빈 문자열로 정규화된다.
    ethics_source: str = ""
    ethics_article_number: str = ""


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
            ethics_source=row.get("ethics_source", "") or "",
            ethics_article_number=row.get("ethics_article_number", "") or "",
        )
        for row in rows
    ]


def _rpc_get_ethics(
    pattern_ids: list[int], sb_url: str, headers: dict,
    article_context: str = 'general',
    timeout: int = 30,
) -> tuple[list[dict], int]:
    """RPC 호출 1회 실행. (rows, http_status) 반환."""
    r = httpx.post(
        f"{sb_url}/rest/v1/rpc/get_ethics_for_patterns",
        headers=headers,
        json={
            "confirmed_pattern_ids": pattern_ids,
            "article_context": article_context,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    rows = r.json()
    return rows, r.status_code


def fetch_ethics_for_patterns(
    pattern_ids: list[int],
    sb_url: str,
    sb_key: str,
    article_context: str = 'general',
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
        rows, status = _rpc_get_ethics(
            pattern_ids, sb_url, headers, article_context=article_context,
        )
        logger.info(f"규범 조회 응답: HTTP {status}, {len(rows)}건")
    except Exception as e:
        logger.error(f"규범 조회 1차 실패 [{type(e).__name__}]: {e}")
        # 네트워크 에러 시 2초 대기 후 1회 재시도
        time.sleep(2)
        try:
            rows, status = _rpc_get_ethics(
                pattern_ids, sb_url, headers, article_context=article_context,
            )
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
            rows, status = _rpc_get_ethics(
                pattern_ids, sb_url, headers, article_context=article_context,
            )
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
                f"ethics_codes!inner(code,title,source,article_number,full_text,tier,is_active,is_citable,applicable_contexts),"
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
                rows = []
                for item in fb_data:
                    ec = item.get("ethics_codes", {})
                    p = item.get("patterns", {})

                    # applicable_contexts 필터 (RPC와 동일 의미: NULL/all/일치 시만 포함)
                    contexts = ec.get("applicable_contexts")
                    if not (
                        contexts is None
                        or "all" in contexts
                        or article_context in contexts
                    ):
                        continue

                    # weak 및 exception_of 제외
                    if item.get("strength") == "weak":
                        continue
                    if item.get("relation_type") == "exception_of":
                        continue

                    rows.append({
                        "pattern_code": p.get("code", ""),
                        "ethics_code": ec.get("code", ""),
                        "ethics_title": ec.get("title", ""),
                        "ethics_full_text": ec.get("full_text", ""),
                        "ethics_tier": ec.get("tier", 0),
                        "relation_type": item.get("relation_type", ""),
                        "strength": item.get("strength", ""),
                        "reasoning": item.get("reasoning", ""),
                        "ethics_source": ec.get("source", "") or "",
                        "ethics_article_number": ec.get("article_number", "") or "",
                    })
                logger.info(f"REST API fallback 성공: {len(rows)}건 (필터링 후)")
            else:
                logger.warning(f"REST API fallback도 0건: pattern_ids={pattern_ids}")
        except Exception as fb_e:
            logger.error(f"REST API fallback 실패 [{type(fb_e).__name__}]: {fb_e}")

    return _parse_ethics_rows(rows)


def _format_ethics_header(r: EthicsReference) -> str:
    """규범 헤더: 내부 ethics_code 미노출, source+article_number 기반 정식 인용명.

    빈 값 가드: source/article_number가 둘 다 비면 〔〕 자체를 출력하지 않는다.
    """
    source = (r.ethics_source or "").strip()
    article_number = (r.ethics_article_number or "").strip()
    citation_label = f"{source} {article_number}".strip()
    if citation_label:
        return f"### 〔{citation_label}〕 {r.ethics_title} (Tier {r.ethics_tier})"
    return f"### {r.ethics_title} (Tier {r.ethics_tier})"


# 롤업 행 식별자.
# RPC `get_ethics_for_patterns`의 parent_chain SELECT가 reasoning 컬럼에 강제 주입하는 마커이며,
# 직접 매핑된 related_to와 parent-chain rollup으로 생성된 related_to를 가르는 유일한 양성 신호다.
# (둘 다 relation_type="related_to" / strength="moderate"로 내려오므로 relation_type만으로는 구분 불가.)
_ROLLUP_MARKER = "parent chain rollup"


def _build_ethics_context(refs: list[EthicsReference]) -> str:
    """규범 컨텍스트를 3섹션으로 분할: 직접 적용 / 직접 참고 / 상위 원칙.

    분류 우선순위 (양성 판정만 사용):
      1. reasoning == _ROLLUP_MARKER → 상위 원칙 (롤업 우선 판정)
      2. relation_type == "violates" + strength in (strong|moderate) → 직접 적용
      3. relation_type == "related_to" + strength in (strong|moderate) → 직접 참고
      그 외(weak / exception_of 등): 무시.
    """
    primary_bucket: list[EthicsReference] = []
    reference_bucket: list[EthicsReference] = []
    rollup_bucket: list[EthicsReference] = []

    for r in refs:
        reasoning = (r.reasoning or "").strip()
        # 롤업 판정을 먼저 한다 — relation_type을 먼저 보면 롤업이 직접 참고로 잘못 빨려든다.
        if reasoning == _ROLLUP_MARKER:
            rollup_bucket.append(r)
        elif r.relation_type == "violates" and r.strength in ("strong", "moderate"):
            primary_bucket.append(r)
        elif r.relation_type == "related_to" and r.strength in ("strong", "moderate"):
            reference_bucket.append(r)

    # 직접 적용/직접 참고는 구체 규범(Tier 4) 우선, 상위 원칙은 상위(Tier 1) 우선.
    primary_bucket.sort(key=lambda r: (-r.ethics_tier, r.ethics_code))
    reference_bucket.sort(key=lambda r: (-r.ethics_tier, r.ethics_code))
    rollup_bucket.sort(key=lambda r: (r.ethics_tier, r.ethics_code))

    # 전역 중복 제거: ethics_code 기준. 같은 코드가 여러 섹션 후보면 먼저 배치된 섹션에만 남는다.
    seen: set[str] = set()

    def _emit(bucket: list[EthicsReference]) -> list[str]:
        lines: list[str] = []
        for r in bucket:
            if r.ethics_code in seen:
                continue
            seen.add(r.ethics_code)
            lines.append(
                f"{_format_ethics_header(r)}\n"
                f"{r.ethics_full_text}"
            )
        return lines

    primary_lines = _emit(primary_bucket)
    reference_lines = _emit(reference_bucket)
    rollup_lines = _emit(rollup_bucket)

    # 빈 섹션의 헤더는 출력하지 않는다.
    sections: list[str] = []
    if primary_lines:
        sections.append("## 직접 적용 규범(인용 1순위)\n\n" + "\n\n".join(primary_lines))
    if reference_lines:
        sections.append("## 직접 참고 규범(보조 인용 가능)\n\n" + "\n\n".join(reference_lines))
    if rollup_lines:
        sections.append("## 상위 원칙(종합 평가 보조용)\n\n" + "\n\n".join(rollup_lines))

    return "\n\n---\n\n".join(sections)


# ── Sonnet 프롬프트 (M6 — 3종 리포트) ──────────────────────────

_SONNET_SYSTEM_PROMPT = """\
당신은 한국 신문윤리위원회 수준의 저널리즘 비평 전문가입니다.
주어진 기사를 분석하여 3가지 독자 유형에 맞는 평가 리포트와 기사 메타분석을 작성합니다.

## 핵심 원칙

### 1. CR-Check 포지셔닝
CR-Check는 저널리즘 비평의 **관점을 제시하는 도구**입니다.
점수, 등급, 순위를 부여하지 않습니다. 서술형으로만 분석합니다.

### 1.5 심각도(severity)와 서술 어조
탐지의 severity는 문제의 무게와 확신의 표현입니다. 리포트의 어조를 여기에 맞추세요.
- high: 분명한 문제 — 명확한 판단으로 서술
- medium: 상당한 개연성 — 절제된 판단에 근거를 병기
- low: 독자가 확인해볼 지점 — 확정된 위반처럼 단정하지 말고, "~로 읽힐 수 있다", "~인지 확인해볼 필요가 있다"처럼 유보형 질문으로 서술

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
- 관련 윤리규범이 제공된 탐지 항목은, 해당 핵심 지적 안에서 최소 1개의 규범을 〔정식 인용명〕 형식으로 반드시 인용하세요. 여러 규범이 제공된 경우 가장 직접적인 규범을 우선 사용하세요.
- 제공된 규범 외의 내용을 지어내지 마세요. 제공된 원문에서만 인용하세요.
- <cite> 태그를 사용하지 마세요. 모든 인용은 직접 텍스트로 작성합니다.

### 3. 규범 인용 전략 (Bottom-up)

규범 컨텍스트는 제공 상황에 따라 다음 섹션을 포함할 수 있습니다.

1. `## 직접 적용 규범(인용 1순위)`
2. `## 직접 참고 규범(보조 인용 가능)`
3. `## 상위 원칙(종합 평가 보조용)`

세 섹션이 항상 모두 제공되는 것은 아닙니다. 제공된 섹션만 사용하세요.

인용 우선순위:
- 직접 적용 규범이 제공된 경우, 핵심 지적의 1차 근거로 우선 사용합니다.
- 직접 참고 규범은 직접 적용 규범을 보완하거나 해석을 넓힐 때 보조 근거로 사용합니다.
- 상위 원칙은 반복적인 단독 근거가 아니라, 직접 규범을 보조하거나 종합 평가를 정리하는 맥락에서 사용합니다.
- 직접 적용 규범 또는 직접 참고 규범이 충분히 제공된 경우, 핵심 지적은 가능한 한 직접 규범을 중심으로 논증합니다.
- 상위 원칙만으로 핵심 위반 판단을 구성하지 않습니다.
- 상위 원칙을 인용할 때는 가능한 한 직접 적용 규범 또는 직접 참고 규범과 연결합니다.
- 직접 적용 규범과 직접 참고 규범이 제공되지 않은 경우, 없는 하위 규범을 만들지 말고 컨텍스트의 한계를 반영해 신중하게 서술합니다.
- 규범을 인용할 때는 컨텍스트 헤더의 〔정식 인용명〕을 그대로 사용합니다.

#### 인용 방식 예시

아래 예시는 인용 방식 설명용입니다. 실제 출력에서는 제공된 컨텍스트의 〔정식 인용명〕만 사용합니다.

- 나쁜 예: 상위 원칙의 〔정식 인용명〕만 반복 인용하며 핵심 위반을 단정하는 서술.
- 좋은 예: 직접 적용 규범의 〔정식 인용명〕을 먼저 근거로 들고, 필요한 경우 상위 원칙의 〔정식 인용명〕과 연결해 종합 평가를 정리하는 서술.

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
- 마크다운 중간제목(###)은 핵심 지적마다 하나씩 사용할 수 있습니다. 지적과 무관한 과도한 구조화는 글의 자연스러움을 해칩니다.
- "문제", "문제점", "문제가 있습니다"라는 표현을 반복하지 마세요. 이미 평가를 요청한 독자에게 "문제가 있다"를 반복 강조할 필요가 없습니다. 대신 "이런 점이 눈에 띕니다", "이 부분을 살펴보겠습니다", "아쉬운 지점입니다" 등 다양한 표현을 쓰세요.
- 3종 리포트 모두, 제목(# 또는 ##)으로 시작하지 마세요.
- 곧바로 본문 첫 문장(도입부)으로 시작하세요.
- 탭 UI에 이미 리포트 유형이 표시되므로, 리포트 안에서 유형을 반복할 필요 없습니다.

## 구조

탐지된 패턴은 원칙적으로 모두 다루되, 같은 현상을 가리키는 패턴은 하나의 지적으로 묶어 설명하세요.

각 리포트는 도입 → 핵심 지적들 → 종합 평가의 흐름을 따르고, 각 핵심 지적은 다음 요소가 독자에게 납득될 만큼 완결되어야 합니다.

1. 무엇이 관찰되는가
2. 기사 안의 어떤 표현이 근거인가
3. 어떤 윤리규범과 연결되는가 (위 「규범 인용 전략」을 따름)
4. 왜 독자의 이해에 영향을 주는가
5. 어떻게 고칠 수 있는가

같은 내용을 반복하거나, 상투적 일반론을 덧붙이지 마세요.

## 분석 개요 작성 규칙

분석 개요의 각 항목(기사 유형, 기사 요소, 편집 구조, 취재 방식, 내용 흐름)은
시민이 "이 기사가 대략 어떤 기사인지" 파악하는 데 필요한 최소한의 정보만 담으세요.

- 각 항목은 1~2문장, 최대 80자 이내로 작성하세요.
- 나열형 설명이 아니라, 핵심만 짚는 한 줄 요약 형태로 쓰세요.
- 구체적인 인물명이나 사건 경위는 본문 리포트에서 다루면 됩니다.
  개요에서는 "익명 취재원 위주, 비판 측 편중"처럼 특징만 짚으세요.

## 출력 형식

반드시 아래 JSON 형식으로만 응답하세요. JSON 외 다른 텍스트를 포함하지 마세요.
리포트 본문 안에서 기사 문장을 인용할 때는 큰따옴표(") 대신 낫표(「 」)를 사용하세요. 큰따옴표는 JSON 구조를 깨뜨립니다.

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


# [DEPRECATED] _SONNET_SYSTEM_PROMPT_LEGACY는 backend/core/report_generator_legacy.py로 분리됨
# (Phase β 이전의 cite 태그 후치환 방식 프롬프트, 비교 실험용 보존)


# ── JSON 파싱 유틸 ──────────────────────────────────────────────

def _unescape_json_string(s: str) -> str:
    """JSON 문자열 이스케이프 시퀀스를 실제 문자로 변환.

    표준 JSON 이스케이프 규칙 (RFC 8259):
      \\n → 줄바꿈, \\t → 탭, \\r → CR, \\b → BS, \\f → FF,
      \\" → ", \\\\ → \\, \\/ → /, \\uXXXX → Unicode 문자.
    알 수 없는 이스케이프는 백슬래시를 그대로 유지하고 한 문자씩 전진.
    """
    result: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "n":
                result.append("\n")
                i += 2
            elif nxt == "t":
                result.append("\t")
                i += 2
            elif nxt == "r":
                result.append("\r")
                i += 2
            elif nxt == "b":
                result.append("\b")
                i += 2
            elif nxt == "f":
                result.append("\f")
                i += 2
            elif nxt == '"':
                result.append('"')
                i += 2
            elif nxt == "\\":
                result.append("\\")
                i += 2
            elif nxt == "/":
                result.append("/")
                i += 2
            elif nxt == "u" and i + 5 < n:
                hex_code = s[i + 2 : i + 6]
                try:
                    result.append(chr(int(hex_code, 16)))
                    i += 6
                except ValueError:
                    result.append(ch)
                    i += 1
            else:
                # 알 수 없는 이스케이프: 백슬래시 그대로 유지
                result.append(ch)
                i += 1
        else:
            result.append(ch)
            i += 1
    return "".join(result)


def _fix_unescaped_newlines_in_strings(s: str) -> str:
    """JSON 문자열 리터럴 내부의 실제 newline/cr/tab을 \\n/\\r/\\t 이스케이프 시퀀스로 치환.

    큰따옴표 상태를 추적하여 문자열 리터럴 내부에서만 치환한다.
    이미 이스케이프된 시퀀스(예: \\")는 건드리지 않는다.
    """
    result: list[str] = []
    in_string = False
    escape = False
    for ch in s:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == "\\":
            result.append(ch)
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == "\n":
                result.append("\\n")
                continue
            if ch == "\r":
                result.append("\\r")
                continue
            if ch == "\t":
                result.append("\\t")
                continue
        result.append(ch)
    return "".join(result)


def _robust_json_parse(text: str) -> dict:
    """4단계 폴백 JSON 파싱.

    1차: 마크다운 코드블록 제거 후 직접 json.loads
    2차: { } 바운더리 추출 후 json.loads
    3차: 후행 쉼표 제거 + 문자열 내 실제 줄바꿈 escape 후 json.loads
    4차: 정규식으로 reports / article_analysis 필드 개별 추출 (logger.warning 기록)
    4단계 모두 실패 시 ValueError raise.
    """
    # 공통 전처리: 마크다운 코드블록 제거
    cleaned = re.sub(r"```json\s*", "", text)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()

    # 1차: 전처리 후 직접 json.loads
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2차 이후에서 사용할 { } 바운더리 추출
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    extracted = cleaned[start : end + 1] if (start != -1 and end != -1) else cleaned

    # 2차: 바운더리 추출 후 json.loads
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass

    # 3차: 후행 쉼표 제거 + 문자열 내 실제 줄바꿈 escape 후 json.loads
    try:
        fixed = re.sub(r",(\s*[}\]])", r"\1", extracted)
        fixed = _fix_unescaped_newlines_in_strings(fixed)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 4차: 슬라이싱 + unescape로 reports / article_analysis 개별 필드 추출
    # 전략: 각 리포트 키의 value 시작 위치를 찾아, 다음 키 시작 직전까지 슬라이싱.
    # 이렇게 하면 리포트 본문에 이스케이프되지 않은 큰따옴표가 있어도 잘리지 않음.
    keys = ("comprehensive", "journalist", "student")
    positions: dict[str, Optional[tuple[int, int]]] = {}
    for key in keys:
        key_match = re.search(rf'"{key}"\s*:\s*', extracted)
        positions[key] = (key_match.start(), key_match.end()) if key_match else None

    reports: dict[str, str] = {}
    for idx, key in enumerate(keys):
        pos = positions[key]
        if pos is None:
            reports[key] = ""
            continue
        _, value_start = pos
        # 다음 키의 key_start를 찾아 슬라이싱 경계로 사용
        end_pos: Optional[int] = None
        for next_key in keys[idx + 1 :]:
            next_pos = positions[next_key]
            if next_pos is not None:
                end_pos = next_pos[0]
                break
        raw_value = extracted[value_start:end_pos] if end_pos is not None else extracted[value_start:]
        # 앞뒤 공백 정리
        raw_value = raw_value.strip()
        # 후행 쉼표 제거
        if raw_value.endswith(","):
            raw_value = raw_value[:-1].rstrip()
        # 앞 큰따옴표 제거
        if raw_value.startswith('"'):
            raw_value = raw_value[1:]
        # 가장 뒤의 큰따옴표 직전까지로 자르기 (리포트 본문의 닫는 따옴표 탐색)
        last_quote = raw_value.rfind('"')
        if last_quote != -1:
            raw_value = raw_value[:last_quote]
        # JSON 이스케이프 시퀀스를 실제 문자로 변환
        reports[key] = _unescape_json_string(raw_value)

    analysis: dict = {}
    aa_match = re.search(
        r'"article_analysis"\s*:\s*(\{[^{}]*\})',
        extracted,
        re.DOTALL,
    )
    if aa_match:
        try:
            analysis = json.loads(aa_match.group(1))
        except json.JSONDecodeError:
            for field_name in ("type", "date", "author", "sources", "tone", "contentFlow"):
                fm = re.search(
                    rf'"{field_name}"\s*:\s*"((?:[^"\\]|\\.)*)"',
                    aa_match.group(1),
                    re.DOTALL,
                )
                if fm:
                    analysis[field_name] = _unescape_json_string(fm.group(1))

    if any(reports.values()) or analysis:
        logger.warning("_robust_json_parse: 4차 정규식 추출 사용")
        return {"reports": reports, "article_analysis": analysis}

    raise ValueError(f"JSON 파싱 4단계 모두 실패: {cleaned[:200]}...")


# ── Sonnet 호출 ──────────────────────────────────────────────────

def call_sonnet(
    article_text: str,
    detections_json: str,
    overall_assessment: str,
    ethics_context: str,
    meta_pattern_block: str = "",
    frame_pattern_block: str = "",
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

    # 프레임 효과 대상 패턴(4-3-b/3-4-a/3-4-b/6-2-d) 확정 시에만 블록 추가
    if frame_pattern_block:
        user_message += f"\n{frame_pattern_block}\n"

    user_message += f"""
## 기사 전문
{article_text}"""

    response = client.messages.create(
        model=SONNET_MODEL,
        # Sonnet 5 토크나이저는 동일 텍스트를 ~30% 더 많은 토큰으로 계산한다.
        # 배포 후 usage.output_tokens 로그를 관찰하고 필요시 후속 커밋에서 조정할 것.
        max_tokens=15000,
        # 이번 라운드는 adaptive thinking 의도적 비활성화 — 모델 자체 성능만 측정.
        # 활성화 실험은 별도 라운드로 진행한다.
        thinking={"type": "disabled"},
        # system prompt만 ephemeral 캐시 대상으로 지정한다.
        # user message(기사 본문/탐지/규범 컨텍스트/메타)는 매 호출 변동이 크므로 캐시하지 않는다.
        system=[
            {
                "type": "text",
                "text": _SONNET_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    report = response.content[0].text
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    return report, in_tok, out_tok


# ── 메인 함수 ────────────────────────────────────────────────────

def _build_meta_pattern_block(meta_patterns: list) -> str:
    # [DEPRECATED] 메타 패턴 비활성화로 현재 활성 파이프라인에서는 메타 블록이 주입되지 않음.
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


def _build_frame_effect_block(detected_codes: set) -> str:
    """사회적 약자·소수자 프레이밍 패턴 탐지 시 Sonnet 프롬프트에 주입할 블록.

    T2의 필수 검토 대상(_MANDATORY_REVIEW_TARGET_CODES)과 동일한 4개 패턴
    (4-3-b/3-4-a/3-4-b/6-2-d) 중 하나라도 이번 분석에서 확정됐을 때만 발동한다.
    탐지되지 않은 기사에는 이 블록 자체가 생성되지 않는다(빈 문자열 반환).
    """
    triggered = _MANDATORY_REVIEW_TARGET_CODES & detected_codes
    if not triggered:
        return ""

    return f"""## 프레임 효과 서술 지시 (차별·낙인·대립 구도 패턴 탐지됨: {', '.join(sorted(triggered))})

이 기사에서 사회적 약자·소수자 관련 프레이밍 패턴이 확정됐습니다. 관련 핵심
지적에 한해, "무엇이 빠졌다/틀렸다"에서 끝나지 말고 그 서술이 독자의 인식에
남기는 프레임을 설명하세요. 다음 네 질문 중 최소 두 가지를 본문에서 다루세요:

① 누구의 목소리가 중심화되고 누구의 목소리가 배제되는가
② 누가 '시민·정상·공공질서'의 바깥으로 밀려나는가
③ 제목과 인용 배치가 어떤 낙인 효과를 만드는가
④ 어떤 대안 제목·추가 취재 질문이 가능했는가

이 지시는 위에 나열된 패턴이 확정된 핵심 지적에만 적용합니다. 다른 핵심
지적(예: 취재원 편중, 사실과 의견 혼재)까지 프레임 효과 언어로 억지로 바꾸지
마세요. 윤리규범 인용은 반드시 위 「관련 윤리규범」 섹션에 제공된 것만
사용합니다(기존 규칙과 동일)."""


def generate_report(
    article_text: str,
    pattern_ids: list[int],
    detections: list[dict],
    overall_assessment: str = "",
    meta_patterns: list = None,
    article_context: str = 'general',
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
    ethics_refs = fetch_ethics_for_patterns(
        pattern_ids, sb_url, sb_key, article_context=article_context,
    )
    ethics_context = _build_ethics_context(ethics_refs)

    # 2. detections JSON 문자열
    detections_json = json.dumps(detections, ensure_ascii=False, indent=2)

    # 2.5 메타 패턴 프롬프트 블록 (조건부)
    meta_block = _build_meta_pattern_block(meta_patterns or [])

    # 2.6 프레임 효과 프롬프트 블록 (조건부 — 대상 4패턴 확정 시에만)
    _detected_codes = {d.get("pattern_code") for d in detections if d.get("pattern_code")}
    frame_block = _build_frame_effect_block(_detected_codes)

    # 3. Sonnet 호출 (3종 JSON 반환) + 재시도 로직
    max_retries = 5

    for attempt in range(max_retries):
        try:
            raw_text, in_tok, out_tok = call_sonnet(
                article_text, detections_json, overall_assessment, ethics_context,
                meta_pattern_block=meta_block,
                frame_pattern_block=frame_block,
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
        except anthropic.APIStatusError as e:
            # (A) API status 오류 — 529/429/그 외로 분기
            status = getattr(e, "status_code", None)
            if status == 529:
                # 과부하: 긴 백오프 (10/20/40/60/60초)
                wait = min(10 * (2 ** attempt), 60)
                logger.warning(
                    f"API 과부하(529), {wait}초 후 재시도 ({attempt + 1}/{max_retries})"
                )
                if attempt == max_retries - 1:
                    raise ValueError(f"API 과부하(529) 최종 실패: {e}")
                time.sleep(wait)
            elif status == 429:
                # 한도 초과: 재시도 없이 즉시 실패
                logger.error(f"API 한도 초과(429): {e}")
                raise ValueError(f"API 한도 초과(429): {e}")
            else:
                # 그 외 status: 짧은 백오프
                logger.error(
                    f"API status 오류({status}), 시도 {attempt + 1}/{max_retries}: "
                    f"[{type(e).__name__}] {e}"
                )
                if attempt == max_retries - 1:
                    raise ValueError(f"리포트 생성 최종 실패: {e}")
                time.sleep(2 ** attempt)
        except (json.JSONDecodeError, ValueError) as e:
            # (B) JSON 파싱 실패 또는 구조 검증 실패
            logger.error(
                f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
                f"[{type(e).__name__}] {e}"
            )
            if attempt == max_retries - 1:
                raise ValueError(f"리포트 생성 최종 실패: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            # (C) 그 외 예외
            logger.error(
                f"리포트 생성 시도 {attempt + 1}/{max_retries} 실패: "
                f"[{type(e).__name__}] {e}"
            )
            if attempt == max_retries - 1:
                raise ValueError(f"리포트 생성 최종 실패: {e}")
            time.sleep(2 ** attempt)
