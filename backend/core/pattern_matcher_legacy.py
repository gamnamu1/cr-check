# backend/core/pattern_matcher_legacy.py
"""
[DEPRECATED] CR-Check 레거시 패턴 매칭 코드 (비교 실험용 보존)

이 모듈은 M6 활성 파이프라인에서 절대 import하지 않는다.
M6는 pattern_matcher.match_patterns_solo() (Sonnet Solo 1-Call + Devil's Advocate CoT)만 사용한다.

여기 보존된 deprecated 함수들:
- 2-Call 아키텍처 (Haiku 대분류 의심 → Sonnet 소분류 검증):
    CATEGORY_PATTERNS, VALID_CATEGORIES
    _HAIKU_SUSPECT_PROMPT, _SONNET_VERIFY_PROMPT, _CONFUSION_PAIRS
    _build_confusion_pairs_text, _build_filtered_pattern_list
    call_haiku_suspect, _parse_suspect_response
    call_sonnet_verify, _parse_verify_response
    match_patterns_2call

- 1-Call 아키텍처 (Sonnet 단일 호출, M4 잔존):
    _HAIKU_SYSTEM_PROMPT
    call_haiku, _parse_haiku_response
    match_patterns

비교 실험 또는 reproducibility 목적이 아닌 한 사용 금지.
"""

import os
import json
import re
import logging
from typing import Optional

from anthropic import Anthropic
import httpx

from .db import _get_supabase_config
from .pattern_matcher import (
    # 데이터 구조
    VectorCandidate,
    HaikuDetection,
    PatternMatchResult,
    SuspectResult,
    # 공통 유틸
    validate_pattern_codes,
    _load_pattern_catalog,
    _build_pattern_list_text,
    generate_embeddings,
    search_vectors,
    # 설정
    SONNET_MODEL,
    VECTOR_THRESHOLD,
)

logger = logging.getLogger(__name__)


# ── [DEPRECATED] 2-Call 아키텍처: 대분류→소분류 매핑 ─────────────

CATEGORY_PATTERNS = {
    "1-1": ["1-1-1", "1-1-2", "1-1-3", "1-1-4", "1-1-5"],
    "1-2": ["1-2-1", "1-2-2", "1-2-3"],
    "1-3": ["1-3-1", "1-3-2", "1-3-3", "1-3-4", "1-3-5"],
    "1-4": ["1-4-1", "1-4-2"],  # 메타 패턴 — Sonnet에서는 제외됨
    "1-5": ["1-5-1", "1-5-2", "1-5-3", "1-5-4"],
    "1-6": ["1-6-1", "1-6-2", "1-6-3"],
    "1-7": ["1-7-1", "1-7-2", "1-7-3", "1-7-4", "1-7-5", "1-7-6"],
    "1-8": ["1-8-1", "1-8-2"],
}

VALID_CATEGORIES = set(CATEGORY_PATTERNS.keys())


# ── 1st Call: Haiku 대분류 의심 식별 ─────────────────────────────

