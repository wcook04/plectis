# Change a workflow without silently changing its guarantees

“I changed this workflow—which results can I keep, and what must run again?”

Plectis can answer that question for a declared dependency graph using a
planner and checker verified with Dafny, a program verifier. It also has a
verified checker for whether one finite state-machine model preserves another
model's required interactions.
The optional [public-view compiler](public-views.md) adds a different kind of
example: a mixed report is transformed into a public-only program that preserves
its public output and reads no private input slots. The checker, transformation
and interpreter themselves run as generated Python. The surrounding Python hosts,
storage and correspondence between a model and a real application have separate,
weaker evidence.

The broader research question is whether we can change agent-written software
while preserving the guarantees its users rely on. A user may need to retain
completed observations, roll back a transaction, recover an unanswered request
or prevent an obsolete worker from replacing a current result. These are
different promises. This study starts with small operations that a Python
caller can use independently, then asks which promises survive a change.

This is an experimental study begun on 23 October 2026. It does not establish
verification of the older 88-component catalogue or an integrated agent platform.

## What this study contributes

The contribution is a set of small decision APIs for changing workflows:
identify affected results without automatically repeating uncertain actions,
check a replacement against the interactions a caller was promised, and compile
a report that can run with public inputs alone. The Python APIs execute the
generated cores whose source is verified. The examples connect those decisions
to concrete changes, rejected candidates and separately tested host behavior.

Dependency closure, refinement, information-flow analysis, code generation and
formal verification are established techniques. This release studies their
application at these workflow boundaries; it does not establish a new formal
method or practical superiority over ordinary implementations. Its stronger
specification test is concrete: a checker that misses a differing interaction
can satisfy the old one-way theorem but fails the new completeness requirement.

The next useful evidence is a real caller with independently fixed requirements,
a competent baseline, and measurements of missed regressions, unnecessary reruns
and integration effort. The authored examples and proof counts cannot establish
that value or predict a research lab's interest.

## Run the changed-evaluation example

From the repository root, with Python 3.11 or newer:

```sh
PYTHONPATH=src python3 examples/operations/evaluation.py --format text
```

No installation, model account or network access is needed. The example uses
deterministic observations in place of costly model calls, creates temporary
local state and prints a short summary. The default output is JSON when
`--format text` is omitted; `--out` always saves JSON. To keep that summary:

```sh
PYTHONPATH=src python3 examples/operations/evaluation.py \
  --out .microcosm/evaluation-study.json
```

The workflow observes three datasets, scores each one, combines the scores and
builds a report. It then changes only dataset A's scoring rule. A worker holding
the earlier publication ticket is deliberately paused until the change is done.
The expected observations are:

| Observation | Result |
|---|---|
| Repair after the scoring change | 8 task results reused, 3 tasks rerun, 1 task blocked |
| Tasks rerun | `score_a`, `aggregate`, `report` |
| Additional observation calls | 0 |
| Delayed worker's new publication | `rejected_stale` |
| Current publication | The report for metric version `2` |
| Identical retry of the original publication | `replayed`; the historical result is not current |
| Export whose acknowledgement was lost | Still unresolved after restart and removal from the graph; a second attempt is refused |

The export is a real local file append followed by a deliberately lost
acknowledgement. It is separate from the SQLite publication store. Repair keeps
its uncertainty in an effect journal and never automatically calls the export
callback. Removing the task cannot establish that the action did not happen.
The example observes one append; it establishes no remote delivery guarantee.

An ordinary dependency cache given the same inputs makes exactly the same
reuse, rerun and blocked decisions. The example claims no speed advantage.
The proposed value is a small decision interface whose stated properties can
be rechecked when its implementation changes. Whether that helps a real caller
enough to justify its cost remains an experimental question.

Read the [example source](../../examples/operations/evaluation.py) to change a
task, and the [Publish guide](publish.md) to use the publication operation alone.

## What the formal results say

### Repair: the least affected and blocked sets

The formal input is a finite directed acyclic graph in topological order,
with two Boolean flags per node: whether it is an invalid root, and whether it
is a nonreplayable action. The checked recurrences are:

```text
dirty[i] = roots[i] or any(dirty[d] for d in deps[i])
blocked[i] = (dirty[i] and effects[i]) or any(blocked[d] for d in deps[i])
```

