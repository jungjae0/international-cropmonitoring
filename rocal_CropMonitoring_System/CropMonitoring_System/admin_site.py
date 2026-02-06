# config/admin_site.py (원하는 위치에 새 파일)
from django.contrib.admin import AdminSite

APP_ORDER = [
    "accounts",
    "django_celery_beat",
    "django_celery_results",
    "fetcher",
    "core",
    "area",
    "nirv",
]


class MyAdminSite(AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)

        # 앱 순서 강제
        order_index = {label: i for i, label in enumerate(APP_ORDER)}
        def app_key(app):
            return order_index.get(app["app_label"], 10_000)

        app_list.sort(key=app_key)

        # (선택) 모델 이름 기준으로 정렬
        for app in app_list:
            app["models"].sort(key=lambda m: m["name"])
        return app_list

my_admin_site = MyAdminSite()
