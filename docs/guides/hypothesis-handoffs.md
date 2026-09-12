# Hypothesis handoffs

An open question is easier to answer when you write down your current guess,
what else could be true, and which observations would distinguish the options.
A hypothesis handoff is a JSON file in which the author records those choices
and a specific request for an expert. Plectis validates the file's fields and
references between records, then prints it in a readable form.

## The worked question

The [example file](../../examples/hypothesis_handoff/independent_evaluation.json)
asks whether evaluator-selected cases would expose a different Plectis failure
profile from the example cases supplied by the author. The tentative leading hypothesis
is that they would reveal more failures and more kinds of failure. The
alternatives are that the existing fixtures are approximately representative,
or that new failures would mostly concern dependencies and the environment.

The author records what each possible outcome would support. For example,
more failures in program results or validation rules would support the leading
hypothesis; a comparable failure profile under adequate coverage would support
the first alternative. An informal review could still reveal a useful defect,
but would not provide the planned comparison of case-selection methods.

This is intentionally more useful than “please evaluate the project” and
intentionally weaker than claiming that an independent evaluation has occurred.

## Run the example

Use Python 3.11 or newer from the clone root. No package installation or model
account is needed. The [quickstart](../../QUICKSTART.md#1-first-result) gives the clone
command and shell setup. In a macOS/Linux shell or WSL, run:

```sh
PYTHONPATH=src python3 -m plectis hypothesis-handoff \
  --input examples/hypothesis_handoff/independent_evaluation.json \
  --format text
```

The supplied example exits with status `0`. Its terminal output begins:

```text
Hypothesis handoff: plectis.independent_evaluation_failure_profile
Question: Would evaluator-selected cases expose a materially different failure profile from the author-selected public fixtures?
```

It then prints the recorded hypotheses, observations, expert request and files
the author proposes updating. No output file is written. With invalid input,
it exits with status `1` and prints `Hypothesis handoff: invalid` followed by
the errors. Use `--format json` to inspect the `status` and `errors` fields.

The command reads only the supplied JSON file. It makes no model calls, changes
no repository files and sends no request to an expert. A successful exit means
the records satisfy the rules below; it does not answer the research question.

## What the validator compares

In the file, a *discriminator* is a proposed observation or experiment that
the author thinks would distinguish hypotheses. A *result map* lists possible
outcomes and the hypothesis IDs each would support.

The [validator](../../src/microcosm_core/hypothesis_handoff.py) requires:

- nonempty required fields, a leading hypothesis marked `tentative`, and
  entries describing support and contrary or missing observations;
- each `distinguished_by` ID to name a row in `discriminating_evidence`, with
  an outcome in that row referring back to the hypothesis;
- each outcome's `supports_hypothesis_ids` to name recorded hypotheses, and
  each discriminator's outcomes to refer to at least two different hypotheses;
- each proposed update path in `expert_return.landing_targets` to be relative,
  contain no `..` path component and occur only once; and
- `landing_order` and `status_change_rule` to match the prescribed text: record
  the argument or observations, independently verify them, update the claim
  record, then regenerate the public documents and run release validation.

For example, `hypothesis.independent_cases_find_more_failures` names
`discriminator.preregistered_case_selection` in `distinguished_by`. That
discriminator's result map must contain an outcome whose
`supports_hypothesis_ids` includes the hypothesis ID.

These are comparisons of supplied fields. A person still has to judge whether
the proposed experiment distinguishes the hypotheses and whether the cited
observations support them. The command does not open cited sources, resolve
target paths on disk or run the validator commands listed beside those paths.
It compares the prescribed order as text; it does not perform those steps.

## Prepare a handoff

Use the example's structure to record your question, tentative answer,
alternatives, proposed observations and expert request. Name the files you
would update after reviewing a response, and the commands you would run to
validate those updates. Keep the original handoff with its date or commit so
you can compare later revisions with the choices made before the outcome.

Your current expectation is not itself evidence. The command does not estimate
a probability or change a claim's status. Independently verify and review an
expert's response before using it to change a public claim. The `declared_gap`
field describes one known gap, following the
[Self-Ignorance Coverage Ledger](../../paper_modules/self_ignorance_coverage_ledger.md):
naming one known gap must never imply that no other gap exists.

The [existing tests](../../tests/test_hypothesis_handoff.py) include invalid IDs,
missing outcomes and paths containing `..`. For other examples, return to the
[documentation index](../README.md).
