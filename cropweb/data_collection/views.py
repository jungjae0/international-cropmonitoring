# views.py
from django.shortcuts import render
from .models import LogEntry
# from django_celery_beat.models import PeriodicTask, IntervalSchedule

def log_view(request):
    logs = LogEntry.objects.all().order_by('-timestamp')  # 최신 로그부터 표시
    return render(request, 'log_view.html', {'logs': logs})



# def start_task(request):
#     schedule, created = IntervalSchedule.objects.get_or_create(every=10,period=IntervalSchedule.SECONDS,)
#     if PeriodicTask.objects.filter(name='run_data_collection').exists(): #'test_task'가 등록되어 있으면,
#     	p_test=PeriodicTask.objects.get(name='run_data_collection')
#         p_test.enabled=True #실행시킨다.
#         p_test.interval=schedule
#         p_test.save()
#     else: #'test_task'가 등록되어 있지 않으면, 새로 생성한다
#         PeriodicTask.objects.create(
#         interval=schedule,  #앞서 정의한 schedule
#         name='run_data_collection',
#         task='bracken.tasks.run_data_collection',
#         )