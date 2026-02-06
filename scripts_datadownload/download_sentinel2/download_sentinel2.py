import os
import json
import time
import zipfile
import boto3
import pandas as pd
import requests
import tqdm
import logging
import urllib3
import csv
from io import BytesIO
from datetime import datetime, timedelta
from multiprocessing import Pool
from shapely.geometry import Polygon

# [설정] SSL 인증서 검증 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# 0. 로깅(Logging) 설정 함수
# ============================================================================
def setup_logger(log_dir=None, log_filename=None):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        if not log_filename:
            log_filename = f"sentinel2_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(log_dir, log_filename)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = logging.getLogger(__name__)

# ============================================================================
# 1. 유틸리티 함수 (파일명 파싱)
# ============================================================================
def extract_metadata_from_name(product_name):
    """
    Sentinel-2 파일명에서 연도(Year)와 타일명(Tile ID)을 추출합니다.
    """
    try:
        parts = product_name.split('_')
        date_str = parts[2]
        year = date_str[:4]
        
        tile_id = "UnknownTile"
        for part in parts:
            if part.startswith('T') and len(part) == 6 and part[1].isdigit():
                tile_id = part[1:] 
                break
                
        return year, tile_id
    except Exception as e:
        return "UnknownYear", "UnknownTile"

# ============================================================================
# 2. Sentinel-2 검색 (Searcher) 클래스
# ============================================================================
class Sentinel2Searcher:
    def __init__(self):
        self.api_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

    def _bbox_to_wkt(self, bbox):
        minx, miny, maxx, maxy = bbox
        coords = [
            (minx, miny), (maxx, miny),
            (maxx, maxy), (minx, maxy),
            (minx, miny)
        ]
        poly = Polygon(coords)
        return poly.wkt

    def _build_date_chunks(self, start_date, end_date):
        if (end_date - start_date).days <= 5:
            return [start_date]
        return pd.date_range(start=start_date, end=end_date, freq='5D')

    def search_products(self, region_name, bbox, start_date, end_date):
        geometry_wkt = self._bbox_to_wkt(bbox)
        all_data = []
        
        date_chunks = self._build_date_chunks(start_date, end_date)
        
        logger.info(f"검색 시작: {region_name} ({start_date.date()} ~ {end_date.date()})")
        
        for date in tqdm.tqdm(date_chunks, desc=f"Querying {region_name}"):
            chunk_start = date
            chunk_end = date + timedelta(days=5)
            if chunk_end > end_date:
                chunk_end = end_date

            start_str = chunk_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            end_str = chunk_end.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            date_filter = (
                f"ContentDate/Start gt {start_str} and "
                f"ContentDate/Start lt {end_str}"
            )
            
            query = (
                f"$filter=Collection/Name eq 'SENTINEL-2' and "
                f"OData.CSC.Intersects(area=geography'SRID=4326;{geometry_wkt}') and "
                f"{date_filter}&$top=1000"
            )
            
            full_url = f"{self.api_url}?{query}"
            
            try:
                response = requests.get(full_url)
                if response.ok:
                    json_data = response.json()
                    products = json_data.get('value', [])
                    if products:
                        df = pd.DataFrame.from_dict(products)
                        all_data.append(df)
                else:
                    logger.warning(f"API 요청 실패: {full_url}")
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"API 요청 에러: {e}")

        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            result_df.drop_duplicates(subset=['Id'], inplace=True)
            logger.info(f"'{region_name}' 검색 완료: 총 {len(result_df)}개 데이터 발견")
            return result_df
        else:
            logger.info(f"'{region_name}' 검색 결과가 없습니다.")
            return pd.DataFrame()

