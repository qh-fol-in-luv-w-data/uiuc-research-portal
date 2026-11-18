# Plan 2a + 3 — Data fixes, Read API, Next.js Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the single-page portal (spec §8) on real data. It is served by a read-only FastAPI service and built with Next.js, following the approved canvas mockup (https://claude.ai/artifact/MQWBWNKAtx5svuXRyNtRcM) and the motion plan below. Four data defects found while mocking up are fixed first.

**Architecture:**
- `apps/api` (FastAPI, psycopg pool) exposes typed read endpoints over the Plan 1 database.
- `apps/web` (Next.js App Router) renders aggregate sections as React Server Components. These fetch from the API server-side, so the browser never sees DB access or retrieval logic.
- Interactive parts (field filter, tabs, faculty search, drawer, map, assistant shell) are client components.
- Animation uses the `motion` library under one shared reduced-motion policy.
- The chat backend (`POST /api/chat`) belongs to Plan 2b. Here the assistant UI is built against the SSE contract with a test double.

**Tech Stack:**
- API: FastAPI, Pydantic v2, psycopg 3 + psycopg_pool, pytest + httpx TestClient.
- Web: Next.js 16.4 (App Router, TypeScript), React 19.3, Tailwind CSS 4.3, motion 14, Recharts 3.11, Leaflet 1.9 + react-leaflet 5, lucide-react, Vitest 5 + Testing Library, Playwright 1.65.

**Spec:** `docs/superpowers/specs/2026-11-16-uiuc-research-portal-design.md` (§6, §8, §9, §11). Design source: canvas mockup above. Motion rules: `engineering-skills:epic-design` (depth layers, reduced motion, GPU-only properties).

## Global Constraints

- Keep all 23,846 works. Do not cap at 20k (user decision 2026-11-18; explain in README).
- Partners exclude UIUC itself, the UI System (`I2801919071`), OpenAlex child institutions of UIUC, institutions whose lineage contains UIUC, and the curated list in `data/uiuc_units.yaml`.
- Rising topics require ≥ 40 works in the recent 12 months.
- Duplicates (preprint + published version) count once: keep the non-preprint record. Mark the others `duplicate_of`; exclude them from stats and lists.
- A work whose `counts_by_year` has citations dated 2+ years before its `publication_year` is flagged outlier `citations_predate_publication` (reissued old work).
- Production web build: `productionBrowserSourceMaps: false`. No DB URL, prompt or retrieval code in client bundles. The browser talks only to the Next.js server, which proxies to the API.
- Colors: navy `#13294B`, navy-2 `#1E3A6B`, orange `#FF5F05` (fills only), orange-ink `#C2410C` (text on white), ground `#F5F6F9`, ink `#0E1A30`, muted `#556074`, line `#DDE2EA`. Fonts: IBM Plex Sans / Sans Condensed / Mono via `next/font/google`. Dark theme mirrors these tokens.
- Motion: only `transform`, `opacity`, `clip-path`. Every animated component honours `useReducedMotion()`. Coarse pointers get no parallax. Nothing ships at `opacity: 0` without an in-view trigger fallback.
- Accessibility: WCAG AA contrast, real buttons and links, labelled inputs, keyboard focus ring `3px #FF5F05`.
- No `Co-Authored-By` lines in commits.

## File Structure

```
data/uiuc_units.yaml                     curated UIUC institutes OpenAlex does not link
ingest/openalex.py                       + fetch_institution(); counts_by_year in WORK_FIELDS; cache key includes fields
ingest/units.py                          resolve_uiuc_units(): children + lineage + curated
ingest/works.py                          is_uiuc via units; citations_predate_publication rule
ingest/dedupe.py                         mark_duplicates(): normalized-title groups
ingest/aggregate.py                      partners exclude units; rising_min=40; skip duplicates
db/migrations/002_quality.sql            works.duplicate_of, institutions.is_uiuc_unit
apps/api/app/main.py                     app factory, CORS off, routers
apps/api/app/db.py                       pool lifecycle
apps/api/app/schemas.py                  Pydantic response models (the web contract)
apps/api/app/routers/{health,stats,works,faculty}.py
apps/api/tests/…                         router tests against portal_test
apps/web/…                               Next.js app (see Task 4+)
data/institution.json                    campus facts + Wikimedia images with credit
docker-compose.yml                       + api, web services
```

## Motion plan (from epic-design, adapted to a data portal)

