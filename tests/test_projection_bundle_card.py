from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from microcosm_core import cli


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_cli_macro_projection_bundle_card_reads_cached_receipt_without_rerun(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "projection-import"
    out_dir.mkdir()
    receipt = out_dir / "exported_projection_import_bundle_validation_result.json"
    receipt_payload = {
        "schema_version": "exported_projection_import_bundle_validation_result_v1",
        "status": "pass",
        "input_mode": "exported_projection_import_bundle",
        "projection_cell_count": 78,
        "ready_projection_cell_count": 78,
        "blocked_projection_cell_count": 0,
        "public_safe_body_import_status": "pass",
        "public_safe_body_import_count": 233,
        "runtime_severance_status": "pass",
        "runtime_dependency_status": "pass",
        "dependency_preflight_gate_status": "pass",
        "organ_lifecycle_coverage_status": "pass",
        "source_ref_count": 12,
        "public_runtime_ref_count": 10,
        "validation_ref_count": 14,
        "next_best_lane": "projection_import_complete",
        "body_in_receipt": False,
    }
    receipt.write_text(json.dumps(receipt_payload), encoding="utf-8")

    def fail_if_rerun(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError(
            "cached projection-bundle card must not rerun validation"
        )

    monkeypatch.setattr(
        cli.macro_projection_import_protocol,
        "run_projection_bundle",
        fail_if_rerun,
    )

    status = cli.main(
        [
            "macro-projection-import-protocol",
            "run-projection-bundle",
            "--card",
            "--input",
            str(
                MICROCOSM_ROOT
                / "examples/macro_projection_import_protocol/"
                "exported_projection_import_bundle"
            ),
            "--out",
            str(out_dir),
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert status == 0
    assert payload["schema_version"] == "macro_projection_bundle_cached_card_v1"
    assert payload["status"] == "pass"
    assert payload["card_id"] == "projection_bundle_cached_validation"
    assert payload["cache_status"] == "cached_receipt_read"
    assert payload["cached_receipt_ref"] == str(receipt)
    assert payload["cached_receipt_bytes"] == receipt.stat().st_size
    assert payload["projection_cell_count"] == 78
    assert payload["public_safe_body_import_count"] == 233
    assert payload["safe_to_show"]["body_in_receipt"] is False
    assert payload["cache_freshness"]["status"] == "current"
    assert payload["cache_freshness"]["input_status"] == "current"
    assert payload["cache_freshness"]["tracked_top_level_json_count"] > 0
    assert payload["cache_freshness"]["stale_top_level_json_count"] == 0
    assert payload["cache_freshness"]["input_refs_exported"] is False
    assert payload["safe_to_show"]["input_refs_exported"] is False
    assert "source_refs" not in payload
    assert "input_refs" not in payload
    assert str(MICROCOSM_ROOT) not in output


def test_cli_macro_projection_bundle_card_marks_input_bundle_stale(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "bundle"
    input_dir.mkdir()
    input_file = input_dir / "projection_protocol.json"
    input_file.write_text("{}", encoding="utf-8")
    out_dir = tmp_path / "projection-import"
    out_dir.mkdir()
    receipt = out_dir / "exported_projection_import_bundle_validation_result.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "exported_projection_import_bundle_validation_result_v1",
                "status": "pass",
                "input_mode": "exported_projection_import_bundle",
                "projection_cell_count": 1,
                "source_ref_count": 0,
                "body_in_receipt": False,
            }
        ),
        encoding="utf-8",
    )
    input_mtime_ns = receipt.stat().st_mtime_ns + 1_000_000_000
    os.utime(input_file, ns=(input_mtime_ns, input_mtime_ns))

    def fail_if_rerun(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError(
            "stale projection-bundle card must not rerun validation"
        )

    monkeypatch.setattr(
        cli.macro_projection_import_protocol,
        "run_projection_bundle",
        fail_if_rerun,
    )

    status = cli.main(
        [
            "macro-projection-import-protocol",
            "run-projection-bundle",
            "--card",
            "--input",
            str(input_dir),
            "--out",
            str(out_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 1
    assert payload["status"] == "stale_cached_receipt"
    assert payload["cache_status"] == "stale_cached_receipt"
    assert payload["cache_freshness"]["status"] == "stale"
    assert payload["cache_freshness"]["input_status"] == "stale"
    assert payload["cache_freshness"]["source_ref_status"] == "current"
    assert payload["cache_freshness"]["tracked_top_level_json_count"] == 1
    assert payload["cache_freshness"]["stale_top_level_json_count"] == 1
    assert payload["cache_freshness"]["tracked_source_ref_count"] == 0
    assert payload["cache_freshness"]["input_refs_exported"] is False
    assert payload["safe_to_show"]["input_refs_exported"] is False
    assert "input_refs" not in payload
    assert "source_refs" not in payload


def test_cli_macro_projection_bundle_card_marks_missing_input_stale(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "missing-bundle"
    out_dir = tmp_path / "projection-import"
    out_dir.mkdir()
    receipt = out_dir / "exported_projection_import_bundle_validation_result.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "exported_projection_import_bundle_validation_result_v1",
                "status": "pass",
                "input_mode": "exported_projection_import_bundle",
                "projection_cell_count": 1,
                "source_ref_count": 0,
                "body_in_receipt": False,
            }
        ),
        encoding="utf-8",
    )

    def fail_if_rerun(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError(
            "missing-input projection card must not rerun validation"
        )

    monkeypatch.setattr(
        cli.macro_projection_import_protocol,
        "run_projection_bundle",
        fail_if_rerun,
    )

    status = cli.main(
        [
            "macro-projection-import-protocol",
            "run-projection-bundle",
            "--card",
            "--input",
            str(input_dir),
            "--out",
            str(out_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 1
    assert payload["status"] == "stale_cached_receipt"
    assert payload["cache_freshness"]["status"] == "stale"
    assert payload["cache_freshness"]["input_status"] == "missing_input"
    assert payload["cache_freshness"]["tracked_top_level_json_count"] == 0
    assert payload["cache_freshness"]["stale_top_level_json_count"] == 0
    assert payload["cache_freshness"]["input_refs_exported"] is False
    assert "input_refs" not in payload


def test_cli_macro_projection_bundle_card_marks_source_refs_stale(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_dir = tmp_path / "bundle"
    input_dir.mkdir()
    (input_dir / "projection_protocol.json").write_text("{}", encoding="utf-8")
    out_dir = tmp_path / "projection-import"
    out_dir.mkdir()
    receipt = out_dir / "exported_projection_import_bundle_validation_result.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "exported_projection_import_bundle_validation_result_v1",
                "status": "pass",
                "input_mode": "exported_projection_import_bundle",
                "projection_cell_count": 1,
                "source_refs": ["live_source.py"],
                "source_ref_count": 1,
                "body_in_receipt": False,
            }
        ),
        encoding="utf-8",
    )
    live_source = tmp_path / "live_source.py"
    live_source.write_text("changed after receipt\n", encoding="utf-8")
    source_mtime_ns = receipt.stat().st_mtime_ns + 1_000_000_000
    os.utime(live_source, ns=(source_mtime_ns, source_mtime_ns))

    def fail_if_rerun(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError(
            "cached projection-bundle card must not rerun validation"
        )

    monkeypatch.setattr(
        cli.macro_projection_import_protocol,
        "run_projection_bundle",
        fail_if_rerun,
    )

    status = cli.main(
        [
            "macro-projection-import-protocol",
            "run-projection-bundle",
            "--card",
            "--input",
            str(input_dir),
            "--out",
            str(out_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 1
    assert payload["status"] == "stale_cached_receipt"
    assert payload["cache_status"] == "stale_cached_receipt"
    assert payload["cache_freshness"]["status"] == "stale"
    assert payload["cache_freshness"]["input_status"] == "current"
    assert payload["cache_freshness"]["source_ref_status"] == "stale"
    assert payload["cache_freshness"]["stale_top_level_json_count"] == 0
    assert payload["cache_freshness"]["tracked_source_ref_count"] == 1
    assert payload["cache_freshness"]["source_refs_exported"] is False
    assert "source_refs" not in payload
