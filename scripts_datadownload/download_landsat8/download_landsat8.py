import os
import json
import time
import datetime
import requests
import threading
import logging
import re
import csv
from tqdm import tqdm


# ============================================================================
# 1. USGS M2M API 클라이언트 클래스
#    - USGS Machine-to-Machine API와 통신을 담당합니다.
#    - 로그인, 로그아웃, 데이터 검색, 다운로드 URL 요청 등의 기능을 수행합니다.
# ============================================================================
class USGSClient:
    """USGS M2M API 통신 클라이언트"""

    # USGS API의 기본 엔드포인트 URL (Stable 버전 사용)
    BASE_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/"

    def __init__(self, username, token):
        self.username = username
        self.token = token
        self.api_key = None  # 로그인 후 발급받는 API 키를 저장

    def _send_request(self, endpoint, data, use_auth=True):
        """
        API 요청을 전송하고 응답을 처리하는 내부 메서드
        - endpoint: API의 끝점 (예: 'login-token')
        - data: 전송할 데이터 (JSON)
        - use_auth: API 키 포함 여부 (로그인 등 일부 요청은 제외)
        """
        url = self.BASE_URL + endpoint
        headers = {'X-Auth-Token': self.api_key} if use_auth and self.api_key else None

        try:
            response = requests.post(url, json.dumps(data), headers=headers)
            response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
            result = response.json()

            # API 내부 에러 코드 확인
            if result.get('errorCode'):
                logging.error(f"API Error [{endpoint}]: {result['errorMessage']}")
                return None
            return result.get('data')
        except Exception as e:
            logging.error(f"Request Exception [{endpoint}]: {e}")
            return None

    def login(self):
        """사용자 인증 및 API 키 발급"""
        data = {'username': self.username, 'token': self.token}
        result = self._send_request("login-token", data, use_auth=False)
        if result:
            self.api_key = result
            logging.info("Login successful")
            return True
        return False

    def logout(self):
        """세션 종료 및 API 키 폐기"""
        if self.api_key:
            self._send_request("logout", None)
            logging.info("Logout completed")
            self.api_key = None

    def search_scenes(self, dataset_name, bbox, start_date, end_date, max_results=1000):
        """
        특정 기간 및 범위에 대한 씬(Scene) 메타데이터 검색
        - bbox: {'min_x', 'min_y', 'max_x', 'max_y'} 형태의 딕셔너리
        """
        # M2M API 형식에 맞는 Spatial Filter 구성 (MBR: Minimum Bounding Rectangle)
        spatial_filter = {
            'filterType': "mbr",
            'lowerLeft': {'latitude': bbox['min_y'], 'longitude': bbox['min_x']},
            'upperRight': {'latitude': bbox['max_y'], 'longitude': bbox['max_x']}
        }

        payload = {
            'datasetName': dataset_name,
            'maxResults': max_results,
            'sceneFilter': {
                'spatialFilter': spatial_filter,
                'acquisitionFilter': {'start': start_date, 'end': end_date},
            }
        }
        return self._send_request("scene-search", payload)

    def get_download_options(self, dataset_name, entity_ids):
        """검색된 씬들에 대해 다운로드 가능한 옵션(Product ID 등) 조회"""
        payload = {'datasetName': dataset_name, 'entityIds': entity_ids}
        return self._send_request("download-options", payload)

    def request_download_urls(self, downloads):
        """선택한 파일들에 대한 실제 다운로드 URL 발급 요청"""
        # 라벨은 요청을 식별하기 위한 용도 (현재 시간 사용)
        label = datetime.datetime.now().strftime("L8_%Y%m%d_%H%M%S")
        payload = {'downloads': downloads, 'label': label}
        return self._send_request("download-request", payload)


