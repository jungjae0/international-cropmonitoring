from typing import Optional

from django.utils import timezone

from core.models import Job
from core.utils.log_files import append_log


def has_running_job(exclude_job_id: Optional[int] = None) -> bool:
    qs = Job.objects.filter(status=Job.STATUS_RUNNING)
    if exclude_job_id is not None:
        qs = qs.exclude(id=exclude_job_id)
    return qs.exists()


def schedule_job(job: Job) -> None:
    from pipeline.tasks import workflow_task

    eta = None
    if job.schedule_at and job.schedule_at > timezone.now():
        eta = job.schedule_at
    if eta:
        result = workflow_task.apply_async(args=[job.id], eta=eta)
    else:
        result = workflow_task.apply_async(args=[job.id])
    job.celery_task_id = result.id or job.celery_task_id
    job.save(update_fields=["celery_task_id", "updated_at"])


def queue_or_start(job: Job) -> bool:
    if has_running_job():
        job.status = Job.STATUS_PENDING
        job.save(update_fields=["status", "updated_at"])
        append_log(job.id, "Queued (waiting for running job to finish)")
        return False
    schedule_job(job)
    return True


def start_next_pending_job() -> Optional[int]:
    if has_running_job():
        return None
    next_job = Job.objects.filter(status=Job.STATUS_PENDING).order_by("created_at").first()
    if not next_job:
        return None
    schedule_job(next_job)
    append_log(next_job.id, "Queued (auto-started after previous job finished)")
    return next_job.id
