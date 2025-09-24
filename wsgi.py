"""
WSGI config for surveillance_system project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings_production')

application = get_wsgi_application() 