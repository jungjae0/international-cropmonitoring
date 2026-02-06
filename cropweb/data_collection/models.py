# models.py
from django.db import models

class LogEntry(models.Model):
    # NULL 허용하기 (null=True, blank=True 설정)
    timestamp = models.DateTimeField(auto_now_add=True)  # 로그 생성 시간
    year = models.IntegerField(blank=True, null=True)  # 년도
    month = models.IntegerField(blank=True, null=True)  # 월
    julian_day = models.IntegerField(blank=True, null=True)  # 일
    status = models.CharField(max_length=50)  # 상태 (e.g., SUCCESS, ERROR)
    file_path = models.TextField(blank=True, null=True)  # 파일 경로
    file_size = models.CharField(max_length=50, blank=True, null=True)  # 파일 크기
    message = models.TextField(blank=True, null=True)  # 상세 메시지


    def __str__(self):
        return f"[{self.timestamp}] {self.status}: {self.message[:50]}"
