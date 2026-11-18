import re

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_conn
from ..queries import LIVE, WORK_SELECT, work_cards
from ..schemas import FacultyCard, FacultyProfile, Page, TopicCount

router = APIRouter(prefix="/api")

CARD_SELECT = ("SELECT f.id, f.name, f.position, f.photo_url, f.primary_field, f.keywords,"
               " (SELECT max(confidence) FROM faculty_author_link l WHERE l.faculty_id = f.id)")


def _terms(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", q.lower()) if len(t) >= 3]


def _matched(keywords: list[str], q: str | None) -> list[str]:
    if not q:
        return []
    terms = _terms(q)
    phrase = q.lower().strip()
    hits = [k for k in keywords if k in phrase or phrase in k or any(re.search(rf"\b{t}", k) for t in terms)]
    return sorted(hits, key=lambda k: -sum(t in k for t in terms))[:6]


def _card(row, q: str | None = None) -> FacultyCard:
    return FacultyCard(id=row[0], name=row[1], position=row[2], photo_url=row[3], primary_field=row[4],
                       keywords=row[5], matched_keywords=_matched(row[5], q), link_confidence=row[6])


@router.get("/faculty", response_model=Page[FacultyCard])
def list_faculty(q: str | None = None, position: str | None = None, field: str | None = None,
                 page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50),
                 conn=Depends(get_conn)) -> Page[FacultyCard]:
    where, params = ["true"], {}
    if q:
        where.append("f.tsv @@ websearch_to_tsquery('english', %(q)s)")
        params["q"] = q
    if position:
        where.append("f.position ILIKE %(position)s")
        params["position"] = f"%{position}%"
    if field:
        where.append("f.primary_field = %(field)s")
        params["field"] = field
    order = "ts_rank(f.tsv, websearch_to_tsquery('english', %(q)s)) DESC, f.name" if q else "f.name"
    params.update(limit=page_size, offset=(page - 1) * page_size)
    with conn.cursor() as cur:
        cur.execute(f"{CARD_SELECT}, count(*) OVER () FROM faculty f WHERE {' AND '.join(where)}"
                    f" ORDER BY {order} LIMIT %(limit)s OFFSET %(offset)s", params)
        rows = cur.fetchall()
    total = rows[0][-1] if rows else 0
    return Page[FacultyCard](items=[_card(r[:-1], q) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/faculty/{faculty_id}", response_model=FacultyProfile)
def faculty_profile(faculty_id: int, conn=Depends(get_conn)) -> FacultyProfile:
    with conn.cursor() as cur:
        cur.execute(f"{CARD_SELECT} FROM faculty f WHERE f.id = %s", (faculty_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"No faculty member with id {faculty_id}")
        cur.execute("SELECT author_id, method FROM faculty_author_link WHERE faculty_id = %s"
                    " ORDER BY confidence DESC, author_id", (faculty_id,))
        links = cur.fetchall()
        author_ids = [a for a, _ in links]
        cur.execute(f"{WORK_SELECT} FROM works w LEFT JOIN topics t ON t.id = w.primary_topic_id"
                    f" WHERE {LIVE} AND w.id IN (SELECT work_id FROM authorships WHERE author_id = ANY(%s))"
                    f" AND w.publication_date <= current_date"
                    f" ORDER BY w.publication_date DESC NULLS LAST, w.id LIMIT 5", (author_ids,))
        recent = cur.fetchall()
        cur.execute(f"SELECT t.display_name, count(*) FROM works w JOIN topics t ON t.id = w.primary_topic_id"
                    f" WHERE {LIVE} AND w.id IN (SELECT work_id FROM authorships WHERE author_id = ANY(%s))"
                    f" GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 8", (author_ids,))
        topics = cur.fetchall()
    card = _card(row)
    return FacultyProfile(**card.model_dump(), link_method=links[0][1] if links else None,
                          openalex_author_ids=author_ids, recent_works=work_cards(conn, recent),
                          topics=[TopicCount(name=n, count=c) for n, c in topics])
