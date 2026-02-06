import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import ee, geemap
from datetime import datetime

# ee.Authenticate()
# ee.Initialize(project='ee-wodudqkqh123')
#
# def ensure_dir(path):
#     if not os.path.exists(path):
#         os.makedirs(path)
#
# def update_mask(image, mask):
#     return image.updateMask(mask).selfMask().copyProperties(image)
#
# def calculate_nirv(vi_collection):
#     def _nirv(img):
#         nir = img.select('NIR_reflectance')
#         ndvi = img.select('NDVI')
#         nirv = nir.multiply(ndvi).rename('NIRv')
#         return img.addBands(nirv).copyProperties(img)
#     return vi_collection.map(_nirv).select('NIRv')
#
# def get_state_feature(state_name):
#     if '_' in state_name:
#         state_name = state_name.replace('_', ' ')
#
#     return ee.FeatureCollection('FAO/GAUL/2015/level1').filter(ee.Filter.eq('ADM1_NAME', state_name))
#
#
# def get_crop_mask(asset_prefix, crop, year, state):
#     crop_codes = {
#         'Corn': 1,
#         'Soybean': 5,
#         'Wheat_Winter': 24,
#         'Wheat_Spring': 22
#     }
#
#     def get_latest_available_year():
#         assets = ee.data.listAssets({'parent': asset_prefix}).get('assets', [])
#         years = []
#         for a in assets:
#             # asset 이름이 예: "users/.../2023_Corn_Texas" 형식이라면
#             parts = a['name'].split('/')[-1].split('_')
#             try:
#                 y = int(parts[0])
#                 years.append(y)
#             except ValueError:
#                 continue
#         return max(years) if years else 2023  # 기본 fallback
#
#     if year < 2018:
#         # CDL을 사용
#         cdl = ee.ImageCollection("USDA/NASS/CDL") \
#             .filter(ee.Filter.calendarRange(year, year, "year")) \
#             .first()
#         crop_code = crop_codes.get(crop)
#         if crop_code is None:
#             raise ValueError(f"Unknown crop type: {crop}")
#
#         feature = get_state_feature(state)
#         cdl = cdl.clip(feature).select('cropland')
#         mask = cdl.eq(crop_code).selfMask()
#         return mask
#
#     elif year > 2023:
#         y = get_latest_available_year()
#     else:
#         y = year
#
#
#     asset_id = f'{asset_prefix}/{y}_{crop}_{state}'
#     if 'Wheat' in crop:
#         asset_id = f'{asset_prefix}/{y}_Wheat_{state}'
#     return ee.Image(asset_id)
#
# # def get_crop_mask(asset_prefix, crop, year, state, fallback_year=None):
# #     if year < 2018:
# #         y = 2018  # 2018년 이전은 2018년 mask 사용
# #     elif year > 2023:
# #         y = fallback_year  # 2024년 이상은 fallback_year 사용
# #     else:
# #         y = year  # 2018~2023은 해당 연도 mask 사용
# #     asset_id = f'{asset_prefix}/{y}_{crop}_{state}'
# #     return ee.Image(asset_id)
#
# def export_zonal_statistics(nirv, mask, feature, out_file, year=None):
#     current_year = datetime.now().year
#
#     if (not os.path.exists(out_file)) or (year == current_year):
#         nirv_masked = nirv.map(lambda img: update_mask(img, mask)).filterBounds(feature).toBands()
#         geemap.zonal_statistics(nirv_masked, feature, out_file, statistics_type='MEAN', scale=500)
#     else:
#         print(f"[{year}] '{out_file}' already exists. Skipping...")
#
# def smooth_nirv(input_csv, output_csv, data_year=None):
#     df_raw = pd.read_csv(input_csv)
#
#     # '_NIRv'로 끝나는 컬럼만 선택
#     nirv_cols = [col for col in df_raw.columns if '_NIRv' in col]
#
#     def parse_date(col):
#         date_str = col.replace('_NIRv', '')
#         return datetime.strptime(date_str, "%Y_%m_%d")
#
#     # 날짜 기준으로 정렬
#     col_date_pairs = [(col, parse_date(col)) for col in nirv_cols]
#     col_date_pairs.sort(key=lambda x: x[1])
#     sorted_cols = [col for col, _ in col_date_pairs]
#     doys = [d.timetuple().tm_yday for _, d in col_date_pairs]
#
#     # 데이터프레임 정리
#     df = df_raw[sorted_cols].copy()
#     df.columns = doys
#     df = df.T.sort_index()
#
#     # 1년 전체 Day-of-Year 기준으로 보간
#     doy_full = np.arange(1, 366)  # 1~365
#     df_interp = df.reindex(doy_full).interpolate('linear', axis=0)
#
#     # Savitzky-Golay 필터 적용
#     df_smooth = df_interp.apply(
#         lambda x: savgol_filter(x, window_length=51, polyorder=4, mode='nearest'),
#         axis=0
#     )
#     df_smooth = pd.DataFrame(df_smooth, index=doy_full)
#
#     # ▶ 현재 연도일 경우 오늘 이후는 제외
#     if data_year == datetime.now().year:
#         today_doy = datetime.now().timetuple().tm_yday
#         df_smooth = df_smooth.loc[:today_doy]
#
#     # CSV 저장 및 첫 열 반환
#     df_smooth.to_csv(output_csv)
#     return df_smooth.iloc[:, 0]  # 첫 번째 열을 시각화용으로 반환
#
#
# def plot_multi_years(state, crop, years_data, out_dir):
#     plt.figure()
#     labels = {
#         "mean": "5-yr Avg",
#         "last": f"{years_data['last_year']}",
#         "current": f"{years_data['target_year']} (YTD)"
#     }
#
#     df_all = pd.DataFrame(years_data['collection'])#.multiply(1e-8)
#     mean = df_all.mean(axis=1)
#     std = df_all.std(axis=1)
#
#     if mean.dropna().empty:
#         print(f"평균값이 NaN — 5-yr Avg 라인을 그릴 수 없음")
#     else:
#         plt.plot(mean, label=labels['mean'], color='black')
#         plt.fill_between(df_all.index, mean - 1.96 * std, mean + 1.96 * std,
#                          color='olive', alpha=0.15)
#
#     plt.plot(years_data['last'], label=labels['last'], color='orange')
#
#     plt.plot(years_data['current'], label=labels['current'], color='red')
#
#     plt.title(f'{state} {crop} NIRv Comparison')
#     plt.xlabel('DOY')
#     plt.ylabel('NIRv')
#     plt.xlim(0, 364)
#     plt.ylim(0, 1)
#     plt.grid(True)
#     plt.legend()
#
#     chart_dir = os.path.join(out_dir, "Chart", "Annual Comparison")
#     ensure_dir(chart_dir)
#     plt.savefig(os.path.join(chart_dir, f'{state}_{crop}_{years_data["target_year"]}_comparison.png'))
#     plt.close()

