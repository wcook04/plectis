# Check monitor verdicts against adversarial probes

> **In plain terms.** A monitor program that watches an automated assistant for problems should be tested against deliberate attempts to fool it. This component is given example records of the watched assistant's actions, the test attacks aimed at the monitor, the monitor's observations, and how flagged problems were handled. It works out again which cases the test attacks cover and what the monitor's verdict should be, then compares both with the recorded labels. The output says whether the evidence meets the example's requirements and lists mismatches, such as a coverage claim with no matching test attack. These are fixed example records, not a live monitor, so a pass says nothing about how often a real monitor catches problems.

This replay joins public trajectory metadata, adversarial probes, monitor observations, escalation and mitigation evidence. It recomputes coverage and monitor verdicts and compares them with the recorded labels. The output identifies whether the supplied evidence satisfies the fixture contract, with findings for mismatches.

For example, a declared coverage claim without a corresponding probe is rejected. The regression tests also change evidence and verify that the computed verdict changes. The examples are bounded public replay records, not a live monitor or an estimate of a monitor’s detection rate. A passing receipt cannot establish real-world safety.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_monitor_redteam_falsification_replay \
  run --input fixtures/first_wave/agent_monitor_redteam_falsification_replay/input \
  --out .microcosm/component-guides/agent_monitor_redteam_falsification_replay/output \
  --acceptance-out .microcosm/component-guides/agent_monitor_redteam_falsification_replay/acceptance.json
```

The result records the monitor verdicts, probe coverage and findings. It is written under `.microcosm/component-guides/agent_monitor_redteam_falsification_replay/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the monitor verdict and probe checks; they do not formally prove the monitor algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported monitor bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/agent_monitor_redteam_falsification_replay.py) · [fixture input](../fixtures/first_wave/agent_monitor_redteam_falsification_replay/input/) · [tests](../tests/test_agent_monitor_redteam_falsification_replay.py) · [sample result (historical)](../receipts/first_wave/agent_monitor_redteam_falsification_replay/agent_monitor_redteam_falsification_replay_result.json) · [JSON record](agent_monitor_redteam_falsification_replay.json).

See [Red Teaming Language Models to Reduce Harms](https://arxiv.org/abs/2209.07858) for related research.
