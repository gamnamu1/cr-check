# CR-Check DB 구축 Week 2 M4 — RAG 파이프라인 구현 플레이북

> 작성일: 2026-03-29 (Claude.ai 초안)  
> 상태: **확정 — 2026-03-29 Gamnamu 승인**  
> 목적: M4(Week 2) 작업의 삼각편대 운영 절차를 STEP 단위로 정리  
> 역할: Claude Code CLI(코딩) → Claude.ai(1차 감리) → 마누스(2차 독립 감리) → Gamnamu(승인)  
> 선행 완료: M1(스키마) + M2(시드 데이터) + M3(임베딩+벤치마크) ✅

---

## 공통 원칙 (M1~M3에서 계승 + M3 교훈 추가)

- **Claude Code CLI 세션 시작 시 반드시**: `/effort max` 설정 → Plan Mode로 문서 숙지 후 Normal Mode 전환
- **컨텍스트 관리**: 50%에서 `/compact` 선제 실행. 변경 전 `/diff`로 사전 확인
- **쓰기 작업은 반드시 Migration 파일로만**. MCP는 읽기 전용 조회 전용
- **KJA 접두어 절대 사용 금지** → JCE가 올바른 접두어
- **OpenAI API 키**: 환경변수 `OPENAI_API_KEY`로 관리. 코드에 하드코딩 금지
- **Anthropic API 키**: 환경변수 `ANTHROPIC_API_KEY`로 관리. 코드에 하드코딩 금지
- **⚠️ M3 교훈 — 과부하 방지**: 체크포인트에서 반드시 끊기. 한 세션에서 무리하게 몰아치지 않는다
- **⚠️ M3 교훈 — FAIL 대응 원칙**: FAIL 시 같은 세션에서 즉시 대안 실행하지 않고 감리 의견 먼저 취합

---

## M4 작업 개요

| 항목 | 내용 |
|------|------|
| **목표** | 1.5회 호출 RAG 파이프라인 구현 + 전체 파이프라인 벤치마크 |
| **파이프라인 구조** | 기사→청킹→임베딩→벡터검색→**Haiku**(패턴 확정)→규범 조회→**Sonnet**(리포트) |
| **M3 핵심 교훈** | 벡터 검색 단독 불가. LLM이 패턴 식별 전담. 벡터 검색은 후보 보조 |
| **벤치마크 기준** | Candidate Recall ≥ 70% / Final Recall ≥ 80% / Final Precision ≥ 60% |
| **예상 일정** | Day 5~6 (체크포인트별 분할) |
| **비용 추정** | OpenAI 임베딩 ~$0.01/기사, Haiku ~$0.01/기사, Sonnet ~$0.05/기사 |

### M4 파이프라인 구조 (마스터 플랜 섹션 7.2)

```
기사 URL → 스크래핑 → 전처리(노이즈 제거)
    → 의미 기반 병합 청킹 (300~500자)
    → 청크별 임베딩 → search_pattern_candidates() (t=0.2~0.25)
    → Haiku (패턴 후보 + 전체 28개 목록 + 기사 → 패턴 확정)
    → 백엔드 밸리데이션 (환각 코드 제거)
    → get_ethics_for_patterns() (규범 정밀 조회)
    → Sonnet (확정 패턴 + 규범 → 결정론적 인용 리포트)
```

### M4 핵심 의사결정 분기점

