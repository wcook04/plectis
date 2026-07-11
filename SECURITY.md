# Security

Plectis is a local research prototype and developer tool, not a production
security product. A passing receipt proves only the command, fixture boundary,
and contract named in that receipt.

## Supported versions

The latest tagged release and the current `main` branch. There is no bug
bounty (this is an unfunded solo student project).

## Reporting privately

Use GitHub Private Vulnerability Reporting on this repository:

```text
https://github.com/wcook04/plectis/security/advisories/new
```

If the "Report a vulnerability" button is not visible on the Security page, do
not open a public issue with vulnerability details; hold the report until the
private route is available. No `security@` email route is published yet.
Reports get a best-effort response from a solo maintainer, normally within a
week.

## What to report

Report an issue if public Plectis material appears to expose or authorize:

- real secrets, credentials, tokens, cookies, private keys, or account
  sessions;
- raw operator voice, private personal material, or provider payload bodies;
- live external targets, live account access, or credentialed provider calls;
- source mutation, publication, or hosted-release authority that is not
  explicitly scoped as a negative fixture;
- unsafe exploit instructions instead of synthetic replay cases.

Synthetic fixtures named credential/payload/secret are not automatically
leaks: they are allowed as negative cases when the surrounding receipt keeps
the unsafe body out of public output.

## What to include

The path, the command, the receipt id, and a short redacted description.
Do not paste the suspected secret, private payload, raw prompt body, or
credential-equivalent value into the report, and do not attach local
validation byproducts (venv directories, `.microcosm/`, pytest caches).

Before reporting a release-boundary or authority issue, the local verification
route (including the release-authority receipt fields a report should cite) is
documented in
[docs/maintainers/security-runbook.md](docs/maintainers/security-runbook.md);
the README's [Choose a route](README.md#choose-a-route) table names the public
surfaces reports should reference.
