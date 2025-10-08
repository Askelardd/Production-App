import calendar
import datetime
import json  # type: ignore
import logging
import re  # type: ignore
from collections import Counter
from datetime import date, timedelta
from unicodedata import name
from urllib import request  # type: ignore
from django.db.models import Q, OuterRef, Exists
import pandas as pd  # type: ignore
from django.conf import settings
from django.contrib import messages  # type: ignore
from django.contrib.auth import authenticate, login, logout  # type: ignore
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required  # type: ignore
from django.contrib.auth.models import User  # type: ignore
from django.core.mail import send_mail  # type: ignore
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction  # type: ignore
from django.db.models import Count  # type: ignore
from django.http import HttpResponse, JsonResponse  # type: ignore
from django.shortcuts import get_object_or_404, redirect, render  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt  # type: ignore
from django.views.decorators.http import require_http_methods, require_POST  # type: ignore

from .models import *  # type: ignore



def home(request):
    users = User.objects.all()
    return render(request, 'theme/home.html', {'users': users})

def qOfficeMenu(request):
    return render(request, 'theme/qOfficeMenu.html')

def productionMenu(request):
    return render(request, 'theme/productionMenu.html')

def comercialMenu(request):
    return render(request, 'theme/comercialMenu.html')

def permission_denied_view(request, exception=None):
    return render(request, '403.html', status=403)

