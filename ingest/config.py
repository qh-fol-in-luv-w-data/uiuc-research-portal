from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_url: str
    ollama_url: str
    embed_model: str
    openalex_api_key: str | None
    openalex_mailto: str | None
    cache_dir: Path
    data_dir: Path
    docs_dir: Path


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgresql://portal:portal@localhost:55432/portal"),
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        embed_model=os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3"),
        openalex_api_key=os.environ.get("OPENALEX_API_KEY") or None,
        openalex_mailto=os.environ.get("OPENALEX_MAILTO") or None,
        cache_dir=Path(os.environ.get("INGEST_CACHE_DIR", str(ROOT / "ingest" / ".cache"))),
        data_dir=ROOT / "data",
        docs_dir=ROOT / "docs",
    )
