import importlib.util
import subprocess
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def smoke():
    path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_test.py"
    spec = importlib.util.spec_from_file_location("showroom_smoke_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("force_kill", [False, True])
def test_child_stopped_when_a_check_fails(smoke, monkeypatch, tmp_path, force_kill):
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = (
        [subprocess.TimeoutExpired("synthetic-child", 5), 0] if force_kill else [0]
    )
    popen = Mock(return_value=process)
    monkeypatch.setattr(smoke.subprocess, "Popen", popen)
    client = Mock()
    client.get.return_value.status_code = 200
    client.get.return_value.json.return_value = {"status": "ok"}
    monkeypatch.setattr(smoke.httpx, "Client", lambda **kwargs: nullcontext(client))
    with (
        pytest.raises(RuntimeError, match="Synthetic failed check"),
        smoke.running_server(
            Path("synthetic-python"), tmp_path, tmp_path / "demo.sqlite3", checkout=True
        ),
    ):
        raise RuntimeError("Synthetic failed check")
    process.terminate.assert_called_once()
    assert process.kill.call_count == int(force_kill)
    assert process.wait.call_count == 1 + int(force_kill)
    assert popen.call_args.kwargs["env"]["PYTHONPATH"] == str(smoke.ROOT / "src")
    assert popen.call_args.kwargs["cwd"] == tmp_path


def test_failed_smoke_removes_its_temporary_data(smoke, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    created = []

    @contextmanager
    def server(python, cwd, db, *, checkout):
        db.parent.mkdir(parents=True)
        db.write_text("Synthetic temporary fixture", encoding="utf-8")
        created.append(db)
        yield object()

    def fail(client):
        raise RuntimeError("PRIVATE_TEST_MARKER")

    monkeypatch.setattr(smoke, "running_server", server)
    monkeypatch.setattr(smoke, "verify_assets", fail)
    assert smoke.main() == 1
    assert created and not created[0].exists()
    assert list((tmp_path / ".tmp").iterdir()) == []
    output = capsys.readouterr().out
    assert "FAIL live smoke check" in output
    assert "PRIVATE_TEST_MARKER" not in output
