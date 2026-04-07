# M6 STEP 73 — main.py 교체 + report_generator.py 3종 리포트 확장 설계서

> 작성: Claude.ai (STEP 71 설계 → STEP 72 Gamnamu 승인 완료)
> 작성일: 2026-03-31
> 대상: Claude Code CLI (STEP 73 실행용)
> 상태: **Gamnamu 승인 완료 — 이 설계대로 구현하라**

---

## 0. 사전 숙지 파일 (Plan Mode에서 먼저 읽을 것)

```
1. docs/SESSION_CONTEXT_2026-03-30_v19.md  ← 프로젝트 전체 상태
2. docs/CR_CHECK_M6_PLAYBOOK.md            ← M6 플레이북 (STEP 73 참조)
3. 이 파일 (M6_STEP73_DESIGN.md)          ← 구현 설계서 ★
4. backend/main.py                         ← 교체 대상
5. backend/core/pipeline.py                ← 수정 대상
6. backend/core/report_generator.py        ← 대규모 수정 대상
7. backend/core/analyzer.py                ← 참조용 (3종 리포트 구조, Phase 2 프롬프트)
8. backend/core/pattern_matcher.py         ← 변경 없음 (overall_assessment 추출 위치 확인)
9. backend/core/citation_resolver.py       ← 변경 없음 (3종 적용 방식 확인)
10. frontend/types/index.ts                ← 최소 수정
11. CLAUDE.md                              ← "리포트 설계 원칙" 섹션 필독
12. docs/_reference/[샘플] 평가 리포트/    ← 리포트 품질 기준 참고
```

---

## 1. 핵심 설계 결정 요약 (4건, 모두 Gamnamu 승인 완료)

| # | 판단 포인트 | 결정 | 근거 |
|---|------------|------|------|
| 1 | 3종 리포트 생성 방식 | **Sonnet 1-Call, 3종 JSON 반환** | analyzer.py 검증된 패턴, 비용 효율, 톤만 다른 구조라 1-Call 충분 |
| 2 | article_analysis 생성 주체 | **리포트 생성 Sonnet에서 함께** | analyzer.py 계승, 맥락상 자연스러움 |
| 3 | overall_assessment 처리 | **Sonnet에게 컨텍스트로 전달, 녹이거나 제외는 Sonnet 판단** | 프론트엔드 무변경, 자연스러운 통합 |
| 4 | TN 케이스 (패턴 미탐지) | **정적 메시지 3종, Sonnet 호출 없음** | "관점 제시 도구"의 정직한 대답 |

---

## 2. 전체 파이프라인 흐름 (TO-BE)

```
기사 URL
  → scraper.scrape(url)                          [변경 없음]
  → article_text 추출
  → chunk_article(article_text)                   [변경 없음]
  → match_patterns_solo(chunks, article_text)     [변경 없음]
      → overall_assessment + detections 반환
  
  ── 분기 ──
  (A) validated_pattern_ids 있음 (TP 경로):
      → fetch_ethics_for_patterns(pattern_ids)    [변경 없음]
      → generate_report(                          [★ 대규모 변경]
            article_text,
            pattern_ids,
            detections,
            overall_assessment                    ← 신규 인자
        )
        → Sonnet 1-Call: 3종 리포트 + article_analysis JSON 반환
        → ReportResult { reports: {comprehensive, journalist, student}, article_analysis: {...} }
      → CitationResolver: 3종 각각에 적용          [★ 적용 방식 변경]
      → 최종 결과
  
  (B) validated_pattern_ids 없음 (TN 경로):
      → 정적 메시지 3종 반환, Sonnet 호출 없음
      → ReportResult { reports: {comprehensive, journalist, student} }
  
  → main.py: AnalysisResult → 프론트엔드 호환 응답 변환
  → { article_info: {...}, reports: {comprehensive, journalist, student} }
```

---

## 3. 파일별 상세 변경 사항


### 3-1. report_generator.py — 대규모 변경

#### 데이터 구조 변경

```python
# AS-IS (M4)
@dataclass
class ReportResult:
    report_text: str = ""
    ethics_refs: list[EthicsReference] = field(default_factory=list)
    sonnet_raw_response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

# TO-BE (M6)
@dataclass
class ReportResult:
    reports: dict[str, str] = field(default_factory=dict)
    # 반드시 { "comprehensive": "...", "journalist": "...", "student": "..." }
    article_analysis: dict = field(default_factory=dict)
    # { "articleType": "...", "articleElements": "...", "editStructure": "...",
    #   "reportingMethod": "...", "contentFlow": "..." }
    ethics_refs: list[EthicsReference] = field(default_factory=list)
    sonnet_raw_response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
```

