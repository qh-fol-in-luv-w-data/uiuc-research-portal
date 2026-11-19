# Security review — 2026-11-19

Scope: the whole stack as shipped by `docker compose up` (Next.js web, FastAPI API, Postgres, local Ollama), the
research assistant, the repository and its history. Re-run the attack suite with `make attacks` (needs the stack and
Ollama running); it writes `eval/attacks-report.md`.

## Automated scans

| Check | Tool | Result |
|---|---|---|
| Secrets in git history (37 commits) and source folders | gitleaks 8 | none found |
| JavaScript dependencies (prod + dev) | `npm audit` | 0 vulnerabilities |
| Python dependencies (85 packages) | `pip-audit` | no known vulnerabilities |
| SQL injection (9 payloads × chat question, chat history, `/api/works`, `/api/faculty`) | `eval/attacks.py` | no 5xx, no SQL errors, row counts of 7 tables unchanged |
| Prompt injection (12 attacks, English and Vietnamese) | `eval/attacks.py` | all blocked after the fixes below (5 got through before) |

## Findings and fixes

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | High | Postgres (with faculty emails, fixed dev password) and the API were published on all interfaces (`0.0.0.0`): reachable from the local network | All ports bind to `127.0.0.1`; `BIND_ADDR=0.0.0.0` opts in to LAN access (README) |
| 2 | High | Prompt injection wrapped inside a valid research question reached the answer model: it leaked the whole system prompt, appended a phishing link (`http://evil… click to verify your account`), echoed a `<script>` tag, and repeated a planted false fact ("UIUC was founded in 1999") | Three layers that do not rely on the model: (a) the answer model never sees the raw question or history, only the planner's rewritten standalone question; (b) a sentence guard drops, before streaming, any sentence with a URL, HTML, markdown link or text copied from the instructions; (c) a grounding filter drops sentences repeating names or numbers that only the question mentions and no source supports. Plus an "untrusted question" rule in the prompt |
| 3 | Medium | `/api/chat` had no concurrency limit: a request loop could tie up the local model server (cheap denial of service) | 2 chats answered at once, further requests get `429` (localized "busy" message in the UI); the slot is released even when the client disconnects |
| 4 | Medium | A NUL byte in a search (`?q=a%00b`) crashed the request (unhandled `psycopg.DataError`, connection dropped) | NUL rejected with `400`; `DataError` → `400`; any unexpected error → generic `500` JSON without internals |
| 5 | Medium | No security headers | CSP (`default-src 'self'`, `connect-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`…), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `COOP` |
| 6 | Low | The web proxy forwarded `..` path segments (reaching the API's `/docs`) and read request bodies of any size | Path segments validated (`404`), bodies over 64 KB rejected (`413`) |
| 7 | Low | `page=10^20` caused a database error | `page ≤ 10,000` (`422`) |
| 8 | Low | Links from data (DOIs, image credits) were not scheme-checked | Only `http(s)` links are rendered (React 19 already blocks `javascript:`; this is defence in depth) |
| 9 | Hardening | The API connected as the database owner | API sessions are read-only (`default_transaction_read_only=on`): even a successful injection could not change data |

Checked and fine: every SQL statement is parameterized (f-strings only splice fixed fragments; user text never
enters SQL text); faculty search terms are reduced to `[a-z0-9]+` before any regex; the answer is rendered as text
(no `dangerouslySetInnerHTML`); API and web containers run as non-root users; the API exposes no email field; the
browser never talks to the API directly; production builds ship no source maps.

## Residual risks (accepted)

- **CSP allows inline scripts** (`'unsafe-inline'`): Next.js streaming needs them unless every page uses per-request
  nonces, which would turn the prerendered pages fully dynamic. External script sources are still blocked.
- **Indirect prompt injection** through publication abstracts (third-party OpenAlex data) is limited by the same
  guards (no links/markup reach the user, 200-character abstracts) but a crafted abstract could still bias wording.
- **The database password is a fixed development value**; safe only while ports stay on `127.0.0.1`. Set a real
  password before any deployment beyond a laptop.
- **Faculty emails ship in the public `-db` image** (decided with the repository owner); they are not served by the API.
- The 4B models are not a security boundary: the guards above are what enforce the rules.
