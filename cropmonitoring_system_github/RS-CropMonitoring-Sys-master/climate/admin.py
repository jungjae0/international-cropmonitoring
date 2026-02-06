from django.contrib import admin
from .models import ClimateData

@admin.register(ClimateData)
class ClimateDataAdmin(admin.ModelAdmin):
    list_display = (
        'get_crop',
        'get_year',
        'get_state',
        'variable',
        'csv_path_cached',
        'file_exists',
    )
    list_filter = ('variable', 'crop_season__year', 'crop_season__crop__name')
    search_fields = ('crop_season__crop__name', 'crop_season__state__name')

    @admin.display(description='Crop')
    def get_crop(self, obj):
        return obj.crop_season.crop.name

    @admin.display(description='Year')
    def get_year(self, obj):
        return obj.crop_season.year

    @admin.display(description='State')
    def get_state(self, obj):
        return obj.crop_season.state.name

    @admin.display(description='File Exists')
    def file_exists(self, obj):
        return obj.exists()
    file_exists.boolean = True
