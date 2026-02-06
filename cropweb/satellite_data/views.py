# views.py
from django.http import HttpResponse, Http404
import zipfile
from django.shortcuts import render
import os
from .models import FileRecord
from django.http import StreamingHttpResponse
from io import BytesIO

def download_file(request, record_id):
    try:
        file_record = FileRecord.objects.get(id=record_id)
        file_path = file_record.path
        with open(file_path, "rb") as file:
            response = HttpResponse(file.read(), content_type="application/octet-stream")
            response["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    except FileRecord.DoesNotExist:
        raise Http404("File not found.")
    except Exception as e:
        raise Http404(str(e))



# views.py
from django.shortcuts import render

# def file_list(request):
#     file_records = FileRecord.objects.all()
#     return render(request, "download_list.html", {"file_records": file_records})
#


# views.py
from django.shortcuts import render
from .models import FileRecord

from django.shortcuts import render
from .models import FileRecord

def file_list(request):
    # GET 요청에서 필터 값 가져오기
    selected_data_sources = request.GET.getlist('data_source')
    selected_nations = request.GET.getlist('nation')
    selected_years = request.GET.getlist('year')
    selected_months = request.GET.getlist('month')

    # 필터링 로직
    file_records = FileRecord.objects.all()
    if selected_data_sources:
        file_records = file_records.filter(data_source__in=selected_data_sources)
    if selected_nations:
        file_records = file_records.filter(nation__in=selected_nations)
    if selected_years:
        file_records = file_records.filter(year__in=[int(year) for year in selected_years])
    if selected_months:
        file_records = file_records.filter(month__in=[int(month) for month in selected_months])

    # 필터링 옵션 데이터
    data_sources = FileRecord.objects.values_list('data_source', flat=True).distinct()
    nations = FileRecord.objects.values_list('nation', flat=True).distinct()
    years = FileRecord.objects.values_list('year', flat=True).distinct()
    months = range(1, 13)  # 1부터 12까지

    # 테이블이 필터 버튼 클릭 후에만 뜨도록 설정
    show_table = bool(request.GET)

    context = {
        'file_records': file_records,
        'data_sources': data_sources,
        'nations': nations,
        'years': years,
        'months': months,
        'selected_data_sources': selected_data_sources,
        'selected_nations': selected_nations,
        'selected_years': selected_years,
        'selected_months': selected_months,
        'show_table': show_table,
    }
    return render(request, 'download_list.html', context)

def download_zip(request):
    # POST 요청에서 필터 값 가져오기
    data_source = request.POST.get('data_source', '')
    nation = request.POST.get('nation', '')
    years = request.POST.get('years', '').split(',')
    months = request.POST.get('months', '').split(',')

    # 필터링 로직
    file_records = FileRecord.objects.all()
    if data_source:
        file_records = file_records.filter(data_source=data_source)
    if nation:
        file_records = file_records.filter(nation=nation)
    if years and years != ['']:
        file_records = file_records.filter(year__in=years)
    if months and months != ['']:
        file_records = file_records.filter(month__in=months)

    # 파일 경로 목록 생성
    file_paths = [record.path for record in file_records if os.path.exists(record.path)]

    # 스트리밍 ZIP 생성
    def stream_zip(files):
        with zipfile.ZipFile(BytesIO(), 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in files:
                try:
                    # ZIP 파일에 추가
                    zip_file.write(file_path, os.path.basename(file_path))
                except Exception as e:
                    # 특정 파일이 잘못되었을 경우 건너뛰기
                    print(f"Failed to add file {file_path}: {e}")
            # ZIP 데이터 스트리밍
            zip_file.fp.seek(0)
            yield zip_file.fp.read()

    if not file_paths:
        return HttpResponse("No valid files found to zip.", status=404)

    response = StreamingHttpResponse(stream_zip(file_paths), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="filtered_files.zip"'
    return response

# def download_zip(request):
#     # GET 요청에서 필터 값 가져오기
#     selected_data_sources = request.GET.getlist('data_source')
#     selected_nations = request.GET.getlist('nation')
#     selected_years = request.GET.getlist('year')
#     selected_months = request.GET.getlist('month')
#
#     # 필터링 로직
#     file_records = FileRecord.objects.all()
#     if selected_data_sources:
#         file_records = file_records.filter(data_source__in=selected_data_sources)
#     if selected_nations:
#         file_records = file_records.filter(nation__in=selected_nations)
#     if selected_years:
#         file_records = file_records.filter(year__in=[int(year) for year in selected_years])
#     if selected_months:
#         file_records = file_records.filter(month__in=[int(month) for month in selected_months])
#
#     # ZIP 파일 생성
#     response = HttpResponse(content_type='application/zip')
#     response['Content-Disposition'] = 'attachment; filename="filtered_files.zip"'
#     zip_file = zipfile.ZipFile(response, 'w')
#
#     for record in file_records:
#         if os.path.exists(record.path):
#             zip_file.write(record.path, os.path.basename(record.path))
#
#     zip_file.close()
#     return response

# def file_list(request):
#     # GET 요청에서 필터 값 가져오기
#     selected_data_source = request.GET.get('data_source', '')
#     selected_nation = request.GET.get('nation', '')
#     selected_year = request.GET.get('year', '')
#     selected_month = request.GET.get('month', '')
#
#     # 필터링 로직
#     file_records = FileRecord.objects.all()
#     if selected_data_source:
#         file_records = file_records.filter(data_source=selected_data_source)
#     if selected_nation:
#         file_records = file_records.filter(nation=selected_nation)
#     if selected_year:
#         try:
#             file_records = file_records.filter(year=int(selected_year))
#         except ValueError:
#             pass  # 유효하지 않은 입력값은 필터링하지 않음
#     if selected_month:
#         try:
#             file_records = file_records.filter(month=int(selected_month))
#         except ValueError:
#             pass
#
#     # 필터링 옵션 데이터 (동적 선택 가능)
#     data_sources = FileRecord.objects.values_list('data_source', flat=True).distinct()
#     nations = FileRecord.objects.values_list('nation', flat=True).distinct()
#     years = FileRecord.objects.values_list('year', flat=True).distinct()
#     months = range(1, 13)  # 1월부터 12월까지 고정 제공
#
#     # 템플릿에 전달
#     context = {
#         'file_records': file_records,
#         'data_sources': data_sources,
#         'nations': nations,
#         'years': years,
#         'months': months,
#         'selected_data_source': selected_data_source,
#         'selected_nation': selected_nation,
#         'selected_year': selected_year,
#         'selected_month': selected_month,
#     }
#     return render(request, 'download_list.html', context)