from __future__ import annotations

import hashlib
import json
from pathlib import Path

from microcosm_core.macro_tools.command_output_projection import (
    ENVELOPE_KIND,
    REQUIRED_FIELDS,
    command_projection,
    envelope_field_present,
    make_currentness,
    make_omission_receipt,
    make_validation_contract,
)
from microcosm_core.macro_tools.command_output_sidecar import (
    ENV_VAR,
    RECEIPT_KIND,
    RECEIPT_SCHEMA_VERSION,
    SIDECAR_ROOT,
    maybe_route_to_sidecar,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
)


def test_command_output_projection_macro_tool_emits_required_projection_envelope() -> None:
    envelope = command_projection(
        command="--demo",
        band="card",
        selector="public-fixture",
        summary={"row_count": 1},
        currentness=make_currentness(
            generated_at="2026-05-25T00:00:00Z",
            source_refs_checked=["microcosm-substrate/tests"],
        ),
        drilldown_command="microcosm command-output-projection-fixture --band full",
        evidence_command="microcosm command-output-projection-fixture --band full",
        omission_receipt=make_omission_receipt(
            omitted=["rows"],
            reason="card band keeps only count-level command-output evidence",
            drilldown="microcosm command-output-projection-fixture --band full",
        ),
        validation_contract=make_validation_contract(
            freshness_probe="pytest microcosm-substrate/tests/test_command_output_projection_runtime.py",
        ),
    )

    assert envelope["kind"] == ENVELOPE_KIND
    assert envelope["row_id"] == "kernel:demo:public-fixture::card"
    for field in REQUIRED_FIELDS:
        assert envelope_field_present(envelope, field), field
    assert envelope["omission_receipt"]["omitted"] == ["rows"]


def test_command_output_sidecar_macro_tool_writes_bounded_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(ENV_VAR, "0")
    payload = {
        "kind": "public_command_output_fixture",
        "schema_version": "public_command_output_fixture_v0",
        "summary": {"row_count": 3},
        "rows": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
    }

    receipt = maybe_route_to_sidecar(
        payload,
        surface="microcosm.command_output_projection.fixture",
        repo_root=tmp_path,
    )

    assert receipt is not None
    assert receipt["kind"] == RECEIPT_KIND
    assert receipt["schema_version"] == RECEIPT_SCHEMA_VERSION
    assert receipt["status"] == "written_to_sidecar"
    assert receipt["payload_summary"]["summary"] == {"row_count": 3}
    sidecar_path = tmp_path / receipt["output_path"]
    assert sidecar_path.is_file()
    assert sidecar_path.parent.parent == tmp_path / SIDECAR_ROOT
    assert json.loads(sidecar_path.read_text(encoding="utf-8")) == payload
    assert all("--command-output" in command for command in receipt["read_next"])


def test_command_output_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(
        (BUNDLE_INPUT / "command_output_source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["manifest_id"] == "command_output_projection_source_modules_import"
    assert manifest["module_count"] == 4
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text
