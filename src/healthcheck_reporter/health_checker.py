"""Healthcheck reporter implementation."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt

from .models import HealthReport, ReporterConfig


logger: logging.Logger = logging.getLogger(__name__)


def probe_tcp_connectivity(host: str, port: int, timeout_seconds: float) -> bool:
    """Attempt a TCP connection to host:port within timeout.

    This is database-agnostic and avoids driver dependencies.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        try:
            sock.connect((host, port))
            return True
        except Exception:
            return False


def probe_postgres_connectivity(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    timeout_seconds: float,
) -> bool:
    """Attempt to establish a PostgreSQL connection using psycopg2, if available.

    Returns True on successful connection; False on failure or if psycopg2 is not installed.
    """
    try:
        import psycopg2  # type: ignore
        from psycopg2 import OperationalError  # type: ignore
    except Exception:
        return False

    dsn: str = (
        f"host={host} port={int(port)} dbname={dbname} user={user} password={password} "
        f"connect_timeout={int(max(1.0, timeout_seconds))}"
    )
    try:
        conn = psycopg2.connect(dsn)
        try:
            conn.close()
        except Exception:
            pass
        return True
    except OperationalError:
        return False
    except Exception:
        return False


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Reporter:
    """Periodic health reporter that publishes to MQTT."""

    def __init__(
        self,
        config: ReporterConfig,
        *,
        interval_seconds: float = 30.0,
        db_probe_timeout_seconds: float = 3.0,
        mqtt_connect_timeout_seconds: float = 5.0,
        debug_mode: bool = False,
    ) -> None:
        self._config = config
        self._interval_seconds = max(0.1, interval_seconds)
        self._db_probe_timeout_seconds = max(0.1, db_probe_timeout_seconds)
        self._mqtt_connect_timeout_seconds = max(0.1, mqtt_connect_timeout_seconds)
        self._debug_mode = debug_mode

        # MQTT client is created per Reporter instance and reused across publishes
        self._mqtt_client = mqtt.Client(client_id=config.mqtt_client_id, clean_session=True)
        if config.mqtt_user is not None:
            self._mqtt_client.username_pw_set(config.mqtt_user, config.mqtt_password)

        # Threading primitives
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Error counters (cumulative)
        self._db_error_count: int = 0
        self._mqtt_error_count: int = 0
        self._db_attempt_count: int = 0
        self._mqtt_attempt_count: int = 0
        self._debug_start_time: float = time.monotonic()

    # Public API
    def start(self) -> None:
        """Start periodic reporting in a background thread (non-blocking)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="healthcheck-reporter", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background reporting loop and wait for thread to exit."""
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=self._interval_seconds + 1.0)
        self._thread = None

    def make_report(self) -> HealthReport:
        """Create a single health report and publish it to MQTT."""

        # Database probe attempt
        self._db_attempt_count += 1
        db_ok: bool
        db_ok = probe_postgres_connectivity(
            self._config.database_host,
            int(self._config.database_port),
            self._config.database_name,
            self._config.database_user,
            self._config.database_password,
            self._db_probe_timeout_seconds,
        )
        if not db_ok:
            db_ok = probe_tcp_connectivity(
                self._config.database_host,
                int(self._config.database_port),
                self._db_probe_timeout_seconds,
            )

        if not db_ok:
            self._db_error_count += 1

        # Prepare MQTT attempt count before publish so payload reflects attempts
        self._mqtt_attempt_count += 1

        # Compute failure rates (percentage 0-100)
        db_failure_rate: float = (
            (self._db_error_count / self._db_attempt_count) * 100.0 if self._db_attempt_count > 0 else 0.0
        )
        mqtt_failure_rate: float = (
            (self._mqtt_error_count / self._mqtt_attempt_count) * 100.0 if self._mqtt_attempt_count > 0 else 0.0
        )

        # Derive overall status
        if self._debug_mode:
            # Debug mode: alternate between degraded and unavailable every 5 seconds
            elapsed = time.monotonic() - self._debug_start_time
            cycle_position = (elapsed % 10.0) / 10.0  # 0-1 over 10 second cycle
            overall_status = "degraded" if cycle_position < 0.5 else "unavailable"
        elif not db_ok:
            overall_status: str = "unavailable"
        elif db_failure_rate >= 20.0 or mqtt_failure_rate >= 20.0:
            overall_status = "degraded"
        else:
            overall_status = "operational"

        report = HealthReport(
            database_status="ok" if db_ok else "failed",
            mqtt_client_id=self._config.mqtt_client_id,
            timestamp=iso_utc_now(),
            db_error_count=self._db_error_count,
            mqtt_error_count=self._mqtt_error_count,
            db_failure_rate=round(db_failure_rate, 2),
            mqtt_failure_rate=round(mqtt_failure_rate, 2),
            overall_status=overall_status,
        )

        self._publish_report(report)
        return report

    # Internal
    def _publish_report(self, report: HealthReport) -> None:
        payload: str = json.dumps(
            {
                "database_status": report.database_status,
                "mqtt_client_id": report.mqtt_client_id,
                "timestamp": report.timestamp,
                "db_error_count": report.db_error_count,
                "mqtt_error_count": report.mqtt_error_count,
                "db_failure_rate": report.db_failure_rate,
                "mqtt_failure_rate": report.mqtt_failure_rate,
                "overall_status": report.overall_status,
            },
            separators=(",", ":"),
        )

        try:
            # Ensure connection before publish; reconnect if needed
            if not self._mqtt_client.is_connected():
                self._connect_mqtt()

            result = self._mqtt_client.publish(self._config.mqtt_topic, payload=payload, qos=1, retain=False)
            status = result.rc if hasattr(result, "rc") else result[0]
            if status != mqtt.MQTT_ERR_SUCCESS:
                self._mqtt_error_count += 1
                logger.error("MQTT publish failed with status %s", status)
        except Exception as exc:
            self._mqtt_error_count += 1
            logger.exception("MQTT publish error: %s", exc)

    def _connect_mqtt(self) -> None:
        self._mqtt_client.reinitialise(client_id=self._config.mqtt_client_id, clean_session=True)
        if self._config.mqtt_user is not None:
            self._mqtt_client.username_pw_set(self._config.mqtt_user, self._config.mqtt_password)
        self._mqtt_client.connect(self._config.mqtt_host, self._config.mqtt_port, keepalive=int(self._mqtt_connect_timeout_seconds))
        self._mqtt_client.loop_start()

    def _run_loop(self) -> None:
        next_run: float = time.monotonic()
        while not self._stop_event.is_set():
            try:
                self.make_report()
            except Exception:
                logger.exception("Unexpected error during make_report")

            next_run += self._interval_seconds
            timeout: float = max(0.0, next_run - time.monotonic())
            self._stop_event.wait(timeout)
