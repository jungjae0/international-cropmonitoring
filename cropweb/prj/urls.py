# """
# URL configuration for prj project.
#
# The `urlpatterns` list routes URLs to views. For more information please see:
#     https://docs.djangoproject.com/en/5.1/topics/http/urls/
# Examples:
# Function views
#     1. Add an import:  from my_app import views
#     2. Add a URL to urlpatterns:  path('', views.home, name='home')
# Class-based views
#     1. Add an import:  from other_app.views import Home
#     2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
# Including another URLconf
#     1. Import the include() function: from django.urls import include, path
#     2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
# """
# #
# # from django.contrib import admin
# # from django.urls import path, include
# #
# # urlpatterns = [
# #     path('admin/', admin.site.urls),
# #     path('', include('satellite_data.urls')),
# #     path('', include('data_collection.urls')),
# # ]
#
# from django.contrib import admin
# from django.urls import path, include
# from django.urls import path
# from django.http import HttpRequest
# from fastapi.middleware.wsgi import WSGIMiddleware
#
# from django.views.decorators.csrf import csrf_exempt
#
#
# from crop_monitor.app import app as crop_monitor_app
#
# # FastAPI를 WSGI로 변환
# fastapi_wsgi = WSGIMiddleware(crop_monitor_app)
#
# # Django 뷰로 FastAPI 실행
# def fastapi_view(request: HttpRequest, *args, **kwargs):
#     return fastapi_wsgi(request.environ, lambda status, headers: None)
#
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('satellite_data.urls')),
#     path('', include('data_collection.urls')),
#     path("crop_monitoring/", csrf_exempt(fastapi_view)),
# ]
#
#


from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
app_name = "dbms"  # Django의 namespace를 설정 (선택 사항)
urlpatterns = [
    path('admin/', admin.site.urls),  # Django 관리 페이지 경로 수정
    path('', include('satellite_data.urls')),  # Django 앱 연결
    path('', include('data_collection.urls')),  # Django 앱 연결
]


urlpatterns += static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)
