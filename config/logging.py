"""Central Loguru configuration for Django and standard-library logs."""

import inspect
import logging
import re
import sys
from http import HTTPStatus

from loguru import logger

PRETTY_LOG_FORMAT = (
    "<green>{time:MMM D, YYYY h:mm:ss A}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[source]: <18}</cyan> | "
    "<level>{message}</level>"
)
SOURCE_LABELS = {
    "django.core.servers.basehttp": "Web server",
    "django.request": "Web request",
    "django.security": "Security",
    "django.server": "Web request",
    "django.utils.autoreload": "Development reload",
    "django_components": "UI components",
    "studio.providers": "Model provider",
    "studio.services": "Workflow service",
    "studio.views": "Web request",
    "config": "Configuration",
}
REQUEST_LOG_PATTERN = re.compile(
    r'^"(?P<method>[A-Z]+) (?P<target>\S+) HTTP/[\d.]+" '
    r"(?P<status>\d{3}) (?P<size>\d+|-)$"
)
LOGGER_LEVELS = {
    "django.db.backends": logging.WARNING,
    "django.template": logging.WARNING,
    "django.utils.autoreload": logging.INFO,
    "django_components": logging.INFO,
    "httpcore": logging.WARNING,
    "httpx": logging.WARNING,
}


class InterceptHandler(logging.Handler):
    """Forward standard-library records to the configured Loguru sink."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        message = record.getMessage()
        logger.bind(source=_friendly_source(record.name, message)).opt(
            depth=depth,
            exception=record.exc_info,
        ).log(
            level,
            _friendly_message(record.name, message),
        )


def _friendly_source(logger_name: str, message: str) -> str:
    """Return a readable subsystem name for a technical logger name."""
    if logger_name == "django.server":
        match = REQUEST_LOG_PATTERN.match(message)
        if match:
            target = match.group("target")
            if target.startswith("/static/django-browser-reload/"):
                return "Browser reload"
            if target.startswith("/static/"):
                return "Static assets"

    for prefix, label in SOURCE_LABELS.items():
        if logger_name == prefix or logger_name.startswith(f"{prefix}."):
            return label

    package_name = logger_name.split(".", maxsplit=1)[0]
    return package_name.replace("_", " ").title()


def _friendly_message(logger_name: str, message: str) -> str:
    """Translate Django's raw development-server line into a clear outcome."""
    if logger_name != "django.server":
        return message

    match = REQUEST_LOG_PATTERN.match(message)
    if not match:
        return message

    status_code = int(match.group("status"))
    try:
        status_name = HTTPStatus(status_code).phrase
    except ValueError:
        status_name = "Response"

    response_size = _format_response_size(match.group("size"))
    return (
        f"{match.group('method')} {match.group('target')} "
        f"→ {status_code} {status_name} · {response_size}"
    )


def _format_response_size(raw_size: str) -> str:
    """Format an HTTP response size for a person reading the console."""
    if raw_size == "-":
        return "size unavailable"

    size = int(raw_size)
    if size == 0:
        return "no response body"
    if size < 1024:
        unit = "byte" if size == 1 else "bytes"
        return f"{size} {unit}"
    if size < 1024**2:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024**2:.1f} MB"


def configure_logging(*, level: str, diagnose: bool) -> None:
    """Configure one readable sink and intercept Django's standard logs."""
    logger.configure(extra={"source": "Application"})
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=PRETTY_LOG_FORMAT,
        colorize=None,
        backtrace=diagnose,
        diagnose=diagnose,
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name, logger_level in LOGGER_LEVELS.items():
        logging.getLogger(logger_name).setLevel(logger_level)
