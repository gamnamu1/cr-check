# CR-Check DB 구축 Week 1 M3 — 임베딩 생성 + 벤치마크 플레이북

> 작성일: 2026-03-28  
> 목적: M3(Day 3) 작업의 삼각편대 운영 절차를 STEP 단위로 정리  
> 역할: Claude Code CLI(코딩) → Claude.ai(1차 감리) → 마누스(2차 독립 감리) → Gamnamu(승인)  
> 선행 완료: M1(스키마, STEP 1-10) + M2(시드 데이터, STEP 11-18) ✅

---

## 공통 원칙 (M1/M2에서 계승)

- **Claude Code CLI 세션 시작 시 반드시**: `/effort high` 설정 → Plan Mode로 문서 숙지 후 Normal Mode 전환
- **컨텍스트 관리**: 50%에서 `/compact` 선제 실행. 변경 전 `/diff`로 사전 확인
- **쓰기 작업은 반드시 Migration 파일로만**. MCP는 읽기 전용 조회 전용
- **KJA 접두어 절대 사용 금지** → JCE가 올바른 접두어
- **OpenAI API 키**: 환경변수 `OPENAI_API_KEY`로 관리. 코드에 하드코딩 금지

---

## M3 작업 개요

| 항목 | 내용 |
|------|------|
| **목표** | 패턴+규범 임베딩 생성 → DB 적재 → 골든 데이터셋 기반 Recall@10 벤치마크 |
| **임베딩 모델** | OpenAI `text-embedding-3-small` (1536차원, 1차 선택) |
| **임베딩 대상** | 패턴 30개(비메타) + 규범 373개(is_citable=TRUE) = 총 403개 |
| **벤치마크 기준** | Recall@10 ≥ 80% (마스터 플랜 섹션 11.3) |
| **비용 추정** | ~$0.01 (403개 텍스트, text-embedding-3-small 요금) |

### M3 핵심 의사결정 분기점

```
Recall@10 ≥ 80%  → 임베딩 모델 확정, threshold 미세조정 후 M4 진행
Recall@10 60~80% → threshold 0.4로 하향 조정 후 재측정
                   → 여전히 미달 시 대안 모델(Voyage AI, Upstage) 테스트
Recall@10 < 60%  → 패턴 38개 → 119개 세분화 검토 + 대안 모델 병렬 테스트
```


---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase A: 임베딩 생성 스크립트 작성 + 감리
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 19. Claude Code CLI — 세션 시작 + 임베딩 생성 스크립트 작성

**[시점]** Day 3 시작. cr-check 프로젝트 디렉토리에서 Claude Code CLI 실행.

**[프롬프트 — Claude Code CLI에게]**

```
/effort high

M1(스키마) + M2(시드 데이터)가 모두 완료된 상태다.
지금부터 M3(임베딩 생성 + 벤치마크) 작업을 시작한다.

■ 사전 숙지 (Plan Mode로 먼저 읽을 것)
1. docs/SESSION_CONTEXT (최신 버전) — M3 핵심 체크포인트 섹션
2. docs/DB_AND_RAG_MASTER_PLAN_v4.0.md — 섹션 4(청킹 전략), 섹션 11(MVE), 섹션 15(기술 결정)
3. CLAUDE.md

■ 작업 내용: 임베딩 생성 스크립트 작성
scripts/generate_embeddings.py를 생성하라.

■ 핵심 요구사항

1. **임베딩 대상 선별**:
   - patterns 테이블: is_meta_pattern = FALSE인 패턴만 (30개)
   - ethics_codes 테이블: is_citable = TRUE AND is_active = TRUE인 규범만 (373개)
   - 총 403개 텍스트

2. **초단문 엔트리 처리 (필수)**:
   - full_text가 30자 미만인 엔트리 26건이 존재
   - 이들은 title + " — " + full_text 형식으로 결합한 텍스트를 임베딩
   - 30자 이상인 엔트리는 full_text만 사용 (patterns는 description)
   - 스크립트 실행 시 초단문 처리 대상 목록을 콘솔에 출력할 것

3. **OpenAI 배치 API 사용**:
   - 모델: text-embedding-3-small (1536차원)
   - 배열로 한 번에 전달 (API 1-2회 호출로 처리)
   - API 키는 환경변수 OPENAI_API_KEY에서 읽기
   - 비용 추정 출력 (~$0.01)

4. **DB UPDATE 쿼리**:
   - patterns → description_embedding 컬럼 UPDATE
   - ethics_codes → text_embedding 컬럼 UPDATE
   - Supabase Python 클라이언트(supabase-py) 또는 직접 SQL 실행
   - 로컬 Docker DB 대상 (postgresql://postgres:postgres@127.0.0.1:54322/postgres)

5. **검증 로직 포함**:
   - UPDATE 전후 NULL이 아닌 임베딩 수 카운트
   - 임베딩 차원 검증 (1536차원 확인)
   - 실패한 엔트리가 있으면 목록 출력

6. **에러 핸들링**:
   - OpenAI API 호출 실패 시 3회 재시도 (exponential backoff)
   - partial failure 시 성공분만 UPDATE하고 실패 목록 보고

■ 작업 완료 후
- 생성된 스크립트 전체 코드 출력
- 임베딩 대상 요약: patterns N개, ethics_codes N개, 초단문 처리 N건
- 필요한 pip 패키지 목록
- 자체 점검: 403개 전부 처리되는지 로직 확인

코드 작성 전에 Plan Mode에서 문서를 읽고, 작업 계획을 보여줘라.
```

