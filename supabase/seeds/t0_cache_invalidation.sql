-- =====================================================================
-- T0 재분석 대상 3건 캐시 무효화 (Wave 1.1 — Phase B 준비)
-- [실행 방식 경고] 이 파일은 기획자가 Supabase SQL Editor에서 "수동" 실행한다.
-- CLI(`supabase db push` 등)로 실행 금지.
-- =====================================================================

-- (a) 대상 확인 — 기획자가 결과를 눈으로 확인한 뒤 (b) 실행
SELECT ar.id AS analysis_id, a.id AS article_id, a.title, ar.created_at
FROM analysis_results ar JOIN articles a ON a.id = ar.article_id
WHERE a.title LIKE '%문명사회%'
   OR a.title LIKE '%중국인%'
   OR a.title LIKE '%외국인보호소%';

-- (b) 기획자 확인 후, 위에서 확인한 analysis_id만 개별 삭제
-- DELETE FROM analysis_results WHERE id = <analysis_id>;
-- ※ articles 행은 삭제하지 않는다 (on_conflict=url UPSERT라 재분석 시 안전 병합)
