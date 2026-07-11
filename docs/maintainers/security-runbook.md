# Security runbook (maintainers and reporters)

The public reporting contract is [SECURITY.md](../../SECURITY.md). This
runbook is the deeper verification lane for boundary reports.

## Local checks before reporting

Start with the source-root probe, then the boundary cards and the focused
tests:

```bash
./bootstrap.sh
VENV=/tmp/plectis-security-venv make install
/tmp/plectis-security-venv/bin/plectis authority --card
/tmp/plectis-security-venv/bin/plectis stripping-guard
PYTHONPATH=src /tmp/plectis-security-venv/bin/python -m pytest tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py tests/test_public_entry_docs.py --basetemp=/tmp/plectis-security-bt
```

`bootstrap.sh` writes ignored `.microcosm/cold_clone_probe.json` evidence and
does not refresh tracked receipts; `./bootstrap.sh --dry-run` previews the
exact command without writing anything. If you are not using the Makefile
wrapper, create the same environment explicitly outside the checkout:

```bash
python3 -m venv /tmp/plectis-security-venv
/tmp/plectis-security-venv/bin/python -m pip install -e '.[test]'
```

## Release-authority reports

If the suspected boundary failure is that a public surface implies release,
publication, hosting, or provider authority, create a bounded release receipt
first:

```bash
make standalone-export EXPORT_OUT=/tmp/plectis-security-boundary-export
```

Inspect `receipts/release/release_export_receipt.json` inside the exported
tree and include the receipt id, artifact hash, blocking codes, and release
gate fields in the report. The expected public boundary is:

- `authority_receipt.release_authorized=false`
- `authority_receipt.publish_authorized=false`
- `release_candidate_packet.authority_state.release_authorization_gate.invoked=false`
- `release_candidate_packet.release_authorization_gate_decision.release_authorization_allowed_now=false`

If a report claims release approval exists, it must name the separate operator
authorization receipt that changed those fields. The release receipt path is
the evidence handle; raw environment state is not. For suspected
release-boundary, hosted-header, CI/supply-chain, or unsafe exploit-content
issues, include expected versus observed boundary and the smallest redacted
reproduction detail that does not expose private state or live-target exploit
steps.
