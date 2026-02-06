# Python 기반 이미지 선택
FROM python:3

# 작업 디렉터리 설정
WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev

# 필요 패키지 설치
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


# 프로젝트 코드 복사
COPY . .


# 서버 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "prj.wsgi:application", "0.0.0.0:7000", "crop_monitor.app:app"]
