from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from ..core.models import HealthReport


logger: logging.Logger = logging.getLogger(__name__)


def create_app(api_path: str, make_report: Callable[[], HealthReport]) -> FastAPI:
    app = FastAPI(title="Health Check API")

    @app.get(f"/{api_path}")
    async def health_endpoint() -> JSONResponse:
        report: HealthReport = make_report()
        return JSONResponse(content={
            "database_status": report.database_status,
            "mqtt_client_id": report.mqtt_client_id,
            "timestamp": report.timestamp,
            "db_error_count": report.db_error_count,
            "mqtt_error_count": report.mqtt_error_count,
            "db_failure_rate": report.db_failure_rate,
            "mqtt_failure_rate": report.mqtt_failure_rate,
            "overall_status": report.overall_status,
            "api_error_count": report.api_error_count,
            "api_failure_rate": report.api_failure_rate,
        })

    return app


def run_server(app: FastAPI, host: str, port: int) -> None:
    try:
        uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)
    except Exception as exc:
        logger.exception("REST API server crashed: %s", exc)