| Section | Depth layers | Technique | Trigger |
|---|---|---|---|
| Hero | 0 grid texture, 1 orange/navy glow blobs, 3 campus photo (parallax 0.8x, float loop 10s), 4 text | masked line reveal on H1, fade-up subtitle | on load |
| KPIs | 4 | count-up (900 ms, ease-out) + 60 ms stagger | in view, once |
| Focus areas | 2 tiles | scale-in by size order; hover lift `translateY(-3px)`; `layout` reorder on filter | in view / state |
| Output chart | 2 bars | bars grow from baseline (`scaleY` 0→1, transform-origin bottom), 15 ms stagger | in view, once |
| Section intros | 4 | word-by-word lighting (opacity 0.25→1) | scroll-linked |
| Lists & cards | 4 | fade-up stagger 40 ms; tab switch crossfade (`AnimatePresence`) | in view / state |
| Assistant | 4 | sources slide in, token stream, typing indicator | SSE events |

Reduced motion: all of the above render in their final state.

---

### Task 1: Data fixes (units, duplicates, reissues, rising threshold)

**Files:**
- Create: `data/uiuc_units.yaml`, `ingest/units.py`, `ingest/dedupe.py`, `db/migrations/002_quality.sql`, `tests/test_units.py`, `tests/test_dedupe.py`
- Modify: `ingest/openalex.py`, `ingest/works.py`, `ingest/load_works.py`, `ingest/aggregate.py`, `ingest/__main__.py`, tests for each

**Interfaces:**
- `fetch_institution(http, inst_id) -> dict`
- `resolve_uiuc_units(cache_dir, http, curated_path) -> set[str]` (cached in `cache_dir/uiuc_units.json`)
- `parse_work(w, uiuc_units: frozenset[str] = frozenset({UIUC_ID}))`
- `mark_outliers` adds reason `citations_predate_publication`
- `mark_duplicates(items) -> int` sets `work["duplicate_of"]`
- `compute_stats(conn, rising_min=40)`

- [ ] **Step 1: Failing tests**
  - Authorship at a curated unit (Woese `I4405271866`) → `is_uiuc` true.
  - `counts_by_year` with citations in 2019 for a 2026 work → outlier `citations_predate_publication`. Citations one year early (online-first) are not flagged.
  - Two works with the same normalized title (case, punctuation and whitespace folded), one `preprint` and one `article`: the article is kept and the preprint gets `duplicate_of`.
  - Partners exclude units.
  - Rising topics exclude topics with recent < 40.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Migration `002_quality.sql`:
```sql
ALTER TABLE works ADD COLUMN duplicate_of text;
ALTER TABLE institutions ADD COLUMN is_uiuc_unit boolean NOT NULL DEFAULT false;
CREATE INDEX works_duplicate_idx ON works (duplicate_of) WHERE duplicate_of IS NOT NULL;
```
  Every stats query and every list query adds `AND w.duplicate_of IS NULL`.
- [ ] **Step 4:** Tests pass. Re-run `fetch-works` (new cache key because the field list changed, ~160 requests), then `clean-works → aggregate`. Check: no UIUC institute in `top_partners`; "Metacognition…" flagged; duplicate count reported in `data-quality.md`.
- [ ] **Step 5:** Commit `fix(ingest): UIUC units, duplicate versions, reissued works, robust rising topics`.

### Task 2: Read API — health, overview, stats

**Files:** `apps/api/pyproject.toml` deps added to the root project (`fastapi`, `uvicorn[standard]`, `psycopg_pool`). Create `apps/api/app/{__init__,main,db,schemas}.py`, `routers/{health,stats}.py`, `apps/api/tests/{conftest,test_health,test_stats}.py`.

**Interfaces (web contract):**
```python
class Overview(BaseModel):
    works: int; citations: int; oa_share: float; faculty: int; faculty_linked: int
    partner_institutions: int; outliers: int
    institution: Institution          # from data/institution.json
class StatsPayload(BaseModel):
    key: Literal["monthly","types","fields","rising_topics","top_venues","top_partners","top_faculty"]
    computed_at: datetime; data: list[dict]
class Health(BaseModel):
    db: bool; ollama: bool; models: list[str]; missing_models: list[str]
```
`GET /health`, `GET /api/overview`, `GET /api/stats/{key}` (404 JSON `{error, detail}` for an unknown key).

- [ ] Steps: failing tests (seeded `stats_cache`; unknown key → 404; Ollama down → `ollama: false`, still 200) → implement → pass → commit.

### Task 3: Read API — works and faculty

