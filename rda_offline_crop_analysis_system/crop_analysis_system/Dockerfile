FROM continuumio/miniconda3:24.3.0-0

# 파이썬 관련 환경 변수 설정
# 1. .pyc 파일 생성 방지 (이미지 크기 절약)
# 2. 로그 버퍼링 비활성화 (Docker 로그에서 실시간 확인 가능)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/crop_analysis_system

# 1. 의존성 설치 (캐싱 효율을 위해 코드 복사보다 먼저 수행)
COPY environment.yml /app/environment.yml

# Conda 환경 생성 및 캐시 정리
## 주의: environment.yml의 'name' 속성과 아래 PATH 경로의 이름이 일치해야 합니다.
RUN conda env create -f /app/environment.yml && conda clean -afy
#RUN conda env update -n base --file /app/environment.yml && conda clean -afy
#RUN conda env create -f /app/environment.yml && \
#    conda clean -afy && \
#    find /opt/conda/ -follow -type f -name '*.a' -delete && \
#    find /opt/conda/ -follow -type f -name '*.pyc' -delete

# 생성된 Conda 가상환경을 기본 PATH로 설정 (activate 불필요하게 만듦)
ENV PATH=/opt/conda/envs/process/bin:$PATH
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 2. 소스 코드 및 실행 스크립트 복사
COPY . /app/crop_analysis_system
COPY entrypoint.sh /app/entrypoint.sh

# 실행 권한 부여

RUN chmod +x /app/entrypoint.sh

# Django 기본 포트 노출
EXPOSE 9000

# 컨테이너 실행 시 entrypoint.sh가 가장 먼저 실행됨
ENTRYPOINT ["/app/entrypoint.sh"]

# entrypoint 실행 후 기본 명령어 (Gunicorn 실행)
# --chdir 옵션으로 프로젝트 루트(manage.py가 있는 곳)를 지정
CMD ["gunicorn", "config.wsgi:application", "--chdir", "/app/crop_analysis_system", "--bind", "0.0.0.0:9000"]
