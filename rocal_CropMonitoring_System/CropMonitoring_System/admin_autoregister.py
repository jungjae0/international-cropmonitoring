# config/admin_autoregister.py (새 파일)
from django.contrib import admin as django_admin
from .admin_site import my_admin_site

# 모든 admin 모듈 import (각 앱의 @admin.register가 먼저 실행되도록)
django_admin.autodiscover()

# 기본 사이트에 등록된 ModelAdmin를 커스텀 사이트로 이관
for model, model_admin in django_admin.site._registry.items():
    # 동일한 ModelAdmin 클래스로 재등록
    my_admin_site.register(model, model_admin.__class__)