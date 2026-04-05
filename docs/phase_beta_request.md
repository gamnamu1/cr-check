# Phase β 작업 요청

첨부한 `docs/phase_beta_cli_prompt.md` 문서에 따라 4건의 수정을 수행해주세요.

## 수정 대상 파일 (2개)
1. `backend/core/report_generator.py` — 수정 1(규범 조회 fallback), 수정 2(프롬프트 교체), 수정 4(컨텍스트 형식)
2. `backend/core/pipeline.py` — 수정 3(citation_resolver 루프 비활성화 + 진단 덤프 CP5 수정)

## 핵심 변경 요약
- `fetch_ethics_for_patterns()`: RPC가 0건일 때 REST API 직접 조회 fallback 추가
- `_SONNET_SYSTEM_PROMPT`: cite 태그 방식을 폐기하고, Sonnet이 규범 원문을 직접 읽고 자연스럽게 인용하도록 전면 교체
- `pipeline.py`의 `resolve_citations` 호출 루프: 주석 처리로 비활성화
- `_build_ethics_context()`: 조항 번호를 Sonnet이 쉽게 인용할 수 있는 형식으로 변경

## 주의사항
- `citation_resolver.py` 파일은 수정/삭제하지 않는다 (pipeline.py에서 호출만 비활성화).
- `_SONNET_SYSTEM_PROMPT_LEGACY`는 수정하지 않는다.
- Supabase REST API의 foreign key 조인(`테이블!inner(컬럼)`)이 동작하지 않으면, 두 번의 개별 쿼리로 분리하여 구현한다.

상세한 수정 내용과 코드는 `docs/phase_beta_cli_prompt.md`에 있다.
