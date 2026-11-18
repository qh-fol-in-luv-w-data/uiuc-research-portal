from ingest.aggregate import aggregate
from ingest.db import get_stat, put_stat
from ingest.load_works import load_works
from tests.factories import HERZEN, UIUC, UISYS, make_author, make_topic, make_work


def test_aggregate_stats(db, tmp_path):
    works = [
        make_work(id="W1", title="Paper one", date="2025-01-10", cited=5, authorships=[
            make_author("A1", "Jane Doe", [UIUC, UISYS], "UIUC"),
            make_author("A2", "Ivan P", [HERZEN], "Herzen", position="last")]),
        make_work(id="W2", title="Paper two", date="2025-01-20", cited=7, source_type="conference", type="other"),
        make_work(id="W3", title="Paper three", date="2025-02-01", cited=1, topic=make_topic("T2", "Organic Synthesis",
                  "Organic Chemistry", "Chemistry", "Physical Sciences")),
        make_work(id="W4", title="Paper four", authorships=[make_author("A3", "Q", [HERZEN], "Herzen")]),  # outlier
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
    assert stats["top_faculty"] == [{"id": 1, "name": "Jane Doe", "count": 3}]  # factory default author A1 is on W1–W3
    assert get_stat(db, "monthly") == stats["monthly"]
    with db.cursor() as cur:
        cur.execute("SELECT primary_field FROM faculty WHERE id = 1")
        assert cur.fetchone()[0] == "Computer Science"
    report = (tmp_path / "data-quality.md").read_text()
    assert "Link rate" in report and "100.0%" in report


def test_partners_exclude_units_and_stats_skip_duplicates(db, tmp_path):
    woese = {"id": "https://openalex.org/I4405271866", "display_name": "Woese IGB", "country_code": "US",
             "type": "facility", "lineage": ["https://openalex.org/I4405271866"]}
    works = [
        make_work(id="W1", authorships=[make_author("A1", "Jane Doe", [UIUC, woese], "UIUC"),
                                        make_author("A2", "Ivan P", [HERZEN], "Herzen", position="last")]),
        make_work(id="W2", type="preprint", authorships=[make_author("A1", "Jane Doe", [UIUC], "UIUC")]),
    ]
    load_works(db, works, uiuc_units=frozenset({"I157725225", "I4405271866"}))
    stats = aggregate(db, tmp_path)
    assert [p["name"] for p in stats["top_partners"]] == ["Herzen University"]
    assert stats["overview"]["works"] == 1  # W2 is a duplicate version of W1
    assert stats["overview"]["duplicates"] == 1


def test_by_field_rising_and_top_faculty(db, tmp_path):
    chem = make_topic("T2", "Organic Synthesis", "Organic Chemistry", "Chemistry", "Physical Sciences")
    works = [make_work(id=f"W{i}", title=f"Vision paper {i}", date="2026-06-01") for i in range(3)]
    works += [make_work(id=f"C{i}", title=f"Chem paper {i}", date="2026-06-01", topic=chem,
                        authorships=[make_author("A5", "Bob Smith", [UIUC], "UIUC")]) for i in range(10)]
    load_works(db, works)
    with db.cursor() as cur:
        cur.execute("INSERT INTO faculty (id, email, name) VALUES (1, 'j@x', 'John Smith'), (2, 'b@x', 'Bob Smith')")
        cur.execute("INSERT INTO faculty_author_link VALUES (1, 'A1', 0.9, 'exact'), (2, 'A5', 0.9, 'exact')")
    db.commit()
    stats = aggregate(db, tmp_path)
    by_field = stats["by_field"]
    assert by_field["Computer Science"]["top_faculty"] == [{"id": 1, "name": "John Smith", "count": 3}]
    assert by_field["Chemistry"]["top_faculty"] == [{"id": 2, "name": "Bob Smith", "count": 10}]
    assert by_field["Chemistry"]["rising"][0]["name"] == "Organic Synthesis"
    assert get_stat(db, "by_field") == by_field
