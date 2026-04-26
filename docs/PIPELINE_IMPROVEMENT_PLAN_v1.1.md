# CR-Check 파이프라인 개선 실행 계획 v1.1

> 작성일: 2026-04-25 이전 버전: v1.0 (2026-04-25) v1.1 변경 내용: 감리 지적 반영 (CLI 6개 필수·높음 항목 + Antigravity 2개 항목) 이 문서는 Claude Code CLI에 직접 전달 가능한 실행 지시 형식으로 작성됨

---

## 0. Phase H와의 관계 (필독)

이 문서는 `PHASE_H_EXECUTION_PLAN_v1.0.md`**를 대체하지 않는다**.Phase H는 38→119 패턴 세분화 + search_text 컬럼 + 임베딩 재생성 + 벤치마크의 독자적인 7-STEP 실행 계획이며, 현재 진행 중인 Single Source of Truth 문서다.

이 문서는 Phase H 위에 얹히는 **보완 설계 문서**다. 역할 분담:

항목Phase H 담당이 문서 담당119개 코드 체계 설계STEP 1—search_text 컬럼 추가STEP 2—detection_strategy 컬럼 추가—Phase 1-Areport_framing 컬럼 추가—Phase 1-Apattern_ethics_relations 재배분STEP 3—applicable_contexts 컬럼 추가—Phase 1-B_build_ethics_context() 구조화STEP 4Phase 1-D (strength 필터 추가)임베딩 재생성STEP 6 (search_text 기준)Phase 3-A (detection_strategy 필터 추가)골든셋 재정비 + 벤치마크STEP 7Phase 3 성능 기준선Sonnet 프롬프트 재설계—Phase 2혼동 쌍 DB화—Phase 2-B벡터 검색 threshold 재조정—Phase 3-B

**실행 순서**: Phase H STEP 1\~7 완료 → 이 문서 Phase 1\~3 순서로 진행. Phase H 진행 중 겹치는 작업(STEP 2 마이그레이션 등)이 있을 경우, 이 문서의 컬럼 추가를 Phase H STEP 2 마이그레이션에 합산할 수 있다.

---

## 1. 배경 및 누수 유형 분류

CR-Check의 핵심 파이프라인은 현재 작동하고 있으나, 세 지점에서 구별되는 성격의 누수가 확인되었다. 이 세 누수를 하나의 처방으로 묶으면 변화 원인을 추적할 수 없고 상충 효과가 발생한다. 따라서 누수 유형별로 분리 진단하고, 순서에 따라 단계적으로 개선한다.

지점누수 성격현재 상태④ 벡터 검색후보 소환 실패 (Recall 손실)threshold=0.2, count=7. "부재 감지" 패턴을 필수 고정 목록으로 우회⑤ Sonnet Solo판단 부정확 (Precision/Recall 둘 다 해당)패턴 카탈로그 28개 평면 나열. 혼동 쌍 5개 하드코딩⑦ 윤리규범 조회인용 품질 저하기사 맥락 무관 규범 발동. related_to/weak 규범도 무조건 전달⑥ 메타패턴 추론**완전 비활성화 확정**inferred_by 관계 0건. 설계만 존재, 데이터·운용 경험 없음

---

## 2. 현재 DB 실측 기준선 (2026-04-25)

### patterns 테이블 (38건)

hierarchy_levelis_meta_pattern건수비고1false8대분류 — Sonnet 카탈로그 비대상3false28소분류 — Sonnet 카탈로그 대상3true2메타 패턴 (4-1, 4-2) — 카탈로그 비대상2—0중분류 없음 (Phase H STEP 1에서 추가 예정)

**현재 컬럼**: id, code, name, description, category, subcategory, is_meta_pattern, hierarchy_level, parent_pattern_id, locale, description_embedding, created_at, updated_at

**없는 컬럼 (is_active 없음)**: 비활성화는 현재 is_meta_pattern=true로 처리. Phase 1-A에서 is_active 컬럼을 추가하여 세분화한다.

### 성능 기준선 (Phase H R5 기준)

지표현재값Phase 1 목표Phase 2 목표Phase 3 목표Recall (FR)36.7%45%60%75%Precision44.2%55%70%80%TN FP Rate6/65/6 이하4/6 이하3/6 이하평균 분석 시간측정 필요——≤ 90초

