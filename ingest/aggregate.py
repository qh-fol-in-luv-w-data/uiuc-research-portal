from __future__ import annotations

from pathlib import Path

import psycopg

from .db import get_stat, put_stat
from .works import UI_SYSTEM_ID, UIUC_ID

EXCLUDED = [UIUC_ID, UI_SYSTEM_ID]


def _rows(conn, sql: str, params=()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def compute_stats(conn: psycopg.Connection, rising_min: int = 40) -> dict[str, object]:
    works, citations, oa_share = _rows(conn, "SELECT count(*), coalesce(sum(cited_by_count), 0),"
                                             " coalesce(avg(is_oa::int), 0) FROM works WHERE NOT is_outlier AND duplicate_of IS NULL")[0]
    outliers = _rows(conn, "SELECT count(*) FROM works WHERE is_outlier")[0][0]
    duplicates = _rows(conn, "SELECT count(*) FROM works WHERE duplicate_of IS NOT NULL")[0][0]
    faculty = _rows(conn, "SELECT count(*) FROM faculty")[0][0]
    linked = _rows(conn, "SELECT count(DISTINCT faculty_id) FROM faculty_author_link")[0][0]
    partners = _rows(conn, "SELECT count(DISTINCT wi.institution_id) FROM work_institutions wi"
                           " JOIN works w ON w.id = wi.work_id"
                           " JOIN institutions i ON i.id = wi.institution_id"
                           " WHERE NOT w.is_outlier AND w.duplicate_of IS NULL AND NOT i.is_uiuc_unit"
                           " AND NOT (wi.institution_id = ANY(%s))", (EXCLUDED,))[0][0]
    monthly = _rows(conn, "SELECT to_char(date_trunc('month', publication_date), 'YYYY-MM'), count(*)"
                          " FROM works WHERE NOT is_outlier AND duplicate_of IS NULL AND publication_date IS NOT NULL"
                          " GROUP BY 1 ORDER BY 1")
    types = _rows(conn, "SELECT CASE WHEN venue_type = 'conference' AND type NOT IN"
                        " ('article','preprint','review','book-chapter') THEN 'conference-paper' ELSE type END,"
                        " count(*) FROM works WHERE NOT is_outlier AND duplicate_of IS NULL GROUP BY 1 ORDER BY 2 DESC, 1")
    field_rows = _rows(conn, "SELECT coalesce(t.field, 'Unknown'), coalesce(t.subfield, 'Unknown'), count(*)"
                             " FROM works w JOIN topics t ON t.id = w.primary_topic_id WHERE NOT w.is_outlier AND w.duplicate_of IS NULL"
                             " GROUP BY 1, 2 ORDER BY 1, 3 DESC, 2")
    fields: dict[str, dict] = {}
    for f, sub, n in field_rows:
        entry = fields.setdefault(f, {"field": f, "count": 0, "subfields": []})
        entry["count"] += n
        entry["subfields"].append({"name": sub, "count": n})
    rising = _rows(conn, """
        WITH b AS (SELECT LEAST(max(publication_date), current_date) AS maxd FROM works WHERE NOT is_outlier AND duplicate_of IS NULL),
        c AS (
          SELECT t.id, t.display_name, t.field,
            count(*) FILTER (WHERE w.publication_date > b.maxd - interval '12 months') AS recent,
            count(*) FILTER (WHERE w.publication_date <= b.maxd - interval '12 months'
                             AND w.publication_date > b.maxd - interval '24 months') AS prior
          FROM works w JOIN topics t ON t.id = w.primary_topic_id CROSS JOIN b
          WHERE NOT w.is_outlier AND w.duplicate_of IS NULL GROUP BY t.id, t.display_name, t.field)
        SELECT id, display_name, field, recent, prior, round((recent + 1)::numeric / (prior + 1), 2)
        FROM c WHERE recent >= %s ORDER BY 6 DESC, recent DESC, id LIMIT 15""", (rising_min,))
    venues = _rows(conn, "SELECT venue_name, count(*) FROM works WHERE NOT is_outlier AND duplicate_of IS NULL AND venue_name IS NOT NULL"
                         " GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 15")
    top_partners = _rows(conn, "SELECT i.id, i.display_name, i.country_code, count(DISTINCT wi.work_id)"
                               " FROM work_institutions wi JOIN institutions i ON i.id = wi.institution_id"
                               " JOIN works w ON w.id = wi.work_id"
                               " WHERE NOT w.is_outlier AND w.duplicate_of IS NULL AND NOT i.is_uiuc_unit AND NOT (i.id = ANY(%s))"
                               " GROUP BY 1, 2, 3 ORDER BY 4 DESC, 2 LIMIT 20", (EXCLUDED,))
    top_fac = _rows(conn, "SELECT f.id, f.name, count(DISTINCT s.work_id) FROM faculty f"
                          " JOIN faculty_author_link l ON l.faculty_id = f.id"
                          " JOIN authorships s ON s.author_id = l.author_id JOIN works w ON w.id = s.work_id"
                          " WHERE NOT w.is_outlier AND w.duplicate_of IS NULL GROUP BY 1, 2 ORDER BY 3 DESC, 2 LIMIT 15")
    return {
        "overview": {"works": works, "citations": int(citations), "oa_share": round(float(oa_share), 4),
                     "faculty": faculty, "faculty_linked": linked, "partner_institutions": partners,
                     "outliers": outliers, "duplicates": duplicates},
        "monthly": [{"month": m, "count": n} for m, n in monthly],
        "types": [{"type": t, "count": n} for t, n in types],
        "fields": sorted(fields.values(), key=lambda e: (-e["count"], e["field"])),
        "rising_topics": [{"id": i, "name": n, "field": f, "recent": r, "prior": p, "growth": float(g)}
                          for i, n, f, r, p, g in rising],
        "top_venues": [{"name": v, "count": n} for v, n in venues],
        "top_partners": [{"id": i, "name": n, "country": c, "count": k} for i, n, c, k in top_partners],
        "top_faculty": [{"id": i, "name": n, "count": k} for i, n, k in top_fac],
    }


def _update_derived(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE faculty f SET primary_field = x.field FROM (
              SELECT DISTINCT ON (l.faculty_id) l.faculty_id, t.field
              FROM faculty_author_link l JOIN authorships s ON s.author_id = l.author_id
              JOIN works w ON w.id = s.work_id JOIN topics t ON t.id = w.primary_topic_id
              WHERE NOT w.is_outlier AND w.duplicate_of IS NULL AND t.field IS NOT NULL
              GROUP BY l.faculty_id, t.field ORDER BY l.faculty_id, count(*) DESC, t.field) x
            WHERE f.id = x.faculty_id""")
        cur.execute("UPDATE authors a SET works_count_in_set = x.n FROM ("
                    " SELECT author_id, count(*) AS n FROM authorships GROUP BY author_id) x"
                    " WHERE a.id = x.author_id")
    conn.commit()


def render_data_quality(dq_works: dict | None, dq_faculty: dict | None, dq_link: dict | None,
                        overview: dict) -> str:
    w, f, l = dq_works or {}, dq_faculty or {}, dq_link or {}
    lines = ["# Data quality report", "", "Generated by `python -m ingest aggregate`.", "", "## Works", "",
             f"- Fetched from OpenAlex: {w.get('fetched', 'n/a')} (duplicates: {w.get('duplicates', 'n/a')})",
             f"- Kept after cleaning: {w.get('kept', 'n/a')} (capped: {w.get('capped', 0)})",
             "- Dropped by reason:"]
    lines += [f"  - `{k}`: {v}" for k, v in sorted((w.get("dropped") or {}).items())] or ["  - none"]
    lines += ["- Flagged as outliers (kept, excluded from notable stats):"]
    lines += [f"  - `{k}`: {v}" for k, v in sorted((w.get("outliers") or {}).items())]
    lines += ["", "## Faculty", "",
              f"- Rows: {f.get('rows', 'n/a')}; missing photo: {f.get('missing_photo', 'n/a')};"
              f" missing position: {f.get('missing_position', 'n/a')}",
              f"- Duplicate emails in CSV (first row kept): {len(f.get('duplicate_emails') or [])}",
              f"- Median keywords per person: raw {f.get('keywords_raw_median', 'n/a')} →"
              f" cleaned {f.get('keywords_clean_median', 'n/a')}",
              "", "## Faculty ↔ OpenAlex author links", "",
              f"- Link rate: {100 * l.get('rate', 0):.1f}% ({l.get('linked', 0)} of {l.get('faculty', 0)})",
              f"- By method: {', '.join(f'{k} {v}' for k, v in sorted((l.get('by_method') or {}).items())) or 'n/a'}",
              f"- No candidate: {l.get('no_candidate', 'n/a')}; below confidence 0.5: {l.get('below_threshold', 'n/a')}",
              "", "## Portal totals (outliers excluded)", "",
              f"- Works: {overview['works']}; citations: {overview['citations']};"
              f" open access: {100 * overview['oa_share']:.1f}%",
              f"- Partner institutions: {overview['partner_institutions']}", ""]
    return "\n".join(lines)


def aggregate(conn: psycopg.Connection, docs_dir: Path) -> dict:
    _update_derived(conn)
    stats = compute_stats(conn)
    for key, payload in stats.items():
        put_stat(conn, key, payload)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "data-quality.md").write_text(
        render_data_quality(get_stat(conn, "dq_works"), get_stat(conn, "dq_faculty"),
                            get_stat(conn, "dq_link"), stats["overview"]), encoding="utf-8")
    return stats
