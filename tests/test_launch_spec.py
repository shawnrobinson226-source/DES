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
SELECTION = "tri_operator_classification@1.0.0"


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


def test_checked_in_launcher_binds_loopback_and_serves_operator_contract():
    port = _free_loopback_port()
    env = os.environ.copy()
    env.update({
        "DES_PORT": str(port),
        "DES_OPERATOR_QUESTION_SET": SELECTION,
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    process = subprocess.Popen(
        [sys.executable, "ui/run_des.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base = f"http://{HOST}:{port}"
    try:
        deadline = time.monotonic() + 10
        while True:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(f"DES launcher exited early: {stdout} {stderr}")
            try:
                health = _read_json(base + "/health")
                break
            except (OSError, URLError):
                if time.monotonic() >= deadline:
                    pytest.fail("DES launcher did not accept a loopback connection")
                time.sleep(0.05)

        assert health == {"ok": True, "service": "DES", "version": "v1"}
        start = _read_json(base + "/interaction/start", body={
            "user_id": "launch-proof-user",
            "session_id": "launch-proof-session",
            "trigger_type": "operator_initiated",
        })
        assert start["done"] is False
        assert start["contract_version"] == "1.0.0"
        assert start["question_set"] == {
            "id": "tri_operator_classification", "version": "1.0.0"}
        assert start["question"]["id"] == "q1"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
