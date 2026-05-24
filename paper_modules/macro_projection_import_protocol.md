# Macro Projection Import Protocol

`macro_projection_import_protocol` is the source-available membrane for bringing
macro substrate into Microcosm. It exists because Microcosm should be dense and
alive without becoming a dump of private source bodies, operator context,
provider payloads, or release material.

The organ validates a projection packet with four public claims:

- non-secret macro bodies are copied or source-faithfully refactored only when
  the target file, digest, provenance, validation refs, and body-free receipt
  contract verify;
- private material is omitted with explicit omission receipts;
- public runtime refs are fixtures, standards, paper modules, exported bundles,
  copied body targets, and receipt refs;
- authority stays capped below release, publication, private-root equivalence,
  and live macro source authority.

## Runtime Shape

Run the fixture:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.macro_projection_import_protocol run --input fixtures/first_wave/macro_projection_import_protocol/input --out receipts/first_wave/macro_projection_import_protocol
```

Run the exported bundle:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.macro_projection_import_protocol run-projection-bundle --input examples/macro_projection_import_protocol/exported_projection_import_bundle --out receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol
```

Preview the next import slice without writing receipts:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.macro_projection_import_protocol plan --input examples/macro_projection_import_protocol/exported_projection_import_bundle
```

The public CLI also exposes the same validator through:

```bash
microcosm macro-projection-import-protocol run-projection-bundle --input examples/macro_projection_import_protocol/exported_projection_import_bundle --out receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol
microcosm macro-projection-import-protocol plan --input examples/macro_projection_import_protocol/exported_projection_import_bundle
microcosm intake
```

The `plan` action emits `macro_projection_import_intake_preview_v1`. It does
not write receipts. It scores each proposed projection cell before import:
source refs, public target refs, validation refs, selected pattern ids, copy
policy, authority ceiling, omitted material, secret-exclusion scan count,
verified body-import status, and ready/blocked status.

It also self-hosts the intake cell state machine. Every projection cell carries
`projection_status`, `cell_state`, `action_required`, status reason, landed
evidence refs, and a next runtime surface. The board totals those fields as
status counts plus an open-actionable count so future passes can distinguish a
ready but unlanded cell from a verified public runtime import, self-hosted
protocol, or runtime bridge that is already consumed.

`microcosm intake` is the runtime bridge over that plan. It writes
`receipts/runtime_shell/intake_bridge/runtime_reveal_import_bridge.json`,
links the projection cells to the spine and reveal commands, and projects the
same statuses into the first-run bridge. Current landed statuses are:
`public_runtime_import_landed` for `formal_math_readiness_extensions`,
`self_hosted_status_protocol_landed` for `projection_protocol_self_host`, and
`runtime_bridge_landed` for `runtime_reveal_import_bridge`. These statuses do
not raise authority above public metadata, fixture shape, and receipt refs.

`microcosm status` and `microcosm spine` also expose the computed
`macro_body_import_floor`: five verified public-safe body material rows, including
two non-Lean tool bodies and one Lean/proof body, with target digests checked
against `projection_protocol.json`. This count is a body-import floor, not a
release signal or private-root equivalence claim.

## Negative Cases

The validator intentionally rejects:

- private body import requests;
- omitted macro material without omission receipt refs;
- authority upgrades into live macro source authority;
- projection cells without validation refs;
- release, publication, recipient-work, or secret-export claims.

## Authority Ceiling

This paper module explains a public projection protocol. It does not authorize
release, hosted deployment, publication, recipient work, provider calls,
Lean/Lake execution, secret export, private source-body export, or
whole-system correctness.
