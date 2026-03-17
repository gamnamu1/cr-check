# CR-Check DB 구축 실행 가이드

> **용도**: 안티그래비티(Antigravity)가 실행하고, Claude Code CLI가 감수하는 워크플로우
> **기반 문서**: `DB_AND_RAG_MASTER_PLAN_v4.0.md`
> **작성일**: 2026-03-15

---

## 0. 사전 준비 사항

### 0.1 Supabase 무료 티어 현황 (2026년 기준)

| 항목 | 무료 한도 | CR-Check 예상 사용량 |
|------|-----------|---------------------|
| DB 저장소 | 500 MB | ~50 MB (262개 엔티티 + 임베딩) |
| 대역폭(egress) | 2 GB/월 | 매우 낮음 (초기) |
| 프로젝트 수 | 2개 | 1개 |
| MAU | 50,000 | 초기 소수 |
| Edge Functions | 500K 호출/월 | 사용 안 함 (Phase 0) |

CR-Check의 데이터 규모(~262개 엔티티, ~50,000자)는 무료 티어로 완전히 충분.
단, **무료 프로젝트는 1주 미사용 시 자동 일시중지(pause)** 됨에 유의.
운영 단계에서는 Pro($25/월)로 전환 권장.

### 0.2 필요한 계정/키

| 서비스 | 용도 | 비용 |
|--------|------|------|
| Supabase 계정 | DB + pgvector + Auth | 무료 |
| OpenAI API 키 | 임베딩 생성 (text-embedding-3-small) | ~$0.01 (262개) |
| GitHub 계정 | 이미 있음 (cr-check 레포) | — |

---

## 1단계: Supabase 프로젝트 생성

### 1-1. 가입 및 프로젝트 생성

1. https://supabase.com 접속 → "Start your project" 클릭
2. GitHub 계정으로 로그인 (또는 이메일 가입)
3. Organization 생성 (이름: `cr-check` 또는 원하는 이름)
4. "New Project" 클릭
   - **Name**: `cr-check-db`
   - **Database Password**: 강력한 비밀번호 생성 → 반드시 별도 저장
   - **Region**: `Northeast Asia (Seoul)` — 한국 사용자 대상이므로 서울 리전 선택
   - **Pricing Plan**: Free tier
5. "Create new project" 클릭 → 2~3분 대기 (프로비저닝)

### 1-2. 핵심 정보 수집 (환경변수용)

프로젝트가 생성되면, 다음 정보를 `.env` 파일에 저장:

```
Project Settings > API 에서:
- SUPABASE_URL=https://[프로젝트ID].supabase.co
- SUPABASE_ANON_KEY=eyJ...  (공개 anon 키)
- SUPABASE_SERVICE_ROLE_KEY=eyJ...  (비공개 서비스 키, 백엔드 전용)

Project Settings > Database 에서:
- DATABASE_URL=postgresql://postgres:[비밀번호]@db.[프로젝트ID].supabase.co:5432/postgres
```

> ⚠️ `SERVICE_ROLE_KEY`는 절대 프론트엔드 코드에 노출하면 안 됨.
> 백엔드(FastAPI)에서만 사용.

### 1-3. pgvector 확장 활성화

**방법 A** — Dashboard UI:
1. 좌측 사이드바 > Database > Extensions
2. "vector" 검색 → Toggle ON

**방법 B** — SQL Editor:
1. 좌측 사이드바 > SQL Editor
2. 다음 SQL 실행:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 📋 감수 포인트 (1단계 완료 후)
- [ ] 프로젝트가 정상 생성되고 Dashboard 접근 가능한가?
- [ ] Region이 Seoul(ap-northeast-2)인가?
- [ ] pgvector 확장이 활성화되었는가? (`SELECT * FROM pg_extension WHERE extname = 'vector';` 로 확인)
- [ ] 4개 환경변수(URL, ANON_KEY, SERVICE_ROLE_KEY, DATABASE_URL)가 모두 수집되었는가?

---

## 2단계: 스키마 생성 (전체 테이블 한 번에)

### 2-1. SQL Editor에서 스키마 실행

Supabase Dashboard > SQL Editor에서 v4.0 문서 섹션 6.1의 SQL을 순서대로 실행.
한 번에 전부 붙여넣어도 되고, 테이블별로 나눠 실행해도 됨.

