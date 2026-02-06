from celery import chain, shared_task
from pathlib import Path
from django.conf import settings
from django.utils import timezone

from core.models import Job, JobOutput
from core.utils.app_settings import get_input_root, get_output_root, resolve_root_path
from core.utils.log_files import append_log, format_error_with_trace
from core.utils.redis_client import (
    is_cancelled,
    set_cancel,
    set_progress,
    set_step_progress,
)
from core.utils.output_tracker import sync_job_outputs
from core.utils.job_queue import start_next_pending_job
from pipeline.services.area_calc import run_area_calc
from pipeline.services.common import ensure_output_structure, validate_input_paths
from pipeline.services.inference import run_inference
from pipeline.services.merge import run_merge
from pipeline.services.thumbnail import create_thumbnail


def _get_job(job_id: int) -> Job:
    return Job.objects.select_related("pipeline_config").get(id=job_id)


def _update_job_status(job: Job, status: str, percent: int, current_step: str = None) -> None:
    job.status = status
    job.progress_percent = percent
    update_fields = ["status", "progress_percent", "updated_at"]
    if current_step is not None:
        job.current_step = current_step
        update_fields.append("current_step")
    job.save(update_fields=update_fields)

def _update_celery_state(job: Job, state: str, error: str = "") -> None:
    job.celery_last_state = state
    job.celery_error = error
    job.save(update_fields=["celery_last_state", "celery_error", "updated_at"])

def _get_output_root(job: Job) -> Path:
    if job.output_path:
        return Path(job.output_path)
    base_output_root = get_output_root()
    output_root = base_output_root / job.output_dir_name if job.output_dir_name else base_output_root
    job.output_path = str(output_root)
    job.save(update_fields=["output_path", "updated_at"])
    return output_root


@shared_task(bind=True)
def workflow_task(self, job_id: int):
    job = _get_job(job_id)
    try:
        if not job.celery_task_id:
            job.celery_task_id = self.request.id or ""
            job.save(update_fields=["celery_task_id", "updated_at"])
        set_cancel(job.id, False)
        input_meta = job.input_path
        year_suffix = input_meta.get("year_suffix")
        country = input_meta.get("country")
        states = job.selected_states
        input_root = get_input_root()
        output_root = _get_output_root(job)
        validate_input_paths(input_root, year_suffix, country, states)
        ensure_output_structure(output_root)
        _update_job_status(job, Job.STATUS_RUNNING, 0)
        _update_celery_state(job, "RUNNING")
        set_progress(job.id, 0, 0, "Queued")
        append_log(job.id, "Workflow queued")
        flow = chain(
            inference_task.s(job_id),
            merge_task.s(),
            area_task.s(),
            thumbnail_task.s(),
        )
        result = flow.apply_async()
        job.celery_chain_id = result.id or ""
        job.save(update_fields=["celery_chain_id", "updated_at"])
        return result.id
    except Exception as exc:
        _update_celery_state(job, "FAILURE", str(exc))
        _update_job_status(job, Job.STATUS_FAILED, job.progress_percent)
        message = format_error_with_trace("workflow task", exc)
        set_step_progress(job.id, "workflow", 0, 0, message)
        append_log(job.id, message)
        start_next_pending_job()
        raise


@shared_task(bind=True)
def inference_task(self, job_id: int):
    job = _get_job(job_id)
    job.celery_task_id = self.request.id or job.celery_task_id
    job.save(update_fields=["celery_task_id", "updated_at"])
    if is_cancelled(job_id):
        _update_job_status(job, Job.STATUS_CANCELLED, job.progress_percent)
        append_log(job.id, "Inference cancelled")
        start_next_pending_job()
        return job_id
    _update_celery_state(job, "RUNNING")
    job.current_step = "inference"
    job.save(update_fields=["celery_task_id", "current_step", "updated_at"])
    append_log(job.id, "Inference task started")
    if not job.pipeline_config:
        _update_celery_state(job, "FAILURE", "PipelineConfig is required for inference.")
        _update_job_status(job, Job.STATUS_FAILED, job.progress_percent)
        raise ValueError("PipelineConfig is required for inference.")
    input_meta = job.input_path
    try:
        input_root = get_input_root()
        output_root = _get_output_root(job)
        run_inference(
            input_root=str(input_root),
            output_root=str(output_root),
            year_suffix=input_meta.get("year_suffix"),
            country=input_meta.get("country"),
            crops=job.target_crops,
            states=job.selected_states,
            weights=str(
                resolve_root_path(job.pipeline_config.model_weights_path, "weights")
            ),
            batch_size=job.pipeline_config.batch_size,
            job_id=job.id,
            gpu_count=job.gpu_count,
            skip_exists=job.skip_inference,
        )
        sync_job_outputs(
            job,
            JobOutput.STEP_INFERENCE,
            output_root / "inference_tiles",
        )
    except Exception as exc:
        _update_celery_state(job, "FAILURE", str(exc))
        _update_job_status(job, Job.STATUS_FAILED, job.progress_percent)
        message = format_error_with_trace("inference task", exc)
        set_step_progress(job.id, "inference", 0, 0, message)
        append_log(job.id, message)
        start_next_pending_job()
        raise
    _update_job_status(job, Job.STATUS_RUNNING, 25, current_step="inference")
    append_log(job.id, "Inference task completed")
    return job_id


