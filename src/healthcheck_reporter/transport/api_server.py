from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from ..core.models import HealthReport


logger: logging.Logger = logging.getLogger(__name__)


def create_app(api_path: str, make_report: Callable[[], HealthReport]) -> FastAPI:
    app = FastAPI(title="Health Check API")

    @app.get(f"/{api_path}")
    async def health_endpoint(request: Request) -> JSONResponse:
        report: HealthReport = make_report()
        return JSONResponse(content=report.to_dict())

    return app


def run_server(app: FastAPI, host: str, port: int) -> None:
    try:
        uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)
    except Exception as exc:
        logger.exception("REST API server crashed: %s", exc)


