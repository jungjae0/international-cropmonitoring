import os
from pathlib import Path
from typing import List


def list_level1(base_dir: Path) -> List[str]:
    if not base_dir.exists():
        return []
    with os.scandir(base_dir) as entries:
        return sorted([entry.name for entry in entries if entry.is_dir()])


def list_level2(base_dir: Path, country: str) -> List[str]:
    target_dir = base_dir / country
    if not target_dir.exists():
        return []
    with os.scandir(target_dir) as entries:
        return sorted([entry.name for entry in entries if entry.is_dir()])


def list_level3(base_dir: Path, country: str, year_suffix: str) -> List[str]:
    target_dir = base_dir / country / year_suffix
    if not target_dir.exists():
        return []
    with os.scandir(target_dir) as entries:
        return sorted([entry.name for entry in entries if entry.is_dir()])