# ============================================================================
# 3. Sentinel-2 다운로드 (Downloader) 클래스
# ============================================================================
class Sentinel2Downloader:
    def __init__(self, key_id, secret_key):
        self.key_id = key_id
        self.secret_key = secret_key
        self.endpoint_url = 'https://eodata.dataspace.copernicus.eu'
        self.bucket_name = 'eodata' 

    def _get_bucket(self):
        session = boto3.session.Session()
        s3 = boto3.resource(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.key_id,
            aws_secret_access_key=self.secret_key,
            region_name='default'
        )
        return s3.Bucket(self.bucket_name)

    def _compress_and_save(self, bucket, product_path, zip_path):
        prefix = product_path
        if prefix.startswith("/eodata/"):
            prefix = prefix.replace("/eodata/", "", 1)
        elif prefix.startswith("eodata/"):
            prefix = prefix.replace("eodata/", "", 1)
        prefix = prefix.lstrip("/")
        
        files = list(bucket.objects.filter(Prefix=prefix))
        if not files:
            return False, "S3 파일 없음"

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    if file.key.endswith("/"): continue
                    relative_path = file.key.replace(prefix, "").lstrip("/")
                    
                    file_data = BytesIO()
                    bucket.download_fileobj(file.key, file_data)
                    file_data.seek(0)
                    zipf.writestr(relative_path, file_data.read())
            return True, "성공"
        except Exception as e:
            return False, str(e)

    def download_single_product(self, product_path, save_dir, product_name):
        """
        다운로드를 수행하고 결과 상태(Status)와 메시지를 반환합니다.
        """
        os.makedirs(save_dir, exist_ok=True)

        zip_path = os.path.join(save_dir, f"{product_name}.zip")
        temp_path = zip_path + ".tmp"

        # 1. 이미 존재하는 경우 (Skip)
        if os.path.exists(zip_path):
            logger.info(f"[SKIP] 이미 존재함: {product_name}")
            return "Success (Skipped)", "File already exists"

        try:
            bucket = self._get_bucket()
            success, msg = self._compress_and_save(bucket, product_path, temp_path)
            
            if success:
                os.rename(temp_path, zip_path)
                logger.info(f"[DONE] 다운로드 완료: {product_name}")
                return "Success", "Downloaded successfully"
            else:
                logger.warning(f"[FAIL] 다운로드 실패 ({product_name}): {msg}")
                if os.path.exists(temp_path): os.remove(temp_path)
                return "Failed", msg
                
        except Exception as e:
            logger.error(f"[ERR] 처리 중 에러 ({product_name}): {e}")
            if os.path.exists(temp_path): os.remove(temp_path)
            return "Failed", str(e)

# ============================================================================
# 4. 병렬 처리 워커
# ============================================================================
def worker_download(args):
    """
    개별 프로세스에서 실행되는 워커.
    """
    product_path, save_dir, name, tile_id, key, secret, log_dir, log_filename = args
    
    global logger
    if not logger.hasHandlers():
        logger = setup_logger(log_dir, log_filename)
        
    downloader = Sentinel2Downloader(key, secret)
    status, msg = downloader.download_single_product(product_path, save_dir, name)
    
    return {
        "filename": name,
        "tile": tile_id,
        "status": status,
        "message": msg
    }

# ============================================================================
# 5. 설정 및 메인 실행
# ============================================================================
def load_config(config_path='config.json'):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"설정 파일({config_path})이 없습니다.")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_date_range(date_settings):
    mode = date_settings.get('mode', 'fixed')
    if mode == 'relative':
        days_before = date_settings['relative_range']['days_before']
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_before)
        end_date = end_date.replace(hour=23, minute=59, second=59)
        start_date = start_date.replace(hour=0, minute=0, second=0)
    else:
        start_str = date_settings['fixed_range']['start_date']
        end_str = date_settings['fixed_range']['end_date']
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    return start_date, end_date

