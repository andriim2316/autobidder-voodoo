from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

@register.filter
def get_field_value(instance, field_name):
    value = getattr(instance, field_name, None)
    if callable(value):
        return value()
    return value