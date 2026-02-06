from django.urls import path
from . import views

urlpatterns = [
    path('', views.climate_view, name='climate_view'),  # 기본 crop 리스트
    path('api/options/', views.get_climate_options, name='get_climate_options'),
    path('api/data/', views.get_climate_data, name='get_climate_data'),
]
