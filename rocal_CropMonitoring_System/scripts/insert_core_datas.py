import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CropMonitoring_System.settings")
django.setup()

from core.models import Country, State, Crop, CropSeason

# # 기본 설정
crop_name = "Wheat_Spring"

# import os

base_dir = rf"Y:\DATA\CropMonitoring\USA\GEE\Cropmap\{crop_name}\2024"
states = [file.replace(f"2024_Wheat_", "").replace(".tif", "") for file in os.listdir(base_dir) if file.endswith(".tif")]
target_years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

# crop_name = "Corn"

state_centers = {
    'Ohio': (40.4, -82.8),
    'Illinois': (40.0, -89.0),
    'North_Dakota': (47.5, -100.5),
    'Iowa': (42.1, -93.5),
    'Minnesota': (46.0, -94.0),
    'Missouri': (38.5, -92.5),
    'Indiana': (39.8, -86.2),
    'South_Dakota': (44.4, -100.2),
    'Wisconsin': (44.5, -89.5),
    'Kansas': (38.5, -98.0),
    'Arkansas': (34.9, -92.3),
    'Nebraska': (41.5, -99.5),
    'Washington': (47.5, -120.5),
    'Montana': (47.0, -110.0),
    'Idaho': (44.2, -114.0),
    'Oregon': (44.0, -120.5),
    'Oklahoma': (35.5, -97.5),
    'Texas': (31.0, -100.0),
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
