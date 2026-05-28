from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from microcosm_core import release_export


def _write(path: Path, text: str = "stub\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
    )


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _make_release_root(root: Path) -> Path:
    root.mkdir()
    for file_name in (
        ".gitignore",
        "AGENTS.md",
        "ANTI_PRINCIPLES.md",
        "AXIOMS.md",
        "CONSTITUTION.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "MANIFEST.in",
        "Makefile",
        "PRINCIPLES.md",
        "QUICKSTART.md",
        "README.md",
        "SECURITY.md",
        "bootstrap.sh",
    ):
        _write(root / file_name, f"{file_name}\n")
    _write(
        root / "pyproject.toml",
        """
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "microcosm-substrate-test"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
microcosm = "microcosm_core.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
""".lstrip(),
    )

    _write(root / "atlas/entry_packet.json", '{"status": "pass"}\n')
    _write(
        root / "core/private_state_forbidden_classes.json",
        json.dumps(
            {
                "schema_version": "secret_exclusion_classes_v1",
                "classes": [],
                "anti_claim": "bounded sentinel scan only",
            }
        ),
    )
    _write(root / "core/organ_registry.json", '{"organs": []}\n')
    _write(root / "examples/basic/README.md", "# Example\n")
    _write(
        root / "Makefile",
        "PUBLIC_TESTS ?= tests/test_public_entry_docs.py\n"
        "test: install\n\tpython -m pytest $(PUBLIC_TESTS)\n"
        "test-all: install\n\tpython -m pytest\n"
        "smoke:\n\tpython -m microcosm_core --version\n"
        "ci: test smoke\n",
    )
    _write(root / ".github/workflows/ci.yml", "run: make ci\n")
    _write(
        root / "examples/runtime_shell/demo_project/.microcosm/project_manifest.json",
        '{"intentional": true}\n',
    )
    _write(root / "fixtures/fixture.json", '{"fixture": true}\n')
    _write(root / "paper_modules/cold_clone_probe.md", "# Cold clone\n")
    _write(root / "scripts/first_screen_composition_card.py", "print('ok')\n")
    _write(root / "skills/cold_start_navigation.md", "# Cold start\n")
    _write(root / "standards/std_microcosm_authority_boundary.json", "{}\n")
    _write(root / "tests/test_example.py", "def test_example():\n    assert True\n")
    _write(root / "tests/__pycache__/test_example.pyc", "cache")
    _write(root / ".DS_Store", "local")
    _write(root / ".microcosm/project_manifest.json", "{}\n")
    _write(root / ".pytest_cache/CACHEDIR.TAG", "cache")
    _write(root / "microcosm-substrate/.microcosm/project_manifest.json", "{}\n")
    _write(
        root
        / release_export.PROJECTION_FRESHNESS_RECEIPT_REF,
        json.dumps(
            {
                "status": "pass",
                "error_codes": [],
                "runtime_severance_status": "pass",
                "dependency_preflight_gate_status": "pass",
                "organ_lifecycle_coverage_status": "pass",
                "macro_runtime_dependency_count": 0,
            }
        ),
    )
    _write(root / "src/microcosm_core/__init__.py", "")
    _write(root / "src/microcosm_substrate.egg-info/PKG-INFO", "generated\n")
    _write(
        root / "src/microcosm_core/cli.py",
        """
from __future__ import annotations

import json
import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) >= 2 and args[0] == "hello":
        print("hello pass")
        return 0
    if len(args) >= 3 and args[0] == "tour" and args[1] == "--card":
        print(json.dumps({"status": "pass"}))
        return 0
    if len(args) >= 2 and args[0] == "first-screen":
        print(json.dumps({"status": "pass"}))
        return 0
    if len(args) >= 2 and args[0] == "authority" and args[1] == "--card":
        print(json.dumps({"status": "pass"}))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
""".lstrip(),
    )
    return root