_HAIKU_SUSPECT_PROMPT = """\
당신은 한국 언론 윤리 전문가입니다.
주어진 뉴스 기사를 읽고, 아래 8개 대분류 중 윤리적 문제가 의심되는 영역을 1~3개 선택하세요.
어떤 영역에서도 문제가 의심되지 않으면, suspect_categories를 빈 배열 []로 반환하세요.

## 8개 대분류
1-1 진실성: 사실 관계 검증, 데이터·통계 정확성, 출처 신뢰성
1-2 투명성: 취재 과정 공개, 이해충돌 고지
1-3 균형성: 다양한 관점 반영, 맥락 제공, 편향 여부
1-4 독립성: 광고·홍보성, 외부 압력, 이해관계자 영향
1-5 인권: 피해자 보호, 차별·혐오, 사생활 침해, 2차 가해
1-6 전문성: 전문지식 부족, 취재 깊이, 검증 절차
1-7 언어: 선정적·자극적 표현, 제목 과장, 차별 표현, 명료성
1-8 디지털: AI 생성 콘텐츠, 딥페이크, 알고리즘 편향

## 판단 가이드

**의심 선택 기준:**
- 기사에서 특정 대분류에 해당하는 문제가 "있을 수 있다"는 합리적 의심이 들면 선택
- 확실하지 않아도 의심이 들면 포함 (2단계에서 정밀 검증함)
- 최대 3개까지만 선택. 4개 이상 의심되면 가장 강한 3개만.

**양질의 보도 판정 기준 (suspect_categories: []):**
- 인권·사회 문제를 깊이 파헤치는 탐사보도·기획보도는, 강렬한 표현이 있더라도 취재 결과에 부합하면 양질의 보도
- 정치적 비판이 구체적 팩트(문서, 수치, 증언)에 근거한 보도는 편향이 아님
- 인권, 차별, 성소수자, 정치 관련 기사는 특히 신중하게 판단할 것
- overall_assessment에 양질로 판단한 근거를 반드시 명시할 것

## 참고 예시

### 예시 1 — [TP] 1-1 진실성: 데이터 오용
기사 제목: "최근 한달 확진 10만명당 확진률 80%↑, 치명률 美·브라질보다 높아… 'K방역의 치욕'"
기사 요약: 코로나19 지표를 두 시점에서 단순 비교하여 한국이 "세계 최악"이라고 단정. 실제 인구 대비 확진자 수는 미국의 1.8% 수준.
올바른 판단:
```json
{
  "overall_assessment": "특정 두 시점의 증가율만으로 국가 간 방역 실태를 비교하는 것은 통계적으로 불충분하다. 실제 절대 수치를 제시하지 않고 증가율만 비교한 것은 데이터 오용이 의심된다.",
  "suspect_categories": ["1-1"]
}
```

### 예시 2 — [TP] 1-3+1-7: 사실/의견 혼재 + 제목 과장
기사 제목: "부작용 불안한데…쉬지도 못하는데…선택도 못하는데… 2030 '접종 보이콧'"
기사 요약: 접종을 꺼리는 3명의 사례를 '보이콧'(공동 거부)으로 제목에 표현. 실제 예약률 61.3%.
올바른 판단:
```json
{
  "overall_assessment": "3개의 개별 사례를 '보이콧'이라는 집단적 행위로 일반화한 제목이 사실과 의견을 혼재시키고 있으며, 제목이 본문 내용을 왜곡·과장하고 있다.",
  "suspect_categories": ["1-1", "1-7"]
}
```

### 예시 3 — [TP] 1-4 독립성: 기사-광고 미구분
기사 제목: [뉴스면 카테고리 편집] (한경닷컴)
기사 요약: 뉴스 카테고리에 주식담보대출 광고를 기사처럼 배치. '#보도자료' 해시태그만 부착.
올바른 판단:
```json
{
  "overall_assessment": "뉴스 카테고리에 투자 권유 광고를 기사 형태로 배치하여 독자를 기만하는 편집 독립성 훼손이 의심된다.",
  "suspect_categories": ["1-4"]
}
```

### 예시 4 — [TP] 1-5 인권: 차별 표현
기사 제목: "'눈먼 돈' 청년 전세대출"
기사 요약: 전세대출 사기 보도에서 시각장애인 비하 관용구를 제목에 사용.
올바른 판단:
```json
{
  "overall_assessment": "'눈먼 돈'은 시각장애를 부정적 의미로 사용하는 차별적 관용구다. 보도 내용과 무관하게 제목의 언어 선택에서 인권 문제가 의심된다.",
  "suspect_categories": ["1-5", "1-7"]
}
```

### 예시 5 — [TP] 1-6+1-1: 사실/의견 혼재
기사 제목: "터졌다 하면 대형참사…'한화 리스크' 진행형"
기사 요약: 과거 사고를 나열하며 '한화 리스크 진행형'이라고 단정. 구조적 분석 없이 프레이밍.
올바른 판단:
```json
{
  "overall_assessment": "'한화 리스크 진행형'은 기자의 해석이지 확인된 사실이 아니다. 사실과 의견의 혼재 및 심층 분석 부족이 의심된다.",
  "suspect_categories": ["1-1", "1-6"]
}
```

### 예시 6 — [TP] 1-7 언어: 제목 왜곡
기사 제목: "공장 세우고 동료 때린 '그들(해고자)'이 돌아온다"
기사 요약: 노조법 개정안 보도에서 폭행 사례를 전체 해고자(2,142명)로 일반화한 제목.
올바른 판단:
```json
{
  "overall_assessment": "제목이 소수 사례를 전체 집단으로 일반화하여 본문과 부합하지 않으며, 법 개정에 대한 부정적 시각을 부추기는 자극적 표현을 사용했다.",
  "suspect_categories": ["1-7"]
}
```

### 예시 7 — [TP] 1-8 디지털: AI 콘텐츠 품질 관리
기사 제목: (가상) "AI 생성 뉴스에서 현직 대통령을 '전 대통령'으로 오표기"
기사 요약: AI가 생성한 기사에서 직함 오류. 편집부가 검증 없이 게재.
올바른 판단:
```json
{
  "overall_assessment": "AI 생성 콘텐츠에 대한 편집 검증이 부재하여 사실 오류가 발생했다. 디지털 콘텐츠 품질 관리 문제가 의심된다.",
  "suspect_categories": ["1-8"]
}
```

### 예시 8 — [TN] 탐사보도: 양질의 보도
기사 제목: "'감금·성폭행'…목포 '옛 동명원' 피해자들의 증언" (전남일보, 이달의 기자상 수상)
기사 요약: 장애인 수용시설의 감금·성폭행 실태를 피해자 증언과 문서 증거로 고발한 탐사보도.
올바른 판단:
```json
{
  "overall_assessment": "'감금', '성폭행' 등 강한 표현이 등장하지만, 피해자 증언과 문서 증거에 기반한 탐사보도로서 사건의 심각성에 부합하는 정당한 저널리즘이다. 이달의 기자상 수상작으로 공익적 가치가 인정된 보도다.",
  "suspect_categories": []
}
```

### 예시 9 — [TN] 환경 탐사보도: 양질의 보도
기사 제목: "추적: 지옥이 된 바다" (한국일보, 이달의 기자상 수상)
기사 요약: 해양 오염 실태를 장기간 추적 취재하여 고발한 탐사보도.
올바른 판단:
```json
{
  "overall_assessment": "'지옥이 된 바다'라는 극단적 비유가 있지만, 장기간 현장 취재에 기반한 팩트가 뒷받침되는 환경 탐사보도다. 서사적 표현은 취재 결과의 심각성에 부합한다.",
  "suspect_categories": []
}
```

## 출력 형식
반드시 아래 JSON 형식으로만 응답하라. 다른 텍스트를 포함하지 마라.
```json
{
  "overall_assessment": "string (2~3문장, 필수)",
  "suspect_categories": ["1-X", ...]
}
```"""


