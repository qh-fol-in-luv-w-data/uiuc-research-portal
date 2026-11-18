from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from .ollama import OllamaTags
from .routers import faculty, health, stats, works

ROOT = Path(__file__).resolve().parents[3]
ERROR_CODES = {400: "bad_request", 404: "not_found", 422: "invalid_request", 503: "unavailable"}


def create_app(database_url: str | None = None, institution_path: Path | None = None, ollama=None) -> FastAPI:
    database_url = database_url or os.environ.get("DATABASE_URL", "postgresql://portal:portal@localhost:55432/portal")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = ConnectionPool(database_url, min_size=1, max_size=10, configure=register_vector, open=True)
        app.state.pool = pool
        try:
            yield
        finally:
            pool.close()

    app = FastAPI(title="UIUC Research Portal API", version="0.1.0", lifespan=lifespan)
    app.state.institution_path = institution_path or ROOT / "data" / "institution.json"
    app.state.ollama = ollama or OllamaTags(os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    app.state.required_models = [os.environ.get("OLLAMA_CHAT_MODEL", "qwen3:4b"),
                                 os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3")]

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content={"error": ERROR_CODES.get(exc.status_code, "error"), "detail": str(exc.detail)})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []))
        return JSONResponse(status_code=422, content={"error": "invalid_request",
                                                      "detail": f"{where}: {first.get('msg', 'invalid')}"})

    for router in (health.router, stats.router, works.router, faculty.router):
        app.include_router(router)
    return app


app = create_app() if os.environ.get("PORTAL_API_AUTOCREATE", "1") == "1" else None
