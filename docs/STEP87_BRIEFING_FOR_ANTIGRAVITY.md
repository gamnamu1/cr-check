# CR-Check STEP 87 리포트 품질 개선 — 작업 완료 브리핑 (Antigravity용)

## 요약

E2E 테스트에서 확인된 평가 리포트 품질 저하 문제를 Claude.ai(설계·감리) + Claude Code CLI(구현) 체계로 해결했습니다. 이전에 여러 감리자분들이 진단해주신 내용을 종합 분석한 후, 3단계(Phase α → β → 임베딩 생성)에 걸쳐 수정을 진행하여 전체 파이프라인이 정상 작동하고, 리포트 품질이 기존 시스템 수준으로 회복되었습니다.

---

## 해결된 문제들

### Phase α — 버그 수정 3건

**Bug A (벡터 검색 항상 0건):**
- 원인: `patterns` 테이블의 `description_embedding` 컬럼에 벡터 데이터가 한 번도 삽입되지 않았음
- 해결: `scripts/generate_embeddings.py` 실행 → 28개 소분류 + 373개 규범 임베딩 생성 (1536차원)
- 결과: 벡터 검색 정상 작동 (candidate_count: 11건 확인)

**Bug B (Sonnet Solo JSON 파싱 전체 실패):**
- 원인: `matched_text`에 복수 문자열이 쉼표로 나열 → 유효하지 않은 JSON → 전체 탐지 유실
- 해결: `_parse_solo_response()`에 3단계 fallback + 프롬프트 경고 추가
- 결과: 깨진 JSON에서도 패턴 복구 가능

**Bug C (규범 조회 간헐적 0건):**
- 원인: `get_ethics_for_patterns` RPC가 특정 패턴 조합에서 간헐적 실패
- 해결: 재시도 + REST API 직접 JOIN fallback 추가
- 결과: RPC 실패 시 자동 우회

### Phase β — 인용 구조 전환 (핵심 변경)

5개 감리 진단서를 종합한 결과, **Sonnet이 규범 원문 없이 리포트를 작성하고 `<cite>` 태그를 기계적으로 후치환하는 구조**가 품질 저하의 근본 원인으로 확인.

- `_SONNET_SYSTEM_PROMPT` 전면 교체: cite 태그 폐기 → 자연 인용 (조항 번호 명시 + 핵심 문구 발췌)
- `citation_resolver.py` 비활성화 (pipeline.py에서 주석 처리, 코드 보존)
- `_build_ethics_context()` 형식 변경
- 프롬프트 정비: 롤업 정정, 톤 재설계, 스타일 가이드 추가

---

## 현재 파이프라인 흐름

```
기사 → 청킹 → 벡터검색(★ 힌트) → Sonnet 4.6 Solo(패턴 식별)
  → 메타 패턴 추론
  → 규범 조회(RPC + REST API fallback)
  → Sonnet 4.6(3종 리포트: 규범 원문 직접 인용, cite 태그 미사용)
  → 최종 리포트 (citation_resolver 비활성화)
```

---

## 최종 테스트 결과 (4건 전부 성공)

| 기사 | 패턴 | 벡터 후보 | 규범 | 리포트 | 시간 |
|------|------|----------|------|--------|------|
| 세계일보 이준석 | 3건 ✅ | 11건 | 28건 | 3종 ✅ | 100초 |
| 조선일보 이준석 | 2건 ✅ | — | 19건 | 3종 ✅ | 97초 |
| 연합뉴스 노동생산성 | 2건 ✅ | — | 11건 | 3종 ✅ | — |
| 나일 외국인 범죄 | 4건 ✅ | 11건 | 38건 | 3종 ✅ | 133초 |

---

## 남은 Phase γ 작업

1. 조항 번호 표시 통일 (JEC-7 → 언론윤리헌장 제7조)
2. 규범 매핑 정비 (무관한 관계 제거)
3. WIP→main 분리 커밋

---

## 확인해야 할 파일 (로컬 경로)

### 전체 맥락
- `/Users/gamnamu/Documents/cr-check/docs/SESSION_CONTEXT_2026-04-05_v21.md`

### 변경된 코드 (직접 확인 가능)
- `/Users/gamnamu/Documents/cr-check/backend/core/report_generator.py` — 수정 1(REST fallback), 수정 2(프롬프트 교체), 수정 4(컨텍스트 형식)
- `/Users/gamnamu/Documents/cr-check/backend/core/pipeline.py` — 수정 3(citation_resolver 비활성화, 진단 덤프)
- `/Users/gamnamu/Documents/cr-check/backend/core/pattern_matcher.py` — Bug B(JSON fallback, 로깅)

### Phase β 수정 지시서
- `/Users/gamnamu/Documents/cr-check/docs/phase_beta_cli_prompt.md`

### 리포트 비교 (기존 vs 최종)
- `/Users/gamnamu/Documents/cr-check/docs/Test/[기존 cr-check 리포트 샘플 1] CR-Check_Report_1765540952584.txt` — 기존 시스템 리포트
- `/Users/gamnamu/Documents/cr-check/docs/Test/[업데이트 cr-check 리포트 1-2] CR-Check_Report_1775317158765.txt` — Phase β 후 리포트
- `/Users/gamnamu/Documents/cr-check/docs/Test/[업데이트 cr-check 리포트 4] CR-Check_Report_1775343661440.txt` — 최종 리포트

### 진단 데이터
- `/Users/gamnamu/Documents/cr-check/docs/Test/diagnostic_20260405_003734.json` — Phase β 후
- `/Users/gamnamu/Documents/cr-check/docs/Test/diagnostic_20260405_075950.json` — 최종 (벡터 검색 정상화 후)

Phase γ 작업에 대한 감리 의견이나 추가 개선 제안이 있으시면 알려주세요. 특히 변경된 코드(report_generator.py, pipeline.py, pattern_matcher.py)를 직접 확인하시고 누락된 부분이나 우려 사항이 있으면 짚어주시면 감사하겠습니다.
