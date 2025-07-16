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
    path('partidosMenu/<int:qrCode_id>/', views.partidosMenu, name='partidosMenu'),
    path('diametroMenu/<int:qrCode_id>/', views.diametroMenu, name='diametroMenu'),
    path('trabalhos/criar/<int:qr_id>/', views.adicionar_trabalho, name='adicionarTrabalhos'),
    path('desbaste-calibre/<int:desbasteCalibre_id>/workers/', views.adicionarDesbasteCalibreWorker, name='adicionarDesbasteCalibreWorker'),
    path('afinacao/<int:afinacao_id>/workers/', views.adicionarAfinacaoWorker, name='adicionarAfinacaoWorker'),
    path('desbaste-agulha/<int:desbaste_agulha_id>/workers/', views.adicionarDesbasteAgulhaWorker, name='adicionarDesbasteAgulhaWorker'),
    path('polimento/<int:polimento_id>/workers/', views.adicionarPolimentoWorker, name='adicionarPolimentoWorker'),
    path('qrcode/<int:qr_id>/detalhes/', views.detalhesQrcode, name='detalhesQrcode'),
    path('qrdata/editar/<int:qr_id>/', views.showDetails, name='showDetails'),
    path('qrcode/<int:qr_id>/dies/', views.adicionar_dies, name='adicionar_dies'),
    path('dies/', views.listar_qrcodes_com_dies, name='listarDies'),
    path('die/<int:die_id>/', views.die_details, name='die_details'),
    path('die/<int:die_id>/novo-trabalho/', views.create_die_work, name='create_die_work'),
    path('die-work/<int:work_id>/add-worker/', views.add_worker_to_die_work, name='add_worker_to_die_work'),

    


]
