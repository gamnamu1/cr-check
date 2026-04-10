# 세션 컨텍스트 — 2026-04-08 v25

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A~E 완료**, **Phase γ(미세 조정) 완료**,
**Phase E(클라우드 배포) 완료**, **Phase 2 Bugfix 완료**.
파이프라인이 프로덕션 환경(Railway + Vercel + Supabase)에서 정상 작동 중이며,
TP/TN 기사 모두 3종 리포트 정상 생성, share_id 기반 공유 URL 작동 확인.
다음은 **Phase F(Reserved Test Set 검증)**이다.

### v24→v25 변경 사항 (2026-04-08)

**Phase 2 Bugfix — 프로덕션 TP 분석 실패 3건 해결:**

Phase E 배포 후 TP 기사 분석 7건 중 4건이 실패. 앙상블 진단(Claude + 마누스 +
제미나이 + 퍼플렉시티) 교차검증으로 3개 독립 버그를 확정하고 수정했다.

1. **`_robust_json_parse` 4단계 폴백 (report_generator.py):**
   - 기존: 마크다운 제거 + `{ }` 바운더리 + `json.loads` 단순 구조
   - 변경: 4단계 폴백 (직접 파싱 → 바운더리 추출 → 후행 쉼표/줄바꿈 정규화 → 정규식 개별 추출)
   - `_fix_unescaped_newlines_in_strings`: state machine 방식 헬퍼 (3차용)
   - `_unescape_json_string`: RFC 8259 JSON 이스케이프 해제 함수 (4차용)
   - 4차 추출을 정규식 매칭에서 **키 위치 기반 슬라이싱**으로 교체 (텍스트 조기 절단 방지)
   - Fixes: id=2 JSONDecodeError, id=10/12 리터럴 `\n` + 텍스트 잘림

2. **529 OverloadedError 백오프 강화 (report_generator.py):**
   - `max_retries` 3→5
   - except 블록 3갈래 분기: `anthropic.APIStatusError` / `JSONDecodeError|ValueError` / `Exception`
   - 529: 긴 백오프 (10/20/40/60/60초) + `logger.warning`
   - 429: 즉시 실패 + `logger.error` (재시도 무의미)
   - `import anthropic` 추가
   - Fixes: id=4,5,7 OverloadedError 3/3 실패

3. **`inference_role` 컬럼 마이그레이션 (meta_pattern_inference.py 대응):**
   - 프로덕션 DB에 `inference_role TEXT CHECK ('required','supporting')` 컬럼 추가
   - `20260408000000_add_inference_role.sql` 마이그레이션 파일 생성
   - 400 Bad Request → 정상 조회 (단, inferred_by 데이터 0건이므로 "0건 → 건너뜀")
   - Fixes: 전체 TP 분석 시 반복되던 메타 패턴 DB 400 에러


**프로덕션 재검증 (Bugfix 후):**
- 이전 실패 기사(id=2,4,5,7) 삭제 후 재분석: 5건 전량 리포트 정상 생성
- 4차 폴백 발동 케이스(id=10,12): 줄바꿈 정상 렌더링, 텍스트 잘림 없음 확인
- 메타 패턴 400 에러 해소 확인

**docs 디렉토리 + 루트 정리:**
- 완료 문서 13건 → `_archive_superseded/` 이동 (phase_alpha/beta/gamma 프롬프트, M6 STEP 설계 등)
- 참조 문서 4건 → `_reference/` 이동 (M5 벤치마크, 메타패턴 설계, 진단 프롬프트, Test/)
- 루트 구버전 문서 4건 → `_archive_superseded/` 이동 (DEPLOYMENT_GUIDE, IMPLEMENTATION_GUIDE, QUICKSTART, USER_FLOW)
- `README.md` 현행화: Hybrid RAG 아키텍처, Sonnet 4.5+4.6, 프로덕션 URL 반영
- `CLAUDE.md` 현행화: 프로덕션 상태, 모델명, URL, Phase 2 Bugfix, Gotchas 갱신

