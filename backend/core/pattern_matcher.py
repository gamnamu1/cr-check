# backend/core/pattern_matcher.py
"""
CR-Check — 벡터 검색 + Sonnet Solo 패턴 식별 모듈

파이프라인 전반부 (M5 Sonnet Solo 아키텍처):
1. 청크별 임베딩 생성 (OpenAI text-embedding-3-small)
2. 벡터 검색 — search_pattern_candidates() RPC
3. Sonnet Solo 호출 — 전체 패턴 목록 + 벡터 후보 ★ 강조 + Devil's Advocate CoT
4. 밸리데이션 — 코드→ID 변환 + 비허용 코드(환각·부모·비활성·메타) 제거
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
SONNET_MODEL = "claude-sonnet-4-6"
VECTOR_THRESHOLD = float(os.environ.get("VECTOR_THRESHOLD", "0.2"))
VECTOR_MATCH_COUNT = 7

# T2 — "사회적 약자·소수자 보도 필수 검토" 지시 블록이 이름으로 지목한 코드.
# mandatory_review_codes는 이 집합과 validated_pattern_codes의 교집합으로
# 파생 계산한다 (Phase 1 JSON 스키마에 새 top-level 키 추가 금지 원칙).
_MANDATORY_REVIEW_TARGET_CODES = {"4-3-b", "3-4-a", "3-4-b", "6-2-d"}


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
    # 거부 코드 목록. 활성 Sonnet Solo 경로에서는 DB 미존재 코드뿐 아니라
    # 부모·비활성·메타 등 런타임 비허용 코드도 포함한다
    # (validate_runtime_pattern_codes 참조). legacy 경로는 기존 "DB 존재 여부"
    # 검증 의미를 유지한다 (validate_pattern_codes). 필드명은 하위 호환용 유지.
    hallucinated_codes: list[str] = field(default_factory=list)
    haiku_raw_response: str = ""
    embedding_tokens: int = 0
    # STEP 5-A 블록3: 카탈로그(active v3 leaf) 외 코드 (구버전·부모·inactive)
    # STEP 6 임베딩 재생성 전까지 추적용
    unmatched_vector_candidates: list[str] = field(default_factory=list)
    suspect_result: object = None  # SuspectResult (2-Call 모드에서만 사용)
    # Phase 1 카탈로그 메타 맵 (code → {name, report_framing}). DB 왕복 0회로
    # _load_pattern_catalog 캐시 결과에서 구성. Phase 2 페이로드 전달용.
    pattern_catalog_meta: dict = field(default_factory=dict)
    # T0 포렌식 — Solo 응답 파싱이 1차 json.loads 외 복구 경로를 탄 경우 True
    parse_fallback_used: bool = False
    # T0 포렌식 — 프롬프트 카탈로그에서 실제로 ★ 마크된 코드 (런타임 원본 기록)
    starred_codes: list[str] = field(default_factory=list)
    # T2 — A-3 지시가 이름으로 지목한 4개 코드 중 이번 분석에서 실제로
    # validated_pattern_codes에 포함된 것 (모델에 새 필드를 묻지 않고 파생 계산)
    mandatory_review_codes: list[str] = field(default_factory=list)


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
_confusion_pairs_cache: list[dict] | None = None


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


def _resolve_report_framing(row: dict) -> str:
    """report_framing 반환. NULL/빈 값이면 parent 유무에 따라 자동 생성.

    NULL fallback의 단일 출처. 카탈로그 프롬프트(_build_pattern_catalog_entry)와
    Phase 2 전달용 pattern_catalog_meta 맵이 이 동일 규칙을 공유한다
    (규칙 신규 발명 금지 — 기존 L225-233 로직을 그대로 반영).
    """
    report_framing = (row.get("report_framing") or "").strip()
    if report_framing:
        return report_framing
    code = row["code"]
    name = row["name"]
    parent_name = row.get("parent_name")
    if parent_name:
        return (
            f"구체 패턴({code}) '{name}'의 판단 기준을 중심으로 설명하되, "
            f"필요 시 {parent_name} 맥락으로 확장"
        )
    return f"구체 패턴({code}) 지적 → 상위 보도윤리 맥락으로 확장"


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

    # report_framing NULL fallback은 _resolve_report_framing 단일 출처에서 처리
    lines.append(f"리포트 서술 방향: {_resolve_report_framing(row)}")

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


def _load_confusion_pairs(sb_url: str, sb_key: str) -> list[dict]:
    """DB에서 활성 패턴 혼동 쌍 로드. 성공한 결과만 캐시.

    is_active=TRUE인 행만, id 오름차순으로 조회하여 벤치마크 재현성을 확보한다.
    각 dict 형식: {code_a, code_b, distinction_guide}.
    조회 실패 시 캐시하지 않고 빈 리스트만 반환 + logger.warning
    (다음 호출에서 재시도 가능. 파이프라인은 혼동 쌍 없이 계속 진행).
    """
    global _confusion_pairs_cache
    if _confusion_pairs_cache is not None:
        return _confusion_pairs_cache

    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    try:
        r = httpx.get(
            f"{sb_url}/rest/v1/pattern_confusion_pairs"
            "?select=code_a,code_b,distinction_guide"
            "&is_active=eq.true"
            "&order=id",
            headers=headers,
        )
        r.raise_for_status()
        rows: list[dict] = r.json()
        _confusion_pairs_cache = rows
        return _confusion_pairs_cache
    except Exception as e:
        logger.warning(
            f"_load_confusion_pairs: 조회 실패 [{type(e).__name__}] — {e}. 빈 리스트로 진행."
        )
        return []


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

_SONNET_SOLO_PROMPT = """\
당신은 한국 뉴스 기사의 보도 품질을 평가하는 전문 분석가입니다.

