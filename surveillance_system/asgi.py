"""
ASGI config for surveillance_system project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# Use production settings by default for deployment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings_production')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# WebSockets supprimés - utilisation d'API REST uniquement
application = django_asgi_app
