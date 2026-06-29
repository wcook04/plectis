"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.validators.dependency_preflight` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: CHECKER_ID, ACCEPTED_ORGAN_IDS, ACCEPTANCE_PLAN_REL, AUTHORITY_SNAPSHOT_REL, EVIDENCE_CLASS_REGISTRY_REL, DEFERRED_ORGAN_IDS, run_dependency_preflight, main
- Reads: call arguments, module constants, imported helpers, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.private_state_scan, microcosm_core.receipts, microcosm_core.runtime_shell, microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.runtime_shell import PRODUCT_PATH_DEMOTED_ORGAN_IDS, RUNTIME_STEPS
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.dependency_preflight"
ACCEPTED_ORGAN_IDS = [step.organ_id for step in RUNTIME_STEPS]
ACCEPTANCE_PLAN_REL = Path("core/acceptance/first_wave_acceptance.json")
AUTHORITY_SNAPSHOT_REL = Path("receipts/runtime_shell/public_authority_map.json")
EVIDENCE_CLASS_REGISTRY_REL = Path("core/organ_evidence_classes.json")
DEFERRED_ORGAN_IDS = ["formal_math_lean_proof_organ"]


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    Resolve the public substrate root that scopes all preflight path display and scanning.

    - Teleology: protects the public-root boundary claim (private-path display + forbidden-class scope) from leaking host/absolute or out-of-tree roots into the receipt.
    - Guarantee: returns a resolved directory Path that either is named ``microcosm-substrate`` or carries the public markers (``pyproject.toml`` + ``src/microcosm_core`` + ``core/private_state_forbidden_classes.json``), walking ``start`` and its parents.
    - Fails: no marker found in any ancestor -> no raise; falls back to ``Path.cwd().resolve(strict=False)`` (returns cwd, never an error envelope).
    - Reads: filesystem only (presence of pyproject.toml / src/microcosm_core / core/private_state_forbidden_classes.json); reads no manifest payload.
    - Writes: None
    - When-needed: trust when establishing which root scopes public-relative display and private-state scanning for a given out_path.
    - Escalates-to: microcosm-substrate/core/private_state_forbidden_classes.json (the marker that confirms a true public root).
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
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
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    """
    [ACTION]
    Render a path as a public-root-relative display string for receipt fields.

    - Teleology: keeps receipt-visible paths scoped to the public root so host/absolute paths never leak into the dependency-preflight receipt.
    - Guarantee: returns the string from ``public_relative_path(path, display_root=public_root)`` (path relativized under public_root, or its safe public form).
    - Fails: delegates to public_relative_path; raises only if that helper raises, otherwise returns a string.
    - Non-goal: does not authorize release, source-body export, or private-root equivalence; only formats a display string.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Strip the forbidden-output-fields detail from a private-state scan before it enters the receipt.

    - Teleology: protects the public-safe-receipt claim by dropping the ``forbidden_output_fields`` payload that could echo private-class detail.
    - Guarantee: returns a shallow copy of ``scan`` with the ``forbidden_output_fields`` key removed (all other keys preserved verbatim); the input dict is not mutated.
    - Fails: never raises; returns the copied dict even when ``forbidden_output_fields`` is absent.
    - Non-goal: does not authorize release or assert the scan passed; only redacts one field for receipt safety.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    Extract the dict-shaped rows under a payload key, discarding non-dict entries.

    - Teleology: gives every downstream registry/plan/snapshot reader a defensive row accessor so malformed non-dict entries never reach contract logic.
    - Guarantee: returns a list containing only the dict elements of ``payload[key]``; returns ``[]`` when the key is absent or its value is not iterable-of-dicts.
    - Fails: raises ``TypeError`` only if ``payload[key]`` is present but not iterable; otherwise never raises and returns a filtered list.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _organ_registry(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    Load the public organ registry that is the source-of-authority for accepted organs.

    - Teleology: provides the single registry source whose ``accepted_current_authority`` rows define the organ set the whole preflight reconciles against.
    - Guarantee: returns the parsed JSON object from ``public_root/core/organ_registry.json`` via read_json_strict.
    - Fails: missing or malformed/non-JSON registry -> ``read_json_strict`` raises (FileNotFound / json / value error) and propagates; there is no empty-envelope fallback.
    - When-needed: trust when you need the authoritative accepted-organ source before any cross-surface convergence check.
    - Escalates-to: core/organ_registry.json (the registry itself).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return read_json_strict(public_root / "core/organ_registry.json")


def _accepted_from_registry(registry: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    Project the accepted-current-authority organ ids out of the registry payload.

    - Teleology: defines the canonical accepted-organ id list that every preflight convergence surface is measured against.
    - Guarantee: returns the ``organ_id`` (stringified) of each ``implemented_organs`` row whose ``status == "accepted_current_authority"``, in registry order.
    - Fails: never raises; returns ``[]`` when no row qualifies or ``implemented_organs`` is absent/non-list (via _rows).
    - When-needed: trust when you need the registry-derived accepted set rather than the runtime-step set.
    - Escalates-to: core/organ_registry.json (``implemented_organs[].status``).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        str(row.get("organ_id"))
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _fixture_input_exists(public_root: Path, rel: str) -> bool:
    """
    [ACTION]
    Test whether a declared fixture input path is present under the public root.

    - Teleology: backs the fixture-input-presence claim by checking each declared input on disk relative to the public root.
    - Guarantee: returns ``True`` iff ``public_root/rel`` exists on the filesystem, else ``False``.
    - Fails: never raises; a non-existent path returns ``False`` rather than erroring.
    - Escalates-to: fixtures/first_wave/<organ_id>/input (the on-disk fixture inputs being probed).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (public_root / rel).exists()