@shared_task(bind=True)
def merge_task(self, job_id: int):
    job = _get_job(job_id)
    job.celery_task_id = self.request.id or job.celery_task_id
    job.save(update_fields=["celery_task_id", "updated_at"])
    if is_cancelled(job_id):
        _update_job_status(job, Job.STATUS_CANCELLED, job.progress_percent)
        append_log(job.id, "Merge cancelled")
        start_next_pending_job()
        return job_id
    job.current_step = "merge"
    job.save(update_fields=["celery_task_id", "current_step", "updated_at"])
    append_log(job.id, "Merge task started")
    input_meta = job.input_path
    try:
        output_root = _get_output_root(job)
        run_merge(
            output_root=str(output_root),
            year_suffix=input_meta.get("year_suffix"),
            country=input_meta.get("country"),
            crops=job.target_crops,
            states=job.selected_states,
            job_id=job.id,
            skip_exists=job.skip_merge,
            workers=4,
        )
        sync_job_outputs(
            job,
            JobOutput.STEP_MERGE,
            output_root / "merged_cropmasks",
        )
    except Exception as exc:
        _update_celery_state(job, "FAILURE", str(exc))
        _update_job_status(job, Job.STATUS_FAILED, job.progress_percent)
        message = format_error_with_trace("merge task", exc)
        set_step_progress(job.id, "merge", 0, 0, message)
        append_log(job.id, message)
        start_next_pending_job()
        raise
    _update_job_status(job, Job.STATUS_RUNNING, 50, current_step="merge")
    append_log(job.id, "Merge task completed")
    return job_id


@shared_task(bind=True)
def area_task(self, job_id: int):
    job = _get_job(job_id)
    job.celery_task_id = self.request.id or job.celery_task_id
    job.save(update_fields=["celery_task_id", "updated_at"])
    if is_cancelled(job_id):
        _update_job_status(job, Job.STATUS_CANCELLED, job.progress_percent)
        append_log(job.id, "Area calculation cancelled")
        start_next_pending_job()
        return job_id
    job.current_step = "area"
    job.save(update_fields=["celery_task_id", "current_step", "updated_at"])
    append_log(job.id, "Area calculation task started")
    if not job.pipeline_config:
        _update_celery_state(job, "FAILURE", "PipelineConfig is required for area calculation.")
        _update_job_status(job, Job.STATUS_FAILED, job.progress_percent)
        raise ValueError("PipelineConfig is required for area calculation.")
    input_meta = job.input_path
    try:
        output_root = _get_output_root(job)
        run_area_calc(
            output_root=str(output_root),
            year_suffix=input_meta.get("year_suffix"),
            country=input_meta.get("country"),
            crops=job.target_crops,
            states=job.selected_states,
            shapefile_path=str(
                resolve_root_path(job.pipeline_config.shapefile_path, "shp")
            ),
            job_id=job.id,
            skip_exists=job.skip_area,
            workers=4,
        )
        sync_job_outputs(
            job,
            JobOutput.STEP_AREA,
            output_root / "calculate_area",
        )
    except Exception as exc:
        _update_celery_state(job, "FAILURE", str(exc))
        _update_job_status(job, Job.STATUS_FAILED, job.progress_percent)
        message = format_error_with_trace("area task", exc)
        set_step_progress(job.id, "area", 0, 0, message)
        append_log(job.id, message)
        start_next_pending_job()
        raise
    _update_job_status(job, Job.STATUS_RUNNING, 75, current_step="area")
    append_log(job.id, "Area calculation completed")
    return job_id


@shared_task(bind=True)
def thumbnail_task(self, job_id: int):
    job = _get_job(job_id)
    job.celery_task_id = self.request.id or job.celery_task_id
    job.save(update_fields=["celery_task_id", "updated_at"])
    if is_cancelled(job_id):
        _update_job_status(job, Job.STATUS_CANCELLED, job.progress_percent)
        append_log(job.id, "Thumbnail generation cancelled")
        start_next_pending_job()
        return job_id

    job.current_step = "thumbnail"
    job.save(update_fields=["celery_task_id", "current_step", "updated_at"])
    append_log(job.id, "Thumbnail generation task started")

    merged_outputs = JobOutput.objects.filter(job=job, step=JobOutput.STEP_MERGE)
    output_root = _get_output_root(job)
    thumbnail_dir = output_root / JobOutput.STEP_THUMBNAIL

    try:
        for merged_output in merged_outputs:
            if is_cancelled(job_id):
                break
            
            tiff_path = Path(merged_output.absolute_path)
            if not tiff_path.exists():
                continue

            png_relative_path = Path(merged_output.relative_path).with_suffix(".png")
            png_path = thumbnail_dir / png_relative_path
            
            bounds = create_thumbnail(str(tiff_path), str(png_path))

            JobOutput.objects.update_or_create(
                job=job,
                step=JobOutput.STEP_THUMBNAIL,
                relative_path=str(png_relative_path),
                defaults={
                    "absolute_path": str(png_path),
                    "bounds": bounds,
                    "size_bytes": png_path.stat().st_size if png_path.exists() else 0,
                    "file_modified_at": timezone.now(),
                },
            )
            append_log(job.id, f"Generated thumbnail for {tiff_path.name}")

    except Exception as exc:
        _update_celery_state(job, "FAILURE", str(exc))
        _update_job_status(job, Job.STATUS_FAILED, job.progress_percent)
        message = format_error_with_trace("thumbnail task", exc)
        append_log(job.id, message)
        start_next_pending_job()
        raise

    _update_job_status(job, Job.STATUS_SUCCESS, 100, current_step="")
    _update_celery_state(job, "SUCCESS")
    append_log(job.id, "Thumbnail generation completed")
    start_next_pending_job()
    return job_id
