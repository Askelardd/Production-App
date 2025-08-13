import json  # type: ignore
import logging  # type: ignore
from django.http import JsonResponse  # type: ignore
from django.shortcuts import get_object_or_404, redirect, render  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.auth.models import User  # type: ignore
from django.contrib.auth import authenticate, login  # type: ignore
from django.contrib.auth.decorators import login_required  # type: ignore
from django.views.decorators.http import require_http_methods  # type: ignore
from django.views.decorators.csrf import csrf_exempt  # type: ignore
from django.utils import timezone  # type: ignore
from .models import *  # type: ignore
import re  # type: ignore
import pandas as pd  # type: ignore
from django.http import HttpResponse  # type: ignore
from django.db.models import Count  # type: ignore

def home(request):
    users = User.objects.all()
    return render(request, 'theme/home.html', {'users': users})

def qOfficeMenu(request):
    return render(request, 'theme/qOfficeMenu.html')

def productionMenu(request):
    return render(request, 'theme/productionMenu.html')

def comercialMenu(request):
    return render(request, 'theme/comercialMenu.html')


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
            login(request, user)  # faz o login
            globalLogs.objects.create(
                user=request.user,
                action=f"{request.user.first_name or request.user.username} fez login no sistema."
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

        try:
            partido = int(numero)
            if partido <= 0:
                messages.error(request, 'O número do partido deve ser um número positivo.')
            else:
                NumeroPartidos.objects.create(
                    qr_code=qr_code,
                    partido=partido,
                    serie_dies_partidos=serie_dies_partidos
                )
                messages.success(request, f'Partido {partido} adicionado com sucesso!')
                globalLogs.objects.create(
                    user=request.user,
                    action=f"{request.user.first_name or request.user.username} adicionou o partido {partido} ao QR Code {qr_code.toma_order_full}.",
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
                    serie_dies=serie_dies
                )
                messages.success(request, f'Pedido de diâmetro {diametro} para {numero} fieiras adicionado com sucesso!')
                globalLogs.objects.create(
                    user=request.user,
                    action=f"{request.user.first_name or request.user.username} adicionou um pedido de diâmetro {diametro} para {numero} fieiras no QR Code {qr_code.toma_order_full}.",
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

    matches = re.findall(r"(\d+)\s*x\s*([\d,\.]+)", qr_code.diameters)

    diameters_list = []
    for qty, value in matches:
        qty = int(qty)
        value = value.replace(",", ".")
        diameters_list.extend([value] * qty)

    # Garantir que não ultrapasse qt
    diameters_list = diameters_list[:qr_code.qt]

    while len(diameters_list) < qr_code.qt:
        diameters_list.append("")

    existing_dies = list(dieInstance.objects.filter(customer=qr_code).order_by('id'))

    if request.method == 'POST':
        total = int(request.POST.get('total', 0))

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

            if i <= len(existing_dies):
                # Atualizar existente
                die_obj = existing_dies[i-1]
                die_obj.serial_number = serial
                die_obj.diameter_text = diameter_value
                die_obj.diam_desbastado = diam_desbastado or None
                die_obj.diam_requerido = diam_requerido or None
                die_obj.die_id = die_id if die_id else None
                die_obj.job_id = job_id if job_id else None
                die_obj.observations = observations
                die_obj.cone = cone
                die_obj.bearing = bearing


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
                    bearing=bearing
                    
                )

        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.first_name or request.user.username} adicionou/atualizou dies para o QR Code {qr_code.toma_order_nr}.",
        )


        messages.success(request, f"Dies atualizados para {qr_code.customer} com sucesso!")
        return redirect('listQrcodes')

    # Prepara os dados para exibição (pré-preenchimento)
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
                'bearing': die.bearing
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
                'bearing': ''
            })

                # Adiciona log na tabela globalLogs
    return render(request, 'theme/adicionarDies.html', {
        'qr_code': qr_code,
        'dies': dies,
        'jobs': jobs,
        'prefilled_data': prefilled_data,
    })

def listar_qrcodes_com_dies(request):
    qrcodes = QRData.objects.prefetch_related('die_instances').all().order_by('-created_at')
    return render(request, 'theme/listarDies.html', {'qrcodes': qrcodes})


def create_caixa(request):
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
            action=f"{request.user.first_name or request.user.username} criou uma nova caixa com o número {box_nr}.",
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
            action=f"{request.user.first_name or request.user.username} atualizou/adicionou os diâmetros do Die {die.serial_number} para {diametro_min} - {diametro_max}.",
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
            subtype=subtipo)

        messages.success(request, f"Trabalho '{tipo_trabalho}' adicionado com sucesso ao Die {die.serial_number}.")
                    # Adiciona log na tabela globalLogs
        globalLogs.objects.create(
            user=request.user,
            action=f"{request.user.first_name or request.user.username} criou um trabalho '{tipo_trabalho}' para o Die {die.serial_number}.",
        )
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
        action=f"{request.user.first_name or request.user.username} criou um exel da ordem {qr.toma_order_nr}",
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
                action=f"{request.user.first_name or request.user.username} enviou a caixa {qr.toma_order_nr} para {box_location.get_where_display()}",
            )

            return redirect('listarDies')
        else:
            messages.error(request, "Opção inválida.")

    return render(request, 'theme/enviar_caixa.html', {'qr': qr, 'choices': whereBox.ONDESTA})

def contar_dies_por_usuario(qr_id, user_id):
    from theme.models import DieWorkWorker

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