# ── 2nd Call: Sonnet 소분류 검증 ─────────────────────────────────

_SONNET_VERIFY_PROMPT = """\
당신은 한국 뉴스 기사의 보도 품질을 평가하는 전문 분석가입니다.

1단계 분석 결과, 이 기사는 {suspect_categories} 영역에서 윤리적 문제가 의심됩니다.
아래의 관련 소분류 목록과 기사를 대조하여, 실제로 위반이 확인되는 패턴만 정확히 찾아내세요.

## 핵심 원칙: 정밀도 우선
- 확신이 없으면 선택하지 마세요. 누락보다 오탐이 더 해롭습니다.
- 기사에서 해당 문제를 보여주는 **구체적 문장이나 표현을 특정할 수 없다면** 그 패턴을 선택하지 마세요.
- 위반이 아닌 이유가 있다면 reasoning에 명시하세요.

## ★ 후보 패턴 활용
★ 표시된 패턴은 벡터 검색으로 사전 선별된 유력 후보입니다.
- 의심 영역의 패턴을 우선 검토하되, ★ 후보도 동등하게 고려하세요.

## 기사 길이별 가이드
- 200자 미만: 최대 1~2개
- 200~500자: 최대 2~3개
- 500~2000자: 최대 3~4개
- 2000자 이상: 최대 4~5개. 근거가 매우 명확한 경우에만.
- 같은 패턴을 여러 번 선택하지 마세요.

{confusion_pairs}

## 기타 규칙
1. 기사에서 **실제로 확인되는** 문제만 선택하세요.
2. "(텍스트 분석 대상 아님)"으로 표시된 패턴은 선택하지 마세요.
3. 유사 패턴 중 더 정확한 쪽을 선택하세요.
4. 문제가 발견되지 않으면 빈 배열 []을 반환하세요.
5. 반드시 아래 JSON 형식으로만 응답하세요.

## 출력 형식
```json
[
  {{
    "matched_text": "문제가 되는 기사 원문 인용 (1~2문장)",
    "reasoning": "이 텍스트가 왜 문제이고 어떤 보도관행 기준을 위반했는지 근거 (1~2문장)",
    "severity": "high|medium|low",
    "pattern_code": "1-1-1"
  }}
]
```"""

# 혼동 패턴 쌍 — 해당 대분류에 따라 동적 포함
_CONFUSION_PAIRS = {
    "1-1": "- **1-1-1 vs 1-1-4**: 팩트 자체가 틀렸으면 1-1-1. 팩트는 맞지만 사실과 의견을 섞었으면 1-1-4.",
    "1-3": "- **1-3-1 vs 1-3-2**: 반론 없이 한쪽만 인용했으면 1-3-1. 양쪽을 언급했지만 틀이 편향적이면 1-3-2.\n- **1-3-1 vs 1-3-4**: 반론 없이 전달했으면 1-3-1. 배경·맥락 생략으로 판단 정보 부족이면 1-3-4.",
    "1-7": "- **1-7-2 vs 1-7-5**: 이념적 틀로 규정(빨갱이, 수구)이면 1-7-2. 감정 자극 과장(충격, 발칵)이면 1-7-5.\n- **1-7-3 vs 1-7-4**: 본문이 과장/왜곡이면 1-7-3. 본문은 정상이고 제목만 과장이면 1-7-4.",
}


def _build_confusion_pairs_text(suspect_categories: list[str]) -> str:
    """의심 대분류에 해당하는 혼동 패턴 쌍 텍스트 생성."""
    pairs = []
    for cat in suspect_categories:
        if cat in _CONFUSION_PAIRS:
            pairs.append(_CONFUSION_PAIRS[cat])
    if pairs:
        return "## 자주 혼동되는 패턴 쌍\n" + "\n".join(pairs)
    return ""


def _build_filtered_pattern_list(
    suspect_categories: list[str],
    all_patterns: list[dict],
    vector_candidates: list["VectorCandidate"],
) -> str:
    """의심 대분류에 속하는 소분류만 필터링 + ★ 마크."""
    # 의심 대분류에 속하는 소분류 코드 집합
    target_codes = set()
    for cat in suspect_categories:
        for code in CATEGORY_PATTERNS.get(cat, []):
            target_codes.add(code)

    # 메타 패턴 제외
    target_codes -= {"1-4-1", "1-4-2"}

    candidate_codes = {c.pattern_code for c in vector_candidates}
    lines = []

    for p in all_patterns:
        code = p["code"]
        if code not in target_codes and code not in candidate_codes:
            continue
        name = p["name"]
        desc = p.get("description") or ""
        if code.startswith("1-2-"):
            entry = f"{code}: {name} (텍스트 분석 대상 아님)"
        else:
            entry = f"{code}: {name} — {desc}"

        if code in candidate_codes:
            lines.append(f"★ {entry}")
        elif code in target_codes:
            lines.append(f"  {entry}")

    return "\n".join(lines)


