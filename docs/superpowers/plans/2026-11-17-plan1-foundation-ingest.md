# Plan 1 — Foundation & Ingest Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a Postgres + pgvector database populated with cleaned UIUC works from OpenAlex (last 2 years), cleaned faculty from the CSV, faculty↔author links, embeddings and portal statistics — reproducible with `uv run python -m ingest all` and dumpable for graders.

**Architecture:** A Python package `ingest/` with one module per pipeline concern (OpenAlex client, work cleaning, faculty cleaning, name matching, linking, embedding, aggregation) and a thin argparse CLI. Pure functions are unit-tested; DB-touching functions are tested against a disposable `portal_test` database in the same Docker Postgres. OpenAlex pages are cached on disk so reruns cost nothing.

**Tech Stack:** Python 3.11, uv, httpx, psycopg 3, pgvector (Python + extension), numpy, unidecode, PyYAML, pytest; Postgres 16 + pgvector via Docker (`pgvector/pgvector:pg16`); Ollama on host with `bge-m3`.

**Spec:** `docs/superpowers/specs/2026-11-16-uiuc-research-portal-design.md` (rev 2) — §2, §4, §5, §9 (ingest part), §11 (compose/Makefile/env part).

**Later plans (not in this file):** Plan 2 — API, retrieval, chat, eval/tune, mock system tests. Plan 3 — Next.js web. Plan 4 — LoRA finetune of query understanding (spec §13).

## Global Constraints

- UIUC OpenAlex institution id `I157725225`; University of Illinois System `I2801919071` (excluded from partner stats).
- Works window: `from_publication_date = today − 2 years`, filter `institutions.id:I157725225`.
- Embedding model `bge-m3`, dimension **1024**; Ollama at `OLLAMA_URL` (default `http://localhost:11434`; containers use `http://host.docker.internal:11434`).
- Postgres exposed on host port **5433** (Homebrew Postgres 15 already uses 5432). DB `portal`, user/password `portal/portal`; test DB `portal_test`.
- Do **not** use OpenAlex `search` per faculty. Only list `/works` with `cursor=*`, `per_page=200`, `select=`.
- `OPENALEX_API_KEY` and `OPENALEX_MAILTO` are optional and default empty; never hard-code an email.
- Every ingest step is idempotent and re-runnable.
- Outliers are never deleted: `is_outlier=true` + `outlier_reason`.
- Do not cap works by citation. Cap only if > 25,000 after filtering, keeping newest by `publication_date`.
- Name-link confidence base: exact 0.9, first_last 0.75, initial_last 0.6; no link below 0.5.

## File Structure

```
pyproject.toml                 uv project, deps, pytest config
.env.example                   env vars (spec §11)
.gitignore
docker-compose.yml             db service only in this plan
Makefile                       db-up, migrate, ingest, test, dump, restore
db/init/00-test-db.sql         creates portal_test on first container start
db/migrations/001_schema.sql   all tables + indexes (spec §4)
data/illinois-researchers.csv  (already present)
data/keyword_stoplist.txt      always-drop keywords
data/keyword_generic.txt       drop only for faculty with >200 keywords
ingest/__init__.py
ingest/__main__.py             argparse CLI
ingest/config.py               Settings from env
ingest/db.py                   connect, apply_migrations, put_stat
ingest/openalex.py             OpenAlexClient (retry, quota stop, page cache), filter helpers
ingest/works.py                pure: abstract rebuild, drop_reason, parse_work, mark_outliers, cap_by_date
ingest/load_works.py           upsert parsed works into DB, clean-works command
ingest/faculty.py              pure: parse_pg_array, normalize/clean keywords; load_faculty command
ingest/names.py                pure: normalize_name, name_keys, AuthorIndex, link_confidence
ingest/embedder.py             OllamaEmbedder
ingest/linking.py              find_candidates, embed_profiles, link_faculty
ingest/embed.py                embed_works, embed_faculty
ingest/aggregate.py            compute + store stats, render docs/data-quality.md
tests/conftest.py              db fixture (fresh schema per test)
tests/factories.py             make_work() builder for OpenAlex-shaped dicts
tests/test_*.py                one file per module
```

---

### Task 1: Project scaffold, Postgres, schema migration

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `docker-compose.yml`, `Makefile`, `db/init/00-test-db.sql`, `db/migrations/001_schema.sql`, `ingest/__init__.py`, `ingest/config.py`, `ingest/db.py`, `tests/__init__.py`, `tests/conftest.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces: `ingest.config.ROOT: Path`, `ingest.config.Settings`, `ingest.config.load_settings() -> Settings`; `ingest.db.connect(url: str) -> psycopg.Connection`; `ingest.db.apply_migrations(conn, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]`; `ingest.db.put_stat(conn, key: str, payload: object) -> None`; `ingest.db.get_stat(conn, key: str) -> object | None`; pytest fixture `db` (open connection on a freshly migrated `portal_test`).

- [ ] **Step 1: Write project files**

`pyproject.toml`:
```toml
[project]
name = "uiuc-portal"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = [
  "httpx>=0.27",
  "psycopg[binary]>=3.2",
  "pgvector>=0.3",
  "numpy>=1.26",
  "unidecode>=1.3",
  "pyyaml>=6.0",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`.gitignore`:
```
.venv/
__pycache__/
.pytest_cache/
ingest/.cache/
.env
node_modules/
.next/
finetune/models/
```

`.env.example`:
```
DATABASE_URL=postgresql://portal:portal@localhost:5433/portal
TEST_DATABASE_URL=postgresql://portal:portal@localhost:5433/portal_test
OLLAMA_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen3:4b
OLLAMA_EMBED_MODEL=bge-m3
OLLAMA_QU_MODEL=
RERANK_ENABLED=false
OPENALEX_API_KEY=
OPENALEX_MAILTO=
```

`docker-compose.yml`:
```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: portal
      POSTGRES_PASSWORD: portal
      POSTGRES_DB: portal
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U portal -d portal"]
      interval: 5s
      timeout: 3s
      retries: 20
volumes:
  pgdata: {}
```

`db/init/00-test-db.sql`:
```sql
CREATE DATABASE portal_test;
```

`Makefile` (recipe lines start with a TAB):
```make
.PHONY: db-up migrate ingest test dump restore

db-up:
	docker compose up -d --wait db

migrate:
	uv run python -m ingest migrate

ingest:
	uv run python -m ingest all

test:
	uv run pytest -q

dump:
	mkdir -p db/dump
	docker compose exec -T db pg_dump -U portal --no-owner --clean --if-exists portal | gzip > db/dump/portal.sql.gz

restore:
	gunzip -c db/dump/portal.sql.gz | docker compose exec -T db psql -U portal -d portal -q
```

`db/migrations/001_schema.sql`:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE topics (
  id text PRIMARY KEY,
  display_name text NOT NULL,
  subfield text,
  field text,
  domain text
);

CREATE TABLE institutions (
  id text PRIMARY KEY,
  display_name text,
  country_code text,
  type text
);

CREATE TABLE authors (
  id text PRIMARY KEY,
  display_name text NOT NULL,
  orcid text,
  works_count_in_set integer NOT NULL DEFAULT 0
);

CREATE TABLE works (
  id text PRIMARY KEY,
  doi text,
  title text NOT NULL,
  abstract text,
  publication_date date,
  type text,
  language text,
  cited_by_count integer NOT NULL DEFAULT 0,
  is_oa boolean NOT NULL DEFAULT false,
  oa_url text,
  venue_name text,
  venue_type text,
  primary_topic_id text REFERENCES topics(id),
  is_outlier boolean NOT NULL DEFAULT false,
  outlier_reason text,
  tsv tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(abstract, '')), 'B')
  ) STORED,
  embedding vector(1024)
);

CREATE TABLE authorships (
  work_id text NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  author_id text NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
  position text,
  is_uiuc boolean NOT NULL DEFAULT false,
  raw_affiliation text,
  PRIMARY KEY (work_id, author_id)
);

CREATE TABLE work_institutions (
  work_id text NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  institution_id text NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  PRIMARY KEY (work_id, institution_id)
);

CREATE TABLE work_topics (
  work_id text NOT NULL REFERENCES works(id) ON DELETE CASCADE,
  topic_id text NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  score real,
  PRIMARY KEY (work_id, topic_id)
);

CREATE TABLE faculty (
  id serial PRIMARY KEY,
  email text NOT NULL UNIQUE,
  name text NOT NULL,
  photo_url text,
  position text,
  keywords_raw text[] NOT NULL DEFAULT '{}',
  keywords text[] NOT NULL DEFAULT '{}',
  keywords_text text NOT NULL DEFAULT '',
  primary_field text,
  tsv tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', keywords_text), 'A') ||
    setweight(to_tsvector('english', coalesce(name, '')), 'B')
  ) STORED,
  keyword_embedding vector(1024),
  embedding vector(1024)
);

CREATE TABLE author_profile (
  author_id text PRIMARY KEY REFERENCES authors(id) ON DELETE CASCADE,
  profile_text text NOT NULL,
  embedding vector(1024) NOT NULL
);

CREATE TABLE faculty_author_link (
  faculty_id integer NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
  author_id text NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
  confidence real NOT NULL,
  method text NOT NULL,
  PRIMARY KEY (faculty_id, author_id)
);

CREATE TABLE stats_cache (
  key text PRIMARY KEY,
  payload jsonb NOT NULL,
  computed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX works_tsv_idx ON works USING gin (tsv);
CREATE INDEX works_embedding_idx ON works USING hnsw (embedding vector_cosine_ops);
CREATE INDEX works_pubdate_idx ON works (publication_date);
CREATE INDEX works_cited_idx ON works (cited_by_count);
CREATE INDEX works_primary_topic_idx ON works (primary_topic_id);
CREATE INDEX authorships_author_idx ON authorships (author_id);
CREATE INDEX work_institutions_inst_idx ON work_institutions (institution_id);
CREATE INDEX work_topics_topic_idx ON work_topics (topic_id);
CREATE INDEX faculty_tsv_idx ON faculty USING gin (tsv);
CREATE INDEX faculty_embedding_idx ON faculty USING hnsw (embedding vector_cosine_ops);
```

`ingest/__init__.py` and `tests/__init__.py`: empty files.

`ingest/config.py`:
```python
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
        database_url=os.environ.get("DATABASE_URL", "postgresql://portal:portal@localhost:5433/portal"),
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        embed_model=os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3"),
        openalex_api_key=os.environ.get("OPENALEX_API_KEY") or None,
        openalex_mailto=os.environ.get("OPENALEX_MAILTO") or None,
        cache_dir=Path(os.environ.get("INGEST_CACHE_DIR", str(ROOT / "ingest" / ".cache"))),
        data_dir=ROOT / "data",
        docs_dir=ROOT / "docs",
    )
```

`ingest/db.py`:
```python
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
```

`tests/conftest.py`:
```python
import os

import pytest

from ingest.db import apply_migrations, connect

TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://portal:portal@localhost:5433/portal_test")


@pytest.fixture
def db():
    conn = connect(TEST_URL)
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    conn.close()
    conn = connect(TEST_URL)
    apply_migrations(conn)
    yield conn
    conn.rollback()
    conn.close()
```

- [ ] **Step 2: Write the failing test** — `tests/test_db.py`
```python
from ingest.db import apply_migrations, get_stat, put_stat


