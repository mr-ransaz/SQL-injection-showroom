# SQL-injection-showroom 0.1.0

By **MR Ransaz** · MIT 2026 · [mr-ransaz/SQL-injection-showroom](https://github.com/mr-ransaz/SQL-injection-showroom)

> **Intentionally vulnerable. Local educational use only.** Use synthetic data
> only. Keep this app on loopback. Do not deploy publicly, use tunnels, or point
> it at another project's database. Local controls are safeguards, not a sandbox
> or a production security claim.

A small Python 3.14 portfolio project showing why SQL code and input data must
stay separate. The same search runs through deliberately interpolated SQL and a
parameterized SQLite query. A responsive dark interface puts their result tables,
SQL and parameters next to each other, stacking the panels on narrow screens.

The lab demonstrates exactly two injection effects: boolean manipulation that
broadens results, and UNION that reads explicitly fake internal records. It also
shows how parameterization preserves legitimate apostrophes.

## PowerShell quick start

Run from the repository root on Windows with Python **3.14** installed:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m sqli_showroom
```

**The terminal stays busy while the server runs.** Open
**[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in a browser.
Stop the server with **Ctrl+C**. All subsequent Python commands use the project
venv. The default launcher binds only `127.0.0.1` and disables proxy-header trust.

If `py -3.14` reports no installed Python, verify your installed Python 3.14
executable and use its absolute path with `-m venv .venv`. This machine's legacy
launcher had that discovery problem; the actual Python314 executable successfully
created the venv. No global Python upgrade or system setting change is required.

Some restricted environments require a writable process-local temporary folder
for dependency/build operations. The following PowerShell preparation is optional:

```powershell
New-Item -ItemType Directory -Force .tmp | Out-Null
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.tmp/pip-cache'
```

Install/build commands require package-registry access. Running the lab itself
uses local assets and same-origin HTTP only, with no external fonts, scripts,
analytics or configured telemetry exporter.

## Try it in 60 seconds

1. Open `/`. The initial **Normal search** finds `Canvas backpack` in both panels.
2. Click **Literal apostrophe**. `Maker's` finds `Maker's notebook` in Fixed;
   Vulnerable shows a controlled SQL error because its string literal is broken.
3. Click **Boolean injection**. Vulnerable returns all four public products;
   Fixed returns no matching rows.
4. Click **UNION injection**. Vulnerable returns four public products plus two
   highlighted **SYNTHETIC INTERNAL** rows. Fixed returns no rows. Look for the
   fake `DEMO_ONLY_INTERNAL_MARKER` / `SYNTHETIC_NOT_A_SECRET` fixture.
5. Inspect **Constructed SQL**, **SQL template** and separately supplied
   **Parameters**. Click **Reset demo data** and confirm to restore the fixtures.

The exact local teaching strings are available in the preset buttons and
`GET /api/examples`; no external target or general SQL console is involved.

## Why the results differ

These short illustrative examples use only `name` to keep the contrast readable;
the real lab projects four columns, including a record-type marker.

| Vulnerable: input becomes SQL syntax | Fixed: input stays a bound value |
| --- | --- |
| `sql = f"SELECT name FROM products WHERE name LIKE '%{query}%'"` | `sql = "SELECT name FROM products WHERE name LIKE ?"` |
| `connection.execute(sql)` | `connection.execute(sql, (f"%{query}%",))` |

The vulnerable string lets a quote end the SQL literal. The boolean preset changes
the predicate; the UNION preset combines the public projection with synthetic
internal records. The fixed template stays constant: SQLite receives the entire
search pattern as one data value, including its quotes. The defense is separation
of code and data. Filtering or manually escaping supposedly dangerous characters
is not the fix used here. See the
[OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html).

**LIKE behavior is intentional:** empty input matches all public products; `%`
matches any sequence, `_` matches one character, and backslash is an ordinary
character because no `ESCAPE` clause is configured. Thus this is a LIKE pattern
search, not literal-substring semantics. Binding protects SQL structure without
removing LIKE wildcards. Results are capped at 100 rows; SQLite VM work is bounded
for this tiny demo. Neither measure makes the vulnerable query a sandbox.

## API

| Method | Endpoint | Purpose / body |
| --- | --- | --- |
| GET | `/` | Actual web interface |
| GET | `/assets/app.css`, `/assets/app.js` | Packaged local assets |
| GET | `/health` | Typed `{"status":"ok"}` |
| GET | `/api/examples` | Four synthetic presets and explanations |
| GET | `/api/config` | Per-process reset CSRF token; never log or put it in a URL |
| POST | `/api/search/vulnerable` | `{"query":"backpack"}`; constructed SQL and rows |
| POST | `/api/search/fixed` | Same body; SQL template, separate parameters and rows |
| POST | `/api/reset` | `{}`; requires `X-CSRF-Token` from local config |
| GET | `/openapi.json` | Typed API schema; CDN-backed Swagger/ReDoc pages disabled |

Search strings are limited to 256 characters; request bodies to 4096 bytes.
Unknown JSON fields, non-string search values and malformed JSON are rejected.
POST requests require `application/json`; supplied `Origin` must exactly match
the HTTP server's scheme/Host/port. The UI supplies its origin automatically.

Errors have one envelope: `{"error":{"code":"...","message":"..."}}`.
An educational malformed-query result returns HTTP 200 with that error detail,
the intentionally displayed constructed SQL, and no rows. It is visibly an error,
not a successful empty result. Invalid requests use 4xx; unexpected application
errors use a sanitized 500 with no raw exception or filesystem path.

## Configuration and data lifecycle

| Setting | Default | Behavior |
| --- | --- | --- |
| Python | 3.14 only | Package metadata requires `>=3.14,<3.15` |
| Launcher address | `127.0.0.1` | No public-host option |
| `--port` | `8000` | Integer from 1 through 65535 |
| `SQLI_SHOWROOM_DB` | `.demo-data/showroom.sqlite3` | Relative to launch directory; use an absolute dedicated path when installed elsewhere |

Launching from this checkout creates the ignored `.demo-data` directory here.
Startup displays the resolved path with control characters escaped. No HTTP
request can choose a database path. Set the environment variable before launch
only when intentionally selecting another dedicated synthetic demo database.

Initialization creates missing parent directories and transactional fixtures:
`products(id, name, description)` and `internal_records(id, label, value)`.
A small ownership metadata table prevents silently repurposing an unrelated
database. An existing valid showroom database is preserved on restart. Reset
transactionally restores four public and two internal fixtures and is repeatable.
Each operation owns and closes its connection; threads never share a connection.
Search does not recreate the schema. All supplied values outside the explicitly
named vulnerable lab module use bound parameters.

## Checks and reproducibility

Install the dev extra first, then run these from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\pytest.exe -q
git diff --check
.\.venv\Scripts\python.exe scripts/smoke_test.py
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe scripts/package_check.py
```

Pytest enforces **at least 90% coverage with branches enabled**, measuring only
application Python. HTML/CSS and browser JavaScript are **not measured**. Tests
use fresh temporary databases and realistic loopback peer addresses. The ignored
`.test-tmp` directory belongs to pytest and is recreated for each run.

The smoke script starts this checkout using `sys.executable` and an explicit `src`
import path on a free loopback port. It checks health, HTML/assets, all four
comparisons, internal-marker isolation and CSRF reset over real HTTP. A bounded
health poll and `finally` cleanup stop its child and remove its own temporary data
on success or failure. It prints PASS/FAIL lines and exits 0 only on success.

`python -m build` builds the sdist and then the wheel from that sdist. The manifest
includes verification scripts, fixtures and documentation. The wheel includes
HTML/CSS/JS as package data. `package_check.py` creates an ignored disposable venv,
installs the wheel, checks dependency/import resolution, and launches from a
directory outside the repository root with a fresh explicit database path. It
verifies root HTML, CSS, JS and health, then removes its own venv/database.
Build artifacts in `dist/` and `build/` remain ignored and are never published.

See [STATE.md](STATE.md) for final gate counts and [NOTES.md](NOTES.md) for actual
stage results, dependency choices and environment details.

The final local regression run passed **92 tests through both entry points**, with
**99.21% application coverage including branches**. Ruff, dependency consistency,
live HTTP smoke, wheel/sdist build and installed-wheel UI/assets/health checks
passed on Windows with Python 3.14.0. This does not establish hosted CI success.

## Browser checks versus HTTP checks

Local browser inspection verified initial loading and the four preset outcomes,
desktop panels sharing a row at 1366px, and stacked panels at a 390px viewport
without horizontal document overflow. The inspected mobile page reported no
browser warning/error logs. These checks are separate from pytest and HTTP smoke.

**Browser reset confirmation completion remains unverified:** the in-app browser
automation timed out on its native confirmation dialog. Missing/invalid CSRF,
same-origin validation, fixture restoration and repeated reset are verified by
automated API tests and real HTTP smoke. Manually accept and cancel the browser
reset confirmation before treating that UI flow as verified. No other browser
engines, screen readers or complete keyboard/accessibility audit were tested.

## Architecture and layout

```text
src/sqli_showroom/
  __main__.py        loopback launcher and port validation
  app.py             application factory, typed routes, packaged asset serving
  boundary.py        peer, Host, Origin, JSON limits, headers, safe errors
  database.py        fixtures, ownership check, lifecycle and bound search
  vulnerable_lab.py  deliberately interpolated SELECT; synthetic lab only
  models.py          request/response contracts and teaching presets
  static/            HTML, CSS and vanilla JavaScript
tests/               temporary-database regression and API/UI contract checks
scripts/             real HTTP smoke and installed-wheel verification
.github/workflows/   Windows/Ubuntu Python 3.14 checks
```

FastAPI handles typed HTTP contracts; synchronous operations run in its worker
threads with independent SQLite connections. Vanilla JavaScript calls both searches
and renders every input/database value through safe DOM methods such as
`textContent`. Static files are resolved relative to the installed package.

## Security boundaries and known limitations

- The application checks the actual IPv4/IPv6 loopback peer and explicit
  `localhost`, `127.0.0.1` or `[::1]` Host values with optional valid ports.
  It ignores client `X-Forwarded-For`; the launcher disables Uvicorn proxy trust.
- CORS is disabled. JSON content-type/Origin checks, custom-header CSRF for reset,
  no-store responses, a restrictive CSP and safe DOM rendering support local use.
  CSRF tokens change on restart; reload the UI if a reset token becomes stale.
- SQL text and parameters are deliberately visible for education. Never enter
  private information or real credentials. Access logging is disabled by the
  supported launcher; application errors do not log raw exceptions or inputs.
- Vulnerable searches use `connection.execute`, never user-input `executescript`.
  Read-only SQLite search connections, one-statement execution, limits and local
  boundary checks **are not a security sandbox or production-grade isolation**.
- Local processes can access this lab. It provides no authentication, authorization
  system, browser isolation or defense against hostile software on the machine.
- Scope excludes stacked-query demos, blind automation, file/OS extraction,
  remote testing, real secrets, external scanning, Docker and public deployment.
  This is not comprehensive SQL injection coverage or a production-ready service.
- Direct dependencies are pinned; transitive versions are not a full lockfile.
  One upstream Starlette/httpx TestClient deprecation warning remains visible;
  no failures or warnings are suppressed.

CI uses read-only repository permissions, `ubuntu-latest`/`windows-latest`, Python
3.14, pinned action major versions, both pytest entry points, smoke, build and
wheel verification. **Hosted CI has not run.** The owner must later create the
empty GitHub repository, push the commits and observe the Actions results.
This release creates no tags and includes no Docker job.

