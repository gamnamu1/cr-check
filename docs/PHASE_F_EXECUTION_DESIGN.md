# Phase F 실행 설계 — Reserved Test Set 격리 검증

> **상태**: STEP F-1 사전 준비 완료.
> **브랜치**: `feature/phase-f-validation`
> **근거**: `docs/_archive_superseded/CR_CHECK_M6_PLAYBOOK.md` L1152~1220 (STEP 98~103).
> **모드**: 20건 선별(격리 주입) → 파일럿 3건 → 본실행 17건 → 사후 채점.

---

## 0. 왜 이 설계가 필요한가

Reserved Test Set은 Dev Set(26건) 개발 과정에서 일체 참조하지 않은 독립
데이터로, 프로덕션 파이프라인의 **일반화 성능(generalization)** 확인에 쓰인다.
개발 중 테스트셋 정보가 우연히라도 코드/프롬프트에 유입되면 그 순간 Test로서의
가치가 사라진다. 따라서 Phase F는 **격리(isolation)** + **블라인드(blind)** 두
원칙을 물리·논리·코드 세 계층에서 동시에 지킨다.

**이 설계의 목표:**
1. Reserved Test Set 원본(73건)을 리포에 절대 유입시키지 않는다
2. 실행기가 레이블을 메모리에 올리지 않는다 (코드 레벨 차단)
3. 실행과 채점을 별도 스크립트로 분리하여 실수 열람을 구조적으로 차단한다
4. 비용과 재시도 예산을 사전 확정한다

---

## 1. 격리 3계층

### 계층 1 — 물리 격리 (파일 시스템)
- Reserved Test Set 원본 73건은 리포 외부 디렉토리에 보관 (경로는 코드/문서에 **명시 금지**).
- CLI는 해당 외부 디렉토리에 **접근하지 않는다**. 존재 확인조차 금지.
- Gamnamu가 외부 디렉토리에서 수동으로 20건을 선별하여 리포 내 임시 경로에 **복사**.

### 계층 2 — 논리 격리 (gitignore)
- 리포 내 주입 경로: `backend/diagnostics/phase_f/injected/`
- 이 디렉토리 전체를 `.gitignore`에 등록하여 실수 커밋 방지.
- 주입 파일 이름 관례: `reserved_subset_20.json` (권장, 스크립트 기본값).

### 계층 3 — 코드 격리 (allowlist 로딩 + 스크립트 분리)
- `phase_f_validation.py` (실행기): `id`, `url`만 메모리에 올림. `label` 필드는 접근 경로 자체가 없음.
- `phase_f_scoring.py` (집계기): 실행기가 끝난 후에만 호출됨. 이 단계에서만 `label`을 로드.
- 두 스크립트는 서로 다른 파일이므로, 실행 중 `label`이 섞일 가능성이 구조적으로 차단됨.

---

## 2. 주입 파일 스키마 (권장 가정)

**위치:** `backend/diagnostics/phase_f/injected/reserved_subset_20.json`

**최상위:** JSON array (20 items)

**항목 예시:**
```json
[
  {
    "id": "R-01",
    "url": "https://example.com/article/12345",
    "label": {
      "expected_patterns": ["1-1", "2-3-1a"],
      "is_tp": true,
      "difficulty": "medium",
      "selection_reason": "여론조사 오차범위 오용 + 출처 불명확"
    }
  }
]
```

**필수 필드:**
- `id` (string): 실행기/집계기 조인 키
- `url` (string): 분석 대상 URL
- `label` (object): 채점용. **집계기만 접근함**.

**`label` 하위 필드는 고정되지 않음.** 집계기 `_extract_expected_codes()`가
다음 후보 키를 차례로 시도: `expected_patterns` → `expected_codes` →
`gold_patterns` → `patterns`. 각 항목은 문자열 또는 `{"code": "..."}` 형식 허용.

> **주의**: Gamnamu가 주입 파일을 배치할 때 위 스키마를 따르지 않아도 됨.
> 주입 파일의 실제 스키마가 확정되는 시점에 `_extract_expected_codes()`를
> 1줄 수정하여 대응할 수 있도록 설계되어 있음.

---

## 3. 실행기 — `backend/scripts/phase_f_validation.py`

### 3.1 책임
- 주입 파일 블라인드 로딩 (allowlist: `id`, `url`만)
- `/analyze` 엔드포인트 호출 (단일 HTTP 요청)
- 네트워크/HTTP 레이어 재시도 (서버 측 LLM 재시도는 Phase 2 Bugfix가 담당)
- 건별 결과 파일 저장 + manifest 관리 + 체크포인트

### 3.2 인터페이스

