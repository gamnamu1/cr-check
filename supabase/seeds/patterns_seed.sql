-- ============================================================
-- patterns_seed.sql
-- STEP 2-3: 107개 패턴 INSERT
-- ============================================================
-- 작성일: 2026-05-02
-- 작성자: Claude Code CLI
-- 입력 문서:
--   - docs/_scratch/step1_output_v3.md (107 leaf 코드 체계)
--   - docs/STEP0A_PATTERN_DECISIONS_v1.0.md §1 카테고리, §6 어휘 코퍼스
--   - docs/current-criteria_v3_active.md (description 원본)
-- 적용 대상: public.patterns
-- 형식: ON CONFLICT (code) DO NOTHING
-- ============================================================

-- 1-1-a: 복수 취재원 원칙 위반 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-a',
  '복수 취재원 원칙 위반',
  '공익에 중대한 영향을 미치는 사안에 대해 최소 둘 이상의 독립적인 취재원에게 사실을 확인받지 않고 단일 취재원에 의존해 보도하는 경우. 일명 ''투 소스 룰(The Two-Source Rule)'' 위반에 해당하며, 정치 스캔들이나 비위 폭로 같은 중대 사안에서 단일 출처로 보도하면 정보 검증이 불가능해진다.',
  '단독 취재원, 단일 출처, 한 명의 관계자, 정보를 입수, 본지 단독 입수, 한 정통 소식통',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-b: 반론권 미보장 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-b',
  '반론권 미보장',
  '비판받거나 의혹이 제기된 당사자에게 해명·반론 기회를 충분히 제공하지 않고 일방의 주장만 전달하는 경우. 교차 검증의 핵심 절차를 생략한 것으로, 특히 피의자·피고인 보도에서 수사기관 발표만 일방 보도하면 무죄추정 원칙을 침해한다. (예: ''연락이 닿지 않았다'' 한 줄로 처리하여 실질적 반론 기회 박탈)',
  '연락을 시도했으나 닿지 않았다, 입장을 밝히지 않았다, 묵묵부답이었다, 해명을 거부했다, 답변을 들을 수 없었다',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-c: 익명 단일 취재원 의존 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-c',
  '익명 단일 취재원 의존',
  '''정부 고위 관계자'', ''사정 당국자'' 같이 익명의 단일 취재원에게 의존하여 중요 사안을 보도하는 행위. 익명 출처 자체가 문제는 아니지만, 익명 단일 출처만으로는 진위 검증 방법이 없으며 특정 세력의 정보 전쟁 도구로 악용될 위험이 크다.',
  '정부 고위 관계자에 따르면, 사정당국 핵심 관계자, 여권 핵심 관계자, 한 소식통은, 청와대 핵심 참모, 복수의 당내 소식통',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-d: 폭로성 발언 무검증 인용 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-d',
  '폭로성 발언 무검증 인용',
  '정치인·기업가 등 주요 취재원이 제3자에 대해 폭로하거나 비판할 때, 그 주장의 진위·배경을 확인하지 않고 발언 내용 자체를 기사 핵심으로 삼는 경우. ''취재원이 그렇게 말했다''는 사실과 ''말한 내용 자체가 사실''은 별개임에도 둘을 혼동하여, 폭로성 발언을 따옴표로 처리해 헤드라인까지 그대로 사용한다.',
  '[단독], 직격탄을 날렸다, 충격 폭로, 작심 비판, 폭로했다, 제기했다, 의혹을 던졌다',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-e: 취재원 주장의 사실화 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-e',
  '취재원 주장의 사실화',
  '취재원의 ''주장·의견·전망·평가''를 마치 객관적으로 확인된 사실인 것처럼 제시하는 경우. 주장과 사실의 경계를 모호하게 만들어 독자가 검증되지 않은 정보를 사실로 오인하게 한다. 기자 의견 사실화(1-4)와 달리 여기서는 ''취재원 주장''을 사실화한다는 점이 다르다.',
  '라고 비판했다, 라고 평가했다, 라고 주장했다, 라고 지적했다, 라고 강조했다, 라고 지목했다',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-f: 따옴표 처리 책임 회피 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-f',
  '따옴표 처리 책임 회피',
  '논란이 될 만한 발언이나 검증되지 않은 주장을 직접 인용구로 처리하여 제목·본문에 그대로 사용함으로써, 형식적으로 ''취재원이 한 말을 전달했을 뿐''이라는 명분으로 보도 책임을 회피하는 경우. 따옴표는 검증 책임을 면제해주는 면죄부가 아니며 오히려 발언에 권위와 신뢰를 부여하므로 더 큰 책임이 따른다.',
  '직접 인용 헤드라인, 따옴표 처리, 발언만 옮겼다, 발언을 그대로 전달, 인용했을 뿐, 큰따옴표',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-g: 통계·연구 출처 미공개 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-g',
  '통계·연구 출처 미공개',
  '통계·연구 결과·전문가 의견을 인용하면서 출처를 구체적으로 밝히지 않아 독자가 정보의 신뢰도를 판단하거나 직접 확인할 수 없게 만드는 행위. ''최근 연구에서…'', ''조사 결과에 따르면…'' 같은 모호한 표현으로 출처를 얼버무리는 것은 기자가 정보의 객관성 입증 책임을 회피하는 것이다. 취재원 신원 모호 표기(2-1-a)와 달리, 본 항목은 데이터·연구 인용 시 출처 누락에 한정한다.',
  '최근 연구에 따르면, 한 연구결과에 따르면, 자체 설문조사 결과, 전문가들에 따르면, 조사 결과에 따르면, 업계에 따르면, 관련 업계에 따르면',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-h: 온라인·SNS 무검증 인용 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-h',
  '온라인·SNS 무검증 인용',
  '검증되지 않은 온라인 커뮤니티 게시글, SNS 등을 마치 객관적이고 신뢰할 만한 정보인 것처럼 인용하는 경우. 1-2-e와 개념상 중복되지만 본 항목은 본문 어휘 신호(''온라인 커뮤니티에 따르면'', ''네티즌들은 발칵'' 등)에 의한 vector 감지에 초점을 맞춘다.',
  '온라인 커뮤니티에 따르면, 블라인드 게시글을 보면, 네티즌들은 발칵, SNS에 올라온 글에 따르면, 누리꾼 반응, 익명 게시판',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-i: 사설 정보지(지라시) 의존 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-i',
  '사설 정보지(지라시) 의존',
  '사설정보지(일명 ''지라시'') 내용을 검증 없이 보도하거나 이를 단초로 무리하게 의혹을 제기하는 행위. 정보지는 출처가 불분명하고 특정 세력의 정치적·경제적 의도가 개입될 수 있어 명예훼손 위험이 크다. 1-2-f와 개념 중복이나 본 항목은 어휘 신호(''증권가 정보지에 따르면'', ''지라시'' 등) 감지에 초점.',
  '증권가 정보지에 따르면, 지라시, 정치권에 떠도는 소문, 사설 정보지에 따르면, 풍문에 따르면',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-1-j: 맥락 정보 생략·체리피킹 [사실 검증과 출처 > 사실 검증 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-1-j',
  '맥락 정보 생략·체리피킹',
  '취재원이나 원문 자료의 전체 맥락을 숨기고, 기자 의도에 맞는 특정 문장이나 단어만 잘라내어(체리피킹) 원작자의 의도를 왜곡하는 행위. 통계·연구 인용 시에도 신뢰도 판단에 필수적인 맥락 정보(조사 방법, 표본 크기, 시점, 한계 등)를 제공하지 않는 경우. 6-3-d 인용 비틀기와 혼동 쌍이며, 1-1-j는 출처·인용 정보의 맥락 삭제, 6-3-d는 표현·문체 층위의 인용 왜곡을 다룬다.',
  '발언 일부, 일부만 발췌, 전체 맥락에서 빠진, 가정 부분 삭제, 조사 한계 미고지, 표본 크기 미공개, 오차범위 미고지',
  '사실 검증과 출처',
  '사실 검증 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-2-a: 보도자료·공식 발표 받아쓰기 [사실 검증과 출처 > 이차 자료 의존]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-2-a',
  '보도자료·공식 발표 받아쓰기',
  '정부·기업·기관의 보도자료나 공식 발표를 추가 취재나 비판적 검증 없이 그대로 기사화하는 경우. 발표 주체가 의도적으로 가공한 정보를 여과 없이 전달함으로써 언론을 감시자가 아닌 해당 기관의 ''홍보 대행사''로 전락시킨다. 본문 단독 감지가 어려워 I-트랙으로 비활성화.',
  '보도자료에 따르면, 정부 발표 자료, 기관 보도자료, 관계 부처 발표, 회사 보도자료에 따르면, 발표 내용을 종합하면',
  '사실 검증과 출처',
  '이차 자료 의존',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-2-b: 국내 언론사 기사 재가공 [사실 검증과 출처 > 이차 자료 의존]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-2-b',
  '국내 언론사 기사 재가공',
  '다른 언론사 보도를 독자적인 사실 확인 없이 자사 기사로 재작성하거나 짜깁기하는 행위. 원 보도의 오류·편향이 검증 없이 확산되며 동일한 출처와 관점의 기사들이 양산되어 언론 다양성을 훼손한다. 본문 단독 감지가 어려워 I-트랙.',
  '다른 매체 보도에 따르면, 타사 기사를 종합하면, 매체 보도를 종합하면, 인용 기사',
  '사실 검증과 출처',
  '이차 자료 의존',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-2-c: 통신사 기사 무비판적 전재 [사실 검증과 출처 > 이차 자료 의존]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-2-c',
  '통신사 기사 무비판적 전재',
  '연합뉴스 등 통신사가 제공하는 기사를 별도 검증·추가 취재 없이 자사 기사로 그대로 싣는 관행. 통신사 의존도가 매우 높아 통신사의 편향이 전국 언론으로 동시 확산된다. 본문 단독 감지가 어려워 I-트랙.',
  '연합뉴스에 따르면, 통신사 보도에 따르면, 통신 기사 인용',
  '사실 검증과 출처',
  '이차 자료 의존',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-2-d: 해외 언론 단순 번역 보도 [사실 검증과 출처 > 이차 자료 의존]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-2-d',
  '해외 언론 단순 번역 보도',
  '외신 기사를 원문 확인이나 국내 전문가 취재 없이 단순 번역 보도하거나, 특파원 바이라인을 달아 마치 독자 취재인 것처럼 위장하는 행위. 원문 맥락·뉘앙스 소실 및 번역 과정의 오류·왜곡이 그대로 전파된다. 본문 단독 감지가 어려워 I-트랙.',
  '외신은 전했다, 로이터통신에 따르면, AFP에 따르면, BBC에 따르면, 외신을 종합하면, 외신 보도에 따르면',
  '사실 검증과 출처',
  '이차 자료 의존',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-2-e: 온라인 정보 무검증 인용 [사실 검증과 출처 > 이차 자료 의존]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-2-e',
  '온라인 정보 무검증 인용',
  '온라인 커뮤니티·SNS·블로그 등에 게시된 검증되지 않은 정보를 사실 확인 절차 없이 기사화하는 행위. 익명 주장·루머·편집된 이미지·영상을 보도함으로써 신뢰성을 부여하고 가짜뉴스 확산에 동조한다. 본 항목은 이차 자료 의존 측면이며 1-1-h와 개념 중복(I-트랙).',
  '온라인 커뮤니티 글, SNS 게시글에 따르면, 익명 게시글, 블로그 글, 댓글창에서',
  '사실 검증과 출처',
  '이차 자료 의존',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-2-f: 사설 정보지 의존(이차자료 측면) [사실 검증과 출처 > 이차 자료 의존]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-2-f',
  '사설 정보지 의존(이차자료 측면)',
  '사설 정보지(지라시) 내용을 이차 자료로서 검증 없이 보도하는 행위. 1-1-i와 개념 중복이나, 본 항목은 이차 자료 의존 차원에서 비활성화 분류된 I-트랙.',
  '지라시, 사설 정보지, 정보지에 따르면, 일명 지라시',
  '사실 검증과 출처',
  '이차 자료 의존',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-3-a: 부실한 정정 보도 [사실 검증과 출처 > 오보 관리 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-3-a',
  '부실한 정정 보도',
  '오보·사실 오류가 확인되었음에도 인정에 인색하거나, 보도로 생긴 피해 크기에 비해 턱없이 축소된 형식으로 정정하는 행위. 1면 톱기사 오보를 며칠 뒤 지면 귀퉁이에 단신 처리하는 등 ''비례성 원칙''을 위반한다. 외부 비교 필요로 본문 단독 감지 불가, I-트랙.',
  '정정보도, 알려드립니다, 바로잡습니다, 유감을 표한다, 취재원의 착오로',
  '사실 검증과 출처',
  '오보 관리 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-3'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-3-b: 온라인 기사 몰래 수정 [사실 검증과 출처 > 오보 관리 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-3-b',
  '온라인 기사 몰래 수정',
  '온라인 환경에서 기사를 쉽게 수정할 수 있다는 점을 악용하여, 오류 발견 시 정정 공지나 수정 이력 표시 없이 슬쩍 내용을 고치는 행위. 독자는 기사가 수정된 사실 자체를 알 수 없고 언론사는 오보 책임을 회피할 수 있어 투명성을 훼손한다. 외부 비교 필요로 I-트랙.',
  '기사 수정, 수정된 기사, 정정 표시 없이, 수정 이력',
  '사실 검증과 출처',
  '오보 관리 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-3'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-4-a: 추측성 술어 단정 [사실-의견 혼재와 책임 회피 > 사실과 의견 혼재]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-4-a',
  '추측성 술어 단정',
  '불확실한 미래나 아직 확인되지 않은 사실에 대해, 명확한 근거 없이 기자의 추론·예상을 단정적인 어조로 서술하는 경우. ''~로 풀이된다'', ''~라는 관측이다'', ''~할 가능성을 배제할 수 없다'' 같은 모호한 서술어를 사용하여 추측을 객관적 분석인 양 포장한다. [B카테고리]',
  '로 보인다, 로 풀이된다, 로 관측된다, 로 전망된다, 할 가능성을 배제할 수 없다, 로 굳어지는 분위기, 수순 밟을 듯',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견 혼재',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-4-b: 미래 단정 [사실-의견 혼재와 책임 회피 > 사실과 의견 혼재]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-4-b',
  '미래 단정',
  '아직 확정되지 않은 사안임에도 ''~가 유력하다'', ''~로 가닥을 잡았다'', ''사실상 확정'' 등 단정적 표현으로 미래를 단정 보도하는 경우. 추측이나 예상을 기정사실인 것처럼 제시하여 독자가 불확실한 정보를 사실로 오인하게 만든다. [B카테고리]',
  '할 것으로 전망된다, 로 가닥을 잡았다, 가 유력하다, 사실상 확정, 는 기정사실이나 다름없다, 굳어지는 분위기',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견 혼재',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-4-c: 의혹 기정사실화 [사실-의견 혼재와 책임 회피 > 사실과 의견 혼재]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-4-c',
  '의혹 기정사실화',
  '''~의혹이 일고 있다'', ''~설(說)이 파다하다'', ''뒷말이 무성하다'' 등의 표현으로 검증되지 않은 의혹·루머를 마치 사실인 것처럼 보도하는 경우. 형식적으로는 ''의혹 제기''에 머무르지만 실질적으로는 의혹을 사실 영역으로 끌어들여 명예 훼손 결과를 야기한다. [B카테고리]',
  '의혹이 일고 있다, 설(說)이 파다하다, 논란 확산, 뒷말이 무성하다, 의혹 눈덩이, 정황이 포착',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견 혼재',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-4-d: 의견의 사실화 (기자) [사실-의견 혼재와 책임 회피 > 사실과 의견 혼재]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-4-d',
  '의견의 사실화 (기자)',
  '기자 개인의 주관적 판단·평가·해석을 객관적으로 확인된 사실인 것처럼 제시하는 행위. ''졸속으로 처리됐다'', ''꼼수'', ''무책임한 태도'' 같은 가치 판단 표현이나 ''~에 급급했다'', ''~로 전락했다'' 같은 사견을 팩트의 서술어 자리에 배치한다. [B카테고리]',
  '졸속으로 처리됐다, 꼼수, 무책임한 태도, 안일한 판단이 화를 불렀다, 전락했다, 급급했다, 무책임한 행태, 자충수를 뒀다, 당연한 수순이다, 비판을 피하기 어렵다',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견 혼재',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-4-e: 심리·의도 단정 [사실-의견 혼재와 책임 회피 > 사실과 의견 혼재]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-4-e',
  '심리·의도 단정',
  '취재원이나 보도 대상의 내면 심리·의도·동기를 확인 없이 단정적으로 서술하는 행위. ''~하려는 노림수'', ''당혹감을 감추지 못했다'', ''정치적 셈법'' 같은 표현으로 타인의 내면을 추측하여 사실처럼 제시한다. [B카테고리]',
  '당혹감을 감추지 못했다, 노림수, 정치적 셈법, 불편한 심기, 속앓이를 하고 있다, 포석, 속내를 드러냈다, 의식한 행보',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견 혼재',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-a: 데이터 출처·조사방법 미공개 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-a',
  '데이터 출처·조사방법 미공개',
  '데이터의 원천·수집 방법·조사 시점 등 정보 신뢰도 판단에 필수적인 배경 정보를 명확히 밝히지 않는 행위. (예: ''최근 연구에 따르면 한국인의 80%가 이 정책에 반대한다''고 보도하면서 어떤 기관이 언제 어떤 방식으로 조사한 연구인지 전혀 밝히지 않는 경우)',
  '최근 한 연구결과에 따르면, 자체 설문조사 결과, 전문가들에 따르면, 조사 결과에 따르면, 출처 미공개, 시점 미상',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-b: 이해충돌 미공개 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-b',
  '이해충돌 미공개',
  '데이터·연구를 제공한 기관의 재정적·정치적 이해관계를 밝히지 않고 객관적 정보인 것처럼 보도하는 행위. (예: 특정 제약회사 후원 임상시험 결과를 인용하며 후원 사실 누락) 외부 정보 비교 필요로 본문 단독 감지 불가, I-트랙.',
  '후원, 자금 지원, 협찬, 의뢰 연구, 컨설팅 의뢰, 이해관계 미공개',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-c: 2차/3차 출처 의존 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-c',
  '2차/3차 출처 의존',
  '원 데이터를 직접 확인하지 않고, 다른 매체나 기관이 이미 가공·해석한 결과를 검증 없이 재인용하는 ''받아쓰기 저널리즘''의 데이터 버전. 원본 맥락 소실 및 이전 단계 오류 확산 위험이 크다. 외부 비교 필요로 I-트랙.',
  '외신을 인용한 보도에 따르면, 다른 매체가 인용한, 재인용, 2차 자료에 따르면',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-d: 대표성 없는 표본 사용 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-d',
  '대표성 없는 표본 사용',
  '특정 성별·연령·지역·이념 성향 등에 치우친 제한적 표본 조사 결과를 전체 모집단 의견인 것처럼 일반화하는 오류. 소수의 의견을 다수 여론으로 포장하여 여론을 왜곡하며, ''일부 사례의 부당한 일반화(3-2-c)''의 통계적 버전이다.',
  '특정 커뮤니티 응답자, 일부 표본, 100명을 대상으로, 표본의 한계, 일부 응답자',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-e: 유도 질문 사용 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-e',
  '유도 질문 사용',
  '특정 답변을 암시·유도하는 편향된 질문을 사용한 설문 결과를 객관적 여론인 것처럼 보도하는 행위. 설문조사의 외형을 띠지만 실제로는 설계자의 주장을 정당화하는 요식행위로, 여론을 ''측정''하는 게 아니라 ''만들어''낸다.',
  '유도 질문, 위협을 가할 수 있는, 부정 전제 질문, 안보를 위협, 폐해, 부작용을 우려',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-f: 선거 여론조사 과장·왜곡 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-f',
  '선거 여론조사 과장·왜곡',
  '정치적으로 민감한 선거 국면에서 여론조사 결과를 부정확하게 해석하거나 과장하여 민심을 왜곡하는 보도 행태. (예: 통계적 동률을 ''선두''로 보도, 오차범위 큰 하위표본 결과를 ''20대 표심 급격 쏠림''으로 과장) 유권자 표심에 직접 영향을 미쳐 선거 공정성을 훼손한다.',
  '오차범위 내에서 선두 탈환, 20대 표심 쏠림 현상 뚜렷, 누리꾼들 사이에서, 표심 급격, 지지율 급등, 압도적 지지',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-g: 작위적 통계 가공(짜깁기) [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-g',
  '작위적 통계 가공(짜깁기)',
  '공식 통계 기준을 무시하고 입맛에 맞는 기준을 적용하거나, 성격이 다른 지표들을 억지로 합쳐 새로운 수치를 만들어내는 행위. (예: 공식 실업자 통계에 포함되지 않는 취업준비생을 임의 포함하여 ''체감 실업률 50% 육박''으로 충격 수치 생성)',
  '체감 ~율, 사실상 ~배, 자체 집계 결과, 환산하면 ~에 달해, 추정 손실, 실질 부담',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-h: 통계 맥락 무시(기저효과·계절성) [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-h',
  '통계 맥락 무시(기저효과·계절성)',
  '데이터에 큰 영향을 미치는 중요 배경(기저효과, 계절성 등)을 무시하고 수치 변화만을 단순 비교하여 현상을 과장·왜곡하는 보도. (예: 작년 폭염에 폭락했던 배추 가격 회복을 ''배추값 1년 새 300% 폭등''으로 보도)',
  '300% 폭등, 작년 동월 대비, 전년 대비 급증, 기저효과 미언급, 계절 요인 미고지, 평년 회복',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-i: 연구 결과 선택적·과장 인용 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-i',
  '연구 결과 선택적·과장 인용',
  '기자의 주장·관점에 부합하는 연구 결과만 선별 인용하거나, 예비 단계의 소규모 연구를 확정된 과학적 사실인 것처럼 과장 보도하는 행위. (예: 수십 개 반대 연구는 무시하고 단 하나의 소규모 연구로 ''암 예방 탁월한 효과 입증'')',
  '효과 입증, 획기적 효과, 탁월한, 단일 연구, 소규모 연구, 첫 임상시험에서, 일부 실험에서',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-j: 그래프 축 조작 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-j',
  '그래프 축 조작',
  '그래프 세로축(Y축)을 0에서 시작하지 않거나 축 간격을 비균등 설정하여 변화 크기·추세를 시각적으로 왜곡하는 기법. 이미지 영역으로 본문 단독 감지 불가, I-트랙.',
  '그래프 Y축, 축 절단, 차트 왜곡 (이미지 영역, 본문 단독 감지 불가)',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 1-5-k: 비례 왜곡·시각효과 남용 [인과 오류와 통계 오용 > 데이터 및 통계 오용]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '1-5-k',
  '비례 왜곡·시각효과 남용',
  '실제 데이터 비율과 맞지 않는 막대 길이·원 면적, 불필요한 3D 효과 등을 사용하여 정확한 비교를 방해하는 행위. (예: 2배 차이를 원 지름 2배로 그려 4배처럼 보이게 하는 경우) 이미지 영역으로 I-트랙.',
  '원 그래프 비례 왜곡, 3D 효과, 막대 길이 차이 (이미지 영역, 본문 단독 감지 불가)',
  '인과 오류와 통계 오용',
  '데이터 및 통계 오용',
  3,
  (SELECT id FROM public.patterns WHERE code = '1-5'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-1-a: 취재원 신원 모호 표기 [사실 검증과 출처 > 취재원 투명성 결여]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-1-a',
  '취재원 신원 모호 표기',
  '익명/비익명을 막론하고, 독자가 취재원의 신뢰도를 판단할 수 있는 최소한의 정보(소속, 직위, 이해관계 등)를 제공하지 않는 행위. ''한 소식통'', ''여권 핵심'' 같은 모호한 수식어로 출처를 뭉갠다. 통계·연구 출처 미공개(1-1-g)와 구분되며, 본 항목은 취재원 신원 익명화·불명확에 한정.',
  '한 관계자, 여권 핵심, 정부 고위 관계자, 한 소식통, 익명을 요청한 관계자, 익명의 한 인물, 익명 처리',
  '사실 검증과 출처',
  '취재원 투명성 결여',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-1-b: 익명 이용 공격·책임 회피 [사실 검증과 출처 > 취재원 투명성 결여]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-1-b',
  '익명 이용 공격·책임 회피',
  '익명 취재원을 내세워 특정 개인·집단을 비난하거나 확인되지 않은 부정적 정보를 유포하는 행위. (예: ''여권 핵심 관계자는 "A의원은 배신자"라고 비판했다'') 실명으로는 어려운 인신공격을 익명 뒤에 숨어 쏟아내거나 정책 결정 전에 여론을 떠보는 도구로 악용된다.',
  '여권 핵심 관계자는, 익명의 비판, 정부 관계자에 따르면 그는, 라고 비판했다, 신변 안전 우려',
  '사실 검증과 출처',
  '취재원 투명성 결여',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-1-c: 익명 남용·설명 책임 부재 [사실 검증과 출처 > 취재원 투명성 결여]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-1-c',
  '익명 남용·설명 책임 부재',
  '내부고발자 보호 등 정당한 사유가 없음에도 단순히 취재 편의를 위해 습관적으로 익명을 사용하는 행태. 기자는 취재원의 익명 요구·수용 이유를 독자에게 설명할 의무가 있음에도 무분별하게 익명 취재원을 인용하여 언론의 투명성·책임성을 무너뜨린다.',
  '한 관계자, 익명 처리, 관계자에 따르면, 한 인물, 한 인사, 또 다른 관계자',
  '사실 검증과 출처',
  '취재원 투명성 결여',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-2-a: 무주체 피동형 남용 [사실-의견 혼재와 책임 회피 > 책임 회피 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-2-a',
  '무주체 피동형 남용',
  '주체가 불명확한 피동형 표현을 사용하여 정보 출처나 책임 소재를 모호하게 만드는 표현 방식. ''~로 알려졌다'', ''~로 전해졌다'', ''~로 관측된다'', ''~로 전망된다'' 등이 대표적이며, ''누가'' 알려줬는지 명시하지 않아 독자가 정보 신뢰도를 판단할 수 없게 만든다. [B카테고리]',
  '로 알려졌다, 로 전해졌다, 로 파악됐다, 로 관측된다, 전망되어진다, 판단되어진다, 로 확인됐다, 로 알려져',
  '사실-의견 혼재와 책임 회피',
  '책임 회피 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-2-b: 이중피동(겹피동) [사실-의견 혼재와 책임 회피 > 책임 회피 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-2-b',
  '이중피동(겹피동)',
  '''풀이되어진다'', ''판단되어진다'', ''관측되어진다'' 등 이중피동(겹피동) 표현. 문법적으로 명백한 오류이면서 동시에 책임 회피를 극대화하는 표현으로, 기자가 자신의 판단·책임을 숨기는 수단으로 악용된다. [B카테고리]',
  '예상되어진다, 판단되어진다, 검토되어지는, 추정되어진다, 관측되어진다, 풀이되어진다',
  '사실-의견 혼재와 책임 회피',
  '책임 회피 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-2-c: 간접인용 판단 서술 [사실-의견 혼재와 책임 회피 > 책임 회피 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-2-c',
  '간접인용 판단 서술',
  '''~라는 평가다'', ''~라는 비판이다'', ''~라는 진단이다'' 같이 인용 내용을 ''~라는''으로 처리하고 뒤에 명사를 붙이는 형태로, 누가 평가하고 비판했는지 밝히지 않는 표현 방식. 기자가 자신의 주관적 견해를 보편적·전문적 판단인 것처럼 포장하면서 책임은 지지 않는다. [B카테고리]',
  '라는 비판이다, 라는 평가다, 라는 진단이다, 라는 지적이 나온다, 라는 후문이다, 라는 말도 나온다, 라는 해석이 지배적이다',
  '사실-의견 혼재와 책임 회피',
  '책임 회피 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-2-d: 익명화된 집단 의견 위조 [사실-의견 혼재와 책임 회피 > 책임 회피 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-2-d',
  '익명화된 집단 의견 위조',
  '구체적인 근거나 출처 없이 마치 다수 합의나 전문가 집단 공통 견해가 존재하는 것처럼 포장하는 표현 방식. ''~라는 목소리가 높다'', ''~라는 시각이 우세하다'', ''~분위기다'' 등이 대표적이며, 소수 의견이나 기자 본인 주관을 다수 여론처럼 권위 부여한다. [B카테고리]',
  '목소리가 높다, 시각이 우세하다, 지배적이다, 분위기다, 관측이 나온다, 힘이 실리고 있다, 여론이 형성되고 있다, 의견이 대세',
  '사실-의견 혼재와 책임 회피',
  '책임 회피 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-3-a: 기자 실명 미표기 [사실 검증과 출처 > 기자명·출처 표기 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-3-a',
  '기자 실명 미표기',
  '기사 작성자의 실명을 표기하지 않아, 보도 내용에 대한 책임 주체를 불명확하게 만드는 행위. 온라인 기사에서 아예 저자 정보를 생략하면 오보·편향 보도가 발생해도 누구도 책임지지 않는 구조가 된다. 메타데이터 영역으로 본문 단독 감지 불가, I-트랙.',
  '기자 실명 미표기, 저자명 누락, 작성자 미상 (메타데이터 영역, 본문 단독 감지 불가)',
  '사실 검증과 출처',
  '기자명·출처 표기 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-3'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 2-3-b: 바이라인 왜곡 [사실 검증과 출처 > 기자명·출처 표기 부실]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '2-3-b',
  '바이라인 왜곡',
  '기사 작성자를 표기하되 실제 취재·작성 과정을 왜곡하여 책임 소재를 불명확하게 만드는 행위. 유령 바이라인(미참여자 이름 표기), 대리 바이라인(인턴 기사에 데스크 이름), 집단 바이라인(''취재팀'') 등이 포함된다. 메타데이터 영역으로 I-트랙.',
  '취재팀, OO 편집부, 특별취재반, 본지 취재팀, 디지털뉴스국, 종합 데스크 (메타데이터 영역, 본문 단독 감지 불가)',
  '사실 검증과 출처',
  '기자명·출처 표기 부실',
  3,
  (SELECT id FROM public.patterns WHERE code = '2-3'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-1-a: 단일 관점 편향 [균형성과 공정성 > 관점 다양성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-1-a',
  '단일 관점 편향',
  '복합·논쟁적 사안에 대해 한 가지 관점만 제시하거나, 특정 입장만 일방적으로 대변하는 보도 행태. 찬반 양론이 존재하는 정책에서 한쪽 입장만 전달하거나 반대 의견을 형식적으로만 언급하여 독자 판단을 특정 방향으로 유도한다. (예: 최저임금 인상 보도에서 자영업자 어려움만 채우고 저임금 노동자 소득 증가 효과는 누락)',
  '일방적 입장, 한쪽 주장만, 반대 의견 누락, 단일 시각, 한 입장만',
  '균형성과 공정성',
  '관점 다양성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-1-b: 편향된 취재원 구성 [균형성과 공정성 > 관점 다양성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-1-b',
  '편향된 취재원 구성',
  '이해관계가 복잡한 사안에서 특정 입장의 취재원만 선별 인용하고 반대 의견 취재원을 의도적으로 배제하여 기사 균형을 무너뜨리는 경우. 직접 인용·간접 인용 비대칭, 동일 진영 취재원 반복 배치 등으로 ''여론의 쏠림''을 인위 연출한다.',
  '특정 전문가 반복, 반대 측 미인용, 동일 진영 인용 반복, 인용 비대칭',
  '균형성과 공정성',
  '관점 다양성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-1-c: 핵심 이해관계자 배제 [균형성과 공정성 > 관점 다양성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-1-c',
  '핵심 이해관계자 배제',
  '사안에 직접 영향받는 당사자나 정책에 관여된 핵심 이해관계자의 목소리를 배제하는 경우. 복합적 사안일수록 다층적 이해관계가 존재하는데, 단순화된 관점만 전달하면 독자는 사안의 복잡성을 이해할 수 없다. (예: 기초생활수급자 선정기준 강화 보도에서 수급 자격을 잃을 저소득층 당사자 목소리를 누락)',
  '당사자 발언 누락, 이해관계자 배제, 핵심 인물 인용 부재, 정작 당사자는, 영향받는 사람들의 의견 미반영',
  '균형성과 공정성',
  '관점 다양성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-2-a: 이념·정파적 프레이밍 [균형성과 공정성 > 편향적 보도]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-2-a',
  '이념·정파적 프레이밍',
  '특정 이념·정파 관점을 전제로 사실을 선택적으로 해석·평가하는 보도 관행. ''보수 vs 진보'', ''친기업 vs 친노동'' 이분법으로 사실 자체보다 ''누구의 편인가''를 기준으로 보도 방향을 결정한다. (예: 비슷한 부동산 정책을 정부에 따라 ''시장 안정화''/''포퓰리즘''으로 다르게 프레이밍)',
  '포퓰리즘 정책, 친노동 편향, 보수 진영, 좌파식 접근, 코드인사, 진보 진영, 우파 정책, 친기업 일변도',
  '균형성과 공정성',
  '편향적 보도',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-2-b: 선별적 사실 제시 [균형성과 공정성 > 편향적 보도]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-2-b',
  '선별적 사실 제시',
  '전체 사실 중 특정 방향에 유리한 부분만 선택적으로 보도하고 불리한 사실은 축소하거나 다루지 않는 보도 행태. 표면적으로는 사실 자체를 충실히 다루지만 중요한 맥락·반대 사실을 의도적으로 누락하여 의도한 방향으로 여론을 조성한다.',
  '긍정 효과만 부각, 부작용 미언급, 일부 통계만 강조, 유리한 사실만, 핵심 정보 누락',
  '균형성과 공정성',
  '편향적 보도',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-2-c: 일부 사례의 부당한 일반화 [균형성과 공정성 > 편향적 보도]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-2-c',
  '일부 사례의 부당한 일반화',
  '통계적으로 유의미하지 않은 극소수의 개별 사례, 특히 극단적·선정적 사례만을 근거로 해당 집단 전체의 특성인 것처럼 일반화하는 논리적 오류. (예: 수천 명 중 일부 폭력 행위로 전체 해고자를 ''잠재적 폭력 집단''으로 낙인) 특정 집단에 대한 편견·혐오를 조장하고 사회적 낙인을 찍는다.',
  '그들(특정 집단)이, MZ세대 전체가, 이대남 현상, 요즘 2030 세대는, 젊은 세대 전체, 그들이 또, 또 다시 그들',
  '균형성과 공정성',
  '편향적 보도',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-2-d: 기계적 양비론 [균형성과 공정성 > 편향적 보도]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-2-d',
  '기계적 양비론',
  '사실과 거짓, 옳고 그름이 분명한 사안임에도, 사안 진실성·증거 비중과 무관하게 형식적으로 양측 입장을 동등하게 다루는 보도 관행. 진실을 규명해야 할 사안을 단순한 ''정쟁''으로 치부하여 명백한 거짓 주장에도 진실과 동등한 지위를 부여한다.',
  '양측 모두 책임, 피장파장, 도토리 키 재기, 네 탓 공방, 양비론, 둘 다 잘못, 어차피 그놈이 그놈',
  '균형성과 공정성',
  '편향적 보도',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-3-a: 인과관계 왜곡 [인과 오류와 통계 오용 > 인과관계 왜곡]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-3-a',
  '인과관계 왜곡',
  '복잡한 사회 현상을 단일 원인으로 축소하거나, 동시 발생·시간 선후만으로 인과관계를 단정하거나, 원인과 결과를 뒤바꿔 해석하는 인과 오류 전반. (예: ''새 정부 출범 후 물가 급등''으로 시간 선후만으로 정책을 원인 지목, ''아이스크림 판매량과 익사 사고 동시 증가''로 진짜 원인 ''여름철 기온'' 미언급) 5-1 인과관계 단순화도 본 항목으로 흡수.',
  '출범 후 발생, 정권 교체 이후 급등, 시행 후, 와 맞물려, 할수록 한다, 와 함께 증가, 전적으로 때문이다, 직접적 원인은, 탓에, 주범은, 만으로',
  '인과 오류와 통계 오용',
  '인과관계 왜곡',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-3'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-4-a: 이분법 대결 구도 [균형성과 공정성 > 갈등 조장 프레이밍]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-4-a',
  '이분법 대결 구도',
  '복잡한 이해관계와 다층적 관점이 공존하는 사안을 ''A진영 vs B진영'', ''찬성 vs 반대'' 같은 단순 이분법 프레임으로 보도하는 행태. 다양한 층위의 의견과 중도적 목소리가 다수임에도 양극단 입장만 부각시켜 사회가 두 진영으로 갈라진 것처럼 묘사한다. (예: 의료 공백 사태를 ''정부 vs 의사'' 대결 구도로만 보도)',
  '정부 vs 의사, 여 vs 야, 강 대 강, 진영 대결, 편 가르기, 두 진영, 양측 충돌',
  '균형성과 공정성',
  '갈등 조장 프레이밍',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-4-b: 제로섬 프레임 [균형성과 공정성 > 갈등 조장 프레이밍]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-4-b',
  '제로섬 프레임',
  '''한쪽의 이익은 곧 다른 쪽의 손실''이라는 논리로 사안을 프레이밍하여, 전체 자원이 증가하거나 양쪽 모두 이익이 될 가능성을 의도적으로 은폐하는 보도. (예: 노인·청년 복지 모두 증액되었음에도 ''기초연금 30만원으로 인상… 청년수당 재원은 또 뒷전''으로 세대 갈등 왜곡)',
  '한정된 재원을 두고, 예산 다툼, 확대로 축소 불가피, 세대 간 밥그릇 싸움, 역차별 논란, 퍼주기 논란, 한쪽 이익 곧 다른 쪽 손실',
  '균형성과 공정성',
  '갈등 조장 프레이밍',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-4-c: 전쟁·전투 은유 [균형성과 공정성 > 갈등 조장 프레이밍]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-4-c',
  '전쟁·전투 은유',
  '정치·사회적 논의나 정책 경쟁을 ''전면전'', ''사활을 건 전투'', ''단두대 매치'', ''칼부림'', ''내부 총질'' 같은 전쟁·폭력 은유로 과도하게 표현하여 정치를 폭력적 대결의 장으로 인식하게 만드는 보도. 정치 혐오를 조장하고 합리적 정책 논의 대신 진영 간 증오를 부추긴다.',
  '전면전, 선전포고, 사활을 건, 단두대 매치, 육탄방어, 피 튀기는, 초토화, 칼부림, 내부 총질, 폭탄 선언',
  '균형성과 공정성',
  '갈등 조장 프레이밍',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-5-a: 선택적 보도 회피 [균형성과 공정성 > 보도 회피와 물타기]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-5-a',
  '선택적 보도 회피',
  '특정 사안을 의도적으로 배제·축소하여 대중 관심에서 멀어지게 하거나 주목도를 떨어뜨리는 보도 행위. ''무엇을 보도하지 않을 것인가''를 통해 여론 방향을 결정하는 정치적 행위로, 단순한 정보 취사 선택이 아니다. 외부 비교 필요로 본문 단독 감지 불가, I-트랙.',
  '보도 회피, 외면, 침묵, 다루지 않음 (외부 비교 필요, 본문 단독 감지 불가)',
  '균형성과 공정성',
  '보도 회피와 물타기',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-5'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 3-5-b: 물타기 보도 [균형성과 공정성 > 보도 회피와 물타기]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '3-5-b',
  '물타기 보도',
  '정치·경제 권력이나 특정 집단에 불리한 이슈가 발생했을 때, 논점을 흐리거나 전환하기 위해 자극적인 연성 뉴스를 배치하거나 상대 진영에 별건의 의혹을 제기해 ''맞불''을 놓는 식의 보도 행위. 외부 비교 필요로 I-트랙.',
  '맞불, 별건 의혹, 자극적 연성 뉴스 배치 (외부 비교 필요, 본문 단독 감지 불가)',
  '균형성과 공정성',
  '보도 회피와 물타기',
  3,
  (SELECT id FROM public.patterns WHERE code = '3-5'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-1-a: 편법 취재 [인권·윤리 > 취재 과정의 인권 침해]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-1-a',
  '편법 취재',
  '신분을 사칭하거나 상황을 속여 정보를 수집하는 행위, 또는 도청·불법 촬영·무단 침입 등 불법 수단으로 취재하는 경우. 공익을 위해 정당화될 수 있는 예외적 상황이 아닌 한, 이러한 방식으로 얻은 정보는 그 자체로 인권을 침해한다. 취재 과정 정보로 본문 단독 감지 불가, I-트랙.',
  '신분 사칭, 위장 잠입, 도청, 불법 촬영, 무단 침입 (취재 과정 정보, 본문 단독 감지 불가)',
  '인권·윤리',
  '취재 과정의 인권 침해',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-1'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-1-b: 사생활 침해(취재 과정) [인권·윤리 > 취재 과정의 인권 침해]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-1-b',
  '사생활 침해(취재 과정)',
  '취재 대상의 동의 없이 사적 공간(주거지·병원·사무실)을 침범하거나, 보도의 공익적 필요성을 넘어 지나치게 사적인 정보(가족관계·건강·재산·성생활)를 수집·보도하는 행위. 취재 과정 정보로 I-트랙.',
  '사적 공간 침범, 동의 없이 가족 정보, 무단 가족관계 공개 (취재 과정 정보, 본문 단독 감지 불가)',
  '인권·윤리',
  '취재 과정의 인권 침해',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-1'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-1-c: 피해자·약자 인권 무시(취재) [인권·윤리 > 취재 과정의 인권 침해]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-1-c',
  '피해자·약자 인권 무시(취재)',
  '사건·사고 현장에서 피해자·유족 의사를 무시하고 무리하게 인터뷰를 요구하거나, 신체적·정신적으로 취약한 이들(아동·장애인·환자·범죄 피해자)을 보호하지 않고 공격적으로 취재하는 행위. 취재 과정 정보로 I-트랙.',
  '유족 의사 무시, 무리한 인터뷰 요구, 공격적 취재 (취재 과정 정보, 본문 단독 감지 불가)',
  '인권·윤리',
  '취재 과정의 인권 침해',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-1'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-2-a: 취재원 신상정보 무단 노출 [인권·윤리 > 개인정보 및 신원 보호 위반]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-2-a',
  '취재원 신상정보 무단 노출',
  '익명 보호가 필요한 취재원(내부고발자·범죄 피해자·미성년자)의 이름·나이·직업·거주지 등 식별 가능 정보를 노출하는 행위. 또는 형식적으로 이름은 가렸지만 직업·소속·특정 경험을 통해 신원이 쉽게 추정되도록 만드는 ''부실 익명화''.',
  '취재원 신상 공개, 내부고발자 신원, 미성년자 이름, 직업·거주지 노출, 부실 익명화, 식별 정보',
  '인권·윤리',
  '개인정보 및 신원 보호 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-2-b: 사건 무관 가족 신원 노출 [인권·윤리 > 개인정보 및 신원 보호 위반]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-2-b',
  '사건 무관 가족 신원 노출',
  '사건·사고의 본질과 직접 관련 없는데도 유명인(연예인·정치인) 가족 구성원 신원을 제목·본문에 노출하는 행위. (예: ''OOO 남편, 음주운전으로 적발'', ''국회의원 OOO 딸 학교폭력 가해 의혹'') 가족이라는 이유만으로 공적 관심 대상이 되도록 강제하여 부당하게 평판을 훼손한다.',
  'OOO 남편, 국회의원 OOO 딸, 유명 가수 A씨 동생, OOO 아들, 연예인 OOO 가족',
  '인권·윤리',
  '개인정보 및 신원 보호 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-3-a: 근거 없는 의혹 제기 보도 [인권·윤리 > 명예와 평판 훼손]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-3-a',
  '근거 없는 의혹 제기 보도',
  '사실 여부가 충분히 검증되지 않은 부정적 의혹·루머·비난을 보도하여 개인·단체의 명예와 사회적 평판을 훼손하는 행위. ''의혹 제기형 보도'' 형식을 취하더라도 언론이 의혹을 크게 부각하는 순간 대중은 사실로 받아들이며, 나중에 의혹이 사실이 아닌 것으로 밝혀져도 명예 훼손은 회복되기 어렵다.',
  '의혹이 일고 있다, 뒷말이 무성, 논란의 여지, 꼬리표가 따라, 의혹 제기, 의혹을 받고',
  '인권·윤리',
  '명예와 평판 훼손',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-3'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-3-b: 차별·혐오·인권침해 표현 (6-5 통합) [인권·윤리 > 명예와 평판 훼손]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-3-b',
  '차별·혐오·인권침해 표현 (6-5 통합)',
  '성별·인종·종교·장애·성적 지향·출신 지역 등 개인이 선택할 수 없는 속성을 이유로 차별·비하·혐오 표현을 사용하거나, 특정 집단에 대한 편견·고정관념을 강화하는 보도. ''눈먼 돈'', ''절름발이 정책'' 같은 차별적 관용구, ''강성 노조'', ''귀족 노조'' 같은 집단 낙인 어휘, ''김치녀'', ''한남충'' 같은 혐오 밈·은어 사용을 포괄한다. (구 6-5 차별·혐오 표현 통합)',
  '절름발이 정책, 눈먼 돈, 꿀 먹은 벙어리, 장님, 벙어리 삼 년, 강성 노조, 귀족 노조, OO카르텔, 무임승차, 생떼, 몽니, 철밥통, 김치녀, 한남충, 맘충, 틀딱, 급식충, 영포티, 지잡대',
  '인권·윤리',
  '명예와 평판 훼손',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-3'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-4-a: 수사기관 발표 일방 의존 [인권·윤리 > 사법 절차 존중 위반]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-4-a',
  '수사기관 발표 일방 의존',
  '경찰·검찰 등 수사기관이 제공한 피의 사실 공표(브리핑·보도자료)를 추가 확인이나 반론 청취 없이 그대로 받아써서 보도하는 행위. 수사기관은 피의자에게 불리한 정보를 선택적으로 공개할 유인이 있어, 이를 여과 없이 전달하면 사실상 수사기관 ''홍보 대행''이 되어 피의자 무죄추정권을 침해한다.',
  '검찰에 따르면, 경찰 조사 결과 드러났다, 수사 당국에 따르면, 검찰은 밝혔다, 경찰은 발표했다, 수사관계자에 따르면',
  '인권·윤리',
  '사법 절차 존중 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-4-b: 무죄추정 원칙 위반 [인권·윤리 > 사법 절차 존중 위반]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-4-b',
  '무죄추정 원칙 위반',
  '유죄 판결이 확정되지 않은 피의자·피고인을 유죄로 단정하는 표현을 사용하여 재판 결과를 예단하는 행위. ''범인 A씨'', ''성폭행범'' 같은 단정적 표현이나 ''결국 범행 자백'', ''철저한 증거로 범죄 입증'' 같은 제목은 헌법 제27조 4항(무죄추정)을 침해한다.',
  '범인 A씨, 성폭행범, 결국 자백, 범행 입증, 철저한 증거로 범죄 입증, 꼬리가 밟혔다, 범행 시인, 잡혔다',
  '인권·윤리',
  '사법 절차 존중 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-4-c: 재판 중 사안 편향 보도 [인권·윤리 > 사법 절차 존중 위반]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-4-c',
  '재판 중 사안 편향 보도',
  '재판이 진행 중인 사건에 대해 한쪽(주로 검찰·피해자 측) 주장만 부각하고 다른 쪽 입장은 축소하거나, 법정에 제출되지 않은 증거·소문을 확실한 사실인 것처럼 보도하여 재판에 부당한 압력을 가하는 행위. 여론 압박으로 공정한 재판 받을 권리를 침해할 수 있다.',
  '재판 중인 사안, 한쪽 입장만 부각, 법정에 제출되지 않은 증거, 여론 압박, 검찰 측 주장만',
  '인권·윤리',
  '사법 절차 존중 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-4-d: 부적절한 피의자 신원 공개 [인권·윤리 > 사법 절차 존중 위반]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-4-d',
  '부적절한 피의자 신원 공개',
  '수사 단계 또는 재판 중인 피의자·피고인의 실명·얼굴·직업·거주지·가족관계 등을 공개하여 유죄 판결 이전에 사회적 낙인을 찍고 개인정보 보호 권리를 침해하는 행위.',
  '피의자 실명 공개, 피의자 얼굴 공개, 거주지 공개, 가족관계 공개, 인적사항 공표',
  '인권·윤리',
  '사법 절차 존중 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 4-4-e: 피해자·증인 보호 소홀 [인권·윤리 > 사법 절차 존중 위반]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '4-4-e',
  '피해자·증인 보호 소홀',
  '범죄 사건 피해자·증인의 신원 정보(이름·사진·거주지·직업)를 노출하여 보복 범죄 위험에 처하게 하거나, 사생활 침해와 2차 피해를 초래하는 행위. 증인 신원 노출은 협박·회유로 사법 절차 자체를 왜곡할 위험이 있다.',
  '피해자 신상, 증인 거주지, 목격자 직업, 피해자 사진, 보복 위험',
  '인권·윤리',
  '사법 절차 존중 위반',
  3,
  (SELECT id FROM public.patterns WHERE code = '4-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-1-a: 현상 중심 파편화(원인 단락 부재) [언어·표현 > 기사의 심층성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-1-a',
  '현상 중심 파편화(원인 단락 부재)',
  '육하원칙 중 ''누가·언제·어디서·무엇을'' 했다는 사실 관계만 전달하고, 왜 그런 일이 발생했는지(원인), 어떤 과정을 거쳤는지(과정), 앞으로 어떤 영향을 미칠지(전망) 분석이 없는 경우. 국내 기사 76.9%가 단순 보도에 그치며, 원인 단락 부재가 핵심 신호. (E이동, structural)',
  '사고가 발생했다, 조사 중이다, 단순 사실 전달, 원인 분석 부재, 과정·전망 부재 (구조 신호: 원인 단락 부재)',
  '언어·표현',
  '기사의 심층성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-1-b: 맥락 없는 사실 나열 [균형성과 공정성 > 기사의 심층성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-1-b',
  '맥락 없는 사실 나열',
  '사건이나 정책을 역사적·국제적·사회적 맥락 속에서 설명하지 않아 독자가 현상을 입체적으로 이해하지 못하는 경우. (예: ''한국 청년 실업률이 x%'' 보도하면서 OECD 평균 비교, 과거 추이, 산정 기준 설명, 구조적 미스매치 등 맥락 정보를 제공하지 않는 경우) (C이동)',
  '수치만 나열, 비교 부재, OECD 비교 없음, 과거 추이 미언급, 산정 기준 미설명, 맥락 정보 누락',
  '균형성과 공정성',
  '기사의 심층성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-1-d: 후속 추적·검증 부재 [언어·표현 > 기사의 심층성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-1-d',
  '후속 추적·검증 부재',
  '특정 사안을 한 번 보도한 후 그 이후 어떻게 전개되었는지, 당초 지적한 문제는 해결되었는지, 정치인 공약이나 기업 약속은 이행되었는지 등을 추적 보도하지 않는 것. 시간 추적 정보 비교 필요로 본문 단독 감지 불가, I-트랙.',
  '후속 추적, 그 이후, 어떻게 되었나, 추적 보도, 검증 결과 (시계열 비교 필요, 본문 단독 감지 불가)',
  '언어·표현',
  '기사의 심층성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-1'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-1-e: 대안·전망 부재 [언어·표현 > 기사의 심층성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-1-e',
  '대안·전망 부재',
  '사안이 어떻게 전개될 것인지에 대한 합리적 전망이나 문제 해결을 위한 다양한 대안을 제시하지 않고, 사안의 부정적 측면만 강조 보도하는 행태. (예: ''국민연금 2055년 고갈… 90년대생은 한 푼도 못 받는다 공포'' 같이 우려만 자극할 뿐 개혁안·해외 사례 등 대안을 다루지 않는 기사) (E이동, structural)',
  '고갈 우려, 위기 강조, 공포 조장, 대안 부재, 해법 미제시, 전망 없음, 부정적 측면만 (구조 신호: 해법 단락 부재)',
  '언어·표현',
  '기사의 심층성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-1'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-2-a: 전문용어 남용·미해설 [언어·표현 > 전문성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-2-a',
  '전문용어 남용·미해설',
  '독자가 이해하기 어려운 전문용어·업계 용어·외래어 등을 아무런 설명 없이 그대로 사용하여 정보 접근성을 떨어뜨리는 보도. (예: ''연준이 FOMC 정례회의에서 매파적 스탠스를 유지하며 25bp 금리 인상을 단행했다'') 시민의 알 권리·이해할 권리를 침해한다.',
  'FOMC 매파적 스탠스, 디폴트, 모라토리엄, 빅스텝 단행, bp 인상, 양적 긴축, 매파적 기조 (해설 부재 패턴)',
  '언어·표현',
  '전문성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-2-b: 해당 분야 지식 결여 [언어·표현 > 전문성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-2-b',
  '해당 분야 지식 결여',
  '보도 주제에 대한 기본적인 배경지식·전문성 없이 피상적으로 기사를 작성하여, 사실관계 오류를 범하거나 중요한 쟁점을 놓치거나 현상의 본질을 잘못 해석하는 경우. 외부 전문성 비교 필요로 본문 단독 감지 불가, I-트랙.',
  '법적 요건 미설명, 쟁점 분석 부재, 본질 오해 (외부 전문성 비교 필요, 본문 단독 감지 불가)',
  '언어·표현',
  '전문성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-2-c: 전문가·자료 맹목적 의존 [언어·표현 > 전문성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-2-c',
  '전문가·자료 맹목적 의존',
  '기술적 타당성·실현 가능성을 따져볼 식견이 없어, 기업·정부 보도자료의 장밋빛 전망이나 특정 전문가의 일방적 주장을 비판 없이 ''복사-붙여넣기''하는 행태. 기자의 비판적 검토·독자적 질문 능력 부족이 원인. 외부 비교 필요로 I-트랙.',
  '보도자료 그대로, 전문가 일방 인용, 비판적 분석 부재 (외부 비교 필요, 본문 단독 감지 불가)',
  '언어·표현',
  '전문성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-3-a: 책상머리 기사(현장 부재) [사실 검증과 출처 > 현장성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-3-a',
  '책상머리 기사(현장 부재)',
  '기자가 취재 현장에 나가지 않고 사무실 모니터 앞에서 인터넷 게시글·보도자료·타사 기사 등 ''2차 정보''에만 의존하여 기사를 작성하는 보도 행태. 현장에서만 확인 가능한 구체적 정황·분위기·맥락이 빠져 추상적·건조한 정보만 전달된다. 취재 과정 정보로 I-트랙.',
  '현장 부재, 사무실에서, 모니터 앞에서, 자료에만 의존 (취재 과정 정보, 본문 단독 감지 불가)',
  '사실 검증과 출처',
  '현장성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-3'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-3-b: 피상적 취재 [사실 검증과 출처 > 현장성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-3-b',
  '피상적 취재',
  '현장을 방문하더라도 형식적으로만 들르거나, 대면 인터뷰 대신 전화·이메일에만 의존하여 심층 질문·답변 과정을 생략하는 취재 관행. 취재원의 비언어적 표현이나 감정을 파악하기 어렵고 준비된 답변만 얻게 된다. 취재 과정 정보로 I-트랙.',
  '전화 인터뷰만, 이메일 답변, 형식적 방문 (취재 과정 정보, 본문 단독 감지 불가)',
  '사실 검증과 출처',
  '현장성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-3'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 5-3-c: 간접 인용 위주 보도 [사실 검증과 출처 > 현장성 부족]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '5-3-c',
  '간접 인용 위주 보도',
  '취재원의 실명·육성(직접 인용)을 담지 못하고 전언이나 추측성 표현 뒤에 숨는 보도 행태. 기자가 팩트를 끝까지 확인하지 못했거나 책임질 수 없는 내용을 보도할 때 주로 나타난다. 취재 과정 정보로 I-트랙.',
  '관계자 전언, 일각의 해석, 측근에 따르면, 한 인사는 (취재 과정 정보, 본문 단독 감지 불가)',
  '사실 검증과 출처',
  '현장성 부족',
  3,
  (SELECT id FROM public.patterns WHERE code = '5-3'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-1-a: 추측을 사실처럼 표현 [사실-의견 혼재와 책임 회피 > 사실과 의견을 뒤섞는 주관적 술어]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-1-a',
  '추측을 사실처럼 표현',
  '기자의 추측을 단정적인 표현으로 포장하여 마치 확인된 사실처럼 보이게 만드는 문제. ''~것으로 보인다'', ''~로 풀이된다'', ''관측되고 있다'', ''전망이다'', ''가능성이 높다'', ''주목된다'' 같은 표현 패턴이 대표적. (예: ''정부가 조기 총선을 검토하는 것으로 보인다'') [B카테고리, 1-4-a와 표면 유사 — 6-1-a는 어휘 단위, 1-4-a는 보도 전반]',
  '것으로 보인다, 로 풀이된다, 관측되고 있다, 전망이다, 예상된다, 가능성이 높다, 주목된다',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견을 뒤섞는 주관적 술어',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-1-b: 의견을 사실처럼 표현 [사실-의견 혼재와 책임 회피 > 사실과 의견을 뒤섞는 주관적 술어]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-1-b',
  '의견을 사실처럼 표현',
  '기자의 의견·평가를 단정적인 표현으로 포장하여 마치 확인된 사실처럼 보이게 만드는 문제. ''지적을 받고 있다'', ''비판이 나오고 있다'', ''논란이 일고 있다'', ''~한 셈이다'' 같은 표현 패턴. (예: ''이번 정책은 졸속 행정이라는 지적을 받고 있다'') [B카테고리]',
  '지적을 받고 있다, 비판이 나오고 있다, 논란이 일고 있다, 한 셈이다, 나 다름없다, 평가가 지배적',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견을 뒤섞는 주관적 술어',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-1-c: 의혹을 사실처럼 표현 [사실-의견 혼재와 책임 회피 > 사실과 의견을 뒤섞는 주관적 술어]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-1-c',
  '의혹을 사실처럼 표현',
  '검증되지 않은 의혹을 단정적인 표현으로 포장하여 마치 확인된 사실처럼 보이게 만드는 문제. ''의혹이 일고 있다'', ''의혹을 받고 있다'', ''의문도 제기된다'', ''뒷말이 무성하다'' 같은 표현. (예: ''C기업의 회계 조작 의혹이 일고 있다'') [B카테고리]',
  '의혹이 일고 있다, 의혹을 받고 있다, 의문도 제기된다, 뒷말이 무성하다, 논란의 여지가 있다',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견을 뒤섞는 주관적 술어',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-1-d: 출처 감추기(피동형) [사실-의견 혼재와 책임 회피 > 사실과 의견을 뒤섞는 주관적 술어]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-1-d',
  '출처 감추기(피동형)',
  '정보 출처나 판단 주체를 명시하지 않고 모호한 표현으로 넘기는 책임 회피 표현. ''전해졌다'', ''알려졌다'', ''~라고 한다'', ''~라는 후문이다'', ''파악됐다'' 같은 출처 감추기 패턴. (예: ''A의원이 사퇴를 검토 중인 것으로 알려졌다'') [B카테고리]',
  '전해졌다, 알려졌다, 라고 한다, 라는 후문이다, 파악됐다, 로 나타났다',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견을 뒤섞는 주관적 술어',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-1-e: 평가 주체 감추기 [사실-의견 혼재와 책임 회피 > 사실과 의견을 뒤섞는 주관적 술어]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-1-e',
  '평가 주체 감추기',
  '평가의 주체를 모호하게 처리하여 책임을 회피하는 표현. ''평가를 받는다'', ''평가된다'', ''풀이된다'', ''목소리가 높다'', ''힘이 실리고 있다'' 같은 평가 주체 감추기 패턴. (예: ''B정책은 실효성이 없다는 평가를 받는다'') [B카테고리]',
  '평가를 받는다, 평가된다, 풀이된다, 목소리가 높다, 힘이 실리고 있다, 주목하고 있다',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견을 뒤섞는 주관적 술어',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-1-f: 사실 강도 부풀림 표현 [사실-의견 혼재와 책임 회피 > 사실과 의견을 뒤섞는 주관적 술어]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-1-f',
  '사실 강도 부풀림 표현',
  '사실의 강도·심각성을 부풀려 묘사하는 표현 문제. ''빗발치고 있다'', ''쏟아지고 있다'', ''쇄도했다'', ''들끓고 있다'', ''소용돌이에 휩싸였다'' 같은 표현으로 일부 반응을 전체 여론처럼 확대. (예: ''정책에 대한 비판이 빗발치고 있다'') [B카테고리]',
  '빗발치고 있다, 쏟아지고 있다, 쇄도했다, 들끓고 있다, 소용돌이에 휩싸였다, 전국이 들썩이다, 찬사가 쏟아지다, 날을 세웠다, 나락으로 떨어졌다, 패닉에 빠졌다',
  '사실-의견 혼재와 책임 회피',
  '사실과 의견을 뒤섞는 주관적 술어',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-2-a: 제목-본문 불일치(맥락 삭제) [언어·표현 > 헤드라인 윤리 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-2-a',
  '제목-본문 불일치(맥락 삭제)',
  '기사 제목이 본문의 핵심 내용을 정확히 대표하지 못하고, 발언이나 사건의 전후 맥락·조건·가정을 제거하여 원래 의미를 왜곡하거나 정반대로 뒤집는 행위. (예: ''만약 ~라면''이라는 가정을 삭제하여 발화자의 진의를 왜곡) 제목-본문 비교 필요한 structural 항목.',
  '(제목)에 가정 삭제, 본문 만약 라면 → 제목 단정, 조건 절 누락, 반어를 단정으로 (제목-본문 비교 필요)',
  '언어·표현',
  '헤드라인 윤리 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-2'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-2-b: 제목-본문 불일치(주어·서술어 생략) [언어·표현 > 헤드라인 윤리 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-2-b',
  '제목-본문 불일치(주어·서술어 생략)',
  '제목에서 사건의 주체(누가)나 행위의 결말(어떻게 되었는가)을 의도적으로 숨겨 독자의 궁금증을 유발하고 클릭을 유도하는 기법. 제목-본문 비교 필요한 structural 항목.',
  '주어 생략 제목, 결론 숨기기, 결말 미공개, 충격 결말, 반전 결과는 (제목-본문 비교 필요)',
  '언어·표현',
  '헤드라인 윤리 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-2'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-2-c: 제목-본문 불일치(침소봉대) [언어·표현 > 헤드라인 윤리 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-2-c',
  '제목-본문 불일치(침소봉대)',
  '기사 본문에서 부차적이거나 일부에 불과한 내용을 제목에서 핵심인 것처럼 부각하여, 기사 주제와 중요도를 왜곡하는 행위. 자극적 일부 사례만 제목으로 뽑아 본질을 흐리는 방식으로 악용된다. 제목-본문 비교 필요한 structural 항목.',
  '본문 일부를 제목, 부차적 내용 제목 부각, 일부 사례만 제목 (제목-본문 비교 필요)',
  '언어·표현',
  '헤드라인 윤리 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-2'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-2-d: 헤드라인 낚시성 제목 [언어·표현 > 헤드라인 윤리 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-2-d',
  '헤드라인 낚시성 제목',
  '기사 본문 내용과 정확히 일치하지 않거나 사실을 과장한 자극적 제목으로 독자 클릭을 유도하는 행위. ''충격'', ''경악'', ''발칵'' 등 자극적 단어 남발이나 제목에 물음표 사용으로 확인되지 않은 의혹을 기정사실화하는 기법(예: ''A의원, 불법 정치자금 수수?'') 포함.',
  '충격, 발칵, 결국 그가, OO에 무슨 일이?, 깜짝, 알고 보니, 충격 반전',
  '언어·표현',
  '헤드라인 윤리 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-2'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-3-a: 과장된 표현 [언어·표현 > 과장과 맥락 왜곡]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-3-a',
  '과장된 표현',
  '사실의 중요도나 심각성을 실제보다 부풀려 표현하는 경우. ''사상 최악'', ''초유의 사태'', ''전례 없는'' 등 극단적 수식어를 남발하거나, 일부 사례를 ''전국이 들썩'', ''온 국민이 분노''로 과장하여 독자 인식을 왜곡한다.',
  '사상 최악, 초유의 사태, 전례 없는, 미증유의, 역대 최대, 사상 처음, 한국 사상',
  '언어·표현',
  '과장과 맥락 왜곡',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-3'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-3-b: 형용사·부사 부적절 사용 [언어·표현 > 과장과 맥락 왜곡]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-3-b',
  '형용사·부사 부적절 사용',
  '감정·평가가 담긴 수식어를 과도하게 사용하여 객관성을 해치는 행위. ''너무나'', ''진짜로'', ''아주'', ''심각하게'', ''터무니없이'' 같은 강도 부사나 ''충격적인'', ''경악스러운'', ''한심한'', ''훌륭한'' 같은 가치 판단 형용사를 남용한다.',
  '너무나, 충격적으로, 터무니없이, 경악스럽게도, 진짜로, 아주, 매우, 심각하게, 한심한, 훌륭한',
  '언어·표현',
  '과장과 맥락 왜곡',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-3'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-3-c: 단정적 용어 사용 [언어·표현 > 과장과 맥락 왜곡]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-3-c',
  '단정적 용어 사용',
  '법적 판단이나 확정되지 않은 사안에 대해 마치 결론이 난 것처럼 단정적인 용어를 사용하는 행위. ''간첩'', ''범죄자'', ''사기꾼'' 등 법적 판단이 필요한 용어를 수사 단계에서 사용하거나 ''실패한 정책'', ''무능한 리더십'' 등 평가 표현을 확정된 사실처럼 제시한다.',
  '간첩, 범죄자, 사기꾼, 실패한 정책, 무능한 리더십, 명백한, 단정적 표현, 확정 단정',
  '언어·표현',
  '과장과 맥락 왜곡',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-3'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-3-d: 인용 비틀기(맥락 왜곡) [언어·표현 > 과장과 맥락 왜곡]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-3-d',
  '인용 비틀기(맥락 왜곡)',
  '취재원 발언이나 원문 자료의 맥락을 무시하고, 기자 의도·기사 프레임에 맞는 특정 문장이나 단어만 선택적으로 인용하여 발화자 의도를 왜곡하는 보도 행태. 가정·예시 발언을 단정적 주장으로 바꾸거나, 반어적 표현을 문자 그대로 인용하여 정반대 의미로 전달한다. 발언 원문-본문 맥락 비교 필요한 structural 항목.',
  '발언 일부 인용, 가정 발언을 단정, 반어를 문자대로, 인용 맥락 왜곡, 인용 비틀기 (발언 원문 비교 필요)',
  '언어·표현',
  '과장과 맥락 왜곡',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-3'),
  TRUE,
  'structural',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-4-a: 낚시성 자극 어휘(충격·경악) [언어·표현 > 자극적·선정적 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-4-a',
  '낚시성 자극 어휘(충격·경악)',
  '''충격'', ''경악'', ''발칵'', ''논란'', ''파문'', ''폭탄 선언'', ''대반전'' 등 자극적 단어를 남발하여 독자의 클릭을 유도하는 행위. 사실의 중요도와 무관하게 감각적 자극에 호소하여 객관 보도 책무를 저버린다.',
  '충격, 경악, 발칵, 파문, 폭탄 선언, 대반전, 충격 폭로, 경악 결과, 발칵 뒤집힌',
  '언어·표현',
  '자극적·선정적 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-4-b: 자살 자극 묘사 [언어·표현 > 자극적·선정적 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-4-b',
  '자살 자극 묘사',
  '자살 방법·장소·도구 등을 지나치게 상세히 묘사하거나 자살을 미화하는 표현을 사용하여 모방 자살을 유발할 위험이 있는 보도. ''투신'', ''목을 매'', ''손목을 그어'', ''유서 내용'', ''자살을 선택'' 등 표현은 자살 충동을 느끼는 사람들에게 위험한 영향을 미친다. WHO·한국기자협회 권고 위반.',
  '투신, 목을 매, 손목을 그어, 유서 내용에는, 유서를 남기고, 자살을 선택, 자살 시도, 극단적 선택',
  '언어·표현',
  '자극적·선정적 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-4-c: 사건·재난 잔혹 묘사 [언어·표현 > 자극적·선정적 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-4-c',
  '사건·재난 잔혹 묘사',
  '범죄·사고·재난 현장의 잔혹하고 충격적인 장면을 필요 이상으로 자세히 묘사하여 독자에게 정신적 충격을 주는 행위. ''피범벅'', ''혈흔'', ''참혹한 모습'', ''신체 절단'', ''끔찍한 비명'' 등 사망자·부상자 신체 상태나 사고 현장 참혹한 모습을 선정적으로 서술하면 피해자·유족 2차 피해를 야기한다.',
  '피범벅이 된, 혈흔이, 참혹한 모습, 신체 절단, 끔찍한 비명, 처참한 시신, 핏자국, 처참한 장면',
  '언어·표현',
  '자극적·선정적 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-4'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-6-a: 복잡한 문장 구조 [언어·표현 > 명료성을 해치는 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-6-a',
  '복잡한 문장 구조',
  '지나치게 긴 문장이나 중문·복문을 남발하는 경우. 한 문장 안에 여러 절을 연결하거나 주어-서술어가 멀리 떨어져 있거나 수식어구가 과도하게 삽입된 문장은 독자 집중력을 흐트러뜨리고 핵심 정보 전달을 방해한다.',
  '긴 문장, 중문 복문, 수식어구 과다, 주어-서술어 멀리 (문장 구조 분석)',
  '언어·표현',
  '명료성을 해치는 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-6'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-6-b: 외래어·전문용어 미해설 [언어·표현 > 명료성을 해치는 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-6-b',
  '외래어·전문용어 미해설',
  '적절한 우리말 표현이 있음에도 충분한 설명 없이 외래어·전문용어를 사용하는 경우. ''디폴트(채무불이행)'', ''모라토리엄(지급유예)'' 등 쉬운 우리말 대신 외래어를 선호하거나, 경제·법률·의료 분야 전문용어를 일반 독자 눈높이 고려 없이 사용하는 것은 정보의 공공성을 해친다.',
  'FOMC, 디폴트, 모라토리엄, 빅스텝, 매파적 스탠스, bp, 디테일, 솔루션 (해설 부재)',
  '언어·표현',
  '명료성을 해치는 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-6'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-6-c: 군더더기 표현 [언어·표현 > 명료성을 해치는 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-6-c',
  '군더더기 표현',
  '의미가 중복되는 표현을 불필요하게 반복하여 문장을 장황하게 만들고 가독성을 떨어뜨리는 경우. ''거의 대부분'', ''가장 최고'', ''판이하게 다르다'', ''과반수 이상'', ''다시 재개'', ''계속 지속'' 등 의미 중복 단어 사용이 대표적이다.',
  '거의 대부분, 가장 최고, 다시 재개, 과반수 이상, 판이하게 다르다, 현격한 격차, 위로 올라가다, 서로 상반된다, 계속 지속',
  '언어·표현',
  '명료성을 해치는 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-6'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 6-6-d: 상투어 남용 [언어·표현 > 명료성을 해치는 표현]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '6-6-d',
  '상투어 남용',
  '진부한 표현을 남발하여 전달력을 떨어뜨리는 경우. ''화들짝 놀랐다'', ''날개 없는 추락'', ''발목을 잡다'', ''암초가 많다'', ''도마 위에 오르다'', ''안갯속'', ''시한폭탄'', ''뇌관'', ''촉각을 곤두세우다'' 등 언론계 관습 상투적 표현이 정확한 사실 전달보다 분위기 연출에 치중한다.',
  '도마 위에 오르다, 암초가 많다, 발목을 잡다, 촉각을 곤두세우다, 화들짝 놀랐다, 공세 수위를 높였다, 안갯속, 시한폭탄, 뇌관, 격랑에 빠진다',
  '언어·표현',
  '명료성을 해치는 표현',
  3,
  (SELECT id FROM public.patterns WHERE code = '6-6'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-1-a: 원작자 동의 없는 무단 전재 [인권·윤리 > 소셜미디어 활용 윤리]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-1-a',
  '원작자 동의 없는 무단 전재',
  '일반인이나 공인의 SNS 게시물(글·사진·영상)을 원작자의 명시적 동의 없이 무단으로 기사에 사용하는 문제. ''출처 표기''만 하면 문제없다는 안일한 인식이 퍼져 있으나, 이는 명백한 저작권·초상권 침해. 외부 동의 절차 비교 필요로 본문 단독 감지 불가, I-트랙.',
  'SNS 게시글, 인스타그램 글, 페이스북 게시물 (원작자 동의 비교 필요, 본문 단독 감지 불가)',
  '인권·윤리',
  '소셜미디어 활용 윤리',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-1'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-1-b: 소셜미디어 정보 무검증 [사실 검증과 출처 > 소셜미디어 활용 윤리]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-1-b',
  '소셜미디어 정보 무검증',
  'SNS상에 떠도는 확인되지 않은 루머·주장·음모론을 사실 확인 절차 없이 그대로 보도하는 행위. 언론이 검증 없이 보도하면 가짜뉴스 확산을 부추기고 언론의 권위를 빌려 검증되지 않은 정보에 신뢰성을 부여한다. (예: ''유명 식당 OOO, 손님이 남긴 반찬 재사용 논란… 온라인 발칵'' 같이 익명 게시글을 검증 없이 인용)',
  '온라인 커뮤니티에 따르면, SNS에 올라온 글, 익명 게시판, 네티즌은 발칵, 누리꾼 발끈, 댓글창은 술렁',
  '사실 검증과 출처',
  '소셜미디어 활용 윤리',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-1-c: SNS 사생활 침해·2차 가해 [인권·윤리 > 소셜미디어 활용 윤리]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-1-c',
  'SNS 사생활 침해·2차 가해',
  '특정 개인(특히 비공인)을 비난의 표적으로 삼아 신상 정보(얼굴·이름·SNS 계정·직장)를 기사에 노출하거나, 유추 가능 단서를 제공하여 대중의 집단 괴롭힘을 유도하는 행위. (예: 피해자의 SNS 마지막 게시물 공개로 사이버 불링 확산)',
  '마지막 게시물에는, SNS 계정에서, 프로필에는, 피해자 SNS, 친구 추가, 인스타그램 사진',
  '인권·윤리',
  '소셜미디어 활용 윤리',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-1'),
  TRUE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-2-a: 하이퍼링크 오남용 [언어·표현 > 디지털 플랫폼 특유 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-2-a',
  '하이퍼링크 오남용',
  '관련성 없는 링크를 과도하게 삽입하여 독자 혼란을 야기하거나 SEO 목적의 광고성 링크를 과다 배치하는 행위. 디지털 환경 메타데이터 영역으로 본문 단독 감지 불가, I-트랙.',
  '관련 링크, 더보기, 추천 기사 과도 (메타데이터 영역, 본문 단독 감지 불가)',
  '언어·표현',
  '디지털 플랫폼 특유 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-2-b: 알고리즘 최적화 유인 보도 [언어·표현 > 디지털 플랫폼 특유 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-2-b',
  '알고리즘 최적화 유인 보도',
  '검색엔진 최적화(SEO)만 고려한 기사 작성 행위. 인기 검색어를 무리하게 끼워 넣거나 콘텐츠 본질보다 알고리즘 노출을 우선시하는 패턴. 디지털 환경 메타데이터 영역으로 I-트랙.',
  'SEO, 검색어 최적화, 인기 키워드 끼워넣기 (메타데이터 영역, 본문 단독 감지 불가)',
  '언어·표현',
  '디지털 플랫폼 특유 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-2-c: 가짜뉴스 확산 방지 소홀 [언어·표현 > 디지털 플랫폼 특유 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-2-c',
  '가짜뉴스 확산 방지 소홀',
  '허위정보 검증 및 대응 미흡으로 가짜뉴스 확산을 방지하지 못하는 보도. 외부 정보 비교·메타데이터 필요로 본문 단독 감지 불가, I-트랙.',
  '허위정보 미검증, 가짜뉴스 무대응 (외부 비교 필요, 본문 단독 감지 불가)',
  '언어·표현',
  '디지털 플랫폼 특유 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-2-d: 포털 환경 악용(반복 업로드) [언어·표현 > 디지털 플랫폼 특유 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-2-d',
  '포털 환경 악용(반복 업로드)',
  '조회수 증가를 위해 동일한 기사를 반복 업로드하거나 약간의 수정만으로 새 기사처럼 발행하는 어뷰징 행위. 디지털 플랫폼 환경 분석 필요로 본문 단독 감지 불가, I-트랙.',
  '동일 기사 재게시, 약간의 수정만, 어뷰징 (디지털 환경 분석 필요, 본문 단독 감지 불가)',
  '언어·표현',
  '디지털 플랫폼 특유 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- 7-2-e: UI/레이아웃 위장 광고 [언어·표현 > 디지털 플랫폼 특유 문제]
INSERT INTO public.patterns
  (code, name, description, search_text,
   category, subcategory, hierarchy_level, parent_pattern_id,
   is_active, detection_strategy, is_meta_pattern, locale)
VALUES (
  '7-2-e',
  'UI/레이아웃 위장 광고',
  '홈페이지에서 ''핫뉴스'', ''관련기사'' 등 기사 목록과 동일한 디자인 서식(UI)을 사용하여 광고를 기사처럼 위장, 독자의 오인을 유도하는 행위. UI/레이아웃 분석 필요로 본문 단독 감지 불가, I-트랙.',
  '위장 광고, 핫뉴스 디자인, 관련기사 디자인, 광고 배너를 기사처럼 (UI 분석 필요, 본문 단독 감지 불가)',
  '언어·표현',
  '디지털 플랫폼 특유 문제',
  3,
  (SELECT id FROM public.patterns WHERE code = '7-2'),
  FALSE,
  'vector',
  FALSE,
  'ko-KR'
) ON CONFLICT (code) DO NOTHING;

-- ============================================================
-- 검증 쿼리
-- ============================================================

-- 전체 leaf 카운트
SELECT hierarchy_level, COUNT(*) FROM public.patterns
WHERE hierarchy_level = 3 GROUP BY hierarchy_level;
-- 예상: hierarchy_level=3, count=107 (또는 기존 INSERT 후 누적)

-- is_active 분포
SELECT is_active, detection_strategy, COUNT(*) FROM public.patterns
WHERE hierarchy_level = 3 GROUP BY is_active, detection_strategy ORDER BY 1, 2;
-- 예상: TRUE/structural=12, TRUE/vector=64, FALSE/vector=31  (총 107)

-- 카테고리 분포
SELECT category, COUNT(*) FROM public.patterns
WHERE hierarchy_level = 3 GROUP BY category ORDER BY category;
