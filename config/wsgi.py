"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import resource
mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(f"RSS before loading app: {mem // 1024} MB", file=sys.stderr)

application = get_wsgi_application()

mem2 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(f"RSS after loading app: {mem2 // 1024} MB", file=sys.stderr)