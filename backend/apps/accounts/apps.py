from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'

    def ready(self):
        # WF-01.06 P-01: stamp every new login with its sign-in time.
        from . import session_timeout  # noqa: F401




