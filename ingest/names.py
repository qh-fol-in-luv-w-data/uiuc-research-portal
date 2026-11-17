from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from unidecode import unidecode

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md"}
METHODS = ("exact", "first_last", "initial_last")
METHOD_BASE = {"exact": 0.9, "first_last": 0.75, "initial_last": 0.6}


@dataclass(frozen=True)
class NameParts:
    first: str
    middles: tuple[str, ...]
    last: str


def normalize_name(name: str | None) -> NameParts | None:
    if not name:
        return None
    s = unidecode(name).lower()
    s = re.sub(r"\(.*?\)", " ", s)
    if "," in s:
        last, _, rest = s.partition(",")
        s = f"{rest} {last}"
    s = s.replace("-", "").replace("'", "")
    s = re.sub(r"[^a-z\s]", " ", s)
    tokens = [t for t in s.split() if t not in SUFFIXES]
    if len(tokens) < 2:
        return None
    return NameParts(tokens[0], tuple(tokens[1:-1]), tokens[-1])


def _keys(p: NameParts) -> dict[str, str]:
    return {
        "exact": " ".join([p.first, *p.middles, p.last]),
        "first_last": f"{p.first} {p.last}",
        "initial_last": f"{p.first[0]} {p.last}",
    }


class AuthorIndex:
    def __init__(self) -> None:
        self._index: dict[str, dict[str, list[str]]] = {m: defaultdict(list) for m in METHODS}
        self._parts: dict[str, NameParts] = {}

    def add(self, author_id: str, display_name: str) -> None:
        p = normalize_name(display_name)
        if p is None or author_id in self._parts:
            return
        self._parts[author_id] = p
        for method, key in _keys(p).items():
            self._index[method][key].append(author_id)

    def match(self, fac: NameParts | None) -> tuple[str, list[str]] | None:
        if fac is None:
            return None
        keys = _keys(fac)
        for method in METHODS:
            ids = list(self._index[method].get(keys[method], []))
            if method == "initial_last":
                # only authors recorded with an initial; a different full first name is another person
                ids = [a for a in ids if len(self._parts[a].first) == 1]
            ids = [a for a in ids if not _middle_conflict(fac, self._parts[a])]
            if ids:
                return method, sorted(ids)
        return None


def _middle_conflict(fac: NameParts, author: NameParts) -> bool:
    """'John A. Smith' and 'John B. Smith' are different people; a missing middle is not a conflict."""
    return bool(fac.middles and author.middles and fac.middles[0][0] != author.middles[0][0])


def link_confidence(method: str, cosines: list[float]) -> tuple[int, float]:
    base = METHOD_BASE[method]
    if len(cosines) == 1:
        return 0, base
    order = sorted(range(len(cosines)), key=lambda i: -cosines[i])
    margin = cosines[order[0]] - cosines[order[1]]
    return order[0], round(base * (0.6 + 0.4 * min(1.0, margin / 0.1)), 4)
