from __future__ import absolute_import, unicode_literals

# Celery 애플리케이션을 임포트하여 Django가 항상 Celery를 로드하도록 함
from .celery import app as celery_app

__all__ = ('celery_app',)