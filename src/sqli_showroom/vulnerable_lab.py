"""DELIBERATELY UNSAFE SQL: synthetic localhost education only.

User input becomes SQL syntax here. Never copy this construction into real apps.
Only this module constructs SQL from user values; connection.execute runs one
statement, which does not make it a security sandbox.
"""

import sqlite3
from pathlib import Path

from .database import read_rows


def search_vulnerable(path: Path, query: str) -> tuple[str, list[dict], bool]:
    sql = (
        "SELECT id, name, description, 'public' AS source "
        f"FROM products WHERE name LIKE '%{query}%' ORDER BY id LIMIT 100"
    )
    try:
        return sql, read_rows(path, sql), False
    except (sqlite3.OperationalError, sqlite3.ProgrammingError):
        # Show the teaching SQL, never SQLite errors or filesystem details.
        return sql, [], True
