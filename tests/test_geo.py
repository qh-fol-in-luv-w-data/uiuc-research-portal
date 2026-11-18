import httpx

from ingest.aggregate import aggregate
from ingest.db import get_stat
from ingest.geo import partner_map
from ingest.load_works import load_works
from tests.factories import HERZEN, UIUC, make_author, make_work


def test_partner_map_fetches_geo_once_and_caches(db, tmp_path):
    load_works(db, [make_work(id="W1", authorships=[make_author("A1", "J D", [UIUC], "UIUC"),
                                                    make_author("A2", "I P", [HERZEN], "Herzen")])])
    aggregate(db, tmp_path / "docs")
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"id": "https://openalex.org/I999", "display_name": "Herzen University",
                                         "geo": {"latitude": 59.93, "longitude": 30.32, "city": "St Petersburg"}})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    rows = partner_map(db, http, tmp_path)
    assert rows == [{"id": "I999", "name": "Herzen University", "country": "RU", "count": 1,
                     "lat": 59.93, "lon": 30.32, "city": "St Petersburg"}]
    assert get_stat(db, "partner_map") == rows
    partner_map(db, http, tmp_path)
    assert calls == ["/institutions/I999"]  # second run served from cache
