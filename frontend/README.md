# CR-Check Frontend

한국신문윤리위원회 윤리규범 기반 기사 분석 도구 - 프론트엔드

## 기술 스택

- **Next.js 15** (App Router)
- **React 18**
- **TypeScript**
- **TailwindCSS 3**

## 디자인

### 컬러 팔레트

- **Primary**: Deep Navy (#1A237E) - 차분하고 신뢰감 있는 배경
- **Secondary**: Warm Amber (#FFB300) - 경고 및 강조용

### 타이포그래피

- **본문**: Georgia, serif (종이 신문 느낌)
- **UI 요소**: Helvetica, sans-serif (현대적 기술력)

## 기능

### 1. 메인 페이지 (`/`)

- 기사 URL 입력 폼
- 실시간 분석 진행 상황 표시
- 로딩 애니메이션 및 상태 메시지
- 타임아웃: 120초

### 2. 결과 페이지 (`/result`)

- 기사 정보 카드
- 3가지 리포트 탭:
  - **시민을 위한 종합 리포트**: 일반 독자용
  - **기자를 위한 전문 리포트**: 윤리규범 근거 및 개선 방안
  - **학생을 위한 교육 리포트**: 문답식 학습 자료
- PDF 다운로드 버튼 (Docker 배포 후 활성화 예정)
- 다른 기사 분석하기 버튼

## 로컬 개발

### 필수 조건

- Node.js 20+
- npm

### 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

서버가 http://localhost:3000에서 실행됩니다.

### 백엔드 연동

프론트엔드는 `next.config.js`의 rewrites 설정을 통해 `/api/*` 경로를 백엔드 서버(`http://localhost:8000`)로 프록시합니다.

백엔드 서버가 먼저 실행되어 있어야 합니다:

```bash
cd ../backend
python3 main.py
```

## 프로덕션 빌드

```bash
# 프로덕션 빌드
npm run build

# 프로덕션 서버 실행
npm start
```

## 배포

### Vercel (권장)

```bash
# Vercel CLI 설치
npm i -g vercel

# 배포
vercel
```

환경 변수 설정:
- `NEXT_PUBLIC_API_URL`: 백엔드 API URL (예: https://your-backend.railway.app)

## 디렉토리 구조

```
frontend/
├── app/
│   ├── globals.css           # 글로벌 스타일
│   ├── layout.tsx            # 루트 레이아웃
│   ├── page.tsx              # 메인 페이지 (URL 입력)
│   └── result/
│       └── page.tsx          # 결과 페이지 (3가지 리포트)
├── components/               # 재사용 가능한 컴포넌트 (미래 확장용)
├── lib/                      # 유틸리티 함수 (미래 확장용)
├── public/                   # 정적 파일
├── next.config.js            # Next.js 설정
├── tailwind.config.ts        # Tailwind 설정
├── tsconfig.json             # TypeScript 설정
└── package.json              # 의존성 및 스크립트
```

## 주요 기능 구현 상세

### API 호출 타임아웃

```typescript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 120000); // 120초

const response = await fetch("/api/analyze", {
  method: "POST",
  signal: controller.signal,
  // ...
});
```

### 결과 저장 및 페이지 이동

```typescript
// 결과를 sessionStorage에 저장
sessionStorage.setItem("analysisResult", JSON.stringify(result));

// 결과 페이지로 이동
router.push("/result");
```

### 탭 UI 구현

사용자가 3가지 리포트 중 하나를 선택하여 볼 수 있습니다:
- comprehensive (기본값)
- journalist
- student

## 다음 단계

- [ ] PDF 다운로드 기능 활성화 (백엔드 Docker 배포 후)
- [ ] 반응형 디자인 개선
- [ ] 애니메이션 효과 추가
- [ ] 접근성(a11y) 개선
- [ ] 다크 모드 지원

## 라이선스

MIT
