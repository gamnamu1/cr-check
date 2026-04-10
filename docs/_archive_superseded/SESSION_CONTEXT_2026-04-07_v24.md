# 세션 컨텍스트 — 2026-04-07 v24

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A~D 완료**, **Phase γ(미세 조정) 완료**,
**Phase E(클라우드 배포) 완료**.
파이프라인이 프로덕션 환경(Railway + Vercel + Supabase)에서 정상 작동 중이며,
분석 결과가 DB에 저장되고 공유 URL로 접근 가능하다.
다음은 **Phase F(Reserved Test Set 검증)**이다.

### v23→v24 변경 사항 (2026-04-07 저녁)

**Phase E — 클라우드 배포 완료 (E-1~E-5):**

1. **코드 수정 (E-1):**
   - `backend/requirements.txt`: `httpx`, `openai` 추가, `weasyprint` 제거. 커밋 `926c5e7`.
   - `backend/core/db.py`: `_get_supabase_config()` 3단 분기 구조로 재설계.
     분기 1: `SUPABASE_LOCAL` → 로컬 강제.
     분기 2: 클라우드 URL 감지 → 로컬 체크 생략 (5초 지연 제거). `SUPABASE_SERVICE_ROLE_KEY` 누락 시 `ValueError`.
     분기 3: URL 미설정 → 기존 로컬 시도 후 클라우드 폴백.

2. **프로덕션 DB 마이그레이션 (E-2):**
   - `20260405000000_cleanup_pattern_ethics_relations.sql` 적용 → 매핑 70→63건.
   - `20260406000000_phase_d_analysis_results.sql` 적용 → share_id, article_analysis, overall_assessment, meta_patterns 컬럼 추가, detected_categories→detected_patterns RENAME.
   - `scripts/generate_embeddings.py` 실행 → 프로덕션 DB에 임베딩 401건(patterns 28 + ethics_codes 373) 적재 완료.
   - Session Pooler 방식(`aws-1-ap-northeast-2.pooler.supabase.com:5432`)으로 연결. Direct Connection은 IPv6 전용이라 IPv4 환경에서 사용 불가.
   - ⚠️ 비밀번호에 `#`, `/` 포함 시 URL escape 필요 (`#`→`%23`, `/`→`%2F`).

3. **환경변수 설정 (E-3):**
   - Railway: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY` 3개 추가 (기존 `ANTHROPIC_API_KEY` 유지, 총 4개).
   - Vercel: `NEXT_PUBLIC_SITE_URL` 1개 추가 (기존 `NEXT_PUBLIC_API_URL` 유지, 총 2개).

4. **PR 병합 + 자동 배포 (E-4):**
   - PR #29: `feature/m6-wip` → `main`, 9 commits, 142 files changed.
   - Railway + Vercel 자동 배포 트리거, 양쪽 모두 빌드 성공.

5. **배포 후 검증 (E-5):**
   - 헬스체크: `{"status":"healthy","api_key_configured":true}` ✅
   - TP 기사: 경기도지사 경선 토론회 기사 → 3종 리포트 정상 생성, share_id `IPVNdIeWVJ8z` 발급, 115초 소요. ✅
   - 캐시 히트: 동일 URL 재분석 → 즉시 반환 ✅
   - 공유 URL: `cr-check.vercel.app/report/IPVNdIeWVJ8z` → DB 기반 리포트 렌더링 + CachedBanner 정상 ✅
   - TN 기사: 부산소방 소방관 미담 기사 → "문제적 보도관행이 발견되지 않았습니다", 26초 소요 ✅
   - DB 적재: articles 3건, analysis_results 3건 확인 ✅

**E-5 중 발견된 이슈:**
- ⚠️ [미수정] analysis_results id=2: 리포트 생성 중 오류 발생 (239초 소요 후 에러 리포트 저장). `_robust_json_parse` fallback 부재 이슈의 실제 발현으로 추정. v23에서 이미 인지된 미수정 이슈.

**Phase E 배포 계획서:**
- `docs/Phase_E_Final_Execution_Plan.md` — 역할별 액션 + 승인 게이트 구조의 플레이북. 4인 외부 감리(마누스·안티그래비티·제미나이·퍼플렉시티) 반영.

---

## M6 진행 현황 체크리스트

- [x] Phase A: 로컬 E2E 연결 ✅
- [x] Phase B: 코드베이스 위생 ✅
- [x] Phase C: 메타 패턴 추론 ✅
- [x] Phase C WIP 커밋 ✅
- [x] ★ STEP 86: 종합 E2E 품질 체감 ✅
- [x] ★ STEP 87: 리포트 품질 개선 ✅
- [x] Phase γ: 미세 조정 ✅
- [x] Supabase heartbeat 설정 ✅
- [x] Phase D: 아카이빙 + 링크 공유 통합 ✅
- [x] WIP 브랜치 push ✅
- [x] **Phase E: 클라우드 배포 ✅** ← v24 완료
- [ ] **Phase F: Reserved Test Set 검증** ← 다음 세션 첫 작업
- [ ] Phase G: 마무리

---

## 파이프라인 최종 흐름 (Phase E 완료 후, 프로덕션 가동 중)

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

**프로덕션 URL:**
- 백엔드: `https://cr-check-production.up.railway.app`
- 프런트엔드: `https://cr-check.vercel.app`
- 공유 URL 예시: `https://cr-check.vercel.app/report/IPVNdIeWVJ8z`

