from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path, PurePosixPath

import pytest

from microcosm_core import release_export


ACCEPTANCE_REL = Path("core/acceptance/first_wave_acceptance.json")
SUBSTRATE_LEDGER_REL = Path("core/substrate_substitution_ledger.json")


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


def _committed_public_refs(root: Path, *top_levels: str) -> set[str] | None:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-tree",
                "-r",
                "--name-only",
                "HEAD",
                "--",
                *top_levels,
            ],
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def _accepted_organ_ids(root: Path) -> set[str]:
    payload = json.loads((root / ACCEPTANCE_REL).read_text(encoding="utf-8"))
    return {
        str(row.get("organ_id") or "")
        for row in payload.get("accepted_current_authority_organs", [])
        if isinstance(row, dict) and row.get("status") == "accepted_current_authority"
    }


def _accepted_public_roots(root: Path, *top_levels: str) -> set[str]:
    accepted = _accepted_organ_ids(root)
    roots: set[str] = set()
    for organ_id in accepted:
        if "examples" in top_levels:
            roots.add(f"examples/{organ_id}")
        if "fixtures" in top_levels:
            roots.add(f"fixtures/first_wave/{organ_id}")
            roots.add(f"fixtures/second_wave/{organ_id}")

    ledger = json.loads((root / SUBSTRATE_LEDGER_REL).read_text(encoding="utf-8"))
    for row in ledger.get("organ_substrate_dispositions", []):
        if not isinstance(row, dict) or row.get("organ_id") not in accepted:
            continue
        for field in ("source_module_manifest_refs", "microcosm_target_refs"):
            for ref in row.get(field, []) or []:
                if not isinstance(ref, str):
                    continue
                parts = PurePosixPath(ref).parts
                if (
                    parts[:1] == ("examples",)
                    and "examples" in top_levels
                    and len(parts) >= 2
                ):
                    roots.add("/".join(parts[:2]))
                elif (
                    parts[:1] == ("fixtures",)
                    and "fixtures" in top_levels
                    and len(parts) >= 3
                ):
                    roots.add("/".join(parts[:3]))
    return roots


def _is_accepted_public_ref(ref: str, roots: set[str]) -> bool:
    return any(ref == root or ref.startswith(f"{root}/") for root in roots)


def test_packaged_source_module_python_dirs_cover_public_body_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    data_files = pyproject["tool"]["setuptools"]["data-files"]
    packaged_globs = {
        pattern
            for patterns in data_files.values()
            for pattern in patterns
            if pattern.endswith("/*.py")
    }
    committed_refs = _committed_public_refs(root, "examples", "fixtures")
    accepted_roots = _accepted_public_roots(root, "examples", "fixtures")
    if committed_refs is None:
        source_module_dirs = sorted(
            {
                source_file.parent.relative_to(root).as_posix()
                for base in ("examples", "fixtures")
                for source_file in (root / base).glob("**/source_modules/**/*.py")
                if "__pycache__" not in source_file.parts
                and _is_accepted_public_ref(
                    source_file.relative_to(root).as_posix(),
                    accepted_roots,
                )
            }
        )
    else:
        source_module_dirs = sorted(
            {
                PurePosixPath(ref).parent.as_posix()
                for ref in committed_refs
                if ref.endswith(".py")
                and "source_modules" in PurePosixPath(ref).parts
                and "__pycache__" not in PurePosixPath(ref).parts
                and _is_accepted_public_ref(ref, accepted_roots)
            }
        )

    missing = [
        source_dir
        for source_dir in source_module_dirs
        if f"{source_dir}/*.py" not in packaged_globs
    ]

    assert missing == []


def test_exported_overnight_test_capsule_uses_public_example_home_only() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (
        root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules/system/server/tests/test_pipeline_overnight.py"
    )
    text = source.read_text(encoding="utf-8")
    private_home_prefix = "/" + "Users" + "/"
    public_example_home = private_home_prefix + "example"

    assert public_example_home in text
    assert private_home_prefix not in text.replace(public_example_home, "")


