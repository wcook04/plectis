from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.public_projection_leak_gate import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    evaluate_case,
    evaluate_fixture_dir,
    run_gitleaks,
    scan_projection,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_public_projection_leak_gate/input"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_clean_projection_is_green(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "Public projection boundary with no private handles.\n")
    receipt = scan_projection(tmp_path)
    assert receipt["status"] == "green"
    assert receipt["blocking_hit_count"] == 0
    assert receipt["public_release_allowed_by_scan"] is True


def test_private_home_path_is_red_and_hash_only(tmp_path: Path) -> None:
    private_path = "/" + "/".join(["Users", "localoperator", "project", "state.json"])
    _write(tmp_path / "docs" / "note.md", f"Do not export {private_path}\n")
    receipt = scan_projection(tmp_path)
    assert receipt["status"] == "red"
    assert receipt["blocking_hit_count"] == 1
    hit = receipt["blocking_hits"][0]
    assert hit["pattern"] == "private_home_path"
    assert "match_sha256" in hit
    assert "matched_text" not in hit
    assert private_path not in json.dumps(hit)


def test_secret_key_shape_is_red_without_raw_value(tmp_path: Path) -> None:
    key_shape = "-".join(["sk", "engine", "room", "abcdefghijklmnopqrstuvwxyz123456"])
    _write(tmp_path / "config.txt", f"credential={key_shape}\n")
    receipt = scan_projection(tmp_path)
    assert receipt["status"] == "red"
    assert receipt["blocking_hits"][0]["pattern"] == "openai_key_shape"
    assert key_shape not in json.dumps(receipt["blocking_hits"])


def test_policy_exception_path_keeps_report_green(tmp_path: Path) -> None:
    allowed_path = Path("docs/dissemination/public_projection_boundary_v0.md")
    private_path = "/" + "/".join(["home", "localoperator", "vault"])
    _write(tmp_path / allowed_path, f"Boundary example: {private_path}\n")
    receipt = scan_projection(tmp_path, policy_exception_paths=[allowed_path])
    assert receipt["status"] == "green"
    assert receipt["hit_count"] == 1
    assert receipt["blocking_hit_count"] == 0
    assert receipt["policy_exception_count"] == 1


def test_required_missing_gitleaks_fails_closed(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "clean\n")
    receipt = scan_projection(
        tmp_path,
        require_gitleaks=True,
        gitleaks_binary="definitely-not-gitleaks-for-engine-room",
    )
    assert receipt["status"] == "red"
    assert receipt["gitleaks_status"] == "unavailable_fail_closed"


def test_optional_gitleaks_receipt_is_hash_only(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "clean\n")
    receipt = run_gitleaks(tmp_path, required=False)
    assert receipt["status"] in {"pass", "unavailable", "error"}
    if receipt["status"] == "pass":
        assert receipt["finding_count"] == 0
        assert "stdout_sha256" in receipt


def test_fixture_matrix_matches_leak_gate_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 5
    assert receipt["passed_case_count"] == 5
    assert "not_general_security_scanner" in ANTI_CLAIMS
    assert "not a general security scanner" in CLAIM_CEILING


def test_policy_exception_perturbation_moves_fixture_verdict(tmp_path: Path) -> None:
    exception_path = "docs/custom_projection_boundary.md"
    fixture = {
        "case_id": "exception_policy_perturbation",
        "expected_status": "green",
        "policy_exception_paths": [exception_path],
        "files": [
            {
                "path": exception_path,
                "text_parts": [
                    "Boundary example names only a hashed private shape: ",
                    {"join_path": ["home", "localoperator", "vault"]},
                    "\n",
                ],
            }
        ],
    }
    allowed = evaluate_case(fixture, scratch=tmp_path / "allowed")
    denied_fixture = dict(fixture, expected_status="red", policy_exception_paths=[])
    denied = evaluate_case(denied_fixture, scratch=tmp_path / "denied")

    assert allowed["observed_status"] == "green"
    assert denied["observed_status"] == "red"
    assert allowed["verdict_basis"]["policy_exception_count"] == 1
    assert denied["verdict_basis"]["blocking_hit_count"] == 1
    assert allowed["verdict_basis"] != denied["verdict_basis"]
    assert "localoperator" not in json.dumps(allowed["receipt"]["policy_exceptions"])
    assert "localoperator" not in json.dumps(denied["receipt"]["blocking_hits"])


def test_leak_input_perturbation_moves_fixture_verdict(tmp_path: Path) -> None:
    clean_fixture = {
        "case_id": "leak_input_clean",
        "expected_status": "green",
        "files": [{"path": "README.md", "text": "Public release notes only.\n"}],
    }
    leaked_fixture = {
        "case_id": "leak_input_planted_key",
        "expected_status": "red",
        "files": [
            {
                "path": "README.md",
                "text_parts": [
                    "Public release notes plus planted key shape ",
                    {"join": ["sk", "engine", "room", "abcdefghijklmnopqrstuvwxyz123456"], "sep": "-"},
                    "\n",
                ],
            }
        ],
    }
    clean = evaluate_case(clean_fixture, scratch=tmp_path / "clean")
    leaked = evaluate_case(leaked_fixture, scratch=tmp_path / "leaked")

    assert clean["observed_status"] == "green"
    assert leaked["observed_status"] == "red"
    assert clean["verdict_basis"]["blocking_hit_count"] == 0
    assert leaked["verdict_basis"]["blocking_category_counts"] == {"credentials": 1}
    assert clean["verdict_basis"] != leaked["verdict_basis"]
    assert "abcdefghijklmnopqrstuvwxyz123456" not in json.dumps(leaked["receipt"]["blocking_hits"])


def test_symlink_escape_fixture_is_red_and_target_hash_only(tmp_path: Path) -> None:
    fixture = {
        "case_id": "symlink_escape",
        "expected_status": "red",
        "files": [{"path": "README.md", "text": "Public file with an escaping symlink sibling.\n"}],
        "symlinks": [
            {
                "path": "docs/escaped-target.txt",
                "target": "operator-shadow/target.txt",
                "target_text": "external fixture-only target\n",
            }
        ],
    }
    result = evaluate_case(fixture, scratch=tmp_path / "symlink")

    assert result["observed_status"] == "red"
    assert result["verdict_basis"]["symlink_escape_count"] == 1
    assert result["receipt"]["blocking_hit_count"] == 0
    assert result["receipt"]["symlink_escapes"][0]["path"] == "docs/escaped-target.txt"
    assert "target_sha256" in result["receipt"]["symlink_escapes"][0]
    assert "operator-shadow" not in json.dumps(result["receipt"]["symlink_escapes"])
    assert "external fixture-only target" not in json.dumps(result["receipt"]["symlink_escapes"])


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.public_projection_leak_gate",
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
    assert payload["organ_id"] == "engine_room_public_projection_leak_gate"
    assert payload["status"] == "pass"
