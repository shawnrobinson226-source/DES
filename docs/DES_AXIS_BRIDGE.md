# DES AXIS Bridge

## Purpose

The DES AXIS bridge is an adapter layer. It converts completed DES decision
friction output into a valid AXIS execution request.

It translates interfaces, enforces the canonical mapping, and passes data
forward. It does not add decision logic, infer meaning, mutate DES behavior,
redefine AXIS taxonomy, or change Sapphire routing.

## System Roles

Sapphire displays and routes.
DES decides decision friction.
AXIS governs execution and continuity.

## Adapter Location

The adapter lives at:

```text
core/axis/bridge.py
```

The local runner lives at:

```text
ui/des_axis_flow.py
```

Run it with:

```text
python -m ui.des_axis_flow
```

The runner uses `AXIS_BASE_URL` from the environment and prints the structured
adapter response. It does not hardcode secrets.

## Mapping Table

The canonical DES to AXIS classification mapping lives in one place only:
`core/axis/bridge.py`.

| DES friction_type | AXIS classification |
| --- | --- |
| `information_gap` | `perceptual` |
| `fit_uncertainty` | `behavioral` |
| `trust_deficit` | `narrative` |

Unknown friction types fail closed. There is no fallback classification.

## Request Flow

1. DES produces completed output.
2. An explicit caller provides the raw trigger text and `operator_id`.
3. The adapter maps DES `friction_type` to AXIS `classification`.
4. The adapter builds the AXIS execute payload.
5. The adapter posts to `AXIS_BASE_URL + /api/v2/execute`.
6. The request includes the `x-operator-id` header.
7. The adapter returns either a structured success or structured error.

The AXIS execute payload contains exactly:

```json
{
  "trigger": "original user input",
  "classification": "perceptual",
  "next_action": "Review the clarified decision information and choose one next step.",
  "reference": true,
  "stability": 6,
  "impact": 4
}
```

The adapter never includes `outcome`. Outcome is not known at bridge time.

## Error Handling

Invalid DES output fails closed before any AXIS call.

Missing `operator_id` fails before any AXIS call.

If AXIS rejects the request, the adapter returns a structured `AXIS_REJECTED`
error. It does not retry, mutate the payload, change classification, or silently
fallback.

## Test Instructions

Run the existing DES tests:

```text
python -m tests.test_flow
python -m tests.test_security
python -m tests.test_classifier
python -m tests.test_output
python -m tests.test_trigger
python -m tests.test_state_machine
```

Run the bridge tests:

```text
python -m tests.test_des_axis_bridge
```

## What Was Not Changed

This bridge does not change:

- DES trigger logic
- DES question flow
- DES classifier logic
- DES output format
- AXIS engine logic
- AXIS taxonomy
- AXIS outcomes
- AXIS continuity logic
- AXIS session schema
- Sapphire runtime behavior
- Sapphire prompt injection
- Sapphire routing

The adapter is a boundary layer only. It translates; it does not think.
