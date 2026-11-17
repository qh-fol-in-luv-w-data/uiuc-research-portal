from __future__ import annotations

import time

import psycopg


def work_text(title: str, abstract: str | None) -> str:
    return f"{title}\n\n{abstract}" if abstract else title


def faculty_text(name: str, keywords: list[str], titles: list[str]) -> str:
    text = f"{name}. Research interests: {', '.join(keywords[:60])}."
    if titles:
        text += f" Selected papers: {'; '.join(titles)}."
    return text


def embed_works(conn: psycopg.Connection, embedder, force: bool = False, chunk: int = 256, progress=print) -> int:
    with conn.cursor() as cur:
        if force:
            cur.execute("UPDATE works SET embedding = NULL")
            conn.commit()
        cur.execute("SELECT id, title, abstract FROM works WHERE embedding IS NULL ORDER BY id")
        rows = cur.fetchall()
    started = time.time()
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        vecs = embedder.embed([work_text(t, a) for _, t, a in part])
        with conn.cursor() as cur:
            cur.executemany("UPDATE works SET embedding = %s WHERE id = %s",
                            [(v, wid) for (wid, _, _), v in zip(part, vecs)])
        conn.commit()
        done = i + len(part)
        rate = done / max(time.time() - started, 1e-6)
        progress(f"embed works: {done}/{len(rows)} ({rate:.1f}/s)")
    return len(rows)


def embed_faculty(conn: psycopg.Connection, embedder, force: bool = False) -> int:
    with conn.cursor() as cur:
        if force:
            cur.execute("UPDATE faculty SET embedding = NULL")
            conn.commit()
        cur.execute(
            "SELECT f.id, f.name, f.keywords, ARRAY("
            "  SELECT w.title FROM faculty_author_link l"
            "  JOIN authorships s ON s.author_id = l.author_id JOIN works w ON w.id = s.work_id"
            "  WHERE l.faculty_id = f.id AND NOT w.is_outlier"
            "  ORDER BY w.cited_by_count DESC, w.id LIMIT 5)"
            " FROM faculty f WHERE f.embedding IS NULL ORDER BY f.id")
        rows = cur.fetchall()
    if not rows:
        return 0
    vecs = embedder.embed([faculty_text(n, kw, titles) for _, n, kw, titles in rows])
    with conn.cursor() as cur:
        cur.executemany("UPDATE faculty SET embedding = %s WHERE id = %s",
                        [(v, fid) for (fid, _, _, _), v in zip(rows, vecs)])
    conn.commit()
    return len(rows)