당신의 분석은 세 가지 목적에 봉사합니다.
① 기사에서 문제적 보도관행 패턴을 정확하게 찾아낸다.
② 발견을 가장 정확한 패턴 코드로 명명한다 — 코드가 곧 윤리규범 인용의 경로다.
③ 시민이 읽을 비평 리포트의 재료를 만든다 — matched_text는 인용될 원문, reasoning은 비평의 뼈대, severity는 문제의 무게와 확신의 표현이다.

기사를 한 명의 비판적이고 성실한 독자로서 처음부터 끝까지 읽으세요. 아래 '패턴 목록'은 발견을 분류하는 도구이지, 시야를 제한하는 체크리스트가 아닙니다. 표면적으로 충실해 보이는 기사라도 제목·통계·인용·프레이밍 구조에 독자가 확인해볼 질문이 있는지 살피세요.

## 1단계: 비판적 정독 — 네 축
1. **통계·수치·연구 인용**: 수치의 조건·한정이 정확히 전달되는가? 특정 집단·조건에 한정된 수치를 일반적 사실처럼 확대하거나, 오차범위 내 차이를 서열화하거나, 예비적 결과를 확정처럼 다루지 않는가? 제목만이 아니라 본문의 통계 서술도 같은 기준으로 봅니다. 원자료를 직접 볼 수 없으므로, 기사 내부에서 확인 가능한 것(조건·한정어의 유무, 제목-본문 대조, 비교 기준)으로 판단합니다. (1-5-g, 1-5-h, 1-5-i, 1-1-j)
2. **제목-본문 정합**: 제목이 본문의 핵심 조건·주어·맥락을 삭제·과장하지 않는가? 주체나 결말을 숨겨 궁금증만 유발하는 제목('…왜?', '알고 보니', '결국')이 아닌가? (6-2-a, 6-2-b, 6-2-c, 6-2-d)
3. **사회적 약자·소수자·집단행동** [신중 판정 — 아래 별도 기준]. (4-3-b, 3-4-a, 3-4-b)
4. **사실-의견, 추측-단정**: 추측·전망이 귀속 없이 단정되지 않는가? 판단·평가의 주체가 감춰지지 않는가? (1-4-a, 1-4-b, 1-4-d, 6-1-d, 2-2-c)

## 2단계: 명명
발견을 가장 정확한 leaf 코드 하나로 연결하세요. 인접 코드가 여럿이면 정의를 대조하세요 — 코드가 어긋나면 리포트가 인용할 윤리규범도 어긋납니다.

## 판정 원칙
- **패턴 정의의 핵심 요건이 기사 안의 구체적 문장으로 확인되면, 확신이 완전하지 않아도 선택하세요.** 확신의 수준은 severity와 reasoning의 어조로 정직하게 드러냅니다.
  - high: 근거가 분명 — 단정형으로 서술
  - medium: 상당한 개연성 — 절제된 판단과 근거 병기
  - low: 독자가 확인해볼 질문 — 유보형으로 서술("~로 읽힐 수 있다", "~인지 확인이 필요하다")
