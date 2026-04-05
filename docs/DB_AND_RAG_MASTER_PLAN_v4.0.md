# CR-Check DB+RAG 통합 마스터 플랜

> **문서 상태**: Active — Single Source of Truth
> **최종 수정**: 2026-03-25 (앙상블 검증 반영: ivfflat 제거, is_citable 추가, 재귀 CTE 롤업, KJA→JCE 수정)
> **운영 방식**: 전 Phase 익명 운영 (Auth 없음), 분석 결과는 공개 URL로 접근·공유

---

## 1. 프로젝트 배경 및 목표

### 1.1 핵심 문제

CR-Check의 가장 근본적인 기술 부채: **119개 보도관행 패턴 ↔ 언론윤리규범의 정적 하드코딩 매핑.**

매핑이 정적이면:
- AI 윤리 코드 인용 시 환각(hallucination) 발생
- 새 패턴/규범 추가 시 코드 수정 필요
- 매핑 근거(reasoning)가 부재하여 설명가능성 부족

### 1.2 해결 방향

**Hybrid RAG (Vector Search + Relational Graph)** — Supabase 단일 플랫폼

- Vector Search: pgvector로 기사↔패턴 의미 매칭 (후보 선정)
- Relational Graph: 관계형 테이블로 패턴→규범 정확 매핑 (경계 강제)
- 원문 직접 조회: 규범 인용은 DB에서 글자 그대로 가져옴 (환각 원천 차단)

이 규모(262개 엔티티)에서 관계 테이블은 오버엔지니어링이 아니라 필수.
순수 벡터 검색만으로는 "자살 보도" 기사에서 '재난보도준칙'이 잘못 매칭되는 등의 경계 실패가 발생할 수 있다.

---

## 2. 도메인 데이터 프로파일

### 2.1 문제적 보도관행 패턴

**출처**: `current-criteria_v2_active.md`

| 항목 | 수치 |
|------|------|
| 대분류 | 8개 (진실성, 투명성, 균형성, 독립성, 인권, 전문성, 언어, 디지털) |
| 중분류 | 27개 |
| 소분류 (임베딩 최소 단위) | ~104개 |
| 메타 패턴 (직접 감지 불가) | 2개 (1-4-1 외부압력, 1-4-2 상업적 동기) |
| 임베딩 대상 | ~102개 |
| 소분류 평균 텍스트 길이 | ~350자 |
| 패턴 간 교차참조 (명시적) | 15건+ |
| 암묵적 관계 추정 | 추가 15~25건 |

### 2.2 윤리규범 원문

**출처**: `Code of Ethics for the Press.md` + 기자협회 사이트

| 항목 | 수치 |
|------|------|
| 수록된 규범 문서 | 14개 (수집 완료, 2026-03-19) |
| 임베딩 대상 (추정) | ~160개 |
| 총 텍스트량 | ~40,000자 (1,097줄) |

**추가 수록 완료된 규범 6개** (2026-03-19 작업 A 완료):

| 규범 | Tier | 패턴 대응 |
|------|------|-----------|
| 자살예방 보도준칙 | 3 | 1-7-4 자살 보도 |
| 재난보도준칙 | 3 | 1-6-3 현장성, 1-7-4 사건 묘사 |
| 감염병보도준칙 | 3 | 1-1-5 데이터 오용, 1-7-3 과장 |
| 선거여론조사 보도준칙 | 3 | 1-1-5 여론조사 특수 문제 |
| 평화통일 보도 준칙 | 3 | 1-3-2 이념 편향, 1-7-5 차별 |
| 혐오표현 반대 미디어 실천 선언 | 4 | 1-7-5 차별/혐오 표현 |

### 2.3 교차 분석 요약

| 항목 | 수치 |
|------|------|
| 패턴 임베딩 대상 | ~102개 |
| 규범 임베딩 대상 | ~160개 |
| 전체 임베딩 대상 | ~262개 |
| 예상 관계 (pattern↔ethics) | 300~500건 |
| 패턴 간 관계 (시드 + 확장) | 30~50건 |
| 총 텍스트량 | ~52,000자 |

**결론**: 소규모 정밀 검색 시스템. Supabase pgvector 무료 티어로 충분.

---

## 3. 로드맵 — 4 Phase 구조

```
Phase 0: RAG 지식베이스 + MVE(최소 평가 체계) ← 동시 진행
    ↓
Phase 1: 아카이빙 (분석 결과 저장 + 공개 URL 공유)
    ↓
Phase 2: 통계 대시보드
    ↓
Phase 3: 커뮤니티 (익명 피드백)
```

전 Phase 익명 운영. 분석 결과는 고유 ID 기반 공개 URL(`/report/{id}`)로 접근·공유.
피드백도 익명 수집(user_id 없이 analysis_id + rating + comment만 저장).

### Phase 0: RAG 지식베이스 + 최소 평가 체계 [핵심]

**해결하는 문제**:
- 정적 JSON 매핑 → 동적 검색+추론으로 대체
- AI 윤리 코드 인용 환각 → 결정론적 인용으로 원천 차단
- 매핑 근거 부재 → reasoning 필드로 설명가능성 확보

**작업** (Phase 0 + 1 동시 진행):
1. Supabase 프로젝트 생성, pgvector 활성화
2. 전체 스키마 한 번에 생성 (RAG 테이블 + 기본 테이블 + 버전관리)
3. 패턴/규범 데이터 입력 및 임베딩 생성
4. 관계 데이터 초기 구축 (시드 15건 + 임베딩 유사도/LLM 추출 확장)
5. 하이브리드 검색 함수 구현
6. 골든 데이터셋 20~30건 구축
7. 임베딩 모델 경량 벤치마크
8. threshold 튜닝

### Phase 1~3

- Phase 1: 아카이빙 + 공개 URL 공유 (2-3일)
- Phase 2: 통계 대시보드 (5-7일)
- Phase 3: 커뮤니티 — 익명 피드백 (향후)

상세 구현 코드: `_archive_superseded/DB_CONSTRUCTION_FINAL_PLAN.md` 참조.

---

## 4. 핵심 기술 결정

### 결정 A — 청킹 전략

