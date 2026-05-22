# Verifier Lab Kernel

`verifier_lab_kernel` is the public composition root for the formal-math
verifier lab. It is not a theorem prover, a benchmark runner, a private Lean
import, or a frontend surface. It composes already-public Microcosm organs into
one leak-proof receipt so a reader can see which claim came from a verifier,
which claim came from an oracle comparator, which claim came from a provider
hypothesis, and which rows were rejected by contract.

The organ consumes:

- a public `ForwardProblem` packet with target shape, statement summary,
  public input hash, and allowed premise ids;
- an `OracleSidecar` packet that may compare against hidden or hindsight
  knowledge but never increments forward success;
- verifier attempts and verifier result classes;
- provider/NIM hypotheses as advisory residual diagnoses only;
- CP2 typed action candidates, not proof bodies or raw tactic scripts;
- bounded Evolve candidates over policy artifacts only.

The runnable fixture also calls the existing public components:

- `tactic_portfolio_availability_probe`;
- `target_shape_tactic_routing_gate`;
- `formal_math_verifier_trace_repair_loop`;
- `formal_math_lean_proof_witness`.

The acceptance receipt must separate these buckets:

- `lean_verified`;
- `provider_suggested`;
- `oracle_compared`;
- `contract_rejected`;
- `retrieval_miss`;
- `cp2_translated`;
- `evolve_candidate`.

The kernel rejects five contract failures:

- forward problems that carry candidate, ideal, repair, oracle, source proof,
  proof body, or base-index fields;
- oracle comparator success counted as forward success;
- provider hypotheses claiming proof authority;
- CP2 candidates carrying proof bodies, raw tactic scripts, provider bodies, or
  oracle templates;
- Evolve candidates mutating anything outside the bounded policy-artifact set.

Authority ceiling: this paper module describes public fixture and exported
bundle receipts only. It does not authorize private proof-body import,
Mathlib-dependent proof authority, oracle-to-forward success, provider proof
authority, CP2 proof bodies, arbitrary Evolve mutation, source mutation,
benchmark solve-rate claims, release, publication, hosted deployment, or
private-data equivalence.
