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
    ) -> None:
        self._config = config
        self._interval_seconds = max(0.1, interval_seconds)
        self._db_probe_timeout_seconds = max(0.1, db_probe_timeout_seconds)
        self._mqtt_connect_timeout_seconds = max(0.1, mqtt_connect_timeout_seconds)

        # MQTT client is created per Reporter instance and reused across publishes
        self._mqtt_client = mqtt.Client(client_id=config.mqtt_client_id, clean_session=True)
        if config.mqtt_user is not None:
            self._mqtt_client.username_pw_set(config.mqtt_user, config.mqtt_password)

        # Threading primitives
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

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

        db_ok = probe_tcp_connectivity(
            self._config.database_host,
            self._config.database_port,
            self._db_probe_timeout_seconds,
        )

        report = HealthReport(
            database_status="ok" if db_ok else "failed",
            mqtt_client_id=self._config.mqtt_client_id,
            timestamp=iso_utc_now(),
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
                logger.error("MQTT publish failed with status %s", status)
        except Exception as exc:
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