**[체크포인트]** Plan을 검토. 특히 초단문 처리 로직과 DB 연결 방식 확인 후 "진행해" 승인.

---

### STEP 20. Claude.ai — 임베딩 스크립트 1차 감리

**[시점]** Claude Code CLI가 스크립트 작성을 완료한 직후.

**[프롬프트 — Claude.ai에게]**

```
CR-Check DB 구축 M3(임베딩 생성) 1차 감리를 요청한다.

Claude Code CLI가 작성한 임베딩 생성 스크립트이다.

---
[여기에 scripts/generate_embeddings.py 전문 붙여넣기]
---

■ 감리 체크리스트 (모든 항목에 대해 ✅/❌ 판정)

[A] 임베딩 대상 정합성
- [ ] patterns에서 is_meta_pattern = FALSE만 선별하는가 (30개 예상)
- [ ] ethics_codes에서 is_citable = TRUE AND is_active = TRUE만 선별하는가 (373개 예상)
- [ ] 총 대상이 403개인가

[B] 초단문 처리 로직
- [ ] 30자 미만 판별 기준이 full_text 길이 기반인가
- [ ] 결합 형식이 title + " — " + full_text인가
- [ ] 30자 이상은 full_text(규범) / description(패턴)만 사용하는가
- [ ] 초단문 대상 목록을 콘솔에 출력하는가

[C] OpenAI API 호출
- [ ] 모델명이 text-embedding-3-small인가
- [ ] 배치 API(배열 입력)를 사용하는가
- [ ] API 키를 환경변수에서 읽는가 (하드코딩 없음)
- [ ] 에러 핸들링: 3회 재시도 + exponential backoff가 있는가

[D] DB UPDATE 정확성
- [ ] patterns → description_embedding 컬럼에 UPDATE하는가
- [ ] ethics_codes → text_embedding 컬럼에 UPDATE하는가
- [ ] 임베딩 벡터를 올바른 형식(vector(1536))으로 변환하는가
- [ ] 각 임베딩이 올바른 레코드(id 매칭)에 UPDATE되는가

[E] 검증 로직
- [ ] UPDATE 전후 NULL이 아닌 임베딩 수를 카운트하는가
- [ ] 1536차원을 검증하는가
- [ ] 실패 건을 식별하고 보고하는가

[F] 구조적 안전성
- [ ] partial failure 시 성공분만 UPDATE하는 로직인가
- [ ] 스크립트가 idempotent한가 (재실행 시 문제 없음)
- [ ] 불필요한 데이터를 외부로 전송하지 않는가

각 항목에 ✅/❌ 판정과 근거를 제시해줘.
종합 판정(승인/조건부 승인/반려)과 이유를 명시해줘.
```

---

### STEP 21. 마누스 — 임베딩 스크립트 2차 독립 감리

**[시점]** Claude.ai 감리 완료 직후. 마누스 채팅으로 이동.

**[프롬프트 — 마누스에게]**

```
CR-Check DB 구축 M3(임베딩 생성)의 2차 독립 감리를 요청한다.

Claude Code CLI가 작성한 임베딩 생성 스크립트를 비-Anthropic 관점에서 리뷰해줘.

■ 스크립트 전문:
---
[여기에 scripts/generate_embeddings.py 전문 붙여넣기]
---

■ 배경 정보:
- DB에 patterns 38개(메타 패턴 2개 + 소분류 30개 + 대분류 8개 중 is_meta=FALSE 30개)
- ethics_codes 394개(is_citable=TRUE 373개)
- 초단문 엔트리(full_text 30자 미만) 26건 존재
- 임베딩 모델: OpenAI text-embedding-3-small (1536차원)

■ 감리 포인트 (Claude.ai와 다른 관점에서)

1. Python 코드 품질: 타입 힌팅, 예외 처리, 로깅이 적절한가?
2. OpenAI API 호출 패턴: rate limit 대응, 배치 크기 최적화는?
3. 초단문 처리의 30자 기준: 임베딩 품질에 영향이 있을 수 있는 더 나은 기준이 있는가?
4. DB 연결 방식: connection pool, timeout 설정이 적절한가?
5. 임베딩 벡터의 DB 저장 형식: pgvector의 vector 타입과 호환되는가?
6. Claude.ai 1차 감리에서 놓쳤을 수 있는 보안/성능 문제가 있는가?
7. text-embedding-3-small 외 대안 모델(Voyage AI, Upstage)로 
   교체 가능한 추상화가 되어 있는가?

종합 판정(승인/조건부 승인/반려)과 함께 보고해줘.
```

