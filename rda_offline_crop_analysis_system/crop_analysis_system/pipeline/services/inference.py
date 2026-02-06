import math
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import time
from datetime import datetime
from dataclasses import dataclass, replace
from multiprocessing import current_process
from typing import Iterable, List, Tuple

import numpy as np
import torch
import torch.multiprocessing as mp
from osgeo import gdal
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
    format_error_with_trace,
)

torch.multiprocessing.set_start_method('spawn')
try:
    from TransUNet.networks.vit_seg_modeling import CONFIGS as CONFIGS_ViT_seg
    from TransUNet.networks.vit_seg_modeling import VisionTransformer as ViT_seg
except ImportError:
    import sys

    sys.path.append(os.getcwd())
    from TransUNet.networks.vit_seg_modeling import CONFIGS as CONFIGS_ViT_seg
    from TransUNet.networks.vit_seg_modeling import VisionTransformer as ViT_seg

gdal.UseExceptions()

INFERENCE_CSV_HEADERS = (
    "timestamp",
    "state",
    "tile",
    "input_bytes",
    "output_bytes",
    "elapsed_sec",
    "elapsed_hms",
    "status",
)


def _log_inference_tile(
        job_id: int,
        state_name: str,
        tile_name: str,
        input_path: str,
        output_paths: List[str],
        elapsed_sec: float,
        status: str,
) -> None:
    input_bytes = os.path.getsize(input_path) if os.path.exists(input_path) else 0
    output_bytes = 0
    for path in output_paths:
        if os.path.exists(path):
            output_bytes += os.path.getsize(path)
    append_csv_row(
        csv_path(job_id, "inference_tiles"),
        INFERENCE_CSV_HEADERS,
        {
            "timestamp": datetime.utcnow().isoformat(),
            "state": state_name,
            "tile": tile_name,
            "input_bytes": input_bytes,
            "output_bytes": output_bytes,
            "elapsed_sec": round(elapsed_sec, 4),
            "elapsed_hms": format_elapsed_hms(elapsed_sec),
            "status": status,
        },
    )
    append_log(
        job_id,
        f"Inference {status}: {state_name}/{tile_name} elapsed={elapsed_sec:.2f}s output_bytes={output_bytes}",
    )


@dataclass
class InferenceConfig:
    modelname: str = "TransUnet3"
    num_class: int = 3
    in_channels: int = 5
    vit_name: str = "R50-ViT-B_16"
    window_size: Tuple[int, int] = (224, 224)
    step: int = 112
    batch_size: int = 64
    band_indices: Tuple[int, ...] = (0, 1, 2, 3, 4)
    device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class CropSchema:
    _ALIASES = {
        "corn": {"corn", "maize"},
        "soy": {"soy", "soybean", "soybeans"},
        "spring_wheat": {"springwheat", "spring_wheat", "spring wheat", "swheat", "spring"},
        "winter_wheat": {"winterwheat", "winter_wheat", "winter wheat", "wwheat", "winter"},
    }
    _CROP_DISPLAY = {
        "corn": "Corn",
        "soy": "Soybean",
        "spring_wheat": "SpringWheat",
        "winter_wheat": "WinterWheat",
    }

    def __init__(self, crops: List[str]):
        self.crops = crops
        self.crop_to_class = {crop: i + 1 for i, crop in enumerate(crops)}
        self.num_class = 1 + len(crops)

    @staticmethod
    def parse(crops_str: str) -> "CropSchema":
        if not crops_str:
            raise ValueError("Crops input is empty.")
        raw = crops_str.lower().replace("\\", "/").replace(",", "/").replace(";", "/")
        tokens = [t.strip() for t in raw.split("/") if t.strip()]
        norm = []
        for token in tokens:
            canonical = None
            for key, alias_set in CropSchema._ALIASES.items():
                if token in alias_set:
                    canonical = key
                    break
            norm.append(canonical if canonical else token)
        return CropSchema(list(dict.fromkeys(norm)))

    def crop_display_name(self, crop: str) -> str:
        return self._CROP_DISPLAY.get(crop, crop)


def read_image_lazy(path: str) -> gdal.Dataset:
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise FileNotFoundError(f"GDAL open failed: {path}")
    return ds


def clip_normalize_to_uint16(data: np.ndarray) -> np.ndarray:
    lower, upper = np.percentile(data, 2.0), np.percentile(data, 98.0)
    denom = upper - lower or 1e-6
    data = np.clip((data - lower) / denom, 0, 1)
    return (data * 65535).astype(np.uint16)


