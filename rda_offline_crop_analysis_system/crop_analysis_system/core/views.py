import json
from datetime import datetime
from typing import Any, Dict, Tuple
import tempfile
import zipfile

from django.conf import settings
from celery import current_app
from celery.result import AsyncResult
from django.http import FileResponse, JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from pathlib import Path
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import Country, Job, JobOutput, PipelineConfig, RootPath
from core.utils.file_manager import list_level1, list_level2, list_level3
from core.utils.redis_client import get_all_progress, reset_progress, set_cancel
from core.utils.output_tracker import output_belongs_to_job
from core.utils.app_settings import (
    get_input_root,
    get_logs_root,
    get_output_root,
    get_root_by_type,
)
from core.utils.gpu import get_available_gpu_count
from core.utils.job_queue import queue_or_start


def _parse_json(request) -> Tuple[Dict[str, Any], JsonResponse]:
    try:
        payload = json.loads(request.body.decode("utf-8"))
        return payload, None
    except json.JSONDecodeError:
        return {}, JsonResponse({"error": "Invalid JSON body."}, status=400)


def list_year_suffix(request):
    country = request.GET.get("country", "").strip()
    if not country:
        return JsonResponse({"items": []})
    input_root = get_root_by_type(RootPath.TYPE_INPUT)
    if not input_root:
        return JsonResponse({"items": []})
    years = list_level2(input_root, country)
    return JsonResponse({"items": years})


def list_countries(request):
    input_root = get_root_by_type(RootPath.TYPE_INPUT)
    if not input_root or not input_root.exists():
        return JsonResponse({"items": []})
    existing = {entry.name for entry in input_root.iterdir() if entry.is_dir()}
    countries = (
        Country.objects.filter(code__in=existing)
        .order_by("code")
        .values_list("code", flat=True)
    )
    return JsonResponse({"items": list(countries)})


def list_states(request):
    year_suffix = request.GET.get("year_suffix", "").strip()
    country = request.GET.get("country", "").strip()
    if not year_suffix or not country:
        return JsonResponse({"error": "year_suffix and country are required."}, status=400)
    input_root = get_root_by_type(RootPath.TYPE_INPUT)
    if not input_root:
        return JsonResponse({"items": []})
    states = list_level3(input_root, country, year_suffix)
    return JsonResponse({"items": states})


def list_pipeline_configs(request):
    configs = PipelineConfig.objects.all().order_by("name")
    data = [
        {
            "id": cfg.id,
            "name": cfg.name,
            "country": cfg.country.code if cfg.country else None,
            "batch_size": cfg.batch_size,
            "crops": [
                link.crop.display_name or link.crop.name
                for link in cfg.pipelineconfigcrop_set.select_related("crop").all()
            ],
        }
        for cfg in configs
    ]
    return JsonResponse({"items": data})


