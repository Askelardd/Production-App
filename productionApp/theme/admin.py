from django.contrib import admin
from .models import (
    Products,
    ProductDeleteLog,
    QRData,
    Jobs,

    Diameters,
    Die,
    Tolerance,

    Polimento,
    PolimentoWorker,
    DesbasteAgulha,
    DesbasteAgulhaWorker,
    DesbasteCalibre,
    DesbasteCalibreWorker,
    Afinacao,
    AfinacaoWorker,
    NumeroPartidos,
    PedidosDiametro,
    
    

)

admin.site.register(Products)
admin.site.register(ProductDeleteLog)
admin.site.register(QRData)
admin.site.register(Jobs)
admin.site.register(Diameters)
admin.site.register(Die)
admin.site.register(Tolerance)
admin.site.register(NumeroPartidos)
admin.site.register(PedidosDiametro)



class PolimentoWorkerInline(admin.TabularInline):
    model = PolimentoWorker
    extra =3
@admin.register(Polimento)

class PolimentoAdmin(admin.ModelAdmin):
    inlines = [PolimentoWorkerInline]

class DesbasteAgulhaWorkerInline(admin.TabularInline):
    model = DesbasteAgulhaWorker
    extra = 3
@admin.register(DesbasteAgulha)

class DesbasteAgulhaAdmin(admin.ModelAdmin):
    inlines = [DesbasteAgulhaWorkerInline]

class DesbasteCalibreWorkerInline(admin.TabularInline):
    model = DesbasteCalibreWorker
    extra = 3
@admin.register(DesbasteCalibre)

class DesbasteCalibreAdmin(admin.ModelAdmin):
    inlines = [DesbasteCalibreWorkerInline]

class AfinacaoWorkerInline(admin.TabularInline):
    model = AfinacaoWorker
    extra = 3
@admin.register(Afinacao)

class AfinacaoAdmin(admin.ModelAdmin):
    inlines = [AfinacaoWorkerInline]


