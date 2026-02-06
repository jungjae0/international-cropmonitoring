from django.contrib import admin
from .models import Country, State, Crop, CropSeason
from django.contrib.admin import SimpleListFilter
from datetime import date


class RecentYearFilter(SimpleListFilter):
    title = '연도(최근)'
    parameter_name = 'recent_years'

    def lookups(self, request, model_admin):
        return [
            ('3', '최근 3년'),
            ('5', '최근 5년'),
            ('10', '최근 10년'),
        ]

    def queryset(self, request, queryset):
        if self.value() in {'3','5','10'}:
            cutoff = date.today().year - int(self.value()) + 1
            return queryset.filter(year__gte=cutoff)
        return queryset


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
    list_filter = ('name',)  # choices라 자동 드롭다운 필터
    search_fields = ('name',)


@admin.register(CropSeason)
class CropSeasonAdmin(admin.ModelAdmin):
    list_display = ('crop', 'year', 'state')
    list_filter = ('year', 'crop', 'state__country', RecentYearFilter)
    search_fields = ('crop__name', 'state__name', 'state__country__name')
