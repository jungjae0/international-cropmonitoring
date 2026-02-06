from django.contrib import admin
from .models import UploadedTif

@admin.register(UploadedTif)
class UploadedTifAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'filename', 'status', 'uploaded_at')
    list_filter = ('status', 'uploaded_at')
    search_fields = ('file', 'user__username')
    readonly_fields = ('uploaded_at', 'error_message')

    def filename(self, obj):
        return obj.file.name.split('/')[-1] if obj.file else 'N/A'
    filename.short_description = '파일명'
