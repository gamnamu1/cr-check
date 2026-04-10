# Phase E — 클라우드 배포 실행 계획서

> **작성일:** 2026-04-07
> **검토·수정:** 2026-04-07 (로컬 코드베이스 대조 검증 완료)
> **기준 문서:** SESSION_CONTEXT v23, DB_AND_RAG_MASTER_PLAN v4.0
> **선행 완료:** M1~M5, M5.5, M6 Phase A~D, Phase γ
> **목표:** `feature/m6-wip` 브랜치의 M6 파이프라인을 프로덕션에 배포

---

## 0. 검토 결과 요약 (v1 → v2 변경 사항)

원본 계획서를 로컬 코드베이스와 대조 검증한 결과, 아래 항목을 수정/보강하였다.

| # | 항목 | 변경 내용 |
|---|------|----------|
| 1 | `generate_embeddings.py` 경로 | `backend/scripts/` → **`scripts/`** (프로젝트 루트) |
| 2 | 임베딩 생성 방식 | REST API 가정 → **psycopg2 직접 PostgreSQL 연결** (Supabase connection string 필요) |
| 3 | 임베딩 대상 검증 수치 | "소분류 약 102건" → **patterns 28건 + ethics_codes 373건 = 401건** |
| 4 | Railway 환경변수 | `SUPABASE_ANON_KEY` **제거** (코드에서 미사용, heartbeat는 GitHub Actions) |
| 5 | BLOCKER-1 보강 | httpx 사용처: db.py 외에 **pattern_matcher·report_generator·meta_pattern_inference·storage.py** 전부 |
| 6 | Supabase 접속 정보 준비 | **PostgreSQL connection string** 확인 단계 추가 (E-2-3 전제 조건) |
| 7 | backend/.env 현황 반영 | 현재 `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`만 존재. SUPABASE 변수 없음 (로컬 자동 감지 의존) |

---

## 1. 현재 상태 진단

### 1-1. 프로덕션 인프라 현황

| 구성 요소 | 현재 상태 | URL |
|-----------|----------|-----|
| **Railway (BE)** | MVP 버전 배포 중, Online | `cr-check-production.up.railway.app` |
| **Vercel (FE)** | MVP 버전 배포 중, Ready | `cr-check.vercel.app` |
| **Supabase** | 프로덕션 DB, FREE 티어 | `vwaelliqpoqzeoggrfew.supabase.co` |
| **GitHub** | `main` 자동 배포, `feature/m6-wip` WIP | `gamnamu1/cr-check` |

**배포 방식:** `main` 브랜치 push 시 Railway + Vercel 자동 배포.
**병합 전략:** `feature/m6-wip` → PR 생성 → `main` 병합.

### 1-2. 프로덕션 Supabase DB 상태

**테이블 (10개 + 뷰 2개):** 모두 존재, 데이터는 시드 데이터만 있음.

| 테이블 | RLS | 데이터 |
|--------|-----|--------|
| patterns | DISABLED | 시드 데이터 있음 (임베딩 미생성 ⚠️) |
| ethics_codes | DISABLED | 시드 데이터 있음 (임베딩 미생성 ⚠️) |
| ethics_code_hierarchy | DISABLED | 시드 데이터 있음 |
| pattern_ethics_relations | DISABLED | 시드 데이터 있음 (정비 미적용 ⚠️) |
| pattern_relations | DISABLED | 시드 데이터 있음 |
| articles | DISABLED | 0건 |
| analysis_results | DISABLED | 0건, **구 스키마** ⚠️ |
| analysis_ethics_snapshot | DISABLED | 0건 |
| feedbacks | DISABLED | 0건 |

**RPC 함수:** `search_pattern_candidates`, `get_ethics_for_patterns`, `get_overall_stats`, `get_publisher_stats`, `get_trending_articles` — 모두 확인됨.

**뷰:** `active_ethics_codes`, `ethics_codes_history` — 확인됨.

### 1-3. `analysis_results` 스키마 차이 (핵심 ⚠️)

프로덕션 DB의 `analysis_results`는 구 스키마. Phase D 마이그레이션 미적용.

