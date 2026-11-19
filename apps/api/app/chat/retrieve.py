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


def search_papers(conn: psycopg.Connection, plan: dict, qvec: np.ndarray, cvec: np.ndarray, cfg: ChatConfig,
                  limit: int | None = None) -> list[dict]:
    """Hybrid candidates fused with reciprocal rank fusion (RRF):
      - full-text: works matching EVERY concept group by text (AND of ORs),
      - meaning: nearest works to the question embedding,
      - meaning: nearest works to the concept embedding (core terms of every group).
    Then the date window, the top `limit` by fused rank, presented in the plan's order (recent/cited/relevance).
    Per-group concept vectors proved unable to separate on- from off-topic works (eval 2026-11-19), so the final
    on-topic judgement is left to the answer step, which cites only relevant sources."""
    groups = [g for g in plan["concepts"] if g]
    params: dict = {"pool": cfg.pool, "qvec": qvec, "cvec": cvec}
    tsq = []
    for i, g in enumerate(groups):
        params[f"g{i}"] = ts_or(g)
        tsq.append(f"websearch_to_tsquery('english', %(g{i})s)")
    and_query = " && ".join(tsq) if tsq else "websearch_to_tsquery('english', %(qtext)s)"
    params["qtext"] = plan["standalone_question"]
    group_cols = "".join(f", w.tsv @@ {q} AS m{i}" for i, q in enumerate(tsq))
    sql = f"""
        WITH fts AS (
          SELECT w.id, row_number() OVER (ORDER BY ts_rank(w.tsv, q) DESC, w.id) AS r
          FROM works w, (SELECT {and_query} AS q) x
          WHERE w.tsv @@ q AND {LIVE} ORDER BY ts_rank(w.tsv, q) DESC, w.id LIMIT %(pool)s),
        vq AS (
          SELECT w.id, row_number() OVER (ORDER BY w.embedding <=> %(qvec)s, w.id) AS r
          FROM works w WHERE {LIVE} AND w.embedding IS NOT NULL ORDER BY w.embedding <=> %(qvec)s, w.id LIMIT %(pool)s),
        vc AS (
          SELECT w.id, row_number() OVER (ORDER BY w.embedding <=> %(cvec)s, w.id) AS r
          FROM works w WHERE {LIVE} AND w.embedding IS NOT NULL ORDER BY w.embedding <=> %(cvec)s, w.id LIMIT %(pool)s),
        cand AS (
          SELECT id, sum(1.0 / ({cfg.k_rrf} + r)) AS rrf FROM (
            SELECT * FROM fts UNION ALL SELECT * FROM vq UNION ALL SELECT * FROM vc) u GROUP BY id)
        SELECT w.id, w.title, w.publication_date, w.type, w.venue_name, w.cited_by_count, w.doi, t.field,
               left(w.abstract, 600), c.rrf{group_cols}
        FROM cand c JOIN works w ON w.id = c.id LEFT JOIN topics t ON t.id = w.primary_topic_id
        ORDER BY c.rrf DESC, w.id"""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.rollback()  # read-only: never hold a transaction open across requests

    today = date.today()
    d_from = date.fromisoformat(plan["date_from"]) if plan.get("date_from") else None
    d_to = date.fromisoformat(plan["date_to"]) if plan.get("date_to") else None
    hits = []
    for r in rows:
        wid, title, pub, typ, venue, cited, doi, field, abstract, rrf = r[:10]
        if pub is not None and pub > today:
            continue  # future issue dates are not "published" yet
        if (d_from and (pub is None or pub < d_from)) or (d_to and (pub is None or pub > d_to)):
            continue
        hits.append({"id": wid, "title": title, "publication_date": pub, "type": typ, "venue": venue,
                     "cited_by_count": cited, "doi": doi, "field": field, "abstract": abstract, "score": float(rrf),
                     "matched_by": ["text" if m else None for m in r[10:]]})
        if len(hits) >= (limit or plan["limit"]):
            break
    key = {"recent": lambda h: (h["publication_date"] or date.min, h["score"]),
           "cited": lambda h: (h["cited_by_count"], h["score"])}.get(plan["sort"])
    if key:
        hits.sort(key=key, reverse=True)
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


# ---------------------------------------------------------------- faculty

import math  # noqa: E402
import re  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402


