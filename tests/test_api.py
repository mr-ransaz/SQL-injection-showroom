import json
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from sqli_showroom import database
from sqli_showroom.app import create_app
from sqli_showroom.models import EXAMPLES


def search(client, mode, query):
    response = client.post(f"/api/search/{mode}", json={"query": query})
    assert response.status_code == 200
    return response.json()


def test_health_and_examples(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/examples").json() == [example.model_dump() for example in EXAMPLES]
    assert client.get("/openapi.json").json()["info"]["version"] == "0.1.0"


def test_normal_search_equivalent(client):
    vulnerable = search(client, "vulnerable", "backpack")
    fixed = search(client, "fixed", "backpack")
    assert vulnerable["rows"] == fixed["rows"]
    assert len(fixed["rows"]) == 1
    assert fixed["rows"][0]["source"] == "public"
    assert vulnerable["error"] is None and fixed["error"] is None


def test_apostrophe_and_controlled_error(client):
    assert search(client, "fixed", "Maker's")["rows"][0]["name"] == "Maker's notebook"
    response = search(client, "vulnerable", "Maker's")
    assert response["rows"] == []
    assert response["error"]["code"] == "invalid_demo_sql"
    assert "Maker's" in response["sql"]
    assert "sqlite" not in response["error"]["message"].lower()


def test_boolean_injection(client):
    payload = EXAMPLES[2].query
    assert len(search(client, "vulnerable", payload)["rows"]) == len(database.PRODUCTS)
    assert search(client, "fixed", payload)["rows"] == []


def test_union_injection(client):
    payload = EXAMPLES[3].query
    rows = search(client, "vulnerable", payload)["rows"]
    assert {row["name"] for row in rows if row["source"] == "internal"} == {
        record[1] for record in database.INTERNAL_RECORDS
    }
    assert len(rows) == len(database.PRODUCTS) + len(database.INTERNAL_RECORDS)
    fixed = search(client, "fixed", payload)
    assert fixed["rows"] == []
    assert "DEMO_ONLY_INTERNAL_MARKER" not in json.dumps(fixed["rows"])


@pytest.mark.parametrize(
    "payload,count", [("'", 1), ("' OR 1=1 -- ", 0), ('<img src=x onerror="alert(1)">', 0)]
)
def test_fixed_payloads_are_data(client, payload, count):
    response = search(client, "fixed", payload)
    assert response["error"] is None
    assert len(response["rows"]) == count
    assert response["sql"] == database.SELECT_TEMPLATE
    assert response["parameters"] == [f"%{payload}%"]


@pytest.mark.parametrize("mode", ["vulnerable", "fixed"])
@pytest.mark.parametrize(
    "query,count", [("", 4), ("%", 4), ("_", 4), ("back_ack", 1), ("\\", 0)]
)
def test_empty_and_like_wildcards(client, mode, query, count):
    assert len(search(client, mode, query)["rows"]) == count


@pytest.mark.parametrize(
    "payload",
    [{"query": "x" * 257}, {"query": "ok", "extra": 1}, {}, {"query": None}, {"query": 1}],
)
def test_request_validation(client, payload):
    response = client.post("/api/search/fixed", json=payload)
    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert "x" * 257 not in response.text


def test_boundary_input_size_and_json(client):
    assert (
        client.post(
            "/api/search/fixed", content="{}", headers={"Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/search/fixed",
            content=b"x" * 4097,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/search/fixed", content="{", headers={"Content-Type": "application/json"}
        ).status_code
        == 422
    )
    assert client.post("/api/search/fixed", json={"query": "x" * 256}).status_code == 200


@pytest.mark.parametrize(
    "origin",
    [
        "null",
        "http://evil.invalid",
        "http://localhost",
        "http://127.0.0.1:9000",
        "https://127.0.0.1",
    ],
)
def test_wrong_origin_rejected(client, origin):
    for endpoint, payload in [("search/fixed", {"query": ""}), ("reset", {})]:
        assert (
            client.post(
                f"/api/{endpoint}", json=payload, headers={"Origin": origin}
            ).status_code
            == 403
        )


def test_correct_origin_and_no_cors(client):
    response = client.post(
        "/api/search/fixed", json={"query": ""}, headers={"Origin": "http://127.0.0.1"}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    response = client.options(
        "/api/reset",
        headers={"Origin": "http://evil.invalid", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 405
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "host",
    [
        "evil.invalid",
        "127.0.0.1.evil.invalid",
        "localhost:bad",
        "localhost:",
        "localhost:0",
        "localhost:65536",
        "localhost/path",
        "user@localhost",
        "[::1",
        "localhost?x",
        "localhost#x",
        "",
    ],
)
def test_invalid_host(client, host):
    response = client.get("/health", headers={"Host": host})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_host"


@pytest.mark.parametrize("host", ["127.0.0.1:8000", "localhost", "[::1]:8000"])
def test_local_host(client, host):
    assert client.get("/health", headers={"Host": host}).status_code == 200


@pytest.mark.parametrize("peer", ["192.0.2.1", "not-an-ip", "::ffff:192.0.2.1"])
def test_nonloopback_and_forwarded_headers(app, peer):
    with TestClient(app, base_url="http://127.0.0.1", client=(peer, 50000)) as outsider:
        response = outsider.get("/health", headers={"X-Forwarded-For": "127.0.0.1"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "loopback_required"


def test_ipv6_loopback(app):
    with TestClient(app, base_url="http://[::1]", client=("::1", 50000)) as client:
        assert client.get("/health").status_code == 200


def test_forwarded_external_address_not_trusted(client):
    assert client.get("/health", headers={"X-Forwarded-For": "192.0.2.1"}).status_code == 200


@pytest.mark.parametrize("token", [None, "invalid-synthetic-test-token", ""])
def test_reset_invalid_csrf(client, token):
    headers = {} if token is None else {"X-CSRF-Token": token}
    response = client.post("/api/reset", json={}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_csrf"


def test_reset_restores_and_repeats(client, db_path):
    token = client.get("/api/config").json()["csrf_token"]
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("DELETE FROM products WHERE id = ?", (1,))
        connection.execute("DELETE FROM internal_records WHERE id = ?", (101,))
    assert len(search(client, "fixed", "")["rows"]) == 3
    for _ in range(2):
        response = client.post(
            "/api/reset", json={}, headers={"Origin": "http://127.0.0.1", "X-CSRF-Token": token}
        )
        assert response.json() == {"status": "reset"}
        assert len(search(client, "fixed", "")["rows"]) == 4
        assert len(search(client, "vulnerable", EXAMPLES[3].query)["rows"]) == 6
    assert (
        client.post(
            "/api/reset", json={"extra": 1}, headers={"X-CSRF-Token": token}
        ).status_code
        == 422
    )


def test_app_instances_do_not_share_tokens(client, tmp_path):
    token = client.get("/api/config").json()["csrf_token"]
    with TestClient(
        create_app(tmp_path / "other.sqlite3"),
        base_url="http://localhost",
        client=("127.0.0.1", 50000),
    ) as other:
        assert (
            other.post("/api/reset", json={}, headers={"X-CSRF-Token": token}).status_code
            == 403
        )


def test_unexpected_errors_are_sanitized(client, monkeypatch):
    def fail(*args):
        raise RuntimeError("PRIVATE_EXCEPTION_MARKER C:/private/path")

    monkeypatch.setattr(database, "search_fixed", fail)
    response = client.post("/api/search/fixed", json={"query": ""})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "PRIVATE_EXCEPTION_MARKER" not in response.text
    assert "Traceback" not in response.text
    assert "C:/private" not in response.text


def test_unknown_route_uses_error_format(client):
    assert client.get("/missing").json()["error"]["code"] == "http_error"
