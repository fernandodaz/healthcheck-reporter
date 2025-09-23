"""Data models and configuration for healthcheck reporter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReporterConfig:
    """Immutable configuration for the healthcheck reporter.

    Using a dataclass reduces constructor argument bloat and keeps the API tidy.
    """

    # Database TCP endpoint (used only for connectivity probe)
    database_host: str
    database_port: int
    database_name: str
    database_password: str
    database_user: str

    # MQTT broker config (required for MQTT mode)
    mqtt_host: Optional[str] = None
    mqtt_port: Optional[int] = None
    mqtt_client_id: Optional[str] = None
    mqtt_topic: Optional[str] = None
    mqtt_user: Optional[str] = None
    mqtt_password: Optional[str] = None

    # REST API config (required for REST mode)
    api_host: Optional[str] = None  # e.g., "0.0.0.0" or "127.0.0.1"
    api_port: Optional[int] = None
    api_path: Optional[str] = None  # e.g., "api/whatever/health"


@dataclass(frozen=True)
class HealthReport:
    """Represents a single healthcheck report payload."""

    database_status: str
    mqtt_client_id: str
    timestamp: str
    db_error_count: int
    mqtt_error_count: int
    db_failure_rate: float
    mqtt_failure_rate: float
    overall_status: str
    api_error_count: int
    api_failure_rate: float
