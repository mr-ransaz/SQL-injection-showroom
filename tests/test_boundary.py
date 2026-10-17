import asyncio

import pytest

from sqli_showroom.boundary import LocalBoundary


def exchange(*, messages, client=("127.0.0.1", 50000), headers=None):
    sent = []
    consumed = iter(messages)

    async def downstream(scope, receive, send):
        body = await receive()
        assert body["body"] == b'{"query":"ok"}'
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return next(consumed)

    async def send(message):
        sent.append(message)

    asyncio.run(
        LocalBoundary(downstream)(
            {
                "type": "http",
                "method": "POST",
                "client": client,
                "headers": headers
                if headers is not None
                else [(b"host", b"localhost"), (b"content-type", b"application/json")],
            },
            receive,
            send,
        )
    )
    return sent


def test_chunked_body_is_bounded_and_reassembled():
    sent = exchange(
        messages=[
            {"type": "http.request", "body": b'{"query":', "more_body": True},
            {"type": "http.request", "body": b'"ok"}', "more_body": False},
        ]
    )
    assert sent[0]["status"] == 200


def test_chunked_limit_cannot_be_bypassed():
    sent = exchange(
        messages=[
            {"type": "http.request", "body": b"x" * 3000, "more_body": True},
            {"type": "http.request", "body": b"x" * 1097, "more_body": False},
        ]
    )
    assert sent[0]["status"] == 413


def test_disconnected_client_stops_without_search():
    assert exchange(messages=[{"type": "http.disconnect"}]) == []


def test_missing_peer_rejected():
    assert exchange(messages=[], client=None)[0]["status"] == 403


@pytest.mark.parametrize(
    "headers",
    [
        [(b"content-type", b"application/json")],
        [(b"host", b"localhost"), (b"host", b"evil.invalid")],
    ],
)
def test_missing_and_duplicate_host_rejected(headers):
    assert exchange(messages=[], headers=headers)[0]["status"] == 400
