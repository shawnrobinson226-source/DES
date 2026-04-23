# DES — Separation Rules (V1)

DES is a decision-friction layer.

## External Systems

AXIS:
- Owns: taxonomy, scoring, truth, outcomes
- DES may ONLY call AXIS via API
- DES must NOT duplicate AXIS logic

SAPPHIRE:
- Owns: UI, rendering, sessions
- DES returns structured data ONLY
- DES must NOT assume UI behavior

## DES Responsibilities

DES owns:
- trigger detection
- question flow (max 3)
- friction classification
- output selection

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
- No additional outputs beyond:
  - clarify
  - filter
  - proof

Violation = system failure