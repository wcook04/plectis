# Projection Import Protocol

This protocol checks records for copying or refactoring selected source material into the public repository. The input identifies source and target references, material classes, digests, omissions, and validation references. It produces a plan or validation receipt so a reviewer can inspect the claimed provenance and boundaries.

A copied-body claim without a target and a real digest is rejected, as is an import without the required verification. The plan can report that a live source has changed since a recorded exact copy; that drift is distinct from a bad recorded import. A digest checks byte identity, not the correctness or completeness of the copied implementation, and a passing protocol is not a release decision. The non-writing plan below is useful when inspecting an import before making changes.

## Run the example

From the repository root with Python 3.11 or newer, preview the supplied exported bundle without writing files:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.macro_projection_import_protocol plan \
  --input examples/macro_projection_import_protocol/exported_projection_import_bundle
```

The returned JSON includes a status and the import-plan findings.

See [W3C PROV](https://www.w3.org/TR/prov-overview/), [SLSA](https://slsa.dev/spec/), and [in-toto](https://in-toto.io/) for related provenance approaches.

## Verification

The plan command above does not invoke formal admission. `make component-replays` runs the exported import bundle through the [shared Dafny admission check](../formal/replay/README.md), checking agreement among supplied source, input, claim policy and receipt observations. A passing digest or test does not prove the import algorithm correct.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/macro_projection_import_protocol.py) and [fixture inputs](../fixtures/first_wave/macro_projection_import_protocol/input/).
- [Tests](../tests/test_macro_projection_import_protocol.py).
- [Saved example result](../receipts/first_wave/macro_projection_import_protocol/macro_projection_import_protocol_result.json) (historical, not a fresh run).
- [Component JSON record](./macro_projection_import_protocol.json) and [canonical capsule](../core/paper_module_capsules.json).
