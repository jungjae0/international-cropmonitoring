import os
import re
import subprocess
from osgeo import gdal
import numpy as np
import sys
os.environ['GDAL_DATA'] = r'C:\OSGeo4W\share\gdal'
os.environ['PROJ_LIB'] = r'C:\OSGeo4W\share\proj'
os.environ['PATH'] = r'C:\OSGeo4W\bin;' + os.environ['PATH']
os.environ['PATH'] = (
    r'C:\OSGeo4W\bin;' +
    r'C:\OSGeo4W\apps\gdal\bin;' +
    r'C:\OSGeo4W\apps\Python39\Scripts;' +
    r'C:\OSGeo4W\apps\Python39;' +
    os.environ['PATH']
)

import gdal2tiles
def black2colors(input_tiff):
    dataset = gdal.Open(input_tiff)
    band = dataset.GetRasterBand(1)
    array = band.ReadAsArray()
    unique_values = np.unique(array)

    temp_color_tiff = os.path.join(os.path.dirname(input_tiff), "temp_color_output.tif")
    final_color_tiff = os.path.join(os.path.dirname(input_tiff), "color_output_3857.tif")

    color_map = {
        0: (0, 0, 0),
        1: (0, 255, 0),
        2: (255, 255, 0),
        # 3: (0, 255, 0),
        # 4: (0, 0, 255),
        # 5: (255, 0, 0),
    }

    color_array = np.zeros((3, array.shape[0], array.shape[1]), dtype=np.uint8)

    for val in unique_values:
        color = color_map.get(val, (0, 0, 0))  # 미정의 값은 검정
        mask = (array == val)
        color_array[0][mask] = color[0]
        color_array[1][mask] = color[1]
        color_array[2][mask] = color[2]

    # 원본 지리정보
    geotransform = dataset.GetGeoTransform()
    projection = dataset.GetProjection()

    # 임시 RGB GeoTIFF 저장
    driver = gdal.GetDriverByName("GTiff")
    out_dataset = driver.Create(temp_color_tiff, array.shape[1], array.shape[0], 3, gdal.GDT_Byte)
    out_dataset.SetGeoTransform(geotransform)
    out_dataset.SetProjection(projection)
    out_dataset.SetMetadata(dataset.GetMetadata())

    for i in range(3):
        out_band = out_dataset.GetRasterBand(i + 1)
        out_band.WriteArray(color_array[i])

    out_dataset.FlushCache()
    out_dataset = None
    dataset = None

    # EPSG:3857 좌표계로 재투영
    gdal.Warp(
        final_color_tiff,
        temp_color_tiff,
        dstSRS='EPSG:3857',
        format='GTiff',
        multithread=True,
        outputType=gdal.GDT_Byte
    )

    # 임시 파일 삭제 (필요 시 생략)
    if os.path.exists(temp_color_tiff):
        os.remove(temp_color_tiff)

    return final_color_tiff


def run(input_tiff, output_dir, progress_callback=None, zoom='5-12'):
    final_color_tiff = black2colors(input_tiff)
    gdal2tiles.generate_tiles(final_color_tiff, output_dir, zoom='5-12')



    # command = [sys.executable, r"C:\code\DataManger\.venv\Lib\site-packages\gdal2tiles\gdal2tiles.py", final_color_tiff, output_dir]
    #
    # pattern = re.compile(r"(\d+)\.\.\.")
    #
    # with subprocess.Popen(
    #         command,
    #         stdout=subprocess.PIPE,
    #         stderr=subprocess.STDOUT,
    #         universal_newlines=True,
    #         bufsize=1
    # ) as proc:
    #     for line in proc.stdout:
    #         print(line.strip())
    #         match = pattern.search(line)
    #         if match and progress_callback:
    #             progress = int(match.group(1))
    #             progress_callback(progress)
    #     proc.wait()
    #
    # if progress_callback:
    #     progress_callback(100)





    # command = ["gdal2tiles", final_color_tiff, output_dir]
    # pattern = re.compile(r"(\d+)\.\.\.")  # 0... 10... 20... 추출
    #
    # with subprocess.Popen(
    #     command,
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.STDOUT,
    #     universal_newlines=True,
    #     bufsize=1,
    # ) as proc:
    #     for line in proc.stdout:
    #         print(line.strip())  # 디버깅용
    #         match = pattern.search(line)
    #         if match and progress_callback:
    #             progress = int(match.group(1))
    #             progress_callback(progress)
    # proc.wait()
    #
    # if progress_callback:
    #     progress_callback(100)
# start_time = time.time()
# output_dir = r'C:\cropmapping\tiles_py_gdal'
# run(r"C:\Users\user\Downloads\2024_Wheat_Kansas.tif", output_dir, zoom='4-20')
# end_time = time.time()
#
# print(time.strftime("%H:%M:%S", time.gmtime(end_time - start_time)))