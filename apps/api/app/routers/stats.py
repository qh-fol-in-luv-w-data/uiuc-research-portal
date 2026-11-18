import json
from typing import get_args

from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import get_conn
from ..schemas import Institution, Overview, StatsKey, StatsPayload

router = APIRouter(prefix="/api")


def _stat(conn, key: str):
    with conn.cursor() as cur:
        cur.execute("SELECT payload, computed_at FROM stats_cache WHERE key = %s", (key,))
        return cur.fetchone()


@router.get("/overview", response_model=Overview)
def overview(request: Request, conn=Depends(get_conn)) -> Overview:
    row = _stat(conn, "overview")
    if not row:
        raise HTTPException(503, "Statistics not computed yet. Run: python -m ingest aggregate")
    path = request.app.state.institution_path
    inst = Institution(**json.loads(path.read_text())) if path.exists() else None
    return Overview(**row[0], computed_at=row[1], institution=inst)


@router.get("/stats/{key}", response_model=StatsPayload)
def stats(key: str, conn=Depends(get_conn)) -> StatsPayload:
    if key not in get_args(StatsKey):
        raise HTTPException(404, f"Unknown stats key: {key}")
    row = _stat(conn, key)
    if not row:
        raise HTTPException(503, f"Statistic {key} not computed yet. Run: python -m ingest aggregate")
    return StatsPayload(key=key, computed_at=row[1], data=row[0])
