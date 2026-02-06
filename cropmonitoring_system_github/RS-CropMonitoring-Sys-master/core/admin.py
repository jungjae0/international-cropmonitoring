from django.contrib import admin
from .models import Country, State, Crop, CropSeason

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'iso_code', 'center_lat', 'center_lng')
    search_fields = ('name', 'iso_code')


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'country', 'center_lat', 'center_lng')
    list_filter = ('country',)
    search_fields = ('name', 'country__name')


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(CropSeason)
class CropSeasonAdmin(admin.ModelAdmin):
    list_display = ('id', 'crop', 'year', 'state')
    list_filter = ('year', 'crop__name', 'state__country__name')
    search_fields = ('crop__name', 'state__name', 'state__country__name')
