# DES V1 Implementation Spec

## Purpose

DES V1 is a deterministic decision-friction resolution layer.

It decides whether to offer a short friction-resolution interaction, asks a fixed
question flow, classifies the friction into a small controlled set, and returns a
structured output for a downstream UI to render.

DES V1 does not persuade, infer emotion, generate AI content, store long-term
identity, duplicate AXIS logic, or assume Sapphire UI behavior.

## Separation Rules

DES owns:

- trigger detection
- question flow with a maximum of three questions
- deterministic friction classification
- deterministic output selection
- strict request validation for its own API boundary

AXIS owns taxonomy, scoring, truth, outcomes, and any deeper intelligence layer.
DES V1 makes no AXIS calls and must not implement AXIS-equivalent logic.

Sapphire owns UI rendering, session presentation, and user-interface behavior.
DES returns structured JSON only and does not assume how Sapphire displays it.

## Trigger Rules

The V1 trigger is the pure function `should_trigger`.

It returns `True` only when all of the following are true:

- `pricing_page_sessions_last_30d >= 2`
- `has_converted is False`
- `current_page == "/pricing"`
- there is no active DES interaction in the current session
- `cooldown_ok is True`

Any failed condition returns `False`. The trigger engine has no side effects and
does not write to storage.

The `/trigger/check` API validates the request, rate-limits by `session_id`, checks
active in-memory interactions, and returns `{"show": bool}`.

## Question Flow

DES V1 asks at most three questions.

Q1 is always:

- `id`: `q1`
- options: `dont_understand_difference`, `not_sure_fit`, `too_expensive`,
  `not_ready`, `other`

Q2 depends only on the Q1 answer:

- `dont_understand_difference`: asks which plans are being compared
- `not_sure_fit`: asks free text for intended use
- `too_expensive`: asks whether the issue is `total_cost`, `value`, or `risk`
- `not_ready`: asks free text for readiness blocker
- fallback: asks for free-text clarification

Q3 is asked only when ambiguity remains:

- Q1 is `other`
- Q2 is missing or empty
- Q1 is `not_sure_fit` or `not_ready` and the free-text Q2 answer is shorter
  than 10 trimmed characters

Q3 options are `clarity`, `fit`, `trust`, and `cost`.

## Friction Types

The classifier returns exactly one of:

- `information_gap`
- `fit_uncertainty`
- `trust_deficit`

Current deterministic mappings:

- Q1 `dont_understand_difference` -> `information_gap`
- Q1 `not_sure_fit` -> `fit_uncertainty`
- Q1 `not_ready` -> `information_gap`
- Q1 `too_expensive` with Q2 `total_cost` -> `fit_uncertainty`
- Q1 `too_expensive` with Q2 `value` or `risk` -> `trust_deficit`
- Q3 `clarity` -> `information_gap`
- Q3 `fit` -> `fit_uncertainty`
- Q3 `trust` -> `trust_deficit`
- Q3 `cost` -> `fit_uncertainty`

Unknown or unmapped inputs fall back to `information_gap`.

## Output Types

`build_output` maps friction types to controlled output payloads:

- `information_gap` -> `clarify`
- `fit_uncertainty` -> `filter`
- `trust_deficit` -> `proof`

Outputs are static JSON objects with:

- `output_type`
- `title`
- `body`
- `cta`
- `ui.suppress_primary_cta`
- `ui.recommend_exit`

Unknown friction types fall back to a safe `clarify` output.

## State Machine

`core/state_machine.py` defines the reserved DES state contract and exposes:

- `VALID_TRANSITIONS`
- `can_transition(current_state, next_state)`
- `transition(current_state, next_state)`

Valid states:

- `idle`
- `triggered`
- `interaction_started`
- `q1_answered`
- `q2_answered`
- `q3_answered`
- `classified`
- `output_rendered`
- `resolved`
- `abandoned`

The current API flow does not import or enforce the state machine. It directly
sets interaction states to `interaction_started`, `q1_answered`, `q2_answered`,
and `output_rendered`, with `resolved = True` when an output is returned.

For V1 hardening, the state machine is documented and tested as reserved contract
surface. It is not wired into live flow to avoid behavior drift.

## API Routes

FastAPI exposes:

- `POST /trigger/check`
- `POST /interaction/start`
- `POST /interaction/answer`
- `GET /health`

`/interaction/start` accepts `user_id`, `session_id`, and
`trigger_type == "repeat_pricing_visit"`, creates an in-memory interaction, and
returns Q1.

`/interaction/answer` accepts `interaction_id`, `question_id`, and `answer`.
It advances the fixed flow, classifies when enough information exists, builds the
output, updates the in-memory interaction, and returns either the next question or
the final output.

## Security Rules

DES V1 fails closed:

- required fields must be present
- unknown fields are rejected
- primitive types are validated
- string length limits are enforced
- invalid trigger types and question IDs are rejected
- all endpoint handlers are rate-limited
- errors return safe structured codes
- no stack traces, file paths, environment values, or internals are returned

String limits:

- `user_id`: 128 characters
- `session_id`: 128 characters
- `current_page`: 128 characters
- answer: 280 characters

Rate limits:

- trigger check: 60 requests per minute per session key
- interaction start: 10 requests per minute per user key
- interaction answer: 30 requests per minute per interaction key

## Non-Goals

DES V1 intentionally does not include:

- AI or generated copy
- persuasion, urgency, pressure, or manipulation logic
- AXIS calls
- Sapphire UI logic
- persistence beyond process-local in-memory storage
- long-term user identity models
- emotion inference
- dynamic question expansion
- additional question count beyond three
- additional output families beyond `clarify`, `filter`, and `proof`

## Test Expectations

The V1 foundation is expected to pass:

- `python -m tests.test_flow`
- `python -m tests.test_security`
- `python -m tests.test_classifier`
- `python -m tests.test_output`
- `python -m tests.test_trigger`
- `python -m tests.test_state_machine`
- `python -m pytest` when pytest is available

Tests should preserve deterministic behavior and cover classifier mappings, output
payloads, trigger gating, and the reserved state machine contract.
