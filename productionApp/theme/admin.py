from django.contrib import admin
from .models import *  # importa os modelos

admin.site.register(Products)       # registra o modelo Products
admin.site.register(ProductDeleteLog)
