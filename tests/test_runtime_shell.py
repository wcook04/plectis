from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from urllib.request import urlopen

from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _copy_runtime_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "examples", public_root / "examples")
    return public_root


def test_runtime_shell_status_is_product_centered() -> None:
    shell = RuntimeShell(MICROCOSM_ROOT)

    status = shell.status()

    assert status["status"] == "pass"
    assert status["adapter_backed_organ_count"] == 7
    assert status["fixture_runner_backed_organ_count"] == 0
    assert status["release_authorized"] is False
    assert "microcosm init <project>" in status["runtime_surface"]["commands"]
    assert "microcosm route <project>" in status["runtime_surface"]["commands"]
    assert "microcosm evidence list <project>" in status["runtime_surface"]["commands"]
    assert status["runtime_surface"]["receipts_are_drilldown_evidence"] is True


def test_runtime_shell_runs_demo_workflow_against_exported_bundles(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    result = shell.run_demo("examples/runtime_shell/demo_project")

    assert result["status"] == "pass"
    assert len(result["events"]) == 7
    assert [event["status"] for event in result["events"]] == ["pass"] * 7
    assert {event["input_mode"] for event in result["events"]} == {
        "exported_substrate_bundle",
        "exported_standards_bundle",
        "exported_evidence_bundle",
        "exported_route_plane_bundle",
        "exported_mission_transaction_bundle",
        "exported_observability_bundle",
        "exported_assimilation_bundle",
    }
    for ref in result["evidence_refs"]:
        assert ref.startswith("receipts/runtime_shell/demo_project/organs/")
        assert (public_root / ref).is_file()

    trace = json.loads((public_root / result["trace_ref"]).read_text(encoding="utf-8"))
    assert trace["status"] == "pass"
    assert trace["otel_shape"]["span_count"] == 7
    assert trace["otel_shape"]["metrics"]["runtime_steps_passed"] == 7
    output_text = (public_root / "receipts/runtime_shell/demo_project/demo_project_result.json").read_text(
        encoding="utf-8"
    )
    assert "/Users/" not in output_text
    assert "src/ai_workflow" not in output_text


def test_runtime_shell_route_and_evidence_drilldowns(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)
    result = shell.run_demo()
    work_demo = shell.run_work_demo()

    route = shell.inspect_route("public_runtime_option_surface")
    evidence = shell.inspect_evidence(result["evidence_refs"][0])

    assert route["status"] == "pass"
    assert route["route"]["route_id"] == "public_runtime_option_surface"
    assert evidence["status"] == "pass"
    assert evidence["receipt"]["status"] == "pass"
    assert evidence["body_redacted"] is True
    assert work_demo["status"] == "pass"
    assert work_demo["evidence_ref"].startswith("receipts/runtime_shell/work_demo/")
    assert work_demo["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False


def test_runtime_shell_serves_status_endpoint(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)
    server = shell.serve("127.0.0.1", 0)
    host, port = server.server_address
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    try:
        with urlopen(f"http://{host}:{port}/status", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        thread.join(timeout=5)
        server.server_close()

    assert payload["status"] == "pass"
    assert payload["adapter_backed_organ_count"] == 7
