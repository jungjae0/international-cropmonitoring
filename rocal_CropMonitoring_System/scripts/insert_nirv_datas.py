import os
import re

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CropMonitoring_System.settings")
django.setup()

from django.conf import settings
from nirv.models import NirvRecord
from core.models import Country, State, Crop

# 경로 정의
nirv_root = os.path.join(settings.MEDIA_ROOT, "USA", "GEE", "Monitoring", "NIRv")
country = Country.objects.get(iso_code="USA")  # 국가 고정

# 정규식으로 파일명에서 정보 추출
pattern = re.compile(r"^(?P<state>.+)_(?P<crop>.+)_(?P<year>\d{4})_smoothed\.csv$")


count = 0

for crop_dir in os.listdir(nirv_root):
    crop_path = os.path.join(nirv_root, crop_dir, "Smoothed")
    if not os.path.isdir(crop_path):
        continue

    for state_dir in os.listdir(crop_path):
        state_path = os.path.join(crop_path, state_dir)
        if not os.path.isdir(state_path):
            continue

        for fname in os.listdir(state_path):
            match = pattern.match(fname)
            if not match:
                continue
            state_name = state_dir
            crop_name = crop_dir
            year = int(match["year"])

            relative_path = os.path.relpath(
                os.path.join(state_path, fname),
                start=settings.MEDIA_ROOT
            )

            try:
                state = State.objects.get(name=state_name)
                crop = Crop.objects.get(name=crop_name)
            except (State.DoesNotExist, Crop.DoesNotExist):
                print(f"❌ Skipping (state/crop not found): {state_name}, {crop_name}")
                continue

            # 중복 등록 방지
            obj, created = NirvRecord.objects.get_or_create(
                country=country,
                state=state,
                crop=crop,
                year=year,
                defaults={"file_path": relative_path}
            )
            if created:
                count += 1
                print(f"✅ Registered: {relative_path}")

print(f"\n🎉 등록 완료: {count}건")
