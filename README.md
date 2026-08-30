# CR-Check

**AI 기반 한국어 뉴스 기사 품질 분석 플랫폼**

> 시민이 뉴스 URL을 입력하면 언론윤리 규범에 근거한 분석 리포트를 생성합니다.
> 119개 문제적 보도관행 패턴에서 출발해 정제된 세부 패턴과, 언론인들이 작성한 언론윤리규범 조항들을 결합해 판단 근거로 삼습니다.

**프로덕션**: https://cr-check.kr

---

## 주요 기능

- 📰 **기사 분석**: URL 입력만으로 한국어 뉴스 기사의 제목·본문·메타데이터를 추출해 저널리즘 윤리 관점에서 자동 분석
- 🔎 **문제적 보도관행 탐지**: 기사 안의 구체적 문장을 근거로 삼는 vector 패턴과, 반론 부재·취재원 편중처럼 특정 문장으로 인용하기 어려운 structural 패턴을 함께 검토
- 🪞 **제목-본문 대조**: 제목이 본문의 주어·조건·맥락을 삭제하거나 과장하는지 별도로 검토
- 📊 **3종 리포트**: 시민용, 기자용, 학생용(초등 4~5학년 눈높이) 리포트 생성
- 🔗 **공유 URL**: 분석 결과를 고유 링크로 공유 (`/report/{share_id}`)
- 🚫 **NO SCORING**: 점수·등급 없이 근거가 드러나는 서술형 비평만 제공 — "관점을 제시하는 도구"
- 🧠 **Hybrid RAG**: 벡터 검색 + 관계형 DB로 8개 대분류 아래 107개 세부 보도관행 패턴(76개 런타임 활성) 식별, 394개 윤리규범 조항을 계층 롤업까지 포함해 정확히 인용
- 🔍 **인용 감사 (Citation Audit)**: 리포트가 실제로 인용한 규범이 제공된 규범 목록과 정확히 일치하는지 자동 검증 — 관측 전용이라 실패해도 리포트 본문은 항상 보존

## 분석 원칙

CR-Check는 기사에 점수나 등급을 매기지 않습니다. 대신 "이 기사에서 독자가 주의 깊게 살펴볼 지점은 무엇이고, 그 판단은 어느 문장·구조에서 비롯되며, 어떤 윤리규범과 연결되는가"에 답할 수 있는 근거를 제공합니다.

1. **판정보다 근거** — 문제 패턴은 기사 안에서 확인할 수 있는 제목 표현, 문장, 인용, 수치 또는 구조적 부재를 근거로만 선택합니다.
2. **패턴 식별과 규범 조회의 분리** — 먼저 기사에서 문제적 보도관행을 식별하고, 그다음 확정된 패턴에 연결된 윤리규범을 DB에서 조회합니다. 모델이 기사에 맞춰 규범을 임의로 창작하거나 자유롭게 선택하지 못하도록 두 단계를 분리했습니다.
3. **가장 구체적인 leaf 코드 사용** — 상위 범주나 부모 코드 대신, 현재 활성 카탈로그에 있는 가장 구체적인 leaf 패턴만 최종 결과로 허용합니다. 부모·비활성·메타 패턴과 카탈로그에 없는 코드는 검증 단계에서 제거됩니다.
4. **불확실성의 명시** — 모든 탐지에는 확신 수준이 함께 표시됩니다.
   - `high`: 기사 안의 근거가 분명한 경우 — 단정형 서술
   - `medium`: 상당한 개연성과 구체적 근거가 있는 경우 — 절제된 판단과 근거 병기
   - `low`: 독자가 추가로 확인해볼 가치가 있는 유보적 질문 — "~로 읽힐 수 있다" 식의 유보형 서술
5. **점수화하지 않는 비평** — 같은 문제가 기사 전체에서 차지하는 의미는 주제·맥락·공익성·표현 방식에 따라 달라지므로, 하나의 숫자로 환원하지 않고 근거와 설명을 중심으로 결과를 제시합니다.

## 현재 운영 데이터

2026년 7월 25일 Supabase 운영 DB 직접 확인 기준입니다.

| 데이터 | 수 |
|---|---:|
| 런타임 활성 leaf 패턴 | 76 |
| 언론윤리규범 조항 | 394 |
| 패턴-윤리규범 직접 관계 | 287 |
| 규범 계층 보조 관계 | 42 |

정확한 수치는 패턴·규범 데이터 큐레이션과 마이그레이션에 따라 계속 바뀝니다.

## Hybrid RAG 구조

CR-Check의 RAG는 단순 벡터 검색만으로 구성되지 않습니다.

