# myapp/templatetags/form_filters.py
from django import template

register = template.Library()

@register.filter
def get_field(form, field_name):
    return form[field_name]

@register.filter(name='not_in_list')
def not_in_list(value, arg):
    return value not in arg.split(',')