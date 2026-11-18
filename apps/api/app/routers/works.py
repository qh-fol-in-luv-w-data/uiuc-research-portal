from typing import Literal

from fastapi import APIRouter, Depends, Query

from ..deps import get_conn
from ..queries import LIVE, WORK_SELECT, work_cards
from ..schemas import Page, WorkCard

router = APIRouter(prefix="/api")

ORDER = {
    "recent": "w.publication_date DESC NULLS LAST, w.cited_by_count DESC, w.id",
    "cited": "w.cited_by_count DESC, w.publication_date DESC NULLS LAST, w.id",
}


@router.get("/works", response_model=Page[WorkCard])
def list_works(q: str | None = None, field: str | None = None,
               sort: Literal["recent", "cited", "relevance"] = "relevance",
               page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
               conn=Depends(get_conn)) -> Page[WorkCard]:
    where, params = [LIVE], {}
    if field:
        where.append("t.field = %(field)s")
        params["field"] = field
    if q:
        where.append("w.tsv @@ websearch_to_tsquery('english', %(q)s)")
        params["q"] = q
    if sort == "recent":
        where.append("w.publication_date <= current_date")  # hide future-dated issue dates
    if sort == "relevance" and q:
        order = "ts_rank(w.tsv, websearch_to_tsquery('english', %(q)s)) DESC, w.cited_by_count DESC, w.id"
    else:
        order = ORDER.get(sort, ORDER["cited"])
    params.update(limit=page_size, offset=(page - 1) * page_size)
    with conn.cursor() as cur:
        cur.execute(f"{WORK_SELECT}, count(*) OVER () FROM works w LEFT JOIN topics t ON t.id = w.primary_topic_id"
                    f" WHERE {' AND '.join(where)} ORDER BY {order} LIMIT %(limit)s OFFSET %(offset)s", params)
        rows = cur.fetchall()
    total = rows[0][-1] if rows else 0
    return Page[WorkCard](items=work_cards(conn, [r[:-1] for r in rows]), total=total, page=page, page_size=page_size)
