"""
simple command to facilitate debugging via `python manage.py debug`

"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    manually trigger a pelican run
    """
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        # Positional arguments
        # parser.add_argument('poll_ids', nargs='+', type=int)

        parser.add_argument(
            '--dbg', action="store_true",
            help='debug mode',
        )

        # Named (optional) arguments
        parser.add_argument(
            "-l",
            "--load-mod",
            help="load module from path with prefix. You might want to provide the `-rwd` flag",
            nargs=2,
            default=None,
            metavar=("MOD_PATH", "PREFIX"),
        )

        parser.add_argument(
            "-rwd",
            "--relative-to-workdir",
            help=(
                "specifies that the module path is interpreted relative to working dir "
                "(not the modules install path)"
            ),
            default=False,
            action="store_true",
        )

    def handle(self, *args, **options):
        from ipydex import IPS, activate_ips_on_exception  # noqa
        activate_ips_on_exception()
        from mainapp.models import Entity  # noqa

        loaded_mod, prefix = options.get("load_mod") or (None, None)

        if loaded_mod is not None and prefix is not None:
            locals()[prefix] = loaded_mod

        IPS()
