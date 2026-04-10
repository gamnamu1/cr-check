# 세션 컨텍스트 — 2026-04-06 v23

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A+B+C 완료**, **STEP 87 완료**, **Phase γ(미세 조정) 완료**,
**Phase D(아카이빙 통합 + 링크 공유) 완료**.
파이프라인 전체가 정상 작동하며, 분석 결과가 DB에 저장되고 공유 URL로 접근 가능하다.
다음은 **Phase E(클라우드 배포)**이다.

### v22→v23 변경 사항 (2026-04-06 저녁)

**Supabase heartbeat 설정 (STEP 0):**
- `.github/workflows/supabase-heartbeat.yml` 생성: 주 2회(월·목 UTC 00:00) 크론잡
- GitHub Secrets에 `SUPABASE_URL` + `SUPABASE_KEY`(anon) 등록
- `main` 브랜치에 cherry-pick하여 Actions 정상 작동 확인 (3초 내 성공)

**Phase D — 아카이빙 + 링크 공유 통합 완료 (D-1~D-8):**

1. **스키마 마이그레이션 (D-1):** `analysis_results` 테이블에 `share_id TEXT UNIQUE NOT NULL`, `article_analysis JSONB`, `overall_assessment TEXT`, `meta_patterns JSONB` 추가. `phase1_model` 기본값 Sonnet 4.5로 변경. `detected_categories` → `detected_patterns` 리네임. 마이그레이션 파일 `20260406000000_phase_d_analysis_results.sql` 생성.

2. **백엔드 storage.py 신규 (D-2):** 캐시 우선(Cache-First) 아키텍처 구현.
   - `normalize_url()`: utm_*, fbclid, gclid, mc_*, ref, source 트래킹 파라미터 + fragment 제거
   - `get_cached_analysis(url)`: URL 정규화 → articles 조회 → analysis_results 최신 1건 → 병합 응답
   - `save_analysis_result(...)`: articles UPSERT(`on_conflict=url`) → share_id 생성(충돌 시 3회 재시도) → analysis_results INSERT
   - `get_analysis_by_share_id(share_id)`: PostgREST 외래키 자동 JOIN(`select=*,articles(*)`)
   - 모든 DB 호출에 `httpx.HTTPStatusError` + 일반 `Exception` 분리 예외 처리, 실패 시 None 반환 (graceful degradation)

3. **main.py 수정 (D-2, D-3):**
   - `AnalyzeResponse` 모델: `Dict[str, str]` → `Dict[str, Any]`, `share_id`, `analyzed_at`, `is_cached` 필드 추가
   - `/analyze` 엔드포인트: ① 캐시 조회 → ② 미스 시 파이프라인 → ③ DB 저장 → ④ 응답
   - `GET /report/{share_id}` 엔드포인트 추가: 404 처리 + `Cache-Control: public, max-age=86400`

4. **프론트엔드 (D-4, D-5):**
   - `frontend/app/report/[id]/page.tsx` 신규: DB 기반 공유 URL 페이지 (sessionStorage 의존 없음). 4가지 상태 분기 (loading/404/error/success).
   - `frontend/app/report/[id]/layout.tsx` 신규: `generateMetadata()` 서버 컴포넌트로 OG/Twitter 메타 태그 생성. `page.tsx`("use client")와 분리.
   - `frontend/components/CachedBanner.tsx` 신규: "이 기사는 {날짜}에 분석된 결과입니다." 안내 배너. 한국어 날짜 포맷. `/report/[id]`와 `/result` 양쪽에서 공유.
   - `frontend/app/result/page.tsx` 수정: `is_cached === true`일 때 CachedBanner 조건부 렌더링.
   - `frontend/types/index.ts`: `share_id`, `analyzed_at`, `is_cached` optional 필드 추가.

5. **deprecated 코드 정리 (D-6):**
   - `pattern_matcher.py`: 1441줄 → 657줄 (레거시 함수 분리)
   - `pattern_matcher_legacy.py` 신규 (838줄): 2-Call(Haiku→Sonnet), 1-Call(게이트+Haiku) 코드 격리
   - `report_generator_legacy.py` 신규 (32줄): cite 태그 후치환 방식 프롬프트 격리
   - `pipeline.py`: 레거시 import 주석 처리 + `_DEPRECATED_` 마커 추가
   - 의존성 방향: legacy → active 공통 유틸 import (역방향 없음, 안전)

