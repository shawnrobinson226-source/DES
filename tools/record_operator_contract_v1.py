#!/usr/bin/env python3
"""Record deterministic, sanitized DES operator-contract loopback fixtures.

The recorder launches the checked-in service twice: once with the exact
operator question set active and once with the default-empty registry. It
never configures or calls AXIS. Random interaction ids are normalized to fixed,
shape-valid UUIDv4 values before serialization.
"""

import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import fastapi
import uvicorn


ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
SELECTION = "tri_operator_classification@1.0.0"
CONTRACT_VERSION = "1.0.0"
QUESTION_SET = {"id": "tri_operator_classification", "version": "1.0.0"}
RUNTIME_COMMIT = "d67ad44f9b5c87583cd7e4644f63b297951b1b5d"
RECORDING_DATE = "2026-10-06"
RECORDER_IDENTITY = "DES tools/record_operator_contract_v1.py"
FORBIDDEN_AXIS_ENV = (
    "AXIS_BASE_URL",
    "AXIS_SERVICE_TOKEN",
    "SAPPHIRE_OPERATOR_ID",
)

NORMALIZED_IDS = {
    "full_length_resolved": "11111111-1111-4111-8111-111111111111",
    "short_resolved": "22222222-2222-4222-8222-222222222222",
    "explicit_unresolved": "33333333-3333-4333-8333-333333333333",
    "invalid_option": "44444444-4444-4444-8444-444444444444",
    "out_of_order": "55555555-5555-4555-8555-555555555555",
    "interaction_closed": "66666666-6666-4666-8666-666666666666",
    "interaction_not_found": "00000000-0000-4000-8000-000000000000",
}


def _assert_axis_unset(environ) -> None:
    present = [name for name in FORBIDDEN_AXIS_ENV if name in environ]
    if present:
        raise RuntimeError(
            "refusing to record while AXIS settings are present: " + ", ".join(present)
        )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def _post(base: str, path: str, body: dict) -> dict:
    request = Request(
        base + path,
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=2) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status {response.status} for {path}")
        return json.loads(response.read().decode("utf-8"))


def _wait_ready(process, base: str) -> None:
    deadline = time.monotonic() + 10
    while True:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"DES launcher exited early: {stdout} {stderr}")
        try:
            with urlopen(base + "/health", timeout=1) as response:
                health = json.loads(response.read().decode("utf-8"))
            if health != {"ok": True, "service": "DES"}:
                raise RuntimeError(f"unexpected health response: {health!r}")
            return
        except (OSError, URLError):
            if time.monotonic() >= deadline:
                raise RuntimeError("DES launcher did not become ready on loopback")
            time.sleep(0.05)


