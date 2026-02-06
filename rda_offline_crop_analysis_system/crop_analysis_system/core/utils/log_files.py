import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from core.utils.app_settings import get_logs_root
from core.utils.django_setup import ensure_django_setup


def ensure_logs_root() -> Path:
    ensure_django_setup()
    root = get_logs_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def log_path(job_id: int) -> Path:
    return ensure_logs_root() / f"{job_id}.log"


def csv_path(job_id: int, suffix: str) -> Path:
    return ensure_logs_root() / f"{job_id}_{suffix}.csv"


def generate_progress_bar(percent: int, bar_length: int = 20) -> str:
    """Generates a text-based progress bar."""
    filled = int(bar_length * percent / 100)
    bar = '=' * filled + '>' + ' ' * (bar_length - filled - 1)
    return f"[{bar}] {percent}%"


def append_log(job_id: int, message: str, percent: Optional[int] = None) -> None:
    ensure_django_setup()
    path = log_path(job_id)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    if percent is not None:
        progress_bar = generate_progress_bar(percent)
        line = f"[{timestamp} UTC] {progress_bar} {message}\n"
    else:
        line = f"[{timestamp} UTC] {message}\n"
        
    with open(path, "a", encoding="utf-8", newline="") as handle:
        handle.write(line)


def format_error(context: str, exc: Exception) -> str:
    return f"ERROR | {context} | {exc.__class__.__name__}: {exc}"


def format_error_message(context: str, message: str) -> str:
    return f"ERROR | {context} | {message}"


def format_error_with_trace(context: str, exc: Exception, limit: int = 3) -> str:
    import traceback

    base = format_error(context, exc)
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=limit))
    trace = trace.strip().replace("\n", " | ")
    return f"{base} | trace: {trace}"


def append_csv_row(path: Path, headers: Sequence[str], row: Mapping[str, object]) -> None:
    ensure_django_setup()
    os.makedirs(path.parent, exist_ok=True)
    write_header = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        if write_header:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in headers})


def format_elapsed_hms(elapsed_sec: float) -> str:
    seconds = max(0, int(round(elapsed_sec)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
