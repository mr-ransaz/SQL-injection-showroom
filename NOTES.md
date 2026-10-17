# Implementation notes

## Bootstrap and dependencies

- Started from a clean `main` at `af89dc6`; STATE.md did not exist.
- Installed Python is 3.14.0. The legacy `py` launcher does not discover it;
  the actual Python314 executable bootstrapped `.venv`.
- The sandbox's default temporary directory prevented ensurepip writes.
  Setting process-local TEMP/TMP to the project's ignored `.tmp` resolved it.
- Direct runtime pins: FastAPI 0.143.3 (typed API, current PyPI release) and
  Uvicorn 0.54.0 (minimal ASGI server, without optional standard extras).
- Dev extra: pytest 9.1.1, pytest-cov 7.1.0, httpx 0.28.1, Ruff 0.14.1,
  build 1.3.0. These provide regression tests, enforced branch coverage,
  in-process/real HTTP clients, lint/format gates and distribution builds.
- Build backend: setuptools 82.0.1, explicitly pinned for reproducible metadata
  and package-data handling. Direct pins do not lock transitive dependencies.
- Compatibility is established by installation and real execution on Python
  3.14, rather than assuming a minimum-version declaration proves support.
- PyPI metadata for every selected direct dependency accepts Python 3.14;
  editable installation succeeded and `python -m pip check` found no broken
  requirements. FastAPI's base dependency includes the OpenTelemetry API, but
  this app configures no telemetry provider/exporter or telemetry requests.

## Design

- Only vulnerable_lab.py interpolates user values into SQL. All other supplied
  SQL values use bound parameters. LIKE deliberately retains `%` and `_`
  wildcard behavior; backslash has no special escape meaning.
- Each operation closes its own connection. Initialization and reset use
  explicit transactions; initialization refuses unrelated database schemas.
- Read connections use SQLite read-only mode, a VM budget and a 100-row cap.
  These resource safeguards do not constitute isolation or a SQL sandbox.
- Exact local Host and same-Origin checks, actual loopback peer checks, bounded
  JSON, per-app CSRF tokens and sanitized errors protect the local lab boundary.
- Docker is explicitly out of scope. Hosted CI and browser behavior remain
  unverified until separately executed. Python coverage excludes HTML/JS.

## Stage 1 verification

- Ruff check and format check passed; both pytest entry points: 72 passed,
  97.95% application coverage with branches enabled. `git diff --check` passed.
- The only forbidden-pattern matches are the documented AGENTS.md rule examples.
- One visible upstream Starlette warning deprecates its httpx TestClient path;
  httpx remains required by this project's tool scope and passes all checks.
- Live UI, smoke and wheel checks are deferred to their implementation stages.

## Stage 2 verification

- Root UI, CSS and JavaScript are package resources. Dynamic text uses safe DOM
  methods; no innerHTML. Four presets, independent panel status/results,
  separate SQL/parameter displays, explanatory text and confirmed reset flow.
- Swagger/ReDoc routes are disabled to avoid their CDN dependencies;
  the typed API schema remains at /openapi.json. No dependency changes.
- Ruff check and format check passed; both pytest entry points: 79 passed,
  98.05% branch-enabled application coverage. `git diff --check` passed.
- Pattern scan still matches only AGENTS.md rule examples.
- Real subprocess smoke: health, root/assets, normal/apostrophe/boolean/UNION
  comparisons, absent-CSRF rejection, valid reset, process/data cleanup passed;
  exit 0. This is HTTP verification, not a browser test.
- Wheel package-data and hosted CI remain unverified at this checkpoint.

## Stage 3 verification and decisions

- Added read-only Windows/Ubuntu Python 3.14 CI with pinned action major
  versions, venv tools, both pytest entry points, real HTTP smoke, builds and
  installed-wheel verification. Hosted Actions has not been run.
- Added the source manifest so the sdist contains test conftest/fixtures,
  verification helpers and project documentation. Wheel package data is
  resolved relative to the installed package, independent of launch directory.
- A real subprocess regression reproduced a startup traceback when the database
  parent was a file. Initialization now runs in the launcher's guarded factory
  call; the same regression verifies sanitized output and a failing exit code.
- Malformed SQL containing a null character now produces a controlled teaching
  error. Chunked-body limits, missing/duplicate Hosts, disconnect handling,
  transaction rollback and smoke failure cleanup have meaningful regression tests.
- Final gates: Ruff check and format --check passed. Both pytest entry points
  passed 92 tests, with 99.21% coverage and branches enabled. No threshold changes
  or warning suppression. Browser JavaScript and HTML are not coverage targets.
- git diff --check passed; forbidden-pattern inspection found only the permitted
  AGENTS.md examples. pip check: no broken requirements. Editable dev installation
  and all selected direct dependency Python requirements were verified on 3.14.0.
- build produced wheel and sdist; archive inspection confirmed all three UI assets,
  no databases in the wheel, and conftest/package-check helpers in the sdist.
- Installed-wheel check passed from a non-root working directory in a fresh venv:
  pip check, installed import origin/version, health, root HTML, CSS and JS.
  The script stopped its server and removed its own disposable venv and database.
- Read/write operations for bootstrap/build used project-local temporary paths.
  No runtime dependencies changed after Stage 1. Ruff 0.14.1 was kept for its
  Python 3.14 target/consistent formatter; build 1.3.0 provides the needed isolated
  wheel-from-sdist workflow. No new dependency was needed for later stages.

Actual final live smoke output (exit 0):

```text
PASS live loopback health
PASS root HTML and local CSS/JS assets
PASS Normal search: vulnerable/fixed comparison
PASS Literal apostrophe: vulnerable/fixed comparison
PASS Boolean injection: vulnerable/fixed comparison
PASS UNION injection: vulnerable/fixed comparison
PASS reset: missing CSRF rejected; valid same-origin CSRF accepted
PASS child process stopped and temporary demo data removed
```

Browser checks, separate from HTTP: initial normal results and all four preset
outcomes verified in the in-app browser; desktop panels share a row at 1366px;
390px mobile panels stack without horizontal document overflow. The inspected
mobile page reported no browser warning/error logs. Native reset confirmation
blocked automation (click timeout; dialog API did not expose a usable dialog), so
browser reset accept/cancel completion remains a manual check. API and real HTTP
reset checks passed. No other browser engines or full accessibility audit ran.
The browser-check server was stopped and port 8000 was verified free afterward.

Remaining unverified: hosted CI/Ubuntu execution, manual browser reset confirmation
and broader accessibility/browser coverage. Docker is excluded from this release.
No push, tag, GitHub repository creation, package publishing or subagents occurred.

