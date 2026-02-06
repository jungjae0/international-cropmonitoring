from django.db import models
from core.models import CropSeason


class CultivatedArea(models.Model):
    crop_season = models.ForeignKey(CropSeason, on_delete=models.CASCADE, related_name='areas')
    area_acres = models.FloatField()

    class Meta:
        unique_together = ('crop_season',)

    def __str__(self):
        return f"{self.crop_season} - {self.area_acres} acre"