def get_patch(
        ds: gdal.Dataset, band_indices: Tuple[int, ...], x: int, y: int, h: int, w: int
) -> np.ndarray:
    img_h, img_w = ds.RasterYSize, ds.RasterXSize
    num_bands = len(band_indices)
    x_valid, y_valid = max(0, x), max(0, y)
    x_end, y_end = min(x + h, img_h), min(y + w, img_w)
    read_h, read_w = x_end - x_valid, y_end - y_valid
    patch = np.zeros((num_bands, h, w), dtype=np.uint16)
    if read_h <= 0 or read_w <= 0:
        return patch
    for i, b in enumerate(band_indices):
        band = ds.GetRasterBand(b + 1)
        arr = band.ReadAsArray(y_valid, x_valid, read_w, read_h)
        if arr is not None:
            arr = clip_normalize_to_uint16(arr)
            p_x, p_y = x_valid - x, y_valid - y
            patch[i, p_x: p_x + read_h, p_y: p_y + read_w] = arr
    return patch


def sliding_window_coords(height: int, width: int, step: int, window_size: Tuple[int, int]):
    win_h, win_w = window_size
    if height <= win_h:
        x_coords = [0]
    else:
        x_coords = list(range(0, height - win_h + 1, step))
        if x_coords[-1] + win_h < height:
            x_coords.append(height - win_h)
    if width <= win_w:
        y_coords = [0]
    else:
        y_coords = list(range(0, width - win_w + 1, step))
        if y_coords[-1] + win_w < width:
            y_coords.append(width - win_w)
    for x in x_coords:
        for y in y_coords:
            yield x, y, win_h, win_w


def write_geotiff(path: str, data: np.ndarray, ref_ds: gdal.Dataset):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    driver = gdal.GetDriverByName("GTiff")
    out = driver.Create(
        path,
        ref_ds.RasterXSize,
        ref_ds.RasterYSize,
        1,
        gdal.GDT_Byte,
        options=["COMPRESS=DEFLATE"],
    )
    out.SetGeoTransform(ref_ds.GetGeoTransform())
    out.SetProjection(ref_ds.GetProjection())
    band = out.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(99)
    band.FlushCache()
    del out


