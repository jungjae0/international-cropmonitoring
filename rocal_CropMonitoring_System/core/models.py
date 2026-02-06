# core/models.py
from django.db import models
from django.conf import settings
import os
import re


class Country(models.Model):
    name = models.CharField(max_length=100)
    iso_code = models.CharField(max_length=3, unique=True)
    center_lat = models.FloatField(default=0.0)
    center_lng = models.FloatField(default=0.0)
    boundary_path_cached = models.TextField(blank=True, null=True)

    @property
    def boundary_path(self):
        """
        항상 forward slash(/)를 사용하여 플랫폼 독립적인 경로 반환
        """
        path = os.path.join(
            settings.MEDIA_ROOT,
            self.iso_code,
            'Layers',
            f'{self.iso_code}_states.json'
        )
        # 윈도우 백슬래시를 슬래시로 변환하여 리눅스에서도 호환
        return path.replace('\\', '/')

    def save(self, *args, **kwargs):
        self.boundary_path_cached = self.boundary_path
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        웹 URL 반환 (항상 forward slash 사용)
        """
        return f"{settings.MEDIA_URL}{self.iso_code}/Layers/{self.iso_code}_states.json"



class State(models.Model):
    name = models.CharField(max_length=100)
    center_lat = models.FloatField(default=0.0)
    center_lng = models.FloatField(default=0.0)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')

    def __str__(self):
        return f"{self.name} ({self.country.name})"


class Crop(models.Model):
    CROP_CHOICES = [
        ('Wheat', 'Wheat'),
        ('Wheat_Spring', 'Wheat Spring'),
        ('Wheat_Winter', 'Wheat Winter'),
        ('Soybean', 'Soybean'),
        ('Corn', 'Corn'),
    ]

    name = models.CharField(max_length=50, choices=CROP_CHOICES)

    def __str__(self):
        return self.name

class CropSeason(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    year = models.IntegerField()
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('crop', 'year', 'state')

    def __str__(self):
        return f"{self.crop} - {self.year} - {self.state.name}"

