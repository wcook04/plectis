# Tactic Portfolio Availability Probe

`tactic_portfolio_availability_probe` is the public organ that turns tactic
callability into an explicit artifact before routing or proof search treats a
tactic as usable.

The fixture is synthetic and source-available. It records a small Lean/Std tactic
portfolio with compile-status metadata for `rfl`, `decide`, `omega`, `simp`,
`simp_all`, `grind`, `native_decide`, and `aesop`. The Mathlib-dependent
`aesop` row is marked `environment_fail` because the paired environment probe
reports `mathlib_lake_project_import_available=false`.

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

Primary commands:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.tactic_portfolio_availability_probe run --input fixtures/first_wave/tactic_portfolio_availability_probe/input --out receipts/first_wave/tactic_portfolio_availability_probe --acceptance-out receipts/acceptance/first_wave/tactic_portfolio_availability_probe_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli tactic-portfolio-availability-probe run-availability-bundle --input examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle --out receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe
```
