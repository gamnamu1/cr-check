# M5 STEP 67 — 독립 감리 프롬프트

> 작성: Claude.ai (2026-03-29)
> 대상: Antigravity + Manus (각각 별도 프롬프트)
> 시점: STEP 66 (Claude.ai 1차 감리) PASS 후

---

## A. Antigravity용 감리 프롬프트

> Antigravity는 로컬 파일 읽기 권한이 있습니다. 경로만 안내합니다.

```
당신은 CR-Check 프로젝트의 독립 감리자입니다.
M5 Phase D(결정론적 인용 후처리)의 구현물을 2차 독립 감리해주세요.
Claude.ai가 1차 감리를 PASS 판정했으므로, 1차 감리에서 놓쳤을 수 있는 문제를 집중 검토합니다.

■ 프로젝트 배경 (간략)

CR-Check는 AI 기반 한국 뉴스 기사 품질 분석 도구입니다.
파이프라인 흐름:
  기사 → 청킹 → 벡터검색 → Sonnet(패턴 식별) → 규범 조회 → Sonnet(리포트) → [신규] CitationResolver → 최종 리포트

Sonnet 리포트에 <cite ref="JCE-03"/> 형태의 태그가 포함되며,
CitationResolver가 이 태그를 실제 규범 원문으로 치환합니다.

핵심 설계 결정(Gamnamu 승인):
- 옵션 B — in-memory 매칭 전용. DB fallback 조회를 하지 않음.
- Sonnet에게 제공된 규범 컨텍스트(ethics_refs) 내에서만 매칭.
- 컨텍스트 밖의 ref는 환각으로 간주하여 제거.

■ 감리 대상 파일 (로컬 경로)

1. [신규 모듈] /Users/gamnamu/Documents/cr-check/backend/core/citation_resolver.py (129줄)
2. [수정 파일] /Users/gamnamu/Documents/cr-check/backend/core/pipeline.py (116줄)
3. [미수정 확인] /Users/gamnamu/Documents/cr-check/backend/core/report_generator.py (215줄)
4. [테스트] /Users/gamnamu/Documents/cr-check/scripts/test_citation_resolver.py (215줄)

■ 참조 문서 (필요시)

- /Users/gamnamu/Documents/cr-check/docs/SESSION_CONTEXT_2026-03-29_v17.md
- /Users/gamnamu/Documents/cr-check/docs/DB_AND_RAG_MASTER_PLAN_v4.0.md (섹션 7.2~7.3)
- /Users/gamnamu/Documents/cr-check/docs/CR_CHECK_M5_PLAYBOOK.md (STEP 65~67)

■ 감리 체크리스트

[1] 코드 품질 + 보안
- [ ] citation_resolver.py에 DB 조회 코드(httpx, supabase, sb_url, sb_key 등)가 없는가 (옵션 B 준수)
- [ ] 정규식(_CITE_PATTERN)에 ReDoS 취약점이 없는가
- [ ] resolve_citations()에서 예외 발생 시 원본 리포트가 보존되는 구조인가 (pipeline.py의 try/except 확인)
- [ ] 환각 ref 제거 시 리포트 텍스트가 깨지지 않는가 (빈 문자열 치환 후 이중 공백 등)
- [ ] logging이 적절한가 (민감 정보 노출 없이 디버깅에 충분한 정보)

[2] 기능 정합성
- [ ] cite 태그 정규식이 Sonnet의 실제 출력 형식과 매칭되는가
      (report_generator.py의 _SONNET_SYSTEM_PROMPT에서 지시한 형식 확인)
- [ ] _truncate_text()의 절단 로직이 한국어 텍스트에서 정상 작동하는가
      (한국어는 공백이 영어보다 적으므로, 200자 이내에 공백이 없는 경우 고려)
- [ ] 중복 인용 처리(seen_codes)가 정확한가 — 첫 출현=원문, 이후=참조
- [ ] ref_map 구축 시 동일 코드 중복 처리가 합리적인가 (첫 번째만 사용)

[3] 아키텍처 정합성
- [ ] pipeline.py의 CitationResolver 삽입 위치가 올바른가
      (generate_report() 직후, result.report_result 할당 직전)
- [ ] report_generator.py가 수정되지 않았는가
- [ ] 마스터 플랜(DB_AND_RAG_MASTER_PLAN_v4.0.md 섹션 7.2)의
      파이프라인 흐름과 일치하는가

[4] 엣지 케이스
- [ ] ethics_refs가 빈 리스트일 때 resolve_citations()가 안전하게 통과하는가
- [ ] report_text가 None이거나 빈 문자열일 때 처리가 적절한가
- [ ] Sonnet이 cite 태그를 하나도 출력하지 않은 경우 (패턴은 감지했으나 규범 인용 없이 서술한 경우)

[5] 테스트 충분성
- [ ] test_citation_resolver.py의 테스트 케이스가 핵심 시나리오를 커버하는가
- [ ] 누락된 엣지 케이스 테스트가 있는가

■ 판정

✅ PASS / ❌ FAIL (수정사항 명시)

특히 1차 감리(Claude.ai)가 놓쳤을 수 있는 관점에서 검토해주세요:
- 한국어 텍스트 특성에 따른 절단 로직 문제
- 정규식의 엣지 케이스
- 환각 제거 후 텍스트 자연스러움 (이중 공백, 구두점 연속 등)
- 보안 관점 (입력 검증, 로깅 안전성)
```