For every valid input, the generated producer terminates and constructs an
accepted plan. Acceptance entails that `dirty` is the least forward closure of
the invalid roots and `blocked` is the least forward closure of dirty
nonreplayable nodes. The accepted masks are unique, `blocked` is a subset of
`dirty`, and every node is classified as reuse, rerun or blocked. A declared
nonreplayable action is never eligible for automatic rerun. There is no fixed
node-count bound. “Least” means set inclusion in this graph; it does not mean
minimum runtime cost or discovery of every semantic dependency.

The [formal source and recheck instructions](../../formal/repair/README.md)
explain the theorem and its assumptions. The host invokes the generated
producer and checker through a strict, isolated JSON worker; there is no
handwritten fallback planner. Its [source](../../src/plectis/repair/_host.py)
also exposes `make_plan` and `check_plan` for callers that only need the graph
operation.

### Compatibility: preserve the receiving user's interactions

The second formal core checks a supplied relation between two deterministic,
partial finite state machines. A machine records which inputs are permitted,
the output for each permitted input and the next state. Acceptance requires
every input permitted by the old machine to remain permitted by the new one,
with the same output and related successor states.

The theorem proves that an accepted relation preserves every finite interaction
sequence admitted by the old model, with no fixed trace-length or state-count
bound. A candidate cannot pass by refusing all required inputs. Errors and
unknown outcomes can be explicit outputs; deleting their transitions would
delete an obligation. The relation is supplied as a certificate and checked;
its existence alone does not establish that a Python or SQLite implementation
matches either model.

Run the supplied document-editing model from the repository root:

```sh
PYTHONPATH=src python3 examples/operations/compatibility.py
```

Adding an `inspect` operation passes. A candidate that acknowledges `cancel`
but retains the edit fails with `begin, append, cancel, read`. The final `read`
returns `base+edit` where the approved interface returns `base`. This is an
explicit model, not one extracted from a real editor. New inputs are permitted,
but the old contract supplies no guarantee after a caller takes a new input.

This matters when a replacement appears to return the right immediate answer
but removes something a caller could do next. For example, a batch insert may
write the requested rows while silently committing its caller's transaction.
`begin; batch; rollback; read` distinguishes that behaviour from an operation
that preserves the caller's right to roll back. The consumer's required
interactions must be fixed independently of the candidate being assessed.

The [Compatibility guide](compatibility.md) explains the API and model format.
Inspect the [formal source](../../formal/compatibility/Compatibility.dfy)
and its [recorded source and generated-file identities](../../formal/compatibility/metadata.json).
Connecting such tables to a real application's complete behaviour is a further
proof obligation, not a consequence of a passing table check. Transitions model
completed synchronous steps; the theorem does not prove concrete termination,
scheduling, fairness or properties of infinite executions.

## Reproduce the proof boundary

The recheckers verify retained source and generated-file hashes:

```sh
python3 scripts/check/check_repair_kernel.py
python3 scripts/check/check_compatibility_kernel.py
python3 scripts/check/check_views_kernel.py
```

These quick checks do not invoke a prover. With the official Dafny 4.11.0
toolchain installed, the full checks verify the sources, regenerate Python,
compare the generated files byte for byte and require deliberate propagation
and output-matching mutants to fail:

```sh
python3 scripts/check/check_repair_kernel.py --dafny /path/to/dafny
python3 scripts/check/check_compatibility_kernel.py --dafny /path/to/dafny
python3 scripts/check/check_views_kernel.py --dafny /path/to/dafny
```

The recorded Repair build has 21 verified tasks and zero errors; the
Compatibility and counterexample build has 41 verified tasks and zero errors;
the public-view build has 30. These are prover
tasks for defined cores, not counts of verified applications. Hashes bind
retained bytes; they do not prove those bytes correct. The verification is
SMT-backed through Dafny, Boogie and Z3. Their encoding, the compiler, generated
runtime, CPython and execution platform remain trusted; this is not a separately
kernel-checked Lean or Rocq proof object.

