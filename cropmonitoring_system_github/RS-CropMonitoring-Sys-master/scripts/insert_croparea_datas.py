import os
import django
import rasterio
import numpy as np

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CropMonitoring_System.settings")
django.setup()

from core.models import Crop, State, CropSeason
from maps.models import TileSet

# ------------------------------
# 설정
# ------------------------------
target_years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
states = ['Washington', 'Montana', 'Idaho', 'Oregon', 'Kansas', 'Oklahoma', 'Texas', 'Nebraska', 'Colorado']
crop_name = "Wheat"

# 면적 계산 함수
def calculate_area(raster_path):
    try:
        with rasterio.open(raster_path) as src:
            band = src.read(1)
            count = np.count_nonzero(band != 0)
            area_acres = (count * 20 * 20) / 4047
            return area_acres
    except Exception as e:
        print(f"[!] 오류 발생: {raster_path} → {e}")
        return None

# ------------------------------
# 삽입
# ------------------------------
crop = Crop.objects.get(name=crop_name)

for year in target_years:
    for state_name in states:
        try:
            state = State.objects.get(name=state_name)
            crop_season = CropSeason.objects.get(crop=crop, year=year, state=state)
        except CropSeason.DoesNotExist:
            print(f"[ ] 누락: {year} - {state_name} → CropSeason 없음")
            continue

        raster_path = f"Y:/DATA/CropMonitoring/USA/GEE/Cropmap/{crop_name}/{year}/{year}_{crop_name}_{state_name}.tif"
        area = calculate_area(raster_path)
        if area is None:
            continue

        tileset, created = TileSet.objects.get_or_create(
            crop_season=crop_season,
            defaults={'area': area}
        )

        if not created:
            tileset.area = area
            tileset.save()

        print(f"✅ {year} - {state_name}: 면적 {area:.2f} acres 등록 완료.")
