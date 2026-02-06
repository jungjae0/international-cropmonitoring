from .forms import JobForm
from .models import Job
from .tasks import process_job_chain
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.http import FileResponse, Http404
from django.conf import settings
import os
from .utils import resolve_existing_result

@login_required
def create_job(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            # 1. Job 객체 생성
            job = form.save(commit=False)
            job.user = request.user
            job.status = 'queued'
            job.save()

            # 2. 기존 결과 확인 → 처리 여부 분기
            resolve_existing_result(job)

            # 3. 상세 페이지로 이동
            return redirect('job_detail', job_id=job.id)
    else:
        form = JobForm()

    return render(request, 'jobs/create_job.html', {'form': form})


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/job_detail.html', {'job': job})


def job_status_api(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return JsonResponse({
        'status': job.status,
        'current_step': job.current_step,
        'progress': job.progress,
        'error_message': job.error_message,
    })

def download_tif(request, job_id):
    job = Job.objects.get(id=job_id)

    file_path = os.path.join(
        settings.MEDIA_ROOT,
        job.crop_type,
        job.region,
        str(job.year),
        'cropmapping.tif'
    )

    if not os.path.exists(file_path):
        raise Http404("파일이 존재하지 않습니다.")

    response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename='cropmapping.tif')
    return response

# def overall_map_view(request):
#     selected_crop = request.GET.get('crop')
#     selected_year = request.GET.get('year')
#
#     crops = Job.objects.values_list('crop_type', flat=True).distinct()
#     years = Job.objects.values_list('year', flat=True).distinct()
#
#     tiles = []
#     if selected_crop and selected_year:
#         jobs = Job.objects.filter(crop_type=selected_crop, year=selected_year, status='done')
#         for job in jobs:
#             tiles.append({
#                 'region': job.region,
#                 'tile_path': f"/media/{job.crop_type}/{job.region}/{job.year}/tiles"
#             })
#
#     return render(request, 'jobs/overall_map.html', {
#         'tiles': tiles,
#         'selected_crop': selected_crop,
#         'selected_year': selected_year,
#         'crops': sorted(set(crops)),
#         'years': sorted(set(years), reverse=True),
#     })



def overall_map_view(request):
    selected_crop = request.GET.get('crop')
    selected_year = request.GET.get('year')

    crops = ['Wheat', 'Corn', 'Bean']
    years = ['2024', '2023', '2022']
    north_state = ["Washington", "Oregon", "Idaho", "Texas"]
    south_state = ["Kansas", "Oklahoma", "Colorado", "Nebraska", ]
    REGIONS = north_state + south_state


    tiles = []
    if selected_crop and selected_year:
        for region in REGIONS:
            tile_dir = os.path.join(
                settings.MEDIA_ROOT,
                selected_crop,
                region,
                selected_year,
                'tiles'
            )
            if os.path.exists(tile_dir):
                tiles.append({
                    'region': region,
                    'tile_path': f"/media/{selected_crop}/{region}/{selected_year}/tiles"
                })

    return render(request, 'jobs/overall_map.html', {
        'tiles': tiles,
        'selected_crop': selected_crop,
        'selected_year': selected_year,
        'crops': crops,
        'years': years,
    })



@login_required
def job_list(request):
    jobs = Job.objects.filter(user=request.user).order_by('-created_at')  # 본인 작업만
    return render(request, 'jobs/job_list.html', {'jobs': jobs})