#### 함수 시그니처 변경

```python
# AS-IS
def generate_report(
    article_text: str,
    pattern_ids: list[int],
    haiku_detections: list[dict],
) -> ReportResult

# TO-BE
def generate_report(
    article_text: str,
    pattern_ids: list[int],
    detections: list[dict],
    overall_assessment: str = "",
) -> ReportResult
```

- `haiku_detections` → `detections`로 이름 변경 (Haiku가 아닌 Sonnet Solo가 생성)
- `overall_assessment` 신규 인자: Devil's Advocate CoT 결과, Sonnet 리포트 생성의 컨텍스트로 전달

#### Sonnet 시스템 프롬프트 재설계

기존 `_SONNET_SYSTEM_PROMPT`를 아래로 전면 교체:

```python
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
```

#### Sonnet 유저 메시지 구성

```python
user_message = f"""## 1차 분석 결과 (Sonnet Solo 패턴 식별)

### 종합 판단
{overall_assessment}

### 탐지된 패턴
{detections_json}

## 관련 윤리규범 (확정 패턴에 연결된 규범, DB 조회 결과)
{ethics_context}

## 기사 전문
{article_text}"""
```

- `overall_assessment`: pattern_matcher.py의 Sonnet Solo가 생성한 Devil's Advocate CoT 결과
- `detections_json`: 확정된 패턴 목록 (pattern_code, matched_text, severity, reasoning)
- `ethics_context`: 기존 `_build_ethics_context()` 함수로 생성 (변경 없음)
- `article_text`: 기사 전문


#### Sonnet 호출 함수 변경

```python
# AS-IS
def call_sonnet(article_text, haiku_result_json, ethics_context) -> tuple[str, int, int]

# TO-BE
def call_sonnet(
    article_text: str,
    detections_json: str,
    overall_assessment: str,
    ethics_context: str,
) -> tuple[str, int, int]
```

- max_tokens: 4096 → **10000** (3종 리포트 + article_analysis, analyzer.py의 Phase 2와 동일)
- temperature: 0.0 유지

#### JSON 파싱 + 재시도 로직

analyzer.py의 `_run_phase2()` 방식을 계승:

```python
max_retries = 3

for attempt in range(max_retries):
    try:
        raw_text, in_tok, out_tok = call_sonnet(...)
        result_json = robust_json_parse(raw_text)  # 마크다운 코드블록 제거 + JSON 추출
        
        # 구조 검증
        if "reports" not in result_json:
            raise ValueError("'reports' 키 누락")
        reports = result_json["reports"]
        for field in ["comprehensive", "journalist", "student"]:
            if field not in reports:
                raise ValueError(f"필수 리포트 '{field}' 누락")
        
        article_analysis = result_json.get("article_analysis", {})
        
        return ReportResult(
            reports=reports,
            article_analysis=article_analysis,
            ethics_refs=ethics_refs,
            sonnet_raw_response=raw_text,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"리포트 생성 시도 {attempt+1}/{max_retries} 실패: {e}")
        if attempt == max_retries - 1:
            raise ValueError(f"리포트 생성 최종 실패: {e}")
        time.sleep(2 ** attempt)  # exponential backoff
```

`robust_json_parse` 함수는 analyzer.py에 이미 구현되어 있음. 동일 로직을 report_generator.py에 복사하거나, 공용 유틸로 분리.

#### generate_report() 메인 함수 전체 흐름

```python
def generate_report(
    article_text: str,
    pattern_ids: list[int],
    detections: list[dict],
    overall_assessment: str = "",
) -> ReportResult:
    sb_url, sb_key = _get_supabase_config()

    # 1. 규범 조회 (변경 없음)
    ethics_refs = fetch_ethics_for_patterns(pattern_ids, sb_url, sb_key)
    ethics_context = _build_ethics_context(ethics_refs)

    # 2. detections JSON 문자열
    detections_json = json.dumps(detections, ensure_ascii=False, indent=2)

    # 3. Sonnet 호출 (3종 JSON 반환) + 재시도 로직
    #    (위의 재시도 로직 적용)

    return report_result
```

#### 기존 코드 보존 원칙

