<!--
SPDX-FileCopyrightText: 2026 Will Cook
SPDX-License-Identifier: CC-BY-4.0
-->

# Claim-against-check audit: frozen protocol

This file fixes the method **before** the audit is run, so that the ordering is
on the public record. Nothing below may be revised after results are seen; if
the method turns out to be wrong, the revision is recorded as a dated amendment
underneath, with the reason, and the original stays.

Written: 26 July 2026, before any component was coded.

## The question

For each registered component, does the rule the code actually enforces support
the claim the public prose actually makes?

This is the gap the paper has previously only asserted could exist. The audit
either finds it or does not.

## Population

All components in `core/organ_registry.json::implemented_organs` at the audited
commit. Not a sample. There is no selection step, so there is nothing for the
author to have selected. Components whose source file is absent are reported as
such rather than dropped.

## What is compared

For each component, exactly three texts:

1. **The public prose claim.** The component's row in `ORGANS.md` ("what it
   makes visible") together with its `classification_basis` in the registry.
   This is what a reader who does not open the code is told.
2. **The declared ceiling.** The component's `claim_ceiling` field.
3. **The enforced rule.** What the component's validator source actually
   computes, established by reading the check functions, not by reading their
   names or their return-field labels.

## Verdict vocabulary, fixed in advance

Each component receives exactly one verdict.

| Verdict | Definition |
|---|---|
| `check_matches_claim` | The enforced rule tests the property the public prose describes. |
| `claim_above_check` | The public prose describes a property stronger than the rule enforces. A behaviour-preserving rewrite of the subject would fail the check, or a subject that does not have the described property would pass it. |
| `claim_below_check` | The rule enforces more than the public prose claims. The description undersells the mechanism. |
| `ceiling_repairs_claim` | The prose reads stronger than the rule, but the component's own `claim_ceiling` states the narrower truth. The gap exists in the description and is closed in the declared limit. |
| `not_assessable` | The comparison cannot be made from public material alone. Reason required. |

`ceiling_repairs_claim` is deliberately separated from both `check_matches_claim`
and `claim_above_check`. It is the verdict that tests whether the ceiling field
— the paper's central mechanism — is doing its job. If the mechanism works,
this category should be populated; if it is empty while `claim_above_check` is
large, the mechanism is decorative.

## Required evidence per component

A verdict without all four of these is discarded and recoded:

- the quoted public prose,
- the quoted claim ceiling,
- the file and line range of the check function that decides the verdict,
- one sentence naming a concrete input or subject state that would separate the
  claim from the check (for `claim_above_check`), or an explicit statement that
  no such separating case was found (for `check_matches_claim`).

## Check-strength labels, applied independently of the verdict

Recorded per component, and more than one may apply:

- `text_presence` — a literal substring test against source text that is never
  executed.
- `existence_or_digest` — a file must be present, or its hash must match.
- `schema_shape` — parsed data must have declared keys or types.
- `recomputation` — a value is derived and compared against a separately
  supplied one.
- `external_tool` — a named external program is invoked and its result used.

## Declared biases and limits of this audit

- **The author designed the components, the prose, the ceilings, and this
  protocol.** Every safeguard here is one the audited party chose. The audit
  can find overreach; it cannot establish that it found all of it.
- **Coding is judgement, not measurement.** Two readers may differ on
  `claim_above_check` versus `ceiling_repairs_claim` in particular. Per-component
  evidence is published so a disagreement can be pointed at a specific line.
- **No inter-rater reliability is claimed.** One coding pass is performed. A
  second independent coder is the obvious next step and has not been done.
- **A verdict is about the description-to-rule fit, not about correctness.** A
  component may be coded `check_matches_claim` and still compute the wrong
  answer.

## What would falsify the paper's central mechanism

Declared in advance, so the result cannot be reinterpreted afterwards:

- If `claim_above_check` is common **and** `ceiling_repairs_claim` is rare, the
  ceiling field is not catching overreach and the mechanism does not work as
  advertised.
- If `text_presence` is a component's only check strength while its public prose
  describes behaviour, that component's evidence is weaker than its description
  regardless of its verdict.

## Reproduction

The population, the per-component evidence, and the verdicts are published in
`paper/audit_claim_against_check.json`. The registry fields are readable with:

```
python3 -c "import json;print(len(json.load(open('core/organ_registry.json'))['implemented_organs']))"
```
