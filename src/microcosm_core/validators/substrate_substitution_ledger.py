from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import PASS, public_relative_path
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.substrate_substitution_ledger"
LEDGER_REL = Path("core/substrate_substitution_ledger.json")
REGISTRY_REL = Path("core/organ_registry.json")
ACCEPTANCE_PLAN_REL = Path("core/acceptance/first_wave_acceptance.json")
ACCEPTANCE_SUMMARY_REL = Path("receipts/first_wave/acceptance_summary.json")
FIXTURE_MANIFESTS_REL = Path("core/fixture_manifests")
EXAMPLES_REL = Path("examples")

REAL_SUBSTRATE_CAPSULE = "real_substrate_capsule"
RETAINED_REGRESSION_VALIDATOR = "retained_regression_validator"
DELETED_DEMOTED_HISTORICAL_ARTIFACT = "deleted_demoted_historical_artifact"
DISPOSITIONS = {
    REAL_SUBSTRATE_CAPSULE,
    RETAINED_REGRESSION_VALIDATOR,
    DELETED_DEMOTED_HISTORICAL_ARTIFACT,
}
FIXTURE_ECHO_CLASS = "fixture_echo_smoke"
REGRESSION_FIXTURE_BUCKET = "regression_negative_fixture"
NAME_PROMISE_RISK_CLASSES = {"semantic_validator", "algorithmic_projection"}
COMPUTE_PROMISE_TERMS = {
    "attribute",
    "attribution",
    "counterfactual",
    "discover",
    "interpret",
    "interpretability",
    "prove",
    "proof",
    "repair",
    "simulate",
    "simulation",
    "world",
}
MECHANISM_THEATER_PROMISE_TERMS = {
    "attribute",
    "attribution",
    "counterfactual",
    "interpret",
    "interpretability",
    "simulate",
    "simulation",
}
COMPUTE_IMPORT_MARKERS = (
    "import numpy",
    "from numpy",
    "import torch",
    "from torch",
    "import scipy",
    "from scipy",
)
RUNTIME_COMPUTE_MARKERS = (
    "def _gridworld_step",
    "def _step",
    "def _toy_transformer_forward",
    "def _run_toy_transformer",
    "np.",
    "forward(",
    "gradient_scores",
    "ablation_result",
    "actual_next_state",
    "predicted_actual_match",
)
RUNTIME_FUNCTION_MARKERS = {
    "_gridworld_step": "def _gridworld_step",
    "_step": "def _step",
    "_toy_transformer_forward": "def _toy_transformer_forward",
    "_run_toy_transformer": "def _run_toy_transformer",
}
RUNTIME_ASSIGNMENT_MARKERS = {
    "gradient_scores": "gradient_scores",
    "ablation_result": "ablation_result",
    "actual_next_state": "actual_next_state",
}
RUNTIME_KEY_MARKERS = {
    "gradient_scores": "gradient_scores",
    "ablation_result": "ablation_result",
    "predicted_actual_match_count": "predicted_actual_match",
}
SOURCE_COMPUTE_PREFILTER_TERMS = (
    "import numpy",
    "from numpy",
    "import torch",
    "from torch",
    "import scipy",
    "from scipy",
    "_gridworld_step",
    "def _step",
    "_toy_transformer_forward",
    "_run_toy_transformer",
    "np.",
    "forward",
    "gradient_scores",
    "ablation_result",
    "actual_next_state",
    "predicted_actual_match",
)
NAME_PROMISE_AXIS_CHECK_FIELDS = (
    "schema_version",
    "policy_ref",
    "status",
    "name_promise_terms",
    "mechanism_theater_terms",
    "risky_evidence_class",
    "source_ref",
    "source_exists",
    "compute_import_markers",
    "runtime_compute_markers",
    "source_inspection_found_runtime_compute",
    "scheduler_target",
)
NAME_PROMISE_SUMMARY_CHECK_FIELDS = (
    "schema_version",
    "policy_ref",
    "status_counts",
    "mechanism_theater_count",
    "mechanism_repair_targets",
)
WRITER_DRIFT_SAMPLE_LIMIT = 20
WRITER_DRIFT_SCOPE_AXES = {
    "full": None,
    "name_promise": {"name_promise"},
}
SETTLEMENT_SAMPLE_LIMIT = 5
SETTLEMENT_OWNER_AXES = {"claim_ceiling", "digest_relation"}
GENERIC_CLAIM_CEILINGS = {
    "validates declared public contract only",
}
BLOCKING_DIGEST_SETTLEMENT_BUCKETS = {
    "body_count_disposition_change",
    "historical_pinned_drift",
    "relation_reclassification",
    "source_moved_target_stale",
    "target_moved_source_stale",
}
BODY_COUNT_AGGREGATE_FIELDS = {
    "digest_drift_disposition_count",
    "digest_relation_status",
    "real_body_count",
    "supporting_body_count",
    "receipt_body_count",
}
VERIFIED_EXACT_COPY_RELATIONS = {
    "declared_public_safe_macro_body_copy",
    "exact_copy",
    "verified_exact_copy_inferred_from_matching_source_target_digest",
    "verified_public_safe_private_path_rewrite",
}
_MISSING = object()
RUNTIME_RECEIPT_SOURCE_FILENAMES = {
    "aggregate_report.json",
    "corpus_readiness.json",
    "cost_metrics.json",
    "failure_taxonomy_report.json",
    "graph_variant_comparison.json",
    "problem_source_manifest.json",
    "run_summary.json",
    "tactic_affordance_probe.json",
    "tactic_portfolio_availability.json",
}
RUNTIME_GENERATED_ARTIFACT_SOURCE_FILENAMES = {
    "graph_update_candidates.json",
    "graph_variant.json",
    "premise_index.json",
    "provider_receipt_reduction_matrix.json",
    "prover_skill_atlas.json",
    "recipe_policy_metrics.json",
    "strategy_cards.json",
    "strategy_hypothesis_set.json",
}
RUNTIME_GENERATED_LEAN_ARTIFACT_SOURCE_FILENAMES = {
    "aesop.lean",
    "decide.lean",
    "grind.lean",
    "mathlib_probe.lean",
    "native_decide.lean",
    "omega.lean",
    "rfl.lean",
    "simp.lean",
    "simp_all.lean",
    "trace_state_probe.lean",
}
RUNTIME_LEAN_DIAGNOSTIC_SOURCE_PREFIX = "state/lean_diagnostics/runs/"
FORMAL_EVIDENCE_CELL_STATE_SOURCE_PREFIX = "state/formal_math_research_operations/"
CONCURRENCY_MISSION_CONTROL_RECEIPT_SOURCE_REFS = {
    "self-indexing-cognitive-substrate/microcosms/provider_harness_canary/canary_board.json",
    "self-indexing-cognitive-substrate/microcosms/task_ledger_cap_economy/events.jsonl",
    "self-indexing-cognitive-substrate/microcosms/task_ledger_cap_economy/projection.json",
    "self-indexing-cognitive-substrate/microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json",
}

PROVER_RUNNER_REFS = (
    "tools/meta/factory/run_prover_statement_only_hammer_bandit.py",
    "tools/meta/factory/run_prover_proof_state_search_curriculum.py",
)
PROVER_SMOKE_COMMANDS = (
    "PYTHONPATH=examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/source_modules "
    "python3 examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/source_modules/"
    "tools/meta/factory/run_prover_statement_only_hammer_bandit.py "
    "--run-root /tmp/microcosm-verifier-lab-hammer-smoke --problem-limit 1 "
    "--timeout-seconds 5 --check --json",
    "PYTHONPATH=examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/source_modules "
    "python3 examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/source_modules/"
    "tools/meta/factory/run_prover_proof_state_search_curriculum.py "
    "--run-root /tmp/microcosm-verifier-lab-curriculum-smoke --external-limit 1 "
    "--local-limit 0 --timeout-seconds 5 --check --json",
)


def _public_root_for_path(path: str | Path) -> Path:
    """Resolve the public-root anchor used by every ledger surface.

    - Teleology: protects the "validated against the real microcosm-substrate public root" claim from a wrong-root invocation that would scan an unrelated dir and false-PASS.
    - Guarantee: returns a Path that is either an ancestor named `microcosm-substrate` / carrying the pyproject+src+forbidden-classes markers, else the resolved input path itself (never a silent CWD fallback).
    - Fails: no marker in ancestry -> returns the resolved input path (not raised), so downstream ledger/registry reads miss and emit a clean `blocked` result rather than a false PASS.
    - Reads: filesystem ancestry (pyproject.toml, src/microcosm_core, core/private_state_forbidden_classes.json).
    - Writes: None.
    - When-needed: trust as the root anchor before reading any ledger/registry/manifest path.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    # No microcosm-substrate marker found in the path's ancestry. Return the
    # resolved input path itself rather than silently falling back to the
    # process CWD: a CWD fallback makes `--check --root <unrelated-dir>` pass
    # against the real repo and exit 0, masking a wrong-root invocation. With
    # the resolved path, downstream validators find no ledger/registry there
    # and emit a clean `blocked` result (exit 1) instead of a false PASS.
    return resolved


def _display(path: Path, *, public_root: Path) -> str:
    """Render an absolute path as a public-root-relative display ref.

    - Teleology: keeps every ref the ledger emits anchored to the public root so receipts never leak an absolute filesystem path.
    - Guarantee: returns `public_relative_path(path, display_root=public_root)` — a string relative to public_root when path is under it.
    - Fails: never raises here; delegates entirely to private_state_scan.public_relative_path, whose return governs out-of-root behavior.
    - Writes: None.
    """
    return public_relative_path(path, display_root=public_root)


def _rows(payload: Any, key: str) -> list[dict[str, Any]]:
    """Extract a list of dict rows under a key, tolerating malformed payloads.

    - Teleology: the single defensive accessor every ledger/registry/manifest reader uses so shape drift degrades to empty, never to a crash.
    - Guarantee: returns a list containing only the dict elements of `payload[key]`; returns `[]` when payload is not a dict or the key is absent/non-iterable-of-dicts.
    - Fails: never raises; non-dict payload or missing key -> `[]`; non-dict rows are silently dropped.
    - Writes: None.
    """
    if not isinstance(payload, dict):
        return []
    return [row for row in payload.get(key, []) if isinstance(row, dict)]


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    """Read a JSON file into a dict, treating absence as an empty dict.

    - Teleology: lets the ledger read optional surfaces (existing ledger, acceptance plan/summary, manifests) without branching on existence at every call site.
    - Guarantee: returns the parsed dict when the file exists and parses to a dict; returns `{}` when the file is absent or parses to a non-dict.
    - Fails: file absent -> `{}` (no raise); a present-but-malformed JSON file propagates read_json_strict's parse exception.
    - Reads: the file at `path`.
    - Writes: None.
    """
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _sha256_file(path: Path) -> str:
    """Stream a file's bytes into a prefixed sha256 content digest.

    - Teleology: the digest primitive backing every target/source body comparison, so "digest-fresh exact copy" claims rest on real file contents.
    - Guarantee: returns `sha256:<hexdigest>` over the file's bytes, read in 1 MiB chunks so large bodies do not load fully into memory.
    - Fails: raises OSError (e.g. FileNotFoundError) if `path` is not readable — callers guard with `path.is_file()` before invoking.
    - Reads: the file at `path` (binary).
    - Writes: None.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _normalize_sha256(value: Any) -> str:
    """Coerce a declared digest to canonical `sha256:`-prefixed form.

    - Teleology: makes manifest-declared digests comparable to computed `_sha256_file` output regardless of whether the manifest stored the prefix.
    - Guarantee: returns `""` for falsy input; otherwise returns the string with a single leading `sha256:` ensured (added only when absent).
    - Fails: never raises; non-string values are stringified first.
    - Writes: None.
    """
    text = str(value or "")
    if not text:
        return ""
    return text if text.startswith("sha256:") else "sha256:" + text


def _strip_public_root_prefix(ref: str) -> str:
    """Normalize a ref to public-root-relative form.

    - Teleology: protects ref-equality comparisons (source-authority role, manifest path joins) from a leading `microcosm-substrate/` prefix splitting one logical ref into two.
    - Guarantee: returns `ref` with a single leading `microcosm-substrate/` removed if present, else `ref` unchanged.
    - Fails: None — pure string transform; never rejects, raises, or returns a failure envelope.
    - Writes: None.
    """
    return ref.removeprefix("microcosm-substrate/")


def _source_authority_role(source_ref: str, material_class: str | None = None) -> str:
    """Classify a source ref into an authority role gating real-body credit.

    - Teleology: protects the "real substrate body" claim from counting fixtures/receipts/generated-projection/runtime-artifact sources as real source bodies.
    - Guarantee: returns exactly one role string (e.g. `fixture_regression_source`, `receipt_projection_source`, `runtime_*_source`, `generated_projection*_source`, `public_substrate_source`, or `external_or_macro_reference`) by ordered prefix/suffix/membership checks on the stripped ref.
    - Fails: no rule matches -> returns `external_or_macro_reference` (default bucket, not an exception); never raises.
    - Reads: the source_ref string and module constant ref-sets (no filesystem).
    - Writes: None.
    - When-needed: inspect when deciding whether a digest row may count toward real-body support; validator escalates several roles to `real_body_*_source_counted_as_substrate` issues.
    - Escalates-to: validate_ledger_payload non-substrate-source issue ids; AP source-authority constants.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    clean = _strip_public_root_prefix(str(source_ref or ""))
    if clean in CONCURRENCY_MISSION_CONTROL_RECEIPT_SOURCE_REFS:
        return "concurrency_mission_control_seed_receipt_source"
    if "::" in clean:
        return "generated_projection_slice_source"
    if clean.endswith("/receipt.json") or clean.endswith("_receipt.json"):
        return "receipt_projection_source"
    if clean.startswith(RUNTIME_LEAN_DIAGNOSTIC_SOURCE_PREFIX) and clean.endswith(".json"):
        return "runtime_lean_diagnostic_source"
    if clean.startswith(FORMAL_EVIDENCE_CELL_STATE_SOURCE_PREFIX) and clean.endswith(".json"):
        return "formal_evidence_cell_state_source"
    if clean.startswith("state/runs/") and Path(clean).name in RUNTIME_RECEIPT_SOURCE_FILENAMES:
        return "runtime_receipt_source"
    if (
        clean.startswith("state/runs/")
        and Path(clean).name in RUNTIME_GENERATED_ARTIFACT_SOURCE_FILENAMES
    ):
        return "runtime_generated_artifact_source"
    if (
        clean.startswith("state/runs/")
        and Path(clean).name in RUNTIME_GENERATED_LEAN_ARTIFACT_SOURCE_FILENAMES
    ):
        return "runtime_generated_lean_artifact_source"
    if clean.startswith("state/microcosm_portfolio/"):
        return "generated_projection_source"
    if clean.startswith("fixtures/"):
        return "fixture_regression_source"
    if clean.startswith("receipts/"):
        return "receipt_projection_source"
    if clean.startswith(("core/", "examples/", "src/", "scripts/", "tools/", "standards/")):
        return "public_substrate_source"
    return "external_or_macro_reference"


def _source_can_count_as_real_body(
    source_ref: str,
    material_class: str | None = None,
) -> bool:
    """Decide whether a source ref's authority role may credit a real body.

    - Teleology: the boolean gate over `_source_authority_role` that protects the "real substrate body" claim from fixtures, projections, receipts, runtime/lean artifacts, formal-state, and concurrency-seed receipts being counted as real source bodies.
    - Guarantee: returns True only when the resolved authority role is NOT in the non-substrate denylist (fixture_regression / generated_projection[_slice] / receipt_projection / runtime_* / formal_evidence_cell_state / concurrency_mission_control_seed_receipt); True for public_substrate_source and external_or_macro_reference.
    - Fails: never raises; an unrecognized ref resolves to external_or_macro_reference and returns True (treated as countable by role, still gated elsewhere by digest/relation checks).
    - Reads: the source_ref string and module constant ref-sets (no filesystem).
    - Writes: None.
    - When-needed: inspect when reasoning about why a digest row did or did not earn counts_as_real_body.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    return _source_authority_role(source_ref, material_class) not in {
        "fixture_regression_source",
        "generated_projection_source",
        "generated_projection_slice_source",
        "receipt_projection_source",
        "runtime_receipt_source",
        "runtime_generated_artifact_source",
        "runtime_generated_lean_artifact_source",
        "runtime_lean_diagnostic_source",
        "formal_evidence_cell_state_source",
        "concurrency_mission_control_seed_receipt_source",
    }


def _path_from_ref(public_root: Path, ref: str, *, manifest_path: Path | None = None) -> Path:
    """Resolve a target ref to a path, preferring public-root then manifest-relative.

    - Teleology: lets a manifest's target_ref resolve whether it is written public-root-relative or relative to the manifest's own directory, so digest checks find the real body.
    - Guarantee: returns `public_root / clean` when that exists; else `manifest_path.parent / clean` when a manifest_path is given; else falls back to `public_root / clean` (which may not exist).
    - Fails: never raises; an unresolvable ref returns a non-existent Path that the caller's `is_file()` check then treats as target_missing.
    - Reads: filesystem existence of the public-root candidate (`.exists()`).
    - Writes: None.
    """
    clean = _strip_public_root_prefix(str(ref))
    if clean:
        candidate = public_root / clean
        if candidate.exists():
            return candidate
    if manifest_path is not None and clean:
        return manifest_path.parent / clean
    return public_root / clean