| 인자 | 타입 | 설명 |
|---|---|---|
| `--pilot N` | int | 파일럿 N건 실행 (seed 기반 무작위 샘플) |
| `--full` | bool | 본실행 (주입 파일 전체, `--exclude-ids`로 제외 가능) |
| `--seed` | int (기본 42) | 파일럿 샘플링 시드 (재현 가능) |
| `--exclude-ids` | csv | 본실행 시 파일럿에서 사용한 ID 제외 |
| `--inject-path` | path | 주입 파일 경로 (기본: `backend/diagnostics/phase_f/injected/reserved_subset_20.json`) |
| `--dry-run` | bool | 스키마 검증만 수행, API 호출 없음 |

### 3.3 출력 구조
```
backend/diagnostics/phase_f/
├── injected/                       (gitignore)
│   └── reserved_subset_20.json     (Gamnamu 수동 배치)
└── run_<YYYYMMDD_HHMMSS>/
    ├── _manifest.json              (실행 요약, 3건마다 체크포인트 저장)
    ├── result_R-01.json            (건별 분석 응답)
    ├── result_R-02.json
    └── ...
```

### 3.4 재시도 로직
- 서버 측 `report_generator.py`의 Phase 2 Bugfix 분기(529/429/기타)가 LLM 레이어 재시도를 이미 처리함.
- 실행기의 `call_analyze()`는 **네트워크/HTTP 레이어** 재시도만 담당:
  - 529: 긴 백오프 `min(10 × 2^attempt, 60)` (10/20/40/60/60초), 5회
  - 429: 즉시 실패, 재시도 없음
  - 기타 HTTP/네트워크 오류: 짧은 백오프 `2^attempt`초, 5회
- 이 분기는 `backend/core/report_generator.py`의 v25 구조와 동일하게 유지.

### 3.5 파일럿/본실행 분리 절차

```bash
# F-2: 파일럿 (3건, seed=42)
python backend/scripts/phase_f_validation.py --pilot 3
# → run_<ts1>/_manifest.json 에 기록된 "ids" 확인 (예: R-05, R-11, R-18)

# F-3: 본실행 (17건, 파일럿 ID 제외)
python backend/scripts/phase_f_validation.py --full \
    --exclude-ids R-05,R-11,R-18
```

---

## 4. 집계기 — `backend/scripts/phase_f_scoring.py`

### 4.1 책임
- 실행 결과 디렉토리 로드 (`result_*.json`)
- 주입 파일 로드 (label 포함, **이 단계에서만**)
- id 기준 조인
- 건별 TP/FP/FN, precision/recall, 매크로 평균 계산
- 오분류 ID 목록 추출

### 4.2 인터페이스

| 인자 | 타입 | 설명 |
|---|---|---|
| `--run-dir` | path (required) | `run_<timestamp>` 디렉토리 |
| `--inject-path` | path (required) | 주입 파일 경로 (label 포함) |
| `--output` | path | 집계 결과 저장 경로 (기본: `<run-dir>/_scoring.json`) |

### 4.3 지표
- **건별**: `tp`, `fp`, `fn`, `precision`, `recall`, `misclassified`
- **매크로 평균**: `precision_macro`, `recall_macro`, `f1_macro` (per-item 평균)
- **오분류 목록**: `tp == 0 && (fp + fn) > 0` 인 ID 모음

### 4.4 판정 기준 (Playbook STEP 101 기준)
- ✅ Dev Set(26건) 대비 격차 **10%p 이내** + TN FP Rate 유지 → Phase F 완료
- ⚠️ 격차 10~15%p → 프롬프트 미세 조정 검토 (M7으로 이월)
- ❌ 격차 15%p 이상 → 감리 협의 (Playbook STEP 106)

---

## 5. 비용 예산

### 5.1 토큰 구조 (code-verified)

| 단계 | 파일:라인 | 모델 | `max_tokens` |
|---|---|---|---|
| Phase 1 패턴 식별 | `backend/core/pattern_matcher.py:577-580` | Sonnet 4.5 | 2048 |
| Phase 2 리포트 생성 | `backend/core/report_generator.py:546-548` | Sonnet 4.6 | 10000 |
| 청크 임베딩 | `backend/core/pattern_matcher.py:131-135` | text-embedding-3-small | — |

### 5.2 1건당 비용 추정
Claude Sonnet 4.x 요금: input $3/M, output $15/M

| 단계 | Input (추정) | Output (추정) | 비용 |
|---|---|---|---|
| 청크 임베딩 | ~500 tok | — | ≈$0 |
| Phase 1 | ~10k tok | ~1.5k tok | **$0.053** |
| Phase 2 | ~15k tok | ~6k tok | **$0.135** |
| **합계 평균** | | | **~$0.19** |
| **상한 (max output)** | ~20k | ~12k | **~$0.24** |

### 5.3 20건 기준 예산

| 시나리오 | 계산 | 금액 |
|---|---|---|
| 파일럿 3건 (평균) | 3 × $0.19 | **$0.57** |
| 본실행 17건 (평균) | 17 × $0.19 | **$3.23** |
| 20건 합계 (평균) | 20 × $0.19 | **$3.80** |
| 20건 상한 | 20 × $0.24 | **$4.80** |
| 재시도 버퍼 포함 (×2) | | **~$10** |

