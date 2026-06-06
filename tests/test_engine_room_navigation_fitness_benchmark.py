from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.navigation_fitness_benchmark import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    NavigationFitnessTask,
    evaluate_benchmark,
    evaluate_fixture_dir,
    evaluate_task,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_navigation_fitness_benchmark/input"


def _task(**overrides) -> NavigationFitnessTask:
    values = {
        "task_id": "demo",
        "family": "heldout_public",
        "task_prompt": "Find the navigation theory roof.",
        "route_type": "context_pack",
        "expected_artifacts": ("paper_modules:navigation_hologram_theory",),
        "forbidden_first_routes": ("--paper-module",),
        "latency_budget_ms": 100,
        "scent_terms": ("navigation", "theory"),
    }
    values.update(overrides)
    return NavigationFitnessTask(**values)


def test_expected_artifacts_drive_recall_and_precision() -> None:
    result = evaluate_task(
        _task(expected_artifacts=("paper_modules:navigation_hologram_theory", "skills:navigation_metabolism")),
        {
            "first_contact_command": "./repo-python kernel.py --context-pack",
            "wall_ms": 30,
            "selected_artifacts": [
                "paper_modules:navigation_hologram_theory",
                "skills:navigation_metabolism",
                "noise:extra",
            ],
            "summary": "navigation theory and route debt",
        },
    )
    assert result["sufficiency_status"] == "pass"
    assert result["recall_at_packet"] == 1.0
    assert result["precision_at_packet"] == round(2 / 3, 4)


def test_forbidden_first_route_is_sufficiency_debt() -> None:
    result = evaluate_task(
        _task(),
        {
            "first_contact_command": "./repo-python kernel.py --paper-module navigation theory",
            "wall_ms": 20,
            "selected_artifacts": ["paper_modules:navigation_hologram_theory"],
            "summary": "navigation theory",
        },
    )
    assert result["sufficiency_status"] == "fail"
    assert result["sufficiency_failure_kind"] == "forbidden_route"
    assert result["forbidden_first_route_hits"] == ["--paper-module"]


def test_latency_debt_is_separate_from_sufficiency() -> None:
    result = evaluate_task(
        _task(),
        {
            "first_contact_command": "./repo-python kernel.py --context-pack",
            "wall_ms": 220,
            "selected_artifacts": ["paper_modules:navigation_hologram_theory"],
            "summary": "navigation theory",
        },
    )
    assert result["sufficiency_status"] == "pass"
    assert result["latency_status"] == "fail"


def test_benchmark_summary_counts_debt_candidates() -> None:
    receipt = evaluate_benchmark(
        {
            "suite": "unit",
            "cases": [
                {
                    "task": {
                        "task_id": "ok",
                        "expected_artifacts": ["skills:navigation_metabolism"],
                        "route_type": "context_pack",
                        "latency_budget_ms": 100,
                    },
                    "packet": {
                        "first_contact_command": "./repo-python kernel.py --context-pack",
                        "wall_ms": 10,
                        "selected_artifacts": ["skills:navigation_metabolism"],
                    },
                },
                {
                    "task": {
                        "task_id": "missing",
                        "expected_artifacts": ["skills:agent_session_diagnostics"],
                        "route_type": "context_pack",
                    },
                    "packet": {
                        "first_contact_command": "./repo-python kernel.py --context-pack",
                        "wall_ms": 10,
                        "selected_artifacts": ["skills:navigation_metabolism"],
                    },
                },
            ],
        }
    )
    assert receipt["summary"]["task_count"] == 2
    assert receipt["summary"]["sufficiency_pass_count"] == 1
    assert receipt["summary"]["debt_candidate_count"] == 1


def test_fixture_matrix_matches_navigation_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 4
    assert receipt["passed_case_count"] == 4
    assert "not_live_private_kernel_run" in ANTI_CLAIMS
    assert "not a live private kernel run" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.navigation_fitness_benchmark",
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
    assert payload["organ_id"] == "engine_room_navigation_fitness_benchmark"
    assert payload["status"] == "pass"
