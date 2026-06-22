# CR-Check 최종 진단 보고서 · 최종 개선안

> **확정일**: 2026-06-12
> **검증 기준**: 코드 HEAD `039f133` 행 단위 대조 + 운영 DB(`vwaelliqpoqzeoggrfew`) 직접 실측
> **성격**: 본 문서는 앞선 진단·개선안 문서들을 대체하는 **단일 확정본**이다. 수록된 모든 사실 명제는 실제 코드와 운영 데이터로 직접 검증되었으며, 모든 패치는 Claude Code CLI에 단위별로 그대로 지시할 수 있는 수준으로 기술한다.

---

# 제1부 — 최종 진단 보고서

## 1. 핵심 결론

리포트 품질 저하는 단일 버그가 아니라 **3개 레이어의 구조적 공백이 같은 방향으로 중첩**된 결과다.

| 레이어 | 공백 | 효과 |
|---|---|---|
| **C — 데이터** | `pattern_ethics_relations` 매핑이 2개 source에 편중. 활성 leaf 패턴 76개 중 **70개(92.1%)는 Tier 3 `violates` 연결 0건** | 인용할 하위 준칙이 컨텍스트에 **공급되지 않음** |
| **B — 직렬화** | RPC가 상위 원칙 롤업 행을 `related_to/moderate`로 강제 주입하는데, `_build_ethics_context`는 롤업 마커가 아닌 `relation_type`으로 분할 | 직접 매핑된 하위 준칙이 "참고 규범(맥락 이해용)"으로 **강등되어 노출** |
| **A — 프롬프트** | 하드코딩 시절 프롬프트의 분량 명세·Bottom-up 인용 우선순위·"헌장 단독 인용 금지"·나쁜/좋은 예가 RAG 전환 시 소실 | 모델이 짧고 평면적인 서술로 수렴, 상위 원칙 **인용을 회피하지 않음** |

여기에 **제4의 힘**이 가세한다: 컨텍스트 내 조문 길이 비대칭(Tier 1 헌장 259~301자의 서사적 전문 vs Tier 3 준칙 38~57자의 한 줄 금지조항)이 모델을 "인용할 내용이 풍부한" 상위 규범으로 끌어당긴다.

따라서 원인 구조의 깊이는 **C(공급) → B(노출) → A(인용 유도)** 순서로 이해해야 한다. 다만 실행은 그 역이다: B·A 코드 수정(Wave 1)을 먼저 적용해 측정 기반을 확보하고, C 큐레이션은 병렬로 준비하되 Wave 1.5 측정 결과와 선행 게이트 통과를 확인한 뒤 배포한다(Wave 2).

## 2. 운영 DB 정량 포렌식 (전수 실측)

### 2.1 매핑 편중 — 체감이 아닌 측정된 사실

`pattern_ethics_relations` 267건의 Tier 분포:

| Tier | 의미 | 연결 수 | 비율 |
|---|---|---|---|
| 1 (언론윤리헌장) | 최상위 포괄 원칙 | 82 | 30.7% |
| 2 (강령·실천요강) | 중간 | 153 | 57.3% |
| 3 (준칙 — 실질 하위 규범) | 구체 | **28** | **10.5%** |
| 4 (선언) | 부속 | 4 | 1.5% |

- 활성 leaf 패턴 76개(vector 64 + structural 12) 중 **70개(92.1%)가 Tier 3 `violates` 연결 0건**. 패턴당 평균 연결 2.1건.
- citable 규범은 225건(T1 8 / T2 52 / **T3 159** / T4 6) — 인용 가능한 하위 준칙의 대부분(159건)이 사실상 미사용 상태.
- **매핑 0건 source 4종**: 자살보도 윤리강령(crisis 한정, 10조항) · 자살예방 보도준칙 4.0(crisis, 10) · 평화통일 보도 준칙(unification, 8) · 군 취재·보도 기준(military, 2). 전부 특정 맥락 한정 조항이다(제2부 Wave 2의 핵심 함정).

### 2.2 실제 인용 분포 — 편중의 재현

운영 84건의 3종 리포트에서 〔…〕 인용 584건 추출:

| 인용된 규범 | Tier | 비율 |
|---|---|---|
| 신문윤리실천요강 | 2 | 68.2% |
| 언론윤리헌장 | 1 | 25.5% |
| 인권보도준칙 | 3 | **1.5%** |
| 미매칭 | — | 4.8% |

미매칭 28건(4.8%)을 표기 변형("제3조 ①" ↔ "제3조 1항" 등)과 구분해 재분류하면 **DB에 실존하지 않는 규범명을 지어낸 진짜 환각은 10건(약 1.7%)**이다(〔언론인 윤리강령 제3조〕 등). 환각은 실재하되, 26건 골든셋으로는 통계적으로 검출 불가능한 희소 사건이므로 골든셋 합격 지표가 아니라 **운영 누적 모니터링 지표**로 다뤄야 한다.

### 2.3 분량·구조 실측

