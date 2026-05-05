# CR-Check 마스터 실행 계획 v1.0

> **문서 상태**: Active — Single Source of Truth
> **작성일**: 2026-04-28
> **이 문서 하나로 모든 후속 작업을 실행한다.**

---

## 0. 이 문서를 읽는 방법

**[기획자 Gamnamu]**: §1(배경·목표) → §2(절대 원칙) → 현재 STEP 순으로 읽는다.
**[Claude.ai 감독]**: 전체 통독 후 기획자 질문에 답하고, STEP별 CLI 프롬프트를 제공한다.
**[Claude Code CLI]**: 기획자 또는 Claude.ai가 전달하는 "CLI 실행 지시" 블록만 읽는다.
단계를 임의로 묶거나 앞질러 실행하는 것을 절대 금지한다.

---

## 1. 배경 및 목표

### 1.1 현재 기준선 (2026-04-25, R5 고정)

| 항목 | 상태 |
|---|---|
| 프로덕션 커밋 | `1795eb0` (feature/fix-generate-embeddings-script) |
| Phase 1 프롬프트 | R5 — 이진 게이트 제거 + 독립 패턴 평가 |
| 벤치마크 | FR 36.7% / Precision 44.2% / TN FP Rate 6/6 |
| 골든셋 | TP 21 + TN 5 = 26건 |
| 패턴 수 | patterns 테이블 38건 (대분류 8 / 소분류 28 / 메타 2) |

### 1.2 근본 원인 진단

세 가지 구조적 문제가 누수를 발생시키고 있다.

**(A) DB 레이어 — 패턴 과압축**
38개 소분류 description 안에 여러 독립 개념이 뭉쳐 있다.
임베딩 벡터 방향이 분산되어 Sonnet이 패턴 간 경계를 모호하게 인식한다.
프롬프트 패치로는 해결 불가능한 데이터 구조 문제다.
→ R6·R7 실험에서 가드 규칙 추가 시 오히려 FR이 R4보다 낮아진 것으로 확인됨.

**(B) 벡터 검색 — 전략 미분화**
"부재 감지" 유형 패턴(반론 없음, 맥락 누락 등)은 임베딩 유사도로 소환이 근본적으로 불가능하다.
이 패턴들을 벡터 검색 대상에 포함하면 임베딩 공간에 노이즈가 생긴다.

**(C) 윤리규범 조회 — 맥락 무관 발동**
related_to/weak 관계 규범이 Sonnet 컨텍스트에 무조건 포함된다.
기사 유형과 무관한 특수 맥락 규범(감염병보도준칙 등)이 발동된다.

### 1.3 단계별 성능 목표

| 지표 | 현재(R5) | STEP 4 후 | STEP 5 후 | STEP 7 후 |
|---|---|---|---|---|
| Recall (FR) | 36.7% | 45% | 60% | 75% |
| Precision | 44.2% | 55% | 70% | 80% |
| TN FP Rate | 6/6 | 5/6 이하 | 4/6 이하 | 3/6 이하 |

> 전 단계 목표 미달 시 다음 STEP 진입 금지.

### 1.4 이 계획이 다루는 범위

```
[STEP 0] 사전 정리 — 패턴·규범 DB 정리 (문서·판단 작업)
[STEP 1] 119개 패턴 코드 체계 설계 (표 출력만, DB 변경 없음)
[STEP 2] DB 마이그레이션 (search_text + 신규 컬럼 + 트리거 + 119개 INSERT)
[STEP 3] pattern_ethics_relations 재배분
[STEP 4] 코드 품질 개선 (_build_ethics_context + RPC + snapshot)
[STEP 5] Sonnet 프롬프트 재설계 (카탈로그 형식 + 혼동 쌍 DB화 + 메타패턴 코드 정리)
[STEP 6] 임베딩 재생성 (search_text + detection_strategy 필터)
[STEP 7] 골든셋 재정비 + R8 벤치마크 + threshold 재조정
```

---

## 2. 절대 원칙

1. **CLI 자동 INSERT/UPDATE 금지** — 모든 DB 변경은 기획자가 SQL Editor에서 직접 실행
2. **diff 선제시 → 기획자 승인 → 커밋** 순서 엄수 (자동 git add/commit 금지)
3. **STEP 단위 승인 게이트** — 기획자 승인 없이 다음 STEP 진행 절대 금지
4. **단계 임의 통합 금지** — CLI는 전달받은 단계 지시만 실행, 앞질러 실행하거나 단계를 묶지 않는다
5. **TN FP Rate 50% 이하 유지** — 초과 시 해당 변경 즉시 롤백
6. **ON CONFLICT DO NOTHING** — UPSERT 절대 금지
7. **is_citable 일괄 변경 금지** — 실질 내용 확인 후 개별 판단
8. **STEP마다 분포 확인 쿼리 2개 의무 실행** — 총량만으로 PASS 불가

---

## 3. 역할 분담

**[기획자 Gamnamu]** 최종 결정권자·큐레이터
- STEP 승인 게이트 Go/No-Go 결정
- Supabase SQL Editor에서 모든 INSERT/UPDATE 직접 실행
- STEP 0 판단 작업 직접 수행 (CLI 단독 실행 불가)
- §12 수동 평가(리포트 품질 기준선 수립) 직접 수행

**[Claude.ai]** 감독·감리 — 코칭 파트너
- 방향 설계 및 단계 분할
- CLI에 전달할 STEP별 프롬프트 제공
- SQL 초안 작성 (최종 실행은 기획자)
- 감리 의견 취합 및 합의 판단

