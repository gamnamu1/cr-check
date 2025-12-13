# CR-Check

**기사 언론윤리 분석 플랫폼**

## 📖 문서 읽기 순서

개발을 시작하려면 다음 순서로 읽어주세요:

1. **README.md** (현재 파일) - 프로젝트 개요 및 설치 방법
2. **[USER_FLOW.md](./USER_FLOW.md)** - 사용자 경험 설계 및 디자인 비전
3. **[IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)** - 상세 구현 가이드 및 코드

---

CR-Check는 한국 언론 기사의 저널리즘 윤리 준수 여부를 정성적으로 분석하는 자동화 도구입니다. 119개의 문제적 보도 관행 패턴을 기반으로 기사를 분석하고, 점수화 없이 서술형 리포트를 제공합니다.

## 주요 기능

- 📰 **기사 분석**: 스트레이트 뉴스와 해설 기사의 저널리즘 윤리 자동 분석
- 📊 **3가지 리포트**: 시민을 위한 리포트, 기자를 위한 리포트, 학생을 위한 리포트 생성
- 🚫 **NO SCORING**: 점수나 등급 표시 없이 윤리규범 기반 정성 평가
- ⚡ **하이브리드 AI 전략**: Phase 1(Haiku)에서 빠른 패턴 식별, Phase 2(Sonnet)에서 상세 리포트 생성
- 🎨 **사용자 친화적 UI**: 탭 방식의 직관적인 리포트 표시

## 기술 스택

### 백엔드
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Anthropic Claude**: 기사 분석을 위한 AI 모델
  - Claude Haiku 4.5: 빠른 패턴 식별 (Phase 1)
  - Claude Sonnet 4.5: 안정적인 리포트 생성 (Phase 2)
- **BeautifulSoup4**: 기사 스크래핑
- **WeasyPrint**: PDF 변환 (향후 기능)

### 프론트엔드
- **Next.js 15**: React 기반 프레임워크 (App Router)
- **TypeScript**: 타입 안전성
- **TailwindCSS 3**: 유틸리티 기반 CSS 프레임워크
- **React 18**: UI 라이브러리

## 설치 방법

### 사전 요구사항

