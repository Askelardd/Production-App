from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve 

# Define o handler de erro 403 globalmente
handler403 = 'theme.views.erro403'

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Aponta para o ficheiro de urls da tua app 'theme'
    path('', include('theme.urls')), 
]

# --- BLOCO MÁGICO PARA A QNAP ---
# Isto força o Django a servir Media e Static files mesmo com DEBUG=False
if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
        re_path(r'^static/(?P<path>.*)$', serve, {
            'document_root': settings.STATIC_ROOT,
        }),
    ]