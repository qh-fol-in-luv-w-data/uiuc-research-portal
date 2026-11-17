from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import psycopg

from .db import put_stat
from .names import AuthorIndex, link_confidence, normalize_name

TOP_TOPICS = 15
MAX_KEYWORDS = 80
# initial-only matches ("J. Ross") are verified against topics even with one candidate;
# below this cosine the confidence is halved (so they fall under the 0.5 link threshold)
MIN_TOPIC_COS = 0.60  # calibrated 2026-11-17 on 15 manual checks: wrong 0.514, lowest correct 0.650


def needs_topic_check(method: str, ids: list[str]) -> bool:
    return len(ids) > 1 or method == "initial_last"


def find_candidates(conn: psycopg.Connection) -> dict[int, tuple[str, list[str]]]:
    idx = AuthorIndex()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT a.id, a.display_name FROM authors a"
                    " JOIN authorships s ON s.author_id = a.id WHERE s.is_uiuc ORDER BY a.id")
        for aid, name in cur.fetchall():
            idx.add(aid, name)
        cur.execute("SELECT id, name FROM faculty ORDER BY id")
        faculty = cur.fetchall()
    out: dict[int, tuple[str, list[str]]] = {}
    for fid, name in faculty:
        m = idx.match(normalize_name(name))
        if m:
            out[fid] = m
    return out


def _faculty_text(keywords: list[str]) -> str:
    return "Research interests: " + ", ".join(keywords[:MAX_KEYWORDS])


def embed_profiles(conn: psycopg.Connection, embedder) -> dict:
    ambiguous = {fid: ids for fid, (m, ids) in find_candidates(conn).items() if needs_topic_check(m, ids)}
    author_ids = sorted({a for ids in ambiguous.values() for a in ids})
    with conn.cursor() as cur:
        cur.execute("SELECT id, keywords FROM faculty WHERE id = ANY(%s) AND keyword_embedding IS NULL ORDER BY id",
                    (list(ambiguous),))
        fac_rows = cur.fetchall()
        cur.execute("SELECT author_id FROM author_profile WHERE author_id = ANY(%s)", (author_ids,))
        done = {r[0] for r in cur.fetchall()}
        todo = [a for a in author_ids if a not in done]
        cur.execute(
            "SELECT s.author_id, t.display_name, count(*) AS n FROM authorships s"
            " JOIN work_topics wt ON wt.work_id = s.work_id JOIN topics t ON t.id = wt.topic_id"
            " WHERE s.author_id = ANY(%s) GROUP BY s.author_id, t.display_name"
            " ORDER BY s.author_id, n DESC, t.display_name", (todo,))
        topics: dict[str, list[str]] = defaultdict(list)
        for aid, tname, _ in cur.fetchall():
            if len(topics[aid]) < TOP_TOPICS:
                topics[aid].append(tname)
    if fac_rows:
        vecs = embedder.embed([_faculty_text(kw) for _, kw in fac_rows])
        with conn.cursor() as cur:
            cur.executemany("UPDATE faculty SET keyword_embedding = %s WHERE id = %s",
                            [(v, fid) for (fid, _), v in zip(fac_rows, vecs)])
    if todo:
        texts = ["Research topics: " + "; ".join(topics.get(a) or ["unknown"]) for a in todo]
        vecs = embedder.embed(texts)
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO author_profile (author_id, profile_text, embedding) VALUES (%s, %s, %s)"
                            " ON CONFLICT (author_id) DO UPDATE SET profile_text = EXCLUDED.profile_text,"
                            " embedding = EXCLUDED.embedding",
                            [(a, t, v) for a, t, v in zip(todo, texts, vecs)])
    conn.commit()
    return {"faculty": len(fac_rows), "authors": len(todo)}


def _np(v) -> np.ndarray:
    return v.to_numpy() if hasattr(v, "to_numpy") else np.asarray(v, dtype=np.float32)


def _cos(a, b) -> float:
    a, b = _np(a), _np(b)
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    return float(a @ b / (na * nb)) if na and nb else 0.0


def link_faculty(conn: psycopg.Connection, min_confidence: float = 0.5) -> dict:
    cands = find_candidates(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM faculty")
        n_faculty = cur.fetchone()[0]
        cur.execute("SELECT id, keyword_embedding FROM faculty WHERE keyword_embedding IS NOT NULL")
        fac_vec = dict(cur.fetchall())
        cur.execute("SELECT author_id, embedding FROM author_profile")
        auth_vec = dict(cur.fetchall())
    links = []
    by_method: Counter[str] = Counter()
    below = 0
    for fid, (method, ids) in cands.items():
        if not needs_topic_check(method, ids):
            choice, conf = 0, link_confidence(method, [1.0])[1]
        else:
            fv = fac_vec.get(fid)
            cos = [_cos(fv, auth_vec[a]) if fv is not None and a in auth_vec else 0.0 for a in ids]
            choice, conf = link_confidence(method, cos)
            if method == "initial_last" and cos[choice] < MIN_TOPIC_COS:
                conf = round(conf * 0.5, 4)
        if conf < min_confidence:
            below += 1
            continue
        links.append((fid, ids[choice], conf, method))
        by_method[method] += 1
    with conn.cursor() as cur:
        cur.execute("DELETE FROM faculty_author_link")
        cur.executemany("INSERT INTO faculty_author_link (faculty_id, author_id, confidence, method)"
                        " VALUES (%s, %s, %s, %s)", links)
    conn.commit()
    report = {"faculty": n_faculty, "linked": len(links),
              "rate": round(len(links) / n_faculty, 4) if n_faculty else 0.0,
              "by_method": dict(by_method), "no_candidate": n_faculty - len(cands), "below_threshold": below}
    put_stat(conn, "dq_link", report)
    return report
