import argparse
from pathlib import Path

import numpy as np
import rasterio

from pipeline.services.thumbnail import create_thumbnail


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a PNG thumbnail from a GeoTIFF and print bounds."
    )
    parser.add_argument("tiff_path", help="Path to input GeoTIFF (.tif)")
    parser.add_argument("output_path", help="Path to output PNG file")
    parser.add_argument(
        "--size",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=(1024, 1024),
        help="Thumbnail max size (default: 1024 1024)",
    )
    parser.add_argument(
        "--class-value",
        type=int,
        default=1,
        help="Class value to render (default: 1)",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Print value distribution and class ratio before rendering",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tiff_path = Path(args.tiff_path)
    output_path = Path(args.output_path)

    if args.diagnose:
        with rasterio.open(tiff_path) as src:
            data = src.read(1, masked=False)
            unique_vals, counts = np.unique(data, return_counts=True)
            total = int(counts.sum())
            class_count = int(counts[unique_vals == args.class_value].sum())
            class_ratio = (class_count / total * 100.0) if total > 0 else 0.0

            if unique_vals.size <= 50:
                pairs = ", ".join(
                    f"{int(v)}:{int(c)}" for v, c in zip(unique_vals, counts)
                )
                print("Value counts:", pairs)
            else:
                print(
                    "Value summary:",
                    f"min={int(unique_vals.min())}",
                    f"max={int(unique_vals.max())}",
                    f"unique={int(unique_vals.size)}",
                )

            print(
                f"Class {args.class_value} ratio: {class_ratio:.2f}% "
                f"({class_count}/{total})"
            )

    bounds = create_thumbnail(
        str(tiff_path),
        str(output_path),
        thumbnail_size=(args.size[0], args.size[1]),
        class_value=args.class_value,
    )
    print("Bounds (Leaflet imageOverlay):", bounds)
    print("Saved:", output_path)


if __name__ == "__main__":
    main()
