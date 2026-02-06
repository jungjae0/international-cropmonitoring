import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import csv
import json
import math
import time
import glob
import numpy as np
import xarray as xr
from tqdm import tqdm
from affine import Affine
import torch
import tensorflow as tf
import segmentation_models_pytorch as smp
from .model_and_env.data_loader import data_load

import rioxarray


from django.conf import settings

def get_model(ckpt_path, device, nclass, bands):
    model = smp.Unet(
        encoder_name="resnet50",
        encoder_weights="imagenet",
        in_channels=len(bands),
        classes=nclass,
        activation="softmax",
        decoder_attention_type="scse",
        decoder_channels=(512, 256, 128, 64, 32)
    ).to(device)
    model = torch.nn.DataParallel(model)

    checkpoint = torch.load(ckpt_path)

    model.load_state_dict(checkpoint)
    model.eval()

    return model

def split_files(tf_files, chunk_count=70):
    tf_files = list(tf_files)
    chunk_count = min(chunk_count, len(tf_files))
    return np.array_split(tf_files, chunk_count)

def doPrediction(tf_files, description, model, bands, batch_size, device,
                 x_buffer, y_buffer, kernel_shape, chunk_count=70, progress_callback=None):

    prediction_results = []

    # TFRecord 파일을 chunk_count 개로 나누기
    tf_chunks = split_files(tf_files, chunk_count)

    for chunk_idx, chunk in enumerate(tqdm(tf_chunks, desc="Predicting chunks")):
        # chunk는 tfrecord 파일 경로 리스트
        data = data_load(
            list(chunk), bands, description, batch_size=batch_size
        ).get_pridiction_dataset()

        chunk_predictions = []

        for batch in data.as_numpy_iterator():
            inputs = torch.tensor(batch)#.to(device)
            with torch.no_grad():
                outputs = model(inputs).cpu().numpy()

            preds = outputs.argmax(axis=1).squeeze()[
                :,
                x_buffer : x_buffer + kernel_shape[0],
                y_buffer : y_buffer + kernel_shape[1],
            ]

            chunk_predictions.append(preds.astype("int8"))

        if chunk_predictions:
            prediction_results.append(np.vstack(chunk_predictions))

        if progress_callback:
            progress = int(100 * (chunk_idx + 1) / chunk_count)
            progress_callback(progress)

    return prediction_results

# def to_image(img, mixer, raster_dir):
#     with open(mixer) as f:
#         mixer = json.load(f)
#
#     doubleMatrix = mixer["projection"]["affine"]["doubleMatrix"]
#     patchesPerRow = mixer["totalPatches"] / mixer["patchesPerRow"]
#     img = np.split(img, patchesPerRow)
#     img = [np.hstack(l) for l in img]
#     img = np.vstack(img).astype("int8")
#
#     ds = xr.DataArray(img)
#
#     # 清理 img 变量以节省内存
#     img = []
#
#     ds = ds.rio.write_crs(4326, inplace=True)
#     transform = Affine(*doubleMatrix)
#     ds.rio.write_transform(transform, inplace=True)
#     ds.spatial_ref.GeoTransform
#     ds.rio.set_spatial_dims("dim_1", "dim_0")
#
#     # 在此处设置无数据值
#     ds.rio.write_nodata(-1, inplace=True)  # 使用适当的无数据值
#
#     # ds = ds.rio.reproject("EPSG:5070")
#     ds.rio.to_raster(raster_dir, driver='GTiff', dtype='int8', compress='LZW')


def to_image(img, mixer, raster_dir):
    with open(mixer) as f:
        mixer = json.load(f)

    doubleMatrix = mixer["projection"]["affine"]["doubleMatrix"]
    patchesPerRow = mixer["totalPatches"] / mixer["patchesPerRow"]
    img = np.split(img, patchesPerRow)
    img = [np.hstack(l) for l in img]
    img = np.vstack(img).astype("int8")

    ds = xr.DataArray(img)

    # 메모리 절약을 위해 img 제거
    img = []

    # 원래 좌표계: EPSG:4326
    ds = ds.rio.write_crs(4326, inplace=True)
    transform = Affine(*doubleMatrix)
    ds.rio.write_transform(transform, inplace=True)
    ds.rio.set_spatial_dims("dim_1", "dim_0")

    # nodata 값 설정
    ds.rio.write_nodata(-1, inplace=True)

    # ✅ EPSG:3857로 재투영
    ds_3857 = ds.rio.reproject("EPSG:3857")

    # GeoTIFF 저장 (재투영 결과)
    ds_3857.rio.to_raster(raster_dir, driver='GTiff', dtype='int8', compress='LZW')

