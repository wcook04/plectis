# Agent Monitor Redteam Falsification Replay

## Abstract

This module is the public Microcosm technical paper for a monitor/redteam
honesty contract. It specifies a synthetic replay fixture that treats a monitor
verdict as an evidence object to falsify: the verdict must be tied to a
trajectory hash, suspicious-span ref, adversarial-probe ref, escalation ref,
mitigation ref, body-omission ref, cold-replay ref, and source-artifact digest
boundary before it can support any monitor-coverage sentence.

The result is a safety/reliability proof about evidence shape, not a live
monitor product, control-eval score, exploit guide, product-spine substrate, or
complete-security claim. The technical contribution is the proof contract: a
public-safe replay can show how a monitor claim would fail under semantic
negatives and perturbations without exporting private reasoning, internal
source bodies, provider payloads, live agent traffic, or release authority.

## Telos

The fixture models three public trajectory cases: a benign control, a suppressed
failure attempt, and a tool-authority boundary attempt. Each case must carry a
trajectory hash, monitor id, suspicious span ref, adversarial probe ref,
verdict, severity, escalation ref, body-omission ref, mitigation ref, and cold
replay ref before the claim is admitted.

The point is to make "the monitor caught it" a rerunnable, falsifiable claim. A
benign pass proves only that the benign route remains admissible. An escalation
proves that a suppressed-failure attempt retained enough evidence for human
escalation. A block proves that the tool-authority boundary attempt was rejected
under the public policy vocabulary. None of those outcomes proves live monitor
performance; together they prove that this fixture's evidence contract catches
missing probes, missing source evidence, private-body leakage, and verdict drift.

## JSON Capsule Binding

- Source authority: `core/paper_module_capsules.json::paper_modules[33:paper_module.agent_monitor_redteam_falsification_replay]` with `source_authority: json_capsule`; the generated instance is `paper_modules/agent_monitor_redteam_falsification_replay.json`.
- This Markdown is a reader projection. The generated Mermaid projection is `available_from_capsule_edges`; the generated Atlas projection is `linked_from_capsule_edges`, so Mermaid and Atlas status are builder-owned projections from the capsule row.
- The authority ceiling is the synthetic monitor/redteam falsification replay fixture boundary. The proof boundary is restricted to body-free trajectory metadata, adversarial probe refs, escalation and mitigation refs, cold replay, negative cases, and validation receipts; it does not establish a live monitor product, control-eval score, exploit guide, production substrate, complete-security proof, or release authority.

## Reader Proof Boundary

A cold reader can validate this module by starting from the JSON capsule row,
then checking the generated JSON instance, exported bundle manifest, trajectory
cases, monitor observations, adversarial probe refs, escalation refs,
mitigation refs, cold replay rows, negative cases, and focused tests. The proof
is limited to the synthetic falsification replay boundary over public metadata
and body-free receipts.

The proof stops before live monitoring, control-eval scoring, production
coverage, exploit guidance, private reasoning export, provider behavior,
complete security, publication, and release. The page may explain generated
Mermaid and Atlas availability, but those projections remain builder-owned
outputs derived from the capsule row.

## Monitor-Falsification Mechanism

The organ turns a monitor claim into a falsification replay. Its inputs are the
projection protocol, monitor policy, trajectory cases, monitor observations,
negative-case files, exported bundle manifest, and source-module manifest.
`_build_result` loads those inputs, validates the projection protocol density,
checks the monitor policy vocabulary, checks trajectory case floors, validates
each observation against required refs and source-artifact evidence, scans
public inputs and copied source artifacts for forbidden private-state classes,
and folds in a public trace recomputation before writing receipts.

