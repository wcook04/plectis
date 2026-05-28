# Security And Public Boundary

Microcosm is a public-safe research runtime, not a production security product.
A passing receipt proves only the command, fixture boundary, and
contract named in that receipt. It does not grant release, hosting, provider
execution, private-root equivalence, proof-correctness, or production security
authority.

## Reportable Boundary Failures

Report an issue if public Microcosm material appears to expose or authorize:

- real secrets, credentials, tokens, cookies, private keys, or account sessions,
- raw operator voice, private personal material, or provider payload bodies,
- live external targets, live account access, or credentialed provider calls,
- source mutation, publication, recipient-send, financial-advice, or hosted
  release authority that is not explicitly scoped as a negative fixture,
- unsafe exploit instructions or live attack steps instead of synthetic replay
  cases and bounded policy receipts.

Synthetic fixtures with names such as credential, payload, secret, or private
are not automatically leaks. They are allowed only when the fixture is a
negative case and the surrounding receipt keeps the unsafe body out of public
output.

## Useful Local Checks

Run these from `microcosm-substrate/` before reporting or accepting a boundary
change. Install the repository-local test extra first so the pytest route uses
the same standalone environment as the public repo:

```bash
make install
.venv/bin/microcosm authority --card
.venv/bin/microcosm stripping-guard
PYTHONPATH=src .venv/bin/python -m pytest tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py tests/test_public_entry_docs.py
```

If you are not using the Makefile wrapper, create the same local test
environment explicitly:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

If the `microcosm` console command is not available yet and you only need the
card checks, use the source form without changing the check boundary:

```bash
PYTHONPATH=src python3 -m microcosm_core authority --card
PYTHONPATH=src python3 -m microcosm_core stripping-guard
```

## Release-Authority Reports

If the suspected boundary failure is that a public surface implies release,
publication, hosting, or provider authority, create a bounded release receipt
before reporting it:

```bash
make standalone-export EXPORT_OUT=/tmp/microcosm-security-boundary-export
```

Inspect
`/tmp/microcosm-security-boundary-export/microcosm-substrate/receipts/release/release_export_receipt.json`
and include the receipt id, artifact hash, blocking codes, and release gate
fields in the report. The expected public boundary is:

- `authority_receipt.release_authorized=false`
- `authority_receipt.publish_authorized=false`
- `release_candidate_packet.authority_state.release_authorization_gate.invoked=false`
- `release_candidate_packet.release_authorization_gate_decision.release_authorization_allowed_now=false`

If a report claims release approval exists, it must name the separate operator
authorization receipt that changed those fields.

Do not attach local validation byproducts such as `.venv/`, `.microcosm/`, or
pytest caches to a public report. The release receipt path is the evidence
handle; raw environment state is not.

When reporting a suspected leak, include the path, command, receipt id, and a
short redacted description. Do not paste the suspected secret, private payload,
raw prompt body, or credential-equivalent value into the report.
