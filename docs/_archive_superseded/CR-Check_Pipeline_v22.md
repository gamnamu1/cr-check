# CR-Check 파이프라인 상세 문서

> **기준 버전:** SESSION_CONTEXT v22 (2026-04-05)
> **브랜치:** `feature/m6-wip`
> **상태:** Phase γ 완료, Phase D(아카이빙) 착수 대기

---

## 파이프라인 한 줄 요약

```
URL → 스크래핑 → 청킹(300~500자) → OpenAI 임베딩 → 벡터 검색(threshold 0.2)
  → ❶ Sonnet 4.5 Solo(패턴 식별 + Devil's Advocate CoT)
  → DB 밸리데이션 → 메타 패턴 추론(DB 동적 조회)
  → 규범 조회(재귀 CTE 롤업, RPC + REST fallback)
  → ❷ Sonnet 4.6(3종 리포트, 〔〕마커 자연 인용)
  → ResultViewer 렌더링(탭 UI, SNS 공유)
```

---

## 1. 입력 & 전처리

### 1-1. URL 입력 — `main.py`

- **엔드포인트:** `POST /analyze`
- **요청 모델:** `AnalyzeRequest(url: HttpUrl)`
- FastAPI 기반. CORS로 `localhost:3000`, `cr-check.vercel.app` 등 허용.
- Next.js 프런트엔드에서 호출.

### 1-2. 스크래핑 — `scraper.py`

- `ArticleScraper.scrape(url)` → 기사 메타데이터 딕셔너리 반환.
- 추출 항목: 제목, 본문, 매체명, 기자명, 게재일.
- 본문 50자 미만이면 `400 Bad Request`.
- publisher·journalist·publish_date 중 "미확인", 빈 값, "N/A" 등은 필터링.

### 1-3. 청킹 — `chunker.py`

한국 온라인 뉴스의 특성을 반영한 의미 기반 병합 청킹. 3단계 처리:

**① 전처리 (노이즈 제거)**
- 29종 정규식 패턴으로 노이즈 제거:
  - 사진 캡션 (`/홍길동 기자`, `[사진=연합뉴스]`)
  - 바이라인 (`홍길동 기자`, 이메일 주소)
  - 저작권 고지 (`ⓒ 연합뉴스`, `무단 전재 금지`)
  - 관련기사 링크, 포털 메타텍스트 (`네이버에서 구독`)
  - HTML 태그 잔여, 구분선

**② 의미 기반 병합**
- `\n\n`(빈 줄) → 단락 경계로 존중
- `\n` 단독 → 한국 뉴스의 한 문장 줄바꿈 관행으로 간주, 공백으로 병합
- 100자(`MIN_CHUNK_SIZE`) 미만 단락은 인접 단락과 병합

**③ 크기 조정**
- 500자(`TARGET_MAX`) 초과 → 한국어 문장 종결 패턴(`[.!?。다요]`) 기준 분할
- 300자(`TARGET_MIN`) 미만 → 인접 청크와 병합
- 500자(`SHORT_ARTICLE`) 이하 단문 기사 → 단일 청크

**출력:** `Chunk(text, start_idx, end_idx)` 리스트

---

## 2. 벡터 검색 (느슨한 후보 사전 필터)

### 2-1. 임베딩 생성 — `pattern_matcher.py`

- **모델:** OpenAI `text-embedding-3-small` (1536차원)
- `generate_embeddings(chunk_texts)` → OpenAI 배치 API 호출
- 현재 DB에 임베딩 401건 적재
- 프로덕션 배포 시 `scripts/generate_embeddings.py` 재실행 필수

### 2-2. 벡터 검색 RPC — `pattern_matcher.py` + Supabase

- **RPC 함수:** `search_pattern_candidates(query_embedding, match_threshold, match_count)`
- **설정:** `threshold=0.2`, `match_count=7`
- 청크별로 RPC 호출 → 패턴별 최고 유사도만 보존 → 유사도 내림차순 정렬
- ~102개 소분류 패턴에 대해 sequential scan (ivfflat 인덱스 불필요, 앙상블 검증 5/5 합의)

**핵심 발견 (M3~M4):**

> 구체적 뉴스 언어와 추상적 규범 설명은 다른 임베딩 공간에 위치한다.
> 벡터 검색만으로는 뉴스 기사와 윤리 위반 패턴을 매칭할 수 없다.
> 따라서 벡터 검색은 threshold 0.2~0.25의 **느슨한 후보 사전 필터**로만 사용하고,
> LLM이 실질적 패턴 식별을 담당하는 구조로 확정했다.