def dashboard(request):
    configs = PipelineConfig.objects.all().order_by("name")
    recent_jobs = Job.objects.all().order_by("-created_at")
    paginator = Paginator(recent_jobs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    input_root_active = RootPath.objects.filter(
        path_type=RootPath.TYPE_INPUT, is_active=True
    ).exists()
    output_root_active = RootPath.objects.filter(
        path_type=RootPath.TYPE_OUTPUT, is_active=True
    ).exists()
    input_root = get_root_by_type(RootPath.TYPE_INPUT)
    output_root = get_root_by_type(RootPath.TYPE_OUTPUT)
    return render(
        request,
        "core/dashboard.html",
        {
            "configs": configs,
            "recent_jobs": page_obj,
            "page_obj": page_obj,
            "input_root": str(input_root) if input_root else "",
            "output_root": str(output_root) if output_root else "",
            "input_root_active": input_root_active,
            "output_root_active": output_root_active,
        },
    )


@csrf_exempt
def create_job(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only."}, status=405)

    payload, error = _parse_json(request)
    if error:
        return error

    year_suffix = str(payload.get("year_suffix", "")).strip()
    country = str(payload.get("country", "")).strip()
    states = payload.get("states", [])
    output_name = str(payload.get("output_name", "")).strip()
    target_crops = str(payload.get("target_crops", "")).strip()
    schedule_at = payload.get("schedule_at")
    pipeline_config_id = payload.get("pipeline_config_id")
    gpu_count_raw = payload.get("gpu_count")
    skip_inference = bool(payload.get("skip_inference"))
    skip_merge = bool(payload.get("skip_merge"))
    skip_area = bool(payload.get("skip_area"))

    if not year_suffix or not country or not target_crops:
        return JsonResponse({"error": "Missing required fields."}, status=400)
    if not isinstance(states, list) or not states:
        return JsonResponse({"error": "At least one state is required."}, status=400)

    output_root = get_output_root()
    output_dir = output_root / output_name if output_name else output_root
    collision = output_dir.exists()
    if collision and output_name:
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{output_name}_{suffix}"
        output_dir = output_root / output_name

    pipeline_config = None
    if pipeline_config_id:
        pipeline_config = PipelineConfig.objects.filter(id=pipeline_config_id).first()
        if pipeline_config and pipeline_config.country and pipeline_config.country.code != country:
            return JsonResponse(
                {"error": "Selected model preset does not match the chosen country."},
                status=400,
            )

    schedule_dt = None
    if schedule_at:
        try:
            schedule_dt = datetime.fromisoformat(schedule_at)
            if timezone.is_naive(schedule_dt):
                schedule_dt = timezone.make_aware(schedule_dt)
        except ValueError:
            return JsonResponse({"error": "schedule_at must be ISO format."}, status=400)

    gpu_count = 0
    if gpu_count_raw is not None and str(gpu_count_raw).strip() != "":
        try:
            gpu_count = int(gpu_count_raw)
        except (TypeError, ValueError):
            return JsonResponse({"error": "gpu_count must be an integer."}, status=400)

        if gpu_count < -1:
            return JsonResponse({"error": "gpu_count must be >= -1."}, status=400)

        if gpu_count > 0:
            available = get_available_gpu_count()
            if available and gpu_count > available:
                return JsonResponse(
                    {"error": f"gpu_count exceeds available GPUs ({available})."},
                    status=400,
                )

    job = Job.objects.create(
        pipeline_config=pipeline_config,
        input_path={"year_suffix": year_suffix, "country": country},
        selected_states=states,
        target_crops=target_crops,
        output_dir_name=output_name,
        output_path=str(output_dir),
        skip_inference=skip_inference,
        skip_merge=skip_merge,
        skip_area=skip_area,
        gpu_count=gpu_count,
        schedule_at=schedule_dt,
    )

    queue_or_start(job)

    return JsonResponse(
        {
            "job_id": job.id,
            "output_dir_name": output_name,
            "collision": collision,
            "celery_task_id": job.celery_task_id,
            "gpu_count": job.gpu_count,
        },
        status=201,
    )


def gpu_available(request):
    return JsonResponse({"available": get_available_gpu_count()})


def job_progress(request, job_id: int):
    progress = get_all_progress(job_id)
    return JsonResponse(progress)


def _serialize_task_result(result: AsyncResult) -> Dict[str, Any]:
    info = result.info
    if isinstance(info, Exception):
        info = str(info)
    return {
        "id": result.id,
        "state": result.state,
        "info": info,
    }


def _build_chain_status(result: AsyncResult) -> Dict[str, Any]:
    chain = []
    node = result
    while node is not None:
        chain.append(_serialize_task_result(node))
        node = node.parent
    chain.reverse()
    return {"chain": chain}


def job_task_status(request, job_id: int):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)
    task_id = job.celery_chain_id or job.celery_task_id
    if not task_id:
        return JsonResponse({"error": "No Celery task registered for this job."}, status=404)
    result = AsyncResult(task_id, app=current_app)
    payload = _build_chain_status(result)
    payload["job_id"] = job.id
    payload["task_id"] = task_id
    return JsonResponse(payload)


def job_outputs(request, job_id: int):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)
    output_root = Path(job.output_path) if job.output_path else get_output_root()
    outputs = job.outputs.all().order_by("step", "relative_path")
    grouped: Dict[str, Any] = {}
    for output in outputs:
        base_dir = output_root / output.step
        file_path = Path(output.absolute_path)
        if not output_belongs_to_job(job, output.step, file_path, base_dir):
            continue
        grouped.setdefault(output.step, []).append(
            {
                "relative_path": output.relative_path,
                "absolute_path": output.absolute_path,
                "size_bytes": output.size_bytes,
                "bounds": output.bounds,
                "file_modified_at": output.file_modified_at.isoformat()
                if output.file_modified_at
                else None,
            }
        )
    return JsonResponse(
        {
            "job_id": job.id,
            "output_path": job.output_path,
            "steps": grouped,
            "logs": _list_job_logs(job.id),
        }
    )