**[Claude Code CLI]** 실행 에이전트
- 전달받은 단계 지시만 실행 (임의 확장 금지)
- 코드 파일 수정 시 diff 선제시 필수
- 벤치마크 스크립트 실행 + 결과 보고
- Deny List: `supabase db push`, `supabase db migration`, `git commit`, `git push`, `git add`, `rm`, `mv`, `sed -i`, `chmod`

**[Antigravity]** 독립 감리 — 로컬 구조 감리
- 로컬 파일 직접 접근, 코드·설계 구조 검토
- 마이그레이션 SQL 구조 검증
- Strict Mode On, Agent Auto-Fix Lints Off

**[Gemini / Manus]** 보조 감리
- Gemini: 한국 언론 현장 어휘, search_text 어휘 적절성
- Manus: 패턴 간 어휘 충돌·중복 분석

---

## 4. 현재 파이프라인 (R5 기준)

```
기사 URL
  → ② 캐시 조회 (storage.py · normalize_url)
      캐시 히트 시 → ⑩ 결과 표시 (즉시 반환)
  → ③ 스크래핑 (scraper.py · 59개 전용 파서)
  → ④ 청킹 + 임베딩 + 벡터 검색
       chunker.py (7단계) → text-embedding-3-small
       → search_pattern_candidates (threshold=0.2, Top-7)
  → ⑤ Sonnet Solo 패턴 감지 (Phase 1)
       claude-sonnet-4-5-20250929, temp=0.0
       패턴 카탈로그 28개 + ★ 힌트 + 구조적 판단 4개 고정
       패턴 미감지 시 → TN (_TN_MESSAGE, pipeline.py)
  → ⑥ 메타패턴 추론 — 비활성 (inferred_by 0건)
  → ⑦ 윤리규범 조회 (fetch_ethics_for_patterns)
  → ⑧ Sonnet 리포트 생성 (Phase 2) — 3종 JSON 반환
  → ⑨ DB 저장 + share_id 발급
  → ⑩ 결과 표시
```

---

## 5. 핵심 설계 결정 (변경 불가)

- Sonnet Solo 1-Call 구조 유지 (Haiku 2-Call 복귀 없음)
- TN 케이스: `pipeline.py`의 `_TN_MESSAGE` 정적 메시지 사용
- 인용 방식: 〔규범 원문〕 마커 직접 출력 (`<cite>` 태그 폐기 확정)
- 이진 게이트: 제거 확정 (R5)
- 메타패턴 추론 (⑥): 완전 비활성화 확정
- GitHub 커밋: 사람이 직접 수행

---

## 6. STEP 0 — 사전 정리 (패턴·규범 DB 판단)

> **성격**: CLI 단독 실행 불가. 항목 단위 검토·판단이 필요한 작업.
> Claude.ai 세션에서 기획자와 함께 진행한다.
> 결과물(확정 목록)은 STEP 2 마이그레이션에 합산된다.

### STEP 0-A: 패턴(patterns) 정리

**비활성화 확정 항목**

| 패턴 코드 | 패턴명 | 사유 |
|---|---|---|
| 4-1 | 외부 압력에 의한 왜곡 | 메타패턴 추론 비활성화. 기사 텍스트만으로 판단 불가 |
| 4-2 | 상업적 동기에 의한 왜곡 | 동일 사유 |

**메타 패턴 비활성화 시 코드 정리 범위** (STEP 5에서 처리)
- `pipeline.py`: `check_meta_patterns()` 호출 블록 DEPRECATED 처리
- `report_generator.py`: `_build_meta_pattern_block()` 함수 DEPRECATED 처리
- `meta_pattern_inference.py`: 전체 파일 DEPRECATED 처리 (삭제 아님)

**119개 각 패턴 검토 기준** (STEP 1과 병행)

아래 세 질문에 모두 "예"일 때만 활성화 유지:
1. 기사 텍스트만으로 감지 가능한가? (외부 정보 없이)
2. Sonnet이 "구체적 문장을 특정"할 수 있는가?
3. 일반 독자에게 의미 있는 지적인가?

**detection_strategy 컬럼 설계** (STEP 2 마이그레이션에서 추가)

| 값 | 의미 |
|---|---|
| `vector` | 임베딩 검색 대상 (기본값) |
| `structural` | 벡터 제외, Sonnet 고정 필수 검토 목록 |

structural 초기 목록:

| 패턴 코드 | 분류 사유 |
|---|---|
| 7-2 | 제목-본문 구조 비교 → 개별 문장 유사도 무의미 |
| 3-1 | 반론의 "부재" 감지 → 없는 텍스트 임베딩 불가 |
| 6-1 | 맥락·배경의 "부재" 판단 → 동일 사유 |
| 3-4 | 기사 전체 프레임 판단 → 개별 문장 유사도 부적합 |

**STEP 2 마이그레이션에 추가할 신규 컬럼** (DB에 현재 없는 것만)

| 컬럼 | 타입 | 기본값 | 목적 |
|---|---|---|---|
| `is_active` | BOOLEAN | TRUE | 비활성화 관리 (현재 is_meta_pattern으로만 처리) |
| `detection_strategy` | TEXT | 'vector' | 검색 전략 구분 |
| `report_framing` | TEXT | NULL | Sonnet 리포트 서술 방향 힌트 |
| `search_text` | TEXT | NULL | 벡터 임베딩 소스 (기사 관찰 어휘 중심) |

