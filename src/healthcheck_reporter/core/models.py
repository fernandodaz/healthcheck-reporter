from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthReport:
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
    uptime: float


