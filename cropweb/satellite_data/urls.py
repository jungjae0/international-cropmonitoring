# urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('files/', views.file_list, name='file_list'),
    path('download_zip/', views.download_zip, name='download_zip'),
    path('download/<int:record_id>/', views.download_file, name='download_file'),
]


# urlpatterns = [
#     path('download/<int:record_id>/', views.download_file, name='download_file'),
# ]
#
# urlpatterns += [
#     path('files/', views.file_list, name='file_list'),
# ]