---

### STEP 22. Gamnamu — 감리 결과 비교 및 최종 판단

**[시점]** Claude.ai + 마누스 양쪽 감리가 모두 완료된 후.

**[판단 기준]**
- 양쪽 모두 "승인" → STEP 23으로 진행
- 한쪽이라도 "반려" → 수정 사항을 정리하여 STEP 22-1로
- "조건부 승인" → 조건 항목을 검토하여 수정 필요 여부 판단

### STEP 22-1. (조건부) Claude Code CLI — 스크립트 수정

**[시점]** 감리에서 수정 사항이 발견된 경우에만.

**[프롬프트 — Claude Code CLI에게]**

```
M3 임베딩 생성 스크립트에 대해 1차·2차 감리 결과 수정이 필요하다.

■ 수정 사항:
[감리에서 지적된 구체적 항목들을 나열]

scripts/generate_embeddings.py를 수정하고, 수정 전후 diff를 보여줘.
수정 완료 후 자체 점검을 다시 수행하라.
```

**[체크포인트]** 수정이 경미하면 바로 STEP 23. 중대하면 STEP 20-21 감리 루프 재진행.


---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase B: 임베딩 실행 + DB 적재 + 검증
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 23. Claude Code CLI — 임베딩 생성 실행 + DB UPDATE + 로컬 검증

**[시점]** STEP 22의 감리 승인 완료 후.

**[프롬프트 — Claude Code CLI에게]**

```
M3 임베딩 생성 스크립트 감리가 승인되었다. 실행하라.

■ 사전 확인
1. Docker가 실행 중인지 확인 (supabase start가 되어 있는지)
2. OPENAI_API_KEY 환경변수가 설정되어 있는지 확인
3. 필요한 pip 패키지 설치 (openai, supabase, psycopg2-binary 등)

■ 실행
python scripts/generate_embeddings.py

■ 실행 후 검증 (반드시 수행)
1. 패턴 임베딩 적재 확인:
   SELECT count(*) FROM patterns WHERE description_embedding IS NOT NULL;
   → 30개 예상

2. 규범 임베딩 적재 확인:
   SELECT count(*) FROM ethics_codes WHERE text_embedding IS NOT NULL;
   → 373개 예상

3. 임베딩 차원 검증:
   SELECT id, code, vector_dims(description_embedding) 
   FROM patterns 
   WHERE description_embedding IS NOT NULL 
   LIMIT 5;
   → 모두 1536이어야 함

4. 초단문 처리 확인 — 대표 1건의 임베딩이 NULL이 아닌지:
   SELECT id, code, title, length(full_text), 
          (text_embedding IS NOT NULL) as has_embedding
   FROM ethics_codes 
   WHERE length(full_text) < 30 
   LIMIT 5;

5. 메타 패턴 제외 확인:
   SELECT id, code, is_meta_pattern, 
          (description_embedding IS NOT NULL) as has_embedding
   FROM patterns 
   WHERE is_meta_pattern = TRUE;
   → 임베딩이 NULL이어야 함

6. is_citable = FALSE 제외 확인:
   SELECT id, code, is_citable, 
          (text_embedding IS NOT NULL) as has_embedding
   FROM ethics_codes 
   WHERE is_citable = FALSE 
   LIMIT 5;
   → 임베딩이 NULL이어야 함

전체 검증 결과를 요약 보고하라.
```

**[체크포인트]** 검증 결과에서 이상이 있으면 원인 파악 후 재실행. 정상이면 STEP 24로.

---

### STEP 24. 마누스 (MCP) — 임베딩 적재 확인

**[시점]** STEP 23 검증 성공 후.

**[프롬프트 — 마누스에게]**

