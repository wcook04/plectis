from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
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
TRACE_CAPSULE_MANIFEST = BUNDLE_INPUT / "trace_capsule_source_module_manifest.json"


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


def test_trace_capsule_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(TRACE_CAPSULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "trace_capsule_prompt_edit_capture_source_modules_import"
    assert manifest["module_count"] == 4
    assert manifest["public_runtime_policy"].startswith("public validation uses fixture")
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


def _load_trace_capsule_source_module():
    module_path = (
        BUNDLE_INPUT
        / "source_modules/tools/meta/observability/cli_prompt_trace.py"
    )
    spec = importlib.util.spec_from_file_location(
        "microcosm_trace_capsule_source_module",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_trace_capsule_cli_prompt_trace_source_module_renders_public_fixture() -> None:
    module = _load_trace_capsule_source_module()
    output = "Process exited with code 0\nOutput:\ncompiled fixture"
    turn = module.Turn(
        provider="codex",
        session_id="public-fixture-session",
        session_file="public-fixture-session.jsonl",
        turn_id="turn_public_fixture",
        turn_index=1,
        cwd="microcosm-substrate",
        started_at="2026-05-25T00:00:00Z",
        completed_at="2026-05-25T00:01:00Z",
        prompt_text="Render a public Trace Capsule fixture.",
        prompt_char_count=len("Render a public Trace Capsule fixture."),
        prompt_sha256_16="fixturepromptsha",
        tool_events=[
            module.ToolEvent(
                index=1,
                name="functions.exec_command",
                input={"cmd": "./repo-python -m py_compile public_fixture.py"},
                tool_call_id="call_public_fixture",
                started_at="2026-05-25T00:00:01Z",
                completed_at="2026-05-25T00:00:02Z",
                duration_ms=1000,
                is_error=False,
                output_text=output,
                output_char_count=len(output),
                output_sha256_16=module._sha16(output),
                exit_code=0,
                source_record_indices=[10, 11],
            )
        ],
        assistant_text="Validation passed.",
        assistant_events=[module.AssistantEvent("Validation passed.", 12)],
        is_complete=True,
        source_record_indices=[1, 2, 10, 11, 12],
        source_ref={"raw_authority": "public_fixture"},
    )

    text, meta = module.render_trace_capsule_text(
        turn,
        title="Public Trace Capsule Fixture",
    )

    assert text.startswith("TRACE CAPSULE v3\n")
    assert "final_validation: passed" in text
    assert "terminal_checks: pass=1 fail=0 other=0 total=1" in text
    assert "not_included: hidden_reasoning" in text
    assert meta["terminal_validation_pass_count"] == 1
    assert meta["closeout_present"] is True
    assert "/Users/" not in text


def test_agent_trace_structurer_parser_source_module_runs_node_fixture_tests() -> None:
    parser_test = (
        BUNDLE_INPUT
        / "source_modules/tools/agent_trace_structurer/parser.test.mjs"
    )

    result = subprocess.run(
        ["node", "--test", str(parser_test.name)],
        cwd=parser_test.parent,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stdout + result.stderr
