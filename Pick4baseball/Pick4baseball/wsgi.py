"""
WSGI config for Pick4baseball project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""
import os
import sys

project_home = '/home/cheald10/PythonAW'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

project_home2 = '/home/cheald10/PythonAW/Pick4baseball'
if project_home2 not in sys.path:
    sys.path.insert(0, project_home2)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Pick4baseball.settings_prod")

application = get_wsgi_application()
