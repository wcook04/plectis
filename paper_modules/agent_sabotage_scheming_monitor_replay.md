# Agent Sabotage Scheming-Monitor Replay

## Abstract

`agent_sabotage_scheming_monitor_replay` is a public-safe technical paper module
for a drilldown-only regression organ. It validates whether a sabotage/scheming
monitor claim is backed by joinable synthetic episodes, action traces,
per-step monitor scores, counterfactual benign replay, cold replay, falsification
fixtures, source-artifact evidence refs, body-free receipts, and an explicit
claim ceiling.

The core contribution is not a live scheming detector. It is a replay contract:
given a public fixture or exported bundle, the organ recomputes caught/not-caught
verdicts from monitor evidence, checks whether counterfactual replay isolates the
side objective, verifies source-artifact digest/provenance rows, rejects common
overclaim shapes, and emits receipts that omit private or harmful bodies.

## Telos

The module exists to make safety-monitor evidence auditable without laundering a
demo into a deployment claim. Frontier-lab readers should be able to answer:

- Which finite evidence rows support the sabotage/scheming monitor claim?
- Which verdicts are recomputed from scores and joins rather than echoed from
  fixture labels?
- Which mutations and negative cases cause rejection?
- Which public body floor is copied, sanitized, digest-checked, and kept out of
  receipts?
- Which claims remain out of scope even when every local check is green?

## JSON Capsule Binding

- Source authority:
  `core/paper_module_capsules.json::paper_modules[34:paper_module.agent_sabotage_scheming_monitor_replay]`
  with `source_authority: json_capsule`; the generated instance is
  `paper_modules/agent_sabotage_scheming_monitor_replay.json`.
- This Markdown is a reader projection. The generated Mermaid projection is
  `available_from_capsule_edges`; the generated Atlas projection is
  `linked_from_capsule_edges`, so diagram and Atlas availability are projections
  derived from the capsule, not independent proof.
- The proof boundary is the body-free synthetic sabotage/scheming replay
  contract. The authority ceiling is: no live sabotage, exploit instruction,
  credential/account material, private reasoning, harmful payload, deployment
  risk product claim, provider behavior claim, source mutation authority,
  publication authority, release approval, or whole-system safety claim.
- Validation receipts prove only the local replay contract: episode/action/score
  joins, counterfactual and cold replay refs, source-artifact evidence refs,
  negative-case coverage, private-state scan, digest checks, and authority
  ceilings.

## Mechanism

The runtime locus is
`src/microcosm_core/organs/agent_sabotage_scheming_monitor_replay.py`. It exposes
two public admission paths:

- `run` validates the first-wave fixture under
  `fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input`.
- `run_sabotage_bundle` validates the exported bundle under
  `examples/agent_sabotage_scheming_monitor_replay/exported_sabotage_monitor_bundle`.

Both paths call `_build_result`. The builder loads:

- `projection_protocol.json`
- `scheming_monitor_policy.json`
- `task_episodes.json`
- `action_traces.json`
- `monitor_scores.json`
- `counterfactual_replay.json`
- `cold_replay.json`
- `source_module_manifest.json` when present

The monitor proof is a join-and-recompute circuit. `validate_task_episodes`,
`validate_action_traces`, and `validate_monitor_scores` require monitor rows to
bind to an episode and action step. Monitor rows must carry evidence refs; in the
exported bundle those refs resolve through the digest-checked source manifest.
`validate_counterfactual_replay` checks that replay rows remove side-task
success while preserving the main task. `validate_cold_replay` requires explicit
passing replay receipts rather than narrative assurance.

The trace recomputation locus is
`src/microcosm_core/macro_tools/agent_execution_trace.py::build_public_sabotage_scheming_monitor_trace`.
It recomputes caught/not-caught from monitor verdicts, suspicion scores,
suspicious-action spans, and evidence refs. A caught verdict requires a blocking
monitor score at or above the suspicion threshold with a non-empty evidence ref
and suspicious-action span; escalate-only rows do not become catches. The trace
also computes whether counterfactual changed steps are the higher-suspicion
steps. A stale declared verdict, benign-step counterfactual spoof, or missing
cold replay becomes a finding.

## Evidence Floor

The local floor is intentionally small and inspectable:

| Evidence class | Fixture mode | Exported-bundle mode |
|---|---:|---:|
| Episodes | 3 | 4 |
| Action trace rows | 6 | 7 |
| Monitor-score rows | 6 | 7 |
| Counterfactual replay rows | 3 | 4 |
| Cold replay rows | 3 | 4 |
| Negative cases | 7 | 0 fixture-negative payloads |
| Copied public source artifacts | macro trace body + trace builder import | 2 manifest rows |