def _public_fixture_manifest(public_root: Path, organ_id: str, row: dict[str, Any]) -> Path:
    """
    [ACTION]
    Resolve the public-tree fixture-manifest path for an organ, never trusting a macro path.

    - Teleology: protects the fixture-presence claim from following a macro/foreign ``fixture_manifest`` path; re-homes it under the public ``core/fixture_manifests`` tree.
    - Guarantee: returns ``public_root/core/fixture_manifests/<name>`` using only the macro manifest's basename; prefers the existing file, else the canonical ``<organ_id>.fixture_manifest.json`` if it exists, else the basename path.
    - Fails: None (cannot raise or return an error; when no file exists it returns a Path whose ``.is_file()`` is False, which the caller treats as absent).
    - Reads: filesystem presence under public_root/core/fixture_manifests/; reads no JSON body.
    - Writes: None
    - When-needed: trust when locating the public manifest for an accepted organ before checking inputs.
    - Escalates-to: core/fixture_manifests/<organ_id>.fixture_manifest.json (canonical public manifest).
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    macro_manifest = Path(str(row.get("fixture_manifest") or ""))
    manifest_name = macro_manifest.name or f"{organ_id}.fixture_manifest.json"
    manifest_path = public_root / "core/fixture_manifests" / manifest_name
    if manifest_path.is_file():
        return manifest_path
    canonical_path = (
        public_root / "core/fixture_manifests" / f"{organ_id}.fixture_manifest.json"
    )
    return canonical_path if canonical_path.is_file() else manifest_path


def _public_manifest_inputs(manifest_path: Path) -> list[str]:
    """
    [ACTION]
    Extract declared fixture input path strings from a public fixture manifest.

    - Teleology: protects the fixture-input-presence claim by reading inputs from the public manifest rather than trusting macro readiness rows.
    - Guarantee: returns a list of input path strings drawn from ``manifest["inputs"]`` (each dict row's ``path`` or each bare string row); returns ``[]`` when the file is absent, the payload is not a dict, or ``inputs`` is not a list.
    - Fails: malformed/non-JSON manifest -> ``read_json_strict`` raises (json/value error) and propagates; a present-but-non-dict payload returns ``[]`` (no raise).
    - Reads: <manifest_path> JSON body via read_json_strict; consumes only the ``inputs`` key.
    - Writes: None
    - When-needed: trust when enumerating which fixture input paths must exist on disk for an accepted organ.
    - Escalates-to: core/fixture_manifests/<organ_id>.fixture_manifest.json (the ``inputs`` array it parses).
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        return []
    inputs = manifest.get("inputs", [])
    paths: list[str] = []
    if isinstance(inputs, list):
        for row in inputs:
            if isinstance(row, dict) and row.get("path"):
                paths.append(str(row["path"]))
            elif isinstance(row, str):
                paths.append(row)
    return paths


def _negative_case_count(payload: Any) -> int:
    """
    [ACTION]
    Count negative-matrix cases across the several shapes the matrix file may take.

    - Teleology: yields the receipt's ``negative_matrix_case_count`` regardless of whether the matrix is a bare list, a keyed-rows dict, or a free-form mapping.
    - Guarantee: returns ``len(payload)`` for a list; for a dict, the length of the first present list under ``negative_cases``/``cases``/``rows``, else the count of dict/list values; ``0`` for any other type.
    - Fails: never raises; an unrecognized payload type returns ``0``.
    - When-needed: trust when reporting how many negative cases the preflight observed (a count, not a pass/fail gate).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("negative_cases", "cases", "rows"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return len(rows)
        return sum(1 for value in payload.values() if isinstance(value, (dict, list)))
    return 0


def _id_counts(ids: list[str]) -> dict[str, int]:
    """
    [ACTION]
    Tally occurrences of each id, the primitive behind duplicate detection.

    - Teleology: provides the per-id multiplicity map that ``_duplicates`` uses to flag double-registered evidence-class / authority rows.
    - Guarantee: returns a dict mapping each distinct id in ``ids`` to its occurrence count (sum of counts equals ``len(ids)``).
    - Fails: never raises; an empty input returns ``{}``.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    counts: dict[str, int] = {}
    for item in ids:
        counts[item] = counts.get(item, 0) + 1
    return counts


def _duplicates(ids: list[str]) -> list[str]:
    """
    [ACTION]
    Return the ids that appear more than once, driving duplicate-row lifecycle defects.

    - Teleology: surfaces double-registered organ ids (evidence-class, authority snapshot) so the coverage pass can emit a duplicate defect.
    - Guarantee: returns the sorted, de-duplicated list of ids whose occurrence count in ``ids`` exceeds one; ``[]`` when all ids are unique.
    - Fails: never raises; an empty input returns ``[]``.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return sorted(item for item, count in _id_counts(ids).items() if count > 1)


def _accepted_plan_organs(public_root: Path) -> list[str]:
    """
    [ACTION]
    Read the accepted organ ids declared by the first-wave acceptance plan.

    - Teleology: provides the acceptance-plan side of the accepted-vs-plan convergence so plan/registry divergence becomes a lifecycle defect.
    - Guarantee: returns the truthy ``organ_id`` strings from ``accepted_current_authority_organs`` rows of ``public_root/core/acceptance/first_wave_acceptance.json``; returns ``[]`` when that file is absent.
    - Fails: malformed/non-JSON plan -> ``read_json_strict`` raises and propagates; a missing file returns ``[]`` (no raise).
    - When-needed: trust when reconciling the acceptance plan against the registry accepted set.
    - Escalates-to: core/acceptance/first_wave_acceptance.json (ACCEPTANCE_PLAN_REL).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = public_root / ACCEPTANCE_PLAN_REL
    if not path.is_file():
        return []
    payload = read_json_strict(path)
    return [
        str(row.get("organ_id"))
        for row in _rows(payload, "accepted_current_authority_organs")
        if row.get("organ_id")
    ]


def _evidence_class_rows(public_root: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    Load the organ evidence-class rows that bind each organ to its evidence discipline.

    - Teleology: provides the evidence-class registry rows used to check one-class-per-organ and the external-subprocess-witness receipt invariant.
    - Guarantee: returns the dict rows under ``organ_evidence_classes`` from ``public_root/core/organ_evidence_classes.json``; returns ``[]`` when that file is absent.
    - Fails: malformed/non-JSON registry -> ``read_json_strict`` raises and propagates; a missing file returns ``[]`` (no raise).
    - When-needed: trust when verifying evidence-class coverage and witness-receipt evidence per organ.
    - Escalates-to: core/organ_evidence_classes.json (EVIDENCE_CLASS_REGISTRY_REL).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, subprocess side effects requested by the caller.
    """
    path = public_root / EVIDENCE_CLASS_REGISTRY_REL
    if not path.is_file():
        return []
    payload = read_json_strict(path)
    return _rows(payload, "organ_evidence_classes")


def _authority_snapshot(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    Load the public runtime-shell authority snapshot used to check organ/surface lens convergence.

    - Teleology: protects the public-authority convergence claim (organ/surface lens coverage) from a missing or non-dict ``public_authority_map.json`` snapshot.
    - Guarantee: returns the snapshot dict from ``public_root/receipts/runtime_shell/public_authority_map.json`` when it is a dict; returns ``{}`` when the file is absent or the payload is not a dict.
    - Fails: malformed/non-JSON snapshot -> ``read_json_strict`` raises and propagates; an empty ``{}`` return downstream drives a ``missing_snapshot_projection`` lifecycle defect (not an exception here).
    - Reads: receipts/runtime_shell/public_authority_map.json via read_json_strict.
    - Writes: None
    - When-needed: trust when reconciling accepted organs against published authority/lens rows.
    - Escalates-to: receipts/runtime_shell/public_authority_map.json (AUTHORITY_SNAPSHOT_REL).
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    path = public_root / AUTHORITY_SNAPSHOT_REL
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _surface_mentions_organ(surface: dict[str, Any], organ_id: str) -> bool:
    """
    [ACTION]
    Decide whether a public surface row references an organ by id or hyphen-slug.

    - Teleology: backs the public-lens coverage claim by detecting whether a command-path organ is actually mentioned by a published surface row.
    - Guarantee: returns ``True`` iff ``organ_id`` or its ``_``->``-`` slug appears in the joined ``surface_id``/``command``/``endpoint``/``authority_role`` text of the surface row, else ``False``.
    - Fails: never raises; missing keys are coerced to empty strings before matching.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    slug = organ_id.replace("_", "-")
    text = " ".join(
        str(surface.get(key) or "")
        for key in ("surface_id", "command", "endpoint", "authority_role")
    )
    return organ_id in text or slug in text


def _add_lifecycle_defect(
    defects: list[dict[str, Any]],
    defect_id: str,
    *,
    organ_id: str | None = None,
    surface: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """
    [ACTION]
    Append one normalized lifecycle-defect record to the accumulating defects list.

    - Teleology: gives the coverage pass a single shaped constructor for every lifecycle defect so defect records stay schema-consistent.
    - Guarantee: mutates ``defects`` in place by appending a dict with ``defect_id`` plus, when provided, ``organ_id``/``surface``/``detail`` keys; returns ``None``.
    - Fails: never raises; omitted optional fields are simply absent from the appended record.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    defect: dict[str, Any] = {"defect_id": defect_id}
    if organ_id is not None:
        defect["organ_id"] = organ_id
    if surface is not None:
        defect["surface"] = surface
    if detail:
        defect["detail"] = detail
    defects.append(defect)


def _consumer_contract_row(
    surface_id: str,
    *,
    required_for_organ_ids: list[str],
    observed_organ_ids: list[str],
    owner_surface: str,
    receipt_ref: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    Build one consumer-surface convergence row comparing required vs observed organ ids.

    - Teleology: encodes the per-surface contract (runtime steps, acceptance plan, evidence registry, authority/lens rows, fixtures) so convergence is auditable surface-by-surface.
    - Guarantee: returns a row with ``status`` = PASS when neither ``missing_organ_ids`` (required minus observed) nor ``stale_organ_ids`` (observed minus required) is non-empty, else ``"blocked"``; echoes both id lists, ``owner_surface``, and an optional ``receipt_ref``.
    - Fails: never raises; returns a ``"blocked"`` row (not an exception) whenever sets diverge.
    - Non-goal: does not authorize release or repair; it only records the convergence verdict for one surface.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    missing = [
        organ_id for organ_id in required_for_organ_ids if organ_id not in observed_organ_ids
    ]
    stale = [
        organ_id for organ_id in observed_organ_ids if organ_id not in required_for_organ_ids
    ]
    row: dict[str, Any] = {
        "surface_id": surface_id,
        "status": PASS if not missing and not stale else "blocked",
        "required_for_organ_ids": required_for_organ_ids,
        "observed_organ_ids": observed_organ_ids,
        "missing_organ_ids": missing,
        "stale_organ_ids": stale,
        "owner_surface": owner_surface,
    }
    if receipt_ref is not None:
        row["receipt_ref"] = receipt_ref
    return row


def _organ_lifecycle_convergence(
    *,
    accepted: list[str],
    public_authority_required_ids: list[str],
    demoted_drilldown_ids: list[str],
    runtime_ids: list[str],
    accepted_plan_ids: list[str],
    evidence_ids: list[str],
    organ_authority_ids: list[str],
    command_path_organs: set[str],
    public_lens_organs: set[str],
    fixture_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    Assemble the consumer-contract convergence block across all six lifecycle consumer surfaces.

    - Teleology: gives the receipt one authoritative convergence object that proves accepted organs are consistently consumed by runtime steps, the acceptance plan, evidence registry, authority/lens rows, and fixtures.
    - Guarantee: returns an ``organ_lifecycle_convergence_v1`` dict whose ``status`` is PASS iff every consumer-surface row passes, listing affected surfaces/organs and pinning ``release_authority``/``proof_authority``/``source_body_exported`` all to ``False``.
    - Fails: never raises; divergence yields ``status == "blocked"`` with populated ``affected_consumer_surfaces`` and ``changed_organ_ids``.
    - When-needed: trust when you need the cross-surface convergence verdict and the list of organs/surfaces that diverged.
    - Escalates-to: receipts/runtime_shell/public_authority_map.json + receipts/preflight/dependency_preflight.json (its required_snapshot_refs).
    - Non-goal: does not authorize release, provider calls, source export, or proof correctness; it asserts consumer-contract convergence only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    fixture_pass_ids = [
        str(row.get("organ_id"))
        for row in fixture_checks
        if row.get("organ_id") and row.get("status") == PASS
    ]
    ordered_command_path_organs = [
        organ_id for organ_id in accepted if organ_id in command_path_organs
    ]
    ordered_public_lens_organs = [
        organ_id for organ_id in accepted if organ_id in public_lens_organs
    ]
    consumer_surfaces = [
        _consumer_contract_row(
            "runtime_steps",
            required_for_organ_ids=accepted,
            observed_organ_ids=runtime_ids,
            owner_surface="microcosm_core.runtime_shell.RUNTIME_STEPS",
        ),
        _consumer_contract_row(
            "first_wave_acceptance_plan",
            required_for_organ_ids=accepted,
            observed_organ_ids=accepted_plan_ids,
            owner_surface=ACCEPTANCE_PLAN_REL.as_posix(),
        ),
        _consumer_contract_row(
            "organ_evidence_class_registry",
            required_for_organ_ids=accepted,
            observed_organ_ids=evidence_ids,
            owner_surface=EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        ),
        _consumer_contract_row(
            "public_authority_organ_rows",
            required_for_organ_ids=public_authority_required_ids,
            observed_organ_ids=organ_authority_ids,
            owner_surface="RuntimeShell.authority().organ_authority",
            receipt_ref=AUTHORITY_SNAPSHOT_REL.as_posix(),
        ),
        _consumer_contract_row(
            "public_command_lens_rows",
            required_for_organ_ids=ordered_command_path_organs,
            observed_organ_ids=ordered_public_lens_organs,
            owner_surface="RuntimeShell.authority().surface_authority",
            receipt_ref=AUTHORITY_SNAPSHOT_REL.as_posix(),
        ),
        _consumer_contract_row(
            "fixture_bundle_checks",
            required_for_organ_ids=accepted,
            observed_organ_ids=fixture_pass_ids,
            owner_surface="core/fixture_manifests/*.fixture_manifest.json",
        ),
    ]
    affected_surfaces = [
        row["surface_id"] for row in consumer_surfaces if row["status"] != PASS
    ]
    affected_organs = sorted(
        {
            organ_id
            for row in consumer_surfaces
            if row["status"] != PASS
            for organ_id in [*row["missing_organ_ids"], *row["stale_organ_ids"]]
        }
    )
    return {
        "schema_version": "organ_lifecycle_convergence_v1",
        "status": PASS if not affected_surfaces else "blocked",
        "source_registry_ref": "core/organ_registry.json",
        "evidence_registry_ref": EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        "organ_count": len(accepted),
        "consumer_surfaces": consumer_surfaces,
        "affected_consumer_surfaces": affected_surfaces,
        "changed_organ_ids": affected_organs,
        "negative_guard_surface_refs": [
            "non-consumer notes, demos, and incidental receipts are excluded from the "
            "organ lifecycle contract unless listed in checked_surfaces"
        ],
        "demoted_drilldown_organ_ids": demoted_drilldown_ids,
        "false_positive_guard_result": PASS if not affected_surfaces else "not_applicable",
        "required_snapshot_refs": [
            AUTHORITY_SNAPSHOT_REL.as_posix(),
            "receipts/preflight/dependency_preflight.json",
        ],
        "incidental_receipt_churn_excluded": True,
        "validation_refs": [
            "microcosm_core.validators.dependency_preflight",
            "tests/test_dependency_preflight.py",
        ],
        "public_authority_boundary": (
            "consumer-contract convergence only; not release, source, proof, or "
            "provider-call authority"
        ),
        "release_authority": False,
        "proof_authority": False,
        "source_body_exported": False,
        "next_reentry_condition": (
            "rerun dependency preflight after accepted organ, evidence-class, "
            "runtime-step, public authority, or fixture-manifest changes"
        ),
    }


def _organ_lifecycle_coverage(
    public_root: Path,
    registry: dict[str, Any],
    *,
    accepted: list[str],
    fixture_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    Run the full organ-lifecycle coverage pass and emit every lifecycle defect it finds.

    - Teleology: the central coverage gate that cross-checks accepted organs against runtime steps, the acceptance plan, evidence classes, fixtures/receipts, the authority snapshot, public lens rows, and witness-receipt evidence.
    - Guarantee: returns an ``organ_lifecycle_coverage_v1`` dict whose ``status`` is PASS iff ``defects == []``, carrying the defect list, ``accepted_order_status``, coverage counts, the nested convergence block, and the ``anti_claim`` ceiling.
    - Fails: helper reads of acceptance/evidence/authority files may raise on malformed JSON and propagate; otherwise never raises, signalling problems as ``"blocked"`` defects rather than exceptions.
    - When-needed: trust when you need the authoritative list of organ-lifecycle defects and the overall coverage verdict.
    - Escalates-to: tests/test_dependency_preflight.py + core/organ_registry.json (the registry/test pair backing every invariant here).
    - Non-goal: does not authorize release, provider calls, source mutation, or private-data equivalence; checks public convergence only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, declared filesystem outputs, subprocess side effects requested by the caller.
    """
    runtime_ids = list(ACCEPTED_ORGAN_IDS)
    accepted_plan_ids = _accepted_plan_organs(public_root)
    evidence_rows = _evidence_class_rows(public_root)
    evidence_ids = [str(row.get("organ_id")) for row in evidence_rows if row.get("organ_id")]
    evidence_class_by_id = {
        str(row.get("organ_id")): str(row.get("evidence_class"))
        for row in evidence_rows
        if row.get("organ_id")
    }
    demoted_drilldown_ids = [
        organ_id for organ_id in accepted if organ_id in PRODUCT_PATH_DEMOTED_ORGAN_IDS
    ]
    public_authority_required_ids = [
        organ_id for organ_id in accepted if organ_id not in PRODUCT_PATH_DEMOTED_ORGAN_IDS
    ]
    registry_rows_by_id = {
        str(row.get("organ_id")): row
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority" and row.get("organ_id")
    }
    authority = _authority_snapshot(public_root)
    surface_rows = _rows(authority, "surface_authority")
    organ_authority_rows = _rows(authority, "organ_authority")
    organ_authority_ids = [
        str(row.get("organ_id")) for row in organ_authority_rows if row.get("organ_id")
    ]
    command_path = [
        str(command) for command in authority.get("command_path", []) if isinstance(command, str)
    ]

    defects: list[dict[str, Any]] = []

    for organ_id in sorted(set(accepted) - set(runtime_ids)):
        _add_lifecycle_defect(defects, "accepted_without_runtime_step", organ_id=organ_id)
    for organ_id in sorted(set(runtime_ids) - set(accepted)):
        _add_lifecycle_defect(defects, "runtime_step_without_accepted_organ", organ_id=organ_id)
    if accepted and set(accepted) == set(runtime_ids):
        accepted_order_status = PASS
    else:
        accepted_order_status = "blocked"

    for organ_id in sorted(set(accepted) - set(accepted_plan_ids)):
        _add_lifecycle_defect(defects, "accepted_without_acceptance_plan", organ_id=organ_id)
    for organ_id in sorted(set(accepted_plan_ids) - set(accepted)):
        _add_lifecycle_defect(defects, "acceptance_plan_without_accepted_organ", organ_id=organ_id)

    for organ_id in sorted(set(accepted) - set(evidence_ids)):
        _add_lifecycle_defect(defects, "missing_evidence_class", organ_id=organ_id)
    for organ_id in sorted(set(evidence_ids) - set(accepted)):
        _add_lifecycle_defect(defects, "evidence_class_without_accepted_organ", organ_id=organ_id)
    for organ_id in _duplicates(evidence_ids):
        _add_lifecycle_defect(defects, "duplicate_evidence_class", organ_id=organ_id)

    fixture_by_id = {str(row.get("organ_id")): row for row in fixture_checks}
    for organ_id in accepted:
        row = fixture_by_id.get(organ_id, {})
        if row.get("status") != PASS:
            _add_lifecycle_defect(
                defects,
                "missing_fixture_bundle",
                organ_id=organ_id,
                detail={
                    "missing_fixture_inputs": row.get("missing_fixture_inputs", []),
                    "fixture_manifest": row.get("fixture_manifest"),
                },
            )
        registry_row = registry_rows_by_id.get(organ_id, {})
        if not registry_row.get("generated_receipts"):
            _add_lifecycle_defect(defects, "missing_receipt_ref", organ_id=organ_id)

    if not authority:
        _add_lifecycle_defect(
            defects,
            "missing_snapshot_projection",
            surface=AUTHORITY_SNAPSHOT_REL.as_posix(),
        )
    else:
        surface_counts = authority.get("surface_counts", {})
        declared_surface_count = (
            surface_counts.get("surface_authority_count")
            if isinstance(surface_counts, dict)
            else None
        )
        declared_organ_count = (
            surface_counts.get("organ_authority_count")
            if isinstance(surface_counts, dict)
            else None
        )
        if declared_surface_count != len(surface_rows):
            _add_lifecycle_defect(
                defects,
                "stale_surface_authority_count",
                detail={
                    "declared_surface_authority_count": declared_surface_count,
                    "actual_surface_authority_count": len(surface_rows),
                },
            )
        if declared_organ_count != len(organ_authority_rows):
            _add_lifecycle_defect(
                defects,
                "stale_organ_authority_count",
                detail={
                    "declared_organ_authority_count": declared_organ_count,
                    "actual_organ_authority_count": len(organ_authority_rows),
                },
            )
        for organ_id in sorted(set(public_authority_required_ids) - set(organ_authority_ids)):
            _add_lifecycle_defect(defects, "missing_snapshot_projection", organ_id=organ_id)
        for organ_id in sorted(set(organ_authority_ids) - set(public_authority_required_ids)):
            _add_lifecycle_defect(defects, "snapshot_projection_without_organ", organ_id=organ_id)
        for organ_id in _duplicates(organ_authority_ids):
            _add_lifecycle_defect(defects, "duplicate_snapshot_projection", organ_id=organ_id)

        command_path_organs = {
            organ_id
            for organ_id in accepted
            if any(organ_id.replace("_", "-") in command for command in command_path)
        }
        public_lens_organs = {
            organ_id
            for organ_id in command_path_organs
            if any(_surface_mentions_organ(surface, organ_id) for surface in surface_rows)
        }
        for organ_id in sorted(command_path_organs):
            if organ_id not in public_lens_organs:
                _add_lifecycle_defect(defects, "missing_public_lens", organ_id=organ_id)
    if not authority:
        command_path_organs = set()
        public_lens_organs = set()

    for organ_id, evidence_class in sorted(evidence_class_by_id.items()):
        if evidence_class != "external_subprocess_witness":
            continue
        registry_row = registry_rows_by_id.get(organ_id, {})
        if not registry_row.get("current_authority_receipt") or not registry_row.get(
            "generated_receipts"
        ):
            _add_lifecycle_defect(
                defects,
                "external_subprocess_witness_without_tool_receipt",
                organ_id=organ_id,
            )

    coverage_counts = {
        "accepted_organ_count": len(accepted),
        "runtime_step_count": len(runtime_ids),
        "acceptance_plan_organ_count": len(accepted_plan_ids),
        "evidence_class_row_count": len(evidence_ids),
        "public_authority_expected_organ_count": len(public_authority_required_ids),
        "demoted_drilldown_organ_count": len(demoted_drilldown_ids),
        "organ_authority_row_count": len(organ_authority_ids),
        "surface_authority_row_count": len(surface_rows),
        "fixture_check_count": len(fixture_checks),
    }
    convergence = _organ_lifecycle_convergence(
        accepted=accepted,
        public_authority_required_ids=public_authority_required_ids,
        demoted_drilldown_ids=demoted_drilldown_ids,
        runtime_ids=runtime_ids,
        accepted_plan_ids=accepted_plan_ids,
        evidence_ids=evidence_ids,
        organ_authority_ids=organ_authority_ids,
        command_path_organs=command_path_organs,
        public_lens_organs=public_lens_organs,
        fixture_checks=fixture_checks,
    )
    return {
        "schema_version": "organ_lifecycle_coverage_v1",
        "status": PASS if not defects else "blocked",
        "defect_count": len(defects),
        "defects": defects,
        "accepted_order_status": accepted_order_status,
        "coverage_counts": coverage_counts,
        "organ_lifecycle_convergence": convergence,
        "checked_surfaces": [
            "core/organ_registry.json",
            ACCEPTANCE_PLAN_REL.as_posix(),
            EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
            AUTHORITY_SNAPSHOT_REL.as_posix(),
            "core/fixture_manifests/*.fixture_manifest.json",
            "fixtures/first_wave/<organ_id>/input",
        ],
        "required_invariants": [
            "accepted organ ids equal RuntimeShell.RUNTIME_STEPS ids",
            "accepted organ ids match first-wave acceptance rows",
            "accepted organ ids have exactly one evidence-class row",
            "product-spine organ ids have public authority snapshot rows",
            "demoted drilldown organs retain runtime and fixture coverage outside the product authority spine",
            "public command-path organs have a matching public lens row",
            "fixture manifests and fixture inputs exist for accepted organs",
            "external subprocess witnesses carry tool/receipt evidence refs",
        ],
        "anti_claim": (
            "Organ lifecycle coverage checks public convergence only; it does not "
            "authorize release, provider calls, source mutation, or private-data "
            "equivalence."
        ),
    }


def run_dependency_preflight(
    readiness_path: str | Path,
    negative_matrix_path: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    """
    [ACTION]
    Run the public dependency preflight and atomically write its receipt to out_path.

    - Teleology: the public entrypoint that gates the accepted runtime-spine — it proves build-dependency closure, fixture presence, wave-order, lifecycle convergence, and private-state cleanliness before any build proceeds.
    - Guarantee: returns and writes a ``dependency_preflight_receipt_v1`` dict whose ``status`` is PASS iff ``blocked_dependency_codes`` is empty; the receipt always pins ``authority_ceiling`` (release/provider/private-equivalence all False, Lean/Lake bounded-public-witness-only) and is persisted via write_json_atomic.
    - Fails: missing/malformed readiness, negative-matrix, or registry JSON -> ``read_json_strict`` raises (FileNotFound / json / value error) and propagates before any write; preflight problems otherwise surface as ``status == "blocked"`` with sorted ``blocked_dependency_codes`` (e.g. MISSING_ACCEPTED_BUILD_DEPENDENCY, MISSING_FIXTURE_INPUT, PRIVATE_STATE_SCAN_BLOCKED), not exceptions.
    - When-needed: trust when establishing whether the accepted public runtime spine is dependency/fixture/lifecycle-ready and private-state-clean for a build.
    - Escalates-to: tests/test_dependency_preflight.py + receipts/preflight/dependency_preflight.json (the written receipt at out_path).
    - Non-goal: a PASS does not authorize release, hosted operations, credentialed provider calls, secret export, financial advice, or Lean/Lake beyond the bounded public witness fixture; it asserts public preflight readiness only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    output_file = Path(out_path)
    public_root = _public_root_for_path(output_file)
    readiness_file = Path(readiness_path)
    negative_matrix_file = Path(negative_matrix_path)
    readiness = read_json_strict(readiness_file)
    negative_matrix = read_json_strict(negative_matrix_file)
    registry = _organ_registry(public_root)

    accepted = _accepted_from_registry(registry)
    readiness_by_id = {
        str(row.get("organ_id")): row for row in _rows(readiness, "organ_readiness")
    }
    blocked_codes: list[str] = []
    fixture_checks: list[dict[str, Any]] = []
    dependency_checks: list[dict[str, Any]] = []
    for organ_id in accepted:
        row = readiness_by_id.get(organ_id, {})
        public_manifest = _public_fixture_manifest(public_root, organ_id, row)
        manifest_inputs = _public_manifest_inputs(public_manifest)
        missing_deps = [
            dep
            for dep in row.get("build_dependencies", [])
            if dep not in accepted and dep not in DEFERRED_ORGAN_IDS
        ]
        if missing_deps:
            blocked_codes.append("MISSING_ACCEPTED_BUILD_DEPENDENCY")
        dependency_checks.append(
            {
                "organ_id": organ_id,
                "build_dependencies": row.get("build_dependencies", []),
                "missing_dependencies": missing_deps,
                "status": PASS if not missing_deps else "blocked",
            }
        )
        macro_fixture_inputs = [str(path) for path in row.get("fixture_inputs", [])]
        fixture_inputs = manifest_inputs or macro_fixture_inputs
        missing_inputs = [
            rel for rel in fixture_inputs if not _fixture_input_exists(public_root, rel)
        ]
        if missing_inputs:
            blocked_codes.append("MISSING_FIXTURE_INPUT")
        fixture_checks.append(
            {
                "organ_id": organ_id,
                "fixture_id": row.get("fixture_id"),
                "fixture_manifest": _display(public_manifest, public_root=public_root)
                if public_manifest.is_file()
                else None,
                "input_source": "public_fixture_manifest"
                if manifest_inputs
                else "macro_readiness_fixture_inputs",
                "macro_fixture_input_ref_count": len(macro_fixture_inputs),
                "fixture_input_count": len(fixture_inputs),
                "missing_fixture_inputs": missing_inputs,
                "status": PASS if not missing_inputs else "blocked",
            }
        )

    missing_runtime_ids = [organ_id for organ_id in accepted if organ_id not in ACCEPTED_ORGAN_IDS]
    runtime_only_ids = [organ_id for organ_id in ACCEPTED_ORGAN_IDS if organ_id not in accepted]
    wave_order_checks = {
        "status": PASS
        if not missing_runtime_ids and not runtime_only_ids
        else "blocked_wave_order_mismatch",
        "expected_runtime_ids": ACCEPTED_ORGAN_IDS,
        "observed_accepted_order": accepted,
        "accepted_without_runtime_step": missing_runtime_ids,
        "runtime_step_without_accepted_organ": runtime_only_ids,
    }
    if wave_order_checks["status"] != PASS:
        blocked_codes.append("ACCEPTED_ORGAN_ORDER_MISMATCH")

    lifecycle_coverage = _organ_lifecycle_coverage(
        public_root,
        registry,
        accepted=accepted,
        fixture_checks=fixture_checks,
    )
    if lifecycle_coverage["status"] != PASS:
        blocked_codes.append("ORGAN_LIFECYCLE_COVERAGE_DEFECT")

    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
            [readiness_file, negative_matrix_file, public_root / "core/organ_registry.json"],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    if scan["blocking_hit_count"]:
        blocked_codes.append("PRIVATE_STATE_SCAN_BLOCKED")

    blocked_codes = sorted(set(blocked_codes))
    status = PASS if not blocked_codes else "blocked"
    receipt = {
        "schema_version": "dependency_preflight_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "checked_organs": accepted,
        "toolchain_checks": {
            "python_validator_runtime": PASS,
            "lean_lake_execution": "bounded_public_witness_only",
            "provider_calls": "not_authorized",
            "trading_or_financial_advice": "not_authorized",
        },
        "fixture_precondition_checks": fixture_checks,
        "wave_order_checks": wave_order_checks,
        "organ_lifecycle_coverage": lifecycle_coverage,
        "dependency_checks": dependency_checks,
        "negative_matrix_case_count": _negative_case_count(negative_matrix),
        "blocked_dependency_count": len(blocked_codes),
        "blocked_dependency_codes": blocked_codes,
        "anti_claim": "Dependency preflight validates accepted public runtime-spine ordering and fixture presence only; it does not authorize Lean/Lake beyond the bounded public witness fixture, hosted release operations, credentialed provider calls, or secret export.",
        "private_state_scan": scan,
        "authority_ceiling": {
            "status": PASS,
            "dependency_preflight_authority": "accepted_public_runtime_spine_preflight_only",
            "lean_lake_authorized": "bounded_public_witness_only",
            "trading_or_financial_advice_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "receipt_paths": [_display(output_file, public_root=public_root)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    Build the CLI argument parser for the dependency-preflight command.

    - Teleology: defines the command-line surface (``--readiness``/``--negative-matrix``/``--out``) through which operators and CI invoke the preflight.
    - Guarantee: returns an ``ArgumentParser`` requiring all three string options; supplies the public-preflight description.
    - Fails: never raises at construction; missing required args raise ``SystemExit`` only later, at ``parse_args`` time in ``main``.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Run public dependency preflight")
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--negative-matrix", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entrypoint: parse args, run the preflight, and map its status to an exit code.

    - Teleology: the process-level adapter that lets CI/shell gate a build on the preflight verdict via exit status.
    - Guarantee: runs ``run_dependency_preflight`` with the parsed ``--readiness``/``--negative-matrix``/``--out`` and the reconstructed command string; returns ``0`` iff the receipt ``status`` is PASS, else ``1``.
    - Fails: invalid/missing CLI args raise ``SystemExit`` via argparse; missing/malformed input JSON propagates the underlying read error from run_dependency_preflight.
    - When-needed: trust as the shell/CI invocation surface; for the receipt object itself, call run_dependency_preflight directly.
    - Escalates-to: run_dependency_preflight (same module) for the full receipt and authority ceiling.
    - Non-goal: a ``0`` exit does not authorize release, provider calls, or anything beyond the bounded public preflight it ran.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.dependency_preflight "
        f"--readiness {args.readiness} --negative-matrix {args.negative_matrix} --out {args.out}"
    )
    receipt = run_dependency_preflight(
        args.readiness,
        args.negative_matrix,
        args.out,
        command=command,
    )
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
