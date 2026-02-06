# maps/models.py

import os
from django.conf import settings
from django.db import models
from core.models import CropSeason


class TileSet(models.Model):
    """
    하나의 CropSeason 당,
    • non-wheat: variant='' (빈 문자열)
    • wheat: variant='SpringWheat' 또는 'WinterWheat'
    으로 구분하여 면적(area)을 별도 관리합니다.
    """
    VARIANT_NONE = ''
    VARIANT_SPRING = 'SpringWheat'
    VARIANT_WINTER = 'WinterWheat'
    VARIANT_CHOICES = [
        (VARIANT_NONE, 'None'),
        (VARIANT_SPRING, 'SpringWheat'),
        (VARIANT_WINTER, 'WinterWheat'),
    ]

    crop_season = models.ForeignKey(
        CropSeason,
        on_delete=models.CASCADE,
        related_name='tilesets',
        help_text="참조 대상 (작물·연도·주)"
    )
    variant = models.CharField(
        max_length=20,
        choices=VARIANT_CHOICES,
        default=VARIANT_NONE,
        help_text="Wheat인 경우 SpringWheat 또는 WinterWheat, 그 외는 빈 문자열"
    )
    area = models.FloatField(
        null=True, blank=True,
        help_text="해당 variant의 면적 (m²)"
    )
    folder_path_cached = models.TextField(
        blank=True,
        help_text="MEDIA_ROOT 기준 캐싱된 폴더 경로"
    )

    class Meta:
        unique_together = ('crop_season', 'variant')
        verbose_name = "Tile Set"
        verbose_name_plural = "Tile Sets"

    def __str__(self):
        v = f" / {self.variant}" if self.variant else ""
        return f"{self.crop_season}{v}"

    @property
    def folder_path(self) -> str:
        """
        실제 타일이 저장된 디렉터리 경로.
        variant에 상관없이 동일합니다.
        """
        state = self.crop_season.state.name.replace(' ', '_')
        return os.path.join(
            settings.MEDIA_ROOT,
            self.crop_season.state.country.iso_code,
            'GEE',
            'Cropmap_color',
            self.crop_season.crop.name,
            str(self.crop_season.year),
            f"{self.crop_season.year}_{self.crop_season.crop.name}_{state}"
        )

    def save(self, *args, **kwargs):
        # 1) folder_path 를 캐싱
        self.folder_path_cached = self.folder_path
        super().save(*args, **kwargs)

    @property
    def folder_exists(self) -> bool:
        return os.path.isdir(self.folder_path)

    def get_tile_url(self) -> str:
        """
        MEDIA_URL 기준의 타일 URL 템플릿 반환.
        {z}/{x}/{y}.png 부분은 프런트에서 치환됩니다.
        """
        rel = self.folder_path_cached.replace(settings.MEDIA_ROOT, '').lstrip(os.sep)
        return f"{settings.MEDIA_URL}{rel}/{{z}}/{{x}}/{{y}}.png"
