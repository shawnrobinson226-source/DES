# DES Operator Contract V1

## Scope

This document describes the `operator_initiated` interaction contract implemented
by DES. It is separate from the legacy `repeat_pricing_visit` flow.

The contract version is `1.0.0`. DES does not execute AXIS as part of this flow.

## Entry And Routing

`POST /interaction/start` accepts:

```json
{
  "user_id": "user-1",
  "session_id": "session-1",
  "trigger_type": "operator_initiated"
}
```

Before operator dispatch, start handling applies rate limiting, required-field
checks, unknown-field rejection, string validation, and `trigger_type`
validation, in that order. Later calls to `POST /interaction/answer` route by the
stored interaction's `trigger_type`. The pricing flow remains separate.

## Availability And Version Pinning

`OPERATOR_QUESTION_SETS` is created empty. Nothing in this repository registers
or activates production question-set content. Until an external bootstrap does
both, an operator start returns:

```json
{
  "error": "Question set unavailable",
  "code": "QUESTION_SET_UNAVAILABLE"
}
```

A successful start pins the active question-set `id` and `version` on the new
interaction. Every later answer looks up that exact pair. Activating a newer
version does not move an existing interaction. If the pinned version is missing,
the answer fails closed with `QUESTION_SET_UNAVAILABLE`.

## Question Response

A question response contains exactly:

```json
{
  "interaction_id": "generated-id",
  "done": false,
  "contract_version": "1.0.0",
  "question_set": {
    "id": "set-id",
    "version": "set-version"
  },
  "question": {
    "id": "q1",
    "text": "Question text",
    "options": [
      {
        "id": "option-id",
        "label": "Option label"
      }
    ]
  }
}
```

`done` is exactly `false`. `question_set` contains exactly `id` and `version`.
`question` contains exactly `id`, `text`, and `options`. Each option contains
exactly `id` and `label`.

Answers must be exact option ids. Labels, free text, case variants, and
whitespace variants are not substitutes. A question-set path may proceed to
another question or terminate, and may skip `q2` or `q3`.

## Terminal Responses

A resolved response contains exactly:

```json
{
  "status": "resolved",
  "classification": "behavioral",
  "done": true,
  "contract_version": "1.0.0",
  "question_set": {
    "id": "set-id",
    "version": "set-version"
  }
}
```

An unresolved response contains exactly:

```json
{
  "status": "unresolved",
  "reason": "NO_MATCHING_RULE",
  "done": true,
  "contract_version": "1.0.0",
  "question_set": {
    "id": "set-id",
    "version": "set-version"
  }
}
```

The only unresolved reasons are `NO_MATCHING_RULE` and
`EXPLICIT_UNRESOLVED`. A complete path without a rule is unresolved; there is no
default classification.

Terminal responses do not contain `interaction_id`. The caller must retain the
id received at start and bind the terminal response to that interaction.

An unresolved response never carries `classification`, pricing output fields,
or AXIS payload fields. Raw operator responses are not legacy pricing responses
and are rejected by `build_axis_payload`. The operator flow makes no AXIS
request.

## Errors

Operator errors contain exactly `error` and `code`. The FastAPI wrapper returns
the plain handler dictionary, so these errors currently use HTTP 200.

| Code | Message |
| --- | --- |
| `QUESTION_SET_UNAVAILABLE` | `Question set unavailable` |
| `INTERACTION_CLOSED` | `Interaction closed` |
| `OUT_OF_ORDER` | `Question out of order` |
| `INVALID_OPTION` | `Invalid option` |
| `RESULT_VALIDATION_FAILED` | `Result validation failed` |

An answer checks conditions in this order:

1. The pinned question set exists.
2. The interaction is not closed.
3. The question id is the expected next question.
4. The answer is an exact option id.

Shared request validation and interaction lookup occur before operator dispatch.

## Mutation And Storage

A start response is built and validated before the interaction is saved.
Answer processing makes a shallow copy of the stored interaction, applies the
candidate answer to the copy, and validates the next-question or terminal
response before one update. A rejection does not create or change the stored
interaction.

Answers use the existing `q1`, `q2`, and `q3` fields. A skipped question stays
`None`.

Operator interactions do not update `state`; it stays at the model default
`interaction_started`. Consumers must use `resolved` and `resolution_status` to
read operator completion.

For a resolved result, storage contains:

- `resolved = True`
- `resolution_status = "resolved"`
- `axis_classification = <classification>`
- `unresolved_reason = None`

For an unresolved result, storage contains:

- `resolved = True`
- `resolution_status = "unresolved"`
- `unresolved_reason = <reason>`
- `axis_classification = None`

`friction_type` and `output_type` stay unset for operator interactions. The
pricing flow does not populate the five operator-specific fields:
`question_set_id`, `question_set_version`, `resolution_status`,
`axis_classification`, and `unresolved_reason`.

The response names `status`, `classification`, and `reason` are distinct from
the stored model names `resolution_status`, `axis_classification`, and
`unresolved_reason`.

## System Boundaries

AXIS owns its five classification names and execution. DES holds an allowlisted
copy of those names and validates operator-authored question-set outcomes against
that allowlist. It does not perform AXIS scoring or inference.

Sapphire or another plugin owns presentation and must retain the
`interaction_id` received at start. Any confirmation must be presented by the
plugin and authorized by the Operator; DES neither confirms nor authorizes. The
plugin must not recreate DES question routing, resolution rules, or defaults.

DES carries no operator identity and verifies none. The request `user_id` is
caller-supplied and unauthenticated. Operator identity and confirmation must live
at the plugin boundary; DES neither provides nor checks them, and this repository
does not verify that any plugin does so.

Legacy pricing terminal output uses `friction_type` and `output.output_type` and
may be passed to the pricing payload builder. Operator terminal output uses
`classification` or `reason` and must not be passed to that builder.

## Current Limitations

- Storage is in-memory and process-local.
- There is no answer locking, compare-and-swap protection, or idempotency key;
  simultaneous answers may race and the last write may win.
- Corrupted stored routing state can produce an uncaught `KeyError` in a path
  normal validated operation cannot create.
- The production registry is empty and this repository has no bootstrap.
- The reserved state machine is not used by operator interactions.
- Terminal responses rely on caller-side interaction-id binding.
- DES carries no operator identity and verifies none. The request `user_id` is
  caller-supplied and unauthenticated. Operator identity and confirmation must
  live at the plugin boundary; DES neither provides nor checks them, and this
  repository does not verify that any plugin does so.
- DES endpoints have no authentication. A loopback-only deployment is a
  compensating control, but this repository does not configure or prove the
  server bind address.
- There is no cancellation route.
