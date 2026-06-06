from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _module_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = manifest.get("modules")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _accepted_organ_ids(root: Path) -> set[str]:
    accepted: set[str] = set()
    acceptance = _read_json(root / "core/acceptance/first_wave_acceptance.json")
    for row in acceptance.get("accepted_current_authority_organs", []):
        if (
            isinstance(row, dict)
            and row.get("status") == "accepted_current_authority"
            and row.get("organ_id")
        ):
            accepted.add(str(row["organ_id"]))
    for key in ("organs", "accepted_organs"):
        rows = acceptance.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, str) and row:
                accepted.add(row)
            elif isinstance(row, dict) and row.get("organ_id"):
                accepted.add(str(row["organ_id"]))
    return accepted


def _ledger_public_roots(root: Path, top_level: str) -> set[str]:
    ledger = _read_json(root / "core/substrate_substitution_ledger.json")
    roots: set[str] = set()
    for row in ledger.get("organ_substrate_dispositions", []):
        if not isinstance(row, dict):
            continue
        if row.get("accepted_authority") is False:
            continue
        for field in ("source_module_manifest_refs", "microcosm_target_refs"):
            refs = row.get(field)
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if not isinstance(ref, str) or not ref.startswith(f"{top_level}/"):
                    continue
                parts = PurePosixPath(ref).parts
                if top_level == "examples" and len(parts) >= 2:
                    roots.add("/".join(parts[:2]))
                elif top_level == "fixtures" and len(parts) >= 3:
                    roots.add("/".join(parts[:3]))
    return roots


def _accepted_public_roots(root: Path, top_level: str) -> set[str]:
    roots = {f"{top_level}/{organ_id}" for organ_id in _accepted_organ_ids(root)}
    roots.update(_ledger_public_roots(root, top_level))
    return roots


def _is_accepted_public_ref(ref: str, roots: set[str]) -> bool:
    return any(ref == root or ref.startswith(f"{root}/") for root in roots)


def _bundle_manifests(root: Path) -> list[Path]:
    examples_root = root / "examples"
    accepted_roots = _accepted_public_roots(root, "examples")
    if not accepted_roots:
        return []
    return sorted(
        path
        for path in examples_root.glob("*/**/source_module_manifest.json")
        if _is_accepted_public_ref(path.relative_to(root).as_posix(), accepted_roots)
    )


def _fixture_manifest_path(root: Path, organ_id: str) -> Path:
    return root / "core/fixture_manifests" / f"{organ_id}.fixture_manifest.json"


def _acceptance_receipt_path(root: Path, organ_id: str) -> Path:
    return root / "receipts/acceptance/first_wave" / f"{organ_id}_fixture_acceptance.json"


def _acceptance_entry(root: Path, organ_id: str) -> dict[str, Any]:
    acceptance = _read_json(root / "core/acceptance/first_wave_acceptance.json")
    for key in ("accepted_current_authority_organs", "organs", "accepted_organs"):
        rows = acceptance.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("organ_id") == organ_id:
                return dict(row)
            if row == organ_id:
                return {"organ_id": organ_id}
    return {}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _acceptance_import_fields(
    acceptance_entry: Mapping[str, Any],
    acceptance_receipt: Mapping[str, Any],
) -> tuple[Any, Any]:
    source_module_imports = (
        acceptance_receipt.get("source_module_imports")
        if isinstance(acceptance_receipt.get("source_module_imports"), Mapping)
        else {}
    )
    source_open_body_imports = (
        acceptance_receipt.get("source_open_body_imports")
        if isinstance(acceptance_receipt.get("source_open_body_imports"), Mapping)
        else {}
    )
    body_count = _first_present(
        acceptance_entry.get("copied_body_count"),
        acceptance_entry.get("body_copied_material_count"),
        acceptance_receipt.get("body_copied_material_count"),
        source_open_body_imports.get("body_material_count"),
        acceptance_receipt.get("source_module_count"),
        source_module_imports.get("module_count"),
    )
    manifest_status = _first_present(
        acceptance_entry.get("source_module_manifest_status"),
        acceptance_entry.get("source_manifest_status"),
        acceptance_receipt.get("source_module_manifest_status"),
        source_module_imports.get("source_module_import_status"),
        source_module_imports.get("status"),
        source_open_body_imports.get("status"),
    )
    return body_count, manifest_status


