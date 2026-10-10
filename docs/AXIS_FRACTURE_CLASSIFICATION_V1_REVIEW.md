# AXIS Fracture Classification V1 — Approval Record

Status: **approved production content; inactive by default**

Approved: 2026-10-08

Selector: `axis_fracture_classification@1.0.0`

## Authority and provenance

The operator approved a copy-with-provenance policy grounded in AXIS commit
`2c3fd35d36fa0d1eea751f02f1ac38776a3d3a1f`:

- vocabulary and labels: `lib/patterns/registry.ts` (`PATTERN_METADATA`)
- fracture-to-class behavior: `app/session/page.tsx` (`classifyFromAnalysis`)

Labels are copied from AXIS `userLabel` values without added interpretations.
The question set does not expose class names as choices.

## Decision policy

Q1 asks which single published AXIS fracture pattern applies. The ten fracture
ids route to Q2. `none_apply` and `unsure` terminate unresolved at Q1.

Q2 asks whether another distinct fracture pattern is also present. A negative
answer applies the pinned AXIS mapping; a positive answer terminates unresolved.
There is no first-wins rule, inference, partial match, or default.

| AXIS class | Fracture ids |
| --- | --- |
| `behavioral` | `avoidance_loop`, `boundary_violation`, `over_responsibility` |
| `emotional` | `rejection_sensitivity`, `shame_spike` |
| `narrative` | `comparison_spiral`, `self_worth_dependency`, `status_threat` |
| `perceptual` | `control_loss`, `uncertainty_intolerance` |
| `continuity` | none |

Continuity is deliberately unreachable because the cited AXIS source defines no
fracture mapped to it. Adding one requires new authority and a new version.

## Complete path accounting

There are exactly 22 complete paths:

- 10 single-fracture paths resolve through the mapping above.
- 10 multiple-pattern paths terminate `EXPLICIT_UNRESOLVED`.
- `none_apply` and `unsure` terminate `EXPLICIT_UNRESOLVED` at Q1.

Every complete path has one explicit rule. Construction fails if a rule is
missing, duplicated, partial, or not a real path.

## Activation boundary

Approval permits the production content to exist and be selected explicitly in
DES. It does not activate the set by default, authorize class-to-`next_action`
text, configure AXIS credentials, or authorize a live AXIS request. Those gates
remain separate.

## Verification evidence

The production runtime is pinned at commit
`6d39960461a4a7960d3e9f9db36fadbc26aa352c`. The loopback recorder generated
the scaffold and production fixtures twice with byte-identical normalized wire
content while AXIS settings were absent. The full DES suite passed 548 tests.

Eight isolated mutations were run and every one was caught:

| Mutation | Gate that failed |
| --- | --- |
| Change `control_loss` from `perceptual` to `narrative` | exact approved mapping and outcome counts |
| Swap the classes for `control_loss` and `rejection_sensitivity` | exact approved mapping |
| Delete the final explicit rule | 22-rule completeness and outcome counts |
| Resolve a multiple-pattern path with the first fracture's class | exact outcome counts |
| Resolve `unsure` as `continuity` | exact outcome counts and Continuity exclusion |
| Route `none_apply` and `unsure` to q2 | load-time exact-path validation |
| Add `behavioral` as a q1 option | 12-option/path counts and real-handler rejection |
| Rename `control_loss` to `control_grip` | pinned fracture-id import guard |

The 22-path real-handler test exercises every authored rule, but the source,
graph, outcome-count and rejection checks are independently necessary: a test
that derives its expectations from mutated rules cannot by itself detect every
policy change. All disposable mutation checkouts were removed after the runs.
