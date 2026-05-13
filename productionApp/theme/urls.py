from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, register_converter
from .converters import HashIdConverter # Importa o ficheiro que criaste

register_converter(HashIdConverter, 'hashid')

urlpatterns = [
    # Authentication
    path('', views.home, name='home'),
    path('create-user/', views.create_user, name='create_user'),
    path('login/<hashid:user_id>/', views.login_view, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('erro403/', views.erro403, name='erro403'),

    # Menu
    path('mainMenu/', views.mainMenu, name='mainMenu'),
    path('qOfficeMenu/', views.qOfficeMenu, name='qOfficeMenu'),
    path('productionMenu/', views.productionMenu, name='productionMenu'),
    path('comercialMenu/', views.comercialMenu, name='comercialMenu'),
    path('administrationMenu/', views.administrationMenu, name='administrationMenu'),
    path('menuFinanceiro/', views.financeiroMenu, name='financeiroMenu'),
    path('documentosMenu/', views.documentosMenu, name='documentosMenu'),

    # Products
    path('inputProduction/', views.inputProduction, name='inputProduction'),
    path('editProduct/<hashid:produto_id>/', views.editProduct, name='editProduct'),
    path('delectProduct/<hashid:produto_id>/', views.deleteProduct, name='delectProduct'),

    # QR Codes
    path('listQrcodes/', views.listQrcodes, name='listQrcodes'),
    path('edit-qr-inline/<hashid:qr_id>/', views.edit_qr_inline, name='edit_qr_inline'),
    path('qrdata/detalhes/<hashid:qr_id>/', views.showDetails, name='showDetails'),
    path('qrcode/<hashid:qr_id>/dies/', views.adicionar_dies, name='adicionar_dies'),
    path('qrcode/<hashid:qr_id>/export-excel/', views.export_qrcode_excel, name='export_qrcode_excel'),
    path('die/<hashid:qr_id>/observacoesProd/', views.observacoes_caixa, name='observacoes_caixa'),
    path('listarQrcodes/ClonarLinha/<hashid:qr_id>/', views.clonar_linha, name='clonar_linha'),
    path('die/inspecao-inicial/<str:toma_order_full>/', views.inspecao_inicial, name='inspecao_inicial'),

    # Dies
    path('dies/', views.listar_qrcodes_geral, name='listarDies'),
    path('die/<hashid:die_id>/', views.die_details, name='die_details'),
    path('die/<hashid:die_id>/novo-trabalho/', views.create_die_work, name='create_die_work'),
    path('die-work/<hashid:work_id>/add-worker/', views.add_worker_to_die_work, name='add_worker_to_die_work'),
    path('die/work/workers/<hashid:qr_id>/', views.add_multiple_works_workers, name='add_multiple_works_workers'),
    path('infoFieira/<hashid:die_id>/', views.info_fieira, name='infoFieira'),
    path('enviar-fieira/<hashid:die_id>/', views.enviar_fieira, name='enviar_fieira'),
    path('localizarFieira/', views.localizarFieira, name='localizarFieira'),

    # Orders
    path('orders/', views.orders, name='orders'),
    path('orders/listar/', views.listar_orders, name='listarOrders'),
    path('orders/<hashid:order_id>/edit/', views.edit_order, name='editOrder'),
    path('orders/<hashid:order_id>/delete/', views.delete_order, name='deleteOrder'),
    path('orders/file/<hashid:file_id>/delete/', views.delete_order_file, name='deleteOrderFile'),
    path('orders/create_orders_coming_ajax/', views.create_orders_coming_ajax, name='create_orders_coming_ajax'),
    path('orders/coming/<hashid:oc_id>/edit/', views.edit_orders_coming, name='editOrdersComing'),
    path('orders/<hashid:order_id>/export-excel/', views.exportOrderExcel, name='exportOrderExcel'),
    path('orders/plant', views.adicionarPlants, name='adicionarPlants'),

    # Pedidos (Diameter & Partidos)
    path('partidosMenu/<path:toma_order_full>/', views.partidosMenu, name='partidosMenu'),
    path('diametroMenu/<path:toma_order_full>/', views.diametroMenu, name='diametroMenu'),
    path('listarPedidosDiametro/', views.listarPedidosDiametro, name='listarPedidosDiametro'),
    path('pedidos/diametro/editar/<hashid:id>/', views.editar_pedido_inline, name='editar_pedido_inline'),
    path('pedidos/diametro/excel/<hashid:id>/', views.exportar_pedido_excel, name='exportar_pedido_excel'),
    path('listarPartidos/', views.listarPartidos, name='listarPartidos'),
    path('partidos/<hashid:pk>/toggle-feito-ajax/', views.toggle_partido_feito_ajax, name='toggle_partido_feito_ajax'),
    path('pedidos/<hashid:pk>/toggle-feito-ajax/', views.toggle_pedido_diametro_feito_ajax, name='toggle_pedido_diametro_feito_ajax'),

    # Delivery
    path('deliveryIdentification/<path:toma_order_full>/', views.deliveryIdentification, name='deliveryIdentification'),
    path('delivery/calendar/', views.deliveryCalendar, name='deliveryCalendar'),
    path('enviar-caixa/<hashid:qr_id>/', views.enviar_caixa, name='enviar_caixa'),
    path('create-caixa/', views.create_caixa, name='create_caixa'),
    path('fieira_path/', views.fieira_path, name='fieira_path'),
    path('listarInfo/', views.listarInfo, name='listarInfo'),
    path('deletarDelivery/<hashid:id>/', views.deletar_delivery, name='deletar_delivery'),

    # Tracking
    path('adicionarTracking/', views.create_tracking, name='adicionarTracking'),
    path('listarTracking/', views.listar_trackings, name='listarTracking'),
    path('editarTracking/<hashid:pk>/', views.create_tracking, name='editarTracking'),

    # Measurements & Calibrations
    path('listarMedicoes/', views.listar_medicoes, name='listarMedicoes'),
    path('listarCalibracoes/', views.listar_calibracoes, name='listarCalibracoes'),
    path('charts/', views.charts, name='production_chart'),

    # Invoices
    path('listarFaturas/', views.listarFaturas, name='listarFaturas'),
    path('criarFatura/', views.criarFatura, name='criarFatura'),
    path('editar_fatura/<hashid:fatura_id>/', views.editarFatura, name='editarFatura'),
    path('api/upload-fatura/', views.upload_arquivo_fatura, name='api_upload_fatura'),
    path('api/delete-anexo/', views.delete_anexo_api, name='api_delete_anexo'),

    # Suppliers
    path('listarFornecedores/', views.listarFornecedores, name='listarFornecedores'),
    path('atualizar-fornecedor/<hashid:id>/', views.atualizar_fornecedor, name='atualizar_fornecedor'),
    path('deletar-fornecedor/<hashid:id>/', views.deletar_fornecedor, name='deletar_fornecedor'),

    # Template Files
    path('templateFiles/', views.templateFiles, name='templateFiles'),
    path('upload-template-file/<hashid:id>/', views.upload_template_file, name='upload_template_file'),
    path('criarTemplate/', views.criarTemplate, name='criarTemplate'),
    path('editarTemplate/<hashid:id>/', views.editarTemplate, name='editarTemplate'),
    path('delete-file/<hashid:file_id>/', views.delete_template_file, name='delete_template_file'),

    # Relatorios
    path('relatorioTrabalhos/', views.relatorio_data, name='relatorio_data'),
]

handler403 = 'theme.views.erro403'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