**문제 패턴 지식층** — `patterns` 테이블은 코드·이름·판단 기준·탐지 전략·계층 관계·리포트 서술 방향·활성 상태·임베딩을 함께 저장합니다. 패턴은 두 방식으로 검토됩니다.

- *Vector 패턴*: 기사 청크 임베딩과 패턴 임베딩을 비교해 관련성 높은 패턴을 후보(★)로 제시합니다. 벡터 후보는 참고 신호일 뿐 최종 판정이 아닙니다.
- *Structural 패턴*: 반론 부재, 취재원 편중, 맥락 누락처럼 특정 문장을 그대로 인용하기 어려운 패턴입니다. 벡터 후보 여부와 관계없이 기사 전체 구조를 읽어 항상 검토합니다.

**윤리규범 지식층** — `ethics_codes`에는 한국의 일반 언론윤리규범과 분야별 보도준칙 14종이 저장돼 있습니다: 언론윤리헌장, 기자윤리강령, 기자윤리실천요강, 신문윤리강령, 신문윤리실천요강, 인권보도준칙, 자살보도 윤리강령, 자살예방 보도준칙, 재난보도준칙, 감염병보도준칙, 선거여론조사보도준칙, 군 취재·보도 기준, 평화통일 보도 준칙, 혐오표현 반대 미디어 실천 선언.

확정된 패턴은 `pattern_ethics_relations`로 관련 규범과 연결되고, `parent_code_id`를 따라 상위 윤리 원칙으로 롤업될 수 있습니다. 관련성이 약한 `weak` 관계와 예외 관계는 기본 인용 대상에서 제외됩니다.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Database | Supabase (PostgreSQL 17, pgvector) |
| Backend | FastAPI + httpx + supabase-py |
| Frontend | Next.js 15 (App Router, TypeScript) |
| Phase 1 (패턴 식별) | Claude Sonnet 4.6 |
| Phase 2 (리포트 생성) | Claude Sonnet 5 |
| Embedding | OpenAI text-embedding-3-small (1536차원) |
| Backend 배포 | Railway |
| Frontend 배포 | Vercel |

## 배포

프론트엔드는 Vercel, 백엔드는 Railway에 배포되며, `main` 브랜치에 병합되면 각각 자동으로 재배포됩니다.

**CORS 제약** — 브라우저가 백엔드 API를 직접 호출하는 구조이므로, 새 도메인을 연결할 때는 `backend/main.py`의 `allow_origins`에도 그 오리진을 등록해야 합니다. 누락하면 페이지는 열리지만 분석과 리포트 조회가 모두 CORS로 차단됩니다.

## 분석 파이프라인

```
POST /analyze { url }

① URL 정규화 → 기존 분석 캐시 조회, 캐시 히트 시 즉시 반환
② 기사 스크래핑 (제목·본문·언론사·기자명·발행일)
③ 시맨틱 청킹 (실패 시 기사 전체를 단일 청크로 사용)
④ OpenAI 임베딩 생성 (text-embedding-3-small, 1536차원)
⑤ Supabase 벡터 검색 → 청크별 관련 패턴 후보 수집
⑥ Phase 1: Sonnet 4.6 — 활성 leaf 카탈로그 전체 검토,
   vector/structural 탐지 전략 구분, 혼동 쌍 구분 기준 적용,
   matched_text · reasoning · severity · pattern_code 생성
⑦ 결정론적 패턴 검증 — DB 미존재 코드 · 부모 코드 · 비활성 코드 · 메타 패턴 제거
⑧ 윤리규범 조회 — get_ethics_for_patterns RPC, 기사 맥락 필터,
   weak · exception 관계 제외, 상위 규범 parent-chain 롤업
⑨ Phase 2: Sonnet 5 — 3종 리포트 생성(시민용·기자용·학생용), 〔〕마커 자연 인용
⑩ 검증 및 저장 — citation audit, phase1 포렌식, articles/analysis_results/
   analysis_ethics_snapshot 저장, share_id 발급
```

## 현재 활성 기능과 비활성 기능

저장소에는 비교 실험과 이전 구조를 위한 코드가 일부 보존돼 있습니다. 파일이 존재한다는 것이 곧 현재 런타임에서 쓰인다는 뜻은 아닙니다.

**활성**

| 기능 | 상태 |
|---|---|
| Sonnet Solo 기반 Phase 1 패턴 식별 | 활성 |
| 벡터 후보 검색 + 전체 활성 leaf 카탈로그 검토 | 활성 |
| vector/structural 탐지 전략 구분 | 활성 |
| 패턴 혼동 쌍 구분 가이드 | 활성 |
| 제목-본문 대조 | 활성 |
| 런타임 leaf 코드 검증 | 활성 |
| 기사 맥락별 규범 조회 + parent-chain 롤업 | 활성 |
| Sonnet 5 기반 3종 리포트, 규범 직접 서술 | 활성 |
| Citation Audit | 활성 |
| Phase 1 포렌식 저장 | 활성 |
| 캐시 및 공유 URL | 활성 |

