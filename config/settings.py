"""Settings for the governed AI studio demonstration."""

import os
from pathlib import Path

from dotenv import load_dotenv

from config.logging import configure_logging

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "demo-only-change-before-deployment")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "auditlog",
    "django_browser_reload",
    "django_components",
    "django_htmx",
    "template_partials.apps.SimpleAppConfig",
    "studio",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                (
                    "template_partials.loader.Loader",
                    [
                        (
                            "django.template.loaders.cached.Loader",
                            [
                                "django.template.loaders.filesystem.Loader",
                                "django.template.loaders.app_directories.Loader",
                                "django_components.template_loader.Loader",
                            ],
                        )
                    ],
                )
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django_components.finders.ComponentsFileSystemFinder",
]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# SQLite cannot persist SQL COMMENT metadata. Keep the comments in Django's model and
# migration state for admin/developer tooling and for databases that support comments,
# without repeating one warning for every documented table and column locally.
SILENCED_SYSTEM_CHECKS = ["fields.W163", "models.W046"]

COMPONENTS = {
    "dirs": [],
    "app_dirs": ["components"],
    # Import component registrations deterministically at Django startup. Autodiscovery
    # remains useful for component assets, but a long-running development server does
    # not watch Python modules that did not exist when its autoreloader started.
    "libraries": [
        "studio.components.menu_icon.menu_icon",
        "studio.components.status_badge.status_badge",
    ],
}

# Audit the governed domain records. Proof events remain the curated business
# evidence trail; these entries preserve lower-level create, update, and delete history.
AUDITLOG_INCLUDE_TRACKING_MODELS = (
    {
        "model": "studio.OntologyNode",
        "exclude_fields": ["updated_at"],
        "serialize_data": True,
        "serialize_auditlog_fields_only": True,
    },
    {"model": "studio.OntologyEdge", "serialize_data": True},
    {
        "model": "studio.WorkflowProposal",
        "exclude_fields": ["updated_at"],
        "serialize_data": True,
        "serialize_auditlog_fields_only": True,
    },
    {"model": "studio.ProposalBinding", "serialize_data": True},
    {"model": "studio.ControlCheck", "serialize_data": True},
    {"model": "studio.ProofEvent", "serialize_data": True},
    {"model": "studio.ProposalApproval", "serialize_data": True},
    {"model": "studio.AgentManifest", "serialize_data": True},
    {
        "model": "studio.SandboxAgentInstance",
        "exclude_fields": ["updated_at"],
        "serialize_data": True,
        "serialize_auditlog_fields_only": True,
    },
    {"model": "studio.ToolInvocation", "serialize_data": True},
    {"model": "studio.InsuranceFinding", "serialize_data": True},
    {"model": "studio.EvaluationResult", "serialize_data": True},
    {"model": "studio.EvidenceArtifact", "serialize_data": True},
)
AUDITLOG_STORE_JSON_CHANGES = True
AUDITLOG_DISABLE_REMOTE_ADDR = True
AUDITLOG_CID_HEADER = "x-request-id"

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()
LOGGING_CONFIG = None
configure_logging(level=LOG_LEVEL, diagnose=DEBUG)
