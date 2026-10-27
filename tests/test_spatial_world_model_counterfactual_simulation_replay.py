from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    _line_count,
    main,
    run,
    run_simulation_bundle,
)
from microcosm_core.organs import (
    spatial_world_model_counterfactual_simulation_replay,
)
from microcosm_core.public_payload_boundary import SOURCE_OPEN_BODY_POLICY


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input"
)
FIXTURE_MANIFEST = (
    MICROCOSM_ROOT
    / "core/fixture_manifests/"
    "spatial_world_model_counterfactual_simulation_replay.fixture_manifest.json"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/spatial_world_model_counterfactual_simulation_replay/"
    "exported_spatial_world_model_simulation_bundle"
)
SPATIAL_SOURCE_BODY_MATERIAL_IDS = [
    "station_geometry_checker_source_body_import",
    "station_geometry_checker_test_body_import",
    "station_geometry_build_wiring_source_body_import",
]


@pytest.mark.parametrize(
    "review_change", [None, "missing_review", "wrong_digest", "changed_body"]
)
def test_standalone_spatial_export_preserves_only_reviewed_source_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    review_change: str | None,
) -> None:
    """Exercise the real export substitution lane, not a full export/build."""
    from microcosm_core import release_export
    from microcosm_core.runtime_shell import RuntimeShell

    source = tmp_path / "source/microcosm-substrate"
    bundle_ref = BUNDLE_INPUT.relative_to(MICROCOSM_ROOT)
    shutil.copytree(
        BUNDLE_INPUT,
        source / bundle_ref,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (source / "core").mkdir()
    for name in ("source_module_refresh_policy_v0.json", "private_state_forbidden_classes.json"):
        shutil.copy2(MICROCOSM_ROOT / "core" / name, source / "core" / name)
    manifest_path = source / bundle_ref / "source_module_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    first_ref = manifest["modules"][0]["target_ref"].removeprefix("microcosm-substrate/")
    policy_path = source / "core/source_module_refresh_policy_v0.json"
    policy = json.loads(policy_path.read_text())
    if review_change == "missing_review":
        policy["reviewed_publication"]["copies"].pop(first_ref)
    elif review_change == "wrong_digest":
        policy["reviewed_publication"]["copies"][first_ref]["sha256"] = "0" * 64
    elif review_change == "changed_body":
        with (source / first_ref).open("a") as stream:
            stream.write("\n# bytes changed after publication review\n")
    policy_path.write_text(json.dumps(policy))

    substitutions = {
        row["path"]: row
        for row in release_export._restricted_source_module_substitution_rows(source)
    }
    assert set(substitutions) == ({first_ref} if review_change else set())
    artifact = tmp_path / "artifact/microcosm-substrate"
    release_export._copy_allowed_files(
        sorted(path for path in source.rglob("*") if path.is_file()),
        root=source,
        target=artifact,
        private_body_substitutions=substitutions,
    )
    release_export._rewrite_private_body_stub_metadata(artifact, substitutions)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert not (artifact / ".git").exists()
    assert subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=artifact,
        capture_output=True,
        check=False,
    ).returncode != 0

    exported_manifest = artifact / bundle_ref / "source_module_manifest.json"
    if review_change:
        # The exporter omits substituted rows; the bundle must reject the
        # resulting incomplete source floor.
        exported = json.loads(exported_manifest.read_text())
        assert len(exported["modules"]) == len(manifest["modules"]) - 1
        assert len(exported["release_substitution_omissions"]) == 1
        assert (artifact / first_ref).read_bytes() != (source / first_ref).read_bytes()
        lens = RuntimeShell(artifact).spatial_simulation()
        assert lens["status"] == "blocked"
        assert lens["source_module_summary"]["status"] == "blocked"
        assert any(
            row["error_code"] == "SPATIAL_SOURCE_MODULE_FLOOR_INVALID"
            for row in lens["source_module_summary"]["findings"]
        )
        return

    assert exported_manifest.read_bytes() == manifest_bytes
    lens = RuntimeShell(artifact).spatial_simulation()
    assert lens["status"] == "pass"
    assert lens["authority_ceiling"]["release_authorized"] is False
    assert lens["simulation_summary"]["scene_state_count"] == 6
    assert lens["source_module_summary"]["public_safe_body_material_ids"] == (
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    for row in manifest["modules"]:
        target = artifact / row["target_ref"].removeprefix("microcosm-substrate/")
        assert hashlib.sha256(target.read_bytes()).hexdigest() == row["target_sha256"]

    # The independent replay validator still rejects bytes changed after export.
    with (artifact / first_ref).open("a") as stream:
        stream.write("\n# altered after export\n")
    tampered = RuntimeShell(artifact).spatial_simulation()
    assert tampered["status"] == "blocked"
    assert tampered["source_module_summary"]["status"] == "blocked"


def _sha256_ref(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


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


def test_spatial_world_model_line_count_streams_without_full_text_read(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "spatial_source.py"
    empty_source = tmp_path / "empty_spatial_source.py"
    source.write_text("one\n\ntwo\n", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in {source, empty_source}:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _line_count(source) == 3
    assert _line_count(empty_source) == 1


def test_spatial_world_model_counterfactual_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "spatial_world_model_counterfactual_simulation_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["selected_route_id"] == "spatial_world_model_counterfactual_simulation_replay"
    assert result["simulation_summary"]["scene_state_count"] == 6
    assert result["simulation_summary"]["replay_count"] == 6
    assert result["simulation_summary"]["state_transition_count"] == 6
    assert result["simulation_summary"]["predicted_state_body_count"] == 6
    assert result["simulation_summary"]["deterministic_simulation_pass_count"] == 6
    assert result["simulation_summary"]["gridworld_step_count"] == 6
    assert result["simulation_summary"]["predicted_actual_match_count"] == 6
    assert result["state_transition_analysis"]["status"] == "pass"
    assert result["state_transition_analysis"]["runtime_kind"] == (
        "deterministic_toy_gridworld_step"
    )
    assert result["simulation_summary"]["transition_diff_count"] == 6
    assert result["simulation_summary"]["oracle_state_check_count"] == 6
    assert result["simulation_summary"]["sensor_packet_ref_count"] == 12
    assert result["negative_case_summary"]["expected_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["observed_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["authority_ceiling"]["private_video_exported"] is False
    assert result["authority_ceiling"]["raw_sensor_data_exported"] is False
    assert result["authority_ceiling"]["live_robot_operation_authorized"] is False
    assert result["authority_ceiling"]["live_av_operation_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert result["unsafe_payload_bodies_in_receipt"] is False
    assert result["source_module_import_status"] == "not_present"
    assert (
        result["payload_boundary"]["boundary_id"]
        == "spatial_world_model_counterfactual_simulation_replay_payload_boundary"
    )
    assert result["safe_to_show"]["unsafe_payload_bodies_absent"] is True
    assert all(
        row["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
        for row in result["counterfactual_replays"]
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in result["counterfactual_replays"]
    )
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        assert result["negative_case_summary"]["observed_codes"][case_id] == codes


def test_spatial_world_model_counterfactual_replay_receipts_are_public_relative_and_payload_bounded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay",
        public_root
        / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input",
        public_root
        / "receipts/first_wave/spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        keys = _walk_keys(json.loads(text))
        assert "private_video_body" not in keys
        assert "raw_sensor_payload" not in keys
        assert "gps_trace_body" not in keys
        assert "body_redacted" not in keys
        assert "private_state_scan" not in keys


def test_spatial_world_model_counterfactual_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_simulation_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_spatial_world_model_simulation_bundle"
    assert result["selected_route_id"] == "spatial_world_model_counterfactual_simulation_replay"
    assert result["simulation_summary"]["replay_count"] == 6
    assert result["simulation_summary"]["state_transition_count"] == 6
    assert result["simulation_summary"]["predicted_state_body_count"] == 6
    assert result["simulation_summary"]["deterministic_simulation_pass_count"] == 6
    assert result["simulation_summary"]["gridworld_step_count"] == 6
    assert result["simulation_summary"]["predicted_actual_match_count"] == 6
    assert result["state_transition_analysis"]["status"] == "pass"
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    assert result["authority_ceiling"]["generated_video_authority_authorized"] is False
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert result["unsafe_payload_bodies_in_receipt"] is False
    assert (
        result["source_module_import_status"]
        == "copied_non_secret_macro_body_landed"
    )
    assert result["source_module_summary"]["status"] == "pass"
    assert result["source_module_summary"]["module_count"] == len(
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_module_summary"]["public_safe_body_material_ids"] == (
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_open_body_imports"]["status"] == "pass"
    assert (
        result["source_open_body_imports"]["source_import_class"]
        == "copied_non_secret_macro_body"
    )
    assert result["source_open_body_imports"]["body_material_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert result["source_open_body_imports"]["body_material_count"] == len(
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert (
        result["source_open_body_imports"]["body_material_ids"]
        == SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_open_body_imports"]["material_classes"] == [
        "public_macro_tool_body"
    ]
    assert result["source_open_body_imports"]["source_manifest_refs"] == [
        "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle/source_module_manifest.json"
    ]
    assert result["source_open_body_imports"]["aggregate_floor_ref"].endswith(
        "source_module_manifest.json::modules"
    )
    assert result["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert (
        result["source_open_body_imports"]["body_text_exported_in_workingness"]
        is False
    )
    assert result["body_copied_material_count"] == len(
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert (
        result["payload_boundary"]["boundary_id"]
        == "spatial_world_model_counterfactual_simulation_replay_payload_boundary"
    )
    encoded = json.dumps(result, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "private_state_scan" not in encoded


def test_spatial_world_model_counterfactual_source_modules_are_exact_station_geometry_imports(
    tmp_path: Path,
) -> None:
    result = run_simulation_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    modules = {
        row["module_id"]: row
        for row in result["source_module_summary"]["modules"]
    }
    assert set(modules) == set(SPATIAL_SOURCE_BODY_MATERIAL_IDS)
    for material_id in SPATIAL_SOURCE_BODY_MATERIAL_IDS:
        row = modules[material_id]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix("microcosm-substrate/")
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        assert target.is_file()
        assert row["status"] == "pass"
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["target_body_digest"] == _sha256_ref(target)
        assert row["source_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
        if source.is_file():
            assert _sha256_ref(source) == _sha256_ref(target)


@pytest.mark.parametrize(
    "change",
    [
        "missing_manifest",
        "omit_0",
        "omit_1",
        "omit_2",
        "extra",
        "duplicate",
        "wrong_id",
        "invalid_id",
        "wrong_count",
        "malformed_row",
    ],
)
def test_spatial_bundle_rejects_incomplete_source_floor(
    tmp_path: Path, change: str
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = public_root / BUNDLE_INPUT.relative_to(MICROCOSM_ROOT)
    shutil.copytree(BUNDLE_INPUT, bundle)
    (public_root / "core").mkdir()
    shutil.copy2(
        MICROCOSM_ROOT / "core/private_state_forbidden_classes.json",
        public_root / "core/private_state_forbidden_classes.json",
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if change == "missing_manifest":
        manifest_path.unlink()
    else:
        modules = manifest["modules"]
        if change.startswith("omit_"):
            modules.pop(int(change[-1]))
        elif change == "extra":
            modules.append({**modules[0], "module_id": "unexpected_material"})
        elif change == "duplicate":
            modules[-1] = dict(modules[0])
        elif change == "wrong_id":
            modules[-1]["module_id"] = "unexpected_material"
        elif change == "invalid_id":
            modules[-1]["module_id"] = {"unexpected": "object"}
        elif change == "wrong_count":
            manifest["module_count"] = 2
        elif change == "malformed_row":
            modules.append("not an object")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_simulation_bundle(bundle, public_root / "out", command="pytest")
    assert result["status"] == "blocked"
    assert result["source_module_summary"]["status"] == "blocked"
    assert any(
        row["error_code"] == "SPATIAL_SOURCE_MODULE_FLOOR_INVALID"
        for row in result["source_module_summary"]["findings"]
    )


def test_spatial_bundle_source_floor_change_invalidates_cached_receipt(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = public_root / BUNDLE_INPUT.relative_to(MICROCOSM_ROOT)
    shutil.copytree(BUNDLE_INPUT, bundle)
    (public_root / "core").mkdir()
    shutil.copy2(
        MICROCOSM_ROOT / "core/private_state_forbidden_classes.json",
        public_root / "core/private_state_forbidden_classes.json",
    )
    out = public_root / "out"
    first = run_simulation_bundle(
        bundle, out, command="pytest", reuse_fresh_receipt=True
    )
    assert first["status"] == "pass"
    cached = run_simulation_bundle(
        bundle, out, command="pytest", reuse_fresh_receipt=True
    )
    assert cached["receipt_reused"] is True

    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"].pop()
    manifest["module_count"] = len(manifest["modules"])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = run_simulation_bundle(
        bundle, out, command="pytest", reuse_fresh_receipt=True
    )
    assert result["receipt_reused"] is False
    assert result["status"] == "blocked"
    assert result["source_module_summary"]["status"] == "blocked"


def test_spatial_world_model_source_modules_reject_body_text_in_receipt(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/spatial_world_model_counterfactual_simulation_replay",
        public_root / "examples/spatial_world_model_counterfactual_simulation_replay",
    )
    bundle = (
        public_root
        / "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["body_text_in_receipt"] = True
    manifest["modules"][0]["body_text_in_receipt"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_simulation_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_summary"]["status"] == "blocked"
    error_codes = {
        finding["error_code"]
        for finding in result["source_module_summary"]["findings"]
    }
    assert "SPATIAL_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN" in error_codes
    assert "SPATIAL_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN" in error_codes


def test_spatial_world_model_counterfactual_fixture_manifest_exports_body_floor_summary(
) -> None:
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    body_imports = manifest["source_open_body_imports"]

    assert body_imports["status"] == "pass"
    assert body_imports["body_material_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert body_imports["body_material_count"] == len(
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert body_imports["body_material_ids"] == SPATIAL_SOURCE_BODY_MATERIAL_IDS
    assert body_imports["material_classes"] == ["public_macro_tool_body"]
    assert body_imports["body_text_exported_in_receipts"] is False
    assert body_imports["body_text_exported_in_workingness"] is False
    assert manifest["body_copied_material_count"] == len(
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )


def test_spatial_world_model_rejects_bad_state_transition_delta(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/spatial_world_model_counterfactual_simulation_replay",
        public_root / "examples/spatial_world_model_counterfactual_simulation_replay",
    )
    bundle = (
        public_root
        / "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle"
    )
    transition_path = bundle / "state_transitions.json"
    payload = json.loads(transition_path.read_text(encoding="utf-8"))
    payload["state_transitions"][0]["transition_diff"]["actor_count_delta"] = 3
    transition_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_simulation_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["state_transition_analysis"]["status"] == "blocked"
    transition_rows = {
        row["replay_id"]: row
        for row in result["state_transition_analysis"]["transition_rows"]
    }
    assert transition_rows["warehouse_occlusion_left_forklift_stop"][
        "simulation_passed"
    ] is False
    assert {
        finding["error_code"] for finding in result["positive_findings"]
    } >= {"SPATIAL_STATE_TRANSITION_SIMULATION_MISMATCH"}


def test_spatial_world_model_rejects_predicted_state_that_misses_gridworld_step(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/spatial_world_model_counterfactual_simulation_replay",
        public_root / "examples/spatial_world_model_counterfactual_simulation_replay",
    )
    bundle = (
        public_root
        / "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle"
    )
    transition_path = bundle / "state_transitions.json"
    payload = json.loads(transition_path.read_text(encoding="utf-8"))
    payload["state_transitions"][0]["predicted_state"]["actor_count"] -= 1
    transition_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_simulation_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    transition_rows = {
        row["replay_id"]: row
        for row in result["state_transition_analysis"]["transition_rows"]
    }
    mismatch = transition_rows["warehouse_occlusion_left_forklift_stop"]
    assert mismatch["gridworld_step_executed"] is True
    assert mismatch["actual_actor_count"] == 5
    assert mismatch["predicted_actor_count"] == 4
    assert mismatch["simulation_passed"] is False
    assert "predicted_state_actor_count_mismatch" in mismatch["findings"]


def test_spatial_world_model_input_perturbation_moves_verdict_and_rejects_stale_expected_transition(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/spatial_world_model_counterfactual_simulation_replay",
        public_root / "examples/spatial_world_model_counterfactual_simulation_replay",
    )
    bundle = (
        public_root
        / "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle"
    )
    receipt_root = (
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay"
    )
    replay_id = "warehouse_occlusion_left_forklift_stop"

    real_good = run_simulation_bundle(
        bundle,
        receipt_root / "real_good",
        command="pytest",
    )
    real_good_rows = {
        row["replay_id"]: row
        for row in real_good["state_transition_analysis"]["transition_rows"]
    }
    assert real_good["status"] == "pass"
    assert real_good_rows[replay_id]["actual_actor_count_delta"] == 1
    assert len(real_good_rows[replay_id]["actual_spawn_cells"]) == 1

    replay_path = bundle / "counterfactual_replays.json"
    replays = json.loads(replay_path.read_text(encoding="utf-8"))
    replay = replays["counterfactual_replays"][0]
    replay["sensor_packet_refs"].append(
        "public_sensor_packet::warehouse_occlusion_left_forklift_stop::motion"
    )
    replay_path.write_text(
        json.dumps(replays, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    stale_expected = run_simulation_bundle(
        bundle,
        receipt_root / "stale_expected",
        command="pytest",
    )
    stale_rows = {
        row["replay_id"]: row
        for row in stale_expected["state_transition_analysis"]["transition_rows"]
    }
    stale_row = stale_rows[replay_id]
    assert stale_expected["status"] == "blocked"
    assert stale_row["actual_actor_count_delta"] == 2
    assert stale_row["actual_actor_count"] == 6
    assert stale_row["predicted_actor_count"] == 5
    assert len(stale_row["actual_spawn_cells"]) == 2
    assert stale_row["simulation_passed"] is False
    assert {
        "predicted_state_actor_count_mismatch",
        "transition_diff_actor_delta_mismatch",
    } <= set(stale_row["findings"])

    transition_path = bundle / "state_transitions.json"
    transitions = json.loads(transition_path.read_text(encoding="utf-8"))
    transition = transitions["state_transitions"][0]
    transition["predicted_state"]["actor_count"] = stale_row["actual_actor_count"]
    transition["transition_diff"]["actor_count_delta"] = stale_row[
        "actual_actor_count_delta"
    ]
    transition["transition_diff"]["spawn_cells"] = stale_row["actual_spawn_cells"]
    transition_path.write_text(
        json.dumps(transitions, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    updated_expected = run_simulation_bundle(
        bundle,
        receipt_root / "updated_expected",
        command="pytest",
    )
    updated_rows = {
        row["replay_id"]: row
        for row in updated_expected["state_transition_analysis"]["transition_rows"]
    }
    updated_row = updated_rows[replay_id]
    assert updated_expected["status"] == "pass"
    assert updated_row["simulation_passed"] is True
    assert updated_row["actual_actor_count_delta"] == 2
    assert updated_row["actual_spawn_cells"] == stale_row["actual_spawn_cells"]
    assert updated_expected["state_transition_analysis"][
        "max_actual_actor_count_delta"
    ] == 2


def test_spatial_world_model_scene_perturbation_moves_gridworld_state_and_rejects_stale_expected_transition(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/spatial_world_model_counterfactual_simulation_replay",
        public_root / "examples/spatial_world_model_counterfactual_simulation_replay",
    )
    bundle = (
        public_root
        / "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle"
    )
    receipt_root = (
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay"
    )
    replay_id = "warehouse_occlusion_left_forklift_stop"

    real_good = run_simulation_bundle(
        bundle,
        receipt_root / "real_good",
        command="pytest",
    )
    real_good_rows = {
        row["replay_id"]: row
        for row in real_good["state_transition_analysis"]["transition_rows"]
    }
    real_good_row = real_good_rows[replay_id]
    assert real_good["status"] == "pass"
    assert real_good_row["source_actor_count"] == 4
    assert real_good_row["actual_actor_count"] == 5

    scene_path = bundle / "scene_states.json"
    scenes = json.loads(scene_path.read_text(encoding="utf-8"))
    scene = scenes["scene_states"][0]
    scene["actor_count"] += 1
    scene["topology_ref"] = "topology::state_perturbation_moves_spawn"
    scene_path.write_text(
        json.dumps(scenes, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    stale_expected = run_simulation_bundle(
        bundle,
        receipt_root / "stale_expected",
        command="pytest",
    )
    stale_rows = {
        row["replay_id"]: row
        for row in stale_expected["state_transition_analysis"]["transition_rows"]
    }
    stale_row = stale_rows[replay_id]
    assert stale_expected["status"] == "blocked"
    assert stale_row["source_actor_count"] == 5
    assert stale_row["actual_actor_count_delta"] == 1
    assert stale_row["actual_actor_count"] == 6
    assert stale_row["predicted_actor_count"] == 5
    assert stale_row["actual_spawn_cells"] != real_good_row["actual_spawn_cells"]
    assert stale_row["simulation_passed"] is False
    assert "predicted_state_actor_count_mismatch" in stale_row["findings"]

    transition_path = bundle / "state_transitions.json"
    transitions = json.loads(transition_path.read_text(encoding="utf-8"))
    transition = transitions["state_transitions"][0]
    transition["predicted_state"]["actor_count"] = stale_row["actual_actor_count"]
    transition["transition_diff"]["spawn_cells"] = stale_row["actual_spawn_cells"]
    transition_path.write_text(
        json.dumps(transitions, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    updated_expected = run_simulation_bundle(
        bundle,
        receipt_root / "updated_expected",
        command="pytest",
    )
    updated_rows = {
        row["replay_id"]: row
        for row in updated_expected["state_transition_analysis"]["transition_rows"]
    }
    updated_row = updated_rows[replay_id]
    assert updated_expected["status"] == "pass"
    assert updated_row["simulation_passed"] is True
    assert updated_row["source_actor_count"] == 5
    assert updated_row["actual_actor_count"] == 6
    assert updated_row["actual_spawn_cells"] == stale_row["actual_spawn_cells"]


def test_spatial_world_model_simulation_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    out_dir = tmp_path / "spatial-card"
    argv = [
        "run-simulation-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out_dir),
        "--card",
    ]

    assert main(argv) == 0
    first_card = json.loads(capsys.readouterr().out)

    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_checked_path_count"] == 12
    assert first_card["simulation"]["replay_count"] == 6
    assert first_card["simulation"]["state_transition_count"] == 6
    assert first_card["simulation"]["predicted_state_body_count"] == 6
    assert first_card["simulation"]["deterministic_simulation_pass_count"] == 6
    assert first_card["simulation"]["gridworld_step_count"] == 6
    assert first_card["simulation"]["predicted_actual_match_count"] == 6
    assert first_card["source_modules"]["module_count"] == len(
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert first_card["source_modules"]["body_material_count"] == len(
        SPATIAL_SOURCE_BODY_MATERIAL_IDS
    )
    assert (
        first_card["source_modules"]["body_text_exported_in_receipts"] is False
    )
    assert first_card["validation"]["finding_count"] == 0
    assert first_card["validation"]["secret_exclusion_hit_count"] == 0
    assert "counterfactual_replays" not in first_card
    assert "scene_states" not in first_card

    def fail_if_uncached(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("fresh card path should reuse the receipt")

    monkeypatch.setattr(
        spatial_world_model_counterfactual_simulation_replay,
        "_build_result",
        fail_if_uncached,
    )

    assert main(argv) == 0
    cached_card = json.loads(capsys.readouterr().out)

    assert cached_card["schema_version"] == CARD_SCHEMA_VERSION
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
