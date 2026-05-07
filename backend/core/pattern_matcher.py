# backend/core/pattern_matcher.py
"""
CR-Check — 벡터 검색 + Sonnet Solo 패턴 식별 모듈

파이프라인 전반부 (M5 Sonnet Solo 아키텍처):
1. 청크별 임베딩 생성 (OpenAI text-embedding-3-small)
2. 벡터 검색 — search_pattern_candidates() RPC
3. Sonnet Solo 호출 — 전체 패턴 목록 + 벡터 후보 ★ 강조 + Devil's Advocate CoT
4. 밸리데이션 — 코드→ID 변환 + 환각 코드 제거
※ [DEPRECATED] 2-Call(Haiku→Sonnet), 1-Call(게이트+Haiku) 코드는 비교용 보존
"""

import os
import json
import re
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx
from anthropic import Anthropic
from openai import OpenAI
from dotenv import load_dotenv

from .db import _get_supabase_config

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# ── 설정 ─────────────────────────────────────────────────────────

EMBEDDING_MODEL = "text-embedding-3-small"
SONNET_MODEL = "claude-sonnet-4-5-20250929"
VECTOR_THRESHOLD = float(os.environ.get("VECTOR_THRESHOLD", "0.2"))
VECTOR_MATCH_COUNT = 7


# ── 데이터 구조 ──────────────────────────────────────────────────

@dataclass
class VectorCandidate:
    """벡터 검색 후보."""
    pattern_id: int
    pattern_code: str
    pattern_name: str
    similarity: float


@dataclass
class HaikuDetection:
    """Haiku가 확정한 패턴."""
    pattern_code: str
    matched_text: str
    severity: str  # high / medium / low
    reasoning: str


@dataclass
class PatternMatchResult:
    """패턴 매칭 결과."""
    vector_candidates: list[VectorCandidate] = field(default_factory=list)
    haiku_detections: list[HaikuDetection] = field(default_factory=list)
    validated_pattern_ids: list[int] = field(default_factory=list)
    validated_pattern_codes: list[str] = field(default_factory=list)
    hallucinated_codes: list[str] = field(default_factory=list)
    haiku_raw_response: str = ""
    embedding_tokens: int = 0
    # STEP 5-A 블록3: 카탈로그(active v3 leaf) 외 코드 (구버전·부모·inactive)
    # STEP 6 임베딩 재생성 전까지 추적용
    unmatched_vector_candidates: list[str] = field(default_factory=list)
    suspect_result: object = None  # SuspectResult (2-Call 모드에서만 사용)


@dataclass
class SuspectResult:
    """1차 의심 식별 결과 (Sonnet Solo의 overall_assessment 보존용 + 2-Call 레거시 호환).

    pattern_matcher_legacy.match_patterns_2call에서도 동일한 클래스를 사용하므로
    legacy 모듈이 이 위치에서 import한다.
    """
    overall_assessment: str = ""
    suspect_categories: list[str] = field(default_factory=list)
    raw_response: str = ""


# ── 전체 패턴 목록 (Haiku 프롬프트용) ────────────────────────────
# DB에서 동적 로드하되, 메타 패턴(1-4-1, 1-4-2) 제외
# 캐시: 벤치마크 26건 실행 시 1회만 DB 조회

# v3 leaf 코드 정규식 (예: 1-1-a, 6-2-c).
# 현재 DB에서 hierarchy_level=2가 비어 있고 부모·leaf 모두 level=3에 저장되어
# 있으므로, leaf 판별은 hierarchy_level이 아닌 code 정규식으로 수행한다.
_LEAF_CODE_RE = re.compile(r'^[0-9]+-[0-9]+-[a-z]+$')

_pattern_catalog_cache: list[dict] | None = None


