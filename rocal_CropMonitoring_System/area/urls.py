from django.urls import path
from . import views

urlpatterns = [
    # 지도 화면은 로그인 필요하지만, API는 공개로 두어 프런트 fetch 302(로그인 리다이렉트) 문제를 방지
    path("", views.area_map, name="area_map"),
    path("api/choropleth/", views.api_choropleth, name="api_choropleth"),
    path("api/available-years/", views.api_available_years, name="api_available_years"),
]
