from django.contrib import admin
from .models import (
    Products,
    ProductDeleteLog,
    QRData,
    Jobs,

    Diameters,
    Die,
    Tolerance,
    Desbaste,
    DesbasteWorker,
    Polimento,
    PolimentoWorker,
    Fio,
    FioWorker,
    NumeroPartidos,
    PedidosDiametro,
    
    

)

admin.site.register(Products)
admin.site.register(ProductDeleteLog)
admin.site.register(QRData)
admin.site.register(Jobs)
admin.site.register(DesbasteWorker)
admin.site.register(PolimentoWorker)
admin.site.register(FioWorker)
admin.site.register(Diameters)
admin.site.register(Die)
admin.site.register(Tolerance)
admin.site.register(NumeroPartidos)
admin.site.register(PedidosDiametro)


class DesbasteWorkerInline(admin.TabularInline):
    model = DesbasteWorker
    extra =3

@admin.register(Desbaste)
class DesbasteAdmin(admin.ModelAdmin):
    inlines = [DesbasteWorkerInline]

class PolimentoWorkerInline(admin.TabularInline):
    model = PolimentoWorker
    extra =3
@admin.register(Polimento)
class PolimentoAdmin(admin.ModelAdmin):
    inlines = [PolimentoWorkerInline]

class FioWorkerInline(admin.TabularInline):
    model = FioWorker
    extra =3

@admin.register(Fio)
class FioAdmin(admin.ModelAdmin):
    inlines = [FioWorkerInline]