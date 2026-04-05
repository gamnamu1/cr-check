# Phase γ-2 CLI 지시서 — 규범 인용 스타일링 개선

## 작업 개요

리포트에서 윤리규범 인용 부분의 시각적 스타일을 개선한다.
**백엔드(프롬프트)와 프런트엔드(렌더링) 양쪽을 수정한다.**

### 목표 스타일

규범 인용 문장 예시:

> 〔신문윤리실천요강 제3조 3항〕은 '보도기사에 개인이나 단체를 비판하거나 비방하는 내용이 포함될 때는 상대방에게 해명의 기회를 주고 그 내용을 반영해야 한다'고 규정합니다.

- **〔규범명〕**: 고딕(sans-serif), font-weight: 300, font-size: 90%, 검정(inherit)
- **'인용 내용'**: 명조(serif, 본문과 동일), color: rgb(70, 130, 180)
- **나머지 본문**: 명조(serif), 검정 — 변경 없음

---

## 작업 1: 백엔드 프롬프트 수정

### 파일: `backend/core/report_generator.py`

`_SONNET_SYSTEM_PROMPT` (또는 리포트 생성 시스템 프롬프트)에 아래 지시를 추가한다.

**추가할 프롬프트 내용:**

```
## 규범 인용 표기 규칙

윤리규범을 인용할 때 반드시 아래 형식을 따르세요:

1. 규범 조항명은 〔 〕(꺾은 대괄호)로 감싸세요.
   - 예: 〔신문윤리실천요강 제3조 1항〕, 〔언론윤리헌장 제7조〕, 〔인권보도준칙 제5조 2항〕
   - JEC-7, PCP-3-1 같은 내부 코드는 절대 사용하지 마세요.
   - 반드시 한국어 조항 표현으로 변환하세요.

2. 규범의 실제 내용을 인용할 때는 작은따옴표 ' '로 감싸세요.
   - 예: '보도기사는 사실과 의견을 명확히 구분하여 작성해야 한다'

3. 완성된 인용 형식:
   〔신문윤리실천요강 제3조 1항〕은 '보도기사는 사실과 의견을 명확히 구분하여 작성해야 한다'고 규정합니다.

4. 〔 〕 괄호는 규범 조항명에만 사용하세요. 다른 용도로 사용하지 마세요.
```

**기존 프롬프트에서 제거/수정할 부분:**
- 기존에 "조항 번호 명시 + 핵심 문구 발췌 인용" 지시가 있다면, 위 형식으로 교체
- 이 변경으로 '1번: 조항 번호 표시 통일' 과제도 함께 해결됨

---

## 작업 2: 프런트엔드 렌더링 수정

### 파일: `frontend/components/ResultViewer.tsx`

`highlightEthics` 함수를 아래 로직으로 교체한다.

**교체할 함수: `highlightEthics`**

현재 코드(48~72행 부근)의 `highlightEthics` 함수를 아래 로직으로 교체:

