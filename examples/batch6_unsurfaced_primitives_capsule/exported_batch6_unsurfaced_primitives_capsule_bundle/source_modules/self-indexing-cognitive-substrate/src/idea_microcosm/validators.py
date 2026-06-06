from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atlas_navigation_specimen import EXPECTED_BANDS as ATLAS_NAVIGATION_EXPECTED_BANDS
from .release_candidates import ALLOWED_SPECIMEN_STATUSES, candidate_shape_failures
from .release_root_compiler import (
    BRANCH_GRAPH_PATH,
    RECEIPT_PATH as RELEASE_ROOT_COMPILER_RECEIPT_PATH,
    ROOT_CONTRACT_PATH,
    STD_PYTHON_REPORT_PATH,
    validate_release_root_artifacts,
)


_PRIVATE_CHROME_PROFILE = "Library/Application Support/" + "Google/Chrome"
_RAW_EXPLETIVE = "f" + "uck"

PRIVATE_PATTERNS = {
    "private_home_path": re.compile(r"/Users/[A-Za-z0-9_.-]+"),
    "private_email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "private_chrome_profile": re.compile(re.escape(_PRIVATE_CHROME_PROFILE)),
    "secret_private_key": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)?PRIVATE KEY"),
    "openai_key_shape": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "github_token_shape": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "slack_token_shape": re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "aws_access_key_shape": re.compile(r"AKIA[0-9A-Z]{16}"),
    "raw_voice_expletive": re.compile(r"\b(?:" + _RAW_EXPLETIVE + r"|" + _RAW_EXPLETIVE + r"ing)\b", re.IGNORECASE),
}

ALLOWED_LICENSE_GRANT_STATUSES = {
    "no_public_license_selected",
    "Apache-2.0_selected_pending_public_toggle",
}
TELEOLOGY_GATE_PATH = Path("strategy/microcosm_teleology_gate.json")


def _json_sha256(payload: Any) -> str:
    stable_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def _optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _retired_candidate_ids(root: Path) -> set[str]:
    gate = _optional_json(root / TELEOLOGY_GATE_PATH)
    return {str(value) for value in gate.get("retired_candidate_ids", []) if isinstance(value, str)}


STATUS_COLLAPSE_SUITE_PATH = Path("fixtures/status/status_collapse_adversarial_suite.json")
EXPECTED_STATUS_COLLAPSE_CASE_IDS = {
    "source_nonrelease_boundary",
    "atom_overupgrade_attempt",
    "workitem_complete_without_receipt",
    "receipt_to_truth_overclaim",
    "runtime_projection_without_freshness_owner",
    "delayed_truth_hindsight_rewrite",
    "private_source_dependency_in_fixture",
    "reviewer_feedback_authority_overclaim",
}
RELEASE_CANDIDATE_REQUIRED_FIELDS = {
    "candidate_id",
    "title",
    "idea_family",
    "five_sentence_release_summary",
    "source_refs",
    "python_refs",
    "standard_refs",
    "skill_refs",
    "concept_refs",
    "receipt_refs",
    "projection_strategy",
    "improvement_delta",
    "public_safety_status",
    "runnability_status",
    "video_demo_potential",
    "external_review_potential",
    "blocked_by",
    "next_action",
    "release_priority",
    "anti_claims",
    "cold_sandbox_status",
    "hosted_public_status",
    "publication_status",
}
LEGAL_STATUS_STATES = {
    "source_recorded",
    "interpretation_proposed",
    "work_requested",
    "validation_required",
    "receipt_observed",
    "fit_for_local_action",
    "fit_for_public_claim",
    "fixture_constructed",
    "projection_visible",
    "truth_arrived",
    "reviewer_feedback_received",
    "blocked",
    "downgraded",
    "repaired",
    "retired",
}
ALLOWED_STATUS_SUITE_RESULTS = {"blocked", "downgraded", "repair_routed", "no_op_routed"}
POLICY_DECISION_TO_OBSERVED_RESULT = {
    "allow": "allowed",
    "block": "blocked",
    "downgrade": "downgraded",
    "route_repair": "repair_routed",
    "route_no_op": "no_op_routed",
}
ALLOWED_POLICY_DECISIONS = set(POLICY_DECISION_TO_OBSERVED_RESULT)
EXPECTED_CLAIM_TIER_LATTICE = [
    "Unsupported",
    "ManuscriptSpecified",
    "FixtureSpecified",
    "FixtureValidated",
    "PublicReproducible",
    "ControlledReviewCorroborated",
    "ProductionValidated",
]
CLAIM_TIER_RANK = {tier: index for index, tier in enumerate(EXPECTED_CLAIM_TIER_LATTICE)}
AUTHORITY_INCREASING_TARGET_STATES = {
    "fit_for_public_release",
    "doctrine_authority",
    "truth_authority",
    "source_authority",
    "forward_claim_rewritten",
    "private_source_corpus_equivalence_claim",
    "claim_tier_upgrade",
}
PUBLIC_CLAIM_TARGET_STATES = {
    "fit_for_public_claim",
    "fit_for_public_release",
    "private_source_corpus_equivalence_claim",
    "claim_tier_upgrade",
}
REQUIRED_STATUS_COLLAPSE_CASE_FIELDS = {
    "case_id",
    "source_object",
    "status_collapse_threat",
    "artifact_under_test",
    "legal_transition",
    "forbidden_transition",
    "required_evidence",
    "test_check",
    "observed_result",
    "downgrade_if_failed",
    "public_private_boundary",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no} invalid JSONL: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no} row must be an object")
        rows.append(row)
    return rows


def _text_files(root: Path):
    skip_dirs = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache"}
    for path in root.rglob("*"):
        if any(part in skip_dirs for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".sqlite"}:
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        yield path


def private_boundary_hits(root: Path) -> list[dict[str, Any]]:
    hits = []
    for path in _text_files(root):
        text = path.read_text(encoding="utf-8")
        for name, pattern in PRIVATE_PATTERNS.items():
            for match in pattern.finditer(text):
                hits.append(
                    {
                        "pattern": name,
                        "path": str(path.relative_to(root)),
                        "offset": match.start(),
                    }
                )
    return hits


def _validate_transition(
    failures: list[dict[str, Any]],
    *,
    case_id: str,
    field: str,
    transition: Any,
    states: set[str],
) -> None:
    if not isinstance(transition, dict):
        failures.append({"case_id": case_id, "field": field, "reason": "transition must be an object"})
        return
    start = transition.get("from")
    end = transition.get("to")
    if start not in states:
        failures.append({"case_id": case_id, "field": field, "unknown_from_state": start})
    if end not in states and end not in {"fit_for_public_release", "doctrine_authority", "truth_authority", "source_authority", "forward_claim_rewritten", "private_source_corpus_equivalence_claim", "claim_tier_upgrade"}:
        failures.append({"case_id": case_id, "field": field, "unknown_to_state": end})
    if field == "forbidden_transition" and not transition.get("reason"):
        failures.append({"case_id": case_id, "field": field, "reason": "forbidden transition must name why it is illegal"})


def _transition_key(transition: Any) -> tuple[str | None, str | None]:
    if not isinstance(transition, dict):
        return (None, None)
    return (transition.get("from"), transition.get("to"))


def _transition_matches(row: Any, request: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False
    return row.get("from") == request.get("from") and row.get("to") == request.get("to")


def _transition_keys(rows: Any) -> set[tuple[str | None, str | None]]:
    if not isinstance(rows, list):
        return set()
    return {_transition_key(row) for row in rows if isinstance(row, dict)}


def _refs_are_nonempty_strings(refs: Any) -> bool:
    return isinstance(refs, list) and bool(refs) and all(isinstance(ref, str) and ref for ref in refs)


def policy_wellformedness_failures(policy: dict[str, Any], state_set: set[str] | None = None) -> list[dict[str, Any]]:
    """Return policy-level failures before judging individual status requests.

    The suite's policy is part of the trusted control plane. A malformed policy
    must not be treated as a permissive policy, because that would move status
    laundering from artifacts into the policy table itself.
    """
    failures: list[dict[str, Any]] = []
    if not isinstance(policy, dict):
        return [{"path": "policy_judgment", "reason": "policy must be an object"}]

    wellformedness = policy.get("policy_wellformedness")
    if not isinstance(wellformedness, dict):
        failures.append({"path": "policy_judgment.policy_wellformedness", "reason": "policy well-formedness rules missing"})
    elif wellformedness.get("policy_poisoning_default") != "malformed_policy_blocks_judgment":
        failures.append({"path": "policy_judgment.policy_wellformedness", "reason": "policy poisoning default must block judgment"})

    tier_model = policy.get("tier_model")
    if not isinstance(tier_model, dict):
        failures.append({"path": "policy_judgment.tier_model", "reason": "tier model missing"})
    elif tier_model.get("model_type") != "product_tiers_with_fixture_ordering_projection":
        failures.append({"path": "policy_judgment.tier_model", "reason": "tier model must distinguish product axes from fixture ordering"})

    allowed_keys = _transition_keys(policy.get("allowed_transitions"))
    prohibited_keys = _transition_keys(policy.get("prohibited_upgrades"))
    for transition_key in sorted(allowed_keys & prohibited_keys):
        failures.append(
            {
                "path": "policy_judgment.allowed_transitions",
                "reason": "allowed transition contradicts prohibited upgrade",
                "transition": list(transition_key),
            }
        )

    required_evidence_keys = _transition_keys(policy.get("required_evidence"))
    required_gate_keys = _transition_keys(policy.get("required_gates"))
    for row in policy.get("allowed_transitions", []):
        if not isinstance(row, dict):
            continue
        transition_key = _transition_key(row)
        target = row.get("to")
        if target in AUTHORITY_INCREASING_TARGET_STATES and transition_key not in required_gate_keys:
            failures.append(
                {
                    "path": "policy_judgment.allowed_transitions",
                    "reason": "authority-increasing transition lacks required gate",
                    "transition": list(transition_key),
                }
            )
        if target in PUBLIC_CLAIM_TARGET_STATES and transition_key not in required_evidence_keys:
            failures.append(
                {
                    "path": "policy_judgment.allowed_transitions",
                    "reason": "public-claim transition lacks required evidence",
                    "transition": list(transition_key),
                }
            )

    for group_name in ("required_evidence", "required_gates"):
        for row in policy.get(group_name, []):
            if not isinstance(row, dict):
                failures.append({"path": f"policy_judgment.{group_name}", "reason": "policy requirement row must be an object"})
                continue
            if not _refs_are_nonempty_strings(row.get("refs")):
                failures.append(
                    {
                        "path": f"policy_judgment.{group_name}",
                        "reason": "policy requirement refs must be non-empty string refs",
                        "transition": list(_transition_key(row)),
                    }
                )
            decision = row.get("decision_if_missing", "downgrade" if group_name == "required_evidence" else "block")
            if decision not in ALLOWED_POLICY_DECISIONS:
                failures.append({"path": f"policy_judgment.{group_name}", "reason": "invalid missing-requirement decision", "decision": decision})

    for row in policy.get("downgrade_rules", []):
        if not isinstance(row, dict):
            failures.append({"path": "policy_judgment.downgrade_rules", "reason": "downgrade rule must be an object"})
            continue
        from_tier = row.get("from_tier")
        to_tier = row.get("to_tier")
        if from_tier not in CLAIM_TIER_RANK or to_tier not in CLAIM_TIER_RANK:
            failures.append({"path": "policy_judgment.downgrade_rules", "reason": "downgrade rule names unknown tier"})
        elif CLAIM_TIER_RANK[to_tier] >= CLAIM_TIER_RANK[from_tier]:
            failures.append(
                {
                    "path": "policy_judgment.downgrade_rules",
                    "reason": "downgrade rule must weaken tier",
                    "from_tier": from_tier,
                    "to_tier": to_tier,
                }
            )
        if not row.get("weaker_claim"):
            failures.append({"path": "policy_judgment.downgrade_rules", "reason": "downgrade rule must name weaker claim"})

    default_decision = policy.get("default_decision", {})
    if isinstance(default_decision, dict) and default_decision.get("decision", "block") not in ALLOWED_POLICY_DECISIONS:
        failures.append({"path": "policy_judgment.default_decision", "reason": "invalid default decision"})

    if state_set is not None:
        legal_targets = state_set | AUTHORITY_INCREASING_TARGET_STATES | {"doctrine_authority", "truth_authority", "source_authority"}
        for group_name in ("allowed_transitions", "prohibited_upgrades", "required_evidence", "required_gates"):
            for row in policy.get(group_name, []):
                if not isinstance(row, dict):
                    continue
                start, end = _transition_key(row)
                if start not in state_set:
                    failures.append({"path": f"policy_judgment.{group_name}", "reason": "unknown from-state", "transition": [start, end]})
                if end not in legal_targets:
                    failures.append({"path": f"policy_judgment.{group_name}", "reason": "unknown to-state", "transition": [start, end]})

    return failures


def _decision_payload(row: dict[str, Any], decision: str) -> dict[str, Any]:
    return {
        "decision": decision,
        "observed_result": POLICY_DECISION_TO_OBSERVED_RESULT[decision],
        "reason": row.get("reason", ""),
        "weaker_claim": row.get("weaker_claim"),
        "weaker_tier": row.get("weaker_tier"),
        "required_refs": row.get("refs", []),
        "missing_refs": row.get("missing_refs", []),
    }


def judge_status_request(policy: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one requested status move against the suite policy.

    The case fixture can carry artifacts and labels, but the decision comes from a
    separately governed policy object. That keeps generated artifacts from
    declaring their own allowed upgrades.
    """
    if not isinstance(policy, dict):
        return {
            "decision": "block",
            "observed_result": "blocked",
            "reason": "missing_policy",
            "weaker_claim": None,
            "weaker_tier": None,
            "required_refs": [],
            "missing_refs": [],
        }
    if not isinstance(request, dict):
        return {
            "decision": "block",
            "observed_result": "blocked",
            "reason": "malformed_request",
            "weaker_claim": None,
            "weaker_tier": None,
            "required_refs": [],
            "missing_refs": [],
        }

    if policy_wellformedness_failures(policy):
        return {
            "decision": "block",
            "observed_result": "blocked",
            "reason": "policy_not_wellformed",
            "weaker_claim": None,
            "weaker_tier": None,
            "required_refs": [],
            "missing_refs": [],
        }

    for row in policy.get("prohibited_upgrades", []):
        if _transition_matches(row, request):
            decision = row.get("decision", "block")
            if decision not in ALLOWED_POLICY_DECISIONS:
                decision = "block"
            return _decision_payload(row, decision)

    for row in policy.get("allowed_transitions", []):
        if not _transition_matches(row, request):
            continue
        evidence_refs = set(request.get("evidence_refs", []))
        gate_refs = set(request.get("gate_refs", []))
        for requirement in policy.get("required_evidence", []):
            if not _transition_matches(requirement, request):
                continue
            required_refs = {ref for ref in requirement.get("refs", []) if isinstance(ref, str)}
            missing_refs = sorted(required_refs - evidence_refs)
            if missing_refs:
                payload = _decision_payload(requirement, requirement.get("decision_if_missing", "downgrade"))
                payload["missing_refs"] = missing_refs
                return payload
        for requirement in policy.get("required_gates", []):
            if not _transition_matches(requirement, request):
                continue
            required_refs = {ref for ref in requirement.get("refs", []) if isinstance(ref, str)}
            missing_refs = sorted(required_refs - gate_refs)
            if missing_refs:
                payload = _decision_payload(requirement, requirement.get("decision_if_missing", "block"))
                payload["missing_refs"] = missing_refs
                return payload
        return _decision_payload(row, "allow")

    default = policy.get("default_decision", {})
    if not isinstance(default, dict):
        default = {}
    decision = default.get("decision", "block")
    if decision not in ALLOWED_POLICY_DECISIONS:
        decision = "block"
    return _decision_payload({"reason": default.get("reason", "transition_not_in_policy")}, decision)


def _validate_policy_judgment(
    failures: list[dict[str, Any]],
    *,
    suite: dict[str, Any],
    state_set: set[str],
) -> dict[str, Any]:
    policy = suite.get("policy_judgment")
    if not isinstance(policy, dict):
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "policy_judgment missing"})
        return {}

    if policy.get("judgment_form") != "judge(policy, artifact_graph, request) -> Allow | Block | Downgrade | RouteRepair | NoOp":
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "policy_judgment must name the judgment form"})
    if policy.get("artifact_policy_boundary") != "artifacts_carry_labels_policy_governs_transitions":
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "policy must be separate from artifact self-declaration"})
    if policy.get("claim_tier_lattice") != EXPECTED_CLAIM_TIER_LATTICE:
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "claim_tier_lattice mismatch"})
    for failure in policy_wellformedness_failures(policy, state_set):
        failure.setdefault("path", str(STATUS_COLLAPSE_SUITE_PATH))
        failures.append(failure)

    for group_name in ("allowed_transitions", "prohibited_upgrades"):
        rows = policy.get(group_name)
        if not isinstance(rows, list) or not rows:
            failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "field": group_name, "reason": "must be a non-empty list"})
            continue
        seen: set[tuple[str | None, str | None]] = set()
        for row in rows:
            if not isinstance(row, dict):
                failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "field": group_name, "reason": "policy row must be an object"})
                continue
            transition_key = _transition_key(row)
            if transition_key in seen:
                failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "field": group_name, "duplicate_transition": list(transition_key)})
            seen.add(transition_key)
            _validate_transition(
                failures,
                case_id=f"policy.{group_name}",
                field=group_name,
                transition=row,
                states=state_set,
            )
            decision = row.get("decision", "allow" if group_name == "allowed_transitions" else "block")
            if decision not in ALLOWED_POLICY_DECISIONS:
                failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "field": group_name, "decision": decision})
    return policy


def _status_collapse_suite_failures(root: Path) -> list[dict[str, Any]]:
    suite_path = root / STATUS_COLLAPSE_SUITE_PATH
    failures: list[dict[str, Any]] = []
    if not suite_path.exists():
        return [{"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "missing adversarial status-collapse suite"}]

    suite = load_json(suite_path)
    if suite.get("schema_version") != "status_collapse_adversarial_suite_v0":
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "unexpected schema_version"})
    if suite.get("authority_posture") != "public_safe_synthetic_fixture_not_private_source_corpus_authority":
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "unexpected authority_posture"})

    states = suite.get("status_states")
    if not isinstance(states, list) or not states:
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "status_states missing"})
        state_set = set(LEGAL_STATUS_STATES)
    else:
        state_set = {str(state) for state in states}
        missing_states = sorted(LEGAL_STATUS_STATES - state_set)
        if missing_states:
            failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "missing_states": missing_states})

    policy = _validate_policy_judgment(failures, suite=suite, state_set=state_set)

    cases = suite.get("cases")
    if not isinstance(cases, list):
        return failures + [{"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "cases must be a list"}]

    case_ids = {case.get("case_id") for case in cases if isinstance(case, dict)}
    missing_case_ids = sorted(EXPECTED_STATUS_COLLAPSE_CASE_IDS - case_ids)
    extra_case_ids = sorted(str(case_id) for case_id in case_ids - EXPECTED_STATUS_COLLAPSE_CASE_IDS)
    if missing_case_ids:
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "missing_case_ids": missing_case_ids})
    if extra_case_ids:
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "extra_case_ids": extra_case_ids})
    if suite.get("case_count") != len(cases):
        failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "case_count": suite.get("case_count"), "expected": len(cases)})

    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": str(STATUS_COLLAPSE_SUITE_PATH), "reason": "case row must be an object"})
            continue
        case_id = str(case.get("case_id"))
        missing = sorted(field for field in REQUIRED_STATUS_COLLAPSE_CASE_FIELDS if case.get(field) in ("", None, [], {}))
        if missing:
            failures.append({"case_id": case_id, "missing": missing})
        if case.get("observed_result") not in ALLOWED_STATUS_SUITE_RESULTS:
            failures.append({"case_id": case_id, "observed_result": case.get("observed_result")})
        required_evidence = case.get("required_evidence")
        if not isinstance(required_evidence, list) or not all(isinstance(ref, str) and ref for ref in required_evidence):
            failures.append({"case_id": case_id, "reason": "required_evidence must be non-empty string refs"})
        boundary = str(case.get("public_private_boundary", "")).lower()
        if "private" not in boundary or (
            "synthetic" not in boundary and "no " not in boundary and "not " not in boundary
        ):
            failures.append({"case_id": case_id, "reason": "public_private_boundary must name synthetic/no-private boundary"})
        _validate_transition(
            failures,
            case_id=case_id,
            field="legal_transition",
            transition=case.get("legal_transition"),
            states=state_set,
        )
        _validate_transition(
            failures,
            case_id=case_id,
            field="forbidden_transition",
            transition=case.get("forbidden_transition"),
            states=state_set,
        )
        if policy:
            legal_request = {
                **case.get("legal_transition", {}),
                "evidence_refs": case.get("required_evidence", []),
                "case_id": case_id,
            }
            legal_decision = judge_status_request(policy, legal_request)
            if legal_decision.get("decision") != "allow":
                failures.append(
                    {
                        "case_id": case_id,
                        "field": "legal_transition",
                        "reason": "legal transition was not allowed by policy judgment",
                        "decision": legal_decision,
                    }
                )
            illegal_request = {
                **case.get("forbidden_transition", {}),
                "evidence_refs": case.get("required_evidence", []),
                "case_id": case_id,
            }
            illegal_decision = judge_status_request(policy, illegal_request)
            if illegal_decision.get("decision") == "allow":
                failures.append({"case_id": case_id, "field": "forbidden_transition", "reason": "illegal transition was allowed"})
            if illegal_decision.get("observed_result") != case.get("observed_result"):
                failures.append(
                    {
                        "case_id": case_id,
                        "field": "observed_result",
                        "expected": case.get("observed_result"),
                        "policy_observed_result": illegal_decision.get("observed_result"),
                    }
                )

    return failures


def _status_preserving_control_plane_specimen_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "status_preserving_control_plane" / "control_plane_board.json"
    lattice_ref = "microcosms/status_preserving_control_plane/claim_inference_authority_lattice.json"
    lattice_path = root / lattice_ref
    receipt_path = root / "microcosms" / "status_preserving_control_plane" / "receipt.json"
    readme_path = root / "microcosms" / "status_preserving_control_plane" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "missing control-plane board"})
    if not lattice_path.exists():
        failures.append({"path": lattice_ref, "reason": "missing claim-inference authority lattice"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/status_preserving_control_plane/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/status_preserving_control_plane/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    lattice = load_json(lattice_path)
    receipt = load_json(receipt_path)
    readme = readme_path.read_text(encoding="utf-8")
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "status": board.get("status")})
    if board.get("candidate_id") != "status_preserving_control_plane_microcosm":
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "unexpected candidate_id"})
    if board.get("authority_posture") != "public_safe_synthetic_status_control_plane_not_private_root_or_publication_authority":
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "unexpected authority posture"})
    if "public-release-ready" in json.dumps(board).lower() or "public-release-ready" in readme.lower():
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "specimen must not imply public release readiness"})

    summary = board.get("summary", {})
    decision_rows = board.get("decision_rows", [])
    if not isinstance(decision_rows, list) or len(decision_rows) < len(EXPECTED_STATUS_COLLAPSE_CASE_IDS):
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "missing decision rows"})
        decision_rows = []
    if summary.get("case_count") != len(decision_rows):
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "summary case_count mismatch"})
    if summary.get("legal_allow_count") != len(decision_rows):
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "every legal transition must be allowed"})
    if summary.get("illegal_allowed_count") != 0:
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "forbidden transitions must not be allowed"})
    if summary.get("observed_mismatch_count") != 0:
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "policy observed results must match fixture expectations"})
    if summary.get("artifact_self_authority_count") != 0:
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "artifacts must not be status authority"})
    if summary.get("status_authority_nodes") != ["policy_judgment_engine", "receipt_gate"]:
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "status authority nodes mismatch"})

    authority_nodes = [
        row.get("node_id")
        for row in board.get("authority_trace", [])
        if isinstance(row, dict) and row.get("status_authority") is True
    ]
    if authority_nodes != ["policy_judgment_engine", "receipt_gate"]:
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "authority trace mismatch"})

    case_ids = {row.get("case_id") for row in decision_rows if isinstance(row, dict)}
    missing_case_ids = sorted(EXPECTED_STATUS_COLLAPSE_CASE_IDS - case_ids)
    if missing_case_ids:
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "missing_case_ids": missing_case_ids})
    observed_forbidden_results = set()
    for row in decision_rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "decision row must be an object"})
            continue
        case_id = row.get("case_id")
        legal_decision = row.get("legal_decision", {})
        forbidden_decision = row.get("forbidden_decision", {})
        if not isinstance(legal_decision, dict) or legal_decision.get("decision") != "allow":
            failures.append({"case_id": case_id, "reason": "legal transition must be allowed"})
        if not isinstance(forbidden_decision, dict) or forbidden_decision.get("decision") == "allow":
            failures.append({"case_id": case_id, "reason": "forbidden transition must not be allowed"})
        if forbidden_decision.get("observed_result") != row.get("expected_observed_result"):
            failures.append({"case_id": case_id, "reason": "forbidden transition observed result mismatch"})
        observed_forbidden_results.add(forbidden_decision.get("observed_result"))
        if row.get("artifact_self_authority_used") is not False:
            failures.append({"case_id": case_id, "reason": "artifact self-authority must be false"})
        if row.get("status_authority") != "policy_judgment_engine_only":
            failures.append({"case_id": case_id, "reason": "decision row must name policy_judgment_engine_only authority"})
    if not {"blocked", "downgraded", "repair_routed"}.issubset(observed_forbidden_results):
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "specimen must demonstrate block, downgrade, and repair-route outcomes"})

    if board.get("claim_inference_authority_lattice_ref") != lattice_ref:
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "missing claim-inference authority lattice ref"})
    if board.get("claim_inference_authority_lattice_summary") != lattice.get("status"):
        failures.append({"path": "microcosms/status_preserving_control_plane/control_plane_board.json", "reason": "lattice summary mismatch"})

    if lattice.get("kind") != "claim_inference_authority_lattice":
        failures.append({"path": lattice_ref, "reason": "unexpected lattice kind"})
    if lattice.get("schema_version") != "claim_inference_authority_lattice_v0":
        failures.append({"path": lattice_ref, "reason": "unexpected lattice schema"})
    generated_by = lattice.get("generated_by", {})
    if generated_by.get("projection_not_authority") is not True:
        failures.append({"path": lattice_ref, "reason": "lattice projection must declare projection_not_authority"})
    lattice_cases = lattice.get("mechanism", {}).get("cases", [])
    lattice_status = lattice.get("status", {})
    lattice_authority = lattice.get("authority", {})
    if not isinstance(lattice_cases, list) or len(lattice_cases) < len(decision_rows):
        failures.append({"path": lattice_ref, "reason": "lattice must cover every decision row"})
        lattice_cases = []
    if lattice_status.get("case_count") != len(lattice_cases):
        failures.append({"path": lattice_ref, "reason": "lattice case_count mismatch"})
    if lattice_status.get("capsule_count") != len(lattice_cases):
        failures.append({"path": lattice_ref, "reason": "lattice capsule_count mismatch"})
    if lattice_status.get("missing_ref_count") != 0:
        failures.append({"path": lattice_ref, "reason": "lattice missing_ref_count must be zero"})
    if lattice_authority.get("self_attestation_count") != 0:
        failures.append({"path": lattice_ref, "reason": "lattice self-attestation must not become authority"})
    if lattice_authority.get("evaluator_authority_count") != len(lattice_cases):
        failures.append({"path": lattice_ref, "reason": "lattice evaluator authority count mismatch"})
    if "hosted_public_status" not in lattice_authority.get("fail_closed_gates", []):
        failures.append({"path": lattice_ref, "reason": "lattice must keep hosted public gate fail-closed"})
    if not lattice.get("route", {}).get("first_command"):
        failures.append({"path": lattice_ref, "reason": "lattice route must expose a runnable first command"})
    for case in lattice_cases:
        if not isinstance(case, dict):
            failures.append({"path": lattice_ref, "reason": "lattice case must be an object"})
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip")
        source_hash = case.get("source_clip_hash")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case missing source_clip"})
        elif source_hash != hashlib.sha256(source_clip.encode("utf-8")).hexdigest():
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice source_clip_hash mismatch"})
        if not case.get("semantic_carryforward"):
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case missing semantic carryforward"})
        if case.get("evaluator_or_validator") != "claim_inference_authority_lattice_evaluator":
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case must use evaluator authority"})
        if not case.get("repair_route"):
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "blocked lattice case missing repair route"})
        if not case.get("restart_point"):
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case missing teaching rule"})
        if not case.get("evidence_refs"):
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case missing evidence refs"})
        if not case.get("anti_claims"):
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case missing anti-claims"})
        if not case.get("permitted_inference") or not case.get("forbidden_inference"):
            failures.append({"path": lattice_ref, "case_id": case_id, "reason": "lattice case missing inference boundary"})
        for ref in case.get("evidence_refs", []):
            is_path_shaped_ref = isinstance(ref, str) and ("/" in ref or ref.endswith((".json", ".md", ".py")))
            if is_path_shaped_ref and ref and not _path_ref_exists(root, ref):
                failures.append({"path": lattice_ref, "case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/status_preserving_control_plane/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/status_preserving_control_plane/control_plane_board.json",
        lattice_ref,
        "microcosms/status_preserving_control_plane/README.md",
        str(STATUS_COLLAPSE_SUITE_PATH),
        "registry/release_candidates.json",
        "registry/validators.json",
        "state/release_candidate_portfolio.json",
        "release/publication_gate.json",
        "src/idea_microcosm/status_preserving_control_plane_specimen.py",
        "src/idea_microcosm/validators.py",
        "skills/cold_start_agent.md",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/status_preserving_control_plane/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/status_preserving_control_plane/receipt.json", "missing_evidence_ref": ref})

    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-status-preserving-control-plane-specimen --root . --write-receipt",
        "not the private control plane",
        "fail-closed",
        "claim-inference authority lattice",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/status_preserving_control_plane/README.md", "missing_text": required_text})
    return failures


def _correction_survival_loop_specimen_failures(root: Path) -> list[dict[str, Any]]:
    """Re-validate the correction-survival-loop board and receipt on disk.

    Asserts the seven internal validators reported pass, the receipt has the
    receipt_v0 shape with claim_tier fixture_validated, evidence_refs resolve,
    fixture hashes are non-empty, fail-closed statuses are declared, and the
    README cites the runnable build command. Catches post-build tampering, not
    author-time logic bugs in the specimen.
    """
    failures: list[dict[str, Any]] = []
    board_rel = "microcosms/correction_survival_loop/correction_survival_board.json"
    receipt_rel = "microcosms/correction_survival_loop/receipt.json"
    readme_rel = "microcosms/correction_survival_loop/README.md"
    board_path = root / board_rel
    receipt_path = root / receipt_rel
    readme_path = root / readme_rel

    for rel, path in ((board_rel, board_path), (receipt_rel, receipt_path), (readme_rel, readme_path)):
        if not path.exists():
            failures.append({"path": rel, "reason": "missing"})

    expected_validators = {
        "validator.capture_before_prose",
        "validator.failure_mode_classified",
        "validator.durable_patch_nonempty",
        "validator.patch_references_capture",
        "validator.future_route_changed",
        "validator.old_behavior_fails_new_behavior_passes",
        "validator.private_content_absent",
    }

    if board_path.exists():
        try:
            board = json.loads(board_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append({"path": board_rel, "reason": "invalid JSON", "detail": str(exc)})
            board = {}
        if board.get("schema_version") != "correction_survival_loop_board_v0":
            failures.append({"path": board_rel, "reason": "unexpected schema_version"})
        if board.get("status") != "ok":
            failures.append({"path": board_rel, "reason": "board status must be ok"})
        if board.get("public_safety_status") != "public_candidate_fail_closed":
            failures.append({"path": board_rel, "reason": "board must declare public_candidate_fail_closed"})
        if board.get("hosted_public_status") != "fail_closed_not_hosted_public":
            failures.append({"path": board_rel, "reason": "board hosted_public_status must stay fail_closed"})
        if board.get("publication_status") != "fail_closed_not_publication_authority":
            failures.append({"path": board_rel, "reason": "board publication_status must stay fail_closed"})
        if board.get("private_root_equivalence_status") != "fail_closed_not_private_root_equivalence":
            failures.append({"path": board_rel, "reason": "board private_root_equivalence_status must stay fail_closed"})
        validator_summary = board.get("validators") or []
        observed_ids = {entry.get("validator_id") for entry in validator_summary if isinstance(entry, dict)}
        missing_validators = sorted(expected_validators - observed_ids)
        if missing_validators:
            failures.append({"path": board_rel, "missing_validators": missing_validators})
        for entry in validator_summary:
            if isinstance(entry, dict) and entry.get("status") != "pass":
                failures.append({"path": board_rel, "validator_id": entry.get("validator_id"), "reason": "validator must report pass"})
        effectiveness = board.get("effectiveness_witnesses") or []
        if not effectiveness:
            failures.append({"path": board_rel, "reason": "effectiveness_witnesses must be non-empty"})
        for row in effectiveness:
            if not isinstance(row, dict) or not row.get("effectiveness_witnessed"):
                failures.append({"path": board_rel, "scenario_id": row.get("scenario_id") if isinstance(row, dict) else None, "reason": "effectiveness witness must be true"})
        if not board.get("anti_claims"):
            failures.append({"path": board_rel, "reason": "anti_claims must be non-empty"})

    if receipt_path.exists():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append({"path": receipt_rel, "reason": "invalid JSON", "detail": str(exc)})
            receipt = {}
        if receipt.get("schema_version") != "receipt_v0":
            failures.append({"path": receipt_rel, "reason": "receipt schema_version must be receipt_v0"})
        if receipt.get("status") != "ok":
            failures.append({"path": receipt_rel, "reason": "receipt status must be ok"})
        if receipt.get("claim_tier") != "fixture_validated":
            failures.append({"path": receipt_rel, "reason": "receipt claim_tier must be fixture_validated"})
        if receipt.get("public_safety_status") != "public_candidate_fail_closed":
            failures.append({"path": receipt_rel, "reason": "receipt must declare public_candidate_fail_closed"})
        if receipt.get("hosted_public_status") != "fail_closed_not_hosted_public":
            failures.append({"path": receipt_rel, "reason": "receipt hosted_public_status must stay fail_closed"})
        if receipt.get("publication_status") != "fail_closed_not_publication_authority":
            failures.append({"path": receipt_rel, "reason": "receipt publication_status must stay fail_closed"})
        for ref in receipt.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"path": receipt_rel, "missing_evidence_ref": ref})
        if not receipt.get("omissions"):
            failures.append({"path": receipt_rel, "reason": "receipt omissions must be non-empty"})
        if not receipt.get("fixture_hashes"):
            failures.append({"path": receipt_rel, "reason": "receipt fixture_hashes must be non-empty"})

    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        for required_text in (
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-correction-survival-loop-specimen --root . --write-receipt",
            "effectiveness witness",
            "fail-closed",
            "synthetic",
        ):
            if required_text not in readme:
                failures.append({"path": readme_rel, "missing_text": required_text})
    return failures


def _self_comprehension_navigator_specimen_failures(root: Path) -> list[dict[str, Any]]:
    """Re-validate the self-comprehension-navigator board and receipt on disk.

    Asserts the seven internal validators reported pass, the receipt has the
    receipt_v0 shape with claim_tier fixture_validated, evidence_refs resolve,
    fixture hashes are non-empty, fail-closed statuses are declared, and the
    README cites the runnable build command.
    """
    failures: list[dict[str, Any]] = []
    board_rel = "microcosms/self_comprehension_navigator/navigator_board.json"
    receipt_rel = "microcosms/self_comprehension_navigator/receipt.json"
    readme_rel = "microcosms/self_comprehension_navigator/README.md"
    board_path = root / board_rel
    receipt_path = root / receipt_rel
    readme_path = root / readme_rel

    for rel, path in ((board_rel, board_path), (receipt_rel, receipt_path), (readme_rel, readme_path)):
        if not path.exists():
            failures.append({"path": rel, "reason": "missing"})

    expected_validators = {
        "validator.entry_packet_binds_kind_and_id",
        "validator.banded_drilldown_order",
        "validator.banned_route_fail_closed",
        "validator.stale_projection_refuses_to_serve",
        "validator.cold_start_routes_to_correct_kind",
        "validator.banned_vs_correct_effectiveness_witness",
        "validator.private_content_absent",
        "validator.packet_compiler_macro_source_capsule_bridge",
        "validator.self_comprehension_live_code_navigation_bridge",
    }

    if board_path.exists():
        try:
            board = json.loads(board_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append({"path": board_rel, "reason": "invalid JSON", "detail": str(exc)})
            board = {}
        if board.get("schema_version") != "self_comprehension_navigator_board_v0":
            failures.append({"path": board_rel, "reason": "unexpected schema_version"})
        if board.get("status") != "ok":
            failures.append({"path": board_rel, "reason": "board status must be ok"})
        if board.get("public_safety_status") != "public_candidate_fail_closed":
            failures.append({"path": board_rel, "reason": "board must declare public_candidate_fail_closed"})
        if board.get("hosted_public_status") != "fail_closed_not_hosted_public":
            failures.append({"path": board_rel, "reason": "board hosted_public_status must stay fail_closed"})
        if board.get("publication_status") != "fail_closed_not_publication_authority":
            failures.append({"path": board_rel, "reason": "board publication_status must stay fail_closed"})
        if board.get("private_root_equivalence_status") != "fail_closed_not_private_root_equivalence":
            failures.append({"path": board_rel, "reason": "board private_root_equivalence_status must stay fail_closed"})
        validator_summary = board.get("validators") or []
        observed_ids = {entry.get("validator_id") for entry in validator_summary if isinstance(entry, dict)}
        missing_validators = sorted(expected_validators - observed_ids)
        if missing_validators:
            failures.append({"path": board_rel, "missing_validators": missing_validators})
        for entry in validator_summary:
            if isinstance(entry, dict) and entry.get("status") != "pass":
                failures.append({"path": board_rel, "validator_id": entry.get("validator_id"), "reason": "validator must report pass"})
        effectiveness = board.get("effectiveness_witnesses") or []
        if not effectiveness:
            failures.append({"path": board_rel, "reason": "effectiveness_witnesses must be non-empty"})
        for row in effectiveness:
            if not isinstance(row, dict) or not row.get("effectiveness_witnessed"):
                failures.append({"path": board_rel, "pair_id": row.get("pair_id") if isinstance(row, dict) else None, "reason": "effectiveness witness must be true"})
        banned_results = board.get("banned_route_results") or []
        if not banned_results or not all(isinstance(r, dict) and r.get("fail_closed") for r in banned_results):
            failures.append({"path": board_rel, "reason": "banned_route_results must all fail_closed"})
        stale_results = board.get("stale_projection_results") or []
        if not stale_results or not all(isinstance(r, dict) and r.get("fail_closed") for r in stale_results):
            failures.append({"path": board_rel, "reason": "stale_projection_results must all fail_closed"})
        if not board.get("anti_claims"):
            failures.append({"path": board_rel, "reason": "anti_claims must be non-empty"})
        live_bridge = board.get("live_code_navigation_bridge") or {}
        if live_bridge.get("schema_version") != "self_comprehension_live_code_navigation_bridge_v0":
            failures.append({"path": board_rel, "reason": "live_code_navigation_bridge missing schema"})
        if live_bridge.get("status") != "available":
            failures.append({"path": board_rel, "reason": "live_code_navigation_bridge must be available"})
        if live_bridge.get("code_card_count", 0) <= 0:
            failures.append({"path": board_rel, "reason": "live_code_navigation_bridge must expose code cards"})
        if live_bridge.get("source_span_count", 0) <= 0:
            failures.append({"path": board_rel, "reason": "live_code_navigation_bridge must expose source spans"})
        commands = live_bridge.get("query_commands") or {}
        if "query-leaf-code-routes" not in str(commands.get("leaf_code_card", "")):
            failures.append({"path": board_rel, "reason": "live bridge missing leaf-code card query"})
        if "query-std-python" not in str(commands.get("std_python_card", "")):
            failures.append({"path": board_rel, "reason": "live bridge missing std_python card query"})
        if "query-leaf-code-routes" not in str(commands.get("source_span", "")):
            failures.append({"path": board_rel, "reason": "live bridge missing source-span query"})
        if not any("self_comprehension_navigator_specimen.py" in str(ref) for ref in live_bridge.get("source_span_refs", [])):
            failures.append({"path": board_rel, "reason": "live bridge source spans must target self_comprehension_navigator_specimen.py"})
        packet_extension = board.get("packet_compiler_extension") or {}
        macro_bridge = packet_extension.get("macro_source_capsule_bridge") or {}
        if macro_bridge.get("schema_version") != "self_comprehension_packet_compiler_macro_source_bridge_v0":
            failures.append({"path": board_rel, "reason": "macro_source_capsule_bridge missing schema"})
        if macro_bridge.get("status") != "verified":
            failures.append({"path": board_rel, "reason": "macro_source_capsule_bridge must be verified"})
        if macro_bridge.get("verified_source_capsule_count", 0) < 3:
            failures.append({"path": board_rel, "reason": "macro_source_capsule_bridge must verify three source capsules"})
        for ref_key in ("source_module_manifest_ref", "projection_protocol_ref"):
            ref = macro_bridge.get(ref_key)
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"path": board_rel, "missing_macro_source_ref": ref})
        expected_module_ids = {
            "profile_loader_source_body_import",
            "profile_registry_source_body_import",
            "profile_loader_test_source_body_import",
        }
        source_capsules = macro_bridge.get("source_capsules") or []
        observed_module_ids = {
            capsule.get("module_id") for capsule in source_capsules if isinstance(capsule, dict)
        }
        if expected_module_ids - observed_module_ids:
            failures.append({"path": board_rel, "missing_macro_source_modules": sorted(expected_module_ids - observed_module_ids)})
        for capsule in source_capsules:
            if not isinstance(capsule, dict):
                continue
            if capsule.get("status") != "verified":
                failures.append({"path": board_rel, "module_id": capsule.get("module_id"), "reason": "source capsule must be verified"})
            target_ref = capsule.get("public_target_ref")
            if isinstance(target_ref, str) and target_ref and not _path_ref_exists(root, target_ref):
                failures.append({"path": board_rel, "missing_macro_source_target": target_ref})
            if capsule.get("body_in_receipt") is not False:
                failures.append({"path": board_rel, "module_id": capsule.get("module_id"), "reason": "source capsule body must stay out of receipt"})
        authority_ceiling = macro_bridge.get("authority_ceiling") or {}
        if authority_ceiling and any(value is not False for value in authority_ceiling.values()):
            failures.append({"path": board_rel, "reason": "macro source bridge authority_ceiling values must stay false"})

    if receipt_path.exists():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append({"path": receipt_rel, "reason": "invalid JSON", "detail": str(exc)})
            receipt = {}
        if receipt.get("schema_version") != "receipt_v0":
            failures.append({"path": receipt_rel, "reason": "receipt schema_version must be receipt_v0"})
        if receipt.get("status") != "ok":
            failures.append({"path": receipt_rel, "reason": "receipt status must be ok"})
        if receipt.get("claim_tier") != "fixture_validated":
            failures.append({"path": receipt_rel, "reason": "receipt claim_tier must be fixture_validated"})
        if receipt.get("public_safety_status") != "public_candidate_fail_closed":
            failures.append({"path": receipt_rel, "reason": "receipt must declare public_candidate_fail_closed"})
        if receipt.get("hosted_public_status") != "fail_closed_not_hosted_public":
            failures.append({"path": receipt_rel, "reason": "receipt hosted_public_status must stay fail_closed"})
        if receipt.get("publication_status") != "fail_closed_not_publication_authority":
            failures.append({"path": receipt_rel, "reason": "receipt publication_status must stay fail_closed"})
        for ref in receipt.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"path": receipt_rel, "missing_evidence_ref": ref})
        if not receipt.get("omissions"):
            failures.append({"path": receipt_rel, "reason": "receipt omissions must be non-empty"})
        if not receipt.get("fixture_hashes"):
            failures.append({"path": receipt_rel, "reason": "receipt fixture_hashes must be non-empty"})

    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        for required_text in (
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-self-comprehension-navigator-specimen --root . --write-receipt",
            "effectiveness witness",
            "fail-closed",
            "synthetic",
            "banned route",
        ):
            if required_text not in readme:
                failures.append({"path": readme_rel, "missing_text": required_text})
    return failures


def _path_ref_exists(root: Path, ref: str) -> bool:
    if not ref or ":" in ref:
        return True
    if ref.endswith("/"):
        return (root / ref).is_dir()
    if "*" in ref:
        return bool(list(root.glob(ref)))
    return (root / ref).exists()


def _receipt_paths(root: Path) -> set[str]:
    paths = {str(path.relative_to(root)) for path in (root / "receipts").glob("*.json")}
    microcosm_root = root / "microcosms"
    if microcosm_root.exists():
        paths.update(str(path.relative_to(root)) for path in microcosm_root.glob("*/receipt.json"))
    return paths


def _task_ledger_specimen_failures(root: Path) -> list[dict[str, Any]]:
    projection_path = root / "microcosms" / "task_ledger_cap_economy" / "projection.json"
    receipt_path = root / "microcosms" / "task_ledger_cap_economy" / "receipt.json"
    provider_residual_bridge_path = root / "microcosms" / "task_ledger_cap_economy" / "provider_repair_residual_bridge.json"
    failures: list[dict[str, Any]] = []
    if not projection_path.exists():
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "missing specimen projection"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/task_ledger_cap_economy/receipt.json", "reason": "missing specimen receipt"})
    if not provider_residual_bridge_path.exists():
        failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "reason": "missing provider repair residual bridge"})
    if failures:
        return failures

    projection = load_json(projection_path)
    receipt = load_json(receipt_path)
    provider_residual_bridge = load_json(provider_residual_bridge_path)
    if projection.get("schema_version") != "task_ledger_cap_economy_projection_v1":
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "unexpected schema_version"})
    if projection.get("status") != "ok":
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "status": projection.get("status")})
    if projection.get("authority_posture") != "public_safe_synthetic_fixture_not_private_task_ledger_authority":
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "unexpected authority_posture"})
    if not projection.get("generated_by", {}).get("projection_not_authority"):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "generated projection must declare projection_not_authority"})
    if projection.get("failure_routing_status") != "all_failures_have_work_items":
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "validation failures and side findings must route to work_item events"})
    if projection.get("prose_only_finding_count") != 0:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "prose-only findings are not allowed"})
    if int(projection.get("validation_failure_count", 0)) < 1:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "fixture must include a validation failure"})
    if int(projection.get("work_item_count", 0)) < int(projection.get("validation_failure_count", 0)):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "validation failures must have durable work items"})
    provenance = projection.get("source_capsule_provenance", {})
    source_capsules = provenance.get("source_capsules", [])
    if not source_capsules or len(source_capsules) != int(projection.get("event_count", 0)):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "every fixture event must emit a source capsule"})
    for capsule in source_capsules:
        source_clip = capsule.get("source_clip")
        source_clip_hash = capsule.get("source_clip_hash")
        if not isinstance(source_clip, str) or hashlib.sha256(source_clip.encode("utf-8")).hexdigest() != source_clip_hash:
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "capsule_id": capsule.get("capsule_id"), "reason": "source capsule hash mismatch"})
    mechanism = projection.get("mechanism", {})
    mechanism_cases = mechanism.get("cases", [])
    if not mechanism_cases:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "mechanism cases missing"})
    for case in mechanism_cases:
        if not case.get("source_clip") or not case.get("source_clip_hash"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "mechanism case missing source clip"})
        if not case.get("evidence_refs"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "mechanism case missing evidence refs"})
        if not case.get("anti_claims"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "mechanism case missing anti-claims"})
    if not mechanism.get("transaction_trace"):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "transaction trace missing"})
    if len(mechanism.get("repair_routes", [])) < int(projection.get("validation_failure_count", 0)):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "validation failures must have repair routes"})
    if projection.get("provider_repair_residual_bridge_ref") != "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json":
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "provider repair residual bridge ref missing"})
    if not mechanism.get("provider_repair_residual_cases"):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "provider repair residual cases missing"})
    bridge_summary = projection.get("provider_repair_residual_bridge_summary", {})
    if int(bridge_summary.get("case_count", 0)) < 4:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "provider repair residual bridge must cover provider cases"})
    if int(bridge_summary.get("open_residual_count", 0)) < 3:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "failed provider cases must become open residuals"})
    self_error_extension = projection.get("self_error_capture_repair_extension", {})
    if self_error_extension.get("schema_version") != "self_error_capture_repair_extension_v0":
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "self-error capture extension missing or has unexpected schema"})
    if self_error_extension.get("status") != "ok":
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "self-error capture extension must pass"})
    self_error_summary = self_error_extension.get("summary", {})
    self_error_cases = self_error_extension.get("cases", [])
    if len(self_error_cases) < 5:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "self-error capture extension needs at least five cases"})
    if int(self_error_summary.get("capture_before_prose_required_count", 0)) != len(self_error_cases):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "every self-error case must require capture-before-prose"})
    if int(self_error_summary.get("blocked_until_capture_count", 0)) < 1:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "self-error extension must include blocked uncaptured prose attempt"})
    if int(self_error_summary.get("typed_nothing_to_refine_count", 0)) < 1:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "self-error extension must include typed nothing_to_refine disposition"})
    if int(self_error_summary.get("publication_permission_count", 1)) != 0:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "self-error capture must grant no publication permission"})
    for case in self_error_cases:
        source_clip = case.get("source_clip")
        source_clip_hash = case.get("source_clip_hash")
        if not isinstance(source_clip, str) or hashlib.sha256(source_clip.encode("utf-8")).hexdigest() != source_clip_hash:
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "self-error case source hash mismatch"})
        if case.get("capture_before_prose_required") is not True:
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "self-error case must require capture-before-prose"})
        if case.get("prose_authority_granted") is not False:
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "self-error prose must not become authority"})
        if case.get("publication_permission") or case.get("public_release_permission") or case.get("private_task_ledger_export"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "self-error capture overclaims authority"})
        if case.get("repair_status") == "blocked":
            if case.get("allowed_to_appear_in_prose"):
                failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "blocked uncaptured case cannot appear in prose"})
        elif not case.get("capture_ref"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "prose-eligible self-error case needs capture_ref"})
        if not case.get("rebuild_or_visibility_command") or not case.get("disposition") or not case.get("teaching_rule"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "case_id": case.get("case_id"), "reason": "self-error case missing rebuild command, disposition, or teaching rule"})
    authority = projection.get("authority", {})
    if authority.get("self_attestation_count") != 0:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "self-attestation must not be authority"})
    if int(authority.get("evaluator_authority_count", 0)) < 1:
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "evaluator authority count missing"})
    if not projection.get("route", {}).get("first_command"):
        failures.append({"path": "microcosms/task_ledger_cap_economy/projection.json", "reason": "runnable route command missing"})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/task_ledger_cap_economy/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/task_ledger_cap_economy/events.jsonl",
        "microcosms/task_ledger_cap_economy/projection.json",
        "microcosms/concurrency_mission_control/provider_repair_bridge.json",
        "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json",
        "microcosms/task_ledger_cap_economy/README.md",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/task_ledger_cap_economy/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/task_ledger_cap_economy/receipt.json", "missing_evidence_ref": ref})
    if receipt.get("self_error_capture_repair_extension_path") != "microcosms/task_ledger_cap_economy/projection.json:self_error_capture_repair_extension":
        failures.append({"path": "microcosms/task_ledger_cap_economy/receipt.json", "reason": "self-error capture extension path missing"})
    if len(receipt.get("self_error_capture_repair_validator_summary", [])) < 4:
        failures.append({"path": "microcosms/task_ledger_cap_economy/receipt.json", "reason": "self-error capture validator summary missing"})
    if int((receipt.get("summary") or {}).get("self_error_capture_publication_permission_count", 1)) != 0:
        failures.append({"path": "microcosms/task_ledger_cap_economy/receipt.json", "reason": "self-error capture receipt must grant no publication permission"})

    if provider_residual_bridge.get("schema_version") != "task_ledger_provider_repair_residual_bridge_v0":
        failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "reason": "unexpected provider bridge schema_version"})
    if not provider_residual_bridge.get("generated_by", {}).get("projection_not_authority"):
        failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "reason": "provider bridge must declare projection_not_authority"})
    provider_authority = provider_residual_bridge.get("authority", {})
    if provider_authority.get("self_attestation_count") != 0:
        failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "reason": "provider residual self-attestation must not be authority"})
    provider_cases = provider_residual_bridge.get("mechanism", {}).get("cases", [])
    if len(provider_cases) < 4:
        failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "reason": "provider residual bridge must include provider cases"})
    provider_open_residual_count = 0
    for case in provider_cases:
        source_clip = case.get("source_clip")
        source_clip_hash = case.get("source_clip_hash")
        if not isinstance(source_clip, str) or hashlib.sha256(source_clip.encode("utf-8")).hexdigest() != source_clip_hash:
            failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "case_id": case.get("case_id"), "reason": "provider residual source hash mismatch"})
        if not case.get("evidence_refs") or not case.get("anti_claims"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "case_id": case.get("case_id"), "reason": "provider residual case missing evidence or anti-claims"})
        if not case.get("restart_point") or not case.get("teaching_rule"):
            failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "case_id": case.get("case_id"), "reason": "provider residual case missing restart point or teaching rule"})
        if case.get("semantic_carryforward", {}).get("repair_required"):
            provider_open_residual_count += 1
            if case.get("repair_route", {}).get("status") != "residual_work_item_open":
                failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "case_id": case.get("case_id"), "reason": "repair-required provider case must open residual work"})
    if provider_open_residual_count < 3:
        failures.append({"path": "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json", "reason": "expected provider failures to open residual work"})
    return failures


def _release_standards_axiom_gate_failures(root: Path) -> list[dict[str, Any]]:
    gate_path = root / "microcosms" / "release_standards_axiom_gate" / "gate.json"
    receipt_path = root / "microcosms" / "release_standards_axiom_gate" / "receipt.json"
    readme_path = root / "microcosms" / "release_standards_axiom_gate" / "README.md"
    failures: list[dict[str, Any]] = []
    if not gate_path.exists():
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "missing specimen gate"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/release_standards_axiom_gate/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/release_standards_axiom_gate/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    gate = load_json(gate_path)
    receipt = load_json(receipt_path)
    if gate.get("status") != "ok":
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "status": gate.get("status")})
    if gate.get("candidate_id") != "release_standards_axiom_gate_microcosm":
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "unexpected candidate_id"})
    if gate.get("authority_posture") != "public_safe_fixture_gate_not_publication_claim":
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "unexpected authority posture"})
    if gate.get("microcosm_primitive") != ["discover", "project", "improve", "gate", "prove", "publish_later"]:
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "microcosm primitive mismatch"})
    candidate_gate = gate.get("candidate_record_gate", {})
    required_fields = set(candidate_gate.get("required_fields", [])) if isinstance(candidate_gate, dict) else set()
    missing_required_fields = sorted(RELEASE_CANDIDATE_REQUIRED_FIELDS - required_fields)
    if missing_required_fields:
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "missing_required_fields": missing_required_fields})
    forbidden_phrases = set(candidate_gate.get("forbidden_mechanismless_phrases", [])) if isinstance(candidate_gate, dict) else set()
    if not {"genius", "cool idea"} <= forbidden_phrases:
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "gate must reject vague praise phrases"})
    if "public-release-ready" in json.dumps(gate).lower():
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "gate must not imply public release readiness"})
    axiom_gate = gate.get("axiom_gate", {})
    if axiom_gate.get("principle_enforcement_status") != "enforced":
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "principle enforcement status must be enforced"})
    if axiom_gate.get("teleology_status") != "operationalized":
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "teleology status must be operationalized"})
    if axiom_gate.get("axiom_kernel_status") != "compiled":
        failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "reason": "axiom kernel status must be compiled"})
    for ref in gate.get("source_refs", []):
        if isinstance(ref, str) and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/release_standards_axiom_gate/gate.json", "missing_source_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/release_standards_axiom_gate/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/release_standards_axiom_gate/gate.json",
        "microcosms/release_standards_axiom_gate/README.md",
        "registry/release_candidates.json",
        "state/principle_enforcement_matrix.json",
        "state/teleology_map.json",
        "state/axiom_kernel.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/release_standards_axiom_gate/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/release_standards_axiom_gate/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-standards-gate-specimen --root . --write-receipt",
        "not a publication claim",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/release_standards_axiom_gate/README.md", "missing_text": required_text})
    return failures


def _atlas_navigation_bands_failures(root: Path) -> list[dict[str, Any]]:
    bands_path = root / "microcosms" / "atlas_navigation_bands" / "navigation_bands.json"
    receipt_path = root / "microcosms" / "atlas_navigation_bands" / "receipt.json"
    readme_path = root / "microcosms" / "atlas_navigation_bands" / "README.md"
    index_path = root / "navigation" / "microcosm_index.json"
    entry_packet_path = root / "navigation" / "entry_packet.json"
    failures: list[dict[str, Any]] = []
    if not bands_path.exists():
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "missing navigation bands projection"})
    if not index_path.exists():
        failures.append({"path": "navigation/microcosm_index.json", "reason": "missing release microcosm index"})
    if not entry_packet_path.exists():
        failures.append({"path": "navigation/entry_packet.json", "reason": "missing entry packet"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/atlas_navigation_bands/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/atlas_navigation_bands/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    bands = load_json(bands_path)
    index = load_json(index_path)
    entry_packet = load_json(entry_packet_path)
    receipt = load_json(receipt_path)
    if bands.get("status") != "ok":
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "status": bands.get("status")})
    if bands.get("candidate_id") != "atlas_navigation_bands_microcosm":
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "unexpected candidate_id"})
    if bands.get("authority_posture") != "release_local_navigation_projection_not_private_system_atlas_authority":
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "unexpected authority posture"})
    expected_bands = list(ATLAS_NAVIGATION_EXPECTED_BANDS)
    expected_band_set = set(expected_bands)
    if bands.get("band_ids") != expected_bands:
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "band ids mismatch"})
    routes = bands.get("routes", [])
    if not isinstance(routes, list) or len(routes) < 5:
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "expected at least five candidate routes"})
    else:
        for route in routes:
            if not isinstance(route, dict):
                failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "route must be an object"})
                continue
            route_bands = route.get("bands")
            if not isinstance(route_bands, dict):
                failures.append({"candidate_id": route.get("candidate_id"), "reason": "route bands must be an object"})
            else:
                route_band_set = set(route_bands)
                if route_band_set != expected_band_set:
                    failures.append(
                        {
                            "candidate_id": route.get("candidate_id"),
                            "reason": "route must expose all four bands",
                            "missing_bands": sorted(expected_band_set - route_band_set),
                            "extra_bands": sorted(route_band_set - expected_band_set),
                        }
                    )
            if not route.get("candidate_id") or not route.get("title"):
                failures.append({"candidate_id": route.get("candidate_id"), "reason": "route missing identity"})
    next_route = bands.get("next_candidate_route")
    next_candidate_id = index.get("next_specimen_candidate_id")
    if next_candidate_id:
        if not isinstance(next_route, dict) or next_route.get("candidate_id") != next_candidate_id:
            failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "next candidate route must match release microcosm index"})
    elif bands.get("all_candidate_specimens_landed") is not True or index.get("all_candidate_specimens_landed") is not True:
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "next candidate route must match release microcosm index"})
    if index.get("authority_posture") != "release_local_navigation_projection_not_private_system_atlas_authority":
        failures.append({"path": "navigation/microcosm_index.json", "reason": "unexpected authority posture"})
    if index.get("band_ids") != expected_bands:
        failures.append({"path": "navigation/microcosm_index.json", "reason": "index band ids mismatch"})
    if "public-release-ready" in json.dumps(bands).lower() or "public-release-ready" in json.dumps(index).lower():
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "navigation specimen must not imply public release readiness"})

    def diagnostic_bridge_failures(surface_path: str, payload: dict[str, Any]) -> None:
        bridge = payload.get("diagnostic_route_bridge")
        if not isinstance(bridge, dict):
            failures.append({"path": surface_path, "reason": "diagnostic_route_bridge must be an object"})
            return
        if bridge.get("schema_version") != "microcosm_diagnostic_route_bridge_v0":
            failures.append({"path": surface_path, "reason": "diagnostic_route_bridge schema mismatch"})
        if bridge.get("primary_leaf") != "meta_diagnostics_workbench":
            failures.append({"path": surface_path, "reason": "diagnostic_route_bridge primary leaf mismatch"})
        if "query-command-latency-inventory" not in str(bridge.get("query_command", "")):
            failures.append({"path": surface_path, "reason": "diagnostic bridge missing command latency inventory query"})
        if "--slow-only" not in str(bridge.get("query_command", "")):
            failures.append({"path": surface_path, "reason": "diagnostic bridge query must expose slow-only lane"})
        if "query-leaf-code-routes" not in str(bridge.get("code_card_command", "")):
            failures.append({"path": surface_path, "reason": "diagnostic bridge missing leaf-code card command"})
        if "source_span" not in str(bridge.get("source_span_command", "")):
            failures.append({"path": surface_path, "reason": "diagnostic bridge missing source-span command"})
        boundary = str(bridge.get("boundary", "")).lower()
        for required_text in ("not live telemetry", "performance certification", "hosted ci", "publication permission"):
            if required_text not in boundary:
                failures.append({"path": surface_path, "reason": "diagnostic bridge boundary missing required anti-upgrade text", "missing_text": required_text})
        route_order = bridge.get("route_order") or []
        if "source span only after one diagnostic row is selected" not in route_order:
            failures.append({"path": surface_path, "reason": "diagnostic bridge must keep source span after diagnostic row selection"})
        anti_claims = " ".join(str(row) for row in bridge.get("anti_claims") or [])
        for required_text in ("live private telemetry", "certify runtime performance", "publication readiness"):
            if required_text not in anti_claims:
                failures.append({"path": surface_path, "reason": "diagnostic bridge anti-claims missing boundary", "missing_text": required_text})
        for ref in bridge.get("source_refs") or []:
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"path": surface_path, "missing_diagnostic_bridge_source_ref": ref})

    diagnostic_bridge_failures("microcosms/atlas_navigation_bands/navigation_bands.json", bands)
    diagnostic_bridge_failures("navigation/microcosm_index.json", index)
    diagnostic_bridge_failures("navigation/entry_packet.json", entry_packet)

    entry_rows = {
        str(row.get("mode_id")): row
        for row in ((entry_packet.get("root_entry_route_map") or {}).get("rows") or [])
        if isinstance(row, dict) and row.get("mode_id")
    }
    concurrent_commands = entry_rows.get("concurrent_editor", {}).get("next_commands") or []
    if not any("query-command-latency-inventory" in str(command) for command in concurrent_commands):
        failures.append({"path": "navigation/entry_packet.json", "reason": "concurrent_editor must route through command latency inventory before duplicate validation"})

    witnesses = bands.get("effectiveness_witnesses")
    if not isinstance(witnesses, list) or not witnesses:
        failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "missing atlas navigation effectiveness witness"})
    else:
        witness = witnesses[0]
        if not isinstance(witness, dict):
            failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "effectiveness witness must be an object"})
        else:
            validator = witness.get("validator") or {}
            without_bands = witness.get("without_bands") or {}
            with_bands = witness.get("with_bands") or {}
            loss_boundary = witness.get("accepted_loss_boundary") or {}
            if validator.get("validator_id") != "validator.atlas_navigation_bands_effectiveness_witness" or validator.get("status") != "pass":
                failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "effectiveness witness validator must pass"})
            if without_bands.get("motif_present") is not False or not str(without_bands.get("outcome", "")).startswith("fail"):
                failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "without_bands side must fail with motif absent"})
            if with_bands.get("motif_present") is not True or with_bands.get("selected_band") != "evidence" or not str(with_bands.get("outcome", "")).startswith("pass"):
                failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "with_bands side must pass through evidence band"})
            if without_bands.get("route_or_behavior") == with_bands.get("route_or_behavior"):
                failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "effectiveness witness must change route or behavior"})
            if not with_bands.get("receipt_refs"):
                failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "with_bands side must land on receipt refs"})
            allowed_loss = set(loss_boundary.get("allowed_loss") or [])
            forbidden_loss = set(loss_boundary.get("forbidden_loss") or [])
            required_forbidden = {"band identity", "receipt boundary", "candidate id"}
            if not allowed_loss or not required_forbidden.issubset(forbidden_loss):
                failures.append({"path": "microcosms/atlas_navigation_bands/navigation_bands.json", "reason": "effectiveness witness must declare allowed and forbidden loss"})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/atlas_navigation_bands/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    if int(receipt.get("effectiveness_witness_count") or 0) < 1:
        failures.append({"path": "microcosms/atlas_navigation_bands/receipt.json", "reason": "receipt must report atlas navigation effectiveness witness"})
    validator_summary = {
        str(row.get("validator_id")): row.get("status")
        for row in receipt.get("validator_summary") or []
        if isinstance(row, dict) and row.get("validator_id")
    }
    if validator_summary.get("validator.atlas_navigation_bands_effectiveness_witness") != "pass":
        failures.append({"path": "microcosms/atlas_navigation_bands/receipt.json", "reason": "receipt must pass atlas navigation effectiveness validator"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/atlas_navigation_bands/navigation_bands.json",
        "navigation/microcosm_index.json",
        "microcosms/atlas_navigation_bands/README.md",
        "registry/release_candidates.json",
        "state/release_candidate_portfolio.json",
        "navigation/atlas.json",
        "navigation/entry_packet.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/atlas_navigation_bands/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/atlas_navigation_bands/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-atlas-navigation-bands-specimen --root . --write-receipt",
        "not the private System Atlas",
        "effectiveness witness",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/atlas_navigation_bands/README.md", "missing_text": required_text})
    return failures


def _lab_evolve_failure_replay_failures(root: Path) -> list[dict[str, Any]]:
    graph_path = root / "microcosms" / "lab_evolve_failure_replay" / "replay_graph.json"
    receipt_path = root / "microcosms" / "lab_evolve_failure_replay" / "receipt.json"
    readme_path = root / "microcosms" / "lab_evolve_failure_replay" / "README.md"
    failures: list[dict[str, Any]] = []
    if not graph_path.exists():
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "missing replay graph"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/lab_evolve_failure_replay/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/lab_evolve_failure_replay/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    graph = load_json(graph_path)
    receipt = load_json(receipt_path)
    if graph.get("status") != "ok":
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "status": graph.get("status")})
    if graph.get("candidate_id") != "lab_evolve_failure_replay_graph_microcosm":
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "unexpected candidate_id"})
    if graph.get("authority_posture") != "public_safe_synthetic_failure_replay_fixture_not_private_lab_or_benchmark_authority":
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "unexpected authority posture"})
    if "public-release-ready" in json.dumps(graph).lower():
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "specimen must not imply public release readiness"})

    summary = graph.get("summary", {})
    cases = graph.get("cases", [])
    if not isinstance(cases, list) or len(cases) < 2:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "expected at least two replay cases"})
        cases = []
    if summary.get("case_count") != len(cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "summary case_count mismatch"})
    if summary.get("baseline_failure_count") != len(cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "baseline failures must cover every case"})
    if summary.get("replay_success_count") != len(cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "replay success must cover every case"})
    if int(summary.get("global_pattern_candidate_count", 0)) < 1:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "expected a global pattern candidate"})
    if int(summary.get("candidate_global_rule_count", 0)) < 1:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "expected a candidate global rule from repeated local teachings"})

    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "case row must be an object"})
            continue
        case_id = case.get("case_id")
        if case.get("failure_origin_node") != "solve_operation":
            failures.append({"case_id": case_id, "reason": "failure must localize to solve_operation"})
        if case.get("restart_point") != "operation_ir":
            failures.append({"case_id": case_id, "reason": "restart point must be operation_ir"})
        if case.get("winner_variant") != "solver_sum_v2":
            failures.append({"case_id": case_id, "reason": "winner variant must be solver_sum_v2"})
        variants = case.get("variants_tried", [])
        if not isinstance(variants, list) or not {row.get("status") for row in variants if isinstance(row, dict)} >= {"fail", "pass"}:
            failures.append({"case_id": case_id, "reason": "variants must include both failed and passing replay attempts"})
        teaching = case.get("teaching", {})
        if not isinstance(teaching, dict) or not teaching.get("teaching_id") or not teaching.get("global_pattern_candidate_ref"):
            failures.append({"case_id": case_id, "reason": "case must record a teaching and global pattern ref"})

    teaching_ledger = graph.get("global_teaching_ledger", {})
    if not isinstance(teaching_ledger, dict):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "global_teaching_ledger must be an object"})
        teaching_ledger = {}
    local_teachings = teaching_ledger.get("local_teachings", [])
    if not isinstance(local_teachings, list) or len(local_teachings) != len(cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "global_teaching_ledger must include one local teaching per case"})
    global_rule_candidates = teaching_ledger.get("global_rule_candidates", [])
    if not isinstance(global_rule_candidates, list) or not global_rule_candidates:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "global_teaching_ledger must include global rule candidates"})
        global_rule_candidates = []
    candidate_rules = [
        row
        for row in global_rule_candidates
        if isinstance(row, dict) and row.get("status") == "candidate_global_rule_local_fixture_only"
    ]
    if not candidate_rules:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "expected a local-fixture-only candidate global rule"})
    for rule in candidate_rules:
        if rule.get("rule_id") != "rule.valid_ir_solver_variant_mismatch":
            failures.append({"rule_id": rule.get("rule_id"), "reason": "unexpected candidate rule id"})
        if int(rule.get("observed_case_count", 0)) < 2:
            failures.append({"rule_id": rule.get("rule_id"), "reason": "candidate rule must cite repeated cases"})
        action_order = rule.get("action_order", [])
        if "mutate_solver_variant" not in action_order or "reuse_passing_operation_ir" not in action_order:
            failures.append({"rule_id": rule.get("rule_id"), "reason": "candidate rule must preserve IR before mutating solver"})
        if not rule.get("evidence_refs"):
            failures.append({"rule_id": rule.get("rule_id"), "reason": "candidate rule must include evidence refs"})
        anti_claims = " ".join(str(value) for value in rule.get("anti_claims", []))
        if "benchmark performance evidence" not in anti_claims or "public release permission" not in anti_claims:
            failures.append({"rule_id": rule.get("rule_id"), "reason": "candidate rule must carry anti-claims"})

    grammar_bridge = graph.get("executable_grammar_replay_bridge", {})
    if not isinstance(grammar_bridge, dict):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "executable_grammar_replay_bridge must be an object"})
        grammar_bridge = {}
    if grammar_bridge.get("schema_version") != "executable_grammar_failure_replay_bridge_v0":
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "unexpected executable grammar bridge schema"})
    if grammar_bridge.get("status") != "ok":
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "executable grammar bridge must be ok"})
    generated_by = grammar_bridge.get("generated_by", {})
    if not isinstance(generated_by, dict) or generated_by.get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "executable grammar bridge must declare projection_not_authority"})
    bridge_cases = grammar_bridge.get("bridge_cases", [])
    if not isinstance(bridge_cases, list) or len(bridge_cases) < 3:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "expected at least three executable grammar replay bridge cases"})
        bridge_cases = []
    bridge_summary = grammar_bridge.get("summary", {})
    if not isinstance(bridge_summary, dict):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "executable grammar bridge summary must be an object"})
        bridge_summary = {}
    if summary.get("executable_grammar_replay_bridge_case_count") != len(bridge_cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge case count must be carried into graph summary"})
    if bridge_summary.get("case_count") != len(bridge_cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge summary case_count mismatch"})
    if bridge_summary.get("self_attestation_authority_count") != 0:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge self-attestation authority count must stay zero"})
    if bridge_summary.get("evaluator_authority_count") != len(bridge_cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge evaluator authority count must cover every case"})
    if bridge_summary.get("repair_route_count") != len(bridge_cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge repair route count must cover every case"})
    if bridge_summary.get("teaching_rule_count") != len(bridge_cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge teaching rule count must cover every case"})
    if bridge_summary.get("source_capsule_count") != len(bridge_cases):
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge source capsule count must cover every case"})
    bridge_authority = grammar_bridge.get("authority", {})
    if not isinstance(bridge_authority, dict) or bridge_authority.get("public_release_claim_count") != 0:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge authority must block public release claims"})
    for bridge_case in bridge_cases:
        if not isinstance(bridge_case, dict):
            failures.append({"path": "microcosms/lab_evolve_failure_replay/replay_graph.json", "reason": "bridge case must be an object"})
            continue
        bridge_case_id = bridge_case.get("bridge_case_id")
        if not bridge_case.get("source_clip"):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must carry source_clip"})
        if bridge_case.get("source_clip_hash") != _json_sha256(bridge_case.get("source_clip", {})):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge source_clip_hash mismatch"})
        if not bridge_case.get("restart_point"):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must carry restart_point"})
        if not bridge_case.get("repair_route"):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must carry repair_route"})
        if not bridge_case.get("teaching_rule"):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must carry teaching_rule"})
        evaluator_result = bridge_case.get("evaluator_result", {})
        if not isinstance(evaluator_result, dict) or evaluator_result.get("authority") != "grammar_evaluator_only":
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must preserve grammar evaluator authority"})
        if evaluator_result.get("provider_or_artifact_self_status_used_as_authority") is not False:
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must not use self status as authority"})
        carryforward = bridge_case.get("semantic_carryforward", {})
        if not isinstance(carryforward, dict) or carryforward.get("projection_not_authority") is not True:
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must carry projection_not_authority semantic carryforward"})
        anti_claims = " ".join(str(value) for value in bridge_case.get("anti_claims", []))
        if "public release approval" not in anti_claims or "private-root equivalence" not in anti_claims:
            failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must carry public/private anti-claims"})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/lab_evolve_failure_replay/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/lab_evolve_failure_replay/replay_graph.json",
        "microcosms/lab_evolve_failure_replay/README.md",
        "microcosms/executable_grammar_metabolism/grammar_board.json",
        "microcosms/executable_grammar_metabolism/receipt.json",
        "registry/release_candidates.json",
        "src/idea_microcosm/lab_evolve_failure_replay_specimen.py",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/lab_evolve_failure_replay/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/lab_evolve_failure_replay/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-lab-evolve-failure-replay-specimen --root . --write-receipt",
        "global_teaching_ledger.global_rule_candidates",
        "executable_grammar_replay_bridge",
        "not the private Lab/Evolve engine",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/lab_evolve_failure_replay/README.md", "missing_text": required_text})
    return failures


def _source_capsule_provenance_specimen_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "source_capsule_provenance" / "capsule_board.json"
    receipt_path = root / "microcosms" / "source_capsule_provenance" / "receipt.json"
    readme_path = root / "microcosms" / "source_capsule_provenance" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "missing source-capsule board"})
        return failures
    if not receipt_path.exists():
        failures.append({"path": "microcosms/source_capsule_provenance/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/source_capsule_provenance/README.md", "reason": "missing specimen README"})

    board = load_json(board_path)
    if board.get("schema_version") != "source_capsule_provenance_specimen_v0":
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "unexpected schema version"})
    if board.get("candidate_id") != "source_capsule_provenance_microcosm":
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "unexpected candidate_id"})
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "status": board.get("status")})
    generated_by = board.get("generated_by") or {}
    if generated_by.get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "generated_by must declare projection_not_authority"})
    cases = ((board.get("mechanism") or {}).get("cases") or [])
    summary = board.get("status_summary") or {}
    authority = board.get("authority") or {}
    if len(cases) < 5:
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "expected at least five source-capsule cases"})
    if summary.get("case_count") != len(cases):
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "case_count mismatch"})
    if summary.get("source_capsule_count") != len(cases):
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "source_capsule_count mismatch"})
    if summary.get("semantic_carryforward_count") != len(cases):
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "semantic_carryforward_count mismatch"})
    if summary.get("missing_ref_count") != 0:
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "source-capsule board has missing refs"})
    if summary.get("source_clip_hash_count") != len(cases):
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "every case must carry a source clip hash"})
    if summary.get("runnable_command_count") != 1:
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "expected one runnable command"})
    if authority.get("self_attestation_count") != 0:
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "self-attestation must not become capsule authority"})
    if authority.get("evaluator_authority_count") != len(cases):
        failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "evaluator authority must cover every case"})
    for field in (
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if authority.get(field) != 0:
            failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": f"authority {field} must remain zero"})

    required_case_fields = {
        "case_id",
        "input_or_trigger",
        "source_ref",
        "source_clip",
        "source_clip_hash",
        "semantic_carryforward",
        "transformation",
        "evaluator_or_validator",
        "outcome",
        "repair_route",
        "restart_point",
        "teaching_rule",
        "evidence_refs",
        "anti_claims",
        "authority_flags",
        "next_case",
    }
    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "reason": "case row must be an object"})
            continue
        for field in sorted(required_case_fields):
            if case.get(field) in ("", None, [], {}):
                failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "missing": field})
        source_clip = case.get("source_clip")
        if isinstance(source_clip, str):
            expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
            if case.get("source_clip_hash") != expected_hash:
                failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "reason": "source_clip_hash mismatch"})
        source_ref = str(case.get("source_ref") or "").split("::", 1)[0]
        if source_ref and not _path_ref_exists(root, source_ref):
            failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "missing_source_ref": source_ref})
        carry = case.get("semantic_carryforward") or {}
        if carry.get("projection_not_authority") is not True:
            failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "reason": "semantic carryforward must declare projection_not_authority"})
        if not case.get("route_consumers"):
            failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "reason": "case must name route consumers"})
        if not case.get("anti_claims"):
            failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "reason": "case must carry anti-claims"})
        flags = case.get("authority_flags") or {}
        for flag in (
            "self_attestation_used_as_authority",
            "projection_used_as_claim_authority",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if flags.get(flag) is not False:
                failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "authority_flag_not_false": flag})
        for evidence_ref in case.get("evidence_refs") or []:
            evidence_path = str(evidence_ref).split("::", 1)[0]
            if evidence_path and not _path_ref_exists(root, evidence_path):
                failures.append({"path": "microcosms/source_capsule_provenance/capsule_board.json", "case_id": case.get("case_id"), "missing_evidence_ref": evidence_path})

    if receipt_path.exists():
        receipt = load_json(receipt_path)
        if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
            failures.append({"path": "microcosms/source_capsule_provenance/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
        for ref in receipt.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref.split("::", 1)[0]):
                failures.append({"path": "microcosms/source_capsule_provenance/receipt.json", "missing_evidence_ref": ref})
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        for required_text in (
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-source-capsule-provenance-specimen --root . --write-receipt",
            "not public release approval",
            "source_clip_hash",
        ):
            if required_text not in readme:
                failures.append({"path": "microcosms/source_capsule_provenance/README.md", "missing_text": required_text})
    return failures


def _source_shuttle_specimen_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "source_shuttle" / "source_shuttle_board.json"
    receipt_path = root / "microcosms" / "source_shuttle" / "receipt.json"
    readme_path = root / "microcosms" / "source_shuttle" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "missing source-shuttle board"})
        return failures
    if not receipt_path.exists():
        failures.append({"path": "microcosms/source_shuttle/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/source_shuttle/README.md", "reason": "missing specimen README"})

    board = load_json(board_path)
    if board.get("schema_version") != "source_shuttle_specimen_v0":
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "unexpected schema version"})
    if board.get("candidate_id") != "source_shuttle_microcosm":
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "unexpected candidate_id"})
    generated_by = board.get("generated_by") or {}
    if generated_by.get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "generated_by must declare projection_not_authority"})

    cases = ((board.get("mechanism") or {}).get("cases") or [])
    effectiveness_witnesses = ((board.get("mechanism") or {}).get("effectiveness_witnesses") or [])
    effectiveness_summary = board.get("effectiveness_witness_summary") or {}
    status = board.get("status") or {}
    authority = board.get("authority") or {}
    if len(cases) < 5:
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "expected at least five shuttle cases"})
    for count_field in (
        "case_count",
        "source_capsule_count",
        "source_clip_hash_count",
        "semantic_carryforward_count",
        "semantic_packet_count",
        "semantic_packet_hash_count",
        "reentry_prompt_count",
        "loss_boundary_count",
        "no_private_copy_rule_count",
        "repair_route_count",
        "teaching_rule_count",
        "evaluator_authority_count",
    ):
        if status.get(count_field) != len(cases):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": f"{count_field} must equal case count"})
    if status.get("missing_ref_count") != 0:
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "source-shuttle board has missing refs"})
    if status.get("runnable_command_count") != 1:
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "expected one runnable command"})
    if status.get("pattern_route_count", 0) < 1:
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "expected at least one pattern route"})
    if status.get("effectiveness_witness_count") != len(effectiveness_witnesses) or status.get("effectiveness_total") != len(effectiveness_witnesses):
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "effectiveness witness counts must equal witness rows"})
    if status.get("effectiveness_validator_status") != "pass" or effectiveness_summary.get("status") != "pass":
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "effectiveness witness validator must pass"})
    if not effectiveness_witnesses:
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "expected at least one effectiveness witness"})
    if authority.get("self_attestation_count") != 0 or authority.get("self_attestation_authority_count") != 0:
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "self-attestation must not become shuttle authority"})
    if authority.get("evaluator_authority_count") != len(cases):
        failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "evaluator authority must cover every case"})
    for field in (
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if authority.get(field) != 0 or status.get(field) != 0:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": f"{field} must remain zero"})

    required_case_fields = {
        "case_id",
        "input_or_trigger",
        "source_ref",
        "source_clip",
        "source_clip_hash",
        "semantic_packet",
        "semantic_packet_hash",
        "semantic_carryforward",
        "transformation",
        "evaluator_or_validator",
        "outcome",
        "repair_route",
        "restart_point",
        "teaching_rule",
        "reentry_prompt",
        "loss_boundary",
        "no_private_copy_rule",
        "evidence_refs",
        "anti_claims",
    }
    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "case row must be an object"})
            continue
        for field in sorted(required_case_fields):
            if case.get(field) in ("", None, [], {}):
                failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "missing": field})
        source_clip = case.get("source_clip")
        if isinstance(source_clip, str):
            expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
            if case.get("source_clip_hash") != expected_hash:
                failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "source_clip_hash mismatch"})
            try:
                decoded_clip = json.loads(source_clip)
            except json.JSONDecodeError:
                decoded_clip = {}
            if not isinstance(decoded_clip, dict) or decoded_clip.get("source_ref") != case.get("source_ref"):
                failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "source_clip must decode to the source ref"})
        packet = case.get("semantic_packet")
        if isinstance(packet, dict):
            expected_packet_hash = hashlib.sha256(
                json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            if case.get("semantic_packet_hash") != expected_packet_hash:
                failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "semantic_packet_hash mismatch"})
            for bool_field, expected in (
                ("projection_not_authority", True),
                ("private_source_copied", False),
                ("private_field_rehydration_allowed", False),
                ("public_release_claimed", False),
                ("publication_claimed", False),
                ("private_root_equivalence_claimed", False),
                ("benchmark_win_claimed", False),
            ):
                if packet.get(bool_field) is not expected:
                    failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "packet_flag": bool_field})
            if packet.get("source_clip_hash") != case.get("source_clip_hash"):
                failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "packet must carry the source_clip_hash"})
        carry = case.get("semantic_carryforward") or {}
        if carry.get("projection_not_authority") is not True:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "semantic carryforward must declare projection_not_authority"})
        if carry.get("private_source_copied") is not False or carry.get("private_field_rehydration_allowed") is not False:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "semantic carryforward must block private copy and rehydration"})
        if "no-private-copy" not in str(case.get("no_private_copy_rule")):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "case must include no-private-copy rule"})
        if "source_clip_hash" not in str(case.get("reentry_prompt")):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "reentry prompt must cite source_clip_hash"})
        loss_boundary = case.get("loss_boundary") or {}
        if loss_boundary.get("loss_is_required_for_public_safety") is not True:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "loss boundary must be public-safety explicit"})
        if not case.get("anti_claims"):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "reason": "case must carry anti-claims"})
        source_ref = str(case.get("source_ref") or "").split("::", 1)[0]
        if source_ref and not _path_ref_exists(root, source_ref):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "missing_source_ref": source_ref})
        for evidence_ref in case.get("evidence_refs") or []:
            evidence_path = str(evidence_ref).split("::", 1)[0]
            if evidence_path and not _path_ref_exists(root, evidence_path):
                failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "case_id": case.get("case_id"), "missing_evidence_ref": evidence_path})

    for witness in effectiveness_witnesses:
        if not isinstance(witness, dict):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "reason": "effectiveness witness row must be an object"})
            continue
        witness_id = witness.get("witness_id")
        required_motif = witness.get("required_motif")
        without_shuttle = witness.get("without_shuttle") or {}
        with_shuttle = witness.get("with_shuttle") or {}
        boundary = witness.get("accepted_loss_boundary") or {}
        witness_validator = witness.get("validator") or {}
        if not required_motif:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "required_motif missing"})
        if witness.get("source_case_id") not in {case.get("case_id") for case in cases if isinstance(case, dict)}:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "source_case_id must reference a case"})
        if without_shuttle.get("motif_present") is not False:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "without_shuttle must lose the motif"})
        if with_shuttle.get("motif_present") is not True:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "with_shuttle must preserve the motif"})
        if without_shuttle.get("route_or_behavior") == with_shuttle.get("route_or_behavior"):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "future route or behavior must change"})
        if not str(without_shuttle.get("outcome") or "").startswith("fail"):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "without_shuttle outcome must fail"})
        if not str(with_shuttle.get("outcome") or "").startswith("pass"):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "with_shuttle outcome must pass"})
        if not boundary.get("allowed_loss") or not boundary.get("forbidden_loss"):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "accepted loss boundary must name allowed and forbidden loss"})
        if "restart point" not in set(boundary.get("forbidden_loss") or []):
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "restart point must be forbidden loss"})
        if witness_validator.get("validator_id") != "validator.source_shuttle_effectiveness_witness" or witness_validator.get("status") != "pass":
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "effectiveness validator must pass"})
        if witness_validator.get("future_route_changed") is not True or witness_validator.get("accepted_loss_declared") is not True:
            failures.append({"path": "microcosms/source_shuttle/source_shuttle_board.json", "witness_id": witness_id, "reason": "validator must assert route change and accepted loss"})

    if receipt_path.exists():
        receipt = load_json(receipt_path)
        if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
            failures.append({"path": "microcosms/source_shuttle/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
        if receipt.get("projection_not_authority") is not True:
            failures.append({"path": "microcosms/source_shuttle/receipt.json", "reason": "receipt must declare projection_not_authority"})
        if receipt.get("effectiveness_witness_count") != len(effectiveness_witnesses) or receipt.get("effectiveness_witness_status") != "pass":
            failures.append({"path": "microcosms/source_shuttle/receipt.json", "reason": "receipt must record passing effectiveness witness count"})
        validator_summary = {
            row.get("validator_id"): row.get("status")
            for row in receipt.get("validator_summary", [])
            if isinstance(row, dict)
        }
        if validator_summary.get("validator.source_shuttle_effectiveness_witness") != "pass":
            failures.append({"path": "microcosms/source_shuttle/receipt.json", "reason": "receipt must cite passing source-shuttle effectiveness validator"})
        for field in (
            "public_release_claim_count",
            "publication_claim_count",
            "private_root_equivalence_claim_count",
            "benchmark_win_claim_count",
            "self_attestation_authority_count",
        ):
            if receipt.get(field) != 0:
                failures.append({"path": "microcosms/source_shuttle/receipt.json", "reason": f"receipt {field} must remain zero"})
        for ref in receipt.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref.split("::", 1)[0]):
                failures.append({"path": "microcosms/source_shuttle/receipt.json", "missing_evidence_ref": ref})
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        for required_text in (
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-source-shuttle-specimen --root . --write-receipt",
            "no-private-copy",
            "source_clip_hash",
            "effectiveness witness",
        ):
            if required_text not in readme:
                failures.append({"path": "microcosms/source_shuttle/README.md", "missing_text": required_text})
    return failures


def _provider_harness_canary_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "provider_harness_canary" / "canary_board.json"
    receipt_path = root / "microcosms" / "provider_harness_canary" / "receipt.json"
    readme_path = root / "microcosms" / "provider_harness_canary" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "missing canary board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/provider_harness_canary/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/provider_harness_canary/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "status": board.get("status")})
    if board.get("candidate_id") != "provider_harness_evaluator_authority_split_microcosm":
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "unexpected candidate_id"})
    if board.get("authority_posture") != "public_safe_synthetic_provider_harness_canary_not_real_provider_or_private_eval_authority":
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "unexpected authority posture"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "specimen must not imply public release readiness"})

    summary = board.get("summary", {})
    cases = board.get("cases", [])
    if not isinstance(cases, list) or len(cases) < 4:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected at least four canary cases"})
        cases = []
    if summary.get("case_count") != len(cases):
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "summary case_count mismatch"})
    if int(summary.get("evaluator_pass_count", 0)) < 1:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected at least one evaluator pass"})
    if int(summary.get("evaluator_fail_count", 0)) < 2:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected at least two evaluator failures"})
    if int(summary.get("evaluator_block_count", 0)) < 1:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected at least one blocked provider route"})
    if int(summary.get("provider_self_attested_rejected_count", 0)) < 2:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected rejected self-attested pass cases"})
    if int(summary.get("provider_self_attestation_authority_count", 0)) != 0:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "provider self-attestation must not be status authority"})
    expected_status_channels = [
        "provider_route_status",
        "provider_output_status",
        "provider_self_attested_status",
        "schema_status",
        "answer_status",
        "evaluator_status",
        "receipt_status",
    ]
    if summary.get("status_channel_names") != expected_status_channels:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "status channel names mismatch"})
    if int(summary.get("status_channel_count", 0)) != len(expected_status_channels):
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "status channel count mismatch"})
    if int(summary.get("repair_route_count", 0)) != len(cases):
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "every case must have a repair route"})
    if int(summary.get("provider_route_unavailable_count", 0)) < 1:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected provider route unavailable channel"})
    if int(summary.get("schema_failed_count", 0)) < 1:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected schema failed channel"})
    if int(summary.get("answer_failed_count", 0)) < 1:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "expected answer failed channel"})
    status_contract = board.get("status_channel_contract", {})
    if not isinstance(status_contract, dict) or set(status_contract) != set(expected_status_channels):
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "status channel contract must cover every channel"})

    status_authority_nodes = [
        row.get("node_id")
        for row in board.get("authority_trace", [])
        if isinstance(row, dict) and row.get("status_authority") is True
    ]
    if status_authority_nodes != ["fixture_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "status authority must belong only to evaluator and receipt gate"})

    observed_failure_classes = set()
    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "case row must be an object"})
            continue
        case_id = case.get("case_id")
        response = case.get("provider_response", {})
        decision = case.get("evaluator_decision", {})
        status_channels = case.get("status_channels", {})
        repair_route = case.get("repair_route", {})
        if not isinstance(response, dict) or not isinstance(decision, dict):
            failures.append({"case_id": case_id, "reason": "case must include provider_response and evaluator_decision objects"})
            continue
        if not isinstance(status_channels, dict) or set(status_channels) != set(expected_status_channels + ["final_status_authority"]):
            failures.append({"case_id": case_id, "reason": "case must expose all status channels plus final authority"})
            status_channels = {}
        if status_channels.get("final_status_authority") != "evaluator_decision":
            failures.append({"case_id": case_id, "reason": "final status authority must be evaluator_decision"})
        if status_channels.get("evaluator_status") != decision.get("evaluator_status"):
            failures.append({"case_id": case_id, "reason": "evaluator channel must mirror evaluator decision"})
        if response.get("route_status") != "ok" and status_channels.get("provider_route_status") != "unavailable":
            failures.append({"case_id": case_id, "reason": "route-unavailable response must stay in provider_route_status channel"})
        if decision.get("failure_class") == "schema_failure" and status_channels.get("schema_status") != "failed":
            failures.append({"case_id": case_id, "reason": "schema failure must stay in schema_status channel"})
        if decision.get("failure_class") == "answer_mismatch" and status_channels.get("answer_status") != "failed":
            failures.append({"case_id": case_id, "reason": "answer mismatch must stay in answer_status channel"})
        if not isinstance(repair_route, dict) or not repair_route.get("owner_lane") or not repair_route.get("restart_from"):
            failures.append({"case_id": case_id, "reason": "case must carry an owner_lane repair route with restart point"})
        elif repair_route.get("failure_class") != decision.get("failure_class"):
            failures.append({"case_id": case_id, "reason": "repair route failure_class must match evaluator decision"})
        if decision.get("status_authority") != "evaluator_only":
            failures.append({"case_id": case_id, "reason": "evaluator decision must declare evaluator_only authority"})
        if decision.get("provider_self_attestation_used_as_authority") is not False:
            failures.append({"case_id": case_id, "reason": "provider self-attestation must never be used as authority"})
        if response.get("provider_self_attested_status") == "pass" and decision.get("evaluator_status") != "pass":
            if case.get("provider_self_attestation_rejected") is not True:
                failures.append({"case_id": case_id, "reason": "self-attested pass rejection must be explicit"})
        failure_class = decision.get("failure_class")
        if failure_class:
            observed_failure_classes.add(failure_class)
    required_failure_classes = {"schema_failure", "answer_mismatch", "provider_route_unavailable"}
    missing_failure_classes = sorted(required_failure_classes - observed_failure_classes)
    if missing_failure_classes:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "missing_failure_classes": missing_failure_classes})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/provider_harness_canary/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/provider_harness_canary/canary_board.json",
        "microcosms/provider_harness_canary/README.md",
        "registry/release_candidates.json",
        "src/idea_microcosm/provider_harness_canary_specimen.py",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/provider_harness_canary/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/provider_harness_canary/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-provider-harness-canary-specimen --root . --write-receipt",
        "status_channels",
        "not a real provider harness",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/provider_harness_canary/README.md", "missing_text": required_text})
    return failures


def _executable_grammar_metabolism_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "executable_grammar_metabolism" / "grammar_board.json"
    receipt_path = root / "microcosms" / "executable_grammar_metabolism" / "receipt.json"
    readme_path = root / "microcosms" / "executable_grammar_metabolism" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "missing grammar board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/executable_grammar_metabolism/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/executable_grammar_metabolism/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "status": board.get("status")})
    if board.get("candidate_id") != "executable_grammar_metabolism_microcosm":
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "unexpected candidate_id"})
    if board.get("authority_posture") != "public_safe_synthetic_executable_grammar_fixture_not_private_standard_authority":
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "unexpected authority posture"})

    public_safety_boundary = str(board.get("public_safety_boundary", "")).lower()
    claim_boundary = str(board.get("claim_boundary", "")).lower()
    publication_boundary = str(board.get("publication_boundary", "")).lower()
    for required_text in ("synthetic", "no private", "private standards engine"):
        if required_text not in public_safety_boundary:
            failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "missing_boundary_text": required_text})
    if "not a public release" not in claim_boundary:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "claim boundary must deny public release"})
    if "blocked until" not in publication_boundary:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "publication boundary must stay fail-closed"})

    summary = board.get("summary", {})
    cases = board.get("cases", [])
    grammar_rules = board.get("grammar_rules", [])
    if not isinstance(cases, list) or len(cases) < 6:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "expected at least six grammar cases"})
        cases = []
    if not isinstance(grammar_rules, list):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "grammar_rules must be a list"})
        grammar_rules = []
    if summary.get("case_count") != len(cases):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "summary case_count mismatch"})
    if int(summary.get("pass_count", 0)) < 1:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "expected at least one passing grammar case"})
    if int(summary.get("block_count", 0)) < 4:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "expected at least four blocked grammar cases"})
    if int(summary.get("repair_row_count", 0)) < int(summary.get("block_count", 0)):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "blocked cases must emit repair rows"})
    if summary.get("worker_action_count") != len(cases):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "summary worker_action_count mismatch"})
    if int(summary.get("repair_routed_count", -1)) != int(summary.get("block_count", 0)):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "blocked cases must route fail-closed worker actions"})
    if int(summary.get("closed_transaction_count", -1)) != int(summary.get("pass_count", 0)):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "passing cases must close local-only transactions"})
    if int(summary.get("publication_permission_count", -1)) != 0:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "worker actions must not grant publication permission"})
    if int(summary.get("public_claim_block_count", 0)) < 1:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "expected a publication-before-gates block"})
    if board.get("grammar_loop") != [
        "standards",
        "projection_case",
        "metabolism",
        "worker_action",
        "proof",
        "transaction",
        "publish-later",
    ]:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "grammar loop must include worker action and transaction stages"})

    required_rule_ids = {
        "required_improvement_delta",
        "source_refs_required",
        "allowed_projection_strategy",
        "anti_vague_praise",
        "no_publication_before_gates",
    }
    rule_ids = {
        row.get("rule_id")
        for row in grammar_rules
        if isinstance(row, dict)
    }
    observed_rule_ids = set(summary.get("observed_rule_ids", [])) if isinstance(summary.get("observed_rule_ids"), list) else set()
    missing_rule_ids = sorted(required_rule_ids - rule_ids)
    missing_observed_rule_ids = sorted(required_rule_ids - observed_rule_ids)
    if missing_rule_ids:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "missing_rule_ids": missing_rule_ids})
    if missing_observed_rule_ids:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "missing_observed_rule_ids": missing_observed_rule_ids})

    status_authority_nodes = summary.get("status_authority_nodes")
    if status_authority_nodes != ["grammar_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "status authority must belong only to grammar evaluator and receipt gate"})

    provider_bridge = board.get("provider_replay_bridge")
    provider_bridge_contract = board.get("provider_replay_bridge_contract", {})
    provider_canary_path = root / "microcosms" / "provider_harness_canary" / "canary_board.json"
    expected_status_channels = {
        "provider_route_status",
        "provider_output_status",
        "provider_self_attested_status",
        "schema_status",
        "answer_status",
        "evaluator_status",
        "receipt_status",
        "final_status_authority",
    }
    canary_cases: list[dict[str, Any]] = []
    if provider_canary_path.exists():
        canary_board = load_json(provider_canary_path)
        canary_cases = [row for row in canary_board.get("cases", []) if isinstance(row, dict)]
    else:
        failures.append({"path": "microcosms/provider_harness_canary/canary_board.json", "reason": "missing provider canary board for replay bridge"})
    if provider_bridge_contract.get("source_board") != "microcosms/provider_harness_canary/canary_board.json":
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge must name provider canary source board"})
    if provider_bridge_contract.get("authority_rule") != "provider_canary_evaluator_result_drives_grammar_replay_action":
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge authority rule mismatch"})
    if not isinstance(provider_bridge, list):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider_replay_bridge must be a list"})
        provider_bridge = []
    if len(provider_bridge) != len(canary_cases):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge must cover every provider canary case"})
    if summary.get("provider_replay_bridge_case_count") != len(provider_bridge):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge case count mismatch"})
    if int(summary.get("provider_replay_bridge_failure_count", 0)) < 2:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge must include failing repair routes"})
    if summary.get("provider_replay_bridge_repair_route_count") != len(provider_bridge):
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge repair route count mismatch"})
    expected_status_channel_count = sum(len(row.get("status_channel_names", [])) for row in provider_bridge if isinstance(row, dict))
    if summary.get("provider_replay_bridge_status_channel_count") != expected_status_channel_count:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge status channel count mismatch"})
    if summary.get("provider_replay_bridge_authority_collapse_count") != 0:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay bridge must preserve evaluator authority"})
    for row in provider_bridge:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "provider replay row must be an object"})
            continue
        bridge_case_id = row.get("bridge_case_id")
        status_channel_names = set(row.get("status_channel_names", [])) if isinstance(row.get("status_channel_names"), list) else set()
        if status_channel_names != expected_status_channels:
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay row status channels mismatch"})
        if row.get("final_status_authority") != "evaluator_decision":
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay row must preserve evaluator final authority"})
        if row.get("provider_self_attestation_used_as_authority") is not False:
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider self-attestation must not be replay authority"})
        if not row.get("status_channels_ref") or not row.get("repair_route_ref"):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay row must carry status channel and repair route refs"})
        grammar_projection = row.get("grammar_projection", {})
        if not isinstance(grammar_projection, dict) or grammar_projection.get("claim_tier") != "provider_canary_replay_fixture_not_real_provider_evidence":
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay row must carry fixture claim tier"})
        worker_action = row.get("worker_action")
        if not isinstance(worker_action, dict):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay row must include worker action"})
            continue
        if worker_action.get("authority_rule") != "provider_canary_evaluator_result_drives_grammar_replay_action":
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay worker action authority rule mismatch"})
        if worker_action.get("publication_permission_granted") is not False:
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay worker action must not grant publication permission"})
        if row.get("failure_class") is None:
            if worker_action.get("transaction_status") != "closed_local_fixture_only":
                failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay pass must close local-only transaction"})
        else:
            if worker_action.get("transaction_status") != "provider_replay_routed_fail_closed":
                failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay failure must route fail-closed transaction"})
            if not row.get("owner_lane") or not row.get("restart_from"):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay failure must name owner lane and restart point"})
        if not worker_action.get("required_refs"):
            failures.append({"bridge_case_id": bridge_case_id, "reason": "provider replay worker action must carry required refs"})

    seen_pass = False
    seen_block = False
    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "case row must be an object"})
            continue
        case_id = case.get("case_id")
        evaluation = case.get("evaluation", {})
        if not isinstance(evaluation, dict):
            failures.append({"case_id": case_id, "reason": "case must include evaluation object"})
            continue
        status = evaluation.get("status")
        if status == "pass":
            seen_pass = True
        if status == "block":
            seen_block = True
            if not evaluation.get("grammar_failures") or not evaluation.get("repair_rows"):
                failures.append({"case_id": case_id, "reason": "blocked case must include grammar failures and repair rows"})
        if status not in {"pass", "block"}:
            failures.append({"case_id": case_id, "reason": "evaluation status must be pass or block"})
        if evaluation.get("status_authority") != "grammar_evaluator_only":
            failures.append({"case_id": case_id, "reason": "grammar evaluator must be the status authority"})
        if evaluation.get("provider_or_artifact_self_status_used_as_authority") is not False:
            failures.append({"case_id": case_id, "reason": "artifact self-status must not be used as authority"})
        worker_action = case.get("worker_action")
        if not isinstance(worker_action, dict):
            failures.append({"case_id": case_id, "reason": "case must include worker_action object"})
        else:
            if worker_action.get("authority_rule") != "grammar_evaluator_result_drives_worker_action":
                failures.append({"case_id": case_id, "reason": "worker action must be driven by grammar evaluator"})
            if worker_action.get("publication_permission_granted") is not False:
                failures.append({"case_id": case_id, "reason": "worker action must not grant publication permission"})
            if status == "block" and worker_action.get("transaction_status") != "repair_routed_fail_closed":
                failures.append({"case_id": case_id, "reason": "blocked case must route fail-closed repair transaction"})
            if status == "pass" and worker_action.get("transaction_status") != "closed_local_fixture_only":
                failures.append({"case_id": case_id, "reason": "passing case must close local-only transaction"})
            if not worker_action.get("required_refs"):
                failures.append({"case_id": case_id, "reason": "worker action must carry required_refs"})
        if case.get("expected_status") != status:
            failures.append({"case_id": case_id, "reason": "case did not match expected status"})
    if not seen_pass or not seen_block:
        failures.append({"path": "microcosms/executable_grammar_metabolism/grammar_board.json", "reason": "fixture must include both pass and block outcomes"})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/executable_grammar_metabolism/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/executable_grammar_metabolism/grammar_board.json",
        "microcosms/executable_grammar_metabolism/README.md",
        "microcosms/provider_harness_canary/canary_board.json",
        "microcosms/provider_harness_canary/receipt.json",
        "registry/release_candidates.json",
        "src/idea_microcosm/executable_grammar_specimen.py",
        "src/idea_microcosm/provider_harness_canary_specimen.py",
        "src/idea_microcosm/release_candidates.py",
        "src/idea_microcosm/validators.py",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/executable_grammar_metabolism/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/executable_grammar_metabolism/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-executable-grammar-metabolism-specimen --root . --write-receipt",
        "not the private standards engine",
        "worker action",
        "provider status-channel",
        "replay repair route",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/executable_grammar_metabolism/README.md", "missing_text": required_text})
    return failures


def _concurrency_mission_control_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "concurrency_mission_control" / "mission_board.json"
    bridge_path = root / "microcosms" / "concurrency_mission_control" / "work_metabolism_bridge.json"
    provider_bridge_path = root / "microcosms" / "concurrency_mission_control" / "provider_repair_bridge.json"
    residual_replay_bridge_path = (
        root / "microcosms" / "concurrency_mission_control" / "task_ledger_residual_replay_bridge.json"
    )
    receipt_path = root / "microcosms" / "concurrency_mission_control" / "receipt.json"
    readme_path = root / "microcosms" / "concurrency_mission_control" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "missing mission board"})
    if not bridge_path.exists():
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "missing work-metabolism bridge"})
    if not provider_bridge_path.exists():
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "missing provider repair bridge"})
    if not residual_replay_bridge_path.exists():
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "missing residual replay bridge"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/concurrency_mission_control/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/concurrency_mission_control/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    bridge = load_json(bridge_path)
    provider_bridge = load_json(provider_bridge_path)
    residual_replay_bridge = load_json(residual_replay_bridge_path)
    receipt = load_json(receipt_path)
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "status": board.get("status")})
    if board.get("candidate_id") != "concurrency_transaction_mission_control_microcosm":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "unexpected candidate_id"})
    if board.get("authority_posture") != "public_safe_synthetic_transaction_fixture_not_private_mission_control_runtime":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "unexpected authority posture"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "specimen must not imply public release readiness"})

    public_safety_boundary = str(board.get("public_safety_boundary", "")).lower()
    claim_boundary = str(board.get("claim_boundary", "")).lower()
    publication_boundary = str(board.get("publication_boundary", "")).lower()
    for required_text in ("synthetic", "no private", "mission-control runtime"):
        if required_text not in public_safety_boundary:
            failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "missing_boundary_text": required_text})
    if "not a scheduler" not in claim_boundary:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "claim boundary must deny scheduler authority"})
    if "blocked until" not in publication_boundary:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "publication boundary must stay fail-closed"})

    summary = board.get("summary", {})
    cases = board.get("cases", [])
    if not isinstance(cases, list) or len(cases) < 9:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "expected at least nine mission cases"})
        cases = []
    if summary.get("case_count") != len(cases):
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "summary case_count mismatch"})
    if int(summary.get("accept_count", 0)) < 1:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "expected at least one accepted case"})
    if int(summary.get("block_count", 0)) < 8:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "expected at least eight blocked cases"})
    if int(summary.get("repair_row_count", 0)) < int(summary.get("block_count", 0)):
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "blocked cases must emit repair rows"})
    for field in (
        "write_scope_conflict_count",
        "duplicate_command_run_count",
        "dependency_block_count",
        "stale_lease_count",
        "missing_receipt_block_count",
        "supervised_scope_missing_contract_count",
        "missing_parent_finalizer_count",
        "misanchored_claim_count",
    ):
        if int(summary.get(field, 0)) < 1:
            failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "missing_summary_count": field})
    if int(summary.get("parent_scope_lane_count", 0)) < 4:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "expected supervised parent-scope lane coverage"})
    if summary.get("status_authority_nodes") != ["mission_transaction_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "status authority must belong only to transaction evaluator and receipt gate"})
    if int(summary.get("lane_self_status_authority_count", 0)) != 0:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "lane self-status must not be status authority"})
    if board.get("work_metabolism_bridge_ref") != "microcosms/concurrency_mission_control/work_metabolism_bridge.json":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "mission board missing work-metabolism bridge ref"})
    if board.get("provider_to_concurrency_repair_loop_ref") != "microcosms/concurrency_mission_control/provider_repair_bridge.json":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "mission board missing provider repair bridge ref"})
    if board.get("task_ledger_residual_replay_bridge_ref") != "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "mission board missing residual replay bridge ref"})
    if summary.get("work_metabolism_bridge_status") != "ok":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "mission board must report bridge ok"})
    if summary.get("provider_repair_bridge_status") != "ok":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "mission board must report provider repair bridge ok"})
    if summary.get("task_ledger_residual_replay_bridge_status") != "ok":
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "mission board must report residual replay bridge ok"})
    if int(summary.get("work_metabolism_transaction_step_count", 0)) < 9:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "bridge transaction path is incomplete"})
    if int(summary.get("work_metabolism_authority_collapse_count", -1)) != 0:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "bridge authority collapse count must be zero"})
    if int(summary.get("provider_repair_bridge_case_count", 0)) < 4:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "provider repair bridge must cover provider canary cases"})
    if int(summary.get("provider_repair_bridge_repair_route_count", 0)) < 3:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "provider failures must become repair routes"})
    if int(summary.get("provider_repair_bridge_teaching_rule_count", 0)) < int(summary.get("provider_repair_bridge_case_count", 0)):
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "provider repair bridge cases must carry teaching rules"})
    if int(summary.get("provider_repair_bridge_source_capsule_count", 0)) < int(summary.get("provider_repair_bridge_case_count", 0)):
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "provider repair bridge cases must carry source capsules"})
    if int(summary.get("provider_repair_bridge_authority_collapse_count", -1)) != 0:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "provider repair bridge authority collapse count must be zero"})
    if int(summary.get("task_ledger_residual_replay_case_count", 0)) < 4:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "residual replay bridge must cover Task Ledger provider residual cases"})
    if int(summary.get("task_ledger_residual_replay_repair_route_count", 0)) < 3:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "open provider residuals must become repair routes"})
    if int(summary.get("task_ledger_residual_replay_replay_seed_count", 0)) < int(summary.get("task_ledger_residual_replay_case_count", 0)):
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "residual replay cases must carry replay seeds"})
    if int(summary.get("task_ledger_residual_replay_teaching_rule_count", 0)) < int(summary.get("task_ledger_residual_replay_case_count", 0)):
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "residual replay cases must carry teaching rules"})
    if int(summary.get("task_ledger_residual_replay_source_capsule_count", 0)) < int(summary.get("task_ledger_residual_replay_case_count", 0)):
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "residual replay cases must carry source capsules"})
    if int(summary.get("task_ledger_residual_replay_authority_collapse_count", -1)) != 0:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "residual replay bridge authority collapse count must be zero"})

    if provider_bridge.get("kind") != "provider_to_concurrency_repair_loop":
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "unexpected provider repair bridge kind"})
    if provider_bridge.get("status") != "ok":
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "status": provider_bridge.get("status")})
    if provider_bridge.get("authority_posture") != "public_safe_provider_repair_transaction_bridge_not_real_provider_or_live_concurrency_authority":
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "unexpected provider repair bridge authority posture"})
    if provider_bridge.get("source_board") != "microcosms/provider_harness_canary/canary_board.json":
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider repair bridge must consume provider canary board"})
    if provider_bridge.get("target_board") != "microcosms/concurrency_mission_control/mission_board.json":
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider repair bridge must target mission board"})
    generated_by = provider_bridge.get("generated_by", {}) if isinstance(provider_bridge.get("generated_by"), dict) else {}
    if generated_by.get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider repair bridge must declare projection_not_authority"})
    provider_bridge_summary = provider_bridge.get("summary", {}) if isinstance(provider_bridge.get("summary"), dict) else {}
    provider_bridge_rows = provider_bridge.get("bridge_rows", [])
    if provider_bridge_summary.get("case_count") != len(provider_bridge_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider bridge summary case_count mismatch"})
    if int(provider_bridge_summary.get("repair_route_count", 0)) < 3:
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider repair bridge must include failure repair routes"})
    if int(provider_bridge_summary.get("replay_seed_count", 0)) != len(provider_bridge_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "every provider bridge row needs replay seed"})
    if int(provider_bridge_summary.get("teaching_rule_count", 0)) != len(provider_bridge_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "every provider bridge row needs teaching rule"})
    if int(provider_bridge_summary.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider self-attestation must not be bridge authority"})
    if int(provider_bridge_summary.get("blocked_public_claim_count", 0)) < 4:
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider repair bridge must block public overclaims"})
    provider_bridge_provenance = (
        provider_bridge.get("source_capsule_provenance", {})
        if isinstance(provider_bridge.get("source_capsule_provenance"), dict)
        else {}
    )
    provider_bridge_capsules = provider_bridge_provenance.get("source_capsules", [])
    if provider_bridge_provenance.get("schema_version") != "source_capsule_provenance_v0":
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider bridge provenance schema mismatch"})
    if len(provider_bridge_capsules) != len(provider_bridge_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider bridge capsules must cover every row"})
    for row in provider_bridge_rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider bridge row must be an object"})
            continue
        if not row.get("source_clip") or not row.get("source_clip_hash"):
            failures.append({"case_id": row.get("case_id"), "reason": "provider bridge row missing source clip or hash"})
        elif row["source_clip_hash"] != _json_sha256(row["source_clip"]):
            failures.append({"case_id": row.get("case_id"), "reason": "provider bridge row source hash mismatch"})
        if not row.get("transaction_claim") or not row.get("repair_route"):
            failures.append({"case_id": row.get("case_id"), "reason": "provider bridge row missing transaction claim or repair route"})
        if not row.get("restart_point") or not row.get("teaching_rule"):
            failures.append({"case_id": row.get("case_id"), "reason": "provider bridge row missing restart point or teaching rule"})
        if row.get("provider_evaluator_result", {}).get("provider_self_attestation_used_as_authority") is not False:
            failures.append({"case_id": row.get("case_id"), "reason": "provider self-attestation entered bridge authority"})
        if not row.get("anti_claims"):
            failures.append({"case_id": row.get("case_id"), "reason": "provider bridge row missing anti-claims"})
    for capsule in provider_bridge_capsules:
        if not isinstance(capsule, dict):
            failures.append({"path": "microcosms/concurrency_mission_control/provider_repair_bridge.json", "reason": "provider bridge capsule must be an object"})
            continue
        if capsule.get("source_class") != "public_safe_provider_to_concurrency_bridge_row":
            failures.append({"capsule_id": capsule.get("capsule_id"), "reason": "unexpected provider bridge source class"})
        if capsule.get("clip_hash") != _json_sha256(capsule.get("source_clip", {})):
            failures.append({"capsule_id": capsule.get("capsule_id"), "reason": "provider bridge capsule hash mismatch"})

    if residual_replay_bridge.get("kind") != "task_ledger_residual_to_concurrency_replay_bridge":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "unexpected residual replay bridge kind"})
    if residual_replay_bridge.get("status") != "ok":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "status": residual_replay_bridge.get("status")})
    if residual_replay_bridge.get("authority_posture") != "public_safe_task_ledger_residual_replay_bridge_not_private_task_or_work_ledger_authority":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "unexpected residual replay bridge authority posture"})
    if residual_replay_bridge.get("source_bridge") != "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge must consume Task Ledger provider residual bridge"})
    if residual_replay_bridge.get("target_board") != "microcosms/concurrency_mission_control/mission_board.json":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge must target mission board"})
    generated_by = (
        residual_replay_bridge.get("generated_by", {})
        if isinstance(residual_replay_bridge.get("generated_by"), dict)
        else {}
    )
    if generated_by.get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge must declare projection_not_authority"})
    residual_summary = (
        residual_replay_bridge.get("summary", {})
        if isinstance(residual_replay_bridge.get("summary"), dict)
        else {}
    )
    residual_mechanism = (
        residual_replay_bridge.get("mechanism", {})
        if isinstance(residual_replay_bridge.get("mechanism"), dict)
        else {}
    )
    residual_rows = residual_mechanism.get("cases", [])
    if residual_summary.get("case_count") != len(residual_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge summary case_count mismatch"})
    if int(residual_summary.get("source_residual_case_count", 0)) < 4:
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge must cover provider residual cases"})
    if int(residual_summary.get("repair_route_count", 0)) < 3:
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "open residuals must include repair routes"})
    if int(residual_summary.get("replay_seed_count", 0)) != len(residual_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "every residual replay row needs replay seed"})
    if int(residual_summary.get("teaching_rule_count", 0)) != len(residual_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "every residual replay row needs teaching rule"})
    if int(residual_summary.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay self-attestation must not be authority"})
    if int(residual_summary.get("blocked_public_claim_count", 0)) < 5:
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge must block public overclaims"})
    if residual_summary.get("next_gap") != "github_export_scope_manifest_hardening":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge must advance the next core gap"})
    if residual_summary.get("next_owner") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay bridge must name the next core owner"})
    residual_provenance = (
        residual_replay_bridge.get("source_capsule_provenance", {})
        if isinstance(residual_replay_bridge.get("source_capsule_provenance"), dict)
        else {}
    )
    residual_capsules = residual_provenance.get("source_capsules", [])
    if residual_provenance.get("schema_version") != "source_capsule_provenance_v0":
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay provenance schema mismatch"})
    if len(residual_capsules) != len(residual_rows):
        failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay capsules must cover every row"})
    for row in residual_rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay row must be an object"})
            continue
        if not row.get("source_clip") or not row.get("source_clip_hash"):
            failures.append({"case_id": row.get("case_id"), "reason": "residual replay row missing source clip or hash"})
        elif row["source_clip_hash"] != _json_sha256(row["source_clip"]):
            failures.append({"case_id": row.get("case_id"), "reason": "residual replay row source hash mismatch"})
        if not row.get("transaction_claim") or not row.get("repair_route"):
            failures.append({"case_id": row.get("case_id"), "reason": "residual replay row missing transaction claim or repair route"})
        if not row.get("restart_point") or not row.get("teaching_rule"):
            failures.append({"case_id": row.get("case_id"), "reason": "residual replay row missing restart point or teaching rule"})
        if not row.get("replay_seed", {}).get("command", "").startswith("PYTHONPATH=src python3 -m idea_microcosm.cli "):
            failures.append({"case_id": row.get("case_id"), "reason": "residual replay row must expose runnable replay command"})
        if row.get("authority", {}).get("self_attestation_authority") is not False:
            failures.append({"case_id": row.get("case_id"), "reason": "residual replay self-attestation entered authority"})
        if not row.get("anti_claims"):
            failures.append({"case_id": row.get("case_id"), "reason": "residual replay row missing anti-claims"})
    for capsule in residual_capsules:
        if not isinstance(capsule, dict):
            failures.append({"path": "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json", "reason": "residual replay capsule must be an object"})
            continue
        if capsule.get("source_class") != "public_safe_task_ledger_residual_replay_case":
            failures.append({"capsule_id": capsule.get("capsule_id"), "reason": "unexpected residual replay source class"})
        if capsule.get("clip_hash") != _json_sha256(capsule.get("source_clip", {})):
            failures.append({"capsule_id": capsule.get("capsule_id"), "reason": "residual replay capsule hash mismatch"})

    if bridge.get("kind") != "work_metabolism_bridge" or bridge.get("id") != "microcosm.concurrency_mission_control.work_metabolism_bridge":
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "unexpected work-metabolism bridge identity"})
    if bridge.get("status") != "ok":
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "status": bridge.get("status")})
    if bridge.get("authority_posture") != "public_safe_synthetic_work_metabolism_bridge_not_private_ledger_or_runtime_authority":
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "unexpected bridge authority posture"})
    if bridge.get("mission_thread_id") != "work_becomes_durable_substrate":
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must bind the work-becomes-durable-substrate thread"})
    if bridge.get("selected_contribution") != "self_indexing_cognitive_substrate":
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must foreground selected contribution"})
    bridge_summary = bridge.get("summary", {}) if isinstance(bridge.get("summary"), dict) else {}
    if int(bridge_summary.get("transaction_step_count", 0)) < 9:
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must expose full transaction path"})
    if int(bridge_summary.get("authority_boundary_count", 0)) < 5:
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must expose authority boundaries"})
    if int(bridge_summary.get("prior_art_boundary_count", 0)) < 4:
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must expose public prior-art boundaries"})
    if int(bridge_summary.get("authority_collapse_count", -1)) != 0:
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge authority collapse count must be zero"})
    if int(bridge_summary.get("duplicate_command_run_count", 0)) < 1:
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must surface duplicate command-run pressure"})
    if bridge_summary.get("next_gap") != "github_export_scope_manifest_hardening":
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must advance the next core gap"})
    if bridge_summary.get("next_owner") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge must name the next core owner"})
    transaction_steps = {
        step.get("step_id")
        for step in bridge.get("transaction_path", [])
        if isinstance(step, dict)
    }
    expected_steps = {
        "capture",
        "shape",
        "claim_or_lease",
        "mutate_or_plan",
        "validate",
        "commit_or_receipt",
        "closeout",
        "residual",
        "residual_replay",
        "projection_update",
    }
    if not expected_steps.issubset(transaction_steps):
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge transaction path missing steps"})
    bridge_evidence_refs = set(bridge.get("evidence_refs", []))
    required_bridge_refs = {
        "microcosms/task_ledger_cap_economy/events.jsonl",
        "microcosms/task_ledger_cap_economy/projection.json",
        "microcosms/task_ledger_cap_economy/receipt.json",
        "microcosms/provider_harness_canary/canary_board.json",
        "microcosms/provider_harness_canary/receipt.json",
        "microcosms/concurrency_mission_control/mission_board.json",
        "microcosms/concurrency_mission_control/receipt.json",
        "microcosms/concurrency_mission_control/work_metabolism_bridge.json",
        "microcosms/concurrency_mission_control/provider_repair_bridge.json",
        "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json",
        "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json",
        "src/idea_microcosm/concurrency_mission_control_specimen.py",
        "src/idea_microcosm/validators.py",
    }
    missing_bridge_refs = sorted(required_bridge_refs - bridge_evidence_refs)
    if missing_bridge_refs:
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "missing_evidence_refs": missing_bridge_refs})
    for ref in bridge_evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "missing_evidence_ref": ref})
    prior_art_ids = {
        row.get("prior_art_id")
        for row in bridge.get("public_prior_art_boundaries", [])
        if isinstance(row, dict)
    }
    if not {
        "event_sourcing_event_log",
        "temporal_durable_execution",
        "azure_saga_distributed_transactions",
        "opentelemetry_observability_signals",
    }.issubset(prior_art_ids):
        failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "reason": "bridge missing public prior-art boundary ids"})
    for phrase in ("event sourcing", "durable workflow", "saga", "observability", "hosted-public"):
        if not any(phrase in str(claim).lower() for claim in bridge.get("anti_claims", [])):
            failures.append({"path": "microcosms/concurrency_mission_control/work_metabolism_bridge.json", "missing_anti_claim_fragment": phrase})

    authority_nodes = [
        row.get("node_id")
        for row in board.get("authority_trace", [])
        if isinstance(row, dict) and row.get("status_authority") is True
    ]
    if authority_nodes != ["mission_transaction_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "authority trace mismatch"})

    seen_accept = False
    seen_block = False
    observed_failure_classes: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "case row must be an object"})
            continue
        case_id = case.get("case_id")
        decision = case.get("evaluator_decision", {})
        if not isinstance(decision, dict):
            failures.append({"case_id": case_id, "reason": "case must include evaluator_decision object"})
            continue
        status = decision.get("evaluator_status")
        if status == "accept":
            seen_accept = True
        elif status == "block":
            seen_block = True
            if not decision.get("failures") or not decision.get("repair_rows"):
                failures.append({"case_id": case_id, "reason": "blocked case must include failures and repair rows"})
            observed_failure_classes.update(str(row.get("failure_class")) for row in decision.get("failures", []) if isinstance(row, dict))
        else:
            failures.append({"case_id": case_id, "reason": "evaluator_status must be accept or block"})
        if decision.get("status_authority") != "mission_transaction_evaluator_only":
            failures.append({"case_id": case_id, "reason": "mission transaction evaluator must be the status authority"})
        if decision.get("lane_self_status_used_as_authority") is not False:
            failures.append({"case_id": case_id, "reason": "lane self-status must never be used as authority"})
        if case.get("expected_decision") != status:
            failures.append({"case_id": case_id, "reason": "case did not match expected decision"})
    if not seen_accept or not seen_block:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "reason": "fixture must include accepted and blocked outcomes"})
    missing_failure_classes = sorted(
        {
            "write_scope_conflict",
            "duplicate_command_run",
            "dependency_not_complete",
            "stale_lease",
            "missing_receipt",
        }
        - observed_failure_classes
    )
    if missing_failure_classes:
        failures.append({"path": "microcosms/concurrency_mission_control/mission_board.json", "missing_failure_classes": missing_failure_classes})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/concurrency_mission_control/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/concurrency_mission_control/mission_board.json",
        "microcosms/concurrency_mission_control/work_metabolism_bridge.json",
        "microcosms/concurrency_mission_control/provider_repair_bridge.json",
        "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json",
        "microcosms/provider_harness_canary/canary_board.json",
        "microcosms/provider_harness_canary/receipt.json",
        "microcosms/concurrency_mission_control/README.md",
        "microcosms/task_ledger_cap_economy/events.jsonl",
        "microcosms/task_ledger_cap_economy/projection.json",
        "microcosms/task_ledger_cap_economy/receipt.json",
        "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json",
        "registry/release_candidates.json",
        "src/idea_microcosm/concurrency_mission_control_specimen.py",
        "src/idea_microcosm/validators.py",
        "skills/cold_start_agent.md",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/concurrency_mission_control/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/concurrency_mission_control/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
        "not the private mission-control runtime",
        "duplicate focused validation",
        "work_metabolism_bridge.json",
        "provider_repair_bridge.json",
        "task_ledger_residual_replay_bridge.json",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/concurrency_mission_control/README.md", "missing_text": required_text})
    return failures


def _native_concurrency_guard_failures(root: Path) -> list[dict[str, Any]]:
    required_paths = {
        "guard": root / "src" / "idea_microcosm" / "concurrency_guard.py",
        "cli": root / "src" / "idea_microcosm" / "cli.py",
        "docs": root / "docs" / "concurrency_guard.md",
        "tests": root / "tests" / "test_concurrency_guard.py",
        "gitignore": root / ".gitignore",
    }
    failures: list[dict[str, Any]] = []
    for label, path in required_paths.items():
        if not path.exists():
            failures.append({"path": str(path.relative_to(root)), "reason": f"missing native concurrency {label}"})
    if failures:
        return failures

    guard_text = required_paths["guard"].read_text(encoding="utf-8")
    for required_text in (
        "SCHEMA_VERSION = \"microcosm_concurrency_guard_v0\"",
        "active_path_conflict",
        "active_command_key_singleflight",
        "supervised_scope_missing_contract",
        "git_landing_plan",
        "scoped_commit",
        "renew_session",
        "status_report",
        "start_command",
        "finish_command",
        "event_type == \"renew\"",
        "event_type\": \"command_start\"",
        "event_type\": \"command_finish\"",
        "active_command_key_singleflight",
        "active_command_run_conflict",
        "_active_command_run_path_conflicts",
        "missing_active_command_run",
        "renewed_at",
        "missing_active_claim",
        "head_cas_rule",
        "external_staged_paths_present",
        "external_staged_paths_present_after_add",
        "scoped_path_commit_allowed",
        "broad_git_add_blocked",
        "normal_git_commit_blocked",
        "authority_boundary",
        "_locked_events",
    ):
        if required_text not in guard_text:
            failures.append({"path": "src/idea_microcosm/concurrency_guard.py", "missing_text": required_text})

    cli_text = required_paths["cli"].read_text(encoding="utf-8")
    for command in (
        "concurrency-preflight",
        "concurrency-status",
        "concurrency-renew",
        "concurrency-command-start",
        "concurrency-command-finish",
        "concurrency-git-plan",
        "concurrency-scoped-commit",
        "concurrency-release",
        "concurrency-finalize",
    ):
        if command not in cli_text:
            failures.append({"path": "src/idea_microcosm/cli.py", "missing_command": command})

    docs_text = required_paths["docs"].read_text(encoding="utf-8")
    for required_text in (
        "clone-local",
        "concurrency-preflight",
        "concurrency-status",
        "concurrency-renew",
        "concurrency-command-start",
        "concurrency-command-finish",
        "concurrency-git-plan",
        "concurrency-scoped-commit",
        "concurrency-finalize",
        "expected_parent",
        "scoped_commit",
        "renew_session",
        "command_start",
        "command_finish",
        "active_command_key_singleflight",
        "active_command_run_conflict",
        "stale_claim_count",
        "missing_active_claim",
        "external_staged_paths_present_after_add",
        "git add -A",
        "git commit -am",
        "not the private Work Ledger",
        "not publication",
    ):
        if required_text not in docs_text:
            failures.append({"path": "docs/concurrency_guard.md", "missing_text": required_text})

    tests_text = required_paths["tests"].read_text(encoding="utf-8")
    for required_text in (
        "test_claim_blocks_overlap_and_releases",
        "test_parent_scope_requires_full_contract",
        "test_git_contract_blocks_broad_add_but_allows_scoped_paths",
        "test_git_landing_plan_adds_head_cas_and_blocks_external_staged",
        "test_git_landing_plan_normalizes_nested_microcosm_paths",
        "test_scoped_commit_requires_active_claim",
        "test_scoped_commit_commits_owned_paths_and_finalizes_claim",
        "test_scoped_commit_blocks_external_staged_paths",
        "test_renew_extends_existing_claim_without_duplicate",
        "test_renew_blocks_missing_active_claim",
        "test_status_reports_active_and_stale_claims",
        "test_command_start_blocks_duplicate_and_finish_allows_next",
        "test_command_start_respects_path_claims_and_command_run_paths",
        "test_preflight_blocks_active_command_run_on_owner_path",
        "test_git_landing_plan_blocks_active_command_run_on_owned_path",
        "test_scoped_commit_blocks_active_command_run_on_owned_path",
        "test_status_reports_stale_and_completed_command_runs",
        "test_cli_preflight_and_finalize",
        "test_cli_git_plan",
        "test_cli_scoped_commit",
        "test_cli_renew_and_status",
        "test_cli_command_start_and_finish",
    ):
        if required_text not in tests_text:
            failures.append({"path": "tests/test_concurrency_guard.py", "missing_test": required_text})

    gitignore_text = required_paths["gitignore"].read_text(encoding="utf-8")
    if ".idea_microcosm/" not in gitignore_text:
        failures.append({"path": ".gitignore", "reason": "clone-local concurrency state must stay untracked"})
    return failures


def _concept_graph_cards_failures(root: Path) -> list[dict[str, Any]]:
    graph_path = root / "microcosms" / "concept_graph_cards" / "concept_graph.json"
    atlas_path = root / "microcosms" / "concept_graph_cards" / "cold_entry_atlas.json"
    receipt_path = root / "microcosms" / "concept_graph_cards" / "receipt.json"
    readme_path = root / "microcosms" / "concept_graph_cards" / "README.md"
    failures: list[dict[str, Any]] = []
    if not graph_path.exists():
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "missing concept graph"})
    if not atlas_path.exists():
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "missing cold entry atlas"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/concept_graph_cards/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/concept_graph_cards/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    graph = load_json(graph_path)
    atlas = load_json(atlas_path)
    receipt = load_json(receipt_path)
    if graph.get("status") != "ok":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "status": graph.get("status")})
    if graph.get("candidate_id") != "concept_graph_cards_microcosm":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "unexpected candidate_id"})
    if graph.get("authority_posture") != "public_safe_concept_graph_fixture_not_private_ontology_or_claim_graph":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "unexpected authority posture"})
    if graph.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(graph).lower():
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "specimen must not imply public release readiness"})

    public_safety_boundary = str(graph.get("public_safety_boundary", "")).lower()
    claim_boundary = str(graph.get("claim_boundary", "")).lower()
    publication_boundary = str(graph.get("publication_boundary", "")).lower()
    for required_text in ("public-safe", "no private", "ontology"):
        if required_text not in public_safety_boundary:
            failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "missing_boundary_text": required_text})
    if "private-system equivalence" not in claim_boundary:
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "claim boundary must deny private-system equivalence"})
    if "blocked until" not in publication_boundary:
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "publication boundary must stay fail-closed"})

    summary = graph.get("summary", {})
    concept_cards = graph.get("concept_cards", [])
    edges = graph.get("edges", [])
    required_concepts = {
        "microcosm",
        "leaf",
        "receipt",
        "atlas",
        "evaluator",
        "cap",
        "skill",
        "standard",
        "retirement_evidence",
        "idea",
        "concept",
        "principle",
        "axiom",
        "mechanism",
        "paper_module",
        "projection",
        "authority_boundary",
        "validator",
        "navigation_packet",
        "artifact_manifest",
        "capability",
        "work_item",
        "teleology",
        "module_blueprint",
        "port_packet",
        "strategy",
        "release_gate",
        "summary_ladder",
        "band_flag",
        "human_read_layer",
        "ai_native_layer",
        "drilldown_layer",
        "root_projection",
        "evidence_surface",
        "proof_path",
        "anti_claim",
        "clone_posture",
        "organ",
        "specimen",
    }
    if not isinstance(concept_cards, list) or len(concept_cards) < len(required_concepts):
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "expected concept cards for the release-local concept set"})
        concept_cards = []
    concept_ids = {row.get("concept_id") for row in concept_cards if isinstance(row, dict)}
    missing_concepts = sorted(required_concepts - {str(concept_id) for concept_id in concept_ids})
    if missing_concepts:
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "missing_concepts": missing_concepts})
    if not isinstance(edges, list) or len(edges) < 12:
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "expected at least twelve concept graph edges"})
        edges = []
    if summary.get("concept_count") != len(concept_cards):
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "summary concept_count mismatch"})
    if summary.get("edge_count") != len(edges):
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "summary edge_count mismatch"})
    for field in ("missing_concept_path_count", "dangling_edge_count", "orphan_concept_count", "website_card_outrun_count", "concept_card_self_authority_count"):
        if int(summary.get(field, -1)) != 0:
            failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "nonzero_summary_count": field, "value": summary.get(field)})
    if summary.get("status_authority_nodes") != ["concept_graph_validator", "receipt_gate"]:
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "status authority must belong only to concept graph validator and receipt gate"})
    if graph.get("cold_entry_atlas_ref") != "microcosms/concept_graph_cards/cold_entry_atlas.json":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "graph must point to the cold entry atlas"})
    if summary.get("cold_entry_atlas_status") != "ok" or summary.get("first_contact_status") != "ok":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "graph summary must expose ok cold-entry status"})
    if summary.get("applied_original_contribution_gap") != "concept_graph_core_self_index_hardening":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "concept graph must close the self-index hardening gap"})
    if summary.get("next_gap_after_entry_atlas") != "github_export_scope_manifest_hardening":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "concept graph must advance to GitHub export scope hardening"})
    if summary.get("next_gap_owner") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "concept graph must name the next gap owner"})

    edge_counts: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "edge row must be an object"})
            continue
        edge_id = edge.get("edge_id")
        from_concept = edge.get("from_concept")
        edge_counts[str(from_concept)] = edge_counts.get(str(from_concept), 0) + 1
        if from_concept not in concept_ids:
            failures.append({"edge_id": edge_id, "reason": "edge source concept must resolve"})
        to_ref = edge.get("to_ref")
        if not isinstance(to_ref, str) or not _path_ref_exists(root, to_ref):
            failures.append({"edge_id": edge_id, "missing_to_ref": to_ref})
        for evidence_ref in edge.get("evidence_refs", []):
            if not _path_ref_exists(root, str(evidence_ref)):
                failures.append({"edge_id": edge_id, "missing_evidence_ref": evidence_ref})
        if edge.get("gate_status") != "pass":
            failures.append({"edge_id": edge_id, "reason": "edge must pass the concept graph gate"})
        if edge.get("status_authority") != "concept_graph_validator_only":
            failures.append({"edge_id": edge_id, "reason": "concept graph validator must be the edge status authority"})
        if edge.get("concept_card_self_status_used_as_authority") is not False:
            failures.append({"edge_id": edge_id, "reason": "concept-card self-status must not be authority"})

    for row in concept_cards:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "concept row must be an object"})
            continue
        concept_id = row.get("concept_id")
        concept_path = row.get("concept_path")
        if not isinstance(concept_path, str) or not _path_ref_exists(root, concept_path):
            failures.append({"concept_id": concept_id, "missing_concept_path": concept_path})
        if not row.get("summary"):
            failures.append({"concept_id": concept_id, "reason": "concept row must include summary"})
        if not row.get("standard_refs") or not row.get("skill_refs") or not row.get("receipt_refs"):
            failures.append({"concept_id": concept_id, "reason": "concept row must include standards, skills, and receipts"})
        if int(row.get("edge_count", 0)) < 1 or edge_counts.get(str(concept_id), 0) < 1:
            failures.append({"concept_id": concept_id, "reason": "concept row must have at least one outgoing edge"})
        for receipt_ref in row.get("receipt_refs", []):
            if not _path_ref_exists(root, str(receipt_ref)):
                failures.append({"concept_id": concept_id, "missing_receipt_ref": receipt_ref})

    website_gate = graph.get("website_projection_gate", {})
    if not isinstance(website_gate, dict) or website_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "website projection gate must fail closed"})
    elif int(website_gate.get("website_card_outrun_count", -1)) != 0:
        failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "reason": "website card outrun count must be zero"})
    for ref in website_gate.get("required_before_website_card_refs", []) if isinstance(website_gate, dict) else []:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/concept_graph_cards/concept_graph.json", "missing_website_gate_ref": ref})

    if atlas.get("kind") != "release_microcosm_cold_entry_atlas" or atlas.get("status") != "ok":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "cold entry atlas must exist and be ok"})
    if atlas.get("selected_contribution") != "self_indexing_cognitive_substrate":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas must foreground the selected contribution"})
    if atlas.get("authority_posture") != "public_safe_first_contact_protocol_not_private_root_or_publication_authority":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "unexpected atlas authority posture"})
    atlas_tracks = atlas.get("entry_tracks", {})
    required_tracks = {"human_reviewer", "technical_cloner", "external_agent", "public_boundary_reviewer"}
    if not isinstance(atlas_tracks, dict) or not required_tracks.issubset(set(atlas_tracks)):
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "missing_tracks": sorted(required_tracks - set(atlas_tracks if isinstance(atlas_tracks, dict) else {}))})
    for track_id in required_tracks:
        track = atlas_tracks.get(track_id, {}) if isinstance(atlas_tracks, dict) else {}
        if not isinstance(track.get("learns"), str) or not track.get("learns"):
            failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "track_id": track_id, "reason": "track must state what it teaches"})
        cannot_support = track.get("cannot_support_claims")
        if not isinstance(cannot_support, list) or not all(isinstance(claim, str) and claim for claim in cannot_support):
            failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "track_id": track_id, "reason": "track must state unsupported claims"})
    atlas_summary = atlas.get("summary", {})
    if atlas_summary.get("first_contact_status") != "ok":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas first-contact status must be ok"})
    if int(atlas_summary.get("entry_track_count", 0)) < 4:
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas must expose at least four first-contact tracks"})
    if int(atlas_summary.get("missing_ref_count", -1)) != 0 or atlas.get("missing_refs"):
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas refs must resolve", "missing_refs": atlas.get("missing_refs")})
    if atlas_summary.get("applied_original_contribution_gap") != "concept_graph_core_self_index_hardening":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas must close the concept graph core gap"})
    if atlas_summary.get("next_gap_after_entry_atlas") != "github_export_scope_manifest_hardening":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas must advance the next gap"})
    if atlas_summary.get("next_gap_owner") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas must name the next gap owner"})
    if atlas_summary.get("work_metabolism_bridge_status") != "bridge_landed":
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas must consume the landed work-metabolism bridge"})
    atlas_graph = atlas.get("concept_graph", {})
    node_kinds = set(atlas_graph.get("node_kinds", [])) if isinstance(atlas_graph, dict) else set()
    if not {"contribution", "microcosm", "command", "evidence", "anti_claim", "boundary_gate", "next_gap"}.issubset(node_kinds):
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas concept graph missing required node kinds"})
    edge_kinds = set(atlas_graph.get("edge_kinds", [])) if isinstance(atlas_graph, dict) else set()
    if not {"explains", "proves_locally", "blocks_overclaim", "next_gap", "supports_contribution"}.issubset(edge_kinds):
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas concept graph missing required edge kinds"})
    analogue_ids = {row.get("analogue_id") for row in atlas.get("public_documentation_analogues", []) if isinstance(row, dict)}
    if not {"github_readme_first_contact", "diataxis_documentation_needs", "nng_progressive_disclosure", "nng_information_scent"}.issubset(analogue_ids):
        failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "reason": "atlas must carry first-contact documentation analogues"})
    for ref in atlas.get("evidence_refs", []):
        if isinstance(ref, str) and ref and ref != "microcosms/concept_graph_cards/cold_entry_atlas.json" and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/concept_graph_cards/cold_entry_atlas.json", "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/concept_graph_cards/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/concept_graph_cards/concept_graph.json",
        "microcosms/concept_graph_cards/cold_entry_atlas.json",
        "microcosms/concept_graph_cards/README.md",
        "concepts/README.md",
        "concepts/cap.md",
        "concepts/skill.md",
        "concepts/standard.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/concept_graph_cards_specimen.py",
        "src/idea_microcosm/validators.py",
        "skills/cold_start_agent.md",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/concept_graph_cards/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/concept_graph_cards/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-concept-graph-cards-specimen --root . --write-receipt",
        "cold_entry_atlas.json",
        "not the private ontology",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/concept_graph_cards/README.md", "missing_text": required_text})
    return failures


def _summary_ladders_specimen_failures(root: Path) -> list[dict[str, Any]]:
    ladders_ref = "microcosms/summary_ladders/summary_ladders.json"
    readme_ref = "microcosms/summary_ladders/README.md"
    receipt_ref = "microcosms/summary_ladders/receipt.json"
    leaf_contract_ref = "microcosms/leaf_entry_contract.json"
    failures: list[dict[str, Any]] = []
    for ref, reason in (
        (ladders_ref, "missing summary ladders"),
        (readme_ref, "missing summary ladders README"),
        (receipt_ref, "missing summary ladders receipt"),
        ("standards/summary_ladder.json", "missing summary ladder standard"),
        ("paper_modules/summary_ladder_projection.md", "missing summary ladder paper module"),
        ("microcosms/specimen_suite/std_python_compliance_report.json", "missing std_python report"),
        ("skills/leaf_porting.md", "missing leaf porting skill"),
        ("skills/summary_ladder_porting.md", "missing summary ladder skill"),
    ):
        if not _path_ref_exists(root, ref):
            failures.append({"path": ref, "reason": reason})
    if failures:
        return failures

    ladders = load_json(root / ladders_ref)
    leaf_contract = load_json(root / leaf_contract_ref)
    receipt = load_json(root / receipt_ref)
    readme = (root / readme_ref).read_text(encoding="utf-8")
    if ladders.get("kind") != "microcosm_summary_ladders":
        failures.append({"path": ladders_ref, "reason": "unexpected kind"})
    if ladders.get("schema_version") != "microcosm_summary_ladders_v0":
        failures.append({"path": ladders_ref, "reason": "unexpected schema_version"})
    if ladders.get("status") != "ok":
        failures.append({"path": ladders_ref, "status": ladders.get("status")})
    if ladders.get("authority_posture") != "generated_navigation_projection_not_source_authority_or_publication_permission":
        failures.append({"path": ladders_ref, "reason": "unexpected authority posture"})
    if ladders.get("standard_ref") != "standards/summary_ladder.json":
        failures.append({"path": ladders_ref, "reason": "missing summary ladder standard ref"})
    if ladders.get("paper_module_ref") != "paper_modules/summary_ladder_projection.md":
        failures.append({"path": ladders_ref, "reason": "missing summary ladder paper module ref"})
    if ladders.get("std_python_standard_ref") != "codex/standards/std_python.py":
        failures.append({"path": ladders_ref, "reason": "missing std_python standard ref"})

    rows = ladders.get("rows", [])
    leaf_rows = leaf_contract.get("leaf_rows", [])
    if not isinstance(rows, list):
        failures.append({"path": ladders_ref, "reason": "rows must be a list"})
        rows = []
    if not isinstance(leaf_rows, list):
        failures.append({"path": leaf_contract_ref, "reason": "leaf_rows must be a list"})
        leaf_rows = []
    leaf_ids = {str(row.get("leaf_id")) for row in leaf_rows if isinstance(row, dict)}
    row_ids = {str(row.get("leaf_id")) for row in rows if isinstance(row, dict)}
    if row_ids != leaf_ids:
        failures.append({"path": ladders_ref, "reason": "summary rows must mirror leaf contract rows", "missing": sorted(leaf_ids - row_ids), "extra": sorted(row_ids - leaf_ids)})

    summary = ladders.get("summary", {})
    if summary.get("leaf_count") != len(leaf_rows):
        failures.append({"path": ladders_ref, "reason": "summary leaf_count must match leaf contract"})
    if summary.get("leaf_count_matches_contract") is not True:
        failures.append({"path": ladders_ref, "reason": "leaf_count_matches_contract must be true"})
    if summary.get("length_level_count") != 4:
        failures.append({"path": ladders_ref, "reason": "expected four length levels"})
    for field in (
        "all_rows_have_one_sentence",
        "all_rows_have_length_layers",
        "all_rows_have_proof_refs",
        "all_rows_have_claim_boundary",
        "all_rows_have_ai_native_layer",
    ):
        if summary.get(field) is not True:
            failures.append({"path": ladders_ref, "reason": f"{field} must be true"})
    if summary.get("std_python_report_available") is not True:
        failures.append({"path": ladders_ref, "reason": "std_python report must be available"})
    rows_with_code_nav = summary.get("rows_with_std_python_navigation", 0)
    if not isinstance(rows_with_code_nav, int) or rows_with_code_nav < max(1, len(leaf_rows) - 2):
        failures.append({"path": ladders_ref, "reason": "summary ladders must route nearly every leaf to std_python navigation"})
    for field in ("human_read_projection_status", "ai_native_projection_status", "claim_boundary_status"):
        if summary.get(field) != "ok":
            failures.append({"path": ladders_ref, "reason": f"{field} must be ok"})

    required_length_keys = {"one_sentence", "concise", "medium", "deep"}
    for row in rows:
        if not isinstance(row, dict):
            failures.append({"path": ladders_ref, "reason": "summary row must be an object"})
            continue
        leaf_id = row.get("leaf_id")
        one_sentence = row.get("one_sentence")
        if not isinstance(one_sentence, str) or not one_sentence.strip() or len(one_sentence) > 240:
            failures.append({"leaf_id": leaf_id, "reason": "one_sentence must be non-empty and <= 240 chars"})
        if not row.get("band_flag"):
            failures.append({"leaf_id": leaf_id, "reason": "missing band flag"})
        length_layers = row.get("length_layers")
        if not isinstance(length_layers, dict) or set(length_layers) != required_length_keys:
            failures.append({"leaf_id": leaf_id, "reason": "length_layers must contain one_sentence, concise, medium, deep"})
        human_layer = row.get("human_read_layer")
        if not isinstance(human_layer, dict) or human_layer.get("primary_projection") != readme_ref:
            failures.append({"leaf_id": leaf_id, "reason": "human_read_layer must point to README projection"})
        ai_layer = row.get("ai_native_layer")
        if not isinstance(ai_layer, dict) or ai_layer.get("primary_projection") != ladders_ref:
            failures.append({"leaf_id": leaf_id, "reason": "ai_native_layer must point to JSON projection"})
            ai_layer = {}
        for key in ("route_tokens", "drilldown_order", "proof_refs", "anti_claims"):
            if not ai_layer.get(key):
                failures.append({"leaf_id": leaf_id, "reason": f"ai_native_layer missing {key}"})
        code_nav = ai_layer.get("std_python_navigation")
        if not isinstance(code_nav, dict):
            failures.append({"leaf_id": leaf_id, "reason": "ai_native_layer missing std_python_navigation"})
            code_nav = {}
        if code_nav.get("report_ref") != "microcosms/specimen_suite/std_python_compliance_report.json":
            failures.append({"leaf_id": leaf_id, "reason": "std_python_navigation missing report ref"})
        if code_nav.get("standard_ref") != "codex/standards/std_python.py":
            failures.append({"leaf_id": leaf_id, "reason": "std_python_navigation missing standard ref"})
        query_commands = code_nav.get("query_commands")
        if not isinstance(query_commands, dict) or "query-std-python" not in str(query_commands.get("card", "")):
            failures.append({"leaf_id": leaf_id, "reason": "std_python_navigation missing card query command"})
        if code_nav.get("status") == "code_cards_available" and not code_nav.get("source_span_refs"):
            failures.append({"leaf_id": leaf_id, "reason": "std_python_navigation card rows must expose source spans"})
        for key in ("proof_refs", "anti_claims", "claim_boundary", "drilldown_order"):
            if not row.get(key):
                failures.append({"leaf_id": leaf_id, "reason": f"summary row missing {key}"})
        for ref in [*row.get("proof_refs", []), *row.get("drilldown_order", [])]:
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"leaf_id": leaf_id, "missing_ref": ref})

    if "AI-Native Layer" not in readme or "summary_ladders.json" not in readme:
        failures.append({"path": readme_ref, "reason": "README must describe human and AI-native layers"})
    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": receipt_ref, "reason": "receipt must be ok with fixture_validated claim tier"})
    required_receipt_refs = {
        ladders_ref,
        readme_ref,
        leaf_contract_ref,
        "standards/summary_ladder.json",
        "paper_modules/summary_ladder_projection.md",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "src/idea_microcosm/summary_ladders_specimen.py",
        "src/idea_microcosm/validators.py",
        "skills/leaf_porting.md",
        "skills/summary_ladder_porting.md",
    }
    evidence_refs = set(receipt.get("evidence_refs", []))
    missing_refs = sorted(required_receipt_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": receipt_ref, "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and ref != receipt_ref and not _path_ref_exists(root, ref):
            failures.append({"path": receipt_ref, "missing_evidence_ref": ref})
    return failures


def _verisoftbench_diagnostic_specimen_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "verisoftbench_diagnostic" / "diagnostic_board.json"
    receipt_path = root / "microcosms" / "verisoftbench_diagnostic" / "receipt.json"
    readme_path = root / "microcosms" / "verisoftbench_diagnostic" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "missing diagnostic board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/verisoftbench_diagnostic/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/verisoftbench_diagnostic/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "status": board.get("status")})
    if board.get("candidate_id") != "verisoftbench_diagnostic_specimen_microcosm":
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "unexpected candidate_id"})
    if board.get("authority_posture") != "public_safe_synthetic_benchmark_diagnostic_fixture_not_real_benchmark_or_private_provider_authority":
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "unexpected authority posture"})
    if board.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "diagnostic board must not imply public release readiness"})

    public_safety_boundary = str(board.get("public_safety_boundary", "")).lower()
    claim_boundary = str(board.get("claim_boundary", "")).lower()
    publication_boundary = str(board.get("publication_boundary", "")).lower()
    for required_text in ("synthetic", "no private", "benchmark"):
        if required_text not in public_safety_boundary:
            failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "missing_boundary_text": required_text})
    for required_text in ("not a verisoftbench score", "private-root equivalence"):
        if required_text not in claim_boundary:
            failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "missing_claim_boundary_text": required_text})
    if "blocked until" not in publication_boundary:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "publication boundary must stay fail-closed"})

    summary = board.get("summary", {})
    cases = board.get("cases", [])
    if not isinstance(cases, list) or len(cases) < 5:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "expected at least five diagnostic cases"})
        cases = []
    if int(summary.get("case_count", 0)) != len(cases):
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "summary case_count mismatch"})
    for field in ("diagnostic_failure_count", "restart_point_count", "failure_origin_count"):
        if int(summary.get(field, 0)) < 4:
            failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "missing_summary_count": field})
    if int(summary.get("synthetic_control_pass_count", 0)) < 1:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "missing_summary_count": "synthetic_control_pass_count"})
    for field in ("provider_self_attestation_authority_count", "benchmark_score_claim_count", "external_trace_count"):
        if int(summary.get(field, -1)) != 0:
            failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "nonzero_summary_count": field, "value": summary.get(field)})
    if summary.get("status_authority_nodes") != ["benchmark_diagnostic_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "status authority must belong only to diagnostic evaluator and receipt gate"})

    authority_nodes = [
        row.get("node_id")
        for row in board.get("authority_trace", [])
        if isinstance(row, dict) and row.get("status_authority") is True
    ]
    if authority_nodes != ["benchmark_diagnostic_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "authority trace mismatch"})

    seen_pass = False
    failure_origins: set[str] = set()
    restart_points: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "case row must be an object"})
            continue
        case_id = case.get("case_id")
        decision = case.get("evaluator_decision", {})
        if not isinstance(decision, dict):
            failures.append({"case_id": case_id, "reason": "case must include evaluator_decision object"})
            continue
        status = decision.get("evaluator_status")
        if status == "pass":
            seen_pass = True
        elif status in {"block", "fail"}:
            failure_origins.add(str(case.get("failure_origin")))
            restart_points.add(str(case.get("restart_point")))
            if not isinstance(case.get("repair_row"), dict) or not case.get("repair_row"):
                failures.append({"case_id": case_id, "reason": "blocked or failed case must include repair_row"})
        else:
            failures.append({"case_id": case_id, "reason": "evaluator_status must be pass, fail, or block"})
        if decision.get("status_authority") != "benchmark_diagnostic_evaluator_only":
            failures.append({"case_id": case_id, "reason": "diagnostic evaluator must be the status authority"})
        if decision.get("provider_self_attestation_used_as_authority") is not False:
            failures.append({"case_id": case_id, "reason": "provider self-attestation must never be used as authority"})
        if decision.get("benchmark_score_claimed") is not False:
            failures.append({"case_id": case_id, "reason": "diagnostic fixture must not claim a benchmark score"})
        if decision.get("external_trace_used") is not False:
            failures.append({"case_id": case_id, "reason": "diagnostic fixture must not use external traces"})
    if not seen_pass:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "fixture must include a synthetic control pass"})
    missing_failure_origins = sorted({"task_input", "harness", "provider", "evaluator"} - failure_origins)
    if missing_failure_origins:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "missing_failure_origins": missing_failure_origins})
    if len(restart_points) < 4:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "reason": "fixture must include four restart points"})

    anti_claims = set(board.get("anti_claims", []))
    for anti_claim in (
        "VeriSoftBench score reported",
        "Lean benchmark solved",
        "provider reliability measured",
        "private benchmark trace exported",
        "public release approved",
    ):
        if anti_claim not in anti_claims:
            failures.append({"path": "microcosms/verisoftbench_diagnostic/diagnostic_board.json", "missing_anti_claim": anti_claim})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/verisoftbench_diagnostic/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/verisoftbench_diagnostic/diagnostic_board.json",
        "microcosms/verisoftbench_diagnostic/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/verisoftbench_diagnostic_specimen.py",
        "src/idea_microcosm/validators.py",
        "microcosms/provider_harness_canary/receipt.json",
        "microcosms/lab_evolve_failure_replay/receipt.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/verisoftbench_diagnostic/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/verisoftbench_diagnostic/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-verisoftbench-diagnostic-specimen --root . --write-receipt",
        "not a VeriSoftBench score",
        "synthetic",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/verisoftbench_diagnostic/README.md", "missing_text": required_text})
    return failures


def _meta_diagnostics_workbench_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "meta_diagnostics_workbench" / "diagnostic_board.json"
    receipt_path = root / "microcosms" / "meta_diagnostics_workbench" / "receipt.json"
    readme_path = root / "microcosms" / "meta_diagnostics_workbench" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "missing diagnostic board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/meta_diagnostics_workbench/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/meta_diagnostics_workbench/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "status": board.get("status")})
    if board.get("candidate_id") != "meta_diagnostics_workbench_microcosm":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "unexpected candidate_id"})
    if board.get("authority_posture") != "public_safe_synthetic_meta_diagnostic_fixture_not_private_root_or_live_performance_authority":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "unexpected authority posture"})
    if board.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "diagnostic board must not imply public release readiness"})

    public_safety_boundary = str(board.get("public_safety_boundary", "")).lower()
    claim_boundary = str(board.get("claim_boundary", "")).lower()
    publication_boundary = board.get("publication_boundary", {})
    publication_boundary_text = json.dumps(publication_boundary, sort_keys=True).lower()
    for required_text in ("synthetic", "no private", "diagnostic"):
        if required_text not in public_safety_boundary:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_boundary_text": required_text})
    for required_text in ("not command-speed certification", "private-root context-fit proof", "standalone wrapper shipment", "private-root equivalence"):
        if required_text not in claim_boundary:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_claim_boundary_text": required_text})
    if not isinstance(publication_boundary, dict) or publication_boundary.get("status") != "fail_closed" or "blocked_until" not in publication_boundary_text:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "publication boundary must stay fail-closed"})

    summary = board.get("summary", {})
    cases = board.get("cases", [])
    if not isinstance(cases, list) or len(cases) < 7:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "expected at least seven diagnostic cases"})
        cases = []
    if int(summary.get("case_count", 0)) != len(cases):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "summary case_count mismatch"})
    for field, minimum in (
        ("repair_row_count", 6),
        ("diagnostic_family_count", 6),
        ("pass_count", 1),
        ("command_wait_tax_case_count", 1),
        ("latency_seed_transfer_case_count", 1),
        ("standalone_wrapper_target_count", 1),
        ("root_leaf_boundary_case_count", 1),
        ("dogfood_preflight_step_count", 4),
        ("command_latency_inventory_count", 3),
        ("slow_command_rank_count", 1),
        ("singleflight_policy_count", 1),
        ("root_owned_surface_count", 4),
        ("leaf_owned_surface_count", 3),
    ):
        if int(summary.get(field, 0)) < minimum:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_summary_count": field})
    for field in (
        "command_speed_certification_count",
        "live_performance_certification_count",
        "private_telemetry_dependency_count",
        "latency_inventory_private_telemetry_count",
        "private_context_dependency_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "standalone_leaf_supported_count",
    ):
        if int(summary.get(field, -1)) != 0:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "nonzero_summary_count": field, "value": summary.get(field)})
    if summary.get("status_authority_nodes") != ["meta_diagnostic_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "status authority must belong only to meta diagnostic evaluator and receipt gate"})

    dogfood_preflight = board.get("dogfood_preflight", {})
    if not isinstance(dogfood_preflight, dict):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "dogfood_preflight must be an object"})
        dogfood_preflight = {}
    if dogfood_preflight.get("status") != "fixture_ready":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "dogfood preflight must be fixture_ready"})
    if dogfood_preflight.get("context_budget_tokens") != 12000:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "dogfood preflight must carry the local context budget"})
    for field in ("private_root_dependency", "command_speed_certification", "publication_authority"):
        if dogfood_preflight.get(field) is not False:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": f"dogfood preflight must keep {field} false"})
    command_sequence = dogfood_preflight.get("command_sequence", [])
    if not isinstance(command_sequence, list) or len(command_sequence) < 4:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "dogfood preflight must include at least four command/route steps"})
        command_sequence = []
    command_text = "\n".join(str(row.get("command", "")) for row in command_sequence if isinstance(row, dict))
    for required_command in (
        "build-meta-diagnostics-workbench-specimen",
        "idea_microcosm.cli validate --root .",
        "pytest tests/test_microcosm_contract.py -q -k meta_diagnostics",
    ):
        if required_command not in command_text:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_dogfood_command": required_command})
    split_contract = dogfood_preflight.get("standalone_split_contract", {})
    if not isinstance(split_contract, dict):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "standalone_split_contract must be an object"})
        split_contract = {}
    if split_contract.get("root_clone_supported") is not True:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "root clone must stay the supported standalone posture"})
    if split_contract.get("leaf_folder_export_supported") is not False:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "leaf folder export must remain unsupported without wrapper"})
    if split_contract.get("wrapper_gap_status") != "diagnosed_not_solved":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "wrapper gap must be diagnosed, not claimed solved"})
    for field in ("root_owned_surfaces", "leaf_owned_surfaces", "wrapper_required_parts", "forbidden_promotions"):
        if not isinstance(split_contract.get(field), list) or not split_contract.get(field):
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": f"standalone split contract missing {field}"})
    required_wrapper_parts = {"README", "local standards subset", "fixture board", "validator or probe", "receipt", "CLI path"}
    if not required_wrapper_parts.issubset(set(split_contract.get("wrapper_required_parts", []))):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "standalone split contract missing wrapper parts"})

    portability_matrix = board.get("portability_authority_matrix", {})
    if not isinstance(portability_matrix, dict):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "portability_authority_matrix must be an object"})
        portability_matrix = {}
    if portability_matrix.get("status") != "fixture_ready":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "portability authority matrix must be fixture_ready"})
    if portability_matrix.get("schema_version") != "meta_diagnostics_portability_authority_matrix_v0":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "unexpected portability authority matrix schema"})
    modes = portability_matrix.get("modes", [])
    if not isinstance(modes, list):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "portability authority matrix modes must be a list"})
        modes = []
    mode_by_id = {row.get("mode_id"): row for row in modes if isinstance(row, dict)}
    expected_modes = {"private_root_adapter", "release_root_clone", "leaf_subrepo_fixture"}
    missing_modes = sorted(expected_modes - set(mode_by_id))
    if missing_modes:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_portability_modes": missing_modes})
    expected_postures = {
        "private_root_adapter": (
            "private_root_only",
            False,
            "private_root_evidence_must_be_reduced_to_public_safe_fixture_shape_before_release_root_consumption",
        ),
        "release_root_clone": (
            "self_indexing_cognitive_substrate_root",
            True,
            "root_validate_and_focused_test_must_pass_before_release_root_claim_strengthens",
        ),
        "leaf_subrepo_fixture": (
            "microcosms/meta_diagnostics_workbench_only",
            False,
            "leaf_subrepo_requires_wrapper_projection_with_standards_subset_validator_or_probe_receipt_readme_and_cli_path",
        ),
    }
    for mode_id, (scope, standalone_safe, promotion_gate) in expected_postures.items():
        row = mode_by_id.get(mode_id, {})
        if not row:
            continue
        if row.get("scope") != scope:
            failures.append({"mode_id": mode_id, "reason": "portability mode has unexpected scope"})
        if row.get("standalone_safe") is not standalone_safe:
            failures.append({"mode_id": mode_id, "reason": "portability mode has unexpected standalone posture"})
        if row.get("promotion_gate") != promotion_gate:
            failures.append({"mode_id": mode_id, "reason": "portability mode promotion gate drifted"})
        for field in ("may_consume", "may_project", "must_not_export"):
            if not isinstance(row.get(field), list) or not row.get(field):
                failures.append({"mode_id": mode_id, "reason": f"portability mode missing {field}"})
    private_mode = mode_by_id.get("private_root_adapter", {})
    private_forbidden = set(private_mode.get("must_not_export", [])) if isinstance(private_mode, dict) else set()
    for forbidden in ("raw session bodies", "raw prompts", "hidden reasoning", "private root paths", "live command logs", "private Work Ledger session cards"):
        if forbidden not in private_forbidden:
            failures.append({"mode_id": "private_root_adapter", "missing_must_not_export": forbidden})
    leaf_mode = mode_by_id.get("leaf_subrepo_fixture", {})
    leaf_forbidden = set(leaf_mode.get("must_not_export", [])) if isinstance(leaf_mode, dict) else set()
    if "leaf folder alone is standalone" not in leaf_forbidden:
        failures.append({"mode_id": "leaf_subrepo_fixture", "missing_must_not_export": "leaf folder alone is standalone"})
    zero_export_counters = portability_matrix.get("zero_export_counters", {})
    if not isinstance(zero_export_counters, dict):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "zero_export_counters must be an object"})
        zero_export_counters = {}
    required_zero_export_counters = {
        "raw_session_body_export_count",
        "raw_prompt_export_count",
        "hidden_reasoning_export_count",
        "private_path_export_count",
        "live_command_log_export_count",
        "private_work_ledger_card_export_count",
    }
    missing_zero_counters = sorted(required_zero_export_counters - set(zero_export_counters))
    if missing_zero_counters:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_zero_export_counters": missing_zero_counters})
    for field in required_zero_export_counters:
        if int(zero_export_counters.get(field, -1)) != 0:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "nonzero_zero_export_counter": field, "value": zero_export_counters.get(field)})
        if int(summary.get(field, -1)) != 0:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "nonzero_summary_count": field, "value": summary.get(field)})
    expected_summary_counts = {
        "portability_mode_count": len(modes),
        "standalone_safe_portability_mode_count": sum(1 for row in modes if isinstance(row, dict) and row.get("standalone_safe") is True),
        "root_only_adapter_mode_count": sum(1 for row in modes if isinstance(row, dict) and row.get("scope") == "private_root_only"),
        "leaf_subrepo_blocked_mode_count": sum(
            1
            for row in modes
            if isinstance(row, dict)
            and row.get("scope") == "microcosms/meta_diagnostics_workbench_only"
            and row.get("standalone_safe") is False
        ),
        "zero_export_counter_count": len(zero_export_counters),
        "nonzero_zero_export_counter_count": sum(1 for value in zero_export_counters.values() if value != 0),
    }
    for field, expected_value in expected_summary_counts.items():
        if summary.get(field) != expected_value:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "summary_mismatch": field, "expected": expected_value, "actual": summary.get(field)})
    fail_closed_if_missing = set(portability_matrix.get("fail_closed_if_missing", []))
    required_fail_closed = {"release root validator", "focused regression", "receipt", "standards subset", "CLI path", "zero-export counter check"}
    if not required_fail_closed.issubset(fail_closed_if_missing):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "portability matrix missing fail-closed checks"})

    latency_inventory = board.get("command_latency_inventory", {})
    if not isinstance(latency_inventory, dict):
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "command_latency_inventory must be an object"})
        latency_inventory = {}
    if latency_inventory.get("status") != "fixture_ready":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "command latency inventory must be fixture_ready"})
    if latency_inventory.get("ranking_basis") != "observed_ms_desc_public_safe_fixture":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "command latency inventory must rank by observed fixture milliseconds"})
    latency_rows = latency_inventory.get("rows", [])
    if not isinstance(latency_rows, list) or len(latency_rows) < 3:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "command latency inventory must include at least three ranked rows"})
        latency_rows = []
    previous_observed_ms: int | None = None
    seen_wait_tax_row = False
    seen_singleflight_policy = False
    for row in latency_rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "command latency inventory row must be an object"})
            continue
        for field in ("rank", "command_id", "command_key", "command_family", "observed_ms", "threshold_ms", "wait_tax_ms", "within_budget", "concurrency_policy", "owner_surface", "repair_route"):
            if field not in row:
                failures.append({"command_id": row.get("command_id"), "reason": f"command latency inventory missing {field}"})
        observed_ms = int(row.get("observed_ms", 0))
        threshold_ms = int(row.get("threshold_ms", 0))
        wait_tax_ms = int(row.get("wait_tax_ms", 0))
        if previous_observed_ms is not None and observed_ms > previous_observed_ms:
            failures.append({"command_id": row.get("command_id"), "reason": "command latency inventory must be sorted by observed_ms descending"})
        previous_observed_ms = observed_ms
        if observed_ms <= 0 or threshold_ms <= 0:
            failures.append({"command_id": row.get("command_id"), "reason": "command latency inventory must carry positive observed and threshold milliseconds"})
        if row.get("source") != "synthetic_fixture":
            failures.append({"command_id": row.get("command_id"), "reason": "command latency inventory must stay synthetic"})
        if row.get("certifies_live_performance") is not False:
            failures.append({"command_id": row.get("command_id"), "reason": "command latency inventory must not certify live performance"})
        if row.get("imports_private_telemetry") is not False:
            failures.append({"command_id": row.get("command_id"), "reason": "command latency inventory must not import private telemetry"})
        if wait_tax_ms > 0:
            seen_wait_tax_row = True
        if "attach" in str(row.get("concurrency_policy", "")) or "reuse" in str(row.get("concurrency_policy", "")):
            seen_singleflight_policy = True
    if not seen_wait_tax_row:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "command latency inventory must include a wait-tax row"})
    if not seen_singleflight_policy:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "command latency inventory must expose attach/reuse policy"})

    authority_nodes = [
        row.get("node_id")
        for row in board.get("authority_trace", [])
        if isinstance(row, dict) and row.get("status_authority") is True
    ]
    if authority_nodes != ["meta_diagnostic_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "authority trace mismatch"})

    seen_families: set[str] = set()
    repair_row_count = 0
    seen_pass = False
    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "case row must be an object"})
            continue
        case_id = case.get("case_id")
        seen_families.add(str(case.get("diagnostic_family")))
        if not case.get("owner_surface") or not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "case must name owner_surface and repair_route"})
        decision = case.get("evaluator_decision", {})
        if not isinstance(decision, dict):
            failures.append({"case_id": case_id, "reason": "case must include evaluator_decision object"})
            continue
        status = decision.get("evaluator_status")
        if status == "pass":
            seen_pass = True
        elif status in {"block", "fail"}:
            repair_row_count += 1
            if not isinstance(case.get("repair_row"), dict) or not case.get("repair_row"):
                failures.append({"case_id": case_id, "reason": "blocked or failed case must include repair_row"})
        else:
            failures.append({"case_id": case_id, "reason": "evaluator_status must be pass, fail, or block"})
        for field in ("private_context_used", "command_speed_certified", "publication_claimed", "private_root_equivalence_claimed", "standalone_wrapper_claimed"):
            if decision.get(field) is not False:
                failures.append({"case_id": case_id, "reason": f"diagnostic fixture must keep {field} false"})
        if decision.get("status_authority") != "meta_diagnostic_evaluator_only":
            failures.append({"case_id": case_id, "reason": "meta diagnostic evaluator must be the status authority"})
    if not seen_pass:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "fixture must include a synthetic control pass"})
    if repair_row_count < 6:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "reason": "fixture must include at least six repair rows"})
    missing_families = sorted(
        {
            "command_speed",
            "command_wait_tax",
            "context_fit",
            "test_coverage",
            "architecture_boundary",
            "standalone_wrapper",
        }
        - seen_families
    )
    if missing_families:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_diagnostic_families": missing_families})

    anti_claims = set(board.get("anti_claims", []))
    for anti_claim in (
        "command speed certified",
        "microcosm latency fixture certifies live command performance",
        "private context budget proven",
        "standalone leaf wrapper shipped",
        "local diagnostic fixture proves hosted public availability",
        "meta diagnostic board approves publication",
        "microcosm is equivalent to the private root",
    ):
        if anti_claim not in anti_claims:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/diagnostic_board.json", "missing_anti_claim": anti_claim})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/meta_diagnostics_workbench/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
        "microcosms/meta_diagnostics_workbench/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/meta_diagnostics_workbench_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "microcosms/leaf_entry_contract.json",
        "navigation/entry_packet.json",
        "navigation/microcosm_index.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/meta_diagnostics_workbench/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/meta_diagnostics_workbench/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-meta-diagnostics-workbench-specimen --root . --write-receipt",
        "python -m pytest tests/test_microcosm_contract.py -q -k meta_diagnostics",
        "Dogfood preflight",
        "not command-speed certification",
        "command wait-tax",
        "standalone wrapper",
        "synthetic",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/meta_diagnostics_workbench/README.md", "missing_text": required_text})
    return failures


def _frontend_hud_control_surface_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "frontend_cockpit_hud" / "hud_board.json"
    receipt_path = root / "microcosms" / "frontend_cockpit_hud" / "receipt.json"
    readme_path = root / "microcosms" / "frontend_cockpit_hud" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "missing HUD board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/frontend_cockpit_hud/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/frontend_cockpit_hud/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("status") != "ok":
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "status": board.get("status")})
    if board.get("candidate_id") != "frontend_cockpit_hud_control_surface_microcosm":
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "unexpected candidate_id"})
    if board.get("authority_posture") != "public_safe_synthetic_hud_fixture_not_private_frontend_or_live_operator_runtime":
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "unexpected authority posture"})
    if board.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "HUD board must not imply public release readiness"})

    public_safety_boundary = str(board.get("public_safety_boundary", "")).lower()
    claim_boundary = str(board.get("claim_boundary", "")).lower()
    publication_boundary = str(board.get("publication_boundary", "")).lower()
    for required_text in ("synthetic", "no private", "hud"):
        if required_text not in public_safety_boundary:
            failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_boundary_text": required_text})
    for required_text in ("not a private frontend export", "live operator workflow proof"):
        if required_text not in claim_boundary:
            failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_claim_boundary_text": required_text})
    if "blocked until" not in publication_boundary:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "publication boundary must stay fail-closed"})

    panels = board.get("panels", [])
    events = board.get("events", [])
    summary = board.get("summary", {})
    if not isinstance(panels, list) or len(panels) < 4:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "expected at least four HUD panels"})
        panels = []
    if not isinstance(events, list) or len(events) < 5:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "expected at least five HUD events"})
        events = []
    if int(summary.get("panel_count", 0)) != len(panels):
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "summary panel_count mismatch"})
    if int(summary.get("event_count", 0)) != len(events):
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "summary event_count mismatch"})
    if int(summary.get("blocked_event_count", 0)) < 3:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_summary_count": "blocked_event_count"})
    if int(summary.get("receipt_backed_event_count", 0)) < 2:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_summary_count": "receipt_backed_event_count"})
    if int(summary.get("website_card_overrun_block_count", 0)) < 1:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_summary_count": "website_card_overrun_block_count"})
    for field in ("private_runtime_input_count", "ui_self_status_authority_count"):
        if int(summary.get(field, -1)) != 0:
            failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "nonzero_summary_count": field, "value": summary.get(field)})
    if int(summary.get("macro_source_capsule_count", 0)) < 6:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_summary_count": "macro_source_capsule_count"})
    if summary.get("macro_source_body_import_verified") is not True:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "macro source body import must be verified"})
    if summary.get("status_authority_nodes") != ["hud_contract_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "status authority must belong only to HUD contract evaluator and receipt gate"})

    bridge = board.get("macro_source_capsule_bridge", {})
    if not isinstance(bridge, dict):
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "macro_source_capsule_bridge must be an object"})
        bridge = {}
    expected_bridge_refs = {
        "microcosms/imported_macro_source/macro_projection_import_protocol/exported_projection_import_bundle/frontend_cockpit_source_projection_protocol.json",
        "microcosms/imported_macro_source/macro_projection_import_protocol/exported_projection_import_bundle/frontend_cockpit_source_bundle_manifest.json",
        "microcosms/imported_macro_source/frontend_cockpit_hud/exported_frontend_cockpit_source_bundle/source_modules",
    }
    if bridge.get("bridge_id") != "frontend_cockpit_macro_source_capsule_bridge":
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "unexpected macro source bridge id"})
    if bridge.get("status") != "exact_macro_source_imported":
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "macro source bridge must use exact source imports"})
    if int(bridge.get("source_capsule_count", 0)) < 6:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "macro source bridge must cite at least six source capsules"})
    if "provider payload" not in str(bridge.get("authority_ceiling", "")).lower():
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "macro source bridge must exclude provider payload authority"})
    bridge_refs = {
        str(bridge.get("projection_protocol_ref", "")),
        str(bridge.get("source_module_manifest_ref", "")),
        str(bridge.get("source_modules_root_ref", "")),
    }
    missing_bridge_refs = sorted(expected_bridge_refs - bridge_refs)
    if missing_bridge_refs:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_macro_source_bridge_refs": missing_bridge_refs})
    for ref in bridge_refs:
        if ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_macro_source_bridge_ref": ref})
    source_capsules = bridge.get("source_capsules", [])
    if not isinstance(source_capsules, list) or len(source_capsules) < 6:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "macro source bridge must list source capsules"})
    elif "system/server/ui/src/navigation/surfaces.ts" not in source_capsules:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "macro source bridge must include Station surface registry"})

    panel_ids = {row.get("panel_id") for row in panels if isinstance(row, dict)}
    missing_panels = sorted({"operator_command", "runtime_status", "receipt_evidence", "publication_boundary"} - panel_ids)
    if missing_panels:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_panel_ids": missing_panels})
    for panel in panels:
        if not isinstance(panel, dict):
            failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "panel row must be an object"})
            continue
        if panel.get("display_is_authority") is not False:
            failures.append({"panel_id": panel.get("panel_id"), "reason": "HUD display panel must not be status authority"})
        if not panel.get("source_authority"):
            failures.append({"panel_id": panel.get("panel_id"), "reason": "panel must declare source_authority"})

    authority_nodes = [
        row.get("node_id")
        for row in board.get("authority_trace", [])
        if isinstance(row, dict) and row.get("status_authority") is True
    ]
    if authority_nodes != ["hud_contract_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "authority trace mismatch"})

    website_overrun_seen = False
    blocked_count = 0
    receipt_backed_count = 0
    for event in events:
        if not isinstance(event, dict):
            failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "event row must be an object"})
            continue
        event_id = event.get("event_id")
        decision = event.get("status_evaluation", {})
        if not isinstance(decision, dict):
            failures.append({"event_id": event_id, "reason": "event must include status_evaluation object"})
            continue
        status = decision.get("status")
        if status == "block":
            blocked_count += 1
            if not isinstance(event.get("repair_row"), dict) or not event.get("repair_row"):
                failures.append({"event_id": event_id, "reason": "blocked event must include repair_row"})
        elif status == "show":
            pass
        else:
            failures.append({"event_id": event_id, "reason": "status must be show or block"})
        if event.get("receipt_backed") is True:
            receipt_backed_count += 1
        if decision.get("failure_class") == "website_card_outruns_registry":
            website_overrun_seen = True
        if decision.get("status_authority") != "hud_contract_evaluator_only":
            failures.append({"event_id": event_id, "reason": "HUD contract evaluator must be event status authority"})
        if decision.get("display_self_status_used_as_authority") is not False:
            failures.append({"event_id": event_id, "reason": "display state must never be status authority"})
        if decision.get("private_runtime_input_used") is not False:
            failures.append({"event_id": event_id, "reason": "private runtime input must never be used"})
        if decision.get("website_card_claimed_release_ready") is not False:
            failures.append({"event_id": event_id, "reason": "website card must not claim release readiness"})
    if blocked_count < 3:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "fixture must include at least three blocked events"})
    if receipt_backed_count < 2:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "fixture must include at least two receipt-backed events"})
    if not website_overrun_seen:
        failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "reason": "fixture must include a website-card overrun block"})

    anti_claims = set(board.get("anti_claims", []))
    for anti_claim in (
        "private frontend exported",
        "operator runtime observed",
        "HUD display state is status authority",
        "website card approved release readiness",
        "public release approved",
    ):
        if anti_claim not in anti_claims:
            failures.append({"path": "microcosms/frontend_cockpit_hud/hud_board.json", "missing_anti_claim": anti_claim})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/frontend_cockpit_hud/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/frontend_cockpit_hud/hud_board.json",
        "microcosms/frontend_cockpit_hud/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "skills/cold_start_agent.md",
        "src/idea_microcosm/frontend_hud_control_surface_specimen.py",
        "src/idea_microcosm/validators.py",
        "receipts/cold_sandbox_probe_latest.json",
        "release/publication_gate.json",
        "microcosms/imported_macro_source/macro_projection_import_protocol/exported_projection_import_bundle/frontend_cockpit_source_projection_protocol.json",
        "microcosms/imported_macro_source/macro_projection_import_protocol/exported_projection_import_bundle/frontend_cockpit_source_bundle_manifest.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/frontend_cockpit_hud/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/frontend_cockpit_hud/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-frontend-hud-control-surface-specimen --root . --write-receipt",
        "not the private frontend",
        "display state never becomes status authority",
        "exact macro frontend source capsules",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/frontend_cockpit_hud/README.md", "missing_text": required_text})
    return failures


def _demo_receipt_storyboard_failures(root: Path) -> list[dict[str, Any]]:
    storyboard_path = root / "microcosms" / "demo_receipt_storyboard" / "storyboard.json"
    receipt_path = root / "microcosms" / "demo_receipt_storyboard" / "receipt.json"
    readme_path = root / "microcosms" / "demo_receipt_storyboard" / "README.md"
    failures: list[dict[str, Any]] = []
    if not storyboard_path.exists():
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "missing storyboard"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/demo_receipt_storyboard/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/demo_receipt_storyboard/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    storyboard = load_json(storyboard_path)
    receipt = load_json(receipt_path)
    if storyboard.get("specimen_id") != "demo_receipt_storyboard_microcosm":
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "unexpected specimen_id"})
    if storyboard.get("authority_posture") != "public_safe_receipt_backed_demo_storyboard_not_video_or_website_publication":
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "unexpected authority posture"})
    if storyboard.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(storyboard).lower():
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "storyboard must not imply public release readiness"})

    summary = storyboard.get("summary", {})
    scenes = storyboard.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 5:
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "expected at least five scenes"})
        scenes = []
    if int(summary.get("scene_count", 0)) != len(scenes):
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "summary scene_count mismatch"})
    if int(summary.get("blocked_scene_count", 0)) < 1:
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "missing_summary_count": "blocked_scene_count"})
    if int(summary.get("allowed_copy_count", 0)) != len(scenes):
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "every scene must have allowed narration"})
    if int(summary.get("disallowed_claim_count", 0)) < len(scenes):
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "missing_summary_count": "disallowed_claim_count"})
    if int(summary.get("receipt_ref_count", 0)) < len(scenes):
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("website_card_overrun_count", 0)) < 1:
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "missing_summary_count": "website_card_overrun_count"})
    if int(summary.get("public_release_claim_count", -1)) != 0:
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "nonzero_summary_count": "public_release_claim_count"})
    if int(summary.get("display_self_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "nonzero_summary_count": "display_self_authority_count"})
    if summary.get("status_authority_nodes") != ["storyboard_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "status authority must belong only to storyboard evaluator and receipt gate"})
    if storyboard.get("website_projection_gate", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "website projection gate must stay fail-closed"})

    validator_ids = {row.get("id") for row in load_json(root / "registry" / "validators.json").get("rows", []) if isinstance(row, dict)}
    candidate_ids = {row.get("candidate_id") for row in load_json(root / "registry" / "release_candidates.json").get("rows", []) if isinstance(row, dict)}
    blocked_scene_seen = False
    for scene in scenes:
        if not isinstance(scene, dict):
            failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "scene row must be an object"})
            continue
        scene_id = scene.get("scene_id")
        if scene.get("candidate_id") not in candidate_ids:
            failures.append({"scene_id": scene_id, "unknown_candidate": scene.get("candidate_id")})
        if scene.get("display_surface_is_authority") is not False:
            failures.append({"scene_id": scene_id, "reason": "scene display surface must not be authority"})
        if not scene.get("allowed_narration"):
            failures.append({"scene_id": scene_id, "reason": "missing allowed narration"})
        if not scene.get("disallowed_claims"):
            failures.append({"scene_id": scene_id, "reason": "missing disallowed claims"})
        if not scene.get("receipt_refs"):
            failures.append({"scene_id": scene_id, "reason": "missing receipt refs"})
        if not scene.get("validator_refs"):
            failures.append({"scene_id": scene_id, "reason": "missing validator refs"})
        if str(scene.get("scene_status", "")).startswith("block"):
            blocked_scene_seen = True
        for ref in scene.get("source_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"scene_id": scene_id, "missing_source_ref": ref})
        for ref in scene.get("receipt_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"scene_id": scene_id, "missing_receipt_ref": ref})
        for validator_ref in scene.get("validator_refs", []):
            if validator_ref not in validator_ids:
                failures.append({"scene_id": scene_id, "unknown_validator": validator_ref})
    if not blocked_scene_seen:
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "expected a blocked publication scene"})

    pattern_routes = storyboard.get("pattern_transfer_routes", [])
    if not isinstance(pattern_routes, list):
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "pattern_transfer_routes must be a list"})
        pattern_routes = []
    routes_by_id = {row.get("route_id"): row for row in pattern_routes if isinstance(row, dict)}
    grammar_route = routes_by_id.get("pattern.grammar_replay_bridge_to_demo_storyboard")
    if not isinstance(grammar_route, dict):
        failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "missing grammar replay bridge route"})
    else:
        bridge_cases = grammar_route.get("bridge_cases", [])
        if not isinstance(bridge_cases, list):
            failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "bridge_cases must be a list"})
            bridge_cases = []
        if grammar_route.get("status") != "ready_local_fixture":
            failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "route must be ready_local_fixture"})
        if int(summary.get("grammar_replay_bridge_route_count", 0)) != 1:
            failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "missing_summary_count": "grammar_replay_bridge_route_count"})
        if int(summary.get("grammar_replay_bridge_case_count", 0)) != len(bridge_cases):
            failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "grammar bridge case count mismatch"})
        if len(bridge_cases) < 3:
            failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "expected at least three bridge cases"})
        if int(grammar_route.get("source_hash_verified_count", 0)) != len(bridge_cases):
            failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "source_hash_verified_count must cover every case"})
        if int(summary.get("grammar_replay_bridge_hash_verified_count", 0)) != len(bridge_cases):
            failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "reason": "summary hash verification count must cover every bridge case"})
        for count_name in (
            "grammar_replay_bridge_source_capsule_count",
            "grammar_replay_bridge_repair_route_count",
            "grammar_replay_bridge_teaching_rule_count",
        ):
            if int(summary.get(count_name, 0)) < len(bridge_cases):
                failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "missing_summary_count": count_name})
        if int(summary.get("grammar_replay_bridge_self_attestation_authority_count", -1)) != 0:
            failures.append({"path": "microcosms/demo_receipt_storyboard/storyboard.json", "nonzero_summary_count": "grammar_replay_bridge_self_attestation_authority_count"})
        if int(grammar_route.get("self_attestation_authority_count", -1)) != 0:
            failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "self-attestation authority count must stay zero"})
        if grammar_route.get("public_claim_allowed") is not False or grammar_route.get("publication_claim_allowed") is not False:
            failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "route must block public and publication claims"})
        if grammar_route.get("private_root_claim_allowed") is not False:
            failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "route must block private-root claims"})
        for bridge_case in bridge_cases:
            if not isinstance(bridge_case, dict):
                failures.append({"route_id": "pattern.grammar_replay_bridge_to_demo_storyboard", "reason": "bridge case must be an object"})
                continue
            bridge_case_id = bridge_case.get("bridge_case_id")
            source_clip = bridge_case.get("source_clip")
            if not isinstance(source_clip, dict):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case must carry source_clip"})
            elif bridge_case.get("source_clip_hash") != _json_sha256(source_clip):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge source_clip_hash mismatch"})
            if bridge_case.get("source_clip_hash_recomputed") != bridge_case.get("source_clip_hash"):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge recomputed hash mismatch"})
            if bridge_case.get("hash_verified") is not True:
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge hash must be verified"})
            if bridge_case.get("evaluator_authority") != "grammar_evaluator_only":
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge evaluator authority must be grammar_evaluator_only"})
            if bridge_case.get("provider_or_artifact_self_status_used_as_authority") is not False:
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge must not use self-status as authority"})
            if not bridge_case.get("repair_route_id"):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case missing repair_route_id"})
            if not bridge_case.get("restart_point"):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case missing restart_point"})
            if not bridge_case.get("teaching_rule"):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case missing teaching_rule"})
            if not bridge_case.get("evidence_refs"):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case missing evidence_refs"})
            if not bridge_case.get("anti_claims"):
                failures.append({"bridge_case_id": bridge_case_id, "reason": "bridge case missing anti_claims"})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/demo_receipt_storyboard/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/demo_receipt_storyboard/storyboard.json",
        "microcosms/demo_receipt_storyboard/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/demo_receipt_storyboard_specimen.py",
        "src/idea_microcosm/validators.py",
        "release/publication_gate.json",
        "microcosms/frontend_cockpit_hud/receipt.json",
        "microcosms/verisoftbench_diagnostic/receipt.json",
        "microcosms/executable_grammar_metabolism/grammar_board.json",
        "microcosms/lab_evolve_failure_replay/replay_graph.json",
        "microcosms/lab_evolve_failure_replay/receipt.json",
        "receipts/cold_sandbox_probe_latest.json",
        "receipts/release_candidate_portfolio.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/demo_receipt_storyboard/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/demo_receipt_storyboard/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-demo-receipt-storyboard-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "does not approve publication",
        "Grammar replay bridge",
        "fail_closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/demo_receipt_storyboard/README.md", "missing_text": required_text})
    return failures


def _website_card_projection_gate_failures(root: Path) -> list[dict[str, Any]]:
    gate_path = root / "microcosms" / "website_card_projection_gate" / "card_gate.json"
    receipt_path = root / "microcosms" / "website_card_projection_gate" / "receipt.json"
    readme_path = root / "microcosms" / "website_card_projection_gate" / "README.md"
    failures: list[dict[str, Any]] = []
    if not gate_path.exists():
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "missing card gate"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/website_card_projection_gate/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/website_card_projection_gate/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    gate = load_json(gate_path)
    receipt = load_json(receipt_path)
    if gate.get("specimen_id") != "website_card_projection_gate_microcosm":
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "unexpected specimen_id"})
    if gate.get("authority_posture") != "public_safe_website_card_projection_gate_not_publication_or_website_claim_authority":
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "unexpected authority posture"})
    if gate.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(gate).lower():
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "card gate must not imply public release readiness"})

    summary = gate.get("summary", {})
    cards = gate.get("cards", [])
    if not isinstance(cards, list) or len(cards) < 5:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "expected at least five cards"})
        cards = []
    if int(summary.get("card_count", 0)) != len(cards):
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "summary card_count mismatch"})
    if int(summary.get("allow_count", 0)) < 2:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "allow_count"})
    if int(summary.get("block_count", 0)) < 2:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "block_count"})
    if int(summary.get("receipt_ref_count", 0)) < len(cards):
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("validator_ref_count", 0)) < len(cards):
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "validator_ref_count"})
    if int(summary.get("unsupported_claim_block_count", 0)) < 2:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "unsupported_claim_block_count"})
    if int(summary.get("source_capsule_count", 0)) < 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "source_capsule_count"})
    if int(summary.get("semantic_carryforward_count", 0)) < 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "semantic_carryforward_count"})
    if int(summary.get("repair_route_count", 0)) < 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "repair_route_count"})
    if int(summary.get("teaching_rule_count", 0)) < 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "teaching_rule_count"})
    if int(summary.get("recipient_packet_bridge_projection_block_count", 0)) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "recipient_packet_bridge_projection_block_count"})
    if int(summary.get("source_shuttle_manifest_card_projection_block_count", 0)) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "source_shuttle_manifest_card_projection_block_count"})
    if int(summary.get("source_shuttle_manifest_card_case_count", 0)) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "source_shuttle_manifest_card_case_count"})
    for count_name in (
        "source_shuttle_manifest_card_ref_count",
        "source_shuttle_manifest_card_packet_hash_preserved_count",
        "source_shuttle_manifest_card_source_clip_hash_preserved_count",
        "source_shuttle_manifest_card_no_private_copy_rule_count",
    ):
        if int(summary.get(count_name, 0)) < 6:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": count_name})
    for count_name in (
        "source_shuttle_manifest_card_private_field_rehydration_count",
        "source_shuttle_manifest_card_authority_count",
        "source_shuttle_manifest_card_public_launch_claim_count",
        "source_shuttle_manifest_card_public_release_claim_count",
        "source_shuttle_manifest_card_publication_claim_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": count_name})
    if summary.get("source_shuttle_manifest_card_source_route_id") != "route.private_source_shuttle_packet_review":
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "source shuttle manifest source route mismatch"})
    if int(summary.get("package_promotion_gate_projection_block_count", 0)) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "package_promotion_gate_projection_block_count"})
    if int(summary.get("artifact_digest_requirement_bridge_projection_block_count", 0)) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "artifact_digest_requirement_bridge_projection_block_count"})
    if int(summary.get("grammar_replay_demo_card_gate_projection_block_count", 0)) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "grammar_replay_demo_card_gate_projection_block_count"})
    for count_name in (
        "grammar_replay_demo_card_gate_case_count",
        "grammar_replay_demo_card_gate_source_capsule_count",
        "grammar_replay_demo_card_gate_semantic_carryforward_count",
        "grammar_replay_demo_card_gate_repair_route_count",
        "grammar_replay_demo_card_gate_teaching_rule_count",
        "grammar_replay_demo_card_gate_hash_verified_count",
        "grammar_replay_demo_card_gate_evaluator_authority_count",
    ):
        if int(summary.get(count_name, 0)) < 3:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": count_name})
    if int(summary.get("grammar_replay_demo_card_gate_blocked_claim_count", 0)) < 10:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "grammar_replay_demo_card_gate_blocked_claim_count"})
    if int(summary.get("grammar_replay_demo_card_gate_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": "grammar_replay_demo_card_gate_missing_ref_count"})
    for count_name in (
        "grammar_replay_demo_card_gate_self_attestation_authority_count",
        "grammar_replay_demo_card_gate_public_release_claim_count",
        "grammar_replay_demo_card_gate_publication_claim_count",
        "grammar_replay_demo_card_gate_private_root_equivalence_claim_count",
        "grammar_replay_demo_card_gate_benchmark_win_claim_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": count_name})
    for count_name in (
        "package_promotion_gate_case_count",
        "package_promotion_gate_source_capsule_count",
        "package_promotion_gate_semantic_carryforward_count",
        "package_promotion_gate_repair_route_count",
        "package_promotion_gate_teaching_rule_count",
    ):
        if int(summary.get(count_name, 0)) < 3:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": count_name})
    if int(summary.get("package_promotion_gate_blocked_claim_count", 0)) < 10:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "package_promotion_gate_blocked_claim_count"})
    if int(summary.get("package_promotion_gate_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": "package_promotion_gate_missing_ref_count"})
    for count_name in (
        "package_promotion_gate_self_attestation_authority_count",
        "package_promotion_gate_public_release_claim_count",
        "package_promotion_gate_publication_claim_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": count_name})
    for count_name in (
        "artifact_digest_requirement_bridge_case_count",
        "artifact_digest_requirement_bridge_source_capsule_count",
        "artifact_digest_requirement_bridge_semantic_carryforward_count",
        "artifact_digest_requirement_bridge_repair_route_count",
        "artifact_digest_requirement_bridge_teaching_rule_count",
    ):
        if int(summary.get(count_name, 0)) < 5:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": count_name})
    if int(summary.get("artifact_digest_requirement_bridge_blocked_claim_count", 0)) < 5:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "artifact_digest_requirement_bridge_blocked_claim_count"})
    if int(summary.get("artifact_digest_requirement_bridge_package_row_attachment_count", 0)) < 5:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "artifact_digest_requirement_bridge_package_row_attachment_count"})
    if int(summary.get("artifact_digest_requirement_bridge_source_witness_hash_preserved_count", 0)) < 5:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "missing_summary_count": "artifact_digest_requirement_bridge_source_witness_hash_preserved_count"})
    if int(summary.get("artifact_digest_requirement_bridge_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": "artifact_digest_requirement_bridge_missing_ref_count"})
    for count_name in (
        "artifact_digest_requirement_bridge_self_attestation_authority_count",
        "artifact_digest_requirement_bridge_public_release_claim_count",
        "artifact_digest_requirement_bridge_publication_claim_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": count_name})
    if int(summary.get("website_card_self_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": "website_card_self_authority_count"})
    if int(summary.get("public_release_claim_count", -1)) != 0:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "nonzero_summary_count": "public_release_claim_count"})
    if summary.get("status_authority_nodes") != ["website_card_gate_evaluator", "receipt_gate"]:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "status authority must belong only to website-card evaluator and receipt gate"})
    if gate.get("website_projection_gate", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "website projection gate must stay fail-closed"})

    validator_ids = {row.get("id") for row in load_json(root / "registry" / "validators.json").get("rows", []) if isinstance(row, dict)}
    candidate_ids = {row.get("candidate_id") for row in load_json(root / "registry" / "release_candidates.json").get("rows", []) if isinstance(row, dict)}
    for card in cards:
        if not isinstance(card, dict):
            failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "card row must be an object"})
            continue
        card_id = card.get("card_id")
        if card.get("candidate_id") not in candidate_ids:
            failures.append({"card_id": card_id, "unknown_candidate": card.get("candidate_id")})
        if card.get("display_surface_is_authority") is not False:
            failures.append({"card_id": card_id, "reason": "display surface must not be authority"})
        if card.get("website_card_is_authority") is not False:
            failures.append({"card_id": card_id, "reason": "website card must not be authority"})
        if not card.get("source_refs"):
            failures.append({"card_id": card_id, "reason": "missing source refs"})
        if not card.get("receipt_refs"):
            failures.append({"card_id": card_id, "reason": "missing receipt refs"})
        if not card.get("validator_refs"):
            failures.append({"card_id": card_id, "reason": "missing validator refs"})
        decision = card.get("evaluator_decision", {})
        if decision.get("status") not in {"allow", "block"}:
            failures.append({"card_id": card_id, "reason": "decision status must be allow or block"})
        if decision.get("status_authority") != "website_card_gate_evaluator_only":
            failures.append({"card_id": card_id, "reason": "unexpected decision authority"})
        if decision.get("website_card_self_status_used_as_authority") is not False:
            failures.append({"card_id": card_id, "reason": "website card self-status used as authority"})
        if decision.get("public_release_claimed") is not False:
            failures.append({"card_id": card_id, "reason": "decision must not claim public release"})
        if decision.get("status") == "block" and not decision.get("repair_row"):
            failures.append({"card_id": card_id, "reason": "blocked card missing repair row"})
        capsule = card.get("source_capsule")
        if capsule:
            source_clip = str(capsule.get("source_clip") or "")
            if capsule.get("source_clip_hash") != hashlib.sha256(source_clip.encode("utf-8")).hexdigest():
                failures.append({"card_id": card_id, "reason": "source capsule hash mismatch"})
            if capsule.get("projection_not_authority") is not True:
                failures.append({"card_id": card_id, "reason": "source capsule must declare projection_not_authority"})
            if not capsule.get("semantic_carryforward"):
                failures.append({"card_id": card_id, "reason": "source capsule missing semantic carryforward"})
            if not capsule.get("repair_route"):
                failures.append({"card_id": card_id, "reason": "source capsule missing repair route"})
            if not capsule.get("restart_point"):
                failures.append({"card_id": card_id, "reason": "source capsule missing restart point"})
            if not capsule.get("teaching_rule"):
                failures.append({"card_id": card_id, "reason": "source capsule missing teaching rule"})
            if not capsule.get("anti_claims"):
                failures.append({"card_id": card_id, "reason": "source capsule missing anti-claims"})
            authority_flags = capsule.get("authority_flags", {})
            for flag_name in (
                "self_attestation_used_as_authority",
                "projection_used_as_claim_authority",
                "public_release_claimed",
                "publication_claimed",
                "private_root_equivalence_claimed",
                "benchmark_win_claimed",
            ):
                if authority_flags.get(flag_name) is not False:
                    failures.append({"card_id": card_id, "unexpected_authority_flag": flag_name})
            for ref in capsule.get("evidence_refs", []):
                if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                    failures.append({"card_id": card_id, "missing_capsule_evidence_ref": ref})
        for ref in card.get("source_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"card_id": card_id, "missing_source_ref": ref})
        for ref in card.get("receipt_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"card_id": card_id, "missing_receipt_ref": ref})
        for validator_ref in card.get("validator_refs", []):
            if validator_ref not in validator_ids:
                failures.append({"card_id": card_id, "unknown_validator": validator_ref})
    bridge_cards = [
        card for card in cards if card.get("card_id") == "card.recipient_packet_bridge_projection_boundary"
    ]
    if len(bridge_cards) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "missing recipient packet bridge boundary card"})
    else:
        bridge_card = bridge_cards[0]
        decision = bridge_card.get("evaluator_decision", {})
        capsule = bridge_card.get("source_capsule", {})
        if decision.get("status") != "block" or decision.get("failure_class") != "recipient_packet_bridge_projection_overrun":
            failures.append({"card_id": "card.recipient_packet_bridge_projection_boundary", "reason": "recipient bridge card must block overrun copy"})
        if capsule.get("source_ref") != (
            "microcosms/public_release_package_manifest_gate/public_projection_handoff.json::"
            "recipient_packet_bridge_bounds_projection_handoff"
        ):
            failures.append({"card_id": "card.recipient_packet_bridge_projection_boundary", "reason": "unexpected bridge source capsule ref"})
        for required_claim in (
            "recipient packet bridge approves outreach send",
            "recipient packet bridge can rehydrate private fields",
            "recipient packet bridge proves publication or public release",
        ):
            if required_claim not in bridge_card.get("disallowed_claims", []):
                failures.append({"card_id": "card.recipient_packet_bridge_projection_boundary", "missing_disallowed_claim": required_claim})
    source_shuttle_cards = [
        card for card in cards if card.get("card_id") == "card.source_shuttle_manifest_website_boundary"
    ]
    if len(source_shuttle_cards) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "missing source-shuttle manifest website boundary card"})
    else:
        source_shuttle_card = source_shuttle_cards[0]
        decision = source_shuttle_card.get("evaluator_decision", {})
        capsule = source_shuttle_card.get("source_capsule", {})
        semantic = capsule.get("semantic_carryforward", {})
        if not isinstance(semantic, dict):
            semantic = {}
        manifest_refs = [
            ref for ref in capsule.get("source_shuttle_manifest_bridge_refs", []) if isinstance(ref, dict)
        ]
        if decision.get("status") != "block" or decision.get("failure_class") != "source_shuttle_manifest_website_projection_overrun":
            failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "reason": "source-shuttle manifest card must block launch copy"})
        if capsule.get("source_ref") != (
            "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json::"
            "recipient_packet_manifest_bridge.redacted_draft.private_source_shuttle_packet_review"
        ):
            failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "reason": "unexpected source-shuttle manifest source capsule ref"})
        if capsule.get("source_clip_hash") != hashlib.sha256(str(capsule.get("source_clip") or "").encode("utf-8")).hexdigest():
            failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "reason": "source-shuttle manifest source capsule hash mismatch"})
        if semantic.get("source_route_id") != "route.private_source_shuttle_packet_review":
            failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "reason": "unexpected source-shuttle source route"})
        if int(semantic.get("source_shuttle_manifest_ref_count", -1)) != len(manifest_refs):
            failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "reason": "source-shuttle manifest ref count mismatch"})
        for count_name in (
            "source_shuttle_packet_hash_preserved_count",
            "source_shuttle_source_clip_hash_preserved_count",
            "source_shuttle_no_private_copy_rule_count",
        ):
            if int(semantic.get(count_name, -1)) != len(manifest_refs):
                failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "mismatched_count": count_name})
        for flag_name in (
            "source_shuttle_private_field_rehydration_allowed",
            "source_shuttle_semantic_packet_used_as_card_authority",
            "source_shuttle_manifest_ref_used_as_website_authority",
            "source_shuttle_manifest_ref_used_as_public_launch_authority",
            "source_shuttle_public_launch_claimed",
            "source_shuttle_package_export_claimed",
            "source_shuttle_packet_hash_rehydrates_private_fields",
        ):
            if capsule.get("authority_flags", {}).get(flag_name) is not False:
                failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "unexpected_source_shuttle_flag": flag_name})
        if len(manifest_refs) < 6:
            failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "reason": "missing source-shuttle manifest refs"})
        for ref in manifest_refs:
            for required_key in (
                "source_shuttle_case_id",
                "semantic_packet_id",
                "semantic_packet_hash",
                "source_clip_hash",
                "no_private_copy_rule",
                "restart_point",
                "repair_route",
                "anti_claims",
            ):
                if required_key not in ref:
                    failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "missing_source_shuttle_ref_key": required_key})
        for required_claim in (
            "source-shuttle manifest refs approve website launch",
            "source-shuttle packet hashes rehydrate private fields in website copy",
            "source-shuttle semantic packet becomes website-card source authority",
        ):
            if required_claim not in source_shuttle_card.get("disallowed_claims", []):
                failures.append({"card_id": "card.source_shuttle_manifest_website_boundary", "missing_disallowed_claim": required_claim})
    package_cards = [
        card for card in cards if card.get("card_id") == "card.package_promotion_gate_projection_boundary"
    ]
    if len(package_cards) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "missing package promotion gate boundary card"})
    else:
        package_card = package_cards[0]
        decision = package_card.get("evaluator_decision", {})
        capsule = package_card.get("source_capsule", {})
        if decision.get("status") != "block" or decision.get("failure_class") != "package_promotion_gate_projection_overrun":
            failures.append({"card_id": "card.package_promotion_gate_projection_boundary", "reason": "package promotion card must block launch copy"})
        if capsule.get("source_ref") != "microcosms/public_release_package_manifest_gate/package_promotion_gate.json::status":
            failures.append({"card_id": "card.package_promotion_gate_projection_boundary", "reason": "unexpected package promotion source capsule ref"})
        if capsule.get("source_clip_hash") != hashlib.sha256(str(capsule.get("source_clip") or "").encode("utf-8")).hexdigest():
            failures.append({"card_id": "card.package_promotion_gate_projection_boundary", "reason": "package promotion source capsule hash mismatch"})
        if capsule.get("authority_flags", {}).get("public_package_promotion_allowed") is not False:
            failures.append({"card_id": "card.package_promotion_gate_projection_boundary", "reason": "package promotion may not approve public promotion"})
        if capsule.get("authority_flags", {}).get("package_promotion_used_as_authority") is not False:
            failures.append({"card_id": "card.package_promotion_gate_projection_boundary", "reason": "package promotion must not become card authority"})
        for required_claim in (
            "package promotion gate approves website public-launch copy",
            "package promotion gate can become website-card authority",
            "website card can turn package promotion blockers into launch approval",
        ):
            if required_claim not in package_card.get("disallowed_claims", []):
                failures.append({"card_id": "card.package_promotion_gate_projection_boundary", "missing_disallowed_claim": required_claim})
    artifact_digest_cards = [
        card for card in cards if card.get("card_id") == "card.artifact_digest_requirement_website_boundary"
    ]
    if len(artifact_digest_cards) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "missing artifact digest requirement boundary card"})
    else:
        artifact_card = artifact_digest_cards[0]
        decision = artifact_card.get("evaluator_decision", {})
        capsule = artifact_card.get("source_capsule", {})
        if decision.get("status") != "block" or decision.get("failure_class") != "artifact_digest_requirement_website_projection_overrun":
            failures.append({"card_id": "card.artifact_digest_requirement_website_boundary", "reason": "artifact digest card must block launch copy"})
        if capsule.get("source_ref") != "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json::status":
            failures.append({"card_id": "card.artifact_digest_requirement_website_boundary", "reason": "unexpected artifact digest source capsule ref"})
        if capsule.get("source_clip_hash") != hashlib.sha256(str(capsule.get("source_clip") or "").encode("utf-8")).hexdigest():
            failures.append({"card_id": "card.artifact_digest_requirement_website_boundary", "reason": "artifact digest source capsule hash mismatch"})
        if capsule.get("authority_flags", {}).get("artifact_digest_requirement_used_as_authority") is not False:
            failures.append({"card_id": "card.artifact_digest_requirement_website_boundary", "reason": "artifact digest requirement may not become card authority"})
        if capsule.get("authority_flags", {}).get("artifact_witness_used_as_public_authority") is not False:
            failures.append({"card_id": "card.artifact_digest_requirement_website_boundary", "reason": "artifact witness may not become public authority"})
        for required_claim in (
            "artifact digest requirement approves website launch copy",
            "artifact digest requirement can become website-card authority",
            "website card can turn digest requirement into public availability proof",
        ):
            if required_claim not in artifact_card.get("disallowed_claims", []):
                failures.append({"card_id": "card.artifact_digest_requirement_website_boundary", "missing_disallowed_claim": required_claim})
    grammar_cards = [
        card for card in cards if card.get("card_id") == "card.demo_grammar_replay_website_boundary"
    ]
    if len(grammar_cards) != 1:
        failures.append({"path": "microcosms/website_card_projection_gate/card_gate.json", "reason": "missing demo grammar replay website boundary card"})
    else:
        grammar_card = grammar_cards[0]
        decision = grammar_card.get("evaluator_decision", {})
        capsule = grammar_card.get("source_capsule", {})
        if decision.get("status") != "block" or decision.get("failure_class") != "demo_grammar_replay_website_projection_overrun":
            failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "reason": "demo grammar replay card must block overrun copy"})
        if capsule.get("source_ref") != (
            "microcosms/demo_receipt_storyboard/storyboard.json::"
            "pattern.grammar_replay_bridge_to_demo_storyboard"
        ):
            failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "reason": "unexpected grammar replay source capsule ref"})
        if capsule.get("source_clip_hash") != hashlib.sha256(str(capsule.get("source_clip") or "").encode("utf-8")).hexdigest():
            failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "reason": "grammar replay source capsule hash mismatch"})
        if capsule.get("authority_flags", {}).get("demo_storyboard_used_as_public_authority") is not False:
            failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "reason": "demo storyboard may not become public authority"})
        if capsule.get("authority_flags", {}).get("grammar_replay_used_as_public_authority") is not False:
            failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "reason": "grammar replay may not become public authority"})
        for required_claim in (
            "grammar replay bridge approves website-card copy",
            "demo storyboard can hide failed grammar cases",
            "website card can smooth a failed grammar case into proof",
        ):
            if required_claim not in grammar_card.get("disallowed_claims", []):
                failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "missing_disallowed_claim": required_claim})
        card_gate_cases = capsule.get("card_gate_cases", [])
        if not isinstance(card_gate_cases, list) or len(card_gate_cases) < 3:
            failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "reason": "missing grammar replay card-gate cases"})
            card_gate_cases = []
        for case in card_gate_cases:
            if not isinstance(case, dict):
                failures.append({"card_id": "card.demo_grammar_replay_website_boundary", "reason": "grammar replay card case must be object"})
                continue
            source_clip = str(case.get("source_clip") or "")
            if case.get("source_clip_hash") != hashlib.sha256(source_clip.encode("utf-8")).hexdigest():
                failures.append({"case_id": case.get("case_id"), "reason": "grammar replay card case source hash mismatch"})
            if case.get("upstream_hash_verified") is not True:
                failures.append({"case_id": case.get("case_id"), "reason": "grammar replay upstream hash must be verified"})
            if not case.get("repair_route"):
                failures.append({"case_id": case.get("case_id"), "reason": "grammar replay card case missing repair route"})
            if not case.get("restart_point"):
                failures.append({"case_id": case.get("case_id"), "reason": "grammar replay card case missing restart point"})
            if not case.get("teaching_rule"):
                failures.append({"case_id": case.get("case_id"), "reason": "grammar replay card case missing teaching rule"})
            if not case.get("anti_claims"):
                failures.append({"case_id": case.get("case_id"), "reason": "grammar replay card case missing anti-claims"})
            if case.get("semantic_carryforward", {}).get("projection_not_authority") is not True:
                failures.append({"case_id": case.get("case_id"), "reason": "grammar replay card case must declare projection_not_authority"})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/website_card_projection_gate/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/website_card_projection_gate/card_gate.json",
        "microcosms/website_card_projection_gate/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/website_card_projection_gate_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "microcosms/demo_receipt_storyboard/storyboard.json",
        "microcosms/demo_receipt_storyboard/receipt.json",
        "microcosms/executable_grammar_metabolism/grammar_board.json",
        "microcosms/executable_grammar_metabolism/receipt.json",
        "microcosms/lab_evolve_failure_replay/replay_graph.json",
        "microcosms/lab_evolve_failure_replay/receipt.json",
        "microcosms/frontend_cockpit_hud/receipt.json",
        "microcosms/concept_graph_cards/receipt.json",
        "microcosms/public_release_package_manifest_gate/public_projection_handoff.json",
        "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
        "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
        "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
        "microcosms/source_shuttle/source_shuttle_board.json",
        "microcosms/source_shuttle/receipt.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
        "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json",
        "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json",
        "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
        "microcosms/recipient_review_route_gate/route_gate.json",
        "microcosms/recipient_review_route_gate/receipt.json",
        "microcosms/public_release_package_manifest_gate/receipt.json",
        "microcosms/release_artifact_integrity_witness/integrity_witness.json",
        "microcosms/release_artifact_integrity_witness/receipt.json",
        "state/artifact_manifest.json",
        "receipts/artifact_manifest.json",
        "release/publication_gate.json",
        "receipts/release_candidate_portfolio.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/website_card_projection_gate/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/website_card_projection_gate/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-website-card-projection-gate-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "website card is not evidence",
        "public_projection_handoff.json::recipient_packet_bridge_bounds_projection_handoff",
        "recipient_packet_manifest_bridge.json::recipient_packet_manifest_bridge.redacted_draft.private_source_shuttle_packet_review",
        "package_promotion_gate.json",
        "artifact_digest_requirement_bridge.json",
        "pattern.grammar_replay_bridge_to_demo_storyboard",
        "source capsule hash",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/website_card_projection_gate/README.md", "missing_text": required_text})
    return failures


def _thiel_evidence_packet_gate_failures(root: Path) -> list[dict[str, Any]]:
    packet_path = root / "microcosms" / "thiel_evidence_packet_gate" / "evidence_packet.json"
    receipt_path = root / "microcosms" / "thiel_evidence_packet_gate" / "receipt.json"
    readme_path = root / "microcosms" / "thiel_evidence_packet_gate" / "README.md"
    failures: list[dict[str, Any]] = []
    if not packet_path.exists():
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "missing evidence packet"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    packet = load_json(packet_path)
    receipt = load_json(receipt_path)
    if packet.get("specimen_id") != "thiel_evidence_packet_gate_microcosm":
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "unexpected specimen_id"})
    if packet.get("authority_posture") != "public_safe_thiel_evidence_packet_gate_not_application_or_publication_authority":
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "unexpected authority posture"})
    if packet.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(packet).lower():
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "packet gate must not imply public release readiness"})

    summary = packet.get("summary", {})
    claims = packet.get("claims", [])
    if not isinstance(claims, list) or len(claims) < 6:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "expected at least six claims"})
        claims = []
    if int(summary.get("claim_count", 0)) != len(claims):
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "summary claim_count mismatch"})
    if int(summary.get("allow_count", 0)) < 2:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "missing_summary_count": "allow_count"})
    if int(summary.get("block_count", 0)) < 3:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "missing_summary_count": "block_count"})
    if int(summary.get("unlanded_candidate_block_count", 0)) < 1:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "missing_summary_count": "unlanded_candidate_block_count"})
    if int(summary.get("website_card_as_evidence_block_count", 0)) < 1:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "missing_summary_count": "website_card_as_evidence_block_count"})
    if int(summary.get("receipt_ref_count", 0)) < len(claims):
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("validator_ref_count", 0)) < len(claims):
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "missing_summary_count": "validator_ref_count"})
    for count_name in ("public_release_claim_count", "private_root_equivalence_claim_count", "packet_self_authority_count"):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "nonzero_summary_count": count_name})
    if summary.get("status_authority_nodes") != ["thiel_packet_gate_evaluator", "receipt_gate", "website_card_gate"]:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "status authority must belong only to packet evaluator, receipt gate, and website-card gate"})
    if packet.get("application_packet_gate", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "application packet gate must stay fail-closed"})

    required_failure_classes = {
        "unlanded_candidate_as_proof",
        "website_card_as_evidence",
        "publication_gate_overrun",
        "private_root_equivalence_overclaim",
    }
    observed_failure_classes = {
        claim.get("evaluator_decision", {}).get("failure_class")
        for claim in claims
        if isinstance(claim, dict) and claim.get("evaluator_decision", {}).get("failure_class")
    }
    missing_failure_classes = sorted(required_failure_classes - observed_failure_classes)
    if missing_failure_classes:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "missing_failure_classes": missing_failure_classes})

    validator_ids = {row.get("id") for row in load_json(root / "registry" / "validators.json").get("rows", []) if isinstance(row, dict)}
    candidate_ids = {row.get("candidate_id") for row in load_json(root / "registry" / "release_candidates.json").get("rows", []) if isinstance(row, dict)}
    for claim in claims:
        if not isinstance(claim, dict):
            failures.append({"path": "microcosms/thiel_evidence_packet_gate/evidence_packet.json", "reason": "claim row must be an object"})
            continue
        claim_id = claim.get("claim_id")
        if claim.get("candidate_id") not in candidate_ids:
            failures.append({"claim_id": claim_id, "unknown_candidate": claim.get("candidate_id")})
        if claim.get("application_copy_is_authority") is not False:
            failures.append({"claim_id": claim_id, "reason": "application copy must not be authority"})
        if claim.get("packet_self_status_is_authority") is not False:
            failures.append({"claim_id": claim_id, "reason": "packet self-status must not be authority"})
        if not claim.get("evidence_refs"):
            failures.append({"claim_id": claim_id, "reason": "missing evidence refs"})
        if not claim.get("receipt_refs"):
            failures.append({"claim_id": claim_id, "reason": "missing receipt refs"})
        if not claim.get("validator_refs"):
            failures.append({"claim_id": claim_id, "reason": "missing validator refs"})
        if not claim.get("website_gate_refs"):
            failures.append({"claim_id": claim_id, "reason": "missing website gate refs"})
        decision = claim.get("evaluator_decision", {})
        if decision.get("status") not in {"allow", "block"}:
            failures.append({"claim_id": claim_id, "reason": "decision status must be allow or block"})
        if decision.get("status_authority") != "thiel_packet_gate_evaluator_only":
            failures.append({"claim_id": claim_id, "reason": "unexpected decision authority"})
        if decision.get("packet_self_status_used_as_authority") is not False:
            failures.append({"claim_id": claim_id, "reason": "packet self-status used as authority"})
        if decision.get("public_release_claimed") is not False:
            failures.append({"claim_id": claim_id, "reason": "decision must not claim public release"})
        if decision.get("private_root_equivalence_claimed") is not False:
            failures.append({"claim_id": claim_id, "reason": "decision must not claim private-root equivalence"})
        if decision.get("status") == "block" and not decision.get("repair_row"):
            failures.append({"claim_id": claim_id, "reason": "blocked claim missing repair row"})
        for ref in claim.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"claim_id": claim_id, "missing_evidence_ref": ref})
        for ref in claim.get("receipt_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"claim_id": claim_id, "missing_receipt_ref": ref})
        for ref in claim.get("website_gate_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"claim_id": claim_id, "missing_website_gate_ref": ref})
        for validator_ref in claim.get("validator_refs", []):
            if validator_ref not in validator_ids:
                failures.append({"claim_id": claim_id, "unknown_validator": validator_ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/thiel_evidence_packet_gate/evidence_packet.json",
        "microcosms/thiel_evidence_packet_gate/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/thiel_evidence_packet_gate_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "microcosms/website_card_projection_gate/receipt.json",
        "microcosms/demo_receipt_storyboard/receipt.json",
        "microcosms/release_standards_axiom_gate/receipt.json",
        "receipts/release_candidate_portfolio.json",
        "receipts/cold_sandbox_probe_latest.json",
        "release/publication_gate.json",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/thiel_evidence_packet_gate/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/thiel_evidence_packet_gate/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-thiel-evidence-packet-gate-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "application packet is not evidence",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/thiel_evidence_packet_gate/README.md", "missing_text": required_text})
    return failures


def _recipient_review_route_gate_failures(root: Path) -> list[dict[str, Any]]:
    gate_path = root / "microcosms" / "recipient_review_route_gate" / "route_gate.json"
    graph_path = root / "microcosms" / "recipient_review_route_gate" / "recipient_evidence_graph.json"
    packet_path = root / "microcosms" / "recipient_review_route_gate" / "recipient_packet_omission_receipt.json"
    draft_path = root / "microcosms" / "recipient_review_route_gate" / "redacted_recipient_packet_draft.json"
    bridge_path = root / "microcosms" / "recipient_review_route_gate" / "source_shuttle_evidence_bridge.json"
    bridge_receipt_path = root / "microcosms" / "recipient_review_route_gate" / "source_shuttle_evidence_bridge_receipt.json"
    receipt_path = root / "microcosms" / "recipient_review_route_gate" / "receipt.json"
    readme_path = root / "microcosms" / "recipient_review_route_gate" / "README.md"
    failures: list[dict[str, Any]] = []
    if not gate_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "missing route gate"})
    if not graph_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "missing recipient evidence graph"})
    if not packet_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "missing recipient packet omission receipt"})
    if not draft_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "missing redacted recipient packet draft"})
    if not bridge_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "missing source-shuttle evidence bridge"})
    if not bridge_receipt_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json", "reason": "missing source-shuttle evidence bridge receipt"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/recipient_review_route_gate/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    gate = load_json(gate_path)
    graph = load_json(graph_path)
    packet = load_json(packet_path)
    draft = load_json(draft_path)
    bridge = load_json(bridge_path)
    bridge_receipt = load_json(bridge_receipt_path)
    receipt = load_json(receipt_path)
    if gate.get("specimen_id") != "recipient_review_route_gate_microcosm":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "unexpected specimen_id"})
    if gate.get("authority_posture") != "public_safe_recipient_review_route_gate_not_outreach_or_publication_authority":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "unexpected authority posture"})
    if gate.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(gate).lower():
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "route gate must not imply public release readiness"})

    summary = gate.get("summary", {})
    routes = gate.get("routes", [])
    if not isinstance(routes, list) or len(routes) < 7:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "expected at least seven route rows"})
        routes = []
    if int(summary.get("route_count", 0)) != len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "summary route_count mismatch"})
    if int(summary.get("allow_private_review_count", 0)) < 2:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "allow_private_review_count"})
    if int(summary.get("block_count", 0)) < 4:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "block_count"})
    for count_name in (
        "public_send_block_count",
        "license_citation_gap_block_count",
        "novelty_gap_block_count",
        "hosted_remote_claim_block_count",
        "private_context_leak_block_count",
    ):
        if int(summary.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": count_name})
    if int(summary.get("receipt_ref_count", 0)) < len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("validator_ref_count", 0)) < len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "validator_ref_count"})
    for count_name in (
        "public_release_claim_count",
        "auto_send_claim_count",
        "private_root_equivalence_claim_count",
        "route_self_authority_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": count_name})
    if summary.get("status_authority_nodes") != [
        "recipient_route_gate_evaluator",
        "receipt_gate",
        "publication_gate",
        "thiel_packet_gate",
    ]:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "status authority must belong only to route evaluator, receipt gate, publication gate, and Thiel packet gate"})
    if gate.get("recipient_review_route_gate", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "recipient route gate must stay fail-closed"})
    if gate.get("publication_gate_snapshot", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "publication gate snapshot must be fail-closed"})
    if gate.get("recipient_evidence_graph_ref") != "microcosms/recipient_review_route_gate/recipient_evidence_graph.json":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "missing recipient evidence graph ref"})
    if gate.get("recipient_packet_omission_receipt_ref") != "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "missing recipient packet omission receipt ref"})
    if gate.get("redacted_recipient_packet_draft_ref") != "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "missing redacted recipient packet draft ref"})
    if gate.get("source_shuttle_evidence_bridge_ref") != "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "missing source-shuttle evidence bridge ref"})
    if gate.get("source_shuttle_evidence_bridge_receipt_ref") != "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json":
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "missing source-shuttle evidence bridge receipt ref"})

    required_failure_classes = {
        "public_send_without_publication_gate",
        "novelty_claim_without_prior_art_receipt",
        "license_citation_gap",
        "recipient_specific_private_context_leak",
        "hosted_remote_claim_without_hosted_receipt",
    }
    observed_failure_classes = {
        route.get("evaluator_decision", {}).get("failure_class")
        for route in routes
        if isinstance(route, dict) and route.get("evaluator_decision", {}).get("failure_class")
    }
    missing_failure_classes = sorted(required_failure_classes - observed_failure_classes)
    if missing_failure_classes:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_failure_classes": missing_failure_classes})

    validator_ids = {row.get("id") for row in load_json(root / "registry" / "validators.json").get("rows", []) if isinstance(row, dict)}
    candidate_ids = {row.get("candidate_id") for row in load_json(root / "registry" / "release_candidates.json").get("rows", []) if isinstance(row, dict)}
    for route in routes:
        if not isinstance(route, dict):
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "reason": "route row must be an object"})
            continue
        route_id = route.get("route_id")
        if route.get("candidate_id") not in candidate_ids:
            failures.append({"route_id": route_id, "unknown_candidate": route.get("candidate_id")})
        if route.get("recipient_copy_is_authority") is not False:
            failures.append({"route_id": route_id, "reason": "recipient copy must not be authority"})
        if route.get("route_self_status_is_authority") is not False:
            failures.append({"route_id": route_id, "reason": "route self-status must not be authority"})
        if route.get("automatic_send_allowed") is not False:
            failures.append({"route_id": route_id, "reason": "automatic sending must be disabled"})
        if not route.get("evidence_refs"):
            failures.append({"route_id": route_id, "reason": "missing evidence refs"})
        if not route.get("receipt_refs"):
            failures.append({"route_id": route_id, "reason": "missing receipt refs"})
        if not route.get("validator_refs"):
            failures.append({"route_id": route_id, "reason": "missing validator refs"})
        decision = route.get("evaluator_decision", {})
        if decision.get("status") not in {"allow_private_review", "block"}:
            failures.append({"route_id": route_id, "reason": "decision status must be allow_private_review or block"})
        if decision.get("status_authority") != "recipient_route_gate_evaluator_only":
            failures.append({"route_id": route_id, "reason": "unexpected decision authority"})
        if decision.get("route_self_status_used_as_authority") is not False:
            failures.append({"route_id": route_id, "reason": "route self-status used as authority"})
        if decision.get("public_send_claimed") is not False:
            failures.append({"route_id": route_id, "reason": "decision must not claim public send"})
        if decision.get("auto_send_claimed") is not False:
            failures.append({"route_id": route_id, "reason": "decision must not claim automatic sending"})
        if decision.get("private_root_equivalence_claimed") is not False:
            failures.append({"route_id": route_id, "reason": "decision must not claim private-root equivalence"})
        if decision.get("status") == "block" and not decision.get("repair_row"):
            failures.append({"route_id": route_id, "reason": "blocked route missing repair row"})
        for ref in route.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"route_id": route_id, "missing_evidence_ref": ref})
        for ref in route.get("receipt_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"route_id": route_id, "missing_receipt_ref": ref})
        for validator_ref in route.get("validator_refs", []):
            if validator_ref not in validator_ids:
                failures.append({"route_id": route_id, "unknown_validator": validator_ref})

    graph_status = graph.get("status", {})
    graph_cases = graph.get("mechanism", {}).get("cases", [])
    if graph.get("schema_version") != "recipient_evidence_graph_v0":
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "unexpected graph schema"})
    if graph.get("microcosm_id") != "recipient_review_route_gate_microcosm":
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "unexpected graph microcosm id"})
    if graph.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "graph must declare projection_not_authority"})
    if not isinstance(graph_cases, list) or len(graph_cases) != len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "graph cases must match route count"})
        graph_cases = []
    for count_name in (
        "recipient_evidence_graph_case_count",
        "recipient_evidence_graph_source_capsule_count",
        "recipient_evidence_graph_semantic_carryforward_count",
        "recipient_evidence_graph_repair_route_count",
        "recipient_evidence_graph_teaching_rule_count",
    ):
        if int(summary.get(count_name, 0)) != len(routes):
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": count_name})
    if int(summary.get("recipient_evidence_graph_self_attestation_count", -1)) != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": "recipient_evidence_graph_self_attestation_count"})
    if int(summary.get("recipient_evidence_graph_evaluator_authority_count", 0)) != len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "recipient_evidence_graph_evaluator_authority_count"})
    if graph.get("authority", {}).get("self_attestation_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "graph self-attestation count must remain zero"})
    if graph.get("authority", {}).get("evaluator_authority_count") != len(graph_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "graph evaluator authority count must match cases"})
    for claim_count in (
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if graph.get("authority", {}).get(claim_count) != 0:
            failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "nonzero_authority_count": claim_count})
    if graph.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-recipient-review-route-gate-specimen --root . --write-receipt":
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "graph route must expose runnable builder command"})
    if graph_status.get("validation_status") != "ok" or graph_status.get("missing_ref_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "graph status must be valid with no missing refs"})
    if graph_status.get("case_count") != len(graph_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "graph case count mismatch"})
    source_shuttle_board = load_json(root / "microcosms" / "source_shuttle" / "source_shuttle_board.json")
    source_shuttle_cases = [
        case
        for case in source_shuttle_board.get("mechanism", {}).get("cases", [])
        if isinstance(case, dict)
    ]
    source_shuttle_status = source_shuttle_board.get("status", {})
    source_shuttle_case_count = int(source_shuttle_status.get("semantic_packet_count", len(source_shuttle_cases)))
    for count_name, expected_count in (
        ("source_shuttle_bridge_case_count", source_shuttle_case_count),
        ("source_shuttle_bridge_hash_count", int(source_shuttle_status.get("source_clip_hash_count", 0))),
        ("source_shuttle_bridge_semantic_packet_hash_count", int(source_shuttle_status.get("semantic_packet_hash_count", 0))),
        ("source_shuttle_bridge_reentry_prompt_count", int(source_shuttle_status.get("reentry_prompt_count", 0))),
    ):
        if int(summary.get(count_name, 0)) != expected_count:
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": count_name})
    if int(summary.get("source_shuttle_bridge_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": "source_shuttle_bridge_self_attestation_authority_count"})
    if int(summary.get("source_shuttle_bridge_public_release_claim_count", -1)) != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": "source_shuttle_bridge_public_release_claim_count"})
    if int(summary.get("recipient_evidence_graph_source_shuttle_bridge_count", 0)) != 1:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "recipient_evidence_graph_source_shuttle_bridge_count"})
    if int(summary.get("recipient_evidence_graph_source_shuttle_packet_hash_count", 0)) != source_shuttle_case_count:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": "recipient_evidence_graph_source_shuttle_packet_hash_count"})
    for case in graph_cases:
        case_id = case.get("case_id")
        route = next((row for row in routes if isinstance(row, dict) and row.get("route_id") == case_id), None)
        if route is None:
            failures.append({"case_id": case_id, "reason": "graph case missing matching route"})
            continue
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "graph case missing source clip"})
        else:
            observed_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
            if case.get("source_clip_hash") != observed_hash:
                failures.append({"case_id": case_id, "reason": "graph source clip hash mismatch"})
        if not case.get("recipient_question"):
            failures.append({"case_id": case_id, "reason": "graph case missing recipient question"})
        if case.get("semantic_carryforward", {}).get("self_attestation_used_as_authority") is not False:
            failures.append({"case_id": case_id, "reason": "graph case used self-attestation as authority"})
        if case.get("evaluator_or_validator") != "recipient_evidence_graph_evaluator":
            failures.append({"case_id": case_id, "reason": "unexpected graph evaluator"})
        if case.get("outcome") != route.get("evaluator_decision", {}).get("status"):
            failures.append({"case_id": case_id, "reason": "graph outcome does not match route decision"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "graph case missing repair route"})
        if case.get("restart_point") != "route_gate_row":
            failures.append({"case_id": case_id, "reason": "graph case missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "graph case missing teaching rule"})
        if not case.get("evidence_refs") or not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "graph case missing evidence refs or anti-claims"})
        flags = case.get("authority_flags", {})
        for flag_name in (
            "recipient_copy_is_authority",
            "route_self_status_is_authority",
            "self_attestation_authority",
            "automatic_send_allowed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if flags.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"graph case authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    source_shuttle_graph_case = next(
        (case for case in graph_cases if case.get("case_id") == "route.private_source_shuttle_packet_review"),
        None,
    )
    if not source_shuttle_graph_case:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "missing source-shuttle recipient evidence graph case"})
    else:
        shuttle_refs = source_shuttle_graph_case.get("source_shuttle_packet_refs", [])
        if len(shuttle_refs) != source_shuttle_case_count:
            failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "source-shuttle packet refs must match source shuttle case count"})
        carry = source_shuttle_graph_case.get("semantic_carryforward", {})
        if carry.get("source_shuttle_ref") != "microcosms/source_shuttle/source_shuttle_board.json":
            failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "source-shuttle graph case missing board ref"})
        if carry.get("source_shuttle_projection_not_authority") is not True:
            failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "source-shuttle graph case must declare projection_not_authority"})
        if carry.get("source_shuttle_packet_hash_preserved_count") != source_shuttle_case_count:
            failures.append({"path": "microcosms/recipient_review_route_gate/recipient_evidence_graph.json", "reason": "source-shuttle hash count mismatch"})

    bridge_status = bridge.get("status", {})
    bridge_cases = bridge.get("mechanism", {}).get("cases", [])
    if bridge.get("schema_version") != "recipient_source_shuttle_evidence_bridge_v0":
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "unexpected source-shuttle bridge schema"})
    if bridge.get("microcosm_id") != "recipient_review_route_gate_microcosm":
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "unexpected source-shuttle bridge microcosm id"})
    if bridge.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "source-shuttle bridge must declare projection_not_authority"})
    if not isinstance(bridge_cases, list) or len(bridge_cases) != source_shuttle_case_count:
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "source-shuttle bridge cases must match source shuttle case count"})
        bridge_cases = []
    for count_name in (
        "source_shuttle_evidence_bridge_case_count",
        "source_shuttle_evidence_bridge_source_capsule_count",
        "source_shuttle_evidence_bridge_semantic_packet_count",
        "source_shuttle_evidence_bridge_semantic_packet_hash_count",
        "source_shuttle_evidence_bridge_source_clip_hash_count",
        "source_shuttle_evidence_bridge_semantic_carryforward_count",
        "source_shuttle_evidence_bridge_reentry_prompt_count",
        "source_shuttle_evidence_bridge_loss_boundary_count",
        "source_shuttle_evidence_bridge_repair_route_count",
        "source_shuttle_evidence_bridge_teaching_rule_count",
    ):
        if int(summary.get(count_name, 0)) != len(bridge_cases):
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": count_name})
    if int(summary.get("source_shuttle_evidence_bridge_blocked_claim_count", 0)) < len(bridge_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "source_shuttle_evidence_bridge_blocked_claim_count"})
    if int(summary.get("source_shuttle_evidence_bridge_self_attestation_count", -1)) != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": "source_shuttle_evidence_bridge_self_attestation_count"})
    if int(summary.get("source_shuttle_evidence_bridge_evaluator_authority_count", 0)) != len(bridge_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "source_shuttle_evidence_bridge_evaluator_authority_count"})
    if bridge.get("authority", {}).get("self_attestation_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "source-shuttle bridge self-attestation count must remain zero"})
    if bridge.get("authority", {}).get("evaluator_authority_count") != len(bridge_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "source-shuttle bridge evaluator authority count must match cases"})
    for claim_count in (
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if bridge.get("authority", {}).get(claim_count) != 0:
            failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "nonzero_authority_count": claim_count})
    if bridge.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-recipient-review-route-gate-specimen --root . --write-receipt":
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "source-shuttle bridge route must expose runnable builder command"})
    if bridge_status.get("validation_status") != "ok" or bridge_status.get("missing_ref_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "reason": "source-shuttle bridge status must be valid with no missing refs"})
    for count_name in (
        "case_count",
        "source_capsule_count",
        "semantic_packet_count",
        "semantic_packet_hash_count",
        "source_clip_hash_count",
        "semantic_carryforward_count",
        "reentry_prompt_count",
        "loss_boundary_count",
        "repair_route_count",
        "teaching_rule_count",
        "claim_boundary_count",
    ):
        if bridge_status.get(count_name) != len(bridge_cases):
            failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json", "missing_or_mismatched_status_count": count_name})
    for case in bridge_cases:
        case_id = case.get("case_id")
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "source-shuttle bridge case missing source clip"})
        else:
            observed_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
            if case.get("source_clip_hash") != observed_hash:
                failures.append({"case_id": case_id, "reason": "source-shuttle bridge source clip hash mismatch"})
        if not case.get("semantic_packet_hash") or not case.get("semantic_packet_id"):
            failures.append({"case_id": case_id, "reason": "source-shuttle bridge case missing semantic packet id or hash"})
        carry = case.get("semantic_carryforward", {})
        for flag_name in (
            "private_source_copied",
            "private_field_rehydration_allowed",
            "self_attestation_used_as_authority",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if carry.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"source-shuttle bridge carryforward {flag_name} must be false"})
        if carry.get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "source-shuttle bridge carryforward must mark projection_not_authority"})
        if case.get("evaluator_or_validator") != "recipient_source_shuttle_bridge_evaluator":
            failures.append({"case_id": case_id, "reason": "unexpected source-shuttle bridge evaluator"})
        if case.get("outcome") != "accepted_private_review_evidence":
            failures.append({"case_id": case_id, "reason": "source-shuttle bridge outcome must be accepted private review evidence"})
        if not case.get("repair_route") or not case.get("restart_point") or not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "source-shuttle bridge case missing repair route, restart point, or teaching rule"})
        if not case.get("loss_boundary") or not case.get("no_private_copy_rule"):
            failures.append({"case_id": case_id, "reason": "source-shuttle bridge case missing loss boundary or no-private-copy rule"})
        if not case.get("evidence_refs") or not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "source-shuttle bridge case missing evidence refs or anti-claims"})
        flags = case.get("authority_flags", {})
        for flag_name in (
            "recipient_copy_is_authority",
            "route_self_status_is_authority",
            "self_attestation_authority",
            "automatic_send_allowed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
            "semantic_packet_used_as_source_authority",
            "private_field_rehydration_allowed",
        ):
            if flags.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"source-shuttle bridge authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if bridge_receipt.get("status") != "ok" or bridge_receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json", "reason": "source-shuttle bridge receipt must be ok with fixture_validated claim tier"})
    bridge_receipt_refs = set(bridge_receipt.get("evidence_refs", []))
    for required_ref in (
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
        "microcosms/source_shuttle/source_shuttle_board.json",
        "microcosms/source_shuttle/receipt.json",
        "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
        "src/idea_microcosm/recipient_review_route_gate_specimen.py",
        "src/idea_microcosm/validators.py",
    ):
        if required_ref not in bridge_receipt_refs:
            failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json", "missing_evidence_ref": required_ref})
    for ref in bridge_receipt_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json", "missing_evidence_ref": ref})

    packet_status = packet.get("status", {})
    packet_cases = packet.get("mechanism", {}).get("cases", [])
    if packet.get("schema_version") != "recipient_packet_omission_receipt_v0":
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "unexpected packet omission receipt schema"})
    if packet.get("microcosm_id") != "recipient_review_route_gate_microcosm":
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "unexpected packet omission receipt microcosm id"})
    if packet.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission receipt must declare projection_not_authority"})
    if not isinstance(packet_cases, list) or len(packet_cases) != len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission receipt cases must match route count"})
        packet_cases = []
    for count_name in (
        "recipient_packet_omission_case_count",
        "recipient_packet_omission_source_capsule_count",
        "recipient_packet_omission_semantic_carryforward_count",
        "recipient_packet_omission_repair_route_count",
        "recipient_packet_omission_teaching_rule_count",
    ):
        if int(summary.get(count_name, 0)) != len(routes):
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": count_name})
    if int(summary.get("recipient_packet_omission_omitted_private_field_count", 0)) < len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "recipient_packet_omission_omitted_private_field_count"})
    if int(summary.get("recipient_packet_omission_self_attestation_count", -1)) != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": "recipient_packet_omission_self_attestation_count"})
    if int(summary.get("recipient_packet_omission_evaluator_authority_count", 0)) != len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "recipient_packet_omission_evaluator_authority_count"})
    if int(summary.get("recipient_packet_omission_source_shuttle_bridge_count", 0)) != 1:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "recipient_packet_omission_source_shuttle_bridge_count"})
    for count_name in (
        "recipient_packet_omission_source_shuttle_packet_ref_count",
        "recipient_packet_omission_source_shuttle_packet_hash_count",
        "recipient_packet_omission_source_shuttle_source_clip_hash_count",
    ):
        if int(summary.get(count_name, 0)) != source_shuttle_case_count:
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": count_name})
    if int(summary.get("recipient_packet_omission_source_shuttle_private_field_rehydration_count", -1)) != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": "recipient_packet_omission_source_shuttle_private_field_rehydration_count"})
    if packet.get("authority", {}).get("self_attestation_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission self-attestation count must remain zero"})
    if packet.get("authority", {}).get("evaluator_authority_count") != len(packet_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission evaluator authority count must match cases"})
    for claim_count in (
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if packet.get("authority", {}).get(claim_count) != 0:
            failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "nonzero_authority_count": claim_count})
    if packet.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-recipient-review-route-gate-specimen --root . --write-receipt":
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission route must expose runnable builder command"})
    if packet_status.get("validation_status") != "ok" or packet_status.get("missing_ref_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission status must be valid with no missing refs"})
    if packet_status.get("case_count") != len(packet_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission case count mismatch"})
    if packet_status.get("omitted_private_field_count", 0) < len(packet_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission cases must declare omitted private fields"})
    if packet_status.get("source_shuttle_packet_omission_bridge_count") != 1:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission receipt must carry one source-shuttle bridge case"})
    for count_name in (
        "source_shuttle_packet_omission_ref_count",
        "source_shuttle_packet_hash_preserved_count",
        "source_shuttle_source_clip_hash_preserved_count",
    ):
        if packet_status.get(count_name) != source_shuttle_case_count:
            failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "missing_or_mismatched_status_count": count_name})
    if packet_status.get("source_shuttle_private_field_rehydration_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json", "reason": "packet omission source-shuttle refs must not rehydrate private fields"})
    for case in packet_cases:
        case_id = case.get("case_id")
        source_route_id = case.get("source_route_id")
        route = next((row for row in routes if isinstance(row, dict) and row.get("route_id") == source_route_id), None)
        if route is None:
            failures.append({"case_id": case_id, "reason": "packet omission case missing matching route"})
            continue
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "packet omission case missing source clip"})
        else:
            observed_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
            if case.get("source_clip_hash") != observed_hash:
                failures.append({"case_id": case_id, "reason": "packet omission source clip hash mismatch"})
        if not case.get("omitted_private_fields") or not case.get("disclosure_boundary"):
            failures.append({"case_id": case_id, "reason": "packet omission case missing omissions or disclosure boundary"})
        if case.get("semantic_carryforward", {}).get("self_attestation_used_as_authority") is not False:
            failures.append({"case_id": case_id, "reason": "packet omission case used self-attestation as authority"})
        if case.get("semantic_carryforward", {}).get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "packet omission case must mark projection_not_authority"})
        source_shuttle_refs = case.get("source_shuttle_packet_omission_refs", [])
        carry = case.get("semantic_carryforward", {})
        if route.get("candidate_id") == "source_shuttle_microcosm":
            if len(source_shuttle_refs) != source_shuttle_case_count:
                failures.append({"case_id": case_id, "reason": "packet omission source-shuttle refs must match source shuttle case count"})
            if carry.get("source_shuttle_evidence_bridge_ref") != "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json":
                failures.append({"case_id": case_id, "reason": "packet omission source-shuttle carryforward missing bridge ref"})
            if carry.get("source_shuttle_evidence_bridge_receipt_ref") != "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json":
                failures.append({"case_id": case_id, "reason": "packet omission source-shuttle carryforward missing bridge receipt ref"})
            for count_name in (
                "source_shuttle_packet_omission_ref_count",
                "source_shuttle_packet_hash_preserved_count",
                "source_shuttle_source_clip_hash_preserved_count",
                "source_shuttle_no_private_copy_rule_count",
            ):
                if carry.get(count_name) != source_shuttle_case_count:
                    failures.append({"case_id": case_id, "reason": f"packet omission carryforward {count_name} mismatch"})
            if carry.get("source_shuttle_private_field_rehydration_allowed") is not False:
                failures.append({"case_id": case_id, "reason": "packet omission cannot rehydrate source-shuttle private fields"})
            if carry.get("source_shuttle_semantic_packet_used_as_source_authority") is not False:
                failures.append({"case_id": case_id, "reason": "packet omission cannot treat source-shuttle semantic packets as source authority"})
            evidence_refs = set(case.get("evidence_refs", []))
            for required_ref in (
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
            ):
                if required_ref not in evidence_refs:
                    failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})
            for ref in source_shuttle_refs:
                if not ref.get("bridge_case_id") or not ref.get("source_shuttle_case_id"):
                    failures.append({"case_id": case_id, "reason": "packet omission source-shuttle ref missing bridge or source case id"})
                if not ref.get("semantic_packet_id") or not ref.get("semantic_packet_hash"):
                    failures.append({"case_id": case_id, "reason": "packet omission source-shuttle ref missing packet id or hash"})
                if not ref.get("source_clip_hash"):
                    failures.append({"case_id": case_id, "reason": "packet omission source-shuttle ref missing source clip hash"})
                if not ref.get("loss_boundary") or not ref.get("no_private_copy_rule"):
                    failures.append({"case_id": case_id, "reason": "packet omission source-shuttle ref missing loss boundary or no-private-copy rule"})
                if not ref.get("repair_route") or not ref.get("restart_point") or not ref.get("anti_claims"):
                    failures.append({"case_id": case_id, "reason": "packet omission source-shuttle ref missing repair route, restart point, or anti-claims"})
        elif source_shuttle_refs:
            failures.append({"case_id": case_id, "reason": "packet omission source-shuttle refs attached to non-source-shuttle route"})
        if case.get("evaluator_or_validator") != "recipient_packet_omission_receipt_evaluator":
            failures.append({"case_id": case_id, "reason": "unexpected packet omission evaluator"})
        if case.get("outcome") != route.get("evaluator_decision", {}).get("status"):
            failures.append({"case_id": case_id, "reason": "packet omission outcome does not match route decision"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "packet omission case missing repair route"})
        if case.get("restart_point") != "redacted_packet_section":
            failures.append({"case_id": case_id, "reason": "packet omission case missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "packet omission case missing teaching rule"})
        if not case.get("evidence_refs") or not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "packet omission case missing evidence refs or anti-claims"})
        flags = case.get("authority_flags", {})
        for flag_name in (
            "recipient_copy_is_authority",
            "route_self_status_is_authority",
            "self_attestation_authority",
            "automatic_send_allowed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
            "source_shuttle_private_field_rehydration_allowed",
            "source_shuttle_semantic_packet_used_as_source_authority",
        ):
            if flags.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"packet omission authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    draft_status = draft.get("status", {})
    draft_cases = draft.get("mechanism", {}).get("cases", [])
    if draft.get("schema_version") != "redacted_recipient_packet_draft_v0":
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "unexpected redacted packet draft schema"})
    if draft.get("microcosm_id") != "recipient_review_route_gate_microcosm":
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "unexpected redacted packet draft microcosm id"})
    if draft.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted packet draft must declare projection_not_authority"})
    if not isinstance(draft_cases, list) or len(draft_cases) != len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted packet draft cases must match route count"})
        draft_cases = []
    for count_name in (
        "redacted_recipient_packet_draft_case_count",
        "redacted_recipient_packet_draft_source_capsule_count",
        "redacted_recipient_packet_draft_semantic_carryforward_count",
        "redacted_recipient_packet_draft_repair_route_count",
        "redacted_recipient_packet_draft_teaching_rule_count",
    ):
        if int(summary.get(count_name, 0)) != len(routes):
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": count_name})
    for count_name in (
        "redacted_recipient_packet_draft_self_attestation_count",
        "redacted_recipient_packet_draft_send_action_count",
        "redacted_recipient_packet_draft_recipient_identity_count",
        "redacted_recipient_packet_draft_private_field_rehydration_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": count_name})
    if int(summary.get("redacted_recipient_packet_draft_evaluator_authority_count", 0)) != len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "redacted_recipient_packet_draft_evaluator_authority_count"})
    if int(summary.get("redacted_recipient_packet_draft_omitted_private_field_count", 0)) < len(routes):
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "redacted_recipient_packet_draft_omitted_private_field_count"})
    if int(summary.get("redacted_recipient_packet_draft_source_shuttle_bridge_count", 0)) != 1:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_summary_count": "redacted_recipient_packet_draft_source_shuttle_bridge_count"})
    for count_name in (
        "redacted_recipient_packet_draft_source_shuttle_packet_ref_count",
        "redacted_recipient_packet_draft_source_shuttle_packet_hash_count",
        "redacted_recipient_packet_draft_source_shuttle_source_clip_hash_count",
    ):
        if int(summary.get(count_name, 0)) != source_shuttle_case_count:
            failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "missing_or_mismatched_summary_count": count_name})
    if int(summary.get("redacted_recipient_packet_draft_source_shuttle_private_field_rehydration_count", -1)) != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/route_gate.json", "nonzero_summary_count": "redacted_recipient_packet_draft_source_shuttle_private_field_rehydration_count"})
    if draft.get("authority", {}).get("self_attestation_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted packet draft self-attestation count must remain zero"})
    if draft.get("authority", {}).get("evaluator_authority_count") != len(draft_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted packet draft evaluator authority count must match cases"})
    for claim_count in (
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
        "send_action_count",
        "recipient_identity_count",
        "private_field_rehydration_count",
    ):
        if draft.get("authority", {}).get(claim_count) != 0:
            failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "nonzero_authority_count": claim_count})
    if draft.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-recipient-review-route-gate-specimen --root . --write-receipt":
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted packet draft route must expose runnable builder command"})
    if draft_status.get("validation_status") != "ok" or draft_status.get("missing_ref_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted packet draft status must be valid with no missing refs"})
    if draft_status.get("case_count") != len(draft_cases):
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted packet draft case count mismatch"})
    for count_name in (
        "recipient_identity_count",
        "send_destination_count",
        "send_action_count",
        "private_field_rehydration_count",
    ):
        if draft_status.get(count_name) != 0:
            failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "nonzero_status_count": count_name})
    if draft_status.get("source_shuttle_redacted_packet_bridge_count") != 1:
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted draft must carry one source-shuttle bridge case"})
    for count_name in (
        "source_shuttle_redacted_packet_ref_count",
        "source_shuttle_packet_hash_preserved_count",
        "source_shuttle_source_clip_hash_preserved_count",
        "source_shuttle_no_private_copy_rule_count",
    ):
        if draft_status.get(count_name) != source_shuttle_case_count:
            failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "missing_or_mismatched_status_count": count_name})
    if draft_status.get("source_shuttle_private_field_rehydration_count") != 0:
        failures.append({"path": "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json", "reason": "redacted draft source-shuttle refs must not rehydrate private fields"})
    for case in draft_cases:
        case_id = case.get("case_id")
        source_route_id = case.get("source_route_id")
        route = next((row for row in routes if isinstance(row, dict) and row.get("route_id") == source_route_id), None)
        if route is None:
            failures.append({"case_id": case_id, "reason": "redacted draft case missing matching route"})
            continue
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "redacted draft case missing source clip"})
        else:
            observed_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
            if case.get("source_clip_hash") != observed_hash:
                failures.append({"case_id": case_id, "reason": "redacted draft source clip hash mismatch"})
        section = case.get("redacted_packet_section", {})
        if not section.get("draft_text") or not section.get("omitted_private_fields"):
            failures.append({"case_id": case_id, "reason": "redacted draft case missing draft text or omissions"})
        for flag_name in (
            "private_field_rehydration_allowed",
            "source_shuttle_private_field_rehydration_allowed",
            "source_shuttle_semantic_packet_used_as_source_authority",
            "send_action_allowed",
            "recipient_identity_present",
        ):
            if section.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"redacted draft section {flag_name} must be false"})
        carry = case.get("semantic_carryforward", {})
        for flag_name in (
            "self_attestation_used_as_authority",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
            "recipient_identity_present",
            "send_destination_present",
            "send_action_present",
            "private_field_rehydration_allowed",
            "source_shuttle_private_field_rehydration_allowed",
            "source_shuttle_semantic_packet_used_as_source_authority",
        ):
            if carry.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"redacted draft carryforward {flag_name} must be false"})
        source_shuttle_refs = case.get("source_shuttle_redacted_packet_refs", [])
        if route.get("candidate_id") == "source_shuttle_microcosm":
            if len(source_shuttle_refs) != source_shuttle_case_count:
                failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle refs must match source shuttle case count"})
            if carry.get("source_shuttle_packet_omission_receipt_ref") != "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json":
                failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle carryforward missing omission receipt ref"})
            for count_name in (
                "source_shuttle_redacted_packet_ref_count",
                "source_shuttle_packet_hash_preserved_count",
                "source_shuttle_source_clip_hash_preserved_count",
                "source_shuttle_no_private_copy_rule_count",
            ):
                if carry.get(count_name) != source_shuttle_case_count:
                    failures.append({"case_id": case_id, "reason": f"redacted draft carryforward {count_name} mismatch"})
            if section.get("source_shuttle_packet_omission_ref_count") != source_shuttle_case_count:
                failures.append({"case_id": case_id, "reason": "redacted draft section source-shuttle ref count mismatch"})
            if len(section.get("source_shuttle_packet_hashes", [])) != source_shuttle_case_count:
                failures.append({"case_id": case_id, "reason": "redacted draft section source-shuttle packet hashes mismatch"})
            if len(section.get("source_shuttle_source_clip_hashes", [])) != source_shuttle_case_count:
                failures.append({"case_id": case_id, "reason": "redacted draft section source-shuttle source clip hashes mismatch"})
            evidence_refs = set(case.get("evidence_refs", []))
            for required_ref in (
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
            ):
                if required_ref not in evidence_refs:
                    failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})
            for ref in source_shuttle_refs:
                if not ref.get("bridge_case_id") or not ref.get("source_shuttle_case_id"):
                    failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle ref missing bridge or source case id"})
                if not ref.get("semantic_packet_id") or not ref.get("semantic_packet_hash"):
                    failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle ref missing packet id or hash"})
                if not ref.get("source_clip_hash"):
                    failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle ref missing source clip hash"})
                if not ref.get("loss_boundary") or not ref.get("no_private_copy_rule"):
                    failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle ref missing loss boundary or no-private-copy rule"})
                if not ref.get("repair_route") or not ref.get("restart_point") or not ref.get("anti_claims"):
                    failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle ref missing repair route, restart point, or anti-claims"})
        elif source_shuttle_refs:
            failures.append({"case_id": case_id, "reason": "redacted draft source-shuttle refs attached to non-source-shuttle route"})
        if carry.get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "redacted draft case must mark projection_not_authority"})
        if case.get("evaluator_or_validator") != "redacted_recipient_packet_draft_evaluator":
            failures.append({"case_id": case_id, "reason": "unexpected redacted draft evaluator"})
        if case.get("outcome") != route.get("evaluator_decision", {}).get("status"):
            failures.append({"case_id": case_id, "reason": "redacted draft outcome does not match route decision"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "redacted draft case missing repair route"})
        if case.get("restart_point") != "recipient_packet_omission_receipt_case":
            failures.append({"case_id": case_id, "reason": "redacted draft case missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "redacted draft case missing teaching rule"})
        if not case.get("evidence_refs") or not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "redacted draft case missing evidence refs or anti-claims"})
        flags = case.get("authority_flags", {})
        for flag_name in (
            "recipient_copy_is_authority",
            "route_self_status_is_authority",
            "self_attestation_authority",
            "automatic_send_allowed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
            "recipient_identity_present",
            "send_destination_present",
            "send_action_present",
            "private_field_rehydration_allowed",
            "source_shuttle_private_field_rehydration_allowed",
            "source_shuttle_semantic_packet_used_as_source_authority",
        ):
            if flags.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"redacted draft authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/recipient_review_route_gate/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/recipient_review_route_gate/route_gate.json",
        "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
        "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json",
        "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
        "microcosms/recipient_review_route_gate/README.md",
        "microcosms/source_shuttle/source_shuttle_board.json",
        "microcosms/source_shuttle/receipt.json",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/recipient_review_route_gate_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "microcosms/thiel_evidence_packet_gate/evidence_packet.json",
        "microcosms/thiel_evidence_packet_gate/receipt.json",
        "microcosms/website_card_projection_gate/receipt.json",
        "microcosms/demo_receipt_storyboard/receipt.json",
        "microcosms/release_standards_axiom_gate/receipt.json",
        "microcosms/atlas_navigation_bands/receipt.json",
        "receipts/release_candidate_portfolio.json",
        "receipts/cold_sandbox_probe_latest.json",
        "release/publication_gate.json",
        "LICENSE",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/recipient_review_route_gate/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/recipient_review_route_gate/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-recipient-review-route-gate-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "recipient_evidence_graph.json",
        "recipient_packet_omission_receipt.json",
        "redacted_recipient_packet_draft.json",
        "source_shuttle_evidence_bridge.json",
        "not an outreach authority",
        "no automatic sending",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/recipient_review_route_gate/README.md", "missing_text": required_text})
    return failures


def _license_citation_disclosure_gate_failures(root: Path) -> list[dict[str, Any]]:
    gate_path = root / "microcosms" / "license_citation_disclosure_gate" / "clearance_gate.json"
    receipt_path = root / "microcosms" / "license_citation_disclosure_gate" / "receipt.json"
    readme_path = root / "microcosms" / "license_citation_disclosure_gate" / "README.md"
    failures: list[dict[str, Any]] = []
    if not gate_path.exists():
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "missing clearance gate"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/license_citation_disclosure_gate/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/license_citation_disclosure_gate/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    gate = load_json(gate_path)
    receipt = load_json(receipt_path)
    if gate.get("specimen_id") != "license_citation_disclosure_gate_microcosm":
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "unexpected specimen_id"})
    if gate.get("authority_posture") != "public_safe_license_citation_disclosure_gate_not_publication_or_rights_authority":
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "unexpected authority posture"})
    if gate.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(gate).lower():
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "clearance gate must not imply public release readiness"})

    summary = gate.get("summary", {})
    rows = gate.get("clearance_rows", [])
    if not isinstance(rows, list) or len(rows) < 8:
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "expected at least eight clearance rows"})
        rows = []
    if int(summary.get("clearance_row_count", 0)) != len(rows):
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "summary clearance_row_count mismatch"})
    if int(summary.get("allow_private_review_count", 0)) < 2:
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "missing_summary_count": "allow_private_review_count"})
    if int(summary.get("block_count", 0)) < 6:
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "missing_summary_count": "block_count"})
    for count_name in (
        "selected_license_public_grant_block_count",
        "citation_gap_block_count",
        "disclosure_gap_block_count",
        "hosted_public_ci_gap_block_count",
        "probe_or_clone_claim_block_count",
        "publication_gate_fail_closed_block_count",
        "private_root_equivalence_block_count",
    ):
        if int(summary.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "missing_summary_count": count_name})
    if int(summary.get("receipt_ref_count", 0)) < len(rows):
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("validator_ref_count", 0)) < len(rows):
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "missing_summary_count": "validator_ref_count"})
    for count_name in (
        "public_release_claim_count",
        "active_public_grant_claim_count",
        "citation_clearance_claim_count",
        "disclosure_clearance_claim_count",
        "hosted_public_status_claim_count",
        "gate_self_authority_count",
        "claim_copy_authority_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "nonzero_summary_count": count_name})
    if summary.get("status_authority_nodes") != [
        "license_citation_disclosure_gate_evaluator",
        "rights_posture_gate",
        "receipt_gate",
        "publication_gate",
        "recipient_route_gate",
    ]:
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "status authority nodes mismatch"})
    if gate.get("license_citation_disclosure_gate", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "clearance gate must stay fail-closed"})
    publication_snapshot = gate.get("publication_gate_snapshot", {})
    if publication_snapshot.get("status") != "fail_closed":
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "publication gate snapshot must be fail-closed"})
    if publication_snapshot.get("rights_license_grant_status") != "Apache-2.0_selected_pending_public_toggle":
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "license grant status must stay pending public toggle"})

    required_failure_classes = {
        "selected_license_as_public_grant",
        "citation_review_missing",
        "disclosure_boundary_missing",
        "hosted_public_ci_missing",
        "stale_probe_or_clone_receipt",
        "publication_gate_fail_closed",
        "private_root_equivalence_overclaim",
    }
    observed_failure_classes = {
        row.get("evaluator_decision", {}).get("failure_class")
        for row in rows
        if isinstance(row, dict) and row.get("evaluator_decision", {}).get("failure_class")
    }
    missing_failure_classes = sorted(required_failure_classes - observed_failure_classes)
    if missing_failure_classes:
        failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "missing_failure_classes": missing_failure_classes})

    validator_ids = {row.get("id") for row in load_json(root / "registry" / "validators.json").get("rows", []) if isinstance(row, dict)}
    for row in rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/license_citation_disclosure_gate/clearance_gate.json", "reason": "clearance row must be an object"})
            continue
        clearance_id = row.get("clearance_id")
        if row.get("claim_copy_is_authority") is not False:
            failures.append({"clearance_id": clearance_id, "reason": "claim copy must not be authority"})
        if row.get("gate_self_status_is_authority") is not False:
            failures.append({"clearance_id": clearance_id, "reason": "gate self-status must not be authority"})
        if row.get("automatic_publication_allowed") is not False:
            failures.append({"clearance_id": clearance_id, "reason": "automatic publication must be disabled"})
        if not row.get("evidence_refs"):
            failures.append({"clearance_id": clearance_id, "reason": "missing evidence refs"})
        if not row.get("receipt_refs"):
            failures.append({"clearance_id": clearance_id, "reason": "missing receipt refs"})
        if not row.get("validator_refs"):
            failures.append({"clearance_id": clearance_id, "reason": "missing validator refs"})
        decision = row.get("evaluator_decision", {})
        if decision.get("status") not in {"allow_private_review", "block"}:
            failures.append({"clearance_id": clearance_id, "reason": "decision status must be allow_private_review or block"})
        if decision.get("status_authority") != "license_citation_disclosure_gate_evaluator_only":
            failures.append({"clearance_id": clearance_id, "reason": "unexpected decision authority"})
        for claim_flag in (
            "claim_copy_used_as_authority",
            "gate_self_status_used_as_authority",
            "public_release_claimed",
            "active_public_grant_claimed",
            "citation_clearance_claimed",
            "disclosure_clearance_claimed",
            "hosted_public_status_claimed",
            "private_root_equivalence_claimed",
        ):
            if decision.get(claim_flag) is not False:
                failures.append({"clearance_id": clearance_id, "reason": f"decision {claim_flag} must be false"})
        if decision.get("status") == "block" and not decision.get("repair_row"):
            failures.append({"clearance_id": clearance_id, "reason": "blocked clearance row missing repair row"})
        for ref in row.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"clearance_id": clearance_id, "missing_evidence_ref": ref})
        for ref in row.get("receipt_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"clearance_id": clearance_id, "missing_receipt_ref": ref})
        for validator_ref in row.get("validator_refs", []):
            if validator_ref not in validator_ids:
                failures.append({"clearance_id": clearance_id, "unknown_validator": validator_ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/license_citation_disclosure_gate/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/license_citation_disclosure_gate/clearance_gate.json",
        "microcosms/license_citation_disclosure_gate/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/license_citation_disclosure_gate_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "microcosms/recipient_review_route_gate/route_gate.json",
        "microcosms/recipient_review_route_gate/receipt.json",
        "receipts/release_candidate_portfolio.json",
        "receipts/cold_sandbox_probe_latest.json",
        "receipts/validation_run.json",
        "release/publication_gate.json",
        "RELEASE_SCOPE.md",
        "LICENSE",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/license_citation_disclosure_gate/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/license_citation_disclosure_gate/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-license-citation-disclosure-gate-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "not a publication authority",
        "active public grant",
        "citation clearance",
        "disclosure clearance",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/license_citation_disclosure_gate/README.md", "missing_text": required_text})
    return failures


def _hosted_public_ci_workflow_gate_failures(root: Path) -> list[dict[str, Any]]:
    gate_path = root / "microcosms" / "hosted_public_ci_workflow_gate" / "workflow_gate.json"
    replay_path = root / "microcosms" / "hosted_public_ci_workflow_gate" / "hosted_claim_replay.json"
    receipt_path = root / "microcosms" / "hosted_public_ci_workflow_gate" / "receipt.json"
    readme_path = root / "microcosms" / "hosted_public_ci_workflow_gate" / "README.md"
    failures: list[dict[str, Any]] = []
    if not gate_path.exists():
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "missing workflow gate"})
    if not replay_path.exists():
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing hosted claim replay"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    gate = load_json(gate_path)
    replay = load_json(replay_path)
    receipt = load_json(receipt_path)
    if gate.get("specimen_id") != "hosted_public_ci_workflow_gate_microcosm":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "unexpected specimen_id"})
    if gate.get("authority_posture") != "public_safe_hosted_public_ci_workflow_gate_not_remote_or_publication_authority":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "unexpected authority posture"})
    if gate.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(gate).lower():
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "workflow gate must not imply public release readiness"})

    summary = gate.get("summary", {})
    rows = gate.get("workflow_rows", [])
    if not isinstance(rows, list) or len(rows) < 14:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "expected at least fourteen workflow rows"})
        rows = []
    if int(summary.get("workflow_row_count", 0)) != len(rows):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "summary workflow_row_count mismatch"})
    if int(summary.get("allow_private_review_count", 0)) < 2:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "allow_private_review_count"})
    if int(summary.get("block_count", 0)) < 7:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "block_count"})
    for count_name in (
        "public_remote_missing_block_count",
        "hosted_public_remote_receipt_missing_block_count",
        "deployment_receipt_missing_block_count",
        "hosted_ci_workflow_missing_block_count",
        "publication_toggle_not_green_block_count",
        "pages_or_site_not_authorized_block_count",
        "local_receipt_overclaim_block_count",
        "external_public_clone_probe_missing_block_count",
        "hosted_workflow_run_receipt_missing_block_count",
        "hosted_workflow_artifact_attestation_missing_block_count",
        "private_repo_visibility_not_public_block_count",
        "public_release_gate_fail_closed_block_count",
    ):
        if int(summary.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": count_name})
    if int(summary.get("receipt_ref_count", 0)) < len(rows):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("validator_ref_count", 0)) < len(rows):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "validator_ref_count"})
    for count_name in (
        "public_remote_clone_claim_count",
        "hosted_public_remote_receipt_claim_count",
        "deployment_receipt_claim_count",
        "external_public_clone_probe_claim_count",
        "hosted_workflow_run_receipt_claim_count",
        "hosted_workflow_artifact_attestation_claim_count",
        "unauthenticated_external_clone_claim_count",
        "hosted_ci_claim_count",
        "github_export_claim_count",
        "public_deployment_claim_count",
        "pages_or_public_site_claim_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_repo_public_proof_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
        "local_receipt_remote_proof_claim_count",
        "workflow_gate_self_authority_count",
        "claim_copy_authority_count",
        "hosted_ci_workflow_present_count",
        "hosted_claim_replay_self_attestation_authority_count",
        "artifact_digest_hosted_claim_replay_self_attestation_authority_count",
        "source_shuttle_site_projection_hosted_claim_replay_self_attestation_authority_count",
        "source_shuttle_site_projection_hosted_claim_replay_private_field_rehydration_count",
        "source_shuttle_site_projection_hosted_claim_replay_hosted_public_authority_count",
        "source_shuttle_site_projection_hosted_claim_replay_public_launch_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_public_release_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_publication_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_private_root_equivalence_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_benchmark_win_claim_count",
        "grammar_replay_site_projection_hosted_claim_replay_self_attestation_authority_count",
        "grammar_replay_site_projection_hosted_claim_replay_public_release_claim_count",
        "grammar_replay_site_projection_hosted_claim_replay_publication_claim_count",
        "grammar_replay_site_projection_hosted_claim_replay_private_root_equivalence_claim_count",
        "grammar_replay_site_projection_hosted_claim_replay_benchmark_win_claim_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "nonzero_summary_count": count_name})
    for count_name in (
        "hosted_claim_replay_case_count",
        "hosted_claim_replay_source_capsule_count",
        "hosted_claim_replay_semantic_carryforward_count",
        "hosted_claim_replay_repair_route_count",
        "hosted_claim_replay_teaching_rule_count",
        "hosted_claim_replay_blocked_claim_count",
        "hosted_claim_replay_site_projection_case_count",
        "external_public_clone_probe_gate_case_count",
        "hosted_workflow_run_receipt_gate_case_count",
        "hosted_workflow_artifact_attestation_gate_case_count",
        "artifact_digest_hosted_claim_replay_case_count",
        "artifact_digest_hosted_claim_replay_blocked_claim_count",
        "artifact_digest_hosted_claim_replay_source_witness_hash_preserved_count",
        "artifact_digest_hosted_claim_replay_package_row_attachment_count",
        "source_shuttle_site_projection_hosted_claim_replay_case_count",
        "source_shuttle_site_projection_hosted_claim_replay_source_capsule_count",
        "source_shuttle_site_projection_hosted_claim_replay_semantic_carryforward_count",
        "source_shuttle_site_projection_hosted_claim_replay_repair_route_count",
        "source_shuttle_site_projection_hosted_claim_replay_teaching_rule_count",
        "source_shuttle_site_projection_hosted_claim_replay_blocked_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_hash_verified_count",
        "source_shuttle_site_projection_hosted_claim_replay_manifest_ref_count",
        "source_shuttle_site_projection_hosted_claim_replay_packet_hash_preserved_count",
        "source_shuttle_site_projection_hosted_claim_replay_source_clip_hash_preserved_count",
        "source_shuttle_site_projection_hosted_claim_replay_no_private_copy_rule_count",
        "grammar_replay_site_projection_hosted_claim_replay_case_count",
        "grammar_replay_site_projection_hosted_claim_replay_source_capsule_count",
        "grammar_replay_site_projection_hosted_claim_replay_semantic_carryforward_count",
        "grammar_replay_site_projection_hosted_claim_replay_failure_replay_count",
        "grammar_replay_site_projection_hosted_claim_replay_repair_route_count",
        "grammar_replay_site_projection_hosted_claim_replay_teaching_rule_count",
        "grammar_replay_site_projection_hosted_claim_replay_hash_verified_count",
        "grammar_replay_site_projection_hosted_claim_replay_blocked_claim_count",
        "hosted_public_remote_receipt_gate_case_count",
        "deployment_receipt_gate_case_count",
    ):
        if int(summary.get(count_name, 0)) < 5:
            if count_name == "hosted_claim_replay_site_projection_case_count":
                minimum = 1
            elif count_name in {
                "hosted_workflow_run_receipt_gate_case_count",
                "hosted_workflow_artifact_attestation_gate_case_count",
            }:
                minimum = 4
            elif count_name in {
                "external_public_clone_probe_gate_case_count",
                "hosted_public_remote_receipt_gate_case_count",
                "deployment_receipt_gate_case_count",
                "artifact_digest_hosted_claim_replay_case_count",
                "source_shuttle_site_projection_hosted_claim_replay_case_count",
                "source_shuttle_site_projection_hosted_claim_replay_source_capsule_count",
                "source_shuttle_site_projection_hosted_claim_replay_semantic_carryforward_count",
                "source_shuttle_site_projection_hosted_claim_replay_repair_route_count",
                "source_shuttle_site_projection_hosted_claim_replay_teaching_rule_count",
                "source_shuttle_site_projection_hosted_claim_replay_hash_verified_count",
            }:
                minimum = 3
            elif count_name in {
                "artifact_digest_hosted_claim_replay_source_witness_hash_preserved_count",
                "artifact_digest_hosted_claim_replay_package_row_attachment_count",
            }:
                minimum = 1
            elif count_name in {
                "source_shuttle_site_projection_hosted_claim_replay_manifest_ref_count",
                "source_shuttle_site_projection_hosted_claim_replay_packet_hash_preserved_count",
                "source_shuttle_site_projection_hosted_claim_replay_source_clip_hash_preserved_count",
                "source_shuttle_site_projection_hosted_claim_replay_no_private_copy_rule_count",
            }:
                minimum = 6
            else:
                minimum = 5
            if int(summary.get(count_name, 0)) < minimum:
                failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": count_name})
    if int(summary.get("external_public_clone_probe_required_field_count", 0)) < 10:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "external_public_clone_probe_required_field_count"})
    if summary.get("external_public_clone_probe_missing_field_count") != summary.get("external_public_clone_probe_required_field_count"):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "external public clone probe missing fields must match required fields in fail-closed fixture"})
    if int(summary.get("hosted_workflow_run_receipt_required_field_count", 0)) < 10:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "hosted_workflow_run_receipt_required_field_count"})
    if summary.get("hosted_workflow_run_receipt_missing_field_count") != summary.get("hosted_workflow_run_receipt_required_field_count"):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "hosted workflow run receipt missing fields must match required fields in fail-closed fixture"})
    if int(summary.get("hosted_workflow_artifact_attestation_required_field_count", 0)) < 10:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "hosted_workflow_artifact_attestation_required_field_count"})
    if summary.get("hosted_workflow_artifact_attestation_missing_field_count") != summary.get("hosted_workflow_artifact_attestation_required_field_count"):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "hosted workflow artifact attestation missing fields must match required fields in fail-closed fixture"})
    if int(summary.get("remote_receipt_required_field_count", 0)) < 6:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "remote_receipt_required_field_count"})
    if summary.get("remote_receipt_missing_field_count") != summary.get("remote_receipt_required_field_count"):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "remote receipt missing fields must match required fields in fail-closed fixture"})
    if int(summary.get("deployment_receipt_required_field_count", 0)) < 8:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "deployment_receipt_required_field_count"})
    if summary.get("deployment_receipt_missing_field_count") != summary.get("deployment_receipt_required_field_count"):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "deployment receipt missing fields must match required fields in fail-closed fixture"})
    if int(summary.get("hosted_claim_replay_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "hosted claim replay must have zero missing refs"})
    if int(summary.get("release_artifact_integrity_witness_hosted_claim_replay_case_count", 0)) < 5:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_summary_count": "release_artifact_integrity_witness_hosted_claim_replay_case_count"})
    if int(summary.get("release_artifact_integrity_witness_hosted_claim_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "nonzero_summary_count": "release_artifact_integrity_witness_hosted_claim_self_attestation_authority_count"})
    if gate.get("hosted_claim_replay_ref") != "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "missing hosted claim replay ref"})
    if gate.get("hosted_claim_replay_summary", {}).get("case_count") != summary.get("hosted_claim_replay_case_count"):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "hosted claim replay summary mismatch"})
    if summary.get("status_authority_nodes") != [
        "hosted_public_ci_workflow_gate_evaluator",
        "external_public_clone_probe_gate",
        "hosted_workflow_run_receipt_gate",
        "hosted_workflow_artifact_attestation_gate",
        "release_artifact_integrity_witness_hosted_claim_gate",
        "grammar_replay_site_projection_hosted_claim_gate",
        "artifact_digest_site_projection_hosted_claim_replay_gate",
        "source_shuttle_site_projection_hosted_claim_gate",
        "hosted_public_remote_receipt_gate",
        "deployment_receipt_gate",
        "receipt_gate",
        "publication_gate",
        "local_clone_gate",
        "license_citation_disclosure_gate",
    ]:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "status authority nodes mismatch"})
    if gate.get("hosted_public_ci_workflow_gate", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "hosted workflow gate must stay fail-closed"})
    publication_snapshot = gate.get("publication_gate_snapshot", {})
    if publication_snapshot.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "publication gate snapshot must be fail-closed"})
    if publication_snapshot.get("rights_license_grant_status") != "Apache-2.0_selected_pending_public_toggle":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "license grant status must stay pending public toggle"})
    workflow_inventory = gate.get("workflow_inventory", {})
    if workflow_inventory.get("hosted_ci_workflow_present") is not False or int(workflow_inventory.get("workflow_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "hosted workflow inventory must remain absent for fail-closed fixture"})

    required_failure_classes = {
        "public_remote_missing",
        "hosted_public_remote_receipt_missing",
        "deployment_receipt_missing",
        "hosted_ci_workflow_missing",
        "publication_toggle_not_green",
        "pages_or_site_not_authorized",
        "local_receipt_overclaim",
        "external_public_clone_probe_missing",
        "hosted_workflow_run_receipt_missing",
        "hosted_workflow_artifact_attestation_missing",
        "private_repo_visibility_not_public",
        "public_release_gate_fail_closed",
    }
    observed_failure_classes = {
        row.get("evaluator_decision", {}).get("failure_class")
        for row in rows
        if isinstance(row, dict) and row.get("evaluator_decision", {}).get("failure_class")
    }
    missing_failure_classes = sorted(required_failure_classes - observed_failure_classes)
    if missing_failure_classes:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "missing_failure_classes": missing_failure_classes})

    validator_ids = {row.get("id") for row in load_json(root / "registry" / "validators.json").get("rows", []) if isinstance(row, dict)}
    for row in rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "reason": "workflow row must be an object"})
            continue
        workflow_id = row.get("workflow_id")
        if row.get("claim_copy_is_authority") is not False:
            failures.append({"workflow_id": workflow_id, "reason": "claim copy must not be authority"})
        if row.get("workflow_gate_self_status_is_authority") is not False:
            failures.append({"workflow_id": workflow_id, "reason": "workflow gate self-status must not be authority"})
        if row.get("automatic_publication_allowed") is not False:
            failures.append({"workflow_id": workflow_id, "reason": "automatic publication must be disabled"})
        if not row.get("evidence_refs"):
            failures.append({"workflow_id": workflow_id, "reason": "missing evidence refs"})
        if not row.get("receipt_refs"):
            failures.append({"workflow_id": workflow_id, "reason": "missing receipt refs"})
        if not row.get("validator_refs"):
            failures.append({"workflow_id": workflow_id, "reason": "missing validator refs"})
        decision = row.get("evaluator_decision", {})
        if decision.get("status") not in {"allow_private_review", "block"}:
            failures.append({"workflow_id": workflow_id, "reason": "decision status must be allow_private_review or block"})
        if decision.get("status_authority") != "hosted_public_ci_workflow_gate_evaluator_only":
            failures.append({"workflow_id": workflow_id, "reason": "unexpected decision authority"})
        for claim_flag in (
            "claim_copy_used_as_authority",
            "workflow_gate_self_status_used_as_authority",
            "remote_receipt_used_as_authority",
            "deployment_receipt_used_as_authority",
            "external_public_clone_probe_used_as_authority",
            "hosted_workflow_run_receipt_used_as_authority",
            "hosted_workflow_artifact_attestation_used_as_authority",
            "public_remote_clone_claimed",
            "hosted_public_remote_receipt_claimed",
            "deployment_receipt_claimed",
            "external_public_clone_probe_claimed",
            "hosted_workflow_run_receipt_claimed",
            "hosted_workflow_artifact_attestation_claimed",
            "unauthenticated_external_clone_claimed",
            "hosted_ci_claimed",
            "github_export_claimed",
            "public_deployment_claimed",
            "pages_or_public_site_claimed",
            "public_release_claimed",
            "private_repo_public_proof_claimed",
            "local_receipt_used_as_remote_proof",
        ):
            if decision.get(claim_flag) is not False:
                failures.append({"workflow_id": workflow_id, "reason": f"decision {claim_flag} must be false"})
        if decision.get("status") == "block" and not decision.get("repair_row"):
            failures.append({"workflow_id": workflow_id, "reason": "blocked workflow row missing repair row"})
        for ref in row.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"workflow_id": workflow_id, "missing_evidence_ref": ref})
        for ref in row.get("receipt_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"workflow_id": workflow_id, "missing_receipt_ref": ref})
        for validator_ref in row.get("validator_refs", []):
            if validator_ref not in validator_ids:
                failures.append({"workflow_id": workflow_id, "unknown_validator": validator_ref})

    if replay.get("schema_version") != "hosted_public_claim_replay_v0":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "unexpected replay schema"})
    if replay.get("microcosm_id") != "hosted_public_ci_workflow_gate_microcosm":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "unexpected replay microcosm_id"})
    if replay.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "replay must declare projection_not_authority"})
    replay_cases = replay.get("mechanism", {}).get("cases", [])
    if not isinstance(replay_cases, list) or len(replay_cases) < 5:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "expected at least five replay cases"})
        replay_cases = []
    required_case_ids = {
        "package_handoff_attempts_github_export",
        "local_clean_run_attempts_hosted_ci",
        "local_clone_attempts_public_remote",
        "external_clone_probe_attempts_public_remote",
        "external_clone_probe_attempts_hosted_ci_run",
        "external_clone_probe_attempts_package_export",
        "external_clone_probe_attempts_public_release_status",
        "hosted_workflow_run_receipt_attempts_hosted_ci",
        "hosted_workflow_run_receipt_attempts_public_remote",
        "hosted_workflow_run_receipt_attempts_package_export",
        "hosted_workflow_run_receipt_attempts_public_release_status",
        "hosted_workflow_artifact_attestation_attempts_artifact_integrity",
        "hosted_workflow_artifact_attestation_attempts_package_export",
        "hosted_workflow_artifact_attestation_attempts_public_deployment",
        "hosted_workflow_artifact_attestation_attempts_public_release_status",
        "release_artifact_witness_attempts_hosted_artifact_attestation",
        "release_artifact_witness_attempts_package_export",
        "release_artifact_witness_attempts_public_deployment",
        "release_artifact_witness_attempts_public_release",
        "release_artifact_witness_attempts_self_attestation",
        "site_projection_artifact_digest_attempts_deployment_evidence",
        "site_projection_artifact_digest_attempts_hosted_public_availability",
        "site_projection_artifact_digest_attempts_public_release_status",
        "site_projection_source_shuttle_attempts_hosted_public_availability",
        "site_projection_source_shuttle_attempts_private_field_rehydration",
        "site_projection_source_shuttle_attempts_public_release_status",
        "hosted_remote_receipt_attempts_public_remote",
        "hosted_remote_receipt_attempts_hosted_ci_run",
        "hosted_remote_receipt_attempts_public_release_status",
        "deployment_receipt_attempts_public_site",
        "deployment_receipt_attempts_github_export",
        "deployment_receipt_attempts_public_release_status",
        "website_projection_attempts_public_site",
        "release_claim_attempts_public_status",
    }
    observed_case_ids = {case.get("case_id") for case in replay_cases if isinstance(case, dict)}
    missing_case_ids = sorted(required_case_ids - observed_case_ids)
    if missing_case_ids:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "missing_case_ids": missing_case_ids})
    site_projection_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("site_projection_source_capsule_attempts_public_site_")
    ]
    if not site_projection_cases:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing site projection source capsule replay cases"})
    grammar_replay_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("grammar_replay_site_projection_attempts_hosted_public_")
    ]
    if len(grammar_replay_cases) < 5:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing grammar replay site projection hosted claim cases"})
    artifact_digest_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("site_projection_artifact_digest_attempts_")
    ]
    if len(artifact_digest_cases) < 3:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing site projection artifact digest replay cases"})
    source_shuttle_site_projection_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("site_projection_source_shuttle_attempts_")
    ]
    if len(source_shuttle_site_projection_cases) < 3:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing source-shuttle site projection hosted claim cases"})
    external_clone_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("external_clone_probe_attempts_")
    ]
    if len(external_clone_cases) < 4:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing external public clone probe replay cases"})
    hosted_workflow_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("hosted_workflow_run_receipt_attempts_")
    ]
    if len(hosted_workflow_cases) < 4:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing hosted workflow run receipt replay cases"})
    artifact_attestation_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("hosted_workflow_artifact_attestation_attempts_")
    ]
    if len(artifact_attestation_cases) < 4:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing hosted workflow artifact attestation replay cases"})
    release_artifact_witness_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("release_artifact_witness_attempts_")
    ]
    if len(release_artifact_witness_cases) < 5:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing release artifact witness hosted replay cases"})
    remote_receipt_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("hosted_remote_receipt_attempts_")
    ]
    if len(remote_receipt_cases) < 3:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing hosted public remote receipt replay cases"})
    deployment_receipt_cases = [
        case
        for case in replay_cases
        if isinstance(case, dict)
        and str(case.get("case_id") or "").startswith("deployment_receipt_attempts_")
    ]
    if len(deployment_receipt_cases) < 3:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "missing deployment receipt replay cases"})
    replay_status = replay.get("status", {})
    if int(replay_status.get("case_count", 0)) != len(replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "replay case count mismatch"})
    if int(replay_status.get("site_projection_source_capsule_replay_count", 0)) != len(site_projection_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "site projection replay count mismatch"})
    if int(replay_status.get("grammar_replay_site_projection_hosted_claim_replay_case_count", 0)) != len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay hosted claim count mismatch"})
    if int(replay_status.get("grammar_replay_site_projection_hosted_claim_replay_hash_verified_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay hosted claim hash verification count too low"})
    if int(replay_status.get("grammar_replay_site_projection_hosted_claim_replay_blocked_claim_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay hosted claim blocked claim count too low"})
    if int(replay_status.get("grammar_replay_site_projection_hosted_claim_replay_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay hosted claim self-attestation authority must be zero"})
    if int(replay_status.get("artifact_digest_hosted_claim_replay_case_count", 0)) != len(artifact_digest_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest hosted replay count mismatch"})
    if int(replay_status.get("artifact_digest_hosted_claim_replay_blocked_claim_count", 0)) < len(artifact_digest_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest hosted replay blocked claim count too low"})
    if int(replay_status.get("artifact_digest_hosted_claim_replay_source_witness_hash_preserved_count", 0)) < 1:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest replay missing source witness hash preservation"})
    if int(replay_status.get("artifact_digest_hosted_claim_replay_package_row_attachment_count", 0)) < 1:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest replay missing package row attachment count"})
    if int(replay_status.get("source_shuttle_site_projection_hosted_claim_replay_case_count", 0)) != len(source_shuttle_site_projection_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection hosted replay count mismatch"})
    if int(replay_status.get("source_shuttle_site_projection_hosted_claim_replay_hash_verified_count", 0)) < len(source_shuttle_site_projection_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection hosted replay hash verification count too low"})
    if int(replay_status.get("source_shuttle_site_projection_hosted_claim_replay_blocked_claim_count", 0)) < len(source_shuttle_site_projection_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection hosted replay blocked claim count too low"})
    for count_name in (
        "source_shuttle_site_projection_hosted_claim_replay_manifest_ref_count",
        "source_shuttle_site_projection_hosted_claim_replay_packet_hash_preserved_count",
        "source_shuttle_site_projection_hosted_claim_replay_source_clip_hash_preserved_count",
        "source_shuttle_site_projection_hosted_claim_replay_no_private_copy_rule_count",
    ):
        if int(replay_status.get(count_name, 0)) < 6:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "missing_status_count": count_name})
    for count_name in (
        "source_shuttle_site_projection_hosted_claim_replay_private_field_rehydration_count",
        "source_shuttle_site_projection_hosted_claim_replay_self_attestation_authority_count",
        "source_shuttle_site_projection_hosted_claim_replay_hosted_public_authority_count",
        "source_shuttle_site_projection_hosted_claim_replay_public_launch_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_public_release_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_publication_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_private_root_equivalence_claim_count",
        "source_shuttle_site_projection_hosted_claim_replay_benchmark_win_claim_count",
    ):
        if int(replay_status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "nonzero_status_count": count_name})
    if int(replay_status.get("external_public_clone_probe_gate_case_count", 0)) != len(external_clone_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "external public clone probe replay count mismatch"})
    if int(replay_status.get("hosted_workflow_run_receipt_gate_case_count", 0)) != len(hosted_workflow_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow run receipt replay count mismatch"})
    if int(replay_status.get("hosted_workflow_artifact_attestation_gate_case_count", 0)) != len(artifact_attestation_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow artifact attestation replay count mismatch"})
    if int(replay_status.get("release_artifact_integrity_witness_hosted_claim_replay_case_count", 0)) != len(release_artifact_witness_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness hosted replay count mismatch"})
    if int(replay_status.get("release_artifact_integrity_witness_source_case_count", 0)) < 5:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness source case count too low"})
    if int(replay_status.get("release_artifact_integrity_witness_hosted_claim_blocked_claim_count", 0)) < len(release_artifact_witness_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness blocked claim count too low"})
    if int(replay_status.get("release_artifact_integrity_witness_hosted_claim_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness hosted replay self-attestation authority must be zero"})
    if int(replay_status.get("hosted_public_remote_receipt_gate_case_count", 0)) != len(remote_receipt_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "remote receipt replay count mismatch"})
    if int(replay_status.get("deployment_receipt_gate_case_count", 0)) != len(deployment_receipt_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "deployment receipt replay count mismatch"})
    external_clone_gate = replay.get("external_public_clone_probe_gate", {})
    if external_clone_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "external public clone probe gate must stay fail-closed"})
    required_external_clone_fields = external_clone_gate.get("required_fields", [])
    missing_external_clone_fields = external_clone_gate.get("missing_fields", [])
    if not isinstance(required_external_clone_fields, list) or len(required_external_clone_fields) < 10:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "external public clone probe gate missing required fields"})
    if missing_external_clone_fields != required_external_clone_fields:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "external public clone probe gate must keep all required fields missing in fail-closed fixture"})
    for flag_name in (
        "external_public_clone_claim_allowed",
        "unauthenticated_clone_claim_allowed",
        "public_remote_claim_allowed",
        "hosted_ci_claim_allowed",
        "github_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if external_clone_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"external public clone probe gate {flag_name} must be false"})
    if int(external_clone_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "external public clone probe gate self-attestation authority must be zero"})

    hosted_workflow_gate = replay.get("hosted_workflow_run_receipt_gate", {})
    if hosted_workflow_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow run receipt gate must stay fail-closed"})
    required_hosted_workflow_fields = hosted_workflow_gate.get("required_fields", [])
    missing_hosted_workflow_fields = hosted_workflow_gate.get("missing_fields", [])
    if not isinstance(required_hosted_workflow_fields, list) or len(required_hosted_workflow_fields) < 10:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow run receipt gate missing required fields"})
    if missing_hosted_workflow_fields != required_hosted_workflow_fields:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow run receipt gate must keep all required fields missing in fail-closed fixture"})
    for flag_name in (
        "hosted_ci_claim_allowed",
        "hosted_run_claim_allowed",
        "public_remote_claim_allowed",
        "github_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if hosted_workflow_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"hosted workflow run receipt gate {flag_name} must be false"})
    if int(hosted_workflow_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow run receipt gate self-attestation authority must be zero"})

    artifact_attestation_gate = replay.get("hosted_workflow_artifact_attestation_gate", {})
    if artifact_attestation_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow artifact attestation gate must stay fail-closed"})
    required_artifact_fields = artifact_attestation_gate.get("required_fields", [])
    missing_artifact_fields = artifact_attestation_gate.get("missing_fields", [])
    if not isinstance(required_artifact_fields, list) or len(required_artifact_fields) < 10:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow artifact attestation gate missing required fields"})
    if missing_artifact_fields != required_artifact_fields:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow artifact attestation gate must keep all required fields missing in fail-closed fixture"})
    for flag_name in (
        "release_artifact_integrity_claim_allowed",
        "github_export_claim_allowed",
        "public_deployment_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if artifact_attestation_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"hosted workflow artifact attestation gate {flag_name} must be false"})
    if int(artifact_attestation_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "hosted workflow artifact attestation gate self-attestation authority must be zero"})

    release_artifact_witness_gate = replay.get("release_artifact_integrity_witness_hosted_claim_gate", {})
    if release_artifact_witness_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness hosted claim gate must stay fail-closed"})
    if int(release_artifact_witness_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness hosted claim gate self-attestation authority must be zero"})
    if int(release_artifact_witness_gate.get("evaluator_authority_count", 0)) < len(release_artifact_witness_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness hosted claim gate evaluator authority count too low"})
    if len(release_artifact_witness_gate.get("case_refs", [])) != len(release_artifact_witness_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "release artifact witness hosted claim gate case refs mismatch"})
    for flag_name in (
        "release_artifact_integrity_witness_authority_allowed",
        "hosted_workflow_artifact_attestation_claim_allowed",
        "package_export_claim_allowed",
        "public_deployment_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if release_artifact_witness_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"release artifact witness hosted claim gate {flag_name} must be false"})

    grammar_replay_gate = replay.get("grammar_replay_site_projection_hosted_claim_gate", {})
    if grammar_replay_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay site projection gate must stay fail-closed"})
    if int(grammar_replay_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay site projection gate self-attestation authority must be zero"})
    if int(grammar_replay_gate.get("evaluator_authority_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay site projection gate evaluator authority count too low"})
    if len(grammar_replay_gate.get("case_refs", [])) != len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay site projection gate case refs mismatch"})
    if int(grammar_replay_gate.get("hash_verified_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "grammar replay site projection gate hash verification count too low"})
    for flag_name in (
        "grammar_replay_authority_allowed",
        "site_projection_claim_authority_allowed",
        "hosted_public_claim_allowed",
        "public_deployment_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if grammar_replay_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"grammar replay site projection gate {flag_name} must be false"})

    artifact_digest_gate = replay.get("artifact_digest_site_projection_hosted_claim_replay_gate", {})
    if artifact_digest_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest site projection gate must stay fail-closed"})
    if int(artifact_digest_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest site projection gate self-attestation authority must be zero"})
    if int(artifact_digest_gate.get("evaluator_authority_count", 0)) < len(artifact_digest_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest site projection gate evaluator authority count too low"})
    if len(artifact_digest_gate.get("case_refs", [])) != len(artifact_digest_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest site projection gate case refs mismatch"})
    if int(artifact_digest_gate.get("source_witness_hash_preserved_count", 0)) < 1:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest site projection gate missing source witness hash preservation"})
    if int(artifact_digest_gate.get("package_row_attachment_count", 0)) < 1:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "artifact digest site projection gate missing package row attachment count"})
    for flag_name in (
        "artifact_digest_requirement_authority_allowed",
        "deployment_claim_allowed",
        "hosted_public_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if artifact_digest_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"artifact digest site projection gate {flag_name} must be false"})

    source_shuttle_gate = replay.get("source_shuttle_site_projection_hosted_claim_gate", {})
    if source_shuttle_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection gate must stay fail-closed"})
    if int(source_shuttle_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection gate self-attestation authority must be zero"})
    if int(source_shuttle_gate.get("evaluator_authority_count", 0)) < len(source_shuttle_site_projection_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection gate evaluator authority count too low"})
    if len(source_shuttle_gate.get("case_refs", [])) != len(source_shuttle_site_projection_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection gate case refs mismatch"})
    if int(source_shuttle_gate.get("source_clip_hash_verified_count", 0)) < len(source_shuttle_site_projection_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection gate hash verification count too low"})
    for count_name in (
        "manifest_ref_count",
        "packet_hash_preserved_count",
        "source_clip_hash_preserved_count",
        "no_private_copy_rule_count",
    ):
        if int(source_shuttle_gate.get(count_name, 0)) < 6:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "missing_gate_count": count_name})
    if int(source_shuttle_gate.get("private_field_rehydration_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "source-shuttle site projection gate private field rehydration must be zero"})
    for flag_name in (
        "source_shuttle_manifest_ref_authority_allowed",
        "source_shuttle_semantic_packet_authority_allowed",
        "source_shuttle_private_field_rehydration_allowed",
        "site_projection_source_shuttle_refs_hosted_public_allowed",
        "public_launch_claim_allowed",
        "hosted_public_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if source_shuttle_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"source-shuttle site projection gate {flag_name} must be false"})

    remote_receipt_gate = replay.get("hosted_public_remote_receipt_gate", {})
    if remote_receipt_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "remote receipt gate must stay fail-closed"})
    required_remote_fields = remote_receipt_gate.get("required_fields", [])
    missing_remote_fields = remote_receipt_gate.get("missing_fields", [])
    if not isinstance(required_remote_fields, list) or len(required_remote_fields) < 6:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "remote receipt gate missing required fields"})
    if missing_remote_fields != required_remote_fields:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "remote receipt gate must keep all required fields missing in fail-closed fixture"})
    for flag_name in (
        "public_remote_claim_allowed",
        "hosted_ci_claim_allowed",
        "github_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if remote_receipt_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"remote receipt gate {flag_name} must be false"})
    if int(remote_receipt_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "remote receipt gate self-attestation authority must be zero"})
    deployment_receipt_gate = replay.get("deployment_receipt_gate", {})
    if deployment_receipt_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "deployment receipt gate must stay fail-closed"})
    required_deployment_fields = deployment_receipt_gate.get("required_fields", [])
    missing_deployment_fields = deployment_receipt_gate.get("missing_fields", [])
    if not isinstance(required_deployment_fields, list) or len(required_deployment_fields) < 8:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "deployment receipt gate missing required fields"})
    if missing_deployment_fields != required_deployment_fields:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "deployment receipt gate must keep all required fields missing in fail-closed fixture"})
    for flag_name in (
        "public_site_claim_allowed",
        "public_deployment_claim_allowed",
        "github_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
    ):
        if deployment_receipt_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": f"deployment receipt gate {flag_name} must be false"})
    if int(deployment_receipt_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "deployment receipt gate self-attestation authority must be zero"})
    for count_name in ("capsule_count", "repair_route_count", "teaching_rule_count"):
        if int(replay_status.get(count_name, 0)) < len(replay_cases):
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "missing_status_count": count_name})
    if int(replay_status.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "replay missing_ref_count must be zero"})
    replay_authority = replay.get("authority", {})
    for count_name in (
        "self_attestation_count",
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(replay_authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "nonzero_authority_count": count_name})
    if int(replay_authority.get("evaluator_authority_count", 0)) < len(replay_cases):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "evaluator authority count too low"})
    if not replay.get("route", {}).get("first_command"):
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json", "reason": "replay missing first command"})
    for case in replay_cases:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip", "")
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "source_clip_hash mismatch"})
        if not case.get("semantic_carryforward"):
            failures.append({"case_id": case_id, "reason": "missing semantic carryforward"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "missing repair route"})
        if not case.get("restart_point"):
            failures.append({"case_id": case_id, "reason": "missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "missing teaching rule"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "missing anti-claims"})
        if not str(case.get("outcome", "")).startswith("blocked:"):
            failures.append({"case_id": case_id, "reason": "replay case must block the hosted claim"})
        flags = case.get("authority_flags", {})
        for flag_name in (
            "claim_copy_is_authority",
            "workflow_gate_self_status_is_authority",
            "self_attestation_is_authority",
            "remote_receipt_is_authority",
            "remote_receipt_claimed",
            "hosted_run_claimed",
            "deployment_receipt_is_authority",
            "deployment_receipt_claimed",
            "external_public_clone_probe_is_authority",
            "external_public_clone_claimed",
            "hosted_workflow_run_receipt_is_authority",
            "hosted_workflow_run_receipt_claimed",
            "hosted_workflow_artifact_attestation_is_authority",
            "hosted_workflow_artifact_attestation_claimed",
            "release_artifact_integrity_claimed",
            "site_projection_used_as_claim_authority",
            "source_capsule_hash_used_as_public_permission",
            "artifact_digest_requirement_used_as_authority",
            "artifact_witness_used_as_public_authority",
            "site_projection_digest_used_as_deployment_evidence",
            "site_projection_digest_used_as_hosted_public_evidence",
            "artifact_digest_requirement_claimed",
            "hosted_public_claimed",
            "package_export_claimed",
            "unauthenticated_external_clone_claimed",
            "public_deployment_claimed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if flags.get(flag_name) is not False:
                failures.append({"case_id": case_id, "reason": f"authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
        "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
        "microcosms/hosted_public_ci_workflow_gate/README.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "src/idea_microcosm/hosted_public_ci_workflow_gate_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "microcosms/license_citation_disclosure_gate/clearance_gate.json",
        "microcosms/license_citation_disclosure_gate/receipt.json",
        "microcosms/recipient_review_route_gate/route_gate.json",
        "microcosms/recipient_review_route_gate/receipt.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
        "microcosms/website_card_projection_gate/card_gate.json",
        "microcosms/website_card_projection_gate/receipt.json",
        "microcosms/source_shuttle/source_shuttle_board.json",
        "microcosms/source_shuttle/receipt.json",
        "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
        "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
        "microcosms/release_artifact_integrity_witness/integrity_witness.json",
        "microcosms/release_artifact_integrity_witness/receipt.json",
        "state/artifact_manifest.json",
        "state/site_projection_manifest.json",
        "site/sandbox/site_projection_manifest.json",
        "site/sandbox/site_projection_bundle.json",
        "site/sandbox/site_projection_receipt.json",
        "receipts/release_candidate_portfolio.json",
        "receipts/cold_sandbox_probe_latest.json",
        "receipts/validation_run.json",
        "release/publication_gate.json",
        "RELEASE_SCOPE.md",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-hosted-public-ci-workflow-gate-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "not a publication authority",
        "source hashes",
        "hosted public CI",
        "hosted public remote",
        "external public clone probe fields",
        "hosted workflow run receipt fields",
        "hosted workflow artifact attestation fields",
        "site projection artifact-digest boundaries",
        "source-shuttle site projection boundaries",
        "hosted public remote receipt fields",
        "Deployment receipt fields",
        "site projection source capsules",
        "Local receipts remain local-only",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/hosted_public_ci_workflow_gate/README.md", "missing_text": required_text})
    return failures


def _release_artifact_integrity_witness_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "release_artifact_integrity_witness" / "integrity_witness.json"
    receipt_path = root / "microcosms" / "release_artifact_integrity_witness" / "receipt.json"
    readme_path = root / "microcosms" / "release_artifact_integrity_witness" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "missing integrity witness board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/release_artifact_integrity_witness/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/release_artifact_integrity_witness/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("schema_version") != "release_artifact_integrity_witness_specimen_v0":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "unexpected schema"})
    if board.get("microcosm_id") != "release_artifact_integrity_witness":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "unexpected microcosm_id"})
    if board.get("candidate_id") != "release_artifact_integrity_witness_microcosm":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "unexpected candidate_id"})
    if board.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "witness must declare projection_not_authority"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "witness must not imply public release readiness"})

    cases = board.get("mechanism", {}).get("cases", [])
    if not isinstance(cases, list) or len(cases) < 5:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "expected at least five witness cases"})
        cases = []
    required_case_ids = {
        "artifact_attestation_placeholder_attempts_integrity_witness",
        "artifact_digest_attempts_package_export",
        "artifact_witness_attempts_public_deployment",
        "artifact_witness_attempts_public_release",
        "artifact_witness_attempts_self_attestation",
    }
    observed_case_ids = {case.get("case_id") for case in cases if isinstance(case, dict)}
    missing_case_ids = sorted(required_case_ids - observed_case_ids)
    if missing_case_ids:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "missing_case_ids": missing_case_ids})

    status = board.get("status", {})
    if int(status.get("case_count", 0)) != len(cases):
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "case count mismatch"})
    for count_name in (
        "source_capsule_count",
        "capsule_count",
        "semantic_carryforward_count",
        "failure_replay_count",
        "repair_route_count",
        "teaching_rule_count",
        "claim_boundary_count",
        "artifact_integrity_witness_case_count",
    ):
        if int(status.get(count_name, 0)) < len(cases):
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "missing_status_count": count_name})
    if int(status.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "witness missing_ref_count must be zero"})
    if status.get("validation_status") != "ok":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "validation_status must be ok"})
    if status.get("next_owner") != "package_manifest_artifact_digest_bridge_microcosm":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "unexpected next_owner"})
    if int(status.get("projection_freshness_case_count", 0)) < 5:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness extension must cover at least five cases"})
    if int(status.get("projection_freshness_refusal_count", 0)) < 4:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness extension must refuse stale or unbound promotions"})
    for count_name in (
        "projection_freshness_source_authority_upgrade_count",
        "projection_freshness_public_release_permission_count",
        "projection_freshness_publication_permission_count",
        "projection_freshness_missing_command_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "nonzero_projection_freshness_count": count_name})

    authority = board.get("authority", {})
    for count_name in (
        "self_attestation_count",
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "nonzero_authority_count": count_name})
    if int(authority.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "evaluator authority count too low"})
    for forbidden in (
        "artifact digest to package export authority",
        "artifact witness to public deployment authority",
        "artifact witness to public release authority",
        "artifact witness to publication permission",
        "stale generated projection to public release authority",
        "receipt-free projection to source authority",
    ):
        if forbidden not in authority.get("forbidden_promotions", []):
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "missing_forbidden_promotion": forbidden})

    projection_extension = board.get("projection_freshness_refusal_extension", {})
    if not isinstance(projection_extension, dict) or projection_extension.get("status") != "pass":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness refusal extension must pass"})
        projection_extension = {}
    if projection_extension.get("schema_version") != "projection_freshness_refusal_extension_v0":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "unexpected projection freshness extension schema"})
    projection_summary = projection_extension.get("summary", {})
    if int(projection_summary.get("projection_case_count", 0)) < 5:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness extension case count too low"})
    if int(projection_summary.get("freshness_refusal_count", 0)) < 4:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness extension must refuse stale or missing authority"})
    for count_name in (
        "source_authority_upgrade_count",
        "public_release_permission_count",
        "publication_permission_count",
        "private_root_equivalence_claim_count",
        "benchmark_claim_count",
        "missing_freshness_command_count",
    ):
        if int(projection_summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "nonzero_projection_extension_count": count_name})
    projection_rows = projection_extension.get("rows", [])
    if not isinstance(projection_rows, list) or len(projection_rows) < 5:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness extension must include rows"})
        projection_rows = []
    for row in projection_rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness row must be an object"})
            continue
        if not row.get("freshness_check_command"):
            failures.append({"row_id": row.get("row_id"), "reason": "projection freshness row must name a freshness_check_command"})
        if row.get("projection_used_as_source_authority") is not False:
            failures.append({"row_id": row.get("row_id"), "reason": "projection row must not become source authority"})
        if row.get("public_release_permission_granted") is not False:
            failures.append({"row_id": row.get("row_id"), "reason": "projection row must not grant public release permission"})
        if row.get("publication_permission_granted") is not False:
            failures.append({"row_id": row.get("row_id"), "reason": "projection row must not grant publication permission"})
    for validator_row in projection_extension.get("validator_results", []):
        if not isinstance(validator_row, dict) or validator_row.get("status") != "pass":
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "projection freshness validator row must pass"})

    artifact_case = next((case for case in cases if case.get("case_id") == "artifact_attestation_placeholder_attempts_integrity_witness"), {})
    if int(artifact_case.get("semantic_carryforward", {}).get("missing_field_count", 0)) < 10:
        failures.append({"case_id": "artifact_attestation_placeholder_attempts_integrity_witness", "reason": "artifact attestation case must preserve missing hosted fields"})
    if "workflow artifact attestation placeholder proves release artifact integrity" not in artifact_case.get("anti_claims", []):
        failures.append({"case_id": "artifact_attestation_placeholder_attempts_integrity_witness", "reason": "missing artifact-attestation anti-claim"})
    package_case = next((case for case in cases if case.get("case_id") == "artifact_digest_attempts_package_export"), {})
    if package_case.get("restart_point") != "microcosms/public_release_package_manifest_gate/package_manifest.json::package_promotion_gate":
        failures.append({"case_id": "artifact_digest_attempts_package_export", "reason": "package case restart point must route through package promotion gate"})
    release_case = next((case for case in cases if case.get("case_id") == "artifact_witness_attempts_public_release"), {})
    if release_case.get("restart_point") != "release/publication_gate.json::status":
        failures.append({"case_id": "artifact_witness_attempts_public_release", "reason": "public-release case restart point must be publication gate status"})

    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/release_artifact_integrity_witness/integrity_witness.json", "reason": "witness case must be an object"})
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip", "")
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "source_clip_hash mismatch"})
        carryforward = case.get("semantic_carryforward", {})
        if carryforward.get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "semantic carryforward must declare projection_not_authority"})
        for claim_name in (
            "release_artifact_integrity_claimed",
            "package_export_claimed",
            "public_deployment_claimed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if carryforward.get(claim_name) is not False:
                failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "missing repair route"})
        if not case.get("restart_point"):
            failures.append({"case_id": case_id, "reason": "missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "missing teaching rule"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "missing anti-claims"})
        if not str(case.get("outcome", "")).startswith("blocked:"):
            failures.append({"case_id": case_id, "reason": "witness case must block the attempted promotion"})
        flags = case.get("authority_flags", {})
        for flag_name, flag_value in flags.items():
            if flag_value is not False:
                failures.append({"case_id": case_id, "reason": f"authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    if receipt.get("projection_freshness_refusal_extension_path") != "microcosms/release_artifact_integrity_witness/integrity_witness.json:projection_freshness_refusal_extension":
        failures.append({"path": "microcosms/release_artifact_integrity_witness/receipt.json", "reason": "receipt must point to projection freshness refusal extension"})
    for validator_row in receipt.get("projection_freshness_refusal_validator_summary", []):
        if not isinstance(validator_row, dict) or validator_row.get("status") != "pass":
            failures.append({"path": "microcosms/release_artifact_integrity_witness/receipt.json", "reason": "receipt projection freshness validator row must pass"})
    required_receipt_refs = {
        "microcosms/release_artifact_integrity_witness/integrity_witness.json",
        "microcosms/release_artifact_integrity_witness/README.md",
        "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
        "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
        "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
        "release/publication_gate.json",
        "registry/release_candidates.json",
        "registry/validators.json",
    }
    evidence_refs = set(receipt.get("evidence_refs", []))
    missing_receipt_refs = sorted(required_receipt_refs - evidence_refs)
    if missing_receipt_refs:
        failures.append({"path": "microcosms/release_artifact_integrity_witness/receipt.json", "missing_evidence_refs": missing_receipt_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/release_artifact_integrity_witness/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-artifact-integrity-witness-specimen --root . --write-receipt",
        "bounded local witness",
        "source capsules",
        "not package export authority",
        "publication permission",
        "fail-closed",
        "projection_freshness_refusal_extension",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/release_artifact_integrity_witness/README.md", "missing_text": required_text})
    return failures


def _external_public_clone_probe_receipt_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "external_public_clone_probe_receipt" / "clone_probe_receipt.json"
    receipt_path = root / "microcosms" / "external_public_clone_probe_receipt" / "receipt.json"
    readme_path = root / "microcosms" / "external_public_clone_probe_receipt" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "missing clone probe receipt board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("schema_version") != "external_public_clone_probe_receipt_specimen_v0":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "unexpected schema"})
    if board.get("microcosm_id") != "external_public_clone_probe_receipt":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "unexpected microcosm_id"})
    if board.get("candidate_id") != "external_public_clone_probe_receipt_microcosm":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "unexpected candidate_id"})
    if board.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt board must declare projection_not_authority"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt board must not imply public release readiness"})

    cases = board.get("mechanism", {}).get("cases", [])
    if not isinstance(cases, list) or len(cases) < 5:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "expected at least five clone probe receipt cases"})
        cases = []
    required_case_ids = {
        "clone_probe_receipt_requires_public_remote_identity",
        "clone_probe_receipt_requires_unauthenticated_clone_result",
        "clone_probe_receipt_requires_output_digests",
        "clone_probe_receipt_requires_commit_and_run_binding",
        "clone_probe_receipt_requires_publication_gate_status",
    }
    observed_case_ids = {case.get("case_id") for case in cases if isinstance(case, dict)}
    missing_case_ids = sorted(required_case_ids - observed_case_ids)
    if missing_case_ids:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "missing_case_ids": missing_case_ids})

    status = board.get("status", {})
    if int(status.get("case_count", 0)) != len(cases):
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "case count mismatch"})
    for count_name in (
        "source_capsule_count",
        "capsule_count",
        "semantic_carryforward_count",
        "failure_replay_count",
        "repair_route_count",
        "teaching_rule_count",
        "claim_boundary_count",
        "external_public_clone_probe_receipt_case_count",
    ):
        if int(status.get(count_name, 0)) < len(cases):
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "missing_status_count": count_name})
    if int(status.get("external_public_clone_probe_required_field_count", 0)) < 10:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt must preserve required external clone fields"})
    if int(status.get("external_public_clone_probe_missing_field_count", -1)) != int(status.get("external_public_clone_probe_required_field_count", 0)):
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "missing external clone fields must match required fields in fail-closed fixture"})
    grammar_replay_case_count = int(status.get("grammar_replay_external_clone_receipt_case_count", 0))
    if grammar_replay_case_count < 5:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "expected hosted grammar replay cases in clone receipt"})
    for count_name in (
        "grammar_replay_external_clone_receipt_source_capsule_count",
        "grammar_replay_external_clone_receipt_semantic_carryforward_count",
        "grammar_replay_external_clone_receipt_failure_replay_count",
        "grammar_replay_external_clone_receipt_repair_route_count",
        "grammar_replay_external_clone_receipt_teaching_rule_count",
        "grammar_replay_external_clone_receipt_hash_verified_count",
    ):
        if int(status.get(count_name, 0)) < grammar_replay_case_count:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "missing_status_count": count_name})
    for count_name in (
        "grammar_replay_external_clone_receipt_self_attestation_authority_count",
        "grammar_replay_external_clone_receipt_public_release_claim_count",
        "grammar_replay_external_clone_receipt_publication_claim_count",
        "grammar_replay_external_clone_receipt_private_root_equivalence_claim_count",
        "grammar_replay_external_clone_receipt_benchmark_win_claim_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "nonzero_grammar_replay_count": count_name})
    source_shuttle_case_count = int(status.get("source_shuttle_external_clone_receipt_case_count", 0))
    if source_shuttle_case_count < 3:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "expected source-shuttle hosted-claim cases in clone receipt"})
    for count_name in (
        "source_shuttle_external_clone_receipt_source_capsule_count",
        "source_shuttle_external_clone_receipt_semantic_carryforward_count",
        "source_shuttle_external_clone_receipt_failure_replay_count",
        "source_shuttle_external_clone_receipt_repair_route_count",
        "source_shuttle_external_clone_receipt_teaching_rule_count",
        "source_shuttle_external_clone_receipt_hash_verified_count",
    ):
        if int(status.get(count_name, 0)) < source_shuttle_case_count:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "missing_status_count": count_name})
    for count_name in (
        "source_shuttle_external_clone_receipt_manifest_ref_count",
        "source_shuttle_external_clone_receipt_packet_hash_preserved_count",
        "source_shuttle_external_clone_receipt_source_clip_hash_preserved_count",
        "source_shuttle_external_clone_receipt_no_private_copy_rule_count",
    ):
        if int(status.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "missing_status_count": count_name})
    for count_name in (
        "source_shuttle_external_clone_receipt_private_field_rehydration_count",
        "source_shuttle_external_clone_receipt_external_clone_authority_count",
        "source_shuttle_external_clone_receipt_public_remote_claim_count",
        "source_shuttle_external_clone_receipt_hosted_public_claim_count",
        "source_shuttle_external_clone_receipt_self_attestation_authority_count",
        "source_shuttle_external_clone_receipt_public_release_claim_count",
        "source_shuttle_external_clone_receipt_publication_claim_count",
        "source_shuttle_external_clone_receipt_private_root_equivalence_claim_count",
        "source_shuttle_external_clone_receipt_benchmark_win_claim_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "nonzero_source_shuttle_count": count_name})
    if int(status.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt board missing_ref_count must be zero"})
    if status.get("validation_status") != "ok":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "validation_status must be ok"})
    if status.get("next_owner") != "hosted_public_remote_receipt_reconciliation_microcosm":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "unexpected next_owner"})

    gate = board.get("external_public_clone_probe_receipt_gate", {})
    if gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt gate must stay fail-closed"})
    if gate.get("missing_fields") != gate.get("required_fields"):
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt gate must keep all required fields missing in fail-closed fixture"})
    if int(gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt gate self-attestation authority must be zero"})
    if int(gate.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt gate evaluator authority count too low"})
    for flag_name in (
        "external_public_clone_claim_allowed",
        "unauthenticated_clone_claim_allowed",
        "public_remote_claim_allowed",
        "hosted_ci_claim_allowed",
        "github_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": f"receipt gate {flag_name} must be false"})

    grammar_gate = board.get("grammar_replay_external_clone_receipt_gate", {})
    if grammar_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "grammar replay clone receipt gate must stay fail-closed"})
    if int(grammar_gate.get("source_case_count", 0)) < 5:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "grammar replay clone receipt gate must carry source cases"})
    if int(grammar_gate.get("hash_verified_count", 0)) < int(grammar_gate.get("source_case_count", 0)):
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "grammar replay clone receipt gate must preserve verified hashes"})
    if int(grammar_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "grammar replay clone receipt self-attestation authority must be zero"})
    for flag_name in (
        "external_clone_receipt_claim_allowed",
        "grammar_replay_authority_allowed",
        "hosted_public_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if grammar_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": f"grammar replay clone receipt gate {flag_name} must be false"})

    source_shuttle_gate = board.get("source_shuttle_external_clone_receipt_gate", {})
    if source_shuttle_gate.get("schema_version") != "source_shuttle_external_clone_receipt_gate_v0":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "source-shuttle clone receipt gate schema mismatch"})
    if source_shuttle_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "source-shuttle clone receipt gate must stay fail-closed"})
    if source_shuttle_gate.get("source_gate_ref") != "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json::source_shuttle_site_projection_hosted_claim_gate":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "source-shuttle clone receipt gate must cite hosted source-shuttle gate"})
    if int(source_shuttle_gate.get("source_case_count", 0)) < 3:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "source-shuttle clone receipt gate must carry source cases"})
    if int(source_shuttle_gate.get("source_clip_hash_verified_count", 0)) < int(source_shuttle_gate.get("source_case_count", 0)):
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "source-shuttle clone receipt gate must preserve verified hashes"})
    for count_name in (
        "manifest_ref_count",
        "packet_hash_preserved_count",
        "source_clip_hash_preserved_count",
        "no_private_copy_rule_count",
    ):
        if int(source_shuttle_gate.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "missing_source_shuttle_gate_count": count_name})
    if int(source_shuttle_gate.get("private_field_rehydration_count", -1)) != 0:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "source-shuttle clone receipt gate must block private-field rehydration"})
    if int(source_shuttle_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "source-shuttle clone receipt self-attestation authority must be zero"})
    for flag_name in (
        "external_clone_receipt_claim_allowed",
        "source_shuttle_authority_allowed",
        "source_shuttle_manifest_ref_public_remote_authority_allowed",
        "source_shuttle_private_field_rehydration_allowed",
        "hosted_public_claim_allowed",
        "public_clone_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if source_shuttle_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": f"source-shuttle clone receipt gate {flag_name} must be false"})

    authority = board.get("authority", {})
    for count_name in (
        "self_attestation_count",
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "nonzero_authority_count": count_name})
    if int(authority.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "evaluator authority count too low"})
    for forbidden in (
        "external clone receipt to public remote authority",
        "external clone receipt to hosted CI authority",
        "external clone receipt to public release authority",
        "external clone receipt to publication permission",
    ):
        if forbidden not in authority.get("forbidden_promotions", []):
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "missing_forbidden_promotion": forbidden})

    identity_case = next((case for case in cases if case.get("case_id") == "clone_probe_receipt_requires_public_remote_identity"), {})
    if int(identity_case.get("semantic_carryforward", {}).get("field_group_missing_count", 0)) < 3:
        failures.append({"case_id": "clone_probe_receipt_requires_public_remote_identity", "reason": "identity case must preserve public remote missing fields"})
    if "local repository path proves public remote identity" not in identity_case.get("anti_claims", []):
        failures.append({"case_id": "clone_probe_receipt_requires_public_remote_identity", "reason": "missing local path anti-claim"})
    clone_case = next((case for case in cases if case.get("case_id") == "clone_probe_receipt_requires_unauthenticated_clone_result"), {})
    if clone_case.get("restart_point") != "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json::external_clone_probe_attempts_public_remote":
        failures.append({"case_id": "clone_probe_receipt_requires_unauthenticated_clone_result", "reason": "clone result case must restart at hosted external clone replay"})
    publication_case = next((case for case in cases if case.get("case_id") == "clone_probe_receipt_requires_publication_gate_status"), {})
    if publication_case.get("restart_point") != "release/publication_gate.json::status":
        failures.append({"case_id": "clone_probe_receipt_requires_publication_gate_status", "reason": "publication case restart point must be publication gate status"})
    grammar_cases = [
        case
        for case in cases
        if isinstance(case, dict) and str(case.get("case_id", "")).startswith("clone_probe_receipt_replays_grammar_replay_site_projection_")
    ]
    if len(grammar_cases) < 5:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "missing grammar replay external clone receipt cases"})
    source_shuttle_cases = [
        case
        for case in cases
        if isinstance(case, dict) and str(case.get("case_id", "")).startswith("clone_probe_receipt_replays_site_projection_source_shuttle_")
    ]
    if len(source_shuttle_cases) < 3:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "missing source-shuttle external clone receipt cases"})

    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json", "reason": "receipt case must be an object"})
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip", "")
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "source_clip_hash mismatch"})
        carryforward = case.get("semantic_carryforward", {})
        if carryforward.get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "semantic carryforward must declare projection_not_authority"})
        if str(case_id).startswith("clone_probe_receipt_replays_grammar_replay_site_projection_"):
            if carryforward.get("upstream_hash_verified") is not True:
                failures.append({"case_id": case_id, "reason": "grammar replay case must preserve verified upstream hash"})
            if carryforward.get("external_clone_probe_receipt_hides_grammar_failure") is not False:
                failures.append({"case_id": case_id, "reason": "grammar replay case must block hidden-failure promotion"})
            if "external clone probe receipt can hide failed grammar cases" not in case.get("anti_claims", []):
                failures.append({"case_id": case_id, "reason": "grammar replay case missing hidden-failure anti-claim"})
        if str(case_id).startswith("clone_probe_receipt_replays_site_projection_source_shuttle_"):
            if carryforward.get("source_clip_hash_verified") is not True:
                failures.append({"case_id": case_id, "reason": "source-shuttle case must preserve verified source hash"})
            for field in (
                "source_shuttle_private_field_rehydration_allowed",
                "source_shuttle_manifest_ref_used_as_external_clone_authority",
                "source_shuttle_manifest_ref_used_as_public_remote_authority",
                "site_projection_source_shuttle_refs_used_as_external_clone_evidence",
                "site_projection_source_shuttle_refs_used_as_public_clone_authority",
                "external_clone_probe_receipt_promotes_source_shuttle_to_public_clone",
                "external_clone_probe_receipt_rehydrates_source_shuttle_private_fields",
                "external_clone_probe_receipt_uses_source_shuttle_as_hosted_public_evidence",
            ):
                if carryforward.get(field) is not False:
                    failures.append({"case_id": case_id, "reason": f"source-shuttle carryforward {field} must be false"})
            if int(carryforward.get("source_shuttle_manifest_ref_count", 0)) < 1:
                failures.append({"case_id": case_id, "reason": "source-shuttle case must preserve manifest refs"})
            if "external clone probe receipt promotes source-shuttle refs to public clone proof" not in case.get("anti_claims", []):
                failures.append({"case_id": case_id, "reason": "source-shuttle case missing public-clone anti-claim"})
        for claim_name in (
            "public_remote_claimed",
            "unauthenticated_external_clone_claimed",
            "hosted_ci_claimed",
            "github_export_claimed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if carryforward.get(claim_name) is not False:
                failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "missing repair route"})
        if not case.get("restart_point"):
            failures.append({"case_id": case_id, "reason": "missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "missing teaching rule"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "missing anti-claims"})
        if not str(case.get("outcome", "")).startswith("blocked:"):
            failures.append({"case_id": case_id, "reason": "receipt case must block the attempted promotion"})
        flags = case.get("authority_flags", {})
        for flag_name, flag_value in flags.items():
            if flag_value is not False:
                failures.append({"case_id": case_id, "reason": f"authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    required_receipt_refs = {
        "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
        "microcosms/external_public_clone_probe_receipt/README.md",
        "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
        "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
        "microcosms/hosted_public_ci_workflow_gate/receipt.json",
        "release/publication_gate.json",
        "registry/release_candidates.json",
    }
    evidence_refs = set(receipt.get("evidence_refs", []))
    missing_receipt_refs = sorted(required_receipt_refs - evidence_refs)
    if missing_receipt_refs:
        failures.append({"path": "microcosms/external_public_clone_probe_receipt/receipt.json", "missing_evidence_refs": missing_receipt_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-external-public-clone-probe-receipt-specimen --root . --write-receipt",
        "bounded local receipt owner",
        "source capsules",
        "not public clone availability",
        "publication permission",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/external_public_clone_probe_receipt/README.md", "missing_text": required_text})
    return failures


def _hosted_public_remote_receipt_reconciliation_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "hosted_public_remote_receipt_reconciliation" / "reconciliation_board.json"
    receipt_path = root / "microcosms" / "hosted_public_remote_receipt_reconciliation" / "receipt.json"
    readme_path = root / "microcosms" / "hosted_public_remote_receipt_reconciliation" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "missing reconciliation board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("schema_version") != "hosted_public_remote_receipt_reconciliation_specimen_v0":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "unexpected schema"})
    if board.get("microcosm_id") != "hosted_public_remote_receipt_reconciliation":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "unexpected microcosm_id"})
    if board.get("candidate_id") != "hosted_public_remote_receipt_reconciliation_microcosm":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "unexpected candidate_id"})
    if board.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation board must declare projection_not_authority"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation board must not imply public release readiness"})

    cases = board.get("mechanism", {}).get("cases", [])
    if not isinstance(cases, list) or len(cases) < 5:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "expected at least five reconciliation cases"})
        cases = []
    required_case_ids = {
        "reconciliation_requires_remote_identity_alignment",
        "reconciliation_requires_commit_and_workflow_binding",
        "reconciliation_requires_clone_output_digest_binding",
        "reconciliation_requires_package_manifest_boundary",
        "reconciliation_requires_publication_gate_status",
    }
    observed_case_ids = {case.get("case_id") for case in cases if isinstance(case, dict)}
    missing_case_ids = sorted(required_case_ids - observed_case_ids)
    if missing_case_ids:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_case_ids": missing_case_ids})
    grammar_replay_cases = [
        case
        for case in cases
        if isinstance(case, dict)
        and str(case.get("case_id", "")).startswith(
            "remote_reconciliation_replays_clone_probe_receipt_replays_grammar_replay_site_projection_"
        )
    ]
    if len(grammar_replay_cases) < 5:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "expected at least five grammar replay reconciliation cases"})
    source_shuttle_cases = [
        case
        for case in cases
        if isinstance(case, dict)
        and str(case.get("case_id", "")).startswith(
            "remote_reconciliation_replays_clone_probe_receipt_replays_site_projection_source_shuttle_"
        )
    ]
    if len(source_shuttle_cases) < 3:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "expected at least three source-shuttle reconciliation cases"})

    status = board.get("status", {})
    if int(status.get("case_count", 0)) != len(cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "case count mismatch"})
    for count_name in (
        "source_capsule_count",
        "capsule_count",
        "semantic_carryforward_count",
        "failure_replay_count",
        "repair_route_count",
        "teaching_rule_count",
        "claim_boundary_count",
        "hosted_public_remote_receipt_reconciliation_case_count",
    ):
        if int(status.get(count_name, 0)) < len(cases):
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_status_count": count_name})
    if int(status.get("grammar_replay_remote_reconciliation_case_count", 0)) != len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "grammar replay reconciliation count mismatch"})
    for count_name in (
        "grammar_replay_remote_reconciliation_source_capsule_count",
        "grammar_replay_remote_reconciliation_semantic_carryforward_count",
        "grammar_replay_remote_reconciliation_failure_replay_count",
        "grammar_replay_remote_reconciliation_repair_route_count",
        "grammar_replay_remote_reconciliation_teaching_rule_count",
        "grammar_replay_remote_reconciliation_hash_verified_count",
    ):
        if int(status.get(count_name, 0)) < len(grammar_replay_cases):
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_status_count": count_name})
    for count_name in (
        "grammar_replay_remote_reconciliation_self_attestation_authority_count",
        "grammar_replay_remote_reconciliation_public_release_claim_count",
        "grammar_replay_remote_reconciliation_publication_claim_count",
        "grammar_replay_remote_reconciliation_private_root_equivalence_claim_count",
        "grammar_replay_remote_reconciliation_benchmark_win_claim_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "nonzero_grammar_replay_count": count_name})
    if int(status.get("source_shuttle_remote_reconciliation_case_count", 0)) != len(source_shuttle_cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "source-shuttle reconciliation count mismatch"})
    for count_name in (
        "source_shuttle_remote_reconciliation_source_capsule_count",
        "source_shuttle_remote_reconciliation_semantic_carryforward_count",
        "source_shuttle_remote_reconciliation_failure_replay_count",
        "source_shuttle_remote_reconciliation_repair_route_count",
        "source_shuttle_remote_reconciliation_teaching_rule_count",
        "source_shuttle_remote_reconciliation_hash_verified_count",
        "source_shuttle_remote_reconciliation_source_clip_hash_verified_count",
    ):
        if int(status.get(count_name, 0)) < len(source_shuttle_cases):
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_status_count": count_name})
    for count_name in (
        "source_shuttle_remote_reconciliation_manifest_ref_count",
        "source_shuttle_remote_reconciliation_packet_hash_preserved_count",
        "source_shuttle_remote_reconciliation_source_clip_hash_preserved_count",
        "source_shuttle_remote_reconciliation_no_private_copy_rule_count",
    ):
        if int(status.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_source_shuttle_count": count_name})
    for count_name in (
        "source_shuttle_remote_reconciliation_private_field_rehydration_count",
        "source_shuttle_remote_reconciliation_self_attestation_authority_count",
        "source_shuttle_remote_reconciliation_public_remote_claim_count",
        "source_shuttle_remote_reconciliation_hosted_public_claim_count",
        "source_shuttle_remote_reconciliation_public_release_claim_count",
        "source_shuttle_remote_reconciliation_publication_claim_count",
        "source_shuttle_remote_reconciliation_private_root_equivalence_claim_count",
        "source_shuttle_remote_reconciliation_benchmark_win_claim_count",
        "source_shuttle_remote_reconciliation_actual_execution_authority_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "nonzero_source_shuttle_count": count_name})
    if int(status.get("remote_receipt_required_field_count", 0)) < 6:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "remote receipt required fields must be preserved"})
    if int(status.get("external_public_clone_probe_required_field_count", 0)) < 10:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "external clone required fields must be preserved"})
    if int(status.get("remote_clone_alignment_missing_field_count", -1)) != int(status.get("remote_clone_alignment_required_field_count", 0)):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "all reconciliation fields must remain missing in fail-closed fixture"})
    if int(status.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation board missing_ref_count must be zero"})
    if status.get("validation_status") != "ok":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "validation_status must be ok"})
    if status.get("next_owner") != "actual_public_remote_clone_execution_microcosm":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "unexpected next_owner"})

    gate = board.get("remote_receipt_reconciliation_gate", {})
    if gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation gate must stay fail-closed"})
    if gate.get("missing_fields") != gate.get("required_fields"):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation gate must keep all required fields missing in fail-closed fixture"})
    if int(gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation gate self-attestation authority must be zero"})
    if int(gate.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation gate evaluator authority count too low"})
    for flag_name in (
        "remote_receipt_reconciliation_allowed",
        "public_remote_claim_allowed",
        "public_clone_claim_allowed",
        "hosted_ci_claim_allowed",
        "package_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": f"reconciliation gate {flag_name} must be false"})

    grammar_gate = board.get("grammar_replay_remote_reconciliation_gate", {})
    if grammar_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "grammar replay reconciliation gate must stay fail-closed"})
    if int(grammar_gate.get("source_case_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "grammar replay reconciliation gate source case count too low"})
    if int(grammar_gate.get("hash_verified_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "grammar replay reconciliation gate hash verified count too low"})
    if int(grammar_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "grammar replay reconciliation gate self-attestation authority must be zero"})
    if int(grammar_gate.get("evaluator_authority_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "grammar replay reconciliation gate evaluator authority count too low"})
    for flag_name in (
        "remote_reconciliation_claim_allowed",
        "external_clone_receipt_claim_allowed",
        "grammar_replay_authority_allowed",
        "hosted_public_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if grammar_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": f"grammar replay reconciliation gate {flag_name} must be false"})

    source_shuttle_gate = board.get("source_shuttle_remote_reconciliation_gate", {})
    if source_shuttle_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "source-shuttle reconciliation gate must stay fail-closed"})
    if int(source_shuttle_gate.get("source_case_count", 0)) < len(source_shuttle_cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "source-shuttle reconciliation gate source case count too low"})
    for count_name in (
        "hash_verified_count",
        "source_clip_hash_verified_count",
    ):
        if int(source_shuttle_gate.get(count_name, 0)) < len(source_shuttle_cases):
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_source_shuttle_gate_count": count_name})
    for count_name in (
        "manifest_ref_count",
        "packet_hash_preserved_count",
        "source_clip_hash_preserved_count",
        "no_private_copy_rule_count",
    ):
        if int(source_shuttle_gate.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_source_shuttle_gate_count": count_name})
    if int(source_shuttle_gate.get("private_field_rehydration_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "source-shuttle gate private field rehydration count must be zero"})
    if int(source_shuttle_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "source-shuttle gate self-attestation authority must be zero"})
    if int(source_shuttle_gate.get("evaluator_authority_count", 0)) < len(source_shuttle_cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "source-shuttle gate evaluator authority count too low"})
    for flag_name in (
        "remote_reconciliation_claim_allowed",
        "external_clone_receipt_claim_allowed",
        "source_shuttle_authority_allowed",
        "source_shuttle_manifest_ref_public_remote_authority_allowed",
        "source_shuttle_private_field_rehydration_allowed",
        "hosted_public_claim_allowed",
        "public_remote_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
        "actual_execution_claim_allowed",
    ):
        if source_shuttle_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": f"source-shuttle reconciliation gate {flag_name} must be false"})

    authority = board.get("authority", {})
    for count_name in (
        "self_attestation_count",
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "nonzero_authority_count": count_name})
    if int(authority.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "evaluator authority count too low"})
    for forbidden in (
        "remote reconciliation to public remote authority",
        "remote reconciliation to hosted CI authority",
        "remote reconciliation to public release authority",
        "remote reconciliation to publication permission",
    ):
        if forbidden not in authority.get("forbidden_promotions", []):
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "missing_forbidden_promotion": forbidden})

    identity_case = next((case for case in cases if case.get("case_id") == "reconciliation_requires_remote_identity_alignment"), {})
    if int(identity_case.get("semantic_carryforward", {}).get("missing_field_count", 0)) < 6:
        failures.append({"case_id": "reconciliation_requires_remote_identity_alignment", "reason": "identity case must preserve missing remote fields"})
    if "hosted remote receipt skeleton proves public remote availability" not in identity_case.get("anti_claims", []):
        failures.append({"case_id": "reconciliation_requires_remote_identity_alignment", "reason": "missing hosted remote skeleton anti-claim"})
    publication_case = next((case for case in cases if case.get("case_id") == "reconciliation_requires_publication_gate_status"), {})
    if publication_case.get("restart_point") != "release/publication_gate.json::status":
        failures.append({"case_id": "reconciliation_requires_publication_gate_status", "reason": "publication case restart point must be publication gate status"})

    for grammar_case in grammar_replay_cases:
        case_id = grammar_case.get("case_id")
        carryforward = grammar_case.get("semantic_carryforward", {})
        if carryforward.get("upstream_hash_verified") is not True:
            failures.append({"case_id": case_id, "reason": "grammar replay reconciliation case must verify upstream hash"})
        if carryforward.get("remote_reconciliation_hides_grammar_failure") is not False:
            failures.append({"case_id": case_id, "reason": "remote reconciliation must not hide grammar failure"})
        if carryforward.get("remote_reconciliation_repairs_grammar_failure") is not False:
            failures.append({"case_id": case_id, "reason": "remote reconciliation must not repair grammar failure"})
        if grammar_case.get("outcome") != "blocked: grammar_replay_failure_cannot_be_hidden_by_remote_receipt_reconciliation":
            failures.append({"case_id": case_id, "reason": "unexpected grammar replay reconciliation outcome"})
        if "remote receipt reconciliation can hide failed grammar cases" not in grammar_case.get("anti_claims", []):
            failures.append({"case_id": case_id, "reason": "missing grammar replay reconciliation anti-claim"})
        if not str(grammar_case.get("restart_point", "")).startswith("microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json::"):
            failures.append({"case_id": case_id, "reason": "grammar replay reconciliation restart point must reference external clone receipt case"})

    for source_shuttle_case in source_shuttle_cases:
        case_id = source_shuttle_case.get("case_id")
        carryforward = source_shuttle_case.get("semantic_carryforward", {})
        if carryforward.get("upstream_hash_verified") is not True:
            failures.append({"case_id": case_id, "reason": "source-shuttle reconciliation case must verify upstream hash"})
        if carryforward.get("source_clip_hash_verified") is not True:
            failures.append({"case_id": case_id, "reason": "source-shuttle reconciliation case must verify source clip hash"})
        if carryforward.get("source_card_id") != "card.source_shuttle_manifest_website_boundary":
            failures.append({"case_id": case_id, "reason": "source-shuttle reconciliation case must preserve source card id"})
        for claim_name in (
            "source_shuttle_private_field_rehydration_allowed",
            "source_shuttle_manifest_ref_used_as_remote_reconciliation_authority",
            "source_shuttle_manifest_ref_used_as_public_remote_authority",
            "remote_reconciliation_promotes_source_shuttle_to_public_remote",
            "remote_reconciliation_rehydrates_source_shuttle_private_fields",
            "remote_reconciliation_uses_source_shuttle_as_hosted_public_evidence",
            "source_shuttle_actual_execution_authority_allowed",
        ):
            if carryforward.get(claim_name) is not False:
                failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
        for count_name in (
            "source_shuttle_manifest_ref_count",
            "source_shuttle_packet_hash_preserved_count",
            "source_shuttle_source_clip_hash_preserved_count",
            "source_shuttle_no_private_copy_rule_count",
        ):
            if int(carryforward.get(count_name, 0)) < 1:
                failures.append({"case_id": case_id, "missing_source_shuttle_semantic_count": count_name})
        if source_shuttle_case.get("outcome") != "blocked: source_shuttle_external_clone_receipt_cannot_become_remote_reconciliation_authority":
            failures.append({"case_id": case_id, "reason": "unexpected source-shuttle reconciliation outcome"})
        if "remote receipt reconciliation promotes source-shuttle refs to public remote proof" not in source_shuttle_case.get("anti_claims", []):
            failures.append({"case_id": case_id, "reason": "missing source-shuttle reconciliation anti-claim"})
        if not str(source_shuttle_case.get("restart_point", "")).startswith("microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json::"):
            failures.append({"case_id": case_id, "reason": "source-shuttle reconciliation restart point must reference external clone receipt case"})

    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json", "reason": "reconciliation case must be an object"})
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip", "")
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "source_clip_hash mismatch"})
        carryforward = case.get("semantic_carryforward", {})
        if carryforward.get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "semantic carryforward must declare projection_not_authority"})
        for claim_name in (
            "remote_receipt_reconciled",
            "external_clone_reconciled",
            "hosted_ci_claimed",
            "package_export_claimed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if carryforward.get(claim_name) is not False:
                failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "missing repair route"})
        if not case.get("restart_point"):
            failures.append({"case_id": case_id, "reason": "missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "missing teaching rule"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "missing anti-claims"})
        if not str(case.get("outcome", "")).startswith("blocked:"):
            failures.append({"case_id": case_id, "reason": "reconciliation case must block the attempted promotion"})
        flags = case.get("authority_flags", {})
        for flag_name, flag_value in flags.items():
            if flag_value is not False:
                failures.append({"case_id": case_id, "reason": f"authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    required_receipt_refs = {
        "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json",
        "microcosms/hosted_public_remote_receipt_reconciliation/README.md",
        "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
        "microcosms/external_public_clone_probe_receipt/receipt.json",
        "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
        "release/publication_gate.json",
        "registry/release_candidates.json",
    }
    evidence_refs = set(receipt.get("evidence_refs", []))
    missing_receipt_refs = sorted(required_receipt_refs - evidence_refs)
    if missing_receipt_refs:
        failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json", "missing_evidence_refs": missing_receipt_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-hosted-public-remote-receipt-reconciliation-specimen --root . --write-receipt",
        "hosted remote receipt skeleton",
        "grammar replay",
        "source-shuttle",
        "source capsules",
        "not public remote availability",
        "publication permission",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/hosted_public_remote_receipt_reconciliation/README.md", "missing_text": required_text})
    return failures


def _actual_public_remote_clone_execution_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "actual_public_remote_clone_execution" / "execution_board.json"
    receipt_path = root / "microcosms" / "actual_public_remote_clone_execution" / "receipt.json"
    readme_path = root / "microcosms" / "actual_public_remote_clone_execution" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "missing execution board"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    receipt = load_json(receipt_path)
    if board.get("schema_version") != "actual_public_remote_clone_execution_specimen_v0":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "unexpected schema"})
    if board.get("microcosm_id") != "actual_public_remote_clone_execution":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "unexpected microcosm_id"})
    if board.get("candidate_id") != "actual_public_remote_clone_execution_microcosm":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "unexpected candidate_id"})
    if board.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution board must declare projection_not_authority"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution board must not imply public release readiness"})

    cases = board.get("mechanism", {}).get("cases", [])
    if not isinstance(cases, list) or len(cases) < 5:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "expected at least five execution cases"})
        cases = []
    required_case_ids = {
        "execution_requires_public_remote_identity_receipt",
        "execution_requires_credential_free_clone_transcript",
        "execution_requires_commit_workflow_and_artifact_binding",
        "execution_requires_observer_environment_boundary",
        "execution_cannot_promote_package_or_publication",
    }
    observed_case_ids = {case.get("case_id") for case in cases if isinstance(case, dict)}
    missing_case_ids = sorted(required_case_ids - observed_case_ids)
    if missing_case_ids:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "missing_case_ids": missing_case_ids})
    grammar_case_prefix = (
        "actual_execution_replays_remote_reconciliation_replays_clone_probe_receipt_replays_"
        "grammar_replay_site_projection_"
    )
    source_shuttle_case_prefix = (
        "actual_execution_replays_remote_reconciliation_replays_clone_probe_receipt_replays_"
        "site_projection_source_shuttle_"
    )
    grammar_replay_cases = [
        case
        for case in cases
        if isinstance(case, dict)
        and str(case.get("case_id", "")).startswith(grammar_case_prefix)
    ]
    if len(grammar_replay_cases) < 5:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "expected at least five grammar replay actual execution cases"})
    source_shuttle_cases = [
        case
        for case in cases
        if isinstance(case, dict)
        and str(case.get("case_id", "")).startswith(source_shuttle_case_prefix)
    ]
    if len(source_shuttle_cases) < 3:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "expected at least three source-shuttle actual execution cases"})

    status = board.get("status", {})
    if int(status.get("case_count", 0)) != len(cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "case count mismatch"})
    for count_name in (
        "source_capsule_count",
        "capsule_count",
        "semantic_carryforward_count",
        "failure_replay_count",
        "repair_route_count",
        "teaching_rule_count",
        "claim_boundary_count",
        "actual_public_remote_clone_execution_case_count",
    ):
        if int(status.get(count_name, 0)) < len(cases):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "missing_status_count": count_name})
    if int(status.get("grammar_replay_actual_execution_case_count", 0)) != len(grammar_replay_cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "grammar replay actual execution count mismatch"})
    for count_name in (
        "grammar_replay_actual_execution_source_capsule_count",
        "grammar_replay_actual_execution_semantic_carryforward_count",
        "grammar_replay_actual_execution_failure_replay_count",
        "grammar_replay_actual_execution_repair_route_count",
        "grammar_replay_actual_execution_teaching_rule_count",
        "grammar_replay_actual_execution_hash_verified_count",
    ):
        if int(status.get(count_name, 0)) < len(grammar_replay_cases):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "missing_status_count": count_name})
    for count_name in (
        "grammar_replay_actual_execution_self_attestation_authority_count",
        "grammar_replay_actual_execution_public_release_claim_count",
        "grammar_replay_actual_execution_publication_claim_count",
        "grammar_replay_actual_execution_private_root_equivalence_claim_count",
        "grammar_replay_actual_execution_benchmark_win_claim_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "nonzero_grammar_replay_count": count_name})
    if int(status.get("source_shuttle_actual_execution_case_count", 0)) != len(source_shuttle_cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "source-shuttle actual execution count mismatch"})
    for count_name in (
        "source_shuttle_actual_execution_source_capsule_count",
        "source_shuttle_actual_execution_semantic_carryforward_count",
        "source_shuttle_actual_execution_failure_replay_count",
        "source_shuttle_actual_execution_repair_route_count",
        "source_shuttle_actual_execution_teaching_rule_count",
        "source_shuttle_actual_execution_hash_verified_count",
        "source_shuttle_actual_execution_source_clip_hash_verified_count",
    ):
        if int(status.get(count_name, 0)) < len(source_shuttle_cases):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "missing_status_count": count_name})
    for count_name in (
        "source_shuttle_actual_execution_manifest_ref_count",
        "source_shuttle_actual_execution_packet_hash_preserved_count",
        "source_shuttle_actual_execution_source_clip_hash_preserved_count",
        "source_shuttle_actual_execution_no_private_copy_rule_count",
    ):
        if int(status.get(count_name, 0)) < len(source_shuttle_cases):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "missing_source_shuttle_count": count_name})
    for count_name in (
        "source_shuttle_actual_execution_private_field_rehydration_count",
        "source_shuttle_actual_execution_self_attestation_authority_count",
        "source_shuttle_actual_execution_public_release_claim_count",
        "source_shuttle_actual_execution_publication_claim_count",
        "source_shuttle_actual_execution_private_root_equivalence_claim_count",
        "source_shuttle_actual_execution_benchmark_win_claim_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "nonzero_source_shuttle_count": count_name})
    if int(status.get("actual_public_remote_clone_execution_required_field_count", 0)) < 17:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution receipt must preserve required fields"})
    if int(status.get("actual_public_remote_clone_execution_missing_field_count", -1)) != int(status.get("actual_public_remote_clone_execution_required_field_count", 0)):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "all execution fields must remain missing in fail-closed fixture"})
    if int(status.get("observed_execution_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "observed execution refs must be zero"})
    if int(status.get("execution_attempt_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution attempt count must be zero"})
    if int(status.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution board missing_ref_count must be zero"})
    if status.get("validation_status") != "ok":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "validation_status must be ok"})
    if status.get("next_owner") != "operator_supplied_public_remote_clone_execution_receipt":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "unexpected next_owner"})

    gate = board.get("actual_public_remote_clone_execution_gate", {})
    if gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution gate must stay fail-closed"})
    if gate.get("missing_fields") != gate.get("required_fields"):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution gate must keep all required fields missing in fail-closed fixture"})
    if gate.get("observed_execution_refs") != []:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution gate must record zero observed executions"})
    if int(gate.get("execution_attempt_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution gate must not record a local execution attempt"})
    if int(gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution gate self-attestation authority must be zero"})
    if int(gate.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution gate evaluator authority count too low"})
    for flag_name in (
        "actual_public_remote_claim_allowed",
        "credential_free_clone_claim_allowed",
        "hosted_ci_claim_allowed",
        "package_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": f"execution gate {flag_name} must be false"})

    grammar_gate = board.get("grammar_replay_actual_remote_clone_execution_gate", {})
    if grammar_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "grammar replay actual execution gate must stay fail-closed"})
    if int(grammar_gate.get("source_case_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "grammar replay actual execution gate source case count too low"})
    if int(grammar_gate.get("hash_verified_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "grammar replay actual execution gate hash verified count too low"})
    if int(grammar_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "grammar replay actual execution gate self-attestation authority must be zero"})
    if int(grammar_gate.get("evaluator_authority_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "grammar replay actual execution gate evaluator authority count too low"})
    for flag_name in (
        "actual_execution_claim_allowed",
        "actual_execution_hides_grammar_failure_allowed",
        "actual_execution_repairs_grammar_failure_allowed",
        "grammar_replay_authority_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if grammar_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": f"grammar replay actual execution gate {flag_name} must be false"})

    source_shuttle_gate = board.get("source_shuttle_actual_remote_clone_execution_gate", {})
    if source_shuttle_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "source-shuttle actual execution gate must stay fail-closed"})
    if int(source_shuttle_gate.get("source_case_count", 0)) < len(source_shuttle_cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "source-shuttle actual execution gate source case count too low"})
    for count_name in (
        "hash_verified_count",
        "source_clip_hash_verified_count",
        "manifest_ref_count",
        "packet_hash_preserved_count",
        "source_clip_hash_preserved_count",
        "no_private_copy_rule_count",
    ):
        if int(source_shuttle_gate.get(count_name, 0)) < len(source_shuttle_cases):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "source_shuttle_gate_count_too_low": count_name})
    if int(source_shuttle_gate.get("private_field_rehydration_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "source-shuttle actual execution gate private-field rehydration must be zero"})
    if int(source_shuttle_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "source-shuttle actual execution gate self-attestation authority must be zero"})
    if int(source_shuttle_gate.get("evaluator_authority_count", 0)) < len(source_shuttle_cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "source-shuttle actual execution gate evaluator authority count too low"})
    for flag_name in (
        "actual_execution_claim_allowed",
        "actual_execution_uses_source_shuttle_as_clone_evidence_allowed",
        "source_shuttle_authority_allowed",
        "source_shuttle_manifest_ref_public_remote_authority_allowed",
        "source_shuttle_manifest_ref_actual_execution_authority_allowed",
        "source_shuttle_private_field_rehydration_allowed",
        "hosted_public_claim_allowed",
        "public_remote_claim_allowed",
        "credential_free_clone_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if source_shuttle_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": f"source-shuttle actual execution gate {flag_name} must be false"})

    authority = board.get("authority", {})
    for count_name in (
        "self_attestation_count",
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "nonzero_authority_count": count_name})
    if int(authority.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "evaluator authority count too low"})
    for forbidden in (
        "execution contract to public remote authority",
        "execution contract to credential-free clone authority",
        "execution contract to hosted CI authority",
        "execution contract to package export authority",
        "execution contract to public release authority",
        "execution contract to publication permission",
    ):
        if forbidden not in authority.get("forbidden_promotions", []):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "missing_forbidden_promotion": forbidden})

    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/execution_board.json", "reason": "execution case must be an object"})
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip", "")
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "source_clip_hash mismatch"})
        carryforward = case.get("semantic_carryforward", {})
        if carryforward.get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "semantic carryforward must declare projection_not_authority"})
        for claim_name in (
            "public_remote_observed",
            "credential_free_clone_observed",
            "hosted_workflow_observed",
            "package_export_claimed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if carryforward.get(claim_name) is not False:
                failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
        if int(carryforward.get("observed_execution_ref_count", -1)) != 0:
            failures.append({"case_id": case_id, "reason": "case observed execution refs must be zero"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "missing repair route"})
        if not case.get("restart_point"):
            failures.append({"case_id": case_id, "reason": "missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "missing teaching rule"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "missing anti-claims"})
        if not str(case.get("outcome", "")).startswith("blocked:"):
            failures.append({"case_id": case_id, "reason": "execution case must block the attempted promotion"})
        if isinstance(case_id, str) and case_id.startswith(grammar_case_prefix):
            if case.get("outcome") != "blocked: grammar_replay_failure_cannot_be_hidden_by_actual_public_remote_clone_execution":
                failures.append({"case_id": case_id, "reason": "grammar replay actual execution case outcome mismatch"})
            if carryforward.get("upstream_hash_verified") is not True:
                failures.append({"case_id": case_id, "reason": "grammar replay actual execution source hash was not verified"})
            for claim_name in (
                "actual_execution_hides_grammar_failure",
                "actual_execution_repairs_grammar_failure",
                "grammar_replay_used_as_authority",
                "actual_execution_observes_public_remote",
                "actual_execution_observes_clone",
            ):
                if carryforward.get(claim_name) is not False:
                    failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
            if not str(case.get("restart_point", "")).startswith("microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json::remote_reconciliation_replays_"):
                failures.append({"case_id": case_id, "reason": "grammar replay actual execution restart point must point to remote reconciliation case"})
            if "actual public remote clone execution can hide failed grammar cases" not in case.get("anti_claims", []):
                failures.append({"case_id": case_id, "reason": "missing grammar replay actual execution anti-claim"})
        if isinstance(case_id, str) and case_id.startswith(source_shuttle_case_prefix):
            if case.get("outcome") != "blocked: source_shuttle_remote_reconciliation_cannot_become_actual_public_remote_clone_execution_authority":
                failures.append({"case_id": case_id, "reason": "source-shuttle actual execution case outcome mismatch"})
            for claim_name in ("upstream_hash_verified", "source_clip_hash_verified"):
                if carryforward.get(claim_name) is not True:
                    failures.append({"case_id": case_id, "reason": f"source-shuttle actual execution {claim_name} must be true"})
            for count_name in (
                "source_shuttle_manifest_ref_count",
                "source_shuttle_packet_hash_preserved_count",
                "source_shuttle_source_clip_hash_preserved_count",
                "source_shuttle_no_private_copy_rule_count",
            ):
                if int(carryforward.get(count_name, 0)) < 1:
                    failures.append({"case_id": case_id, "reason": f"source-shuttle actual execution {count_name} must be positive"})
            for claim_name in (
                "source_shuttle_private_field_rehydration_allowed",
                "source_shuttle_manifest_ref_used_as_actual_execution_authority",
                "source_shuttle_manifest_ref_used_as_public_remote_authority",
                "source_shuttle_actual_execution_authority_allowed",
                "actual_execution_promotes_source_shuttle_to_public_remote",
                "actual_execution_rehydrates_source_shuttle_private_fields",
                "actual_execution_uses_source_shuttle_as_hosted_public_evidence",
                "actual_execution_uses_source_shuttle_as_clone_evidence",
            ):
                if carryforward.get(claim_name) is not False:
                    failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
            if not str(case.get("restart_point", "")).startswith("microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json::remote_reconciliation_replays_"):
                failures.append({"case_id": case_id, "reason": "source-shuttle actual execution restart point must point to remote reconciliation case"})
            if "actual public remote clone execution promotes source-shuttle refs to public remote proof" not in case.get("anti_claims", []):
                failures.append({"case_id": case_id, "reason": "missing source-shuttle actual execution anti-claim"})
        flags = case.get("authority_flags", {})
        for flag_name, flag_value in flags.items():
            if flag_value is not False:
                failures.append({"case_id": case_id, "reason": f"authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    required_receipt_refs = {
        "microcosms/actual_public_remote_clone_execution/execution_board.json",
        "microcosms/actual_public_remote_clone_execution/README.md",
        "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json",
        "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json",
        "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
        "microcosms/external_public_clone_probe_receipt/receipt.json",
        "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
        "release/publication_gate.json",
        "registry/release_candidates.json",
    }
    evidence_refs = set(receipt.get("evidence_refs", []))
    missing_receipt_refs = sorted(required_receipt_refs - evidence_refs)
    if missing_receipt_refs:
        failures.append({"path": "microcosms/actual_public_remote_clone_execution/receipt.json", "missing_evidence_refs": missing_receipt_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-actual-public-remote-clone-execution-specimen --root . --write-receipt",
        "actual public remote clone execution",
        "source capsules",
        "grammar replay",
        "source-shuttle",
        "not public remote availability",
        "publication permission",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/actual_public_remote_clone_execution/README.md", "missing_text": required_text})
    return failures


def _operator_public_remote_clone_execution_receipt_failures(root: Path) -> list[dict[str, Any]]:
    board_path = root / "microcosms" / "operator_public_remote_clone_execution_receipt" / "receipt_intake_board.json"
    template_path = root / "microcosms" / "operator_public_remote_clone_execution_receipt" / "operator_receipt_template.json"
    replay_fixtures_path = root / "microcosms" / "operator_public_remote_clone_execution_receipt" / "operator_receipt_replay_fixtures.json"
    receipt_path = root / "microcosms" / "operator_public_remote_clone_execution_receipt" / "receipt.json"
    readme_path = root / "microcosms" / "operator_public_remote_clone_execution_receipt" / "README.md"
    failures: list[dict[str, Any]] = []
    if not board_path.exists():
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "missing receipt-intake board"})
    if not template_path.exists():
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json", "reason": "missing operator receipt template"})
    if not replay_fixtures_path.exists():
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json", "reason": "missing operator receipt replay fixtures"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    board = load_json(board_path)
    template = load_json(template_path)
    replay_fixtures = load_json(replay_fixtures_path)
    receipt = load_json(receipt_path)
    if board.get("schema_version") != "operator_public_remote_clone_execution_receipt_specimen_v0":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "unexpected schema"})
    if board.get("microcosm_id") != "operator_public_remote_clone_execution_receipt":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "unexpected microcosm_id"})
    if board.get("candidate_id") != "operator_public_remote_clone_execution_receipt_microcosm":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "unexpected candidate_id"})
    if board.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "intake board must declare projection_not_authority"})
    if "public-release-ready" in json.dumps(board).lower():
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "intake board must not imply public release readiness"})

    if template.get("schema_version") != "operator_public_remote_clone_execution_receipt_v0":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json", "reason": "unexpected template schema"})
    if len(template.get("field_values", {})) < 17:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json", "reason": "template must preserve outside-world receipt fields"})
    if not template.get("source_artifact_digests"):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json", "reason": "template must bind source artifact digests"})
    for count_name in (
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(template.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json", "nonzero_template_count": count_name})

    if replay_fixtures.get("schema_version") != "operator_receipt_replay_fixtures_v0":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json", "reason": "unexpected replay fixture schema"})
    if replay_fixtures.get("authority_posture") != "synthetic_replay_fixtures_not_operator_evidence":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json", "reason": "replay fixtures must not become operator evidence"})
    fixtures = replay_fixtures.get("fixtures", [])
    if not isinstance(fixtures, list) or len(fixtures) < 4:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json", "reason": "expected at least four replay fixtures"})
        fixtures = []
    fixture_ids = {fixture.get("case_id") for fixture in fixtures if isinstance(fixture, dict)}
    for fixture_id in (
        "synthetic_complete_schema_pass_not_authority",
        "synthetic_source_digest_mismatch_blocks_replay",
        "synthetic_private_root_evidence_blocks_replay",
        "synthetic_self_promoting_public_release_blocks_replay",
    ):
        if fixture_id not in fixture_ids:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json", "missing_fixture_id": fixture_id})

    cases = board.get("mechanism", {}).get("cases", [])
    if not isinstance(cases, list) or len(cases) < 5:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected at least five receipt-intake cases"})
        cases = []
    required_case_ids = {
        "intake_requires_complete_operator_receipt_schema",
        "intake_requires_source_digest_binding",
        "intake_requires_credential_free_observer_boundary",
        "intake_requires_public_safe_redaction",
        "intake_cannot_promote_package_or_publication",
    }
    observed_case_ids = {case.get("case_id") for case in cases if isinstance(case, dict)}
    missing_case_ids = sorted(required_case_ids - observed_case_ids)
    if missing_case_ids:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "missing_case_ids": missing_case_ids})
    grammar_replay_cases = [
        case
        for case in cases
        if isinstance(case, dict) and str(case.get("case_id", "")).startswith("operator_receipt_intake_replays_")
    ]
    if len(grammar_replay_cases) < 5:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected grammar replay operator receipt intake cases"})

    status = board.get("status", {})
    if int(status.get("case_count", 0)) != len(cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "case count mismatch"})
    for count_name in (
        "source_capsule_count",
        "capsule_count",
        "semantic_carryforward_count",
        "failure_replay_count",
        "repair_route_count",
        "teaching_rule_count",
        "claim_boundary_count",
        "operator_public_remote_clone_execution_receipt_case_count",
    ):
        if int(status.get(count_name, 0)) < len(cases):
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "missing_status_count": count_name})
    required_field_count = int(status.get("operator_public_remote_clone_execution_receipt_required_field_count", 0))
    if required_field_count < 17:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "operator receipt required fields must be preserved"})
    if int(status.get("operator_public_remote_clone_execution_receipt_missing_field_count", -1)) != required_field_count:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "all operator receipt fields must remain missing in fail-closed fixture"})
    for count_name in (
        "observed_operator_receipt_ref_count",
        "accepted_operator_receipt_count",
        "source_digest_mismatch_count",
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
        "missing_ref_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "nonzero_status_count": count_name})
    if int(status.get("operator_receipt_template_field_count", 0)) != required_field_count:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "template field count must match required field count"})
    if int(status.get("operator_receipt_replay_case_count", 0)) < 4:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected replay lab cases"})
    if int(status.get("operator_receipt_replay_fail_closed_count", 0)) < 3:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected fail-closed replay cases"})
    if int(status.get("operator_receipt_replay_authority_violation_count", 0)) < 1:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected self-promoting receipt replay block"})
    if int(status.get("operator_receipt_replay_source_digest_mismatch_count", 0)) < 1:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected source-digest mismatch replay block"})
    if int(status.get("synthetic_operator_receipt_schema_pass_count", 0)) != 1:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected exactly one synthetic schema pass"})
    if int(status.get("grammar_replay_operator_receipt_intake_case_count", 0)) != len(grammar_replay_cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator intake case count mismatch"})
    for count_name in (
        "grammar_replay_operator_receipt_intake_source_capsule_count",
        "grammar_replay_operator_receipt_intake_semantic_carryforward_count",
        "grammar_replay_operator_receipt_intake_failure_replay_count",
        "grammar_replay_operator_receipt_intake_repair_route_count",
        "grammar_replay_operator_receipt_intake_teaching_rule_count",
        "grammar_replay_operator_receipt_intake_hash_verified_count",
    ):
        if int(status.get(count_name, 0)) < len(grammar_replay_cases):
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "missing_grammar_status_count": count_name})
    if int(status.get("grammar_replay_operator_receipt_intake_blocked_claim_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator intake blocked claim count too low"})
    for count_name in (
        "grammar_replay_operator_receipt_intake_self_attestation_authority_count",
        "grammar_replay_operator_receipt_intake_public_release_claim_count",
        "grammar_replay_operator_receipt_intake_publication_claim_count",
        "grammar_replay_operator_receipt_intake_private_root_equivalence_claim_count",
        "grammar_replay_operator_receipt_intake_benchmark_win_claim_count",
    ):
        if int(status.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "nonzero_grammar_status_count": count_name})
    if status.get("validation_status") != "ok":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "validation_status must be ok"})
    if status.get("next_owner") != "operator_supplied_public_remote_clone_execution_receipt":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "unexpected next_owner"})

    gate = board.get("operator_receipt_intake_gate", {})
    if gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "operator receipt gate must stay fail-closed"})
    if gate.get("missing_fields") != gate.get("required_fields"):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "operator receipt gate must keep all required fields missing in fail-closed fixture"})
    if gate.get("operator_receipt_present") is not False or gate.get("accepted_for_local_evaluation") is not False:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "fixture must not include or accept an operator receipt"})
    if int(gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "operator receipt gate self-attestation authority must be zero"})
    if int(gate.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "operator receipt gate evaluator authority count too low"})
    for flag_name in (
        "actual_public_remote_claim_allowed",
        "credential_free_clone_claim_allowed",
        "hosted_ci_claim_allowed",
        "package_export_claim_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
        "self_attestation_used_as_authority",
    ):
        if gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": f"operator receipt gate {flag_name} must be false"})

    grammar_gate = board.get("grammar_replay_operator_receipt_intake_gate", {})
    if grammar_gate.get("status") != "fail_closed":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator receipt gate must stay fail-closed"})
    if grammar_gate.get("source_gate_ref") != "microcosms/actual_public_remote_clone_execution/execution_board.json::grammar_replay_actual_remote_clone_execution_gate":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator receipt gate must point at actual execution grammar gate"})
    if int(grammar_gate.get("source_case_count", 0)) != len(grammar_replay_cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator receipt gate source count mismatch"})
    if int(grammar_gate.get("hash_verified_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator receipt gate hash verification too low"})
    if int(grammar_gate.get("self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator receipt gate self-attestation authority must be zero"})
    if int(grammar_gate.get("evaluator_authority_count", 0)) < len(grammar_replay_cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "grammar replay operator receipt gate evaluator authority count too low"})
    for flag_name in (
        "operator_receipt_intake_hides_grammar_failure_allowed",
        "operator_receipt_intake_repairs_grammar_failure_allowed",
        "grammar_replay_authority_allowed",
        "public_release_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "benchmark_win_claim_allowed",
    ):
        if grammar_gate.get(flag_name) is not False:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": f"grammar replay operator receipt gate {flag_name} must be false"})
    for anti_claim in (
        "operator receipt intake can hide failed grammar cases",
        "operator receipt intake repairs upstream grammar failures",
        "operator receipt intake turns grammar replay into publication permission",
    ):
        if anti_claim not in grammar_gate.get("anti_claims", []):
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "missing_grammar_gate_anti_claim": anti_claim})

    replay_lab = board.get("operator_receipt_replay_lab", {})
    if replay_lab.get("schema_version") != "operator_receipt_replay_lab_v0":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "missing replay lab"})
    if replay_lab.get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "replay lab must declare projection_not_authority"})
    if replay_lab.get("fixture_ref") != "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "unexpected replay fixture ref"})
    replay_results = replay_lab.get("replay_results", [])
    if not isinstance(replay_results, list) or len(replay_results) < 4:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "expected replay results"})
        replay_results = []
    replay_by_id = {result.get("case_id"): result for result in replay_results if isinstance(result, dict)}
    complete_replay = replay_by_id.get("synthetic_complete_schema_pass_not_authority", {})
    if complete_replay.get("accepted_for_local_evaluation") is not True:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "complete synthetic replay should pass local schema evaluation"})
    if complete_replay.get("synthetic_fixture_not_operator_evidence") is not True:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "complete replay must remain synthetic"})
    self_promoting_replay = replay_by_id.get("synthetic_self_promoting_public_release_blocks_replay", {})
    if self_promoting_replay.get("accepted_for_local_evaluation") is not False:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "self-promoting replay must fail closed"})
    if int(self_promoting_replay.get("authority_claim_violation_count", 0)) < 1:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "self-promoting replay must expose authority violation"})
    digest_replay = replay_by_id.get("synthetic_source_digest_mismatch_blocks_replay", {})
    if int(digest_replay.get("source_digest_mismatch_count", 0)) < 1:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "digest mismatch replay must expose mismatch"})
    private_root_replay = replay_by_id.get("synthetic_private_root_evidence_blocks_replay", {})
    if private_root_replay.get("private_root_evidence_included") is not True or private_root_replay.get("accepted_for_local_evaluation") is not False:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "private-root replay must fail closed"})
    for count_name in (
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
        "accepted_real_operator_receipt_count",
    ):
        if int(replay_lab.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "nonzero_replay_lab_count": count_name})
    for result in replay_results:
        if not isinstance(result, dict):
            continue
        if result.get("public_release_claim_allowed") is not False or result.get("publication_permission_claim_allowed") is not False:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "replay result attempted public/publication authority"})
        if not result.get("repair_route"):
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "replay result missing repair route"})
        for flag_name, flag_value in result.get("authority_flags", {}).items():
            if flag_value is not False:
                failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": f"replay authority flag {flag_name} must be false"})

    authority = board.get("authority", {})
    if authority.get("authority_class") != "operator_receipt_intake_evaluator_only":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "unexpected authority class"})
    for count_name in (
        "self_attestation_count",
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "nonzero_authority_count": count_name})
    if int(authority.get("evaluator_authority_count", 0)) < len(cases):
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "evaluator authority count too low"})
    for forbidden in (
        "operator receipt intake to public remote authority",
        "operator receipt intake to package export authority",
        "operator receipt intake to public release authority",
        "operator receipt intake to publication permission",
    ):
        if forbidden not in authority.get("forbidden_promotions", []):
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "missing_forbidden_promotion": forbidden})

    for case in cases:
        if not isinstance(case, dict):
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json", "reason": "receipt-intake case must be an object"})
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip", "")
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "source_clip_hash mismatch"})
        carryforward = case.get("semantic_carryforward", {})
        if carryforward.get("projection_not_authority") is not True:
            failures.append({"case_id": case_id, "reason": "semantic carryforward must declare projection_not_authority"})
        if carryforward.get("operator_receipt_present") is not False or carryforward.get("accepted_for_local_evaluation") is not False:
            failures.append({"case_id": case_id, "reason": "fixture cases must not include or accept an operator receipt"})
        for claim_name in (
            "public_remote_observed",
            "credential_free_clone_observed",
            "hosted_workflow_observed",
            "package_export_claimed",
            "public_release_claimed",
            "publication_claimed",
            "private_root_equivalence_claimed",
            "benchmark_win_claimed",
        ):
            if carryforward.get(claim_name) is not False:
                failures.append({"case_id": case_id, "reason": f"semantic carryforward {claim_name} must be false"})
        if not case.get("repair_route"):
            failures.append({"case_id": case_id, "reason": "missing repair route"})
        if not case.get("restart_point"):
            failures.append({"case_id": case_id, "reason": "missing restart point"})
        if not case.get("teaching_rule"):
            failures.append({"case_id": case_id, "reason": "missing teaching rule"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "missing anti-claims"})
        if not str(case.get("outcome", "")).startswith("blocked:"):
            failures.append({"case_id": case_id, "reason": "receipt-intake case must block the attempted promotion"})
        if str(case_id).startswith("operator_receipt_intake_replays_"):
            if carryforward.get("upstream_hash_verified") is not True:
                failures.append({"case_id": case_id, "reason": "grammar replay operator intake case must verify upstream source hash"})
            if carryforward.get("operator_receipt_intake_hides_grammar_failure") is not False:
                failures.append({"case_id": case_id, "reason": "operator receipt intake must not hide grammar failure"})
            if carryforward.get("operator_receipt_intake_repairs_grammar_failure") is not False:
                failures.append({"case_id": case_id, "reason": "operator receipt intake must not repair grammar failure"})
            if carryforward.get("grammar_replay_used_as_authority") is not False:
                failures.append({"case_id": case_id, "reason": "grammar replay must not become receipt authority"})
            if case.get("outcome") != "blocked: grammar_replay_failure_cannot_be_hidden_by_operator_receipt_intake":
                failures.append({"case_id": case_id, "reason": "unexpected grammar replay operator intake outcome"})
            if not str(case.get("restart_point", "")).startswith("microcosms/actual_public_remote_clone_execution/execution_board.json::actual_execution_replays_"):
                failures.append({"case_id": case_id, "reason": "grammar replay operator intake restart point must return to actual execution case"})
        flags = case.get("authority_flags", {})
        for flag_name, flag_value in flags.items():
            if flag_value is not False:
                failures.append({"case_id": case_id, "reason": f"authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    required_receipt_refs = {
        "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json",
        "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json",
        "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json",
        "microcosms/operator_public_remote_clone_execution_receipt/README.md",
        "microcosms/actual_public_remote_clone_execution/execution_board.json",
        "microcosms/actual_public_remote_clone_execution/receipt.json",
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
        "release/publication_gate.json",
        "registry/release_candidates.json",
    }
    evidence_refs = set(receipt.get("evidence_refs", []))
    missing_receipt_refs = sorted(required_receipt_refs - evidence_refs)
    if missing_receipt_refs:
        failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt.json", "missing_evidence_refs": missing_receipt_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-operator-public-remote-clone-execution-receipt-specimen --root . --write-receipt",
        "receipt-intake board",
        "source capsules",
        "synthetic replay fixtures",
        "grammar replay failures",
        "not public remote availability",
        "publication permission",
        "fail-closed",
        "not operator evidence",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/operator_public_remote_clone_execution_receipt/README.md", "missing_text": required_text})
    return failures


def _public_release_package_manifest_gate_failures(root: Path) -> list[dict[str, Any]]:
    manifest_path = root / "microcosms" / "public_release_package_manifest_gate" / "package_manifest.json"
    handshake_path = root / "microcosms" / "public_release_package_manifest_gate" / "release_authority_handshake.json"
    handoff_path = root / "microcosms" / "public_release_package_manifest_gate" / "public_projection_handoff.json"
    promotion_path = root / "microcosms" / "public_release_package_manifest_gate" / "package_promotion_gate.json"
    bridge_path = root / "microcosms" / "public_release_package_manifest_gate" / "recipient_packet_manifest_bridge.json"
    digest_bridge_path = root / "microcosms" / "public_release_package_manifest_gate" / "artifact_digest_requirement_bridge.json"
    receipt_path = root / "microcosms" / "public_release_package_manifest_gate" / "receipt.json"
    readme_path = root / "microcosms" / "public_release_package_manifest_gate" / "README.md"
    failures: list[dict[str, Any]] = []
    if not manifest_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing package manifest"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/receipt.json", "reason": "missing specimen receipt"})
    if not handshake_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "missing release authority handshake"})
    if not handoff_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "missing public projection handoff"})
    if not promotion_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "missing package promotion gate"})
    if not bridge_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "missing recipient packet manifest bridge"})
    if not digest_bridge_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "missing artifact digest requirement bridge"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    manifest = load_json(manifest_path)
    handshake = load_json(handshake_path)
    handoff = load_json(handoff_path)
    promotion = load_json(promotion_path)
    bridge = load_json(bridge_path)
    digest_bridge = load_json(digest_bridge_path)
    receipt = load_json(receipt_path)
    artifact_witness_path = root / "microcosms" / "release_artifact_integrity_witness" / "integrity_witness.json"
    artifact_witness = load_json(artifact_witness_path) if artifact_witness_path.exists() else {}
    redacted_draft_path = root / "microcosms" / "recipient_review_route_gate" / "redacted_recipient_packet_draft.json"
    redacted_draft = load_json(redacted_draft_path) if redacted_draft_path.exists() else {}
    quality_delta_board_path = root / "microcosms" / "specimen_suite" / "quality_delta_board.json"
    quality_delta_board = load_json(quality_delta_board_path) if quality_delta_board_path.exists() else {}
    current_quality_summary = quality_delta_board.get("summary", {}) if isinstance(quality_delta_board, dict) else {}
    if manifest.get("specimen_id") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "unexpected specimen_id"})
    if manifest.get("authority_posture") != "public_safe_package_manifest_gate_not_export_or_publication_authority":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "unexpected authority posture"})
    if manifest.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(manifest).lower():
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "package manifest must not imply public release readiness"})

    summary = manifest.get("summary", {})
    rows = manifest.get("package_rows", [])
    if not isinstance(rows, list) or len(rows) < 10:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "expected at least ten package rows"})
        rows = []
    if int(summary.get("package_row_count", 0)) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "summary package_row_count mismatch"})
    if int(summary.get("allow_private_review_count", 0)) < 3:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "allow_private_review_count"})
    if int(summary.get("block_count", 0)) < 7:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "block_count"})
    for count_name in (
        "public_export_without_publication_toggle_block_count",
        "package_manifest_row_missing_block_count",
        "registry_candidate_omission_block_count",
        "receipt_dependency_missing_or_stale_block_count",
        "hosted_public_boundary_missing_block_count",
        "rights_citation_disclosure_boundary_missing_block_count",
        "private_root_or_raw_seed_inclusion_block_count",
    ):
        if int(summary.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": count_name})
    if int(summary.get("receipt_ref_count", 0)) < len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("validator_ref_count", 0)) < len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "validator_ref_count"})
    if summary.get("release_root_compiler_validator_ref") != "validator.release_root_compiler":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing release root compiler validator ref"})
    if summary.get("release_root_compiler_status") != "pass":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "release root compiler gate must pass"})
    for count_name in (
        "release_root_artifact_ref_count",
        "release_root_branch_count",
        "release_root_mission_thread_count",
        "release_root_std_python_scanned_count",
    ):
        if int(summary.get(count_name, 0)) < 1:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": count_name})
    for count_name in (
        "release_root_missing_ref_count",
        "release_root_std_python_blocker_count",
        "release_root_authority_collapse_count",
        "release_root_projection_authority_violation_count",
        "release_root_validation_failure_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": count_name})
    if int(summary.get("artifact_manifest_row_count", 0)) < 60:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "artifact manifest snapshot is unexpectedly small"})
    if int(summary.get("registry_candidate_count", 0)) < 18:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "registry candidate snapshot is unexpectedly small"})
    for count_name in (
        "public_export_claim_count",
        "public_release_claim_count",
        "publication_claim_count",
        "hosted_public_claim_count",
        "license_clearance_claim_count",
        "citation_clearance_claim_count",
        "disclosure_clearance_claim_count",
        "private_root_inclusion_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
        "automatic_publication_count",
        "self_attestation_authority_count",
        "package_manifest_self_authority_count",
        "artifact_manifest_self_authority_count",
        "package_copy_authority_count",
    ):
        if int(summary.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": count_name})
    if int(summary.get("recipient_packet_manifest_bridge_case_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_case_count"})
    if int(summary.get("recipient_packet_manifest_bridge_source_capsule_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_source_capsule_count"})
    if int(summary.get("recipient_packet_manifest_bridge_semantic_carryforward_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_semantic_carryforward_count"})
    if int(summary.get("recipient_packet_manifest_bridge_repair_route_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_repair_route_count"})
    if int(summary.get("recipient_packet_manifest_bridge_teaching_rule_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_teaching_rule_count"})
    if int(summary.get("recipient_packet_manifest_bridge_blocked_claim_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_blocked_claim_count"})
    if int(summary.get("recipient_packet_manifest_bridge_omission_receipt_attachment_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_omission_receipt_attachment_count"})
    if int(summary.get("recipient_packet_manifest_bridge_package_row_attachment_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "recipient_packet_manifest_bridge_package_row_attachment_count"})
    if int(summary.get("recipient_packet_manifest_bridge_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "recipient_packet_manifest_bridge_missing_ref_count"})
    if int(summary.get("recipient_packet_manifest_bridge_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "recipient_packet_manifest_bridge_self_attestation_authority_count"})
    if int(summary.get("artifact_digest_requirement_bridge_case_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_case_count"})
    if int(summary.get("artifact_digest_requirement_bridge_source_capsule_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_source_capsule_count"})
    if int(summary.get("artifact_digest_requirement_bridge_semantic_carryforward_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_semantic_carryforward_count"})
    if int(summary.get("artifact_digest_requirement_bridge_repair_route_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_repair_route_count"})
    if int(summary.get("artifact_digest_requirement_bridge_teaching_rule_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_teaching_rule_count"})
    if int(summary.get("artifact_digest_requirement_bridge_blocked_claim_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_blocked_claim_count"})
    if int(summary.get("artifact_digest_requirement_bridge_source_witness_hash_preserved_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_source_witness_hash_preserved_count"})
    if int(summary.get("artifact_digest_requirement_bridge_package_row_attachment_count", 0)) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "artifact_digest_requirement_bridge_package_row_attachment_count"})
    if int(summary.get("artifact_digest_requirement_bridge_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "artifact_digest_requirement_bridge_missing_ref_count"})
    if int(summary.get("artifact_digest_requirement_bridge_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "artifact_digest_requirement_bridge_self_attestation_authority_count"})
    if int(summary.get("public_projection_handoff_case_count", 0)) < 6:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "public_projection_handoff_case_count"})
    if int(summary.get("public_projection_handoff_source_capsule_count", 0)) < 6:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "public_projection_handoff_source_capsule_count"})
    if int(summary.get("public_projection_handoff_semantic_carryforward_count", 0)) < 6:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "public_projection_handoff_semantic_carryforward_count"})
    if int(summary.get("public_projection_handoff_repair_route_count", 0)) < 6:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "public_projection_handoff_repair_route_count"})
    if int(summary.get("public_projection_handoff_blocked_claim_count", 0)) < 12:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "public_projection_handoff_blocked_claim_count"})
    if int(summary.get("public_projection_handoff_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "public_projection_handoff_missing_ref_count"})
    if int(summary.get("public_projection_handoff_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "public_projection_handoff_self_attestation_authority_count"})
    if int(summary.get("package_promotion_gate_case_count", 0)) < 4:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_case_count"})
    if int(summary.get("package_promotion_gate_source_capsule_count", 0)) < 4:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_source_capsule_count"})
    if int(summary.get("package_promotion_gate_semantic_carryforward_count", 0)) < 4:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_semantic_carryforward_count"})
    if int(summary.get("package_promotion_gate_repair_route_count", 0)) < 4:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_repair_route_count"})
    if int(summary.get("package_promotion_gate_teaching_rule_count", 0)) < 4:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_teaching_rule_count"})
    if int(summary.get("package_promotion_gate_blocked_claim_count", 0)) < 10:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_blocked_claim_count"})
    if int(summary.get("package_promotion_gate_site_source_handoff_case_count", 0)) < 1:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_site_source_handoff_case_count"})
    if int(summary.get("package_promotion_gate_source_capsule_hash_preserved_count", 0)) < 1:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_summary_count": "package_promotion_gate_source_capsule_hash_preserved_count"})
    if int(summary.get("package_promotion_gate_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "package_promotion_gate_missing_ref_count"})
    if int(summary.get("package_promotion_gate_self_attestation_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_summary_count": "package_promotion_gate_self_attestation_authority_count"})
    if summary.get("status_authority_nodes") != [
        "public_release_package_manifest_gate_evaluator",
        "claim_inference_map_evaluator",
        "claim_inference_authority_lattice_evaluator",
        "recipient_packet_manifest_bridge_evaluator",
        "artifact_digest_requirement_bridge_evaluator",
        "package_promotion_gate_evaluator",
        "release_axiom_gate",
        "principle_enforcement_matrix",
        "artifact_manifest_projection",
        "release_root_compiler_validator",
        "receipt_gate",
        "publication_gate",
        "website_card_projection_gate_evaluator",
        "site_projection_manifest_validator",
        "hosted_public_ci_workflow_gate",
        "license_citation_disclosure_gate",
        "recipient_review_route_gate",
    ]:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "status authority nodes mismatch"})
    if manifest.get("package_manifest_gate", {}).get("status") != "fail_closed":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "package manifest gate must stay fail-closed"})
    release_root_gate = manifest.get("release_root_compiler_gate", {})
    required_release_root_refs = {
        "microcosms/specimen_suite/release_branch_graph.json",
        "microcosms/specimen_suite/release_root_contract.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "microcosms/specimen_suite/release_root_compiler_receipt.json",
    }
    if release_root_gate.get("status") != "pass":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "release root compiler gate must pass"})
    if release_root_gate.get("validator_ref") != "validator.release_root_compiler":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "release root compiler gate missing validator ref"})
    if set(release_root_gate.get("required_refs", [])) != required_release_root_refs:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "release root compiler gate required refs mismatch"})
    for claim_flag in (
        "public_release_claim_allowed",
        "hosted_public_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
    ):
        if release_root_gate.get(claim_flag) is not False:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": f"release root compiler gate {claim_flag} must be false"})
    for count_name in (
        "authority_collapse_count",
        "projection_authority_violation_count",
        "std_python_blocker_count",
        "validation_failure_count",
    ):
        if int(release_root_gate.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "nonzero_release_root_gate_count": count_name})
    publication_snapshot = manifest.get("publication_gate_snapshot", {})
    if publication_snapshot.get("status") != "fail_closed":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "publication gate snapshot must be fail-closed"})
    if publication_snapshot.get("rights_license_grant_status") != "Apache-2.0_selected_pending_public_toggle":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "license grant status must stay pending public toggle"})
    if manifest.get("release_authority_handshake_ref") != "microcosms/public_release_package_manifest_gate/release_authority_handshake.json":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing release authority handshake ref"})
    handshake_summary = manifest.get("release_authority_handshake_summary", {})
    if int(handshake_summary.get("rows_checked", 0)) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "handshake row summary mismatch"})
    if int(handshake_summary.get("authority_collapse_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "manifest reports authority collapse"})
    if "microcosms/public_release_package_manifest_gate/release_authority_handshake.json" not in manifest.get("output_refs", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing handshake output ref"})
    if manifest.get("recipient_packet_manifest_bridge_ref") != "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing recipient packet manifest bridge ref"})
    if "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json" not in manifest.get("output_refs", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing recipient packet manifest bridge output ref"})
    if int(manifest.get("recipient_packet_manifest_bridge_summary", {}).get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "recipient packet manifest bridge summary reports missing refs"})
    if manifest.get("artifact_digest_requirement_bridge_ref") != "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing artifact digest requirement bridge ref"})
    if "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json" not in manifest.get("output_refs", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing artifact digest requirement bridge output ref"})
    if int(manifest.get("artifact_digest_requirement_bridge_summary", {}).get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "artifact digest requirement bridge summary reports missing refs"})
    if manifest.get("public_projection_handoff_ref") != "microcosms/public_release_package_manifest_gate/public_projection_handoff.json":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing public projection handoff ref"})
    if "microcosms/public_release_package_manifest_gate/public_projection_handoff.json" not in manifest.get("output_refs", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing public projection handoff output ref"})
    if int(manifest.get("public_projection_handoff_summary", {}).get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "public projection handoff summary reports missing refs"})
    if manifest.get("package_promotion_gate_ref") != "microcosms/public_release_package_manifest_gate/package_promotion_gate.json":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing package promotion gate ref"})
    if "microcosms/public_release_package_manifest_gate/package_promotion_gate.json" not in manifest.get("output_refs", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing package promotion gate output ref"})
    if int(manifest.get("package_promotion_gate_summary", {}).get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "package promotion gate summary reports missing refs"})

    required_failure_classes = {
        "public_export_without_publication_toggle",
        "package_manifest_row_missing",
        "registry_candidate_omission",
        "receipt_dependency_missing_or_stale",
        "hosted_public_boundary_missing",
        "rights_citation_disclosure_boundary_missing",
        "private_root_or_raw_seed_inclusion",
    }
    observed_failure_classes = {
        row.get("evaluator_decision", {}).get("failure_class")
        for row in rows
        if isinstance(row, dict) and row.get("evaluator_decision", {}).get("failure_class")
    }
    missing_failure_classes = sorted(required_failure_classes - observed_failure_classes)
    if missing_failure_classes:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "missing_failure_classes": missing_failure_classes})
    if not any(
        isinstance(row, dict)
        and row.get("package_row_id") == "package.recipient_redacted_packet_draft_private_review"
        for row in rows
    ):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing recipient redacted packet package row"})
    if not any(
        isinstance(row, dict)
        and row.get("package_row_id") == "package.artifact_integrity_witness_private_review"
        for row in rows
    ):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "missing artifact integrity witness package row"})

    validator_ids = {row.get("id") for row in load_json(root / "registry" / "validators.json").get("rows", []) if isinstance(row, dict)}
    for row in rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_manifest.json", "reason": "package row must be an object"})
            continue
        package_row_id = row.get("package_row_id")
        if row.get("package_copy_is_authority") is not False:
            failures.append({"package_row_id": package_row_id, "reason": "package copy must not be authority"})
        if row.get("manifest_self_status_is_authority") is not False:
            failures.append({"package_row_id": package_row_id, "reason": "manifest self-status must not be authority"})
        if row.get("artifact_manifest_self_status_is_authority") is not False:
            failures.append({"package_row_id": package_row_id, "reason": "artifact manifest self-status must not be authority"})
        if row.get("automatic_publication_allowed") is not False:
            failures.append({"package_row_id": package_row_id, "reason": "automatic publication must be disabled"})
        if not row.get("included_refs"):
            failures.append({"package_row_id": package_row_id, "reason": "missing included refs"})
        if not row.get("excluded_refs"):
            failures.append({"package_row_id": package_row_id, "reason": "missing excluded refs"})
        if not row.get("evidence_refs"):
            failures.append({"package_row_id": package_row_id, "reason": "missing evidence refs"})
        if not row.get("receipt_refs"):
            failures.append({"package_row_id": package_row_id, "reason": "missing receipt refs"})
        if not row.get("validator_refs"):
            failures.append({"package_row_id": package_row_id, "reason": "missing validator refs"})
        if package_row_id == "package.release_root_private_review_manifest":
            if "validator.release_root_compiler" not in row.get("validator_refs", []):
                failures.append({"package_row_id": package_row_id, "reason": "release root row missing compiler validator"})
            if not required_release_root_refs <= set(row.get("included_refs", [])):
                failures.append({"package_row_id": package_row_id, "reason": "release root row missing compiler refs"})
            if "release-root compiler pass approves public release" not in row.get("anti_claims", []):
                failures.append({"package_row_id": package_row_id, "reason": "release root row missing compiler anti-claim"})
        if package_row_id == "package.recipient_redacted_packet_draft_private_review":
            required_recipient_refs = {
                "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json",
                "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json",
                "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
                "microcosms/recipient_review_route_gate/route_gate.json",
            }
            if not required_recipient_refs <= set(row.get("included_refs", [])):
                failures.append({"package_row_id": package_row_id, "reason": "recipient packet row missing bridge source refs"})
            if "validator.recipient_review_route_gate_specimen" not in row.get("validator_refs", []):
                failures.append({"package_row_id": package_row_id, "reason": "recipient packet row missing route gate validator"})
            if "redacted recipient packet draft is sendable outreach copy" not in row.get("anti_claims", []):
                failures.append({"package_row_id": package_row_id, "reason": "recipient packet row missing sendable-copy anti-claim"})
            if "recipient_identity" not in row.get("excluded_refs", []):
                failures.append({"package_row_id": package_row_id, "reason": "recipient packet row must exclude recipient identity"})
            if "send_action" not in row.get("excluded_refs", []):
                failures.append({"package_row_id": package_row_id, "reason": "recipient packet row must exclude send action"})
        if package_row_id == "package.artifact_integrity_witness_private_review":
            required_artifact_refs = {
                "microcosms/release_artifact_integrity_witness/integrity_witness.json",
                "microcosms/release_artifact_integrity_witness/receipt.json",
                "state/artifact_manifest.json",
                "release/publication_gate.json",
            }
            if not required_artifact_refs <= set(row.get("included_refs", [])):
                failures.append({"package_row_id": package_row_id, "reason": "artifact witness row missing digest bridge source refs"})
            if "validator.release_artifact_integrity_witness_specimen" not in row.get("validator_refs", []):
                failures.append({"package_row_id": package_row_id, "reason": "artifact witness row missing witness validator"})
            if "artifact witness approves package export" not in row.get("anti_claims", []):
                failures.append({"package_row_id": package_row_id, "reason": "artifact witness row missing package export anti-claim"})
            if "public package tarball" not in row.get("excluded_refs", []):
                failures.append({"package_row_id": package_row_id, "reason": "artifact witness row must exclude public package tarball"})
        decision = row.get("evaluator_decision", {})
        if decision.get("status") not in {"allow_private_review", "block"}:
            failures.append({"package_row_id": package_row_id, "reason": "decision status must be allow_private_review or block"})
        if decision.get("status_authority") != "public_release_package_manifest_gate_evaluator_only":
            failures.append({"package_row_id": package_row_id, "reason": "unexpected decision authority"})
        for claim_flag in (
            "package_copy_used_as_authority",
            "manifest_self_status_used_as_authority",
            "artifact_manifest_self_status_used_as_authority",
            "public_export_claimed",
            "public_release_claimed",
            "hosted_public_claimed",
            "license_clearance_claimed",
            "citation_clearance_claimed",
            "disclosure_clearance_claimed",
            "private_root_included",
            "automatic_publication_allowed",
        ):
            if decision.get(claim_flag) is not False:
                failures.append({"package_row_id": package_row_id, "reason": f"decision {claim_flag} must be false"})
        if decision.get("status") == "block" and not decision.get("repair_row"):
            failures.append({"package_row_id": package_row_id, "reason": "blocked package row missing repair row"})
        for ref in row.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"package_row_id": package_row_id, "missing_evidence_ref": ref})
        for ref in row.get("receipt_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"package_row_id": package_row_id, "missing_receipt_ref": ref})
        for validator_ref in row.get("validator_refs", []):
            if validator_ref not in validator_ids:
                failures.append({"package_row_id": package_row_id, "unknown_validator": validator_ref})

    if handshake.get("status") != "ok":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake status must be ok"})
    if handshake.get("mission_thread_id") != "authority_never_collapses":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "unexpected mission thread"})
    if handshake.get("authority_posture") != "release_authority_handshake_not_publication_hosted_public_or_claim_authority":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "unexpected handshake authority posture"})
    if handshake.get("package_manifest_ref") != "microcosms/public_release_package_manifest_gate/package_manifest.json":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "unexpected package manifest ref"})
    handshake_summary_payload = handshake.get("summary", {})
    handshake_rows = handshake.get("package_rows", [])
    if not isinstance(handshake_rows, list) or len(handshake_rows) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake rows must match package rows"})
        handshake_rows = []
    if int(handshake_summary_payload.get("rows_checked", 0)) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake summary rows_checked mismatch"})
    if int(handshake_summary_payload.get("rows_with_claim_inference_refs", 0)) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "every handshake row must cite claim inference"})
    if int(handshake_summary_payload.get("rows_with_claim_authority_lattice_refs", 0)) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "every handshake row must cite claim authority lattice"})
    if int(handshake_summary_payload.get("rows_with_standard_axiom_principle_refs", 0)) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "every handshake row must cite standards, axioms, and principles"})
    if int(handshake_summary_payload.get("rows_with_fail_closed_public_boundary", 0)) != len(rows):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "every handshake row must keep public boundary fail-closed"})
    if int(handshake_summary_payload.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake missing refs must be zero"})
    if int(handshake_summary_payload.get("authority_collapse_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake authority collapse count must be zero"})
    if int(handshake_summary_payload.get("claim_authority_lattice_case_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake must consume claim authority lattice cases"})
    if int(handshake_summary_payload.get("claim_authority_lattice_source_capsule_count", 0)) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake must consume claim authority lattice capsules"})
    if int(handshake_summary_payload.get("claim_authority_lattice_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "claim authority lattice missing refs must be zero"})
    if handshake.get("claim_authority_lattice_ref") != "microcosms/status_preserving_control_plane/claim_inference_authority_lattice.json":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake missing claim authority lattice ref"})
    if handshake.get("claim_authority_lattice_projection_not_authority") is not True:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "claim authority lattice must remain projection_not_authority"})
    handshake_quality_selection = handshake.get("quality_delta_selection", {})
    if not isinstance(handshake_quality_selection, dict) or not handshake_quality_selection.get("top_upgrade_candidate_id"):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake must consume the current quality-delta top lane"})
    if current_quality_summary:
        if handshake_quality_selection.get("top_upgrade_candidate_id") != current_quality_summary.get("top_upgrade_candidate_id"):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake quality selection must match the current quality-delta top candidate"})
        if handshake_quality_selection.get("top_patch_lane") != current_quality_summary.get("top_patch_lane"):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake quality selection must match the current quality-delta patch lane"})
    if "claim_inference_map_evaluator" not in handshake.get("status_authority_nodes", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "missing claim inference authority node"})
    if "claim_inference_authority_lattice_evaluator" not in handshake.get("status_authority_nodes", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "missing claim authority lattice node"})
    if "release_axiom_gate" not in handshake.get("status_authority_nodes", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "missing release axiom authority node"})
    if "release_root_compiler_validator" not in handshake.get("status_authority_nodes", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "missing release root compiler authority node"})
    for missing_ref in handshake.get("missing_refs", []):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "missing_ref": missing_ref})
    for row in handshake_rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "reason": "handshake row must be an object"})
            continue
        package_row_id = row.get("package_row_id")
        if row.get("mission_thread_id") != "authority_never_collapses":
            failures.append({"package_row_id": package_row_id, "reason": "handshake row missing authority_never_collapses mission thread"})
        for refs_field in (
            "claim_inference_refs",
            "claim_authority_lattice_refs",
            "standard_refs",
            "axiom_refs",
            "principle_refs",
            "evidence_refs",
            "evidence_receipt_refs",
            "anti_claims",
            "validator_refs",
        ):
            if not row.get(refs_field):
                failures.append({"package_row_id": package_row_id, "reason": f"handshake row missing {refs_field}"})
        if row.get("claim_inference_source_ref") != "microcosms/specimen_suite/claim_inference_map.json":
            failures.append({"package_row_id": package_row_id, "reason": "handshake row missing claim inference source"})
        if row.get("claim_authority_lattice_source_ref") != "microcosms/status_preserving_control_plane/claim_inference_authority_lattice.json":
            failures.append({"package_row_id": package_row_id, "reason": "handshake row missing claim authority lattice source"})
        if row.get("hosted_public_status") != "fail_closed_not_proven":
            failures.append({"package_row_id": package_row_id, "reason": "hosted public status must stay fail-closed"})
        if row.get("publication_status") != "fail_closed":
            failures.append({"package_row_id": package_row_id, "reason": "publication status must stay fail-closed"})
        if row.get("authority_collapse_detected") is not False:
            failures.append({"package_row_id": package_row_id, "reason": "handshake row detected authority collapse"})
        if row.get("public_boundary_fail_closed") is not True:
            failures.append({"package_row_id": package_row_id, "reason": "handshake row must preserve public fail-closed boundary"})
        if not row.get("authority_boundary") or not row.get("downgrade_if"):
            failures.append({"package_row_id": package_row_id, "reason": "handshake row missing authority boundary or downgrade rule"})
        if package_row_id == "package.release_root_private_review_manifest":
            if "validator.release_root_compiler" not in row.get("validator_refs", []):
                failures.append({"package_row_id": package_row_id, "reason": "handshake release root row missing compiler validator"})
            if not required_release_root_refs <= set(row.get("included_artifacts", [])):
                failures.append({"package_row_id": package_row_id, "reason": "handshake release root row missing compiler artifacts"})

    if digest_bridge.get("schema_version") != "artifact_digest_requirement_bridge_v0":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "unexpected digest bridge schema"})
    if digest_bridge.get("microcosm_id") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "unexpected digest bridge microcosm_id"})
    if digest_bridge.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "digest bridge must declare projection_not_authority"})
    digest_summary = digest_bridge.get("status", {})
    digest_cases = digest_bridge.get("mechanism", {}).get("cases", [])
    artifact_witness_cases = artifact_witness.get("mechanism", {}).get("cases", [])
    if not isinstance(artifact_witness_cases, list):
        artifact_witness_cases = []
    if not isinstance(digest_cases, list) or len(digest_cases) < 5:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "expected at least five artifact digest bridge cases"})
        digest_cases = []
    if int(digest_summary.get("case_count", 0)) != len(digest_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "digest bridge case count mismatch"})
    if artifact_witness_cases and len(digest_cases) != len(artifact_witness_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "digest bridge cases must match artifact witness cases"})
    for count_name in (
        "source_capsule_count",
        "semantic_carryforward_count",
        "repair_route_count",
        "teaching_rule_count",
        "source_witness_hash_preserved_count",
        "package_row_attachment_count",
    ):
        if int(digest_summary.get(count_name, 0)) < len(digest_cases):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "missing_summary_count": count_name})
    if int(digest_summary.get("blocked_claim_count", 0)) < len(digest_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "missing_summary_count": "blocked_claim_count"})
    if int(digest_summary.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "nonzero_summary_count": "missing_ref_count"})
    digest_authority = digest_bridge.get("authority", {})
    for count_name in (
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(digest_authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "nonzero_authority_count": count_name})
    if int(digest_authority.get("evaluator_authority_count", 0)) < len(digest_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "digest bridge must cite evaluator authority for every case"})
    if digest_bridge.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "digest bridge route command mismatch"})
    observed_digest_cases = {case.get("case_id") for case in digest_cases if isinstance(case, dict)}
    if "artifact_digest_requirement_bridge.artifact_digest_attempts_package_export" not in observed_digest_cases:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json", "reason": "missing artifact digest package-export bridge case"})
    for case in digest_cases:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "digest bridge case missing source_clip"})
            continue
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "digest bridge source_clip_hash mismatch"})
        for required_field in (
            "semantic_carryforward",
            "transformation",
            "evaluator_or_validator",
            "outcome",
            "repair_route",
            "restart_point",
            "teaching_rule",
            "next_case",
            "digest_requirement",
        ):
            if not case.get(required_field):
                failures.append({"case_id": case_id, "missing": required_field})
        if case.get("evaluator_or_validator") != "artifact_digest_requirement_bridge_evaluator":
            failures.append({"case_id": case_id, "reason": "unexpected digest bridge evaluator"})
        if not case.get("evidence_refs"):
            failures.append({"case_id": case_id, "reason": "digest bridge case missing evidence refs"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "digest bridge case missing anti-claims"})
        if case.get("digest_requirement", {}).get("package_export_allowed") is not False:
            failures.append({"case_id": case_id, "reason": "digest requirement must not allow package export"})
        authority_flags = case.get("authority_flags", {})
        for flag_name, expected_value in (
            ("self_attestation_used_as_authority", False),
            ("projection_used_as_claim_authority", False),
            ("package_manifest_used_as_authority", False),
            ("artifact_witness_used_as_export_authority", False),
            ("artifact_digest_claimed", False),
            ("package_export_claimed", False),
            ("public_export_claimed", False),
            ("public_release_claimed", False),
            ("publication_claimed", False),
            ("hosted_public_claimed", False),
            ("private_root_equivalence_claimed", False),
            ("benchmark_win_claimed", False),
        ):
            if authority_flags.get(flag_name) is not expected_value:
                failures.append({"case_id": case_id, "reason": f"digest bridge authority flag {flag_name} must be false"})
        if authority_flags.get("package_row_attached") is not True:
            failures.append({"case_id": case_id, "reason": "digest bridge must attach package row"})
        if authority_flags.get("source_witness_hash_preserved") is not True:
            failures.append({"case_id": case_id, "reason": "digest bridge must preserve source witness hash"})
        for required_ref in (
            "microcosms/release_artifact_integrity_witness/integrity_witness.json",
            "microcosms/release_artifact_integrity_witness/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "release/publication_gate.json",
        ):
            if required_ref not in case.get("evidence_refs", []):
                failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if handoff.get("schema_version") != "package_public_projection_handoff_v0":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "unexpected handoff schema"})
    if handoff.get("microcosm_id") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "unexpected handoff microcosm_id"})
    if handoff.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "handoff must declare projection_not_authority"})
    handoff_summary = handoff.get("status", {})
    handoff_cases = handoff.get("mechanism", {}).get("cases", [])
    if not isinstance(handoff_cases, list) or len(handoff_cases) < 6:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "expected at least six public projection handoff cases"})
        handoff_cases = []
    if int(handoff_summary.get("case_count", 0)) != len(handoff_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "handoff case count mismatch"})
    for count_name in (
        "source_capsule_count",
        "semantic_carryforward_count",
        "repair_route_count",
        "teaching_rule_count",
    ):
        if int(handoff_summary.get(count_name, 0)) < len(handoff_cases):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "missing_summary_count": count_name})
    if int(handoff_summary.get("blocked_claim_count", 0)) < 12:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "missing_summary_count": "blocked_claim_count"})
    if int(handoff_summary.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "nonzero_summary_count": "missing_ref_count"})
    handoff_authority = handoff.get("authority", {})
    for count_name in (
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(handoff_authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "nonzero_authority_count": count_name})
    if int(handoff_authority.get("evaluator_authority_count", 0)) < len(handoff_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "handoff must cite evaluator authority for every case"})
    if handoff.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-site-projection --root . --write-receipt":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "reason": "handoff route command mismatch"})
    expected_handoff_cases = {
        "package_manifest_to_projection_handoff",
        "recipient_packet_bridge_bounds_projection_handoff",
        "artifact_digest_requirement_bounds_projection_handoff",
        "website_card_gate_bounds_projection_copy",
        "site_projection_sandbox_mode_blocks_public_launch",
        "publication_gate_keeps_release_claim_fail_closed",
    }
    observed_handoff_cases = {case.get("case_id") for case in handoff_cases if isinstance(case, dict)}
    missing_handoff_cases = sorted(expected_handoff_cases - observed_handoff_cases)
    if missing_handoff_cases:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/public_projection_handoff.json", "missing_cases": missing_handoff_cases})
    for case in handoff_cases:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "handoff case missing source_clip"})
            continue
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "source_clip_hash mismatch"})
        for required_field in (
            "semantic_carryforward",
            "transformation",
            "evaluator_or_validator",
            "outcome",
            "repair_route",
            "restart_point",
            "teaching_rule",
            "next_case",
        ):
            if not case.get(required_field):
                failures.append({"case_id": case_id, "missing": required_field})
        if not case.get("evidence_refs"):
            failures.append({"case_id": case_id, "reason": "handoff case missing evidence refs"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "handoff case missing anti-claims"})
        for flag_name, expected_value in (
            ("self_attestation_used_as_authority", False),
            ("projection_used_as_claim_authority", False),
            ("public_release_claimed", False),
            ("publication_claimed", False),
            ("private_root_equivalence_claimed", False),
            ("benchmark_win_claimed", False),
        ):
            if case.get("authority_flags", {}).get(flag_name) is not expected_value:
                failures.append({"case_id": case_id, "reason": f"authority flag {flag_name} must be false"})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})
        if case_id == "recipient_packet_bridge_bounds_projection_handoff":
            if case.get("restart_point") != "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json":
                failures.append({"case_id": case_id, "reason": "recipient bridge handoff must restart from the bridge artifact"})
            for required_ref in (
                "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
                "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json",
                "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json",
                "microcosms/recipient_review_route_gate/route_gate.json",
            ):
                if required_ref not in case.get("evidence_refs", []):
                    failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})
        if case_id == "artifact_digest_requirement_bounds_projection_handoff":
            if case.get("restart_point") != "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json":
                failures.append({"case_id": case_id, "reason": "artifact digest handoff must restart from the bridge artifact"})
            for required_ref in (
                "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
                "microcosms/release_artifact_integrity_witness/integrity_witness.json",
                "microcosms/release_artifact_integrity_witness/receipt.json",
                "release/publication_gate.json",
            ):
                if required_ref not in case.get("evidence_refs", []):
                    failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})

    if promotion.get("schema_version") != "package_promotion_gate_v0":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "unexpected promotion gate schema"})
    if promotion.get("microcosm_id") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "unexpected promotion gate microcosm_id"})
    if promotion.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "promotion gate must declare projection_not_authority"})
    promotion_summary = promotion.get("status", {})
    promotion_cases = promotion.get("mechanism", {}).get("cases", [])
    if not isinstance(promotion_cases, list) or len(promotion_cases) < 4:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "expected at least four package promotion gate cases"})
        promotion_cases = []
    if int(promotion_summary.get("case_count", 0)) != len(promotion_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "promotion gate case count mismatch"})
    for count_name in (
        "source_capsule_count",
        "semantic_carryforward_count",
        "repair_route_count",
        "teaching_rule_count",
    ):
        if int(promotion_summary.get(count_name, 0)) < len(promotion_cases):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "missing_summary_count": count_name})
    if int(promotion_summary.get("site_source_handoff_case_count", 0)) < 1:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "missing_summary_count": "site_source_handoff_case_count"})
    if int(promotion_summary.get("source_capsule_hash_preserved_count", 0)) < 1:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "missing_summary_count": "source_capsule_hash_preserved_count"})
    if int(promotion_summary.get("blocked_claim_count", 0)) < 10:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "missing_summary_count": "blocked_claim_count"})
    if int(promotion_summary.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "nonzero_summary_count": "missing_ref_count"})
    promotion_authority = promotion.get("authority", {})
    for count_name in (
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(promotion_authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "nonzero_authority_count": count_name})
    if int(promotion_authority.get("evaluator_authority_count", 0)) < len(promotion_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "promotion gate must cite evaluator authority for every case"})
    if promotion.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "promotion gate route command mismatch"})
    expected_promotion_cases = {
        "package_promotion_gate.artifact_digest_requirement_status",
        "package_promotion_gate.public_projection_handoff_status",
        "package_promotion_gate.publication_gate_fail_closed",
    }
    observed_promotion_cases = {case.get("case_id") for case in promotion_cases if isinstance(case, dict)}
    if not any(
        isinstance(case_id, str)
        and case_id.startswith(
            "package_promotion_gate.site_projection_consumes_card_recipient_packet_bridge_projection_boundary_source_capsule"
        )
        for case_id in observed_promotion_cases
    ):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "reason": "missing site projection source-capsule promotion case"})
    missing_promotion_cases = sorted(expected_promotion_cases - observed_promotion_cases)
    if missing_promotion_cases:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/package_promotion_gate.json", "missing_cases": missing_promotion_cases})
    for case in promotion_cases:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "promotion gate case missing source_clip"})
            continue
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "promotion gate source_clip_hash mismatch"})
        if case.get("upstream_source_clip_hash") and case.get("upstream_source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "promotion gate upstream source hash mismatch"})
        for required_field in (
            "semantic_carryforward",
            "transformation",
            "evaluator_or_validator",
            "outcome",
            "repair_route",
            "restart_point",
            "teaching_rule",
            "next_case",
        ):
            if not case.get(required_field):
                failures.append({"case_id": case_id, "missing": required_field})
        if case.get("evaluator_or_validator") != "package_promotion_gate_evaluator":
            failures.append({"case_id": case_id, "reason": "unexpected promotion gate evaluator"})
        if not case.get("evidence_refs"):
            failures.append({"case_id": case_id, "reason": "promotion gate case missing evidence refs"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "promotion gate case missing anti-claims"})
        promotion_decision = case.get("promotion_decision", {})
        if not isinstance(promotion_decision, dict) or promotion_decision.get("status") not in {
            "blocked_public_promotion",
            "fail_closed",
        }:
            failures.append({"case_id": case_id, "reason": "promotion decision must block public package promotion"})
        authority_flags = case.get("authority_flags", {})
        for flag_name, expected_value in (
            ("self_attestation_used_as_authority", False),
            ("projection_used_as_claim_authority", False),
            ("package_manifest_used_as_authority", False),
            ("site_projection_used_as_claim_authority", False),
            ("public_package_promotion_allowed", False),
            ("public_export_claimed", False),
            ("public_release_claimed", False),
            ("publication_claimed", False),
            ("hosted_public_claimed", False),
            ("private_root_equivalence_claimed", False),
            ("benchmark_win_claimed", False),
        ):
            if authority_flags.get(flag_name) is not expected_value:
                failures.append({"case_id": case_id, "reason": f"promotion authority flag {flag_name} must be false"})
        for required_ref in (
            "microcosms/public_release_package_manifest_gate/public_projection_handoff.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "state/site_projection_manifest.json",
            "release/publication_gate.json",
        ):
            if required_ref not in case.get("evidence_refs", []):
                failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if bridge.get("schema_version") != "recipient_packet_manifest_bridge_v0":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "unexpected bridge schema"})
    if bridge.get("microcosm_id") != "public_release_package_manifest_gate_microcosm":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "unexpected bridge microcosm_id"})
    if bridge.get("generated_by", {}).get("projection_not_authority") is not True:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "bridge must declare projection_not_authority"})
    bridge_source_refs = bridge.get("generated_by", {}).get("source_refs", [])
    for required_ref in (
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
    ):
        if required_ref not in bridge_source_refs:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "missing_source_ref": required_ref})
    bridge_summary = bridge.get("status", {})
    bridge_cases = bridge.get("mechanism", {}).get("cases", [])
    draft_cases = redacted_draft.get("mechanism", {}).get("cases", [])
    if not isinstance(draft_cases, list):
        draft_cases = []
    source_shuttle_draft_cases = [
        case
        for case in draft_cases
        if isinstance(case, dict) and case.get("source_route_id") == "route.private_source_shuttle_packet_review"
    ]
    source_shuttle_expected_ref_count = sum(
        len(case.get("source_shuttle_redacted_packet_refs", []))
        for case in source_shuttle_draft_cases
        if isinstance(case.get("source_shuttle_redacted_packet_refs", []), list)
    )
    if not isinstance(bridge_cases, list) or len(bridge_cases) < 8:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "expected at least eight bridge cases"})
        bridge_cases = []
    if int(bridge_summary.get("case_count", 0)) != len(bridge_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "bridge case count mismatch"})
    if draft_cases and len(bridge_cases) != len(draft_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "bridge cases must match redacted draft cases"})
    for count_name in (
        "source_capsule_count",
        "semantic_carryforward_count",
        "repair_route_count",
        "teaching_rule_count",
        "omission_receipt_attachment_count",
        "package_row_attachment_count",
    ):
        if int(bridge_summary.get(count_name, 0)) < len(bridge_cases):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "missing_summary_count": count_name})
    if int(bridge_summary.get("blocked_claim_count", 0)) < len(bridge_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "missing_summary_count": "blocked_claim_count"})
    if source_shuttle_expected_ref_count:
        source_shuttle_bridge_case_count = sum(
            1
            for case in bridge_cases
            if isinstance(case, dict)
            and case.get("semantic_carryforward", {}).get("source_route_id")
            == "route.private_source_shuttle_packet_review"
        )
        expected_summary_counts = {
            "source_shuttle_manifest_bridge_count": source_shuttle_bridge_case_count,
            "source_shuttle_manifest_ref_count": source_shuttle_expected_ref_count,
            "source_shuttle_packet_hash_preserved_count": source_shuttle_expected_ref_count,
            "source_shuttle_source_clip_hash_preserved_count": source_shuttle_expected_ref_count,
            "source_shuttle_no_private_copy_rule_count": source_shuttle_expected_ref_count,
        }
        for count_name, expected_count in expected_summary_counts.items():
            if int(bridge_summary.get(count_name, -1)) != expected_count:
                failures.append(
                    {
                        "path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
                        "unexpected_summary_count": count_name,
                        "expected": expected_count,
                    }
                )
        for count_name in (
            "source_shuttle_private_field_rehydration_count",
            "source_shuttle_package_authority_count",
            "source_shuttle_export_authority_claim_count",
        ):
            if int(bridge_summary.get(count_name, -1)) != 0:
                failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "nonzero_summary_count": count_name})
    if int(bridge_summary.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "nonzero_summary_count": "missing_ref_count"})
    bridge_authority = bridge.get("authority", {})
    for count_name in (
        "self_attestation_authority_count",
        "public_release_claim_count",
        "publication_claim_count",
        "private_root_equivalence_claim_count",
        "benchmark_win_claim_count",
    ):
        if int(bridge_authority.get(count_name, -1)) != 0:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "nonzero_authority_count": count_name})
    if int(bridge_authority.get("evaluator_authority_count", 0)) < len(bridge_cases):
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "bridge must cite evaluator authority for every case"})
    if bridge.get("route", {}).get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json", "reason": "bridge route command mismatch"})
    for case in bridge_cases:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        source_clip = case.get("source_clip")
        if not isinstance(source_clip, str) or not source_clip:
            failures.append({"case_id": case_id, "reason": "bridge case missing source_clip"})
            continue
        expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
        if case.get("source_clip_hash") != expected_hash:
            failures.append({"case_id": case_id, "reason": "bridge source_clip_hash mismatch"})
        for required_field in (
            "semantic_carryforward",
            "transformation",
            "evaluator_or_validator",
            "outcome",
            "repair_route",
            "restart_point",
            "teaching_rule",
            "next_case",
        ):
            if not case.get(required_field):
                failures.append({"case_id": case_id, "missing": required_field})
        if case.get("evaluator_or_validator") != "recipient_packet_manifest_bridge_evaluator":
            failures.append({"case_id": case_id, "reason": "unexpected bridge evaluator"})
        if not case.get("evidence_refs"):
            failures.append({"case_id": case_id, "reason": "bridge case missing evidence refs"})
        if not case.get("anti_claims"):
            failures.append({"case_id": case_id, "reason": "bridge case missing anti-claims"})
        authority_flags = case.get("authority_flags", {})
        for flag_name, expected_value in (
            ("self_attestation_used_as_authority", False),
            ("projection_used_as_claim_authority", False),
            ("package_copy_used_as_authority", False),
            ("recipient_copy_is_authority", False),
            ("public_export_claimed", False),
            ("public_release_claimed", False),
            ("publication_claimed", False),
            ("hosted_public_claimed", False),
            ("recipient_identity_present", False),
            ("send_action_allowed", False),
            ("send_destination_present", False),
            ("private_field_rehydration_allowed", False),
            ("source_shuttle_private_field_rehydration_allowed", False),
            ("source_shuttle_semantic_packet_used_as_package_authority", False),
            ("source_shuttle_manifest_ref_used_as_export_authority", False),
            ("source_shuttle_export_permission_claimed", False),
            ("private_root_equivalence_claimed", False),
            ("benchmark_win_claimed", False),
        ):
            if authority_flags.get(flag_name) is not expected_value:
                failures.append({"case_id": case_id, "reason": f"bridge authority flag {flag_name} must be false"})
        if authority_flags.get("omission_receipt_attached") is not True:
            failures.append({"case_id": case_id, "reason": "bridge must attach omission receipt"})
        if authority_flags.get("package_row_attached") is not True:
            failures.append({"case_id": case_id, "reason": "bridge must attach package row"})
        for required_ref in (
            "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json",
            "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json",
            "microcosms/recipient_review_route_gate/route_gate.json",
        ):
            if required_ref not in case.get("evidence_refs", []):
                failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})
        semantic = case.get("semantic_carryforward", {})
        source_shuttle_manifest_refs = case.get("source_shuttle_manifest_bridge_refs", [])
        if semantic.get("source_route_id") == "route.private_source_shuttle_packet_review":
            if not isinstance(source_shuttle_manifest_refs, list) or not source_shuttle_manifest_refs:
                failures.append({"case_id": case_id, "reason": "source-shuttle bridge case missing manifest refs"})
                source_shuttle_manifest_refs = []
            if int(semantic.get("source_shuttle_manifest_ref_count", -1)) != len(source_shuttle_manifest_refs):
                failures.append({"case_id": case_id, "reason": "source-shuttle manifest ref count mismatch"})
            for count_name in (
                "source_shuttle_packet_hash_preserved_count",
                "source_shuttle_source_clip_hash_preserved_count",
                "source_shuttle_no_private_copy_rule_count",
            ):
                if int(semantic.get(count_name, -1)) != len(source_shuttle_manifest_refs):
                    failures.append({"case_id": case_id, "reason": f"{count_name} mismatch"})
            for flag_name in (
                "source_shuttle_private_field_rehydration_allowed",
                "source_shuttle_semantic_packet_used_as_package_authority",
                "source_shuttle_package_export_authority_allowed",
            ):
                if semantic.get(flag_name) is not False:
                    failures.append({"case_id": case_id, "reason": f"{flag_name} must be false"})
            for required_ref in (
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
            ):
                if required_ref not in case.get("evidence_refs", []):
                    failures.append({"case_id": case_id, "missing_evidence_ref": required_ref})
            for ref in source_shuttle_manifest_refs:
                if not isinstance(ref, dict):
                    failures.append({"case_id": case_id, "reason": "source-shuttle manifest ref must be object"})
                    continue
                for required_key in (
                    "bridge_case_id",
                    "source_shuttle_case_id",
                    "semantic_packet_hash",
                    "source_clip_hash",
                    "restart_point",
                    "no_private_copy_rule",
                ):
                    if not ref.get(required_key):
                        failures.append({"case_id": case_id, "missing_source_shuttle_ref_key": required_key})
        for ref in case.get("evidence_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"case_id": case_id, "missing_evidence_ref": ref})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/public_release_package_manifest_gate/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
        "microcosms/public_release_package_manifest_gate/release_authority_handshake.json",
        "microcosms/public_release_package_manifest_gate/public_projection_handoff.json",
        "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
        "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
        "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
        "microcosms/public_release_package_manifest_gate/README.md",
        "AXIOMS.md",
        "registry/release_candidates.json",
        "registry/validators.json",
        "state/artifact_manifest.json",
        "state/axiom_kernel.json",
        "state/principle_enforcement_matrix.json",
        "state/teleology_map.json",
        "microcosms/specimen_suite/release_branch_graph.json",
        "microcosms/specimen_suite/release_root_contract.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "microcosms/specimen_suite/release_root_compiler_receipt.json",
        "src/idea_microcosm/public_release_package_manifest_gate_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "microcosms/specimen_suite/claim_inference_map.json",
        "microcosms/status_preserving_control_plane/claim_inference_authority_lattice.json",
        "microcosms/specimen_suite/quality_delta_board.json",
        "microcosms/release_artifact_integrity_witness/integrity_witness.json",
        "microcosms/release_artifact_integrity_witness/receipt.json",
        "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
        "microcosms/hosted_public_ci_workflow_gate/receipt.json",
        "microcosms/license_citation_disclosure_gate/clearance_gate.json",
        "microcosms/license_citation_disclosure_gate/receipt.json",
        "microcosms/recipient_review_route_gate/route_gate.json",
        "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
        "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json",
        "microcosms/recipient_review_route_gate/redacted_recipient_packet_draft.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
        "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
        "microcosms/recipient_review_route_gate/receipt.json",
        "microcosms/website_card_projection_gate/card_gate.json",
        "microcosms/website_card_projection_gate/receipt.json",
        "state/site_projection_manifest.json",
        "site/sandbox/site_projection_manifest.json",
        "site/sandbox/site_projection_bundle.json",
        "receipts/site_projection_manifest_latest.json",
        "site/sandbox/site_projection_receipt.json",
        "receipts/release_candidate_portfolio.json",
        "receipts/cold_sandbox_probe_latest.json",
        "receipts/validation_run.json",
        "release/publication_gate.json",
        "RELEASE_SCOPE.md",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/public_release_package_manifest_gate/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/public_release_package_manifest_gate/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "not a publication authority",
        "release authority handshake",
        "recipient packet manifest bridge",
        "redacted recipient packet draft",
        "omission receipt",
        "source-shuttle redacted packet refs",
        "artifact digest requirement bridge",
        "release artifact integrity witness",
        "public projection handoff",
        "package promotion gate",
        "site projection source capsule handoff",
        "source-clip hashes",
        "claim-authority lattice refs",
        "package manifest",
        "public export",
        "Local receipts remain local-only",
        "fail-closed",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/public_release_package_manifest_gate/README.md", "missing_text": required_text})
    return failures


def _cold_start_agent_skills_pack_failures(root: Path) -> list[dict[str, Any]]:
    probe_path = root / "microcosms" / "cold_start_agent_skills_pack" / "skill_pack_probe.json"
    receipt_path = root / "microcosms" / "cold_start_agent_skills_pack" / "receipt.json"
    readme_path = root / "microcosms" / "cold_start_agent_skills_pack" / "README.md"
    failures: list[dict[str, Any]] = []
    if not probe_path.exists():
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "missing skill-pack probe"})
    if not receipt_path.exists():
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/receipt.json", "reason": "missing specimen receipt"})
    if not readme_path.exists():
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/README.md", "reason": "missing specimen README"})
    if failures:
        return failures

    probe = load_json(probe_path)
    receipt = load_json(receipt_path)
    if probe.get("specimen_id") != "cold_start_agent_skills_pack_microcosm":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "unexpected specimen_id"})
    if probe.get("authority_posture") != "public_safe_cold_start_skill_pack_probe_not_private_agent_or_hosted_public_authority":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "unexpected authority posture"})
    if probe.get("release_scope_statement") != "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "missing release scope statement"})
    if "public-release-ready" in json.dumps(probe).lower():
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "skill-pack probe must not imply public release readiness"})

    summary = probe.get("summary", {})
    if int(summary.get("route_step_count", 0)) < 6:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "route_step_count"})
    if int(summary.get("runnable_command_count", 0)) < 7:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "runnable_command_count"})
    if int(summary.get("selected_specimen_count", 0)) < 3:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "selected_specimen_count"})
    if int(summary.get("receipt_ref_count", 0)) < 5:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "receipt_ref_count"})
    if int(summary.get("diagnosis_count", 0)) < 3:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "diagnosis_count"})
    if int(summary.get("blocked_public_claim_count", 0)) < 1:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "blocked_public_claim_count"})
    if int(summary.get("missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "nonzero_summary_count": "missing_ref_count"})
    if int(summary.get("failed_probe_row_count", -1)) != 0:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "nonzero_summary_count": "failed_probe_row_count"})
    if int(summary.get("skill_pack_self_authority_count", -1)) != 0:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "nonzero_summary_count": "skill_pack_self_authority_count"})
    if summary.get("status_authority_nodes") != [
        "skill_pack_probe_evaluator",
        "release_root_compiler_validator",
        "receipt_gate",
        "publication_gate",
    ]:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "status authority nodes mismatch"})
    if summary.get("release_root_route_status") != "pass":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route must pass"})
    if int(summary.get("release_root_artifact_ref_count", 0)) < 5:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "release_root_artifact_ref_count"})
    if int(summary.get("release_root_validator_ref_count", 0)) < 1:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "missing_summary_count": "release_root_validator_ref_count"})
    if int(summary.get("release_root_missing_ref_count", -1)) != 0:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "nonzero_summary_count": "release_root_missing_ref_count"})
    if int(summary.get("release_root_blocker_count", -1)) != 0:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "nonzero_summary_count": "release_root_blocker_count"})
    if int(summary.get("release_root_public_claim_allowed_count", -1)) != 0:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "nonzero_summary_count": "release_root_public_claim_allowed_count"})
    if int(summary.get("std_python_blocker_count", -1)) != 0:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "nonzero_summary_count": "std_python_blocker_count"})

    publication_snapshot = probe.get("publication_gate_snapshot", {})
    if publication_snapshot.get("status") != "fail_closed":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "publication gate snapshot must be fail-closed"})
    if probe.get("candidate_snapshot", {}).get("all_candidate_specimens_landed") is not True:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "candidate snapshot must declare terminal landed status"})

    release_root_route = probe.get("release_root_compiler_route", {})
    if release_root_route.get("status") != "pass":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route status must pass"})
    if release_root_route.get("first_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-root-compiler --root . --write-receipt":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route command mismatch"})
    if release_root_route.get("validation_command") != "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route validation command mismatch"})
    if "validator.release_root_compiler" not in release_root_route.get("validator_refs", []):
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route missing validator ref"})
    release_root_required_refs = {
        "microcosms/specimen_suite/release_branch_graph.json",
        "microcosms/specimen_suite/release_root_contract.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "microcosms/specimen_suite/release_root_compiler_receipt.json",
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
    }
    if not release_root_required_refs <= set(release_root_route.get("artifact_refs", [])):
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route missing artifact refs"})
    if release_root_route.get("missing_refs"):
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route has missing refs"})
    if not release_root_route.get("anti_claims"):
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "release root compiler route missing anti-claims"})
    for claim_flag in (
        "public_release_claim_allowed",
        "hosted_public_claim_allowed",
        "publication_permission_claim_allowed",
        "private_root_equivalence_claim_allowed",
        "generated_projection_is_source_authority",
    ):
        if release_root_route.get("authority_flags", {}).get(claim_flag) is not False:
            failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": f"release root compiler route {claim_flag} must be false"})

    rows = probe.get("probe_rows", [])
    if not isinstance(rows, list) or len(rows) < 5:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "expected at least five probe rows"})
        rows = []
    blocked_public_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "probe row must be an object"})
            continue
        row_id = row.get("row_id")
        if row.get("missing_refs"):
            failures.append({"row_id": row_id, "reason": "probe row has missing refs"})
        decision = row.get("evaluator_decision", {})
        if decision.get("status") not in {"pass", "block"}:
            failures.append({"row_id": row_id, "reason": "decision status must be pass or block"})
        if decision.get("status_authority") != "skill_pack_probe_evaluator_only":
            failures.append({"row_id": row_id, "reason": "unexpected decision authority"})
        for claim_flag in (
            "skill_text_used_as_status_authority",
            "local_probe_claimed_hosted_public",
            "hosted_public_claimed",
            "publication_claimed",
            "private_context_required",
        ):
            if decision.get(claim_flag) is not False:
                failures.append({"row_id": row_id, "reason": f"decision {claim_flag} must be false"})
        if decision.get("failure_class") == "hosted_public_or_publication_overclaim":
            blocked_public_rows += 1
            if decision.get("status") != "block":
                failures.append({"row_id": row_id, "reason": "public overclaim row must be blocked"})
            if not decision.get("repair_row"):
                failures.append({"row_id": row_id, "reason": "blocked public claim row missing repair row"})
        for ref in row.get("input_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"row_id": row_id, "missing_input_ref": ref})
    if blocked_public_rows < 1:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json", "reason": "missing blocked public claim row"})

    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/receipt.json", "reason": "receipt must be ok with fixture_validated claim tier"})
    evidence_refs = set(receipt.get("evidence_refs", []))
    required_refs = {
        "microcosms/cold_start_agent_skills_pack/skill_pack_probe.json",
        "microcosms/cold_start_agent_skills_pack/README.md",
        "microcosms/specimen_suite/release_branch_graph.json",
        "microcosms/specimen_suite/release_root_contract.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "microcosms/specimen_suite/release_root_compiler_receipt.json",
        "microcosms/public_release_package_manifest_gate/package_manifest.json",
        "registry/release_candidates.json",
        "registry/validators.json",
        "state/release_candidate_portfolio.json",
        "navigation/microcosm_index.json",
        "state/artifact_manifest.json",
        "skills/cold_start_agent.md",
        "src/idea_microcosm/cold_start_agent_skills_pack_specimen.py",
        "src/idea_microcosm/validators.py",
        "src/idea_microcosm/cli.py",
        "receipts/validation_run.json",
        "receipts/cold_sandbox_probe_latest.json",
        "microcosms/executable_grammar_metabolism/receipt.json",
        "microcosms/task_ledger_cap_economy/receipt.json",
        "microcosms/status_preserving_control_plane/receipt.json",
        "microcosms/public_release_package_manifest_gate/receipt.json",
        "release/publication_gate.json",
        "RELEASE_SCOPE.md",
    }
    missing_refs = sorted(required_refs - evidence_refs)
    if missing_refs:
        failures.append({"path": "microcosms/cold_start_agent_skills_pack/receipt.json", "missing_evidence_refs": missing_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "microcosms/cold_start_agent_skills_pack/receipt.json", "missing_evidence_ref": ref})

    readme = readme_path.read_text(encoding="utf-8")
    for required_text in (
        "PYTHONPATH=src python3 -m idea_microcosm.cli build-cold-start-agent-skills-pack-specimen --root . --write-receipt",
        "This is a distilled beta demonstration of selected mechanisms. It is not the full private system.",
        "not a hosted-public authority",
        "machine-readable checklist",
    ):
        if required_text not in readme:
            failures.append({"path": "microcosms/cold_start_agent_skills_pack/README.md", "missing_text": required_text})
    return failures


def _release_specimen_suite_probe_failures(root: Path) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    receipt_path = root / "receipts" / "specimen_suite_probe_latest.json"
    board_path = root / "microcosms" / "specimen_suite" / "selection_board.json"
    apex_board_path = root / "microcosms" / "specimen_suite" / "apex_reviewer_board.json"
    claim_map_path = root / "microcosms" / "specimen_suite" / "claim_inference_map.json"
    quality_delta_board_path = root / "microcosms" / "specimen_suite" / "quality_delta_board.json"
    dogfood_control_loop_path = root / "microcosms" / "specimen_suite" / "dogfood_control_loop_receipt.json"
    living_substrate_witness_path = root / "microcosms" / "specimen_suite" / "living_substrate_witness.json"
    macrocosm_contribution_assay_path = root / "microcosms" / "specimen_suite" / "macrocosm_contribution_assay.json"
    release_microcosm_ontology_path = root / "microcosms" / "specimen_suite" / "release_microcosm_ontology.json"
    board_readme_path = root / "microcosms" / "specimen_suite" / "README.md"
    if not receipt_path.exists():
        return [{"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing specimen-suite probe receipt"}]
    if not board_path.exists():
        failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "missing specimen-suite selection board"})
    if not apex_board_path.exists():
        failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "missing apex reviewer board"})
    if not claim_map_path.exists():
        failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "missing claim-inference map"})
    if not quality_delta_board_path.exists():
        failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "missing quality-delta board"})
    if not dogfood_control_loop_path.exists():
        failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "missing dogfood control-loop receipt"})
    if not living_substrate_witness_path.exists():
        failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "missing living-substrate witness"})
    if not macrocosm_contribution_assay_path.exists():
        failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "missing macrocosm contribution assay"})
    if not release_microcosm_ontology_path.exists():
        failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "missing release microcosm ontology"})
    if not board_readme_path.exists():
        failures.append({"path": "microcosms/specimen_suite/README.md", "reason": "missing specimen-suite selection board README"})

    receipt = load_json(receipt_path)
    board = load_json(board_path) if board_path.exists() else {}
    apex_board = load_json(apex_board_path) if apex_board_path.exists() else {}
    claim_map = load_json(claim_map_path) if claim_map_path.exists() else {}
    quality_delta_board = load_json(quality_delta_board_path) if quality_delta_board_path.exists() else {}
    dogfood_control_loop = load_json(dogfood_control_loop_path) if dogfood_control_loop_path.exists() else {}
    living_substrate_witness = load_json(living_substrate_witness_path) if living_substrate_witness_path.exists() else {}
    macrocosm_contribution_assay = load_json(macrocosm_contribution_assay_path) if macrocosm_contribution_assay_path.exists() else {}
    release_microcosm_ontology = load_json(release_microcosm_ontology_path) if release_microcosm_ontology_path.exists() else {}
    work_bridge_ref = "microcosms/concurrency_mission_control/work_metabolism_bridge.json"
    applied_original_contribution_gap = "concept_graph_core_self_index_hardening"
    next_gap_after_work_bridge = "github_export_scope_manifest_hardening"
    next_owner_after_work_bridge = "meta_diagnostics_workbench_microcosm"
    next_public_boundary_gap = "source_shuttle_microcosm"
    expected_contribution_first_route_status = "cold_entry_atlas_landed"
    required_selected_ids = {
        "executable_grammar_metabolism_microcosm",
        "task_ledger_cap_economy_microcosm",
        "concurrency_transaction_mission_control_microcosm",
        "concept_graph_cards_microcosm",
        "lab_evolve_failure_replay_graph_microcosm",
        "provider_harness_evaluator_authority_split_microcosm",
        "atlas_navigation_bands_microcosm",
        "cold_start_agent_skills_pack_microcosm",
        "status_preserving_control_plane_microcosm",
    }
    selected_ids = set(receipt.get("selected_specimen_ids", []))
    missing_selected_ids = sorted(required_selected_ids - selected_ids)
    if missing_selected_ids:
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "missing_selected_specimen_ids": missing_selected_ids})
    if receipt.get("selection_board_ref") != "microcosms/specimen_suite/selection_board.json":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing selection board reference"})
    if receipt.get("selection_board_readme_ref") != "microcosms/specimen_suite/README.md":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing selection board README reference"})
    if receipt.get("apex_reviewer_board_ref") != "microcosms/specimen_suite/apex_reviewer_board.json":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing apex reviewer board reference"})
    if receipt.get("claim_inference_map_ref") != "microcosms/specimen_suite/claim_inference_map.json":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing claim-inference map reference"})
    if receipt.get("quality_delta_board_ref") != "microcosms/specimen_suite/quality_delta_board.json":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing quality-delta board reference"})
    if receipt.get("dogfood_control_loop_receipt_ref") != "microcosms/specimen_suite/dogfood_control_loop_receipt.json":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing dogfood control-loop receipt reference"})
    if receipt.get("living_substrate_witness_ref") != "microcosms/specimen_suite/living_substrate_witness.json":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing living-substrate witness reference"})
    if receipt.get("macrocosm_contribution_assay_ref") != "microcosms/specimen_suite/macrocosm_contribution_assay.json":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing macrocosm contribution assay reference"})
        if receipt.get("release_microcosm_ontology_ref") != "microcosms/specimen_suite/release_microcosm_ontology.json":
            failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing release microcosm ontology reference"})
        if receipt.get("work_metabolism_bridge_ref") != work_bridge_ref:
            failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing work-metabolism bridge reference"})
        if not receipt.get("highest_score_candidate_id") or not receipt.get("ranked_candidate_ids"):
            failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "selection ranking summary missing"})

    if receipt.get("kind") != "receipt" or receipt.get("id") != "receipt.release_specimen_suite_probe":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "unexpected receipt identity"})
    if receipt.get("status") != "ok" or receipt.get("result") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "suite receipt must be ok with fixture_validated claim tier"})
    if receipt.get("authority_posture") != "local_release_specimen_suite_probe_not_hosted_public_or_publication_authority":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "unexpected authority posture"})
    if receipt.get("hosted_public_status") != "fail_closed_not_proven":
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "hosted public status must remain fail-closed"})
    if not str(receipt.get("publication_status", "")).startswith("blocked_"):
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "publication status must stay blocked"})
    if "public-release-ready" in json.dumps(receipt).lower():
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "suite probe must not imply public release readiness"})

    summary = receipt.get("summary", {})
    if summary.get("selected_specimen_count", 0) < len(required_selected_ids):
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "missing_summary_count": "selected_specimen_count"})
    if summary.get("ok_count") != summary.get("selected_specimen_count"):
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "all selected specimen rows must pass"})
    for count_name in ("failed_count", "missing_candidate_count", "not_landed_count"):
        if summary.get(count_name) != 0:
            failures.append({"path": "receipts/specimen_suite_probe_latest.json", "nonzero_summary_count": count_name})
    if summary.get("status_authority_nodes") != [
        "specimen_suite_probe_evaluator",
        "individual_specimen_receipts",
        "publication_gate",
        "hosted_public_ci_gate",
    ]:
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "status authority nodes mismatch"})

    specimen_results = receipt.get("specimen_results", [])
    if len(specimen_results) < len(required_selected_ids):
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "missing specimen result rows"})
    for row in specimen_results:
        if not isinstance(row, dict):
            failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "specimen result row must be an object"})
            continue
        candidate_id = row.get("candidate_id")
        if candidate_id not in required_selected_ids:
            failures.append({"path": "receipts/specimen_suite_probe_latest.json", "unexpected_candidate_id": candidate_id})
        if row.get("status") != "ok" or row.get("builder_status") != "ok":
            failures.append({"candidate_id": candidate_id, "reason": "specimen suite row must be ok"})
        if row.get("status_authority") != "specimen_suite_probe_evaluator_only":
            failures.append({"candidate_id": candidate_id, "reason": "unexpected status authority"})
        if not row.get("primary_artifact_ref") or row.get("artifact_ref_count", 0) < 1 or not row.get("receipt_path"):
            failures.append({"candidate_id": candidate_id, "reason": "specimen suite row must expose primary artifact and receipt path"})
        for ref in list(row.get("artifact_refs", [])) + [row.get("receipt_ref")]:
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"candidate_id": candidate_id, "missing_ref": ref})
        if row.get("missing_refs"):
            failures.append({"candidate_id": candidate_id, "reason": "missing_refs must be empty", "missing_refs": row.get("missing_refs")})

    if board:
        board_ids = set(board.get("selected_specimen_ids", []))
        if board.get("kind") != "microcosm_selection_board" or board.get("id") != "microcosm.specimen_suite.selection_board":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "unexpected board identity"})
        if board.get("status") != "ok":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "selection board must be ok"})
        if board.get("authority_posture") != "local_specimen_selection_board_not_publication_or_hosted_authority":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "unexpected board authority posture"})
        if board_ids != required_selected_ids:
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board selected ids must match suite ids"})
        if set(board.get("ranked_candidate_ids", [])) != required_selected_ids or not board.get("highest_score_candidate_id"):
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board ranking must cover all selected specimens"})
        if board.get("apex_reviewer_board_ref") != "microcosms/specimen_suite/apex_reviewer_board.json":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing apex reviewer board reference"})
        if board.get("claim_inference_map_ref") != "microcosms/specimen_suite/claim_inference_map.json":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing claim-inference map reference"})
        if board.get("quality_delta_board_ref") != "microcosms/specimen_suite/quality_delta_board.json":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing quality-delta board reference"})
        if board.get("dogfood_control_loop_receipt_ref") != "microcosms/specimen_suite/dogfood_control_loop_receipt.json":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing dogfood control-loop receipt reference"})
        if board.get("living_substrate_witness_ref") != "microcosms/specimen_suite/living_substrate_witness.json":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing living-substrate witness reference"})
        if board.get("macrocosm_contribution_assay_ref") != "microcosms/specimen_suite/macrocosm_contribution_assay.json":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing macrocosm contribution assay reference"})
        if board.get("release_microcosm_ontology_ref") != "microcosms/specimen_suite/release_microcosm_ontology.json":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing release microcosm ontology reference"})
        if board.get("work_metabolism_bridge_ref") != work_bridge_ref:
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board missing work-metabolism bridge reference"})
        if board.get("hosted_public_status") != "fail_closed_not_proven":
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board hosted public status must stay fail-closed"})
        if not str(board.get("publication_status", "")).startswith("blocked_"):
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board publication status must stay blocked"})
        if "public-release-ready" in json.dumps(board).lower():
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board must not imply public release readiness"})
        board_rows = board.get("rows", [])
        if not isinstance(board_rows, list) or len(board_rows) != len(required_selected_ids):
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board must contain one row per selected specimen"})
        for row in (board_rows if isinstance(board_rows, list) else []):
            if not isinstance(row, dict):
                failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board row must be an object"})
                continue
            candidate_id = row.get("candidate_id")
            if candidate_id not in required_selected_ids:
                failures.append({"path": "microcosms/specimen_suite/selection_board.json", "unexpected_candidate_id": candidate_id})
            if row.get("status_authority") != "specimen_suite_selection_board_evaluator_only":
                failures.append({"candidate_id": candidate_id, "reason": "unexpected board row status authority"})
            if int(row.get("selection_score", 0)) <= 0 or not isinstance(row.get("score_breakdown"), dict):
                failures.append({"candidate_id": candidate_id, "reason": "board row must expose positive transparent score breakdown"})
            for required_field in ("primary_artifact_ref", "receipt_ref", "improvement_delta", "anti_claims", "hosted_public_status", "publication_status"):
                if not row.get(required_field):
                    failures.append({"candidate_id": candidate_id, "missing_board_field": required_field})
            for ref in list(row.get("artifact_refs", [])) + [row.get("receipt_ref")]:
                if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                    failures.append({"candidate_id": candidate_id, "missing_board_ref": ref})
        board_anti_claims = board.get("anti_claims", [])
        if not isinstance(board_anti_claims, list) or len(board_anti_claims) < 4:
            failures.append({"path": "microcosms/specimen_suite/selection_board.json", "reason": "board anti_claims must cover hosted, publication, score, and equivalence boundaries"})
    if claim_map:
        if claim_map.get("kind") != "microcosm_claim_inference_map" or claim_map.get("id") != "microcosm.specimen_suite.claim_inference_map":
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "unexpected claim-inference map identity"})
        if claim_map.get("status") != "ok":
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "claim-inference map must be ok"})
        if claim_map.get("authority_posture") != "local_specimen_selection_board_not_publication_or_hosted_authority":
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "unexpected claim-inference map authority posture"})
        if claim_map.get("hosted_public_status") != "fail_closed_not_proven":
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "claim-inference map hosted public status must stay fail-closed"})
        if not str(claim_map.get("publication_status", "")).startswith("blocked_"):
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "claim-inference map publication status must stay blocked"})
        claim_rows = claim_map.get("rows", [])
        if not isinstance(claim_rows, list) or len(claim_rows) < 5:
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "claim-inference map must expose at least five inference rows"})
            claim_rows = []
        for row in claim_rows:
            if not isinstance(row, dict):
                failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "claim-inference row must be an object"})
                continue
            inference_id = row.get("inference_id")
            if row.get("status_authority") != "claim_inference_map_evaluator_only":
                failures.append({"inference_id": inference_id, "reason": "unexpected claim row status authority"})
            for required_field in (
                "human_claim",
                "selected_specimen_ids",
                "evidence_refs",
                "cold_start_command_refs",
                "authority_boundary",
                "anti_claims",
                "next_upgrade",
                "what_would_downgrade",
            ):
                if not row.get(required_field):
                    failures.append({"inference_id": inference_id, "missing_claim_map_field": required_field})
            if row.get("missing_refs"):
                failures.append({"inference_id": inference_id, "reason": "claim row missing_refs must be empty", "missing_refs": row.get("missing_refs")})
            for ref in row.get("evidence_refs", []):
                if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                    failures.append({"inference_id": inference_id, "missing_evidence_ref": ref})
        summary = claim_map.get("summary", {})
        if summary.get("status_authority_nodes") != [
            "claim_inference_map_evaluator",
            "individual_specimen_receipts",
            "publication_gate",
            "hosted_public_ci_gate",
        ]:
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "claim-inference status authority nodes mismatch"})
        if int(summary.get("missing_ref_count", -1)) != 0:
            failures.append({"path": "microcosms/specimen_suite/claim_inference_map.json", "reason": "claim-inference map missing_ref_count must be zero"})
    if quality_delta_board:
        if quality_delta_board.get("kind") != "microcosm_quality_delta_board" or quality_delta_board.get("id") != "microcosm.specimen_suite.quality_delta_board":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "unexpected quality-delta board identity"})
        if quality_delta_board.get("status") != "ok":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality-delta board must be ok"})
        if quality_delta_board.get("authority_posture") != "local_specimen_selection_board_not_publication_or_hosted_authority":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "unexpected quality-delta board authority posture"})
        if quality_delta_board.get("selection_board_ref") != "microcosms/specimen_suite/selection_board.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing selection board ref"})
        if quality_delta_board.get("apex_reviewer_board_ref") != "microcosms/specimen_suite/apex_reviewer_board.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing apex board ref"})
        if quality_delta_board.get("claim_inference_map_ref") != "microcosms/specimen_suite/claim_inference_map.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing claim map ref"})
        if quality_delta_board.get("release_authority_handshake_ref") != "microcosms/public_release_package_manifest_gate/release_authority_handshake.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing release authority handshake ref"})
        if quality_delta_board.get("dogfood_control_loop_receipt_ref") != "microcosms/specimen_suite/dogfood_control_loop_receipt.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing dogfood control-loop ref"})
        if quality_delta_board.get("macrocosm_contribution_assay_ref") != "microcosms/specimen_suite/macrocosm_contribution_assay.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing macrocosm contribution assay ref"})
        if quality_delta_board.get("release_microcosm_ontology_ref") != "microcosms/specimen_suite/release_microcosm_ontology.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing release microcosm ontology ref"})
        quality_rows = quality_delta_board.get("rows", [])
        summary = quality_delta_board.get("summary", {})
        all_considered = quality_delta_board.get("all_microcosms_considered", [])
        if not isinstance(all_considered, list) or len(all_considered) < 17:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must consider all release microcosms"})
        if not isinstance(quality_rows, list) or len(quality_rows) != len(all_considered):
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board rows must match considered microcosms"})
            quality_rows = []
        if int(summary.get("all_microcosms_considered_count", 0)) != len(all_considered):
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board summary count mismatch"})
        if int(summary.get("mission_thread_count", 0)) < 5:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must expose mission-thread coverage"})
        if not summary.get("top_patch_lane") or not summary.get("top_upgrade_candidate_id"):
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must name the top patch lane"})
        if int(summary.get("missing_ref_count", -1)) != 0:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing_ref_count must be zero"})
        if summary.get("previous_top_upgrade_candidate_id") != "public_release_package_manifest_gate_microcosm":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must remember the previously selected package-manifest gap"})
        applied_patch_count = int(summary.get("applied_patch_count", 0))
        if summary.get("did_quality_board_update_after_applied_patch") not in {True, False}:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must state whether an applied patch advanced the board"})
        if applied_patch_count and "public_release_package_manifest_gate_microcosm" not in summary.get("applied_patch_candidate_ids", []):
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board applied patch ids must name the observed patch"})
        if summary.get("top_upgrade_candidate_id") == "public_release_package_manifest_gate_microcosm":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must not keep selecting the applied package-manifest bridge"})
        if summary.get("next_gap_after_applied_patch") != summary.get("top_upgrade_candidate_id"):
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board next gap must match the current top open gap"})
        if summary.get("next_public_boundary_gap") != next_public_boundary_gap:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must preserve the current public-boundary gap"})
        if summary.get("next_capability_witness_gap") != "erdos257_period_noncollapse_formal_math_strike":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must split out the living capability-witness gap"})
        if summary.get("flagship_living_mission_witness_ref") != "microcosms/specimen_suite/living_substrate_witness.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing flagship living mission witness ref"})
        if summary.get("previous_original_contribution_gap") != "contribution_first_cold_reviewer_route":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must remember the contribution-first route gap"})
        if summary.get("contribution_first_route_status") != expected_contribution_first_route_status:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must mark the cold-entry atlas as landed on the contribution-first route"})
        if summary.get("applied_original_contribution_gap") != applied_original_contribution_gap:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must mark the concept-graph self-index hardening gap as applied"})
        if summary.get("work_metabolism_bridge_status") != "bridge_landed":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must consume the landed work-metabolism bridge"})
        if summary.get("work_metabolism_bridge_ref") != work_bridge_ref:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board missing work-metabolism bridge ref"})
        if summary.get("next_original_contribution_gap") != next_gap_after_work_bridge:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must advance the original-contribution gap after the work-metabolism bridge"})
        if summary.get("next_original_contribution_ref") != "microcosms/concept_graph_cards/cold_entry_atlas.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board next original-contribution ref must point at the cold-entry atlas"})
        if summary.get("release_microcosm_ontology_ref") != "microcosms/specimen_suite/release_microcosm_ontology.json":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board summary missing release ontology ref"})
        if summary.get("next_core_upgrade_owner") != next_owner_after_work_bridge:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must name the next core upgrade owner"})
        if summary.get("selected_macrocosm_contribution") != "self_indexing_cognitive_substrate":
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must foreground the selected macrocosm contribution"})
        applied_observations = quality_delta_board.get("applied_patch_observations", [])
        if not isinstance(applied_observations, list) or not applied_observations:
            failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board must expose applied patch observations"})
        else:
            first_observation = applied_observations[0]
            if not isinstance(first_observation, dict) or first_observation.get("status") != "satisfied":
                failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "release authority handshake observation must be satisfied"})
            elif first_observation.get("release_authority_handshake_ref") != "microcosms/public_release_package_manifest_gate/release_authority_handshake.json":
                failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "applied patch observation must point to the release authority handshake"})
        for row in quality_rows:
            if not isinstance(row, dict):
                failures.append({"path": "microcosms/specimen_suite/quality_delta_board.json", "reason": "quality board row must be an object"})
                continue
            candidate_id = row.get("candidate_id")
            if row.get("status_authority") != "apex_quality_delta_board_evaluator_only":
                failures.append({"candidate_id": candidate_id, "reason": "unexpected quality board row status authority"})
            for required_field in (
                "current_claim",
                "strongest_inference_supported",
                "mission_thread_ids",
                "composition_role",
                "missing_bridge",
                "top_upgrade",
                "what_would_downgrade",
                "anti_claims",
                "candidate_patch_lane",
                "evidence_refs",
                "score_breakdown",
            ):
                if not row.get(required_field):
                    failures.append({"candidate_id": candidate_id, "missing_quality_field": required_field})
            score_breakdown = row.get("score_breakdown", {})
            if not isinstance(score_breakdown, dict) or "positive" not in score_breakdown or "penalties" not in score_breakdown:
                failures.append({"candidate_id": candidate_id, "reason": "quality row missing transparent score breakdown"})
            if row.get("missing_refs"):
                failures.append({"candidate_id": candidate_id, "reason": "quality row missing_refs must be empty", "missing_refs": row.get("missing_refs")})
            for ref in row.get("evidence_refs", []):
                if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                    failures.append({"candidate_id": candidate_id, "missing_quality_ref": ref})
            if candidate_id == "public_release_package_manifest_gate_microcosm":
                if row.get("candidate_patch_lane") != "applied_patch_observed:authority_never_collapses":
                    failures.append({"candidate_id": candidate_id, "reason": "package-manifest bridge must be marked as an observed applied patch"})
                if row.get("applied_patch_status") != "observed_satisfied":
                    failures.append({"candidate_id": candidate_id, "reason": "package-manifest applied patch status must be observed_satisfied"})
                if "microcosms/public_release_package_manifest_gate/release_authority_handshake.json" not in row.get("applied_patch_refs", []):
                    failures.append({"candidate_id": candidate_id, "reason": "package-manifest applied patch refs must include release_authority_handshake.json"})
                satisfaction_refs = row.get("mission_thread_satisfaction_refs", [])
                if not isinstance(satisfaction_refs, list) or not satisfaction_refs:
                    failures.append({"candidate_id": candidate_id, "reason": "package-manifest bridge must expose mission-thread satisfaction refs"})
                elif satisfaction_refs[0].get("authority_collapse_count") != 0:
                    failures.append({"candidate_id": candidate_id, "reason": "package-manifest satisfaction ref must preserve zero authority collapse"})
    if dogfood_control_loop:
        if dogfood_control_loop.get("kind") != "microcosm_dogfood_control_loop_receipt" or dogfood_control_loop.get("id") != "microcosm.specimen_suite.dogfood_control_loop_receipt":
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "unexpected dogfood control-loop receipt identity"})
        if dogfood_control_loop.get("status") not in {"ok", "failed"}:
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "dogfood control-loop receipt must expose a typed status"})
        if dogfood_control_loop.get("authority_posture") != "local_specimen_selection_board_not_publication_or_hosted_authority":
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "unexpected dogfood authority posture"})
        selected_before = dogfood_control_loop.get("selected_gap_before", {})
        if selected_before.get("candidate_id") != "public_release_package_manifest_gate_microcosm":
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "dogfood receipt must record package-manifest gate as the selected gap before the patch"})
        action_taken = dogfood_control_loop.get("action_taken", {})
        if action_taken.get("patch_type") != "quality_board_perception_patch":
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "dogfood receipt must name the quality-board perception patch"})
        learning = dogfood_control_loop.get("learning", {})
        if learning.get("did_quality_board_update") not in {True, False}:
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "dogfood receipt must state whether the board advanced"})
        if learning.get("previous_gap_candidate_id") != "public_release_package_manifest_gate_microcosm":
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "dogfood receipt previous gap mismatch"})
        if quality_delta_board and learning.get("next_gap_after_patch") != quality_delta_board.get("summary", {}).get("next_gap_after_applied_patch"):
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "dogfood receipt next gap must match quality board"})
        if dogfood_control_loop.get("missing_refs"):
            failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "reason": "dogfood receipt missing_refs must be empty", "missing_refs": dogfood_control_loop.get("missing_refs")})
        for ref in dogfood_control_loop.get("input_refs", []) + dogfood_control_loop.get("proof", {}).get("proof_refs", []):
            if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                failures.append({"path": "microcosms/specimen_suite/dogfood_control_loop_receipt.json", "missing_ref": ref})
    if living_substrate_witness:
        if living_substrate_witness.get("kind") != "microcosm_living_substrate_witness" or living_substrate_witness.get("id") != "microcosm.specimen_suite.living_substrate_witness":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "unexpected living-substrate witness identity"})
        if living_substrate_witness.get("status") != "ok":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living-substrate witness must be ok"})
        if living_substrate_witness.get("authority_posture") != "local_living_substrate_witness_not_math_proof_or_publication_authority":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "unexpected living-substrate witness authority posture"})
        if living_substrate_witness.get("selected_flagship_mission") != "erdos257_period_noncollapse_formal_math_strike":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must name the selected flagship mission"})
        gap_split = living_substrate_witness.get("quality_gap_split", {})
        if gap_split.get("next_public_boundary_gap") != next_public_boundary_gap:
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must preserve the current public-boundary gap"})
        if gap_split.get("next_capability_witness_gap") != "erdos257_period_noncollapse_formal_math_strike":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must expose the capability-witness gap"})
        artifact_output = living_substrate_witness.get("artifact_output", {})
        if artifact_output.get("cases_checked") != 7925 or artifact_output.get("passing_cases") != 7925:
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must preserve bounded finite-search counts"})
        if artifact_output.get("fragility_failures") != 93 or artifact_output.get("proof_kernel_status") != "blocked_by_fragility_or_route_gap":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must preserve proof-fragility boundary"})
        evidence_boundary = living_substrate_witness.get("evidence_boundary", {})
        does_not_prove = evidence_boundary.get("does_not_prove", [])
        if "Erdos #257 is solved" not in does_not_prove:
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must preserve Erdos anti-claim"})
        if living_substrate_witness.get("missing_refs"):
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness missing_refs must be empty", "missing_refs": living_substrate_witness.get("missing_refs")})
        if len(living_substrate_witness.get("mission_trace", [])) < 5:
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must expose a mission trace"})
        if not living_substrate_witness.get("live_source_refs") or not living_substrate_witness.get("source_commit_refs"):
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must name live source refs and source commits"})
        anti_claims = living_substrate_witness.get("anti_claims", [])
        if not isinstance(anti_claims, list) or len(anti_claims) < 5:
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness anti_claims must preserve proof/public/private boundaries"})
        for ref in living_substrate_witness.get("release_root_evidence_refs", []):
            if isinstance(ref, str) and ref and ref != "microcosms/specimen_suite/living_substrate_witness.json" and not _path_ref_exists(root, ref):
                failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "missing_ref": ref})
        if living_substrate_witness.get("role") != "exemplar_capability_witness":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must be marked as an exemplar capability witness"})
        if living_substrate_witness.get("macrocosm_identity_role") != "not_macrocosm_identity":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must not be the macrocosm identity"})
        if living_substrate_witness.get("contribution_context_ref") != "microcosms/specimen_suite/macrocosm_contribution_assay.json":
            failures.append({"path": "microcosms/specimen_suite/living_substrate_witness.json", "reason": "living witness must point to contribution assay context"})
    if macrocosm_contribution_assay:
        if (
            macrocosm_contribution_assay.get("kind") != "macrocosm_contribution_assay"
            or macrocosm_contribution_assay.get("id") != "microcosm.specimen_suite.macrocosm_contribution_assay"
        ):
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "unexpected macrocosm contribution assay identity"})
        if macrocosm_contribution_assay.get("status") != "ok":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "macrocosm contribution assay must be ok"})
        if macrocosm_contribution_assay.get("authority_posture") != "local_contribution_assay_not_originality_or_publication_authority":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "unexpected contribution assay authority posture"})
        selected_contribution = macrocosm_contribution_assay.get("selected_contribution", {})
        if selected_contribution.get("hypothesis_id") != "self_indexing_cognitive_substrate":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must select self-indexing cognitive substrate"})
        if "workflow persistence" not in str(selected_contribution.get("why_not_rehash", "")).lower():
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "selected contribution must explain why it is not workflow persistence"})
        summary = macrocosm_contribution_assay.get("summary", {})
        if int(summary.get("hypothesis_count", 0)) < 5:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must compare at least five contribution hypotheses"})
        if int(summary.get("prior_art_boundary_count", 0)) < 5:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must keep public prior-art boundaries explicit"})
        if summary.get("role_of_erdos_witness") != "exemplar_capability_witness_not_macrocosm_identity":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must demote Erdos to exemplar role"})
        if int(summary.get("missing_ref_count", -1)) != 0 or macrocosm_contribution_assay.get("missing_refs"):
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "contribution assay missing_refs must be empty", "missing_refs": macrocosm_contribution_assay.get("missing_refs")})
        if macrocosm_contribution_assay.get("previous_original_contribution_gap") != "contribution_first_cold_reviewer_route":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must remember the contribution-first route gap"})
        if macrocosm_contribution_assay.get("applied_original_contribution_gap") != applied_original_contribution_gap:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must mark the concept-graph self-index hardening gap as applied"})
        if macrocosm_contribution_assay.get("work_metabolism_bridge_status") != "bridge_landed":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must consume the landed work-metabolism bridge"})
        if macrocosm_contribution_assay.get("work_metabolism_bridge_ref") != work_bridge_ref:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay missing work-metabolism bridge ref"})
        if macrocosm_contribution_assay.get("next_original_contribution_gap") != next_gap_after_work_bridge:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must advance the next original contribution gap"})
        if macrocosm_contribution_assay.get("release_microcosm_ontology_ref") != "microcosms/specimen_suite/release_microcosm_ontology.json":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay missing release ontology ref"})
        role_of_erdos = macrocosm_contribution_assay.get("role_of_erdos_witness", {})
        if role_of_erdos.get("role") != "exemplar_capability_witness_not_macrocosm_identity":
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "Erdos witness role must be bounded"})
        prior_art_rows = macrocosm_contribution_assay.get("public_prior_art_boundary", [])
        if not isinstance(prior_art_rows, list) or len(prior_art_rows) < 5:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "missing public prior-art boundary rows"})
        for row in prior_art_rows if isinstance(prior_art_rows, list) else []:
            if not isinstance(row, dict):
                failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "prior-art row must be an object"})
                continue
            for required_field in ("prior_art_id", "url", "already_public_component", "boundary"):
                if not row.get(required_field):
                    failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "missing_prior_art_field": required_field})
        hypotheses = macrocosm_contribution_assay.get("contribution_hypotheses", [])
        selected_rows = [row for row in hypotheses if isinstance(row, dict) and row.get("selected")]
        if len(selected_rows) != 1:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must select exactly one primary contribution"})
        for row in hypotheses if isinstance(hypotheses, list) else []:
            if not isinstance(row, dict):
                failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "hypothesis row must be an object"})
                continue
            if row.get("status_authority") != "macrocosm_contribution_assay_evaluator_only":
                failures.append({"hypothesis_id": row.get("hypothesis_id"), "reason": "unexpected contribution hypothesis status authority"})
            for required_field in (
                "claim",
                "why_not_rehash",
                "public_prior_art_boundary",
                "internal_evidence_refs",
                "public_safe_witness_refs",
                "weakest_gap",
                "next_patch_lane",
                "anti_claims",
                "score_breakdown",
            ):
                if not row.get(required_field):
                    failures.append({"hypothesis_id": row.get("hypothesis_id"), "missing_contribution_field": required_field})
            if row.get("missing_refs"):
                failures.append({"hypothesis_id": row.get("hypothesis_id"), "reason": "contribution hypothesis missing_refs must be empty", "missing_refs": row.get("missing_refs")})
            for ref in list(row.get("internal_evidence_refs", [])) + list(row.get("public_safe_witness_refs", [])):
                if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                    failures.append({"hypothesis_id": row.get("hypothesis_id"), "missing_contribution_ref": ref})
        anti_claims = macrocosm_contribution_assay.get("anti_claims", [])
        if "the Erdos witness is the macrocosm identity" not in anti_claims:
            failures.append({"path": "microcosms/specimen_suite/macrocosm_contribution_assay.json", "reason": "assay must preserve Erdos anti-claim"})
    if release_microcosm_ontology:
        if (
            release_microcosm_ontology.get("kind") != "release_microcosm_ontology"
            or release_microcosm_ontology.get("id") != "microcosm.specimen_suite.release_microcosm_ontology"
        ):
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "unexpected release ontology identity"})
        if release_microcosm_ontology.get("status") != "ok":
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must be ok"})
        if release_microcosm_ontology.get("authority_posture") != "local_release_microcosm_ontology_not_originality_or_publication_authority":
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "unexpected release ontology authority posture"})
        if release_microcosm_ontology.get("selected_contribution") != "self_indexing_cognitive_substrate":
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must foreground the selected contribution"})
        for required_ref_field, expected_ref in (
            ("macrocosm_contribution_assay_ref", "microcosms/specimen_suite/macrocosm_contribution_assay.json"),
            ("quality_delta_board_ref", "microcosms/specimen_suite/quality_delta_board.json"),
            ("claim_inference_map_ref", "microcosms/specimen_suite/claim_inference_map.json"),
        ):
            if release_microcosm_ontology.get(required_ref_field) != expected_ref:
                failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "missing_ref_field": required_ref_field})
        summary = release_microcosm_ontology.get("summary", {})
        if int(summary.get("release_candidate_row_count", 0)) < 17:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must classify every release candidate"})
        if int(summary.get("core_microcosm_count", 0)) < 7:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must expose a meaningful core set"})
        if int(summary.get("support_count", 0)) < 3:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must expose supporting surfaces"})
        if int(summary.get("exemplar_count", 0)) < 1:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must preserve exemplars"})
        if int(summary.get("boundary_count", 0)) != 0:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must keep retired downstream-release boundary gates out of active ontology"})
        if int(summary.get("missing_ref_count", -1)) != 0 or release_microcosm_ontology.get("missing_refs"):
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology missing_refs must be empty", "missing_refs": release_microcosm_ontology.get("missing_refs")})
        if int(summary.get("missing_role_count", -1)) != 0:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must cover every ontology role"})
        if summary.get("previous_original_contribution_gap") != "contribution_first_cold_reviewer_route":
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must close over the previous contribution route gap"})
        if summary.get("applied_original_contribution_gap") != applied_original_contribution_gap:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must mark the concept-graph self-index hardening gap as applied"})
        if summary.get("work_metabolism_bridge_status") != "bridge_landed":
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must consume the landed work-metabolism bridge"})
        if summary.get("work_metabolism_bridge_ref") != work_bridge_ref:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology missing work-metabolism bridge ref"})
        if summary.get("next_original_contribution_gap") != next_gap_after_work_bridge:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must name the next core contribution gap after the bridge"})
        if summary.get("next_upgrade_owner") != next_owner_after_work_bridge:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must name the next upgrade owner"})
        role_ids = {row.get("role_id") for row in release_microcosm_ontology.get("ontology_roles", []) if isinstance(row, dict)}
        expected_role_ids = {
            "constitution",
            "perception",
            "work_memory",
            "work_metabolism",
            "authority_boundary",
            "evaluation_proof",
            "repair_replay_learning",
            "release_distillation",
            "cold_reviewer_operation",
            "capability_exemplar",
        }
        if not expected_role_ids.issubset(role_ids):
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology missing role definitions"})
        structural_analogues = release_microcosm_ontology.get("structural_analogues", [])
        if not isinstance(structural_analogues, list) or len(structural_analogues) < 4:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must expose structural analogues"})
        for row in structural_analogues if isinstance(structural_analogues, list) else []:
            if not isinstance(row, dict):
                failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "structural analogue row must be an object"})
                continue
            for required_field in ("analogue_id", "url", "borrowed_mechanism", "boundary"):
                if not row.get(required_field):
                    failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "missing_structural_analogue_field": required_field})
        ontology_rows = release_microcosm_ontology.get("rows", [])
        if not isinstance(ontology_rows, list) or len(ontology_rows) < 19:
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must include generated and candidate surfaces"})
            ontology_rows = []
        ontology_by_id = {
            row.get("microcosm_id"): row
            for row in ontology_rows
            if isinstance(row, dict)
        }
        for required_id, required_status in (
            ("macrocosm_contribution_assay", "core"),
            ("quality_delta_board", "core"),
            ("dogfood_control_loop", "core"),
            ("task_ledger_cap_economy_microcosm", "core"),
            ("concurrency_transaction_mission_control_microcosm", "core"),
            ("living_substrate_witness", "exemplar"),
            ("system_logic_substrate", "core"),
            ("source_shuttle_microcosm", "core"),
            ("verisoftbench_diagnostic_specimen_microcosm", "exemplar"),
        ):
            row = ontology_by_id.get(required_id)
            if not row or row.get("core_status") != required_status:
                failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "microcosm_id": required_id, "reason": f"expected {required_status} ontology classification"})
        route_steps = release_microcosm_ontology.get("contribution_first_route", [])
        route_step_ids = {step.get("step_id") for step in route_steps if isinstance(step, dict)}
        if not {"inspect_contribution", "inspect_release_ontology", "inspect_core_mechanisms", "inspect_boundary_gates"}.issubset(route_step_ids):
            failures.append({"path": "microcosms/specimen_suite/release_microcosm_ontology.json", "reason": "release ontology must expose contribution-first route steps"})
        for row in ontology_rows:
            if not isinstance(row, dict):
                continue
            microcosm_id = row.get("microcosm_id")
            if row.get("status_authority") != "release_microcosm_ontology_evaluator_only":
                failures.append({"microcosm_id": microcosm_id, "reason": "unexpected release ontology row authority"})
            for required_field in (
                "current_role",
                "contribution_role",
                "core_status",
                "why_included",
                "evidence_refs",
                "claim_refs",
                "standards_axiom_refs",
                "provenance_refs",
                "reviewer_step",
                "weakness",
                "upgrade_action",
                "anti_claims",
            ):
                if not row.get(required_field):
                    failures.append({"microcosm_id": microcosm_id, "missing_release_ontology_field": required_field})
            if row.get("missing_refs"):
                failures.append({"microcosm_id": microcosm_id, "reason": "release ontology row missing_refs must be empty", "missing_refs": row.get("missing_refs")})
            for ref in list(row.get("evidence_refs", [])) + list(row.get("claim_refs", [])) + list(row.get("provenance_refs", [])):
                if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                    failures.append({"microcosm_id": microcosm_id, "missing_release_ontology_ref": ref})
    if apex_board:
        if apex_board.get("kind") != "apex_microcosm_reviewer_board" or apex_board.get("id") != "microcosm.specimen_suite.apex_reviewer_board":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "unexpected apex reviewer board identity"})
        if apex_board.get("status") != "ok":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex reviewer board must be ok"})
        if apex_board.get("authority_posture") != "local_specimen_selection_board_not_publication_or_hosted_authority":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "unexpected apex reviewer board authority posture"})
        if apex_board.get("proof_status", {}).get("hosted_public") != "fail_closed_not_proven":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex hosted public proof status must stay fail-closed"})
        if not str(apex_board.get("proof_status", {}).get("publication", "")).startswith("blocked_"):
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex publication proof status must stay blocked"})
        if len(apex_board.get("top_inference_ids", [])) < 5:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board must expose top inference ids"})
        if len(apex_board.get("best_specimens", [])) < len(required_selected_ids):
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board must include selected best specimens"})
        if len(apex_board.get("reviewer_path", [])) < 7:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board must include reviewer flight path"})
        if apex_board.get("missing_refs"):
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing_refs must be empty", "missing_refs": apex_board.get("missing_refs")})
        if apex_board.get("output_refs", {}).get("quality_delta_board") != "microcosms/specimen_suite/quality_delta_board.json":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing quality board output ref"})
        if apex_board.get("output_refs", {}).get("living_substrate_witness") != "microcosms/specimen_suite/living_substrate_witness.json":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing living-substrate witness output ref"})
        if apex_board.get("output_refs", {}).get("macrocosm_contribution_assay") != "microcosms/specimen_suite/macrocosm_contribution_assay.json":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing macrocosm contribution assay output ref"})
        if apex_board.get("output_refs", {}).get("release_microcosm_ontology") != "microcosms/specimen_suite/release_microcosm_ontology.json":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing release ontology output ref"})
        if apex_board.get("output_refs", {}).get("work_metabolism_bridge") != work_bridge_ref:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing work-metabolism bridge output ref"})
        if not apex_board.get("quality_delta_summary", {}).get("top_patch_lane"):
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing quality delta summary"})
        if apex_board.get("macrocosm_contribution_summary", {}).get("selected_contribution_id") != "self_indexing_cognitive_substrate":
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing selected macrocosm contribution summary"})
        if apex_board.get("release_microcosm_ontology_summary", {}).get("next_original_contribution_gap") != next_gap_after_work_bridge:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex board missing release ontology summary"})
        if "inspect_quality_delta_tournament" not in {step.get("step_id") for step in apex_board.get("reviewer_path", []) if isinstance(step, dict)}:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex reviewer path must inspect quality delta tournament"})
        if "inspect_macrocosm_contribution_assay" not in {step.get("step_id") for step in apex_board.get("reviewer_path", []) if isinstance(step, dict)}:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex reviewer path must inspect macrocosm contribution assay"})
        if "inspect_release_microcosm_ontology" not in {step.get("step_id") for step in apex_board.get("reviewer_path", []) if isinstance(step, dict)}:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex reviewer path must inspect release microcosm ontology"})
        if "inspect_work_metabolism_bridge" not in {step.get("step_id") for step in apex_board.get("reviewer_path", []) if isinstance(step, dict)}:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex reviewer path must inspect the work-metabolism bridge"})
        if "inspect_living_substrate_witness" not in {step.get("step_id") for step in apex_board.get("reviewer_path", []) if isinstance(step, dict)}:
            failures.append({"path": "microcosms/specimen_suite/apex_reviewer_board.json", "reason": "apex reviewer path must inspect the living-substrate witness"})
        for step in apex_board.get("reviewer_path", []):
            if isinstance(step, dict):
                for ref in step.get("read_refs", []):
                    if ref in {
                        "microcosms/specimen_suite/apex_reviewer_board.json",
                        "microcosms/specimen_suite/claim_inference_map.json",
                        "microcosms/specimen_suite/quality_delta_board.json",
                        "microcosms/specimen_suite/living_substrate_witness.json",
                        "microcosms/specimen_suite/macrocosm_contribution_assay.json",
                        "microcosms/specimen_suite/release_microcosm_ontology.json",
                        work_bridge_ref,
                    }:
                        continue
                    if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
                        failures.append({"step_id": step.get("step_id"), "missing_read_ref": ref})
    if board_readme_path.exists():
        readme = board_readme_path.read_text(encoding="utf-8")
        for required_text in (
            "PYTHONPATH=src python3 -m idea_microcosm.cli run-specimen-suite-probe --root . --write-receipt",
            "Selection scores are local routing aids, not public claims.",
            "This board does not prove hosted public CI.",
            "apex reviewer board",
            "claim-inference map",
            "quality-delta board",
            "dogfood control-loop receipt",
            "macrocosm contribution assay",
            "release microcosm ontology",
            "living-substrate witness",
        ):
            if required_text not in readme:
                failures.append({"path": "microcosms/specimen_suite/README.md", "missing_text": required_text})

    evidence_refs = set(receipt.get("evidence_refs", []))
    required_evidence_refs = {
        "src/idea_microcosm/specimen_suite_probe.py",
        "src/idea_microcosm/cli.py",
        "registry/release_candidates.json",
        "state/release_candidate_portfolio.json",
        "registry/validators.json",
        "skills/cold_start_agent.md",
        "microcosms/specimen_suite/selection_board.json",
        "microcosms/specimen_suite/apex_reviewer_board.json",
        "microcosms/specimen_suite/claim_inference_map.json",
        "microcosms/specimen_suite/quality_delta_board.json",
        "microcosms/specimen_suite/dogfood_control_loop_receipt.json",
        "microcosms/specimen_suite/living_substrate_witness.json",
        "microcosms/specimen_suite/macrocosm_contribution_assay.json",
        "microcosms/specimen_suite/release_microcosm_ontology.json",
        "microcosms/specimen_suite/README.md",
        "microcosms/executable_grammar_metabolism/receipt.json",
        "microcosms/task_ledger_cap_economy/receipt.json",
        "microcosms/lab_evolve_failure_replay/receipt.json",
        "microcosms/provider_harness_canary/receipt.json",
        "microcosms/atlas_navigation_bands/receipt.json",
        "microcosms/cold_start_agent_skills_pack/receipt.json",
        "microcosms/status_preserving_control_plane/receipt.json",
    }
    missing_evidence_refs = sorted(required_evidence_refs - evidence_refs)
    if missing_evidence_refs:
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "missing_evidence_refs": missing_evidence_refs})
    for ref in evidence_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": "receipts/specimen_suite_probe_latest.json", "missing_evidence_ref": ref})
    anti_claims = receipt.get("anti_claims", [])
    if not isinstance(anti_claims, list) or len(anti_claims) < 4:
        failures.append({"path": "receipts/specimen_suite_probe_latest.json", "reason": "anti_claims must cover suite boundaries"})
    return failures


def _release_root_compiler_failures(root: Path) -> list[dict[str, Any]]:
    artifact_paths = {
        "release_branch_graph": BRANCH_GRAPH_PATH,
        "release_root_contract": ROOT_CONTRACT_PATH,
        "std_python_compliance_report": STD_PYTHON_REPORT_PATH,
        "release_root_compiler_receipt": RELEASE_ROOT_COMPILER_RECEIPT_PATH,
    }
    failures: list[dict[str, Any]] = []
    for rel in artifact_paths.values():
        if not (root / rel).exists():
            failures.append({"path": rel, "reason": "missing release-root compiler artifact"})
    if failures:
        return failures

    branch_graph = load_json(root / BRANCH_GRAPH_PATH)
    root_contract = load_json(root / ROOT_CONTRACT_PATH)
    std_report = load_json(root / STD_PYTHON_REPORT_PATH)
    receipt = load_json(root / RELEASE_ROOT_COMPILER_RECEIPT_PATH)
    failures.extend(validate_release_root_artifacts(root, branch_graph, root_contract, std_report))

    if branch_graph.get("schema_version") != "release_microcosm_branch_graph_v1":
        failures.append({"path": BRANCH_GRAPH_PATH, "reason": "unexpected branch graph schema"})
    if root_contract.get("schema_version") != "release_root_contract_v0":
        failures.append({"path": ROOT_CONTRACT_PATH, "reason": "unexpected root contract schema"})
    if std_report.get("schema_version") != "std_python_compliance_report_v0":
        failures.append({"path": STD_PYTHON_REPORT_PATH, "reason": "unexpected std_python report schema"})

    branch_status = branch_graph.get("status", {})
    if int(branch_status.get("branch_count", 0)) < 15:
        failures.append({"path": BRANCH_GRAPH_PATH, "reason": "branch graph must expose the release root as branches"})
    if int(branch_status.get("mission_thread_count", 0)) < 5:
        failures.append({"path": BRANCH_GRAPH_PATH, "reason": "branch graph must expose mission threads"})
    if int(branch_status.get("missing_ref_count", -1)) != 0:
        failures.append({"path": BRANCH_GRAPH_PATH, "reason": "branch graph refs must resolve"})
    if branch_graph.get("compliance_diagnostics", {}).get("public_boundary_status") != "fail_closed":
        failures.append({"path": BRANCH_GRAPH_PATH, "reason": "public boundary must remain fail-closed"})
    entry_tracks = branch_graph.get("entry_tracks", {})
    required_tracks = {
        "human_reviewer",
        "technical_cloner",
        "external_agent",
        "public_boundary_reviewer",
        "future_maintainer",
    }
    if not isinstance(entry_tracks, dict) or not required_tracks.issubset(set(entry_tracks)):
        present_tracks = set(entry_tracks if isinstance(entry_tracks, dict) else {})
        failures.append({"path": BRANCH_GRAPH_PATH, "missing_entry_tracks": sorted(required_tracks - present_tracks)})

    contract_status = root_contract.get("status", {})
    if int(contract_status.get("authority_collapse_count", -1)) != 0:
        failures.append({"path": ROOT_CONTRACT_PATH, "reason": "authority collapse count must stay zero"})
    if int(contract_status.get("projection_authority_violation_count", -1)) != 0:
        failures.append({"path": ROOT_CONTRACT_PATH, "reason": "projection authority violations must stay zero"})
    if int(contract_status.get("branch_rule_violation_count", -1)) != 0:
        failures.append({"path": ROOT_CONTRACT_PATH, "reason": "branch rule violations must stay zero"})
    constitutional_rule_ids = {
        row.get("rule_id")
        for row in root_contract.get("constitutional_rules", [])
        if isinstance(row, dict)
    }
    required_rule_ids = {
        "claim_routes_to_evidence_or_boundary",
        "projection_is_not_authority",
        "authority_never_collapses",
        "public_release_fail_closed",
        "standards_are_executable",
        "work_metabolism_is_durable",
    }
    missing_rule_ids = sorted(required_rule_ids - constitutional_rule_ids)
    if missing_rule_ids:
        failures.append({"path": ROOT_CONTRACT_PATH, "missing_constitutional_rule_ids": missing_rule_ids})

    report_summary = std_report.get("summary", {})
    if int(report_summary.get("scanned_count", 0)) <= 0:
        failures.append({"path": STD_PYTHON_REPORT_PATH, "reason": "std_python report must scan release Python files"})
    if int(report_summary.get("blocker_count", -1)) != 0:
        failures.append({"path": STD_PYTHON_REPORT_PATH, "reason": "std_python report must have zero blockers"})
    if "not public release approval" not in std_report.get("anti_claims", []):
        failures.append({"path": STD_PYTHON_REPORT_PATH, "reason": "std_python report must deny public release approval"})

    if receipt.get("kind") != "receipt" or receipt.get("id") != "receipt.release_root_compiler":
        failures.append({"path": RELEASE_ROOT_COMPILER_RECEIPT_PATH, "reason": "unexpected release-root compiler receipt identity"})
    if receipt.get("status") != "ok" or receipt.get("claim_tier") != "fixture_validated":
        failures.append({"path": RELEASE_ROOT_COMPILER_RECEIPT_PATH, "reason": "receipt must be ok with fixture_validated claim tier"})
    required_receipt_refs = {BRANCH_GRAPH_PATH, ROOT_CONTRACT_PATH, STD_PYTHON_REPORT_PATH}
    receipt_refs = set(receipt.get("evidence_refs", []))
    missing_receipt_refs = sorted(required_receipt_refs - receipt_refs)
    if missing_receipt_refs:
        failures.append({"path": RELEASE_ROOT_COMPILER_RECEIPT_PATH, "missing_evidence_refs": missing_receipt_refs})
    for ref in receipt_refs:
        if isinstance(ref, str) and ref and not _path_ref_exists(root, ref):
            failures.append({"path": RELEASE_ROOT_COMPILER_RECEIPT_PATH, "missing_evidence_ref": ref})
    if receipt.get("summary", {}).get("validation_failure_count") != 0:
        failures.append({"path": RELEASE_ROOT_COMPILER_RECEIPT_PATH, "reason": "receipt validation failure count must stay zero"})

    return failures


def validate(root: Path, *, write_receipt: bool = False, at: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    errors: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    def check(check_id: str, ok: bool, detail: str, **extra: Any) -> None:
        checks.append({"id": check_id, "status": "pass" if ok else "fail", "detail": detail, **extra})
        if not ok:
            errors.append({"check": check_id, "detail": detail, **extra})

    retired_candidate_ids = _retired_candidate_ids(root)

    def check_specimen(
        check_id: str,
        candidate_id: str,
        failure_fn: Any,
        detail: str,
    ) -> None:
        if candidate_id in retired_candidate_ids:
            check(
                check_id,
                True,
                "retired from active microcosm ontology by teleology gate",
                retired_by=TELEOLOGY_GATE_PATH.as_posix(),
                candidate_id=candidate_id,
            )
            return
        failures = failure_fn(root)
        check(check_id, not failures, detail, failures=failures[:20])

    idea_graph = load_json(root / "state" / "idea_graph.json")
    ideas = idea_graph.get("ideas", [])
    idea_ids = {idea.get("id") for idea in ideas if isinstance(idea, dict)}
    edges = idea_graph.get("edges", [])
    idea_types = {row["id"] for row in load_json(root / "registry" / "idea_types.json")["rows"]}
    file_type_rows = load_json(root / "registry" / "file_types.json")["rows"]
    file_types = {row["file_type"] for row in file_type_rows}
    validators = {row["id"] for row in load_json(root / "registry" / "validators.json")["rows"]}
    axioms = {row["id"] for row in load_json(root / "registry" / "axioms.json")["rows"]}
    principles = {row["id"] for row in load_json(root / "registry" / "principles.json")["rows"]}
    capability_rows = load_json(root / "capabilities" / "capability_map.json")["rows"]
    capability_ids = {row["id"] for row in capability_rows}
    standards = load_json(root / "registry" / "standards.json")["rows"]
    standard_ids = {row["id"] for row in standards}
    internal_patterns = load_json(root / "registry" / "internal_pattern_inventory.json")["rows"]
    internal_pattern_ids = {row["pattern_id"] for row in internal_patterns}
    annex_patterns = load_json(root / "registry" / "annex_patterns.json")["rows"]
    annex_pattern_ids = {row["pattern_id"] for row in annex_patterns}
    module_blueprints = load_json(root / "modules" / "module_blueprints.json")["rows"]
    module_blueprint_ids = {row["id"] for row in module_blueprints}
    work_items = read_jsonl(root / "state" / "work_items.jsonl")
    work_ids = {row.get("id") for row in work_items}
    receipt_refs = _receipt_paths(root)
    strategy_rows = read_jsonl(root / "strategy" / "ledger.jsonl")
    deliverable_ids = {ref for idea in ideas for ref in idea.get("deliverable_refs", [])}

    required_idea_fields = {"id", "type", "claim", "standard_refs", "evidence_refs", "validators", "next_moves", "omissions"}
    malformed = []
    for idea in ideas:
        missing = sorted(field for field in required_idea_fields if idea.get(field) in ("", None, []))
        if missing:
            malformed.append({"idea_id": idea.get("id"), "missing": missing})
        for validator_ref in idea.get("validators", []):
            if validator_ref not in validators:
                malformed.append({"idea_id": idea.get("id"), "unknown_validator": validator_ref})
        for axiom_ref in idea.get("governing_axioms", []):
            if axiom_ref not in axioms:
                malformed.append({"idea_id": idea.get("id"), "unknown_axiom": axiom_ref})
        for principle_ref in idea.get("governing_principles", []):
            if principle_ref not in principles:
                malformed.append({"idea_id": idea.get("id"), "unknown_principle": principle_ref})
        for ref in idea.get("standard_refs", []) + idea.get("projections", []):
            if not _path_ref_exists(root, ref):
                malformed.append({"idea_id": idea.get("id"), "missing_ref": ref})
    check("validator.idea_schema", not malformed, "all idea rows have required fields and resolvable local refs", failures=malformed[:20])

    graph_failures = []
    for edge in edges:
        if edge.get("from") not in idea_ids or edge.get("to") not in idea_ids:
            graph_failures.append(edge)
    check("validator.idea_graph", not graph_failures, "idea graph edges resolve", failures=graph_failures[:20])

    artifact_failures = []
    for row in file_type_rows:
        if row.get("idea_type") not in idea_types:
            artifact_failures.append({"file_type": row.get("file_type"), "unknown_idea_type": row.get("idea_type")})
        for validator_ref in row.get("validator_refs", []):
            if validator_ref not in validators:
                artifact_failures.append({"file_type": row.get("file_type"), "unknown_validator": validator_ref})
        if not row.get("projection_rule"):
            artifact_failures.append({"file_type": row.get("file_type"), "missing": "projection_rule"})
    manifest_path = root / "state" / "artifact_manifest.json"
    manifest: dict[str, Any] = {}
    manifest_rows: list[dict[str, Any]] = []
    if not manifest_path.exists():
        artifact_failures.append({"path": "state/artifact_manifest.json", "reason": "missing manifest"})
    else:
        manifest = load_json(manifest_path)
        if manifest.get("authority_posture") != "projection_not_authority":
            artifact_failures.append({"path": "state/artifact_manifest.json", "reason": "manifest must declare projection_not_authority"})
        manifest_rows = manifest.get("rows", [])
        required_manifest_fields = {"path", "file_type", "idea_refs", "standard_refs", "validator_refs", "authority_role", "read_hint", "projection_rule", "rights_posture"}
        manifest_paths = {row.get("path") for row in manifest_rows if isinstance(row, dict)}
        expected_paths = {str(path.relative_to(root)) for path in _text_files(root)}
        missing_paths = sorted(expected_paths - manifest_paths)
        for missing_path in missing_paths[:20]:
            artifact_failures.append({"path": missing_path, "reason": "missing manifest row"})
        for row in manifest_rows:
            if not isinstance(row, dict):
                artifact_failures.append({"reason": "manifest row must be an object"})
                continue
            missing = sorted(field for field in required_manifest_fields if row.get(field) in ("", None, []))
            if missing:
                artifact_failures.append({"path": row.get("path"), "missing": missing})
            rel_path = row.get("path")
            if rel_path and not (root / rel_path).exists():
                artifact_failures.append({"path": rel_path, "reason": "manifest path does not exist"})
            if row.get("file_type") not in file_types:
                artifact_failures.append({"path": rel_path, "unknown_file_type": row.get("file_type")})
            for idea_ref in row.get("idea_refs", []):
                if idea_ref not in idea_ids:
                    artifact_failures.append({"path": rel_path, "unknown_idea": idea_ref})
            for standard_ref in row.get("standard_refs", []):
                if standard_ref not in standard_ids:
                    artifact_failures.append({"path": rel_path, "unknown_standard": standard_ref})
            for validator_ref in row.get("validator_refs", []):
                if validator_ref not in validators:
                    artifact_failures.append({"path": rel_path, "unknown_validator": validator_ref})
    check("validator.artifact_manifest", not artifact_failures, "artifact manifest covers public files and resolves file types, ideas, standards, validators, and authority roles", failures=artifact_failures[:20])

    rights_failures = []
    required_publication_rights = {
        "schema_version",
        "license_grant_status",
        "fixture_rights_status",
        "generated_artifact_rights_status",
        "release_effect",
        "public_use_grant",
    }
    required_artifact_rights = {
        "schema_version",
        "content_origin",
        "derivation",
        "license_grant_status",
        "release_effect",
        "real_private_data",
        "private_raw_voice",
        "third_party_source_included",
        "public_use_grant",
        "path_scope",
    }

    def _rights_missing(payload: Any, required: set[str]) -> list[str]:
        if not isinstance(payload, dict):
            return sorted(required)
        return sorted(field for field in required if payload.get(field) in ("", None, []))

    manifest_rights = manifest.get("rights_posture") if manifest else None
    missing_manifest_rights = _rights_missing(manifest_rights, required_publication_rights)
    if missing_manifest_rights:
        rights_failures.append({"path": "state/artifact_manifest.json", "missing": missing_manifest_rights})
    elif manifest_rights.get("license_grant_status") not in ALLOWED_LICENSE_GRANT_STATUSES:
        rights_failures.append({"path": "state/artifact_manifest.json", "reason": "unexpected license grant status"})

    for row in manifest_rows:
        if not isinstance(row, dict):
            continue
        rights = row.get("rights_posture")
        missing = _rights_missing(rights, required_artifact_rights)
        rel_path = row.get("path")
        if missing:
            rights_failures.append({"path": rel_path, "missing": missing})
            continue
        if rights.get("path_scope") != rel_path:
            rights_failures.append({"path": rel_path, "reason": "rights path_scope must match manifest path"})
        if rights.get("license_grant_status") not in ALLOWED_LICENSE_GRANT_STATUSES:
            rights_failures.append({"path": rel_path, "reason": "unexpected license grant status"})
        if rights.get("real_private_data") is not False or rights.get("private_raw_voice") is not False:
            rights_failures.append({"path": rel_path, "reason": "rights posture must declare no real private data or private raw voice"})
        if row.get("file_type") == "fixture" and rights.get("content_origin") != "synthetic_fixture":
            rights_failures.append({"path": rel_path, "reason": "fixture rows must declare synthetic_fixture origin"})

    gate_path = root / "release" / "publication_gate.json"
    if not gate_path.exists():
        rights_failures.append({"path": "release/publication_gate.json", "reason": "missing publication gate"})
    else:
        gate = load_json(gate_path)
        gate_rights = gate.get("rights_posture")
        missing_gate_rights = _rights_missing(gate_rights, required_publication_rights)
        if missing_gate_rights:
            rights_failures.append({"path": "release/publication_gate.json", "missing": missing_gate_rights})
        elif gate_rights.get("license_grant_status") not in ALLOWED_LICENSE_GRANT_STATUSES:
            rights_failures.append({"path": "release/publication_gate.json", "reason": "unexpected license grant status"})
        if gate.get("status") != "fail_closed":
            rights_failures.append({"path": "release/publication_gate.json", "reason": "rights posture validator expects fail-closed status until a license/no-license posture is selected"})
        required_claim_ids = {"fixture_rights_posture_selected", "generated_artifact_rights_posture_selected"}
        observed_claim_ids = {row.get("id") for row in gate.get("required_green_checks", []) if isinstance(row, dict)}
        missing_claim_ids = sorted(required_claim_ids - observed_claim_ids)
        if missing_claim_ids:
            rights_failures.append({"path": "release/publication_gate.json", "missing_required_green_checks": missing_claim_ids})
    check("validator.rights_posture", not rights_failures, "publication gate and manifest declare fixture and generated-artifact rights posture without granting a public license", failures=rights_failures[:20])

    standard_failures = []
    for row in standards:
        if not _path_ref_exists(root, row.get("path", "")):
            standard_failures.append({"standard_id": row.get("id"), "missing_path": row.get("path")})
    check("validator.standards", not standard_failures, "standard registry paths resolve", failures=standard_failures[:20])

    capability_failures = []
    required_capability_fields = {"id", "claim", "axiom_refs", "idea_refs", "artifact_refs", "validator_refs", "proof_refs"}
    for capability in capability_rows:
        missing = sorted(field for field in required_capability_fields if capability.get(field) in ("", None, []))
        if missing:
            capability_failures.append({"capability_id": capability.get("id"), "missing": missing})
        for axiom_ref in capability.get("axiom_refs", []):
            if axiom_ref not in axioms:
                capability_failures.append({"capability_id": capability.get("id"), "unknown_axiom": axiom_ref})
        for principle_ref in capability.get("principle_refs", []):
            if principle_ref not in principles:
                capability_failures.append({"capability_id": capability.get("id"), "unknown_principle": principle_ref})
        for idea_ref in capability.get("idea_refs", []):
            if idea_ref not in idea_ids:
                capability_failures.append({"capability_id": capability.get("id"), "unknown_idea": idea_ref})
        for validator_ref in capability.get("validator_refs", []):
            if validator_ref not in validators:
                capability_failures.append({"capability_id": capability.get("id"), "unknown_validator": validator_ref})
        for ref in capability.get("artifact_refs", []) + capability.get("proof_refs", []):
            if not _path_ref_exists(root, ref):
                capability_failures.append({"capability_id": capability.get("id"), "missing_ref": ref})
    matrix = load_json(root / "capabilities" / "axiom_capability_matrix.json")
    for row in matrix.get("rows", []):
        if row.get("axiom_id") not in axioms:
            capability_failures.append({"matrix_row": row.get("axiom_id"), "unknown_axiom": row.get("axiom_id")})
        for capability_ref in row.get("capability_refs", []):
            if capability_ref not in capability_ids:
                capability_failures.append({"matrix_row": row.get("axiom_id"), "unknown_capability": capability_ref})
    check("validator.capability_map", not capability_failures, "capabilities resolve axioms, ideas, artifacts, validators, and proof refs", failures=capability_failures[:20])

    principle_matrix_failures = []
    matrix_path = root / "state" / "principle_enforcement_matrix.json"
    if not matrix_path.exists():
        principle_matrix_failures.append({"path": "state/principle_enforcement_matrix.json", "reason": "missing principle enforcement matrix"})
    else:
        principle_matrix = load_json(matrix_path)
        matrix_rows = principle_matrix.get("rows", [])
        rows_by_key = {(row.get("target_kind"), row.get("target_id")): row for row in matrix_rows if isinstance(row, dict)}
        for principle_id in sorted(principles):
            if ("principle", principle_id) not in rows_by_key:
                principle_matrix_failures.append({"target_kind": "principle", "target_id": principle_id, "reason": "missing matrix row"})
        for axiom_id in sorted(axioms):
            if ("axiom", axiom_id) not in rows_by_key:
                principle_matrix_failures.append({"target_kind": "axiom", "target_id": axiom_id, "reason": "missing matrix row"})
        required_matrix_fields = {"target_kind", "target_id", "coverage_status", "idea_refs", "capability_refs", "artifact_refs", "validator_refs", "proof_refs"}
        for row in matrix_rows:
            if not isinstance(row, dict):
                principle_matrix_failures.append({"reason": "matrix row must be an object"})
                continue
            missing = sorted(field for field in required_matrix_fields if row.get(field) in ("", None, []))
            if missing:
                principle_matrix_failures.append({"target_id": row.get("target_id"), "missing": missing})
            if row.get("coverage_status") != "enforced":
                principle_matrix_failures.append({"target_id": row.get("target_id"), "coverage_status": row.get("coverage_status")})
            for idea_ref in row.get("idea_refs", []):
                if idea_ref not in idea_ids:
                    principle_matrix_failures.append({"target_id": row.get("target_id"), "unknown_idea": idea_ref})
            for capability_ref in row.get("capability_refs", []):
                if capability_ref not in capability_ids:
                    principle_matrix_failures.append({"target_id": row.get("target_id"), "unknown_capability": capability_ref})
            for validator_ref in row.get("validator_refs", []):
                if validator_ref not in validators:
                    principle_matrix_failures.append({"target_id": row.get("target_id"), "unknown_validator": validator_ref})
            for ref in row.get("artifact_refs", []):
                if not _path_ref_exists(root, ref):
                    principle_matrix_failures.append({"target_id": row.get("target_id"), "missing_artifact_ref": ref})
            for proof_ref in row.get("proof_refs", []):
                if proof_ref not in receipt_refs:
                    principle_matrix_failures.append({"target_id": row.get("target_id"), "missing_proof_ref": proof_ref})
        summary = principle_matrix.get("summary", {})
        if summary.get("uncovered_count") not in (0, None):
            principle_matrix_failures.append({"summary_uncovered_count": summary.get("uncovered_count")})
    check("validator.principle_enforcement", not principle_matrix_failures, "principles and axioms compile into executable idea, capability, artifact, validator, and receipt gates", failures=principle_matrix_failures[:20])

    teleology_failures = []
    teleology_path = root / "state" / "teleology_map.json"
    if not teleology_path.exists():
        teleology_failures.append({"path": "state/teleology_map.json", "reason": "missing teleology map"})
    else:
        teleology = load_json(teleology_path)
        teleology_rows = teleology.get("rows", [])
        rows_by_key = {(row.get("target_kind"), row.get("target_id")): row for row in teleology_rows if isinstance(row, dict)}
        for principle_id in sorted(principles):
            if ("principle", principle_id) not in rows_by_key:
                teleology_failures.append({"target_kind": "principle", "target_id": principle_id, "reason": "missing teleology row"})
        for axiom_id in sorted(axioms):
            if ("axiom", axiom_id) not in rows_by_key:
                teleology_failures.append({"target_kind": "axiom", "target_id": axiom_id, "reason": "missing teleology row"})
        required_teleology_fields = {
            "target_kind",
            "target_id",
            "purpose_statement",
            "pressure_class",
            "idea_refs",
            "capability_refs",
            "deliverable_refs",
            "module_blueprint_refs",
            "proof_refs",
            "next_move_refs",
            "coverage_status",
        }
        for row in teleology_rows:
            if not isinstance(row, dict):
                teleology_failures.append({"reason": "teleology row must be an object"})
                continue
            missing = sorted(field for field in required_teleology_fields if row.get(field) in ("", None, []))
            if missing:
                teleology_failures.append({"target_id": row.get("target_id"), "missing": missing})
            if row.get("coverage_status") != "operationalized":
                teleology_failures.append({"target_id": row.get("target_id"), "coverage_status": row.get("coverage_status")})
            for idea_ref in row.get("idea_refs", []):
                if idea_ref not in idea_ids:
                    teleology_failures.append({"target_id": row.get("target_id"), "unknown_idea": idea_ref})
            for capability_ref in row.get("capability_refs", []):
                if capability_ref not in capability_ids:
                    teleology_failures.append({"target_id": row.get("target_id"), "unknown_capability": capability_ref})
            for deliverable_ref in row.get("deliverable_refs", []):
                if deliverable_ref not in deliverable_ids:
                    teleology_failures.append({"target_id": row.get("target_id"), "unknown_deliverable": deliverable_ref})
            for module_ref in row.get("module_blueprint_refs", []):
                if module_ref not in module_blueprint_ids:
                    teleology_failures.append({"target_id": row.get("target_id"), "unknown_module_blueprint": module_ref})
            for proof_ref in row.get("proof_refs", []):
                if proof_ref not in receipt_refs:
                    teleology_failures.append({"target_id": row.get("target_id"), "missing_proof_ref": proof_ref})
            for next_move_ref in row.get("next_move_refs", []):
                if next_move_ref not in work_ids:
                    teleology_failures.append({"target_id": row.get("target_id"), "unknown_next_move": next_move_ref})
        summary = teleology.get("summary", {})
        if summary.get("gap_count") not in (0, None):
            teleology_failures.append({"summary_gap_count": summary.get("gap_count")})
    check("validator.teleology_map", not teleology_failures, "principles and axioms resolve to purpose pressure, deliverables, modules, receipts, and next moves", failures=teleology_failures[:20])

    microcosm_posture_failures = []
    teleology_gate_path = root / "strategy" / "microcosm_teleology_gate.json"
    reconstruction_posture_path = root / "strategy" / "microcosm_reconstruction_posture.json"
    sandbox_gate_path = root / "sandbox" / "microcosm_sandbox_gate.json"
    if not teleology_gate_path.exists():
        microcosm_posture_failures.append({"path": "strategy/microcosm_teleology_gate.json", "reason": "missing microcosm teleology gate"})
        teleology_gate = {}
    else:
        teleology_gate = load_json(teleology_gate_path)
    if not reconstruction_posture_path.exists():
        microcosm_posture_failures.append({"path": "strategy/microcosm_reconstruction_posture.json", "reason": "missing microcosm reconstruction posture"})
        reconstruction_posture = {}
    else:
        reconstruction_posture = load_json(reconstruction_posture_path)
    if not sandbox_gate_path.exists():
        microcosm_posture_failures.append({"path": "sandbox/microcosm_sandbox_gate.json", "reason": "missing microcosm sandbox gate"})
        sandbox_gate = {}
    else:
        sandbox_gate = load_json(sandbox_gate_path)

    if teleology_gate.get("reconstruction_posture_ref") != "strategy/microcosm_reconstruction_posture.json":
        microcosm_posture_failures.append({"path": "strategy/microcosm_teleology_gate.json", "reason": "teleology gate must reference reconstruction posture"})
    vision_posture = teleology_gate.get("vision_posture", {})
    if vision_posture.get("final_ontology_status") != "provisional_until_pattern_population_read":
        microcosm_posture_failures.append({"path": "strategy/microcosm_teleology_gate.json", "reason": "final ontology must stay provisional until pattern population is read"})
    if vision_posture.get("quality_target") != "10_out_of_10_coherence_bar":
        microcosm_posture_failures.append({"path": "strategy/microcosm_teleology_gate.json", "reason": "teleology gate must name the 10/10 coherence bar"})
    if vision_posture.get("current_leaf_set_status") != "cleaned_scaffold_not_final_architecture":
        microcosm_posture_failures.append({"path": "strategy/microcosm_teleology_gate.json", "reason": "current leaf set must not be treated as final architecture"})

    if reconstruction_posture.get("status") != "active_provisional":
        microcosm_posture_failures.append({"path": "strategy/microcosm_reconstruction_posture.json", "reason": "reconstruction posture must be active_provisional"})
    quality_bar = reconstruction_posture.get("quality_bar", {})
    if quality_bar.get("target") != "10_out_of_10_coherence_bar":
        microcosm_posture_failures.append({"path": "strategy/microcosm_reconstruction_posture.json", "reason": "reconstruction posture must define the coherence bar"})
    pattern_dependency = reconstruction_posture.get("pattern_population_dependency", {})
    if pattern_dependency.get("status") != "awaiting_populated_pattern_surfaces":
        microcosm_posture_failures.append({"path": "strategy/microcosm_reconstruction_posture.json", "reason": "reconstruction posture must wait for populated pattern surfaces"})
    if "final leaf count" not in reconstruction_posture.get("not_decided_yet", []):
        microcosm_posture_failures.append({"path": "strategy/microcosm_reconstruction_posture.json", "reason": "final leaf count must remain undecided"})
    if reconstruction_posture.get("provisional_current_surface", {}).get("status") != "active_scaffold_not_final_architecture":
        microcosm_posture_failures.append({"path": "strategy/microcosm_reconstruction_posture.json", "reason": "current active surface must be marked scaffold, not final"})

    sandbox_maturity = sandbox_gate.get("maturity", {})
    if sandbox_gate.get("reconstruction_posture_ref") != "strategy/microcosm_reconstruction_posture.json":
        microcosm_posture_failures.append({"path": "sandbox/microcosm_sandbox_gate.json", "reason": "sandbox gate must reference reconstruction posture"})
    if sandbox_maturity.get("current_mode") != "root_backed_active_scaffold":
        microcosm_posture_failures.append({"path": "sandbox/microcosm_sandbox_gate.json", "reason": "sandbox current mode must be root-backed scaffold"})
    if sandbox_maturity.get("target_mode") != "self_contained_runtime_root_with_leaf_export_candidates":
        microcosm_posture_failures.append({"path": "sandbox/microcosm_sandbox_gate.json", "reason": "sandbox target mode must name self-contained runtime root"})
    check("validator.microcosm_posture", not microcosm_posture_failures, "microcosm posture keeps final ontology provisional, pattern-population gated, and aimed at an ideal self-contained substrate", failures=microcosm_posture_failures[:20])

    module_failures = []
    required_module_fields = {
        "id",
        "source_kind",
        "source_pattern_ref",
        "port_mode",
        "public_contract",
        "target_artifact_refs",
        "standard_refs",
        "validator_refs",
        "capability_refs",
        "proof_refs",
        "do_not_copy_boundary",
    }
    for blueprint in module_blueprints:
        missing = sorted(field for field in required_module_fields if blueprint.get(field) in ("", None, []))
        if missing:
            module_failures.append({"blueprint_id": blueprint.get("id"), "missing": missing})
        source_kind = blueprint.get("source_kind")
        source_pattern = blueprint.get("source_pattern_ref")
        if source_kind == "internal_code_pattern" and source_pattern not in internal_pattern_ids:
            module_failures.append({"blueprint_id": blueprint.get("id"), "unknown_internal_pattern": source_pattern})
        if source_kind == "annex_pattern" and source_pattern not in annex_pattern_ids:
            module_failures.append({"blueprint_id": blueprint.get("id"), "unknown_annex_pattern": source_pattern})
        for ref in blueprint.get("target_artifact_refs", []) + blueprint.get("proof_refs", []):
            if not _path_ref_exists(root, ref):
                module_failures.append({"blueprint_id": blueprint.get("id"), "missing_ref": ref})
        for standard_ref in blueprint.get("standard_refs", []):
            if standard_ref not in standard_ids:
                module_failures.append({"blueprint_id": blueprint.get("id"), "unknown_standard": standard_ref})
        for validator_ref in blueprint.get("validator_refs", []):
            if validator_ref not in validators:
                module_failures.append({"blueprint_id": blueprint.get("id"), "unknown_validator": validator_ref})
        for capability_ref in blueprint.get("capability_refs", []):
            if capability_ref not in capability_ids:
                module_failures.append({"blueprint_id": blueprint.get("id"), "unknown_capability": capability_ref})
    check("validator.module_blueprints", not module_failures, "module blueprints resolve source patterns, target artifacts, standards, validators, capabilities, and proof refs", failures=module_failures[:20])

    port_packet_failures = []
    port_packet_path = root / "ports" / "port_packets.json"
    if not port_packet_path.exists():
        port_packet_failures.append({"path": "ports/port_packets.json", "reason": "missing port packet registry"})
    else:
        port_packets = load_json(port_packet_path)
        packet_rows = port_packets.get("rows", [])
        packet_by_blueprint = {
            row.get("module_blueprint_ref"): row
            for row in packet_rows
            if isinstance(row, dict) and row.get("module_blueprint_ref")
        }
        for blueprint_id in sorted(module_blueprint_ids):
            if blueprint_id not in packet_by_blueprint:
                port_packet_failures.append({"module_blueprint_ref": blueprint_id, "reason": "missing port packet"})
        required_packet_fields = {
            "id",
            "module_blueprint_ref",
            "source_pattern_ref",
            "port_mode",
            "implementation_goal",
            "target_artifact_refs",
            "read_first_refs",
            "standard_refs",
            "validator_refs",
            "capability_refs",
            "proof_refs",
            "acceptance_checks",
            "implementation_steps",
            "do_not_copy_boundary",
            "next_work_item_ref",
            "status",
        }
        for packet in packet_rows:
            if not isinstance(packet, dict):
                port_packet_failures.append({"reason": "port packet row must be an object"})
                continue
            missing = sorted(field for field in required_packet_fields if packet.get(field) in ("", None, []))
            if missing:
                port_packet_failures.append({"packet_id": packet.get("id"), "missing": missing})
            if packet.get("module_blueprint_ref") not in module_blueprint_ids:
                port_packet_failures.append({"packet_id": packet.get("id"), "unknown_module_blueprint": packet.get("module_blueprint_ref")})
            if packet.get("next_work_item_ref") not in work_ids:
                port_packet_failures.append({"packet_id": packet.get("id"), "unknown_next_work_item": packet.get("next_work_item_ref")})
            if packet.get("status") != "ready_for_clean_room_implementation":
                port_packet_failures.append({"packet_id": packet.get("id"), "status": packet.get("status")})
            for ref in packet.get("target_artifact_refs", []) + packet.get("read_first_refs", []):
                if not _path_ref_exists(root, ref):
                    port_packet_failures.append({"packet_id": packet.get("id"), "missing_ref": ref})
            for standard_ref in packet.get("standard_refs", []):
                if standard_ref not in standard_ids:
                    port_packet_failures.append({"packet_id": packet.get("id"), "unknown_standard": standard_ref})
            for validator_ref in packet.get("validator_refs", []):
                if validator_ref not in validators:
                    port_packet_failures.append({"packet_id": packet.get("id"), "unknown_validator": validator_ref})
            for capability_ref in packet.get("capability_refs", []):
                if capability_ref not in capability_ids:
                    port_packet_failures.append({"packet_id": packet.get("id"), "unknown_capability": capability_ref})
            for proof_ref in packet.get("proof_refs", []):
                if proof_ref not in receipt_refs:
                    port_packet_failures.append({"packet_id": packet.get("id"), "missing_proof_ref": proof_ref})
            for check_row in packet.get("acceptance_checks", []):
                if not isinstance(check_row, dict) or not check_row.get("id") or not check_row.get("command") or not check_row.get("expected"):
                    port_packet_failures.append({"packet_id": packet.get("id"), "bad_acceptance_check": check_row})
        summary = port_packets.get("summary", {})
        if summary.get("packet_count") != len(module_blueprint_ids):
            port_packet_failures.append({"summary_packet_count": summary.get("packet_count"), "expected": len(module_blueprint_ids)})
        if summary.get("ready_count") != len(module_blueprint_ids):
            port_packet_failures.append({"summary_ready_count": summary.get("ready_count"), "expected": len(module_blueprint_ids)})
    check("validator.port_packets", not port_packet_failures, "port packets cover every module blueprint with implementation checks and private-safe boundaries", failures=port_packet_failures[:20])

    axiom_kernel_failures = []
    axiom_kernel_path = root / "state" / "axiom_kernel.json"
    if not axiom_kernel_path.exists():
        axiom_kernel_failures.append({"path": "state/axiom_kernel.json", "reason": "missing axiom kernel"})
    else:
        axiom_kernel = load_json(axiom_kernel_path)
        kernel_rows = axiom_kernel.get("rows", [])
        kernel_by_key = {(row.get("target_kind"), row.get("target_id")): row for row in kernel_rows if isinstance(row, dict)}
        port_packet_rows = load_json(root / "ports" / "port_packets.json").get("rows", [])
        port_packet_ids = {row.get("id") for row in port_packet_rows if isinstance(row, dict)}
        for principle_id in sorted(principles):
            if ("principle", principle_id) not in kernel_by_key:
                axiom_kernel_failures.append({"target_kind": "principle", "target_id": principle_id, "reason": "missing kernel row"})
        for axiom_id in sorted(axioms):
            if ("axiom", axiom_id) not in kernel_by_key:
                axiom_kernel_failures.append({"target_kind": "axiom", "target_id": axiom_id, "reason": "missing kernel row"})
        required_kernel_fields = {
            "target_kind",
            "target_id",
            "agent_rule",
            "pressure_class",
            "pressure_score",
            "deliverable_refs",
            "capability_refs",
            "artifact_refs",
            "validator_refs",
            "module_blueprint_refs",
            "port_packet_refs",
            "proof_refs",
            "next_move_refs",
            "coverage_status",
        }
        for row in kernel_rows:
            if not isinstance(row, dict):
                axiom_kernel_failures.append({"reason": "kernel row must be an object"})
                continue
            missing = sorted(field for field in required_kernel_fields if row.get(field) in ("", None, []))
            if missing:
                axiom_kernel_failures.append({"target_id": row.get("target_id"), "missing": missing})
            if row.get("coverage_status") != "compiled":
                axiom_kernel_failures.append({"target_id": row.get("target_id"), "coverage_status": row.get("coverage_status")})
            if not isinstance(row.get("pressure_score"), int) or row.get("pressure_score", 0) <= 0:
                axiom_kernel_failures.append({"target_id": row.get("target_id"), "bad_pressure_score": row.get("pressure_score")})
            if row.get("target_kind") == "principle" and row.get("target_id") not in principles:
                axiom_kernel_failures.append({"target_id": row.get("target_id"), "unknown_principle": row.get("target_id")})
            if row.get("target_kind") == "axiom" and row.get("target_id") not in axioms:
                axiom_kernel_failures.append({"target_id": row.get("target_id"), "unknown_axiom": row.get("target_id")})
            for capability_ref in row.get("capability_refs", []):
                if capability_ref not in capability_ids:
                    axiom_kernel_failures.append({"target_id": row.get("target_id"), "unknown_capability": capability_ref})
            for validator_ref in row.get("validator_refs", []):
                if validator_ref not in validators:
                    axiom_kernel_failures.append({"target_id": row.get("target_id"), "unknown_validator": validator_ref})
            for module_ref in row.get("module_blueprint_refs", []):
                if module_ref not in module_blueprint_ids:
                    axiom_kernel_failures.append({"target_id": row.get("target_id"), "unknown_module_blueprint": module_ref})
            for packet_ref in row.get("port_packet_refs", []):
                if packet_ref not in port_packet_ids:
                    axiom_kernel_failures.append({"target_id": row.get("target_id"), "unknown_port_packet": packet_ref})
            for proof_ref in row.get("proof_refs", []):
                if proof_ref not in receipt_refs:
                    axiom_kernel_failures.append({"target_id": row.get("target_id"), "missing_proof_ref": proof_ref})
            for next_move_ref in row.get("next_move_refs", []):
                if next_move_ref not in work_ids:
                    axiom_kernel_failures.append({"target_id": row.get("target_id"), "unknown_next_move": next_move_ref})
            for ref in row.get("artifact_refs", []):
                if not _path_ref_exists(root, ref):
                    axiom_kernel_failures.append({"target_id": row.get("target_id"), "missing_artifact_ref": ref})
        summary = axiom_kernel.get("summary", {})
        expected_count = len(principles) + len(axioms)
        if summary.get("row_count") != expected_count:
            axiom_kernel_failures.append({"summary_row_count": summary.get("row_count"), "expected": expected_count})
        if summary.get("gap_count") not in (0, None):
            axiom_kernel_failures.append({"summary_gap_count": summary.get("gap_count")})
    check("validator.axiom_kernel", not axiom_kernel_failures, "principles and axioms compile into cold-agent rules with validators, modules, port packets, receipts, and next moves", failures=axiom_kernel_failures[:20])

    release_candidate_failures = []
    candidate_source_path = root / "registry" / "release_candidates.json"
    portfolio_path = root / "state" / "release_candidate_portfolio.json"
    if not candidate_source_path.exists():
        release_candidate_failures.append({"path": "registry/release_candidates.json", "reason": "missing release candidate source registry"})
    if not portfolio_path.exists():
        release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "missing ranked release candidate portfolio"})
    if not release_candidate_failures:
        candidate_source = load_json(candidate_source_path)
        portfolio = load_json(portfolio_path)
        source_rows_raw = candidate_source.get("rows", [])
        source_rows = [
            row
            for row in source_rows_raw
            if isinstance(row, dict) and str(row.get("candidate_id", "")) not in retired_candidate_ids
        ]
        portfolio_rows = portfolio.get("candidates", [])
        if candidate_source.get("authority_posture") != "public_safe_candidate_source_registry_not_publication_claim":
            release_candidate_failures.append({"path": "registry/release_candidates.json", "reason": "source registry must not claim publication authority"})
        if portfolio.get("authority_posture") != "ranked_projection_not_publication_claim":
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio must declare ranked_projection_not_publication_claim"})
        if portfolio.get("status") != "ok":
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "status": portfolio.get("status")})
        if not isinstance(source_rows_raw, list) or len(source_rows) < 5:
            release_candidate_failures.append({"path": "registry/release_candidates.json", "reason": "expected at least five candidate records"})
        if not isinstance(portfolio_rows, list) or len(portfolio_rows) != len(source_rows):
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio candidates must mirror source rows"})
        source_ids = {row.get("candidate_id") for row in source_rows if isinstance(row, dict)}
        portfolio_ids = {row.get("candidate_id") for row in portfolio_rows if isinstance(row, dict)}
        if source_ids != portfolio_ids:
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio ids must match source ids"})
        retired_portfolio_ids = sorted(portfolio_ids & retired_candidate_ids)
        if retired_portfolio_ids:
            release_candidate_failures.append(
                {
                    "path": "state/release_candidate_portfolio.json",
                    "reason": "portfolio must exclude teleology-retired dissemination candidates",
                    "candidate_ids": retired_portfolio_ids,
                }
            )
        scores = [row.get("score") for row in portfolio_rows if isinstance(row, dict)]
        if scores != sorted(scores, reverse=True):
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio must be sorted by descending score"})
        implemented_specimen_candidate_ids = portfolio.get("implemented_specimen_candidate_ids")
        if not isinstance(implemented_specimen_candidate_ids, list) or not all(isinstance(item, str) for item in implemented_specimen_candidate_ids):
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "implemented specimen ids must be a string list"})
            implemented_specimen_id_set: set[str] = set()
        else:
            implemented_specimen_id_set = set(implemented_specimen_candidate_ids)
        for row in source_rows:
            if not isinstance(row, dict):
                release_candidate_failures.append({"path": "registry/release_candidates.json", "reason": "candidate row must be an object"})
                continue
            release_candidate_failures.extend(candidate_shape_failures(row))
            for standard_ref in row.get("standard_refs", []):
                if standard_ref not in standard_ids:
                    release_candidate_failures.append({"candidate_id": row.get("candidate_id"), "unknown_standard": standard_ref})
            for receipt_ref in row.get("receipt_refs", []):
                if receipt_ref and receipt_ref not in receipt_refs:
                    release_candidate_failures.append({"candidate_id": row.get("candidate_id"), "missing_receipt_ref": receipt_ref})
        for row in portfolio_rows:
            if not isinstance(row, dict):
                continue
            candidate_id = row.get("candidate_id")
            if not isinstance(row.get("score"), int):
                release_candidate_failures.append({"candidate_id": candidate_id, "reason": "score must be an integer"})
            score_components = row.get("score_components")
            if not isinstance(score_components, dict) or "evidence_density" not in score_components:
                release_candidate_failures.append({"candidate_id": candidate_id, "reason": "score components missing evidence density"})
            if not row.get("selector_reason"):
                release_candidate_failures.append({"candidate_id": candidate_id, "reason": "selector reason missing"})
            if row.get("specimen_status") not in ALLOWED_SPECIMEN_STATUSES:
                release_candidate_failures.append({"candidate_id": candidate_id, "reason": "unknown specimen status", "specimen_status": row.get("specimen_status")})
            if candidate_id in implemented_specimen_id_set and row.get("specimen_status") != "landed":
                release_candidate_failures.append({"candidate_id": candidate_id, "reason": "implemented specimen must have landed status"})
        top_candidate_id = portfolio.get("top_candidate_id")
        if portfolio_rows and top_candidate_id != portfolio_rows[0].get("candidate_id"):
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "top_candidate_id must match first row"})
        next_specimen_candidate_id = portfolio.get("next_specimen_candidate_id")
        all_candidate_specimens_landed = portfolio.get("all_candidate_specimens_landed") is True
        terminal_portfolio = all_candidate_specimens_landed and implemented_specimen_id_set == portfolio_ids
        if next_specimen_candidate_id:
            if next_specimen_candidate_id not in portfolio_ids:
                release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "next specimen candidate must resolve"})
            elif next_specimen_candidate_id in implemented_specimen_id_set:
                release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "next specimen must not be an already-landed specimen"})
        elif not terminal_portfolio:
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "next specimen candidate must resolve unless all candidate specimens are landed"})
        next_status_rows = [
            row
            for row in portfolio_rows
            if isinstance(row, dict) and row.get("specimen_status") == "next_candidate"
        ]
        if next_specimen_candidate_id:
            if len(next_status_rows) != 1 or next_status_rows[0].get("candidate_id") != next_specimen_candidate_id:
                release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "exactly one next_candidate row must match next_specimen_candidate_id"})
        elif next_status_rows:
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "exactly one next_candidate row must match next_specimen_candidate_id"})
        if "public-release-ready" in json.dumps(portfolio).lower():
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio must not imply public release readiness"})
        microcosm_index = portfolio.get("microcosm_portfolio_index")
        if not isinstance(microcosm_index, dict):
            release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "missing microcosm portfolio index"})
        else:
            route_index = microcosm_index.get("route_to_command_index")
            if not isinstance(route_index, dict):
                release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "missing route-to-command index"})
            else:
                route_summary = route_index.get("summary", {})
                routes = route_index.get("routes", [])
                route_count = route_summary.get("route_count")
                if route_index.get("authority_posture") != "route_index_projection_not_publication_or_release_authority":
                    release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index authority posture must remain projection-only"})
                if not isinstance(routes, list) or not routes:
                    release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index must include route rows"})
                if route_count != len(routes):
                    release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index route count mismatch"})
                if route_summary.get("missing_ref_count") != 0:
                    release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index has missing refs"})
                if route_summary.get("ready_route_count") != route_count:
                    release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "all route index rows must be ready local fixtures"})
                if route_summary.get("source_clip_hash_count") != route_count:
                    release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index rows must carry source clip hashes"})
                for claim_counter in (
                    "public_release_claim_count",
                    "publication_permission_claim_count",
                    "private_root_equivalence_claim_count",
                    "benchmark_win_claim_count",
                ):
                    if route_summary.get(claim_counter) != 0:
                        release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index claim counter must remain zero", "field": claim_counter})
                retired_route_tokens = (
                    "website_card",
                    "demo_card",
                    "public_release_package",
                    "recipient_packet",
                    "hosted_public",
                    "external_clone",
                    "actual_execution",
                    "operator_receipt",
                )
                for row in routes:
                    route_id = str(row.get("route_id", "")) if isinstance(row, dict) else ""
                    if any(token in route_id for token in retired_route_tokens):
                        release_candidate_failures.append(
                            {
                                "path": "state/release_candidate_portfolio.json",
                                "reason": "route index must not route active microcosm selection through retired dissemination leaves",
                                "route_id": route_id,
                            }
                        )
                if "route-to-command index is not public release approval" not in route_index.get("anti_claims", []):
                    release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index anti-claims missing public release boundary"})
                for row in routes:
                    if not isinstance(row, dict):
                        release_candidate_failures.append({"path": "state/release_candidate_portfolio.json", "reason": "route index row must be an object"})
                        continue
                    route_id = row.get("route_id")
                    if row.get("status") != "ready_local_fixture":
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index row must be ready local fixture"})
                    if not row.get("source_clip_hash"):
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index row missing source clip hash"})
                    if row.get("missing_ref_count") != 0 or row.get("missing_refs"):
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index row has missing refs"})
                    if not row.get("evidence_refs") or not row.get("receipt_refs"):
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index row must carry evidence and receipt refs"})
                    if not all(isinstance(command, str) and command.startswith("PYTHONPATH=src python3 -m idea_microcosm.cli build-") for command in row.get("command_sequence", [])):
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index command sequence must use local builders"})
                    claim_boundary = row.get("claim_boundary", {})
                    if claim_boundary.get("projection_not_authority") is not True:
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index row must declare projection_not_authority"})
                    if claim_boundary.get("self_attestation_authority_count") != 0:
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index self-attestation authority must be zero"})
                    if not row.get("blocked_claims"):
                        release_candidate_failures.append({"route_id": route_id, "reason": "route index row must carry blocked claims"})
    check("validator.release_candidates", not release_candidate_failures, "release candidate portfolio carries required fields, improvement deltas, ranking scores, landed-specimen skip logic, and no publication claim", failures=release_candidate_failures[:20])

    source_capsule_failures = _source_capsule_provenance_specimen_failures(root)
    check(
        "validator.source_capsule_provenance_specimen",
        not source_capsule_failures,
        "Source-capsule provenance specimen hashes public-safe clips, carries bounded semantics, declares projection-not-authority, and blocks public overclaims",
        failures=source_capsule_failures[:20],
    )

    source_shuttle_failures = _source_shuttle_specimen_failures(root)
    check(
        "validator.source_shuttle_specimen",
        not source_shuttle_failures,
        "Source-shuttle specimen hashes source clips, emits bounded semantic packets, records loss/no-private-copy boundaries, proves a before/after motif-route effectiveness witness, and blocks authority promotion",
        failures=source_shuttle_failures[:20],
    )

    task_ledger_specimen_failures = _task_ledger_specimen_failures(root)
    check(
        "validator.task_ledger_cap_economy_specimen",
        not task_ledger_specimen_failures,
        "Task Ledger cap-economy specimen routes validation failures and side findings into durable work events",
        failures=task_ledger_specimen_failures[:20],
    )

    release_standards_failures = _release_standards_axiom_gate_failures(root)
    check(
        "validator.release_standards_axiom_gate_specimen",
        not release_standards_failures,
        "Release standards and axiom gate specimen turns candidate and governing-principle requirements into executable public-safe checks",
        failures=release_standards_failures[:20],
    )

    atlas_navigation_failures = _atlas_navigation_bands_failures(root)
    check(
        "validator.atlas_navigation_bands_specimen",
        not atlas_navigation_failures,
        "Atlas navigation bands specimen projects release candidates into compressed, technical, evidence, and sandbox drilldowns",
        failures=atlas_navigation_failures[:20],
    )

    lab_evolve_failures = _lab_evolve_failure_replay_failures(root)
    check(
        "validator.lab_evolve_failure_replay_specimen",
        not lab_evolve_failures,
        "Lab/Evolve failure replay specimen localizes failures, restarts from safe points, replays variants, and records teachings",
        failures=lab_evolve_failures[:20],
    )

    provider_canary_failures = _provider_harness_canary_failures(root)
    check(
        "validator.provider_harness_canary_specimen",
        not provider_canary_failures,
        "Provider harness canary keeps provider route, output, self-attestation, schema, answer, evaluator, receipt, and repair-route statuses separate",
        failures=provider_canary_failures[:20],
    )

    executable_grammar_failures = _executable_grammar_metabolism_failures(root)
    check(
        "validator.executable_grammar_metabolism_specimen",
        not executable_grammar_failures,
        "Executable grammar specimen turns release-candidate field failures and provider canary status channels into rule-specific repair rows, bounded worker actions, local-only transactions, and fail-closed replay repairs",
        failures=executable_grammar_failures[:20],
    )

    concurrency_failures = _concurrency_mission_control_failures(root)
    check(
        "validator.concurrency_mission_control_specimen",
        not concurrency_failures,
        "Concurrency mission-control specimen blocks overlapping owner paths, stale leases, unmet dependencies, unreceipted completion, unsupervised parent scopes, missing parent finalizers, and misanchored claims",
        failures=concurrency_failures[:20],
    )

    native_concurrency_guard_failures = _native_concurrency_guard_failures(root)
    check(
        "validator.native_concurrency_guard",
        not native_concurrency_guard_failures,
        "Native concurrency guard exposes clone-local path claims, command-run leases, command-key singleflight, parent-scope contracts, and git-safe scoped landing without private runtime dependencies",
        failures=native_concurrency_guard_failures[:20],
    )

    concept_graph_failures = _concept_graph_cards_failures(root)
    check(
        "validator.concept_graph_cards_specimen",
        not concept_graph_failures,
        "Concept graph cards specimen links concepts to standards, skills, microcosms, receipts, and a fail-closed website projection gate",
        failures=concept_graph_failures[:20],
    )

    summary_ladders_failures = _summary_ladders_specimen_failures(root)
    check(
        "validator.summary_ladders_specimen",
        not summary_ladders_failures,
        "Summary ladders project every leaf into one-sentence, concise, medium, and deep human and AI-native layers without strengthening claims",
        failures=summary_ladders_failures[:20],
    )

    verisoftbench_failures = _verisoftbench_diagnostic_specimen_failures(root)
    check(
        "validator.verisoftbench_diagnostic_specimen",
        not verisoftbench_failures,
        "Benchmark diagnostic specimen localizes synthetic failure origin, restart point, evaluator authority, anti-claims, and fail-closed publication boundaries",
        failures=verisoftbench_failures[:20],
    )

    meta_diagnostics_failures = _meta_diagnostics_workbench_failures(root)
    check(
        "validator.meta_diagnostics_workbench_specimen",
        not meta_diagnostics_failures,
        "Meta diagnostics workbench localizes command-speed, context-fit, test, architecture-boundary, and standalone-wrapper readiness failures without granting private-root, performance, wrapper, hosted, or publication authority",
        failures=meta_diagnostics_failures[:20],
    )

    frontend_hud_failures = _frontend_hud_control_surface_failures(root)
    check(
        "validator.frontend_hud_control_surface_specimen",
        not frontend_hud_failures,
        "Frontend HUD control-surface specimen separates operator command, runtime status, receipt evidence, and publication boundaries without making display state authority",
        failures=frontend_hud_failures[:20],
    )

    check_specimen(
        "validator.demo_receipt_storyboard_specimen",
        "demo_receipt_storyboard_microcosm",
        _demo_receipt_storyboard_failures,
        "Demo receipt storyboard specimen sequences scenes through registry rows, validator refs, receipt refs, allowed narration, disallowed claims, and fail-closed website/publication gates",
    )

    check_specimen(
        "validator.website_card_projection_gate_specimen",
        "website_card_projection_gate_microcosm",
        _website_card_projection_gate_failures,
        "Website-card projection gate blocks copy that outruns registry rows, storyboard receipts, validator refs, HUD boundaries, publication gates, or card authority boundaries",
    )

    check_specimen(
        "validator.thiel_evidence_packet_gate_specimen",
        "thiel_evidence_packet_gate_microcosm",
        _thiel_evidence_packet_gate_failures,
        "Thiel evidence packet gate blocks unlanded candidates, website-card-as-evidence, probe/publication overclaims, and private-root equivalence claims",
    )

    check_specimen(
        "validator.recipient_review_route_gate_specimen",
        "recipient_review_route_gate_microcosm",
        _recipient_review_route_gate_failures,
        "Recipient review route gate allows only private review rows and blocks public-send, novelty, license/citation, hosted-remote, private-context, and publication overclaims",
    )

    check_specimen(
        "validator.license_citation_disclosure_gate_specimen",
        "license_citation_disclosure_gate_microcosm",
        _license_citation_disclosure_gate_failures,
        "License/citation/disclosure gate separates selected license posture from active public grant, mechanism description from citation clearance, scope text from disclosure clearance, and local probes from hosted-public or publication claims",
    )

    check_specimen(
        "validator.hosted_public_ci_workflow_gate_specimen",
        "hosted_public_ci_workflow_gate_microcosm",
        _hosted_public_ci_workflow_gate_failures,
        "Hosted-public CI workflow gate separates local clone and local clean-run evidence from hosted public remote, hosted CI, GitHub export, deployment, public-site, and publication claims",
    )

    check_specimen(
        "validator.release_artifact_integrity_witness_specimen",
        "release_artifact_integrity_witness_microcosm",
        _release_artifact_integrity_witness_failures,
        "Release artifact integrity witness hashes source clips and keeps artifact evidence below evaluator, package, deployment, public-release, publication, private-root, and benchmark authority",
    )

    check_specimen(
        "validator.external_public_clone_probe_receipt_specimen",
        "external_public_clone_probe_receipt_microcosm",
        _external_public_clone_probe_receipt_failures,
        "External public clone probe receipt hashes hosted-gate source clips, preserves required clone proof fields, and keeps clone evidence below hosted-public, package, publication, private-root, and benchmark authority",
    )

    check_specimen(
        "validator.hosted_public_remote_receipt_reconciliation_specimen",
        "hosted_public_remote_receipt_reconciliation_microcosm",
        _hosted_public_remote_receipt_reconciliation_failures,
        "Hosted public remote receipt reconciliation hashes hosted, clone, package, and publication source clips, preserves missing proof fields, and keeps local reconciliation below hosted-public, package, publication, private-root, and benchmark authority",
    )

    check_specimen(
        "validator.actual_public_remote_clone_execution_specimen",
        "actual_public_remote_clone_execution_microcosm",
        _actual_public_remote_clone_execution_failures,
        "Actual public remote clone execution gate hashes reconciliation, clone, hosted, package, and publication source clips, preserves missing outside-world execution proof fields, and keeps the execution contract below public remote, package, publication, private-root, and benchmark authority",
    )

    check_specimen(
        "validator.operator_public_remote_clone_execution_receipt_specimen",
        "operator_public_remote_clone_execution_receipt_microcosm",
        _operator_public_remote_clone_execution_receipt_failures,
        "Operator public remote clone execution receipt intake hashes actual-execution, package, and publication source clips, emits a receipt template, and keeps operator receipt intake below public remote, package, publication, private-root, and benchmark authority",
    )

    check_specimen(
        "validator.public_release_package_manifest_gate_specimen",
        "public_release_package_manifest_gate_microcosm",
        _public_release_package_manifest_gate_failures,
        "Public release package manifest gate composes release, artifact, hosted-public, rights, citation, disclosure, recipient, probe, and publication boundaries without allowing package copy to become export or publication authority",
    )

    cold_start_skill_pack_failures = _cold_start_agent_skills_pack_failures(root)
    check(
        "validator.cold_start_agent_skills_pack_specimen",
        not cold_start_skill_pack_failures,
        "Cold-start skill-pack specimen turns markdown guidance into a deterministic agent route, specimen selector, receipt inspector, and fail-closed public-claim diagnosis probe",
        failures=cold_start_skill_pack_failures[:20],
    )

    specimen_suite_probe_failures = _release_specimen_suite_probe_failures(root)
    check(
        "validator.release_specimen_suite_probe",
        not specimen_suite_probe_failures,
        "Release specimen suite probe reruns selected mechanism specimens, binds their receipts, and preserves hosted-public/publication fail-closed boundaries",
        failures=specimen_suite_probe_failures[:20],
    )

    release_root_compiler_failures = _release_root_compiler_failures(root)
    check(
        "validator.release_root_compiler",
        not release_root_compiler_failures,
        "Release-root compiler enforces branch graph, root contract, std_python diagnostics, projection boundaries, and fail-closed authority",
        failures=release_root_compiler_failures[:20],
    )

    work_packet_failures = []
    work_packet_root = root / "runs" / "work_packets"
    kernel_rows = load_json(root / "state" / "axiom_kernel.json").get("rows", [])
    kernel_refs = {f"{row.get('target_kind')}:{row.get('target_id')}" for row in kernel_rows if isinstance(row, dict)}
    port_packet_ids = {row.get("id") for row in load_json(root / "ports" / "port_packets.json").get("rows", []) if isinstance(row, dict)}
    if not work_packet_root.exists():
        work_packet_failures.append({"path": "runs/work_packets", "reason": "missing work packet directory"})
    for path in (work_packet_root.glob("*.json") if work_packet_root.exists() else []):
        packet = load_json(path)
        rel = str(path.relative_to(root))
        required_packet_fields = {
            "id",
            "input_ref",
            "selected_ideas",
            "governing_axiom_rules",
            "selected_port_packets",
            "validator_refs",
            "receipt_refs",
            "next_move_refs",
            "acceptance_commands",
            "decision",
            "omissions",
        }
        missing = sorted(field for field in required_packet_fields if packet.get(field) in ("", None, []))
        if missing:
            work_packet_failures.append({"path": rel, "missing": missing})
        if not _path_ref_exists(root, packet.get("input_ref", "")):
            work_packet_failures.append({"path": rel, "missing_input_ref": packet.get("input_ref")})
        for selected in packet.get("selected_ideas", []):
            if selected.get("idea_id") not in idea_ids:
                work_packet_failures.append({"path": rel, "unknown_idea": selected.get("idea_id")})
        for rule in packet.get("governing_axiom_rules", []):
            if rule.get("kernel_ref") not in kernel_refs:
                work_packet_failures.append({"path": rel, "unknown_kernel_ref": rule.get("kernel_ref")})
            for validator_ref in rule.get("validator_refs", []):
                if validator_ref not in validators:
                    work_packet_failures.append({"path": rel, "unknown_rule_validator": validator_ref})
            for next_move_ref in rule.get("next_move_refs", []):
                if next_move_ref not in work_ids:
                    work_packet_failures.append({"path": rel, "unknown_rule_next_move": next_move_ref})
        for selected_packet in packet.get("selected_port_packets", []):
            if selected_packet.get("packet_id") not in port_packet_ids:
                work_packet_failures.append({"path": rel, "unknown_port_packet": selected_packet.get("packet_id")})
            if selected_packet.get("next_work_item_ref") not in work_ids:
                work_packet_failures.append({"path": rel, "unknown_packet_next_work": selected_packet.get("next_work_item_ref")})
        for validator_ref in packet.get("validator_refs", []):
            if validator_ref not in validators:
                work_packet_failures.append({"path": rel, "unknown_validator": validator_ref})
        for receipt_ref in packet.get("receipt_refs", []):
            if receipt_ref not in receipt_refs:
                work_packet_failures.append({"path": rel, "missing_receipt_ref": receipt_ref})
        for next_move_ref in packet.get("next_move_refs", []):
            if next_move_ref not in work_ids:
                work_packet_failures.append({"path": rel, "unknown_next_move": next_move_ref})
    if "receipts/work_packet_dogfood_operator_prompt.json" not in receipt_refs:
        work_packet_failures.append({"path": "receipts/work_packet_dogfood_operator_prompt.json", "reason": "missing dogfood receipt"})
    check("validator.work_packet", not work_packet_failures, "work packets turn public-safe prompts into selected ideas, axiom rules, port packets, validators, receipts, and next moves", failures=work_packet_failures[:20])

    missing_next_moves = []
    for idea in ideas:
        for next_move in idea.get("next_moves", []):
            if next_move not in work_ids:
                missing_next_moves.append({"idea_id": idea.get("id"), "next_move": next_move})
    check("validator.workitem_next_moves", not missing_next_moves, "idea next moves have WorkItem rows", failures=missing_next_moves[:20])

    receipt_failures = []
    receipt_files = list((root / "receipts").glob("*.json"))
    if (root / "microcosms").exists():
        receipt_files.extend((root / "microcosms").glob("*/receipt.json"))
    for path in receipt_files:
        receipt = load_json(path)
        for field in ("id", "claim_ref", "claim_tier", "command", "result", "status", "evidence_refs", "omissions"):
            if receipt.get(field) in ("", None, []):
                receipt_failures.append({"path": str(path.relative_to(root)), "missing": field})
    check("validator.receipts", not receipt_failures, "receipts carry command, result, evidence, and omissions", failures=receipt_failures[:20])

    strategy_failures = []
    for row in strategy_rows:
        for field in ("id", "lane_id", "receipt_ref", "decision", "pivot", "next_wave"):
            if field not in row:
                strategy_failures.append({"row_id": row.get("id"), "missing": field})
        receipt_ref = row.get("receipt_ref")
        if receipt_ref and receipt_ref not in receipt_refs:
            strategy_failures.append({"row_id": row.get("id"), "missing_receipt": receipt_ref})
    check("validator.strategy_ledger", not strategy_failures, "strategy ledger rows cite receipts and pivot decisions", failures=strategy_failures[:20])

    autonomous_seed_failures = []
    strategy_path = root / "strategy" / "strategy.json"
    seed_path = root / "strategy" / "seed.md"
    lattice_path = root / "strategy" / "open_subphases.json"
    fixture_path = root / "fixtures" / "ideas" / "synthetic_autonomous_seed.json"
    receipt_path = root / "receipts" / "autonomous_seed_fixture.json"
    if not strategy_path.exists():
        autonomous_seed_failures.append({"path": "strategy/strategy.json", "reason": "missing strategy"})
    if not seed_path.exists():
        autonomous_seed_failures.append({"path": "strategy/seed.md", "reason": "missing seed"})
    if not lattice_path.exists():
        autonomous_seed_failures.append({"path": "strategy/open_subphases.json", "reason": "missing open subphase lattice"})
    if not fixture_path.exists():
        autonomous_seed_failures.append({"path": "fixtures/ideas/synthetic_autonomous_seed.json", "reason": "missing autonomous seed fixture"})
    if not receipt_path.exists():
        autonomous_seed_failures.append({"path": "receipts/autonomous_seed_fixture.json", "reason": "missing autonomous seed receipt"})
    if not autonomous_seed_failures:
        strategy = load_json(strategy_path)
        seed_text = seed_path.read_text(encoding="utf-8").lower()
        lattice = load_json(lattice_path)
        fixture = load_json(fixture_path)
        receipt = load_json(receipt_path)
        for ref in strategy.get("reads_first", []):
            if not _path_ref_exists(root, ref):
                autonomous_seed_failures.append({"path": "strategy/strategy.json", "missing_read": ref})
        required_reads = {
            "strategy/seed.md",
            "strategy/strategy.json",
            "fixtures/ideas/synthetic_autonomous_seed.json",
            "strategy/ledger.jsonl",
            "receipts/autonomous_seed_fixture.json",
        }
        missing_reads = sorted(required_reads - set(strategy.get("reads_first", [])))
        if missing_reads:
            autonomous_seed_failures.append({"path": "strategy/strategy.json", "missing_required_reads": missing_reads})
        for term in ("validator", "receipt", "ledger", "workitem", "pivot"):
            if term not in seed_text and term not in " ".join(strategy.get("wave_loop", [])).lower():
                autonomous_seed_failures.append({"path": "strategy/seed.md", "missing_seed_term": term})
        pivot_text = " ".join(strategy.get("pivot_rules", [])).lower()
        if "receipt" not in pivot_text or "workitem" not in pivot_text:
            autonomous_seed_failures.append({"path": "strategy/strategy.json", "reason": "pivot rules must cite receipt pressure and WorkItems"})
        if fixture.get("kind") != "synthetic_autonomous_seed":
            autonomous_seed_failures.append({"path": "fixtures/ideas/synthetic_autonomous_seed.json", "kind": fixture.get("kind")})
        for idea_ref in fixture.get("expected_idea_refs", []):
            if idea_ref not in idea_ids:
                autonomous_seed_failures.append({"path": "fixtures/ideas/synthetic_autonomous_seed.json", "unknown_idea_ref": idea_ref})
        if "idea.autonomous_strategy_seed" not in fixture.get("expected_idea_refs", []):
            autonomous_seed_failures.append({"path": "fixtures/ideas/synthetic_autonomous_seed.json", "reason": "fixture must target idea.autonomous_strategy_seed"})
        lanes = lattice.get("lanes", [])
        lane_ids = [lane.get("lane_id") for lane in lanes if isinstance(lane, dict)]
        if len(lane_ids) != len(set(lane_ids)):
            autonomous_seed_failures.append({"path": "strategy/open_subphases.json", "reason": "lane ids must be unique"})
        namespaces = [lane.get("receipt_namespace") for lane in lanes if isinstance(lane, dict)]
        if len(namespaces) != len(set(namespaces)):
            autonomous_seed_failures.append({"path": "strategy/open_subphases.json", "reason": "receipt namespaces must be unique"})
        owned_paths: list[tuple[str, str]] = []
        for lane in lanes:
            if not isinstance(lane, dict):
                autonomous_seed_failures.append({"path": "strategy/open_subphases.json", "reason": "lane must be an object"})
                continue
            if not lane.get("owned_paths"):
                autonomous_seed_failures.append({"lane_id": lane.get("lane_id"), "missing": "owned_paths"})
            for owned in lane.get("owned_paths", []):
                normalized = str(owned).strip("/")
                if normalized:
                    owned_paths.append((str(lane.get("lane_id")), normalized))
        for index, (left_lane, left_path) in enumerate(owned_paths):
            for right_lane, right_path in owned_paths[index + 1 :]:
                if left_lane == right_lane:
                    continue
                if left_path == right_path or left_path.startswith(right_path + "/") or right_path.startswith(left_path + "/"):
                    autonomous_seed_failures.append(
                        {
                            "path": "strategy/open_subphases.json",
                            "reason": "owned path overlap",
                            "left": {"lane_id": left_lane, "path": left_path},
                            "right": {"lane_id": right_lane, "path": right_path},
                        }
                    )
        if receipt.get("claim_ref") != "idea.autonomous_strategy_seed" or receipt.get("status") != "ok":
            autonomous_seed_failures.append({"path": "receipts/autonomous_seed_fixture.json", "reason": "receipt must claim idea.autonomous_strategy_seed with ok status"})
        for ref in receipt.get("evidence_refs", []):
            if not _path_ref_exists(root, ref):
                autonomous_seed_failures.append({"path": "receipts/autonomous_seed_fixture.json", "missing_evidence_ref": ref})
    check("validator.autonomous_seed_fixture", not autonomous_seed_failures, "autonomous seed fixture has public reads, pivot rules, receipt, and non-overlapping lanes", failures=autonomous_seed_failures[:20])

    status_control_failures = _status_preserving_control_plane_specimen_failures(root)
    check(
        "validator.status_preserving_control_plane_specimen",
        not status_control_failures,
        "Status-preserving control-plane specimen evaluates legal and forbidden status transitions through a separate policy judgment engine and keeps hosted/public/publication authority fail-closed",
        failures=status_control_failures[:20],
    )

    correction_survival_failures = _correction_survival_loop_specimen_failures(root)
    check(
        "validator.correction_survival_loop_specimen",
        not correction_survival_failures,
        "Correction-survival loop specimen re-checks capture-before-prose ordering, typed failure-mode classification, durable patch nonempty, capture reference, future-route change, effectiveness witness (old-behavior-fails/new-behavior-passes), and private-content absence",
        failures=correction_survival_failures[:20],
    )

    navigator_failures = _self_comprehension_navigator_specimen_failures(root)
    check(
        "validator.self_comprehension_navigator_specimen",
        not navigator_failures,
        "Self-comprehension navigator specimen re-checks entry-packet kind+ids binding, banded drilldown order, banned-route fail-closure with replacement, stale-projection refusal with freshness command, cold-start routing to correct kind, banned-vs-correct effectiveness witness, and private-content absence",
        failures=navigator_failures[:20],
    )

    status_collapse_failures = _status_collapse_suite_failures(root)
    check(
        "validator.status_collapse_suite",
        not status_collapse_failures,
        "adversarial public-safe microcosm cases compute policy judgments for illicit source, atom, WorkItem, receipt, runtime, hindsight, fixture, and review authority upgrades",
        failures=status_collapse_failures[:20],
        expected_case_ids=sorted(EXPECTED_STATUS_COLLAPSE_CASE_IDS),
    )

    projection_failures = []
    atlas = load_json(root / "navigation" / "atlas.json")
    if atlas.get("authority_posture") != "projection_not_authority":
        projection_failures.append({"path": "navigation/atlas.json", "reason": "atlas must declare projection_not_authority"})
    for row in atlas.get("rows", []):
        card = row.get("card")
        if not card or not (root / card).exists():
            projection_failures.append({"idea_id": row.get("idea_id"), "missing_card": card})
        elif "Projection, not authority" not in (root / card).read_text(encoding="utf-8"):
            projection_failures.append({"idea_id": row.get("idea_id"), "card": card, "reason": "missing projection boundary"})
    check("validator.projection_preservation", not projection_failures, "navigation projections preserve authority boundary and cards", failures=projection_failures[:20])

    cold_eval_failures = []
    tasks_payload = load_json(root / "evals" / "cold_agent_ab" / "tasks.json")
    task_ids = {task.get("id") for task in tasks_payload.get("tasks", [])}
    for task in tasks_payload.get("tasks", []):
        if set(task.get("arms", [])) != {"A.flat_repo_entry", "B.idea_first_packet"}:
            cold_eval_failures.append({"task_id": task.get("id"), "reason": "expected both eval arms"})
        for ref in task.get("expected_refs", []):
            if not _path_ref_exists(root, ref):
                cold_eval_failures.append({"task_id": task.get("id"), "missing_ref": ref})
    scorecard_path = root / "runs" / "cold_agent_ab" / "seed_scorecard.json"
    expected_scoring_policy = "declared_route_refs_no_expected_ref_injection_v1"
    if not scorecard_path.exists():
        cold_eval_failures.append({"path": "runs/cold_agent_ab/seed_scorecard.json", "reason": "missing seed scorecard"})
    else:
        scorecard = load_json(scorecard_path)
        if scorecard.get("tasks_ref") != "evals/cold_agent_ab/tasks.json":
            cold_eval_failures.append({"path": "runs/cold_agent_ab/seed_scorecard.json", "reason": "wrong tasks_ref"})
        if scorecard.get("scoring_policy") != expected_scoring_policy:
            cold_eval_failures.append(
                {
                    "path": "runs/cold_agent_ab/seed_scorecard.json",
                    "reason": "cold-agent scorecard must use declared-route scoring without expected-ref injection",
                    "scoring_policy": scorecard.get("scoring_policy"),
                }
            )
        route_sources = scorecard.get("route_sources", {})
        if (
            "B.idea_first_packet" not in route_sources
            or "evals/cold_agent_ab/tasks.json" in route_sources.get("B.idea_first_packet", [])
        ):
            cold_eval_failures.append(
                {
                    "path": "runs/cold_agent_ab/seed_scorecard.json",
                    "reason": "idea-first arm route sources must come from navigation surfaces, not task expected refs",
                }
            )
        if scorecard.get("summary", {}).get("idea_first_win_count") != len(task_ids):
            cold_eval_failures.append(
                {"path": "runs/cold_agent_ab/seed_scorecard.json", "reason": "idea-first arm did not win every fixture task"}
            )
        rows_by_key = {(row.get("task_id"), row.get("arm")): row for row in scorecard.get("rows", [])}
        for row in scorecard.get("rows", []):
            if row.get("scoring_policy") != expected_scoring_policy:
                cold_eval_failures.append(
                    {"task_id": row.get("task_id"), "arm": row.get("arm"), "reason": "row has wrong scoring policy"}
                )
            if row.get("expected_ref_injection_used") is not False:
                cold_eval_failures.append(
                    {
                        "task_id": row.get("task_id"),
                        "arm": row.get("arm"),
                        "reason": "row must not inject expected refs into the arm route",
                    }
                )
        for task_id in task_ids:
            flat = rows_by_key.get((task_id, "A.flat_repo_entry"))
            idea = rows_by_key.get((task_id, "B.idea_first_packet"))
            if not flat or not idea:
                cold_eval_failures.append({"task_id": task_id, "reason": "missing arm score row"})
                continue
            if idea.get("score", 0) <= flat.get("score", 0):
                cold_eval_failures.append({"task_id": task_id, "reason": "idea-first score must exceed flat score"})
            if idea.get("private_boundary_violations") != 0 or flat.get("private_boundary_violations") != 0:
                cold_eval_failures.append({"task_id": task_id, "reason": "private boundary violation in eval arm"})
            for ref in idea.get("evidence_refs", []):
                if not _path_ref_exists(root, ref):
                    cold_eval_failures.append({"task_id": task_id, "missing_evidence_ref": ref})
    if "receipts/cold_agent_ab_seed.json" not in receipt_refs:
        cold_eval_failures.append({"path": "receipts/cold_agent_ab_seed.json", "reason": "missing eval receipt"})
    check(
        "validator.cold_agent_ab",
        not cold_eval_failures,
        "idea-first packet beats flat repo entry on declared-route fixture quality without expected-ref injection",
        failures=cold_eval_failures[:20],
    )

    synthesis_failures = []
    synthesis_root = root / "runs" / "synthesis"
    if not synthesis_root.exists():
        synthesis_failures.append({"path": "runs/synthesis", "reason": "missing synthesis run directory"})
    for path in (synthesis_root.glob("*.json") if synthesis_root.exists() else []):
        if path.name.endswith(".schema.json"):
            continue
        run = load_json(path)
        if not _path_ref_exists(root, run.get("input_ref", "")):
            synthesis_failures.append({"path": str(path.relative_to(root)), "missing_input": run.get("input_ref")})
        if not run.get("selected_ideas"):
            synthesis_failures.append({"path": str(path.relative_to(root)), "reason": "no selected ideas"})
        for selected in run.get("selected_ideas", []):
            if selected.get("idea_id") not in idea_ids:
                synthesis_failures.append({"path": str(path.relative_to(root)), "unknown_idea": selected.get("idea_id")})
        for capability_ref in run.get("capability_refs", []):
            if capability_ref not in capability_ids:
                synthesis_failures.append({"path": str(path.relative_to(root)), "unknown_capability": capability_ref})
        for projected in run.get("projected_work_items", []):
            if projected.get("work_item_id") not in work_ids:
                synthesis_failures.append({"path": str(path.relative_to(root)), "unknown_work_item": projected.get("work_item_id")})
    check("validator.synthesis_run", not synthesis_failures, "synthesis runs resolve input, selected ideas, capabilities, and WorkItems", failures=synthesis_failures[:20])

    benchmark = load_json(root / "benchmarks" / "research" / "benchmark_feasibility.json")
    benchmark_failures = [
        row for row in benchmark.get("rows", []) if row.get("adapter_status") != "blocked_until_gate_receipt"
    ]
    check("validator.benchmark_gate", not benchmark_failures, "benchmark adapters stay blocked until research receipts exist", failures=benchmark_failures[:20])

    private_hits = private_boundary_hits(root)
    check("validator.private_boundary", not private_hits, "public root has no private paths, credentials, provider state, or raw expletive voice", hits=private_hits[:20])

    site_projection_failures: list[dict[str, Any]] = []
    site_manifest_path = root / "state" / "site_projection_manifest.json"
    if not site_manifest_path.exists():
        site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "missing site projection manifest"})
    else:
        site_manifest = load_json(site_manifest_path)
        required_top = {
            "kind",
            "schema_version",
            "authority_posture",
            "mode",
            "generated_at",
            "generated_by",
            "source_refs",
            "publication_gate_ref",
            "publication_gate_status",
            "preview_controls",
            "mode_invariants",
            "pages",
            "card_rows",
            "blocked_cards",
            "website_card_source_capsule_handoff",
            "grammar_replay_card_gate_site_projection_handoff",
            "summary",
        }
        # Required fields must be PRESENT; empty arrays are allowed for blocked_cards
        # and (in edge cases) other list-shaped fields. Use key presence, not truthiness.
        for field in sorted(required_top):
            if field not in site_manifest:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "missing": field})
        # Mandatory non-empty fields (top-level scalars and the must-not-be-empty list/dict shapes)
        for field in ("kind", "schema_version", "authority_posture", "mode", "generated_at", "publication_gate_ref", "publication_gate_status"):
            if site_manifest.get(field) in ("", None):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "empty_required_scalar": field})
        for field in ("source_refs", "preview_controls", "mode_invariants", "pages", "card_rows", "summary"):
            if site_manifest.get(field) in (None, [], {}):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "empty_required_field": field})
        if site_manifest.get("kind") != "site_projection_manifest":
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "wrong_kind": site_manifest.get("kind")})
        if site_manifest.get("authority_posture") != "sandbox_projection_not_publication_authority":
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "authority_posture must declare sandbox_projection_not_publication_authority"})
        generated_by = site_manifest.get("generated_by") or {}
        if generated_by.get("projection_not_authority") is not True:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "generated_by must declare projection_not_authority true"})
        if not generated_by.get("source_refs"):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "generated_by.source_refs must not be empty"})
        site_mode = site_manifest.get("mode")
        legal_modes = {"local", "sandbox_preview", "controlled_review", "public"}
        if site_mode not in legal_modes:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "unknown_mode": site_mode})
        pc = site_manifest.get("preview_controls") or {}
        if site_mode != "public":
            if pc.get("noindex") is not True:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "mode": site_mode, "reason": "non-public mode requires noindex true"})
            if pc.get("production_domain_bound") is not False:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "mode": site_mode, "reason": "non-public mode forbids production_domain_bound"})
            if pc.get("public_claims_allowed") not in (False, "controlled_packet_only"):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "mode": site_mode, "reason": "non-public mode forbids general public_claims_allowed"})
        if site_mode == "public" and site_manifest.get("publication_gate_status") != "green":
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "public mode requires publication gate green"})
        gate_ref = site_manifest.get("publication_gate_ref")
        if gate_ref and not _path_ref_exists(root, gate_ref):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "missing_publication_gate": gate_ref})
        forbidden_tokens = tuple(site_manifest.get("forbidden_public_launch_tokens") or [])
        seen_routes: set[str] = set()
        for page in site_manifest.get("pages", []) or []:
            if not isinstance(page, dict):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "page row must be an object"})
                continue
            for field in ("page_id", "route", "title", "source_refs"):
                if page.get(field) in ("", None, []):
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "page_id": page.get("page_id"), "missing": field})
            route = page.get("route")
            if not isinstance(route, str) or not route.endswith(".html") or "/" in route:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "page_id": page.get("page_id"), "reason": "page route must be a flat .html filename"})
                continue
            if route in seen_routes:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "duplicate page route", "route": route})
            seen_routes.add(route)
            sandbox_html = root / "site" / "sandbox" / route
            if not sandbox_html.exists():
                site_projection_failures.append({"path": f"site/sandbox/{route}", "reason": "missing sandbox HTML page"})
                continue
            text = sandbox_html.read_text(encoding="utf-8")
            lowered = text.lower()
            if site_mode != "public" and "noindex" not in lowered:
                site_projection_failures.append({"path": f"site/sandbox/{route}", "reason": "sandbox HTML must carry noindex meta in non-public mode"})
            if site_mode == "sandbox_preview" and "sandbox preview" not in lowered:
                site_projection_failures.append({"path": f"site/sandbox/{route}", "reason": "sandbox_preview mode HTML must carry SANDBOX PREVIEW banner"})
            if site_mode != "public":
                for forbidden in forbidden_tokens:
                    if not isinstance(forbidden, str) or not forbidden:
                        continue
                    if forbidden.lower() in lowered:
                        site_projection_failures.append({"path": f"site/sandbox/{route}", "forbidden_token": forbidden})
        for card in site_manifest.get("card_rows", []) or []:
            if not isinstance(card, dict):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "card_row must be an object"})
                continue
            card_id = card.get("card_id")
            for python_ref in card.get("python_refs") or []:
                if not _path_ref_exists(root, python_ref):
                    site_projection_failures.append({"card_id": card_id, "missing_python_ref": python_ref})
            for receipt_ref in card.get("receipt_refs") or []:
                if not _path_ref_exists(root, receipt_ref):
                    site_projection_failures.append({"card_id": card_id, "missing_receipt_ref": receipt_ref})
            # Slice 2: extended ref checks — source/concept refs are paths,
            # standard refs are symbolic registry ids (presence-only here).
            for source_ref in card.get("source_refs") or []:
                if isinstance(source_ref, str) and source_ref and not _path_ref_exists(root, source_ref):
                    site_projection_failures.append({"card_id": card_id, "missing_source_ref": source_ref})
            for concept_ref in card.get("concept_refs") or []:
                if isinstance(concept_ref, str) and concept_ref and not _path_ref_exists(root, concept_ref):
                    site_projection_failures.append({"card_id": card_id, "missing_concept_ref": concept_ref})
            standard_refs_list = card.get("standard_refs") or []
            if not all(isinstance(s, str) and s for s in standard_refs_list):
                site_projection_failures.append({"card_id": card_id, "reason": "standard_refs must be non-empty strings"})

        handoff = site_manifest.get("website_card_source_capsule_handoff") or {}
        if handoff.get("schema_version") != "site_projection_website_card_source_capsule_handoff_v0":
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "website card source-capsule handoff schema mismatch"})
        if (handoff.get("generated_by") or {}).get("projection_not_authority") is not True:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "handoff generated_by must declare projection_not_authority true"})
        handoff_cases = ((handoff.get("mechanism") or {}).get("cases") or [])
        handoff_status = handoff.get("status") or {}
        handoff_authority = handoff.get("authority") or {}
        if not handoff_cases:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "website card source-capsule handoff must include cases"})
        if handoff_status.get("case_count") != len(handoff_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "handoff case_count does not match cases"})
        if site_manifest.get("summary", {}).get("website_card_source_capsule_count") != len(handoff_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "summary website_card_source_capsule_count does not match cases"})
        if handoff_status.get("source_capsule_count") != len(handoff_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "handoff source_capsule_count does not match cases"})
        if handoff_authority.get("self_attestation_count") != 0:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "handoff self_attestation_count must remain zero"})
        for field in ("public_release_claim_count", "publication_claim_count", "private_root_equivalence_claim_count", "benchmark_win_claim_count"):
            if handoff_authority.get(field) != 0:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": f"handoff authority {field} must remain zero"})
            if site_manifest.get("summary", {}).get(field) != 0:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": f"site projection summary {field} must remain zero"})
        if int(handoff_authority.get("evaluator_authority_count", 0)) < len(handoff_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "handoff evaluator authority must cover every case"})
        for case in handoff_cases:
            if not isinstance(case, dict):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "handoff case must be an object"})
                continue
            for field in (
                "case_id",
                "source_card_id",
                "source_ref",
                "source_clip",
                "source_clip_hash",
                "semantic_carryforward",
                "transformation",
                "evaluator_or_validator",
                "outcome",
                "repair_route",
                "restart_point",
                "teaching_rule",
                "evidence_refs",
                "anti_claims",
                "authority_flags",
            ):
                if case.get(field) in ("", None, [], {}):
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "missing": field})
            source_clip = case.get("source_clip")
            if isinstance(source_clip, str):
                expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
                if case.get("source_clip_hash") != expected_hash:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "reason": "source_clip_hash mismatch"})
                if case.get("upstream_source_clip_hash") not in (None, expected_hash):
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "reason": "upstream source hash does not match carried source clip"})
            source_ref = case.get("source_ref")
            if isinstance(source_ref, str) and source_ref and not _path_ref_exists(root, source_ref.split("::", 1)[0]):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "missing_source_ref": source_ref})
            for evidence_ref in case.get("evidence_refs") or []:
                if isinstance(evidence_ref, str) and evidence_ref and not _path_ref_exists(root, evidence_ref.split("::", 1)[0]):
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "missing_evidence_ref": evidence_ref})
            flags = case.get("authority_flags") or {}
            for flag in (
                "self_attestation_used_as_authority",
                "projection_used_as_claim_authority",
                "site_projection_used_as_claim_authority",
                "website_card_used_as_claim_authority",
                "public_release_claimed",
                "publication_claimed",
                "private_root_equivalence_claimed",
                "benchmark_win_claimed",
            ):
                if flags.get(flag) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "authority_flag_not_false": flag})

        grammar_handoff = site_manifest.get("grammar_replay_card_gate_site_projection_handoff") or {}
        if grammar_handoff.get("schema_version") != "site_projection_grammar_replay_card_gate_handoff_v0":
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay site-projection handoff schema mismatch"})
        if (grammar_handoff.get("generated_by") or {}).get("projection_not_authority") is not True:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay handoff generated_by must declare projection_not_authority true"})
        grammar_cases = ((grammar_handoff.get("mechanism") or {}).get("cases") or [])
        grammar_status = grammar_handoff.get("status") or {}
        grammar_authority = grammar_handoff.get("authority") or {}
        if len(grammar_cases) < 5:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay handoff must carry at least five failed cases"})
        for status_key, summary_key in (
            ("case_count", "grammar_replay_site_projection_case_count"),
            ("source_capsule_count", "grammar_replay_site_projection_source_capsule_count"),
            ("semantic_carryforward_count", "grammar_replay_site_projection_semantic_carryforward_count"),
            ("failure_replay_count", "grammar_replay_site_projection_failure_replay_count"),
            ("repair_route_count", "grammar_replay_site_projection_repair_route_count"),
            ("teaching_rule_count", "grammar_replay_site_projection_teaching_rule_count"),
            ("hash_verified_count", "grammar_replay_site_projection_hash_verified_count"),
            ("blocked_claim_count", "grammar_replay_site_projection_blocked_claim_count"),
        ):
            if grammar_status.get(status_key) != site_manifest.get("summary", {}).get(summary_key):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": f"grammar replay summary mismatch for {summary_key}"})
        if grammar_status.get("case_count") != len(grammar_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay handoff case_count does not match cases"})
        if grammar_status.get("source_capsule_count") != len(grammar_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay source_capsule_count does not match cases"})
        if grammar_status.get("failure_replay_count") != len(grammar_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay failure_replay_count does not match cases"})
        if grammar_status.get("hash_verified_count") != len(grammar_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay hash_verified_count must cover every case"})
        if grammar_status.get("missing_ref_count") != 0:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay handoff has missing refs"})
        if grammar_authority.get("self_attestation_count") != 0:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay self_attestation_count must remain zero"})
        if int(grammar_authority.get("evaluator_authority_count", 0)) < len(grammar_cases):
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay evaluator authority must cover every case"})
        for field, summary_key in (
            ("public_release_claim_count", "grammar_replay_site_projection_public_release_claim_count"),
            ("publication_claim_count", "grammar_replay_site_projection_publication_claim_count"),
            ("private_root_equivalence_claim_count", "grammar_replay_site_projection_private_root_equivalence_claim_count"),
            ("benchmark_win_claim_count", "grammar_replay_site_projection_benchmark_win_claim_count"),
        ):
            if grammar_authority.get(field) != 0:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": f"grammar replay authority {field} must remain zero"})
            if site_manifest.get("summary", {}).get(summary_key) != 0:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": f"site projection summary {summary_key} must remain zero"})
        for case in grammar_cases:
            if not isinstance(case, dict):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "grammar replay case must be an object"})
                continue
            for field in (
                "case_id",
                "source_card_id",
                "source_card_gate_case_id",
                "source_ref",
                "source_clip",
                "source_clip_hash",
                "semantic_carryforward",
                "transformation",
                "evaluator_or_validator",
                "outcome",
                "repair_route",
                "restart_point",
                "teaching_rule",
                "evidence_refs",
                "anti_claims",
                "authority_flags",
            ):
                if case.get(field) in ("", None, [], {}):
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "missing": field})
            source_clip = case.get("source_clip")
            if isinstance(source_clip, str):
                expected_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
                if case.get("source_clip_hash") != expected_hash:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "reason": "grammar replay source_clip_hash mismatch"})
                if case.get("upstream_source_clip_hash") != expected_hash:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "reason": "grammar replay upstream source hash not preserved"})
            if case.get("source_card_id") != "card.demo_grammar_replay_website_boundary":
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "reason": "grammar replay case source_card_id mismatch"})
            for evidence_ref in case.get("evidence_refs") or []:
                if isinstance(evidence_ref, str) and evidence_ref and not _path_ref_exists(root, evidence_ref.split("::", 1)[0]):
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "missing_evidence_ref": evidence_ref})
            semantic = case.get("semantic_carryforward") or {}
            for field in (
                "projection_not_authority",
            ):
                if semantic.get(field) is not True:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "semantic_claim_not_true": field})
            for field in (
                "public_release_claimed",
                "publication_claimed",
                "private_root_equivalence_claimed",
                "benchmark_win_claimed",
                "hosted_public_claimed",
                "site_projection_used_as_claim_authority",
            ):
                if semantic.get(field) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "semantic_claim_not_false": field})
            flags = case.get("authority_flags") or {}
            for flag in (
                "self_attestation_used_as_authority",
                "projection_used_as_claim_authority",
                "site_projection_used_as_claim_authority",
                "website_card_used_as_claim_authority",
                "grammar_replay_used_as_public_authority",
                "source_capsule_hash_used_as_public_permission",
                "hosted_public_claimed",
                "public_release_claimed",
                "publication_claimed",
                "private_root_equivalence_claimed",
                "benchmark_win_claimed",
            ):
                if flags.get(flag) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": case.get("case_id"), "authority_flag_not_false": flag})

        artifact_case_id = "site_projection_consumes_card_artifact_digest_requirement_website_boundary_source_capsule"
        artifact_cases = [
            case
            for case in handoff_cases
            if isinstance(case, dict) and case.get("case_id") == artifact_case_id
        ]
        if not artifact_cases:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "missing artifact digest site-projection boundary case"})
        else:
            artifact_case = artifact_cases[0]
            if handoff_status.get("artifact_digest_site_projection_case_count") != len(artifact_cases):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "artifact digest site-projection case count mismatch"})
            if site_manifest.get("summary", {}).get("artifact_digest_site_projection_case_count") != len(artifact_cases):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "summary artifact digest site-projection case count mismatch"})
            required_artifact_refs = {
                "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
                "microcosms/release_artifact_integrity_witness/integrity_witness.json",
                "microcosms/release_artifact_integrity_witness/receipt.json",
                "microcosms/public_release_package_manifest_gate/package_manifest.json",
                "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
                "state/artifact_manifest.json",
                "release/publication_gate.json",
                "site/sandbox/site_projection_manifest.json",
                "site/sandbox/site_projection_bundle.json",
            }
            artifact_evidence = set(artifact_case.get("evidence_refs") or [])
            for required_ref in sorted(required_artifact_refs):
                if required_ref not in artifact_evidence:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "missing_artifact_evidence_ref": required_ref})
            artifact_semantic = artifact_case.get("semantic_carryforward") or {}
            if artifact_semantic.get("projection_not_authority") is not True:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "reason": "artifact semantic carryforward must declare projection_not_authority"})
            for field in (
                "public_release_claimed",
                "publication_claimed",
                "hosted_public_claimed",
                "package_export_claimed",
                "private_root_equivalence_claimed",
                "benchmark_win_claimed",
            ):
                if artifact_semantic.get(field) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "semantic_claim_not_false": field})
            artifact_boundary = artifact_case.get("artifact_digest_site_projection_boundary") or {}
            if artifact_boundary.get("schema_version") != "site_projection_artifact_digest_boundary_v0":
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "reason": "artifact digest site-projection boundary schema mismatch"})
            if artifact_boundary.get("site_projection_digest_is_deployment_evidence") is not False:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "reason": "site projection digest cannot be deployment evidence"})
            if artifact_boundary.get("site_projection_digest_is_hosted_public_evidence") is not False:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "reason": "site projection digest cannot be hosted public evidence"})
            if artifact_boundary.get("artifact_digest_requirement_used_as_authority") is not False:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "reason": "artifact digest requirement cannot become site projection authority"})
            if int(artifact_boundary.get("source_witness_hash_preserved_count", 0)) < 1:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "reason": "artifact digest boundary must preserve source witness hash count"})
            if int(artifact_boundary.get("package_row_attachment_count", 0)) < 1:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "reason": "artifact digest boundary must preserve package row attachment count"})
            artifact_flags = artifact_case.get("authority_flags") or {}
            for flag in (
                "artifact_digest_requirement_used_as_site_projection_authority",
                "artifact_witness_used_as_public_authority",
                "site_projection_digest_used_as_deployment_evidence",
                "hosted_public_claimed",
                "package_export_claimed",
            ):
                if artifact_flags.get(flag) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": artifact_case_id, "authority_flag_not_false": flag})

        source_shuttle_case_id = "site_projection_consumes_card_source_shuttle_manifest_website_boundary_source_capsule"
        source_shuttle_cases = [
            case
            for case in handoff_cases
            if isinstance(case, dict) and case.get("case_id") == source_shuttle_case_id
        ]
        if not source_shuttle_cases:
            site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "missing source-shuttle site-projection boundary case"})
        else:
            source_shuttle_case = source_shuttle_cases[0]
            if handoff_status.get("source_shuttle_site_projection_case_count") != len(source_shuttle_cases):
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "source-shuttle site-projection case count mismatch"})
            for status_key, summary_key in (
                ("source_shuttle_site_projection_case_count", "source_shuttle_site_projection_case_count"),
                ("source_shuttle_site_projection_manifest_ref_count", "source_shuttle_site_projection_manifest_ref_count"),
                ("source_shuttle_site_projection_packet_hash_preserved_count", "source_shuttle_site_projection_packet_hash_preserved_count"),
                ("source_shuttle_site_projection_source_clip_hash_preserved_count", "source_shuttle_site_projection_source_clip_hash_preserved_count"),
                ("source_shuttle_site_projection_no_private_copy_rule_count", "source_shuttle_site_projection_no_private_copy_rule_count"),
                ("source_shuttle_site_projection_private_field_rehydration_count", "source_shuttle_site_projection_private_field_rehydration_count"),
                ("source_shuttle_site_projection_authority_count", "source_shuttle_site_projection_authority_count"),
                ("source_shuttle_site_projection_public_launch_claim_count", "source_shuttle_site_projection_public_launch_claim_count"),
                ("source_shuttle_site_projection_public_release_claim_count", "source_shuttle_site_projection_public_release_claim_count"),
                ("source_shuttle_site_projection_publication_claim_count", "source_shuttle_site_projection_publication_claim_count"),
                ("source_shuttle_site_projection_blocked_claim_count", "source_shuttle_site_projection_blocked_claim_count"),
            ):
                if handoff_status.get(status_key) != site_manifest.get("summary", {}).get(summary_key):
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": f"source-shuttle summary mismatch for {summary_key}"})
            required_source_shuttle_refs = {
                "microcosms/source_shuttle/source_shuttle_board.json",
                "microcosms/source_shuttle/receipt.json",
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
                "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
                "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
                "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
                "microcosms/public_release_package_manifest_gate/package_manifest.json",
                "microcosms/website_card_projection_gate/card_gate.json",
                "site/sandbox/site_projection_manifest.json",
                "site/sandbox/site_projection_bundle.json",
                "release/publication_gate.json",
            }
            source_shuttle_evidence = set(source_shuttle_case.get("evidence_refs") or [])
            for required_ref in sorted(required_source_shuttle_refs):
                if required_ref not in source_shuttle_evidence:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "missing_source_shuttle_evidence_ref": required_ref})
            source_shuttle_semantic = source_shuttle_case.get("semantic_carryforward") or {}
            for field in (
                "projection_not_authority",
            ):
                if source_shuttle_semantic.get(field) is not True:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "semantic_claim_not_true": field})
            for field in (
                "source_shuttle_private_field_rehydration_allowed",
                "source_shuttle_manifest_ref_used_as_site_projection_authority",
                "site_projection_source_shuttle_refs_used_as_public_launch_authority",
                "site_projection_source_shuttle_refs_used_as_hosted_public_evidence",
                "source_shuttle_public_launch_claimed",
                "source_shuttle_package_export_claimed",
                "hosted_public_claimed",
                "public_release_claimed",
                "publication_claimed",
                "private_root_equivalence_claimed",
                "benchmark_win_claimed",
            ):
                if source_shuttle_semantic.get(field) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "semantic_claim_not_false": field})
            source_shuttle_boundary = source_shuttle_case.get("source_shuttle_site_projection_boundary") or {}
            if source_shuttle_boundary.get("schema_version") != "site_projection_source_shuttle_boundary_v0":
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "reason": "source-shuttle site-projection boundary schema mismatch"})
            if int(source_shuttle_boundary.get("source_shuttle_manifest_ref_count", 0)) < 1:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "reason": "source-shuttle boundary must preserve manifest refs"})
            if int(source_shuttle_boundary.get("source_shuttle_packet_hash_preserved_count", 0)) < 1:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "reason": "source-shuttle boundary must preserve packet hashes"})
            if int(source_shuttle_boundary.get("source_shuttle_source_clip_hash_preserved_count", 0)) < 1:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "reason": "source-shuttle boundary must preserve source clip hashes"})
            if int(source_shuttle_boundary.get("source_shuttle_no_private_copy_rule_count", 0)) < 1:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "reason": "source-shuttle boundary must preserve no-private-copy rules"})
            for field in (
                "source_shuttle_private_field_rehydration_allowed",
                "source_shuttle_manifest_ref_used_as_site_projection_authority",
                "site_projection_source_shuttle_refs_used_as_public_launch_authority",
                "site_projection_source_shuttle_refs_used_as_hosted_public_evidence",
            ):
                if source_shuttle_boundary.get(field) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "boundary_claim_not_false": field})
            source_shuttle_flags = source_shuttle_case.get("authority_flags") or {}
            for flag in (
                "source_shuttle_private_field_rehydration_allowed",
                "source_shuttle_semantic_packet_used_as_card_authority",
                "source_shuttle_manifest_ref_used_as_website_authority",
                "source_shuttle_manifest_ref_used_as_site_projection_authority",
                "source_shuttle_manifest_ref_used_as_public_launch_authority",
                "site_projection_source_shuttle_refs_used_as_hosted_public_evidence",
                "source_shuttle_package_export_claimed",
                "source_shuttle_public_launch_claimed",
                "hosted_public_claimed",
                "public_release_claimed",
                "publication_claimed",
                "private_root_equivalence_claimed",
                "benchmark_win_claimed",
            ):
                if source_shuttle_flags.get(flag) is not False:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "case_id": source_shuttle_case_id, "authority_flag_not_false": flag})

        # Slice 2: self-contained preview bundle integrity.
        bundle_path = root / "site" / "sandbox" / "site_projection_bundle.json"
        if not bundle_path.exists():
            site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "reason": "missing sandbox preview bundle"})
        else:
            bundle = load_json(bundle_path)
            if bundle.get("kind") != "site_projection_bundle":
                site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "wrong_kind": bundle.get("kind")})
            for field in ("mode", "manifest_copy", "preview_controls", "link_resolution_invariants", "page_routes"):
                if bundle.get(field) in ("", None, [], {}):
                    site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "missing": field})
            if bundle.get("mode") != site_manifest.get("mode"):
                site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "reason": "bundle mode does not match manifest mode"})
            for summary_key in (
                "source_shuttle_site_projection_case_count",
                "source_shuttle_site_projection_manifest_ref_count",
                "source_shuttle_site_projection_packet_hash_preserved_count",
                "source_shuttle_site_projection_no_private_copy_rule_count",
                "source_shuttle_site_projection_authority_count",
                "source_shuttle_site_projection_public_launch_claim_count",
            ):
                if (bundle.get("summary") or {}).get(summary_key) != site_manifest.get("summary", {}).get(summary_key):
                    site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "reason": f"bundle source-shuttle summary mismatch for {summary_key}"})
            canonical_manifest_sha = hashlib.sha256(site_manifest_path.read_bytes()).hexdigest()
            bundle_manifest_copy = bundle.get("manifest_copy") or {}
            if bundle_manifest_copy.get("sha256") != canonical_manifest_sha:
                site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "reason": "bundle manifest_copy sha256 does not match canonical manifest"})
            # Slice 3A: per-page route shape + sha256 + kind legality + alignment with manifest.pages.
            legal_page_kinds = {"index", "microcosm_atlas", "release_gate", "evidence_graph_stub", "standards_wiki_stub", "demo_room_placeholder"}
            bundle_page_routes = bundle.get("page_routes") or []
            if not isinstance(bundle_page_routes, list):
                site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "reason": "page_routes must be a list"})
                bundle_page_routes = []
            bundle_route_set: set[str] = set()
            for entry in bundle_page_routes:
                if not isinstance(entry, dict):
                    site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "reason": "page_routes entry must be an object", "entry": entry})
                    continue
                for field in ("route", "page_id", "kind", "title", "sha256"):
                    if entry.get(field) in ("", None):
                        site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "route_entry": entry.get("route"), "missing": field})
                route = entry.get("route")
                if isinstance(route, str):
                    bundle_route_set.add(route)
                kind = entry.get("kind")
                if kind not in legal_page_kinds:
                    site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "route_entry": route, "unknown_kind": kind})
                if isinstance(route, str) and entry.get("sha256"):
                    page_path = root / "site" / "sandbox" / route
                    if page_path.exists():
                        actual_sha = hashlib.sha256(page_path.read_bytes()).hexdigest()
                        if actual_sha != entry["sha256"]:
                            site_projection_failures.append({"path": f"site/sandbox/{route}", "reason": "page sha256 mismatch vs bundle"})
                    else:
                        site_projection_failures.append({"path": f"site/sandbox/{route}", "reason": "page declared in bundle but file missing"})
            manifest_route_set = {p.get("route") for p in (site_manifest.get("pages") or []) if isinstance(p, dict)}
            orphan_in_bundle = bundle_route_set - manifest_route_set
            orphan_in_manifest = manifest_route_set - bundle_route_set
            if orphan_in_bundle:
                site_projection_failures.append({"path": "site/sandbox/site_projection_bundle.json", "reason": "page_routes contains routes not in manifest.pages", "orphans": sorted(orphan_in_bundle)})
            if orphan_in_manifest:
                site_projection_failures.append({"path": "state/site_projection_manifest.json", "reason": "pages contains routes not in bundle.page_routes", "orphans": sorted(orphan_in_manifest)})
            # Manifest pages must declare a kind too.
            for page in site_manifest.get("pages", []) or []:
                if not isinstance(page, dict):
                    continue
                if page.get("kind") not in legal_page_kinds:
                    site_projection_failures.append({"path": "state/site_projection_manifest.json", "page_id": page.get("page_id"), "unknown_kind": page.get("kind")})
            sandbox_manifest_path = root / "site" / "sandbox" / "site_projection_manifest.json"
            if not sandbox_manifest_path.exists():
                site_projection_failures.append({"path": "site/sandbox/site_projection_manifest.json", "reason": "missing sandbox manifest copy"})
            else:
                sandbox_manifest_sha = hashlib.sha256(sandbox_manifest_path.read_bytes()).hexdigest()
                if sandbox_manifest_sha != canonical_manifest_sha:
                    site_projection_failures.append({"path": "site/sandbox/site_projection_manifest.json", "reason": "sandbox manifest copy bytes differ from canonical"})
            receipt_copy = bundle.get("receipt_copy")
            if receipt_copy:
                sandbox_receipt_path = root / "site" / "sandbox" / "site_projection_receipt.json"
                if not sandbox_receipt_path.exists():
                    site_projection_failures.append({"path": "site/sandbox/site_projection_receipt.json", "reason": "bundle declares receipt_copy but file is missing"})
                else:
                    sandbox_receipt_sha = hashlib.sha256(sandbox_receipt_path.read_bytes()).hexdigest()
                    if receipt_copy.get("sha256") != sandbox_receipt_sha:
                        site_projection_failures.append({"path": "site/sandbox/site_projection_receipt.json", "reason": "bundle receipt_copy sha256 does not match sandbox receipt"})

        # Slice 2: link resolution from site/sandbox as static root.
        href_pattern = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
        external_prefixes = ("http://", "https://", "//", "mailto:", "data:", "tel:", "#")
        sandbox_static_root = root / "site" / "sandbox"
        for page in site_manifest.get("pages", []) or []:
            if not isinstance(page, dict):
                continue
            route = page.get("route")
            if not isinstance(route, str) or not route.endswith(".html") or "/" in route:
                continue
            html_path = sandbox_static_root / route
            if not html_path.exists():
                continue
            text = html_path.read_text(encoding="utf-8")
            for href in href_pattern.findall(text):
                stripped = href.strip()
                if not stripped or stripped.startswith(external_prefixes):
                    continue
                if stripped.startswith("/"):
                    site_projection_failures.append({"page": route, "absolute_link_not_allowed_in_sandbox": stripped})
                    continue
                if ".." in stripped.split("/"):
                    site_projection_failures.append({"page": route, "parent_path_escape": stripped})
                    continue
                target_rel = stripped.split("?", 1)[0].split("#", 1)[0]
                if not target_rel:
                    continue
                if not (sandbox_static_root / target_rel).exists():
                    site_projection_failures.append({"page": route, "unresolved_sandbox_link": stripped})
    check("validator.site_projection_manifest", not site_projection_failures, "site projection manifest is mode-controlled, references resolve, sandbox HTML carries noindex + SANDBOX PREVIEW banner without forbidden public-launch tokens, the preview bundle integrity-tags the manifest and receipt with sha256, and every internal link resolves from site/sandbox as static root", failures=site_projection_failures[:20])

    status = "ok" if not errors else "failed"
    report = {
        "kind": "idea_microcosm_validation_report",
        "schema_version": "validation_report_v0",
        "generated_at": at or _utc_now(),
        "root": str(root),
        "status": status,
        "error_count": len(errors),
        "checks": checks,
        "errors": errors,
    }
    if write_receipt:
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": "receipt.validation_run",
            "generated_at": report["generated_at"],
            "owner": "idea_microcosm.validator",
            "claim_ref": "idea.receipts_as_workingness",
            "claim_tier": "validator_result",
            "command": "python -m idea_microcosm.cli validate --root . --write-receipt",
            "result": status,
            "status": status,
            "evidence_refs": ["state/idea_graph.json", "navigation/atlas.json", "strategy/ledger.jsonl"],
            "omissions": ["This receipt proves fixture validators only, not external benchmark success."],
            "summary": {"error_count": len(errors), "check_count": len(checks)},
        }
        receipt_path = root / "receipts" / "validation_run.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["receipt_written"] = str(receipt_path.relative_to(root))
    return report
