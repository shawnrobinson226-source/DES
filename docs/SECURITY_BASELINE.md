# DES — Security Baseline (V1)

## Core Principle

System must fail closed.

If anything is invalid, unclear, or unexpected:
→ reject request

---

## Input Validation

Baseline target:

- All requests must match exact schema
- Missing fields → reject (400)
- Unknown fields → reject (400)
- Enum mismatch → reject (400)
- String limits enforced:
  - user_id ≤ 128 chars
  - session_id ≤ 128 chars
  - answer ≤ 280 chars

---

## Rate Limiting

Apply to all endpoints:

- /trigger/check → 60 req/min per session_id
- /interaction/start → 10 req/min per user_id
- /interaction/answer → 30 req/min per interaction_id

Exceed → reject (429)

---

## Logging Rules

DO NOT log:
- raw user answers
- full user_id (mask or hash if needed)

Log ONLY:
- interaction_id
- state transitions
- error codes
- timestamps

---

## Error Handling

All responses must be safe.

Allowed:

{
  "error": "Invalid request",
  "code": "INVALID_INPUT"
}

NOT allowed:
- stack traces
- DB errors
- internal messages
- file paths
- environment data

---

## Execution Safety

- No eval / exec
- No dynamic code execution
- No runtime imports from user input

---

## External Calls

- DES interaction routes do not call AXIS automatically.
- The explicit legacy pricing adapter can call the allowlisted AXIS execute path.
- Current adapter behavior:
  - allowlist endpoints only
  - timeout = 10 seconds
  - fail closed on error
- The operator flow makes no AXIS request.

---

## Current Implementation Limitations

These are current gaps, not completed controls:

- The FastAPI routes return handler dictionaries directly. Validation and rate
  limit errors therefore use HTTP 200 instead of the baseline 400 and 429 status
  codes.
- DES endpoints have no authentication.
- A loopback-only server bind is required as a compensating deployment control,
  but this repository does not configure or prove the bind address.
- The only in-repository AXIS caller is the CLI in `ui/des_axis_flow.py`, and it
  passes the fixed `operator_id` value `local-operator`. The bridge function
  requires a non-empty value, but nothing in DES authenticates or verifies an
  operator identity.
- Operator state is process-local and in-memory.
- There is no operator answer locking or idempotency protection.
- There is no operator cancellation route.

---

## Output Safety

- No HTML in output
- No script injection
- All output is plain structured JSON

---

## Final Rule

If validation fails at any point:
→ STOP processing
→ return error