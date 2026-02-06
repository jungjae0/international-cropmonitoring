from django.contrib import admin
from django.utils.html import format_html
from .models import NirvRecord

@admin.register(NirvRecord)
class NirvRecordAdmin(admin.ModelAdmin):
    list_display = ("state", "crop", "year", "file_link", "country")
    list_filter = ("country", "state", "crop", "year")
    search_fields = ("state__name", "crop__name", "file_path")
    ordering = ("-year", "state", "crop")

    @admin.display(description="파일 링크")
    def file_link(self, obj):
        if obj.file_path:
            url = f"/media/{obj.file_path}"
            return format_html('<a href="{}" target="_blank">📎 파일 보기</a>', url)
        return "-"