```
Final Recall ≥ 80% + Final Precision ≥ 60%
  → M4 완료, M5(결정론적 인용 후처리)로 진행

Final Recall 60~80%
  → Haiku 프롬프트 조정 (패턴 설명 보강, 예시 추가)
  → 벡터 검색 threshold 미세조정 (0.15~0.20)
  → 재벤치마크

Final Recall < 60%
  → 감리 합동 회의 소집 (근본 원인 분석)
  → Haiku → Sonnet 또는 Opus 업그레이드 검토
  → 청킹 전략 재검토
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase A: 앙상블 보류 건 해결 (3건)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> M4 코딩 착수 전에 설계 레벨에서 해결해야 할 보류 사항 3건.
> Claude.ai가 해결안을 제시 → Gamnamu 승인 → CLI에 전달.

### STEP 32. Claude.ai — 메타 패턴 라우팅 방식 확정

**[배경]** 1-4-1(외부 압력), 1-4-2(상업적 동기)는 직접 감지 불가한 메타 패턴.
마스터 플랜 섹션 8의 추론 규칙(필수+보강 조건 기반 트리거)을 M4 파이프라인에 어떻게 통합할지 확정.

**[해결안]**
- 메타 패턴(1-4-1, 1-4-2)은 Haiku 프롬프트에 **직접 포함하지 않는다**
- Haiku는 직접 감지 가능한 28개 패턴만 대상으로 한다
- 메타 패턴 추론은 **M5로 이관**: Haiku 확정 패턴 목록 → 백엔드 규칙 엔진 → Sonnet 종합 판단
- 근거: M4의 핵심 목표는 "직접 감지 패턴의 Recall/Precision"이며, 메타 패턴은 이 기반 위에 올라가는 상위 레이어

**[감리 판정 기준]**
- ✅ 메타 패턴이 Haiku 프롬프트에서 제외되었는가
- ✅ M5에서 메타 패턴 추론 로직 구현이 명시적으로 예약되었는가
- ✅ pattern_relations의 `inferred_by` 관계 데이터가 이미 M2에 시드되어 있는가

**[Gamnamu 판단 요청]** 위 해결안 승인/수정?

---

### STEP 33. Claude.ai — 1-2 투명성 패턴 필터링 방식 확정

**[배경]** 1-2(투명성) 패턴들은 텍스트 분석이 아닌 메타데이터 분석이 필요.
(예: 출처 미표시, 저작권 침해 등은 기사 본문만으로 판단 불가)
앙상블 리뷰에서 `is_text_analyzable` 플래그 도입이 제안됨.

**[해결안]**
- M4에서는 **별도 플래그 추가 없이** 기존 구조로 처리
- 근거: Dev Set 26건에 1-2 투명성 패턴이 아예 없음 (SESSION_CONTEXT v15 확인)
- 1-2 패턴은 Phase 1 메타데이터 모듈로 이미 이관 결정됨
- Haiku 프롬프트에서 1-2 계열 패턴을 **"텍스트 분석 대상 아님" 주석으로 명시**하여 Haiku가 이 패턴을 선택하지 않도록 유도
- `is_text_analyzable` 컬럼 추가는 M5 이후 Phase 1 메타데이터 모듈 구현 시 검토

**[감리 판정 기준]**
- ✅ Haiku 프롬프트에 1-2 패턴 제외 지시가 포함되었는가
- ✅ 1-2 패턴이 벤치마크 기대값(expected_patterns)에 없는 것을 확인했는가

**[Gamnamu 판단 요청]** 위 해결안 승인/수정?

---

### STEP 34. Claude.ai — get_ethics_for_patterns 입력 타입 확정

**[배경]** Haiku는 패턴 **코드**(예: "1-1-1")를 출력하지만, `get_ethics_for_patterns()`는 패턴 **ID**(BIGINT[])를 입력으로 받음. 코드→ID 변환 계층이 필요.

**[해결안]**
- **백엔드(FastAPI) 레벨에서 코드→ID 변환** 처리
- Haiku 출력에서 패턴 코드 목록 추출 → DB 조회로 코드→ID 매핑 → `get_ethics_for_patterns()` 호출
- 별도 RPC 함수(code→ID 변환용) 생성하지 않음 — 단순 SELECT 쿼리로 충분
- 변환 시 DB에 존재하지 않는 코드는 **환각으로 간주하여 제거** (밸리데이션 레이어)

```python
# 의사 코드
haiku_pattern_codes = ["1-1-1", "1-3-2", "1-7-3"]  # Haiku 출력
valid_patterns = db.query(
    "SELECT id, code FROM patterns WHERE code = ANY($1)",
    haiku_pattern_codes
)
# DB에 없는 코드는 자동 탈락 (환각 제거)
confirmed_ids = [p.id for p in valid_patterns]
ethics_data = db.call_rpc("get_ethics_for_patterns", confirmed_ids)
```

**[감리 판정 기준]**
- ✅ 코드→ID 변환이 백엔드 레벨에서 처리되는가
- ✅ DB에 없는 코드(환각)가 자동 제거되는가
- ✅ 별도 Migration이 필요 없는가 (기존 RPC 변경 없음)

**[Gamnamu 판단 요청]** 위 해결안 승인/수정?

---

### STEP 35. Gamnamu — 보류 건 3건 일괄 승인

**[시점]** STEP 32~34의 해결안을 검토하고 일괄 승인/수정.

**[체크리스트]**
- [x] STEP 32 메타 패턴 라우팅 → **승인** (2026-03-29)
- [x] STEP 33 1-2 투명성 필터링 → **승인** (2026-03-29)
- [x] STEP 34 get_ethics_for_patterns 입력 타입 → **승인** (2026-03-29)

**[결과]** 3건 모두 승인 완료. Phase B로 진행.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase B: 기사 청킹 로직 구현 + 감리
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 36. Claude Code CLI — 세션 시작 + 기사 청킹 모듈 구현

**[시점]** Phase A 승인 완료 후. CLI 새 세션 시작.

**[프롬프트 — Claude Code CLI에게]**

```
/effort max

M1~M3 완료, M4(RAG 파이프라인) 작업을 시작한다.