| 항목 | 프로덕션 (현재) | 로컬 (Phase D 적용 후) |
|------|----------------|----------------------|
| `share_id` | ❌ 없음 | ✅ TEXT UNIQUE NOT NULL |
| `article_analysis` | ❌ 없음 | ✅ JSONB |
| `overall_assessment` | ❌ 없음 | ✅ TEXT |
| `meta_patterns` | ❌ 없음 | ✅ JSONB |
| `detected_categories` | 있음 | → `detected_patterns`으로 RENAME |
| `phase1_model` 기본값 | Haiku | → Sonnet 4.5로 변경 |

**위험도: 낮음** — 프로덕션 테이블에 데이터가 0건이므로 ALTER/RENAME 안전.

---

## 2. 사전 수정 필수 사항 (PR 생성 전)

### 🔴 BLOCKER-1: `requirements.txt` 누락 패키지

**현재 `backend/requirements.txt` 내용:**
```
fastapi>=0.104.1,<0.120.0
anthropic>=0.49.0,<1.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
weasyprint>=60.0.0          ← ⚠️ 미사용 (export_pdf 주석 처리), 시스템 의존성 빌드 실패 위험
python-multipart>=0.0.6
uvicorn>=0.24.0
python-dotenv>=1.0.0
json_repair>=0.25.0
```

**누락된 핵심 패키지 (코드베이스 검증 결과):**

| 패키지 | 사용처 | 영향 |
|--------|--------|------|
| `httpx` | `db.py`, `storage.py`, `pattern_matcher.py`, `report_generator.py`, `meta_pattern_inference.py` | **서버 시작 불가** |
| `openai` | `pattern_matcher.py` (쿼리 임베딩 생성) | **파이프라인 실행 불가** |

**수정안:**
```
# 추가 필요
httpx>=0.27.0,<1.0.0
openai>=1.0.0,<2.0.0

# 제거 권장 (미사용 + Railway 빌드 실패 위험)
# weasyprint>=60.0.0
```

> **참고:** `json_repair`는 `backend/json_parser.py`에서 사용하나, 현재 활성 파이프라인의 직접 의존은 아님. 제거하지 않는 것이 안전.

### ✅ 해결됨: Railway 시작 명령어

Railway Settings > Source에서 **Root Directory: `backend`**로 설정 확인.
Nixpacks가 `requirements.txt`를 감지하여 Python/FastAPI 앱으로 자동 빌드 + uvicorn 시작. 별도 Procfile 불필요.

### ✅ 해결됨: 프런트엔드 API URL

`frontend/lib/config.ts` 확인 결과:
```typescript
export const CONFIG = {
    API_URL: (() => {
        if (process.env.NEXT_PUBLIC_API_URL) {
            return process.env.NEXT_PUBLIC_API_URL;
        }
        return 'http://localhost:8000';
    })(),
};
```
환경변수 방식. Vercel에 `NEXT_PUBLIC_API_URL` 설정만 필요.
`next.config.js`의 rewrite는 로컬 개발 편의용이며 프로덕션 영향 없음.

### 🟡 WARNING-2: `db.py` 클라우드 전환 로직

**현재 `backend/core/db.py` 코드 (실제 확인):**
```python
def _get_supabase_config() -> tuple[str, str]:
    local_url = "http://127.0.0.1:54321"
    sb_url = os.environ.get("SUPABASE_URL", "")

    if os.environ.get("SUPABASE_LOCAL") or "127.0.0.1" in sb_url or "localhost" in sb_url:
        return local_url, _LOCAL_SERVICE_KEY

    # ⚠️ 여기서 문제: SUPABASE_URL이 클라우드 URL이어도 로컬 체크 실행
    try:
        r = httpx.get(f"{local_url}/rest/v1/patterns?select=id&limit=1",
                      headers={"apikey": _LOCAL_SERVICE_KEY}, timeout=5)
        if r.status_code == 200:
            return local_url, _LOCAL_SERVICE_KEY
    except (httpx.ConnectError, httpx.ReadTimeout):
        pass

    cloud_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return sb_url, cloud_key
```

**문제:** Railway 환경에서 매 API 호출마다 로컬 Supabase 체크 → 5초 타임아웃 대기 후 클라우드 폴백.

