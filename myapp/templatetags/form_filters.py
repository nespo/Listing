# myapp/templatetags/form_filters.py
from django import template

register = template.Library()

@register.filter
def get_field(form, field_name):
    return form[field_name]
