import gzip
import json

import httpx

from ingest.bootstrap import db_is_empty, dump_source, ensure_models


def test_db_is_empty(db):
    assert db_is_empty(db) is True
    with db.cursor() as cur:
        cur.execute("INSERT INTO works (id, title) VALUES ('W1', 't')")
    db.commit()
    assert db_is_empty(db) is False


def test_dump_source_prefers_local_file(tmp_path):
    local = tmp_path / "portal.sql.gz"
    assert dump_source(local, "https://example.org/d.gz") == "https://example.org/d.gz"
    local.write_bytes(gzip.compress(b"select 1;"))
    assert dump_source(local, "https://example.org/d.gz") == str(local)
    assert dump_source(tmp_path / "missing.gz", "") is None


def test_ensure_models_pulls_only_missing():
    pulled = []

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "bge-m3:latest"}]})
        pulled.append(json.loads(request.content)["model"])
        return httpx.Response(200, json={"status": "success"})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    assert ensure_models(http, "http://o", ["qwen3:4b", "bge-m3"]) == {"pulled": ["qwen3:4b"], "present": ["bge-m3"]}
    assert pulled == ["qwen3:4b"]


def test_ensure_models_tolerates_missing_ollama():
    def handler(request):
        raise httpx.ConnectError("refused")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    assert ensure_models(http, "http://o", ["qwen3:4b"]) == {"error": "Ollama not reachable at http://o"}


def test_db_is_empty_leaves_no_open_transaction(db):
    # an open transaction would hold a lock on `works` and block psql's DROP during restore
    from psycopg.pq import TransactionStatus
    db_is_empty(db)
    assert db.info.transaction_status == TransactionStatus.IDLE
