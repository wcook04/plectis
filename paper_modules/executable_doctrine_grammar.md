# Validate standards and paper-module grammar

> **In plain terms.** A project's written rules and explanatory pages should follow a fixed format. This check reads a list of the written rules, a set of short pages and some deliberately flawed example inputs. It checks that every rule and page has the required fields and that its references lead somewhere real, and it expects to catch the flawed examples, such as a rule name used twice with conflicting definitions. It writes a list of findings and a summary of what it covered, so problems can be found and fixed. A pass means the expected bad cases were caught, not that every example is valid or that the written guidance is complete.

The validator reads a standards registry and Markdown module fixtures, checks their required fields and references, and writes findings and coverage summaries. The fixture run also expects deliberately invalid cases to be detected. For example, a standard that claims prose is executable authority is rejected, as is a duplicate standard slug with conflicting definitions.

A passing fixture run means the expected negative cases were observed and the input scan passed; it does not mean every example input is valid or that the doctrine is complete. The exported metabolism bundle also checks imported-source digests; those checks establish byte identity, not correctness of the imported algorithms.

## Run the example

Python 3.11 or later is required. From the repository root, use the Python API to direct both result and acceptance output into ignored local state. The CLI does not expose the acceptance path for this action.

```bash
PYTHONPATH=src python3 - <<'PYCODE'
from microcosm_core.organs.executable_doctrine_grammar import validate
result = validate('fixtures/first_wave/executable_doctrine_grammar/input', '.microcosm/component-guides/executable_doctrine_grammar', acceptance_out='.microcosm/component-guides/executable_doctrine_grammar/acceptance.json')
print(result['status'])
PYCODE
```

## Verification

The tests exercise grammar checks and rejected fixtures; they do not prove the validator. `make component-replays` runs the exported standards bundle through the [shared Dafny admission check](../formal/replay/README.md), which checks agreement of supplied source, input, claim policy and receipt observations. The direct example does not invoke that admission gate.

## Source

[Implementation](../src/microcosm_core/organs/executable_doctrine_grammar.py) · [Input](../fixtures/first_wave/executable_doctrine_grammar/input) · [Tests](../tests/test_executable_doctrine_grammar.py) · [Historical sample](../receipts/acceptance/first_wave/executable_doctrine_grammar_fixture_acceptance.json) · [JSON record](executable_doctrine_grammar.json)

[JSON Schema](https://json-schema.org/specification) is useful background for structured validation; this fixture implements its own checks.