def _load_pattern_catalog(sb_url: str, sb_key: str) -> list[dict]:
    """DB에서 v3 leaf 패턴 카탈로그 로드 + 계층 경로 이름 보강. 결과 캐시.

    전략 (STEP 5-A 블록2 STEP 1):
    1. is_meta_pattern=FALSE 조건만으로 전체 패턴(부모·leaf 모두) 한 번에 로드.
       inactive 부모도 계층 경로 이름 구성에 필요하므로 is_active 필터는
       DB 레이어에서 적용하지 않고 Python 레이어에서 처리한다.
    2. id → row 매핑을 만든 뒤 parent_pattern_id FK를 따라가며
       각 leaf에 parent_name과 grandparent_name을 in-memory로 보강.
    3. 최종 반환은 is_active=TRUE AND code ~ '^[0-9]+-[0-9]+-[a-z]+$'
       (v3 leaf)만 포함. 부모는 출력 후보에서 제외하고 이름 참조용으로만
       사용한다.

    각 leaf row에 다음 키가 존재한다:
      id, code, name, description, search_text, detection_strategy,
      report_framing, hierarchy_level, parent_pattern_id,
      is_meta_pattern, is_active, parent_name, grandparent_name
    parent_pattern_id가 NULL이거나 부모를 찾지 못하면
    parent_name / grandparent_name은 None.
    """
    global _pattern_catalog_cache
    if _pattern_catalog_cache is not None:
        return _pattern_catalog_cache

    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    select_fields = (
        "id,code,name,description,search_text,"
        "detection_strategy,report_framing,"
        "hierarchy_level,parent_pattern_id,is_meta_pattern,is_active"
    )
    r = httpx.get(
        f"{sb_url}/rest/v1/patterns"
        f"?select={select_fields}"
        "&is_meta_pattern=eq.false"
        "&order=code",
        headers=headers,
    )
    r.raise_for_status()
    all_rows: list[dict] = r.json()

    # 계층 경로 이름 추출용 매핑 (inactive 부모도 포함)
    by_id: dict[int, dict] = {row["id"]: row for row in all_rows}

    catalog: list[dict] = []
    for row in all_rows:
        # 출력 후보 조건: active leaf만
        if not row.get("is_active"):
            continue
        if not _LEAF_CODE_RE.match(row["code"]):
            continue

        parent_name: str | None = None
        grandparent_name: str | None = None
        parent_id = row.get("parent_pattern_id")
        if parent_id is not None and parent_id in by_id:
            parent = by_id[parent_id]
            parent_name = parent.get("name")
            gp_id = parent.get("parent_pattern_id")
            if gp_id is not None and gp_id in by_id:
                grandparent_name = by_id[gp_id].get("name")

        enriched = dict(row)
        enriched["parent_name"] = parent_name
        enriched["grandparent_name"] = grandparent_name
        catalog.append(enriched)

    _pattern_catalog_cache = catalog
    return _pattern_catalog_cache


def _build_pattern_catalog_entry(row: dict) -> str:
    """단일 leaf 패턴의 카탈로그 텍스트 한 블록 생성 (vector·structural 공통).

    출력 형식:
        [{code}] {name}
        계층 경로: {grandparent_name} > {parent_name} > {name}
        판단 기준: {description}
        주요 어휘: {search_text}
        리포트 서술 방향: {report_framing}

    NULL 처리 규칙 (STEP 5-A 블록2 STEP 2):
    - grandparent_name 없음 → 계층 경로 체인에서 생략
    - parent_name·grandparent_name 모두 없음 → '계층 경로' 행 자체 생략
    - search_text 없음(NULL/빈 문자열) → '주요 어휘' 행 자체 생략
    - description 없음 → '판단 기준' 행 자체 생략 (defensive; 정상 데이터에서는 발생 안 함)
    - report_framing 없음 → 자동 생성:
        · parent_name 있음:
            "구체 패턴({code}) '{name}'의 판단 기준을 중심으로 설명하되,
             필요 시 {parent_name} 맥락으로 확장"
        · parent_name 없음:
            "구체 패턴({code}) 지적 → 상위 보도윤리 맥락으로 확장"

    인자 row 형식: _load_pattern_catalog() 반환 항목과 동일.
        필요 키: code, name, description, search_text, report_framing,
                parent_name, grandparent_name
    """
    code = row["code"]
    name = row["name"]
    description = (row.get("description") or "").strip()
    search_text = (row.get("search_text") or "").strip()
    report_framing = (row.get("report_framing") or "").strip()
    parent_name = row.get("parent_name")
    grandparent_name = row.get("grandparent_name")

    lines: list[str] = [f"[{code}] {name}"]

    # 계층 경로: grandparent → parent → self
    chain_parts: list[str] = []
    if grandparent_name:
        chain_parts.append(grandparent_name)
    if parent_name:
        chain_parts.append(parent_name)
    if chain_parts:
        chain_parts.append(name)
        lines.append(f"계층 경로: {' > '.join(chain_parts)}")

    if description:
        lines.append(f"판단 기준: {description}")

    if search_text:
        lines.append(f"주요 어휘: {search_text}")

    # report_framing NULL fallback (parent 유무 분기)
    if not report_framing:
        if parent_name:
            report_framing = (
                f"구체 패턴({code}) '{name}'의 판단 기준을 중심으로 설명하되, "
                f"필요 시 {parent_name} 맥락으로 확장"
            )
        else:
            report_framing = f"구체 패턴({code}) 지적 → 상위 보도윤리 맥락으로 확장"
    lines.append(f"리포트 서술 방향: {report_framing}")

    return "\n".join(lines)