- Phase 2 출력은 `max_tokens=10000` 대비 35~42%(3.5~4.2k 토큰)에서 자체 종료 — cap에 걸리지 않는데도 짧게 끝낸다. `temperature=0.0`에서 분량 하한이 없으면 모델은 최단 길이로 수렴한다.
- 시민용 리포트 평균 1,000~1,500자이나, 하드코딩 시절의 "문제점 분석 + 종합 평가"로 구조화된 분량이 아니라 비구조 나열의 분량이다. 탐지 패턴 수가 늘어도(4월 1.7개 → 5월 3.0개) 인용·분량이 비례 증가하지 않음 — 패턴당 서술 깊이가 얕아지는 방향.

### 2.4 기타 운영 리스크

| 항목 | 실측 |
|---|---|
| 마이그레이션 드리프트 | DB `schema_migrations` 기록 **3건** vs 저장소 마이그레이션 파일 **11개**. 이력 테이블 구조는 `version(text) / name(text) / statements(text[])` 3컬럼 |
| NULL 임베딩 | **활성 vector leaf 64건은 전원 임베딩 보유(NULL 0건).** 임베딩 NULL은 부모·최상위 패턴 12건(1~8 및 4-3·4-4·6-4·6-6)뿐 — leaf 정규식 `^[0-9]+-[0-9]+-[a-z]+$` 미매칭으로 **설계상 의도된 제외**이며, 부모 4건(4-3·4-4·6-4·6-6)의 자식 leaf 14개는 전원 임베딩 보유·활성. 재임베딩 등 보정 작업 불필요. 단 이들 부모가 `hierarchy_level=3`으로 저장되어 있어 관리상 혼동 가능(기능 영향 없음) |
| meta_patterns | `analysis_results` 84건 전수 **NULL** — 메타패턴 추론 비활성화로 직렬화 결과가 항상 빈 리스트 → None 적재 |
| feedbacks | 0건 — 정성 평가 루프 미축적 |
| analysis_ethics_snapshot | 54건 적재 중, Tier 분포(T2 28/T1 20/T3 6)가 인용 편중과 동일 패턴 |

## 3. 코드 레이어 확정 진단 (행 단위 검증 완료)

### 3.1 프롬프트 — 소실 자산 목록

`prompt_builder.py:106-206`(하드코딩 자산)에 있었으나 현행 `_SONNET_SYSTEM_PROMPT`(`report_generator.py:274-375`)로 이전되지 않은 것:

| 소실 자산 | 원위치 | 현행 상태 |
|---|---|---|
| 분량 명세(시민용 1000-1500자 + 내부 분할) | `prompt_builder.py:153-158` | **글자 수 지정 0건** — 유일한 길이 지시는 분석 개요 항목의 상한(L342 "최대 80자")과 간결성 지시(L340)뿐. 즉 분량 하한·섹션 구조 디렉티브는 "복원"이 아니라 **신규 추가** 대상이다 |
| 구조 골격(도입→본론→개선안→결론) | `prompt_builder.py:170-174` | 없음. L333-334는 "제목으로 시작 금지"만 지시 |
| Bottom-up 인용 1·2·3순위 | `prompt_builder.py:128-139` | 약화(L308-312) — "1~2회 상위 확장"이 오히려 상위 인용을 정당화 |
| **헌장 단독 인용 금지** | `prompt_builder.py:136` | 삭제됨 |
| 나쁜 예/좋은 예 대비 | `prompt_builder.py:138-139` | 삭제됨 |

현행 프롬프트의 좋은 자산(〔 〕 표기 규칙, 3종 톤 차이, JSON 출력 형식, L331 "중간제목 ### 최대 3~4개" 규칙)은 보존한다. 특히 "도입 → 핵심 지적 2~3개 → 종합"의 구조 디렉티브는 중간제목 3~4개 규칙과 **양립**하므로 함께 명시할 수 있다.

### 3.2 직렬화 — 롤업 강등 메커니즘

- RPC `get_ethics_for_patterns(confirmed_pattern_ids bigint[], article_context text DEFAULT 'general')`는 직접 매핑 행은 원래 `relation_type/strength/reasoning`을 보존하되, parent-chain 롤업 행(재귀 CTE, 깊이 ≤5)은 **`'related_to','moderate','parent chain rollup'`으로 강제 주입**한다.
- `_build_ethics_context`(`report_generator.py:215-269`)는 `relation_type`으로만 2분할(violates → "핵심 규범" / related_to → "참고 규범(직접 인용보다 맥락 이해용)"). 결과: 직접 매핑된 `related_to` 하위 준칙이 자동 롤업 상위 원칙과 같은 "참고용" 섹션에 섞여 강등된다. 양 섹션 정렬키는 `(-r.ethics_tier, r.ethics_code)`로 동일.
- `reasoning` 필드는 RPC → `_parse_ethics_rows`(L65-79)까지 보존되나, 소비처인 `_build_ethics_context`가 이를 분기 기준으로 사용하지 않는 것이 결함의 정확한 위치다.
- RPC 반환 10컬럼에는 `source`·`article_number`가 없다. 반면 `ethics_codes`의 citable 225건은 **전건이 source+article_number를 보유하며 그 쌍이 고유**하다 — 정식 인용명 생성과 인용 대조의 canonical key로 즉시 사용 가능.

### 3.3 인용 대조의 함정 — 조항번호는 title에 없다

