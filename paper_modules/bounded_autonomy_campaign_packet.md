# Draft a bounded campaign packet

> **In plain terms.** A program that proposes its own work needs firm limits, so a person can review each proposal first. This component is given a made-up list of gaps in what a project checks, a policy of limits and a ledger of failed plans. It drafts candidate work items for people to review, each naming one gap and none allowed to change code, using the project's plan-building tool in read-only mode, which the public copy inspects rather than runs. It blocks a policy that would allow code changes, an empty draft, or a ledger listing the same failed plan more than once.

This fixture reads synthetic coverage gaps, a campaign policy and a failed-digest ledger, then drafts candidate records for human review. Each candidate names a gap and specifies no source-write surface.

When the parent campaign builder is available, the fixture invokes it as a read-only subprocess and uses its candidate count. In a standalone public checkout, it instead checks the copied builder's manifest, digest and required source anchors; the candidate count comes from the policy limit. That source-only witness does not execute the builder. The evaluator blocks a policy that permits `write_source`, a failed witness or empty packet, and duplicate failed campaign digests. A missing copied builder target also blocks the public witness.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.bounded_autonomy_campaign_packet run \
  --input fixtures/first_wave/bounded_autonomy_campaign_packet/input \
  --out .microcosm/component-guides/bounded_autonomy_campaign_packet \
  --acceptance-out .microcosm/component-guides/bounded_autonomy_campaign_packet/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

The source witness and packet checks do not formally prove the campaign builder or its decisions. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

The packet is a draft for review. The public source-only witness does not establish builder behavior. The fixture does not perform autonomous repair, execute a campaign or authorize source changes.

## Sources

[src/microcosm_core/organs/bounded_autonomy_campaign_packet.py](../src/microcosm_core/organs/bounded_autonomy_campaign_packet.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/bounded_autonomy_campaign_packet/input/), [tests](../tests/test_bounded_autonomy_campaign_packet.py), [historical sample acceptance result](../receipts/acceptance/first_wave/bounded_autonomy_campaign_packet_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). Related background: [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework).