def _list_job_logs(job_id: int):
    logs_root = get_logs_root()
    if not logs_root or not logs_root.exists():
        return []
    prefix = f"{job_id}"
    entries = []
    for path in logs_root.glob(f"{prefix}*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append(
            {
                "name": path.name,
                "size_bytes": stat.st_size,
                "file_modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    entries.sort(key=lambda item: item["name"])
    return entries


def download_log(request, job_id: int):
    name = request.GET.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "name is required."}, status=400)
    if not name.startswith(f"{job_id}"):
        return JsonResponse({"error": "Invalid log name."}, status=400)
    logs_root = get_logs_root()
    file_path = (logs_root / name).resolve()
    try:
        file_path.relative_to(logs_root)
    except ValueError:
        return JsonResponse({"error": "Invalid log path."}, status=400)
    if not file_path.exists() or not file_path.is_file():
        return JsonResponse({"error": "Log file not found."}, status=404)
    return FileResponse(file_path.open("rb"), as_attachment=True, filename=file_path.name)


def download_output(request, job_id: int):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)

    # The `path` parameter from the client is the relative_path
    relative_path_req = request.GET.get("path", "").strip()
    if not relative_path_req:
        return JsonResponse({"error": "path is required."}, status=400)

    output = job.outputs.filter(relative_path=relative_path_req).first()
    if not output:
        return JsonResponse({"error": "File not found in this job's records."}, status=404)

    # Reconstruct the path from the job's output directory and the file's relative path
    # This is more robust than relying on the stored absolute_path
    if not job.output_path:
         return JsonResponse({"error": "Job has no output path defined."}, status=500)

    file_path = (Path(job.output_path) / output.step / output.relative_path).resolve()

    if not file_path.exists() or not file_path.is_file():
        # Provide a more detailed error message for debugging
        return JsonResponse({
            "error": "File missing on disk.",
            "debug_info": {
                "searched_path": str(file_path),
                "job_output_path": job.output_path,
                "output_step": output.step,
                "output_relative_path": output.relative_path
            }
        }, status=404)

    return FileResponse(file_path.open("rb"), as_attachment=True, filename=file_path.name)


@csrf_exempt
def download_job_outputs_zip(request, job_id: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST only."}, status=405)
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)
    payload, error = _parse_json(request)
    paths = []
    if error is None and isinstance(payload, dict) and payload.get("paths"):
        paths = payload.get("paths", [])
    else:
        paths = request.POST.getlist("paths")
    if not paths:
        return JsonResponse({"error": "No outputs selected."}, status=400)
    outputs = list(job.outputs.filter(absolute_path__in=paths))
    if not outputs:
        return JsonResponse({"error": "No matching outputs."}, status=404)
    import tempfile
    import zipfile

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for output in outputs:
            file_path = Path(output.absolute_path)
            if file_path.exists():
                zf.write(file_path, arcname=output.relative_path)
    filename = f"job_{job.id}_outputs.zip"
    return FileResponse(open(tmp.name, "rb"), as_attachment=True, filename=filename)


def job_detail(request, job_id: int):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)
    return render(
        request,
        "core/job_detail.html",
        {
            "job": job,
        },
    )


def job_outputs_page(request):
    selected_country = request.GET.get("country", "").strip()
    selected_year_suffix = request.GET.get("year_suffix", "").strip()
    selected_output_name = request.GET.get("output_name", "").strip()

    # Base queryset for outputs
    outputs_qs = JobOutput.objects.select_related("job").order_by("-file_modified_at")

    # Apply filters
    if selected_country:
        outputs_qs = outputs_qs.filter(job__input_path__country=selected_country)
    if selected_year_suffix:
        outputs_qs = outputs_qs.filter(job__input_path__year_suffix=selected_year_suffix)
    if selected_output_name:
        outputs_qs = outputs_qs.filter(job__output_dir_name=selected_output_name)

    # Group filtered outputs by step
    outputs_by_step = {
        JobOutput.STEP_INFERENCE: [],
        JobOutput.STEP_MERGE: [],
        JobOutput.STEP_AREA: [],
    }
    
    # Deduplicate outputs, keeping only the latest version of each file
    latest_outputs = {}
    for output in outputs_qs:
        if output.relative_path not in latest_outputs or output.file_modified_at > latest_outputs[output.relative_path].file_modified_at:
            latest_outputs[output.relative_path] = output

    for output in latest_outputs.values():
        if output.step in outputs_by_step:
            outputs_by_step[output.step].append(output)

    # Get distinct values for filter dropdowns from ALL jobs, not just filtered ones
    all_jobs = Job.objects.all()
    countries = sorted(list(all_jobs.values_list("input_path__country", flat=True).distinct()))
    year_suffixes = sorted(list(all_jobs.values_list("input_path__year_suffix", flat=True).distinct()))
    output_names = sorted(list(all_jobs.values_list("output_dir_name", flat=True).distinct()))

    context = {
        "outputs_by_step": outputs_by_step,
        "countries": [c for c in countries if c],
        "year_suffixes": [y for y in year_suffixes if y],
        "output_names": [n for n in output_names if n],
        "selected_country": selected_country,
        "selected_year_suffix": selected_year_suffix,
        "selected_output_name": selected_output_name,
    }
    return render(request, "core/job_outputs.html", context)


