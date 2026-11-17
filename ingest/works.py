from __future__ import annotations

from dataclasses import dataclass, field

UIUC_ID = "I157725225"
UI_SYSTEM_ID = "I2801919071"
KEEP_TYPES = {"article", "preprint", "review", "book-chapter", "conference-paper"}
TRUNCATED_AUTHORS = 100  # OpenAlex list responses cap authorships at 100


def short_id(url: str | None) -> str | None:
    if not url:
        return None
    return url.rstrip("/").rsplit("/", 1)[-1]


def rebuild_abstract(inv: dict | None) -> str | None:
    if not inv:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            positions[i] = word
    text = " ".join(positions[i] for i in sorted(positions))
    return text or None


def _source(work: dict) -> dict:
    return ((work.get("primary_location") or {}).get("source")) or {}


def drop_reason(work: dict) -> str | None:
    if work.get("is_retracted"):
        return "retracted"
    if work.get("is_paratext"):
        return "paratext"
    if not (work.get("title") or "").strip():
        return "no_title"
    if work.get("type") in KEEP_TYPES or _source(work).get("type") == "conference":
        return None
    return f"type:{work.get('type')}"


@dataclass
class ParsedWork:
    work: dict
    authors: list[dict] = field(default_factory=list)
    authorships: list[dict] = field(default_factory=list)
    institutions: list[dict] = field(default_factory=list)
    work_institutions: list[str] = field(default_factory=list)
    topics: list[dict] = field(default_factory=list)
    work_topics: list[tuple[str, float]] = field(default_factory=list)
    # authorships OpenAlex has not attributed to an author id: no author row, but still affiliation evidence
    unattributed_uiuc: bool = False
    unattributed_raw: list[str] = field(default_factory=list)


def _topic_row(t: dict) -> dict:
    return {
        "id": short_id(t.get("id")),
        "display_name": t.get("display_name") or "",
        "subfield": (t.get("subfield") or {}).get("display_name"),
        "field": (t.get("field") or {}).get("display_name"),
        "domain": (t.get("domain") or {}).get("display_name"),
    }


def parse_work(w: dict) -> ParsedWork:
    wid = short_id(w["id"])
    src = _source(w)
    oa = w.get("open_access") or {}
    pt = w.get("primary_topic") or {}
    p = ParsedWork(work={
        "id": wid,
        "doi": w.get("doi"),
        "title": (w.get("title") or "").strip(),
        "abstract": rebuild_abstract(w.get("abstract_inverted_index")),
        "publication_date": w.get("publication_date"),
        "type": w.get("type"),
        "language": w.get("language"),
        "cited_by_count": int(w.get("cited_by_count") or 0),
        "is_oa": bool(oa.get("is_oa")),
        "oa_url": oa.get("oa_url"),
        "venue_name": src.get("display_name"),
        "venue_type": src.get("type"),
        "primary_topic_id": short_id(pt.get("id")),
        "is_outlier": False,
        "outlier_reason": None,
    })
    insts: dict[str, dict] = {}
    seen: set[str] = set()
    for a in w.get("authorships") or []:
        au = a.get("author") or {}
        aid = short_id(au.get("id"))
        if aid and aid in seen:
            continue
        inst_ids = []
        uiuc = False
        for i in a.get("institutions") or []:
            iid = short_id(i.get("id"))
            if not iid:
                continue
            inst_ids.append(iid)
            insts[iid] = {"id": iid, "display_name": i.get("display_name"),
                          "country_code": i.get("country_code"), "type": i.get("type")}
            # child institutions (institutes, centers) list UIUC in their lineage
            if iid == UIUC_ID or UIUC_ID in {short_id(x) for x in i.get("lineage") or []}:
                uiuc = True
        raw = "; ".join(a.get("raw_affiliation_strings") or []) or None
        if not aid:
            # OpenAlex has not attributed this authorship to an author id yet: no author row,
            # but its institutions and affiliation still count as evidence for the work
            p.unattributed_uiuc = p.unattributed_uiuc or uiuc
            if raw:
                p.unattributed_raw.append(raw)
            continue
        seen.add(aid)
        p.authors.append({"id": aid, "display_name": au.get("display_name") or "", "orcid": au.get("orcid")})
        p.authorships.append({
            "work_id": wid, "author_id": aid, "position": a.get("author_position"),
            "is_uiuc": uiuc, "raw_affiliation": raw,
        })
    p.institutions = list(insts.values())
    p.work_institutions = list(insts.keys())
    seen_topics: set[str] = set()
    for t in list(w.get("topics") or []) + ([pt] if pt else []):
        row = _topic_row(t)
        if not row["id"] or row["id"] in seen_topics:
            continue
        seen_topics.add(row["id"])
        p.topics.append(row)
        p.work_topics.append((row["id"], float(t.get("score") or 0.0)))
    return p


def mark_outliers(items: list[ParsedWork]) -> dict[str, int]:
    counts = {"no_uiuc_affiliation": 0, "non_english_high_citation": 0}
    cites = sorted(p.work["cited_by_count"] for p in items)
    p99 = cites[int(0.99 * (len(cites) - 1))] if cites else 0
    for p in items:
        has_uiuc = p.unattributed_uiuc or any(a["is_uiuc"] for a in p.authorships)
        raws = [a["raw_affiliation"] or "" for a in p.authorships] + p.unattributed_raw
        mentions = any("illinois" in r.lower() for r in raws)
        reason = None
        truncated = len(p.authorships) >= TRUNCATED_AUTHORS  # the UIUC author may be cut off
        if not has_uiuc and not mentions and not truncated:
            reason = "no_uiuc_affiliation"
        elif p.work["language"] not in (None, "en") and p99 > 0 and p.work["cited_by_count"] >= p99:
            reason = "non_english_high_citation"
        if reason:
            p.work["is_outlier"] = True
            p.work["outlier_reason"] = reason
            counts[reason] += 1
    return counts


def cap_by_date(items: list[ParsedWork], limit: int = 25000) -> list[ParsedWork]:
    if len(items) <= limit:
        return items
    return sorted(items, key=lambda p: p.work["publication_date"] or "", reverse=True)[:limit]