def test_release_export_generates_clean_standalone_folder_and_receipt(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "microcosm@example.invalid")
    _git(repo, "config", "user.name", "Microcosm Test")
    root = _make_release_root(repo / release_export.ARTIFACT_DIR_NAME)
    _commit_all(repo, "candidate")
    out = tmp_path / "out"

    receipt = release_export.build_release_export(
        root,
        out,
        force=True,
        run_smoke=True,
        command="pytest release export",
    )

    target = out / release_export.ARTIFACT_DIR_NAME
    written_receipt = json.loads(
        (target / release_export.RELEASE_RECEIPT_REF).read_text(encoding="utf-8")
    )
    summary = release_export.release_export_summary(receipt, target)

    assert receipt["status"] == "pass"
    assert written_receipt["status"] == "pass"
    assert summary["schema_version"] == "microcosm_release_export_summary_v1"
    assert summary["status"] == "pass"
    assert summary["blocking_codes"] == []
    assert summary["release_candidate_blocking_codes"] == []
    assert summary["release_authorization_blocking_codes"] == []
    assert summary["artifact_path"] == str(target)
    assert summary["release_receipt_path"] == str(
        target / release_export.RELEASE_RECEIPT_REF
    )
    assert summary["release_receipt_ref"] == release_export.RELEASE_RECEIPT_REF
    assert summary["artifact"]["file_count"] == receipt["artifact"]["file_count"]
    assert (
        summary["validation_summary"]["candidate_status"]
        == "pass_with_external_warnings"
    )
    assert summary["authority"]["release_authorized"] is False
    assert summary["release_authorization_gate"]["decision"] is not None
    assert "release_candidate_packet" not in summary
    assert len(json.dumps(summary, indent=2).splitlines()) < 80
    assert receipt["blocking_codes"] == []
    assert receipt["artifact"]["mode"] == "generated_standalone_folder"
    assert receipt["artifact"]["file_count"] > 0
    assert (target / "Makefile").is_file()
    assert (target / ".github/workflows/ci.yml").is_file()
    assert (target / "CONTRIBUTING.md").is_file()
    assert (target / "QUICKSTART.md").is_file()
    assert (target / "SECURITY.md").is_file()
    assert receipt["authority_receipt"]["release_authorized"] is False
    candidate = receipt["release_candidate_packet"]
    assert candidate["status"] == "pass_with_external_warnings"
    assert (
        candidate["candidate_state"]
        == "validated_release_candidate_pending_explicit_authorization"
    )
    assert candidate["candidate_identity"]["artifact"] == {
        "artifact_dir": release_export.ARTIFACT_DIR_NAME,
        "mode": "generated_standalone_folder",
        "artifact_payload_hash_sha256": receipt["artifact"][
            "artifact_payload_hash_sha256"
        ],
        "file_count": receipt["artifact"]["file_count"],
        "payload_bytes": receipt["artifact"]["payload_bytes"],
    }
    assert candidate["validation_summary"]["exclusion_status"] == "pass"
    assert candidate["validation_summary"]["runnable_smoke_status"] == "pass"
    assert candidate["validation_summary"]["install_smoke_status"] == "pass"
    assert candidate["validation_summary"]["standalone_severance_status"] == "pass"
    assert (
        candidate["validation_summary"]["standalone_claim_level"]
        == "standalone_install_verified"
    )
    assert (
        candidate["validation_summary"][
            "standalone_required_public_entry_refs_missing_count"
        ]
        == 0
    )
    assert candidate["validation_summary"]["standalone_escaping_symlink_ref_count"] == 0
    assert candidate["validation_summary"]["projection_freshness_status"] == "pass"
    assert candidate["validation_summary"]["wheel_install_supported"] is True
    assert ".github" in receipt["inventory_receipt"]["include_refs"]
    assert "CONTRIBUTING.md" in receipt["inventory_receipt"]["include_refs"]
    assert "Makefile" in receipt["inventory_receipt"]["include_refs"]
    assert "QUICKSTART.md" in receipt["inventory_receipt"]["include_refs"]
    assert "SECURITY.md" in receipt["inventory_receipt"]["include_refs"]
    assert receipt["inventory_receipt"]["role_counts"]["ci_workflow"] == 1
    assert receipt["inventory_receipt"]["role_counts"]["command_surface"] == 1
    assert candidate["authority_state"]["release_authorized"] is False
    assert (
        candidate["authority_state"]["release_authorization_gate"]["gate_id"]
        == release_export.RELEASE_AUTHORIZATION_GATE_ID
    )
    assert (
        candidate["authority_state"]["release_authorization_gate"]["invoked"]
        is False
    )
    gate_decision = candidate["release_authorization_gate_decision"]
    assert gate_decision["gate_id"] == release_export.RELEASE_AUTHORIZATION_GATE_ID
    assert gate_decision["dry_run"] is True
    assert gate_decision["release_authorization_allowed_now"] is False
    assert gate_decision["decision"] == "ready_pending_operator_authorization"
    assert gate_decision["operator_authorization_gate_eligible"] is True
    assert gate_decision["blocking_codes"] == []
    assert (
        candidate["candidate_identity"]["source"]["source_tree_state_kind"]
        == "git_head_clean"
    )
    warning_rows = candidate["external_warning_classification"]["warnings"]
    warning_ids = {row["warning_id"] for row in warning_rows}
    assert {
        "historical_evidence_durability_backlog",
        "cap_cartography.json",
        "cap_census.json",
    }.issubset(warning_ids)
    assert (
        candidate["external_warning_classification"][
            "release_blocking_warning_count"
        ]
        == 0
    )
    assert all(row["release_blocking"] is False for row in warning_rows)
    assert receipt["runnable_receipt"]["status"] == "pass"
    assert receipt["runnable_receipt"]["source_tree_cwd_used"] is False
    assert receipt["runnable_receipt"]["source_tree_pythonpath_used"] is False
    assert receipt["runnable_receipt"]["release_artifact_cwd_used"] is False
    assert receipt["runnable_receipt"]["bytecode_write_suppressed"] is True
    assert receipt["install_smoke_receipt"]["status"] == "pass"
    assert receipt["install_smoke_receipt"]["console_entrypoint_used"] is True
    assert receipt["install_smoke_receipt"]["source_tree_cwd_used"] is False
    assert receipt["install_smoke_receipt"]["source_tree_pythonpath_used"] is False
    assert receipt["install_smoke_receipt"]["release_artifact_cwd_used"] is False
    assert receipt["install_smoke_receipt"]["release_artifact_pythonpath_used"] is False
    assert receipt["install_smoke_receipt"]["isolated_artifact_copy_used"] is True
    assert (
        receipt["install_smoke_receipt"]["install_artifact_source"]
        == "isolated_release_artifact_copy"
    )
    assert receipt["install_smoke_receipt"]["bytecode_write_suppressed"] is True
    assert {
        row["command_id"] for row in receipt["install_smoke_receipt"]["commands"]
    } == {
        "create_venv",
        "install_artifact",
        "hello",
        "tour_card",
        "first_screen",
        "authority_card",
    }
    assert all(
        row["body_in_receipt"] is False
        for row in receipt["install_smoke_receipt"]["commands"]
    )
    assert receipt["authority_receipt"]["wheel_install_supported"] is True
    assert (
        receipt["authority_receipt"]["wheel_install_authority"]
        == "outside_source_root_package_install_smoke_pass"
    )
    assert receipt["authority_receipt"]["release_authorized"] is False
    assert receipt["authority_receipt"]["publish_authorized"] is False
    severance = receipt["standalone_severance_receipt"]
    assert severance["schema_version"] == "microcosm_standalone_severance_receipt_v1"
    assert severance["status"] == "pass"
    assert severance["artifact_dir"] == release_export.ARTIFACT_DIR_NAME
    assert severance["mode"] == "generated_standalone_folder"
    assert severance["claim_level"] == "standalone_install_verified"
    assert severance["required_public_entry_refs_missing"] == []
    assert set(severance["required_public_entry_refs_present"]).issuperset(
        {
            "README.md",
            "AGENTS.md",
            "MANIFEST.in",
            "pyproject.toml",
            "src",
            "tests",
            "Makefile",
            "bootstrap.sh",
            ".github",
            "CONTRIBUTING.md",
            "QUICKSTART.md",
            "SECURITY.md",
        }
    )
    assert severance["missing_include_refs"] == []
    assert severance["forbidden_root_prefix_hits"] == []
    assert severance["artifact_residue_violations"] == []
    assert severance["artifact_symlink_refs"] == []
    assert severance["escaping_symlink_refs"] == []
    assert severance["private_path_hit_count"] == 0
    assert severance["strong_secret_hit_count"] == 0
    assert severance["bounded_secret_scan_status"] == "pass"
    assert severance["projection_freshness_status"] == "pass"
    assert severance["runnable_smoke_status"] == "pass"
    assert severance["install_smoke_status"] == "pass"
    assert severance["install_smoke_supports_standalone_run"] is True
    assert severance["authority_boundary"] == {
        "release_authorized": False,
        "publish_authorized": False,
        "hosted_launch_authorized": False,
        "provider_calls_authorized": False,
        "source_files_mutation_authorized": False,
        "private_data_equivalence_authorized": False,
        "supported_public_mode": "generated_standalone_folder",
    }
    assert severance["blocking_codes"] == []
    assert receipt["projection_freshness_receipt"]["status"] == "pass"
    assert (
        receipt["projection_freshness_receipt"]["macro_runtime_dependency_count"] == 0
    )
    assert receipt["exclusion_receipt"]["status"] == "pass"
    assert (
        receipt["exclusion_receipt"]["bounded_secret_exclusion_scan"]["status"]
        == "pass"
    )
    residue_paths = sorted(
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.name == "build"
        or path.name == "__pycache__"
        or path.name.endswith(".egg-info")
        or path.suffix in {".pyc", ".pyo"}
    )
    assert residue_paths == []
    assert any(
        row["path"] == "src/microcosm_substrate.egg-info"
        and row["reason"] == "package_build_metadata"
        for row in receipt["exclusion_receipt"]["source_residue_excluded"]
    )
    assert not (target / ".DS_Store").exists()
    assert not (target / ".microcosm").exists()
    assert not (target / ".pytest_cache").exists()
    assert not (target / release_export.ARTIFACT_DIR_NAME).exists()
    assert (
        target / "examples/runtime_shell/demo_project/.microcosm/project_manifest.json"
    ).is_file()
    assert (
        receipt["inventory_receipt"]["role_counts"][
            "intentional_example_generated_state"
        ]
        == 1
    )
    assert root.as_posix() not in json.dumps(receipt, sort_keys=True)


