# myapp/templatetags/form_filters.py
from django import template

register = template.Library()

@register.filter
def get_field(form, field_name):
    return form[field_name]

@register.filter
def not_in_list(value, arg):
    return value not in arg