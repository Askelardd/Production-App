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
        'desbasteAgulha': DesbasteAgulha.TIPO_TRABALHO,
        'desbasteCalibre': DesbasteCalibre.TIPO_TRABALHO,
        'polimento': Polimento.TIPO_TRABALHO,
        'afinacao': Afinacao.TIPO_TRABALHO,
    }

    subtipo_json = json.dumps(subtipo_options)

    if request.method == 'POST':
        tipo = request.POST.get('tipo_trabalho')
        subtipo = request.POST.get('subtipo')

        if tipo == 'desbasteAgulha':
            trabalho = DesbasteAgulha.objects.create(tipo=subtipo, qr_code=qr_code)
            return redirect('adicionarDesbasteAgulhaWorker', desbaste_agulha_id=trabalho.id)

        elif tipo == 'desbasteCalibre':
            trabalho = DesbasteCalibre.objects.create(tipo=subtipo, qr_code=qr_code)
            return redirect('adicionarDesbasteCalibreWorker', desbasteCalibre_id=trabalho.id)

        elif tipo == 'polimento':
            trabalho = Polimento.objects.create(tipo=subtipo, qr_code=qr_code)
            return redirect('adicionarPolimentoWorker', polimento_id=trabalho.id)

        elif tipo == 'afinacao':
            trabalho = Afinacao.objects.create(tipo=subtipo, qr_code=qr_code)
            return redirect('adicionarAfinacaoWorker', afinacao_id=trabalho.id)

        messages.error(request, "Tipo de trabalho inválido.")
        return redirect('adicionarTrabalhos', qr_id=qr_id)

    return render(request, 'theme/adicionarTrabalhos.html', {
        'qr_code': qr_code,
        'subtipo_json': subtipo_json
    })


def adicionarDesbasteAgulhaWorker(request, desbaste_agulha_id):
    desbaste_agulha = get_object_or_404(DesbasteAgulha, id=desbaste_agulha_id)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('worker')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            DesbasteAgulhaWorker.objects.create(desbaste_agulha=desbaste_agulha, worker=user)
            messages.success(request, f'{user.get_full_name() or user.username} adicionado ao trabalho de Desbaste Agulha.')
            return redirect('adicionarDesbasteAgulhaWorker', desbaste_agulha_id=desbaste_agulha.id)
        else:
            messages.error(request, 'Seleciona um trabalhador.')

    return render(request, 'theme/adicionarDesbasteAgulhaWorker.html', {'desbaste_agulha': desbaste_agulha, 'users': users})


def adicionarDesbasteCalibreWorker(request, desbasteCalibre_id):
    desbaste_calibre = get_object_or_404(DesbasteCalibre, id=desbasteCalibre_id)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('worker')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            DesbasteCalibreWorker.objects.create(desbaste_calibre=desbaste_calibre, worker=user)
            messages.success(request, f'{user.get_full_name() or user.username} adicionado ao trabalho de Desbaste Calibre.')
            return redirect('adicionarDesbasteCalibreWorker', desbasteCalibre_id=desbaste_calibre.id)
        else:
            messages.error(request, 'Seleciona um trabalhador.')
    return render(request, 'theme/adicionarDesbasteCalibreWorker.html', {'desbaste_calibre': desbaste_calibre, 'users': users})


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

def adicionarAfinacaoWorker(request, afinacao_id):
    afinacao = get_object_or_404(Afinacao, id=afinacao_id)
    users = User.objects.all()
    if request.method == 'POST':
        user_id = request.POST.get('worker')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            AfinacaoWorker.objects.create(afinacao=afinacao, worker=user)
            messages.success(request, f'{user.get_full_name() or user.username} adicionado ao trabalho de Afinação.')
            return redirect('adicionarAfinacaoWorker', afinacao_id=afinacao.id)
        else:
            messages.error(request, 'Seleciona um trabalhador.')
    return render(request, 'theme/adicionarAfinacaoWorker.html', {'afinacao': afinacao, 'users': users})



def detalhesQrcode(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)

    # Buscar os trabalhos relacionados
    afinacoes = Afinacao.objects.filter(qr_code=qr)
    desbastes_calibre = DesbasteCalibre.objects.filter(qr_code=qr)
    desbastes_agulha = DesbasteAgulha.objects.filter(qr_code=qr)
    polimentos = Polimento.objects.filter(qr_code=qr)

    # Buscar dados adicionais
    diametros = PedidosDiametro.objects.filter(qr_code=qr)
    partidos = NumeroPartidos.objects.filter(qr_code=qr)

    context = {
        'qr': qr,
        'afinacoes': afinacoes,
        'desbastes_calibre': desbastes_calibre,
        'desbastes_agulha': desbastes_agulha,
        'polimentos': polimentos,
        'diametros': diametros,
        'partidos': partidos,
    }

    return render(request, 'theme/detalhesQrcode.html', context)


def addDetails(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)

    if request.method == 'POST':
        # Observações
        qr.observations = request.POST.get('observacoes', '')

        # Diâmetros
        diametro_min = request.POST.get('diametro_min')
        diametro_max = request.POST.get('diametro_max')

        if diametro_min and diametro_max:
            if qr.diameter:
                # Atualiza os valores existentes
                qr.diameter.min = diametro_min
                qr.diameter.max = diametro_max
                qr.diameter.save()
            else:
                # Cria novo e liga ao QRData
                novo_diametro = Diameters.objects.create(
                    min=diametro_min,
                    max=diametro_max
                )
                qr.diameter = novo_diametro

        qr.save()
        messages.success(request, "Informações atualizadas com sucesso!")
        return redirect('listQrcodes')

    afinacoes = qr.afinacao_set.all()
    desbastes_calibre = qr.desbastecalibre_set.all()
    desbastes_agulha = qr.desbasteagulha_set.all()
    polimentos = qr.polimento_set.all()
    diametros = qr.diametro_set.all() if hasattr(qr, 'diametro_set') else []
    partidos = qr.partido_set.all() if hasattr(qr, 'partido_set') else []

    afinacoes_validas = [a for a in afinacoes if a.afinacaoworker_set.exists()]
    desbastes_calibre_validos = [dc for dc in desbastes_calibre if dc.desbastecalibreworker_set.exists()]
    desbastes_agulha_validos = [da for da in desbastes_agulha if da.desbasteagulhaworker_set.exists()]
    polimentos_validos = [p for p in polimentos if p.polimentoworker_set.exists()]

    context = {
        'qr': qr,
        'afinacoes': afinacoes_validas,
        'desbastes_calibre': desbastes_calibre_validos,
        'desbastes_agulha': desbastes_agulha_validos,
        'polimentos': polimentos_validos,
        'diametros': diametros,
        'partidos': partidos,
    }

    return render(request, 'theme/addDetails.html', context)