```
M3 임베딩이 로컬 DB에 적재되었다.
MCP(읽기 전용)로 다음을 확인해줘:

1. patterns 테이블에서 description_embedding IS NOT NULL인 건수
   → 30건 예상

2. ethics_codes 테이블에서 text_embedding IS NOT NULL인 건수
   → 373건 예상

3. 메타 패턴(is_meta_pattern = TRUE)에 임베딩이 없는지 확인

4. is_citable = FALSE인 규범에 임베딩이 없는지 확인

5. 무작위 3개 패턴의 임베딩 차원(vector_dims) 확인

결과를 보고해줘.
```

**[체크포인트]** 마누스 보고에 이상이 없는지 확인. 이상 없으면 Phase C로.


---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase C: 벤치마크 (Recall@10 측정)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 25. Claude Code CLI — 벤치마크 스크립트 작성 + 실행

**[시점]** Phase B 완료 후.

**[프롬프트 — Claude Code CLI에게]**

```
임베딩 적재가 완료되었다. 이제 Recall@10 벤치마크를 수행하라.

■ 사전 숙지
1. docs/golden_dataset_labels.json — 26건의 expected_patterns 확인
2. Golden_Data_Set_Pool/article_texts/ — 26건 기사 원문 경로
3. docs/DB_AND_RAG_MASTER_PLAN_v4.0.md — 섹션 11.3(핵심 평가 메트릭)

■ 작업 내용: scripts/benchmark_recall.py 작성 + 실행

■ 벤치마크 절차

1. **쿼리 생성**:
   - 골든 데이터셋 26건의 article_key_text를 읽어들이기
   - 각 article_key_text를 OpenAI text-embedding-3-small로 임베딩
   - (article_key_text가 없는 경우 article_texts/ 폴더의 원문 사용)

2. **검색 실행**:
   - 각 쿼리 임베딩으로 search_pattern_candidates(embedding, 0.5, 10) RPC 호출
   - threshold = 0.5 (기본값), match_count = 10

3. **Recall@10 계산**:
   - golden_dataset_labels.json에서 expected_patterns 추출
   - 반환된 상위 10개 패턴 중 expected_patterns가 몇 개 포함되는지 계산
   - Recall@10 = (반환 결과 ∩ 정답) / 정답 수
   - True Negative 6건(C-02, C-04, C2-01, C2-07, E-17, E-19)은 
     expected_patterns가 빈 목록이므로, 반환 결과가 0건이면 정답으로 처리

4. **출력 형식**:

   === CR-Check Recall@10 벤치마크 결과 ===
   
   [건별 결과]
   | # | Article ID | Expected | Retrieved | Hit | Recall |
   |---|-----------|----------|-----------|-----|--------|
   | 1 | A-01      | 1-1-1    | 1-1-1, ...| ✅  | 1.00   |
   | 2 | A-06      | 1-1-2    | 1-3-1, ...| ❌  | 0.00   |
   ...
   
   [대분류별 Recall]
   | 대분류 | 건수 | 평균 Recall@10 |
   |--------|------|---------------|
   | 1-1 진실성 | 3건 | 0.89 |
   ...
   
   [전체 요약]
   - 전체 평균 Recall@10: X.XX
   - threshold: 0.5
   - 목표: ≥ 0.80
   - 판정: PASS / FAIL
   
   [상세 분석 — Recall이 낮은 건]
   (Recall < 0.5인 건에 대해 반환된 패턴 목록과 유사도 점수 출력)

5. **threshold 변형 테스트** (자동 실행):
   - threshold 0.3, 0.4, 0.5, 0.6으로 각각 Recall@10 측정
   - 4가지 threshold 비교표 출력

■ 작업 완료 후
- 벤치마크 결과 전문 출력
- scripts/benchmark_recall.py 코드 출력
- 결과를 docs/M3_BENCHMARK_RESULTS.md로 저장
```

**[체크포인트]** 스크립트 작성 완료 확인 후, 실행 결과를 기다림.

---

### STEP 26. Claude.ai — Recall@10 결과 리뷰 + threshold 판단

**[시점]** STEP 25의 벤치마크 실행이 완료된 직후.

**[프롬프트 — Claude.ai에게]**

