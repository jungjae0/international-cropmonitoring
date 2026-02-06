import shutil
import subprocess
from typing import List
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'


def _parse_nvidia_smi(lines: List[str], memory_threshold_mb: int) -> List[int]:
    available = []
    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            idx = int(parts[0])
            util = int(parts[1])
            mem_used = int(parts[2])
        except ValueError:
            continue
        if util == 0 and mem_used <= memory_threshold_mb:
            available.append(idx)
    return available


def get_available_gpu_ids(memory_threshold_mb: int = 200) -> List[int]:
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,utilization.gpu,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            ids = _parse_nvidia_smi(lines, memory_threshold_mb)
            if ids:
                return ids
        except Exception:
            pass
    try:
        import torch
    except Exception:
        return []

    count = torch.cuda.device_count()
    return list(range(count))


def get_available_gpu_count() -> int:
    return len(get_available_gpu_ids())
