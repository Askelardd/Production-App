from datetime import date
from importlib.resources import files
from pyclbr import Class
from urllib import request
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
        ('F', 'Final(F)'),
        ('R', 'Recondicionado(R)'),
        ('P', 'Polir(P)'),
        ('W', 'Com o mesmo diametro(W)'),
        ('N', 'Novo(N)'),    
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
    min = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    max = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    def __str__(self):
        return f"Tolerância: {self.min} - {self.max}"

class Diameters(models.Model):
    min = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    max = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    def __str__(self):
        return f"Diametro: {self.min} - {self.max}"

class QRData(models.Model):
    customer = models.CharField(max_length=100)
    diameters = models.CharField(max_length=50)  # original diameter
    customer_order_nr = models.CharField(max_length=50, blank=False, null=False)  # customer order number
    toma_order_nr = models.CharField(max_length=50)
    toma_order_year = models.CharField(max_length=10)
    toma_order_full = models.CharField(max_length=20, unique=True, blank=True, null=True)  # novo campo único
    box_nr = models.CharField(max_length=10)
    qt = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    production_start = models.DateField(blank=True, null=True)
    envio = models.DateField(blank=True, null=True)
    observations = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.toma_order_full = f"{self.toma_order_year}-{self.toma_order_nr}-{self.box_nr}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} - {self.toma_order_full} - {self.diameters} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    

class whereBox(models.Model):
    ONDESTA = [
        ('AFINACAO', 'Afinação'),
        ('POLIMENTO', 'Polimento'),
        ('DESBASTE_AGULHA', 'Desbaste Agulha'),
        ('DESBASTE_CALIBRE', 'Desbaste Calibre'),
        ('INSPEÇÃO_FINAL', 'Inspeção Final'),
        ('METROLOGY', 'Metrology'),
        ('FECHADO', 'Fechado'),

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
        ('INSPEÇÃO_FINAL', 'Inspeção Final'),
        ('METROLOGY', 'Metrology'),
        ('FECHADO', 'Fechado'),
    ]
    die = models.ForeignKey('dieInstance', on_delete=models.CASCADE, related_name='locations')
    where = models.CharField(max_length=20, choices=ONDESTA)
    updated_at = models.DateTimeField(auto_now_add=True)

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
    cone = models.CharField(max_length=20)  
    bearing = models.CharField(max_length=100)  
    bearing_is_red = models.BooleanField(default=False)  
    diam_requerido = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    die = models.ForeignKey(Die, on_delete=models.CASCADE, related_name='instances')
    job = models.ForeignKey(Jobs, on_delete=models.CASCADE, related_name='die_instances')
    tolerance = models.ForeignKey(Tolerance, on_delete=models.CASCADE, related_name='die_instances', null=True, blank=True)
    new_diameter = models.CharField(max_length=50, blank=True, null=True)  
    partida = models.BooleanField(default=False)
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
    observations = models.TextField(blank=False, null=False)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"QR Code: {self.qr_code.toma_order_nr} - Partido: {self.partido} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    

class PedidosDiametro(models.Model):
    qr_code = models.ForeignKey(QRData, on_delete=models.CASCADE)
    diametro = models.CharField(max_length=50)
    diametro_min = FlexibleDecimalField(max_digits=6, decimal_places=4, null=False, blank=False)
    novo_diametro = models.CharField(max_length=50, null=True, blank=True)
    numero_fieiras = models.IntegerField()
    trabalhado = models.BooleanField(default=False, verbose_name="Trabalhado")
    pedido_por = models.TextField(max_length=50, blank=False, null=False)
    serie_dies = models.TextField(blank=False, null=False)
    checkbox = models.BooleanField(default=False, verbose_name="Feito")
    observations = models.CharField(
        max_length=50,
        choices=[
            ('buraco_no_cone', 'Buraco no Cone'),
            ('buraco_no_calibre', 'Buraco no Calibre'),
            ('riscos_cone', 'Riscos no Cone'),
            ('riscos_calibre', 'Riscos no Calibre'),
            ('margem', 'Margem'),
            ('outros', 'Outros'),
        ],
        default='buraco_no_cone'
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"QR Code: {self.qr_code.toma_order_nr} - {self.numero_fieiras} fieiras para diametro {self.diametro} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


    

class InfoFieira(models.Model):
    serial_number = models.CharField(max_length=20)
    data_criacao = models.DateField(auto_now_add=True)
    diametro_atual = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    angulo = models.CharField(max_length=30, null=True, blank=True)
    po = models.CharField(max_length=30, null=True, blank=True)
    tempo = models.CharField(max_length=8, null=True, blank=True)
    quando = models.DateTimeField(default=timezone.now)
    observacoes = models.TextField(blank=True, null=True)
    utilizador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.serial_number

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

class DieWork(models.Model):
    die = models.ForeignKey('dieInstance', on_delete=models.CASCADE, related_name='works')
    work_type = models.CharField(max_length=20, choices=[
        ('polimento', 'Polimento'),
        ('desbaste_agulha', 'Desbaste Agulha'),
        ('desbaste_calibre', 'Desbaste Calibre'),
        ('afinacao', 'Afinação')
    ])
    subtype = models.CharField(max_length=20, null=True, blank=True)  # ex.: entrada, saída, cone
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.get_work_type_display()} - {self.die.serial_number}"

