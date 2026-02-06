import ee
import pandas as pd
import geopandas as gpd
from datetime import datetime
import random
import shapely
from shapely.wkt import loads  # WKT 형식의 문자열을 폴리곤으로 변환

ee.Initialize()
def get_weather(region, start_date, end_date):
    selected_bands = [
        'temperature_2m',
        'soil_temperature_level_1',
        'soil_temperature_level_2',
        'volumetric_soil_water_layer_1',
        'volumetric_soil_water_layer_2',
        'total_precipitation_sum',
        'leaf_area_index_high_vegetation',
        'leaf_area_index_low_vegetation',
        'surface_net_solar_radiation_sum',
        'surface_latent_heat_flux_sum',
    ]

    # Load ERA5-Land Daily Aggregates dataset and filter by date and region
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date, end_date) \
        .filterBounds(region)

    # Function to extract all band data for each image
    # def extract_all_band_data(image):
    #     date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
    #     band_values = image.reduceRegion(
    #         reducer=ee.Reducer.mean(),
    #         geometry=region,
    #         scale=1000
    #     )
    #     return ee.Feature(None, band_values.set('date', date))
    #
    # # Apply function to each image in collection and export as list
    # data = dataset.map(extract_all_band_data).getInfo()
    #
    # # Convert to pandas DataFrame
    # df = pd.DataFrame([{
    #     **feature['properties'],
    #     'date': datetime.strptime(feature['properties']['date'], '%Y-%m-%d')
    # } for feature in data['features']])

    def extract_selected_band_data(image):
        date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')

        # 선택한 밴드의 데이터만 추출
        band_values = image.select(selected_bands).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=1000
        )

        return ee.Feature(None, band_values.set('date', date))

    # Apply function to each image in collection and export as list
    data = dataset.map(extract_selected_band_data).getInfo()

    # Convert to pandas DataFrame
    df = pd.DataFrame([{
        **feature['properties'],
        'date': datetime.strptime(feature['properties']['date'], '%Y-%m-%d')
    } for feature in data['features']])

    return df

def random_point_in_polygon(polygon):
    """폴리곤 내에서 랜덤한 점을 생성합니다."""
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        random_point = shapely.geometry.Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(random_point):
            return random_point
# Initialize Earth Engine
def convert_k_to_c(k):
    return k - 273.15
def main():
    gdf = pd.read_csv('../static/crop_calendar.csv')
    gdf['geometry'] = gdf['geometry'].apply(loads)  # WKT 문자열을 Polygon 객체로 변환

    # gdf = gdf.head(300)

    gdf['points'] = gdf['geometry'].apply(
        lambda geom: ee.Geometry.Point(random_point_in_polygon(geom).x, random_point_in_polygon(geom).y)
    )
    gdf = gpd.GeoDataFrame(gdf, geometry='geometry')

    # Define date range
    start_date = '2015-01-01'
    end_date = '2024-10-30'

    import os
    already_lst = os.listdir("../weather")
    already_lst = ["_".join(f.replace(".csv", "").split("_")[:-1])
 for f in already_lst]
    # print(already_lst)
    # "_".join(parts[:-1])
    # all_dfs = []
    import tqdm

    for idx, row in tqdm.tqdm(gdf.iterrows(), total = len(gdf)):
        region = row['points']

        info = f'{row["crop"]}_{row["country"]}_{row["region"]}'
        if not info in already_lst:
            try:
                # 지역별 날씨 데이터를 가져옴
                df = get_weather(region, start_date, end_date)

                # 'index' 열을 추가하여 모든 행에 동일한 값 설정
                # df['index'] = idx

                # row의 모든 열을 추가
                for col_name, col_value in row.items():
                    if col_name != 'points' and col_name != 'geometry':
                        df[col_name] = col_value

                # 온도 데이터를 변환하는 로직 적용
                for column in df.columns:
                    if "temperature" in column:
                        df[column] = df[column].apply(convert_k_to_c)

                df['date'] = pd.to_datetime(df['date'])
                df['year'] = df['date'].dt.year
                years = df['year'].unique()

                for year in years:
                    filtered = df[df['year'] == year]
                    path = f"../weather/{row['crop']}_{row['country']}_{row['region']}_{year}.csv"
                    filtered.to_csv(path, index=False)



                # 연도별로 데이터를 나누어 저장
                # for year, group in df.groupby(df['date'].dt.year):
                #
                #     # 각각의 연도별 데이터프레임을 CSV 파일로 저장
                #     group.to_csv(f'../weather/{row["crop"].replace(" "), ""}_{row["country"]}_{row["region"]}_{year}.csv', index=False)
                # df.to_csv(f'../data/{row["crop"]}_{row["country"]}_{row["region"]}.csv', index=False)

            except:
                continue
    #
    # # # Concatenate all_dfs and merge with gdf
    # # combined_df = pd.concat(all_dfs).set_index('index')
    # # gdf = gdf.merge(combined_df, left_index=True, right_index=True, how='left')
    # #
    # # gdf.to_csv("../data/ERA5_data.csv", index=False)
    # # gdf.to_json("../data/ERA5_data.json", orient='records', lines=True)
    #

if __name__ == '__main__':
    main()
