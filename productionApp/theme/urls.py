from django.urls import path # type: ignore
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create-user/', views.create_user, name='create_user'),
    path('login/<int:user_id>/', views.login_view, name='login'),
    path('production-menu/<int:user_id>/', views.production_menu, name='production_menu'),
    path('input_production/', views.inputProduction, name='input_production'),
    path('editar-produto/<int:produto_id>/', views.editProduct, name='editar_produto'),
    path('deletar-produto/<int:produto_id>/', views.deleteProduct, name='deletar_produto'),

]