> 목표는 단계별 중간값으로 설정. 전 단계 목표 미달 시 다음 단계 진입 금지.

---

## 3. 핵심 아키텍처 결정사항 (변경 불가 전제)

- Sonnet Solo 1-Call 구조 유지 (Haiku → Sonnet 2-Call 복귀 없음)
- TN 케이스: `pipeline.py`의 `_TN_MESSAGE` 정적 메시지 사용 (Phase 2 미호출)
- Phase β 확정: `<cite>` 태그 후치환 방식 폐기, Sonnet 직접 서술 방식 유지
- GitHub 커밋은 사람이 직접 수행 (CLI 자동 커밋 금지)
- 임베딩 소스: Phase H STEP 6에서 search_text 기준으로 전환 확정

---

## 4. 전체 실행 로드맵

```
[Phase H STEP 1~7] 선행 완료 필요
        ↓
Phase 0 — 패턴·규범 DB 정리        ← Phase H STEP 1~2와 병행 가능
Phase 1 — DB 스키마 확장           ← Phase H STEP 2 마이그레이션에 합산 가능
Phase 2 — Sonnet 프롬프트 재설계   ← Phase H STEP 4 이후
Phase 3 — 벡터 검색 재조정         ← Phase H STEP 6~7 이후 실측 기반
```

---

## Phase 0 — 패턴·규범 DB 정리 (선행 필수)

