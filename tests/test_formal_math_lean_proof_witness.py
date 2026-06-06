from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import microcosm_core.organs.formal_math_lean_proof_witness as witness_module
from microcosm_core.organs.formal_math_lean_proof_witness import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_witness_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/formal_math_lean_proof_witness/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle"
)


def _copy_exported_bundle_public_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_lean_proof_witness",
        public_root / "fixtures/first_wave/formal_math_lean_proof_witness",
    )
    source_file = public_root / "src/microcosm_core/organs/formal_math_lean_proof_witness.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        MICROCOSM_ROOT / "src/microcosm_core/organs/formal_math_lean_proof_witness.py",
        source_file,
    )
    shutil.copytree(
        BUNDLE_INPUT,
        public_root
        / "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle",
    )
    return public_root


def _public_path(ref: str) -> Path:
    return MICROCOSM_ROOT / ref.removeprefix("microcosm-substrate/")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def lean_witness_public_root_run(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], Path]:
    root = tmp_path_factory.mktemp("lean_witness_fixture_public_root")
    public_root = root / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_lean_proof_witness",
        public_root / "fixtures/first_wave/formal_math_lean_proof_witness",
    )
    result = run(
        public_root / "fixtures/first_wave/formal_math_lean_proof_witness/input",
        public_root / "receipts/first_wave/formal_math_lean_proof_witness",
        command="pytest",
        acceptance_out=public_root
        / "receipts/acceptance/first_wave/formal_math_lean_proof_witness_fixture_acceptance.json",
    )
    return result, public_root


@pytest.fixture(scope="module")
def lean_witness_fixture_run(
    lean_witness_public_root_run: tuple[dict[str, Any], Path],
) -> dict[str, Any]:
    result, _public_root = lean_witness_public_root_run
    return result


@pytest.fixture(scope="module")
def lean_witness_bundle_card_run(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], Path, list[str], str]:
    root = tmp_path_factory.mktemp("lean_witness_bundle")
    out = root / "receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness"
    argv = [
        "run-witness-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out),
        "--card",
    ]
    command = (
        "python -m microcosm_core.organs.formal_math_lean_proof_witness "
        f"run-witness-bundle --input {BUNDLE_INPUT} --out {out} --card"
    )
    result = run_witness_bundle(BUNDLE_INPUT, out, command=command)
    return result, out, argv, command


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


def test_formal_math_lean_proof_witness_input_scan_streams_project_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    project_dir = input_dir / "lake_project"
    nested = project_dir / "MicrocosmProofWitness"
    nested.mkdir(parents=True)
    (input_dir / "witness_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmProofWitness.Basic\n",
        encoding="utf-8",
    )
    (nested / "Basic.lean").write_text(
        "theorem t : True := by trivial\n",
        encoding="utf-8",
    )
    (nested / "notes.md").write_text("public notes\n", encoding="utf-8")
    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == project_dir:
            raise AssertionError("Lean project scan should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    assert [
        path.relative_to(input_dir).as_posix()
        for path in witness_module._input_paths(input_dir, include_negative=False)
    ] == [
        "witness_manifest.json",
        "lake_project/lakefile.lean",
        "lake_project/MicrocosmProofWitness/Basic.lean",
        "lake_project/lakefile.lean",
    ]


