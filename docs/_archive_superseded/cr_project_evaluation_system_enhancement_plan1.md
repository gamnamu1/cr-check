# CR 프로젝트 평가 시스템 고도화 플랜

## 1. 현황 진단

### 1.1 현재 시스템 구조

- **MVP 웹앱**: cr-check (github.com/gamnamu1/cr-check)
- **분석 흐름**: Phase 1 (Haiku - 카테고리 식별) → Phase 2 (Sonnet - 상세 리포트)
- **평가 기준**: 8개 대분류, 119개 세부 항목 (current-criteria_v2_active.md)

### 1.2 해결해야 할 문제

| 문제 | 현상 | 영향 |
|------|------|------|
| **서술형 기준** | AI가 "무엇을 검사해야 하는지" 불명확 | 탐지 누락, 일관성 저하 |
| **규범 연계 부족** | 평가 기준과 윤리규범이 분리 | 인용 부정확, 근거 빈약 |
| **구조화 미비** | 진단 기준이 암묵적으로 숨어 있음 | AI 판단력 저하 |
| **환각 위험** | AI가 존재하지 않는 규범을 생성할 수 있음 | 리포트 신뢰도 하락 |

---

## 2. 설계 원칙

### 2.1 최우선 목표

> **"시민 독자가 받아볼 평가 리포트의 퀄리티 극대화"**

이를 위한 3대 조건:

1. **빠짐없이** - 기사 내 모든 문제적 보도 관행 탐지
2. **정확하게** - 기사 본문에서 증거 직접 인용
3. **근거있게** - 관련 언론윤리규범 정확히 매칭

### 2.2 핵심 전략: 진단과 근거의 분리 (Diagnosis & Evidence)

단순히 긴 텍스트 파일을 AI에게 던져주는 방식에서 벗어나, **'진단(체크리스트)'**과 **'근거(윤리규범)'**를 구조적으로 분리하여 관리하는 **이중 레이어(Two-Layer) 전략**을 채택합니다.

- **기존 방식의 문제점:** 방대한 서술형 텍스트를 통째로 주면 AI가 핵심을 놓치거나, 문제 현상과 윤리 규범을 섞어서 부정확하게 인용할 위험이 있음
- **변경 전략:**
  1. **진단(Diagnosis):** 기사를 읽을 때는 **'체크리스트(질문)'**만 사용하여 문제를 빠르고 정확하게 탐지
  2. **근거(Evidence):** 탐지된 문제에 대해서만 **'관련 윤리규범 전문'**을 정밀하게 가져와 매칭

### 2.3 핵심 설계 결정

#### 결정 1: 전체 스캔 방식 채택

차원별 분리 분석(예: 진실성만, 균형성만)은 토큰을 절약하지만, **교차 문제를 누락**할 위험이 있습니다. 예를 들어 "제목 낚시 + 통계 왜곡"이 복합된 기사에서 하나만 검색하면 다른 문제를 놓칩니다.

**→ Phase 2에서 전체 평가 기준을 입력하고 AI가 모두 스캔하도록 합니다.**

#### 결정 2: 벡터DB(RAG) 보류

RAG는 질문과 유사한 일부만 가져오므로, "검색되지 않은 기준은 평가에서 제외"됩니다. 이는 "빠짐없이 분석"이라는 최우선 목표와 정면 충돌합니다.

**→ MVP 단계에서는 로컬 JSON 파일 기반으로 진행. 벡터DB는 규모 확대 시 재검토.**

#### 결정 3: 프롬프트 캐싱으로 비용 해결

전체 기준 입력 시 토큰 비용 증가 우려가 있으나, Anthropic의 **프롬프트 캐싱** 기능을 활용하면 비용 최대 90% 절감, 속도 2배 이상 향상이 가능합니다.

#### 결정 4: 규범 분리 저장 + 자동 병합

