from django.urls import path
from . import views

urlpatterns = [
    path('', views.map_view, name='map_view'),
    path('api/options/', views.get_tile_options, name='get_tile_options'),
    path('api/tile-url/', views.get_tile_url, name='get_tile_url'),
    path('api/country-zoom/', views.get_country_tiles, name='get_country_tiles'),
    path('api/area-summary/', views.area_summary, name='area_summary'),
    path('api/boundaries/', views.country_boundaries, name='country_boundaries'),
    path('api/state-boundary/', views.state_boundary, name='state_boundary'),
]
