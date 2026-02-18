from django import template
import re

register = template.Library()

@register.filter
def separar_maiusculas(value):
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', value)