# ── 1st Call 함수 ────────────────────────────────────────────────
# SuspectResult 클래스는 pattern_matcher.py 활성 영역에 정의되어 import됨


def call_haiku_suspect(article_text: str) -> SuspectResult:
    """Haiku를 호출하여 대분류 의심 영역을 식별."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=_HAIKU_SUSPECT_PROMPT,
        messages=[{"role": "user", "content": f"## 기사 전문\n{article_text}"}],
        temperature=0.0,
    )

    raw = response.content[0].text
    return _parse_suspect_response(raw)


def _parse_suspect_response(text: str) -> SuspectResult:
    """Haiku suspect 응답 파싱."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        logger.warning("Suspect response: JSON object not found")
        return SuspectResult(raw_response=text)

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        logger.warning(f"Suspect JSON parse error: {e}")
        return SuspectResult(raw_response=text)

    assessment = data.get("overall_assessment", "")
    categories = data.get("suspect_categories", [])

    # 유효성 검증: 8개 대분류 코드만 허용
    valid_cats = [c for c in categories if c in VALID_CATEGORIES]
    if len(valid_cats) != len(categories):
        invalid = set(categories) - VALID_CATEGORIES
        logger.warning(f"Invalid suspect categories removed: {invalid}")

    return SuspectResult(
        overall_assessment=assessment,
        suspect_categories=valid_cats,
        raw_response=text,
    )


# ── 2nd Call 함수 ────────────────────────────────────────────────

def call_sonnet_verify(
    article_text: str,
    suspect_categories: list[str],
    all_patterns: list[dict],
    vector_candidates: list[VectorCandidate],
) -> tuple[list[HaikuDetection], str]:
    """Sonnet을 호출하여 소분류 검증. (detections, raw_response) 반환."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # 동적 소분류 목록 생성
    pattern_list = _build_filtered_pattern_list(
        suspect_categories, all_patterns, vector_candidates
    )

    # 혼동 패턴 쌍 동적 삽입
    confusion_text = _build_confusion_pairs_text(suspect_categories)

    # 프롬프트 조립
    cats_str = ", ".join(suspect_categories)
    system_prompt = _SONNET_VERIFY_PROMPT.format(
        suspect_categories=cats_str,
        confusion_pairs=confusion_text,
    )

    user_message = f"""## 관련 소분류 패턴 목록
{pattern_list}

## 기사 전문
{article_text}"""

    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
    )

    raw = response.content[0].text
    detections = _parse_verify_response(raw)
    return detections, raw


def _parse_verify_response(text: str) -> list[HaikuDetection]:
    """Sonnet verify 응답 파싱 (배열). 중복 pattern_code 제거."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        logger.warning("Verify response: JSON array not found")
        return []

    try:
        items = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        logger.warning(f"Verify JSON parse error: {e}")
        return []

    seen_codes = set()
    detections = []
    for item in items:
        if isinstance(item, dict) and "pattern_code" in item:
            code = item.get("pattern_code", "")
            if code in seen_codes:
                continue
            seen_codes.add(code)
            detections.append(
                HaikuDetection(
                    pattern_code=code,
                    matched_text=item.get("matched_text", ""),
                    severity=item.get("severity", "medium"),
                    reasoning=item.get("reasoning", ""),
                )
            )
    return detections


# ── 2-Call 통합 함수 ─────────────────────────────────────────────

def match_patterns_2call(
    chunks: list[str],
    article_text: str,
    threshold: Optional[float] = None,
) -> PatternMatchResult:
    """2-Call 파이프라인: Haiku(대분류 의심) → Sonnet(소분류 검증)."""
    sb_url, sb_key = _get_supabase_config()
    t = threshold if threshold is not None else VECTOR_THRESHOLD

    # 1. 패턴 카탈로그 로드
    catalog = _load_pattern_catalog(sb_url, sb_key)

    # 2. 청크 임베딩 + 벡터 검색
    if chunks:
        embeddings, emb_tokens = generate_embeddings(chunks)
    else:
        embeddings, emb_tokens = generate_embeddings([article_text])
    candidates = search_vectors(embeddings, sb_url, sb_key, threshold=t)

    # 3. 1st Call: Haiku 대분류 의심
    suspect = call_haiku_suspect(article_text)

    # 4. 의심 없으면 즉시 반환
    if not suspect.suspect_categories:
        return PatternMatchResult(
            vector_candidates=candidates,
            haiku_detections=[],
            validated_pattern_ids=[],
            validated_pattern_codes=[],
            hallucinated_codes=[],
            haiku_raw_response=suspect.raw_response,
            embedding_tokens=emb_tokens,
            suspect_result=suspect,
        )

    # 5. 2nd Call: Sonnet 소분류 검증
    detections, verify_raw = call_sonnet_verify(
        article_text, suspect.suspect_categories, catalog, candidates
    )

    # 6. 밸리데이션
    valid_ids, valid_codes, hallucinated = validate_pattern_codes(
        detections, sb_url, sb_key
    )

    return PatternMatchResult(
        vector_candidates=candidates,
        haiku_detections=detections,
        validated_pattern_ids=valid_ids,
        validated_pattern_codes=valid_codes,
        hallucinated_codes=hallucinated,
        haiku_raw_response=f"[SUSPECT] {suspect.raw_response}\n[VERIFY] {verify_raw}",
        embedding_tokens=emb_tokens,
        suspect_result=suspect,
    )