```tsx
const highlightEthics = (text: string) => {
  // 1단계: 〔규범명〕 + 뒤따르는 '인용 내용' 패턴 감지
  //   〔규범명〕은(는) '인용 내용'고/라고 ...
  const citationPattern = /(〔[^〕]+〕)((?:[^']*)'([^']+)')/g;
  
  // 2단계: 〔규범명〕만 단독으로 나오는 경우 (인용 없이 언급만)
  const ruleOnlyPattern = /〔([^〕]+)〕/g;

  // 먼저 전체 인용 패턴(규범명+인용)을 처리
  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;
  let match;

  // Reset regex
  citationPattern.lastIndex = 0;
  
  while ((match = citationPattern.exec(text)) !== null) {
    // 매치 이전의 일반 텍스트
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    
    const ruleName = match[1]; // 〔규범명〕
    const connector = match[2]; // 은(는) '인용내용'
    const quoteContent = match[3]; // 인용 내용 (따옴표 안)
    
    // 규범명 스타일: 고딕, weight 300, 90% size, 검정
    parts.push(
      <span key={`rule-${match.index}`}
        style={{
          fontFamily: '"Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif',
          fontWeight: 300,
          fontSize: '0.9em',
        }}>
        {ruleName.replace(/[〔〕]/g, '')}
      </span>
    );
    
    // 연결어 (은, 는, 이, 가 등) + 따옴표 앞 텍스트
    const beforeQuote = connector.slice(0, connector.indexOf("'"));
    parts.push(beforeQuote);
    
    // 인용 내용 스타일: 명조(본문과 동일), rgb(70,130,180)
    parts.push(
      <span key={`cite-${match.index}`}
        style={{ color: 'rgb(70, 130, 180)' }}
        className="font-serif">
        '{quoteContent}'
      </span>
    );
    
    lastIndex = match.index + match[0].length;
  }
  
  // 남은 텍스트 처리 (〔규범명〕만 단독 등장하는 경우 포함)
  if (lastIndex < text.length) {
    const remaining = text.slice(lastIndex);
    // 단독 규범명 패턴 처리
    const remainParts = remaining.split(/(〔[^〕]+〕)/g);
    remainParts.forEach((part, idx) => {
      if (part.startsWith('〔') && part.endsWith('〕')) {
        parts.push(
          <span key={`rule-solo-${lastIndex}-${idx}`}
            style={{
              fontFamily: '"Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif',
              fontWeight: 300,
              fontSize: '0.9em',
            }}>
            {part.replace(/[〔〕]/g, '')}
          </span>
        );
      } else if (part) {
        // bold 처리 유지
        if (part.includes('**')) {
          const boldParts = part.split(/(\*\*.*?\*\*)/g);
          boldParts.forEach((bp, bIdx) => {
            if (bp.startsWith('**') && bp.endsWith('**')) {
              parts.push(<strong key={`b-${lastIndex}-${idx}-${bIdx}`} className="text-navy-900 font-bold">{bp.slice(2, -2)}</strong>);
            } else if (bp) {
              parts.push(bp);
            }
          });
        } else {
          parts.push(part);
        }
      }
    });
  }
  
  return parts.length > 0 ? parts : [text];
};
```

**핵심 변경 요약:**
- 기존: 정규식으로 규범명 키워드를 감지 → 규범명+인용을 통째로 파란 고딕 span
- 변경: 〔〕 마커로 규범명 감지, '…' 따옴표로 인용 내용 감지 → 각각 다른 스타일 적용


---

## 작업 3: 검증

수정 후 다음을 확인한다:

1. **백엔드 서버 시작** 후 테스트 기사 분석 실행
2. 리포트에서 〔〕 마커가 올바르게 출력되는지 진단 JSON 확인
3. 프런트엔드(localhost:3000)에서 스타일이 의도대로 적용되는지 확인:
   - 규범명: 고딕, 가는 글씨(300), 약간 작게(90%), 검정
   - 인용 내용: 명조, 파란색 rgb(70,130,180)
   - 나머지 본문: 명조, 검정 (변경 없음)
4. TXT 저장 시 〔〕 괄호가 자연스럽게 보이는지 확인
   - TXT에서는 CSS 스타일이 적용되지 않으므로, 〔〕 자체가 시각적 구분 역할

---

## 제약 조건

1. `report_generator.py`의 모델(`SONNET_MODEL`)은 변경하지 않는다 (Sonnet 4.6 유지)
2. `pattern_matcher.py`의 모델은 현재 상태(Sonnet 4.5) 유지
3. 기존 `highlightEthics`의 **bold 처리 로직**은 보존한다
4. `git commit/push/add` 실행 금지
5. 기존 프롬프트의 다른 지시사항(톤, 서술 스타일 등)은 변경하지 않는다
6. 〔〕 마커를 규범명 이외의 용도로 사용하지 않는다

## 참고

- 이 작업으로 Phase γ의 '1번: 조항 번호 표시 통일' 과제도 동시에 해결된다
  (프롬프트에 "JEC-7 같은 내부 코드 대신 한국어 조항 표현 사용" 지시 포함)
- `pattern_matcher.py` 37행은 현재 `claude-sonnet-4-5-20250929`로 설정되어 있어야 함


---

## 작업 4: 추가 개선 사항 (프롬프트 + 프런트엔드)

### 4-1. 메타 정보 간결화 (프롬프트 수정)

**파일:** `backend/core/report_generator.py`

현재 Sonnet이 생성하는 분석 개요(기사 유형, 기사 요소, 편집 구조, 취재 방식, 내용 흐름)의
분량이 과하다. 시민 이용자가 처음 화면을 열었을 때 메타 정보에 압도되면 안 된다.

시스템 프롬프트에서 분석 개요 관련 지시를 찾아 아래 내용을 추가/수정한다:

