# Python 3.11 slim 베이스 이미지
FROM python:3.11-slim


# 작업 디렉토리 설정
WORKDIR /app

# WeasyPrint 시스템 종속성 설치
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
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
#
# 워커 2개. 동시 추출 상한(extract_api.MAX_CONCURRENT_EXTRACTIONS)은 프로세스별로
# 독립이므로, 서비스 전체 동시 추출 상한은 그 값의 2배가 된다.
#
# 순수 exec form(배열만)으로는 ${PORT} 확장이 되지 않아 sh -c로 감싼다.
# exec를 붙이는 이유: uvicorn master가 PID 1이 되어 SIGTERM을 직접 받고 워커에
# 전파한다. 셸이 PID 1로 남으면 재배포 시 정상 종료가 되지 않는다.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
