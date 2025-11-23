# backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict
import os

from scraper import ArticleScraper
from analyzer import ArticleAnalyzer
from export import generate_pdf_response

# FastAPI 앱 생성
app = FastAPI(
    title="CR-Check API",
    description="한국 언론 기사의 저널리즘 윤리 준수 여부를 평가하는 API",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 인스턴스 생성
scraper = ArticleScraper()
analyzer = ArticleAnalyzer()


# 요청/응답 모델
class AnalyzeRequest(BaseModel):
    url: HttpUrl

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://news.naver.com/main/read.nhn?mode=LSD&mid=sec&sid1=001&oid=001&aid=0012345678"
            }
        }


class AnalyzeResponse(BaseModel):
    article_info: Dict[str, str]
    reports: Dict[str, str]

    class Config:
        json_schema_extra = {
            "example": {
                "article_info": {
                    "title": "기사 제목",
                    "url": "https://..."
                },
                "reports": {
                    "comprehensive": "일반 시민용 종합 리포트...",
                    "journalist": "기자용 전문 리포트...",
                    "student": "학생용 교육 리포트..."
                }
            }
        }


# 엔드포인트
@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "message": "CR-Check API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (Railway, Render 등에서 사용)"""
    # API 키 확인
    api_key_exists = bool(os.environ.get("ANTHROPIC_API_KEY"))

    return {
        "status": "healthy",
        "api_key_configured": api_key_exists
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_article(request: AnalyzeRequest):
    print(f"📥 [Backend] Analysis request received for URL: {request.url}")
    """
    기사 URL을 분석하여 3가지 평가 리포트 생성

    ## 프로세스
    1. URL에서 기사 스크래핑 (제목 + 본문)
    2. Phase 1 (Haiku): 문제 카테고리 식별 (5-10초)
    3. Phase 2 (Sonnet): 3가지 리포트 생성 (30-50초)

    ## 리포트 종류
    - comprehensive: 일반 시민용 종합 리포트
    - journalist: 기자/작성자용 전문 리포트
    - student: 학생용 교육 리포트

    ## 평가 원칙
    - 윤리규범 기반: 한국신문윤리위원회 규범을 근거로
    - 서술형 평가: 점수/등급 없이 구체적 설명
    - 건설적 피드백: 개선 방향 제시
    """
    try:
        # 1. 기사 스크래핑
        print(f"📰 기사 스크래핑 시작: {request.url}")
        article_data = scraper.scrape(str(request.url))
        print(f"✅ 스크래핑 완료: {article_data['title'][:50]}...")

        # 2. 기사 분석 (2단계)
        print(f"🔍 기사 분석 시작...")
        result = await analyzer.analyze(article_data)
        print(f"✅ 분석 완료")

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


@app.post("/export-pdf")
async def export_to_pdf(analysis_result: AnalyzeResponse):
    """
    분석 결과를 PDF로 변환하여 다운로드

    ## 입력
    - analysis_result: /analyze 엔드포인트의 응답 데이터

    ## 출력
    - PDF 파일 (다운로드)
    """
    try:
        print(f"📄 PDF 생성 시작: {analysis_result.article_info['title'][:50]}...")

        pdf_response = generate_pdf_response(
            analysis_result.model_dump(),
            analysis_result.article_info["title"]
        )

        print(f"✅ PDF 생성 완료")
        return pdf_response

    except Exception as e:
        print(f"❌ PDF 생성 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF 생성 중 오류가 발생했습니다: {str(e)}"
        )


# 개발 환경에서 직접 실행
if __name__ == "__main__":
    import uvicorn

    # API 키 확인
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  경고: ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("설정 방법: export ANTHROPIC_API_KEY='your-key-here'")
    else:
        print("✅ ANTHROPIC_API_KEY 설정됨")

    print("\n🚀 CR-Check API 서버 시작...")
    print("📍 http://localhost:8000")
    print("📖 API 문서: http://localhost:8000/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 개발 환경에서 자동 리로드
    )
