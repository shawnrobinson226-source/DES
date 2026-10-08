# Operator Plumbing Scaffold 0.1.0 — Approval Record

Status: **approved for scaffold use only**

This document prints the exact mechanics-only content and every complete path
in `tri_operator_plumbing_scaffold@0.1.0`. Importing the scaffold remains inert,
and the DES registry remains empty unless the exact version is selected at
startup.

The implementation was drafted by Codex and approved by the operator on
2026-10-07 for plumbing and browser-trial use only. It is not production
classification policy, makes no semantic claims, and must not be presented as
DES deciding a real classification. The operator selects a test label and DES
echoes it through explicit rules so the system can exercise every mechanism.

## Source audit

AXIS locks the five identifiers `narrative`, `emotional`, `behavioral`,
`perceptual`, and `continuity`. Its checked-in governance prohibits external
systems from renaming, merging, splitting, or reinterpreting those values.
The AXIS repository does not provide an authoritative prose definition for
each of the five identifiers. The explanatory labels below are therefore
draft operator-facing language, not quoted AXIS definitions.

AXIS does contain these existing fracture-to-class mappings:

- `avoidance_loop`, `boundary_violation`, `over_responsibility` -> `behavioral`
- `rejection_sensitivity`, `shame_spike` -> `emotional`
- `comparison_spiral`, `self_worth_dependency`, `status_threat` -> `narrative`
- `control_loss`, `uncertainty_intolerance` -> `perceptual`

No comparable checked-in mapping was found for `continuity`. The operator must
either approve the draft labels as policy or replace them with authoritative
wording before activation.

The scaffold is intentionally balanced at the path level: each of the five class
outcomes has 7 complete paths, and 11 paths end explicitly unresolved. A test
runs all 46 paths through the real operator handler and compares every terminal
result with the table below.

Continuity remains here only to exercise the full allowlist mechanically. Its
label and seven outcomes remain draft test data. Production use of Continuity
stays unresolved until AXIS supplies an authoritative definition.

## Questions and option wording

### q1

Which kind of change is most needed before the next decision or action?

- `perceptual`: Clarify facts, distinctions, or what is being observed.
- `narrative`: Reframe the story, interpretation, or meaning.
- `emotional`: Address emotion, pressure, or felt safety before deciding.
- `behavioral`: Turn an understood decision into a concrete action.
- `continuity`: Restore context, commitment, or follow-through across time.
- `uncertain`: I cannot classify this yet; show every category before resolving.

### q2

Should DES use the category you selected, or should you review all categories?

- `confirm`: Use the category I selected.
- `review_all`: Review every category before resolving.
- `unresolved`: End unresolved; I do not have enough confidence to classify this.

### q3

Choose the category that should be used for the AXIS preview, or end unresolved.

- `choose_perceptual`: Clarify facts, distinctions, or what is being observed.
- `choose_narrative`: Reframe the story, interpretation, or meaning.
- `choose_emotional`: Address emotion, pressure, or felt safety before deciding.
- `choose_behavioral`: Turn an understood decision into a concrete action.
- `choose_continuity`: Restore context, commitment, or follow-through across time.
- `choose_unresolved`: End unresolved; none of these categories is sufficiently supported.

## Complete path table

There are **46 total complete paths**. The **11 unresolved paths are included
in that total**, not additional to it. The other 35 paths resolve to one of the
five locked AXIS class identifiers.

```text
q1=perceptual, q2=confirm -> perceptual
q1=perceptual, q2=unresolved -> UNRESOLVED
q1=perceptual, q2=review_all, q3=choose_perceptual -> perceptual
q1=perceptual, q2=review_all, q3=choose_narrative -> narrative
q1=perceptual, q2=review_all, q3=choose_emotional -> emotional
q1=perceptual, q2=review_all, q3=choose_behavioral -> behavioral
q1=perceptual, q2=review_all, q3=choose_continuity -> continuity
q1=perceptual, q2=review_all, q3=choose_unresolved -> UNRESOLVED
q1=narrative, q2=confirm -> narrative
q1=narrative, q2=unresolved -> UNRESOLVED
q1=narrative, q2=review_all, q3=choose_perceptual -> perceptual
q1=narrative, q2=review_all, q3=choose_narrative -> narrative
q1=narrative, q2=review_all, q3=choose_emotional -> emotional
q1=narrative, q2=review_all, q3=choose_behavioral -> behavioral
q1=narrative, q2=review_all, q3=choose_continuity -> continuity
q1=narrative, q2=review_all, q3=choose_unresolved -> UNRESOLVED
q1=emotional, q2=confirm -> emotional
q1=emotional, q2=unresolved -> UNRESOLVED
q1=emotional, q2=review_all, q3=choose_perceptual -> perceptual
q1=emotional, q2=review_all, q3=choose_narrative -> narrative
q1=emotional, q2=review_all, q3=choose_emotional -> emotional
q1=emotional, q2=review_all, q3=choose_behavioral -> behavioral
q1=emotional, q2=review_all, q3=choose_continuity -> continuity
q1=emotional, q2=review_all, q3=choose_unresolved -> UNRESOLVED
q1=behavioral, q2=confirm -> behavioral
q1=behavioral, q2=unresolved -> UNRESOLVED
q1=behavioral, q2=review_all, q3=choose_perceptual -> perceptual
q1=behavioral, q2=review_all, q3=choose_narrative -> narrative
q1=behavioral, q2=review_all, q3=choose_emotional -> emotional
q1=behavioral, q2=review_all, q3=choose_behavioral -> behavioral
q1=behavioral, q2=review_all, q3=choose_continuity -> continuity
q1=behavioral, q2=review_all, q3=choose_unresolved -> UNRESOLVED
q1=continuity, q2=confirm -> continuity
q1=continuity, q2=unresolved -> UNRESOLVED
q1=continuity, q2=review_all, q3=choose_perceptual -> perceptual
q1=continuity, q2=review_all, q3=choose_narrative -> narrative
q1=continuity, q2=review_all, q3=choose_emotional -> emotional
q1=continuity, q2=review_all, q3=choose_behavioral -> behavioral
q1=continuity, q2=review_all, q3=choose_continuity -> continuity
q1=continuity, q2=review_all, q3=choose_unresolved -> UNRESOLVED
q1=uncertain, q3=choose_perceptual -> perceptual
q1=uncertain, q3=choose_narrative -> narrative
q1=uncertain, q3=choose_emotional -> emotional
q1=uncertain, q3=choose_behavioral -> behavioral
q1=uncertain, q3=choose_continuity -> continuity
q1=uncertain, q3=choose_unresolved -> UNRESOLVED
```

## Approval boundary

The operator approved Option B: scaffold only. This approval permits local
loopback fixture recording and the controlled no-AXIS browser trial. It does
not approve these questions, labels, or paths as production classification
content; does not approve any `next_action`; does not approve a live AXIS
request; and does not authorize a public push.