def test_exported_macro_source_modules_use_public_safe_homes_only() -> None:
    """Copied macro bodies may carry only the two public-safe home spellings:
    /Users/example (the export replacement home) and /Users/operator (the house
    synthetic-fixture convention, admitted by the contamination policy and a
    rewrite fixed point so exact-copy digest pins survive the export boundary).
    Any other /Users/<name> is a real-home leak."""
    root = Path(__file__).resolve().parents[1]
    source_modules_root = (
        root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules"
    )
    private_home_prefix = "/" + "Users" + "/"
    public_safe_homes = (
        private_home_prefix + "example",
        private_home_prefix + "operator",
    )
    violations: list[str] = []

    for source in sorted(source_modules_root.rglob("*")):
        if not source.is_file() or source.suffix not in {
            ".js",
            ".json",
            ".md",
            ".mjs",
            ".py",
            ".txt",
        }:
            continue
        text = source.read_text(encoding="utf-8", errors="ignore")
        for safe_home in public_safe_homes:
            text = text.replace(safe_home, "")
        if private_home_prefix in text:
            violations.append(source.relative_to(root).as_posix())

    assert violations == []


def test_standalone_required_refs_exist_in_real_tree() -> None:
    """The synthetic release fixture can never mask a missing real file: every
    standalone-required public ref must exist in the actual repo root."""
    from microcosm_core import release_export as release_export_mod

    repo_root = Path(__file__).resolve().parents[1]
    missing = [
        ref
        for ref in release_export_mod.STANDALONE_REQUIRED_PUBLIC_REFS
        if not (repo_root / ref).exists()
    ]
    assert missing == []