- 문제가 있는데도 침묵하는 분석은 시민에게 질문할 기회를 주지 못합니다. 그러나 근거 없는 지적은 질문이 아니라 소음입니다. 질문에도 주소가 필요합니다 — 기사 안의 구체적 문장, 제목 표현, 누락된 조건이 그 주소입니다.
- 공익 목적에 부합하는 표현(탐사보도의 강렬한 묘사, 인권 고발의 피해 서술)은 그 자체로 위반이 아닙니다.

## 패턴군별 기준
**적극 탐지** — 제목-본문(6-2), 통계·인용(1-5, 1-1-j), 추측·단정(1-4), 출처 귀속(6-1-d, 2-2-c): 시민이 지적의 타당성을 스스로 판단할 수 있는 영역입니다. 근거 문장이 있으면 low/medium의 유보적 어조로도 적극적으로 질문을 제기하세요.

**신중 판정** — 차별·혐오·프레이밍(4-3-b, 3-4-a, 3-4-b): 이 판정은 기사에 낙인을 남기므로 무겁게 다룹니다. 주제나 인용어의 등장만으로 판정하지 마세요. 차별적 표현을 고발·비판·기록하기 위해 거리를 두고 인용한 기사는 해당하지 않습니다. 기사 스스로 그 프레임을 채택해 제목·리드·본문 구조로 사안을 조직하고 증폭할 때만 해당합니다. 판단이 서지 않으면 선택하지 않습니다.

## ★ 표시
★는 벡터 검색의 참고 신호일 뿐입니다. ★ 유무와 무관하게 1단계 정독의 발견을 기준으로 판단하세요.

{confusion_pairs_section}

## 탐지 개수 원칙
- 탐지 개수에 임의의 상한을 두지 마세요. 기사 안에서 독립적인 근거가 확인되는 패턴은 모두 기록하세요.
- 정의상 중복되는 대체 후보 패턴은 가장 정확한 leaf 하나로 정리하되, 서로 다른 문제를 설명하는 패턴은 각각 기록하세요.
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

