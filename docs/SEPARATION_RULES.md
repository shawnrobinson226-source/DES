# DES — Separation Rules (V1)

DES is a decision-friction layer.

## External Systems

AXIS:
- Owns: the five classification names, scoring, truth, execution, and outcomes
- DES holds an allowlisted copy of the class names for boundary validation
- DES may call AXIS only via API, and only through the legacy pricing adapter in
  `core/axis/bridge.py`. No operator-flow path to AXIS exists.
- DES must NOT duplicate AXIS logic

SAPPHIRE:
- Owns: UI, rendering, sessions
- Presents operator confirmation; the Operator authorizes. Callers must retain
  the interaction id (see `docs/DES_OPERATOR_CONTRACT_V1.md`).
- DES returns structured data ONLY
- DES must NOT assume UI behavior

## DES Responsibilities

DES owns:
- trigger detection
- question flow (max 3)
- legacy pricing friction classification and output selection
- validated operator question-set routing
- deterministic operator path resolution

Output families stay separate:

- Legacy pricing terminal output uses `friction_type` and `output_type`.
- Operator terminal output uses `classification` or `reason`.
- Operator output never passes through the pricing payload builder.

DES does NOT:
- store identity models
- track long-term continuity
- infer emotion
- persuade
- override AXIS

## Hard Rules

- No cross-layer logic leakage
- No duplication of AXIS logic
- No UI assumptions
- No hidden steps
- No additional legacy pricing outputs beyond:
  - clarify
  - filter
  - proof

Violation = system failure