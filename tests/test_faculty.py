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


def test_load_faculty_reports_unique_rows(db, tmp_path):
    p = tmp_path / "f.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["email", "name", "photo_url", "position", "keywords"])
        w.writerow(["a@illinois.edu", "A One", "NULL", "Professor", "{x1}"])
        w.writerow(["A@illinois.edu", "A One", "NULL", "Professor", "{x2}"])
    report = load_faculty(db, p, tmp_path)
    assert report["rows"] == 1 and report["duplicate_emails"] == ["a@illinois.edu"]
