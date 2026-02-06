from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET
from .models import TileSet
from core.models import Country, State, Crop, CropSeason
import os


def map_view(request):
    crops = Crop.objects.all().values_list('name', flat=True).distinct()
    return render(request, 'maps/map_view.html', {'crops': crops})


def get_tile_options(request):
    crop = request.GET.get('crop')
    year = request.GET.get('year')
    country = request.GET.get('country')

    if crop and not year:
        years = CropSeason.objects.filter(crop__name=crop).values_list('year', flat=True).distinct()
        return JsonResponse({'years': sorted(set(years))})

    if crop and year and not country:
        countries = Country.objects.filter(
            states__cropseason__crop__name=crop,
            states__cropseason__year=year
        ).distinct().values_list('name', flat=True)
        return JsonResponse({'countries': list(countries)})

    if crop and year and country:
        states = State.objects.filter(
            country__name=country,
            cropseason__crop__name=crop,
            cropseason__year=year
        ).distinct().values_list('name', flat=True)
        return JsonResponse({'states': list(states)})

    return JsonResponse({'error': 'Invalid parameters'}, status=400)


def get_tile_url(request):
    crop = request.GET.get('crop')
    year = request.GET.get('year')
    country = request.GET.get('country')
    state = request.GET.get('state')

    try:
        tileset = TileSet.objects.select_related('crop_season__state__country', 'crop_season__crop').get(
            crop_season__crop__name=crop,
            crop_season__year=year,
            crop_season__state__name=state,
            crop_season__state__country__name=country
        )
        return JsonResponse({'tile_url': tileset.get_tile_url()})
    except TileSet.DoesNotExist:
        return JsonResponse({'error': 'No tileset found'}, status=404)


def get_country_tiles(request):
    crop = request.GET.get('crop')
    year = request.GET.get('year')
    country_name = request.GET.get('country')

    try:
        country = Country.objects.get(name=country_name)
        states = State.objects.filter(country=country)

        tilesets = TileSet.objects.select_related('crop_season__state').filter(
            crop_season__crop__name=crop,
            crop_season__year=year,
            crop_season__state__in=states
        )

        tile_data = [
            {
                'state': ts.crop_season.state.name,
                'tile_url': ts.get_tile_url(),
                'center_lat': ts.crop_season.state.center_lat,
                'center_lng': ts.crop_season.state.center_lng
            }
            for ts in tilesets
        ]

        return JsonResponse({
            'country_center': {
                'lat': country.center_lat,
                'lng': country.center_lng
            },
            'tiles': tile_data
        })

    except Country.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)


def area_summary(request):
    crop = request.GET.get('crop')
    year = request.GET.get('year')
    country = request.GET.get('country')
    state = request.GET.get('state')

    tilesets = TileSet.objects.select_related('crop_season__state').filter(
        crop_season__crop__name=crop,
        crop_season__year=year,
        crop_season__state__country__name=country
    )

    if not state or state == "전체":
        result = []
        total_area = 0
        for ts in tilesets:
            if ts.area is not None:
                result.append({
                    'state': ts.crop_season.state.name,
                    'area': ts.area
                })
                total_area += ts.area

        return JsonResponse({
            'mode': 'summary',
            'total_area': round(total_area, 2),
            'by_state': sorted(result, key=lambda x: x['area'], reverse=True)
        })

    else:
        ts = tilesets.filter(crop_season__state__name=state).first()
        if ts and ts.area is not None:
            return JsonResponse({
                'mode': 'single',
                'state': ts.crop_season.state.name,
                'area': round(ts.area, 2)
            })
        else:
            return JsonResponse({
                'mode': 'single',
                'state': state,
                'area': None
            })


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