- 평가 기준 파일에는 **규범 ID만** 기록
- 규범 원문은 **별도 파일**에 저장 (단일 진실 소스)
- 프롬프트 생성 시 자동 병합
- **환각 방지**: AI에게 검색을 시키는 게 아니라, 우리가 준비한 규범 텍스트 내에서만 찾게 하므로 없는 조항을 지어낼 수 없음

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│  CR 평가 시스템 아키텍처                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📁 데이터 레이어 (JSON 파일)                                     │
│  ├─ criteria_checklist.json  ← 평가 기준 + 진단 질문 + Red Flag  │
│  └─ ethics_library.json      ← 언론윤리규범 원문 (단일 진실 소스)  │
│                                                                 │
│  🔄 분석 파이프라인                                               │
│  ├─ Phase 0: Red Flag 사전 스크리닝 (코드 레벨, API 호출 없음)    │
│  ├─ Phase 1: Haiku - 전체 진단 질문 기반 문제 탐지               │
│  └─ Phase 2: Sonnet - 탐지된 문제 + 규범 주입 → 상세 리포트      │
│      └─ 프롬프트 캐싱 적용 (비용 90% 절감)                        │
│                                                                 │
│  🔧 핵심 컴포넌트                                                 │
│  ├─ criteria_manager.py      ← 기준 로드 + 규범 병합              │
│  ├─ prompt_builder.py        ← 프롬프트 생성 (캐싱 지원)          │
│  └─ analyzer.py              ← Claude API 호출                   │
│                                                                 │
│  📝 리포트 생성                                                   │
│  └─ 문제 지적 + 기사 증거 + 규범 원문 인용                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 파일 구조

```
backend/
├── data/
│   ├── criteria_checklist.json     # 평가 기준 + 진단 질문 + Red Flag
│   └── ethics_library.json         # 언론윤리규범 원문
├── core/
│   ├── criteria_manager.py         # 기준 로드 + 규범 병합
│   ├── prompt_builder.py           # 프롬프트 생성 (캐싱 지원)
│   └── analyzer.py                 # Claude API 호출
└── tests/
    └── sample_articles/            # 테스트용 기사
```

---

## 4. 데이터 구조 설계

### 4.1 criteria_checklist.json - 진단용 두뇌

새 평가 기준(current-criteria_v2_active.md)을 AI가 체계적으로 검사할 수 있는 형태로 변환한 데이터입니다.

**역할:** Phase 1 진단 단계에서 사용

```json
{
  "version": "2.0",
  "categories": [
    {
      "id": "1-1",
      "name": "진실성과 정확성",
      "subcategories": [
        {
          "id": "1-1-1",
          "name": "사실 검증 부실",
          "definition": "정보의 정확성을 충분히 확인하지 않거나, 교차 검증 및 반론권 보장 절차를 생략한 보도",
          "severity": "critical",

          "diagnostic_questions": [
            {
              "q_id": "1-1-1-a",
              "question": "민감한 사안임에도 익명의 단일 취재원 발언에만 의존했는가?",
              "red_flags": [
                "관계자에 따르면",
                "소식통에 의하면",
                "~로 알려졌다 (단독 사용)"
              ],
              "weight": 0.35
            },
            {
              "q_id": "1-1-1-b",
              "question": "비판 대상에게 반론 기회를 실질적으로 제공했는가?",
              "red_flags": [
                "연락이 닿지 않았다",
                "답변을 거부했다 (구체적 시도 없이)",
                "반론 내용 1문장 이하"
              ],
              "weight": 0.40
            },
            {
              "q_id": "1-1-1-c",
              "question": "취재원의 주장을 따옴표로만 처리하고 검증 없이 전달했는가?",
              "red_flags": [
                "제목에 따옴표 + 폭로성 발언",
                "본문 따옴표 인용 비중 30% 초과"
              ],
              "weight": 0.25
            }
          ],

          "ethics_code_refs": [
            "newspaper_ethics_practice_3_4",
            "newspaper_ethics_practice_3_9",
            "journalism_ethics_charter_1"
          ]
        },
        {
          "id": "1-7-3",
          "name": "낚시성 제목",
          "definition": "본문 내용과 다르거나 과장된 제목으로 독자를 유인하는 행위",
          "severity": "major",

          "diagnostic_questions": [
            {
              "q_id": "1-7-3-a",
              "question": "제목이 기사 본문의 내용과 다르거나 과장되었는가?",
              "red_flags": [
                "제목에 '충격', '경악', '발칵' 등 자극적 표현",
                "본문에 없는 내용이 제목에 등장"
              ],
              "weight": 0.50
            },
            {
              "q_id": "1-7-3-b",
              "question": "물음표(?) 등을 사용하여 근거 없는 의혹을 확정적 사실처럼 보이게 했는가?",
              "red_flags": [
                "제목에 물음표 + 부정적 암시",
                "~인가?, ~했나? 형태의 의혹 제기"
              ],
              "weight": 0.50
            }
          ],

          "ethics_code_refs": [
            "newspaper_ethics_practice_10_1",
            "journalism_ethics_charter_9"
          ]
        }
      ]
    }
  ]
}
```

