from django.contrib import admin
from django.urls import include, path

from core import views


urlpatterns = [
    path("", views.dashboard, name="home"),
    path("admin/", admin.site.urls),
    path("core/", include("core.urls")),
]
