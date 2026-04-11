#!/usr/bin/env python3
"""규범 마커 → pattern_code 정적 매핑 사전 생성기 (1회 실행).

pattern_ethics_relations + ethics_codes(+ patterns) 를 조회하여
리포트 본문의 〔규범 마커〕 를 패턴 코드로 되돌리는 사전을 만든다.

v25 아키텍처 (report_generator.py _SONNET_SYSTEM_PROMPT L221-235):
    Sonnet 4.6은 "JEC-7, PCP-3-1 같은 내부 코드를 절대 사용하지 말고 한국어
    조항 표현으로 변환"하도록 지시받는다. 실제 리포트에는
    〔신문윤리실천요강 제3조 1항〕, 〔언론윤리헌장 제4조〕 같은 마커가 나온다.

    DB의 ethics_codes.article_number 필드는 원문자(①②③...)를 쓴다:
        - source="신문윤리실천요강", article_number="제3조 ①"
    Sonnet은 이를 "1항" 형태로 변환한다:
        - 리포트 마커: "신문윤리실천요강 제3조 1항"

매핑 사전은 하나의 ethics row 당 여러 키 변형을 동시에 등록하여 robustness 확보:
    1. 원본:        "신문윤리실천요강 제3조 ①"
    2. 항 변환형:    "신문윤리실천요강 제3조 1항"
    3. 조만:        "신문윤리실천요강 제3조"
    (같은 조에 여러 항이 있으면 union — Sonnet이 조 레벨로 축약했을 때 대응)

출력:
    backend/scripts/ethics_to_pattern_map.json

실행:
    .venv/bin/python backend/scripts/generate_ethics_to_pattern_map.py
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx

# backend/core/db.py의 _get_supabase_config 재사용
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.db import _get_supabase_config  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("generate_ethics_map")

OUTPUT_PATH = Path(__file__).resolve().parent / "ethics_to_pattern_map.json"


def fetch_all_relations(sb_url: str, sb_key: str) -> list[dict]:
    """pattern_ethics_relations 전체 + patterns + ethics_codes JOIN.

    report_generator.fetch_ethics_for_patterns의 REST fallback 쿼리와
    유사한 구조. source + article_number를 추가로 select한다.
    pattern_id 필터 없이 전체를 가져온다.
    """
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
    }
    url = (
        f"{sb_url}/rest/v1/pattern_ethics_relations"
        "?select="
        "patterns!inner(code),"
        "ethics_codes!inner(code,title,source,article_number,is_active,is_citable)"
        "&ethics_codes.is_active=eq.true"
        "&ethics_codes.is_citable=eq.true"
        "&limit=5000"
    )
    r = httpx.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


# 원문자 → "N항" 변환 테이블
# Sonnet이 리포트에 쓸 때 "제3조 ①" → "제3조 1항" 형태로 변환하는 것을 역산.
_CIRCLED_TO_HANG = {
    "①": "1항", "②": "2항", "③": "3항", "④": "4항", "⑤": "5항",
    "⑥": "6항", "⑦": "7항", "⑧": "8항", "⑨": "9항", "⑩": "10항",
    "⑪": "11항", "⑫": "12항", "⑬": "13항", "⑭": "14항", "⑮": "15항",
    "⑯": "16항", "⑰": "17항", "⑱": "18항", "⑲": "19항", "⑳": "20항",
}
_CIRCLED_RE = re.compile("|".join(re.escape(c) for c in _CIRCLED_TO_HANG))


def _marker_variants(source: str, article: str, title: str = "") -> list[str]:
    """하나의 ethics_codes 행에서 가능한 마커 키 변형 목록을 생성.

    변형:
        1. 원본 그대로                        ("신문윤리실천요강 제3조 ①")
        2. 원문자 → N항 변환                  ("신문윤리실천요강 제3조 1항")
        3. 조만 남긴 축약형 (항/원문자 제거)   ("신문윤리실천요강 제3조")
        4. source + title 조합                ("신문윤리실천요강 공정보도")
        5. title 단독                         ("공정보도")
        (4, 5는 Sonnet이 조항 번호 대신 title로 인용하는 경우 대응)
    """
    variants: list[str] = []
    original = f"{source} {article}".strip()
    variants.append(original)

    converted = _CIRCLED_RE.sub(
        lambda m: _CIRCLED_TO_HANG[m.group(0)], article
    )
    if converted != article:
        variants.append(f"{source} {converted}".strip())

    # 조만 남기기: "제3조 ①" → "제3조", "제3조 1항" → "제3조"
    article_only = re.sub(
        r"\s*(?:[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|\d+\s*항).*$",
        "",
        article,
    ).strip()
    if article_only and article_only != article:
        variants.append(f"{source} {article_only}".strip())

    # title 기반 변형 — Sonnet이 "제3조 ①" 대신 "보도기사의 사실과 의견 구분"
    # 또는 "신문윤리실천요강 보도기사의 사실과 의견 구분"으로 인용할 때 대응
    if title:
        variants.append(f"{source} {title}".strip())
        variants.append(title)

    # 중복 제거, 순서 유지
    seen: set[str] = set()
    unique: list[str] = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def build_map(relations: list[dict]) -> dict[str, list[str]]:
    """marker_variant → sorted unique pattern_code list.

    각 ethics_codes 행에 대해 여러 마커 키 변형을 모두 등록한다.
    같은 조 내 여러 항이 있으면 "조만" 축약형 키와 title 기반 키에서
    union되어, Sonnet이 어느 형태로 인용하든 동일 패턴 코드 세트가 반환된다.
    """
    raw: defaultdict[str, set[str]] = defaultdict(set)
    for row in relations:
        p = row.get("patterns") or {}
        ec = row.get("ethics_codes") or {}
        pattern_code = str(p.get("code") or "").strip()
        source = str(ec.get("source") or "").strip()
        article = str(ec.get("article_number") or "").strip()
        title = str(ec.get("title") or "").strip()
        if not pattern_code or not source or not article:
            continue
        for key in _marker_variants(source, article, title):
            raw[key].add(pattern_code)
    return {k: sorted(v) for k, v in sorted(raw.items())}


def main() -> None:
    sb_url, sb_key = _get_supabase_config()
    logger.info(f"Supabase URL: {sb_url}")
    if not sb_key:
        raise RuntimeError(
            "Supabase service role key가 설정되지 않았습니다. "
            ".env 또는 환경변수 확인 필요."
        )

    relations = fetch_all_relations(sb_url, sb_key)
    logger.info(f"fetch 완료: {len(relations)}건")

    ethics_map = build_map(relations)
    logger.info(
        f"매핑 완성: {len(ethics_map)}개 ethics_title "
        f"(패턴 코드 total {sum(len(v) for v in ethics_map.values())})"
    )

    OUTPUT_PATH.write_text(
        json.dumps(ethics_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"저장: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
