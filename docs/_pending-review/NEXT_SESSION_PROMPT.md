# 다음 세션 첫 프롬프트

## CR-Check 이어서 작업합니다

세션 컨텍스트를 읽어주세요: `docs/SESSION_CONTEXT_2026-04-05_v22.md`

### 오늘 진행할 작업

**작업 0 (즉시): Supabase heartbeat 설정**

Supabase 무료 플랜이 7일 비활성 시 일시중지되므로, GitHub Actions 크론잡을 설정해야 합니다.
`.github/workflows/supabase-heartbeat.yml` 파일을 생성해주세요.

요구사항:
- 주 2회(월·목 UTC 09:00) 실행
- Supabase REST API로 `patterns` 테이블에 간단한 SELECT 쿼리 1건
- GitHub Secrets: `SUPABASE_URL`, `SUPABASE_KEY` 사용
- `workflow_dispatch`로 수동 실행도 가능하게
- 실행 결과를 로그로 출력

생성 후 main 브랜치에 직접 push해주세요 (이건 인프라 설정이므로 main에 바로 적용).
단, GitHub Secrets 등록은 제가 직접 하겠습니다. 어떤 값을 넣어야 하는지 알려주세요.

**작업 1: Phase D 설계 검토**

세션 컨텍스트의 "Phase D" 섹션을 참고하여, Phase D 작업 범위와 구체적 작업 목록을 제안해주세요.
실행은 제 승인 후에 진행합니다.
