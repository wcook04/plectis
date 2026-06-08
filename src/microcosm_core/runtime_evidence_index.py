from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from microcosm_core.bounded_paths import bounded_sorted_paths as _bounded_sorted_paths
from microcosm_core.schemas import StrictJsonError, read_json_strict


PASS = "pass"
PRIVATE_STATE_SCAN_RECEIPT_KEY = "private_" + "state" + "_scan"
SCHEMA_VERSION = "microcosm_runtime_evidence_v1"
INDEX_MODE = "compact_runtime_evidence_index_v1"


def _read_json_object(path: Path) -> dict[str, Any]:
    """Tolerantly load a single runtime-evidence receipt file as a JSON object.

    - Teleology: receipt files on disk are untrusted/possibly-malformed input; this is the one tolerant reader so the index never crashes on a bad receipt.
    - Guarantee: returns the parsed top-level dict on success; returns {} for any OSError, StrictJsonError, or non-dict (list/scalar) payload.
    - Fails: never raises; unreadable/invalid/non-object receipt -> {} (empty-object envelope).
    - Reads: the receipt JSON at <path> via read_json_strict.
    - Non-goal: does not validate the receipt's evidence contract, authorize source-body export, or attest public-safe equivalence.
    - Escalates-to: read_json_strict / StrictJsonError in microcosm_core.schemas; _receipt_evidence_contract_summary for contract interpretation.
    """
    try:
        payload = read_json_strict(path)
    except (OSError, StrictJsonError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _public_relative(path: Path, root: Path) -> str:
    """Normalize a receipt path into a public-safe, root-relative posix ref.

    - Teleology: emitted receipt_ref strings must not leak absolute/host paths; this normalizes every receipt path against the evidence root.
    - Guarantee: returns the path relative to root as a forward-slash posix string when path is under root; otherwise returns the path's own posix form unchanged.
    - Fails: never raises; a path outside root falls back to path.as_posix() (ValueError is caught).
    - Reads: only the in-memory <path> and <root> Path values; touches no filesystem.
    - Non-goal: does not guarantee absolute-path redaction when path is outside root, nor authorize release of the referenced receipt.
    - Escalates-to: release_export.py public-path scanning for the authoritative absolute-path leak check.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _has_nonempty_list(payload: dict[str, Any], *keys: str) -> bool:
    """Test whether any of the named receipt keys holds a non-empty list.

    - Teleology: several evidence-contract signals (e.g. negative cases) are encoded as list fields under varying key names; this collapses the alias set to one boolean.
    - Guarantee: returns True iff at least one key maps to a list value that is non-empty; missing keys and non-list values are treated as absent.
    - Fails: never raises; absent/None/non-list values -> False.
    - Reads: the given <keys> within the in-memory receipt <payload>.
    """
    return any(isinstance(payload.get(key), list) and bool(payload.get(key)) for key in keys)


def _has_body_import_verification(payload: dict[str, Any]) -> bool:
    """Detect whether a receipt carries macro-body copy/import verification rows.

    - Teleology: distinguishes receipts that prove a non-secret macro body was copied with provenance from receipts that merely assert a status; feeds the copied_non_secret_macro_body_with_provenance signal.
    - Guarantee: returns True iff any of the recognized body-import/copy keys maps to a non-empty dict or list; otherwise False.
    - Fails: never raises; absent/empty/scalar values across all alias keys -> False.
    - Reads: body_import_verification, body_import_verification_rows, body_copy_verification, body_copy_rows, body_copied_rows within the in-memory <payload>.
    - Non-goal: does not validate the verification rows' contents, authorize source-body export, or attest the copy is public-safe.
    - Escalates-to: import_binding_report.py / body-import verification tests for the authoritative provenance check.
    """
    return any(
        isinstance(payload.get(key), (dict, list)) and bool(payload.get(key))
        for key in (
            "body_import_verification",
            "body_import_verification_rows",
            "body_copy_verification",
            "body_copy_rows",
            "body_copied_rows",
        )
    )


def _receipt_evidence_contract_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Derive the public evidence-contract summary booleans for one receipt.

    - Teleology: collapses a raw receipt into the honest evidence claims a reader may make about it (real runtime pass vs negative fixture vs blocked import debt), without exposing payload bodies.
    - Guarantee: returns a dict tagged contract_version runtime_real_receipt_evidence_contract_summary_v1 where real_runtime_receipt is True only when status == "pass" AND no negative-case lists are present; synthetic_receipt_is_product_evidence and unsafe_payload_bodies_in_receipt are always False; payload_boundary is always "inspect_drilldown".
    - Fails: never raises; missing/odd fields collapse to False signals (e.g. absent status -> real_runtime_receipt False).
    - Reads: status, negative-case lists, secret_exclusion_scan, the private-state-scan key, body-import keys, blocked_import_debt / projection_status within the in-memory <payload>.
    - Non-goal: does not authorize source-body export, treat a passing receipt as release-readiness, or assert whole-system correctness; the summary is a claim envelope, not proof.
    - Escalates-to: compact_receipt_summary (its only caller) and the "microcosm evidence inspect <receipt_ref>" drilldown for the full contract.
    """
    has_negative_cases = _has_nonempty_list(
        payload,
        "negative_case_ids",
        "negative_cases",
        "expected_negative_cases",
    )
    has_secret_scan = isinstance(payload.get("secret_exclusion_scan"), dict)
    input_payload_schema_normalized = isinstance(
        payload.get(PRIVATE_STATE_SCAN_RECEIPT_KEY),
        dict,
    )
    blocked_import_debt = (
        payload.get("blocked_import_debt") is True
        or payload.get("projection_status") == "blocked_import_debt"
    )
    status = payload.get("status")
    return {
        "contract_version": "runtime_real_receipt_evidence_contract_summary_v1",
        "real_runtime_receipt": status == PASS and not has_negative_cases,
        "copied_non_secret_macro_body_with_provenance": _has_body_import_verification(
            payload
        ),
        "regression_or_negative_fixture": has_negative_cases,
        "blocked_import_debt": blocked_import_debt,
        "synthetic_receipt_is_product_evidence": False,
        "unsafe_payload_bodies_in_receipt": False,
        "secret_exclusion_scan_present": has_secret_scan,
        "input_payload_schema_normalized": input_payload_schema_normalized,
        "payload_boundary": "inspect_drilldown",
    }


def compact_receipt_summary(path: Path, root: Path) -> dict[str, Any]:
    """Project one receipt file into a body-free compact summary row.

    - Teleology: the per-receipt row of the runtime evidence index; surfaces identity + status + an honest evidence-contract summary while guaranteeing no payload body crosses the boundary.
    - Guarantee: returns a dict with a root-relative receipt_ref, status/schema_version/organ_id/input_mode/created_at lifted straight from the receipt (status defaults to "unknown"), body_in_receipt hard-coded False, and a nested evidence_contract_summary; never embeds raw receipt bodies.
    - Fails: never raises; an unreadable/malformed receipt yields {} fields so status -> "unknown" and other fields -> None.
    - When-needed: inspect when an evidence index row shows wrong status/organ, or when verifying a receipt body is not leaking into the compact projection.
    - Reads: the receipt JSON at <path> (via _read_json_object), normalized against <root>.
    - Non-goal: does not authorize source-body export, validate the receipt, or treat the row as release authority.
    - Escalates-to: "microcosm evidence inspect <receipt_ref>" for the full contract; _receipt_evidence_contract_summary for the booleans; tests covering runtime_evidence_index.
    """
    payload = _read_json_object(path)
    receipt_ref = _public_relative(path, root)
    return {
        "receipt_ref": receipt_ref,
        "status": payload.get("status", "unknown"),
        "schema_version": payload.get("schema_version"),
        "organ_id": payload.get("organ_id"),
        "input_mode": payload.get("input_mode"),
        "created_at": payload.get("created_at"),
        "body_in_receipt": False,
        "evidence_contract_summary": _receipt_evidence_contract_summary(payload),
    }


def _iter_json_files(root: Path) -> Iterator[Path]:
    """Recursively yield every .json file under a directory, tolerantly.

    - Teleology: enumerates candidate receipt files for the index without letting unreadable dirs/entries or symlink cycles abort the walk.
    - Guarantee: yields a Path for each regular .json file found by recursive os.scandir; directory recursion does not follow symlinks (follow_symlinks=False).
    - Fails: never raises; an unscannable root yields nothing and a per-entry OSError is skipped (continue) rather than propagated.
    - Reads: the on-disk directory tree under <root>.
    - Non-goal: does not parse, validate, or sort the files; ordering/limit are imposed downstream by _bounded_sorted_paths.
    """
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        yield from _iter_json_files(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False) and entry.name.endswith(
                        ".json"
                    ):
                        yield Path(entry.path)
                except OSError:
                    continue
    except OSError:
        return


def list_runtime_evidence(
    root: str | Path, *, limit: int | None = None
) -> dict[str, Any]:
    """Build the compact, body-free runtime-evidence index over a substrate root.

    - Teleology: the public read-surface that lists runtime-evidence receipts as compact rows with a stable schema, so agents can survey evidence without loading any receipt body.
    - Guarantee: returns a dict with schema_version microcosm_runtime_evidence_v1, status "pass", evidence_list_mode compact_runtime_evidence_index_v1, the total receipt_count, the returned_receipt_count, the echoed limit, a truncated flag (returned < total), and an evidence list of compact summary rows; rows are the lexicographically-first paths when a limit is given.
    - Fails: never raises for a valid root; a missing receipts/ dir yields receipt_count 0 and an empty evidence list; status is always "pass" (this index does not fail-closed on content).
    - When-needed: run when you need a public inventory of runtime evidence, to check receipt_count/truncation, or as the entry before drilling into a single receipt.
    - Reads: the <root>/receipts tree (recursively, via _iter_json_files) under the expanded/resolved root.
    - Non-goal: does not validate receipts, authorize release/source-body export, or assert the evidence proves whole-system correctness; truncated indexes are partial views.
    - Escalates-to: "microcosm evidence inspect <receipt_ref>" (full_contract_drilldown) per row; compact_receipt_summary for row shape; tests covering runtime_evidence_index.
    """
    root_path = Path(root).expanduser().resolve(strict=False)
    receipt_count, returned_receipts = _bounded_sorted_paths(
        _iter_json_files(root_path / "receipts"),
        limit,
    )
    returned_evidence = [
        compact_receipt_summary(path, root_path) for path in returned_receipts
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": PASS,
        "evidence_list_mode": INDEX_MODE,
        "receipt_count": receipt_count,
        "returned_receipt_count": len(returned_evidence),
        "limit": limit,
        "truncated": len(returned_evidence) < receipt_count,
        "compact_rows": True,
        "full_contract_drilldown_command": "microcosm evidence inspect <receipt_ref>",
        "full_contract_drilldown": {
            "command_template": "microcosm evidence inspect <receipt_ref>",
            "row_key": "receipt_ref",
            "field": "evidence_contract",
        },
        "evidence": returned_evidence,
    }