```
CR-Check M3 벤치마크 결과를 리뷰해줘.

■ 벤치마크 결과:
---
[여기에 STEP 25의 벤치마크 결과 전문 붙여넣기]
---

■ 리뷰 체크리스트

[A] 전체 성능 판단
- [ ] 전체 평균 Recall@10이 ≥ 80%인가
- [ ] True Negative 6건이 올바르게 처리되었는가 (반환 0건 = 정답)
- [ ] 대분류별로 Recall이 고르게 분포되어 있는가

[B] 실패 케이스 분석
- [ ] Recall이 낮은 건이 있는가? 원인은 무엇으로 추정되는가?
  · 패턴 설명 텍스트가 너무 짧아서?
  · 기사 텍스트와 패턴 설명의 어휘 도메인 갭?
  · threshold가 너무 높아서 후보가 잘림?
  · 패턴 38개 세분화가 필요한 케이스?
- [ ] 실패 건에 대한 개선 제안을 구체적으로 제시할 수 있는가

[C] threshold 최적화
- [ ] 4가지 threshold(0.3, 0.4, 0.5, 0.6) 비교에서 최적값은?
- [ ] threshold를 낮추면 Recall은 오르지만 노이즈도 늘어남 — 
      Haiku가 필터 역할을 하므로 느슨한 threshold가 유리한가?
- [ ] 최종 threshold 추천값과 근거

[D] 모델 교체 필요성 판단
- [ ] text-embedding-3-small로 충분한가?
- [ ] 한국어 특화 모델(Upstage, BAAI bge-m3)이 필요해 보이는가?
- [ ] 법률/규범 문체와 뉴스 문체 간 도메인 갭이 심각한가?

[E] 패턴 세분화 필요성 판단
- [ ] 현재 38개 패턴(대분류 8 + 소분류 30)으로 충분한가?
- [ ] 119개 세분화(소분류 내 bullet point)가 Recall 개선에 도움이 될 것인가?
- [ ] 세분화가 필요한 특정 대분류가 있는가?

종합 의견:
- 모델 확정 가능 여부
- threshold 추천값
- 패턴 세분화 필요 여부
- M4 진행 가능 여부

을 명시해줘.
```

---

### STEP 27. Gamnamu — 벤치마크 결과 최종 판단 (분기점)

**[시점]** STEP 26의 Claude.ai 리뷰 완료 후.

**[판단 기준 — 분기점]**

```
경로 A: Recall@10 ≥ 80% (어떤 threshold에서든)
→ 임베딩 모델 + 최적 threshold 확정
→ STEP 29 배포로 진행

경로 B: Recall@10 60~80% (threshold 0.4 이하에서)
→ STEP 28로 이동: threshold 미세조정 + 초단문 처리 개선
→ 개선 후 재측정하여 80% 도달 시 STEP 29로
→ 여전히 미달 시 경로 C로

경로 C: Recall@10 < 60% (또는 경로 B에서 개선 안 됨)
→ STEP 28로 이동: 대안 모델(Voyage AI voyage-3, Upstage solar-embedding-1-large) 테스트
→ 대안 모델로도 미달 시 패턴 38개 → 119개 세분화 검토
→ 세분화는 M2 시드 데이터 재작업이 필요하므로 별도 플랜 수립
```

**[Gamnamu 직접 수행]**
1. Claude.ai의 종합 의견을 읽고 판단
2. 결과가 경계선(75~80%)이면, Claude.ai와 마누스에게 각각 의견을 구해 교차 확인
3. 경로 결정 후 해당 STEP으로 이동


---

### STEP 28. (조건부) Claude Code CLI — threshold 조정 / 대안 모델 테스트 / 패턴 세분화

**[시점]** STEP 27에서 경로 B 또는 C를 선택한 경우에만.

#### STEP 28-A. threshold 미세조정 (경로 B)

**[프롬프트 — Claude Code CLI에게]**

```
M3 벤치마크에서 Recall@10이 목표(80%)에 미달했다.
threshold를 조정하여 재측정하라.

1. threshold 0.3으로 Recall@10 재측정
2. threshold 0.35로 Recall@10 재측정
3. Recall이 가장 높은 threshold에서의 반환 패턴 수 평균도 함께 보고
   (너무 많은 후보가 반환되면 Haiku에 부담)
4. 결과를 docs/M3_BENCHMARK_RESULTS.md에 추가 기록
```

#### STEP 28-B. 대안 모델 테스트 (경로 C)

**[프롬프트 — Claude Code CLI에게]**

```
M3 벤치마크에서 text-embedding-3-small의 Recall이 부족하다.
대안 모델을 테스트하라.

■ 테스트 대상 (우선순위 순):
1. OpenAI text-embedding-3-large (3072차원) — 같은 API로 즉시 테스트 가능
2. Voyage AI voyage-3 — API 키 필요, 별도 가입
3. Upstage solar-embedding-1-large — API 키 필요, 별도 가입

■ 작업 내용
1. text-embedding-3-large로 403개 임베딩 재생성 (차원: 3072)
   ⚠️ DB의 vector(1536) 컬럼 크기 변경 필요 — Migration 파일로 ALTER
2. 같은 벤치마크 스크립트로 Recall@10 재측정
3. text-embedding-3-small vs large 비교표 출력
4. large 모델이 80%를 넘기면 확정. 아니면 Voyage AI 테스트로 진행.

■ 주의사항
- vector 차원 변경은 Migration으로만. MCP 쓰기 금지.
- 기존 임베딩 데이터는 새 모델로 덮어씀 (idempotent)
- 결과를 docs/M3_BENCHMARK_RESULTS.md에 추가 기록
```

