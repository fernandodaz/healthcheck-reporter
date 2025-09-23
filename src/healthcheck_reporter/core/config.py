from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReporterConfig:
    """Immutable configuration for the healthcheck reporter.

    Supports both MQTT and REST modes; only the relevant fields are required per mode.
    """

    # Database
    database_host: str
    database_port: int
    database_name: str
    database_password: str
    database_user: str

    # MQTT (for MQTT mode)
    mqtt_host: Optional[str] = None
    mqtt_port: Optional[int] = None
    mqtt_client_id: Optional[str] = None
    mqtt_topic: Optional[str] = None
    mqtt_user: Optional[str] = None
    mqtt_password: Optional[str] = None

    # REST (for REST mode)
    api_host: Optional[str] = None
    api_port: Optional[int] = None
    api_path: Optional[str] = None


