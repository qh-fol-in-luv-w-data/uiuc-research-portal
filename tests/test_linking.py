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
