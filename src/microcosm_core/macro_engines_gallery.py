"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_engines_gallery` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, RECEIPT_NAME, MICROCOSM_ROOT, REPO_ROOT, DEFAULT_OUT, ANTI_CLAIM, AUTHORITY_CEILING, DECLARED_REFACTOR_RELATIONS, ProbeRunner, PROBE_RUNNERS, run, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from microcosm_core.organs import (
    batch4_proof_authority_runtime,
    batch6_unsurfaced_primitives_capsule,
    batch7_macro_engines_capsule,
    batch9_macro_engines_capsule,
    engine_room_demo,
)
from microcosm_core.receipts import utc_now, write_json_atomic


SCHEMA_VERSION = "microcosm_macro_engines_gallery_receipt_v1"
RECEIPT_NAME = "macro_engines_gallery_receipt.json"
MICROCOSM_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = MICROCOSM_ROOT.parent
DEFAULT_OUT = MICROCOSM_ROOT / "receipts/first_wave/macro_engines_gallery"
ANTI_CLAIM = (
    "The macro engines gallery is a cold-reader composition receipt over accepted "
    "public Macro/Microcosm organs. It runs only bounded public fixtures and "
    "source-faithful exercises; it does not authorize release, publication, live "
    "provider calls, private-root equivalence, source mutation, live ledger "
    "authority, trading advice, or whole-system correctness claims."
)
AUTHORITY_CEILING = {
    "release_authorized": False,
    "publication_authorized": False,
    "hosted_public_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "private_root_equivalence_claim": False,
    "live_task_ledger_mutation_authorized": False,
    "trading_or_financial_advice_authorized": False,
    "whole_system_correctness_claim": False,
}
# Module relations whose target is a declared public-safe refactor of the
# source: custody is recorded basis-source pin + recorded target pin, never
# source==target byte equality. Any relation outside this set keeps the strict
# exact-copy three-way digest contract.
DECLARED_REFACTOR_RELATIONS = frozenset(
    {
        "public_package_body_exercised_directly",
        "source_faithful_public_refactor",
    }
)


ProbeRunner = Callable[[Path, Path], dict[str, Any]]