6. **통합 테스트 (D-7):** 7개 시나리오 전부 통과.
   - 시나리오 1: 최초 분석 → DB 저장 → share_id 발급 (TP 기사 212초)
   - 시나리오 2: 동일 URL 캐시 히트 → 277ms, is_cached=true, Sonnet 호출 0원
   - 시나리오 3: URL 정규화 캐시 히트 → 143ms (utm/fbclid 무시)
   - 시나리오 4: TN 기사 → DB 저장 + share_id 발급 + 캐시 히트 정상
   - 시나리오 5: 미존재 share_id → HTTP 404
   - 시나리오 6: DB 실패 graceful degradation → 3개 함수 모두 None 반환 + ConnectError 로깅
   - 시나리오 7: 프론트엔드 → CachedBanner, OG 메타, ResultViewer 정상 렌더링

7. **WIP push (D-8):** 13개 파일 커밋 (`be87c54`), docs 제외.

**D-7 중 발견된 이슈:**
- ✅ [수정 완료] `_upsert_article`의 한국 뉴스 publish_date 형식 거부 → `_normalize_publish_date()` 헬퍼 추가
- ⚠️ [미수정] `report_generator._robust_json_parse`가 Sonnet 비정형 JSON 복구 실패 → 3회 재시도 후 에러 리포트 저장. `_parse_solo_response`에는 fallback이 있지만 `_robust_json_parse`에는 없음. 향후 별도 작업으로 3단계 fallback 추가 권장.

---

## M6 진행 현황 체크리스트

- [x] Phase A: 로컬 E2E 연결 ✅
- [x] Phase B: 코드베이스 위생 ✅
- [x] Phase C: 메타 패턴 추론 ✅
- [x] Phase C WIP 커밋 ✅
- [x] ★ STEP 86: 종합 E2E 품질 체감 ✅
- [x] ★ STEP 87: 리포트 품질 개선 ✅
- [x] Phase γ: 미세 조정 ✅
- [x] Supabase heartbeat 설정 ✅ ← v23 완료
- [x] **Phase D: 아카이빙 + 링크 공유 통합 ✅** ← v23 완료
- [x] WIP 브랜치 push ✅
- [ ] **Phase E: 클라우드 배포** ← 다음 세션 첫 작업
- [ ] Phase F: Reserved Test Set 검증
- [ ] Phase G: 마무리

---

## 파이프라인 최종 흐름 (Phase D 완료 후) ★ v23 갱신

```
POST /analyze { url }
  ① URL 정규화 (utm_*, fbclid 등 제거)
  ② DB 캐시 조회 → 있으면 즉시 반환 (is_cached: true, 0원, ~150ms)
  ③ 캐시 미스 → 기사 스크래핑 → 청킹 → 벡터검색(OpenAI 임베딩, ★ 힌트)
  → ❶ Sonnet 4.5 Solo(패턴 식별 + Devil's Advocate CoT)
  → check_meta_patterns(탐지된 패턴, DB inferred_by 동적 조회)
  → 규범 조회(get_ethics_for_patterns RPC + REST API fallback)
  → ❷ Sonnet 4.6(3종 리포트: 〔〕마커 자연 인용, cite 태그 미사용)
  ④ DB 저장 (articles UPSERT + analysis_results INSERT + share_id 발급)
  ⑤ 응답 반환 (share_id 포함, 실패 시 share_id=None)

GET /report/{share_id}
  → PostgREST 외래키 JOIN (analysis_results + articles)
  → Cache-Control: public, max-age=86400
  → 404 시 "공유된 분석 결과를 찾을 수 없습니다."
```

**v22 대비 변경점:**
- 캐시 우선 아키텍처 추가 (①②⑤ 신규)
- URL 정규화 (트래킹 파라미터 제거)
- DB 저장 + share_id 발급 (④ 신규)
- `/report/{share_id}` 조회 엔드포인트 (신규)
- deprecated 코드 분리: `pattern_matcher.py` 1441→657줄