| 데이터 유형 | 청킹 전략 | 근거 |
|-------------|-----------|------|
| 패턴 소분류 | 그대로 사용 | 평균 350자, 자연 구조 |
| 윤리규범 조항 | 세부 조항 단위 | 정확한 원문 인용 필요 |
| 기사 텍스트 | 의미 기반 병합 청킹 | 한국 뉴스의 한 문장 줄바꿈 관행 대응 |

**기사 청킹 상세**:

한국 온라인 뉴스는 한 문장 단위로 줄바꿈하는 경우가 매우 많아,
단순 `\n\n` 분리 시 문맥이 완전히 훼손된다.

```
[의미 기반 병합 청킹 절차]

1. 전처리 (노이즈 제거)
   - 사진 캡션, 바이라인, 기자 이메일을 정규식으로 제거
   - 광고성 문구, 관련기사 링크 등 비본문 요소 필터링

2. 단락 병합
   - 짧은 단락(100자 미만)을 인접 단락과 병합
   - 목표: 300~500자 단위의 의미 있는 컨텍스트 블록
   - 기사당 2~5개 청크 생성

3. 각 청크를 개별 임베딩하여 패턴 DB 검색
4. 검색 결과를 청크별로 수집, 패턴별 최고 유사도 기준 상위 후보 도출
5. 기사 텍스트 자체는 DB에 저장하지 않음 (저작권 원칙 준수)
```

**엣지케이스 대응**:
- 한 문장 줄바꿈 기사: 병합 로직이 처리
- 리스트형 기사: 리스트 항목을 하나의 청크로 묶음
- 1만자+ 장문 기사: 매칭 상위 3~4개 청크만 프롬프트에 선별 주입

### 결정 B — 관계 모델링 수준

**결정**: 관계형 테이블로 충분. 단, 3가지를 보강.

- 보강 1: ethics_codes에 tier, tier_rationale, parent_code_id, domain, locale, 버전관리 컬럼 추가
- 보강 2: pattern_relations 테이블 신규 (source, confidence, verified 포함)
- 보강 3: ethics_code_hierarchy Junction Table 사전 생성 (다대다 대비)

전용 Graph DB(Neo4j)는 **4-Hop 이상의 다중 네트워크 순회**가 필요해질 때 재검토.
현 규모(262개 엔티티)에서는 명백한 오버엔지니어링.

### 결정 C — 임베딩 모델

**1차 선택**: OpenAI text-embedding-3-small (1536차원)
**대안 후보**: Voyage AI voyage-3, Upstage solar-embedding-1-large, BAAI bge-m3

Phase 0에서 골든셋 20~30건을 활용해 OpenAI vs 대안 모델의 Recall을 비교하는 **경량 벤치마크**를 실시.
결과에 따라 모델 교체 가능하도록 **임베딩 생성 모듈을 추상화**.

벤치마크 시 핵심 검증 포인트:
- 기사 문장("무죄추정 원칙을 위반했다")과 규범 문장("피의자는 유죄 판결 확정 전까지 무죄로 추정") 간 의미적 매칭
- 법률/규범 문체와 일상 뉴스 문체 사이의 도메인 갭 처리 능력

### 결정 D — 유사도 검색 전략

Top-K + 느슨한 threshold 혼합.

```
match_threshold = 0.5  (느슨하게, 환경변수로 관리)
match_count = 10       (상위 K개로 제한)
```

- 느슨한 threshold로 관련 패턴의 누락(recall 저하)을 방지
- Top-K로 무관한 패턴의 유입(precision 저하)을 제한
- Haiku가 컨텍스트를 읽고 무관한 결과를 걸러내는 "LLM as filter" 역할
- threshold 값은 골든셋 기반으로 경험적 튜닝

### 결정 E — RAG 호출 구조 ⭐

**1.5회 호출 구조**:

```
기사 → 청킹 → 임베딩 → 벡터검색(패턴 후보만, 규범 없이)
    → Haiku(패턴 확정)
    → 확정된 패턴 ID로 규범 정밀 조회 (DB JOIN)
    → Sonnet(확정 패턴 + 정확한 규범 컨텍스트)
```

**핵심 가치**:
- Haiku에게는 패턴 후보(코드+설명)만 제공 → 토큰 절약
- Sonnet에게는 Haiku가 확정한 패턴에 연결된 규범만 정밀 전달 → 사각지대 제거
- "컨텍스트에 없어서 규범을 인용 못하는" 문제(Silent Miss)를 구조적으로 해소

### 결정 F — 인용 아키텍처 ⭐

**결정론적 인용(Deterministic Quoting)** 도입.

LLM에게 규범 원문을 "복사해서 출력하라"고 기대하는 대신,
**식별자만 반환**하게 하고, 백엔드에서 DB 원문을 직접 삽입.

```
[흐름]
1. Sonnet 프롬프트: "규범 인용 시 <cite ref="{ethics_code}"/> 태그만 출력하세요"
2. Sonnet 출력: "이 기사는 <cite ref="JCE-3"/>을 위반합니다"
3. 백엔드 후처리: <cite ref="JCE-3"/>를 ethics_codes 테이블의 full_text로 치환
4. 최종 리포트: 100% 정확한 원문 인용 보장

[보완] 정규식 검증을 안전망으로 병행:
- 리포트 내 인용문이 DB 원문과 일치하는지 후처리 검증
```

**가치**: 인용 정확성이 LLM의 확률적 생성에 의존하지 않음.

---

## 5. 윤리규범 위계 & 인용 구조

### 5.1 4 Tier 위계 구조

**분류 기준**: 명칭이 아닌 **"규범의 적용 범위와 구체성"**으로 분류.
- Tier 1: 전 분야에 걸친 선언적 원칙
- Tier 2: 전 분야에 걸친 행동 규범
- Tier 3: 특정 분야의 구체적 지침
- Tier 4: 권고 수준

