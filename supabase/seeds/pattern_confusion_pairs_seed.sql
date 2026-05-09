-- STEP 5-B 시드: 5개 v3 leaf 혼동 쌍.
-- distinction_guide는 dollar-quoted string으로 작성하여 작은따옴표 이스케이프를 피함.
-- ON CONFLICT (code_a, code_b)는 UNIQUE 제약을 타겟으로 한 멱등 INSERT.

-- 쌍 1: 1-1-e vs 1-4-d
INSERT INTO public.pattern_confusion_pairs (code_a, code_b, distinction_guide)
VALUES (
  '1-1-e',
  '1-4-d',
  $guide$
취재원 주장의 사실화(1-1-e) vs 의견의 사실화 - 기자(1-4-d):
단정적으로 서술된 내용의 원 출처가 누구인지 먼저 확인하라.
- 1-1-e: 취재원(인물·기관)의 발언·주장·평가를 검증 없이 사실로 제시한 경우
  (예: '라고 주장했다', '라고 비판했다'는 취재원 발언을 기자가 사실로 흡수하여 단정 서술)
- 1-4-d: 취재원 발언 없이 기자 본인의 가치 판단·해석을 사실 서술어 자리에 배치한 경우
  (예: '졸속으로 처리됐다', '무책임한 행태', '꼼수')
판별 기준: 단정의 주인이 취재원이면 1-1-e, 기자이면 1-4-d.
양쪽 요소가 혼재할 때는 더 구체적 근거가 있는 쪽을 선택하라.
$guide$
) ON CONFLICT (code_a, code_b) DO NOTHING;

-- 쌍 2: 3-1-b vs 3-2-b
INSERT INTO public.pattern_confusion_pairs (code_a, code_b, distinction_guide)
VALUES (
  '3-1-b',
  '3-2-b',
  $guide$
편향된 취재원 구성(3-1-b) vs 선별적 사실 제시(3-2-b):
기사에 반대 입장 취재원이 실제로 등장하는지 먼저 확인하라.
- 3-1-b: 반대 의견 취재원이 완전히 배제되거나 형식적 한 줄에 그쳐 실질적 균형이 없는 경우
- 3-2-b: 반대 취재원이 형식적으로 등장하지만, 특정 방향에 유리한 사실만 선별·부각하고
  불리한 맥락을 의도적으로 누락한 경우
판별 기준: 취재원 존재 여부가 문제이면 3-1-b, 정보 선택의 편향이 문제이면 3-2-b.
$guide$
) ON CONFLICT (code_a, code_b) DO NOTHING;

-- 쌍 3: 3-1-a vs 3-4-a
INSERT INTO public.pattern_confusion_pairs (code_a, code_b, distinction_guide)
VALUES (
  '3-1-a',
  '3-4-a',
  $guide$
단일 관점 편향(3-1-a) vs 이분법 대결 구도(3-4-a):
기사에 반대 입장이나 다른 진영이 실제로 등장하는지 먼저 확인하라.
- 3-1-a: 복합·논쟁적 사안에서 반대 의견이나 다른 관점이 기사에서 완전히 누락된 경우
- 3-4-a: 양측 입장이 모두 등장하지만 'A 진영 vs B 진영' 이분법으로 단순화하여
  중도적 목소리와 다층적 맥락을 소거한 경우
  (예: '강 대 강', '정면충돌', '편 가르기', '정부 vs 의사')
판별 기준: 관점 자체가 없으면 3-1-a, 관점은 있지만 이분법 대결로 납작해졌으면 3-4-a.
$guide$
) ON CONFLICT (code_a, code_b) DO NOTHING;

-- 쌍 4: 3-2-a vs 6-4-a
INSERT INTO public.pattern_confusion_pairs (code_a, code_b, distinction_guide)
VALUES (
  '3-2-a',
  '6-4-a',
  $guide$
이념·정파적 프레이밍(3-2-a) vs 낚시성 자극 어휘(6-4-a):
자극적인 어휘가 발견됐을 때 그 어휘의 사용 목적을 먼저 확인하라.
- 3-2-a: 특정 인물·집단·사안을 이념·정파 잣대로 규정하고 낙인찍는 어휘가 문제인 경우
  (예: '빨갱이', '수구', '좌파 포퓰리즘', '친중 매국노', '종북')
- 6-4-a: 이념 맥락과 무관하게 독자의 말초적 감정과 클릭을 유도하는 어휘 남발이 문제인 경우
  (예: '충격', '경악', '발칵', '폭탄 선언', '대반전')
판별 기준: 이념 진영 규정이 목적이면 3-2-a, 감각적 클릭 유도가 목적이면 6-4-a.
두 어휘가 공존할 때는 기사의 주된 윤리 문제가 이념 낙인찍기인지 선정적 어휘 남발인지로 판단하라.
둘 다 명확히 해당하면 각각 별도로 선택하되 근거를 분리하여 서술하라.
$guide$
) ON CONFLICT (code_a, code_b) DO NOTHING;

-- 쌍 5: 6-3-a vs 6-2-c
INSERT INTO public.pattern_confusion_pairs (code_a, code_b, distinction_guide)
VALUES (
  '6-3-a',
  '6-2-c',
  $guide$
과장된 표현(6-3-a) vs 제목-본문 불일치·침소봉대(6-2-c):
과장이나 극단적 표현이 보이면 제목만 보지 말고 본문을 먼저 읽어라.
- 6-3-a: 기사 본문 전반에 걸쳐 극단적 수식어가 반복 사용되어 사실 자체가 부풀려진 경우
  (예: '사상 최악', '초유의 사태', '전례 없는')
- 6-2-c: 본문은 비교적 평이한데 제목에서만 부차적 내용을 핵심인 것처럼 부각하여
  중요도를 왜곡한 경우
  (예: 본문 말미 한 줄짜리 발언을 제목에서 '전면전 선포'로 키움)
판별 기준: 과장이 본문 전반이면 6-3-a, 제목에 집중된 비중 왜곡이면 6-2-c.
제목에 극단적 어휘가 있더라도 본문이 평이하다면 6-2-c로 판단하라.
$guide$
) ON CONFLICT (code_a, code_b) DO NOTHING;