#### STEP 28-C. 패턴 세분화 검토 (모든 모델 실패 시)

**[Gamnamu 판단]**
- 38개 패턴 → 119개 세분화는 M2 시드 데이터 재작업이 필요
- 이 결정은 비용이 크므로, Claude.ai + 마누스에게 각각 의견을 구한 후 판단
- 세분화 결정 시 별도 "M2.5 세분화 플레이북"을 작성

**[프롬프트 — Claude.ai + 마누스 각각에게]**

```
M3 벤치마크에서 모든 임베딩 모델이 Recall@10 80%에 미달했다.

현재 patterns 테이블은 38개(대분류 8 + 소분류 30)이다.
current-criteria_v2_active.md의 119개(소분류 내 bullet point까지)로 
세분화하면 Recall이 개선될 가능성이 있는가?

■ 판단 근거로 고려할 점:
1. 현재 실패 케이스들의 패턴 — 소분류 레벨의 설명이 너무 포괄적이어서 
   기사의 구체적 문장과 유사도가 낮은 것인가?
2. 119개로 세분화하면 각 패턴 설명이 더 구체적이 되어 유사도가 높아지는가?
3. 119개로 늘리면 유사한 패턴 간 혼동(False Positive)이 증가하지 않는가?
4. 비용: M2 시드 재작업 + 임베딩 재생성 + 벤치마크 재측정

세분화 찬/반 의견과 근거를 제시해줘.
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase D: 배포 + 마무리
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 29. Claude Code CLI — 클라우드 배포

**[시점]** 벤치마크 PASS 확정 후 (STEP 27 경로 A 또는 STEP 28 후 재측정 PASS).

**[프롬프트 — Claude Code CLI에게]**

```
M3 벤치마크가 PASS되었다. 임베딩이 포함된 DB를 클라우드에 배포하라.

■ 배포 절차

1. 임베딩 데이터를 포함한 Migration 파일 생성:
   - 임베딩 벡터는 SQL INSERT/UPDATE로 직접 포함하기에 너무 크므로,
     별도 Python 스크립트로 클라우드 DB에 직접 UPDATE하는 방식을 사용
   - 스크립트: scripts/push_embeddings_to_cloud.py

2. 스크립트 내용:
   - 로컬 DB에서 임베딩 벡터를 읽어서
   - 클라우드 DB(DATABASE_URL 환경변수)에 UPDATE
   - 건별 진행률 출력

3. 실행 전 확인:
   - supabase db push로 스키마 동기화 확인 (이미 M2에서 push됨)
   - 클라우드 DB에 시드 데이터(394 규범, 38 패턴)가 있는지 확인

4. 실행 후 검증:
   - 클라우드 DB에서 patterns 임베딩 NOT NULL 건수 확인
   - 클라우드 DB에서 ethics_codes 임베딩 NOT NULL 건수 확인

⚠️ 이 작업은 Claude Code CLI에서만 실행. 마누스 Deny List 해당.

결과를 보고하라.
```

**[체크포인트]** 배포 성공 확인.

---

### STEP 30. 마누스 (MCP) — 클라우드 DB 최종 확인

**[시점]** STEP 29 완료 후.

**[프롬프트 — 마누스에게]**

```
M3 임베딩이 클라우드 DB에 배포되었다.
MCP(읽기 전용)로 클라우드 DB를 확인해줘:

1. patterns 테이블: 총 건수, description_embedding IS NOT NULL 건수
2. ethics_codes 테이블: 총 건수, text_embedding IS NOT NULL 건수
3. search_pattern_candidates() 함수 테스트:
   - 임의의 임베딩 벡터로 호출하여 결과가 반환되는지 확인
   (실제 기사 임베딩은 없으므로, 기존 패턴의 임베딩을 쿼리로 사용하여 자기 자신이 
    최상위로 반환되는지 self-retrieval 테스트)

결과를 보고해줘.
```

**[체크포인트]** 클라우드 DB에서 정상 동작 확인.


---

### STEP 31. Claude Code CLI — SESSION_CONTEXT 갱신

**[시점]** STEP 30 완료 후. Day 3 마무리.

**[프롬프트 — Claude Code CLI에게]**

```
M3가 완료되었다. 세션 컨텍스트를 갱신하라.

