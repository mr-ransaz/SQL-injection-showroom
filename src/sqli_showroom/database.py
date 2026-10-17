"""Dedicated synthetic fixtures; each operation owns and closes its connection."""

import sqlite3
from contextlib import closing
from pathlib import Path

PRODUCTS = (
    (1, "Canvas backpack", "Public demo catalogue: a green backpack."),
    (2, "Maker's notebook", "Public demo catalogue: dotted paper."),
    (3, "Desk lamp", "Public demo catalogue: a warm reading light."),
    (4, "Travel mug", "Public demo catalogue: a reusable blue mug."),
)
INTERNAL_RECORDS = (
    (101, "DEMO_ONLY_INTERNAL_MARKER", "SYNTHETIC_NOT_A_SECRET"),
    (102, "FAKE_INTERNAL_NOTE", "FICTIONAL_TRAINING_DATA_ONLY"),
)
SELECT_TEMPLATE = (
    "SELECT id, name, description, 'public' AS source "
    "FROM products WHERE name LIKE ? ORDER BY id LIMIT 100"
)


def _seed(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM products")
    connection.execute("DELETE FROM internal_records")
    connection.executemany(
        "INSERT INTO products(id, name, description) VALUES (?, ?, ?)", PRODUCTS
    )
    connection.executemany(
        "INSERT INTO internal_records(id, label, value) VALUES (?, ?, ?)", INTERNAL_RECORDS
    )


def initialize(path: Path) -> None:
    """Initialize once, refusing to repurpose an unrelated existing database."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type = ?", ("table",))
        names = {row[0] for row in tables}
        if names:
            if names != {"showroom_metadata", "products", "internal_records"}:
                raise ValueError("Database is not a dedicated showroom database.")
            marker = connection.execute(
                "SELECT value FROM showroom_metadata WHERE id = ?", (1,)
            )
            if marker.fetchone() != ("sqli-showroom-synthetic-v1",):
                raise ValueError("Database is not a dedicated showroom database.")
            return
        # Explicit BEGIN includes schema creation and fixtures in one transaction.
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE showroom_metadata(id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute(
            "INSERT INTO showroom_metadata(id, value) VALUES (?, ?)",
            (1, "sqli-showroom-synthetic-v1"),
        )
        connection.execute(
            "CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
            "description TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE internal_records(id INTEGER PRIMARY KEY, label TEXT NOT NULL, "
            "value TEXT NOT NULL)"
        )
        _seed(connection)


def reset(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        _seed(connection)


def read_rows(path: Path, sql: str, parameters: tuple[str, ...] = ()) -> list[dict]:
    """Bound work and result size for this tiny lab; this is not a SQL sandbox."""
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        steps = 0

        def budget() -> int:
            nonlocal steps
            steps += 1
            return int(steps > 100)

        connection.set_progress_handler(budget, 1000)
        return [dict(row) for row in connection.execute(sql, parameters).fetchmany(100)]


def search_fixed(path: Path, query: str) -> tuple[str, list[str], list[dict]]:
    parameters = (f"%{query}%",)
    return SELECT_TEMPLATE, list(parameters), read_rows(path, SELECT_TEMPLATE, parameters)
