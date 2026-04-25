# DES AXIS Bridge V1

## Status

This document describes bridge preparation only.

DES V1 does not automatically execute AXIS. It does not call the live AXIS URL,
does not include a network client, and does not wire the bridge mapper into DES
API routes.

The only bridge behavior in V1 is a deterministic payload mapper:

```python
build_axis_payload(des_result: dict) -> dict
```

## Separation

Sapphire displays.
DES decides.
AXIS governs.

DES remains separate from AXIS and Sapphire. DES does not duplicate AXIS logic,
redefine AXIS taxonomy, infer emotions, persuade, store long-term identity, or
bypass AXIS governance.

AXIS remains the source of truth and governing engine. A future AXIS caller would
need explicit, separate approval before any live request is added.

## Friction Mapping

DES `friction_type` maps to AXIS `classification`:

| DES friction_type | AXIS classification |
| --- | --- |
| `information_gap` | `perceptual` |
| `fit_uncertainty` | `behavioral` |
| `trust_deficit` | `narrative` |
| `unknown` | `continuity` |

Unknown friction values fail closed with `BridgeError`.

## Output Mapping

DES `output.output_type` maps to AXIS `next_action`:

| DES output_type | AXIS next_action |
| --- | --- |
| `clarify` | `Review the clarified decision information and choose one next step.` |
| `filter` | `Confirm fit or non-fit and act on the result.` |
| `proof` | `Review the evidence and separate verified claims from assumptions.` |

Unknown output values fail closed with `BridgeError`.

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

The mapper prefers `des_result["trigger"]`.

If `trigger` is absent, the mapper may use `des_result["output"]["title"]` as a
documented fallback label for older completed DES results. This fallback is not
inference and does not add behavior to DES decision logic.

If `trigger` is present but empty, the mapper fails closed. It does not fall back
to `output.title` because an explicit empty trigger is invalid input.

## Failure Cases

`build_axis_payload` raises `BridgeError`, a `ValueError` subclass, when:

- the DES result is not a dict
- `trigger` is present but empty
- `trigger` is missing and `output.title` is not a valid fallback
- `friction_type` is missing
- `friction_type` is unknown
- `output` is missing
- `output` is not a dict
- `output.output_type` is missing
- `output.output_type` is unknown
- the produced payload fields differ from the exact allowed AXIS field set

Runtime validation uses explicit conditionals and `BridgeError`; it does not use
assertions.

## Future Step

The next step, if separately approved, would be an explicit AXIS client/caller
that sends this payload to the locked AXIS V2 execute endpoint. That future work
must be reviewed as a separate integration step and must not change DES V1
decision behavior.
