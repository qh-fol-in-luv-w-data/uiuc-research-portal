"""Numbered sources for the answer model, the answer prompt, and the citation check."""
from __future__ import annotations

import re
from datetime import date

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TYPE_LABEL = {"article": "Article", "preprint": "Preprint", "conference-paper": "Conference paper",
              "book-chapter": "Book chapter", "review": "Review"}

SYSTEM = (
    "You are the research assistant of a University of Illinois Urbana-Champaign (UIUC) research portal. "
    "Every numbered source is a UIUC publication from the last two years or a UIUC faculty member, retrieved by search, "
    "so some may be off-topic. Answer using ONLY these sources. "
    "Mention the sources that are about the question's topic, with a few words on what each contributes, "
    "and cite each one as [n] with its number. List papers newest first when the question asks for recent work, "
    "most cited first when it asks for top or most cited work, otherwise most relevant first. "
    "Ignore off-topic sources. If no source is squarely on the topic, say so plainly and name the closest ones and how "
    "they relate. Never invent papers, people or facts. Answer in the language of the question, in 3 to 5 sentences."
)
OUT_OF_SCOPE = ("I can only help with research at the University of Illinois Urbana-Champaign (UIUC): recent publications, "
                "notable papers and faculty expertise. Try asking about a research topic.")


def month(d: date | None) -> str:
    return f"{MONTHS[d.month - 1]} {d.year}" if d else "undated"


def no_results(plan: dict) -> str:
    topic = " and ".join(g[0] for g in plan["concepts"] if g) or "this topic"
    return (f"I couldn't find UIUC publications or faculty from the last two years about {topic}. "
            "Try a broader or differently worded question.")


def build_sources(papers: list[dict], faculty: list[dict], abstract_chars: int = 200) -> tuple[list[dict], str]:
    """Returns (sources for the UI, numbered source text for the prompt). Papers first, then faculty."""
    ui, lines = [], []
    for p in papers:
        n = len(ui) + 1
        kind = TYPE_LABEL.get(p["type"] or "", (p["type"] or "work").replace("-", " ").capitalize())
        venue = (p["venue"] or "").split(" (")[0]
        meta = " · ".join(x for x in (kind, month(p["publication_date"]), venue) if x)
        url = p["doi"] or f"https://openalex.org/{p['id']}"
        ui.append({"n": n, "kind": "work", "id": p["id"], "title": p["title"], "meta": meta, "url": url})
        authors = ", ".join(p.get("uiuc_authors", [])[:4]) or "not listed"
        abstract = re.sub(r"\s+", " ", (p.get("abstract") or "")).strip()[:abstract_chars]
        lines.append(f"[{n}] {p['title']} ({kind}, {month(p['publication_date'])}{', ' + venue if venue else ''}; "
                     f"{p['cited_by_count']} citations). UIUC authors: {authors}. {abstract}")
    for f in faculty:
        n = len(ui) + 1
        expertise = ", ".join(f["matched_keywords"][:5]) or "related research"
        meta = " · ".join(x for x in (f.get("position"), f.get("primary_field"), f"matched: {expertise}") if x)
        ui.append({"n": n, "kind": "faculty", "id": str(f["id"]), "title": f["name"], "meta": meta, "url": None})
        papers_txt = "; ".join(f["related_papers"]) or "none in the retrieved set"
        lines.append(f"[{n}] {f['name']}, {f.get('position') or 'faculty'}"
                     f"{', ' + f['primary_field'] if f.get('primary_field') else ''}. "
                     f"Expertise matching the question: {expertise}. Related UIUC papers: {papers_txt}.")
    return ui, "\n".join(lines)


def build_messages(question: str, history: list[dict] | None, sources_text: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM}]
    for turn in (history or [])[-4:]:
        msgs.append({"role": turn["role"], "content": turn["content"]})
    msgs.append({"role": "user", "content": f"Sources:\n{sources_text}\n\nQuestion: {question}"})
    return msgs


_CITE = re.compile(r"\s*\[(\d+|n)\]")


def clean_citations(text: str, n_sources: int) -> str:
    """Drop citations that point to no source (and a literal "[n]"), keeping valid ones."""
    def keep(m: re.Match) -> str:
        v = m.group(1)
        return m.group(0) if v.isdigit() and 1 <= int(v) <= n_sources else ""
    return re.sub(r" {2,}", " ", _CITE.sub(keep, text)).strip()
