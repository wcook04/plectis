# Compile a mixed report into a public-only job

Write a fixed report recipe with public and internal output. `plectis.views`
checks it against the application's field policy, removes internal work and
runs the resulting public program without receiving private record values.
The actual checker, transformation and interpreter are generated from the
[Dafny source](../../formal/views/Release.dfy).

Try the two self-contained examples from the clone root with Python 3.11+:

```sh
PYTHONPATH=src python3 examples/operations/public_views_recipe_change.py
PYTHONPATH=src python3 examples/operations/public_views_sqlite.py
```

The first changes a public report line from `passed` to `approved` and compares
full reference execution with the compiled public output. A further edit that
makes the public line depend on a private flag is refused. The full reference
runner is a development helper using synthetic data; it is separate from the
public API. The SQLite example queries only public columns and checks an
independently chosen expected report. An ordinary public-only renderer matches
both: confidentiality alone does not require this compiler. The candidate value
is preserving output across changes to one mixed recipe; maintenance savings
and external demand remain unmeasured.

Use the [virtual-environment installation or copy-only instructions](../../examples/operations/README.md)
to add the component to your own project. The runtime has
no third-party dependency beyond retained generated support. Copy the complete
`src/plectis` package, including `_sealed_kernel.py`, generated subpackages and
licence files. A prover is needed only to replay or change the formal core.

## Minimal complete example

```python
from plectis.views import compile_public, run_public, RejectedPlan

# The application owner supplies this policy independently of the candidate.
schema = {
    "version": 1,
    "fields": [
        {"name": "name", "type": "text", "visibility": "public"},
        {"name": "note", "type": "text", "visibility": "private"},
    ],
}

plan = {
    "seq": [
        {"emit": {"channel": "internal", "value": {"input": "note"}}},
        {"emit": {"channel": "public", "value": {
            "concat": [{"literal": "Result for "}, {"input": "name"}]
        }}},
    ]
}

compiled = compile_public(plan, schema)
assert compiled.read_fields == ("name",)
assert run_public(compiled, {"name": "example-01"}) == ("Result for example-01",)
```

There is no `note` value in the public run. Supplying one causes a host error
before record values are serialised for the worker. The compile step accepts no
records at all. The plan generator must not already know protected values.

## Public API

| Function or value | Meaning |
|---|---|
| `compile_public(plan, schema)` | Strictly decode, check and derive a public slice; return immutable source snapshots |
| `run_public(compiled, row)` | Recheck and run one public-only row; return `tuple[str, ...]` |
| `run_public_batch(compiled, rows)` | Run a finite public-only row list in its given order; return tuple of traces |
| `compiled.public_plan` | Detached JSON representation of the derived slice, for inspection |
| `compiled.public_fields` | Every public schema field, all currently required by the host |
| `compiled.read_fields` | Syntactic input-read footprint of the generated slice; not necessarily minimal semantically |
| `compiled.digest` | SHA-256 identity of canonical source and policy; no authentication claim |
| `RejectedPlan` | Decoded plan fails the generated static checker |
| `InvalidInput` | Malformed/unsupported input or local worker failure |

Do not use a cached slice as an authorisation token or call internal generated
functions with untrusted input. The public wrapper reconstructs and rechecks the
source on every run. Metadata forgery cannot bypass that path, but a malicious
Python caller can bypass the package entirely. The integrating application owns
the real boundary.

## Schema

The only schema keys are `version` and `fields`. Version is integer `1`, not
Boolean `true`. Every field has exactly `name`, `type` and `visibility`.
Names match `[A-Za-z][A-Za-z0-9_]{0,63}` and must be unique. Types are `text` or
`flag`; visibilities are `public` or `private`.

The schema's order maps names to the formal input slots. Its names, types,
length and classifications are public configuration. Each public row must have
exactly the public keys, with exact `str` or `bool` values. The current host
requires every public key even if the slice does not read it. Private keys,
unknown keys, missing keys and integer stand-ins for Boolean values are refused.

## Expression grammar

| JSON | Type and behaviour |
|---|---|
| `{"literal": "text"}` | Text constant |
| `{"literal": true}` | Boolean constant |
| `{"input": "field"}` | Read a declared field; inherits its type and class |
| `{"concat": [left, right]}` | Concatenate two Text expressions |
| `{"equals": [left, right]}` | Boolean equality; operand types must agree |

