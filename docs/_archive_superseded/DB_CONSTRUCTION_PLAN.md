# CR-Check 서비스 확장 및 DB 구축 계획 (Supabase 기반)

## 1. 기획 의도 및 서비스 확장 제안

현재 CR-Check는 단일성 "도구"로 동작하고 있습니다. 이를 "플랫폼"으로 확장하고 데이터베이스를 도입함으로써 다음과 같은 가치를 창출할 수 있습니다.

### A. 개인화 서비스 (Personal Archive)
- **나의 분석 기록**: 사용자가 자신이 분석했던 기사들의 리포트를 저장하고 언제든 다시 열람할 수 있습니다.
- **스크랩북**: 나중에 읽거나 참고하기 위해 분석 결과와 원본 기사를 저장합니다.
- **윤리 노트**: 학생이나 기자 지망생이 분석 리포트에 자신의 생각이나 메모를 덧붙여 공부 자료로 활용합니다.

### B. 미디어 리터러시 데이터베이스 (Public & Stats)
- **실시간 트렌드**: 현재 사람들이 가장 많이 분석하고 있는 뉴스가 무엇인지 보여줍니다. (예: "실시간 CR 핫이슈")
- **언론사/기자 윤리 대시보드**: 누적된 분석 데이터를 기반으로, 특정 언론사나 기자가 자주 지적받는 윤리 위반 유형(예: 익명 취재원 남발, 제목 낚시 등)을 통계로 시각화합니다. **(이는 매우 강력한 기능이 될 것입니다)**
- **위반 유형 백과사전**: AI가 찾아낸 실제 기사 사례들을 윤리 규범 조항별로 모아서 보여줍니다. (예: "상관관계를 인과관계로 왜곡한 사례 모음")

### C. 참여형 기능 (Community & Feedback)
- **분석 피드백**: AI의 분석 결과에 대해 사용자가 "동의함", "동의하지 않음" 투표를 하거나 의견을 남겨, AI 모델을 개선하는 데이터로 활용합니다.
- **베스트 리포트**: 훌륭하게 분석된 리포트를 메인에 큐레이션하여 사용자들의 관심을 유도합니다.

---

## 2. 데이터베이스 설계 (Supabase / PostgreSQL)

Supabase는 **PostgreSQL** 기반이며, 인증(Auth)과 DB를 통합 제공하므로 본 프로젝트에 최적입니다. 무료 티어로도 충분한 시작이 가능합니다.

### ERD (Entity Relationship Diagram) 구조 제안

#### 1. 사용자 (User Management)
Supabase Auth가 기본 관리하지만, 추가 정보를 위해 `profiles` 테이블을 만듭니다.

- **`profiles`**
  - `id` (UUID, PK): Supabase Auth의 user.id와 1:1 매칭
  - `nickname` (Text): 닉네임
  - `role` (Text): 'user' | 'admin' (나중에 관리자 기능을 위해)
  - `created_at` (Timestamp)

#### 2. 기사 및 분석 데이터 (Core Data)
중복 분석을 방지하고 통계를 내기 위해 **기사 정보**와 **분석 결과**를 분리합니다.

- **`articles`** (기사 원본 메타데이터)
  - `id` (BigInt, PK)
  - `url` (Text, Unique): 기사 URL (중복 방지 핵심)
  - `title` (Text): 기사 제목
  - `publisher` (Text): 언론사명 (통계용)
  - `journalist` (Text): 기자명 (통계용)
  - `publish_date` (Timestamp): 기사 작성일
  - `created_at` (Timestamp): 최초 분석 시점

- **`analysis_results`** (AI 분석 결과)
  - `id` (BigInt, PK)
  - `article_id` (FK -> articles.id)
  - `user_id` (FK -> profiles.id, Nullable): 로그인한 유저가 분석했으면 기록, 비로그인이면 Null
  - `comprehensive_report` (Text): 시민용 리포트 전체 텍스트
  - `journalist_report` (Text): 기자용 리포트
  - `student_report` (Text): 학생용 리포트
  - `model_version` (Text): 분석에 사용된 모델 (예: 'claude-3-5-sonnet')
  - `duration` (Float): 분석 소요 시간
  - `created_at` (Timestamp)

