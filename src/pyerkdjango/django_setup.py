import os
import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.apps import apps


# The following is necessary to let us use django functionality without accessing via manage.py
try:
    hasattr(settings, "BASE_DIR")
except ImproperlyConfigured:
    settings_configured_flag = False
else:
    settings_configured_flag = True


if not apps.apps_ready:
    settings_configured_flag = False

if not settings_configured_flag:

    os.environ["DJANGO_SETTINGS_MODULE"] = "pyerkdjango.django_project.settings"
    django.setup()
else:
    pass