> `hierarchy_level`과 `parent_pattern_id`는 이미 존재. 중복 생성 금지.

**STEP 0-A 산출물** (기획자가 직접 작성 또는 승인)
- [ ] 활성화 패턴 확정 목록 (코드 + detection_strategy + report_framing 초안)
- [ ] 비활성화 패턴 목록 (코드 + 사유)

---

### STEP 0-B: 윤리규범(ethics_codes) 정리

**현황**
- is_active=true, is_citable=true 기준 375건
- Tier 분포: Tier1(9) / Tier2(105) / Tier3(254) / Tier4(7)

**현재 문제**
1. 특수 맥락 규범(감염병보도준칙 등)이 기사 유형 무관하게 발동
2. `related_to/weak` 규범이 Sonnet 컨텍스트에 무조건 포함 → 노이즈
3. 명목적 선언 조항이 is_citable=true 상태로 방치

**각 조항 검토 기준**
1. 이 조항을 기사에 실제로 적용할 수 있는가?
2. 적용 가능하다면, 어떤 기사 유형에서인가?
3. 상위 조항과 내용이 중복되는가? (중복이면 하위만 활성화)

**applicable_contexts 컬럼 설계** (STEP 2 마이그레이션에서 추가)
- NULL이면 `all` 컨텍스트로 간주 (하위 호환)
- 예: `'{general}'`, `'{health,disaster}'`, `'{crime}'`

**확정 컨텍스트 값 목록** (STEP0B_ETHICS_PLAN §3 참조 — 2026-05-01 교차 감리 확정):
NULL(all) / `{general}` / `{health}` / `{military}` / `{election}` /
`{crisis}` / `{disaster}` / `{unification}` / `{crime}`

**strength 필터링 정책 확정**

| relation_type | strength | Sonnet 컨텍스트 포함 |
|---|---|---|
| violates | strong | ✅ 핵심 섹션 |
| violates | moderate | ✅ 핵심 섹션 |
| related_to | moderate | ⚠️ 참고 규범 섹션으로 분리 |
| related_to | weak | ❌ 제외 (RPC 레벨 필터) |

**STEP 0-B 산출물** (기획자가 직접 작성 또는 승인)
- [ ] 규범별 applicable_contexts 레이블 목록
- [ ] 규범별 is_citable 재조정 목록

---

## 7. STEP 1 — 119개 패턴 코드 체계 설계

> **선행 조건**: STEP 0-A 착수 (병행 가능)
> **실행 환경**: Claude Code CLI
> **산출물**: 표 출력만. 파일 생성·DB 변경 없음.

### 코드 체계 원칙

기존 38개 소분류 코드(1-1, 1-2 …)를 상위 코드로 유지한다.
각 소분류 안의 개별 불릿을 하위 코드로 확장한다.

```
형식: {기존 소분류 코드}-{알파벳 소문자}
예시:
  1-1 (사실 검증 부실) ← 상위 유지 (hierarchy_level=2)
    1-1-a: 교차 검증 부재 및 단일 취재원 의존
    1-1-b: 취재원 발언의 무비판적 중계
    1-1-c: 인용 정보의 출처 및 신뢰성 문제
    1-1-d: 반론권 미보장
```

### CLI 실행 지시

```
docs/current-criteria_v2_active.md를 읽어라.

각 소분류(### 섹션) 아래 불릿 항목을 1-1-a, 1-1-b 형식으로 코드화하라.
다음 형식의 표를 출력하라:

| 신규 코드 | 상위 코드 | 개념명 |
|---|---|---|
| 1-1-a | 1-1 | 교차 검증 부재 및 단일 취재원 의존 |
| ... | ... | ... |

총 건수를 확인하고 기획자에게 승인을 요청하라.
파일 생성이나 DB 변경은 하지 마라.
```

### 승인 게이트 (STEP 1)

기획자 확인 포인트:
- (A) `current-criteria_v2_active.md` 원본과 비교 — 누락 없는가
- (B) 경계 모호 불릿 — 소분류 귀속 처리가 타당한가
- (C) 코드 명명 — 1-1-a 형식이 전체에 걸쳐 일관되게 적용됐는가
- (D) 확장성 — 새 개념 추가 시 자연스럽게 수용 가능한가

교차 감리: Claude.ai + Antigravity + Gemini/Manus 중 1인.
2인 이상 독립 지적 = 수정 필수. 1인 단독 = 기획자 판단.

---

## 8. STEP 2 — DB 마이그레이션

> **선행 조건**: STEP 1 승인 완료 + STEP 0-A/B 산출물 확정
> **실행 환경**: SQL 초안은 CLI, 실행은 기획자 SQL Editor
> **합산 내용**: Phase H STEP 2 + Phase 1-A + Phase 1-B

### 8.1 신규 컬럼 추가 SQL

```sql
-- patterns 테이블
ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS search_text TEXT;
ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS detection_strategy TEXT DEFAULT 'vector';
ALTER TABLE public.patterns ADD COLUMN IF NOT EXISTS report_framing TEXT;

-- 메타 패턴 비활성화
UPDATE public.patterns SET is_active = FALSE WHERE is_meta_pattern = TRUE;

-- structural 패턴 4종 지정
UPDATE public.patterns SET detection_strategy = 'structural'
  WHERE code IN ('7-2', '3-1', '6-1', '3-4');

-- ethics_codes 테이블
ALTER TABLE public.ethics_codes ADD COLUMN IF NOT EXISTS applicable_contexts TEXT[];
```

