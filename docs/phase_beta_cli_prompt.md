# 작업 지시: Phase β — 인용 구조 전환 + 규범 조회 안정화 + 프롬프트 정비

## 배경

Phase α에서 JSON 파싱 버그는 해결되었으나, 두 가지 근본 문제가 남아 있다:
1. `get_ethics_for_patterns` RPC가 간헐적으로 0건을 반환하여 리포트 생성이 실패한다.
2. `<cite>` 태그 후치환 방식은 규범을 문장에 자연스럽게 녹이지 못해 리포트 품질을 떨어뜨린다.

이 작업에서 네 가지를 동시에 수행한다:
- 수정 1: 규범 조회에 REST API fallback 추가 (Bug C 근본 대응)
- 수정 2: 리포트 생성 프롬프트를 전면 교체 (cite 태그 폐기, 자연 인용)
- 수정 3: pipeline.py에서 citation_resolver 루프 비활성화
- 수정 4: 프롬프트 표현력 정비

---

## 수정 1: 규범 조회 REST API fallback 추가

### 대상 파일
`backend/core/report_generator.py` — `fetch_ethics_for_patterns()` 함수

### 증상
동일한 패턴(1-3-1)이 테스트 1에서는 규범 31건이 조회되지만, 테스트 2·3에서는 0건이 반환된다. RPC 재시도로도 해결되지 않는다.

### 수정 내용

현재 `fetch_ethics_for_patterns()` 함수의 "재시도까지 0건이면 fallback 진단 쿼리" 블록을 수정한다. 기존의 "진단만 하고 빈 리스트 반환"을 **"REST API로 직접 데이터를 가져와서 반환"**으로 변경한다.

기존 fallback 진단 쿼리 블록(`# 재시도까지 0건이면 fallback 진단 쿼리` 주석부터 `return _parse_ethics_rows(rows)` 직전까지)을 아래 로직으로 교체한다:

```python
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
```

### 주의사항
- Supabase REST API의 foreign key 조인 문법(`테이블!inner(컬럼)`)을 사용한다. 정확한 테이블명과 컬럼명은 스키마 마이그레이션 파일(`supabase/migrations/20260328000000_create_cr_check_schema.sql`)에서 확인할 수 있다.
- 만약 Supabase REST API의 foreign key 조인이 동작하지 않으면, 두 번의 개별 쿼리(relations 조회 → ethics_codes 조회)로 분리하여 구현한다.
- `_parse_ethics_rows(rows)`는 기존과 동일하게 사용한다.

---

## 수정 2: 리포트 생성 프롬프트 전면 교체

### 대상 파일
`backend/core/report_generator.py` — `_SONNET_SYSTEM_PROMPT` 문자열 전체

### 수정 내용

기존 `_SONNET_SYSTEM_PROMPT` 전체를 아래 내용으로 교체한다. 핵심 변경점:
- `<cite ref="..."/>` 태그 사용 지시 → 완전 삭제
- 규범을 "알고 있는 상태에서 자연스럽게 녹여 쓰기" 지시로 변경
- 롤업 원칙 재정의
- 3종 톤 재설계
- "문제" 반복 금지, 중간제목 남발 제한 등 표현 가이드 추가