def test_schema_has_all_tables(db):
    with db.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = {r[0] for r in cur.fetchall()}
    assert {
        "works", "authors", "authorships", "institutions", "work_institutions", "topics",
        "work_topics", "faculty", "author_profile", "faculty_author_link", "stats_cache",
        "schema_migrations",
    } <= tables


def test_migrations_are_idempotent(db):
    assert apply_migrations(db) == []


def test_put_and_get_stat_roundtrip(db):
    put_stat(db, "k", {"a": [1, 2]})
    put_stat(db, "k", {"a": [3]})
    assert get_stat(db, "k") == {"a": [3]}
    assert get_stat(db, "missing") is None
```

- [ ] **Step 3: Start DB and install deps**

Run: `docker compose up -d --wait db && uv sync`
Expected: container `db` healthy; `.venv` created.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_db.py -v`
Expected: 3 passed. (If `portal_test` missing because the volume pre-existed: `docker compose exec db psql -U portal -c "CREATE DATABASE portal_test"`.)

- [ ] **Step 5: Commit**
```bash
git add pyproject.toml uv.lock .gitignore .env.example docker-compose.yml Makefile db ingest tests docs data/illinois-researchers.csv
git commit -m "chore: scaffold ingest project, postgres+pgvector schema"
```

---

### Task 2: Work cleaning (pure functions)

**Files:**
- Create: `ingest/works.py`, `tests/factories.py`
- Test: `tests/test_works.py`

**Interfaces:**
- Consumes: nothing.
- Produces (in `ingest/works.py`): `UIUC_ID = "I157725225"`, `UI_SYSTEM_ID = "I2801919071"`, `KEEP_TYPES`, `short_id(url: str | None) -> str | None`, `rebuild_abstract(inv: dict | None) -> str | None`, `drop_reason(work: dict) -> str | None`, `@dataclass ParsedWork(work: dict, authors: list[dict], authorships: list[dict], institutions: list[dict], work_institutions: list[str], topics: list[dict], work_topics: list[tuple[str, float]])`, `parse_work(work: dict) -> ParsedWork`, `mark_outliers(items: list[ParsedWork]) -> dict[str, int]`, `cap_by_date(items: list[ParsedWork], limit: int = 25000) -> list[ParsedWork]`.
- Produces (in `tests/factories.py`): `make_work(**overrides) -> dict` OpenAlex-shaped work.

- [ ] **Step 1: Write the test factory** — `tests/factories.py`
```python
UIUC = {"id": "https://openalex.org/I157725225", "display_name": "University of Illinois Urbana-Champaign",
        "country_code": "US", "type": "education"}
UISYS = {"id": "https://openalex.org/I2801919071", "display_name": "University of Illinois System",
         "country_code": "US", "type": "education"}
HERZEN = {"id": "https://openalex.org/I999", "display_name": "Herzen University", "country_code": "RU",
          "type": "education"}


def make_author(aid: str, name: str, institutions: list[dict], raw: str, position: str = "first") -> dict:
    return {
        "author_position": position,
        "author": {"id": f"https://openalex.org/{aid}", "display_name": name, "orcid": None},
        "institutions": institutions,
        "raw_affiliation_strings": [raw],
    }


def make_topic(tid="T1", name="Computer Vision", subfield="Computer Vision and Pattern Recognition",
               field="Computer Science", domain="Physical Sciences", score=0.9) -> dict:
    return {"id": f"https://openalex.org/{tid}", "display_name": name, "score": score,
            "subfield": {"display_name": subfield}, "field": {"display_name": field},
            "domain": {"display_name": domain}}


def make_work(id="W1", title="Deep learning for drone detection", type="article", language="en", cited=10,
              date="2025-06-01", authorships=None, abstract=None, topic=None, source_type="journal",
              venue="Venue X", retracted=False, paratext=False, is_oa=True) -> dict:
    if authorships is None:
        authorships = [make_author("A1", "John A. Smith", [UIUC], "University of Illinois Urbana-Champaign")]
    if abstract is None:
        abstract = {"Deep": [0], "learning": [1], "works": [2]}
    t = topic or make_topic()
    return {
        "id": f"https://openalex.org/{id}", "doi": f"https://doi.org/10.1/{id}", "title": title,
        "publication_date": date, "type": type, "language": language, "cited_by_count": cited,
        "open_access": {"is_oa": is_oa, "oa_url": "https://example.org/x.pdf" if is_oa else None},
        "primary_location": {"source": {"display_name": venue, "type": source_type}},
        "primary_topic": t, "topics": [t], "authorships": authorships,
        "is_retracted": retracted, "is_paratext": paratext, "abstract_inverted_index": abstract,
    }
```

- [ ] **Step 2: Write the failing tests** — `tests/test_works.py`
```python
from ingest.works import cap_by_date, drop_reason, mark_outliers, parse_work, rebuild_abstract, short_id
from tests.factories import HERZEN, UIUC, make_author, make_work


def test_short_id():
    assert short_id("https://openalex.org/W123") == "W123"
    assert short_id(None) is None


def test_rebuild_abstract_orders_by_position():
    assert rebuild_abstract({"world": [1], "hello": [0, 2]}) == "hello world hello"
    assert rebuild_abstract(None) is None
    assert rebuild_abstract({}) is None


def test_drop_reason():
    assert drop_reason(make_work()) is None
    assert drop_reason(make_work(retracted=True)) == "retracted"
    assert drop_reason(make_work(paratext=True)) == "paratext"
    assert drop_reason(make_work(title="  ")) == "no_title"
    assert drop_reason(make_work(type="erratum")) == "type:erratum"
    assert drop_reason(make_work(type="other", source_type="conference")) is None
    assert drop_reason(make_work(type="preprint")) is None


def test_parse_work_maps_tables():
    w = make_work(authorships=[
        make_author("A1", "John A. Smith", [UIUC], "UIUC"),
        make_author("A2", "Ivan Petrov", [HERZEN], "Herzen University", position="last"),
        make_author("A2", "Ivan Petrov", [HERZEN], "dup", position="last"),
    ])
    p = parse_work(w)
    assert p.work["id"] == "W1"
    assert p.work["abstract"] == "Deep learning works"
    assert p.work["primary_topic_id"] == "T1"
    assert p.work["venue_type"] == "journal"
    assert [a["author_id"] for a in p.authorships] == ["A1", "A2"]
    assert p.authorships[0]["is_uiuc"] is True and p.authorships[1]["is_uiuc"] is False
    assert sorted(p.work_institutions) == ["I157725225", "I999"]
    assert p.work_topics == [("T1", 0.9)]
    assert p.topics[0]["field"] == "Computer Science"


def test_mark_outliers_flags_non_english_top_citation_and_missing_affiliation():
    items = [parse_work(make_work(id=f"W{i}", cited=i)) for i in range(1, 201)]
    ru = parse_work(make_work(id="WRU", language="ru", cited=8198, authorships=[
        make_author("A9", "Ниводничева М. Р.", [UIUC, HERZEN], "Herzen; University of Illinois")]))
    stray = parse_work(make_work(id="WX", authorships=[make_author("A8", "X Y", [HERZEN], "Herzen University")]))
    mention = parse_work(make_work(id="WM", authorships=[
        make_author("A7", "Z Q", [HERZEN], "Dept of CS, University of Illinois")]))
    counts = mark_outliers(items + [ru, stray, mention])
    assert ru.work["is_outlier"] and ru.work["outlier_reason"] == "non_english_high_citation"
    assert stray.work["is_outlier"] and stray.work["outlier_reason"] == "no_uiuc_affiliation"
    assert not mention.work["is_outlier"]
    assert not items[-1].work["is_outlier"]  # top English paper is not an outlier
    assert counts == {"no_uiuc_affiliation": 1, "non_english_high_citation": 1}


def test_cap_by_date_keeps_newest():
    items = [parse_work(make_work(id="W1", date="2024-01-01")),
             parse_work(make_work(id="W2", date="2025-01-01")),
             parse_work(make_work(id="W3", date=None))]
    assert [p.work["id"] for p in cap_by_date(items, limit=1)] == ["W2"]
    assert len(cap_by_date(items, limit=10)) == 3
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_works.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest.works'`.

- [ ] **Step 4: Implement** — `ingest/works.py`
```python
from __future__ import annotations

from dataclasses import dataclass, field

UIUC_ID = "I157725225"
UI_SYSTEM_ID = "I2801919071"
KEEP_TYPES = {"article", "preprint", "review", "book-chapter"}


def short_id(url: str | None) -> str | None:
    if not url:
        return None
    return url.rstrip("/").rsplit("/", 1)[-1]


def rebuild_abstract(inv: dict | None) -> str | None:
    if not inv:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            positions[i] = word
    text = " ".join(positions[i] for i in sorted(positions))
    return text or None


def _source(work: dict) -> dict:
    return ((work.get("primary_location") or {}).get("source")) or {}


def drop_reason(work: dict) -> str | None:
    if work.get("is_retracted"):
        return "retracted"
    if work.get("is_paratext"):
        return "paratext"
    if not (work.get("title") or "").strip():
        return "no_title"
    if work.get("type") in KEEP_TYPES or _source(work).get("type") == "conference":
        return None
    return f"type:{work.get('type')}"


@dataclass
class ParsedWork:
    work: dict
    authors: list[dict] = field(default_factory=list)
    authorships: list[dict] = field(default_factory=list)
    institutions: list[dict] = field(default_factory=list)
    work_institutions: list[str] = field(default_factory=list)
    topics: list[dict] = field(default_factory=list)
    work_topics: list[tuple[str, float]] = field(default_factory=list)


def _topic_row(t: dict) -> dict:
    return {
        "id": short_id(t.get("id")),
        "display_name": t.get("display_name") or "",
        "subfield": (t.get("subfield") or {}).get("display_name"),
        "field": (t.get("field") or {}).get("display_name"),
        "domain": (t.get("domain") or {}).get("display_name"),
    }


def parse_work(w: dict) -> ParsedWork:
    wid = short_id(w["id"])
    src = _source(w)
    oa = w.get("open_access") or {}
    pt = w.get("primary_topic") or {}
    p = ParsedWork(work={
        "id": wid,
        "doi": w.get("doi"),
        "title": (w.get("title") or "").strip(),
        "abstract": rebuild_abstract(w.get("abstract_inverted_index")),
        "publication_date": w.get("publication_date"),
        "type": w.get("type"),
        "language": w.get("language"),
        "cited_by_count": int(w.get("cited_by_count") or 0),
        "is_oa": bool(oa.get("is_oa")),
        "oa_url": oa.get("oa_url"),
        "venue_name": src.get("display_name"),
        "venue_type": src.get("type"),
        "primary_topic_id": short_id(pt.get("id")),
        "is_outlier": False,
        "outlier_reason": None,
    })
    insts: dict[str, dict] = {}
    seen: set[str] = set()
    for a in w.get("authorships") or []:
        au = a.get("author") or {}
        aid = short_id(au.get("id"))
        if not aid or aid in seen:
            continue
        seen.add(aid)
        inst_ids = []
        for i in a.get("institutions") or []:
            iid = short_id(i.get("id"))
            if not iid:
                continue
            inst_ids.append(iid)
            insts[iid] = {"id": iid, "display_name": i.get("display_name"),
                          "country_code": i.get("country_code"), "type": i.get("type")}
        p.authors.append({"id": aid, "display_name": au.get("display_name") or "", "orcid": au.get("orcid")})
        p.authorships.append({
            "work_id": wid, "author_id": aid, "position": a.get("author_position"),
            "is_uiuc": UIUC_ID in inst_ids,
            "raw_affiliation": "; ".join(a.get("raw_affiliation_strings") or []) or None,
        })
    p.institutions = list(insts.values())
    p.work_institutions = list(insts.keys())
    seen_topics: set[str] = set()
    for t in list(w.get("topics") or []) + ([pt] if pt else []):
        row = _topic_row(t)
        if not row["id"] or row["id"] in seen_topics:
            continue
        seen_topics.add(row["id"])
        p.topics.append(row)
        p.work_topics.append((row["id"], float(t.get("score") or 0.0)))
    return p


def mark_outliers(items: list[ParsedWork]) -> dict[str, int]:
    counts = {"no_uiuc_affiliation": 0, "non_english_high_citation": 0}
    cites = sorted(p.work["cited_by_count"] for p in items)
    p99 = cites[int(0.99 * (len(cites) - 1))] if cites else 0
    for p in items:
        has_uiuc = any(a["is_uiuc"] for a in p.authorships)
        mentions = any("illinois" in (a["raw_affiliation"] or "").lower() for a in p.authorships)
        reason = None
        if not has_uiuc and not mentions:
            reason = "no_uiuc_affiliation"
        elif p.work["language"] not in (None, "en") and p99 > 0 and p.work["cited_by_count"] >= p99:
            reason = "non_english_high_citation"
        if reason:
            p.work["is_outlier"] = True
            p.work["outlier_reason"] = reason
            counts[reason] += 1
    return counts


def cap_by_date(items: list[ParsedWork], limit: int = 25000) -> list[ParsedWork]:
    if len(items) <= limit:
        return items
    return sorted(items, key=lambda p: p.work["publication_date"] or "", reverse=True)[:limit]
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_works.py -v` → all PASS.

