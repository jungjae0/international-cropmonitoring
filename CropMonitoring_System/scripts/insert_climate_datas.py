import os
import django

# Django 환경 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CropMonitoring_System.settings')
django.setup()

from core.models import Crop, State, CropSeason
from climate.models import ClimateCSV, ClimateImage
from django.db import transaction

# 설정 값
target_years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
north_state = ['Washington', 'Montana', 'Idaho', 'Oregon']
south_state = ['Kansas', 'Oklahoma', 'Texas', 'Nebraska', 'Colorado']
states = north_state + south_state
crop_name = "Wheat"

# Wheat 전용 variant
VARIANT_NONE = ''
VARIANT_SPRING = 'SpringWheat'
VARIANT_WINTER = 'WinterWheat'
VARIANTS = [VARIANT_SPRING, VARIANT_WINTER] if crop_name.lower() == 'wheat' else [VARIANT_NONE]

# 기상 변수 목록 (이미지 생성 기준)
variables = [
    'tmmx_daily',
    'tmmn_daily',
    'tmean_daily',
    'pr_daily',
    'pr_cumul'
]

@transaction.atomic
def populate_climate_data():
    crop = Crop.objects.get(name=crop_name)

    for year in target_years:
        for state_name in states:
            try:
                state = State.objects.get(name=state_name)
            except State.DoesNotExist:
                print(f"[SKIP] State '{state_name}' not found.")
                continue

            season, _ = CropSeason.objects.get_or_create(
                crop=crop,
                year=year,
                state=state
            )

            for variant in VARIANTS:
                # ClimateCSV 생성 및 존재 여부 확인
                csv_obj = ClimateCSV(season=season, variant=variant)
                csv_obj.save()
                if csv_obj.csv_path:
                    print(f"[CSV] 등록: {season} / {variant}")
                else:
                    csv_obj.delete()
                    print(f"[CSV] 없음: {season} / {variant} → 건너뜀")

                # ClimateImage 생성 및 존재 여부 확인
                for var in variables:
                    img_obj = ClimateImage(season=season, variant=variant, variable=var)
                    img_obj.save()
                    if img_obj.image_path:
                        print(f"[IMG] 등록: {season} / {variant} / {var}")
                    else:
                        img_obj.delete()
                        print(f"[IMG] 없음: {season} / {variant} / {var} → 건너뜀")

if __name__ == "__main__":
    populate_climate_data()