def _build_pattern_list_text(patterns: list[dict]) -> str:
    """Sonnet에 전달할 패턴 카탈로그 텍스트 (3섹션 구조) 생성.

    구조 (STEP 5-A 블록2 STEP 3):
    [섹션 0] ## 패턴 카탈로그 공통 안내 — 계층 경로·주요 어휘 의미 + vector·structural 선택 규칙
    [섹션 1] ## 벡터 검색 기반 패턴 — vector_rows의 카탈로그 엔트리
    [섹션 2] ## 구조적 판단 필수 검토 패턴 — 1줄 안내 + structural_rows 엔트리

    인자 patterns는 _load_pattern_catalog() 반환 (active leaf만,
    계층 경로 보강 후). detection_strategy 값으로 두 그룹을 분리한다.
    Few-shot 예시는 이 함수에 포함하지 않는다 (system 프롬프트 측 책임).
    """
    vector_rows = [p for p in patterns if p.get("detection_strategy") == "vector"]
    structural_rows = [p for p in patterns if p.get("detection_strategy") == "structural"]

    # [섹션 0] 공통 안내
    common_intro = (
        "※ '계층 경로'는 분류상 위치를 보여주는 참고 정보입니다.\n"
        "   실제 판단과 리포트 서술은 '판단 기준'과 '리포트 서술 방향'을 우선합니다.\n"
        "※ '주요 어휘'는 탐지 단서 예시일 뿐 필수 포함 조건이 아닙니다.\n"
        "   같은 의미의 다른 표현도 판단 기준에 해당하면 선택할 수 있습니다.\n"
        "※ vector 패턴: 기사 원문에서 문제가 되는 구체적 문장·표현을\n"
        "   matched_text로 인용할 수 있을 때만 선택합니다.\n"
        "※ structural 패턴: 기사에 \"있어야 할 관점·반론·맥락\"이 빠진 경우도\n"
        "   감지 대상입니다. matched_text에는 원문 인용 대신 구조적 부재 상황을\n"
        "   간결히 묘사할 수 있습니다. 단, reasoning에서 \"누구의 관점/반론/맥락이\n"
        "   빠졌는지\"를 구체적으로 설명할 수 있을 때만 선택합니다.\n"
        "   단순히 기사 길이가 짧거나 속보라는 이유만으로 선택하지 않습니다."
    )
    sections: list[str] = ["## 패턴 카탈로그 공통 안내\n\n" + common_intro]

    # [섹션 1] 벡터 검색 기반 패턴
    if vector_rows:
        vector_blocks = [_build_pattern_catalog_entry(r) for r in vector_rows]
        sections.append("## 벡터 검색 기반 패턴\n\n" + "\n\n".join(vector_blocks))

    # [섹션 2] 구조적 판단 필수 검토 패턴
    if structural_rows:
        structural_header = (
            "## 구조적 판단 필수 검토 패턴\n"
            "※ 아래 패턴들은 벡터 검색 후보와 무관하게, 기사 구조 자체를\n"
            "   직접 검토하여 판단하십시오. ★ 표시와 무관하게 반드시 확인합니다."
        )
        structural_blocks = [_build_pattern_catalog_entry(r) for r in structural_rows]
        sections.append(structural_header + "\n\n" + "\n\n".join(structural_blocks))

    return "\n\n".join(sections)


# ── 임베딩 생성 ──────────────────────────────────────────────────

