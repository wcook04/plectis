# Copilot Instructions - Microcosm Substrate Adapter

This is a thin adapter for GitHub Copilot, which may load it beside `AGENTS.md`,
`CLAUDE.md`, and `GEMINI.md` in no fixed order, so it states no rule of its own:
`AGENTS.override.md` is the compact cold-clone entry and `AGENTS.md` remains the
deep public mutation contract, and those two settle any disagreement.

First read `AGENTS.md` only after the compact task router names a deep section.
With a goal, convert it into your first correct action (demonstrated in
`FIRST_ACTION.md`); then run the bootstrap preview and card:
```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --first-action "<your goal>" --format text
./bootstrap.sh --dry-run
PYTHONPATH=src python3 -m microcosm_core hello --reader agent .
```

This adapter does not authorize release, publication, provider calls, source
mutation, private-root equivalence, proof correctness, production use, or
financial advice.