def _read_json(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    Load and parse one JSON file from disk as a dict.

    - Teleology: single decode helper for the registry/acceptance/manifest inputs this gallery reads.
    - Guarantee: returns the parsed JSON object for an existing UTF-8 JSON file at `path`.
    - Fails: missing file -> FileNotFoundError; malformed JSON -> json.JSONDecodeError.
    - Reads: the JSON file at `path` (registry, acceptance, or `source_module_manifest.json`).
    - Non-goal: does not validate schema, authorize source-body export, release, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    Coerce `payload[key]` into a clean list of dict rows.

    - Teleology: defensive row extractor so registry/acceptance/manifest reads tolerate missing or malformed lists.
    - Guarantee: returns only the dict elements of `payload[key]` when it is a list, else an empty list.
    - Fails: never raises; non-list or absent key -> [].
    - Non-goal: does not validate row contents, authorize source-body export, release, or correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = payload.get(key)
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _sha256(path: Path) -> str | None:
    """
    [ACTION]
    Compute the SHA-256 hex digest of a file's bytes, or None if absent.

    - Teleology: digest primitive backing the source-vs-target copied-body custody check in `_manifest_card`.
    - Guarantee: returns the lowercase hex SHA-256 of the file at `path` when it exists, else None.
    - Fails: never raises for a missing path (returns None); unreadable existing file -> OSError.
    - Reads: the raw bytes of the file at `path` (a manifest-declared source or target module).
    - Non-goal: does not compare digests, authorize source-body export, public-safe equivalence, or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    """
    [ACTION]
    Render a path as a MICROCOSM_ROOT-relative posix string for receipt refs.

    - Teleology: keep receipt path fields portable and root-relative instead of leaking absolute host paths.
    - Guarantee: returns the posix path relative to MICROCOSM_ROOT, or the bare filename when `path` is outside it.
    - Fails: never raises; non-descendant path -> path.name via the ValueError fallback.
    - Non-goal: does not authorize disclosure of absolute host roots, source-body export, or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return path.resolve(strict=False).relative_to(MICROCOSM_ROOT).as_posix()
    except ValueError:
        return path.name


def _manifest_path(organ_id: str) -> Path:
    """
    [ACTION]
    Resolve the canonical source-module-manifest path for one organ.

    - Teleology: single naming convention for where an organ's exported-bundle manifest lives.
    - Guarantee: returns the `examples/<organ_id>/exported_<organ_id>_bundle/source_module_manifest.json` path under MICROCOSM_ROOT.
    - Fails: never raises; pure path construction (the file may or may not exist).
    - Reads: nothing yet; only computes the manifest path consumed by `_manifest_card`.
    - Non-goal: does not read or validate the manifest, authorize source-body export, or release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return MICROCOSM_ROOT / f"examples/{organ_id}/exported_{organ_id}_bundle/source_module_manifest.json"


def _manifest_card(organ_id: str) -> dict[str, Any]:
    """
    [ACTION]
    Build the copied-source-body digest custody card for one organ's manifest.

    - Teleology: prove each manifest-declared copied module matches its expected SHA-256 at both source and target.
    - Guarantee: returns a card whose `digest_status` is "pass" only when every module's source, target, and source==target digest all match; "blocked" on any mismatch; "not_applicable" when the manifest is absent; never sets `body_in_receipt` true unless the manifest declared it.
    - Fails: never raises for a missing manifest (returns the not_applicable card); malformed manifest JSON -> json.JSONDecodeError via `_read_json`.
    - Reads: `examples/<organ_id>/exported_<organ_id>_bundle/source_module_manifest.json` plus each declared source (under REPO_ROOT) and target module file.
    - Escalates-to: the per-organ exported bundle manifest and the organ's own validator/receipt for full digest detail.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness; only checks declared digests.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    manifest_path = _manifest_path(organ_id)
    if not manifest_path.is_file():
        return {
            "manifest_ref": None,
            "source_module_count": 0,
            "digest_status": "not_applicable",
            "source_import_class": None,
            "body_in_receipt": False,
        }
    manifest = _read_json(manifest_path)
    modules = _rows(manifest, "modules")
    digest_rows: list[dict[str, Any]] = []
    refactored_row_count = 0
    for module in modules:
        source_ref = str(module.get("source_ref") or "")
        target_ref = str(module.get("path") or "")
        source_path = REPO_ROOT / source_ref
        target_path = manifest_path.parent / target_ref
        if not target_path.is_file():
            # Some bundles (e.g. engine_room_demo) record repo-root-relative
            # target_ref paths instead of bundle-relative `path` entries.
            alt_ref = str(module.get("target_ref") or "")
            for base, ref in (
                (REPO_ROOT, alt_ref),
                (MICROCOSM_ROOT, alt_ref),
                (REPO_ROOT, target_ref),
            ):
                if ref and (base / ref).is_file():
                    target_path = base / ref
                    break
        source_sha = _sha256(source_path)
        target_sha = _sha256(target_path)
        relation = str(module.get("source_to_target_relation") or "")
        if relation in DECLARED_REFACTOR_RELATIONS:
            # A declared refactored body never promises source==target byte
            # equality. Its custody contract is: the recorded basis source is
            # unchanged AND the refactored target matches its own recorded pin.
            refactored_row_count += 1
            expected_source = str(module.get("source_sha256") or "")
            expected_target = str(module.get("target_sha256") or "")
            digest_rows.append(
                {
                    "module_id": module.get("module_id"),
                    "relation_class": "declared_refactored_body",
                    "source_exists": source_path.is_file(),
                    "target_exists": target_path.is_file(),
                    "source_digest_match": bool(
                        expected_source and source_sha == expected_source
                    ),
                    "target_digest_match": bool(
                        expected_target and target_sha == expected_target
                    ),
                    "source_target_match": True,
                }
            )
            continue
        expected = str(module.get("sha256") or module.get("expected_sha256") or "")
        digest_rows.append(
            {
                "module_id": module.get("module_id"),
                "relation_class": "exact_copy",
                "source_exists": source_path.is_file(),
                "target_exists": target_path.is_file(),
                "source_digest_match": bool(expected and source_sha == expected),
                "target_digest_match": bool(expected and target_sha == expected),
                "source_target_match": bool(source_sha and source_sha == target_sha),
            }
        )
    all_digests_match = all(
        row["source_digest_match"] and row["target_digest_match"] and row["source_target_match"]
        for row in digest_rows
    )
    return {
        "manifest_ref": _rel(manifest_path),
        "source_module_count": manifest.get("module_count", len(modules)),
        "source_import_class": manifest.get("source_import_class"),
        "digest_status": "pass" if all_digests_match else "blocked",
        "module_digest_check_count": len(digest_rows),
        "declared_refactored_body_row_count": refactored_row_count,
        "body_in_receipt": manifest.get("body_in_receipt") is True,
    }


def _accepted_registry_rows() -> list[dict[str, Any]]:
    """
    [ACTION]
    Select the accepted macro-import organ rows in acceptance order.

    - Teleology: define the gallery's membership — accepted organs whose body is a verified copied macro import.
    - Guarantee: returns registry rows (tagged with `accepted_ordinal`) only for accepted organs that are macro-body imports (by truth-accounting bucket, evidence class, or the engine_room_demo allowance), preserving acceptance order.
    - Fails: missing/malformed `core/organ_registry.json` or `core/acceptance/first_wave_acceptance.json` -> FileNotFoundError / json.JSONDecodeError via `_read_json`.
    - Reads: `core/organ_registry.json` (implemented_organs) and `core/acceptance/first_wave_acceptance.json` (accepted_current_authority_organs).
    - Escalates-to: the organ registry and first-wave acceptance JSON as the authority for which organs are accepted.
    - Non-goal: does not re-accept organs, authorize release, or assert source equivalence beyond the registry's own classification.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    registry = _read_json(MICROCOSM_ROOT / "core/organ_registry.json")
    acceptance = _read_json(MICROCOSM_ROOT / "core/acceptance/first_wave_acceptance.json")
    accepted_order = [
        str(row.get("organ_id"))
        for row in _rows(acceptance, "accepted_current_authority_organs")
        if row.get("organ_id")
    ]
    registry_by_id = {
        str(row.get("organ_id")): row
        for row in _rows(registry, "implemented_organs")
        if row.get("organ_id")
    }
    rows: list[dict[str, Any]] = []
    for index, organ_id in enumerate(accepted_order, start=1):
        row = registry_by_id.get(organ_id)
        if not row:
            continue
        is_macro_import = (
            row.get("truth_accounting_bucket") == "copied_non_secret_macro_body"
            or row.get("evidence_class") == "verified_macro_body_import"
            or organ_id == "engine_room_demo"
        )
        if not is_macro_import:
            continue
        rows.append({"accepted_ordinal": index, **row})
    return rows


def _gallery_card(row: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Project one accepted organ row into a public-safe gallery card.

    - Teleology: render each accepted macro organ as a cold-reader card carrying its claim ceiling and digest custody.
    - Guarantee: returns a card echoing the row's evidence class, truth-accounting bucket, authority receipt, validator command, and claim ceiling, embedding the manifest digest card, with release/publication/private-root-equivalence pinned False.
    - Fails: missing manifest is absorbed by `_manifest_card`; malformed manifest JSON -> json.JSONDecodeError.
    - Reads: the organ's `source_module_manifest.json` (transitively, via `_manifest_card`).
    - Non-goal: does not authorize release, publication, or private-root equivalence — those fields are hardcoded False.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    organ_id = str(row.get("organ_id") or "")
    manifest = _manifest_card(organ_id)
    return {
        "accepted_ordinal": row.get("accepted_ordinal"),
        "organ_id": organ_id,
        "evidence_class": row.get("evidence_class"),
        "truth_accounting_bucket": row.get("truth_accounting_bucket"),
        "current_authority_receipt": row.get("current_authority_receipt"),
        "validator_command": row.get("validator_command"),
        "claim_ceiling": row.get("claim_ceiling"),
        "classification_basis": row.get("classification_basis"),
        "source_module_manifest": manifest,
        "release_authorized": False,
        "publication_authorized": False,
        "private_root_equivalence_claim": False,
    }


def _run_batch4(input_root: Path, out_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    Run the batch4 proof-authority-runtime organ as a gallery probe.

    - Teleology: adapt the batch4 organ to the gallery's `(input_root, out_dir) -> result` probe contract.
    - Guarantee: delegates to `batch4_proof_authority_runtime.run` with the gallery command tag and returns its result dict.
    - Fails: propagates whatever the underlying organ raises; status/error are carried in the returned dict's `status`/`error_codes`.
    - When-needed: when batch4 is among the discovered accepted organs and is selected as the earlier-macro probe.
    - Escalates-to: `microcosm_core.organs.batch4_proof_authority_runtime` and its own receipt for full probe detail.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return batch4_proof_authority_runtime.run(input_root, out_dir, command="microcosm macro-engines-gallery run")


def _run_batch6(input_root: Path, out_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    Run the batch6 unsurfaced-primitives-capsule organ as a gallery probe.

    - Teleology: adapt the batch6 organ to the gallery's `(input_root, out_dir) -> result` probe contract.
    - Guarantee: delegates to `batch6_unsurfaced_primitives_capsule.run` with the gallery command tag and returns its result dict.
    - Fails: propagates whatever the underlying organ raises; status/error are carried in the returned dict's `status`/`error_codes`.
    - When-needed: when batch6 is among the discovered accepted organs and is selected as the earlier-macro probe.
    - Escalates-to: `microcosm_core.organs.batch6_unsurfaced_primitives_capsule` and its own receipt for full probe detail.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return batch6_unsurfaced_primitives_capsule.run(input_root, out_dir, command="microcosm macro-engines-gallery run")


def _run_batch7(input_root: Path, out_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    Run the batch7 macro-engines-capsule bundle as a mandatory gallery probe.

    - Teleology: adapt the batch7 capsule's bundle runner to the gallery's probe contract; batch7 is a required probe for a `pass`.
    - Guarantee: delegates to `batch7_macro_engines_capsule.run_batch7_bundle` with the gallery command tag and returns its result dict.
    - Fails: propagates whatever the underlying organ raises; status/error are carried in the returned dict's `status`/`error_codes`.
    - When-needed: always selected when discovered; its `pass` status gates the gallery's overall status.
    - Escalates-to: `microcosm_core.organs.batch7_macro_engines_capsule` and its own receipt for full probe detail.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return batch7_macro_engines_capsule.run_batch7_bundle(
        input_root,
        out_dir,
        command="microcosm macro-engines-gallery run",
    )


def _run_batch9(input_root: Path, out_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    Run the batch9 macro-engines-capsule organ as a mandatory gallery probe.

    - Teleology: adapt the batch9 capsule to the gallery's probe contract; batch9 is a required probe for a `pass`.
    - Guarantee: delegates to `batch9_macro_engines_capsule.run` with the gallery command tag and returns its result dict.
    - Fails: propagates whatever the underlying organ raises; status/error are carried in the returned dict's `status`/`error_codes`.
    - When-needed: always selected when discovered; its `pass` status gates the gallery's overall status.
    - Escalates-to: `microcosm_core.organs.batch9_macro_engines_capsule` and its own receipt for full probe detail.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return batch9_macro_engines_capsule.run(input_root, out_dir, command="microcosm macro-engines-gallery run")


def _run_engine_room(input_root: Path, out_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    Run the engine-room-demo organ over a synthesized positive+negative fixture pair.

    - Teleology: exercise the engine-room organ with one bounded positive case and one missing-target negative case so the gallery shows a real negative-detection probe.
    - Guarantee: writes two synthetic case files into a temp dir, calls `engine_room_demo.run` with the gallery command tag, and returns its result dict; `input_root` is unused (the synthesized cases replace it).
    - Fails: propagates whatever the underlying organ raises; the temp fixture dir is always cleaned up; status/error are carried in the returned dict's `status`/`error_codes`.
    - Writes: ephemeral `positive_controller_audit.json` and `missing_expected_target_negative.json` in a TemporaryDirectory (deleted on exit).
    - When-needed: when engine_room_demo is the discovered earlier-macro probe; demonstrates negative-case observation.
    - Escalates-to: `microcosm_core.organs.engine_room_demo` and its own receipt for full probe detail.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    """
    with tempfile.TemporaryDirectory(prefix="microcosm-gallery-engine-room-") as fixture_dir:
        gallery_input = Path(fixture_dir)
        (gallery_input / "positive_controller_audit.json").write_text(
            json.dumps(
                {
                    "case_id": "positive_controller_audit",
                    "case_type": "positive",
                    "run_exercises": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (gallery_input / "missing_expected_target_negative.json").write_text(
            json.dumps(
                {
                    "case_id": "missing_expected_target_negative",
                    "case_type": "negative",
                    "expected_jewel_targets": [
                        "lean_and_or_proof_search",
                        "engine_room_target_that_should_not_exist",
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return engine_room_demo.run(
            gallery_input,
            out_dir,
            command="microcosm macro-engines-gallery run",
        )


PROBE_RUNNERS: dict[str, tuple[str, ProbeRunner]] = {
    "batch4_proof_authority_runtime": (
        "fixtures/first_wave/batch4_proof_authority_runtime/input",
        _run_batch4,
    ),
    "batch6_unsurfaced_primitives_capsule": (
        "fixtures/first_wave/batch6_unsurfaced_primitives_capsule/input",
        _run_batch6,
    ),
    "batch7_macro_engines_capsule": (
        "examples/batch7_macro_engines_capsule/exported_batch7_macro_engines_capsule_bundle",
        _run_batch7,
    ),
    "batch9_macro_engines_capsule": (
        "fixtures/first_wave/batch9_macro_engines_capsule/input",
        _run_batch9,
    ),
    "engine_room_demo": (
        "fixtures/first_wave/engine_room_demo/input",
        _run_engine_room,
    ),
}


def _select_probe_ids(cards: list[dict[str, Any]]) -> list[str]:
    """
    [ACTION]
    Choose which discovered organs to actually run as live probes.

    - Teleology: always probe batch7 and batch9, plus the first available earlier-macro organ, to keep the gallery run bounded.
    - Guarantee: returns an ordered id list starting with batch7 then batch9, plus at most one earlier-macro organ (engine_room/batch6/batch4 by preference), filtered to ids that are both discovered and have a registered runner.
    - Fails: never raises; returns only ids present in both `cards` and PROBE_RUNNERS.
    - Reads: the `organ_id` field of each gallery card and the PROBE_RUNNERS registry keys.
    - Non-goal: does not run probes or assert their pass; only selects ids for `run` to execute.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    discovered = {str(card.get("organ_id")) for card in cards}
    probe_ids = ["batch7_macro_engines_capsule", "batch9_macro_engines_capsule"]
    for preferred in (
        "engine_room_demo",
        "batch6_unsurfaced_primitives_capsule",
        "batch4_proof_authority_runtime",
    ):
        if preferred in discovered:
            probe_ids.append(preferred)
            break
    return [organ_id for organ_id in probe_ids if organ_id in discovered and organ_id in PROBE_RUNNERS]


def _probe_card(organ_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Normalize one organ's raw run result into a compact gallery probe card.

    - Teleology: distill heterogeneous organ run results into a uniform probe summary (status, source digests, negatives, receipts).
    - Guarantee: returns a card with the organ's status, derived source-module status/count, sorted evidence classes, observed and missing negative cases, error codes, anti-claim, and receipt-ref count; `source_module_status` is "pass" only when the result's manifest reports all digests matched and all anchors present.
    - Fails: never raises; missing or wrong-typed result fields default to empty lists / passthrough values.
    - Reads: only the in-memory `result` dict returned by a probe runner (no disk access).
    - Non-goal: does not run the organ, recompute digests, authorize release, or assert whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    manifest = result.get("source_module_manifest")
    manifest = manifest if isinstance(manifest, dict) else {}
    mechanisms = _rows(result.get("exercise", {}) if isinstance(result.get("exercise"), dict) else {}, "mechanisms")
    observed_negative_cases = result.get("observed_negative_cases")
    observed_negative_cases = observed_negative_cases if isinstance(observed_negative_cases, list) else []
    observed_negative_case_count = result.get("observed_negative_case_count")
    if not isinstance(observed_negative_case_count, int):
        observed_negative_case_count = len(observed_negative_cases)
    missing_negative_cases = result.get("missing_negative_cases")
    missing_negative_cases = missing_negative_cases if isinstance(missing_negative_cases, list) else []
    receipt_paths = result.get("receipt_paths")
    receipt_paths = receipt_paths if isinstance(receipt_paths, list) else []
    return {
        "organ_id": organ_id,
        "status": result.get("status"),
        "source_module_count": manifest.get("module_count") or result.get("source_module_count"),
        "source_module_status": "pass"
        if manifest.get("all_expected_digests_matched") is True
        and manifest.get("all_required_anchors_present") is True
        else result.get("source_module_status"),
        "evidence_classes": sorted(
            {
                str(row.get("evidence_class"))
                for row in mechanisms
                if row.get("evidence_class")
            }
        ),
        "observed_negative_case_count": observed_negative_case_count,
        "observed_negative_cases": observed_negative_cases,
        "missing_negative_cases": missing_negative_cases,
        "error_codes": result.get("error_codes", []),
        "anti_claim": result.get("anti_claim"),
        "body_in_receipt": result.get("body_in_receipt") is True,
        "receipt_ref_count": len(receipt_paths),
    }


def run(out_dir: str | Path = DEFAULT_OUT, *, command: str = "microcosm macro-engines-gallery run") -> dict[str, Any]:
    """
    [ACTION]
    Compose the macro-engines gallery: build cards, run probes, and write the receipt.

    - Teleology: the gallery's organ entrypoint — assemble accepted macro organs into one cold-reader composition receipt with embedded digest custody and live probe results.
    - Guarantee: writes a `macro_engines_gallery_receipt_v1` receipt to `<out_dir>/macro_engines_gallery_receipt.json` and returns the payload; `status` is "pass" only when there are cards, batch7 and batch9 both probed, at least 3 probes, every probe passed, and no probe has missing negative cases — otherwise "blocked"; always pins the AUTHORITY_CEILING and ANTI_CLAIM and sets `body_in_receipt` False.
    - Fails: missing/malformed registry, acceptance, or manifest inputs -> FileNotFoundError / json.JSONDecodeError; otherwise degrades to a "blocked" payload rather than raising.
    - Reads: accepted organ registry, first-wave acceptance, per-organ source-module manifests, and each selected organ's fixture input under MICROCOSM_ROOT.
    - Writes: the gallery receipt at `<out_dir>/macro_engines_gallery_receipt.json` plus per-organ probe receipts under `<out_dir>/organs/<organ_id>`.
    - When-needed: run to regenerate the gallery composition receipt or to verify accepted macro organs still probe green and digests are unbroken.
    - Escalates-to: the per-organ validators/receipts and the organ registry / acceptance JSON as the higher-fidelity authority behind this projection.
    - Non-goal: does not authorize release, publication, provider calls, source mutation, private-root equivalence, or whole-system correctness — those stay False in AUTHORITY_CEILING.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    gallery_cards = [_gallery_card(row) for row in _accepted_registry_rows()]
    probe_ids = _select_probe_ids(gallery_cards)
    probes: list[dict[str, Any]] = []
    for organ_id in probe_ids:
        input_ref, runner = PROBE_RUNNERS[organ_id]
        result = runner(MICROCOSM_ROOT / input_ref, out_path / "organs" / organ_id)
        probes.append(_probe_card(organ_id, result))

    negative_case_summary = {
        row["organ_id"]: {
            "observed_negative_case_count": row["observed_negative_case_count"],
            "missing_negative_cases": row["missing_negative_cases"],
        }
        for row in probes
    }
    receipt_path = out_path / RECEIPT_NAME
    digest_statuses = [
        (card.get("source_module_manifest") or {}).get("digest_status")
        for card in gallery_cards
    ]
    digest_blocked_count = len([status for status in digest_statuses if status == "blocked"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "command": command,
        "status": "pass"
        if gallery_cards
        and "batch7_macro_engines_capsule" in probe_ids
        and "batch9_macro_engines_capsule" in probe_ids
        and len(probe_ids) >= 3
        and all(row["status"] == "pass" for row in probes)
        and all(not row["missing_negative_cases"] for row in probes)
        else "blocked",
        "gallery_card_count": len(gallery_cards),
        "gallery_cards": gallery_cards,
        "probe_count": len(probes),
        "probe_ids": probe_ids,
        "probes": probes,
        "negative_case_summary": negative_case_summary,
        "batch7_visible": any(card.get("organ_id") == "batch7_macro_engines_capsule" for card in gallery_cards),
        "batch9_visible": any(card.get("organ_id") == "batch9_macro_engines_capsule" for card in gallery_cards),
        "earlier_macro_probe_visible": any(
            row.get("organ_id") not in {"batch7_macro_engines_capsule", "batch9_macro_engines_capsule"}
            for row in probes
        ),
        "copied_source_digest_status": "pass"
        if digest_blocked_count == 0
        else "mixed_historical_drift",
        "copied_source_digest_summary": {
            "pass_count": len([status for status in digest_statuses if status == "pass"]),
            "blocked_count": digest_blocked_count,
            "not_applicable_count": len(
                [status for status in digest_statuses if status == "not_applicable"]
            ),
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "receipt_ref": _rel(receipt_path),
    }
    write_json_atomic(receipt_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entry: run the macro engines gallery composition and emit its receipt.

    - Teleology: give the cold-reader macro-engines composition receipt a runnable `run` front door.
    - Guarantee: prints the gallery receipt JSON and returns 0 when status is `pass`, 1 when `blocked`.
    - Fails: missing subcommand -> argparse error (exit 2); blocked probe/digest gallery -> exit 1.
    - Reads: accepted organ registry, acceptance, and example manifests under MICROCOSM_ROOT plus per-organ fixture inputs.
    - Writes: the gallery receipt (and per-organ probe receipts) under `--out`.
    - When-needed: invoked from the shell or test harness, not from library code (call `run()` directly there).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    parser = argparse.ArgumentParser(prog="microcosm macro-engines-gallery")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    if args.action == "run":
        payload = run(args.out)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("status") == "pass" else 1
    parser.error("expected subcommand: run")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
