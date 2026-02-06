# data_collector.py

import warnings
from datetime import datetime

import warnings
warnings.filterwarnings("ignore")
import rioxarray
import geopandas as gpd
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import os
import requests
from datetime import datetime, timedelta
import time
import random
# from .models import LogEntry

# 희원 Key
CLIENT_ID = "sh-f6247fd9-06ed-4767-b812-297639448909"
CLIENT_SECRET = "Fm6bjpYWuW7KTjNW8X2zW4FeC5RleubN"
# CLIENT_ID = 'sh-001540ed-6fed-47c1-adc0-a08de0d8ca4b'
# CLIENT_SECRET = 'N5iTP39uZ1XHcKGP7VFqgd6HKPycABv5'
client = BackendApplicationClient(client_id=CLIENT_ID)
oauth = OAuth2Session(client=client)



# API_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

def read_file_to_evalscript(file_path):
    # tiff 파일을 다운로드 받기 위한 evalscript 파일을 읽어오는 함수
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return f"""{content}"""

def polygon_to_bbox(value):
    return list(value.bounds)

def get_bbox_datas():
    tiger_shp_path = r"D:\Projects\2407_2712_crop_monitoring\01_us_wheat\99_US_County_Boundary\TIGER_US_2018"
    tiger_shp = gpd.read_file(tiger_shp_path)  # 총 3233개의 레코드

    state = "North Dakota"

    dakota = tiger_shp[tiger_shp['STATE'] == state]
    dakota['geometry'] = dakota['geometry'].apply(polygon_to_bbox)
    dakota = dakota.reset_index(drop=True)

    return dakota


def check_exists_new_image(start_date, end_date, bbox_value):
    # start_date와 end_date는 "YYYY-MM-DD" 형식의 문자열
    # bbox_value는 [minx, miny, maxx, maxy] 형식의 리스트

    search_url = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"

    search_data = {
        "bbox": bbox_value,
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "collections": ["sentinel-2-l2a"],
        "limit": 100,
        "filter": "eo:cloud_cover < 80",
        "distinct": "date"
    }

    try:
        response = oauth.post(search_url, json=search_data)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 처리

        features = response.json().get("features", [])

        if not features:
            return None  # 요청 성공했지만 데이터가 없음

        datetime_list = list(set(features))
        sorted_dates = sorted(datetime_list, key=lambda x: datetime.strptime(x, "%Y-%m-%d"))
        return sorted_dates

    except requests.exceptions.RequestException as e:
        return f"API 요청 오류: {str(e)}"

def request_image(bbox, datetime_value):
    evalscript = read_file_to_evalscript("evalscript.txt")

    download_url = "https://sh.dataspace.copernicus.eu/api/v1/process"
    """Sentinel Hub API 요청 생성 및 실행"""
    request = {
        "input": {
            "bounds": {
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
                "bbox": bbox,
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{datetime_value}T00:00:00Z",
                            "to": f"{datetime_value}T23:59:59Z",
                        },
                        # "mosaickingOrder": "leastRecent",
                    },
                    "processing": {"harmonizeValues": "false"},
                    "maxCloudCoverage": 20

    }
            ],
        },
        "output": {
            "width": 836,
            "height": 836,
            # "resx": 20,  # 해상도를 20m로 설정
            # "resy": 20,  # 해상도를 20m로 설정
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/tiff"}
                    # "type": 'application/x-zarr'
                }
            ]
        },
        "evalscript": evalscript}

    response = oauth.post(download_url, json=request)

    if response.status_code == 200:
        return response.content  # 성공 시 TIFF 데이터 반환
    else:
        print(f"API 요청 실패: {response.status_code}")
        print(response.text)
        return None


def login():
    token = oauth.fetch_token(
        token_url='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
        client_secret=CLIENT_SECRET, include_client_id=True)

    return token


def check_tiff_file(output_path):
    try:
        dataset = rioxarray.open_rasterio(output_path)
        return "SUCCESS"
    except Exception as e:
        return "FAIL"

def check_tiff_file_size(output_path):
    file_size_bytes = os.path.getsize(output_path)
    file_size_kb = file_size_bytes / (1024)  # Convert Bytes to KB
    file_size_mb = file_size_bytes / (1024 * 1024)  # Convert Bytes to MB
    file_size_gb = file_size_bytes / (1024 * 1024 * 1024)  # Convert Bytes to GB

    if file_size_mb < 1:
        file_size = f"{file_size_bytes:.2f} Bytes"
    elif file_size_mb < 1024:
        file_size = f"{file_size_kb:.2f} KB"
    else:
        file_size = f"{file_size_gb:.2f} GB"

    return file_size


def each_time_value(datetime_value):
    julian_day = datetime.strptime(datetime_value, '%Y-%m-%d').strftime('%j')
    month = datetime.strptime(datetime_value, '%Y-%m-%d').strftime('%m')
    year = datetime.strptime(datetime_value, '%Y-%m-%d').strftime('%Y')


    return year, month, julian_day


