# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.log_view, name='log_view'),
]