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
change:

```bash
microcosm authority --card
microcosm stripping-guard
python3 -m pytest tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py tests/test_public_entry_docs.py
```

When reporting a suspected leak, include the path, command, receipt id, and a
short redacted description. Do not paste the suspected secret, private payload,
raw prompt body, or credential-equivalent value into the report.