```
## 분석 개요 작성 규칙

분석 개요의 각 항목(기사 유형, 기사 요소, 편집 구조, 취재 방식, 내용 흐름)은
시민이 "이 기사가 대략 어떤 기사인지" 파악하는 데 필요한 최소한의 정보만 담으세요.

- 각 항목은 1~2문장, 최대 80자 이내로 작성하세요.
- 나열형 설명이 아니라, 핵심만 짚는 한 줄 요약 형태로 쓰세요.
- 구체적인 인물명이나 사건 경위는 본문 리포트에서 다루면 됩니다.
  개요에서는 "익명 취재원 위주, 비판 측 편중"처럼 특징만 짚으세요.
```

### 4-2. 리포트 첫머리 제목 제거 (프롬프트 수정)

**파일:** `backend/core/report_generator.py`

현재 시민 리포트는 `# 시민을 위한 기사 분석 리포트`로 시작하고,
학생 리포트는 `# 학생을 위한 기사 분석 리포트`로 시작한다.
이는 탭 제목("시민을 위한 종합 리포트", "학생을 위한 교육 리포트")과 의미가 겹친다.

시스템 프롬프트에서 3종 리포트 형식 관련 지시를 찾아 아래 내용을 추가한다:

```
## 리포트 시작 규칙

- 3종 리포트 모두, 제목(# 또는 ##)으로 시작하지 마세요.
- 곧바로 본문 첫 문장(도입부)으로 시작하세요.
- 탭 UI에 이미 리포트 유형이 표시되므로, 리포트 안에서 유형을 반복할 필요 없습니다.
```

### 4-3. 중간제목 스타일 변경 (프런트엔드 수정)

**파일:** `frontend/components/ResultViewer.tsx`

현재 H3(### 중간제목)가 `font-serif`(명조)로 렌더링되고 있다.
이를 고딕(sans-serif)으로 바꾸고 크기를 약간 키운다.

H4 렌더링 부분(기존 코드에서 `### `을 처리하는 블록)을 찾아 수정한다:

```tsx
// H3 (### 중간제목)
else if (line.startsWith('### ')) {
  const text = line.replace('### ', '');
  elements.push(
    <h4 key={key++}
      className="text-navy-700 mt-4 mb-2 font-semibold"
      style={{
        fontFamily: '"Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif',
        fontSize: '1.1em',
      }}>
      {text}
    </h4>
  );
}
```

핵심 변경:
- `font-serif` → 고딕(Pretendard) sans-serif
- `text-lg`(기존) → `fontSize: '1.1em'` (본문 대비 110%)
- 기존의 isTarget 분기 제거 — 모든 중간제목을 동일하게 처리

### 4-4. 학생 리포트 톤 재설계 (프롬프트 수정)

**파일:** `backend/core/report_generator.py`

현재 학생 리포트의 톤 지시(### 4. 3종 리포트 톤 차이 섹션)에서
student 부분을 아래로 교체한다:

**현재:**
```
- **student** (학생용): "여러분"이라는 호칭. 일상적 비유와 질문 형식으로
  비판적 읽기를 유도. 이모지 적절히 활용. 단, 딱딱한 교과서 설명이 아닌,
  함께 탐구하는 느낌.
```

**교체:**
```
- **student** (학생용): 초등학교 4~5학년이 이해할 수 있는 눈높이로 작성.
  "여러분"이라는 호칭, 해요체("~해요", "~이에요", "~거예요", "~까요?")를
  일관되게 사용. "~합니다", "~됩니다", "~입니다" 같은 격식체는 쓰지 마세요.
  윤리규범을 인용할 때도 "~라고 정해놓았어요", "~라고 말하고 있어요"처럼
  해요체를 유지하세요. 어려운 개념은 일상적 비유로 풀어 설명하고,
  질문 형식("어떻게 생각해요?", "한번 찾아볼까요?")으로 참여를 유도하세요.
  이모지를 적절히 활용하되, 내용의 핵심을 흐리지 않을 정도로만 사용하세요.
```

---

## 제약 조건 (추가)

- 기존 phase_gamma2_citation_style.md의 모든 제약 조건 유지
- 메타 정보 간결화는 프롬프트 수정이므로, 수정 후 테스트 기사 실행으로 확인
- 중간제목 스타일 변경 시, H1(#)과 H2(##) 스타일은 건드리지 않는다
- 학생 리포트 톤 변경은 student 섹션만 수정, comprehensive/journalist 톤은 유지