class DieWorkWorker(models.Model):
    work = models.ForeignKey('DieWork', on_delete=models.CASCADE, related_name='workers')
    worker = models.ForeignKey(User, on_delete=models.CASCADE)
    diam_min = FlexibleDecimalField(max_digits=6, decimal_places=4, null=False, blank=False)
    diam_max = FlexibleDecimalField(max_digits=6, decimal_places=4, null=False, blank=False)
    added_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.worker.get_full_name()} - {self.work}"

class OrdersComing(models.Model):
    order = models.CharField(max_length=500, blank=False, null=False)
    inspectionMetrology = models.BooleanField(default=False)
    preshipment = models.BooleanField(default=False)
    days_2_3 = models.BooleanField(default=False)
    days_3_4 = models.BooleanField(default=False)
    recondicioning = models.BooleanField(default=False)
    semifinished = models.BooleanField(default=False)
    casing = models.BooleanField(default=False)
    mark = models.BooleanField(default=False)
    urgent = models.BooleanField(default=False)
    done = models.BooleanField(default=False)
    data_done = models.DateField(null=True, blank=True)
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
        'Toma',
        'Spider Extrusion',
        'Paganoni',
        'Outros',
    ]

    tracking_number = models.CharField(max_length=20, unique=True)
    orders_coming = models.ManyToManyField(OrdersComing, related_name='orders', blank=True)
    plant = models.CharField(max_length=30, choices=[(p, p) for p in plant_choices], blank=True, null=True)
    courier = models.CharField(max_length=100, choices=[(c, c) for c in courier_choices], blank=True, null=True)
    shipping_date = models.DateField(null=True, blank=True)
    arriving_date = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    exportado = models.BooleanField(default=False)


    def __str__(self):
        return f"Order {self.tracking_number}, {self.courier}, {self.shipping_date}"

class OrderFile(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='order_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    restricted = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.file.name}"

    

class Tracking(models.Model):
    finalidade_choices = [
        ('Importacao', 'Importação'),
        ('Exportacao', 'Exportação'),
    ]
    courier_choices = [
        'DHL',
        'UPS',
        'FedEx',
        'SCHENKER',
        'TNT',
        'NACEX',
        'Outros',
    ]

    data = models.DateField()
    finalidade = models.CharField(max_length=20, choices=finalidade_choices)
    crm = models.CharField(max_length=100)
    transportadora = models.CharField(max_length=20, choices=[(c, c) for c in courier_choices])
    carta_de_porte = models.CharField(max_length=100, blank=True, null=True)
    numero_recolha = models.CharField(max_length=100, blank=True, null=True)
    recebido_por = models.CharField(max_length=100, blank=True, null=True) # recebido_por
    data_entrega = models.DateField(blank=True, null=True)
    cliente = models.CharField(max_length=100, blank=True, null=True) # passar para texto
    email = models.CharField(max_length=100, blank=True, null=True) # passar para texto
    enviado = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True, null=True)
    files = models.ManyToManyField('TrackingFile', related_name='trackings', blank=True)

    def __str__(self):
        return f"{self.data} - {self.finalidade} - {self.crm} - {self.cliente} - {self.transportadora}"


class TrackingFile(models.Model):
    file = models.FileField(upload_to='tracking_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name}"
    

class Maquinas(models.Model):
    machine_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.machine_name}"
    
class MedidasMaquinas(models.Model):
    serie_number = models.CharField(max_length=50) 
    diameter = FlexibleDecimalField(max_digits=6, decimal_places=4)

    def __str__(self):
        return f"Nr Série: {self.serie_number} - Diâmetro: {self.diameter}"

class Medicao(models.Model):
    machine = models.ForeignKey(Maquinas, on_delete=models.CASCADE, related_name='medicoes')
    diameter = models.ForeignKey(MedidasMaquinas, on_delete=models.CASCADE, related_name='medicoes')
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Máquina: {self.machine.machine_name} - Medida: {self.diameter.serie_number} - Data: {self.date.strftime('%Y-%m-%d %H:%M')}"