- `fetch_ethics_for_patterns()`: 변경 없음
- `_build_ethics_context()`: 변경 없음
- `EthicsReference` 데이터클래스: 변경 없음
- 기존 `_SONNET_SYSTEM_PROMPT`: 삭제하지 말고 `_SONNET_SYSTEM_PROMPT_LEGACY`로 이름 변경하여 보존


---

### 3-2. pipeline.py — 중규모 변경

#### AnalysisResult 구조 조정

```python
@dataclass
class AnalysisResult:
    # 기존 유지
    chunks: list[Chunk] = field(default_factory=list)
    chunk_count: int = 0
    avg_chunk_length: float = 0.0
    pattern_result: PatternMatchResult = field(default_factory=PatternMatchResult)
    report_result: ReportResult = field(default_factory=ReportResult)
    total_seconds: float = 0.0
    embedding_tokens: int = 0
    sonnet_input_tokens: int = 0
    sonnet_output_tokens: int = 0
    # 추가
    overall_assessment: str = ""  # Sonnet Solo 판단 근거 (아카이빙용 보존)
```

#### analyze_article() 변경 사항

**변경 1 — overall_assessment 추출 및 전달:**

```python
pm = match_patterns_solo(chunk_texts, article_text, threshold=vector_threshold)
result.pattern_result = pm
result.embedding_tokens = pm.embedding_tokens

# overall_assessment 보존 (Phase D 아카이빙용)
result.overall_assessment = pm.suspect_result.overall_assessment if pm.suspect_result else ""
```

**변경 2 — generate_report() 호출 시그니처 변경:**

```python
# AS-IS
rr = generate_report(article_text, pm.validated_pattern_ids, haiku_dicts)

# TO-BE
rr = generate_report(
    article_text,
    pm.validated_pattern_ids,
    haiku_dicts,
    overall_assessment=result.overall_assessment,
)
```

**변경 3 — CitationResolver 3종 적용:**

```python
# AS-IS
try:
    if rr.report_text:
        resolved_text, hallucinated = resolve_citations(rr.report_text, rr.ethics_refs or [])
        rr.report_text = resolved_text
        ...

# TO-BE
try:
    for report_type in ["comprehensive", "journalist", "student"]:
        text = rr.reports.get(report_type, "")
        if text:
            resolved, hallucinated = resolve_citations(text, rr.ethics_refs or [])
            rr.reports[report_type] = resolved
            if hallucinated:
                logger.warning(f"[{report_type}] 환각 ref 제거: {hallucinated}")
except Exception as e:
    logger.error(f"CitationResolver 실패, cite 태그 제거 후 반환: {e}")
    for report_type in ["comprehensive", "journalist", "student"]:
        text = rr.reports.get(report_type, "")
        if text:
            text = re.sub(r'<cite\s+ref="[^"]*"\s*/>', '', text)
            text = re.sub(r'<cite\s+ref="[^"]*"\s*>\s*</cite>', '', text)
            text = re.sub(r' {2,}', ' ', text)
            rr.reports[report_type] = text
```

**변경 4 — TN 분기 (패턴 미탐지):**

```python
# AS-IS
elif run_sonnet and not pm.validated_pattern_ids:
    result.report_result = ReportResult(
        report_text="분석 결과 문제적 보도관행이 발견되지 않았습니다."
    )

# TO-BE
_TN_MESSAGE = "분석 결과 문제적 보도관행이 발견되지 않았습니다."

elif run_sonnet and not pm.validated_pattern_ids:
    result.report_result = ReportResult(
        reports={
            "comprehensive": _TN_MESSAGE,
            "journalist": _TN_MESSAGE,
            "student": _TN_MESSAGE,
        }
    )
```

#### 독스트링 갱신

파일 상단 독스트링을 현재 아키텍처에 맞게 갱신:

```python
"""
CR-Check — RAG 파이프라인 오케스트레이션

Sonnet Solo 1-Call 아키텍처:
기사 → 청킹 → 임베딩 → 벡터검색
  → Sonnet Solo(패턴 식별 + Devil's Advocate CoT)
  → 규범 조회(get_ethics_for_patterns RPC)
  → Sonnet(3종 리포트 + article_analysis, cite 태그)
  → CitationResolver(cite → 규범 원문 치환, 3종 각각 적용)
  → 최종 결과: { reports: {comprehensive, journalist, student}, article_analysis }
"""
```


---

### 3-3. main.py — 중규모 변경 (파이프라인 교체)

#### import 변경

```python
# AS-IS
from core.analyzer import ArticleAnalyzer
from export import generate_pdf_response

# TO-BE
from core.pipeline import analyze_article as run_pipeline, AnalysisResult
# analyzer.py import 제거 (파일 자체는 보존)
# export import 주석 처리 (Phase D에서 재설계)
```

