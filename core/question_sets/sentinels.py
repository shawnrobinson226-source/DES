# DES — Question-set sentinels

"""
Sentinels used in question-set definitions.

Both are enum members, so they are singletons that survive copy and deepcopy,
and neither is a string, so neither can equal an AXIS class name.
"""

from enum import Enum


class Route(Enum):
    END = "END"


class Outcome(Enum):
    UNRESOLVED = "UNRESOLVED"


END = Route.END
UNRESOLVED = Outcome.UNRESOLVED