**권장 수정안:**
```python
def _get_supabase_config() -> tuple[str, str]:
    sb_url = os.environ.get("SUPABASE_URL", "")

    if os.environ.get("SUPABASE_LOCAL"):
        return "http://127.0.0.1:54321", _LOCAL_SERVICE_KEY

    # 클라우드 URL이 명시적으로 설정되어 있으면 로컬 체크 생략
    if sb_url and "127.0.0.1" not in sb_url and "localhost" not in sb_url:
        cloud_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        return sb_url, cloud_key

    # URL 미설정 또는 로컬 URL → 로컬 시도
    try:
        r = httpx.get("http://127.0.0.1:54321/rest/v1/patterns?select=id&limit=1",
                      headers={"apikey": _LOCAL_SERVICE_KEY}, timeout=5)
        if r.status_code == 200:
            return "http://127.0.0.1:54321", _LOCAL_SERVICE_KEY
    except (httpx.ConnectError, httpx.ReadTimeout):
        pass

    cloud_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return sb_url, cloud_key
```

**효과:** Railway에 `SUPABASE_URL`이 클라우드 URL로 설정되면 로컬 체크를 완전히 건너뛰어 5초 지연 제거.

---

## 3. 배포 실행 단계 (순서 엄수)

### Phase E-1: 코드 수정 (로컬, `feature/m6-wip`)

| STEP | 작업 | 파일 | 상태 |
|------|------|------|------|
| E-1-1 | `requirements.txt`에 `httpx`, `openai` 추가 + `weasyprint` 제거 | `backend/requirements.txt` | 🔴 필수 |
| E-1-2 | `db.py` 클라우드 전환 최적화 (WARNING-2 수정안 적용) | `backend/core/db.py` | 🟡 권장 |
| E-1-3 | CORS 도메인 확인 | `backend/main.py` | 🟡 확인 |
| E-1-4 | 로컬 E2E 테스트 (클라우드 DB 연결) | — | ✅ E-2 이후 |

**E-1-3 상세 (CORS, 코드 확인 결과):**
현재 `main.py`의 `allow_origins`:
```python
[
    "http://localhost:3000",
    "http://localhost:3001",
    "https://cr-check.com",
    "https://cr-check.vercel.app",
    "https://www.cr-check.vercel.app",
]
```
- `cr-check.vercel.app` ✅ 등록됨
- Vercel 프리뷰 URL 패턴(`cr-check-*-gamnamu1s-projects.vercel.app`) ❌ 미등록
- 프리뷰 배포 테스트가 필요하면 와일드카드 패턴 또는 동적 CORS 추가 고려

### Phase E-2: 프로덕션 DB 마이그레이션

**⚠️ 순서 엄수 — 코드 배포(E-4) 전에 DB부터 준비해야 한다.**
코드가 먼저 배포되면 `share_id` NOT NULL 컬럼이 없어서 INSERT 실패.

| STEP | 작업 | 비고 |
|------|------|------|
| E-2-1 | 매핑 정비 마이그레이션 적용 | `20260405000000_cleanup_pattern_ethics_relations.sql` |
| E-2-2 | Phase D 마이그레이션 적용 | `20260406000000_phase_d_analysis_results.sql` |
| E-2-3 | 임베딩 생성 | `scripts/generate_embeddings.py` (**루트 scripts/, backend/ 아님**) |
| E-2-4 | 검증 쿼리 | 아래 참조 |

**E-2-1~E-2-2 실행 방법:**
Supabase Dashboard > SQL Editor에서 각 마이그레이션 파일 내용을 순서대로 실행.

**E-2-3 임베딩 생성 — ★ 중요 수정사항:**

이 스크립트는 **psycopg2**로 PostgreSQL에 **직접 연결**한다 (REST API 아님).
프로덕션 실행 시 Supabase의 PostgreSQL connection string이 필요하다.

> **전제 조건:** Supabase Dashboard > Settings > Database > Connection string(URI)에서
> `postgresql://postgres.[project-ref]:[password]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`
> 형식의 연결 문자열을 미리 확인해둘 것.

