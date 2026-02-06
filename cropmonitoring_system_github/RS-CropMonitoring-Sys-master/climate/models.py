from django.db import models
from core.models import CropSeason
from django.conf import settings
import os
import json

class ClimateData(models.Model):
    CLIMATE_FEATURE_CHOICES = [
        ('pr', 'Precipitation'),
        ('tmmx', 'Maximum Temperature'),
        ('tmmn', 'Minimum Temperature'),
        ('srad', 'Surface Radiation'),
        ('rmin', 'Minimum Relative Humidity'),
        ('rmax', 'Maximum Relative Humidity'),
    ]

    crop_season = models.ForeignKey(CropSeason, on_delete=models.CASCADE)
    variable = models.CharField(max_length=50, choices=CLIMATE_FEATURE_CHOICES)
    csv_path_cached = models.TextField(blank=True)

    class Meta:
        unique_together = ('crop_season', 'variable')

    def __str__(self):
        return f"{self.crop_season.crop.name}-{self.crop_season.year}-{self.crop_season.state.name} - {self.variable}"

    def save(self, *args, **kwargs):
        self.csv_path_cached = self.csv_path
        super().save(*args, **kwargs)

    @property
    def csv_path(self):
        safe_state_name = self.crop_season.state.name.replace(" ", "_")
        return os.path.join(
            settings.MEDIA_ROOT,
            self.crop_season.state.country.iso_code,
            "Climate", "csv",
            str(self.crop_season.year),
            self.variable,
            f"{self.variable}_{self.crop_season.year}_{self.crop_season.crop.name}_{safe_state_name}.csv"
        )

    def exists(self):
        return os.path.exists(self.csv_path)
