# CR-Check Phase H 실행계획 v1.0

> **문서 상태**: Active — Single Source of Truth
> **작성일**: 2026-04-21
> **목적**: 38→119 패턴 세분화 + 리포트 품질 개선 전 작업의 완결 실행 기준
> **사전 문서 참조 불필요**: 이 문서 하나로 Phase H 전 작업을 실행 가능하게 작성됨

---

## 0. 이 문서를 읽는 방법

[Claude Code CLI]: §3(절대 원칙) → §4(역할) → 현재 STEP 절 순서로 읽는다.
[Claude.ai 감독]: 전체 통독 후 기획자 질문에 답한다.
[기획자 Gamnamu]: §1(배경)으로 맥락 파악 후 현재 STEP에서 판단·실행.

---

## 1. Phase H가 필요한 이유

### 1.1 직전까지의 작업 요약

R4~R7 실험에서 두 가지가 확인됐다.

(1) **이진 게이트가 병목이었다.**
Devil's Advocate CoT에서 "(가) 양질 판정 → detections=[]" 구조가
벡터가 찾아준 정답의 ~46%를 기각하고 있었다.
이진 게이트를 제거(R5)하자 FR이 26.7% → 36.7%로 상승했다.

(2) **프롬프트 패치는 작동하지 않는다.**
1-4 오탐을 막기 위해 가드 규칙을 추가했더니 FR이 오히려 R4보다 낮아졌다.
패턴 판단 기준은 메인 프롬프트가 아니라 DB description 필드에 있어야 한다.

### 1.2 근본 원인

38개 소분류로 압축된 description 안에 여러 독립 개념이 뭉쳐 있다.
이로 인해 임베딩 벡터의 방향성이 분산되고,
Sonnet이 패턴 간 경계를 모호하게 인식한다.
이는 프롬프트로 해결되지 않는 데이터 레이어의 구조적 문제다.

### 1.3 AUDIT 문서에서 추가 발견된 품질 과제

(A) **롤업 미가시화**: RPC 롤업 로직은 정상 작동하지만, Sonnet이 받는
ethics_context에서 직접 매핑 조항 vs 롤업 조항이 구분되지 않아
"상위 원칙 확장" 지시가 불안정하게 실행된다.

(B) **analysis_ethics_snapshot 0건**: CitationResolver 비활성화 후
스냅샷 저장도 멈췄다. 규범 개정 시 과거 리포트의 인용 근거 추적 불가.

(C) **updated_at 트리거 부재**: patterns, ethics_codes,
pattern_ethics_relations 세 테이블에 변경 이력 추적 트리거가 없다.

### 1.4 현재 고정 상태 (Phase H 착수 전 기준선)

| 항목 | 상태 |
|---|---|
| Phase 1 프롬프트 | R5 — 이진 게이트 제거 + 독립 패턴 평가 |
| 커밋 | `1795eb0` (feature/fix-generate-embeddings-script) |
| 벤치마크 기준 | FR 36.7% / Precision 44.2% / TN FP 6/6 (R5, 구 골든셋) |
| 골든셋 | 수정 확정 (§2.2 참조) |

---

## 2. 착수 전 확정 사항

### 2.1 프롬프트 최적화 트랙 중단 결정

T-2 트랙(description 어휘 재작성) — Phase H 완료 후 재개.
프롬프트 패치 실험(R8 이후) — 중단.
Phase G 매핑 복원 작업 — Phase H 완료 후 재개.

유지되는 것: R5 프롬프트 구조, Phase G에서 복원된 63건 매핑,
벤치마크 스크립트, 골든셋 구조.

### 2.2 골든셋 TN 라벨 수정 (2026-04-21 확정)

| ID | 제목 | 변경 | 근거 |
|---|---|---|---|
| C-02 | 트랜스젠더 보고서 | TN → **제거** | R5~R7 전 버전 일관 FP. 1-4 경계선 표현 실재. |
| C2-07 | 대리 입영 적발 | TN → **유지** | R5·R7 FP / R6 OK 불일치. 노이즈 수준. 재독 후 TN 확정. |
| E-17 | AI 여성 성희롱 | TN → **TP** | R4 포함 전 버전 일관 FP. 7-5 실재. |
변경 후 골든셋: TP 21건 + TN 5건 = 총 26건. C-02 제거 후 난이도 유사 기사 1건 보충 필요 (STEP 7에서 처리).

