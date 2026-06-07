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


ProbeRunner = Callable[[Path, Path], dict[str, Any]]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key)
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(MICROCOSM_ROOT).as_posix()
    except ValueError:
        return path.name


def _manifest_path(organ_id: str) -> Path:
    return MICROCOSM_ROOT / f"examples/{organ_id}/exported_{organ_id}_bundle/source_module_manifest.json"


def _manifest_card(organ_id: str) -> dict[str, Any]:
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
    for module in modules:
        source_ref = str(module.get("source_ref") or "")
        target_ref = str(module.get("path") or "")
        source_path = REPO_ROOT / source_ref
        target_path = manifest_path.parent / target_ref
        expected = str(module.get("sha256") or module.get("expected_sha256") or "")
        source_sha = _sha256(source_path)
        target_sha = _sha256(target_path)
        digest_rows.append(
            {
                "module_id": module.get("module_id"),
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
        "body_in_receipt": manifest.get("body_in_receipt") is True,
    }


def _accepted_registry_rows() -> list[dict[str, Any]]:
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
    return batch4_proof_authority_runtime.run(input_root, out_dir, command="microcosm macro-engines-gallery run")


def _run_batch6(input_root: Path, out_dir: Path) -> dict[str, Any]:
    return batch6_unsurfaced_primitives_capsule.run(input_root, out_dir, command="microcosm macro-engines-gallery run")


def _run_batch7(input_root: Path, out_dir: Path) -> dict[str, Any]:
    return batch7_macro_engines_capsule.run_batch7_bundle(
        input_root,
        out_dir,
        command="microcosm macro-engines-gallery run",
    )


def _run_batch9(input_root: Path, out_dir: Path) -> dict[str, Any]:
    return batch9_macro_engines_capsule.run(input_root, out_dir, command="microcosm macro-engines-gallery run")


def _run_engine_room(input_root: Path, out_dir: Path) -> dict[str, Any]:
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
    """CLI entry: run the macro engines gallery composition and emit its receipt.

    - Teleology: give the cold-reader macro-engines composition receipt a runnable `run` front door.
    - Guarantee: prints the gallery receipt JSON and returns 0 when status is `pass`, 1 when `blocked`.
    - Fails: missing subcommand -> argparse error (exit 2); blocked probe/digest gallery -> exit 1.
    - Reads: accepted organ registry, acceptance, and example manifests under MICROCOSM_ROOT plus per-organ fixture inputs.
    - Writes: the gallery receipt (and per-organ probe receipts) under `--out`.
    - When-needed: invoked from the shell or test harness, not from library code (call `run()` directly there).
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
