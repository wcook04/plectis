# Lean Proof-Search Lab Runtime - exported bundle

This bundle accompanies the `lean_proof_search_lab_runtime` organ. The organ surfaces the public `lean_proof_search_lab` engine-room capsule as a first-class gated external-tool organ.

## What the mechanism does

A small, runnable proof-search lab for toy logic theorems, checked by the real Lean theorem prover. For each toy theorem it searches over candidate tactic scripts, compiles each one with Lean, and keeps a script only when Lean actually closes the proof. It refuses three ways of cheating: forwarding a ready-made proof body (an oracle leak), leaning on `sorry` or extra axioms (an unclean proof), and a policy that only picks the right tactic because it recognised the problem's name (memorisation, caught by renaming the problem). It shows one honest search succeeding and four cheats being rejected. Lean is optional: install it to unlock the real run; without it the lab reports itself locked and claims nothing, rather than pretending to have proved anything.

## What it does not claim

Real-substrate external-tool witness over bounded public toy theorems. A pass attests only that the installed Lean subprocess closed the toy positive theorems and rejected the planted oracle-leak, axiom-taint, and problem-id-memorisation negatives on these fixtures. It does NOT prove any open mathematical problem, is NOT neural theorem proving, does NOT forward oracle proof bodies, is NOT an oracle/prover authority, and does NOT authorize release, publication, production use, or source mutation. When Lean is absent the organ is locked and attests nothing at all.

## Locked vs unlocked (Lean is an optional dependency)

This capability is shipped but dependency-gated. On a base install with no Lean, the organ reports itself **locked** (`tool_state=tool_missing`) and verifies nothing - it never fakes a pass and never counts the absence as a proof failure. Install Lean 4 so the `lean` binary is on PATH (the elan version manager places `lean` and `lake` on PATH and selects the toolchain named by a project's lean-toolchain file; see https://lean-lang.org/install/), then re-run: the same command runs the real proof-search subprocess and reports `tool_present_and_verified`. An installed-but-failing Lean is a real failure (`tool_present_but_failed`); a missing Lean is not.

## Fixture cases

- `positive_symbolic_lab_pass.json` - the real lean subprocess closes two toy theorems (lab_and_intro, lab_or_comm) via and/or search with a clean axiom audit and a passing problem-id ablation (positive).
- `oracle_field_negative.json` - a problem row forwards a forbidden oracle field; the forward firewall rejects it with oracle_firewall_violation (negative).
- `nested_oracle_field_negative.json` - a nested payload smuggles forbidden oracle fields; the firewall walks the nested paths and rejects with oracle_firewall_violation (negative).
- `sorry_axiom_negative.json` - a candidate leans on `sorry`; the #print axioms cleanliness gate rejects it with axiom_taint_detected (negative).
- `memorized_policy_negative.json` - a policy only picks the right tactic because it memorised the problem id; renaming the id fails the ablation with problem_id_ablation_failure (negative).

## Run it

```bash
python -m microcosm_core.organs.lean_proof_search_lab_runtime run \
  --input fixtures/first_wave/lean_proof_search_lab_runtime/input \
  --out receipts/first_wave/lean_proof_search_lab_runtime
```
