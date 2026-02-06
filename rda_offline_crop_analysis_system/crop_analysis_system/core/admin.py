from django.contrib import admin

import os
from pathlib import Path

from django.conf import settings
from django import forms
from django.utils.safestring import mark_safe

from core.models import Country, Crop, Job, JobOutput, PipelineConfig, PipelineConfigCrop, RootPath
from core.utils.app_settings import get_root_by_type, resolve_root_path


class PipelineConfigCropInline(admin.TabularInline):
    model = PipelineConfigCrop
    extra = 1


class PipelineConfigAdminForm(forms.ModelForm):
    weights_file = forms.ChoiceField(required=False)
    shapefile_file = forms.ChoiceField(required=False)

    class Meta:
        model = PipelineConfig
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["weights_file"].help_text = "Select a weights file from the active weights root."
        self.fields["shapefile_file"].help_text = "Select a shapefile from the active shapefile root."
        self.fields["weights_file"].choices = self._build_file_choices("weights", None)
        self.fields["shapefile_file"].choices = self._build_file_choices("shp", (".shp",))
        self.fields["weights_file"].initial = self._initial_from_path(
            "weights", self.instance.model_weights_path
        )
        self.fields["shapefile_file"].initial = self._initial_from_path(
            "shp", self.instance.shapefile_path
        )
        self.fields["model_weights_path"].required = False
        self.fields["shapefile_path"].required = False
        self.fields["model_weights_path"].widget = forms.HiddenInput()
        self.fields["shapefile_path"].widget = forms.HiddenInput()

    def _build_file_choices(self, root_type: str, extensions):
        root = get_root_by_type(root_type)
        if not root or not root.exists():
            return [("", "-- No active root --")]
        choices = [("", "-- Select --")]
        for dirpath, _, filenames in os.walk(root):
            for name in sorted(filenames):
                if extensions is None or name.lower().endswith(extensions):
                    full = Path(dirpath) / name
                    rel = full.relative_to(root)
                    choices.append((str(rel), str(rel)))
        return choices

    def _initial_from_path(self, root_type: str, existing_path: str) -> str:
        if not existing_path:
            return ""
        root = get_root_by_type(root_type)
        if not root:
            return ""
        try:
            rel = Path(existing_path).resolve().relative_to(root)
        except ValueError:
            return ""
        return str(rel)

    def clean(self):
        cleaned = super().clean()
        weights_file = cleaned.get("weights_file")
        shapefile_file = cleaned.get("shapefile_file")
        if weights_file:
            cleaned["model_weights_path"] = weights_file
        if shapefile_file:
            cleaned["shapefile_path"] = shapefile_file
        return cleaned


class RootPathAdminForm(forms.ModelForm):
    class Meta:
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        help_text = self.fields["path"].help_text or ""
        self.fields["path"].help_text = mark_safe(
            f"{help_text}<div class='path-preview' id='root-path-preview'></div>"
        )


@admin.register(PipelineConfig)
class PipelineConfigAdmin(admin.ModelAdmin):
    form = PipelineConfigAdminForm
    list_display = (
        "id",
        "name",
        "country",
        "model_weights_path",
        "batch_size",
        "created_at",
    )
    search_fields = ("name",)
    inlines = [PipelineConfigCropInline]
    readonly_fields = (
        "model_weights_resolved",
        "model_weights_exists",
        "shapefile_resolved",
        "shapefile_exists",
    )
    class Media:
        js = ("js/admin_path_check.js",)
        css = {"all": ("css/admin_custom.css",)}

    def _resolve_path(self, value: str, root_type: str) -> Path:
        return resolve_root_path(value, root_type)

    def model_weights_resolved(self, obj: PipelineConfig) -> str:
        path = self._resolve_path(obj.model_weights_path, "weights")
        return str(path) if path else ""

    def model_weights_exists(self, obj: PipelineConfig) -> bool:
        path = self._resolve_path(obj.model_weights_path, "weights")
        return path.exists() if path else False

    def shapefile_resolved(self, obj: PipelineConfig) -> str:
        path = self._resolve_path(obj.shapefile_path, "shp")
        return str(path) if path else ""

    def shapefile_exists(self, obj: PipelineConfig) -> bool:
        path = self._resolve_path(obj.shapefile_path, "shp")
        return path.exists() if path else False

    model_weights_resolved.short_description = "Resolved weights path"
    model_weights_exists.short_description = "Weights path exists"
    shapefile_resolved.short_description = "Resolved shapefile path"
    shapefile_exists.short_description = "Shapefile path exists"


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "display_name", "created_at")
    search_fields = ("name", "display_name")


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "created_at")
    search_fields = ("code", "name")


@admin.register(RootPath)
class RootPathAdmin(admin.ModelAdmin):
    form = RootPathAdminForm
    list_display = ("id", "path_type", "path", "is_active", "updated_at")
    list_filter = ("path_type", "is_active")
    search_fields = ("path",)
    class Media:
        js = ("js/admin_path_check.js",)
        css = {"all": ("css/admin_custom.css",)}


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "current_step",
        "output_dir_name",
        "progress_percent",
        "celery_last_state",
        "celery_error",
        "created_at",
    )
    list_filter = ("status", "current_step", "celery_last_state")
    search_fields = ("output_dir_name",)
    readonly_fields = (
        "pipeline_config",
        "input_path",
        "selected_states",
        "target_crops",
        "output_dir_name",
        "output_path",
        "celery_task_id",
        "celery_chain_id",
        "celery_last_state",
        "celery_error",
        "created_at",
        "updated_at",
    )


@admin.register(JobOutput)
class JobOutputAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "step", "relative_path", "size_bytes", "file_modified_at")
    list_filter = ("step",)
    search_fields = ("relative_path", "absolute_path")
