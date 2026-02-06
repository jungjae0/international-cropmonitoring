from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_view, name='tile_upload'),
    path('list/', views.list_view, name='tile_list'),
    path('result/<int:tif_id>/', views.result_view, name='tile_result'),
    path('delete/<int:tif_id>/', views.delete_view, name='tile_delete'),
]
