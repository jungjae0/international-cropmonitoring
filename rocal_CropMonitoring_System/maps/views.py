# maps/views.py
import os
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET

from core.models import Country, State, Crop, CropSeason
from .models import TileSet


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


def map_view(request):
    crops = Crop.objects.values_list('name', flat=True).distinct()
    return render(request, 'maps/map_view.html', {'crops': crops})


@require_GET
def get_tile_options(request):
    crop    = request.GET.get('crop')
    year    = request.GET.get('year')
    country = request.GET.get('country')
    state   = request.GET.get('state')  # NOTE: 이 값이 ""일 수도 있음

    if crop and not year:
        years = (
            CropSeason.objects
            .filter(crop__name=crop)
            .values_list('year', flat=True)
            .distinct()
        )
        return JsonResponse({'years': sorted(years)})

    if crop and year and not country:
        countries = (
            Country.objects
            .filter(states__cropseason__crop__name=crop,
                    states__cropseason__year=year)
            .distinct()
            .values_list('name', flat=True)
        )
        return JsonResponse({'countries': list(countries)})

    if crop and year and country and (state is None or state == ""):
        # 주 목록 반환
        try:
            country_obj = Country.objects.get(name=country)
        except Country.DoesNotExist:
            return JsonResponse({'error': 'Country not found'}, status=404)

        states = (
            State.objects
            .filter(country=country_obj, cropseason__crop__name=crop, cropseason__year=year)
            .distinct()
            .values_list('name', flat=True)
        )
        return JsonResponse({'states': list(states)})

    if crop and year and country:
        # ✅ variant 목록 반환 (state가 있어도 없어도 처리 가능)
        qs = TileSet.objects.filter(
            crop_season__crop__name=crop,
            crop_season__year=year,
            crop_season__state__country__name=country
        )
        if state:
            qs = qs.filter(crop_season__state__name=state)

        variants = qs.values_list('variant', flat=True).distinct()
        return JsonResponse({'variants': list(variants)})

    return JsonResponse({'error': 'Invalid parameters'}, status=400)

@require_GET
def get_tile_url(request):
    crop    = request.GET.get('crop')
    year    = request.GET.get('year')
    country = request.GET.get('country')
    state   = request.GET.get('state')
    variant = request.GET.get('variant', '')

    if not all([crop, year, country, state]):
        return JsonResponse({'error': 'Missing parameters.'}, status=400)

    try:
        ts = TileSet.objects.select_related(
            'crop_season__state__country',
            'crop_season__crop'
        ).get(
            crop_season__crop__name=crop,
            crop_season__year=int(year),
            crop_season__state__name=state,
            crop_season__state__country__name=country,
            variant=variant
        )
    except (TileSet.DoesNotExist, ValueError):
        return JsonResponse({'error': 'No tileset found'}, status=404)

    return JsonResponse({'tile_url': ts.get_tile_url()})


@require_GET
def get_country_tiles(request):
    crop    = request.GET.get('crop')
    year    = request.GET.get('year')
    country = request.GET.get('country')
    variant = request.GET.get('variant')

    if not all([crop, year, country]):
        return JsonResponse({'error': 'Missing parameters.'}, status=400)

    try:
        country_obj = Country.objects.get(name=country)
    except Country.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)

    states_qs = State.objects.filter(country=country_obj)

    tilesets = TileSet.objects.select_related('crop_season__state').filter(
        crop_season__crop__name=crop,
        crop_season__year=int(year),
        crop_season__state__in=states_qs,
    )
    if variant:
        tilesets = tilesets.filter(variant=variant)

    tile_data = []
    seen_states = set()

    for ts in tilesets:
        state_name = ts.crop_season.state.name
        if state_name not in seen_states:
            seen_states.add(state_name)
            tile_data.append({
                'state': state_name,
                'tile_url': ts.get_tile_url(),
                'center_lat': ts.crop_season.state.center_lat,
                'center_lng': ts.crop_season.state.center_lng,
            })

    return JsonResponse({
        'country_center': {
            'lat': country_obj.center_lat,
            'lng': country_obj.center_lng,
        },
        'tiles': tile_data,
        'states': sorted(seen_states),
    })


