"""Install the built wheel in a disposable venv and serve UI outside the checkout root."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from smoke_test import ROOT, require, running_server, verify_assets


def run_checked(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    require(result.returncode == 0, "Wheel environment command")


def main() -> int:
    temporary_root = ROOT / ".package-check"
    try:
        temporary_root.mkdir(parents=True, exist_ok=True)
        wheels = list((ROOT / "dist").glob("sql_injection_showroom-0.1.0-*.whl"))
        require(len(wheels) == 1, "Build exactly one 0.1.0 wheel before checking")
        with tempfile.TemporaryDirectory(prefix="wheel-", dir=temporary_root) as directory:
            folder = Path(directory)
            environment = folder / "venv"
            cwd = folder / "outside-root"
            cwd.mkdir()
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            for variable in ("TEMP", "TMP", "TMPDIR"):
                env[variable] = str(folder)
            env["PIP_CACHE_DIR"] = str(ROOT / ".tmp" / "pip-cache")
            run_checked([sys.executable, "-m", "venv", str(environment)], cwd, env)
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run_checked([str(python), "-m", "pip", "install", str(wheels[0])], cwd, env)
            run_checked([str(python), "-m", "pip", "check"], cwd, env)
            run_checked(
                [
                    str(python),
                    "-c",
                    "from pathlib import Path; import sys, sqli_showroom; "
                    "assert Path(sqli_showroom.__file__).is_relative_to(Path(sys.prefix)); "
                    "assert sqli_showroom.__version__ == '0.1.0'",
                ],
                cwd,
                env,
            )
            print(
                "PASS wheel installed in isolated Python 3.14 venv; "
                "pip check; installed imports"
            )
            with running_server(
                python, cwd, folder / "isolated-data" / "wheel.sqlite3", checkout=False
            ) as client:
                require(client.get("/health").json() == {"status": "ok"}, "Wheel health")
                print("PASS installed wheel health from outside repository root")
                verify_assets(client)
        print("PASS wheel server stopped and disposable venv/database removed")
        return 0
    except Exception:
        print("FAIL wheel installation/UI/assets/health check; build distributions first")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