**설계 포인트:**

- `diagnostic_questions`: AI가 "Yes/No"로 판단할 수 있는 명확한 질문
- `red_flags`: 기사에서 탐지할 구체적 표현/패턴 (Phase 0 사전 스크리닝에 활용)
- `weight`: 심각도 가중치 (추후 종합 평가 시 활용 가능)
- `ethics_code_refs`: 규범 ID만 기록 (원문은 별도 파일)

### 4.2 ethics_library.json - 인용용 라이브러리

언론윤리규범(강령, 준칙, 헌장 등)의 **전문(Full Text)**을 담은 데이터베이스입니다.

**역할:** Phase 2 리포트 작성 단계에서 정확한 인용(Copy & Paste)을 위해 사용

```json
{
  "codes": {
    "newspaper_ethics_practice_3_4": {
      "source": "신문윤리실천요강",
      "article": "제3조",
      "clause": "4항",
      "title": "미확인보도 명시",
      "full_text": "출처가 분명하지 않거나 확인되지 않은 사실을 부득이 보도할 때는 그 사유를 분명히 밝혀야 한다.",
      "keywords": ["출처", "확인", "명시"]
    },
    "newspaper_ethics_practice_3_9": {
      "source": "신문윤리실천요강",
      "article": "제3조",
      "clause": "9항",
      "title": "피의사실 보도",
      "full_text": "신문은 범죄의 피의자 또는 피고인에 대한 보도를 할 때 무죄추정의 원칙을 존중해야 하며, 피의자 측에게 해명의 기회를 주기 위해 최선을 다해야 한다.",
      "keywords": ["무죄추정", "피의자", "해명기회"]
    },
    "journalism_ethics_charter_1": {
      "source": "언론윤리헌장",
      "article": "제1조",
      "clause": null,
      "title": "진실 보도",
      "full_text": "언론인은 모든 정보를 성실하게 검증하고 명확한 근거를 바탕으로 보도한다.",
      "keywords": ["검증", "근거", "진실"]
    },
    "newspaper_ethics_practice_10_1": {
      "source": "신문윤리실천요강",
      "article": "제10조",
      "clause": "1항",
      "title": "제목의 정확성",
      "full_text": "기사의 제목은 기사 내용을 정확하게 반영해야 하며, 과장하거나 왜곡해서는 안 된다.",
      "keywords": ["제목", "정확", "과장"]
    },
    "journalism_ethics_charter_9": {
      "source": "언론윤리헌장",
      "article": "제9조",
      "clause": null,
      "title": "디지털 환경의 책임",
      "full_text": "언론인은 디지털 환경에서 클릭 유도를 위한 선정적 제목이나 과장된 표현을 자제한다.",
      "keywords": ["디지털", "클릭", "선정적"]
    }
  }
}
```

**설계 포인트:**

- 규범 원문을 **단일 파일에서 관리** (Single Source of Truth)
- 규범 업데이트 시 한 곳만 수정
- 같은 규범이 여러 기준에서 참조되어도 중복 없음
- **환각 방지**: AI는 이 라이브러리 내의 텍스트만 인용 가능

### 4.3 규범 매핑 설계: 1:N 관계

하나의 문제적 보도 패턴은 **여러 윤리규범과 연결**될 수 있습니다.

```
"단일 취재원 의존" (1-1-1-a)
    │
    ├─→ 신문윤리실천요강 제3조 4항 (출처 명시)
    ├─→ 신문윤리실천요강 제3조 9항 (해명 기회)
    └─→ 언론윤리헌장 제1조 (진실 보도)

→ 사전 매핑은 "후보군"을 제공
→ AI가 맥락에 맞는 1-2개를 선택하여 인용
```

---

## 5. 분석 파이프라인

### 5.1 3단계 분석 프로세스

