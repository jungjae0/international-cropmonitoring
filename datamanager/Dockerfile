FROM andrejreznik/python-gdal:latest

# 작업 디렉토리 설정
WORKDIR /app

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

#
## 서버 실행
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "prj.wsgi:application", "0.0.0.0:7000", "crop_monitor.app:app"]




#FROM python:3.10-slim
#
#ENV PYTHONDONTWRITEBYTECODE=1
#ENV PYTHONUNBUFFERED=1
#
#WORKDIR /app
#
#RUN apt-get update && apt-get install -y --no-install-recommends \
#    software-properties-common \
#    curl \
#    gpg \
#    ca-certificates \
#    build-essential \
#    git \
#    gdal-bin \
#    libgdal-dev \
#    libspatialindex-dev \
#    libproj-dev \
#    && rm -rf /var/lib/apt/lists/*
#
#ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
#ENV C_INCLUDE_PATH=/usr/include/gdal
#
#
#COPY requirements.txt .
#RUN pip install --upgrade pip
#RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
#RUN pip install -r requirements.txt
#
#COPY . .


# 서버 실행
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "prj.wsgi:application", "0.0.0.0:7000", "crop_monitor.app:app"]