def download():
    print("test")
    # # ========== 설정 ========== #
    # target_year = 2025
    # crops = ['Corn', 'Soybean']
    #
    # state_dir = rf"Y:\DATA\CropMonitoring\USA\GEE\Cropmap\Corn\2024"
    # states = [file.replace(f"2024_Corn_", "").replace(".tif", "") for file in os.listdir(state_dir) if file.endswith(".tif")]
    #
    # base_dir = r'Y:\DATA\CropMonitoring\USA\GEE\Monitoring\NIRv'
    #
    # average_years = list(range(target_year - 5, target_year))
    # last_year = target_year - 1
    # current_year = target_year
    #
    # # ========== 시작 ========== #
    # viirs = ee.ImageCollection("NASA/VIIRS/002/VNP13A1").filterDate(f'{average_years[0]}-01-01', f'{current_year}-12-31')
    # nirv = calculate_nirv(viirs)
    #
    # for crop in crops:
    #     asset_prefix = f'users/wodudqkqh123/USA_{crop}'
    #
    #     print(f"=== {crop} ===")
    #     for state in states:
    #         try:
    #             print(f"-- {state} --")
    #             feature = get_state_feature(state)
    #             collection = []
    #             years_data = {
    #                 'target_year': current_year,
    #                 'last_year': last_year
    #             }
    #
    #             orig_dir = os.path.join(base_dir, crop, "Original", state)
    #             smooth_dir = os.path.join(base_dir, crop, "Smoothed", state)
    #             ensure_dir(orig_dir)
    #             ensure_dir(smooth_dir)
    #
    #             # ========== 과거 5년 평균 ========== #
    #             for y in average_years:
    #                 mask = get_crop_mask(asset_prefix, crop, y, state)
    #                 out_csv = os.path.join(orig_dir, f'{state}_{crop}_{y}.csv')
    #                 export_zonal_statistics(nirv.filterDate(f'{y}-01-01', f'{y}-12-31'), mask, feature, out_csv)
    #                 sm_csv = os.path.join(smooth_dir, f'{state}_{crop}_{y}_smoothed.csv')
    #                 smoothed = smooth_nirv(out_csv, sm_csv, data_year=y)
    #                 collection.append(smoothed)
    #
    #             years_data['collection'] = np.array(collection).T
    #
    #             # ========== 전년도 ========== #
    #             mask = get_crop_mask(asset_prefix, crop, last_year, state)
    #             csv_last = os.path.join(orig_dir, f'{state}_{crop}_{last_year}.csv')
    #             export_zonal_statistics(
    #                 nirv.filterDate(f'{last_year}-01-01', f'{last_year}-12-31'),
    #                 mask,
    #                 feature,
    #                 csv_last,
    #                 year=last_year
    #             )
    #             smoothed_last = smooth_nirv(csv_last, os.path.join(smooth_dir, f'{state}_{crop}_{last_year}_smoothed.csv'), data_year=last_year)
    #             years_data['last'] = smoothed_last
    #
    #             # ========== 당해년도 ========== #
    #             mask = get_crop_mask(asset_prefix, crop, current_year, state)
    #             csv_cur = os.path.join(orig_dir, f'{state}_{crop}_{current_year}.csv')
    #             export_zonal_statistics(
    #                 nirv.filterDate(f'{current_year}-01-01', f'{current_year}-12-31'),
    #                 mask,
    #                 feature,
    #                 csv_cur,
    #                 year=current_year
    #             )
    #             smoothed_cur = smooth_nirv(csv_cur, os.path.join(smooth_dir, f'{state}_{crop}_{current_year}_smoothed.csv'), data_year=current_year)
    #
    #             # 오늘 날짜 기준 DOY 계산
    #             today_doy = datetime.now().timetuple().tm_yday
    #
    #             # 오늘 날짜까지만 슬라이싱
    #             smoothed_cur = smoothed_cur.loc[:today_doy]
    #
    #             years_data['current'] = smoothed_cur
    #             years_data['current'] = smoothed_cur
    #
    #             # ========== Plot ========== #
    #             # plot_multi_years(state, crop, years_data, base_dir)
    #         except Exception as e:
    #             print(f"오류 - {state} {crop}: {e}")
    #             continue
if __name__ == '__main__':
    download()
