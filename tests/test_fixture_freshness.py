from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.validators import fixture_freshness
from microcosm_core.validators.fixture_freshness import (
    HASH_CHUNK_SIZE,
    _iter_directory_files,
    _sha256,
    _sha256_directory,
    run_fixture_freshness,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SUPPORT = MICROCOSM_ROOT / "core/preflight_support"
READINESS = PREFLIGHT_SUPPORT / "organ_fixture_validator_readiness_v1.json"
NEGATIVE_MATRIX = PREFLIGHT_SUPPORT / "fixture_negative_case_matrix_v1.json"
MISSION_DAG = PREFLIGHT_SUPPORT / "microcosm_rebuild_mission_graph_v1.json"
RECEIPT_COVERAGE = PREFLIGHT_SUPPORT / "validator_receipt_coverage_map_v1.json"


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _copy_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _symlink_readonly_fixture_tree(MICROCOSM_ROOT / "examples", public_root / "examples")
    _symlink_readonly_fixture_tree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    _copytree_readonly_fixture(MICROCOSM_ROOT / "receipts", public_root / "receipts")
    return public_root


def _symlink_readonly_fixture_tree(source: Path, destination: Path) -> None:
    try:
        destination.symlink_to(source.resolve(), target_is_directory=True)
    except OSError:
        _copytree_readonly_fixture(source, destination)


def _copytree_readonly_fixture(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, copy_function=_copy_readonly_fixture_file)


def _copy_readonly_fixture_file(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return destination


def _accepted_registry_rows(public_root: Path) -> list[dict[str, object]]:
    registry = json.loads((public_root / "core/organ_registry.json").read_text(encoding="utf-8"))
    return [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]


def _source_body_import_expectations(
    public_root: Path,
    accepted_rows: list[dict[str, object]],
) -> dict[str, object]:
    organ_ids: list[str] = []
    body_material_count = 0
    source_manifest_ref_count = 0
    for row in accepted_rows:
        organ_id = str(row["organ_id"])
        manifest_path = (
            public_root
            / "core/fixture_manifests"
            / f"{organ_id}.fixture_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_open = manifest.get("source_open_body_imports")
        if not isinstance(source_open, dict):
            continue
        organ_ids.append(organ_id)
        body_count = source_open.get("body_material_count") or manifest.get(
            "body_copied_material_count"
        )
        if not isinstance(body_count, int):
            body_count = len(source_open.get("body_material_ids", []))
        body_material_count += body_count
        source_manifest_refs = source_open.get("source_manifest_refs", [])
        source_manifest_ref_count += (
            len(source_manifest_refs) if isinstance(source_manifest_refs, list) else 0
        )
    return {
        "organ_ids": organ_ids,
        "body_material_count": body_material_count,
        "source_manifest_ref_count": source_manifest_ref_count,
    }


def _update_source_open_body_imports(
    public_root: Path,
    organ_id: str,
    updates: dict[str, object],
) -> None:
    manifest_path = (
        public_root / "core/fixture_manifests" / f"{organ_id}.fixture_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_open = manifest["source_open_body_imports"]
    source_open.update(updates)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _update_registry_row(
    public_root: Path,
    organ_id: str,
    mutator: Any,
) -> None:
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for row in registry["implemented_organs"]:
        if row.get("organ_id") == organ_id:
            mutator(row)
            break
    else:
        raise AssertionError(f"missing organ registry row: {organ_id}")
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_fixture_freshness_passes_and_emits_acceptance_summary(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    out = public_root / "receipts/preflight/fixture_runner_freshness.json"
    accepted_rows = _accepted_registry_rows(public_root)
    expected_source_bodies = _source_body_import_expectations(public_root, accepted_rows)
    expected_truth_counts = Counter(
        str(row["truth_accounting_bucket"]) for row in accepted_rows
    )
    expected_evidence_counts = Counter(
        str(row["evidence_class"]) for row in accepted_rows
    )
    expected_disposition_counts = Counter(
        str(row["real_substrate_disposition"]) for row in accepted_rows
    )
    expected_progress_count = sum(
        1 for row in accepted_rows if row.get("counts_as_real_substrate_progress")
    )

    receipt = run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        out,
        command="pytest",
    )

    summary_path = public_root / "receipts/first_wave/acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "pass"
    assert receipt["stale_receipt_count"] == 0
    assert receipt["stale_receipt_codes"] == []
    assert receipt["acceptance_summary_receipt"] == "receipts/first_wave/acceptance_summary.json"
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in receipt
    assert "private_state_scan" not in summary
    assert summary["status"] == "pass"
    assert summary["acceptance_summary_blockers"] == []
    assert summary["accepted_count"] == len(accepted_rows)
    assert summary["truth_accounting"]["real_substrate_progress_count"] == (
        expected_progress_count
    )
    assert summary["truth_accounting"]["non_progress_accepted_count"] == (
        len(accepted_rows) - expected_progress_count
    )
    assert summary["truth_accounting"]["copied_non_secret_macro_body_count"] == (
        expected_truth_counts.get("copied_non_secret_macro_body", 0)
    )
    assert summary["truth_accounting"]["real_import_validation_count"] == (
        expected_truth_counts.get("real_import_validation", 0)
    )
    assert summary["truth_accounting"]["regression_negative_fixture_count"] == (
        expected_truth_counts.get("regression_negative_fixture", 0)
    )
    assert summary["truth_accounting"]["evidence_class_counts"] == dict(
        expected_evidence_counts
    )
    disposition_coverage = summary["disposition_coverage"]
    assert disposition_coverage == summary["truth_accounting"][
        "disposition_coverage"
    ]
    assert disposition_coverage["status"] == "pass"
    assert disposition_coverage["covered_count"] == len(accepted_rows)
    assert disposition_coverage["synthetic_accepted_count"] == 3
    assert disposition_coverage["disposition_counts"] == dict(
        sorted(expected_disposition_counts.items())
    )
    assert (
        disposition_coverage["missing_synthetic_acceptance_dispositions"] == []
    )
    assert (
        disposition_coverage["invalid_synthetic_acceptance_disposition"] == []
    )
    assert (
        disposition_coverage["synthetic_acceptance_progress_flag_mismatch"] == []
    )
    source_body_imports = summary["source_body_imports"]
    assert source_body_imports == summary["truth_accounting"]["source_body_imports"]
    assert source_body_imports["status"] == "pass"
    assert source_body_imports["source_body_import_organ_count"] == len(
        expected_source_bodies["organ_ids"]
    )
    assert source_body_imports["body_material_count"] == expected_source_bodies[
        "body_material_count"
    ]
    assert source_body_imports["source_manifest_ref_count"] == expected_source_bodies[
        "source_manifest_ref_count"
    ]
    assert source_body_imports["missing_source_manifest_refs"] == []
    assert source_body_imports["body_in_receipt"] is False
    source_rows = {row["organ_id"]: row for row in source_body_imports["rows"]}
    assert source_rows["agent_route_observability_runtime"][
        "body_material_count"
    ] == 8
    assert source_rows["macro_projection_import_protocol"][
        "body_material_count"
    ] == 177
    assert source_rows["macro_projection_import_protocol"][
        "source_manifest_refs_omitted"
    ] > 0
    manifest_coverage = summary["source_module_manifest_coverage"]
    assert manifest_coverage["status"] == "pass"
    assert manifest_coverage["source_manifest_ref_count"] == source_body_imports[
        "source_manifest_ref_count"
    ]
    assert manifest_coverage["missing_source_manifest_refs"] == []
    assert summary["lean_lake_authorized"] == "bounded_public_witness_only"
    assert summary["release_authorized"] is False
    assert summary["provider_calls_authorized"] is False
    assert summary["trading_or_financial_advice_authorized"] is False
    assert "receipts/preflight/dependency_preflight.json" in summary["preflight_receipts"]

    for path in (out, summary_path):
        text = path.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)
    assert "matched_excerpt" not in _walk_keys(summary)
    assert "body" not in _walk_keys(summary)


def test_fixture_freshness_blocks_missing_source_body_manifest_ref(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_tree(tmp_path)
    organ_id = "agent_route_observability_runtime"
    missing_ref = "examples/missing/source_manifest.json"
    manifest_path = (
        public_root / "core/fixture_manifests" / f"{organ_id}.fixture_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_open = manifest["source_open_body_imports"]
    source_open["source_manifest_refs"] = [
        *source_open["source_manifest_refs"],
        missing_ref,
    ]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    receipt = run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )
    summary = json.loads(
        (public_root / "receipts/first_wave/acceptance_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert receipt["status"] == "blocked"
    assert receipt["acceptance_summary_status"] == "blocked"
    assert (
        "ACCEPTANCE_SUMMARY_BLOCKED:source_body_imports"
        in receipt["stale_receipt_codes"]
    )
    assert summary["status"] == "blocked"
    assert summary["acceptance_summary_blockers"] == ["source_body_imports"]
    assert summary["source_body_imports"]["status"] == "blocked"
    assert summary["source_module_manifest_coverage"]["status"] == "blocked"
    assert {
        "organ_id": organ_id,
        "source_manifest_ref": missing_ref,
    } in summary["source_body_imports"]["missing_source_manifest_refs"]


def test_fixture_freshness_blocks_source_body_material_in_receipt(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_tree(tmp_path)
    organ_id = "agent_route_observability_runtime"
    _update_source_open_body_imports(
        public_root,
        organ_id,
        {"body_in_receipt": True},
    )

    receipt = run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )
    summary = json.loads(
        (public_root / "receipts/first_wave/acceptance_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert receipt["status"] == "blocked"
    assert receipt["acceptance_summary_status"] == "blocked"
    assert summary["status"] == "blocked"
    assert summary["acceptance_summary_blockers"] == ["source_body_imports"]
    assert summary["source_body_imports"]["body_in_receipt"] is True
    assert summary["source_body_imports"]["body_in_receipt_organs"] == [organ_id]
    assert summary["source_module_manifest_coverage"]["body_in_receipt"] is True


def test_fixture_freshness_blocks_missing_synthetic_disposition(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_tree(tmp_path)
    organ_id = "agent_benchmark_integrity_anti_gaming_replay"

    def remove_synthetic_disposition(row: dict[str, object]) -> None:
        row.pop("synthetic_acceptance_disposition", None)

    _update_registry_row(public_root, organ_id, remove_synthetic_disposition)

    receipt = run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )
    summary = json.loads(
        (public_root / "receipts/first_wave/acceptance_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert receipt["status"] == "blocked"
    assert receipt["acceptance_summary_status"] == "blocked"
    assert (
        "ACCEPTANCE_SUMMARY_BLOCKED:disposition_coverage"
        in receipt["stale_receipt_codes"]
    )
    assert summary["status"] == "blocked"
    assert summary["acceptance_summary_blockers"] == ["disposition_coverage"]
    assert summary["disposition_coverage"]["status"] == "blocked"
    assert summary["disposition_coverage"][
        "missing_synthetic_acceptance_dispositions"
    ] == [organ_id]


def test_fixture_freshness_blocks_missing_command_receipt(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    missing = public_root / "receipts/first_wave/navigation_hologram_route_plane/route_lease.json"
    missing.unlink()

    receipt = run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert receipt["stale_receipt_count"] == 1
    assert receipt["stale_receipt_codes"] == [
        "MISSING_RECEIPT:receipts/first_wave/navigation_hologram_route_plane/route_lease.json"
    ]


def test_fixture_freshness_file_hash_streams_without_materializing_body(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fixture_file = tmp_path / "large_fixture.json"
    body = b'{"payload":"' + (b"x" * (HASH_CHUNK_SIZE + 17)) + b'"}'
    fixture_file.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == fixture_file:
            raise AssertionError("fixture file hash should stream file bodies")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256(fixture_file) == hashlib.sha256(body).hexdigest()


def test_fixture_freshness_directory_hash_streams_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fixture_dir = tmp_path / "fixture"
    nested_dir = fixture_dir / "nested"
    nested_dir.mkdir(parents=True)
    (fixture_dir / "a.json").write_text('{"a": 1}\n', encoding="utf-8")
    nested_file = nested_dir / "b.json"
    nested_file.write_text('{"b": 2}\n', encoding="utf-8")

    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == fixture_dir:
            raise AssertionError("directory hash should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == fixture_dir or fixture_dir in self.parents:
            raise AssertionError("directory hash should stream child file bodies")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)
    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    digest = _sha256_directory(fixture_dir)
    assert digest == _sha256_directory(fixture_dir)

    nested_file.write_text('{"b": 3}\n', encoding="utf-8")
    assert _sha256_directory(fixture_dir) != digest


def test_fixture_freshness_directory_walk_recurses_without_entry_list(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fixture_dir = tmp_path / "fixture"
    nested_dir = fixture_dir / "nested"
    fixture_dir.mkdir()
    nested_dir.mkdir()
    nested_opened = False
    original_scandir = fixture_freshness.os.scandir

    class FakeEntry:
        def __init__(self, name: str, *, is_dir: bool, is_file: bool) -> None:
            self.name = name
            self._is_dir = is_dir
            self._is_file = is_file

        def is_dir(self, *, follow_symlinks: bool = False) -> bool:
            return self._is_dir

        def is_file(self, *, follow_symlinks: bool = False) -> bool:
            return self._is_file

    class ScandirRows:
        def __init__(self, rows: list[FakeEntry], *, guarded_parent: bool = False) -> None:
            self._rows = rows
            self._guarded_parent = guarded_parent
            self._index = 0

        def __enter__(self) -> "ScandirRows":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> "ScandirRows":
            return self

        def __next__(self) -> FakeEntry:
            nonlocal nested_opened
            if self._index >= len(self._rows):
                raise StopIteration
            if self._guarded_parent and self._index == 1 and not nested_opened:
                raise AssertionError(
                    "fixture freshness walk should recurse before pulling sibling entries"
                )
            row = self._rows[self._index]
            self._index += 1
            return row

    def guarded_scandir(path: Path) -> ScandirRows:
        nonlocal nested_opened
        if path == fixture_dir:
            return ScandirRows(
                [
                    FakeEntry("nested", is_dir=True, is_file=False),
                    FakeEntry("root.json", is_dir=False, is_file=True),
                ],
                guarded_parent=True,
            )
        if path == nested_dir:
            nested_opened = True
            return ScandirRows([FakeEntry("artifact.json", is_dir=False, is_file=True)])
        return original_scandir(path)

    monkeypatch.setattr(fixture_freshness.os, "scandir", guarded_scandir)

    assert [
        path.relative_to(fixture_dir).as_posix()
        for path in _iter_directory_files(fixture_dir)
    ] == ["nested/artifact.json", "root.json"]
    assert nested_opened is True


def test_fixture_freshness_directory_scan_skips_symlinked_files(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    direct = fixture_dir / "direct.json"
    direct.write_text('{"direct": true}\n', encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text('{"outside": true}\n', encoding="utf-8")
    symlink = fixture_dir / "linked.json"
    try:
        symlink.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    refs = [
        path.relative_to(fixture_dir).as_posix()
        for path in _iter_directory_files(fixture_dir)
    ]

    assert refs == ["direct.json"]
