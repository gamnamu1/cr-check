# Python 3.11 slim 베이스 이미지
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# WeasyPrint 시스템 종속성 설치
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY . .

# 포트 노출 (Railway가 자동으로 PORT 환경변수 제공)
EXPOSE 8000

# Uvicorn으로 FastAPI 실행
# Railway의 PORT 환경변수 사용, 기본값 8000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
