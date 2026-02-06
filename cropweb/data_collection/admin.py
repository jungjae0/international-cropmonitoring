# admin.py
from django.contrib import admin
from .models import LogEntry

from django.utils.timezone import now

from django.utils.timezone import now
from django.utils.html import format_html


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    # 목록에서 보여줄 필드
    list_display = ('timestamp', 'status', 'short_message', 'year', 'month', 'julian_day', 'file_path', 'file_size')

    # 필터링 옵션
    list_filter = ('status', 'timestamp', 'year', 'month')  # 년도와 월로도 필터링 가능

    # 검색 필드
    search_fields = ('message', 'file_path')  # 메시지와 파일 경로 검색 가능

    # 최신 로그부터 정렬
    ordering = ('-timestamp',)

    # 날짜 필터링 추가 (연도, 월 등)
    date_hierarchy = 'timestamp'

    # 메시지가 너무 길 경우 앞부분만 표시
    def short_message(self, obj):
        """메시지가 너무 길 경우 앞부분만 표시"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message

    short_message.short_description = 'Message'

    # 필드셋을 사용하여 필드 순서 지정
    fieldsets = (
        (None, {
            'fields': ('timestamp', 'status', 'year', 'month', 'julian_day', 'message', 'file_path', 'file_size')
        }),
    )

    # 모델 생성 시 'timestamp'가 자동 생성되므로 필드를 수정할 수 없도록 설정
    readonly_fields = ('timestamp',)


#
# @admin.register(LogEntry)
# class LogEntryAdmin(admin.ModelAdmin):
#     list_display = ('timestamp', 'status', 'short_message')  # 목록에서 보여줄 필드
#     list_filter = ('status', 'timestamp')  # 필터링 옵션
#     search_fields = ('message',)  # 검색 필드
#     ordering = ('-timestamp',)  # 최신 로그부터 정렬
#
#     def short_message(self, obj):
#         """메시지가 너무 길 경우 앞부분만 표시"""
#         return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
#     short_message.short_description = 'Message'
