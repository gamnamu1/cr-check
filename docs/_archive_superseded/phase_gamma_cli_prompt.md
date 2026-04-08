# Phase γ CLI 지시서 — 매핑 정비 + 모델 교체 실험

## 작업 개요

Phase γ 두 가지 작업을 순서대로 진행한다.
- **작업 A**: `pattern_ethics_relations` 테이블에서 관련성 낮은 매핑 제거/수정
- **작업 B**: Phase 1(패턴 식별) 모델을 Opus 4.6으로 교체하고 A/B 비교

**순서가 중요하다:** 작업 A를 먼저 완료해야 작업 B의 비교가 깨끗한 컨텍스트에서 이루어진다.

---

## 작업 A: 규범 매핑 정비

### A-1. 마이그레이션 파일 생성

`supabase/migrations/20260405000000_cleanup_pattern_ethics_relations.sql` 파일을 생성한다.

**중요:**
- `pattern_ethics_relations` 테이블은 `pattern_id`(BIGINT)와 `ethics_code_id`(BIGINT) 외래키를 사용한다.
- 우리가 아는 것은 문자열 코드(`'1-7-2'`, `'HRG-5-2b'` 등)이므로, `patterns` 테이블과 `ethics_codes` 테이블에서 서브쿼리로 BIGINT ID를 조회하여 DELETE/UPDATE 해야 한다.
- **기존 시드 마이그레이션 파일(`20260328100000_seed_data.sql`)은 절대 수정하지 않는다.**

#### DELETE 대상 (7건) — 패턴과 무관한 규범 매핑 제거

| pattern_code | ethics_code | 제거 이유 |
|---|---|---|
| `1-7-2` | `HRG-5-2b` | 헤드라인 윤리와 무관. 차별 표현 규범은 1-7-5에 이미 매핑됨 |
| `1-7-2` | `PCP-1-4` | 헤드라인 윤리와 무관. 편견 조장은 1-7-5의 영역 |
| `1-7-2` | `PCP-3-3` | 반론권 부여는 균형성(1-3-1) 영역이지 헤드라인 문제 아님 |
| `1-5-2` | `PCP-13-3` | 청소년 유해환경 조성은 개인정보 보호와 직접 무관 |
| `1-5-2` | `PCP-3-6` | 선정성은 1-7-4(자극적·선정적 표현)의 영역 |
| `1-6-1` | `PCP-3-6` | 선정적 묘사는 심층성 부족과 무관 |
| `1-6-1` | `PCP-3-7` | 참혹 장면 보도는 심층성 부족과 무관 |

#### UPDATE 대상 (2건) — strength를 'strong' → 'moderate'로 하향

| pattern_code | ethics_code | 하향 이유 |
|---|---|---|
| `1-7-2` | `PCP-3-6` | 선정적 제목과 간접 관련이나, 이 코드의 원래 맥락은 본문 내 선정적 묘사 |
| `1-7-4` | `PCP-13-3` | 관련은 있으나, 이 규범의 핵심은 청소년 보호이지 선정적 표현 자체가 아님 |

#### SQL 작성 시 참고 패턴 (시드 데이터의 INSERT문과 동일한 JOIN 방식 사용):

```sql
BEGIN;

-- DELETE: 서브쿼리로 BIGINT ID 조회
DELETE FROM public.pattern_ethics_relations
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-7-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'HRG-5-2b' AND version = 1);

-- UPDATE: strength 변경
UPDATE public.pattern_ethics_relations
SET strength = 'moderate'
WHERE pattern_id = (SELECT id FROM public.patterns WHERE code = '1-7-2')
  AND ethics_code_id = (SELECT id FROM public.ethics_codes WHERE code = 'PCP-3-6' AND version = 1);

COMMIT;
```

위 패턴으로 DELETE 7건, UPDATE 2건 모두 작성한다.
`ethics_codes` 조회 시 `AND version = 1` 조건을 반드시 포함한다.

### A-2. 로컬 DB 적용

마이그레이션 파일 생성 후, 로컬 Supabase DB에 적용한다.

```bash
# 로컬 Supabase가 실행 중인지 확인
supabase status

# 마이그레이션 적용 (로컬만)
supabase db reset
```

**주의:** `supabase db push`는 실행하지 않는다 (프로덕션 DB 보호).

### A-3. 적용 확인

적용 후, 변경된 매핑 건수를 확인한다:

```sql
-- 전체 매핑 수 확인 (기대값: 63건 = 기존 70 - 삭제 7)
SELECT COUNT(*) FROM public.pattern_ethics_relations;

-- 삭제 대상이 실제로 없는지 확인
SELECT per.*, p.code AS pattern_code, ec.code AS ethics_code
FROM public.pattern_ethics_relations per
JOIN public.patterns p ON p.id = per.pattern_id
JOIN public.ethics_codes ec ON ec.id = per.ethics_code_id
WHERE (p.code = '1-7-2' AND ec.code IN ('HRG-5-2b', 'PCP-1-4', 'PCP-3-3'))
   OR (p.code = '1-5-2' AND ec.code IN ('PCP-13-3', 'PCP-3-6'))
   OR (p.code = '1-6-1' AND ec.code IN ('PCP-3-6', 'PCP-3-7'));
-- 기대값: 0건 (모두 삭제됨)

-- UPDATE 확인 (strength가 'moderate'인지)
SELECT p.code AS pattern_code, ec.code AS ethics_code, per.strength
FROM public.pattern_ethics_relations per
JOIN public.patterns p ON p.id = per.pattern_id
JOIN public.ethics_codes ec ON ec.id = per.ethics_code_id
WHERE (p.code = '1-7-2' AND ec.code = 'PCP-3-6')
   OR (p.code = '1-7-4' AND ec.code = 'PCP-13-3');
-- 기대값: 2건, 모두 strength = 'moderate'
```