def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"설정 로드 실패: {e}")
        return

    # 1. 설정 로드
    settings = config['settings']
    path_settings = config.get('path_settings', {}) # 추가된 설정
    creds = config['auth']
    root_dir = settings['root_dir']
    
    # 2. 폴더명 가져오기 (기본값 설정)
    log_folder = path_settings.get('log_dir', 'Logs')
    history_folder = path_settings.get('search_history_dir', 'Search_History')
    report_folder = path_settings.get('report_dir', 'Reports')

    # 3. 로그 폴더 생성 및 로거 시작
    log_dir = os.path.join(root_dir, log_folder)
    global logger
    logger = setup_logger(log_dir)
    
    logger.info("========== 작업 시작 ==========")
    logger.info(f"경로 설정: Logs={log_folder}, History={history_folder}, Reports={report_folder}")
    
    # 4. 날짜 설정
    try:
        start_date, end_date = get_date_range(config['date_settings'])
        logger.info(f"기간: {start_date.date()} ~ {end_date.date()}")
    except Exception as e:
        logger.error(f"날짜 설정 오류: {e}")
        return

    searcher = Sentinel2Searcher()
    target_regions_config = config.get('target_regions', {})

    # 5. 설정된 region 데이터 표준화
    regions_to_process = []
    
    if isinstance(target_regions_config, dict):
        for name, data in target_regions_config.items():
            bbox = [data.get('min_x'), data.get('min_y'), data.get('max_x'), data.get('max_y')]
            regions_to_process.append((name, bbox))
    elif isinstance(target_regions_config, list):
        for r in target_regions_config:
            name = r['name']
            if isinstance(r['bbox'], dict):
                bbox = [r['bbox']['min_x'], r['bbox']['min_y'], r['bbox']['max_x'], r['bbox']['max_y']]
            else:
                bbox = r['bbox']
            regions_to_process.append((name, bbox))

    if not regions_to_process:
        logger.warning("config.json에 설정된 target_regions가 없습니다.")
        return

    # 6. 각 지역별 작업 수행
    for r_name, bbox in regions_to_process:
        logger.info(f"Processing Region: {r_name}")
        
        # 검색 목록 저장용 폴더 (Config에서 읽은 폴더명 사용)
        history_dir = os.path.join(root_dir, history_folder, r_name)
        os.makedirs(history_dir, exist_ok=True)
        
        # 다운로드 로그 저장용 폴더 (Config에서 읽은 폴더명 사용)
        report_dir = os.path.join(root_dir, report_folder, r_name)
        os.makedirs(report_dir, exist_ok=True)
        
        # CSV 파일명 생성
        date_suffix = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        search_csv_path = os.path.join(history_dir, f"Search_{r_name}_{date_suffix}.csv")
        download_log_path = os.path.join(report_dir, f"Download_Log_{r_name}_{date_suffix}.csv")

        df = pd.DataFrame()

        # [Step 1] 검색
        if settings['do_search']:
            try:
                df = searcher.search_products(r_name, bbox, start_date, end_date)
                if not df.empty:
                    df.to_csv(search_csv_path, index=False)
                    logger.info(f"검색 목록 저장: {search_csv_path}")
                else:
                    logger.info("검색 결과 없음.")
                    continue
            except Exception as e:
                logger.error(f"검색 오류: {e}")
                continue
        else:
            if os.path.exists(search_csv_path):
                df = pd.read_csv(search_csv_path)
            else:
                logger.warning("저장된 검색 목록이 없어 스킵합니다.")
                continue

        # [Step 2] 다운로드 및 로그 기록
        if settings['do_download'] and not df.empty:
            tasks = []
            
            for _, row in df.iterrows():
                s3_path = row.get('S3Path')
                name = row.get('Name')
                
                if s3_path and name:
                    year, tile_id = extract_metadata_from_name(name)
                    target_save_dir = os.path.join(root_dir, year, tile_id)
                    
                    tasks.append((
                        s3_path, 
                        target_save_dir,
                        name,
                        tile_id,
                        creds['access_key'], 
                        creds['secret_key'],
                        log_dir,
                        None
                    ))

            if not tasks:
                continue

            if settings['mode'] == 'TEST':
                logger.info(f">>> [TEST] 1개 파일만 다운로드")
                tasks = tasks[:1]
            
            logger.info(f"다운로드 시작 (총 {len(tasks)}개)")
            
            with open(download_log_path, 'w', newline='', encoding='utf-8') as f:
                csv_writer = csv.DictWriter(f, fieldnames=["filename", "tile", "status", "message"])
                csv_writer.writeheader()
                
                parallel_cnt = settings.get('max_threads', 1)
                
                if parallel_cnt > 1:
                    with Pool(processes=parallel_cnt) as pool:
                        results = tqdm.tqdm(pool.imap(worker_download, tasks), total=len(tasks), desc=f"DL-{r_name}")
                        for res in results:
                            csv_writer.writerow(res)
                            f.flush()
                else:
                    for task in tqdm.tqdm(tasks, desc=f"DL-{r_name}"):
                        res = worker_download(task)
                        csv_writer.writerow(res)
                        f.flush()

            logger.info(f"다운로드 로그 저장 완료: {download_log_path}")

    logger.info("========== 작업 완료 ==========")

if __name__ == "__main__":
    main()