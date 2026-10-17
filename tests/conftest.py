import pytest
from fastapi.testclient import TestClient

from sqli_showroom.app import create_app


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "new-parent" / "demo.sqlite3"


@pytest.fixture
def app(db_path):
    return create_app(db_path)


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        yield client