**비활성 · 레거시**

| 기능 | 상태 |
|---|---|
| Devil's Advocate CoT 절차 | 현재 Phase 1에서 비활성 |
| 메타 패턴 추론 | 비활성 (2026-04, `inferred_by` 관계 데이터 부재로 운용 불가 — 재활성화 시 주석 해제) |
| 구형 Haiku → Sonnet 2-Call 경로 | 레거시 코드로 분리 (`pattern_matcher_legacy.py`) |
| 구형 단일 게이트 방식 | 레거시 코드로 분리 |
| CitationResolver의 `<cite>` 후치환 | 비활성 (현재는 Phase 2가 규범을 직접 서술) |
| PDF 내보내기 API | 비활성 |

메타 패턴과 레거시 코드는 향후 데이터가 충분히 쌓이거나 비교 실험이 필요할 때를 대비해 저장소에 보존돼 있습니다.

## 인용과 검증

Phase 2 모델에는 확정된 패턴에 연결된 윤리규범 원문만 제공됩니다. 모델은 이 규범을 리포트 문장 안에 직접 서술하며, 현재 파이프라인은 별도의 인용 후치환 과정을 거치지 않습니다.

생성 이후 `citation_audit`이 다음을 관측 전용으로 검사합니다.

- 모델에 제공된 허용 규범 목록
- 리포트별 실제 규범 인용
- 허용 목록과 일치한 인용 / 일치하지 않은 인용
- 리포트 유형별 인용 일치율

검사 로직이 실패하더라도 생성된 리포트 본문은 항상 보존되고, 감사 오류만 별도로 기록됩니다.

## 로컬 개발

### 사전 요구사항

- Python 3.11+, Node.js 18+
- Anthropic API 키, OpenAI API 키
- Supabase 로컬 또는 클라우드 프로젝트

### 백엔드

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

환경변수는 `backend/.env` 또는 저장소 루트의 `.env`에 설정합니다.

| 변수 | 용도 |
|---|---|
| `ANTHROPIC_API_KEY` | Phase 1·2 모델 호출 |
| `OPENAI_API_KEY` | 임베딩 생성 |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | DB 접근 |

### 프론트엔드

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

| 변수 | 용도 |
|---|---|
| `NEXT_PUBLIC_API_URL` | 백엔드 API 주소 (기본 `http://localhost:8000`) |
| `NEXT_PUBLIC_SITE_URL` | 사이트 절대 URL. 미설정 시 `lib/site.ts`의 기본값 사용 |
| `NEXT_PUBLIC_ANALYSIS_TIMEOUT` | 분석 타임아웃 ms (기본 300000) |

`NEXT_PUBLIC_*` 값은 빌드 시점에 번들로 치환됩니다. 배포 플랫폼 대시보드에서 값을 바꾼 뒤에는 재배포해야 반영되며, 대시보드에 값이 있으면 코드의 기본값보다 우선합니다.

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|---|---|---|
| `GET` | `/` | API 기본 상태 |
| `GET` | `/health` | 서버 상태 + API 키 설정 확인 |
| `POST` | `/analyze` | 기사 URL → 3종 리포트 + share_id 반환 |
| `GET` | `/report/{share_id}` | 저장된 분석 결과 조회 (PostgREST JOIN) |

응답 구조 예시:

```json
{
  "article_info": { "title": "기사 제목", "url": "https://..." },
  "reports": {
    "comprehensive": "시민용 리포트",
    "journalist": "기자용 리포트",
    "student": "학생용 리포트"
  },
  "share_id": "Ab12CdEf3GhI",
  "analyzed_at": "2026-07-25T12:00:00Z",
  "is_cached": false
}
```

## 프로젝트 구조

