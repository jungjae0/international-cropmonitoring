# utils.py
import os
from .models import FileRecord

# root_dir 설정
# ROOT_DIR = r"satellite"
#
# # data_source와 region 리스트 설정
# DATA_SOURCES = ["sentinel2"]
# REGIONS = ["korea"]



# def save_file_paths_to_db():
#     for data_source in DATA_SOURCES:
#         data_source_path = os.path.join(ROOT_DIR, data_source)
#         REGIONS = os.listdir(data_source_path)
#         # "Z:\DATA\00_국외작황모니터링 자료\satellite\sentinel2\korea_sentinel2\2020\1"
#         for region in REGIONS:
#             region_path = os.path.join(data_source_path, region)
#             years = sorted(int(os.path.basename(year)) for year in os.listdir(region_path))
#
#             for year in years:
#                 year_path = os.path.join(region_path, f"{year}")
#                 months = sorted([int(os.path.basename(month)) for month in os.listdir(year_path)])
#
#                 for month in months:
#                     month_path = os.path.join(year_path, f"{int(month):02d}")
#
#                     for file_name in os.listdir(month_path):
#                         if file_name.endswith(".tif"):
#                             file_path = os.path.join(month_path, file_name)
#
#                             if os.path.isfile(file_path):
#                                 # print(file_path)
#                                 FileRecord.objects.get_or_create(
#                                     data_source=data_source,
#                                     year = year,
#                                     month = month,
#                                     nation=region,
#                                     path=file_path
#                                 )

# save_file_paths_to_db()

                # for month in months:
                #     month_path = os.path.join(year_path, month)
                #     for file_name in os.listdir(month_path):
                #         file_path = os.path.join(month_path, file_name)
                #         print(file_path)




# def save_file_paths_to_db():
#     for data_source in DATA_SOURCES:
#         for region in REGIONS:
#             folder_path = os.path.join(ROOT_DIR, data_source, f"{region}_{data_source}")
#             # print(folder_path)
#             if os.path.exists(folder_path):
#                 for file_name in os.listdir(folder_path):
#                     file_path = os.path.join(folder_path, file_name)
#                     # print(file_path)
#                     if os.path.isfile(file_path):  # 파일만 저장
#                         # 데이터베이스에 저장
#                         FileRecord.objects.get_or_create(
#                             data_source=data_source,
#                             region=region,
#                             path=file_path
#                         )
# save_file_paths_to_db()
# temp()



def save_file_paths_to_db():
    ROOT_DIR = r"./data"
    DATA_SOURCES = ["sentinel2"]
    REGIONS = ["us/north_dakota"]
    YEARS = [2025]


    for region in REGIONS:
        for data_source in DATA_SOURCES:
            for year in YEARS:
                data_year_folder = os.path.join(ROOT_DIR, region, data_source, str(year))
                if os.path.exists(data_year_folder):
                    for year_folder in os.listdir(data_year_folder):
                        month_folder = os.path.join(data_year_folder, year_folder)
                        month = os.path.basename(month_folder)

                        for doy_file_name in os.listdir(month_folder):
                            if doy_file_name.endswith('.tif'):
                                doy_file_path = os.path.join(month_folder, doy_file_name)

                                FileRecord.objects.get_or_create(
                                    data_source=data_source,
                                    year = year,
                                    month = month,
                                    nation=region,
                                    path=doy_file_path
                                )