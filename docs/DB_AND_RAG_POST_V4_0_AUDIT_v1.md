# CR-Check v4.0 이후 — 추가 진단 리포트

> **문서 상태**: Post-Audit (DB_AND_RAG_MASTER_PLAN_v4.0 보강)
> **작성일**: 2026-04-17
> **전제**: v4.0 로드맵(Phase 0~3 + Phase D/E/F-2)과 v32 후속 작업(Phase F 회귀 검증 → LAYER2_AUDIT_REPORT.md 통합 → commit → Phase G STEP 3)이 완료된 직후 시점
> **진단 범위**: 프로덕션 DB 상태(`vwaelliqpoqzeoggrfew`) + main 브랜치 코드 + v32 운영 컨텍스트
> **작성 주체**: Claude.ai 1차 감리 (Supabase MCP read-only + GitHub MCP 조회)

---

## 0. 한 줄 요약

v4.0 계획이 의도한 롤업·인용 아키텍처는 **DB 레이어와 RPC 레이어에서 정확히 구현되어 있다.**
리포트에서 롤업이 눈에 띄지 않는 현상의 원인은 **데이터나 함수의 부재가 아니라, Sonnet이 받는 `ethics_context` 문자열에서 "직접 매핑 조항 vs 롤업된 상위 조항"의 구분이 표시되지 않아 프롬프트 지시가 일관되게 실행되지 않는 데** 있다. 해소 작업은 v4.0 인프라와 **충돌 없이 독립적으로** 수행 가능하며, Phase H 혹은 별도 소마일스톤으로 편입을 권한다.

---

## 1. 진단 배경

2026-04-17 대화에서 기획자로부터 제기된 문제 인식:

> "리포트에서 기사 속에 있는 여러 문제 패턴 중 (롤업할 가치가 있는) 한 개 정도의 패턴에 대해 롤업을 하면 좋겠다고 제안했는데, 현재 실질적으로 롤업이 표시되지 않고 있다."

이 관찰은 다음 네 가지 가설로 분해된다.

| 가설 | 내용 |
|---|---|
| H1 | `ethics_code_hierarchy` 혹은 `ethics_codes.parent_code_id`가 비어 있어 상위 조항을 참조할 수 없다 |
| H2 | RPC 함수 자체가 롤업 로직을 구현하지 않았다 |
| H3 | 파이프라인 코드가 RPC를 호출하지 않는다 |
| H4 | 모든 레이어는 작동하지만 Sonnet의 출력 단계에서 롤업이 표면화되지 않는다 |

본 진단의 목적은 위 네 가설을 실증적으로 구별하는 것이다.

---

## 2. 실증 결과

### 2.1 데이터 레이어 — H1 기각

```sql
SELECT COUNT(*) AS total, COUNT(parent_code_id) AS with_parent
FROM ethics_codes WHERE is_active = TRUE;
-- 결과: total=394, with_parent=384 (97.5% 충족)
```

`ethics_codes.parent_code_id`는 전체 394건 중 **384건(97.5%)**이 채워져 있다. 단일 부모 롤업 체인은 사실상 완비되어 있으며, 미충족 10건은 Tier 1 최상위 조항(헌장 자체)으로 추정된다. `ethics_code_hierarchy`(42건)는 v4.0 §5.3이 명시한 "다대다 확장 대비 Junction Table"로 남아 있으며, 현 시점에 활용되지 않는 것은 설계 의도와 일치한다.

### 2.2 RPC 레이어 — H2 기각

`get_ethics_for_patterns` 함수의 DDL을 프로덕션에서 직접 추출한 결과, v4.0 §6.1에 명시된 재귀 CTE 롤업이 **그대로 구현되어 있다.** 앙상블 검증의 수정사항까지 반영되어 있다.

