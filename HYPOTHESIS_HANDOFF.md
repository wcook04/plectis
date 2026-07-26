# Hypothesis handoffs

An open question is easier to answer when the project exposes what it currently
thinks, what else could be true, and which evidence would separate the options.
Plectis calls that object a hypothesis handoff.

A valid packet contains:

- one declared known gap with source references and an explicit refusal to
  claim that every unknown question has been inventoried;
- a tentative leading hypothesis, with evidence for and evidence still missing;
- serious alternatives, each wired to named discriminators;
- result maps naming which options each possible observation would support;
- an exact request for an expert, including decisive and route-only returns;
- repository-relative landing targets with their validators and a checked
  landing order; and
- an authority ceiling that prevents a guess or expert response becoming a
  public claim automatically.

Validate the worked example from a source checkout:

```sh
PYTHONPATH=src python3 -m plectis hypothesis-handoff \
  --input examples/hypothesis_handoff/independent_evaluation.json \
  --format text
```

The command reads only the supplied JSON file. It does not call a model, mutate
the repository, score an expert, infer probabilities, or change claim status.
Its output is a validation and reading card, not an answer to the question.

The current project expectation is not counted as evidence. The value of
declaring it is that a later result cannot silently redefine the alternatives
or the update rule after the outcome is known. The validator checks that every
option is connected to a real discriminator, that every result points back to
a named option, and that the landing targets cannot escape the repository.
The declared-gap field applies the same bounded self-ignorance rule as the
[Self-Ignorance Coverage Ledger](paper_modules/self_ignorance_coverage_ledger.md):
naming one known gap must never imply that no other gap exists.

The worked packet asks whether evaluator-selected cases would expose a
different Plectis failure profile from the author-selected fixtures. Its
leading hypothesis is visible, but so are the evidence against it and two
outcomes that would displace it. This is intentionally more useful than
“please evaluate the project” and intentionally weaker than claiming that an
independent evaluation has occurred.
