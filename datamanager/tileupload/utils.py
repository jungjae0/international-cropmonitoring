import subprocess, os, sys
import time
import gdal2tiles
from django.conf import settings
from osgeo import gdal
import numpy as np


def black2colors(input_tiff, label_data):
    dataset = gdal.Open(input_tiff)
    band = dataset.GetRasterBand(1)
    array = band.ReadAsArray()
    unique_values = np.unique(array)
    print("Done reading array...")
    if dataset is None:
        raise FileNotFoundError(f"GDAL cannot open input file: {input_tiff}")
    temp_color_tiff = os.path.join(os.path.dirname(input_tiff), "_colored.tif")
    final_color_tiff = os.path.join(os.path.dirname(input_tiff), "_3857.tif")

    # ✅ label_data로 color_map 생성
    color_map = {}
    for item in label_data:
        rgb = tuple(int(item['color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        color_map[int(item['value'])] = (rgb, 255)  # 항상 불투명 처리

    # default: 회색 + 투명
    default_rgba = ((200, 200, 200), 0)

    color_array = np.zeros((4, array.shape[0], array.shape[1]), dtype=np.uint8)

    for val in unique_values:
        (r, g, b), a = color_map.get(val, default_rgba)
        mask = (array == val)
        color_array[0][mask] = r
        color_array[1][mask] = g
        color_array[2][mask] = b
        color_array[3][mask] = a
    geotransform = dataset.GetGeoTransform()
    projection = dataset.GetProjection()
    driver = gdal.GetDriverByName("GTiff")
    out_dataset = driver.Create(temp_color_tiff, array.shape[1], array.shape[0], 4, gdal.GDT_Byte)
    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)
    out_dataset.SetMetadata(dataset.GetMetadata())

    # ✅ 밴드별로 RGBA 배열을 작성
    print("Done writing array...")
    for i in range(4):
        out_band = out_dataset.GetRasterBand(i + 1)
        out_band.WriteArray(color_array[i])
        if i == 3:
            out_band.SetColorInterpretation(gdal.GCI_AlphaBand)  # 4번째는 알파 밴드
        else:
            out_band.SetNoDataValue(0)

    out_dataset.FlushCache()
    out_dataset = None
    dataset = None


    # 좌표계 재투영 (RGBA 그대로 유지됨)
    gdal.Warp(
        final_color_tiff,
        temp_color_tiff,
        dstSRS='EPSG:3857',
        format='GTiff',
        # multithread=True,
        outputType=gdal.GDT_Byte,
    creationOptions=["COMPRESS=LZW"]  # ✅ 압축 옵션 추가

    )

    print("Done reproject...")
    # 임시 파일 삭제 (필요 시 생략)
    if os.path.exists(temp_color_tiff):
        os.remove(temp_color_tiff)

    if not os.path.exists(final_color_tiff):
        raise RuntimeError("GDAL failed to produce output TIFF.")

    return final_color_tiff

def run_gdal2tiles(input_tiff, output_dir, label_data):
    print("📦 Starting GDAL conversion...")
    final_color_tiff = black2colors(input_tiff, label_data)
    print("📦 Done GDAL conversion...")

    print("📦 Starting generate_tiles...")
    # gdal2tiles.generate_tiles(final_color_tiff, output_dir, zoom='5-12')

    cmd = [
        "gdal2tiles.py",
        "-z", '5-12',
        final_color_tiff,
        output_dir
    ]
    subprocess.run(cmd, check=True)

    print("📦 Done generate_tiles...")

    time.sleep(5)
    os.remove(final_color_tiff)