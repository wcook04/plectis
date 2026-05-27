from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core import release_export


def _write(path: Path, text: str = "stub\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_release_root(root: Path) -> Path:
    root.mkdir()
    for file_name in (
        ".gitignore",
        "AGENTS.md",
        "ANTI_PRINCIPLES.md",
        "AXIOMS.md",
        "CONSTITUTION.md",
        "LICENSE",
        "PRINCIPLES.md",
        "README.md",
        "bootstrap.sh",
        "pyproject.toml",
    ):
        _write(root / file_name, f"{file_name}\n")

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
    if len(args) >= 2 and args[0] == "first-screen":
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
    root = _make_release_root(tmp_path / "source")
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

    assert receipt["status"] == "pass"
    assert written_receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["artifact"]["mode"] == "generated_standalone_folder"
    assert receipt["artifact"]["file_count"] > 0
    assert receipt["authority_receipt"]["release_authorized"] is False
    assert receipt["authority_receipt"]["wheel_install_supported"] is False
    assert receipt["runnable_receipt"]["status"] == "pass"
    assert receipt["runnable_receipt"]["source_tree_cwd_used"] is False
    assert receipt["runnable_receipt"]["source_tree_pythonpath_used"] is False
    assert receipt["projection_freshness_receipt"]["status"] == "pass"
    assert (
        receipt["projection_freshness_receipt"]["macro_runtime_dependency_count"] == 0
    )
    assert receipt["exclusion_receipt"]["status"] == "pass"
    assert (
        receipt["exclusion_receipt"]["bounded_secret_exclusion_scan"]["status"]
        == "pass"
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
