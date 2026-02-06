from django.contrib.auth.decorators import login_required
from .forms import UploadedTifForm
from .models import UploadedTif
from .utils import run_gdal2tiles
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
import os
import shutil
from .tasks import process_uploaded_tif  # Celery task 불러오기
from django.http import HttpResponse

import json
# @login_required
# def upload_view(request):
#     if request.method == 'POST':
#         form = UploadedTifForm(request.POST, request.FILES)
#         if form.is_valid():
#             tif = form.save(commit=False)
#             tif.user = request.user
#             tif.status = 'pending'
#             tif.save()
#
#             input_path = os.path.join(settings.MEDIA_ROOT, tif.file.name)
#             output_path = os.path.join(settings.MEDIA_ROOT, tif.tile_output_path())
#             os.makedirs(output_path, exist_ok=True)
#             process_uploaded_tif.delay(tif.id, input_path, output_path)
#
#             return redirect('tile_list')  # 또는 'tile_result'는 상태 확인 필요
#     else:
#         form = UploadedTifForm()
#     return render(request, 'tileupload/tile_upload.html', {'form': form})

@login_required
def upload_view(request):

    if request.method == 'POST':
        form = UploadedTifForm(request.POST, request.FILES)
        print("📋 form fields:", form.fields)
        if form.is_valid():
            tif = form.save(commit=False)
            tif.user = request.user
            tif.status = 'pending'

            label_data = json.loads(form.cleaned_data['color_label_json'])
            tif.set_color_labels(label_data)

            tif.save()

            input_path = os.path.join(settings.MEDIA_ROOT, tif.file.name)
            output_path = os.path.join(settings.MEDIA_ROOT, tif.tile_output_path())

            # ✅ Celery task 호출 시 색상 정보도 함께 전달
            from .tasks import process_uploaded_tif
            process_uploaded_tif.delay(tif.id, input_path, output_path, label_data)

            return redirect('tile_list')
        else:
            return render(request, 'tileupload/tile_upload.html', {
                'form': form,
                'form_errors': form.errors,  # 이걸 템플릿에서 보여줌
            })
    else:
        form = UploadedTifForm()
    return render(request, 'tileupload/tile_upload.html', {'form': form})

@login_required
def result_view(request, tif_id):
    tif = get_object_or_404(UploadedTif, id=tif_id, user=request.user)
    tile_url = f"/media/{tif.tile_output_path()}"
    legend_items = tif.get_color_labels()
    legend_json = json.dumps(legend_items)
    return render(request, 'tileupload/tile_detail.html', {
        'tile_url': tile_url,
        'tif': tif,
        'legend_items': legend_items,
        'legend_json': legend_json,
    })
# @login_required
# def result_view(request, tif_id):
#     tif = get_object_or_404(UploadedTif, id=tif_id, user=request.user)
#     tile_url = f"/media/{tif.tile_output_path()}"
#     return render(request, 'tileupload/tile_detail.html', {'tile_url': tile_url, 'tif': tif})

@login_required
def list_view(request):
    files = UploadedTif.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'tileupload/tile_list.html', {'files': files})

@login_required
def delete_view(request, tif_id):
    tif = get_object_or_404(UploadedTif, id=tif_id, user=request.user)
    file_path = tif.file.path
    tile_dir = os.path.join(settings.MEDIA_ROOT, tif.tile_output_path())

    tif.delete()

    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(tile_dir):
        shutil.rmtree(tile_dir)

    return redirect('tile_list')
