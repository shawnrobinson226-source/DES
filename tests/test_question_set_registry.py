import pytest

from core.question_sets import registry as registry_module
from core.question_sets.errors import QuestionSetRegistryError
from core.question_sets.registry import OPERATOR_QUESTION_SETS, QuestionSetRegistry
from tests.operator_fixtures import branching_set, single_question_set


def production_is_empty():
    return OPERATOR_QUESTION_SETS.keys() == () and OPERATOR_QUESTION_SETS.get_active() is None


@pytest.fixture(autouse=True)
def production_registry_stays_empty():
    assert production_is_empty()
    yield
    assert production_is_empty()


@pytest.fixture
def restored_production_registry():
    entries = dict(OPERATOR_QUESTION_SETS._entries)
    active_key = OPERATOR_QUESTION_SETS._active_key
    yield OPERATOR_QUESTION_SETS
    OPERATOR_QUESTION_SETS._entries = entries
    OPERATOR_QUESTION_SETS._active_key = active_key


def test_production_registry_is_empty_by_default():
    assert registry_module.OPERATOR_QUESTION_SETS is OPERATOR_QUESTION_SETS
    assert OPERATOR_QUESTION_SETS.keys() == ()
    assert OPERATOR_QUESTION_SETS.get_active() is None


def test_production_registry_fixture_restores_state(restored_production_registry):
    restored_production_registry.register(single_question_set())
    restored_production_registry.activate("test_single", "test-1")

    assert restored_production_registry.get_active() is not None


def test_new_registry_is_empty():
    registry = QuestionSetRegistry()

    assert registry.keys() == ()
    assert registry.get_active() is None
    assert registry.get("test_set", "test-1") is None


def test_register_does_not_activate():
    registry = QuestionSetRegistry()
    registry.register(branching_set())

    assert registry.get_active() is None
    assert registry.get("test_set", "test-1") is not None


def test_explicit_activation():
    registry = QuestionSetRegistry()
    question_set = branching_set()
    registry.register(question_set)
    registry.activate("test_set", "test-1")

    assert registry.get_active() is question_set


def test_activating_new_version_retains_old_version():
    registry = QuestionSetRegistry()
    old = branching_set(version="test-1")
    new = branching_set(version="test-2")
    registry.register(old)
    registry.register(new)

    registry.activate("test_set", "test-1")
    registry.activate("test_set", "test-2")

    assert registry.get_active() is new
    assert registry.get("test_set", "test-1") is old
    assert registry.get("test_set", "test-2") is new
    assert registry.keys() == (("test_set", "test-1"), ("test_set", "test-2"))


def test_only_one_entry_is_active():
    registry = QuestionSetRegistry()
    registry.register(branching_set())
    registry.register(single_question_set())

    registry.activate("test_set", "test-1")
    registry.activate("test_single", "test-1")

    assert registry.get_active().id == "test_single"


def test_duplicate_id_and_version_is_rejected():
    registry = QuestionSetRegistry()
    registry.register(branching_set())

    with pytest.raises(QuestionSetRegistryError, match="already registered"):
        registry.register(branching_set())


def test_activating_unregistered_entry_is_rejected():
    registry = QuestionSetRegistry()

    with pytest.raises(QuestionSetRegistryError, match="unregistered"):
        registry.activate("test_set", "test-1")

    assert registry.get_active() is None


def test_failed_activation_keeps_previous_active_entry():
    registry = QuestionSetRegistry()
    question_set = branching_set()
    registry.register(question_set)
    registry.activate("test_set", "test-1")

    with pytest.raises(QuestionSetRegistryError):
        registry.activate("test_set", "test-9")

    assert registry.get_active() is question_set


def test_only_question_sets_can_be_registered():
    registry = QuestionSetRegistry()

    with pytest.raises(QuestionSetRegistryError, match="QuestionSet"):
        registry.register({"id": "test_set", "version": "test-1"})


@pytest.mark.parametrize("set_id, version", [(1, "test-1"), ("test_set", 1), ("test_set", True), (None, None)])
def test_lookup_keys_must_be_strings(set_id, version):
    registry = QuestionSetRegistry()

    with pytest.raises(QuestionSetRegistryError, match="strings"):
        registry.get(set_id, version)
    with pytest.raises(QuestionSetRegistryError, match="strings"):
        registry.activate(set_id, version)