def test_formal_math_lean_proof_witness_project_scan_recurses_before_root_sibling(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project_dir = tmp_path / "lake_project"
    nested_opened = {"value": False}

    class FakeEntry:
        def __init__(self, name: str, *, is_dir: bool = False, is_file: bool = False) -> None:
            self.name = name
            self._is_dir = is_dir
            self._is_file = is_file

        def is_dir(self, *, follow_symlinks: bool = True) -> bool:
            return self._is_dir

        def is_file(self, *, follow_symlinks: bool = True) -> bool:
            return self._is_file

    class FakeScandir:
        def __init__(self, path: Path, entries: list[FakeEntry]) -> None:
            self.path = path
            self.entries = entries

        def __enter__(self) -> "FakeScandir":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> Any:
            for index, entry in enumerate(self.entries):
                if self.path == project_dir and index == 1 and not nested_opened["value"]:
                    raise AssertionError("Lean project scan should recurse before root siblings")
                yield entry

    def fake_scandir(path: Path) -> FakeScandir:
        path = Path(path)
        if path == project_dir:
            return FakeScandir(
                path,
                [
                    FakeEntry("MicrocosmProofWitness", is_dir=True),
                    FakeEntry("lakefile.lean", is_file=True),
                ],
            )
        if path == project_dir / "MicrocosmProofWitness":
            nested_opened["value"] = True
            return FakeScandir(path, [FakeEntry("Basic.lean", is_file=True)])
        raise AssertionError(f"unexpected scandir path: {path}")

    class FakeOs:
        scandir = staticmethod(fake_scandir)

    monkeypatch.setattr(witness_module, "os", FakeOs)

    refs = [
        path.relative_to(project_dir).as_posix()
        for path in witness_module._iter_lean_project_files(project_dir)
    ]

    assert refs == ["MicrocosmProofWitness/Basic.lean", "lakefile.lean"]


def test_formal_math_lean_proof_witness_sha256_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source_file = tmp_path / "large_witness.lean"
    body = (
        b"theorem microcosm_streaming_witness : True := by trivial\n"
        * (witness_module.HASH_CHUNK_SIZE // 32)
    )
    source_file.write_bytes(body)
    expected = hashlib.sha256(body).hexdigest()

    def fail_read_bytes(self: Path) -> bytes:
        raise AssertionError("_sha256 should stream bytes instead of materializing")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    assert witness_module._sha256(source_file) == expected
    assert witness_module._sha256_file(source_file) == f"sha256:{expected}"


def test_formal_math_lean_proof_witness_caches_tool_version_probes(
    monkeypatch: Any,
) -> None:
    which_calls: list[str] = []

    def fake_which(name: str) -> str | None:
        which_calls.append(name)
        return f"/tmp/fake-{name}" if name in {"lean", "lake"} else None

    def fail_run_command(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("tool version metadata should not spawn subprocesses")

    monkeypatch.setattr(witness_module, "_TOOL_VERSION_CACHE", None)
    monkeypatch.setattr(witness_module.shutil, "which", fake_which)
    monkeypatch.setattr(witness_module, "_run_command", fail_run_command)

    first = witness_module._tool_versions()
    first["lean_available"] = False
    second = witness_module._tool_versions()

    assert which_calls == ["lean", "lake"]
    assert second["lean_available"] is True
    assert second["lake_version_command"]["skipped"] is True
    assert second["lean_version_command"]["skip_reason"] == "version_probe_skipped_hot_path"
    assert second["lean_version_command"]["tool_path_available"] is True
    assert "tool_path" not in second["lean_version_command"]


def test_formal_math_lean_proof_witness_reuses_built_lake_project_cache(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    project_dir = input_dir / "lake_project"
    nested = project_dir / "MicrocosmProofWitness"
    nested.mkdir(parents=True)
    (project_dir / "lakefile.lean").write_text(
        "import MicrocosmProofWitness.Basic\n",
        encoding="utf-8",
    )
    lean_file = nested / "Basic.lean"
    lean_file.write_text("theorem witness_smoke : True := by trivial\n", encoding="utf-8")
    monkeypatch.setattr(witness_module, "_LAKE_PROJECT_BUILD_CACHE", {})
    monkeypatch.setattr(witness_module, "_LAKE_PROJECT_BUILD_CACHE_HOLDERS", [])

    first_root = tmp_path / "first"
    first_root.mkdir()
    first_project = witness_module._copy_project_to_temp(input_dir, first_root)
    build_marker = first_project / ".lake/build.stamp"
    build_marker.parent.mkdir(parents=True)
    build_marker.write_text("built\n", encoding="utf-8")
    witness_module._remember_built_lake_project(input_dir, first_project)

    second_root = tmp_path / "second"
    second_root.mkdir()
    second_project = witness_module._copy_project_to_temp(input_dir, second_root)

    assert (second_project / ".lake/build.stamp").read_text(encoding="utf-8") == "built\n"
    lean_file.write_text(
        "theorem witness_smoke_changed : True := by trivial\n",
        encoding="utf-8",
    )
    third_root = tmp_path / "third"
    third_root.mkdir()
    third_project = witness_module._copy_project_to_temp(input_dir, third_root)
    assert not (third_project / ".lake/build.stamp").exists()


def test_formal_math_lean_proof_witness_builds_and_observes_negative_cases(
    lean_witness_fixture_run: dict[str, Any],
) -> None:
    result = lean_witness_fixture_run

    assert result["status"] == "pass"
    assert result["lake_build"]["argv"] == ["lake", "build", "MicrocosmProofWitness"]
    assert result["lake_build"]["return_code"] == 0
    assert result["lake_build"]["timeout_seconds"] == 90
    assert result["tool_versions"]["lean_version_command"]["timeout_seconds"] == 30
    assert result["tool_versions"]["lake_version_command"]["timeout_seconds"] == 30
    assert result["compiled_declaration_count"] == 8
    assert result["validator_cache_version"].endswith("source_module_scan")
    assert result["private_state_scan"]["scanned_path_count"] >= 8
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is True
    assert result["authority_ceiling"]["proof_bodies_allowed_in_receipts"] is False
    assert result["authority_ceiling"]["mathlib_presence_claim_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_lean_proof_witness_receipts_are_public_relative_and_redacted(
    lean_witness_public_root_run: tuple[dict[str, Any], Path],
) -> None:
    result, public_root = lean_witness_public_root_run

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "Mathlib" not in text or "FORBIDDEN_IMPORT" in text
        assert "by rfl" not in text
        assert '"proof_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert "proof_body" not in _walk_keys(payload)


def test_formal_math_lean_proof_witness_exported_bundle_validates_runtime_shape(
    lean_witness_bundle_card_run: tuple[dict[str, Any], Path, list[str], str],
) -> None:
    result, _target, _argv, _command = lean_witness_bundle_card_run

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_lean_proof_witness_bundle"
    assert result["bundle_id"] == "formal_math_lean_proof_witness_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["compiled_declaration_count"] == 8
    assert result["validator_cache_version"].endswith("source_module_scan")
    assert result["private_state_scan"]["scanned_path_count"] >= 6
    assert result["source_module_imports"]["status"] == "pass"
    assert result["source_module_imports"]["module_count"] == 5
    assert any(
        module["material_class"] == "public_python_source_body"
        and module["source_ref"]
        == "microcosm-substrate/src/microcosm_core/organs/formal_math_lean_proof_witness.py"
        for module in result["source_module_imports"]["modules"]
    )
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 5
    assert result["body_copied_material_count"] == 5
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["lean_witness_board"]["lean_lake_execution_authorized"] is True
    assert result["lean_witness_board"]["mathlib_authorized"] is False


def test_formal_math_lean_proof_witness_exported_bundle_uses_standalone_contract(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def fail_command(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("exported witness bundle should not spawn Lean or Lake")

    monkeypatch.setattr(witness_module, "_run_command", fail_command)

    result = run_witness_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness",
        command="pytest standalone exported lean proof witness",
    )

    assert result["status"] == "pass"
    assert result["execution_witness_mode"] == "standalone_exported_witness_contract"
    assert result["tool_versions"]["standalone_exported_witness_contract"] is True
    assert result["lake_build"]["skipped"] is True
    assert result["lake_build"]["skip_reason"] == "standalone_exported_witness_contract"
    assert result["compiled_declaration_count"] == 8
    assert result["source_module_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 5
    assert result["private_state_scan"]["blocking_hit_count"] == 0


def test_formal_math_lean_proof_witness_source_module_manifest_exact_copy_floor() -> None:
    manifest_path = BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_imports = witness_module.validate_source_module_imports(
        BUNDLE_INPUT,
        public_root=MICROCOSM_ROOT,
    )

    assert manifest["source_import_class"] == "copied_non_secret_formal_math_witness_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 5
    assert source_imports["status"] == "pass"
    assert source_imports["module_count"] == 5

    allowed_source_prefixes = (
        "microcosm-substrate/fixtures/first_wave/formal_math_lean_proof_witness/input/",
        "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/",
        "microcosm-substrate/src/microcosm_core/organs/",
    )
    for row in manifest["modules"]:
        source_ref = str(row["source_ref"])
        source_path = _public_path(source_ref)
        target_path = _public_path(str(row["target_ref"]))
        source_sha256 = _file_sha256(source_path)
        target_sha256 = _file_sha256(target_path)

        assert source_ref.startswith(allowed_source_prefixes)
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["sha256"] == f"sha256:{target_sha256}"
        assert row["source_sha256"] == source_sha256
        assert row["target_sha256"] == target_sha256
        if row["source_to_target_relation"] == "exact_copy":
            assert row["sha256_match"] is True
            assert source_path.read_bytes() == target_path.read_bytes()
            assert source_sha256 == target_sha256
        elif row["source_to_target_relation"] == "public_replacement_source_body":
            assert row["sha256_match"] is False
            assert source_path.read_bytes() != target_path.read_bytes()
            assert source_sha256 != target_sha256
        else:
            raise AssertionError(row["source_to_target_relation"])


def test_formal_math_lean_proof_witness_bundle_rejects_body_digest_tamper(
    tmp_path: Path,
) -> None:
    public_root = _copy_exported_bundle_public_root(tmp_path)
    bundle = (
        public_root
        / "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle"
    )
    source_file = bundle / "lake_project/MicrocosmProofWitness/Basic.lean"
    source_file.write_text(
        source_file.read_text(encoding="utf-8") + "\n-- tampered after manifest\n",
        encoding="utf-8",
    )

    result = run_witness_bundle(
        bundle,
        tmp_path / "receipts/formal_math_lean_proof_witness",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_imports"]["status"] == "blocked"
    assert result["lake_build"]["skipped"] is True
    assert result["lake_build"]["skip_reason"] == "source_module_import_blocked"
    assert "LEAN_WITNESS_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_formal_math_lean_proof_witness_bundle_rejects_source_digest_tamper(
    tmp_path: Path,
) -> None:
    public_root = _copy_exported_bundle_public_root(tmp_path)
    bundle = (
        public_root
        / "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle"
    )
    source_file = (
        public_root
        / "fixtures/first_wave/formal_math_lean_proof_witness/input/witness_manifest.json"
    )
    source_file.write_text(
        source_file.read_text(encoding="utf-8")
        + "\n",
        encoding="utf-8",
    )

    result = run_witness_bundle(
        bundle,
        tmp_path / "receipts/formal_math_lean_proof_witness_source_tamper",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_imports"]["status"] == "blocked"
    assert result["lake_build"]["skipped"] is True
    assert result["lake_build"]["skip_reason"] == "source_module_import_blocked"
    assert "LEAN_WITNESS_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH" in result["error_codes"]


def test_formal_math_lean_proof_witness_bundle_reuses_fresh_receipt(
    lean_witness_bundle_card_run: tuple[dict[str, Any], Path, list[str], str],
    monkeypatch: Any,
) -> None:
    first, target, _argv, command = lean_witness_bundle_card_run

    def fail_command(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh bundle cache should avoid Lean command probes")

    monkeypatch.setattr(witness_module, "_run_command", fail_command)
    second = run_witness_bundle(BUNDLE_INPUT, target, command=command)

    assert first["status"] == "pass"
    assert second["status"] == "pass"
    assert second["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert second["receipt_paths"] == first["receipt_paths"]
    assert second["compiled_declaration_count"] == first["compiled_declaration_count"]
    assert second["lean_witness_board"]["lean_lake_execution_authorized"] is True


def test_formal_math_lean_proof_witness_bundle_card_reuses_fresh_receipt(
    capsys: Any,
    monkeypatch: Any,
    lean_witness_bundle_card_run: tuple[dict[str, Any], Path, list[str], str],
) -> None:
    _result, target, argv, _command = lean_witness_bundle_card_run

    assert main(argv) == 0
    first_stdout = capsys.readouterr().out
    first_card = json.loads(first_stdout)
    receipt_path = target / BUNDLE_RESULT_NAME
    assert receipt_path.is_file()

    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert first_card["execution_summary"]["compiled_declaration_count"] == 8
    assert first_card["runtime_summary"]["lake_return_code"] == 0
    assert first_card["receipt_summary"]["full_receipts_written"] is True
    assert len(first_stdout.encode("utf-8")) < 3600

    def fail_command(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh bundle card should avoid Lean command probes")

    monkeypatch.setattr(witness_module, "_run_command", fail_command)
    assert main(argv) == 0
    second_stdout = capsys.readouterr().out
    second_card = json.loads(second_stdout)

    assert second_card["status"] == "pass"
    assert second_card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert second_card["receipt_summary"]["receipt_paths_exported"] is False
    assert len(second_stdout.encode("utf-8")) < 3600

    forbidden_card_keys = {
        "anti_claim",
        "findings",
        "private_state_scan",
        "proof_body",
        "public_replacement_refs",
        "receipt_paths",
        "source_files",
        "source_refs",
    }
    assert forbidden_card_keys.isdisjoint(_walk_keys(second_card))

    full_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert "source_files" in full_receipt
    assert full_receipt["command"].endswith("--card")
    assert full_receipt["source_open_body_imports"]["status"] == "pass"
    assert full_receipt["source_open_body_imports"]["body_material_count"] == 5
    assert full_receipt["body_copied_material_count"] == 5