def generate_embeddings(texts: list[str]) -> tuple[list[list[float]], int]:
    """OpenAI 배치 API로 임베딩 생성. (texts, token_count) 반환."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    embeddings = [item.embedding for item in response.data]
    tokens = response.usage.total_tokens
    dim = len(embeddings[0]) if embeddings else 0
    logger.info(f"임베딩 생성: {len(texts)}건 입력, {len(embeddings)}건 출력, 차원={dim}, 토큰={tokens}")
    return embeddings, tokens


# ── 벡터 검색 ────────────────────────────────────────────────────

def search_vectors(
    embeddings: list[list[float]],
    sb_url: str,
    sb_key: str,
    threshold: float = VECTOR_THRESHOLD,
    match_count: int = VECTOR_MATCH_COUNT,
) -> list[VectorCandidate]:
    """청크별 벡터 검색 후 결과 집계 (패턴별 최고 유사도)."""
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }
    best: dict[str, VectorCandidate] = {}

    logger.info(f"벡터 검색 시작: {len(embeddings)}건 임베딩, threshold={threshold}, match_count={match_count}")
    if embeddings:
        logger.info(f"임베딩 차원: {len(embeddings[0])}")

    for idx, emb in enumerate(embeddings):
        try:
            r = httpx.post(
                f"{sb_url}/rest/v1/rpc/search_pattern_candidates",
                headers=headers,
                json={
                    "query_embedding": emb,
                    "match_threshold": threshold,
                    "match_count": match_count,
                },
                timeout=30,
            )
            r.raise_for_status()
            rows = r.json()
            if not rows:
                logger.warning(
                    f"청크 {idx}: RPC 성공(HTTP {r.status_code}), 결과 0건 — "
                    f"threshold={threshold}, match_count={match_count}"
                )
            else:
                logger.info(f"청크 {idx}: RPC 성공(HTTP {r.status_code}), 결과 {len(rows)}건")
            for row in rows:
                code = row["pattern_code"]
                sim = row["similarity"]
                if code not in best or sim > best[code].similarity:
                    best[code] = VectorCandidate(
                        pattern_id=row["pattern_id"],
                        pattern_code=code,
                        pattern_name=row["pattern_name"],
                        similarity=sim,
                    )
        except httpx.HTTPStatusError as e:
            logger.error(f"청크 {idx}: RPC HTTP 에러 {e.response.status_code} — {e.response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"청크 {idx}: RPC 호출 실패 [{type(e).__name__}] — {e}")
            raise

    # 유사도 내림차순 정렬
    result = sorted(best.values(), key=lambda x: x.similarity, reverse=True)
    logger.info(f"벡터 검색 완료: 고유 패턴 {len(result)}건")
    return result


# ── Sonnet Solo 1-Call (게이트 없음 + Devil's Advocate CoT) ──────

# [DEPRECATED - STEP 5-B에서 pattern_confusion_pairs 테이블 기반으로 재도입 예정]
# 구버전 코드 오염 방지를 위해 프롬프트 문자열에서 제거.
# 기존 내용:
# ## 자주 혼동되는 패턴 쌍
# - **1-1 vs 1-4**: 팩트 자체가 틀렸으면 1-1. 팩트는 맞지만 사실과 의견을 섞었으면 1-4.
# - **3-1 vs 3-2**: 반론 없이 한쪽만 인용했으면 3-1. 양쪽을 언급했지만 틀이 편향적이면 3-2.
# - **3-1 vs 3-4**: 반론 없이 전달했으면 3-1. 배경·맥락 생략으로 판단 정보 부족이면 3-4.
# - **7-2 vs 7-5**: 이념적 틀로 규정(빨갱이, 수구)이면 7-2. 감정 자극 과장(충격, 발칵)이면 7-5.
# - **7-3 vs 7-4**: 본문이 과장/왜곡이면 7-3. 본문은 정상이고 제목만 과장이면 7-4.

_SONNET_SOLO_PROMPT = """\
당신은 한국 뉴스 기사의 보도 품질을 평가하는 전문 분석가입니다.

기사를 읽고, 아래 '패턴 목록'과 대조하여 문제적 보도관행 패턴을 식별하세요.

## 분석 절차

1. **overall_assessment 작성 (필수, 반드시 먼저)**:
   기사의 전반적인 보도 품질을 1~2문장으로 평가하세요.
   양질의 보도라도 특정 측면에서 윤리 문제를 동시에 가질 수 있습니다.
   전반적 품질 평가와 개별 패턴 판단은 독립적입니다.

2. **detections 작성**:
   각 패턴 후보에 대해 독립적으로 해당/비해당을 판단하세요.
   기사가 전반적으로 양질이더라도, 특정 패턴에 해당하는 구체적 근거가 있으면 선택하세요.
   어떤 패턴도 해당하지 않으면 detections를 빈 배열 []로 두세요.

## 핵심 원칙: 정밀도 우선
- 확신이 없으면 선택하지 마세요. 누락보다 오탐이 더 해롭습니다.
- 기사에서 해당 문제를 보여주는 **구체적 문장이나 표현을 특정할 수 없다면** 그 패턴을 선택하지 마세요.
- 기사의 공익적 목적에 부합하는 표현(탐사보도의 강렬한 묘사, 인권 고발의 피해 서술 등)은 그 자체로 위반이 아닙니다.

## ★ 후보 패턴 활용
★ 표시된 패턴은 벡터 검색으로 사전 선별된 유력 후보입니다.
- ★ 패턴을 먼저 우선적으로 검토하세요.
- 단, ★ 표시가 없는 패턴도 기사에 명확히 해당하면 동등하게 선택하세요.

## 기사 길이별 가이드
- 200자 미만: 최대 1~2개
- 200~500자: 최대 2~3개
- 500~2000자: 최대 3~4개
- 2000자 이상: 최대 4~5개. 근거가 매우 명확한 경우에만.
- 같은 패턴을 여러 번 선택하지 마세요.

## 기타 규칙
1. 기사에서 **실제로 확인되는** 문제만 선택하세요.
2. "(텍스트 분석 대상 아님)"으로 표시된 패턴은 선택하지 마세요.
3. 유사 패턴 중 더 정확한 쪽을 선택하세요.
4. 문제가 발견되지 않으면 detections를 빈 배열 []로 두세요.
5. 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.
6. pattern_code는 반드시 위 패턴 카탈로그에 존재하는 v3 leaf 코드만 사용하라.
   부모 코드(예: 1-1, 3-1) 또는 카탈로그에 없는 코드는 출력하지 마라.