def _make_release_root(root: Path) -> Path:
    root.mkdir()
    for file_name in (
        ".gitignore",
        "AGENTS.md",
        "AGENT_ROUTES.md",
        "ANTI_PRINCIPLES.md",
        "ARCHITECTURE.md",
        "AXIOMS.md",
        "CLAUDE.md",
        "CONSTITUTION.md",
        "CONTRIBUTING.md",
        "CODEX.md",
        "CURSOR.md",
        "FIRST_ACTION.md",
        "LICENSE",
        "MANIFEST.in",
        "Makefile",
        "NOTICE",
        "ORGANS.md",
        "PRINCIPLES.md",
        "PROVENANCE.md",
        "QUICKSTART.md",
        "RELEASE_DISCIPLINE.md",
        "RELEASE_REVIEW.md",
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
license = "Apache-2.0"
license-files = ["LICENSE"]

[project.scripts]
microcosm = "microcosm_core.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.data-files]
"share/microcosm-substrate" = [
  "LICENSE",
  "NOTICE",
  "PROVENANCE.md",
  "README.md",
  "pyproject.toml"
]
""".lstrip(),
    )

    _write(root / "atlas/entry_packet.json", '{"status": "pass"}\n')
    _write(root / "atlas/agent_task_routes.json", '{"status": "pass"}\n')
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
    _write(root / "core/organ_evidence_classes.json", '{"organ_evidence_classes": []}\n')
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
    _write(root / "tests/.venv/should_not_be_walked.txt", "local venv residue\n")
    _write(root / "tests/.pytest_cache/should_not_be_walked.txt", "cache residue\n")
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
    _write(
        root / "src/microcosm_core/__main__.py",
        "from microcosm_core.cli import main\nraise SystemExit(main())\n",
    )
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
    assert (target / "AGENT_ROUTES.md").is_file()
    assert (target / "atlas/agent_task_routes.json").is_file()
    assert (target / "ARCHITECTURE.md").is_file()
    assert (target / "ORGANS.md").is_file()
    assert (target / "NOTICE").is_file()
    assert (target / "PROVENANCE.md").is_file()
    assert (target / "Makefile").is_file()
    assert (target / ".github/workflows/ci.yml").is_file()
    assert (target / "CONTRIBUTING.md").is_file()
    assert (target / "QUICKSTART.md").is_file()
    assert (target / "RELEASE_DISCIPLINE.md").is_file()
    assert (target / "SECURITY.md").is_file()
    assert receipt["authority_receipt"]["release_authorized"] is False
    assert (
        receipt["authority_receipt"]["standalone_run_command"]
        == "PYTHONPATH=src python3 -m microcosm_core hello <project>"
    )
    assert (
        written_receipt["authority_receipt"]["standalone_run_command"]
        == receipt["authority_receipt"]["standalone_run_command"]
    )
    assert "microcosm_core.cli" not in json.dumps(receipt["authority_receipt"])
    runnable_commands = {
        row["command_id"]: row["argv"]
        for row in written_receipt["runnable_receipt"]["commands"]
    }
    assert runnable_commands["hello"][:3] == [
        "python3",
        "-m",
        "microcosm_core",
    ]
    assert runnable_commands["first_screen"][:3] == [
        "python3",
        "-m",
        "microcosm_core",
    ]
    assert "microcosm_core.cli" not in json.dumps(written_receipt)
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
    assert candidate["validation_summary"]["release_assurance_v2_status"] == "pass"
    assert (
        candidate["validation_summary"]["release_assurance_v2_candidate_status"]
        == "pass"
    )
    assert (
        candidate["validation_summary"]["release_assurance_v2_publication_status"]
        == "operator_review_required"
    )
    assert candidate["validation_summary"]["materials_ledger_status"] == "pass"
    assert candidate["validation_summary"]["publication_history_status"] == "pass"
    assert candidate["validation_summary"]["claim_language_scan_status"] == "pass"
    assert candidate["validation_summary"]["finance_promotion_scan_status"] == "pass"
    assert candidate["validation_summary"]["privacy_review_status"] == "pass"
    assert (
        candidate["validation_summary"]["release_substance_selector_status"]
        == "pass"
    )
    assert candidate["validation_summary"]["evidence_truth_floor_status"] == "pass"
    assert (
        candidate["validation_summary"]["evidence_truth_floor_blocking_issue_count"]
        == 0
    )
    assert candidate["validation_summary"]["wheel_install_supported"] is True
    assert ".github" in receipt["inventory_receipt"]["include_refs"]
    assert "CONTRIBUTING.md" in receipt["inventory_receipt"]["include_refs"]
    assert "NOTICE" in receipt["inventory_receipt"]["include_refs"]
    assert "PROVENANCE.md" in receipt["inventory_receipt"]["include_refs"]
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
    assert receipt["install_smoke_receipt"]["installed_prefix_pythonpath_used"] is True
    assert receipt["install_smoke_receipt"]["isolated_artifact_copy_used"] is True
    assert (
        receipt["install_smoke_receipt"]["install_artifact_source"]
        == "isolated_release_artifact_copy"
    )
    assert receipt["install_smoke_receipt"]["bytecode_write_suppressed"] is True
    assert {
        row["command_id"] for row in receipt["install_smoke_receipt"]["commands"]
    } == {
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
            "LICENSE",
            "NOTICE",
            "PROVENANCE.md",
            "CLAUDE.md",
            "CODEX.md",
            "CURSOR.md",
            "AGENTS.md",
            "AGENT_ROUTES.md",
            "ANTI_PRINCIPLES.md",
            "ARCHITECTURE.md",
            "AXIOMS.md",
            "CONSTITUTION.md",
            "ORGANS.md",
            "PRINCIPLES.md",
            "MANIFEST.in",
            "pyproject.toml",
            "src",
            "tests",
            "Makefile",
            "bootstrap.sh",
            ".github",
            "CONTRIBUTING.md",
            "QUICKSTART.md",
            "RELEASE_DISCIPLINE.md",
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
    residue_excluded = {
        row["path"]: row["reason"]
        for row in receipt["exclusion_receipt"]["source_residue_excluded"]
    }
    assert residue_excluded["tests/.venv"] == "cache_or_build_directory"
    assert residue_excluded["tests/.pytest_cache"] == "cache_or_build_directory"
    assert (
        residue_excluded["examples/runtime_shell/demo_project/.microcosm"]
        == "cache_or_build_directory"
    )
    assert "tests/.venv/should_not_be_walked.txt" not in residue_excluded
    assert "tests/.pytest_cache/should_not_be_walked.txt" not in residue_excluded
    assert not (target / ".DS_Store").exists()
    assert not (target / ".microcosm").exists()
    assert not (target / ".pytest_cache").exists()
    assert not (target / release_export.ARTIFACT_DIR_NAME).exists()
    assert not (
        target / "examples/runtime_shell/demo_project/.microcosm"
    ).exists()
    assert "intentional_example_generated_state" not in receipt["inventory_receipt"][
        "role_counts"
    ]
    assurance = receipt["release_assurance_v2"]
    assert assurance["schema_version"] == release_export.RELEASE_ASSURANCE_SCHEMA_VERSION
    assert assurance["status"] == "pass"
    assert assurance["release_candidate_status"] == "pass"
    assert assurance["operator_publication_status"] == "operator_review_required"
    assert assurance["release_authorized"] is False
    assert assurance["publish_authorized"] is False
    assert assurance["materials_ledger"]["status"] == "pass"
    assert (
        assurance["materials_ledger"]["license_notice_chain"]["license_expression"]
        == "Apache-2.0"
    )
    assert assurance["materials_ledger"]["required_license_notice_refs_missing"] == []
    assert (
        assurance["materials_ledger"]["dependency_summary"]["runtime_dependency_count"]
        == 0
    )
    assert assurance["materials_ledger"]["sbom"]["status"] == "not_generated"
    assert assurance["publication_history_receipt"]["status"] == "pass"
    assert (
        assurance["publication_history_receipt"]["artifact_contains_git_metadata"]
        is False
    )
    assert (
        assurance["publication_history_receipt"]["fresh_public_repository_required"]
        is True
    )
    assert assurance["claim_language_scan"]["status"] == "pass"
    assert assurance["claim_language_scan"]["release_candidate_blocking_hit_count"] == 0
    assert (
        assurance["finance_promotion_scan"][
            "release_authorization_blocking_hit_count"
        ]
        == 0
    )
    assert assurance["privacy_review_receipt"]["status"] == "pass"
    selector = assurance["release_substance_selector"]
    assert selector["selector_id"] == "evidence_truth_floor"
    assert selector["status"] == "pass"
    assert selector["evidence_truth_floor_status"] == "pass"
    assert selector["blocking_issue_count"] == 0
    assert selector["required_for_release_candidate"] is True
    assert selector["body_in_receipt"] is False
    assert (
        assurance["operator_publication_checklists"]["status"]
        == "operator_review_required"
    )
    assert assurance["release_candidate_blocking_codes"] == []
    assert "GITHUB_PUBLICATION_SETTINGS_REVIEW_REQUIRED" in assurance[
        "release_authorization_blocking_codes"
    ]
    assert assurance["publication_gate"]["release_authorization_allowed_now"] is False

    residue_probe = target / "examples/basic/.microcosm/state.json"
    _write(residue_probe, "{}\n")
    assert {
        "path": "examples/basic/.microcosm/state.json",
        "reason": "generated_microcosm_state",
    } in release_export._artifact_residue_violations(target)
    swift_residue_probe = (
        target / "examples/basic/source_modules/apps/demo/.build/output-file-map.json"
    )
    _write(swift_residue_probe, "{}\n")
    assert {
        "path": "examples/basic/source_modules/apps/demo/.build/output-file-map.json",
        "reason": "compiler_build_artifact",
    } in release_export._artifact_residue_violations(target)
    assert root.as_posix() not in json.dumps(receipt, sort_keys=True)


def test_release_export_blocks_failed_release_substance_selector(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")

    def fake_truth_floor(_target: Path) -> dict[str, object]:
        return {
            "schema_version": "microcosm_evidence_truth_floor_audit_v1",
            "status": "blocked",
            "source_ref": "core/organ_evidence_classes.json",
            "registry_ref": "core/organ_registry.json",
            "receipt_root_ref": "receipts/first_wave",
            "candidate_count": 0,
            "blocking_issue_count": 1,
            "advisory_only": False,
            "disposition_guard": {"issue_count": 1},
            "proof_gap_guard": {"issue_count": 0},
        }

    monkeypatch.setattr(
        release_export,
        "audit_evidence_truth_floor",
        fake_truth_floor,
    )

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export",
    )

    selector = receipt["release_assurance_v2"]["release_substance_selector"]
    assert selector["selector_id"] == "evidence_truth_floor"
    assert selector["status"] == "blocked"
    assert selector["blocking_issue_count"] == 1
    assert receipt["release_assurance_v2"]["release_candidate_status"] == "blocked"
    assert "RELEASE_ASSURANCE_EVIDENCE_TRUTH_FLOOR_BLOCKED" in receipt[
        "release_assurance_v2"
    ]["release_candidate_blocking_codes"]
    assert "RELEASE_EXPORT_ASSURANCE_V2_BLOCKED" in receipt["blocking_codes"]
    assert receipt["release_candidate_packet"]["status"] == "blocked"
    assert (
        receipt["release_candidate_packet"]["validation_summary"][
            "release_substance_selector_status"
        ]
        == "blocked"
    )


def test_release_export_blocks_source_parent_private_path_leaks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    root = _make_release_root(repo / release_export.ARTIFACT_DIR_NAME)
    leaked_path = repo / "state/private_macro_payload.json"
    _write(
        root / "fixtures/leaked_macro_path.json",
        json.dumps({"source_path": leaked_path.as_posix()}),
    )

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export private path leak",
    )

    assert receipt["status"] == "blocked"
    assert "RELEASE_EXPORT_PRIVATE_PATH_LEAK" in receipt["blocking_codes"]
    assert {
        "path": "fixtures/leaked_macro_path.json",
        "needle": "<source-parent>",
        "kind": "absolute_source_parent",
    } in receipt["exclusion_receipt"]["private_path_hits"]
    assert repo.as_posix() not in json.dumps(receipt, sort_keys=True)


def test_release_export_substitutes_private_body_source_module_matches(
    tmp_path: Path,
) -> None:
    private_root = tmp_path / "repo"
    private_root.mkdir()
    root = _make_release_root(private_root / release_export.ARTIFACT_DIR_NAME)
    _write(private_root / "kernel.py", "# private macro root marker\n")
    private_body = (
        "PRIVATE_SENTINEL = 'control plane body must not publish'\n"
        "def run_private_control_plane():\n"
        "    return PRIVATE_SENTINEL\n"
    )
    _write(private_root / "system/lib/work_ledger.py", private_body)
    source_module = (
        root
        / "examples/work_ledger_leak/exported_work_ledger_bundle/"
        "source_modules/system/lib/work_ledger.py"
    )
    _write(source_module, private_body)
    manifest_path = source_module.parents[3] / "source_module_manifest.json"
    _write(
        manifest_path,
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "work_ledger_body_import",
                        "source_ref": "system/lib/work_ledger.py",
                        "target_ref": "source_modules/system/lib/work_ledger.py",
                        "body_copied": True,
                        "body_in_receipt": False,
                        "source_sha256": "stale",
                        "target_sha256": "stale",
                        "sha256": "stale",
                        "sha256_match": True,
                        "line_count": 1,
                    }
                ]
            },
            indent=2,
        )
        + "\n",
    )
    protocol_path = source_module.parents[3] / "custom_projection_protocol.json"
    _write(
        protocol_path,
        json.dumps(
            {
                "copied_material": [
                    {
                        "material_id": "work_ledger_body_import",
                        "source_ref": "system/lib/work_ledger.py",
                        "target_ref": (
                            "examples/work_ledger_leak/exported_work_ledger_bundle/"
                            "source_modules/system/lib/work_ledger.py"
                        ),
                        "body_digest": "sha256:stale",
                        "body_line_count": 1,
                        "body_import_verification": {
                            "verification_status": "verified",
                            "verification_mode": "exact_source_digest_match",
                            "source_body_digest": "sha256:stale",
                            "target_body_digest": "sha256:stale",
                            "source_ref": "system/lib/work_ledger.py",
                            "target_ref": (
                                "examples/work_ledger_leak/"
                                "exported_work_ledger_bundle/source_modules/"
                                "system/lib/work_ledger.py"
                            ),
                            "source_to_target_relation": "exact_copy",
                        },
                    }
                ]
            },
            indent=2,
        )
        + "\n",
    )

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export private body block",
    )

    contamination = receipt["source_modules_contamination"]
    substitution = receipt["exclusion_receipt"]["source_module_private_body_substitution"]
    target_text = (
        tmp_path
        / "out"
        / release_export.ARTIFACT_DIR_NAME
        / source_module.relative_to(root)
    ).read_text(encoding="utf-8")

    assert receipt["status"] == "pass"
    assert contamination["status"] == "pass"
    assert contamination["row_count"] == 0
    assert contamination["blocking_row_count"] == 0
    assert contamination["source_tree_private_body_row_count"] == 1
    assert contamination["source_tree_private_body_substitution_count"] == 1
    assert substitution["substituted_file_count"] == 1
    assert substitution["substituted_files"][0]["contamination_class"] == (
        "private_body_exact_match"
    )
    assert substitution["substituted_files"][0]["matched_private_ref"] == (
        "system/lib/work_ledger.py"
    )
    assert substitution["metadata_rewrite_file_count"] == 2
    assert "WITHHELD_PRIVATE_SOURCE_REF = 'system/lib/work_ledger.py'" in target_text
    assert private_body not in target_text
    assert private_body not in json.dumps(contamination, sort_keys=True)
    exported_manifest = json.loads(
        (
            tmp_path
            / "out"
            / release_export.ARTIFACT_DIR_NAME
            / manifest_path.relative_to(root)
        ).read_text(encoding="utf-8")
    )
    stub_digest = release_export._sha256_file(
        tmp_path
        / "out"
        / release_export.ARTIFACT_DIR_NAME
        / source_module.relative_to(root)
    )
    assert exported_manifest["module_count"] == 0
    assert exported_manifest["modules"] == []
    assert exported_manifest["release_substitution_omissions"][0][
        "source_ref"
    ] == "system/lib/work_ledger.py"
    assert exported_manifest["release_substitution_omissions"][0][
        "release_substitution"
    ] == (
        {
            "substitution": "public_safe_stub",
            "matched_private_ref": "system/lib/work_ledger.py",
            "contamination_class": "private_body_exact_match",
            "body_in_receipt": False,
        }
    )
    exported_protocol = json.loads(
        (
            tmp_path
            / "out"
            / release_export.ARTIFACT_DIR_NAME
            / protocol_path.relative_to(root)
        ).read_text(encoding="utf-8")
    )
    protocol_row = exported_protocol["copied_material"][0]
    assert protocol_row["source_ref"] == source_module.relative_to(root).as_posix()
    assert protocol_row["body_digest"] == f"sha256:{stub_digest}"
    assert protocol_row["body_import_verification"]["target_body_digest"] == (
        f"sha256:{stub_digest}"
    )


def test_release_export_redacts_concrete_home_paths_in_text_source_modules(
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")
    private_home = "/" + "Users" + "/willcook/src/ai_workflow"
    public_home = "/" + "Users" + "/example/src/ai_workflow"
    fixture_home = "/" + "Users" + "/operator/src/ai_workflow"
    generic_private_home_re = r"/" + r"Users/[A-Za-z0-9_.-]+"
    source_module = (
        root
        / "examples/private_home_source/exported_private_home_bundle/"
        "source_modules/tools/example_home.py"
    )
    fixture_home_bare = "/" + "Users" + "/operator"
    real_shaped_longer_name = "/" + "Users" + "/operatorfoo"
    _write(
        source_module,
        f'DEFAULT_HOME = "{private_home}"\n'
        f'PUBLIC_HOME = "{public_home}"\n'
        f'FIXTURE_HOME = "{fixture_home}"\n'
        f'FIXTURE_CMD = "find {fixture_home_bare} -maxdepth 4 -type d"\n'
        f'NOT_THE_FIXTURE = "{real_shaped_longer_name}"\n'
        f'GENERIC_PRIVATE_HOME_RE = r"{generic_private_home_re}"\n',
    )

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=False,
        command="pytest release export home redaction",
    )

    target_text = (
        tmp_path
        / "out"
        / release_export.ARTIFACT_DIR_NAME
        / source_module.relative_to(root)
    ).read_text(encoding="utf-8")

    assert receipt["status"] == "pass"
    assert private_home not in target_text
    assert public_home in target_text
    # The synthetic fixture home is a rewrite fixed point: convention-following
    # imported bodies must survive the export boundary byte-identical so their
    # exact-copy digest pins keep holding — at every boundary the name can end
    # on (slash, space, quote), not only before "/".
    assert fixture_home in target_text
    assert f'FIXTURE_CMD = "find {fixture_home_bare} -maxdepth 4 -type d"' in target_text
    # A longer real-shaped name is NOT the fixture and must still be rewritten.
    assert real_shaped_longer_name not in target_text
    assert f'r"{generic_private_home_re}"' in target_text
    redaction = receipt["exclusion_receipt"]["source_module_home_redaction"]
    assert redaction == {
        "status": "pass",
        "policy": (
            "concrete_non_example_home_paths_in_text_source_modules_are_"
            "rewritten_to_public_example_home"
        ),
        "replacement": "/" + "Users" + "/example",
        "redacted_file_count": 1,
        "concrete_home_path_replacement_count": 2,
        "redacted_files": [
            {
                "path": source_module.relative_to(root).as_posix(),
                "concrete_home_path_replacement_count": 2,
                "replacement": "/" + "Users" + "/example",
                "body_in_receipt": False,
            }
        ],
        "body_in_receipt": False,
    }
    assert private_home not in json.dumps(receipt, sort_keys=True)

    written_receipt = json.loads(
        (
            tmp_path
            / "out"
            / release_export.ARTIFACT_DIR_NAME
            / release_export.RELEASE_RECEIPT_REF
        ).read_text(encoding="utf-8")
    )
    assert written_receipt["exclusion_receipt"]["source_module_home_redaction"] == {
        **redaction,
        "replacement": "<private-home-path>",
        "redacted_files": [
            {
                **redaction["redacted_files"][0],
                "replacement": "<private-home-path>",
            }
        ],
    }
    assert written_receipt["public_path_sanitization"]["status"] == "transformed"


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
            "release_substance_selector_status"
        ]
        == "pass"
    )
    assert (
        receipt["release_candidate_packet"]["validation_summary"][
            "evidence_truth_floor_status"
        ]
        == "pass"
    )
    assert (
        receipt["release_assurance_v2"]["release_substance_selector"]["status"]
        == "pass"
    )
    assert (
        receipt["release_candidate_packet"]["validation_summary"][
            "wheel_install_supported"
        ]
        is False
    )


def test_release_export_cleans_validation_residue_before_residue_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")

    def residue_writing_smoke(target: Path, *, source_root: Path) -> dict:
        assert source_root == root
        (target / ".microcosm/evidence").mkdir(parents=True)
        (target / ".microcosm/evidence/init.json").write_text("{}\n", encoding="utf-8")
        cache_dir = target / "src/microcosm_core/__pycache__"
        cache_dir.mkdir(parents=True)
        (cache_dir / "cli.cpython-313.pyc").write_bytes(b"bytecode")
        return {"status": "pass"}

    monkeypatch.setattr(release_export, "_run_smoke", residue_writing_smoke)
    monkeypatch.setattr(
        release_export,
        "_run_install_smoke",
        lambda target, *, source_root: {"status": "pass"},
    )

    receipt = release_export.build_release_export(
        root,
        tmp_path / "out",
        force=True,
        run_smoke=True,
        command="pytest release export validation residue cleanup",
    )
    target = tmp_path / "out" / release_export.ARTIFACT_DIR_NAME
    cleanup = receipt["exclusion_receipt"]["validation_residue_cleanup"]

    assert receipt["status"] == "pass"
    assert receipt["exclusion_receipt"]["artifact_residue_violations"] == []
    assert cleanup["pre_validation_residue_violation_count"] == 0
    assert cleanup["post_validation_residue_violation_count"] == 0
    assert cleanup["cleaned_path_count"] >= 2
    assert not (target / ".microcosm").exists()
    assert not (target / "src/microcosm_core/__pycache__").exists()


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


def test_projection_freshness_allows_private_body_stub_digest_mismatches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")
    (
        root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
    ).mkdir(parents=True)
    substituted_ref = (
        "examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/source_modules/system/lib/work_ledger.py"
    )

    def fake_run_projection_bundle(
        bundle_dir: Path,
        output_dir: Path,
        *,
        command: str,
    ) -> dict:
        assert bundle_dir.is_dir()
        return {
            "status": "blocked",
            "error_codes": ["MACRO_PROJECTION_PUBLIC_SAFE_BODY_DIGEST_MISMATCH"],
            "findings": [
                {
                    "error_code": "MACRO_PROJECTION_PUBLIC_SAFE_BODY_DIGEST_MISMATCH",
                    "negative_case_id": "public_safe_body_import_floor",
                    "subject_id": substituted_ref,
                    "subject_kind": "copied_material",
                    "body_in_receipt": False,
                }
            ],
            "runtime_severance_status": "pass",
            "dependency_preflight_gate_status": "pass",
            "organ_lifecycle_coverage_status": "pass",
            "macro_runtime_dependency_count": 0,
        }

    monkeypatch.setattr(
        release_export.macro_projection_import_protocol,
        "run_projection_bundle",
        fake_run_projection_bundle,
    )

    receipt = release_export._projection_freshness(
        root,
        substituted_source_module_paths={substituted_ref},
    )
    runtime_shape = receipt["runtime_shape_validation"]

    assert receipt["status"] == "pass"
    assert runtime_shape["status"] == "pass"
    assert runtime_shape["effective_source_status"] == "pass"
    assert runtime_shape["error_codes"] == []
    assert runtime_shape["waived_private_body_stub_mismatch_count"] == 1
    assert runtime_shape["waived_private_body_stub_subject_count"] == 1


def test_projection_freshness_receipt_rejects_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")
    (
        root / release_export.PROJECTION_FRESHNESS_RECEIPT_REF
    ).write_text(
        (
            '{"status":"blocked",'
            '"status":"pass",'
            '"error_codes":[],'
            '"runtime_severance_status":"pass",'
            '"dependency_preflight_gate_status":"pass",'
            '"organ_lifecycle_coverage_status":"pass",'
            '"macro_runtime_dependency_count":0}'
        ),
        encoding="utf-8",
    )

    receipt = release_export._projection_freshness(root)

    assert receipt["status"] == "blocked"
    assert receipt["source_status"] == "invalid_json"
    assert receipt["error_codes"] == ["INVALID_PROJECTION_FRESHNESS_RECEIPT"]
    assert receipt["blocking_codes"] == ["INVALID_PROJECTION_FRESHNESS_RECEIPT"]
    assert receipt["runtime_shape_validation"] == {
        "status": "not_run",
        "reason": "invalid_projection_freshness_receipt",
    }
    assert receipt["release_authorized"] is False
    assert receipt["body_in_receipt"] is False


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


def test_release_export_blocks_missing_doctrine_spine_entry_ref(
    tmp_path: Path,
) -> None:
    root = _make_release_root(tmp_path / "source")
    (root / "AXIOMS.md").unlink()

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
    assert severance["required_public_entry_refs_missing"] == ["AXIOMS.md"]
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


def test_release_export_artifact_safety_scans_stream_without_path_rglob(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / release_export.ARTIFACT_DIR_NAME
    _write(
        target / "core/private_state_forbidden_classes.json",
        json.dumps(
            {
                "schema_version": "secret_exclusion_classes_v1",
                "classes": [],
                "anti_claim": "bounded sentinel scan only",
            }
        ),
    )
    _write(target / "src/microcosm_core/__init__.py", "")
    _write(
        target / "src/microcosm_core/local_secret.py",
        "api" + "_key = " + '"1234567890123456"\n',
    )
    _write(target / ".microcosm/state.json", "{}\n")

    def fail_rglob(self: Path, pattern: str) -> object:
        raise AssertionError("release artifact scans must not materialize Path.rglob")

    monkeypatch.setattr(Path, "rglob", fail_rglob)

    assert {
        "path": ".microcosm/state.json",
        "reason": "generated_microcosm_state",
    } in release_export._artifact_residue_violations(target)
    assert release_export._strong_secret_hits(target) == [
        {
            "path": "src/microcosm_core/local_secret.py",
            "pattern": (
                "(?i)\\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)"
                "\\s*=\\s*['\\\"][^'\\\"]{12,}['\\\"]"
            ),
            "body_in_receipt": False,
        }
    ]
    scan = release_export._secret_scan(target)
    assert scan["status"] == "pass"
    assert scan["scanned_path_count"] >= 3


def test_release_export_artifact_file_scans_skip_symlinked_files(
    tmp_path: Path,
) -> None:
    target = tmp_path / release_export.ARTIFACT_DIR_NAME
    target.mkdir()
    outside = tmp_path / "outside_secret.py"
    outside.write_text("api" + "_key = " + '"1234567890123456"\n', encoding="utf-8")
    symlink = target / "linked_secret.py"
    try:
        symlink.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    assert list(release_export._iter_artifact_files(target)) == []
    assert release_export._strong_secret_hits(target) == []
    assert release_export._artifact_symlink_refs(target) == [
        {
            "path": "linked_secret.py",
            "target_within_artifact": False,
            "body_in_receipt": False,
        }
    ]


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


def test_assess_candidate_cli_rejects_duplicate_receipt_keys(tmp_path: Path) -> None:
    root = _make_release_root(tmp_path / "source")
    receipt_path = tmp_path / "release_export_receipt.json"
    receipt_path.write_text(
        (
            '{"release_candidate_packet": {"candidate_identity": {"source": {"git_head": "old"}}},'
            '"release_candidate_packet": {"candidate_identity": {"source": {"git_head": "new"}}}}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(release_export.StrictJsonError, match="duplicate JSON key"):
        release_export.main(
            [
                "--root",
                str(root),
                "--assess-candidate",
                str(receipt_path),
            ]
        )