```python
_SONNET_SYSTEM_PROMPT = """\
당신은 한국 신문윤리위원회 수준의 저널리즘 비평 전문가입니다.
주어진 기사를 분석하여 3가지 독자 유형에 맞는 평가 리포트와 기사 메타분석을 작성합니다.

## 핵심 원칙

### 1. CR-Check 포지셔닝
CR-Check는 저널리즘 비평의 **관점을 제시하는 도구**입니다.
점수, 등급, 순위를 부여하지 않습니다. 서술형으로만 분석합니다.

### 2. 윤리규범 인용 방식 (절대 규칙)
아래 "관련 윤리규범" 섹션에 제공된 규범 원문을 읽고, 리포트에 자연스럽게 녹여 쓰세요.

**올바른 인용 예시:**
- "언론윤리헌장 제4조는 '사회적으로 중요한 사안이나 갈등적 사안을 다룰 때는 다양한 입장을 두루 담아 균형 잡힌 시각과 관점을 보여준다'고 명시합니다."
- "신문윤리실천요강 제3조 2항은 '경합 중인 사안을 보도할 때 한 쪽의 주장을 편파적으로 보도하지 않는다'고 규정합니다."

**규칙:**
- 조항 번호(예: 제4조, 제3조 2항)를 반드시 명시하세요. 조항 번호는 제공된 ethics_code 또는 article_number를 참고하세요.
- 규범의 핵심 문구를 발췌하여 작은따옴표(' ')로 감싸 인용하세요. 전문을 통째로 넣지 마세요.
- 제공된 규범 외의 내용을 지어내지 마세요. 제공된 원문에서만 인용하세요.
- <cite> 태그를 사용하지 마세요. 모든 인용은 직접 텍스트로 작성합니다.

### 3. 규범 인용의 깊이
- 각 지적 사항에 대해 가장 직접 관련된 구체적 조항(Tier 3~4)을 인용하세요.
- 리포트 전체에서 **1~2회 정도**는 구체적 조항에서 상위 원칙(Tier 1~2)으로 의미를 확장하는 서술을 넣으세요.
  예: "이는 단순히 공정보도 조항(제3조 2항)의 위반을 넘어, 언론윤리헌장이 천명하는 '다양한 입장을 두루 담아 균형 잡힌 시각을 보여준다'는 근본 원칙에 어긋납니다."
- 매 지적마다 하위→상위를 반복하지는 마세요. 종합 평가에서 한두 번 자연스럽게 사용하세요.

### 4. 3종 리포트 톤 차이

- **comprehensive** (시민용): 이웃에게 말하듯 자연스럽고 따뜻한 어투. 왜 이것이 우려되는지를 일상적 비유로 설명. "이 기사를 읽으면서 이런 점을 생각해보시면 좋겠습니다" 같은 톤. 절대 가르치거나 교육하려는 톤이 아닌, 함께 살펴보는 시민의 관점.
- **journalist** (기자용): "시민 주도 CR 프로젝트를 통해 기자님의 기사를 평가했습니다"로 시작. 동료 전문가에게 건설적 피드백을 주듯 구체적 개선안 제시. 기자의 노력을 인정하되 정확한 비판.
- **student** (학생용): "여러분"이라는 호칭. 일상적 비유와 질문 형식으로 비판적 읽기를 유도. 이모지 적절히 활용. 단, 딱딱한 교과서 설명이 아닌, 함께 탐구하는 느낌.

### 5. 1차 분석 결과 활용
아래 "1차 분석 결과"의 overall_assessment를 참고하여 리포트의 관점과 종합 평가를 자연스럽게 결정하세요.
overall_assessment를 리포트에 그대로 인용하지 말고, 분석의 방향성만 참고하세요.

### 6. 서술 스타일 가이드
- 마크다운 중간제목(###)은 리포트당 최대 3~4개만 사용하세요. 과도한 구조화는 글의 자연스러움을 해칩니다.
- "문제", "문제점", "문제가 있습니다"라는 표현을 반복하지 마세요. 이미 평가를 요청한 독자에게 "문제가 있다"를 반복 강조할 필요가 없습니다. 대신 "이런 점이 눈에 띕니다", "이 부분을 살펴보겠습니다", "아쉬운 지점입니다" 등 다양한 표현을 쓰세요.
- 각 리포트의 첫 줄에 "# 시민을 위한 기사 분석 리포트" 같은 제목을 넣되, 본문 첫 문단에서 같은 제목을 반복하지 마세요.

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
```

### 주의사항
- `_SONNET_SYSTEM_PROMPT_LEGACY`(비교용 보존 프롬프트)는 수정하지 않는다.
- 프롬프트 내의 중괄호 `{}`가 Python f-string과 충돌하지 않도록 주의한다. 이 프롬프트는 f-string이 아닌 일반 문자열이다.


---

## 수정 3: pipeline.py에서 citation_resolver 루프 비활성화

### 대상 파일
`backend/core/pipeline.py` — `analyze_article()` 함수 내 인용 치환 루프