```
┌──────────────────────────────────────────────────────────────┐
│                     분석 파이프라인                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 0: Red Flag 사전 스크리닝                              │
│  ├─ 입력: 기사 본문                                          │
│  ├─ 처리: 코드 레벨에서 red_flags 패턴 매칭 (API 호출 없음)   │
│  └─ 출력: 의심 항목 ID 리스트 + 기사 텍스트 (Phase 1로 전달)  │
│                                                              │
│                         ↓                                    │
│                                                              │
│  Phase 1: 정밀 진단 (Haiku)                                   │
│  ├─ 입력: 기사 본문 + diagnostic_questions 전체               │
│  ├─ 처리: AI가 각 질문에 Yes/No 판단                         │
│  └─ 출력: 발견된 문제 ID 리스트 (예: ["1-1-1", "1-7-3"])      │
│                                                              │
│                         ↓                                    │
│                                                              │
│  Phase 2: 근거 매핑 및 리포트 작성 (Sonnet)                   │
│  ├─ 입력: 기사 본문 + 탐지된 ID + 관련 규범 텍스트 주입       │
│  ├─ 처리: 프롬프트 캐싱 적용, 규범 기반 상세 분석            │
│  └─ 출력: 완성된 평가 리포트                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Phase 0: Red Flag 사전 스크리닝

**목적:** API 호출 전에 명백한 위험 신호를 미리 탐지하여 Phase 1의 정확도 향상

```python
def pre_screen_red_flags(article_text: str) -> dict:
    """
    Red flag 패턴을 먼저 스캔하여 AI 분석 효율화

    - API 호출 없이 코드 레벨에서 처리
    - 탐지된 패턴을 Phase 1에 힌트로 전달
    """
    detected = []
    checklist = load_criteria_checklist()

    for category in checklist['categories']:
        for sub in category['subcategories']:
            for q in sub['diagnostic_questions']:
                for flag in q['red_flags']:
                    if flag in article_text:
                        detected.append({
                            'criteria_id': sub['id'],
                            'q_id': q['q_id'],
                            'matched_flag': flag,
                            'severity': sub['severity']
                        })

    return {
        'flagged_items': detected,
        'flagged_ids': list(set([d['criteria_id'] for d in detected]))
    }
```

### 5.3 Phase 1: 정밀 진단 (Issue Detection)

**목적:** 전체 진단 질문을 기반으로 기사의 모든 문제점 탐지

- **입력:** 기사 본문 + criteria_checklist.json의 **진단 질문(diagnostic_questions)** 목록 + Phase 0 힌트
- **작업:** AI는 기사를 읽고 질문에 "Yes"라고 답할 수 있는 항목을 찾음
- **출력:** 발견된 문제의 ID 리스트 (예: `["1-1-1", "1-7-3"]`)

```python
def run_phase1_diagnosis(article_text: str, pre_screen_result: dict) -> list:
    """Phase 1: Haiku를 사용한 정밀 진단"""

    checklist = criteria_manager.get_diagnostic_checklist()
    flagged_hint = pre_screen_result.get('flagged_ids', [])

    prompt = f"""다음 기사를 읽고 아래 체크리스트 중 해당하는 항목을 모두 선택하시오.

[사전 탐지된 의심 항목]: {flagged_hint}
위 항목들은 텍스트 패턴 매칭으로 사전 탐지된 것입니다.
이 항목들을 우선 검토하되, 다른 항목도 빠짐없이 확인하십시오.

[기사 본문]
{article_text}

[진단 체크리스트]
{checklist}

[출력 형식]
JSON: {{"detected_issues": ["1-1-1", "1-7-3", ...]}}
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)['detected_issues']
```

### 5.4 Phase 2: 근거 매핑 및 리포트 작성 (Evidence Mapping & Reporting)

**목적:** 탐지된 문제에 대해 정확한 규범을 인용하여 완성도 높은 리포트 생성

- **입력:** 기사 본문 + Phase 1에서 찾은 ID 리스트
- **시스템 동작 (핵심):**
  1. 백엔드는 발견된 ID(1-1-1)에 연결된 `ethics_code_refs`를 확인
  2. `ethics_library.json`에서 해당 규범의 **전문(Text)**을 가져옴
  3. 프롬프트에 **"이 기사는 [사실 검증 부실] 문제가 의심됩니다. 아래 제공된 [윤리규범 텍스트]를 참고하여 위반 사항을 정확히 지적하십시오."**라며 규범 텍스트를 주입(Injection)
- **출력:** 문제점 지적 (기사 문장 인용) + 윤리적 근거 (규범 조항 정확히 인용)

```python
def run_phase2_report(article_url: str, article_text: str, detected_ids: list) -> str:
    """Phase 2: Sonnet을 사용한 상세 리포트 생성"""

    # 탐지된 문제에 관련된 규범만 필터링하여 가져옴
    ethics_context = criteria_manager.get_ethics_context(detected_ids)
    criteria_context = criteria_manager.get_criteria_by_ids(detected_ids)

    system_prompt = """당신은 'CR 프로젝트'의 수석 미디어 감사관입니다.

