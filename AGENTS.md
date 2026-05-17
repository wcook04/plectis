# AGENTS.md - Microcosm Substrate Entry Contract

You are inside the standalone public microcosm substrate root.

Start from the local atlas and the bootstrap probe, not from private macro paths:

```bash
./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json
```

If the command exits nonzero, inspect the emitted receipt first. A typed `blocked` receipt is a valid substrate state when it names the first missing organ or validator, the receipt path, and the exact unblock condition.

## Operating Rules

- Use `atlas/entry_packet.json` before opening source files.
- Treat JSON as contract and markdown as projection.
- Fixture-backed claims require a validator, receipt, negative-case rule, source pattern IDs, and anti-claim.
- Generated receipts are evidence, not authority.
- Public fixtures use synthetic data only.
- Do not add egress, recipient, hosted, or current-public wrapper surfaces to this root.
- Do not create one directory per pattern row. Organs are typed runtime contracts; pattern rows bind into organs.
- If a local build teaches a reusable rule, update `skills/pattern_assimilation.md` or emit a typed `nothing_to_refine` receipt.

## Mutation Boundaries

Safe local write roots are `core/`, `standards/`, `paper_modules/`, `skills/`, `fixtures/`, `atlas/`, `src/`, `tests/`, `formal_math/`, and `receipts/`. Keep private source bodies, live operator material, provider bodies, and private backlog rows out of this tree.