---

## 다음 세션 작업

### 작업 1: Phase E — 클라우드 배포

**프로덕션 DB 준비:**
1. `scripts/generate_embeddings.py` 실행 (프로덕션 DB에 401건 임베딩 생성)
2. 매핑 정비 마이그레이션 적용: `20260405000000_cleanup_pattern_ethics_relations.sql`
3. Phase D 마이그레이션 적용: `20260406000000_phase_d_analysis_results.sql`
4. RLS 정책 확인: `analysis_results`, `articles` 테이블에 anon SELECT 허용 (현재 RLS disabled 상태)

**환경변수 확인:**
- `pattern_matcher.py`의 `SONNET_MODEL`이 `claude-sonnet-4-5-20250929`인지 확인
- Vercel 환경변수: `NEXT_PUBLIC_API_URL` (Railway 백엔드 URL), `NEXT_PUBLIC_SITE_URL`
- Railway 환경변수: `SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` 등

**배포:**
- Railway(BE): FastAPI 백엔드 + storage.py 포함
- Vercel(FE): Next.js 프론트엔드 + `/report/[id]` 동적 라우팅

### 작업 2: Phase F — Reserved Test Set 검증

Reserved Test Set 73건으로 파이프라인 성능 검증. Phase E 완료 후 진행.

### 작업 3 (미수정 이슈): `_robust_json_parse` 개선

`report_generator.py`의 `_robust_json_parse`에 `_parse_solo_response`와 동일한 3단계 fallback 추가.
현재는 Sonnet 비정형 JSON 시 3회 재시도 후 에러 리포트 저장. 긴급하지 않으나 품질 개선 효과 있음.

---

## 주요 파일 경로 (★ v23 갱신)

### 백엔드 (backend/core/) — ★ v23 갱신
```
backend/core/
├── storage.py               ← ★ NEW: 캐시 조회 + 결과 저장 + URL 정규화
├── pattern_matcher.py        ← ★ 657줄로 경량화 (레거시 분리)
├── pattern_matcher_legacy.py ← ★ NEW: 2-Call/1-Call 레거시 (838줄, 비교용)
├── report_generator.py       ← Phase 2 모델: claude-sonnet-4-6 + 〔〕마커
├── report_generator_legacy.py← ★ NEW: cite 태그 프롬프트 (32줄, 비교용)
├── pipeline.py               ← 파이프라인 (레거시 import 주석 처리)
├── meta_pattern_inference.py
├── citation_resolver.py      ← 비활성화 (코드 보존)
├── db.py / chunker.py / analyzer.py(참조용)
└── criteria_manager.py / prompt_builder.py
```

### 프런트엔드 — ★ v23 갱신
```
frontend/
├── app/
│   ├── report/[id]/
│   │   ├── page.tsx          ← ★ NEW: 공유 URL 페이지 ("use client")
│   │   └── layout.tsx        ← ★ NEW: generateMetadata() OG/Twitter
│   └── result/page.tsx       ← ★ 캐시 배너 조건부 렌더링 추가
├── components/
│   ├── ResultViewer.tsx      ← 〔〕마커 + H3 고딕 (Phase γ)
│   └── CachedBanner.tsx      ← ★ NEW: 캐시 안내 배너 (공용)
├── types/index.ts            ← ★ share_id, analyzed_at, is_cached 추가
└── lib/config.ts             ← API base URL 설정
```

### 마이그레이션 파일
```
supabase/migrations/
├── 20260328000000_create_cr_check_schema.sql
├── 20260328100000_seed_data.sql
├── 20260329000000_data_implant_pattern_desc.sql
├── 20260401000000_meta_pattern_inference.sql
├── 20260405000000_cleanup_pattern_ethics_relations.sql
└── 20260406000000_phase_d_analysis_results.sql  ← ★ NEW
```

### GitHub Actions — ★ v23 신규
```
.github/workflows/
└── supabase-heartbeat.yml    ← ★ NEW: 주 2회 크론잡 (main 브랜치)
```

