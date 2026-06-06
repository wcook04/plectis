from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.derived_fact_provider_engine import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    evaluate_fixture_dir,
    evaluate_registry,
    resolve_json_pointer,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_derived_fact_provider_engine/input"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_json_pointer_supports_lists_and_escaping() -> None:
    payload = {"items": [{"a/b": {"value": 7}}]}
    assert resolve_json_pointer(payload, "/items/0/a~1b/value") == 7


def test_registry_evaluates_json_pointer_and_glob_count(tmp_path: Path) -> None:
    _write(tmp_path / "state/report.json", '{"summary":{"fact_count":3}}\n')
    _write(tmp_path / "docs/a.md", "a\n")
    _write(tmp_path / "docs/b.md", "b\n")
    registry = {
        "facts": [
            {
                "id": "demo.fact_count",
                "provider_type": "json_pointer",
                "source_path": "state/report.json",
                "pointer": "/summary/fact_count",
                "value_type": "integer",
            },
            {
                "id": "demo.markdown_count",
                "provider_type": "glob_count",
                "glob": "docs/*.md",
                "value_type": "integer",
            },
        ]
    }
    receipt = evaluate_registry(registry, root=tmp_path)
    facts = {fact["id"]: fact for fact in receipt["ledger"]["facts"]}
    assert receipt["status"] == "ok"
    assert facts["demo.fact_count"]["value"] == 3
    assert facts["demo.markdown_count"]["sample_matches"] == ["docs/a.md", "docs/b.md"]


def test_callable_uses_git_index_not_untracked_files(tmp_path: Path) -> None:
    _write(tmp_path / "src/tool.py", "print('tracked')\n")
    _write(tmp_path / "README.md", "tracked\n")
    _write(tmp_path / "scratch/untracked.py", "print('untracked')\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "--", "src/tool.py", "README.md"], cwd=tmp_path, check=True)
    receipt = evaluate_registry(
        {
            "facts": [
                {
                    "id": "demo.tracked_files",
                    "provider_type": "callable",
                    "callable": "git_tracked_file_count",
                    "value_type": "integer",
                },
                {
                    "id": "demo.tracked_python",
                    "provider_type": "callable",
                    "callable": "git_tracked_python_count",
                    "value_type": "integer",
                },
            ]
        },
        root=tmp_path,
    )
    facts = {fact["id"]: fact for fact in receipt["ledger"]["facts"]}
    assert facts["demo.tracked_files"]["value"] == 2
    assert facts["demo.tracked_python"]["value"] == 1


def test_provider_failures_are_error_rows(tmp_path: Path) -> None:
    receipt = evaluate_registry(
        {
            "facts": [
                {
                    "id": "demo.missing",
                    "provider_type": "json_pointer",
                    "source_path": "missing.json",
                    "pointer": "/value",
                    "value_type": "integer",
                },
                {
                    "id": "demo.bad_callable",
                    "provider_type": "callable",
                    "callable": "does_not_exist",
                    "value_type": "integer",
                },
            ]
        },
        root=tmp_path,
    )
    facts = {fact["id"]: fact for fact in receipt["ledger"]["facts"]}
    assert receipt["status"] == "degraded"
    assert receipt["audit"]["provider_error_count"] == 2
    assert facts["demo.missing"]["provider_status"] == "error"
    assert facts["demo.missing"]["required_next_action"] == "restore_or_rebuild_source_path:missing.json"
    assert str(tmp_path) not in json.dumps(receipt)
    assert facts["demo.bad_callable"]["error_class"] == "KeyError"


def test_fixture_matrix_matches_provider_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 4
    assert receipt["passed_case_count"] == 4
    assert "not_doctrine_truth_auditor" in ANTI_CLAIMS
    assert "not a doctrine truth auditor" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.derived_fact_provider_engine",
            "evaluate-fixtures",
            "--input",
            str(INPUT_DIR),
            "--json",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": "src"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["organ_id"] == "engine_room_derived_fact_provider_engine"
    assert payload["status"] == "pass"