class DetalhesMedicao(models.Model):
    read_number = models.IntegerField()
    diameter = FlexibleDecimalField(max_digits=6, decimal_places=4)
    bearing = models.CharField(max_length=100, blank=True, null=True)
    ovality = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    toleranciaMin = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    toleranciaMax = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    medicao = models.ForeignKey(Medicao, on_delete=models.CASCADE, related_name='detalhes')
    operador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"Medicao ID: {self.medicao.id} - Operador: {self.operador.get_full_name() if self.operador else 'N/A'}"
    
class CalibracaoMaquina(models.Model):
    machine = models.ForeignKey(Maquinas, on_delete=models.CASCADE, related_name='calibracoes')
    diam_original = FlexibleDecimalField(max_digits=6, decimal_places=4)
    diam_calibrado = FlexibleDecimalField(max_digits=6, decimal_places=4)
    diam_calibrado_max = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    diam_calibrado_min = FlexibleDecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    operador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Calibração da Máquina: {self.machine.machine_name} - Data: {self.date.strftime('%Y-%m-%d %H:%M')} - Operador: {self.operador.get_full_name() if self.operador else 'N/A'}"
    

class faturas(models.Model):
    fornecedor = models.ForeignKey('Fornecedor', on_delete=models.CASCADE, related_name='faturas')
    fatura_unica = models.CharField(max_length=100, unique=True, null=False, blank=False)
    numero_fatura = models.CharField(max_length=100)
    data_fatura = models.DateField(null=True, blank=True)
    data_emissao = models.DateField()
    valor = FlexibleDecimalField(max_digits=10, decimal_places=2)
    pago = models.BooleanField(default=False)
    descricao = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        self.fatura_unica = f"{self.fornecedor.name}-{self.numero_fatura}"
        super().save(*args, **kwargs)

    @property
    def is_urgent(self):
        # Se já está pago, nunca é urgente
        if self.pago:
            return False
        
        # Se não tem data, não calculamos (segurança)
        if not self.data_fatura:
            return False

        # Calcula dias restantes
        dias_restantes = (self.data_fatura - date.today()).days
        
        # É urgente se faltarem 7 dias ou menos (ou se já tiver passado o prazo)
        return dias_restantes <= 7

    def __str__(self):
        # Verifica se existe data antes de formatar
        if self.data_fatura:
            data_texto = self.data_fatura.strftime('%Y-%m-%d')
        else:
            data_texto = "Débito Direto"

        return f"Fatura {self.numero_fatura} do Fornecedor {self.fornecedor.name} - Valor: {self.valor} - Data: {data_texto}"

class FaturaFile(models.Model):
    fatura = models.ForeignKey(faturas, on_delete=models.CASCADE, related_name='ficheiros')
    file = models.FileField(upload_to='faturas_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} - fatura - {self.fatura.numero_fatura}"
    
class FaturaEstrangeitoFile(models.Model):
    fatura = models.ForeignKey(faturas, on_delete=models.CASCADE, related_name='ficheiros_estrangeiro')
    file = models.FileField(upload_to='faturas_files_estrangeiro/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} - fatura - {self.fatura.numero_fatura}"
    

class FaturaPagoFile(models.Model):
    fatura = models.ForeignKey(faturas, on_delete=models.CASCADE, related_name='ficheiros_pago')
    file = models.FileField(upload_to='faturas_files_pago/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} - fatura - {self.fatura.numero_fatura}"


class Fornecedor(models.Model):
    name = models.CharField(max_length=100, unique=True)
    debito_direto = models.BooleanField(default=False)
    email = models.TextField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    dados_bancarios = models.TextField(blank=True, null=True)
    vat = models.CharField(max_length=50, blank=True, null=True)
    morada = models.TextField(blank=True, null=True)
    estrangeiro = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name }- VAT: {self.vat} - Debito Direto: {'Sim' if self.debito_direto else 'Não'} estrangeiro: {'Sim' if self.estrangeiro else 'Não'}"
    

class Template(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateField(default=timezone.now)
    approved = models.BooleanField(default=False)
    approved_by = models.CharField(max_length=20, blank=True, null=True)
    last_updated = models.DateField(null=True, blank=True, default=timezone.now)
    editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_file = models.FileField(upload_to='approved_templates_files/', null=True, blank=True)
    

    def __str__(self):
        return f"{self.name} - {self.department}"
    
class TemplateFiles(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='templates_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} - template - {self.template.name}"