# SQL-injection-showroom 0.1.0

By MR Ransaz · MIT 2026 · [Repository](https://github.com/mr-ransaz/SQL-injection-showroom)

**Intentionally vulnerable. Local educational use only. Do not deploy publicly or tunnel it.**

This Python 3.14 lab compares an interpolated SQLite SELECT with a bound query
against dedicated synthetic fixtures. Boolean manipulation broadens public results;
a four-column UNION reads explicitly fake internal records. Local controls are
safeguards, not a sandbox or production security claim.

## PowerShell quick start

From the repository root, with Python 3.14 installed:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m sqli_showroom
```

The terminal stays busy while the server runs. Open
**http://127.0.0.1:8000/** in a browser; stop with Ctrl+C.
If the legacy `py` launcher cannot discover Python, use the verified Python 3.14
installation's executable to create `.venv` instead.

The page runs a normal comparison immediately. Click the apostrophe, boolean,
and UNION presets to compare result tables and SQL. Reset demo data asks for
confirmation and restores the deterministic fixtures.

## Current verification

Both pytest entry points pass 79 tests with 98.05% application Python coverage,
branches enabled. HTML and browser JavaScript are not measured by coverage.
The live subprocess smoke test passes all required HTTP checks:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_test.py
```

HTTP checks verify HTML/assets, the four comparisons and CSRF reset behavior.
They do not verify browser rendering or click flows. Browser checks have not yet
run. Wheel verification, CI configuration and full reference documentation are
part of the next checkpoint.

