# Information-flow policy and taint closure

This core decides the policy verdict for normalized flow observations and computes finite taint reachability. The public information-flow replay calls the generated Python through the isolated component worker; it does not use a handwritten fallback. The source theorem, compiled files, tool version and two deliberately weakened variants are bound in [metadata.json](metadata.json).

## What is proved

`Policy` specifies four verdicts independently of `Decide`: hidden-policy promotion blocks; an unsanitized untrusted flow to a privileged sink blocks; the other untrusted cases review or warn according to privilege and sanitization; a trusted, non-promotion case allows. `DecideMany` preserves this relation for every input row, including the two blocking guarantees.

`Closure` returns exactly the vertices reachable along finite directed walks from source-label seeds. For the `hidden_policy_claim` label it also seeds the destination of each edge marked as a hidden-policy promotion. It includes the seeds, is closed under each edge, and terminates on finite inputs. `ReachMonotone` proves that adding seeds cannot remove reachability; `ReachWithinEpisode` states the isolation result when the supplied graph and seeds respect an episode boundary. These are general finite-graph claims, not tests on a bounded collection of examples.

The verdict mutant changes the unsanitized privileged case to review; the hidden-seed mutant omits injected hidden labels. Each changes one executable expression while retaining the specification, and each fails verification.

## Runtime boundary

The host converts each `(episode_id, node_id)` into an episode-local graph, extracts labels only from source records in that episode, and marks instruction-channel or `promote` edges. The validator blocks a flow that references a source record from another episode. The adapter validates and encodes those observations; those Python steps are tested but not proved by this core. The policy proof assumes the host correctly applies Python's case-sensitive string checks and `is True` flag semantics. The graph proof assumes the supplied edges and seeds represent the intended flows; it does not establish their authenticity, temporal meaning, or sanitizer effectiveness.

The host separately constructs finite, deterministic witness walks, checks their node/label reachability against the generated core, and records edge references for the selected witnesses. Witness construction and receipt serialization are not Dafny-proved. Cycles do not lead to enumeration of all walks. Independent episodes do not share taint merely because their node IDs match. The projection also matches results by episode and flow ID, preserving input order when a key repeats. Because downstream records join by flow ID alone, the validator blocks duplicate flow IDs rather than allowing an ambiguous join. It also blocks duplicate source IDs, which would otherwise let one source overwrite another's trust labels.

This replaces the previous single pass ordered by episode and flow ID. An upstream untrusted edge now reaches a downstream privileged action even when the downstream edge sorts first; derived labels, verdicts, witness paths, counts and pass/block results can change. `analysis_kind` now names episode-scoped least-fixed-point propagation. Each flow row records its episode and label-specific witness paths with edge indices and flow IDs. An edge index is its position among the episode's flows sorted by flow ID, excluding flows with an empty sink; it disambiguates repeated flow IDs in diagnostics. `source_to_sink_paths` contains distinct canonical witness paths, and `path_count` counts those paths. For compatibility, `propagated_node_count` still counts distinct source and sink ID strings across the supplied records, not episode-qualified vertices. The shared worker has a 30-second timeout, so a large episode can fail to complete even though the finite-graph theorem holds. No theorem here establishes live prompt-injection resistance or the correctness of the surrounding validator.

## Recheck

Use the pinned Dafny 4.11.0 build recorded in metadata. From the repository root, replace `/path/to/dafny` with its executable:

```sh
/path/to/dafny verify formal/components/information_flow/InformationFlow.dfy --verification-time-limit 120 --cores 1
/path/to/dafny verify formal/components/information_flow/negative/UntrustedWriteMutant.dfy --verification-time-limit 120 --cores 1
/path/to/dafny verify formal/components/information_flow/negative/HiddenSeedMutant.dfy --verification-time-limit 120 --cores 1
python3 scripts/check/check_component_kernels.py --component information_flow --dafny /path/to/dafny
PYTHONPATH=src python3 -m pytest tests/test_component_information_flow.py tests/test_indirect_prompt_injection_information_flow_policy_replay.py
```

The first command should verify; each mutant should fail a proof obligation. The shared component-kernel checker also checks the source and generated-byte inventory. Dafny, Boogie, Z3, the compiler/runtime, Python, the sealed loader and the host observations remain trusted.
