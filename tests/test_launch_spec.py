"""Runtime pin, fixed bind, port validation, and real loopback launch proof."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

from ui.run_des import DEFAULT_PORT, HOST, configured_port


ROOT = Path(__file__).resolve().parent.parent
SELECTION = "tri_operator_plumbing_scaffold@0.1.0"


def test_runtime_requirements_are_exactly_pinned():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert requirements == ["fastapi==0.142.2", "uvicorn==0.54.0"]


def test_launcher_host_is_fixed_to_ipv4_loopback():
    assert HOST == "127.0.0.1"
    source = (ROOT / "ui" / "run_des.py").read_text(encoding="utf-8")
    assert "0.0.0.0" not in source
    assert "DES_HOST" not in source


def test_port_default_and_exact_validation():
    assert configured_port({}) == DEFAULT_PORT == 8000
    assert configured_port({"DES_PORT": "1024"}) == 1024
    assert configured_port({"DES_PORT": "65535"}) == 65535
    for bad in ("", " 8000", "8000 ", "0", "1023", "65536", "+8000", "８０００"):
        with pytest.raises(RuntimeError, match="DES_PORT"):
            configured_port({"DES_PORT": bad})


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def _read_json(url: str, *, body=None) -> dict:
    headers = {"Content-Type": "application/json"} if body is not None else {}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    with urlopen(Request(url, data=data, headers=headers), timeout=1) as response:
        return json.loads(response.read().decode("utf-8"))


def _launcher_env(port: int, selection=SELECTION) -> dict:
    env = os.environ.copy()
    env.update({
        "DES_PORT": str(port),
        # A hostile-looking value proves the checked-in launcher has no host
        # environment override.
        "DES_HOST": "0.0.0.0",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    # No AXIS setting or credential is needed to exercise operator questions.
    for name in ("AXIS_BASE_URL", "AXIS_SERVICE_TOKEN", "SAPPHIRE_OPERATOR_ID"):
        env.pop(name, None)
    if selection is None:
        env.pop("DES_OPERATOR_QUESTION_SET", None)
    else:
        env["DES_OPERATOR_QUESTION_SET"] = selection
    return env


def _launch(port: int, selection=SELECTION, *extra_args):
    return subprocess.Popen(
        [sys.executable, "ui/run_des.py", *extra_args],
        cwd=ROOT,
        env=_launcher_env(port, selection),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_health(process, port: int) -> dict:
    base = f"http://{HOST}:{port}"
    deadline = time.monotonic() + 10
    while True:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(f"DES launcher exited early: {stdout} {stderr}")
        try:
            return _read_json(base + "/health")
        except (OSError, URLError):
            if time.monotonic() >= deadline:
                pytest.fail("DES launcher did not accept a loopback connection")
            time.sleep(0.05)


def _stop(process) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _non_loopback_ipv4_addresses() -> set:
    try:
        addresses = socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        return set()
    return {address for address in addresses if not address.startswith("127.")}


def test_checked_in_launcher_binds_loopback_and_serves_operator_contract():
    port = _free_loopback_port()
    # Extra command-line and environment host values are intentionally ignored.
    process = _launch(port, SELECTION, "--host=0.0.0.0")
    base = f"http://{HOST}:{port}"
    try:
        health = _wait_for_health(process, port)
        assert health == {"ok": True, "service": "DES"}

        for address in _non_loopback_ipv4_addresses():
            try:
                with socket.create_connection((address, port), timeout=0.25):
                    pytest.fail(f"DES launch port was reachable on LAN address {address}")
            except OSError:
                pass
        start = _read_json(base + "/interaction/start", body={
            "user_id": "launch-proof-user",
            "session_id": "launch-proof-session",
            "trigger_type": "operator_initiated",
        })
        assert start["done"] is False
        assert start["contract_version"] == "1.0.0"
        assert start["question_set"] == {
            "id": "tri_operator_plumbing_scaffold", "version": "0.1.0"}
        assert start["question"]["id"] == "q1"
    finally:
        _stop(process)


def test_default_empty_registry_fails_closed_over_real_loopback_process():
    port = _free_loopback_port()
    process = _launch(port, None)
    try:
        assert _wait_for_health(process, port) == {"ok": True, "service": "DES"}
        response = _read_json(f"http://{HOST}:{port}/interaction/start", body={
            "user_id": "default-empty-proof-user",
            "session_id": "default-empty-proof-session",
            "trigger_type": "operator_initiated",
        })
        assert response == {
            "error": "Question set unavailable",
            "code": "QUESTION_SET_UNAVAILABLE",
        }
    finally:
        _stop(process)


def test_unknown_selection_exits_nonzero_before_binding_port():
    port = _free_loopback_port()
    process = _launch(port, "unknown@9")
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode != 0
    assert "OperatorBootstrapError" in stderr
    with pytest.raises(OSError):
        socket.create_connection((HOST, port), timeout=0.25)
