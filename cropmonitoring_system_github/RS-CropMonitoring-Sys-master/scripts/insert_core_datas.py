import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CropMonitoring_System.settings")
django.setup()

from core.models import Country, State, Crop, CropSeason

# 기본 설정
target_years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
north_state = ['Washington', 'Montana', 'Idaho', 'Oregon']
south_state = ['Kansas', 'Oklahoma', 'Texas', 'Nebraska', 'Colorado']
states = north_state + south_state
crop_name = "Wheat"

# 중심 좌표
state_centers = {
    'Washington': (47.5, -120.5),
    'Montana': (47.0, -110.0),
    'Idaho': (44.2, -114.0),
    'Oregon': (44.0, -120.5),
    'Kansas': (38.5, -98.0),
    'Oklahoma': (35.5, -97.5),
    'Texas': (31.0, -100.0),
    'Nebraska': (41.5, -99.5),
    'Colorado': (39.0, -105.5),
}

# Country 생성 또는 가져오기
country, _ = Country.objects.get_or_create(
    name="United States",
    iso_code="USA",
    defaults={"center_lat": 39.8283, "center_lng": -98.5795}
)

# Crop 생성 또는 가져오기
crop, _ = Crop.objects.get_or_create(name=crop_name)

created_states = 0
created_seasons = 0

for state_name in states:
    lat, lng = state_centers[state_name]
    state, state_created = State.objects.get_or_create(
        name=state_name,
        country=country,
        defaults={"center_lat": lat, "center_lng": lng}
    )
    if state_created:
        created_states += 1

    for year in target_years:
        crop_season, season_created = CropSeason.objects.get_or_create(
            crop=crop,
            year=year,
            state=state
        )
        if season_created:
            created_seasons += 1

print(f"{created_states}개 State 생성")
print(f"{created_seasons}개 CropSeason 생성")
