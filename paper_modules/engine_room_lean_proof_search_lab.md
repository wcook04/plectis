# Search for small Lean proofs

This lab generates bounded symbolic tactic candidates for small Lean statements, asks Lean to check candidates, and audits their axioms. It also tests a statement-only candidate policy and an ablation that renames problem IDs. A firewall rejects forward input containing prohibited oracle or candidate-body fields.

## Run the example

From the repository root, with Python 3.11 or newer and Lean available on `PATH`:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.lean_proof_search_lab evaluate-fixtures \
  --input fixtures/first_wave/engine_room_lean_proof_search_lab/input --json
```

The result reports each fixture’s observed status and whether it met the expected status. The suite includes tiny solvable statements, an oracle-field rejection, a problem-ID memorization check and a `sorry`-tainted candidate rejection. A passing fixture matrix includes these expected failures; it is not a claim that all problems were solved.

The candidates are symbolic templates, not a neural theorem prover. Lean checks the supplied tiny examples; this does not demonstrate frontier-scale automation. See [Theorem Proving in Lean 4](https://lean-lang.org/theorem_proving_in_lean4/Tactics/) for tactic construction and [Sledgehammer](https://isabelle.in.tum.de/doc/sledgehammer.pdf) for a related candidate-and-check workflow.

## Verification

With Lean on `PATH`, the positive fixture checks candidate proofs of `p → q → p ∧ q` and `p ∨ q → q ∨ p`, including an axiom audit. A successful check establishes those two propositions, not correctness of the search algorithm. This helper has no registered component replay route of its own; the Engine Room demo separately exercises it.

## Source and evidence

- [Implementation](../src/microcosm_core/engine_room/lean_proof_search_lab.py) and [focused tests](../tests/test_engine_room_lean_proof_search_lab.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_lean_proof_search_lab/input/); [historical Engine Room composition result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) (summary, not a detailed result for this individual fixture).
- [JSON record](../paper_modules/engine_room_lean_proof_search_lab.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