```bash
# 프로젝트 루트에서 실행 (backend/ 아님!)
cd /Users/gamnamu/Documents/cr-check

# .venv에 psycopg2 설치 확인 (이미 설치되어 있을 가능성 높음)
# pip install psycopg2-binary  # 필요 시

# 프로덕션 DB에 임베딩 생성
python scripts/generate_embeddings.py \
  --db-url "postgresql://postgres.[project-ref]:[password]@aws-0-...:6543/postgres"
```

**스크립트 동작:**
1. patterns 테이블에서 `hierarchy_level=3, is_meta_pattern=false` → **28건** 조회
2. ethics_codes 테이블에서 `is_citable=true, is_active=true` → **373건** 조회
3. OpenAI `text-embedding-3-small` API로 합계 **401건** 임베딩 생성
4. patterns → `description_embedding` 컬럼, ethics_codes → `text_embedding` 컬럼에 UPDATE
5. 검증 출력: `Patterns with embedding: 28/28`, `Ethics codes with embedding: 373/373`

**예상 비용:** ~401 × 350 tokens × $0.02/1M ≈ $0.003 미만

**E-2-4 검증 쿼리 (SQL Editor에서 실행):**
```sql
-- 1. 임베딩 적재 확인 (patterns)
SELECT COUNT(*) AS total,
       COUNT(description_embedding) AS with_embedding
FROM patterns
WHERE hierarchy_level = 3 AND is_meta_pattern = false;
-- ★ 예상: total = 28, with_embedding = 28

-- 2. 임베딩 적재 확인 (ethics_codes)
SELECT COUNT(*) AS total,
       COUNT(text_embedding) AS with_embedding
FROM ethics_codes
WHERE is_citable = true AND is_active = true;
-- ★ 예상: total = 373, with_embedding = 373

-- 3. Phase D 컬럼 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'analysis_results'
  AND column_name IN ('share_id', 'article_analysis', 'overall_assessment',
                       'meta_patterns', 'detected_patterns');
-- 예상: 5개 행 반환

-- 4. 매핑 정비 확인
SELECT COUNT(*) FROM pattern_ethics_relations;
-- 예상: 63건

-- 5. RPC 함수 동작 확인
SELECT * FROM search_pattern_candidates(
  (SELECT description_embedding FROM patterns WHERE code = '1-1-1' LIMIT 1),
  0.2, 5
);
-- 예상: 유사 패턴 최대 5건 반환
```

### Phase E-3: 환경변수 설정

**Railway (백엔드):**

| 변수 | 값 | 비고 |
|------|-----|------|
| `SUPABASE_URL` | `https://vwaelliqpoqzeoggrfew.supabase.co` | 클라우드 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | (Dashboard > Settings > API > service_role) | ⚠️ anon key 아님 |
| `ANTHROPIC_API_KEY` | (Anthropic Console) | Sonnet 4.5 + 4.6 호출용 |
| `OPENAI_API_KEY` | (OpenAI Dashboard) | 쿼리 임베딩 생성용 |
| `PORT` | Railway 자동 주입 | 설정 불필요 |

> ★ `SUPABASE_ANON_KEY`는 **불필요** — 코드에서 `SUPABASE_SERVICE_ROLE_KEY`만 사용.
> heartbeat 크론잡은 GitHub Actions에서 별도 Secrets로 관리됨.

**현재 `backend/.env` 상태 (로컬 확인 결과):**
`ANTHROPIC_API_KEY`와 `OPENAI_API_KEY`만 있음. SUPABASE 변수 없음 — 로컬에서는 `db.py`의 자동 감지(127.0.0.1:54321 체크)에 의존 중.

**Vercel (프런트엔드):**

| 변수 | 값 | 비고 |
|------|-----|------|
| `NEXT_PUBLIC_API_URL` | `https://cr-check-production.up.railway.app` | 백엔드 URL |
| `NEXT_PUBLIC_SITE_URL` | `https://cr-check.vercel.app` | OG 메타 + 공유 URL 기본 도메인 |

> `layout.tsx`에서 두 환경변수 모두 사용 확인됨 (코드 검증 완료).

### Phase E-4: PR 생성 + 병합 + 자동 배포

