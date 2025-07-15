from django.utils import timezone # type: ignore
from django.db import models # type: ignore
from django.contrib.auth.models import User # type: ignore

    
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
        ('F', 'Final'),
        ('R', 'Recondicionado'),
        ('P', 'Polimento'),
        ('W', 'Com o mesmo diametro(W)'),
        ('N', 'Novo'),    
    ]
    
    job = models.CharField(max_length=1, choices=JOB_CHOICES, unique=True)
    descricao = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.get_job_display()}"

class Die(models.Model):
    DIE_CHOICES = [
        ('ND', 'Diamante Natural'),
        ('PCD', 'Policristalino'),
        ('MCD', 'Monocristalino'),
    ]

    die_type = models.CharField(max_length=3, choices=DIE_CHOICES, unique=True)
    descricao = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.get_die_type_display()}"
    
class Tolerance(models.Model):
    min = models.DecimalField(max_digits=6, decimal_places=4) 
    max = models.DecimalField(max_digits=6, decimal_places=4)

    def __str__(self):
        return f"Tolerância: {self.min} - {self.max}"
    
class Diameters(models.Model):
    min = models.DecimalField(max_digits=6, decimal_places=4) 
    max = models.DecimalField(max_digits=6, decimal_places=4)

    def __str__(self):
        return f"Diametro: {self.min} - {self.max}"

class Worker(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Polimento(models.Model):
    TIPO_TRABALHO = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('cone', 'Cone'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_TRABALHO)
    qr_code = models.ForeignKey('theme.QRData', on_delete=models.CASCADE, related_name='polimentos',null=True, blank=True)
    workers = models.ManyToManyField(User, through='PolimentoWorker')

    def __str__(self):
        return f"{self.tipo.capitalize()} - ID {self.id} - QR Code: {self.qr_code.toma_order_nr if self.qr_code else 'N/A'} - {self.qr_code.customer if self.qr_code else 'N/A'}"


class PolimentoWorker(models.Model):
    polimento = models.ForeignKey('Polimento', on_delete=models.CASCADE)
    worker = models.ForeignKey(User, on_delete=models.CASCADE)  # Aqui usas User
    data = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.worker.get_full_name() or self.worker.username} em {self.polimento.tipo} (ID {self.polimento.id}) ({self.data.strftime('%Y-%m-%d %H:%M')})"



class DesbasteAgulha(models.Model):
    TIPO_TRABALHO = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('cone', 'Cone'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_TRABALHO)
    qr_code = models.ForeignKey('theme.QRData', on_delete=models.CASCADE, related_name='DesbasteAgulhas', null=True, blank=True)
    workers = models.ManyToManyField(User, through='DesbasteAgulhaWorker')

    def __str__(self):
        return f"{self.tipo.capitalize()} - ID {self.id} - QR Code: {self.qr_code.toma_order_nr if self.qr_code else 'N/A'} - {self.qr_code.customer if self.qr_code else 'N/A'}"


class DesbasteAgulhaWorker(models.Model):
    desbaste_agulha = models.ForeignKey('DesbasteAgulha', on_delete=models.CASCADE)
    worker = models.ForeignKey(User, on_delete=models.CASCADE)  # Aqui usas User
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.get_full_name() or self.worker.username} em {self.desbaste_agulha.tipo} (ID {self.desbaste_agulha.id}) ({self.data.strftime('%Y-%m-%d %H:%M')})"