7. '리포트 서술 방향'은 참고용 힌트입니다. reasoning에서 장황하게 서술하지 말고,
   기사 내 구체적 근거를 바탕으로 1~2문장의 간결한 감지 사유만 작성하세요.

## 참고 예시

### 예시 1 — [TP] 1-5-h: 통계 맥락 무시 (코로나 데이터)
기사 제목: "최근 한달 확진 10만명당 확진률 80%↑, 치명률 美·브라질보다 높아… 'K방역의 치욕'"
기사 요약: 코로나19 지표를 두 시점에서 단순 비교하여 한국이 "세계 최악"이라고 단정. 실제 인구 대비 확진자 수는 미국의 1.8% 수준.
올바른 분석:
```json
{{
  "overall_assessment": "코로나19 국가 간 비교를 시도한 시의적절한 보도이나, 특정 두 시점의 증가율만으로 비교하는 것은 통계적으로 불충분하다. 절대 수치(인구 대비 확진자 수)를 의도적으로 배제한 데이터 오용이 확인된다.",
  "detections": [
    {{
      "matched_text": "10만 명당 확진자 수가 80% 늘어 세계 최고 수준의 증가율을 기록",
      "reasoning": "특정 두 시점의 증가율만 비교하면 기저효과·계절성을 무시하게 된다. 실제 절대 수치(인구 대비 확진자 수)를 제시하지 않고 증가율만 부각한 것이 핵심 오류로, 통계 맥락을 의도적으로 배제한 데이터 오용이다.",
      "severity": "high",
      "pattern_code": "1-5-h"
    }}
  ]
}}
```

### 예시 2 — [TP] 3-2-c + 6-2-c: 사례 일반화 + 제목 침소봉대
기사 제목: "부작용 불안한데…쉬지도 못하는데…선택도 못하는데… 2030 '접종 보이콧'"
기사 요약: 접종을 꺼리는 3명의 사례를 '보이콧'(공동 거부)으로 제목에 표현. 실제 예약률 61.3%.
올바른 분석:
```json
{{
  "overall_assessment": "백신 접종에 대한 청년층의 우려를 다룬 시의적절한 보도이나, 3개의 개별 사례를 '보이콧'이라는 집단적 행위로 일반화한 제목에서 사실과 의견의 혼재 및 실제 예약률 61.3%와 배치되는 과장이 확인된다.",
  "detections": [
    {{
      "matched_text": "2030 '접종 보이콧'",
      "reasoning": "'보이콧'은 집단적 거부를 뜻하지만 본문에는 3개의 개별 사례만 있을 뿐이다. 3개 사례를 2030세대 전체의 집단행동으로 일반화하여 소수 사례를 다수 여론처럼 포장한 점이 핵심이다.",
      "severity": "high",
      "pattern_code": "3-2-c"
    }},
    {{
      "matched_text": "제목에서 3개 개별 사례를 '2030 보이콧'으로 일반화하여 부각, 본문의 61.3% 예약률 맥락은 누락",
      "reasoning": "실제 예약률 61.3%인 상황에서 3개 개별 사례를 '보이콧'으로 제목에 부각한 것은 부차적 일부에 불과한 내용을 제목 핵심처럼 키운 침소봉대다.",
      "severity": "medium",
      "pattern_code": "6-2-c"
    }}
  ]
}}
```

### 예시 3 — [TP] 4-3-b: 차별·혐오 표현 ('눈먼 돈')
기사 제목: "'눈먼 돈' 청년 전세대출"
기사 요약: 전세대출 사기 보도에서 시각장애인 비하 관용구를 제목에 사용.
올바른 분석:
```json
{{
  "overall_assessment": "전세대출 사기 사건의 공익적 보도 가치가 있으나, '눈먼 돈'은 시각장애를 부정적 의미로 사용하는 차별적 관용구다. 보도 내용의 공익성과 무관하게 차별적 언어 사용이 확인된다.",
  "detections": [
    {{
      "matched_text": "'눈먼 돈' 청년 전세대출",
      "reasoning": "'눈먼 돈'은 시각장애인 비하 표현이다. 문제는 단순한 자극적 표현이 아니라, 시각장애를 부정적 의미로 사용하는 차별적 관용구라는 점이다.",
      "severity": "medium",
      "pattern_code": "4-3-b"
    }}
  ]
}}
```

