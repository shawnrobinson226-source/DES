"""The human-review artifact must remain an exact view of authored content."""

from pathlib import Path

from core.question_sets.operator_v1 import OPERATOR_QUESTION_SET_V1


ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "docs" / "OPERATOR_QUESTION_SET_V1_REVIEW.md"


def _printed_paths(text: str) -> list:
    marker = "## Complete path table"
    section = text.split(marker, 1)[1]
    block = section.split("```text", 1)[1].split("```", 1)[0]
    return [line.strip() for line in block.splitlines() if line.strip()]


def _authored_paths() -> list:
    result = []
    for rule in OPERATOR_QUESTION_SET_V1.rules:
        path = ", ".join(f"{question}={answer}" for question, answer in rule.path)
        outcome = getattr(rule.outcome, "value", rule.outcome)
        result.append(f"{path} -> {outcome}")
    return result


def test_review_document_prints_every_authored_path_in_order():
    text = REVIEW.read_text(encoding="utf-8")
    assert _printed_paths(text) == _authored_paths()
    assert len(_printed_paths(text)) == 46
    assert sum(line.endswith("-> UNRESOLVED") for line in _printed_paths(text)) == 11


def test_review_document_keeps_content_authority_gate_explicit():
    text = REVIEW.read_text(encoding="utf-8")
    assert "draft pending explicit operator approval" in text
    assert "draft operator-facing language, not quoted AXIS definitions" in text
    assert "Approval is not implied" in text
