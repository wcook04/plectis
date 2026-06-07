from __future__ import annotations

import argparse
import json
import shlex
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.accepted_organ_companion_gate"
SCHEMA_VERSION = "accepted_organ_companion_gate_card_v1"
PASS = "pass"
BLOCKED = "blocked"

ACCEPTED_ORGAN_COMPANION_PATHS: tuple[str, ...] = (
    "microcosm-substrate/core/substrate_substitution_ledger.json",
    "microcosm-substrate/core/organ_atlas.json",
    "microcosm-substrate/core/organ_evidence_classes.json",
    "microcosm-substrate/pyproject.toml",
    "microcosm-substrate/AGENTS.md",
    "microcosm-substrate/README.md",
    "microcosm-substrate/ORGANS.md",
    "microcosm-substrate/ARCHITECTURE.md",
)

ACTIVE_CLAIM_STATUSES = frozenset({"claimed", "active", "held", "leased"})
INACTIVE_CLAIM_STATUSES = frozenset(
    {"released", "expired", "refused", "failed", "stale", "closed"}
)

ANTI_CLAIM = (
    "This card only proves companion-packet completeness and visible Work "
    "Ledger ownership pressure. It does not authorize release, acceptance, "
    "publication, private-root equivalence, or bypassing an owning session."
)
DEFAULT_REQUESTER_LABEL = "microcosm companion gate"
DEFAULT_BLOCKED_ON = "accepted-organ companion packet blocked by live owner claim"
DEFAULT_VALIDATION_STATUS = (
    "companion gate card generated; rerun full transaction preflight before landing"
)


def _normalize_path(path: object) -> str:
    """Canonicalize a path-ish value for set comparison against companion paths.

    - Teleology: collapse declared/required/claim path spellings to one form so companion membership compares by value, not by accidental "./"-prefix or whitespace.
    - Guarantee: returns a stripped string with every leading "./" removed; None/empty/non-str inputs become "".
    - Fails: never raises; non-string inputs are coerced via str() and may yield "".
    """
    value = str(path or "").strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def _candidate_path(row: dict[str, Any]) -> str:
    """Pick the path a claim row is asserting ownership over.

    - Teleology: Work Ledger rows name their held surface under several keys; this normalizes them to one comparable path for companion matching.
    - Guarantee: returns the first non-empty normalized value among path/scope_id/scope_ref/held_surface, else "".
    - Fails: never raises; a row with none of those keys (or only empties) returns "".
    """
    for key in ("path", "scope_id", "scope_ref", "held_surface"):
        value = _normalize_path(row.get(key))
        if value:
            return value
    return ""


def extract_claim_rows(payload: object) -> list[dict[str, Any]]:
    """Extract Work Ledger-like claim rows from cards, status, or raw payloads.

    - Teleology: public entry that lets the gate accept a card, status dump, or raw Work Ledger blob and recover the claim rows hidden anywhere inside it.
    - Guarantee: returns a flat list of claim-row dicts harvested recursively; each row that lacked an own session id inherits the nearest enclosing owner_session_id/session_id.
    - Fails: never raises; payloads with no claim-shaped dict (no path or no claim_id/leased_until/session/collision marker) return [].
    - When-needed: inspect when feeding companion-owner detection from an arbitrary JSON shape and you need the claim-row normalization rules.
    - Escalates-to: _extract_claim_rows (the recursive implementation) and _candidate_path / _claim_session_id for per-row field semantics.
    """
    return _extract_claim_rows(payload)


def _extract_claim_rows(
    payload: object, *, inherited_session_id: str = ""
) -> list[dict[str, Any]]:
    """Recursively harvest claim rows, threading enclosing session ownership downward.

    - Teleology: walk an arbitrarily nested dict/list payload and collect every claim-shaped dict while propagating the closest owner_session_id so child rows inherit ownership.
    - Guarantee: returns claim-row dicts in document order; a dict is kept only if it has a candidate path AND a claim_id/leased_until/current-session/collision_sessions signal, with owner_session_id backfilled from the inherited id when the row had none.
    - Fails: never raises; scalars and claim-less containers contribute nothing and yield [].
    """
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        current_session_id = str(
            payload.get("owner_session_id")
            or payload.get("session_id")
            or inherited_session_id
            or ""
        )
        row = dict(payload)
        path = _candidate_path(row)
        if not path:
            pass
        elif (
            row.get("claim_id")
            or row.get("leased_until")
            or current_session_id
            or row.get("collision_sessions")
        ):
            if current_session_id and not _claim_session_id(row):
                row["owner_session_id"] = current_session_id
            rows.append(row)
        for child in payload.values():
            rows.extend(
                _extract_claim_rows(child, inherited_session_id=current_session_id)
            )
    elif isinstance(payload, list):
        for child in payload:
            rows.extend(
                _extract_claim_rows(child, inherited_session_id=inherited_session_id)
            )
    return rows


