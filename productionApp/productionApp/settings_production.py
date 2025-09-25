# productionApp/settings_production.py
from pathlib import Path
import os
import environ, dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(str, "localhost,127.0.0.1, 192.168.1.105, 94.60.97.225"),
    DJANGO_CSRF_TRUSTED_ORIGINS=(str, ""),
    DJANGO_CONN_MAX_AGE=(int, 60),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# --- Core ---
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("DJANGO_CSRF_TRUSTED_ORIGINS").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "tailwind","theme",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "productionApp.urls"

# 👉 Estamos a usar WSGI (Gunicorn)
WSGI_APPLICATION = "productionApp.wsgi.application"

LOGIN_URL = "/login"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # procura templates em <project>/templates
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,  # também procura em <app>/templates/
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Email ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

EMAIL_TO_EMAIL = [e.strip() for e in env("EMAIL_TO_EMAIL", default="").split(",") if e.strip()]
EMAIL_DIAMETRO = [e.strip() for e in env("EMAIL_DIAMETRO", default="").split(",") if e.strip()]

# --- Database ---
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", default="postgres://askelardd:pass@db:5432/transporteinfo"),
        conn_max_age=env("DJANGO_CONN_MAX_AGE"),
        ssl_require=False,
    )
}

# --- Locale ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

# --- Static & Media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # <- corrigido
# se tiveres uma pasta <project>/static para assets do projeto:
if (BASE_DIR / "static").exists():
    STATICFILES_DIRS = [BASE_DIR / "static"]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Security (ativa em HTTPS) ---
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# (opcional) logging básico para produção
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
