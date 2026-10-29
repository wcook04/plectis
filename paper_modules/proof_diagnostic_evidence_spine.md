# Check proof diagnostic evidence

> **In plain terms.** Diagnostic reports about proofs are only useful if their claims point to real files that have not changed. This component is given a bundle of diagnostic entries, each linking a failure report to a spot in a saved record, plus the source files and their fingerprints. It follows each link to the file and spot it names, compares fingerprints, and rejects any row from an outside provider that contains a full proof. It writes a result without proof text, listing which evidence is supported and flagging any changed source file as out of date.

Checks in a public evidence bundle point to source files and receipt anchors. This validator resolves those references, compares source digests and checks the receipt bindings; it also checks diagnostic rows and provider payload policy. For example, a diagnostic row links a failure-taxonomy report to a receipt anchor. Provider rows must not contain proof bodies. The validator writes a body-free result for inspecting which evidence is supported.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.proof_diagnostic_evidence_spine run-evidence-bundle \
  --input examples/proof_diagnostic_evidence_spine/exported_evidence_bundle \
  --out .microcosm/component-guides/proof_diagnostic_evidence_spine
```

Inspect `.microcosm/component-guides/proof_diagnostic_evidence_spine/exported_evidence_bundle_validation_result.json` for the result and findings.

The check also inspects copied artifact digests and rejects evidence anchors that do not match the cited source. The saved result records diagnostic evidence, not proof authority.

## What the result means

Resolves the bundle's source and receipt references, compares source digests and checks its diagnostic rows, rejecting a provider row that contains a proof body and reporting a stale source fingerprint.

Related reading: [NTRS 20160005295](https://ntrs.nasa.gov/citations/20160005295), [W3C PROV](https://www.w3.org/TR/prov-overview/).

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. No component-specific formal proof establishes the diagnostic algorithm or a theorem.

## Source

[Implementation](../src/microcosm_core/organs/proof_diagnostic_evidence_spine.py) · [input](../examples/proof_diagnostic_evidence_spine/exported_evidence_bundle) · [tests](../tests/test_proof_diagnostic_evidence_spine.py) · [historical sample result](../receipts/first_wave/proof_diagnostic_evidence_spine/exported_evidence_bundle_validation_result.json) · [component record](../core/paper_module_capsules.json).
