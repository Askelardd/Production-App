import json
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render # type: ignore
from django.contrib import messages # type: ignore
from django.contrib.auth.models import User # type: ignore
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from .models import *
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.shortcuts import render, redirect

def home(request):
    users = User.objects.all()
    return render(request, 'theme/home.html', {'users': users})

def create_user(request):  
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        password = request.POST.get('password')

        if not first_name or not password:
            context = {
                'error_message': 'Todos os campos são obrigatórios.'
            }
            return render(request, 'theme/createUser.html', context)

        # Verifica se o utilizador já existe (opcional)
        if User.objects.filter(username=first_name).exists():
            context = {
                'error_message': 'Este nome de utilizador já existe.'
            }
            return render(request, 'theme/createUser.html', context)

        # Cria o utilizador na base de dados
        User.objects.create_user(username=first_name, password=password)

        # Redireciona para a página inicial após criar o utilizador
        return redirect('home')
    
    return render(request, 'theme/createUser.html')

@login_required
def productionMenu(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Utilizador não encontrado.')
        return redirect('home')
    
    # Verifica se o utilizador logado está a tentar ver outro perfil
    if request.user.id != user.id:
        messages.error(request, 'Acesso negado.')
        return redirect('home')

    return render(request, 'theme/productionMenu.html', {'user': user})

from django.contrib.auth import login as auth_login
from django.views.decorators.csrf import csrf_exempt

def login_view(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Utilizador não encontrado.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')

        user = authenticate(request, username=user.username, password=password)
        if user is not None:
            auth_login(request, user)  # faz o login
            return redirect('productionMenu', user_id=user.id)
        else:
            messages.error(request, 'Palavra-passe incorreta.')

    return render(request, 'theme/login.html', {'user': user})

def inputProduction(request):
    products = Products.objects.all().order_by('-created_at')
    return render(request, 'theme/inputProduction.html', {'products': products})

@login_required
def editProduct(request, produto_id):
    product = get_object_or_404(Products, id= produto_id)

    if request.method == 'POST':
        product.order_Nmber = request.POST.get('order_Nmber')
        product.box_Nmber = request.POST.get('box_Nmber')
        product.task = request.POST.get('task')
        product.qnt = request.POST.get('qnt')
        product.edit_by = request.user

        product.save()
        return redirect('inputProduction')

    return render(request, 'theme/editProduct.html', {'product': product})

@login_required
def deleteProduct(request, produto_id):
    product = get_object_or_404(Products, id=produto_id)

    if request.method == 'POST':
        ProductDeleteLog.objects.create(
            product_id=product.id,
            order_Nmber=product.order_Nmber,
            task=product.task,
            deleted_by=request.user
        )
        product.delete()
        return redirect('inputProduction')

    return render(request, 'theme/confirmDelete.html', {'product': product})

def listQrcodes(request):
    qrcodes = QRData.objects.all().order_by('-created_at')
    return render(request, 'theme/listQrcodes.html', {'qrcodes': qrcodes})

import json
import logging
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import QRData

# Configure logging
logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
def scanBox(request):
    if request.method == 'GET':
        return render(request, 'theme/scanBox.html')
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Log dos dados recebidos para debug
            logger.info(f"Dados recebidos: {data}")
            
            # Verificação de campos obrigatórios
            if not data.get('toma_order_nr') or not data.get('box_nr'):
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Campos obrigatórios em falta (toma_order_nr, box_nr).'
                }, status=400)
            
            # Conversão segura de números
            try:
                box_nr = int(data.get('box_nr', 0)) if data.get('box_nr') else 0
            except (ValueError, TypeError):
                box_nr = 0
                
            try:
                qt = int(data.get('qt', 0)) if data.get('qt') else 0
            except (ValueError, TypeError):
                qt = 0
            
            # Obter diameters com fallbacks
            diameters = (
                data.get('diameters') or 
                data.get('diameter') or 
                data.get('diametro') or 
                data.get('diametros') or 
                ''
            )
            
            # Log específico para diameters
            logger.info(f"Diameter value: '{diameters}'")
            
            # Inserção na base de dados
            qr_record = QRData.objects.create(
                customer=data.get('customer', ''),
                customer_order_nr=data.get('customer_order_nr', ''),
                toma_order_nr=data.get('toma_order_nr', ''),
                toma_order_year=data.get('toma_order_year', ''),
                box_nr=box_nr,
                qt=qt,
                diameters=diameters,
                created_at=timezone.now()
            )
            
            logger.info(f"QR Record criado com ID: {qr_record.id}, diameters: '{qr_record.diameters}'")
            
            return JsonResponse({
                'status': 'success', 
                'message': 'QR Code registado com sucesso!',
                'data': {
                    'id': qr_record.id,
                    'diameters': qr_record.diameters
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error', 
                'message': 'Dados JSON inválidos.'
            }, status=400)
        except Exception as e:
            logger.error(f"Erro ao processar QR Code: {str(e)}")
            return JsonResponse({
                'status': 'error', 
                'message': f'Erro interno: {str(e)}'
            }, status=500)


def partidosMenu(request, qrCode_id):
    try:
        qr_code = QRData.objects.get(toma_order_nr=qrCode_id)
    except QRData.DoesNotExist:
        messages.error(request, 'QR Code não encontrado.')
        return redirect('listQrcodes')
    
    if request.method == 'POST':
        numero = request.POST.get('numeroPartidos')

        try:
            partido = int(numero)
            if partido <= 0:
                messages.error(request, 'O número do partido deve ser um número positivo.')
            else:
                NumeroPartidos.objects.create(qr_code=qr_code, partido=partido)
                messages.success(request, f'Partido {partido} adicionado com sucesso!')
        except ValueError:
            messages.error(request, 'Número do partido inválido. Por favor, insira um número válido.')
        except Exception as e:
            messages.error(request, f'Erro ao adicionar partido: {str(e)}')

    return render(request, 'theme/partidosMenu.html', {'qr_code': qr_code})

def diametroMenu(request, qrCode_id):
    try:
        qr_code = QRData.objects.get(toma_order_nr=qrCode_id)
    except QRData.DoesNotExist:
        messages.error(request, 'QR Code não encontrado.')
        return redirect('listQrcodes')
    
    if request.method == 'POST':
        numero = request.POST.get('numeroAlterar')
        diametro = request.POST.get('diametroNovo')

        try:
            numero = int(numero)
            if numero <= 0:
                messages.error(request, 'O número de fieiras deve ser positivo.')
            elif not diametro:
                messages.error(request, 'Por favor, insira o valor do diâmetro.')
            else:
                PedidosDiametro.objects.create(
                    qr_code=qr_code,
                    diametro=diametro,
                    numero_fieiras=numero
                )
                messages.success(request, f'Pedido de diâmetro {diametro} para {numero} fieiras adicionado com sucesso!')
        except ValueError:
            messages.error(request, 'Número de fieiras inválido. Por favor, insira um número válido.')
        except Exception as e:
            messages.error(request, f'Erro ao adicionar pedido: {str(e)}')

    return render(request, 'theme/diametroMenu.html', {'qr_code': qr_code})



def adicionar_trabalho(request, qr_id):
    qr_code = get_object_or_404(QRData, id=qr_id)

    subtipo_options = {
        'fio': Fio.TIPO_TRABALHO,
        'desbaste': Desbaste.TIPO_TRABALHO,
        'polimento': Polimento.TIPO_TRABALHO,
    }

    subtipo_json = json.dumps(subtipo_options)

    if request.method == 'POST':
        tipo = request.POST.get('tipo_trabalho')
        subtipo = request.POST.get('subtipo')

        if tipo == 'fio':
            trabalho = Fio.objects.create(tipo=subtipo, qr_code=qr_code)
            return redirect('adicionarFioWorker', fio_id=trabalho.id)

        elif tipo == 'desbaste':
            trabalho = Desbaste.objects.create(tipo=subtipo, qr_code=qr_code)
            return redirect('adicionarDesbasteWorker', desbaste_id=trabalho.id)

        elif tipo == 'polimento':
            trabalho = Polimento.objects.create(tipo=subtipo, qr_code=qr_code)
            return redirect('adicionarPolimentoWorker', polimento_id=trabalho.id)

        messages.error(request, "Tipo de trabalho inválido.")
        return redirect('adicionarTrabalhos', qr_id=qr_id)

    return render(request, 'theme/adicionarTrabalhos.html', {
        'qr_code': qr_code,
        'subtipo_json': subtipo_json
    })


def adicionarFioWorker(request, fio_id):
    fio = get_object_or_404(Fio, id=fio_id)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('worker')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            FioWorker.objects.create(Fio=fio, worker=user)
            messages.success(request, f'{user.get_full_name()} adicionado ao trabalho de Fio.')
            return redirect('adicionarFioWorker', fio_id=fio.id)
        else:
            messages.error(request, 'Seleciona um trabalhador.')

    return render(request, 'theme/adicionarFioWorker.html', {'fio': fio, 'users': users})

def adicionarDesbasteWorker(request, desbaste_id):
    desbaste = get_object_or_404(Desbaste, id=desbaste_id)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('worker')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            DesbasteWorker.objects.create(desbaste=desbaste, worker=user)
            messages.success(request, f'{user.get_full_name()} adicionado ao trabalho de Desbaste.')
            return redirect('adicionarDesbasteWorker', desbaste_id=desbaste.id)

    return render(request, 'theme/adicionarDesbasteWorker.html', {'desbaste': desbaste, 'users': users})

def adicionarPolimentoWorker(request, polimento_id):
    polimento = get_object_or_404(Polimento, id=polimento_id)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('worker')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            PolimentoWorker.objects.create(polimento=polimento, worker=user)
            messages.success(request, f'{user.get_full_name()} adicionado ao trabalho de Polimento.')
            return redirect('adicionarPolimentoWorker', polimento_id=polimento.id)

    return render(request, 'theme/adicionarPolimentoWorker.html', {'polimento': polimento, 'users': users})


def detalhesQrcode(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)

    fios = Fio.objects.filter(qr_code=qr)
    desbastes = Desbaste.objects.filter(qr_code=qr)
    polimentos = Polimento.objects.filter(qr_code=qr)

    diametros = PedidosDiametro.objects.filter(qr_code=qr)
    partidos = NumeroPartidos.objects.filter(qr_code=qr)

    context = {
        'qr': qr,
        'fios': fios,
        'desbastes': desbastes,
        'polimentos': polimentos,
        'diametros': diametros,
        'partidos': partidos,
    }

    return render(request, 'theme/detalhesQrcode.html', context)

    