---

## 3. 절대 원칙

(1) CLI 자동 INSERT/UPDATE 금지 — 모든 DB 변경은 기획자가 SQL Editor에서 직접 실행 (2) diff 선제시 → 기획자 승인 → 커밋 순서 엄수 (자동 git add/commit 금지) (3) STEP 단위 승인 게이트 — 기획자 승인 없이 다음 STEP 진행 금지 (4) TN FP Rate 50% 이하 유지 (초과 시 해당 변경 즉시 롤백) (5) ON CONFLICT DO NOTHING — UPSERT 절대 금지 (6) is_citable 일괄 변경 금지 — 실질 내용 확인 후 개별 판단 (7) STEP마다 분포 확인 쿼리 2개 의무 실행 (총량만으로 PASS 불가)

---

## 4. 역할 분담

\[기획자 Gamnamu\] 최종 결정권자·큐레이터

- 코드 체계 설계안 승인/거부
- Supabase SQL Editor에서 모든 INSERT/UPDATE 직접 실행
- STEP 승인 게이트 Go/No-Go 결정
- §9 수동 평가(리포트 품질 기준선 수립) 직접 수행

\[[Claude.ai](http://Claude.ai)\] 감독·감리 — 코칭 파트너

- 방향 설계 및 단계 분할
- CLI에게 전달할 프롬프트 제공
- SQL 초안 작성 (최종 실행은 기획자)
- 감리 의견 취합 및 합의 판단

\[Claude Code CLI\] 실행 에이전트

- 119개 코드 체계 설계안 생성
- 마이그레이션 SQL 초안 생성
- 코드 파일 수정 (diff 선제시 필수)
- generate_embeddings.py 실행
- 벤치마크 스크립트 실행 + 결과 보고
- Deny List: supabase db push, supabase db migration, git commit, git push, git add, rm, mv, sed -i, chmod

\[Antigravity\] 독립 감리 — 로컬 구조 감리

- 로컬 파일 직접 접근, 코드·설계 구조 검토
- 마이그레이션 SQL 구조 검증
- Strict Mode On, Agent Auto-Fix Lints Off

\[Gemini / Manus\] 보조 감리

- Gemini: 한국 언론 현장 어휘, search_text 어휘 적절성
- Manus: 패턴 간 어휘 충돌·중복 분석
- 주의: 수치·인용 디테일은 원본 증거로 교차 검증 후 채택

---

## 5. 전체 작업 흐름

```
[STEP 1] 119개 패턴 코드 체계 설계
    ↓ 교차 감리 → 기획자 승인
[STEP 2] DB 마이그레이션 (search_text 컬럼 + 트리거 + 119개 INSERT)
    ↓ 분포 쿼리 의무 실행 + 교차 감리
[STEP 3] pattern_ethics_relations 재배분
    ↓ 분포 쿼리 의무 실행 + 교차 감리
[STEP 4] _build_ethics_context() 구조화 + 롤업 프롬프트 강화
    ↓ 리포트 샘플 5건 롤업 출현 확인
[STEP 5] analysis_ethics_snapshot 재활성화
    ↓ 분석 1건 실행 후 스냅샷 테이블 확인
[STEP 6] 임베딩 재생성 (search_text 기준)
    ↓ 임베딩 건수 확인
[STEP 7] 골든셋 재정비 + R8 벤치마크
    ↓ §10 성공 기준 대조 + 앙상블 감리
```

---

## 6. STEP 1 — 119개 패턴 코드 체계 설계

### 목표

38개 소분류 레코드를 119개 단일 개념 단위로 분리하는 코드 체계를 설계한다.
### 코드 체계 원칙

기존 38개 소분류 코드(1-1, 1-2 ...)를 상위 코드로 유지한다. 각 소분류 안의 개별 불릿을 하위 코드로 확장한다.

```
형식: {기존 코드}-{알파벳 소문자}
예시:
  1-1 (사실 검증 부실) ← 상위 유지 (hierarchy_level=2)
    1-1-a: 교차 검증 부재 및 단일 취재원 의존
    1-1-b: 취재원 발언의 무비판적 중계
    1-1-c: 인용 정보의 출처 및 신뢰성 문제
    1-1-d: 반론권 미보장
```

### CLI 작업 지시

```
docs/current-criteria_v2_active.md를 읽고
각 소분류(###) 아래 불릿 항목을 1-1-a, 1-1-b 형식으로 코드화한다.
```

```

다음 형식의 표를 출력한다:

신규 코드상위 코드개념명1-1-a1-1교차 검증 부재 및 단일 취재원 의존...
```

총 건수를 확인하고 감나무에게 승인을 요청한다. 파일 생성이나 DB 변경은 하지 않는다.

- 

### 교차 감리 포인트 (STEP 1 완료 후)

(A) 코드 체계 일관성 — 명명 규칙이 전체에 걸쳐 일관되게 적용됐는가 (B) 누락 없음 — current-criteria_v2_active.md 원본과 건수가 일치하는가 (C) 경계 모호 케이스 — 어느 소분류에 속할지 애매한 불릿의 처리가 타당한가 (D) 확장성 — 향후 새 개념 추가 시 이 체계에서 자연스럽게 수용 가능한가

감리 투입: [Claude.ai](http://Claude.ai) + Antigravity + Gemini/Manus 중 1인. 2인 이상 독립 지적 = 수정 필수. 1인 단독 = 기획자 판단.

---

## 7. STEP 2 — DB 마이그레이션

### 7.1 신규 컬럼 추가 — search_text

description 단일 필드가 두 가지 목적을 감당하는 충돌 해소.

필드용도작성 기준`description`Sonnet 리포트 생성 컨텍스트품격 있는 윤리 비평 정의. 어뷰징 어휘 없음.`search_text`벡터 임베딩 소스뉴스 기사에 실제 등장하는 관찰 가능 어휘 중심.

```sql
-- CLI가 초안 생성, 기획자가 SQL Editor에서 실행
ALTER TABLE public.patterns
ADD COLUMN IF NOT EXISTS search_text TEXT;
```

### 7.2 updated_at 트리거 추가

```sql
-- 3개 테이블에 각각 적용
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
```
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

### 7.3 119개 패턴 INSERT

```sql
-- 예시 구조 (STEP 1 승인 후 CLI가 전체 초안 생성)
INSERT INTO public.patterns
  (code, name, description, search_text, category, subcategory,
   hierarchy_level, parent_pattern_id, is_meta_pattern, locale)
VALUES
  ('1-1-a', '교차 검증 부재 및 단일 취재원 의존',
   '복수의 독립적 취재원을 통한 사실 확인 없이 단일 취재원에 의존하는 보도 관행.',
   '단독 취재원, 단일 출처, 교차 검증 없음, 반론 없이, 한쪽 주장만',
   '진실성', '사실 검증 부실', 3,
   (SELECT id FROM patterns WHERE code='1-1'),
   FALSE, 'ko-KR')
ON CONFLICT DO NOTHING;
```

### 7.4 감리 포인트 (STEP 2 완료 후)

필수 쿼리 1 — 패턴별 건수 분포:
```sql
SELECT hierarchy_level, COUNT(*) FROM patterns
GROUP BY hierarchy_level ORDER BY hierarchy_level;
-- 기대: level=2 → 38건, level=3 → ~119건
```

필수 쿼리 2 — search_text 공백 여부:
```sql
SELECT COUNT(*) FROM patterns
WHERE hierarchy_level=3 AND (search_text IS NULL OR search_text='');
-- 기대: 0건
```

감리 투입: description 품질 10건 샘플 → Claude.ai + Antigravity.
search_text 어휘 적절성 → Gemini.

---

## 8. STEP 3 — pattern_ethics_relations 재배분

### 목표

기존 63건 매핑을 119개 새 패턴에 배분한다.
38개 상위 패턴에 연결된 매핑을 적절한 하위 패턴으로 이전.

### 원칙

- strength 3-카테고리 유지: strong(1:1 직접 위반) / moderate(보조 적용) / weak(유추 적용)
- 하위 패턴에 배분 불가능한 매핑은 상위 패턴에 그대로 유지
- 신규 하위 패턴에 추가 매핑이 필요한 경우 큐레이션

### 감리 포인트 (STEP 3 완료 후)

필수 쿼리 1 — 공백 패턴 확인:
```sql
SELECT p.code, p.name, COUNT(per.id) AS mapping_count
FROM patterns p
LEFT JOIN pattern_ethics_relations per ON p.id = per.pattern_id
WHERE p.is_meta_pattern = FALSE AND p.hierarchy_level = 3
GROUP BY p.id, p.code, p.name
ORDER BY mapping_count ASC;
-- 기대: 모든 level=3 패턴이 1건 이상
```

필수 쿼리 2 — 소스별 분포:
```sql
SELECT ec.source, COUNT(*) AS cnt,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM pattern_ethics_relations per
JOIN ethics_codes ec ON per.ethics_code_id = ec.id
GROUP BY ec.source ORDER BY cnt DESC;
-- 기대: PCP 편중 완화, 다양한 소스 분포
```

감리 투입: Claude.ai + Manus (패턴 간 충돌·중복 분석).

---

## 9. STEP 4·5 — 코드 품질 개선 (AUDIT 발견 해소)

### STEP 4: _build_ethics_context() 구조화

AUDIT에서 확인됨: ethics_context 문자열에서 직접 매핑 조항과
롤업 조항이 구분되지 않아 Sonnet의 롤업 지시 실행이 불안정하다.

```python
# 현행: 구분 없이 나열
# 변경 방향: reasoning='parent chain rollup' 조항에 구분자 추가
# 예시:
#   [직접 연결] PCP-3-1 (Tier 2) — 보도기사의 사실과 의견 구분
#   [상위 원칙] JEC-1 (Tier 1) — 진실을 추구한다 ↑ 위 조항의 상위 원칙
```

Sonnet 프롬프트 롤업 지시도 함께 강화.
감리 포인트: 수정 후 리포트 샘플 5건에서 롤업 출현 확인.
투입 감리: Claude.ai + 기획자 직접 확인.

### STEP 5: analysis_ethics_snapshot 재활성화

```python
# 재활성화 방향:
# Phase 2 리포트 생성 직후 report_generator.py에서
# 리포트 본문에 실제 인용된 ethics_code를 문자열 검색으로 추출
# → analysis_ethics_snapshot 테이블에 INSERT
# CitationResolver 없이 구현 가능 (기존 ethics_refs 활용)
```

감리 포인트: 분석 1건 실행 후 analysis_ethics_snapshot 테이블 확인.

---

## 10. STEP 6 — 임베딩 재생성

search_text 필드를 임베딩 소스로 사용하도록 generate_embeddings.py 수정.
description이 아닌 search_text를 임베딩한다.

```
scripts/generate_embeddings.py 증분 실행
-- level=3 신규 119개 패턴만 대상
-- 기존 38개 상위 패턴 임베딩은 유지 (호환성)
```

감리 포인트: 임베딩 건수 확인. 신규 119건 모두 생성됐는지 검증.

---

## 11. STEP 7 — 골든셋 재정비 + R8 벤치마크

### 골든셋 재정비

(A) E-17: TN → TP 전환. golden_dataset_labels.json에서
expected_patterns에 7-5 추가.

(B) C-02: 골든셋에서 제거. 난이도 유사 기사 1건 추가 검토.

(C) 119개 새 코드 기준으로 expected_patterns 전면 재매핑.
예: 기존 1-1 → 해당 하위 코드(1-1-a, 1-1-b 등)로 구체화.

### R8 벤치마크

```
scripts/benchmark_pipeline_v3.py 전체 재측정 (26건)
보고 형식:
  (A) FR / Precision / TN FP Rate (R5 수치와 나란히)
  (B) TN 5건 각각 합격/실패
  (C) 새로 HIT된 TP 케이스 목록
  (D) 여전히 MISS인 패턴 목록
```

### 성공 기준

| 지표 | 목표 |
|---|---|
| FR | R5(36.7%) 대비 개선 |
| Precision | R5(44.2%) 유지 또는 개선 |
| TN FP Rate | 50% 이하 (5건 기준) |
| 리포트 품질 점수 | 기준선 대비 개선 (§12 수동 평가) |
| 롤업 출현 | 리포트 5건 중 3건 이상 |

앙상블 감리 투입: R8 결과를 전원이 독립 검토 후 취합.

---

## 12. 기획자 수동 개입 방법

### 12.1 단일 기사 수동 테스트

```
대상: Golden_Data_Set_Pool/article_texts/ 내 txt 파일
방법: 기사 본문 복사 → CR-Check 프론트엔드 붙여넣기 → 결과 확인
확인 포인트:
  (A) 탐지 패턴이 golden_dataset_labels.json의 expected_patterns와 일치하는가
  (B) 인용된 윤리규범이 해당 패턴과 실제로 연결되는가
  (C) 시민용/기자용/학생용 리포트 어조가 독자에게 적합한가
  (D) 롤업 — 하위 조항 → 상위 원칙으로 연결되는 서술이 있는가
```

### 12.2 리포트 품질 기준선 수립 (STEP 7 전 필수)

골든셋 10건의 현재 리포트를 기획자가 직접 채점.
저장 위치: docs/_scratch/report_quality_baseline.md

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

### 12.3 STEP 1 코드 체계 검토

```
확인 포인트:
  (A) current-criteria_v2_active.md 원본과 비교 — 누락 없는가
  (B) 경계 모호 불릿 — 소분류 귀속이 애매한 경우 처리가 타당한가
  (C) 코드 명명 — 1-1-a 형식이 일관되게 적용됐는가
  (D) 확장성 — 새 개념 추가 시 자연스럽게 수용 가능한가
```

### 12.4 R8 결과 직접 확인

```
확인 항목:
  (A) TN 5건 각각 합격/실패 — 실패 시 어떤 패턴으로 오탐됐는가
  (B) 새로 HIT된 TP 케이스 — 진짜 개선인가
  (C) R5 대비 FR 변화 — 의미 있는 개선인가, 노이즈인가
  (D) 리포트 품질 점수 — §12.2 기준선과 비교
```

---

## 13. 교차 감리 체계 요약

| STEP | 감리 대상 | 투입 감리자 | 합산 원칙 |
|---|---|---|---|
| STEP 1 후 | 119개 코드 체계 설계안 | Claude.ai + Antigravity + Gemini/Manus 중 1 | 2인 이상 지적 = 수정 필수 |
| STEP 2 후 | description 샘플 10개 | Claude.ai + Antigravity | 동일 |
| STEP 2 후 | search_text 어휘 | Gemini | 단독 의견, 기획자 판단 |
| STEP 3 후 | 매핑 분포 쿼리 결과 | Claude.ai + Manus | 2인 이상 지적 = 수정 필수 |
| STEP 4 후 | 리포트 샘플 5건 롤업 | Claude.ai + 기획자 | 기획자 직접 확인 |
| STEP 7 후 | R8 벤치마크 전체 해석 | 전원 앙상블 | 2인 이상 지적 = 수정 필수 |

감리 요청 패키지 구조 (공통):
(1) 변경 대상 항목, (2) 판단 기준(§11 성공 기준),
(3) 확인 요청 포인트, (4) 이전 감리 의견 요약 (앵커링 방지로 마지막에).
다른 감리자 초안·기획자 선호 방향은 비공개 유지.

---

## 14. 향후 트랙 재개 순서

```
Phase H STEP 7 완료 (R8 벤치마크)
    ↓
T-2 트랙 재개 — search_text 필드에 어휘 재작성 (리포트 품질 영향 없음)
    ↓
Phase G 매핑 복원 재개 — 119개 기준으로 공백 패턴 보완
    ↓
리포트 품질 정성 평가 — 기준선 대비 개선 확인
```

---

*작성: Claude.ai — 2026-04-21*
*Phase H 진행에 따라 버전 업데이트 예정*