### 문서 (docs/) — ★ v23 갱신
```
docs/
├── SESSION_CONTEXT_2026-04-06_v23.md      ← ★ 이 문서
├── Phase_D_Final_Execution_Plan.md        ← Phase D 최종 실행 계획 (4인 감리 반영)
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         ← Phase E~G 계획
├── SESSION_CONTEXT_2026-04-05_v22.md      ← 이전 버전
└── (기타 기존 문서 유지)
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **Phase D 완료.** 분석 결과 DB 저장, 캐시 우선 정책, 공유 URL(`/report/{share_id}`) 모두 구현됨.
2. **캐시 우선 정책.** 동일 URL 재분석 시 DB에서 즉시 반환 (is_cached: true, ~150ms, 0원). URL 정규화 적용 (utm 등 트래킹 파라미터 제거).
3. **share_id 생성:** `secrets.token_urlsafe(9)` → 12자, 충돌 시 3회 재시도.
4. **Phase 1 모델은 Sonnet 4.5 (`claude-sonnet-4-5-20250929`).** Phase 2는 Sonnet 4.6 (`claude-sonnet-4-6`). 이 분리 구조를 유지할 것.
5. **인용 형식은 〔〕 마커 방식.** cite 태그 폐기됨. 내부 코드(JEC-7 등) 사용 금지.
6. **규범 매핑은 63건.** 기존 70건에서 7건 삭제, 2건 하향.
7. **벡터 검색 정상 작동.** 임베딩 401건. 프로덕션 배포 시 재실행 필요.
8. **deprecated 코드 분리 완료.** `pattern_matcher_legacy.py` (838줄), `report_generator_legacy.py` (32줄). 활성 파이프라인에서 import하지 않음.
9. **Supabase heartbeat 작동 중.** 주 2회(월·목) 크론잡, `main` 브랜치에 배치.
10. **v22까지의 모든 교훈(1~27) 유효.**
11. **CLI 자율 진행 제한.** 플레이북 STEP 단위 승인 게이트 엄격 적용.

### 주의사항 (v22에서 계승 + v23 추가)

- **KJA 접두어 절대 금지**
- **Supabase Legacy JWT 키 사용 중**
- **GitHub PAT 만료일: 2026-05-05** (약 1개월 남음, 갱신 필요)
- **Reserved Test Set 73건은 참조 금지** (Phase F 전까지)
- **벤치마크 결과 파일 삭제 금지**
- **deprecated 코드 삭제 금지** (분리/격리만 — pattern_matcher_legacy.py, report_generator_legacy.py)
- **프로덕션 배포 시 `scripts/generate_embeddings.py` 실행 필수** (Phase E)
- **프로덕션 배포 시 마이그레이션 2건 적용 필수** (Phase E): `20260405000000_cleanup_...` + `20260406000000_phase_d_...` ★ v23 갱신
- **`ResultViewer.tsx`의 규범명 opacity: 0.9 설정은 Gamnamu 개인 취향**
- **프론트엔드 App Router 사용 중** — Pages Router 관련 코드 생성 금지 ★ NEW
- **`generateMetadata()`는 layout.tsx(서버 컴포넌트)에 배치** — page.tsx("use client")와 분리 ★ NEW
- **Vercel 배포 시 환경변수 필요:** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL` ★ NEW
- **`og-image.png` 미준비** — 텍스트 미리보기만 표시됨, 이미지 추가는 선택사항 ★ NEW
- **UNIQUE 인덱스 중복:** `analysis_results.share_id`에 UNIQUE 제약 + 명시적 인덱스 공존 (기능 무관, 정리 가능) ★ NEW
- **`_robust_json_parse` 미수정 이슈:** 비정형 JSON 복구 실패 시 에러 리포트 저장됨. 향후 3단계 fallback 추가 권장 ★ NEW

---

*이 세션 컨텍스트는 2026-04-06 저녁에 v22→v23으로 갱신되었다.*
*Phase D(아카이빙 + 링크 공유 통합) 완료: storage.py, /report/{share_id}, 캐시 우선 정책, deprecated 코드 분리.*
*Supabase heartbeat 설정 완료.*
*D-7 통합 테스트 7개 시나리오 전부 통과.*
*다음 작업: Phase E(클라우드 배포) → Phase F(Reserved Test Set 검증) → Phase G(마무리).*
