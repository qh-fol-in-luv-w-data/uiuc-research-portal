from __future__ import annotations

import asyncio

import os
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from .ollama import OllamaTags
from .chat.config import ChatConfig
from .chat.ollama import Ollama
from .routers import chat, faculty, health, stats, works

ROOT = Path(__file__).resolve().parents[3]
ERROR_CODES = {400: "bad_request", 404: "not_found", 422: "invalid_request", 429: "busy", 503: "unavailable"}


def create_app(database_url: str | None = None, institution_path: Path | None = None, ollama=None,
               chat_ollama=None) -> FastAPI:
    database_url = database_url or os.environ.get("DATABASE_URL", "postgresql://portal:portal@localhost:55432/portal")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # read-only sessions: the API never writes, so even a successful injection could not change data
        pool = ConnectionPool(database_url, min_size=1, max_size=10, configure=register_vector, open=True,
                              kwargs={"options": "-c default_transaction_read_only=on"})
        app.state.pool = pool
        try:
            yield
        finally:
            pool.close()

    app = FastAPI(title="UIUC Research Portal API", version="0.1.0", lifespan=lifespan)
    app.state.institution_path = institution_path or ROOT / "data" / "institution.json"
    app.state.ollama = ollama or OllamaTags(os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    app.state.chat_cfg = ChatConfig()
    cfg = app.state.chat_cfg
    app.state.chat_ollama = chat_ollama or Ollama(
        cfg.ollama_url, keep_alive=cfg.keep_alive,
        # chat model last: if the QU and chat model are the same, they share one context size (no reloads)
        num_ctx={cfg.qu_model: cfg.qu_num_ctx, cfg.embed_model: cfg.embed_num_ctx, cfg.chat_model: cfg.chat_num_ctx})
    app.state.faculty_index = None
    app.state.chat_slots = asyncio.Semaphore(cfg.max_concurrent)
    app.state.required_models = [app.state.chat_cfg.chat_model, app.state.chat_cfg.embed_model]

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content={"error": ERROR_CODES.get(exc.status_code, "error"), "detail": str(exc.detail)})

    @app.middleware("http")
    async def reject_nul(request: Request, call_next):
        # Postgres text cannot hold NUL bytes; reject them up front instead of failing inside a query
        if "%00" in request.url.query or "\x00" in request.url.path:
            return JSONResponse(status_code=400, content={"error": "bad_request", "detail": "NUL bytes are not allowed."})
        return await call_next(request)

    @app.exception_handler(psycopg.DataError)
    async def data_error(_: Request, exc: psycopg.DataError):
        return JSONResponse(status_code=400, content={"error": "bad_request", "detail": "Invalid characters in the request."})

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):  # never leak internals (SQL, paths) to clients
        return JSONResponse(status_code=500, content={"error": "internal", "detail": "Unexpected server error."})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []))
        return JSONResponse(status_code=422, content={"error": "invalid_request",
                                                      "detail": f"{where}: {first.get('msg', 'invalid')}"})

    for router in (health.router, stats.router, works.router, faculty.router, chat.router):
        app.include_router(router)
    return app


app = create_app() if os.environ.get("PORTAL_API_AUTOCREATE", "1") == "1" else None
