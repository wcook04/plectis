"""Cross-context agreement compares semantic action, not literal command text.

The operator's distribution claim: the same product semantics must hold across the
source checkout, a built wheel, and the standalone export — judged by semantic
action identity, NOT by identical command strings. A checkout legitimately runs
``PYTHONPATH=src python3 -m microcosm_core X ...``; an installed wheel runs
``plectis X ...``. These name the same action and must agree; a genuinely
different capability must still block.
"""

from __future__ import annotations

from microcosm_core.release_candidate_proof import (
    CONTEXT_IDS,
    derive_cross_context_agreement,
    derive_expectation_policy,
    semantic_action_key,
)


ORGAN = "finance_forecast_evaluation_spine"
ACTION = "finance-forecast-evaluation-spine run --input fixtures/x --out out/y"
VALIDATOR_ACTION = "finance-forecast-evaluation-spine verify --input out/y"
SRC_PREFIX = "PYTHONPATH=src python3 -m microcosm_core"


def _src(action: str) -> str:
    return f"{SRC_PREFIX} {action}"


def _installed(action: str) -> str:
    return f"plectis {action}"


def _encounter(command: str, validator: str, organ: str = ORGAN) -> dict[str, object]:
    return {
        "owner": {"organ_id": organ},
        "command": command,
        "validator_command": validator,
    }


# --- semantic_action_key -----------------------------------------------------


def test_semantic_action_key_strips_invocation_prefix() -> None:
    assert semantic_action_key(_src(ACTION)) == ACTION
    assert semantic_action_key(_installed(ACTION)) == ACTION
    # The whole point: two legitimate invocations of the same action are equal.
    assert semantic_action_key(_src(ACTION)) == semantic_action_key(_installed(ACTION))


def test_semantic_action_key_edge_cases() -> None:
    assert semantic_action_key(None) is None
    assert semantic_action_key("   ") is None
    assert semantic_action_key(123) is None
    # A bare invocation has no action.
    assert semantic_action_key("plectis") == ""
    # An unrecognized prefix is returned whole and so cannot accidentally agree.
    assert semantic_action_key("weird-tool run x") == "weird-tool run x"
    # Whitespace is normalized.
    assert semantic_action_key("plectis   tour    .") == "tour ."


# --- cross-context agreement -------------------------------------------------


def test_agreement_passes_when_only_the_invocation_prefix_differs() -> None:
    # The headline new behavior: identical command TEXT is not required where the
    # distribution context legitimately differs, as long as the action agrees.
    encounters = {
        "source_checkout": _encounter(_src(ACTION), _src(VALIDATOR_ACTION)),
        "fresh_install": _encounter(_installed(ACTION), _installed(VALIDATOR_ACTION)),
        "standalone_export": _encounter(
            _installed(ACTION), _installed(VALIDATOR_ACTION)
        ),
    }
    agreement = derive_cross_context_agreement(encounters)
    assert agreement["status"] == "pass"
    assert agreement["command_identical"] is True
    assert agreement["validator_command_identical"] is True
    # The literal command strings genuinely differed across contexts.
    assert len(set(agreement["commands"].values())) > 1


def test_agreement_blocks_when_the_capability_differs() -> None:
    # A context-specific command that produces DIVERGENT semantics must fail, even
    # with an identical owner organ_id.
    encounters = {
        "source_checkout": _encounter(_src(ACTION), _src(VALIDATOR_ACTION)),
        "fresh_install": _encounter(_installed(ACTION), _installed(VALIDATOR_ACTION)),
        "standalone_export": _encounter(
            _installed("some-other-organ run --input z"),
            _installed(VALIDATOR_ACTION),
        ),
    }
    agreement = derive_cross_context_agreement(encounters)
    assert agreement["status"] == "blocked"
    assert agreement["command_identical"] is False


def test_agreement_still_passes_on_identical_commands() -> None:
    # Backward compatibility: the prior all-source-form world still agrees.
    encounters = {
        context_id: _encounter(_src(ACTION), _src(VALIDATOR_ACTION))
        for context_id in CONTEXT_IDS
    }
    agreement = derive_cross_context_agreement(encounters)
    assert agreement["status"] == "pass"


# --- expectation policy ------------------------------------------------------


def test_committed_source_form_matches_observed_installed_form() -> None:
    # The committed demonstration is recorded in source form; an installed context
    # observes the `plectis` form. The expectation policy must still match them by
    # semantic action — source-checkout syntax is not required of an installed run.
    expectation = {
        "committed_demonstration_present": True,
        "expected_owner_organ_id": ORGAN,
        "expected_command": _src(ACTION),
        "expected_validator_command": _src(VALIDATOR_ACTION),
    }
    encounters = {
        "source_checkout": _encounter(_src(ACTION), _src(VALIDATOR_ACTION)),
        "fresh_install": _encounter(_installed(ACTION), _installed(VALIDATOR_ACTION)),
        "standalone_export": _encounter(
            _installed(ACTION), _installed(VALIDATOR_ACTION)
        ),
    }
    agreement = derive_cross_context_agreement(encounters)
    policy = derive_expectation_policy(expectation, agreement)
    assert policy["status"] == "pass"
    assert policy["checks"]["command_matches_committed_demonstration"] is True
    assert policy["checks"]["validator_matches_committed_demonstration"] is True


def test_expectation_policy_blocks_when_observed_action_diverges() -> None:
    expectation = {
        "committed_demonstration_present": True,
        "expected_owner_organ_id": ORGAN,
        "expected_command": _src(ACTION),
        "expected_validator_command": _src(VALIDATOR_ACTION),
    }
    encounters = {
        "source_checkout": _encounter(_src(ACTION), _src(VALIDATOR_ACTION)),
        "fresh_install": _encounter(_installed(ACTION), _installed(VALIDATOR_ACTION)),
        "standalone_export": _encounter(
            _installed("different-organ run"), _installed(VALIDATOR_ACTION)
        ),
    }
    agreement = derive_cross_context_agreement(encounters)
    policy = derive_expectation_policy(expectation, agreement)
    assert policy["status"] == "blocked"
    assert "command_matches_committed_demonstration" in policy["failed_checks"]