■ 사전 숙지 (Plan Mode로 먼저 읽을 것)
1. docs/SESSION_CONTEXT (최신 버전) — M4 설계 지침 전체
2. docs/DB_AND_RAG_MASTER_PLAN_v4.0.md — 섹션 4(청킹 전략), 섹션 7.2(파이프라인)
3. docs/CR_CHECK_M4_PLAYBOOK.md — 이 플레이북
4. CLAUDE.md

■ 작업: 기사 청킹 모듈 구현
backend/core/chunker.py를 생성하라.

■ 핵심 요구사항 (마스터 플랜 섹션 4 준수)

1. **전처리 — 노이즈 제거**:
   - 사진 캡션 (예: ○○○ 기자, [사진=○○], /○○○ 기자)
   - 바이라인 (기자 이름 + 이메일)
   - 광고성 문구, 관련기사 링크
   - 저작권 고지 (ⓒ, 무단 전재 재배포 금지 등)
   - 포털 전재 시 추가되는 메타 텍스트

2. **의미 기반 병합 청킹**:
   - 한국 온라인 뉴스의 한 문장 줄바꿈 관행 대응
   - 짧은 단락(100자 미만)을 인접 단락과 병합
   - 목표 청크 크기: 300~500자
   - 기사당 예상 청크 수: 2~5개

3. **엣지케이스 대응**:
   - 리스트형 기사: 리스트 항목을 하나의 청크로 묶음
   - 1만자+ 장문 기사: 정상 청킹 후, 임베딩 검색 상위 3~4 청크만 선별
   - 극단적 단문 기사(500자 미만): 전체를 단일 청크로

4. **입출력**:
   - 입력: 기사 원문 텍스트 (스크래핑 결과)
   - 출력: List[str] (청크 리스트)
   - 각 청크의 원본 내 위치 정보(시작/끝 인덱스) 보존

5. **테스트**:
   - 골든 데이터셋의 기사 3건(장문/중문/단문)으로 청킹 결과 출력
   - 청크 수, 평균 길이, 최소/최대 길이 통계
```

**[완료 기준]**
- [ ] `backend/core/chunker.py` 생성됨
- [ ] 노이즈 제거 정규식이 한국 뉴스 관행에 맞게 구현됨
- [ ] 300~500자 범위의 의미 기반 병합이 작동함
- [ ] 엣지케이스 3종 대응됨
- [ ] 테스트 기사 3건의 청킹 결과 출력됨

---

### STEP 37. Claude.ai — 청킹 모듈 1차 감리

**[감리 대상]** `backend/core/chunker.py`

**[체크리스트]**
- [ ] 노이즈 제거 정규식이 한국 뉴스 포맷에 적합한가
  - 사진 캡션, 바이라인, 저작권 고지, 관련기사 링크
  - 포털(네이버/다음) 전재 시 추가 메타텍스트
- [ ] 한 문장 줄바꿈 관행이 제대로 처리되는가
  - `\n`으로만 구분된 단문이 병합되는가
  - `\n\n`은 의미적 경계로 존중되는가
- [ ] 청크 크기가 300~500자 범위를 지키는가
  - 100자 미만 잔여 단락이 인접 청크로 병합되는가
  - 500자 초과 시 적절히 분할되는가
- [ ] 원본 위치 정보(시작/끝 인덱스)가 보존되는가
- [ ] 극단적 케이스 대응: 단문(500자 미만), 장문(1만자+), 리스트형
- [ ] 테스트 결과의 청크 수/길이가 합리적인가

**[판정]** ✅ PASS / ❌ FAIL (수정사항 명시)

---

### STEP 38. 마누스 — 청킹 모듈 2차 독립 감리

**[감리 범위]** Claude.ai가 놓칠 수 있는 비Anthropic 관점의 검토

**[중점 확인]**
- [ ] 한국 뉴스 포털(네이버/다음) 특유의 포맷이 누락 없이 처리되는가
- [ ] 실제 한국 기사를 넣었을 때 의미 단위가 깨지지 않는가
- [ ] 정규식 성능: 특수문자, 유니코드, 이모지 등에서 오류 없는가

**[판정]** ✅ PASS / ❌ FAIL

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase C: 1.5회 호출 파이프라인 구현 + 감리
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> ⚠️ **체크포인트**: Phase B 감리 통과 후 시작. CLI 컨텍스트 50% 이상이면 `/compact` 실행.

### STEP 39. Claude Code CLI — 벡터 검색 + Haiku 통합 모듈 구현

**[프롬프트 — Claude Code CLI에게]**

```
Phase B(청킹 모듈) 감리 통과. 이제 1.5회 호출 파이프라인의 전반부를 구현한다.

■ 작업: 벡터 검색 + Haiku 패턴 식별 모듈
backend/core/pattern_matcher.py를 생성하라.

■ 파이프라인 전반부 구조

1. **청킹 → 임베딩 생성**:
   - chunker.py 결과를 받아 각 청크별 OpenAI 임베딩 생성
   - 배치 API 1회 호출로 모든 청크 처리

