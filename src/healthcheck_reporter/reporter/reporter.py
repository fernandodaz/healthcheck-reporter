from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from ..core.config import ReporterConfig
from ..core.models import HealthReport
from ..probes.db_probe import probe_postgres_connectivity, probe_tcp_connectivity
from ..reporter.report_builder import build_report
from ..transport.mqtt_publisher import MqttPublisher
from ..transport.api_server import create_app, run_server


logger: logging.Logger = logging.getLogger(__name__)


class Reporter:
    def __init__(
        self,
        config: ReporterConfig,
        *,
        interval_seconds: float = 30.0,
        db_probe_timeout_seconds: float = 3.0,
        mqtt_connect_timeout_seconds: float = 5.0,
        debug_mode: bool = False,
        mode: str = "mqtt",
    ) -> None:
        self._config = config
        self._interval_seconds = max(0.1, interval_seconds)
        self._db_probe_timeout_seconds = max(0.1, db_probe_timeout_seconds)
        self._mqtt_connect_timeout_seconds = max(0.1, mqtt_connect_timeout_seconds)
        self._debug_mode = debug_mode
        self._mode = mode

        # State
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._debug_start_time: float = time.monotonic()
        self._process_start_time: float = time.monotonic()

        # Counters
        self._db_error_count = 0
        self._db_attempt_count = 0
        self._mqtt_error_count = 0
        self._mqtt_attempt_count = 0
        self._api_error_count = 0
        self._api_attempt_count = 0

        # Transports
        self._publisher: Optional[MqttPublisher] = None
        if mode == "mqtt":
            if not all([config.mqtt_host, config.mqtt_port, config.mqtt_client_id, config.mqtt_topic]):
                raise ValueError("MQTT mode requires mqtt_host, mqtt_port, mqtt_client_id, and mqtt_topic")
            
            mqtt_host: str = config.mqtt_host  # type: ignore[assignment]
            mqtt_port: int = int(config.mqtt_port)  # type: ignore[arg-type]
            mqtt_client_id: str = config.mqtt_client_id  # type: ignore[assignment]
            mqtt_topic: str = config.mqtt_topic  # type: ignore[assignment]
            self._publisher = MqttPublisher(
                client_id=mqtt_client_id,
                host=mqtt_host,
                port=mqtt_port,
                user=config.mqtt_user,
                password=config.mqtt_password,
                connect_timeout_seconds=self._mqtt_connect_timeout_seconds,
            )
            logger.info(
                "Healthcheck reporter initialized in MQTT mode - topic: %s, client_id: %s",
                mqtt_topic, mqtt_client_id,
            )
        elif mode == "rest":
            if not all([config.api_host, config.api_port, config.api_path]):
                raise ValueError("REST mode requires api_host, api_port and api_path")
            api_host: str = config.api_host  # type: ignore[assignment]
            api_port: int = int(config.api_port)  # type: ignore[arg-type]
            api_path: str = config.api_path  # type: ignore[assignment]
            self._app = create_app(api_path, self.make_report)
            logger.info(
                "Healthcheck reporter initialized in REST mode - host: %s, port: %s, path: /%s",
                api_host, api_port, api_path,
            )
        else:
            raise ValueError("Mode must be 'mqtt' or 'rest'")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        if self._mode == "rest":
            api_host: str = self._config.api_host or "127.0.0.1"
            api_port: int = int(self._config.api_port or 8000)
            self._thread = threading.Thread(
                target=lambda: run_server(self._app, api_host, api_port),
                name="healthcheck-rest-api",
                daemon=True,
            )
        else:
            self._thread = threading.Thread(target=self._run_loop, name="healthcheck-reporter", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=self._interval_seconds + 1.0)
        self._thread = None

    def make_report(self) -> HealthReport:
        # Probe DB
        self._db_attempt_count += 1
        db_ok = probe_postgres_connectivity(
            self._config.database_host,
            int(self._config.database_port),
            self._config.database_name,
            self._config.database_user,
            self._config.database_password,
            self._db_probe_timeout_seconds,
        )
        if not db_ok:
            db_ok: bool = probe_tcp_connectivity(
                self._config.database_host,
                int(self._config.database_port),
                self._db_probe_timeout_seconds,
            )
        if not db_ok:
            self._db_error_count += 1

        # Prepare MQTT attempts
        self._mqtt_attempt_count += 1

        # Debug status override
        debug_status: Optional[str] = None
        if self._debug_mode:
            elapsed: float = time.monotonic() - self._debug_start_time
            cycle_position: float = (elapsed % 10.0) / 10.0
            debug_status = "degraded" if cycle_position < 0.5 else "unavailable"

        uptime_seconds: float = max(0.0, time.monotonic() - self._process_start_time)

        report: HealthReport = build_report(
            db_ok=db_ok,
            mqtt_client_id=self._config.mqtt_client_id or "",
            db_error_count=self._db_error_count,
            db_attempt_count=self._db_attempt_count,
            mqtt_error_count=self._mqtt_error_count,
            mqtt_attempt_count=self._mqtt_attempt_count,
            api_error_count=self._api_error_count,
            api_attempt_count=self._api_attempt_count,
            debug_overall_status=debug_status,
            uptime=uptime_seconds,
        )

        if self._mode == "mqtt" and self._publisher and self._config.mqtt_topic:
            status: int = self._publisher.publish_json(self._config.mqtt_topic, payload=report.to_dict())
            if status != 0:
                self._mqtt_error_count += 1
                logger.error("MQTT publish failed with status %s", status)

        return report

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