| STEP | 작업 |
|------|------|
| E-4-1 | `feature/m6-wip`에서 E-1 수정사항 커밋 |
| E-4-2 | GitHub PR 생성 (`feature/m6-wip` → `main`) |
| E-4-3 | PR 최종 리뷰 (변경 파일 목록 확인) |
| E-4-4 | PR 병합 → Railway + Vercel 자동 배포 트리거 |
| E-4-5 | Railway 빌드 로그 확인 (정상 기동 여부) |
| E-4-6 | Vercel 빌드 로그 확인 |

### Phase E-5: 배포 후 검증

| STEP | 검증 항목 | 방법 | 예상 결과 |
|------|----------|------|----------|
| E-5-1 | 헬스체크 | `GET .../health` | `{"status": "healthy", "api_key_configured": true}` |
| E-5-2 | 프런트엔드 접근 | `cr-check.vercel.app` 브라우저 접속 | UI 정상 렌더링 |
| E-5-3 | TP 기사 분석 | 프런트엔드에서 TP 기사 URL 입력 | 3종 리포트 생성, share_id 발급, ~3~4분 이내 |
| E-5-4 | 캐시 히트 | 동일 URL 재분석 | `is_cached: true`, ~150ms |
| E-5-5 | URL 정규화 캐시 | 동일 URL + `?utm_source=test` | 캐시 히트 |
| E-5-6 | 공유 URL | `/report/{share_id}` 접근 | DB 기반 리포트 렌더링 |
| E-5-7 | OG 메타 | 카카오톡/X에 공유 URL 붙여넣기 | 미리보기 표시 (텍스트만) |
| E-5-8 | TN 기사 | 양질의 기사 URL 분석 | "문제적 보도관행이 발견되지 않았습니다" |
| E-5-9 | 404 처리 | `/report/nonexistent` 접근 | 404 에러 메시지 |
| E-5-10 | DB 저장 확인 | Supabase Table Editor | articles + analysis_results 레코드 확인 |

---

## 4. 위험 요소 및 대응

### 높은 위험도

| 위험 | 영향 | 대응 |
|------|------|------|
| `requirements.txt` 누락 (httpx, openai) | **서버 시작 불가** — 6개 모듈에서 httpx import | E-1-1에서 사전 수정 (BLOCKER) |
| DB 마이그레이션 전에 코드 배포 | `share_id` NOT NULL 위반으로 INSERT 실패 | E-2를 E-4보다 먼저 실행 (순서 엄수) |
| `db.py` 로컬 체크 5초 지연 | 매 API 호출마다 +5초 (캐싱 없음) | E-1-2에서 사전 수정 |
| `weasyprint` 빌드 실패 | Railway 빌드 자체가 실패 (cairo/pango 시스템 의존성) | E-1-1에서 제거 |

### 중간 위험도

| 위험 | 영향 | 대응 |
|------|------|------|
| CORS에 Vercel 프리뷰 URL 미등록 | 프리뷰 배포에서 API 호출 차단 | 필요 시 와일드카드 패턴 추가 |
| Supabase FREE 티어 7일 비활성화 | DB 일시정지 | heartbeat 크론잡 이미 설정됨 ✅ |
| GitHub PAT 만료 (2026-05-05) | push/자동배포 실패 | 배포 후 1개월 내 갱신 |
| `generate_embeddings.py` PostgreSQL 접속 | Supabase connection string 오류 시 임베딩 실패 | E-2-3 전에 connection string 확인 |

### 낮은 위험도

| 위험 | 영향 | 대응 |
|------|------|------|
| `UNIQUE 인덱스 중복` (share_id) | 기능 무관, 스토리지 미세 낭비 | 향후 정리 (Phase G) |
| `_robust_json_parse` fallback 부재 | 간헐적 에러 리포트 저장 | 향후 별도 작업 |
| `og-image.png` 미준비 | 공유 시 이미지 없이 텍스트만 표시 | 선택사항, Phase G |

---

## 5. 롤백 계획

**Railway:** Instant Rollback이 없으므로, 이전 커밋으로 revert 후 push.
- `git revert` 또는 Railway Dashboard > 이전 배포 선택 > Redeploy