### 8.2 updated_at 트리거 추가

```sql
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER handle_updated_at
  BEFORE UPDATE ON public.patterns
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- ethics_codes, pattern_ethics_relations 동일 적용
```

### 8.3 119개 패턴 INSERT

STEP 1 승인 후 CLI가 전체 INSERT SQL 초안 생성.

```sql
-- 구조 예시 (STEP 1 승인 후 CLI가 전체 생성)
INSERT INTO public.patterns
  (code, name, description, search_text, category, subcategory,
   hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES
  ('1-1-a', '교차 검증 부재 및 단일 취재원 의존',
   '복수의 독립적 취재원을 통한 사실 확인 없이 단일 취재원에 의존하는 보도 관행.',
   '단독 취재원, 단일 출처, 교차 검증 없음, 반론 없이, 한쪽 주장만',
   '진실성', '사실 검증 부실', 3,
   (SELECT id FROM patterns WHERE code='1-1'),
   TRUE, 'vector', FALSE, 'ko-KR')
ON CONFLICT DO NOTHING;
```

### 8.4 applicable_contexts 및 is_citable 업데이트

STEP 0-B 확정 목록을 기반으로 CLI가 시드 파일 초안 생성.
파일명: `supabase/seeds/ethics_codes_context_seed.sql`

### 8.5 CLI 실행 지시

```
다음 작업을 순서대로 수행하라.

1. 아래 파일들을 순서대로 읽어라:
   - docs/MASTER_EXECUTION_PLAN_v1.0.md (§8.1~8.4)
   - docs/current-criteria_v2_active.md
   - STEP 1에서 승인된 119개 코드 체계 표
   - STEP 0-A 확정 목록 (detection_strategy, report_framing 초안)
   - STEP 0-B 확정 목록 (applicable_contexts, is_citable 재조정)

2. supabase/migrations/ 디렉토리에 마이그레이션 파일을 생성하라.
   파일명: {timestamp}_master_migration.sql
   내용: §8.1 컬럼 추가 SQL + §8.2 트리거 SQL

3. 119개 패턴 INSERT SQL을 별도 시드 파일로 작성하라.
   파일명: supabase/seeds/patterns_119_seed.sql
   description: STEP 0-A 확정 목록의 report_framing 초안 반영
   search_text: STEP 0-A 확정 목록 반영

4. applicable_contexts + is_citable 업데이트 SQL을 시드 파일로 작성하라.
   파일명: supabase/seeds/ethics_codes_context_seed.sql

5. 위 파일들을 작성만 하고 실행하지 마라.
   커밋은 사람이 직접 수행한다.
```

### 승인 게이트 (STEP 2) — 의무 확인 쿼리

```sql
-- 쿼리 1: 패턴 계층 분포
SELECT hierarchy_level, COUNT(*) FROM patterns
GROUP BY hierarchy_level ORDER BY hierarchy_level;
-- 기대: level=1 → 8건, level=2 → 38건, level=3 → ~119건

-- 쿼리 2: search_text 공백 여부
SELECT COUNT(*) FROM patterns
WHERE hierarchy_level=3 AND (search_text IS NULL OR search_text='');
-- 기대: 0건

-- 쿼리 3: is_active + detection_strategy 분포
SELECT is_active, detection_strategy, COUNT(*)
FROM patterns GROUP BY is_active, detection_strategy;
-- 기대: is_active=false → 2건(메타), structural → 4건 이상

-- 쿼리 4: applicable_contexts 입력 여부
SELECT COUNT(*) FROM ethics_codes WHERE applicable_contexts IS NOT NULL;
```

교차 감리: Antigravity (마이그레이션 SQL 구조 검증) + Gemini (search_text 어휘).

---

## 9. STEP 3 — pattern_ethics_relations 재배분 ✅ 완료 (2026-05-03)

> **선행 조건**: STEP 2 완료 및 기획자 승인
> **실행 환경**: Claude.ai + 기획자 SQL Editor
> **완료 일자**: 2026-05-03

### 목표

기존 매핑을 107개 새 패턴(leaf) 기준으로 재배분.
38개 상위 패턴에 연결된 매핑을 적절한 하위 패턴으로 이전.

### 원칙

- strength 3-카테고리 유지: strong / moderate / weak
- 하위 패턴에 배분 불가능한 매핑은 상위 패턴에 그대로 유지
- 신규 하위 패턴에 추가 매핑 필요 시 큐레이션 (기획자 판단)

### 실제 실행 결과 (계획 대비 차이 포함)

**Phase 1 — 현황 파악 발견사항**

- 계획 기준 매핑 건수: 63건 → **실제 DB: 111건** (레거시 DB 전용 소분류 7건 포함)
- DB 전용 소분류 7건 (v3 체계 미정의): `5-4`, `7-3`, `7-4`, `7-5`, `7-6`, `8-1`, `8-2`
- DB·v3 의미 충돌 소분류 9건: 동일 코드가 DB와 v3에서 다른 개념 지칭
- inactive 부모 2건(`4-1`, `4-2`) 매핑 7건 잔존 확인
- `hierarchy_level=2` 비어 있음 → 부모·leaf 모두 level=3에 위치

**Phase 2 — 내려보내기 (Batch 1~3)**

