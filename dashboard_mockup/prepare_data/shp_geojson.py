import geopandas as gpd

# Shapefile 파일 경로
shp_file = "./data/GEOGLAM_CM4EW_Calendars_V1.0.shp"

# Shapefile을 읽기
gdf = gpd.read_file(shp_file)

# GeoJSON으로 저장
geojson_file = "../static/crop_calendar.geojson"
gdf.to_file(geojson_file, driver="GeoJSON")

print(f"GeoJSON 파일이 저장되었습니다: {geojson_file}")
