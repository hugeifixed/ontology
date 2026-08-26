"""Application configuration."""

from django.apps import AppConfig


class StudioConfig(AppConfig):
    """Configure the governed AI studio app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "studio"
    verbose_name = "Governed AI Studio"
