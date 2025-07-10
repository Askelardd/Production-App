from django.contrib import admin
from .models import *  # importa os modelos

admin.site.register(Products)
admin.site.register(ProductDeleteLog)
admin.site.register(QRData)