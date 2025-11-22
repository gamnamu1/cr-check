"""
PDF 내보내기 모듈
WeasyPrint를 사용하여 분석 결과를 PDF로 변환
"""

from weasyprint import HTML, CSS
from datetime import datetime
from urllib.parse import quote
import io


def generate_pdf(analysis_result: dict) -> bytes:
    """
    분석 결과를 PDF로 변환

    Args:
        analysis_result: analyze_article()의 반환값

    Returns:
        PDF 바이트 데이터
    """

    article_info = analysis_result["article_info"]
    reports = analysis_result["reports"]

    # HTML 템플릿 생성
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>CR-Check 분석 결과 - {article_info['title']}</title>
    </head>
    <body>
        <div class="container">
            <!-- 헤더 -->
            <div class="header">
                <h1>CR-Check 언론윤리 분석 리포트</h1>
                <p class="subtitle">한국신문윤리위원회 윤리규범 기반 평가</p>
                <p class="date">생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
            </div>

            <!-- 기사 정보 -->
            <div class="section">
                <h2>📰 기사 정보</h2>
                <div class="info-box">
                    <p><strong>제목:</strong> {article_info['title']}</p>
                    <p><strong>URL:</strong> <a href="{article_info['url']}">{article_info['url']}</a></p>
                </div>
            </div>

            <!-- 시민용 종합 리포트 -->
            <div class="section">
                <h2>📊 시민을 위한 종합 리포트</h2>
                <div class="report-box">
                    <pre class="report-content">{reports['comprehensive']}</pre>
                </div>
            </div>

            <!-- 기자용 전문 리포트 -->
            <div class="section page-break">
                <h2>📊 기자를 위한 전문 리포트</h2>
                <div class="report-box">
                    <pre class="report-content">{reports['journalist']}</pre>
                </div>
            </div>

            <!-- 학생용 교육 리포트 -->
            <div class="section page-break">
                <h2>📊 학생을 위한 교육 리포트</h2>
                <div class="report-box">
                    <pre class="report-content">{reports['student']}</pre>
                </div>
            </div>

            <!-- 푸터 -->
            <div class="footer">
                <p>Powered by CR-Check Analysis Engine</p>
                <p>한국신문윤리위원회 윤리규범 기반 | cr-check.org</p>
            </div>
        </div>
    </body>
    </html>
    """

    # CSS 스타일
    css_content = """
    @page {
        size: A4;
        margin: 2cm;
    }

    body {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
    }

    .container {
        max-width: 800px;
        margin: 0 auto;
    }

    .header {
        text-align: center;
        margin-bottom: 2cm;
        padding-bottom: 1cm;
        border-bottom: 3px solid #1A237E;
    }

    .header h1 {
        color: #1A237E;
        font-size: 24pt;
        margin-bottom: 0.5cm;
        font-weight: bold;
    }

    .header .subtitle {
        color: #FFB300;
        font-size: 14pt;
        margin-bottom: 0.3cm;
    }

    .header .date {
        color: #666;
        font-size: 10pt;
    }

    .section {
        margin-bottom: 1.5cm;
    }

    .section h2 {
        color: #1A237E;
        font-size: 16pt;
        margin-bottom: 0.5cm;
        font-weight: bold;
        border-left: 4px solid #FFB300;
        padding-left: 0.3cm;
    }

    .info-box {
        background-color: #f5f5f5;
        padding: 0.5cm;
        border-radius: 5px;
        border-left: 3px solid #FFB300;
    }

    .info-box p {
        margin: 0.3cm 0;
    }

    .info-box strong {
        color: #1A237E;
        font-weight: bold;
    }

    .report-box {
        background-color: #fafafa;
        padding: 0.7cm;
        border-radius: 5px;
        border: 1px solid #ddd;
    }

    .report-content {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 10pt;
        line-height: 1.7;
        margin: 0;
    }

    .page-break {
        page-break-before: always;
    }

    .footer {
        margin-top: 2cm;
        padding-top: 0.5cm;
        border-top: 1px solid #ddd;
        text-align: center;
        font-size: 9pt;
        color: #999;
    }

    .footer p {
        margin: 0.2cm 0;
    }

    a {
        color: #FFB300;
        text-decoration: none;
    }
    """

    # HTML → PDF 변환
    html = HTML(string=html_content)
    css = CSS(string=css_content)

    pdf_bytes = html.write_pdf(stylesheets=[css])

    return pdf_bytes


def generate_pdf_response(analysis_result: dict, article_title: str):
    """
    FastAPI 응답용 PDF 생성

    Args:
        analysis_result: 분석 결과
        article_title: 기사 제목 (파일명 생성용)

    Returns:
        StreamingResponse 객체
    """
    from fastapi.responses import StreamingResponse

    pdf_bytes = generate_pdf(analysis_result)

    # 파일명 생성 (한글 제목은 URL 인코딩)
    safe_title = article_title[:50]  # 최대 50자
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"CR-Check_{safe_title}_{timestamp}.pdf"

    # URL 인코딩 (한글 지원)
    encoded_filename = quote(filename.encode('utf-8'))

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )
