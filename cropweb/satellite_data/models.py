# models.py
from django.db import models

class FileRecord(models.Model):
    data_source = models.CharField(max_length=100)
    nation = models.CharField(max_length=100)
    year = models.IntegerField()
    month = models.IntegerField()
    path = models.TextField()

    def __str__(self):
        return f"{self.data_source} - {self.nation} - {self.year} - {self.month} - {self.path}"
        # return f"{self.data_source} - {self.region} - {self.path}"
