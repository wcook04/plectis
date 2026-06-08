from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


def _read_json(path: Path) -> dict[str, Any]:
    """Read one JSON file as a dict, tolerating absence and non-object payloads.

    - Teleology: single tolerant reader so every acceptance/ledger/manifest/receipt lookup degrades to an empty dict instead of crashing the report.
    - Guarantee: returns the parsed object when `path` is a file containing a JSON object; returns `{}` when the file is missing or the top-level JSON is not an object.
    - Fails: propagates `read_json_strict` parse errors when the file exists but holds malformed JSON; never raises for a missing path.
    - Reads: the exact `path` passed in (read-only).
    - Non-goal: does not validate schema, authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    """
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _module_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Extract the per-module dict rows from a source-module manifest.

    - Teleology: normalize a manifest's `modules` field into a clean list of dict rows for body/digest counting downstream.
    - Guarantee: returns every dict element of `manifest["modules"]`; returns `[]` when `modules` is absent or not a list.
    - Fails: never raises; non-dict entries and missing keys are silently dropped.
    - Reads: the in-memory `manifest` mapping's `modules` key (no filesystem access).
    - Non-goal: does not validate module-row contents, authorize source-body export, equivalence, or release.
    """
    rows = manifest.get("modules")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _accepted_organ_ids(root: Path) -> set[str]:
    """Collect organ ids holding current acceptance authority from the first-wave acceptance file.

    - Teleology: derive the authoritative set of accepted organ ids that gates which example roots the report is allowed to inspect.
    - Guarantee: returns the union of `organ_id`s under `accepted_current_authority_organs` (status `accepted_current_authority`) plus any string/dict ids under `organs`/`accepted_organs`; returns an empty set when the acceptance file is missing or holds none.
    - Fails: never raises; rows lacking the required status or `organ_id` are skipped.
    - Reads: `<root>/core/acceptance/first_wave_acceptance.json` (read-only).
    - Non-goal: does not grant acceptance, mutate the acceptance file, or authorize source-body export, equivalence, or release.
    """
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
    """Derive accepted public path roots under `top_level` from the substrate substitution ledger.

    - Teleology: extend the accepted-roots set with paths the substitution ledger marks as accepted authority, so ledger-only bindings are still inspectable.
    - Guarantee: returns the set of `top_level/...` path roots (depth 2 for `examples`, depth 3 for `fixtures`) drawn from `source_module_manifest_refs`/`microcosm_target_refs` of dispositions whose `accepted_authority` is not `False`; returns an empty set when the ledger is missing or has no qualifying refs.
    - Fails: never raises; rows that are not dicts, are explicitly rejected, or whose refs do not start with `top_level/` are skipped.
    - Reads: `<root>/core/substrate_substitution_ledger.json` (read-only).
    - Non-goal: does not mutate the ledger, refresh digests, or authorize source-body export, equivalence, or release.
    """
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
    """Union acceptance-derived and ledger-derived public roots under `top_level`.

    - Teleology: produce the single accepted-roots allowlist that bounds which manifests the report may read.
    - Guarantee: returns `{top_level/<organ_id>}` for every accepted organ id merged with `_ledger_public_roots(root, top_level)`; returns an empty set when neither source yields a root.
    - Fails: never raises; inherits the tolerant read behavior of both source helpers.
    - Reads: `<root>/core/acceptance/first_wave_acceptance.json` and `<root>/core/substrate_substitution_ledger.json` (read-only).
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond accepted-root membership, or release.
    """
    roots = {f"{top_level}/{organ_id}" for organ_id in _accepted_organ_ids(root)}
    roots.update(_ledger_public_roots(root, top_level))
    return roots


def _is_accepted_public_ref(ref: str, roots: set[str]) -> bool:
    """Test whether a path ref is at or beneath any accepted public root.

    - Teleology: the membership gate that keeps the report's manifest scan inside accepted-authority roots only.
    - Guarantee: returns `True` iff `ref` equals some root in `roots` or begins with `root + "/"`; otherwise `False`.
    - Fails: never raises; an empty `roots` set always yields `False`.
    - Reads: only the in-memory `ref` string and `roots` set (no filesystem access).
    - Non-goal: does not normalize or validate the path, authorize export, equivalence, or release.
    """
    return any(ref == root or ref.startswith(f"{root}/") for root in roots)


def _bundle_manifests(root: Path) -> list[Path]:
    """List accepted example source-module manifests under the examples tree.

    - Teleology: enumerate exactly the `source_module_manifest.json` files inside accepted example roots that the report will analyze.
    - Guarantee: returns a sorted list of `examples/**/source_module_manifest.json` paths whose repo-relative ref passes the accepted-roots gate; returns `[]` when no example roots are accepted.
    - Fails: never raises; non-accepted manifests are filtered out before return.
    - Reads: globs `<root>/examples/*/**/source_module_manifest.json`, gated by acceptance + ledger roots (read-only).
    - Non-goal: does not read manifest bodies, authorize source-body export, equivalence, or release.
    """
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
    """Compute the expected fixture-manifest path for an organ.

    - Teleology: single source of the fixture-manifest path convention so presence checks and refs stay consistent.
    - Guarantee: returns `<root>/core/fixture_manifests/<organ_id>.fixture_manifest.json` (path object; not checked for existence here).
    - Fails: never raises; performs pure path construction.
    - Reads: nothing from disk.
    - Non-goal: does not read or validate the manifest, authorize export, equivalence, or release.
    """
    return root / "core/fixture_manifests" / f"{organ_id}.fixture_manifest.json"


def _acceptance_receipt_path(root: Path, organ_id: str) -> Path:
    """Compute the expected first-wave acceptance-receipt path for an organ.

    - Teleology: single source of the acceptance-receipt path convention so presence checks and refs stay consistent.
    - Guarantee: returns `<root>/receipts/acceptance/first_wave/<organ_id>_fixture_acceptance.json` (path object; not checked for existence here).
    - Fails: never raises; performs pure path construction.
    - Reads: nothing from disk.
    - Non-goal: does not read or validate the receipt, authorize export, equivalence, or release.
    """
    return root / "receipts/acceptance/first_wave" / f"{organ_id}_fixture_acceptance.json"


def _acceptance_entry(root: Path, organ_id: str) -> dict[str, Any]:
    """Fetch the acceptance row for one organ from the first-wave acceptance file.

    - Teleology: locate the per-organ acceptance record that supplies the report's accepted body-count and manifest-status fields.
    - Guarantee: returns the matching dict row (copied) for `organ_id` across `accepted_current_authority_organs`/`organs`/`accepted_organs`; returns `{"organ_id": organ_id}` for a bare string match and `{}` when no entry exists.
    - Fails: never raises; non-list sections and non-matching rows are skipped.
    - Reads: `<root>/core/acceptance/first_wave_acceptance.json` (read-only).
    - Non-goal: does not grant acceptance, mutate the file, or authorize export, equivalence, or release.
    """
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
    """Return the first non-None argument, preserving fallback order.

    - Teleology: coalesce ordered field candidates so acceptance entry/receipt sources are tried in priority order.
    - Guarantee: returns the first argument that is not `None`, including falsy values like `0` or `""`; returns `None` when every argument is `None`.
    - Fails: never raises.
    - Non-goal: does not treat `0`/`""` as absent and does not authorize export, equivalence, or release.
    """
    for value in values:
        if value is not None:
            return value
    return None


def _acceptance_import_fields(
    acceptance_entry: Mapping[str, Any],
    acceptance_receipt: Mapping[str, Any],
) -> tuple[Any, Any]:
    """Resolve the accepted body-count and source-module-manifest status from entry+receipt.

    - Teleology: collapse the several acceptance-entry/receipt field spellings into the two values the gap-code logic compares against.
    - Guarantee: returns `(body_count, manifest_status)` taken by ordered `_first_present` precedence over entry then receipt then nested `source_module_imports`/`source_open_body_imports`; either element is `None` when no source supplies it.
    - Fails: never raises; non-Mapping nested fields are treated as empty maps.
    - Reads: only the in-memory `acceptance_entry` and `acceptance_receipt` mappings (no filesystem access).
    - Non-goal: does not verify digests, authorize source-body export, equivalence, or release.
    """
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
    """Build the report-only gap analysis of accepted example bodies vs. acceptance/fixture binding.

    - Teleology: surface organs whose example module bodies are imported but not bound to fixture-manifest or acceptance authority, so the binding gap is visible without mutating anything.
    - Guarantee: returns a `microcosm_partial_import_binding_report_v1` dict with `status` always `"pass"`, per-organ `rows` (sorted gap-first then organ id) carrying `gap_codes`/`recommended_action`, and aggregate counts (`row_count`, `gap_count`, `examples_body_present_count`, `acceptance_zero_gap_count`, `fixture_manifest_gap_count`); `rows` is empty when no example roots are accepted.
    - Fails: never raises and never reports a non-`pass` status; gaps are encoded as `gap_codes` strings on rows, not exceptions. Malformed JSON in a read file would propagate the underlying parse error.
    - Reads: acceptance, substitution-ledger, example `source_module_manifest.json`, fixture-manifest, and acceptance-receipt JSON under `root` (all read-only; report-only, no mutation per `authority_boundary`).
    - When-needed: inspect when example bodies look present but acceptance/fixtures appear unbound, or before trusting that imported example substrate is bound to authority.
    - Escalates-to: the per-organ `recommended_action` (e.g. `bind_acceptance_to_verified_example_substrate`), the fixture/acceptance receipts under `receipts/acceptance/first_wave`, and `core/acceptance/first_wave_acceptance.json` as the binding authority.
    - Non-goal: does not bind, mutate acceptance/fixtures/registries, authorize source-body export, public-safe equivalence, or release; it is a diagnostic, not a repair.
    """
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
    """CLI entry: build and emit the partial import-binding gap report (full report or card).

    - Teleology: surface organs whose example bodies are imported but not bound to acceptance/fixture authority.
    - Guarantee: prints the report (or compact card with `--card`) JSON and always returns 0; optionally writes it to `--out`.
    - Fails: None for normal runs (report status is always `pass`); a malformed `--out` parent dir would raise from the atomic write.
    - Reads: acceptance, substitution-ledger, manifest, and receipt JSON under `--root` (read-only; report-only, no mutation).
    - Writes: `--out` JSON file when provided.
    - When-needed: invoked from the shell or test harness, not from library code.
    """
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
