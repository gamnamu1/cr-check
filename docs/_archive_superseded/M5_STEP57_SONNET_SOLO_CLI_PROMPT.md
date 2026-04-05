# M5 STEP 57-S — Sonnet Solo 1-Call 재설계 CLI 프롬프트

> 작성일: 2026-03-29
> 작성: Claude.ai (1차 감리)
> 목적: 2-Call 파이프라인 실패 후, 게이트 완전 제거 + Sonnet 단독 1-Call로 전환

---

## CLI 작업 내용 프롬프트

```

⚠️ 이 STEP(57-S)만 수행하고, 완료 후 결과를 보고하고 멈춰줘(STOP).
다음 STEP(58: Claude.ai 감리)은 건너뛰지 말고, Gamnamu 지시 전까지 다음 작업에 착수하지 말아줘.

■ 배경

M5에서 두 가지 아키텍처를 시도했으나 모두 실패:
1. 1-Call + 1단계 이진 게이트 → TP를 양질로 오판 (B2-10), TN 보호 실패 (E-19)
2. 2-Call (Haiku 대분류→Sonnet 소분류) → Haiku가 대분류조차 정반대로 판단

3자 감리 협의(Claude.ai + Antigravity + Manus) 최종 합의:
- "게이트" 개념 자체의 구조적 한계 확인
- Sonnet 단독 1-Call + 강제 CoT + Devil's Advocate + few-shot 9건으로 재설계
- TN 보호를 일반 문구가 아닌 few-shot TN 예시 내부에서만 처리

■ 사전 숙지 (Plan Mode로 먼저 읽을 것)
1. docs/SESSION_CONTEXT_2026-03-29_v16.md
2. docs/CR_CHECK_M5_PLAYBOOK.md
3. backend/core/pattern_matcher.py — 현재 코드 전체 (deprecated 1-Call + 2-Call 포함)
4. CLAUDE.md

■ 핵심 설계 원칙 — 왜 이렇게 바꾸는가

1. 게이트 제거: "양질이면 즉시 [] 반환"하는 이진 판정을 완전히 없앤다.
   모든 기사가 패턴 매칭 단계까지 도달한다.

2. Devil's Advocate CoT: overall_assessment에서 반드시 찬반 양론을 모두 기술한 뒤
   최종 판단을 내리게 한다. 단일 관점 매몰을 방지.

3. TN 보호는 few-shot 예시에서만: 일반 문구("탐사보도는 양질", "팩트 기반 비판은 
   편향 아님")를 프롬프트 본문에서 제거하고, few-shot TN 예시의 reasoning 내부에서만 
   "왜 이 기사가 양질인지"를 설명한다.

4. 출력 형식 변경: 기존 JSON 배열 [] → 객체 { overall_assessment, detections }

■ 작업: _SONNET_SOLO_PROMPT 신규 작성 + match_patterns_solo() 구현

=== 새 프롬프트: _SONNET_SOLO_PROMPT ===

아래 구조로 작성하라. 프롬프트 전체를 그대로 사용하되,
few-shot 예시는 기존 _HAIKU_SYSTEM_PROMPT의 예시 1~9를 기반으로
overall_assessment를 추가하여 변환한다.

--- 프롬프트 시작 ---

당신은 한국 뉴스 기사의 보도 품질을 평가하는 전문 분석가입니다.

기사를 읽고, 아래 '패턴 목록'과 대조하여 문제적 보도관행 패턴을 식별하세요.

## 분석 절차

1. **overall_assessment 작성 (필수, 반드시 먼저)**:
   아래 두 가지를 모두 기술하세요:
   (가) 이 기사가 양질의 보도일 수 있는 근거 — 어떤 점에서 저널리즘 기준을 충족하는가
   (나) 이 기사에 윤리적 문제가 있을 수 있는 근거 — 어떤 점에서 보도관행 기준을 위반하는가
   둘 다 기술한 후, 어느 쪽이 더 강한지 종합 판단하세요.
   양질의 보도라면 "(가)의 근거가 더 강하다"고 명시하고 detections를 빈 배열로 두세요.
   
2. **detections 작성**:
   overall_assessment에서 (나)가 더 강하다고 판단한 경우에만,
   기사에서 실제로 확인되는 문제 패턴을 아래 형식으로 기술하세요.

## 핵심 원칙: 정밀도 우선
- 확신이 없으면 선택하지 마세요. 누락보다 오탐이 더 해롭습니다.
- 기사에서 해당 문제를 보여주는 **구체적 문장이나 표현을 특정할 수 없다면** 
  그 패턴을 선택하지 마세요.

## ★ 후보 패턴 활용
★ 표시된 패턴은 벡터 검색으로 사전 선별된 유력 후보입니다.
- ★ 패턴을 먼저 우선적으로 검토하세요.
- 단, ★ 표시가 없는 패턴도 기사에 명확히 해당하면 동등하게 선택하세요.

## 기사 길이별 가이드
- 200자 미만: 최대 1~2개
- 200~500자: 최대 2~3개
- 500~2000자: 최대 3~4개
- 2000자 이상: 최대 4~5개. 근거가 매우 명확한 경우에만.
- 같은 패턴을 여러 번 선택하지 마세요.

## 자주 혼동되는 패턴 쌍
- **1-1-1 vs 1-1-4**: 팩트 자체가 틀렸으면 1-1-1. 팩트는 맞지만 사실과 의견을 섞었으면 1-1-4.
- **1-3-1 vs 1-3-2**: 반론 없이 한쪽만 인용했으면 1-3-1. 양쪽을 언급했지만 틀이 편향적이면 1-3-2.
- **1-3-1 vs 1-3-4**: 반론 없이 전달했으면 1-3-1. 배경·맥락 생략으로 판단 정보 부족이면 1-3-4.
- **1-7-2 vs 1-7-5**: 이념적 틀로 규정(빨갱이, 수구)이면 1-7-2. 감정 자극 과장(충격, 발칵)이면 1-7-5.
- **1-7-3 vs 1-7-4**: 본문이 과장/왜곡이면 1-7-3. 본문은 정상이고 제목만 과장이면 1-7-4.

## 기타 규칙
1. 기사에서 **실제로 확인되는** 문제만 선택하세요.
2. "(텍스트 분석 대상 아님)"으로 표시된 패턴은 선택하지 마세요.
3. 유사 패턴 중 더 정확한 쪽을 선택하세요.
4. 문제가 발견되지 않으면 detections를 빈 배열 []로 두세요.
5. 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.

## 참고 예시

(⚠️ 기존 _HAIKU_SYSTEM_PROMPT의 예시 1~9를 아래 형식으로 변환하여 삽입하라.
 기존 예시의 기사 제목, 요약, 올바른 분석 JSON은 그대로 유지하되,
 overall_assessment를 추가하고 전체를 객체로 감싼다.
 
 TP 예시: overall_assessment에 (가) 양질 근거 + (나) 문제 근거를 모두 기술.
          "(나)가 더 강하다"고 명시한 뒤 detections에 기존 분석 JSON 삽입.
 TN 예시: overall_assessment에 (가) 양질 근거 + (나) 오탐 위험을 모두 기술.
          "(가)가 더 강하다"고 명시한 뒤 detections를 빈 배열로.)

### 변환 예시 — 기존 예시 1 (TP)을 새 형식으로:

예시 1 — [TP] 1-1 진실성: 데이터 오용
기사 제목: "최근 한달 확진 10만명당 확진률 80%↑, 치명률 美·브라질보다 높아… 'K방역의 치욕'"
기사 요약: (기존과 동일)
올바른 분석:
```json
{
  "overall_assessment": "(가) 코로나19 관련 국가 간 비교를 시도한 시의적절한 보도이며, 구체적 수치를 제시하고 있다. (나) 그러나 특정 두 시점의 증가율만으로 방역 실태를 비교하는 것은 통계적으로 불충분하며, 절대 수치(인구 대비 확진자 수)를 의도적으로 배제한 채 결론을 도출했다. 종합: (나)가 더 강하다. 데이터 선택적 제시와 통계 오용이 확인된다.",
  "detections": [
    {
      "matched_text": "10만 명당 확진자 수가 80% 늘어 세계 최고 수준의 증가율을 기록",
      "reasoning": "(기존 reasoning 그대로)",
      "severity": "high",
      "pattern_code": "1-1-5"
    }
  ]
}
```

### 변환 예시 — 기존 예시 8 (TN)을 새 형식으로:

예시 8 — [TN] 탐사보도
기사 제목: "'감금·성폭행'…목포 '옛 동명원' 피해자들의 증언"
기사 요약: (기존과 동일)
올바른 분석:
```json
{
  "overall_assessment": "(가) 피해자 증언과 문서 증거에 기반한 탐사보도로 공익적 가치가 높다. 이달의 기자상 수상작으로 저널리즘 기준을 충족한다. (나) '감금', '성폭행' 등 강한 표현이 1-7-4(자극적 표현)로 오탐될 위험이 있고, 피해자 관점 중심 서술이 1-3-1(관점 다양성 부족)으로 보일 수 있다. 종합: (가)가 압도적으로 강하다. 표현의 강도는 사건의 심각성에 부합하며, 피해자 관점 중심은 인권 탐사보도의 정당한 방법론이다.",
  "detections": []
}
```

(나머지 예시 2~7, 9도 동일한 방식으로 변환할 것.
 기존 _HAIKU_SYSTEM_PROMPT의 예시를 기반으로 하되,
 overall_assessment에 Devil's Advocate 형식을 적용.)

## 출력 형식
반드시 아래 JSON 형식으로만 응답하라. 다른 텍스트를 포함하지 마라.
```json
{
  "overall_assessment": "(가) 양질 근거. (나) 문제 근거. 종합: (가)/(나)가 더 강하다.",
  "detections": [
    {
      "matched_text": "문제가 되는 기사 원문 인용 (1~2문장)",
      "reasoning": "왜 문제이고 어떤 기준을 위반했는지 (1~2문장)",
      "severity": "high|medium|low",
      "pattern_code": "1-1-1"
    }
  ]
}
```

--- 프롬프트 끝 ---

=== 코드 변경 ===

### pattern_matcher.py 변경사항

1. **새 프롬프트 상수**: _SONNET_SOLO_PROMPT (위 내용)
   - few-shot 9건은 기존 _HAIKU_SYSTEM_PROMPT의 예시를 변환
   - 각 예시에 overall_assessment (가)/(나) 형식 추가
   - TN 보호 일반 문구("탐사보도는 양질", "팩트 기반 비판은 편향 아님")는 
     프롬프트 본문에 넣지 말 것. TN 예시 내부에서만 기술.

2. **새 함수**: match_patterns_solo()
   시그니처:
   def match_patterns_solo(
       chunks: list[str],
       article_text: str,
       threshold: Optional[float] = None,
   ) -> PatternMatchResult:
   
   흐름:
   (1) 패턴 카탈로그 로드
   (2) 청크 임베딩 + 벡터 검색 (기존과 동일)
   (3) Sonnet 1-Call 호출:
       - 시스템 프롬프트: _SONNET_SOLO_PROMPT
       - 유저 메시지: 패턴 목록(★ 마크 포함) + 기사 전문
       - 모델: claude-sonnet-4-6
       - temperature: 0.0
       - max_tokens: 2048
   (4) 응답 파싱: _parse_solo_response()
   (5) 밸리데이션 (기존 validate_pattern_codes 재사용)
   (6) PatternMatchResult 반환
       - suspect_result에 SuspectResult(overall_assessment=총평, suspect_categories=[]) 저장
         (벤치마크 호환을 위해. solo 모드에서 suspect_categories는 항상 빈 배열)

3. **새 파싱 함수**: _parse_solo_response(text: str) -> tuple[str, list[HaikuDetection]]
   반환: (overall_assessment, detections)
   
   파싱 로직:
   - 마크다운 코드블록 제거
   - JSON 객체 추출 ({ ... })
   - overall_assessment 필드 추출
   - detections 배열 추출 → 기존 HaikuDetection으로 변환
   - 중복 pattern_code 제거 (seen_codes)
   - 파싱 실패 시 graceful fallback: ("", [])
   
   ⚠️ 핵심: 기존 1-Call은 배열 [] 파싱, 2-Call도 배열 파싱이었음.
      이번에는 객체 {} 파싱이다. { 와 } 사이에서 JSON을 추출할 것.
      detections가 빈 배열인 경우도 정상 처리해야 한다.

4. **패턴 목록 구성**:
   기존 match_patterns()의 방식과 동일하게 구성.
   _load_pattern_catalog() + ★ 마크 적용.
   전체 28개 패턴 + 벡터 후보 ★.
   동적 필터링 없음 (2-Call에서는 의심 대분류만 필터링했으나, solo는 전체).

5. **기존 코드 보존**:
   - match_patterns(): [DEPRECATED] 1-Call (M4)
   - match_patterns_2call(): [DEPRECATED] 2-Call (M5 시도 1)
   - 새로: match_patterns_solo(): Sonnet Solo 1-Call (M5 시도 2)
   - 삭제하지 말 것. 비교 실험용 보존.

### pipeline.py 변경사항

analyze_article()에서:
- match_patterns_2call → match_patterns_solo 로 교체
- import 수정

### benchmark_pipeline_v3.py 변경사항

1. pipeline_path에 "sonnet_solo" 추가:
   - detections 있음 → "sonnet_solo_detect"
   - detections 없음 → "sonnet_solo_empty"

2. overall_assessment 기록:
   - suspect_result.overall_assessment에서 추출 (기존 2-Call과 동일 경로)

3. Haiku 관련 지표:
   - Haiku Suspect Accuracy → N/A 또는 제거 (Haiku 미호출)
   - Haiku TN Pass Rate → "Solo TN Pass Rate"로 변경:
     detections == [] 인 TN 건의 비율

■ 주의사항

1. ⚠️ 기존 코드(1-Call, 2-Call)를 삭제하지 마라. deprecated 처리하라.
2. ⚠️ KJA 접두어 절대 금지. JCE가 올바른 접두어.
3. ⚠️ few-shot 예시 변환 시 기존 reasoning은 그대로 유지.
   overall_assessment만 새로 추가 (Devil's Advocate 형식).
4. ⚠️ TN 보호 일반 문구를 프롬프트 본문에 넣지 마라.
   "탐사보도는 양질", "팩트 기반 비판은 편향 아님" 등의 문구는
   few-shot TN 예시의 overall_assessment 내부에서만 기술.
5. ⚠️ 출력 형식이 JSON 객체 {}임에 주의. 배열 []이 아님.
   .format() 사용 시 중괄호 이스케이프 ({{ }}) 필수.
6. 프롬프트 전체 토큰 추정치를 보고할 것 (기존 대비 증감).
7. 변경 전 반드시 git diff로 변경 범위 확인.
8. 1건 동작 확인 테스트(A-06 등)를 실행하여 에러 없이 완주하는지 확인.
   JSON 파싱이 정상 작동하는지 특히 확인 (객체 파싱).

■ 완료 기준
- [ ] _SONNET_SOLO_PROMPT 신규 작성 (few-shot 9건 변환 포함)
- [ ] match_patterns_solo() 구현
- [ ] _parse_solo_response() 구현 (객체 파싱 + overall_assessment 추출)
- [ ] pipeline.py → match_patterns_solo() 전환
- [ ] benchmark_pipeline_v3.py → pipeline_path "sonnet_solo_*" 추가
- [ ] 기존 함수 deprecated 보존 (1-Call, 2-Call 모두)
- [ ] 1건 동작 확인 테스트 통과
- [ ] 프롬프트 토큰 추정치 보고
- [ ] git diff 변경 범위 보고
```

---

## 참고: 이전 시도 대비 핵심 차이점

| 요소 | M4 1-Call | M5 2-Call | M5 Sonnet Solo (이번) |
|------|-----------|----------|----------------------|
| 게이트 | ✅ 1단계 이진 | ✅ Haiku 이진 | ❌ 없음 |
| 모델 | Sonnet 1회 | Haiku+Sonnet | Sonnet 1회 |
| CoT | ❌ | ✅ (Haiku) | ✅ Devil's Advocate |
| Few-shot | 2건→9건 | 9건 (Haiku) | 9건 (Sonnet) |
| TN 보호 | 일반 문구 | 일반 문구 | few-shot 내부만 |
| 패턴 목록 | 전체 28개 | 동적 필터링 | 전체 28개 |
| 출력 형식 | 배열 [] | 배열 [] | 객체 {assessment, detections} |

핵심: 이전 시도들과 달리 **어떤 기사도 패턴 매칭 기회를 잃지 않으며**,
Sonnet이 찬반 양론을 강제로 검토한 뒤 최종 판단을 내린다.