def filtered_outputs(request):
    selected_country = request.GET.get("country", "").strip()
    selected_year_suffix = request.GET.get("year_suffix", "").strip()
    selected_output_name = request.GET.get("output_name", "").strip()

    outputs_qs = JobOutput.objects.select_related("job").filter(step=JobOutput.STEP_THUMBNAIL).order_by("-file_modified_at")

    if selected_country:
        outputs_qs = outputs_qs.filter(job__input_path__country=selected_country)
    if selected_year_suffix:
        outputs_qs = outputs_qs.filter(job__input_path__year_suffix=selected_year_suffix)
    if selected_output_name:
        outputs_qs = outputs_qs.filter(job__output_dir_name=selected_output_name)

    # Deduplicate outputs, keeping only the latest version of each file
    latest_outputs = {}
    for output in outputs_qs:
        if output.relative_path not in latest_outputs or output.file_modified_at > latest_outputs[output.relative_path].file_modified_at:
            latest_outputs[output.relative_path] = output
    
    results = []
    for output in latest_outputs.values():
        results.append({
            "job_id": output.job.id,
            "relative_path": output.relative_path,
            "bounds": output.bounds,
        })

    return JsonResponse({"items": results})


def download_job_step_zip(request, job_id: int):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return HttpResponse("Job not found", status=404)

    step = request.GET.get("step", "").strip()
    
    outputs_qs = job.outputs.all()
    if step:
        outputs_qs = outputs_qs.filter(step=step)

    if not outputs_qs.exists():
        return HttpResponse("No output files found for this job/step.", status=404)

    with tempfile.NamedTemporaryFile(delete=True, suffix=".zip") as tmp:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for output in outputs_qs:
                try:
                    file_path = (Path(job.output_path) / output.step / output.relative_path).resolve()
                    if file_path.exists() and file_path.is_file():
                        # Create a nested structure inside the zip
                        arcname = Path(output.step) / output.relative_path
                        zf.write(file_path, arcname=arcname)
                except Exception:
                    # Ignore files that can't be found or read
                    pass
        
        # Check if the zip file has content
        if zf.namelist():
            tmp.seek(0)
            response = HttpResponse(tmp.read(), content_type="application/zip")
            zip_filename = f"job_{job.id}_{step if step else 'all'}_outputs.zip"
            response["Content-Disposition"] = f"attachment; filename={zip_filename}"
            return response
        else:
            return HttpResponse("No valid output files could be zipped.", status=404)


@csrf_exempt
def download_outputs_zip(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only."}, status=405)
    payload, error = _parse_json(request)
    paths = []
    if error is None and isinstance(payload, dict) and payload.get("paths"):
        paths = payload.get("paths", [])
    else:
        paths = request.POST.getlist("paths")
    if not paths:
        return JsonResponse({"error": "No outputs selected."}, status=400)
    outputs = list(JobOutput.objects.select_related("job").filter(absolute_path__in=paths))
    if not outputs:
        return JsonResponse({"error": "No matching outputs."}, status=404)
    import tempfile
    import zipfile

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for output in outputs:
            file_path = Path(output.absolute_path)
            if file_path.exists():
                arcname = f"{output.job_id}/{output.step}/{output.relative_path}"
                zf.write(file_path, arcname=arcname)
    filename = "job_outputs.zip"
    return FileResponse(open(tmp.name, "rb"), as_attachment=True, filename=filename)


def job_info(request, job_id: int):
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)
    return JsonResponse(
        {
            "id": job.id,
            "status": job.status,
            "progress_percent": job.progress_percent,
            "current_step": job.current_step,
            "celery_last_state": job.celery_last_state,
            "error": job.celery_error,
        }
    )