class DesbasteCalibre(models.Model):
    TIPO_TRABALHO = [
        ('polimento De Calibre', 'Polimento de Calibre'),
        ('desbaste De Calibre', 'Desbaste de Calibre'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_TRABALHO)
    qr_code = models.ForeignKey('theme.QRData', on_delete=models.CASCADE, related_name='DesbasteCalibres', null=True, blank=True)
    workers = models.ManyToManyField(User, through='DesbasteCalibreWorker')

    def __str__(self):
        return f"{self.tipo.capitalize()} - ID {self.id} - QR Code: {self.qr_code.toma_order_nr if self.qr_code else 'N/A'} - {self.qr_code.customer if self.qr_code else 'N/A'}"


class DesbasteCalibreWorker(models.Model):
    desbaste_calibre = models.ForeignKey('DesbasteCalibre', on_delete=models.CASCADE)
    worker = models.ForeignKey(User, on_delete=models.CASCADE)  # Aqui usas User
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.get_full_name() or self.worker.username} em {self.desbaste_calibre.tipo} (ID {self.desbaste_calibre.id}) ({self.data.strftime('%Y-%m-%d %H:%M')})"




class Afinacao(models.Model):
    TIPO_TRABALHO = [
        ('calibre', 'Calibre'),
        ('afinacao', 'Afinação'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_TRABALHO)
    qr_code = models.ForeignKey('theme.QRData', on_delete=models.CASCADE, related_name='Afinacoes', null=True, blank=True)
    workers = models.ManyToManyField(User, through='AfinacaoWorker')

    def __str__(self):
        return f"{self.tipo.capitalize()} - ID {self.id}"


class AfinacaoWorker(models.Model):
    afinacao = models.ForeignKey('Afinacao', on_delete=models.CASCADE)
    worker = models.ForeignKey(User, on_delete=models.CASCADE)  # Aqui usas User
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.get_full_name() or self.worker.username} em {self.afinacao.tipo} (ID {self.afinacao.id}) ({self.data.strftime('%Y-%m-%d %H:%M')})"







class QRData(models.Model):
    customer = models.CharField(max_length=100)
    diameters = models.CharField(max_length=50)  #original diameter
    customer_order_nr = models.CharField(max_length=50)
    toma_order_nr = models.CharField(max_length=50) 
    tolerance = models.ForeignKey(Tolerance, on_delete=models.SET_NULL, null=True, blank=True) # type of tolerance
    toma_order_year = models.CharField(max_length=10)
    box_nr = models.IntegerField()
    qt = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    observations = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer} - {self.toma_order_nr} - {self.diameters} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    


class dieInstance(models.Model):
    customer = models.ForeignKey(QRData, on_delete=models.CASCADE, related_name='die_instances')
    serial_number = models.CharField(max_length=20, unique=True, null=False, blank=False)
    diameter_text = models.CharField(max_length=50, blank=True, null=True)  # <-- Novo campo
    diam_desbastado = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    diam_requerido = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)  # requerido
    die = models.ForeignKey(Die, on_delete=models.CASCADE, related_name='instances')
    job = models.ForeignKey(Jobs, on_delete=models.CASCADE, related_name='die_instances')
    tolerance = models.ForeignKey(Tolerance, on_delete=models.CASCADE, related_name='die_instances', null=True, blank=True)
    diam_max_min = models.ForeignKey(Diameters, on_delete=models.CASCADE, related_name='die_instances_max_min', null=True, blank=True) 
    observations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    polimento = models.ForeignKey(Polimento, on_delete=models.SET_NULL, null=True, blank=True)
    desbaste_agulha = models.ForeignKey(DesbasteAgulha, on_delete=models.SET_NULL, null=True, blank=True) 
    desbaste_calibre  = models.ForeignKey(DesbasteCalibre, on_delete=models.SET_NULL, null=True, blank=True)
    afinacao = models.ForeignKey(Afinacao, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Die {self.serial_number} - {self.die.get_die_type_display()} - Job: {self.job.get_job_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"




    
class NumeroPartidos(models.Model):
    qr_code = models.ForeignKey(QRData, on_delete=models.CASCADE)
    partido = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"QR Code: {self.qr_code.toma_order_nr} - Partido: {self.partido} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    

class PedidosDiametro(models.Model):
    qr_code = models.ForeignKey(QRData, on_delete=models.CASCADE)
    diametro = models.CharField(max_length=50)
    numero_fieiras = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"QR Code: {self.qr_code.toma_order_nr} - {self.numero_fieiras} fieiras para diametro {self.diametro} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

