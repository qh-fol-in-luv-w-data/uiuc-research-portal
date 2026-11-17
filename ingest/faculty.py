from __future__ import annotations

import csv
import re
import statistics
from pathlib import Path

import psycopg

from .db import put_stat

ORG_MARKERS = ("university", "universität", "conference", "symposium", "proceedings", "journal of",
               "institute of", "workshop on")


def parse_pg_array(s: str | None) -> list[str]:
    if s is None:
        return []
    s = s.strip()
    if s in ("", "NULL", "{}"):
        return []
    if not (s.startswith("{") and s.endswith("}")):
        raise ValueError(f"not a postgres array literal: {s[:40]!r}")
    row = next(csv.reader([s[1:-1]], delimiter=",", quotechar='"', escapechar="\\", doublequote=False))
    return [x for x in row if x and x != "NULL"]


def normalize_keyword(k: str) -> str:
    return re.sub(r"\s+", " ", k.lower()).strip(" .,;:-")


def clean_keywords(raw: list[str], stoplist: set[str], org_names: set[str], generic: set[str],
                   large_threshold: int = 200) -> list[str]:
    large = len(raw) > large_threshold
    out: list[str] = []
    seen: set[str] = set()
    for k in raw:
        n = normalize_keyword(k)
        if len(n) < 2 or n in seen:
            continue
        seen.add(n)
        if n in stoplist or n in org_names or any(m in n for m in ORG_MARKERS):
            continue
        if large and n in generic:
            continue
        out.append(n)
    return out


def load_word_list(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {normalize_keyword(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")}


def _nullable(v: str | None) -> str | None:
    v = (v or "").strip()
    return None if v in ("", "NULL") else v


def load_faculty(conn: psycopg.Connection, csv_path: Path, data_dir: Path) -> dict:
    stoplist = load_word_list(data_dir / "keyword_stoplist.txt")
    generic = load_word_list(data_dir / "keyword_generic.txt")
    with conn.cursor() as cur:
        cur.execute("SELECT lower(display_name) FROM institutions WHERE display_name IS NOT NULL")
        org_names = {r[0] for r in cur.fetchall()}
    csv.field_size_limit(10 ** 8)
    rows = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            raw = parse_pg_array(r.get("keywords"))
            clean = clean_keywords(raw, stoplist, org_names, generic)
            rows.append({
                "email": r["email"].strip().lower(), "name": r["name"].strip(),
                "photo_url": _nullable(r.get("photo_url")), "position": _nullable(r.get("position")),
                "keywords_raw": raw, "keywords": clean, "keywords_text": ", ".join(clean),
            })
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO faculty (email, name, photo_url, position, keywords_raw, keywords, keywords_text)"
            " VALUES (%(email)s, %(name)s, %(photo_url)s, %(position)s, %(keywords_raw)s, %(keywords)s,"
            " %(keywords_text)s)"
            " ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, photo_url = EXCLUDED.photo_url,"
            " position = EXCLUDED.position, keywords_raw = EXCLUDED.keywords_raw,"
            " keywords = EXCLUDED.keywords, keywords_text = EXCLUDED.keywords_text",
            rows)
    conn.commit()
    report = {
        "rows": len(rows),
        "missing_photo": sum(1 for r in rows if r["photo_url"] is None),
        "missing_position": sum(1 for r in rows if r["position"] is None),
        "keywords_raw_median": statistics.median([len(r["keywords_raw"]) for r in rows]) if rows else 0,
        "keywords_clean_median": statistics.median([len(r["keywords"]) for r in rows]) if rows else 0,
    }
    put_stat(conn, "dq_faculty", report)
    return report