**실행 순서** (FK 의존성 고려):
1. `CREATE EXTENSION IF NOT EXISTS vector;` (이미 했으면 생략)
2. `patterns` 테이블
3. `ethics_codes` 테이블
4. `ethics_code_hierarchy` 테이블
5. `pattern_ethics_relations` 테이블
6. `pattern_relations` 테이블
7. `active_ethics_codes` 뷰
8. `ethics_codes_history` 뷰
9. `analysis_ethics_snapshot` 테이블 — 이 테이블은 `analysis_results`에 의존하므로,
   Phase 1의 `analysis_results` 테이블이 먼저 생성되어야 함.
   → Phase 1 스키마와 함께 생성하거나, 나중에 별도 생성.
10. `search_pattern_candidates()` 함수
11. `get_ethics_for_patterns()` 함수

### 2-2. Phase 1 기본 테이블도 동시 생성

`_archive_superseded/DB_CONSTRUCTION_FINAL_PLAN.md`의 섹션 1.1에서
Phase 1-2 테이블 SQL을 가져와 실행:
- `profiles` (auth.users 확장)
- `articles`
- `analysis_results`
- 트리거 함수 (profiles 자동 생성)

이후 `analysis_ethics_snapshot` 테이블도 생성 가능.

### 2-3. 스키마 검증 쿼리

모든 테이블 생성 후, 아래 쿼리로 확인:

```sql
-- 테이블 목록 확인
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 예상 결과: analysis_ethics_snapshot, analysis_results, articles,
-- ethics_code_hierarchy, ethics_codes, pattern_ethics_relations,
-- pattern_relations, patterns, profiles (+ bookmarks, feedbacks는 Phase 4)

-- 뷰 확인
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';
-- 예상: active_ethics_codes, ethics_codes_history

-- 함수 확인
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_type = 'FUNCTION';
-- 예상: search_pattern_candidates, get_ethics_for_patterns

-- pgvector 벡터 컬럼 확인
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE data_type = 'USER-DEFINED'
AND udt_name = 'vector';
-- 예상: patterns.description_embedding, ethics_codes.text_embedding
```

### 📋 감수 포인트 (2단계 완료 후)
- [ ] 모든 테이블이 생성되었는가? (위 검증 쿼리 결과 확인)
- [ ] 뷰 2개가 정상 동작하는가? (`SELECT * FROM active_ethics_codes LIMIT 1;`)
- [ ] 함수 2개가 존재하는가?
- [ ] vector(1536) 컬럼이 patterns, ethics_codes에 있는가?
- [ ] FK 관계가 올바른가? (Dashboard > Table Editor에서 시각적으로 확인)
- [ ] ethics_codes의 UNIQUE 제약이 (code, version)인가?

---

## 3단계: 시드 데이터 입력 (패턴 + 규범)

### 3-1. 패턴 데이터 입력

**출처**: `current-criteria_v2_active.md`의 ~102개 소분류

입력 방법 — Python 스크립트 권장:
```python
# seed_patterns.py (개념적 예시)
import json
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# criteria 파일을 파싱하여 패턴 목록 생성
patterns = parse_criteria_file("current-criteria_v2_active.md")

for p in patterns:
    supabase.table("patterns").insert({
        "code": p["code"],          # "1-1-1"
        "name": p["name"],          # "불분명한 출처 표기"
        "description": p["description"],
        "category": p["category"],   # "진실성"
        "subcategory": p["subcategory"],
        "is_meta_pattern": p["code"] in ["1-4-1", "1-4-2"],
        "hierarchy_level": 3,        # 소분류
        "locale": "ko-KR"
    }).execute()
```

> 안티그래비티는 criteria 파일의 구조를 이미 알고 있으므로,
> 파싱 로직을 적절히 구현해야 함.

### 3-2. 규범 데이터 입력

**출처**: `Code of Ethics for the Press.md` (14개 규범, 작업 A 완료 후)

**전제**: 작업 B(`ethics_codes_mapping.json`)가 완료되어
각 조항에 tier, tier_rationale, parent_code_id, domain이 부여된 상태여야 함.

