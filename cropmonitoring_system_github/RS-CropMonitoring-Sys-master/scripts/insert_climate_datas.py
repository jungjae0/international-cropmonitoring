import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CropMonitoring_System.settings")
django.setup()

from core.models import Crop, State, CropSeason
from climate.models import ClimateData

# ------------------------------
# 설정
# ------------------------------
target_years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
states = ['Washington', 'Montana', 'Idaho', 'Oregon', 'Kansas', 'Oklahoma', 'Texas', 'Nebraska', 'Colorado']
crop_name = "Wheat"
variables = ['tmmx', 'srad', 'rmin', 'rmax', 'pr', 'tmmn']

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

        for variable in variables:
            safe_state_name = state_name.replace(" ", "_")
            csv_path = os.path.join(
                "Y:/DATA/CropMonitoring/USA/Climate/csv",
                str(year),
                variable,
                f"{variable}_{year}_{crop_name}_{safe_state_name}.csv"
            )

            if not os.path.exists(csv_path):
                print(f"[ ] 파일 없음: {csv_path}")
                continue

            climate_data, created = ClimateData.objects.get_or_create(
                crop_season=crop_season,
                variable=variable
            )

            climate_data.save()
            print(f"✅ {year} - {state_name} - {variable}: 등록 완료")
