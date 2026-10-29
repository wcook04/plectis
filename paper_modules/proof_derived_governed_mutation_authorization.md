# Governed mutation evidence replay

> **In plain terms.** A system that changes things automatically needs evidence that each change was checked, allowed by policy and can be undone. This component is given made-up change proposals, each linked to proof records, policy rulings, an undo record and a version-control record. It looks up each record, recalculates a fingerprint summarizing the evidence, checks the version-control record, and rejects a proposal with only one visible policy ruling, a stale fingerprint or no undo record for a reversible write. It writes a saved record of whether each proposal's evidence holds together, showing which are properly backed.

Checks synthetic mutation proposals against linked proof, policy, side-effect, rollback and replay records, then writes an authorization replay receipt.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.proof_derived_governed_mutation_authorization run --input fixtures/first_wave/proof_derived_governed_mutation_authorization/input --out .microcosm/component-guides/proof_derived_governed_mutation_authorization --acceptance-out .microcosm/component-guides/proof_derived_governed_mutation_authorization/acceptance.json --card
```

Inspect the status and findings in `.microcosm/component-guides/`; the linked result below is a historical sample.

## What it checks

For each proposal, the validator resolves proof cells and visible policy verdicts, recomputes an evidence-chain hash and checks the associated record. Write and rollback proposals require side-effect and rollback records. It also checks a Git commit witness and its changed paths; Git must be installed and the referenced commit available. A proposal with one visible verdict, a stale hash or no rollback for a reversible write is rejected.

## Limits

Checks synthetic mutation proposals against their proof cells, policy verdicts, evidence-chain hash, rollback records and a Git commit, and rejects a proposal with a single verdict, a stale hash or a missing rollback.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported authorization bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/proof_derived_governed_mutation_authorization.py) and [focused tests](../tests/test_proof_derived_governed_mutation_authorization.py)
- [Example input](../fixtures/first_wave/proof_derived_governed_mutation_authorization/input/mutation_proposals.json) and [historical sample result](../receipts/first_wave/proof_derived_governed_mutation_authorization/proof_derived_governed_mutation_authorization_result.json)
- [Component JSON record](./proof_derived_governed_mutation_authorization.json) and [canonical capsule](../core/paper_module_capsules.json)

For policy-engine context see [Open Policy Agent](https://www.openpolicyagent.org/docs), [Kubernetes admission controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/), and [feature toggles](https://martinfowler.com/articles/feature-toggles.html).