def _claim_is_active(row: dict[str, Any]) -> bool:
    """Decide whether a claim row still holds its surface.

    - Teleology: only live ownership pressure should block; this collapses status/state and lease fields into one liveness verdict.
    - Guarantee: returns False for INACTIVE statuses, True for ACTIVE statuses, else True only when leased_until is set and released_at is absent.
    - Fails: never raises; missing/unknown status with no live lease returns False.
    """
    status = str(row.get("status") or row.get("state") or "").lower()
    if status in INACTIVE_CLAIM_STATUSES:
        return False
    if status in ACTIVE_CLAIM_STATUSES:
        return True
    return bool(row.get("leased_until") and not row.get("released_at"))


def _claim_session_id(row: dict[str, Any]) -> str:
    """Resolve the owning session id of a claim row.

    - Teleology: actor-vs-other ownership comparison needs one canonical session id regardless of which key carries it.
    - Guarantee: returns owner_session_id if set, else session_id, else "".
    - Fails: never raises; a row with neither key returns "".
    """
    return str(row.get("owner_session_id") or row.get("session_id") or "")


def _blocking_claims(
    claim_rows: Iterable[dict[str, Any]],
    *,
    actor_session_id: str | None,
    companion_paths: set[str],
) -> list[dict[str, Any]]:
    """Select live foreign claims that sit on required companion paths.

    - Teleology: identify which other-session claims actually obstruct the scoped landing of the companion packet.
    - Guarantee: returns one deterministic blocker dict per active claim whose path is in companion_paths and whose owner differs from actor_session_id, sorted by (path, owner_session_id, claim_id), each carrying a request_owner_land_release_or_handoff coordination_action.
    - Fails: never raises; rows off-path, inactive, or owned by the actor are skipped; no qualifying claims yields [].
    - When-needed: inspect when a companion gate reports blocking_claims and you need the membership/liveness/self-ownership filter rules.
    - Escalates-to: _claim_is_active and _claim_session_id for the per-row predicates; evaluate_companion_gate for how blockers become BLOCKED status.
    - Non-goal: presence of zero blockers does not authorize release or landing; it only clears this one ownership-pressure check.
    """
    blockers: list[dict[str, Any]] = []
    for row in claim_rows:
        path = _candidate_path(row)
        if path not in companion_paths or not _claim_is_active(row):
            continue
        owner = _claim_session_id(row)
        if actor_session_id and owner == actor_session_id:
            continue
        blockers.append(
            {
                "path": path,
                "owner_session_id": owner,
                "claim_id": str(row.get("claim_id") or ""),
                "leased_until": str(row.get("leased_until") or ""),
                "coordination_action": "request_owner_land_release_or_handoff",
            }
        )
    return sorted(
        blockers,
        key=lambda row: (row["path"], row["owner_session_id"], row["claim_id"]),
    )


def _shell_join(argv: Iterable[str]) -> str:
    """Render an argv list as a copy-paste-safe shell command string.

    - Teleology: generated yield-request commands must paste cleanly even when paths or labels contain spaces/quotes.
    - Guarantee: returns the argv parts shlex-quoted and space-joined into one string.
    - Fails: never raises; an empty iterable returns "".
    """
    return " ".join(shlex.quote(str(part)) for part in argv)


def _yield_request_command(
    blocker: dict[str, Any],
    *,
    requester_session_id: str,
    requester_label: str,
    blocked_on: str,
    validation_status: str,
) -> str:
    """Build the paste-ready work_ledger.py session-yield-request command for one blocker.

    - Teleology: turn a detected blocking claim into the exact CLI an agent runs to ask the owning session to land-and-release.
    - Guarantee: returns a shell-quoted command targeting blocker.owner_session_id with class settlement_obligation_owner, action release_after_landing, result requested, and the blocker path plus requester/blocked-on/validation-status fields embedded.
    - Fails: never raises; emits a string regardless of field content (does not validate that the session id exists).
    """
    return _shell_join(
        [
            "./repo-python",
            "tools/meta/factory/work_ledger.py",
            "session-yield-request",
            "--target-session-id",
            blocker["owner_session_id"],
            "--target-class",
            "settlement_obligation_owner",
            "--requested-action",
            "release_after_landing",
            "--result",
            "requested",
            "--coordination-brief",
            "--requester-session-id",
            requester_session_id,
            "--requester-label",
            requester_label,
            "--blocked-on",
            blocked_on,
            "--validation-status",
            validation_status,
            "--held-path",
            blocker["path"],
        ]
    )