### 예시 3-1 — [TP] 4-3-b: 차별·혐오 표현 (프레이밍형 — 명시적 비하어 없음)
기사 제목: "○○단체 또 도심 점거…'볼모' 잡힌 출근길"
기사 요약: 한 정치인이 장애인단체의 이동권 시위를 "시민을 볼모로 잡는 독선"이라
비판한 발언을 제목과 리드에 그대로 배치하고, 시민 불편 사례를 나열함.
올바른 분석:
```json
{{
  "overall_assessment": "이동권 시위라는 공적 쟁점을 다루면서, '볼모'·'독선' 등의 표현과 '시민 대 장애인' 대립 구도를 거리두기 없이 증폭하여 장애인의 권리 요구를 공공질서 파괴로만 프레이밍하는 문제가 확인된다.",
  "detections": [
    {{
      "matched_text": "'볼모' 잡힌 출근길",
      "reasoning": "명시적 비하어는 없으나, 권리 요구 집단을 시민 피해의 가해자로 위치시키는 프레이밍이다. 문제는 개별 단어가 아니라 제목·인용 배치가 만드는 구도로, 4-3-b의 프레이밍형 사례에 해당한다.",
      "severity": "high",
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


def _build_sonnet_solo_prompt(sb_url: str, sb_key: str) -> str:
    """혼동 쌍 섹션을 포함한 system 프롬프트를 동적으로 빌드.

    - DB에서 활성 혼동 쌍을 가져와 ## 자주 혼동되는 패턴 쌍 섹션 문자열을 만든다.
    - 데이터가 없으면 섹션 자리를 비우고 앞뒤 빈 줄을 정리해 자연스럽게 보이게 한다.
    - .replace()를 사용한다 (.format()은 _SONNET_SOLO_PROMPT 내부의 {{ }} JSON 예시와
      충돌하므로 절대 사용 금지).
    """
    pairs = _load_confusion_pairs(sb_url, sb_key)
    if pairs:
        blocks = [
            f"{p['code_a']} vs {p['code_b']}: {p['distinction_guide'].strip()}"
            for p in pairs
        ]
        section_text = "## 자주 혼동되는 패턴 쌍\n\n" + "\n\n".join(blocks)
    else:
        section_text = ""

    result = _SONNET_SOLO_PROMPT.replace("{confusion_pairs_section}", section_text)
    if not section_text:
        # placeholder 자리에 빈 문자열이 들어가 발생한 \n{3,}을 \n\n로 정리.
        result = re.sub(r'\n{3,}', '\n\n', result)
    return result


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


def _parse_solo_response(text: str) -> tuple[str, list[HaikuDetection], bool]:
    """Sonnet Solo 응답 파싱. 3단계 fallback으로 JSON 복구 시도.

    Returns:
        (overall_assessment, detections, fallback_used)
        fallback_used: 1차 json.loads 성공 시 False, 그 외 모든 경로 True (T0 포렌식)
    """
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # JSON 객체 추출
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        logger.warning("Solo response: JSON object not found")
        return "", [], True

    json_str = text[start : end + 1]

    # 1차 시도: 기존 json.loads()
    try:
        data = json.loads(json_str)
        logger.info("Solo JSON 1차 파싱 성공")
        assessment, detections = _extract_solo_detections(data)
        return assessment, detections, False
    except json.JSONDecodeError as e:
        logger.warning(f"Solo JSON 1차 실패, 2차 복구 시도: {e}")

    # 2차 시도: LLM JSON 오류 수정 후 재시도
    try:
        fixed = _fix_llm_json(json_str)
        data = json.loads(fixed)
        logger.info("Solo JSON 2차 복구 성공")
        assessment, detections = _extract_solo_detections(data)
        return assessment, detections, True
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
        return assessment, detections, True

    logger.warning("Solo JSON 모든 파싱 시도 실패, 빈 결과 반환")
    return "", [], True


def match_patterns_solo(
    chunks: list[str],
    article_text: str,
    threshold: Optional[float] = None,
    title: Optional[str] = None,
) -> PatternMatchResult:
    """Sonnet Solo 1-Call: 게이트 없음 + Devil's Advocate CoT."""
    sb_url, sb_key = _get_supabase_config()
    t = threshold if threshold is not None else VECTOR_THRESHOLD

    # 1. 패턴 카탈로그 + 벡터 검색
    catalog = _load_pattern_catalog(sb_url, sb_key)
    catalog_text = _build_pattern_list_text(catalog)

    # 카탈로그 캐시 결과에서 Phase 2 전달용 메타 맵 구성 (신규 DB 쿼리 0건)
    pattern_catalog_meta = {
        row["code"]: {
            "name": row["name"],
            "report_framing": _resolve_report_framing(row),
        }
        for row in catalog
    }

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
    starred_codes: list[str] = []  # T0 포렌식 — 실제 ★ 마크된 코드 원본 기록
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
                starred_codes.append(code)
                marked_lines.append(f"★ {line}")
                continue
        marked_lines.append(line)
    marked_catalog = "\n".join(marked_lines)

    # 3. Sonnet 호출
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    title_block = f"## 기사 제목\n{title}\n\n" if title else ""
    user_message = f"""## 패턴 목록
{marked_catalog}

{title_block}## 기사 전문
{article_text}"""

    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2048,
        system=_build_sonnet_solo_prompt(sb_url, sb_key),
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
    )

    raw = response.content[0].text
    assessment, detections, parse_fallback_used = _parse_solo_response(raw)

    # 4. 밸리데이션 — 이미 로드한 활성 v3 leaf 카탈로그만으로 strict 검증 (DB 조회 0회)
    valid_ids, valid_codes, hallucinated = validate_runtime_pattern_codes(
        detections, catalog
    )

    # T2: 필수 검토 지시 대상 코드 중 실제 확정된 것 (파생 계산)
    mandatory_review_codes = sorted(
        _MANDATORY_REVIEW_TARGET_CODES & set(valid_codes)
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
        pattern_catalog_meta=pattern_catalog_meta,
        parse_fallback_used=parse_fallback_used,
        starred_codes=sorted(starred_codes),
        mandatory_review_codes=mandatory_review_codes,
    )


# ── 밸리데이션: 코드→ID 변환 + 비허용 코드 제거 (active/legacy 분리) ──
#
# 활성 경로  : validate_runtime_pattern_codes — 전달된 활성 v3 leaf 카탈로그만으로
#              strict 검증 (DB 조회 0회). 부모·비활성·메타·미존재 코드 거부.
# legacy 경로: validate_pattern_codes — DB 존재 여부만 확인 (기존 계약 보존).
#              숫자형 구코드를 쓰는 pattern_matcher_legacy.py·기존 스크립트가 사용.

_REJECT_REASON_NON_LEAF = "non_leaf_or_malformed"
_REJECT_REASON_NOT_IN_CATALOG = "not_in_runtime_catalog"


def validate_runtime_pattern_codes(
    detections: list[HaikuDetection],
    catalog: list[dict],
) -> tuple[list[int], list[str], list[str]]:
    """활성 파이프라인 전용 strict 검증 — 전달된 catalog만 사용, DB 조회 없음.

    match_patterns_solo()가 이미 로드한 런타임 활성 v3 leaf 카탈로그를 받아
    검증한다. 숫자형 구코드를 쓰는 legacy 경로는 이 함수를 타지 않는다
    (validate_pattern_codes 참조).

    통과 조건 (모두 충족):
      - 코드가 catalog 안에서 아래 3조건을 모두 만족하는 row의 code와 일치
        · is_active is True
        · is_meta_pattern is False
        · code가 v3 leaf 형식 (_LEAF_CODE_RE: ^[0-9]+-[0-9]+-[a-z]+$)
        (catalog row 자체를 재검증 — 비활성·메타·비-leaf row가 카탈로그에
         오염 유입돼도 허용 맵에서 배제된다)
    따라서 부모 코드, 비활성 leaf, 메타 패턴, 미존재 코드는 모두 거부된다.

    Returns:
        (valid_ids, valid_codes, rejected_codes)
        — 중복 코드는 기존 계약대로 입력 순서·횟수 그대로 반영된다.

    ※ rejected_codes는 PatternMatchResult.hallucinated_codes 필드로 흘러간다.
      의미 확장 (2026-07-13): 기존 "DB 미존재 환각 코드"에서 "부모·비활성·메타
      등 런타임 비허용 코드 전체"로 확대. 필드명·위치는 하위 호환 유지.
      거부 사유는 로컬 판별 가능한 2종만 로그로 구분:
        non_leaf_or_malformed  — v3 leaf 형식 불일치 (부모 코드 등)
        not_in_runtime_catalog — leaf 형식이나 활성 카탈로그에 없음
      (미존재/비활성/메타 세부 분류는 후속 forensic 과제로 이관)
    """
    if not detections:
        return [], [], []

    allowed: dict[str, int] = {}
    for row in catalog:
        code = row.get("code") or ""
        if (
            row.get("is_active") is True
            and row.get("is_meta_pattern") is False
            and _LEAF_CODE_RE.match(code)
        ):
            allowed[code] = row["id"]

    valid_ids: list[int] = []
    valid_codes: list[str] = []
    rejected: list[str] = []

    for det in detections:
        code = det.pattern_code
        if code in allowed:
            valid_ids.append(allowed[code])
            valid_codes.append(code)
        else:
            rejected.append(code)
            reason = (
                _REJECT_REASON_NOT_IN_CATALOG
                if _LEAF_CODE_RE.match(code)
                else _REJECT_REASON_NON_LEAF
            )
            logger.warning(
                f"Rejected pattern code removed: {code} (reason={reason})"
            )

    return valid_ids, valid_codes, rejected


def validate_pattern_codes(
    detections: list[HaikuDetection],
    sb_url: str,
    sb_key: str,
) -> tuple[list[int], list[str], list[str]]:
    """패턴 코드를 DB 존재 여부로 검증하고 ID로 변환 (legacy 전용).

    ※ 역할 분리 (2026-07-13): 활성 파이프라인(match_patterns_solo)은 이 함수가
      아니라 validate_runtime_pattern_codes(strict)를 사용한다. 이 함수는
      숫자형 3세그먼트 구코드(예: 1-1-1, 1-7-2)를 쓰는
      pattern_matcher_legacy.py와 기존 스크립트의 "DB에 존재하면 통과" 계약을
      그대로 보존한다 — v3 leaf 기준으로 강화하지 말 것 (legacy 코드 체계가
      전부 거부된다). 현행 DB와 legacy 구코드 체계는 이미 일치하지 않을 수
      있다. 이 분리의 목적은 현 DB에서 legacy를 즉시 복구하는 것이 아니라,
      함수 의미를 보존해 구 DB 스냅샷 기반 재현 가능성을 방해하지 않는 것이다.

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
