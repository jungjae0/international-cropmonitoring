FROM python:3.10-slim

# 시스템 패키지 업데이트 및 필수 의존성 설치
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# GDAL 버전 확인 (디버깅용, 선택)
RUN gdalinfo --version || true

WORKDIR /usr/src/app

COPY . /usr/src/app

## requirements.txt 복사
#COPY requirements.txt /app/requirements.txt

# pip 업그레이드 및 패키지 설치
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["localtileserver"]
