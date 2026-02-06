from rest_framework import serializers

from core.models import Job, JobOutput, PipelineConfig, PipelineConfigCrop


class PipelineConfigSerializer(serializers.ModelSerializer):
    crops = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()

    class Meta:
        model = PipelineConfig
        fields = (
            "id",
            "name",
            "country",
            "batch_size",
            "crops",
        )

    def get_crops(self, obj):
        return [
            {
                "name": link.crop.name,
                "display_name": link.crop.display_name or link.crop.name,
            }
            for link in PipelineConfigCrop.objects.filter(pipeline_config=obj).select_related(
                "crop"
            )
        ]

    def get_country(self, obj):
        return obj.country.code if obj.country else None


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = (
            "id",
            "input_path",
            "selected_states",
            "target_crops",
            "output_dir_name",
            "output_path",
            "status",
            "progress_percent",
            "celery_task_id",
            "celery_chain_id",
            "celery_last_state",
            "celery_error",
            "schedule_at",
            "created_at",
            "updated_at",
        )


class JobOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOutput
        fields = (
            "id",
            "job",
            "step",
            "relative_path",
            "absolute_path",
            "size_bytes",
            "file_modified_at",
            "created_at",
            "updated_at",
        )
