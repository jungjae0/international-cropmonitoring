# insert_croparea_datas.py

import os
import sys
import csv
import django
import pandas as pd
from decimal import Decimal

# ──────────────────────────────────────────────────────────────────────────────
# 1) Django 세팅 (프로젝트에 맞게 수정)
# ──────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CropMonitoring_System.settings")
django.setup()

from core.models import CropSeason
from maps.models import TileSet



# ────────────────────────────────────────────────────────────────
# 3) 헬퍼 함수
# ────────────────────────────────────────────────────────────────
def parse_variant(crop_name: str) -> str:
    """
    'Spring Wheat' → 'SpringWheat', 'Winter Wheat' → 'WinterWheat'
    그 외는 '' 반환
    """
    key = crop_name.strip().lower().replace(' ', '')
    if key == 'springwheat':
        return 'SpringWheat'
    if key == 'winterwheat':
        return 'WinterWheat'
    return ''

def acres_to_m2(acres_str: str) -> float:
    """
    '12,345.67' 같은 문자열을 Decimal로 파싱해
    m² 로 환산 (1 acre = 4046.8564224 m²)
    """
    num = Decimal(str(acres_str).replace(',', '').strip())
    return float(acres_str.replace(',', '').strip())

# ────────────────────────────────────────────────────────────────
# 4) 메인 로직
# ────────────────────────────────────────────────────────────────
def main(csv_path: str):
    if not os.path.exists(csv_path):
        print(f"[ERROR] 파일을 찾을 수 없습니다: {csv_path}")
        sys.exit(1)

    # 파일명에서 연도 추출 (예: '2018_log.csv' → year=2018)
    fname = os.path.basename(csv_path)
    try:
        year = int(fname.split('_')[0])
    except ValueError:
        print("[ERROR] 파일명에서 연도를 파싱할 수 없습니다. 'YYYY_...' 형식이어야 합니다.")
        sys.exit(1)

    # pandas로 CSV 읽기: State, Crop, Area (acres) 세 컬럼만
    df = pd.read_csv(
        csv_path,
        header=0,
        usecols=[0, 1, 2],
        names=['State', 'Crop', 'Area_acres'],
        dtype={'State': str, 'Crop': str, 'Area_acres': str}
    )

    updated = skipped = 0

    for idx, row in df.iterrows():
        state_name = row['State'].strip()
        crop_raw   = row['Crop'].strip()
        area_str   = row['Area_acres'].strip()

        # 면적 → m²
        try:
            area_m2 = acres_to_m2(area_str)
        except Exception as e:
            print(f"[WARNING] {idx+2}행: 면적 변환 실패('{area_str}'): {e}")
            skipped += 1
            continue

        # CropSeason 조회 (wheat 고정)
        try:
            season = CropSeason.objects.get(
                crop__name__iexact='wheat',
                year=year,
                state__name__iexact=state_name
            )
        except CropSeason.DoesNotExist:
            print(f"[WARNING] {idx+2}행: CropSeason 없음(wheat, {year}, {state_name})")
            skipped += 1
            continue

        # variant 결정
        variant = parse_variant(crop_raw)

        if area_m2 == 0:
            continue

        # TileSet 생성/업데이트
        ts, created = TileSet.objects.get_or_create(
            crop_season=season,
            variant=variant,
            defaults={'area': area_m2}
        )
        if not created:
            ts.area = area_m2
            ts.save()

        verb = "생성" if created else "업데이트"
        print(f"[{verb}] {year} | {state_name} / {variant or 'Default'} → {area_m2:,.2f} acres")
        updated += 1

    print(f"\n완료: {updated}건 처리, {skipped}건 스킵")
if __name__ == '__main__':

    for year in [2024]:
        main(rf"Y:\DATA\CropMonitoring\USA\GEE\Cropmap_color\Wheat\{year}_Wheat_log.csv")  # CSV 파일 경로를 여기에 지정