| 배치 | 내용 | 결과 |
|---|---|---|
| Batch 1 | 4-1·4-2 오연결·메타 선언 조항 DELETE | 6건 삭제 |
| Batch 2 | DB 전용 소분류 7건 → v3 leaf 귀속 | 27건 INSERT (신규 22건) |
| Batch 3 | 의미 충돌 소분류 6건 → v3 leaf 귀속 | 20건 INSERT (신규 14건) |

**Phase 3 — 빈 leaf 채우기 (Batch 4~6)**

- 활성 leaf 76개 중 58개가 매핑 0건 → 특화 준칙 조항 신규 큐레이션
- EPG(선거여론조사), DRG(재난보도), SPG·SRE(자살보도), PCP-5(취재원), PCP-7(피의자) 등 특화 조항 다수 발굴
- 총 126건 INSERT

**최종 검증 결과**

| 검증 항목 | 목표 | 결과 |
|---|---|---|
| 활성 leaf 전원 매핑 | cnt ≥ 1 | 76/76 전부 ≥ 1 ✅ |
| PCP 편중 완화 | 60% 이하 | **44.6%** (목표 초과 달성) ✅ |

### 승인 게이트 (STEP 3) — 의무 확인 쿼리

> **주의**: `hierarchy_level=3` 필터가 실제 DB에서 동작하지 않음.
> `hierarchy_level` 컬럼이 부모·leaf 모두 3으로 저장되어 있으므로
> 정규식 필터로 대체할 것.

```sql
-- 쿼리 1: 공백 패턴 확인 (정규식 필터 사용)
SELECT p.code, p.name, COUNT(per.id) AS cnt
FROM patterns p
LEFT JOIN pattern_ethics_relations per ON p.id = per.pattern_id
WHERE p.is_active = TRUE
  AND p.code ~ '^[0-9]+-[0-9]+-[a-z]+$'
GROUP BY p.id, p.code, p.name
ORDER BY cnt ASC;
-- 기대: 모든 활성 leaf cnt ≥ 1

-- 쿼리 2: 소스별 분포
SELECT ec.source, COUNT(*) AS cnt,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM pattern_ethics_relations per
JOIN ethics_codes ec ON per.ethics_code_id = ec.id
GROUP BY ec.source ORDER BY cnt DESC;
-- 기대: PCP 편중 60% 이하 (실제 달성: 44.6%)
```

교차 감리: Claude.ai + 5인 독립 감리자 (Antigravity·Gemini·Manus·NotebookLM·Perplexity).
감리 단계마다 동일 프롬프트로 교차 검증 수행 (교차 감리 원칙 적용).

---

## 10. STEP 4 — 코드 품질 개선

> **선행 조건**: STEP 3 완료 및 기획자 승인
> **실행 환경**: Claude Code CLI

### STEP 4-A: _build_ethics_context() 구조화

**문제**: ethics_context 문자열에서 직접 매핑 조항과 롤업 조항이 구분되지 않아
Sonnet의 롤업 지시 실행이 불안정하다.

```python
# 현행: 구분 없이 나열
# 목표: 두 그룹 분리

# primary: relation_type='violates' (strong + moderate)
# reference: relation_type='related_to' AND strength='moderate'
#   (strength='weak'는 STEP 4-C RPC에서 필터링)

# 출력 예시:
# [직접 연결] PCP-3-1 (Tier 2) — 보도기사의 사실과 의견 구분
# ---
# ## 참고 규범 (직접 인용보다 맥락 이해용)
# [상위 원칙] JEC-1 (Tier 1) — 진실을 추구한다
```

### STEP 4-B: analysis_ethics_snapshot 재활성화

```python
# Phase 2 리포트 생성 직후 report_generator.py에서
# 리포트 본문에 실제 인용된 ethics_code를 문자열 검색으로 추출
# → analysis_ethics_snapshot 테이블에 INSERT
# CitationResolver 없이 구현 가능 (기존 ethics_refs 활용)
```

### STEP 4-C: get_ethics_for_patterns RPC 수정 (applicable_contexts 필터 추가)

**articleType 시퀀싱 문제**: Phase 2 Sonnet의 articleType 출력이 RPC 시점보다 늦으므로
RPC 인자로 사용 불가. 대신 기사 텍스트 키워드 휴리스틱으로 사전 추정.

```python
def _infer_article_context(article_text: str, pattern_codes: set) -> str:
    """
    기사 원문 키워드 + 확정 패턴 코드로 기사 맥락을 사전 추정.
    반환값: 'health' | 'disaster' | 'crisis' | 'crime' |
            'election' | 'military' | 'unification' | 'general'

    ※ 2026-05-01 STEP 0-B Phase 1 확정 컨텍스트 9개와 1:1 대응하도록 확장.
       이전 'court' 반환값은 폐기, 'crime'으로 통합.
       키워드 사전은 STEP 7 골든셋 재정비 시점에 성능 기반으로 재조정.
    """
    text_sample = article_text[:500]

    health_keywords      = ['감염병', '코로나', '백신', '의료', '병원', '질병', '바이러스']
    disaster_keywords    = ['재난', '지진', '화재', '홍수', '사고', '피해', '구조']
    crisis_keywords      = ['자살', '극단적 선택', '자해', '유서', '투신']
    crime_keywords       = ['재판', '판결', '검찰', '기소', '법원', '피의자', '피고인', '수사']
    election_keywords    = ['선거', '여론조사', '후보', '투표', '당선', '공약']
    military_keywords    = ['군사', '작전', '국방', '군대', '병력', '북한 도발']
    unification_keywords = ['남북', '통일', '북한', '조선민주주의인민공화국', '평화통일']

    if any(kw in text_sample for kw in health_keywords):      return 'health'
    if any(kw in text_sample for kw in disaster_keywords):    return 'disaster'
    if any(kw in text_sample for kw in crisis_keywords):      return 'crisis'
    if any(kw in text_sample for kw in crime_keywords):       return 'crime'
    if any(kw in text_sample for kw in election_keywords):    return 'election'
    if any(kw in text_sample for kw in military_keywords):    return 'military'
    if any(kw in text_sample for kw in unification_keywords): return 'unification'
    return 'general'
```