---

## B. Manus용 감리 프롬프트

> Manus는 로컬 파일 접근이 불가합니다. 아래 파일들을 첨부해주세요.

### 첨부할 파일 목록

| # | 파일 경로 | 설명 |
|---|----------|------|
| 1 | `/Users/gamnamu/Documents/cr-check/backend/core/citation_resolver.py` | 신규 모듈 (감리 핵심 대상) |
| 2 | `/Users/gamnamu/Documents/cr-check/backend/core/pipeline.py` | 수정 파일 (통합 부분) |
| 3 | `/Users/gamnamu/Documents/cr-check/backend/core/report_generator.py` | 미수정 확인용 (Sonnet 프롬프트 형식 참조) |
| 4 | `/Users/gamnamu/Documents/cr-check/scripts/test_citation_resolver.py` | 테스트 스크립트 |
| 5 | `/Users/gamnamu/Documents/cr-check/docs/SESSION_CONTEXT_2026-03-29_v17.md` | 프로젝트 상태 (배경 이해용) |

### 프롬프트

```
당신은 CR-Check 프로젝트의 독립 감리자입니다.
M5 Phase D(결정론적 인용 후처리)의 구현물을 2차 독립 감리해주세요.
Claude.ai가 1차 감리를 PASS 판정했으므로, 1차 감리에서 놓쳤을 수 있는 문제를 집중 검토합니다.

■ 프로젝트 배경 (간략)

CR-Check는 AI 기반 한국 뉴스 기사 품질 분석 도구입니다.
파이프라인 흐름:
  기사 → 청킹 → 벡터검색 → Sonnet(패턴 식별) → 규범 조회 → Sonnet(리포트) → [신규] CitationResolver → 최종 리포트

Sonnet 리포트에 <cite ref="JCE-03"/> 형태의 태그가 포함되며,
CitationResolver가 이 태그를 실제 규범 원문으로 치환합니다.

핵심 설계 결정(Gamnamu 승인):
- 옵션 B — in-memory 매칭 전용. DB fallback 조회를 하지 않음.
- Sonnet에게 제공된 규범 컨텍스트(ethics_refs) 내에서만 매칭.
- 컨텍스트 밖의 ref는 환각으로 간주하여 제거.

■ 첨부 파일 설명

1. citation_resolver.py — 이번 STEP에서 신규 생성된 모듈. 감리 핵심 대상.
2. pipeline.py — CitationResolver 통합 부분 (import 1줄 + try/except 블록 추가).
3. report_generator.py — 수정되지 않아야 하는 파일. Sonnet 프롬프트의 cite 태그 지시 형식 참조용.
4. test_citation_resolver.py — 유닛 테스트 + E2E 테스트 스크립트.
5. SESSION_CONTEXT_2026-03-29_v17.md — 프로젝트 전체 상태 (배경 이해용).

■ 감리 체크리스트

[1] 코드 품질 + 보안
- [ ] citation_resolver.py에 DB 조회 코드(httpx, supabase, sb_url, sb_key 등)가 없는가 (옵션 B 준수)
- [ ] 정규식(_CITE_PATTERN)에 ReDoS 취약점이 없는가
- [ ] resolve_citations()에서 예외 발생 시 원본 리포트가 보존되는 구조인가 (pipeline.py의 try/except 확인)
- [ ] 환각 ref 제거 시 리포트 텍스트가 깨지지 않는가 (빈 문자열 치환 후 이중 공백 등)
- [ ] logging이 적절한가 (민감 정보 노출 없이 디버깅에 충분한 정보)

[2] 기능 정합성
- [ ] cite 태그 정규식이 report_generator.py의 _SONNET_SYSTEM_PROMPT에서 지시한 형식과 매칭되는가
- [ ] _truncate_text()의 절단 로직이 한국어 텍스트에서 정상 작동하는가
      (한국어는 공백이 영어보다 적으므로, 200자 이내에 공백이 없는 경우 고려)
- [ ] 중복 인용 처리(seen_codes)가 정확한가 — 첫 출현=원문, 이후=참조
- [ ] ref_map 구축 시 동일 코드 중복 처리가 합리적인가 (첫 번째만 사용)

[3] 아키텍처 정합성
- [ ] pipeline.py의 CitationResolver 삽입 위치가 올바른가
      (generate_report() 직후, result.report_result 할당 직전)
- [ ] report_generator.py가 수정되지 않았는가
- [ ] 전체 파이프라인 흐름이 논리적으로 일관되는가

[4] 엣지 케이스
- [ ] ethics_refs가 빈 리스트일 때 resolve_citations()가 안전하게 통과하는가
- [ ] report_text가 None이거나 빈 문자열일 때 처리가 적절한가
- [ ] Sonnet이 cite 태그를 하나도 출력하지 않은 경우

[5] 테스트 충분성
- [ ] test_citation_resolver.py의 테스트 케이스가 핵심 시나리오를 커버하는가
- [ ] 누락된 엣지 케이스 테스트가 있는가

■ 판정

✅ PASS / ❌ FAIL (수정사항 명시)

특히 1차 감리(Claude.ai)가 놓쳤을 수 있는 관점에서 검토해주세요:
- 한국어 텍스트 특성에 따른 절단 로직 문제
- 정규식의 엣지 케이스
- 환각 제거 후 텍스트 자연스러움 (이중 공백, 구두점 연속 등)
- 보안 관점 (입력 검증, 로깅 안전성)
```

---

## 1차 감리(Claude.ai) 결과 요약 — 감리자 참고용

STEP 66 판정: ✅ PASS

주요 확인 사항:
- 옵션 B 준수 (DB 조회 코드 없음) ✅
- cite 태그 정규식 3종 변형 대응 ✅
- 치환 형식 「title: 원문」 정상 ✅
- 200자 절단 어절 경계 ✅
- 중복 인용 축약 ✅
- 환각 ref 제거 + WARNING 로그 ✅
- pipeline.py graceful fallback ✅
- report_generator.py 미수정 ✅
- 마스터 플랜 정합성 ✅

1차 감리에서 관찰한 경미한 사항 (FAIL 아님):
1. 마침표 뒤 절단 시 "보도한다...." (마침표+말줄임표) 가능성 — 발생 빈도 낮아 수용
2. ethics_refs의 코드가 JEC (JCE 아님) — CitationResolver 동작에 영향 없으나 문서와 불일치

*이 감리 프롬프트는 2026-03-29 Claude.ai가 작성했습니다.*