```sql
-- 프로덕션 함수 본문에서 발췌
WITH RECURSIVE direct_codes AS (
  -- 1단계: pattern_ethics_relations에서 직접 연결된 규범
  ...
),
parent_chain AS (
  -- 2단계: 직접 규범의 parent chain을 재귀적으로 수집 (구체→포괄 롤업)
  -- [C-01 fix] pattern_id를 base case에서 상속하여 CROSS JOIN 제거
  -- [W-01 fix] depth 카운터로 무한 루프 방지 (최대 5)
  ...
  WHERE ... AND child.depth < 5
)
```

### 2.3 실제 호출 결과 — H2/H4 판별

패턴 1-1-4(사실과 의견 혼재)에 대한 RPC 실행 결과:

| ethics_code | title | tier | relation_type | strength | reasoning |
|---|---|---|---|---|---|
| PCP-3-1 | 보도기사의 사실과 의견 구분 | 2 | violates | strong | 직접 적용 |
| PCP-3-2 | 공정보도 | 2 | violates | strong | 직접 적용 |
| PCP-10-1 | 제목의 원칙 | 2 | violates | strong | 직접 적용 |
| JEC-1 | 진실을 추구한다 | 1 | violates | strong | Layer 2 감리 확정 |
| **PCE-4** | 보도와 평론 | 2 | related_to | moderate | **parent chain rollup** |
| **JEC-4** | 공정하게 보도한다 | 1 | related_to | moderate | **parent chain rollup** |

**직접 매핑 4건 + 롤업 2건**이 정확히 반환되었다. 재귀 CTE가 실제로 작동하며, reasoning 필드에 `"parent chain rollup"` 마커로 롤업 여부가 구분되어 있다.

### 2.4 코드 레이어 — H3 기각

`backend/core/report_generator.py`는 `fetch_ethics_for_patterns` 함수에서 `/rest/v1/rpc/get_ethics_for_patterns`를 호출하고, 반환된 row를 `_build_ethics_context`에서 tier 역순으로 정렬하여 Sonnet 프롬프트에 주입한다. `_SONNET_SYSTEM_PROMPT`에는 롤업 수행 지시가 명시되어 있다 — "리포트 전체에서 1~2회 정도는 구체적 조항에서 상위 원칙(Tier 1~2)으로 의미를 확장하는 서술을 넣으세요."

### 2.5 결론 — H4 채택

네 레이어(데이터·RPC·코드·프롬프트)의 모든 구성 요소가 **v4.0 계획대로 정상 작동**한다. 롤업이 리포트 표면에서 일관되게 관찰되지 않는 유일한 구조적 원인은 다음 한 지점에 수렴한다:

> **Sonnet이 받는 `ethics_context` 문자열에서, 직접 매핑된 조항과 parent chain rollup으로 추가된 조항이 시각적으로 구분되지 않는다.** Sonnet은 reasoning 필드("parent chain rollup" 마커)를 볼 수 없으며, tier 기준 정렬만 전달받기 때문에 "어느 조항이 하위 위반이고 어느 조항이 그것의 상위 원칙인지"를 구조적으로 식별할 근거가 약하다. 결과적으로 프롬프트의 "1~2회 상위 원칙 확장" 지시가 불안정하게 실행된다.

이는 **데이터 결핍이 아니라 컨텍스트 직렬화(serialization) 설계의 공백**이다.

---

## 3. v4.0 계획 진행에 대한 정합성 평가

### 3.1 본 진단이 v4.0 실행에 미치는 영향: **무충돌**

v4.0 로드맵(Phase 0 → 1 → 2 → 3, 그리고 v32의 Phase F/STEP 3/H)은 **데이터 레이어 및 RPC 레이어**를 다룬다. 본 진단의 해소 작업은 **애플리케이션 레이어(ethics_context 조립 함수 + Sonnet 프롬프트)**에만 국한되며, v4.0이 건드리는 스키마·시드 데이터·RPC 함수와 단 하나의 충돌점도 없다.

구체적으로:

| v4.0 작업 영역 | 본 진단의 수정 범위 | 충돌 여부 |
|---|---|---|
| `ethics_codes` 스키마 | 건드리지 않음 | ✅ 없음 |
| `ethics_codes_hierarchy` | 건드리지 않음 | ✅ 없음 |
| `get_ethics_for_patterns` RPC | **추가 필드 반환만 고려** (기존 필드 보존) | ⚠️ 하위 호환 유지 필요 |
| 임베딩 생성 | 건드리지 않음 | ✅ 없음 |
| Phase D 아카이빙 | 건드리지 않음 | ✅ 없음 |
| Phase E 배포 | 건드리지 않음 | ✅ 없음 |

유일한 주의 지점은 RPC 확장 시 기존 필드 시그니처를 깨뜨리지 않는 것이다. 현재 RPC는 이미 `reasoning` 필드에 `"parent chain rollup"` 문자열을 반환하므로, 이 값만 코드 레이어에서 활용해도 추가 DDL 없이 해소 가능하다.

### 3.2 v4.0 → 본 진단 해소의 자연스러운 순서

v4.0 후속 작업(Phase F 회귀 검증 → LAYER2 통합 리포트 → Phase G STEP 3)을 **먼저 마무리한 후** 본 진단을 착수하는 것이 다음 이유로 적합하다.

1. **Phase F 회귀 검증이 현 Sonnet 출력의 기준선을 확정**한다. 이 기준선 없이 롤업 개선의 효과를 측정할 수 없다.
2. **LAYER2_AUDIT_REPORT.md 통합**이 현 pattern_ethics_relations 분포 해석을 완결한다. 특히 JEC 직접 매핑 23건(20.9%)이 본 진단에서 다시 쟁점이 된다(§4.2 참조).
3. **STEP 3 조건부 벡터 안전망** 구현이 완료되면 Phase 1 후보 집합이 안정되며, 그 다음 Phase 2 프롬프트·ethics_context 개선이 의미 있는 비교 대상이 된다.

---

## 4. 부수적 발견 사항

본 진단 과정에서 v4.0 로드맵과 별개로 확인된 보조 이슈들.

### 4.1 `analysis_ethics_snapshot` 0건 — 인용 보존 메커니즘 Dormant

v4.0 §7.2와 §10.3은 "Sonnet이 실제로 `<cite ref/>`로 인용한 규범만 스냅샷 저장, `CitationResolver`가 cite 태그를 파싱하는 시점에 해당 규범을 스냅샷 테이블에 함께 INSERT"를 명시한다. 실제로 `analysis_results` 71건이 생성되는 동안 이 테이블은 **0건**으로 유지되고 있다.

**원인 추정:** v32의 Phase γ에서 "`<cite>` 태그 기계적 치환 방식 폐기 → 윤리 전문을 Phase 2 Sonnet 프롬프트에 직접 주입"으로 인용 방식이 전환되면서 `CitationResolver`가 비활성화되었다. 이에 따라 스냅샷 트리거(cite 태그 파싱 시점)도 함께 dormant 상태가 되었다.

**영향:** 시간 축의 정직성 이슈. 언론윤리 규범은 실제로 개정되며(감염병보도준칙·인권보도준칙 등 상황 대응형 규범은 상대적으로 자주 갱신된다), 개정 후에 과거 리포트가 인용한 조항의 원문을 추적할 수단이 없어진다. 외부 공개 후 1~2년이 지나 첫 개정이 발생하는 시점에 리포트의 근거가 "댕기는 링크" 상태가 될 수 있다.

**해소 방향 (개요):**
1. Phase 2 리포트 생성 직후 `ethics_refs`(이미 `ReportResult`에 담겨 있음) 중 실제 리포트 본문에 `ethics_code`가 인용되어 등장한 것만 추려서 `analysis_ethics_snapshot`에 INSERT.
2. 판별 로직은 정규식 또는 문자열 검색으로 충분하며, 기존 `<cite ref/>` 태그 기반 파싱 없이도 구현 가능.
3. v4.0 §10.2의 개정 워크플로우는 스키마 변경 없이 그대로 재활성화 가능.