@dataclass
class FacultyIndex:
    """All faculty in memory (999 rows): keywords, profile embedding, linked works, keyword IDF."""
    rows: list[dict]
    emb: np.ndarray                      # (n, 1024), zero rows where missing
    works: dict[int, set[str]]           # faculty id -> work ids by their linked OpenAlex authors
    idf: dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, conn: psycopg.Connection) -> "FacultyIndex":
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, position, primary_field, photo_url, keywords, embedding FROM faculty ORDER BY id")
            raw = cur.fetchall()
            cur.execute("SELECT l.faculty_id, s.work_id FROM faculty_author_link l JOIN authorships s ON s.author_id = l.author_id")
            pairs = cur.fetchall()
        conn.rollback()
        rows, vecs = [], []
        for fid, name, pos, fld, photo, kws, e in raw:
            rows.append({"id": fid, "name": name, "position": pos, "primary_field": fld, "photo_url": photo,
                         "keywords": list(kws or [])})
            v = np.asarray(e.to_numpy() if hasattr(e, "to_numpy") else (e if e is not None else np.zeros(1024)),
                           dtype=np.float32)
            n = float(np.linalg.norm(v))
            vecs.append(v / n if n else v)
        works: dict[int, set[str]] = {}
        for fid, wid in pairs:
            works.setdefault(fid, set()).add(wid)
        df: dict[str, int] = {}
        for r in rows:
            for k in set(r["keywords"]):
                df[k] = df.get(k, 0) + 1
        n = max(len(rows), 1)
        idf = {k: math.log((n + 1) / (c + 0.5)) for k, c in df.items()}
        return cls(rows=rows, emb=np.vstack(vecs) if vecs else np.zeros((0, 1024), np.float32), works=works, idf=idf)


def _term_hits(term: str, keyword: str) -> bool:
    """Whole-word containment either way ("medical" ~ "medical imaging"); padded strings, no regex (hot loop)."""
    t, k = f" {term.lower().strip()} ", f" {keyword.lower()} "
    return len(t) > 2 and (t in k or (" " in keyword and k in t))


def _minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)


def _match_strength(term: str, keyword: str) -> float:
    """1.0 when the keyword is about the term ("computer vision", "3d computer vision"); 0.6 when the term only
    modifies another head noun ("healthcare information security" is about security, not healthcare)."""
    if not _term_hits(term, keyword):
        return 0.0
    k, t = keyword.lower().strip(), term.lower().strip()
    return 1.0 if k == t or k.endswith(" " + t) or " " not in k else 0.6


def search_faculty(idx: FacultyIndex, plan: dict, qvec: np.ndarray, related: list[dict], cfg: ChatConfig,
                   limit: int | None = None, cvec: np.ndarray | None = None) -> list[dict]:
    """Rank faculty for a question's concept groups.

    Evidence strength per group: the core term (listed first by the plan) counts fully, a synonym counts up to half,
    scaled by how specific (IDF) the matched keyword is, so a generic "machine learning" barely counts toward
    "computer vision". Faculty are ranked by evidence strength across all groups (rounded to half steps), then by
    w_keywords * IDF evidence + w_vector * profile similarity to the concept vector + w_papers * related papers.
    Eval (2026-11-19, reference set for "computer vision in healthcare"): P@6 5/6 vs 3/6 for count-based coverage."""
    groups = [g for g in plan["concepts"] if g]
    if not idx.rows:
        return []
    related_ids = {p["id"]: p["title"] for p in related}
    n = len(idx.rows)
    kw_score, strength, covered = np.zeros(n, np.float32), np.zeros(n, np.float32), np.zeros(n, np.int32)
    matched: list[list[str]] = []
    papers: list[list[str]] = []
    for i, r in enumerate(idx.rows):
        hits_kw: list[str] = []
        total = 0.0
        for g in groups:
            best = best_strength = 0.0
            best_k = None
            for k in r["keywords"]:
                core = _match_strength(g[0], k)
                syn = 0.5 if any(_term_hits(t, k) for t in g[1:]) else 0.0
                w_match = max(core, syn)
                if not w_match:
                    continue
                idf = idx.idf.get(k, 0.0)
                if idf * w_match > best:
                    best, best_k = idf * w_match, k
                best_strength = max(best_strength, core if core >= syn else syn * min(1.0, idf / 3.0))
            if best_k:
                hits_kw.append(best_k)
                hits_kw += [k for k in r["keywords"] if k not in hits_kw and _term_hits(g[0], k)][:2]
                covered[i] += 1
            total += best
            strength[i] += best_strength
        kw_score[i] = total / max(len(groups), 1)
        matched.append(hits_kw)
        papers.append([related_ids[w] for w in idx.works.get(r["id"], set()) if w in related_ids])
    v = cvec if cvec is not None else qvec
    v = v / (float(np.linalg.norm(v)) or 1.0)
    vec_score = idx.emb @ v
    n_papers = np.array([len(p) for p in papers], np.float32)
    total = (cfg.w_keywords * _minmax(kw_score) + cfg.w_vector * _minmax(vec_score)
             + cfg.w_papers * (n_papers / n_papers.max() if n_papers.max() > 0 else n_papers))
    tier = np.round(strength * 2) / 2
    order = sorted(range(n), key=lambda i: (-float(tier[i]), -float(total[i])))
    out = []
    for i in order:
        if covered[i] == 0 and n_papers[i] == 0:
            continue  # no evidence for any concept: similarity alone is not enough to name someone an expert
        r = idx.rows[i]
        out.append({**r, "score": float(total[i]), "groups_covered": int(covered[i]), "strength": float(strength[i]),
                    "matched_keywords": matched[i][:6], "related_papers": sorted(papers[i])[:2]})
        if len(out) >= (limit or plan["limit"]):
            break
    return out
