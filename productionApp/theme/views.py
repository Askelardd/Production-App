import calendar
import datetime
import json  
import logging
import os
from productionApp.templatetags.extras import *
from collections import Counter
from datetime import date, timedelta
from django.db.models import Q, OuterRef, Exists, Prefetch
from django.urls import reverse
import pandas as pd  
from django.conf import settings
from django.contrib import messages  
from django.contrib.auth import authenticate, login  
from django.contrib.auth import logout as auth_logout
from django.core.mail import EmailMessage
from django.contrib.auth.decorators import login_required  
from django.contrib.auth.models import User  
from django.db.models.functions import TruncMonth, TruncDay
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction  
from django.db.models import Count  
from django.http import HttpResponse, JsonResponse  
from django.shortcuts import get_object_or_404, redirect, render  
from django.utils import timezone  
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt  
from django.views.decorators.http import require_http_methods, require_POST  
from collections import OrderedDict
import openpyxl
from .models import *  
from collections import defaultdict
from django.db.models.functions import TruncDate


def stock_overview(request):
    return redirect('http://192.168.2.112:18000')    


def home(request):
    # Lista com a ordem que queres que apareça no ecrã
    grupos_ordenados = ['Administracao', 'Producao', 'Q-Office', 'Comercial']
    
    # Vamos construir uma lista de dicionários para passar ao HTML
    usuarios_por_grupo = []

    for nome_grupo in grupos_ordenados:
        # Vai buscar os utilizadores que pertencem a este grupo, ordenados por nome
        usuarios = User.objects.filter(groups__name=nome_grupo).order_by('username')
        
        # Se houver utilizadores neste grupo, adicionamos à nossa lista final
        if usuarios.exists():
            usuarios_por_grupo.append({
                'nome_grupo': nome_grupo,
                'usuarios': usuarios
            })

    # Caso tenhas utilizadores sem grupo atribuído e os queiras mostrar (Opcional)
    usuarios_sem_grupo = User.objects.filter(groups__isnull=True).order_by('username')
    if usuarios_sem_grupo.exists():
        usuarios_por_grupo.append({
            'nome_grupo': 'Outros',
            'usuarios': usuarios_sem_grupo
        })

    # Passamos a nova estrutura agrupada para o template
    return render(request, 'theme/home.html', {'usuarios_por_grupo': usuarios_por_grupo})

def erro403(request, exception=None):
    return render(request, '403.html', status=403)


@csrf_exempt
def login_view(request, user_id):
    try:
        user_alvo = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Utilizador não encontrado.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')
        
        # 2. Usar uma variável DIFERENTE para testar a autenticação
        user_autenticado = authenticate(request, username=user_alvo.username, password=password)
        
        if user_autenticado is not None:
            login(request, user_autenticado)
            globalLogs.objects.create(
                user=request.user,
                action=f"{request.user.get_username()} fez login no sistema."
            )
            return redirect('mainMenu')
        else:
            messages.error(request, 'Palavra-passe incorreta.')
            # O código continua para baixo e usa o 'user_alvo' original

    # 3. Enviar o 'user_alvo' original para o template saber desenhar o formulário novamente
    return render(request, 'theme/login.html', {'user': user_alvo})


def qOfficeMenu(request):
    return render(request, 'theme/qOfficeMenu.html')

@group_required('Comercial', 'Administracao')
def financeiroMenu(request):
    return render(request, 'theme/menuFinanceiro.html')

@group_required('Administracao')
def documentosMenu(request):
    return render(request, 'theme/menuDocumentos.html')

def productionMenu(request):
    q = request.GET.get('q', '').strip()
    results = []
    
    if q:
        # Define um Prefetch para obter a última localização (WhereDie) de cada fieira
        latest_location_prefetch = Prefetch(
            'locations',  # O related_name no modelo dieInstance é 'locations'
            queryset=WhereDie.objects.order_by('-updated_at'),
            to_attr='latest_location' # Armazena o resultado em 'latest_location'
        )
        
        results = (
            dieInstance.objects
            .select_related('customer') # QRData (box_nr, toma_order_full, customer)
            # Adiciona o Prefetch à query
            .prefetch_related(latest_location_prefetch) 
            .filter(serial_number__icontains=q) 
            .order_by('serial_number')[:100]
        )
    return render(request, 'theme/productionMenu.html', {'results': results, 'q': q})

@login_required
def fieira_path(request):
    dies = dieInstance.objects.select_related('customer').prefetch_related('locations').all()

    paths = []
    for die in dies:
        locations = die.locations.order_by('-updated_at')
        paths.append({
            'serial_number': die.serial_number,
            'customer': die.customer, # Isto passa o Objeto QRData inteiro
            'cone': die.cone,
            'locations': locations,
        })

    context = {
        'paths': paths,
    }
    return render(request, 'theme/fieira_path.html', context)

@group_required('Comercial', 'Administracao')
@login_required
def comercialMenu(request):
    return render(request, 'theme/comercialMenu.html')

@group_required('Comercial', 'Administracao')
@login_required
def orders(request):
    choices = Order.courier_choices
    plants = Order.plant_choices
    orders_coming_list = OrdersComing.objects.all().order_by('order')  # Para preencher o <select>
    
    if request.method == 'POST':
        plant = request.POST.get('plant') or None
        tracking_number = request.POST.get('tracking_number')
        orders_coming_ids = request.POST.getlist('orders_coming')  # <- agora é uma lista
        courier = request.POST.get('courier') or None
        shipping_date_str = request.POST.get('shipping_date') or ""
        comment = request.POST.get('comment', '')

        # Parse da data
        shipping_date = None
        if shipping_date_str:
            try:
                shipping_date = datetime.datetime.strptime(shipping_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Data de envio inválida.")
                return render(request, 'theme/orders.html', {
                    'courier_choices': choices,
                    'orders_coming': orders_coming_list,
                })

        # Validação básica
        if not tracking_number:
            messages.error(request, "Número de rastreamento é obrigatório.")
            return render(request, 'theme/orders.html', {
                'courier_choices': choices,
                'orders_coming': orders_coming_list,
                'plant_choices': plants,
            })

        # Busca múltiplos OrdersComing
        orders_coming_qs = OrdersComing.objects.filter(id__in=orders_coming_ids)

        # Cria a Order (sem orders_coming ainda)
        order = Order.objects.create(
            plant=plant,
            tracking_number=tracking_number,
            courier=courier,
            shipping_date=shipping_date,
            comment=comment,
        )

        # Adiciona os múltiplos OrdersComing
        order.orders_coming.set(orders_coming_qs)

        # Grava os ficheiros
        for index, f in enumerate(request.FILES.getlist('files')):
            restricted = bool(request.POST.get(f'restricted_{index}'))
            OrderFile.objects.create(order=order, file=f, restricted=restricted)

        # 1. Garante que as variáveis são listas (como já estavas a fazer bem)
        lista_to = settings.EMAIL_TO_EMAIL if isinstance(settings.EMAIL_TO_EMAIL, list) else [settings.EMAIL_TO_EMAIL]
        lista_bcc = settings.DEFAULT_BCC_EMAIL if isinstance(settings.DEFAULT_BCC_EMAIL, list) else [settings.DEFAULT_BCC_EMAIL]

        # 2. Constrói a mensagem avançada
        email = EmailMessage(
            subject=f"Novo pedido criado: {order.tracking_number} de {order.plant}",
            body=(f"Um novo pedido foi criado com o número de rastreamento: {order.tracking_number}\n"
                f"Plant: {order.plant}, shipping date: {order.shipping_date}\n"),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=lista_to,       # Vai para o EMAIL_TO_EMAIL
            bcc=lista_bcc,     # Vai para o EMAIL_DIAMETRO (BCC)
        )

        # 3. Envia!
        email.send()

        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.username} criou o pedido {order.tracking_number}.",
        )

        messages.success(request, "Pedido criado com sucesso!")
        return redirect('listarOrders')

    return render(request, 'theme/orders.html', {
        'courier_choices': choices,
        'plant_choices': plants,
        'orders_coming': orders_coming_list,
    })