def download_image(base_output_folder, max_retries=3):
    """
    Sentinel 데이터를 다운로드하고 검증 실패 시 재시도하는 함수.

    5일에 한 번씩 데이터를 수집하고 저장한다고 가정

    Args:
        output_folder (str): TIFF 파일을 저장할 폴더 경로.
        max_retries (int): 작업 실패 시 재시도 횟수.
    """

    try:
        bbox_datas = get_bbox_datas()
        # start_date = "2025-01-30"
        # end_date = "2025-01-31"

        # 현재 날짜를 원하는 형식으로 출력
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        for idx, bbox_data in bbox_datas.iterrows():
            login()
            # print(bbox_data['geometry'])
            bbox_value = bbox_data['geometry']

            if idx <= 0:
                # 1. 해당 날짜에 수집된 데이터가 있는지 확인
                datetime_list = check_exists_new_image(start_date, end_date, bbox_value)

                if isinstance(datetime_list, list):  # 수집한 일자의 list 값을 가져옴
                    for datetime_value in datetime_list:
                        retry_count = 0  # 재시도 횟수 초기화

                        year, month, julian_day = each_time_value(datetime_value)
                        output_folder = f"{base_output_folder}/{year}/{int(month):02d}"
                        if not os.path.exists(output_folder):
                            os.makedirs(output_folder)

                        output_path = os.path.join(output_folder, f"{int(julian_day):03d}.tif")

                        # Check if the file already exists in the DB
                        # if LogEntry.objects.filter(file_path=output_path).exists():
                        #     print(f"File {output_path} already exists in the DB, skipping...")
                        #     continue  # Skip if file already exists in the DB

                        while retry_count < max_retries:

                            if not os.path.exists(output_path):

                                tiff_data = request_image(bbox_value, datetime_value)
                                if tiff_data:
                                    with open(output_path, "wb") as file:
                                        file.write(tiff_data)
                                else:
                                    break

                            save_result = check_tiff_file(output_path)

                            # 4-1. 파일이 잘 열리면 파일 크기와 상태 등을 log에 저장
                            if save_result == "SUCCESS":
                                file_size = check_tiff_file_size(output_path)
                                # LogEntry.objects.create(status=save_result, file_size=file_size, file_path=output_path)
                                # print(f"Successfully downloaded and verified: {output_path}")

                                # LogEntry.objects.create(status="Success", year=year, month=month, julian_day=julian_day,
                                #                         file_path=output_path, file_size=file_size,
                                #                         message="Successfully downloaded and verified")
                                break

                            # 4-2. 데이터가 잘 열리지 않으면 파일을 지우고 다시 시도
                            else:
                                retry_count += 1
                                # print(f"Verification failed for {output_path}. Retrying ({retry_count}/{max_retries})...")

                                # 실패 시 파일 제거
                                try:
                                    os.remove(output_path)
                                except FileNotFoundError:
                                    pass

                            time.sleep(1)
                        if retry_count >= max_retries:  # 재시도 초과 시 오류 처리
                            # LogEntry.objects.create(status="Fail", year=year, month=month, julian_day=julian_day,
                            #                         file_path=output_path, file_size=None,
                            #                         message="Verification failed")
                            pass

                elif isinstance(datetime_list, str):  # API 호출 오류 발생
                    # LogEntry.objects.create(status="Search API Error", year=None, month=None, julian_day=None,
                    #                         file_path=None, file_size=None, message=datetime_list)
                    pass
                elif datetime_list is None:  # 수집된 데이터가 없는 경우
                    # LogEntry.objects.create(status="None Data", year=None, month=None, julian_day=None, file_path=None,
                    #                         file_size=None, message="수집된 위성 이미지가 없습니다.")

                    pass
                else:  # 예상하지 못한 오류가 발생
                    # LogEntry.objects.create(status="Unexpected error", year=None, month=None, julian_day=None,
                    #                         file_path=None, file_size=None, message=datetime_list)
                    pass
    except Exception as e:
        # LogEntry.objects.create(status="Error", year=None, month=None, julian_day=None, file_path=None, file_size=None,
        #                         message=str(e))
        pass

# Log: 저장에 소요된 시간, 파일 크기, 성공 여부, 저장 일자

def collect_data():
    base_output_folder = r"Z:\DATA\00_국외작황모니터링 자료\satellite\sentinel2\north_dakota"

    download_image(base_output_folder, max_retries=3)

# collect_data()

    # """
    # 데이터 수집을 자동으로 실행하는 함수.
    # """
    # try:
    #     # 예: 데이터 수집 작업 수행
    #     time.sleep(2)  # 작업 시뮬레이션
    #     if random.random() < 0.2:  # 오류를 20% 확률로 발생시키는 시뮬레이션
    #         raise Exception("Random error occurred during data collection!")
    #
    #     # 수집 성공 로그 저장
    #     LogEntry.objects.create(status="SUCCESS", message="Data collection completed successfully.")
    #     return True
    #
    # except Exception as e:
    #     # 오류 로그 저장
    #     LogEntry.objects.create(status="ERROR", message=str(e))
    #     return False