def _coordination_requests(
    blocking_claims: Iterable[dict[str, Any]],
    *,
    requester_session_id: str | None,
    requester_label: str,
    blocked_on: str,
    validation_status: str,
) -> list[dict[str, Any]]:
    """Assemble paste-ready coordination requests for every owned blocker.

    - Teleology: give the actor a ready list of who to ask, for which path, with the exact yield command, when blockers exist.
    - Guarantee: returns one request dict (target_session_id, held_path, claim_id, leased_until, command) per blocker that has an owner_session_id.
    - Fails: never raises; returns [] when requester_session_id is falsy or when no blocker carries an owner_session_id.
    - Escalates-to: _yield_request_command for the command shape; evaluate_companion_gate exposes the result as coordination_requests.
    """
    if not requester_session_id:
        return []
    requests: list[dict[str, Any]] = []
    for blocker in blocking_claims:
        if not blocker.get("owner_session_id"):
            continue
        requests.append(
            {
                "target_session_id": blocker["owner_session_id"],
                "held_path": blocker["path"],
                "claim_id": blocker["claim_id"],
                "leased_until": blocker["leased_until"],
                "command": _yield_request_command(
                    blocker,
                    requester_session_id=requester_session_id,
                    requester_label=requester_label,
                    blocked_on=blocked_on,
                    validation_status=validation_status,
                ),
            }
        )
    return requests


def evaluate_companion_gate(
    declared_paths: Iterable[str],
    claim_rows: Iterable[dict[str, Any]] = (),
    *,
    actor_session_id: str | None = None,
    requester_session_id: str | None = None,
    requester_label: str = DEFAULT_REQUESTER_LABEL,
    blocked_on: str = DEFAULT_BLOCKED_ON,
    validation_status: str = DEFAULT_VALIDATION_STATUS,
    required_companion_paths: Iterable[str] = ACCEPTED_ORGAN_COMPANION_PATHS,
) -> dict[str, Any]:
    """Render the read-only accepted-organ companion-gate card (packet completeness + owner pressure).

    - Teleology: the core checker proving a scoped accepted-organ landing both declares all required companion paths and faces no live foreign Work Ledger owner on them.
    - Guarantee: returns a SCHEMA_VERSION-stamped card whose status is PASS only when no required companion path is missing AND no other-session active claim sits on a required path; otherwise BLOCKED, with missing_companion_paths, blocking_claims, coordination_requests, a routed next_action, reentry_condition, and the ANTI_CLAIM string.
    - Fails: never raises; the card is the result envelope (status=BLOCKED with populated missing/blocking lists encodes failure, not an exception).
    - When-needed: inspect before landing or preflighting an accepted-organ companion packet, or when triaging why such a packet is BLOCKED.
    - Escalates-to: std accepted-organ companion-gate contract and full transaction preflight (DEFAULT_VALIDATION_STATUS says rerun it); _blocking_claims / _coordination_requests for the owner-pressure detail.
    - Non-goal: a PASS card does not authorize release, acceptance, publication, private-root equivalence, or bypassing an owning session — see anti_claim; it gates only companion completeness and visible ownership pressure.
    """
    required = tuple(_normalize_path(path) for path in required_companion_paths)
    required_set = set(required)
    declared = sorted({_normalize_path(path) for path in declared_paths if path})
    declared_set = set(declared)
    missing = sorted(required_set - declared_set)
    blocking_claims = _blocking_claims(
        claim_rows,
        actor_session_id=actor_session_id,
        companion_paths=required_set,
    )
    blocking_owner_session_ids = sorted(
        {
            row["owner_session_id"]
            for row in blocking_claims
            if row["owner_session_id"]
        }
    )
    coordination_requests = _coordination_requests(
        blocking_claims,
        requester_session_id=requester_session_id,
        requester_label=requester_label,
        blocked_on=blocked_on,
        validation_status=validation_status,
    )
    status = PASS if not missing and not blocking_claims else BLOCKED
    if missing:
        next_action = "include_required_companion_packet_or_split_non_accepted_mutation"
    elif blocking_claims:
        next_action = "wait_for_or_request_release_from_owner_session"
    else:
        next_action = "scoped_landing_may_continue_to_other_preflight_gates"
    return {
        "schema_version": SCHEMA_VERSION,
        "checker_id": CHECKER_ID,
        "status": status,
        "required_companion_paths": list(required),
        "declared_paths": declared,
        "declared_companion_count": len(required_set & declared_set),
        "declared_packet_has_all_companions": not missing,
        "missing_companion_paths": missing,
        "blocking_claim_count": len(blocking_claims),
        "blocking_owner_session_ids": blocking_owner_session_ids,
        "blocking_claims": blocking_claims,
        "coordination_request_count": len(coordination_requests),
        "coordination_requests": coordination_requests,
        "next_action": next_action,
        "reentry_condition": (
            "All required companion paths are present in the scoped packet and "
            "no other live Work Ledger owner holds those companion paths."
        ),
        "anti_claim": ANTI_CLAIM,
    }


