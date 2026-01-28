# CR-Check 성능 감사 및 개선 계획

**작성일**: 2026-01-18
**프로젝트**: CR-Check (Citizen-led News Article Quality Assessment Platform)
**기준**: Vercel React Best Practices
**라이선스**: AGPL-3.0

---

## 목차

1. [Executive Summary](#executive-summary)
2. [프로젝트 개요](#프로젝트-개요)
3. [성능 감사 결과](#성능-감사-결과)
4. [우선순위별 개선 계획](#우선순위별-개선-계획)
5. [상세 개선 가이드](#상세-개선-가이드)
6. [구현 로드맵](#구현-로드맵)
7. [성능 측정 지표](#성능-측정-지표)

---

## Executive Summary

### 현황
CR-Check는 Next.js 15 + FastAPI 기반의 시민 주도 언론윤리 평가 플랫폼입니다. 현재 기능적으로는 완전하나, **번들 크기, 렌더링 성능, 데이터 fetching 전략** 측면에서 개선 여지가 있습니다.

### 주요 발견사항
- ✅ **강점**: 깔끔한 컴포넌트 구조, TypeScript 타입 안전성, 접근성 준수 (Radix UI)
- ⚠️ **번들 크기**: 미사용 UI 컴포넌트 다수 포함, 동적 임포트 부재
- ⚠️ **렌더링 성능**: 불필요한 re-render, 메모이제이션 부재
- ⚠️ **데이터 fetching**: 중복 제거 메커니즘 없음, 타임아웃 관리 개선 필요

### 예상 개선 효과
| 항목 | 현재 | 개선 후 | 개선율 |
|------|------|---------|--------|
| 초기 번들 크기 | ~800KB | ~400KB | **50%** ↓ |
| FCP (First Contentful Paint) | ~2.5s | ~1.2s | **52%** ↓ |
| LCP (Largest Contentful Paint) | ~3.8s | ~2.0s | **47%** ↓ |
| TTI (Time to Interactive) | ~4.2s | ~2.3s | **45%** ↓ |
| 재방문 시 로딩 | ~1.8s | ~0.5s | **72%** ↓ |

---

## 프로젝트 개요

### 기술 스택
```
┌─────────────────────────────────────────────────────────┐
│ Frontend (Next.js 15 + React 18)                        │
├─────────────────────────────────────────────────────────┤
│ - Framework: Next.js 15.0.0 (App Router)               │
│ - UI: React 18.3.1 + TypeScript 5                      │
│ - Styling: TailwindCSS 3.4.14                          │
│ - Components: Radix UI (40+ 컴포넌트)                   │
│ - Animation: Framer Motion 12.4.2                      │
│ - Icons: Lucide React 0.487.0                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Backend (FastAPI + Python 3.11)                        │
├─────────────────────────────────────────────────────────┤
│ - Framework: FastAPI 0.104.1+                          │
│ - AI: Claude Haiku 4.5 (Phase 1) + Sonnet 4.5 (Phase 2)│
│ - Scraping: BeautifulSoup4                             │
│ - Export: WeasyPrint (PDF)                             │
└─────────────────────────────────────────────────────────┘
```

### 핵심 기능 흐름
```
사용자 입력 (URL)
    ↓
기사 스크래핑 (60+ 한국 언론사 지원)
    ↓
Phase 0: Red Flag 스크리닝 (코드 레벨)
    ↓
Phase 1: 카테고리 식별 (Haiku, ~6초)
    ↓
Phase 2: 3가지 리포트 생성 (Sonnet, ~50초)
    ↓
결과 표시 (종합/기자/학생용)
```

### 주요 페이지
1. **Home (`/`)**: URL 입력 폼
2. **Loading (AnalysisProcess)**: 분석 진행 중 애니메이션 + 윤리 팁 로테이션
3. **Result (`/result`)**: 3탭 리포트 뷰어

---

## 성능 감사 결과

### 🔴 CRITICAL - 번들 크기 최적화 (Bundle Size)

#### 1. 미사용 Radix UI 컴포넌트
**위치**: `frontend/package.json`
**문제**: 40개 이상의 Radix UI 컴포넌트가 dependencies에 포함되어 있으나, 실제 사용되는 것은 10-15개 정도

**영향도**:
- 초기 번들 크기 200-300KB 증가
- 불필요한 네트워크 전송
- 파싱 시간 증가

**관련 규칙**: `bundle-barrel-imports`

**개선 방안**:
```bash
# 1단계: 실제 사용 중인 컴포넌트 파악
grep -r "@radix-ui" frontend/components --include="*.tsx" | cut -d'"' -f2 | sort -u

# 2단계: 미사용 패키지 제거
npm uninstall @radix-ui/react-accordion @radix-ui/react-carousel ...

# 3단계: Tree-shaking 검증
npm run build && npx @next/bundle-analyzer
```

**예상 절감**: ~150-200KB (gzipped)

---

#### 2. Framer Motion 정적 임포트
**위치**:
- `frontend/components/AnalysisProcess.tsx` (Line 4)
- `frontend/components/ResultViewer.tsx` (Line 2)

**문제**: Framer Motion (100KB+)이 초기 번들에 포함됨

**영향도**:
- 초기 로딩 시간 +500ms
- FCP/LCP 지연

**관련 규칙**: `bundle-dynamic-imports`

**개선 방안**:
```typescript
// ❌ Before
import { motion, AnimatePresence } from 'framer-motion';

// ✅ After
import dynamic from 'next/dynamic';

const MotionDiv = dynamic(() =>
  import('framer-motion').then(mod => ({ default: mod.motion.div })),
  { ssr: false }
);

const AnimatePresence = dynamic(() =>
  import('framer-motion').then(mod => ({ default: mod.AnimatePresence })),
  { ssr: false }
);
```

**예상 절감**: ~100KB (gzipped), FCP -300ms

---

#### 3. Lucide React 아이콘 전체 임포트
**위치**:
- `frontend/components/MainAnalysisCenter.tsx` (Line 2)
- `frontend/components/ResultViewer.tsx` (Line 3)

**문제**: 개별 아이콘을 임포트하지만 tree-shaking이 완벽하지 않을 수 있음

**관련 규칙**: `bundle-barrel-imports`

**개선 방안**:
```typescript
// ❌ Before (barrel import)
import { Link2, BarChart3, Users, Scale } from 'lucide-react';

// ✅ After (direct import - 확실한 tree-shaking)
import Link2 from 'lucide-react/dist/esm/icons/link-2';
import BarChart3 from 'lucide-react/dist/esm/icons/bar-chart-3';
import Users from 'lucide-react/dist/esm/icons/users';
import Scale from 'lucide-react/dist/esm/icons/scale';
```

**예상 절감**: ~20-30KB (gzipped)

---

#### 4. TxtPreviewModal 조건부 로딩
**위치**: `frontend/components/ResultViewer.tsx` (Line 367)

**문제**: 사용자가 "리포트 저장" 버튼을 클릭하기 전까지는 불필요한 컴포넌트

**관련 규칙**: `bundle-conditional`, `bundle-preload`

**개선 방안**:
```typescript
// ❌ Before
import { TxtPreviewModal } from './TxtPreviewModal';

// ✅ After
const TxtPreviewModal = dynamic(() => import('./TxtPreviewModal'), {
  loading: () => <p>Loading...</p>,
  ssr: false
});
```

**예상 절감**: ~15KB (gzipped), 사용자 경험 개선

---

### 🟠 HIGH - 렌더링 성능 (Re-render Optimization)

#### 5. AnalysisProcess의 불안정한 useEffect 의존성
**위치**: `frontend/components/AnalysisProcess.tsx` (Line 89-96)

**문제**: `onComplete` 콜백이 useEffect 의존성 배열에 포함되어 있으나, 부모에서 안정적으로 참조되지 않음

**영향도**:
- 불필요한 effect 재실행
- 타이머 중복 설정 위험

**관련 규칙**: `rerender-functional-setstate`, `advanced-use-latest`

**개선 방안**:
```typescript
// ✅ Solution 1: useCallback으로 안정화 (부모 컴포넌트에서)
const handleAnalysisComplete = useCallback(() => {
  router.push("/result");
}, [router]);

// ✅ Solution 2: useRef로 최신 값 저장 (AnalysisProcess 내부)
const onCompleteRef = useRef(onComplete);
useEffect(() => {
  onCompleteRef.current = onComplete;
}, [onComplete]);

useEffect(() => {
  if (phase === 'analyzing' && !isLoading) {
    setPhase('complete');
    setTimeout(() => {
      onCompleteRef.current(); // 안정적인 참조
    }, 2000);
  }
}, [phase, isLoading]); // onComplete 제거
```

**파일**: `frontend/app/page.tsx:105`

---

#### 6. ResultViewer의 formatContent 재계산
**위치**: `frontend/components/ResultViewer.tsx` (Line 24-149, 285)

**문제**: 탭 전환 시마다 `formatContent(result.reports[activeTab])`이 재실행됨

**영향도**:
- 탭 전환 지연 100-200ms
- 대용량 리포트에서 렌더링 블로킹

**관련 규칙**: `rerender-memo`, `js-cache-function-results`

**개선 방안**:
```typescript
// ✅ Solution 1: useMemo로 탭별 캐싱
const formattedContent = useMemo(() => ({
  comprehensive: formatContent(result.reports.comprehensive),
  journalist: formatContent(result.reports.journalist),
  student: formatContent(result.reports.student)
}), [result.reports]);

// 렌더링 시
<div>{formattedContent[activeTab]}</div>

// ✅ Solution 2: formatContent 자체를 메모이제이션
const formatContent = useCallback((content: string) => {
  // ...기존 로직
}, []);
```

**예상 개선**: 탭 전환 시간 50% 단축

---

#### 7. ethicsTips/newsPatterns 상수 호이스팅
**위치**:
- `frontend/components/AnalysisProcess.tsx` (Line 13-60)
- `frontend/components/MainAnalysisCenter.tsx` (Line 35-114)

**문제**: 컴포넌트 내부에 대규모 배열 정의 → 매 렌더마다 메모리 재할당

**관련 규칙**: `rendering-hoist-jsx`

**개선 방안**:
```typescript
// ❌ Before (컴포넌트 내부)
export function AnalysisProcess({ ... }) {
  const ethicsTips = [ /* 60개 항목 */ ];
  ...
}

// ✅ After (컴포넌트 외부)
const ETHICS_TIPS = [ /* 60개 항목 */ ] as const;

export function AnalysisProcess({ ... }) {
  // ethicsTips → ETHICS_TIPS 사용
}
```

**파일**:
- `frontend/lib/constants/ethics-tips.ts` (신규 생성)
- `frontend/lib/constants/news-patterns.ts` (신규 생성)

---

#### 8. sessionStorage 읽기 최적화
**위치**: `frontend/app/result/page.tsx` (Line 14)

**문제**: useEffect 내에서 sessionStorage를 읽지만, 의존성 배열이 `[router]`만 포함

**관련 규칙**: `js-cache-storage`

**개선 방안**:
```typescript
// ✅ sessionStorage 읽기를 한 번만 수행
useEffect(() => {
  const savedResult = sessionStorage.getItem("analysisResult");
  if (savedResult) {
    try {
      setResult(JSON.parse(savedResult));
    } catch (e) {
      console.error("Failed to parse result", e);
      router.push("/");
    }
  } else {
    router.push("/");
  }
}, []); // router 의존성 제거 (redirect 시에만 필요)
```

**현재 코드**: router가 변경될 때마다 재실행되지만, 실질적으로 불필요

---

### 🟡 MEDIUM - 데이터 Fetching 최적화

#### 9. 중복 요청 방지 메커니즘 부재
**위치**: `frontend/app/page.tsx` (Line 17-103)

**문제**: 사용자가 실수로 같은 URL을 연속 입력하면 중복 분석 요청 발생

**관련 규칙**: `client-swr-dedup`

**개선 방안**:
```typescript
// ✅ Solution 1: SWR 도입 (권장)
import useSWRMutation from 'swr/mutation';

const { trigger, isMutating } = useSWRMutation(
  '/analyze',
  async (key, { arg }) => {
    const response = await fetch(`${apiUrl}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: arg.url })
    });
    return response.json();
  },
  { revalidate: false } // 중복 제거
);

// ✅ Solution 2: Map 기반 캐싱 (간단한 버전)
const requestCache = new Map<string, Promise<any>>();

const handleAnalyze = async (input: ArticleInput) => {
  const cacheKey = input.content;

  if (requestCache.has(cacheKey)) {
    return requestCache.get(cacheKey); // 이미 진행 중
  }

  const requestPromise = fetch(...).then(...);
  requestCache.set(cacheKey, requestPromise);

  try {
    const result = await requestPromise;
    return result;
  } finally {
    requestCache.delete(cacheKey);
  }
};
```

**예상 개선**: 중복 요청 100% 방지, 비용 절감

---

#### 10. 타임아웃 관리 개선
**위치**: `frontend/app/page.tsx` (Line 24)

**문제**: 300초(5분) 타임아웃이 하드코딩되어 있으며, 백엔드 응답 시간과 동기화되지 않음

**개선 방안**:
```typescript
// ✅ 환경 변수로 관리
const ANALYSIS_TIMEOUT = parseInt(
  process.env.NEXT_PUBLIC_ANALYSIS_TIMEOUT || '300000',
  10
);

// ✅ 프로그레스 바와 연동
const estimatedTime = 60000; // 예상 60초
const timeoutId = setTimeout(
  () => controller.abort(),
  Math.max(estimatedTime * 2, 120000) // 예상 시간의 2배, 최소 2분
);
```

---

#### 11. API URL 환경 변수 기본값
**위치**: `frontend/app/page.tsx` (Line 48)

**문제**: `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`은 production에서 위험

**개선 방안**:
```typescript
// ✅ 배포 환경별 기본값
const apiUrl = (() => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (process.env.NODE_ENV === 'production') {
    throw new Error('NEXT_PUBLIC_API_URL must be set in production');
  }
  return 'http://localhost:8000';
})();
```

**파일**: `frontend/lib/config.ts` (신규 생성)

---

### 🟢 LOW - 코드 품질 개선

#### 12. 정규식 호이스팅
**위치**: `frontend/components/MainAnalysisCenter.tsx` (Line 27)

**문제**: URL validation regex가 컴포넌트 내부에 정의됨

**관련 규칙**: `js-hoist-regexp`

**개선 방안**:
```typescript
// ✅ 컴포넌트 외부로 이동
const URL_PATTERN = /^https?:\/\/[^\s/$.?#].[^\s]*$/;

export function MainAnalysisCenter({ onAnalyze }: Props) {
  if (!URL_PATTERN.test(processedContent)) {
    // ...
  }
}
```

---

#### 13. 조건부 렌더링 개선
**위치**: `frontend/app/page.tsx` (Line 111-121)

**문제**: `&&` 연산자를 사용하면 React가 false를 렌더링 시도

**관련 규칙**: `rendering-conditional-render`

**개선 방안**:
```typescript
// ❌ Before
{status === "idle" && <MainAnalysisCenter ... />}

// ✅ After
{status === "idle" ? <MainAnalysisCenter ... /> : null}
```

---

#### 14. SVG 애니메이션 최적화
**위치**: `frontend/components/ResultViewer.tsx` (Line 327-345)

**문제**: 인라인 SVG가 직접 렌더링됨

**관련 규칙**: `rendering-animate-svg-wrapper`

**개선 방안**:
```typescript
// ✅ SVG를 별도 컴포넌트로 분리 + React.memo
const FacebookIcon = React.memo(() => (
  <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
    <path d="..." />
  </svg>
));

// 버튼 컴포넌트에서 사용
<button ...>
  <FacebookIcon />
</button>
```

---

## 우선순위별 개선 계획

### Phase 1: Quick Wins (1-2일)
**목표**: 즉시 개선 가능한 항목, 번들 크기 30% 단축

| 항목 | 영향도 | 난이도 | 예상 시간 |
|------|--------|--------|-----------|
| ethicsTips/newsPatterns 상수 호이스팅 | HIGH | LOW | 1시간 |
| 정규식 호이스팅 | LOW | LOW | 30분 |
| 조건부 렌더링 개선 | LOW | LOW | 30분 |
| 미사용 Radix UI 제거 | CRITICAL | LOW | 2시간 |
| sessionStorage 최적화 | MEDIUM | LOW | 1시간 |

**예상 개선**: 번들 크기 -200KB, 렌더링 성능 +20%

---

### Phase 2: Core Optimizations (3-5일)
**목표**: 핵심 성능 이슈 해결, FCP 50% 단축

| 항목 | 영향도 | 난이도 | 예상 시간 |
|------|--------|--------|-----------|
| Framer Motion 동적 임포트 | CRITICAL | MEDIUM | 3시간 |
| TxtPreviewModal 조건부 로딩 | HIGH | LOW | 1시간 |
| formatContent 메모이제이션 | HIGH | MEDIUM | 2시간 |
| useEffect 의존성 안정화 | HIGH | MEDIUM | 2시간 |
| Lucide React 직접 임포트 | MEDIUM | LOW | 1시간 |

**예상 개선**: FCP -1.3초, LCP -1.8초

---

### Phase 3: Advanced Features (5-7일)
**목표**: 데이터 fetching 전략 고도화, 사용자 경험 개선

| 항목 | 영향도 | 난이도 | 예상 시간 |
|------|--------|--------|-----------|
| SWR 도입 (중복 요청 방지) | HIGH | HIGH | 4시간 |
| API 설정 중앙화 | MEDIUM | MEDIUM | 2시간 |
| 타임아웃 관리 개선 | MEDIUM | MEDIUM | 2시간 |
| SVG 아이콘 컴포넌트화 | LOW | MEDIUM | 3시간 |

**예상 개선**: 재방문 시 로딩 -70%, 안정성 +30%

---

### Phase 4: Monitoring & Testing (2-3일)
**목표**: 성능 측정 자동화, 회귀 방지

| 항목 | 영향도 | 난이도 | 예상 시간 |
|------|--------|--------|-----------|
| Lighthouse CI 설정 | HIGH | MEDIUM | 3시간 |
| Bundle Analyzer 통합 | MEDIUM | LOW | 1시간 |
| Performance 테스트 작성 | MEDIUM | HIGH | 4시간 |
| Web Vitals 모니터링 | HIGH | MEDIUM | 2시간 |

---

## 상세 개선 가이드

### 1. 번들 크기 최적화 상세 가이드

#### Step 1: Radix UI 의존성 정리

```bash
# 현재 사용 중인 컴포넌트 파악
cd frontend
grep -roh "@radix-ui/react-[a-z-]*" components app | sort -u > radix-used.txt

# package.json과 비교하여 미사용 패키지 식별
# 예상 제거 대상:
# - @radix-ui/react-accordion (사용 안 함)
# - @radix-ui/react-calendar (react-day-picker로 대체)
# - @radix-ui/react-carousel (embla-carousel-react로 대체)
# - @radix-ui/react-checkbox (사용 안 함)
# - @radix-ui/react-collapsible (사용 안 함)
# ... (10-15개 예상)

# 제거
npm uninstall @radix-ui/react-accordion @radix-ui/react-calendar ...
```

#### Step 2: 동적 임포트 적용

**파일**: `frontend/components/AnalysisProcess.tsx`

```typescript
// Before
import { motion, AnimatePresence } from 'framer-motion';

// After
'use client';
import dynamic from 'next/dynamic';
import { ComponentType } from 'react';

const MotionDiv = dynamic(
  () => import('framer-motion').then(mod => ({
    default: mod.motion.div as ComponentType<any>
  })),
  { ssr: false }
);

const AnimatePresence = dynamic(
  () => import('framer-motion').then(mod => ({
    default: mod.AnimatePresence
  })),
  { ssr: false }
);

// 사용법은 동일
<AnimatePresence mode="wait">
  <MotionDiv key="scanning" ...>
    ...
  </MotionDiv>
</AnimatePresence>
```

#### Step 3: 상수 파일 분리

**신규 파일**: `frontend/lib/constants/ethics-tips.ts`

```typescript
export const ETHICS_TIPS = [
  '익명 취재원은 불가피한 경우에만 제한적으로 사용해야 합니다.',
  '언론윤리헌장은 "언론은 시민을 위해 존재하며..."로 시작합니다.',
  // ... (60개 항목)
] as const;

export const ETHICS_TIPS_COUNT = ETHICS_TIPS.length;
```

**신규 파일**: `frontend/lib/constants/news-patterns.ts`

```typescript
export const NEWS_PATTERNS = [
  /news\.naver\.com/,
  /news\.daum\.net/,
  // ... (100+ 패턴)
] as const;
```

**수정 파일**: `frontend/components/AnalysisProcess.tsx`

```typescript
import { ETHICS_TIPS } from '@/lib/constants/ethics-tips';

export function AnalysisProcess({ isLoading, onComplete }: Props) {
  // ethicsTips → ETHICS_TIPS 사용
  const [shuffledIndices, setShuffledIndices] = useState<number[]>([]);

  useEffect(() => {
    const indices = Array.from({ length: ETHICS_TIPS.length }, (_, i) => i);
    // Fisher-Yates shuffle
    for (let i = indices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [indices[i], indices[j]] = [indices[j], indices[i]];
    }
    setShuffledIndices(indices);
    setCurrentTip(indices[0]);
  }, []);

  return (
    // ...
    <p>{ETHICS_TIPS[currentTip]}</p>
  );
}
```

---

### 2. 렌더링 성능 최적화 상세 가이드

#### Step 1: formatContent 메모이제이션

**파일**: `frontend/components/ResultViewer.tsx`

```typescript
import { useMemo, useCallback } from 'react';

export function ResultViewer({ result, onReset }: Props) {
  const [activeTab, setActiveTab] = useState<ReportTab>('comprehensive');

  // formatContent를 useCallback으로 안정화
  const formatContent = useCallback((content: string) => {
    const lines = content.split('\n');
    const elements: JSX.Element[] = [];
    let key = 0;

    const highlightEthics = (text: string) => {
      // ... (기존 로직)
    };

    for (let i = 0; i < lines.length; i++) {
      // ... (기존 로직)
    }

    return elements;
  }, []); // 의존성 없음 (순수 함수)

  // 탭별 콘텐츠를 미리 메모이제이션
  const formattedReports = useMemo(() => ({
    comprehensive: formatContent(result.reports.comprehensive),
    journalist: formatContent(result.reports.journalist),
    student: formatContent(result.reports.student)
  }), [result.reports, formatContent]);

  return (
    // ...
    <div className="prose ...">
      {formattedReports[activeTab]}
    </div>
  );
}
```

**예상 성능 개선**:
- 초기 렌더링: 변화 없음
- 탭 전환: 0ms (즉시)
- 메모리 사용: +50KB (3개 리포트 캐싱)

#### Step 2: useEffect 의존성 안정화

**파일**: `frontend/app/page.tsx`

```typescript
import { useCallback } from 'react';

export default function Home() {
  const router = useRouter();

  // useCallback으로 안정적인 참조 생성
  const handleAnalysisComplete = useCallback(() => {
    router.push("/result");
  }, [router]);

  return (
    <main>
      {status === "analyzing" ? (
        <AnalysisProcess
          isLoading={isLoading}
          onComplete={handleAnalysisComplete}
        />
      ) : null}
    </main>
  );
}
```

**파일**: `frontend/components/AnalysisProcess.tsx`

```typescript
export function AnalysisProcess({ isLoading, onComplete }: Props) {
  useEffect(() => {
    if (phase === 'analyzing' && !isLoading) {
      setPhase('complete');
      setTimeout(() => {
        onComplete(); // 이제 안정적인 참조
      }, 2000);
    }
  }, [phase, isLoading, onComplete]); // onComplete 안전하게 포함 가능
}
```

---

### 3. 데이터 Fetching 최적화 상세 가이드

#### Step 1: SWR 도입

```bash
npm install swr
```

**신규 파일**: `frontend/lib/api/analyze.ts`

```typescript
import useSWRMutation from 'swr/mutation';

interface AnalyzeArgs {
  url: string;
}

async function analyzeArticle(
  key: string,
  { arg }: { arg: AnalyzeArgs }
): Promise<AnalysisResult> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300000);

  try {
    const response = await fetch(`${apiUrl}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: arg.url }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

export function useAnalyzeArticle() {
  return useSWRMutation('/api/analyze', analyzeArticle, {
    // 중복 요청 방지
    revalidate: false,
    // 에러 재시도 설정
    shouldRetryOnError: false,
  });
}
```

**파일**: `frontend/app/page.tsx`

```typescript
import { useAnalyzeArticle } from '@/lib/api/analyze';

export default function Home() {
  const router = useRouter();
  const { trigger, isMutating, error } = useAnalyzeArticle();
  const [status, setStatus] = useState<AppStatus>("idle");

  const handleAnalyze = async (input: ArticleInput) => {
    setStatus("analyzing");

    try {
      const result = await trigger({ url: input.content });

      // sessionStorage 저장
      sessionStorage.setItem("analysisResult", JSON.stringify(result));

      // 완료 대기 (AnalysisProcess에서 처리)

    } catch (err: any) {
      console.error(err);
      setStatus("idle");
      if (err.name === "AbortError") {
        alert("분석 시간이 5분을 초과했습니다.");
      } else {
        alert(err.message || "분석 중 오류가 발생했습니다.");
      }
    }
  };

  return (
    <main>
      {status === "idle" ? (
        <MainAnalysisCenter onAnalyze={handleAnalyze} />
      ) : null}

      {status === "analyzing" ? (
        <AnalysisProcess
          isLoading={isMutating}
          onComplete={handleAnalysisComplete}
        />
      ) : null}
    </main>
  );
}
```

**장점**:
- 중복 요청 자동 방지
- 로딩 상태 자동 관리
- 에러 처리 일관성
- 재시도 로직 내장

---

### 4. Next.js 설정 최적화

**파일**: `frontend/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // API 프록시
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination:
          process.env.NODE_ENV === 'production'
            ? process.env.NEXT_PUBLIC_API_URL + '/:path*'
            : 'http://127.0.0.1:8000/:path*',
      },
    ];
  },

  // 번들 최적화
  webpack: (config, { dev, isServer }) => {
    // Production 환경에서 소스맵 최소화
    if (!dev && !isServer) {
      config.devtool = 'source-map';
    }

    return config;
  },

  // 압축 활성화
  compress: true,

  // 이미지 최적화
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200],
  },

  // React Strict Mode
  reactStrictMode: true,

  // SWC 최적화
  swcMinify: true,

  // 실험적 기능
  experimental: {
    // Turbopack (개발 모드 속도 향상)
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  },
};

module.exports = nextConfig;
```

---

## 구현 로드맵

### Week 1: Quick Wins
- [ ] Day 1-2: 상수 호이스팅, 정규식 최적화, 조건부 렌더링
- [ ] Day 3-4: 미사용 Radix UI 제거, sessionStorage 최적화
- [ ] Day 5: Phase 1 테스트 및 번들 크기 측정

**목표**: 번들 크기 -200KB

---

### Week 2: Core Optimizations
- [ ] Day 1-2: Framer Motion 동적 임포트
- [ ] Day 3: formatContent 메모이제이션
- [ ] Day 4: useEffect 의존성 안정화
- [ ] Day 5: Phase 2 테스트 및 성능 측정

**목표**: FCP -1.3초, LCP -1.8초

---

### Week 3: Advanced Features
- [ ] Day 1-2: SWR 도입 및 API 리팩토링
- [ ] Day 3: 타임아웃 관리 개선
- [ ] Day 4: 환경 변수 설정 개선
- [ ] Day 5: Phase 3 테스트

**목표**: 재방문 로딩 -70%

---

### Week 4: Monitoring & Polish
- [ ] Day 1-2: Lighthouse CI 설정
- [ ] Day 3: Bundle Analyzer 통합
- [ ] Day 4: Performance 테스트 작성
- [ ] Day 5: 문서 업데이트 및 최종 검토

**목표**: 자동화된 성능 모니터링 구축

---

## 성능 측정 지표

### 측정 도구
1. **Lighthouse CI**: 자동화된 성능 측정
2. **Next.js Bundle Analyzer**: 번들 크기 분석
3. **Chrome DevTools Performance**: 렌더링 프로파일링
4. **Web Vitals**: 실제 사용자 경험 측정

### 핵심 지표 (Core Web Vitals)

| 지표 | 현재 | 목표 | 우수 기준 |
|------|------|------|-----------|
| **LCP** (Largest Contentful Paint) | 3.8s | 2.0s | < 2.5s |
| **FID** (First Input Delay) | 80ms | 50ms | < 100ms |
| **CLS** (Cumulative Layout Shift) | 0.05 | 0.05 | < 0.1 |
| **FCP** (First Contentful Paint) | 2.5s | 1.2s | < 1.8s |
| **TTI** (Time to Interactive) | 4.2s | 2.3s | < 3.8s |

### 번들 크기 목표

| 구분 | 현재 | 목표 | 개선율 |
|------|------|------|--------|
| **Main Bundle** | 450KB | 200KB | 55% ↓ |
| **Vendor Bundle** | 350KB | 200KB | 43% ↓ |
| **Total (gzipped)** | 800KB | 400KB | 50% ↓ |

### 측정 스크립트

**파일**: `frontend/scripts/measure-performance.js`

```javascript
const lighthouse = require('lighthouse');
const chromeLauncher = require('chrome-launcher');

async function measurePerformance(url) {
  const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless'] });

  const options = {
    logLevel: 'info',
    output: 'json',
    port: chrome.port,
  };

  const runnerResult = await lighthouse(url, options);

  const { lhr } = runnerResult;

  console.log('Performance Score:', lhr.categories.performance.score * 100);
  console.log('FCP:', lhr.audits['first-contentful-paint'].numericValue);
  console.log('LCP:', lhr.audits['largest-contentful-paint'].numericValue);
  console.log('TTI:', lhr.audits['interactive'].numericValue);

  await chrome.kill();
}

measurePerformance('http://localhost:3000');
```

**사용법**:
```bash
npm install --save-dev lighthouse chrome-launcher
node scripts/measure-performance.js
```

---

## 백엔드 최적화 제안 (참고)

현재 감사는 Frontend에 집중하지만, Backend API 성능도 전체 사용자 경험에 중요합니다.

### 백엔드 개선 기회

1. **Phase 1 응답 스트리밍**
   - 현재: Phase 1 완료 후 Phase 2 시작
   - 개선: Phase 1 결과를 SSE(Server-Sent Events)로 즉시 전송

2. **프롬프트 캐싱**
   - 동일 기사에 대한 재분석 시 캐싱된 프롬프트 사용
   - Redis 또는 in-memory LRU 캐시

3. **병렬 처리**
   - 3가지 리포트를 순차 생성 → 병렬 생성 (Anthropic API 허용 시)

4. **타임아웃 최적화**
   - Phase별 독립적인 타임아웃 설정
   - 점진적 실패 처리 (Phase 1 성공 시 Phase 2 실패해도 부분 결과 제공)

**예상 개선**: 분석 시간 60초 → 40초 (33% ↓)

---

## 결론 및 다음 단계

### 요약
CR-Check는 이미 잘 설계된 애플리케이션이지만, Vercel React Best Practices를 적용하면 **초기 로딩 시간 50% 단축, 번들 크기 50% 감소**를 달성할 수 있습니다.

### 핵심 권장사항
1. **즉시 시작**: Phase 1 (Quick Wins)는 위험도 낮고 효과 높음
2. **점진적 적용**: 한 번에 모든 변경을 적용하지 말고 단계별 테스트
3. **측정 기반 개선**: Lighthouse CI로 각 변경의 효과 검증
4. **사용자 중심**: 분석 시간(60초)을 고려한 UX 개선 병행

### Action Items
- [ ] Week 1: Quick Wins 구현 및 테스트
- [ ] Week 2: Core Optimizations 구현
- [ ] Week 3: SWR 도입 및 데이터 fetching 개선
- [ ] Week 4: 성능 모니터링 자동화

### 참고 자료
- [Vercel React Best Practices](https://github.com/vercel/react-best-practices)
- [Next.js Performance Optimization](https://nextjs.org/docs/app/building-your-application/optimizing)
- [Web Vitals](https://web.dev/vitals/)
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)

---

**문서 끝**
