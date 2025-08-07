from django.urls import path # type: ignore
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create-user/', views.create_user, name='create_user'),
    path('login/<int:user_id>/', views.login_view, name='login'),
    path('productionMenu/<int:user_id>/', views.productionMenu, name='productionMenu'),
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



    


]