def predict_and_save_tif(bands, num_class, state, weights_path, tfrecord_paths, mixer_path, output_npy_path, output_tiff_path, chunk_count=70, progress_callback=None):
    if not os.path.exists(output_npy_path) and not os.path.exists(output_tiff_path):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = get_model(weights_path, device, num_class, bands)

        features = bands


        batch_size = 64
        kernel_shape = [128, 128]
        kernel_buffer = [64, 64]

        x_buffer = int(kernel_buffer[0] / 2)
        y_buffer = int(kernel_buffer[1] / 2)

        buffered_shape = [
            kernel_shape[0] + kernel_buffer[0],
            kernel_shape[1] + kernel_buffer[1],
        ]
        columns = [
            tf.io.FixedLenFeature(shape=buffered_shape, dtype=tf.float32) for k in features
        ]

        description = dict(zip(features, columns))


        prediction = doPrediction(tfrecord_paths, description, model, bands, batch_size, device,
                     x_buffer, y_buffer, kernel_shape, chunk_count=chunk_count, progress_callback=progress_callback)

        img = np.vstack(prediction)
        np.save(output_npy_path, img)

        for_tiff_img = np.load(output_npy_path, allow_pickle=True)

        to_image(for_tiff_img, mixer_path, output_tiff_path)

    elif os.path.exists(output_npy_path) and not os.path.exists(output_tiff_path):
        for_tiff_img = np.load(output_npy_path, allow_pickle=True)

        to_image(for_tiff_img, mixer_path, output_tiff_path)

    else:
        print(f"Prediction already done for {state}.")


    # os.remove(output_npy_path)
    # print("-" * 50 , f"Prediction Done {state}", "-" * 50)
    # print(f"Prediction saved to {output_npy_path}")
    # print(f"Prediction saved to {output_tiff_path}")

def run(crop, target_year, target_state, job=None):
    # time.sleep(90)
    def update_progress(p):
        if job:
            job.progress = p
            job.current_step = 'model_inference'
            job.save()
    bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'ndvi', 'nirv']

    # drive_folder = fr"H:\내 드라이브"
    drive_folder = r"Y:\DATA\국외작황모니터링 자료\US_TFrecord"
    weights_folder = r"Y:\DATA\국외작황모니터링 자료\US_Satellite\weights"
    # predict_folder = rf"Y:\DATA\국외작황모니터링 자료\01_미국작물구분도\{target_year}_cropmapping"


    output_dir = os.path.join(
        settings.MEDIA_ROOT,
        job.crop_type,
        job.region,
        str(job.year)
    )
    os.makedirs(
        output_dir,
        exist_ok=True
    )
    output_tif_path = os.path.join(output_dir, f"{str(job.year)}_{job.crop_type}_{job.region}.tif")
    output_npy_path = output_tif_path.replace(".tif", ".npy")



    north_state = ["Washington", "Oregon", "Idaho", "Texas"]
    south_state = ["Kansas", "Oklahoma", "Colorado", "Nebraska",]

    num_class = 3 if target_state in north_state else 2
    point = "north" if target_state in north_state else "south"
    weights_path = os.path.join(weights_folder, f"{point}.pt")
    state_folder = os.path.join(drive_folder, f"{target_year}_{target_state}")

    mixer_path = glob.glob(os.path.join(state_folder, "*.json"))[0]
    tfrecord_paths = glob.glob(os.path.join(state_folder, "*.tfrecord.gz"))
    tfrecord_paths = sorted(tfrecord_paths)

    # output_tif_path = os.path.join(predict_folder, f"{target_year}_{crop}_{target_state}.tif")
    # output_npy_path = os.path.join(predict_folder, f"{target_year}_{crop}_{target_state}.npy")

    predict_and_save_tif(bands, num_class, target_state, weights_path, tfrecord_paths, mixer_path, output_npy_path, output_tif_path,  progress_callback=update_progress)

    return output_tif_path

def main():
    pass


if __name__ == "__main__":
    main()
