from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import uvicorn

from ..core.models import HealthReport
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    CONTENT_TYPE_LATEST,
    generate_latest,
)


logger: logging.Logger = logging.getLogger(__name__)


def create_app(api_path: str, make_report: Callable[[], HealthReport]) -> FastAPI:
    app = FastAPI(title="Health Check API")

    # Prometheus registry and metrics
    registry: CollectorRegistry = CollectorRegistry()
    g_db_ok: Gauge = Gauge("healthcheck_database_ok", "Database connectivity (1 ok, 0 failed)", registry=registry)
    g_db_error_count: Gauge = Gauge("healthcheck_db_error_count", "DB error count", registry=registry)
    g_mqtt_error_count: Gauge = Gauge("healthcheck_mqtt_error_count", "MQTT error count", registry=registry)
    g_api_error_count: Gauge = Gauge("healthcheck_api_error_count", "API error count", registry=registry)
    g_db_failure_rate: Gauge = Gauge(
        "healthcheck_db_failure_rate_percent", "DB failure rate percent", registry=registry
    )
    g_mqtt_failure_rate: Gauge = Gauge(
        "healthcheck_mqtt_failure_rate_percent", "MQTT failure rate percent", registry=registry
    )
    g_api_failure_rate: Gauge = Gauge(
        "healthcheck_api_failure_rate_percent", "API failure rate percent", registry=registry
    )
    g_uptime_seconds: Gauge = Gauge("healthcheck_uptime_seconds", "Process uptime seconds", registry=registry)
    g_overall_status: Gauge = Gauge(
        "healthcheck_overall_status", "Overall status as labeled gauge", ["status"], registry=registry
    )

    @app.get(f"/{api_path}")
    async def health_endpoint(request: Request) -> JSONResponse:
        report: HealthReport = make_report()
        return JSONResponse(content=report.to_dict())

    @app.get("/metrics")
    async def metrics_endpoint() -> Response:
        # Refresh metrics from current report
        report: HealthReport = make_report()
        data = report.to_dict()

        g_db_ok.set(1.0 if report.db_ok else 0.0)
        g_db_error_count.set(report.db_error_count)
        g_mqtt_error_count.set(report.mqtt_error_count)
        g_api_error_count.set(report.api_error_count)
        g_db_failure_rate.set(float(data.get("db_failure_rate", 0.0)))
        g_mqtt_failure_rate.set(float(data.get("mqtt_failure_rate", 0.0)))
        g_api_failure_rate.set(float(data.get("api_failure_rate", 0.0)))
        g_uptime_seconds.set(float(data.get("uptime", 0.0)))

        # Set overall status (1 for the current status label)
        status: str = str(data.get("overall_status", "unknown"))
        g_overall_status.labels(status=status).set(1)

        output: bytes = generate_latest(registry)
        return Response(content=output, media_type=CONTENT_TYPE_LATEST)

    return app


def run_server(app: FastAPI, host: str, port: int) -> None:
    try:
        uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)
    except Exception as exc:
        logger.exception("REST API server crashed: %s", exc)


