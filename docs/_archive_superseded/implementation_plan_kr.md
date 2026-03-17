# CR 프로젝트 평가 시스템 고도화 구현 계획

## 목표
현재 평가 시스템을 **"Two-Layer" 아키텍처 (진단 & 근거 분리)** 로 업그레이드합니다.
AI가 생성하는 리포트가 **빠짐없이, 정확하게, 근거있게** 작성되도록 보장합니다.

## 핵심 전략: 진단(Diagnosis)과 근거(Evidence)의 분리
- **기존 방식 문제점**: 방대한 MD 파일을 통째로 AI에게 전달 → 핵심 누락, 윤리규범 환각 위험
- **개선 전략**:
  1. **진단 레이어**: 체크리스트(질문)로 문제를 빠르고 정확하게 탐지
  2. **근거 레이어**: 탐지된 문제에 대해서만 관련 윤리규범 원문을 정밀하게 매칭

---

## 변경 사항

### 1. 데이터 레이어 (신규)
`backend/data/` 디렉토리 생성

| 파일명 | 역할 | 비고 |
|--------|------|------|
| `criteria_checklist.json` | 진단용 체크리스트 (질문 + Red Flag + 규범ID) | `current-criteria_v2_active.md`에서 변환 |
| `ethics_library.json` | 윤리규범 원문 DB (인용 전용) | 환각 방지를 위한 Single Source of Truth |

---

### 2. 백엔드 핵심 모듈 (리팩토링)
`backend/core/` 디렉토리 신설

| 파일명 | 변경 유형 | 주요 로직 |
|--------|----------|----------|
| `criteria_manager.py` | 리팩토링 | JSON 로더 + `get_diagnostic_checklist()`, `get_ethics_context()` 구현 |
| `prompt_builder.py` | 신규 | 프롬프트 생성 전담, **Anthropic 프롬프트 캐싱** 헤더 적용 |
| `analyzer.py` | 전면 리팩토링 | 3단계 파이프라인 구현 |

#### 3단계 분석 파이프라인
```
Phase 0: Red Flag 사전 스크리닝 (코드 레벨, API 호출 없음)
    ↓
Phase 1: 정밀 진단 (Haiku) - 체크리스트 기반 문제 ID 탐지
    ↓
Phase 2: 근거 매핑 및 리포트 생성 (Sonnet) - 규범 인용 + 상세 분석
```

---

### 3. 유틸리티 (신규)
| 파일명 | 역할 |
|--------|------|
| `backend/tools/migrate_criteria.py` | MD → JSON 변환 스크립트 |

---

## 실행 로드맵

### Step 1: 데이터 마이그레이션 ← **현재 단계**
1. `migrate_criteria.py` 작성
2. `current-criteria_v2_active.md` 파싱
3. `criteria_checklist.json`, `ethics_library.json` 생성

### Step 2: 백엔드 핵심 모듈 구현
1. `backend/core/` 디렉토리 생성
2. `criteria_manager.py` 리팩토링
3. `prompt_builder.py` 신규 작성
4. `analyzer.py` 전면 리팩토링

### Step 3: 통합 및 검증
1. `main.py` 임포트 경로 수정
2. 로컬 서버 실행 후 E2E 테스트
3. Phase별 로그 확인 및 리포트 품질 검증

---

## 검증 계획

### 성공 기준
- [ ] Phase 0, 1, 2 로그가 순차적으로 출력됨
- [ ] 최종 리포트에 구체적인 규범 인용 포함 (예: "신문윤리실천요강 제3조")
- [ ] `reports` JSON 구조가 프론트엔드와 호환됨