def orders(request):
    if not request.user.groups.filter(name__in=['Administracao', 'Comercial']).exists():
        return permission_denied_view(request)
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

        send_mail(
            subject=f"Novo pedido criado: {order.tracking_number} de {order.plant}",
            message=(f"Um novo pedido foi criado com o número de rastreamento: {order.tracking_number}\n"
                     f"Plant: {order.plant}, shipping date: {order.shipping_date}\n"),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.DEFAULT_REPLY_TO_EMAIL if isinstance(settings.DEFAULT_REPLY_TO_EMAIL, list) else [settings.DEFAULT_REPLY_TO_EMAIL],  # lista de emails
        )

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
def create_orders_coming_ajax(request):
    if not request.user.groups.filter(name__in=['Administracao', 'Comercial']).exists():
        return permission_denied_view(request)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            oc = OrdersComing.objects.create(
                order=data.get('order'),
                urgent=data.get('urgent', False),
                comment=data.get('comment', ''),
            )
            return JsonResponse({
                'success': True,
                'data': {
                    'id': oc.id,
                    'order': oc.order,
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método inválido'})

def listar_orders(request):
    if not request.user.groups.filter(name__in=['Administracao', 'Comercial','Q-Office']).exists():
        return permission_denied_view(request)

    orders = (
        Order.objects
        .prefetch_related('orders_coming', 'files')
        .annotate(
            has_tasks=Exists(
                OrdersComing.objects
                .filter(orders=OuterRef('pk'))  
                .filter(
                    Q(inspectionMetrology=True) |
                    Q(preshipment=True) |
                    Q(mark=True) |
                    Q(urgent=True)
                )
            )
        )
        .order_by('-shipping_date', '-id')
    )

    ordersComing = OrdersComing.objects.all()

    is_admin = request.user.groups.filter(name__in=["Administracao", "Comercial"]).exists()
    is_qOffice = request.user.groups.filter(name='Q-Office').exists()

    return render(request, 'theme/listarOrders.html', {
        'orders': orders,
        'is_admin': is_admin,
        'ordersComing': ordersComing,
        'is_qOffice': is_qOffice,
    })


def edit_order(request, order_id):
    if not request.user.groups.filter(name__in=['Administracao', 'Comercial']).exists():
        messages.error(request, "Não tem permissão para editar esta ordem.")
        return redirect('listarOrders')

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
def delete_order(request, order_id):
    if not request.user.groups.filter(name__in=['Administracao']).exists():
        messages.error(request, "Não tem permissão para eliminar esta ordem.")
        return redirect('listarOrders')

    order = get_object_or_404(Order, id=order_id)
    order.delete()

    globalLogs.objects.create(
        user=request.user,
        action=f"{request.user.username} eliminou o pedido {order.tracking_number}.",
    )
    messages.success(request, "Pedido eliminado com sucesso!")
    return redirect('listarOrders')

@require_POST
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
def edit_orders_coming(request, oc_id):
    orders_coming = get_object_or_404(OrdersComing, id=oc_id)

    if request.method == 'POST':
        orders_coming.order = request.POST.get('order')
        orders_coming.inspectionMetrology = request.POST.get('inspectionMetrology') == 'on'
        orders_coming.preshipment = request.POST.get('preshipment') == 'on'
        orders_coming.mark = request.POST.get('mark') == 'on'
        orders_coming.urgent = request.POST.get('urgent') == 'on'
        orders_coming.done = request.POST.get('done') == 'on' 
        if orders_coming.done and not orders_coming.data_done:
            orders_coming.data_done = timezone.now()
        orders_coming.comment = request.POST.get('comment', '')
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
            'Inspection Metrology': 'Sim' if oc.inspectionMetrology else '-',
            'Preshipment': 'Sim' if oc.preshipment else '-',
            'Mark': 'Sim' if oc.mark else '-',
            'Urgent': 'Sim' if oc.urgent else '-',
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

def administrationMenu(request):
    is_admin = request.user.groups.filter(name='Administracao').exists()
    return render(request, 'theme/administrationMenu.html', {'is_admin': is_admin})


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



@require_http_methods(["GET", "POST"])
def deliveryIdentification(request, toma_order_full):
    
    if not request.user.groups.filter(name__in=['Administracao', 'Comercial']).exists():
        return permission_denied_view(request)
    
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
def mainMenu(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Utilizador não encontrado.')
        return redirect('home')
    
    # Verifica se o utilizador logado está a tentar ver outro perfil
    if request.user.id != user.id:
        messages.error(request, 'Acesso negado.')
        return redirect('home')

    return render(request, 'theme/mainMenu.html', {'user': user})


@csrf_exempt
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
            login(request, user)
            globalLogs.objects.create(
                user=request.user,  # já autenticado
                action=f"{request.user.get_username()} fez login no sistema."
            )
            return redirect('mainMenu', user_id=user.id)
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


def listarInfo(request):
    deliveries = DeliveryInfo.objects.all()
    return render(request, 'theme/listarInfo.html', {'deliveries': deliveries})

def deletar_delivery(request, id):
    delivery = get_object_or_404(DeliveryInfo, id=id)

    if request.method == 'POST':
        delivery.delete()
        messages.success(request, 'Entrega deletada com sucesso!')
        return redirect('listarInfo')

    messages.error(request, 'Requisição inválida.')
    return redirect('listarInfo')


def listarInfo(request):
    deliveries = DeliveryInfo.objects.all()
    return render(request, 'theme/listarInfo.html', {'deliveries': deliveries})

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

@require_http_methods(["GET", "POST"])
@csrf_exempt
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

@csrf_exempt
def partidosMenu(request, toma_order_full):
    qr_code = get_object_or_404(QRData, toma_order_full=toma_order_full)
    dies_existentes = dieInstance.objects.filter(customer=qr_code).order_by('-created_at')

    if request.method == 'POST':
        numero = request.POST.get('numeroPartidos')
        serie_dies_list = request.POST.getlist('serieDies')  # <-- recebe checkboxes
        serie_dies_partidos = ', '.join(serie_dies_list)     # <-- transforma em string
        observations = request.POST.get('observations', '')
        observations = request.POST.get('observations', '')

        try:
            partido = int(numero)
            if partido <= 0:
                messages.error(request, 'O número do partido deve ser um número positivo.')
            else:
                NumeroPartidos.objects.create(
                    qr_code=qr_code,
                    partido=partido,
                    serie_dies_partidos=serie_dies_partidos,
                    observations=observations
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
def diametroMenu(request, toma_order_full):
    try:
        qr_code = QRData.objects.get(toma_order_full=toma_order_full)
    except QRData.DoesNotExist:
        messages.error(request, 'QR Code não encontrado.')
        return redirect('listarDies')

    dies_existentes = dieInstance.objects.filter(customer=qr_code).order_by('-created_at')  # <- os dies deste QR

    if request.method == 'POST':
        numero = request.POST.get('numeroAlterar')
        diametro = request.POST.get('diametroNovo')
        pedido_por = request.POST.get('pedidoPor')
        serie_dies_list = request.POST.getlist('serieDies')  # <-- recebe os checkboxes
        serie_dies = ', '.join(serie_dies_list)
        observations = request.POST.get('observations', '')
        observations = request.POST.get('observations', '')

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
                    numero_fieiras=numero,
                    pedido_por=pedido_por,
                    serie_dies=serie_dies,
                    observations=observations
                )
                messages.success(request, f'Pedido de diâmetro {diametro} para {numero} fieiras adicionado com sucesso!')
                globalLogs.objects.create(
                    user=request.user,
                    action=f"{request.user.username} adicionou um pedido de diâmetro {diametro} para {numero} fieiras no QR Code {qr_code.toma_order_full}.",
                )
                
                send_mail(
                    subject="Novo Pedido de Diâmetro",
                    message=(
                        f"Novo pedido de diâmetro criado:\n"
                        f"Pedido criado por {request.user.username}\n"
                        f"- QR Code: {qr_code.toma_order_full}\n"
                        f"- Cliente: {qr_code.customer}\n"
                        f"- Diâmetro: {diametro}\n"
                        f"- Nº de fieiras: {numero}\n"
                        f"- Pedido por: {pedido_por or '-'}\n"
                        f"- Série de dies: {serie_dies or '-'}\n"
                        f"- Observações: {observations or '-'}"
                    ),
                    from_email=None,               # usa DEFAULT_FROM_EMAIL
                    recipient_list=settings.DEFAULT_BCC_EMAIL if isinstance(settings.DEFAULT_BCC_EMAIL, list) else [settings.DEFAULT_BCC_EMAIL],  # lista de emails
                    fail_silently=False,
                )

        except ValueError:
            messages.error(request, 'Número de fieiras inválido. Por favor, insira um número válido.')
        except Exception as e:
            messages.error(request, f'Erro ao adicionar pedido: {str(e)}')

    return render(request, 'theme/diametroMenu.html', {
        'qr_code': qr_code,
        'dies_existentes': dies_existentes
    })

@csrf_exempt
def showDetails(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)

    # Todos os Dies deste QR Code
    dies = qr.die_instances.all()
    die_ids = dies.values_list('id', flat=True)

    # Para cada die, pega todos os workers que fizeram pelo menos 1 trabalho nesse die
    die_workers = {}
    for die in dies:
        workers = (
            DieWorkWorker.objects
            .filter(work__die=die)
            .values_list('worker_id', 'worker__first_name', 'worker__last_name', 'worker__username')
            .distinct()
        )
        for worker_id, first_name, last_name, username in workers:
            if worker_id not in die_workers:
                die_workers[worker_id] = {
                    'name': f"{first_name} {last_name}",
                    'username': username,
                    'dies_worked': set()
                }
            die_workers[worker_id]['dies_worked'].add(die.id)

    # Agora, para cada worker, conta em quantos dies ele trabalhou (pelo menos 1 trabalho em cada die)
    workers_stats_list = []
    for worker in die_workers.values():
        total_dies = len(worker['dies_worked'])
        if total_dies > 0:
            workers_stats_list.append({
                'name': worker['name'],
                'username': worker['username'],
                'total_dies': total_dies
            })

    # Ordena por total_dies decrescente
    workers_stats_list = sorted(workers_stats_list, key=lambda x: x['total_dies'], reverse=True)

    return render(request, 'theme/showDetails.html', {
        'qr': qr,
        'dies': dies,
        'workers_stats': workers_stats_list
    })


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
                    'diam_desbastado': request.POST.get(f'diam_desbastado_{i}', ''),
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
                    diam_desbastado = request.POST.get(f'diam_desbastado_{i}')
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
                        die_obj.diam_desbastado = diam_desbastado or None
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
                            diam_desbastado=diam_desbastado or None,
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
                'diam_desbastado': die.diam_desbastado,
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
                'diam_desbastado': '',
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

def listar_qrcodes_com_dies(request):
    qrcodes = QRData.objects.prefetch_related('die_instances').all().order_by('-created_at')
    return render(request, 'theme/listarDies.html', {'qrcodes': qrcodes})

@login_required
def create_caixa(request):
    if not request.user.groups.filter(name__in=['Q-Office', 'Administracao']).exists():
        messages.error(request, "Não tens permissão para criar caixas.")
        return redirect('listarDies')
    
    if request.method == 'POST':
        required_fields = ['customer', 'customer_order_nr', 'toma_order_nr', 'toma_order_year', 'box_nr', 'qt', 'diameters']

        # Verifica se há campos obrigatórios vazios
        for field in required_fields:
            if not request.POST.get(field):
                messages.error(request, f"Todos os campos obrigatórios devem ser preenchidos.")
                return redirect('listarDies')

        try:
            box_nr = int(request.POST.get('box_nr'))
            qt = int(request.POST.get('qt'))
        except ValueError:
            messages.error(request, "Os campos 'Caixa' e 'Quantidade' devem ser números válidos.")
            return redirect('listarDies')

        # Cria o objeto se tudo estiver válido
        QRData.objects.create(
            customer=request.POST.get('customer'),
            customer_order_nr=request.POST.get('customer_order_nr'),
            toma_order_nr=request.POST.get('toma_order_nr'),
            toma_order_year=request.POST.get('toma_order_year', timezone.now().year),
            box_nr=box_nr,
            qt=qt,
            diameters=request.POST.get('diameters'),
            observations=request.POST.get('observations', ''),
            created_at=timezone.now()
        )

        messages.success(request, "Caixa criada com sucesso!")

        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.username} criou uma nova caixa com o número {box_nr}.",
        )

        return redirect('listarDies')

    return redirect('listarDies')

def listar_qrcodes_com_dies(request):
    qrcodes = QRData.objects.prefetch_related('die_instances').all().order_by('-created_at')
    return render(request, 'theme/listarDies.html', {'qrcodes': qrcodes})

@login_required
def create_caixa(request):
    if not request.user.groups.filter(name__in=['Q-Office', 'Administracao']).exists():
        messages.error(request, "Não tens permissão para criar caixas.")
        return redirect('listarDies')
    
    if request.method == 'POST':
        required_fields = ['customer', 'customer_order_nr', 'toma_order_nr', 'toma_order_year', 'box_nr', 'qt', 'diameters']

        # Verifica se há campos obrigatórios vazios
        for field in required_fields:
            if not request.POST.get(field):
                messages.error(request, f"Todos os campos obrigatórios devem ser preenchidos.")
                return redirect('listarDies')

        try:
            box_nr = int(request.POST.get('box_nr'))
            qt = int(request.POST.get('qt'))
        except ValueError:
            messages.error(request, "Os campos 'Caixa' e 'Quantidade' devem ser números válidos.")
            return redirect('listarDies')

        # Cria o objeto se tudo estiver válido
        QRData.objects.create(
            customer=request.POST.get('customer'),
            customer_order_nr=request.POST.get('customer_order_nr'),
            toma_order_nr=request.POST.get('toma_order_nr'),
            toma_order_year=request.POST.get('toma_order_year', timezone.now().year),
            box_nr=box_nr,
            qt=qt,
            diameters=request.POST.get('diameters'),
            observations=request.POST.get('observations', ''),
            created_at=timezone.now()
        )

        messages.success(request, "Caixa criada com sucesso!")

        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.username} criou uma nova caixa com o número {box_nr}.",
        )

        return redirect('listarDies')

    return redirect('listarDies')


