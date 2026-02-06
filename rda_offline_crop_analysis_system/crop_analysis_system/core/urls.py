from django.urls import path

from core import views


urlpatterns = [
    path("input/years/", views.list_year_suffix, name="list_year_suffix"),
    path("input/countries/", views.list_countries, name="list_countries"),
    path("input/states/", views.list_states, name="list_states"),
    path("configs/", views.list_pipeline_configs, name="list_pipeline_configs"),
    path("jobs/", views.create_job, name="create_job"),
    path("jobs/<int:job_id>/", views.job_detail, name="job_detail"),
    path("jobs/<int:job_id>/info/", views.job_info, name="job_info"),
    path("jobs/<int:job_id>/progress/", views.job_progress, name="job_progress"),
    path("jobs/<int:job_id>/task-status/", views.job_task_status, name="job_task_status"),
    path("jobs/<int:job_id>/outputs/", views.job_outputs, name="job_outputs"),
    path("jobs/<int:job_id>/outputs/download/", views.download_output, name="download_output"),
    path("jobs/<int:job_id>/outputs/download-zip/", views.download_job_step_zip, name="download_job_step_zip"),
    path("jobs/<int:job_id>/outputs/zip/", views.download_job_outputs_zip, name="download_job_outputs_zip"),
    path("jobs/<int:job_id>/logs/download/", views.download_log, name="download_log"),
    path("gpu/available/", views.gpu_available, name="gpu_available"),
    path("jobs/<int:job_id>/cancel/", views.cancel_job, name="cancel_job"),
    path("jobs/<int:job_id>/retry/", views.retry_job, name="retry_job"),
    path("outputs/", views.job_outputs_page, name="job_outputs_page"),
    path("outputs/filtered/", views.filtered_outputs, name="filtered_outputs"),
    path("outputs/zip/", views.download_outputs_zip, name="download_outputs_zip"),
    path("validate-path/", views.validate_path, name="validate_path"),
    path("settings/", views.root_settings_page, name="root_settings_page"),
    path("root-settings/", views.root_settings, name="root_settings"),
]
