from importlib.resources import files
from django.utils import timezone # type: ignore
from django.db import models # type: ignore
from django.contrib.auth.models import User # type: ignore
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError # type: ignore
    
class FlexibleDecimalField(models.DecimalField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(',', '.')
        try:
            return super().to_python(value)
        except (InvalidOperation, ValueError):
            return None
        


class Products(models.Model):
    order_Nmber = models.IntegerField(unique=True, null=False, blank=False)
    box_Nmber = models.IntegerField(null=False, blank=False)
    task = models.CharField(max_length=100, null=False, blank=False)
    qnt = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    edit_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Order: {self.order_Nmber}, Box: {self.box_Nmber}, Task: {self.task}, Qnt: {self.qnt}, Created at: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} by {self.edit_by.first_name if self.edit_by else 'N/A'}"
    
class ProductDeleteLog(models.Model):
    product_id = models.IntegerField()
    order_Nmber = models.IntegerField()
    task = models.CharField(max_length=100)
    deleted_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    deleted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Produto {self.order_Nmber} deletado por {self.deleted_by} em {self.deleted_at.strftime('%d/%m/%Y %H:%M')}"

class Jobs(models.Model):
    JOB_CHOICES = [
        ('F', 'F'),
        ('R', 'R'),
        ('P', 'P'),
        ('W', 'W'),
        ('N', 'N'),    
    ]
    
    job = models.CharField(max_length=1, choices=JOB_CHOICES, unique=True)
    descricao = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.get_job_display()}"

class Die(models.Model):
    DIE_CHOICES = [
        ('ND', 'ND'),
        ('PCD', 'PCD'),
        ('MCD', 'MCD'),
    ]

    die_type = models.CharField(max_length=3, choices=DIE_CHOICES, unique=True)
    descricao = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.get_die_type_display()}"
    
class Tolerance(models.Model):
    min = FlexibleDecimalField(max_digits=6, decimal_places=4)
    max = FlexibleDecimalField(max_digits=6, decimal_places=4)

    def __str__(self):
        return f"Tolerância: {self.min} - {self.max}"

class Diameters(models.Model):
    min = FlexibleDecimalField(max_digits=6, decimal_places=4)
    max = FlexibleDecimalField(max_digits=6, decimal_places=4)

    def __str__(self):
        return f"Diametro: {self.min} - {self.max}"

class QRData(models.Model):
    customer = models.CharField(max_length=100)
    diameters = models.CharField(max_length=50)  # original diameter
    customer_order_nr = models.CharField(max_length=50)  # customer order number
    toma_order_nr = models.CharField(max_length=50)
    toma_order_year = models.CharField(max_length=10)
    toma_order_full = models.CharField(max_length=20, unique=True, blank=True, null=True)  # novo campo único
    tolerance = models.ForeignKey(Tolerance, on_delete=models.SET_NULL, null=True, blank=True)
    box_nr = models.IntegerField()
    qt = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    observations = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.toma_order_full = f"{self.toma_order_year}-{self.toma_order_nr}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} - {self.toma_order_full} - {self.diameters} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    

class whereBox(models.Model):
    ONDESTA = [
        ('AFINACAO', 'Afinação'),
        ('POLIMENTO', 'Polimento'),
        ('DESBASTE_AGULHA', 'Desbaste Agulha'),
        ('DESBASTE_CALIBRE', 'Desbaste Calibre'),

    ]
    order_number = models.ForeignKey(QRData, on_delete=models.CASCADE, related_name='where_boxes')
    where = models.CharField(max_length=20, choices=ONDESTA, default='FIO')

    def __str__(self):
        return f"A Caixa {self.order_number.toma_order_nr} esta em no {self.get_where_display()}"
    
class WhereDie(models.Model):
    ONDESTA = [
        ('AFINACAO', 'Afinação'),
        ('POLIMENTO', 'Polimento'),
        ('DESBASTE_AGULHA', 'Desbaste Agulha'),
        ('DESBASTE_CALIBRE', 'Desbaste Calibre'),
    ]
    die = models.OneToOneField('dieInstance', on_delete=models.CASCADE)
    where = models.CharField(max_length=20, choices=ONDESTA, default='FIO')
    updated_at = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return f"{self.die.serial_number} - {self.get_where_display()}"


    