> **이 Phase는 항목 단위 검토·판단이 필요하다. Claude Code CLI 단독 실행 불가**.Phase H STEP 1(코드 체계 설계)과 병행하여 [Claude.ai](http://Claude.ai) 세션에서 진행한다. 확정 목록을 CLI에 전달하여 Phase H STEP 2 마이그레이션에 합산한다.

### Phase 0-A: 패턴(patterns) 정리

**현황 (DB 실측)**

- 전체 38개: 대분류 8 + 소분류 28 (Sonnet 카탈로그 대상) + 메타 2 (4-1, 4-2)
- Phase H STEP 1에서 소분류 28개 → 119개로 확장 예정 (1-1-a 형식)
- 중분류(hierarchy_level=2)는 현재 DB에 없음

**비활성화 확정 항목 (사전 결정)**

패턴 코드패턴명비활성화 사유4-1외부 압력에 의한 왜곡메타패턴 추론 완전 비활성화와 동시 처리. 기사 텍스트만으로 판단 불가4-2상업적 동기에 의한 왜곡동일 사유

메타 패턴 비활성화 시 코드 정리 범위:

- `pipeline.py`: `check_meta_patterns()` 호출 블록 제거 또는 조건부 비활성화
- `report_generator.py`: `_build_meta_pattern_block()` 함수 — 사용되지 않으므로 DEPRECATED 처리
- `meta_pattern_inference.py` 전체: 비활성 모듈로 격리 (삭제 아닌 주석 처리)

**119개 검토 기준 (각 패턴에 적용)**

아래 세 질문에 모두 "예"일 때만 활성화 유지:

1. 기사 텍스트만으로 감지 가능한가? (외부 정보 없이)
2. Sonnet이 "구체적 문장을 특정"할 수 있는가?
3. 일반 독자에게 의미 있는 지적인가?

`detection_strategy` **컬럼 설계 (Phase 1-A에서 추가)**

값의미`vector`임베딩 검색 대상 (기본값)`structural`벡터 제외, Sonnet 고정 필수 검토 목록

`structural` 초기 목록 (확장 가능):

패턴 코드분류 사유7-2제목-본문 구조 비교 → 개별 문장 유사도 무의미3-1반론의 "부재" 감지 → 없는 텍스트 임베딩 불가6-1맥락·배경의 "부재" 판단 → 동일 사유3-4기사 전체 프레임 판단 → 개별 문장 유사도 부적합

**기존 컬럼 활용 방침**

DB에 이미 존재하는 `hierarchy_level INT`와 `parent_pattern_id BIGINT FK`를 활용한다. Phase 1-A에서 **신규 컬럼으로 중복 생성하지 않는다**. 추가할 컬럼:

- `is_active BOOLEAN DEFAULT TRUE` — 비활성화 관리 (현재 is_meta_pattern으로만 관리)
- `detection_strategy TEXT DEFAULT 'vector'` — 검색 전략 구분
- `report_framing TEXT` — Sonnet 리포트 서술 방향 힌트

중분류(hierarchy_level=2)는 Phase H STEP 1에서 코드 체계 확정 후 추가한다.

---

### Phase 0-B: 윤리규범(ethics_codes) 정리

**현황 (DB 실측)**

- is_active=true, is_citable=true 기준 375건
- Tier 분포: Tier1(9) / Tier2(105) / Tier3(254) / Tier4(7)
- 현재 문제:
  1. 특수 맥락 규범(감염병보도준칙 등)이 기사 유형 무관하게 발동
  2. `related_to/weak` 규범이 Sonnet 컨텍스트에 무조건 포함 → 노이즈
  3. 명목적 선언 조항이 실제 기사 적용 어려운 채로 is_citable=true 상태

**검토 기준 (각 조항에 적용)**

1. 이 조항을 기사에 실제로 적용할 수 있는가?
2. 적용 가능하다면, 어떤 기사 유형에서인가?
3. 상위 조항과 내용이 중복되는가? (중복이면 하위만 활성화)

`applicable_contexts TEXT[]` **컬럼 설계 (Phase 1-B에서 추가)**

NULL이면 `all` 컨텍스트로 간주 (하위 호환). 예: `'{general}'`, `'{health,disaster}'`, `'{all}'`

`strength` **필터링 정책 확정**

relation_typestrengthSonnet 컨텍스트 포함 여부violatesstrong✅ 핵심 섹션 포함violatesmoderate✅ 핵심 섹션 포함related_tomoderate⚠️ 참고 규범 섹션으로 분리related_toweak❌ 제외 (RPC 레벨에서 필터)

---

### Phase 0 산출물 (다음 Phase 진입 조건)

- \[ \] 활성화 패턴 확정 목록 (코드 + detection_strategy + report_framing)
- \[ \] 비활성화 패턴 목록 (코드 + 사유)
- \[ \] 규범별 applicable_contexts 레이블 목록
- \[ \] 규범별 is_citable 재조정 목록

---

## Phase 1 — DB 스키마 확장

> **선행 조건**: Phase 0 산출물 확정 완료 **실행 환경**: Claude Code CLI **합산 가능**: Phase H STEP 2 마이그레이션 실행 전이라면, 아래 컬럼 추가를 STEP 2에 합산한다 **감리**: Antigravity (Strict Mode On, Deny List 적용)

### Phase 1-A: patterns 테이블 확장

```
다음 작업을 순서대로 수행하라.

1. docs/PIPELINE_IMPROVEMENT_PLAN_v1.1.md의 Phase 0-A 설계를 읽어라.
2. supabase/migrations/ 디렉토리에 새 마이그레이션 파일을 생성하라.
   파일명: {timestamp}_patterns_strategy.sql
3. 파일 내용 (작성만, 실행 금지):
   -- is_active 컬럼 추가 (현재 없음, is_meta_pattern과 별도 관리)
   ALTER TABLE patterns ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
   -- 기존 메타 패턴을 is_active=false로 전환
   UPDATE patterns SET is_active = FALSE WHERE is_meta_pattern = TRUE;
   -- detection_strategy 컬럼 추가
   ALTER TABLE patterns ADD COLUMN IF NOT EXISTS detection_strategy TEXT DEFAULT 'vector';
   -- structural 패턴 4종 지정
   UPDATE patterns SET detection_strategy = 'structural'
     WHERE code IN ('7-2', '3-1', '6-1', '3-4');
   -- report_framing 컬럼 추가
   ALTER TABLE patterns ADD COLUMN IF NOT EXISTS report_framing TEXT;
4. Phase 0-A 확정 목록을 기반으로 report_framing UPDATE SQL을 별도 시드 파일로 작성하라.
   파일명: supabase/seeds/patterns_framing_seed.sql
5. 위 파일들을 작성만 하고 실행하지 마라.
```

### Phase 1-B: ethics_codes 테이블 확장

```
다음 작업을 순서대로 수행하라.

1. docs/PIPELINE_IMPROVEMENT_PLAN_v1.1.md의 Phase 0-B 설계를 읽어라.
2. supabase/migrations/ 디렉토리에 새 마이그레이션 파일을 생성하라.
   파일명: {timestamp}_ethics_codes_context.sql
3. 파일 내용 (작성만, 실행 금지):
   ALTER TABLE ethics_codes ADD COLUMN IF NOT EXISTS applicable_contexts TEXT[];
4. Phase 0-B 확정 목록을 기반으로 applicable_contexts 및 is_citable 재조정
   UPDATE SQL을 별도 시드 파일로 작성하라.
   파일명: supabase/seeds/ethics_codes_context_seed.sql
5. 위 파일들을 작성만 하고 실행하지 마라.
```

### Phase 1-C: get_ethics_for_patterns RPC 수정

**articleType 시퀀싱 문제 해결 방안**

`article_analysis.articleType`은 Phase 2 Sonnet의 출력이므로, 규범 조회(Phase 1-C) 시점에는 아직 생성되지 않았다. 따라서 `articleType`을 RPC 인자로 쓸 수 없다.

해결 방안: **Phase 1 패턴 매칭 직후 기사 유형 휴리스틱 사전 분류**

```python
# pipeline.py에 추가할 함수 설계
def _infer_article_context(article_text: str, pattern_codes: set) -> str:
    """
    기사 원문 키워드 + 확정 패턴 코드로 기사 맥락을 사전 추정.
    Sonnet Phase 2가 생성하는 articleType보다 정밀도가 낮지만,
    규범 필터링에 충분한 수준의 맥락 구분을 제공한다.
    반환값: 'health' | 'disaster' | 'court' | 'general'
    """
    health_keywords = ['감염병', '코로나', '백신', '의료', '병원', '질병', '바이러스']
    disaster_keywords = ['재난', '지진', '화재', '홍수', '사고', '피해']
    court_keywords = ['재판', '판결', '검찰', '기소', '법원', '변호']
    
    text_sample = article_text[:500]  # 앞 500자만 확인 (효율)
    if any(kw in text_sample for kw in health_keywords):
        return 'health'
    if any(kw in text_sample for kw in disaster_keywords):
        return 'disaster'
    if any(kw in text_sample for kw in court_keywords):
        return 'court'
    return 'general'
```

```
다음 작업을 순서대로 수행하라.

1. backend/core/report_generator.py의 fetch_ethics_for_patterns()와
   backend/core/pipeline.py의 analyze_article()를 읽어라.
2. pipeline.py에 _infer_article_context() 함수를 추가하라.
   위 설계를 참고하되, 키워드 목록은 Phase 0-B 확정 applicable_contexts 레이블을
   기준으로 보완하라.
3. pipeline.py의 generate_report() 호출 직전에 article_context를 추론하라:
   article_context = _infer_article_context(article_text, pm.validated_pattern_codes)
4. supabase/migrations/ 디렉토리에 새 마이그레이션 파일을 생성하라.
   파일명: {timestamp}_rpc_ethics_context_filter.sql
   내용:
   - get_ethics_for_patterns RPC 파라미터에 article_context TEXT DEFAULT 'general' 추가
   - 필터: applicable_contexts IS NULL
           OR 'all' = ANY(applicable_contexts)
           OR article_context = ANY(applicable_contexts)
   - strength='weak' AND relation_type='related_to' 제외
5. fetch_ethics_for_patterns() 시그니처에 article_context: str = 'general' 추가.
   RPC 페이로드에 article_context 포함.
6. generate_report() 시그니처에 article_context: str = 'general' 추가.
   pipeline.py에서 추론한 값을 전달.
7. REST API fallback 로직 (fetch_ethics_for_patterns 내부)도 동일하게 수정하라:
   applicable_contexts 필터를 REST API 쿼리 파라미터에 추가.
   (Antigravity 지적: RPC와 fallback 동기화 필수)
8. 모든 변경사항을 파일 수정만 수행하라. 커밋은 사람이 직접 수행한다.
```

### Phase 1-D: \_build_ethics_context() 수정

```
backend/core/report_generator.py의 _build_ethics_context() 함수를 수정하라.

수정 내용:
1. EthicsReference 리스트를 두 그룹으로 분리:
   - primary: relation_type='violates' (strong + moderate)
   - reference: relation_type='related_to' AND strength='moderate'
   (strength='weak'는 Phase 1-C RPC에서 이미 제거됨)
2. primary 그룹 출력: 기존 Tier 역순 정렬 유지 (-x.ethics_tier)
3. reference 그룹 출력: 아래 헤더로 분리 (비어 있으면 섹션 전체 생략)
   "## 참고 규범 (직접 인용보다 맥락 이해용)"
4. 시스템 프롬프트(_SONNET_SYSTEM_PROMPT)에 두 섹션 활용 지침을 추가하라:
   핵심 규범 → 구체적 조항 직접 인용
   참고 규범 → 맥락 확장 시 선택적으로 언급
```

### Phase 1 검증 체크리스트

- \[ \] 마이그레이션 SQL 문법 오류 없음 (Antigravity 감리)
- \[ \] 기존 71건 analysis_results에 영향 없음
- \[ \] is_active=false 패턴이 카탈로그 로드에서 제외되는지 확인
- \[ \] structural 패턴 4개가 별도 섹션으로 분리되는지 확인
- \[ \] article_context 필터가 올바르게 작동하는지 단위 테스트
- \[ \] REST API fallback에서도 applicable_contexts 필터 동작 확인

---

## Phase 2 — Sonnet 프롬프트 재설계

> **선행 조건**: Phase 1 완료 + DB에 detection_strategy, report_framing 데이터 입력 완료
> **Phase H 연관**: Phase H STEP 4 (_build_ethics_context 구조화) 이후 진행

### Phase 2-A: 패턴 카탈로그 형식 재설계

**현재 문제**

소분류 28개가 평면 나열된다. 119개로 늘어나면 Sonnet의 주의(attention)가 분산된다.
또한 패턴 감지 후 리포트에서 "어느 계층까지 서술할지" 힌트가 없다.

**목표 카탈로그 항목 형식**

```
[{code}] {name}
계층 경로: {대분류명} > {중분류명} > 현재 패턴
감지 힌트: {description 또는 search_text}
리포트 서술 방향: {report_framing}
```

```
다음 작업을 순서대로 수행하라.

1. backend/core/pattern_matcher.py의 패턴 카탈로그 로드 로직 전체를 읽어라.
2. DB에서 패턴 카탈로그를 로드하는 쿼리를 아래와 같이 수정하라:
   SELECT p.id, p.code, p.name, p.description, p.detection_strategy,
          p.report_framing, p.hierarchy_level, p.parent_pattern_id,
          parent.code AS parent_code, parent.name AS parent_name,
          grandparent.name AS grandparent_name
   FROM patterns p
   LEFT JOIN patterns parent ON p.parent_pattern_id = parent.id
   LEFT JOIN patterns grandparent ON parent.parent_pattern_id = grandparent.id
   WHERE p.is_active = TRUE AND p.is_meta_pattern = FALSE
3. _build_pattern_catalog_entry(row) 헬퍼 함수를 새로 작성하라:
   - detection_strategy='vector'인 패턴: 목표 형식 텍스트 블록 반환
   - report_framing이 NULL이면: "구체 패턴({code}) 지적 → {parent_name} 맥락으로 확장" 자동 생성
4. detection_strategy='structural' 패턴은 별도 섹션으로 분리:
   "## 구조적 판단 필수 검토 패턴 (★ 마크 무관 항상 직접 검토)"
   이 섹션의 패턴 목록은 DB에서 동적으로 로드한다 (하드코딩 제거).
5. 기존 하드코딩된 구조적 판단 4개 고정 목록을 DB 조회 결과로 대체하라.
```

### Phase 2-B: 혼동 쌍 관리 방식 개선

**현재 상태**: 5개 혼동 쌍이 `_SONNET_SOLO_PROMPT`에 하드코딩.
**단기 방침**: 별도 테이블 생성은 119개 확장 후로 유보.
지금은 `patterns` 테이블의 메타데이터 방식으로 처리한다.

```
다음 작업을 순서대로 수행하라.

1. backend/core/pattern_matcher.py의 _SONNET_SOLO_PROMPT에서
   혼동 쌍 관련 섹션(현재 5개)을 식별하라.
2. supabase/migrations/ 디렉토리에 새 마이그레이션 파일을 생성하라.
   파일명: {timestamp}_pattern_confusion_pairs.sql
   내용:
   CREATE TABLE IF NOT EXISTS pattern_confusion_pairs (
     id         BIGSERIAL PRIMARY KEY,
     code_a     TEXT NOT NULL,
     code_b     TEXT NOT NULL,
     distinction_guide TEXT NOT NULL,
     is_active  BOOLEAN DEFAULT TRUE,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
3. 기존 5개 혼동 쌍을 시드 데이터로 작성하라.
   파일명: supabase/seeds/pattern_confusion_pairs_seed.sql
4. pattern_matcher.py에 _load_confusion_pairs() 함수를 추가하라:
   - pattern_confusion_pairs 테이블에서 is_active=true인 쌍을 로드
   - _pattern_catalog_cache와 동일한 모듈 전역 캐싱 방식 적용
5. _SONNET_SOLO_PROMPT의 혼동 쌍 하드코딩 섹션을 동적 로드 결과로 대체하라.
6. SQL 파일들을 작성만 하고 실행하지 마라.
```

### Phase 2-C: 메타 패턴 관련 코드 정리

**(Antigravity 지적 반영)**

```
다음 작업을 순서대로 수행하라.

1. pipeline.py의 check_meta_patterns() 호출 블록을 읽어라.
2. 아래 세 파일의 메타 패턴 관련 코드를 DEPRECATED 처리하라:
   a. pipeline.py: check_meta_patterns() 호출 블록 전체를
      # [DEPRECATED] 메타 패턴 추론 비활성화 (Phase I, 2026-04-25)
      # inferred_by 관계 0건. 데이터 없이 운용 불가. 재활성화 시 주석 해제.
      주석으로 감싸라. 삭제하지 마라.
   b. report_generator.py: _build_meta_pattern_block() 함수 상단에
      # [DEPRECATED] 메타 패턴 비활성화로 이 함수는 현재 호출되지 않음.
      주석을 추가하라.
   c. meta_pattern_inference.py: 파일 상단에
      # [DEPRECATED MODULE] 메타 패턴 추론 비활성화 (Phase I, 2026-04-25)
      주석을 추가하라.
3. 비활성화 후 파이프라인 E2E 테스트를 실행하여 오류 없음을 확인하라.
```

### Phase 2 검증 체크리스트

- [ ] 계층 경로 포함 카탈로그 형식이 실제 프롬프트에서 올바르게 출력되는지 확인
- [ ] structural 패턴이 DB 조회로 동적 로드되는지 확인 (하드코딩 제거 확인)
- [ ] 혼동 쌍이 DB에서 로드되는지 확인
- [ ] 메타 패턴 코드 DEPRECATED 처리 후 파이프라인 오류 없음 확인
- [ ] Dev Set 26건 벤치마크: Phase 1 대비 Precision/Recall 비교
- [ ] 토큰 사용량 증가 여부 확인 (목표: input_tokens 50% 이하 증가)

---

## Phase 3 — 벡터 검색 재조정

> **선행 조건**: Phase 1 + Phase 2 완료 + Phase H STEP 6~7 완료
> **핵심 원칙**: 실측 기반 조정만. 가설 기반 변경 금지.
> **임베딩 소스**: Phase H STEP 6에서 search_text 기준으로 전환 완료 전제

### Phase 3-A: 임베딩 재생성 (detection_strategy 필터 추가)

```
다음 작업을 순서대로 수행하라.

1. scripts/generate_embeddings.py를 읽어라.
2. 임베딩 대상 필터를 아래로 수정하라:
   is_active=TRUE AND detection_strategy='vector'
   (structural 패턴은 임베딩 불필요, is_active=FALSE 패턴 제외)
3. 수정된 스크립트를 실행하라.
4. 재생성 후 pattern_count, ethics_count를 로그로 출력하라.
   예상: vector 패턴 수 = 전체 활성 패턴 - structural 4개 이상
```

### Phase 3-B: threshold/count 재조정

```
다음 작업을 순서대로 수행하라.

1. backend/core/pattern_matcher.py의 search_vectors() 함수를 읽어라.
2. scripts/ 디렉토리에 threshold 스윕 스크립트를 작성하라.
   파일명: scripts/threshold_sweep.py
   기능:
   - threshold를 0.10에서 0.40까지 0.05 단위로 변경하며 Dev Set 26건 실행
   - 각 threshold에서 Recall@k (k=5, 7, 10) 측정
   - 결과를 docs/_scratch/threshold_sweep_{timestamp}.csv로 저장
3. 스크립트를 실행하고 결과를 출력하라.
4. 결과를 바탕으로 최적 threshold와 count를 추천하라.
   추천 기준: Recall@7 ≥ 0.70을 달성하는 최고(보수적) threshold
5. 추천값으로 pattern_matcher.py의 기본값을 수정하라.
   주석으로 조정 근거와 날짜를 남길 것.
```

### Phase 3-C: 병렬화 (조건부)

Phase H 이후 패턴이 119개로 늘면 "청크 수 × RPC 호출"이 증가한다.
아래 조건이 충족될 때만 실행한다:

```
조건: threshold_sweep.py 실행 결과 평균 RPC 호출 시간이 2초를 초과하는 경우

조건 충족 시:
1. search_vectors()의 RPC 호출을 asyncio.gather()를 사용한 병렬 호출로 변경하라.
2. FastAPI의 analyze_article()가 동기 def임을 확인하고
   병렬 처리를 위한 asyncio.run() 래퍼 필요 여부를 검토하라.
3. 변경 후 Dev Set 전체 실행 시간 비교 결과를 로그로 출력하라.
```

### Phase 3 검증 체크리스트

- [ ] 임베딩 재생성 후 패턴 수 확인 (structural 제외 확인)
- [ ] threshold 스윕 결과 CSV 저장 확인
- [ ] 최적 threshold 적용 후 Dev Set Recall@7 ≥ 0.70 달성 여부
- [ ] E2E 테스트: 5개 이상 실제 기사 분석 + 리포트 품질 육안 확인
- [ ] Railway 배포 후 응답 시간 측정 (목표: ≤ 90초)

---

## 공통 작업 원칙

### 브랜치 전략

```
feature/pipeline-improvement-phase{N}
```

Phase 0: 브랜치 불필요 (문서 작업)
Phase 1~3: 각 Phase별 별도 브랜치 생성
Phase H와 겹치는 작업은 Phase H 브랜치에 합산 가능

### 금지 사항 (Antigravity Deny List)

```
supabase db push / supabase db migration
git commit / git push / git add
rm / mv / sed -i / chmod
```

### 진단 덤프 활용

각 Phase 완료 후 `backend/diagnostics/` 최신 JSON 덤프를 확인한다.
`checkpoint_4_ethics.ethics_ref_count`가 0이면 Phase 1-C 폴백 체인 재점검.

### 롤백 전략

| Phase | 롤백 방법 |
|-------|-----------|
| Phase 1 마이그레이션 | 각 ALTER TABLE에 대응하는 DROP COLUMN SQL 준비 (사람이 실행) |
| Phase 1-C RPC 수정 | 이전 RPC 정의를 supabase/migrations/ 에 보존 |
| Phase 2 프롬프트 수정 | git revert (사람이 수행) |
| Phase 3 threshold 수정 | 변경 전 값을 주석으로 보존 |

---

## 이정표 요약

```
[Phase H STEP 1~7]  선행 실행 (PHASE_H_EXECUTION_PLAN_v1.0.md 기준)
        ↓
Phase 0  패턴·규범 DB 정리  ← Phase H STEP 1~2와 병행 가능 (지금 시작)
        ↓
Phase 1  DB 스키마 확장      ← Phase H STEP 2 마이그레이션에 합산 가능
        ↓
Phase 2  Sonnet 재설계       ← Phase H STEP 4 이후
        ↓
Phase 3  벡터 검색 재조정    ← Phase H STEP 6~7 이후 실측 기반
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2026-04-25 | 최초 작성 |
| v1.1 | 2026-04-25 | 감리 반영: Phase H 관계 명시, articleType 시퀀싱 해결, is_active 컬럼 추가, 계층 컬럼 중복 제거, 혼동 쌍 5개로 수정, 메타 패턴 코드 정리 추가, fallback 동기화 추가, 단계별 성능 목표 추가, 롤백 전략 추가 |

---

*문서 끝 — PIPELINE_IMPROVEMENT_PLAN_v1.1.md*
