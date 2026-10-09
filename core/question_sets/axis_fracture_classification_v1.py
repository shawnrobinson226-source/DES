# DES — AXIS fracture classification, version 1.0.0

"""Approved production classification policy grounded in AXIS vocabulary.

The operator identifies one published AXIS fracture pattern. DES then applies
the published fracture-to-class mapping. A second pattern, no matching pattern,
or uncertainty ends explicitly unresolved. Continuity is intentionally absent:
the cited AXIS source defines no fracture that maps to it.

Importing this module constructs immutable validated content only. Registration
and activation remain an explicit bootstrap choice.
"""

from core.axis.bridge import CLASSIFICATION_VALUES
from core.question_sets.definitions import END, UNRESOLVED, Option, Question, QuestionSet, Rule


QUESTION_SET_ID = "axis_fracture_classification"
QUESTION_SET_VERSION = "1.0.0"

AXIS_SOURCE_COMMIT = "2c3fd35d36fa0d1eea751f02f1ac38776a3d3a1f"
AXIS_SOURCE_FILE = "lib/patterns/registry.ts"
AXIS_EXECUTION_FILE = "app/session/page.tsx"

# (fracture id, verbatim AXIS userLabel, AXIS class)
FRACTURE_CHOICES = (
    ("control_loss", "Control Grip", "perceptual"),
    ("rejection_sensitivity", "Rejection Alarm", "emotional"),
    ("status_threat", "Status Threat", "narrative"),
    ("uncertainty_intolerance", "Uncertainty Pressure", "perceptual"),
    ("self_worth_dependency", "Worth Attachment", "narrative"),
    ("boundary_violation", "Boundary Drift", "behavioral"),
    ("comparison_spiral", "Comparison Loop", "narrative"),
    ("over_responsibility", "Responsibility Overreach", "behavioral"),
    ("avoidance_loop", "Avoidance Loop", "behavioral"),
    ("shame_spike", "Shame Spike", "emotional"),
)

EXPECTED_FRACTURE_IDS = frozenset({
    "avoidance_loop", "boundary_violation", "comparison_spiral", "control_loss",
    "over_responsibility", "rejection_sensitivity", "self_worth_dependency",
    "shame_spike", "status_threat", "uncertainty_intolerance",
})

if {fracture_id for fracture_id, _, _ in FRACTURE_CHOICES} != EXPECTED_FRACTURE_IDS:
    raise RuntimeError("production fracture ids drifted from the approved AXIS source")
if any(fracture_id in CLASSIFICATION_VALUES or label.lower() in CLASSIFICATION_VALUES
       for fracture_id, label, _ in FRACTURE_CHOICES):
    raise RuntimeError("fracture choices must not expose AXIS class names")
if {classification for _, _, classification in FRACTURE_CHOICES} != (
        CLASSIFICATION_VALUES - {"continuity"}):
    raise RuntimeError("production fracture mapping drifted from the approved AXIS classes")


def _questions() -> tuple:
    fracture_options = tuple(
        Option(id=fracture_id, label=label, next="q2")
        for fracture_id, label, _ in FRACTURE_CHOICES
    )
    return (
        Question(
            id="q1",
            text="Which single AXIS fracture pattern applies?",
            options=fracture_options + (
                Option(id="none_apply", label="None of these patterns applies.", next=END),
                Option(id="unsure", label="I am not sure which pattern applies.", next=END),
            ),
        ),
        Question(
            id="q2",
            text="Is another distinct fracture pattern also present?",
            options=(
                Option(id="no_other_pattern", label="No.", next=END),
                Option(id="another_pattern_present", label="Yes.", next=END),
            ),
        ),
    )


def _rules() -> tuple:
    rules = []
    for fracture_id, _, classification in FRACTURE_CHOICES:
        rules.append(Rule(
            path=(("q1", fracture_id), ("q2", "no_other_pattern")),
            outcome=classification,
        ))
        rules.append(Rule(
            path=(("q1", fracture_id), ("q2", "another_pattern_present")),
            outcome=UNRESOLVED,
        ))
    rules.extend((
        Rule(path=(("q1", "none_apply"),), outcome=UNRESOLVED),
        Rule(path=(("q1", "unsure"),), outcome=UNRESOLVED),
    ))
    return tuple(rules)


AXIS_FRACTURE_CLASSIFICATION_V1 = QuestionSet(
    id=QUESTION_SET_ID,
    version=QUESTION_SET_VERSION,
    questions=_questions(),
    rules=_rules(),
)


__all__ = [
    "AXIS_EXECUTION_FILE",
    "AXIS_FRACTURE_CLASSIFICATION_V1",
    "AXIS_SOURCE_COMMIT",
    "AXIS_SOURCE_FILE",
    "EXPECTED_FRACTURE_IDS",
    "FRACTURE_CHOICES",
    "QUESTION_SET_ID",
    "QUESTION_SET_VERSION",
]
