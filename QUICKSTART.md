# QUICKSTART.md

# CR-Check 빠른 시작 가이드

## 핵심 3단계

1. **평가 기준 통합**: docs/evaluatie-template.md + docs/current-criteria.md
→ backend/references/unified-criteria.md
2. **2단계 분석 플로우**:
    - Phase 1 (Haiku): 카테고리 식별 → JSON {"categories": [...]}
    - Phase 2 (Sonnet): 상세 리포트 → JSON {"comprehensive": ..., "journalist": ..., "student": ...}
3. **프롬프트 구조**:
    - Phase 1: 카테고리 목록만 (2KB)
    - Phase 2: 식별된 카테고리 상세 내용만 (8-15KB)

## 필수 파일

- `backend/criteria_manager.py`: 평가 기준 관리
- `backend/json_parser.py`: 재귀적 JSON 파싱
- `backend/analyzer.py`: 2단계 분석 로직
- `backend/references/unified-criteria.md`: 통합 평가 기준 (직접 생성 필요)

## 참고

- 상세 구현: IMPLEMENTATION_GUIDE.md Section 4-5
- 리포트 형식: docs/[샘플]평가 리포트.html

```

### 2. **프롬프트 템플릿 파일** (명시적 분리)

```

backend/prompts/
├── phase1_identify.txt          # Phase 1 프롬프트 템플릿
├── phase2_generate.txt          # Phase 2 프롬프트 템플릿
└── json_format_examples.json    # JSON 형식 예시