class TileInferenceEngine:
    def __init__(self, cfg: InferenceConfig, weight_path: str):
        self.cfg = cfg
        self.device = cfg.device
        vit_cfg = CONFIGS_ViT_seg[cfg.vit_name]
        vit_cfg.n_classes = cfg.num_class
        vit_cfg.n_skip = 3
        vit_cfg.in_channels = cfg.in_channels
        vit_cfg.patches.grid = (cfg.window_size[0] // 16, cfg.window_size[1] // 16)
        self.net = ViT_seg(
            vit_cfg, img_size=cfg.window_size[0], num_classes=cfg.num_class
        ).to(self.device)
        self.net.load_state_dict(torch.load(weight_path, map_location=self.device, weights_only=True))
        self.net.eval()

    @torch.no_grad()
    def predict(self, ds: gdal.Dataset, desc: str, job_id: int | None = None) -> np.ndarray:
        h, w = ds.RasterYSize, ds.RasterXSize
        pred_accum = np.zeros((h, w, self.cfg.num_class), dtype=np.float32)
        coords = list(sliding_window_coords(h, w, self.cfg.step, self.cfg.window_size))
        if job_id:
            add_step_total(job_id, "inference_windows", len(coords))
        batch_size = self.cfg.batch_size
        chunks = [coords[i: i + batch_size] for i in range(0, len(coords), batch_size)]
        for batch in tqdm(chunks, desc=desc, leave=False):
            if job_id and is_cancelled(job_id):
                raise RuntimeError("Cancelled")
            patches = [get_patch(ds, self.cfg.band_indices, x, y, hh, ww) for x, y, hh, ww in batch]
            x_tensor = torch.from_numpy(np.array(patches)).float().to(self.device)
            logits, _ = self.net(x_tensor)
            probs = torch.nn.functional.softmax(logits, dim=1).cpu().numpy()
            for prob, (x, y, hh, ww) in zip(probs, batch):
                x_end, y_end = min(x + hh, h), min(y + ww, w)
                valid_h, valid_w = x_end - max(0, x), y_end - max(0, y)
                p_x, p_y = max(0, x) - x, max(0, y) - y
                i_x, i_y = max(0, x), max(0, y)
                if valid_h > 0 and valid_w > 0:
                    data = prob[:, p_x: p_x + valid_h, p_y: p_y + valid_w].transpose(1, 2, 0)
                    pred_accum[i_x: i_x + valid_h, i_y: i_y + valid_w] += data
            if job_id:
                increment_step_progress(
                    job_id,
                    "inference_windows",
                    increment=len(batch),
                    message=f"Windows {desc}",
                )
        return np.argmax(pred_accum, axis=-1).astype(np.uint8)


def _count_tiff_files(state_paths: Iterable[str]) -> int:
    total = 0
    for state_path in state_paths:
        total += len(
            [
                f
                for f in os.listdir(state_path)
                if f.lower().endswith((".tif", ".tiff"))
            ]
        )
    return total


def run_worker_process(
    rank: int,
    num_gpus: int,
    all_files: List[str],
    args,
    base_cfg: InferenceConfig,
    schema: CropSchema,
    output_root: str,
    state_name: str,
    job_id: int,
):
    total_files = len(all_files)
    chunk_size = math.ceil(total_files / num_gpus)
    start_idx = rank * chunk_size
    end_idx = min(start_idx + chunk_size, total_files)
    my_files = all_files[start_idx:end_idx]
    if not my_files:
        return
    gpu_id = rank
    device = torch.device(f"cuda:{gpu_id}")
    local_cfg = replace(base_cfg, device=device)
    try:
        engine = TileInferenceEngine(local_cfg, args["weights"])
    except Exception:
        return
    for in_fp in tqdm(
        my_files,
        desc=f"Inference {state_name} GPU {gpu_id}",
        unit="tile",
        leave=False,
    ):
        if is_cancelled(job_id):
            return
        fname = os.path.basename(in_fp)
        if args["skip_exists"]:
            all_outputs_exist = True
            for crop in schema.crops:
                save_dir = os.path.join(
                    output_root,
                    "inference_tiles",
                    args["year_suffix"],
                    args["country"],
                    state_name,
                    schema.crop_display_name(crop),
                )
                if not os.path.exists(os.path.join(save_dir, fname)):
                    all_outputs_exist = False
                    break
            if all_outputs_exist:
                increment_progress(job_id, increment=1, message=f"Skipping {state_name}")
                increment_step_progress(
                    job_id, "inference", increment=1, message=f"Skipping {state_name}"
                )
                _log_inference_tile(
                    job_id,
                    state_name,
                    fname,
                    in_fp,
                    [],
                    0.0,
                    "skipped",
                )
                continue
        try:
            started = time.perf_counter()
            ds = read_image_lazy(in_fp)
            pred = engine.predict(ds, desc=f"[GPU {gpu_id}] {fname}", job_id=job_id)
            output_paths = []
            for crop in schema.crops:
                class_id = schema.crop_to_class[crop]
                mask = (pred == class_id).astype(np.uint8)
                save_dir = os.path.join(
                    output_root,
                    "inference_tiles",
                    args["year_suffix"],
                    args["country"],
                    state_name,
                    schema.crop_display_name(crop),
                )
                save_path = os.path.join(save_dir, fname)
                write_geotiff(save_path, mask, ds)
                output_paths.append(save_path)
            del ds
            elapsed = time.perf_counter() - started
            _log_inference_tile(
                job_id,
                state_name,
                fname,
                in_fp,
                output_paths,
                elapsed,
                "ok",
            )
        except Exception as exc:
            if is_cancelled(job_id):
                return
            append_log(job_id, format_error_with_trace(f"inference {state_name}/{fname}", exc))
            raise
        increment_progress(job_id, increment=1, message=f"Processing {state_name}")
        increment_step_progress(
            job_id, "inference", increment=1, message=f"Processing {state_name}"
        )


def run_state_inference(
    state_path: str,
    output_root: str,
    args,
    cfg,
    schema,
    job_id: int,
    desired_gpus: int = 0,
):
    state_name = os.path.basename(state_path)
    input_files = sorted(
        [
            os.path.join(state_path, f)
            for f in os.listdir(state_path)
            if f.lower().endswith((".tif", ".tiff"))
        ]
    )
    if not input_files:
        return
    num_gpus = desired_gpus
    if num_gpus > 1 and not current_process().daemon:
        mp.spawn(
            run_worker_process,
            nprocs=num_gpus,
            args=(num_gpus, input_files, args, cfg, schema, output_root, state_name, job_id),
            join=True,
        )
    else:
        engine = TileInferenceEngine(cfg, args["weights"])
        for in_fp in tqdm(input_files, desc=f"Inference {state_name}", unit="tile"):
            if is_cancelled(job_id):
                return
            fname = os.path.basename(in_fp)
            if args["skip_exists"]:
                all_outputs_exist = True
                for crop in schema.crops:
                    save_dir = os.path.join(
                        output_root,
                        "inference_tiles",
                        args["year_suffix"],
                        args["country"],
                        state_name,
                        schema.crop_display_name(crop),
                    )
                    if not os.path.exists(os.path.join(save_dir, fname)):
                        all_outputs_exist = False
                        break
                if all_outputs_exist:
                    increment_progress(job_id, increment=1, message=f"Skipping {state_name}")
                    increment_step_progress(
                        job_id, "inference", increment=1, message=f"Skipping {state_name}"
                    )
                    _log_inference_tile(
                        job_id,
                        state_name,
                        fname,
                        in_fp,
                        [],
                        0.0,
                        "skipped",
                    )
                    continue
            try:
                started = time.perf_counter()
                ds = read_image_lazy(in_fp)
                pred = engine.predict(ds, desc=f"{fname}", job_id=job_id)
                output_paths = []
                for crop in schema.crops:
                    class_id = schema.crop_to_class[crop]
                    mask = (pred == class_id).astype(np.uint8)
                    save_dir = os.path.join(
                        output_root,
                        "inference_tiles",
                        args["year_suffix"],
                        args["country"],
                        state_name,
                        schema.crop_display_name(crop),
                    )
                    save_path = os.path.join(save_dir, fname)
                    write_geotiff(save_path, mask, ds)
                    output_paths.append(save_path)
                del ds
                elapsed = time.perf_counter() - started
                _log_inference_tile(
                    job_id,
                    state_name,
                    fname,
                    in_fp,
                    output_paths,
                    elapsed,
                    "ok",
                )
            except Exception as exc:
                if is_cancelled(job_id):
                    return
                append_log(job_id, format_error_with_trace(f"inference {state_name}/{fname}", exc))
                raise
            increment_progress(job_id, increment=1, message=f"Processing {state_name}")
            increment_step_progress(
                job_id, "inference", increment=1, message=f"Processing {state_name}"
            )


def run_inference(
    input_root: str,
    output_root: str,
    year_suffix: str,
    country: str,
    crops: str,
    states: List[str],
    weights: str,
    batch_size: int,
    job_id: int,
    gpu_count: int = 0,
    skip_exists: bool = False,
) -> None:
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass
    schema = CropSchema.parse(crops)
    cfg = InferenceConfig(num_class=schema.num_class, batch_size=batch_size)
    base_input_dir = os.path.join(input_root, country, year_suffix)
    all_states_paths = sorted(
        [
            os.path.join(base_input_dir, d)
            for d in os.listdir(base_input_dir)
            if os.path.isdir(os.path.join(base_input_dir, d))
        ]
    )
    target_states = []
    for state in states:
        for path in all_states_paths:
            if os.path.basename(path) == state:
                target_states.append(path)
                break
    if not target_states:
        return
    total_tiles = _count_tiff_files(target_states)
    set_progress(job_id, 0, total_tiles, "Starting inference")
    set_step_progress(job_id, "inference", 0, total_tiles, "Starting inference")
    set_step_progress(job_id, "inference_windows", 0, 0, "Starting windows")
    args = {
        "year_suffix": year_suffix,
        "country": country,
        "weights": weights,
        "skip_exists": skip_exists,
    }
    append_log(job_id, "Inference started")
    gpu_count = gpu_count if gpu_count is not None else 0
    available_gpus = torch.cuda.device_count()

    if gpu_count == -1:
        desired_gpus = available_gpus
    elif gpu_count == 0:
        desired_gpus = 0
    else:  # gpu_count > 0
        if available_gpus > 0:
            desired_gpus = min(gpu_count, available_gpus)
        else:
            desired_gpus = 0
    
    if desired_gpus == 0:
        cfg = replace(cfg, device=torch.device("cpu"))

    for state_path in tqdm(target_states, desc="Inference States", unit="state"):
        run_state_inference(state_path, output_root, args, cfg, schema, job_id, desired_gpus)
    append_log(job_id, "Inference finished")
