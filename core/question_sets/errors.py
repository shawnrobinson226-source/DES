# DES — Operator flow errors

"""
Distinct error types for the operator flow foundations.

All subclass ValueError, matching core.axis.bridge.AxisBridgeError.
"""


class OperatorFlowError(ValueError):
    """Base class for operator flow errors."""


class QuestionSetDefinitionError(OperatorFlowError):
    """A question-set definition is invalid."""


class QuestionSetRegistryError(OperatorFlowError):
    """A registry operation is invalid."""


class QuestionSetPathError(OperatorFlowError):
    """An answer path is not a complete path through its question set."""


class ResultValidationError(OperatorFlowError):
    """A resolver result or terminal response fails validation."""