```
Tier 1 — 헌장·선언
  └─ 언론윤리헌장 (9개 원칙)

Tier 2 — 강령·요강 (전 분야 행동 규범)
  ├─ 기자윤리강령 (10조)
  ├─ 기자윤리실천요강 (3장 17항)
  ├─ 신문윤리강령 (7조)
  └─ 신문윤리실천요강 (16조 ~50개 세부항)

Tier 3 — 준칙·보도기준 (특정 분야 지침)
  ├─ 인권보도준칙, 자살보도 윤리강령*, 자살예방 보도준칙,
  │   재난보도준칙, 감염병보도준칙, 선거여론조사 보도준칙,
  │   평화통일 보도 준칙, 군 취재·보도 기준, 생성형AI 준칙

Tier 4 — 권고기준·가이드라인
  ├─ 혐오표현 반대 미디어 실천 선언*, 성폭력/아동학대/정신건강/장애인 보도 권고기준 등
```

*주의: '자살보도 윤리강령'은 명칭에 '강령'이 있으나 특정 분야(자살보도) 지침이므로 Tier 3.
'혐오표현 반대 선언'은 명칭에 '선언'이 있으나 권고 수준이므로 Tier 4.
이러한 경계 모호 케이스는 `tier_rationale` 필드에 분류 근거를 명시한다.

### 5.2 구체→포괄 롤업 인용법

리포트 인용 시 가장 구체적인(하위 tier) 규범을 먼저 제시하고,
상위 규범으로 올라가며 원칙적 맥락을 부여한다.

```
[리포트 인용 포맷]
위반 사항: {구체적 문제 설명}
관련 규범:
① [준칙] {Tier 3/4 조항} — 가장 구체적인 근거
② [강령] {Tier 2 조항} — 원칙적 근거
③ [원칙] {Tier 1 조항} — 포괄적 맥락
```

### 5.3 parent-child 매핑 원칙

**초기 전략**: 단일 부모(primary parent)로 출발.
**확장 대비**: `ethics_code_hierarchy` Junction Table을 미리 생성.

하나의 조항이 여러 상위 원칙에 해당하는 경우(예: 인권보도준칙 2장 2조 가항 →
'무죄추정 원칙' + '공정보도 원칙' 양쪽에 연결), 운영 과정에서 롤업이 불완전한
케이스가 발견될 때 Junction Table을 통해 보조 부모를 점진적으로 추가한다.

---

## 6. 통합 데이터베이스 스키마

### 6.1 Phase 0: RAG 지식베이스 테이블

```sql
-- ============================================
-- CR-Check RAG 지식베이스 스키마
-- ============================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 문제적 보도관행 패턴
CREATE TABLE public.patterns (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT,
  subcategory TEXT,
  is_meta_pattern BOOLEAN DEFAULT FALSE,
  hierarchy_level INT,          -- 1=대분류, 2=중분류, 3=소분류
  parent_pattern_id BIGINT REFERENCES public.patterns(id),
  locale TEXT NOT NULL DEFAULT 'ko-KR',   -- 다국어 확장 대비
  description_embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_patterns_code ON public.patterns(code);
CREATE INDEX idx_patterns_locale ON public.patterns(locale);
-- 벡터 인덱스 불필요: ~102개 패턴 규모에서 sequential scan이
-- 100% recall + 1ms 미만 응답으로 ivfflat/HNSW보다 우수.
-- 1만 건 이상 확장 시 HNSW 도입 검토. (앙상블 검증 2026-03-25, 5/5 합의)
```

```sql
-- 2. 언론윤리규범 조항 (버전 관리 포함)
CREATE TABLE public.ethics_codes (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  code TEXT NOT NULL,
  title TEXT NOT NULL,
  full_text TEXT NOT NULL,
  source TEXT NOT NULL,
  article_number TEXT,
  tier INT NOT NULL CHECK (tier BETWEEN 1 AND 4),
  tier_rationale TEXT,          -- Tier 분류의 논리적 근거 (경계 모호 케이스 대응)
  parent_code_id BIGINT REFERENCES public.ethics_codes(id),
  domain TEXT DEFAULT 'general',
  locale TEXT NOT NULL DEFAULT 'ko-KR',   -- 다국어 확장 대비
  -- 버전 관리
  version INT NOT NULL DEFAULT 1,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
  effective_until DATE,                    -- NULL = 현재 유효
  superseded_by BIGINT REFERENCES public.ethics_codes(id),
  change_reason TEXT,
  is_citable BOOLEAN NOT NULL DEFAULT TRUE,  -- 서문/부칙 등 인용 부적합 조항 필터링 (앙상블 검증 5/5 합의)
  text_embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT unique_ethics_code_version UNIQUE (code, version)
);

CREATE INDEX idx_ethics_code ON public.ethics_codes(code);
CREATE INDEX idx_ethics_locale ON public.ethics_codes(locale);
CREATE INDEX idx_ethics_active ON public.ethics_codes(is_active);
-- 벡터 인덱스 불필요: ~160개 규범 규모에서 sequential scan 충분.
-- 패턴 관계 확장(섹션 9) 및 임베딩 벤치마크(M3)에서 활용 예정.

-- 활성 규범만 검색하는 뷰
CREATE VIEW public.active_ethics_codes AS
  SELECT * FROM public.ethics_codes WHERE is_active = TRUE;

-- 규범 변경 이력 추적 뷰
CREATE VIEW public.ethics_codes_history AS
  SELECT ec.code, ec.version, ec.title,
         ec.effective_from, ec.effective_until,
         ec.is_active, ec.change_reason,
         successor.code as successor_code,
         successor.version as successor_version
  FROM public.ethics_codes ec
  LEFT JOIN public.ethics_codes successor ON ec.superseded_by = successor.id
  ORDER BY ec.code, ec.version;
```

