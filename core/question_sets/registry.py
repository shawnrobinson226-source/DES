# DES — Question-set registry

"""
Registry of validated question sets, keyed by (id, version).

- duplicate (id, version) entries are rejected
- at most one entry is active for new starts, and only by explicit activation
- activating a newer entry keeps older versions available for lookup

The production registry OPERATOR_QUESTION_SETS is created empty. Nothing in
DES registers production content into it.
"""

from core.question_sets.definitions import QuestionSet
from core.question_sets.errors import QuestionSetRegistryError


class QuestionSetRegistry:

    def __init__(self):
        self._entries = {}
        self._active_key = None

    def register(self, question_set: QuestionSet) -> None:
        if not isinstance(question_set, QuestionSet):
            raise QuestionSetRegistryError("only QuestionSet instances can be registered")

        key = (question_set.id, question_set.version)
        if key in self._entries:
            raise QuestionSetRegistryError("question set id and version are already registered")

        self._entries[key] = question_set

    def activate(self, set_id: str, version: str) -> None:
        key = _key(set_id, version)
        if key not in self._entries:
            raise QuestionSetRegistryError("cannot activate an unregistered question set")

        self._active_key = key

    def get(self, set_id: str, version: str) -> QuestionSet | None:
        return self._entries.get(_key(set_id, version))

    def get_active(self) -> QuestionSet | None:
        if self._active_key is None:
            return None
        return self._entries[self._active_key]

    def keys(self) -> tuple:
        return tuple(self._entries)


def _key(set_id, version) -> tuple:
    if type(set_id) is not str or type(version) is not str:
        raise QuestionSetRegistryError("question set id and version must be strings")
    return (set_id, version)


OPERATOR_QUESTION_SETS = QuestionSetRegistry()
