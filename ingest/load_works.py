from __future__ import annotations

from collections import Counter
from typing import Iterable

import psycopg

from .db import put_stat
from .works import ParsedWork, cap_by_date, drop_reason, mark_outliers, parse_work

WORK_COLS = ["id", "doi", "title", "abstract", "publication_date", "type", "language", "cited_by_count",
             "is_oa", "oa_url", "venue_name", "venue_type", "primary_topic_id", "is_outlier", "outlier_reason"]


def upsert_parsed(conn: psycopg.Connection, items: list[ParsedWork]) -> None:
    topics = {t["id"]: t for p in items for t in p.topics}
    insts = {i["id"]: i for p in items for i in p.institutions}
    authors = {a["id"]: a for p in items for a in p.authors}
    cols = ", ".join(WORK_COLS)
    vals = ", ".join(f"%({c})s" for c in WORK_COLS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in WORK_COLS if c != "id")
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO topics (id, display_name, subfield, field, domain)"
            " VALUES (%(id)s, %(display_name)s, %(subfield)s, %(field)s, %(domain)s)"
            " ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name,"
            " subfield = EXCLUDED.subfield, field = EXCLUDED.field, domain = EXCLUDED.domain",
            list(topics.values()))
        cur.executemany(
            "INSERT INTO institutions (id, display_name, country_code, type)"
            " VALUES (%(id)s, %(display_name)s, %(country_code)s, %(type)s)"
            " ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name,"
            " country_code = EXCLUDED.country_code, type = EXCLUDED.type",
            list(insts.values()))
        cur.executemany(
            "INSERT INTO authors (id, display_name, orcid) VALUES (%(id)s, %(display_name)s, %(orcid)s)"
            " ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, orcid = EXCLUDED.orcid",
            list(authors.values()))
        cur.executemany(
            f"INSERT INTO works ({cols}) VALUES ({vals}) ON CONFLICT (id) DO UPDATE SET {updates}",
            [p.work for p in items])
        ids = [p.work["id"] for p in items]
        cur.execute("DELETE FROM works WHERE NOT (id = ANY(%s))", (ids,))
        cur.execute("DELETE FROM authorships WHERE work_id = ANY(%s)", (ids,))
        cur.execute("DELETE FROM work_institutions WHERE work_id = ANY(%s)", (ids,))
        cur.execute("DELETE FROM work_topics WHERE work_id = ANY(%s)", (ids,))
        cur.executemany(
            "INSERT INTO authorships (work_id, author_id, position, is_uiuc, raw_affiliation)"
            " VALUES (%(work_id)s, %(author_id)s, %(position)s, %(is_uiuc)s, %(raw_affiliation)s)",
            [a for p in items for a in p.authorships])
        cur.executemany(
            "INSERT INTO work_institutions (work_id, institution_id) VALUES (%s, %s)",
            [(p.work["id"], iid) for p in items for iid in p.work_institutions])
        cur.executemany(
            "INSERT INTO work_topics (work_id, topic_id, score) VALUES (%s, %s, %s)",
            [(p.work["id"], tid, score) for p in items for tid, score in p.work_topics])
    conn.commit()


def load_works(conn: psycopg.Connection, raw_works: Iterable[dict], cap: int = 25000) -> dict:
    fetched = duplicates = 0
    dropped: Counter[str] = Counter()
    seen: set[str] = set()
    parsed: list[ParsedWork] = []
    for w in raw_works:
        fetched += 1
        if w.get("id") in seen:
            duplicates += 1
            continue
        seen.add(w.get("id"))
        reason = drop_reason(w)
        if reason:
            dropped[reason] += 1
            continue
        parsed.append(parse_work(w))
    outliers = mark_outliers(parsed)
    kept_before_cap = len(parsed)
    parsed = cap_by_date(parsed, limit=cap)
    upsert_parsed(conn, parsed)
    report = {"fetched": fetched, "duplicates": duplicates, "dropped": dict(dropped), "kept": len(parsed),
              "outliers": outliers, "capped": kept_before_cap - len(parsed)}
    put_stat(conn, "dq_works", report)
    return report