The exported bundle adds `scheming_ep_public_authority_probe` and
`obs_public_authority_probe`. That row is the real dogfood-trace floor: it comes
from a sanitized public command-trace slice, verifies against the source trace
digest, drops argv/stdout/stderr previews, and remains body-free in receipts.
The tests require it to compute a `block` monitor verdict and a caught episode
without exporting private session material.

The source-open body floor is split:

- The runtime imports
  `microcosm_core.macro_tools.agent_execution_trace::build_public_sabotage_scheming_monitor_trace`
  as the public recomputation body.
- The exported bundle manifest carries
  `agent_sabotage_scheming_extracted_pattern_ledger_row_body_import` as a
  source-faithful public macro pattern slice with digest
  `sha256:e1ad34691ca598b878f8658485ce78fa4fa59b3eb0a4bd078355c415ca2cb312`.
- The same manifest carries
  `agent_sabotage_scheming_public_dogfood_safety_evals_trace_slice_import` as a
  source-faithful sanitized command-trace slice with digest
  `sha256:7b6255ec65f4b21163685cf9d7a59dd9ae6075126deac065dec9a45d79dcea06`
  and source trace digest
  `sha256:24487cf8edb0779cfdd460b04a4ea7701805686545069f9e1c5767250c223cd3`.

Both manifest rows require `body_in_receipt: false`.

## Shape

```mermaid
flowchart TD
  capsule["JSON capsule authority"]
  fixture["fixture or exported bundle"]
  episodes["task episodes"]
  actions["action traces"]
  scores["monitor scores"]
  sourceManifest["source module manifest"]
  sourceArtifacts["digest-checked public artifacts"]
  counterfactual["counterfactual replay"]
  cold["cold replay"]
  recompute["public trace recomputation"]
  negatives["negative/falsification cases"]
  receipt["body-free validation receipt"]
  ceiling["authority ceiling"]

  capsule --> fixture
  fixture --> episodes
  fixture --> actions
  fixture --> scores
  fixture --> counterfactual
  fixture --> cold
  fixture --> sourceManifest
  sourceManifest --> sourceArtifacts
  episodes --> recompute
  actions --> recompute
  scores --> recompute
  counterfactual --> recompute
  cold --> recompute
  negatives --> receipt
  sourceArtifacts --> receipt
  recompute --> receipt
  receipt --> ceiling
```

## Rejection And Perturbation Evidence

The focused regression suite is the strongest technical evidence for the paper
claim. `tests/test_agent_sabotage_scheming_monitor_replay.py` covers:

- Digest mismatch in `source_module_manifest.json` blocks the exported bundle.
- `target_ref` / path mismatch blocks the exported bundle.
- `body_text_in_receipt` at manifest or row level is rejected.
- Missing `source_artifact_evidence_refs` quarantines a monitor row.
- A declared caught verdict that disagrees with recomputation emits
  `PUBLIC_TRACE_SCHEMING_CAUGHT_VERDICT_MISMATCH`.
- Perturbing a high-suspicion block row down to pass moves the recomputed
  caught verdict and blocks the receipt.
- A stale `caught_verdict` label inside a monitor-score row is rejected against
  the recomputed episode verdict.
- A counterfactual row that changes a benign low-suspicion step fails the rank
  delta check and the isolation check.
- Spoofing a declared negative-case id is caught by semantic negative-case
  floors.
- Public-relative, body-free receipts exclude absolute local paths and private
  keys such as credentials, provider payloads, hidden reasoning, raw harmful
  payloads, exploit instructions, and real target identifiers.
- The real sanitized public probe must compute `block`, carry verified source
  artifact evidence, and join to its counterfactual row.
- Spoofing the public probe to `pass` is rejected by verdict recomputation and
  the real-sanitized-evidence check.

These tests matter because they exercise the falsification path, not only the
happy path. The organ is permitted to say "this synthetic replay failed closed
under these mutations"; it is not permitted to say "this detects real scheming".

## Reader Evidence Routing

- Capsule:
  `core/paper_module_capsules.json::paper_modules[34:paper_module.agent_sabotage_scheming_monitor_replay]`
- Generated instance:
  `paper_modules/agent_sabotage_scheming_monitor_replay.json`
- Standard:
  `standards/std_microcosm_agent_sabotage_scheming_monitor_replay.json`
- Mechanism:
  `mechanisms/mechanism.agent_sabotage_scheming_monitor_replay.validates_public_sabotage_scheming_monitor_replay.json`