class globalLogs(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"



class dieInstance(models.Model):
    customer = models.ForeignKey(QRData, on_delete=models.CASCADE, related_name='die_instances')
    serial_number = models.CharField(max_length=20, unique=True, null=False, blank=False)
    diameter_text = models.CharField(max_length=50, blank=True, null=True)  # <-- Novo campo
    cone = models.CharField(max_length=10, blank=True, null=True)  # <-- Novo campo
    bearing = models.CharField(max_length=10, blank=True, null=True)  # <-- Novo campo
    diam_desbastado = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    diam_requerido = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    die = models.ForeignKey(Die, on_delete=models.CASCADE, related_name='instances')
    job = models.ForeignKey(Jobs, on_delete=models.CASCADE, related_name='die_instances')
    tolerance = models.ForeignKey(Tolerance, on_delete=models.CASCADE, related_name='die_instances', null=True, blank=True)
    diam_max_min = models.ForeignKey(Diameters, on_delete=models.CASCADE, related_name='die_instances_max_min', null=True, blank=True) 
    observations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f" Custumer {self.customer.customer} -  Die {self.serial_number} - {self.die.get_die_type_display()} - Trabalho - {self.job.get_job_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class NumeroPartidos(models.Model):
    qr_code = models.ForeignKey(QRData, on_delete=models.CASCADE)
    partido = models.IntegerField(null=False, blank=False)
    serie_dies_partidos = models.TextField(blank=True, null=True)
    checkbox = models.BooleanField(default=False, verbose_name="Feito")
    observations = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"QR Code: {self.qr_code.toma_order_nr} - Partido: {self.partido} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    

class PedidosDiametro(models.Model):
    qr_code = models.ForeignKey(QRData, on_delete=models.CASCADE)
    diametro = models.CharField(max_length=50)
    numero_fieiras = models.IntegerField()
    pedido_por = models.TextField(max_length=50, blank=True, null=True)
    serie_dies = models.TextField(blank=True, null=True)
    checkbox = models.BooleanField(default=False, verbose_name="Feito")
    observations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"QR Code: {self.qr_code.toma_order_nr} - {self.numero_fieiras} fieiras para diametro {self.diametro} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class DieWork(models.Model):
    die = models.ForeignKey('dieInstance', on_delete=models.CASCADE, related_name='works')
    work_type = models.CharField(max_length=20, choices=[
        ('polimento', 'Polimento'),
        ('desbaste_agulha', 'Desbaste Agulha'),
        ('desbaste_calibre', 'Desbaste Calibre'),
        ('afinacao', 'Afinação')
    ])
    subtype = models.CharField(max_length=20, null=True, blank=True)  # ex.: entrada, saída, cone
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_work_type_display()} - {self.die.serial_number}"


class DeliveryType(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=True)

    def __str__(self):
        return self.name

class DeliveryEntity(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

class DeliveryInfo(models.Model):
    identificator = models.ForeignKey(
        'QRData',
        to_field="toma_order_full",
        on_delete=models.CASCADE,
        db_column="identificator",
        null=True, blank=True
    )
    deliveryEntity = models.ForeignKey(
        DeliveryEntity,
        to_field="name",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    deliveryDate = models.DateField(null=True, blank=True)
    deliveryType = models.ForeignKey(
        DeliveryType,
        to_field="name",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    costumer = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        ent = self.deliveryEntity.name if self.deliveryEntity else 'N/A'
        return f"{self.identificator} - {ent} - {self.deliveryDate} - {self.deliveryType}"

    # --- Regras de negócio centralizadas no modelo ---
    def clean(self):
        super().clean()

        # Se não houver deliveryType, não aplicamos regras adicionais
        if not self.deliveryType:
            return

        dtype = (self.deliveryType.name or '').strip().lower()

        if dtype == 'customer':
            # precisa de identificator para sabermos o cliente
            if not self.identificator:
                raise ValidationError("Para Delivery Type = Customer, selecione um Identificator (QRData).")
            # não exigimos deliveryEntity aqui; será definido no save()
        elif dtype == 'supplier':
            # para Supplier, deliveryEntity é obrigatório
            if not self.deliveryEntity:
                raise ValidationError("Para Delivery Type = Supplier, selecione o Delivery Entity.")
        # outros tipos (se existirem) não têm regra específica aqui

    def save(self, *args, **kwargs):
        """
        Força as regras também no save para garantir consistência
        mesmo fora de ModelForms. Chamamos full_clean() para validar.
        """
        # valida antes de salvar
        self.full_clean()

        if self.identificator:
            # espelha sempre o nome do cliente do QR no campo costumer
            self.costumer = self.identificator.customer

        if self.deliveryType:
            dtype = (self.deliveryType.name or '').strip().lower()

            if dtype == 'customer':
                # força deliveryEntity = cliente do QRData
                customer_name = self.identificator.customer if self.identificator else None
                if customer_name:
                    ent, _ = DeliveryEntity.objects.get_or_create(name=customer_name)
                    self.deliveryEntity = ent

            # se for Supplier, mantemos o que veio do form (já validado no clean)

        return super().save(*args, **kwargs)
    

class DieWorkWorker(models.Model):
    work = models.ForeignKey('DieWork', on_delete=models.CASCADE, related_name='workers')
    worker = models.ForeignKey(User, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.get_full_name()} - {self.work}"

class OrdersComing(models.Model):
    order = models.CharField(max_length=500, blank=False, null=False)
    inspectionMetrology = models.BooleanField(default=False)
    preshipment = models.BooleanField(default=False)
    mark = models.BooleanField(default=False)
    urgent = models.BooleanField(default=False)
    done = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"OrdersComing {self.order}"

class Order(models.Model):
    # -- DHL, UPS, FedEx , SCHNENKER , TNT
    courier_choices = [
        'DHL',
        'UPS',
        'FedEx',
        'SCHENKER',
        'TNT'
    ]
    plant_choices = [
        'P2',
        'P3',
        'Toma'
    ]

    tracking_number = models.CharField(max_length=20, unique=True)
    orders_coming = models.ManyToManyField(OrdersComing, related_name='orders', blank=True)
    plant = models.CharField(max_length=6, choices=[(p, p) for p in plant_choices], blank=True, null=True)
    courier = models.CharField(max_length=100, choices=[(c, c) for c in courier_choices], blank=True, null=True)
    shipping_date = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"Order {self.tracking_number}, {self.courier}, {self.shipping_date}"

class OrderFile(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='order_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    restricted = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.file.name}"

    

