from __future__ import annotations

import json
from pathlib import Path

import httpx
import yaml

from .openalex import BASE_URL
from .works import UIUC_ID, short_id


def fetch_institution(http: httpx.Client, inst_id: str) -> dict:
    resp = http.get(f"{BASE_URL}/institutions/{inst_id}",
                    params={"select": "id,display_name,associated_institutions,geo"}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def load_curated(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [str(entry["id"]) for entry in (yaml.safe_load(path.read_text()) or [])]


def resolve_uiuc_units(cache_dir: Path, http: httpx.Client, curated_path: Path) -> frozenset[str]:
    """UIUC plus its OpenAlex child institutions plus curated institutes OpenAlex does not link."""
    cache = cache_dir / "uiuc_units.json"
    if cache.exists():
        children = json.loads(cache.read_text())["children"]
    else:
        inst = fetch_institution(http, UIUC_ID)
        children = sorted(short_id(a["id"]) for a in inst.get("associated_institutions") or []
                          if a.get("relationship") == "child")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"children": children}))
    return frozenset({UIUC_ID, *children, *load_curated(curated_path)})