## 임무
시민 독자에게 제공될 고품질 비평 리포트를 작성하십시오.

## 분석 원칙 (최우선)
1. **빠짐없이**: 제공된 모든 문제 항목을 하나도 빠뜨리지 말고 분석하십시오.
2. **정확하게**: 문제를 지적할 때는 반드시 기사 본문에서 직접 인용하십시오.
3. **근거있게**: 제공된 언론윤리규범 텍스트를 정확히 인용하십시오.

## 중요 제약
- 규범 인용 시 반드시 [제공된 규범 텍스트]만 사용하십시오.
- 제공되지 않은 규범을 임의로 생성하거나 인용하지 마십시오.

## 출력 형식
각 문제점마다:
- **지적**: "[항목ID] 위반 - [진단 질문 요약]"
- **증거**: "기사 본문 중 '...'는 ..."
- **근거**: "[규범명 제X조]에 따르면 '...'"
"""

    user_prompt = f"""다음 기사에서 발견된 문제점들을 분석하십시오.

[기사 URL]: {article_url}

[기사 본문]
{article_text}

[탐지된 문제 항목]
{criteria_context}

[적용할 언론윤리규범 - 이 텍스트만 인용 가능]
{ethics_context}

위 정보를 바탕으로 각 문제점에 대해 증거와 윤리규범 근거를 제시하십시오."""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # 프롬프트 캐싱
            }
        ],
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text
```

---

## 6. 핵심 컴포넌트 설계

### 6.1 CriteriaManager

```python
class CriteriaManager:
    """평가 기준 및 윤리규범 관리"""

    def __init__(self):
        self.checklist = self._load_json('data/criteria_checklist.json')
        self.ethics_library = self._load_json('data/ethics_library.json')

    def _load_json(self, path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_diagnostic_checklist(self) -> str:
        """Phase 1용 진단 질문 리스트 반환"""
        lines = []
        for category in self.checklist['categories']:
            lines.append(f"## {category['name']}")
            for sub in category['subcategories']:
                lines.append(f"\n### {sub['id']}. {sub['name']}")
                lines.append(f"정의: {sub['definition']}")
                lines.append("진단 질문:")
                for q in sub['diagnostic_questions']:
                    lines.append(f"  - [{q['q_id']}] {q['question']}")
        return "\n".join(lines)

    def get_red_flags(self) -> list:
        """Phase 0용 Red Flag 패턴 리스트 반환"""
        flags = []
        for category in self.checklist['categories']:
            for sub in category['subcategories']:
                for q in sub['diagnostic_questions']:
                    for flag in q.get('red_flags', []):
                        flags.append({
                            'pattern': flag,
                            'criteria_id': sub['id'],
                            'q_id': q['q_id'],
                            'severity': sub['severity']
                        })
        return flags

    def get_criteria_by_ids(self, ids: list) -> str:
        """ID 목록으로 해당 평가 기준 상세 반환"""
        result = []
        for category in self.checklist['categories']:
            for sub in category['subcategories']:
                if sub['id'] in ids:
                    result.append(f"### {sub['id']}. {sub['name']}")
                    result.append(f"정의: {sub['definition']}")
                    result.append("진단 질문:")
                    for q in sub['diagnostic_questions']:
                        result.append(f"  - {q['question']}")
        return "\n".join(result)

    def get_ethics_context(self, issue_ids: list) -> str:
        """
        Phase 2용: 감지된 이슈 ID 목록을 받으면,
        관련된 윤리규범 텍스트만 필터링하여 문자열로 반환
        """
        ethics_ids = set()

        # 탐지된 이슈에 연결된 규범 ID 수집
        for category in self.checklist['categories']:
            for sub in category['subcategories']:
                if sub['id'] in issue_ids:
                    ethics_ids.update(sub.get('ethics_code_refs', []))

        # 규범 원문 조회 및 포맷팅
        result = []
        for ethics_id in ethics_ids:
            code = self.ethics_library['codes'].get(ethics_id)
            if code:
                clause = f" {code['clause']}" if code.get('clause') else ""
                result.append(
                    f"**{code['source']} {code['article']}{clause} '{code['title']}'**\n"
                    f"> {code['full_text']}"
                )

        return "\n\n".join(result)
```

### 6.2 PromptBuilder

```python
class PromptBuilder:
    """프롬프트 생성 (캐싱 지원)"""

    def __init__(self, criteria_manager: CriteriaManager):
        self.cm = criteria_manager
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """당신은 'CR 프로젝트'의 수석 미디어 감사관입니다.

