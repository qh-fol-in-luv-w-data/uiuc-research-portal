"""Deterministic retrieval for the assistant: no LLM calls, every parameter in ChatConfig."""
from __future__ import annotations

from datetime import date

import numpy as np
import psycopg

from .config import ChatConfig

LIVE = "NOT w.is_outlier AND w.duplicate_of IS NULL"


def ts_or(terms: list[str]) -> str:
    """websearch_to_tsquery text matching any of the terms (multi-word terms as phrases)."""
    return " OR ".join(f'"{t}"' if " " in t else t for t in (t.strip().replace('"', "") for t in terms) if t)


def search_papers(conn: psycopg.Connection, plan: dict, qvec: np.ndarray, group_vecs: list[np.ndarray],
                  cfg: ChatConfig, limit: int | None = None) -> list[dict]:
    """Hybrid search: full-text ∪ vector candidates, RRF fusion, every concept group must match
    (by text, or by meaning: cosine(work, group) >= tau), date window, then the plan's sort."""
    groups = [g for g in plan["concepts"] if g]
    all_terms = [t for g in groups for t in g]
    params: dict = {"pool": cfg.pool, "qvec": qvec, "all": ts_or(all_terms) or plan["standalone_question"]}
    group_cols = []
    for i, (g, v) in enumerate(zip(groups, group_vecs)):
        params[f"g{i}"], params[f"v{i}"] = ts_or(g), v
        group_cols.append(f"(w.tsv @@ websearch_to_tsquery('english', %(g{i})s)) AS m{i},"
                          f" 1 - (w.embedding <=> %(v{i})s) AS s{i}")
    sql = f"""
        WITH fts AS (
          SELECT w.id, row_number() OVER (ORDER BY ts_rank(w.tsv, q) DESC, w.id) AS r
          FROM works w, websearch_to_tsquery('english', %(all)s) q
          WHERE w.tsv @@ q AND {LIVE}
          ORDER BY ts_rank(w.tsv, q) DESC, w.id LIMIT %(pool)s),
        vec AS (
          SELECT w.id, row_number() OVER (ORDER BY w.embedding <=> %(qvec)s, w.id) AS r
          FROM works w WHERE {LIVE} AND w.embedding IS NOT NULL
          ORDER BY w.embedding <=> %(qvec)s, w.id LIMIT %(pool)s),
        cand AS (
          SELECT id, min(fr) AS fr, min(vr) AS vr FROM (
            SELECT id, r AS fr, NULL::bigint AS vr FROM fts UNION ALL SELECT id, NULL, r FROM vec) u
          GROUP BY id)
        SELECT w.id, w.title, w.publication_date, w.type, w.venue_name, w.cited_by_count, w.doi, t.field,
               left(w.abstract, 600), c.fr, c.vr{"," if group_cols else ""} {", ".join(group_cols)}
        FROM cand c JOIN works w ON w.id = c.id LEFT JOIN topics t ON t.id = w.primary_topic_id"""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.rollback()  # read-only: never hold a transaction open across requests

    today = date.today()
    d_from = date.fromisoformat(plan["date_from"]) if plan.get("date_from") else None
    d_to = date.fromisoformat(plan["date_to"]) if plan.get("date_to") else None
    hits = []
    for r in rows:
        wid, title, pub, typ, venue, cited, doi, field, abstract, fr, vr = r[:11]
        matched_by = []
        for i in range(len(groups)):
            m, s = r[11 + 2 * i], r[12 + 2 * i]
            matched_by.append("text" if m else "meaning" if s is not None and s >= cfg.tau else None)
        if None in matched_by:
            continue
        if pub is not None and pub > today:
            continue  # future issue dates are not "published" yet
        if (d_from and (pub is None or pub < d_from)) or (d_to and (pub is None or pub > d_to)):
            continue
        rrf = (1 / (cfg.k_rrf + fr) if fr else 0.0) + (1 / (cfg.k_rrf + vr) if vr else 0.0)
        hits.append({"id": wid, "title": title, "publication_date": pub, "type": typ, "venue": venue,
                     "cited_by_count": cited, "doi": doi, "field": field, "abstract": abstract,
                     "score": rrf, "matched_by": matched_by})
    key = {"recent": lambda h: (h["publication_date"] or date.min, h["score"]),
           "cited": lambda h: (h["cited_by_count"], h["score"])}.get(plan["sort"], lambda h: (h["score"],))
    hits.sort(key=key, reverse=True)
    hits = hits[: (limit or plan["limit"])]
    _attach_authors(conn, hits)
    return hits


def _attach_authors(conn: psycopg.Connection, hits: list[dict]) -> None:
    if not hits:
        return
    with conn.cursor() as cur:
        cur.execute("""SELECT s.work_id, a.display_name FROM authorships s JOIN authors a ON a.id = s.author_id
                       WHERE s.work_id = ANY(%s) AND s.is_uiuc
                       ORDER BY s.work_id, CASE s.position WHEN 'first' THEN 0 WHEN 'middle' THEN 1 ELSE 2 END, a.id""",
                    ([h["id"] for h in hits],))
        rows = cur.fetchall()
    conn.rollback()
    by_work: dict[str, list[str]] = {}
    for wid, name in rows:
        by_work.setdefault(wid, []).append(name)
    for h in hits:
        h["uiuc_authors"] = by_work.get(h["id"], [])
