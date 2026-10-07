#!/usr/bin/env python3
"""Record deterministic, sanitized DES operator-contract loopback fixtures.

The recorder launches the checked-in service twice: once with the exact
operator question set active and once with the default-empty registry. It
never configures or calls AXIS. Random interaction ids are normalized to fixed,
shape-valid UUIDv4 values before serialization.
"""

import hashlib
import http.client
import ipaddress
import json
import os
import platform
import socket
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

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


def _direct_json(method: str, base: str, path: str, body=None) -> tuple:
    """Use a direct socket connection, bypassing all proxy configuration."""
    parsed = urlsplit(base)
    if parsed.scheme != "http" or parsed.hostname != HOST or parsed.port is None:
        raise RuntimeError("recorder target must be an explicit IPv4 loopback URL")
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=2)
    payload = None
    headers = {}
    if body is not None:
        payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        connection.connect()
        peer = connection.sock.getpeername()[0]
        if not ipaddress.ip_address(peer).is_loopback:
            raise RuntimeError(f"recorder connected to a non-loopback peer: {peer}")
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        status = response.status
        result = json.loads(response.read().decode("utf-8"))
        return status, result
    finally:
        connection.close()


def _post(base: str, path: str, body: dict) -> tuple:
    status, response = _direct_json("POST", base, path, body)
    if status != 200:
        raise RuntimeError(f"unexpected HTTP status {status} for {path}")
    return status, response


def _wait_ready(process, base: str) -> None:
    deadline = time.monotonic() + 10
    while True:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"DES launcher exited early: {stdout} {stderr}")
        try:
            status, health = _direct_json("GET", base, "/health")
            if status != 200:
                raise RuntimeError(f"unexpected health HTTP status: {status}")
            if health != {"ok": True, "service": "DES"}:
                raise RuntimeError(f"unexpected health response: {health!r}")
            return
        except OSError:
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
    status, response = _post(base, path, body)
    return {"request": deepcopy(body), "status": status, "response": response}


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


def _assert_runtime_tree_clean() -> None:
    runtime_paths = (
        "api", "core", "models", "security", "storage", "ui", "requirements.txt"
    )
    diff = subprocess.run(
        ["git", "diff", "--quiet", RUNTIME_COMMIT, "--", *runtime_paths],
        cwd=ROOT,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *runtime_paths],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    if diff.returncode != 0 or status.stdout.strip():
        raise RuntimeError(
            "refusing to record because server code differs from des_runtime_commit"
        )


def render_fixture(environ=None) -> str:
    source_env = os.environ if environ is None else environ
    _assert_axis_unset(source_env)
    _assert_runtime_tree_clean()
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
        "des_runtime_commit_role": (
            "server code under test; recorder, fixture, tests, and docs were added later"
        ),
        "server_tree_clean_against_runtime_commit": True,
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
        "normalization_version": "1",
        "canonicalization": "UTF-8 JSON, sorted keys, no insignificant whitespace",
        "hash_scope": (
            "normalized request bodies, HTTP status codes, and response bodies; "
            "provenance fields are excluded"
        ),
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
