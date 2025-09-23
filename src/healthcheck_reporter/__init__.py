"""Public API for healthcheck-reporter."""

from importlib.metadata import PackageNotFoundError, version

from .reporter.reporter import Reporter
from .core.config import ReporterConfig
from .core.models import HealthReport

try:
    __version__: str = version("healthcheck-reporter")
except PackageNotFoundError:
    __version__ = "0.0.0"
__all__: list[str] = ["Reporter", "ReporterConfig", "HealthReport"]