```sql
-- 3. 규범 위계 관계 (다대다 대비 Junction Table)
CREATE TABLE public.ethics_code_hierarchy (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  parent_code_id BIGINT REFERENCES public.ethics_codes(id) NOT NULL,
  child_code_id BIGINT REFERENCES public.ethics_codes(id) NOT NULL,
  relation_note TEXT,
  CONSTRAINT unique_hierarchy UNIQUE (parent_code_id, child_code_id)
);

-- 초기에는 ethics_codes.parent_code_id(단일 부모)만 사용.
-- 롤업 불완전 케이스 발견 시 이 테이블을 통해 보조 부모 추가.

-- 4. 패턴 ↔ 윤리규범 관계
CREATE TABLE public.pattern_ethics_relations (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  pattern_id BIGINT REFERENCES public.patterns(id) ON DELETE CASCADE NOT NULL,
  ethics_code_id BIGINT REFERENCES public.ethics_codes(id) ON DELETE CASCADE NOT NULL,
  relation_type TEXT NOT NULL CHECK (relation_type IN (
    'violates', 'related_to', 'exception_of'
  )),
  strength TEXT DEFAULT 'moderate' CHECK (strength IN ('strong', 'moderate', 'weak')),
  reasoning TEXT,
  examples TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT unique_pattern_ethics UNIQUE (pattern_id, ethics_code_id, relation_type)
);

CREATE INDEX idx_rel_pattern ON public.pattern_ethics_relations(pattern_id);
CREATE INDEX idx_rel_ethics ON public.pattern_ethics_relations(ethics_code_id);

-- 5. 패턴 간 관계
CREATE TABLE public.pattern_relations (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  source_pattern_id BIGINT REFERENCES public.patterns(id) NOT NULL,
  target_pattern_id BIGINT REFERENCES public.patterns(id) NOT NULL,
  relation_type TEXT NOT NULL CHECK (relation_type IN (
    'co_occurs', 'escalates_to', 'variant_of', 'inferred_by'
  )),
  description TEXT,
  source TEXT DEFAULT 'manual' CHECK (source IN (
    'manual', 'embedding_similarity', 'llm_extracted', 'co_occurrence_mined'
  )),
  confidence FLOAT DEFAULT 1.0,   -- 0.0~1.0, manual=1.0
  verified BOOLEAN DEFAULT FALSE,
  CONSTRAINT unique_pattern_rel UNIQUE (source_pattern_id, target_pattern_id, relation_type)
);
```

```sql
-- 6. 분석 리포트 규범 스냅샷 (시점 보존)
CREATE TABLE public.analysis_ethics_snapshot (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  analysis_id BIGINT REFERENCES public.analysis_results(id) ON DELETE CASCADE NOT NULL,
  ethics_code_id BIGINT REFERENCES public.ethics_codes(id) NOT NULL,
  snapshot_full_text TEXT NOT NULL,   -- 분석 시점 원문 (비정규화, 의도적)
  snapshot_version INT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE public.analysis_ethics_snapshot IS
  '분석 리포트가 참조한 규범 조항의 시점 스냅샷.
   규범이 개정되어도 과거 리포트의 인용 근거가 보존됨.
   저장 범위: Sonnet이 실제로 <cite ref/>로 인용한 규범만 스냅샷.
   get_ethics_for_patterns가 반환한 전체가 아님 — 리포트에 인용되지 않은 규범의 스냅샷은 불필요.';
```

```sql
-- 7. 하이브리드 검색 함수

-- 7a. 패턴 후보 검색 (Haiku 단계용: 규범 없이 패턴만)
CREATE OR REPLACE FUNCTION search_pattern_candidates(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.5,
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  pattern_id BIGINT,
  pattern_code TEXT,
  pattern_name TEXT,
  pattern_description TEXT,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.code, p.name, p.description,
         1 - (p.description_embedding <=> query_embedding) as similarity
  FROM public.patterns p
  WHERE p.is_meta_pattern = FALSE
  AND 1 - (p.description_embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- 7b. 확정 패턴에 대한 규범 정밀 조회 + 롤업 parent chain (Sonnet 단계용)
-- 앙상블 검증 반영: 재귀 CTE로 parent chain 수집 (최대 2-hop, 비용 미미)
CREATE OR REPLACE FUNCTION get_ethics_for_patterns(
  confirmed_pattern_ids BIGINT[]
)
RETURNS TABLE (
  pattern_id BIGINT,
  pattern_code TEXT,
  ethics_code_id BIGINT,
  ethics_code TEXT,
  ethics_title TEXT,
  ethics_full_text TEXT,
  ethics_tier INT,
  relation_type TEXT,
  strength TEXT,
  reasoning TEXT
) AS $$
BEGIN
  RETURN QUERY
  WITH direct_codes AS (
    -- 1단계: pattern_ethics_relations에서 직접 연결된 규범
    SELECT per.pattern_id, p.code AS p_code,
           ec.id AS ec_id, ec.code AS ec_code, ec.title, ec.full_text, ec.tier,
           per.relation_type, per.strength, per.reasoning
    FROM public.pattern_ethics_relations per
    JOIN public.patterns p ON per.pattern_id = p.id
    JOIN public.active_ethics_codes ec ON per.ethics_code_id = ec.id
    WHERE per.pattern_id = ANY(confirmed_pattern_ids)
    AND ec.is_citable = TRUE
  ),
  parent_chain AS (
    -- 2단계: 직접 규범의 parent chain을 재귀적으로 수집 (구체→포괄 롤업)
    SELECT ec.id, ec.code, ec.title, ec.full_text, ec.tier, ec.parent_code_id
    FROM public.ethics_codes ec
    WHERE ec.id IN (SELECT ec_id FROM direct_codes)
    AND ec.is_active = TRUE
    UNION
    SELECT parent.id, parent.code, parent.title, parent.full_text, parent.tier, parent.parent_code_id
    FROM public.ethics_codes parent
    JOIN parent_chain child ON parent.id = child.parent_code_id
    WHERE parent.is_active = TRUE AND parent.is_citable = TRUE
  )
  -- 직접 관계 규범 반환
  SELECT dc.pattern_id, dc.p_code,
         dc.ec_id, dc.ec_code, dc.title, dc.full_text, dc.tier,
         dc.relation_type, dc.strength, dc.reasoning
  FROM direct_codes dc
  UNION
  -- 롤업 상위 규범 반환 (직접 관계에 없는 parent만)
  SELECT DISTINCT d.pattern_id, d.p_code,
         pc.id, pc.code, pc.title, pc.full_text, pc.tier,
         'related_to'::TEXT, 'moderate'::TEXT, 'parent chain rollup'::TEXT
  FROM parent_chain pc
  CROSS JOIN (SELECT DISTINCT pattern_id, p_code FROM direct_codes) d
  WHERE pc.id NOT IN (SELECT ec_id FROM direct_codes)
  ORDER BY tier;
END;
$$ LANGUAGE plpgsql STABLE;
```

### 6.2 Phase 1 이후: 기본 테이블