`ethics_codes.title`에 조항번호가 들어 있는 것은 아니다 — 문제는 naive 정규식이 조항번호로 **오인**할 수 있는 문자열이 title에 실재한다는 점이다. 실측 예: PCP-5-3의 title **"제3자 비방과 익명보도 금지"** — `제[0-9]` 류 정규식으로 파싱하면 "제3자"가 조항번호로 오인된다. **조항번호의 신뢰 가능한 출처는 `article_number` 컬럼뿐**이며, 인용 검증·헤더 생성 모두 `source + article_number`를 키로 사용해야 한다. title 정규식 파싱은 금지.

### 3.4 확정된 개별 결함

| # | 결함 | 위치 | 판정 |
|---|---|---|---|
| 1 | Chunk fallback이 `start=, end=, length=` 3개 무효 kwarg로 호출 — 청킹 실패 시 `TypeError` 이중 폭발 | `pipeline.py:121` (`Chunk`는 `text, start_idx, end_idx`만 보유, `length`는 property) | 버그 확정 |
| 2 | 활성 파이프라인에 프롬프트 캐싱 전무 — `cache_control`은 코드베이스 전체에서 1건(`analyzer.py:272`)뿐이며, `analyzer.py`는 `main.py:21-22` 주석대로 런타임 미호출 레거시 | Phase 1·2 모두 매 호출 평문 재전송. Phase 2 시스템 프롬프트는 3,067자 고정 텍스트 | 확정 |
| 3 | Phase 1→2 페이로드 4필드 압축(pattern_code, matched_text, severity, reasoning) — 패턴명·기각 근거 미전달 | `pipeline.py:162-171` | 확정 |
| 4 | `report_framing`·`name`은 카탈로그 select(`pattern_matcher.py:128-139`)에 이미 포함·캐시되나 Phase 2로 전달 안 됨 | — | 확정(DB 왕복 0회로 해결 가능) |
| 5 | 메타패턴 잔존 코드는 전 실행 경로에서 격리된 dead code — 품질 영향 0 | `pipeline.py:144-158` 외 | 반증 완료 |
| 6 | threshold 0.2 → 0.5 인상은 안티패턴 — search_text 기반 임베딩은 유사도 절대값이 낮아(STEP6 명시) 정답 컷오프 → recall 붕괴 | `pattern_matcher.py:38` | 인상 금지 확정 |
| 7 | `_infer_article_context`는 기사 앞 500자 키워드 휴리스틱. crisis 키워드는 `['극단적 선택','자해','유서','투신','심리상담']`로 **'자살' 미포함**(L79 주석 "오분류 방지를 위해 복합어·구체적 키워드만 사용" — 의도적 보수 설계). 추론 결과는 어디에도 저장되지 않아 오분류 감사가 현재 불가능 | `pipeline.py:67-95` | 확정 |
| 8 | `analysis_results` INSERT payload는 11키+share_id. JSONB 3종 중 프런트엔드에 노출되는 것은 **`article_analysis`뿐**(article_info로 평탄화, `ResultViewer.tsx:287-316`). `detected_patterns`·`meta_patterns`는 프런트 참조 0건 | `storage.py:487-505` | 확정(신규 감사 데이터의 적재 위치 결정 근거) |
| 9 | `anthropic>=0.49.0,<1.0.0` — `cache_control`(SDK 0.30.0+ 지원)·system 블록 배열 모두 추가 의존성 없이 사용 가능 | `backend/requirements.txt:3` | 확정 |
| 10 | 골든셋 기사 원문은 저장소 외부 `/Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts/`에 위치 | `docs/SESSION_CONTEXT_2026-05-10_v55.md:57` | 확정(CLI 작업 지시 시 명시 필수) |

## 4. 관찰 9건 최종 판정 요약

| 관찰 | 요지 | 판정 | 근거 요약 |
|---|---|---|---|
| 1 | 분량·일관성 저하, 두루뭉수리 | **확인** | 분량 하한 0건 + temperature 0.0 → 최단 수렴 |
| 2 | match_count↑? threshold 0.2→0.5? | **부분확인/주의** | threshold 인상은 recall 붕괴. match_count 증가는 한계 효용 낮음 — 진짜 병목은 매핑 편중 |
| 3 | Sonnet 2-call 교차검증 | **설명** | 과거 2-Call 실패는 Haiku(Suspect 0.0%) 탓 — 별개 시나리오. 단 비용·Duration 2배, A/B 측정이 선결 |
| 4 | 메타패턴 잔존 코드 영향? | **반증** | 전 경로 격리 dead code, 영향 0 |
| 5 | TN/TP 근거의 Phase 2 전달? | **확인** | 4필드 압축, 기각 근거 전달 경로 없음 |
| 6 | 단순 나열, 논리 축적 없음 | **확인** | 누적 골격 소실(관찰 1과 동일 뿌리) |
| 7★ | 하위 준칙 미소환, 상위만 인용 | **확인(3원인+1)** | A 프롬프트 + B 직렬화 + C 데이터 + 조문 길이 비대칭 |
| 8 | 서둘러 작성된 느낌, Duration | **확인** | 출력이 객관적으로 짧음(cap 35~42%). 원인은 관찰 1과 동일 |
| 9 | report_generator만의 문제인가 | **확인(다중)** | 프롬프트·직렬화·파이프라인·RPC·데이터 5지점 의존 |
| API | Phase 1 입력 39,999토큰 절단? | **설명(절단 아님)** | 카탈로그 전체+기사 구성, 200k 한도 대비 여유 |

