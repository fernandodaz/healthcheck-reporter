"""Simple health checker service for testing."""

import logging

logger = logging.getLogger(__name__)

def hello_healthcheck():
    """Log a simple hello message for testing."""
    logger.info("Hello from healtcheck")