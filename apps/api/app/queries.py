"""SQL shared by the works and faculty routers."""
from __future__ import annotations

from collections import defaultdict

from .schemas import AuthorRef, WorkCard

LIVE = "NOT w.is_outlier AND w.duplicate_of IS NULL"
POSITION_ORDER = "CASE s.position WHEN 'first' THEN 0 WHEN 'middle' THEN 1 ELSE 2 END"


def uiuc_authors(conn, work_ids: list[str]) -> dict[str, list[AuthorRef]]:
    out: dict[str, list[AuthorRef]] = defaultdict(list)
    if not work_ids:
        return out
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT s.work_id, a.display_name, min(l.faculty_id) FROM authorships s"
            f" JOIN authors a ON a.id = s.author_id"
            f" LEFT JOIN faculty_author_link l ON l.author_id = s.author_id"
            f" WHERE s.work_id = ANY(%s) AND s.is_uiuc"
            f" GROUP BY s.work_id, a.display_name, {POSITION_ORDER}, a.id ORDER BY s.work_id, {POSITION_ORDER}, a.id",
            (work_ids,))
        for wid, name, fid in cur.fetchall():
            out[wid].append(AuthorRef(name=name, faculty_id=fid))
    return out


def work_cards(conn, rows: list[tuple]) -> list[WorkCard]:
    """rows: (id, title, publication_date, type, venue_name, cited_by_count, is_oa, doi, field)"""
    authors = uiuc_authors(conn, [r[0] for r in rows])
    return [WorkCard(id=r[0], title=r[1], publication_date=r[2], type=r[3], venue=r[4], cited_by_count=r[5],
                     is_oa=r[6], doi=r[7], field=r[8], uiuc_authors=authors.get(r[0], [])) for r in rows]


WORK_SELECT = ("SELECT w.id, w.title, w.publication_date, w.type, w.venue_name, w.cited_by_count, w.is_oa,"
               " w.doi, t.field")
