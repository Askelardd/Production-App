from django.contrib import admin # type: ignore
from django import forms  # type: ignore

from .models import (
    Order, Products, ProductDeleteLog, QRData, Jobs,
    Diameters, Die, Tolerance,
    NumeroPartidos, PedidosDiametro,
    dieInstance,
    DieWork, DieWorkWorker,
    WhereDie,
    whereBox,
    globalLogs,
    DeliveryInfo,
    DeliveryEntity,
    DeliveryType,
    OrderFile,
    OrdersComing
    
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
    list_filter = ['created_at', 'checkbox']


# -------------------
# DeliveryInfo, DeliveryEntity
# -------------------

@admin.register(DeliveryEntity)
class DeliveryEntityAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(DeliveryType)
class DeliveryTypeAdmin(admin.ModelAdmin):
    list_display = ['name']  # Removed 'description' since it does not exist on the model
    search_fields = ['name']
    list_per_page = 20

# --- Admin do DeliveryInfo usando o form acima ---
class DeliveryInfoForm(forms.ModelForm):
    class Meta:
        model = DeliveryInfo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Mostrar apenas toma_order_full para identificator
        if 'identificator' in self.fields:
            self.fields['identificator'].queryset = QRData.objects.order_by('toma_order_full')
            self.fields['identificator'].label_from_instance = lambda obj: obj.toma_order_full

        # Mostrar apenas name para deliveryEntity
        if 'deliveryEntity' in self.fields:
            self.fields['deliveryEntity'].queryset = DeliveryEntity.objects.order_by('name')
            self.fields['deliveryEntity'].label_from_instance = lambda obj: obj.name

        # Mostrar apenas name para deliveryType
        if 'deliveryType' in self.fields:
            self.fields['deliveryType'].queryset = DeliveryType.objects.order_by('name')
            self.fields['deliveryType'].label_from_instance = lambda obj: obj.name

        # Dica visual
        self.fields['deliveryEntity'].help_text = (
            "Quando Delivery Type = Customer, este campo é preenchido automaticamente com o nome do cliente do QR."
        )

@admin.register(DeliveryInfo)
class DeliveryInfoAdmin(admin.ModelAdmin):
    form = DeliveryInfoForm
    list_display = ('identificator_toma', 'deliveryType', 'deliveryEntity', 'deliveryDate', 'costumer')
    list_filter = ('deliveryType', 'deliveryDate', 'deliveryEntity')
    search_fields = ('identificator__toma_order_full', 'deliveryEntity__name', 'costumer')
    list_per_page = 20

    # (opcional) autocompletar se preferires em vez de dropdown
    # autocomplete_fields = ('identificator', 'deliveryEntity', 'deliveryType')

    def identificator_toma(self, obj):
        return getattr(obj.identificator, 'toma_order_full', None)
    identificator_toma.short_description = 'TOMA'

    class Media:
        # carrega o JS que esconde/desativa o campo deliveryEntity quando Type=Customer
        js = ('theme/js/deliveryinfo_admin.js',)

# -------------------
# Order , OrderFile
# -------------------

# -------------------
# OrdersComing
# -------------------
@admin.register(OrdersComing)
class OrdersComingAdmin(admin.ModelAdmin):
    list_display = ['order', 'inspectionMetrology', 'mark', 'urgent', 'done', 'comment']
    search_fields = ['order', 'comment']
    list_filter = ['inspectionMetrology', 'mark', 'urgent', 'done']
    list_per_page = 20

# -------------------
# Order + Inline OrderFile
# -------------------
class OrderFileInline(admin.TabularInline):
    model = OrderFile
    extra = 0
    fields = ['file', 'uploaded_at', 'restricted']
    readonly_fields = ['uploaded_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'courier', 'shipping_date', 'comment']
    search_fields = ['tracking_number', 'courier', 'orders_coming__order', 'comment']
    list_filter = ['courier', 'shipping_date', 'orders_coming', 'arriving_date']
    inlines = [OrderFileInline]
    list_per_page = 20

# -------------------
# OrderFile
# -------------------
@admin.register(OrderFile)
class OrderFileAdmin(admin.ModelAdmin):
    list_display = ['order', 'file', 'uploaded_at', 'restricted']
    search_fields = ['order__tracking_number', 'order__courier']
    list_filter = ['order__courier', 'order__shipping_date', 'restricted']
    list_per_page = 20