from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Literal


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

    # Raw counters to enable single-point DTO computation
    db_attempt_count: int = 0
    mqtt_attempt_count: int = 0
    api_attempt_count: int = 0
    db_ok: bool = False
    debug_overall_status: Optional[str] = None
    degraded_threshold_percent: float = 20.0
    unavailable_threshold_percent: float = 100.0

    def to_dict(self) -> dict[str, object]:
        # Compute derived metrics centrally to avoid duplication across transports
        db_failure_rate = (
            (self.db_error_count / self.db_attempt_count) * 100.0 if self.db_attempt_count > 0 else 0.0
        )
        mqtt_failure_rate = (
            (self.mqtt_error_count / self.mqtt_attempt_count) * 100.0 if self.mqtt_attempt_count > 0 else 0.0
        )
        api_failure_rate = (
            (self.api_error_count / self.api_attempt_count) * 100.0 if self.api_attempt_count > 0 else 0.0
        )

        if self.debug_overall_status is not None:
            overall_status = self.debug_overall_status
        elif (db_failure_rate >= self.unavailable_threshold_percent
              or mqtt_failure_rate >= self.unavailable_threshold_percent
              or api_failure_rate >= self.unavailable_threshold_percent
              or not self.db_ok):
            # Consider hard failure if DB currently down or any rate exceeds the unavailable threshold
            overall_status = "unavailable"
        elif (db_failure_rate >= self.degraded_threshold_percent
              or mqtt_failure_rate >= self.degraded_threshold_percent
              or api_failure_rate >= self.degraded_threshold_percent):
            overall_status = "degraded"
        else:
            overall_status = "operational"

        database_status: Literal['failed', 'ok'] = "ok" if self.db_ok else "failed"
        timestamp: str = self.timestamp or datetime.now(timezone.utc).isoformat()

        return {
            "database_status": database_status,
            "mqtt_client_id": self.mqtt_client_id,
            "timestamp": timestamp,
            "db_error_count": self.db_error_count,
            "mqtt_error_count": self.mqtt_error_count,
            "db_failure_rate": round(db_failure_rate, 2),
            "mqtt_failure_rate": round(mqtt_failure_rate, 2),
            "overall_status": overall_status,
            "api_error_count": self.api_error_count,
            "api_failure_rate": round(api_failure_rate, 2),
            "uptime": self.uptime,
        }

