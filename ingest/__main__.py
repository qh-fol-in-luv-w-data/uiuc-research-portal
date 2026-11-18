from __future__ import annotations

import argparse
import sys
from datetime import date

import httpx

from .aggregate import aggregate
from .config import load_settings
from .db import apply_migrations, connect
from .embed import embed_faculty, embed_works
from .embedder import EmbedderUnavailable, OllamaEmbedder
from .faculty import load_faculty
from .linking import embed_profiles, link_faculty
from .load_works import load_works
from .units import resolve_uiuc_units
from .openalex import (OpenAlexClient, QuotaExhausted, SliceTooLarge, month_slices, page_dir_for,
                       read_cached_results, resolve_filter)

STEPS = ["fetch-works", "clean-works", "load-faculty", "embed-profiles", "link-faculty", "embed", "aggregate"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m ingest", description="UIUC portal ingest pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ["migrate", *STEPS, "all"]:
        sp = sub.add_parser(name)
        sp.add_argument("--force", action="store_true", help="recompute embeddings from scratch")
        sp.add_argument("--refresh-filter", action="store_true", help="recompute the 2-year window from today")
    return p


def run_step(step: str, s, conn, http: httpx.Client, force: bool, refresh: bool) -> None:
    filter_str = resolve_filter(s.cache_dir, date.today(), refresh=refresh and step == "fetch-works")
    embedder = OllamaEmbedder(http, s.ollama_url, s.embed_model)
    if step == "fetch-works":
        client = OpenAlexClient(http, s.cache_dir, api_key=s.openalex_api_key, mailto=s.openalex_mailto)
        total = 0
        for sl in month_slices(filter_str):
            for page in client.iter_pages(sl):
                total += len(page)
            print(f"fetch-works: {total} works (through {sl.rsplit('from_publication_date:', 1)[1]})", flush=True)
    elif step == "clean-works":
        raw = (w for sl in month_slices(filter_str) for w in read_cached_results(page_dir_for(s.cache_dir, sl)))
        units = resolve_uiuc_units(s.cache_dir, http, s.data_dir / "uiuc_units.yaml")
        print(load_works(conn, raw, uiuc_units=units))
    elif step == "load-faculty":
        print(load_faculty(conn, s.data_dir / "illinois-researchers.csv", s.data_dir))
    elif step == "embed-profiles":
        print(embed_profiles(conn, embedder))
    elif step == "link-faculty":
        print(link_faculty(conn))
    elif step == "embed":
        print("works embedded:", embed_works(conn, embedder, force=force,
                                             progress=lambda m: print(m, flush=True)))
        print("faculty embedded:", embed_faculty(conn, embedder, force=force))
    elif step == "aggregate":
        print(aggregate(conn, s.docs_dir)["overview"])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    s = load_settings()
    conn = connect(s.database_url)
    try:
        print("migrations applied:", apply_migrations(conn))
        if args.cmd == "migrate":
            return 0
        steps = STEPS if args.cmd == "all" else [args.cmd]
        with httpx.Client(headers={"User-Agent": "uiuc-research-portal-ingest"}) as http:
            for step in steps:
                print(f"== {step}", flush=True)
                run_step(step, s, conn, http, args.force, args.refresh_filter)
        return 0
    except (QuotaExhausted, SliceTooLarge) as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 2
    except EmbedderUnavailable as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 3
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
