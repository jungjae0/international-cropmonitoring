
import numpy as np
import random
from functools import partial
from datetime import datetime, timedelta, date
import time
import time
import csv
import os
from datetime import datetime
import tqdm
import ee

ee.Authenticate()

ee.Initialize(project='ee-mmkk')


def submitExportTasks(image, year, state, kernel_shape, kernel_buffer):
    country = 'United States of America'
    us = ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level1").filter(
        'ADM0_NAME == "{}"'.format(country)
    )

    out_image_base = f"{state}".replace(' ', '_')
    region = us.filter(ee.Filter.eq("ADM1_NAME", state))
    folder = f'{year}_{state}'.replace(' ', '_')
    # image_base = 'cdl_{}_{}'.format(crop, state).replace(' ', '_')
    task = ee.batch.Export.image.toDrive(
        image=image,
        folder=folder,
        description=out_image_base,
        fileNamePrefix=out_image_base,
        region=region.geometry(),
        scale=30,
        fileFormat='TFRecord',
        maxPixels=1e10,
        formatOptions={
            'patchDimensions': kernel_shape,
            'kernelSize': kernel_buffer,
            'compressed': True,
            'maxFileSize': 104857600
        }
    )
    task.start()

    return task


def downlaod(state, year):
    export_image = ee.batch.Export.image.toDrive(...)
    export_image.start()

    return export_image

# ====== 위성영상 처리 함수들
def mask_l8_sr(image):
    cloud_shadow_bit_mask = ee.Number(2).pow(4).int()
    clouds_bit_mask = ee.Number(2).pow(3).int()
    qa = image.select("QA_PIXEL")
    mask1 = (
        qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0).And(qa.bitwiseAnd(clouds_bit_mask).eq(0))
    )
    mask2 = image.mask().reduce("min")
    mask = mask1.And(mask2)
    return image.updateMask(mask)


def mask_edges(s2_img):
    return s2_img.updateMask(s2_img.select('B8A').mask().updateMask(s2_img.select('B9').mask()))


def mask_clouds(img, max_cloud_probability):
    clouds = ee.Image(img.get('cloud_mask')).select('probability')
    is_not_cloud = clouds.lt(max_cloud_probability)
    return img.updateMask(is_not_cloud)


def merge_s2_l8(s2, l8):
    merged = ee.ImageCollection([s2, l8]).mean()
    return merged


def img_vi(img):
    img = img.addBands(img.normalizedDifference(["nir", "red"]).rename("ndvi"))
    img = img.addBands(img.select(["ndvi"]).multiply(img.select(["nir"])).rename("nirv"))
    return img


def process_date_range(start_date, end_date, s2Sr, l8sr, use_l8):
    s2_criteria = ee.Filter.date(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    l8_criteria = ee.Filter.date(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    s2_reduced = s2Sr.filter(s2_criteria).median().divide(10000).float()
    l8_reduced = l8sr.filter(l8_criteria).median().multiply(0.0000275).add(-0.2).float()
    if use_l8:
        image = merge_s2_l8(s2_reduced, l8_reduced)
    else:
        image = s2_reduced
    return img_vi(image).float()


# ======= Sentinel2 영상 최종 결과 얻기
def get_final_s2(max_cloud_probability, band_names_s2, band_names_out):
    s2_sr = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").map(mask_edges)
    s2_clouds = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
    s2_sr_with_cloud_mask = ee.Join.saveFirst('cloud_mask').apply(
        primary=s2_sr,
        secondary=s2_clouds,
        condition=ee.Filter.equals(leftField='system:index', rightField='system:index')
    )
    partial_mask_clouds = partial(mask_clouds, max_cloud_probability=max_cloud_probability)
    s2_cloud_masked = ee.ImageCollection(s2_sr_with_cloud_mask).map(partial_mask_clouds)
    s2_sr = s2_cloud_masked.select(band_names_s2, band_names_out)

    return s2_sr


# ======== Landsat8 영상 최종 결과 얻기
def get_final_landsat8(band_names_l8, band_names_out):
    l8sr = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").map(mask_l8_sr)
    l8sr = l8sr.select(band_names_l8, band_names_out)

    return l8sr



def run(target_year, target_state):
    # ====== 입력자료의 기간
    start_month, start_day = 5, 1
    end_month, end_day = 7, 1

    # ====== 위성이미지 처리를 위해 사용하는 band와 cloud 값
    band_names_out = ["blue", "green", "red", "nir", "swir1", "swir2"]
    band_names_l8 = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
    band_names_s2 = ["B2", "B3", "B4", "B8", "B11", "B12"]
    bands = ["blue", "green", "red", "nir", "swir1", "swir2", "ndvi", "nirv"]
    max_cloud_probability = 65

    # ====== Sentinel2와 Landsat8 불러옴
    s2_sr = get_final_s2(max_cloud_probability, band_names_s2, band_names_out)
    l8sr = get_final_landsat8(band_names_l8, band_names_out)

    # ====== kernel
    kernel_size = 128
    kernel_shape = [kernel_size, kernel_size]
    kernel_buffer = [64, 64]
    list1 = ee.List.repeat(1, kernel_size)
    lists = ee.List.repeat(list1, kernel_size)
    kernel = ee.Kernel.fixed(kernel_size, kernel_size, lists)

    image = process_date_range(date(target_year, start_month, start_day), date(target_year, end_month, end_day),
                               s2_sr, l8sr, use_l8=True)

    task = submitExportTasks(image, target_year, target_state, kernel_shape, kernel_buffer)
    return task

def main():
    target_year = 2023
    target_state = 'Nebraska'

    task = run(target_year, target_state)





if __name__ == '__main__':
    main()
