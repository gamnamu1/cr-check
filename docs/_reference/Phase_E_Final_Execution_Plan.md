# Phase E — 클라우드 배포 플레이북

> **작성일:** 2026-04-07
> **선행 완료:** M1~M5, M5.5, M6 Phase A~D, Phase γ
> **목표:** `feature/m6-wip` 브랜치의 M6 파이프라인을 프로덕션에 배포
> **예상 소요:** 1.5~2.5시간

---

## 역할 정의

| 역할 | 담당 | 주요 책임 |
|------|------|----------|
| **기획자 (Gamnamu)** | 프로젝트 오너 | 대시보드 조작(Supabase·Railway·Vercel), 최종 승인, GitHub PR 관리 |
| **감리자 (Claude Desktop)** | 코칭·검증 | STEP별 프롬프트 제공, CLI 산출물 검증, 진행 승인 |
| **작업자 (Claude Code CLI)** | 코드 수정·실행 | 프롬프트 단위 작업 수행, 단일 STEP만 진행, 감리 승인 전 다음 STEP 진입 금지 |

**핵심 규칙:** CLI는 프롬프트에 명시된 단일 STEP만 수행한다. 다음 STEP으로의 진행은 감리자의 산출물 확인 + 기획자의 승인이 있어야만 가능하다.

---

## 사전 준비 (기획자)

Phase E 착수 전, 기획자가 대시보드에서 준비할 항목. CLI 작업 시작 전에 완료해야 한다.

| # | 항목 | 확인 방법 |
|---|------|----------|
| 1 | Supabase `service_role` 키 확보 | Dashboard > Settings > API > `service_role` (anon 아님) |
| 2 | Supabase PostgreSQL connection string 확보 | Dashboard > Settings > Database > Connection string(URI). 포트 `6543` 기본, 실패 시 `5432` 시도. |
| 3 | Railway Variables 탭 현재 값 확인 | 기존 MVP에 어떤 환경변수가 설정되어 있는지 스크린샷 또는 메모 |
| 4 | Vercel Environment Variables 현재 값 확인 | 동일 |

> 위 4개가 준비되면 감리자에게 "사전 준비 완료"를 알리고, E-1 프롬프트를 받는다.

---

## STEP E-1: 코드 수정 — `requirements.txt` + `db.py`

### E-1a: `requirements.txt` 수정

**작업자:** CLI
**CLI 프롬프트:**
```
Phase E-1a: backend/requirements.txt 수정.

1. 다음 패키지를 추가:
   httpx>=0.27.0,<1.0.0
   openai>=1.0.0,<2.0.0

2. weasyprint>=60.0.0 줄을 삭제.
   (export_pdf가 주석 처리된 상태이며, Railway에서 cairo/pango 빌드 실패 위험.)

3. 나머지 패키지는 그대로 유지.

수정 후 최종 requirements.txt 내용을 출력해줘.
이 STEP만 수행하고 멈춰. 다음 STEP은 감리 승인 후 진행.
```

**감리자 확인:**
- [ ] httpx, openai 추가 확인
- [ ] weasyprint 삭제 확인
- [ ] 기존 패키지(fastapi, anthropic, beautifulsoup4, requests, python-multipart, uvicorn, python-dotenv, json_repair) 유지 확인

**승인 게이트:** 감리자 확인 완료 → E-1b 진행

### E-1b: `db.py` 클라우드 전환 최적화

**작업자:** CLI
**배경:** 현재 `_get_supabase_config()`는 `SUPABASE_URL`이 클라우드 URL이어도 로컬 Supabase 체크(`httpx.get`, timeout 5초)를 시도한다. Railway에서 매 API 호출마다 5초 지연 발생.

