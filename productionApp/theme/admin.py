from django.contrib import admin # type: ignore
from .models import (
    Products, ProductDeleteLog, QRData, Jobs,
    Diameters, Die, Tolerance,
    NumeroPartidos, PedidosDiametro,
    dieInstance,
    DieWork, DieWorkWorker,
    WhereDie,
    whereBox,
    globalLogs
)

# -------------------
# Products
# -------------------
@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ['order_Nmber', 'box_Nmber', 'task', 'qnt', 'edit_by', 'created_at']
    search_fields = ['order_Nmber', 'box_Nmber', 'task', 'edit_by__username']
    list_filter = ['created_at', 'edit_by']
    list_per_page = 20


# -------------------
# Product Delete Log
# -------------------
@admin.register(ProductDeleteLog)
class ProductDeleteLogAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'order_Nmber', 'task', 'deleted_by', 'deleted_at']
    search_fields = ['order_Nmber', 'task', 'deleted_by__username']
    list_filter = ['deleted_at']
    list_per_page = 20


# -------------------
# QRData + Inline DieInstance
# -------------------
class DieInstanceInline(admin.TabularInline):
    model = dieInstance
    fields = ['serial_number', 'diameter_text', 'die', 'job', 'tolerance', 'observations']
    extra = 2


@admin.register(QRData)
class QRDataAdmin(admin.ModelAdmin):
    list_display = ['customer', 'toma_order_nr', 'customer_order_nr', 'qt', 'created_at']
    search_fields = ['customer', 'toma_order_nr', 'customer_order_nr']
    list_filter = ['created_at']
    inlines = [DieInstanceInline]
    list_per_page = 20


# -------------------
# DieInstance
# -------------------
@admin.register(dieInstance)
class DieInstanceAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'customer', 'die', 'job', 'created_at']
    search_fields = ['serial_number', 'customer__customer', 'die__die_type']
    list_filter = ['job', 'die', 'created_at']
    list_per_page = 20


# -------------------
# DieWork + Inline DieWorkWorker
# -------------------
class DieWorkWorkerInline(admin.TabularInline):
    model = DieWorkWorker
    extra = 2


@admin.register(DieWork)
class DieWorkAdmin(admin.ModelAdmin):
    list_display = ['die', 'work_type', 'subtype', 'created_at']
    search_fields = ['die__serial_number', 'work_type', 'subtype']
    list_filter = ['work_type', 'created_at']
    inlines = [DieWorkWorkerInline]
    list_per_page = 20


# -------------------
# WhereDie
# -------------------
@admin.register(WhereDie)
class WhereDieAdmin(admin.ModelAdmin):
    list_display = ['die', 'where', 'updated_at'] 
    list_filter = ['where', 'updated_at']
    search_fields = ['die__serial_number']

    

# -------------------
# WhereBox
# -------------------
@admin.register(whereBox)
class WhereBoxAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'where']
    search_fields = ['order_number__toma_order_nr']
    list_filter = ['where']
    list_per_page = 20



# -------------------
# Global Logs
# -------------------
@admin.register(globalLogs)
class GlobalLogsAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'timestamp']
    search_fields = ['user__username', 'action']
    list_filter = ['timestamp']
    list_per_page = 50


# -------------------
# Jobs, Diameters, Die, Tolerance, NumeroPartidos, PedidosDiametro
# -------------------
@admin.register(Jobs)
class JobsAdmin(admin.ModelAdmin):
    list_display = ['job', 'descricao']
    search_fields = ['descricao']
    list_filter = ['job']


@admin.register(Diameters)
class DiametersAdmin(admin.ModelAdmin):
    list_display = ['min', 'max']
    search_fields = ['min', 'max']


@admin.register(Die)
class DieAdmin(admin.ModelAdmin):
    list_display = ['die_type', 'descricao']
    search_fields = ['descricao']
    list_filter = ['die_type']


@admin.register(Tolerance)
class ToleranceAdmin(admin.ModelAdmin):
    list_display = ['min', 'max']
    search_fields = ['min', 'max']


@admin.register(NumeroPartidos)
class NumeroPartidosAdmin(admin.ModelAdmin):
    list_display = ['qr_code', 'partido', 'created_at']
    search_fields = ['qr_code__toma_order_nr']
    list_filter = ['created_at']


@admin.register(PedidosDiametro)
class PedidosDiametroAdmin(admin.ModelAdmin):
    list_display = ['qr_code', 'diametro', 'numero_fieiras', 'created_at']
    search_fields = ['qr_code__toma_order_nr', 'diametro']
    list_filter = ['created_at']