- Organ model:
  `organs/agent_sabotage_scheming_monitor_replay.json`
- Runtime:
  `src/microcosm_core/organs/agent_sabotage_scheming_monitor_replay.py`
- Trace recomputation:
  `src/microcosm_core/macro_tools/agent_execution_trace.py::build_public_sabotage_scheming_monitor_trace`
- Fixture input:
  `fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input`
- Exported bundle:
  `examples/agent_sabotage_scheming_monitor_replay/exported_sabotage_monitor_bundle`
- Focused tests:
  `tests/test_agent_sabotage_scheming_monitor_replay.py`
- Runtime-shell receipt:
  `receipts/runtime_shell/demo_project/organs/agent_sabotage_scheming_monitor_replay/exported_sabotage_monitor_bundle_validation_result.json`

## Governing Relations

The generated paper-module instance binds this reader page to:

- `organ:agent_sabotage_scheming_monitor_replay`
- `mechanism:mechanism.agent_sabotage_scheming_monitor_replay.validates_public_sabotage_scheming_monitor_replay`
- `concept:concept.agent_reliability_and_safety_validator_bundle`
- `principle:P-1`
- `principle:P-2`
- `axiom:AX-1`
- `paper_module.agent_monitor_redteam_falsification_replay`
- code locus:
  `src/microcosm_core/organs/agent_sabotage_scheming_monitor_replay.py`
  with `run`, `run_sabotage_bundle`, `_build_result`, `_write_receipts`, and
  `result_card`

Those edges are structural evidence-routing edges. They do not by themselves
prove runtime correctness; the runtime receipts and tests carry that narrower
claim.

## Validation

Run the body-free fixture validator:

```bash
cd microcosm-substrate && PYTHONPATH=src ../repo-python \
  -m microcosm_core.organs.agent_sabotage_scheming_monitor_replay \
  run \
  --input fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input \
  --out /tmp/agent_sabotage_scheming_receipt \
  --acceptance-out /tmp/agent_sabotage_scheming_acceptance.json \
  --card > /tmp/agent_sabotage_scheming_card.json
```

Run the exported-bundle validator:

```bash
cd microcosm-substrate && PYTHONPATH=src ../repo-python \
  -m microcosm_core.organs.agent_sabotage_scheming_monitor_replay \
  run-sabotage-bundle \
  --input examples/agent_sabotage_scheming_monitor_replay/exported_sabotage_monitor_bundle \
  --out /tmp/agent_sabotage_scheming_bundle_receipt \
  --card > /tmp/agent_sabotage_scheming_bundle_card.json
```

Run focused tests and paper-module corpus validation:

```bash
PYTHONPATH=microcosm-substrate/src ./repo-pytest \
  microcosm-substrate/tests/test_agent_sabotage_scheming_monitor_replay.py
cd microcosm-substrate && PYTHONPATH=src python3 \
  scripts/build_doctrine_projection.py --check-paper-module-corpus
```

Expected local result: the fixture and exported-bundle validators pass on the
checked-in inputs; the mutation tests block when digest, target-ref,
body-in-receipt, evidence-ref, caught-verdict, counterfactual-rank, negative
semantic, or public-probe labels are corrupted.

## Public-Safety Boundary

Public rendering may describe the replay grammar, recomputation rule,
falsification cases, sanitized command-trace source artifact, digest checks, and
body-free receipts.

Public rendering must not include or imply:

- live sabotage instructions
- exploit steps
- credentials, cookies, account/session material, or provider payloads
- private chain-of-thought or hidden reasoning bodies
- raw harmful payloads
- unsanitized argv/stdout/stderr previews
- browser/HUD state
- production telemetry
- live traffic
- live agent execution authorization
- deployment-risk measurement
- product monitor performance
- benchmark scores
- provider affiliation or provider behavior claims
- source mutation authority
- publication/release authority
- private-root equivalence
- whole-system safety

## Prior-Art Positioning

The module borrows evaluation grammar from sabotage, scheming, and deceptive
behavior evaluations: episodes, action traces, monitor scores, counterfactual
benign replay, falsification cases, and fail-closed monitor disagreement. The
closest public references remain Anthropic's sabotage evaluations, Apollo's
in-context scheming evaluations, Anthropic's Sleeper Agents work, and the
OpenAI/Apollo line on detecting and reducing scheming.

The Microcosm claim is deliberately narrower than those research programs. It
does not evaluate frontier models or live deployments. It gives the public
Microcosm substrate a receipt-backed, body-free, replayable safety-monitor proof
shape that can reject overclaims and provenance drift.