**CLI 프롬프트:**
```
Phase E-1b: backend/core/db.py의 _get_supabase_config() 함수 수정.

현재 코드의 문제: SUPABASE_URL이 클라우드 URL이어도 로컬 체크를 시도하여 5초 지연.

다음과 같이 수정:
1. SUPABASE_LOCAL 환경변수가 있으면 로컬 강제 (기존과 동일)
2. sb_url이 설정되어 있고 "127.0.0.1"도 "localhost"도 포함하지 않으면 →
   로컬 체크 없이 즉시 (sb_url, cloud_key) 반환.
   이때 SUPABASE_SERVICE_ROLE_KEY가 없으면 ValueError 발생시킬 것.
3. 그 외(URL 미설정 또는 로컬 URL) → 기존과 동일하게 로컬 시도 후 클라우드 폴백.

함수 전체를 수정하고, 수정 전/후 diff를 보여줘.
이 STEP만 수행하고 멈춰.
```

**감리자 확인:**
- [ ] 분기 2에서 클라우드 URL 감지 시 로컬 체크 생략 확인
- [ ] `SUPABASE_SERVICE_ROLE_KEY` 누락 시 ValueError 발생 확인
- [ ] 분기 3의 기존 로컬 폴백 로직 보존 확인
- [ ] `_LOCAL_SERVICE_KEY` 상수 미변경 확인

**승인 게이트:** 감리자 확인 완료 → E-1c 진행

### E-1c: CORS 도메인 확인

**작업자:** CLI
**CLI 프롬프트:**
```
Phase E-1c: backend/main.py의 CORS allow_origins 확인.

1. 현재 allow_origins 목록을 출력해줘.
2. "https://cr-check.vercel.app"이 포함되어 있는지 확인.
3. 코드 수정은 하지 마. 현재 상태만 보고해줘.

이 STEP만 수행하고 멈춰.
```

**감리자 확인:**
- [ ] `https://cr-check.vercel.app` 등록 확인
- [ ] Vercel 프리뷰 URL은 미등록 상태 — 당장 필수 아님, Phase G에서 `allow_origin_regex` 추가 고려

**승인 게이트:** 확인 완료 → E-1d 진행

### E-1d: WIP 커밋

**작업자:** CLI
**CLI 프롬프트:**
```
Phase E-1d: E-1a, E-1b 수정사항을 커밋.

git add backend/requirements.txt backend/core/db.py
git commit -m "Phase E-1: requirements.txt 정비 + db.py 클라우드 전환 최적화

- httpx, openai 추가 (서버 필수 의존성)
- weasyprint 제거 (미사용 + Railway 빌드 실패 방지)
- _get_supabase_config(): 클라우드 URL 감지 시 로컬 체크 생략 (5초 지연 제거)"

커밋 후 git log --oneline -3 출력.
이 STEP만 수행하고 멈춰. push는 하지 마.
```

**감리자 확인:**
- [ ] 커밋 메시지와 변경 파일 2개 확인
- [ ] push 하지 않았음을 확인

**승인 게이트:** 확인 완료 → E-2 진행 (기획자 대시보드 작업)

---

## STEP E-2: 프로덕션 DB 준비

**⚠️ 이 단계는 코드 배포(E-4) 전에 반드시 완료해야 한다.**
코드가 먼저 배포되면 `share_id` NOT NULL 컬럼이 없어서 INSERT 실패.

### E-2a: 매핑 정비 마이그레이션

**작업자:** 기획자 (Supabase Dashboard)
**절차:**
1. Supabase Dashboard > SQL Editor 접속
2. 로컬 `supabase/migrations/20260405000000_cleanup_pattern_ethics_relations.sql` 내용을 복사
3. SQL Editor에 붙여넣고 실행
4. "Success" 확인

**감리자 확인:**
- [ ] 기획자가 실행 결과 "Success" 보고

### E-2b: Phase D 마이그레이션

**작업자:** 기획자 (Supabase Dashboard)
**절차:**
1. 로컬 `supabase/migrations/20260406000000_phase_d_analysis_results.sql` 내용을 복사
2. SQL Editor에 붙여넣고 실행
3. "Success" 확인

**감리자 확인:**
- [ ] 기획자가 실행 결과 "Success" 보고

