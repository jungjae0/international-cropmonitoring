import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import ee, geemap
from datetime import datetime

ee.Initialize(project='ee-wodudqkqh123')

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def update_mask(image, mask):
    return image.updateMask(mask).selfMask().copyProperties(image)

def calculate_nirv(vi_collection):
    def _nirv(img):
        nir = img.select('NIR_reflectance')
        ndvi = img.select('NDVI')
        nirv = nir.multiply(ndvi).rename('NIRv')
        return img.addBands(nirv).copyProperties(img)
    return vi_collection.map(_nirv).select('NIRv')

def get_state_feature(state_name):
    if '_' in state_name:
        state_name = state_name.replace('_', ' ')

    return ee.FeatureCollection('FAO/GAUL/2015/level1').filter(ee.Filter.eq('ADM1_NAME', state_name))


def get_crop_mask(asset_prefix, crop, year, state):
    asset_id = f'{asset_prefix}/{year}_{crop}_{state}'
    if 'Wheat' in crop:
        asset_id = f'{asset_prefix}/{year}_Wheat_{state}'
    return ee.Image(asset_id)

def export_zonal_statistics(nirv, mask, feature, out_file, year=None):
    nirv_masked = nirv.map(lambda img: update_mask(img, mask)).filterBounds(feature).toBands()
    geemap.zonal_statistics(nirv_masked, feature, out_file, statistics_type='MEAN', scale=500)

def smooth_nirv(input_csv, output_csv, data_year=None):
    df_raw = pd.read_csv(input_csv)

    nirv_cols = [col for col in df_raw.columns if '_NIRv' in col]

    def parse_date(col):
        date_str = col.replace('_NIRv', '')
        return datetime.strptime(date_str, "%Y_%m_%d")

    col_date_pairs = [(col, parse_date(col)) for col in nirv_cols]
    col_date_pairs.sort(key=lambda x: x[1])
    sorted_cols = [col for col, _ in col_date_pairs]
    doys = [d.timetuple().tm_yday for _, d in col_date_pairs]

    df = df_raw[sorted_cols].copy()
    df.columns = doys
    df = df.T.sort_index()

    doy_full = np.arange(1, 366)
    df_interp = df.reindex(doy_full).interpolate('linear', axis=0)

    df_smooth = df_interp.apply(
        lambda x: savgol_filter(x, window_length=51, polyorder=4, mode='nearest'),
        axis=0
    )
    df_smooth = pd.DataFrame(df_smooth, index=doy_full)

    if data_year == datetime.now().year:
        today_doy = datetime.now().timetuple().tm_yday
        df_smooth = df_smooth.loc[:today_doy]

    df_smooth.to_csv(output_csv)
    return df_smooth.iloc[:, 0]





def main():
    # ========== 시작 ========== #
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(BASE_PATH, "datas", "USA", "GEE", "Monitoring", "NIRv")
    current_year = datetime.now().year



    viirs = ee.ImageCollection("NASA/VIIRS/002/VNP13A1").filterDate(f'{current_year}-01-01',f'{current_year}-12-31')
    nirv = calculate_nirv(viirs)

    corn_states = ["Arkansas", "Illinois", "Indiana", "Iowa", "Kansas", "Minnesota", "Missouri", "Nebraska",
                   "North_Dakota", "Ohio", "South_Dakota", "Wisconsin"]
    soybean_states = ["Arkansas", "Illinois", "Indiana", "Iowa", "Kansas", "Minnesota", "Missouri", "Nebraska",
                      "North_Dakota", "Ohio", "South_Dakota", "Wisconsin"]
    spring_wheat_states = ["Idaho", "Montana", "Oregon", "Washington"]

    winter_wheat_states = ["Colorado", "Idaho", "Kansas", "Montana", "Nebraska", "Oklahoma", "Oregon", "Texas",
                           "Washington"]

    crop_state_dict = {
        'Corn': corn_states,
        'Soybean': soybean_states,
#        'Wheat_Spring': spring_wheat_states,
#        'Wheat_Winter': winter_wheat_states
    }

    for crop, states in crop_state_dict.items():
        asset_prefix = f'users/wodudqkqh123/USA_{crop}'
        for state in states:
            orig_dir = os.path.join(base_dir, crop, "Original", state)
            smooth_dir = os.path.join(base_dir, crop, "Smoothed", state)
            ensure_dir(orig_dir)
            ensure_dir(smooth_dir)

            feature = get_state_feature(state)

            mask = get_crop_mask(asset_prefix, crop, current_year, state)
            csv_cur = os.path.join(orig_dir, f'{state}_{crop}_{current_year}.csv')
            export_zonal_statistics(
                nirv.filterDate(f'{current_year}-01-01', f'{current_year}-12-31'),
                mask,
                feature,
                csv_cur,
                year=current_year
            )
            smoothed_cur = smooth_nirv(csv_cur, os.path.join(smooth_dir, f'{state}_{crop}_{current_year}_smoothed.csv'),
                                       data_year=current_year)


    base_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_path, "cron_test_output.txt"), "a") as f:
        f.write(f"CRON TEST executed at {datetime.now()}\n{base_path}")


if __name__ == "__main__":
    main()