Phase 1~3의 테이블(articles, analysis_results, feedbacks)과
통계 함수는 `_archive_superseded/DB_CONSTRUCTION_FINAL_PLAN.md`의 스키마를 기반으로 사용한다.
단, `profiles` 테이블, `bookmarks` 테이블, `analysis_results.user_id` FK는 제거.
분석 결과는 고유 ID로만 식별하고 공개 URL로 접근·공유.
피드백은 익명 수집 (user_id 없이 analysis_id + rating + comment만 저장).

핵심 테이블 요약:

| 테이블 | 역할 | Phase |
|--------|------|-------|
| articles | 기사 메타데이터 (URL 중복 방지) | 1 |
| analysis_results | AI 분석 결과 저장 + 공개 URL 공유 | 1 |
| feedbacks | 익명 사용자 피드백 (평점 + 코멘트) | 3 |

---

## 7. RAG 파이프라인 아키텍처

### 7.1 현재 구조 (As-Is)

```
기사 URL → 스크래핑 → Haiku (패턴 식별) → Sonnet (보고서)
                            ↓                    ↓
                     정적 JSON 참조          정적 JSON 참조
```

### 7.2 RAG 통합 후 구조 (To-Be) — 1.5회 호출

```
기사 URL → 스크래핑 → 전처리(노이즈 제거)
    ↓
의미 기반 병합 청킹 (300~500자 블록)
    ↓
청크별 임베딩 생성 (배치 API 1회 호출)
    ↓
search_pattern_candidates() — [벡터검색: 패턴 후보만, 규범 없이]
(느슨한 threshold + Top-K)
    ↓
Claude Haiku ← 기사 + 패턴 후보 (코드, 이름, 설명)
(패턴 식별 및 확정)
    ↓
백엔드 밸리데이션: Haiku가 출력한 패턴 코드가 DB에 존재하는지 검증
(RAG 컨텍스트에 없는 코드를 환각할 수 있으므로, 미존재 코드는 제거)
    ↓
get_ethics_for_patterns() — [정밀 조회: 확정 패턴의 규범만]
(관계 테이블 JOIN → parent chain 수집 → tier 역순 정렬)
    ↓
Claude Sonnet ← Haiku 확정 결과 + 규범 원문 컨텍스트
(결정론적 인용: <cite ref/> 태그만 출력)
    ↓
백엔드 후처리: cite 태그 → DB 원문 치환 + 정규식 검증
    ↓
최종 리포트 → Supabase 저장
  - analysis_results: 리포트 본문
  - analysis_ethics_snapshot: Sonnet이 실제로 <cite ref/>로 인용한 규범만 스냅샷 저장
```

### 7.3 프롬프트 템플릿

```
[Haiku 프롬프트 — 패턴 식별]

<s>
당신은 한국 뉴스 기사의 보도 품질을 평가하는 전문 분석가입니다.
아래 '후보 패턴'과 기사를 비교하여, 실제로 해당되는 패턴을 선별하세요.
후보에 없더라도 기사에서 명백히 발견되는 문제가 있으면 패턴 코드와 함께 제시하세요.
</s>

<candidates>
## 후보 패턴 (벡터 검색 상위 결과)
{pattern_code}: {pattern_name}
설명: {pattern_description}
(반복, 규범 텍스트 없음)
</candidates>

<article>
{기사 전문}
</article>

<instruction>
기사에서 확인되는 문제적 보도관행을 JSON으로 반환하세요.
각 항목: pattern_code, matched_text (해당 문장), severity (high/medium/low)
</instruction>
```

```
[Sonnet 프롬프트 — 상세 보고서 + 결정론적 인용]

<s>
당신은 한국 신문윤리위원회 수준의 상세 분석 보고서를 작성하는 전문가입니다.
규범을 인용할 때 원문을 직접 작성하지 마세요.
대신 <cite ref="{ethics_code}"/> 태그만 삽입하세요.
시스템이 자동으로 정확한 원문을 삽입합니다.
</s>

<haiku_result>
{Haiku 1단계 분석 결과 JSON}
</haiku_result>

<ethics_context>
## 관련 윤리규범 (확정 패턴에 연결된 규범만, tier 역순)
[코드: {code}] [Tier {tier}] {title}
원문: {full_text}
(반복)
</ethics_context>

<article>
{기사 전문}
</article>

<instruction>
각 위반 사항에 대해:
- 구체적 문장 인용 + 문제점 설명
- 관련 규범: <cite ref="{ethics_code}"/> 태그로 삽입 (구체→포괄 순)
- 종합 평가 및 개선 제안
메타 패턴(1-4-1, 1-4-2)이 의심되는 경우 별도 섹션으로 분리.
</instruction>
```

### 7.4 토큰 예산

| 항목 | 추정 토큰 |
|------|-----------|
| 시스템 프롬프트 + 지시 | ~500 |
| 패턴 후보 (Haiku용, 10개) | ~1,500 |
| 규범 컨텍스트 (Sonnet용, 확정 패턴 기준) | ~2,000 |
| 기사 텍스트 | ~1,500~2,000 |
| **총 입력** | **~5,000~6,000** |

한국어 토큰 소비율(영어 대비 2~2.5배) 감안해도 충분.
1만자+ 장문 기사 대응: 매칭 상위 3~4개 청크만 선별 주입.

---

## 8. 메타 패턴 추론 설계

1-4-1(외부 압력)과 1-4-2(상업적 동기)는 직접 감지가 불가능하며,
다른 패턴의 조합으로 추론해야 하는 "메타 패턴"이다.

### 8.1 하이브리드 추론 파이프라인

```
Step 1: 규칙 기반 사전 필터링 (Deterministic)
├─ Haiku가 식별한 패턴 중 메타 패턴 관련 지표 수를 카운트
├─ 관련 지표 2개 미만 → 메타 패턴 추론 건너뜀
├─ 관련 지표 2개 이상 → Step 2로 전달
└─ 근거 패턴 목록을 리포트에 명시

Step 2: LLM 기반 종합 판단 (Probabilistic)
├─ Sonnet에 메타 패턴 추론 지시 + 관련 지표 목록 주입
├─ 기사의 전체 맥락(주제, 취재원 구성, 논조)을 고려한 판단
├─ 확신도(낮음/중간/높음)와 근거를 함께 생성

Step 3: 표현 수위 가드레일
├─ 지표 2개 + 확신도 낮음 → "일부 징후가 관찰됩니다"
├─ 지표 3개 + 확신도 중간 → "구조적 문제의 가능성이 있습니다"
├─ 지표 4개+ + 확신도 높음 → "강한 의심이 됩니다"
└─ 단정적 표현("외부 압력이 있었다") 절대 금지
```

