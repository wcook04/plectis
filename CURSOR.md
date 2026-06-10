# CURSOR.md - Microcosm Substrate Adapter

This is a thin adapter for Cursor-style agents. The canonical public agent
contract is `AGENTS.md`; do not duplicate or override it here.

First read `AGENTS.md`. With a goal, convert it into your first correct action
(demonstrated in `FIRST_ACTION.md`); then run the bootstrap preview and card:
```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --first-action "<your goal>"
./bootstrap.sh --dry-run
PYTHONPATH=src python3 -m microcosm_core hello --reader agent .
```

This adapter does not authorize release, publication, provider calls, source
mutation, private-root equivalence, proof correctness, production use, or
financial advice.
