# cr-check 에 대한 친구C의 조언

## 1. 웹 애플리케이션 총평

### 🔍 전체 설계 평가

**장점:**

- **명확한 목적성**: 언론 윤리 평가라는 구체적 목표에 집중된 설계
- **체계적인 평가 기준**: 119개의 문제적 보도 패턴을 8개 차원으로 체계화한 통합 기준서(unified-criteria.md, 74KB)
- **하이브리드 AI 전략**: Phase 1(Haiku)에서 패턴 식별, Phase 2(Sonnet)에서 리포트 생성으로 비용 최적화(80% 절감)
- **모듈화된 구조**: 백엔드(FastAPI)와 프론트엔드(Next.js)의 깔끔한 분리

**개선이 필요한 부분:**

1. **에러 처리 취약점**:
    - JSON 파싱 실패 시 재시도 로직 부족
    - API 타임아웃(60초) 설정이 있지만, 실제 처리 시간이 길 경우 대응 미흡
2. **성능 최적화 부족**:
    - 평가 기준 파일(74KB)을 매 요청마다 전체 로드
    - 캐싱 메커니즘 부재
3. **보안 및 운영 이슈**:
    - CORS 설정이 모든 도메인 허용(`allow_origins=["*"]`)
    - API 키가 환경변수로만 관리(키 로테이션, 암호화 미고려)
    - Rate limiting 없음
<!-- 4. **UX 개선 필요**:
    - 분석 중 진행률 표시가 실제 진행 상황과 연동되지 않음(하드코딩된 시뮬레이션)
    - 에러 발생 시 사용자 친화적 메시지 부족 -->

### 💡 추가 최적화 제안

```python
# 1. 캐싱 추가
from functools import lru_cache

@lru_cache(maxsize=1)
def load_criteria():
    return CriteriaManager()

# 2. 재시도 로직
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
async def analyze_with_retry(article_content):
    return await analyzer.analyze(article_content)

# 3. Rate limiting
from fastapi import Request
from slowapi import Limiter
limiter = Limiter(key_func=lambda request: request.client.host)
app.state.limiter = limiter

@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze_article(request: Request, req: AnalyzeRequest):
    # ... 기존 코드
```

## 2. 백엔드 최적화 방법론

### 🎯 최적의 접근 방법 (우선순위별)

- **적용 방법**:

    ```python
    # analyzer.py 개선 예시class ArticleAnalyzer:    def __init__(self):        # 기존 코드...        # 캐싱 추가        self._criteria_cache = None        self._last_cache_time = None            def get_criteria(self):        """평가 기준을 캐싱하여 반환"""        now = time.time()        if self._criteria_cache is None or (now - self._last_cache_time) > 3600:            self._criteria_cache = CriteriaManager()            self._last_cache_time = now        return self._criteria_cache
    ```

### 📊 구체적 최적화 작업

```python
# 1. 비동기 처리 개선
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OptimizedAnalyzer:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def parallel_analysis(self, article_content):
        """Phase 1과 기본 정보 추출을 병렬 처리"""
        tasks = [
            self._identify_categories(article_content),
            self._extract_metadata(article_content),
            self._check_article_type(article_content)
        ]
        results = await asyncio.gather(*tasks)
        return results

# 2. 스트리밍 응답 구현
from fastapi.responses import StreamingResponse

@app.post("/analyze/stream")
async def analyze_stream(request: AnalyzeRequest):
    async def generate():
        yield '{"status": "starting"}\n'
        # Phase 1
        categories = await analyzer._identify_categories(article_data)
        yield f'{{"status": "categories", "data": {json.dumps(categories)}}}\n'
        # Phase 2
        reports = await analyzer._generate_reports(article_data, categories)
        yield f'{{"status": "complete", "data": {json.dumps(reports)}}}\n'

    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

### 🔧 간단한 기능 추가

**URL 유효성 검사 강화:**

파일: `/frontend/components/MainAnalysisCenter.tsx`

```tsx
// handleSubmit 함수 수정 (12번째 줄)
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();

  // URL 패턴 검증 추가
  const urlPattern = /^https?:\/\/([\w\-]+\.)+[\w\-]+(\/[\w\-._~:/?#[\]@!$&'()*+,;=]*)?$/;

  if (!content.trim()) {
    alert('URL을 입력해주세요.');
    return;
  }

  if (!urlPattern.test(content.trim())) {
    alert('올바른 URL 형식이 아닙니다. http:// 또는 https://로 시작하는 전체 URL을 입력해주세요.');
    return;
  }

  // 뉴스 사이트 확인 (선택적)
  const newsPatterns = [
    /news\.naver\.com/,
    /news\.daum\.net/,
    /\.joins\.com/,
    /\.chosun\.com/,
    /\.donga\.com/,
    /\.hani\.co\.kr/,
    /\.khan\.co\.kr/
  ];

  const isNewsUrl = newsPatterns.some(pattern => pattern.test(content));

  if (!isNewsUrl) {
    const proceed = confirm('일반적인 뉴스 사이트 URL이 아닌 것 같습니다. 계속 진행하시겠습니까?');
    if (!proceed) return;
  }

  onAnalyze({ type: 'url', content: content.trim() });
};

```