def die_details(request, die_id):
    die = get_object_or_404(dieInstance, id=die_id)
    works = die.works.prefetch_related('workers__worker')

    if request.method == "POST" and request.POST.get("action") == "update_diametros":
        diametro_min = request.POST.get('diametro_min')
        diametro_max = request.POST.get('diametro_max')

        try:
            diametro_min = Decimal(diametro_min)
            diametro_max = Decimal(diametro_max)
        except (InvalidOperation, TypeError):
            messages.error(request, "Valores inválidos para diâmetros.")
            return redirect('die_details', die_id=die.id)

        if diametro_min > diametro_max:
            messages.error(request, "O diâmetro mínimo não pode ser maior que o máximo.")
            return redirect('die_details', die_id=die.id)

        if die.diam_max_min:
            die.diam_max_min.min = diametro_min
            die.diam_max_min.max = diametro_max
            die.diam_max_min.save()
        else:
            new_diam = Diameters.objects.create(min=diametro_min, max=diametro_max)
            die.diam_max_min = new_diam
            die.save()
        
        # Atualiza o texto do observations
        # Pega observações preenchidas pelo cliente
        observations = request.POST.get('observations', '').strip()
        die.observations = observations
        die.save()

        messages.success(request, "Diâmetros atualizados com sucesso!")
                    # Adiciona log na tabela globalLogs
        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.username} atualizou/adicionou os diâmetros do Die {die.serial_number} para {diametro_min} - {diametro_max}.",
        )
        return redirect('die_details', die_id=die.id)

    return render(request, 'theme/die_details.html', {'die': die, 'works': works})

