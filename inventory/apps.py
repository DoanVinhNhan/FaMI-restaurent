from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"

    def ready(self):
        # Import signal handlers so they are registered when the app is loaded
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid raising during manage.py operations if signals import fails
            pass
