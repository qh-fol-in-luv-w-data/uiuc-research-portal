import numpy as np

from app.chat.config import ChatConfig
from app.chat.retrieve import search_papers
from ingest.load_works import load_works
from tests.factories import UIUC, make_author, make_work

CFG = ChatConfig(tau=0.55, pool=50)


def axis(*idx):
    v = np.zeros(1024, dtype=np.float32)
    for i in idx:
        v[i] = 1.0
    return v / np.linalg.norm(v)


PLAN = {"intent": "papers", "standalone_question": "recent papers on AI in war", "date_from": None, "date_to": None,
        "concepts": [["ai", "machine learning"], ["war", "military", "armed conflict"]], "sort": "recent", "limit": 5}
GROUP_VECS = [axis(0), axis(1)]
QVEC = axis(0, 1)


def seed(db):
    a = [make_author("A1", "Jane Doe", [UIUC], "UIUC")]
    works = [
        make_work(id="WBOTH", title="Machine learning for military logistics", date="2025-05-01", authorships=a),
        make_work(id="WAIONLY", title="Machine learning for protein folding", date="2026-01-01", authorships=a),
        make_work(id="WVEC", title="Algorithmic targeting and the ethics of lethal autonomy", date="2025-09-01", authorships=a),
        make_work(id="WOUT", title="Machine learning in armed conflict zones", date="2026-02-01", authorships=a),
        make_work(id="WFUT", title="Military applications of machine learning", date="2027-03-01", authorships=a),
    ]
    load_works(db, works)
    vecs = {"WBOTH": axis(0, 1), "WAIONLY": axis(0), "WVEC": axis(0, 1), "WOUT": axis(0, 1), "WFUT": axis(0, 1)}
    with db.cursor() as cur:
        for wid, v in vecs.items():
            cur.execute("UPDATE works SET embedding = %s WHERE id = %s", (v, wid))
        cur.execute("UPDATE works SET is_outlier = true WHERE id = 'WOUT'")
    db.commit()


def test_concept_groups_must_all_match_by_text_or_meaning(db):
    seed(db)
    ids = [h["id"] for h in search_papers(db, PLAN, QVEC, GROUP_VECS, CFG)]
    assert "WAIONLY" not in ids          # matches only the AI group
    assert "WVEC" in ids                 # no keyword for either group, kept by meaning (cosine 0.71 >= tau)
    assert "WOUT" not in ids             # outlier never returned


def test_recent_sort_excludes_future_dates(db):
    seed(db)
    hits = search_papers(db, PLAN, QVEC, GROUP_VECS, CFG)
    assert [h["id"] for h in hits] == ["WVEC", "WBOTH"]
    assert hits[0]["uiuc_authors"] == ["Jane Doe"] and hits[0]["matched_by"] == ["meaning", "meaning"]
    assert hits[1]["matched_by"] == ["text", "text"]


def test_date_window_and_cited_sort(db):
    seed(db)
    plan = {**PLAN, "sort": "cited", "date_from": "2025-06-01", "date_to": "2025-12-31"}
    assert [h["id"] for h in search_papers(db, plan, QVEC, GROUP_VECS, CFG)] == ["WVEC"]
