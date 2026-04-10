# 안티그래비티

전반적으로 **매우 훌륭하고 치밀하게 작성된 배포 계획서**입니다. 특히 막힐 수 있는 병목 지점들(WeasyPrint 빌드 에러, db.py의 5초 타임아웃, 마이그레이션과 코드 배포의 순서)을 사전에 캐치한 점이 인상적입니다. 이대로 진행하셔도 무방할 만큼 완성도가 높습니다.

계획의 완성도를 더욱 높이기 위해, 몇 가지 **감리 의견 및 개선 제안**을 덧붙여 드립니다.

### 💡 감리 의견 및 추천 개선 사항

### 1. `db.py` 클라우드 전환 최적화 로직 개선 제안 (E-1-2 관련)

제안하신 `127.0.0.1` 문자열 필터링 방식도 훌륭합니다. 다만 휴리스틱을 줄이고 더 명시적으로 클라우드(Railway) 환경임을 확정 짓는 방법이 있습니다.
Railway는 실행 시 컨테이너에 `RAILWAY_ENVIRONMENT_NAME` (또는 `RAILWAY_PROJECT_NAME`) 같은 고유 환경 변수를 자동 주입합니다.

```python
# 수정안 응용:
def _get_supabase_config() -> tuple[str, str]:
    sb_url = os.environ.get("SUPABASE_URL", "")
    cloud_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    # Railway 환경이면 로컬 체크 없이 즉시 클라우드 반환
    if os.environ.get("RAILWAY_ENVIRONMENT_NAME") or (sb_url and "supabase.co" in sb_url):
        return sb_url, cloud_key

    # ... 이후 로컬(127.0.0.1) 폴백 로직 진행 ...
```

이렇게 하면 예기치 않은 URL 파싱 오류나 타임아웃 걱정 없이 Railway 내에서는 100% 즉각적으로 클라우드 설정을 반환하게 됩니다. (현재 작성하신 코드도 충분히 안전하므로, 둘 중 편한 방향을 선택하시면 됩니다.)

### 2. Supabase RLS(Row Level Security) 상태에 대한 코멘트 (1-2 관련)

현재 모든 테이블의 RLS가 `DISABLED`로 되어 있습니다.

- **구조적 안전성:** 프론트엔드에서 Supabase로 직접 쿼리하지 않고 **모든 데이터 처리가 FastAPI 백엔드(Service Role Key 사용)를 통해서만 이루어진다면**, RLS가 꺼져 있어도 보안상 즉각적인 치명타는 없습니다.
- **향후 권장 사항:** 프로덕션 환경의 베스트 프랙티스로는 `articles`나 `analysis_results` 등의 테이블에서 RLS를 활성화하고, 오직 `authenticated` 역할이나 `service_role` 접근만 허용하는 정책을 추가하는 것이 좋습니다. 당장 Phase E의 Blocker는 아니지만, 배포 후 안정화 단계에서 한 번 잠가주시는 걸 권장합니다.

### 3. 임베딩 스크립트 실행 환경 (E-2-3 관련)

`scripts/generate_embeddings.py`를 로컬에서 실행하여 프로덕션 DB에 연결하는 방식은 확실하고 빠릅니다. 단, 로컬 시스템의 Python 환변(주로 `.venv`)에 스크립트가 실행되기 위한 `psycopg2-binary`, `openai` 패키지가 잘 설치되어 있는지 한 번 더 확인(실행 전 `pip install psycopg2-binary openai` 실행 권장)하시면 당황하는 일 없이 매끄럽게 진행될 것입니다.

### 4. WeasyPrint 제거 (E-1-1 관련)

최고의 결정입니다. Railway의 기본 `nixpacks` 빌드 시스템에는 `pango`, `cairo` 같은 크로스플랫폼 렌더링 라이브러리가 기본 탑재되어 있지 않아 배포가 100% 실패하게 됩니다. 당장 안 쓰는 기능을 분리한 것은 배포 리스크를 없애는 훌륭한 조치입니다.

---

### 🚀 총평 및 다음 단계

**[판정: PASS - 즉시 실행 가능]**
DB 변경(E-2)을 프론트/백엔드 배포(E-4)보다 선행하도록 명시한 점이 전체 시퀀스의 핵심을 찌르고 있습니다.

계획이 이미 완벽하므로, 승인해주시면 **[Phase E-1: 코드 수정 (로컬)]** 단계부터 제가 직접 코드를 수정하여 PR 준비를 돕겠습니다.

작업을 시작할까요? (진행을 원하시면 허락해 주시면 됩니다!)