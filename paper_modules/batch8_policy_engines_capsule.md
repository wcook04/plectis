# Exercise three policy decisions

> **In plain terms.** Programs that allow or refuse an action need their rules tested on known cases. This check loads three copied decision rules and feeds them made-up cases, including lab result files, an unregistered market situation and campaign status changes. The lab audit flags a summary containing a question mark, the market gate refuses the unregistered situation, and the campaign check allows a move from candidate to blocked but refuses completed back to running. The refusals come from running the copied code, not from a label declaring an error, and a saved status reports the outcome. The examples do not show that lab output is right, live market claims are valid or campaigns are safe to run.

The fixture loads three copied policy engines and applies them to synthetic artifacts. The Lab audit checks JSON artifacts written by its compute nodes, such as cross-correlation summaries. It reports green for the prepared artifacts and red when a summary contains a question mark. The market readiness gate refuses an unregistered situation with `candidate_situation_gate_missing`. The campaign transition check accepts `candidate` to `blocked`, treats `completed` to `completed` as already at target, and refuses `completed` to `running`.

These are concrete checks of particular decisions. The negative cases derive their verdicts from the copied functions rather than accepting a declared error label as proof.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_policy_engines_capsule run \
  --input fixtures/first_wave/batch8_policy_engines_capsule/input \
  --out .microcosm/component-guides/batch8_policy_engines_capsule \
  --acceptance-out .microcosm/component-guides/batch8_policy_engines_capsule/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

The synthetic decision tests do not formally prove the policy engines. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

The examples do not establish the semantic correctness of Lab output, the validity of live market claims, or the safety of campaign execution.

## Sources

[src/microcosm_core/organs/batch8_policy_engines_capsule.py](../src/microcosm_core/organs/batch8_policy_engines_capsule.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/batch8_policy_engines_capsule/input/), [tests](../tests/test_batch8_policy_engines_capsule.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch8_policy_engines_capsule_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). For policy-engine context, see [Open Policy Agent](https://www.openpolicyagent.org/docs/latest).
