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

class Desbaste(models.Model):
    TIPO_TRABALHO = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('cone', 'Cone'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPO_TRABALHO)
    workers = models.ManyToManyField(User, through='DesbasteWorker')

    def __str__(self):
        return f"{self.tipo.capitalize()} - ID {self.id}"


class DesbasteWorker(models.Model):
    desbaste = models.ForeignKey('Desbaste', on_delete=models.CASCADE)
    worker = models.ForeignKey(User, on_delete=models.CASCADE)  # Aqui usas User
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.get_full_name() or self.worker.username} em {self.desbaste.tipo}(ID {self.desbaste.id}) ({self.data.strftime('%Y-%m-%d %H:%M')})"

class Polimento(models.Model):
    TIPO_TRABALHO = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('cone', 'Cone'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_TRABALHO)
    workers = models.ManyToManyField(User, through='PolimentoWorker')

    def __str__(self):
        return f"{self.tipo.capitalize()} - ID {self.id}"


class PolimentoWorker(models.Model):
    polimento = models.ForeignKey('Polimento', on_delete=models.CASCADE)
    worker = models.ForeignKey(User, on_delete=models.CASCADE)  # Aqui usas User
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.get_full_name() or self.worker.username} em {self.polimento.tipo} (ID {self.polimento.id}) ({self.data.strftime('%Y-%m-%d %H:%M')})"

class Fio(models.Model):
    TIPO_TRABALHO = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('cone', 'Cone'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_TRABALHO)
    workers = models.ManyToManyField(User, through='FioWorker')

    def __str__(self):
        return f"{self.tipo.capitalize()} - ID {self.id}"


class FioWorker(models.Model):
    Fio = models.ForeignKey('Fio', on_delete=models.CASCADE)
    worker = models.ForeignKey(User, on_delete=models.CASCADE)  # Aqui usas User
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.get_full_name() or self.worker.username} em {self.Fio.tipo} (ID {self.Fio.id}) ({self.data.strftime('%Y-%m-%d %H:%M')})"



class QRData(models.Model):
    customer = models.CharField(max_length=100)
    customer_order_nr = models.CharField(max_length=50)
    toma_order_nr = models.CharField(max_length=50) 
    job = models.ForeignKey(Jobs, on_delete=models.SET_NULL, null=True, blank=True)
    die = models.ForeignKey(Die, on_delete=models.SET_NULL, null=True, blank=True)
    tolerance = models.ForeignKey(Tolerance, on_delete=models.SET_NULL, null=True, blank=True)
    diameter = models.ForeignKey(Diameters, on_delete=models.SET_NULL, null=True, blank=True)
    desbaste = models.ForeignKey(Desbaste, on_delete=models.SET_NULL, null=True, blank=True)
    polimento = models.ForeignKey(Polimento, on_delete=models.SET_NULL, null=True, blank=True)
    fio = models.ForeignKey(Fio, on_delete=models.SET_NULL, null=True, blank=True)

    toma_order_year = models.CharField(max_length=10)
    box_nr = models.IntegerField()
    qt = models.IntegerField()
    diameters = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=timezone.now)
    observations = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer} - {self.toma_order_nr}"
    
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