2. **벡터 검색 — search_pattern_candidates()**:
   - 각 청크별로 search_pattern_candidates() 호출
   - threshold: 0.2 (환경변수 VECTOR_THRESHOLD로 관리, 기본값 0.2)
   - match_count: 15 (넓게 뿌리기)
   - 결과 집계: 청크별 결과를 합산, 패턴별 최고 유사도 기준 상위 후보 도출
   - **중복 제거**: 같은 패턴이 여러 청크에서 나오면 최고 유사도만 유지

3. **Haiku 호출 — 패턴 확정**:
   - 입력 구성:
     a. 시스템 프롬프트 (마스터 플랜 7.3 기반, 아래 수정사항 반영)
     b. 전체 28개 패턴 목록 (코드 + 이름 + 한 줄 설명)
     c. 벡터 검색 상위 후보 (★ 표시로 강조)
     d. 기사 전문
   - ⚠️ 1-2 계열 패턴은 목록에 포함하되 "(텍스트 분석 대상 아님)" 주석 추가
   - ⚠️ 메타 패턴(1-4-1, 1-4-2)은 목록에서 제외
   - 출력 포맷: JSON (pattern_code, matched_text, severity, reasoning)
   - 모델: claude-haiku-4-5-20251001

4. **백엔드 밸리데이션**:
   - Haiku 출력의 pattern_code가 DB에 존재하는지 검증
   - 코드→ID 변환 (SELECT id, code FROM patterns WHERE code = ANY($1))
   - DB에 없는 코드는 환각으로 제거, 로그 남김

■ Haiku 프롬프트 수정사항 (마스터 플랜 7.3 대비)

- "후보에 없더라도 명백히 발견되는 문제" → 전체 28개 목록을 제공하므로 이 지시 유지
- 벡터 검색 후보에 ★ 마크 → "벡터 검색으로 사전 선별된 후보입니다. 참고하되, 
  목록의 다른 패턴도 해당되면 자유롭게 선택하세요"
- 출력에 reasoning 필드 추가 (디버깅용, 리포트에는 미포함)

■ 환경변수
OPENAI_API_KEY, ANTHROPIC_API_KEY, VECTOR_THRESHOLD(기본 0.2)
Supabase 연결: 기존 환경변수 사용
```

**[완료 기준]**
- [ ] `backend/core/pattern_matcher.py` 생성됨
- [ ] 청크별 임베딩 → 벡터 검색 → 결과 집계 로직 구현됨
- [ ] Haiku 프롬프트가 마스터 플랜 7.3 + 수정사항 반영하여 구성됨
- [ ] 전체 28개 패턴 목록이 Haiku에 전달됨 (1-2 주석, 메타 패턴 제외)
- [ ] 코드→ID 변환 + 환각 제거 밸리데이션 구현됨
- [ ] 골든 데이터셋 기사 1건으로 end-to-end 테스트 실행됨

---

### STEP 40. Claude Code CLI — Sonnet 리포트 생성 모듈 구현

**[프롬프트 — Claude Code CLI에게]**

```
벡터 검색 + Haiku 모듈 구현 완료. 파이프라인 후반부를 구현한다.

■ 작업: 규범 조회 + Sonnet 리포트 모듈
backend/core/report_generator.py를 생성하라.

■ 파이프라인 후반부 구조

1. **규범 정밀 조회 — get_ethics_for_patterns()**:
   - Haiku 확정 패턴 ID 배열로 RPC 호출
   - 반환: 직접 관계 규범 + parent chain 롤업 (tier 역순 정렬)

2. **Sonnet 호출 — 상세 리포트 생성**:
   - 입력 구성:
     a. 시스템 프롬프트 (마스터 플랜 7.3 기반)
     b. Haiku 확정 결과 JSON
     c. 규범 원문 컨텍스트 (get_ethics_for_patterns 결과)
     d. 기사 전문
   - 결정론적 인용: <cite ref="{ethics_code}"/> 태그만 출력
   - 모델: claude-sonnet-4-20250514
   - ⚠️ M4에서는 cite 태그 → 원문 치환 후처리는 구현하지 않음 (M5 범위)
   - M4에서는 Sonnet 출력에 cite 태그가 올바르게 포함되는지만 검증

3. **M4 범위의 출력**:
   - Sonnet 리포트 원문 (cite 태그 포함 상태)
   - Haiku 확정 패턴 목록 + 벡터 검색 후보 목록 (벤치마크용)
   - 처리 시간, 토큰 사용량 로그

■ 주의사항
- Sonnet 프롬프트의 메타 패턴 관련 지시("메타 패턴이 의심되는 경우 별도 섹션")는
  M4에서는 제거. 메타 패턴 추론은 M5에서 구현.