---

## 다음 세션 작업

### 작업 1: Phase F — Reserved Test Set 검증

Reserved Test Set 73건으로 프로덕션 파이프라인 성능 검증. 프로덕션 환경에서 실행.

### 작업 2: 프런트엔드 미세 개선 (선택)

- 소셜 공유 버튼(Facebook, X, 카카오톡)에 `/report/{share_id}` 링크 자동 삽입
- "링크 복사" 버튼 추가
- OG 이미지(`og-image.png`) 제작 및 적용

### 작업 3 (미수정 이슈): `_robust_json_parse` 개선

`report_generator.py`의 `_robust_json_parse`에 3단계 fallback 추가.
analysis_results id=2에서 실제 에러 발현 확인됨 (239초 소요 후 에러 리포트 저장).
긴급하지 않으나 프로덕션 안정성 개선에 필요.

### 작업 4: Phase G 마무리 항목

- RLS 정책 활성화 (articles, analysis_results 등)
- `share_id` UNIQUE 인덱스 중복 정리
- `export.py` weasyprint import 정리 (try-except 또는 제거)
- Vercel 프리뷰 URL CORS `allow_origin_regex` 추가 (선택)
- GitHub PAT 갱신 (만료일: 2026-05-05)

---

## 주요 파일 경로 (★ v24 갱신)

### 백엔드 (backend/core/)
```
backend/core/
├── db.py                     ← ★ v24: 3단 분기 클라우드 전환 로직
├── storage.py                ← 캐시 조회 + 결과 저장 + URL 정규화
├── pattern_matcher.py        ← Phase 1: Sonnet 4.5 Solo (657줄)
├── pattern_matcher_legacy.py ← 레거시 비교용 (838줄, 비활성)
├── report_generator.py       ← Phase 2: Sonnet 4.6 + 〔〕마커
├── report_generator_legacy.py← cite 태그 프롬프트 (32줄, 비활성)
├── pipeline.py               ← 파이프라인 오케스트레이터
├── meta_pattern_inference.py
├── citation_resolver.py      ← 비활성화 (코드 보존)
└── criteria_manager.py / prompt_builder.py
```

### 프런트엔드
```
frontend/
├── app/
│   ├── report/[id]/
│   │   ├── page.tsx          ← 공유 URL 페이지 ("use client")
│   │   └── layout.tsx        ← generateMetadata() OG/Twitter
│   └── result/page.tsx       ← 캐시 배너 조건부 렌더링
├── components/
│   ├── ResultViewer.tsx      ← 〔〕마커 + H3 고딕 (Phase γ)
│   └── CachedBanner.tsx      ← 캐시 안내 배너 (공용)
├── types/index.ts
└── lib/config.ts             ← NEXT_PUBLIC_API_URL 환경변수
```

