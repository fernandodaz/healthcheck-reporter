"""
A simple health checker service package for microservices.
"""

from importlib.metadata import PackageNotFoundError, version

from .health_checker import hello_healthcheck
from .models import get_hello_message

try:
    __version__ = version("healthcheck-reporter")
except PackageNotFoundError:
    __version__ = "0.0.0"
__all__ = ["hello_healthcheck", "get_hello_message"]