def _launch(selection) -> tuple:
    port = _free_port()
    env = os.environ.copy()
    for name in FORBIDDEN_AXIS_ENV:
        env.pop(name, None)
    env.update({"DES_PORT": str(port), "PYTHONDONTWRITEBYTECODE": "1"})
    if selection is None:
        env.pop("DES_OPERATOR_QUESTION_SET", None)
    else:
        env["DES_OPERATOR_QUESTION_SET"] = selection
    process = subprocess.Popen(
        [sys.executable, "ui/run_des.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base = f"http://{HOST}:{port}"
    _wait_ready(process, base)
    return process, base


def _stop(process) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _exchange(base: str, path: str, body: dict) -> dict:
    return {"request": deepcopy(body), "response": _post(base, path, body)}


def _start(base: str, scenario: str) -> dict:
    return _exchange(base, "/interaction/start", {
        "user_id": f"fixture-{scenario}-user",
        "session_id": f"fixture-{scenario}-session",
        "trigger_type": "operator_initiated",
    })


def _answer(base: str, interaction_id: str, question_id: str, answer: str) -> dict:
    return _exchange(base, "/interaction/answer", {
        "interaction_id": interaction_id,
        "question_id": question_id,
        "answer": answer,
    })


def _record_active() -> dict:
    process, base = _launch(SELECTION)
    try:
        recorded = {}

        steps = [_start(base, "full-resolved")]
        interaction_id = steps[0]["response"]["interaction_id"]
        steps.append(_answer(base, interaction_id, "q1", "behavioral"))
        steps.append(_answer(base, interaction_id, "q2", "review_all"))
        steps.append(_answer(base, interaction_id, "q3", "choose_perceptual"))
        recorded["full_length_resolved"] = steps

        steps = [_start(base, "short-resolved")]
        interaction_id = steps[0]["response"]["interaction_id"]
        steps.append(_answer(base, interaction_id, "q1", "uncertain"))
        steps.append(_answer(base, interaction_id, "q3", "choose_continuity"))
        recorded["short_resolved"] = steps

        steps = [_start(base, "explicit-unresolved")]
        interaction_id = steps[0]["response"]["interaction_id"]
        steps.append(_answer(base, interaction_id, "q1", "uncertain"))
        steps.append(_answer(base, interaction_id, "q3", "choose_unresolved"))
        recorded["explicit_unresolved"] = steps

        steps = [_start(base, "invalid-option")]
        interaction_id = steps[0]["response"]["interaction_id"]
        steps.append(_answer(base, interaction_id, "q1", "not-an-option"))
        recorded["invalid_option"] = steps

        steps = [_start(base, "out-of-order")]
        interaction_id = steps[0]["response"]["interaction_id"]
        steps.append(_answer(base, interaction_id, "q2", "confirm"))
        recorded["out_of_order"] = steps

        steps = [_start(base, "interaction-closed")]
        interaction_id = steps[0]["response"]["interaction_id"]
        steps.append(_answer(base, interaction_id, "q1", "behavioral"))
        steps.append(_answer(base, interaction_id, "q2", "confirm"))
        steps.append(_answer(base, interaction_id, "q2", "confirm"))
        recorded["interaction_closed"] = steps

        missing_id = NORMALIZED_IDS["interaction_not_found"]
        recorded["interaction_not_found"] = [
            _answer(base, missing_id, "q1", "behavioral")
        ]
        return recorded
    finally:
        _stop(process)


def _record_default_empty() -> list:
    process, base = _launch(None)
    try:
        return [_start(base, "default-empty")]
    finally:
        _stop(process)


def _replace_string(value, old: str, new: str):
    if isinstance(value, dict):
        return {key: _replace_string(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_string(item, old, new) for item in value]
    return new if value == old else value


def _normalize(recorded: dict) -> dict:
    normalized = deepcopy(recorded)
    for scenario, replacement in NORMALIZED_IDS.items():
        if scenario == "interaction_not_found":
            continue
        steps = normalized[scenario]
        raw_id = steps[0]["response"]["interaction_id"]
        normalized[scenario] = _replace_string(steps, raw_id, replacement)
    return normalized


def render_fixture(environ=None) -> str:
    source_env = os.environ if environ is None else environ
    _assert_axis_unset(source_env)
    wire = _normalize(_record_active())
    wire["default_empty"] = _record_default_empty()
    canonical_wire = json.dumps(
        wire, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    fixture = {
        "contract_version": CONTRACT_VERSION,
        "source": "recorded DES loopback plus labeled contract-derived cases",
        "question_set": QUESTION_SET,
        "des_runtime_commit": RUNTIME_COMMIT,
        "recording_date": RECORDING_DATE,
        "runtime": {
            "python": platform.python_version(),
            "fastapi": fastapi.__version__,
            "uvicorn": uvicorn.__version__,
        },
        "recorder": RECORDER_IDENTITY,
        "normalizations": [
            "synthetic fixture user_id and session_id values",
            "interaction_id replaced per scenario with a fixed valid UUIDv4",
            "HTTP Date and Server headers omitted",
            "ephemeral loopback port omitted",
            "no local filesystem path recorded",
        ],
        "normalized_wire_sha256": hashlib.sha256(canonical_wire).hexdigest(),
        "recorded_wire": wire,
        "contract_derived": {
            "result_validation_failed": {
                "error": "Result validation failed",
                "code": "RESULT_VALIDATION_FAILED",
            },
            "no_matching_rule": {
                "status": "unresolved",
                "reason": "NO_MATCHING_RULE",
                "done": True,
                "contract_version": CONTRACT_VERSION,
                "question_set": QUESTION_SET,
            },
        },
    }
    return json.dumps(fixture, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    sys.stdout.write(render_fixture())


if __name__ == "__main__":
    main()
