import os
import subprocess
import sys


def test_launcher_sanitizes_initialization_failure(tmp_path):
    parent = tmp_path / "existing-file"
    parent.write_text("Synthetic non-directory fixture", encoding="utf-8")
    env = os.environ.copy()
    env["SQLI_SHOWROOM_DB"] = str(parent / "demo.sqlite3")
    result = subprocess.run(
        [sys.executable, "-m", "sqli_showroom"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "Traceback" not in output
    assert "FileExistsError" not in output
    assert "Startup failed." in output
