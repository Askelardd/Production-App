import socket
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse


class AcessoExternoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        #  endereço DDNS 
        self.ddns_escritorio = 'endreço ddns' 

    def obter_ip_escritorio(self):
        # 1. Tenta ir buscar o IP à cache do Django para ser super rápido
        ip_atual = cache.get('ip_escritorio_cache')
        
        # 2. Se não estiver na cache vai à Internt do user descobrir
        if not ip_atual:
            try:
                ip_atual = socket.gethostbyname(self.ddns_escritorio)
                # Guarda na cache por 5 minutos 
                cache.set('ip_escritorio_cache', ip_atual, 300)
            except socket.error:
                message = f"Não consegui resolver o DDNS '{self.ddns_escritorio}' para obter o IP do escritório."
                print(message)
                return None  # Se não conseguir resolver o DDNS, retorna None
                
        return ip_atual

    def __call__(self, request):
            # 1. Tentar primeiro o Cloudflare
            ip_utilizador = request.META.get('HTTP_CF_CONNECTING_IP')

            # 2. Se não vier do Cloudflare, tenta o X-Forwarded-For
            if not ip_utilizador:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_utilizador = x_forwarded_for.split(',')[0].strip()
                else:
                    # 3. Em último caso, usa o REMOTE_ADDR
                    ip_utilizador = request.META.get('REMOTE_ADDR')

            # Vamos buscar o IP atual do escritório
            ip_escritorio = self.obter_ip_escritorio()
            
            print(f"IP do utilizador: {ip_utilizador}, IP do escritório: {ip_escritorio}")

            # O IP é o próprio servidor (localhost) ou é o IP de dentro do escritório? -> Sim, entra.
            if ip_utilizador == '127.0.0.1' or (ip_escritorio and ip_utilizador == ip_escritorio):
                return self.get_response(request)

            if request.path == reverse('logout'):
                return self.get_response(request)

            if request.user.is_authenticated:
                if request.user.groups.filter(name='externo').exists() or request.user.is_superuser:
                    return self.get_response(request)
                else:
                    return render(request, 'access_denied.html', status=403)

            return self.get_response(request)