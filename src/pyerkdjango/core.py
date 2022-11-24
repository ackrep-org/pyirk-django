
import os
from . import django_setup  # noqa
from django.core import management
import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from ipydex import IPS, activate_ips_on_exception  # noqa
activate_ips_on_exception()


def setup_django():
    try:
        hasattr(settings, "BASE_DIR")
    except ImproperlyConfigured:
        settings_configured_flag = False
    else:
        settings_configured_flag = True

    if not settings_configured_flag:
        # mod_path = os.path.dirname(os.path.abspath(__file__))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyerkdjango.django_project.settings")
        django.setup()
    else:
        pass


def start_django(*args, **kwargs):
    print("starting django")
    # exit()

    management.call_command("runserver", *args, **kwargs)
