"""Explicit startup activation with an inert, fail-closed default."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.question_sets.bootstrap import (
    ACTIVATION_ENV,
    AVAILABLE_QUESTION_SETS,
    OperatorBootstrapError,
    bootstrap_operator_question_sets,
)
from core.question_sets.axis_fracture_classification_v1 import AXIS_FRACTURE_CLASSIFICATION_V1
from core.question_sets.operator_scaffold_v1 import OPERATOR_PLUMBING_SCAFFOLD_V1
from core.question_sets.registry import QuestionSetRegistry
from tests.operator_fixtures import single_question_set


SCAFFOLD_SELECTION = (
    f"{OPERATOR_PLUMBING_SCAFFOLD_V1.id}@{OPERATOR_PLUMBING_SCAFFOLD_V1.version}"
)
PRODUCTION_SELECTION = (
    f"{AXIS_FRACTURE_CLASSIFICATION_V1.id}@{AXIS_FRACTURE_CLASSIFICATION_V1.version}"
)
SELECTION = SCAFFOLD_SELECTION
ROOT = Path(__file__).resolve().parent.parent


def test_available_sets_have_only_explicit_versioned_names():
    assert AVAILABLE_QUESTION_SETS == {
        SCAFFOLD_SELECTION: OPERATOR_PLUMBING_SCAFFOLD_V1,
        PRODUCTION_SELECTION: AXIS_FRACTURE_CLASSIFICATION_V1,
    }


@pytest.mark.parametrize("environ", [{}, {ACTIVATION_ENV: ""}])
def test_default_and_empty_environment_leave_registry_empty(environ):
    registry = QuestionSetRegistry()
    assert bootstrap_operator_question_sets(registry=registry, environ=environ) is None
    assert registry.keys() == ()
    assert registry.get_active() is None


def test_exact_selection_registers_and_activates_scaffold_content():
    registry = QuestionSetRegistry()
    result = bootstrap_operator_question_sets(
        registry=registry, environ={ACTIVATION_ENV: SELECTION})
    assert result == (OPERATOR_PLUMBING_SCAFFOLD_V1.id,
                      OPERATOR_PLUMBING_SCAFFOLD_V1.version)
    assert registry.keys() == (result,)
    assert registry.get_active() is OPERATOR_PLUMBING_SCAFFOLD_V1


def test_exact_selection_registers_and_activates_production_content():
    registry = QuestionSetRegistry()
    result = bootstrap_operator_question_sets(PRODUCTION_SELECTION, registry=registry)
    assert result == (AXIS_FRACTURE_CLASSIFICATION_V1.id,
                      AXIS_FRACTURE_CLASSIFICATION_V1.version)
    assert registry.keys() == (result,)
    assert registry.get_active() is AXIS_FRACTURE_CLASSIFICATION_V1


def test_explicit_argument_overrides_environment_mapping():
    registry = QuestionSetRegistry()
    result = bootstrap_operator_question_sets(
        SELECTION, registry=registry, environ={ACTIVATION_ENV: "unknown@9"})
    assert result == (OPERATOR_PLUMBING_SCAFFOLD_V1.id,
                      OPERATOR_PLUMBING_SCAFFOLD_V1.version)
    assert registry.get_active() is OPERATOR_PLUMBING_SCAFFOLD_V1


@pytest.mark.parametrize("selection", [
    "unknown@1.0.0",
    "tri_operator_plumbing_scaffold",
    "tri_operator_plumbing_scaffold@latest",
    "axis_fracture_classification",
    "axis_fracture_classification@latest",
    f" {SELECTION}",
    f"{SELECTION} ",
    1,
    True,
])
def test_malformed_or_unknown_selection_fails_without_registry_mutation(selection):
    registry = QuestionSetRegistry()
    with pytest.raises(OperatorBootstrapError):
        bootstrap_operator_question_sets(selection, registry=registry)
    assert registry.keys() == ()
    assert registry.get_active() is None


def test_bootstrap_is_idempotent_only_for_the_same_authored_object():
    registry = QuestionSetRegistry()
    assert bootstrap_operator_question_sets(SELECTION, registry=registry)
    assert bootstrap_operator_question_sets(SELECTION, registry=registry)
    assert registry.keys() == ((OPERATOR_PLUMBING_SCAFFOLD_V1.id,
                                OPERATOR_PLUMBING_SCAFFOLD_V1.version),)


def test_conflicting_object_with_same_identity_fails_closed():
    registry = QuestionSetRegistry()
    conflicting = single_question_set(
        set_id=OPERATOR_PLUMBING_SCAFFOLD_V1.id,
        version=OPERATOR_PLUMBING_SCAFFOLD_V1.version,
    )
    registry.register(conflicting)
    with pytest.raises(OperatorBootstrapError, match="different question set"):
        bootstrap_operator_question_sets(SELECTION, registry=registry)
    assert registry.get_active() is None


def launch_import(selection_marker):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if selection_marker is None:
        env.pop(ACTIVATION_ENV, None)
    else:
        env[ACTIVATION_ENV] = selection_marker
    code = (
        "import api.app; "
        "from core.question_sets.registry import OPERATOR_QUESTION_SETS as r; "
        "print(r.keys(), getattr(r.get_active(), 'id', None))"
    )
    return subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env,
        text=True, capture_output=True,
    )


def test_application_import_keeps_default_registry_empty():
    result = launch_import(None)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "() None"


def test_application_import_applies_exact_environment_activation():
    result = launch_import(SELECTION)
    assert result.returncode == 0, result.stderr
    assert "tri_operator_plumbing_scaffold" in result.stdout


def test_application_import_applies_exact_production_activation():
    result = launch_import(PRODUCTION_SELECTION)
    assert result.returncode == 0, result.stderr
    assert "axis_fracture_classification" in result.stdout


def test_application_import_refuses_unknown_environment_activation():
    result = launch_import("unknown@9")
    assert result.returncode != 0
    assert "OperatorBootstrapError" in result.stderr