**승인 게이트:** E-2a + E-2b 모두 Success → E-2c 진행

### E-2c: 임베딩 생성

**작업자:** CLI (로컬에서 프로덕션 DB 연결)
**전제:** 기획자가 PostgreSQL connection string을 감리자에게 전달 완료.

**CLI 프롬프트:**
```
Phase E-2c: 프로덕션 DB에 임베딩 생성.

프로젝트 루트의 scripts/generate_embeddings.py를 실행한다 (backend/ 아님).
이 스크립트는 psycopg2로 PostgreSQL에 직접 연결한다.

실행 전 확인:
1. .venv에 psycopg2-binary, openai 패키지가 설치되어 있는지 확인
2. 없으면 pip install psycopg2-binary openai

실행:
OPENAI_API_KEY="[기획자가 제공한 키]" python scripts/generate_embeddings.py \
  --db-url "[기획자가 제공한 connection string]"

예상 출력:
- Patterns (non-meta, 소분류): 28
- Ethics codes (citable, active): 373
- Total embedding targets: 401
- Patterns with embedding: 28/28
- Ethics codes with embedding: 373/373

실행 결과를 전부 출력해줘.
이 STEP만 수행하고 멈춰.
```

> **주의:** connection string과 API key는 기획자가 직접 프롬프트에 삽입한다.
> 포트 `6543` 연결 실패 시 `5432`로 재시도 (Supabase Dashboard에서 대체 URI 확인).

**감리자 확인:**
- [ ] patterns 28/28, ethics_codes 373/373 성공 확인
- [ ] 에러 없음 확인

**승인 게이트:** 확인 완료 → E-2d 진행

### E-2d: 검증 쿼리

**작업자:** 기획자 (Supabase SQL Editor)
**절차:** 아래 5개 쿼리를 순서대로 실행하고 결과를 감리자에게 보고.

```sql
-- 1. patterns 임베딩 (예상: total=28, with_embedding=28)
SELECT COUNT(*) AS total,
       COUNT(description_embedding) AS with_embedding
FROM patterns
WHERE hierarchy_level = 3 AND is_meta_pattern = false;

-- 2. ethics_codes 임베딩 (예상: total=373, with_embedding=373)
SELECT COUNT(*) AS total,
       COUNT(text_embedding) AS with_embedding
FROM ethics_codes
WHERE is_citable = true AND is_active = true;

-- 3. Phase D 컬럼 존재 (예상: 5개 행)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'analysis_results'
  AND column_name IN ('share_id', 'article_analysis',
                       'overall_assessment', 'meta_patterns',
                       'detected_patterns');

-- 4. 매핑 정비 (예상: 63건)
SELECT COUNT(*) FROM pattern_ethics_relations;

-- 5. 벡터 검색 RPC 동작 (예상: 최대 5건 반환)
SELECT * FROM search_pattern_candidates(
  (SELECT description_embedding FROM patterns
   WHERE code = '1-1-1' LIMIT 1),
  0.2, 5
);
```

**감리자 확인:**
- [ ] 5개 쿼리 모두 예상 결과와 일치
- [ ] 특히 쿼리 5(벡터 검색)가 실제 결과를 반환하는지 확인

**승인 게이트:** 전체 일치 → E-3 진행

---

## STEP E-3: 환경변수 설정

**⚠️ 이 단계는 코드 배포(E-4) 전에 반드시 완료해야 한다.**
`NEXT_PUBLIC_*` 환경변수는 Vercel 빌드 시점에 정적 주입되므로 배포 후 설정하면 반영 안 됨.

### E-3a: Railway 환경변수

**작업자:** 기획자 (Railway Dashboard > Variables)
**설정할 변수 (4개):**

