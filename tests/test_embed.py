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
