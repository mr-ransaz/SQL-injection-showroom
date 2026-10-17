"""Loopback, exact Host/Origin checks, bounded JSON, and sanitized failures."""

from ipaddress import ip_address
from re import fullmatch

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def local_host(host: str) -> bool:
    match = fullmatch(r"(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?", host)
    return match is not None and (match[1] is None or 1 <= int(match[1]) <= 65535)


class LocalBoundary:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self'; style-src 'self'; "
                            b"connect-src 'self'; img-src 'self' data:; object-src 'none'; "
                            b"base-uri 'none'; "
                            b"frame-ancestors 'none'; form-action 'self'",
                        ),
                    ]
                )
            await send(message)

        async def reject(status: int, code: str, message: str) -> None:
            await error_response(status, code, message)(scope, receive, secured_send)

        try:
            address = ip_address(scope["client"][0]) if scope.get("client") else None
        except ValueError:
            address = None
        if address is None or not address.is_loopback:
            await reject(403, "loopback_required", "Only loopback clients are allowed.")
            return
        headers = Headers(scope=scope)
        host = headers.get("host", "")
        if len(headers.getlist("host")) != 1 or not local_host(host):
            await reject(400, "invalid_host", "Use an explicit local Host.")
            return
        if scope["method"] == "POST":
            origin = headers.get("origin")
            if origin is not None and origin != f"http://{host}":
                await reject(403, "invalid_origin", "Origin must match this local server.")
                return
            if (
                headers.get("content-type", "").split(";")[0].strip().lower()
                != "application/json"
            ):
                await reject(415, "json_required", "Use application/json.")
                return
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > 4096:
                    await reject(413, "body_too_large", "JSON body exceeds 4096 bytes.")
                    return
                if not message.get("more_body", False):
                    break

            async def replay() -> dict:
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            request_receive = replay
        else:
            request_receive = receive
        try:
            await self.app(scope, request_receive, secured_send)
        except Exception:
            # No raw exception logging: queries may contain private user input.
            await reject(
                500, "internal_error", "The local operation failed. Restart and retry."
            )