- [ ] **Step 6: Commit**
```bash
git add ingest/works.py tests/factories.py tests/test_works.py
git commit -m "feat(ingest): pure work cleaning, parsing and outlier rules"
```

---

### Task 3: OpenAlex client with page cache, retry and quota stop

**Files:**
- Create: `ingest/openalex.py`
- Test: `tests/test_openalex.py`

**Interfaces:**
- Consumes: `ingest.works.UIUC_ID`.
- Produces: `WORK_FIELDS: list[str]`; `class QuotaExhausted(RuntimeError)`; `works_filter(today: date) -> str`; `resolve_filter(cache_dir: Path, today: date, refresh: bool = False) -> str` (persists the filter in `cache_dir/works/filter.txt` so later steps reuse it); `page_dir_for(cache_dir: Path, filter_str: str) -> Path`; `read_cached_results(page_dir: Path) -> Iterator[dict]`; `class OpenAlexClient(http: httpx.Client, cache_dir: Path, api_key=None, mailto=None, min_remaining_usd=0.005, max_retries=5, sleep=time.sleep)` with `.iter_pages(filter_str: str, per_page: int = 200) -> Iterator[list[dict]]`.

- [ ] **Step 1: Write the failing tests** — `tests/test_openalex.py`
```python
from datetime import date

import httpx
import pytest

from ingest.openalex import (OpenAlexClient, QuotaExhausted, page_dir_for, read_cached_results,
                             resolve_filter, works_filter)


def _pages_handler(pages, calls, remaining="0.09"):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["cursor"])
        idx = {"*": 0, "c1": 1, "c2": 2}[request.url.params["cursor"]]
        results, nxt = pages[idx]
        return httpx.Response(200, json={"meta": {"next_cursor": nxt}, "results": results},
                              headers={"x-ratelimit-remaining-usd": remaining})
    return handler


PAGES = [([{"id": "W1"}, {"id": "W2"}], "c1"), ([{"id": "W3"}], "c2"), ([], None)]


def test_works_filter_two_years_back():
    assert works_filter(date(2026, 11, 17)) == "institutions.id:I157725225,from_publication_date:2024-11-17"
    assert works_filter(date(2028, 2, 29)).endswith("2026-02-28")


def test_resolve_filter_is_sticky(tmp_path):
    f1 = resolve_filter(tmp_path, date(2026, 11, 17))
    assert resolve_filter(tmp_path, date(2026, 11, 20)) == f1
    assert resolve_filter(tmp_path, date(2026, 11, 20), refresh=True).endswith("2024-11-20")


def test_iter_pages_fetches_all_and_caches(tmp_path):
    calls = []
    http = httpx.Client(transport=httpx.MockTransport(_pages_handler(PAGES, calls)))
    client = OpenAlexClient(http, tmp_path, sleep=lambda s: None)
    ids = [w["id"] for page in client.iter_pages("F") for w in page]
    assert ids == ["W1", "W2", "W3"]
    assert calls == ["*", "c1", "c2"]
    assert [w["id"] for w in read_cached_results(page_dir_for(tmp_path, "F"))] == ["W1", "W2", "W3"]
    calls.clear()
    assert [w["id"] for page in client.iter_pages("F") for w in page] == ["W1", "W2", "W3"]
    assert calls == []  # fully served from cache


def test_quota_stop_then_resume(tmp_path):
    calls = []
    low = httpx.Client(transport=httpx.MockTransport(_pages_handler(PAGES, calls, remaining="0.001")))
    with pytest.raises(QuotaExhausted):
        list(OpenAlexClient(low, tmp_path, sleep=lambda s: None).iter_pages("F"))
    assert calls == ["*"]
    calls.clear()
    ok = httpx.Client(transport=httpx.MockTransport(_pages_handler(PAGES, calls)))
    ids = [w["id"] for page in OpenAlexClient(ok, tmp_path, sleep=lambda s: None).iter_pages("F") for w in page]
    assert ids == ["W1", "W2", "W3"]
    assert calls == ["c1", "c2"]


def test_retries_on_500_then_succeeds(tmp_path):
    state = {"n": 0}
    sleeps = []

    def handler(request):
        state["n"] += 1
        if state["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"meta": {"next_cursor": None}, "results": [{"id": "W1"}]})

    client = OpenAlexClient(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path, sleep=sleeps.append)
    assert [w["id"] for p in client.iter_pages("F") for w in p] == ["W1"]
    assert sleeps == [1, 2]


def test_long_retry_after_raises_quota(tmp_path):
    handler = lambda r: httpx.Response(429, headers={"retry-after": "76367"})
    client = OpenAlexClient(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path, sleep=lambda s: None)
    with pytest.raises(QuotaExhausted):
        list(client.iter_pages("F"))
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_openalex.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement** — `ingest/openalex.py`
```python
from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from pathlib import Path
from typing import Callable, Iterator

import httpx

from .works import UIUC_ID

BASE_URL = "https://api.openalex.org"
WORK_FIELDS = [
    "id", "doi", "title", "publication_date", "type", "language", "cited_by_count", "open_access",
    "primary_location", "primary_topic", "topics", "authorships", "is_retracted", "is_paratext",
    "abstract_inverted_index",
]


class QuotaExhausted(RuntimeError):
    pass


def works_filter(today: date) -> str:
    try:
        start = today.replace(year=today.year - 2)
    except ValueError:  # Feb 29
        start = today.replace(year=today.year - 2, day=28)
    return f"institutions.id:{UIUC_ID},from_publication_date:{start.isoformat()}"


def resolve_filter(cache_dir: Path, today: date, refresh: bool = False) -> str:
    path = cache_dir / "works" / "filter.txt"
    if path.exists() and not refresh:
        return path.read_text().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    value = works_filter(today)
    path.write_text(value)
    return value


def page_dir_for(cache_dir: Path, filter_str: str) -> Path:
    return cache_dir / "works" / hashlib.sha1(filter_str.encode()).hexdigest()[:12]


def _cached_pages(page_dir: Path) -> list[Path]:
    return sorted(page_dir.glob("page-*.json"))


def read_cached_results(page_dir: Path) -> Iterator[dict]:
    for path in _cached_pages(page_dir):
        yield from json.loads(path.read_text())["results"]


class OpenAlexClient:
    def __init__(self, http: httpx.Client, cache_dir: Path, api_key: str | None = None,
                 mailto: str | None = None, min_remaining_usd: float = 0.005, max_retries: int = 5,
                 sleep: Callable[[float], None] = time.sleep):
        self.http = http
        self.cache_dir = cache_dir
        self.api_key = api_key
        self.mailto = mailto
        self.min_remaining_usd = min_remaining_usd
        self.max_retries = max_retries
        self.sleep = sleep

    def _get(self, params: dict) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.http.get(f"{BASE_URL}/works", params=params, timeout=60)
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
                self.sleep(2 ** attempt)
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("retry-after")
                wait = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else 2 ** attempt
                if resp.status_code == 429 and wait > 120:
                    raise QuotaExhausted(
                        f"OpenAlex daily budget exhausted (retry after {int(wait)}s). "
                        "Re-run later or set OPENALEX_API_KEY; progress is cached.")
                if attempt == self.max_retries:
                    resp.raise_for_status()
                self.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError("unreachable")

    def iter_pages(self, filter_str: str, per_page: int = 200) -> Iterator[list[dict]]:
        page_dir = page_dir_for(self.cache_dir, filter_str)
        page_dir.mkdir(parents=True, exist_ok=True)
        cursor: str | None = "*"
        n = 0
        for path in _cached_pages(page_dir):
            page = json.loads(path.read_text())
            yield page["results"]
            cursor = page["next_cursor"]
            n += 1
        while cursor is not None:
            params = {"filter": filter_str, "per_page": per_page, "cursor": cursor,
                      "select": ",".join(WORK_FIELDS)}
            if self.api_key:
                params["api_key"] = self.api_key
            if self.mailto:
                params["mailto"] = self.mailto
            resp = self._get(params)
            body = resp.json()
            results = body.get("results") or []
            next_cursor = body.get("meta", {}).get("next_cursor") if results else None
            tmp = page_dir / f"page-{n:05d}.json.tmp"
            tmp.write_text(json.dumps({"cursor": cursor, "next_cursor": next_cursor, "results": results}))
            tmp.rename(page_dir / f"page-{n:05d}.json")
            yield results
            n += 1
            cursor = next_cursor
            remaining = resp.headers.get("x-ratelimit-remaining-usd")
            if cursor is not None and remaining is not None and float(remaining) < self.min_remaining_usd:
                raise QuotaExhausted(
                    f"OpenAlex budget nearly exhausted (remaining ${remaining}). "
                    f"Re-run later or set OPENALEX_API_KEY; progress cached in {page_dir}.")
```

Note on `test_iter_pages_fetches_all_and_caches`: page 3 has empty results, so `next_cursor` is stored as `None` and the second run stops after cached pages. Page 3 is cached as an empty page, which is expected.

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_openalex.py -v` → all PASS.

- [ ] **Step 5: Commit**
```bash
git add ingest/openalex.py tests/test_openalex.py
git commit -m "feat(ingest): OpenAlex client with cursor paging, disk cache, retry, quota stop"
```

---

### Task 4: Load works into Postgres (`clean-works`)

**Files:**
- Create: `ingest/load_works.py`
- Test: `tests/test_load_works.py`

**Interfaces:**
- Consumes: `parse_work`, `drop_reason`, `mark_outliers`, `cap_by_date`, `ParsedWork` (Task 2); `put_stat` (Task 1).
- Produces: `upsert_parsed(conn, items: list[ParsedWork]) -> None` (also deletes works not in `items`); `load_works(conn, raw_works: Iterable[dict], cap: int = 25000) -> dict` that returns and stores (`stats_cache` key `dq_works`) `{"fetched": int, "duplicates": int, "dropped": {reason: n}, "kept": int, "outliers": {reason: n}, "capped": int}`.

