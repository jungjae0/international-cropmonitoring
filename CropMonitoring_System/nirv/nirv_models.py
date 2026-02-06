from django.db import models
from core.models import State, Crop, Country

class NirvRecord(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()

    # ✅ MEDIA_ROOT 이후 경로만 저장
    file_path = models.CharField(max_length=500)

    class Meta:
        unique_together = ("state", "crop", "year")
        ordering = ["-year"]

    def __str__(self):
        return f"{self.state.name} {self.crop.name} ({self.year})"

    def get_full_path(self):
        from django.conf import settings
        import os
        return os.path.join(settings.MEDIA_ROOT, self.file_path)
