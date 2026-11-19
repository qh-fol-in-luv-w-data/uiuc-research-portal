"""End-to-end eval of the research assistant against the running API.

    uv run python eval/run.py [--api http://localhost:8010] [--only req1,fac2]

Per question: SSE contract, plan (intent, sort), source relevance (keyword proxy), date window, citation
validity, answer language, prompt leakage, latency. Writes eval/results.jsonl and eval/report.md."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).parent
VI = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)
LEAK = re.compile(r"<think>|</think>|Sources:\n|You answer questions about|system prompt", re.I)


def ask(client: httpx.Client, api: str, item: dict) -> dict:
    body = {"question": item["q"], "history": item.get("history", []), "lang": item.get("ui", "en")}
    t0, ttft, events = time.perf_counter(), None, []
    with client.stream("POST", f"{api}/api/chat", json=body, timeout=180) as r:
        if r.status_code != 200:
            return {"status": r.status_code, "events": [], "latency": time.perf_counter() - t0, "ttft": None}
        ev = None
        for line in r.iter_lines():
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                if ev == "token" and ttft is None:
                    ttft = time.perf_counter() - t0
                events.append((ev, json.loads(line[6:])))
    return {"status": 200, "events": events, "latency": time.perf_counter() - t0, "ttft": ttft}


def as_list(x):
    return x if isinstance(x, list) else [x]


def score(item: dict, res: dict) -> dict:
    ev = res["events"]
    names = [e for e, _ in ev]
    get = lambda n: next((d for e, d in ev if e == n), None)  # noqa: E731
    plan, srcs, done = get("plan") or {}, (get("sources") or {}).get("sources", []), get("done") or {}
    answer = done.get("answer", "")
    fails: list[str] = []

    order_ok = res["status"] == 200 and names[:2] == ["plan", "sources"] and names[-1] == "done" \
        and all(n == "token" for n in names[2:-1])
    if not order_ok:
        fails.append(f"contract({res['status']},{','.join(dict.fromkeys(names))})")
    if plan.get("intent") not in as_list(item["intent"]):
        fails.append(f"intent={plan.get('intent')}")
    if item.get("sort") and plan.get("sort") not in as_list(item["sort"]):
        fails.append(f"sort={plan.get('sort')}")

    rel = None
    if item.get("kw") and srcs:
        kw = re.compile(item["kw"], re.I)
        top = srcs[:5]
        rel = sum(bool(kw.search(s["title"] + " " + (s.get("meta") or ""))) for s in top) / len(top)
        if rel < 0.4:
            fails.append(f"relevance={rel:.1f}")
    if item.get("kw") and not srcs and not item.get("expect_few"):
        fails.append("no_sources")

    if item.get("years"):
        bad = [s["meta"] for s in srcs if s["kind"] == "work"
               and not any(str(y) in s["meta"] for y in item["years"])]
        if bad:
            fails.append(f"dates({len(bad)} outside {item['years']})")
        # the sort order is also shown by the plan; "recent" must list newest first
    cites = [int(n) for n in re.findall(r"\[(\d+)\]", answer)]
    if any(n < 1 or n > len(srcs) for n in cites):
        fails.append("invalid_citation")
    if plan.get("sort") in ("recent", "cited") and cites and cites[0] != min(cites):
        fails.append(f"order(first [{cites[0]}], best cited [{min(cites)}])")  # e.g. calls an older paper "newest"
    if srcs and not cites and plan.get("intent") != "out_of_scope":
        fails.append("no_citation")
    want = item.get("lang", "en")
    if want == "vi" and not VI.search(answer):
        fails.append("not_vietnamese")
    if want == "en" and VI.search(answer):
        fails.append("not_english")
    if LEAK.search(answer):
        fails.append("leak")
    if not answer.strip():
        fails.append("empty_answer")
    if res["latency"] > 15:
        fails.append(f"slow({res['latency']:.0f}s)")
    return {"id": item["id"], "cat": item["cat"], "q": item["q"], "pass": not fails, "fails": fails,
            "plan": plan, "n_sources": len(srcs), "relevance": rel, "n_cites": len(set(cites)),
            "latency": round(res["latency"], 2), "ttft": round(res["ttft"], 2) if res["ttft"] else None,
            "sources": [f"[{s['n']}] {s['title']} — {s.get('meta', '')}" for s in srcs], "answer": answer}


def report(rows: list[dict]) -> str:
    lat = [r["latency"] for r in rows]
    ttft = [r["ttft"] for r in rows if r["ttft"]]
    p = lambda xs, q: sorted(xs)[min(len(xs) - 1, int(q * len(xs)))]  # noqa: E731
    out = [f"# Assistant eval — {time.strftime('%Y-%m-%d %H:%M')}", "",
           f"**{sum(r['pass'] for r in rows)}/{len(rows)} passed.** Latency p50 {statistics.median(lat):.1f}s, "
           f"p90 {p(lat, .9):.1f}s, max {max(lat):.1f}s; first token p50 {statistics.median(ttft):.1f}s.", "",
           "| Category | Passed | Intent ok | Mean relevance@5 |", "|---|---|---|---|"]
    for cat in dict.fromkeys(r["cat"] for r in rows):
        rs = [r for r in rows if r["cat"] == cat]
        rels = [r["relevance"] for r in rs if r["relevance"] is not None]
        out.append(f"| {cat} | {sum(r['pass'] for r in rs)}/{len(rs)} | "
                   f"{sum(not any(f.startswith('intent') for f in r['fails']) for r in rs)}/{len(rs)} | "
                   f"{statistics.mean(rels):.2f} |" if rels else f"| {cat} | {sum(r['pass'] for r in rs)}/{len(rs)} | "
                   f"{sum(not any(f.startswith('intent') for f in r['fails']) for r in rs)}/{len(rs)} | – |")
    out += ["", "## Failures", ""]
    for r in rows:
        if not r["pass"]:
            out.append(f"- **{r['id']}** {r['q']} → {', '.join(r['fails'])} (plan {r['plan'].get('intent')}/"
                       f"{r['plan'].get('sort')}/{r['plan'].get('source')})")
    out += ["", "## All answers", ""]
    for r in rows:
        out += [f"### {r['id']} {'✅' if r['pass'] else '❌'} {r['q']}",
                f"plan: `{json.dumps(r['plan'], ensure_ascii=False)}` · {r['latency']}s", "",
                *[f"- {s}" for s in r["sources"]], "", r["answer"], ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8010")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    items = yaml.safe_load((HERE / "queries.yaml").read_text())
    if args.only:
        items = [i for i in items if i["id"] in args.only.split(",")]
    rows = []
    with httpx.Client() as client:
        ask(client, args.api, {"q": "warm up: recent UIUC papers on robotics"})
        for item in items:
            row = score(item, ask(client, args.api, item))
            rows.append(row)
            print(f"{'PASS' if row['pass'] else 'FAIL'} {row['id']:7} {row['latency']:5.1f}s "
                  f"{row['plan'].get('intent', '?'):12} {row['plan'].get('sort', ''):9} {' '.join(row['fails'])}",
                  flush=True)
    (HERE / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (HERE / "report.md").write_text(report(rows))
    print(f"\n{sum(r['pass'] for r in rows)}/{len(rows)} passed -> eval/report.md")


if __name__ == "__main__":
    main()
