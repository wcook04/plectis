# Resolve evidence cells to public source anchors

> **In plain terms.** Each claim in a research paper should point to real evidence and to a findable place in public files. The resolver reads the paper's claims, evidence records and a list of named places in public source files. It checks that every claim names an evidence record that exists, that each file and marked spot it cites can be found, and that imported copies match their stored fingerprints. It saves a record of what resolved and rejects deliberately bad example claims, such as a missing cited place, a reference to private material and human approval treated as proof. A pass shows only that references line up and copies match, not that any theorem is correct.

The resolver reads paper claims, evidence-cell records and public source anchors, then checks that claims name known cells and that referenced paths and markers resolve. Its result records the resolution without copying proof bodies into the receipt. The fixture includes deliberately invalid claims: a missing source anchor, a private source reference and a claim that human approval is proof evidence are rejected.

The bundled source checks also compare imported module digests. These checks establish that references and configured copies match; they do not prove theorem correctness or independently validate the mathematics.

## Run the example

Python 3.11 or later is required. From the repository root, write the fixture result and acceptance record to ignored local state.

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.formal_evidence_cell_anchor_resolver run --input fixtures/first_wave/formal_evidence_cell_anchor_resolver/input --out .microcosm/component-guides/formal_evidence_cell_anchor_resolver --acceptance-out .microcosm/component-guides/formal_evidence_cell_anchor_resolver/acceptance.json --card
```

## Verification

Tests exercise source-marker resolution, refusals and bundle digest checks; they do not prove the referenced claims. `make component-replays` runs the exported anchor bundle through the [shared Dafny check](../formal/replay/README.md) over supplied source, input, claim-policy and receipt observations. The direct example does not invoke that gate.

## Source

[Implementation](../src/microcosm_core/organs/formal_evidence_cell_anchor_resolver.py) · [Input](../fixtures/first_wave/formal_evidence_cell_anchor_resolver/input) · [Tests](../tests/test_formal_evidence_cell_anchor_resolver.py) · [Historical sample](../receipts/first_wave/formal_evidence_cell_anchor_resolver/formal_evidence_cell_anchor_resolver_result.json) · [JSON record](formal_evidence_cell_anchor_resolver.json)

[W3C PROV](https://www.w3.org/TR/prov-overview/) describes a general provenance model; this resolver implements its own anchor checks.