**출력:** `VectorCandidate(pattern_id, pattern_code, pattern_name, similarity)` 리스트

---

## 3. Phase 1 — 패턴 식별 (Sonnet 4.5)

### 3-1. 패턴 카탈로그 로드 + ★ 마킹

- `_load_pattern_catalog()` → DB에서 `hierarchy_level=3, is_meta_pattern=false` 조건으로 소분류 패턴 목록 로드 (결과 캐시됨)
- 벡터 검색 결과에 해당하는 패턴 코드에 ★ 마크 부착
- Sonnet이 ★ 패턴을 **우선 검토**하되, 비★ 패턴도 기사에 명확히 해당하면 **동등하게 선택** 가능

### 3-2. Sonnet 4.5 Solo 호출 — `match_patterns_solo()`

- **모델:** `claude-sonnet-4-5-20250929`
- **temperature:** 0.0
- **max_tokens:** 2048

**프롬프트 구조 (`_SONNET_SOLO_PROMPT`):**

1. **overall_assessment (필수, 먼저 작성)**
   - (가) 이 기사가 양질의 보도일 수 있는 근거
   - (나) 이 기사에 윤리적 문제가 있을 수 있는 근거
   - 둘 다 기술한 후, 어느 쪽이 더 강한지 종합 판단 (**Devil's Advocate CoT**)
   - (가)가 더 강하면 detections를 빈 배열로 둠

2. **detections (조건부)**
   - (나)가 더 강할 때만 JSON 배열로 출력
   - 형식: `[{pattern_code, matched_text, severity, reasoning}]`

**핵심 원칙:**
- **정밀도 우선:** 누락보다 오탐이 더 해로움
- 구체적 문장/표현을 특정할 수 없으면 해당 패턴 미선택
- 기사 길이별 최대 개수 가이드:
  - 200자 미만: 최대 1~2개
  - 200~500자: 최대 2~3개
  - 500~2000자: 최대 3~4개
  - 2000자 이상: 최대 4~5개

**few-shot 예시 9개** (TP 7 + TN 2):
- 언론윤리위 심의 데이터 2,597건 + 수상 저널리즘 작품에서 sourcing
- 혼동 패턴 쌍 가이드 포함 (1-1-1 vs 1-1-4, 1-3-1 vs 1-3-2, 1-7-2 vs 1-7-5 등)
- TN 예시로 탐사보도의 강한 표현이 양질의 보도일 수 있음을 학습

### 3-3. 밸리데이션 — `validate_pattern_codes()`

- Sonnet이 출력한 패턴 코드를 DB `patterns` 테이블에서 검증
- DB에 없는 코드는 **hallucinated**로 분류·제거
- 유효 코드만 ID로 변환
- 중복 `pattern_code` 제거 (첫 번째만 유지)

**출력:** `PatternMatchResult`
- `validated_pattern_ids`: 유효 패턴 ID 리스트
- `validated_pattern_codes`: 유효 패턴 코드 리스트
- `hallucinated_codes`: 환각 코드 리스트
- `haiku_raw_response`: Sonnet 원본 응답

**TN 처리:** 유효 패턴 0건이면 3종 리포트 모두 정적 메시지 반환:
> "분석 결과 문제적 보도관행이 발견되지 않았습니다."

---

## 4. 메타 패턴 추론 (Deterministic) — `meta_pattern_inference.py`

직접 감지가 불가능한 메타 패턴을 다른 패턴의 조합으로 간접 추론한다.

- **대상 패턴:**
  - `1-4-1`: 외부 압력에 의한 왜곡
  - `1-4-2`: 상업적 동기에 의한 왜곡

**추론 절차:**

1. DB `pattern_relations` 테이블에서 `relation_type=inferred_by` 관계 동적 조회 (코드에 규칙 하드코딩 없음)
2. `inference_role`로 `required`(필수 지표)와 `supporting`(보강 지표) 분리
3. 탐지된 패턴 코드와 대조

**트리거 조건:** `required` 1개 이상 AND `supporting` 1개 이상

**확신도 계산:**

| required | supporting | 확신도 |
|----------|------------|--------|
| ≥ 2     | ≥ 2       | high   |
| ≥ 1     | ≥ 2       | medium |
| 그 외    | —         | low    |

**발동 시 후속 처리:**
- Phase 2 Sonnet 프롬프트에 "구조적 문제 분석" 블록 주입
- 표현 수위는 확신도에 연동:
  - low → "일부 징후가 관찰됩니다"
  - medium → "구조적 문제의 가능성이 있습니다"
  - high → "강한 의심이 됩니다"
  - ❌ 단정적 표현("외부 압력이 있었다") 절대 금지

---

## 5. Phase 2 — 리포트 생성 (Sonnet 4.6)

### 5-1. 규범 조회 — `report_generator.py` + Supabase

**`fetch_ethics_for_patterns(pattern_ids)`**

확정 패턴 ID 리스트로 관련 윤리규범 원문을 조회한다.

**RPC 내부 로직 (`get_ethics_for_patterns`, 재귀 CTE):**

1. **`direct_codes`** — `pattern_ethics_relations` JOIN `active_ethics_codes` (is_active=true, is_citable=true)
2. **`parent_chain`** — 직접 규범의 상위 규범을 재귀적으로 수집 (최대 depth=5)
   - Tier 3~4(구체적 조항) → Tier 1~2(포괄적 원칙) 롤업
3. UNION으로 직접 관계 + 롤업 상위 규범 합산, 중복 자연 제거, tier 순 정렬

**3단계 방어 로직:**

1. RPC 1차 호출
2. 실패 또는 0건 → 2초 대기 후 재시도
3. 재시도도 0건 → REST API 직접 JOIN fallback (`pattern_ethics_relations` + `ethics_codes`)

**현재 매핑:** 63건 (Phase γ에서 무관한 매핑 7건 삭제, 2건 strength 하향)

**출력:** `EthicsReference(pattern_code, ethics_code, ethics_title, ethics_full_text, ethics_tier, relation_type, strength, reasoning)` 리스트 → tier 역순(구체→포괄) 정렬하여 텍스트 생성

### 5-2. Sonnet 4.6 3종 리포트 생성 — `call_sonnet()`

- **모델:** `claude-sonnet-4-6`
- **temperature:** 0.0
- **max_tokens:** 10000

**Sonnet에 전달되는 입력:**

```
1. 1차 분석 결과 (overall_assessment + detections JSON)
2. 관련 윤리규범 (규범 컨텍스트, tier 역순 정렬)
3. [조건부] 메타 패턴 구조적 문제 분석 블록
4. 기사 전문
```

**시스템 프롬프트 (`_SONNET_SYSTEM_PROMPT`) 핵심 원칙:**

**① CR-Check 포지셔닝**
- 저널리즘 비평의 **관점을 제시하는 도구**
- 점수, 등급, 순위 부여 절대 금지. 서술형 분석만.

**② 윤리규범 인용 방식 (〔〕 마커)**
- 규범 조항명: `〔신문윤리실천요강 제3조 1항〕` (꺾은 대괄호)
- 규범 내용 인용: `'보도기사는 사실과 의견을 명확히 구분하여 작성해야 한다'` (작은따옴표)
- 완성형: `〔신문윤리실천요강 제3조 1항〕은 '보도기사는...'고 규정합니다.`
- JEC-7, PCP-3-1 같은 내부 코드 사용 금지
- `<cite>` 태그 사용 금지

**③ 규범 인용의 깊이**
- 각 지적 사항에 구체적 조항(Tier 3~4) 인용
- 리포트 전체에서 1~2회 정도 상위 원칙(Tier 1~2)으로 의미 확장
- 매 지적마다 하위→상위 반복 금지

**④ 3종 리포트 톤 차이**

| 리포트 유형 | 대상 | 톤 | 특징 |
|------------|------|-----|------|
| comprehensive | 시민 | 이웃에게 말하듯 따뜻함 | 일상적 비유, 함께 살펴보는 시민의 관점 |
| journalist | 기자 | 동료 전문가의 건설적 피드백 | "시민 주도 CR 프로젝트를 통해..."로 시작, 개선안 제시 |
| student | 학생 | 초등 4~5학년 눈높이 | 해요체 일관, 격식체 금지, 이모지 적절 활용, 질문 유도 |

**⑤ 서술 스타일 가이드**
- 3종 리포트 모두 제목(#, ##) 없이 도입부 직접 시작
- 중간제목(###) 최대 3~4개
- "문제", "문제점" 반복 금지 → "눈에 띕니다", "아쉬운 지점" 등 다양한 표현
- 분석 개요: 각 항목 1~2문장, 최대 80자, 한 줄 요약

**⑥ 출력 형식**

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
    "comprehensive": "시민용 종합 리포트 (마크다운)",
    "journalist": "기자용 전문 리포트 (마크다운)",
    "student": "학생용 교육 리포트 (마크다운)"
  }
}
```

**재시도 로직:** 최대 3회, exponential backoff (1초→2초→4초). 구조 검증 — `reports` 키 존재 + 3종 필수 필드(`comprehensive`, `journalist`, `student`) 확인.

---

## 6. 출력 & 렌더링

### 6-1. 진단 JSON 덤프 — `pipeline.py`

파이프라인 완료 후 `backend/diagnostics/diagnostic_{timestamp}.json`에 자동 저장.
실패해도 파이프라인에 영향 없음 (try/except 격리).

**5개 체크포인트:**

| CP | 항목 | 내용 |
|----|------|------|
| 1 | 청킹 | 청크 수, 평균 길이, 청크별 미리보기 (80자) |
| 2 | 벡터 검색 | 후보 수, 패턴별 코드·이름·유사도 |
| 3 | 패턴 식별 | overall_assessment, detections, 환각 코드, Sonnet raw 응답 |
| 4 | 규범 조회 | 규범 수, 규범 없는 패턴, 규범별 상세 (코드·제목·tier·원문 300자 미리보기) |
| 5 | 리포트 | 3종 리포트 전문 (pre/post 동일 — cite 후치환 비활성화 상태), Sonnet raw 응답 |

### 6-2. API 응답 조합 — `main.py`

```python
AnalyzeResponse = {
    "article_info": {
        # 스크래퍼 메타데이터
        "title": "...",
        "url": "...",
        "publisher": "...",     # "미확인" 등 필터링
        "publishDate": "...",
        "journalist": "...",
        # Sonnet이 생성한 분석 개요 (병합)
        "articleType": "...",
        "articleElements": "...",
        "editStructure": "...",
        "reportingMethod": "...",
        "contentFlow": "..."
    },
    "reports": {
        "comprehensive": "시민용 종합 리포트",
        "journalist": "기자용 전문 리포트",
        "student": "학생용 교육 리포트"
    }
}
```

### 6-3. 프런트엔드 렌더링 — `ResultViewer.tsx`

**탭 UI:** 시민(Users) · 기자(NotebookPen) · 학생(BookOpenCheck) 3개 탭

**인용 렌더링 (`highlightEthics`):**

1. `〔규범명〕` + `'인용내용'` 패턴 감지 → 두 부분을 분리 스타일링:
   - **규범명:** Pretendard 고딕, fontWeight 400, opacity 0.9, fontSize 1em
   - **인용 내용:** 명조(본문 동일), `rgb(70, 130, 180)` (스틸블루)
2. `〔규범명〕` 단독 등장 → 동일 고딕 스타일 적용
3. `###` 중간제목 → Pretendard 고딕, fontSize 1.1em, fontWeight 600

**기타 기능:**
- Framer Motion 애니메이션 (fade-in, slide-up)
- TXT 저장 모달 (`TxtPreviewModal`)
- SNS 공유: 페이스북, X(트위터), 카카오톡(클립보드 복사 방식)
- 현재 `sessionStorage` 기반 → Phase F-2에서 URL 공유 전환 예정

---

## DB 스키마 개요 (Supabase)

### 핵심 테이블

| 테이블 | 역할 | 비고 |
|--------|------|------|
| `patterns` | 문제적 보도관행 패턴 (3계층) | description_embedding vector(1536), is_meta_pattern 구분 |
| `ethics_codes` | 언론윤리규범 조항 | 4-tier 구조, 버전 관리, is_citable 필터 |
| `pattern_ethics_relations` | 패턴 ↔ 규범 매핑 (63건) | relation_type: violates/related_to/exception_of, strength: strong/moderate/weak |
| `pattern_relations` | 패턴 간 관계 | relation_type: co_occurs/escalates_to/variant_of/inferred_by, inference_role 컬럼 |
| `ethics_code_hierarchy` | 규범 위계 (다대다) | parent_code_id ↔ child_code_id |
| `articles` | 기사 메타데이터 | URL 유니크 제약 (중복 분석 방지) |
| `analysis_results` | AI 분석 결과 | 3종 리포트 + detected_categories JSONB |
| `feedbacks` | 익명 피드백 | rating 1~5 + comment |
| `analysis_ethics_snapshot` | 규범 시점 스냅샷 | 규범 개정 시 과거 리포트 인용 근거 보존 |

### 핵심 RPC 함수

| 함수 | 용도 | 단계 |
|------|------|------|
| `search_pattern_candidates` | 벡터 검색 (cosine distance) | Phase 1 전처리 |
| `get_ethics_for_patterns` | 확정 패턴 → 규범 조회 (재귀 CTE 롤업) | Phase 2 |
| `get_trending_articles` | 실시간 트렌드 | 통계 |
| `get_publisher_stats` | 언론사별 통계 | 통계 |
| `get_overall_stats` | 전체 통계 요약 | 통계 |

### 뷰

| 뷰 | 역할 |
|----|------|
| `active_ethics_codes` | 활성 규범만 필터 (is_active=true) |
| `ethics_codes_history` | 규범 변경 이력 추적 (버전·개정 사유·후속 코드) |

---

## 주요 파일 경로

```
backend/
├── main.py                          ← FastAPI 엔드포인트
├── scraper.py                       ← 기사 스크래핑
├── core/
│   ├── pipeline.py                  ← 파이프라인 오케스트레이션 + 진단 덤프
│   ├── pattern_matcher.py           ← Phase 1: 벡터 검색 + Sonnet 4.5 Solo
│   ├── report_generator.py          ← Phase 2: 규범 조회 + Sonnet 4.6 리포트
│   ├── meta_pattern_inference.py    ← 메타 패턴 추론 (Deterministic)
│   ├── chunker.py                   ← 기사 청킹
│   ├── db.py                        ← Supabase 연결 (로컬 우선, 클라우드 폴백)
│   ├── criteria_manager.py          ← 평가 기준 관리 (레거시 호환)
│   ├── citation_resolver.py         ← 비활성화 (코드 보존)
│   └── prompt_builder.py            ← 프롬프트 빌더
├── diagnostics/                     ← 진단 JSON 자동 저장
└── .env                             ← 환경변수

frontend/
└── components/
    └── ResultViewer.tsx             ← 리포트 렌더링 (〔〕마커 + 탭 UI)

supabase/migrations/
├── 20260328000000_create_cr_check_schema.sql
├── 20260328100000_seed_data.sql
├── 20260329000000_data_implant_pattern_desc.sql
├── 20260401000000_meta_pattern_inference.sql
└── 20260405000000_cleanup_pattern_ethics_relations.sql
```

---

## 모델 구성

| 단계 | 모델 | 용도 | 비고 |
|------|------|------|------|
| 임베딩 | OpenAI `text-embedding-3-small` | 청크 임베딩 생성 | 1536차원 |
| Phase 1 | `claude-sonnet-4-5-20250929` | 패턴 식별 + Devil's Advocate | Phase γ에서 확정 (비용 28% 절감) |
| Phase 2 | `claude-sonnet-4-6` | 3종 리포트 생성 | 〔〕마커 자연 인용 |

Phase 1과 Phase 2를 다른 모델로 분리한 이유:
1. **비용 절감:** A/B 비교(B-11 기사)에서 패턴 식별 결과 유사, 비용 28% 절감
2. **편향 감소:** 모델 다양성에 의한 편향 감소 효과

---

## 설계 원칙 & 교훈

### 벡터 검색의 역할 한정
벡터 검색은 "정답을 찾는 도구"가 아니라 "후보를 줄여주는 사전 필터"로 자리매김. 구체적 뉴스 언어와 추상적 윤리 규범 설명은 다른 임베딩 공간에 위치하므로, 벡터 유사도만으로는 매칭 불가.

### 정밀도 우선 (Precision > Recall)
확증 편향(confirmation bias)을 방지하기 위해 Devil's Advocate CoT 도입. 양면 분석(양질의 보도 근거 vs 윤리적 문제 근거)을 강제하여 오탐(False Positive) 최소화.

### 인용 대체 아키텍처 폐기
초기 설계에서는 `<cite ref="JEC-7"/>` 태그를 Sonnet이 출력하고, `CitationResolver`가 사후에 규범 원문으로 치환하는 구조였다. 그러나 다섯 개 AI 시스템의 진단 보고서를 종합한 결과, **Sonnet이 실제 윤리 규범 텍스트 없이 보고서를 작성하고 인용이 사후 기계적으로 삽입되는 구조가 품질 저하의 근본 원인**으로 확인되어 폐기. 현재는 규범 원문을 프롬프트에 직접 제공하고 Sonnet이 자연어로 인용하는 방식(〔〕 마커).

### 규범 조회 3단계 방어
RPC 1차 호출 → 2초 대기 재시도 → REST API fallback. 네트워크 일시적 장애에도 규범 없이 리포트가 생성되는 상황을 방지.

### 메타 패턴의 결정론적 추론
외부 압력·상업적 동기는 텍스트에서 직접 감지할 수 없으므로, 다른 패턴의 조합으로 간접 추론하되 DB 동적 조회 방식으로 규칙을 코드에 하드코딩하지 않음.

---

*이 문서는 SESSION_CONTEXT v22 및 코드베이스 분석에 기반하여 2026-04-06에 작성되었다.*
