# Mission Transaction Work Spine

This source-available module validates the public mission transaction work-spine over imported `work_landing` and `mission_transaction_preflight` macro-tool substrate.

The slice consumes `microcosm_core.macro_tools.work_landing` receipts for public work landing status, attempt binding, and source-faithful 12-step reconcile ordering. It also consumes `microcosm_core.macro_tools.mission_transaction_preflight` for the macro preflight decision rules around same-path claim conflicts, expected-parent mismatch, missing owned paths, checkpoint-lane selection, and the rule that a clean preflight still cannot claim landed work.

Regression task, claim, checkpoint, and dependency rows remain negative-case harnesses. They are not product evidence unless the organ binds them to body-free public macro-tool receipts, secret-exclusion scan output, source/target symbol refs, and runtime validation.

It does not mutate live work ledgers, git state, Task Ledger authority, raw operator material, provider material, release surfaces, or private source bodies.
