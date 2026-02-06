import os
import time
from datetime import datetime
from multiprocessing import Pool, current_process, get_context
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS
from rasterio.mask import mask
from rasterio.warp import Resampling, calculate_default_transform, reproject
from rasterio.warp import transform as rio_transform
from tqdm import tqdm

from core.utils.redis_client import (
    increment_progress,
    increment_step_progress,
    is_cancelled,
    set_progress,
    set_step_progress,
)
from core.utils.log_files import (
    append_csv_row,
    append_log,
    csv_path,
    format_elapsed_hms,
    format_error_with_trace,
)

import unicodedata

AREA_CSV_HEADERS = (
    "timestamp",
    "state",
    "crop",
    "input_path",
    "input_bytes",
    "elapsed_sec",
    "elapsed_hms",
    "status",
)


def reproject_to_1bit_binary(input_path, output_path, resolution=10, nodata_value=255):
    with rasterio.open(input_path) as src:
        if src.crs.is_geographic:
            left, bottom, right, top = src.bounds
            center_lon = (left + right) / 2
            center_lat = (bottom + top) / 2
        else:
            left, bottom, right, top = src.bounds
            center_x = (left + right) / 2
            center_y = (bottom + top) / 2
            center_lon, center_lat = rio_transform(
                src.crs, "EPSG:4326", [center_x], [center_y]
            )
            center_lon, center_lat = center_lon[0], center_lat[0]
        zone_number = int((center_lon + 180) / 6) + 1
        is_northern = center_lat >= 0
        utm_crs = CRS.from_dict({"proj": "utm", "zone": zone_number, "south": not is_northern})
        dst_transform, width, height = calculate_default_transform(
            src.crs, utm_crs, src.width, src.height, *src.bounds, resolution=resolution
        )
        kwargs = src.meta.copy()
        kwargs.update(
            {
                "driver": "GTiff",
                "crs": utm_crs,
                "transform": dst_transform,
                "width": width,
                "height": height,
                "dtype": "uint8",
                "count": src.count,
                "nodata": nodata_value,
            }
        )
        with rasterio.open(output_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=utm_crs,
                    resampling=Resampling.nearest,
                    src_nodata=src.nodata,
                    dst_nodata=nodata_value,
                )
    return output_path, utm_crs


def remove_accents(text):
    if isinstance(text, str):
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    return text


def clip_and_calculate_area_by_class(raster_path, vector_path, state_name, resolution):
    gdf = gpd.read_file(vector_path)
    query_name = state_name.replace("_", " ")
    state_layer = gdf[gdf["NAME_1"].apply(remove_accents) == query_name]
    if state_layer.empty:
        raise ValueError(f"State name '{query_name}' not found in shapefile.")
    with rasterio.open(raster_path) as src:
        if state_layer.crs != src.crs:
            state_layer = state_layer.to_crs(src.crs)
        clipped_image, _ = mask(src, state_layer.geometry, crop=True)
        clipped_data = clipped_image[0]
        unique, counts = np.unique(clipped_data, return_counts=True)
        pixel_area = resolution * resolution
        area_by_class = {
            int(cls): int(count * pixel_area)
            for cls, count in zip(unique, counts)
            if cls != src.nodata
        }
        return area_by_class


def process_tiff_task(args):
    input_tiff, temp_dir, shapefile_path, resolution, crop, year_suffix, state_name, job_id = args
    if is_cancelled(job_id):
        return {
            "rows": [],
            "metrics": {
                "state": state_name,
                "crop": crop,
                "input_path": input_tiff,
                "input_bytes": 0,
                "elapsed_sec": 0.0,
                "status": "cancelled",
            },
        }
    filename = os.path.basename(input_tiff)
    output_temp_tiff = os.path.join(temp_dir, f"temp_area_{filename}")
    results = []
    started = time.perf_counter()
    input_bytes = os.path.getsize(input_tiff) if os.path.exists(input_tiff) else 0
    try:
        reprojected_path, _ = reproject_to_1bit_binary(
            input_tiff, output_temp_tiff, resolution
        )
        area_by_class = clip_and_calculate_area_by_class(
            reprojected_path, shapefile_path, state_name, resolution
        )
        for cls, area_m2 in area_by_class.items():
            if cls == 0:
                continue
            area_acre = area_m2 / 4046.8564224
            area_ha = area_m2 / 10000.0
            results.append(
                {
                    "state": state_name,
                    "year": year_suffix,
                    "crop": crop,
                    "class_id": cls,
                    "area_m2": area_m2,
                    "area_ha": round(area_ha, 2),
                    "area_acre": round(area_acre, 2),
                }
            )
    except Exception as exc:
        append_log(job_id, format_error_with_trace(f"area {state_name}/{crop}", exc))
        raise
    finally:
        if os.path.exists(output_temp_tiff):
            try:
                os.remove(output_temp_tiff)
            except OSError:
                pass
    elapsed = time.perf_counter() - started
    return {
        "rows": results,
        "metrics": {
            "state": state_name,
            "crop": crop,
            "input_path": input_tiff,
            "input_bytes": input_bytes,
            "elapsed_sec": round(elapsed, 4),
            "status": "ok",
        },
    }


