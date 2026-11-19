import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from ingest.db import put_stat
from ingest.load_works import load_works
from tests.conftest import TEST_URL, db  # noqa: F401  (re-exported fixture)
from tests.factories import HERZEN, UIUC, make_author, make_topic, make_work

BIO = make_topic("T2", "Organic Synthesis", "Organic Chemistry", "Chemistry", "Physical Sciences")


class FakeOllama:
    def __init__(self, up=True, models=("qwen3:4b-instruct-2507-q4_K_M", "bge-m3:latest")):
        self.up, self.models = up, list(models)

    def tags(self):
        if not self.up:
            raise ConnectionError("down")
        return self.models


def seed(conn):
    works = [
        make_work(id="W1", title="Deep learning for drone detection", date="2025-03-01", cited=50,
                  authorships=[make_author("A1", "Jane Doe", [UIUC], "UIUC"),
                               make_author("A2", "Ivan P", [HERZEN], "Herzen", position="last")]),
        make_work(id="W2", title="Vision transformers for radiology", date="2026-02-01", cited=5,
                  authorships=[make_author("A1", "Jane Doe", [UIUC], "UIUC")]),
        make_work(id="W3", title="Catalysis of organic synthesis", date="2025-06-01", cited=20, topic=BIO,
                  authorships=[make_author("A3", "Bob Smith", [UIUC], "UIUC")]),
        make_work(id="W4", title="Stray paper", authorships=[make_author("A9", "Q", [HERZEN], "Herzen")]),
    ]
    load_works(conn, works)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO faculty (id, email, name, position, keywords, keywords_text, primary_field) VALUES"
                    " (1, 'jd@x', 'Jane Doe', 'Professor', '{computer vision,medical imaging}',"
                    " 'computer vision, medical imaging', 'Computer Science'),"
                    " (2, 'bs@x', 'Bob Smith', 'Assistant Professor', '{organic chemistry}', 'organic chemistry',"
                    " 'Chemistry')")
        cur.execute("INSERT INTO faculty_author_link VALUES (1, 'A1', 0.9, 'exact')")
    conn.commit()
    put_stat(conn, "overview", {"works": 3, "citations": 75, "oa_share": 1.0, "faculty": 2, "faculty_linked": 1,
                                "partner_institutions": 1, "outliers": 1, "duplicates": 0})
    put_stat(conn, "monthly", [{"month": "2025-03", "count": 1}])


@pytest.fixture
def client(db, tmp_path):  # noqa: F811
    seed(db)
    inst = tmp_path / "institution.json"
    inst.write_text(json.dumps({"name": "University of Illinois Urbana-Champaign", "founded": 1867,
                                "latitude": 40.1, "longitude": -88.2, "images": []}))
    app = create_app(database_url=TEST_URL, institution_path=inst, ollama=FakeOllama())
    with TestClient(app) as c:
        yield c