| 변수 | 값 |
|------|-----|
| `SUPABASE_URL` | `https://vwaelliqpoqzeoggrfew.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | (사전 준비에서 확보한 service_role 키) |
| `ANTHROPIC_API_KEY` | (Anthropic Console에서 확인) |
| `OPENAI_API_KEY` | (OpenAI Dashboard에서 확인) |

> `PORT`는 Railway 자동 주입. `SUPABASE_ANON_KEY`는 불필요 (코드에서 미사용).

### E-3b: Vercel 환경변수

**작업자:** 기획자 (Vercel Dashboard > Settings > Environment Variables)
**설정할 변수 (2개):**

| 변수 | 값 | 주의사항 |
|------|-----|---------|
| `NEXT_PUBLIC_API_URL` | `https://cr-check-production.up.railway.app` | **끝에 `/` 없음** |
| `NEXT_PUBLIC_SITE_URL` | `https://cr-check.vercel.app` | OG 메타용 |

> URL 끝에 슬래시가 들어가면 fetch 시 `//analyze` 같은 이중 슬래시 에러 발생.

**감리자 확인:**
- [ ] 기획자가 Railway 4개 + Vercel 2개 설정 완료 보고
- [ ] `NEXT_PUBLIC_API_URL` trailing slash 없음 확인

**승인 게이트:** 확인 완료 → E-4 진행

---

## STEP E-4: PR 생성 + 병합 + 자동 배포

**전제 확인 (감리자):** E-2(DB 준비) + E-3(환경변수) 모두 완료되었는가? → 미완료 시 E-4 진입 금지.

### E-4a: WIP 브랜치 push

**작업자:** CLI
**CLI 프롬프트:**
```
Phase E-4a: feature/m6-wip 브랜치를 원격에 push.

git push origin feature/m6-wip

push 결과를 보여줘.
이 STEP만 수행하고 멈춰.
```

**감리자 확인:**
- [ ] push 성공 확인

### E-4b: PR 생성 + 병합

**작업자:** 기획자 (GitHub)
**절차:**
1. GitHub에서 `feature/m6-wip` → `main` PR 생성
2. 변경 파일 목록 리뷰 (감리자와 함께)
3. PR 병합 → Railway + Vercel 자동 배포 트리거

**감리자 확인 (PR 리뷰):**
- [ ] `backend/requirements.txt` 변경 포함
- [ ] `backend/core/db.py` 변경 포함
- [ ] `backend/core/storage.py` 포함 (Phase D)
- [ ] `frontend/app/report/[id]/` 포함 (Phase D)
- [ ] 예상치 못한 파일 변경 없음

### E-4c: 빌드 확인

**작업자:** 기획자 (Railway + Vercel Dashboard)
**절차:**
1. Railway Dashboard > 최신 배포 빌드 로그 확인 → "Listening on 0.0.0.0:PORT" 정상 기동
2. Vercel Dashboard > 최신 배포 빌드 로그 확인 → "Ready" 상태

**감리자 확인:**
- [ ] Railway 빌드 성공, 서버 기동 확인
- [ ] Vercel 빌드 성공 확인
- [ ] 빌드 실패 시 → 롤백 계획(부록 A) 참조

**승인 게이트:** 양쪽 모두 빌드 성공 → E-5 진행

---

## STEP E-5: 배포 후 검증

### E-5a: 헬스체크 + 기본 접근

**작업자:** 기획자 (브라우저/터미널)
**절차:**
1. `curl https://cr-check-production.up.railway.app/health` → `{"status":"healthy","api_key_configured":true}`
2. `https://cr-check.vercel.app` 브라우저 접속 → UI 정상 렌더링

**감리자 확인:**
- [ ] 헬스체크 응답 정상
- [ ] 프런트엔드 UI 렌더링 정상

### E-5b: TP 기사 분석 (핵심 검증)

**작업자:** 기획자 (프런트엔드)
**절차:**
1. 프런트엔드에서 **문제가 있는 뉴스 기사(TP)** URL 입력 → 분석 실행
2. 3종 리포트(일반·전문가·학생) 정상 생성 확인
3. 응답에 `share_id` 포함 확인

