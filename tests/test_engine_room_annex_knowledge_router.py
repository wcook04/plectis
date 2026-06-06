from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.annex_knowledge_router import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    evaluate_fixture_dir,
    route_catalog,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_annex_knowledge_router/input"


def _catalog() -> dict:
    return {
        "annexes": [
            {
                "slug": "provider-rate-limit-patterns",
                "display_name": "Provider Rate Limit Patterns",
                "description": "Backoff and retry patterns across provider APIs.",
                "tags": ["providers", "retry", "backoff"],
                "source_kind": "sanitized_fixture",
                "routing_summary": {
                    "domains": ["agent-runtime"],
                    "clusters": ["provider-control"],
                    "problem_spaces": ["rate limit backoff across multiple llm providers"],
                    "capabilities": ["retry scheduling", "provider quota fallback"],
                },
                "open_first": [
                    {"summary": "Use when provider calls need rate-limit backoff and fallback."}
                ],
                "notes": [
                    {
                        "id": "note_provider_backoff",
                        "relevance": 90,
                        "note": "Back off across multiple LLM providers and preserve a retry receipt.",
                        "routing": {
                            "problem_spaces": ["provider rate limit handling"],
                            "capabilities": ["backoff", "retry receipt"],
                        },
                    }
                ],
            },
            {
                "slug": "finance-forecast-eval",
                "display_name": "Finance Forecast Evaluation",
                "description": "Forecast scoring and market outcome evaluation.",
                "tags": ["finance", "forecast"],
                "source_kind": "sanitized_fixture",
                "routing_summary": {
                    "domains": ["finance"],
                    "clusters": ["forecasting"],
                    "problem_spaces": ["forecast error scoring"],
                    "capabilities": ["forecast evaluation"],
                },
            },
        ]
    }


def test_structured_routing_beats_family_text() -> None:
    receipt = route_catalog(
        _catalog(),
        problem="rate limit and back off across multiple LLM providers",
    )
    assert receipt["status"] == "routed"
    top = receipt["rows"][0]
    assert top["slug"] == "provider-rate-limit-patterns"
    assert top["match_breakdown"]["structured"] > top["match_breakdown"]["family_text"]


def test_domain_filter_excludes_other_domains() -> None:
    receipt = route_catalog(
        _catalog(),
        problem="forecast error scoring",
        domain="agent-runtime",
    )
    assert receipt["status"] == "no_match"
    assert receipt["rows"] == []


def test_notes_add_matched_note_ids() -> None:
    receipt = route_catalog(
        _catalog(),
        problem="provider rate limit retry receipt",
    )
    assert receipt["rows"][0]["slug"] == "provider-rate-limit-patterns"
    assert "note_provider_backoff" in receipt["rows"][0]["matched_note_ids"]


def test_empty_problem_routes_nowhere() -> None:
    receipt = route_catalog(_catalog(), problem="")
    assert receipt["status"] == "no_match"
    assert receipt["rows"] == []


def test_fixture_matrix_matches_router_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 4
    assert receipt["passed_case_count"] == 4
    assert "not_bm25" in ANTI_CLAIMS
    assert "not BM25" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.annex_knowledge_router",
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
    assert payload["organ_id"] == "engine_room_annex_knowledge_router"
    assert payload["status"] == "pass"
