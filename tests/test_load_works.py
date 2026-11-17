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
