# 세션 컨텍스트 — 2026-04-05 v22

## 프로젝트 상태 요약

CR-Check의 Hybrid RAG 파이프라인 **M1~M5 완료**, **M5.5(종합 감리) 완료**,
**M6 Phase A+B+C 완료**, **STEP 87(리포트 품질 개선) 실질 완료**,
**Phase γ(미세 조정) 실질 완료**.
파이프라인 전체가 정상 작동하며, 리포트 품질·스타일·톤이 모두 개선되었다.
다음은 **Phase D(아카이빙 통합) + Supabase heartbeat 설정**이다.

### v21→v22 변경 사항 (2026-04-05 저녁)

**Phase γ — 미세 조정 완료:**

1. **규범 매핑 정비**: `pattern_ethics_relations` 테이블에서 무관한 매핑 7건 DELETE, 2건 strength 하향(strong→moderate). 전체 매핑 70건→63건. 마이그레이션 파일 `20260405000000_cleanup_pattern_ethics_relations.sql` 생성.

2. **Phase 1 모델 교체 — Sonnet 4.5 확정**: `pattern_matcher.py`의 `SONNET_MODEL`을 `claude-sonnet-4-5-20250929`로 변경. Phase 1(패턴 식별)=Sonnet 4.5, Phase 2(리포트 생성)=Sonnet 4.6 분리 구조. A/B 비교(B-11 기사)에서 패턴 식별 결과 유사, 비용 28% 절감, 모델 다양성에 의한 편향 감소 효과.

3. **인용 스타일링 구현**: 프롬프트에 〔〕 마커 형식 도입 + 프런트엔드 `highlightEthics` 함수 전면 교체.
   - 규범명(〔신문윤리실천요강 제3조 1항〕): 고딕(Pretendard), weight 400, opacity 0.9
   - 인용 내용('보도기사는...'): 명조(본문 동일), rgb(70,130,180)
   - 내부 코드(JEC-7 등) 사용 금지 → 한국어 조항 표현으로 통일
   - 이로써 '조항 번호 표시 통일' 과제도 동시 해결

