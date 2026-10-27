# Check a checkout's first run

The cold-clone probe runs a small checkout test before installation. It checks that the required pattern-binding inputs are readable, runs the configured secret-exclusion scan, validates the pattern-binding example and records the result as JSON.

## Run the example

From the repository root, with Python 3.11 or later:

```bash
./bootstrap.sh --suite first-wave --emit .microcosm/component-guides/cold_clone_probe.json
```

The bootstrap script imports the package from `src/`. The probe writes its pattern-binding results under `.microcosm/cold_clone_probe/` and the requested summary under `.microcosm/component-guides/`. If historical pattern-binding result files are missing, it also copies the newly generated files into the expected `receipts/first_wave/pattern_binding_contract/` locations; existing files are left in place.

## What this checks

`run_probe` stops before validation if required inputs are missing. A failed exclusion scan produces `blocked_secret_exclusion`; a missing or failed pattern-binding result produces a dependency error. Tests cover unreadable paths, missing generated files and duplicate JSON keys in a copied validation result. Only the `first-wave` suite is supported: an unknown suite passed to the Python API returns `UNKNOWN_COLD_CLONE_SUITE`.

## Limits

This is one example's bootstrap check. It does not install the package, run the full test suite or establish release readiness. A pass includes the configured scan result, whose coverage depends on its rules.

## Verification

The probe is tested by the linked regression tests and runs its configured scan and pattern-binding example. It has no component-specific formal proof or registered component replay route. A passing scan and fixture check do not prove the probe algorithm correct.

## Sources

- [Bootstrap script](../bootstrap.sh) and [probe implementation](../src/microcosm_core/cold_clone_probe.py).
- [Pattern-binding inputs](../fixtures/first_wave/pattern_binding_contract/input), [historical example result](../receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json) and [tests](../tests/test_cold_clone_probe.py).
- [Canonical description](../core/paper_module_capsules.json); [reproducible-build guidance](https://reproducible-builds.org/docs/) gives broader context.