### 8.2 추론 규칙

**1-4-1 외부 압력**:
- 필수 조건 (1개+): 1-1-1(익명 단일 취재원) 또는 1-1-2(보도자료 받아쓰기)
- 보강 조건 (1개+): 1-3-2(이념 편향), 1-3-2(선별적 사실), 1-1-1(반론권 미보장), 1-3-1(관점 다양성 부족)
- 트리거: 필수 1개 + 보강 1개 이상

**1-4-2 상업적 동기**:
- 필수 조건 (1개+): 1-7-3(낚시성 제목) 또는 1-7-4(자극적 표현)
- 보강 조건 (1개+): 1-1-1(무검증 인용), 1-8-2(뉴스 어뷰징), 1-7-3(과장), 1-6-1(심층성 부족)
- 트리거: 필수 1개 + 보강 1개 이상

### 8.3 구현 원칙

- 추론 규칙을 코드에 하드코딩하지 않음. `pattern_relations`의 `inferred_by` 관계를 동적 조회하여 규칙 구성.
- 메타 패턴 추론 결과는 리포트에서 **별도 섹션("구조적 문제 분석")**으로 분리.
- 직접 탐지된 패턴과 추론된 패턴의 구분을 명확히 한다.

---

## 9. 패턴 관계 확장 워크플로우

### 9.1 현황

명시적 교차참조 15건은 문서 작성자가 부수적으로 삽입한 것에 불과.
최소 9건 이상의 의미적으로 유효한 암묵적 관계가 누락 추정.
전체 유의미 관계는 30~50건 수준으로 추정.

### 9.2 3단계 점진적 확장

```
[Stage 1: Phase 0 구축 시점] — 즉시 실행
├─ 명시적 교차참조 15건 → pattern_relations 시드 INSERT
├─ 102개 패턴 임베딩 유사도 매트릭스 → 유사도 상위 후보 추출
├─ LLM(Claude)에 102개 패턴 전문 제공 → 구조화된 관계 추출
├─ 두 후보의 교집합(높은 확신) + 합집합(검수 대상) 분류
└─ 수동 검수 → 총 30~40건 초기 관계 확보

[Stage 2: Phase 1 운영 3개월 후] — 데이터 축적 후
├─ analysis_results에서 패턴 공출현(co-occurrence) 마이닝
├─ 경험적으로 확인된 관계 강화, 미확인 관계 약화
└─ 총 40~60건 관계 확보

[Stage 3: 지속적 운영] — 반기 1회
├─ 공출현 통계 갱신
├─ 새 패턴 추가 시 기존 패턴과의 관계 자동 후보 생성
└─ 관계 데이터 precision/recall 정기 평가
```

---

## 10. 규범 버전 관리

### 10.1 핵심 원칙

1. 규범 레코드는 **절대 UPDATE/DELETE하지 않는다** (Immutable Records)
2. 개정 시 새 레코드를 INSERT하고, 이전 레코드를 비활성화한다
3. 리포트는 생성 시점의 규범 버전을 스냅샷으로 보존한다

### 10.2 개정 시 운영 워크플로우

```
1. 기존 레코드 비활성화
   UPDATE ethics_codes SET is_active=FALSE, effective_until=CURRENT_DATE
   WHERE code='개정_코드' AND is_active=TRUE;

2. 새 버전 INSERT (version = 이전+1, is_active=TRUE)

3. 이전 레코드의 superseded_by = 새 레코드 ID

4. 새 레코드 임베딩 생성

5. pattern_ethics_relations: 기존 관계를 새 버전으로 복제 (또는 재검토)

6. 검색 함수는 active_ethics_codes 뷰를 사용하므로 자동으로 최신만 검색
```

### 10.3 과거 리포트 처리 정책

- 과거 리포트는 수정하지 않고 "분석 시점 기준" 표시
- analysis_ethics_snapshot으로 시점 원문 보존 (Sonnet이 실제로 `<cite ref/>`로 인용한 규범만 저장. CitationResolver가 cite 태그를 파싱하는 시점에 해당 규범을 스냅샷 테이블에 함께 INSERT)
- 리포트 열람 시 인용 규범의 현행 버전과 비교, 차이 있으면 알림 배지 표시

---

## 11. 최소 실행 가능 평가(MVE) 체계

### 11.1 우선순위: Phase 0 병행 필수

eval 없이 출발하는 것은 가장 위험한 기술 부채.
threshold 조정, 임베딩 모델 비교, 프롬프트 수정의 효과를 측정할 기준이 없으면
"감에 의존한 개발"이 된다.

### 11.2 골든 데이터셋 구조 (20~30건)

| 필드 | 설명 |
|------|------|
| article_url | 테스트 기사 URL |
| article_key_text | 핵심 문단 텍스트 |
| expected_patterns | 반드시 탐지되어야 할 패턴 코드 목록 |
| expected_ethics_codes | 인용되어야 할 규범 코드 목록 |
| difficulty | easy / medium / hard |
| notes | 판단 근거 |

**데이터셋 구성**: 8개 대분류에서 각 3~4건씩 선정하여 다양성 확보.
복합 패턴(여러 패턴 동시 출현) 케이스를 포함.
**정상 기사(True Negative) 2~3건도 반드시 포함**: 언뜻 보면 문제 같지만 윤리규범상 허용되는 기사.
threshold 튜닝 시 오탐지(False Positive) 방지 기준으로 사용.

### 11.3 핵심 평가 메트릭

- **Recall@K**: 벡터 검색 상위 K개에 정답 패턴이 포함되는 비율
- **Pattern Precision**: Haiku가 확정한 패턴 중 정답과 일치하는 비율
- **Citation Accuracy**: 리포트의 규범 인용이 정답 규범과 일치하는 비율
- **Faithfulness**: 생성된 리포트가 컨텍스트에 충실한 정도

### 11.4 임베딩 모델 벤치마크