@csrf_exempt
@login_required
@group_required('Comercial', 'Administracao', 'Q-Office')
def create_orders_coming_ajax(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            oc = OrdersComing.objects.create(
                order=data.get('order'),
                conoptica =data.get('conoptica', False),
                inspectionMetrology=data.get('inspectionMetrology', False),
                preshipment=data.get('preshipment', False),
                mark=data.get('mark', False),
                urgent=data.get('urgent', False),
                days_2_3=data.get('days_2_3', False),
                days_3_4=data.get('days_3_4', False),
                recondicioning=data.get('recondicioning', False),
                semifinished=data.get('semifinished', False),
                casing=data.get('casing', False),
                pin=data.get('pin', False),
                done=data.get('done', False),
                comment=data.get('comment', ''),
            )
            return JsonResponse({
                'success': True,
                'data': {
                    'id': oc.id,
                    'order': oc.order,
                    'pin': oc.pin,
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método inválido'})

@group_required('Comercial', 'Administracao', 'Q-Office')
def listar_orders(request):
    ordersComing = OrdersComing.objects.all()

    limite_escolhido = request.GET.get('limit', '20')
    search_query = request.GET.get('q', '').strip()
    filtro_tipo = request.GET.get('tipo', 'todos')

    orders = (
        Order.objects
        .prefetch_related('orders_coming', 'files')
        .annotate(has_tasks=Exists(
                OrdersComing.objects
                .filter(orders=OuterRef('pk'))  
                .filter(
                    Q(inspectionMetrology=True) |
                    Q(preshipment=True) |
                    Q(mark=True) |
                    Q(urgent=True)
                )
            ))
    )

    if search_query:
        orders = orders.filter(
            Q(tracking_number__icontains=search_query) |
            Q(plant__icontains=search_query) |
            Q(courier__icontains=search_query) |
            Q(comment__icontains=search_query) |
            Q(orders_coming__order__icontains=search_query) 
        ).distinct()

    if filtro_tipo == 'import':
        orders = orders.exclude(plant__iexact='toma')
    elif filtro_tipo == 'export':
        orders = orders.filter(plant__iexact='toma')

    orders = orders.order_by('-shipping_date', '-id')


    if limite_escolhido == 'todos':
        orders = orders
    else:
        try:
            limite = int(limite_escolhido)
            orders = orders[:limite] 
        except ValueError:
            orders = orders[:20]
            limite_escolhido = '20'


    is_admin = request.user.groups.filter(name__in=["Administracao", "Comercial"]).exists()
    is_qOffice = request.user.groups.filter(name='Q-Office').exists()

    return render(request, 'theme/listarOrders.html', {
        'orders': orders, # Mandas as orders já cortadas
        'limite_escolhido': limite_escolhido, 
        'search_query': search_query,
        'filtro_tipo': filtro_tipo,

        'is_admin': is_admin,
        'ordersComing': ordersComing,
        'is_qOffice': is_qOffice,
    })


@login_required
@csrf_exempt
@group_required('Comercial', 'Administracao')
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    files = order.files.all()
    choices = Order.courier_choices
    plants = Order.plant_choices
    orders_coming_list = OrdersComing.objects.all().order_by('order')

    if request.method == 'POST':
        plants = request.POST.get('plant') or None
        order.tracking_number = request.POST.get('tracking_number')
        courier = request.POST.get('courier') or None
        shipping_date_str = request.POST.get('shipping_date') or ""
        arriving_date_str = request.POST.get('arriving_date') or ""
        comment = request.POST.get('comment', '')
        orders_coming_ids = request.POST.getlist('orders_coming')  # <-- now a list of IDs

        
        arriving_date = None
        if arriving_date_str:
            try:
                arriving_date = datetime.datetime.strptime(arriving_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Data de chegada inválida.")
                return render(request, 'theme/editOrder.html', {
                    'order': order,
                    'files': files,
                    'courier_choices': choices,
                    'plant_choices': plants,
                    'orders_coming': orders_coming_list,
                })
        # Parse shipping date
        shipping_date = None
        if shipping_date_str:
            try:
                shipping_date = datetime.datetime.strptime(shipping_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Data de envio inválida.")
                return render(request, 'theme/editOrder.html', {
                    'order': order,
                    'files': files,
                    'courier_choices': choices,
                    'plant_choices': plants,
                    'orders_coming': orders_coming_list,
                })

        order.courier = courier
        order.plant = plants
        order.shipping_date = shipping_date
        order.arriving_date = arriving_date
        order.comment = comment
        order.save()

        # Atualiza relação ManyToMany
        orders_coming_qs = OrdersComing.objects.filter(id__in=orders_coming_ids)
        order.orders_coming.set(orders_coming_qs)

        # Novos ficheiros
        for index, f in enumerate(request.FILES.getlist('files')):
            restricted = bool(request.POST.get(f'restricted_{index}'))
            OrderFile.objects.create(order=order, file=f, restricted=restricted)
            
        
        for f in files:
            is_restricted = bool(request.POST.get(f'restricted_existing_%s' % f.id))
            if f.restricted != is_restricted:
                f.restricted = is_restricted
                f.save()
                
        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.username} editou o pedido {order.tracking_number}.",
        )

        messages.success(request, "Pedido atualizado com sucesso!")
        return redirect('listarOrders')
    


    return render(request, 'theme/editOrder.html', {
        'order': order,
        'files': files,
        'courier_choices': choices,
        'plant_choices': plants,
        'orders_coming': orders_coming_list,
    })

@require_POST
@login_required
@admin_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()

    globalLogs.objects.create(
        user=request.user,
        action=f"{request.user.username} eliminou o pedido {order.tracking_number}.",
    )
    messages.success(request, "Pedido eliminado com sucesso!")
    return redirect('listarOrders')

@require_POST
@login_required
def delete_order_file(request, file_id):
    f = get_object_or_404(OrderFile, id=file_id)
    order_id = f.order_id
    # Apaga o ficheiro do storage também:
    if f.file:
        f.file.delete(save=False)
    f.delete()

    globalLogs.objects.create(
        user=request.user,
        action=f"{request.user.username} eliminou o ficheiro {f.file.name}.",
    )
    messages.success(request, "Ficheiro eliminado com sucesso!")
    # volta para a listagem ou para a edição da order
    return redirect('listarOrders')  # ou redirect('editOrder', order_id=order_id)


@require_http_methods(["GET", "POST"])
@login_required
def edit_orders_coming(request, oc_id):
    orders_coming = get_object_or_404(OrdersComing, id=oc_id)

    if request.method == 'POST':
        orders_coming.order = request.POST.get('order')
        orders_coming.conoptica = request.POST.get('conoptica') == 'on'
        orders_coming.inspectionMetrology = request.POST.get('inspectionMetrology') == 'on'
        orders_coming.preshipment = request.POST.get('preshipment') == 'on'
        orders_coming.mark = request.POST.get('mark') == 'on'
        orders_coming.urgent = request.POST.get('urgent') == 'on'
        orders_coming.days_2_3 = request.POST.get('days_2_3') == 'on'
        orders_coming.days_3_4 = request.POST.get('days_3_4') == 'on'
        orders_coming.recondicioning = request.POST.get('recondicioning') == 'on'
        orders_coming.semifinished = request.POST.get('semifinished') == 'on'
        orders_coming.pin = request.POST.get('pin') == 'on'
        orders_coming.casing = request.POST.get('casing') == 'on'
        orders_coming.done = request.POST.get('done') == 'on' 
        done = request.POST.get('done') == 'on'
        data_done_str = request.POST.get('data_done', '')

        orders_coming.done = done

        if done:
            if data_done_str:
                # Se o utilizador preencheu ou o JS colocou a data de hoje
                orders_coming.data_done = data_done_str
            else:
                # Fallback caso a data venha vazia por algum motivo
                orders_coming.data_done = timezone.now().date()
        else:
            # Se desmarcar o "Concluído", limpamos a data
            orders_coming.data_done = None

        orders_coming.comment = request.POST.get('comment', '')
        orders_coming.done = done
        orders_coming.save()

        messages.success(request, "OrdersComing atualizado com sucesso.")
        return redirect('listarOrders')

    return render(request, 'theme/editOrdersComing.html', {
        'oc': orders_coming
    })

def exportOrderExcel(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    orders_coming = order.orders_coming.all()
    order_files = order.files.all()

    # Criar dados
    data = []
    for oc in orders_coming:
        data.append({
            'Plant': order.plant or 'N/A',
            'Shipping Number': order.tracking_number or 'N/A',
            'Order': oc.order,
            'Conoptica': 'Sim' if oc.conoptica else '-',
            'Inspection Metrology': 'Sim' if oc.inspectionMetrology else '-',
            'Preshipment': 'Sim' if oc.preshipment else '-',
            'Mark': 'Sim' if oc.mark else '-',
            'Urgent': 'Sim' if oc.urgent else '-',
            'Days 2-3': 'Sim' if oc.days_2_3 else '-',
            'Days 3-4': 'Sim' if oc.days_3_4 else '-',
            'Recondicioning': 'Sim' if oc.recondicioning else '-',
            'Semifinished': 'Sim' if oc.semifinished else '-',
            'Pin': 'Sim' if oc.pin else '-',
            'Casing': 'Sim' if oc.casing else '-',
            'Done': 'Sim' if oc.done else '-',
            'Comment': oc.comment,
        })

    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=Order_{order.tracking_number}_Details.xlsx'

    # Gerar o Excel em memória
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dados', index=False)

    # Se chegou aqui, a exportação foi gerada — marca como exportado
    if not order.exportado:
        order.exportado = True
        order.save(update_fields=['exportado'])

    # Log (mantém o teu)
    globalLogs.objects.create(
        user=request.user,
        action=f"{request.user.username} criou um exel da ordem {order.tracking_number}.",
    )

    return response

@login_required
@group_required('Administracao', 'Comercial', 'Q-Office')
def administrationMenu(request):
    return render(request, 'theme/administrationMenu.html')


@login_required
def user_logout(request):
    uid = request.user.id                            # <-- guarda antes do logout
    username = request.user.get_username()

    globalLogs.objects.create(
        user=request.user,
        action=f"{username} fez logout do sistema."
    )

    auth_logout(request)
    messages.success(request, "Saiu da sua conta com sucesso!")
    return redirect('login', 0)            # <-- passa o argumento exigido


@group_required('Comercial', 'Administracao')
@require_http_methods(["GET", "POST"])
@login_required
def deliveryIdentification(request, toma_order_full):
    
    qr = get_object_or_404(QRData, toma_order_full=toma_order_full)

    # obter ou criar o DeliveryInfo para este QR
    info, _created = DeliveryInfo.objects.get_or_create(identificator=qr)

    # listas para selects
    types = DeliveryType.objects.order_by('name')
    entities = DeliveryEntity.objects.order_by('name')

    if request.method == "POST":
        dtype_name = (request.POST.get('deliveryType') or '').strip()
        dent_name  = (request.POST.get('deliveryEntity') or '').strip()
        ddate      = (request.POST.get('deliveryDate') or '').strip()
        costumer   = (request.POST.get('costumer') or '').strip()

        # aplicar no objeto
        info.deliveryType = DeliveryType.objects.filter(name=dtype_name).first() if dtype_name else None
        info.deliveryEntity = DeliveryEntity.objects.filter(name=dent_name).first() if dent_name else None
        info.costumer = costumer or info.costumer
        info.deliveryDate = ddate or None  # DateInput manda 'YYYY-MM-DD' (o modelo converte)

        # Regras finais continuam garantidas no modelo (clean/save)
        try:
            with transaction.atomic():
                info.save()
            globalLogs.objects.create(
                user=request.user,
                action=f"{request.user.username} atualizou a informação de entrega do pedido {info.id}.",
            )
            messages.success(request, "Informação de entrega atualizada com sucesso.")
            return redirect('deliveryCalendar')
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao guardar: {e}")


    return render(request, 'theme/deliveryIdentification.html', {
        'toma_order_full': toma_order_full,
        'qr': qr,
        'info': info,
        'types': types,
        'entities': entities,
    })


def _parse_checked(request):
    """Lê o boolean 'checked' do corpo JSON ou do POST tradicional."""
    try:
        data = json.loads(request.body or '{}')
        return bool(data.get('checked'))
    except Exception:
        return bool(request.POST.get('checked'))

@require_POST
def toggle_partido_feito_ajax(request, pk):
    obj = get_object_or_404(NumeroPartidos, pk=pk)
    checked = _parse_checked(request)
    obj.checkbox = checked
    obj.save(update_fields=['checkbox'])
    return JsonResponse({
        "ok": True,
        "id": obj.id,
        "checked": obj.checkbox,
        "label": "Sim" if obj.checkbox else "Não"
    })

@require_POST
def toggle_pedido_diametro_feito_ajax(request, pk):
    obj = get_object_or_404(PedidosDiametro, pk=pk)
    checked = _parse_checked(request)
    obj.checkbox = checked
    obj.save(update_fields=['checkbox'])
    return JsonResponse({
        "ok": True,
        "id": obj.id,
        "checked": obj.checkbox,
        "label": "Sim" if obj.checkbox else "Não"
    })



@csrf_exempt
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
def mainMenu(request):
    
    user = request.user
    
    # Verifica se o utilizador logado está a tentar ver outro perfil
    if request.user.id != user.id:
        messages.error(request, 'Acesso negado.')
        return redirect('home')

    return render(request, 'theme/mainMenu.html', {'user': user})



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

@group_required('Comercial', 'Administracao', 'Q-Office')
def listQrcodes(request):
    # 1. Buscar todos os dados ordenados
    all_qrcodes = QRData.objects.all().order_by('-created_at')

    # 2. Agrupar os dados
    # A estrutura será: chave (nr, ano) -> { info_cliente, total_qty, lista_de_caixas }
    grouped_data = {}

    for qr in all_qrcodes:
        # Criamos uma chave única para o grupo
        key = (qr.toma_order_nr, qr.toma_order_year)

        if key not in grouped_data:
            grouped_data[key] = {
                'toma_order_nr': qr.toma_order_nr,
                'toma_order_year': qr.toma_order_year,
                'customer': qr.customer,
                'customer_order_nr': qr.customer_order_nr,
                'total_qt': 0,
                'boxes': [] # Aqui guardamos os objetos originais
            }
        
        # Adicionamos a quantidade ao total do grupo
        grouped_data[key]['total_qt'] += qr.qt
        # Adicionamos a caixa à lista deste grupo
        grouped_data[key]['boxes'].append(qr)

    # Convertemos o dicionário numa lista para o template ler facilmente
    # Ordenamos pela data de criação da primeira caixa (opcional)
    final_list = list(grouped_data.values())

    return render(request, 'theme/listQrcodes.html', {
        'grouped_qrcodes': final_list, # Mudámos o nome da variável para não confundir
        'current_time': timezone.now()
    })

@login_required
def edit_qr_inline(request, qr_id):
    if request.method == "POST":
        qr = get_object_or_404(QRData, id=qr_id)

        # Atualiza os campos
        qr.customer = request.POST.get('customer')
        qr.customer_order_nr = request.POST.get('customer_order_nr')
        qr.toma_order_nr = request.POST.get('toma_order_nr')
        qr.toma_order_year = request.POST.get('toma_order_year')
        qr.box_nr = request.POST.get('box_nr')
        qr.qt = request.POST.get('qt')
        
        # Datas precisam de atenção se vierem vazias
        p_start = request.POST.get('production_start')
        envio = request.POST.get('envio')
        qr.production_start = p_start if p_start else None
        qr.envio = envio if envio else None


        novo_order = f"{qr.toma_order_nr}-{qr.toma_order_year}-{qr.box_nr}"

        if QRData.objects.filter(toma_order_full=novo_order).exclude(id=qr.id).exists():
            messages.error(request, "O pedido já tem uma caixa com este numero, se achar que é um erro, contacte o Andre.")
            return redirect(request.META.get('HTTP_REFERER', 'listarDies'))
        
        qr.toma_order_full = f"{qr.toma_order_nr}-{qr.toma_order_year}-{qr.box_nr}"
    
        qr.save() # O teu método save() já gera o toma_order_full automaticamente!
        
        messages.success(request, f"Registo de {qr.customer} atualizado.")
        
    return redirect(request.META.get('HTTP_REFERER', 'listarDies'))


@login_required
def clonar_linha(request, qr_id):
    original = get_object_or_404(QRData, id=qr_id)

    if request.method != 'POST':
        return redirect('listQrcodes')

    diametro = (request.POST.get('diametro') or '').strip()
    if not diametro:
        messages.error(request, "O diâmetro é obrigatório.")
        return redirect('listQrcodes')

    try:
        # novo número de caixa dentro do mesmo pedido
        last_box = (
            QRData.objects
            .filter(
                toma_order_nr=original.toma_order_nr,
                toma_order_year=original.toma_order_year
            )
            .order_by('-box_nr')
            .first()
        )

        try:
            next_box_nr = int(last_box.box_nr) + 1 if last_box and str(last_box.box_nr).isdigit() else 1
        except Exception:
            next_box_nr = 1

        nova_caixa = QRData.objects.create(
            customer=original.customer,
            customer_order_nr=original.customer_order_nr,
            toma_order_nr=original.toma_order_nr,
            toma_order_year=original.toma_order_year,
            box_nr=next_box_nr,
            qt=original.qt,
            diameters=diametro,
            production_start=original.production_start,
            envio=original.envio,
            observations=original.observations,
            created_by=request.user,
        )

        messages.success(request, f"Caixa clonada com sucesso: {nova_caixa.toma_order_full}.")
        return redirect('listQrcodes')

    except Exception as e:
        messages.error(request, f"Erro ao clonar a caixa: {e}")
        return redirect('listQrcodes')
    

@login_required
def listarInfo(request):
    deliveries = DeliveryInfo.objects.all()
    return render(request, 'theme/listarInfo.html', {'deliveries': deliveries})

@group_required('Comercial', 'Administracao')
@login_required
def deletar_delivery(request, id):
    delivery = get_object_or_404(DeliveryInfo, id=id)

    if request.method == 'POST':
        delivery.delete()
        messages.success(request, 'Entrega deletada com sucesso!')
        return redirect('listarInfo')

    messages.error(request, 'Requisição inválida.')
    return redirect('listarInfo')


@login_required
def listarInfo(request):
    deliveries = DeliveryInfo.objects.all()
    return render(request, 'theme/listarInfo.html', {'deliveries': deliveries})

@login_required
def deletar_delivery(request, id):
    delivery = get_object_or_404(DeliveryInfo, id=id)

    if request.method == 'POST':
        delivery.delete()
        messages.success(request, 'Entrega deletada com sucesso!')
        return redirect('listarInfo')

    messages.error(request, 'Requisição inválida.')
    return redirect('listarInfo')

# Configure logging
logger = logging.getLogger(__name__)

''''
@require_http_methods(["GET", "POST"])
@csrf_exempt
@login_required
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
'''

@csrf_exempt
@login_required
def partidosMenu(request, toma_order_full):
    qr_code = get_object_or_404(QRData, toma_order_full=toma_order_full)
    dies_existentes = dieInstance.objects.filter(customer=qr_code).order_by('-created_at')
    user = request.user
    if request.method == 'POST':
        numero = request.POST.get('numeroPartidos')
        serie_dies_list = request.POST.getlist('serieDies')  # <-- recebe checkboxes
        serie_dies_partidos = ', '.join(serie_dies_list)     # <-- transforma em string
        observations = request.POST.get('observations', '')

        # Update partida flag for selected dies
        for die in dies_existentes.filter(serial_number__in=serie_dies_list):
            die.partida = True
            die.save()
            

        try:
            partido = int(numero)
            if partido <= 0:
                messages.error(request, 'O número do partido deve ser um número positivo.')
            else:
                NumeroPartidos.objects.create(
                    qr_code=qr_code,
                    partido=partido,
                    serie_dies_partidos=serie_dies_partidos,
                    observations=observations,
                    criado_por=user
                )
                messages.success(request, f'Partido {partido} adicionado com sucesso!')
                globalLogs.objects.create(
                    user=request.user,
                    action=f"{request.user.username} adicionou o partido {partido} ao QR Code {qr_code.toma_order_full}.",
                )
        except ValueError:
            messages.error(request, 'Número do partido inválido. Por favor, insira um número válido.')
        except Exception as e:
            messages.error(request, f'Erro ao adicionar partido: {str(e)}')

    

    return render(request, 'theme/partidosMenu.html', {
        'qr_code': qr_code,
        'dies_existentes': dies_existentes
    })

    


@csrf_exempt
@login_required
def showDetails(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)
    pedidos = PedidosDiametro.objects.filter(qr_code=qr)
    
    # Preparar obs_limpa para cada pedido
    for pedido in pedidos:
        if pedido.observations:
            pedido.obs_limpa = pedido.observations.replace('_', ' ').title()
        else:
            pedido.obs_limpa = '-'
    
    partidos = NumeroPartidos.objects.filter(qr_code=qr)
    user = request.user.username
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    polimentos = Polimentos.objects.filter(
        created_at__date__range=(week_start, week_end)
    ).order_by('-created_at')

    dies = qr.die_instances.all()
    polimentos_dies_ids = list(polimentos)

    # ---------------------------------------------------------
    # NOVO CÁLCULO DE ESTATÍSTICAS DOS TRABALHADORES
    # ---------------------------------------------------------
    die_workers = {}
    
    if DieWorkWorker.objects.filter(work__die__in=dies).values('worker_id').distinct().count() == 0:
        messages.info(request, "Nenhum trabalho foi realizado nestas caixa.")
        return render(request, 'theme/showDetails.html', {
            'qr': qr,
            'dies': dies,
            'workers_stats': [],
            'pedidos': pedidos,
            'partidos': partidos,
            'polimentos_dies_ids': polimentos_dies_ids,
            'pessoal': None
        })

    # 1. Procurar TODOS os trabalhos feitos nas dies deste QR Code
    # Anotamos a contagem para encontrar repetições do mesmo tipo/subtipo pela mesma pessoa na mesma die
    trabalhos = DieWorkWorker.objects.filter(work__die__in=dies).values(
        'worker_id', 
        'worker__first_name', 
        'worker__last_name', 
        'worker__username',
        'work__die__serial_number', # Precisamos saber a qual die se refere
        'work__die_id',
        'work__work_type',
        'work__subtype'
    ).annotate(total_vezes=Count('id')) # Conta quantas vezes fez este trabalho específico        

    # 2. Organizar a informação
    for trab in trabalhos:
        worker_id = trab['worker_id']
        username = trab['worker__username']
        
        if worker_id not in die_workers:
            die_workers[worker_id] = {
                'name': f"{trab['worker__first_name']} {trab['worker__last_name']}",
                'username': username,
                'dies_worked': set(),
                'repeticoes': [], # Lista para guardar os avisos de trabalhos repetidos
                'total_trabalhos': 0,
                'trabalhos_realizados': []
            }
            
        # Adiciona a die ao set (como é um set, dies repetidas não contam duas vezes para o total)
        die_workers[worker_id]['dies_worked'].add(trab['work__die_id'])
        die_workers[worker_id]['total_trabalhos'] += trab['total_vezes']

        
        # Se fez o mesmo trabalho mais de 1 vez na MESMA die, guarda o aviso!
        if trab['total_vezes'] > 1:
            tipo = trab['work__work_type']
            subtipo = trab['work__subtype'] if trab['work__subtype'] else 'Geral'
            serie = trab['work__die__serial_number']
            vezes = trab['total_vezes']
            
            mensagem = f"Fez {vezes - 1} correção de {tipo} ({subtipo}) na fieira {serie}"
            die_workers[worker_id]['repeticoes'].append(mensagem)
            
            trabalhos_relizados = f"{tipo} ({subtipo}) na fieira {serie} - {vezes} vezes"

        if trab['total_vezes'] >= 1:
            tipo = trab['work__work_type']
            subtipo = trab['work__subtype'] if trab['work__subtype'] else 'Geral'
            serie = trab['work__die__serial_number']
            vezes = trab['total_vezes']
            
            for i in range(vezes):
                trabalhos_relizados = f"{tipo} ({subtipo}) na fieira {serie}"
                die_workers[worker_id]['trabalhos_realizados'].append(trabalhos_relizados)

    # 3. Preparar a lista final para o template
    workers_stats_list = []
    trabalhos_Realizado_limpo = []
    pessoal = None

    for trabalhos_realizados in die_workers[worker_id]['trabalhos_realizados']:
        trabalhos_Realizado_limpo.append(trabalhos_realizados.replace('[', '').replace(']', '').replace("'", "").replace('_', ' ').title())
    
    for worker in die_workers.values():
        total_dies = len(worker['dies_worked'])
        if total_dies > 0:
            workers_stats_list.append({
                'name': worker['name'],
                'username': worker['username'],
                'total_dies': total_dies,
                'repeticoes': worker['repeticoes'], # Passamos a lista de repetições
                'total_trabalhos': worker['total_trabalhos'], # Lista de Trabalhos absolutos
                'trabalhos_realizados': trabalhos_Realizado_limpo # Lista de trabalhos realizados (com repetições)
            })

        # Verifica o utilizador atual (logado)
        if worker['username'] == user:
            pessoal = total_dies

    # Ordena por total_dies decrescente
    workers_stats_list = sorted(workers_stats_list, key=lambda x: x['total_dies'], reverse=True)



    return render(request, 'theme/showDetails.html', {
        'qr': qr,
        'dies': dies,
        'workers_stats': workers_stats_list,
        'pedidos': pedidos,
        'partidos': partidos,
        'polimentos_dies_ids': polimentos_dies_ids,
        'pessoal': pessoal
        
    })

@login_required
def adicionar_dies(request, qr_id):
    qr_code = get_object_or_404(QRData, id=qr_id)
    dies = Die.objects.all()
    jobs = Jobs.objects.all()


    raw_value = qr_code.diameters.strip() if qr_code.diameters else ""
    diameters_list = []
    # Formato "2 x 0,1243"
    matches = re.findall(r"(\d+)\s*x\s*([\d,\.]+)", raw_value)
    if matches:
        for qty, value in matches:
            qty = int(qty)
            value = value.replace(",", ".")
            diameters_list.extend([value] * qty)
    else:
        value = raw_value.replace(",", ".")
        diameters_list = [value] * qr_code.qt

    existing_dies = list(dieInstance.objects.filter(customer=qr_code).order_by('id'))

    if request.method == 'POST':
        total = int(request.POST.get('total', 0))

        # ====== VALIDAÇÃO DE NÚMEROS DE SÉRIE DUPLICADOS ======
        errors = []
        posted_serials = []
        for i in range(1, total + 1):
            s = (request.POST.get(f'serial_{i}') or '').strip()
            posted_serials.append(s)

        dup_in_form = [s for s, cnt in Counter([s for s in posted_serials if s]).items() if cnt > 1]
        if dup_in_form:
            errors.append(f"Números de série repetidos no formulário: {', '.join(dup_in_form)}.")

        for i in range(1, total + 1):
            s = (request.POST.get(f'serial_{i}') or '').strip()
            if not s:
                continue
            if i <= len(existing_dies):
                current_obj = existing_dies[i - 1]
                if s != (current_obj.serial_number or '') and dieInstance.objects.filter(serial_number=s).exists():
                    errors.append(f"O número de série '{s}' já existe.")
            else:
                if dieInstance.objects.filter(serial_number=s).exists():
                    errors.append(f"O número de série '{s}' já existe.")

        if errors:
            for e in errors:
                messages.error(request, e)

            # Reconstrói prefill a partir do POST (inclui bearing_red)
            prefilled_data = []
            for i in range(1, total + 1):
                prefilled_data.append({
                    'serial': request.POST.get(f'serial_{i}', ''),
                    'diameter': request.POST.get(f'diameter_{i}', ''),
                    'diam_requerido': request.POST.get(f'diam_requerido_{i}', ''),
                    'die': request.POST.get(f'die_{i}', ''),
                    'job': request.POST.get(f'job_{i}', ''),
                    'tol_max': request.POST.get(f'tol_max_{i}', ''),
                    'tol_min': request.POST.get(f'tol_min_{i}', ''),
                    'observations': request.POST.get(f'observations_{i}', ''),
                    'cone': request.POST.get(f'cone_{i}', ''),
                    'bearing': request.POST.get(f'bearing_{i}', ''),
                    'bearing_red': (request.POST.get(f'bearing_red_{i}') == 'on'),
                })

            return render(request, 'theme/adicionarDies.html', {
                'qr_code': qr_code,
                'dies': dies,
                'jobs': jobs,
                'prefilled_data': prefilled_data,
            })
        # ====== FIM VALIDAÇÃO ======

        # ====== GRAVAÇÃO ======
        try:
            with transaction.atomic():
                for i in range(1, total + 1):
                    serial = request.POST.get(f'serial_{i}')
                    diameter_value = request.POST.get(f'diameter_{i}')
                    diam_requerido = request.POST.get(f'diam_requerido_{i}')
                    die_id = request.POST.get(f'die_{i}')
                    job_id = request.POST.get(f'job_{i}')
                    tol_max = request.POST.get(f'tol_max_{i}')
                    tol_min = request.POST.get(f'tol_min_{i}')
                    observations = request.POST.get(f'observations_{i}')
                    cone = request.POST.get(f'cone_{i}')
                    bearing = request.POST.get(f'bearing_{i}')
                    bearing_red = (request.POST.get(f'bearing_red_{i}') == 'on')

                    if i <= len(existing_dies):
                        # Atualizar existente
                        die_obj = existing_dies[i - 1]
                        die_obj.serial_number = serial
                        die_obj.diameter_text = diameter_value
                        die_obj.diam_requerido = diam_requerido or None
                        die_obj.die_id = die_id if die_id else None
                        die_obj.job_id = job_id if job_id else None
                        die_obj.observations = observations
                        die_obj.cone = cone
                        die_obj.bearing = bearing
                        die_obj.bearing_is_red = bearing_red

                        if tol_max and tol_min:
                            if die_obj.tolerance:
                                die_obj.tolerance.max = tol_max
                                die_obj.tolerance.min = tol_min
                                die_obj.tolerance.save()
                            else:
                                tolerance_obj = Tolerance.objects.create(min=tol_min, max=tol_max)
                                die_obj.tolerance = tolerance_obj

                        die_obj.save()
                    else:
                        # Criar novo
                        tolerance = None
                        if tol_max and tol_min:
                            tolerance = Tolerance.objects.create(min=tol_min, max=tol_max)

                        dieInstance.objects.create(
                            customer=qr_code,
                            serial_number=serial,
                            diameter_text=diameter_value,
                            diam_requerido=diam_requerido or None,
                            die_id=die_id if die_id else None,
                            job_id=job_id if job_id else None,
                            tolerance=tolerance,
                            observations=observations,
                            cone=cone,
                            bearing=bearing,
                            bearing_is_red=bearing_red,  # <-- aqui é o booleano
                        )

                globalLogs.objects.create(
                    user=request.user,
                    action=f"{request.user.username} adicionou/atualizou dies para o QR Code {qr_code.toma_order_nr}.",
                )

            messages.success(request, f"Dies atualizados para {qr_code.customer} com sucesso!")
            return redirect('listQrcodes')

        except IntegrityError:
            messages.error(request, "Falha ao gravar: número de série duplicado.")
            return redirect(request.path)
        # ====== FIM GRAVAÇÃO ======

    # GET → Preenche formulário
    prefilled_data = []
    for i in range(qr_code.qt):
        if i < len(existing_dies):
            die = existing_dies[i]
            prefilled_data.append({
                'serial': die.serial_number,
                'diameter': die.diameter_text,
                'diam_requerido': die.diam_requerido,
                'die': die.die_id,
                'job': die.job_id,
                'tol_max': getattr(die.tolerance, 'max', ''),
                'tol_min': getattr(die.tolerance, 'min', ''),
                'observations': die.observations,
                'cone': die.cone,
                'bearing': die.bearing,
                'bearing_red': getattr(die, 'bearing_is_red', False),  # <-- reflete BD
            })
        else:
            prefilled_data.append({
                'serial': '',
                'diameter': '',
                'diam_requerido': diameters_list[i] if i < len(diameters_list) else '',
                'die': '',
                'job': '',
                'tol_max': '',
                'tol_min': '',
                'observations': '',
                'cone': '',
                'bearing': '',
                'bearing_red': False,
            })

    return render(request, 'theme/adicionarDies.html', {
        'qr_code': qr_code,
        'dies': dies,
        'jobs': jobs,
        'prefilled_data': prefilled_data,
    })

@login_required
def listar_qrcodes_geral(request):

    estado = request.GET.get('estado', 'todos') # Pode ser 'todos', 'abertos' ou 'fechados'

    all_qrcodes = QRData.objects.prefetch_related('die_instances', 'where_boxes').all().order_by('-created_at')

    pedidos_fechados = []
    if estado in ['abertos', 'fechados']:
        pedidos_unicos = QRData.objects.values('toma_order_nr', 'toma_order_year').distinct()
        for pedido in pedidos_unicos:
            nr = pedido['toma_order_nr']
            ano = pedido['toma_order_year']
            
            tem_caixas_abertas = QRData.objects.filter(
                toma_order_nr=nr, 
                toma_order_year=ano
            ).exclude(where_boxes__where='FECHADO').exists()

            if not tem_caixas_abertas:
                pedidos_fechados.append((nr, ano))

    # 2. Agrupar os dados
    grouped_data = {}
    for qr in all_qrcodes:
        key = (qr.toma_order_nr, qr.toma_order_year)

        # 3. A MAGIA DO FILTRO: Saltar as iterações que não interessam consoante o estado
        if estado == 'fechados' and key not in pedidos_fechados:
            continue # Salta para o próximo qr se quisermos os fechados e este não for
            
        if estado == 'abertos' and key in pedidos_fechados:
            continue # Salta para o próximo qr se quisermos os abertos e este estiver fechado


        if key not in grouped_data:
            grouped_data[key] = {
                'toma_order_nr': qr.toma_order_nr,
                'toma_order_year': qr.toma_order_year,
                'customer': qr.customer,
                'customer_order_nr': qr.customer_order_nr,
                'total_qt': 0,
                'boxes': []
            }
        
        grouped_data[key]['total_qt'] += qr.qt
        grouped_data[key]['boxes'].append(qr)

    final_list = list(grouped_data.values())

    tipo_choices = Polimentos._meta.get_field('tipo').choices

    if request.method == "POST":
        numero_fieiras = request.POST.get('numero_fieiras')
        tipo = request.POST.get('tipo')
        cliente = request.POST.get('cliente')
        user = request.user
        created_at = timezone.now()
        observations = request.POST.get('observations', '')

        try:
            Polimentos.objects.create(
                numero_fieiras=numero_fieiras,
                tipo=tipo,
                cliente=cliente,
                created_at=created_at,
                user=user,
                observations=observations
            )
            messages.success(request, "Polimento criado com sucesso!")
            return redirect('listarDies')
        except Exception as e:
            messages.error(request, f"Erro ao criar polimento: {e}")
            return redirect('listarDies')

    # Passamos o 'estado_atual' para o HTML para podermos pintar o botão ativo!
    context = {
        'grouped_qrcodes': final_list,
        'estado_atual': estado,
        'tipo_choices': tipo_choices,
    }
    
    # Mantemos apenas 1 ficheiro HTML! Podes apagar os outros 2.
    return render(request, 'theme/listarDies.html', context)

@login_required
def create_caixa(request):
    user = request.user
    
    # 1. Verificação de permissões
    if not user.groups.filter(name__in=['Q-Office', 'Administracao']).exists():
        messages.error(request, "Não tens permissão para criar caixas.")
        return redirect('listarDies')
    
    if request.method == 'POST':
        # Lista de campos para extrair do POST de forma limpa
        data = request.POST
        
        # 2. Validação de campos obrigatórios
        required_fields = ['customer', 'toma_order_nr', 'toma_order_year', 'box_nr', 'qt', 'diameters']
        for field in required_fields:
            if not data.get(field):
                messages.error(request, "Todos os campos obrigatórios devem ser preenchidos.")
                return redirect('listarDies')

        try:
            box_nr = str(data.get('box_nr'))
            qt = int(data.get('qt'))
            
            # 3. Tratamento de datas (evita erro se vierem vazias)
            p_start = data.get('production_start') if data.get('production_start') else None
            envio = data.get('envio') if data.get('envio') else None
            
            # 4. Lógica de Negócio
            toma_order_full = f"{data.get('toma_order_year')}-{data.get('toma_order_nr')}-{data.get('box_nr')}"

            if QRData.objects.filter(toma_order_full=toma_order_full, box_nr=box_nr).exists():
                messages.error(request, f"Já existe a caixa {box_nr} para o pedido {toma_order_full}.")
                return redirect('listarDies')

            # 5. Criação do Objeto (Corrigido o nome do campo)
            QRData.objects.create(
                customer=data.get('customer'),
                customer_order_nr=data.get('customer_order_nr'),
                toma_order_nr=data.get('toma_order_nr'),
                toma_order_year=data.get('toma_order_year'),
                toma_order_full=toma_order_full, # O save() do model também faz isto, mas aqui é seguro
                box_nr=box_nr,
                qt=qt,
                diameters=data.get('diameters'),
                production_start=p_start,
                envio=envio,
                created_by=user,  
                observations=data.get('observations', ''),
            )


            # 6. Log de Atividade
            globalLogs.objects.create(
                user=user,
                action=f"Criou a caixa {box_nr} para o pedido {toma_order_full}.",
            )

            messages.success(request, "Caixa criada com sucesso!")
            
        except ValueError:
            messages.error(request, "Os campos 'Caixa' e 'Quantidade' devem ser números.")
        except Exception as e:
            messages.error(request, f"Erro inesperado: {str(e)}")

    return redirect('listQrcodes')

@login_required
def die_details(request, die_id):
    die = get_object_or_404(dieInstance, id=die_id)
    works = die.works.prefetch_related('workers__worker')

    if request.method == "POST":
        action = request.POST.get("action")

        # --- AÇÃO 1: ATUALIZAR TRABALHADOR ESPECÍFICO ---
        if action == "update_worker_diams":
            worker_rel_id = request.POST.get('worker_rel_id')
            rel = get_object_or_404(DieWorkWorker, id=worker_rel_id)
            try:
                rel.diam_min = Decimal(request.POST.get('diam_min') or 0)
                rel.diam_max = Decimal(request.POST.get('diam_max') or 0)
                rel.save()
                messages.success(request, "Medidas do trabalhador atualizadas.")
            except (InvalidOperation, TypeError):
                messages.error(request, "Valores inválidos para o trabalhador.")

        # --- AÇÃO 2: ATUALIZAR DIÂMETROS GERAIS E OBSERVAÇÕES ---
        elif action == "update_diametros":
            d_min = request.POST.get('diametro_min')
            d_max = request.POST.get('diametro_max')
            obs = request.POST.get('observations_prod', '').strip()

            try:
                # Converter para Decimal
                val_min = Decimal(d_min) if d_min else Decimal('0.0000')
                val_max = Decimal(d_max) if d_max else Decimal('0.0000')

                if val_min > val_max:
                    messages.error(request, "O mínimo geral não pode ser maior que o máximo.")
                else:
                    # Atualiza ou cria a instância de Diameters
                    if die.diam_max_min:
                        die.diam_max_min.min = val_min
                        die.diam_max_min.max = val_max
                        die.diam_max_min.save()
                    else:
                        from .models import Diameters # Ajusta o import se necessário
                        new_diam = Diameters.objects.create(min=val_min, max=val_max)
                        die.diam_max_min = new_diam
                    
                    die.observations_prod = obs
                    die.save()
                    
                    messages.success(request, "Dados gerais do Die atualizados!")
                    
                    globalLogs.objects.create(
                        user=request.user,
                        action=f"Atualizou diâmetros gerais do Die {die.serial_number}."
                    )
            except (InvalidOperation, TypeError):
                messages.error(request, "Erro ao processar os valores numéricos.")

        # Importante: Redirecionar após qualquer POST para evitar re-submissão
        return redirect('die_details', die_id=die.id)

    return render(request, 'theme/die_details.html', {'die': die, 'works': works})
    

@login_required
def create_die_work(request, die_id):
    die = get_object_or_404(dieInstance, id=die_id)

    if request.method == 'POST':
        tipo_trabalho = request.POST.get('tipo_trabalho')
        subtipo = request.POST.get('subtipo')
        add_another = request.POST.get('add_another') # Capturamos a variável aqui

        # Validações
        if not tipo_trabalho:
            messages.error(request, "Escolha um tipo de trabalho.")
            return redirect(request.path)
        if not subtipo:
            messages.error(request, "Escolha um subtipo.")
            return redirect(request.path)

        # Criação do trabalho
        DieWork.objects.create(
            die=die,
            work_type=tipo_trabalho,
            subtype=subtipo
        )

        messages.success(request, f"Trabalho '{tipo_trabalho}' adicionado com sucesso ao Die {die.serial_number}.")
        
        # Adiciona log na tabela globalLogs
        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.username} criou um trabalho '{tipo_trabalho}' para o Die {die.serial_number}.",
        )

        # Verifica se o utilizador quer adicionar outro trabalho
        # Alterado de "in request.POST" para verificar o valor exato
        if add_another == '1':
            return redirect('create_die_work', die_id=die.id)
        else:
            # Se for vazio (clicou em "Não"), redireciona para os detalhes
            return redirect('die_details', die_id=die.id)

    return render(request, 'theme/create_die_work.html', {'die': die})

@login_required
def add_multiple_works_workers(request, qr_id):
    work = get_object_or_404(QRData, id=qr_id)
    dies = work.die_instances.all()
    users = User.objects.filter(groups__name='Producao').distinct().order_by('username')

    pedido = work.toma_order_full or f"{work.toma_order_year}-{work.toma_order_nr}"

    if request.method == 'POST':
        die_ids = request.POST.getlist('serieDies')  # ← Pega vários IDs
        work_type = request.POST.get('tipo_trabalho')
        subtype = request.POST.get('subtipo')
        worker_ids = request.POST.getlist('workers')  # ← Pega vários IDs de trabalhadores
        add_another = request.POST.get('add_another')

        diam_min = 0.0000
        diam_max = 0.0000

        if not die_ids or not work_type or not subtype or not worker_ids:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect(request.path)

        selected_workers = list(users.filter(id__in=worker_ids))
        if len(selected_workers) != len(set(worker_ids)):
            messages.error(request, "Só é permitido selecionar trabalhadores do grupo Producao.")
            return redirect(request.path)

        for die_id in die_ids:
            die = get_object_or_404(dieInstance, id=die_id)

            # Cria o trabalho
            new_work = DieWork.objects.create(
                die=die, work_type=work_type, subtype=subtype
            )

            # Associa os trabalhadores ao trabalho
            for user in selected_workers:
                DieWorkWorker.objects.create(work=new_work, worker=user,diam_min=diam_min, diam_max=diam_max)

                # Log individual para cada trabalhador
                globalLogs.objects.create(
                    user=request.user,
                    action=f"{request.user.username} criou um trabalho '{work_type}' para o Die {die.serial_number} com o trabalhador {user.username}.",
                )

        messages.success(request, f"{len(die_ids)} trabalho(s) adicionados com sucesso para {len(worker_ids)} trabalhador(es).")

        # Se o campo hidden add_another estiver presente → volta pro mesmo formulário
        if add_another:
            return redirect('add_multiple_works_workers', qr_id=qr_id)

        # Caso contrário, redireciona para os detalhes do último die
        return redirect('die_details', die_id=die_ids[-1])

    return render(
        request,
        'theme/add_multiple_works_workers.html',
        {'qr_id': qr_id, 'dies': dies, 'users': users, 'pedido': pedido},
    )

@login_required
def add_worker_to_die_work(request, work_id):
    work = get_object_or_404(DieWork, id=work_id)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('worker')
        diam_min = request.POST.get('diametro_min')
        diam_max = request.POST.get('diametro_max')

        if not user_id:
            messages.error(request, "Selecione um utilizador.")
            return redirect(request.path)

        user = get_object_or_404(User, id=user_id)



        # Adicionar trabalhador ao trabalho
        DieWorkWorker.objects.create(work=work, worker=user, diam_min=diam_min or None, diam_max=diam_max or None)
        messages.success(request, f"Trabalhador {user.username} adicionado com sucesso!")
        return redirect('die_details', die_id=work.die.id)

    return render(request, 'theme/add_worker_to_die_work.html', {
        'work': work,
        'users': users
    })


def export_qrcode_excel(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)
    dies = qr.die_instances.all()

    # Criar lista com dados
    data = []
    for die in dies:
        data.append({
            "Year": qr.toma_order_year,
            "Toma Order NR": qr.toma_order_nr,
            "Customer": qr.customer,
            "Customer Order NR": qr.customer_order_nr,
            "Reception Date": qr.created_at.strftime("%d/%m/%Y"),
            "Shipping Date": "",  # Se existir no modelo, coloca aqui
            "Diameter": qr.diameters,
            "Tech Spec": die.diameter_text,
            "SerialNr": die.serial_number,
            "Required Ø": die.diam_requerido or "",
            "Suggested Ø": "",
            "Type of Die": die.die.get_die_type_display(),
            "Type of Job": die.job.get_job_display(),
            "Min Tol": die.tolerance.min if die.tolerance else "",
            "Max Tol": die.tolerance.max if die.tolerance else "",
            "Min Ø": die.diam_max_min.min if die.diam_max_min else "",
            "Max Ø": die.diam_max_min.max if die.diam_max_min else "",
            "Observations": die.observations or "",
            "BoxNR": qr.box_nr,
        })

    # Converter para DataFrame
    df = pd.DataFrame(data)

    # Criar resposta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="QRCode_{qr.toma_order_nr}_Caixa_{qr.box_nr}.xlsx"'

    # Gravar no Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dados', index=False)

                # Adiciona log na tabela globalLogs
    globalLogs.objects.create(
        user=request.user,
        action=f"{request.user.username} criou um exel da ordem {qr.toma_order_nr}",
    )

    return response

 


@login_required
def info_fieira(request, die_id):
    die = get_object_or_404(dieInstance, id=die_id)
    serial_number = die.serial_number

    if request.method == 'POST':
        # Cria um novo registro (não atualiza o anterior)
        InfoFieira.objects.create(
            serial_number=serial_number,
            diametro_atual=request.POST.get('diametro_atual') or None,
            angulo=request.POST.get('angulo') or None,
            po=request.POST.get('po') or None,
            tempo=request.POST.get('tempo') or None,
            observacoes=request.POST.get('observacoes') or None,
            utilizador=request.user,
            quando=timezone.now(),
        )
        messages.success(request, "Novo registro adicionado com sucesso!")
        return redirect('infoFieira', die_id=die_id)

    registros = InfoFieira.objects.filter(serial_number=serial_number).order_by('-quando')

    context = {
        'die': die,
        'serial_number': serial_number,
        'registros': registros,
    }
    return render(request, 'theme/infoFieira.html', context)

@login_required
def enviar_fieira(request, die_id):
    die = get_object_or_404(dieInstance, id=die_id)

    # Obter a última localização, se existir
    current_location = die.locations.order_by('-updated_at').first()  # related_name='locations'

    if request.method == 'POST':
        destino = request.POST.get('where')
        if destino in dict(WhereDie.ONDESTA):
            # Criar um novo registro para manter histórico
            new_location = WhereDie.objects.create(die=die, where=destino)
            
            # Criar log da ação
            globalLogs.objects.create(
                user=request.user,
                action=f"{request.user} enviou a fieira {die.serial_number} para {new_location.get_where_display()}",
            )
            
            messages.success(request, f"Fieira {die.serial_number} enviada para {new_location.get_where_display()}.")
            return redirect('listarDies')
        else:
            messages.error(request, "Destino inválido.")
    
    return render(request, 'theme/enviar_fieira.html', {
        'die': die,
        'current_location': current_location,
        'choices': WhereDie.ONDESTA
    })


@login_required
def enviar_caixa(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)
    dies = qr.die_instances.only('id')

    if request.method == 'POST':
        destino = request.POST.get('where')
        if destino in dict(whereBox.ONDESTA):
            # Atualiza ou cria a localização da caixa
            box_location, created = whereBox.objects.get_or_create(order_number=qr)
            box_location.where = destino
            box_location.save()

            for die in dies:
                destino = request.POST.get('where')
                if destino in dict(WhereDie.ONDESTA):
                    WhereDie.objects.create(die=die, where=destino)

            # Mensagem de sucesso
            messages.success(request, f"Caixa enviada para {box_location.get_where_display()}.")

            # Adiciona log na tabela globalLogs
            globalLogs.objects.create(
                user=request.user,
                action=f"{request.user.username} enviou a caixa {qr.toma_order_nr} para {box_location.get_where_display()}",
            )

            return redirect('listarDies')
        else:
            messages.error(request, "Opção inválida.")

    return render(request, 'theme/enviar_caixa.html', {'qr': qr, 'choices': whereBox.ONDESTA})

@login_required
def contar_dies_por_usuario(qr_id, user_id):

    count = DieWorkWorker.objects.filter(
        die_work__die__customer_id=qr_id, 
        worker_id=user_id
    ).aggregate(total=Count('id'))['total']

    return count

@login_required
def editar_pedido_inline(request, id):
    pedido = get_object_or_404(PedidosDiametro, id=id)
    # Procuramos a instância da fieira associada ao QR Code do pedido
    die = dieInstance.objects.filter(customer=pedido.qr_code).first()
    
    if request.method == "POST":

        novo_diametro_valor = request.POST.get('novo_diametro')
        diametro_min_valor = request.POST.get('diametro_min')

        pedido.diametro_min = diametro_min_valor
        pedido.novo_diametro = novo_diametro_valor
        pedido.save()

        if die:
            die.new_diameter = novo_diametro_valor   
            die.save()            
        else:
            messages.error(request, "Fieira associada ao pedido não encontrada.")

        return redirect('listarPedidosDiametro')
    
    return redirect('listarPedidosDiametro')

@login_required
def exportar_pedido_excel(request, id):
    # 1. Buscar o pedido
    pedido = get_object_or_404(PedidosDiametro, id=id)

    # 2. Replicar a lógica para encontrar a Caixa e Diâmetros (igual à tua listagem)
    numeros_serie = dieInstance.objects.filter(customer=pedido.qr_code).values_list('serial_number', flat=True)
    serie_dies_pedido = pedido.serie_dies.split(', ')
    numeros_iguais = [num for num in numeros_serie if num in serie_dies_pedido]

    box_nr = "-"
    original_dims_str = "-"
    requerido_dim_str = "-"

    if pedido.qr_code:
        die_instances = dieInstance.objects.filter(customer=pedido.qr_code, serial_number__in=numeros_iguais)
        if die_instances.exists():
            box_nr = die_instances.first().customer.box_nr
            
            # Formatar originais
            original_dims = [die.diameter_text for die in die_instances]
            original_dims_str = ', '.join(original_dims)
            
            # Formatar requeridos
            requerido_dims = [str(die.diam_requerido) for die in die_instances]
            requerido_dim_str = ', '.join(requerido_dims)

    # 3. Criar o ficheiro Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Pedido {pedido.id}"

    # Cabeçalhos
    headers = [
        "Cliente", "Serial", "Box Nr", "Ø Original", "Ø Atual", 
        "Trabalhado", "Ø Requerido", "Descrição", "Ø Mínimo", 
        "Ø Novo", "Pedido Por", "Data", "Estado"
    ]
    ws.append(headers)

    # Dados
    row = [
        str(pedido.qr_code.customer if pedido.qr_code else "-"),
        pedido.serie_dies,
        str(box_nr),
        original_dims_str,
        str(pedido.diametro),
        "Sim" if pedido.trabalhado else "Não",
        requerido_dim_str,
        pedido.get_observations_display(),
        str(pedido.diametro_min),
        str(pedido.novo_diametro),
        pedido.pedido_por,
        pedido.created_at.strftime("%d/%m/%Y %H:%M"),
        "Feito" if pedido.checkbox else "Pendente"
    ]
    ws.append(row)

    # Ajustar largura das colunas (opcional, para ficar bonito)
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    # 4. Preparar resposta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=Pedido_{pedido.serie_dies}_{pedido.id}.xlsx'
    
    wb.save(response)
    return response

@csrf_exempt
@login_required
def listarPedidosDiametro(request):
    pedidos = PedidosDiametro.objects.all().order_by('-created_at')
    pedidos_com_box = []

    for pedido in pedidos:
        if pedido.observations:
            pedido.obs_limpa = pedido.observations.replace('_', ' ').title()
        numeros_serie = dieInstance.objects.filter(customer=pedido.qr_code).values_list('serial_number', flat=True)

        serie_dies_pedido = pedido.serie_dies.split(', ')  # Access 'serie_dies' on the individual 'pedido' object
        numeros_iguais = [num for num in numeros_serie if num in serie_dies_pedido]

        # Verifica se o pedido está associado a um QR Code e obtém o box_nr
        qr_code = pedido.qr_code  


        box_nr = None
        original_dim = None
        requerido_dim = None
        if qr_code is not None:
            die_instances = dieInstance.objects.filter(customer=qr_code, serial_number__in=numeros_iguais)
            if die_instances.exists():
                n_encomenda = die_instances.first().customer.customer_order_nr
                cliente = die_instances.first().customer.customer
                box_nr = die_instances.first().customer.box_nr
                requerido_dim = []
                for die in die_instances:
                    requerido_dim_value = die.diam_requerido
                    requerido_dim.append(f"{requerido_dim_value}")
                    requerido_dim_str = ' \n'.join(requerido_dim)
                diam_requerido = die_instances.first().diam_requerido
                original_dims = []
                for die in die_instances:
                    original_dim = die.diameter_text
                    original_dims.append(f"{original_dim}")
                    original_dims_str = ' \n'.join(original_dims)

        pedidos_com_box.append({
            'pedido': pedido,
            'box_nr': box_nr,
            'original_dim': original_dims_str,
            'diam_requerido': diam_requerido,
            'requerido_dim_str': requerido_dim_str,
            'n_encomenda': n_encomenda,
            'cliente': cliente,
            'obs_limpa': getattr(pedido, 'obs_limpa', '-')

        })

    return render(request, 'theme/listarPedidosDiametro.html', {'pedidos_com_box': pedidos_com_box})

@csrf_exempt
@login_required
def diametroMenu(request, toma_order_full):
    try:
        qr_code = QRData.objects.get(toma_order_full=toma_order_full)
    except QRData.DoesNotExist:
        messages.error(request, 'QR Code não encontrado.')
        return redirect('listarDies')

    dies_existentes = dieInstance.objects.filter(customer=qr_code).order_by('-created_at')  # <- os dies deste QR
    observation_choices = PedidosDiametro._meta.get_field('observations').choices

    if request.method == 'POST':
        numero = request.POST.get('numeroAlterar')
        diametro = request.POST.get('diametroAtual')
        diametro_min = request.POST.get('diametroMin')
        pedido_por = request.POST.get('pedidoPor')
        serie_dies_list = request.POST.getlist('serieDies')  # <-- recebe os checkboxes
        serie_dies = ', '.join(serie_dies_list)
        fieira_trabalhada = request.POST.get('fieiraTrabalhada')
        observations = request.POST.get('observations', '')

        # Aceita valores antigos (Sim/Não) e atuais do radio (True/False).
        fieira_trabalhada = str(fieira_trabalhada).strip().lower() in {'true', 'sim', '1', 'on'}
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
                    diametro_min=diametro_min,
                    numero_fieiras=numero,
                    pedido_por=pedido_por,
                    serie_dies=serie_dies,
                    observations=observations,
                    trabalhado=fieira_trabalhada,
                )
                
                messages.success(request, f'Pedido de diâmetro {diametro} para {numero} fieiras adicionado com sucesso!')
                
                globalLogs.objects.create(
                    user=request.user,
                    action=f"{request.user.username} adicionou um pedido de diâmetro {diametro} para {numero} fieiras no QR Code {qr_code.toma_order_full}.",
                )
                
                # Bloco de Email
                try:
                    # Garantir que é uma lista
                    lista_diametro = settings.EMAIL_DIAMETRO if isinstance(settings.EMAIL_DIAMETRO, list) else [settings.EMAIL_DIAMETRO]
                    
                    # Usar o EmailMessage em vez do send_mail
                    email = EmailMessage(
                        subject="Novo Pedido de Diâmetro",
                        body=(
                            f"Novo pedido de diâmetro criado:\n"
                            f"Pedido criado por {request.user.username}\n"
                            f"- QR Code: {qr_code.toma_order_full}\n"
                            f"- Cliente: {qr_code.customer}\n"
                            f"- Diâmetro: {diametro}\n"
                            f"- Nº de fieiras: {numero}\n"
                            f"- Pedido por: {pedido_por or '-'}\n"
                            f"- Matrícula: {serie_dies or '-'}\n"
                            f"- Observações: {observations or '-'}"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[settings.DEFAULT_FROM_EMAIL], # Envia para o vosso email principal
                        bcc=lista_diametro,               # E envia para as 9 pessoas em oculto
                    )
                    email.send(fail_silently=False)
                    
                except Exception as e:
                    messages.error(request, f"Pedido adicionado, mas falha ao enviar email: {str(e)}")
                return redirect('listarDies') 

        except ValueError:
            messages.error(request, 'Número de fieiras inválido. Por favor, insira um número válido.')
        except Exception as e:
            messages.error(request, f'Erro ao adicionar pedido: {str(e)}')
            
    return render(request, 'theme/diametroMenu.html', {
        'qr_code': qr_code,
        'dies_existentes': dies_existentes,
        'choices' : observation_choices,
    })
                

@login_required
def listarPartidos(request):
    numero_partidos = NumeroPartidos.objects.all().order_by('-created_at')
    return render(request, 'theme/listarPartidos.html', {'numero_partidos': numero_partidos})

@login_required
def localizarFieira(request):
    q = request.GET.get('q', '').strip()
    results = []
    
    if q:
        # Define um Prefetch para obter a última localização (WhereDie) de cada fieira
        latest_location_prefetch = Prefetch(
            'locations',  # O related_name no modelo dieInstance é 'locations'
            queryset=WhereDie.objects.order_by('-updated_at'),
            to_attr='latest_location' # Armazena o resultado em 'latest_location'
        )
        
        results = (
            dieInstance.objects
            .select_related('customer') # QRData (box_nr, toma_order_full, customer)
            # Adiciona o Prefetch à query
            .prefetch_related(latest_location_prefetch) 
            .filter(serial_number__icontains=q) 
            .order_by('serial_number')[:100]
        )

    return render(request, 'theme/localizarFieira.html', {
        'q': q,
        # 'die': die, # <-- Remova, ou defina como None, para evitar confusão.
        'results': results,
    })


@login_required
def deliveryCalendar(request):
    today = timezone.localdate()

    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year, month = today.year, today.month

    # limites do mês
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # eventos só do mês (com deliveryDate definido)
    events = DeliveryInfo.objects.filter(deliveryDate__range=(first_day, last_day))

    # mapa por dia
    events_by_day = {}
    for ev in events:
        events_by_day.setdefault(ev.deliveryDate, []).append(ev)

    cal = calendar.Calendar(firstweekday=0)   # 0 = Segunda, 6 = Domingo
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_cells = []
        for d in week:
            in_month = (d.month == month)
            day_events = events_by_day.get(d, [])
            is_today = (d == today)
            # “a vermelho” se dentro dos próximos 7 dias (>= hoje e <= hoje+7)
            is_soon = (d >= today and d <= today + timedelta(days=7) and in_month and len(day_events) > 0)
            week_cells.append({
                'date': d,
                'in_month': in_month,
                'events': day_events,
                'is_today': is_today,
                'is_soon': is_soon,
            })
        weeks.append(week_cells)

    # avisos (lista plana dos próximos 7 dias com eventos, independentemente do mês)
    soon_start = today
    soon_end = today + timedelta(days=7)
    soon_events = (
        DeliveryInfo.objects
        .filter(deliveryDate__range=(soon_start, soon_end))
        .order_by('deliveryDate')
    )

    # navegação (prev/next)
    prev_month = (first_day.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (last_day + timedelta(days=1)).replace(day=1)

    context = {
        'today': today,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'weeks': weeks,
        'soon_events': soon_events,
        'prev_year': prev_month.year,
        'prev_month': prev_month.month,
        'next_year': next_month.year,
        'next_month': next_month.month,
    }
    return render(request, 'theme/deliveryCalendar.html', context)

@login_required
def create_tracking(request, pk=None):
    tracking = get_object_or_404(Tracking, pk=pk) if pk else None

    view_type = request.GET.get('view', 'cards')

    if request.method == 'POST':
        # 1) ler campos
        data             = parse_date(request.POST.get('data') or '')
        finalidade       = (request.POST.get('finalidade') or '').strip()   # "Importacao" | "Exportacao"
        crm              = request.POST.get('crm') or ''
        transportadora   = request.POST.get('transportadora') or ''
        carta_de_porte   = request.POST.get('carta_de_porte') or ''
        numero_recolha   = request.POST.get('numero_recolha') or ''
        recebido_por     = request.POST.get('recebido_por') or ''
        data_entrega = parse_date(request.POST.get('data_entrega')) if request.POST.get('data_entrega') else None
        cliente          = request.POST.get('cliente') or ''
        email            = request.POST.get('email') or ''
        enviado          = 'enviado' in request.POST
        observacoes      = request.POST.get('observacoes') or ''


        with transaction.atomic():
            if tracking is None:
                tracking = Tracking.objects.create(
                    data=data,
                    finalidade=finalidade,
                    crm=crm,
                    transportadora=transportadora,
                    carta_de_porte=carta_de_porte,
                    numero_recolha=numero_recolha,
                    recebido_por=recebido_por,
                    data_entrega=data_entrega,
                    cliente=cliente,
                    email=email,
                    enviado=enviado,
                    observacoes=observacoes,
                )
            else:
                tracking.data = data
                tracking.finalidade = finalidade
                tracking.crm = crm
                tracking.transportadora = transportadora
                tracking.carta_de_porte = carta_de_porte
                tracking.numero_recolha = numero_recolha
                tracking.recebido_por = recebido_por
                tracking.data_entrega = data_entrega
                tracking.cliente = cliente
                tracking.email = email
                tracking.enviado = enviado
                tracking.observacoes = observacoes
                tracking.save()

            # 3) remover anexos marcados
            ids_a_remover = request.POST.getlist('delete_files')
            if ids_a_remover:
                for tf in TrackingFile.objects.filter(id__in=ids_a_remover):
                    tracking.files.remove(tf)
                    if tf.trackings.count() == 0:
                        tf.file.delete(save=False)
                        tf.delete()

            # 4) upload de novos ficheiros
            for f in request.FILES.getlist('files'):
                tf = TrackingFile.objects.create(file=f)
                tracking.files.add(tf)

        return redirect(reverse('listarTracking') + f'?view={view_type}')
    
    # GET – render do form (mesmo template para add/edit)
    context = {
        'tracking': tracking,
        'finalidades': Tracking._meta.get_field('finalidade').choices,
        'transportadoras': Tracking.courier_choices,
    }
    return render(request, 'theme/adicionarTracking.html', context)


@login_required
def listar_trackings(request):
    qs = Tracking.objects.all().prefetch_related('files')

    # filtros
    q                = (request.GET.get('q') or '').strip()
    finalidade       = request.GET.get('finalidade') or ''
    entregue         = request.GET.get('entregue') or ''
    transportadora   = request.GET.get('transportadora') or ''
    recebido_por     = (request.GET.get('recebido_por') or '').strip()
    de               = request.GET.get('de') or ''
    ate              = request.GET.get('ate') or ''
    # NOVOS filtros dedicados:
    cliente_q       = (request.GET.get('cliente') or '').strip()

    if q:
        qs = qs.filter(
            Q(crm__icontains=q) |
            Q(cliente__icontains=q) |
            Q(numero_recolha__icontains=q) |
            Q(carta_de_porte__icontains=q) |
            Q(observacoes__icontains=q) |
            Q(email__icontains=q)
        )
    if finalidade:
        qs = qs.filter(finalidade=finalidade)

    if entregue:
        if entregue == 'sim':
            # Retorna se tiver data de entrega OU (quem recebeu não é nulo E não é vazio)
            qs = qs.filter(
                Q(data_entrega__isnull=False) | 
                (~Q(recebido_por__isnull=True) & ~Q(recebido_por__exact=''))
            )
            
        elif entregue == 'nao':
            # Retorna se a data de entrega é nula E (quem recebeu é nulo OU vazio)
            qs = qs.filter(
                Q(data_entrega__isnull=True),
                Q(recebido_por__isnull=True) | Q(recebido_por__exact='')
        )
        
    if transportadora:
        qs = qs.filter(transportadora=transportadora)
    if recebido_por:
        qs = qs.filter(recebido_por__icontains=recebido_por)

    # NOVO: filtros específicos
    if cliente_q:
        qs = qs.filter(cliente__icontains=cliente_q)



    de_date = parse_date(de) if de else None
    ate_date = parse_date(ate) if ate else None
    if de_date:
        qs = qs.filter(data__gte=de_date)
    if ate_date:
        qs = qs.filter(data__lte=ate_date)

    # ordenação
    sort = request.GET.get('sort') or '-data'
    allowed = {'data','finalidade','crm','cliente','transportadora',
               'carta_de_porte','numero_recolha','recebido_por','data_entrega',
               'email','observacoes'}
    qs = qs.order_by(sort, '-id') if sort.lstrip('-') in allowed else qs.order_by('-data','-id')

    # paginação
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    # querystring sem page
    params = request.GET.copy(); params.pop('page', None)
    current_query = params.urlencode()



    columns = [
        ('data', 'Data'),
        ('finalidade', 'Finalidade'),
        ('crm', 'CRM'),
        ('cliente', 'Cliente'),        # nesta vamos mostrar "um ou outro"
        ('transportadora', 'Transportadora'),
        ('carta_de_porte', 'Carta de Porte'),
        ('numero_recolha', 'Nº Recolha'),
        ('recebido_por', 'Recebido Por'),
        ('data_entrega', 'Data Entrega'),
        ('email', 'Email'),
        ('email_enviado', 'Email Enviado'),
        ('observacoes', 'Observações'),
    ]

    context = {
        'trackings': page_obj.object_list,
        'page_obj': page_obj,
        'current_query': current_query,
        'sort': sort,
        'q': q,
        'selected_finalidade': finalidade,
        'selected_entregue': entregue,
        'selected_transportadora': transportadora,
        'recebido_por': recebido_por,
        'de': de,
        'ate': ate,
        'cliente': cliente_q,
        'finalidades': Tracking._meta.get_field('finalidade').choices,
        'transportadoras': Tracking.courier_choices,
        'columns': columns,
    }
    template = 'theme/listarTrackings_cards.html' if (request.GET.get('view') or 'cards') == 'cards' else 'theme/trackingList.html'
    return render(request, template, context)


@login_required
def listar_medicoes(request):
    medicao = Medicao.objects.all().order_by('-date')
    detalhes = DetalhesMedicao.objects.all()
    maquina = Maquinas.objects.all()
    medidas_maquinas = MedidasMaquinas.objects.all()
    user = request.user

    def to_decimal(value):
        return value if value not in (None, '') else None

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'adicionar_fieira':

            numero_serie = request.POST.get('serie_number')
            diametro = request.POST.get('diametro')

            try:
                diametro_decimal = to_decimal(diametro)
                MedidasMaquinas.objects.create(
                    serie_number=numero_serie,
                    diameter=diametro_decimal,
                )
                messages.success(request, "Fieira adicionada com sucesso!")
                return redirect('listarMedicoes')  # usa o name da tua url
            except Exception as e:
                messages.error(request, f"Erro ao adicionar fieira: {e}")
        elif form_type == 'adicionar_leitura':
            edit_id = request.POST.get('edit_id')        # id da medicao original 
            maquina_id = request.POST.get('maquina')    # id da maquina escolhida no select 
            diameter = request.POST.get('diameter')
            bearing = request.POST.get('bearing')
            ovality = request.POST.get('ovality')
            toleranciaMin = request.POST.get('toleranciaMin')
            toleranciaMax = request.POST.get('toleranciaMax')

            def to_decimal(v): 
                return v if v not in (None, '') else None

            # valida edit_id
            medicao_obj = None
            if edit_id:
                try:
                    medicao_obj = Medicao.objects.get(id=int(edit_id))
                except (ValueError, Medicao.DoesNotExist):
                    medicao_obj = None

            # então criamos/obtemos uma medição para a combinação máquina + fieira
            if maquina_id:
                try:
                    maquina_obj = Maquinas.objects.get(id=int(maquina_id))
                except (ValueError, Maquinas.DoesNotExist):
                    maquina_obj = None

                # se já temos medicao_obj e a máquina é a mesma, keep it
                if medicao_obj and medicao_obj.machine.id == maquina_obj.id:
                    target_medicao = medicao_obj
                else:
                    diameter_obj = None
                    fieira_id = request.POST.get('fieira_id')
                    if fieira_id:
                        try:
                            diameter_obj = MedidasMaquinas.objects.get(id=int(fieira_id))
                        except:
                            diameter_obj = None
                    elif medicao_obj:
                        diameter_obj = medicao_obj.diameter

                    if diameter_obj and maquina_obj:
                        # opcional: tenta reutilizar uma medição existente (por ex. última do dia)
                        existing = Medicao.objects.filter(machine=maquina_obj, diameter=diameter_obj).order_by('-date').first()
                        if existing:
                            target_medicao = existing
                        else:
                            target_medicao = Medicao.objects.create(
                                machine=maquina_obj,
                                diameter=diameter_obj,
                                date=timezone.now()
                            )
                    else:
                        target_medicao = medicao_obj  
            else:
                target_medicao = medicao_obj

            if not target_medicao:
                messages.error(request, "Não foi possível determinar a Medicao alvo. Abortado.")
            else:
                ultimo = DetalhesMedicao.objects.filter(medicao=target_medicao).order_by('-read_number').first()
                num_leitura = (ultimo.read_number + 1) if ultimo else 1

                DetalhesMedicao.objects.create(
                    read_number=num_leitura,
                    diameter=to_decimal(diameter),
                    bearing=bearing if bearing not in (None, '') else None,
                    ovality=to_decimal(ovality),
                    toleranciaMin=to_decimal(toleranciaMin),
                    toleranciaMax=to_decimal(toleranciaMax),
                    medicao=target_medicao,
                    operador=request.user,
                )
                messages.success(request, "Leitura adicionada com sucesso!")
                return redirect('listarMedicoes')  # usa o name da tua url
        
    dados_completos = OrderedDict()
    for medida in medidas_maquinas:
        # pega todas as medições existentes para essa medida
        medicoes_existentes = Medicao.objects.filter(diameter=medida).order_by('-date')
        dados_completos[medida] = medicoes_existentes  # QuerySet vazio se não houver

    return render(request, 'theme/listarMedicoes.html', {
        'dados_completos': dados_completos,
        'maquina': maquina,
        'medidas_maquinas': medidas_maquinas,
        'user': request.user,
    })

@login_required
def listar_calibracoes(request):
    calibracoes = CalibracaoMaquina.objects.all().order_by('-date')
    maquinas = Maquinas.objects.all()

    if request.method == 'POST':
        maquina_id = request.POST.get('machine_id')
        diam_original = Decimal(request.POST.get('diam_original'))
        diam_calibrado = Decimal(request.POST.get('diam_calibrado'))
        
        diam_calibrado_min = request.POST.get('diam_calibrado_min')
        diam_calibrado_max = request.POST.get('diam_calibrado_max')

        # converte vazio para None
        diam_calibrado_min = Decimal(diam_calibrado_min) if diam_calibrado_min else None
        diam_calibrado_max = Decimal(diam_calibrado_max) if diam_calibrado_max else None

        details = request.POST.get('details')
        data_calibracao = timezone.now()
        user = request.user

        try:
            maquina = Maquinas.objects.get(id=maquina_id)
            CalibracaoMaquina.objects.create(
                machine=maquina,
                diam_original=diam_original,
                diam_calibrado=diam_calibrado,
                diam_calibrado_min=diam_calibrado_min,
                diam_calibrado_max=diam_calibrado_max,
                date=data_calibracao,
                operador=user,
                details=details
            )
            messages.success(request, "Calibração adicionada com sucesso!")
        except Maquinas.DoesNotExist:
            messages.error(request, "Máquina não encontrada. Por favor, selecione uma máquina válida.")
        except Exception as e:
            messages.error(request, str(e))

        return redirect('listarCalibracoes')
    
    return render(request, 'theme/listar_calibracoes.html', {'calibracoes': calibracoes, 'maquinas': maquinas})

def charts(request):
    # --- Parte 1: Determinação do Intervalo de Tempo ---
    try:
        days_range = int(request.GET.get('days', 7))
    except ValueError:
        days_range = 7
        
    if days_range not in [7, 30, 90, 365]:
        days_range = 7

    today = timezone.now().date()
    # A data de início é days_range - 1 para incluir o dia de hoje
    start_date = today - timedelta(days=days_range - 1)
    
    chart_series = []
    date_labels = []

    # --- Parte 2: Otimização e Agregação de Dados ---

    # Agrupamento base para todos os trabalhadores no período
    filtro_base = {
        'added_at__date__range': [start_date, today],
        'id__isnull': False # Garante que só conta trabalhos reais
    }

    # 7 & 30 Dias: Agregação Diária
    if days_range in [7, 30]:
        # TruncDay agrupa os dados por dia (eficiente na BD)
        raw_data = DieWorkWorker.objects.filter(**filtro_base).annotate(
            period=TruncDay('added_at')
        ).values('worker__username', 'period').annotate(total_works=Count('id'))

        # Gerar lista de datas/rótulos
        dates_list = [start_date + timedelta(days=i) for i in range(days_range)]
        date_labels = [d.strftime('%d %b') for d in dates_list]
        
        # Mapeamento e Estruturação
        data_map = {}
        workers_found = set()
        for entry in raw_data:
            # O Django retorna 'period' como datetime, convertemos para date
            period_date = entry['period'].date() if hasattr(entry['period'], 'date') else entry['period']
            username = entry['worker__username'] or 'Desconhecido'
            workers_found.add(username)
            data_map[(username, period_date)] = entry['total_works']

        # Montar a série final para o ApexCharts
        for username in workers_found:
            data_points = []
            for d in dates_list:
                data_points.append(data_map.get((username, d), 0))
            
            # Só inclui se houver pelo menos 1 trabalho no período
            if sum(data_points) > 0:
                chart_series.append({'name': username, 'data': data_points})


    # 90 Dias: Agregação Quinzenal (2 semanas)
    elif days_range == 90:
        # Buscamos dados diários e agrupamos em Python (mais simples que agregar por quinzena na BD)
        raw_data_daily = DieWorkWorker.objects.filter(**filtro_base).values(
            'worker__username', 'added_at__date'
        ).annotate(total_works=Count('id'))

        # Criar buckets de 14 dias (quinzenas)
        periods = []
        current = start_date
        while current <= today:
            periods.append(current)
            current += timedelta(days=14)
            
        date_labels = [f"Início {d.strftime('%d/%m')}" for d in periods]
        
        user_buckets = {} 
        
        for entry in raw_data_daily:
            username = entry['worker__username'] or 'Desconhecido'
            entry_date = entry['added_at__date']
            qty = entry['total_works']
            
            if username not in user_buckets:
                user_buckets[username] = [0] * len(periods)
            
            # Descobrir em qual quinzena este dia cai
            delta = (entry_date - start_date).days
            bucket_index = int(delta // 14)
            
            if 0 <= bucket_index < len(periods):
                user_buckets[username][bucket_index] += qty

        for username, data_points in user_buckets.items():
            if sum(data_points) > 0:
                chart_series.append({'name': username, 'data': data_points})


    # 365 Dias: Agregação Mensal
    elif days_range == 365:
        # TruncMonth agrupa os dados por mês (eficiente na BD)
        raw_data = DieWorkWorker.objects.filter(**filtro_base).annotate(
            period=TruncMonth('added_at')
        ).values('worker__username', 'period').annotate(total_works=Count('id'))

        # Gerar lista de meses para o eixo X
        current = start_date.replace(day=1)
        months_periods = []
        while current <= today:
            months_periods.append(current)
            current = (current + timedelta(days=32)).replace(day=1)
            
        date_labels = [d.strftime('%b %Y') for d in months_periods]
        
        # Mapear dados
        data_map = {}
        workers_found = set()
        for entry in raw_data:
            username = entry['worker__username'] or 'Desconhecido'
            workers_found.add(username)
            d_date = entry['period'].date() if hasattr(entry['period'], 'date') else entry['period']
            data_map[(username, d_date)] = entry['total_works']

        # Montar séries
        for username in workers_found:
            data_points = []
            for m_date in months_periods:
                qty = data_map.get((username, m_date), 0)
                data_points.append(qty)
            
            if sum(data_points) > 0:
                chart_series.append({'name': username, 'data': data_points})


    return render(request, 'theme/charts.html', {
        'chart_data': chart_series,       # O teu 'chart_series' é agora 'chart_data'
        'chart_dates': date_labels,       # O teu 'date_labels' é agora 'chart_dates'
        'current_range': days_range,      # O teu 'selected_days_range' é agora 'current_range'
    })

@login_required
@admin_required
def listarFaturas(request):
    ordenacao = request.GET.get('ordenacao', 'recentes')

    if ordenacao == 'nao_pagos':
        invoice_qs = faturas.objects.all().order_by('pago', '-created_at')
    elif ordenacao == 'pagos':
        invoice_qs = faturas.objects.all().order_by('-pago', '-created_at')
    else:
        invoice_qs = faturas.objects.all().order_by('-created_at')

    fornecedor = Fornecedor.objects.all().order_by('name') 

    de = request.GET.get('de') or ''
    ate = request.GET.get('ate') or ''

    de_date = parse_date(de) if de else None
    ate_date = parse_date(ate) if ate else None

    if de_date and ate_date and de_date > ate_date:
        messages.error(request, "Eu sou só um filtro não posso viajar no tempo!")
        return redirect('listarFaturas')

    if de_date:
        invoice_qs = invoice_qs.filter(data_emissao__gte=de_date)
    if ate_date:
        invoice_qs = invoice_qs.filter(data_emissao__lte=ate_date)

    filtro_pago = request.GET.get('pago')
    if filtro_pago == 'sim':
        invoice_qs = invoice_qs.filter(pago=True)
    elif filtro_pago == 'nao':
        invoice_qs = invoice_qs.filter(pago=False)

    return render(request, 'theme/listarFaturas.html', {
        'invoice_qs': invoice_qs,
        'de': de, 
        'ate': ate, 
        'fornecedor': fornecedor, 
        'filtro_pago': filtro_pago,
        'ordenacao': ordenacao # Adicionado aqui!
    })

@login_required
@admin_required
def criarFatura(request):
    fornecedores = Fornecedor.objects.all().order_by('name')

    if request.method == 'POST':
        # Captura os dados
        fornecedor_id = request.POST.get('fornecedor')
        numero_fatura = request.POST.get('numero_fatura')
        data_fatura = request.POST.get('data_fatura')
        data_emissao = request.POST.get('data_emissao')
        valor = request.POST.get('valor')
        moeda = request.POST.get('moeda')
        descricao = request.POST.get('descricao')
        
        try:
            fornecedor = Fornecedor.objects.get(id=fornecedor_id)
            
            if fornecedor.debito_direto == False:
                if not data_fatura:
                    messages.error(request, "A data limite de pagamento é obrigatória quando débito direto não está ativo.")
                    
                    # AQUI ESTÁ O TRUQUE:
                    # Enviamos 'values': request.POST para o template recuperar os dados
                    return render(request, 'theme/criarFatura.html', {
                        'fornecedores': fornecedores,
                        'values': request.POST 
                    })
                
                japago = False
            else:
                data_fatura = None
                japago = True

            nova_fatura = faturas(
                fornecedor=fornecedor,
                numero_fatura=numero_fatura,
                data_fatura=data_fatura,
                pago=japago,
                data_emissao=data_emissao,
                valor=valor,
                moeda=moeda,
                descricao=descricao,
            )
            nova_fatura.save() # Aqui o fatura_unica é gerado pelo teu model
            # Adiciona ficheiros após salvar a fatura
            for ficheiro in request.FILES.getlist('ficheiros'):
                FaturaFile.objects.create(fatura=nova_fatura, file=ficheiro)
            for ficheiro_estrangeiro in request.FILES.getlist('ficheiros_estrangeiro'):
                FaturaEstrangeitoFile.objects.create(fatura=nova_fatura, file=ficheiro_estrangeiro)
            
            messages.success(request, "Fatura criada com sucesso!")
            return redirect('listarFaturas') # Altera para o nome da tua rota de listagem
            
        except Exception as e:
            messages.error(request, f"Erro ao criar fatura: {e}")
            # Em caso de erro genérico (ex: base de dados), também devolvemos os dados
            return render(request, 'theme/criarFatura.html', {
                'fornecedores': fornecedores,
                'values': request.POST
            })

    return render(request, 'theme/criarFatura.html', {'fornecedores': fornecedores})

@login_required
@admin_required
def corrigir_nome_ficheiro(ficheiro):
    """
    Tenta corrigir problemas de codificação no nome do ficheiro (ex: acentos 'í' que vêm como 0xed).
    """
    try:
        ficheiro.name = ficheiro.name.encode('iso-8859-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Se der erro na conversão (ou seja, se já estiver correto ou for muito estranho),
        # deixamos como está para não estragar mais.
        pass
    return ficheiro

@login_required
@csrf_exempt
@admin_required
def editarFatura(request, fatura_id):
    fatura = get_object_or_404(faturas, id=fatura_id)
    
    if request.method == 'POST':
        try:
            fornecedor_id = request.POST.get('fornecedor')
            fatura.fornecedor = Fornecedor.objects.get(id=fornecedor_id)
            fatura.numero_fatura = request.POST.get('numero_fatura')
            fatura.data_fatura = request.POST.get('data_fatura')
            fatura.data_emissao = request.POST.get('data_emissao')
            fatura.valor = request.POST.get('valor')
            fatura.moeda = request.POST.get('moeda')
            fatura.descricao = request.POST.get('descricao')

            # Lógica da checkbox Pago
            pago_checkbox = 'pago' in request.POST
            novos_ficheiros_pago = request.FILES.getlist('ficheiro_pago')
            
            if pago_checkbox or novos_ficheiros_pago:
                fatura.pago = True
            else:
                if not fatura.ficheiros_pago.exists():
                     fatura.pago = False
            
            fatura.save()

            # --- AQUI ESTÁ A CORREÇÃO MÁGICA ---
            
            # 1. Ficheiros Gerais
            for ficheiro in request.FILES.getlist('ficheiros'):
                ficheiro = corrigir_nome_ficheiro(ficheiro) # <--- Limpa o nome
                FaturaFile.objects.create(fatura=fatura, file=ficheiro)

            # 2. Ficheiros Estrangeiros
            for ficheiro_estrangeiro in request.FILES.getlist('ficheiros_estrangeiro'):
                ficheiro_estrangeiro = corrigir_nome_ficheiro(ficheiro_estrangeiro) # <--- Limpa o nome
                FaturaEstrangeitoFile.objects.create(fatura=fatura, file=ficheiro_estrangeiro)

            # 3. Ficheiros de Pagamento
            for fatura_pagamento in novos_ficheiros_pago:
                fatura_pagamento = corrigir_nome_ficheiro(fatura_pagamento) # <--- Limpa o nome
                FaturaPagoFile.objects.create(fatura=fatura, file=fatura_pagamento)

            messages.success(request, "Fatura atualizada com sucesso!")
            return redirect('listarFaturas')

        except Exception as e:
            # Adicionei este print para ajudar a ver o erro real na consola/terminal se acontecer de novo
            print(f"ERRO AO SALVAR FATURA: {e}") 
            messages.error(request, f"Erro ao atualizar fatura: {e}")

    fornecedores = Fornecedor.objects.all().order_by('name')
    
    context = {
        'fatura': fatura, 
        'fornecedores': fornecedores,
        'is_urgent': False # Adicionei isto só para o template não dar erro se faltar a variável
    }
    return render(request, 'theme/editarFatura.html', context)

@login_required
@csrf_exempt
@admin_required
def delete_anexo_api(request):
    file_id = request.POST.get('file_id')
    tipo = request.POST.get('tipo') # 'geral', 'pago', 'estrangeiro'

    try:
        if tipo == 'geral':
            anexo = FaturaFile.objects.get(id=file_id)
        elif tipo == 'pago':
            anexo = FaturaPagoFile.objects.get(id=file_id)
        elif tipo == 'estrangeiro':
            anexo = FaturaEstrangeitoFile.objects.get(id=file_id)
        else:
            return JsonResponse({'status': 'error', 'message': 'Tipo inválido'}, status=400)

        # Apaga o ficheiro do disco e o registo da BD
        anexo.delete()
        
        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    
@require_POST
@csrf_exempt
@admin_required
def upload_arquivo_fatura(request):
    fatura_id = request.POST.get('fatura_id')
    tipo = request.POST.get('tipo')  # 'geral', 'pago', ou 'estrangeiro'
    arquivo = request.FILES.get('ficheiro')

    if not fatura_id or not arquivo or not tipo:
        return JsonResponse({'status': 'error', 'message': 'Dados incompletos'}, status=400)

    try:
        fatura = get_object_or_404(faturas, id=fatura_id)
        novo_anexo = None

        # Decide qual tabela usar com base no tipo
        if tipo == 'geral':
            novo_anexo = FaturaFile.objects.create(fatura=fatura, file=arquivo)
        elif tipo == 'pago':
            novo_anexo = FaturaPagoFile.objects.create(fatura=fatura, file=arquivo)
            if not fatura.pago:
                fatura.pago = True
                fatura.save()
        elif tipo == 'estrangeiro':
            novo_anexo = FaturaEstrangeitoFile.objects.create(fatura=fatura, file=arquivo)
        else:
            return JsonResponse({'status': 'error', 'message': 'Tipo inválido'}, status=400)

        # Retorna os dados
        nome_limpo = os.path.basename(novo_anexo.file.name)
        return JsonResponse({
            'status': 'success', 
            'url': novo_anexo.file.url, 
            'name': nome_limpo
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@group_required('Administracao','Comercial')
def listarFornecedores(request):
    fornecedores = Fornecedor.objects.all().order_by('name')

    if request.method == 'POST':
        # Lógica para adicionar um novo fornecedor
        nome = request.POST.get('nome')
        debito_direto = request.POST.get('debito_direto') == 'on'
        email = request.POST.get('email')
        telefone = request.POST.get('telefone')
        dados_bancarios = request.POST.get('dados_bancarios')
        vat = request.POST.get('vat')
        morada = request.POST.get('morada')
        estrangeiro = request.POST.get('estrangeiro') == 'on'

        try:   
            Fornecedor.objects.create(
                name=nome,
                debito_direto=debito_direto,
                email=email,
                telefone=telefone,
                dados_bancarios=dados_bancarios,
                vat=vat,
                morada=morada,
                estrangeiro=estrangeiro
            )
            messages.success(request, "Fornecedor adicionado com sucesso!")
            return redirect('listarFornecedores')
        except Exception as e:
            messages.error(request, f"Erro ao adicionar fornecedor: {e}")      

    return render(request, 'theme/listarFornecedores.html', {'fornecedores': fornecedores})

@csrf_exempt
@require_POST
@group_required('Administracao','Comercial')
def atualizar_fornecedor(request, id):
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')
        
        fornecedor = get_object_or_404(Fornecedor, id=id)
        
        # Segurança básica: verificar se o campo existe no modelo
        if hasattr(fornecedor, field):
            setattr(fornecedor, field, value)
            fornecedor.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Campo inválido'}, status=400)
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@admin_required    
def deletar_fornecedor(request, id):
    fornecedor = get_object_or_404(Fornecedor, id=id)
    if request.method == 'POST':
        fornecedor.delete()
        messages.success(request, "Fornecedor deletado com sucesso!")
        return redirect('listarFornecedores')
    else:
        messages.error(request, "Método inválido para deletar fornecedor.")
        return redirect('listarFornecedores')

@admin_required    
def templateFiles(request):
    templates = Template.objects.all().order_by('department')
    return render(request, 'theme/templateFiles.html', {'templates': templates})

@csrf_exempt
@require_POST
@admin_required
def upload_template_file(request, id):
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': 'Nenhum ficheiro enviado.'}, status=400)

        template = get_object_or_404(Template, id=id)
        
        # 1. Salva o ficheiro
        file = request.FILES['file']
        template.approved_file = file
        
        # 2. Atualiza os campos automaticamente
        template.approved = True 
        template.approved_by = "Aniceta Graf"
        template.editor = request.user 
        template.last_updated = timezone.now()
        
        template.save()

        # 3. Retorna os dados para atualizar o HTML
        return JsonResponse({
            'status': 'success',
            'file_name': template.approved_file.name.split('/')[-1],
            'file_url': template.approved_file.url,
            'approved_by': template.approved_by,
            'editor_name': request.user.username, 
            'approved': True
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@admin_required
@login_required
def criarTemplate(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        department = request.POST.get('department')
        
        # 1. Pega na lista de ficheiros
        files = request.FILES.getlist('file') 

        try:
            # 2. Cria o Template (PAI) e guarda-o numa variável 'novo_template'
            # Nota: Não precisas passar created_at/last_updated se tiveres auto_now_add no model
            novo_template = Template.objects.create(
                name=name, 
                description=description, 
                department=department
            )

            # 3. Agora fazemos o Loop para salvar os ficheiros (FILHOS)
            if files:
                for f in files:
                    TemplateFiles.objects.create(
                        template=novo_template, # Usa a variável que criaste acima
                        file=f # Passa um ficheiro de cada vez
                    )

            messages.success(request, "Template criado com sucesso!")
            return redirect('templateFiles')

        except Exception as e:
            # Se der erro, convém apagar o template se ele chegou a ser criado (opcional, mas boa prática)
            messages.error(request, f"Erro ao criar template: {e}")

    return render(request, 'theme/criarTemplate.html')

@admin_required
@login_required
def editarTemplate(request, id):
    template = get_object_or_404(Template, id=id)

    if request.method == 'POST':
        template.name = request.POST.get('name')
        template.description = request.POST.get('description')
        template.department = request.POST.get('department')

        template.created_at = request.POST.get('created_at') or template.created_at 
        template.last_updated = request.POST.get('last_updated') or template.last_updated
        template.editor = request.user
        
        # Converter string 'True'/'False' para Booleano
        approved_val = request.POST.get('approved')
        template.approved = True if approved_val == 'True' else False
        template.approved_by = request.POST.get('approved_by') or template.approved_by

        # 1. Adicionar NOVOS ficheiros à lista existente
        new_files = request.FILES.getlist('file')
        for f in new_files:
            TemplateFiles.objects.create(template=template, file=f)

        # 2. Substituir o Ficheiro Aprovado (se for enviado um novo)
        if 'approved_file' in request.FILES:
            template.approved_file = request.FILES['approved_file']

        template.save()
        messages.success(request, "Template atualizado com sucesso!")
        return redirect('templateFiles')

    return render(request, 'theme/editarTemplate.html', {'template': template})

@require_POST
def delete_template_file(request, file_id):
    try:
        # Busca o ficheiro específico pelo ID
        file_to_delete = get_object_or_404(TemplateFiles, id=file_id)
        
        # Apaga da base de dados (e do disco, dependendo da configuração do Django)
        file_to_delete.delete()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def observacoes_caixa(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)
    
    if request.method == 'POST':
        # Vamos buscar apenas o texto novo do formulário
        nova_observacao = request.POST.get('nova_observacao', '').strip()
        
        if nova_observacao:
            # Se já existir texto antigo, juntamos o novo na linha de baixo
            if qr.observations_prod:
                qr.observations_prod += f"\n\n{nova_observacao}"
            # Se a caixa ainda não tiver observações, guarda apenas o texto novo
            else:
                qr.observations_prod = nova_observacao
                
            qr.save()
            messages.success(request, "Observações de produção atualizadas com sucesso!")
            
        return redirect('listarDies')
        
    return render(request, 'theme/observacoes_caixa.html', {'qr': qr, 'qr_id': qr.id})


MAPA_OPERACOES = {
    ('polimento', 'entrada'): 'Polimento Entrada',
    ('polimento', 'saida'): 'Polimento Saída',
    ('polimento', 'cone'): 'Polimento Saída', 
    ('desbaste_agulha', 'entrada'): 'Desbaste Agulha Entrada',
    ('desbaste_agulha', 'saida'): 'Desbaste Agulha Saída',
    ('desbaste_agulha', 'cone'): 'Desbaste Agulha Saída',
    ('desbaste_calibre', 'desbaste_de_calibre'): 'Desbaste Calibre',
    ('desbaste_calibre', 'calibre'): 'Desbaste Calibre',
    ('afinacao', 'afinacao'): 'Afinação',
    ('afinacao', 'calibre'): 'Afinação Calibre',
    # Adiciona as restantes conforme precisares
}

@login_required
@group_required('Administracao','Q-Office')
def relatorio_data(request):

    # --- 1. GESTÃO DE DATAS (POST e GET para testes) ---
    if request.method == 'POST':
        de_date_str = request.POST.get('data_inicio')
        ate_date_str = request.POST.get('data_fim')
        try:
            de_date = parse_date(de_date_str)
            ate_date = parse_date(ate_date_str)
            if not de_date or not ate_date:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Datas inválidas. Por favor, insira datas no formato YYYY-MM-DD.")
            return redirect('relatorio_data') # Ajusta o nome do url se necessário
    else: 
        # Fallback para GET (útil para os teus testes com prints)
        de = request.GET.get('de')
        ate = request.GET.get('ate')
        
        # Se não houver POST nem parâmetros GET, mostra o form vazio
        if not de and not ate and not request.GET.get('test'): 
            return render(request, 'theme/relatorio_data.html')
            
        de_date = parse_date(de) if de else parse_date("2026-03-09")
        ate_date = parse_date(ate) if ate else timezone.now().date()


    # --- 2. QUERIES OTIMIZADAS À BD ---
    trabalhos_no_periodo = DieWorkWorker.objects.filter(
        added_at__date__gte=de_date, 
        added_at__date__lte=ate_date 
    ).select_related(
        'work__die__customer', 
        'work__die__die', 
        'worker'
    )
    
    nr_trabalhos = trabalhos_no_periodo.count()
    nr_fieiras_unicas = trabalhos_no_periodo.values('work__die').distinct().count()

    #print("\n--- TOTAL ---")
    #print(f"Trabalhos realizados entre {de_date} e {ate_date}: {nr_trabalhos}")
    #print(f"Fieiras ÚNICAS mexidas: {nr_fieiras_unicas}")


    # --- 3. TIPO DE FIEIRAS ---
    tipos_fieira_lista = ['ND', 'PCD', 'MCD']
    contagens_tipos_qs = (
        trabalhos_no_periodo
        .values('work__die__die__die_type')
        .annotate(total=Count('work__die', distinct=True)) 
    )
    
    contagens_por_tipo = {
        item['work__die__die__die_type']: item['total']
        for item in contagens_tipos_qs if item['work__die__die__die_type']
    }

    #print("\n--- TIPO DE FIEIRAS ---")
    lista_tipos_front = [] # <--- LISTA PARA O HTML
    for tipo in tipos_fieira_lista:
        total = contagens_por_tipo.get(tipo, 0)
        percentagem = (total / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0
        
        # Guardar para o Front-end
        lista_tipos_front.append({
            'tipo': tipo,
            'total': total,
            'percentagem': percentagem
        })
        #print(f"Número de fieiras '{tipo}': {total} (sendo {percentagem:.2f}% do total de fieiras)")
    


    # --- 4. PARTIDOS ---
    partidos_qs = NumeroPartidos.objects.filter(
        created_at__date__range=(de_date, ate_date)
    ).select_related('qr_code')
    
    total_partidos = partidos_qs.count() 
    contagem_partidos_por_pedido = defaultdict(int)
    
    for partido in partidos_qs:
        if partido.qr_code: 
            ped_partido = f"{partido.qr_code.toma_order_nr}/{partido.qr_code.toma_order_year}"
            qtd = partido.partido if partido.partido else 1
            contagem_partidos_por_pedido[ped_partido] += qtd

    #print("\n--- PARTIDOS ---")
    #print(f"Número de registos de partidos entre {de_date} e {ate_date}: {total_partidos}")

    percentage_partidas = (total_partidos / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0

    # --- 5. TAMANHOS / LISTA DETALHADA ---
    resumo_pedidos_dict = {}

    for trabalho in trabalhos_no_periodo:
        diametro = trabalho.work.die.diameter_text
        cliente = trabalho.work.die.customer.customer
        pedido = f"{trabalho.work.die.customer.toma_order_nr}/{trabalho.work.die.customer.toma_order_year}"
        box = str(trabalho.work.die.customer.box_nr) 
        die_id = trabalho.work.die.id 
        
        if pedido not in resumo_pedidos_dict: 
            resumo_pedidos_dict[pedido] = {'fieiras': set(), 'caixas': set(), 'cliente': cliente, 'diametros_por_fieira': {}}
            
        resumo_pedidos_dict[pedido]['fieiras'].add(die_id)
        
        if box and box != 'None':
            resumo_pedidos_dict[pedido]['caixas'].add(box)
            
        if diametro not in (None, ''):
            resumo_pedidos_dict[pedido]['diametros_por_fieira'][die_id] = str(diametro)

    #print("\n--- RESUMO DE FIEIRAS E CAIXAS POR PEDIDO ---")
    
    lista_pedidos_front = [] # <--- LISTA PARA O HTML
    
    for ped, info in resumo_pedidos_dict.items():
        total_fieiras = len(info['fieiras']) 
        cliente = info['cliente']
        caixas_formatadas = " e ".join(sorted(info['caixas'])) if len(info['caixas']) > 1 else "".join(info['caixas'])
        texto_caixa = "nas caixas" if len(info['caixas']) > 1 else "na caixa"
        diametros_lista = sorted(info['diametros_por_fieira'].values())
        diametros_str = ", ".join(diametros_lista) if diametros_lista else "-"
        
        qtd_partidas = contagem_partidos_por_pedido.get(ped, 0)
        aviso_partidas = f" (Tem {qtd_partidas} fieira(s) partida(s)!)" if qtd_partidas > 0 else ""

        num_mini = num_pequenas = num_medias = num_grandes = num_extragrandes = num_ultra = 0
        for diam in info['diametros_por_fieira'].values():
            try:
                diam_val = float(str(diam).strip().replace(',', '.'))
            except (TypeError, ValueError):
                continue

            if 0.100 <= diam_val <= 0.399: num_mini += 1
            elif 0.400 <= diam_val <= 0.799: num_pequenas += 1
            elif 0.800 <= diam_val <= 1.499: num_medias += 1
            elif 1.500 <= diam_val <= 2.499: num_grandes += 1
            elif 2.500 <= diam_val <= 3.999: num_extragrandes += 1
            elif 4.000 <= diam_val <= 8.000: num_ultra += 1

        #print(f"Numero peq = {num_pequenas}")
        #print(f"Numero med = {num_medias}")
        tamanhos_no_pedido = []
        if num_mini >= 1: tamanhos_no_pedido.append(f"mini: {num_mini}")
        if num_pequenas >= 1: tamanhos_no_pedido.append(f"pequenas: {num_pequenas}")
        if num_medias >= 1: tamanhos_no_pedido.append(f"médias: {num_medias}")
        if num_grandes >= 1: tamanhos_no_pedido.append(f"grandes: {num_grandes}")
        if num_extragrandes >= 1: tamanhos_no_pedido.append(f"extragrandes: {num_extragrandes}")
        if num_ultra >= 1: tamanhos_no_pedido.append(f"ultra: {num_ultra}")

        percentagem_mini = (num_mini / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0
        percentagem_pequenas = (num_pequenas / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0
        #print(f"Percentagem peq: {percentagem_pequenas:.2f}%, calculo: {num_pequenas} / {nr_fieiras_unicas} * 100")
        percentagem_medias = (num_medias / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0
        percentagem_grandes = (num_grandes / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0
        percentagem_extragrandes = (num_extragrandes / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0
        percentagem_ultra = (num_ultra / nr_fieiras_unicas * 100) if nr_fieiras_unicas > 0 else 0

        detalhe_tamanhos = f" | Tamanhos no pedido: {', '.join(tamanhos_no_pedido)}" if tamanhos_no_pedido else ""

        # Print mantido para testes
        #print(f"No pedido {ped} do cliente {cliente} foram trabalhadas {total_fieiras} fieiras, {texto_caixa} {caixas_formatadas}.{aviso_partidas} (Recebidos os diâmetros: {diametros_str}){detalhe_tamanhos}")
        
        # Guardar para o Front-end
        lista_pedidos_front.append({
            'ped': ped,
            'total_fieiras': total_fieiras,
            'cliente': cliente,
            'texto_caixa': texto_caixa,
            'caixas_formatadas': caixas_formatadas,
            'diametros_str': diametros_str,
            'qtd_partidas': qtd_partidas,

            
            'num_mini': num_mini,
            'num_pequenas': num_pequenas,
            'num_medias': num_medias,
            'num_grandes': num_grandes,
            'num_extragrandes': num_extragrandes,
            'num_ultra': num_ultra,

            'percentagem_mini': percentagem_mini,
            'percentagem_pequenas': percentagem_pequenas,
            'percentagem_medias': percentagem_medias,
            'percentagem_grandes': percentagem_grandes,
            'percentagem_extragrandes': percentagem_extragrandes,
            'percentagem_ultra': percentagem_ultra,
        })


    # --- 6. RELATÓRIO POR UTILIZADOR ---
    #print("\n--- RELATORIO POR UTILIZADOR ---")

    resumo_workers_qs = (
        trabalhos_no_periodo
        .values('worker_id', 'worker__username')
        .annotate(
            total_trabalhos=Count('id'),
            total_fieiras=Count('work__die', distinct=True),
        ).order_by('worker__username')
    )

    resumo_diario_qs = (
        trabalhos_no_periodo
        .annotate(dia=TruncDate('added_at')) # Transforma "17/03/2026 14:30" em "17/03/2026"
        .values('dia')                       # Dizemos para agrupar por esse dia
        .annotate(
            total_trabalhos=Count('id'),
            total_fieiras=Count('work__die', distinct=True)
        )
        .order_by('dia') # Ordena do primeiro ao último dia da semana
    )

    # Passamos isto para uma lista limpa para o Front-end
    lista_resumo_diario = list(resumo_diario_qs)

    detalhe_workers_qs = (
        trabalhos_no_periodo
        .values(
            'worker_id', 'worker__username', 'work__die_id', 
            'work__die__serial_number', 'work__work_type', 
            'work__subtype', 'work__die__die__die_type'
        )
        .annotate(total=Count('id'))
        .order_by('worker__username', 'work__die__serial_number', 'work__work_type', 'work__subtype')
    )

    detalhes_por_worker_dict = defaultdict(list)
    for d in detalhe_workers_qs:
        detalhes_por_worker_dict[d['worker_id']].append(d)

    lista_workers_front = [] # <--- LISTA PARA O HTML

    for w in resumo_workers_qs:
        wid = w['worker_id']
        nome = w['worker__username'] or "Desconhecido"
        
        total_retificacoes_worker = 0
        nd_trabalhadas = 0
        pcd_trabalhadas = 0
        mcd_trabalhadas = 0
        
        contagens_operacoes = defaultdict(int)
        lista_detalhes_worker = [] # Lista de trabalhos para o loop interno

        #print(f"\nTrabalhador: {nome}")
        #print(f"  Total de trabalhos: {w['total_trabalhos']}")
        #print(f"  Total de fieiras únicas: {w['total_fieiras']}")

        for d in detalhes_por_worker_dict.get(wid, []):
            tipo = d['work__work_type'] or "N/A"
            subtipo = d['work__subtype'] or "Geral"
            tipo_die = d['work__die__die__die_type'] or "N/A"
            serie = d['work__die__serial_number'] or "N/A"
            retificacoes = max((d['total'] or 0) - 1, 0)
            
            total_retificacoes_worker += retificacoes

            if tipo_die == 'ND': nd_trabalhadas += 1
            if tipo_die == 'PCD': pcd_trabalhadas += 1
            if tipo_die == 'MCD': mcd_trabalhadas += 1

            #print(f"  - Série: {serie} | {tipo} / {subtipo} | Die: {tipo_die} | trabalhos: {d['total']}")

            # Adicionar detalhe à lista do worker para o Front-end
            lista_detalhes_worker.append({
                'serie': serie,
                'tipo': tipo,
                'subtipo': subtipo,
                'tipo_die': tipo_die,
                'total': d['total']
            })

            # Contabilizar operações pelo MAPA
            chave = (tipo, subtipo)
            operacao_label = MAPA_OPERACOES.get(chave, tipo.replace('_', ' ').title())
            contagens_operacoes[operacao_label] += 1

        # Imprimir e preparar operações para o Front-end
        lista_operacoes_front = []
        for operacao, total in contagens_operacoes.items():
            #print(f"  Total {operacao}: {total}")
            lista_operacoes_front.append({
                'operacao': operacao,
                'total': total
            })

        """print(f"Total de retificações: {total_retificacoes_worker}")
        if nd_trabalhadas >= 1: print(f"Total de fieiras ND: {nd_trabalhadas}")
        if pcd_trabalhadas >= 1: print(f"Total de fieiras PCD: {pcd_trabalhadas}")
        if mcd_trabalhadas >= 1: print(f"Total de fieiras MCD: {mcd_trabalhadas}")"""

        # Guardar Worker com tudo lá dentro para o Front-end
        lista_workers_front.append({
            'nome': nome,
            'total_trabalhos': w['total_trabalhos'],
            'total_fieiras': w['total_fieiras'],
            
            'detalhes': lista_detalhes_worker,     # Para o: for trab in worker.detalhes
            'contagens': lista_operacoes_front,    # Para o: for cont in worker.contagens
            
            'total_retificacoes_worker': total_retificacoes_worker,
            'nd_trabalhadas': nd_trabalhadas,
            'pcd_trabalhadas': pcd_trabalhadas,
            'mcd_trabalhadas': mcd_trabalhadas,
        })

    #testes
    
    relatorio_diario = {}

    # Para garantir que os partidos são associados ao dia certo, precisamos 
    # de uma query dos partidos com a data truncada.
    partidos_por_dia_pedido = defaultdict(int)
    for partido in partidos_qs:
        if partido.qr_code:
            # Apanhamos a data da criação do registo de partido
            dia_partido = partido.created_at.date() 
            ped_partido = f"{partido.qr_code.toma_order_nr}/{partido.qr_code.toma_order_year}"
            qtd = partido.partido if partido.partido else 1
            chave = (dia_partido, ped_partido)
            partidos_por_dia_pedido[chave] += qtd

    # Iteramos de novo (ou podes juntar isto ao loop principal se preferires otimizar)
    # Para este exemplo, faço um loop novo para ficar mais claro
    for trabalho in trabalhos_no_periodo:
        dia = trabalho.added_at.date() # Agrupador principal!
        pedido = f"{trabalho.work.die.customer.toma_order_nr}/{trabalho.work.die.customer.toma_order_year}"
        cliente = trabalho.work.die.customer.customer
        box = str(trabalho.work.die.customer.box_nr)
        die_id = trabalho.work.die.id
        tipo_die = trabalho.work.die.die.die_type # Para a contagem de ND/PCD

        # Inicializa o dia no dicionário
        if dia not in relatorio_diario:
            relatorio_diario[dia] = {}
            
        # Inicializa o pedido dentro do dia
        if pedido not in relatorio_diario[dia]:
            relatorio_diario[dia][pedido] = {
                'cliente': cliente,
                'caixas': set(),
                'fieiras_unicas': set(),
                'diametros_raw': {}, # Para contar os tamanhos depois
                'nd': 0,
                'pcd': 0,
                'mcd': 0
            }

        # Adiciona a caixa
        if box and box != 'None':
            relatorio_diario[dia][pedido]['caixas'].add(box)
            
        # Processa fieira única para este dia+pedido
        if die_id not in relatorio_diario[dia][pedido]['fieiras_unicas']:
            relatorio_diario[dia][pedido]['fieiras_unicas'].add(die_id)
            
            # Guarda o diâmetro para contar tamanhos
            diametro = trabalho.work.die.diameter_text
            if diametro not in (None, ''):
                relatorio_diario[dia][pedido]['diametros_raw'][die_id] = str(diametro)
                
            # Conta ND / PCD / MCD
            if tipo_die == 'ND': relatorio_diario[dia][pedido]['nd'] += 1
            elif tipo_die == 'PCD': relatorio_diario[dia][pedido]['pcd'] += 1
            elif tipo_die == 'MCD': relatorio_diario[dia][pedido]['mcd'] += 1

    # Processamento final para a lista que vai para o Front-end
    lista_relatorio_diario = []

    # Totais da Semana inteira
    totais_semana = {
        'pieces': 0, 'broken': 0, 'mini': 0, 'pequenas': 0, 'medias': 0,
        'grandes': 0, 'extragrandes': 0, 'ultra': 0, 'nd': 0, 'pcd': 0, 'mcd': 0
    }

    # Ordenamos os dias cronologicamente
    for dia in sorted(relatorio_diario.keys()):
        pedidos_do_dia = []
        
        # Totais específicos deste dia
        totais_dia = {
            'pieces': 0, 'broken': 0, 'mini': 0, 'pequenas': 0, 'medias': 0,
            'grandes': 0, 'extragrandes': 0, 'ultra': 0, 'nd': 0, 'pcd': 0, 'mcd': 0
        }

        for ped, info in relatorio_diario[dia].items():
            total_fieiras = len(info['fieiras_unicas'])
            caixas_str = ", ".join(sorted(info['caixas']))
            
            # Partidas desse dia para esse pedido
            qtd_partidas = partidos_por_dia_pedido.get((dia, ped), 0)
            
            # Lógica de tamanhos (igual ao que já tens)
            num_mini = num_pequenas = num_medias = num_grandes = num_extragrandes = num_ultra = 0
            for diam in info['diametros_raw'].values():
                try: diam_val = float(str(diam).strip().replace(',', '.'))
                except: continue
                if 0.100 <= diam_val <= 0.399: num_mini += 1
                elif 0.400 <= diam_val <= 0.799: num_pequenas += 1
                elif 0.800 <= diam_val <= 1.499: num_medias += 1
                elif 1.500 <= diam_val <= 2.499: num_grandes += 1
                elif 2.500 <= diam_val <= 3.999: num_extragrandes += 1
                elif 4.000 <= diam_val <= 8.000: num_ultra += 1

            # Construir o objeto do pedido
            pedido_processado = {
                'pedido': ped,
                'cliente': info['cliente'],
                'caixas': caixas_str,
                'total_fieiras': total_fieiras,
                'partidas': qtd_partidas,
                'mini': num_mini, 'pequenas': num_pequenas, 'medias': num_medias,
                'grandes': num_grandes, 'extragrandes': num_extragrandes, 'ultra': num_ultra,
                'nd': info['nd'], 'pcd': info['pcd'], 'mcd': info['mcd']
            }
            pedidos_do_dia.append(pedido_processado)

            # Somar aos totais do dia
            totais_dia['pieces'] += total_fieiras
            totais_dia['broken'] += qtd_partidas
            totais_dia['mini'] += num_mini
            totais_dia['pequenas'] += num_pequenas
            totais_dia['medias'] += num_medias
            totais_dia['grandes'] += num_grandes
            totais_dia['extragrandes'] += num_extragrandes
            totais_dia['ultra'] += num_ultra
            totais_dia['nd'] += info['nd']
            totais_dia['pcd'] += info['pcd']
            totais_dia['mcd'] += info['mcd']

        # Adicionar totais da semana
        for k in totais_semana.keys():
            totais_semana[k] += totais_dia[k]

        # Guarda o pacote do dia inteiro na lista final
        lista_relatorio_diario.append({
            'data': dia,
            'pedidos': pedidos_do_dia,
            'totais_dia': totais_dia,
            'rowspan': len(pedidos_do_dia) # Necessário para o HTML agrupar o bloco "Day"
        })

    # --- 7. ENVIO PARA O TEMPLATE ---
    context = {
        # Totais
        'nr_trabalhos': nr_trabalhos,
        'nr_fieiras_unicas': nr_fieiras_unicas,
        'total_partidos': total_partidos,
        'percentage_partidas': percentage_partidas,

        # Listas de Dicionários 
        'tipos_fieira': lista_tipos_front,
        'resumo_pedidos': lista_pedidos_front,
        'resumo_workers': lista_workers_front,
        'tamanhos_no_pedido': tamanhos_no_pedido,
        'resumo_diario': lista_resumo_diario,
        'relatorio_diario': lista_relatorio_diario,
        'totais_semana': totais_semana
    }

    if request.headers.get('HX-Request'):

            # Devolve APENAS o pedacinho de HTML com a tabela preenchida
            return render(request, 'theme/partials/tabela_relatorio.html', context)
        
        # Se foi um carregamento normal da página (F5 ou escrever o link)
    return render(request, 'theme/relatorio_data.html', context)

    
# adicionar outro charts mas agora para producao semanal e compare com a semana anterior
# link: https://flowbite.com/docs/plugins/charts/#column-chart || https://apexcharts.com/javascript-chart-demos/column-charts/stacked/