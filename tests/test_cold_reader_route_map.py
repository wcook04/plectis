from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.organs.cold_reader_route_map as cold_reader_route_map
from microcosm_core import cli
from microcosm_core.organs.cold_reader_route_map import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_route_map_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/cold_reader_route_map/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle"
)
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"
# Copied non-secret macro bodies carried verbatim into the exported bundle's
# `modules` list. The kernel command body (`comprehension_snapshot.py`) is a
# private source: on export the firewall substitutes it with a public-safe stub
# and records it under `release_substitution_omissions`, so it is NOT a copied
# source module and is intentionally absent here.
COLD_READER_SOURCE_MODULE_IDS = {
    "agent_instruction_router_body_import",
    "agent_entry_reference_body_import",
    "kernel_bootstrap_skill_body_import",
    "kernel_navigation_seed_skill_body_import",
}


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


def _public_ref_path(ref: str) -> Path:
    return Path(ref.partition("#")[0].removeprefix("microcosm-substrate/"))


def _copy_public_route_replay_refs(public_root: Path, input_dir: Path) -> None:
    route_map = json.loads((input_dir / "route_map.json").read_text(encoding="utf-8"))
    route_receipts = json.loads(
        (input_dir / "route_receipts.json").read_text(encoding="utf-8")
    )
    refs = {
        *cold_reader_route_map.ROUTE_SOURCE_REPLAY_PUBLIC_REFS,
        *(
            ref
            for row in route_map["routes"]
            for ref in row.get("docs_refs", [])
            if isinstance(ref, str)
        ),
        *(
            ref
            for row in route_receipts["route_receipts"]
            for ref in row.get("receipt_refs", [])
            if isinstance(ref, str)
        ),
    }
    for ref in sorted(refs):
        relative = _public_ref_path(ref)
        if not str(relative) or relative.is_absolute() or ".." in relative.parts:
            continue
        source = MICROCOSM_ROOT / relative
        target = public_root / relative
        if not source.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def test_cold_reader_route_map_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/cold_reader_route_map",
        command="pytest",
        acceptance_out=(
            tmp_path
            / "receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json"
        ),
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["route_count"] == 10
    assert result["command_count"] == 10
    assert result["receipt_ref_count"] >= 10
    assert result["first_run_sequence"][:3] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert result["front_door_route_ids"] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert result["front_door_command_count"] == 3
    assert result["authority_ceiling"]["route_registry_authority"] is False
    assert result["route_source_replay"]["status"] == "pass"
    assert result["route_source_replay"]["supported_route_count"] == 10
    assert result["route_source_replay"]["resolved_docs_ref_count"] == 20
    assert result["route_source_replay"]["resolved_pass_receipt_ref_count"] == 10
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_cold_reader_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_route_map_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_cold_reader_route_map_bundle"
    assert result["bundle_id"] == "public_cold_reader_route_map_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["covered_route_ids"] == [
        "compile_project",
        "inspect_cold_reader_route_map",
        "inspect_public_spine",
        "inspect_route",
        "open_import_bridge",
        "open_observatory",
        "open_reveal_board",
        "proof_lab",
        "status_card",
        "tour_project",
    ]
    assert result["first_run_sequence"][:3] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert result["front_door_command_count"] == 3
    route_source_replay = result["route_source_replay"]
    assert route_source_replay["status"] == "pass"
    assert route_source_replay["route_count"] == 10
    assert route_source_replay["supported_route_count"] == 10
    assert route_source_replay["docs_ref_count"] == 20
    assert route_source_replay["resolved_docs_ref_count"] == 20
    assert route_source_replay["receipt_ref_count"] == 10
    assert route_source_replay["resolved_pass_receipt_ref_count"] == 10
    assert all(row["status"] == "pass" for row in route_source_replay["rows"])
    assert "microcosm-substrate/src/microcosm_core/runtime_shell.py" in result["source_refs"]
    assert "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle" in result[
        "public_runtime_refs"
    ]
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert result["copied_source_module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert set(row["module_id"] for row in result["source_module_results"]) == (
        COLD_READER_SOURCE_MODULE_IDS
    )
    assert all(row["digest_match"] for row in result["source_module_results"])
    assert all(row["anchor_status"] == "pass" for row in result["source_module_results"])
    assert "docs/agent_instruction_router.md" in result["real_substrate_refs"]
    # The kernel command body is a private source substituted with a public-safe
    # stub on export (release_substitution_omissions), so it is not a copied
    # macro body and must not surface among the real substrate refs.
    assert not any(
        "comprehension_snapshot.py" in ref for ref in result["real_substrate_refs"]
    )
    verification = result["body_import_verification"]
    expected_digests = sorted(
        f"sha256:{row['source_sha256']}" for row in result["source_module_results"]
    )
    assert verification["verification_status"] == "pass"
    assert verification["verification_mode"] == (
        "exact_source_digest_match_plus_required_anchor_check"
    )
    assert verification["source_to_target_relation"] == "exact_copy"
    assert verification["digest_relation"] == "source_target_digest_sets_match"
    assert verification["source_module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert verification["copied_source_module_count"] == len(
        COLD_READER_SOURCE_MODULE_IDS
    )
    assert verification["source_body_digests"] == expected_digests
    assert verification["target_body_digests"] == expected_digests
    assert verification["source_refs"] == sorted(
        {row["source_ref"] for row in result["source_module_results"]}
    )
    assert verification["target_refs"] == result["source_module_refs"]
    assert verification["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)


def test_cold_reader_exported_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    _copy_public_route_replay_refs(public_root, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_route_map_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "COLD_ROUTE_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    mismatch_rows = [
        row for row in result["source_module_results"] if not row["digest_match"]
    ]
    assert [row["module_id"] for row in mismatch_rows] == [
        "agent_instruction_router_body_import"
    ]


def test_cold_reader_exported_bundle_rejects_unsupported_route_command(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    _copy_public_route_replay_refs(public_root, bundle)
    route_map_path = bundle / "route_map.json"
    route_map = json.loads(route_map_path.read_text(encoding="utf-8"))
    for row in route_map["routes"]:
        if row["route_id"] == "open_import_bridge":
            row["command"] = "microcosm hallucinated-import"
    route_map_path.write_text(
        json.dumps(route_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_route_map_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "COLD_ROUTE_COMMAND_SOURCE_UNSUPPORTED" in result["error_codes"]
    replay_row = next(
        row
        for row in result["route_source_replay"]["rows"]
        if row["route_id"] == "open_import_bridge"
    )
    assert replay_row["status"] == "blocked"
    assert replay_row["command_support"]["status"] == "blocked"


def test_cold_reader_exported_bundle_rejects_stale_docs_anchor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    _copy_public_route_replay_refs(public_root, bundle)
    route_map_path = bundle / "route_map.json"
    route_map = json.loads(route_map_path.read_text(encoding="utf-8"))
    route_map["routes"][0]["docs_refs"][0] = "README.md#not-a-real-heading"
    route_map_path.write_text(
        json.dumps(route_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_route_map_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "COLD_ROUTE_DOC_REF_ANCHOR_MISSING" in result["error_codes"]
    replay_row = next(
        row
        for row in result["route_source_replay"]["rows"]
        if row["route_id"] == "tour_project"
    )
    assert replay_row["status"] == "blocked"
    assert replay_row["docs_ref_results"][0]["status"] == "blocked"


def test_cold_reader_exported_bundle_rejects_non_pass_receipt_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    _copy_public_route_replay_refs(public_root, bundle)
    route_receipts = json.loads(
        (bundle / "route_receipts.json").read_text(encoding="utf-8")
    )
    proof_lab_receipt = next(
        row["receipt_refs"][0]
        for row in route_receipts["route_receipts"]
        if row["route_id"] == "proof_lab"
    )
    receipt_path = public_root / _public_ref_path(proof_lab_receipt)
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["status"] = "blocked"
    receipt_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_route_map_bundle(
        bundle,
        public_root / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "COLD_ROUTE_RECEIPT_STATUS_UNSUPPORTED" in result["error_codes"]
    replay_row = next(
        row
        for row in result["route_source_replay"]["rows"]
        if row["route_id"] == "proof_lab"
    )
    assert replay_row["status"] == "blocked"
    assert replay_row["receipt_ref_results"][0]["status"] == "blocked"
    assert replay_row["receipt_ref_results"][0]["receipt_status"] == "blocked"


def test_cold_reader_line_count_streams_without_materializing_file(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    empty_source = tmp_path / "empty_source.py"
    source.write_text("one\n\ntwo", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    guarded_paths = {source, empty_source}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert cold_reader_route_map._line_count(source) == 3
    assert cold_reader_route_map._line_count(empty_source) == 1


def test_cold_reader_sha256_streams_without_materializing_file(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    marker = b"cold-reader-route-map-source-module\n"
    body = (
        marker * (cold_reader_route_map.HASH_CHUNK_SIZE // len(marker) + 2)
    ) + b"tail\n"
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == source:
            raise AssertionError("digest should stream source-module input")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert cold_reader_route_map._sha256(source) == hashlib.sha256(body).hexdigest()


def test_cold_reader_source_module_import_reuses_anchor_text_for_line_count(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fail_line_count(_path: Path) -> int:
        raise AssertionError("source-module line count should reuse anchor text")

    monkeypatch.setattr(cold_reader_route_map, "_line_count", fail_line_count)

    result = run_route_map_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert all(
        row["target_line_count"] == row["source_line_count"]
        for row in result["source_module_results"]
    )


def test_cold_reader_source_manifest_matches_exported_body_floor() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert set(row["module_id"] for row in manifest["modules"]) == (
        COLD_READER_SOURCE_MODULE_IDS
    )
    assert [
        row["module_id"] for row in manifest["release_substitution_omissions"]
    ] == ["kernel_entry_packet_command_body_import"]
    for row in manifest["modules"]:
        source_ref = Path(row["source_ref"])
        target = MICROCOSM_ROOT / Path(row["target_ref"]).relative_to(
            "microcosm-substrate"
        )
        assert not source_ref.is_absolute()
        assert ".." not in source_ref.parts
        assert target.is_file(), row["target_ref"]
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        assert row["source_to_target_relation"] == "exact_copy"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        for anchor in row["required_anchors"]:
            assert anchor in target.read_text(encoding="utf-8")


def test_cold_reader_bundle_manifest_counts_only_copied_source_modules() -> None:
    bundle_manifest = json.loads(
        (BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    source_manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    copied_refs = {row["target_ref"] for row in source_manifest["modules"]}

    assert bundle_manifest["copied_source_module_count"] == len(
        COLD_READER_SOURCE_MODULE_IDS
    )
    assert set(bundle_manifest["copied_source_module_refs"]) == copied_refs
    assert not any(
        "comprehension_snapshot.py" in ref
        for ref in bundle_manifest["copied_source_module_refs"]
    )
    assert [
        row["module_id"] for row in source_manifest["release_substitution_omissions"]
    ] == ["kernel_entry_packet_command_body_import"]


def test_cold_reader_fixture_manifest_counts_source_open_body_floor() -> None:
    manifest = json.loads(
        (MICROCOSM_ROOT / "core/fixture_manifests/cold_reader_route_map.fixture_manifest.json")
        .read_text(encoding="utf-8")
    )

    source_imports = manifest["source_open_body_imports"]
    assert manifest["body_copied_material_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert source_imports["status"] == "pass"
    assert source_imports["source_import_class"] == "copied_non_secret_macro_body"
    assert source_imports["body_material_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert set(source_imports["body_material_ids"]) == COLD_READER_SOURCE_MODULE_IDS
    assert source_imports["body_in_receipt"] is False
    assert (
        source_imports["aggregate_floor_ref"]
        == "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle/source_module_manifest.json::modules"
    )


def test_cold_reader_receipts_are_public_relative_with_secret_exclusion(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/cold_reader_route_map",
        public_root / "fixtures/first_wave/cold_reader_route_map",
    )
    _copy_public_route_replay_refs(
        public_root, public_root / "fixtures/first_wave/cold_reader_route_map/input"
    )
    result = run(
        public_root / "fixtures/first_wave/cold_reader_route_map/input",
        public_root / "receipts/first_wave/cold_reader_route_map",
        command="pytest",
        acceptance_out=(
            public_root
            / "receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json"
        ),
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in _walk_keys(payload)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_cold_reader_exported_bundle_receipt_omits_source_bodies(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        BUNDLE_INPUT,
        public_root / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
    )
    _copy_public_route_replay_refs(
        public_root,
        public_root / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
    )
    result = run_route_map_bundle(
        public_root / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["source_module_manifest_status"] == "pass"
        assert payload["source_module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_import_verification"]["body_in_receipt"] is False
        assert "body_redacted" not in _walk_keys(payload)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_cold_reader_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out_dir = tmp_path / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map"
    args = [
        "run-route-map-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out_dir),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    receipt_path = out_dir / BUNDLE_RESULT_NAME
    assert receipt_path.is_file()
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["cache_status"] == "rebuilt"
    assert first_card["route_map"]["route_count"] == 10
    assert first_card["route_map"]["first_run_sequence_head"] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert first_card["source_import_floor"]["source_module_count"] == len(
        COLD_READER_SOURCE_MODULE_IDS
    )
    assert first_card["output_economy"]["source_bodies_exported"] is False
    assert "source_module_results" in first_card["output_economy"]["omitted_payload_keys"]

    def fail_build(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the written receipt")

    monkeypatch.setattr(cold_reader_route_map, "_build_result", fail_build)

    assert main(args) == 0
    cached_stdout = capsys.readouterr().out
    cached_card = json.loads(cached_stdout)
    assert cached_card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert cached_card["freshness_basis"]["missing_path_count"] == 0
    assert cached_card["route_map"]["front_door_command_count"] == 3
    assert len(cached_stdout.encode("utf-8")) < receipt_path.stat().st_size


def test_cold_reader_bundle_card_is_available_from_top_level_cli(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map"

    assert (
        cli.main(
            [
                "cold-reader-route-map",
                "run-route-map-bundle",
                "--input",
                str(BUNDLE_INPUT),
                "--out",
                str(out_dir),
                "--card",
            ]
        )
        == 0
    )
    card = json.loads(capsys.readouterr().out)

    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["route_map"]["route_count"] == 10
    assert card["output_economy"]["source_bodies_exported"] is False