RPC 수정 방향:
- `article_context TEXT DEFAULT 'general'` 파라미터 추가
- 필터: `applicable_contexts IS NULL OR 'all' = ANY(applicable_contexts) OR article_context = ANY(applicable_contexts)`
- `strength='weak' AND relation_type='related_to'` 제외
- REST API fallback에도 동일 필터 적용 (Antigravity 지적사항)

### CLI 실행 지시 (STEP 4)

```
다음 작업을 순서대로 수행하라.

1. 다음 파일들을 읽어라:
   - backend/core/report_generator.py (전체)
   - backend/core/pipeline.py (전체)

2. report_generator.py의 _build_ethics_context()를 수정하라:
   - EthicsReference를 primary / reference 두 그룹으로 분리
   - primary: relation_type='violates' (strong + moderate), Tier 역순 정렬
   - reference: relation_type='related_to' AND strength='moderate'
   - reference 헤더: "## 참고 규범 (직접 인용보다 맥락 이해용)"
   - reference가 비어 있으면 섹션 전체 생략

3. pipeline.py에 _infer_article_context() 함수를 추가하라 (위 설계 참고).
   generate_report() 호출 직전에 article_context 추론을 삽입하라.

4. supabase/migrations/{timestamp}_rpc_ethics_context_filter.sql 파일을 생성하라:
   - get_ethics_for_patterns RPC에 article_context TEXT DEFAULT 'general' 추가
   - applicable_contexts 필터 추가
   - strength='weak' AND relation_type='related_to' 제외 조건 추가

5. fetch_ethics_for_patterns() 시그니처에 article_context 추가하고
   REST API fallback에도 동일 필터를 적용하라.

6. pipeline.py의 analysis_ethics_snapshot INSERT 로직을 재활성화하라.
   CitationResolver 없이 리포트 본문 문자열 검색으로 구현하라.

7. 모든 변경사항을 diff로 선제시하고 기획자 승인을 기다려라.
   실행·커밋 금지.
```

### 승인 게이트 (STEP 4)

- 리포트 샘플 5건에서 primary/reference 섹션 구분 확인
- 롤업 출현 여부 확인 (5건 중 3건 이상)
- 분석 1건 실행 후 analysis_ethics_snapshot 테이블 기록 확인
- REST API fallback에서도 applicable_contexts 필터 동작 확인

교차 감리: Claude.ai + 기획자 직접 확인.

---

## 11. STEP 5 — Sonnet 프롬프트 재설계

> **선행 조건**: STEP 4 완료 및 기획자 승인
> **실행 환경**: Claude Code CLI
> **주의**: DB에 detection_strategy, report_framing 데이터 입력 완료 전제

### STEP 5-A: 패턴 카탈로그 형식 재설계

**문제**: 119개 패턴이 평면 나열되면 Sonnet attention이 분산된다.
계층 경로와 report_framing 힌트가 없어 리포트 서술 깊이가 불안정하다.

목표 카탈로그 항목 형식:
```
[{code}] {name}
계층 경로: {대분류명} > {중분류명} > 현재 패턴
감지 힌트: {description 또는 search_text}
리포트 서술 방향: {report_framing}
```

structural 패턴은 별도 섹션으로 분리:
```
## 구조적 판단 필수 검토 패턴 (★ 마크 무관 항상 직접 검토)
```
→ 하드코딩 제거, DB 조회로 동적 로드.

### STEP 5-B: 혼동 쌍 DB화

현재 5개 혼동 쌍이 `_SONNET_SOLO_PROMPT`에 하드코딩되어 있다.
별도 테이블로 분리하여 관리성을 높인다.

```sql
-- CLI가 생성, 기획자가 실행
CREATE TABLE IF NOT EXISTS pattern_confusion_pairs (
  id         BIGSERIAL PRIMARY KEY,
  code_a     TEXT NOT NULL,
  code_b     TEXT NOT NULL,
  distinction_guide TEXT NOT NULL,
  is_active  BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### STEP 5-C: 메타패턴 코드 DEPRECATED 처리

```python
# pipeline.py — check_meta_patterns() 호출 블록 전체:
# [DEPRECATED] 메타 패턴 추론 비활성화 (Phase I, 2026-04-28)
# inferred_by 관계 0건. 데이터 없이 운용 불가. 재활성화 시 주석 해제.

# report_generator.py — _build_meta_pattern_block() 함수 상단:
# [DEPRECATED] 메타 패턴 비활성화로 이 함수는 현재 호출되지 않음.

# meta_pattern_inference.py — 파일 상단:
# [DEPRECATED MODULE] 메타 패턴 추론 비활성화 (Phase I, 2026-04-28)
```

### CLI 실행 지시 (STEP 5)

```
다음 작업을 순서대로 수행하라.