```
cr-check/
├── backend/
│   ├── main.py                       # FastAPI 엔드포인트
│   ├── scraper.py                    # 기사 스크래핑
│   ├── requirements.txt
│   └── core/
│       ├── pipeline.py               # 오케스트레이터
│       ├── pattern_matcher.py        # Phase 1: Sonnet 4.6 Solo 패턴 식별
│       ├── pattern_matcher_legacy.py # 구형 비교 경로 (비활성)
│       ├── report_generator.py       # Phase 2: Sonnet 5, 3종 리포트
│       ├── verify_citations.py       # 인용 감사 — 관측 전용
│       ├── citation_resolver.py      # 인용 후치환 (비활성)
│       ├── meta_pattern_inference.py # 메타 패턴 추론 (비활성)
│       ├── storage.py                # 캐시 + DB 저장 + URL 정규화
│       ├── chunker.py                # 시맨틱 청킹
│       └── db.py                     # Supabase 연결 (로컬/클라우드 분기)
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                # 루트 레이아웃 + 사이트 메타데이터
│   │   ├── page.tsx                  # 기사 URL 입력 화면
│   │   ├── robots.ts                 # robots.txt 생성
│   │   ├── sitemap.ts                # sitemap.xml 생성 (홈만 포함)
│   │   ├── report/[id]/
│   │   │   ├── layout.tsx            # 공유 리포트 메타데이터 (canonical, noindex)
│   │   │   └── page.tsx              # 공유 URL 페이지
│   │   └── result/
│   │       ├── layout.tsx            # 결과 화면 noindex 선언
│   │       └── page.tsx              # 분석 결과 페이지
│   ├── components/
│   │   ├── ResultViewer.tsx          # 3종 탭 리포트 렌더러
│   │   └── CachedBanner.tsx
│   └── lib/
│       ├── api/                      # 백엔드 호출
│       ├── constants/
│       ├── config.ts                 # API URL 등 설정
│       ├── shareTitle.ts             # SNS 공유용 기사 제목 축약
│       └── site.ts                   # 사이트 URL 단일 진실 공급원
├── docs/                              # 설계 문서 + 데이터셋
├── supabase/migrations/               # DB 마이그레이션 (SSoT)
└── scripts/                           # 벤치마크 + 임베딩 생성
```

## 주요 DB 테이블

| 테이블 | 역할 |
|---|---|
| `patterns` | 문제적 보도관행 패턴과 탐지 메타데이터 |
| `pattern_confusion_pairs` | 유사 패턴 간 구분 기준 |
| `ethics_codes` | 언론윤리규범 원문과 계층 정보 |
| `ethics_code_hierarchy` | 규범 간 보조 계층 관계 |
| `pattern_ethics_relations` | 패턴과 윤리규범의 직접 매핑 |
| `articles` | 분석 기사 메타데이터 |
| `analysis_results` | 3종 리포트, citation_audit, phase1_forensic 등 분석 메타데이터 |
| `analysis_ethics_snapshot` | 분석 시점에 참조한 규범 스냅샷 |
| `feedbacks` | 사용자 피드백 |

## 현재 한계

- **기사 스크래핑 의존성**: 언론사 페이지 구조, 유료 장벽, 동적 렌더링, 봇 차단 정책에 따라 본문을 가져오지 못할 수 있습니다.
- **외부 원자료의 직접 검증 제한**: 기사에 인용된 통계·연구·판결문의 원문 내용까지 자동으로 대조하는 팩트체크 시스템은 아닙니다. 기사 내부에서 확인 가능한 것을 근거로 판단합니다.
- **확률적 모델 판단**: 같은 기사도 모델 버전과 실행 조건에 따라 일부 탐지와 표현이 달라질 수 있습니다. 결과는 최종 판정이 아니라 사람이 검토할 비평 자료입니다.
- **법적 판단이 아님**: 언론중재, 명예훼손, 차별, 개인정보 보호 등에 대한 법적 판단을 대신하지 않습니다.
- **기사 밖 맥락의 한계**: 연속 보도, 지면 배치, 영상·사진 구성 등 URL 본문 밖의 편집 맥락은 충분히 반영되지 않을 수 있습니다.

## 검색 색인 정책

리포트 상세(`/report/{share_id}`)와 결과 화면(`/result`)은 메타데이터 `noindex`로 검색 색인에서 제외하며, `sitemap.xml`에는 홈만 포함합니다.

`robots.txt`에서는 크롤링을 막지 않습니다. 크롤러가 각 페이지에 도달해야 그 `noindex`를 읽을 수 있기 때문입니다. `Disallow`는 크롤링 차단이지 색인 금지가 아니며, 크롤링만 막으면 검색엔진이 내용을 읽지 못한 채 URL만 색인할 수 있습니다.

이 정책의 근거는 CR-Check가 만드는 리포트가 사람의 검수를 거치지 않은 초안이라는 점입니다. 검수를 통과한 결과를 공개하고 색인하는 역할은 자매 저장소 cr-report가 맡습니다. 접근을 통제하는 장치가 아니라, 검수 전 결과를 검색엔진에 적극 유통하지 않는다는 편집 정책입니다.

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

GitHub Issues 또는 cr@cr-project.org

---

**CR-Check** — 신뢰 받는 언론을 위한 시민 주도 언론윤리 분석 도구