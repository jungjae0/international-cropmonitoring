from celery import shared_task, chain
from .models import Job
import time
# from .modules import gee_exporter, inference, generate_maptile
import sys
from django.conf import settings
import os
# 1. 데이터 다운로드 Task
@shared_task(bind=True)
def download_data(self, job_id):
    import time
    import ee

    job = Job.objects.get(id=job_id)

    try:
        job.status = 'running'
        job.current_step = 'downloading'
        job.progress = 0
        job.save()


        for i in range(0, 100, 10):
            time.sleep(0.5)
            job.progress = i
            job.save()

        # task = gee_exporter.run(job.year, job.region)
        #
        # def monitor_gee_export(task, job, interval_minutes=5, max_checks=20):
        #     progress = 0
        #     for i in range(max_checks):
        #         status = task.status()
        #         print(f"[GEE Export] Check {i}: state = {status['state']}")
        #         if status['state'] == 'COMPLETED':
        #             job.progress = 100
        #             job.save()
        #             return True
        #         elif status['state'] in ['FAILED', 'CANCELLED']:
        #             job.status = 'failed'
        #             job.error_message = f"[GEE Export 실패] {status.get('error_message', 'Unknown')}"
        #             job.save()
        #             return False
        #
        #         progress = min(progress + 5, 95)
        #         job.progress = progress
        #         job.save()
        #         time.sleep(interval_minutes * 60)
        #     job.status = 'failed'
        #     job.error_message = "[GEE Export 실패] 시간 초과"
        #     job.save()
        #     return False
        #
        # success = monitor_gee_export(task, job)
        #
        # if not success:
        #     return

        job.progress = 100
        job.save()
        return job_id

    except Exception as e:
        job.status = 'failed'
        job.error_message = f"[다운로드 실패] {str(e)}"
        job.save()
        raise



# 2. 모델 추론 Task
@shared_task(bind=True)
def run_model(self, job_id):
    job = Job.objects.get(id=job_id)
    try:
        job.current_step = 'model_inference'
        job.progress = 0
        job.save()

        # inference.run(
        #     crop=job.crop_type,
        #     target_year=job.year,
        #     target_state=job.region,
        #     job=job
        # )

        for i in range(0, 100, 10):
            time.sleep(0.5)
            job.progress = i
            job.save()



        job.progress = 100
        job.save()
        return job_id

    except Exception as e:
        job.status = 'failed'
        job.error_message = f"[모델 추론 실패] {str(e)}"
        job.save()
        raise


# 3. GDAL 타일 생성 Task
@shared_task(bind=True)
def generate_tiles(self, job_id):
    job = Job.objects.get(id=job_id)
    try:
        job.current_step = 'generating_tiles'
        job.progress = 0
        job.save()

        # input_file = os.path.join(
        #     settings.MEDIA_ROOT,
        #     job.crop_type,
        #     job.region,
        #     str(job.year),
        #     f"{str(job.year)}_{job.crop_type}_{job.region}.tif"
        # )
        # tile_dir = os.path.join(
        #     settings.MEDIA_ROOT,
        #     job.crop_type,
        #     job.region,
        #     str(job.year),
        #     "tiles"
        # )
        # if not os.path.exists(tile_dir):
        #     os.makedirs(tile_dir, exist_ok=True)
        #
        #
        # # ✅ 진행률 업데이트용 콜백 정의
        # def update_progress(p):
        #     job.progress = p
        #     job.save()
        #
        # generate_maptile.run(input_file, tile_dir, progress_callback=update_progress)
        for i in range(0, 100, 10):
            time.sleep(0.5)
            job.progress = i
            job.save()

        job.status = 'done'
        job.progress = 100
        job.current_step = 'finished'
        job.save()
        return 'SUCCESS'

    except Exception as e:
        job.status = 'failed'
        job.error_message = f"[타일 생성 실패] {str(e)}"
        job.save()
        sys.stdout = sys.__stdout__  # 예외 발생 시에도 복구
        raise


# 4. 전체 체이닝 함수
def process_job_chain(job_id):
    return chain(
        download_data.s(job_id),
        run_model.s(),
        generate_tiles.s()
    )()