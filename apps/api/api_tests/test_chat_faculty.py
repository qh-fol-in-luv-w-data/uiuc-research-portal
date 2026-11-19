import numpy as np

from app.chat.config import ChatConfig
from app.chat.retrieve import FacultyIndex, search_faculty

CFG = ChatConfig()
PLAN = {"intent": "faculty", "standalone_question": "Which faculty work on computer vision in healthcare?",
        "concepts": [["computer vision", "image analysis"], ["healthcare", "medical", "clinical"]],
        "date_from": None, "date_to": None, "sort": "relevance", "limit": 5}


def vec(*idx):
    v = np.zeros(1024, dtype=np.float32)
    for i in idx:
        v[i] = 1.0
    return v / np.linalg.norm(v)


def seed(db):
    with db.cursor() as cur:
        rows = [
            (1, "Both Groups", ["computer vision", "medical imaging", "deep learning"], vec(0, 1)),
            (2, "Vision Only", ["computer vision", "robotics", "deep learning"], vec(0)),
            (3, "Health Only", ["clinical trials", "public health"], vec(1)),
            (4, "Unrelated", ["soil science", "deep learning"], vec(5)),
        ]
        for fid, name, kw, emb in rows:
            cur.execute("INSERT INTO faculty (id, email, name, position, keywords, keywords_text, embedding)"
                        " VALUES (%s, %s, %s, 'Professor', %s, %s, %s)", (fid, f"{fid}@x", name, kw, ", ".join(kw), emb))
        cur.execute("INSERT INTO works (id, title, publication_date) VALUES ('W1', 'Vision models for radiology', '2025-01-01')")
        cur.execute("INSERT INTO authors (id, display_name) VALUES ('A1', 'Both Groups')")
        cur.execute("INSERT INTO authorships (work_id, author_id, is_uiuc) VALUES ('W1', 'A1', true)")
        cur.execute("INSERT INTO faculty_author_link VALUES (1, 'A1', 0.9, 'exact')")
    db.commit()


def test_matching_every_group_ranks_first_with_evidence(db):
    seed(db)
    idx = FacultyIndex.load(db)
    related = [{"id": "W1", "title": "Vision models for radiology"}]
    hits = search_faculty(idx, PLAN, vec(0, 1), related, CFG)
    assert [h["name"] for h in hits[:3]] == ["Both Groups", "Vision Only", "Health Only"] or hits[0]["name"] == "Both Groups"
    top = hits[0]
    assert top["name"] == "Both Groups"
    assert "computer vision" in top["matched_keywords"] and "medical imaging" in top["matched_keywords"]
    assert top["related_papers"] == ["Vision models for radiology"]
    assert "Unrelated" not in [h["name"] for h in hits]  # matches no concept group


def test_rare_keyword_outweighs_common_one(db):
    seed(db)
    idx = FacultyIndex.load(db)
    assert idx.idf["medical imaging"] > idx.idf["deep learning"]


def test_full_coverage_beats_partial_coverage_with_more_papers(db):
    seed(db)
    with db.cursor() as cur:  # give "Health Only" two related papers: still below the two-group match
        cur.execute("INSERT INTO works (id, title) VALUES ('W2','Clinical AI'),('W3','Hospital AI')")
        cur.execute("INSERT INTO authors (id, display_name) VALUES ('A3','Health Only')")
        cur.execute("INSERT INTO authorships (work_id, author_id, is_uiuc) VALUES ('W2','A3',true),('W3','A3',true)")
        cur.execute("INSERT INTO faculty_author_link VALUES (3, 'A3', 0.9, 'exact')")
    db.commit()
    idx = FacultyIndex.load(db)
    related = [{"id": "W1", "title": "Vision models for radiology"}, {"id": "W2", "title": "Clinical AI"},
               {"id": "W3", "title": "Hospital AI"}]
    assert search_faculty(idx, PLAN, vec(0, 1), related, CFG)[0]["name"] == "Both Groups"
