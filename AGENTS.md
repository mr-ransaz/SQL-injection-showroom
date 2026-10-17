# Working agreement

## Session-start protocol
1. Read this file and STATE.md before editing anything.
2. Run `git status --short`; stop if the tree is dirty. Never overwrite or
   discard existing changes.
3. Run `git log -1 --oneline`; confirm branch and Python version.
4. Inspect the relevant code, tests and docs before changing anything.
5. If STATE.md mentions a release tag, resolve it with
   `git rev-list -n 1 <tag>` (never use `^{commit}` in PowerShell).

## Rules
- Python 3.14 only. Run every Python tool through
  `.\.venv\Scripts\python.exe` (pip, ruff, pytest, project CLI/server).
  Never use global Python or global tool launchers. Git uses `git`.
- Dependencies follow the Project profile below. Every dependency change
  must be explained in NOTES.md. Dev-only tools go in the `dev` extra.
- Never log, store, print or commit real passwords, tokens, keys, .env
  files or databases. Use only public synthetic values in tests and docs.
  Never put raw exceptions or secret values into logs or responses.
- Inspect before editing; make the smallest complete fix; add meaningful
  regression tests. Never skip tests or suppress failures to pass a gate.
- README claims and captured outputs must be verified by execution.
  Clearly separate local/mocked checks from unverified external services
  (Docker, hosted CI, live network). Never claim an unrun check passed.
- No placeholders in committed files (YOUR_USERNAME, Your Name, TODO,
  changeme). Use the real values from the Project profile.
- Small Conventional Commits (feat:, fix:, test:, docs:, ci:, chore:) with
  explicit paths. Do not push, rewrite history, reset unrelated changes,
  or touch anything outside the project folder.
- Tags: follow the Project profile. Never move or delete an existing tag.
- No subagents unless the user explicitly asks.

## Gate checklist (run in this order)
1. `.\.venv\Scripts\python.exe -m ruff check .`
2. `.\.venv\Scripts\python.exe -m ruff format --check .`
3. `.\.venv\Scripts\python.exe -m pytest -q` (coverage minimum from profile)
4. `.\.venv\Scripts\pytest.exe -q`
5. `git diff --check`
6. Placeholder scan:
   `git grep -n -i -E "YOUR_USERNAME|Your Name|TODO|FIXME|changeme"`
   must be empty (except documented placeholders in .env.example).
7. Docker build only if docker exists; otherwise list as manual check.
8. Verify every runnable README example and its output/exit code.

## End of task
- Update README, NOTES.md and CHANGELOG with supported claims only.
- Update STATE.md last (max 60 lines): real gate results, last
  implementation commit, remaining unverified work.
- Commit the checkpoint, confirm a clean tree, then STOP. Print:
  `git log --oneline`, `git status`, test count and coverage, anything
  not verified, and MANUAL CHECKS.

## Project profile
- Name: SQL-injection-showroom
- GitHub repository: mr-ransaz/SQL-injection-showroom
- Distribution / Python package: sql-injection-showroom / sqli_showroom
- Author / license: MR Ransaz / MIT 2026
- Version: 0.1.0
- Purpose: a localhost-only educational showroom comparing deliberately
  vulnerable SQL queries with parameterized fixes.
- Stack: Python 3.14, FastAPI, Uvicorn, stdlib sqlite3, vanilla HTML/CSS/JS.
  Development tools: pytest, pytest-cov, httpx, ruff, build.
- Dependency policy: declare runtime dependencies and a dev extra in
  pyproject.toml. Verify Python 3.14 compatibility before choosing versions.
  Pin direct dependencies and explain choices in NOTES.md.
- Layout: src/sqli_showroom/, tests/, scripts/. README.md, NOTES.md,
  STATE.md, CHANGELOG.md and AGENTS.md live in the repository root.
- Coverage minimum: 90% with branch coverage enabled, application Python
  code only. State explicitly that browser JavaScript is not measured.
- Security boundary: intentionally vulnerable SQL is allowed only inside
  the clearly named vulnerable lab module and only against synthetic data.
  Fixed queries and all other database operations must use bound parameters
  wherever values are supplied.
- Local use only: bind the documented launcher to 127.0.0.1, reject
  non-loopback clients at the application boundary, validate Host, disable
  CORS, and never expose the lab through public deployment or tunnels.
  These controls are safeguards, not a sandbox or production security claim.
- No real credentials, external targets, external scanning, telemetry,
  external assets, command execution, or file-reading attack scenarios.
- Use a dedicated resettable SQLite database with synthetic fixtures.
  Never modify databases from other projects.
- Tag policy: create no tags. Never push or create a GitHub repository.
- Initial bootstrap exception: if STATE.md or commit history does not
  exist, record that and initialize them. The initial untracked AGENTS.md
  may be inspected and committed; stop for other unexplained user changes.
- Placeholder scan exception: literal forbidden-pattern examples in
  AGENTS.md and intentional synthetic attack fixtures are not defects.
  Inspect matches; do not modify valid examples merely to silence a scan.
- README verification: execute safe local examples. GitHub push/release
  commands and optional Docker commands are manual checks, not actions
  authorized by documentation.
- Docker is out of scope for version 0.1.0. Skip the conditional Docker
  gate explicitly; do not add Docker files or a Docker CI job.