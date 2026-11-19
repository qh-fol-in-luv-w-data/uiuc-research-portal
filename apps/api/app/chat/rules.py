"""Rule-based search plan: the fallback when the language model is slow, missing or returns nothing usable."""
from __future__ import annotations

import re

from . import qu

SYNONYMS: dict[str, list[str]] = {
    "ai": ["artificial intelligence", "machine learning", "deep learning"],
    "artificial intelligence": ["ai", "machine learning"],
    "machine learning": ["deep learning", "artificial intelligence"],
    "war": ["armed conflict", "military", "warfare", "defense"],
    "war conflict": ["war", "armed conflict", "military", "warfare"],
    "conflict": ["armed conflict", "war", "military"],
    "healthcare": ["health care", "medical", "clinical", "medicine", "health"],
    "health": ["healthcare", "medical", "clinical"],
    "computer vision": ["image analysis", "image recognition", "visual recognition"],
    "climate change": ["global warming", "climate"],
    "llm": ["large language models", "language models"],
}
FACULTY = re.compile(r"\b(faculty|professors?|researchers?|experts?|people|scientists?|who)\b")
PAPERS = re.compile(r"\b(papers?|publications?|articles?|works?|studies|research)\b")
LEAD = re.compile(
    r"^.*?\b(?:on|about|regarding|related to|in the area of|in the field of|work(?:s|ing)? on|research(?:es|ing)? on|studying)\s+",
)
# eval 2026-11-19: the planner refused explicit topic requests ("Papers on underwater basket weaving") and broad ones
TOPIC_REQUEST = re.compile(r"\b(papers?|publications?|articles?|research|studies|work|faculty|professors?|experts?|who)\b"
                           r".*\b(on|about|regarding|related to|in the (?:area|field) of)\s+\w")
BROAD = re.compile(r"\b(research|stud(?:y|ies)|publish\w*|faculty|professors?|uiuc|illinois)\b|nghiên cứu", re.I)
_VI = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)
_VI_WHO = re.compile(r"^\s*ai\b|giảng viên|giáo sư|nhà (?:khoa học|nghiên cứu)|chuyên gia", re.I)


def vietnamese_who(question: str) -> bool:
    """Vietnamese "Ai ..." means "who ...", not AI; the planner reads it as AI and returns papers."""
    return bool(_VI.search(question) and _VI_WHO.search(question))


FILLER = re.compile(r"\b(uiuc|illinois|university of illinois|the|recent|latest|newest|most cited|papers?|publications?)\b")


def _terms(phrase: str) -> list[list[str]]:
    groups = []
    for part in re.split(r"\s+(?:in|and|for|of|with)\s+|,", phrase):
        core = re.sub(r"\s+", " ", FILLER.sub(" ", part)).strip(" ?.!")
        if len(core) >= 2:
            groups.append([core] + [s for s in SYNONYMS.get(core, []) if s != core])
    return groups


def parse(question: str, today: str) -> dict:
    q = question.lower().strip()
    wants_faculty, wants_papers = bool(FACULTY.search(q)), bool(PAPERS.search(q))
    intent = "both" if wants_faculty and wants_papers and "work on" not in q else "faculty" if wants_faculty else "papers"
    sort = ("recent" if re.search(r"\b(recent|latest|newest|new)\b", q)
            else "cited" if re.search(r"\b(most cited|highly cited|influential|top|best known|well known|landmark|seminal|"
                                       r"most important|key papers)\b", q) else "relevance")
    limit_m = re.search(r"\b(?:top|first)\s+(\d{1,2})\b|\b(\d{1,2})\s+(?:papers|publications|faculty|people)\b", q)
    limit = min(20, max(1, int(next(g for g in limit_m.groups() if g)))) if limit_m else 5
    date_from = date_to = None
    if m := re.search(r"\b(?:since|from|after)\s+(20\d\d)\b", q):
        date_from = f"{m.group(1)}-01-01"
    elif m := re.search(r"\bin\s+(20\d\d)\b", q):
        date_from, date_to = f"{m.group(1)}-01-01", f"{m.group(1)}-12-31"
    body = re.sub(r"\b(?:since|from|after|in)\s+20\d\d\b", " ", q)
    m = LEAD.match(body)
    phrase = body[m.end():] if m else body
    phrase = re.sub(r"^(?:top\s+\d+\s+|\d+\s+)", "", phrase)
    concepts = _terms(phrase) or _terms(body)
    return {"intent": intent, "standalone_question": question.strip(), "concepts": concepts,
            "date_from": date_from, "date_to": date_to, "sort": sort, "limit": limit}


assert not qu.schema_errors(parse("papers on soil", "2026-01-01"))
