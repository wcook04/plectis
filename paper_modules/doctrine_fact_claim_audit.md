# Audit fact references and numeric claims

> **In plain terms.** A project's written guidance states facts, and the references showing where each comes from can break or fall out of step. This check reads a table of stated facts with their code locations, a map of links between facts, and sample text containing numbers. It compares the declared fact count with the actual rows, checks each fact has a code location and each link ends at a real fact, and flags current-state figures with no matching fact section. It reports broken references and mismatched declarations so maintainers can fix them.

`doctrine_fact_claim_audit` checks a supplied table of fact assertions, their source references and a graph of fact IDs. It also uses a copied numeric-claim detector to find fixture text whose current-state numbers lack a corresponding assertion section. The result helps maintainers find broken references and mismatched declarations.

## Run the example

From the repository root, with Python 3.11 or later:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.doctrine_fact_claim_audit run \
  --input fixtures/first_wave/doctrine_fact_claim_audit/input \
  --out .microcosm/component-guides/doctrine_fact_claim_audit \
  --acceptance-out .microcosm/component-guides/doctrine_fact_claim_audit/acceptance.json
```

The output includes a result, board, validation and acceptance record. The evaluator compares the declared fact count with the actual rows, checks that each fact has a code location and that any specified anchor appears in the copied source, and verifies graph edge endpoints. It also checks the numeric detector's expected results.

## What this checks

The tests mutate the input to create wrong counts, missing locations, dead graph references and unbound numeric claims. A dead graph endpoint, for example, is rejected rather than accepted merely because a fixture labels it as a failure. Source manifest digests are checked separately from the fact relations.

## Limits

These checks establish the listed relations over the supplied public fixture. They do not determine whether the assertions themselves are true, prove that the graph covers every useful reading route, or establish that a reader understands the doctrine.

## Verification

The direct example does not invoke the shared gate. In `make component-replays`, this component’s registered route passes through the [Dafny replay admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement over host-supplied observations. It does not prove this component’s algorithm.

## Sources

- [Implementation](../src/microcosm_core/organs/doctrine_fact_claim_audit.py), [fixture inputs](../fixtures/first_wave/doctrine_fact_claim_audit/input) and [tests](../tests/test_doctrine_fact_claim_audit.py).
- [Historical result](../receipts/first_wave/doctrine_fact_claim_audit/doctrine_fact_claim_audit_result.json) and [component record](../core/paper_module_capsules.json).
- [W3C PROV](https://www.w3.org/TR/prov-overview/) describes provenance records; it does not verify the assertions in this fixture.