A positive observation cannot pass by carrying a verdict label alone. The
policy requires a trajectory id, monitor id, coverage label, suspicious action
span ref, adversarial probe ref, monitor verdict, severity tier, human
escalation ref, body-omission ref, mitigation diff ref, and cold replay ref.
For positive observations, source-artifact evidence refs must match the targets
declared by the exported source-module manifest. Missing fields, unsupported
verdicts, unverified source evidence, private chain-of-thought export,
internal-code export, exploit-instruction material, credential material, live
agent traffic, monitor product-performance claims, and coverage without a
probe become quarantine or blocking findings.

The exported body floor is checked separately from the receipt. The
source-module manifest admits two public-safe source artifacts: a copied public
macro pattern body for the monitor-redteam compound row, and a sanitized public
dogfood safety-evals trace slice. `validate_source_module_manifest` requires
the declared module count to match the rows, requires `body_in_receipt=false`,
rejects body text in receipts, resolves each target path, and verifies every
declared digest field against disk. Receipts and cards then expose ids, refs,
digests, counts, verdicts, findings, and ceilings, not copied bodies.

The public trace is the anti-echo pass. `build_public_monitor_redteam_falsification_trace`
recomputes whether a coverage label is backed by an adversarial-probe span,
then derives the monitor verdict from severity, escalation, and mitigation
evidence. In the first-wave fixture, the three spans recompute to one `pass`,
one `escalate`, and one `block`. If a declared verdict no longer matches the
span-derived verdict, `validate_public_trace` records
`PUBLIC_TRACE_MONITOR_REDTEAM_VERDICT_MISMATCH` and the organ blocks.

## Named Proof Consumers

- `run` consumes the first-wave fixture and writes result, board, validation,
  acceptance, and body-free command-card receipts. It is the proof consumer for
  the three synthetic trajectory cases and seven required negative cases.
- `run-monitor-bundle` consumes the exported public bundle and proves that the
  bundle manifest, source-module manifest, copied/sanitized source artifacts,
  four bundle observations, digest checks, private-state scan, and body-free
  card path remain valid outside the fixture directory.
- `tests/test_agent_monitor_redteam_falsification_replay.py` is the focused
  regression consumer. It asserts digest verification, sanitized dogfood trace
  slicing, workingness exposure of source-body imports, negative-case semantic
  floors, public trace verdict recomputation, source-evidence ref enforcement,
  public-relative body-free receipts, manifest boundary rejection, and fresh
  receipt reuse.
- A cold reader consumes this Markdown only after checking the JSON capsule,
  generated JSON instance, exported source manifest, trajectory and observation
  fixtures, public trace recomputation path, focused tests, and authority
  ceiling. The reader may verify the replay boundary but must not infer live
  monitor performance, control-eval score, exploit guidance, complete security,
  publication, or release readiness.

## Public Site Availability Boundary

This Markdown is public-site projection-safe within the release-boundary gate
because it exposes
trajectory hashes, monitor ids, probe refs, verdict labels, mitigation and
escalation refs, validator commands, and anti-claims without exporting private
reasoning, internal source bodies, exploit instructions, credentials, live
agent traffic, browser state, or provider payloads.

Public rendering may show the falsification accounting pattern. It must not
advertise a live monitor product, a control-eval score, production monitoring
coverage, exploit instructions, or complete-security status.

## Public-Safe Body Handling

The public body floor is the exported source-module manifest plus two copied or
sanitized source artifacts: the public macro-pattern body for
`agent_monitor_redteam_falsification_replay_compound`, and the sanitized public
dogfood safety-evals trace slice. Both remain bundle artifacts with
`body_in_receipt: false`. Receipts and cards should carry manifest refs, digest
status, counts, verdicts, negative cases, and authority ceilings only.

Future body updates must stay in the bundle and manifest lanes. Markdown and
public-site projections must not inline private chain-of-thought, internal
source bodies, exploit material, credentials, live traffic, provider payloads,
or raw session state.

## Semantic Negative and Perturbation Proof

