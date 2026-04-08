# CR-Check

**AI 기반 한국어 뉴스 기사 품질 분석 플랫폼**

> CR-Project(시민 주도 언론개혁 이니셔티브)의 핵심 도구.
> 시민이 뉴스 URL을 입력하면 저널리즘 윤리 기준에 근거한 분석 리포트를 생성합니다.

**프로덕션**: https://cr-check.vercel.app

---

## 주요 기능

- 📰 **기사 분석**: URL 입력만으로 한국어 뉴스 기사의 저널리즘 윤리 자동 분석
- 📊 **3종 리포트**: 시민용, 기자용, 학생용(초등 4~5학년 눈높이) 리포트 생성
- 🔗 **공유 URL**: 분석 결과를 고유 링크로 공유 (`/report/{share_id}`)
- 🚫 **NO SCORING**: 점수·등급 없이 서술형 비평만 제공 — "관점을 제시하는 도구"
- 🧠 **Hybrid RAG**: 벡터 검색 + 관계형 DB로 119개 보도관행 패턴 식별, 14개 윤리규범 정확 인용

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Database | Supabase (PostgreSQL 15+, pgvector) |
| Backend | FastAPI + httpx + supabase-py |
| Frontend | Next.js 15 (App Router, TypeScript) |
| AI (패턴 식별) | Claude Sonnet 4.5 (Devil's Advocate CoT) |
| AI (리포트 생성) | Claude Sonnet 4.6 (3종 리포트 + 〔〕규범 인용) |
| AI (임베딩) | OpenAI text-embedding-3-small (1536차원) |
| 배포 | Railway (BE) + Vercel (FE) |


## 분석 파이프라인

```
POST /analyze { url }
  ① URL 정규화 → DB 캐시 조회 → 캐시 히트 시 즉시 반환
  ② 캐시 미스 → 기사 스크래핑 → 시맨틱 청킹 (300~500자, 노이즈 제거)
  ③ OpenAI 임베딩 → Supabase 벡터 검색 (패턴 후보)
  ④ Phase 1: Sonnet 4.5 Solo (패턴 식별 + Devil's Advocate CoT)
  ⑤ DB 검증 → 메타패턴 추론 → 윤리코드 조회 (재귀 CTE + REST 폴백)
  ⑥ Phase 2: Sonnet 4.6 (3종 리포트 생성, 〔〕마커 자연 인용)
  ⑦ DB 저장 (articles + analysis_results + share_id 발급)
```

## 로컬 개발

### 사전 요구사항

- Python 3.11+, Node.js 18+
- Anthropic API 키, OpenAI API 키
- Supabase 로컬 또는 클라우드 프로젝트

### 백엔드

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # API 키 설정
uvicorn main:app --reload --port 8080
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

## API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `POST /analyze` | 기사 URL → 3종 리포트 + share_id 반환 |
| `GET /report/{share_id}` | 저장된 분석 결과 조회 (PostgREST JOIN) |
| `GET /health` | 서버 상태 + API 키 설정 확인 |

## 프로젝트 구조

```
cr-check/
├── backend/core/           # 파이프라인 핵심 모듈
│   ├── pipeline.py         # 오케스트레이터
│   ├── pattern_matcher.py  # Phase 1: Sonnet 4.5 Solo
│   ├── report_generator.py # Phase 2: Sonnet 4.6 3종 리포트
│   ├── meta_pattern_inference.py  # 메타 패턴 추론
│   ├── storage.py          # 캐시 + DB 저장 + URL 정규화
│   ├── chunker.py          # 시맨틱 청킹
│   └── db.py               # Supabase 연결 (로컬/클라우드 분기)
├── frontend/
│   ├── app/                # Next.js App Router
│   │   ├── report/[id]/    # 공유 URL 페이지
│   │   └── result/         # 분석 결과 페이지
│   └── components/
│       ├── ResultViewer.tsx # 3종 탭 리포트 렌더러
│       └── CachedBanner.tsx
├── docs/                   # 설계 문서 + 데이터셋
├── supabase/migrations/    # DB 마이그레이션 (SSoT)
└── scripts/                # 벤치마크 + 임베딩 생성
```

## 라이선스

GNU Affero General Public License v3.0 (AGPL-3.0).
시민 주도 언론 비평 생태계의 투명성과 무결성을 보장하기 위해 채택했습니다.

## 문의

GitHub Issues 또는 gamnamu2915@gmail.com

---

**CR-Check** — 더 나은 언론을 위한 시민 주도 언론윤리 분석 도구
