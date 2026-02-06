from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from .admin_site import my_admin_site        # 경로는 실제 위치에 맞게
from .admin_autoregister import *            # 이 줄이 admin 모듈을 강제로 로드/이관

urlpatterns = [
                  # 루트 URL을 /area로 리다이렉트
                  path('', RedirectView.as_view(url='/area/', permanent=False), name='home'),

                  path('admin/', my_admin_site.urls),
                  # path('maps/', include('maps.urls')),
                  path('area/', include('area.urls')),
                  path('nirv/', include('nirv.urls')),

                  path('accounts/login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
                  path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
                  path('accounts/signup/', include('accounts.urls')),
              ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)