```python
# seed_ethics.py (개념적 예시)
mapping = json.load(open("ethics_codes_mapping.json"))

for ec in mapping:
    supabase.table("ethics_codes").insert({
        "code": ec["code"],
        "title": ec["title"],
        "full_text": ec["full_text"],
        "source": ec["source"],
        "article_number": ec["article_number"],
        "tier": ec["tier"],
        "tier_rationale": ec.get("tier_rationale"),
        "parent_code_id": ec.get("parent_code_id"),
        "domain": ec["domain"],
        "locale": "ko-KR",
        "version": 1,
        "is_active": True,
        "effective_from": "2026-03-15"
    }).execute()
```

### 3-3. 관계 데이터 입력

**시드 데이터**: criteria 파일의 명시적 교차참조 15건 + Stage 1 확장분

```python
# seed_relations.py (개념적 예시)
# pattern_ethics_relations: 패턴→규범 매핑
# pattern_relations: 패턴→패턴 교차참조

relations = [
    # 예시: 교차참조 시드
    {"source": "1-7-1", "target": "1-2-2", "type": "variant_of",
     "description": "주관적 술어와 책임회피 표현", "source_method": "manual"},
    # ... 15건+
]
```

### 3-4. 데이터 검증 쿼리

```sql
-- 패턴 수 확인
SELECT COUNT(*) FROM patterns;
-- 예상: ~102

-- 규범 수 확인
SELECT COUNT(*) FROM ethics_codes WHERE is_active = TRUE;
-- 예상: ~160

-- Tier 분포 확인
SELECT tier, COUNT(*) FROM ethics_codes WHERE is_active = TRUE GROUP BY tier ORDER BY tier;
-- 예상: Tier 1: ~9, Tier 2: ~80, Tier 3: ~50, Tier 4: ~20 (대략)

-- 관계 수 확인
SELECT COUNT(*) FROM pattern_ethics_relations;
SELECT COUNT(*) FROM pattern_relations;

-- 메타 패턴 확인
SELECT code, name FROM patterns WHERE is_meta_pattern = TRUE;
-- 예상: 1-4-1, 1-4-2
```

### 📋 감수 포인트 (3단계 완료 후)
- [ ] 패턴 ~102개가 입력되었는가?
- [ ] 규범 ~160개가 입력되었는가? (14개 규범 문서 모두 포함)
- [ ] 각 규범의 tier가 올바른가? (경계 모호 케이스에 tier_rationale이 있는가?)
- [ ] parent_code_id 체인이 유효한가? (Tier 3 → Tier 2 → Tier 1 연결 확인)
- [ ] domain이 적절히 부여되었는가? (자살보도='suicide', 재난='disaster' 등)
- [ ] 메타 패턴 2개가 is_meta_pattern=TRUE로 설정되었는가?
- [ ] pattern_relations에 시드 15건+이 입력되었는가?

---

## 4단계: 임베딩 생성

### 4-1. OpenAI API 키 설정

`.env`에 추가:
```
OPENAI_API_KEY=sk-...
```

### 4-2. 임베딩 생성 스크립트

```python
# generate_embeddings.py (개념적 예시)
import openai
from supabase import create_client

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# 패턴 임베딩 (배치 처리)
patterns = supabase.table("patterns").select("id, description").execute()
texts = [p["description"] for p in patterns.data]

# 배치 API 1회 호출로 모든 패턴 임베딩 생성
response = openai_client.embeddings.create(
    input=texts,
    model="text-embedding-3-small"
)

for i, p in enumerate(patterns.data):
    supabase.table("patterns").update({
        "description_embedding": response.data[i].embedding
    }).eq("id", p["id"]).execute()

# 규범 임베딩 (동일 방식)
ethics = supabase.table("ethics_codes").select("id, full_text").eq("is_active", True).execute()
# ... (동일 패턴)
```

> 262개 임베딩 생성 비용: ~$0.01 미만
> 소요 시간: ~10초 (배치 1회)

### 4-3. 임베딩 검증

```sql
-- 임베딩이 NULL이 아닌 레코드 수
SELECT COUNT(*) FROM patterns WHERE description_embedding IS NOT NULL;
-- 예상: 102 (메타 패턴 포함 전체)

SELECT COUNT(*) FROM ethics_codes
WHERE text_embedding IS NOT NULL AND is_active = TRUE;
-- 예상: ~160
```