- 토큰 예산 확인: 입력 ~5,000~6,000 토큰 (마스터 플랜 7.4)
- 장문 기사 대응: Haiku 결과에서 매칭된 청크 상위 3~4개만 Sonnet에 전달
```

**[완료 기준]**
- [ ] `backend/core/report_generator.py` 생성됨
- [ ] get_ethics_for_patterns() RPC 호출이 정상 작동함
- [ ] Sonnet 프롬프트가 결정론적 인용 지시를 포함함
- [ ] cite 태그가 올바른 형식으로 출력됨
- [ ] 골든 데이터셋 기사 1건으로 전체 파이프라인 end-to-end 실행됨

---

### STEP 41. Claude Code CLI — 파이프라인 통합 + 단일 기사 E2E 테스트

**[프롬프트 — Claude Code CLI에게]**

```
청킹 + Haiku + Sonnet 모듈이 모두 구현되었다. 통합 테스트를 수행한다.

■ 작업: 파이프라인 통합 모듈 + E2E 테스트
1. backend/core/pipeline.py — 전체 파이프라인 오케스트레이션
2. scripts/test_pipeline.py — E2E 테스트 스크립트

■ pipeline.py 구조
   analyze_article(article_text: str) → AnalysisResult
   - chunker.chunk(article_text) → chunks
   - pattern_matcher.match(chunks) → haiku_result
   - report_generator.generate(haiku_result, article_text) → report

■ E2E 테스트 (골든 데이터셋 기사 3건)
   - 장문(A-01), 중문(B-11), 단문(D-01) 각 1건씩
   - 출력:
     a. 청크 수 / 평균 길이
     b. 벡터 검색 후보 (패턴 코드 + 유사도)
     c. Haiku 확정 패턴 (코드 + severity + reasoning)
     d. Sonnet 리포트 (cite 태그 확인)
     e. 총 처리 시간, API 호출 횟수, 토큰 사용량
   - 기대값과의 비교: expected_patterns vs Haiku 확정 패턴
```

**[완료 기준]**
- [ ] `backend/core/pipeline.py` 생성됨
- [ ] 기사 3건의 E2E 테스트가 에러 없이 완료됨
- [ ] 각 기사별 청킹→검색→Haiku→규범조회→Sonnet 전 과정이 순차 실행됨
- [ ] 테스트 결과가 콘솔에 구조화되어 출력됨

---

### STEP 42. Claude.ai — 파이프라인 1차 감리

**[감리 대상]**
- `backend/core/chunker.py` (Phase B 감리 통과 전제, 변경사항 있으면 재감리)
- `backend/core/pattern_matcher.py`
- `backend/core/report_generator.py`
- `backend/core/pipeline.py`
- E2E 테스트 결과

**[체크리스트]**

파이프라인 정합성:
- [ ] 마스터 플랜 7.2의 흐름과 코드 구현이 일치하는가
- [ ] 각 모듈 간 데이터 흐름(입출력 타입)이 일관되는가

Haiku 프롬프트 리뷰:
- [ ] 전체 28개 패턴 목록이 정확한가 (메타 패턴 제외, 1-2 주석 포함)
- [ ] 벡터 검색 후보가 ★ 마크로 구분되는가
- [ ] 출력 JSON 포맷이 후속 처리에 적합한가
- [ ] "기사에서 확인되는 문제만 선택" 지시가 명확한가

Sonnet 프롬프트 리뷰:
- [ ] 결정론적 인용 지시가 명확한가 (<cite ref/> 태그만 출력)
- [ ] 규범 컨텍스트가 tier 역순으로 정렬되는가
- [ ] 메타 패턴 관련 지시가 제거되었는가 (M5 이관)

밸리데이션 로직:
- [ ] 코드→ID 변환이 정확한가
- [ ] 환각 코드 제거 시 로그가 남는가
- [ ] DB 미존재 코드가 실제로 탈락하는가

E2E 테스트 결과:
- [ ] 3건 모두 에러 없이 완료되었는가
- [ ] Haiku 확정 패턴이 기대값과 대체로 일치하는가 (정성적 판단)
- [ ] cite 태그가 올바른 형식인가
- [ ] 토큰 사용량이 마스터 플랜 7.4 예산 범위 내인가

**[판정]** ✅ PASS / ❌ FAIL (수정사항 명시)

---

### STEP 43. 마누스 — 파이프라인 2차 독립 감리

**[감리 범위]** 전체 파이프라인 코드 + E2E 테스트 결과

**[중점 확인]**
- [ ] Anthropic 모델 호출 파라미터 (temperature, max_tokens 등) 적절한가
- [ ] 에러 핸들링: API 타임아웃, rate limit, 빈 응답 등에 대한 대응
- [ ] 보안: API 키 노출 없는가, 기사 텍스트 로깅 시 개인정보 처리
- [ ] Haiku/Sonnet 프롬프트가 한국어 뉴스 도메인에 최적화되었는가

**[판정]** ✅ PASS / ❌ FAIL

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase D: 벤치마크 v3 (전체 파이프라인 대상)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> ⚠️ **체크포인트**: Phase C 감리 통과 후 시작. 여기서부터는 Day 6 또는 별도 세션 권장.

### STEP 44. Claude Code CLI — 벤치마크 v3 스크립트 작성

**[프롬프트 — Claude Code CLI에게]**

```
파이프라인 감리 통과. 전체 파이프라인 대상 벤치마크를 수행한다.