### 예시 4 — [TP] 1-4-d: 의견의 사실화 (한화 리스크)
기사 제목: "터졌다 하면 대형참사…'한화 리스크' 진행형"
기사 요약: 과거 사고를 나열하며 '한화 리스크 진행형'이라고 단정. 구조적 분석 없이 프레이밍.
올바른 분석:
```json
{{
  "overall_assessment": "기업의 안전 관련 이슈를 추적하는 공익적 보도 시도이나, '한화 리스크 진행형'은 기자의 해석이지 확인된 사실이 아니다. 의견을 사실 보도 형식으로 포장한 문제가 확인된다.",
  "detections": [
    {{
      "matched_text": "'한화 리스크' 진행형",
      "reasoning": "'리스크 진행형'은 기자의 주관적 해석이지 확인된 사실이 아니다. 가치 판단 표현을 사실 서술어 자리에 배치하여 기자 의견을 객관 사실인 것처럼 제시한 점이 핵심이다.",
      "severity": "medium",
      "pattern_code": "1-4-d"
    }}
  ]
}}
```

### 예시 5 — [TP] 6-2-c: 제목-본문 침소봉대 (해고자 일반화)
기사 제목: "공장 세우고 동료 때린 '그들(해고자)'이 돌아온다"
기사 요약: 노조법 개정안 보도에서 폭행 사례를 전체 해고자(2,142명)로 일반화한 제목.
올바른 분석:
```json
{{
  "overall_assessment": "노조법 개정이라는 중요한 사회적 사안을 보도하고 있으나, 제목이 소수 사례를 전체 집단으로 일반화하여 본문과 부합하지 않으며 자극적 표현을 사용했다.",
  "detections": [
    {{
      "matched_text": "2,142명 중 폭행 사례 수가 기사에 없음에도 제목이 전체 해고자를 폭행범으로 부각",
      "reasoning": "2,142명 중 폭행 해고자 수가 기사에 없음에도 소수 사례를 전체로 부각한 제목이다. 부차적 일부에 불과한 내용을 제목 핵심으로 키운 침소봉대가 핵심이다.",
      "severity": "high",
      "pattern_code": "6-2-c"
    }}
  ]
}}
```

### 예시 6 — [TN] 탐사보도: 양질의 보도
기사 제목: "'감금·성폭행'…목포 '옛 동명원' 피해자들의 증언" (전남일보, 이달의 기자상 수상)
기사 요약: 장애인 수용시설의 감금·성폭행 실태를 피해자 증언과 문서 증거로 고발한 탐사보도.
올바른 분석:
```json
{{
  "overall_assessment": "피해자 증언과 문서 증거에 기반한 탐사보도로 공익적 가치가 높다. 개별 패턴 검토: '감금·성폭행' 등 강한 표현은 사건의 심각성에 부합하므로 자극·과장 어휘 패턴 해당 아님. 피해자 관점 중심 서술은 인권 탐사보도의 정당한 방법론이므로 관점 다양성 부족 패턴 해당 아님. 구체적 위반 근거 없음.",
  "detections": []
}}
```

### 예시 7 — [TN] 환경 탐사보도: 양질의 보도
기사 제목: "추적: 지옥이 된 바다" (한국일보, 이달의 기자상 수상)
기사 요약: 해양 오염 실태를 장기간 추적 취재하여 고발한 탐사보도.
올바른 분석:
```json
{{
  "overall_assessment": "장기간 현장 취재에 기반한 환경 탐사보도다. 개별 패턴 검토: '지옥이 된 바다'는 구체적 팩트에 근거한 서사적 표현으로 과장·맥락 왜곡 패턴 해당 아님. 구체적 위반 근거 없음.",
  "detections": []
}}
```

## 구조적 패턴 감지 예시

이 섹션은 structural 패턴의 reasoning 작성 방식을 보여주는 예시입니다.
패턴 카탈로그 정의와 별도로 배치됩니다.
matched_text에는 원문 인용이 아니라 구조적 부재 상황을 묘사합니다.

### [structural] 3-1-b: 편향된 취재원 구성
기사 제목: (가상) "정부, 규제 완화 정책 전면 시행…'경제 도약의 전환점'"
기사 요약: 정부의 규제 완화 정책을 찬성 측 전문가 2명만 인용하여 보도.
반대 측 의견이나 우려, 피해 가능성에 대한 언급이 전무.
올바른 분석:
```json
{{
  "overall_assessment": "정부 정책을 신속하게 보도하는 시의적절한 보도이나, 찬성 측 전문가 2명만 인용하고 반대 측 의견이나 피해 가능성을 전혀 다루지 않아 균형성에 문제가 있다.",
  "detections": [
    {{
      "matched_text": "찬성 측 전문가 2명만 인용하고, 반대 측 의견이나 피해 가능성을 다룬 취재원은 제시하지 않음",
      "reasoning": "이해관계가 복잡한 사안임에도 찬성 입장의 취재원만 선별 인용하고 반대 의견 취재원이 누락되어 기사 균형이 무너졌다. 본문 어디에도 반대 측 인용이 없다는 구조적 부재가 핵심이다.",
      "severity": "high",
      "pattern_code": "3-1-b"
    }}
  ]
}}
```

