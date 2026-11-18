from __future__ import annotations

import re
from collections import defaultdict

from unidecode import unidecode

from .works import ParsedWork

# lower rank = preferred canonical version
TYPE_RANK = {"article": 0, "review": 0, "conference-paper": 1, "book-chapter": 1, "preprint": 3}


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", unidecode(title).lower())).strip()


def mark_duplicates(items: list[ParsedWork]) -> int:
    """Collapse versions of one paper (e.g. arXiv preprint + journal article).

    Same normalized title AND at least one shared author id: keep the published, cited version.
    """
    groups: dict[str, list[ParsedWork]] = defaultdict(list)
    for p in items:
        key = normalize_title(p.work["title"])
        if len(key) >= 15:
            groups[key].append(p)
    marked = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda p: (TYPE_RANK.get(p.work["type"], 2), p.work["venue_name"] is None,
                                               -p.work["cited_by_count"], p.work["id"]))
        # cluster by shared authors first: one title can belong to unrelated works
        clusters: list[tuple[set[str], list[ParsedWork]]] = []
        for p in ordered:
            authors = {a["author_id"] for a in p.authorships}
            for cluster_authors, members in clusters:
                if cluster_authors & authors:
                    cluster_authors |= authors
                    members.append(p)
                    break
            else:
                clusters.append((set(authors), [p]))
        for _, members in clusters:
            for p in members[1:]:  # members[0] is the preferred version
                p.work["duplicate_of"] = members[0].work["id"]
                marked += 1
    return marked
