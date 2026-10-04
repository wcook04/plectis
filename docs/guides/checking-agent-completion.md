# Checking an agent's completion report

An agent says it committed a fix and ran a test. This example checks those
statements against a disposable Git repository and an actual pytest run. It
also rejects four deliberately incorrect claims, so you can inspect both
the successful checks and the failures they catch.

## Run the example

Start in a Plectis clone with Python 3.11 or newer and Git available on your
command line. The audit needs pytest; the ordinary toolkit installation does
not include it. In a macOS/Linux shell or WSL, create an isolated environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "pytest>=8,<9"
```

If your existing environment can run `python -m pytest --version`, use it.
The source invocation below needs no Plectis package installation or model
account:

```sh
PYTHONPATH=src python -m plectis agent-closeout-faithfulness-audit run \
  --input fixtures/first_wave/agent_closeout_faithfulness_audit/input \
  --out .microcosm/examples/agent-completion
```

The command prints JSON and saves its result under the ignored `.microcosm/`
directory. Its Git operations and test run happen in a temporary copy of the
tiny [example project](../../fixtures/first_wave/agent_closeout_faithfulness_audit/input/public_fixture_repo/).
That temporary repository is removed when the audit finishes. It does not
commit to or change the source files of your checkout.

## Read the result

Open `.microcosm/examples/agent-completion/agent_closeout_faithfulness_audit_result.json`.
A successful run includes these fields:

```json
{
  "status": "pass",
  "exercise": {
    "claim_count": 3,
    "verified_claim_count": 3,
    "pytest_span_ran_count": 1,
    "pytest_pass_status_checked_count": 1
  },
  "missing_negative_cases": []
}
```

This is an excerpt, not the complete result. The three claims come from
[closeout_claims.json](../../fixtures/first_wave/agent_closeout_faithfulness_audit/input/closeout_claims.json):

| Reported claim | What the audit checks |
| --- | --- |
| A commit exists | Initializes and commits the temporary project, reads its actual Git HEAD, and compares the claim with it. |
| A work record exists | Looks for the named record in the supplied example ledger. |
| A named test passed | Runs that pytest test, checks exit code zero, and requires the claim to record that success was checked. |

Under `exercise.spans`, the addition test should have `span_ran: true`,
`passed: true`, `pass_status_checked: true`, and `returncode: 0`.
`exercise.external_witness` records the Git and pytest subprocess counts.

The same result's `negative_case_semantics` lists a nonexistent commit, a
missing ledger record, a nonexistent test, and a success claim without an
explicit status check. Each should be `blocked`. Their codes also appear in
`error_codes`: these are the expected rejected examples, so they coexist with
the overall `status: pass`. A missing pytest installation produces
`CLOSEOUT_PYTEST_UNAVAILABLE` rather than a verdict about the agent's claim.

## Inspect the check

Follow the [input claims](../../fixtures/first_wave/agent_closeout_faithfulness_audit/input/closeout_claims.json)
through the [implementation](../../src/microcosm_core/organs/agent_closeout_faithfulness_audit.py)
to the result file. The [tests](../../tests/test_agent_closeout_faithfulness_audit.py)
change the claims and check that forged commits, absent tests and unchecked
success reports are rejected. You can run them in the same environment:

```sh
PYTHONPATH=src python -m pytest tests/test_agent_closeout_faithfulness_audit.py
```

This example checks evidence in the supplied small project. It does not audit
your agent's conversation, certify an arbitrary commit or test suite, or
establish that an agent is reliable. The useful pattern is concrete: separate
what was reported, what you can locate, what you actually reran, and what passed.

Return to the [documentation index](../README.md) for other examples.
