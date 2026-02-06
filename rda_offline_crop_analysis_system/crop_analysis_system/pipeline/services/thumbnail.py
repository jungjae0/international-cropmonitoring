import os
from typing import List, Tuple

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds


def get_wgs84_bounds(src: rasterio.DatasetReader) -> List[List[float]]:
    """
    Get the bounding box of a raster in WGS84 (EPSG:4326) coordinates.

    Args:
        src: The rasterio dataset reader.

    Returns:
        A list of [lat, lon] pairs representing the bounding box corners.
        Specifically: [[north, west], [south, east]] for Leaflet's imageOverlay.
    """
    bounds = src.bounds
    wgs84_bounds = transform_bounds(src.crs, "EPSG:4326", *bounds)
    # Leaflet needs [[north, west], [south, east]] which is [[lat, lon], [lat, lon]]
    return [[wgs84_bounds[3], wgs84_bounds[0]], [wgs84_bounds[1], wgs84_bounds[2]]]


def create_thumbnail(
    tiff_path: str,
    output_path: str,
    thumbnail_size: Tuple[int, int] = (1024, 1024),
    class_value: int = 1,
) -> List[List[float]]:
    """
    Create a low-resolution PNG thumbnail from a GeoTIFF.

    Notes:
        - Preserves aspect ratio (fits within thumbnail_size).
        - Uses nodata/mask for transparency (does NOT assume value 0 is nodata).
        - Uses nearest resampling by default (safer for masks/classes).

    Args:
        tiff_path: Path to the input GeoTIFF file.
        output_path: Path to save the output PNG thumbnail.
        thumbnail_size: The maximum dimensions (width, height) of the thumbnail.

    Returns:
        The geographic bounds of the raster in WGS84 format.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with rasterio.open(tiff_path) as src:
        # Get bounds in WGS84
        bounds = get_wgs84_bounds(src)

        # Preserve aspect ratio while fitting within thumbnail_size
        max_w, max_h = thumbnail_size
        scale = min(max_w / src.width, max_h / src.height)
        out_w = max(1, int(round(src.width * scale)))
        out_h = max(1, int(round(src.height * scale)))

        # Read as plain array to avoid dataset masks shrinking the visible area
        # Nearest is safer for masks/classes (avoid mixing labels like bilinear does)
        data = src.read(
            1,
            out_shape=(out_h, out_w),
            resampling=Resampling.nearest,
            masked=False,
        )

        # Show only the requested class value; everything else is transparent
        valid = data == class_value

        # Optional: normalize valid data to 0-255 (kept similar to original intent)
        arr = np.array(data, dtype=np.float32)
        if np.any(valid):
            v = arr[valid]
            vmin = float(np.min(v))
            vmax = float(np.max(v))
            if vmax > vmin:
                arr = (arr - vmin) / (vmax - vmin) * 255.0
            else:
                arr = np.zeros(arr.shape, dtype=np.float32)
        else:
            arr = np.zeros(arr.shape, dtype=np.float32)

        arr8 = np.clip(arr, 0, 255).astype(np.uint8)

        # Build RGBA output:
        # - background -> transparent
        # - valid pixels -> Blue with some transparency
        rgba = np.zeros((out_h, out_w, 4), dtype=np.uint8)
        rgba[valid] = (30, 144, 255, 150)  # DodgerBlue with alpha

        # Use Pillow to create a PNG image
        img = Image.fromarray(rgba, "RGBA")
        img.save(output_path, "PNG")

    return bounds
