# DES — Security Baseline (V1)

## Core Principle

System must fail closed.

If anything is invalid, unclear, or unexpected:
→ reject request

---

## Input Validation

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

- /trigger/check → 60 req/min per user_id
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

- AXIS not used in V1
- Future:
  - allowlist endpoints only
  - timeout ≤ 3 seconds
  - fail closed on error

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