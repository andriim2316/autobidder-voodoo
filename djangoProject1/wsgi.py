"""
WSGI config for djangoProject1 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from werkzeug.middleware.proxy_fix import ProxyFix

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoProject1.settings')

# Initialize WSGI application
application = get_wsgi_application()

# Apply ProxyFix middleware
application = ProxyFix(application, x_for=1, x_proto=1, x_host=1, x_port=1)