# ── [DEPRECATED] 1-Call Haiku 호출 ───────────────────────────────
# 아래 함수들은 M4 1-Call 아키텍처의 잔존 코드. 비교 실험용으로 보존.

_HAIKU_SYSTEM_PROMPT = """\
당신은 한국 뉴스 기사의 보도 품질을 평가하는 전문 분석가입니다.

## 1단계: 품질 평가 (반드시 먼저 수행)
기사를 읽고, 이 기사가 전문적인 저널리즘 기준을 충족하는 양질의 보도인지 먼저 평가하세요.
- 사실 관계가 정확하고 출처가 명시되어 있는가?
- 다양한 관점이 반영되어 있는가?
- 공익적 목적이 분명한 탐사보도·기획보도인가?
- 강렬한 주제를 다루더라도, 표현이 취재 결과에 부합하는가?

인권·사회 문제를 깊이 파헤치는 탐사보도·기획보도는 강렬한 표현이 있더라도, 그것이 취재 결과에 부합하면 양질의 보도입니다.
정치적 비판이 구체적 팩트(문서, 수치, 증언)에 근거한 보도는 편향이 아닙니다.
기사의 주제가 인권·차별·정치와 관련된다는 이유만으로 문제 보도로 판정하지 마세요. 강렬한 표현이 취재 결과에 부합하는지를 기준으로 판단하세요.

위 기준을 대체로 충족하는 양질의 보도라면, 아래 2단계를 진행하지 말고 빈 배열 []을 즉시 반환하세요.
양질의 기사에서 억지로 문제를 찾으려 하지 마세요.

## 2단계: 패턴 식별 (1단계에서 문제가 있다고 판단한 경우만)
아래 '패턴 목록'과 기사를 비교하여, 기사에서 실제로 확인되는 문제적 보도관행 패턴을 선별하세요.

### 핵심 원칙: 정밀도 우선
- 확신이 없으면 선택하지 마세요. 누락보다 오탐이 더 해롭습니다.
- 기사에서 해당 문제를 보여주는 **구체적 문장이나 표현을 특정할 수 없다면** 그 패턴을 선택하지 마세요.

### ★ 후보 패턴 활용
★ 표시된 패턴은 벡터 검색으로 사전 선별된 유력 후보입니다.
- ★ 패턴을 먼저 우선적으로 검토하세요.
- 단, ★ 표시가 없는 패턴도 기사에 명확히 해당하면 동등하게 선택하세요.

### 기사 길이별 가이드
- 200자 미만: 최대 1~2개
- 200~500자: 최대 2~3개
- 500~2000자: 최대 3~4개
- 2000자 이상: 최대 4~5개. 근거가 매우 명확한 경우에만.
- 같은 패턴을 여러 번 선택하지 마세요. 가장 강력한 근거 하나만 제시하세요.

### 자주 혼동되는 패턴 쌍
- **1-1-1 vs 1-1-4**: 팩트 자체가 틀렸으면 1-1-1. 팩트는 맞지만 사실과 의견을 섞었으면 1-1-4.
- **1-3-1 vs 1-3-2**: 반론 없이 한쪽만 인용했으면 1-3-1. 양쪽을 언급했지만 틀이 편향적이면 1-3-2.
- **1-3-1 vs 1-3-4**: 반론 없이 전달했으면 1-3-1. 배경·맥락 생략으로 판단 정보 부족이면 1-3-4.
- **1-7-2 vs 1-7-5**: 이념적 틀로 규정(빨갱이, 수구)이면 1-7-2. 감정 자극 과장(충격, 발칵)이면 1-7-5.
- **1-7-3 vs 1-7-4**: 본문이 과장/왜곡이면 1-7-3. 본문은 정상이고 제목만 과장이면 1-7-4.

### 기타 규칙
1. 기사에서 **실제로 확인되는** 문제만 선택하세요.
2. "(텍스트 분석 대상 아님)"으로 표시된 패턴은 선택하지 마세요.
3. 유사 패턴 중 더 정확한 쪽을 선택하세요.
4. 문제가 발견되지 않으면 빈 배열 []을 반환하세요.
5. 반드시 아래 JSON 형식으로만 응답하세요.

## 참고 예시

### 예시 1 — [TP] 1-1 진실성: 데이터 및 통계 오용
기사 제목: "최근 한달 확진 10만명당 확진률 80%↑, 치명률 美·브라질보다 높아… 'K방역의 치욕'"
기사 요약: 코로나19 관련 지표를 한 달간의 두 시점에서 단순 비교하여, 한국이 미국·브라질보다 "세계 최악 수준으로 전락했다"고 단정. 실제 인구 대비 확진자 수는 미국의 1.8%, 브라질의 2.9% 수준이었음.
올바른 분석:
```json
[
  {
    "matched_text": "10만 명당 확진자 수가 80% 늘어 세계 최고 수준의 증가율을 기록",
    "reasoning": "특정 두 시점의 증가율만으로 국가 간 방역 실태를 비교하는 것은 통계적으로 불충분하다. 신문윤리위원회는 이를 '불충분하고 적은 증거로 결론을 이끌어낸 것'으로 판단했다. 실제 절대 수치(인구 10만 명당 한국 101명 vs 미국 5,552명)를 제시하지 않고 증가율만 비교한 것이 핵심 오류다. 이것은 1-7-3(과장과 맥락 왜곡)과 구분해야 한다 — 단순한 표현의 과장이 아니라, 비교 기준 자체가 통계적으로 무의미한 데이터 오용이다.",
    "severity": "high",
    "pattern_code": "1-1-5"
  }
]
```

### 예시 2 — [TP] 1-3 균형성 + 1-7 언어: 사실/의견 혼재 + 제목 과장
기사 제목: "부작용 불안한데…쉬지도 못하는데…선택도 못하는데… 2030 '접종 보이콧'"
기사 요약: 코로나 백신접종 예약 첫날, 접종을 꺼리는 20~30대 3명의 사례를 인용하여 "2030세대 일부는 접종을 거부한다"고 기술하고, 제목에서 '보이콧'(공동 거부)으로 표현. 실제 예약률은 61.3%로, 집단적 거부는 확인되지 않음.
올바른 분석:
```json
[
  {
    "matched_text": "2030 '접종 보이콧'",
    "reasoning": "신문윤리위는 '보이콧'이 '공동으로 받아들이지 않고 물리치는 일'이라는 집단적 움직임을 뜻하지만, 본문에는 3개의 개별 사례만 있을 뿐 집단적 거부의 근거가 없다고 판단했다. 이것은 두 가지 위반이 중첩된 사례다: (1)사실과 의견의 미구분(소수 사례를 일반화), (2)제목이 본문 내용을 왜곡·과장. 1-3-1(관점 다양성 부족)과의 구분 — 여기서 핵심은 다른 관점을 안 다룬 것이 아니라, 사실적 근거 없이 결론을 예단한 것이다.",
    "severity": "high",
    "pattern_code": "1-1-4"
  },
  {
    "matched_text": "'접종 보이콧'이라는 제목",
    "reasoning": "제목은 기사 내용을 정확하게 반영해야 한다. 실제 예약률 61.3%인 상황에서 '보이콧'이라는 표현은 제목-본문 불일치이며, 재난 상황에서 과장 보도로 혼란을 야기한다.",
    "severity": "medium",
    "pattern_code": "1-7-2"
  }
]
```

### 예시 3 — [TP] 1-4 독립성: 기사와 광고의 구분 위반
기사 제목: [뉴스면 카테고리 편집] (한경닷컴)
기사 요약: 한경닷컴이 실시간 뉴스 카테고리에 주식담보대출 광고, 종목추천 유료서비스 광고, 주식 카톡방 홍보 등을 기사 사이에 배치. '#보도자료' 해시태그만 붙이고 광고 표시 없이 마치 기사처럼 게재.
올바른 분석:
```json
[
  {
    "matched_text": "뉴스 카테고리 중간에 투자 권유 광고를 기사처럼 배치",
    "reasoning": "신문윤리위는 '리스크가 높은 주식투자 권유 광고를 기사처럼 배치한 것은 독자에게 혼란을 주고, 광고가 신뢰성 있는 정보라는 잘못된 메시지를 전달한다'고 판단했다. 이것은 1-1-4(사실과 의견 혼재)와 다르다 — 문제의 본질은 기사 내용의 정확성이 아니라, 광고가 기사의 외형을 취하여 독자를 기만하는 편집 독립성의 훼손이다. 1-4-2는 1-1(진실성) 계열보다 구조적으로 상위의 문제로, 기사의 내용이 사실일지라도 그 존재 목적 자체가 저널리즘의 독립성을 훼손하는 위반이다.",
    "severity": "high",
    "pattern_code": "1-4-2"
  }
]
```

### 예시 4 — [TP] 1-5 인권: 차별 표현과 약자 보호
기사 제목: "'눈먼 돈' 청년 전세대출"
기사 요약: 무주택 청년전세대출 제도를 악용한 83억 원 사기 사건을 보도하면서, 제목에 '눈먼 돈'이라는 표현을 사용.
올바른 분석:
```json
[
  {
    "matched_text": "'눈먼 돈' 청년 전세대출",
    "reasoning": "신문윤리위는 '눈먼 돈'이 시각장애인을 비하하는 표현으로, 장애인과 가족에게 상처를 주고 장애에 대한 편견을 부추긴다고 판단했다. 이것은 1-7-4(자극적 표현)와 구분해야 한다 — 문제는 표현의 선정성이 아니라, 특정 장애를 부정적 의미의 관용구로 사용함으로써 해당 집단을 비하하는 차별적 언어 사용이다.",
    "severity": "medium",
    "pattern_code": "1-7-5"
  }
]
```

### 예시 5 — [TP] 1-6 전문성 + 1-1 진실성: 사실/의견 혼재와 전문성의 경계
기사 제목: "터졌다 하면 대형참사…'한화 리스크' 진행형"
기사 요약: 한화 계열사에서 발생한 사고들을 나열하며 '한화 리스크가 진행형'이라고 단정. 과거 사고와 현재 사안의 인과관계나 구조적 분석 없이 '리스크 진행형'이라는 프레이밍을 사실처럼 기술.
올바른 분석:
```json
[
  {
    "matched_text": "'한화 리스크' 진행형",
    "reasoning": "신문윤리위는 '사실에 기반하지 않은 의견을 보도기사에 혼재시켰다'고 판단했다. '리스크 진행형'은 기자의 해석이지 확인된 사실이 아니며, 이를 사실 보도의 형식으로 기술한 것이 핵심 위반이다. 이 사례는 1-6-1(심층성 부족)과 1-1-4(사실/의견 혼재)의 경계선에 있다. 구분 기준: '기사에 적힌 내용이 사실과 의견을 혼재시킨 것인가'(→1-1-4) vs '다뤄야 할 구조적 맥락을 안 다루고 파편적으로 보도한 것인가'(→1-6-1). 이 기사는 의견을 사실로 포장한 것이므로 1-1-4가 우선 적용된다. 핵심 질문: 기사가 의견을 사실처럼 기술했는가(작위 → 1-1-4), 다뤄야 할 맥락을 빠뜨렸는가(부작위 → 1-6-1)?",
    "severity": "medium",
    "pattern_code": "1-1-4"
  }
]
```

### 예시 6 — [TP] 1-7 언어: 제목-본문 괴리와 갈등 조장
기사 제목: "공장 세우고 동료 때린 '그들(해고자)'이 돌아온다"
기사 요약: 해고자의 노조 활동을 허용하는 노조법 개정안 통과를 보도하면서, 동료를 폭행해 해고된 특정 사례를 제목에 내세워 마치 전체 해고자(2,142명)가 모두 폭행범인 것처럼 표현.
올바른 분석:
```json
[
  {
    "matched_text": "공장 세우고 동료 때린 '그들(해고자)'이 돌아온다",
    "reasoning": "신문윤리위는 '2,142명의 해고자 중 폭행으로 해고된 사람이 얼마인지 기사에 나와있지 않음에도, 제목이 전체 해고자를 폭행범으로 일반화했다'고 판단했다. 이 제목은 두 가지 점에서 위반이다: (1)제목이 본문 내용과 부합하지 않으며, (2)법 개정에 대한 부정적 시각을 부추기기 위해 자극적 표현을 사용. 1-3-4(갈등 조장 프레이밍)와의 구분 — 여기서는 이분법적 대결 구도 설정이 아니라, 본문에 없는 내용을 제목이 왜곡한 것이 핵심이므로 제목의 원칙 위반이 우선 적용된다.",
    "severity": "high",
    "pattern_code": "1-7-2"
  }
]
```

### 예시 7 — [TP] 1-8 디지털: AI 생성 콘텐츠 품질 관리 소홀
기사 제목: (가상 사례) "AI 생성 뉴스에서 현직 대통령을 '전 대통령'으로 오표기"
기사 요약: AI(LLM) 모델이 자동 생성한 뉴스 기사에서 현직 대통령의 직함을 '전 대통령'으로 잘못 표기하는 AI 환각(hallucination) 오류가 발생. 편집부가 이를 검증·교정하지 않고 그대로 게재.
올바른 분석:
```json
[
  {
    "matched_text": "AI가 생성한 기사에서 현직 대통령을 '전 대통령'으로 표기",
    "reasoning": "AI 생성 콘텐츠의 사실 검증은 편집부의 책임이다. AI 도구 사용 자체가 아니라, AI 출력물에 대한 편집 과정의 부재가 문제다. 이것은 1-1-1(사실 검증 부실)에도 해당하지만, 1-1-1이 '결과'라면 1-8-2는 그 '원인'에 해당하는 패턴이다. 즉, AI 기술 활용이라는 새로운 제작 방식에서 품질 관리 체계가 부재하여 사실 검증 부실이라는 결과가 발생한 것이므로 1-8-2가 우선 적용된다.",
    "severity": "medium",
    "pattern_code": "1-8-2"
  }
]
```

### 예시 8 — [TN] 탐사보도의 강한 표현은 양질의 보도일 수 있다
기사 제목: "'감금·성폭행'…목포 '옛 동명원' 피해자들의 증언" (전남일보, 이달의 기자상 수상)
기사 요약: 장애인 수용시설에서 수십 년간 자행된 감금, 성폭행, 강제 노역 실태를 피해자 증언과 문서 증거로 고발한 탐사보도.
올바른 분석:
```json
[]
```
판단 근거: '감금', '성폭행' 등 강한 표현이 등장하여 1-7-4(자극적 표현)로, 피해자 관점 중심 서술이 1-3-1(관점 다양성 부족)으로 오탐될 위험이 높다. 그러나 사건의 심각성과 공익적 가치를 고려하면, 이러한 표현은 사실의 무게에 부합하는 정당한 저널리즘이다. 기사의 주제가 인권·범죄와 관련된다는 이유만으로 문제 보도로 판정해서는 안 된다.

### 예시 9 — [TN] 환경 탐사보도의 극단적 비유는 양질의 보도일 수 있다
기사 제목: "추적: 지옥이 된 바다" (한국일보, 이달의 기자상 수상)
기사 요약: 불법 어업과 해양 오염으로 파괴된 해양 생태계의 실태를 장기간 추적 취재하여 고발한 탐사보도.
올바른 분석:
```json
[]
```
판단 근거: '지옥이 된 바다'라는 극단적 비유가 1-7-3(과장과 맥락 왜곡)으로 오탐될 위험이 있다. 그러나 환경 파괴의 심각성을 전달하기 위한 서사적 표현이며, 장기간 현장 취재에 기반한 팩트가 뒷받침된다. 정치적 비판이나 사회 고발이 구체적 팩트에 근거한 보도는 편향이나 과장이 아니다.

## 출력 형식
```json
[
  {
    "matched_text": "문제가 되는 기사 원문 인용 (1~2문장)",
    "reasoning": "이 텍스트가 왜 문제이고 어떤 보도관행 기준을 위반했는지 근거 (1~2문장)",
    "severity": "high|medium|low",
    "pattern_code": "1-1-1"
  }
]
```"""


