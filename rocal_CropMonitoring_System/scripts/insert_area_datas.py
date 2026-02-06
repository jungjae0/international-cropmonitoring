import os

import pandas as pd
# import geopandas as gpd

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CropMonitoring_System.settings")
django.setup()

from core.models import State, Crop, CropSeason
from area.models import CultivatedArea


crop_values= ['Corn', 'Soybean']# , 'Wheat_Spring', 'Wheat_Winter' 'Corn', 'Soybean'

for crop_value in crop_values:
    # for year in range(2024, 2026):
    year = 2025


    df_path = rf"Y:\DATA\CropMonitoring\utilization\crop\area\SOY\USA\v1\area_2025_10_31_new.csv"
    df = pd.read_csv(df_path)
    df = df[df['cls'] == 1]
    # print(df)

    for _, row in df.iterrows():
        year = year
        state_name = row['state_name'].replace(" ", "_").capitalize()
        if state_name.endswith("akota") and state_name.startswith("N"):
            state_name = "North_Dakota"
        elif state_name.endswith("akota") and state_name.startswith("S"):
            state_name = "South_Dakota"

        crop_name = crop_value
        area = float(row['area_acre'])

        try:
            state = State.objects.get(name=state_name)
            crop = Crop.objects.get(name=crop_name)
        except (State.DoesNotExist, Crop.DoesNotExist) as e:
            print(f"❌ 누락: {e}")
            continue

        crop_season, _ = CropSeason.objects.get_or_create(
            crop=crop, state=state, year=year
        )
        CultivatedArea.objects.update_or_create(
            crop_season=crop_season,
            defaults={'area_acres': area}
        )