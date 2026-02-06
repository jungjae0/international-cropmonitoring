import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

from django.utils import timezone

from core.models import Job, JobOutput


def _parse_crop_list(crops_str: str) -> list[str]:
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
    final_list: list[str] = []
    for item in raw_list:
        if item in alias_map:
            val = alias_map[item]
            if val not in final_list:
                final_list.append(val)
        else:
            cap = item.capitalize()
            if cap not in final_list:
                final_list.append(cap)
    return final_list


def output_belongs_to_job(job: Job, step: str, file_path: Path, base_dir: Path) -> bool:
    input_meta = job.input_path or {}
    year_suffix = str(input_meta.get("year_suffix", "")).strip()
    country = str(input_meta.get("country", "")).strip()
    if not year_suffix or not country:
        return False
    states = set(job.selected_states or [])
    crops = set(_parse_crop_list(job.target_crops or ""))
    try:
        rel_parts = file_path.relative_to(base_dir).parts
    except ValueError:
        return False

    if step in (JobOutput.STEP_INFERENCE, JobOutput.STEP_MERGE):
        if len(rel_parts) < 5:
            return False
        if rel_parts[0] != year_suffix or rel_parts[1] != country:
            return False
        if states and rel_parts[2] not in states:
            return False
        if crops and rel_parts[3] not in crops:
            return False
        return True

    if step == JobOutput.STEP_AREA:
        if not file_path.name.endswith(".csv"):
            return False
        prefix = f"{year_suffix}_{country}_"
        if not file_path.stem.startswith(prefix):
            return False
        crop = file_path.stem[len(prefix) :]
        if crops and crop not in crops:
            return False
        return True

    return True


def _iter_files(base_dir: Path) -> Iterable[Path]:
    for root, _, files in os.walk(base_dir):
        for filename in files:
            yield Path(root) / filename


def sync_job_outputs(job: Job, step: str, base_dir: Path) -> None:
    if not base_dir.exists():
        return
    for file_path in _iter_files(base_dir):
        if not output_belongs_to_job(job, step, file_path, base_dir):
            continue
        try:
            stat = file_path.stat()
        except OSError:
            continue
        modified_at = datetime.fromtimestamp(stat.st_mtime)
        if timezone.is_naive(modified_at):
            modified_at = timezone.make_aware(modified_at)
        relative_path = str(file_path.relative_to(base_dir))
        JobOutput.objects.update_or_create(
            job=job,
            absolute_path=str(file_path),
            defaults={
                "step": step,
                "relative_path": relative_path,
                "size_bytes": stat.st_size,
                "file_modified_at": modified_at,
            },
        )
