from django import template

register = template.Library()

STEP_LABELS = {
    'downloading': '데이터 다운로드',
    'model_inference': '모델 추론',
    'generating_tiles': '타일 생성',
    'finished': '완료',
}

@register.filter
def step_label(value):
    return STEP_LABELS.get(value, value)
