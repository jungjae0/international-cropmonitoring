from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET
from core.models import Crop, Country, State, CropSeason
from .models import ClimateData
import pandas as pd
from django.shortcuts import render

def climate_view(request):
    crops = Crop.objects.all().values_list('name', flat=True).distinct()
    return render(request, 'climate/climate_view.html', {'crops': crops})

@require_GET
def get_climate_options(request):
    crop = request.GET.get('crop')
    year = request.GET.get('year')
    country = request.GET.get('country')
    state = request.GET.get('state')

    if crop and not year:
        years = CropSeason.objects.filter(crop__name=crop).values_list('year', flat=True).distinct()
        return JsonResponse({'years': sorted(set(years))})

    if crop and year and not country:
        countries = Country.objects.filter(
            states__cropseason__crop__name=crop,
            states__cropseason__year=year
        ).distinct().values_list('name', flat=True)
        return JsonResponse({'countries': list(countries)})

    if crop and year and country and not state:
        states = State.objects.filter(
            country__name=country,
            cropseason__crop__name=crop,
            cropseason__year=year
        ).distinct().values_list('name', flat=True)
        return JsonResponse({'states': list(states)})

    if crop and year and country and state:
        try:
            crop_season = CropSeason.objects.get(
                crop__name=crop,
                year=year,
                state__name=state,
                state__country__name=country
            )
        except CropSeason.DoesNotExist:
            return JsonResponse({'variables': []})

        variables = ClimateData.objects.filter(
            crop_season=crop_season
        ).values_list('variable', flat=True).distinct()

        return JsonResponse({'variables': list(variables)})

    return JsonResponse({'error': 'Invalid parameters'}, status=400)


@require_GET
def get_climate_data(request):
    crop = request.GET.get('crop')
    year = request.GET.get('year')
    country = request.GET.get('country')
    state = request.GET.get('state')
    variable = request.GET.get('variable')

    if not all([crop, year, country, state, variable]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        year = int(year)
        crop_season_now = CropSeason.objects.get(
            crop__name=crop,
            year=year,
            state__name=state,
            state__country__name=country
        )
        climate_now = ClimateData.objects.get(crop_season=crop_season_now, variable=variable)
    except (CropSeason.DoesNotExist, ClimateData.DoesNotExist):
        return JsonResponse({'error': 'Current year data not found'}, status=404)

    # 현재 연도 데이터 불러오기
    def read_csv_data(climate_obj):
        if not climate_obj.exists():
            return None, None
        try:
            df = pd.read_csv(climate_obj.csv_path_cached)
            date_col = 'date' if 'date' in df.columns else df.columns[0]
            value_col = [col for col in df.columns if 'mask1' in col]
            value_col = value_col[0] if value_col else df.columns[1]
            return df[date_col].tolist(), df[value_col].tolist()
        except Exception as e:
            return None, None

    date_now, value_now = read_csv_data(climate_now)

    # 이전 연도 데이터 (없어도 무방)
    try:
        crop_season_prev = CropSeason.objects.get(
            crop__name=crop,
            year=year - 1,
            state__name=state,
            state__country__name=country
        )
        climate_prev = ClimateData.objects.get(crop_season=crop_season_prev, variable=variable)
        date_prev, value_prev = read_csv_data(climate_prev)
    except (CropSeason.DoesNotExist, ClimateData.DoesNotExist):
        date_prev, value_prev = [], []

    return JsonResponse({
        'crop': crop,
        'state': state,
        'country': country,
        'variable': variable,
        'current_year': year,
        'previous_year': year - 1,
        'data': {
            'current': {'date': date_now, 'value': value_now},
            'previous': {'date': date_prev, 'value': value_prev}
        }
    })






# @require_GET
# def get_climate_data(request):
#     crop = request.GET.get('crop')
#     year = request.GET.get('year')
#     country = request.GET.get('country')
#     state = request.GET.get('state')
#     variable = request.GET.get('variable')
#
#     if not all([crop, year, country, state, variable]):
#         return JsonResponse({'error': 'Missing parameters'}, status=400)
#
#     try:
#         crop_season = CropSeason.objects.get(
#             crop__name=crop,
#             year=year,
#             state__name=state,
#             state__country__name=country
#         )
#         climate = ClimateData.objects.get(crop_season=crop_season, variable=variable)
#     except (CropSeason.DoesNotExist, ClimateData.DoesNotExist):
#         return JsonResponse({'error': 'Climate data not found'}, status=404)
#
#     if not climate.exists():
#         return JsonResponse({'error': 'CSV file not found'}, status=404)
#
#     try:
#         df = pd.read_csv(climate.csv_path_cached)
#     except Exception as e:
#         return JsonResponse({'error': f'CSV read error: {e}'}, status=500)
#
#     date_col = 'date' if 'date' in df.columns else df.columns[0]
#     value_col = [col for col in df.columns if 'mask1' in col][0] if any('mask1' in col for col in df.columns) else df.columns[1]
#     # value_col은 mask1을 컬럼명에 포함한 열
#
#
#     return JsonResponse({
#         'crop': crop,
#         'year': year,
#         'state': state,
#         'country': country,
#         'variable': variable,
#         'data': {
#             'date': df[date_col].tolist(),
#             'value': df[value_col].tolist()
#         }
#     })