1. SESSION_CONTEXT 최신 버전(v14)을 복사하여 v15를 생성하라.
2. v15에 다음 내용을 반영:
   - M3 완료 상태 기록:
     · 날짜
     · 임베딩 모델 최종 확정 (모델명, 차원)
     · 임베딩 적재 결과 (patterns N건, ethics_codes N건)
     · Recall@10 결과 (전체 평균, 대분류별)
     · 최종 확정 threshold
     · 초단문 처리 26건 결과
   - 벤치마크에서 발견된 교훈/이슈 요약
   - "다음 세션에서 할 일"을 M4(RAG 파이프라인 구현)로 갱신
   - M4 사전 준비 사항 추가:
     · 기사 청킹 로직 프로토타이핑 (마스터 플랜 섹션 4에서 미결)
     · 메타 패턴 라우팅 방식 확정 (앙상블 보류 건)
     · get_ethics_for_patterns 입력 타입 처리 (앙상블 보류 건)
3. v14는 _archive_superseded/로 이동
4. docs/M3_BENCHMARK_RESULTS.md가 생성되었는지 확인
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 비상 시나리오별 대응 프롬프트
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 시나리오 E: OpenAI API 키 오류 또는 한도 초과

**[증상]** `AuthenticationError` 또는 `RateLimitError` 발생

**[대응]**
1. API 키 확인: `echo $OPENAI_API_KEY | head -c 10` (앞 10자 확인)
2. 잔액 확인: OpenAI 대시보드에서 크레딧 확인
3. Rate limit일 경우: 배치 크기를 줄이고 sleep 추가

**[프롬프트 — Claude Code CLI에게]**

```
OpenAI API 호출 중 오류가 발생했다.

■ 오류 메시지:
[오류 전문 붙여넣기]

1. 오류 원인을 분석하라
2. Rate limit인 경우: 배치를 100개씩 나눠서 호출하도록 스크립트 수정
3. 인증 오류인 경우: 환경변수 설정을 확인하고 가이드 제시
4. 수정 후 재실행
```

### 시나리오 F: 임베딩 차원 불일치

**[증상]** DB UPDATE 시 `invalid input syntax for type vector` 오류

**[대응]**
- DB 컬럼은 vector(1536)으로 정의됨
- text-embedding-3-small은 1536차원이므로 정상적으로 일치해야 함
- 다른 모델을 사용했거나, 차원 파라미터를 잘못 지정한 경우 발생

**[프롬프트 — Claude Code CLI에게]**

```
임베딩 차원 불일치 오류가 발생했다.

■ 오류 메시지:
[오류 전문 붙여넣기]

1. 생성된 임베딩의 실제 차원을 확인하라 (len(embedding) 출력)
2. DB 컬럼의 차원을 확인하라 (SELECT * FROM information_schema.columns WHERE ...)
3. 차원이 다르면:
   - 임베딩 모델의 dimensions 파라미터를 조정하거나
   - DB 컬럼을 ALTER TABLE로 변경 (Migration 파일로만)
4. 수정 후 재실행
```

### 시나리오 G: Recall@10이 전체적으로 낮은 경우

**[증상]** 전체 평균 Recall@10 < 50%

**[프롬프트 — Claude.ai에게]**

```
M3 벤치마크에서 Recall@10이 전체적으로 매우 낮다 (평균 X%).

■ 벤치마크 결과:
[결과 전문]

근본 원인 진단을 해줘:
1. 패턴 description 텍스트가 기사 문체와 너무 다른가?
2. 골든 데이터셋의 article_key_text 품질에 문제가 있는가?
3. 임베딩 모델이 한국어 법률/규범 도메인에 약한가?
4. search_pattern_candidates() 함수 로직에 문제가 있는가?
5. 다른 근본 원인이 있는가?

각 가능성에 대해 검증 방법과 해결책을 제시해줘.
```

### 시나리오 H: 특정 대분류만 Recall이 낮은 경우

**[증상]** 예: "1-5 인권"의 Recall만 20%, 나머지는 85%+

**[프롬프트 — Claude Code CLI에게]**

