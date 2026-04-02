from hashids import Hashids
from django.conf import settings

# Cria o gerador de hashes usando a chave secreta do teu projeto para segurança
hashids = Hashids(salt=settings.SECRET_KEY, min_length=8)

class HashIdConverter:
    # Aceita letras maiúsculas, minúsculas e números, com pelo menos 8 caracteres
    regex = '[a-zA-Z0-9]{8,}'

    def to_python(self, value):
        decoded = hashids.decode(value)
        if decoded:
            return int(decoded[0])
        raise ValueError("URL Inválido")

    def to_url(self, value):
        return hashids.encode(int(value))