골든셋의 article_key_text를 쿼리로 사용하여,
OpenAI / Voyage AI / Upstage의 Recall@10을 비교.
결과에 따라 임베딩 모델을 최종 확정.

---

## 12. 구현 가이드라인

### 12.1 리포지토리 패턴 추상화

Supabase 직접 호출을 인터페이스로 감싸서, 향후 DB 마이그레이션 비용을 최소화.

```python
# 예시: 패턴 검색 인터페이스
class PatternRepository(ABC):
    @abstractmethod
    async def search_candidates(self, embedding, threshold, count) -> list: ...
    @abstractmethod
    async def get_ethics_for_patterns(self, pattern_ids) -> list: ...

class SupabasePatternRepository(PatternRepository):
    # Supabase 구현
    ...
```

### 12.2 RAG 모듈화

현재의 통짜 파이프라인을 독립 모듈로 분리:
- `EmbeddingGenerator` — 임베딩 생성 (모델 추상화)
- `PatternRetriever` — 벡터 검색
- `EthicsLookup` — 관계 테이블 조회 + parent chain 수집
- `ContextAssembler` — RAG 컨텍스트 조립
- `CitationResolver` — cite 태그를 원문으로 치환

각 모듈은 향후 LLM Tool Calling 스펙으로 노출 가능한 형태로 설계.

### 12.3 성능 최적화

**배치 임베딩**: 단락 배열을 한 번의 API 호출로 묶어 처리.
```python
# OpenAI 배치 API 예시
response = openai.embeddings.create(
    input=[chunk1, chunk2, chunk3],  # 배열로 한 번에
    model="text-embedding-3-small"
)
```

**비동기 처리**: 임베딩 생성을 `asyncio.gather`로 병렬화.
**스트리밍 응답**: Sonnet의 리포트 생성을 프론트엔드로 스트리밍.

예상 레이턴시: 스크래핑(1s) + 임베딩(1s) + DB검색(0.1s) + LLM생성(5~10s) ≈ 10~15초

---

## 13. 미결 사항

### 높은 우선순위 (구현 전 해결 필수)

| 항목 | 상태 | 설명 |
|------|------|------|
| 작업 A: 추가 규범 6개 원문 수집 | ✅ | 완료 (2026-03-19). 14개 규범 전부 수록, 원문 대조 교정 완료 |
| 작업 B: 규범 parent-child 매핑 | ✅ | 완료 (2026-03-23). 394개 코드, 교차검증 에러 0건. `ethics_codes_mapping.json` |
| 골든 데이터셋 구축 | ✅ | 완료 (2026-03-23). 26건 확정 (TP 20 + TN 6). `golden_dataset_final.json` |
| 레이블링 | ✅ | 완료 (2026-03-23). v3, weight 필드 포함. `golden_dataset_labels.json` |
| Data Leakage 점검 | ✅ | 완료 (2026-03-23). 26건 전부 CLEAN, 포털 전재본으로 해결 |
| 기사 원문 아카이빙 | ✅ | 완료 (2026-03-23). 26건 `article_texts/` 저장, URL Rot 대비 |
| 앙상블 검증 (DB 구축 사전 검수) | ✅ | 완료 (2026-03-25). 5AI 교차검증, 반영 4건·보류 4건·불채택 2건 |
| 기사 청킹 로직 프로토타이핑 | ⬜ | M3 벤치마크 전까지 검증 필수 (섹션 4 참조) |
| 임베딩 모델 벤치마크 | ⬜ | 골든셋 기반 Recall@10 비교 (Week 1 M3) |
| CR-Check GitHub 코드의 정적 매핑 구조 파악 | ⬜ | M4(RAG 파이프라인) 구현 시 처리 |

### 중간 우선순위

| 항목 | 설명 |
|------|------|
| 패턴 교차참조 확장 (Stage 1) | 임베딩 유사도 + LLM 추출 (섹션 9 참조) |
| 메타 패턴 추론 규칙 검증 | 골든셋으로 추론 정확도 확인 |

### 낮은 우선순위 (운영 단계)

| 항목 | 설명 |
|------|------|
| RAG eval 확장 | RAGAS 프레임워크 도입, 데이터셋 50건+ 확장 |
| 패턴/규범 업데이트 워크플로우 자동화 | 임베딩 재생성 자동화 |
| 패턴 공출현 마이닝 (Stage 2) | Phase 1 운영 3개월 후 |

### 작업 A 상세: 추가 규범 6개 원문 수집 ✅ (2026-03-19 완료)

**수집 URL**:

| 규범 | URL |
|------|-----|
| 자살예방 보도준칙 | journalist.or.kr/news/section4.html?p_num=12 |
| 재난보도준칙 | journalist.or.kr/news/section4.html?p_num=10 |
| 감염병보도준칙 | journalist.or.kr/news/section4.html?p_num=17 |
| 선거여론조사 보도준칙 | journalist.or.kr/news/section4.html?p_num=13 |
| 평화통일 보도 준칙 | journalist.or.kr/news/section4.html?p_num=14 |
| 혐오표현 반대 선언 | journalist.or.kr/news/section4.html?p_num=16 |

**절차**: 전문 수집 → Code of Ethics 파일에 동일 형식으로 추가 → 조항 수 재집계
**완료 기준**: 14개 규범 모두 수록, 각 조항이 개별 식별 가능 → ✅ 달성 (원문 대조 교정까지 완료)

### 작업 B 상세: 규범 parent-child 매핑

**절차**:
1. 모든 조항 목록화 (ID, 규범명, 조문번호, 제목)
2. 각 조항에 tier 부여 (섹션 5.1의 기준)
3. tier_rationale 작성 (경계 모호 케이스)
4. 주제별 구체화 체인: Tier 3/4 → Tier 2 parent → Tier 1 parent
5. domain 부여 (general, suicide, disaster, election 등)
6. locale 부여 (ko-KR)

**산출물**: `ethics_codes_mapping.json`

---

## 14. 실행 순서 및 타임라인

### 14.1 Phase 0 + 1 동시 진행

Supabase 프로젝트 생성 시 RAG 테이블 + 기본 테이블 + 버전관리 테이블을 한 번에 생성.
데이터 규모가 작아(~262개 엔티티) 스키마 전체 생성의 부담이 없음.

