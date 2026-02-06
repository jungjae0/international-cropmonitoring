import os
from django.conf import settings
from .tasks import generate_tiles, process_job_chain

def resolve_existing_result(job):
    base_path = os.path.join(
        settings.MEDIA_ROOT,
        job.crop_type,
        job.region,
        str(job.year)
    )
    tif_path = os.path.join(base_path, "cropmapping.tif")
    tile_path = os.path.join(base_path, "tiles")

    tif_exists = os.path.isfile(tif_path)
    tile_exists = os.path.isdir(tile_path) and any(os.listdir(tile_path))

    if tif_exists and tile_exists:
        job.status = 'done'
        job.current_step = 'finished'
        job.progress = 100
        job.tif_file.name = os.path.relpath(tif_path, settings.MEDIA_ROOT)
        job.save()
    elif tif_exists:
        job.tif_file.name = os.path.relpath(tif_path, settings.MEDIA_ROOT)
        job.status = 'running'
        job.current_step = 'generating_tiles'
        job.progress = 90
        job.save()
        generate_tiles.delay(job.id)
    else:
        process_job_chain(job.id)