- Python 3.11 이상
- Node.js 18 이상
- Anthropic API 키 ([발급 방법](#anthropic-api-키-발급))

### 1. 저장소 클론

```bash
git clone https://github.com/gamnamu1/cr-check.git
cd cr-check
```

### 2. 환경 변수 설정

#### Anthropic API 키 발급

1. [Anthropic Console](https://console.anthropic.com/account/keys)에 접속
2. API 키 생성
3. 생성된 키 복사 (sk-ant-로 시작)

#### 백엔드 환경 변수 설정

```bash
# 방법 1: 환경 변수로 직접 설정 (권장)
export ANTHROPIC_API_KEY="sk-ant-api..."

# 방법 2: .env 파일 생성
cd backend
cp .env.example .env
# .env 파일을 열어 ANTHROPIC_API_KEY 값 입력
```

#### 프론트엔드 환경 변수 설정 (선택)

```bash
cd frontend
cp .env.example .env
# 필요 시 백엔드 API URL 수정 (기본값: http://localhost:8000)
```

### 3. 백엔드 실행

```bash
cd backend

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload

# 서버가 http://localhost:8000 에서 실행됩니다
```

### 4. 프론트엔드 실행

새 터미널 창을 열고:

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 애플리케이션이 http://localhost:3000 에서 실행됩니다
```

## 사용 방법

1. 브라우저에서 http://localhost:3000 접속
2. 분석할 기사의 URL 입력 (네이버 뉴스, 다음 뉴스, 언론사 직접 링크 등)
3. "분석하기" 버튼 클릭
4. 3가지 리포트 확인:
   - **시민을 위한 리포트 리포트**: (평가 결과 종합) 기사의 전반적인 윤리 준수 현황
   - **기자 작성자를 위한 리포트**: 개선 방향 제시
   - **학생을 위한 교육용 리포트**: 미디어 리터러시 수업 자료로 활용

## 지원하는 기사 유형

### ✅ 분석 가능
- 스트레이트 뉴스
- 해설 기사

### ❌ 분석 불가
- 칼럼
- 사설
- 인터뷰
- 리뷰
- 광고성 기사

## 프로젝트 구조

```
cr-check/
├── backend/              # FastAPI 백엔드
│   ├── main.py          # API 엔드포인트
│   ├── analyzer.py      # 기사 분석 로직 (2단계 하이브리드 전략)
│   ├── criteria_manager.py # 평가 기준 관리
│   ├── json_parser.py   # 강화된 JSON 파싱
│   ├── scraper.py       # 웹 스크래핑
│   ├── requirements.txt # Python 의존성
│   └── references/
│       └── unified-criteria.md # 통합 평가 기준 (72KB)
├── frontend/            # Next.js 15 프론트엔드
│   ├── app/            # Next.js 앱 라우터
│   │   ├── page.tsx   # 메인 페이지 (URL 입력)
│   │   ├── result/
│   │   │   └── page.tsx # 결과 페이지 (3가지 리포트 탭)
│   │   ├── layout.tsx # 루트 레이아웃
│   │   └── globals.css # 글로벌 스타일
│   └── package.json    # Node.js 의존성
└── docs/               # 문서 및 샘플
    ├── USER_FLOW.md    # UX 설계
    └── IMPLEMENTATION_GUIDE.md # 구현 가이드
```

## API 엔드포인트

### POST /analyze
기사 URL을 받아 분석 결과를 반환합니다.

**요청:**
```json
{
  "url": "https://example.com/news/article/123"
}
```

**응답:**
```json
{
  "article_info": {
    "title": "기사 제목",
    "url": "기사 URL"
  },
  "classification": {
    "type": "스트레이트 뉴스",
    "evaluable": true,
    "reason": "분류 사유"
  },
  "reports": {
    "comprehensive": "종합 리포트 내용...",
    "journalist": "기자용 리포트 내용..."
  }
}
```

### GET /health
서버 상태를 확인합니다.

## 하이브리드 모델 전략

CR-Check는 2단계 하이브리드 AI 전략을 사용하여 최적의 비용과 성능을 달성합니다:

- **Phase 1 (Claude Haiku 4.5)**: 기사에서 문제 패턴을 빠르게 식별 (~6초, 저비용)
- **Phase 2 (Claude Sonnet 4.5)**: 식별된 패턴을 바탕으로 상세한 서술형 리포트 생성 (안정적, 고품질)

이 전략은:
- ✅ 전체 Sonnet 사용 대비 비용 절감 (~80%)
- ✅ 전체 Haiku 사용 대비 안정성 향상 (JSON 파싱 실패율 0%)
- ✅ 빠른 분석 속도 유지 (전체 ~60초)

## 문제 해결

### 백엔드 서버가 시작되지 않아요

**에러:** `ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.`

**해결:**
1. API 키가 올바르게 설정되었는지 확인:
   ```bash
   echo $ANTHROPIC_API_KEY
   ```
2. 키가 출력되지 않으면 다시 설정:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```
3. 또는 `backend/.env` 파일에 저장

### 프론트엔드에서 백엔드에 연결할 수 없어요

**에러:** "백엔드 서버에 연결할 수 없습니다"

**해결:**
1. 백엔드 서버가 실행 중인지 확인 (http://localhost:8000)
2. CORS 에러인 경우 `backend/main.py`의 CORS 설정 확인
3. `frontend/.env` 파일의 `NEXT_PUBLIC_API_URL` 확인

### 기사를 분석할 수 없어요

**가능한 원인:**
- 평가 불가능한 기사 유형 (칼럼, 사설 등)
- 스크래핑 실패 (특정 언론사의 페이지 구조가 다를 수 있음)
- 잘못된 URL 형식

**해결:**
- 다른 언론사의 스트레이트 뉴스로 시도
- 네이버 뉴스나 다음 뉴스 URL 사용 권장

## 개발 가이드

### 백엔드 개발

```bash
cd backend

# 개발 모드로 실행 (자동 재시작)
uvicorn main:app --reload

# API 문서 확인
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### 프론트엔드 개발

```bash
cd frontend

# 개발 서버
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 서버 실행
npm start

# 린트 검사
npm run lint
```

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다.

## 기여하기

이슈 리포트와 Pull Request를 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 문의

프로젝트 관련 문의사항은 GitHub Issues를 통해 남겨주세요.

---

**CR-Check** - 더 나은 언론을 위한 언론윤리 분석 도구