# ============================================================================
# 2. Landsat 프로세서 클래스
#    - 파일 시스템 관리, 중복 확인, 병렬 다운로드 실행 등을 담당합니다.
#    - CSV 로그 기록 기능도 포함되어 있습니다.
# ============================================================================
class LandsatProcessor:
    """데이터 처리 및 다운로드 관리자"""

    def __init__(self, root_dir, max_threads=5, save_csv_log=True, logs_dir=None):
        self.root_dir = root_dir

        # [안전장치] 병렬 실행 개수가 너무 많으면 서버 차단 위험이 있어 5개로 제한
        if max_threads > 5:
            max_threads = 5

        self.sema = threading.Semaphore(max_threads)  # 스레드 수 제어용 세마포어
        self.threads = []

        # CSV 로깅 설정 초기화
        self.save_csv_log = save_csv_log
        self.csv_lock = threading.Lock()  # 여러 스레드가 동시에 쓸 때 충돌 방지

        # 실행 시점 기준 로그 파일 경로 설정
        now = datetime.datetime.now()
        self.exec_year = now.strftime("%Y")
        self.exec_date = now.strftime("%Y-%m-%d")

        if self.save_csv_log:
            # logs_dir 설정 확인: 사용자 지정 경로가 있으면 우선 사용, 없으면 기본 경로(root/year/log) 사용
            if logs_dir:
                self.log_dir = logs_dir
            else:
                self.log_dir = os.path.join(self.root_dir, self.exec_year, "log")

            os.makedirs(self.log_dir, exist_ok=True)
            self.csv_path = os.path.join(self.log_dir, f"{self.exec_date}.csv")

            # 파일이 없으면 헤더(컬럼명)를 먼저 작성
            if not os.path.exists(self.csv_path):
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["filename", "tile", "status"])

        # 콘솔 출력 로거 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()]
        )

    def write_csv_log(self, filename, tile, status):
        """CSV 파일에 로그 한 줄을 추가하는 메서드 (Thread-Safe)"""
        if not self.save_csv_log:
            return
        with self.csv_lock:
            try:
                with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([filename, tile, status])
            except Exception as e:
                logging.error(f"Failed to write CSV log: {e}")

    def get_info(self, metadata):
        """
        메타데이터에서 저장 경로(연도/타일) 및 Display ID 추출
        - Display ID는 파일명으로 사용됩니다.
        """
        display_id = metadata.get('displayId', 'Unknown')
        year = None

        # 1. 촬영 날짜(acquisitionDate)에서 연도 추출 시도
        acq_date = metadata.get('acquisitionDate')
        if acq_date:
            year = acq_date.split('-')[0]

        # 2. 실패 시 시작 시간(startTime)에서 추출 시도
        if not year:
            start_time = metadata.get('startTime')
            if start_time:
                year = start_time.split('-')[0]

        # 3. 실패 시 ID 문자열(LC08_..._YYYYMMDD...)에서 추출 시도
        if not year and display_id != 'Unknown':
            parts = display_id.split('_')
            if len(parts) > 3 and len(parts[3]) == 8 and parts[3].isdigit():
                year = parts[3][:4]

        if not year:
            year = 'UnknownYear'

        # 타일 정보 (Path/Row) 추출 (보통 ID의 3번째 부분)
        parts = display_id.split('_')
        tile = parts[2] if len(parts) > 2 else 'UnknownTile'

        # 저장 폴더 생성: <루트>/<연도>/<타일>
        save_dir = os.path.join(self.root_dir, year, tile)
        os.makedirs(save_dir, exist_ok=True)

        return save_dir, tile, display_id

    def check_file_exists(self, directory, filename_prefix):
        """
        해당 폴더에 특정 파일명(prefix)으로 시작하는 .tar 파일이 이미 존재하는지 확인
        - 내용이 비어있지 않은지(size > 0)도 체크
        """
        if not os.path.exists(directory):
            return False
        for f in os.listdir(directory):
            if f.startswith(filename_prefix) and f.endswith('.tar') and os.path.getsize(os.path.join(directory, f)) > 0:
                return True
        return False

    def download_file(self, url, save_dir, tile, display_id):
        """
        개별 파일 다운로드 로직 (안전한 저장 방식 적용)
        - .part 파일로 먼저 받고, 완료 시 .tar로 변경하여 파일 손상 방지
        - URL의 난수 파일명 대신 display_id를 사용하여 명확한 파일명 지정
        """
        with self.sema:  # 세마포어를 통해 동시 실행 스레드 수 제한
            # 파일명 강제 지정 (예: LC08_..._T1.tar)
            local_filename = f"{display_id}.tar"

            final_path = os.path.join(save_dir, local_filename)
            temp_path = final_path + ".part"  # 임시 파일 경로

            try:
                # 1. 중복 다운로드 방지 (이미 있으면 성공 처리하고 종료)
                if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                    self.write_csv_log(local_filename, tile, "Success")
                    return

                # 2. 다운로드 스트림 연결
                with requests.get(url, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    # 3. 임시 파일(.part)에 데이터 쓰기
                    with open(temp_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

                # 4. 기존 파일이 있다면 삭제 (혹시 모를 충돌 방지)
                if os.path.exists(final_path):
                    try:
                        os.remove(final_path)
                    except:
                        pass

                # 5. 임시 파일을 최종 파일명으로 변경 (Atomic Operation에 가까움)
                os.replace(temp_path, final_path)

                logging.info(f"[Done] Download complete: {local_filename}")
                self.write_csv_log(local_filename, tile, "Success")

            except Exception as e:
                logging.error(f"[Error] Download failed ({local_filename}): {e}")
                self.write_csv_log(local_filename, tile, "Failed")

                # 실패 시 쓰다 만 임시 파일 삭제 (공간 낭비 방지)
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass

    def run_downloads_parallel(self, download_list):
        """다운로드 작업 목록을 받아 스레드 병렬 처리 수행"""
        for item in download_list:
            t = threading.Thread(
                target=self.download_file,
                args=(item['url'], item['save_dir'], item['tile'], item['display_id'])
            )
            self.threads.append(t)
            t.start()

        # 모든 스레드가 끝날 때까지 대기 (Main Thread Blocking)
        for t in self.threads:
            t.join()
        self.threads = []


# ============================================================================
# 3. 메인 로직
#    - 설정 로드 -> 초기화 -> 기간 설정 -> 검색 -> 필터링 -> 다운로드 요청 -> 실행
# ============================================================================
def load_config(config_path='config.json'):
    """설정 파일(config.json)을 읽어 딕셔너리로 반환"""
    if not os.path.exists(config_path):
        logging.error(f"Config file not found: {config_path}")
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading config file: {e}")
        return None


def main():
    # 1. 설정 파일 로드
    config_data = load_config()
    if not config_data:
        return

    # 설정값 파싱
    auth = config_data.get('auth', {})
    settings = config_data.get('settings', {})
    regions = config_data.get('regions', {})

    username = auth.get('username')
    token = auth.get('token')

    if not username or not token:
        logging.error("'auth' info (username/token) missing in config.json.")
        return

    # 2. 클라이언트 및 프로세서 객체 생성
    client = USGSClient(username, token)
    processor = LandsatProcessor(
        root_dir=settings.get('root_dir', './LandsatData'),
        max_threads=settings.get('max_threads', 4),
        save_csv_log=settings.get('save_csv_log', True),
        logs_dir=settings.get('logs_dir')  # logs_dir 설정 추가
    )

    # 3. 날짜 설정 (Lookback Days 적용)
    # 오늘 날짜를 기준으로 과거 며칠(lookback_days) 전부터 검색
    today = datetime.datetime.now(datetime.timezone.utc)
    lookback = settings.get('lookback_days', 3)
    start_dt = today - datetime.timedelta(days=lookback)

    s_date = start_dt.strftime("%Y-%m-%d") # 오늘 날짜 기준으로 룩백 날짜 계산
    e_date = today.strftime("%Y-%m-%d")    # 오늘 날짜

    logging.info(f"Processing Period: {s_date} ~ {e_date}")

    # 4. API 로그인
    if not client.login():
        return

    try:
        dataset_name = settings.get('dataset_name', 'landsat_ot_c2_l2')

        # 5. 국가별 순차 처리
        for country, bbox in regions.items():
            logging.info(f">>> Processing Country: {country}")

            # (1) 씬 검색 (Scene Search)
            search_res = client.search_scenes(dataset_name, bbox, s_date, e_date)
            if not search_res or not search_res.get('results'):
                logging.info(f"  - No data found for: {country}")
                continue

            scenes = search_res['results']
            logging.info(f"  - Total scenes found: {len(scenes)}")

            download_candidates = []
            entity_id_map = {}

            # (2) 필터링 및 중복 확인 (Early Filtering)
            filtered_count = 0
            skipped_count = 0

            for scene in scenes:
                display_id = scene.get('displayId', '')

                # 필터: Landsat 8 (LC08) 및 Tier 1 (T1) 데이터만 대상
                if not display_id.startswith("LC08"): continue
                is_t1 = "_T1" in display_id or scene.get('collectionCategory') == 'T1'
                if not is_t1: continue

                filtered_count += 1

                # 저장 경로 및 정보 확인
                save_dir, tile, display_id = processor.get_info(scene)

                # [최적화] 로컬에 이미 파일이 있으면 URL 요청 단계 생략 (Fast Skip)
                if processor.check_file_exists(save_dir, display_id):
                    processor.write_csv_log(f"{display_id}.tar", tile, "Success")
                    skipped_count += 1
                    continue

                # 다운로드 대상 목록에 추가
                download_candidates.append(scene['entityId'])
                entity_id_map[scene['entityId']] = {
                    'save_dir': save_dir,
                    'tile': tile,
                    'display_id': display_id
                }

            logging.info(f"  - Scenes after filter: {filtered_count}")
            logging.info(f"  - Skipped (Already exists): {skipped_count}")
            logging.info(f"  - New downloads required: {len(download_candidates)}")

            if not download_candidates:
                continue

            # (3) 다운로드 옵션 조회 (실제 다운로드 가능한지 확인)
            options = client.get_download_options(dataset_name, download_candidates)

            final_downloads = []
            for opt in options:
                # available 상태이고, 우리가 요청한 Entity ID가 맞는지 확인
                if opt['available'] and opt['entityId'] in entity_id_map:
                    final_downloads.append({'entityId': opt['entityId'], 'productId': opt['id']})

            if not final_downloads:
                logging.info("  - No valid download URLs returned.")
                continue

            # (4) 실제 다운로드 URL 발급 요청
            url_response = client.request_download_urls(final_downloads)
            if not url_response:
                continue

            # (5) 다운로드 작업 목록 구성
            tasks = []
            for item in url_response.get('availableDownloads', []):
                eid = item['entityId']
                if eid in entity_id_map:
                    info = entity_id_map[eid]
                    tasks.append({
                        'url': item['url'],
                        'save_dir': info['save_dir'],
                        'tile': info['tile'],
                        'display_id': info['display_id']
                    })

            # (6) 병렬 다운로드 시작
            processor.run_downloads_parallel(tasks)

    except Exception as e:
        logging.error(f"Main Process Error: {e}")
    finally:
        # 작업 종료 후 로그아웃
        client.logout()
        logging.info("All tasks completed.")


if __name__ == '__main__':
    main()