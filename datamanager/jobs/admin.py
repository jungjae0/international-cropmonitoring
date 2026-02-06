from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'crop_type', 'year', 'region',
        'status', 'current_step', 'progress', 'created_at'
    )
    list_filter = ('status', 'crop_type', 'region', 'year')
    search_fields = ('user__username', 'region')
    readonly_fields = ('status', 'progress', 'current_step', 'error_message', 'created_at', 'updated_at')

# from django.contrib import admin
# from .models import Job
#
# admin.site.register(Job)
