from django.contrib import admin # type: ignore
from .models import (
    Products, ProductDeleteLog, QRData, Jobs,
    Diameters, Die, Tolerance,
    NumeroPartidos, PedidosDiametro,
    dieInstance,
    DieWork, DieWorkWorker
)

# Registro simples
admin.site.register(Products)
admin.site.register(ProductDeleteLog)
admin.site.register(Jobs)
admin.site.register(Diameters)
admin.site.register(Die)
admin.site.register(Tolerance)
admin.site.register(NumeroPartidos)
admin.site.register(PedidosDiametro)


class DieInstanceInline(admin.TabularInline):
    model = dieInstance
    fields = ['serial_number', 'diameter_text', 'die', 'job', 'tolerance', 'observations']
    extra = 3


@admin.register(QRData)
class QRDataAdmin(admin.ModelAdmin):
    list_display = ['customer', 'toma_order_nr', 'qt', 'created_at']
    inlines = [DieInstanceInline]

@admin.register(dieInstance)
class DieInstanceAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'customer', 'die', 'job', 'created_at']
    search_fields = ['serial_number', 'customer__customer', 'die__die_type']
    list_filter = ['job', 'die']


class DieWorkWorkerInline(admin.TabularInline):
    model = DieWorkWorker
    extra = 3

@admin.register(DieWork)
class DieWorkAdmin(admin.ModelAdmin):
    list_display = ['die', 'work_type', 'subtype', 'created_at']
    list_filter = ['work_type']
    inlines = [DieWorkWorkerInline]

