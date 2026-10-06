# DES AXIS Bridge V1

## Status

The bridge is implemented for legacy pricing output.

DES interaction API routes do not automatically execute AXIS and do not wire the
bridge into start or answer handling. An explicit caller can use
`core.axis.bridge.execute_axis_request`, which posts to the configured AXIS URL.

The compatibility mapper for completed legacy pricing results is:

```python
build_axis_payload(des_result: dict) -> dict
```

The operator flow is excluded from this bridge and makes no AXIS request.

## Separation

Sapphire displays.
DES decides.
AXIS governs.

DES remains separate from AXIS and Sapphire. DES does not duplicate AXIS logic,
redefine AXIS taxonomy, infer emotions, persuade, store long-term identity, or
bypass AXIS governance.

AXIS remains the source of truth and governing engine.

## Friction Mapping

DES `friction_type` maps to AXIS `classification`:

| DES friction_type | AXIS classification |
| --- | --- |
| `information_gap` | `perceptual` |
| `fit_uncertainty` | `behavioral` |
| `trust_deficit` | `narrative` |

Unknown friction values fail closed with `AxisBridgeError`.

## Output Mapping

DES `output.output_type` maps to AXIS `next_action`:

| DES output_type | AXIS next_action |
| --- | --- |
| `clarify` | `Review the clarified decision information and choose one next step.` |
| `filter` | `Confirm fit or non-fit and act on the result.` |
| `proof` | `Review the evidence and separate verified claims from assumptions.` |

Unknown output values fail closed with `AxisBridgeError`.

## Payload Contract

The AXIS-ready payload contains exactly:

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

Allowed fields are exactly:

- `trigger`
- `classification`
- `next_action`
- `reference`
- `stability`
- `impact`

The mapper never includes:

- `outcome`
- `friction_type`
- `output_type`
- `ui`
- `distortion_class`

Defaults:

- `reference`: `true`
- `stability`: `6`
- `impact`: `4`

## Trigger Source

The compatibility mapper passes `des_result["trigger"]` to the canonical mapper.
A missing, empty, or whitespace-only trigger fails closed. There is no
`output.title` fallback.

## Failure Cases

`build_axis_payload` raises `AxisBridgeError`, a `ValueError` subclass exported
by the compatibility wrapper under its legacy exception alias, when:

- the DES result is not a dict
- `trigger` is missing, empty, or whitespace-only; there is no `output.title`
  fallback
- `friction_type` is missing
- `friction_type` is unknown
- `output` is missing
- `output` is not a dict
- `output.output_type` is missing
- `output.output_type` is unknown
- the produced payload fields differ from the exact allowed AXIS field set

Runtime validation uses explicit conditionals and `AxisBridgeError`; it does not
use assertions.

## Execution Boundary

`core.axis.bridge.execute_axis_request` is the explicit caller. It requires a
non-empty `operator_id`, sends `x-operator-id`, posts only to
`/api/v2/execute`, uses a 10-second timeout, and does not retry.

It is not called by DES interaction routes. Wiring any automatic API execution,
or adding an operator-to-AXIS path, requires separate approval and must not
change DES decision behavior.

Operator terminal responses are intentionally incompatible with
`build_axis_payload`: they have no pricing `output` or `friction_type` fields.
