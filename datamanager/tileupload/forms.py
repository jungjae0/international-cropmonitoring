from django import forms
from .models import UploadedTif

class UploadedTifForm(forms.ModelForm):
    color_label_json = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = UploadedTif
        fields = ['file', 'color_label_json']  # ✅ 반드시 이처럼 명시해야 함