### 수정 내용

현재 코드에서 아래 블록을 찾는다:

```python
# 결정론적 인용 후처리: cite 태그 → 규범 원문 치환 (3종 각각)
for report_type in ["comprehensive", "journalist", "student"]:
```

이 `for` 루프 전체(for 문부터 해당 블록이 끝나는 곳까지)를 **주석 처리**한다. 삭제하지 않고 주석 처리하여 비교 실험이 필요할 때 복원할 수 있게 한다.

주석 처리 전에 아래 한 줄을 추가한다:

```python
# [Phase β] cite 태그 후치환 비활성화 — Sonnet이 규범을 직접 서술하므로 불필요
# 복원이 필요하면 아래 주석을 해제하세요.
```

`pre_citation_reports`와 `hallucinated_refs_log` 변수 초기화 코드(진단용으로 Phase α에서 추가한 부분)도 함께 주석 처리한다. 단, 진단 JSON 덤프 코드에서 이 변수들을 참조하므로, 덤프 코드의 CP5 섹션에서 `pre_citation_reports`를 `rr.reports`와 동일하게 설정하도록 수정한다:

```python
# CP5: 리포트 (cite 태그 후치환 비활성화 상태에서는 pre/post가 동일)
_cp5 = {
    "pre_citation_reports": {rt: rr.reports.get(rt, "") for rt in ["comprehensive", "journalist", "student"]},
    "post_citation_reports": {rt: rr.reports.get(rt, "") for rt in ["comprehensive", "journalist", "student"]},
    "hallucinated_refs_per_report": {},
    "sonnet_raw_response": rr.sonnet_raw_response,
}
```

---

## 수정 4: _build_ethics_context 형식 개선

### 대상 파일
`backend/core/report_generator.py` — `_build_ethics_context()` 함수

### 수정 내용

현재 형식:
```
[코드: JEC-4] [Tier 1] 공정하게 보도한다
원문: 윤리적 언론은 특정 집단...
```

Sonnet이 조항 번호를 쉽게 인용할 수 있도록 형식을 변경한다:

```python
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
```

---

## 수정하지 않는 것

- `citation_resolver.py` 파일 자체는 수정하지 않는다. 코드를 삭제하지 않고 그대로 보존한다. pipeline.py에서 호출만 비활성화한다.
- `pattern_matcher.py`의 Sonnet Solo 프롬프트(`_SONNET_SOLO_PROMPT`)는 수정하지 않는다.
- `_SONNET_SYSTEM_PROMPT_LEGACY`(비교용 보존 프롬프트)는 수정하지 않는다.
- 메타 패턴 관련 코드(`meta_pattern_inference.py`, `_build_meta_pattern_block`)는 이번 작업에서 수정하지 않는다.
- 진단용 JSON 덤프 코드는 CP5 부분만 위에서 명시한 대로 수정하고, 나머지는 유지한다.

---

## 수정 후 테스트

수정 완료 후 로컬 서버를 실행하고, 이전과 동일한 기사 3건으로 테스트한다:
1. 세계일보 이준석 기사: https://www.segye.com/newsView/20220325505972
2. 조선일보 이준석 기사: https://www.chosun.com/politics/politics_general/2022/03/27/GFDP2HEB2NDC5LSRIAI5DZ7KLU/
3. 연합뉴스 노동생산성 기사: https://www.yna.co.kr/view/AKR20250922018300003

터미널 로그에서 확인할 사항:
- 규범 조회: RPC가 0건일 때 REST API fallback이 동작하여 규범을 가져오는지
- 리포트 생성: 3종 리포트가 에러 없이 생성되는지
- cite 태그: 리포트에 `<cite` 문자열이 포함되어 있지 않은지

## 금지 사항
- 기존 함수의 시그니처(매개변수, 반환 타입)를 변경하지 않는다.
- `citation_resolver.py` 파일의 내용을 수정하거나 삭제하지 않는다.
- 프롬프트 외의 코드 로직 변경은 수정 1(fallback)과 수정 3(비활성화)에 명시된 범위만 수행한다.
