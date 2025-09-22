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

    # MQTT broker config
    mqtt_host: str
    mqtt_port: int
    mqtt_client_id: str
    mqtt_topic: str
    mqtt_user: Optional[str] = None
    mqtt_password: Optional[str] = None


@dataclass(frozen=True)
class HealthReport:
    """Represents a single healthcheck report payload."""

    database_status: str
    mqtt_client_id: str
    timestamp: str