## 임무
시민 독자에게 제공될 고품질 비평 리포트를 작성하십시오.

## 분석 원칙 (최우선)
1. **빠짐없이**: 제공된 모든 평가 기준을 하나도 빠뜨리지 말고 검토하십시오.
2. **정확하게**: 문제를 지적할 때는 반드시 기사 본문에서 직접 인용하십시오.
3. **근거있게**: 매핑된 언론윤리규범을 정확히 인용하십시오.

## 분석 절차
1. 기사 전문을 정독합니다.
2. 각 항목의 **'진단 질문'**을 기사에 대입합니다.
3. 진단 질문에 'Yes'로 답할 수 있다면:
   - 해당 항목 위반으로 판단
   - 기사에서 증거 문장을 직접 인용
   - 제공된 윤리규범 중 가장 적합한 것을 선택하여 인용

## 중요 제약
- 규범 인용 시 반드시 [제공된 규범 텍스트]만 사용하십시오.
- 제공되지 않은 규범을 임의로 생성하지 마십시오.

## 출력 형식
각 문제점마다:
- **지적**: "[항목ID] 위반 - [진단 질문 요약]"
- **증거**: "기사 본문 중 '...'는 ..."
- **근거**: "[규범명 제X조]에 따르면 '...'"
"""

    def build_phase1_prompt(self, article_text: str, flagged_hint: list) -> dict:
        """Phase 1용 프롬프트 생성"""
        checklist = self.cm.get_diagnostic_checklist()

        return {
            "system": "당신은 뉴스 기사의 문제적 보도 관행을 탐지하는 전문가입니다.",
            "user": f"""다음 기사를 읽고 아래 체크리스트 중 해당하는 항목을 모두 선택하시오.

[사전 탐지된 의심 항목]: {flagged_hint}
이 항목들을 우선 검토하되, 다른 항목도 빠짐없이 확인하십시오.

[기사 본문]
{article_text}

[진단 체크리스트]
{checklist}

[출력 형식]
JSON: {{"detected_issues": ["1-1-1", "1-7-3", ...]}}
"""
        }

    def build_phase2_prompt(self, article_url: str, article_text: str,
                           detected_ids: list) -> dict:
        """Phase 2용 프롬프트 생성 (캐싱 지원)"""

        criteria_context = self.cm.get_criteria_by_ids(detected_ids)
        ethics_context = self.cm.get_ethics_context(detected_ids)

        return {
            "system": [
                {
                    "type": "text",
                    "text": self._system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            "user": f"""다음 기사에서 발견된 문제점들을 분석하십시오.

[기사 URL]: {article_url}

[기사 본문]
{article_text}

[탐지된 문제 항목]
{criteria_context}

[적용할 언론윤리규범 - 이 텍스트만 인용 가능]
{ethics_context}

