# 마누스

Phase E 배포 계획서를 검토했습니다. 매우 꼼꼼하고 논리적으로 잘 짜인 계획입니다. 특히 DB 마이그레이션을 코드 배포보다 먼저 수행하도록 명시한 점(E-2 → E-4 순서 엄수), `requirements.txt` 누락 패키지(`httpx`, `openai` )를 사전 발견한 점, `db.py`의 5초 지연 문제를 파악하고 최적화한 점 등은 훌륭한 엔지니어링 감각을 보여줍니다.

전체적으로 이 계획대로 진행해도 무리가 없으나, 완벽한 배포를 위해 **몇 가지 추가로 점검하거나 보완하면 좋을 세부 사항**을 감리 의견으로 제안합니다.

**1. `db.py` 클라우드 전환 로직 보완 (WARNING-2 관련)**

계획서의 `db.py` 수정안은 5초 지연을 없애는 좋은 해결책입니다. 다만, Railway에서 실행될 때 `sb_url`이 설정되어 있어 분기 2번에서 반환될 경우, 반환되는 `cloud_key`가 제대로 설정되어 있는지 보장하는 방어 로직을 약간 더 추가하면 좋습니다.

**현재 제안된 코드 (계획서):**

Python

    `# 2) 클라우드 URL이 명시적으로 설정되어 있으면 로컬 체크 생략
    if sb_url and "127.0.0.1" not in sb_url and "localhost" not in sb_url:
        cloud_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        return sb_url, cloud_key`

**개선 제안:**`SUPABASE_SERVICE_ROLE_KEY`가 환경변수에서 누락되었을 때 빈 문자열(`""`)을 반환하면, 나중에 디버깅하기 어려운 인증 에러가 발생할 수 있습니다. 명시적으로 예외를 발생시키거나 경고 로그를 남기는 것이 좋습니다.

Python

    `# 2) 클라우드 URL이 명시적으로 설정되어 있으면 로컬 체크 생략
    if sb_url and "127.0.0.1" not in sb_url and "localhost" not in sb_url:
        cloud_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not cloud_key:
            raise ValueError("SUPABASE_URL은 설정되었으나 SUPABASE_SERVICE_ROLE_KEY가 없습니다.")
        return sb_url, cloud_key`

**2. CORS 설정과 Vercel 배포 URL (E-1-3 관련)**

계획서에 "Vercel 프리뷰 URL 패턴 미등록" 이슈가 언급되어 있습니다.
Next.js 프론트엔드가 Railway 백엔드를 호출할 때, `NEXT_PUBLIC_API_URL`을 통해 통신하므로 백엔드의 CORS 허용 목록(`allow_origins`)에 프론트엔드의 도메인이 있어야 합니다.

현재 `main.py`의 CORS 목록:

Python

    `"https://cr-check.vercel.app",
    "https://www.cr-check.vercel.app",`

**보완 제안:**
만약 Vercel에서 PR을 올릴 때마다 생성되는 프리뷰 배포 환경에서도 백엔드 API 테스트를 하고 싶다면, 정규식을 사용하는 `allow_origin_regex`를 추가하는 것을 고려해 볼 수 있습니다. (FastAPI 지원 기능 )
당장 필수는 아니지만, 향후 QA를 위해 알아두시면 좋습니다.

Python

`app.add_middleware(
    CORSMiddleware,
    allow_origins=[...],
    allow_origin_regex=r"https://cr-check-.*-gamnamu1s-projects\.vercel\.app",
    ...
 )`

**3. Vercel 환경변수 배포 타이밍**

Phase E-3(환경변수 설정)과 E-4(자동 배포 트리거)의 순서와 관련하여 주의할 점이 있습니다.

- `NEXT_PUBLIC_API_URL` 등은 Vercel에서 빌드 시점(Build Time)에 정적으로 주입되거나 런타임에 사용됩니다.
- 따라서 **E-4에서 PR을 병합하기 전(또는 Vercel이 새 커밋을 빌드하기 전)에 반드시 E-3(Vercel 환경변수 설정)이 완료되어 있어야 합니다.**
- 계획서의 순서(E-3 후 E-4)가 정확히 맞습니다. 이 순서를 반드시 지키도록 리마인드합니다.

**4. 마이그레이션 롤백(Down) 스크립트 부재**

Phase E-2에서 두 개의 마이그레이션 스크립트를 SQL Editor에서 직접 실행하도록 되어 있습니다.

- `20260405000000_cleanup_pattern_ethics_relations.sql`
- `20260406000000_phase_d_analysis_results.sql`

계획서 5장(롤백 계획)에 "최악의 경우 `analysis_results` DROP + 재생성"이라고 적혀 있으나, 수동 조작은 휴먼 에러를 유발할 수 있습니다.
마이그레이션을 적용하기 전에, 문제가 생겼을 때 이전 상태로 되돌리는 **Down SQL(롤백 쿼리)을 미리 메모장 등에 준비해 두는 것**을 권장합니다.

**Phase D 롤백용 예시 쿼리:**

SQL

- `- analysis_results 테이블 롤백
ALTER TABLE analysis_results DROP COLUMN IF EXISTS share_id;
ALTER TABLE analysis_results DROP COLUMN IF EXISTS article_analysis;
ALTER TABLE analysis_results DROP COLUMN IF EXISTS overall_assessment;
ALTER TABLE analysis_results DROP COLUMN IF EXISTS meta_patterns;
ALTER TABLE analysis_results RENAME COLUMN detected_patterns TO detected_categories;`

**5. 임베딩 생성 스크립트 실행 환경 (E-2-3 관련)**

계획서에 `python scripts/generate_embeddings.py`를 로컬에서 실행하여 프로덕션 DB에 접속한다고 되어 있습니다.
이 스크립트는 `openai` 패키지를 사용하므로, 실행하는 로컬 터미널 환경에 `OPENAI_API_KEY` 환경변수가 반드시 세팅되어 있어야 합니다.

**보완 제안:**
명령어 실행 예시에 환경변수 주입을 명시하면 실수를 줄일 수 있습니다.

Bash

`OPENAI_API_KEY="sk-..." python scripts/generate_embeddings.py \
  --db-url "postgresql://postgres.[project-ref]:[password]@aws-0-...:6543/postgres"`

**종합 감리평:**
전체적인 배포 시퀀스(코드 수정 → DB 스키마 마이그레이션 → 임베딩 생성 → 환경변수 세팅 → 코드 배포 → 검증)가 매우 교과서적이고 훌륭합니다. 위에서 제안드린 몇 가지 방어적 코드 추가 및 롤백 대비만 가미하신다면, 장애 없는 무중단 배포가 가능할 것으로 판단됩니다.

이대로 진행하셔도 좋습니다.