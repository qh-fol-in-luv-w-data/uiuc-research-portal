from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import TEST_URL

from .conftest import FakeOllama


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"db": True, "ollama": True, "models": ["qwen3:4b", "bge-m3:latest"], "missing_models": []}


def test_health_reports_ollama_down_without_failing(db, tmp_path):
    app = create_app(database_url=TEST_URL, institution_path=tmp_path / "none.json", ollama=FakeOllama(up=False))
    with TestClient(app) as c:
        body = c.get("/health").json()
    assert body["db"] is True and body["ollama"] is False
    assert body["missing_models"] == ["qwen3:4b", "bge-m3"]


def test_overview_merges_institution(client):
    body = client.get("/api/overview").json()
    assert body["works"] == 3 and body["faculty_linked"] == 1
    assert body["institution"]["founded"] == 1867


def test_stats_key_and_unknown_key(client):
    r = client.get("/api/stats/monthly")
    assert r.status_code == 200 and r.json()["data"] == [{"month": "2025-03", "count": 1}]
    bad = client.get("/api/stats/nope")
    assert bad.status_code == 404
    assert bad.json() == {"error": "not_found", "detail": "Unknown stats key: nope"}