■ 작업: 벤치마크 v3 스크립트
scripts/benchmark_pipeline_v3.py를 생성하라.

■ 벤치마크 설계 (M3 최종 결론 섹션 3.3 기반)

1. **대상**: 골든 데이터셋 26건 전체 (TP 20 + TN 6)
   - 데이터 소스: docs/golden_dataset_final.json (article_key_text 포함)
   - 레이블: docs/golden_dataset_labels.json
   - 기사 원문: Golden_Data_Set_Pool/article_texts/

2. **3단 지표 측정**:

   a. Candidate Recall (벡터 검색 단계):
      - 벡터 검색이 반환한 후보에 expected_patterns이 포함되었는가
      - 목표: ≥ 70%
      - 의미: 벡터 검색이 최소한 정답을 후보군에 넣어주는가

   b. Final Recall (Haiku 확정 단계):
      - Haiku가 최종 확정한 패턴이 expected_patterns과 일치하는가
      - 목표: ≥ 80%
      - 의미: 전체 파이프라인의 탐지율

   c. Final Precision (Haiku 확정 단계):
      - Haiku 확정 패턴 중 expected_patterns에 실제로 있는 비율
      - 목표: ≥ 60%
      - 의미: 오탐(false positive) 통제

3. **TN 처리**:
   - TN 6건: Haiku가 "문제 없음"으로 판정해야 함
   - TN에서 패턴을 잘못 식별하면 False Positive로 기록

4. **출력 포맷**:
   - 건별 상세 (기사ID, expected, candidate_retrieved, haiku_confirmed, recall, precision)
   - 대분류별 집계
   - 전체 평균 (3개 지표)
   - 처리 시간, API 비용 추정
   - ⚠️ Sonnet은 벤치마크에서 실행하지 않음 (비용 절약, Haiku 확정까지만 측정)

5. **결과 저장**: docs/M4_BENCHMARK_RESULTS.md
```

**[완료 기준]**
- [ ] `scripts/benchmark_pipeline_v3.py` 생성됨
- [ ] 3개 지표(Candidate Recall, Final Recall, Final Precision)가 모두 측정됨
- [ ] TN 6건의 False Positive가 기록됨
- [ ] 결과가 docs/M4_BENCHMARK_RESULTS.md에 저장됨

---

### STEP 45. Claude.ai — 벤치마크 스크립트 1차 감리

**[감리 대상]** `scripts/benchmark_pipeline_v3.py`

**[체크리스트]**
- [ ] 3개 지표 계산 로직이 정확한가
  - Candidate Recall: 벡터 검색 후보 vs expected
  - Final Recall: Haiku 확정 vs expected
  - Final Precision: Haiku 확정 중 expected에 있는 비율
- [ ] 골든 데이터셋 26건이 빠짐없이 포함되는가
- [ ] TN 처리가 올바른가 (패턴 감지 시 FP 기록)
- [ ] Sonnet이 벤치마크에서 실행되지 않는가 (비용 절약)
- [ ] 결과 포맷이 M3 벤치마크와 일관되는가 (비교 가능)

**[판정]** ✅ PASS / ❌ FAIL

---

### STEP 46. Claude Code CLI — 벤치마크 v3 실행

**[시점]** STEP 45 감리 통과 후.

**[실행]**
```bash
cd /Users/gamnamu/Documents/cr-check
python scripts/benchmark_pipeline_v3.py
```

**[주의사항]**
- 26건 전체 실행 시 Haiku API 비용 발생 (~$0.26 추정)
- 기사 원문 로딩 시 파일 경로 확인
- API rate limit 고려하여 건 사이 1초 sleep 추가
- ⚠️ **실행 결과가 FAIL이면 이 세션에서 즉시 수정하지 않는다** → STEP 48로 이동

---

### STEP 47. Claude.ai — 벤치마크 결과 1차 분석 + 판정

**[분석 대상]** `docs/M4_BENCHMARK_RESULTS.md`

**[판정 기준]**

| 지표 | 목표 | 판정 |
|------|------|------|
| Candidate Recall | ≥ 70% | ✅ PASS / ❌ FAIL |
| Final Recall | ≥ 80% | ✅ PASS / ❌ FAIL |
| Final Precision | ≥ 60% | ✅ PASS / ❌ FAIL |
| TN False Positive Rate | < 30% | ✅ PASS / ⚠️ WARN |

**[분석 포인트]**
- M3 벤치마크(벡터 검색 단독) 대비 개선폭
- 대분류별 성능 편차 (1-7 언어, 1-5 인권은 M3에서 특히 약했음)
- Candidate Recall이 낮으면: threshold 조정 또는 청킹 전략 문제
- Final Recall이 높고 Candidate Recall이 낮으면: Haiku가 벡터 검색 없이도 잘 찾는 것
- Final Precision이 낮으면: Haiku가 오탐이 많은 것 → 프롬프트 조정 필요

**[결과 경로]**

```
3개 지표 모두 PASS → STEP 49(마무리)로 진행
1~2개 FAIL      → STEP 48(감리 협의 + 조정)으로 이동
3개 모두 FAIL    → 감리 합동 회의 소집
```

---

### STEP 48. (조건부) 감리 협의 + 조정

**[트리거]** STEP 47에서 1개 이상 FAIL 시.

**[원칙]**
- ⚠️ 같은 세션에서 즉시 수정하지 않는다
- Claude.ai가 분석 소견 제시 → Gamnamu 검토 → 조정 방향 합의 → CLI 새 세션에서 수정

**[조정 옵션]**

| 실패 지표 | 조정 방향 |
|----------|-----------|
| Candidate Recall < 70% | threshold 하향 (0.15), match_count 상향 (20) |
| Final Recall < 80% | Haiku 프롬프트 보강 (패턴 설명 확장, few-shot 예시 추가) |
| Final Precision < 60% | Haiku 프롬프트 제약 강화 ("확실한 경우만 선택") |
| 복합 실패 | Haiku → Sonnet 4 또는 Haiku 4.5 → Haiku 4.6(출시 시) 모델 업그레이드 검토 |

**[재벤치마크]** 조정 후 STEP 46~47 반복 (최대 2회)

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Phase E: 마무리 + 인수인계
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 49. Claude Code CLI — SESSION_CONTEXT v15→v16 갱신

**[작업]**
```
M4 완료. SESSION_CONTEXT를 v16으로 갱신하라.