---

# 제2부 — 최종 개선안

## 0. 설계 원칙

1. **이해는 C → B → A, 실행은 B·A 먼저.** 데이터(공급) 공백이 가장 깊은 원인이지만, 큐레이션은 검증 비용이 크고 오염 리스크가 있으므로 코드 수정(Wave 1: B·A)을 먼저 배포·측정하고, C 큐레이션은 병렬 준비 후 Wave 1.5 결과를 보고 배포한다(Wave 2).
2. **자동 INSERT 금지.** 매핑 확장의 최종 판단은 인간 검수. 자동화는 후보 제안까지만.
3. **DB 변경은 SQL Editor 수동 실행 + 이력 동기화.** 동일 SQL을 저장소 마이그레이션 파일로 커밋하고, `schema_migrations`에 수동 INSERT(실제 테이블 구조 `version/name/statements` 준수)하여 드리프트(현재 3 vs 11)를 더 키우지 않는다.
4. **측정 없는 도입 금지.** 재시도 트리거·모델 교차검증·threshold 변경은 전부 측정 후 결정.
5. **내부 코드 비노출.** JEC-4, PCP-3-1 같은 내부 코드는 어떤 fallback 경로에서도 사용자 화면에 노출되지 않는다.

## 1. Wave 1 — 즉시 적용 7항목

### 의존성 그래프

```
1-2 RPC 마이그레이션 → 1-3 파이썬 소비층 동기화 → 1-4 3섹션 재구성 → 1-5 프롬프트 개편+캐싱
1-1 Chunk 버그           (독립 — 언제든 병렬)
1-6 report_framing 전달   (독립 — 언제든 병렬)
1-7 verify_citations 로깅 (독립 — 단 source/article_number 매칭은 1-2 완료 후)
```

### 1-1. Chunk fallback 버그 수정 (독립, 1줄)

```python
# pipeline.py:121 — 현행: start/end/length 3개 모두 무효 kwarg
chunks = [Chunk(text=article_text, start=0, end=len(article_text), length=len(article_text))]
# 수정 (length는 @property이므로 전달 금지)
chunks = [Chunk(text=article_text, start_idx=0, end_idx=len(article_text))]
```

검증: `chunk_article` 강제 예외 후 fallback이 `TypeError` 없이 단일 청크를 반환하는 단위 테스트.

### 1-2. RPC 마이그레이션 — source/article_number 추가 + citation_audit 컬럼 동봉 (선행)

`RETURNS TABLE` 컬럼 추가는 `CREATE OR REPLACE` 불가 → **DROP 후 재생성**. 하나의 마이그레이션에 다음을 모두 담아 트랜잭션으로 묶는다(분리 마이그레이션 추가 비용·드리프트 방지).

**(0) 사전 백업 — 현행 정의를 로컬 파일로 보관(필수 선행):**

```sql
SELECT pg_get_functiondef('public.get_ethics_for_patterns(bigint[], text)'::regprocedure);
```

→ 출력 전문을 `supabase/migrations/_backup/get_ethics_for_patterns_pre_20260612.sql`로 저장소에 커밋. DROP 이후의 유일한 원복 수단이다.

**(1) 마이그레이션 본문:**

```sql
BEGIN;

DROP FUNCTION IF EXISTS public.get_ethics_for_patterns(BIGINT[], TEXT);

CREATE FUNCTION public.get_ethics_for_patterns(
  confirmed_pattern_ids BIGINT[],
  article_context TEXT DEFAULT 'general'
)
RETURNS TABLE(
  pattern_id BIGINT, pattern_code TEXT, ethics_code_id BIGINT, ethics_code TEXT,
  ethics_title TEXT, ethics_source TEXT, ethics_article_number TEXT,   -- ★ 신규 2컬럼
  ethics_full_text TEXT, ethics_tier INTEGER,
  relation_type TEXT, strength TEXT, reasoning TEXT
)
-- 본문은 백업한 현행 정의에 ec.source, ec.article_number를 추가
;

-- 인용 감사 로그 적재 컬럼 (1-7에서 사용)
ALTER TABLE public.analysis_results
  ADD COLUMN IF NOT EXISTS citation_audit JSONB;

COMMIT;

NOTIFY pgrst, 'reload schema';
```

**SQL 본문의 수정 지점은 정확히 5곳** — 재귀 CTE의 `UNION`은 양변 컬럼 수·타입이 완전히 일치해야 하므로 한 곳이라도 빠지면 함수 생성 자체가 실패한다:

| # | 위치 | 수정 |
|---|---|---|
| 1 | `direct_codes` CTE의 SELECT | `ec.source, ec.article_number` 추가 |
| 2 | `parent_chain` 재귀 CTE — base case | `source, article_number` 컬럼 추가 |
| 3 | `parent_chain` 재귀 CTE — recursive case | 동일 추가(양변 컬럼 일치) |
| 4 | 최종 SELECT — 직접 매핑 분기 | `dc.source, dc.article_number` |
| 5 | 최종 SELECT — 롤업 분기 | `pc.source, pc.article_number` |

**(2) 사후 검증 — 정의 확인 + 실호출 테스트:**

