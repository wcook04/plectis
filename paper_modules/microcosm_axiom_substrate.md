# Axiom support cover

Reads axiom routing, witness and receipt records and reports support and remaining gaps for piloted axioms.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.validators.axiom_support_cover --root .
```

The command prints its report as JSON; use `--out` to write a chosen file.

## What it checks

The registry breaks each axiom into obligations: smaller clauses to check. A support case records the witnesses and receipts associated with an obligation. An anti-axiom names the contrary failure the axiom is meant to exclude. The evaluator compiles those support cases and separately checks whether evidence maps to rejection of the named anti-axiom. A principle is not itself a witness. The strong gate requires both sufficient positive support and a suitable rejection mapping; the output keeps `strong_certified` false. A conflict or unverified rejection mapping blocks a strong verdict.

## Limits

Reads the axiom routing, witness and receipt records and reports support and remaining gaps for the piloted axioms, keeping `strong_certified` false; a negative suite counts only when its evidence maps to rejection of the named anti-axiom.

## Verification

The linked tests exercise the support evaluator and its claim ceilings. This helper has no registered component-replay route or component-specific formal proof. Its report is a computation over the supplied records; it does not prove an axiom or rejection of its anti-axiom.

## Source and evidence

- [Implementation](../src/microcosm_core/validators/axiom_support_cover.py) and [focused tests](../tests/test_axiom_support_cover.py)
- [Example input](../core/axiom_organ_routing.json) and [historical sample result](../receipts/first_wave/axiom_support_cover/axiom_support_cover_result.json)
- [Component JSON record](./microcosm_axiom_substrate.json) and [canonical capsule](../core/paper_module_capsules.json)

[W3C PROV](https://www.w3.org/TR/prov-overview/) provides broader provenance context.
