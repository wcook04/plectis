# Audit claims about a completed task

This audit checks structured claims about a commit, a ledger entry and a test against a public fixture. It copies the fixture repository into a temporary directory, uses Git to create and inspect its HEAD, and runs the named pytest test. A test-pass claim needs both a zero exit status and an explicit indication that the status was checked. The ledger claim is checked against the supplied fixture ledger.

For example, a commit reference that does not match the temporary repository HEAD is rejected. A missing pytest node or an unchecked pass claim is also rejected. The audit evaluates structured fixture claims; it does not read arbitrary closeout prose or verify a real project’s ledger or deployment.

The example requires Git and a Python interpreter with pytest available; install the repository’s test dependencies with `python3 -m pip install -e '.[test]'` if needed. The runner probes for a pytest-capable interpreter and blocks the pytest lane if none is available.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_closeout_faithfulness_audit \
  run --input fixtures/first_wave/agent_closeout_faithfulness_audit/input \
  --out .microcosm/component-guides/agent_closeout_faithfulness_audit/output \
  --acceptance-out .microcosm/component-guides/agent_closeout_faithfulness_audit/acceptance.json
```

The result records which claims were verified and whether the pytest span ran and passed. It is written under `.microcosm/component-guides/agent_closeout_faithfulness_audit/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the commit, ledger and subprocess checks; they do not formally prove the closeout audit algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported closeout bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/agent_closeout_faithfulness_audit.py) · [fixture input](../fixtures/first_wave/agent_closeout_faithfulness_audit/input/) · [tests](../tests/test_agent_closeout_faithfulness_audit.py) · [sample result (historical)](../receipts/first_wave/agent_closeout_faithfulness_audit/agent_closeout_faithfulness_audit_result.json) · [JSON record](agent_closeout_faithfulness_audit.json).

[FEVER](https://arxiv.org/abs/1803.05355) is related work on evidence-backed claims.