#### 3. 사용자 활동 (User Interaction)

- **`bookmarks`** (스크랩북)
  - `id` (BigInt, PK)
  - `user_id` (FK -> profiles.id)
  - `analysis_id` (FK -> analysis_results.id)
  - `memo` (Text): 사용자 메모
  - `created_at` (Timestamp)

- **`feedbacks`** (AI 성능 개선용)
  - `id` (BigInt, PK)
  - `analysis_id` (FK -> analysis_results.id)
  - `user_id` (FK, Nullable)
  - `rating` (Int): 1~5점
  - `comment` (Text): "이 부분은 오분석 같습니다" 등의 의견

---

## 3. 구축 및 개발 로드맵

### Phase 1: 아카이빙 시작 (현재 단계에서 즉시 적용 가능)
로그인 기능이 없더라도, 백엔드에서 분석이 완료될 때마다 DB에 결과를 저장하기 시작합니다.
*   **목표**: 데이터 쌓기 (통계를 위한 기초 자산)
*   **작업**:
    1.  Supabase 프로젝트 생성.
    2.  `articles`, `analysis_results` 테이블 생성.
    3.  FastAPI 백엔드(`main.py` 또는 `analyzer.py`)에서 분석 성공 시 Supabase로 데이터 Insert.

### Phase 2: 사용자 계정 및 개인화 (소셜 로그인 도입)
프론트엔드에 로그인 기능을 붙이고, '내 기록' 기능을 만듭니다.
*   **목표**: 사용자 리텐션(재방문) 증가
*   **작업**:
    1.  Next.js에 Supabase Auth 연동 (Google, Kakao 로그인).
    2.  로그인한 사용자가 분석 요청 시, 백엔드에 `user_id`를 전달하여 분석 결과와 매핑.
    3.  마이페이지 개발: `SELECT * FROM analysis_results WHERE user_id = :current_user`

### Phase 3: 인사이트 및 통계 (데이터 활용)
쌓인 데이터를 시각화하여 보여줍니다.
*   **목표**: 서비스의 공익적 가치 극대화
*   **작업**:
    1.  언론사별 분석 횟수 랭킹 쿼리 작성.
    2.  메인 페이지에 "오늘의 분석 트렌드" 섹션 추가.

---

## 4. 기술적 구현 팁 (CR-Check 맞춤)

**1. 하이브리드 접근 (Backend + Frontend)**
CR-Check는 Next.js(프론트)와 FastAPI(백엔드)가 분리되어 있습니다. Supabase는 양쪽 모두에서 접근 가능합니다.

*   **FastAPI (Backend)**: `analysis_results` 테이블에 **쓰기(Insert)** 권한을 가집니다. 분석이 끝나면 결과를 저장합니다. (Service Role Key 사용)
*   **Next.js (Frontend)**: `analysis_results` 테이블에서 **읽기(Select)** 권한을 가집니다. 사용자가 자신의 기록을 보거나, 랭킹을 볼 때 사용합니다. (Anon Key + RLS 정책 사용)

**2. RLS (Row Level Security) 설정**
Supabase의 강력한 기능인 RLS를 통해 보안을 설정해야 합니다.
*   `analysis_results`: 본인이 생성한 데이터만 볼 수 있게 하거나, '공개'로 설정된 데이터는 누구나 볼 수 있게 설정 가능.

---

## 5. 요약: 당장 무엇을 해야 하나요?

주변 분들과 상의하실 때 이 3가지를 결정하시면 됩니다.

1.  **"우리가 사용자들의 분석 이력을 저장해도 될까?"** (개인정보 및 프라이버시 이슈 검토) -> 보통은 '익명화된 통계'용으로는 저장하고, '개인 기록'은 동의 하에 저장합니다.
2.  **"어떤 통계를 보여주고 싶은가?"** -> 언론사 줄세우기가 될 수도 있어 민감할 수 있습니다. 긍정적인 방향(우수 보도 사례)을 강조할지 고민이 필요합니다.
3.  **"로그인이 꼭 필요한가?"** -> 로그인은 진입 장벽이 됩니다. 비로그인 상태에서도 핵심 기능(분석)은 유지하되, '저장'하려면 로그인하게 하는 '소프트 월(Soft Wall)' 전략을 추천합니다.
