import os
# 1) pyproj가 사용하는 proj 데이터 디렉터리를 강제로 PROJ_LIB로 지정
# os.environ["PROJ_LIB"] = r"C:\Users\user\anaconda3\envs\rs\Library\share\proj"
# import os
# import shutil
# import rasterio
# from rasterio.warp import calculate_default_transform, reproject, Resampling
import leafmap.foliumap as leafmap
from localtileserver import TileClient
import streamlit as st
# def ensure_3857_tif(src_path, dst_path=None, overwrite=False, num_threads=4):
#     """
#     src_path GeoTIFF을 EPSG:3857로 재투영하여 저장하고,
#     결과 GeoTIFF 경로를 반환한다.
#
#     - 이미 3857이면 재투영 생략하고 그대로 사용 (또는 복사)
#     - 타일 서버 친화적으로 압축/타일링/오버뷰 생성
#     """
#
#     if dst_path is None:
#         base, ext = os.path.splitext(src_path)
#         dst_path = base + "_3857" + ext
#
#     # 이미 결과 파일이 있고, 덮어쓰지 않는 옵션이면 바로 반환
#     if os.path.exists(dst_path) and not overwrite:
#         return dst_path
#
#     with rasterio.open(src_path) as src:
#         src_crs = src.crs
#         dst_crs = "EPSG:3857"
#
#         # 이미 3857이면 굳이 재투영 안 하고 복사만 할 수도 있음
#         if src_crs is not None and src_crs.to_string() == dst_crs and not overwrite:
#             if src_path != dst_path:
#                 shutil.copy2(src_path, dst_path)
#             return dst_path
#
#         # 새 transform, width, height 계산
#         dst_transform, width, height = calculate_default_transform(
#             src.crs, dst_crs, src.width, src.height, *src.bounds
#         )
#
#         # 메타데이터 복사 후 3857 및 최적화 옵션 반영
#         dst_meta = src.meta.copy()
#         dst_meta.update(
#             {
#                 "crs": dst_crs,
#                 "transform": dst_transform,
#                 "width": width,
#                 "height": height,
#                 "driver": "GTiff",
#                 "compress": "LZW",   # 무손실 압축
#                 "tiled": True,       # 타일 단위 저장
#                 "blockxsize": 256,
#                 "blockysize": 256,
#             }
#         )
#
#         # 재투영 + 저장
#         with rasterio.open(dst_path, "w", **dst_meta) as dst:
#             for i in range(1, src.count + 1):
#                 reproject(
#                     source=rasterio.band(src, i),
#                     destination=rasterio.band(dst, i),
#                     src_transform=src.transform,
#                     src_crs=src.crs,
#                     dst_transform=dst_transform,
#                     dst_crs=dst_crs,
#                     resampling=Resampling.nearest,
#                     num_threads=num_threads,
#                 )
#
#             # 오버뷰(overview) 생성: 줌 레벨 변환 속도 향상
#             factors = [2, 4, 8, 16]
#             dst.build_overviews(factors, Resampling.nearest)
#             dst.update_tags(ns="rio_overview", resampling="nearest")
#
#     return dst_path



def main():
    # 원본 4326(또는 다른 CRS) GeoTIFF
    src_path = r"Y:\DATA\CropMonitoring\cropmap\MAIZE\USA\v1\US-WI\2025\10\MAIZE_USA_US-WI_10_30.tif"

    # 3857 최적화 GeoTIFF 생성/재사용
    path_3857 = "MAIZE_USA_US-WI_10_30_3857.tif"# ensure_3857_tif(src_path)
    st.write(f"EPSG:3857 GeoTIFF path: {path_3857}")

    # 로컬 타일 서버 클라이언트 생성
    client = TileClient(path_3857)
    st.write(client.get_tile_url())


    # Leafmap 지도 (기본 베이스맵은 EPSG:3857)
    m = leafmap.Map()

    # 타일 레이어 추가
    m.add_tile_layer(
        url=client.get_tile_url(),
        name="MAIZE_US-WI_3857",
        attribution="Local Tile Server",
    )

    # Streamlit에 렌더링
    m.to_streamlit(height=600)


if __name__ == "__main__":
    main()
