import os
import pandas as pd
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings

from .models import NirvRecord
from core.models import Crop, State


def sanitize_for_json(obj):
    """NaN, Infinity를 None으로 변환하고 numpy 수치를 파이썬 기본형으로 변환"""
    if isinstance(obj, (float, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    return obj


# 📄 전체 파일 경로 구성 함수
def build_full_path(relative_path):
    """
    DB에 저장된 경로(윈도우 백슬래시 포함 가능)를 리눅스에서도 올바르게 처리
    """
    if not relative_path:
        return None

    # 윈도우 백슬래시를 슬래시로 변환
    safe_path = str(relative_path).replace("\\", "/")

    # 드라이브 문자(Y:/...) 제거 후 항상 MEDIA_ROOT 기준으로 결합
    drive, tail = os.path.splitdrive(safe_path)
    safe_path = tail.lstrip("/")

    normalized = os.path.join(settings.MEDIA_ROOT, safe_path)
    return os.path.normpath(normalized)


# 🌐 기본 맵 페이지: crop만 미리 로딩 (나머지는 JS에서 동적 호출)
def nirv_map(request):
    crops = NirvRecord.objects.values_list('crop__name', flat=True).distinct().order_by('crop__name')
    return render(request, 'nirv/nirv_map.html', {
        'crops': crops,
    })

def compute_zscore_series(baseline_series_list, current_series):
    import numpy as np
    if not baseline_series_list or not current_series.any():
        return [], [], []

    baseline_df = pd.concat(baseline_series_list, axis=1)
    mean = baseline_df.mean(axis=1)
    std = baseline_df.std(axis=1)
    z = (current_series - mean) / std.replace(0, np.nan)

    bins = [-np.inf, -2, -1.5, -1, 1, 1.5, 2, np.inf]
    labels = [
        "Extremely bad", "Bad", "Poor", "Slightly below normal",
        "Slightly above normal", "Good", "Extremely good"
    ]
    z_class = pd.cut(z, bins=bins, labels=labels)
    z_class_num = z_class.cat.codes + 1  # 1~7

    return current_series.index.tolist(), z_class.tolist(), z_class_num.tolist()


@require_GET
def graph_data(request):
    crop_name = request.GET.get("crop")
    state_name = request.GET.get("state")
    year = request.GET.get("year")

    if not crop_name or not state_name or not year:
        return JsonResponse({"error": "Missing parameters"}, status=400)

    crop = Crop.objects.filter(name=crop_name).first()
    state = State.objects.filter(name=state_name).first()
    year = int(year)

    if not crop or not state:
        return JsonResponse({"error": "Invalid crop or state"}, status=400)

    # === 1. 평년 처리 === #
    avg_dfs = []
    for y in range(2018, 2025):
        record = NirvRecord.objects.filter(crop=crop, state=state, year=y).first()
        if record:
            fpath = build_full_path(record.file_path)
            if os.path.exists(fpath):
                df = pd.read_csv(fpath, index_col=0)
                avg_dfs.append(df.iloc[:, 0])  # 첫 번째 열만
            else:
                print(f"⚠️ [nirv.graph_data] File not found: {fpath}")

    if avg_dfs:
        df_all = pd.concat(avg_dfs, axis=1)
        df_all.columns = [str(y) for y in range(2018, 2018 + len(avg_dfs))]
        mean_series = df_all.mean(axis=1)
        std_series = df_all.std(axis=1)
        lower = (mean_series - 1.96 * std_series).replace([np.nan, np.inf, -np.inf], None).tolist()
        upper = (mean_series + 1.96 * std_series).replace([np.nan, np.inf, -np.inf], None).tolist()
        mean = mean_series.replace([np.nan, np.inf, -np.inf], None).tolist()
        x = df_all.index.tolist()
    else:
        mean, lower, upper, x = [], [], [], list(range(1, 366))

    # === 2. 전년도 === #
    last = NirvRecord.objects.filter(crop=crop, state=state, year=year - 1).first()
    last_y = []
    if last:
        fpath = build_full_path(last.file_path)
        if os.path.exists(fpath):
            df = pd.read_csv(fpath, index_col=0)
            last_y = df.iloc[:, 0].replace([np.nan, np.inf, -np.inf], None).tolist()
        else:
            print(f"⚠️ [nirv.graph_data] Last year file not found: {fpath}")

    # === 3. 올해 === #
    current = NirvRecord.objects.filter(crop=crop, state=state, year=year).first()
    current_y = []
    if current:
        fpath = build_full_path(current.file_path)
        if os.path.exists(fpath):
            df = pd.read_csv(fpath, index_col=0)
            current_y = df.iloc[:, 0].replace([np.nan, np.inf, -np.inf], None).tolist()
            print(f"✅ [nirv.graph_data] Current year file loaded: {fpath}")
        else:
            print(f"⚠️ [nirv.graph_data] Current year file not found: {fpath}")

    zscore_doy, zscore_class_label, zscore_class_num = [], [], []
    if avg_dfs and current_y:
        try:
            current_length = len(current_y)

            # baseline도 동일한 길이로 잘라냄
            clipped_baseline = [s.iloc[:current_length] for s in avg_dfs]

            # x 값도 자름
            current_x = x[:current_length]
            current_series = pd.Series(current_y, index=current_x)

            # Z-score 계산
            zscore_doy, zscore_class_label, zscore_class_num = compute_zscore_series(clipped_baseline, current_series)

        except Exception as e:
            print("❌ Z-score 계산 오류:", e)

    response_data = {
        "x": x,
        "mean": mean,
        "lower": lower,
        "upper": upper,
        "last": last_y,
        "current": current_y,
        "zscore_doy": zscore_doy,
        "zscore_class_num": zscore_class_num,
        "zscore_class_label": zscore_class_label,
    }

    # NaN 값을 None으로 변환
    return JsonResponse(response_data)



# 🔄 API: crop 선택 → 사용 가능한 연도 목록
@require_GET
def available_years(request):
    crop_name = request.GET.get("crop")
    crop = Crop.objects.filter(name=crop_name).first()
    if not crop:
        return JsonResponse({"years": []})

    years = NirvRecord.objects.filter(crop=crop).values_list("year", flat=True).distinct().order_by('-year')
    return JsonResponse({"years": list(years)})


# 🔄 API: crop + year 선택 → 사용 가능한 주(state) 목록
@require_GET
def available_states(request):
    crop_name = request.GET.get("crop")
    year = request.GET.get("year")

    crop = Crop.objects.filter(name=crop_name).first()
    if not crop or not year:
        return JsonResponse({"states": []})

    states = NirvRecord.objects.filter(crop=crop, year=year).values_list("state__name", flat=True).distinct().order_by('state__name')
    return JsonResponse({"states": list(states)})



@require_GET
def multi_graph_data(request):
    crop_name = request.GET.get("crop")
    year = request.GET.get("year")

    if not crop_name or not year:
        return JsonResponse({"error": "Missing crop or year"}, status=400)

    crop = Crop.objects.filter(name=crop_name).first()
    year = int(year)

    if not crop:
        return JsonResponse({"error": "Invalid crop"}, status=400)

    records = NirvRecord.objects.filter(crop=crop, year=year)
    states = records.values_list("state", flat=True).distinct()

    # 디버깅: 레코드 수 확인
    print(f"🔍 NIRv multi-graph: crop={crop_name}, year={year}, records={records.count()}, states={list(states)}")

    all_data = []

    for state_id in states:
        try:
            state = State.objects.get(pk=state_id)

            x = list(range(1, 366))
            avg_dfs = []

            # === baseline data ===
            for y in range(2018, 2024):
                record = NirvRecord.objects.filter(crop=crop, state=state, year=y).first()
                if record:
                    fpath = build_full_path(record.file_path)
                    if os.path.exists(fpath):
                        df = pd.read_csv(fpath, index_col=0)
                        avg_dfs.append(df.iloc[:, 0])
                        x = df.index
                    else:
                        print(f"⚠️ [nirv.multi_graph_data] Baseline file not found ({y}): {fpath}")

        # === 평년 평균/표준편차 계산 ===
            if avg_dfs:
                df_all = pd.concat(avg_dfs, axis=1)
                mean = df_all.mean(axis=1).replace([np.nan, np.inf, -np.inf], None).tolist()
                std = df_all.std(axis=1)
                lower = (df_all.mean(axis=1) - 1.96 * std).replace([np.nan, np.inf, -np.inf], None).tolist()
                upper = (df_all.mean(axis=1) + 1.96 * std).replace([np.nan, np.inf, -np.inf], None).tolist()
            else:
                mean, lower, upper = [], [], []

            # === 전년도 ===
            last = NirvRecord.objects.filter(crop=crop, state=state, year=year - 1).first()
            last_y = []
            if last:
                fpath = build_full_path(last.file_path)
                if os.path.exists(fpath):
                    df = pd.read_csv(fpath, index_col=0)
                    last_y = df.iloc[:, 0].replace([np.nan, np.inf, -np.inf], None).tolist()
                else:
                    print(f"⚠️ [nirv.multi_graph_data] Last year file not found: {fpath}")

            # === 올해 ===
            current = NirvRecord.objects.filter(crop=crop, state=state, year=year).first()
            current_y = []
            if current:
                fpath = build_full_path(current.file_path)
                if os.path.exists(fpath):
                    df = pd.read_csv(fpath, index_col=0)
                    current_y = df.iloc[:, 0].replace([np.nan, np.inf, -np.inf], None).tolist()
                    print(f"✅ [nirv.multi_graph_data] Current year file loaded ({state.name}): {fpath}")
                else:
                    print(f"⚠️ [nirv.multi_graph_data] Current year file not found ({state.name}): {fpath}")
            # 마지막 유효 DOY 계산
            last_sensing_doy = None
            if current_y:
                for idx in range(len(current_y) - 1, -1, -1):
                    val = current_y[idx]
                    if val is not None and not pd.isna(val):
                        # x_list는 current_x로 제한되어 있음
                        current_x = x[:len(current_y)]
                        raw_doy = current_x[idx] if idx < len(current_x) else idx + 1
                        last_sensing_doy = int(raw_doy)
                        break

            # === Z-score 계산 ===
            zscore_doy, zscore_class_label, zscore_class_num = [], [], []
            if avg_dfs and current_y:
                try:
                    current_length = len(current_y)
                    clipped_baseline = [s.iloc[:current_length] for s in avg_dfs]
                    current_x = x[:current_length]
                    current_series = pd.Series(current_y, index=current_x)
                    zscore_doy, zscore_class_label, zscore_class_num = compute_zscore_series(clipped_baseline, current_series)
                except Exception as e:
                    print(f"❌ Z-score 계산 오류 ({state.name}):", e)

            # x 값을 안전하게 변환
            x_list = []
            if hasattr(x, "tolist"):
                x_list = [int(val) if not pd.isna(val) else None for val in x.tolist()]
            elif isinstance(x, list):
                x_list = x
            else:
                x_list = list(range(1, 366))




            all_data.append({
                "state": state.name,
                "x": x_list,
                "mean": mean,
                "lower": lower,
                "upper": upper,
            "last": last_y,
            "current": current_y,
            "last_sensing_doy": last_sensing_doy,
            "zscore_doy": zscore_doy,
            "zscore_class_label": zscore_class_label,
            "zscore_class_num": zscore_class_num,
        })
        except Exception as e:
            print(f"[multi_graph_data] state {state_id} error: {e}")
            continue

    # 디버깅: 반환 데이터 확인
    print(f"✅ NIRv multi-graph: returning {len(all_data)} states")

    # NaN 값을 None으로 변환
    # return JsonResponse(sanitize_for_json(all_data), safe=False)

    return JsonResponse(sanitize_for_json(all_data), safe=False)

def nirv_map_multi(request):
    crops = NirvRecord.objects.values_list('crop__name', flat=True).distinct().order_by('crop__name')
    return render(request, 'nirv/nirv_map_multi.html', {
        'crops': crops,
    })
