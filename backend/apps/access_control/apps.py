from django.apps import AppConfig


class AccessControlConfig(AppConfig):
    name = 'apps.access_control'

    def ready(self):
        from . import checks  # noqa: F401




