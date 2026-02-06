"""
URL configuration for datamanager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from users.views import signup, redirect_after_login  # 직접 만드는 회원가입 뷰
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
                  path('admin/', admin.site.urls),

                  # 로그인/로그아웃
                  path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
                  path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

                  # 회원가입
                  path('accounts/signup/', signup, name='signup'),

                  # 앱들
                  # path('jobs/', include('jobs.urls')),
                  path('uploadtif/', include('tileupload.urls')),

                  path('', redirect_after_login, name='redirect_after_login'),

                  path('', lambda request: redirect('redirect_after_login'), name='home'),

              ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)
