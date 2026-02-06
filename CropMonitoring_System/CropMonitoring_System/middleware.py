# middleware.py
from django.shortcuts import redirect
from django.conf import settings
from django.urls import resolve

EXEMPT_URLS = [
    '/accounts/login/',
    '/accounts/signup/',
    '/admin/',
    '/static/',  # 정적 파일 접근 허용
]

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if (not request.user.is_authenticated
                and not any(path.startswith(exempt) for exempt in EXEMPT_URLS)):
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)