1. 다음 파일들을 읽어라:
   - backend/core/pattern_matcher.py (전체)
   - backend/core/pipeline.py (check_meta_patterns 관련 부분)
   - backend/core/report_generator.py (_build_meta_pattern_block 관련 부분)
   - meta_pattern_inference.py (파일 상단)

2. pattern_matcher.py의 패턴 카탈로그 로드 쿼리를 수정하라:
   SELECT p.id, p.code, p.name, p.description, p.search_text,
          p.detection_strategy, p.report_framing,
          p.hierarchy_level, p.parent_pattern_id,
          parent.code AS parent_code, parent.name AS parent_name,
          grandparent.name AS grandparent_name
   FROM patterns p
   LEFT JOIN patterns parent ON p.parent_pattern_id = parent.id
   LEFT JOIN patterns grandparent ON parent.parent_pattern_id = grandparent.id
   WHERE p.is_active = TRUE AND p.is_meta_pattern = FALSE

3. _build_pattern_catalog_entry(row) 헬퍼 함수를 새로 작성하라:
   - detection_strategy='vector'인 패턴: 목표 형식 텍스트 블록 반환
   - report_framing이 NULL이면: "구체 패턴({code}) 지적 → {parent_name} 맥락으로 확장" 자동 생성

4. detection_strategy='structural' 패턴을 별도 섹션으로 분리하라.
   하드코딩된 4개 목록을 DB 조회 결과로 대체하라.

5. supabase/migrations/{timestamp}_pattern_confusion_pairs.sql을 작성하라.
   기존 5개 혼동 쌍을 시드 파일(pattern_confusion_pairs_seed.sql)로 작성하라.
   _load_confusion_pairs() 함수를 추가하고 프롬프트의 하드코딩 섹션을 대체하라.

6. STEP 5-C 지시에 따라 세 파일에 DEPRECATED 주석을 추가하라.
   삭제는 금지한다.

7. 비활성화 후 파이프라인 E2E 테스트를 실행하여 오류 없음을 확인하라.

8. 모든 변경사항을 diff로 선제시하고 기획자 승인을 기다려라.
```

### 승인 게이트 (STEP 5)

- 계층 경로 포함 카탈로그 형식이 실제 프롬프트에서 올바르게 출력되는지 확인
- structural 패턴이 DB 조회로 동적 로드되는지 확인 (하드코딩 제거 확인)
- 혼동 쌍이 DB에서 로드되는지 확인
- 메타 패턴 코드 DEPRECATED 처리 후 파이프라인 오류 없음 확인
- 토큰 사용량 증가 여부 확인 (목표: input_tokens 50% 이하 증가)

---

## 12. STEP 6 — 임베딩 재생성

> **선행 조건**: STEP 5 완료 및 기획자 승인
> **실행 환경**: Claude Code CLI

### 목표

search_text 필드를 임베딩 소스로 사용하도록 전환.
detection_strategy='structural' 패턴은 임베딩 대상에서 제외.

### CLI 실행 지시

```
다음 작업을 순서대로 수행하라.

1. scripts/generate_embeddings.py를 읽어라.

2. 임베딩 소스를 description → search_text로 변경하라.

3. 임베딩 대상 필터를 아래로 수정하라:
   is_active=TRUE AND detection_strategy='vector'
   (structural 패턴은 임베딩 불필요, is_active=FALSE 패턴 제외)

4. 수정된 스크립트를 실행하라 (level=3 신규 패턴만 대상).
   기존 38개 상위 패턴 임베딩은 유지 (호환성).

5. 재생성 후 pattern_count, ethics_count를 로그로 출력하라.
   예상: vector 패턴 수 = 전체 활성 패턴 - structural 패턴 수
```

### 승인 게이트 (STEP 6)

- 임베딩 건수 확인: 신규 119건 중 structural 제외 건수만 생성됐는지
- 기존 38개 상위 패턴 임베딩 유지 여부 확인

---

## 13. STEP 7 — 골든셋 재정비 + R8 벤치마크 + threshold 재조정

> **선행 조건**: STEP 6 완료 및 기획자 승인
> **실행 환경**: Claude Code CLI + 기획자 직접 확인

### STEP 7-A: 골든셋 재정비

(A) **E-17**: TN → TP 전환. `golden_dataset_labels.json`의 expected_patterns에 7-5 추가.

(B) **C-02**: 골든셋에서 제거. 난이도 유사 기사 1건 추가 검토 (기획자 판단).

(C) **119개 새 코드 기준으로 expected_patterns 전면 재매핑**.
예: 기존 1-1 → 해당 하위 코드(1-1-a, 1-1-b 등)로 구체화.

골든셋 최종: TP 21건 + TN 5건 = 26건.

### STEP 7-B: R8 벤치마크

```
scripts/benchmark_pipeline_v3.py 전체 재측정 (26건)

보고 형식:
  (A) FR / Precision / TN FP Rate (R5 수치와 나란히)
  (B) TN 5건 각각 합격/실패
  (C) 새로 HIT된 TP 케이스 목록
  (D) 여전히 MISS인 패턴 목록
```

### STEP 7-C: threshold/count 재조정

```
scripts/ 디렉토리에 threshold 스윕 스크립트를 작성하라.
파일명: scripts/threshold_sweep.py

