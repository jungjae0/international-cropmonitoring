from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('new/', views.create_job, name='create_job'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('<int:job_id>/status/', views.job_status_api, name='job_status_api'),
    path('<int:job_id>/download/', views.download_tif, name='download_tif'),
    path('map/', views.overall_map_view, name='overall_map'),

]