**Git 이력:**
- PR #30: `fix/phase2-reliability` → `main` (bugfix 3건)
- PR #31: 4차 폴백 개선 (unescape + 슬라이싱)
- PR #32: docs/루트 정리 + README/CLAUDE.md 현행화
- 병합 완료 브랜치: `fix/phase2-reliability`, `feature/m6-wip` (삭제 가능)

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
- [x] Phase E: 클라우드 배포 ✅
- [x] **Phase 2 Bugfix: 프로덕션 안정성 개선 ✅** ← v25 완료
- [ ] **Phase F: Reserved Test Set 검증** ← 다음 세션 첫 작업
- [ ] Phase G: 마무리


---

## 파이프라인 최종 흐름 (Phase 2 Bugfix 후, 프로덕션 가동 중)

```
POST /analyze { url }
  ① URL 정규화 (utm_*, fbclid 등 제거)
  ② DB 캐시 조회 → 있으면 즉시 반환 (is_cached: true, 0원, ~150ms)
  ③ 캐시 미스 → 기사 스크래핑 → 청킹 → 벡터검색(OpenAI 임베딩, ★ 힌트)
  → ❶ Sonnet 4.5 Solo(패턴 식별 + Devil's Advocate CoT)
  → check_meta_patterns(탐지된 패턴, DB inferred_by 동적 조회)
  → 규범 조회(get_ethics_for_patterns RPC + REST API fallback)
  → ❷ Sonnet 4.6(3종 리포트: 〔〕마커 자연 인용, cite 태그 미사용)
     ├─ _robust_json_parse: 4단계 폴백 (직접→바운더리→정규화→슬라이싱 추출)
     └─ 재시도: 5회, 529=긴백오프(10-60초), 429=즉시실패
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
- 공유 URL 예시: `https://cr-check.vercel.app/report/FnS7GRd01KB4`

---

## 다음 세션 작업

### 작업 1: Stash 복원 + 문서 정리

로컬에 `stash@{0}` (feature/m6-wip에서 보관한 docs + diagnostics WIP)이 남아있다.
main 브랜치에서 `git stash pop`으로 복원한 뒤, 새로 나타나는 파일들을 분류:


- `SESSION_CONTEXT_2026-04-07_v24.md` → `_archive_superseded/` (v25로 대체됨)
- `Phase_E_Final_Execution_Plan.md` → `_reference/` (Phase E 완료, 참조 가치)
- `PHASE2_BUGFIX_PLAN_2026-04-08.md` → `_reference/` (Bugfix 완료, 진단 과정 기록)
- `CR-Check_Pipeline_v22.md` → 상태 확인 후 분류
- `오류 진단 및 해법_마누스/제미나이/퍼플렉시티.md` → `_reference/` (앙상블 진단 기록)
- `backend/diagnostics/*.json` 4건 → 기존 diagnostics 디렉토리에 유지

### 작업 2: Phase F — Reserved Test Set 검증

Reserved Test Set 73건으로 프로덕션 파이프라인 성능 검증.
프로덕션 환경에서 실행. API 비용 예산 사전 확인 권장.

### 작업 3: 프런트엔드 미세 개선 (선택)

- 소셜 공유 버튼(Facebook, X, 카카오톡)에 `/report/{share_id}` 링크 자동 삽입
- "링크 복사" 버튼 추가
- OG 이미지(`og-image.png`) 제작 및 적용

### 작업 4: Phase G 마무리 항목

- RLS 정책 활성화 (articles, analysis_results 등)
- `share_id` UNIQUE 인덱스 중복 정리
- `export.py` weasyprint import 정리 (try-except 또는 제거)
- Vercel 프리뷰 URL CORS `allow_origin_regex` 추가 (선택)
- GitHub PAT 갱신 (만료일: 2026-05-05)
- 메타 패턴 `inferred_by` 데이터 시딩 (현재 0건, 기능 비활성 상태)

---

## 주요 파일 경로 (★ v25 갱신)

### 백엔드 (backend/core/)
```
backend/core/
├── db.py                     ← 3단 분기 클라우드 전환 로직
├── storage.py                ← 캐시 조회 + 결과 저장 + URL 정규화
├── pattern_matcher.py        ← Phase 1: Sonnet 4.5 Solo (657줄)
├── report_generator.py       ← ★ v25: 4단계 폴백 + 529 백오프 + 예외 3분기
├── meta_pattern_inference.py ← ★ v25: inference_role 컬럼 쿼리 (DB에 컬럼 추가됨)
├── pipeline.py               ← 파이프라인 오케스트레이터
├── citation_resolver.py      ← 비활성화 (코드 보존)
└── chunker.py / criteria_manager.py / prompt_builder.py
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
└── lib/config.ts             ← NEXT_PUBLIC_API_URL 환경변수
```

