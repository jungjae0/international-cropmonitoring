import os

import django
from django.apps import apps


def ensure_django_setup() -> None:
    if not apps.ready:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