def call_haiku(
    article_text: str,
    pattern_catalog_text: str,
    vector_candidates: list[VectorCandidate],
) -> tuple[list[HaikuDetection], str]:
    """Haiku를 호출하여 패턴을 식별. (detections, raw_response) 반환."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # 벡터 후보 ★ 강조
    candidate_codes = {c.pattern_code for c in vector_candidates}
    marked_catalog = []
    for line in pattern_catalog_text.split("\n"):
        code = line.split(":")[0].strip()
        if code in candidate_codes:
            marked_catalog.append(f"★ {line}")
        else:
            marked_catalog.append(f"  {line}")
    catalog_text = "\n".join(marked_catalog)

    user_message = f"""## 패턴 목록
{catalog_text}

## 기사 전문
{article_text}"""

    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2048,
        system=_HAIKU_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
    )

    raw = response.content[0].text
    detections = _parse_haiku_response(raw)

    # 중복 pattern_code 제거 (첫 번째만 유지)
    seen_codes = set()
    unique_detections = []
    for d in detections:
        if d.pattern_code not in seen_codes:
            seen_codes.add(d.pattern_code)
            unique_detections.append(d)
    detections = unique_detections

    return detections, raw


def _parse_haiku_response(text: str) -> list[HaikuDetection]:
    """Haiku JSON 응답 파싱."""
    # 마크다운 코드블록 제거
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # JSON 배열 추출
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        logger.warning("Haiku response: JSON array not found")
        return []

    try:
        items = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        logger.warning(f"Haiku JSON parse error: {e}")
        return []

    detections = []
    for item in items:
        if isinstance(item, dict) and "pattern_code" in item:
            detections.append(
                HaikuDetection(
                    pattern_code=item.get("pattern_code", ""),
                    matched_text=item.get("matched_text", ""),
                    severity=item.get("severity", "medium"),
                    reasoning=item.get("reasoning", ""),
                )
            )
    return detections



# ── 메인 함수 ────────────────────────────────────────────────────

def match_patterns(
    chunks: list[str],
    article_text: str,
    threshold: Optional[float] = None,
) -> PatternMatchResult:
    """청크 리스트 + 기사 전문으로 패턴 매칭 수행.

    Args:
        chunks: 청킹된 텍스트 리스트
        article_text: 기사 전문 (Haiku에 전달)
        threshold: 벡터 검색 threshold (None이면 환경변수 기본값)

    Returns:
        PatternMatchResult
    """
    sb_url, sb_key = _get_supabase_config()
    t = threshold if threshold is not None else VECTOR_THRESHOLD

    # 1. 패턴 카탈로그 로드
    catalog = _load_pattern_catalog(sb_url, sb_key)
    catalog_text = _build_pattern_list_text(catalog)

    # 2. 청크 임베딩 생성
    if chunks:
        embeddings, emb_tokens = generate_embeddings(chunks)
    else:
        # 청크가 없으면 기사 전문을 단일 청크로
        embeddings, emb_tokens = generate_embeddings([article_text])

    # 3. 벡터 검색
    candidates = search_vectors(embeddings, sb_url, sb_key, threshold=t)

    # 4. Haiku 호출
    detections, raw_response = call_haiku(article_text, catalog_text, candidates)

    # 5. 밸리데이션
    valid_ids, valid_codes, hallucinated = validate_pattern_codes(
        detections, sb_url, sb_key
    )

    return PatternMatchResult(
        vector_candidates=candidates,
        haiku_detections=detections,
        validated_pattern_ids=valid_ids,
        validated_pattern_codes=valid_codes,
        hallucinated_codes=hallucinated,
        haiku_raw_response=raw_response,
        embedding_tokens=emb_tokens,
    )
