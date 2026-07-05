# T1 임베딩 재생성 절차 (기획자 본인 터미널에서 실행)

Wave 1.1 T1 — `wave1.1_t1_pattern_enrichment.sql`을 SQL Editor에서 실행·검증한
**이후**에만 아래를 순서대로 실행한다. CLI(Claude Code)는 이 스크립트를 실행하지
않는다 (OpenAI API 호출 + DB 직접 UPDATE = DB 쓰기 행위).

## 사전 확인 (스크립트 동작 범위 — 실측)

- `--patterns-only`는 **"이번에 search_text가 바뀐 4건만"이 아니라, 활성 vector
  leaf 패턴 전체(STEP 6 기준 64건)를 재생성한다**
  (`fetch_patterns()`의 4-필터: is_active / vector / leaf 정규식, NULL 임베딩
  조건 없음 — 직접 UPDATE 덮어쓰기 방식).
- `--codes 4-3-b,...` 같은 **범위 한정 옵션은 존재하지 않는다** (argparse 인자:
  `--db-url`, `--patterns-only`, `--dry-run` 3개뿐).
- 따라서 실행 시 STEP 6에서 만든 나머지 60건의 임베딩도 **같은 search_text로
  재생성**된다. search_text가 동일하면 임베딩도 사실상 동일하게 재현되지만
  (동일 모델·동일 입력), 재생성 자체를 피하고 싶다면 스크립트에 범위 한정
  옵션을 추가하는 별도 STEP이 필요하다 — **실행 여부는 기획자 판단**.
- 임베딩 입력은 `search_text` **단독**이다 (description은 리포트·카탈로그용,
  임베딩에 미사용 — C-13). 즉 T1 SQL의 description 확장은 Phase 1 카탈로그
  텍스트에, search_text 확장은 벡터 유사도에 각각 반영된다.
- 6-2-c는 structural이라 재생성 대상에 포함되지 않는다 (정상).

## 실행 순서

```bash
# 1. dry-run — 대상 64건 목록과 4-3-b/3-4-a/3-4-b/6-2-d의 확장된
#    search_text preview가 보이는지 확인
python scripts/generate_embeddings.py --patterns-only --dry-run --db-url "<운영 DB URL>"

# 2. 본 실행
python scripts/generate_embeddings.py --patterns-only --db-url "<운영 DB URL>"
```

주의:
- `--db-url` 기본값은 **로컬**(`postgresql://postgres:postgres@127.0.0.1:54322/postgres`)
  이므로 운영 반영 시 반드시 운영 DB URL을 명시한다.
- 비밀번호에 `#`, `/` 포함 시 URL escape 필요 (CLAUDE.md Gotcha).
- `OPENAI_API_KEY`는 `backend/.env`에서 로드된다.

## 사후 검증 (SQL Editor)

```sql
SELECT code, detection_strategy, description_embedding IS NOT NULL AS has_embedding
FROM public.patterns WHERE code IN ('4-3-b','3-4-a','3-4-b','6-2-d');

-- 전체 차원 검증 (STEP 6과 동일 기준: dims=[1536])
SELECT DISTINCT vector_dims(description_embedding) FROM public.patterns
WHERE description_embedding IS NOT NULL;
```
