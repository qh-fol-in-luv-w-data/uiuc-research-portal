from __future__ import annotations

import hashlib
import json
import time
from datetime import date
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


class QuotaExhausted(RuntimeError):
    pass


def works_filter(today: date) -> str:
    try:
        start = today.replace(year=today.year - 2)
    except ValueError:  # Feb 29
        start = today.replace(year=today.year - 2, day=28)
    return f"institutions.id:{UIUC_ID},from_publication_date:{start.isoformat()}"


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
        page_dir = page_dir_for(self.cache_dir, filter_str)
        page_dir.mkdir(parents=True, exist_ok=True)
        cursor: str | None = "*"
        n = 0
        for path in _cached_pages(page_dir):
            page = json.loads(path.read_text())
            yield page["results"]
            cursor = page["next_cursor"]
            n += 1
        while cursor is not None:
            params = {"filter": filter_str, "per_page": per_page, "cursor": cursor,
                      "select": ",".join(WORK_FIELDS)}
            if self.api_key:
                params["api_key"] = self.api_key
            if self.mailto:
                params["mailto"] = self.mailto
            resp = self._get(params)
            body = resp.json()
            results = body.get("results") or []
            next_cursor = body.get("meta", {}).get("next_cursor") if results else None
            tmp = page_dir / f"page-{n:05d}.json.tmp"
            tmp.write_text(json.dumps({"cursor": cursor, "next_cursor": next_cursor, "results": results}))
            tmp.rename(page_dir / f"page-{n:05d}.json")
            yield results
            n += 1
            cursor = next_cursor
            remaining = resp.headers.get("x-ratelimit-remaining-usd")
            if cursor is not None and remaining is not None and float(remaining) < self.min_remaining_usd:
                raise QuotaExhausted(
                    f"OpenAlex budget nearly exhausted (remaining ${remaining}). "
                    f"Re-run later or set OPENALEX_API_KEY; progress cached in {page_dir}.")
