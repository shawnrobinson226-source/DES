"""Test-only question sets for operator-flow tests.

Every id, label and text here is a placeholder. None of it is production
content, and nothing here is registered into the production registry.
"""

from core.axis.bridge import CLASSIFICATION_VALUES
from core.question_sets.definitions import END, UNRESOLVED, Option, Question, QuestionSet, Rule


CLASSES = tuple(sorted(CLASSIFICATION_VALUES))

# Complete paths of the branching test set:
#   q1/opt_a -> q2/opt_d -> q3/opt_f
#   q1/opt_a -> q2/opt_d -> q3/opt_g
#   q1/opt_a -> q2/opt_e
#   q1/opt_b -> q3/opt_f
#   q1/opt_b -> q3/opt_g
#   q1/opt_c                 (explicitly UNRESOLVED)
#   q1/opt_h                 (no rule)
PATH_ADF = (("q1", "opt_a"), ("q2", "opt_d"), ("q3", "opt_f"))
PATH_ADG = (("q1", "opt_a"), ("q2", "opt_d"), ("q3", "opt_g"))
PATH_AE = (("q1", "opt_a"), ("q2", "opt_e"))
PATH_BF = (("q1", "opt_b"), ("q3", "opt_f"))
PATH_BG = (("q1", "opt_b"), ("q3", "opt_g"))
PATH_C = (("q1", "opt_c"),)
PATH_H = (("q1", "opt_h"),)

CLASS_PATHS = (PATH_ADF, PATH_ADG, PATH_AE, PATH_BF, PATH_BG)


def option(option_id, next_step=END, label=None):
    return Option(id=option_id, label=label or f"Test label {option_id}", next=next_step)


def question(question_id, *options, text=None):
    return Question(id=question_id, text=text or f"Test question {question_id}", options=tuple(options))


def branching_questions():
    return (
        question("q1",
                 option("opt_a", "q2"),
                 option("opt_b", "q3"),
                 option("opt_c", END),
                 option("opt_h", END)),
        question("q2",
                 option("opt_d", "q3"),
                 option("opt_e", END)),
        question("q3",
                 option("opt_f", END),
                 option("opt_g", END)),
    )


def branching_rules():
    rules = tuple(Rule(path=path, outcome=cls) for path, cls in zip(CLASS_PATHS, CLASSES))
    return rules + (Rule(path=PATH_C, outcome=UNRESOLVED),)


def branching_set(set_id="test_set", version="test-1"):
    return QuestionSet(
        id=set_id,
        version=version,
        questions=branching_questions(),
        rules=branching_rules(),
    )


def single_question_set(set_id="test_single", version="test-1", rules=None):
    questions = (question("q1", option("opt_x"), option("opt_y")),)
    if rules is None:
        rules = (Rule(path=(("q1", "opt_x"),), outcome=CLASSES[0]),)
    return QuestionSet(id=set_id, version=version, questions=questions, rules=rules)