def update_csv_results(output_csv_path: str, new_rows: List[Dict], processed_states: List[str]):
    if not new_rows and not processed_states:
        return
    cols = ["state", "year", "crop", "class_id", "area_m2", "area_ha", "area_acre"]
    new_df = pd.DataFrame(new_rows)
    if not new_df.empty:
        new_df = new_df[cols]
    if os.path.exists(output_csv_path):
        try:
            existing_df = pd.read_csv(output_csv_path)
            cleaned_df = existing_df[~existing_df["state"].isin(processed_states)]
            if not new_df.empty:
                final_df = pd.concat([cleaned_df, new_df], ignore_index=True)
            else:
                final_df = cleaned_df
        except Exception:
            final_df = new_df
    else:
        final_df = new_df
    if not final_df.empty:
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        final_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")


def get_crop_list(crops_str: str) -> List[str]:
    alias_map = {
        "corn": "Corn",
        "maize": "Corn",
        "soy": "Soybean",
        "soybean": "Soybean",
        "soybeans": "Soybean",
        "springwheat": "SpringWheat",
        "spring_wheat": "SpringWheat",
        "winterwheat": "WinterWheat",
        "winter_wheat": "WinterWheat",
    }
    raw_list = [c.strip().lower() for c in crops_str.replace(" ", ",").split(",") if c.strip()]
    final_list = []
    for item in raw_list:
        if item in alias_map:
            val = alias_map[item]
            if val not in final_list:
                final_list.append(val)
        else:
            if item.capitalize() not in final_list:
                final_list.append(item.capitalize())
    return final_list


def run_area_calc(
        output_root: str,
        year_suffix: str,
        country: str,
        crops: str,
        states: List[str],
        shapefile_path: str,
        job_id: int,
        resolution: int = 10,
        workers: int = 4,
        temp_dir: str = "temp_area",
        skip_exists: bool = False,
) -> None:
    input_base = os.path.join(output_root, "merged_cropmasks", year_suffix, country)
    output_dir = os.path.join(output_root, "calculate_area")
    if not os.path.exists(input_base):
        return
    crop_names = get_crop_list(crops)
    os.makedirs(temp_dir, exist_ok=True)
    all_tasks: List[Tuple] = []
    for crop in crop_names:
        for state in states:
            filename = f"{year_suffix}_{country}_{state}_{crop}.tif"
            file_path = os.path.join(input_base, state, crop, filename)
            if os.path.exists(file_path):
                if skip_exists:
                    csv_filename = f"{year_suffix}_{country}_{crop}.csv"
                    csv_file_path = os.path.join(output_dir, csv_filename)
                    if os.path.exists(csv_file_path):
                        continue
                all_tasks.append(
                    (file_path, temp_dir, shapefile_path, resolution, crop, year_suffix, state, job_id)
                )
    set_progress(job_id, 0, len(all_tasks), "Starting area calculation")
    set_step_progress(job_id, "area", 0, len(all_tasks), "Starting area calculation")
    if not all_tasks:
        return
    crop_results: List[Dict] = []

    def _iter_results() -> Iterable[List[Dict]]:
        if current_process().daemon:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(process_tiff_task, t) for t in all_tasks]
                for fut in as_completed(futures):
                    yield fut.result()
        else:
            ctx = get_context("spawn")
            with ctx.Pool(processes=workers) as pool:
                for result in pool.imap_unordered(process_tiff_task, all_tasks):
                    yield result

    append_log(job_id, "Area calculation started")
    with tqdm(total=len(all_tasks), desc="Calculating area", unit="file") as pbar:
        for result in _iter_results():
            crop_results.extend(result.get("rows", []))
            metrics = result.get("metrics")
            if metrics:
                append_csv_row(
                    csv_path(job_id, "area_states"),
                    AREA_CSV_HEADERS,
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "state": metrics["state"],
                        "crop": metrics["crop"],
                        "input_path": metrics["input_path"],
                        "input_bytes": metrics["input_bytes"],
                        "elapsed_sec": metrics["elapsed_sec"],
                        "elapsed_hms": format_elapsed_hms(metrics["elapsed_sec"]),
                        "status": metrics["status"],
                    },
                )
                append_log(
                    job_id,
                    f"Area {metrics['state']}/{metrics['crop']} status={metrics['status']} elapsed={metrics['elapsed_sec']:.2f}s input_bytes={metrics['input_bytes']}",
                )
            increment_progress(job_id, increment=1, message="Calculating area")
            increment_step_progress(job_id, "area", increment=1, message="Calculating area")
            pbar.update(1)
    for crop in crop_names:
        crop_rows = [row for row in crop_results if row["crop"] == crop]
        csv_filename = f"{year_suffix}_{country}_{crop}.csv"
        csv_file_path = os.path.join(output_dir, csv_filename)
        update_csv_results(csv_file_path, crop_rows, states)
    append_log(job_id, "Area calculation finished")
    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except OSError:
        pass
