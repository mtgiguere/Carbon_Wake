"""WSGI entry point — arrived with the deployment step (gunicorn needs it;
runserver and the tests never did)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carbon_atlas.web.settings")

application = get_wsgi_application()
