import os
import dj_database_url
from decouple import config
from datetime import timedelta
from .settings import *

# Production settings
DEBUG = False

# Security
SECRET_KEY = config('SECRET_KEY', default='django-insecure-default-key-for-render-deployment-change-me')

# Allowed hosts
ALLOWED_HOSTS = [
    '51.75.253.11',
    '.onrender.com',
    'surveillance-ia.onrender.com',
    'app-surveillance.onrender.com',
    'localhost',
    '127.0.0.1'
]

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'http://51.75.253.11',
    'http://51.75.253.11:8090',
    'http://51.75.253.11:80',
    'https://app-surveillance.onrender.com',
    'https://*.onrender.com'
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'surveillance_db',
        'USER': 'surveillance_user',
        'PASSWORD': 'm77dq3RxTJHPCrF',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Redis/Channels
# Utiliser Redis si disponible, sinon InMemoryChannelLayer
# WebSocket support supprimé - utilisation d'API REST uniquement
# redis_url = config('REDIS_URL', default=None)

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
# Middlewares personnalisés réactivés
MIDDLEWARE.insert(-1, 'surveillance_system.middleware.SecurityHeadersMiddleware')

# CORS pour production
CORS_ALLOWED_ORIGINS = [
    "http://51.75.253.11",
    "http://51.75.253.11:8090",
    "https://surveillance-ia.onrender.com",
    "https://app-surveillance.onrender.com",
    "https://*.onrender.com",
]

# Logging pour production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'surveillance_system': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Email configuration (optionnel)
if config('EMAIL_HOST', default=None):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cross-Origin-Opener-Policy pour éviter les avertissements
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# Session security
SESSION_COOKIE_SECURE = False  # False pour HTTP, True pour HTTPS
CSRF_COOKIE_SECURE = False     # False pour HTTP, True pour HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Session timeout - 2 heures maximum
SESSION_COOKIE_AGE = 7200  # 2 heures en secondes (2 * 60 * 60)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # Renouveler à chaque requête

# Token expiration pour REST Framework

# REST Framework settings avec expiration des tokens
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
} 