from django import template
from django.apps import apps

register = template.Library()


@register.simple_tag(name="app_name")
def get_app_name():
    return apps.get_app_config("baskets").verbose_name
