# CLI decomposition plan

`src/microcosm_core/cli.py` is a single ~5,100-line module: 65 top-level
functions, 48 `add_parser` registrations, and `main()` at the bottom doing
parse-and-dispatch. It works and is tested, but a reviewer cannot find a
command, follow its dispatch, and test it without traversing one multipurpose
file. This is the owned plan for splitting it; it is deliberately a follow-on
to the public-surface normalisation, not part of it.

## Constraints discovered in the live tree

- `projections/organ_surface_contract.py` parses `src/microcosm_core/cli.py`
  with `ast` to extract the `add_parser` first-arguments as the command-name
  contract. Any split must either keep a single parse target for that
  extraction or update the extractor to walk the new package.
- `pyproject.toml` pins two console entry points to `microcosm_core.cli:main`
  (`plectis`, `microcosm`), and `src/plectis/cli.py` re-exports the same
  `main`. The import path `microcosm_core.cli:main` must keep working.
- `validators/public_entry_docs.py` reads the `FIRST_SCREEN_HELP` top-level
  string assignment out of `cli.py` by `ast` (`CLI_FIRST_SCREEN_HELP_REL`).
  The constant's home must move in lockstep with that validator.
- Makefile smoke targets and many tests invoke `python3 -m microcosm_core`
  (package `__main__`), which must keep dispatching to the same `main`.

## Target shape

```text
src/microcosm_core/cli/
    __init__.py      # re-exports main + FIRST_SCREEN_HELP (import-compatible)
    __main__.py      # python -m microcosm_core.cli
    _shell.py        # parse/dispatch only: argparse tree, _display_program_name
    first_screen.py  # hello / first-screen / tour text card / fast path
    cards.py         # status / authority / workingness / observe card emitters
    proof_lab.py     # the ~20 proof-lab cache/receipt helpers (lines 1363-2460 today)
    lenses.py        # comprehend / public lens subcommands
    serve.py         # serve + observatory boundary
    evidence.py      # evidence list/inspect + receipt refs
```

Grouping follows the live helper clusters (the proof-lab helper block is the
largest single extraction). `main()` stays thin in `_shell.py`; command groups
own their arguments and handlers.

## Gates for the split (each phase lands green)

1. `make ci` (public floor) after every extraction phase.
2. `tests/test_cli.py` and the organ-surface contract test prove the command
   registry is unchanged (same `add_parser` set, same help text).
3. `validators/public_entry_docs.py` first-screen help contract still resolves
   `FIRST_SCREEN_HELP`.
4. No behaviour change: this is a mechanical decomposition; any behavioural
   fix found on the way lands separately first.

## Non-goals

- No renaming of user-visible commands.
- No new abstractions (typed command framework, plugin registry) in the first
  pass; structure first, machinery only if a later need proves it.
