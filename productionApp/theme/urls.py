from django.urls import path # type: ignore
from django.conf.urls.static import static # type: ignore

from productionApp import settings # type: ignore
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create-user/', views.create_user, name='create_user'),
    path('login/<int:user_id>/', views.login_view, name='login'),
    path('mainMenu/<int:user_id>/', views.mainMenu, name='mainMenu'),
    path('inputProduction/', views.inputProduction, name='inputProduction'),
    path('editProduct/<int:produto_id>/', views.editProduct, name='editProduct'),
    path('delectProduct/<int:produto_id>/', views.deleteProduct, name='delectProduct'),
    path('scanBox/', views.scanBox, name='scanBox'),
    path('listQrcodes/', views.listQrcodes, name='listQrcodes'),
    path('partidosMenu/<slug:toma_order_full>/', views.partidosMenu, name='partidosMenu'),
    path('diametroMenu/<slug:toma_order_full>/', views.diametroMenu, name='diametroMenu'),
    path('qrdata/editar/<int:qr_id>/', views.showDetails, name='showDetails'),
    path('qrcode/<int:qr_id>/dies/', views.adicionar_dies, name='adicionar_dies'),
    path('dies/', views.listar_qrcodes_com_dies, name='listarDies'),
    path('die/<int:die_id>/', views.die_details, name='die_details'),
    path('die/<int:die_id>/novo-trabalho/', views.create_die_work, name='create_die_work'),
    path('die-work/<int:work_id>/add-worker/', views.add_worker_to_die_work, name='add_worker_to_die_work'),
    path('qrcode/<int:qr_id>/export-excel/', views.export_qrcode_excel, name='export_qrcode_excel'),
    path('enviar-fieira/<int:die_id>/', views.enviar_fieira, name='enviar_fieira'),
    path('enviar-caixa/<int:qr_id>/', views.enviar_caixa, name='enviar_caixa'),
    path('create-caixa/', views.create_caixa, name='create_caixa'),
    path('listarPedidosDiametro/', views.listarPedidosDiametro, name='listarPedidosDiametro'),
    path('listarPartidos/', views.listarPartidos, name='listarPartidos'),
    path('localizarFieira/', views.localizarFieira, name='localizarFieira'),
    path('qOfficeMenu/', views.qOfficeMenu, name='qOfficeMenu'),
    path('productionMenu/', views.productionMenu, name='productionMenu'),
    path('comercialMenu/', views.comercialMenu, name='comercialMenu'),
    path('partidos/<int:pk>/toggle-feito-ajax/', views.toggle_partido_feito_ajax, name='toggle_partido_feito_ajax'),
    path('pedidos/<int:pk>/toggle-feito-ajax/', views.toggle_pedido_diametro_feito_ajax, name='toggle_pedido_diametro_feito_ajax'),
    path('deliveryIdentification/<slug:toma_order_full>/', views.deliveryIdentification, name='deliveryIdentification'),
    path('delivery/calendar/', views.deliveryCalendar, name='deliveryCalendar'),
    path('listarInfo/', views.listarInfo, name='listarInfo'),
    path('deletarDelivery/<int:id>/', views.deletar_delivery, name='deletar_delivery'),
    path('logout/', views.user_logout, name='logout'),
    path('orders/', views.orders, name='orders'),
    path('orders/listar/', views.listar_orders, name='listarOrders'),  
    path('orders/<int:order_id>/edit/', views.edit_order, name='editOrder'),
    path('orders/<int:order_id>/delete/', views.delete_order, name='deleteOrder'),
    path('orders/file/<int:file_id>/delete/', views.delete_order_file, name='deleteOrderFile'),
    path('orders/create_orders_coming_ajax/', views.create_orders_coming_ajax, name='create_orders_coming_ajax'),
    path('orders/coming/<int:oc_id>/edit/', views.edit_orders_coming, name='editOrdersComing'),
    path('administrationMenu/', views.administrationMenu, name='administrationMenu'),
    path('orders/<int:order_id>/export-excel/', views.exportOrderExcel, name='exportOrderExcel'),

]

handler403 = 'theme.views.permission_denied_view'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)