from datetime import date

import httpx
import pytest

from ingest.openalex import (OpenAlexClient, QuotaExhausted, page_dir_for, read_cached_results,
                             resolve_filter, works_filter)


def _pages_handler(pages, calls, remaining="0.09"):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["cursor"])
        idx = {"*": 0, "c1": 1, "c2": 2}[request.url.params["cursor"]]
        results, nxt = pages[idx]
        return httpx.Response(200, json={"meta": {"next_cursor": nxt}, "results": results},
                              headers={"x-ratelimit-remaining-usd": remaining})
    return handler


PAGES = [([{"id": "W1"}, {"id": "W2"}], "c1"), ([{"id": "W3"}], "c2"), ([], None)]


def test_works_filter_two_years_back():
    assert works_filter(date(2026, 11, 17)) == "institutions.id:I157725225,from_publication_date:2024-11-17"
    assert works_filter(date(2028, 2, 29)).endswith("2026-02-28")


def test_resolve_filter_is_sticky(tmp_path):
    f1 = resolve_filter(tmp_path, date(2026, 11, 17))
    assert resolve_filter(tmp_path, date(2026, 11, 20)) == f1
    assert resolve_filter(tmp_path, date(2026, 11, 20), refresh=True).endswith("2024-11-20")


def test_iter_pages_fetches_all_and_caches(tmp_path):
    calls = []
    http = httpx.Client(transport=httpx.MockTransport(_pages_handler(PAGES, calls)))
    client = OpenAlexClient(http, tmp_path, sleep=lambda s: None)
    ids = [w["id"] for page in client.iter_pages("F") for w in page]
    assert ids == ["W1", "W2", "W3"]
    assert calls == ["*", "c1", "c2"]
    assert [w["id"] for w in read_cached_results(page_dir_for(tmp_path, "F"))] == ["W1", "W2", "W3"]
    calls.clear()
    assert [w["id"] for page in client.iter_pages("F") for w in page] == ["W1", "W2", "W3"]
    assert calls == []  # fully served from cache


def test_quota_stop_then_resume(tmp_path):
    calls = []
    low = httpx.Client(transport=httpx.MockTransport(_pages_handler(PAGES, calls, remaining="0.001")))
    with pytest.raises(QuotaExhausted):
        list(OpenAlexClient(low, tmp_path, sleep=lambda s: None).iter_pages("F"))
    assert calls == ["*"]
    calls.clear()
    ok = httpx.Client(transport=httpx.MockTransport(_pages_handler(PAGES, calls)))
    ids = [w["id"] for page in OpenAlexClient(ok, tmp_path, sleep=lambda s: None).iter_pages("F") for w in page]
    assert ids == ["W1", "W2", "W3"]
    assert calls == ["c1", "c2"]


def test_retries_on_500_then_succeeds(tmp_path):
    state = {"n": 0}
    sleeps = []

    def handler(request):
        state["n"] += 1
        if state["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"meta": {"next_cursor": None}, "results": [{"id": "W1"}]})

    client = OpenAlexClient(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path, sleep=sleeps.append)
    assert [w["id"] for p in client.iter_pages("F") for w in p] == ["W1"]
    assert sleeps == [1, 2]


def test_long_retry_after_raises_quota(tmp_path):
    handler = lambda r: httpx.Response(429, headers={"retry-after": "76367"})
    client = OpenAlexClient(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path, sleep=lambda s: None)
    with pytest.raises(QuotaExhausted):
        list(client.iter_pages("F"))
