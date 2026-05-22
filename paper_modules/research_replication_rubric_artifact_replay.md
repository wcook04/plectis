# Research Replication Rubric-Artifact Replay

## Purpose

`research_replication_rubric_artifact_replay` turns a research-agent replication claim into a public-safe replay contract. A paper is not treated as replicated because an agent summarizes it; the replay must expose a contribution decomposition, rubric tree, allowed public inputs, scratch repo scaffold, experiment DAG, metric scripts, declared artifact-hash roster, artifact hashes, grader report, cost/runtime budget, ablation diff, failure taxonomy, and cold rerun receipt.

## Public Inputs

- `fixtures/first_wave/research_replication_rubric_artifact_replay/input/projection_protocol.json` maps the macro pattern to public replacements and omission receipts.
- `fixtures/first_wave/research_replication_rubric_artifact_replay/input/replication_policy.json` declares required replay fields and rubric axes.
- `fixtures/first_wave/research_replication_rubric_artifact_replay/input/research_replays.json` carries two synthetic paper capsules: one ML-method replay and one computational-science replay.
- Negative fixtures reject original-author-code reuse, hidden rubric leakage, report-only success, benchmark performance claims, private paper/data bodies, unbounded compute search, final-answer-only grading, and undeclared artifact hash refs.

## Runtime

```bash
python -m microcosm_core.organs.research_replication_rubric_artifact_replay run \
  --input fixtures/first_wave/research_replication_rubric_artifact_replay/input \
  --out receipts/first_wave/research_replication_rubric_artifact_replay

python -m microcosm_core.cli research-replication-rubric-artifact-replay \
  run-replication-bundle \
  --input examples/research_replication_rubric_artifact_replay/exported_research_replication_bundle \
  --out receipts/runtime_shell/demo_project/organs/research_replication_rubric_artifact_replay
```

## Authority Boundary

The organ validates synthetic replay metadata and receipt shape only. It does not claim benchmark performance, run providers, expose private paper or data bodies, admit artifact hashes outside the declared public roster, reuse forbidden original-author code, perform unbounded compute search, grade final answers alone, publish, host, or authorize release.
