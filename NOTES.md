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

