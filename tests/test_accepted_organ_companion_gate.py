from __future__ import annotations

import json

from microcosm_core.validators.accepted_organ_companion_gate import (
    ACCEPTED_ORGAN_COMPANION_PATHS,
    PASS,
    BLOCKED,
    evaluate_companion_gate,
    extract_claim_rows,
    main,
)


def _claim(
    path: str,
    *,
    session_id: str = "codex_20260601T0410Z_batch11_substrate_honesty_closure",
    claim_id: str = "wlc_batch11",
    status: str = "claimed",
) -> dict[str, str]:
    return {
        "status": status,
        "path": path,
        "session_id": session_id,
        "claim_id": claim_id,
        "leased_until": "2026-06-01T08:54:06Z",
    }


def test_gate_blocks_when_companion_packet_is_missing() -> None:
    card = evaluate_companion_gate(["microcosm-substrate/src/microcosm_core/organs/x.py"])

    assert card["status"] == BLOCKED
    assert card["declared_packet_has_all_companions"] is False
    assert card["missing_companion_paths"] == sorted(ACCEPTED_ORGAN_COMPANION_PATHS)
    assert card["blocking_claim_count"] == 0
    assert card["next_action"] == "include_required_companion_packet_or_split_non_accepted_mutation"
    assert "does not authorize release" in card["anti_claim"]


def test_gate_blocks_when_companions_are_held_by_another_session() -> None:
    claims = [
        _claim("microcosm-substrate/core/substrate_substitution_ledger.json"),
        _claim("microcosm-substrate/core/organ_atlas.json", claim_id="wlc_atlas"),
        _claim(
            "microcosm-substrate/README.md",
            session_id="codex_owning_session",
            claim_id="wlc_self",
        ),
    ]

    card = evaluate_companion_gate(
        ACCEPTED_ORGAN_COMPANION_PATHS,
        claims,
        actor_session_id="codex_owning_session",
        requester_session_id="codex_requester",
        requester_label="batch5 closure",
        blocked_on="Batch5 closeout needs accepted-organ companions",
        validation_status="companion gate card blocked only by Batch11 claims",
    )

    assert card["status"] == BLOCKED
    assert card["declared_packet_has_all_companions"] is True
    assert card["missing_companion_paths"] == []
    assert card["blocking_claim_count"] == 2
    assert card["blocking_owner_session_ids"] == [
        "codex_20260601T0410Z_batch11_substrate_honesty_closure"
    ]
    assert {
        row["path"] for row in card["blocking_claims"]
    } == {
        "microcosm-substrate/core/substrate_substitution_ledger.json",
        "microcosm-substrate/core/organ_atlas.json",
    }
    assert card["coordination_request_count"] == 2
    commands = [row["command"] for row in card["coordination_requests"]]
    assert all("session-yield-request" in command for command in commands)
    assert all("--requested-action release_after_landing" in command for command in commands)
    assert all("--requester-session-id codex_requester" in command for command in commands)
    assert all("'batch5 closure'" in command for command in commands)
    assert any(
        "--held-path microcosm-substrate/core/organ_atlas.json" in command
        for command in commands
    )
    assert card["next_action"] == "wait_for_or_request_release_from_owner_session"


def test_gate_passes_when_companions_are_declared_and_unblocked() -> None:
    card = evaluate_companion_gate(
        ACCEPTED_ORGAN_COMPANION_PATHS,
        [
            _claim(
                "microcosm-substrate/core/organ_atlas.json",
                session_id="codex_current",
            ),
            _claim(
                "microcosm-substrate/core/organ_evidence_classes.json",
                status="released",
            ),
        ],
        actor_session_id="codex_current",
    )

    assert card["status"] == PASS
    assert card["declared_companion_count"] == len(ACCEPTED_ORGAN_COMPANION_PATHS)
    assert card["blocking_claims"] == []


def test_extract_claim_rows_accepts_nested_work_ledger_payloads() -> None:
    payload = {
        "contention_envelope": {
            "owner_sessions": [
                {
                    "claims": [
                        _claim("microcosm-substrate/README.md"),
                        {"path": "", "status": "claimed"},
                    ]
                }
            ]
        }
    }

    rows = extract_claim_rows(payload)

    assert [row["path"] for row in rows] == ["microcosm-substrate/README.md"]


def test_cli_check_returns_nonzero_for_blocked_packet(
    tmp_path, capsys
) -> None:
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(
        json.dumps({"claims": [_claim("microcosm-substrate/README.md")]}),
        encoding="utf-8",
    )

    code = main(
        [
            "--declared-path",
            "microcosm-substrate/README.md",
            "--claims-json",
            str(claims_path),
            "--requester-session-id",
            "codex_requester",
            "--check",
        ]
    )

    assert code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == BLOCKED
    assert output["coordination_request_count"] == 1
    assert "session-yield-request" in output["coordination_requests"][0]["command"]
    assert "microcosm-substrate/AGENTS.md" in output["missing_companion_paths"]
