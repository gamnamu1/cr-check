# CR-Check DB 구축 실행 계획서 (상세 버전)

> 이 문서는 [DB_CONSTRUCTION_PLAN.md](./DB_CONSTRUCTION_PLAN.md)의 개념적 설계를 바탕으로, **실제 구현 가능한 코드와 단계별 실행 지침**을 제공합니다.

---

## 📋 목차

1. [사전 준비](#사전-준비)
2. [Phase 1: 아카이빙 시스템](#phase-1-아카이빙-시스템-2-3일)
3. [Phase 2: 사용자 인증 및 개인화](#phase-2-사용자-인증-및-개인화-3-5일)
4. [Phase 3: 통계 대시보드](#phase-3-통계-대시보드-5-7일)
5. [보안 체크리스트](#보안-체크리스트)
6. [타임라인 요약](#타임라인-요약)
7. [주의사항](#주의사항)

---

## 사전 준비

### 결정해야 할 사항

#### 1. 개인정보 정책
- [ ] 비로그인 사용자의 분석 데이터도 저장할 것인가? (익명 통계용)
- [ ] 사용자 동의 절차를 어떻게 구성할 것인가?
- [ ] GDPR/개인정보보호법 준수 방안 검토

#### 2. 기능 우선순위
```
필수 (Phase 1): 분석 결과 아카이빙 - 데이터 축적 시작
중요 (Phase 2): 사용자 로그인 + 내 기록 보기 - 리텐션 증가
선택 (Phase 3): 통계 대시보드 + 커뮤니티 - 공익적 가치
```

#### 3. 배포 환경 확인
- 백엔드: Railway? Render? 자체 서버?
- 프론트엔드: Vercel 사용 중?
- Supabase 무료 티어: 500MB DB, 50K 월간 활성 사용자

---

## Phase 1: 아카이빙 시스템 (2-3일)

**목표**: 로그인 없이도 모든 분석 결과를 DB에 저장하여 데이터 축적 시작

### Step 1.1: Supabase 프로젝트 생성 및 설정

#### 작업 순서

1. [Supabase Console](https://app.supabase.com) 접속 → 새 프로젝트 생성
2. 프로젝트 설정 정보 확보:
   - `SUPABASE_URL`: 프로젝트 URL
   - `SUPABASE_ANON_KEY`: 프론트엔드용 (공개 가능)
   - `SUPABASE_SERVICE_ROLE_KEY`: 백엔드용 (비밀, 절대 Git에 커밋 금지)

#### 환경 변수 설정

**백엔드 설정**:
```bash
# backend/.env에 추가
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # 절대 공개하지 말 것
```

**프론트엔드 설정**:
```bash
# frontend/.env.local에 추가
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...  # 공개 가능 (RLS로 보호됨)
```

---

### Step 1.2: 데이터베이스 스키마 설계 및 생성

#### Supabase SQL Editor에서 실행

```sql
-- ============================================
-- CR-Check 데이터베이스 스키마 v1.0
-- Phase 1: 아카이빙 시스템
-- ============================================

-- 1. 기사 메타데이터 테이블
-- 목적: 중복 분석 방지, 언론사별 통계 기반
CREATE TABLE articles (
  id BIGSERIAL PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,  -- 중복 방지의 핵심
  title TEXT NOT NULL,
  publisher TEXT,
  journalist TEXT,
  publish_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),

  CONSTRAINT articles_url_key UNIQUE (url)
);

-- 인덱스 (검색 성능 향상)
CREATE INDEX idx_articles_url ON articles(url);
CREATE INDEX idx_articles_publisher ON articles(publisher);
CREATE INDEX idx_articles_created_at ON articles(created_at DESC);

COMMENT ON TABLE articles IS '기사 원본 메타데이터 (중복 방지용)';
COMMENT ON COLUMN articles.url IS '기사 고유 식별자 (중복 분석 방지)';


-- 2. 분석 결과 테이블
-- 목적: AI 분석 결과 저장, 사용자 연결 (Phase 2)
CREATE TABLE analysis_results (
  id BIGSERIAL PRIMARY KEY,
  article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,

  -- 분석 결과 (텍스트)
  comprehensive_report TEXT NOT NULL,
  journalist_report TEXT NOT NULL,
  student_report TEXT,  -- 선택적 (없을 수도 있음)

  -- 메타데이터
  model_version TEXT DEFAULT 'claude-sonnet-4-5',
  phase1_model TEXT DEFAULT 'claude-haiku-4-5',
  phase2_model TEXT DEFAULT 'claude-sonnet-4-5',
  detected_categories JSONB,  -- Phase 1 결과 저장 (예: ["1-1-1", "1-7-3"])
  duration_seconds FLOAT,

  -- 사용자 연결 (Phase 2에서 활성화)
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

  created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_analysis_article_id ON analysis_results(article_id);
CREATE INDEX idx_analysis_user_id ON analysis_results(user_id);
CREATE INDEX idx_analysis_created_at ON analysis_results(created_at DESC);

COMMENT ON TABLE analysis_results IS 'AI 분석 결과 저장';
COMMENT ON COLUMN analysis_results.detected_categories IS 'Phase 1에서 탐지된 문제 카테고리 ID 목록';


-- 3. Row Level Security (RLS) 설정
-- Phase 1: 백엔드(Service Role)만 쓰기 가능, 읽기는 공개
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;

-- 읽기: 모두 허용 (프론트엔드에서 통계 조회용)
CREATE POLICY "모두가 기사를 조회할 수 있음" ON articles
  FOR SELECT USING (true);

CREATE POLICY "모두가 분석 결과를 조회할 수 있음" ON analysis_results
  FOR SELECT USING (true);

-- 쓰기: Service Role만 가능 (백엔드 전용)
-- 프론트엔드의 anon key로는 쓰기 불가 (보안)
-- Service Role은 RLS 정책을 우회하므로 별도 정책 불필요


-- 4. 성공 확인 쿼리
-- 테이블 생성 확인
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('articles', 'analysis_results');

-- 인덱스 확인
SELECT indexname, tablename FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('articles', 'analysis_results');
```

#### 스키마 설계 이유

| 설계 결정 | 이유 |
|-----------|------|
| `articles` 테이블 분리 | 같은 기사를 여러 사용자가 분석해도 중복 저장 방지 |
| `JSONB` 타입 사용 | `detected_categories` 같은 동적 데이터 저장에 유연함 |
| `user_id` nullable | Phase 1에서는 null, Phase 2에서 채워짐 |
| RLS 설정 | 백엔드만 쓰기, 읽기는 공개 (통계용) |
| 인덱스 3개 | URL, publisher, created_at 검색 최적화 |

---

### Step 1.3: 백엔드에 Supabase 클라이언트 연동

#### 파일 생성: `backend/database.py`

```python
# backend/database.py
"""
Supabase 데이터베이스 연동 모듈

역할:
- 분석 결과를 Supabase에 저장
- 기사 중복 방지 (URL 기준)
- 사용자 연결 (Phase 2)
"""

import os
from supabase import create_client, Client
from typing import Optional, Dict, Any
from datetime import datetime

class DatabaseManager:
    """분석 결과를 Supabase에 저장하는 관리자"""

    def __init__(self):
        """Supabase 클라이언트 초기화"""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            print("⚠️  Supabase 설정이 없습니다. DB 저장 기능 비활성화됨.")
            self.client = None
        else:
            self.client: Client = create_client(url, key)
            print("✅ Supabase 연결 성공")

    async def save_analysis(
        self,
        article_data: Dict[str, Any],
        analysis_result: Dict[str, Any],
        duration: float,
        user_id: Optional[str] = None
    ) -> Optional[int]:
        """
        분석 결과를 DB에 저장

        Args:
            article_data: 기사 원본 정보 (title, url, publisher, ...)
            analysis_result: 분석 결과 (reports, detected_categories)
            duration: 분석 소요 시간 (초)
            user_id: (선택) 로그인한 사용자 ID (Phase 2)

        Returns:
            analysis_result_id: 저장된 분석 결과의 ID

        Raises:
            None: 저장 실패해도 예외를 발생시키지 않음 (서비스 중단 방지)
        """
        if not self.client:
            print("⚠️  DB 저장 건너뜀 (Supabase 미설정)")
            return None

        try:
            # 1. 기사가 이미 있는지 확인 (URL 기준)
            article_response = self.client.table("articles") \
                .select("id") \
                .eq("url", article_data["url"]) \
                .execute()

            if article_response.data:
                # 이미 있음 → 기존 ID 사용
                article_id = article_response.data[0]["id"]
                print(f"📌 기존 기사 사용 (ID: {article_id})")
            else:
                # 없음 → 새로 삽입
                insert_response = self.client.table("articles").insert({
                    "url": article_data["url"],
                    "title": article_data["title"],
                    "publisher": article_data.get("publisher"),
                    "journalist": article_data.get("journalist"),
                    "publish_date": article_data.get("publish_date")
                }).execute()

                article_id = insert_response.data[0]["id"]
                print(f"✨ 새 기사 저장 (ID: {article_id})")

            # 2. 분석 결과 저장
            reports = analysis_result.get("reports", {})
            detected_categories = analysis_result.get("detected_categories", [])

            result_response = self.client.table("analysis_results").insert({
                "article_id": article_id,
                "comprehensive_report": reports.get("comprehensive", ""),
                "journalist_report": reports.get("journalist", ""),
                "student_report": reports.get("student"),
                "detected_categories": detected_categories,
                "duration_seconds": duration,
                "user_id": user_id,
                "model_version": "hybrid-haiku-sonnet-4.5"
            }).execute()

            result_id = result_response.data[0]["id"]
            print(f"💾 분석 결과 저장 완료 (ID: {result_id})")

            return result_id

        except Exception as e:
            print(f"❌ DB 저장 실패: {str(e)}")
            # 저장 실패해도 사용자에게는 분석 결과 반환 (서비스 중단 방지)
            return None

    async def get_analysis_by_id(self, analysis_id: int) -> Optional[Dict]:
        """
        분석 ID로 결과 조회

        Args:
            analysis_id: 분석 결과 ID

        Returns:
            분석 결과 딕셔너리 (article 정보 포함)
        """
        if not self.client:
            return None

        try:
            response = self.client.table("analysis_results") \
                .select("*, articles(*)") \
                .eq("id", analysis_id) \
                .single() \
                .execute()

            return response.data
        except Exception as e:
            print(f"❌ 분석 결과 조회 실패: {str(e)}")
            return None
```

#### 의존성 추가

**파일 수정**: `backend/requirements.txt`에 추가

```txt
supabase==2.3.4
```

#### 설치 명령어

```bash
cd backend
pip install supabase==2.3.4
```

---

### Step 1.4: main.py에서 DB 저장 로직 통합

**파일 수정**: `backend/main.py`

```python
# backend/main.py

from database import DatabaseManager  # 추가

# 전역 인스턴스 생성 (기존 코드 아래에 추가)
scraper = ArticleScraper()
analyzer = ArticleAnalyzer()
db_manager = DatabaseManager()  # 추가


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_article(request: AnalyzeRequest):
    """
    기사 분석 엔드포인트 (DB 저장 추가)

    변경사항:
    - 분석 결과를 Supabase에 자동 저장
    - 저장 실패해도 사용자에게는 결과 반환 (서비스 중단 방지)
    """
    try:
        # 분석 시작 시간 기록
        import time
        start_time = time.time()

        # 1. 기사 스크래핑
        print(f"📰 기사 스크래핑 시작: {request.url}")
        article_data = scraper.scrape(str(request.url))
        print(f"✅ 스크래핑 완료: {article_data['title'][:50]}...")

        # 2. 기사 분석 (2단계 파이프라인)
        print(f"🔍 기사 분석 시작...")
        result = await analyzer.analyze(article_data)
        print(f"✅ 분석 완료")

        # 분석 소요 시간 계산
        duration = time.time() - start_time

        # 3. DB에 저장 (비동기, 실패해도 결과는 반환)
        await db_manager.save_analysis(
            article_data=article_data,
            analysis_result=result,
            duration=duration,
            user_id=None  # Phase 1에서는 항상 None
        )

        return result

    except ValueError as e:
        # 스크래핑 또는 분석 중 발생한 에러
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # 예상치 못한 에러
        import traceback
        from datetime import datetime

        error_msg = f"[{datetime.now()}] Error processing {request.url}: {str(e)}\n{traceback.format_exc()}\n{'='*50}\n"

        try:
            with open("backend_error.log", "a", encoding="utf-8") as f:
                f.write(error_msg)
        except Exception as log_err:
            print(f"Failed to write log: {log_err}")

        print(f"❌ 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류가 발생했습니다: {str(e)}"
        )
```

---

### Step 1.5: 테스트 및 검증

#### 테스트 시나리오

**1. 백엔드 서버 재시작**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**예상 출력**:
```
✅ Supabase 연결 성공
🚀 CR-Check API 서버 시작...
```

**2. 분석 요청 전송**

방법 1: 프론트엔드에서 기사 분석 (http://localhost:3000)

방법 2: curl 테스트
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://n.news.naver.com/article/001/0014912345"}'
```

**예상 출력**:
```
📰 기사 스크래핑 시작: https://...
✅ 스크래핑 완료: [기사제목]...
🔍 기사 분석 시작...
📊 Phase 1 (Haiku): 평가 대상 여부 확인 및 문제 카테고리 식별 중...
✅ Phase 1 완료 (6.2초): 3개 카테고리 발견
📝 Phase 2 (Sonnet): 3가지 리포트 생성 중...
✅ Phase 2 완료 (45.8초)
🎉 전체 분석 완료 (총 52.0초)
✨ 새 기사 저장 (ID: 1)
💾 분석 결과 저장 완료 (ID: 1)
```

**3. Supabase Console에서 데이터 확인**

1. Supabase Console → Table Editor 이동
2. `articles` 테이블 확인:
   - 기사 URL, 제목, 언론사 등이 저장되어 있어야 함
3. `analysis_results` 테이블 확인:
   - comprehensive_report, journalist_report 등이 저장되어 있어야 함
   - detected_categories에 JSON 배열 (예: `["1-1-1", "1-7-3"]`)

**4. 중복 방지 테스트**

같은 URL로 다시 분석 요청:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://n.news.naver.com/article/001/0014912345"}'
```

**예상 출력**:
```
📌 기존 기사 사용 (ID: 1)
💾 분석 결과 저장 완료 (ID: 2)
```

→ 기사는 재사용, 분석 결과만 새로 저장

#### 성공 기준

- [x] 서버 로그에 "💾 분석 결과 저장 완료" 출력
- [x] Supabase에 데이터가 실제로 저장됨
- [x] 같은 URL 재분석 시 "📌 기존 기사 사용" 메시지
- [x] 프론트엔드에서 분석 결과 정상 표시 (기존과 동일)

---

## Phase 2: 사용자 인증 및 개인화 (3-5일)

**목표**: 로그인 기능 추가 + 내가 분석한 기사 목록 보기

### Step 2.1: Supabase Auth 설정

#### Supabase Console 설정

1. **Email Provider 활성화** (기본 활성화됨)
   - Authentication → Providers → Email
   - "Enable Email Provider" 체크

2. **Google OAuth 추가** (선택사항)
   - [Google Cloud Console](https://console.cloud.google.com) 접속
   - 새 프로젝트 생성 → API 및 서비스 → OAuth 2.0 클라이언트 ID 생성
   - 승인된 리디렉션 URI 추가:
     ```
     https://[your-project-ref].supabase.co/auth/v1/callback
     ```
   - Client ID와 Secret을 복사
   - Supabase Console → Authentication → Providers → Google
   - Client ID와 Secret 입력 후 저장

3. **Kakao OAuth 추가** (한국 사용자용, 선택사항)
   - [Kakao Developers](https://developers.kakao.com) 접속
   - 애플리케이션 추가 → 앱 키 확인
   - 플랫폼 설정 → Web 플랫폼 추가
   - Redirect URI 설정:
     ```
     https://[your-project-ref].supabase.co/auth/v1/callback
     ```
   - Supabase Console → Authentication → Providers → Kakao
   - Client ID와 Secret 입력 후 저장

4. **Site URL 설정**
   - Authentication → URL Configuration
   - Site URL:
     - Development: `http://localhost:3000`
     - Production: `https://your-domain.com`

5. **Redirect URLs 화이트리스트**
   - Redirect URLs에 추가:
     ```
     http://localhost:3000/**
     http://localhost:3000/auth/callback
     https://your-domain.com/**
     https://your-domain.com/auth/callback
     ```

---

### Step 2.2: 프론트엔드 Supabase 클라이언트 설정

#### 파일 생성: `frontend/lib/supabase.ts`

```typescript
// frontend/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Supabase 환경 변수가 설정되지 않았습니다.')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

#### 의존성 추가

```bash
cd frontend
npm install @supabase/supabase-js @supabase/auth-helpers-nextjs
```

---

### Step 2.3: 프론트엔드 인증 UI 구현

#### 파일 생성: `frontend/app/login/page.tsx`

```typescript
// frontend/app/login/page.tsx
'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleGoogleLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    })

    if (error) {
      setMessage(`오류: ${error.message}`)
    }
  }

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`
      }
    })

    if (error) {
      setMessage(`오류: ${error.message}`)
    } else {
      setMessage('✅ 이메일을 확인해주세요! 로그인 링크가 전송되었습니다.')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">로그인</h1>

        {/* Google 로그인 */}
        <button
          onClick={handleGoogleLogin}
          className="w-full bg-white border border-gray-300 py-3 rounded-lg hover:bg-gray-50 mb-4 flex items-center justify-center"
        >
          <span className="mr-2">🔵</span>
          Google로 계속하기
        </button>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">또는</span>
          </div>
        </div>

        {/* 이메일 로그인 */}
        <form onSubmit={handleEmailLogin}>
          <input
            type="email"
            placeholder="이메일 주소"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border p-3 rounded-lg mb-3"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? '전송 중...' : '이메일로 로그인'}
          </button>
        </form>

        {message && (
          <div className={`mt-4 p-3 rounded-lg text-sm ${
            message.startsWith('✅')
              ? 'bg-green-50 text-green-800'
              : 'bg-red-50 text-red-800'
          }`}>
            {message}
          </div>
        )}

        <p className="text-sm text-gray-500 mt-4 text-center">
          이메일로 로그인 시 Magic Link가 전송됩니다
        </p>

        <button
          onClick={() => router.push('/')}
          className="w-full mt-4 text-gray-600 hover:text-gray-800 text-sm"
        >
          ← 돌아가기
        </button>
      </div>
    </div>
  )
}
```

#### 파일 생성: `frontend/app/auth/callback/route.ts`

```typescript
// frontend/app/auth/callback/route.ts
import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/'

  if (code) {
    const cookieStore = cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          get(name: string) {
            return cookieStore.get(name)?.value
          },
          set(name: string, value: string, options: any) {
            cookieStore.set({ name, value, ...options })
          },
          remove(name: string, options: any) {
            cookieStore.delete({ name, ...options })
          },
        },
      }
    )

    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      return NextResponse.redirect(`${origin}${next}`)
    }
  }

  // 에러 발생 시 로그인 페이지로
  return NextResponse.redirect(`${origin}/login`)
}
```

---

### Step 2.4: 백엔드에 user_id 전달 로직 추가

#### 프론트엔드: 분석 요청 시 JWT 토큰 전달

**파일 수정**: `frontend/app/page.tsx` (또는 분석 요청하는 컴포넌트)

```typescript
// 분석 요청 함수 수정
const analyzeArticle = async (url: string) => {
  // 1. 현재 사용자 세션 확인
  const { data: { session } } = await supabase.auth.getSession()

  // 2. API 요청 (토큰이 있으면 헤더에 포함)
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(session ? { 'Authorization': `Bearer ${session.access_token}` } : {})
    },
    body: JSON.stringify({ url })
  })

  return response.json()
}
```

#### 백엔드: JWT 검증 및 user_id 추출

**파일 수정**: `backend/main.py`

```python
from fastapi import Request, HTTPException
from supabase import create_client  # 추가

# Supabase 클라이언트 초기화 (JWT 검증용)
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if supabase_url and supabase_key:
    supabase_client = create_client(supabase_url, supabase_key)
else:
    supabase_client = None


def get_user_id_from_token(request: Request) -> Optional[str]:
    """
    요청 헤더에서 JWT 토큰을 추출하고 사용자 ID 반환

    Returns:
        user_id (UUID) 또는 None (비로그인)
    """
    if not supabase_client:
        return None

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]

    try:
        # Supabase JWT 검증
        user = supabase_client.auth.get_user(token)
        return user.user.id
    except Exception as e:
        print(f"⚠️  JWT 검증 실패: {str(e)}")
        return None


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_article(body: AnalyzeRequest, request: Request):
    """분석 엔드포인트 (인증 선택)"""

    # 사용자 ID 추출 (로그인한 경우에만)
    user_id = get_user_id_from_token(request)
    if user_id:
        print(f"👤 로그인 사용자: {user_id}")
    else:
        print(f"👤 비로그인 사용자")

    try:
        # ... 기존 분석 로직 ...

        # DB 저장 시 user_id 전달
        await db_manager.save_analysis(
            article_data=article_data,
            analysis_result=result,
            duration=duration,
            user_id=user_id  # Phase 2에서 활성화
        )

        return result

    except Exception as e:
        # ... 에러 처리 ...
```

---

### Step 2.5: 마이페이지 구현

#### 파일 생성: `frontend/app/my-analyses/page.tsx`

```typescript
// frontend/app/my-analyses/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

interface Analysis {
  id: number
  created_at: string
  comprehensive_report: string
  articles: {
    title: string
    url: string
    publisher: string
  }
}

export default function MyAnalysesPage() {
  const router = useRouter()
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    checkAuthAndFetch()
  }, [])

  const checkAuthAndFetch = async () => {
    // 1. 로그인 확인
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) {
      router.push('/login')
      return
    }

    setUser(user)

    // 2. 내 분석 결과 조회
    fetchMyAnalyses(user.id)
  }

  const fetchMyAnalyses = async (userId: string) => {
    const { data, error } = await supabase
      .from('analysis_results')
      .select(`
        id,
        created_at,
        comprehensive_report,
        articles (
          title,
          url,
          publisher
        )
      `)
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(20)

    if (error) {
      console.error('분석 결과 조회 실패:', error)
    } else {
      setAnalyses(data as Analysis[])
    }

    setLoading(false)
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">내가 분석한 기사</h1>
        <div className="flex gap-3">
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
          >
            홈으로
          </button>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            로그아웃
          </button>
        </div>
      </div>

      {/* 사용자 정보 */}
      {user && (
        <div className="bg-blue-50 p-4 rounded-lg mb-6">
          <p className="text-sm text-gray-600">로그인: {user.email}</p>
        </div>
      )}

      {/* 분석 결과 목록 */}
      {analyses.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-600 mb-4">아직 분석한 기사가 없습니다.</p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            첫 기사 분석하기
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {analyses.map((analysis) => (
            <div key={analysis.id} className="border rounded-lg p-5 hover:shadow-md transition-shadow bg-white">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-lg flex-1">{analysis.articles.title}</h3>
              </div>

              <div className="flex items-center gap-3 text-sm text-gray-500 mb-3">
                <span>{analysis.articles.publisher}</span>
                <span>•</span>
                <span>{new Date(analysis.created_at).toLocaleDateString('ko-KR')}</span>
              </div>

              <div className="flex gap-2">
                <a
                  href={`/result?id=${analysis.id}`}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  리포트 다시 보기
                </a>
                <a
                  href={analysis.articles.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
                >
                  원문 보기 ↗
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

#### 네비게이션 바에 로그인 버튼 추가

**파일 수정**: `frontend/app/layout.tsx` (또는 네비게이션 컴포넌트)

```typescript
// 헤더에 로그인 상태 표시 및 버튼 추가
'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export function Header() {
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    // 초기 사용자 확인
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user)
    })

    // 인증 상태 변경 리스너
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  return (
    <header className="border-b">
      <div className="container mx-auto flex justify-between items-center p-4">
        <h1 className="text-xl font-bold">CR-Check</h1>

        <div className="flex gap-3">
          {user ? (
            <>
              <a href="/my-analyses" className="px-4 py-2 bg-blue-600 text-white rounded-lg">
                내 분석 기록
              </a>
              <span className="px-4 py-2 text-gray-600">{user.email}</span>
            </>
          ) : (
            <a href="/login" className="px-4 py-2 bg-gray-200 rounded-lg">
              로그인
            </a>
          )}
        </div>
      </div>
    </header>
  )
}
```

---

## Phase 3: 통계 대시보드 (5-7일)

**목표**: 언론사별 분석 통계, 실시간 트렌드 표시

### Step 3.1: 통계 쿼리 함수 생성 (Supabase)

#### Supabase SQL Editor에서 실행

```sql
-- ============================================
-- 통계 함수들
-- ============================================

-- 1. 언론사별 통계
CREATE OR REPLACE FUNCTION get_publisher_stats()
RETURNS TABLE (
  publisher TEXT,
  total_analyses BIGINT,
  avg_duration FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.publisher,
    COUNT(ar.id) as total_analyses,
    AVG(ar.duration_seconds) as avg_duration
  FROM articles a
  JOIN analysis_results ar ON a.id = ar.article_id
  WHERE a.publisher IS NOT NULL
  GROUP BY a.publisher
  ORDER BY total_analyses DESC
  LIMIT 20;
END;
$$ LANGUAGE plpgsql;


-- 2. 실시간 트렌드 (최근 24시간)
CREATE OR REPLACE FUNCTION get_trending_articles(hours_ago INT DEFAULT 24)
RETURNS TABLE (
  article_id BIGINT,
  title TEXT,
  url TEXT,
  publisher TEXT,
  analysis_count BIGINT,
  latest_analysis TIMESTAMP
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id as article_id,
    a.title,
    a.url,
    a.publisher,
    COUNT(ar.id) as analysis_count,
    MAX(ar.created_at) as latest_analysis
  FROM articles a
  JOIN analysis_results ar ON a.id = ar.article_id
  WHERE ar.created_at >= NOW() - INTERVAL '1 hour' * hours_ago
  GROUP BY a.id, a.title, a.url, a.publisher
  ORDER BY analysis_count DESC, latest_analysis DESC
  LIMIT 10;
END;
$$ LANGUAGE plpgsql;


-- 3. 전체 통계 요약
CREATE OR REPLACE FUNCTION get_overall_stats()
RETURNS TABLE (
  total_articles BIGINT,
  total_analyses BIGINT,
  avg_duration FLOAT,
  unique_users BIGINT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    COUNT(DISTINCT a.id) as total_articles,
    COUNT(ar.id) as total_analyses,
    AVG(ar.duration_seconds) as avg_duration,
    COUNT(DISTINCT ar.user_id) FILTER (WHERE ar.user_id IS NOT NULL) as unique_users
  FROM articles a
  LEFT JOIN analysis_results ar ON a.id = ar.article_id;
END;
$$ LANGUAGE plpgsql;
```

---

### Step 3.2: 백엔드 통계 API 엔드포인트 추가

**파일 수정**: `backend/main.py`

```python
@app.get("/stats/trending")
async def get_trending_articles(hours: int = 24):
    """
    최근 N시간 내 가장 많이 분석된 기사

    Args:
        hours: 조회 기간 (기본 24시간)

    Returns:
        실시간 트렌드 기사 목록
    """
    if not supabase_client:
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    try:
        response = supabase_client.rpc('get_trending_articles', {'hours_ago': hours}).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@app.get("/stats/publishers")
async def get_publisher_stats():
    """
    언론사별 분석 횟수 및 평균 소요 시간

    Returns:
        언론사별 통계
    """
    if not supabase_client:
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    try:
        response = supabase_client.rpc('get_publisher_stats').execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@app.get("/stats/overall")
async def get_overall_stats():
    """
    전체 통계 요약

    Returns:
        총 기사 수, 총 분석 수, 평균 소요 시간, 사용자 수
    """
    if not supabase_client:
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    try:
        response = supabase_client.rpc('get_overall_stats').execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")
```

---

### Step 3.3: 대시보드 페이지 구현

#### 파일 생성: `frontend/app/stats/page.tsx`

```typescript
// frontend/app/stats/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface TrendingArticle {
  article_id: number
  title: string
  url: string
  publisher: string
  analysis_count: number
  latest_analysis: string
}

interface PublisherStat {
  publisher: string
  total_analyses: number
  avg_duration: number
}

interface OverallStats {
  total_articles: number
  total_analyses: number
  avg_duration: number
  unique_users: number
}

export default function StatsPage() {
  const router = useRouter()
  const [trending, setTrending] = useState<TrendingArticle[]>([])
  const [publishers, setPublishers] = useState<PublisherStat[]>([])
  const [overall, setOverall] = useState<OverallStats | null>(null)
  const [loading, setLoading] = useState(true)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetchAllStats()
  }, [])

  const fetchAllStats = async () => {
    try {
      const [trendingRes, publishersRes, overallRes] = await Promise.all([
        fetch(`${API_URL}/stats/trending`),
        fetch(`${API_URL}/stats/publishers`),
        fetch(`${API_URL}/stats/overall`)
      ])

      const trendingData = await trendingRes.json()
      const publishersData = await publishersRes.json()
      const overallData = await overallRes.json()

      setTrending(trendingData)
      setPublishers(publishersData)
      setOverall(overallData)
    } catch (error) {
      console.error('통계 조회 실패:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">통계 불러오는 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">CR 통계 대시보드</h1>
        <button
          onClick={() => router.push('/')}
          className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
        >
          ← 홈으로
        </button>
      </div>

      {/* 전체 통계 요약 */}
      {overall && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-blue-50 p-6 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">총 분석 기사</p>
            <p className="text-3xl font-bold text-blue-600">{overall.total_articles.toLocaleString()}</p>
          </div>
          <div className="bg-green-50 p-6 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">총 분석 횟수</p>
            <p className="text-3xl font-bold text-green-600">{overall.total_analyses.toLocaleString()}</p>
          </div>
          <div className="bg-purple-50 p-6 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">평균 소요 시간</p>
            <p className="text-3xl font-bold text-purple-600">{overall.avg_duration.toFixed(1)}초</p>
          </div>
          <div className="bg-orange-50 p-6 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">등록 사용자</p>
            <p className="text-3xl font-bold text-orange-600">{overall.unique_users.toLocaleString()}</p>
          </div>
        </div>
      )}

      {/* 실시간 트렌드 */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4 flex items-center">
          🔥 실시간 인기 분석 <span className="text-sm font-normal text-gray-500 ml-2">(최근 24시간)</span>
        </h2>

        {trending.length === 0 ? (
          <div className="bg-gray-50 p-8 rounded-lg text-center text-gray-500">
            아직 분석된 기사가 없습니다.
          </div>
        ) : (
          <div className="grid gap-4">
            {trending.map((item, idx) => (
              <div key={item.article_id} className="border rounded-lg p-5 hover:shadow-md transition-shadow bg-white">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <span className="text-2xl font-bold text-blue-600">#{idx + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg mb-2">{item.title}</h3>
                    <div className="flex items-center gap-3 text-sm text-gray-500 mb-3">
                      <span className="font-medium">{item.publisher}</span>
                      <span>•</span>
                      <span>분석 {item.analysis_count}회</span>
                      <span>•</span>
                      <span>최근: {new Date(item.latest_analysis).toLocaleString('ko-KR')}</span>
                    </div>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline text-sm"
                    >
                      원문 보기 ↗
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 언론사별 통계 */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">📰 언론사별 분석 통계</h2>

        {publishers.length === 0 ? (
          <div className="bg-gray-50 p-8 rounded-lg text-center text-gray-500">
            통계 데이터가 없습니다.
          </div>
        ) : (
          <div className="bg-white border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">순위</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">언론사</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-700">분석 횟수</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-700">평균 소요 시간</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {publishers.map((pub, idx) => (
                  <tr key={pub.publisher} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-500">{idx + 1}</td>
                    <td className="px-6 py-4 text-sm font-medium">{pub.publisher}</td>
                    <td className="px-6 py-4 text-sm text-right">{pub.total_analyses}회</td>
                    <td className="px-6 py-4 text-sm text-right">{pub.avg_duration.toFixed(1)}초</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 주의사항 */}
      <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-gray-700">
          💡 <strong>통계 안내:</strong> 이 통계는 CR-Check를 통해 분석된 기사들의 데이터를 기반으로 합니다.
          특정 언론사의 분석 횟수가 많다는 것은 해당 언론사의 기사가 많이 검토되었음을 의미하며,
          품질에 대한 절대적 평가는 아닙니다.
        </p>
      </div>
    </div>
  )
}
```

#### 네비게이션에 통계 링크 추가

```typescript
// 헤더에 통계 페이지 링크 추가
<a href="/stats" className="px-4 py-2 text-gray-700 hover:text-blue-600">
  📊 통계
</a>
```

---

## 보안 체크리스트

실행 전 반드시 확인해야 할 보안 사항:

- [ ] **Service Role Key를 `.env`에만 저장** (Git에 커밋 금지)
  - `.gitignore`에 `.env` 추가 확인

- [ ] **Anon Key는 프론트엔드에 노출 가능** (RLS로 보호됨)
  - RLS 정책이 올바르게 설정되어 있는지 확인

- [ ] **RLS 정책이 올바르게 설정됨**
  - 읽기: 공개 (통계용)
  - 쓰기: Service Role만 가능 (백엔드 전용)

- [ ] **JWT 토큰 검증 로직 추가됨**
  - 백엔드에서 `get_user_id_from_token` 함수 사용

- [ ] **CORS 설정이 프로덕션 도메인으로 제한됨**
  - `main.py`의 `allow_origins` 확인

- [ ] **환경 변수가 프로덕션 환경에 설정됨**
  - Railway/Render/Vercel 환경 변수 설정 확인

- [ ] **Supabase RLS 테스트**
  - Supabase Console에서 "Test RLS Policies" 실행

- [ ] **SQL Injection 방지**
  - Supabase 클라이언트 메서드 사용 (raw query 지양)

---

## 타임라인 요약

```
Week 1 (Phase 1): 아카이빙 시스템
├─ Day 1: Supabase 프로젝트 생성 + 환경 변수 설정
├─ Day 2: 데이터베이스 스키마 생성 + RLS 설정
├─ Day 3: 백엔드 DatabaseManager 구현 + main.py 수정
└─ Day 4: 테스트 및 검증 (중복 방지, 저장 확인)

Week 2 (Phase 2): 사용자 인증 및 개인화
├─ Day 5: Supabase Auth 설정 (Google/Email OAuth)
├─ Day 6-7: 프론트엔드 로그인 UI + 콜백 핸들러
├─ Day 8: 백엔드 JWT 검증 로직 추가
├─ Day 9: 마이페이지 구현
└─ Day 10: user_id 연동 테스트 (로그인/비로그인)

Week 3-4 (Phase 3): 통계 대시보드
├─ Day 11-12: Supabase 통계 함수 작성 (SQL)
├─ Day 13: 백엔드 통계 API 엔드포인트 추가
├─ Day 14-16: 대시보드 UI 구현
└─ Day 17: 통합 테스트 및 최적화
```

**예상 총 소요 기간**: 3-4주 (파트타임 기준)

---

## 주의사항

### 1. 점진적 배포 전략

**Phase 1 완료 후 즉시 배포 권장**:
- 이유: 데이터 축적이 시작되어야 Phase 3 통계가 의미 있음
- 방법: Phase 1만 배포 → 사용자 피드백 수집 → Phase 2/3 순차 배포

### 2. DB 비용 모니터링

**Supabase 무료 티어 제한**:
- Database: 500MB
- Auth users: 50,000 MAU (Monthly Active Users)
- Edge Functions: 500K invocations/month
- Storage: 1GB

**예상 데이터 사용량**:
- 분석 1회당 약 10-20KB (리포트 텍스트)
- 500MB = 약 25,000~50,000회 분석 저장 가능

**모니터링 방법**:
- Supabase Dashboard → Settings → Database → Usage 확인
- 80% 도달 시 유료 플랜 고려 또는 오래된 데이터 아카이빙

### 3. 개인정보 처리방침

**법적 고지 필요**:
- 사용자 데이터(이메일, 분석 기록) 저장 전 동의 필요
- 개인정보 처리방침 페이지 작성 권장
- 예시: "CR-Check는 서비스 개선을 위해 분석 데이터를 저장합니다. 자세한 내용은 [개인정보 처리방침]을 참조하세요."

### 4. 백업 전략

**Supabase 자동 백업**:
- Pro 플랜 이상: 자동 일일 백업
- 무료 플랜: 자동 백업 없음 (수동 필요)

**수동 백업 방법**:
```bash
# PostgreSQL dump (Supabase 제공 도구 사용)
supabase db dump > backup_$(date +%Y%m%d).sql
```

**권장 백업 주기**:
- 주간: 수동 백업 (중요 데이터)
- 월간: 전체 데이터 export (JSON/CSV)

### 5. 인덱스 최적화

**데이터 증가 시 성능 저하 방지**:
- 10,000개 레코드 이상 시 쿼리 성능 모니터링
- Supabase Dashboard → Database → Query Performance 확인
- 느린 쿼리 발견 시 인덱스 추가:
  ```sql
  CREATE INDEX idx_custom ON table_name(column_name);
  ```

### 6. API Rate Limiting

**백엔드 보호**:
- Phase 2 이후 로그인 없는 무한 분석 방지 필요
- FastAPI Rate Limiting 미들웨어 추가 고려:
  ```python
  from slowapi import Limiter
  limiter = Limiter(key_func=get_remote_address)

  @app.post("/analyze")
  @limiter.limit("10/hour")  # 비로그인 사용자: 시간당 10회
  async def analyze_article(...):
      ...
  ```

### 7. 에러 로깅 및 모니터링

**프로덕션 환경 권장 도구**:
- Sentry: 에러 추적 (백엔드/프론트엔드)
- Supabase Logs: DB 쿼리 로그
- Vercel Analytics: 프론트엔드 성능

---

## 다음 단계

Phase 1부터 순차적으로 진행하세요:

1. ✅ 이 문서를 팀원과 공유하여 리뷰
2. ✅ Supabase 프로젝트 생성 (Step 1.1)
3. ✅ 환경 변수 설정 확인
4. ✅ 데이터베이스 스키마 실행 (Step 1.2)
5. ✅ 백엔드 코드 구현 (Step 1.3-1.4)
6. ✅ 테스트 및 검증 (Step 1.5)
7. ✅ Phase 1 배포 → 데이터 축적 시작
8. ✅ Phase 2 진행 (사용자 피드백 반영)

각 Phase 완료 시마다 이 문서를 업데이트하여 진행 상황을 체크하세요.

---

**작성일**: 2025-12-18
**버전**: 1.0
**기반 문서**: [DB_CONSTRUCTION_PLAN.md](./DB_CONSTRUCTION_PLAN.md)
