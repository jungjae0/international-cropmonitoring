import ee
import pandas as pd
import datetime
import geopandas as gpd
from shapely import wkt
# Google Earth Engine API 초기화
ee.Initialize(project='ee-jyihaan4')

import shapely.geometry
import random
def apply_scale_factors(image, img_key):
    # 1. 위성영상에 따라 스케일링 팩터 적용
    if 'landsat' in img_key:
        optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
        thermal_bands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
        return image.addBands(optical_bands, None, True).addBands(thermal_bands, None, True)
    elif 'sentinel' in img_key:
        return image.divide(10000)


def mask_clouds(image, img_key):
    # 1. 위성영상에 따라 클라우드 마스킹
    if 'sentinel' in img_key:
        qa = image.select('QA60')

        # 1.1. 구름과 권운 비트 마스크
        cloud_bit_mask = 1 << 10
        cirrus_bit_mask = 1 << 11

        # 1.2. 마스킹 조건 정의

        mask = (qa.bitwiseAnd(cloud_bit_mask).eq(0)
                .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0)))

        return image.updateMask(mask)

    elif 'landsat' in img_key:
        qa = image.select('QA_PIXEL')

        # 1.1. 구름과 그림자 비트 마스크
        cloud_shadow_bit_mask = 1 << 3
        clouds_bit_mask = 1 << 5

        # 1.2. 마스킹 조건 정의
        mask = (qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0)
                .And(qa.bitwiseAnd(clouds_bit_mask).eq(0)))

        return image.updateMask(mask)

def add_indices_band(image, img_key):
    if 'landsat' in img_key:
        band_dct = {'NIR': 'SR_B5', 'RED': 'SR_B4', 'GREEN': 'SR_B3', 'RED_EDGE': 'SR_B6', 'BLUE': 'SR_B2'}

    elif 'sentinel' in img_key:
        band_dct = {'NIR': 'B8', 'RED': 'B4', 'GREEN': 'B3', 'RED_EDGE': 'B5', 'BLUE': 'B2', 'SWIR': 'B11'}

    NIR = image.select(band_dct['NIR'])
    RED = image.select(band_dct['RED'])
    GREEN = image.select(band_dct['GREEN'])

    # 1. 식생지수 산출

    # 1.1. NDVI = (NIR - RED) / (NIR + RED)
    ndvi = image.normalizedDifference([band_dct['NIR'], band_dct['RED']]).rename('NDVI')

    # 1.2. NDRE = (NIR - RED_EDGE) / (NIR + RED_EDGE)
    ndre = image.normalizedDifference([band_dct['NIR'], band_dct['RED_EDGE']]).rename('NDRE')

    # 1.3. GNDVI = (NIR - GREEN) / (NIR + GREEN)
    gndvi = image.normalizedDifference([band_dct['NIR'], band_dct['GREEN']]).rename('GNDVI')

    # 1.4. RVI = NIR / RED
    rvi = NIR.divide(RED).rename('RVI')

    # 1.5. CVI = (RED / GREEN^2) * NIR
    cvi = image.expression(
        '(RED / GREEN ** 2) * NIR', {
            'NIR': image.select(band_dct['NIR']),
            'GREEN': image.select(band_dct['GREEN']),
            'RED': image.select(band_dct['RED'])
        }).rename('CVI')

    # 2. 위성영상에 식생지수 밴드 추가
    return image.addBands([ndvi, cvi, ndre, gndvi, rvi])



def get_satellite(start_date, end_date, site, img_key, imgs):
    # 1. 날짜, 지역
    filtered_imgs = imgs.filterDate(start_date, end_date).filterBounds(site)


    # 2. 클라우드 마스킹, 스케일링 팩터 적용, 식생지수 밴드 추가
    processed_img_collection = (filtered_imgs.map(lambda image: mask_clouds(image, img_key))
                                             .map(lambda image: apply_scale_factors(image, img_key))
                                             .map(lambda image: add_indices_band(image, img_key)))


    return processed_img_collection



def extract_multiple_bands_with_index(image, geometry):
    # 각 밴드 평균 값을 계산
    ndvi_value = image.reduceRegion(ee.Reducer.mean(), geometry=geometry, scale=30).get('NDVI')
    gndvi_value = image.reduceRegion(ee.Reducer.mean(), geometry=geometry, scale=30).get('GNDVI')
    rvi_value = image.reduceRegion(ee.Reducer.mean(), geometry=geometry, scale=30).get('RVI')
    ndre_value = image.reduceRegion(ee.Reducer.mean(), geometry=geometry, scale=30).get('NDRE')
    cvi_value = image.reduceRegion(ee.Reducer.mean(), geometry=geometry, scale=30).get('CVI')

    # system:index와 각 밴드 값을 속성으로 설정
    return image.set({
        'system_index': image.get('system:index'),
        'NDVI_mean': ndvi_value,
        'GNDVI_mean': gndvi_value,
        'RVI_mean': rvi_value,
        'CVI_mean': cvi_value,
        'NDRE_mean': ndre_value,
    })

def process_row(row, images_dct):
    geometry = row['points']
    bands = ['NDVI', 'GNDVI', 'RVI', 'CVI', 'NDRE']

    bands_mean = [band + '_mean' for band in bands]


    imgs, start_date, end_date = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED"), '2021-01-01', '2021-12-31'
    processed_img_collection = get_satellite(start_date, end_date, geometry, 'sentinel', imgs)

    # 컬렉션에 각 이미지의 NDVI 값을 추가한 후, 리스트로 수집
    processed_img_collection = processed_img_collection.map(lambda img: extract_multiple_bands_with_index(img, geometry))
    index_values = processed_img_collection.aggregate_array('system_index').getInfo()
    ndvi_values = processed_img_collection.aggregate_array('NDVI_mean').getInfo()
    gndvi_values = processed_img_collection.aggregate_array('GNDVI_mean').getInfo()
    rvi_values = processed_img_collection.aggregate_array('RVI_mean').getInfo()
    ndre_values = processed_img_collection.aggregate_array('NDRE_mean').getInfo()
    cvi_values = processed_img_collection.aggregate_array('CVI_mean').getInfo()

    # 여러 리스트를 zip으로 묶어 매칭
    combined_values = list(zip(index_values, ndvi_values, gndvi_values, rvi_values))
    df = pd.DataFrame(combined_values, columns=['date', 'NDVI_mean', 'GNDVI_mean', 'RVI_mean', 'NDRE_mean', 'CVI_mean'])
    df['date'] = df['date'].str[:8]

    return df



def random_point_in_polygon(polygon):
    """폴리곤 내에서 랜덤한 점을 생성합니다."""
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        random_point = shapely.geometry.Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(random_point):
            return random_point

def main():
    start_date = ''
    end_date = ''
    file_path = "./static/crop_calendar.geojson"
    # file_path = "test.csv"

    gdf = gpd.read_file(file_path)
    # gdf = pd.read_csv(file_path)

    gdf = gdf.explode()
    gdf = gdf.head()

    # 'points' 열에 랜덤 점 추가
    gdf['points'] = gdf['geometry'].apply(
        lambda geom: ee.Geometry.Point(random_point_in_polygon(geom).x, random_point_in_polygon(geom).y)
    )
    # gdf['points'] = ee.Geometry.Point([126.9780, 37.5665])
    #
    images_dct = {
        'sentinel2': {'imgs': ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED"), 'start_date': '2021-01-01', 'end_date': '2021-12-31'}
                  }

    for idx, row in gdf.iterrows():
        df = process_row(row, images_dct)
        print(df)


if __name__ == '__main__':
    main()