**감리자 확인:**
- [ ] 3종 리포트 내용 정상 (〔〕 마커 인용, 패턴 식별)
- [ ] `share_id` 발급됨
- [ ] 소요 시간 ~3~4분 이내

### E-5c: 캐시 + URL 정규화 검증

**작업자:** 기획자 (프런트엔드)
**절차:**
1. E-5b와 **동일한 URL**로 재분석 → `is_cached: true`, ~150ms 확인
2. 동일 URL에 `?utm_source=test` 추가 후 분석 → 캐시 히트 확인

**감리자 확인:**
- [ ] 캐시 히트 정상 (CachedBanner 표시)
- [ ] URL 정규화 캐시 히트 정상

### E-5d: 공유 URL + 404 + OG 메타

**작업자:** 기획자 (브라우저)
**절차:**
1. `https://cr-check.vercel.app/report/{share_id}` 접근 → DB 기반 리포트 렌더링
2. `https://cr-check.vercel.app/report/nonexistent` → 404 에러 메시지
3. 카카오톡 또는 X에 공유 URL 붙여넣기 → 텍스트 미리보기 표시 (og-image 미준비, 텍스트만)

**감리자 확인:**
- [ ] 공유 URL 리포트 렌더링 정상
- [ ] 404 처리 정상
- [ ] OG 메타 미리보기 표시 (텍스트)

### E-5e: TN 기사 + DB 확인

**작업자:** 기획자 (프런트엔드 + Supabase)
**절차:**
1. **양질의 기사(TN)** URL 분석 → "문제적 보도관행 미발견" 결과
2. Supabase Table Editor에서 `articles` + `analysis_results` 테이블 확인 → 분석한 기사 수만큼 레코드

**감리자 확인:**
- [ ] TN 기사 정상 처리
- [ ] DB 레코드 정상 적재

**승인 게이트:** E-5a~E-5e 전체 통과 → **Phase E 완료**

---

## 부록 A: 롤백 계획

| 대상 | 방법 |
|------|------|
| **Railway** | Dashboard > 이전 배포 선택 > Redeploy, 또는 `git revert` 후 push |
| **Vercel** | Dashboard > Instant Rollback (즉시 복원) |
| **Supabase** | 데이터 0건이므로 아래 Down SQL로 복원 가능 |

**Phase D 마이그레이션 롤백 SQL (데이터 0건 전제):**
```sql
ALTER TABLE analysis_results DROP COLUMN IF EXISTS share_id;
ALTER TABLE analysis_results DROP COLUMN IF EXISTS article_analysis;
ALTER TABLE analysis_results DROP COLUMN IF EXISTS overall_assessment;
ALTER TABLE analysis_results DROP COLUMN IF EXISTS meta_patterns;
ALTER TABLE analysis_results RENAME COLUMN detected_patterns TO detected_categories;
ALTER TABLE analysis_results ALTER COLUMN phase1_model SET DEFAULT 'claude-haiku-3';
DROP INDEX IF EXISTS idx_analysis_share_id;
```

**매핑 정비 롤백:** `pattern_ethics_relations` DELETE 7건은 시드 데이터 SQL 재실행으로 복원.

---

## 부록 B: 위험 요소 요약

| 위험도 | 항목 | 대응 |
|--------|------|------|
| 🔴 높음 | `requirements.txt` 누락 (httpx, openai) | E-1a에서 해결 |
| 🔴 높음 | `weasyprint` Railway 빌드 실패 | E-1a에서 제거 |
| 🔴 높음 | DB 마이그레이션 전 코드 배포 | **E-2 → E-4 순서 엄수** |
| 🔴 높음 | `db.py` 5초 지연 | E-1b에서 해결 |
| 🟡 중간 | Vercel 프리뷰 CORS 미등록 | Phase G에서 `allow_origin_regex` 추가 |
| 🟡 중간 | GitHub PAT 만료 (2026-05-05) | 배포 후 1개월 내 갱신 |
| 🟡 중간 | 임베딩 PostgreSQL 접속 실패 | 포트 6543 → 5432 대체 시도 |
| ⚪ 낮음 | RLS 전테이블 DISABLED | Phase G에서 활성화 |
| ⚪ 낮음 | `share_id` UNIQUE 인덱스 중복 | Phase G에서 정리 |
| ⚪ 낮음 | `export.py` weasyprint import 잔존 | main.py에서 주석 처리, 런타임 영향 없음 |

