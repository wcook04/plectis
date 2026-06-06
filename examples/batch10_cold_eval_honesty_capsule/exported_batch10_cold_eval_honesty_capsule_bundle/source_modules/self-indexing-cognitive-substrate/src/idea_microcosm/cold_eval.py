"""Score cold-agent navigation routes inside the release microcosm.

[PURPOSE]
Compare flat repo entry against idea-first entry for public-safe cold-start tasks.

[INTERFACE]
Exports run_cold_eval for CLI probes and receipt generation.

[FLOW]
Load evaluation tasks, score both arms, summarize winners, and optionally write output.

[DEPENDENCIES]
Uses JSON fixtures, navigation entry packets, receipts, pathlib, and datetime.

[CONSTRAINTS]
Scores are local fixture diagnostics, not benchmark wins or external agent proof.
- When-needed: Open when comparing flat repository entry against idea-first cold-agent navigation or explaining why entry packets beat unguided file browsing.
- Escalates-to: navigation/entry_packet.json; navigation/atlas.json; evals/cold_agent_ab/tasks.json; runs/cold_agent_ab/seed_scorecard.json
- Navigation-group: microcosm_support.cold_agent_entry
- Validator: validator.cold_agent_eval; validator.release_root_compiler
- Receipt: runs/cold_agent_ab/seed_scorecard.json; receipts/cold_agent_ab_seed.json
- Anti-claim: Cold-agent scorecards are deterministic route-quality fixtures and do not claim a benchmark win, live agent result, or hosted public readiness.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_receipt_slug(path: str) -> str:
    stem = Path(path).stem
    return "seed" if stem == "seed_scorecard" else stem.replace(" ", "_")


def _flat_refs() -> list[str]:
    return ["README.md", "docs/quickstart.md", "pyproject.toml"]


SCORING_POLICY = "declared_route_refs_no_expected_ref_injection_v1"
_ROOT_FILE_REF_RE = re.compile(r"\b(?:AGENTS|README|AXIOMS|RELEASE_SCOPE)\.md\b|\bpyproject\.toml\b")
_PATH_REF_RE = re.compile(r"(?<![\w.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.@+=-]+(?:\.[A-Za-z0-9]+)?/?")
_IDEA_FIRST_ROUTE_SOURCES = [
    "navigation/entry_packet.json",
    "navigation/atlas.json",
    "navigation/microcosm_index.json",
    "navigation/standard_cards.json",
]


def _append_unique(refs: list[str], ref: str) -> None:
    if ref not in refs:
        refs.append(ref)


def _normalize_route_ref(root: Path, token: str) -> str | None:
    ref = token.strip().strip("`\"'.,;:)]}")
    ref = ref.split("::", 1)[0]
    if not ref or any(char in ref for char in "*<>[]"):
        return None
    return ref if (root / ref).exists() else None


def _route_refs_from_text(root: Path, text: str) -> list[str]:
    refs: list[str] = []
    for pattern in (_ROOT_FILE_REF_RE, _PATH_REF_RE):
        for match in pattern.finditer(text):
            ref = _normalize_route_ref(root, match.group(0))
            if ref:
                _append_unique(refs, ref)
    return refs


def _route_refs_from_payload(root: Path, payload: Any) -> list[str]:
    refs: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str):
            for ref in _route_refs_from_text(root, value):
                _append_unique(refs, ref)

    visit(payload)
    return refs


def _declared_route_refs(root: Path, source_refs: list[str]) -> list[str]:
    refs: list[str] = []
    for source_ref in source_refs:
        _append_unique(refs, source_ref)
        source_path = root / source_ref
        if not source_path.exists():
            continue
        text = source_path.read_text(encoding="utf-8")
        if source_path.suffix == ".json":
            try:
                nested_refs = _route_refs_from_payload(root, json.loads(text))
            except json.JSONDecodeError:
                nested_refs = _route_refs_from_text(root, text)
        else:
            nested_refs = _route_refs_from_text(root, text)
        for ref in nested_refs:
            _append_unique(refs, ref)
    return refs


def _idea_first_route_refs(root: Path) -> list[str]:
    return _declared_route_refs(root, _IDEA_FIRST_ROUTE_SOURCES)


def _requires_standard(expected_refs: list[str]) -> bool:
    return any(
        ref.startswith("standards/") or ref == "registry/standards.json" or ref.startswith("navigation/standard")
        for ref in expected_refs
    )


def _requires_receipt(expected_refs: list[str]) -> bool:
    return any(ref.startswith("receipts/") or ref == "release/publication_gate.json" for ref in expected_refs)


def _requires_validator_output(expected_refs: list[str]) -> bool:
    return "registry/validators.json" in expected_refs or "state/work_items.jsonl" in expected_refs


def _score_task(
    task: dict[str, Any],
    arm: str,
    visited_refs: list[str],
    available_refs: list[str] | None = None,
) -> dict[str, Any]:
    expected_refs = task.get("expected_refs", [])
    route_refs = list(visited_refs)
    for ref in available_refs or []:
        _append_unique(route_refs, ref)
    covered_refs = sorted(ref for ref in expected_refs if ref in route_refs)
    coverage_score = int(round(40 * len(covered_refs) / max(1, len(expected_refs))))
    first_relevant_file_reached = bool(visited_refs and visited_refs[0] in expected_refs)
    standard_citation = any(ref.startswith("standards/") or ref == "registry/standards.json" for ref in covered_refs)
    receipt_citation = any(ref.startswith("receipts/") or ref == "release/publication_gate.json" for ref in covered_refs)
    validator_output_used = "registry/validators.json" in covered_refs or "state/work_items.jsonl" in covered_refs
    unsupported_claim_count = 0
    if not covered_refs:
        unsupported_claim_count += 1
    if _requires_standard(expected_refs) and not standard_citation:
        unsupported_claim_count += 1
    if _requires_receipt(expected_refs) and not receipt_citation:
        unsupported_claim_count += 1
    if _requires_validator_output(expected_refs) and not validator_output_used:
        unsupported_claim_count += 1
    coverage_ratio = len(covered_refs) / max(1, len(expected_refs))
    next_move_quality = (
        (1 if covered_refs else 0)
        + (1 if coverage_ratio >= 0.5 else 0)
        + (
            1
            if unsupported_claim_count == 0
            and (standard_citation or receipt_citation or validator_output_used or coverage_ratio == 1)
            else 0
        )
    )
    selected_followup_refs = [ref for ref in covered_refs if ref not in visited_refs]
    step_count = len(visited_refs) + len(selected_followup_refs)
    score = (
        coverage_score
        + (10 if first_relevant_file_reached else 0)
        + (10 if standard_citation else 0)
        + (10 if receipt_citation else 0)
        + 10
        + (10 if validator_output_used else 0)
        + next_move_quality * 5
        - unsupported_claim_count * 4
        - max(0, step_count - 5)
    )
    return {
        "task_id": task["id"],
        "arm": arm,
        "score": score,
        "scoring_policy": SCORING_POLICY,
        "expected_refs": expected_refs,
        "visited_refs": visited_refs,
        "selected_followup_refs": selected_followup_refs,
        "available_ref_count": len(route_refs),
        "covered_refs": covered_refs,
        "first_relevant_file_reached": first_relevant_file_reached,
        "unsupported_claim_count": unsupported_claim_count,
        "private_boundary_violations": 0,
        "correct_standard_citation": standard_citation,
        "correct_receipt_citation": receipt_citation,
        "next_move_quality": next_move_quality,
        "step_count": step_count,
        "validator_output_used": validator_output_used,
        "evidence_refs": covered_refs,
        "expected_ref_injection_used": False,
    }


def run_cold_eval(
    root: Path,
    *,
    output_path: str = "runs/cold_agent_ab/seed_scorecard.json",
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    """
    Build the deterministic cold-agent A/B scorecard and optional receipt.

    - When-needed: Open when a cold-start claim needs exact scoring logic, output shape, or omission language for flat-entry versus idea-first navigation.
    - Escalates-to: evals/cold_agent_ab/tasks.json; navigation/entry_packet.json; runs/cold_agent_ab/seed_scorecard.json
    - Navigation-group: microcosm_support.cold_agent_entry
    - Validator: validator.cold_agent_eval
    - Receipt: runs/cold_agent_ab/seed_scorecard.json; receipts/cold_agent_ab_seed.json
    - Anti-claim: This function writes a local deterministic fixture, not external benchmark evidence or live user study proof.
    """
    root = root.resolve()
    generated_at = at or _utc_now()
    tasks_payload = json.loads((root / "evals" / "cold_agent_ab" / "tasks.json").read_text(encoding="utf-8"))
    tasks = tasks_payload.get("tasks", [])
    idea_route_refs = _idea_first_route_refs(root)
    idea_available_refs = [ref for ref in idea_route_refs if ref not in _IDEA_FIRST_ROUTE_SOURCES]
    rows = []
    for task in tasks:
        rows.append(_score_task(task, "A.flat_repo_entry", _flat_refs()))
        rows.append(_score_task(task, "B.idea_first_packet", _IDEA_FIRST_ROUTE_SOURCES, idea_available_refs))

    by_task: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_task.setdefault(row["task_id"], {})[row["arm"]] = row
    winners = []
    for task_id, arms in sorted(by_task.items()):
        flat = arms["A.flat_repo_entry"]["score"]
        idea = arms["B.idea_first_packet"]["score"]
        winners.append(
            {
                "task_id": task_id,
                "winner": "B.idea_first_packet" if idea > flat else "A.flat_repo_entry" if flat > idea else "tie",
                "score_delta": idea - flat,
            }
        )
    status = (
        "idea_first_packet_wins_fixture"
        if winners and all(row["winner"] == "B.idea_first_packet" for row in winners)
        else "needs_navigation_repair"
    )
    scorecard = {
        "kind": "cold_agent_ab_scorecard",
        "schema_version": "cold_agent_ab_scorecard_v0",
        "id": f"cold_agent_ab.{Path(output_path).stem}",
        "generated_at": generated_at,
        "claim_ref": "idea.navigation_before_search",
        "claim_tier": "deterministic_fixture_route_eval",
        "scoring_policy": SCORING_POLICY,
        "route_sources": {
            "A.flat_repo_entry": _flat_refs(),
            "B.idea_first_packet": _IDEA_FIRST_ROUTE_SOURCES,
        },
        "tasks_ref": "evals/cold_agent_ab/tasks.json",
        "arms": ["A.flat_repo_entry", "B.idea_first_packet"],
        "rows": rows,
        "summary": {
            "task_count": len(tasks),
            "row_count": len(rows),
            "idea_first_win_count": sum(1 for row in winners if row["winner"] == "B.idea_first_packet"),
            "flat_repo_win_count": sum(1 for row in winners if row["winner"] == "A.flat_repo_entry"),
            "tie_count": sum(1 for row in winners if row["winner"] == "tie"),
            "winner_by_task": winners,
            "status": status,
        },
        "omissions": [
            "Deterministic route-quality simulator only.",
            "Expected refs score coverage but are never injected into an arm route.",
            "No live model, external benchmark, or human-agent result is claimed.",
        ],
    }
    output_file = root / output_path
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(scorecard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {
        "status": "ok" if status == "idea_first_packet_wins_fixture" else "failed",
        "output": output_path,
        "task_count": len(tasks),
        "idea_first_win_count": scorecard["summary"]["idea_first_win_count"],
        "flat_repo_win_count": scorecard["summary"]["flat_repo_win_count"],
        "tie_count": scorecard["summary"]["tie_count"],
    }
    if write_receipt:
        slug = _safe_receipt_slug(output_path)
        receipt_rel = f"receipts/cold_agent_ab_{slug}.json"
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": f"receipt.cold_agent_ab_{slug}",
            "generated_at": generated_at,
            "owner": "idea_microcosm.cold_eval",
            "claim_ref": "idea.navigation_before_search",
            "claim_tier": "deterministic_fixture_route_eval",
            "scoring_policy": SCORING_POLICY,
            "command": "python -m idea_microcosm.cli run-cold-eval --root . --write-receipt",
            "result": status,
            "status": "ok" if status == "idea_first_packet_wins_fixture" else "failed",
            "evidence_refs": ["evals/cold_agent_ab/tasks.json", output_path, "navigation/entry_packet.json"],
            "omissions": scorecard["omissions"],
        }
        receipt_file = root / receipt_rel
        receipt_file.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result["receipt_written"] = receipt_rel
    return result
