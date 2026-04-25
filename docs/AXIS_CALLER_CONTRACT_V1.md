# DES AXIS Caller Contract V1

## Status

This is a design contract only.

No AXIS caller exists in DES V1. This document defines the future boundary for
how DES may be allowed to call AXIS after separate approval. It does not add
code, routes, persistence, network clients, or runtime behavior.

## Core Rule

Sapphire displays.
DES decides.
AXIS governs.

DES may prepare an AXIS-ready payload, but AXIS remains the source of truth and
the governing execution layer.

## When A Call Is Allowed

A DES to AXIS call is allowed only after DES has produced a completed result.

Allowed timing:

- after DES classification is complete
- after DES output selection is complete
- after `core/axis_bridge.py` has produced a valid AXIS payload
- after an explicit caller action has requested execution

Disallowed timing:

- never during the trigger phase
- never during question flow
- never while classification is incomplete
- never as an automatic side effect of producing DES output

Execution must be explicit. DES must not auto-call AXIS.

## Who Can Trigger The Call

Only an explicit external actor may request the future AXIS call:

- an operator
- an external system, such as Sapphire
- a manual confirmation layer

DES itself must not decide to execute AXIS automatically.

## What Is Sent

The future caller may send only the payload produced by
`core/axis_bridge.py`.

No additional fields are allowed.
No hidden metadata is allowed.
No identity leakage is allowed.

The payload must contain exactly:

```json
{
  "trigger": "repeat_pricing_visit",
  "classification": "perceptual",
  "next_action": "Review the clarified decision information and choose one next step.",
  "reference": true,
  "stability": 6,
  "impact": 4
}
```

The future caller must not add:

- user identity
- session identity
- raw DES answers
- DES `friction_type`
- DES `output_type`
- DES UI data
- `distortion_class`
- `outcome` unless a later approved contract explicitly changes this rule
- analytics metadata
- continuity state

## How The Call Happens

This section is conceptual only.

If a future implementation is approved, the only allowed AXIS execution target is:

```text
POST /api/v2/execute
```

The request must include:

- the exact bridge payload body
- an `x-operator-id` header supplied by the explicit caller context

Before sending, the future caller must validate:

- the payload came from `core/axis_bridge.py`
- the payload contains only the allowed AXIS fields
- `classification` is one of the AXIS-accepted classification values
- `trigger` and `next_action` are non-empty strings
- `reference` is a boolean
- `stability` is a number from 0 to 10
- `impact` is a number from 0 to 10
- `x-operator-id` is present and non-empty

If validation fails, the caller must fail closed and send nothing.

## Failure Rules

If AXIS rejects a request, DES does nothing.

Required failure behavior:

- no retry loops
- no silent fallback
- no mutation of the payload
- no local execution substitute
- no classification override
- no persistence of failed execution state

The failed request may be surfaced to the explicit caller as a failure, but DES
must not attempt to correct, reinterpret, or resubmit the payload.

## Logging Rules

DES does not store AXIS execution results.

AXIS owns execution logging, analytics, governance history, and any resulting
continuity records.

DES may optionally log that a call was attempted, but such logging must be
minimal and must not include identity, raw answers, hidden metadata, or the AXIS
result body.

Allowed optional DES log facts:

- attempted or not attempted
- validation failed or passed
- safe error code
- timestamp

## Hard Boundaries

DES never overrides AXIS classification.
DES never edits the payload after bridge mapping.
DES never auto-executes.
DES never retries.
DES never stores continuity.
DES never stores AXIS execution results.
DES never sends identity or hidden metadata.
DES never adds fields outside the bridge payload contract.

## Future Implementation Slot

The future implementation slot is:

```text
core/axis_client.py
```

This file is not created yet.

If later approved, `core/axis_client.py` will be the only place in DES where AXIS
calls are allowed. It must wrap the output of `core/axis_bridge.py` and enforce
the full validation contract again immediately before sending.

No API route, classifier, trigger logic, question flow, or output builder may
call AXIS directly.

## Non-Goals

This contract does not allow:

- batching
- async execution
- queue systems
- retry systems
- analytics merging
- persistence
- route wiring
- automatic execution
- identity transfer
- Sapphire implementation work
- AXIS implementation work

## Implementation Checklist For Future Work

Before any future caller is built, the implementing engineer must confirm:

- bridge output validation still passes
- no additional payload fields are added
- `x-operator-id` is required
- failure behavior is fail-closed
- no retries are introduced
- no local result storage is introduced
- no DES decision behavior changes
- no AXIS call occurs without an explicit caller action