### 4.2 Layer 2 감리와 롤업의 역할 분담 재정의 필요

v32 §13.4 기준 pattern_ethics_relations 111건 중 **JEC 직접 매핑이 23건(20.9%)**이다. 이 중 다수는 Layer 2 감리(2026-04-15 확정 발견 7건 포함)에서 **직접 매핑으로 추가된 항목**이다.

본 진단의 관점에서 이 결정은 이중의 의미를 가진다:

| 관점 | 평가 |
|---|---|
| 품질 안전장치 | ✅ Sonnet이 롤업 지시를 따르지 않을 가능성에 대비한 **강한 보장** — JEC 조항이 직접 매핑으로 들어오면 Sonnet은 상위 원칙으로 인용할 수밖에 없다 |
| 롤업 RPC와의 관계 | ⚠️ 재귀 CTE 롤업이 정상 작동하는 환경에서는 **부분적 중복** — JEC-1이 직접 매핑으로도, parent chain rollup으로도 반환되는 경우가 발생 가능 |

실제로 패턴 1-1-4의 RPC 호출 결과에서 JEC-1은 `relation_type='violates'`(직접 매핑, Layer 2 감리 산물)로 반환되고, JEC-4는 `relation_type='related_to', reasoning='parent chain rollup'`으로 반환된다. Sonnet이 `ethics_context` 문자열을 받을 때 둘의 **출처(manual vs auto)가 구분되지 않는 것**은 앞서 §2.5에서 지적한 핵심 병목과 같은 맥락이다.

정책 방향 선택지:
- **A안 (현행 유지):** JEC 직접 매핑을 유지하고 `ethics_context`에서만 구분자 추가. 이중 안전장치 유지.
- **B안 (정리):** Layer 2에서 추가한 JEC 직접 매핑을 `related_to/moderate`로 다운그레이드하거나 삭제하고 롤업에 일임. DB 데이터 모델이 더 깔끔해짐.

**권장:** 외부 공개 준비 단계에서는 **A안(현행 유지) + ethics_context 구분자 추가**가 안전하다. B안은 실 사용 데이터가 누적된 이후 피드백을 보고 재검토한다.

### 4.3 `updated_at` 자동 갱신 트리거 부재

v4.0 §6.1의 스키마에 `updated_at TIMESTAMPTZ DEFAULT now()` 컬럼이 있으나, `handle_updated_at` 함수를 테이블에 연결하는 트리거가 프로덕션에서 **0건**이다. v32 기록의 "2 트리거"와 불일치.

**실질 영향:** 현 단계(수동 큐레이션 중심)에서는 드러나지 않으나, 향후 개정 추적·변경 감사 기능이 요구될 때 문제가 된다.

**해소 방향:** `patterns`, `ethics_codes`, `pattern_ethics_relations` 세 테이블에 `BEFORE UPDATE` 트리거 추가. 1회성 마이그레이션 작업.

---

## 5. 해소 방안 — Phase H (가칭: 리포트 품질 정교화)

### 5.1 제안 마일스톤 구성

| STEP | 작업 | 추정 공수 | 의존성 |
|---|---|---|---|
| H-1 | `_build_ethics_context` 구조화 | 0.5일 | 없음 |
| H-2 | Sonnet 시스템 프롬프트 롤업 지시 강화 | 0.5일 | H-1 완료 |
| H-3 | `analysis_ethics_snapshot` 저장 로직 재활성화 | 1일 | 없음 (병렬 가능) |
| H-4 | `updated_at` 트리거 추가 마이그레이션 | 0.5일 | 없음 (병렬 가능) |
| H-5 | Phase F 회귀 검증 재실행 (롤업 출현 빈도 측정) | 0.5일 | H-1, H-2 완료 |

**총 예상:** 2~3일 (파트타임 기준, H-3/H-4 병행 시).

### 5.2 STEP H-1 상세: `_build_ethics_context` 구조화

