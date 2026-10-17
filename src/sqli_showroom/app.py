"""Application factory; test instances never share database paths or CSRF tokens."""

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from . import __version__, database, vulnerable_lab
from .boundary import LocalBoundary, error_response
from .models import (
    EXAMPLES,
    ConfigResponse,
    ErrorDetail,
    Example,
    HealthResponse,
    ResetRequest,
    ResetResponse,
    SearchRequest,
    SearchResponse,
)


def database_path() -> Path:
    return Path(os.environ.get("SQLI_SHOWROOM_DB", ".demo-data/showroom.sqlite3")).resolve()


def create_app(path: Path | None = None) -> FastAPI:
    db_path = (path if path is not None else database_path()).resolve()
    csrf_token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize(db_path)
        yield

    app = FastAPI(title="SQL-injection-showroom", version=__version__, lifespan=lifespan)
    app.add_middleware(LocalBoundary)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        return error_response(
            422, "invalid_request", "Check JSON fields and the 256-character limit."
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(
            exc.status_code, "http_error", "Requested operation is unavailable."
        )

    @app.get("/health", response_model=HealthResponse)
    def health():
        return HealthResponse()

    @app.get("/api/examples", response_model=list[Example])
    def examples():
        return EXAMPLES

    @app.get("/api/config", response_model=ConfigResponse)
    def config():
        return ConfigResponse(csrf_token=csrf_token)

    @app.post("/api/search/vulnerable", response_model=SearchResponse)
    def vulnerable(payload: SearchRequest):
        sql, rows, failed = vulnerable_lab.search_vulnerable(db_path, payload.query)
        return SearchResponse(
            sql=sql,
            parameters=[],
            rows=rows,
            error=ErrorDetail(
                code="invalid_demo_sql",
                message=(
                    "The constructed SQL could not run. "
                    "Input changed its syntax or exceeded the lab budget."
                ),
            )
            if failed
            else None,
        )

    @app.post("/api/search/fixed", response_model=SearchResponse)
    def fixed(payload: SearchRequest):
        sql, parameters, rows = database.search_fixed(db_path, payload.query)
        return SearchResponse(sql=sql, parameters=parameters, rows=rows)

    @app.post("/api/reset", response_model=ResetResponse)
    def reset(payload: ResetRequest, request: Request):
        supplied = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(supplied.encode(), csrf_token.encode()):
            return error_response(
                403, "invalid_csrf", "Reset requires the current local UI token."
            )
        database.reset(db_path)
        return ResetResponse()

    return app
