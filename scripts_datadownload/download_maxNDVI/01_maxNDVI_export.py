import ee
import os
import json
import time
import csv
import warnings
import requests
from datetime import datetime

# ==========================================
# 1. SSL 인증 우회 및 환경 설정 (전역 설정)
# ==========================================
warnings.filterwarnings("ignore")
os.environ['CURL_CA_BUNDLE'] = ''

old_merge_environment_settings = requests.Session.merge_environment_settings

def merge_environment_settings(self, url, proxies, stream, verify, cert):
    settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
    settings['verify'] = False
    return settings

requests.Session.merge_environment_settings = merge_environment_settings


class GEECropMonitor:
    """
    Google Earth Engine을 사용하여 작물 모니터링 데이터를 처리하고 내보내는 클래스.
    설정 로드, GEE 인증, 이미지 처리, CSV 로깅 기능을 포함함.
    """

    def __init__(self, config_path='config.json'):
        self.config = self._load_config(config_path)
        # config에서 로그 파일명을 가져오고, 없으면 기본값 사용
        self.log_file = self.config.get('task_log_file', 'tasks_log.csv')
        self.project_id = self.config.get('project_id')
        self._init_log_file()

    def _load_config(self, path):
        """설정 파일 로드"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _init_log_file(self):
        """Task ID 기록을 위한 CSV 파일 초기화"""
        # 파일이 없으면 헤더 생성
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 헤더 작성
                writer.writerow(['Timestamp', 'Task ID', 'Description', 'Folder', 'Status', 'Note'])

    def _log_task_to_csv(self, task_id, description, folder, status="STARTED", note=""):
        """Task 정보를 CSV에 추가"""
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([timestamp, task_id, description, folder, status, note])
        except Exception as e:
            print(f"[Warning] Failed to write to log file: {e}")

    def authenticate(self):
        """GEE 인증 및 초기화"""
        if not self.project_id:
            raise ValueError("Project ID is missing in configuration.")

        try:
            ee.Initialize(project=self.project_id)
            print(f"[Info] GEE Initialized successfully (Project: {self.project_id})")
        except ee.EEException:
            print("[Info] Authentication required. Starting authentication flow...")
            try:
                ee.Authenticate()
                ee.Initialize(project=self.project_id)
                print("[Info] GEE Initialized after authentication.")
            except Exception as e:
                raise RuntimeError(f"Failed to authenticate and initialize: {e}")

    def _get_geometry(self, country_name, state_name):
        """FAO GAUL 데이터셋에서 Geometry 반환"""
        states = ee.FeatureCollection('FAO/GAUL/2015/level1') \
            .filter(ee.Filter.eq('ADM0_NAME', country_name)) \
            .filter(ee.Filter.eq('ADM1_NAME', state_name))
        return states.geometry()

    def _process_image_collection(self, roi, start_date, end_date, cloud_cover_max):
        """Sentinel-2 컬렉션 필터링 및 NDVI 계산, Mosaicking"""
        
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)

        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterDate(start_date, end_date)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover_max))
                      .filterBounds(roi)
                      .select(['B2', 'B3', 'B4', 'B8', 'B11']))
        
        # NDVI 추가 및 Greenest Pixel Mosaic (NDVI 최대값 기준 합성)
        collection_ndvi = collection.map(add_ndvi)
        max_ndvi = collection_ndvi.qualityMosaic('NDVI')
        
        return max_ndvi.select(['B2', 'B3', 'B4', 'B8', 'B11']).clip(roi)

    def _submit_export(self, image, roi, description, folder_name):
        """Google Drive Export 작업 제출 및 로깅"""
        params = self.config['export_params']
        
        try:
            task = ee.batch.Export.image.toDrive(
                image=image,
                description=description,
                folder=folder_name,
                scale=params['scale'],
                region=roi,
                maxPixels=params['max_pixels'],
            )
            task.start()
            
            # Task ID 로깅
            print(f" >> [Started] Task ID: {task.id} | Folder: {folder_name}")
            self._log_task_to_csv(task.id, description, folder_name, status="STARTED")
            
        except Exception as e:
            print(f" >> [Error] Export failed for {description}: {e}")
            self._log_task_to_csv("N/A", description, folder_name, status="FAILED", note=str(e))

    def run(self):
        """설정에 따른 전체 배치 작업 실행"""
        self.authenticate()

        years = self.config['years']
        locations = self.config['locations']
        periods = self.config['periods']
        params = self.config['export_params']

        total_tasks = 0

        for year in years:
            for loc in locations:
                country_name = loc['country_name']
                country_code = loc['country_code']
                states = loc['states']

                for state_name in states:
                    state_clean = state_name.replace(" ", "")
                    
                    # 1. Geometry 확보
                    try:
                        roi = self._get_geometry(country_name, state_name)
                    except Exception as e:
                        print(f"[Skip] Geometry Error ({state_name}, {country_name}): {e}")
                        continue

                    for suffix, date_fmt in periods.items():
                        start_date = date_fmt['start_fmt'].format(year=year)
                        end_date = date_fmt['end_fmt'].format(year=year)

                        # 폴더명: Year_Suffix_CountryCode_State
                        folder_name = f"{year}_{suffix}_{country_code}_{state_clean}"
                        # Task Description
                        description = folder_name

                        print(f"\n[Processing] {country_code}-{state_name} ({start_date} ~ {end_date})")

                        # 2. 이미지 처리
                        try:
                            processed_image = self._process_image_collection(
                                roi, start_date, end_date, params['cloud_cover_max']
                            )
                            
                            # 3. Export 제출
                            self._submit_export(processed_image, roi, description, folder_name)
                            total_tasks += 1
                            
                            time.sleep(1.5)

                        except Exception as e:
                            print(f" >> [Error] Processing failed: {e}")
                            self._log_task_to_csv("N/A", description, folder_name, status="ERROR", note=str(e))

        print(f"\n[Done] All jobs submitted. Total tasks: {total_tasks}")
        print(f"Check '{self.log_file}' for task details.")


def main():
    try:
        monitor = GEECropMonitor(config_path='config.json')
        monitor.run()
    except Exception as e:
        print(f"Program terminated with error: {e}")

if __name__ == '__main__':
    main()