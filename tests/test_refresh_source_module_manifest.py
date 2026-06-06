from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


SUBSTRATE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SUBSTRATE_ROOT / "scripts" / "refresh_source_module_manifest.py"


def _load_refresh_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "refresh_source_module_manifest", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_manifest(
    public_root: Path,
    *,
    module_id: str,
    source_ref: str,
    target_ref: str,
) -> Path:
    manifest_path = public_root / "examples/demo/source_module_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    target_path_ref = target_ref.removeprefix("microcosm-substrate/examples/demo/")
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_id": "demo_source_body_imports",
                "modules": [
                    {
                        "module_id": module_id,
                        "path": target_path_ref,
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "source_to_target_relation": "exact_copy",
                        "body_copied": True,
                        "body_in_receipt": False,
                        "body_text_in_receipt": False,
                        "material_class": "public_macro_tool_body",
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return manifest_path


def test_refresh_manifest_resolves_substrate_local_src_refs(tmp_path: Path) -> None:
    refresh_module = _load_refresh_module()
    public_root = tmp_path / "microcosm-substrate"
    source_ref = "src/microcosm_core/organs/demo.py"
    target_ref = (
        "microcosm-substrate/examples/demo/source_modules/microcosm_core/organs/demo.py"
    )
    source_path = public_root / source_ref
    target_path = public_root / target_ref.removeprefix("microcosm-substrate/")
    source_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text('ORGAN_ID = "demo"\n\ndef run():\n    return "pass"\n')
    target_path.write_bytes(source_path.read_bytes())
    manifest_path = _write_manifest(
        public_root,
        module_id="demo_source_body_import",
        source_ref=source_ref,
        target_ref=target_ref,
    )

    result = refresh_module.refresh_manifest(
        manifest_path,
        module_ids={"demo_source_body_import"},
        write=False,
    )

    assert result["status"] == "pass"
    assert result["finding_count"] == 0
    assert result["rows"][0]["digest_match"] is True
    assert result["rows"][0]["source_ref"] == source_ref


def test_refresh_manifest_keeps_repo_root_tool_refs(tmp_path: Path) -> None:
    refresh_module = _load_refresh_module()
    repo_root = tmp_path / "repo"
    public_root = repo_root / "microcosm-substrate"
    source_ref = "tools/meta/factory/demo_tool.py"
    target_ref = "microcosm-substrate/examples/demo/source_modules/tools/meta/factory/demo_tool.py"
    source_path = repo_root / source_ref
    target_path = public_root / target_ref.removeprefix("microcosm-substrate/")
    source_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("def main():\n    return 0\n")
    target_path.write_bytes(source_path.read_bytes())
    manifest_path = _write_manifest(
        public_root,
        module_id="demo_tool_body_import",
        source_ref=source_ref,
        target_ref=target_ref,
    )

    result = refresh_module.refresh_manifest(
        manifest_path,
        module_ids={"demo_tool_body_import"},
        write=False,
    )

    assert result["status"] == "pass"
    assert result["finding_count"] == 0
    assert result["rows"][0]["digest_match"] is True
    assert result["rows"][0]["source_ref"] == source_ref


def test_refresh_manifest_public_safe_normalize_writes_transformed_target(tmp_path: Path) -> None:
    refresh_module = _load_refresh_module()
    repo_root = tmp_path / "repo"
    public_root = repo_root / "microcosm-substrate"
    source_ref = "tools/meta/bridge/demo_transport.py"
    target_ref = "microcosm-substrate/examples/demo/source_modules/demo.py"
    source_path = repo_root / source_ref
    target_path = public_root / target_ref.removeprefix("microcosm-substrate/")
    raw_seed_root = "obsidian/" + "okay lets do this"
    transport_symbol = "claude" + "_app_injector"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        f"TRACE_ROOT = {raw_seed_root!r}\nTRANSPORT = {transport_symbol!r}\n",
        encoding="utf-8",
    )
    manifest_path = _write_manifest(
        public_root,
        module_id="demo_public_safe_normalized_import",
        source_ref=source_ref,
        target_ref=target_ref,
    )

    result = refresh_module.refresh_manifest(
        manifest_path,
        module_ids={"demo_public_safe_normalized_import"},
        write=True,
        public_safe_normalize=True,
    )

    target_text = target_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    transform = row["public_safe_transform"]

    assert result["status"] == "pass"
    assert result["public_safe_normalize"] is True
    assert result["rows"][0]["source_to_target_relation"] == (
        "source_faithful_public_safe_path_normalized_copy"
    )
    assert result["rows"][0]["source_target_digest_match"] is False
    assert result["rows"][0]["target_expected_digest_match"] is True
    assert raw_seed_root not in target_text
    assert transport_symbol not in target_text
    assert "<private-raw-seed-root>" in target_text
    assert "<private-browser-transport-symbol>" in target_text
    assert row["source_to_target_relation"] == "source_faithful_public_safe_path_normalized_copy"
    assert row["public_safe_mode"] == "verified_public_macro_body_light_edit"
    assert row["public_safety_transformations"] == [
        "private raw-seed or vault roots replaced with <private-raw-seed-root> public-safe boundary tokens",
        "private browser transport symbols replaced with <private-browser-transport-symbol> public-safe boundary tokens",
    ]
    assert row["source_target_sha256_match"] is False
    assert row["sha256_match"] is True
    assert transform["public_safe"] is True
    assert transform["replacement_count"] == 2
    assert "text" not in transform
    assert raw_seed_root not in str(transform)
    assert transport_symbol not in str(transform)


def test_refresh_manifest_public_safe_normalize_rewrites_private_macro_source_refs(
    tmp_path: Path,
) -> None:
    refresh_module = _load_refresh_module()
    repo_root = tmp_path / "repo"
    public_root = repo_root / "microcosm-substrate"
    private_macro_root = "self-indexing-" + "cognitive-substrate"
    raw_seed_root = "obsidian/" + "okay lets do this"
    source_ref = f"{private_macro_root}/microcosms/demo/specimen.py"
    target_ref = "microcosm-substrate/examples/demo/source_modules/specimen.py"
    source_path = repo_root / source_ref
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        f"TRACE_ROOT = {raw_seed_root!r}\n",
        encoding="utf-8",
    )
    manifest_path = _write_manifest(
        public_root,
        module_id="demo_private_macro_body_import",
        source_ref=source_ref,
        target_ref=target_ref,
    )
    bundle_manifest_path = manifest_path.parent / "bundle_manifest.json"
    bundle_manifest_path.write_text(
        json.dumps(
            {
                "bundle_id": "demo_private_macro_bundle",
                "source_root": f"{private_macro_root}/microcosms/demo",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = refresh_module.refresh_manifest(
        manifest_path,
        module_ids={"demo_private_macro_body_import"},
        write=True,
        public_safe_normalize=True,
    )

    target_text = (
        public_root / target_ref.removeprefix("microcosm-substrate/")
    ).read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]

    assert result["status"] == "pass"
    assert result["bundle_manifest_public_safe_transform"]["status"] == "transformed"
    assert result["bundle_manifest_public_safe_transform"]["write_applied"] is True
    assert row["source_ref"] == "private-macro-source/microcosms/demo/specimen.py"
    assert row["source_ref_public_safe_transform"]["public_safe"] is True
    assert bundle_manifest["source_root"] == "private-macro-source/microcosms/demo"
    assert bundle_manifest["source_root_public_safe_transform"]["public_safe"] is True
    assert row["source_to_target_relation"] == (
        "source_faithful_public_safe_path_normalized_copy"
    )
    assert private_macro_root not in json.dumps(manifest, sort_keys=True)
    assert private_macro_root not in json.dumps(bundle_manifest, sort_keys=True)
    assert raw_seed_root not in target_text
    assert "<private-raw-seed-root>" in target_text

    reread = refresh_module.refresh_manifest(
        manifest_path,
        module_ids={"demo_private_macro_body_import"},
        write=False,
        public_safe_normalize=True,
    )

    assert reread["status"] == "pass"
    assert reread["rows"][0]["source_ref"] == row["source_ref"]


def test_refresh_manifest_repairs_stale_public_copy_self_ref_with_original_source(
    tmp_path: Path,
) -> None:
    refresh_module = _load_refresh_module()
    repo_root = tmp_path / "repo"
    public_root = repo_root / "microcosm-substrate"
    source_ref = "tools/meta/factory/demo_atlas.py"
    target_ref = (
        "microcosm-substrate/examples/demo/source_modules/tools/meta/factory/demo_atlas.py"
    )
    source_path = repo_root / source_ref
    target_path = public_root / target_ref.removeprefix("microcosm-substrate/")
    raw_seed_root = "obsidian/" + "okay lets do this"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        f"BUILDER_ID = {source_ref!r}\nTRACE_ROOT = {raw_seed_root!r}\n",
        encoding="utf-8",
    )
    target_path.write_text(
        "BUILDER_ID = 'tools/meta/factory/demo_atlas.py'\n"
        "TRACE_ROOT = '<private-raw-seed-root>'\n",
        encoding="utf-8",
    )
    manifest_path = _write_manifest(
        public_root,
        module_id="demo_atlas_public_safe_body_import",
        source_ref=target_ref,
        target_ref=target_ref,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0].pop("module_id")
    manifest["modules"][0]["original_source_ref"] = source_ref
    manifest["modules"][0]["source_to_target_relation"] = (
        "public_bound_sanitized_source_authority_self_ref"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = refresh_module.refresh_manifest(
        manifest_path,
        module_ids=set(),
        write=True,
        public_safe_normalize=True,
    )

    target_text = target_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]

    assert result["status"] == "pass"
    assert result["rows"][0]["source_ref"] == source_ref
    assert result["rows"][0]["module_id"] == "demo_atlas_public_safe_body_import"
    assert result["rows"][0]["source_ref_repair"] == {
        "source_ref_repaired_from": target_ref,
        "source_ref_repair_basis": (
            "original_source_ref_for_stale_copied_target_self_reference"
        ),
    }
    assert row["module_id"] == "demo_atlas_public_safe_body_import"
    assert row["source_ref"] == source_ref
    assert row["source_ref_repaired_from"] == target_ref
    assert row["source_to_target_relation"] == (
        "source_faithful_public_safe_path_normalized_copy"
    )
    assert row["source_target_sha256_match"] is False
    assert row["target_expected_digest_match"] is True
    assert raw_seed_root not in target_text
    assert "<private-raw-seed-root>" in target_text