@csrf_exempt
def cancel_job(request, job_id: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST only."}, status=405)
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)
    set_cancel(job.id, True)
    job.status = Job.STATUS_CANCELLED
    job.celery_error = "Cancelled by user."
    job.save(update_fields=["status", "celery_error", "updated_at"])
    from celery import current_app

    task_ids = {job.celery_chain_id, job.celery_task_id}
    for task_id in task_ids:
        if task_id:
            current_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
    return JsonResponse({"status": "cancelled"})


@csrf_exempt
def retry_job(request, job_id: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST only."}, status=405)
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "Job not found."}, status=404)
    payload, error = _parse_json(request)
    if error:
        payload = {}
    if isinstance(payload, dict):
        if "skip_inference" in payload:
            job.skip_inference = bool(payload.get("skip_inference"))
        if "skip_merge" in payload:
            job.skip_merge = bool(payload.get("skip_merge"))
        if "skip_area" in payload:
            job.skip_area = bool(payload.get("skip_area"))
    reset_progress(job.id)
    set_cancel(job.id, False)
    job.status = Job.STATUS_PENDING
    job.progress_percent = 0
    job.celery_error = ""
    job.celery_last_state = ""
    job.save(
        update_fields=[
            "status",
            "progress_percent",
            "celery_error",
            "celery_last_state",
            "skip_inference",
            "skip_merge",
            "skip_area",
            "updated_at",
        ]
    )
    queue_or_start(job)
    return JsonResponse({"status": "queued"})


@staff_member_required
def validate_path(request):
    raw_path = request.GET.get("path", "").strip()
    if not raw_path:
        return JsonResponse({"resolved": "", "exists": False})
    path = Path(raw_path)
    if not path.is_absolute():
        base_dir = getattr(settings, "MEDIA_ROOT", settings.BASE_DIR)
        path = (base_dir / path).resolve()
    return JsonResponse({"resolved": str(path), "exists": path.exists()})


def root_settings_page(request):
    return render(request, "core/settings.html")


@csrf_exempt
def root_settings(request):
    if request.method == "GET":
        input_items = list(
            RootPath.objects.filter(path_type=RootPath.TYPE_INPUT)
            .order_by("-updated_at")
            .values("id", "path", "is_active")
        )
        output_items = list(
            RootPath.objects.filter(path_type=RootPath.TYPE_OUTPUT)
            .order_by("-updated_at")
            .values("id", "path", "is_active")
        )
        log_items = list(
            RootPath.objects.filter(path_type=RootPath.TYPE_LOGS)
            .order_by("-updated_at")
            .values("id", "path", "is_active")
        )
        return JsonResponse(
            {
                "input": input_items,
                "output": output_items,
                "logs": log_items,
            }
        )
    if request.method != "POST":
        return JsonResponse({"error": "POST only."}, status=405)

    payload, error = _parse_json(request)
    if error:
        return error

    action = payload.get("action")
    root_type = payload.get("type")
    path_value = str(payload.get("path", "")).strip()
    root_id = payload.get("id")

    if root_type not in ["input", "output", "logs"]:
        return JsonResponse({"error": "type must be input, output, or logs."}, status=400)

    model = RootPath
    if root_type == "input":
        path_type = RootPath.TYPE_INPUT
    elif root_type == "output":
        path_type = RootPath.TYPE_OUTPUT
    else:
        path_type = RootPath.TYPE_LOGS

    if action == "add":
        if not path_value:
            return JsonResponse({"error": "path is required."}, status=400)
        obj = model.objects.create(
            path=path_value,
            path_type=path_type,
            is_active=bool(payload.get("activate")),
        )
        return JsonResponse({"id": obj.id, "path": obj.path, "is_active": obj.is_active})

    if action == "activate":
        if not root_id:
            return JsonResponse({"error": "id is required."}, status=400)
        obj = model.objects.filter(id=root_id, path_type=path_type).first()
        if not obj:
            return JsonResponse({"error": "root not found."}, status=404)
        obj.is_active = True
        obj.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"id": obj.id, "path": obj.path, "is_active": obj.is_active})

    return JsonResponse({"error": "Unknown action."}, status=400)
