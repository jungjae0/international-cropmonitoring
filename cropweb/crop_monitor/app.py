from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from fastapi import FastAPI, Query
import os
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
templates = Jinja2Templates(directory="frontend")
from pathlib import Path

app = FastAPI(root_path="/cropmonitor")

# 현재 파일(app.py)의 디렉토리 경로 설정
BASE_DIR = Path(__file__).parent

# 정적 파일 및 템플릿 폴더 설정 (절대 경로 사용)
app.mount("/crop_monitor/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSV 파일 읽기 (절대 경로 사용)
df = pd.read_csv(BASE_DIR / "static/crop_calendar.csv")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(BASE_DIR / "templates/index.html", encoding='UTF8') as f:
        return f.read()

@app.get("/crop_monitoring/countries")
async def get_countries():
    countries = df['country'].unique().tolist()
    return JSONResponse(countries)

@app.get("/crop_monitoring/regions")
async def get_regions(country: str):
    regions = df[df['country'] == country]['region'].unique().tolist()
    return JSONResponse(regions)

@app.get("/crop_monitoring/crops")
async def get_crops(country: str, region: str):
    crops = df[(df['country'] == country) & (df['region'] == region)]['crop'].unique().tolist()
    return JSONResponse(crops)


@app.get("/crop_monitoring/year-range")
async def get_years():
    years = list(range(2016, 2025))
    return JSONResponse(years)

@app.get("/crop_monitoring/elements")  # Correct the endpoint name here
async def get_elements():
    elements = [
        'leaf_area_index_high_vegetation',
        'leaf_area_index_low_vegetation',
        'soil_temperature_level_1',
        'soil_temperature_level_2',
        'surface_latent_heat_flux_sum',
        'surface_net_solar_radiation_sum',
        'temperature_2m',
        'total_precipitation_sum',
        'volumetric_soil_water_layer_1',
        'volumetric_soil_water_layer_2'
    ]
    return JSONResponse(elements)

@app.get("/crop_monitoring/filter_data")
async def filter_data(
    country: str,
    region: str,
    crop: str,
    element: str,
    start_year: int = Query(...),  # 시작 연도
    end_year: int = Query(...),      # 끝 연도
):

    files = [f for f in os.listdir("./weather") if f"{crop}_{country}_{region}" in f]
    filtered_files = []
    for file in files:
        if start_year <= int(file.split('_')[-1].split('.')[0]) <= end_year:
            year_df = pd.read_csv(os.path.join("./weather", file))
            year_df['total_precipitation_sum'] = year_df['total_precipitation_sum'].cumsum()
            filtered_files.append(year_df)


    filtered_df = pd.concat(filtered_files)

    filtered_df['date'] = pd.to_datetime(filtered_df['date'])
    filtered_df['year'] = filtered_df['date'].dt.year
    filtered_df['doy'] = filtered_df['date'].dt.dayofyear  # Day of Year 계산

    doy_lst = ['planting','vegetative','harvest','endofseaso','outofseaso']
    data = filtered_df[['doy', element, 'year']].to_dict(orient='records')

    response = {
        'data': data,
    }
    for doy in doy_lst:
        response[doy] = int(filtered_df[doy].unique()[0])

    return JSONResponse(response)

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(app, port=7000)
