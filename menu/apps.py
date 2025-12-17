# menu/apps.py
from django.apps import AppConfig


class MenuConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "menu"

    def ready(self):
        # Signals import karo taaki register ho jaayein
        from . import signals  # noqa
