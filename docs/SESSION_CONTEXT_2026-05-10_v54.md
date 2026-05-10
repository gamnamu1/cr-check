# 세션 컨텍스트 — 2026-05-10 v54

## 프로젝트 한줄 요약

CR-Check: 한국 뉴스 기사의 언론 윤리 위반 여부를 AI가 진단하는 공익 도구. 프로덕션 가동 중 (Railway + Vercel + Supabase).

---

## 현 위치 한눈에

**MASTER_EXECUTION_PLAN_v1.0.md 기준: STEP 5 전체 완료 → STEP 6 실행 준비 완료.**

```
✅ STEP 0-B  윤리규범 DB 정리 (Phase 1~3 전체)
✅ STEP 2    DB 마이그레이션 + 107개 패턴 INSERT + 감리 + 후속 수정
✅ STEP 3    pattern_ethics_relations 재배분 (Phase 1~4 전체)
✅ STEP 4    코드 품질 개선 (4-A/4-B/4-C 전체)
✅ STEP 5    Sonnet 프롬프트 재설계 — 전체 완료
             ↳ 5-A: 블록1·2·3 CLI 실행 완료 (v51, 2026-05-08) ✅
             ↳ 5-B: 혼동 쌍 DB화 완료 (v53, 2026-05-09) ✅
             ↳ 5-C: 메타패턴 DEPRECATED 처리 완료 (v53, 2026-05-09) ✅
             ↳ 로컬 커밋: 완료 (2026-05-09 이후)
✅ STEP 6 계획 확정: STEP6_EMBEDDING_REGEN_PLAN_v9.md
             (GPT + Perplexity 11차 교차 감리 최종 승인, 2026-05-10)
🔲 STEP 6   임베딩 재생성 — 다음 세션에서 CLI 실행
🔲 STEP 7   골든셋 재정비 + R8 벤치마크 + threshold 재조정
```

---

## 2026-05-10 완료된 작업 (v53 → v54)

### STEP 6 세부 실행 계획 확정

- GPT·Perplexity 교차 감리 8차~11차(GPT 기준) 전 항목 반영 완료
- 최종 산출물: `docs/STEP6_EMBEDDING_REGEN_PLAN_v9.md`
- 이전 임시 파일명(`STEP 6 임베딩 재작성_계획 문서.md`) → 최종 파일명으로 변경 및 `docs/`로 이동

**주요 확정 사항 (v9 핵심):**

| 항목 | 내용 |
|---|---|
| `--dry-run` 단독 실행 | `exit 1` 코드 레벨 강제 (args.dry_run and not args.patterns_only) |
| `--dry-run` 범위 | API key 검사·OpenAI client·verify_embeddings() 모두 skip |
| `fetch_patterns()` | SQL 필터 제거 → Python tuple unpacking으로 NULL/공백 명시적 `exit 1` |
| A-3 / B-10 | pg_proc 1순위 → pg_get_functiondef 2순위 (2단계 일치) |
| D-21 | active vector leaf 한정 차원 확인 (전체 아님) |
| D-22 | vector leaf 1순위 + structural leaf 보조 쿼리 |
| D-24 | CTE 2단계: candidate_count ≥ 1 → 이상 코드 0건 순서 |
| D-24 골든셋 | 운영값 threshold=0.2, match_count=7로도 별도 실행, HIT/MISS 로그 |

### 문서 정리

- `SESSION_CONTEXT_2026-05-09_v52.md` → `docs/_archive_superseded/` 이동
- `MASTER_EXECUTION_PLAN_v1.0.md` v1.4 업데이트 (STEP 5-A 완료 마커, §12 참조 교체)
- `DB_AND_RAG_MASTER_PLAN_v4.0.md` §0 업데이트 (패턴 수 149건, 매핑 현황, 병목 해소 표기)

---

## 다음 세션: STEP 6 CLI 실행

**실행 문서**: `docs/STEP6_EMBEDDING_REGEN_PLAN_v9.md` (Phase A → E 순서)

### Phase A — 사전 점검 (기획자 SQL Editor)

```sql
-- A-3: RPC 실제 시그니처 확인 (1순위)
SELECT oid::regprocedure FROM pg_proc WHERE proname = 'search_pattern_candidates';

-- A-0: step6_start_ts 기록 (이후 D-18·D-19에서 사용)
SELECT NOW();  -- 반환값을 메모해둘 것
```

Phase A 확인 후 → CLI에 Phase B~C 지시 전달

### Phase C 실행 명령어

```bash
python scripts/generate_embeddings.py --db-url "$DATABASE_URL" --patterns-only --dry-run
# exit 0 확인 후
python scripts/generate_embeddings.py --db-url "$DATABASE_URL" --patterns-only
```

---

## DB 현황 (2026-05-09 기준, 변동 없음)

### patterns 테이블

| 구분 | 건수 |
|---|---|
| 대분류 (hierarchy_level=1) | 8 |
| 소분류·부모 (level=3, 2-segment) | 34 |
| leaf (level=3, 3-segment) | 107 |
| **합계** | **149** |

- `is_active=TRUE, structural`: 17건 (leaf 12 + 부모 5)
- `is_active=TRUE, vector`: 87건
- `is_active=FALSE`: 33건

