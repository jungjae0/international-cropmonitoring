from django.db import models
from django.contrib.auth.models import User

north_state = ['Washington', 'Montana', 'Idaho', 'Oregon']
south_state = ['Kansas', 'Oklahoma', 'Texas', 'Nebraska', 'Colorado']
states = north_state + south_state



class Job(models.Model):
    CROP_CHOICES = [
        ('Wheat', 'Wheat'),
        ('Corn', 'Corn'),
        ('Bean', 'Bean'),
    ]

    # REGION_CHOICES = [
    #     ('kansas', 'Kansas'),
    #     ('idaho', 'Idaho'),
    #     ('texas', 'Texas'),
    # ]

    REGION_CHOICES = []
    for state in states:
        REGION_CHOICES.append((state, state))



    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    crop_type = models.CharField(max_length=10, choices=CROP_CHOICES, default='wheat')
    year = models.PositiveIntegerField()
    region = models.CharField(max_length=20, choices=REGION_CHOICES)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    current_step = models.CharField(max_length=50, null=True, blank=True)
    progress = models.FloatField(default=0.0)

    tif_file = models.FileField(upload_to='jobs/%Y/%m/%d/', null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crop_type.capitalize()} {self.year} - {self.region.capitalize()}"