#### 전역 인스턴스 변경

```python
# AS-IS
scraper = ArticleScraper()
analyzer = ArticleAnalyzer()

# TO-BE
scraper = ArticleScraper()
# analyzer 인스턴스 제거
```

#### 응답 모델 변경

```python
# AS-IS — 변경 없음, 그대로 유지
class AnalyzeResponse(BaseModel):
    article_info: Dict[str, str]
    reports: Dict[str, str]
```

AnalyzeResponse는 변경하지 않는다. 기존 구조 그대로.

#### /analyze 엔드포인트 재작성

```python
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_article(request: AnalyzeRequest):
    """
    기사 URL을 분석하여 3가지 평가 리포트 생성

    ## 프로세스 (M6 — Sonnet Solo 아키텍처)
    1. URL에서 기사 스크래핑 (제목 + 본문)
    2. 청킹 → 벡터검색 → Sonnet Solo (패턴 식별)
    3. 규범 조회 → Sonnet (3종 리포트, cite 태그)
    4. CitationResolver (규범 원문 결정론적 치환)
    """
    try:
        # 1. 기사 스크래핑
        print(f"📰 기사 스크래핑 시작: {request.url}")
        article_data = scraper.scrape(str(request.url))
        article_text = article_data.get("content", "")
        print(f"✅ 스크래핑 완료: {article_data['title'][:50]}...")

        if not article_text or len(article_text.strip()) < 50:
            raise ValueError("기사 본문을 추출할 수 없거나 너무 짧습니다.")

        # 2. 파이프라인 실행
        print(f"🔍 파이프라인 분석 시작...")
        result: AnalysisResult = run_pipeline(article_text)
        print(f"✅ 파이프라인 완료 ({result.total_seconds:.1f}초)")

        # 3. 응답 구성 — 프론트엔드 호환 형식
        article_info = {
            "title": article_data.get("title", ""),
            "url": str(request.url),
        }

        # scraper 메타데이터 병합
        if article_data.get("publisher") and article_data["publisher"] != "미확인":
            article_info["publisher"] = article_data["publisher"]
        if article_data.get("publish_date") and article_data["publish_date"] != "미확인":
            article_info["publishDate"] = article_data["publish_date"]
        if article_data.get("journalist") and article_data["journalist"] != "미확인":
            article_info["journalist"] = article_data["journalist"]

        # Sonnet이 생성한 article_analysis 병합
        if result.report_result.article_analysis:
            article_info.update(result.report_result.article_analysis)

        return AnalyzeResponse(
            article_info=article_info,
            reports=result.report_result.reports,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        from datetime import datetime
        error_msg = (
            f"[{datetime.now()}] Error processing {request.url}: "
            f"{str(e)}\n{traceback.format_exc()}\n{'='*50}\n"
        )
        try:
            with open("backend_error.log", "a", encoding="utf-8") as f:
                f.write(error_msg)
        except Exception as log_err:
            print(f"Failed to write log: {log_err}")
        print(f"❌ 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류가 발생했습니다: {str(e)}"
        )
```

#### /export-pdf 주석 처리

```python
# [M6] Phase D에서 재설계 예정 — 주석 처리
# @app.post("/export-pdf")
# async def export_to_pdf(analysis_result: AnalyzeResponse):
#     ...
```

import 문의 `from export import generate_pdf_response`도 함께 주석 처리.

#### 변경하지 않는 것

- `/` (root) 엔드포인트: 그대로 유지
- `/health` 엔드포인트: 그대로 유지
- CORS 설정: 그대로 유지
- `if __name__ == "__main__"` 블록: 그대로 유지


---

### 3-4. frontend/types/index.ts — 최소 변경

```typescript
// 기존 — 변경 없음
export interface ArticleMetadata {
  title: string;
  url: string;
  publisher?: string;
  journalist?: string;
  publishDate?: string;
  articleType?: string;
  originalUrl?: string;
  articleElements?: string;
  editStructure?: string;
  reportingMethod?: string;
  contentFlow?: string;
}

export interface AnalysisReport {
  comprehensive: string;
  journalist: string;
  student: string;
}

export interface AnalysisResult {
  article_info: ArticleMetadata;
  reports: AnalysisReport;
  // ▼ M6 추가 (optional, Phase D 아카이빙용)
  overall_assessment?: string;
  detections?: Array<{
    pattern_code: string;
    matched_text: string;
    severity: string;
    reasoning: string;
  }>;
}
```