### pattern_ethics_relations 테이블

- 활성 leaf 76개 전원 매핑 완료 (cnt ≥ 1)
- source별 분포: PCP 44.6% / JEC 30.7% / PCE 7.5% / EPG 4.9% / 기타 12.3%

---

## 벤치마크 이력 및 목표

| 버전 | FR | Precision | TN FP |
|---|---|---|---|
| R5 (현 프로덕션) | 36.7% | 44.2% | 6/6 |
| STEP 5 후 목표 | 60% | 70% | 4/6 이하 |
| R8 목표 (STEP 7) | 75% | 80% | 3/6 이하 |

※ STEP 4·5 효과는 STEP 6(임베딩 재생성) 완료 후 R8과 통합 측정.

---

## 핵심 설계 결정 (변경 불가)

- Sonnet Solo 1-Call 구조 유지
- TN 케이스: `pipeline.py`의 `_TN_MESSAGE` 정적 메시지
- 인용 방식: 〔규범 원문〕 마커 직접 출력
- 이진 게이트: 제거 확정 (R5)
- 임베딩 소스: STEP 6에서 `search_text` 기준으로 전환
- 메타패턴 추론: 완전 비활성화 확정 (STEP 5-C)
- 혼동 쌍: pattern_confusion_pairs 테이블 DB 동적 로드 (STEP 5-B)
- GitHub 커밋: 사람이 직접 수행. 푸시는 STEP 7 완료 후.
- 교차 감리 원칙: 모든 감리자 동일 프롬프트·역할 분리 금지

---

## 절대 원칙

1. CLI 자동 INSERT/UPDATE 금지 — DB 변경은 기획자가 SQL Editor에서 직접 실행
2. diff 선제시 → 기획자 승인 → 커밋 순서 엄수
3. STEP 단위 승인 게이트 — 승인 없이 다음 STEP 진행 금지
4. 단계 임의 통합 금지 — CLI는 전달받은 단계 지시만 실행
5. ON CONFLICT DO NOTHING (UPSERT 절대 금지)
6. STEP마다 분포 확인 쿼리 2개 의무 실행 — 총량만으로 PASS 불가

---

## 도구·환경

- 프로덕션 DB: DATABASE_URL in .env (Transaction pooler, port 6543)
- 벤치마크 스크립트: `scripts/benchmark_pipeline_v3.py`
- 골든셋: `docs/golden_dataset_final.json` (26건: TP 21 + TN 5)
- 기사 본문: `Golden_Data_Set_Pool/article_texts/*.txt`
- Antigravity: Strict Mode On, Deny List 9개, Agent Auto-Fix Lints Off

---

## 주요 산출물 (누적)

| 파일 | 내용 | 상태 |
|---|---|---|
| `docs/STEP6_EMBEDDING_REGEN_PLAN_v9.md` | STEP 6 세부 실행 계획 | **확정 (11차 감리 완료)** |
| `supabase/migrations/20260509232754_pattern_confusion_pairs.sql` | STEP 5-B 테이블 생성 | DB 실행 완료 |
| `supabase/seeds/pattern_confusion_pairs_seed.sql` | STEP 5-B 혼동 쌍 5개 | DB 실행 완료 |
| `backend/core/pattern_matcher.py` | STEP 5-A/B 전체 반영 | 로컬 커밋 완료 |
| `backend/core/pipeline.py` | STEP 4-C + 5-C 반영 | 로컬 커밋 완료 |
| `backend/core/report_generator.py` | STEP 4-A/B/C + 5-C 반영 | 로컬 커밋 완료 |
| `backend/core/meta_pattern_inference.py` | STEP 5-C DEPRECATED 처리 | 로컬 커밋 완료 |
| `docs/_scratch/step1_output_v3.md` | 107개 leaf 코드 체계 기준표 | 참조용 |

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v41~v46 | 2026-04-28~05-02 | STEP 0~2 완료 과정 |
| v47 | 2026-05-03 | STEP 3 완전 완료 (Phase 1~4). STEP 4 진입 대기. |
| v48 | 2026-05-06 | STEP 4 완전 완료 (4-A/4-B/4-C). STEP 5 진입 대기. |
| v49 | 2026-05-06 | STEP 5-A CLI 실행 프롬프트 v3 확정 (6인 교차 감리 3라운드 완료). |
| v50 | 2026-05-07 | STEP 5-A 프롬프트 v3 → 3블록 분할 완료. 블록별 감리 의견 반영. |
| v51 | 2026-05-08 | STEP 5-A 블록1·2·3 전체 완료. pattern_matcher.py 전면 재작성. 로컬 커밋 완료. |
| v52 | 2026-05-09 | STEP 5-B 혼동 쌍 5개 확정 완료. distinction_guide v4 확정. |
| v53 | 2026-05-09 | STEP 5-B/C CLI 실행 완료. STEP 5 전체 완료. 로컬 커밋 완료. |
| **v54** | **2026-05-10** | **STEP 6 계획 확정(STEP6_EMBEDDING_REGEN_PLAN_v9.md, 11차 감리 완료). 문서 정리(파일명 확정·이동, 마스터 플랜 2종 업데이트, v52 아카이브).** |
