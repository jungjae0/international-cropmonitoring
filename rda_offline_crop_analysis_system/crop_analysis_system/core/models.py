from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models


class Country(models.Model):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name or self.code


class RootPath(models.Model):
    TYPE_INPUT = "input"
    TYPE_OUTPUT = "output"
    TYPE_WEIGHTS = "weights"
    TYPE_SHAPEFILE = "shp"
    TYPE_LOGS = "logs"

    TYPE_CHOICES = [
        (TYPE_INPUT, "Input"),
        (TYPE_OUTPUT, "Output"),
        (TYPE_WEIGHTS, "Weights"),
        (TYPE_SHAPEFILE, "Shapefile"),
        (TYPE_LOGS, "Logs"),
    ]

    path_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    path = models.CharField(
        max_length=512,
        help_text="Absolute or project-relative path for root directory.",
    )
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.path:
            raise ValidationError({"path": "Root path is required."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            RootPath.objects.filter(path_type=self.path_type).exclude(id=self.id).update(
                is_active=False
            )

    def __str__(self) -> str:
        return f"{self.path_type}: {self.path}"


class PipelineConfig(models.Model):
    name = models.CharField(max_length=128, unique=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, null=True, blank=True)
    model_weights_path = models.CharField(max_length=512, blank=True)
    shapefile_path = models.CharField(max_length=512, blank=True)
    batch_size = models.PositiveIntegerField(default=64)
    crops = models.ManyToManyField(
        "Crop",
        through="PipelineConfigCrop",
        related_name="pipeline_configs",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Crop(models.Model):
    name = models.CharField(max_length=64)
    display_name = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.display_name or self.name


class PipelineConfigCrop(models.Model):
    pipeline_config = models.ForeignKey(PipelineConfig, on_delete=models.CASCADE)
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]


class Job(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_RUNNING = "RUNNING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    pipeline_config = models.ForeignKey(
        PipelineConfig, on_delete=models.SET_NULL, null=True, blank=True
    )
    input_path = models.JSONField()
    selected_states = models.JSONField(default=list)
    target_crops = models.CharField(max_length=256)
    output_dir_name = models.CharField(max_length=128)
    output_path = models.CharField(max_length=512, blank=True)
    skip_inference = models.BooleanField(default=False)
    skip_merge = models.BooleanField(default=False)
    skip_area = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    current_step = models.CharField(max_length=32, blank=True)
    progress_percent = models.PositiveIntegerField(default=0)
    gpu_count = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="Number of GPUs to use. -1 for auto, 0 for CPU.",
    )
    celery_task_id = models.CharField(max_length=128, blank=True)
    celery_chain_id = models.CharField(max_length=128, blank=True)
    celery_last_state = models.CharField(max_length=32, blank=True)
    celery_error = models.TextField(blank=True)
    schedule_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Job {self.id} - {self.status}"


class JobOutput(models.Model):
    STEP_INFERENCE = "inference_tiles"
    STEP_MERGE = "merged_cropmasks"
    STEP_AREA = "calculate_area"
    STEP_THUMBNAIL = "mask_thumbnails"

    STEP_CHOICES = [
        (STEP_INFERENCE, "Inference Tiles"),
        (STEP_MERGE, "Merged Cropmasks"),
        (STEP_AREA, "Calculate Area"),
        (STEP_THUMBNAIL, "Mask Thumbnails"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="outputs")
    step = models.CharField(max_length=64, choices=STEP_CHOICES)
    relative_path = models.CharField(max_length=512)
    absolute_path = models.CharField(max_length=1024)
    size_bytes = models.BigIntegerField(default=0)
    bounds = models.JSONField(null=True, blank=True)
    file_modified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("job", "absolute_path")
        indexes = [
            models.Index(fields=["job", "step"]),
        ]

    def __str__(self) -> str:
        return f"{self.job_id} - {self.step} - {self.relative_path}"
