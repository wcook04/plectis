# Tactic Portfolio Availability Probe

`tactic_portfolio_availability_probe` is the public organ that turns tactic
callability into an explicit artifact before routing or proof search treats a
tactic as usable.

The fixture is copied from real non-secret macro substrate: the 2026-05-11
`PROVER_PROOF_STATE_SEARCH_CURRICULUM` smoke run's Lean/Std tactic affordance
probe. It records compile-status rows for `rfl`, `decide`, `omega`, `simp`,
`simp_all`, `grind`, `native_decide`, and `aesop`, with source digests for the
run-level affordance probe, the `portfolio_core_v0` tactic availability artifact,
and the paired corpus-readiness boundary. The Mathlib-dependent `aesop` row is
marked `environment_fail` because the paired environment probe reports
`mathlib_lake_project_import_available=false`.

The organ validates:

- every tactic has an environment-scoped `compile_status`;
- Mathlib-dependent tactics are not marked available without a passing Mathlib
  import probe;
- downstream consumers reference only tactics present in the probe portfolio;
- proof bodies, raw provider payloads, benchmark claims, release authority, and
  private paths stay out of the public artifact.

The generated board is a callability map, not proof evidence. It can make
target-shape routing cheaper and more honest, but it cannot prove a goal, widen
Lean/Lake authority, call providers, claim benchmark performance, or authorize
release.

The receipt contract reports
`body_material_status=copied_non_secret_macro_body_with_provenance`,
`tactic_availability_status=real_lean_std_tactic_affordance_probe_rows`, source
digests, target refs, and `secret_exclusion_scan`. It does not use body-redaction
or private-state-scan grammar as product evidence.

Primary commands:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.tactic_portfolio_availability_probe run --input fixtures/first_wave/tactic_portfolio_availability_probe/input --out receipts/first_wave/tactic_portfolio_availability_probe --acceptance-out receipts/acceptance/first_wave/tactic_portfolio_availability_probe_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli tactic-portfolio-availability-probe run-availability-bundle --input examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle --out receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe
```
