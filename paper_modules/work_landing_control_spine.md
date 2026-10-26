# Validate the work-landing control bundle

This helper checks an exported bundle of work-landing control source files, a manifest and a runtime contract. It writes a report on the bundle’s declared source bindings and boundaries. This source-level helper is not a separately registered component; the related registered component is the macro projection import protocol.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 - <<'PY'
from microcosm_core.macro_tools.work_landing_control_spine import validate_work_landing_control_bundle
r = validate_work_landing_control_bundle(
    'examples/work_landing_control_spine/exported_work_landing_control_bundle',
    '.microcosm/component-guides/work_landing_control_spine',
)
print(r['status'])
PY
```

The command writes local output under `.microcosm/component-guides/`. A local run passed: it checked five source modules with no missing anchors and a passing secret scan. The linked sample receipt is historical; inspect a new result for the current findings.

## What this checks

The validator compares the required source-module roster, digests, line counts and anchors, then checks contract flags. The tests specify rejection of manifest drift and claims of authority the bundle does not have. Digest agreement establishes a recorded byte match, not correctness of the copied code.

## Limits

The helper validates an exported bundle; it does not perform a live Git commit, mutate a task ledger or authorize publication.

## Verification

The helper checks the bundle’s manifest, source files and contract, and has focused tests. No component-specific formal proof or separate replay admission route is established for this helper. The registered macro projection import protocol has its own replay route; that route does not establish correctness of this helper.

## Source

[Implementation](../src/microcosm_core/macro_tools/work_landing_control_spine.py) · [Example input](../examples/work_landing_control_spine/exported_work_landing_control_bundle/) · [Tests](../tests/test_work_landing_control_spine.py) · [Historical sample result](../receipts/first_wave/work_landing_control_spine/exported_work_landing_control_bundle_validation_result.json) · [JSON record](work_landing_control_spine.json)

Background: [Git recording changes](https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository).