def _accepted_registry_rows(public_root: Path) -> list[dict[str, Any]]:
    """Read the organ registry and return only accepted-current-authority rows.

    - Teleology: defines the authoritative set of organs the ledger must account for, anchoring every "accepted organ has a disposition" check to the registry.
    - Guarantee: returns the list of `implemented_organs` dict rows whose `status == "accepted_current_authority"`; returns `[]` when the block is absent.
    - Fails: raises if `core/organ_registry.json` is missing or malformed (read_json_strict); a present-but-shapeless registry yields `[]` via `_rows`.
    - Reads: core/organ_registry.json under public_root.
    - Writes: None.
    """
    registry = read_json_strict(public_root / REGISTRY_REL)
    return [
        row
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _fixture_manifest(public_root: Path, organ_id: str) -> tuple[Path | None, dict[str, Any]]:
    """Load an organ's fixture manifest if it exists.

    - Teleology: feeds fixture-derived refs/counts into the ledger row while keeping fixtures input-only, never body authority.
    - Guarantee: returns `(path, payload_dict)` when the per-organ fixture manifest file exists and parses to a dict; returns `(None, {})` when the file is absent.
    - Fails: file absent -> returns `(None, {})` (no raise); a present-but-non-dict payload is coerced to `{}` while path is still returned.
    - Reads: core/fixture_manifests/<organ_id>.fixture_manifest.json.
    - Writes: None.
    """
    path = public_root / FIXTURE_MANIFESTS_REL / f"{organ_id}.fixture_manifest.json"
    if not path.is_file():
        return None, {}
    payload = read_json_strict(path)
    return path, payload if isinstance(payload, dict) else {}


def _source_manifest_refs_from_fixture(fixture: dict[str, Any]) -> list[str]:
    """Extract source_module_manifest refs declared inside a fixture's open-body imports.

    - Teleology: supplies the manifest-ref set that backs digest/real-body accounting, so fixture-declared manifests join the same body verification path as direct manifests.
    - Guarantee: returns a de-duplicated, order-preserving list of public-root-stripped refs from `source_open_body_imports.source_manifest_refs`; returns `[]` when that block is missing or not a dict.
    - Fails: malformed/absent block -> returns `[]` (no raise); falsy refs are skipped.
    - Reads: the in-memory fixture dict only (no filesystem).
    - Writes: None.
    """
    refs: list[str] = []
    source_open = fixture.get("source_open_body_imports")
    if isinstance(source_open, dict):
        refs.extend(
            _strip_public_root_prefix(str(ref))
            for ref in source_open.get("source_manifest_refs", [])
            if ref
        )
    return list(dict.fromkeys(refs))


def _source_refs_from_fixture(fixture: dict[str, Any]) -> list[str]:
    """Collect macro/source refs declared anywhere in a fixture for the macro_refs set.

    - Teleology: surfaces every source/portfolio/body-material ref a fixture names so the ledger row's macro_refs list reflects the organ's claimed provenance.
    - Guarantee: returns a de-duplicated, order-preserving list of stringified refs gathered from `source_refs`, `source_portfolio_refs`, and `source_open_body_imports.body_material_ids`; returns `[]` when none present.
    - Fails: never raises; non-list/non-dict blocks contribute nothing; falsy refs skipped.
    - Reads: the in-memory fixture dict only (no filesystem).
    - Writes: None.
    """
    refs: list[str] = []
    for key in ("source_refs", "source_portfolio_refs"):
        value = fixture.get(key)
        if isinstance(value, list):
            refs.extend(str(ref) for ref in value if ref)
    source_open = fixture.get("source_open_body_imports")
    if isinstance(source_open, dict):
        refs.extend(str(ref) for ref in source_open.get("body_material_ids", []) if ref)
    return list(dict.fromkeys(refs))


def _direct_source_module_manifest_refs(public_root: Path, organ_id: str) -> list[str]:
    """Discover on-disk source_module_manifest.json refs under an organ's examples tree.

    - Teleology: anchors real-body accounting to actual examples/<organ>/ manifests so the ledger's body support is grounded in shipped files, not fixture claims.
    - Guarantee: returns a sorted, de-duplicated list of public-root-relative display refs for every `source_module_manifest.json` regular file under examples/<organ_id>/; returns `[]` when that directory does not exist.
    - Fails: examples/<organ_id> not a dir -> returns `[]` (no raise).
    - Reads: examples/<organ_id>/**/source_module_manifest.json (recursive rglob).
    - Writes: None.
    """
    base = public_root / EXAMPLES_REL / organ_id
    if not base.is_dir():
        return []
    refs = [
        _display(path, public_root=public_root)
        for path in sorted(base.rglob("source_module_manifest.json"))
        if path.is_file()
    ]
    return list(dict.fromkeys(refs))


def _manifest_path(public_root: Path, ref: str) -> Path:
    """Join a manifest ref to its absolute path under the public root.

    - Teleology: keeps manifest existence/digest checks anchored to the resolved public root so refs resolve under the validated tree, not the process CWD.
    - Guarantee: returns `public_root / <ref with microcosm-substrate/ prefix stripped>`; existence is the caller's check, not asserted here.
    - Fails: None — pure path join; never inspects the filesystem, raises, or returns a failure envelope.
    - Writes: None.
    """
    clean = _strip_public_root_prefix(ref)
    return public_root / clean


def _module_row_target_path(
    public_root: Path,
    manifest_path: Path,
    module_row: dict[str, Any],
) -> tuple[Path, str]:
    """Resolve a module row's copied-body target to an (absolute path, display ref) pair.

    - Teleology: gives digest accounting one canonical target body to hash per module row, tolerating the three manifest shapes (target_ref, target_refs list, bare path).
    - Guarantee: returns `(target_path, display_ref)` using `target_ref` if set, else the first truthy entry of `target_refs`, else `manifest_path.parent / path`; display_ref is always public-root-relative.
    - Fails: never raises; an absent/empty ref yields a target_path that may not exist, which downstream `is_file()` treats as target_missing.
    - Reads: filesystem existence only via `_path_from_ref` (for target_ref/target_refs resolution).
    - Writes: None.
    """
    target_ref = str(module_row.get("target_ref") or "")
    if target_ref:
        target_path = _path_from_ref(public_root, target_ref, manifest_path=manifest_path)
        return target_path, _display(target_path, public_root=public_root)
    target_refs = module_row.get("target_refs")
    if isinstance(target_refs, list):
        for candidate_ref in target_refs:
            if not candidate_ref:
                continue
            target_path = _path_from_ref(
                public_root,
                str(candidate_ref),
                manifest_path=manifest_path,
            )
            return target_path, _display(target_path, public_root=public_root)
    path_ref = str(module_row.get("path") or "")
    target_path = manifest_path.parent / path_ref
    return target_path, _display(target_path, public_root=public_root)


def _manifest_module_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a source_module_manifest into uniform per-body module rows.

    - Teleology: protects digest/real-body accounting from manifest-shape drift by folding `modules`, `copied_macro_body_artifacts`, and `source_open_body_imports` into one row schema with normalized relation/digest/body flags.
    - Guarantee: returns a list of dicts each carrying module_id/source_ref/target_ref/source_to_target_relation/sha256/body_copied/body_in_receipt, with artifact copy_policy mapped to a relation and open-body imports zipped by index.
    - Fails: None — emits only what the manifest provides; missing blocks contribute zero rows rather than raising; never returns a failure envelope.
    - Reads: the in-memory manifest dict (modules, copied_macro_body_artifacts, source_open_body_imports, source_digests).
    - Writes: None.
    """
    rows = list(_rows(manifest, "modules"))
    for artifact in _rows(manifest, "copied_macro_body_artifacts"):
        copy_policy = str(artifact.get("copy_policy") or "")
        relation = str(artifact.get("source_to_target_relation") or "")
        if not relation and copy_policy == "exact_public_safe_runtime_artifact":
            relation = "exact_copy"
        elif not relation and copy_policy:
            relation = copy_policy
        rows.append(
            {
                "module_id": artifact.get("artifact_id"),
                "source_ref": artifact.get("source_ref"),
                "target_ref": artifact.get("target_ref"),
                "source_to_target_relation": relation,
                "sha256": artifact.get("target_sha256") or artifact.get("sha256"),
                "target_sha256": artifact.get("target_sha256") or artifact.get("sha256"),
                "body_copied": artifact.get("body_copied") is not False,
                "body_in_receipt": artifact.get("body_in_receipt") is True,
            }
        )
    source_open = manifest.get("source_open_body_imports")
    if isinstance(source_open, dict):
        material_ids = [
            str(value)
            for value in source_open.get("body_material_ids", [])
            if str(value).strip()
        ]
        source_refs = [
            str(value)
            for value in source_open.get("source_refs", [])
            if str(value).strip()
        ]
        target_refs = [
            str(value)
            for value in source_open.get("target_refs", [])
            if str(value).strip()
        ]
        source_digests = manifest.get("source_digests")
        source_digests = source_digests if isinstance(source_digests, dict) else {}
        for index, (source_ref, target_ref) in enumerate(zip(source_refs, target_refs, strict=False)):
            rows.append(
                {
                    "module_id": material_ids[index] if index < len(material_ids) else Path(target_ref).stem,
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "source_to_target_relation": "source_open_body_import_with_digest_provenance",
                    "sha256": source_digests.get(source_ref),
                    "body_copied": True,
                    "body_in_receipt": source_open.get("body_in_receipt") is True,
                }
            )
    return rows


def _digest_relation_rows(
    public_root: Path,
    manifest_refs: list[str],
) -> tuple[list[dict[str, Any]], list[str], list[str], int, int, int]:
    """Verify each manifest module's source/target/digest relation and tally real bodies.

    - Teleology: protects the "real substrate body, digest-fresh, provenance-backed" claim from drifted/missing targets, fixture/receipt sources, and stale pinned exact-copies being counted as real.
    - Guarantee: returns `(digest_rows, unique_macro_refs, unique_target_refs, supporting_body_count, receipt_body_count, digest_drift_disposition_count)`; each digest row carries computed actual/expected/source sha256, target/source existence, resolved relation, `status` (PASS only when target exists, target_digest matches, and any required source match holds), and `counts_as_real_body` only when body-copied + not-in-receipt + source role countable + relation present + target exists + status PASS (or non-exact-copy with matching target digest).
    - Fails: missing manifest file -> appends a `status:target_missing` / `missing_manifest` digest row and skips it; drifted exact_copy -> `status:blocked` with a `digest_drift_disposition` and excluded from real-body count.
    - Reads: each manifest_ref under public_root, each module target file, and source files under repo_root (public_root.parent) for sha256.
    - Writes: None.
    - When-needed: inspect when auditing whether an organ's claimed real bodies are digest-verified and provenance-clean.
    - Escalates-to: validate_ledger_payload real_body_* issue ids; per-row status/counts_as_real_body fields.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    digest_rows: list[dict[str, Any]] = []
    macro_refs: list[str] = []
    target_refs: list[str] = []
    supporting_body_count = 0
    receipt_body_count = 0
    digest_drift_disposition_count = 0
    repo_root = public_root.parent
    for manifest_ref in manifest_refs:
        manifest_path = _manifest_path(public_root, manifest_ref)
        if not manifest_path.is_file():
            digest_rows.append(
                {
                    "manifest_ref": manifest_ref,
                    "status": "target_missing",
                    "source_to_target_relation": "missing_manifest",
                }
            )
            continue
        manifest = _read_json_if_exists(manifest_path)
        for row in _manifest_module_rows(manifest):
            source_ref = str(row.get("source_ref") or "")
            if source_ref:
                macro_refs.append(source_ref)
            body_copied = row.get("body_copied") is True
            body_in_receipt = row.get("body_in_receipt") is True
            target_path, target_ref = _module_row_target_path(public_root, manifest_path, row)
            target_refs.append(target_ref)
            expected_digest = _normalize_sha256(row.get("sha256") or row.get("target_sha256"))
            declared_relation = str(row.get("source_to_target_relation") or "")
            material_class = str(row.get("material_class") or row.get("source_import_class") or "")
            actual_digest = _sha256_file(target_path) if target_path.is_file() else ""
            source_path = repo_root / source_ref if source_ref else None
            source_digest = (
                _sha256_file(source_path)
                if source_path is not None and source_path.is_file()
                else ""
            )
            source_matches_target = bool(source_digest and actual_digest) and source_digest == actual_digest
            if not expected_digest and source_matches_target:
                expected_digest = actual_digest
            target_digest_matches = bool(expected_digest and actual_digest) and expected_digest == actual_digest
            relation = declared_relation
            if not relation and source_matches_target:
                relation = "verified_exact_copy_inferred_from_matching_source_target_digest"
            if (
                not relation
                and row.get("classification") == "copied_non_secret_macro_body"
                and row.get("sha256_match") is True
                and body_copied
                and not body_in_receipt
            ):
                relation = "declared_public_safe_macro_body_copy"
            source_match_required = relation in {
                "exact_copy",
                "verified_exact_copy_inferred_from_matching_source_target_digest",
            } and bool(source_digest)
            status = (
                PASS
                if target_path.is_file()
                and target_digest_matches
                and (not source_match_required or source_matches_target)
                else "blocked"
            )
            digest_drift_disposition = None
            if relation == "exact_copy" and status != PASS:
                digest_drift_disposition = (
                    "pinned_historical_exact_copy_drift_not_counted_as_real_body_until_refreshed"
                )
                digest_drift_disposition_count += 1
            counts_as_real_body = (
                body_copied
                and not body_in_receipt
                and _source_can_count_as_real_body(source_ref, material_class)
                and bool(relation)
                and target_path.is_file()
                and (
                    status == PASS
                    or (
                        relation != "exact_copy"
                        and target_digest_matches
                    )
                )
            )
            if body_in_receipt:
                receipt_body_count += 1
            if counts_as_real_body:
                supporting_body_count += 1
            digest_row = {
                "manifest_ref": manifest_ref,
                "module_id": row.get("module_id"),
                "source_ref": source_ref,
                "target_ref": target_ref,
                "source_to_target_relation": relation,
                "expected_sha256": expected_digest,
                "actual_target_sha256": actual_digest,
                "source_sha256": source_digest,
                "target_exists": target_path.is_file(),
                "source_exists": source_path.is_file() if source_path is not None else False,
                "body_copied": body_copied,
                "body_in_receipt": body_in_receipt,
                "manifest_material_class": material_class,
                "source_authority_role": _source_authority_role(source_ref, material_class),
                "counts_as_real_body": counts_as_real_body,
                "status": status,
            }
            if digest_drift_disposition:
                digest_row["digest_drift_disposition"] = digest_drift_disposition
            digest_rows.append(
                digest_row
            )
    return (
        digest_rows,
        list(dict.fromkeys(macro_refs)),
        list(dict.fromkeys(target_refs)),
        supporting_body_count,
        receipt_body_count,
        digest_drift_disposition_count,
    )


def _count_from_source_open_fixture(fixture: dict[str, Any]) -> int:
    """Read the fixture-declared open-body material count.

    - Teleology: surfaces what a fixture CLAIMS as body count so the ledger can contrast it against the examples-manifest-verified count and demote fixture claims to non-authority.
    - Guarantee: returns the int `source_open_body_imports.body_material_count`; returns `0` when the block or field is missing or not an int.
    - Fails: never raises; malformed/absent input -> `0`.
    - Reads: the in-memory fixture dict only (no filesystem).
    - Writes: None.
    """
    source_open = fixture.get("source_open_body_imports")
    if not isinstance(source_open, dict):
        return 0
    value = source_open.get("body_material_count")
    return int(value) if isinstance(value, int) else 0


def _disposition_for(row: dict[str, Any], supporting_body_count: int) -> str:
    """Classify a registry row into its substrate-substitution disposition.

    - Teleology: the core state-machine assignment that routes each accepted organ to real_substrate_capsule, retained_regression_validator, or deleted_demoted_historical_artifact, enforcing that fixtures and body-free organs cannot pose as real substrate.
    - Guarantee: returns RETAINED_REGRESSION_VALIDATOR when evidence_class is fixture_echo_smoke or bucket is regression_negative_fixture; else REAL_SUBSTRATE_CAPSULE when supporting_body_count > 0; else DELETED_DEMOTED_HISTORICAL_ARTIFACT.
    - Fails: never raises; missing fields stringify to "" and fall through to the body-count branch.
    - Reads: the registry row's evidence_class/truth_accounting_bucket and the precomputed supporting_body_count (no filesystem).
    - Writes: None.
    - When-needed: inspect when an organ's disposition seems wrong; compare evidence_class/bucket and verified body count.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    evidence_class = str(row.get("evidence_class") or "")
    bucket = str(row.get("truth_accounting_bucket") or "")
    if evidence_class == FIXTURE_ECHO_CLASS or bucket == REGRESSION_FIXTURE_BUCKET:
        return RETAINED_REGRESSION_VALIDATOR
    if supporting_body_count > 0:
        return REAL_SUBSTRATE_CAPSULE
    return DELETED_DEMOTED_HISTORICAL_ARTIFACT


def _body_support_class(manifest_refs: list[str], supporting_body_count: int) -> str:
    """Label the kind of body support a row has, for the real-capsule gate.

    - Teleology: gives the validator a single field to assert that a real capsule's body support is manifest-verified, not merely asserted.
    - Guarantee: returns `source_module_manifest_verified_body` only when there is at least one manifest ref AND supporting_body_count > 0; otherwise `none_verified`.
    - Fails: never raises; empty refs or zero count -> `none_verified` (which the validator flags for real capsules).
    - Reads: the in-memory manifest_refs list and count (no filesystem).
    - Writes: None.
    """
    if supporting_body_count > 0 and manifest_refs:
        return "source_module_manifest_verified_body"
    return "none_verified"


def _fixture_role(disposition: str, fixture_path: Path | None, supporting_body_count: int) -> str:
    """Describe the non-authority role a fixture plays for an organ row.

    - Teleology: encodes the doctrine that fixtures are input or regression wrappers, never body authority, so the ledger can name a fixture's role without ever crediting it as substrate.
    - Guarantee: returns one of `retained_regression_negative_wrapper_only` (retained disposition), `regression_wrapper_around_real_substrate` (fixture + verified bodies), `fixture_input_only_not_authority` (fixture, no bodies), or `no_fixture_authority` (no fixture).
    - Fails: never raises; precedence is disposition first, then presence-of-fixture and body count.
    - Reads: the disposition string, fixture_path presence, and count (no filesystem).
    - Writes: None.
    """
    if disposition == RETAINED_REGRESSION_VALIDATOR:
        return "retained_regression_negative_wrapper_only"
    if fixture_path is not None and supporting_body_count:
        return "regression_wrapper_around_real_substrate"
    if fixture_path is not None:
        return "fixture_input_only_not_authority"
    return "no_fixture_authority"


def _examples_fixtures_consistency(
    *,
    disposition: str,
    supporting_body_count: int,
    fixture_source_body_count: int,
) -> str:
    """Reconcile examples-manifest body count against fixture-declared body count.

    - Teleology: makes the examples-manifest the authority over fixture claims so a fixture under-/over-counting bodies cannot silently distort accounting; the validator flags `contradiction_unexplained` if it ever appears.
    - Guarantee: returns `fixture_body_support_demoted_to_regression_not_authority` for retained fixtures; `examples_body_manifest_controls_fixture_zero_receipt` when manifests verify bodies but the fixture declared zero; else `consistent`.
    - Fails: never raises; this function emits no `contradiction_unexplained` (that value is checked by the validator but produced elsewhere); all inputs are ints/strings.
    - Reads: the disposition and two precomputed counts (no filesystem).
    - Writes: None.
    """
    if disposition == RETAINED_REGRESSION_VALIDATOR:
        return "fixture_body_support_demoted_to_regression_not_authority"
    if supporting_body_count and fixture_source_body_count == 0:
        return "examples_body_manifest_controls_fixture_zero_receipt"
    return "consistent"


def _public_commands(organ_id: str, validator_command: str) -> list[str]:
    """Assemble the public, runnable exercise commands for an organ row.

    - Teleology: backs the "real capsule has a runnable public exercise command connected to its body" claim that the validator enforces against real_substrate_capsule rows.
    - Guarantee: returns `[validator_command]` (omitting it when empty) plus the two PROVER_SMOKE_COMMANDS appended only for organ_id `verifier_lab_kernel`.
    - Fails: None — always returns a list (possibly empty); never raises or returns a failure envelope. (Emptiness is later flagged downstream by real_capsule_missing_public_exercise_command, not here.)
    - Writes: None.
    """
    commands = [validator_command] if validator_command else []
    if organ_id == "verifier_lab_kernel":
        commands.extend(PROVER_SMOKE_COMMANDS)
    return commands


def _organ_source_path(public_root: Path, organ_id: str) -> Path:
    """Map an organ id to its source module path under the public root.

    - Teleology: the single place that names where an organ's body lives, so source-compute inspection always reads the right module.
    - Guarantee: returns `public_root / src/microcosm_core/organs / <organ_id>.py`; existence is the caller's concern.
    - Fails: never raises; pure path join, no filesystem touch.
    - Writes: None.
    """
    return public_root / "src/microcosm_core/organs" / f"{organ_id}.py"


def _name_promise_terms(organ_id: str) -> list[str]:
    """Extract the compute-promise terms embedded in an organ's id.

    - Teleology: detects when an organ's NAME promises a mechanism (interpret/prove/simulate/...), which AP-15 uses to demand runtime-compute evidence or a bound claim ceiling.
    - Guarantee: returns the sorted subset of COMPUTE_PROMISE_TERMS appearing as `_`/`-`-delimited tokens in the organ id; returns `[]` when none match.
    - Fails: never raises; tokenization is split-only on a stringified id.
    - Reads: the organ_id string and the COMPUTE_PROMISE_TERMS constant (no filesystem).
    - Writes: None.
    """
    tokens = {
        token
        for token in organ_id.replace("-", "_").split("_")
        if token in COMPUTE_PROMISE_TERMS
    }
    return sorted(tokens)


def _call_name(node: ast.AST) -> str:
    """Resolve the callee name of an AST call target.

    - Teleology: lets source-compute detection recognize runtime helper calls (`_gridworld_step`, `forward`, `np.*`) regardless of plain-name vs attribute form.
    - Guarantee: returns `node.id` for an ast.Name, `node.attr` for an ast.Attribute, else `""`.
    - Fails: never raises; any other node type -> `""`.
    - Reads: the AST node only.
    - Writes: None.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _target_names(node: ast.AST) -> set[str]:
    """Collect the bound names of an assignment target, flattening unpacking.

    - Teleology: lets runtime-compute detection see which variables an assignment binds (e.g. `gradient_scores`, `ablation_result`) even through tuple/list unpacking.
    - Guarantee: returns `{node.id}` for a Name, `{node.attr}` for an Attribute, the recursive union of element names for a Tuple/List, else `set()`.
    - Fails: never raises; unrecognized target node -> empty set.
    - Reads: the AST node only.
    - Writes: None.
    """
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for item in node.elts:
            names.update(_target_names(item))
        return names
    if isinstance(node, ast.Attribute):
        return {node.attr}
    return set()


def _dict_key_strings(node: ast.AST) -> set[str]:
    """Collect literal string keys from a dict (or sequence of dicts) AST node.

    - Teleology: detects "receipt-returning" functions and runtime result keys (`gradient_scores`, `ablation_result`, `predicted_actual_match_count`) by inspecting returned dict literals.
    - Guarantee: returns the set of constant string keys of an ast.Dict, unioned recursively over Tuple/List elements; returns `set()` for any other node.
    - Fails: never raises; non-string/computed keys are ignored.
    - Reads: the AST node only.
    - Writes: None.
    """
    keys: set[str] = set()
    if isinstance(node, ast.Dict):
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for item in node.elts:
            keys.update(_dict_key_strings(item))
    return keys


def _function_has_runtime_structure(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Heuristically decide whether a function body performs real runtime compute.

    - Teleology: distinguishes a function that actually computes a receipt (arithmetic/control-flow/runtime calls feeding a dict return) from a cosmetic stub, backing the AP-15 mechanism-theater check.
    - Guarantee: returns True only when the function both returns a dict literal (receipt) AND contains arithmetic (BinOp/UnaryOp/AugAssign), control flow (loops/if/comprehensions), or a known runtime/aggregation call (`_gridworld_step`, `forward`, `len`, `sum`, ...); else False.
    - Fails: never raises; a function without a dict-returning shape returns False regardless of its arithmetic.
    - Reads: the function AST subtree only (ast.walk).
    - Writes: None.
    """
    has_arithmetic = any(
        isinstance(node, (ast.BinOp, ast.UnaryOp, ast.AugAssign))
        for node in ast.walk(function)
    )
    has_control_flow = any(
        isinstance(
            node,
            (
                ast.For,
                ast.While,
                ast.If,
                ast.ListComp,
                ast.DictComp,
                ast.SetComp,
                ast.GeneratorExp,
            ),
        )
        for node in ast.walk(function)
    )
    has_receipt_return = any(
        isinstance(node, ast.Return) and bool(_dict_key_strings(node.value))
        for node in ast.walk(function)
    )
    has_runtime_call = any(
        _call_name(node.func)
        in {
            "_gridworld_step",
            "_toy_transformer_forward",
            "_vector_matrix_product",
            "abs",
            "len",
            "max",
            "range",
            "round",
            "sum",
        }
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    )
    return has_receipt_return and (
        has_arithmetic or has_control_flow or has_runtime_call
    )


def _compute_import_markers_from_ast(tree: ast.AST) -> list[str]:
    """Detect numeric-compute imports (numpy/torch/scipy) in a parsed module.

    - Teleology: surfaces hard evidence that an organ links a real compute stack, one of the two signals that an honest mechanism backs a name promise.
    - Guarantee: returns the subset of COMPUTE_IMPORT_MARKERS (`import numpy`, `from torch`, ...) actually present, in COMPUTE_IMPORT_MARKERS order; returns `[]` when none import numpy/torch/scipy.
    - Fails: never raises on a valid AST; only top-level package of each import is matched (e.g. `numpy.linalg` -> `import numpy`).
    - Reads: the AST tree only (ast.walk).
    - Writes: None.
    """
    markers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                package = alias.name.split(".", 1)[0]
                if package in {"numpy", "torch", "scipy"}:
                    markers.add(f"import {package}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            package = node.module.split(".", 1)[0]
            if package in {"numpy", "torch", "scipy"}:
                markers.add(f"from {package}")
    return [marker for marker in COMPUTE_IMPORT_MARKERS if marker in markers]


def _runtime_compute_markers_from_ast(tree: ast.AST) -> list[str]:
    """Detect in-body runtime-compute markers across a module's functions.

    - Teleology: gathers the runtime-mechanism evidence (gridworld/transformer steps, `np.` use, gradient/ablation assignments, predicted-actual keys) that lets a mechanism-term name promise be honestly backed rather than theater.
    - Guarantee: returns the subset of RUNTIME_COMPUTE_MARKERS present, in RUNTIME_COMPUTE_MARKERS order, considering only functions that pass `_function_has_runtime_structure`; returns `[]` when no such evidence exists.
    - Fails: never raises on a valid AST; functions without runtime structure are skipped entirely.
    - Reads: the AST tree only (ast.walk over each qualifying function).
    - Writes: None.
    """
    markers: set[str] = set()
    for function in (
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        if not _function_has_runtime_structure(function):
            continue
        function_marker = RUNTIME_FUNCTION_MARKERS.get(function.name)
        if function_marker:
            markers.add(function_marker)

        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                if call_name == "_toy_transformer_forward" or call_name == "forward":
                    markers.add("forward(")
                continue
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "np"
            ):
                markers.add("np.")
                continue
            if isinstance(node, ast.Assign):
                target_names: set[str] = set()
                for target in node.targets:
                    target_names.update(_target_names(target))
                for target_name in target_names:
                    marker = RUNTIME_ASSIGNMENT_MARKERS.get(target_name)
                    if marker:
                        markers.add(marker)
                continue
            if isinstance(node, ast.AnnAssign):
                for target_name in _target_names(node.target):
                    marker = RUNTIME_ASSIGNMENT_MARKERS.get(target_name)
                    if marker:
                        markers.add(marker)
                continue
            if isinstance(node, ast.Return):
                for key in _dict_key_strings(node.value):
                    marker = RUNTIME_KEY_MARKERS.get(key)
                    if marker:
                        markers.add(marker)

    return [marker for marker in RUNTIME_COMPUTE_MARKERS if marker in markers]


def _source_compute_evidence(public_root: Path, organ_id: str) -> dict[str, Any]:
    """Inspect an organ's source for compute import + runtime-compute evidence.

    - Teleology: produces the per-organ evidence record that the AP-15 name-promise axis consumes to decide mechanism-theater vs runtime-backed, reading the actual organ body.
    - Guarantee: returns a dict with `source_ref` (display ref), `source_exists`, `compute_import_markers`, and `runtime_compute_markers`; markers are empty when the source is absent, fails the cheap prefilter, or does not parse.
    - Fails: never raises; a missing file returns source_exists False + empty markers; a SyntaxError yields empty markers with source_exists True.
    - Reads: the organ source module under public_root (text + AST parse).
    - Writes: None.
    """
    source_path = _organ_source_path(public_root, organ_id)
    if not source_path.is_file():
        return {
            "source_ref": _display(source_path, public_root=public_root),
            "source_exists": False,
            "compute_import_markers": [],
            "runtime_compute_markers": [],
        }
    text = source_path.read_text(encoding="utf-8")
    if not any(term in text for term in SOURCE_COMPUTE_PREFILTER_TERMS):
        return {
            "source_ref": _display(source_path, public_root=public_root),
            "source_exists": True,
            "compute_import_markers": [],
            "runtime_compute_markers": [],
        }
    try:
        tree = ast.parse(text)
    except SyntaxError:
        tree = None
    return {
        "source_ref": _display(source_path, public_root=public_root),
        "source_exists": True,
        "compute_import_markers": _compute_import_markers_from_ast(tree)
        if tree is not None
        else [],
        "runtime_compute_markers": _runtime_compute_markers_from_ast(tree)
        if tree is not None
        else [],
    }


def _name_promise_axis(
    *,
    public_root: Path,
    organ_id: str,
    evidence_class: str,
    source_compute_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the AP-15 mechanism-theater name-promise axis for one organ.

    - Teleology: protects the public surface from an organ whose NAME promises a mechanism (interpret/simulate/...) while its risky evidence class has no runtime compute, by emitting a status + scheduler_target the validator enforces.
    - Guarantee: returns a `microcosm_name_promise_axis_v1` dict whose `status` is exactly one of name_promise_mechanism_theater, name_promise_backed_by_runtime_compute, name_promise_non_runtime_obligation_in_risky_class, name_promise_not_in_risky_evidence_class, or no_compute_name_promise, with the matching scheduler_target and the evidence fields that drove it.
    - Fails: never raises; absent source/evidence yields empty marker lists and routes to a non-theater status; this is a pure projection, not a gate.
    - Reads: source-compute evidence (passed-in, else recomputed from the organ source under public_root).
    - Writes: None.
    - When-needed: inspect when an organ is flagged name_promise_mechanism_theater or its next_repair is stale.
    - Escalates-to: AP-15::mechanism_theater_name_promise policy; validate_ledger_payload name_promise_axis_* issues.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    terms = _name_promise_terms(organ_id)
    evidence = source_compute_evidence or _source_compute_evidence(
        public_root,
        organ_id,
    )
    has_compute_evidence = bool(
        evidence["compute_import_markers"] or evidence["runtime_compute_markers"]
    )
    risky_evidence_class = evidence_class in NAME_PROMISE_RISK_CLASSES
    theater_terms = sorted(set(terms) & MECHANISM_THEATER_PROMISE_TERMS)
    mismatch = bool(theater_terms and risky_evidence_class and not has_compute_evidence)
    if mismatch:
        status = "name_promise_mechanism_theater"
        scheduler_target = "replace_cosmetic_validator_target_with_mechanism_repair"
    elif terms and has_compute_evidence:
        status = "name_promise_backed_by_runtime_compute"
        scheduler_target = "maintain_runtime_compute_receipts"
    elif terms and risky_evidence_class:
        # The name carries a mechanism term and the evidence class is risky, but
        # the term is not one AP-15 treats as a runtime-compute obligation
        # (e.g. proof/world/repair/discover, not attribute/simulate/interpret),
        # so this is not mechanism theater. The validator or projection itself is
        # the mechanism and the honest obligation is a bound claim ceiling rather
        # than in-organ runtime compute. Emitting "not_in_risky_evidence_class"
        # here would contradict the row's own risky_evidence_class=True
        # (AP-17 projection-as-source: a status must not lie about its own fields).
        status = "name_promise_non_runtime_obligation_in_risky_class"
        scheduler_target = "maintain_claim_ceiling"
    elif terms:
        status = "name_promise_not_in_risky_evidence_class"
        scheduler_target = "maintain_claim_ceiling"
    else:
        status = "no_compute_name_promise"
        scheduler_target = "maintain_current_disposition"
    return {
        "schema_version": "microcosm_name_promise_axis_v1",
        "policy_ref": "AP-15::mechanism_theater_name_promise",
        "status": status,
        "name_promise_terms": terms,
        "mechanism_theater_terms": theater_terms,
        "risky_evidence_class": risky_evidence_class,
        "source_ref": evidence["source_ref"],
        "source_exists": evidence["source_exists"],
        "compute_import_markers": evidence["compute_import_markers"],
        "runtime_compute_markers": evidence["runtime_compute_markers"],
        "source_inspection_found_runtime_compute": has_compute_evidence,
        "scheduler_target": scheduler_target,
    }


def _ledger_row(
    public_root: Path,
    registry_row: dict[str, Any],
    *,
    validation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the full substrate-disposition row for one accepted organ.

    - Teleology: composes the single authoritative ledger row (disposition, digest relation, body counts, name-promise axis, claim ceiling, next repair) that downstream validation and the public site consume per organ.
    - Guarantee: returns a dict whose disposition comes from `_disposition_for`, whose real_body_count is the supporting count only when disposition is real_substrate_capsule (else 0), and whose digest_relation/name_promise/body_support fields are derived from on-disk manifests + organ source — never from fixture claims.
    - Fails: never raises; a missing fixture/manifest/source degrades to empty refs and a deleted_demoted disposition rather than an error.
    - Reads: fixture manifest, examples source-module manifests, manifest target/source bodies, and organ source compute evidence under public_root.
    - Writes: None.
    - When-needed: inspect to see exactly what evidence produced an organ's disposition and body credit.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    organ_id = str(registry_row.get("organ_id") or "")
    fixture_path, fixture = _fixture_manifest(public_root, organ_id)
    direct_manifest_refs = _direct_source_module_manifest_refs(public_root, organ_id)
    fixture_manifest_refs = _source_manifest_refs_from_fixture(fixture)
    manifest_refs = list(dict.fromkeys([*direct_manifest_refs, *fixture_manifest_refs]))
    (
        digest_rows,
        macro_refs,
        target_refs,
        supporting_body_count,
        receipt_body_count,
        digest_drift_disposition_count,
    ) = _digest_relation_rows(public_root, manifest_refs)
    fixture_source_body_count = _count_from_source_open_fixture(fixture)
    macro_refs = list(dict.fromkeys([*macro_refs, *_source_refs_from_fixture(fixture)]))
    disposition = _disposition_for(registry_row, supporting_body_count)
    real_body_count = (
        supporting_body_count if disposition == REAL_SUBSTRATE_CAPSULE else 0
    )
    validator_command = str(registry_row.get("validator_command") or "")
    public_commands = _public_commands(organ_id, validator_command)
    source_evidence = _source_compute_evidence_from_context(
        validation_context,
        organ_id,
    )
    name_promise = _name_promise_axis(
        public_root=public_root,
        organ_id=organ_id,
        evidence_class=str(registry_row.get("evidence_class") or ""),
        source_compute_evidence=source_evidence,
    )
    return {
        "organ_id": organ_id,
        "accepted_authority": True,
        "registry_status": registry_row.get("status"),
        "evidence_class": registry_row.get("evidence_class"),
        "truth_accounting_bucket": registry_row.get("truth_accounting_bucket"),
        "counts_as_real_substrate_progress": registry_row.get(
            "counts_as_real_substrate_progress"
        )
        is True,
        "disposition": disposition,
        "macro_refs": macro_refs,
        "microcosm_target_refs": list(dict.fromkeys(target_refs + manifest_refs)),
        "source_module_manifest_refs": manifest_refs,
        "digest_relation": digest_rows,
        "digest_relation_status": PASS
        if all(row.get("status") == PASS for row in digest_rows)
        else "blocked",
        "fixture_manifest_ref": _display(fixture_path, public_root=public_root)
        if fixture_path
        else None,
        "fixture_role": _fixture_role(disposition, fixture_path, supporting_body_count),
        "acceptance_command": validator_command,
        "public_exercise_commands": public_commands,
        "real_body_count": real_body_count,
        "supporting_body_count": supporting_body_count,
        "body_support_class": _body_support_class(manifest_refs, supporting_body_count),
        "receipt_body_count": receipt_body_count,
        "fixture_declared_body_count": fixture_source_body_count,
        "digest_drift_disposition_count": digest_drift_disposition_count,
        "examples_fixtures_consistency": _examples_fixtures_consistency(
            disposition=disposition,
            supporting_body_count=supporting_body_count,
            fixture_source_body_count=fixture_source_body_count,
        ),
        "stale_standard_language_status": "anti_claim_language_only",
        "name_promise": name_promise,
        "claim_ceiling": registry_row.get("claim_ceiling"),
        "claim_ceiling_source": "core/organ_registry.json",
        "next_repair": _next_repair(disposition, name_promise),
    }


def _next_repair(disposition: str, name_promise: dict[str, Any] | None = None) -> str:
    """Derive the actionable next-repair string for a row's disposition + axis.

    - Teleology: gives each row a single concrete remediation, prioritizing AP-15 mechanism-theater repair over disposition-based maintenance, so the ledger doubles as a worklist.
    - Guarantee: returns the mechanism-repair string when name_promise.status is name_promise_mechanism_theater; else a disposition-specific string for real_substrate_capsule / retained_regression_validator / (default) demoted artifact.
    - Fails: never raises; a None or non-dict name_promise simply skips the theater branch.
    - Reads: the disposition string and name_promise dict (no filesystem).
    - Writes: None.
    """
    if (
        isinstance(name_promise, dict)
        and name_promise.get("status") == "name_promise_mechanism_theater"
    ):
        return "mechanism repair: add small real runtime compute or rename/demote the organ"
    if disposition == REAL_SUBSTRATE_CAPSULE:
        return "maintain digest freshness and keep public exercise command green"
    if disposition == RETAINED_REGRESSION_VALIDATOR:
        return "retain only as negative/regression wrapper until a real substrate capsule exists"
    return "remove from accepted authority or import public-safe real substrate"


def _name_promise_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-organ name-promise axes into a ledger-level summary.

    - Teleology: gives the ledger summary one place to report mechanism-theater pressure and its repair targets, and gives the validator a recomputable summary to detect staleness.
    - Guarantee: returns a `microcosm_name_promise_summary_v1` dict with status_counts over each row's name_promise.status, a mechanism_theater_count, and a mechanism_repair_targets list (one entry per mechanism-theater organ with its terms/scheduler_target/next_repair).
    - Fails: never raises; rows missing name_promise contribute the `""` status bucket.
    - Reads: the in-memory rows list (no filesystem).
    - Writes: None.
    """
    name_promise_counts: dict[str, int] = {}
    for row in rows:
        status = str((row.get("name_promise") or {}).get("status") or "")
        name_promise_counts[status] = name_promise_counts.get(status, 0) + 1
    mechanism_repair_targets = [
        {
            "organ_id": row.get("organ_id"),
            "name_promise_terms": (row.get("name_promise") or {}).get(
                "name_promise_terms",
                [],
            ),
            "scheduler_target": (row.get("name_promise") or {}).get(
                "scheduler_target"
            ),
            "next_repair": row.get("next_repair"),
        }
        for row in rows
        if (row.get("name_promise") or {}).get("status")
        == "name_promise_mechanism_theater"
    ]
    return {
        "schema_version": "microcosm_name_promise_summary_v1",
        "policy_ref": "AP-15::mechanism_theater_name_promise",
        "status_counts": name_promise_counts,
        "mechanism_theater_count": name_promise_counts.get(
            "name_promise_mechanism_theater",
            0,
        ),
        "mechanism_repair_targets": mechanism_repair_targets,
    }


def _count_reconciliation(public_root: Path, accepted_count: int) -> dict[str, Any]:
    """Reconcile registry accepted count against acceptance plan + summary.

    - Teleology: protects the accepted-organ count from a stale acceptance summary or drifted plan silently disagreeing with the registry, demoting a divergent summary to receipt-not-authority.
    - Guarantee: returns a dict with `status` = PASS when plan_count == accepted_count AND the summary either agrees, is an explicit (recorded) divergence, or is absent; else `blocked`. Records the three counts and a divergence_disposition.
    - Fails: never raises; missing plan/summary files read as empty and yield plan_count 0 / summary_count None (blocking only if the plan count then mismatches).
    - Reads: core/acceptance/first_wave_acceptance.json and receipts/first_wave/acceptance_summary.json under public_root.
    - Writes: None.
    """
    plan = _read_json_if_exists(public_root / ACCEPTANCE_PLAN_REL)
    summary = _read_json_if_exists(public_root / ACCEPTANCE_SUMMARY_REL)
    plan_count = len(_rows(plan, "accepted_current_authority_organs"))
    summary_count = summary.get("accepted_current_authority_count")
    if not isinstance(summary_count, int):
        summary_count = summary.get("accepted_count")
    explicit_summary_divergence = (
        isinstance(summary_count, int) and summary_count != accepted_count
    )
    return {
        "status": PASS
        if plan_count == accepted_count
        and (
            summary_count == accepted_count
            or explicit_summary_divergence
            or summary_count is None
        )
        else "blocked",
        "registry_accepted_count": accepted_count,
        "acceptance_plan_count": plan_count,
        "acceptance_summary_count": summary_count,
        "divergence_disposition": "acceptance_summary_stale_projection_demoted_to_receipt_not_authority"
        if explicit_summary_divergence
        else "counts_aligned",
    }


def _build_validation_context(
    public_root: str | Path,
    *,
    accepted_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Precompute the shared accepted-ids + source-compute evidence context.

    - Teleology: lets build and validation share one resolved root, one accepted-id list, and one source-compute scan per organ, so name-promise recomputation in the validator matches the builder exactly (no double-scan drift).
    - Guarantee: returns a dict with `public_root` (resolved), `accepted_ids` (from accepted_rows or the registry), and `source_compute_evidence_by_organ` mapping each accepted id to its `_source_compute_evidence` record.
    - Fails: raises only if the registry read fails when accepted_rows is None (via _accepted_registry_rows).
    - Reads: organ registry (when accepted_rows omitted) and each accepted organ's source module under the resolved root.
    - Writes: None.
    """
    root = _public_root_for_path(public_root)
    rows = accepted_rows if accepted_rows is not None else _accepted_registry_rows(root)
    accepted_ids = [
        str(row.get("organ_id"))
        for row in rows
        if row.get("organ_id")
    ]
    return {
        "public_root": root,
        "accepted_ids": accepted_ids,
        "source_compute_evidence_by_organ": {
            organ_id: _source_compute_evidence(root, organ_id)
            for organ_id in accepted_ids
        },
    }


def _source_compute_evidence_from_context(
    validation_context: dict[str, Any] | None,
    organ_id: str,
) -> dict[str, Any] | None:
    """Look up an organ's precomputed source-compute evidence from the context.

    - Teleology: lets the row builder and validator reuse the one-time source scan instead of re-reading each organ body, keeping their name-promise axes identical.
    - Guarantee: returns the cached evidence dict for organ_id when present in `validation_context.source_compute_evidence_by_organ`; returns None when the context, the map, or the entry is missing or wrong-typed.
    - Fails: never raises; any shape mismatch -> None (callers then recompute fresh).
    - Reads: the in-memory validation_context only (no filesystem).
    - Writes: None.
    """
    if not isinstance(validation_context, dict):
        return None
    evidence_by_organ = validation_context.get("source_compute_evidence_by_organ")
    if not isinstance(evidence_by_organ, dict):
        return None
    evidence = evidence_by_organ.get(organ_id)
    return evidence if isinstance(evidence, dict) else None


def build_ledger(public_root: str | Path) -> dict[str, Any]:
    """Build the full substrate-substitution ledger payload from disk.

    - Teleology: the canonical projection that turns the organ registry + manifests + organ sources into the disposition ledger (real_substrate_capsule / retained_regression / demoted) plus its embedded validation receipt.
    - Guarantee: returns a `microcosm_substrate_substitution_ledger_v1` dict with per-organ rows, disposition_counts, name_promise + count_reconciliation summaries, an embedded `validation`, and a `status` mirroring that validation (PASS only when zero issues); real-substrate counts come only from real_substrate_capsule rows.
    - Fails: never raises for normal substrate; raises only if the organ registry is missing/malformed (read_json_strict). A blocked validation yields `status:blocked`, not an exception.
    - Reads: registry, acceptance plan/summary, fixture manifests, examples source-module manifests + bodies, organ sources under the resolved public root.
    - Writes: None — pure projection; persistence is write_ledger's job.
    - When-needed: call to inspect or regenerate the current ledger without writing.
    - Escalates-to: validate_ledger_payload; std organ-registry authority floor + tests/test_organ_registry_authority_floor.py.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    root = _public_root_for_path(public_root)
    accepted_rows = _accepted_registry_rows(root)
    validation_context = _build_validation_context(root, accepted_rows=accepted_rows)
    rows = [
        _ledger_row(root, row, validation_context=validation_context)
        for row in accepted_rows
    ]
    disposition_counts: dict[str, int] = {}
    for row in rows:
        disposition = str(row.get("disposition") or "")
        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
    name_promise_summary = _name_promise_summary(rows)
    validation = validate_ledger_payload(
        {
            "organ_substrate_dispositions": rows,
            "summary": {
                "accepted_organ_count": len(rows),
                "disposition_counts": disposition_counts,
                "name_promise": name_promise_summary,
                "count_reconciliation": _count_reconciliation(root, len(rows)),
            },
        },
        public_root=root,
        validation_context=validation_context,
    )
    return {
        "schema_version": "microcosm_substrate_substitution_ledger_v1",
        "ledger_id": "microcosm_substrate_substitution_ledger",
        "checker_id": CHECKER_ID,
        "status": validation["status"],
        "source_surfaces": [
            REGISTRY_REL.as_posix(),
            ACCEPTANCE_PLAN_REL.as_posix(),
            ACCEPTANCE_SUMMARY_REL.as_posix(),
            "core/fixture_manifests/*.fixture_manifest.json",
            "examples/**/source_module_manifest.json",
        ],
        "state_machine": {
            REAL_SUBSTRATE_CAPSULE: (
                "copied or public-safe-refactored non-secret macro code, proof, "
                "control-plane, or mechanism body with provenance, digest relation, "
                "target body, runnable public command, and claim ceiling"
            ),
            RETAINED_REGRESSION_VALIDATOR: (
                "synthetic fixture retained only as a negative/regression wrapper; "
                "excluded from body-import, readiness, impressiveness, and validation "
                "authority counts"
            ),
            DELETED_DEMOTED_HISTORICAL_ARTIFACT: (
                "historical or body-free artifact that cannot remain accepted "
                "authority without a public-safe real substrate capsule"
            ),
        },
        "summary": {
            "status": validation["status"],
            "accepted_organ_count": len(rows),
            "disposition_counts": disposition_counts,
            "real_substrate_capsule_count": disposition_counts.get(
                REAL_SUBSTRATE_CAPSULE, 0
            ),
            "retained_regression_validator_count": disposition_counts.get(
                RETAINED_REGRESSION_VALIDATOR, 0
            ),
            "deleted_demoted_historical_artifact_count": disposition_counts.get(
                DELETED_DEMOTED_HISTORICAL_ARTIFACT, 0
            ),
            "real_body_count": sum(int(row.get("real_body_count") or 0) for row in rows),
            "receipt_body_count": sum(
                int(row.get("receipt_body_count") or 0) for row in rows
            ),
            "digest_drift_disposition_count": sum(
                int(row.get("digest_drift_disposition_count") or 0) for row in rows
            ),
            "fixture_authority_ban_status": PASS
            if validation["status"] == PASS
            else "blocked",
            "name_promise": name_promise_summary,
            "count_reconciliation": _count_reconciliation(root, len(rows)),
            "validation_issue_count": validation["issue_count"],
        },
        "organ_substrate_dispositions": rows,
        "validation": validation,
        "anti_claim": (
            "This ledger is an enforcement index over public substrate disposition. "
            "It does not make fixture-only rows impressive; retained fixtures are "
            "negative/regression wrappers and real-substrate counts come only from "
            "rows with real_substrate_capsule disposition."
        ),
    }


def _rows_by_organ_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a ledger payload's disposition rows by organ id.

    - Teleology: gives the organ-slice merge an O(1) lookup of current/rebuilt rows so a targeted write can splice one organ without rebuilding the whole list.
    - Guarantee: returns a dict mapping organ_id -> row for every disposition row carrying a truthy organ_id; later duplicates overwrite earlier ones.
    - Fails: never raises; a malformed payload yields `{}` via `_rows`.
    - Reads: the in-memory payload only (no filesystem).
    - Writes: None.
    """
    return {
        str(row.get("organ_id")): row
        for row in _rows(payload, "organ_substrate_dispositions")
        if row.get("organ_id")
    }


def _ordered_ids_for_organ_slice(
    public_root: Path,
    current: dict[str, Any],
    rebuilt: dict[str, Any],
    organ_ids: set[str],
) -> list[str]:
    """Choose the canonical row ordering for an organ-slice merge.

    - Teleology: keeps the merged ledger's row order stable and registry-aligned so a targeted slice write does not reshuffle unrelated rows.
    - Guarantee: returns the registry accepted-id order when the registry exists; else the current rows' order, appended with any rebuilt id that is in the selected slice and not already present.
    - Fails: never raises; missing registry falls back to current/rebuilt orderings.
    - Reads: organ registry under public_root (existence-guarded).
    - Writes: None.
    """
    registry_ids = _expected_accepted_ids_if_registry_exists(public_root)
    if registry_ids:
        return registry_ids
    ordered_ids = list(_rows_by_organ_id(current))
    for organ_id in _rows_by_organ_id(rebuilt):
        if organ_id in organ_ids and organ_id not in ordered_ids:
            ordered_ids.append(organ_id)
    return ordered_ids


def _summary_and_validation_for_rows(
    public_root: Path,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recompute the ledger summary + validation for an arbitrary row set.

    - Teleology: lets an organ-slice merge re-derive a consistent summary and full validation over the spliced rows, so a partial write is still validated as a whole ledger.
    - Guarantee: returns `(summary, validation)` where summary carries disposition/body/receipt/drift counts and name_promise + count_reconciliation, and its `status` / fixture_authority_ban_status / validation_issue_count are reconciled to the freshly run `validate_ledger_payload` (PASS only when zero issues).
    - Fails: never raises for normal input; raises only if the underlying registry read inside validation fails.
    - Reads: organ registry + acceptance surfaces via _build_validation_context and _count_reconciliation under public_root.
    - Writes: None.
    """
    disposition_counts: dict[str, int] = {}
    for row in rows:
        disposition = str(row.get("disposition") or "")
        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
    name_promise_summary = _name_promise_summary(rows)
    validation_context = _build_validation_context(public_root)
    summary = {
        "status": PASS,
        "accepted_organ_count": len(rows),
        "disposition_counts": disposition_counts,
        "real_substrate_capsule_count": disposition_counts.get(
            REAL_SUBSTRATE_CAPSULE, 0
        ),
        "retained_regression_validator_count": disposition_counts.get(
            RETAINED_REGRESSION_VALIDATOR, 0
        ),
        "deleted_demoted_historical_artifact_count": disposition_counts.get(
            DELETED_DEMOTED_HISTORICAL_ARTIFACT, 0
        ),
        "real_body_count": sum(int(row.get("real_body_count") or 0) for row in rows),
        "receipt_body_count": sum(
            int(row.get("receipt_body_count") or 0) for row in rows
        ),
        "digest_drift_disposition_count": sum(
            int(row.get("digest_drift_disposition_count") or 0) for row in rows
        ),
        "fixture_authority_ban_status": PASS,
        "name_promise": name_promise_summary,
        "count_reconciliation": _count_reconciliation(public_root, len(rows)),
        "validation_issue_count": 0,
    }
    validation = validate_ledger_payload(
        {
            "organ_substrate_dispositions": rows,
            "summary": summary,
        },
        public_root=public_root,
        validation_context=validation_context,
    )
    summary["status"] = validation["status"]
    summary["fixture_authority_ban_status"] = (
        PASS if validation["status"] == PASS else "blocked"
    )
    summary["validation_issue_count"] = validation["issue_count"]
    return summary, validation


def _merge_organ_slice(
    public_root: Path,
    current: dict[str, Any],
    rebuilt: dict[str, Any],
    organ_ids: set[str],
) -> dict[str, Any]:
    """Splice rebuilt rows for selected organs into the current ledger.

    - Teleology: enables a surgical, reviewable write of only the organs that changed, while still re-deriving a whole-ledger summary + validation so the spliced result stays self-consistent.
    - Guarantee: returns a copy of `current` with organ_substrate_dispositions rebuilt only for ids in organ_ids (others retained from current), and status/summary/validation recomputed via _summary_and_validation_for_rows.
    - Fails: raises ValueError when organ_ids is empty, or when any selected id is missing from the rebuilt ledger (`rebuilt ledger is missing organ rows: ...`) — the caller converts this to a blocked_invalid_organ_slice result.
    - Reads: registry/acceptance surfaces via the summary/validation recompute under public_root.
    - Writes: None — returns a new dict; persistence is the caller's.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    if not organ_ids:
        raise ValueError("at least one organ id is required for organ-slice write")
    current_rows = _rows_by_organ_id(current)
    rebuilt_rows = _rows_by_organ_id(rebuilt)
    missing = sorted(organ_id for organ_id in organ_ids if organ_id not in rebuilt_rows)
    if missing:
        raise ValueError(f"rebuilt ledger is missing organ rows: {', '.join(missing)}")

    ordered_ids = _ordered_ids_for_organ_slice(public_root, current, rebuilt, organ_ids)
    rows: list[dict[str, Any]] = []
    for organ_id in ordered_ids:
        if organ_id in organ_ids:
            rows.append(rebuilt_rows[organ_id])
        elif organ_id in current_rows:
            rows.append(current_rows[organ_id])
        elif organ_id in rebuilt_rows:
            rows.append(rebuilt_rows[organ_id])
    summary, validation = _summary_and_validation_for_rows(public_root, rows)
    merged = dict(current)
    merged["status"] = validation["status"]
    merged["summary"] = summary
    merged["organ_substrate_dispositions"] = rows
    merged["validation"] = validation
    return merged


def _expected_accepted_ids(public_root: Path) -> list[str]:
    """List the organ ids the registry currently accepts as authority.

    - Teleology: the expected-id set the validator compares against ledger rows to catch accepted-organ-without-row and row-without-accepted-organ drift.
    - Guarantee: returns the organ_id of every accepted_current_authority registry row, in registry order.
    - Fails: raises if the organ registry is missing/malformed (via _accepted_registry_rows).
    - Reads: core/organ_registry.json under public_root.
    - Writes: None.
    """
    return [str(row.get("organ_id")) for row in _accepted_registry_rows(public_root)]


def _expected_accepted_ids_if_registry_exists(public_root: Path) -> list[str]:
    """List accepted organ ids, tolerating a missing registry.

    - Teleology: lets the missing-ledger error path and slice-ordering report an accepted count/order without raising when the registry file is absent.
    - Guarantee: returns the accepted_current_authority organ ids when the registry exists; returns `[]` when the registry file is missing.
    - Fails: never raises for a missing file; a present-but-malformed registry propagates read_json_strict's parse error.
    - Reads: core/organ_registry.json under public_root (existence-guarded).
    - Writes: None.
    """
    registry = _read_json_if_exists(public_root / REGISTRY_REL)
    return [
        str(row.get("organ_id"))
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _issue(
    issues: list[dict[str, Any]],
    issue_id: str,
    *,
    organ_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Append one structured violation to the validator's issues list.

    - Teleology: the single sink for every validation violation, so each blocking finding is a consistent {issue_id, organ_id?, detail?} record an agent can route on.
    - Guarantee: appends `{"issue_id": issue_id}` to `issues`, adding `organ_id` and/or `detail` only when truthy. Returns None.
    - Fails: never raises; mutates the passed-in list in place.
    - Reads: nothing (no filesystem).
    - Writes: None to disk — appends to the in-memory issues list.
    """
    row: dict[str, Any] = {"issue_id": issue_id}
    if organ_id:
        row["organ_id"] = organ_id
    if detail:
        row["detail"] = detail
    issues.append(row)


def _exercise_commands_reference_body(row: dict[str, Any]) -> bool:
    """Check a real capsule's exercise command actually touches its real body.

    - Teleology: protects the "real capsule has a runnable command CONNECTED to its body" claim from a generic command that exercises nothing the digest counted as a real body.
    - Guarantee: returns True when any public_exercise_command string contains the organ_id OR a token (full ref / file name / stem) of any digest row whose counts_as_real_body is True; returns False otherwise.
    - Fails: never raises; no commands or no counted body tokens -> False (the validator then flags real_capsule_public_exercise_not_connected_to_body).
    - Reads: the in-memory row (commands + digest_relation) only (no filesystem).
    - Writes: None.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    commands = [str(command) for command in row.get("public_exercise_commands", []) if command]
    if not commands:
        return False
    joined = "\n".join(commands)
    organ_id = str(row.get("organ_id") or "")
    if organ_id and organ_id in joined:
        return True
    body_tokens: set[str] = set()
    for digest_row in row.get("digest_relation", []):
        if not isinstance(digest_row, dict) or digest_row.get("counts_as_real_body") is not True:
            continue
        for key in ("target_ref", "source_ref", "module_id"):
            value = str(digest_row.get(key) or "")
            if not value:
                continue
            body_tokens.add(value)
            body_tokens.add(Path(value).name)
            body_tokens.add(Path(value).stem)
    return any(token and token in joined for token in body_tokens)


def validate_ledger_payload(
    payload: dict[str, Any],
    *,
    public_root: str | Path,
    validation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a substrate-substitution ledger payload against registry + body evidence.

    - Teleology: the release-trust gate protecting the public "fixture-only rows are not impressive; real-substrate counts come only from verified real bodies" claim from fixtures-as-authority, stale name-promise axes, demoted-but-accepted organs, and non-substrate sources counted as real.
    - Guarantee: returns a result dict with `status` = PASS only when zero issues, else `blocked`; carries issue_count, the full issues list, accepted_organ_count, checked_row_count, and `fixture_only_authority_banned` = (not issues). Recomputes expected name_promise axis + next_repair per organ and flags any divergence.
    - Fails: each violation (accepted organ missing row, row without accepted organ, invalid disposition, demoted-still-accepted, fixture-echo-not-demoted, retained-fixture counts-as-progress, real-capsule missing ceiling/command/body/manifest/digest, real-body from fixture/receipt/generated/runtime/formal/concurrency source, exact-copy drift, count divergence, stale name-promise) appends an issue and forces `status:blocked` (exit 1 via main).
    - Reads: registry-derived accepted ids (via validation_context or rebuilt), each row's digest_relation/name_promise/claim_ceiling, and summary.count_reconciliation.
    - Writes: None — read-only; returns a receipt dict, does not mutate the ledger.
    - When-needed: trust as the authority on whether a ledger payload is release-safe; inspect `issues` for the concrete failing organ/field.
    - Escalates-to: std organ-registry authority floor + tests/test_organ_registry_authority_floor.py; per-issue issue_id.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    root = _public_root_for_path(public_root)
    issues: list[dict[str, Any]] = []
    rows = _rows(payload, "organ_substrate_dispositions")
    rows_by_id = {str(row.get("organ_id")): row for row in rows if row.get("organ_id")}
    if (
        not isinstance(validation_context, dict)
        or validation_context.get("public_root") != root
    ):
        validation_context = _build_validation_context(root)
    accepted_ids = validation_context.get("accepted_ids")
    if not isinstance(accepted_ids, list):
        accepted_ids = _expected_accepted_ids(root)
    expected_name_promise_rows: list[dict[str, Any]] = []
    for organ_id in accepted_ids:
        if organ_id not in rows_by_id:
            _issue(issues, "accepted_organ_missing_substrate_disposition", organ_id=organ_id)
    for organ_id in sorted(set(rows_by_id) - set(accepted_ids)):
        _issue(issues, "ledger_row_without_accepted_organ", organ_id=organ_id)

    for organ_id, row in rows_by_id.items():
        disposition = str(row.get("disposition") or "")
        evidence_class = str(row.get("evidence_class") or "")
        bucket = str(row.get("truth_accounting_bucket") or "")
        digest_rows = [
            digest_row
            for digest_row in row.get("digest_relation", [])
            if isinstance(digest_row, dict)
        ]
        counted_body_rows = [
            digest_row
            for digest_row in digest_rows
            if digest_row.get("counts_as_real_body") is True
        ]
        receipt_body_rows = [
            digest_row
            for digest_row in digest_rows
            if digest_row.get("body_in_receipt") is True
        ]
        if disposition not in DISPOSITIONS:
            _issue(issues, "invalid_substrate_disposition", organ_id=organ_id)
            continue
        expected_name_promise = _name_promise_axis(
            public_root=root,
            organ_id=organ_id,
            evidence_class=evidence_class,
            source_compute_evidence=_source_compute_evidence_from_context(
                validation_context,
                organ_id,
            ),
        )
        actual_name_promise = row.get("name_promise")
        if not isinstance(actual_name_promise, dict):
            _issue(issues, "name_promise_axis_missing", organ_id=organ_id)
        else:
            for field in NAME_PROMISE_AXIS_CHECK_FIELDS:
                if actual_name_promise.get(field) != expected_name_promise.get(field):
                    _issue(
                        issues,
                        "name_promise_axis_stale_or_mismatched",
                        organ_id=organ_id,
                        detail={
                            "field": field,
                            "expected": expected_name_promise.get(field),
                            "actual": actual_name_promise.get(field),
                        },
                    )
        expected_next_repair = _next_repair(disposition, expected_name_promise)
        if row.get("next_repair") != expected_next_repair:
            _issue(
                issues,
                "name_promise_next_repair_stale",
                organ_id=organ_id,
                detail={
                    "expected": expected_next_repair,
                    "actual": row.get("next_repair"),
                },
            )
        expected_name_promise_rows.append(
            {
                "organ_id": organ_id,
                "name_promise": expected_name_promise,
                "next_repair": expected_next_repair,
            }
        )
        if disposition == DELETED_DEMOTED_HISTORICAL_ARTIFACT:
            _issue(issues, "demoted_artifact_still_accepted_authority", organ_id=organ_id)
        if (
            evidence_class == FIXTURE_ECHO_CLASS or bucket == REGRESSION_FIXTURE_BUCKET
        ) and disposition != RETAINED_REGRESSION_VALIDATOR:
            _issue(issues, "fixture_echo_not_demoted_to_regression_validator", organ_id=organ_id)
        if disposition == RETAINED_REGRESSION_VALIDATOR:
            if row.get("counts_as_real_substrate_progress") is True:
                _issue(issues, "retained_fixture_counts_as_progress", organ_id=organ_id)
            if int(row.get("real_body_count") or 0) != 0:
                _issue(issues, "retained_fixture_has_authority_body_count", organ_id=organ_id)
        if disposition == REAL_SUBSTRATE_CAPSULE:
            if not str(row.get("claim_ceiling") or "").strip():
                _issue(issues, "real_capsule_missing_claim_ceiling", organ_id=organ_id)
            if not row.get("public_exercise_commands"):
                _issue(issues, "real_capsule_missing_public_exercise_command", organ_id=organ_id)
            if not _exercise_commands_reference_body(row):
                _issue(issues, "real_capsule_public_exercise_not_connected_to_body", organ_id=organ_id)
            if int(row.get("real_body_count") or 0) <= 0:
                _issue(issues, "real_capsule_missing_verified_body_support", organ_id=organ_id)
            if int(row.get("supporting_body_count") or 0) <= 0:
                _issue(issues, "real_capsule_missing_supporting_body_count", organ_id=organ_id)
            if str(row.get("body_support_class") or "") in {"", "none_verified"}:
                _issue(issues, "real_capsule_missing_body_support_class", organ_id=organ_id)
            if not row.get("source_module_manifest_refs"):
                _issue(issues, "real_capsule_missing_source_module_manifest", organ_id=organ_id)
            if not row.get("digest_relation"):
                _issue(issues, "real_capsule_missing_digest_relation", organ_id=organ_id)
            if int(row.get("real_body_count") or 0) != len(counted_body_rows):
                _issue(
                    issues,
                    "real_capsule_real_body_count_diverges_from_digest_rows",
                    organ_id=organ_id,
                    detail={
                        "real_body_count": row.get("real_body_count"),
                        "counted_digest_body_rows": len(counted_body_rows),
                    },
                )
            if int(row.get("supporting_body_count") or 0) != len(counted_body_rows):
                _issue(
                    issues,
                    "real_capsule_supporting_body_count_diverges_from_digest_rows",
                    organ_id=organ_id,
                    detail={
                        "supporting_body_count": row.get("supporting_body_count"),
                        "counted_digest_body_rows": len(counted_body_rows),
                    },
                )
            if int(row.get("receipt_body_count") or 0) != len(receipt_body_rows):
                _issue(
                    issues,
                    "real_capsule_receipt_body_count_diverges_from_digest_rows",
                    organ_id=organ_id,
                    detail={
                        "receipt_body_count": row.get("receipt_body_count"),
                        "receipt_digest_body_rows": len(receipt_body_rows),
                    },
                )
            if row.get("macro_refs") and not row.get("microcosm_target_refs"):
                _issue(issues, "source_refs_without_target_bodies", organ_id=organ_id)
        if row.get("examples_fixtures_consistency") == "contradiction_unexplained":
            _issue(issues, "examples_fixture_body_count_contradiction", organ_id=organ_id)
        for digest_row in digest_rows:
            drift_disposition = str(digest_row.get("digest_drift_disposition") or "")
            if digest_row.get("counts_as_real_body") is True and (
                not str(digest_row.get("source_ref") or "").strip()
                or not str(digest_row.get("target_ref") or "").strip()
                or not str(digest_row.get("source_to_target_relation") or "").strip()
                or not str(digest_row.get("expected_sha256") or "").strip()
                or not str(digest_row.get("actual_target_sha256") or "").strip()
            ):
                _issue(
                    issues,
                    "real_body_missing_target_digest_or_provenance",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "target_ref": digest_row.get("target_ref"),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and digest_row.get("status") != PASS
            ):
                _issue(
                    issues,
                    "real_body_digest_relation_status_not_pass",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "status": digest_row.get("status"),
                        "target_ref": digest_row.get("target_ref"),
                    },
                )
            source_ref = str(digest_row.get("source_ref") or "")
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                in {"fixture_regression_source", "receipt_projection_source"}
            ):
                _issue(
                    issues,
                    "real_body_fixture_or_receipt_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                in {"generated_projection_source", "generated_projection_slice_source"}
            ):
                _issue(
                    issues,
                    "real_body_generated_projection_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                == "runtime_receipt_source"
            ):
                _issue(
                    issues,
                    "real_body_runtime_receipt_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                == "runtime_generated_artifact_source"
            ):
                _issue(
                    issues,
                    "real_body_runtime_generated_artifact_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                == "runtime_generated_lean_artifact_source"
            ):
                _issue(
                    issues,
                    "real_body_runtime_generated_lean_artifact_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                == "runtime_lean_diagnostic_source"
            ):
                _issue(
                    issues,
                    "real_body_runtime_lean_diagnostic_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                == "formal_evidence_cell_state_source"
            ):
                _issue(
                    issues,
                    "real_body_formal_evidence_cell_state_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if (
                digest_row.get("counts_as_real_body") is True
                and _source_authority_role(
                    source_ref,
                    str(digest_row.get("manifest_material_class") or ""),
                )
                == "concurrency_mission_control_seed_receipt_source"
            ):
                _issue(
                    issues,
                    "real_body_concurrency_seed_receipt_source_counted_as_substrate",
                    organ_id=organ_id,
                    detail={
                        "module_id": digest_row.get("module_id"),
                        "source_ref": source_ref,
                        "manifest_material_class": digest_row.get("manifest_material_class"),
                        "source_authority_role": _source_authority_role(
                            source_ref,
                            str(digest_row.get("manifest_material_class") or ""),
                        ),
                    },
                )
            if digest_row.get("source_to_target_relation") == "exact_copy":
                if digest_row.get("status") != PASS and not drift_disposition:
                    _issue(
                        issues,
                        "exact_copy_digest_or_target_drift",
                        organ_id=organ_id,
                        detail={
                            "module_id": digest_row.get("module_id"),
                            "source_ref": digest_row.get("source_ref"),
                            "target_ref": digest_row.get("target_ref"),
                        },
                    )
                if digest_row.get("status") != PASS and digest_row.get("counts_as_real_body") is True:
                    _issue(
                        issues,
                        "exact_copy_drift_counted_as_real_body",
                        organ_id=organ_id,
                        detail={
                            "module_id": digest_row.get("module_id"),
                            "target_ref": digest_row.get("target_ref"),
                        },
                    )
            if (
                digest_row.get("source_ref")
                and not digest_row.get("target_exists")
                and not drift_disposition
            ):
                _issue(
                    issues,
                    "source_ref_without_copied_target_body",
                    organ_id=organ_id,
                    detail={"source_ref": digest_row.get("source_ref")},
                )

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    count_reconciliation = summary.get("count_reconciliation")
    if isinstance(count_reconciliation, dict) and count_reconciliation.get("status") != PASS:
        _issue(
            issues,
            "registry_acceptance_count_divergence_unexplained",
            detail=count_reconciliation,
        )
    if isinstance(summary.get("accepted_organ_count"), int) and summary[
        "accepted_organ_count"
    ] != len(accepted_ids):
        _issue(
            issues,
            "ledger_accepted_count_mismatch",
            detail={
                "ledger_accepted_organ_count": summary["accepted_organ_count"],
                "registry_accepted_organ_count": len(accepted_ids),
            },
        )
    expected_name_promise_summary = _name_promise_summary(expected_name_promise_rows)
    actual_name_promise_summary = summary.get("name_promise")
    if not isinstance(actual_name_promise_summary, dict):
        _issue(issues, "name_promise_summary_missing")
    else:
        for field in NAME_PROMISE_SUMMARY_CHECK_FIELDS:
            if (
                actual_name_promise_summary.get(field)
                != expected_name_promise_summary.get(field)
            ):
                _issue(
                    issues,
                    "name_promise_summary_stale_or_mismatched",
                    detail={
                        "field": field,
                        "expected": expected_name_promise_summary.get(field),
                        "actual": actual_name_promise_summary.get(field),
                    },
                )
    return {
        "schema_version": "microcosm_substrate_substitution_validation_v1",
        "checker_id": CHECKER_ID,
        "status": PASS if not issues else "blocked",
        "issue_count": len(issues),
        "issues": issues,
        "accepted_organ_count": len(accepted_ids),
        "checked_row_count": len(rows_by_id),
        "fixture_only_authority_banned": not issues,
    }


def validate_ledger(public_root: str | Path) -> dict[str, Any]:
    """Validate the on-disk ledger file as a release-trust gate.

    - Teleology: the entrypoint (`--check`) that decides whether the persisted substrate-substitution ledger is currently release-safe, including the missing-ledger / missing-registry failure modes.
    - Guarantee: returns a `microcosm_substrate_substitution_validation_v1` result; when the ledger file is absent it returns `status:blocked` with a `substrate_substitution_ledger_missing` issue (plus `organ_registry_missing` if the registry is also gone); otherwise delegates to validate_ledger_payload.
    - Fails: never raises for absent files (they become blocking issues -> exit 1 via main); raises only if a present registry/ledger is malformed JSON.
    - Reads: core/substrate_substitution_ledger.json and core/organ_registry.json under the resolved public root.
    - Writes: None — read-only check; emits no mutation.
    - When-needed: call to gate whether the committed ledger passes; inspect `issues` for the failing organ/field.
    - Escalates-to: validate_ledger_payload; std organ-registry authority floor + tests/test_organ_registry_authority_floor.py.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    root = _public_root_for_path(public_root)
    ledger = _read_json_if_exists(root / LEDGER_REL)
    if not ledger:
        issues = [{"issue_id": "substrate_substitution_ledger_missing"}]
        registry_path = root / REGISTRY_REL
        if not registry_path.is_file():
            issues.append(
                {
                    "issue_id": "organ_registry_missing",
                    "path": _display(registry_path, public_root=root),
                }
            )
        return {
            "schema_version": "microcosm_substrate_substitution_validation_v1",
            "checker_id": CHECKER_ID,
            "status": "blocked",
            "issue_count": len(issues),
            "issues": issues,
            "accepted_organ_count": len(_expected_accepted_ids_if_registry_exists(root)),
            "checked_row_count": 0,
            "fixture_only_authority_banned": False,
        }
    return validate_ledger_payload(ledger, public_root=root)


def _json_pointer(path: tuple[str, ...]) -> str:
    """Render a diff path tuple as an RFC6901-escaped JSON pointer string.

    - Teleology: gives drift/settlement receipts a stable, human-readable address for each changed field so reviewers can locate exactly what moved.
    - Guarantee: returns `/` for an empty path; otherwise `/`-joined parts with `~`->`~0` and `/`->`~1` escaping applied to each segment.
    - Fails: never raises; pure string transform.
    - Writes: None.
    """
    if not path:
        return "/"
    escaped = [part.replace("~", "~0").replace("/", "~1") for part in path]
    return "/" + "/".join(escaped)


def _json_diff_value(payload: Any, path: tuple[str, ...]) -> Any:
    """Resolve the value at a diff path inside a JSON payload.

    - Teleology: lets settlement read the current/rebuilt value at each changed path so a verdict rests on the actual before/after values, not just the field name.
    - Guarantee: walks `path` through dict keys, list `key=value` row selectors, and list integer indices; returns the located value, or the sentinel `_MISSING` when any segment cannot be resolved.
    - Fails: never raises; out-of-range index, missing key, or unmatched row selector -> `_MISSING`.
    - Reads: the in-memory payload only (no filesystem).
    - Writes: None.
    """
    node = payload
    for part in path:
        if isinstance(node, dict):
            if part not in node:
                return _MISSING
            node = node[part]
            continue
        if isinstance(node, list):
            if "=" in part:
                key, row_id = part.split("=", 1)
                for row in node:
                    if isinstance(row, dict) and str(row.get(key) or "") == row_id:
                        node = row
                        break
                else:
                    return _MISSING
                continue
            try:
                index = int(part)
            except ValueError:
                return _MISSING
            if index < 0 or index >= len(node):
                return _MISSING
            node = node[index]
            continue
        return _MISSING
    return node


def _json_diff_value_for_json(value: Any) -> Any:
    """Make a possibly-missing diff value JSON-serializable for a receipt.

    - Teleology: lets settlement receipts record "this side was absent" explicitly instead of dropping a key or emitting an unserializable sentinel.
    - Guarantee: returns `{"missing": True}` when value is the `_MISSING` sentinel; otherwise returns the value unchanged.
    - Fails: never raises.
    - Writes: None.
    """
    if value is _MISSING:
        return {"missing": True}
    return value


def _json_payload_sha256(value: Any) -> str:
    """Compute a stable content digest of a JSON-serializable value.

    - Teleology: gives settlement receipts a reproducible current/rebuilt/drift/path-set hash so a review's "this is the exact payload I settled" claim is verifiable.
    - Guarantee: returns `sha256:<hex>` over `json.dumps(value, sort_keys=True, separators=(",",":"))`, so logically-equal payloads hash identically regardless of key order.
    - Fails: raises TypeError if `value` is not JSON-serializable (json.dumps); no failure-envelope return.
    - Writes: None.
    """
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _organ_id_from_diff_path(path: tuple[str, ...]) -> str:
    """Recover the organ id a diff path belongs to, if any.

    - Teleology: lets each settlement/blocker row attribute a changed field to the organ it concerns, so reviewers see which organ a drift affects.
    - Guarantee: returns the value of the first `organ_id=<id>` row selector segment in `path`; returns `""` when the path does not pass through a keyed organ row.
    - Fails: never raises; no organ selector -> `""`.
    - Writes: None.
    """
    for part in path:
        if part.startswith("organ_id="):
            return part.split("=", 1)[1]
    return ""


def _digest_row_for_diff_path(payload: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    """Recover the enclosing digest-relation row for a JSON diff path.

    - Teleology: lets drift settlement read the rebuilt row's provenance/digest fields so a bucket/verdict decision is grounded in real evidence, not just the changed field name.
    - Guarantee: returns the nearest ancestor dict along `path` that carries both a relation/ref marker key and a digest key (source/target/relation set intersected with expected/actual/source sha256 set); returns `{}` when no enclosing digest row is found.
    - Fails: path resolves to no qualifying dict -> returns `{}` (no raise); callers treat `{}` as no-evidence and route to review.
    - Reads: the in-memory payload at sub-paths (no filesystem).
    - Writes: None.
    """
    for end in range(len(path), 0, -1):
        value = _json_diff_value(payload, path[:end])
        if not isinstance(value, dict):
            continue
        if (
            {"source_ref", "target_ref", "source_to_target_relation"} & set(value)
            and {"expected_sha256", "actual_target_sha256", "source_sha256"} & set(value)
        ):
            return value
    return {}


def _keyed_dict_list(rows: list[Any]) -> tuple[str, dict[str, Any]] | None:
    """Detect a stable identity key for a list of dict rows.

    - Teleology: lets the JSON differ align list elements by identity (so a reordered or inserted organ/module row diffs cleanly) instead of by fragile positional index.
    - Guarantee: returns `(key, {id_value: row})` for the first of (organ_id, module_id, target_ref, source_ref) that is present, truthy, and unique across all rows; returns None when rows is empty, contains a non-dict, or no key is a total unique index.
    - Fails: never raises; ambiguous/duplicate/empty key values -> None (caller falls back to index diffing).
    - Reads: the in-memory rows only (no filesystem).
    - Writes: None.
    """
    if not rows or not all(isinstance(row, dict) for row in rows):
        return None
    for key in ("organ_id", "module_id", "target_ref", "source_ref"):
        keyed: dict[str, Any] = {}
        for row in rows:
            value = str(row.get(key) or "")
            if not value or value in keyed:
                break
            keyed[value] = row
        else:
            if len(keyed) == len(rows):
                return key, keyed
    return None


def _json_diff_paths(
    current: Any,
    rebuilt: Any,
    path: tuple[str, ...] = (),
) -> list[tuple[str, ...]]:
    """Compute the set of changed paths between two JSON payloads.

    - Teleology: the structural diff that feeds drift classification and settlement, identifying every field that differs between the current and rebuilt ledger so each can be routed to a verdict.
    - Guarantee: returns a list of path tuples (dict-key / `key=id` row-selector / index segments) for every leaf that differs; identity-keyed lists are aligned by key, others by index; type mismatch at a node yields that node's path; equal payloads yield `[]`.
    - Fails: never raises; recursion terminates on scalars and on the keyed/index branches.
    - Reads: the two in-memory payloads only (no filesystem).
    - Writes: None.
    """
    if type(current) is not type(rebuilt):
        return [path]
    if isinstance(current, dict):
        paths: list[tuple[str, ...]] = []
        for key in sorted(set(current) | set(rebuilt)):
            if key not in current or key not in rebuilt:
                paths.append(path + (str(key),))
                continue
            paths.extend(_json_diff_paths(current[key], rebuilt[key], path + (str(key),)))
        return paths
    if isinstance(current, list):
        current_keyed = _keyed_dict_list(current)
        rebuilt_keyed = _keyed_dict_list(rebuilt)
        if (
            current_keyed is not None
            and rebuilt_keyed is not None
            and current_keyed[0] == rebuilt_keyed[0]
        ):
            key = current_keyed[0]
            current_rows = current_keyed[1]
            rebuilt_rows = rebuilt_keyed[1]
            paths = []
            for row_id in sorted(set(current_rows) | set(rebuilt_rows)):
                row_path = path + (f"{key}={row_id}",)
                if row_id not in current_rows or row_id not in rebuilt_rows:
                    paths.append(row_path)
                    continue
                paths.extend(
                    _json_diff_paths(current_rows[row_id], rebuilt_rows[row_id], row_path)
                )
            return paths
        paths = []
        for index in range(max(len(current), len(rebuilt))):
            index_path = path + (str(index),)
            if index >= len(current) or index >= len(rebuilt):
                paths.append(index_path)
                continue
            paths.extend(_json_diff_paths(current[index], rebuilt[index], index_path))
        return paths
    return [] if current == rebuilt else [path]


def _writer_drift_axis(path: tuple[str, ...]) -> str:
    """Classify a changed path into a writer-drift axis.

    - Teleology: routes each diffed field to a drift axis so a scoped write can allow only its own axis and block unrelated rebuild drift, and so settlement knows which owner must review a change.
    - Guarantee: returns exactly one axis string — name_promise, claim_ceiling, digest_relation, validation, summary, ledger_metadata, or other — by ordered substring/segment matching on the path.
    - Fails: never raises; an unrecognized path falls through to `other`.
    - Reads: the path tuple only (no filesystem).
    - Writes: None.
    """
    text = "/".join(path).lower()
    if "name_promise" in path or (path and path[-1] == "next_repair"):
        return "name_promise"
    if "claim_ceiling" in text:
        return "claim_ceiling"
    if (
        "digest_relation" in path
        or "sha256" in text
        or "digest_drift" in text
        or "digest_relation_status" in text
        or "source_to_target_relation" in text
        or "source_authority_role" in text
        or "counts_as_real_body" in text
        or "body_count" in text
    ):
        return "digest_relation"
    if "validation" in path or "issue_count" in text:
        return "validation"
    if path and path[0] == "summary":
        return "summary"
    if path and path[0] in {
        "anti_claim",
        "checker_id",
        "ledger_id",
        "schema_version",
        "source_surfaces",
        "state_machine",
        "status",
    }:
        return "ledger_metadata"
    return "other"


def _classify_rebuild_drift(
    current: dict[str, Any],
    rebuilt: dict[str, Any],
    *,
    write_scope: str = "full",
) -> dict[str, Any]:
    """Classify current-vs-rebuilt drift into per-axis counts under a write scope.

    - Teleology: the writer guard that decides whether a rebuild's changes fall inside the requested write scope, blocking unrelated-axis drift before any mutation.
    - Guarantee: returns a `microcosm_substrate_substitution_writer_drift_v1` dict whose `status` is PASS (no changes), `drift_detected` (changes only on allowed axes), or `blocked_unrelated_rebuild_drift` (any change on a disallowed axis), with axis_counts, changed_axes, unrelated_axes, and bounded sample paths.
    - Fails: raises ValueError for an unsupported write_scope (`unsupported writer drift scope: ...`); otherwise never raises.
    - Reads: the two in-memory payloads only (no filesystem).
    - Writes: None.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    if write_scope not in WRITER_DRIFT_SCOPE_AXES:
        raise ValueError(f"unsupported writer drift scope: {write_scope}")
    paths = _json_diff_paths(current, rebuilt)
    axis_counts: dict[str, int] = {}
    samples_by_axis: dict[str, list[str]] = {}
    for path in paths:
        axis = _writer_drift_axis(path)
        axis_counts[axis] = axis_counts.get(axis, 0) + 1
        axis_samples = samples_by_axis.setdefault(axis, [])
        if len(axis_samples) < 5:
            axis_samples.append(_json_pointer(path))
    allowed_axes = WRITER_DRIFT_SCOPE_AXES[write_scope]
    unrelated_axes = (
        []
        if allowed_axes is None
        else sorted(axis for axis in axis_counts if axis not in allowed_axes)
    )
    if not paths:
        status = PASS
    elif unrelated_axes:
        status = "blocked_unrelated_rebuild_drift"
    else:
        status = "drift_detected"
    return {
        "schema_version": "microcosm_substrate_substitution_writer_drift_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "write_scope": write_scope,
        "changed_path_count": len(paths),
        "changed_axes": sorted(axis_counts),
        "axis_counts": axis_counts,
        "unrelated_axes": unrelated_axes,
        "unrelated_axis_count": len(unrelated_axes),
        "sample_paths": [_json_pointer(path) for path in paths[:WRITER_DRIFT_SAMPLE_LIMIT]],
        "samples_by_axis": samples_by_axis,
    }


def _claim_ceiling_settlement_rows(
    current: dict[str, Any],
    rebuilt: dict[str, Any],
    paths: list[tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Settle each claim-ceiling diff into a review verdict.

    - Teleology: protects the public claim-ceiling (authority-ceiling) surface from a stale-projection or conflicting rewrite being auto-applied without review.
    - Guarantee: returns one row per claim_ceiling-axis diff path, each with verdict in {claim_ceiling_conflict (a side MISSING), claim_ceiling_unchanged (equal), claim_ceiling_safe_narrowing (safe-narrowing predicate), claim_ceiling_stale_projection (else)}, and `mutation_eligible_without_review` True ONLY for unchanged/safe_narrowing; review_required is its negation.
    - Fails: a changed-but-not-safe ceiling -> verdict `claim_ceiling_stale_projection`, review_required True, mutation_eligible False (blocks auto-write); a MISSING side -> `claim_ceiling_conflict`, blocking.
    - Reads: current/rebuilt ledger values at each claim_ceiling diff path; claim_ceiling_source recorded as core/organ_registry.json.
    - Writes: None.
    - When-needed: inspect before auto-applying any rebuilt claim ceiling.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    rows = []
    for path in paths:
        if _writer_drift_axis(path) != "claim_ceiling":
            continue
        current_value = _json_diff_value(current, path)
        rebuilt_value = _json_diff_value(rebuilt, path)
        if current_value is _MISSING or rebuilt_value is _MISSING:
            verdict = "claim_ceiling_conflict"
        elif current_value == rebuilt_value:
            verdict = "claim_ceiling_unchanged"
        elif _is_safe_claim_ceiling_narrowing(current_value, rebuilt_value):
            verdict = "claim_ceiling_safe_narrowing"
        else:
            verdict = "claim_ceiling_stale_projection"
        mutation_eligible = verdict in {
            "claim_ceiling_unchanged",
            "claim_ceiling_safe_narrowing",
        }
        rows.append(
            {
                "organ_id": _organ_id_from_diff_path(path),
                "path": _json_pointer(path),
                "claim_ceiling_source": REGISTRY_REL.as_posix(),
                "current_claim_ceiling": _json_diff_value_for_json(current_value),
                "rebuilt_claim_ceiling": _json_diff_value_for_json(rebuilt_value),
                "verdict": verdict,
                "review_required": not mutation_eligible,
                "mutation_eligible_without_review": mutation_eligible,
                "evidence_class": (
                    "registry_claim_ceiling_safe_narrowing"
                    if verdict == "claim_ceiling_safe_narrowing"
                    else "registry_claim_ceiling_projection"
                ),
            }
        )
    return rows


def _normalised_text(value: Any) -> str:
    """Normalise a value to lowercase, single-spaced comparison text.

    - Teleology: lets claim-ceiling comparison ignore case/whitespace noise so a genuine narrowing is distinguished from a cosmetic rephrase.
    - Guarantee: returns the stringified value lowercased, stripped, with internal whitespace runs collapsed to single spaces.
    - Fails: never raises; non-string values are stringified first.
    - Writes: None.
    """
    return " ".join(str(value).strip().lower().split())


def _is_safe_claim_ceiling_narrowing(current_value: Any, rebuilt_value: Any) -> bool:
    """Decide whether a claim-ceiling change is a safe, auto-applicable narrowing.

    - Teleology: protects the authority-ceiling surface by letting ONLY a strict narrowing (generic ceiling -> longer, explicitly-bounded ceiling) skip human review, never a widening or rephrase.
    - Guarantee: returns True only when both values are str, the normalised current text is a member of GENERIC_CLAIM_CEILINGS, and the rebuilt text is strictly longer and contains both `validates only` and `does not`; returns False otherwise.
    - Fails: non-str inputs, non-generic current, or rebuilt lacking the bounding phrases / not longer -> returns False (treated as review-required upstream); never raises.
    - Reads: the two values and the GENERIC_CLAIM_CEILINGS constant (no filesystem).
    - Writes: None.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    if not isinstance(current_value, str) or not isinstance(rebuilt_value, str):
        return False
    current_text = _normalised_text(current_value)
    rebuilt_text = _normalised_text(rebuilt_value)
    return (
        current_text in GENERIC_CLAIM_CEILINGS
        and len(rebuilt_text) > len(current_text)
        and "validates only" in rebuilt_text
        and "does not" in rebuilt_text
    )


def _digest_bucket_for_path(
    path: tuple[str, ...],
    rebuilt: dict[str, Any],
) -> str:
    """Bucket a digest-relation diff path by the kind of drift it represents.

    - Teleology: routes a digest change to a settlement bucket so body-count/relation/source-moved changes get review while pure metadata refreshes can be mechanical, protecting real-body accounting from silent reclassification.
    - Guarantee: returns exactly one bucket string keyed off the changed field and the enclosing rebuilt digest row — relation_reclassification, body_count_disposition_change, historical_pinned_drift, exact_copy_hash_refresh, source_moved_target_stale, target_moved_source_stale, or digest_metadata_refresh.
    - Fails: None — every path falls through to `digest_metadata_refresh` default; never raises or returns a failure envelope. (Blocking is decided later by _digest_settlement_verdict.)
    - Reads: the rebuilt payload's enclosing digest row (relation + sha256 fields); no filesystem.
    - Writes: None.
    """
    field = path[-1] if path else ""
    rebuilt_row = _digest_row_for_diff_path(rebuilt, path)
    relation = str(rebuilt_row.get("source_to_target_relation") or "")
    expected_digest = str(rebuilt_row.get("expected_sha256") or "")
    actual_digest = str(rebuilt_row.get("actual_target_sha256") or "")
    source_digest = str(rebuilt_row.get("source_sha256") or "")
    if field in {"source_to_target_relation", "source_authority_role"}:
        return "relation_reclassification"
    if field in {
        "counts_as_real_body",
        "digest_drift_disposition",
        "digest_drift_disposition_count",
        "digest_relation_status",
        "real_body_count",
        "supporting_body_count",
        "receipt_body_count",
        "status",
    }:
        return "body_count_disposition_change"
    if rebuilt_row.get("digest_drift_disposition"):
        return "historical_pinned_drift"
    if field in {
        "actual_target_sha256",
        "expected_sha256",
        "sha256",
        "source_sha256",
        "target_sha256",
    }:
        if relation == "exact_copy" and source_digest and actual_digest:
            if source_digest == actual_digest:
                return "exact_copy_hash_refresh"
            return "source_moved_target_stale"
        if expected_digest and actual_digest and expected_digest != actual_digest:
            return "target_moved_source_stale"
        return "digest_metadata_refresh"
    return "digest_metadata_refresh"


def _digest_row_has_verified_exact_copy_evidence(row: dict[str, Any]) -> bool:
    """Test whether a digest row carries genuine verified-exact-copy evidence.

    - Teleology: gates auto-promotion of a relation/body-count change so only a row whose digests actually match may be promoted without review, protecting real-body credit from being granted to unverified exact-copies.
    - Guarantee: returns True only when relation is in VERIFIED_EXACT_COPY_RELATIONS, a source_ref or target_ref is present, an actual_target_sha256 is present, AND it equals either the source_sha256 or the expected_sha256; returns False otherwise.
    - Fails: missing relation/material-ref/actual digest, or no matching source/expected digest -> returns False (no auto-promotion); never raises.
    - Reads: the in-memory digest row fields only (no filesystem).
    - Writes: None.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    relation = str(row.get("source_to_target_relation") or "")
    expected_digest = str(row.get("expected_sha256") or "")
    actual_digest = str(row.get("actual_target_sha256") or "")
    source_digest = str(row.get("source_sha256") or "")
    has_material_ref = bool(row.get("source_ref") or row.get("target_ref"))
    return (
        relation in VERIFIED_EXACT_COPY_RELATIONS
        and has_material_ref
        and bool(actual_digest)
        and (
            bool(source_digest and source_digest == actual_digest)
            or bool(expected_digest and expected_digest == actual_digest)
        )
    )


def _digest_settlement_verdict(
    path: tuple[str, ...],
    rebuilt: dict[str, Any],
    *,
    bucket: str,
    current_value: Any,
    rebuilt_value: Any,
) -> tuple[str, bool, bool, bool]:
    """Decide the settlement verdict and review/mutation flags for one digest diff.

    - Teleology: protects real-body accounting by requiring verified-exact-copy evidence before any promotion (status/relation/body-count) is auto-applied; everything else routes to owner review.
    - Guarantee: returns `(verdict, review_required, mutation_eligible_without_review, aggregate_counter)`; mechanical refresh and evidence-backed promotions return review_required False / mutation_eligible True; relation/body-count/historical/source-moved changes without evidence return review_required True / mutation_eligible False; derived aggregate counters return `(... , True, False, True)` pending row proof.
    - Fails: any unrecognized or evidence-lacking change -> a `*_requires_review` / `*_requires_refresh` verdict with review_required True, blocking auto-write; never raises.
    - Reads: the rebuilt payload's enclosing digest row plus the field name and current/rebuilt values (no filesystem).
    - Writes: None.
    - When-needed: inspect to understand why a specific digest change is blocking or auto-applicable.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    field = path[-1] if path else ""
    rebuilt_row = _digest_row_for_diff_path(rebuilt, path)
    if bucket in {"digest_metadata_refresh", "exact_copy_hash_refresh"}:
        return "mechanical_digest_metadata_refresh", False, True, False
    if bucket == "relation_reclassification":
        if _digest_row_has_verified_exact_copy_evidence(rebuilt_row):
            return "verified_exact_copy_relation_promotion", False, True, False
        return "relation_reclassification_requires_review", True, False, False
    if bucket == "body_count_disposition_change":
        if (
            field == "counts_as_real_body"
            and current_value is not True
            and rebuilt_value is True
            and _digest_row_has_verified_exact_copy_evidence(rebuilt_row)
        ):
            return "verified_exact_copy_body_count_promotion", False, True, False
        if (
            field == "digest_drift_disposition"
            and isinstance(current_value, str)
            and current_value.startswith("pinned_historical_exact_copy_drift")
            and rebuilt_value is _MISSING
            and _digest_row_has_verified_exact_copy_evidence(rebuilt_row)
        ):
            return "resolved_pinned_exact_copy_drift", False, True, False
        if (
            field == "status"
            and current_value == "blocked"
            and rebuilt_value == PASS
            and _digest_row_has_verified_exact_copy_evidence(rebuilt_row)
        ):
            return "resolved_verified_exact_copy_row_status", False, True, False
        if field in BODY_COUNT_AGGREGATE_FIELDS:
            return "derived_body_count_counter_pending_row_proof", True, False, True
        return "body_count_disposition_requires_review", True, False, False
    if bucket == "historical_pinned_drift":
        return "historical_pinned_drift_requires_review", True, False, False
    if bucket in {"source_moved_target_stale", "target_moved_source_stale"}:
        return f"{bucket}_requires_refresh", True, False, False
    return "digest_relation_requires_review", True, False, False


def _digest_settlement_rows(
    current: dict[str, Any],
    rebuilt: dict[str, Any],
    paths: list[tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Build per-path digest settlement rows with bucket + verdict + blocking flags.

    - Teleology: produces the digest-axis evidence rows that decide whether a generated-ledger refresh may proceed, protecting real-body/digest claims from unreviewed mutation.
    - Guarantee: returns one row per digest_relation-axis diff path, each carrying organ_id, json-pointer path, field, bucket, current/rebuilt value, settlement_verdict, review_required, mutation_eligible_without_review, aggregate_counter, and `blocking` (= review_required), derived from _digest_bucket_for_path + _digest_settlement_verdict.
    - Fails: an evidence-lacking digest change -> a row with review_required/blocking True (caller treats as blocked_pending_drift_settlement); never raises.
    - Reads: current/rebuilt ledger values at each digest diff path (no filesystem).
    - Writes: None — returns rows; _promote_eligible_digest_aggregate_rows may later mutate them in place.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    rows = []
    for path in paths:
        if _writer_drift_axis(path) != "digest_relation":
            continue
        current_value = _json_diff_value(current, path)
        rebuilt_value = _json_diff_value(rebuilt, path)
        bucket = _digest_bucket_for_path(path, rebuilt)
        verdict, review_required, mutation_eligible, aggregate_counter = (
            _digest_settlement_verdict(
                path,
                rebuilt,
                bucket=bucket,
                current_value=current_value,
                rebuilt_value=rebuilt_value,
            )
        )
        rows.append(
            {
                "organ_id": _organ_id_from_diff_path(path),
                "path": _json_pointer(path),
                "field": path[-1] if path else "",
                "bucket": bucket,
                "current_value": _json_diff_value_for_json(current_value),
                "rebuilt_value": _json_diff_value_for_json(rebuilt_value),
                "settlement_verdict": verdict,
                "review_required": review_required,
                "mutation_eligible_without_review": mutation_eligible,
                "aggregate_counter": aggregate_counter,
                "blocking": review_required,
            }
        )
    return rows


def _promote_eligible_digest_aggregate_rows(rows: list[dict[str, Any]]) -> None:
    """In-place promote derived aggregate-counter rows whose organ has no blocking row.

    - Teleology: protects real-body counters from being auto-refreshed while any underlying per-row digest change for the SAME organ is still pending review.
    - Guarantee: mutates only rows where `aggregate_counter` is truthy and whose organ_id is NOT in the blocked set; for those it sets settlement_verdict=`derived_body_count_counter_from_verified_rows`, review_required False, mutation_eligible_without_review True, blocking False. Returns None.
    - Fails: an organ with any non-aggregate blocking-bucket row that is not mutation-eligible -> its aggregate rows stay blocked (unchanged); empty input -> early return; never raises.
    - Reads: the rows list only (no filesystem).
    - Writes: None to disk — mutates the passed-in row dicts in place.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    if not rows:
        return
    blocked_organs = {
        str(row.get("organ_id") or "")
        for row in rows
        if not row.get("aggregate_counter")
        and row.get("bucket") in BLOCKING_DIGEST_SETTLEMENT_BUCKETS
        and not row.get("mutation_eligible_without_review")
    }
    for row in rows:
        if not row.get("aggregate_counter"):
            continue
        if str(row.get("organ_id") or "") in blocked_organs:
            continue
        row["settlement_verdict"] = "derived_body_count_counter_from_verified_rows"
        row["review_required"] = False
        row["mutation_eligible_without_review"] = True
        row["blocking"] = False


def _increment(mapping: dict[str, int], key: str) -> None:
    """Increment a counter for `key` in a count mapping, defaulting to zero.

    - Teleology: the shared tally primitive for settlement verdict/bucket/blocked counts.
    - Guarantee: sets `mapping[key]` to its prior value (or 0) plus 1, in place. Returns None.
    - Fails: never raises.
    - Writes: None to disk — mutates the passed-in mapping.
    """
    mapping[key] = mapping.get(key, 0) + 1


def _sample_bucket(
    samples_by_bucket: dict[str, list[str]],
    bucket: str,
    path: str,
) -> None:
    """Record a bounded sample pointer for a settlement bucket.

    - Teleology: keeps settlement receipts small by capping how many example paths each bucket carries while still showing representative evidence.
    - Guarantee: appends `path` to `samples_by_bucket[bucket]` only while that bucket holds fewer than SETTLEMENT_SAMPLE_LIMIT entries. Returns None.
    - Fails: never raises; once the cap is reached the call is a no-op.
    - Writes: None to disk — mutates the passed-in mapping.
    """
    bucket_samples = samples_by_bucket.setdefault(bucket, [])
    if len(bucket_samples) < SETTLEMENT_SAMPLE_LIMIT:
        bucket_samples.append(path)


def _sample_blocked_settlement_row(
    samples_by_bucket: dict[str, list[dict[str, Any]]],
    bucket: str,
    row: dict[str, Any],
) -> None:
    """Record a bounded copy of a blocking settlement row by bucket.

    - Teleology: gives a blocked-pending-settlement receipt concrete (but capped) row evidence per bucket so a reviewer sees what blocked without the full row list.
    - Guarantee: appends a shallow copy `dict(row)` to `samples_by_bucket[bucket]` only while that bucket holds fewer than SETTLEMENT_SAMPLE_LIMIT entries. Returns None.
    - Fails: never raises; over-cap calls are no-ops; the copy avoids later in-place mutation aliasing.
    - Writes: None to disk — mutates the passed-in mapping.
    """
    bucket_samples = samples_by_bucket.setdefault(bucket, [])
    if len(bucket_samples) < SETTLEMENT_SAMPLE_LIMIT:
        bucket_samples.append(dict(row))


def _non_settlement_axis_blocker_row(
    current: dict[str, Any],
    rebuilt: dict[str, Any],
    path: tuple[str, ...],
) -> dict[str, Any]:
    """Build a blocker row for a change on a non-settlement-owned axis.

    - Teleology: ensures a change on an axis the settlement owner does not arbitrate (e.g. summary/validation/metadata) still blocks the write and is attributed to its owning projection.
    - Guarantee: returns a row with organ_id, json-pointer path, field, axis, current/rebuilt values, a `non_settlement_axis_<axis>_requires_owner_projection` verdict, and review_required/blocking True with mutation_eligible_without_review False.
    - Fails: never raises.
    - Reads: current/rebuilt values at the path (no filesystem).
    - Writes: None.
    """
    axis = _writer_drift_axis(path)
    return {
        "organ_id": _organ_id_from_diff_path(path),
        "path": _json_pointer(path),
        "field": path[-1] if path else "",
        "axis": axis,
        "current_value": _json_diff_value_for_json(_json_diff_value(current, path)),
        "rebuilt_value": _json_diff_value_for_json(_json_diff_value(rebuilt, path)),
        "settlement_verdict": f"non_settlement_axis_{axis}_requires_owner_projection",
        "review_required": True,
        "mutation_eligible_without_review": False,
        "blocking": True,
    }


def _settlement_status_basis(
    *,
    status: str,
    changed_path_count: int,
    blocked_bucket_counts: dict[str, int],
) -> dict[str, Any]:
    """Explain why a settlement receipt has the status it does.

    - Teleology: makes the settlement decision auditable by recording the rule and the blocking-change arithmetic that produced PASS / ready / blocked, so the status is not an opaque verdict.
    - Guarantee: returns a dict with status, a decision_rule (no_changed_paths / blocked_bucket_counts_nonempty / changed_paths_without_blocking_buckets), changed_path_count, blocking bucket/change counts split into settlement-owner vs non-settlement-axis, and the evidence_fields list.
    - Fails: never raises; counts derive from summing the provided mapping.
    - Reads: the passed-in counts only (no filesystem).
    - Writes: None.
    """
    blocking_change_count = sum(blocked_bucket_counts.values())
    non_settlement_axis_blocking_change_count = sum(
        count
        for bucket, count in blocked_bucket_counts.items()
        if bucket.startswith("non_settlement_axis:")
    )
    if changed_path_count == 0:
        decision_rule = "no_changed_paths"
    elif blocked_bucket_counts:
        decision_rule = "blocked_bucket_counts_nonempty"
    else:
        decision_rule = "changed_paths_without_blocking_buckets"
    return {
        "status": status,
        "decision_rule": decision_rule,
        "changed_path_count": changed_path_count,
        "blocking_bucket_count": len(blocked_bucket_counts),
        "blocking_change_count": blocking_change_count,
        "settlement_owner_blocking_change_count": (
            blocking_change_count - non_settlement_axis_blocking_change_count
        ),
        "non_settlement_axis_blocking_change_count": (
            non_settlement_axis_blocking_change_count
        ),
        "evidence_fields": [
            "changed_path_count",
            "blocked_bucket_counts",
            "claim_ceiling_verdict_counts",
            "digest_relation_verdict_counts",
            "non_settlement_axis_counts",
        ],
    }


def _settlement_receipt_from_payloads(
    current: dict[str, Any],
    rebuilt: dict[str, Any],
    *,
    write_scope: str = "full",
) -> dict[str, Any]:
    """Build the no-write drift-settlement receipt comparing current vs rebuilt ledger.

    - Teleology: gates a generated-ledger refresh behind a review receipt so the ledger (a release-trust surface) is never auto-overwritten while any claim-ceiling/digest/non-settlement-axis change is unsettled.
    - Guarantee: returns a receipt dict with `status` = PASS (no paths), `blocked_pending_drift_settlement` (any blocked bucket), or `ready_for_reviewed_generated_ledger_refresh`; carries content digests of current/rebuilt/drift/path-set, per-axis counts, claim/digest verdict rows, blocked-bucket samples, mutation_plan, reentry_condition, `write_performed: False`, and `authority_posture: settlement_receipt_not_source_authority`.
    - Fails: any blocking claim-ceiling verdict, blocking digest bucket, or non-settlement axis change -> status `blocked_pending_drift_settlement`, mutation_plan `no_generated_ledger_write` (caller refuses to write).
    - Reads: the in-memory current/rebuilt payloads only; performs no filesystem read or write itself.
    - Writes: None — `write_performed` is always False here; the actual write is the caller's (write_ledger).
    - When-needed: inspect before passing --write --confirm-rebuild-drift; preserve as the review evidence.
    - Escalates-to: write_ledger gate + LEDGER_REL path; the receipt's reentry_condition.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    paths = _json_diff_paths(current, rebuilt)
    path_set = [_json_pointer(path) for path in paths]
    writer_drift = _classify_rebuild_drift(current, rebuilt, write_scope=write_scope)
    claim_rows = _claim_ceiling_settlement_rows(current, rebuilt, paths)
    digest_rows = _digest_settlement_rows(current, rebuilt, paths)
    _promote_eligible_digest_aggregate_rows(digest_rows)
    claim_verdict_counts: dict[str, int] = {}
    digest_bucket_counts: dict[str, int] = {}
    digest_verdict_counts: dict[str, int] = {}
    blocked_bucket_counts: dict[str, int] = {}
    sample_paths_by_bucket: dict[str, list[str]] = {}
    blocked_settlement_samples_by_bucket: dict[str, list[dict[str, Any]]] = {}
    for row in claim_rows:
        verdict = str(row["verdict"])
        _increment(claim_verdict_counts, verdict)
        _sample_bucket(sample_paths_by_bucket, verdict, str(row["path"]))
        if not row.get("mutation_eligible_without_review"):
            _increment(blocked_bucket_counts, verdict)
            _sample_blocked_settlement_row(
                blocked_settlement_samples_by_bucket,
                verdict,
                row,
            )
    for row in digest_rows:
        bucket = str(row["bucket"])
        verdict = str(row["settlement_verdict"])
        _increment(digest_bucket_counts, bucket)
        _increment(digest_verdict_counts, verdict)
        _sample_bucket(sample_paths_by_bucket, bucket, str(row["path"]))
        if row.get("blocking"):
            _increment(blocked_bucket_counts, bucket)
            _sample_blocked_settlement_row(
                blocked_settlement_samples_by_bucket,
                bucket,
                row,
            )
    non_settlement_axis_counts = {
        axis: count
        for axis, count in writer_drift["axis_counts"].items()
        if axis not in SETTLEMENT_OWNER_AXES
    }
    for axis, count in non_settlement_axis_counts.items():
        bucket = f"non_settlement_axis:{axis}"
        blocked_bucket_counts[bucket] = count
        for path in paths:
            if _writer_drift_axis(path) == axis:
                _sample_bucket(sample_paths_by_bucket, bucket, _json_pointer(path))
                _sample_blocked_settlement_row(
                    blocked_settlement_samples_by_bucket,
                    bucket,
                    _non_settlement_axis_blocker_row(current, rebuilt, path),
                )
    if not paths:
        status = PASS
        mutation_plan = "no_write_needed"
        reentry_condition = "no drift detected; no settlement action required"
    elif blocked_bucket_counts:
        status = "blocked_pending_drift_settlement"
        mutation_plan = "no_generated_ledger_write"
        reentry_condition = (
            "review claim_ceiling verdicts, settle blocking digest buckets, and clear "
            "non-settlement axes before any generated-ledger write"
        )
    else:
        status = "ready_for_reviewed_generated_ledger_refresh"
        mutation_plan = (
            "rerun with --write --confirm-rebuild-drift only after preserving this "
            "settlement receipt as the review evidence"
        )
        reentry_condition = "review receipt, then run the owner writer and post-write check"
    status_basis = _settlement_status_basis(
        status=status,
        changed_path_count=len(paths),
        blocked_bucket_counts=blocked_bucket_counts,
    )
    return {
        "schema_version": "microcosm_substrate_substitution_drift_settlement_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "status_basis": status_basis,
        "settlement_item_id": (
            "substrate_substitution_drift_settlement:"
            f"{_json_payload_sha256(path_set)[len('sha256:'):][:12]}"
        ),
        "owner_lane": CHECKER_ID,
        "authority_posture": "settlement_receipt_not_source_authority",
        "ledger_path": LEDGER_REL.as_posix(),
        "current_ledger_sha256": _json_payload_sha256(current),
        "rebuilt_ledger_sha256": _json_payload_sha256(rebuilt),
        "drift_report_hash_or_ref": _json_payload_sha256(writer_drift),
        "expected_path_set_hash": _json_payload_sha256(path_set),
        "write_scope": write_scope,
        "allowed_axes": sorted(WRITER_DRIFT_SCOPE_AXES[write_scope])
        if WRITER_DRIFT_SCOPE_AXES[write_scope] is not None
        else "all",
        "changed_path_count": len(paths),
        "axis_counts": writer_drift["axis_counts"],
        "claim_ceiling_verdict_counts": claim_verdict_counts,
        "claim_ceiling_verdicts": claim_rows,
        "digest_relation_bucket_counts": digest_bucket_counts,
        "digest_relation_verdict_counts": digest_verdict_counts,
        "digest_relation_bucket_samples": digest_rows[:SETTLEMENT_SAMPLE_LIMIT],
        "non_settlement_axis_counts": non_settlement_axis_counts,
        "blocked_bucket_counts": blocked_bucket_counts,
        "blocked_settlement_samples_by_bucket": (
            blocked_settlement_samples_by_bucket
        ),
        "sample_paths_by_bucket": sample_paths_by_bucket,
        "mutation_plan": mutation_plan,
        "mutation_intent": mutation_plan,
        "write_performed": False,
        "post_write_check_status": "not_run_no_write",
        "reentry_condition": reentry_condition,
        "retirement_evidence": [
            "current ledger digest recorded",
            "rebuilt candidate digest recorded",
            "drift report hash recorded",
            "expected changed path set hash recorded",
            "post-write validation recorded when write_performed becomes true",
        ],
    }


def classify_rebuild_drift(
    public_root: str | Path,
    *,
    write_scope: str = "full",
) -> dict[str, Any]:
    """Report on-disk-vs-rebuilt ledger drift without writing (`--drift-report`).

    - Teleology: the no-write entrypoint that shows what a rebuild would change and whether it stays within the requested write scope, so an operator can review before confirming a write.
    - Guarantee: returns the `_classify_rebuild_drift` report (status PASS / drift_detected / blocked_unrelated_rebuild_drift) annotated with ledger_path, current_status, rebuilt_status, and a reentry_condition.
    - Fails: raises ValueError for an unsupported write_scope; raises if the registry is missing/malformed (via build_ledger). No mutation occurs.
    - Reads: existing ledger + all build_ledger source surfaces under the resolved public root.
    - Writes: None.
    - When-needed: run before `--write --confirm-rebuild-drift` to inspect changed axes.
    - Escalates-to: write_ledger; the report's reentry_condition.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    root = _public_root_for_path(public_root)
    current = _read_json_if_exists(root / LEDGER_REL)
    rebuilt = build_ledger(root)
    report = _classify_rebuild_drift(current, rebuilt, write_scope=write_scope)
    report["ledger_path"] = LEDGER_REL.as_posix()
    report["current_status"] = current.get("status") if current else None
    report["rebuilt_status"] = rebuilt.get("status")
    report["reentry_condition"] = (
        "rerun without --write after reviewing changed_axes; use --write "
        "--confirm-rebuild-drift only when the full classified drift is intended"
    )
    return report


def classify_drift_settlement(
    public_root: str | Path,
    *,
    write_scope: str = "full",
) -> dict[str, Any]:
    """Produce the no-write drift-settlement receipt (`--settlement-report`).

    - Teleology: the entrypoint that emits the review receipt gating a generated-ledger refresh, so claim-ceiling/digest/non-settlement-axis changes are settled before any write.
    - Guarantee: returns the `_settlement_receipt_from_payloads` receipt (status PASS / blocked_pending_drift_settlement / ready_for_reviewed_generated_ledger_refresh) annotated with current_status and rebuilt_status; `write_performed` is always False.
    - Fails: raises ValueError for an unsupported write_scope; raises if the registry is missing/malformed (via build_ledger). No mutation occurs.
    - Reads: existing ledger + all build_ledger source surfaces under the resolved public root.
    - Writes: None.
    - When-needed: run before `--write --confirm-rebuild-drift`; preserve the receipt as review evidence.
    - Escalates-to: write_ledger; the receipt's reentry_condition.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    root = _public_root_for_path(public_root)
    current = _read_json_if_exists(root / LEDGER_REL)
    rebuilt = build_ledger(root)
    receipt = _settlement_receipt_from_payloads(
        current,
        rebuilt,
        write_scope=write_scope,
    )
    receipt["current_status"] = current.get("status") if current else None
    receipt["rebuilt_status"] = rebuilt.get("status")
    return receipt


def _blocked_write_result(
    status: str,
    drift: dict[str, Any],
    settlement_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the no-write result returned when a write is blocked.

    - Teleology: gives every refused write a uniform, actionable result carrying why it blocked and how to re-enter, so the writer guard never mutates silently or opaquely.
    - Guarantee: returns a `microcosm_substrate_substitution_write_result_v1` dict with the given `status`, `write_performed: False`, the writer_drift report, a status-specific reentry_condition, and the settlement_receipt when provided.
    - Fails: never raises.
    - Reads: the passed-in drift/receipt only (no filesystem).
    - Writes: None — by construction this is the not-written path.
    """
    if status == "blocked_unrelated_rebuild_drift":
        reentry_condition = (
            "choose a broader write scope, pass --allow-unrelated-rebuild-drift "
            "after reviewing changed_axes, or use a surgical refresh for the scoped axis"
        )
    else:
        reentry_condition = (
            "review writer_drift, then rerun with --confirm-rebuild-drift if the "
            "classified rebuild changes are intended"
        )
    result = {
        "schema_version": "microcosm_substrate_substitution_write_result_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "ledger_path": LEDGER_REL.as_posix(),
        "write_performed": False,
        "writer_guard": "rebuild_drift_classified_before_mutation",
        "writer_drift": drift,
        "reentry_condition": reentry_condition,
    }
    if settlement_receipt is not None:
        result["settlement_receipt"] = settlement_receipt
    return result


def write_ledger(
    public_root: str | Path,
    *,
    write_scope: str = "full",
    confirm_rebuild_drift: bool = False,
    allow_unrelated_rebuild_drift: bool = False,
) -> dict[str, Any]:
    """Rebuild and atomically persist the ledger behind three drift guards.

    - Teleology: the guarded mutating entrypoint (`--write`) — it refuses to overwrite the release-trust ledger until unrelated-axis drift, blocking settlement, and unconfirmed drift are all cleared.
    - Guarantee: writes `core/substrate_substitution_ledger.json` (atomic) ONLY when no unrelated axes (or override), settlement is not blocked, and either there are no changed paths or confirm_rebuild_drift is set; then returns the ledger plus a write_result with write_performed True and a post-write validation. When any guard trips it returns a `_blocked_write_result` with write_performed False and writes nothing.
    - Fails: raises ValueError for an unsupported write_scope; raises if the registry is missing/malformed (via build_ledger). A failed post-write validation surfaces as `post_write_validation_blocked` in the settlement receipt, not as an exception.
    - Reads: existing ledger + all build_ledger source surfaces under the resolved public root.
    - Writes: core/substrate_substitution_ledger.json (atomic) on the success path ONLY; no write on any blocked path.
    - When-needed: call to commit a reviewed rebuild after classify_rebuild_drift / classify_drift_settlement.
    - Escalates-to: validate_ledger (post-write); tests/test_organ_registry_authority_floor.py.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness — a written ledger is not a release sign-off.
    """
    root = _public_root_for_path(public_root)
    ledger = build_ledger(root)
    current = _read_json_if_exists(root / LEDGER_REL)
    drift = _classify_rebuild_drift(current, ledger, write_scope=write_scope)
    drift["ledger_path"] = LEDGER_REL.as_posix()
    settlement_receipt = _settlement_receipt_from_payloads(
        current,
        ledger,
        write_scope=write_scope,
    )
    if drift["unrelated_axes"] and not allow_unrelated_rebuild_drift:
        return _blocked_write_result(
            "blocked_unrelated_rebuild_drift",
            drift,
            settlement_receipt,
        )
    if settlement_receipt.get("status") == "blocked_pending_drift_settlement":
        return _blocked_write_result(
            "blocked_pending_drift_settlement",
            drift,
            settlement_receipt,
        )
    if drift["changed_path_count"] and not confirm_rebuild_drift:
        return _blocked_write_result(
            "blocked_unconfirmed_rebuild_drift",
            drift,
            settlement_receipt,
        )
    write_json_atomic(root / LEDGER_REL, ledger)
    post_write_validation = validate_ledger(root)
    applied_settlement_receipt = dict(settlement_receipt)
    applied_settlement_receipt.update(
        {
            "status": PASS
            if post_write_validation.get("status") == PASS
            else "post_write_validation_blocked",
            "mutation_plan": "reviewed_generated_ledger_refresh_applied",
            "mutation_intent": "reviewed_generated_ledger_refresh_applied",
            "write_performed": True,
            "post_write_check_status": post_write_validation.get("status"),
            "post_write_validation": post_write_validation,
        }
    )
    result = dict(ledger)
    result["write_result"] = {
        "schema_version": "microcosm_substrate_substitution_write_result_v1",
        "status": PASS,
        "ledger_path": LEDGER_REL.as_posix(),
        "write_performed": True,
        "writer_guard": "rebuild_drift_classified_before_mutation",
        "writer_drift": drift,
        "settlement_receipt": applied_settlement_receipt,
    }
    return result


def write_ledger_organ_slice(
    public_root: str | Path,
    organ_ids: list[str],
) -> dict[str, Any]:
    """Rebuild and persist only the selected organ rows into the ledger.

    - Teleology: the surgical write path (`--write --organ-id ...`) that refreshes specific organs while leaving unrelated rows byte-stable, used when a full rebuild would fold in concurrent drift.
    - Guarantee: on success writes the merged ledger (atomic) and returns it with a write_result (write_performed True, post-write validation, selected_organ_ids). On an invalid slice returns `blocked_invalid_organ_slice` (with the error) and on a failing merged validation returns `blocked_organ_slice_validation` — both with write_performed False and no write.
    - Fails: never raises out of this function for slice errors (ValueError from _merge_organ_slice is caught and returned as blocked_invalid_organ_slice); raises only if build_ledger's registry read fails.
    - Reads: existing ledger + all build_ledger source surfaces under the resolved public root.
    - Writes: core/substrate_substitution_ledger.json (atomic) ONLY when the merged slice validates; no write on either blocked path.
    - When-needed: call to land one organ's refreshed row without a whole-ledger rewrite.
    - Escalates-to: validate_ledger (post-write); tests/test_organ_registry_authority_floor.py.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    root = _public_root_for_path(public_root)
    current = _read_json_if_exists(root / LEDGER_REL)
    rebuilt = build_ledger(root)
    selected_ids = {str(organ_id) for organ_id in organ_ids if str(organ_id).strip()}
    try:
        merged = _merge_organ_slice(root, current, rebuilt, selected_ids)
    except ValueError as exc:
        return {
            "schema_version": "microcosm_substrate_substitution_write_result_v1",
            "checker_id": CHECKER_ID,
            "status": "blocked_invalid_organ_slice",
            "ledger_path": LEDGER_REL.as_posix(),
            "write_performed": False,
            "selected_organ_ids": sorted(selected_ids),
            "error": str(exc),
        }
    drift = _classify_rebuild_drift(current, merged, write_scope="full")
    drift["ledger_path"] = LEDGER_REL.as_posix()
    if merged.get("status") != PASS:
        return {
            "schema_version": "microcosm_substrate_substitution_write_result_v1",
            "checker_id": CHECKER_ID,
            "status": "blocked_organ_slice_validation",
            "ledger_path": LEDGER_REL.as_posix(),
            "write_performed": False,
            "selected_organ_ids": sorted(selected_ids),
            "writer_drift": drift,
            "validation": merged.get("validation"),
        }
    write_json_atomic(root / LEDGER_REL, merged)
    post_write_validation = validate_ledger(root)
    result = dict(merged)
    result["write_result"] = {
        "schema_version": "microcosm_substrate_substitution_write_result_v1",
        "status": PASS
        if post_write_validation.get("status") == PASS
        else "post_write_validation_blocked",
        "ledger_path": LEDGER_REL.as_posix(),
        "write_performed": True,
        "writer_guard": "organ_slice_merge_validated_before_mutation",
        "selected_organ_ids": sorted(selected_ids),
        "writer_drift": drift,
        "post_write_check_status": post_write_validation.get("status"),
        "post_write_validation": post_write_validation,
        "mutation_intent": "organ_slice_ledger_merge",
    }
    return result


def _parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for this validator.

    - Teleology: defines the command surface (build / --check / --write / --drift-report / --settlement-report / --write-scope / --organ-id / confirmation flags) that main dispatches on.
    - Guarantee: returns an argparse.ArgumentParser with --root (default "."), the mode flags, --write-scope constrained to the supported scopes, and an appendable --organ-id list.
    - Fails: never raises at construction.
    - Writes: None.
    """
    parser = argparse.ArgumentParser(description="Build or validate substrate disposition ledger")
    parser.add_argument("--root", default=".")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--drift-report", action="store_true")
    parser.add_argument("--settlement-report", action="store_true")
    parser.add_argument(
        "--write-scope",
        choices=sorted(WRITER_DRIFT_SCOPE_AXES),
        default="full",
    )
    parser.add_argument("--confirm-rebuild-drift", action="store_true")
    parser.add_argument("--allow-unrelated-rebuild-drift", action="store_true")
    parser.add_argument(
        "--organ-id",
        action="append",
        default=[],
        help=(
            "With --write, merge only the selected rebuilt organ row(s) plus "
            "derived summary/validation into the existing ledger."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: dispatch to build/check/write/drift/settlement and print JSON.

    - Teleology: the process-exit surface that turns this validator into a CI/command gate, mapping mode flags to the right function and translating result status into an exit code.
    - Guarantee: parses argv, runs the selected operation (settlement-report > drift-report > write[/organ-slice] > check > default build), prints the result as sorted-indent JSON, and returns 0 when result.status == PASS else 1.
    - Fails: propagates ValueError from an unsupported write_scope and registry-missing errors from the called functions; otherwise returns a non-zero exit for any non-PASS status rather than raising.
    - Reads: whatever the dispatched function reads under the resolved root.
    - Writes: core/substrate_substitution_ledger.json only when a --write mode is selected and its guards pass.
    - When-needed: this is the shell/CI entry; inspect printed JSON `status` + `issues` on a non-zero exit.
    - Escalates-to: validate_ledger / write_ledger; tests/test_organ_registry_authority_floor.py.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    args = _parser().parse_args(argv)
    root = _public_root_for_path(args.root)
    if args.settlement_report:
        result = classify_drift_settlement(root, write_scope=args.write_scope)
    elif args.drift_report:
        result = classify_rebuild_drift(root, write_scope=args.write_scope)
    elif args.write:
        if args.organ_id:
            result = write_ledger_organ_slice(root, args.organ_id)
        else:
            result = write_ledger(
                root,
                write_scope=args.write_scope,
                confirm_rebuild_drift=args.confirm_rebuild_drift,
                allow_unrelated_rebuild_drift=args.allow_unrelated_rebuild_drift,
            )
    elif args.check:
        result = validate_ledger(root)
    else:
        result = build_ledger(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