위 정보를 바탕으로 각 문제점에 대해 증거와 윤리규범 근거를 제시하십시오."""
        }
```

### 6.3 Analyzer

```python
from anthropic import Anthropic

class Analyzer:
    """기사 분석 실행"""

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.cm = CriteriaManager()
        self.pb = PromptBuilder(self.cm)

    def analyze(self, article_url: str, article_text: str) -> dict:
        """전체 분석 파이프라인 실행"""

        # Phase 0: Red Flag 사전 스크리닝
        phase0_result = self._run_phase0(article_text)

        # Phase 1: 정밀 진단 (Haiku)
        phase1_result = self._run_phase1(article_text, phase0_result)

        # Phase 2: 상세 분석 및 리포트 (Sonnet)
        phase2_result = self._run_phase2(article_url, article_text, phase1_result)

        return {
            "phase0_flags": phase0_result,
            "phase1_detected": phase1_result,
            "report": phase2_result
        }

    def _run_phase0(self, article_text: str) -> dict:
        """Phase 0: Red Flag 사전 스크리닝 (API 호출 없음)"""
        red_flags = self.cm.get_red_flags()
        detected = []

        for flag in red_flags:
            if flag['pattern'] in article_text:
                detected.append(flag)

        return {
            'flagged_items': detected,
            'flagged_ids': list(set([d['criteria_id'] for d in detected]))
        }

    def _run_phase1(self, article_text: str, phase0_result: dict) -> list:
        """Phase 1: Haiku를 사용한 정밀 진단"""
        prompt = self.pb.build_phase1_prompt(
            article_text,
            phase0_result['flagged_ids']
        )

        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=prompt["system"],
            messages=[{"role": "user", "content": prompt["user"]}]
        )

        result = json.loads(response.content[0].text)
        return result.get('detected_issues', [])

    def _run_phase2(self, article_url: str, article_text: str,
                   detected_ids: list) -> str:
        """Phase 2: Sonnet을 사용한 상세 리포트 (프롬프트 캐싱 적용)"""

        if not detected_ids:
            return "분석 결과: 주요 문제점이 탐지되지 않았습니다."

        prompt = self.pb.build_phase2_prompt(article_url, article_text, detected_ids)

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=4000,
            system=prompt["system"],
            messages=[{"role": "user", "content": prompt["user"]}]
        )

        return response.content[0].text
```

---

## 7. 생성되는 리포트 예시

```markdown
# CR 평가 리포트

## 분석 대상
- URL: https://example.com/news/12345
- 분석일시: 2025-01-15

---

## 발견된 문제점

### 1-1-1 위반 - 사실 검증 부실

**지적**: 민감한 정책 비판 사안임에도 익명의 단일 취재원에만 의존했습니다.

**증거**:
기사 본문 중 *"정부 고위 관계자에 따르면 이번 정책은 완전히 실패한 것으로 평가된다"*는
단일 익명 취재원의 발언만을 근거로 하고 있으며, 이에 대한 교차 검증이나
정부 측 공식 반론이 포함되어 있지 않습니다.

**근거**:
> **신문윤리실천요강 제3조 4항 '미확인보도 명시'**
> 출처가 분명하지 않거나 확인되지 않은 사실을 부득이 보도할 때는 그 사유를 분명히 밝혀야 한다.

---

### 1-7-3 위반 - 낚시성 제목

**지적**: 제목이 기사 본문의 내용과 다르거나 과장되었습니다.

**증거**:
제목 *"정부 정책 '완전 실패'…충격 폭로"*는 본문에서 한 관계자의 개인 의견으로만
언급된 내용을 마치 확정된 사실인 것처럼 표현하고 있습니다.

**근거**:
> **신문윤리실천요강 제10조 1항 '제목의 정확성'**
> 기사의 제목은 기사 내용을 정확하게 반영해야 하며, 과장하거나 왜곡해서는 안 된다.

---

## 종합 평가
이 기사는 **2개의 주요 윤리 위반 사항**이 발견되었습니다.
특히 사실 검증 부실(심각도: Critical)과 낚시성 제목(심각도: Major)이
복합적으로 나타나 독자의 올바른 정보 습득을 저해할 우려가 있습니다.
```

---

## 8. 실행 로드맵

### Phase 1 (Week 1-2): 데이터 구조화

| 작업 | 상세 | 산출물 |
|------|------|--------|
| 평가 기준 변환 | 새 버전의 각 항목을 진단 질문 형식으로 변환 | criteria_checklist.json |
| Red Flag 추출 | 각 진단 질문에 탐지 패턴 추가 | criteria_checklist.json 내 red_flags |
| 규범 수집 | 신문윤리실천요강, 언론윤리헌장 등 원문 수집 | ethics_library.json |
| 매핑 작업 | 각 평가 기준에 관련 규범 ID 연결 | criteria_checklist.json 내 ethics_code_refs |

### Phase 2 (Week 3-4): 핵심 컴포넌트 구현

| 작업 | 상세 | 산출물 |
|------|------|--------|
| CriteriaManager | 기준 로드 + 규범 병합 + Red Flag 추출 | criteria_manager.py |
| PromptBuilder | 캐싱 지원 프롬프트 생성 | prompt_builder.py |
| Analyzer 수정 | 3단계 파이프라인 적용 | analyzer.py |

### Phase 3 (Week 5-6): 테스트 및 최적화

| 작업 | 상세 | 산출물 |
|------|------|--------|
| 테스트 기사 수집 | 다양한 문제 유형의 기사 10-20개 | sample_articles/ |
| 품질 검증 | 탐지율, 규범 인용 정확도 측정 | 테스트 리포트 |
| 프롬프트 튜닝 | 결과 기반 프롬프트 개선 | 최적화된 프롬프트 |

---

## 9. 성공 지표

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| **문제점 탐지율** | 85% 이상 | 전문가 검수 대비 AI 탐지 비율 |
| **규범 인용 정확도** | 100% | ethics_library.json과 일치 여부 |
| **복합 문제 탐지** | 90% 이상 | 2개 이상 문제가 있는 기사에서 모두 탐지 |
| **환각 발생률** | 0% | 제공되지 않은 규범 인용 여부 |
| **기사당 분석 시간** | 30초 이내 | API 호출 포함 |
| **토큰 비용** | $0.02 이하 | 캐싱 적용 후 |

---

## 10. 기대 효과

1. **리포트 퀄리티의 비약적 상승**: AI가 막연하게 "윤리 위반"을 외치는 게 아니라, "신문윤리실천요강 제3조 4항 위반"이라고 콕 집어서 말하게 됩니다.

2. **환각(Hallucination) 방지**: AI에게 검색을 시키는 게 아니라, 우리가 준비한 규범 텍스트 내에서만 찾게 하므로 없는 조항을 지어낼 수 없습니다.

3. **빠짐없는 탐지**: 전체 스캔 방식으로 복합 문제(예: 제목 낚시 + 통계 왜곡)도 놓치지 않습니다.

4. **비용 효율성**: 프롬프트 캐싱으로 API 비용 90% 절감, 탐지된 문제 관련 규범만 주입하여 토큰 최적화.

5. **유연한 확장성**: 새로운 보도 관행 문제가 생기면 checklist.json에 질문만 추가하면 되고, 법이 바뀌면 library.json만 수정하면 됩니다. 코드를 건드릴 필요가 없습니다.

---

## 11. 코딩 에이전트 위임용 체크리스트

```markdown
# IMPLEMENTATION_GUIDE.md

## 구현 순서
1. [ ] data/criteria_checklist.json 작성
2. [ ] data/ethics_library.json 작성
3. [ ] core/criteria_manager.py 구현
4. [ ] core/prompt_builder.py 구현
5. [ ] core/analyzer.py 수정
6. [ ] 테스트 실행

## 핵심 요구사항
- Phase 0: Red Flag 패턴 사전 스크리닝 (API 호출 없음)
- Phase 1: Haiku로 전체 진단 질문 기반 문제 탐지
- Phase 2: Sonnet으로 탐지된 문제 + 관련 규범만 주입하여 상세 리포트
- 프롬프트 캐싱 반드시 적용 (cache_control: ephemeral)
- 규범은 ID로 참조, 원문은 ethics_library.json에서 로드
- AI는 제공된 규범 텍스트만 인용 가능 (환각 방지)

## 테스트 케이스
□ 단일 취재원 의존 기사 → 1-1-1 탐지 확인
□ 반론권 미보장 기사 → 해당 항목 탐지 확인
□ 제목 낚시 기사 → 1-7-3 탐지 확인
□ 복합 문제 기사 → 여러 항목 동시 탐지 확인
□ 규범 인용 → ethics_library.json 원문과 일치 확인
□ Red Flag 패턴 → Phase 0에서 사전 탐지 확인
□ 환각 테스트 → 제공되지 않은 규범 인용 없음 확인
```

---

이 플랜은 **"빠짐없이 탐지 + 정확한 규범 인용 + 환각 방지"**라는 핵심 목표에 집중하며, 전체 스캔 방식과 프롬프트 캐싱, 진단/근거 분리 원칙으로 품질과 비용 효율을 모두 확보하는 구조입니다.
