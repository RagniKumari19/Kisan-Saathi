"""FastAPI application factory."""
from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.errors import AppError, app_error_handler, error_body, unhandled_error_handler
from app.core.migrate import upgrade_database
from app.routers import admin, auth, calendar, crops, disease, markets, soil, system, users, weather
from app.seed import seed_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("app")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(upgrade_database)
    async with SessionLocal() as db:
        await seed_all(db)
    log.info("database ready; reference data seeded")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    dist = Path(__file__).resolve().parents[2] / "web" / "dist"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return await app_error_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e.get("loc", []) if p not in ("body", "query")),
             "issue": e.get("msg", "invalid value")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=400, content=error_body(
            "VALIDATION_ERROR", "One or more fields are invalid.", details,
            getattr(request.state, "request_id", ""),
        ))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        path = request.url.path
        if (exc.status_code == 404 and (dist / "index.html").exists()
                and not path.startswith(("/api", "/media"))):
            return FileResponse(dist / "index.html")
        code = {401: "AUTH_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
                409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE",
                429: "RATE_LIMITED"}.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(status_code=exc.status_code, content=error_body(
            code, message, None, getattr(request.state, "request_id", ""),
        ))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error", exc_info=exc)
        return await unhandled_error_handler(request, exc)

    for module in (auth, users, soil, weather, crops, disease, markets, admin, system, calendar):
        app.include_router(module.router, prefix=API_PREFIX)

    @app.get("/healthz", include_in_schema=False)
    async def root_healthz():
        return {"status": "ok"}

    media = Path(settings.storage_dir)
    media.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media), name="media")

    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
        log.info("serving built web app from %s", dist)

    return app


app = create_app()