```sql
SELECT pg_get_function_result('public.get_ethics_for_patterns(bigint[], text)'::regprocedure);
-- ethics_source, ethics_article_number 포함 12컬럼인지 확인

SELECT * FROM public.get_ethics_for_patterns(
  ARRAY[(SELECT id FROM patterns WHERE is_active LIMIT 1)]::bigint[], 'general'
) LIMIT 5;  -- 신규 컬럼에 실값이 채워지는지 확인
```

**(3) 이력 동기화** — `schema_migrations`의 실제 구조(`version text, name text, statements text[]`)에 맞춰 수동 INSERT:

```sql
INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
VALUES ('20260612000000', 'rpc_source_article_number_and_citation_audit',
        ARRAY['<위 마이그레이션 SQL 전문>']);
```

동일 SQL을 `supabase/migrations/20260612000000_rpc_source_article_number_and_citation_audit.sql`로 커밋하고, SESSION_CONTEXT 문서에 "운영 DB 적용 완료" 여부를 명시한다.

> **citation_audit을 별도 컬럼으로 두는 근거(코드 실측 기반)**: ① `article_analysis`는 article_info로 평탄화되어 **UI에 노출**되므로 내부 감사 데이터를 섞으면 안 되고, ② `detected_patterns`는 탐지 결과 리스트라 감사 메타데이터를 끼워 넣으면 의미가 오염되며, ③ `meta_patterns`는 메타패턴 재활성화 시를 위해 비워둔다. ④ 별도 컬럼은 이번 마이그레이션에 동봉되므로 추가 비용이 0이고, 주간 모니터링 SQL 집계가 가장 단순해진다. 프런트엔드는 이 컬럼을 참조하지 않으므로 사용자 비노출이 보장된다.

### 1-3. 파이썬 소비층 동기화 — 동반 수정 5곳 (1-2 직후)

| 위치 | 수정 |
|---|---|
| `EthicsReference`(`report_generator.py:37-47`) | 필드 추가: `ethics_source: str = ""`, `ethics_article_number: str = ""` — 기존 8필드는 기본값이 없고 유일 인스턴스화는 `_parse_ethics_rows` 1곳뿐이지만, 신규 2필드는 **맨 뒤에 기본값과 함께** 추가해 부분 적용 시점·예외 경로에서도 생성이 깨지지 않게 한다 |
| `_parse_ethics_rows`(L65-79) | `ethics_source=row.get("ethics_source", "")`, `ethics_article_number=row.get("ethics_article_number", "")` 파싱 추가 |
| REST fallback select(L165) | `ethics_codes!inner(code,title,source,article_number,full_text,tier,is_active,is_citable,applicable_contexts)` |
| REST fallback row 조립(L196-205) | `"ethics_source": ec.get("source", "")`, `"ethics_article_number": ec.get("article_number", "")` 추가 |
| 헤더 생성 규칙 | 아래 빈 값 가드 적용 |

**헤더 빈 값 가드** — source/article_number 어느 한쪽이라도 비면 빈 괄호 〔 〕가 출력되지 않도록:

```python
citation_label = f"{r.ethics_source} {r.ethics_article_number}".strip()
if citation_label:
    header = f"### 〔{citation_label}〕 {r.ethics_title} (Tier {r.ethics_tier})"
else:
    header = f"### {r.ethics_title} (Tier {r.ethics_tier})"   # 강등 — 내부 코드는 절대 노출 금지
```

**fallback 한계 명시**: REST fallback은 parent-chain 롤업을 수행하지 않으므로(직접 관계 단순 JOIN) 발동 시 "상위 원칙" 섹션이 부실해진다. 발동 로깅은 이미 존재(L155 외) → Wave 1.5 측정 시 교란 변수로 기록만 하면 충분하며, 롤업 백필 구현은 발동 빈도 실측 후 판단한다.

### 1-4. `_build_ethics_context` 3섹션 재구성 (1-3 직후)

분할 기준을 `relation_type`에서 **롤업 마커**로 교체:

```python
_ROLLUP_MARKER = "parent chain rollup"

for r in refs:
    if (r.reasoning or "").strip() == _ROLLUP_MARKER:
        rollup.append(r)        # ③ 상위 원칙 — 단독 인용 금지
    elif r.relation_type == "violates" and r.strength in ("strong", "moderate"):
        primary.append(r)       # ① 직접 적용 규범 — 인용 1순위
    elif r.relation_type == "related_to" and r.strength in ("strong", "moderate"):
        reference.append(r)     # ② 직접 참고 규범 — 보조 인용 가능
```

- 섹션 라벨: **"직접 적용 규범(인용 1순위)" / "직접 참고 규범(보조 인용 가능)" / "상위 원칙(단독 인용 금지 — 종합 평가 보조용)"**.
- 정렬: ①·②는 현행 `(-r.ethics_tier, r.ethics_code)` 유지(Tier 4→1, 구체 우선). ③은 `(r.ethics_tier, r.ethics_code)`(Tier 1→2, 상위 원칙부터) — "단독 인용 금지" 라벨과 정합.
- 헤더는 1-3의 〔정식 인용명〕 형식 + 빈 값 가드. `seen` set 중복 제거는 현행 유지.
- 짧은 하위 준칙(Tier ≥3, 원문 80자 미만)에는 인용 형식 힌트 1줄을 부착해 조문 길이 비대칭을 보정한다(직접 섹션에 한정, 보수적으로).

