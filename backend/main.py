# backend/main.py
"""
CR-Check: Citizen-led News Article Quality Assessment Platform
Copyright (C) 2025 CR Project Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE file for details.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict
import os

from scraper import ArticleScraper
# [M6] analyzer → pipeline 교체. analyzer.py 파일 자체는 보존 (참조용)
from core.pipeline import analyze_article as run_pipeline, AnalysisResult
# [M6] Phase D에서 재설계 예정
# from export import generate_pdf_response

# FastAPI 앱 생성
app = FastAPI(
    title="CR-Check API",
    description="한국 언론 기사의 저널리즘 윤리 준수 여부를 평가하는 API",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 로컬 개발
        "http://localhost:3001",  # 로컬 개발 (대체 포트)
        "https://cr-check.com",   # 프로덕션 (예시)
        "https://cr-check.vercel.app", # Vercel 배포
        "https://www.cr-check.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 인스턴스 생성
scraper = ArticleScraper()


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
    api_key_exists = bool(os.environ.get("ANTHROPIC_API_KEY"))

    return {
        "status": "healthy",
        "api_key_configured": api_key_exists
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_article(request: AnalyzeRequest):
    """
    기사 URL을 분석하여 3가지 평가 리포트 생성

    ## 프로세스 (M6 — Sonnet Solo 아키텍처)
    1. URL에서 기사 스크래핑 (제목 + 본문)
    2. 청킹 → 벡터검색 → Sonnet Solo (패턴 식별)
    3. 규범 조회 → Sonnet (3종 리포트, cite 태그)
    4. CitationResolver (규범 원문 결정론적 치환)
    """
    try:
        # 1. 기사 스크래핑
        print(f"📰 기사 스크래핑 시작: {request.url}")
        article_data = scraper.scrape(str(request.url))
        article_text = article_data.get("content", "")
        print(f"✅ 스크래핑 완료: {article_data['title'][:50]}...")

        if not article_text or len(article_text.strip()) < 50:
            raise ValueError("기사 본문을 추출할 수 없거나 너무 짧습니다.")

        # 2. 파이프라인 실행
        print(f"🔍 파이프라인 분석 시작...")
        result: AnalysisResult = run_pipeline(article_text)
        print(f"✅ 파이프라인 완료 ({result.total_seconds:.1f}초)")

        # 3. 응답 구성 — 프론트엔드 호환 형식
        article_info = {
            "title": article_data.get("title", ""),
            "url": str(request.url),
        }

        # scraper 메타데이터 병합
        if article_data.get("publisher") and article_data["publisher"] != "미확인":
            article_info["publisher"] = article_data["publisher"]
        if article_data.get("publish_date") and article_data["publish_date"] != "미확인":
            article_info["publishDate"] = article_data["publish_date"]
        if article_data.get("journalist") and article_data["journalist"] != "미확인":
            article_info["journalist"] = article_data["journalist"]

        # Sonnet이 생성한 article_analysis 병합
        if result.report_result.article_analysis:
            article_info.update(result.report_result.article_analysis)

        return AnalyzeResponse(
            article_info=article_info,
            reports=result.report_result.reports,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        from datetime import datetime
        error_msg = (
            f"[{datetime.now()}] Error processing {request.url}: "
            f"{str(e)}\n{traceback.format_exc()}\n{'='*50}\n"
        )
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


# [M6] Phase D에서 재설계 예정 — 주석 처리
# @app.post("/export-pdf")
# async def export_to_pdf(analysis_result: AnalyzeResponse):
#     """분석 결과를 PDF로 변환하여 다운로드"""
#     try:
#         pdf_response = generate_pdf_response(
#             analysis_result.model_dump(),
#             analysis_result.article_info["title"]
#         )
#         return pdf_response
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"PDF 생성 중 오류가 발생했습니다: {str(e)}"
#         )


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
        reload=True
    )
