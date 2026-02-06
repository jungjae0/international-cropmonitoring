import gc
import glob
import os
import time
from datetime import datetime
from dataclasses import dataclass
from multiprocessing import Pool, current_process, get_context
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Iterable

import rioxarray
import xarray as xr
from dask.callbacks import Callback
from tqdm import tqdm

from core.utils.redis_client import (
    add_step_total,
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
    format_error_message,
)

try:
    from rioxarray.merge import merge_arrays as rio_merge_arrays
except ImportError:
    rio_merge_arrays = None

MERGE_CSV_HEADERS = (
    "timestamp",
    "state",
    "crop",
    "output_path",
    "output_bytes",
    "elapsed_sec",
    "elapsed_hms",
    "status",
)


@dataclass
class MergeConfig:
    tile_glob_pattern: str = "*.tif"
    dask_chunks: Tuple[int, int] = (2048, 2048)
    compress: str = "DEFLATE"
    bigtiff: str = "YES"
    nodata_value: float = 99
    skip_if_exists: bool = True


def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def merge_task_worker(args):
    state, crop, input_dir, output_path, cfg_dict = args
    job_id = cfg_dict.pop("job_id", 0)
    if is_cancelled(job_id):
        return (state, crop, False, "Cancelled", 0.0, 0, output_path)
    cfg = MergeConfig(**cfg_dict)
    tiles = glob.glob(os.path.join(input_dir, cfg.tile_glob_pattern))
    if not tiles:
        return (state, crop, False, "No tiles found", 0.0, 0, output_path)
    if cfg.skip_if_exists and os.path.exists(output_path):
        return (state, crop, True, "Skipped (Exists)", 0.0, os.path.getsize(output_path), output_path)
    started = time.perf_counter()
    try:
        datasets = []
        add_step_total(job_id, "merge_tiles", len(tiles))
        for fp in tiles:
            if is_cancelled(job_id):
                return (state, crop, False, "Cancelled")
            ds = rioxarray.open_rasterio(
                fp,
                chunks={"x": cfg.dask_chunks[0], "y": cfg.dask_chunks[1]},
                masked=True,
            )
            datasets.append(ds)
            increment_step_progress(
                job_id,
                "merge_tiles",
                increment=1,
                message=f"Reading {state} {crop}",
            )
        if rio_merge_arrays:
            merged = rio_merge_arrays(datasets)
        else:
            merged = xr.combine_by_coords(datasets, combine_attrs="drop_conflicts")
        if "_FillValue" in merged.attrs:
            del merged.attrs["_FillValue"]
        if hasattr(merged, "data_vars"):
            for var in merged.data_vars:
                if "_FillValue" in merged[var].attrs:
                    del merged[var].attrs["_FillValue"]
        ensure_dir(os.path.dirname(output_path))

        def _compute_progress_ctx():
            if not hasattr(merged.data, "__dask_graph__"):
                return None
            try:
                dsk = merged.data.__dask_graph__()
                total = len(dsk)
                add_step_total(job_id, "merge_compute", total)
            except Exception:
                return None

            class _Callback(Callback):
                def _pretask(self, key, dsk, state):
                    if is_cancelled(job_id):
                        raise RuntimeError("Cancelled")

                def _posttask(self, key, result, dsk, state, id):
                    increment_step_progress(
                        job_id,
                        "merge_compute",
                        increment=1,
                        message=f"Computing {state} {crop}",
                    )

            return _Callback()

        cb = _compute_progress_ctx()
        if cb:
            with cb:
                merged.rio.to_raster(
                    output_path,
                    compress=cfg.compress,
                    BIGTIFF=cfg.bigtiff,
                    nodata=cfg.nodata_value,
                    tiled=True,
                    windowed=True,
                )
        else:
            merged.rio.to_raster(
                output_path,
                compress=cfg.compress,
                BIGTIFF=cfg.bigtiff,
                nodata=cfg.nodata_value,
                tiled=True,
                windowed=True,
            )
        merged.close()
        for ds in datasets:
            ds.close()
        gc.collect()
        elapsed = time.perf_counter() - started
        output_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        return (state, crop, True, "Success", elapsed, output_bytes, output_path)
    except Exception as exc:
        elapsed = time.perf_counter() - started
        output_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        return (state, crop, False, str(exc), elapsed, output_bytes, output_path)


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


def run_merge(
        output_root: str,
        year_suffix: str,
        country: str,
        crops: str,
        states: List[str],
        job_id: int,
        skip_exists: bool = True,
        workers: int = 4,
) -> None:
    input_base = os.path.join(output_root, "inference_tiles", year_suffix, country)
    output_base = os.path.join(output_root, "merged_cropmasks", year_suffix, country)
    if not os.path.exists(input_base):
        return
    crop_names = get_crop_list(crops)
    tasks = []
    for state in states:
        for crop in crop_names:
            state_crop_in_dir = os.path.join(input_base, state, crop)
            filename = f"{year_suffix}_{country}_{state}_{crop}.tif"
            state_crop_out_dir = os.path.join(output_base, state, crop)
            output_file_path = os.path.join(state_crop_out_dir, filename)
            cfg = vars(MergeConfig(skip_if_exists=skip_exists))
            cfg["job_id"] = job_id
            tasks.append((state, crop, state_crop_in_dir, output_file_path, cfg))
    set_progress(job_id, 0, len(tasks), "Starting merge")
    set_step_progress(job_id, "merge", 0, len(tasks), "Starting merge")
    set_step_progress(job_id, "merge_tiles", 0, 0, "Starting merge tiles")
    set_step_progress(job_id, "merge_compute", 0, 0, "Starting merge compute")

    def _iter_results() -> Iterable[Tuple[str, str, bool, str, float, int, str]]:
        if current_process().daemon:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(merge_task_worker, t) for t in tasks]
                for fut in as_completed(futures):
                    yield fut.result()
        else:
            ctx = get_context("spawn")
            with ctx.Pool(processes=workers) as pool:
                for res in pool.imap_unordered(merge_task_worker, tasks):
                    yield res

    append_log(job_id, "Merge started")
    failures = []
    with tqdm(total=len(tasks), desc="Merging Progress") as pbar:
        for res in _iter_results():
            state, crop, success, msg, elapsed, output_bytes, output_path = res
            increment_progress(job_id, increment=1, message=f"Merging {state} {crop}")
            increment_step_progress(job_id, "merge", increment=1, message=f"Merging {state} {crop}")
            append_csv_row(
                csv_path(job_id, "merge_states"),
                MERGE_CSV_HEADERS,
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "state": state,
                    "crop": crop,
                    "output_path": output_path,
                    "output_bytes": output_bytes,
                    "elapsed_sec": round(elapsed, 4),
                    "elapsed_hms": format_elapsed_hms(elapsed),
                    "status": "ok" if success else "failed",
                },
            )
            append_log(
                job_id,
                f"Merge {state}/{crop} status={msg} elapsed={elapsed:.2f}s output_bytes={output_bytes}",
            )
            if not success:
                append_log(job_id, format_error_message(f"merge {state}/{crop}", msg))
                failures.append(f"{state}/{crop}: {msg}")
            pbar.update(1)
    append_log(job_id, "Merge finished")
    if failures:
        raise RuntimeError(f"Merge failed for {len(failures)} task(s): " + "; ".join(failures[:5]))