단위 테스트: (직접 `related_to` 1건 + 롤업 1건) 혼합 입력 → 각각 ②·③ 섹션 배치 assert.

### 1-5. 프롬프트 개편 + max_tokens + Phase 2 캐싱 (1-4 직후)

현행 프롬프트의 검증된 자산(〔 〕 표기, 3종 톤, JSON 형식, "제목으로 시작 금지", 중간제목 최대 3~4개)은 보존하고, 다음을 추가·교체한다.

**(a) 인용 전략 — Bottom-up 복원:**

```
### 규범 인용 전략 (절대 준수)
컨텍스트는 "직접 적용 규범(인용 1순위)" / "직접 참고 규범" / "상위 원칙(단독 인용 금지)"로 나뉩니다.
1. 1순위 — 직접 적용 규범의 구체 조항을 항상 첫 번째 근거로 인용하세요.
2. 2순위 — 직접 참고 규범. 보완이 필요할 때.
3. 3순위 — 상위 원칙. 반드시 하위 규범과 함께만. 상위 원칙 단독 인용은 금지합니다.

나쁜 예: "언론윤리헌장 제1조에 따르면..." (상위 원칙만 반복 인용)
좋은 예: "〔신문윤리실천요강 제3조 4항〕은 '...'고 규정합니다.
        이는 〔언론윤리헌장 제1조〕가 천명하는 원칙을 구체화한 것입니다."

문제점 3건을 지적한다면: 2건은 직접 규범만으로 논증하고, 1건에서만 하위→상위로 확장하세요.
헤더의 〔정식 인용명〕을 그대로 인용하세요. 컨텍스트에 없는 규범명·조항번호를 만들지 마세요.
```

(인용명 변환 지시와 중복되는 기존 지시 2곳은 1곳으로 통합.)

**(b) 분량·구조 명세 — 신규 추가** (현행 프롬프트에는 길이 하한·구조 디렉티브가 일절 없음을 실측 확인. 기존 "### 최대 3~4개" 규칙과 양립):

```
### 분량·구조 명세 (필수 — 하한을 반드시 충족)
- comprehensive(시민용): 900~1,300자
- journalist(기자용): 900~1,300자
- student(학생용): 700~1,100자
구조: 도입 → 핵심 지적 2~3개(각 지적마다 기사 본문 근거 문장 ≥1 + 규범 근거 + 개선 방향) → 종합 평가.
단순 나열이 아니라 각 지적이 (관찰→근거→규범→대안)으로 한 단계씩 쌓이고,
종합 평가는 앞선 지적들을 묶어 한 단계 높은 통찰로 마무리합니다. 분량을 채우기 위한 군더더기는 금지합니다.
```

**(c) max_tokens**: 현행 10,000 유지. Wave 1.5에서 출력 토큰 분포 실측 후 필요 시에만 12,000 상향.

**(d) Phase 2 시스템 프롬프트 캐싱** — `call_sonnet`(L613-619)의 `system`을 블록 배열로 (3,067자 고정 텍스트, SDK `anthropic>=0.49.0` 추가 의존성 없이 지원):

```python
system=[{"type": "text", "text": _SONNET_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]
```

(Phase 1 캐싱은 카탈로그·★마킹 분리 등 프롬프트 구조 개편이 필요하므로 Wave 3 유지.)

### 1-6. report_framing Phase 2 전달 (독립, DB 왕복 0회)

카탈로그 select에 `name`·`report_framing`이 이미 포함·캐시되어 있으므로 신규 쿼리 없이:

1. `PatternMatchResult`에 `pattern_catalog_meta: dict = field(default_factory=dict)` 추가 — `code → {"name": ..., "report_framing": ...}`.
2. Phase 1에서 `_load_pattern_catalog()`(위치: `pattern_matcher.py:103`, active-leaf 필터 L146-152) 결과로 맵 구성. NULL framing 자동 생성 로직(L225-233) 활용.
3. `pipeline.py:162-171`의 haiku_dicts에 2필드 추가 — **방어적 조회 필수** (카탈로그 캐시 미적재·코드 불일치 등 엣지 케이스에서 KeyError 방지):

```python
meta = pm.pattern_catalog_meta.get(d.pattern_code) or {"name": d.pattern_code, "report_framing": ""}
# "pattern_name": meta["name"], "report_framing": meta["report_framing"]
```

4. Phase 2 user 메시지 조립부에서 패턴별 서술 방향으로 출력.

### 1-7. verify_citations — 신규 모듈, Wave 1은 로깅 전용 (독립)

- 공수: 중간 규모 신규 구현. `citation_resolver.py`는 `<cite ref>` 체계의 비활성 레거시라 재사용 불가. `phase_f_scoring.py:30`의 `ETHICS_MARKER_RE = re.compile(r"〔([^〕]+)〕")`만 재사용.
- 동작: 리포트 3종에서 〔…〕 추출 → **`source + article_number` canonical key로 정규화 매칭**. 정규화 규칙: 공백 정리, "①"↔"1항" 등 표기 변형 동치 처리. **title 정규식 파싱 금지**(제1부 3.3 — "제3자 비방과 익명보도 금지" 오인 사례).
- **재시도·차단·경고 일절 없음.** 결과는 1-2에서 만든 `analysis_results.citation_audit` JSONB에 적재만:

