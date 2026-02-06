import cdsapi
import os
import json
import datetime
import time
import csv
import logging
from collections import defaultdict

# xarray 임포트 (데이터 병합용)
try:
    import xarray as xr

    HAS_XARRAY = True
except ImportError:
    HAS_XARRAY = False


class ERA5DailyDownloader:
    """
    ERA5 Daily Statistics 데이터를 다운로드하고 관리하는 클래스

    기능:
    - config.json의 'auth' 정보를 이용한 인증
    - 파이썬 내부 파일 로깅 제거 (배치 파일 리다이렉션 이용)
    - CSV 로그 기록 (옵션)
    - 일평균(Daily Mean) 데이터 다운로드 및 월별 병합
    """

    def __init__(self, config_path='config.json'):
        self.config = self._load_config(config_path)
        self.settings = self.config.get('settings', {})
        self.auth = self.config.get('auth', {})

        # 로깅 초기화
        self.logger = self._setup_logging()

        # 기본 디렉토리 생성
        self._ensure_root_directory()

        # 라이브러리 체크
        if not HAS_XARRAY:
            self.logger.warning("'xarray'가 없어 월별 병합이 불가능합니다. (pip install xarray netCDF4)")

        # API 클라이언트 설정
        self.client = self._setup_client()

    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"설정 파일({path})을 찾을 수 없습니다.")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _setup_logging(self):
        """
        로깅을 설정합니다.
        파일 핸들러를 제거하고 콘솔(Stream) 핸들러만 설정합니다.
        로그 파일은 bat 실행 시 리다이렉션(>>)을 통해 생성됩니다.
        """
        logger = logging.getLogger("ERA5_Downloader")
        logger.setLevel(logging.DEBUG)
        logger.handlers = []

        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # 콘솔 핸들러 (배치 파일에서 이 출력을 캡처함)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        return logger

    def _ensure_root_directory(self):
        root_dir = self.settings.get('root_dir', './era5_downloads')
        if not os.path.exists(root_dir):
            os.makedirs(root_dir, exist_ok=True)
            self.logger.info(f"루트 저장 경로 생성: {root_dir}")

    def _setup_client(self):
        """
        config.json의 auth 정보를 사용하여 CDS API 클라이언트를 초기화합니다.
        """
        url = self.auth.get('url')
        key = self.auth.get('key')
        if not url or not key:
            self.logger.error("config.json에 'auth' 정보(url, key)가 누락되었습니다.")
            raise ValueError("config.json의 'auth' 항목에 url과 key가 필요합니다.")

        try:
            return cdsapi.Client(url=url, key=key)
        except Exception as e:
            self.logger.error(f"CDS API 클라이언트 초기화 실패: {e}")
            raise

    def _log_to_csv(self, record):
        """CSV 로그 파일에 한 줄을 추가합니다."""
        if not self.settings.get('save_csv_log', False):
            return

        log_dir = self.settings.get('logs_dir', './logs')
        # 로그 디렉토리가 없으면 생성 (CSV 로그용)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # 파일명을 log_{year}{month}.csv 형태로 동적 생성
        # record 딕셔너리에 있는 year, month 정보를 사용
        year = record.get('year', datetime.datetime.now().strftime('%Y'))
        month = record.get('month', datetime.datetime.now().strftime('%m'))

        csv_filename = f"log_{year}{month}.csv"
        csv_path = os.path.join(log_dir, csv_filename)

        file_exists = os.path.exists(csv_path)

        fieldnames = ['timestamp', 'status', 'region', 'variable', 'year', 'month', 'days', 'filename', 'elapsed_sec',
                      'message']

        try:
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()

                # timestamp 추가
                record['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow(record)
        except Exception as e:
            self.logger.error(f"CSV 로그 기록 실패: {e}")

    def get_target_dates_grouped(self):
        lookback_days = self.settings.get('lookback_days', 3)
        today = datetime.datetime.now()  # 코드 실행되는 날짜
        date_list = [today - datetime.timedelta(days=x) for x in range(lookback_days + 1)] # 오늘부터 룩백일까지의 날짜 리스트 생성
        date_list = sorted(date_list)

        grouped = defaultdict(list)
        for date in date_list:
            grouped[(date.year, date.month)].append(date.day)
        return grouped

    def _convert_bbox_to_area(self, region_data):
        return [
            region_data['max_y'],  # North
            region_data['min_x'],  # West
            region_data['min_y'],  # South
            region_data['max_x']  # East
        ]

    def _merge_and_save(self, temp_path, target_path):
        if not HAS_XARRAY:
            return False, "xarray 미설치"

        try:
            with xr.open_dataset(target_path) as ds_target, \
                    xr.open_dataset(temp_path) as ds_new:

                ds_merged = ds_target.combine_first(ds_new)
                temp_merged = target_path + ".tmp"
                ds_merged.to_netcdf(temp_merged)

            os.replace(temp_merged, target_path)
            os.remove(temp_path)
            return True, "병합 성공"
        except Exception as e:
            return False, str(e)

    def download_data(self):
        grouped_dates = self.get_target_dates_grouped()
        regions = self.config.get('regions', {})
        variables = self.config.get('variables', [])
        root_dir = self.settings.get('root_dir', './era5_downloads')
        dataset_name = self.settings.get('dataset_name', 'derived-era5-single-levels-daily-statistics')

        self.logger.info(f"작업 시작 (기간 그룹: {len(grouped_dates)}개, 룩백: {self.settings.get('lookback_days')}일)")

        for (year_int, month_int), days in grouped_dates.items():
            year_str = str(year_int)
            month_str = f"{month_int:02d}"

            self.logger.info(f">> 기간: {year_str}-{month_str}, 일자: {days}")

            for region_name, region_data in regions.items():
                safe_region = region_name.replace(" ", "_")
                save_dir = os.path.join(root_dir, year_str, month_str, safe_region)

                if not os.path.exists(save_dir):
                    os.makedirs(save_dir, exist_ok=True)

                area = self._convert_bbox_to_area(region_data)

                for var in variables:
                    start_time = time.time()
                    target_file = os.path.join(save_dir, f"{var}.nc")

                    # 요청 날짜 태그 (임시파일용)
                    days_tag = f"{min(days):02d}-{max(days):02d}"
                    temp_file = os.path.join(save_dir, f"{var}_temp_{days_tag}.nc")

                    request_params = {
                        'product_type': 'reanalysis',
                        'format': 'netcdf',
                        'variable': var,
                        'year': year_str,
                        'month': month_str,
                        'day': [f"{d:02d}" for d in days],
                        'daily_statistic': 'daily_mean',
                        'time_zone': 'utc+00:00',
                        'area': area,
                    }

                    log_record = {
                        'status': 'FAIL',
                        'region': region_name,
                        'variable': var,
                        'year': year_str,
                        'month': month_str,
                        'days': str(days),
                        'filename': f"{var}.nc",
                        'elapsed_sec': 0,
                        'message': ''
                    }

                    try:
                        self.logger.info(f"다운로드 요청: {region_name} - {var}")
                        self.client.retrieve(dataset_name, request_params, temp_file)

                        # 병합 로직
                        if os.path.exists(target_file):
                            success, msg = self._merge_and_save(temp_file, target_file)
                            if success:
                                self.logger.debug(f"병합 완료: {target_file}")
                                log_record['status'] = 'MERGED'
                                log_record['message'] = 'Existing file updated'
                            else:
                                self.logger.error(f"병합 실패: {msg}")
                                log_record['message'] = f"Merge failed: {msg}"
                        else:
                            os.rename(temp_file, target_file)
                            self.logger.info(f"새 파일 생성: {target_file}")
                            log_record['status'] = 'CREATED'
                            log_record['message'] = 'New file created'

                    except Exception as e:
                        self.logger.error(f"처리 중 오류: {e}")
                        log_record['message'] = str(e)

                    finally:
                        elapsed = time.time() - start_time
                        log_record['elapsed_sec'] = round(elapsed, 2)
                        self._log_to_csv(log_record)


def main():
    try:
        downloader = ERA5DailyDownloader()
        downloader.download_data()
    except Exception as e:
        logging.error(f"치명적 오류: {e}", exc_info=True)


if __name__ == "__main__":
    main()