- [ ] **Step 1: Write the failing tests** — `tests/test_load_works.py`
```python
import numpy as np

from ingest.db import get_stat
from ingest.load_works import load_works
from tests.factories import HERZEN, make_author, make_work


def _count(db, table):
    with db.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table}")
        return cur.fetchone()[0]


def test_load_works_writes_tables_and_report(db):
    raw = [make_work(id="W1"), make_work(id="W1"), make_work(id="W2", type="erratum"),
           make_work(id="W3", authorships=[make_author("A5", "X", [HERZEN], "Herzen")])]
    report = load_works(db, raw)
    assert report["fetched"] == 4 and report["duplicates"] == 1
    assert report["dropped"] == {"type:erratum": 1}
    assert report["kept"] == 2
    assert report["outliers"]["no_uiuc_affiliation"] == 1
    assert _count(db, "works") == 2
    assert _count(db, "authorships") == 2
    assert _count(db, "topics") == 1
    assert get_stat(db, "dq_works")["kept"] == 2
    with db.cursor() as cur:
        cur.execute("SELECT is_outlier FROM works WHERE id='W3'")
        assert cur.fetchone()[0] is True
        cur.execute("SELECT count(*) FROM works WHERE tsv @@ websearch_to_tsquery('english', 'drone')")
        assert cur.fetchone()[0] == 2


def test_reload_is_idempotent_and_keeps_embeddings(db):
    load_works(db, [make_work(id="W1"), make_work(id="W2")])
    with db.cursor() as cur:
        cur.execute("UPDATE works SET embedding = %s WHERE id = 'W1'", (np.ones(1024, dtype=np.float32),))
    db.commit()
    load_works(db, [make_work(id="W1", cited=99)])
    assert _count(db, "works") == 1  # W2 removed
    with db.cursor() as cur:
        cur.execute("SELECT cited_by_count, embedding IS NOT NULL FROM works WHERE id='W1'")
        assert cur.fetchone() == (99, True)
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_load_works.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement** — `ingest/load_works.py`
```python
from __future__ import annotations

from collections import Counter
from typing import Iterable

import psycopg

from .db import put_stat
from .works import ParsedWork, cap_by_date, drop_reason, mark_outliers, parse_work

WORK_COLS = ["id", "doi", "title", "abstract", "publication_date", "type", "language", "cited_by_count",
             "is_oa", "oa_url", "venue_name", "venue_type", "primary_topic_id", "is_outlier", "outlier_reason"]


def upsert_parsed(conn: psycopg.Connection, items: list[ParsedWork]) -> None:
    topics = {t["id"]: t for p in items for t in p.topics}
    insts = {i["id"]: i for p in items for i in p.institutions}
    authors = {a["id"]: a for p in items for a in p.authors}
    cols = ", ".join(WORK_COLS)
    vals = ", ".join(f"%({c})s" for c in WORK_COLS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in WORK_COLS if c != "id")
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO topics (id, display_name, subfield, field, domain)"
            " VALUES (%(id)s, %(display_name)s, %(subfield)s, %(field)s, %(domain)s)"
            " ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name,"
            " subfield = EXCLUDED.subfield, field = EXCLUDED.field, domain = EXCLUDED.domain",
            list(topics.values()))
        cur.executemany(
            "INSERT INTO institutions (id, display_name, country_code, type)"
            " VALUES (%(id)s, %(display_name)s, %(country_code)s, %(type)s)"
            " ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name,"
            " country_code = EXCLUDED.country_code, type = EXCLUDED.type",
            list(insts.values()))
        cur.executemany(
            "INSERT INTO authors (id, display_name, orcid) VALUES (%(id)s, %(display_name)s, %(orcid)s)"
            " ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, orcid = EXCLUDED.orcid",
            list(authors.values()))
        cur.executemany(
            f"INSERT INTO works ({cols}) VALUES ({vals}) ON CONFLICT (id) DO UPDATE SET {updates}",
            [p.work for p in items])
        ids = [p.work["id"] for p in items]
        cur.execute("DELETE FROM works WHERE NOT (id = ANY(%s))", (ids,))
        cur.execute("DELETE FROM authorships WHERE work_id = ANY(%s)", (ids,))
        cur.execute("DELETE FROM work_institutions WHERE work_id = ANY(%s)", (ids,))
        cur.execute("DELETE FROM work_topics WHERE work_id = ANY(%s)", (ids,))
        cur.executemany(
            "INSERT INTO authorships (work_id, author_id, position, is_uiuc, raw_affiliation)"
            " VALUES (%(work_id)s, %(author_id)s, %(position)s, %(is_uiuc)s, %(raw_affiliation)s)",
            [a for p in items for a in p.authorships])
        cur.executemany(
            "INSERT INTO work_institutions (work_id, institution_id) VALUES (%s, %s)",
            [(p.work["id"], iid) for p in items for iid in p.work_institutions])
        cur.executemany(
            "INSERT INTO work_topics (work_id, topic_id, score) VALUES (%s, %s, %s)",
            [(p.work["id"], tid, score) for p in items for tid, score in p.work_topics])
    conn.commit()


def load_works(conn: psycopg.Connection, raw_works: Iterable[dict], cap: int = 25000) -> dict:
    fetched = duplicates = 0
    dropped: Counter[str] = Counter()
    seen: set[str] = set()
    parsed: list[ParsedWork] = []
    for w in raw_works:
        fetched += 1
        if w.get("id") in seen:
            duplicates += 1
            continue
        seen.add(w.get("id"))
        reason = drop_reason(w)
        if reason:
            dropped[reason] += 1
            continue
        parsed.append(parse_work(w))
    outliers = mark_outliers(parsed)
    kept_before_cap = len(parsed)
    parsed = cap_by_date(parsed, limit=cap)
    upsert_parsed(conn, parsed)
    report = {"fetched": fetched, "duplicates": duplicates, "dropped": dict(dropped), "kept": len(parsed),
              "outliers": outliers, "capped": kept_before_cap - len(parsed)}
    put_stat(conn, "dq_works", report)
    return report
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_load_works.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add ingest/load_works.py tests/test_load_works.py
git commit -m "feat(ingest): idempotent upsert of cleaned works with data-quality report"
```

---

### Task 5: Faculty loading and keyword cleaning

**Files:**
- Create: `ingest/faculty.py`, `data/keyword_stoplist.txt`, `data/keyword_generic.txt`
- Test: `tests/test_faculty.py`

**Interfaces:**
- Consumes: `put_stat` (Task 1); `institutions` table filled by Task 4 (used as org-name set; empty is fine).
- Produces: `parse_pg_array(s: str | None) -> list[str]`; `normalize_keyword(k: str) -> str`; `clean_keywords(raw: list[str], stoplist: set[str], org_names: set[str], generic: set[str], large_threshold: int = 200) -> list[str]`; `load_word_list(path: Path) -> set[str]`; `load_faculty(conn, csv_path: Path, data_dir: Path) -> dict` that returns and stores (`dq_faculty`) `{"rows": n, "missing_photo": n, "missing_position": n, "keywords_raw_median": x, "keywords_clean_median": x}`.

- [ ] **Step 1: Write word lists**

`data/keyword_stoplist.txt`:
```
# Always dropped (exact match after normalization). One per line.
real world
such information networks
case study
et al
results
method
methods
approach
study
paper
applications
```

`data/keyword_generic.txt`:
```
# Dropped only for faculty with more than 200 raw keywords.
mathematics
computer science
engineering
science
research
technology
information technology
computational science
statistics
data
analysis
biology
physics
chemistry
medicine
psychology
economics
education
```

- [ ] **Step 2: Write the failing tests** — `tests/test_faculty.py`
```python
import csv

from ingest.db import get_stat
from ingest.faculty import clean_keywords, load_faculty, normalize_keyword, parse_pg_array


def test_parse_pg_array():
    assert parse_pg_array('{"parallel computing",sampling,"a \\"quoted\\" word"}') == [
        "parallel computing", "sampling", 'a "quoted" word']
    assert parse_pg_array("{}") == []
    assert parse_pg_array(None) == []
    assert parse_pg_array("NULL") == []


def test_normalize_keyword():
    assert normalize_keyword("  Deep   Learning. ") == "deep learning"


def test_clean_keywords_rules():
    raw = ["Deep Learning", "deep learning", "Simon Fraser University", "SIAM International Conference",
           "real world", "mathematics", "AI", "x"]
    small = clean_keywords(raw, stoplist={"real world"}, org_names={"simon fraser university"},
                           generic={"mathematics"})
    assert small == ["deep learning", "mathematics", "ai"]
    large = clean_keywords(raw + [f"kw{i}" for i in range(250)], stoplist=set(), org_names=set(),
                           generic={"mathematics"})
    assert "mathematics" not in large and "real world" in large


def test_load_faculty(db, tmp_path):
    p = tmp_path / "f.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["email", "name", "photo_url", "position", "keywords"])
        w.writerow(["a@illinois.edu", "Jiawei Han", "NULL", "Professor", '{"text mining","real world"}'])
        w.writerow(["b@illinois.edu", "Jane Doe", "https://x/p.jpg", "NULL", "{vision}"])
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "keyword_stoplist.txt").write_text("# c\nreal world\n")
    (data_dir / "keyword_generic.txt").write_text("")
    report = load_faculty(db, p, data_dir)
    assert report["rows"] == 2 and report["missing_photo"] == 1 and report["missing_position"] == 1
    load_faculty(db, p, data_dir)  # idempotent
    with db.cursor() as cur:
        cur.execute("SELECT name, photo_url, keywords, keywords_raw FROM faculty ORDER BY email")
        rows = cur.fetchall()
    assert rows[0] == ("Jiawei Han", None, ["text mining"], ["text mining", "real world"])
    assert len(rows) == 2
    assert get_stat(db, "dq_faculty")["rows"] == 2
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_faculty.py -v` → FAIL.

- [ ] **Step 4: Implement** — `ingest/faculty.py`
```python
from __future__ import annotations

import csv
import re
import statistics
from pathlib import Path

import psycopg

from .db import put_stat

ORG_MARKERS = ("university", "universität", "conference", "symposium", "proceedings", "journal of",
               "institute of", "workshop on")


def parse_pg_array(s: str | None) -> list[str]:
    if s is None:
        return []
    s = s.strip()
    if s in ("", "NULL", "{}"):
        return []
    if not (s.startswith("{") and s.endswith("}")):
        raise ValueError(f"not a postgres array literal: {s[:40]!r}")
    row = next(csv.reader([s[1:-1]], delimiter=",", quotechar='"', escapechar="\\", doublequote=False))
    return [x for x in row if x and x != "NULL"]


def normalize_keyword(k: str) -> str:
    return re.sub(r"\s+", " ", k.lower()).strip(" .,;:-")


def clean_keywords(raw: list[str], stoplist: set[str], org_names: set[str], generic: set[str],
                   large_threshold: int = 200) -> list[str]:
    large = len(raw) > large_threshold
    out: list[str] = []
    seen: set[str] = set()
    for k in raw:
        n = normalize_keyword(k)
        if len(n) < 2 or n in seen:
            continue
        seen.add(n)
        if n in stoplist or n in org_names or any(m in n for m in ORG_MARKERS):
            continue
        if large and n in generic:
            continue
        out.append(n)
    return out


