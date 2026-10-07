# DES — Decision Environment System (V1)

DES is a deterministic decision-friction resolution layer.

It exposes two separate interaction flows:

- `repeat_pricing_visit`: the legacy pricing flow
- `operator_initiated`: a versioned, question-set-driven operator flow

It:
- detects friction
- asks up to 3 questions
- follows validated question-set routes for operator interactions
- classifies friction
- returns structured output

It does NOT:
- persuade
- infer emotion
- store identity logic
- duplicate AXIS
- assume UI (Sapphire)

Legacy pricing outputs:
- clarify
- filter
- proof

Operator terminal outcomes:
- resolved with an allowlisted AXIS classification name
- unresolved with an explicit reason

See [DES Operator Contract V1](docs/DES_OPERATOR_CONTRACT_V1.md) for the
`operator_initiated` response and storage contract. Production content is
available but remains inactive unless an exact version is selected through the
fail-closed startup bootstrap. See the
[DES Local Launch Specification](docs/DES_LAUNCH_SPEC.md).

System principles:
- deterministic behavior
- strict validation
- fail-closed security
- no hidden logic