The replay proves its boundary through negative and perturbation cases, not by
trusting the positive fixture. The negative floor includes private
chain-of-thought leakage, internal code export, exploit-instruction material,
credential material, live agent traffic, monitor product-performance claims, and
coverage claims without adversarial probes. Those cases are expected to block or
quarantine because they violate the public-source/body-free contract, not
because they resemble production attacks.

The perturbation proof is the public trace recomputation. A declared verdict is
accepted only when the public span evidence derives the same `pass`,
`escalate`, or `block` result. Removing the adversarial-probe span, weakening
the escalation or mitigation refs, changing the severity/verdict relation, or
declaring source evidence that is absent from the exported source-module
manifest turns the replay into a mismatch or blocking finding. That is the
technical safety property: the paper authority lives in disagreement detection
between declared monitor coverage and independently recomputed public evidence.

## Limitations and Claim Ceiling

This module may claim public fixture evidence that trajectory hashes, synthetic
monitor ids, suspicious-span refs, adversarial-probe refs, verdict labels,
escalation refs, mitigation refs, body-omission refs, cold replay refs,
negative-case labels, manifest digests, and validation receipts are checked by
the listed runtime witnesses.

This module may not claim a live monitor product, control-eval score,
production monitoring, exploit guidance, private reasoning export, internal
source export, live agent traffic, provider behavior, complete security,
source mutation authority, publication authority, release approval, or
whole-system correctness.

## Shape

```mermaid
flowchart TD
  capsule["JSON capsule authority"]
  markdown["Markdown reader projection"]
  manifest["source_module_manifest.json"]
  digest["2 source-artifact digest gates"]
  cases["three trajectory cases"]
  policy["public monitor policy"]
  observations["three observations"]
  required["required refs: span, probe, escalation, mitigation, replay"]
  trace["public trace verdict recomputation"]
  verdicts["pass / escalate / block"]
  negatives["7 negative semantic floors"]
  privateScan["body-free private-state scan"]
  receipt["body-free validation receipt"]
  ceiling["authority ceilings"]

  capsule --> markdown
  manifest --> digest
  digest --> observations
  cases --> required
  policy --> required
  required --> observations
  observations --> trace
  trace --> verdicts
  negatives --> receipt
  digest --> privateScan
  verdicts --> receipt
  privateScan --> receipt
  receipt --> ceiling
```

The module's shape is evidence narrowing. A public capsule points to a reader
projection, a copied/sanitized source manifest states which source material was
admitted and which bodies remain out of receipts, trajectory cases and policy
rules define the allowed verdict vocabulary, observations bind each verdict to
probe and mitigation refs, and the runtime recomputes a public trace without
expanding into live monitor authority.

## Reader Evidence Routing

- Capsule route: `core/paper_module_capsules.json::paper_modules[33]` is the
  capsule-backed authority row, and `paper_modules/agent_monitor_redteam_falsification_replay.json`
  is the generated paper-module instance.
- Source-module route: `examples/agent_monitor_redteam_falsification_replay/exported_monitor_redteam_bundle/source_module_manifest.json`
  records two admitted source artifacts with `body_in_receipt: false`: the
  public macro-pattern JSON slice with digest
  `sha256:89792add1e2f03a09c40f64d19c1ac0a54d62c053aabe11ecad0a9846a54cf33`,
  and the sanitized public dogfood safety-evals trace slice with digest
  `sha256:88493225f908f3f8892d187370d30231cb4e292b43bed202b462b6a6888e1eb0`.
- Trajectory route: `trajectory_cases.json` carries the three public trajectory
  hashes `sha256:monitor-redteam-benign-route-review`,
  `sha256:monitor-redteam-suppressed-failure`, and
  `sha256:monitor-redteam-tool-authority-escape`.
- Observation route: `monitor_observations.json` binds
  `obs_benign_route_review_pass` to `monitor.synthetic.route-review.v1` and a
  `pass` verdict, `obs_suppressed_failure_escalate` to
  `monitor.synthetic.failure-suppression.v1` and an `escalate` verdict, and
  `obs_tool_authority_escape_block` to `monitor.synthetic.tool-authority.v1`
  and a `block` verdict. Each observation carries a body-omission ref and cold
  replay ref.