**현행** (`backend/core/report_generator.py`의 `_build_ethics_context`):
```python
def _build_ethics_context(refs: list[EthicsReference]) -> str:
    sorted_refs = sorted(refs, key=lambda x: (-x.ethics_tier, x.ethics_code))
    seen = set()
    lines = []
    for ref in sorted_refs:
        if ref.ethics_code in seen:
            continue
        seen.add(ref.ethics_code)
        lines.append(
            f"### {ref.ethics_title} (코드: {ref.ethics_code}, Tier {ref.ethics_tier})\n"
            f"{ref.ethics_full_text}"
        )
    return "\n\n".join(lines)
```

**개선안:** reasoning 필드의 `"parent chain rollup"` 마커를 활용해 `ethics_context`를 **두 섹션으로 분할**.

```python
def _build_ethics_context(refs: list[EthicsReference]) -> str:
    """두 섹션으로 분할: (A) 직접 매핑 조항 (B) 구체→포괄 롤업된 상위 조항."""
    direct = [r for r in refs if r.reasoning != "parent chain rollup"]
    rollup = [r for r in refs if r.reasoning == "parent chain rollup"]
    
    direct_sorted = sorted(direct, key=lambda x: (-x.ethics_tier, x.ethics_code))
    rollup_sorted = sorted(rollup, key=lambda x: (x.ethics_tier, x.ethics_code))
    
    lines = []
    
    if direct_sorted:
        lines.append("## [A] 탐지된 패턴과 직접 연결된 조항 (우선 인용 대상)")
        seen = set()
        for ref in direct_sorted:
            if ref.ethics_code in seen:
                continue
            seen.add(ref.ethics_code)
            lines.append(
                f"### {ref.ethics_title} "
                f"(코드: {ref.ethics_code}, Tier {ref.ethics_tier}, 관계: {ref.relation_type}/{ref.strength})\n"
                f"{ref.ethics_full_text}"
            )
    
    if rollup_sorted:
        lines.append("\n## [B] 상위 원칙으로 롤업된 조항 (맥락 확장용)")
        lines.append("※ 아래 조항들은 위 [A] 조항들이 구체화하는 상위 원칙입니다.")
        lines.append("※ 리포트 전체에서 1~2회 정도, [A]의 구체적 위반을 지적한 뒤 [B]의 상위 원칙으로 확장하는 서술을 권장합니다.")
        seen = set()
        for ref in rollup_sorted:
            if ref.ethics_code in seen:
                continue
            seen.add(ref.ethics_code)
            lines.append(
                f"### {ref.ethics_title} (코드: {ref.ethics_code}, Tier {ref.ethics_tier})\n"
                f"{ref.ethics_full_text}"
            )
    
    return "\n\n".join(lines)
```

**효과:** Sonnet이 받는 컨텍스트에서 "이 조항은 직접 위반인가, 롤업된 상위 원칙인가"가 시각적으로 명백해진다. 프롬프트 지시의 실행 가능성이 구조적으로 보장된다.

### 5.3 STEP H-2 상세: 시스템 프롬프트 강화

`_SONNET_SYSTEM_PROMPT`의 "규범 인용의 깊이" 섹션을 다음과 같이 수정:

> **현행**: "리포트 전체에서 1~2회 정도는 구체적 조항에서 상위 원칙(Tier 1~2)으로 의미를 확장하는 서술을 넣으세요."
>
> **개선**: "관련 윤리규범은 [A] 직접 연결 조항과 [B] 상위 롤업 조항으로 제공됩니다. 리포트 본문의 지적은 반드시 [A] 조항을 근거로 작성하되, 종합 평가 부분(또는 가장 핵심적인 지적 1~2회)에서 [A]의 구체적 위반이 [B]의 어떤 상위 원칙을 구조적으로 훼손하는지 확장 서술하세요. [A] 조항의 직접 인용 없이 [B] 조항만 단독으로 인용하지 마세요."

### 5.4 STEP H-3 상세: analysis_ethics_snapshot 재활성화