@require_GET
def area_summary(request):
    crop    = request.GET.get('crop')
    year    = request.GET.get('year')
    country = request.GET.get('country')
    state   = request.GET.get('state')
    variant = request.GET.get('variant') or ""
    mode    = request.GET.get('mode', '')

    if not all([crop, year, country]):
        return JsonResponse({'error': 'Missing parameters.'}, status=400)

    try:
        year = int(year)
        last_year = year - 1
    except ValueError:
        return JsonResponse({'error': 'Invalid year'}, status=400)

    # ✅ 시계열 모드
    if mode == 'time_series' and state:
        series = TileSet.objects.select_related('crop_season').filter(
            crop_season__crop__name=crop,
            crop_season__state__name=state,
            crop_season__state__country__name=country,
            variant=variant
        ).order_by('crop_season__year')

        time_data = [
            {'year': ts.crop_season.year, 'area': round(ts.area, 2)}
            for ts in series if ts.area is not None
        ]
        response_data = {
            'mode': 'time_series',
            'state': state,
            'variant': variant,
            'series': time_data
        }
        return JsonResponse(response_data)

    # 기본 쿼리셋
    qs = TileSet.objects.select_related('crop_season__state__country').filter(
        crop_season__crop__name=crop,
        crop_season__state__country__name=country,
        crop_season__year__in=[last_year, year]
    )

    # 국가 전체 요약
    if not state:
        if variant:
            qs = qs.filter(variant=variant)
        current = {}
        previous = {}
        for ts in qs:
            key = ts.crop_season.state.name
            if ts.crop_season.year == year:
                current[key] = current.get(key, 0.0) + (ts.area or 0)
            elif ts.crop_season.year == last_year:
                previous[key] = previous.get(key, 0.0) + (ts.area or 0)

        combined = []
        for st in current:
            cur = current.get(st, 0.0)
            prev = previous.get(st, 0.0)
            diff = cur - prev
            pct = (diff / prev * 100) if prev else None
            combined.append({
                'state': st,
                'variant': variant or '전체',
                'area': round(cur, 2),
                'last_year_area': round(prev, 2),
                'diff': round(diff, 2),
                'percent_change': round(pct, 1) if pct is not None else None
            })

        total = sum(item['area'] for item in combined)
        response_data = {
            'mode': 'summary',
            'total_area': round(total, 2),
            'by_state': sorted(combined, key=lambda x: x['area'], reverse=True)
        }
        return JsonResponse(response_data)

    # 특정 state 선택 시 qs 필터 추가
    qs = qs.filter(crop_season__state__name=state)

    # 단일 state + variant 지정 → 전년도 포함 응답
    if variant:
        area = None
        last_area = None

        try:
            ts = qs.get(
                crop_season__year=year,
                variant=variant
            )
            area = round(ts.area, 2) if ts.area else None
        except TileSet.DoesNotExist:
            pass

        try:
            ts_last = qs.get(
                crop_season__year=last_year,
                variant=variant
            )
            last_area = round(ts_last.area, 2) if ts_last.area else None
        except TileSet.DoesNotExist:
            pass

        response_data = {
            'mode': 'single',
            'state': state,
            'variant': variant,
            'area': area,
            'last_year_area': last_area
        }
        return JsonResponse(response_data)

    # 단일 state 지정, variant 없음 → spring + winter 나눠서 표시
    if state and not variant:
        current = {}
        previous = {}

        for ts in qs.filter(crop_season__state__name=state):
            key = ts.variant or 'None'
            if ts.crop_season.year == year:
                current[key] = current.get(key, 0.0) + (ts.area or 0)
            elif ts.crop_season.year == last_year:
                previous[key] = previous.get(key, 0.0) + (ts.area or 0)

        parts = []
        for variant_key in current:
            cur = current.get(variant_key, 0.0)
            prev = previous.get(variant_key, 0.0)
            parts.append({
                'variant': variant_key,
                'area': round(cur, 2),
                'last_year_area': round(prev, 2),
                'diff': round(cur - prev, 2),
                'percent_change': round((cur - prev) / prev * 100, 1) if prev else None
            })

        response_data = {
            'mode': 'state_summary',
            'state': state,
            'areas': parts
        }
        return JsonResponse(response_data)


@require_GET
def country_boundaries(request):
    country_name = request.GET.get('country')

    if not country_name:
        return JsonResponse({'error': 'Missing country parameter'}, status=400)

    try:
        country = Country.objects.get(name=country_name)
    except Country.DoesNotExist:
        raise Http404("Country not found")

    full_path = country.boundary_path_cached
    if not os.path.exists(full_path):
        return JsonResponse({'error': f'GeoJSON file not found {full_path}'}, status=404)

    geojson_url = country.get_absolute_url()
    return JsonResponse({'geojson_url': geojson_url})


@require_GET
def state_boundary(request):
    state_name = request.GET.get('state')
    country_name = request.GET.get('country')

    if not state_name or not country_name:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        country = Country.objects.get(name=country_name)
    except Country.DoesNotExist:
        raise Http404("Country not found")

    full_path = country.boundary_path_cached
    if not os.path.exists(full_path):
        return JsonResponse({'error': 'GeoJSON file not found'}, status=404)

    return JsonResponse({
        "geojson_url": country.get_absolute_url(),
        "state": state_name
    })
