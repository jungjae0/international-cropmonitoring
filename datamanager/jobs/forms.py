from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['crop_type', 'year', 'region']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['year'].widget = forms.Select(choices=[
            (2022, '2022'),
            (2023, '2023'),
            (2024, '2024'),
        ])

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
            })