---

## 부록 C: 주요 파일 경로

```
프로젝트 루트/
├── scripts/
│   └── generate_embeddings.py         ← 루트 scripts/ (backend/ 아님)
├── backend/
│   ├── requirements.txt               ← E-1a 수정 대상
│   ├── main.py                        ← CORS, /analyze, /report/{share_id}
│   ├── export.py                      ← weasyprint import 잔존 (런타임 영향 없음)
│   └── core/
│       ├── db.py                      ← E-1b 수정 대상
│       ├── storage.py                 ← 캐시 + 저장 + URL 정규화
│       ├── pattern_matcher.py         ← httpx + openai 사용
│       ├── report_generator.py        ← httpx 사용
│       └── meta_pattern_inference.py  ← httpx 사용
├── frontend/
│   ├── lib/config.ts                  ← NEXT_PUBLIC_API_URL
│   └── app/report/[id]/
│       ├── layout.tsx                 ← generateMetadata (서버 컴포넌트)
│       └── page.tsx                   ← "use client" 공유 URL 페이지
└── supabase/migrations/
    ├── 20260405...cleanup_pattern_ethics_relations.sql  ← E-2a
    └── 20260406...phase_d_analysis_results.sql          ← E-2b
```

---

## 실행 흐름 요약

```
사전 준비 (기획자: 대시보드 키 확보)
  │
  ▼
E-1a  CLI: requirements.txt 수정        ──→ 감리 확인 ──→
E-1b  CLI: db.py 수정                   ──→ 감리 확인 ──→
E-1c  CLI: CORS 확인 (읽기만)           ──→ 감리 확인 ──→
E-1d  CLI: git commit (push 안 함)      ──→ 감리 확인 ──→
  │
  ▼
E-2a  기획자: SQL 마이그레이션 ①         ──→ 감리 확인 ──→
E-2b  기획자: SQL 마이그레이션 ②         ──→ 감리 확인 ──→
E-2c  CLI: 임베딩 생성                   ──→ 감리 확인 ──→
E-2d  기획자: 검증 쿼리 5개              ──→ 감리 확인 ──→
  │
  ▼
E-3a  기획자: Railway 환경변수 4개       ──→ 감리 확인 ──→
E-3b  기획자: Vercel 환경변수 2개        ──→ 감리 확인 ──→
  │
  ▼  ⚠️ E-2 + E-3 미완료 시 진입 금지
E-4a  CLI: git push                     ──→ 감리 확인 ──→
E-4b  기획자: PR 생성 + 병합             ──→ 감리 PR 리뷰 ──→
E-4c  기획자: 빌드 로그 확인             ──→ 감리 확인 ──→
  │
  ▼
E-5a  기획자: 헬스체크 + UI              ──→ 감리 확인 ──→
E-5b  기획자: TP 기사 분석               ──→ 감리 확인 ──→
E-5c  기획자: 캐시 + URL 정규화          ──→ 감리 확인 ──→
E-5d  기획자: 공유 URL + 404 + OG        ──→ 감리 확인 ──→
E-5e  기획자: TN 기사 + DB 확인          ──→ 감리 확인 ──→
  │
  ▼
Phase E 완료 ✅
```

---

*이 문서는 로컬 코드베이스(`feature/m6-wip`)와 전수 대조 검증 + 4인 외부 감리를 거쳐 확정되었다.*
*다음 작업: 사전 준비 완료 후, 감리자에게 "사전 준비 완료"를 알리고 E-1a 프롬프트를 받는다.*