def load_word_list(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {normalize_keyword(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")}


def _nullable(v: str | None) -> str | None:
    v = (v or "").strip()
    return None if v in ("", "NULL") else v


def load_faculty(conn: psycopg.Connection, csv_path: Path, data_dir: Path) -> dict:
    stoplist = load_word_list(data_dir / "keyword_stoplist.txt")
    generic = load_word_list(data_dir / "keyword_generic.txt")
    with conn.cursor() as cur:
        cur.execute("SELECT lower(display_name) FROM institutions WHERE display_name IS NOT NULL")
        org_names = {r[0] for r in cur.fetchall()}
    csv.field_size_limit(10 ** 8)
    rows = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            raw = parse_pg_array(r.get("keywords"))
            clean = clean_keywords(raw, stoplist, org_names, generic)
            rows.append({
                "email": r["email"].strip().lower(), "name": r["name"].strip(),
                "photo_url": _nullable(r.get("photo_url")), "position": _nullable(r.get("position")),
                "keywords_raw": raw, "keywords": clean, "keywords_text": ", ".join(clean),
            })
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO faculty (email, name, photo_url, position, keywords_raw, keywords, keywords_text)"
            " VALUES (%(email)s, %(name)s, %(photo_url)s, %(position)s, %(keywords_raw)s, %(keywords)s,"
            " %(keywords_text)s)"
            " ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, photo_url = EXCLUDED.photo_url,"
            " position = EXCLUDED.position, keywords_raw = EXCLUDED.keywords_raw,"
            " keywords = EXCLUDED.keywords, keywords_text = EXCLUDED.keywords_text",
            rows)
    conn.commit()
    report = {
        "rows": len(rows),
        "missing_photo": sum(1 for r in rows if r["photo_url"] is None),
        "missing_position": sum(1 for r in rows if r["position"] is None),
        "keywords_raw_median": statistics.median([len(r["keywords_raw"]) for r in rows]) if rows else 0,
        "keywords_clean_median": statistics.median([len(r["keywords"]) for r in rows]) if rows else 0,
    }
    put_stat(conn, "dq_faculty", report)
    return report
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_faculty.py -v` → PASS.

- [ ] **Step 6: Commit**
```bash
git add ingest/faculty.py data/keyword_stoplist.txt data/keyword_generic.txt tests/test_faculty.py
git commit -m "feat(ingest): faculty CSV loader with keyword cleaning"
```

---

### Task 6: Name normalization and matching tiers (pure)

**Files:**
- Create: `ingest/names.py`
- Test: `tests/test_names.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) NameParts(first: str, middles: tuple[str, ...], last: str)`; `normalize_name(name: str | None) -> NameParts | None`; `METHODS = ("exact", "first_last", "initial_last")`; `METHOD_BASE = {"exact": 0.9, "first_last": 0.75, "initial_last": 0.6}`; `class AuthorIndex` with `add(author_id: str, display_name: str) -> None` and `match(fac: NameParts) -> tuple[str, list[str]] | None`; `link_confidence(method: str, cosines: list[float]) -> tuple[int, float]` (index of chosen candidate, confidence).

- [ ] **Step 1: Write the failing tests** — `tests/test_names.py`
```python
from ingest.names import AuthorIndex, NameParts, link_confidence, normalize_name


def test_normalize_name():
    assert normalize_name("José A. García") == NameParts("jose", ("a",), "garcia")
    assert normalize_name("Smith, John") == NameParts("john", (), "smith")
    assert normalize_name("Martin Luther King Jr.") == NameParts("martin", ("luther",), "king")
    assert normalize_name("Mary-Kate O'Neil") == NameParts("marykate", (), "oneil")
    assert normalize_name("Robert (Bob) Stone") == NameParts("robert", (), "stone")
    assert normalize_name("Plato") is None
    assert normalize_name(None) is None


def test_match_tiers():
    idx = AuthorIndex()
    idx.add("A1", "John A. Smith")
    idx.add("A2", "John Smith")
    idx.add("A3", "J. Smith")
    idx.add("A4", "Jane Smith")
    assert idx.match(normalize_name("John A Smith")) == ("exact", ["A1"])
    assert idx.match(normalize_name("John B Smith")) == ("first_last", ["A1", "A2"])
    assert idx.match(normalize_name("Jack Smith")) == ("initial_last", ["A3"])  # Jane excluded
    assert idx.match(normalize_name("Wei Zhang")) is None


def test_link_confidence():
    assert link_confidence("exact", [0.4]) == (0, 0.9)
    i, c = link_confidence("initial_last", [0.30, 0.71, 0.50])
    assert i == 1 and c == 0.6
    i, c = link_confidence("initial_last", [0.70, 0.69])
    assert i == 0 and c < 0.5
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_names.py -v` → FAIL.

- [ ] **Step 3: Implement** — `ingest/names.py`
```python
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from unidecode import unidecode

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md"}
METHODS = ("exact", "first_last", "initial_last")
METHOD_BASE = {"exact": 0.9, "first_last": 0.75, "initial_last": 0.6}


@dataclass(frozen=True)
class NameParts:
    first: str
    middles: tuple[str, ...]
    last: str


def normalize_name(name: str | None) -> NameParts | None:
    if not name:
        return None
    s = unidecode(name).lower()
    s = re.sub(r"\(.*?\)", " ", s)
    if "," in s:
        last, _, rest = s.partition(",")
        s = f"{rest} {last}"
    s = s.replace("-", "").replace("'", "")
    s = re.sub(r"[^a-z\s]", " ", s)
    tokens = [t for t in s.split() if t not in SUFFIXES]
    if len(tokens) < 2:
        return None
    return NameParts(tokens[0], tuple(tokens[1:-1]), tokens[-1])


def _keys(p: NameParts) -> dict[str, str]:
    return {
        "exact": " ".join([p.first, *p.middles, p.last]),
        "first_last": f"{p.first} {p.last}",
        "initial_last": f"{p.first[0]} {p.last}",
    }


class AuthorIndex:
    def __init__(self) -> None:
        self._index: dict[str, dict[str, list[str]]] = {m: defaultdict(list) for m in METHODS}
        self._parts: dict[str, NameParts] = {}

    def add(self, author_id: str, display_name: str) -> None:
        p = normalize_name(display_name)
        if p is None or author_id in self._parts:
            return
        self._parts[author_id] = p
        for method, key in _keys(p).items():
            self._index[method][key].append(author_id)

    def match(self, fac: NameParts | None) -> tuple[str, list[str]] | None:
        if fac is None:
            return None
        keys = _keys(fac)
        for method in METHODS:
            ids = list(self._index[method].get(keys[method], []))
            if method == "initial_last":
                # only authors recorded with an initial; a different full first name is another person
                ids = [a for a in ids if len(self._parts[a].first) == 1]
            if ids:
                return method, sorted(ids)
        return None


def link_confidence(method: str, cosines: list[float]) -> tuple[int, float]:
    base = METHOD_BASE[method]
    if len(cosines) == 1:
        return 0, base
    order = sorted(range(len(cosines)), key=lambda i: -cosines[i])
    margin = cosines[order[0]] - cosines[order[1]]
    return order[0], round(base * (0.6 + 0.4 * min(1.0, margin / 0.1)), 4)
```

Check `test_link_confidence` case 2: margin 0.71 − 0.50 = 0.21 → factor 1.0 → 0.6. Case 3: margin 0.01 → 0.6 × 0.64 = 0.384 < 0.5. ✓

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_names.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add ingest/names.py tests/test_names.py
git commit -m "feat(ingest): name normalization, tiered author matching, link confidence"
```

---

### Task 7: Ollama embedder

**Files:**
- Create: `ingest/embedder.py`
- Test: `tests/test_embedder.py`

**Interfaces:**
- Produces: `MAX_CHARS = 2000`; `class EmbedderUnavailable(RuntimeError)`; `class OllamaEmbedder(http: httpx.Client, base_url: str, model: str, batch_size: int = 32, timeout: float = 120.0)` with `.embed(texts: list[str]) -> list[np.ndarray]` (float32, one per input, same order).

- [ ] **Step 1: Write the failing tests** — `tests/test_embedder.py`
```python
import json

import httpx
import numpy as np
import pytest

from ingest.embedder import EmbedderUnavailable, OllamaEmbedder


def test_embed_batches_and_truncates():
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={"embeddings": [[float(len(t)), 0.0] for t in body["input"]]})

    e = OllamaEmbedder(httpx.Client(transport=httpx.MockTransport(handler)), "http://o", "bge-m3", batch_size=2)
    out = e.embed(["a", "bb", "x" * 5000])
    assert [len(b["input"]) for b in seen] == [2, 1]
    assert seen[0]["model"] == "bge-m3"
    assert [v[0] for v in out] == [1.0, 2.0, 2000.0]
    assert out[0].dtype == np.float32


def test_missing_model_raises_with_hint():
    e = OllamaEmbedder(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))), "http://o", "bge-m3")
    with pytest.raises(EmbedderUnavailable, match="ollama pull bge-m3"):
        e.embed(["a"])


def test_connection_error_raises_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused")
    e = OllamaEmbedder(httpx.Client(transport=httpx.MockTransport(handler)), "http://o", "bge-m3")
    with pytest.raises(EmbedderUnavailable, match="Ollama"):
        e.embed(["a"])
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_embedder.py -v` → FAIL.

- [ ] **Step 3: Implement** — `ingest/embedder.py`
```python
from __future__ import annotations

import httpx
import numpy as np

MAX_CHARS = 2000


class EmbedderUnavailable(RuntimeError):
    pass


class OllamaEmbedder:
    def __init__(self, http: httpx.Client, base_url: str, model: str, batch_size: int = 32,
                 timeout: float = 120.0):
        self.http = http
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [t[:MAX_CHARS] for t in texts[i:i + self.batch_size]]
            try:
                resp = self.http.post(f"{self.base_url}/api/embed", json={"model": self.model, "input": batch},
                                      timeout=self.timeout)
            except httpx.TransportError as exc:
                raise EmbedderUnavailable(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
            if resp.status_code == 404:
                raise EmbedderUnavailable(f"Model {self.model} not found. Run: ollama pull {self.model}")
            resp.raise_for_status()
            vecs = resp.json()["embeddings"]
            if len(vecs) != len(batch):
                raise RuntimeError(f"Ollama returned {len(vecs)} embeddings for {len(batch)} inputs")
            out.extend(np.asarray(v, dtype=np.float32) for v in vecs)
        return out
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_embedder.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add ingest/embedder.py tests/test_embedder.py
git commit -m "feat(ingest): batched Ollama embedder"
```

---

### Task 8: Profile embeddings and faculty linking

**Files:**
- Create: `ingest/linking.py`
- Test: `tests/test_linking.py`

**Interfaces:**
- Consumes: `AuthorIndex`, `normalize_name`, `link_confidence` (Task 6); an embedder object with `.embed(list[str]) -> list[np.ndarray]` (Task 7); `put_stat` (Task 1).
- Produces: `find_candidates(conn) -> dict[int, tuple[str, list[str]]]` (faculty_id → (method, author_ids), only UIUC authors); `embed_profiles(conn, embedder) -> dict` (`{"faculty": n, "authors": n}` newly embedded, only for ambiguous matches); `link_faculty(conn, min_confidence: float = 0.5) -> dict` that returns and stores (`dq_link`) `{"faculty": n, "linked": n, "rate": float, "by_method": {...}, "no_candidate": n, "below_threshold": n}`.

- [ ] **Step 1: Write the failing tests** — `tests/test_linking.py`
```python
import numpy as np

from ingest.db import get_stat
from ingest.linking import embed_profiles, find_candidates, link_faculty


def _vec(i):
    v = np.zeros(1024, dtype=np.float32)
    v[i] = 1.0
    return v


class FakeEmbedder:
    """Puts 'vision' texts on axis 0, 'chemistry' texts on axis 1."""
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [_vec(0) if "vision" in t.lower() else _vec(1) for t in texts]


def _seed(db):
    with db.cursor() as cur:
        cur.execute("INSERT INTO topics VALUES ('T1','Computer Vision',NULL,'Computer Science',NULL),"
                    " ('T2','Organic Chemistry',NULL,'Chemistry',NULL)")
        cur.execute("INSERT INTO works (id, title, primary_topic_id) VALUES ('W1','a','T1'),('W2','b','T2'),"
                    " ('W3','c','T1')")
        cur.execute("INSERT INTO work_topics VALUES ('W1','T1',0.9),('W2','T2',0.9),('W3','T1',0.9)")
        cur.execute("INSERT INTO authors (id, display_name) VALUES ('A1','J. Wang'),('A2','J. Wang'),"
                    " ('A3','Alice B. Cooper'),('A4','Bob Outsider')")
        cur.execute("INSERT INTO authorships (work_id, author_id, is_uiuc) VALUES ('W1','A1',true),"
                    " ('W2','A2',true),('W3','A3',true),('W3','A4',false)")
        cur.execute("INSERT INTO faculty (email, name, keywords, keywords_text) VALUES"
                    " ('jw@x','Jian Wang','{computer vision}','computer vision'),"
                    " ('ac@x','Alice B Cooper','{robotics}','robotics'),"
                    " ('bo@x','Bob Outsider','{x}','x')")
    db.commit()


def test_find_candidates_only_uiuc_authors(db):
    _seed(db)
    c = find_candidates(db)
    by_email = {}
    with db.cursor() as cur:
        cur.execute("SELECT id, email FROM faculty")
        for fid, email in cur.fetchall():
            by_email[email] = c.get(fid)
    assert by_email["jw@x"] == ("initial_last", ["A1", "A2"])
    assert by_email["ac@x"] == ("exact", ["A3"])
    assert by_email["bo@x"] is None


def test_embed_profiles_then_link(db):
    _seed(db)
    emb = FakeEmbedder()
    counts = embed_profiles(db, emb)
    assert counts == {"faculty": 1, "authors": 2}  # only the ambiguous Jian Wang case
    assert embed_profiles(db, emb) == {"faculty": 0, "authors": 0}  # idempotent
    report = link_faculty(db)
    with db.cursor() as cur:
        cur.execute("SELECT f.email, l.author_id, l.method, l.confidence FROM faculty_author_link l"
                    " JOIN faculty f ON f.id = l.faculty_id ORDER BY f.email")
        rows = cur.fetchall()
    assert [(r[0], r[1], r[2]) for r in rows] == [("ac@x", "A3", "exact"), ("jw@x", "A1", "initial_last")]
    assert report["linked"] == 2 and report["no_candidate"] == 1
    assert get_stat(db, "dq_link")["faculty"] == 3
    link_faculty(db)  # idempotent
    with db.cursor() as cur:
        cur.execute("SELECT count(*) FROM faculty_author_link")
        assert cur.fetchone()[0] == 2
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_linking.py -v` → FAIL.

- [ ] **Step 3: Implement** — `ingest/linking.py`
```python
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import psycopg

from .db import put_stat
from .names import AuthorIndex, link_confidence, normalize_name

TOP_TOPICS = 15
MAX_KEYWORDS = 80


def find_candidates(conn: psycopg.Connection) -> dict[int, tuple[str, list[str]]]:
    idx = AuthorIndex()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT a.id, a.display_name FROM authors a"
                    " JOIN authorships s ON s.author_id = a.id WHERE s.is_uiuc ORDER BY a.id")
        for aid, name in cur.fetchall():
            idx.add(aid, name)
        cur.execute("SELECT id, name FROM faculty ORDER BY id")
        faculty = cur.fetchall()
    out: dict[int, tuple[str, list[str]]] = {}
    for fid, name in faculty:
        m = idx.match(normalize_name(name))
        if m:
            out[fid] = m
    return out


def _faculty_text(keywords: list[str]) -> str:
    return "Research interests: " + ", ".join(keywords[:MAX_KEYWORDS])


def embed_profiles(conn: psycopg.Connection, embedder) -> dict:
    ambiguous = {fid: ids for fid, (_, ids) in find_candidates(conn).items() if len(ids) > 1}
    author_ids = sorted({a for ids in ambiguous.values() for a in ids})
    with conn.cursor() as cur:
        cur.execute("SELECT id, keywords FROM faculty WHERE id = ANY(%s) AND keyword_embedding IS NULL ORDER BY id",
                    (list(ambiguous),))
        fac_rows = cur.fetchall()
        cur.execute("SELECT author_id FROM author_profile WHERE author_id = ANY(%s)", (author_ids,))
        done = {r[0] for r in cur.fetchall()}
        todo = [a for a in author_ids if a not in done]
        cur.execute(
            "SELECT s.author_id, t.display_name, count(*) AS n FROM authorships s"
            " JOIN work_topics wt ON wt.work_id = s.work_id JOIN topics t ON t.id = wt.topic_id"
            " WHERE s.author_id = ANY(%s) GROUP BY s.author_id, t.display_name"
            " ORDER BY s.author_id, n DESC, t.display_name", (todo,))
        topics: dict[str, list[str]] = defaultdict(list)
        for aid, tname, _ in cur.fetchall():
            if len(topics[aid]) < TOP_TOPICS:
                topics[aid].append(tname)
    if fac_rows:
        vecs = embedder.embed([_faculty_text(kw) for _, kw in fac_rows])
        with conn.cursor() as cur:
            cur.executemany("UPDATE faculty SET keyword_embedding = %s WHERE id = %s",
                            [(v, fid) for (fid, _), v in zip(fac_rows, vecs)])
    if todo:
        texts = ["Research topics: " + "; ".join(topics.get(a) or ["unknown"]) for a in todo]
        vecs = embedder.embed(texts)
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO author_profile (author_id, profile_text, embedding) VALUES (%s, %s, %s)"
                            " ON CONFLICT (author_id) DO UPDATE SET profile_text = EXCLUDED.profile_text,"
                            " embedding = EXCLUDED.embedding",
                            [(a, t, v) for a, t, v in zip(todo, texts, vecs)])
    conn.commit()
    return {"faculty": len(fac_rows), "authors": len(todo)}


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    return float(a @ b / (na * nb)) if na and nb else 0.0


def link_faculty(conn: psycopg.Connection, min_confidence: float = 0.5) -> dict:
    cands = find_candidates(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM faculty")
        n_faculty = cur.fetchone()[0]
        cur.execute("SELECT id, keyword_embedding FROM faculty WHERE keyword_embedding IS NOT NULL")
        fac_vec = dict(cur.fetchall())
        cur.execute("SELECT author_id, embedding FROM author_profile")
        auth_vec = dict(cur.fetchall())
    links = []
    by_method: Counter[str] = Counter()
    below = 0
    for fid, (method, ids) in cands.items():
        if len(ids) == 1:
            choice, conf = 0, link_confidence(method, [1.0])[1]
        else:
            fv = fac_vec.get(fid)
            cos = [_cos(fv, auth_vec[a]) if fv is not None and a in auth_vec else 0.0 for a in ids]
            choice, conf = link_confidence(method, cos)
        if conf < min_confidence:
            below += 1
            continue
        links.append((fid, ids[choice], conf, method))
        by_method[method] += 1
    with conn.cursor() as cur:
        cur.execute("DELETE FROM faculty_author_link")
        cur.executemany("INSERT INTO faculty_author_link (faculty_id, author_id, confidence, method)"
                        " VALUES (%s, %s, %s, %s)", links)
    conn.commit()
    report = {"faculty": n_faculty, "linked": len(links),
              "rate": round(len(links) / n_faculty, 4) if n_faculty else 0.0,
              "by_method": dict(by_method), "no_candidate": n_faculty - len(cands), "below_threshold": below}
    put_stat(conn, "dq_link", report)
    return report
```

Check test: Jian Wang → initial_last ["A1","A2"]; faculty text contains "computer vision" → axis 0; A1 topics "Computer Vision" → axis 0, A2 "Organic Chemistry" → axis 1; cos = [1, 0]; margin 1 → conf 0.6 → link A1. Alice exact single → 0.9. Bob Outsider only non-UIUC author → no candidate. ✓

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_linking.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add ingest/linking.py tests/test_linking.py
git commit -m "feat(ingest): profile embeddings and confidence-scored faculty linking"
```

---

### Task 9: Work and faculty embeddings

**Files:**
- Create: `ingest/embed.py`
- Test: `tests/test_embed.py`

**Interfaces:**
- Consumes: embedder `.embed()` (Task 7); `faculty_author_link` (Task 8).
- Produces: `work_text(title: str, abstract: str | None) -> str`; `faculty_text(name: str, keywords: list[str], titles: list[str]) -> str`; `embed_works(conn, embedder, force: bool = False, chunk: int = 256, progress=print) -> int`; `embed_faculty(conn, embedder, force: bool = False) -> int`. Both return the number of rows embedded and commit after each chunk, so an interrupted run resumes.

- [ ] **Step 1: Write the failing tests** — `tests/test_embed.py`
```python
import numpy as np

from ingest.embed import embed_faculty, embed_works, faculty_text, work_text


class CountingEmbedder:
    def __init__(self):
        self.texts = []

    def embed(self, texts):
        self.texts.extend(texts)
        return [np.full(1024, 0.5, dtype=np.float32) for _ in texts]


def test_text_builders():
    assert work_text("T", None) == "T"
    assert work_text("T", "abs") == "T\n\nabs"
    t = faculty_text("Jane Doe", ["vision", "health"], ["Paper A", "Paper B"])
    assert t.startswith("Jane Doe. Research interests: vision, health.") and "Paper A; Paper B" in t


def test_embed_works_resumable(db):
    with db.cursor() as cur:
        cur.execute("INSERT INTO works (id, title, abstract) VALUES ('W1','a','x'),('W2','b',NULL),('W3','c','y')")
    db.commit()
    e = CountingEmbedder()
    assert embed_works(db, e, chunk=2, progress=lambda *a: None) == 3
    assert embed_works(db, e, progress=lambda *a: None) == 0
    assert embed_works(db, e, force=True, progress=lambda *a: None) == 3


def test_embed_faculty_uses_linked_titles(db):
    with db.cursor() as cur:
        cur.execute("INSERT INTO works (id, title, cited_by_count) VALUES ('W1','Vision paper',5)")
        cur.execute("INSERT INTO authors (id, display_name) VALUES ('A1','Jane Doe')")
        cur.execute("INSERT INTO authorships (work_id, author_id, is_uiuc) VALUES ('W1','A1',true)")
        cur.execute("INSERT INTO faculty (id, email, name, keywords) VALUES (1,'j@x','Jane Doe','{vision}')")
        cur.execute("INSERT INTO faculty_author_link VALUES (1,'A1',0.9,'exact')")
    db.commit()
    e = CountingEmbedder()
    assert embed_faculty(db, e) == 1
    assert "Vision paper" in e.texts[0]
    with db.cursor() as cur:
        cur.execute("SELECT embedding IS NOT NULL FROM faculty WHERE id = 1")
        assert cur.fetchone()[0] is True
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_embed.py -v` → FAIL.

- [ ] **Step 3: Implement** — `ingest/embed.py`
```python
from __future__ import annotations

import time

import psycopg


def work_text(title: str, abstract: str | None) -> str:
    return f"{title}\n\n{abstract}" if abstract else title


def faculty_text(name: str, keywords: list[str], titles: list[str]) -> str:
    text = f"{name}. Research interests: {', '.join(keywords[:60])}."
    if titles:
        text += f" Selected papers: {'; '.join(titles)}."
    return text


def embed_works(conn: psycopg.Connection, embedder, force: bool = False, chunk: int = 256, progress=print) -> int:
    with conn.cursor() as cur:
        if force:
            cur.execute("UPDATE works SET embedding = NULL")
            conn.commit()
        cur.execute("SELECT id, title, abstract FROM works WHERE embedding IS NULL ORDER BY id")
        rows = cur.fetchall()
    started = time.time()
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        vecs = embedder.embed([work_text(t, a) for _, t, a in part])
        with conn.cursor() as cur:
            cur.executemany("UPDATE works SET embedding = %s WHERE id = %s",
                            [(v, wid) for (wid, _, _), v in zip(part, vecs)])
        conn.commit()
        done = i + len(part)
        rate = done / max(time.time() - started, 1e-6)
        progress(f"embed works: {done}/{len(rows)} ({rate:.1f}/s)")
    return len(rows)


def embed_faculty(conn: psycopg.Connection, embedder, force: bool = False) -> int:
    with conn.cursor() as cur:
        if force:
            cur.execute("UPDATE faculty SET embedding = NULL")
            conn.commit()
        cur.execute(
            "SELECT f.id, f.name, f.keywords, ARRAY("
            "  SELECT w.title FROM faculty_author_link l"
            "  JOIN authorships s ON s.author_id = l.author_id JOIN works w ON w.id = s.work_id"
            "  WHERE l.faculty_id = f.id AND NOT w.is_outlier"
            "  ORDER BY w.cited_by_count DESC, w.id LIMIT 5)"
            " FROM faculty f WHERE f.embedding IS NULL ORDER BY f.id")
        rows = cur.fetchall()
    if not rows:
        return 0
    vecs = embedder.embed([faculty_text(n, kw, titles) for _, n, kw, titles in rows])
    with conn.cursor() as cur:
        cur.executemany("UPDATE faculty SET embedding = %s WHERE id = %s",
                        [(v, fid) for (fid, _, _, _), v in zip(rows, vecs)])
    conn.commit()
    return len(rows)
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_embed.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add ingest/embed.py tests/test_embed.py
git commit -m "feat(ingest): resumable work and faculty embeddings"
```

---

### Task 10: Aggregate portal statistics and data-quality report

**Files:**
- Create: `ingest/aggregate.py`
- Test: `tests/test_aggregate.py`

**Interfaces:**
- Consumes: all tables; `put_stat`, `get_stat` (Task 1); `UIUC_ID`, `UI_SYSTEM_ID` (Task 2).
- Produces: `compute_stats(conn, rising_min: int = 10) -> dict[str, object]` with keys `overview`, `monthly`, `types`, `fields`, `rising_topics`, `top_venues`, `top_partners`, `top_faculty`; `aggregate(conn, docs_dir: Path) -> dict` that also updates `faculty.primary_field` and `authors.works_count_in_set`, stores every key in `stats_cache` and writes `docs/data-quality.md`; `render_data_quality(dq_works, dq_faculty, dq_link, overview) -> str`.
- Payload shapes (Plan 2 API reads these verbatim):
  - `overview`: `{"works": int, "citations": int, "oa_share": float, "faculty": int, "faculty_linked": int, "partner_institutions": int, "outliers": int}`
  - `monthly`: `[{"month": "YYYY-MM", "count": int}]`
  - `types`: `[{"type": str, "count": int}]`
  - `fields`: `[{"field": str, "count": int, "subfields": [{"name": str, "count": int}]}]`
  - `rising_topics`: `[{"id": str, "name": str, "field": str, "recent": int, "prior": int, "growth": float}]`
  - `top_venues`: `[{"name": str, "count": int}]`
  - `top_partners`: `[{"id": str, "name": str, "country": str|None, "count": int}]`
  - `top_faculty`: `[{"id": int, "name": str, "count": int}]`

- [ ] **Step 1: Write the failing tests** — `tests/test_aggregate.py`
```python
from ingest.aggregate import aggregate
from ingest.db import get_stat, put_stat
from ingest.load_works import load_works
from tests.factories import HERZEN, UIUC, UISYS, make_author, make_topic, make_work


def test_aggregate_stats(db, tmp_path):
    works = [
        make_work(id="W1", date="2025-01-10", cited=5, authorships=[
            make_author("A1", "Jane Doe", [UIUC, UISYS], "UIUC"),
            make_author("A2", "Ivan P", [HERZEN], "Herzen", position="last")]),
        make_work(id="W2", date="2025-01-20", cited=7, source_type="conference", type="other"),
        make_work(id="W3", date="2025-02-01", cited=1, topic=make_topic("T2", "Organic Synthesis",
                  "Organic Chemistry", "Chemistry", "Physical Sciences")),
        make_work(id="W4", authorships=[make_author("A3", "Q", [HERZEN], "Herzen")]),  # outlier
    ]
    load_works(db, works)
    with db.cursor() as cur:
        cur.execute("INSERT INTO faculty (id, email, name) VALUES (1, 'j@x', 'Jane Doe')")
        cur.execute("INSERT INTO faculty_author_link VALUES (1, 'A1', 0.9, 'exact')")
    db.commit()
    put_stat(db, "dq_faculty", {"rows": 1, "missing_photo": 0, "missing_position": 0,
                                "keywords_raw_median": 1, "keywords_clean_median": 1})
    put_stat(db, "dq_link", {"faculty": 1, "linked": 1, "rate": 1.0, "by_method": {"exact": 1},
                             "no_candidate": 0, "below_threshold": 0})
    stats = aggregate(db, tmp_path)
    o = stats["overview"]
    assert o["works"] == 3 and o["citations"] == 13 and o["outliers"] == 1
    assert o["faculty"] == 1 and o["faculty_linked"] == 1
    assert o["partner_institutions"] == 1  # Herzen only; UIUC + UI System excluded
    assert stats["monthly"] == [{"month": "2025-01", "count": 2}, {"month": "2025-02", "count": 1}]
    assert {t["type"] for t in stats["types"]} == {"article", "conference-paper"}
    assert stats["fields"][0]["field"] == "Computer Science" and stats["fields"][0]["count"] == 2
    assert stats["top_partners"][0]["name"] == "Herzen University"
    assert stats["top_faculty"] == [{"id": 1, "name": "Jane Doe", "count": 1}]
    assert get_stat(db, "monthly") == stats["monthly"]
    with db.cursor() as cur:
        cur.execute("SELECT primary_field FROM faculty WHERE id = 1")
        assert cur.fetchone()[0] == "Computer Science"
    report = (tmp_path / "data-quality.md").read_text()
    assert "Link rate" in report and "100.0%" in report
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_aggregate.py -v` → FAIL.

- [ ] **Step 3: Implement** — `ingest/aggregate.py`
```python
from __future__ import annotations

from pathlib import Path

import psycopg

from .db import get_stat, put_stat
from .works import UI_SYSTEM_ID, UIUC_ID

EXCLUDED = [UIUC_ID, UI_SYSTEM_ID]


def _rows(conn, sql: str, params=()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def compute_stats(conn: psycopg.Connection, rising_min: int = 10) -> dict[str, object]:
    works, citations, oa_share = _rows(conn, "SELECT count(*), coalesce(sum(cited_by_count), 0),"
                                             " coalesce(avg(is_oa::int), 0) FROM works WHERE NOT is_outlier")[0]
    outliers = _rows(conn, "SELECT count(*) FROM works WHERE is_outlier")[0][0]
    faculty = _rows(conn, "SELECT count(*) FROM faculty")[0][0]
    linked = _rows(conn, "SELECT count(DISTINCT faculty_id) FROM faculty_author_link")[0][0]
    partners = _rows(conn, "SELECT count(DISTINCT wi.institution_id) FROM work_institutions wi"
                           " JOIN works w ON w.id = wi.work_id"
                           " WHERE NOT w.is_outlier AND NOT (wi.institution_id = ANY(%s))", (EXCLUDED,))[0][0]
    monthly = _rows(conn, "SELECT to_char(date_trunc('month', publication_date), 'YYYY-MM'), count(*)"
                          " FROM works WHERE NOT is_outlier AND publication_date IS NOT NULL"
                          " GROUP BY 1 ORDER BY 1")
    types = _rows(conn, "SELECT CASE WHEN venue_type = 'conference' AND type NOT IN"
                        " ('article','preprint','review','book-chapter') THEN 'conference-paper' ELSE type END,"
                        " count(*) FROM works WHERE NOT is_outlier GROUP BY 1 ORDER BY 2 DESC, 1")
    field_rows = _rows(conn, "SELECT coalesce(t.field, 'Unknown'), coalesce(t.subfield, 'Unknown'), count(*)"
                             " FROM works w JOIN topics t ON t.id = w.primary_topic_id WHERE NOT w.is_outlier"
                             " GROUP BY 1, 2 ORDER BY 1, 3 DESC, 2")
    fields: dict[str, dict] = {}
    for f, sub, n in field_rows:
        entry = fields.setdefault(f, {"field": f, "count": 0, "subfields": []})
        entry["count"] += n
        entry["subfields"].append({"name": sub, "count": n})
    rising = _rows(conn, """
        WITH b AS (SELECT LEAST(max(publication_date), current_date) AS maxd FROM works WHERE NOT is_outlier),
        c AS (
          SELECT t.id, t.display_name, t.field,
            count(*) FILTER (WHERE w.publication_date > b.maxd - interval '12 months') AS recent,
            count(*) FILTER (WHERE w.publication_date <= b.maxd - interval '12 months'
                             AND w.publication_date > b.maxd - interval '24 months') AS prior
          FROM works w JOIN topics t ON t.id = w.primary_topic_id CROSS JOIN b
          WHERE NOT w.is_outlier GROUP BY t.id, t.display_name, t.field)
        SELECT id, display_name, field, recent, prior, round((recent + 1)::numeric / (prior + 1), 2)
        FROM c WHERE recent >= %s ORDER BY 6 DESC, recent DESC, id LIMIT 15""", (rising_min,))
    venues = _rows(conn, "SELECT venue_name, count(*) FROM works WHERE NOT is_outlier AND venue_name IS NOT NULL"
                         " GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 15")
    top_partners = _rows(conn, "SELECT i.id, i.display_name, i.country_code, count(DISTINCT wi.work_id)"
                               " FROM work_institutions wi JOIN institutions i ON i.id = wi.institution_id"
                               " JOIN works w ON w.id = wi.work_id"
                               " WHERE NOT w.is_outlier AND NOT (i.id = ANY(%s))"
                               " GROUP BY 1, 2, 3 ORDER BY 4 DESC, 2 LIMIT 20", (EXCLUDED,))
    top_fac = _rows(conn, "SELECT f.id, f.name, count(DISTINCT s.work_id) FROM faculty f"
                          " JOIN faculty_author_link l ON l.faculty_id = f.id"
                          " JOIN authorships s ON s.author_id = l.author_id JOIN works w ON w.id = s.work_id"
                          " WHERE NOT w.is_outlier GROUP BY 1, 2 ORDER BY 3 DESC, 2 LIMIT 15")
    return {
        "overview": {"works": works, "citations": int(citations), "oa_share": round(float(oa_share), 4),
                     "faculty": faculty, "faculty_linked": linked, "partner_institutions": partners,
                     "outliers": outliers},
        "monthly": [{"month": m, "count": n} for m, n in monthly],
        "types": [{"type": t, "count": n} for t, n in types],
        "fields": sorted(fields.values(), key=lambda e: (-e["count"], e["field"])),
        "rising_topics": [{"id": i, "name": n, "field": f, "recent": r, "prior": p, "growth": float(g)}
                          for i, n, f, r, p, g in rising],
        "top_venues": [{"name": v, "count": n} for v, n in venues],
        "top_partners": [{"id": i, "name": n, "country": c, "count": k} for i, n, c, k in top_partners],
        "top_faculty": [{"id": i, "name": n, "count": k} for i, n, k in top_fac],
    }


def _update_derived(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE faculty f SET primary_field = x.field FROM (
              SELECT DISTINCT ON (l.faculty_id) l.faculty_id, t.field
              FROM faculty_author_link l JOIN authorships s ON s.author_id = l.author_id
              JOIN works w ON w.id = s.work_id JOIN topics t ON t.id = w.primary_topic_id
              WHERE NOT w.is_outlier AND t.field IS NOT NULL
              GROUP BY l.faculty_id, t.field ORDER BY l.faculty_id, count(*) DESC, t.field) x
            WHERE f.id = x.faculty_id""")
        cur.execute("UPDATE authors a SET works_count_in_set = x.n FROM ("
                    " SELECT author_id, count(*) AS n FROM authorships GROUP BY author_id) x"
                    " WHERE a.id = x.author_id")
    conn.commit()


def render_data_quality(dq_works: dict | None, dq_faculty: dict | None, dq_link: dict | None,
                        overview: dict) -> str:
    w, f, l = dq_works or {}, dq_faculty or {}, dq_link or {}
    lines = ["# Data quality report", "", "Generated by `python -m ingest aggregate`.", "", "## Works", "",
             f"- Fetched from OpenAlex: {w.get('fetched', 'n/a')} (duplicates: {w.get('duplicates', 'n/a')})",
             f"- Kept after cleaning: {w.get('kept', 'n/a')} (capped: {w.get('capped', 0)})",
             "- Dropped by reason:"]
    lines += [f"  - `{k}`: {v}" for k, v in sorted((w.get("dropped") or {}).items())] or ["  - none"]
    lines += ["- Flagged as outliers (kept, excluded from notable stats):"]
    lines += [f"  - `{k}`: {v}" for k, v in sorted((w.get("outliers") or {}).items())]
    lines += ["", "## Faculty", "",
              f"- Rows: {f.get('rows', 'n/a')}; missing photo: {f.get('missing_photo', 'n/a')};"
              f" missing position: {f.get('missing_position', 'n/a')}",
              f"- Median keywords per person: raw {f.get('keywords_raw_median', 'n/a')} →"
              f" cleaned {f.get('keywords_clean_median', 'n/a')}",
              "", "## Faculty ↔ OpenAlex author links", "",
              f"- Link rate: {100 * l.get('rate', 0):.1f}% ({l.get('linked', 0)} of {l.get('faculty', 0)})",
              f"- By method: {', '.join(f'{k} {v}' for k, v in sorted((l.get('by_method') or {}).items())) or 'n/a'}",
              f"- No candidate: {l.get('no_candidate', 'n/a')}; below confidence 0.5: {l.get('below_threshold', 'n/a')}",
              "", "## Portal totals (outliers excluded)", "",
              f"- Works: {overview['works']}; citations: {overview['citations']};"
              f" open access: {100 * overview['oa_share']:.1f}%",
              f"- Partner institutions: {overview['partner_institutions']}", ""]
    return "\n".join(lines)


def aggregate(conn: psycopg.Connection, docs_dir: Path) -> dict:
    _update_derived(conn)
    stats = compute_stats(conn)
    for key, payload in stats.items():
        put_stat(conn, key, payload)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "data-quality.md").write_text(
        render_data_quality(get_stat(conn, "dq_works"), get_stat(conn, "dq_faculty"),
                            get_stat(conn, "dq_link"), stats["overview"]), encoding="utf-8")
    return stats
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_aggregate.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add ingest/aggregate.py tests/test_aggregate.py
git commit -m "feat(ingest): portal statistics and data-quality report"
```

---

### Task 11: CLI and full real run

**Files:**
- Create: `ingest/__main__.py`
- Test: `tests/test_cli.py`
- Generated (commit): `docs/data-quality.md`; `db/dump/portal.sql.gz` (commit only if < 100 MB, otherwise attach to a GitHub release and note it in README)

**Interfaces:**
- Consumes: every earlier task.
- Produces: `python -m ingest {migrate|fetch-works|clean-works|load-faculty|embed-profiles|link-faculty|embed|aggregate|all} [--force] [--refresh-filter]`; `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing test** — `tests/test_cli.py`
```python
import pytest

from ingest.__main__ import build_parser


def test_parser_accepts_all_steps():
    p = build_parser()
    for cmd in ["migrate", "fetch-works", "clean-works", "load-faculty", "embed-profiles", "link-faculty",
                "embed", "aggregate", "all"]:
        assert p.parse_args([cmd]).cmd == cmd
    assert p.parse_args(["embed", "--force"]).force is True
    with pytest.raises(SystemExit):
        p.parse_args(["nope"])
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_cli.py -v` → FAIL.

- [ ] **Step 3: Implement** — `ingest/__main__.py`
```python
from __future__ import annotations

import argparse
import sys
from datetime import date

import httpx

from .aggregate import aggregate
from .config import load_settings
from .db import apply_migrations, connect
from .embed import embed_faculty, embed_works
from .embedder import EmbedderUnavailable, OllamaEmbedder
from .faculty import load_faculty
from .linking import embed_profiles, link_faculty
from .load_works import load_works
from .openalex import OpenAlexClient, QuotaExhausted, page_dir_for, read_cached_results, resolve_filter

STEPS = ["fetch-works", "clean-works", "load-faculty", "embed-profiles", "link-faculty", "embed", "aggregate"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m ingest", description="UIUC portal ingest pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ["migrate", *STEPS, "all"]:
        sp = sub.add_parser(name)
        sp.add_argument("--force", action="store_true", help="recompute embeddings from scratch")
        sp.add_argument("--refresh-filter", action="store_true", help="recompute the 2-year window from today")
    return p


def run_step(step: str, s, conn, http: httpx.Client, force: bool, refresh: bool) -> None:
    filter_str = resolve_filter(s.cache_dir, date.today(), refresh=refresh and step == "fetch-works")
    embedder = OllamaEmbedder(http, s.ollama_url, s.embed_model)
    if step == "fetch-works":
        client = OpenAlexClient(http, s.cache_dir, api_key=s.openalex_api_key, mailto=s.openalex_mailto)
        total = 0
        for page in client.iter_pages(filter_str):
            total += len(page)
            print(f"fetch-works: {total} works", flush=True)
    elif step == "clean-works":
        print(load_works(conn, read_cached_results(page_dir_for(s.cache_dir, filter_str))))
    elif step == "load-faculty":
        print(load_faculty(conn, s.data_dir / "illinois-researchers.csv", s.data_dir))
    elif step == "embed-profiles":
        print(embed_profiles(conn, embedder))
    elif step == "link-faculty":
        print(link_faculty(conn))
    elif step == "embed":
        print("works embedded:", embed_works(conn, embedder, force=force,
                                             progress=lambda m: print(m, flush=True)))
        print("faculty embedded:", embed_faculty(conn, embedder, force=force))
    elif step == "aggregate":
        print(aggregate(conn, s.docs_dir)["overview"])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    s = load_settings()
    conn = connect(s.database_url)
    try:
        print("migrations applied:", apply_migrations(conn))
        if args.cmd == "migrate":
            return 0
        steps = STEPS if args.cmd == "all" else [args.cmd]
        with httpx.Client(headers={"User-Agent": "uiuc-research-portal-ingest"}) as http:
            for step in steps:
                print(f"== {step}", flush=True)
                run_step(step, s, conn, http, args.force, args.refresh_filter)
        return 0
    except QuotaExhausted as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 2
    except EmbedderUnavailable as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 3
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run all tests** — `uv run pytest -q` → all PASS.

- [ ] **Step 5: Real run, step by step** (Ollama must be running with `bge-m3`)

```bash
uv run python -m ingest fetch-works     # ~135 requests, ~$0.014; prints running total ≈ 26,9xx
uv run python -m ingest clean-works     # prints report; expect kept ≈ 15–20k, outliers include non_english_high_citation ≥ 1
uv run python -m ingest load-faculty    # rows 1000, missing_photo 105, missing_position 2
uv run python -m ingest embed-profiles
uv run python -m ingest link-faculty    # expect rate 0.70–0.85
uv run python -m ingest embed           # longest step; prints throughput
uv run python -m ingest aggregate
```

Spot checks (run in `docker compose exec db psql -U portal -d portal`):
```sql
SELECT id, title, language, cited_by_count, outlier_reason FROM works WHERE is_outlier ORDER BY cited_by_count DESC LIMIT 5;
-- expect the Russian psychology paper (8,198 citations) flagged non_english_high_citation
SELECT count(*) FILTER (WHERE embedding IS NULL) FROM works;   -- expect 0
SELECT method, count(*), round(avg(confidence)::numeric, 2) FROM faculty_author_link GROUP BY 1;
SELECT f.name, a.display_name, l.method, l.confidence FROM faculty_author_link l
  JOIN faculty f ON f.id = l.faculty_id JOIN authors a ON a.id = l.author_id
  WHERE l.method = 'initial_last' ORDER BY random() LIMIT 15;   -- manually verify ~15 initial-tier links
```
If link rate < 0.70 or the manual check shows more than 2 wrong links out of 15, record the finding in `docs/data-quality.md` under a "Known issues" heading. Do not tune silently.

- [ ] **Step 6: Dump**

Run: `make dump && ls -lh db/dump/portal.sql.gz`

- [ ] **Step 7: Commit**
```bash
git add ingest/__main__.py tests/test_cli.py docs/data-quality.md
git commit -m "feat(ingest): CLI for full pipeline; first real ingest + data-quality report"
```

---

## Self-review notes

- **Spec coverage:**
  - §2.1 (OpenAlex): Tasks 3 and 11.
  - §2.2 (faculty CSV): Task 5.
  - §4 (schema): Task 1. `author_profile` and `faculty.keyword_embedding` implement the "embed-profiles" storage from §5.4.
  - §5 steps 1–8: Tasks 3, 4, 5, 8, 8, 9, 10, 11.
  - §9 (ingest errors): Tasks 3, 7, 11.
  - §11 (compose/Makefile/env for db + ingest): Task 1.
  - `institution.json` (§2.3) is hand-authored content consumed by the API/web, so it is in Plan 2. `synonyms.yaml` is also in Plan 2.
- **Deviation from spec, flagged:** embed-profiles stores faculty keyword vectors on `faculty.keyword_embedding` rather than in a shared temp table. The spec text should say "`faculty.keyword_embedding` + `author_profile`".
- **Known finding from real data (2026-11-17 probe):** the top-cited "outlier" lists UIUC in `institutions` and its raw affiliation contains "University of Illinois", so outlier rule (a) cannot catch it. Rule (b) does. Keep both rules and report counts.
