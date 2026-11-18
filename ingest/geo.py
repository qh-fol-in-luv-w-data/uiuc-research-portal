from __future__ import annotations

import json
from pathlib import Path

import httpx
import psycopg

from .db import put_stat
from .units import fetch_institution
from .works import UI_SYSTEM_ID, UIUC_ID


def partner_map(conn: psycopg.Connection, http: httpx.Client, cache_dir: Path, limit: int = 40) -> list[dict]:
    """Top external partners with coordinates, for the collaboration map (stats key `partner_map`)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT i.id, i.display_name, i.country_code, count(DISTINCT wi.work_id) FROM work_institutions wi"
            " JOIN institutions i ON i.id = wi.institution_id JOIN works w ON w.id = wi.work_id"
            " WHERE NOT w.is_outlier AND w.duplicate_of IS NULL AND NOT i.is_uiuc_unit AND NOT (i.id = ANY(%s))"
            " GROUP BY 1, 2, 3 ORDER BY 4 DESC, 2 LIMIT %s", ([UIUC_ID, UI_SYSTEM_ID], limit))
        partners = cur.fetchall()
    geo_dir = cache_dir / "institutions"
    geo_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for iid, name, country, n in partners:
        path = geo_dir / f"{iid}.json"
        if path.exists():
            geo = json.loads(path.read_text())
        else:
            geo = fetch_institution(http, iid).get("geo") or {}
            path.write_text(json.dumps(geo))
        if geo.get("latitude") is None or geo.get("longitude") is None:
            continue
        rows.append({"id": iid, "name": name, "country": country, "count": n,
                     "lat": geo["latitude"], "lon": geo["longitude"], "city": geo.get("city")})
    put_stat(conn, "partner_map", rows)
    return rows