### 14.2 통합 타임라인

```
Week 0: 선행 작업 (Week 1 시작 전 완료 필수)
├─ 작업 A: 추가 규범 6개 원문 수집 → Code of Ethics 파일에 추가
├─ 작업 B: ~160개 조항 tier/parent 매핑 → ethics_codes_mapping.json 산출
└─ 기사 청킹 로직 프로토타이핑 (다양한 HTML 소스에서 전처리+병합 검증)

Week 1: 기반 구축
├─ Day 1: Supabase 프로젝트 생성, pgvector 활성화, 전체 스키마 생성
├─ Day 2: 패턴/규범 데이터 입력 + 임베딩 생성
├─ Day 3: 관계 데이터 구축 (시드 15건 + Stage 1 확장)
├─ Day 4: 골든 데이터셋 20~30건 구축 + 임베딩 모델 벤치마크
└─ Day 5: threshold 튜닝 + 하이브리드 검색 함수 구현

Week 2: Phase 0 완성 + Phase 1
├─ Day 6-7: 1.5회 RAG 파이프라인 구현 (패턴 후보→Haiku→규범 정밀조회→Sonnet)
├─ Day 8: 결정론적 인용 후처리 + 메타 패턴 추론 로직
├─ Day 9: Phase 1 — DatabaseManager + main.py 수정 (아카이빙 + 공개 URL)
└─ Day 10: Phase 1 — 통합 테스트 + 배포

Week 3: Phase 2
├─ Day 11-12: 통계 함수 + API
└─ Day 13-14: 대시보드 UI
```

예상 총 소요: 2~3주 (파트타임 기준)

### 14.3 작업-감수 루프 단위

실행은 Claude Code CLI, 1차 감리는 Claude.ai, 2차 더블체크는 Antigravity(Gemini).
마일스톤 단위로 감수 사이클을 진행:

| 마일스톤 | 작업 내용 | 감수 포인트 |
|----------|----------|------------|
| M1 | 스키마 생성 (전체 테이블 + 뷰 + 함수) | SQL 정합성, 컬럼 누락, 인덱스 |
| M2 | 시드 데이터 입력 (패턴 + 규범 + 관계) | 데이터 정확성, tier 분류, parent 매핑 |
| M3 | 임베딩 생성 + 벤치마크 | 모델 성능, Recall@K 결과 |
| M4 | RAG 파이프라인 (1.5회 호출 구현) | 흐름 정합성, 토큰 예산 |
| M5 | 결정론적 인용 + 메타 패턴 추론 | cite 태그 치환, 가드레일 |
| M6 | Phase 1 아카이빙 통합 | 엔드투엔드 테스트, 골든셋 평가 |

---

## 15. 확정된 기술 결정 요약

| 항목 | 결정 |
|------|------|
| RAG 방식 | Hybrid RAG (pgvector + 관계형 테이블) |
| 인프라 | Supabase 단일 플랫폼 (리포지토리 패턴으로 추상화) |
| 임베딩 모델 | OpenAI text-embedding-3-small 1차, 벤치마크 후 최종 확정 |
| 청킹 (패턴/규범) | 자연 구조 그대로 |
| 청킹 (기사) | 의미 기반 병합 청킹 (300~500자) + 노이즈 제거 |
| 검색 전략 | Top-K(10) + 느슨한 threshold(0.5), 환경변수 관리 |
| 관계 모델링 | 관계형 테이블 (Graph DB 불필요, 4-Hop 이상 시 재검토) |
| 규범 인용 방식 | 구체→포괄 롤업 + 결정론적 인용 (cite 태그) |
| RAG 호출 구조 | 1.5회: 벡터검색→Haiku(확정)→규범 정밀조회→Sonnet |
| 메타 패턴 추론 | 하이브리드 (규칙 사전필터 + LLM 판단 + 표현 가드레일) |
| 규범 버전 관리 | Immutable Records + 스냅샷 |
| Eval 체계 | Phase 0 병행, 골든셋 20~30건, Recall@K 기반 |
| Phase 실행 순서 | Phase 0 + 1 동시 진행 |
| 사용자 인증 | 없음 — 전 Phase 익명 운영, 공개 URL 공유 |
| 기존 스택 | FastAPI(BE) + Next.js(FE) + Railway/Vercel 유지 |

---

## 16. 기술 스택

| 레이어 | 기술 | 용도 |
|--------|------|------|
| Database | Supabase (PostgreSQL 15+) | 전체 데이터 저장 |
| Vector Search | pgvector + pgvectorscale | RAG 임베딩 검색 |
| Backend | FastAPI + supabase-py | API + DB 연동 |
| Frontend | Next.js 15 | UI |
| AI (분석) | Claude Haiku + Sonnet | 2단계 뉴스 분석 |
| AI (임베딩) | OpenAI text-embedding-3-small (벤치마크 후 확정) | 텍스트 임베딩 |
| 배포 | Railway (BE) + Vercel (FE) | 호스팅 |

---

## 17. 주요 파일 경로

### 활성 계획 문서 (docs/)
```
/Users/gamnamu/Documents/cr-check/docs/
├── DB_AND_RAG_MASTER_PLAN_v4.0.md    ← 본 문서 (Single Source of Truth)
├── DB_BUILD_EXECUTION_GUIDE.md        ← 실행 가이드 (Antigravity용)
├── Code of Ethics for the Press.md    ← 규범 원문 (14개 수록 완료, 1,097줄)
├── current-criteria_v2_active.md      ← 패턴 원문 (v2, 활성)
├── SESSION_CONTEXT_2026-03-19.md      ← 세션 컨텍스트
├── CR_CHECK_PERFORMANCE_AUDIT.md      ← 성능 감사
├── evaluatie-template.md              ← 평가 템플릿
├── scraping-lists.md                  ← 스크래핑 목록
├── [샘플]평가 리포트.html              ← 샘플 리포트
└── _archive_superseded/               ← 대체된 문서 + README
```

---

*이 문서는 CR-Check DB 구축 및 RAG 도입의 Single Source of Truth입니다.*
*Phase 1-2 상세 구현 코드: `_archive_superseded/DB_CONSTRUCTION_FINAL_PLAN.md`*