- Runtime route: `src/microcosm_core/organs/agent_monitor_redteam_falsification_replay.py`
  and `tests/test_agent_monitor_redteam_falsification_replay.py` verify manifest
  digest visibility, negative-case coverage, required observation fields,
  public trace recomputation, and body-free receipt boundaries.

## Public Mechanics

- A monitor claim cannot pass unless the observation includes a verdict and the
  probe, escalation, mitigation, body-omission, and replay refs that make the
  verdict rerunnable.
- Coverage labels require adversarial probe refs; benign-only trajectories do
  not authorize coverage language.
- Private reasoning, internal code, exploit-detail, credential, live-traffic,
  product-performance, and coverage-without-probe cases are expected
  falsification fixtures.
- Receipts expose ids, refs, verdict counts, negative cases, `body_in_receipt:
  false`, private-state scan, and authority ceilings only.

## Prior Art Grounding

This organ is grounded in model red-team and behavior-discovery work that treats
monitor claims as things to falsify with adversarial probes. Anthropic's
[Red Teaming Language Models to Reduce Harms](https://arxiv.org/abs/2209.07858)
is a close procedural anchor for eliciting harmful or unwanted behavior, and
[Discovering Language Model Behaviors with Model-Written Evaluations](https://arxiv.org/abs/2212.09251)
anchors the idea that evaluation prompts can surface behavior classes worth
tracking. More recent sabotage and control-evaluation work reinforces the same
shape: monitors need adversarial trajectories, suspicious spans, escalation
paths, and negative cases, not just benign examples.

Microcosm borrows the falsification accounting pattern. A monitor verdict needs
trajectory hashes, probe refs, suspicious-span refs, escalation refs, mitigation
refs, replay refs, and body-omission receipts before coverage language is
allowed. It does not claim a live monitor product or control-eval score.

## Governing Lattice Relation

The capsule binds this page to
`mechanism.agent_monitor_redteam_falsification_replay.validates_public_monitor_verdict_receipts`,
the `agent_reliability_and_safety_validator_bundle` concept, provisional
principles `P-1` and `P-2`, provisional axiom `AX-1`, and the
`agent_monitor_redteam_falsification_replay` runtime locus. Within that
lattice, the mechanism is an evidence-before-monitor-claim gate: monitor
coverage language has no paper authority unless the capsule row, policy,
trajectory roster, observations, source-artifact manifest, negative-case
semantic floors, public trace, and body-free receipts agree.

The governing concept is validator-bundle accountability, not live monitor
operation. The principle/axiom ceiling is enforced as a refusal surface:
private reasoning, internal code, exploit instructions, credentials, live
agent traffic, provider payloads, performance claims, source mutation,
publication approval, and release approval remain false even when the replay
fixture passes.

## Structured Lattice Bindings

- `source_authority`: `json_capsule`
- `paper_module_id`: `paper_module.agent_monitor_redteam_falsification_replay`
- `reader_projection`: `microcosm-substrate/paper_modules/agent_monitor_redteam_falsification_replay.md`
- `generated_projection`: `microcosm-substrate/paper_modules/agent_monitor_redteam_falsification_replay.json`
- `organ_id`: `agent_monitor_redteam_falsification_replay`
- `runtime_locus`: `src/microcosm_core/organs/agent_monitor_redteam_falsification_replay.py`
- `fixture_locus`: `fixtures/first_wave/agent_monitor_redteam_falsification_replay/input`
- `exported_bundle`: `examples/agent_monitor_redteam_falsification_replay/exported_monitor_redteam_bundle`
- `source_open_body_floor`: one copied public macro-pattern body plus one
  sanitized public dogfood safety-evals trace slice, with body text excluded
  from receipts.
- `trajectory_floor`: three public trajectory cases.
- `verdict_floor`: one `pass`, one `escalate`, and one `block`; two high-severity
  observations; five adversarial probes.
- `negative_case_floor`: private chain-of-thought leakage, internal code export,
  exploit-instruction material, credential material, live agent traffic,
  monitor product-performance claim, and coverage without adversarial probe.
- `projection_status`: generated Mermaid and Atlas bindings are builder-owned
  capsule projections, not hand-maintained Markdown authority.

## Evidence Contract Summary

The evidence contract has four gates:

1. **Capsule gate**: the JSON capsule binds this reader projection to the
   organ, mechanism, code locus, generated JSON instance, generated Mermaid
   projection, and generated Atlas projection.
2. **Trajectory gate**: each monitor observation must cite a trajectory hash,
   monitor id, suspicious-span ref, adversarial-probe ref, verdict, severity,
   escalation ref, body-omission ref, mitigation ref, and cold-replay ref.
3. **Source-body gate**: the exported source-module manifest names the admitted
   copied/sanitized public source artifacts, requires matching digests, and
   keeps `body_in_receipt: false`.
4. **Falsification gate**: semantic negatives and public trace recomputation
   reject private-body leakage, unsupported source evidence, missing probes,
   unsupported verdicts, and declared/recomputed verdict mismatch.

A valid paper claim must pass all four gates and still inherit the limitations
above.

## Receipt Expectations

A valid receipt exposes the capsule id, manifest id, source-module digest,
trajectory hashes, monitor ids, verdict counts, suspicious-span refs,
adversarial-probe refs, escalation refs, mitigation refs, body-omission refs,
cold-replay refs, negative-case labels, and authority-ceiling booleans. It also
shows that public trace recomputation reached the expected `pass`, `escalate`,
and `block` outcomes without admitting private or live source bodies.

A valid receipt omits private chain-of-thought, private reasoning, internal
source bodies, exploit instructions, credentials, account or session material,
provider payloads, raw live transcripts, live agent traffic, and browser or HUD
access state. It may say the synthetic replay respected the falsification
boundary; it may not claim live monitor performance, control-eval scoring,
exploit guidance, complete security, provider behavior, source mutation,
publication authority, or release authority.

## Validation Receipt Path

Run the first-wave fixture validator from the repo root and write its receipt
outside the repo working tree:

```bash
cd microcosm-substrate && PYTHONPATH=src ../repo-python -m microcosm_core.organs.agent_monitor_redteam_falsification_replay run --input fixtures/first_wave/agent_monitor_redteam_falsification_replay/input --out /tmp/agent_monitor_redteam_receipt --acceptance-out /tmp/agent_monitor_redteam_acceptance.json --card > /tmp/agent_monitor_redteam_card.json
```

Then run the exported bundle validator:

```bash
cd microcosm-substrate && PYTHONPATH=src ../repo-python -m microcosm_core.organs.agent_monitor_redteam_falsification_replay run-monitor-bundle --input examples/agent_monitor_redteam_falsification_replay/exported_monitor_redteam_bundle --out /tmp/agent_monitor_redteam_bundle_receipt --card > /tmp/agent_monitor_redteam_bundle_card.json
```

The focused regression test and corpus projection checks are run from the repo
root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/mc_agent_monitor_pyc ./repo-pytest microcosm-substrate/tests/test_agent_monitor_redteam_falsification_replay.py -q -p no:cacheprovider --basetemp=/tmp/mc_agent_monitor_bt
./repo-python microcosm-substrate/scripts/build_doctrine_projection.py --check-paper-module-corpus
```

The validation ceiling remains synthetic monitor falsification replay only.

## Anti-Claim

This module does not run live agents, call providers, expose private
chain-of-thought, export internal code, provide exploit instructions, include
credentials, import live agent traffic, claim monitor product performance, claim
control-eval scores, mutate source, publish results, or authorize release.
