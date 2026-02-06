from django.contrib import admin
from .models import TileSet

@admin.register(TileSet)
class TileSetAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_crop',
        'get_year',
        'get_state',
        'area',
        'folder_path_cached',
    )
    list_filter = ('crop_season__crop__name', 'crop_season__year', 'crop_season__state__name')
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

