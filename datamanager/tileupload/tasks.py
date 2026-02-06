from celery import shared_task
from .models import UploadedTif
from .utils import run_gdal2tiles
import os
from django.conf import settings
import time

@shared_task(bind=True)
def process_uploaded_tif(self, tif_id, input_path, output_path, label_data):
    tif = UploadedTif.objects.get(id=tif_id)

    try:
        tif.status = 'processing'
        tif.save()

        run_gdal2tiles(input_path, output_path, label_data)

        # for i in range(0, 100, 10):
        #     time.sleep(0.5)
            # job.progress = i
            # job.save()


        tif.status = 'success'

    except Exception as e:
        print(f"🔥 Celery Task Error: {e}")
        tif.status = 'failed'
        tif.error_message = str(e)

    finally:
        # ✅ 작업 완료 후 tif 파일 삭제
        if os.path.exists(input_path):
            os.remove(input_path)
        tif.save()