---

## 작업 B: Phase 1 모델 교체 실험 (Opus 4.6 A/B 비교)

### B-1. 기준선 측정 — Sonnet 4.6 (현재 모델)

매핑 정비 적용 후, **기존 Sonnet 4.6 상태에서** 테스트 기사 1건을 돌린다.
이것이 비교의 기준선이 된다.

1. FastAPI 서버 시작:
```bash
cd /Users/gamnamu/Documents/cr-check/backend
uvicorn main:app --reload --port 8000
```

2. 테스트 기사 URL로 분석 실행 (아래 중 1건 선택):
   - 세계일보 이준석: `https://n.news.naver.com/mnews/article/022/0003994271`
   - 나일 외국인 범죄: `https://n.news.naver.com/mnews/article/001/0014918144`

3. `backend/diagnostics/` 에 생성된 진단 JSON에서 아래 항목을 기록:
   - `checkpoint_2_vector.candidate_count` (벡터 후보 수)
   - `checkpoint_3_pattern.validated_pattern_codes` (식별된 패턴)
   - `checkpoint_3_pattern.overall_assessment` (전체 평가)
   - `checkpoint_4_ethics.ethics_ref_count` (규범 조회 수 — 매핑 정비 효과 확인)
   - `total_seconds` (전체 소요 시간)

4. 결과를 `docs/phase_gamma_ab_results.md`에 기록한다:
```markdown
# Phase γ A/B 비교 결과

## 기준선: Sonnet 4.6 (매핑 정비 후)
- 테스트 기사: [URL]
- 벡터 후보: N건
- 식별 패턴: [코드 목록]
- 전체 평가: [assessment]
- 규범 조회: N건
- 소요 시간: N초
```

### B-2. Opus 4.6 교체

**`backend/core/pattern_matcher.py`의 37행만 변경한다:**

```python
# 변경 전
SONNET_MODEL = "claude-sonnet-4-6"

# 변경 후
SONNET_MODEL = "claude-opus-4-6"
```

**주의:**
- `backend/core/report_generator.py`의 모델은 변경하지 않는다 (Sonnet 4.6 유지).
- 즉, Phase 1(패턴 식별)만 Opus, Phase 2(리포트 생성)는 Sonnet 유지.
- 변수명 `SONNET_MODEL`은 그대로 둔다 (파일 전체에서 참조하므로).

### B-3. Opus 4.6 테스트

B-1과 **동일한 테스트 기사**로 다시 분석을 실행한다.

1. 서버가 이미 `--reload`로 실행 중이므로 모델 변경이 자동 반영됨
2. 같은 기사 URL로 분석 실행
3. `backend/diagnostics/`에 새로 생성된 진단 JSON에서 동일 항목 기록

`docs/phase_gamma_ab_results.md`에 추가:

```markdown
## 실험: Opus 4.6 (Phase 1만)
- 테스트 기사: [동일 URL]
- 벡터 후보: N건
- 식별 패턴: [코드 목록]
- 전체 평가: [assessment]
- 규범 조회: N건
- 소요 시간: N초

## 비교 분석
- 패턴 식별 차이: [있으면 상세 기술]
- 소요 시간 차이: N초 → N초
- 품질 차이 소견: [자유 서술]
```

### B-4. 결과 보고 후 대기

**A/B 비교 결과를 보고하고, Opus 4.6을 최종 채택할지 여부는 Gamnamu 승인을 받는다.**
승인 없이 자율적으로 최종 결정하지 않는다.

---

## 제약 조건

1. `supabase db push` 실행 금지 (프로덕션 DB 보호)
2. `git commit`, `git push`, `git add` 실행 금지 (승인 게이트)
3. `rm`, `mv`, `sed -i`, `chmod` 실행 금지
4. 기존 시드 마이그레이션 파일 수정 금지
5. `report_generator.py`의 모델 변경 금지 (Sonnet 4.6 유지)
6. Reserved Test Set 73건 참조 금지
7. 벤치마크 결과 파일 삭제 금지
8. deprecated 코드 삭제 금지
9. 모든 작업은 `feature/m6-wip` 브랜치에서 진행

## 참고 파일 경로

- 마이그레이션 디렉토리: `supabase/migrations/`
- 패턴 매처: `backend/core/pattern_matcher.py` (37행: `SONNET_MODEL`)
- 리포트 생성기: `backend/core/report_generator.py` (변경 금지)
- 파이프라인: `backend/core/pipeline.py`
- 진단 출력: `backend/diagnostics/`
- 시드 데이터: `supabase/migrations/20260328100000_seed_data.sql` (수정 금지)
- 스키마: `supabase/migrations/20260328000000_create_cr_check_schema.sql`
- 세션 컨텍스트: `docs/SESSION_CONTEXT_2026-04-05_v21.md`