## 출력 형식

⚠️ JSON 형식 주의:
- "matched_text" 값은 반드시 하나의 문자열이어야 합니다.
- 여러 문구를 포함하려면 하나의 문자열 안에서 ' / '로 구분하세요.
- ❌ 틀린 예: "matched_text": "첫번째 문장", "두번째 문장"
- ✅ 올바른 예: "matched_text": "첫번째 문장 / 두번째 문장"
- JSON 문법 오류가 발생하면 분석 결과 전체가 유실됩니다.

반드시 아래 JSON 형식으로만 응답하라. 다른 텍스트를 포함하지 마라.
```json
{{
  "overall_assessment": "기사의 전반적 품질 평가. 확인된 문제점 또는 문제 없음 판단 근거.",
  "detections": [
    {{
      "matched_text": "문제가 되는 기사 원문 인용 (1~2문장)",
      "reasoning": "왜 문제이고 어떤 기준을 위반했는지 (1~2문장)",
      "severity": "high|medium|low",
      "pattern_code": "1-1-a"
    }}
  ]
}}
```"""


def _extract_solo_detections(data: dict) -> tuple[str, list[HaikuDetection]]:
    """파싱된 JSON dict에서 (overall_assessment, detections) 추출."""
    assessment = data.get("overall_assessment", "")
    raw_detections = data.get("detections", [])

    seen_codes = set()
    detections = []
    for item in raw_detections:
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

    return assessment, detections


def _fix_llm_json(json_str: str) -> str:
    """LLM이 생성한 비정형 JSON의 일반적 오류를 수정."""
    fixed = json_str
    # 1. 값 위치에서 복수 문자열을 하나로 합침
    #    ": "text1", "text2" (text2 뒤에 : 가 아닌 경우) → ": "text1 / text2"
    for _ in range(5):
        new_fixed = re.sub(
            r'(:\s*"[^"]*?")\s*,\s*"([^"]*?)"(?!\s*:)',
            lambda m: m.group(1)[:-1] + " / " + m.group(2) + '"',
            fixed,
            count=1,
        )
        if new_fixed == fixed:
            break
        fixed = new_fixed
    # 2. trailing comma 제거 (배열/객체 마지막 요소 뒤 쉼표)
    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
    return fixed


def _parse_solo_response(text: str) -> tuple[str, list[HaikuDetection]]:
    """Sonnet Solo 응답 파싱. 3단계 fallback으로 JSON 복구 시도."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # JSON 객체 추출
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        logger.warning("Solo response: JSON object not found")
        return "", []

    json_str = text[start : end + 1]

    # 1차 시도: 기존 json.loads()
    try:
        data = json.loads(json_str)
        logger.info("Solo JSON 1차 파싱 성공")
        return _extract_solo_detections(data)
    except json.JSONDecodeError as e:
        logger.warning(f"Solo JSON 1차 실패, 2차 복구 시도: {e}")

    # 2차 시도: LLM JSON 오류 수정 후 재시도
    try:
        fixed = _fix_llm_json(json_str)
        data = json.loads(fixed)
        logger.info("Solo JSON 2차 복구 성공")
        return _extract_solo_detections(data)
    except json.JSONDecodeError as e:
        logger.warning(f"Solo JSON 2차 실패, 3차 정규식 추출 시도: {e}")

    # 3차 시도: 정규식으로 pattern_code만 추출 (최소한의 결과)
    codes = re.findall(r'"pattern_code"\s*:\s*"([\d\-]+)"', json_str)
    if codes:
        # overall_assessment도 추출 시도
        oa_match = re.search(r'"overall_assessment"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str, re.DOTALL)
        assessment = oa_match.group(1) if oa_match else ""
        seen = set()
        detections = []
        for code in codes:
            if code not in seen:
                seen.add(code)
                detections.append(HaikuDetection(
                    pattern_code=code,
                    matched_text="",
                    severity="medium",
                    reasoning="",
                ))
        logger.warning(f"Solo JSON 3차 정규식 추출 사용: {[d.pattern_code for d in detections]}")
        return assessment, detections

    logger.warning("Solo JSON 모든 파싱 시도 실패, 빈 결과 반환")
    return "", []


def match_patterns_solo(
    chunks: list[str],
    article_text: str,
    threshold: Optional[float] = None,
) -> PatternMatchResult:
    """Sonnet Solo 1-Call: 게이트 없음 + Devil's Advocate CoT."""
    sb_url, sb_key = _get_supabase_config()
    t = threshold if threshold is not None else VECTOR_THRESHOLD

    # 1. 패턴 카탈로그 + 벡터 검색
    catalog = _load_pattern_catalog(sb_url, sb_key)
    catalog_text = _build_pattern_list_text(catalog)

    if chunks:
        embeddings, emb_tokens = generate_embeddings(chunks)
    else:
        embeddings, emb_tokens = generate_embeddings([article_text])
    candidates = search_vectors(embeddings, sb_url, sb_key, threshold=t)

    # 2. ★ 마크 적용 (vector 섹션만) + unmatched_vector_candidates 수집
    candidate_codes = {c.pattern_code for c in candidates}
    leaf_codes = {row["code"] for row in catalog}
    vector_leaf_codes = {
        row["code"] for row in catalog
        if row.get("detection_strategy") == "vector"
    }

    # vector candidate 중 active v3 leaf 카탈로그에 없는 코드 (구버전·부모·inactive)
    # STEP 6 임베딩 재생성 전까지 추적용. 자동 보정 금지.
    unmatched_vector_candidates = sorted(
        c for c in candidate_codes if c not in leaf_codes
    )
    if unmatched_vector_candidates:
        logger.warning(
            f"unmatched_vector_candidates: {unmatched_vector_candidates} "
            f"(STEP 6 임베딩 재생성 전까지 구버전 코드가 candidate로 올라올 수 있음)"
        )

    # ★ 마킹: [code] name 형식 매칭 + vector 섹션만 적용
    star_re = re.compile(r'^\[([^\]]+)\] ')
    marked_lines: list[str] = []
    current_section: str | None = None
    for line in catalog_text.split("\n"):
        if line.startswith("## 벡터 검색 기반 패턴"):
            current_section = "vector"
            marked_lines.append(line)
            continue
        if line.startswith("## 구조적 판단 필수 검토 패턴"):
            current_section = "structural"
            marked_lines.append(line)
            continue
        if line.startswith("## "):
            current_section = None
            marked_lines.append(line)
            continue
        m = star_re.match(line)
        if m and current_section == "vector":
            code = m.group(1)
            if code in candidate_codes and code in vector_leaf_codes:
                marked_lines.append(f"★ {line}")
                continue
        marked_lines.append(line)
    marked_catalog = "\n".join(marked_lines)

    # 3. Sonnet 호출
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_message = f"""## 패턴 목록
{marked_catalog}

## 기사 전문
{article_text}"""

    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2048,
        system=_SONNET_SOLO_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
    )

    raw = response.content[0].text
    assessment, detections = _parse_solo_response(raw)

    # 4. 밸리데이션
    valid_ids, valid_codes, hallucinated = validate_pattern_codes(
        detections, sb_url, sb_key
    )

    # 5. 벤치마크 호환용 SuspectResult
    suspect = SuspectResult(
        overall_assessment=assessment,
        suspect_categories=[],
        raw_response=raw,
    )

    return PatternMatchResult(
        vector_candidates=candidates,
        haiku_detections=detections,
        validated_pattern_ids=valid_ids,
        validated_pattern_codes=valid_codes,
        hallucinated_codes=hallucinated,
        haiku_raw_response=raw,
        embedding_tokens=emb_tokens,
        unmatched_vector_candidates=unmatched_vector_candidates,
        suspect_result=suspect,
    )


