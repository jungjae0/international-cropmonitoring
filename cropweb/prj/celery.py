# from __future__ import absolute_import, unicode_literals
# import os
# from celery import Celery
#
# # Django 설정 모듈 환경 변수 설정
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj.settings')
#
# app = Celery('prj')
#
# # Django 설정에서 Celery 설정 불러오기
# app.config_from_object('django.conf:settings', namespace='CELERY')
#
# # 자동으로 tasks.py를 검색
# app.autodiscover_tasks()
#
# @app.task(bind=True)
# def debug_task(self):
#     print(f'Request: {self.request!r}')



from __future__ import absolute_import, unicode_literals
import sys
from kombu.utils import encoding
sys.modules['celery.utils.encoding'] = encoding

import os, django
from celery import Celery
from datetime import timedelta
from django.conf import settings
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj.settings')

app = Celery('prj', include=['prj.tasks'])
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_RESULT_SERIALIZER='json',
    CELERY_TIMEZONE='Asia/Seoul',
    CELERY_ENABLE_UTC=False,
    CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler',
)

django.setup()


app.autodiscover_tasks()
if __name__ == '__main__':
    app.start()