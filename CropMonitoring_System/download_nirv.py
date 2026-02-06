import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from tqdm import tqdm

import ee
import geemap
from datetime import datetime


class NIRvProcessor:
    """
    VIIRS NIRv processing pipeline.

    기능:
    - 디렉터리 생성
    - VIIRS 컬렉션에서 NIRv 계산
    - 작물/주(state) 마스크
    - Zonal statistics CSV 추출
    - (옵션) NIRv 시계열 전처리 및 DOY-NIRv 형식 CSV 생성
      * preprocess=True  : 1~365 DOY 기준 보간(+옵션 스무딩)
      * preprocess=False : 원본 날짜 기준으로 DOY, NIRv만 추출
    """

    def __init__(
        self,
        base_dir: str,
        project_id: str = "ee-wodudqkqh123",
        preprocess: bool = True,
        smooth: bool = True,
        smooth_window: int = 51,
        smooth_polyorder: int = 4,
    ) -> None:
        """Args:
        Args:
            base_dir: 결과 파일을 저장할 기본 디렉터리.
            project_id: Earth Engine 프로젝트 ID.
            preprocess: True이면 DOY 기준 보간/스무딩 등 전처리 수행.
                        False이면 원본 관측일에 대해서만 DOY, NIRv 열 저장.
            smooth: True이면 Savitzky-Golay 필터로 스무딩 수행.
            smooth_window: Savitzky-Golay 윈도우 길이(홀수).
            smooth_polyorder: Savitzky-Golay 다항식 차수.
        """
        self.base_dir = base_dir
        self.project_id = project_id
        self.preprocess = preprocess
        self.smooth = smooth
        self.smooth_window = smooth_window
        self.smooth_polyorder = smooth_polyorder

        ee.Initialize(project=self.project_id)

    # ---------- Utility methods ---------- #
    @staticmethod
    def ensure_dir(path: str) -> None:
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def update_mask(image, mask):
        return image.updateMask(mask).selfMask().copyProperties(image)

    @staticmethod
    def get_state_feature(state_name: str):
        if "_" in state_name:
            state_name = state_name.replace("_", " ")
        return ee.FeatureCollection("FAO/GAUL/2015/level1").filter(
            ee.Filter.eq("ADM1_NAME", state_name)
        )

    @staticmethod
    def get_crop_mask(asset_prefix: str, crop: str, year: int, state: str):
        asset_id = f"{asset_prefix}/{year}_{crop}_{state}"
        if "Wheat" in crop:
            asset_id = f"{asset_prefix}/{year}_Wheat_{state}"
        return ee.Image(asset_id)

    @staticmethod
    def calculate_nirv(vi_collection):
        def _nirv(img):
            nir = img.select("NIR_reflectance")
            ndvi = img.select("NDVI")
            nirv = nir.multiply(ndvi).rename("NIRv")
            return img.addBands(nirv).copyProperties(img)

        return vi_collection.map(_nirv).select("NIRv")

    # ---------- Core processing ---------- #
    def export_zonal_statistics(
        self,
        nirv,
        mask,
        feature,
        out_file: str,
        scale: int = 500,
    ):
        nirv_masked = (
            nirv.map(lambda img: self.update_mask(img, mask))
            .filterBounds(feature)
            .toBands()
        )
        self.ensure_dir(os.path.dirname(out_file))
        geemap.zonal_statistics(
            nirv_masked,
            feature,
            out_file,
            statistics_type="MEAN",
            scale=scale,
        )

    def smooth_nirv(
        self,
        input_csv: str,
        output_csv: str,
        data_year: Optional[int] = None,
    ):
        """NIRv 시계열을 DOY-NIRv CSV로 변환.

        - preprocess=True  : 1~365 DOY 기준으로 선형 보간 후,
                             smooth=True이면 Savitzky-Golay 스무딩 적용.
        - preprocess=False : 원본 날짜에 대해서만 DOY, NIRv(평균) 추출.

        Args:
            input_csv: raw NIRv CSV 경로 (zonal statistics 결과).
            output_csv: 결과 CSV 저장 경로.
            data_year: 데이터 연도(현재 연도면 오늘 DOY까지만 자름 - preprocess=True일 때만).
        """
        df_raw = pd.read_csv(input_csv)

        # zonal_statistics 결과에서 날짜별 NIRv 컬럼 찾기
        nirv_cols = [col for col in df_raw.columns if "_NIRv" in col]

        if not nirv_cols:
            # NIRv 컬럼 없으면 그냥 리턴
            return None

        def parse_date(col: str) -> datetime:
            date_str = col.replace("_NIRv", "")
            return datetime.strptime(date_str, "%Y_%m_%d")

        col_date_pairs = [(col, parse_date(col)) for col in nirv_cols]
        col_date_pairs.sort(key=lambda x: x[1])
        sorted_cols = [col for col, _ in col_date_pairs]
        doys = [d.timetuple().tm_yday for _, d in col_date_pairs]

        # ---------- 전처리 OFF: 원본 관측일만 DOY/NIRv 추출 ---------- #
        if not self.preprocess:
            # 여러 feature가 있을 경우 날짜별 평균 사용
            nirv_values = df_raw[sorted_cols].mean(axis=0).values

            df_out = pd.DataFrame({
                "DOY": doys,
                "NIRv": nirv_values,
            })

            self.ensure_dir(os.path.dirname(output_csv))
            df_out.to_csv(output_csv, index=False)
            return df_out

        # ---------- 전처리 ON: 1~365 DOY 기준 보간 (+옵션 스무딩) ---------- #
        # 열 이름을 DOY로 바꿔서 index로 사용
        df = df_raw[sorted_cols].copy()
        df.columns = doys
        df = df.T.sort_index()

        # 1~365일 전체로 reindex 후 선형 보간
        doy_full = np.arange(1, 366)
        df_interp = df.reindex(doy_full).interpolate("linear", axis=0)

        # smoothing 옵션
        if self.smooth:
            df_smooth_values = df_interp.apply(
                lambda x: savgol_filter(
                    x,
                    window_length=self.smooth_window,
                    polyorder=self.smooth_polyorder,
                    mode="nearest",
                ),
                axis=0,
            )
            df_smooth = pd.DataFrame(df_smooth_values, index=doy_full)
        else:
            # smoothing 끈 상태면 보간 결과만 사용
            df_smooth = df_interp

        # 해당 연도가 현재 연도면 오늘 DOY까지만 자르기
        if data_year == datetime.now().year:
            today_doy = datetime.now().timetuple().tm_yday
            df_smooth = df_smooth.loc[: today_doy]

        # feature가 여러 개 있을 경우 DOY별 평균 NIRv 사용
        nirv_series = df_smooth.mean(axis=1)

        df_out = pd.DataFrame({
            "DOY": df_smooth.index.values,
            "NIRv": nirv_series.values,
        })

        self.ensure_dir(os.path.dirname(output_csv))
        df_out.to_csv(output_csv, index=False)
        return df_out

    # ---------- High-level runner ---------- #
    def run(
        self,
        year: Optional[int] = None,
        crops: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """전체 파이프라인 실행.

        Args:
            year: 타겟 연도 (None이면 현재 연도).
            crops: {"작물이름": ["State1", "State2", ...]} 형태의 dict.
                   None이면 기본 US Corn/Soy/Wheat dict 사용.
        """
        current_year = year or datetime.now().year

        # Earth Engine VIIRS 컬렉션 & NIRv 계산
        viirs = ee.ImageCollection("NASA/VIIRS/002/VNP13A1").filterDate(
            f"{current_year}-01-01", f"{current_year}-12-31"
        )
        nirv = self.calculate_nirv(viirs)

        # 기본 crop/state 설정
        if crops is None:
            corn_states = [
                "Arkansas",
                "Illinois",
                "Indiana",
                "Iowa",
                "Kansas",
                "Minnesota",
                "Missouri",
                "Nebraska",
                "North_Dakota",
                "Ohio",
                "South_Dakota",
                "Wisconsin",
            ]
            soybean_states = corn_states.copy()
            spring_wheat_states = ["Idaho", "Montana", "Oregon", "Washington"]
            winter_wheat_states = [
                "Colorado",
                "Idaho",
                "Kansas",
                "Montana",
                "Nebraska",
                "Oklahoma",
                "Oregon",
                "Texas",
                "Washington",
            ]

            crops = {
                "Corn": corn_states,
                "Soybean": soybean_states,
                "Wheat_Spring": spring_wheat_states,
                "Wheat_Winter": winter_wheat_states,
            }

        # 전체 state 개수 계산 (tqdm total 용)
        total_states = sum(len(states) for states in crops.values())

        with tqdm(total=total_states, desc="Processing states", unit="state") as pbar:
            for crop, states in crops.items():
                asset_prefix = f"users/wodudqkqh123/USA_{crop}"

                for state in states:
                    # 디렉터리 준비
                    orig_dir = os.path.join(self.base_dir, crop, "Original", state)
                    processed_dir = os.path.join(
                        self.base_dir, crop, "Smoothed", state
                    )  # 기존 폴더 이름 유지
                    self.ensure_dir(orig_dir)
                    self.ensure_dir(processed_dir)

                    # 행정구역 feature & crop mask
                    feature = self.get_state_feature(state)
                    mask = self.get_crop_mask(asset_prefix, crop, current_year, state)

                    # 원본 CSV 경로
                    csv_cur = os.path.join(
                        orig_dir,
                        f"{state}_{crop}_{current_year}.csv",
                    )

                    # Zonal statistics export
                    self.export_zonal_statistics(
                        nirv.filterDate(
                            f"{current_year}-01-01",
                            f"{current_year}-12-31",
                        ),
                        mask,
                        feature,
                        csv_cur,
                        scale=500,
                    )

                    # 전처리/스무딩 결과 파일명 결정
                    if not self.preprocess:
                        suffix = "smoothed"
                    else:
                        suffix = "smoothed" if self.smooth else "interp"

                    output_csv = os.path.join(
                        processed_dir,
                        f"{state}_{crop}_{current_year}_{suffix}.csv",
                    )

                    # NIRv -> DOY, NIRv 형식 CSV 생성
                    self.smooth_nirv(csv_cur, output_csv, data_year=current_year)

                    # tqdm 진행상황 업데이트
                    pbar.set_postfix_str(f"{crop} - {state}")
                    pbar.update(1)


# ---------- main: 여기에서 year, crops, 옵션 정의 ---------- #
# atas/USA/GEE/Monitoring/NIRv/Corn
def main():
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(BASE_PATH, "datas", "USA", "GEE", "Monitoring", "NIRv")

    # 1) 사용할 연도

    # 2) 원하는 crop/state 조합 정의
    corn_states = [
        "Arkansas",
        "Illinois",
        "Indiana",
        "Iowa",
        "Kansas",
        "Minnesota",
        "Missouri",
        "Nebraska",
        "North_Dakota",
        "Ohio",
        "South_Dakota",
        "Wisconsin",
    ]
    soybean_states = corn_states.copy()
    spring_wheat_states = ["Idaho", "Montana", "Oregon", "Washington"]
    winter_wheat_states = [
        "Colorado",
        "Idaho",
        "Kansas",
        "Montana",
        "Nebraska",
        "Oklahoma",
        "Oregon",
        "Texas",
        "Washington",
    ]

    crop_state_dict: Dict[str, List[str]] = {
        "Corn": corn_states,
        "Soybean": soybean_states,
        # "Wheat_Spring": spring_wheat_states,
        # "Wheat_Winter": winter_wheat_states,
    }

    # 3) Processor 설정 (여기서 전처리/스무딩 ON/OFF 선택)
    processor = NIRvProcessor(
        base_dir=base_dir,
        preprocess=False,   # ← False 로 두면 전처리 없이 원본 DOY, NIRv만 저장
        smooth=True,       # preprocess=True일 때만 의미 있음
        smooth_window=51,
        smooth_polyorder=4,
    )

    # 4) 실행

    year = 2025#2024#datetime.now().year  # 또는 2024, 2025 등 명시

    for year in range(2018, 2020):
        processor.run(
            year=year,
            crops=crop_state_dict,
        )


if __name__ == "__main__":
    main()
