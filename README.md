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
- 🧠 **Hybrid RAG**: 벡터 검색 + 관계형 DB로 38개 보도관행 패턴 식별, 375개 윤리규범 조항 DB 정확 인용 (Phase H에서 119개 패턴으로 세분화 진행 중)

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
  ⑤ DB 검증 → 윤리코드 조회 (재귀 CTE + REST 폴백) [메타패턴 추론: 비활성화]
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

## 개발 방식 — 인간-AI 협업 구조

이 프로젝트는 처음부터 끝까지 **한 명의 기획자와 여러 AI 도구의 협업**으로 구축됐습니다.
코드 한 줄, 데이터베이스 설계 하나도 기획자의 판단과 승인 없이 자동으로 진행된 것은 없습니다.

| 역할 | 주체 |
|------|------|
| 기획·큐레이션·최종 결정 | 기획자, 감나무 |
| 설계 감독 · 단계별 가이드 | Claude.ai (Claude Sonnet) |
| 코드 작성 · 실행 | Claude Code CLI |
| 독립 감리 | Antigravity · Gemini · Manus · Perplexity · ChatGPT · NotebookLM |

감리는 단순 검토가 아닙니다. 동일한 프롬프트를 여러 AI에게 독립적으로 제출하고 결과를 교차 검증하여, 어느 한 AI의 판단에 의존하지 않는 방식으로 운영됩니다.

이 구조 자체가 CR-Project의 실험 중 하나입니다. **단독 개발자도, 대형 팀도 아닌 '한 명 + AI 앙상블'이 공익 도구를 만들 수 있다는 것을 증명하는 과정**이기도 합니다. 이 리포지토리를 포크해서 다른 언어·다른 맥락에 맞게 발전시키는 것을 환영합니다.

## 라이선스

GNU Affero General Public License v3.0 (AGPL-3.0).
시민 주도 언론 비평 생태계의 투명성과 무결성을 보장하기 위해 채택했습니다.

## 문의

GitHub Issues 또는 gamnamu2915@gmail.com

---

**CR-Check** — 더 나은 언론을 위한 시민 주도 언론윤리 분석 도구