def test_release_export_main_summary_prints_compact_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    receipt = {
        "status": "pass",
        "blocking_codes": [],
        "artifact": {
            "artifact_dir": release_export.ARTIFACT_DIR_NAME,
            "file_count": 12,
            "payload_bytes": 3456,
            "artifact_payload_hash_sha256": "abc123",
        },
        "authority_receipt": {
            "release_authorized": False,
            "publish_authorized": False,
            "hosted_launch_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutation_authorized": False,
        },
        "release_candidate_packet": {
            "status": "pass_with_external_warnings",
            "candidate_state": "validated_release_candidate_pending_explicit_authorization",
            "validation_summary": {
                "runnable_smoke_status": "pass",
                "install_smoke_status": "pass",
                "standalone_severance_status": "pass",
                "projection_freshness_status": "pass",
            },
            "external_warning_classification": {
                "release_blocking_warning_count": 0,
                "release_authorization_blocking_warning_count": 0,
            },
            "release_authorization_gate_decision": {
                "decision": "ready_pending_operator_authorization",
                "release_authorization_allowed_now": False,
                "operator_authorization_gate_eligible": True,
                "blocking_codes": [],
                "required_actions": ["operator_invokes_release_authorization_gate"],
            },
        },
    }

    def fake_build_release_export(*args: object, **kwargs: object) -> dict[str, object]:
        assert kwargs["command"].endswith("--force --skip-smoke --summary")
        return receipt

    monkeypatch.setattr(
        release_export, "build_release_export", fake_build_release_export
    )

    rc = release_export.main(
        [
            "--root",
            str(tmp_path),
            "--out",
            str(out),
            "--force",
            "--skip-smoke",
            "--summary",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["schema_version"] == "microcosm_release_export_summary_v1"
    assert payload["status"] == "pass"
    assert payload["release_candidate_blocking_codes"] == []
    assert payload["release_authorization_blocking_codes"] == []
    assert payload["artifact_path"] == str(
        out.resolve() / release_export.ARTIFACT_DIR_NAME
    )
    assert payload["release_receipt_ref"] == release_export.RELEASE_RECEIPT_REF
    assert payload["validation_summary"]["runnable_smoke_status"] == "pass"
    assert payload["authority"]["release_authorized"] is False
    assert (
        payload["release_authorization_gate"]["operator_authorization_gate_eligible"]
        is True
    )
    assert "release_candidate_packet" not in payload
    assert len(json.dumps(payload, indent=2).splitlines()) < 80


def test_release_export_summary_separates_candidate_and_authorization_blockers(
    tmp_path: Path,
) -> None:
    target = tmp_path / release_export.ARTIFACT_DIR_NAME
    receipt = {
        "status": "pass",
        "blocking_codes": [],
        "artifact": {
            "artifact_dir": release_export.ARTIFACT_DIR_NAME,
            "file_count": 12,
            "payload_bytes": 3456,
            "artifact_payload_hash_sha256": "abc123",
        },
        "authority_receipt": {
            "release_authorized": False,
            "publish_authorized": False,
            "hosted_launch_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutation_authorized": False,
        },
        "release_candidate_packet": {
            "status": "pass_with_external_warnings",
            "candidate_state": "validated_release_candidate_pending_explicit_authorization",
            "validation_summary": {
                "runnable_smoke_status": "pass",
                "install_smoke_status": "pass",
                "standalone_severance_status": "pass",
                "projection_freshness_status": "pass",
            },
            "external_warning_classification": {
                "release_blocking_warning_count": 0,
                "release_authorization_blocking_warning_count": 1,
            },
            "release_authorization_gate_decision": {
                "decision": "defer",
                "release_authorization_allowed_now": False,
                "operator_authorization_gate_eligible": False,
                "blocking_codes": ["RELEASE_AUTHORIZATION_DIRTY_SOURCE_TREE"],
                "required_actions": [
                    "regenerate_from_clean_source_tree_or_authorize_dirty_material_fingerprint"
                ],
            },
        },
    }

    summary = release_export.release_export_summary(receipt, target)

    assert summary["status"] == "pass"
    assert summary["blocking_codes"] == []
    assert summary["release_candidate_blocking_codes"] == []
    assert summary["release_authorization_blocking_codes"] == [
        "RELEASE_AUTHORIZATION_DIRTY_SOURCE_TREE"
    ]
    assert summary["release_authorization_gate"]["blocking_codes"] == [
        "RELEASE_AUTHORIZATION_DIRTY_SOURCE_TREE"
    ]
    assert len(json.dumps(summary, indent=2).splitlines()) < 80


def test_release_export_skip_smoke_keeps_install_support_unclaimed(
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export",
    )

    assert receipt["status"] == "pass"
    assert receipt["runnable_receipt"]["status"] == "not_run"
    assert receipt["install_smoke_receipt"]["status"] == "not_run"
    assert receipt["standalone_severance_receipt"]["status"] == "pass"
    assert (
        receipt["standalone_severance_receipt"]["claim_level"]
        == "standalone_shape_verified_without_install_claim"
    )
    assert (
        receipt["standalone_severance_receipt"][
            "install_smoke_supports_standalone_run"
        ]
        is False
    )
    assert receipt["authority_receipt"]["wheel_install_supported"] is False
    assert (
        receipt["authority_receipt"]["wheel_install_authority"]
        == "unsupported_until_outside_source_root_package_install_smoke_pass"
    )
    assert (
        receipt["release_candidate_packet"]["validation_summary"][
            "install_smoke_status"
        ]
        == "not_run"
    )
    assert (
        receipt["release_candidate_packet"]["validation_summary"][
            "standalone_severance_status"
        ]
        == "pass"
    )
    assert (
        receipt["release_candidate_packet"]["validation_summary"][
            "wheel_install_supported"
        ]
        is False
    )


def test_projection_freshness_receipt_names_stale_runtime_shape_subjects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")
    (
        root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
    ).mkdir(parents=True)

    def fake_run_projection_bundle(
        bundle_dir: Path,
        output_dir: Path,
        *,
        command: str,
    ) -> dict:
        assert bundle_dir.is_dir()
        assert command == "release-export projection freshness check"
        return {
            "status": "blocked",
            "error_codes": [
                "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISMATCH",
                "MACRO_PROJECTION_DEPENDENCY_PREFLIGHT_BLOCKED",
            ],
            "findings": [
                {
                    "error_code": (
                        "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISMATCH"
                    ),
                    "message": "source body mismatch detail should stay out",
                    "negative_case_id": "public_safe_body_import_floor",
                    "subject_id": "system/server/main.py",
                    "subject_kind": "public_safe_body_target",
                    "body_in_receipt": False,
                },
                {
                    "error_code": (
                        "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISMATCH"
                    ),
                    "message": "release artifact path should be redacted",
                    "negative_case_id": "public_safe_body_import_floor",
                    "subject_id": (
                        root
                        / "examples/macro_projection_import_protocol/"
                        "exported_projection_import_bundle/source_modules/"
                        "system/lib/generated_projection_registry.py"
                    ).as_posix(),
                    "subject_kind": "public_safe_body_target",
                    "body_in_receipt": False,
                },
                {
                    "error_code": "MACRO_PROJECTION_DEPENDENCY_PREFLIGHT_BLOCKED",
                    "message": "temp output path should be redacted",
                    "negative_case_id": "dependency_preflight_lifecycle_gate",
                    "subject_id": (
                        output_dir / "receipts/preflight/dependency_preflight.json"
                    ).as_posix(),
                    "subject_kind": "dependency_preflight_receipt",
                    "body_in_receipt": False,
                },
            ],
            "runtime_severance_status": "pass",
            "dependency_preflight_gate_status": "blocked",
            "organ_lifecycle_coverage_status": "pass",
            "macro_runtime_dependency_count": 0,
        }

    monkeypatch.setattr(
        release_export.macro_projection_import_protocol,
        "run_projection_bundle",
        fake_run_projection_bundle,
    )

    receipt = release_export._projection_freshness(root)
    runtime_shape = receipt["runtime_shape_validation"]
    serialized = json.dumps(receipt, sort_keys=True)

    assert receipt["status"] == "blocked"
    assert runtime_shape["status"] == "blocked"
    assert runtime_shape["finding_count"] == 3
    assert runtime_shape["finding_error_code_counts"] == {
        "MACRO_PROJECTION_DEPENDENCY_PREFLIGHT_BLOCKED": 1,
        "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISMATCH": 2,
    }
    assert runtime_shape["finding_subject_id_count"] == 3
    assert runtime_shape["finding_subject_id_overflow_count"] == 0
    assert "system/server/main.py" in runtime_shape["finding_subject_ids"]
    assert any(
        subject_id.startswith("<release-artifact>/")
        for subject_id in runtime_shape["finding_subject_ids"]
    )
    assert any(
        subject_id.startswith("<projection-check-temp>/")
        for subject_id in runtime_shape["finding_subject_ids"]
    )
    assert all(row["body_in_receipt"] is False for row in runtime_shape["finding_sample"])
    assert "source body mismatch detail should stay out" not in serialized
    assert root.as_posix() not in serialized


def test_release_export_blocks_missing_standalone_entry_ref(
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")
    (root / "bootstrap.sh").unlink()

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export",
    )

    severance = receipt["standalone_severance_receipt"]
    assert receipt["status"] == "blocked"
    assert "RELEASE_EXPORT_INCLUDE_REFS_MISSING" in receipt["blocking_codes"]
    assert "RELEASE_EXPORT_STANDALONE_SEVERANCE_BLOCKED" in receipt["blocking_codes"]
    assert severance["status"] == "blocked"
    assert severance["required_public_entry_refs_missing"] == ["bootstrap.sh"]
    assert "STANDALONE_REQUIRED_PUBLIC_REFS_MISSING" in severance["blocking_codes"]
    assert "STANDALONE_INCLUDE_REFS_MISSING" in severance["blocking_codes"]
    assert (
        receipt["release_candidate_packet"]["validation_summary"][
            "standalone_severance_status"
        ]
        == "blocked"
    )
    assert receipt["release_candidate_packet"]["status"] == "blocked"


def _candidate_packet_for_gate_decision(
    *,
    source_tree_state_kind: str,
    dirty_source_path_count: int = 0,
) -> dict:
    source = {
        "status": "available",
        "source_root_ref": "microcosm-substrate",
        "source_tree_state_kind": source_tree_state_kind,
        "git_head": "abc123",
        "dirty_source_path_count": dirty_source_path_count,
        "dirty_source_path_sample": ["README.md"] if dirty_source_path_count else [],
        "dirty_source_path_overflow_count": 0,
        "body_in_receipt": False,
    }
    warning_rows = release_export._release_candidate_warning_rows(source)
    return {
        "schema_version": "microcosm_release_candidate_packet_v1",
        "status": "pass_with_external_warnings",
        "candidate_state": "validated_release_candidate_pending_explicit_authorization",
        "candidate_identity": {
            "source": source,
            "artifact": {
                "artifact_dir": release_export.ARTIFACT_DIR_NAME,
                "mode": "generated_standalone_folder",
                "artifact_payload_hash_sha256": "def456",
                "file_count": 1,
                "payload_bytes": 1,
            },
            "release_receipt_ref": release_export.RELEASE_RECEIPT_REF,
        },
        "validation_summary": {
            "export_status": "pass",
            "blocking_codes": [],
        },
        "authority_state": {
            "release_authorized": False,
            "release_authorization_gate": {
                "gate_id": release_export.RELEASE_AUTHORIZATION_GATE_ID,
                "invoked": False,
            },
        },
        "external_warning_classification": {
            "warning_count": len(warning_rows),
            "release_blocking_warning_count": sum(
                1 for row in warning_rows if row.get("release_blocking") is True
            ),
            "release_authorization_blocking_warning_count": sum(
                1
                for row in warning_rows
                if row.get("release_authorization_blocking") is True
            ),
            "warnings": warning_rows,
        },
    }


def test_release_authorization_gate_dry_run_defers_dirty_source() -> None:
    packet = _candidate_packet_for_gate_decision(
        source_tree_state_kind="git_head_with_worktree_delta",
        dirty_source_path_count=2,
    )

    decision = release_export._release_authorization_gate_decision(packet)

    assert decision["decision"] == "defer"
    assert decision["operator_authorization_gate_eligible"] is False
    assert "RELEASE_AUTHORIZATION_DIRTY_SOURCE_TREE" in decision["blocking_codes"]
    assert decision["blocking_promotion_inputs"] == ["source_tree_dirty_at_export"]
    assert decision["evaluated_inputs"]["dirty_source_path_count"] == 2


def test_release_authorization_gate_dry_run_allows_clean_candidate_to_wait_for_operator() -> None:
    packet = _candidate_packet_for_gate_decision(
        source_tree_state_kind="git_head_clean",
        dirty_source_path_count=0,
    )

    decision = release_export._release_authorization_gate_decision(packet)

    assert decision["decision"] == "ready_pending_operator_authorization"
    assert decision["operator_authorization_gate_eligible"] is True
    assert decision["release_authorization_allowed_now"] is False
    assert decision["blocking_codes"] == []
    assert decision["required_actions"] == []


def test_release_export_rejects_output_inside_source_root(tmp_path: Path) -> None:
    root = _make_release_root(tmp_path / "source")

    with pytest.raises(ValueError, match="must not be inside the source root"):
        release_export.build_release_export(
            root,
            root / "dist",
            force=True,
            run_smoke=False,
        )


def test_release_export_blocks_strong_secret_patterns_without_body_in_receipt(
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")
    secret_line = "api" + "_key = " + '"1234567890123456"\n'
    _write(root / "src/microcosm_core/local_secret.py", secret_line)

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
    )

    serialized = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "blocked"
    assert receipt["release_candidate_packet"]["status"] == "blocked"
    assert (
        receipt["release_candidate_packet"]["candidate_state"]
        == "not_candidate_blocked"
    )
    assert "RELEASE_EXPORT_STRONG_SECRET_PATTERN" in receipt["blocking_codes"]
    assert receipt["exclusion_receipt"]["strong_secret_hits"] == [
        {
            "body_in_receipt": False,
            "path": "src/microcosm_core/local_secret.py",
            "pattern": (
                "(?i)\\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)"
                "\\s*=\\s*['\\\"][^'\\\"]{12,}['\\\"]"
            ),
        }
    ]
    assert "1234567890123456" not in serialized


def test_candidate_invalidation_assessment_keeps_non_material_head_motion_gate_eligible(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "microcosm@example.invalid")
    _git(repo, "config", "user.name", "Microcosm Test")
    root = _make_release_root(repo / release_export.ARTIFACT_DIR_NAME)
    candidate_head = _commit_all(repo, "candidate")

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export",
    )
    candidate = receipt["release_candidate_packet"]
    assert candidate["candidate_identity"]["source"]["git_head"] == candidate_head
    assert (
        candidate["candidate_invalidation_assessment"]["candidate_validity_result"]
        == "gate_eligible"
    )

    _write(repo / "docs/unrelated.md", "# Unrelated\n")
    _commit_all(repo, "unrelated mainline docs")

    assessment = release_export.assess_candidate_invalidation(candidate, root)

    assert assessment["candidate_validity_result"] == "gate_eligible"
    assert assessment["comparison"]["commits_after_candidate_count"] == 1
    assert assessment["path_classification"]["material_change_intersection"] is False
    assert (
        "docs/unrelated.md"
        in assessment["path_classification"]["changed_paths_by_class"][
            "unrelated_macro_mainline_change"
        ]
    )
    assert assessment["disclosure"] == "newer_non_material_commits_exist"


def test_candidate_invalidation_assessment_stales_on_release_material_change(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "microcosm@example.invalid")
    _git(repo, "config", "user.name", "Microcosm Test")
    root = _make_release_root(repo / release_export.ARTIFACT_DIR_NAME)
    _commit_all(repo, "candidate")
    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export",
    )
    candidate = receipt["release_candidate_packet"]

    _write(root / "README.md", "# Updated Microcosm\n")
    _commit_all(repo, "microcosm release material")

    assessment = release_export.assess_candidate_invalidation(candidate, root)

    assert assessment["candidate_validity_result"] == "stale_requires_rehearsal"
    assert assessment["path_classification"]["material_change_intersection"] is True
    assert (
        f"{release_export.ARTIFACT_DIR_NAME}/README.md"
        in assessment["path_classification"]["changed_paths_by_class"][
            "release_material_change"
        ]
    )
    assert assessment["disclosure"] == "release_material_commits_after_candidate"


def test_candidate_invalidation_assessment_marks_status_projection_refresh_only(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "microcosm@example.invalid")
    _git(repo, "config", "user.name", "Microcosm Test")
    root = _make_release_root(repo / release_export.ARTIFACT_DIR_NAME)
    _commit_all(repo, "candidate")
    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export",
    )
    candidate = receipt["release_candidate_packet"]

    _write(
        repo / "tools/meta/observability/cli_prompt_trace.py",
        "STATUS = 'projection only'\n",
    )
    _commit_all(repo, "trace projection semantics")

    assessment = release_export.assess_candidate_invalidation(candidate, root)

    assert assessment["candidate_validity_result"] == "gate_eligible"
    assert assessment["status_receipt_refresh_recommended"] is True
    assert assessment["path_classification"]["material_change_intersection"] is False
    assert (
        "tools/meta/observability/cli_prompt_trace.py"
        in assessment["path_classification"]["changed_paths_by_class"][
            "release_status_projection_only_change"
        ]
    )