### 📋 감수 포인트 (4단계 완료 후)
- [ ] 모든 패턴에 임베딩이 생성되었는가? (NULL 레코드 0건)
- [ ] 모든 활성 규범에 임베딩이 생성되었는가?
- [ ] 임베딩 차원이 1536인가? (`SELECT vector_dims(description_embedding) FROM patterns LIMIT 1;`)
- [ ] 간단한 유사도 테스트가 작동하는가? (아래 쿼리)

```sql
-- 간단 유사도 테스트: 특정 패턴과 가장 유사한 패턴 5개
SELECT code, name, 1 - (description_embedding <=> (
    SELECT description_embedding FROM patterns WHERE code = '1-1-1'
)) as similarity
FROM patterns
WHERE code != '1-1-1'
ORDER BY similarity DESC LIMIT 5;
```

---

## 5단계: 골든 데이터셋 구축 + 벤치마크

### 5-1. 골든 데이터셋 20~30건 수동 선정

8개 대분류에서 각 3~4건의 실제 기사를 선정.
각 기사에 대해 "이 기사에서 반드시 탐지되어야 할 패턴"을 사람이 판단.

```json
// golden_dataset.json 구조 예시
[
  {
    "id": "GD-001",
    "article_url": "https://example.com/news/12345",
    "article_key_text": "정부 고위 관계자에 따르면...(기사 핵심 문단)",
    "expected_patterns": ["1-1-1", "1-2-1"],
    "expected_ethics_codes": ["KJA-3", "PCC-7.2"],
    "difficulty": "easy",
    "category": "진실성",
    "notes": "익명 단일 취재원, 반론 없음"
  },
  ...
]
```

### 5-2. 임베딩 모델 벤치마크 (선택적)

골든셋의 article_key_text를 쿼리로,
`search_pattern_candidates()` 함수의 결과에 expected_patterns가 포함되는지 측정.

```python
# benchmark.py (개념적 예시)
for case in golden_dataset:
    embedding = generate_embedding(case["article_key_text"])
    results = supabase.rpc("search_pattern_candidates", {
        "query_embedding": embedding,
        "match_threshold": 0.5,
        "match_count": 10
    }).execute()

    found_codes = {r["pattern_code"] for r in results.data}
    expected = set(case["expected_patterns"])
    recall = len(found_codes & expected) / len(expected)
    # ... 집계
```

### 5-3. threshold 튜닝

벤치마크 결과를 보고 threshold를 조정:
- Recall이 낮으면 → threshold를 낮춤 (0.5 → 0.4)
- 노이즈가 많으면 → threshold를 높이거나 match_count를 줄임

### 📋 감수 포인트 (5단계 완료 후)
- [ ] 골든 데이터셋 20~30건이 구축되었는가?
- [ ] 8개 대분류에서 골고루 선정되었는가?
- [ ] Recall@10이 80% 이상인가? (기준선)
- [ ] threshold 값이 결정되었는가?
- [ ] 임베딩 모델이 최종 확정되었는가? (OpenAI 유지 또는 대안 전환)

---

## 6단계: FastAPI 백엔드에 Supabase 연결

### 6-1. Python 패키지 설치

```bash
pip install supabase openai
```

### 6-2. 환경변수 설정

기존 cr-check 백엔드의 `.env`에 추가:
```
SUPABASE_URL=https://[프로젝트ID].supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
OPENAI_API_KEY=sk-...
```

### 6-3. RAG 모듈 구현

v4.0 섹션 12.2의 모듈 구조에 따라:
- `backend/rag/embedding_generator.py`
- `backend/rag/pattern_retriever.py`
- `backend/rag/ethics_lookup.py`
- `backend/rag/context_assembler.py`
- `backend/rag/citation_resolver.py`

각 모듈은 리포지토리 패턴(v4.0 섹션 12.1)으로 추상화.

### 6-4. 1.5회 호출 파이프라인 연결

v4.0 섹션 7.2의 흐름에 따라 `main.py`의 분석 엔드포인트를 수정:
1. 기사 스크래핑 → 전처리 → 의미 기반 청킹
2. 배치 임베딩 → `search_pattern_candidates()` 호출
3. Haiku에 패턴 후보 전달 → 확정 결과 수신
4. `get_ethics_for_patterns()` → 규범 정밀 조회
5. Sonnet에 확정 패턴 + 규범 컨텍스트 전달 (결정론적 인용)
6. 후처리: cite 태그 → DB 원문 치환
7. 결과 저장 (analysis_results + analysis_ethics_snapshot)