⚠️ 기존 `ArticleMetadata`, `AnalysisReport`, `AnalysisPhase`는 일절 변경하지 않는다.
optional 필드만 `AnalysisResult`에 추가. 프론트엔드 코드(ResultViewer, TxtPreviewModal 등)는 변경 없음.

---

### 3-5. 변경하지 않는 파일 (명시적 목록)

| 파일 | 이유 |
|------|------|
| `scraper.py` | 파이프라인 앞단, 변경 불필요 |
| `core/analyzer.py` | 파일 보존 (기존 MVP 참조용). import만 main.py에서 제거 |
| `core/pattern_matcher.py` | Sonnet Solo 아키텍처 변경 없음 |
| `core/citation_resolver.py` | in-memory 원칙 변경 없음 |
| `core/chunker.py` | 변경 없음 |
| `core/db.py` | 변경 없음 |
| `core/criteria_manager.py` | 기존 MVP용, 변경 불필요 |
| `core/prompt_builder.py` | 기존 MVP용, 변경 불필요 |
| `frontend/components/ResultViewer.tsx` | 3종 탭, 디자인, 폰트 유지 |
| `frontend/components/TxtPreviewModal.tsx` | TXT 내보내기 유지 |
| `frontend/app/result/` | 결과 페이지 유지 |

---

## 4. 로컬 기동 테스트 절차

STEP 73 완료 기준으로, **기술적 기동 여부만 확인**한다.
품질 체감 평가는 Phase C 완료 후 종합 E2E(STEP 86)에서 수행.

### 4-1. 백엔드 기동

```bash
cd /Users/gamnamu/Documents/cr-check/backend
supabase start  # Docker 필요
SUPABASE_LOCAL=1 uvicorn main:app --reload --port 8000
```

확인:
- `http://localhost:8000/health` → 200 + `{"status": "healthy"}`
- `http://localhost:8000/docs` → Swagger UI에서 /analyze 스키마 확인
  - Request: `{ "url": "https://..." }`
  - Response: `{ "article_info": {...}, "reports": {"comprehensive": "...", "journalist": "...", "student": "..."} }`

### 4-2. 프론트엔드 기동

```bash
cd /Users/gamnamu/Documents/cr-check/frontend
npm run dev
```

확인:
- `http://localhost:3000` → 정상 로딩 (에러 없음)
- 기사 URL 입력 화면이 표시됨

### 4-3. 기동 테스트 (선택, API 비용 발생)

⚠️ 이 테스트는 Gamnamu 판단에 따라 수행. API 비용 ~$0.10/건.

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://news.nate.com/view/20251223n00688"}'
```

응답 확인:
- `article_info`에 title, url, articleType 등이 존재하는가
- `reports`에 comprehensive, journalist, student 3종이 모두 존재하는가
- 각 리포트에 cite 태그가 아닌 규범 원문이 삽입되어 있는가

---

## 5. 주의사항 체크리스트

- [ ] `core/analyzer.py` 파일 자체 삭제 금지 (참조용 보존)
- [ ] `scraper.py` 변경 금지
- [ ] deprecated 코드(1-Call, 2-Call) 삭제 금지
- [ ] 환경변수 확인: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SUPABASE_LOCAL`
- [ ] KJA 접두어 사용 금지
- [ ] 벤치마크 결과 파일 삭제 금지
- [ ] 기존 프론트엔드 인터페이스(ArticleMetadata, AnalysisReport) 변경 금지
- [ ] ResultViewer.tsx, TxtPreviewModal.tsx 변경 금지
- [ ] git commit/push 실행 금지 (Deny List)

---

## 6. 완료 보고 형식

STEP 73 완료 시, 아래 형식으로 보고:

```
## STEP 73 완료 보고

### 변경 파일
- backend/core/report_generator.py: (변경 요약)
- backend/core/pipeline.py: (변경 요약)
- backend/main.py: (변경 요약)
- frontend/types/index.ts: (변경 요약)

### 기동 테스트 결과
- localhost:8000/health: (결과)
- localhost:8000/docs: (스키마 확인)
- localhost:3000: (로딩 확인)

### 미해결 사항
- (있으면 기술)
```

---

*이 설계서는 2026-03-31 Claude.ai(STEP 71)가 작성하고, Gamnamu(STEP 72)가 승인했다.*
*Claude Code CLI는 이 설계서의 지시를 따라 STEP 73을 실행한다.*