**Vercel:** Instant Rollback 버튼으로 즉시 이전 배포 복원 가능.

**Supabase:** 마이그레이션은 되돌리기 어려우나, `analysis_results` 데이터가 0건이므로 최악의 경우 테이블 DROP + 재생성 가능. `pattern_ethics_relations`의 DELETE 7건은 시드 데이터 재삽입으로 복원 가능.

---

## 6. 사전 준비 체크리스트 (Gamnamu 액션 아이템)

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 1 | Railway Start Command 확인 | ✅ 완료 | Root Directory `backend`, Nixpacks 자동 |
| 2 | `frontend/lib/config.ts` API URL 방식 확인 | ✅ 완료 | 환경변수 방식 |
| 3 | Railway Variables 탭 확인 (현재 환경변수) | 🟡 권장 | 기존 MVP 환경변수 확인 |
| 4 | Vercel Environment Variables 확인 | 🟡 권장 | 기존 MVP 환경변수 확인 |
| 5 | `weasyprint` 제거 여부 결정 | 🟡 권장 | 미사용 + 빌드 실패 위험 |
| 6 | Supabase service_role 키 준비 | 🔴 필수 | Dashboard > Settings > API |
| 7 | Supabase PostgreSQL connection string 준비 | 🔴 필수 | Dashboard > Settings > Database > URI (임베딩 생성용) |
| 8 | 로컬 .venv에 psycopg2-binary 설치 확인 | 🟡 권장 | `generate_embeddings.py` 실행 전제 |

---

## 7. 예상 소요 시간

| 단계 | 예상 시간 | 비고 |
|------|----------|------|
| E-1: 코드 수정 | 15~25분 | requirements.txt + db.py + CORS 확인 |
| E-2: DB 마이그레이션 + 임베딩 | 20~35분 | SQL 2건 실행 + 임베딩 API 호출 + 검증 쿼리 |
| E-3: 환경변수 설정 | 10~15분 | Railway + Vercel 대시보드 |
| E-4: PR + 병합 + 빌드 | 10~20분 | 자동 배포 대기 |
| E-5: 검증 | 30~45분 | TP/TN 기사 분석 포함 (각 3~4분) |
| **합계** | **약 1.5~2.5시간** | |

---

## 8. 주요 파일 경로 (코드 검증 완료)

```
프로젝트 루트/
├── scripts/
│   └── generate_embeddings.py       ← ★ 루트 scripts/ (backend/ 아님!)
├── backend/
│   ├── requirements.txt             ← ★ httpx, openai 추가 필요
│   ├── main.py                      ← CORS 설정, /analyze, /report/{share_id}
│   ├── .env                         ← 현재: ANTHROPIC_API_KEY, OPENAI_API_KEY만
│   └── core/
│       ├── db.py                    ← ★ 클라우드 전환 로직 수정 대상
│       ├── storage.py               ← 캐시 + 저장 + URL 정규화
│       ├── pattern_matcher.py       ← httpx + openai import
│       ├── report_generator.py      ← httpx import
│       └── meta_pattern_inference.py ← httpx import
├── frontend/
│   ├── lib/config.ts                ← NEXT_PUBLIC_API_URL 환경변수 방식 ✅
│   └── app/report/[id]/
│       ├── layout.tsx               ← NEXT_PUBLIC_API_URL + NEXT_PUBLIC_SITE_URL 사용
│       └── page.tsx                 ← "use client" 공유 URL 페이지
└── supabase/migrations/
    ├── 20260405000000_cleanup_pattern_ethics_relations.sql
    └── 20260406000000_phase_d_analysis_results.sql
```

---

*이 문서는 2026-04-07에 작성 후, 로컬 코드베이스(`feature/m6-wip` 브랜치)와 대조 검증하여 v2로 수정되었다.*
*검증 범위: requirements.txt, db.py, main.py, storage.py, pattern_matcher.py, config.ts, layout.tsx, next.config.js, generate_embeddings.py, backend/.env, 마이그레이션 SQL 2건.*
*다음 작업: 사전 준비 체크리스트(#6~#8) 완료 후, E-1부터 순서대로 진행.*
