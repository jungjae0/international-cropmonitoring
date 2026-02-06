from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings
import json

def upload_path(instance, filename):
    instance._original_filename = filename  # 임시로 저장
    return f"uploadfiles/{instance.user.username}/_temp_"

class UploadedTif(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    error_message = models.TextField(blank=True, null=True)
    color_labels_json = models.TextField(blank=True, null=True)

    def set_color_labels(self, label_list):
        self.color_labels_json = json.dumps(label_list)

    def get_color_labels(self):
        if self.color_labels_json:
            return json.loads(self.color_labels_json)
        return []


    def original_filename(self):
        return '_'.join(self.filename().split('_')[1:])


    def filename(self):
        return os.path.basename(self.file.name)

    def tile_output_path(self):
        base = os.path.splitext(os.path.basename(self.file.name))[0]
        return f"uploadfiles/{self.user.username}/{base}_tiles/"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new and hasattr(self, '_original_filename'):
            try:
                original_name = self._original_filename
                new_filename = f"{self.id}_{original_name}"
                new_rel_path = f"uploadfiles/{self.user.username}/{new_filename}"
                new_abs_path = os.path.join(settings.MEDIA_ROOT, new_rel_path)

                old_abs_path = self.file.path
                os.makedirs(os.path.dirname(new_abs_path), exist_ok=True)

                with open(old_abs_path, 'rb') as src, open(new_abs_path, 'wb') as dst:
                    dst.write(src.read())
                os.remove(old_abs_path)

                self.file.name = new_rel_path
                super().save(update_fields=['file'])

            except Exception as e:
                print(f"🔥 save 내부 오류: {e}")
                raise


    # def save(self, *args, **kwargs):
    #     is_new = self._state.adding
    #     super().save(*args, **kwargs)
    #
    #     if is_new and hasattr(self, '_original_filename'):
    #         original_name = self._original_filename
    #         new_filename = f"{self.id}_{original_name}"
    #         new_rel_path = f"uploadfiles/{self.user.username}/{new_filename}"
    #         new_abs_path = os.path.join(settings.MEDIA_ROOT, new_rel_path)
    #
    #         old_abs_path = self.file.path
    #
    #         # 이동
    #         os.makedirs(os.path.dirname(new_abs_path), exist_ok=True)
    #         with open(old_abs_path, 'rb') as src, open(new_abs_path, 'wb') as dst:
    #             dst.write(src.read())
    #         os.remove(old_abs_path)
    #
    #         self.file.name = new_rel_path
    #         super().save(update_fields=['file'])