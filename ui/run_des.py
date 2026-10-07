# DES — loopback-only local launcher

"""Run the DES FastAPI application on IPv4 loopback only."""

import os
import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def configured_port(environ=None) -> int:
    source = os.environ if environ is None else environ
    raw = source.get("DES_PORT", str(DEFAULT_PORT))
    if type(raw) is not str or not raw.isascii() or not raw.isdigit():
        raise RuntimeError("DES_PORT must be an integer from 1024 through 65535")
    port = int(raw)
    if not 1024 <= port <= 65535:
        raise RuntimeError("DES_PORT must be an integer from 1024 through 65535")
    return port


def main() -> None:
    uvicorn.run(
        "api.app:app",
        host=HOST,
        port=configured_port(),
        access_log=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
