"""Static check: operator-flow modules import no network libraries directly.

core.axis.bridge imports urllib, so importing CLASSIFICATION_VALUES from it
loads urllib transitively. This test covers direct imports only.
"""

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent

OPERATOR_MODULES = [
    "core/contracts.py",
    "core/operator_resolver.py",
    "core/question_sets/__init__.py",
    "core/question_sets/bootstrap.py",
    "core/question_sets/definitions.py",
    "core/question_sets/errors.py",
    "core/question_sets/operator_v1.py",
    "core/question_sets/registry.py",
    "core/question_sets/sentinels.py",
    "core/question_sets/validation.py",
]

FORBIDDEN_ROOTS = {"urllib", "socket", "requests", "httpx", "http"}


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_operator_module_list_is_complete():
    found = {
        path.relative_to(ROOT).as_posix()
        for path in [ROOT / "core" / "contracts.py", ROOT / "core" / "operator_resolver.py"]
        + sorted((ROOT / "core" / "question_sets").glob("*.py"))
    }

    assert found == set(OPERATOR_MODULES)


@pytest.mark.parametrize("module", OPERATOR_MODULES)
def test_no_direct_network_imports(module):
    imports = imported_modules(ROOT / module)

    assert [name for name in imports if name.split(".")[0] in FORBIDDEN_ROOTS] == []


def test_forbidden_import_detection_works(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "import socket\nfrom urllib.request import urlopen\nimport http.client\nimport json\n",
        encoding="utf-8",
    )

    imports = imported_modules(sample)

    assert [name for name in imports if name.split(".")[0] in FORBIDDEN_ROOTS] == [
        "socket", "urllib.request", "http.client",
    ]
