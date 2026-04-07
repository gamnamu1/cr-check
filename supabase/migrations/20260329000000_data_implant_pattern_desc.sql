-- M5 Data Implant: 패턴 description 보강
-- 벡터 검색 Candidate Recall 개선을 위해 실제 기사에서 사용되는 어휘를 추가
-- ⚠️ 임베딩 재생성 필요: description 변경 후 generate_embeddings.py 재실행

BEGIN;

-- 1-7-5 차별·혐오 표현: 따옴표 저널리즘의 혐오 유통 관련 키워드 추가
UPDATE public.patterns
SET description = description || '; 따옴표 저널리즘, 막말 그대로 인용, 혐오 발언 여과 없이 보도, 차별적 발언 무비판 전달',
    updated_at = now()
WHERE code = '1-7-5';

-- 1-7-2 헤드라인 윤리 문제: 제목 관련 키워드 추가
UPDATE public.patterns
SET description = description || '; 자극적 제목, 논란 발언 제목 사용, 클릭베이트, 본문과 제목 불일치, 과장 헤드라인',
    updated_at = now()
WHERE code = '1-7-2';

COMMIT;
