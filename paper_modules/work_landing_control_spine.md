# Work Landing Control Spine

## Teleology

`work_landing_control_spine` makes the macro work-landing control plane
inspectable inside Microcosm by copying the non-secret command, reconcile,
mission preflight, and private-index scoped commit source bodies into a public
bundle. The point is not to let the public validator mutate Git or ledgers; it
is to expose the real control-plane mechanics that govern claims, owned paths,
same-path conflicts, expected-parent checks, shared-index quarantine, finalizer
ordering, and scoped commit discipline.

## Public Contract

The public command is:

```bash
PYTHONPATH=src python3 -m microcosm_core.cli work-landing-control-spine validate-control-bundle \
  --input examples/work_landing_control_spine/exported_work_landing_control_bundle \
  --out receipts/first_wave/work_landing_control_spine
```

The validator checks copied module digests, line counts, required source
anchors, the no-live-mutation runtime contract, the originating overclaim
WorkItem reference, and a secret-exclusion scan over the copied bundle. Source
bodies live in the bundle; receipts carry refs, hashes, counts, gates, and
findings.

## Governing Standard

`standards/std_microcosm_work_landing_control_spine.json` owns the receipt
contract, source refs, allowed public inputs, forbidden private inputs, and
authority ceiling for this import.

## Source Substrate

The copied macro bodies are:

- `tools/meta/control/work_landing.py`
- `system/lib/work_landing_status.py`
- `tools/meta/control/mission_transaction_preflight.py`
- `system/lib/mission_transaction_landing_preflight.py`
- `tools/meta/control/scoped_commit.py`

This closes the old `work_landing_tool_body_import` overclaim by adding an
exact copied-source bundle beneath the existing public dry-run refactor.

## Anti-Claim

This spine is local control-plane substrate for inspection and validation. It
does not run live Git mutations; mutate Task Ledger or Work Ledger state;
release claims; stage broadly; execute private-index commits; call providers;
export credentials, account/session state, provider payload bodies, or
recipient-send state; publish; host; or authorize release.
