import argparse
import sqlite3
from contextlib import closing

import pytest

from sqli_showroom import __main__ as cli
from sqli_showroom import database
from sqli_showroom.app import database_path


def test_missing_parent_and_repeat_initialization(db_path):
    assert not db_path.parent.exists()
    database.initialize(db_path)
    database.initialize(db_path)
    assert len(database.search_fixed(db_path.resolve(), "")[2]) == 4


def test_initialize_preserves_existing_data(db_path):
    database.initialize(db_path)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("DELETE FROM products WHERE id = ?", (1,))
    database.initialize(db_path)
    assert len(database.search_fixed(db_path.resolve(), "")[2]) == 3


def test_unrelated_database_refused(db_path):
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("CREATE TABLE unrelated(id INTEGER)")
    with pytest.raises(ValueError, match="not a dedicated"):
        database.initialize(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute("SELECT name FROM sqlite_master").fetchall() == [
            ("unrelated",)
        ]


def test_invalid_metadata_refused(db_path):
    database.initialize(db_path)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("UPDATE showroom_metadata SET value = ?", ("wrong",))
    with pytest.raises(ValueError, match="not a dedicated"):
        database.initialize(db_path)


def test_initialization_rolls_back_schema_and_seed(db_path, monkeypatch):
    original = database._seed

    def fail(connection):
        original(connection)
        raise RuntimeError("Synthetic transaction failure")

    with monkeypatch.context() as context:
        context.setattr(database, "_seed", fail)
        with pytest.raises(RuntimeError, match="Synthetic transaction"):
            database.initialize(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute("SELECT name FROM sqlite_master").fetchall() == []
    database.initialize(db_path)
    assert len(database.search_fixed(db_path.resolve(), "")[2]) == 4


def test_reset_rolls_back_on_failure(db_path, monkeypatch):
    database.initialize(db_path)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("DELETE FROM products WHERE id = ?", (1,))
    original = database._seed

    def fail(connection):
        original(connection)
        raise RuntimeError("Synthetic transaction failure")

    monkeypatch.setattr(database, "_seed", fail)
    with pytest.raises(RuntimeError, match="Synthetic transaction"):
        database.reset(db_path)
    assert len(database.search_fixed(db_path.resolve(), "")[2]) == 3


def test_fixed_passes_bound_parameters(db_path, monkeypatch):
    calls = []

    def capture(path, sql, parameters):
        calls.append((path, sql, parameters))
        return []

    monkeypatch.setattr(database, "read_rows", capture)
    query = "Maker's%_\\"
    database.search_fixed(db_path, query)
    assert calls == [(db_path, database.SELECT_TEMPLATE, (f"%{query}%",))]
    assert query not in calls[0][1]


def test_query_budget_and_row_limit(db_path):
    database.initialize(db_path)
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        database.read_rows(
            db_path.resolve(),
            "WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL "
            "SELECT x+1 FROM n WHERE x<1000000) SELECT sum(x) FROM n",
        )
    rows = database.read_rows(
        db_path.resolve(),
        "WITH RECURSIVE n(id) AS (VALUES(1) UNION ALL "
        "SELECT id+1 FROM n WHERE id<200) SELECT id FROM n",
    )
    assert len(rows) == 100


def test_configured_and_default_path(monkeypatch, tmp_path):
    monkeypatch.delenv("SQLI_SHOWROOM_DB", raising=False)
    assert database_path().name == "showroom.sqlite3"
    monkeypatch.setenv("SQLI_SHOWROOM_DB", str(tmp_path / "explicit.sqlite3"))
    assert database_path() == tmp_path / "explicit.sqlite3"


@pytest.mark.parametrize("port", ["0", "65536", "-1"])
def test_invalid_port_range(port):
    with pytest.raises(argparse.ArgumentTypeError):
        cli.port_number(port)


@pytest.mark.parametrize("args,port", [([], 8000), (["--port", "8123"], 8123)])
def test_cli_local_defaults(monkeypatch, capsys, args, port):
    calls = []
    monkeypatch.setattr("sys.argv", ["sqli_showroom", *args])
    monkeypatch.setattr(cli, "create_app", lambda path: object())
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    assert cli.main() == 0
    assert calls == [
        {"host": "127.0.0.1", "port": port, "proxy_headers": False, "access_log": False}
    ]
    assert repr(str(database_path())) in capsys.readouterr().out


def test_cli_startup_error_sanitized(monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE_MARKER")

    monkeypatch.setattr("sys.argv", ["sqli_showroom"])
    monkeypatch.setattr(cli, "create_app", lambda path: object())
    monkeypatch.setattr(cli.uvicorn, "run", fail)
    assert cli.main() == 1
    assert "PRIVATE_MARKER" not in capsys.readouterr().out


@pytest.mark.parametrize("args", [["--host", "0.0.0.0"], ["--port", "not-a-number"]])
def test_cli_rejects_unsupported_arguments(monkeypatch, args):
    monkeypatch.setattr("sys.argv", ["sqli_showroom", *args])
    with pytest.raises(SystemExit) as raised:
        cli.main()
    assert raised.value.code == 2