| Layer | Evidence and remaining responsibility |
|---|---|
| Graph and machine decisions | Formal statements and executable Dafny-generated cores; typed input assumptions apply. |
| Python decoding and execution | Tested hosts must preserve those types, invoke the checked core and handle failures correctly. |
| Workflow declarations | The caller supplies complete dependencies, meaningful code/environment/freshness identities and honest replayability flags. A hidden file or changed callback under an unchanged identity can cause stale reuse. |
| Checkpoints and uncertain actions | Tested single-writer persistence. Keep the same effect journal across restarts and graph changes. Checkpoint and journal writes are separate; crash atomicity and authenticated history are not proved. |
| SQLite publication | Tested conditional update and exact-request history in one writer transaction. SQLite storage semantics and the coordinator's control of the database are trusted. |
| Application contract | Someone must establish that the chosen model describes the real inputs, outputs, effects and future interactions that matter to the consumer. |

Publish does not check that a result satisfies the contract named by its ticket.
The integrating host must check the exact result for the exact input, then
publish those same bytes under the corresponding identities. A historical retry
returns an old outcome; current authority is checked when admitting a new
publication. A structured ticket is cooperative API data, not cryptographic
authentication. The [Publish guide](publish.md#what-the-boundary-establishes)
states the transaction and access boundary.

Run Repair with one cooperative synchronous writer. Callbacks must not mutate
the workflow or checkpoint during execution; the graph proof does not enforce
that host discipline.

## Experiments that decide whether to keep building

The useful target is a guarantee that survives a meaningful change. Proving a
pleasant model beside unrelated runtime code would not meet it. The following
candidate experiments test the broader question. They are alternatives for a
solo builder to investigate, rather than a commitment to build every subsystem:

| Change | Required evidence | Reason to stop or narrow |
|---|---|---|
| Replace a transaction operation | Freeze the caller's contract; accept useful implementations and reject loss of rollback, caller writes or required inputs. Exercise the same distinctions in an actual ingestion caller. | Only abstract tables are connected to the theorem, or passing requires weakening the caller's contract. |
| Change persisted state while an action is unanswered | Preserve the original request identity, operation phase and unresolved obligation. Reject migrations that drop history or turn “sent” back into “ready to send”. Allow useful new work after legitimate settlement. | Preserving only a total count or current graph permits a duplicate action. The present journal example is not yet a verified live schema migration. |
| Change policy or task authority before an effect | Use a small typed request, prove the decision actually called, and test the original stale request at the protected destination alongside a valid fresh request. | A proved text classifier is treated as complete mediation of arbitrary shell or remote effects. |
| Modify Repair and an ordinary cache with identical information | Compare false reuse, unnecessary reruns, blocked legitimate work, integration effort and effort to repair guarantees. Include changed input representation and effect protocol. | The ordinary implementation is equally dependable and easier to maintain, with no compensating benefit from the proved interface. |

Safety Core supplies a candidate pure policy analyser and reviewed rule meaning;
its shell classification and hook activation still need their own justification.
Existing policy provers are competing implementations, not evidence that
Plectis needs a new policy language. Git publication and staged-edit recovery
remain owned by One Checkout rather than being copied into this SQLite API.

If the publication adapter is retained, a next formal target is an executable
admission function that
distinguishes a new result, exact historical replay, conflicting replay and
stale work. Its generated decision must run inside the actual writer
transaction. A further argument must connect that decision to decoding, SQL
updates, history insertion and rollback. The present adapter is tested, not
deductively verified.

External use, developer time saved, maintenance savings, research novelty and
performance gains have not been measured. Counted lemmas, models and green
examples cannot decide those questions.

## Research provenance and selection

<details>
<summary>Original research returns and implementation decisions</summary>


The first implementation draws on fifteen research returns reviewed on 23 October 2026.
They share source material and a common brief, so agreement is not fifteen
independent votes. Selection follows reproduced mechanisms, useful counterexamples
and explicit limits. The less frequent replacement, migration and recovery ideas
are part of the central question, not incidental additions to Repair and Publish.

| Returns | Contribution retained and current disposition |
|---|---|
| p01, p08 | Task/policy generations checked at the actual Git destination. Preserve the lesson and adverse schedules; keep Git integration in One Checkout. |
| p02 | Bind checks to the exact candidate and preserve caller-visible outcomes, including interruption and uncertainty. |
| p03, p11, p13 | Atomic result/history recording and exact-request historical replay. Adapted into the small SQLite Publish operation; no formal SQLite refinement theorem. |
| p04 | Proved least graph closures and the generated code used in dispatch. Repair's formal source and generated Python are retained unchanged. |
| p05, p10 | Selected edits and saved snapshots express different intentions. Keep any staged-change transport opt-in; do not silently redefine index preservation. |
| p06, p07 | Separate permission, actual effects and knowledge of outcomes. Ordinary absence or timeout does not establish that an earlier request cannot still commit. |
| p09 | Exact executable correspondence and a competent immutable-candidate/CAS baseline. Digests alone do not establish complete dependencies or semantics. |
| p12, p15 | Independently chosen consumer requirements and distinguishing future interactions. The compatibility core formalises the finite-machine decision boundary; its concrete application bridge remains separate. |
| p14 | Replacement and migration must preserve outstanding identities, phases and obligations. Live migration is a candidate experiment rather than an implemented guarantee. |

The [Repair provenance](../../formal/repair/metadata.json),
[Compatibility provenance](../../formal/compatibility/metadata.json) and
[Publish source header](../../src/plectis/publish.py) bind the implemented
artifacts to their origins and evidence. The retained Dafny runtime has its MIT
licence beside the generated code. The fifteen returns are research inputs;
their models, finite tests and informal arguments do not combine into an
end-to-end proof.

### Second-round assimilation

A further fifteen returns were compared against the actual first-round code.
Five reviewers covered all fifteen; the synthesis selects distinct mechanisms
and checks ordinary alternatives. It does not interpret repeated recommendations
as independent votes. Three contributions improve existing operations:

- **p01:** explicit restoration of a confirmed effect result from the retained
  journal when the separately written checkpoint lost it. Recovery does not
  execute the effect again or make an obsolete result current.
- **p09:** bind the Python code actually imported to captured, checked source
  bytes. Tests reproduce source-package and sourceless-package shadowing,
  poisoned bytecode, modified manifests and malformed worker responses. The
  loader is trusted/tested host code, not a verified Python environment.
- **p14:** independently check a proposed distinguishing word with a generated
  negative-witness checker before reporting incompatibility. An old example is
  a proposal to recheck, not authority for a new pair of models.

**p15** supplies the one new optional experiment, the public-view compiler.
Its finite report language is the actual executed program, so its transformation
proof has a short path to a useful caller. The
[changed-recipe example](../../examples/operations/public_views_recipe_change.py)
compares two revisions with fixed expected outputs and generated full-reference
execution. A normal public-only renderer matches both when updated. The
experiment therefore establishes preservation in this language, not superiority
over normal rendering, measured maintenance savings or demand for a new DSL.

Other returns remain valuable without another installed API. P05's actual
SQLite rollback/savepoint continuations sharpen Compatibility's consumer
contract. P02 and p12 exhibit insufficient specifications; p03's fresh audit
found that a positive currentness requirement could be weakened while the
original proof suite still passed. An independently stated requirement rejected
both new mutants. These are specification-adequacy results, not refutations of
proof soundness or demonstrations that the original implementation is wrong.

P04's recover-or-cancel settlement is the strongest next stateful candidate if
a receiving caller needs it. P07 offers settle-or-replace, p10 current-policy
meaning, p03 an executed publication transition, and p13 a useful disjoint-work
frame property. Their semantics are different. Adding them all would multiply
state lifecycles and obscure the current API. P06/p11 migration preserves exact
outstanding obligations but needs a real migration consumer; p08's dependency
evaluator needs a workload where reuse beats reevaluation. P09's independent
Lean certificate route remains optional research, not a default runtime cost.

The [round-two implementation record](../../formal/round2-integration.json)
identifies imported source archives and changed owners. The older 88-component
catalogue remains a reference collection, not a count of verified components.
The next decision is whether a real caller benefits enough from one operation
to justify continuing it; neither proof counts nor this authored demo answer that.

</details>

## Checking the claim as well as the implementation

A proof establishes its stated property under its stated assumptions. It does
not decide whether that property captures what a caller needs. For example,
proving that every reported incompatibility is real leaves open a checker that
misses some incompatibilities. The compatibility replay now proves both
directions: it reports a mismatch exactly when the supplied interaction word
contains an approved-admissible prefix that the candidate fails to preserve.
The [missed-difference mutant](../../formal/compatibility/negative/ReplayMissedDifferenceMutant.dfy)
still satisfies the older one-way obligation but fails this stronger theorem.
That is a concrete specification check, not a proof that the specification is
complete for every application.

The catalogue's evidence is a separate layer. A source hash establishes which
bytes were replayed; an execution receipt reports what happened for particular
inputs; a deliberate bad case checks that a gate can reject a particular defect.
These do not turn all 88 components into formally verified programs. The current
component audit distinguishes those evidence classes from the three formal
cores. Restored source snapshots retain their original identities, while their
new replays describe the current public execution. Synthetic numeric examples
are fixture data, not measurements or claims about physical experiments.

### Patterns from other verified software repositories

A useful verification repository makes the property, proof, executable and
reproduction command easy to follow together. We reviewed the following source
revisions on 26 October 2026. This was a source comparison, not a reproduction
of their proofs or an exhaustive novelty search; no external code was copied.

| Project | Pattern to learn from | Application here |
|---|---|---|
| [Cedar specification, `301bdd2`](https://github.com/cedar-policy/cedar-spec/tree/301bdd22df134786a8a1312e24138afcd3f8bffe) | Names the Lean definitions and theorems, then separately tests its production Rust implementation against the executable model. | The proof and Python-host boundary stay explicit. A differential study with a real caller is the next proposed experiment, not a completed equivalence proof. |
| [Verified IronKV, `7e35ed0`](https://github.com/verus-lang/verified-ironkv/tree/7e35ed097c4089b9fbda483ea2629a0033f4d874) | States up front that its Verus port verifies the host program and does not reproduce IronFleet's distributed refinement proof. | The README links each decision core to its generated code and states what remains outside its proof. The catalogue cannot inherit those guarantees. |
| [Theorem OSS Verify, `2730445`](https://github.com/theorem-labs/oss-verify/blob/273044531e6ea0841351fe1ca3f009a7f2d37a31/docs/what-gets-proven.md) | Defines claims for exact compiled binaries, input conditions and process semantics. | Keep exact source/generated-byte binding, pinned tools and replay commands. Plectis proves Dafny source properties; it does not claim Theorem's binary-level guarantees. |

These comparisons support a presentation and validation practice, not a claim
that Plectis invented those techniques. A reviewer can start at the
[README's operation table](../../README.md#formally-checked-workflow-operations),
open the specification and generated implementation, then run
`make verify-operations DAFNY=/path/to/dafny`. The
[formal index](../../formal/README.md) names the trusted tools and unproved hosts.

### Research reviewed on 26 October 2026

The following sources informed this boundary. The videos were reviewed through
timestamped captions; no claim here depends on inspecting their visuals.

| Source | Useful lesson and disposition |
|---|---|
| [Carl Kadie, Microsoft Reactor, 22 October](https://www.youtube.com/watch?v=P9xCUmjkPUM&t=1254s) | Review the specification, preserve the algorithm's structure, and use adversarial review. Applied here by adding an independently meaningful completeness requirement and a mutant that the previous requirement missed. |
| [Álvaro Silva's ProofPulse demonstration, 11 May](https://www.youtube.com/watch?v=8pO3NAodjoQ) and [project source](https://github.com/VeriFixer/ProofPulse) | Proof-dependency coverage can flag vacuous or unused obligations. Retained as a diagnostic option; it is not an additional correctness certificate, and Plectis does not require this tool to reproduce its proofs. |
| [Gabriela Moreira, Type Theory Forall, 19 October, 36:13](https://www.youtube.com/watch?v=SdwjRJgp6gs&t=2173s) and [Quint model-based testing documentation](https://quint.sh/docs/model-based-testing) | Generated programs, model-based tests and trace validation connect models to implementations in different ways. Plectis keeps generated executable cores and tests their Python boundaries; it does not count a separately checked model as proof of arbitrary Python. |
| [Anthropic, 22 October](https://www.anthropic.com/research/formal-verification) and [Theorem's public verification interface](https://github.com/theorem-labs/oss-verify) | Their guarantees attach to selected entrypoints, checked properties and identified build artifacts. Plectis follows that precision about scope. This review does not claim a Theorem or Anthropic verification run; the current release is checked through its existing Dafny route. |

The next useful formal target should come from a real failing obligation at a
consumer boundary. Changing proof assistants or increasing a component count
does not by itself supply that obligation.

This guide is a reproducible study record. The canonical system paper remains
`claim-faithful-publication-systems` in the
[Plectis Erdős repository](https://github.com/wcook04/plectis-erdos).
