"""Real HTTP checks against this checkout; never a browser UI test."""

import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError(label)


@contextmanager
def running_server(python: Path, cwd: Path, db: Path, *, checkout: bool):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env["SQLI_SHOWROOM_DB"] = str(db)
    if checkout:
        env["PYTHONPATH"] = str(ROOT / "src")
    else:
        env.pop("PYTHONPATH", None)
    process = subprocess.Popen(
        [str(python), "-m", "sqli_showroom", "--port", str(port)],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=2, trust_env=False
        ) as client:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                require(process.poll() is None, "Server exited before becoming healthy")
                try:
                    response = client.get("/health")
                    if response.status_code == 200 and response.json() == {"status": "ok"}:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Health timeout")
            yield client
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def verify_assets(client: httpx.Client) -> None:
    root = client.get("/")
    require(
        root.status_code == 200 and "text/html" in root.headers["content-type"], "Root HTML"
    )
    require(
        "One input." in root.text and "Intentionally vulnerable" in root.text, "Root content"
    )
    for path, content_type, marker in [
        ("/assets/app.css", "text/css", ".comparison"),
        ("/assets/app.js", "text/javascript", "textContent"),
    ]:
        response = client.get(path)
        require(
            response.status_code == 200
            and content_type in response.headers["content-type"]
            and marker in response.text,
            "Local asset",
        )
    print("PASS root HTML and local CSS/JS assets")


def verify_comparisons(client: httpx.Client) -> None:
    examples = client.get("/api/examples")
    require(examples.status_code == 200, "Presets")
    for index, example in enumerate(examples.json()):
        results = []
        for mode in ("vulnerable", "fixed"):
            response = client.post(f"/api/search/{mode}", json={"query": example["query"]})
            require(response.status_code == 200, "Search HTTP response")
            results.append(response.json())
        vulnerable, fixed = results
        require(fixed["error"] is None, "Fixed query error")
        require(
            "DEMO_ONLY_INTERNAL_MARKER" not in str(fixed["rows"])
            and all(row["source"] == "public" for row in fixed["rows"]),
            "Fixed internal-data isolation",
        )
        if index == 0:
            require(
                len(fixed["rows"]) == 1 and fixed["rows"] == vulnerable["rows"], "Normal search"
            )
        elif index == 1:
            require(len(fixed["rows"]) == 1 and vulnerable["error"] is not None, "Apostrophe")
        elif index == 2:
            require(
                len(vulnerable["rows"]) == 4 and fixed["rows"] == [], "Boolean demonstration"
            )
        elif index == 3:
            internal = [row for row in vulnerable["rows"] if row["source"] == "internal"]
            require(
                len(internal) == 2
                and any(row["name"] == "DEMO_ONLY_INTERNAL_MARKER" for row in internal)
                and fixed["rows"] == [],
                "UNION demonstration",
            )
        print(f"PASS {example['label']}: vulnerable/fixed comparison")
    require(len(examples.json()) == 4, "Exactly four presets")


def verify_reset(client: httpx.Client) -> None:
    response = client.post("/api/reset", json={})
    require(response.status_code == 403, "Missing CSRF rejection")
    config = client.get("/api/config")
    require(config.status_code == 200, "Local config")
    response = client.post(
        "/api/reset",
        json={},
        headers={
            "X-CSRF-Token": config.json()["csrf_token"],
            "Origin": str(client.base_url).rstrip("/"),
        },
    )
    require(response.status_code == 200 and response.json() == {"status": "reset"}, "Reset")
    response = client.post("/api/search/fixed", json={"query": ""})
    require(len(response.json()["rows"]) == 4, "Reset fixtures")
    print("PASS reset: missing CSRF rejected; valid same-origin CSRF accepted")


def main() -> int:
    temporary_root = ROOT / ".tmp"
    try:
        temporary_root.mkdir(parents=True, exist_ok=True)
        with (
            tempfile.TemporaryDirectory(prefix="smoke-", dir=temporary_root) as directory,
            running_server(
                Path(sys.executable),
                ROOT,
                Path(directory) / "data" / "demo.sqlite3",
                checkout=True,
            ) as client,
        ):
            print("PASS live loopback health")
            verify_assets(client)
            verify_comparisons(client)
            verify_reset(client)
        print("PASS child process stopped and temporary demo data removed")
        return 0
    except Exception:
        print("FAIL live smoke check; no exception details or tokens are printed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
