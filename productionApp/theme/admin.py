from django.contrib import admin # type: ignore
from .models import (
    Products, ProductDeleteLog, QRData, Jobs,
    Diameters, Die, Tolerance,
    Polimento, PolimentoWorker,
    DesbasteAgulha, DesbasteAgulhaWorker,
    DesbasteCalibre, DesbasteCalibreWorker,
    Afinacao, AfinacaoWorker,
    NumeroPartidos, PedidosDiametro,
    dieInstance
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

# Polimento
class PolimentoWorkerInline(admin.TabularInline):
    model = PolimentoWorker
    extra = 3

@admin.register(Polimento)
class PolimentoAdmin(admin.ModelAdmin):
    inlines = [PolimentoWorkerInline]

# Desbaste Agulha
class DesbasteAgulhaWorkerInline(admin.TabularInline):
    model = DesbasteAgulhaWorker
    extra = 3

@admin.register(DesbasteAgulha)
class DesbasteAgulhaAdmin(admin.ModelAdmin):
    inlines = [DesbasteAgulhaWorkerInline]

# Desbaste Calibre
class DesbasteCalibreWorkerInline(admin.TabularInline):
    model = DesbasteCalibreWorker
    extra = 3

@admin.register(DesbasteCalibre)
class DesbasteCalibreAdmin(admin.ModelAdmin):
    inlines = [DesbasteCalibreWorkerInline]

# Afinação
class AfinacaoWorkerInline(admin.TabularInline):
    model = AfinacaoWorker
    extra = 3

@admin.register(Afinacao)
class AfinacaoAdmin(admin.ModelAdmin):
    inlines = [AfinacaoWorkerInline]

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