**Anthropic 잔액 확인:**
- https://console.anthropic.com/settings/billing
- Railway 환경변수 `ANTHROPIC_API_KEY` 계정 기준
- **권장 잔액**: ≥ $15 (상한 $5 + 재시도 버퍼 + 안전 마진)

> **주의**: Playbook v19 추정치 "$1.50"은 Sonnet Solo 1-Call 기준이고, 현재는
> Phase 1(Sonnet 4.5) + Phase 2(Sonnet 4.6) 2단 호출 구조이므로 실측이 더 높다.

### 5.4 캐시 효과
- `/analyze` 엔드포인트는 URL 정규화 + DB 캐시 조회 우선이므로, Gamnamu 수동
  배치 과정에서 동일 URL이 Dev Set과 중복되면 즉시 캐시 반환(비용 0원).
- Reserved Test Set은 Dev Set과 겹치지 않아야 함 (물리 격리 원칙).

---

## 6. 실행 절차 (STEP 단위)

### F-1 (이 STEP, 완료)
- [x] `feature/phase-f-validation` 브랜치 생성
- [x] `.gitignore`에 `backend/diagnostics/phase_f/injected/` 추가
- [x] `backend/scripts/phase_f_validation.py` 작성 (작성만)
- [x] `backend/scripts/phase_f_scoring.py` 작성 (작성만)
- [x] 본 문서 작성

### F-2 (다음 STEP, 승인 후)
- [ ] Gamnamu: 주입 파일 수동 배치 (`backend/diagnostics/phase_f/injected/reserved_subset_20.json`)
- [ ] Gamnamu: Anthropic 잔액 ≥$15 확인
- [ ] CLI: `python backend/scripts/phase_f_validation.py --pilot 3 --dry-run` (스키마 검증)
- [ ] CLI: `python backend/scripts/phase_f_validation.py --pilot 3` (실제 파일럿)
- [ ] CLI: 파일럿 manifest.json 보고 (성공/실패, 소요 시간, 예상 비용 확인)
- [ ] Gamnamu: 파일럿 결과 승인 후 F-3 진행 결정

### F-3 (본실행)
- [ ] CLI: `python backend/scripts/phase_f_validation.py --full --exclude-ids <파일럿 ID>`
- [ ] CLI: 본실행 manifest.json 보고

### F-4 (집계)
- [ ] CLI: `python backend/scripts/phase_f_scoring.py --run-dir ... --inject-path ...`
- [ ] Claude.ai: 결과 분석 + 일반화 성능 판정 (Playbook STEP 101)
- [ ] Antigravity/Manus: 종합 독립 감리 (Playbook STEP 102)

### F-5 (조건부 수정)
- [ ] 감리 지적 수정 반영 (Playbook STEP 103)

---

## 7. 금지 사항 (CLI)

- ❌ Pool 외부 디렉토리 접근 (`/Users/gamnamu/Documents/Golden_Data_Set_Pool` 등). **경로 언급도 금지**.
- ❌ `phase_f_validation.py` 실행 스크립트 자율 실행 (Gamnamu 승인 후에만)
- ❌ 주입 파일의 `label` 필드 열람 (집계기 외부에서)
- ❌ 주입 파일 git add / commit
- ❌ 다음 STEP 자율 진행 (STEP 단위 승인 게이트)

---

## 8. 확인 사항 (Gamnamu)

### 주입 전
- [ ] 20건 선별 기준 (난이도 분포, TP/TN 비율, 언론사 다양성)
- [ ] 주입 파일 스키마 — 본 문서 §2의 권장안과 차이 확인 (차이가 있으면 `_extract_expected_codes` 미세 조정 필요)
- [ ] Anthropic 잔액 $15 이상

### 주입 후
- [ ] 파일 경로: `backend/diagnostics/phase_f/injected/reserved_subset_20.json`
- [ ] 건수: 20
- [ ] `--dry-run`으로 스키마 검증 성공 확인

---

## 9. 참고 파일

| 파일 | 역할 |
|---|---|
| `backend/scripts/phase_f_validation.py` | 블라인드 실행기 |
| `backend/scripts/phase_f_scoring.py` | 사후 채점기 |
| `backend/core/pattern_matcher.py` | Phase 1 (Sonnet 4.5) |
| `backend/core/report_generator.py` | Phase 2 (Sonnet 4.6), 재시도 3분기 |
| `backend/core/storage.py` | URL 정규화 + 캐시 + 저장 |
| `backend/main.py` | `/analyze` 엔드포인트 |
| `docs/golden_dataset_final.json` | Dev Set 26건 (Reserved Test와 구분) |
| `docs/_archive_superseded/CR_CHECK_M6_PLAYBOOK.md` L1152~1220 | 원 Phase F STEP 정의 |

---

*본 문서는 STEP F-1 사전 준비 결과물이다. F-2 실행 전 Gamnamu 승인 필수.*