`generate_report` 함수 반환 직전 또는 `save_analysis_result` 내부에서 다음 단계를 수행:

```python
# generate_report 이후 save 단계에서:
# 1. 실제 리포트 본문 3종을 문자열로 합침
report_text = "\n".join(reports.values())

# 2. ethics_refs 중 report_text에 실제로 인용된 조항만 필터
cited = []
for ref in ethics_refs:
    # 조항 제목 또는 코드가 리포트에 등장하면 인용된 것으로 간주
    if ref.ethics_title in report_text or ref.ethics_code in report_text:
        cited.append(ref)

# 3. analysis_ethics_snapshot에 INSERT
for ref in cited:
    httpx.post(
        f"{sb_url}/rest/v1/analysis_ethics_snapshot",
        headers=headers,
        json={
            "analysis_id": analysis_id,
            "ethics_code_id": <ref의 ethics_code로 조회한 id>,
            "snapshot_full_text": ref.ethics_full_text,
            "snapshot_version": <현재 ethics_codes.version>,
        },
    )
```

**주의:** 인용 판별 로직은 v4.0 §7.2의 `<cite ref/>` 태그 파싱 방식보다 느슨하지만, 현재 Sonnet이 자연어로 조항명을 인용하는 방식과 정확히 일치한다. v32 Phase γ의 전환 결정과 호환된다.

### 5.5 STEP H-4 상세: updated_at 트리거

```sql
-- 마이그레이션 파일 (예: 20260420000000_add_updated_at_triggers.sql)
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER patterns_updated_at
  BEFORE UPDATE ON public.patterns
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER ethics_codes_updated_at
  BEFORE UPDATE ON public.ethics_codes
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
```

**주의:** `pattern_ethics_relations`에는 `updated_at` 컬럼이 없어 트리거 생성 전 컬럼 추가가 선행되어야 한다(선택 사항).

### 5.6 STEP H-5 상세: 회귀 검증

Phase F 테스트 세트(53건)를 H-1·H-2 적용 후 재실행하여 다음 메트릭을 측정:

| 메트릭 | 현재 기준선 (추정) | 목표 |
|---|---|---|
| Tier 1 조항 인용이 포함된 리포트 비율 | 측정 필요 | > 50% |
| "상위 원칙으로 확장" 서술이 포함된 리포트 비율 | 측정 필요 | > 30% |
| 직접 매핑 조항의 인용 누락 비율 | 측정 필요 | < 10% |

메트릭은 단순 키워드 검색(JEC-*, `언론윤리헌장`, `~원칙을`, `~구체화한 것`)으로 1차 판별 가능하며, 샘플 기반 수동 감리를 보조로 한다.

---

## 6. 외부 공개 관점에서의 가치 판단

CR-Check가 시민 미디어 리터러시 도구로 기능하기 위해, **"왜 이 기사가 문제인가"를 구조적으로 설명하는 능력**은 점수·등급을 대체하는 서술형 리포트의 핵심 설득력이다.

현 시점 리포트는 "신문윤리실천요강 제3조 1항을 어겼다"까지는 지적하지만, "이것이 결국 언론윤리헌장 제1조의 진실 추구 원칙 자체를 훼손한다"까지 연결하는 빈도가 낮다. 전자는 **기술적 위반 지적**이고 후자는 **규범적 의미 설명**이다. 시민 독자에게는 후자가 훨씬 더 중요하다. 노르딕 언론위원회 모델에서 감나무 님이 영감을 얻은 "시민이 언론을 읽는 관점을 형성한다"는 기획 의도에 가장 가까운 리포트 스타일은 이 확장 서술에서 나온다.

Phase H의 해소 작업은 **외부 공개 가치 제안의 강도를 크게 높이는 반면 공수는 2~3일로 제한적**이다. 시빅해킹 그룹·언론 시민사회 커뮤니티와의 첫 시연 이전에 완료하는 것이 특히 의미 있다.

---

## 7. 우선순위 제안

본 진단에 따른 권장 작업 순서:

