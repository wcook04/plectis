# CLI decomposition plan

The command-line interface is still implemented in one
[`cli.py`](../../src/microcosm_core/cli.py) file. Its `main()` function creates
the argument parser and selects a handler; the same file contains command
handlers, output formatting and proof-lab cache helpers. Splitting those jobs
would let a contributor read one command's implementation without searching
through the others. This is a proposal for that work. The split has not been
implemented.

## Constraints discovered in the live tree

- [`organ_surface_contract.py`](../../src/microcosm_core/projections/organ_surface_contract.py)
  reads `src/microcosm_core/cli.py` in `_cli_command_names()` and parses its
  Python syntax tree. It collects literal strings from two forms:
  `subparsers.add_parser("name", ...)` and
  `_add_bundle_parser(subparsers, "name", ...)`. The helper registers many
  commands, including `finance-forecast-evaluation-spine`; looking only for
  literal `add_parser` arguments would miss them. Keep both forms visible to
  the extractor, or update it to read their new locations. This extraction
  returns command names, not argument definitions or complete help text.
- `pyproject.toml` pins two console entry points to `microcosm_core.cli:main`
  (`plectis`, `microcosm`), and `src/plectis/cli.py` re-exports the same
  `main`. The import path `microcosm_core.cli:main` must keep working.
- [`public_entry_docs.py`](../../src/microcosm_core/validators/public_entry_docs.py)
  reads the `FIRST_SCREEN_HELP` top-level string assignment from the file
  named by `CLI_FIRST_SCREEN_HELP_REL`. Re-exporting the constant from a new
  package preserves Python imports but does not preserve this syntax-tree
  lookup. Update the reader when moving the assignment.
- The package entry points `python3 -m microcosm_core` and
  `python3 -m plectis` both call that `main`. Keep them working alongside the
  installed console commands.

## Target shape

```text
src/microcosm_core/cli/
    __init__.py      # re-exports main + FIRST_SCREEN_HELP (import-compatible)
    __main__.py      # python -m microcosm_core.cli
    _shell.py        # parse/dispatch only: argparse tree, _display_program_name
    first_screen.py  # hello / first-screen / tour text card / fast path
    cards.py         # status / authority / workingness / observe card emitters
    proof_lab.py     # proof-lab cache, receipt and card helpers
    lenses.py        # comprehend / public lens subcommands
    serve.py         # serve + observatory boundary
    evidence.py      # evidence list/inspect + receipt refs
```

This proposed grouping follows the existing functions. For example,
`_proof_lab_cache_freshness()`, `_proof_lab_cached_result()` and
`_proof_lab_first_screen_card()` belong together because the card uses the
cached result and its freshness calculation. In the proposed layout,
`main()` in `_shell.py` would assemble the parser and dispatch commands;
each command module would define its arguments and handlers.

## Gates for the split (each phase lands green)

1. Run `make ci` after each extraction phase.
2. Before moving a command, record its names and aliases, accepted arguments,
   help text, exit codes, output and files written for the cases being moved.
   Compare those observations after the move, including commands omitted
   from the short root help. Preserve the console entry points, both package
   entry points and the `microcosm_core.cli:main` import.
3. Run the existing [CLI tests](../../tests/test_cli.py) and
   [organ-surface tests](../../tests/test_organ_surface_contract.py). They test
   particular commands, help passages, output fields and missing command
   registrations. They do not compare every command's behaviour before and
   after a refactor. Add focused coverage for any moved behaviour those tests
   do not exercise.
4. Confirm that `public_entry_docs.py` can still read the `FIRST_SCREEN_HELP`
   assignment and validate its contents. A successful import alone is not
   sufficient for that reader.
5. Keep behaviour changes separate from the extraction. If a command needs a
   fix, make and test that change before moving its implementation.

## Non-goals

- No renaming of user-visible commands.
- Keep the first pass to moving existing functions. A typed command framework
  or plugin registry would need a separate proposal describing the problem it
  solves.