■ v15→v16 변경사항:
- M4 RAG 파이프라인 구현 완료
- 벤치마크 v3 결과 기록 (3개 지표 값)
- 확정된 threshold 값
- Haiku 프롬프트 최종 버전 경로
- 다음 작업: M5 (결정론적 인용 후처리 + 메타 패턴 추론)
- v15를 _archive_superseded/로 이동
```

---

### STEP 50. Gamnamu — M4 최종 승인

**[체크리스트]**
- [ ] 벤치마크 v3 결과가 목표를 달성했는가
- [ ] 파이프라인이 마스터 플랜 7.2 구조와 일치하는가
- [ ] SESSION_CONTEXT v16이 정확하게 갱신되었는가
- [ ] M5 범위가 명확한가 (결정론적 인용 후처리 + 메타 패턴 추론)

**[판정]** ✅ M4 완료 승인 / ❌ 추가 작업 필요

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 비상 시나리오 (Emergency Scenarios)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 비상 I: Haiku API 지속 타임아웃

**[상황]** Haiku 호출이 반복적으로 타임아웃되는 경우
**[대응]**
1. 기사 텍스트를 청크 상위 3개만으로 축소하여 재시도
2. max_tokens 축소 (1024→512)
3. 여전히 실패 시 Haiku → Sonnet으로 임시 대체 (비용 증가 감수)

### 비상 J: Haiku 출력이 JSON 파싱 불가

**[상황]** Haiku가 JSON이 아닌 자유 텍스트로 응답하는 경우
**[대응]**
1. 시스템 프롬프트에 "반드시 JSON만 출력" 강조 추가
2. 출력 앞뒤의 마크다운 코드블록(```json) 자동 제거 로직 추가
3. 3회 연속 파싱 실패 시 해당 기사 스킵 + 로그

### 비상 K: 벡터 검색이 0건 반환 (threshold 0.2에서도)

**[상황]** 특정 기사에서 벡터 검색 결과가 전혀 없는 경우
**[대응]**
1. threshold를 0.0으로 하향 → 유사도 상위 10개 강제 반환
2. 이 경우에도 Haiku에게 전체 28개 패턴 목록이 제공되므로 패턴 식별 가능
3. 벤치마크에서 해당 건의 Candidate Recall을 별도 표기

### 비상 L: 골든 데이터셋 기사 파일 접근 불가

**[상황]** article_texts/ 폴더의 기사 파일이 누락되거나 인코딩 오류
**[대응]**
1. golden_dataset_final.json의 article_key_text를 대체 입력으로 사용
2. 해당 건은 벤치마크 결과에 "(key_text 대체)" 표기
3. 원본 파일 복구 후 재벤치마크

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 구조 요약
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
Phase A — 앙상블 보류 건 해결
├─ STEP 32: Claude.ai — 메타 패턴 라우팅 확정
├─ STEP 33: Claude.ai — 1-2 투명성 필터링 확정
├─ STEP 34: Claude.ai — get_ethics_for_patterns 입력 타입 확정
└─ STEP 35: Gamnamu — 보류 건 3건 일괄 승인

