## Summary

- What public runtime, fixture, receipt, standard, doc, or test surface changed?
- What claim is now stronger, narrower, clearer, or deliberately removed?

## Validation

- [ ] Ran the focused tests for the touched surface.
- [ ] Ran `make ci` or explained why a narrower validation lane is sufficient.
- [ ] For source-only checks, used `PYTHONPATH=src python3 -m microcosm_core ...` or the project `.venv`, not a host interpreter by accident.
- [ ] If tracked receipts changed, I intentionally own that receipt refresh.

## Public Boundary

- [ ] No secrets, credentials, sessions, provider payload bodies, raw operator voice, private personal material, live account data, or unsafe exploit steps were added.
- [ ] No source-mutation, provider-call, hosted-release, recipient-send, financial-advice, product-readiness, proof-correctness, or production-security authority was widened.
- [ ] Synthetic fixtures are used only as regression wrappers, negative cases, or toy inputs around a real mechanism.
- [ ] Any new or stronger public claim points at runnable behavior, a validator, a receipt, or an explicit omission boundary.

## Standalone Shape

- [ ] The first useful reader path still starts with `README.md`, `QUICKSTART.md`, `AGENTS.md`, or `microcosm hello .`.
- [ ] The change keeps `release_authorized=false` unless there is a separate operator authorization receipt.
- [ ] New GitHub/source surfaces are included in `MANIFEST.in`, package data, or release export when a standalone clone needs them.