```json
{
  "citations": [{"raw": "신문윤리실천요강 제3조 1항", "matched": true,
                  "source": "신문윤리실천요강", "article_number": "제3조 1항"}],
  "unmatched": ["언론인 윤리강령 제3조"],
  "match_rate": 0.92,
  "article_context": "crisis",
  "fallback_used": false
}
```

- `storage.py:487-499`의 `base_record`에 `"citation_audit": citation_audit_payload or None` 키 추가.
- `_infer_article_context` 결과(`article_context`)와 fallback 발동 여부를 같은 payload에 동봉 — Wave 2 선행 게이트(아래 §3)의 데이터 기반이 된다.

### Wave 1 배포 스모크 테스트 체크리스트

1. `/health` 200 응답.
2. 실기사 1건 `/analyze` 전 구간 정상 완료(3종 리포트 + article_analysis 생성).
3. system 블록 배열 호출 정상 — 응답 `usage.cache_creation_input_tokens` / `cache_read_input_tokens` 로깅으로 캐시 동작 확인.
4. `analysis_results.citation_audit`에 신규 행 적재 확인.
5. 〔 〕 헤더에 빈 괄호·내부 코드 노출 0건.

## 2. Wave 1.5 — 측정 명세

### 골든셋 대표성 점검 (선행 절차)

- `article_analysis.articleType`은 자유 텍스트(84건 중 NULL 21건)라 기존 데이터로 context 커버리지 판단 불가.
- 절차: 골든셋 26건 각각에 `_infer_article_context` 오프라인 실행 → 8개 context(조항 수 기준 분포: general 66 / disaster 23 / crisis 21 / election 17 / crime 14 / unification 11 / health 7 / military 2) 커버리지 확인 → **crisis·unification·military 기사가 없으면 해당 유형 기사를 골든셋에 보충**(Wave 2 효과 측정의 전제).
- **CLI 작업 지시 시 주의**: 골든셋 기사 원문은 저장소 안에 없다. 실제 위치는 `/Users/gamnamu/Documents/Golden_Data_Set_Pool/article_texts/`(프로젝트 외부, SESSION_CONTEXT v55 명시) — Claude Code에 측정 작업을 지시할 때 이 경로를 반드시 함께 제공한다.

### 측정 지표

| 구분 | 지표 |
|---|---|
| 구조 | 리포트별 글자수 범위 충족(시민·기자 900~1,300 / 학생 700~1,100), "도입→핵심 지적 2~3개→종합" 구조 보유 |
| 밀도 | 핵심 지적당 기사 근거 문장 ≥1, 종합 평가가 앞선 지적을 수렴(단순 반복 아님) |
| 인용 | **직접 적용 규범 섹션에서 실제 인용된 규범 수 ≥1**(컨텍스트 제공 수가 아니라 리포트 본문 실인용 기준 — 직접 매핑된 Tier 2 실천요강 인용도 동등하게 긍정 신호로 집계해 Tier 3 단일 지표의 편향을 피한다), 상위 원칙 단독 인용 0건, 〔 〕 인용의 source+article_number 매칭률, Tier 3 인용율(추세 지표) |
| 보조 | 출력 토큰 분포(참고용), Duration, fallback 발동 여부 |
| 운영(주간) | 환각률 — 골든셋 합격 지표에서 제외(1.7% 희소 사건은 26건으로 검출 불가). 1-7 citation_audit 누적 기반 주간 모니터링: `match_rate` 추이, `unmatched` 빈출 목록 |

## 3. Wave 2 — Tier 3 매핑 큐레이션 (선행 게이트 포함)

### 선행 하드 게이트 — context 오분류 감사

매핑 0건 source 4종은 전부 맥락 한정(crisis·unification·military)이고, RPC 필터는 `applicable_contexts IS NULL OR 'all' = ANY(...) OR article_context = ANY(...)`이다. 따라서 **기사 context가 'general'로 오추론되면 큐레이션한 조항이 통째로 필터에서 탈락**한다. 특히 crisis 키워드에 '자살'이 없으므로(의도적 보수 설계), '극단적 선택' 등 우회 표현을 쓰지 않은 자살 보도 기사는 general로 떨어질 위험이 실재한다.

**게이트 조건(통과 전 큐레이션 배포 금지):**

1. 골든셋(보충 후)의 crisis·unification·military 기사 각각이 `_infer_article_context`에서 올바른 context로 분류될 것.
2. 1-7에서 적재한 운영 `citation_audit.article_context` 로그에서, 특수 준칙이 필요한 기사가 'general'로 떨어진 사례를 수집·검토할 것.
3. 오분류가 확인되면 키워드 사전 보강(예: '자살' 추가 여부)을 **게이트 측정 결과로 결정** — 측정 없이 키워드를 늘리면 일반 기사 오분류라는 반대 방향 리스크가 생긴다.

### 큐레이션 워크플로 (4단계, 자동 INSERT 금지)

