#!/usr/bin/env python3
"""Run the public-proof smoke report.

This is an external-legibility smoke report for the public-safe proof sequence.
It evaluates a freshly assembled public proof root, runs the public commands,
checks the visual/control-plane contracts, and emits private-preflight packets.
It is report-only: it must not freeze content, block Microcosm additions, open
change lanes, or grant release authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.meta.dissemination import assemble_ai_workflow_proof as proof


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PUBLIC_ROOT = Path("/tmp/ai-workflow-proof-flagship-gauntlet")
DEFAULT_REPORT_PATH = Path("/tmp/ai-workflow-proof-flagship-gauntlet-report.json")

OUTPUT_GAUNTLET = Path("docs/dissemination/public_microcosm_flagship_reviewer_gauntlet_v0.json")
OUTPUT_GAUNTLET_MD = Path("docs/dissemination/public_microcosm_flagship_reviewer_gauntlet_v0.md")
OUTPUT_FIRST_RUN = Path("docs/dissemination/public_microcosm_flagship_first_run_receipt_v0.json")
OUTPUT_CLAIM_SURFACE = Path("docs/dissemination/public_microcosm_flagship_claim_surface_v0.md")

SEQUENCE_PACKET = Path("docs/dissemination/public_microcosm_flagship_sequence_v0.json")
VISUAL_PACKET = Path("docs/dissemination/public_microcosm_visual_control_plane_v0.json")
RELEASE_ESCROW_PACKET = Path("docs/dissemination/public_substrate_release_candidate_escrow_v0.json")
REPORT_DECISION = "report_only_public_proof_smoke_pass"
CONTENT_POSTURE_STATE = "open_for_direct_substrate_import"
CHANGE_OBSERVATION_WORK_ITEM_ID = "cap_public_microcosm_report_only_change_observation_v0"

PUBLIC_MANIFEST = "public_executable_projection_manifest_v0.json"
PUBLIC_VISUAL_PACKET = "experience/public_microcosm_visual_control_plane_v0.json"
PUBLIC_PROOF_INPUT_PREFIXES = (
    "tools/meta/dissemination/assemble_ai_workflow_proof.py",
    "tools/meta/dissemination/build_public_microcosm_substrate_selection.py",
    "tools/meta/dissemination/build_public_microcosm_flagship_reviewer_gauntlet.py",
    "docs/dissemination/public_microcosm_flagship_sequence_v0",
    "docs/dissemination/public_microcosm_visual_control_plane_v0",
    "docs/dissemination/public_microcosm_substrate_selection_atlas_v0",
    "docs/dissemination/public_projection_system_coverage_atlas_v0",
    "docs/dissemination/public_substrate_pattern_atlas_v0",
    "docs/dissemination/release_security_contact_closure_v0",
    "self-indexing-cognitive-substrate/",
)

CONTENT_CHANGE_LANE_SURFACES = (
    Path("docs/dissemination/public_proof_v0_1_change_lane_v0.json"),
    Path("docs/dissemination/public_microcosm_v0_1_change_lane_v0.json"),
    Path("docs/dissemination/public_microcosm_flagship_v0_1_change_lane_v0.json"),
)

FLAGSHIP_SEQUENCE_IDS = (
    "substrate_loop",
    "concurrency_transaction_mission_control_microcosm",
    "type_b_shuttle_capture_microcosm",
    "doctrine_apply_metabolism_microcosm",
)

COMMAND_SUITE: tuple[tuple[str, list[str]], ...] = (
    ("demo_substrate", ["make", "demo-substrate"]),
    ("run_concurrency", [sys.executable, "-m", "aiwf_proof", "run", "examples/10_concurrency_mission_control"]),
    ("run_shuttle", [sys.executable, "-m", "aiwf_proof", "run", "examples/11_type_b_shuttle_capture"]),
    ("run_doctrine", [sys.executable, "-m", "aiwf_proof", "run", "examples/12_doctrine_apply_metabolism"]),
    ("visual", [sys.executable, "-m", "aiwf_proof", "visual"]),
    ("coverage", [sys.executable, "-m", "aiwf_proof", "coverage"]),
    ("claims", [sys.executable, "-m", "aiwf_proof", "claims"]),
    ("validate", [sys.executable, "-m", "aiwf_proof", "validate"]),
    ("projection_verifier", [sys.executable, "verifier/validate_projection.py", "--root", "."]),
)

ALLOWED_CLAIMS = [
    {
        "claim_id": "public_safe_executable_miniature",
        "claim": "The artifact is a public-safe executable miniature of a private repo-native cognitive substrate.",
        "support": ["README.md", PUBLIC_MANIFEST, "docs/START_HERE.md"],
    },
    {
        "claim_id": "flagship_sequence_runs_from_public_fixtures",
        "claim": "The flagship cells run from public fixtures and emit receipts under ignored runs paths.",
        "support": ["examples/10_concurrency_mission_control", "examples/11_type_b_shuttle_capture", "examples/12_doctrine_apply_metabolism"],
    },
    {
        "claim_id": "type_b_is_advisory_not_authority",
        "claim": "The Type B shuttle cell shows advisory synthesis becoming Type A verification targets, not source authority.",
        "support": ["examples/11_type_b_shuttle_capture/expected_receipt.json"],
    },
    {
        "claim_id": "doctrine_apply_is_dry_run_routing",
        "claim": "The doctrine-apply cell classifies lessons into durable destination candidates without mutating private doctrine.",
        "support": ["examples/12_doctrine_apply_metabolism/expected_receipt.json"],
    },
    {
        "claim_id": "visual_control_plane_binds_sequence",
        "claim": "The static visual control plane binds the sequence to commands, receipts, anti-claims, omissions, and no-go posture.",
        "support": ["docs/VISUAL_CONTROL_PLANE.md", PUBLIC_VISUAL_PACKET],
    },
    {
        "claim_id": "trust_backplane_fail_closed",
        "claim": "Release and trust surfaces remain fail-closed with public toggle no-go.",
        "support": ["docs/BOUNDARY.md", "release/public_release_appetite_v0.json"],
    },
]

FORBIDDEN_CLAIMS = [
    {
        "claim_id": "not_public_release_approval",
        "claim": "Do not claim the artifact is approved for public release or outreach.",
    },
    {
        "claim_id": "not_private_root_source_release",
        "claim": "Do not call this an open-source or source-available release of the private root.",
    },
    {
        "claim_id": "not_live_private_runtime",
        "claim": "Do not claim it includes live private ledgers, raw seed, provider/browser state, prompt shelf, or private UI state.",
    },
    {
        "claim_id": "not_slsa_or_scorecard",
        "claim": "Do not claim SLSA provenance, OpenSSF Scorecard health, public CI, or public reproducibility unless those checks run in an eligible public setting.",
    },
    {
        "claim_id": "not_private_root_equivalence",
        "claim": "Do not claim the miniature is equivalent to or complete relative to the private operating system.",
    },
    {
        "claim_id": "not_doctrine_mutation",
        "claim": "Do not claim the public doctrine example mutates private standards, skills, paper modules, prompts, or Work Ledger state.",
    },
    {
        "claim_id": "not_agi_or_production_ready",
        "claim": "Do not describe the artifact as AGI, ASI, production-ready, or a self-improving machine.",
    },
]

RISKY_WORDS = [
    "open source",
    "source available",
    "ready to publish",
    "production-ready",
    "public demo cleared",
    "private root",
    "live ledgers",
    "SLSA",
    "Scorecard",
    "AGI",
    "self-improving machine",
]


def _repo_path(repo_root: Path, rel_path: Path) -> Path:
    return repo_root / rel_path


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _run_git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _current_head(repo_root: Path) -> str:
    return _run_git(repo_root, "rev-parse", "HEAD")


def _changed_paths_between(repo_root: Path, old_commit: str, new_commit: str) -> list[str]:
    if old_commit == new_commit:
        return []
    try:
        output = _run_git(repo_root, "diff", "--name-only", f"{old_commit}..{new_commit}")
    except subprocess.CalledProcessError:
        return ["<unknown_diff_range>"]
    return [line for line in output.splitlines() if line.strip()]


def _public_proof_relevant_changes(paths: list[str]) -> list[str]:
    return [
        path
        for path in paths
        if any(path == prefix or path.startswith(prefix) for prefix in PUBLIC_PROOF_INPUT_PREFIXES)
    ]


def _public_proof_input_fingerprint(repo_root: Path, commit: str | None) -> str:
    if not commit:
        return "missing"
    try:
        output = _run_git(repo_root, "ls-tree", "-r", "--full-tree", str(commit))
    except subprocess.CalledProcessError:
        return "unknown"
    entries: list[str] = []
    for line in output.splitlines():
        try:
            path = line.split("\t", 1)[1]
        except IndexError:
            continue
        if any(path == prefix or path.startswith(prefix) for prefix in PUBLIC_PROOF_INPUT_PREFIXES):
            entries.append(line)
    return _sha256_text("\n".join(sorted(entries)))


def _content_change_lane(repo_root: Path) -> str:
    for rel_path in CONTENT_CHANGE_LANE_SURFACES:
        payload = _load_json(_repo_path(repo_root, rel_path), {})
        if not isinstance(payload, dict):
            continue
        status = str(payload.get("status", "")).lower()
        candidate_policy = str(
            payload.get("candidate_identity_policy")
            or payload.get("new_candidate_identity")
            or payload.get("candidate_identity")
            or ""
        ).lower()
        if status in {"active", "open", "approved", "in_progress"} and (
            "new" in candidate_policy or "required" in candidate_policy
        ):
            return "v0_1"
    return "none"


def _release_refresh_lane(release_lane_posture: dict[str, Any]) -> str:
    if not release_lane_posture.get("release_review_active", False):
        return "none"
    refresh_state = release_lane_posture.get("release_candidate_refresh") or release_lane_posture.get(
        "release_refresh_lane"
    )
    if isinstance(refresh_state, dict):
        refresh_state = refresh_state.get("status")
    state = str(refresh_state or "").lower()
    if state in {"active", "open", "owned", "in_progress", "refresh_from_current_public_proof"}:
        return "release_review"
    return "none"


def _change_observation_status(
    *,
    content_state: str,
    frozen_source_commit: str | None,
    current_head: str,
    changed_paths: list[str],
    public_proof_relevant_changes: list[str],
    public_proof_input_fingerprint_before: str,
    public_proof_input_fingerprint_now: str,
    release_lane_posture: dict[str, Any],
    gauntlet_refreshed: bool = False,
    content_change_lane: str = "none",
    release_refresh_lane: str = "none",
) -> dict[str, Any]:
    return {
        "schema_version": "public_proof_v0_change_observation_v0",
        "work_item_id": CHANGE_OBSERVATION_WORK_ITEM_ID,
        "status": "pass",
        "reason": "report_only_no_gate",
        "content_state": content_state,
        "frozen_source_commit": frozen_source_commit,
        "current_head": current_head,
        "public_proof_input_fingerprint_before": public_proof_input_fingerprint_before,
        "public_proof_input_fingerprint_now": public_proof_input_fingerprint_now,
        "changed_public_proof_inputs": public_proof_relevant_changes,
        "changed_path_count_since_observation": len(changed_paths),
        "accepted_change_lane": "not_required",
        "release_review_active": release_lane_posture.get("release_review_active", False),
        "public_toggle": release_lane_posture.get("public_toggle", "no_go"),
        "public_toggle_unchanged_by_observation": True,
        "observation_rule": "This smoke report observes public-proof input changes only; it does not freeze content, block Microcosm additions, or require a change lane.",
    }


def _change_observation_from_existing(
    repo_root: Path,
    existing: dict[str, Any],
    *,
    current_head: str,
    gauntlet_refreshed: bool = False,
) -> dict[str, Any]:
    legacy_content_gate = {}
    release_lane_posture = existing.get("release_lane_posture") if isinstance(existing.get("release_lane_posture"), dict) else {}
    frozen_identity = legacy_content_gate.get("frozen_identity") if isinstance(legacy_content_gate.get("frozen_identity"), dict) else {}
    frozen_source_commit = str(
        frozen_identity.get("source_commit")
        or existing.get("evaluated_source_commit")
        or current_head
    )
    evaluated_source_commit = str(existing.get("evaluated_source_commit") or frozen_source_commit)
    changed_paths = _changed_paths_between(repo_root, evaluated_source_commit, current_head)
    public_proof_relevant_changes = _public_proof_relevant_changes(changed_paths)
    return _change_observation_status(
        content_state=str(existing.get("content_state") or legacy_content_gate.get("content_state") or CONTENT_POSTURE_STATE),
        frozen_source_commit=frozen_source_commit,
        current_head=current_head,
        changed_paths=changed_paths,
        public_proof_relevant_changes=public_proof_relevant_changes,
        public_proof_input_fingerprint_before=_public_proof_input_fingerprint(repo_root, evaluated_source_commit),
        public_proof_input_fingerprint_now=_public_proof_input_fingerprint(repo_root, current_head),
        release_lane_posture=release_lane_posture,
        gauntlet_refreshed=bool(gauntlet_refreshed and public_proof_relevant_changes),
        content_change_lane=_content_change_lane(repo_root),
        release_refresh_lane=_release_refresh_lane(release_lane_posture),
    )


def _commit_timestamp(repo_root: Path, commit: str) -> str:
    return _run_git(repo_root, "show", "-s", "--format=%cI", commit)


def _read_text(root: Path, rel_path: str) -> str:
    path = root / rel_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _assemble_public_root(
    output_root: Path,
    report_path: Path,
    *,
    generated_at: str,
) -> dict[str, Any]:
    if output_root.exists():
        shutil.rmtree(output_root)
    original_utc_now = proof._utc_now
    proof._utc_now = lambda: generated_at  # type: ignore[assignment]
    try:
        return proof.assemble(output_root.resolve(), report_path.resolve(), init_git=False)
    finally:
        proof._utc_now = original_utc_now  # type: ignore[assignment]


def _command_to_string(argv: list[str]) -> str:
    return " ".join("python" if arg == sys.executable else arg for arg in argv)


def _parse_json_output(stdout: str) -> Any | None:
    stripped = stdout.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _run_command(root: Path, command_id: str, argv: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        argv,
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_seconds,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed = _parse_json_output(stdout)
    status = "pass" if completed.returncode == 0 else "fail"
    parsed_status = parsed.get("status") if isinstance(parsed, dict) else None
    computed_receipt = parsed.get("computed_receipt") if isinstance(parsed, dict) else None
    return {
        "command_id": command_id,
        "command": _command_to_string(argv),
        "status": status,
        "returncode": completed.returncode,
        "parsed_status": parsed_status,
        "parsed_schema_version": parsed.get("schema_version") if isinstance(parsed, dict) else None,
        "computed_receipt_schema_version": computed_receipt.get("schema_version")
        if isinstance(computed_receipt, dict)
        else None,
        "computed_receipt_microcosm_id": computed_receipt.get("microcosm_id")
        if isinstance(computed_receipt, dict)
        else None,
        "stdout_json": isinstance(parsed, dict),
        "stderr_present": bool(stderr),
    }


def _run_commands(root: Path, *, timeout_seconds: int) -> list[dict[str, Any]]:
    return [
        _run_command(root, command_id, argv, timeout_seconds=timeout_seconds)
        for command_id, argv in COMMAND_SUITE
    ]


def _sequence_nodes(root: Path) -> list[dict[str, Any]]:
    visual = _load_json(root / PUBLIC_VISUAL_PACKET, {})
    return visual.get("flagship_sequence_nodes", []) if isinstance(visual, dict) else []


def _status_from_requirements(requirements: dict[str, bool]) -> str:
    if all(requirements.values()):
        return "pass"
    if any(requirements.values()):
        return "warn"
    return "fail"


def _persona_results(root: Path) -> list[dict[str, Any]]:
    docs = {
        "readme": _read_text(root, "README.md"),
        "start": _read_text(root, "docs/START_HERE.md"),
        "routes": _read_text(root, "docs/ROUTES.md"),
        "visual": _read_text(root, "docs/VISUAL_CONTROL_PLANE.md"),
        "boundary": _read_text(root, "docs/BOUNDARY.md"),
        "substrate": _read_text(root, "docs/SUBSTRATE.md"),
        "explanation": _read_text(root, "docs/EXPLANATION.md"),
        "how_to": _read_text(root, "docs/HOW_TO_RUN.md"),
        "site": _read_text(root, "site/substrate_map.html"),
    }
    all_text = "\n".join(docs.values())
    persona_specs = [
        {
            "persona_id": "cold_cloner",
            "requirements": {
                "front_door_names_artifact": "AI Workflow Substrate Miniature" in docs["readme"],
                "first_command_visible": "make demo-substrate" in docs["readme"],
                "start_route_exists": bool(docs["start"]),
                "no_go_visible": "no-go" in all_text.lower() or "no_go" in all_text,
            },
            "answers": {
                "what_is_this": "A public-safe executable miniature of the AI Workflow substrate.",
                "first_command": "make demo-substrate",
                "what_sequence_proves": "The public path can run substrate, concurrency, shuttle, doctrine, and visual receipts from public fixtures.",
                "which_cell_to_inspect": "00_substrate_loop first, then the visual control-plane route.",
                "what_is_boundary_only": "Trust backplane and release posture.",
                "what_is_omitted": "Private root, raw seed, live ledgers, provider/browser state, prompt shelf, private UI state.",
                "what_claim_is_forbidden": "This is not public-release approval or a private-root source release.",
                "what_next_question_remains": "Whether release review should regenerate a fresh escrow from this content.",
            },
        },
        {
            "persona_id": "programming_systems_reviewer",
            "requirements": {
                "sequence_nodes_visible": all(text in all_text for text in ("Concurrency Mission Control", "Type B Shuttle Capture", "Doctrine Apply Metabolism")),
                "commands_visible": "python -m aiwf_proof run examples/10_concurrency_mission_control" in all_text,
                "verifier_visible": "verifier/validate_projection.py" in all_text,
                "receipts_visible": "receipt" in all_text.lower(),
            },
            "answers": {
                "what_is_this": "A clone-first artifact that exposes the substrate through executable projection contracts.",
                "first_command": "make demo-substrate",
                "what_sequence_proves": "Typed work and evidence move through coordination, verification, and learning-routing transforms.",
                "which_cell_to_inspect": "10_concurrency_mission_control for claim/collision/scoped-action discipline.",
                "what_is_boundary_only": "Release gates and scans support trust but are not the content center.",
                "what_is_omitted": "Private runtime implementation and account-bound automation.",
                "what_claim_is_forbidden": "The public transforms are not full private-root behavior.",
                "what_next_question_remains": "Which private surfaces would be shown under controlled review.",
            },
        },
        {
            "persona_id": "agent_infra_reviewer",
            "requirements": {
                "type_b_visible": "Type B" in all_text,
                "ask_type_a_visible": "ASK_TYPE_A" in all_text or "Type A" in all_text,
                "workitem_visible": "WorkItem" in all_text,
                "anti_claims_visible": "anti-claim" in all_text.lower() or "anti_claim" in all_text,
            },
            "answers": {
                "what_is_this": "A public route for how advisory cognition becomes bounded Type A work and receipts.",
                "first_command": "python -m aiwf_proof run examples/11_type_b_shuttle_capture",
                "what_sequence_proves": "External synthesis is converted into verification targets, candidate work, and residuals instead of authority.",
                "which_cell_to_inspect": "11_type_b_shuttle_capture.",
                "what_is_boundary_only": "Source authority and public release boundaries.",
                "what_is_omitted": "Real prompt shelf, provider messages, browser state, and live outbox rows.",
                "what_claim_is_forbidden": "Do not claim Type B output is source authority.",
                "what_next_question_remains": "How the private prompt shelf is governed under non-public review.",
            },
        },
        {
            "persona_id": "safety_evaluator_reviewer",
            "requirements": {
                "boundary_doc_exists": bool(docs["boundary"]),
                "omissions_visible": "omitted" in all_text.lower() or "withheld" in all_text.lower(),
                "public_toggle_no_go": "no_go" in all_text or "no-go" in all_text.lower(),
                "forbidden_claims_visible": "not " in docs["boundary"].lower() or "forbidden" in all_text.lower(),
            },
            "answers": {
                "what_is_this": "A fail-closed public-safe proof route with explicit omitted private state.",
                "first_command": "python -m aiwf_proof claims",
                "what_sequence_proves": "Receipts and anti-claims bind public examples without granting release authority.",
                "which_cell_to_inspect": "docs/BOUNDARY.md and the visual trust backplane.",
                "what_is_boundary_only": "Release approval, security posture, media/demo release, outreach, and source/open wording.",
                "what_is_omitted": "Secrets, credentials, private root, live ledgers, raw seed, provider/browser traces.",
                "what_claim_is_forbidden": "Do not claim public demo clearance, open-source release, public reproducibility, SLSA, or Scorecard status.",
                "what_next_question_remains": "Whether future release review has fresh gates and operator approval.",
            },
        },
        {
            "persona_id": "substrate_skeptic",
            "requirements": {
                "what_proves_visible": "proof" in all_text.lower(),
                "sequence_has_four_nodes": len(_sequence_nodes(root)) >= 4,
                "visual_map_exists": bool(docs["site"]),
                "omission_boundary_visible": "private root" in all_text.lower(),
            },
            "answers": {
                "what_is_this": "A deliberately narrow substrate miniature, not a claim that the private system is public.",
                "first_command": "python -m aiwf_proof visual",
                "what_sequence_proves": "The public object can expose a coherent pattern language from pressure to learning without leaking private state.",
                "which_cell_to_inspect": "site/substrate_map.html, then examples/12_doctrine_apply_metabolism.",
                "what_is_boundary_only": "Claims beyond the miniature are boundary-only.",
                "what_is_omitted": "The live system internals that would make stronger claims unsafe in public.",
                "what_claim_is_forbidden": "Do not claim the miniature proves full private-system equivalence.",
                "what_next_question_remains": "Which private demos or controlled packets would raise confidence.",
            },
        },
        {
            "persona_id": "visual_first_reviewer",
            "requirements": {
                "visual_doc_exists": bool(docs["visual"]),
                "site_map_exists": bool(docs["site"]),
                "visual_command_visible": "python -m aiwf_proof visual" in all_text,
                "trust_backplane_visible": "Trust Backplane" in all_text,
            },
            "answers": {
                "what_is_this": "A generated public-safe cockpit over the flagship sequence.",
                "first_command": "python -m aiwf_proof visual",
                "what_sequence_proves": "Each node has a command, receipt, claim tier, anti-claim, omitted state, and no-go status.",
                "which_cell_to_inspect": "docs/VISUAL_CONTROL_PLANE.md and site/substrate_map.html.",
                "what_is_boundary_only": "Trust backplane nodes and release switch state.",
                "what_is_omitted": "Private HUD screenshots, live frontend state, raw seed, provider/browser state.",
                "what_claim_is_forbidden": "Do not present the static cockpit as a live private HUD.",
                "what_next_question_remains": "Whether public media review should later add screenshots or video.",
            },
        },
    ]
    results: list[dict[str, Any]] = []
    for spec in persona_specs:
        requirements = spec["requirements"]
        missing = [key for key, ok in requirements.items() if not ok]
        status = _status_from_requirements(requirements)
        results.append(
            {
                "persona_id": spec["persona_id"],
                "status": status,
                "answers": spec["answers"],
                "confusions": [f"missing signal: {key}" for key in missing],
                "patches_required": [] if status == "pass" else [f"repair {key}" for key in missing],
                "requirement_checks": requirements,
            }
        )
    return results


def _route_quality(root: Path) -> dict[str, str]:
    checks = {
        "tutorial": {
            "docs/START_HERE.md": bool(_read_text(root, "docs/START_HERE.md")),
            "first_command": "make demo-substrate" in _read_text(root, "README.md"),
        },
        "how_to": {
            "docs/HOW_TO_RUN.md": bool(_read_text(root, "docs/HOW_TO_RUN.md")),
            "route_commands": "python -m aiwf_proof" in _read_text(root, "docs/ROUTES.md"),
        },
        "reference": {
            "docs/REFERENCE.md": bool(_read_text(root, "docs/REFERENCE.md")),
            "manifest": (root / PUBLIC_MANIFEST).exists(),
        },
        "explanation": {
            "docs/EXPLANATION.md": bool(_read_text(root, "docs/EXPLANATION.md")),
            "substrate_doc": bool(_read_text(root, "docs/SUBSTRATE.md")),
        },
    }
    return {key: _status_from_requirements(value) for key, value in checks.items()}


def _claim_surface_payload(root: Path) -> dict[str, Any]:
    scanned_paths = [
        "README.md",
        "index.html",
        "docs/START_HERE.md",
        "docs/ROUTES.md",
        "docs/VISUAL_CONTROL_PLANE.md",
        "docs/SUBSTRATE.md",
        "docs/BOUNDARY.md",
        "LIMITATIONS.md",
        "CLAIMS.md",
    ]
    text_by_path = {rel_path: _read_text(root, rel_path) for rel_path in scanned_paths}
    risky_hits: list[dict[str, Any]] = []
    for phrase in RISKY_WORDS:
        lower_phrase = phrase.lower()
        paths = [
            rel_path
            for rel_path, text in text_by_path.items()
            if lower_phrase in text.lower()
        ]
        risky_hits.append(
            {
                "phrase": phrase,
                "occurrence_paths": paths,
                "required_context": "negative_boundary_or_anti_claim_only",
            }
        )
    return {
        "status": "pass",
        "allowed_claims": ALLOWED_CLAIMS,
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "risky_words": risky_hits,
        "claim_surface_rule": "Allowed claims must stay tied to public commands, receipts, and generated packets; forbidden claims remain blocked by the release shell.",
    }


def _artifact_identity(repo_root: Path, root: Path, source_commit: str) -> dict[str, Any]:
    sequence_path = _repo_path(repo_root, SEQUENCE_PACKET)
    private_visual_path = _repo_path(repo_root, VISUAL_PACKET)
    return {
        "artifact_id": "ai-workflow-proof",
        "generated_root": str(root),
        "source_commit": source_commit,
        "tracked_manifest_path": PUBLIC_MANIFEST,
        "tracked_manifest_sha256": _sha256_file(root / PUBLIC_MANIFEST),
        "visual_packet_path": PUBLIC_VISUAL_PACKET,
        "visual_packet_sha256": _sha256_file(root / PUBLIC_VISUAL_PACKET),
        "private_sequence_packet_path": SEQUENCE_PACKET.as_posix(),
        "private_sequence_packet_sha256": _sha256_file(sequence_path) if sequence_path.exists() else "missing",
        "private_visual_packet_path": VISUAL_PACKET.as_posix(),
        "private_visual_packet_sha256": _sha256_file(private_visual_path) if private_visual_path.exists() else "missing",
    }


def _release_lane_posture(repo_root: Path, root: Path) -> dict[str, Any]:
    public_visual = _load_json(root / PUBLIC_VISUAL_PACKET, {})
    private_sequence = _load_json(_repo_path(repo_root, SEQUENCE_PACKET), {})
    release_lane = public_visual.get("release_lane_posture", {}) if isinstance(public_visual, dict) else {}
    sequence_release = private_sequence.get("release_lane_posture", {}) if isinstance(private_sequence, dict) else {}
    return {
        "public_toggle": release_lane.get("public_toggle", sequence_release.get("public_toggle", "no_go")),
        "release_review_active": False,
        "escrow_current_for_content": release_lane.get(
            "escrow_current_for_content",
            sequence_release.get("escrow_current_for_content", False),
        ),
        "release_candidate_refresh_required_for_public_review": True,
        "stale_reason": "release escrow predates the current flagship sequence and visual control-plane content unless regenerated by release review",
        "release_escrow_packet": RELEASE_ESCROW_PACKET.as_posix(),
    }


def _first_pass_questions(root: Path) -> dict[str, str]:
    readme = _read_text(root, "README.md")
    visual = _read_text(root, "docs/VISUAL_CONTROL_PLANE.md")
    boundary = _read_text(root, "docs/BOUNDARY.md")
    all_text = "\n".join([readme, visual, boundary])
    return {
        "what_is_this": "pass" if "AI Workflow Substrate Miniature" in readme else "fail",
        "what_can_i_run": "pass" if "make demo-substrate" in readme else "fail",
        "what_does_it_prove": "pass" if "flagship sequence" in all_text.lower() or "proof" in all_text.lower() else "warn",
        "what_is_omitted": "pass" if "private root" in all_text.lower() else "fail",
        "why_no_go": "pass" if "no_go" in all_text or "no-go" in all_text.lower() else "fail",
    }


def _decision(command_receipts: list[dict[str, Any]], persona_results: list[dict[str, Any]], route_quality: dict[str, str]) -> str:
    if any(row["status"] == "fail" for row in command_receipts):
        return "patch_sequence"
    if any(row["status"] == "fail" for row in persona_results) or any(value == "fail" for value in route_quality.values()):
        return "patch_front_door"
    if any(row["status"] == "warn" for row in persona_results) or any(value == "warn" for value in route_quality.values()):
        return "patch_front_door"
    return REPORT_DECISION


def _content_posture(
    artifact_identity: dict[str, Any],
    release_lane_posture: dict[str, Any],
    first_run_receipt: dict[str, Any],
    claim_surface_md: str,
    decision: str,
) -> dict[str, Any]:
    return {
        "schema_version": "public_microcosm_report_only_content_posture_v0",
        "work_item_id": "cap_public_microcosm_report_only_content_posture_v0",
        "source_gauntlet": OUTPUT_GAUNTLET.as_posix(),
        "gauntlet_decision": decision,
        "content_state": CONTENT_POSTURE_STATE,
        "release_lane_posture": {
            "public_toggle": release_lane_posture.get("public_toggle", "no_go"),
            "release_review_active": release_lane_posture.get("release_review_active", False),
            "release_candidate_refresh": "not_required_by_smoke_report",
            "escrow_current_for_content": release_lane_posture.get("escrow_current_for_content", False),
        },
        "observed_identity": {
            "source_commit": artifact_identity.get("source_commit"),
            "public_manifest_path": artifact_identity.get("tracked_manifest_path"),
            "public_manifest_sha256": artifact_identity.get("tracked_manifest_sha256"),
            "sequence_packet_path": artifact_identity.get("private_sequence_packet_path"),
            "sequence_packet_sha256": artifact_identity.get("private_sequence_packet_sha256"),
            "visual_packet_path": artifact_identity.get("private_visual_packet_path"),
            "visual_packet_sha256": artifact_identity.get("private_visual_packet_sha256"),
            "public_visual_packet_path": artifact_identity.get("visual_packet_path"),
            "public_visual_packet_sha256": artifact_identity.get("visual_packet_sha256"),
            "claim_surface_path": OUTPUT_CLAIM_SURFACE.as_posix(),
            "claim_surface_sha256": _sha256_text(claim_surface_md),
            "first_run_receipt_path": OUTPUT_FIRST_RUN.as_posix(),
            "first_run_receipt_sha256": _sha256_text(_canonical_json(first_run_receipt)),
        },
        "change_policy": {
            "microcosm_additions": "allowed_by_direct_substrate_queue",
            "front_door_copy": "allowed_only_for_claim_or_legibility_regression",
            "release_escrow_refresh": "not_required_by_smoke_report",
            "unrelated_head_churn": "observed_not_gated",
        },
        "next_allowed_moves": [
            "import_real_substrate",
            "delete_misleading_projection_layer",
            "patch_front_door_if_smoke_report_fails",
        ],
        "forbidden_moves": [
            "release_authority_from_gauntlet_pass",
            "public_toggle_change_without_release_docket_and_operator_approval",
            "claiming_open_source_or_public_reproducibility_without_eligible_checks",
        ],
    }


def build(
    repo_root: Path = REPO_ROOT,
    *,
    public_root: Path = DEFAULT_PUBLIC_ROOT,
    report_path: Path = DEFAULT_REPORT_PATH,
    generated_at: str | None = None,
    run_commands: bool = True,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    previous_gauntlet = _load_json(_repo_path(repo_root, OUTPUT_GAUNTLET), {})
    source_commit = _current_head(repo_root)
    generated_at = generated_at or _commit_timestamp(repo_root, source_commit)
    report = _assemble_public_root(public_root, report_path, generated_at=generated_at)
    manifest = _load_json(public_root / PUBLIC_MANIFEST, {})
    visual_packet = _load_json(public_root / PUBLIC_VISUAL_PACKET, {})
    command_receipts = _run_commands(public_root, timeout_seconds=timeout_seconds) if run_commands else []
    if not run_commands:
        command_receipts = [
            {
                "command_id": command_id,
                "command": _command_to_string(argv),
                "status": "not_run",
                "returncode": None,
                "parsed_status": None,
                "parsed_schema_version": None,
                "computed_receipt_schema_version": None,
                "computed_receipt_microcosm_id": None,
                "stdout_json": False,
                "stderr_present": False,
            }
            for command_id, argv in COMMAND_SUITE
        ]
    persona_results = _persona_results(public_root)
    route_quality = _route_quality(public_root)
    claim_surface = _claim_surface_payload(public_root)
    artifact_identity = _artifact_identity(repo_root, public_root, source_commit)
    release_lane_posture = _release_lane_posture(repo_root, public_root)
    sequence_nodes = visual_packet.get("flagship_sequence_nodes", []) if isinstance(visual_packet, dict) else []
    decision = _decision(command_receipts, persona_results, route_quality)
    first_run_receipt = {
        "schema_version": "public_microcosm_flagship_first_run_receipt_v0",
        "work_item_id": "cap_public_microcosm_flagship_reviewer_gauntlet_v0",
        "generated_at": generated_at,
        "evaluated_source_commit": source_commit,
        "generated_public_root": str(public_root),
        "command_suite_status": "pass" if all(row["status"] == "pass" for row in command_receipts) else "fail",
        "command_receipts": command_receipts,
        "flagship_sequence_nodes": sequence_nodes,
        "visual_route": {
            "path": "site/substrate_map.html",
            "exists": (public_root / "site/substrate_map.html").exists(),
            "sha256": _sha256_file(public_root / "site/substrate_map.html") if (public_root / "site/substrate_map.html").exists() else "missing",
        },
        "release_lane_posture": release_lane_posture,
        "private_state_touched": False,
    }
    gauntlet = {
        "schema_version": "public_microcosm_flagship_reviewer_gauntlet_v0",
        "work_item_id": "cap_public_microcosm_flagship_reviewer_gauntlet_v0",
        "generated_at": generated_at,
        "evaluated_source_commit": source_commit,
        "generated_artifact_identity": artifact_identity,
        "release_lane_posture": release_lane_posture,
        "public_root_report": {
            "path": str(report_path),
            "status": report.get("status"),
            "scan": report.get("scan", {}),
        },
        "flagship_sequence": {
            "required_microcosm_ids": list(FLAGSHIP_SEQUENCE_IDS),
            "nodes": sequence_nodes,
            "status": "pass"
            if set(FLAGSHIP_SEQUENCE_IDS)
            <= {row.get("microcosm_id") for row in sequence_nodes if isinstance(row, dict)}
            else "fail",
        },
        "visual_route": {
            "status": "pass" if (public_root / "site/substrate_map.html").exists() else "fail",
            "path": "site/substrate_map.html",
            "packet_path": PUBLIC_VISUAL_PACKET,
            "first_pass_questions": _first_pass_questions(public_root),
        },
        "command_receipts": command_receipts,
        "persona_results": persona_results,
        "claim_surface": claim_surface,
        "route_quality": route_quality,
        "decision": decision,
        "content_state": CONTENT_POSTURE_STATE,
        "next_patch": {
            "class": "direct_substrate_import_queue_open" if decision == REPORT_DECISION else decision,
            "release_candidate_refresh": "not_required_by_smoke_report",
            "microcosm_additions": "allowed_by_direct_substrate_queue",
        },
    }
    claim_surface_md = _render_claim_surface_md(gauntlet)
    gauntlet["content_posture"] = _content_posture(
        artifact_identity,
        release_lane_posture,
        first_run_receipt,
        claim_surface_md,
        decision,
    )
    if isinstance(previous_gauntlet, dict) and previous_gauntlet:
        posture = previous_gauntlet.get("content_posture", {})
        frozen_identity = posture.get("observed_identity", {}) if isinstance(posture, dict) else {}
        frozen_source_commit = str(frozen_identity.get("source_commit") or previous_gauntlet.get("evaluated_source_commit") or source_commit)
    else:
        frozen_source_commit = source_commit
    changed_paths = _changed_paths_between(repo_root, frozen_source_commit, source_commit)
    public_proof_relevant_changes = _public_proof_relevant_changes(changed_paths)
    gauntlet["change_observation"] = _change_observation_status(
        content_state=str(gauntlet.get("content_state", "not_frozen")),
        frozen_source_commit=frozen_source_commit,
        current_head=source_commit,
        changed_paths=changed_paths,
        public_proof_relevant_changes=public_proof_relevant_changes,
        public_proof_input_fingerprint_before=_public_proof_input_fingerprint(repo_root, frozen_source_commit),
        public_proof_input_fingerprint_now=_public_proof_input_fingerprint(repo_root, source_commit),
        release_lane_posture=release_lane_posture,
        gauntlet_refreshed=bool(public_proof_relevant_changes),
        content_change_lane=_content_change_lane(repo_root),
        release_refresh_lane=_release_refresh_lane(release_lane_posture),
    )
    return {
        "status": "pass"
        if first_run_receipt["command_suite_status"] == "pass"
        and gauntlet["flagship_sequence"]["status"] == "pass"
        and gauntlet["visual_route"]["status"] == "pass"
        and all(row["status"] in {"pass", "warn"} for row in persona_results)
        and gauntlet["change_observation"]["status"] == "pass"
        else "fail",
        "gauntlet": gauntlet,
        "first_run_receipt": first_run_receipt,
        "claim_surface_md": _render_claim_surface_md(gauntlet),
        "gauntlet_md": _render_gauntlet_md(gauntlet),
        "public_root": str(public_root),
        "report_path": str(report_path),
    }


def _render_claim_surface_md(gauntlet: dict[str, Any]) -> str:
    claim_surface = gauntlet["claim_surface"]
    lines = [
        "# Public Microcosm Claim Surface v0",
        "",
        "This is private-preflight guidance for the public-safe proof sequence. It is not public-release approval.",
        "",
        f"- Evaluated source commit: `{gauntlet['evaluated_source_commit']}`",
        f"- Public toggle: `{gauntlet['release_lane_posture']['public_toggle']}`",
        f"- Escrow current for content: `{gauntlet['release_lane_posture']['escrow_current_for_content']}`",
        "",
        "## Allowed Claims",
        "",
        "| Claim ID | Claim | Support |",
        "|---|---|---|",
    ]
    for row in claim_surface["allowed_claims"]:
        support = ", ".join(f"`{item}`" for item in row["support"])
        lines.append(f"| `{row['claim_id']}` | {row['claim']} | {support} |")
    lines.extend(["", "## Forbidden Claims", "", "| Claim ID | Claim |", "|---|---|"])
    for row in claim_surface["forbidden_claims"]:
        lines.append(f"| `{row['claim_id']}` | {row['claim']} |")
    lines.extend(["", "## Risky Wording", "", "| Phrase | Occurrence paths | Required context |", "|---|---|---|"])
    for row in claim_surface["risky_words"]:
        paths = ", ".join(f"`{item}`" for item in row["occurrence_paths"]) if row["occurrence_paths"] else "none"
        lines.append(f"| `{row['phrase']}` | {paths} | {row['required_context']} |")
    lines.extend(
        [
            "",
            "## Rule",
            "",
            claim_surface["claim_surface_rule"],
            "",
        ]
    )
    return "\n".join(lines)


def _render_gauntlet_md(gauntlet: dict[str, Any]) -> str:
    content_posture = gauntlet.get("content_posture") if isinstance(gauntlet.get("content_posture"), dict) else {}
    change_observation = gauntlet.get("change_observation") if isinstance(gauntlet.get("change_observation"), dict) else {}
    lines = [
        "# Public Microcosm Flagship Reviewer Gauntlet v0",
        "",
        "This packet evaluates external legibility for the public-safe proof sequence. It is report-only and does not grant publication authority.",
        "",
        f"- Evaluated source commit: `{gauntlet['evaluated_source_commit']}`",
        f"- Generated public root: `{gauntlet['generated_artifact_identity']['generated_root']}`",
        f"- Public toggle: `{gauntlet['release_lane_posture']['public_toggle']}`",
        f"- Release review active: `{gauntlet['release_lane_posture']['release_review_active']}`",
        f"- Escrow current for content: `{gauntlet['release_lane_posture']['escrow_current_for_content']}`",
        f"- Decision: `{gauntlet['decision']}`",
        f"- Content state: `{gauntlet.get('content_state', 'unknown')}`",
        "",
        "## Command Suite",
        "",
        "| Command ID | Status | Parsed status | Command |",
        "|---|---|---|---|",
    ]
    for row in gauntlet["command_receipts"]:
        lines.append(
            f"| `{row['command_id']}` | `{row['status']}` | `{row.get('parsed_status')}` | `{row['command']}` |"
        )
    lines.extend(["", "## Persona Matrix", "", "| Persona | Status | First command | Remaining question |", "|---|---|---|---|"])
    for row in gauntlet["persona_results"]:
        answers = row["answers"]
        lines.append(
            f"| `{row['persona_id']}` | `{row['status']}` | `{answers['first_command']}` | {answers['what_next_question_remains']} |"
        )
    lines.extend(["", "## Route Quality", "", "| Need | Status |", "|---|---|"])
    for key, value in gauntlet["route_quality"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## First-Pass Questions", "", "| Question | Status |", "|---|---|"])
    for key, value in gauntlet["visual_route"]["first_pass_questions"].items():
        lines.append(f"| `{key}` | `{value}` |")
    if content_posture:
        identity = content_posture.get("observed_identity", {})
        policy = content_posture.get("change_policy", {})
        lines.extend(
            [
                "",
                "## Content Posture",
                "",
                f"- Work item: `{content_posture.get('work_item_id')}`",
                f"- Content state: `{content_posture.get('content_state')}`",
                f"- Source commit: `{identity.get('source_commit')}`",
                f"- Public manifest SHA256: `{identity.get('public_manifest_sha256')}`",
                f"- Sequence packet SHA256: `{identity.get('sequence_packet_sha256')}`",
                f"- Visual packet SHA256: `{identity.get('visual_packet_sha256')}`",
                f"- Claim surface SHA256: `{identity.get('claim_surface_sha256')}`",
                f"- First-run receipt SHA256: `{identity.get('first_run_receipt_sha256')}`",
                f"- Microcosm additions: `{policy.get('microcosm_additions')}`",
                f"- Release escrow refresh: `{policy.get('release_escrow_refresh')}`",
                f"- Unrelated HEAD churn: `{policy.get('unrelated_head_churn')}`",
            ]
        )
    if change_observation:
        changed_inputs = change_observation.get("changed_public_proof_inputs", [])
        lines.extend(
            [
                "",
                "## Change Observation",
                "",
                f"- Status: `{change_observation.get('status')}`",
                f"- Reason: `{change_observation.get('reason')}`",
                f"- Accepted change lane: `{change_observation.get('accepted_change_lane')}`",
                f"- Observed source commit: `{change_observation.get('frozen_source_commit')}`",
                f"- Current HEAD: `{change_observation.get('current_head')}`",
                f"- Public-proof input fingerprint before: `{change_observation.get('public_proof_input_fingerprint_before')}`",
                f"- Public-proof input fingerprint now: `{change_observation.get('public_proof_input_fingerprint_now')}`",
                f"- Changed public-proof inputs: `{len(changed_inputs)}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Next Patch",
            "",
            f"- Class: `{gauntlet['next_patch']['class']}`",
            f"- Release candidate refresh: `{gauntlet['next_patch']['release_candidate_refresh']}`",
            f"- Microcosm additions: `{gauntlet['next_patch']['microcosm_additions']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(repo_root: Path = REPO_ROOT, *, public_root: Path = DEFAULT_PUBLIC_ROOT) -> dict[str, Any]:
    payloads = build(repo_root, public_root=public_root)
    targets = {
        OUTPUT_GAUNTLET: _canonical_json(payloads["gauntlet"]),
        OUTPUT_GAUNTLET_MD: payloads["gauntlet_md"],
        OUTPUT_FIRST_RUN: _canonical_json(payloads["first_run_receipt"]),
        OUTPUT_CLAIM_SURFACE: payloads["claim_surface_md"],
    }
    written: list[str] = []
    for rel_path, content in targets.items():
        path = _repo_path(repo_root, rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
        written.append(rel_path.as_posix())
    return {
        "status": payloads["status"],
        "paths": written,
        "public_root": payloads["public_root"],
        "report_path": payloads["report_path"],
    }


def check_outputs(repo_root: Path = REPO_ROOT, *, public_root: Path = DEFAULT_PUBLIC_ROOT) -> dict[str, Any]:
    existing = _load_json(_repo_path(repo_root, OUTPUT_GAUNTLET), {})
    generated_at = existing.get("generated_at") if isinstance(existing, dict) else None
    evaluated_source_commit = existing.get("evaluated_source_commit") if isinstance(existing, dict) else None
    current_head = _current_head(repo_root)
    payloads = build(repo_root, public_root=public_root, generated_at=generated_at)
    expected = {
        OUTPUT_GAUNTLET: _canonical_json(payloads["gauntlet"]),
        OUTPUT_GAUNTLET_MD: payloads["gauntlet_md"],
        OUTPUT_FIRST_RUN: _canonical_json(payloads["first_run_receipt"]),
        OUTPUT_CLAIM_SURFACE: payloads["claim_surface_md"],
    }
    missing: list[str] = []
    mismatches: list[str] = []
    for rel_path, content in expected.items():
        path = _repo_path(repo_root, rel_path)
        if not path.exists():
            missing.append(rel_path.as_posix())
            continue
        if path.read_text(encoding="utf-8") != str(content):
            mismatches.append(rel_path.as_posix())
    changed_paths = (
        _changed_paths_between(repo_root, str(evaluated_source_commit), current_head)
        if evaluated_source_commit
        else []
    )
    public_proof_relevant_changes = _public_proof_relevant_changes(changed_paths)
    change_observation = (
        _change_observation_from_existing(
            repo_root,
            existing,
            current_head=current_head,
            gauntlet_refreshed=not missing and not mismatches and payloads["status"] == "pass",
        )
        if isinstance(existing, dict)
        else {
            "status": "fail",
            "reason": "missing_existing_gauntlet",
            "changed_public_proof_inputs": [],
        }
    )
    unrelated_head_advance = bool(mismatches) and bool(evaluated_source_commit) and not public_proof_relevant_changes
    status = "in_sync" if not missing and not mismatches and payloads["status"] == "pass" else "out_of_sync"
    if status == "out_of_sync" and not missing and payloads["status"] == "pass" and unrelated_head_advance:
        status = "in_sync_unrelated_head_advance"
    if (
        status == "out_of_sync"
        and not missing
        and payloads["status"] == "pass"
        and change_observation.get("status") == "pass"
        and change_observation.get("reason")
        in {"content_change_lane_open", "release_review_refresh_lane_open"}
    ):
        status = str(change_observation["reason"])
    if change_observation.get("status") == "fail":
        status = str(change_observation.get("reason") or "change_observation_failed")
    return {
        "status": status,
        "gauntlet_status": payloads["status"],
        "change_observation": change_observation,
        "missing": missing,
        "mismatches": mismatches,
        "evaluated_source_commit": evaluated_source_commit,
        "current_head": current_head,
        "changed_path_count_since_evaluation": len(changed_paths),
        "public_proof_relevant_changes_since_evaluation": public_proof_relevant_changes,
        "public_root": payloads["public_root"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--public-root", type=Path, default=DEFAULT_PUBLIC_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        result = check_outputs(args.repo_root, public_root=args.public_root)
        print(_canonical_json(result), end="")
        return 0 if result["status"] in {
            "in_sync",
            "in_sync_unrelated_head_advance",
            "content_change_lane_open",
            "release_review_refresh_lane_open",
        } else 1

    result = write_outputs(args.repo_root, public_root=args.public_root)
    print(_canonical_json(result), end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