```
M3 벤치마크에서 대분류 [X]의 Recall만 현저히 낮다.

■ 해당 대분류의 건별 결과:
[결과 붙여넣기]

1. 해당 대분류의 패턴 description을 출력하라
2. 실패한 기사의 article_key_text를 출력하라
3. 두 텍스트를 나란히 비교하여, 의미적 유사도가 낮은 이유를 분석하라
4. 패턴 description을 보강(enrichment)하면 해결될 수 있는가?
   - 보강 방법: description에 동의어, 사례 문장을 추가
   - 주의: 원본 패턴 정의를 변경하는 것이 아니라, 
     임베딩용 보강 텍스트를 별도 관리
5. 보강 텍스트 초안을 제시하고, 보강 후 재임베딩 → 재측정
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 사전 점검 노트: 기사 청킹 로직
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

마스터 플랜에서 "기사 청킹 로직 프로토타이핑: M3 벤치마크 전까지 검증 필수"로 
표기되어 있으나, M3 벤치마크 자체는 골든 데이터셋의 article_key_text를 
직접 쿼리로 사용하므로 청킹이 필수가 아니다.

**청킹이 실제로 필요한 시점**: M4(RAG 파이프라인 구현)에서 실제 기사 URL → 
스크래핑 → 청킹 → 임베딩 → 검색 흐름을 구현할 때.

**M4 플레이북에서 다룰 청킹 관련 사항**:
- 의미 기반 병합 청킹 (300~500자 블록)
- 한 문장 줄바꿈 한국 뉴스 관행 대응
- 노이즈 제거 (사진 캡션, 바이라인, 관련기사 링크 등)
- 엣지케이스: 리스트형 기사, 1만자+ 장문 기사

단, M3 벤치마크 결과가 좋지 않을 경우 청킹 품질 문제를 의심할 수도 있으므로,
벤치마크 결과 분석 시 이 점을 염두에 둘 것.


---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 타임라인 요약
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
Day 3 (M3: 임베딩 + 벤치마크)

Phase A — 임베딩 생성 스크립트 (감리 포함)
├─ STEP 19: CC CLI — 세션 시작 + 임베딩 생성 스크립트 작성
├─ STEP 20: Claude.ai — 1차 감리 (스크립트)
├─ STEP 21: 마누스 — 2차 독립 감리 (스크립트)
├─ STEP 22: Gamnamu — 비교·판단·(수정 22-1)

Phase B — 임베딩 실행 + 적재 검증
├─ STEP 23: CC CLI — 임베딩 생성 실행 + DB UPDATE + 로컬 검증
├─ STEP 24: 마누스 MCP — 임베딩 적재 확인

Phase C — 벤치마크 (핵심)
├─ STEP 25: CC CLI — 벤치마크 스크립트 작성 + 실행
├─ STEP 26: Claude.ai — Recall@10 결과 리뷰 + threshold 판단
├─ STEP 27: Gamnamu — 벤치마크 결과 최종 판단 (★ 분기점)
├─ STEP 28: (조건부) CC CLI — threshold 조정 / 대안 모델 / 세분화

Phase D — 배포 + 마무리
├─ STEP 29: CC CLI — 클라우드 배포
├─ STEP 30: 마누스 MCP — 클라우드 DB 최종 확인
└─ STEP 31: CC CLI — SESSION_CONTEXT v14→v15 갱신
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M1/M2 대비 M3의 구조적 차이점
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 항목 | M1/M2 | M3 |
|------|-------|-----|
| **감리 대상** | SQL Migration 파일 | Python 스크립트 + 실행 결과 |
| **2차 감리자** | Antigravity/Gemini | 마누스 |
| **스크립트 감리 시점** | 실행 전 | 실행 전 (STEP 20-21) |
| **결과 감리 시점** | — | 실행 후 (STEP 26) |
| **분기점** | 감리 승인/반려만 | Recall@10 기준 3경로 분기 |
| **배포 방식** | supabase db push | Python 스크립트로 임베딩 직접 UPDATE |
| **외부 API 의존** | 없음 | OpenAI API (비용 발생) |
| **비상 시나리오** | A-D (4건) | E-H (4건, 누적 8건) |

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M3 완료 기준 (Definition of Done)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- [ ] 패턴 30개의 description_embedding이 DB에 적재됨
- [ ] 규범 373개의 text_embedding이 DB에 적재됨
- [ ] 메타 패턴 2개 + is_citable=FALSE 21건에 임베딩 없음 확인
- [ ] 초단문 26건이 결합 텍스트로 임베딩됨
- [ ] Recall@10 ≥ 80% 달성 (또는 대안 모델로 달성)
- [ ] 최적 threshold 확정
- [ ] 임베딩 모델 최종 확정
- [ ] 벤치마크 결과가 docs/M3_BENCHMARK_RESULTS.md에 기록됨
- [ ] 클라우드 DB에 임베딩 배포 완료
- [ ] 마누스 MCP로 클라우드 검증 완료
- [ ] SESSION_CONTEXT v15 갱신 완료

---

*이 플레이북은 2026-03-28에 작성되었으며, M1/M2 플레이북(CR_CHECK_WEEK1_PLAYBOOK.md)의 
삼각편대 감리 흐름과 STEP 구조를 동일하게 적용했다.*
*2차 독립 감리자가 Antigravity/Gemini에서 마누스로 변경되었다.*
*실제 작업 중 상황에 따라 유연하게 조정할 수 있다.*