# ── 밸리데이션: 코드→ID 변환 + 환각 제거 ─────────────────────────

def validate_pattern_codes(
    detections: list[HaikuDetection],
    sb_url: str,
    sb_key: str,
) -> tuple[list[int], list[str], list[str]]:
    """패턴 코드를 DB에서 검증하고 ID로 변환.

    Returns:
        (valid_ids, valid_codes, hallucinated_codes)
    """
    if not detections:
        return [], [], []

    codes = [d.pattern_code for d in detections]
    codes_param = ",".join(f'"{c}"' for c in codes)

    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    r = httpx.get(
        f"{sb_url}/rest/v1/patterns?select=id,code&code=in.({codes_param})",
        headers=headers,
    )
    r.raise_for_status()
    db_patterns = {row["code"]: row["id"] for row in r.json()}

    valid_ids = []
    valid_codes = []
    hallucinated = []

    for code in codes:
        if code in db_patterns:
            valid_ids.append(db_patterns[code])
            valid_codes.append(code)
        else:
            hallucinated.append(code)
            logger.warning(f"Hallucinated pattern code removed: {code}")

    return valid_ids, valid_codes, hallucinated



# ──────────────────────────────────────────────────────────────────
# Legacy 코드는 backend/core/pattern_matcher_legacy.py로 분리됨
# (비교 실험 / reproducibility 목적 보존, 활성 파이프라인은 import 금지)
# ──────────────────────────────────────────────────────────────────