Phase B — 기사 청킹 구현 + 감리
├─ STEP 36: CC CLI — 청킹 모듈 구현
├─ STEP 37: Claude.ai — 청킹 1차 감리
└─ STEP 38: 마누스 — 청킹 2차 감리

Phase C — 1.5회 호출 파이프라인 구현 + 감리
├─ STEP 39: CC CLI — 벡터 검색 + Haiku 모듈 구현
├─ STEP 40: CC CLI — Sonnet 리포트 모듈 구현
├─ STEP 41: CC CLI — 파이프라인 통합 + E2E 테스트
├─ STEP 42: Claude.ai — 파이프라인 1차 감리
└─ STEP 43: 마누스 — 파이프라인 2차 감리

Phase D — 벤치마크 v3
├─ STEP 44: CC CLI — 벤치마크 스크립트 작성
├─ STEP 45: Claude.ai — 벤치마크 스크립트 감리
├─ STEP 46: CC CLI — 벤치마크 실행
├─ STEP 47: Claude.ai — 결과 분석 + 판정 (★ 분기점)
└─ STEP 48: (조건부) 감리 협의 + 조정

Phase E — 마무리
├─ STEP 49: CC CLI — SESSION_CONTEXT v16 갱신
└─ STEP 50: Gamnamu — M4 최종 승인
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M3 대비 M4의 구조적 차이점
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 항목 | M3 | M4 |
|------|-----|-----|
| **핵심 산출물** | 임베딩 401개 + 벤치마크 결과 | RAG 파이프라인 코드 4개 모듈 + 벤치마크 결과 |
| **감리 대상** | Python 스크립트 1개 + 실행 결과 | Python 모듈 4개 + 프롬프트 2개 + E2E 결과 |
| **외부 API** | OpenAI (임베딩만) | OpenAI (임베딩) + Anthropic (Haiku+Sonnet) |
| **벤치마크 지표** | Recall@10 (1개) | Candidate Recall + Final Recall + Final Precision (3개) |
| **분기 복잡도** | Recall 기준 3경로 | 3개 지표 조합 분기 |
| **FAIL 시 대응** | 모델 교체/세분화 | 프롬프트 조정/threshold 조정/모델 업그레이드 |
| **비용** | ~$0.01 | ~$0.30 (26건 벤치마크) |
| **M5로 이관** | 임베딩 모델 재평가 | 결정론적 인용 후처리 + 메타 패턴 추론 |

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M4 완료 기준 (Definition of Done)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- [ ] `backend/core/chunker.py` — 기사 청킹 모듈 구현 + 감리 통과
- [ ] `backend/core/pattern_matcher.py` — 벡터 검색 + Haiku 패턴 식별 모듈 구현 + 감리 통과
- [ ] `backend/core/report_generator.py` — 규범 조회 + Sonnet 리포트 모듈 구현 + 감리 통과
- [ ] `backend/core/pipeline.py` — 전체 파이프라인 오케스트레이션 구현 + 감리 통과
- [ ] 벤치마크 v3 실행 완료 (Candidate Recall ≥ 70%, Final Recall ≥ 80%, Final Precision ≥ 60%)
- [ ] 벤치마크 결과가 docs/M4_BENCHMARK_RESULTS.md에 기록됨
- [ ] 앙상블 보류 건 3건 해결됨
- [ ] SESSION_CONTEXT v16 갱신 완료
- [ ] Gamnamu 최종 승인

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## M5 예고 (M4 완료 후)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

M5의 예상 범위 (M4 결과에 따라 조정 가능):

1. **결정론적 인용 후처리**: cite 태그 → DB 원문 치환 + 정규식 검증 (마스터 플랜 결정 F)
2. **메타 패턴 추론 로직**: pattern_relations의 inferred_by 기반 규칙 엔진 + Sonnet 종합 판단 (마스터 플랜 섹션 8)
3. **임베딩 모델 재평가** (선택): M3에서 이월된 건. M4 벤치마크에서 Candidate Recall이 낮으면 우선순위 상향
4. **클라우드 배포**: 임베딩 + M4 코드 일괄 클라우드 배포

---

*이 플레이북은 2026-03-29 Claude.ai가 초안으로 작성하고, 같은 날 Gamnamu가 확정했다.*  
*M1~M3 플레이북(CR_CHECK_WEEK1_PLAYBOOK.md, CR_CHECK_M3_PLAYBOOK.md)의 삼각편대 감리 흐름과 STEP 구조를 동일하게 적용했다.*
