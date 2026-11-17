from ingest.db import apply_migrations, get_stat, put_stat


def test_schema_has_all_tables(db):
    with db.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = {r[0] for r in cur.fetchall()}
    assert {
        "works", "authors", "authorships", "institutions", "work_institutions", "topics",
        "work_topics", "faculty", "author_profile", "faculty_author_link", "stats_cache",
        "schema_migrations",
    } <= tables


def test_migrations_are_idempotent(db):
    assert apply_migrations(db) == []


def test_put_and_get_stat_roundtrip(db):
    put_stat(db, "k", {"a": [1, 2]})
    put_stat(db, "k", {"a": [3]})
    assert get_stat(db, "k") == {"a": [3]}
    assert get_stat(db, "missing") is None
