from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path

from microcosm_core.organs import tool_server_pressure_inventory as organ

MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = MICROCOSM_ROOT / "fixtures/first_wave/tool_server_pressure_inventory/input"
EXAMPLE_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/tool_server_pressure_inventory/exported_tool_server_pressure_inventory_bundle"
)

POLICY = json.loads((INPUT_DIR / "pressure_policy.json").read_text())
OWNER_CLASSES = json.loads((INPUT_DIR / "owner_classes.json").read_text())
PS_TEXT = json.loads((INPUT_DIR / "process_table.json").read_text())["ps_text"]


def _source_target_path(ref: str) -> Path:
    target = Path(ref)
    if target.parts and target.parts[0] == "microcosm-substrate":
        target = Path(*target.parts[1:])
    return MICROCOSM_ROOT / target


def _sha256_ref(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_run_passes_and_observes_every_negative_case(tmp_path: Path) -> None:
    result = organ.run(INPUT_DIR, tmp_path / "out")
    assert result["status"] == "pass", result["findings"]
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 1
    assert result["missing_negative_cases"] == []
    for case_id, codes in organ.EXPECTED_NEGATIVE_CASES.items():
        observed = result["observed_negative_cases"].get(case_id, [])
        for code in codes:
            assert code in observed, (case_id, observed)


def test_exported_pressure_bundle_requires_source_module_manifest(tmp_path: Path) -> None:
    result = organ.run_pressure_bundle(EXAMPLE_BUNDLE, tmp_path / "bundle-out")
    assert result["status"] == "pass", result["findings"]
    assert result["input_mode"] == "exported_tool_server_pressure_inventory_bundle"
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_summary"]["verified_module_count"] == 1
    assert result["source_open_body_imports"]["material_classes"] == [
        "public_macro_tool_body"
    ]


def test_exported_pressure_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/tool_server_pressure_inventory/"
        "exported_tool_server_pressure_inventory_bundle"
    )
    shutil.copytree(EXAMPLE_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_id = manifest["modules"][0]["module_id"]
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = organ.run_pressure_bundle(
        bundle,
        public_root / "receipts/tool_server_pressure_inventory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "TSPI_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_summary"]["verified_module_count"] == 0
    assert result["source_module_summary"]["module_ids"] == [module_id]
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_exported_pressure_bundle_rejects_source_module_target_ref_path_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/tool_server_pressure_inventory/"
        "exported_tool_server_pressure_inventory_bundle"
    )
    shutil.copytree(EXAMPLE_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["path"] = (
        "examples/tool_server_pressure_inventory/"
        "exported_tool_server_pressure_inventory_bundle/source_modules/"
        "tools/meta/control/wrong_orphan_reaper.py"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = organ.run_pressure_bundle(
        bundle,
        public_root / "receipts/tool_server_pressure_inventory",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "TSPI_SOURCE_MODULE_TARGET_REF_PATH_MISMATCH" in result["error_codes"]
    assert "TSPI_SOURCE_MODULE_DIGEST_MISMATCH" not in result["error_codes"]
    assert result["source_module_summary"]["verified_module_count"] == 0
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_inventory_classifies_orphan_active_and_keep() -> None:
    inventory = organ.build_tool_server_pressure_inventory(
        PS_TEXT, policy=POLICY, owner_classes=OWNER_CLASSES
    )
    assert inventory["schema"] == "tool_server_pressure_inventory_v1"
    rows = {row["pid"]: row for row in inventory["rows"]}
    # ppid==1, allowlisted, old -> the only safe-close candidate.
    assert rows[200]["decision"] == "candidate_safe_close"
    assert rows[200]["owner_status"] == "launchd_detached"
    # young orphan (age < min_age) is NOT a safe-close candidate.
    assert rows[201]["decision"] == "requires_owner_check"
    # keep runtimes.
    assert rows[300]["decision"] == "keep"
    assert inventory["summary"]["candidate_safe_close_count"] == 1
    # rows carry a command_hash, never a command preview.
    assert all("command_hash" in row for row in inventory["rows"])
    assert all("command_preview" not in row for row in inventory["rows"])


def test_active_owner_descendant_is_never_safe_close() -> None:
    inventory = organ.build_tool_server_pressure_inventory(
        PS_TEXT, policy=POLICY, owner_classes=OWNER_CLASSES
    )
    for row in inventory["rows"]:
        if row["owner_status"] in organ.ACTIVE_OWNER_STATUS_VALUES:
            assert row["decision"] != "candidate_safe_close"


def test_owner_chain_cycle_terminates_and_requires_owner_check() -> None:
    cyclic_ps_text = (
        "8830 8831 20:00 0.0 12000 node tool-helper-mcp --port 8830\n"
        "8831 8830 20:00 0.0 8000 helper-parent-process\n"
    )
    inventory = organ.build_tool_server_pressure_inventory(
        cyclic_ps_text, policy=POLICY, owner_classes=OWNER_CLASSES
    )
    rows = {row["pid"]: row for row in inventory["rows"]}

    assert rows[8830]["owner_status"] == "active_parent_process"
    assert rows[8830]["decision"] == "requires_owner_check"
    assert rows[8830]["reason"] == "active_parent_chain_requires_owner_check"
    assert rows[8830]["decision"] != "candidate_safe_close"


def test_over_budget_active_owner_gets_release_request_not_kill() -> None:
    inventory = organ.build_tool_server_pressure_inventory(
        PS_TEXT, policy=POLICY, owner_classes=OWNER_CLASSES
    )
    groups = inventory["summary"]["active_owner_pressure_groups"]
    assert len(groups) == 1
    group = groups[0]
    assert group["process_kind"] == "mcp_tool_helper"
    assert group["owner_status"] == "active_session_chain"
    assert group["excess_count"] == 1
    request = group["owner_release_request"]
    assert request["schema"] == "helper_owner_release_request_v1"
    assert request["requested_action"] == "release_tool_lease"
    assert request["result"] == "requested"
    assert request["target_owner"] == "owning_session"
    assert request["safety"]["no_process_signal_sent"] is True


def test_relief_receipt_never_signals_and_recommends_release() -> None:
    receipt = organ.build_pressure_hygiene_relief_receipt(
        PS_TEXT, policy=POLICY, owner_classes=OWNER_CLASSES
    )
    assert receipt["schema"] == "pressure_hygiene_relief_receipt_v1"
    assert receipt["action"]["safe_close_action_count"] == 0
    assert receipt["action"]["no_process_signal_sent"] is True
    # A safe-close candidate exists (pid 200), so the verdict is safe-action-available
    # but the receipt still takes ZERO action.
    assert receipt["verdict"] == "pending_safe_close_action"


def test_module_has_no_actuator_and_no_live_ps() -> None:
    # Structural proof (prose-immune): the module imports no process-control
    # stdlib and never calls `.kill(...)`. The docstring may *name* os.kill /
    # SIGKILL to explain their removal, so scan the AST, not the text.
    tree = ast.parse(Path(organ.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "os" not in imported
    assert "signal" not in imported
    assert "subprocess" not in imported
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr != "kill"


def test_source_module_body_has_no_actuator_and_no_public_redaction_hits() -> None:
    manifest = json.loads((EXAMPLE_BUNDLE / "source_module_manifest.json").read_text())
    target_ref = manifest["modules"][0]["target_ref"]
    source_body = MICROCOSM_ROOT / target_ref
    tree = ast.parse(source_body.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert {"os", "signal", "subprocess"}.isdisjoint(imported)
    text = source_body.read_text(encoding="utf-8")
    assert "/Users/" not in text
    assert "command_preview" not in text
    assert '"process_signal_sent":' not in text


def test_source_module_manifest_target_ref_matches_path_and_digest() -> None:
    manifest = json.loads((EXAMPLE_BUNDLE / "source_module_manifest.json").read_text())
    module = manifest["modules"][0]

    target_from_ref = _source_target_path(module["target_ref"])
    target_from_path = _source_target_path(module["path"])

    assert target_from_ref == target_from_path
    assert target_from_ref.is_file()
    assert module["sha256"] == _sha256_ref(target_from_ref)
    assert module["target_sha256"] == _sha256_ref(target_from_ref)


def test_receipts_use_secret_exclusion_and_carry_no_absolute_paths(tmp_path: Path) -> None:
    result = organ.run(INPUT_DIR, tmp_path / "out")
    scan = result["secret_exclusion_scan"]
    assert scan["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    # The planted negative-fixture absolute path must never echo into a receipt.
    assert "/Users/REDACTION_NEGATIVE_FIXTURE" not in serialized
    # No receipt row carries the forbidden command_preview KEY (the case-id
    # "command_preview_leak" is a label, not a leak).
    assert '"command_preview":' not in serialized


def test_card_is_compact_and_omission_receipted(tmp_path: Path) -> None:
    result = organ.run(INPUT_DIR, tmp_path / "out")
    card = organ.result_card(result)
    assert card["schema_version"] == organ.CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["omission_receipt"]["omitted_full_payload_keys"]
    assert len(json.dumps(card, sort_keys=True)) < 4000
