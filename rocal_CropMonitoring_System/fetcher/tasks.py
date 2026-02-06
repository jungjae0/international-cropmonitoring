# fetcher/tasks.py

from celery import shared_task
from .scripts.download_nirv import download

@shared_task(bind=True)
def collect_data_nirv(self):
    try:
        pass
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        raise

@shared_task(bind=True)
def create_crop_mask(self):
    try:
        pass
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        raise