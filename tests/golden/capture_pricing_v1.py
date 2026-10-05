"""One-time capture of tests/golden/pricing_v1.json.

Run from the repository root:

    python -m tests.golden.capture_pricing_v1

Refuses to run if the recording already exists, or if anything outside
tests/ differs from the pinned source commit.
"""

import json
import subprocess
import sys
from pathlib import Path

from tests.golden.pricing_cases import CASES, SOURCE_COMMIT, run_case


OUTPUT = Path(__file__).with_name("pricing_v1.json")


def _source_matches_pinned_commit() -> bool:
    diff = subprocess.run(
        ["git", "diff", "--quiet", SOURCE_COMMIT, "--", ".", ":(exclude)tests"],
        check=False,
    )
    untracked = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", ":(exclude)tests"],
        capture_output=True,
        text=True,
        check=False,
    )
    return diff.returncode == 0 and untracked.returncode == 0 and untracked.stdout == ""


def main() -> int:
    if OUTPUT.exists():
        print(f"Refusing to overwrite {OUTPUT}")
        return 1

    if not _source_matches_pinned_commit():
        print(f"Source outside tests/ differs from {SOURCE_COMMIT}")
        return 1

    recording = {
        "source_commit": SOURCE_COMMIT,
        "cases": {
            name: {"group": group, "result": run_case(name)}
            for name, (group, _) in CASES.items()
        },
    }

    OUTPUT.write_text(
        json.dumps(recording, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Recorded {len(CASES)} cases to {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
