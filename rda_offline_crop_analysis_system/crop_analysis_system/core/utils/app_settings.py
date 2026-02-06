from pathlib import Path
from typing import Optional

from django.conf import settings

from core.utils.django_setup import ensure_django_setup


def get_root_by_type(path_type: str) -> Optional[Path]:
    ensure_django_setup()
    from core.models import RootPath

    row = RootPath.objects.filter(path_type=path_type, is_active=True).order_by("-updated_at").first()
    if row and row.path:
        path = Path(row.path)
        if path.is_absolute():
            return path
        base_dir = getattr(settings, "MEDIA_ROOT", settings.BASE_DIR)
        return (base_dir / path).resolve()
    return None


def get_input_root() -> Path:
    from core.models import RootPath

    path = get_root_by_type(RootPath.TYPE_INPUT)
    return path or settings.DATA_INPUT_DIR


def get_output_root() -> Path:
    from core.models import RootPath

    path = get_root_by_type(RootPath.TYPE_OUTPUT)
    return path or settings.DATA_OUTPUT_DIR


def get_logs_root() -> Path:
    from core.models import RootPath

    path = get_root_by_type(RootPath.TYPE_LOGS)
    return path or settings.DATA_LOG_DIR


def resolve_root_path(path_value: str, root_type: str) -> Path:
    if not path_value:
        return Path()
    path = Path(path_value)
    if path.is_absolute():
        return path
    root = get_root_by_type(root_type)
    if root:
        return (root / path).resolve()
    base_dir = getattr(settings, "MEDIA_ROOT", settings.BASE_DIR)
    return (base_dir / path).resolve()
