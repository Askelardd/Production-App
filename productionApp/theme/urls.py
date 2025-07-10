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


]
