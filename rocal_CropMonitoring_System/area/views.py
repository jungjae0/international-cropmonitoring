from django.shortcuts import render
from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import Sum
from django.views.decorators.http import require_GET
import numpy as np
import json
import os

from .models import CultivatedArea
from core.models import Crop, State, Country
from django.conf import settings


def sanitize_for_json(obj):
    """NaN, Infinity를 None으로 변환하여 JSON 직렬화 가능하게 만듦"""
    if isinstance(obj, (float, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    return obj


# 1. 지도 및 필터 UI 렌더링
def area_map(request):
    years = list(range(now().year, 2017, -1))  # 2025 → 2018
    crops = Crop.objects.values_list('name', flat=True)
    countries = Country.objects.all()

    return render(request, 'area/area_map.html', {
        'years': years,
        'crops': crops,
        'countries': countries,
    })


# 2. GeoJSON 지도 + 그래프용 데이터 API
@require_GET
def api_choropleth(request):
    crop_name = request.GET.get("crop")
    year = request.GET.get("year")
    country_iso = request.GET.get("country")

    if not crop_name or not year or not country_iso:
        return JsonResponse({"error": "Missing crop, year, or country"}, status=400)

    try:
        crop = Crop.objects.get(name=crop_name)
        country = Country.objects.get(iso_code=country_iso)
        year = int(year)
    except (Crop.DoesNotExist, Country.DoesNotExist, ValueError):
        return JsonResponse({"error": "Invalid crop, country, or year"}, status=400)

    states = State.objects.filter(country=country)

    area_by_state = {}
    boundary_geojson = None

    # Boundary GeoJSON을 직접 읽어 반환 (Nginx /media 문제 우회)
    try:
        # MEDIA_ROOT 기준 경로 생성 (플랫폼 독립적)
        local_boundary = os.path.join(settings.MEDIA_ROOT, country.iso_code, "Layers", f"{country.iso_code}_states.json")

        # 디버깅: 경로 정보 출력
        print(f"[DEBUG] MEDIA_ROOT: {settings.MEDIA_ROOT}")
        print(f"[DEBUG] country.iso_code: {country.iso_code}")
        print(f"[DEBUG] local_boundary (raw): {local_boundary}")
        print(f"[DEBUG] country.boundary_path: {country.boundary_path}")

        candidates = [local_boundary, country.boundary_path]
        for path in candidates:
            # 윈도우 경로를 리눅스에서도 사용 가능하도록 변환
            normalized_path = path.replace('\\', '/')
            print(f"[DEBUG] Trying path: {normalized_path}")
            print(f"[DEBUG] Path exists: {os.path.exists(normalized_path)}")

            if os.path.exists(normalized_path):
                with open(normalized_path, "r", encoding="utf-8") as f:
                    boundary_geojson = json.load(f)
                print(f"✅ [area.api_choropleth] boundary loaded: {normalized_path}")
                break
        else:
            # 파일을 찾지 못한 경우 디렉토리 내용 확인
            media_root_exists = os.path.exists(settings.MEDIA_ROOT)
            print(f"[DEBUG] MEDIA_ROOT exists: {media_root_exists}")
            if media_root_exists:
                try:
                    contents = os.listdir(settings.MEDIA_ROOT)
                    print(f"[DEBUG] MEDIA_ROOT contents: {contents}")
                except Exception as e:
                    print(f"[DEBUG] Cannot list MEDIA_ROOT: {e}")
            print(f"⚠️ [area.api_choropleth] boundary not found. Tried: {candidates}")
    except Exception as e:
        boundary_geojson = None
        print(f"❌ [area.api_choropleth] boundary load error: {e}")
        import traceback
        traceback.print_exc()

    # 전체 국가의 올해 면적 총합
    total_area = CultivatedArea.objects.filter(
        crop_season__crop=crop,
        crop_season__year=year,
        crop_season__state__in=states
    ).aggregate(total=Sum('area_acres'))['total'] or 0

    for state in states:
        # 올해
        current = CultivatedArea.objects.filter(
            crop_season__crop=crop,
            crop_season__year=year,
            crop_season__state=state
        ).aggregate(total=Sum('area_acres'))['total'] or 0

        # 전년도
        last = CultivatedArea.objects.filter(
            crop_season__crop=crop,
            crop_season__year=year - 1,
            crop_season__state=state
        ).aggregate(total=Sum('area_acres'))['total'] or 0

        # 평년
        previous_years = CultivatedArea.objects.filter(
            crop_season__crop=crop,
            crop_season__year__gte=2018,
            crop_season__year__lte=2023,
            crop_season__state=state
        ).values('crop_season__year').annotate(total=Sum('area_acres'))

        # NaN 방지: 빈 리스트일 경우 0 반환
        year_totals = [row['total'] for row in previous_years if row['total'] is not None]
        average = float(np.mean(year_totals)) if year_totals else 0.0

        percent = (current / total_area * 100) if total_area > 0 else 0.0

        area_by_state[state.name] = {
            "current": float(current),
            "last": float(last),
            "average": float(average),
            "percent": round(percent, 1),
            "center_lat": state.center_lat,
            "center_lng": state.center_lng
        }

    response_data = {
        "center_lat": country.center_lat,
        "center_lng": country.center_lng,
        "boundary_url": country.get_absolute_url(),
        "boundary_geojson": boundary_geojson,
        "area_by_state": area_by_state,
    }

    # NaN 값을 None으로 변환
    return JsonResponse(response_data)


# 3. crop-country 기반 유효 연도 조회 API
@require_GET
def api_available_years(request):
    crop_name = request.GET.get("crop")
    country_iso = request.GET.get("country")

    crop = Crop.objects.filter(name=crop_name).first()
    country = Country.objects.filter(iso_code=country_iso).first()

    if not crop or not country:
        return JsonResponse({"years": []})

    states = State.objects.filter(country=country)

    years = (
        CultivatedArea.objects
        .filter(
            crop_season__crop=crop,
            crop_season__state__in=states
        )
        .values_list("crop_season__year", flat=True)
        .distinct()
    )

    return JsonResponse({"years": sorted(years, reverse=True)})