### 프로덕션 환경변수
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

### 문서 (docs/) — ★ v25 정리 후
```
docs/
├── SESSION_CONTEXT_2026-04-08_v25.md      ← ★ 이 문서
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         ← 마스터 플랜 SSoT
├── current-criteria_v2_active.md          ← 패턴 원문
├── Code of Ethics for the Press.md        ← 규범 원문
├── ethics_codes_mapping.json              ← 규범 매핑 (394개)
├── golden_dataset_final.json              ← 골든 데이터셋 (26건)
├── golden_dataset_labels.json             ← 레이블링 (v3)
├── NEXT_SESSION_PROMPT.md                 ← 다음 세션 프롬프트
├── _reference/                            ← 참조 문서 (벤치마크, 설계, 진단)
└── _archive_superseded/                   ← 대체된 문서 보관
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **Phase E 완료 + Phase 2 Bugfix 완료. 프로덕션 안정 가동 중.**
2. **main 브랜치가 프로덕션.** push 시 자동 배포 트리거. 반드시 PR 경유.
3. **Phase 1 모델은 Sonnet 4.5, Phase 2는 Sonnet 4.6.** 이 분리 구조 유지.
4. **인용 형식은 〔〕 마커 방식.** cite 태그 폐기됨.
5. **`_robust_json_parse` 4단계 폴백 적용됨.** 3차는 `_fix_unescaped_newlines_in_strings`, 4차는 키 위치 기반 슬라이싱 + `_unescape_json_string`.
6. **재시도 로직 3갈래 분기.** 529=긴백오프(10-60초, 5회), 429=즉시실패, 기타=짧은백오프.
7. **`inference_role` 컬럼 프로덕션 추가됨.** 단, `inferred_by` 데이터 0건이므로 메타패턴 추론은 "0건 → 건너뜀" 상태.
8. **규범 매핑 63건, 임베딩 401건.** 프로덕션 반영 완료.
9. **Stash `stash@{0}` 복원 필요.** docs + diagnostics WIP 파일 보관 중.
10. **v24까지의 모든 교훈(1~27) + v25 추가 교훈 유효.**
11. **CLI 자율 진행 제한.** STEP 단위 승인 게이트 엄격 적용.


### 주의사항 (v24 계승 + v25 추가)

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
- **`export.py`에 `from weasyprint import HTML, CSS` 잔존** — 런타임 영향 없음. Phase G에서 정리
- **RLS 전테이블 DISABLED** — Phase G에서 활성화 권장
- **Supabase 비밀번호에 특수문자** — connection string 사용 시 URL escape 필요 (`#`→`%23`)
- **Railway 환경변수는 escape 불필요** — 환경변수 값은 그대로 저장됨
- **`import anthropic` 추가됨** — OverloadedError/RateLimitError 예외 분기에 필요 ★ NEW
- **`_unescape_json_string` + `_fix_unescaped_newlines_in_strings`** — 두 함수는 역방향 변환. 혼동 주의. 전자는 4차 폴백용(JSON→실제문자), 후자는 3차 정규화용(실제문자→JSON이스케이프) ★ NEW
- **4차 폴백 발동 시 logger.warning 기록됨** — Railway 로그에서 "4차 정규식 추출 사용" 검색 가능 ★ NEW
- **inferred_by 데이터 0건** — inference_role 컬럼은 추가됨, 데이터 시딩은 Phase G 이후 ★ NEW
- **앙상블 진단 문서 3건 보존 중** — `_reference/오류 진단 및 해법_*.md` (stash 복원 후) ★ NEW

---

*이 세션 컨텍스트는 2026-04-08 밤에 v24→v25로 갱신되었다.*
*Phase 2 Bugfix 완료: _robust_json_parse 4단계 폴백, 529 백오프 강화, inference_role 마이그레이션.*
*docs/루트 정리: 구버전 문서 아카이빙, README.md/CLAUDE.md 현행화.*
*PR #30~#32 병합, Railway + Vercel 자동 배포 정상.*
*다음 작업: Stash 복원 → Phase F(Reserved Test Set 검증) → Phase G(마무리).*