def _load_claim_rows(path: str | None) -> list[dict[str, Any]]:
    """Load and flatten claim rows from an optional Work Ledger JSON file.

    - Teleology: adapt the CLI's --claims-json file into the claim-row list the gate consumes.
    - Guarantee: returns extract_claim_rows over the strictly-parsed file contents; a falsy path returns [].
    - Fails: propagates read_json_strict errors (missing file / malformed or non-strict JSON) to the caller; it does not swallow them.
    - Escalates-to: microcosm_core.schemas.read_json_strict for parse-failure semantics; extract_claim_rows for row recovery.
    """
    if not path:
        return []
    payload = read_json_strict(Path(path))
    return extract_claim_rows(payload)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: print the companion-gate card and signal blocked status via exit code.

    - Teleology: expose evaluate_companion_gate as a read-only command for preflight scripts and operators.
    - Guarantee: prints the card as sorted indented JSON to stdout and returns 0 when status is PASS or --check was not given; returns 1 only when --check is set and status is not PASS.
    - Fails: argparse exits nonzero on bad flags; a supplied --claims-json that is missing/malformed propagates read_json_strict errors (no card printed).
    - When-needed: inspect when wiring this gate into a CI/preflight step or interpreting its exit code.
    - Escalates-to: evaluate_companion_gate for the card contract; --check is the nonzero-on-blocked switch.
    - Non-goal: a zero exit does not authorize release/landing — it only reports companion completeness and ownership pressure (see the card anti_claim).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Render a read-only card for the accepted-organ companion packet gate."
        )
    )
    parser.add_argument(
        "--declared-path",
        action="append",
        default=[],
        help="Path declared in the scoped landing packet. Repeatable.",
    )
    parser.add_argument(
        "--claims-json",
        help="Optional Work Ledger status/claim JSON to inspect for companion owners.",
    )
    parser.add_argument(
        "--actor-session-id",
        help="Session id whose own claims should not be counted as blockers.",
    )
    parser.add_argument(
        "--requester-session-id",
        help="Session id to embed in paste-ready Work Ledger yield requests.",
    )
    parser.add_argument(
        "--requester-label",
        default=DEFAULT_REQUESTER_LABEL,
        help="Human-readable label to embed in generated yield requests.",
    )
    parser.add_argument(
        "--blocked-on",
        default=DEFAULT_BLOCKED_ON,
        help="Blocked-on text to embed in generated yield requests.",
    )
    parser.add_argument(
        "--validation-status",
        default=DEFAULT_VALIDATION_STATUS,
        help="Validation status text to embed in generated yield requests.",
    )
    parser.add_argument("--check", action="store_true", help="Exit nonzero if blocked.")
    args = parser.parse_args(argv)

    card = evaluate_companion_gate(
        args.declared_path,
        _load_claim_rows(args.claims_json),
        actor_session_id=args.actor_session_id,
        requester_session_id=args.requester_session_id,
        requester_label=args.requester_label,
        blocked_on=args.blocked_on,
        validation_status=args.validation_status,
    )
    print(json.dumps(card, indent=2, sort_keys=True))
    return 0 if card["status"] == PASS or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
