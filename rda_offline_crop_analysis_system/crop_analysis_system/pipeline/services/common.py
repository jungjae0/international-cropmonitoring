from dataclasses import dataclass
from pathlib import Path
from typing import List

from django.conf import settings

from core.utils.app_settings import get_input_root, get_output_root


@dataclass
class PipelineInput:
    year_suffix: str
    country: str
    states: List[str]
    crops: str
    output_name: str
    weights_path: str
    batch_size: int
    shapefile_path: str
    skip_exists: bool = False


def build_input_base(input_root: Path, country: str, year_suffix: str) -> Path:
    return input_root / country / year_suffix


def build_output_root(output_root: Path, output_name: str) -> Path:
    return output_root / output_name


def ensure_output_structure(output_root: Path) -> None:
    (output_root / "inference_tiles").mkdir(parents=True, exist_ok=True)
    (output_root / "merged_cropmasks").mkdir(parents=True, exist_ok=True)
    (output_root / "calculate_area").mkdir(parents=True, exist_ok=True)


def validate_input_paths(input_root: Path, year_suffix: str, country: str, states: List[str]) -> None:
    base = build_input_base(input_root, country, year_suffix)
    if not base.exists():
        raise FileNotFoundError(f"Input base not found: {base}")
    missing = [state for state in states if not (base / state).exists()]
    if missing:
        raise FileNotFoundError(f"Missing states: {', '.join(missing)}")


def default_input_root() -> Path:
    return get_input_root()


def default_output_root() -> Path:
    return get_output_root()
