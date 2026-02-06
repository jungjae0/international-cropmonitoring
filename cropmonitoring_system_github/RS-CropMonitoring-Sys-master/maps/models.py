from django.db import models
from django.conf import settings
import os
import re
from core.models import CropSeason, State, Country  # State는 여전히 필요

def slugify(value):
    return re.sub(r'[\W_]+', '_', value).strip('_').lower()


class TileSet(models.Model):
    crop_season = models.ForeignKey(CropSeason, on_delete=models.CASCADE, related_name='tilesets')
    area = models.FloatField(null=True, blank=True)
    folder_path_cached = models.TextField(blank=True)  # 실제 저장된 경로

    class Meta:
        unique_together = ('crop_season',)

    def __str__(self):
        return f"{self.crop_season.crop.name} - {self.crop_season.year} - {self.crop_season.state.name}"

    @property
    def folder_path(self):
        safe_state_name = self.crop_season.state.name.replace(' ', '_')
        return os.path.join(
            settings.MEDIA_ROOT,
            self.crop_season.state.country.iso_code,
            'GEE',
            'Cropmap',
            self.crop_season.crop.name,
            str(self.crop_season.year),
            f"{self.crop_season.year}_{self.crop_season.crop.name}_{safe_state_name}"
        )

    def save(self, *args, **kwargs):
        self.folder_path_cached = self.folder_path
        super().save(*args, **kwargs)

    @property
    def folder_exists(self):
        return os.path.isdir(self.folder_path)

    def get_tile_url(self):
        rel_path = self.folder_path.replace(settings.MEDIA_ROOT, '').lstrip(os.sep)
        return f"{settings.MEDIA_URL}{rel_path}/{{z}}/{{x}}/{{y}}.png"
