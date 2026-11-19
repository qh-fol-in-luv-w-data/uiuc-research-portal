"""First-run setup used by the `setup` service in docker-compose: one command, ready portal.

1. If the database has no works: restore the prebuilt dump (local file or URL); with no dump
   available, fall back to the full ingest pipeline (needs data/illinois-researchers.csv).
2. Pull missing Ollama models on the configured Ollama server. A missing Ollama is not fatal:
   the portal works and the assistant reports itself offline.
"""
from __future__ import annotations

import gzip
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import httpx
import psycopg


def db_is_empty(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT NOT EXISTS (SELECT 1 FROM works LIMIT 1)")
        empty = bool(cur.fetchone()[0])
    conn.rollback()  # release the lock on `works`: the restore's DROP/ALTER statements need it
    return empty


def dump_source(local: Path, url: str) -> str | None:
    if local.exists() and local.stat().st_size > 0:
        return str(local)
    return url or None


def restore_dump(source: str, database_url: str, http: httpx.Client, log: Callable[[str], None] = print) -> None:
    path = Path(source)
    tmp: Path | None = None
    if source.startswith(("http://", "https://")):
        log(f"downloading database dump from {source}")
        tmp = Path(tempfile.mkstemp(suffix=".sql.gz")[1])
        with http.stream("GET", source, follow_redirects=True, timeout=None) as resp:
            resp.raise_for_status()
            with tmp.open("wb") as fh:
                for chunk in resp.iter_bytes(1 << 20):
                    fh.write(chunk)
        path = tmp
    log("restoring database dump (a few minutes)")
    try:
        proc = subprocess.Popen(["psql", database_url, "-q", "-v", "ON_ERROR_STOP=1", "-o", os.devnull],
                                stdin=subprocess.PIPE)
        assert proc.stdin is not None
        with gzip.open(path, "rb") as src:
            shutil.copyfileobj(src, proc.stdin, 1 << 20)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("psql failed while restoring the dump")
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)


def _installed(required: str, models: list[str]) -> bool:
    return any(m == required or m.split(":")[0] == required for m in models)


def ensure_models(http: httpx.Client, ollama_url: str, models: list[str], log: Callable[[str], None] = print,
                  optional: list[str] | None = None) -> dict:
    """Pull missing models. `optional` ones (the finetuned query model) may fail without stopping setup:
    the assistant then falls back to the chat model with few-shot examples."""
    base = ollama_url.rstrip("/")
    try:
        have = [m["name"] for m in http.get(f"{base}/api/tags", timeout=5).json().get("models", [])]
    except httpx.TransportError:
        log(f"Ollama not reachable at {base}: the portal works, the assistant stays offline until it runs")
        return {"error": f"Ollama not reachable at {base}"}
    pulled, present, failed = [], [], []
    for m in [*models, *(optional or [])]:
        if _installed(m, have):
            present.append(m)
            continue
        log(f"pulling Ollama model {m} (one-time download, can take several minutes)")
        resp = http.post(f"{base}/api/pull", json={"model": m, "stream": False}, timeout=None)
        if resp.status_code >= 400 and m in (optional or []):
            log(f"optional model {m} could not be pulled; the assistant will use its few-shot fallback")
            failed.append(m)
            continue
        resp.raise_for_status()
        pulled.append(m)
    report = {"pulled": pulled, "present": present}
    if optional:
        report["optional_failed"] = failed
    return report


def bootstrap(conn: psycopg.Connection, http: httpx.Client, *, database_url: str, ollama_url: str,
              models: list[str], dump_path: Path, dump_url: str, run_full_ingest: Callable[[], None],
              log: Callable[[str], None] = print, optional_models: list[str] | None = None) -> dict:
    report: dict = {}
    if db_is_empty(conn):
        source = dump_source(dump_path, dump_url)
        if source:
            try:
                restore_dump(source, database_url, http, log)
                report["data"] = f"restored from {source}"
            except (httpx.HTTPError, RuntimeError) as exc:
                log(f"dump unavailable ({exc}); running the full ingest instead")
                source = None
        if not source:
            run_full_ingest()
            report["data"] = "built by full ingest"
    else:
        report["data"] = "already present"
    report["models"] = ensure_models(http, ollama_url, models, log, optional=optional_models)
    return report