def build_partial_import_binding_report(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    rows: list[dict[str, Any]] = []
    for manifest_path in _bundle_manifests(root_path):
        manifest = _read_json(manifest_path)
        module_rows = _module_rows(manifest)
        if not module_rows:
            continue
        try:
            organ_id = manifest_path.relative_to(root_path / "examples").parts[0]
        except ValueError:
            organ_id = manifest_path.parts[-3]
        body_count = sum(1 for row in module_rows if row.get("body_copied") is True)
        aligned_count = sum(
            1
            for row in module_rows
            if row.get("sha256_match") is True
            or (
                row.get("source_sha256")
                and row.get("target_sha256")
                and row.get("source_sha256") == row.get("target_sha256")
            )
        )
        fixture_manifest = _fixture_manifest_path(root_path, organ_id)
        acceptance_receipt = _acceptance_receipt_path(root_path, organ_id)
        acceptance_entry = _acceptance_entry(root_path, organ_id)
        acceptance_receipt_payload = _read_json(acceptance_receipt)
        accepted_body_count, source_module_manifest_status = _acceptance_import_fields(
            acceptance_entry,
            acceptance_receipt_payload,
        )
        gap_codes: list[str] = []
        if body_count and not fixture_manifest.is_file():
            gap_codes.append("examples_body_present_fixture_manifest_missing")
        if body_count and accepted_body_count in (0, "0"):
            gap_codes.append("examples_body_present_acceptance_zero")
        if body_count and source_module_manifest_status == "not_present":
            gap_codes.append("examples_body_present_acceptance_manifest_not_present")
        if body_count and acceptance_receipt.is_file() and source_module_manifest_status is None:
            gap_codes.append("examples_body_present_acceptance_import_fields_missing")
        if body_count and not acceptance_receipt.is_file():
            gap_codes.append("examples_body_present_acceptance_receipt_missing")

        if "acceptance_zero" in " ".join(gap_codes) or "manifest_not_present" in " ".join(gap_codes):
            recommended_action = "bind_acceptance_to_verified_example_substrate"
        elif "fixture_manifest_missing" in " ".join(gap_codes):
            recommended_action = "add_or_migrate_fixture_manifest_for_existing_body_import"
        elif gap_codes:
            recommended_action = "inspect_and_bind"
        else:
            recommended_action = "already_bound_or_no_gap_detected"

        rows.append(
            {
                "organ_id": organ_id,
                "example_manifest_ref": str(manifest_path.relative_to(root_path)),
                "examples_body_present": body_count > 0,
                "example_body_count": body_count,
                "aligned_body_count": aligned_count,
                "fixture_manifest_present": fixture_manifest.is_file(),
                "fixture_manifest_ref": str(fixture_manifest.relative_to(root_path)),
                "acceptance_receipt_present": acceptance_receipt.is_file(),
                "acceptance_receipt_ref": str(acceptance_receipt.relative_to(root_path)),
                "acceptance_body_count": accepted_body_count,
                "source_module_manifest_status": source_module_manifest_status,
                "gap_codes": gap_codes,
                "recommended_action": recommended_action,
            }
        )

    rows.sort(key=lambda row: (0 if row["gap_codes"] else 1, row["organ_id"]))
    return {
        "schema_version": "microcosm_partial_import_binding_report_v1",
        "generated_at": utc_now(),
        "status": "pass",
        "root": ".",
        "row_count": len(rows),
        "gap_count": sum(1 for row in rows if row["gap_codes"]),
        "examples_body_present_count": sum(1 for row in rows if row["examples_body_present"]),
        "acceptance_zero_gap_count": sum(
            1 for row in rows if "examples_body_present_acceptance_zero" in row["gap_codes"]
        ),
        "fixture_manifest_gap_count": sum(
            1
            for row in rows
            if "examples_body_present_fixture_manifest_missing" in row["gap_codes"]
        ),
        "rows": rows,
        "authority_boundary": (
            "Report only. It inspects accepted public roots from acceptance "
            "or substrate-ledger authority, and does not mutate acceptance, "
            "fixtures, registries, or shared organ authority surfaces."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="microcosm import-binding-report")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    report = build_partial_import_binding_report(args.root)
    if args.out:
        write_json_atomic(Path(args.out), report)
    if args.card:
        card = {
            "schema_version": "microcosm_partial_import_binding_report_card_v1",
            "status": report["status"],
            "row_count": report["row_count"],
            "gap_count": report["gap_count"],
            "examples_body_present_count": report["examples_body_present_count"],
            "acceptance_zero_gap_count": report["acceptance_zero_gap_count"],
            "fixture_manifest_gap_count": report["fixture_manifest_gap_count"],
            "authority_boundary": report["authority_boundary"],
        }
        print(json.dumps(card, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
