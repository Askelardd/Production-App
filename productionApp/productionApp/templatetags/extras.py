from django import template
from django.core.exceptions import PermissionDenied
from functools import wraps
import re


register = template.Library()

@register.filter
def separar_maiusculas(value):
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', value)

def group_required(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            if not any(request.user.groups.filter(name=group_name).exists() for group_name in group_names):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_required(view_func):
    return group_required('Administracao')(view_func)

def comercial_required(view_func):
    return group_required('Comercial')(view_func)

def qoffice_required(view_func):
    return group_required('Q-Office')(view_func)

def production_required(view_func):
    return group_required('Producao')(view_func)
