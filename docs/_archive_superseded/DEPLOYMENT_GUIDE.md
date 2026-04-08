# CR-Check 배포 가이드

이 문서는 CR-Check 애플리케이션을 Railway(백엔드)와 Vercel(프론트엔드)에 배포하는 방법을 설명합니다.

## 📋 배포 전 체크리스트

- [x] ✅ Dockerfile 생성 완료 (`backend/Dockerfile`)
- [x] ✅ railway.json 설정 완료 (`backend/railway.json`)
- [x] ✅ PDF 내보내기 기능 구현 완료 (`backend/export.py`, `/export-pdf` 엔드포인트)
- [ ] 🔲 Railway 계정 생성 (https://railway.app)
- [ ] 🔲 Vercel 계정 생성 (https://vercel.com)
- [ ] 🔲 GitHub 저장소 생성 및 코드 푸시

---

## 🚂 Part 1: Railway 백엔드 배포

### 1-1. Railway 프로젝트 생성

1. **Railway 로그인**: https://railway.app 접속 후 GitHub 계정으로 로그인
2. **New Project** 클릭
3. **Deploy from GitHub repo** 선택
4. CR-Check 저장소 선택 (또는 연결)

### 1-2. 환경변수 설정

Railway 프로젝트 설정에서 다음 환경변수를 추가하세요:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**설정 방법**:
1. Railway 프로젝트 대시보드 → **Variables** 탭 클릭
2. `ANTHROPIC_API_KEY` 입력
3. Anthropic API 키 값 붙여넣기
4. **Add** 클릭

### 1-3. 빌드 설정

Railway는 자동으로 `railway.json`을 감지하고 Dockerfile을 사용합니다.

**확인 사항**:
- Root Directory: `backend` (설정 필요)
- Builder: Dockerfile (자동 감지)
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT` (railway.json에 설정됨)

**Root Directory 설정**:
1. Railway 프로젝트 → **Settings** 탭
2. **Service Settings** 섹션
3. **Root Directory** 에 `backend` 입력
4. **Save** 클릭

### 1-4. 배포 실행

1. 설정 완료 후 자동으로 배포가 시작됩니다
2. **Deployments** 탭에서 배포 진행 상황 확인
3. 빌드 로그에서 다음 메시지 확인:
   ```
   ✅ ANTHROPIC_API_KEY 설정됨
   🚀 CR-Check API 서버 시작...
   ```

### 1-5. 배포 URL 확인

1. **Settings** → **Networking** → **Public Networking** 활성화
2. 생성된 도메인 확인 (예: `cr-check-backend.up.railway.app`)
3. 헬스체크 테스트:
   ```bash
   curl https://your-backend-url.railway.app/health
   ```

   예상 응답:
   ```json
   {
     "status": "healthy",
     "api_key_configured": true
   }
   ```

---

## ▲ Part 2: Vercel 프론트엔드 배포

### 2-1. 프론트엔드 환경변수 업데이트

**배포 전 필수**: Railway에서 받은 백엔드 URL로 프론트엔드 코드를 업데이트해야 합니다.

#### 옵션 A: 환경변수 사용 (권장)

1. `frontend/.env.production` 파일 생성:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```

2. `frontend/app/page.tsx` 수정 (Line 71):
   ```typescript
   // 변경 전:
   const response = await fetch("http://localhost:8000/analyze", {

   // 변경 후:
   const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analyze`, {
   ```

3. `frontend/app/result/page.tsx` 수정 (Line 114):
   ```typescript
   // 변경 전:
   const response = await fetch("http://localhost:8000/export-pdf", {

   // 변경 후:
   const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/export-pdf`, {
   ```

#### 옵션 B: 직접 URL 하드코딩

1. `frontend/app/page.tsx`와 `frontend/app/result/page.tsx`에서 `http://localhost:8000`을 Railway URL로 직접 변경

### 2-2. Vercel 프로젝트 생성

1. **Vercel 로그인**: https://vercel.com 접속 후 GitHub 계정으로 로그인
2. **Add New...** → **Project** 클릭
3. CR-Check 저장소 선택 (Import)

### 2-3. 빌드 설정

**Framework Preset**: Next.js (자동 감지됨)

**Root Directory**: `frontend` 설정 필요
- **Edit** 클릭
- Root Directory에 `frontend` 입력
- **Continue** 클릭

**Build and Output Settings** (기본값 사용):
- Build Command: `npm run build`
- Output Directory: `.next`
- Install Command: `npm install`

### 2-4. 환경변수 설정 (옵션 A 선택 시)

Vercel 프로젝트 설정에서:
1. **Environment Variables** 섹션
2. Key: `NEXT_PUBLIC_API_URL`
3. Value: `https://your-backend-url.railway.app`
4. **Add** 클릭

### 2-5. 배포 실행

1. **Deploy** 클릭
2. 배포 진행 상황 확인
3. 배포 완료 후 생성된 도메인 확인 (예: `cr-check.vercel.app`)

---

## 🧪 Part 3: 배포 테스트

### 3-1. 백엔드 API 테스트

```bash
# 헬스체크
curl https://your-backend-url.railway.app/health

# 분석 API 테스트 (POST)
curl -X POST https://your-backend-url.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://n.news.naver.com/mnews/article/023/0003907303"}'
```

### 3-2. 프론트엔드 전체 테스트

1. Vercel 도메인 접속 (예: `https://cr-check.vercel.app`)
2. 기사 URL 입력:
   ```
   https://n.news.naver.com/mnews/article/023/0003907303?sid=102
   ```
3. **기사 분석 시작** 클릭
4. 60-90초 대기
5. 3가지 리포트 확인:
   - 시민용 종합 리포트
   - 기자용 전문 리포트
   - 학생용 교육 리포트
6. **PDF로 결과 저장** 버튼 클릭하여 PDF 다운로드 테스트

### 3-3. 예상 문제 및 해결

#### 문제 1: "서버 오류가 발생했습니다"
- **원인**: Railway 백엔드 URL이 올바르지 않음
- **해결**: 프론트엔드 코드의 API URL 확인 및 재배포

#### 문제 2: CORS 오류
- **원인**: Railway 백엔드의 CORS 설정
- **해결**: `backend/main.py`의 `allow_origins`를 Vercel 도메인으로 변경:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://cr-check.vercel.app"],  # 또는 ["*"]
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

#### 문제 3: PDF 생성 실패
- **원인**: WeasyPrint 시스템 종속성 누락
- **해결**: Dockerfile의 apt-get 패키지 확인 (이미 설정됨)

#### 문제 4: API 키 오류
- **원인**: Railway 환경변수 미설정
- **해결**: Railway 프로젝트 Variables 탭에서 `ANTHROPIC_API_KEY` 확인

---

## 🔄 Part 4: 업데이트 및 재배포

### 코드 업데이트 시

1. **GitHub에 푸시**:
   ```bash
   git add .
   git commit -m "Update: ..."
   git push origin main
   ```

2. **자동 배포**:
   - Railway: 자동으로 감지하고 재배포
   - Vercel: 자동으로 감지하고 재배포

### 수동 재배포 (필요 시)

- **Railway**: Deployments → 최신 커밋 → **Redeploy** 클릭
- **Vercel**: Deployments → 최신 배포 → **Redeploy** 클릭

---

## 📊 Part 5: 모니터링 및 로그

### Railway 로그 확인

1. Railway 프로젝트 → **Deployments** 탭
2. 최신 배포 클릭 → **View Logs** 클릭
3. 실시간 로그 확인:
   ```
   📰 기사 스크래핑 시작: https://...
   ✅ 스크래핑 완료: ...
   🔍 기사 분석 시작...
   ✅ 분석 완료
   ```

### Vercel 로그 확인

1. Vercel 프로젝트 → **Logs** 탭
2. Runtime Logs 또는 Build Logs 선택

---

## 💰 Part 6: 비용 안내

### Railway (백엔드)

- **Hobby Plan**: $5/월 (500시간 실행 시간)
- **평균 사용량**: 분석 1회당 60-90초 → 월 300-500회 분석 가능

### Vercel (프론트엔드)

- **Hobby Plan**: 무료
- **제한**: 월 100GB 대역폭, 무제한 배포

### Anthropic API

- **Claude Haiku**: $0.25/M tokens (input), $1.25/M tokens (output)
- **Claude Sonnet**: $3/M tokens (input), $15/M tokens (output)
- **평균 비용**: 분석 1회당 약 $0.10-0.20

---

## 🔐 Part 7: 보안 권장사항

1. **API 키 관리**:
   - Railway 환경변수에만 저장
   - `.env` 파일은 `.gitignore`에 추가
   - GitHub에 API 키 절대 커밋 금지

2. **CORS 설정**:
   - 프로덕션에서는 `allow_origins=["*"]` 대신 특정 도메인 사용
   - 예: `allow_origins=["https://cr-check.vercel.app"]`

3. **Rate Limiting** (선택 사항):
   - 추후 FastAPI의 `slowapi` 라이브러리로 요청 제한 추가 고려

---

## 📚 Part 8: 다음 단계 (Optional)

### 커스텀 도메인 설정

1. **Vercel 커스텀 도메인**:
   - Vercel 프로젝트 → **Settings** → **Domains**
   - 도메인 추가 (예: `cr-check.com`)

2. **Railway 커스텀 도메인**:
   - Railway 프로젝트 → **Settings** → **Domains**
   - 도메인 추가 (예: `api.cr-check.com`)

### 성능 최적화

1. **CDN 캐싱**: Vercel은 자동으로 CDN 사용
2. **이미지 최적화**: Next.js Image 컴포넌트 활용
3. **API 응답 캐싱**: Redis 추가 고려 (향후)

---

## ✅ 배포 완료 체크리스트

배포가 완료되면 다음 항목들을 확인하세요:

- [ ] Railway 백엔드가 정상적으로 실행 중 (`/health` 엔드포인트 응답)
- [ ] Vercel 프론트엔드가 정상적으로 로드됨
- [ ] 실제 기사 URL로 분석 테스트 성공 (60-90초 내 결과 반환)
- [ ] 3가지 리포트가 모두 다른 톤으로 생성됨
- [ ] PDF 다운로드 기능 정상 작동
- [ ] 윤리규범 인용이 올바르게 하이라이팅됨
- [ ] 로딩 화면의 저널리즘 Tip이 랜덤으로 표시됨

---

## 🆘 문제 해결 및 지원

### 문제가 발생하면:

1. Railway 로그 확인
2. Vercel 로그 확인
3. 브라우저 개발자 도구의 Console 및 Network 탭 확인

### 일반적인 오류:

| 오류 메시지 | 원인 | 해결 방법 |
|------------|------|----------|
| "서버 오류가 발생했습니다" | Railway URL 불일치 | 프론트엔드 API URL 확인 |
| "API key not found" | 환경변수 미설정 | Railway Variables 확인 |
| "PDF 생성 실패" | WeasyPrint 오류 | Dockerfile 시스템 패키지 확인 |
| "CORS error" | CORS 설정 문제 | main.py의 allow_origins 확인 |

---

## 📞 연락처

- **GitHub Issues**: https://github.com/your-repo/cr-check/issues
- **이메일**: your-email@example.com

---

**배포 성공을 기원합니다! 🎉**
