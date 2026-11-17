from datetime import date

import httpx
import pytest

from ingest.openalex import (OpenAlexClient, QuotaExhausted, SliceTooLarge, month_slices, page_dir_for,
                             read_cached_results, resolve_filter, works_filter)

BASE = "institutions.id:I157725225,from_publication_date:2024-11-17"


def _handler(pages, calls, remaining="0.09", count=None):
    """pages: list of result lists for page=1..N; count defaults to total results."""
    total = count if count is not None else sum(len(p) for p in pages)

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        calls.append(page)
        results = pages[page - 1] if page <= len(pages) else []
        return httpx.Response(200, json={"meta": {"count": total}, "results": results},
                              headers={"x-ratelimit-remaining-usd": remaining})
    return handler


PAGES = [[{"id": "W1"}, {"id": "W2"}], [{"id": "W3"}]]


def test_works_filter_two_years_back():
    assert works_filter(date(2026, 11, 17)) == BASE
    assert works_filter(date(2028, 2, 29)).endswith("2026-02-28")


def test_resolve_filter_is_sticky(tmp_path):
    f1 = resolve_filter(tmp_path, date(2026, 11, 17))
    assert resolve_filter(tmp_path, date(2026, 11, 20)) == f1
    assert resolve_filter(tmp_path, date(2026, 11, 20), refresh=True).endswith("2024-11-20")


def test_month_slices_cover_window_with_open_last_slice():
    s = month_slices(BASE)
    assert len(s) == 25
    assert s[0] == "institutions.id:I157725225,from_publication_date:2024-11-17,to_publication_date:2024-11-30"
    assert s[1].endswith("from_publication_date:2024-12-01,to_publication_date:2024-12-31")
    assert s[-1] == "institutions.id:I157725225,from_publication_date:2026-11-01"  # open: catches future-dated


def test_iter_pages_fetches_all_and_caches(tmp_path):
    calls = []
    http = httpx.Client(transport=httpx.MockTransport(_handler(PAGES, calls)))
    client = OpenAlexClient(http, tmp_path, sleep=lambda s: None)
    ids = [w["id"] for page in client.iter_pages("F", per_page=2) for w in page]
    assert ids == ["W1", "W2", "W3"]
    assert calls == [1, 2]  # stops when page * per_page >= count
    assert [w["id"] for w in read_cached_results(page_dir_for(tmp_path, "F"))] == ["W1", "W2", "W3"]
    calls.clear()
    assert [w["id"] for page in client.iter_pages("F", per_page=2) for w in page] == ["W1", "W2", "W3"]
    assert calls == []  # fully served from cache


def test_quota_stop_then_resume(tmp_path):
    calls = []
    low = httpx.Client(transport=httpx.MockTransport(_handler(PAGES, calls, remaining="0.001")))
    with pytest.raises(QuotaExhausted):
        list(OpenAlexClient(low, tmp_path, sleep=lambda s: None).iter_pages("F", per_page=2))
    assert calls == [1]
    calls.clear()
    ok = httpx.Client(transport=httpx.MockTransport(_handler(PAGES, calls)))
    ids = [w["id"] for p in OpenAlexClient(ok, tmp_path, sleep=lambda s: None).iter_pages("F", per_page=2) for w in p]
    assert ids == ["W1", "W2", "W3"]
    assert calls == [2]


def test_slice_over_page_limit_raises(tmp_path):
    http = httpx.Client(transport=httpx.MockTransport(_handler(PAGES, [], count=10001)))
    with pytest.raises(SliceTooLarge):
        list(OpenAlexClient(http, tmp_path, sleep=lambda s: None).iter_pages("F"))


def test_api_key_is_sent_when_configured(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.url.params.get("api_key"))
        return httpx.Response(200, json={"meta": {"count": 1}, "results": [{"id": "W1"}]})

    client = OpenAlexClient(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path, api_key="K",
                            sleep=lambda s: None)
    list(client.iter_pages("F"))
    assert seen == ["K"]


def test_retries_on_500_then_succeeds(tmp_path):
    state = {"n": 0}
    sleeps = []

    def handler(request):
        state["n"] += 1
        if state["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"meta": {"count": 1}, "results": [{"id": "W1"}]})

    client = OpenAlexClient(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path, sleep=sleeps.append)
    assert [w["id"] for p in client.iter_pages("F") for w in p] == ["W1"]
    assert sleeps == [1, 2]


def test_long_retry_after_raises_quota(tmp_path):
    handler = lambda r: httpx.Response(429, headers={"retry-after": "76367"})
    client = OpenAlexClient(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path, sleep=lambda s: None)
    with pytest.raises(QuotaExhausted):
        list(client.iter_pages("F"))