### 프로덕션 환경변수 (★ v24 신규)
```
Railway (4개):
  ANTHROPIC_API_KEY    ← Sonnet 4.5 + 4.6
  OPENAI_API_KEY       ← 쿼리 임베딩 생성
  SUPABASE_URL         ← https://vwaelliqpoqzeoggrfew.supabase.co
  SUPABASE_SERVICE_ROLE_KEY ← service_role (anon 아님)

Vercel (2개):
  NEXT_PUBLIC_API_URL  ← https://cr-check-production.up.railway.app
  NEXT_PUBLIC_SITE_URL ← https://cr-check.vercel.app
```

### 문서 (docs/)
```
docs/
├── SESSION_CONTEXT_2026-04-07_v24.md      ← ★ 이 문서
├── Phase_E_Final_Execution_Plan.md        ← Phase E 플레이북 (역할별 액션 + 승인 게이트)
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         ← Phase F~G 계획
└── (기타 기존 문서 유지)
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **Phase E 완료. 프로덕션 가동 중.** Railway(백엔드) + Vercel(프런트엔드) + Supabase(DB) 삼각 구조.
2. **main 브랜치가 프로덕션.** PR #29로 `feature/m6-wip` → `main` 병합 완료. 이후 main 직접 push 시 자동 배포 트리거됨에 주의.
3. **캐시 우선 정책 가동 중.** 동일 URL 재분석 시 DB에서 즉시 반환.
4. **Phase 1 모델은 Sonnet 4.5, Phase 2는 Sonnet 4.6.** 이 분리 구조를 유지할 것.
5. **인용 형식은 〔〕 마커 방식.** cite 태그 폐기됨.
6. **규범 매핑은 63건.** 프로덕션 DB에 반영 완료.
7. **벡터 검색 정상 작동.** 프로덕션 임베딩 401건 적재 완료.
8. **deprecated 코드 분리 완료.** 활성 파이프라인에서 import하지 않음.
9. **Supabase heartbeat 작동 중.** 주 2회(월·목) 크론잡.
10. **v23까지의 모든 교훈(1~27) 유효.**
11. **CLI 자율 진행 제한.** 플레이북 STEP 단위 승인 게이트 엄격 적용.

### 주의사항 (v23에서 계승 + v24 추가)

- **KJA 접두어 절대 금지**
- **Supabase Legacy JWT 키 사용 중**
- **GitHub PAT 만료일: 2026-05-05** (약 1개월 남음)
- **Reserved Test Set 73건은 참조 금지** (Phase F 전까지)
- **벤치마크 결과 파일 삭제 금지**
- **deprecated 코드 삭제 금지** (분리/격리만)
- **`ResultViewer.tsx`의 규범명 opacity: 0.9 설정은 Gamnamu 개인 취향**
- **프런트엔드 App Router 사용 중** — Pages Router 코드 생성 금지
- **`generateMetadata()`는 layout.tsx(서버 컴포넌트)에 배치** — page.tsx("use client")와 분리
- **`og-image.png` 미준비** — 텍스트 미리보기만 표시됨
- **`export.py`에 `from weasyprint import HTML, CSS` 잔존** — main.py에서 주석 처리되어 런타임 영향 없음. Phase G에서 정리 ★ NEW
- **`_robust_json_parse` 미수정 이슈** — 프로덕션에서 실제 에러 발현 확인 (id=2). 3단계 fallback 추가 권장 ★ NEW
- **RLS 전테이블 DISABLED** — 현재 아키텍처에서는 당장 위험 없으나, Phase G에서 활성화 권장 ★ NEW
- **Supabase 비밀번호에 특수문자** — connection string 사용 시 URL escape 필요 (`#`→`%23`) ★ NEW
- **Railway 환경변수는 escape 불필요** — 환경변수 값은 그대로 저장됨 ★ NEW

---

*이 세션 컨텍스트는 2026-04-07 밤에 v23→v24로 갱신되었다.*
*Phase E(클라우드 배포) 완료: Railway + Vercel + Supabase 프로덕션 가동 중.*
*PR #29 병합, 자동 배포, E-5 검증 통과 (TP/TN/캐시/공유 URL 모두 정상).*
*다음 작업: Phase F(Reserved Test Set 검증) → 프런트엔드 미세 개선 → Phase G(마무리).*
