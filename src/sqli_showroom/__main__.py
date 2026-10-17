"""The supported launcher always binds loopback and ignores proxy headers."""

import argparse

import uvicorn

from .app import create_app, database_path


def port_number(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535.")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description="Local educational SQL injection showroom")
    parser.add_argument("--port", type=port_number, default=8000)
    args = parser.parse_args()
    try:
        path = database_path()
        print(f"Synthetic demo database: {str(path)!r}", flush=True)
        print(f"Open http://127.0.0.1:{args.port}/ (Ctrl+C to stop)", flush=True)
        uvicorn.run(
            create_app(path),
            host="127.0.0.1",
            port=args.port,
            proxy_headers=False,
            access_log=False,
        )
    except Exception:
        print("Startup failed. Check the dedicated database path and local port.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