기능:
- threshold를 0.10에서 0.40까지 0.05 단위로 변경하며 Dev Set 26건 실행
- 각 threshold에서 Recall@k (k=5, 7, 10) 측정
- 결과를 docs/_scratch/threshold_sweep_{timestamp}.csv로 저장

추천 기준: Recall@7 ≥ 0.70을 달성하는 최고(보수적) threshold
추천값으로 pattern_matcher.py의 기본값을 수정.
주석으로 조정 근거와 날짜를 남길 것.
```

병렬화 조건부 실행: threshold_sweep 결과 평균 RPC 호출 시간 > 2초인 경우에만
`asyncio.gather()` 병렬 처리 적용.

### STEP 7-D: 기획자 수동 리포트 품질 평가 (STEP 7 전 필수)

골든셋 10건의 현재 리포트를 기획자가 직접 채점.
저장 위치: `docs/_scratch/report_quality_baseline.md`

```
채점 기준 (건당 0~6점, 3항목 × 0~2점):

[항목 1] 탐지 정확도 (0~2)
  0 = 핵심 문제 완전히 놓침
  1 = 부분 탐지, 중요 패턴 누락
  2 = 핵심 문제 정확히 탐지

[항목 2] 규범 인용 적절성 (0~2)
  0 = 인용 규범이 패턴과 무관하거나 오인용
  1 = 관련은 있으나 가장 적절한 규범 아님
  2 = 가장 구체적·직접적인 규범 인용

[항목 3] 비평 깊이 (0~2)
  0 = 단순 나열, 이유 설명 없음
  1 = 문제 지적하나 독자가 이해하기 어려움
  2 = 구체적 근거 + 독자가 납득할 수 있는 설명
```

### 성공 기준 (STEP 7)

| 지표 | 목표 |
|---|---|
| FR | R5(36.7%) 대비 유의미한 개선 |
| Precision | R5(44.2%) 유지 또는 개선 |
| TN FP Rate | 3/6 이하 (5건 기준) |
| Recall@7 | ≥ 0.70 (threshold 스윕 기준) |
| 리포트 품질 점수 | STEP 7-D 기준선 대비 개선 |
| 롤업 출현 | 리포트 5건 중 3건 이상 |

앙상블 감리 투입: R8 결과를 전원이 독립 검토 후 취합.

---

## 14. 향후 트랙 (STEP 7 완료 후)

```
STEP 7 완료 (R8 벤치마크)
    ↓
T-2 트랙 재개 — search_text 어휘 재작성 (리포트 품질 영향 없음)
    ↓
Phase G 매핑 복원 재개 — 119개 기준으로 공백 패턴 보완
    ↓
리포트 품질 정성 평가 — 기준선 대비 개선 확인
```

---

## 15. 교차 감리 체계

| STEP | 감리 대상 | 투입 감리자 | 합산 원칙 |
|---|---|---|---|
| STEP 1 후 | 119개 코드 체계 설계안 | Claude.ai + Antigravity + Gemini/Manus 중 1 | 2인 이상 지적 = 수정 필수 |
| STEP 2 후 | description 샘플 10개 | Claude.ai + Antigravity | 2인 이상 지적 = 수정 필수 |
| STEP 2 후 | search_text 어휘 | Gemini | 단독 의견, 기획자 판단 |
| STEP 3 후 | 매핑 분포 쿼리 결과 | Claude.ai + Manus | 2인 이상 지적 = 수정 필수 |
| STEP 4 후 | 리포트 샘플 5건 롤업 | Claude.ai + 기획자 | 기획자 직접 확인 |
| STEP 5 후 | 프롬프트 형식 + DEPRECATED 처리 | Claude.ai + Antigravity | 2인 이상 지적 = 수정 필수 |
| STEP 7 후 | R8 벤치마크 전체 해석 | 전원 앙상블 | 2인 이상 지적 = 수정 필수 |

감리 요청 패키지 구조 (공통):
(1) 변경 대상 항목
(2) 판단 기준 (§13 성공 기준)
(3) 확인 요청 포인트
(4) 이전 감리 의견 요약 (앵커링 방지로 마지막에)
다른 감리자 초안·기획자 선호 방향은 비공개 유지.

---

## 16. 도구·환경

- 프로덕션 DB: DATABASE_URL in .env (Transaction pooler, port 6543)
- 벤치마크 스크립트: `scripts/benchmark_pipeline_v3.py`
- 골든셋: `docs/golden_dataset_final.json` (26건: TP 21 + TN 5)
- 기사 본문: `Golden_Data_Set_Pool/article_texts/*.txt`
- Antigravity: Strict Mode On, Deny List 9개, Agent Auto-Fix Lints Off

---

## 17. 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1.0 | 2026-04-28 | `PHASE_H_EXECUTION_PLAN_v1.0.md` + `PIPELINE_IMPROVEMENT_PLAN_v1.1.md` 실행 순서 기반 완전 통합 |
| v1.1 | 2026-05-01 | STEP 0-B §6: applicable_contexts 컨텍스트 목록에 `{crime}` 추가, 확정 목록 명시. STEP 4-C: `_infer_article_context()` 함수 'court' 폐기 후 `crime` 포함 9개 컨텍스트로 확장. |
| v1.2 | 2026-05-03 | STEP 3 완료 기록. §9 실제 실행 결과 반영 (111건 발견·처리, hierarchy_level 필터 정규식 교체, PCP 44.6% 달성). |

---

*작성: Claude.ai (감나무와 협업) — 2026-04-28*
