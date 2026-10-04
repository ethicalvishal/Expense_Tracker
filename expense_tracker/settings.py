"""
Django settings for expense_tracker project.

Configuration comes from environment variables, so the same code runs
locally (no setup needed) and on Render (set the variables in the dashboard).

Environment variables:
    SECRET_KEY      Django secret key (REQUIRED on Render - set your own)
    DATABASE_URL    PostgreSQL URL. If missing, local SQLite is used.
    DEBUG           "True" / "False". Defaults to True locally, False on Render.
    ALLOWED_HOSTS   Extra hosts, comma separated (e.g. your custom domain).
    EMAIL_HOST_USER / EMAIL_HOST_PASSWORD
                    SMTP login used to send "forgot password" emails
                    (optional; without it the reset link is printed in the logs).
    EMAIL_HOST / EMAIL_PORT / DEFAULT_FROM_EMAIL
                    Optional SMTP overrides (default: Gmail on port 587).
"""

import os
import warnings
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Render sets the RENDER environment variable automatically.
IS_RENDER = 'RENDER' in os.environ


# --- Security -------------------------------------------------------------

_DEV_SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
SECRET_KEY = os.environ.get('SECRET_KEY', _DEV_SECRET_KEY)
if IS_RENDER and SECRET_KEY == _DEV_SECRET_KEY:
    warnings.warn(
        'SECRET_KEY is not set on Render. Add it in the Render dashboard '
        '(Environment tab) with a new random value.'
    )

DEBUG = os.environ.get('DEBUG', 'False' if IS_RENDER else 'True').lower() == 'true'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com']
ALLOWED_HOSTS += [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if _render_host:
    ALLOWED_HOSTS.append(_render_host)

CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']
CSRF_TRUSTED_ORIGINS += [
    f'https://{h.strip()}'
    for h in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if h.strip()
]

if IS_RENDER:
    # Render terminates HTTPS in front of gunicorn.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# --- Application definition -----------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'expenses',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'expense_tracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'expense_tracker.wsgi.application'


# --- Database -------------------------------------------------------------
# PostgreSQL when DATABASE_URL is set (Render), otherwise local SQLite.
# Render's disk is temporary, so SQLite data there is lost on every deploy.

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        ),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# --- Password validation --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internationalization -------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# --- Static files ---------------------------------------------------------

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# Also serve files straight from the app's static folders, so the CSS/JS work
# even if "collectstatic" was not part of the build command.
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Login / logout -------------------------------------------------------

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Keep users logged in for 30 days. Their data lives in the database and is
# never removed unless the user deletes it (or their account) themselves.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

# Bootstrap calls the "error" alert style "danger".
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}


# --- Email (forgot-password) ----------------------------------------------

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'Expense Tracker <noreply@example.com>'
)
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    # No SMTP configured: emails are printed to the server log instead.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# --- Logging (shows up in the Render logs) --------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
