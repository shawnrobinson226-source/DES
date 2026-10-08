# DES — Non-production operator plumbing scaffold, version 0.1.0

"""Mechanics-only questions and exact path rules for integration trials.

Importing this module constructs validated immutable content but does not
register or activate it. This set makes no semantic or production
classification claim: the operator selects labels and the rules echo that
selection only to exercise routing, provenance, terminal outcomes, and caller
failures. There is no inferred or default classification, and every complete
path has an explicit rule, including unresolved exits.
"""

from core.axis.bridge import CLASSIFICATION_VALUES
from core.question_sets.definitions import END, UNRESOLVED, Option, Question, QuestionSet, Rule


QUESTION_SET_ID = "tri_operator_plumbing_scaffold"
QUESTION_SET_VERSION = "0.1.0"

# The ids exercise AXIS's exact allowlist mechanically. These labels are draft
# test language, not AXIS definitions and not production classification policy.
CLASS_CHOICES = (
    ("perceptual", "Clarify facts, distinctions, or what is being observed."),
    ("narrative", "Reframe the story, interpretation, or meaning."),
    ("emotional", "Address emotion, pressure, or felt safety before deciding."),
    ("behavioral", "Turn an understood decision into a concrete action."),
    ("continuity", "Restore context, commitment, or follow-through across time."),
)

if {name for name, _ in CLASS_CHOICES} != CLASSIFICATION_VALUES:
    raise RuntimeError("operator question choices do not match the AXIS classification allowlist")


def _questions() -> tuple:
    initial = tuple(
        Option(id=classification, label=label, next="q2")
        for classification, label in CLASS_CHOICES
    ) + (
        Option(
            id="uncertain",
            label="I cannot classify this yet; show every category before resolving.",
            next="q3",
        ),
    )

    review = (
        Option(id="confirm", label="Use the category I selected.", next=END),
        Option(id="review_all", label="Review every category before resolving.", next="q3"),
        Option(
            id="unresolved",
            label="End unresolved; I do not have enough confidence to classify this.",
            next=END,
        ),
    )

    final = tuple(
        Option(id=f"choose_{classification}", label=label, next=END)
        for classification, label in CLASS_CHOICES
    ) + (
        Option(
            id="choose_unresolved",
            label="End unresolved; none of these categories is sufficiently supported.",
            next=END,
        ),
    )

    return (
        Question(
            id="q1",
            text="Which kind of change is most needed before the next decision or action?",
            options=initial,
        ),
        Question(
            id="q2",
            text="Should DES use the category you selected, or should you review all categories?",
            options=review,
        ),
        Question(
            id="q3",
            text="Choose the category that should be used for the AXIS preview, or end unresolved.",
            options=final,
        ),
    )


def _rules() -> tuple:
    rules = []

    # A confident initial choice is confirmed, explicitly abandoned, or
    # replaced by a final category selected from the complete list.
    for initial_class, _ in CLASS_CHOICES:
        rules.append(Rule(
            path=(("q1", initial_class), ("q2", "confirm")),
            outcome=initial_class,
        ))
        rules.append(Rule(
            path=(("q1", initial_class), ("q2", "unresolved")),
            outcome=UNRESOLVED,
        ))
        for final_class, _ in CLASS_CHOICES:
            rules.append(Rule(
                path=(("q1", initial_class), ("q2", "review_all"),
                      ("q3", f"choose_{final_class}")),
                outcome=final_class,
            ))
        rules.append(Rule(
            path=(("q1", initial_class), ("q2", "review_all"),
                  ("q3", "choose_unresolved")),
            outcome=UNRESOLVED,
        ))

    # An uncertain initial answer goes directly to the complete category list.
    for final_class, _ in CLASS_CHOICES:
        rules.append(Rule(
            path=(("q1", "uncertain"), ("q3", f"choose_{final_class}")),
            outcome=final_class,
        ))
    rules.append(Rule(
        path=(("q1", "uncertain"), ("q3", "choose_unresolved")),
        outcome=UNRESOLVED,
    ))

    return tuple(rules)


OPERATOR_PLUMBING_SCAFFOLD_V1 = QuestionSet(
    id=QUESTION_SET_ID,
    version=QUESTION_SET_VERSION,
    questions=_questions(),
    rules=_rules(),
)


__all__ = [
    "CLASS_CHOICES",
    "OPERATOR_PLUMBING_SCAFFOLD_V1",
    "QUESTION_SET_ID",
    "QUESTION_SET_VERSION",
]