### 📋 감수 포인트 (6단계 완료 후)
- [ ] Supabase 연결이 정상 동작하는가? (간단한 SELECT 테스트)
- [ ] RAG 모듈들이 독립적으로 테스트 가능한가?
- [ ] 1.5회 호출 파이프라인이 엔드투엔드로 작동하는가?
- [ ] 결정론적 인용이 정상 동작하는가? (cite 태그 → 원문 치환)
- [ ] 골든셋으로 파이프라인 전체 Recall/Precision 측정 결과는?
- [ ] 분석 결과가 analysis_results에 저장되는가?
- [ ] analysis_ethics_snapshot에 규범 스냅샷이 저장되는가?

---

## 전체 마일스톤 요약

| 마일스톤 | 작업 | 안티그래비티 | Claude Code CLI 감수 | 선행 조건 |
|----------|------|:-----------:|:-------------------:|-----------|
| **M0** | 작업 A: 추가 규범 6개 수집 | ✅ 실행 | ✅ 감수 | — |
| **M0.5** | 작업 B: tier/parent 매핑 | ✅ 실행 | ✅ 감수 | M0 완료 |
| **M1** | 1단계: Supabase 생성 + pgvector | ✅ 실행 | ✅ 감수 | — |
| **M2** | 2단계: 전체 스키마 생성 | ✅ 실행 | ✅ 감수 | M1 |
| **M3** | 3단계: 시드 데이터 입력 | ✅ 실행 | ✅ 감수 | M0.5 + M2 |
| **M4** | 4단계: 임베딩 생성 | ✅ 실행 | ✅ 감수 | M3 |
| **M5** | 5단계: 골든셋 + 벤치마크 | 함께 | ✅ 감수 | M4 |
| **M6** | 6단계: FastAPI 연결 + 파이프라인 | ✅ 실행 | ✅ 감수 | M5 |

### 병렬 가능한 작업

```
[병렬 트랙 A] M0 → M0.5 (규범 수집 → 매핑)
[병렬 트랙 B] M1 → M2 (Supabase 생성 → 스키마)

트랙 A + B 합류 → M3 (시드 데이터) → M4 (임베딩) → M5 (골든셋) → M6 (파이프라인)
```

M0(규범 수집)과 M1(Supabase 생성)은 독립적이므로 동시에 진행 가능.
M3(시드 데이터 입력)이 양쪽 모두 필요로 하는 합류 지점.

---

## 안티그래비티에게 전달할 자료 목록

1. **`DB_AND_RAG_MASTER_PLAN_v4.0.md`** — 전체 설계의 Single Source of Truth
2. **`DB_BUILD_EXECUTION_GUIDE.md`** — 이 문서 (단계별 실행 가이드)
3. **`Code of Ethics for the Press.md`** — 규범 원문 (작업 A에서 추가 후)
4. **`current-criteria_v2_active.md`** — 패턴 원문
5. **`ethics_codes_mapping.json`** — 작업 B 산출물 (tier/parent 매핑)
6. **`_archive_superseded/DB_CONSTRUCTION_FINAL_PLAN.md`** — Phase 1-3 상세 코드 참조

---

## 주의사항

1. **무료 티어 일시중지**: 1주 미사용 시 자동 pause. 개발 기간 중 주기적으로 접속하거나,
   간단한 cron job(예: 매일 1회 health check API 호출)으로 방지.
2. **SERVICE_ROLE_KEY 보안**: 이 키는 RLS(Row Level Security)를 우회하므로
   절대 프론트엔드에 노출 금지. 백엔드 `.env`에만 저장.
3. **RLS 정책**: Phase 2(사용자 인증) 이전까지는 RLS를 비활성화하거나
   permissive 정책으로 설정. Phase 2에서 적절한 정책으로 전환.
4. **백업**: 무료 티어는 자동 백업이 없음. 중요한 시드 데이터 입력 전후로
   SQL Export(Dashboard > Database > Backups)를 수동으로 수행.

---

*이 문서는 `DB_AND_RAG_MASTER_PLAN_v4.0.md`의 실행 가이드입니다.*
*설계 근거와 아키텍처 결정은 v4.0을 참조하세요.*
