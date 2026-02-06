# admin.py
from django.contrib import admin
from .models import FileRecord

@admin.register(FileRecord)
class FileRecordAdmin(admin.ModelAdmin):
    list_display = ("data_source", "nation", "year", "month", "path")
    search_fields = ("data_source", "nation", "year", "month", "path")