```
[v32 현행 작업]
1. Phase F 회귀 검증 (CLI)
2. LAYER2_AUDIT_REPORT.md 통합 작성
3. git commit (criteria_checklist.json + ethics_to_pattern_map.json)
4. Phase G STEP 3 착수 (조건부 벡터 안전망)

        ↓ (현행 우선순위 완료 후)

[Phase H — 본 리포트 제안]
5. H-1: _build_ethics_context 구조화 ← 즉시 착수 가능
6. H-2: 시스템 프롬프트 롤업 지시 강화 ← H-1 직후
7. H-3: analysis_ethics_snapshot 재활성화 ← 5·6과 병행 가능
8. H-4: updated_at 트리거 추가 ← 5·6·7과 병행 가능
9. H-5: Phase F 회귀 검증 재실행 (품질 개선 확인)

        ↓ (Phase H 완료 후)

[시빅해킹/시민사회 커뮤니티 시연 준비]
10. 베타 공개 체크리스트 수립
11. 외부 접촉 개시
```

---

## 8. 부록: 진단에 사용된 실증 증거

### 8.1 사용된 쿼리 및 도구

| 레이어 | 확인 수단 | 결과 |
|---|---|---|
| DB 스키마 | Supabase MCP `list_tables verbose=true` | 9 테이블, RLS 활성, `parent_code_id` 컬럼 존재 확인 |
| 뷰 정의 | `SELECT definition FROM pg_views` | `active_ethics_codes`, `ethics_codes_history` 뷰 정의 확인 |
| RPC 본문 | `SELECT pg_get_functiondef(oid) FROM pg_proc` | 재귀 CTE 롤업 구현 확인 |
| parent_code_id 충족률 | 집계 쿼리 | 394건 중 384건 (97.5%) |
| RPC 실행 테스트 | `SELECT * FROM get_ethics_for_patterns(ARRAY[12])` | 직접 4건 + 롤업 2건 정상 반환 |
| 코드 검증 | GitHub MCP `get_file_contents` on `report_generator.py` | `fetch_ethics_for_patterns` RPC 호출 및 `_build_ethics_context` 조립 확인 |
| 프롬프트 검증 | `_SONNET_SYSTEM_PROMPT` 원문 확인 | 롤업 지시 존재, 시각적 구분자 주입 없음 |

### 8.2 핵심 데이터 샘플 — 패턴 1-1-4 RPC 응답 전체

```
pattern_id=12 ("1-1-4 사실과 의견 혼재")

[직접 매핑]
- PCP-3-1 "보도기사의 사실과 의견 구분" (Tier 2, violates/strong)
- PCP-3-2 "공정보도" (Tier 2, violates/strong)
- PCP-10-1 "제목의 원칙" (Tier 2, violates/strong)
- JEC-1 "진실을 추구한다" (Tier 1, violates/strong) 
  [Layer 2 감리 2026-04-15, 3명 확정]

[Parent chain rollup (자동)]
- PCE-4 "보도와 평론" (Tier 2, related_to/moderate)
- JEC-4 "공정하게 보도한다" (Tier 1, related_to/moderate)
```

이 6건이 Sonnet에게 동일한 포맷(`### 제목 (코드: X, Tier Y)` + 전문)으로 주입되며, 직접 매핑과 롤업의 구분 마커가 없다. 이것이 §2.5에서 지적한 핵심 병목이다.

---

*이 리포트는 2026-04-17 Claude.ai의 DB+코드 동시 진단에서 도출되었다.*
*v4.0 계획 문서와 병행 참조를 전제로 작성되었으며, v4.0의 Phase 0~3 로드맵·RPC 설계·스키마 결정에 어떠한 수정도 요구하지 않는다.*
*후속 작업(Phase H)은 애플리케이션 레이어(`_build_ethics_context`, 시스템 프롬프트, 스냅샷 저장 로직)에 한정되며 v4.0 인프라와 완전히 독립적으로 수행 가능하다.*
