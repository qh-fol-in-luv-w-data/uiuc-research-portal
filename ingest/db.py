from __future__ import annotations

from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from .config import ROOT

MIGRATIONS_DIR = ROOT / "db" / "migrations"


def connect(url: str) -> psycopg.Connection:
    conn = psycopg.connect(url, autocommit=False)
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    return conn


def apply_migrations(conn: psycopg.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    applied: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        cur.execute("SELECT name FROM schema_migrations")
        done = {row[0] for row in cur.fetchall()}
        for path in sorted(migrations_dir.glob("*.sql")):
            if path.name in done:
                continue
            cur.execute(path.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            applied.append(path.name)
    conn.commit()
    return applied


def put_stat(conn: psycopg.Connection, key: str, payload: object) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO stats_cache (key, payload, computed_at) VALUES (%s, %s, now())"
            " ON CONFLICT (key) DO UPDATE SET payload = EXCLUDED.payload, computed_at = now()",
            (key, Jsonb(payload)),
        )
    conn.commit()


def get_stat(conn: psycopg.Connection, key: str) -> object | None:
    with conn.cursor() as cur:
        cur.execute("SELECT payload FROM stats_cache WHERE key = %s", (key,))
        row = cur.fetchone()
    return row[0] if row else None
