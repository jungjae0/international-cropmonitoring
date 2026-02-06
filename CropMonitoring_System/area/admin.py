from django.contrib import admin
from .models import CultivatedArea

@admin.register(CultivatedArea)
class CultivatedAreaAdmin(admin.ModelAdmin):
    list_display = ('crop_season', 'area_acres')
    list_filter = ('crop_season__year', 'crop_season__crop__name', 'crop_season__state__name')
    search_fields = ('crop_season__state__name', 'crop_season__crop__name')