def create_die_work(request, die_id):
    die = get_object_or_404(dieInstance, id=die_id)

    if request.method == 'POST':
        tipo_trabalho = request.POST.get('tipo_trabalho')
        subtipo = request.POST.get('subtipo')

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

        # Verifica se o usuário quer adicionar outro trabalho
        if 'add_another' in request.POST:
            return redirect('create_die_work', die_id=die.id)


        return redirect('die_details', die_id=die.id)

    return render(request, 'theme/create_die_work.html', {'die': die})

def add_worker_to_die_work(request, work_id):
    work = get_object_or_404(DieWork, id=work_id)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('worker')
        password = request.POST.get('password')

        if not user_id or not password:
            messages.error(request, "Selecione um utilizador e insira a senha.")
            return redirect(request.path)

        user = get_object_or_404(User, id=user_id)

        # Verificar senha do utilizador selecionado
        auth_user = authenticate(username=user.username, password=password)
        if auth_user is None:
            messages.error(request, "Senha incorreta para o utilizador selecionado!")
            return redirect(request.path)

        # Adicionar trabalhador ao trabalho
        DieWorkWorker.objects.create(work=work, worker=user)
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
            "Original Ø": die.diam_desbastado or "",
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

def enviar_fieira(request, die_id):
    die = get_object_or_404(dieInstance, id=die_id)
    
    # Obter a localização atual
    try:
        current_location = WhereDie.objects.get(die=die)
    except WhereDie.DoesNotExist:
        current_location = None
    
    if request.method == 'POST':
        destino = request.POST.get('where')
        if destino in dict(WhereDie.ONDESTA):
            # Usar get_or_create para garantir que existe um registro
            location, created = WhereDie.objects.get_or_create(die=die)
            location.where = destino
            location.save()
            
            # Criar log da ação
            globalLogs.objects.create(
                user=request.user,
                action=f"{request.user} enviou a fieira {die.serial_number} para {location.get_where_display()}",
            )
            
            messages.success(request, f"Fieira {die.serial_number} enviada para {location.get_where_display()}.")
            return redirect('listarDies')
        else:
            messages.error(request, "Destino inválido.")
    
    return render(request, 'theme/enviar_fieira.html', {
        'die': die,
        'current_location': current_location,
        'choices': WhereDie.ONDESTA
    })