There are no numeric operations, arbitrary format strings, functions, getters,
regular-expression engines or calls into application code. Scores in the demo
are already-approved public strings. Calculating a public score from protected
raw results is a different policy decision, not an implicit feature.

## Command grammar

| JSON | Behaviour |
|---|---|
| `{"skip": true}` | Emit nothing |
| `{"emit": {"channel": "public", "value": expression}}` | Emit one Text value publicly, if data/control checks permit |
| `{"emit": {"channel": "internal", "value": expression}}` | Internal reference event; erased from the public job |
| `{"seq": [first, second]}` | Exactly two sequential commands; nest for more |
| `{"if": {"condition": flag, "then": first, "else": second}}` | Execute one branch, tracking condition dependence |

Each node has exactly one constructor. Unknown keys and constructors are
rejected. A channel is an observation class in this language, not a destination
address or authority to transmit information. Internal events can be observed
in the separately used full reference semantics during development, but are not
returned by the public API.

## A rejection worth understanding

If a private condition controls whether a public line appears, the line leaks
that condition even when it is constant. A private-dependent public branch is
therefore refused. The current conservative checker also refuses two identical
public branches under a private guard. Move the common public emission outside
that conditional. Automatic equivalence-based acceptance would require another
checked transformation; it is not quietly inferred by the host.

Rejection does not necessarily mean the plan is semantically unsafe. The finite
experiment includes unnecessarily refused safe cases. Conversely, acceptance
does not mean the plan completes the user's job. Maintain independent expected
outputs or business requirements; an empty report satisfies confidentiality.

## SQLite integration

[`public_views_sqlite.py`](../../examples/operations/public_views_sqlite.py) is a separate local application. It owns the schema,
compiles the report before querying, selects `compiled.public_fields`, converts
SQLite's 0/1 flag into an exact Boolean, and executes the public job. It compares
against an ordinary handwritten renderer and asserts a separately chosen
expected output.

The example's authoriser rejects both direct private-column selection and a
private row filter. It is an integration test, not a verified SQL compiler. A
different application must make row membership/order public as well as cell
values. Replacing `SELECT public_columns` with `SELECT *` and dropping columns
later removes the no-acquisition benefit. A high-dependent `WHERE`, `JOIN` or
sort can reveal information through output shape.

The source data, row identifiers, scores and private canaries in the example are
synthetic. No private account, production database or external model was used.

## Bounds and failure behaviour

The current host permits at most 128 schema fields, AST depth 32, 4,096 AST
nodes, 16,384 Unicode scalar characters in an individual input/literal, 2,000
rows, a 2,000,000-byte canonical request and 8,000,000 bytes of accepted emitted
UTF-8 text per batch. Host preparation also refuses more than 300,000 expanded
JSON value/container visits, counting repeated references to shared subtrees.
A worker request has a 30-second completion timeout.

These are refusal limits. Output size is checked after evaluation, and JSON
escaping overhead is not part of that emitted-text limit. They are not a proof
of peak resource use or isolation. A failed batch returns no partial trace to
the caller. The component performs no publication, network or database writes.

## Changing and rechecking

Changing a report or schema uses `compile_public` again. Type/flow checks run at
use time and do not require a new theorem, within the language already proved.
Changing field visibility is a policy revision to be reviewed by the owner;
the component does not authorise it.

Changing the language or compiler requires revisiting the formal definitions,
proving the affected lemmas, regenerating the Python files, retaining the runtime
licence, and updating the source bindings after review. Do not edit generated
Python and retain the old proof claim. A different language port is a new
implementation needing its own correspondence evidence.

Run these from the repository root:

```sh
PYTHONPATH=src python3 -m pytest tests/test_public_views.py tests/test_public_views_recipe_change.py
python3 scripts/check/check_views_kernel.py
python3 scripts/check/check_views_kernel.py --dafny /absolute/path/to/dafny
```

The second command checks file identities and loader inventory only. The third
replays 30 verification tasks, requires byte-identical regenerated Python and
checks two deliberately broken specifications fail. These are tasks in one
small language, not 30 verified applications. The
[formal boundary](../../formal/views/README.md) names the obligations and trust
assumptions. Keep formal sources, check scripts, tests and licences with any
adaptation that must be independently rechecked.