4. **리포트 양식 개선 (4건)**:
   - 메타 정보 간결화: 프롬프트에 "1~2문장, 최대 80자, 한 줄 요약" 지시 추가
   - 첫머리 제목 제거: 3종 리포트 모두 제목(#) 없이 도입부 직접 시작
   - 중간제목 고딕화: H3(###)를 Pretendard 고딕, fontSize 1.1em으로 변경
   - 학생 리포트 톤: 초등 4~5학년 눈높이, 해요체 일관, 격식체 금지

5. **GitHub 관련**: PAT 만료일 2026-05-05로 갱신 완료. WIP 브랜치에 Phase γ 작업물 push 완료.

---

## M6 진행 현황 체크리스트

- [x] Phase A: 로컬 E2E 연결 ✅
- [x] Phase B: 코드베이스 위생 ✅
- [x] Phase C: 메타 패턴 추론 ✅
- [x] Phase C WIP 커밋 ✅
- [x] ★ STEP 86: 종합 E2E 품질 체감 ✅
- [x] ★ STEP 87: 리포트 품질 개선 ✅
- [x] **Phase γ: 미세 조정 ✅** ← v22 완료
- [x] WIP 브랜치 push (백업) ✅
- [ ] **Supabase heartbeat 설정** ← 다음 세션 첫 작업
- [ ] Phase D: 아카이빙 통합
- [ ] Phase E: 클라우드 배포 (프로덕션 DB 임베딩 실행 필요)
- [ ] Phase F: Reserved Test Set 검증
- [ ] Phase F-2: 리포트 링크 공유 기능
- [ ] Phase G: 마무리

---

## 파이프라인 최종 흐름 (Phase γ 완료 후) ★ v22 갱신

```
기사 → 청킹 → 벡터검색(OpenAI 임베딩, ★ 힌트) → ❶ Sonnet 4.5 Solo(패턴 식별 + Devil's Advocate CoT)
  → check_meta_patterns(탐지된 패턴, DB inferred_by 동적 조회)
  → 규범 조회(get_ethics_for_patterns RPC + REST API fallback)
  → ❷ Sonnet 4.6(3종 리포트: 〔〕마커 자연 인용, cite 태그 미사용)
  → 최종 리포트 (citation_resolver 비활성화)
```

**v21 대비 변경점:**
- Phase 1 모델: Sonnet 4.6 → **Sonnet 4.5** (`claude-sonnet-4-5-20250929`)
- 규범 매핑: 70건 → **63건** (7건 삭제, 2건 strength 하향)
- 인용 형식: 자연 인용 → **〔〕 마커 + 한국어 조항명** 방식
- 리포트 양식: 메타 정보 간결화, 첫머리 제목 제거, 중간제목 고딕, 학생 톤 초등 눈높이

---

## 다음 세션 작업

### 작업 0 (즉시): Supabase heartbeat 설정

Supabase 무료 플랜은 7일간 활동 없으면 프로젝트가 일시중지됨.
`.github/workflows/supabase-heartbeat.yml` 파일을 생성하여
GitHub Actions 크론잡으로 주 2회 간단한 SELECT 쿼리를 날리는 워크플로우 설정.
GitHub Secrets에 `SUPABASE_URL`과 `SUPABASE_KEY` 등록 필요.

### 작업 1: Phase D — 아카이빙 통합

**v22 기준 변경 사항 반영:**
- `citation_resolver.py`가 비활성화되었으므로, 관련 아카이빙 로직 제거
- 진단 JSON 덤프(`backend/diagnostics/`)를 아카이빙 체계에 통합할지 결정
- deprecated 코드 정리 (비교용 보존 원칙은 유지)
- `analysis_results` 테이블 스키마 설계 (기사 메타 + 3종 리포트 + 패턴 결과)

### 작업 2: Phase E — 클라우드 배포

**v22 기준 변경 사항 반영:**
- `pattern_matcher.py`의 모델이 Sonnet 4.5로 변경됨 → 프로덕션 환경변수 확인
- 프로덕션 DB에 `scripts/generate_embeddings.py` 실행 필수
- 프로덕션 DB에 매핑 정비 마이그레이션(`20260405000000_cleanup_...`) 적용 필요
- Railway(BE) + Vercel(FE) 배포 설정

### 작업 3: Phase F-2 — 리포트 링크 공유 기능 (Phase E 이후)

현재 결과 페이지가 sessionStorage 기반이라 URL 공유 불가.
링크 공유를 위해:
1. `analysis_results` 테이블에 분석 결과 저장 + 고유 ID 발급
2. `/result/[id]` 동적 라우팅 — Supabase에서 결과 불러와 렌더링
3. OG 메타 태그 — 카카오톡/페이스북 미리보기용 서버사이드 메타 생성

---

## 주요 파일 경로 (★ v22 갱신)

### 백엔드 (backend/core/) — ★ v22 갱신
```
backend/core/
├── pattern_matcher.py    ← ★ Phase 1 모델: claude-sonnet-4-5-20250929
├── report_generator.py   ← ★ Phase 2 모델: claude-sonnet-4-6 + 〔〕마커 프롬프트
├── pipeline.py           ← 파이프라인 (citation_resolver 비활성화, 진단 덤프)
├── meta_pattern_inference.py
├── citation_resolver.py  ← 비활성화 (코드 보존)
├── db.py / chunker.py / analyzer.py(참조용)
└── criteria_manager.py / prompt_builder.py
```

### 프런트엔드 — ★ v22 갱신
```
frontend/components/
└── ResultViewer.tsx       ← ★ highlightEthics 전면 교체 (〔〕마커 + 스타일 분리)
                             ★ H3 중간제목 고딕화 (Pretendard, 1.1em)
```

### 마이그레이션 파일
```
supabase/migrations/
├── 20260328000000_create_cr_check_schema.sql
├── 20260328100000_seed_data.sql
├── 20260329000000_data_implant_pattern_desc.sql
├── 20260401000000_meta_pattern_inference.sql
└── 20260405000000_cleanup_pattern_ethics_relations.sql  ← ★ NEW
```

### 문서 (docs/) — ★ v22 갱신
```
docs/
├── SESSION_CONTEXT_2026-04-05_v22.md      ← ★ 이 문서
├── phase_gamma_cli_prompt.md              ← Phase γ 작업 A+B 지시서
├── phase_gamma2_citation_style.md         ← Phase γ 작업 1~4 지시서
├── phase_gamma_ab_results.md              ← A/B 비교 결과
├── DB_AND_RAG_MASTER_PLAN_v4.0.md         ← ★ Phase D~F-2 갱신
├── Test/                                  ← B-11 기사 A/B 비교 진단+리포트
└── (기타 기존 문서 유지)
```

---

## 다음 세션의 Claude에게

### 핵심 지침

1. **Phase γ 완료.** 매핑 정비, 모델 교체, 인용 스타일링, 리포트 양식 개선 모두 완료.
2. **Phase 1 모델은 Sonnet 4.5 (`claude-sonnet-4-5-20250929`).** Phase 2는 Sonnet 4.6 (`claude-sonnet-4-6`). 이 분리 구조를 유지할 것.
3. **인용 형식은 〔〕 마커 방식.** cite 태그 폐기됨. 내부 코드(JEC-7 등) 사용 금지. 한국어 조항명만 사용.
4. **규범 매핑은 63건.** 기존 70건에서 7건 삭제, 2건 하향.
5. **벡터 검색 정상 작동.** 임베딩 401건. 프로덕션 배포 시 재실행 필요.
6. **진단 JSON 덤프가 `backend/diagnostics/`에 자동 저장됨.**
7. **Supabase heartbeat를 첫 작업으로 설정할 것.** 7일 비활성 방지.
8. **v21까지의 모든 교훈(1~27) 유효.**
9. **CLI 자율 진행 제한.** 플레이북 STEP 단위 승인 게이트 엄격 적용.

### 주의사항 (v21에서 계승 + 추가)

- **KJA 접두어 절대 금지**
- **Supabase Legacy JWT 키 사용 중**
- **GitHub PAT 만료일: 2026-05-05**
- **Reserved Test Set 73건은 참조 금지** (Phase F 전까지)
- **벤치마크 결과 파일 삭제 금지**
- **deprecated 코드 삭제 금지** (비교 실험용 보존)
- **프로덕션 배포 시 `scripts/generate_embeddings.py` 실행 필수**
- **프로덕션 배포 시 매핑 정비 마이그레이션 적용 필수** ★ NEW
- **`ResultViewer.tsx`의 규범명 opacity: 0.9 설정은 Gamnamu 개인 취향** ★ NEW

---

*이 세션 컨텍스트는 2026-04-05 저녁에 v21→v22로 갱신되었다.*
*Phase γ 미세 조정 완료: 매핑 정비, Sonnet 4.5 교체, 인용 스타일링, 리포트 양식 개선.*
*다음 작업: Supabase heartbeat → Phase D(아카이빙) → Phase E(배포) → Phase F-2(링크 공유).*
