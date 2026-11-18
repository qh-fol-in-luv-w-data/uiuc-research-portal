import json

import httpx

from ingest.units import resolve_uiuc_units


def test_resolve_units_combines_children_and_curated_and_caches(tmp_path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"id": "https://openalex.org/I157725225", "associated_institutions": [
            {"id": "https://openalex.org/I4210135837", "display_name": "NCSA", "relationship": "child"},
            {"id": "https://openalex.org/I2801919071", "display_name": "UI System", "relationship": "parent"},
            {"id": "https://openalex.org/I1308343090", "display_name": "Carle", "relationship": "related"}]})

    curated = tmp_path / "units.yaml"
    curated.write_text("- id: I4405271866\n  name: Woese\n")
    http = httpx.Client(transport=httpx.MockTransport(handler))
    units = resolve_uiuc_units(tmp_path, http, curated)
    assert units == frozenset({"I157725225", "I4210135837", "I4405271866"})
    assert json.loads((tmp_path / "uiuc_units.json").read_text())["children"] == ["I4210135837"]
    assert resolve_uiuc_units(tmp_path, http, curated) == units
    assert len(calls) == 1  # second call served from cache