**Interfaces:**
```python
class WorkCard(BaseModel):
    id: str; title: str; publication_date: date | None; type: str | None; venue: str | None
    cited_by_count: int; is_oa: bool; doi: str | None; field: str | None
    uiuc_authors: list[AuthorRef]      # AuthorRef(name, faculty_id: int | None)
class Page[T](BaseModel): items: list[T]; total: int; page: int; page_size: int
class FacultyCard(BaseModel):
    id: int; name: str; position: str | None; photo_url: str | None; primary_field: str | None
    keywords: list[str]; matched_keywords: list[str]; link_confidence: float | None
class FacultyProfile(FacultyCard):
    link_method: str | None; openalex_author_ids: list[str]; recent_works: list[WorkCard]
    topics: list[TopicCount]
```
- `GET /api/works?q&field&sort=recent|cited|relevance&page&page_size≤50`. `q` uses `websearch_to_tsquery` over `tsv` for now (Plan 2b swaps in hybrid search). Excludes outliers and duplicates.
- `GET /api/faculty?q&position&field&page`. `q` ranks `ts_rank(tsv)` + keyword overlap; `matched_keywords` = keywords containing a query term.
- `GET /api/faculty/{id}`.
- [ ] Steps: failing tests (sort orders, field filter, pagination bounds, 404 faculty, outliers/duplicates excluded) → implement → pass → commit.

### Task 4: Web scaffold, tokens, layout, API client

**Files:** `apps/web` via `npx create-next-app@16.4.6 apps/web --ts --tailwind --app --src-dir --eslint --no-turbopack-dev --import-alias "@/*"`, then:
- `src/app/layout.tsx` (fonts, theme tokens, skip link)
- `src/app/globals.css` (tokens as CSS variables for light and dark, reduced-motion block)
- `src/lib/api.ts` (server-only fetchers, `import "server-only"`, `API_URL` env, `next: { revalidate: 3600 }`)
- `src/lib/types.ts` (mirrors schemas)
- `src/components/motion/*` (`Reveal`, `CountUp`, `WordLight`, `useParallax`, all reduced-motion aware)
- `next.config.ts` (`productionBrowserSourceMaps: false`, `poweredByHeader: false`, rewrites `/api/:path*` → `${API_URL}/api/:path*` for client calls)
- [ ] Steps: Vitest for `CountUp` (reduced motion → final value immediately) and `api.ts` (error → typed `ApiError`) → implement → `npm run build` passes and `grep -r DATABASE_URL .next/static` is empty → commit.

### Task 5: Hero + KPIs
Header nav (sticky, `top: env(safe-area-inset-top)`), hero with depth layers 0/1/3/4, campus image via `next/image` with credit, 4 KPI tiles with `CountUp`. Test: renders real overview numbers from a fixture, and the headline is an `h1`.

### Task 6: Focus areas
Treemap tiles (flex-grow by count, as in the mockup) as `<button aria-pressed>`. The field filter lives in the URL (`?field=`) so it is shareable. It filters Notable and Faculty sections. Rising topics list and top faculty bars. Tests: clicking a tile sets the search param; a second click clears it.

### Task 7: Scholarly output
Recharts monthly bar chart (January bars in a lighter tone with the 1-January note; last month marked partial), type stacked bar + legend, OA share, top venues. Bars grow in view. Test: the chart has an accessible summary (`role="img"` + `aria-label` with min/max).

### Task 8: Notable publications
Tabs Most cited / Most recent (`role="tablist"`), field-aware, `AnimatePresence` crossfade. UIUC authors linked to the faculty drawer. Test: tab keyboard navigation (arrow keys) switches lists.

### Task 9: Faculty expertise + profile drawer
Search form (debounced, client fetch via the Next rewrite), position/field filters, card grid with initials avatar fallback for the 105 missing photos, drawer (`dialog`, focus trap, Esc closes) with keywords, recent works, topics and the link confidence badge. Tests: empty state, error state, drawer focus returns to the trigger.

### Task 10: Collaboration & campus
Leaflet map (client-only dynamic import, OSM tiles with attribution) with partner markers (institution geo fetched once in ingest → `institutions.lat/lon`; add to migration 002), top partners list, campus facts from `data/institution.json` with photo credits.

### Task 11: Assistant shell (contract with Plan 2b)
Inline section + floating button opening a side panel (mockup "Assistant" artboard). SSE client parses `plan`, `sources`, `token`, `done`, `error`. Citation chips scroll to the source card. "Assistant offline" state when `/health` reports Ollama down. Suggested questions include the two required ones. Tests use a fake SSE stream: event order renders correctly; `[n]` becomes a link.

### Task 12: Compose, e2e, polish
Add `api` and `web` services with healthchecks to `docker-compose.yml`; `make up`. Playwright: load page → filter by field → search faculty → open drawer → open assistant (mocked SSE). Lighthouse pass (performance ≥ 85, accessibility ≥ 95) recorded in `docs/`. Screenshots for the README.

## Self-review notes
- Spec §6 endpoints: Tasks 2–3 (chat in Plan 2b). §8 sections 1–7: Tasks 5–11. §9 errors: API 404/503 JSON, web error/empty states in each task. §11 compose: Task 12.
- UI tasks (5–12) state behaviour and tests rather than full JSX listings. The approved mockup is the visual source of truth, which keeps this plan reviewable.
