from __future__ import annotations

import hashlib
import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterator

import httpx

from .works import UIUC_ID

BASE_URL = "https://api.openalex.org"
WORK_FIELDS = [
    "id", "doi", "title", "publication_date", "type", "language", "cited_by_count", "open_access",
    "primary_location", "primary_topic", "topics", "authorships", "is_retracted", "is_paratext",
    "abstract_inverted_index",
]


PAGE_LIMIT = 10000  # OpenAlex basic paging (page=) cannot go past 10,000 results per query


class QuotaExhausted(RuntimeError):
    pass


class SliceTooLarge(RuntimeError):
    pass


def _years_shift(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year + years, day=28)


def works_filter(today: date) -> str:
    return f"institutions.id:{UIUC_ID},from_publication_date:{_years_shift(today, -2).isoformat()}"


def month_slices(base_filter: str) -> list[str]:
    """Split a 2-year `from_publication_date` window into calendar-month filters.

    Cursor paging needs an API key, and page-number paging stops at 10,000 results, so each
    month (~1,100 UIUC works) is paged separately. The last slice is open-ended so that
    future-dated publications are still included.
    """
    prefix, _, start = base_filter.rpartition("from_publication_date:")
    cur = date.fromisoformat(start)
    end = _years_shift(cur, 2)
    slices = []
    while True:
        nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        if nxt > end:
            slices.append(f"{prefix}from_publication_date:{cur.isoformat()}")
            return slices
        slices.append(f"{prefix}from_publication_date:{cur.isoformat()},"
                      f"to_publication_date:{(nxt - timedelta(days=1)).isoformat()}")
        cur = nxt


def resolve_filter(cache_dir: Path, today: date, refresh: bool = False) -> str:
    path = cache_dir / "works" / "filter.txt"
    if path.exists() and not refresh:
        return path.read_text().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    value = works_filter(today)
    path.write_text(value)
    return value


def page_dir_for(cache_dir: Path, filter_str: str) -> Path:
    return cache_dir / "works" / hashlib.sha1(filter_str.encode()).hexdigest()[:12]


def _cached_pages(page_dir: Path) -> list[Path]:
    return sorted(page_dir.glob("page-*.json"))


def read_cached_results(page_dir: Path) -> Iterator[dict]:
    for path in _cached_pages(page_dir):
        yield from json.loads(path.read_text())["results"]


class OpenAlexClient:
    def __init__(self, http: httpx.Client, cache_dir: Path, api_key: str | None = None,
                 mailto: str | None = None, min_remaining_usd: float = 0.005, max_retries: int = 5,
                 sleep: Callable[[float], None] = time.sleep):
        self.http = http
        self.cache_dir = cache_dir
        self.api_key = api_key
        self.mailto = mailto
        self.min_remaining_usd = min_remaining_usd
        self.max_retries = max_retries
        self.sleep = sleep

    def _get(self, params: dict) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.http.get(f"{BASE_URL}/works", params=params, timeout=60)
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
                self.sleep(2 ** attempt)
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("retry-after")
                wait = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else 2 ** attempt
                if resp.status_code == 429 and wait > 120:
                    raise QuotaExhausted(
                        f"OpenAlex daily budget exhausted (retry after {int(wait)}s). "
                        "Re-run later or set OPENALEX_API_KEY; progress is cached.")
                if attempt == self.max_retries:
                    resp.raise_for_status()
                self.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError("unreachable")

    def iter_pages(self, filter_str: str, per_page: int = 200) -> Iterator[list[dict]]:
        """Yield result pages for one filter using page-number paging, cached on disk."""
        page_dir = page_dir_for(self.cache_dir, filter_str)
        page_dir.mkdir(parents=True, exist_ok=True)
        next_page: int | None = 1
        for path in _cached_pages(page_dir):
            cached = json.loads(path.read_text())
            yield cached["results"]
            next_page = cached["next_page"]
        while next_page is not None:
            params = {"filter": filter_str, "per_page": per_page, "page": next_page,
                      "select": ",".join(WORK_FIELDS)}
            if self.api_key:
                params["api_key"] = self.api_key
            if self.mailto:
                params["mailto"] = self.mailto
            resp = self._get(params)
            body = resp.json()
            results = body.get("results") or []
            count = int((body.get("meta") or {}).get("count") or 0)
            if count > PAGE_LIMIT:
                raise SliceTooLarge(f"{count} results for {filter_str!r}; split the date range further")
            nxt = next_page + 1 if results and next_page * per_page < count else None
            tmp = page_dir / f"page-{next_page:05d}.json.tmp"
            tmp.write_text(json.dumps({"page": next_page, "next_page": nxt, "count": count, "results": results}))
            tmp.rename(page_dir / f"page-{next_page:05d}.json")
            yield results
            next_page = nxt
            remaining = resp.headers.get("x-ratelimit-remaining-usd")
            if next_page is not None and remaining is not None and float(remaining) < self.min_remaining_usd:
                raise QuotaExhausted(
                    f"OpenAlex budget nearly exhausted (remaining ${remaining}). "
                    f"Re-run later or set OPENALEX_API_KEY; progress cached in {page_dir}.")
