"""Public API for healthcheck-reporter."""

from importlib.metadata import PackageNotFoundError, version

from .health_checker import Reporter
from .models import HealthReport, ReporterConfig

try:
    __version__ = version("healthcheck-reporter")
except PackageNotFoundError:
    __version__ = "0.0.0"
__all__: list[str] = ["Reporter", "ReporterConfig", "HealthReport"]