```
[1] 결핍 패턴 식별 — Tier3 violates 0건인 활성 leaf 추출 (70개 추정)
[2] 후보 자동 생성 — 패턴 임베딩 ↔ 규범 임베딩 코사인 유사도, Tier3/4 citable 한정 Top-5,
    검수용 CSV 출력 (SIM_FLOOR 0.30, 자동 INSERT 금지)
[3] 인간 검수 — accept(violates/strong) | accept(violates/moderate) | accept(related_to) | reject
[4] 검수 완료분만 시드 적재 — ON CONFLICT DO NOTHING 멱등,
    reasoning='tier3 expansion 2026-06 (curated)' 마커('parent chain rollup'과 절대 불충돌),
    마이그레이션 파일 + schema_migrations 이력 동시 기록
```

- 우선순위: 매핑 0건 source 4종 → 패턴 20개 단위 배치.
- **'all' 부여 규칙**: 일반 기사에도 적용 가능한 조항만 `applicable_contexts`에 `'all'` 추가 검토(RPC가 이미 지원). 단 **자살·군사·평화통일·감염병·재난 관련 조항은 'all' 부여 금지** — 무관한 기사에 특수 준칙이 인용되는 부적절 인용을 유발한다. 조항별 인간 판단.
- 롤백: `DELETE FROM pattern_ethics_relations WHERE reasoning LIKE 'tier3 expansion%(curated)'`로 정밀 롤백 가능.
- 동반 작업: context 추론 개선(키워드 사전 보강 또는 Phase 1 출력에 `article_context_suggestion` 추가)을 Wave 2와 함께 진행 — 큐레이션 효과가 추론 정확도에 종속되기 때문.

### 데이터 위생 (Wave 2 전후 병행)

- 마이그레이션 드리프트: `pg_get_functiondef`로 운영 RPC와 파일 대조 → 미기록분 이력 보정 → 이후 모든 변경은 파일+이력 동시 기록.

## 4. Wave 3 — 측정 후 결정 항목

| 항목 | 조건 |
|---|---|
| 환각 인용 재시도 트리거 | Wave 1.5 측정에서 잔존 환각이 확인될 때만. 표기 변형 정규화 규칙 선행. `generate_report` 재시도 루프(최대 5회) 재사용 |
| Phase 1 프롬프트 캐싱 | 카탈로그(고정부)와 ★마킹(가변부) 분리 후 적용 — 분리해야 캐시 적중률 확보 |
| Phase 1→2 페이로드 확장(기각 후보 요약) | 1-6 효과 측정 후 |
| Sonnet 4.6↔4.5 교차검증 A/B | 골든셋 벤치마크로 Recall/비용/Duration 측정 후 채택 여부 결정. 측정 없는 도입 금지 |
| threshold 0.15/0.2/0.25 · match_count 7/10/15 A/B | 데이터 검증 후에만 변경. 0.5 인상은 금지 확정 |
| max_tokens 12,000 상향 | Wave 1.5 출력 토큰 분포 실측 후 필요 시 |

## 5. 로드맵 및 완료 판정

```
Wave 1 (1~3일, 코드+마이그레이션 1건)
  1-2 → 1-3 → 1-4 → 1-5 (직렬), 1-1·1-6·1-7 (병렬) → 스모크 테스트
Wave 1.5 (2~3일, 측정)
  골든셋 대표성 점검·보충 → A/B 측정(구 vs 신) → 지표 채점
Wave 2 (1~2주, 데이터 — 검수가 병목)
  하드 게이트 통과 → 후보 생성 → 인간 검수 → 시드 적재 → 재측정
Wave 3 (1주, 최적화)
  측정 결과에 따른 조건부 항목들
```

| 단계 | 완료 판정 |
|---|---|
| Wave 1 | ① Chunk 단위테스트 통과 ② RPC 12컬럼 + 실호출 테스트 통과 ③ 3섹션 배치 단위테스트 통과 ④ 스모크 테스트 5항목 전부 통과 ⑤ 마이그레이션 파일·이력 동시 기록 |
| Wave 1.5 | ① 골든셋 8개 context 커버리지 확인(미달 유형 보충) ② 측정표 산출 — 분량 범위 충족률, 직접 규범 실인용 ≥1 비율, 상위 단독 인용 0건, 매칭률 |
| Wave 2 | ① 하드 게이트 통과 기록 ② Tier3 violates 0건 패턴 70 → 목표 ≤20 ③ 골든셋 재실행 시 직접 규범 실인용 유의 상승 ④ 부적절 맥락 인용('all' 오부여) 0건 |
| Wave 3 | ① 각 항목 채택/기각의 측정 근거 문서화 ② 캐시 적중 로그 확인 ③ Duration < 120s 유지 |

## 6. 맺음

이 개선안의 뼈대는 한 문장으로 요약된다 — **하위 준칙을 공급하고(C), 강등 없이 노출하고(B), 인용하도록 유도한다(A).** 그 위에 인용을 사후 검증하는 데이터 루프(citation_audit)와, 맥락 한정 준칙이 필터에서 증발하지 않게 하는 선행 게이트(context 감사)를 얹었다. 모든 수치·행 번호·스키마는 운영 환경 실측값이므로, 본 문서의 각 절을 단위 그대로 Claude Code CLI에 지시하면 된다. 단 두 가지 원칙만은 어떤 경우에도 유지한다: DB 변경은 수동 실행과 이력 동기화를 함께, 매핑 확장은 인간 검수를 거쳐서.