def enviar_caixa(request, qr_id):
    qr = get_object_or_404(QRData, id=qr_id)

    if request.method == 'POST':
        destino = request.POST.get('where')
        if destino in dict(whereBox.ONDESTA):
            # Atualiza ou cria a localização da caixa
            box_location, created = whereBox.objects.get_or_create(order_number=qr)
            box_location.where = destino
            box_location.save()

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

def contar_dies_por_usuario(qr_id, user_id):

    count = DieWorkWorker.objects.filter(
        die_work__die__customer_id=qr_id, 
        worker_id=user_id
    ).aggregate(total=Count('id'))['total']

    return count

def listarPedidosDiametro(request):
    pedidos = PedidosDiametro.objects.all().order_by('-created_at')
    return render(request, 'theme/listarPedidosDiametro.html', {'pedidos': pedidos})

def listarPartidos(request):
    numero_partidos = NumeroPartidos.objects.all().order_by('-created_at')
    return render(request, 'theme/listarPartidos.html', {'numero_partidos': numero_partidos})

def localizarFieira(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        results = (
            dieInstance.objects
            .select_related('customer')          # QRData (box_nr, toma_order_full, customer)
            .select_related()                    # no-op; apenas para clareza
            .filter(serial_number__icontains=q)  # troca para __iexact se quiseres busca exata
            .order_by('serial_number')[:100]
        )

        # opcional: se quiser trazer "onde está" (WhereDie) sem consultas extras:
        # o reverse OneToOne de WhereDie é "wheredie" (nome automático)
        # não dá para select_related no reverse sem nomear, então usamos uma mini cache:
        # results = results.select_related('customer')  # já está
        # depois no template, usa die.wheredie.where (se existir)

    return render(request, 'theme/localizarFieira.html', {
        'q': q,
        'results': results,
    })

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


def create_tracking(request, pk=None):
    tracking = get_object_or_404(Tracking, pk=pk) if pk else None

    if request.method == 'POST':
        # 1) ler campos
        data             = parse_date(request.POST.get('data') or '')
        finalidade       = (request.POST.get('finalidade') or '').strip()   # "Importacao" | "Exportacao"
        crm              = request.POST.get('crm') or ''
        transportadora   = request.POST.get('transportadora') or ''
        carta_de_porte   = request.POST.get('carta_de_porte') or None
        numero_recolha   = request.POST.get('numero_recolha') or None
        recebido_por     = request.POST.get('recebido_por') or None
        data_entrega     = parse_date(request.POST.get('data_entrega') or '') if request.POST.get('data_entrega') else None
        cliente          = request.POST.get('cliente') or None
        email            = request.POST.get('email') or None
        observacoes      = request.POST.get('observacoes') or None


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

        return redirect('listarTracking')

    # GET – render do form (mesmo template para add/edit)
    context = {
        'tracking': tracking,
        'finalidades': Tracking._meta.get_field('finalidade').choices,
        'transportadoras': Tracking.courier_choices,
    }
    return render(request, 'theme/adicionarTracking.html', context)



def listar_trackings(request):
    qs = Tracking.objects.all().prefetch_related('files')

    # filtros
    q                = (request.GET.get('q') or '').strip()
    finalidade       = request.GET.get('finalidade') or ''
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
        ('observacoes', 'Observações'),
    ]

    context = {
        'trackings': page_obj.object_list,
        'page_obj': page_obj,
        'current_query': current_query,
        'sort': sort,
        'q': q,
        'selected_finalidade': finalidade,
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

def edit_tracking(request, tracking_id):
    tracking = get_object_or_404(Tracking.objects.prefetch_related('files'), id=tracking_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # campos base
                tracking.data = parse_date(request.POST.get('data') or '')
                tracking.finalidade = (request.POST.get('finalidade') or '').strip()  # "Importacao" | "Exportacao"
                tracking.crm = request.POST.get('crm') or ''
                tracking.transportadora = request.POST.get('transportadora') or None
                tracking.carta_de_porte = request.POST.get('carta_de_porte') or ''
                tracking.numero_recolha = request.POST.get('numero_recolha') or ''
                tracking.recebido_por = request.POST.get('recebido_por') or ''
                tracking.data_entrega = parse_date(request.POST.get('data_entrega') or '')
                tracking.email = request.POST.get('email') or None
                tracking.observacoes = request.POST.get('observacoes') or ''
                tracking.cliente = request.POST.get('cliente') or ''

                # anexar novos ficheiros (não remove os antigos aqui)
                for f in request.FILES.getlist('files'):
                    tf = TrackingFile.objects.create(file=f)
                    tracking.files.add(tf)

                tracking.save()

                # remoção de anexos marcados
                delete_ids = request.POST.getlist('delete_files')  # checkboxes
                if delete_ids:
                    to_remove = TrackingFile.objects.filter(id__in=delete_ids)
                    removed, deleted = 0, 0
                    for tf in to_remove:
                        tracking.files.remove(tf)
                        removed += 1
                        if not tf.trackings.exists():
                            tf.file.delete(save=False)
                            tf.delete()
                            deleted += 1
                    if removed:
                        messages.info(
                            request,
                            f'Removidos {removed} anexo(s). ' +
                            (f'Eliminados do servidor: {deleted}.' if deleted else '')
                        )

            messages.success(request, 'Tracking atualizado com sucesso!')
            return redirect('listarTracking')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar tracking: {e}')

    return render(request, 'theme/adicionarTracking.html', {
        'tracking': tracking,
        'finalidades': Tracking._meta.get_field('finalidade').choices,
        'transportadoras': Tracking.courier_choices,
    })
