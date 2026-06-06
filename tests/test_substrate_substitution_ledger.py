from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
from typing import Any

import microcosm_core.validators.substrate_substitution_ledger as ledger_mod
from microcosm_core.validators.substrate_substitution_ledger import (
    PASS,
    REAL_SUBSTRATE_CAPSULE,
    RETAINED_REGRESSION_VALIDATOR,
    _build_validation_context,
    _classify_rebuild_drift,
    _name_promise_axis,
    build_ledger,
    main,
    validate_ledger_payload,
    write_ledger_organ_slice,
)
from microcosm_core.schemas import read_json_strict


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = MICROCOSM_ROOT / "core/substrate_substitution_ledger.json"
LEDGER_REL = Path("core/substrate_substitution_ledger.json")
OWNER_SCOPE_AUTHORITY_REFS = {
    "microcosm-substrate/core/acceptance/first_wave_acceptance.json",
    "microcosm-substrate/core/organ_atlas.json",
    "microcosm-substrate/core/organ_evidence_classes.json",
    "microcosm-substrate/core/organ_families.json",
    "microcosm-substrate/core/organ_registry.json",
    "microcosm-substrate/core/preflight_support/organ_fixture_validator_readiness_v1.json",
    "microcosm-substrate/core/preflight_support/validator_receipt_coverage_map_v1.json",
    "microcosm-substrate/core/standards_registry.json",
    "microcosm-substrate/pyproject.toml",
}
FIXTURE_ECHO_ORGANS = {
    "agent_benchmark_integrity_anti_gaming_replay",
    "agent_monitor_redteam_falsification_replay",
    "agent_sabotage_scheming_monitor_replay",
}
PROVER_RUNNERS = {
    "tools/meta/factory/run_prover_statement_only_hammer_bandit.py",
    "tools/meta/factory/run_prover_proof_state_search_curriculum.py",
}
RUNTIME_GENERATED_JSON_BASENAMES = {
    "graph_update_candidates.json",
    "graph_variant.json",
    "premise_index.json",
    "provider_receipt_reduction_matrix.json",
    "prover_skill_atlas.json",
    "recipe_policy_metrics.json",
    "strategy_cards.json",
    "strategy_hypothesis_set.json",
}
RUNTIME_GENERATED_JSON_BACKFILLED_ORGANS = {
    "formal_math_premise_retrieval",
    "formal_math_verifier_trace_repair_loop",
    "lean_std_premise_index",
    "proof_diagnostic_evidence_spine",
    "target_shape_tactic_routing_gate",
}
RUNTIME_GENERATED_LEAN_BASENAMES = {
    "aesop.lean",
    "decide.lean",
    "grind.lean",
    "mathlib_probe.lean",
    "native_decide.lean",
    "omega.lean",
    "rfl.lean",
    "simp.lean",
    "simp_all.lean",
    "trace_state_probe.lean",
}
RUNTIME_GENERATED_LEAN_BACKFILLED_ORGANS = {
    "corpus_readiness_mathlib_absence_gate",
    "formal_math_readiness_gate",
    "tactic_portfolio_availability_probe",
}
RUNTIME_LEAN_DIAGNOSTIC_SOURCE_PREFIX = "state/lean_diagnostics/runs/"
FORMAL_EVIDENCE_CELL_STATE_SOURCE_PREFIX = "state/formal_math_research_operations/"
CONCURRENCY_MISSION_CONTROL_ORGAN = "concurrency_mission_control"
PRIVATE_MACRO_SOURCE_SENTINELS = {
    Path("state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json"),
    Path("system/server/ui/src/components/world/home/StationSurfaceAtlas.tsx"),
}
_VALIDATION_CONTEXT: dict[str, Any] | None = None


def _ledger() -> dict:
    return read_json_strict(LEDGER_PATH)


def _validation_context() -> dict[str, Any]:
    global _VALIDATION_CONTEXT
    if _VALIDATION_CONTEXT is None:
        _VALIDATION_CONTEXT = _build_validation_context(MICROCOSM_ROOT)
    return _VALIDATION_CONTEXT


def _validate_ledger_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return validate_ledger_payload(
        payload,
        public_root=MICROCOSM_ROOT,
        validation_context=_validation_context(),
    )


def _git_repo_root() -> Path | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(MICROCOSM_ROOT), "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    text = completed.stdout.strip()
    return Path(text) if text else None


def _dirty_owner_scope_refs(repo_root: Path) -> set[str]:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "status",
                "--porcelain",
                "--",
                *sorted(OWNER_SCOPE_AUTHORITY_REFS),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    refs: set[str] = set()
    for line in completed.stdout.splitlines():
        ref = line[3:].strip()
        if " -> " in ref:
            ref = ref.rsplit(" -> ", 1)[-1]
        if ref:
            refs.add(ref)
    return refs


def _actively_claimed_refs(repo_root: Path) -> set[str]:
    snapshot = repo_root / "state/work_ledger/active_claims_snapshot.json"
    if not snapshot.is_file():
        return set()
    payload = read_json_strict(snapshot)
    return {
        str(row.get("path") or "")
        for row in payload.get("active_claims", [])
        if isinstance(row, dict) and row.get("path")
    }


def _missing_private_macro_source_refs(public_root: Path) -> set[str]:
    return {
        ref.as_posix()
        for ref in PRIVATE_MACRO_SOURCE_SENTINELS
        if not (public_root / ref).is_file()
    }


def _owner_scope_requires_committed_ledger_blob(repo_root: Path) -> bool:
    claimed_dirty_refs = _dirty_owner_scope_refs(repo_root) & _actively_claimed_refs(
        repo_root
    )
    return bool(
        claimed_dirty_refs or _missing_private_macro_source_refs(MICROCOSM_ROOT)
    )


def _validate_committed_ledger_blob(repo_root: Path) -> dict:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "show",
            "HEAD:microcosm-substrate/core/substrate_substitution_ledger.json",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    validation = _validate_ledger_payload(payload)
    return {
        "validation_status": validation.get("status"),
        "issue_count": validation.get("issue_count"),
        "written_summary_status": payload.get("summary", {}).get("status"),
    }


def _row(payload: dict, organ_id: str) -> dict:
    return next(
        row
        for row in payload["organ_substrate_dispositions"]
        if row["organ_id"] == organ_id
    )


def test_substrate_substitution_ledger_is_current_and_valid(tmp_path: Path) -> None:
    repo_root = _git_repo_root()
    if repo_root is not None and _owner_scope_requires_committed_ledger_blob(repo_root):
        # Missing private macro source parents make exact digest rebuilds the
        # wrong owner-scope proof; the committed public ledger must validate.
        snapshot_validation = _validate_committed_ledger_blob(repo_root)
        assert snapshot_validation["validation_status"] == PASS
        assert snapshot_validation["issue_count"] == 0
        assert snapshot_validation["written_summary_status"] == PASS
        return
    if _missing_private_macro_source_refs(MICROCOSM_ROOT):
        # Standalone exports intentionally lack the private macro source parents
        # needed for exact digest rebuilds, so the shipped public ledger is the
        # authority surface to validate in that context.
        written = read_json_strict(MICROCOSM_ROOT / LEDGER_REL)
        validation = _validate_ledger_payload(written)
        assert validation["status"] == PASS
        assert validation["issue_count"] == 0
        assert written["summary"]["status"] == PASS
        return

    written = read_json_strict(MICROCOSM_ROOT / LEDGER_REL)
    rebuilt = build_ledger(MICROCOSM_ROOT)

    assert written == rebuilt
    validation = rebuilt["validation"]
    assert validation["status"] == PASS
    assert validation["issue_count"] == 0
    expected_accepted_count = len(written["organ_substrate_dispositions"])
    assert written["summary"]["accepted_organ_count"] == expected_accepted_count
    assert written["summary"]["disposition_counts"] == {
        REAL_SUBSTRATE_CAPSULE: expected_accepted_count - len(FIXTURE_ECHO_ORGANS),
        RETAINED_REGRESSION_VALIDATOR: len(FIXTURE_ECHO_ORGANS),
    }
    assert written["summary"]["fixture_authority_ban_status"] == PASS


def test_substrate_substitution_ledger_cli_reports_wrong_root_without_traceback(
    tmp_path: Path,
    capsys: Any,
) -> None:
    code = main(["--check", "--root", str(tmp_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["status"] == "blocked"
    assert payload["accepted_organ_count"] == 0
    assert {row["issue_id"] for row in payload["issues"]} == {
        "substrate_substitution_ledger_missing",
        "organ_registry_missing",
    }


def test_source_compute_evidence_skips_ast_for_marker_free_sources(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source_dir = tmp_path / "src/microcosm_core/organs"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "plain_capsule.py"
    source_path.write_text(
        "def run() -> dict[str, str]:\n"
        "    return {'status': 'pass'}\n",
        encoding="utf-8",
    )

    def fail_parse(_text: str) -> Any:
        raise AssertionError("marker-free sources should skip ast.parse")

    monkeypatch.setattr(ledger_mod.ast, "parse", fail_parse)
    evidence = ledger_mod._source_compute_evidence(tmp_path, "plain_capsule")
    assert evidence["source_exists"] is True
    assert evidence["compute_import_markers"] == []
    assert evidence["runtime_compute_markers"] == []


def test_fixture_echo_organs_are_retained_regression_validators() -> None:
    ledger = _ledger()

    for organ_id in FIXTURE_ECHO_ORGANS:
        row = _row(ledger, organ_id)
        assert row["disposition"] == RETAINED_REGRESSION_VALIDATOR
        assert row["fixture_role"] == "retained_regression_negative_wrapper_only"
        assert row["real_body_count"] == 0
        assert row["counts_as_real_substrate_progress"] is False


def test_verifier_lab_imports_bounded_public_prover_runners() -> None:
    row = _row(_ledger(), "verifier_lab_kernel")

    assert row["disposition"] == REAL_SUBSTRATE_CAPSULE
    assert row["real_body_count"] == 14
    assert PROVER_RUNNERS.issubset(set(row["macro_refs"]))
    for runner_ref in PROVER_RUNNERS:
        target_ref = (
            "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/"
            f"source_modules/{runner_ref}"
        )
        assert target_ref in row["microcosm_target_refs"]
        assert (MICROCOSM_ROOT / target_ref).is_file()
    assert any(
        "run_prover_statement_only_hammer_bandit.py" in command
        for command in row["public_exercise_commands"]
    )
    assert any(
        "run_prover_proof_state_search_curriculum.py" in command
        for command in row["public_exercise_commands"]
    )


def test_name_promise_axis_shows_priority_offenders_backed_by_runtime_compute() -> None:
    ledger = _ledger()
    summary = ledger["summary"]["name_promise"]
    targets = {
        row["organ_id"]: row
        for row in summary["mechanism_repair_targets"]
    }

    assert summary["policy_ref"] == "AP-15::mechanism_theater_name_promise"
    assert summary["mechanism_theater_count"] == 0
    assert targets == {}

    mechanistic = _row(ledger, "mechanistic_interpretability_circuit_attribution_replay")
    assert mechanistic["evidence_class"] == "bounded_runtime_computation"
    assert mechanistic["truth_accounting_bucket"] == "real_runtime_receipt"
    assert (
        mechanistic["name_promise"]["status"]
        == "name_promise_backed_by_runtime_compute"
    )
    assert mechanistic["name_promise"]["scheduler_target"] == (
        "maintain_runtime_compute_receipts"
    )
    assert mechanistic["name_promise"]["compute_import_markers"] == []
    assert mechanistic["name_promise"]["source_inspection_found_runtime_compute"] is True
    assert {
        "def _toy_transformer_forward",
        "gradient_scores",
        "ablation_result",
    }.issubset(set(mechanistic["name_promise"]["runtime_compute_markers"]))

    spatial = _row(ledger, "spatial_world_model_counterfactual_simulation_replay")
    assert spatial["evidence_class"] == "bounded_runtime_computation"
    assert spatial["truth_accounting_bucket"] == "real_runtime_receipt"
    assert spatial["name_promise"]["status"] == "name_promise_backed_by_runtime_compute"
    assert "def _gridworld_step" in spatial["name_promise"]["runtime_compute_markers"]

    governed = _row(ledger, "proof_derived_governed_mutation_authorization")
    assert governed["disposition"] == REAL_SUBSTRATE_CAPSULE
    assert governed["real_body_count"] > 0
    # semantic_validator is a risky evidence class, so the honest status must say
    # so. "proof" is a name-promise term but not a runtime-compute obligation, and
    # this organ's claim ceiling bounds it to "validates declared public contract
    # only" -- the validator itself is the mechanism, not theater.
    assert governed["name_promise"]["risky_evidence_class"] is True
    assert (
        governed["name_promise"]["status"]
        == "name_promise_non_runtime_obligation_in_risky_class"
    )
    assert governed["name_promise"]["scheduler_target"] == "maintain_claim_ceiling"


def test_substrate_substitution_validator_rejects_stale_name_promise_axis() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "mechanistic_interpretability_circuit_attribution_replay")
    bad["name_promise"]["status"] = "name_promise_mechanism_theater"
    bad["name_promise"]["compute_import_markers"] = []
    bad["name_promise"]["runtime_compute_markers"] = []
    bad["name_promise"]["source_inspection_found_runtime_compute"] = False
    bad["name_promise"]["scheduler_target"] = (
        "replace_cosmetic_validator_target_with_mechanism_repair"
    )
    bad["next_repair"] = (
        "mechanism repair: add small real runtime compute or rename/demote the organ"
    )
    ledger["summary"]["name_promise"]["status_counts"] = {
        "name_promise_mechanism_theater": 1
    }
    ledger["summary"]["name_promise"]["mechanism_theater_count"] = 1
    ledger["summary"]["name_promise"]["mechanism_repair_targets"] = [
        {
            "organ_id": bad["organ_id"],
            "name_promise_terms": bad["name_promise"]["name_promise_terms"],
            "scheduler_target": bad["name_promise"]["scheduler_target"],
            "next_repair": bad["next_repair"],
        }
    ]

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "name_promise_axis_stale_or_mismatched" in issue_ids
    assert "name_promise_next_repair_stale" in issue_ids
    assert "name_promise_summary_stale_or_mismatched" in issue_ids


def test_name_promise_axis_detects_structural_runtime_without_imports(
    tmp_path: Path,
) -> None:
    organ_id = "mechanistic_interpretability_circuit_attribution_replay"
    source_dir = tmp_path / "src/microcosm_core/organs"
    source_dir.mkdir(parents=True)
    (source_dir / f"{organ_id}.py").write_text(
        """
PASS = "pass"


def _toy_transformer_forward(token_ids, embeddings, layer1, layer2):
    context = [
        sum(embeddings[token_id][index] for token_id in token_ids) / len(token_ids)
        for index in range(len(embeddings[0]))
    ]
    hidden = [
        sum(context[index] * weights[index] for index in range(len(context)))
        for weights in layer1
    ]
    logits = [
        sum(hidden[index] * weights[index] for index in range(len(hidden)))
        for weights in layer2
    ]
    return {"hidden": hidden, "logits": logits}


def _toy_transformer_attribution_runtime():
    forward = _toy_transformer_forward(
        [0, 1],
        [[1.0, 0.0], [0.0, 1.0]],
        [[0.8, 0.2], [0.3, 0.7]],
        [[0.4, 0.6], [0.9, 0.1]],
    )
    gradient_scores = [
        forward["hidden"][index] * 0.5
        for index in range(len(forward["hidden"]))
    ]
    ablation_result = {
        "rows": [
            {"feature_id": f"toy_feature_{index}", "delta": score - 0.1}
            for index, score in enumerate(gradient_scores)
        ],
        "body_in_receipt": False,
    }
    return {
        "status": PASS,
        "runtime_kind": "pure_python_toy_forward_gradient_ablation",
        "forward_receipt": forward,
        "gradient_scores": gradient_scores,
        "ablation_result": ablation_result,
        "body_in_receipt": False,
    }
""".strip()
        + "\n",
        encoding="utf-8",
    )

    axis = _name_promise_axis(
        public_root=tmp_path,
        organ_id=organ_id,
        evidence_class="semantic_validator",
    )

    assert axis["status"] == "name_promise_backed_by_runtime_compute"
    assert axis["compute_import_markers"] == []
    assert axis["source_inspection_found_runtime_compute"] is True
    assert {
        "def _toy_transformer_forward",
        "forward(",
        "gradient_scores",
        "ablation_result",
    }.issubset(set(axis["runtime_compute_markers"]))


def test_name_promise_axis_rejects_shape_only_runtime_vocabulary(
    tmp_path: Path,
) -> None:
    organ_id = "mechanistic_interpretability_circuit_attribution_replay"
    source_dir = tmp_path / "src/microcosm_core/organs"
    source_dir.mkdir(parents=True)
    (source_dir / f"{organ_id}.py").write_text(
        """
EXPECTED_RECEIPT_KEYS = [
    "forward_receipt",
    "gradient_scores",
    "ablation_result",
]


def validate_receipt_shape(payload):
    return {
        "status": "pass",
        "required_keys": EXPECTED_RECEIPT_KEYS,
        "gradient_scores": [],
        "ablation_result": {},
    }
""".strip()
        + "\n",
        encoding="utf-8",
    )

    axis = _name_promise_axis(
        public_root=tmp_path,
        organ_id=organ_id,
        evidence_class="semantic_validator",
    )

    assert axis["status"] == "name_promise_mechanism_theater"
    assert axis["runtime_compute_markers"] == []
    assert axis["source_inspection_found_runtime_compute"] is False
    assert axis["scheduler_target"] == (
        "replace_cosmetic_validator_target_with_mechanism_repair"
    )


def _write_no_compute_validator_source(tmp_path: Path, organ_id: str) -> None:
    source_dir = tmp_path / "src/microcosm_core/organs"
    source_dir.mkdir(parents=True, exist_ok=True)
    # A shape validator: returns a receipt-shaped dict but has no arithmetic,
    # control flow, or runtime call, so the AST detector finds no runtime compute.
    (source_dir / f"{organ_id}.py").write_text(
        """
PASS = "pass"
EXPECTED_KEYS = ["contract", "handles"]


def validate_contract(payload):
    return {"status": PASS, "expected_keys": EXPECTED_KEYS}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_name_promise_axis_risky_class_non_runtime_term_is_not_mislabeled(
    tmp_path: Path,
) -> None:
    # "world" is a name-promise term but not a runtime-compute obligation term.
    # In a risky evidence class with no compute, the honest status must affirm the
    # risky class instead of claiming the row is "not_in_risky_evidence_class".
    organ_id = "world_model_projection_drift_control_room"
    _write_no_compute_validator_source(tmp_path, organ_id)

    axis = _name_promise_axis(
        public_root=tmp_path,
        organ_id=organ_id,
        evidence_class="semantic_validator",
    )

    assert axis["name_promise_terms"] == ["world"]
    assert axis["mechanism_theater_terms"] == []
    assert axis["risky_evidence_class"] is True
    assert axis["source_inspection_found_runtime_compute"] is False
    assert axis["status"] == "name_promise_non_runtime_obligation_in_risky_class"
    assert axis["status"] != "name_promise_not_in_risky_evidence_class"
    assert axis["scheduler_target"] == "maintain_claim_ceiling"


def test_name_promise_axis_non_risky_class_keeps_not_in_risky_label(
    tmp_path: Path,
) -> None:
    # Same name promise, but a non-risky evidence class: the older
    # "not_in_risky_evidence_class" status is now truthful and must be retained.
    organ_id = "world_model_projection_drift_control_room"
    _write_no_compute_validator_source(tmp_path, organ_id)

    axis = _name_promise_axis(
        public_root=tmp_path,
        organ_id=organ_id,
        evidence_class="external_subprocess_witness",
    )

    assert axis["risky_evidence_class"] is False
    assert axis["status"] == "name_promise_not_in_risky_evidence_class"
    assert axis["scheduler_target"] == "maintain_claim_ceiling"


def test_name_promise_status_never_contradicts_risky_evidence_class() -> None:
    # AP-17 (projection-as-source): a status label must not contradict its own
    # adjacent fields. "not_in_risky_evidence_class" may only appear when the
    # evidence class is genuinely not risky, and the in-risky-class status may
    # only appear when it is.
    ledger = _ledger()
    for row in ledger["organ_substrate_dispositions"]:
        axis = row.get("name_promise") or {}
        status = axis.get("status")
        risky = axis.get("risky_evidence_class")
        if status == "name_promise_not_in_risky_evidence_class":
            assert risky is False, row.get("organ_id")
        if status == "name_promise_non_runtime_obligation_in_risky_class":
            assert risky is True, row.get("organ_id")
            assert axis.get("mechanism_theater_terms") == [], row.get("organ_id")


def _minimal_writer_drift_payload() -> dict[str, Any]:
    return {
        "schema_version": "microcosm_substrate_substitution_ledger_v1",
        "ledger_id": "microcosm_substrate_substitution_ledger",
        "checker_id": "checker.microcosm.validators.substrate_substitution_ledger",
        "status": PASS,
        "summary": {
            "name_promise": {
                "schema_version": "microcosm_name_promise_summary_v1",
                "policy_ref": "AP-15::mechanism_theater_name_promise",
                "status_counts": {"name_promise_not_in_risky_evidence_class": 1},
                "mechanism_theater_count": 0,
                "mechanism_repair_targets": [],
            },
            "validation_issue_count": 0,
        },
        "organ_substrate_dispositions": [
            {
                "organ_id": "world_model_projection_drift_control_room",
                "claim_ceiling": "projection mechanics only",
                "digest_relation": [
                    {
                        "module_id": "body",
                        "expected_sha256": "sha256:old",
                        "actual_target_sha256": "sha256:old",
                        "counts_as_real_body": True,
                    }
                ],
                "name_promise": {
                    "status": "name_promise_not_in_risky_evidence_class",
                    "risky_evidence_class": False,
                },
                "next_repair": "maintain_claim_ceiling",
            }
        ],
        "validation": {"issue_count": 0},
    }


def test_writer_drift_classifier_flags_unrelated_scoped_rebuild_axes() -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    row = rebuilt["organ_substrate_dispositions"][0]
    row["name_promise"] = {
        "status": "name_promise_non_runtime_obligation_in_risky_class",
        "risky_evidence_class": True,
    }
    row["claim_ceiling"] = "projection mechanics only, not domain correctness"
    row["digest_relation"][0]["actual_target_sha256"] = "sha256:new"
    rebuilt["summary"]["name_promise"]["status_counts"] = {
        "name_promise_non_runtime_obligation_in_risky_class": 1
    }
    rebuilt["validation"]["issue_count"] = 1

    report = _classify_rebuild_drift(current, rebuilt, write_scope="name_promise")

    assert report["status"] == "blocked_unrelated_rebuild_drift"
    assert report["axis_counts"]["name_promise"] >= 1
    assert report["axis_counts"]["claim_ceiling"] == 1
    assert report["axis_counts"]["digest_relation"] == 1
    assert report["axis_counts"]["validation"] == 1
    assert set(report["unrelated_axes"]) >= {
        "claim_ceiling",
        "digest_relation",
        "validation",
    }
    assert any("/claim_ceiling" in path for path in report["sample_paths"])


def test_write_ledger_blocks_scoped_unrelated_rebuild_drift_before_write(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    rebuilt["organ_substrate_dispositions"][0]["claim_ceiling"] = (
        "projection mechanics only, not domain correctness"
    )
    rebuilt["organ_substrate_dispositions"][0]["name_promise"]["status"] = (
        "name_promise_non_runtime_obligation_in_risky_class"
    )
    root = tmp_path / "microcosm-substrate"
    (root / LEDGER_REL.parent).mkdir(parents=True)
    (root / LEDGER_REL).write_text(
        json.dumps(current, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    writes: list[tuple[Path, dict[str, Any]]] = []
    monkeypatch.setattr(ledger_mod, "build_ledger", lambda _root: rebuilt)
    monkeypatch.setattr(
        ledger_mod,
        "write_json_atomic",
        lambda path, payload: writes.append((Path(path), payload)),
    )

    result = ledger_mod.write_ledger(
        root,
        write_scope="name_promise",
        confirm_rebuild_drift=True,
    )

    assert result["status"] == "blocked_unrelated_rebuild_drift"
    assert result["write_performed"] is False
    assert result["writer_drift"]["unrelated_axes"] == ["claim_ceiling"]
    assert result["settlement_receipt"]["status"] == "blocked_pending_drift_settlement"
    assert result["settlement_receipt"]["write_performed"] is False
    assert writes == []


def test_drift_settlement_receipt_keeps_axes_reviewable_before_write() -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    row = rebuilt["organ_substrate_dispositions"][0]
    row["claim_ceiling"] = "projection mechanics only, not domain correctness"
    row["digest_relation"][0]["source_to_target_relation"] = "exact_copy"
    row["digest_relation"][0]["counts_as_real_body"] = False
    row["next_repair"] = "review claim ceiling before digest refresh"

    receipt = ledger_mod._settlement_receipt_from_payloads(
        current,
        rebuilt,
        write_scope="full",
    )

    assert receipt["status"] == "blocked_pending_drift_settlement"
    assert receipt["status_basis"] == {
        "status": "blocked_pending_drift_settlement",
        "decision_rule": "blocked_bucket_counts_nonempty",
        "changed_path_count": receipt["changed_path_count"],
        "blocking_bucket_count": 4,
        "blocking_change_count": 4,
        "settlement_owner_blocking_change_count": 3,
        "non_settlement_axis_blocking_change_count": 1,
        "evidence_fields": [
            "changed_path_count",
            "blocked_bucket_counts",
            "claim_ceiling_verdict_counts",
            "digest_relation_verdict_counts",
            "non_settlement_axis_counts",
        ],
    }
    assert receipt["mutation_plan"] == "no_generated_ledger_write"
    assert receipt["mutation_intent"] == "no_generated_ledger_write"
    assert receipt["write_performed"] is False
    assert receipt["settlement_item_id"].startswith(
        "substrate_substitution_drift_settlement:"
    )
    assert receipt["authority_posture"] == "settlement_receipt_not_source_authority"
    assert receipt["allowed_axes"] == "all"
    assert receipt["current_ledger_sha256"].startswith("sha256:")
    assert receipt["rebuilt_ledger_sha256"].startswith("sha256:")
    assert receipt["drift_report_hash_or_ref"].startswith("sha256:")
    assert receipt["expected_path_set_hash"].startswith("sha256:")
    assert receipt["claim_ceiling_verdict_counts"] == {
        "claim_ceiling_stale_projection": 1
    }
    assert receipt["claim_ceiling_verdicts"][0]["review_required"] is True
    assert receipt["claim_ceiling_verdicts"][0]["claim_ceiling_source"] == (
        "core/organ_registry.json"
    )
    assert receipt["digest_relation_bucket_counts"]["relation_reclassification"] == 1
    assert receipt["digest_relation_bucket_counts"][
        "body_count_disposition_change"
    ] == 1
    assert receipt["non_settlement_axis_counts"]["name_promise"] == 1
    assert receipt["blocked_bucket_counts"]["claim_ceiling_stale_projection"] == 1
    assert receipt["blocked_bucket_counts"]["relation_reclassification"] == 1
    assert receipt["blocked_bucket_counts"]["body_count_disposition_change"] == 1
    assert receipt["blocked_bucket_counts"]["non_settlement_axis:name_promise"] == 1
    blocked_samples = receipt["blocked_settlement_samples_by_bucket"]
    assert blocked_samples["claim_ceiling_stale_projection"][0][
        "current_claim_ceiling"
    ] == "projection mechanics only"
    assert blocked_samples["relation_reclassification"][0][
        "settlement_verdict"
    ] == "relation_reclassification_requires_review"
    assert blocked_samples["body_count_disposition_change"][0]["field"] == (
        "counts_as_real_body"
    )
    assert blocked_samples["non_settlement_axis:name_promise"][0] == {
        "organ_id": "world_model_projection_drift_control_room",
        "path": (
            "/organ_substrate_dispositions/organ_id=world_model_projection_drift_"
            "control_room/next_repair"
        ),
        "field": "next_repair",
        "axis": "name_promise",
        "current_value": "maintain_claim_ceiling",
        "rebuilt_value": "review claim ceiling before digest refresh",
        "settlement_verdict": (
            "non_settlement_axis_name_promise_requires_owner_projection"
        ),
        "review_required": True,
        "mutation_eligible_without_review": False,
        "blocking": True,
    }
    assert any(
        "/claim_ceiling" in path
        for path in receipt["sample_paths_by_bucket"]["claim_ceiling_stale_projection"]
    )


def test_settlement_report_cli_exposes_blocked_receipt(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    rebuilt["organ_substrate_dispositions"][0]["claim_ceiling"] = (
        "projection mechanics only, not domain correctness"
    )
    root = tmp_path / "microcosm-substrate"
    (root / LEDGER_REL.parent).mkdir(parents=True)
    (root / LEDGER_REL).write_text(
        json.dumps(current, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ledger_mod, "build_ledger", lambda _root: rebuilt)

    code = main(["--settlement-report", "--root", str(root)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["schema_version"] == (
        "microcosm_substrate_substitution_drift_settlement_receipt_v1"
    )
    assert payload["status"] == "blocked_pending_drift_settlement"
    assert payload["status_basis"]["decision_rule"] == "blocked_bucket_counts_nonempty"
    assert payload["status_basis"]["blocking_change_count"] == 1
    assert payload["status_basis"]["settlement_owner_blocking_change_count"] == 1
    assert payload["status_basis"]["non_settlement_axis_blocking_change_count"] == 0
    assert payload["claim_ceiling_verdict_counts"] == {
        "claim_ceiling_stale_projection": 1
    }
    assert payload["blocked_settlement_samples_by_bucket"][
        "claim_ceiling_stale_projection"
    ][0]["path"].endswith("/claim_ceiling")
    assert payload["write_performed"] is False
    assert payload["mutation_intent"] == "no_generated_ledger_write"


def test_drift_settlement_receipt_accepts_safe_narrowing_and_exact_copy_promotion() -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    current_row = current["organ_substrate_dispositions"][0]
    rebuilt_row = rebuilt["organ_substrate_dispositions"][0]
    current_row["claim_ceiling"] = "validates declared public contract only"
    rebuilt_row["claim_ceiling"] = (
        "validates only public projection metadata fixtures; does not certify "
        "runtime behavior, release, publication, private-data equivalence, or "
        "whole-system correctness"
    )
    current_digest = current_row["digest_relation"][0]
    rebuilt_digest = rebuilt_row["digest_relation"][0]
    for row in (current_digest, rebuilt_digest):
        row["source_ref"] = "system/lib/example.py"
        row["target_ref"] = "examples/example_bundle/source_modules/system/lib/example.py"
        row["source_sha256"] = "sha256:matching"
        row["expected_sha256"] = "sha256:matching"
        row["actual_target_sha256"] = "sha256:matching"
    current_digest["source_to_target_relation"] = ""
    current_digest["counts_as_real_body"] = False
    rebuilt_digest["source_to_target_relation"] = (
        "verified_exact_copy_inferred_from_matching_source_target_digest"
    )
    rebuilt_digest["counts_as_real_body"] = True
    current_row["digest_relation"].append(
        {
            "module_id": "declared_copy",
            "source_ref": "system/lib/declared.py",
            "target_ref": (
                "examples/example_bundle/source_modules/system/lib/declared.py"
            ),
            "source_to_target_relation": "exact_copy",
            "source_sha256": "sha256:declared",
            "expected_sha256": "sha256:declared",
            "actual_target_sha256": "sha256:declared",
            "counts_as_real_body": True,
            "digest_drift_disposition": (
                "pinned_historical_exact_copy_drift_not_counted_as_real_body_"
                "until_refreshed"
            ),
            "status": "blocked",
        }
    )
    rebuilt_row["digest_relation"].append(
        {
            "module_id": "declared_copy",
            "source_ref": "system/lib/declared.py",
            "target_ref": (
                "examples/example_bundle/source_modules/system/lib/declared.py"
            ),
            "source_to_target_relation": "declared_public_safe_macro_body_copy",
            "source_sha256": "sha256:declared",
            "expected_sha256": "sha256:declared",
            "actual_target_sha256": "sha256:declared",
            "counts_as_real_body": True,
            "status": PASS,
        }
    )

    receipt = ledger_mod._settlement_receipt_from_payloads(
        current,
        rebuilt,
        write_scope="full",
    )

    assert receipt["status"] == "ready_for_reviewed_generated_ledger_refresh"
    assert receipt["status_basis"]["status"] == (
        "ready_for_reviewed_generated_ledger_refresh"
    )
    assert receipt["status_basis"]["decision_rule"] == (
        "changed_paths_without_blocking_buckets"
    )
    assert receipt["status_basis"]["blocking_bucket_count"] == 0
    assert receipt["status_basis"]["blocking_change_count"] == 0
    assert receipt["blocked_bucket_counts"] == {}
    assert receipt["claim_ceiling_verdict_counts"] == {
        "claim_ceiling_safe_narrowing": 1
    }
    assert receipt["blocked_settlement_samples_by_bucket"] == {}
    assert receipt["claim_ceiling_verdicts"][0]["review_required"] is False
    assert receipt["claim_ceiling_verdicts"][0][
        "mutation_eligible_without_review"
    ] is True
    assert receipt["digest_relation_bucket_counts"] == {
        "body_count_disposition_change": 3,
        "relation_reclassification": 2,
    }
    assert receipt["digest_relation_verdict_counts"] == {
        "resolved_pinned_exact_copy_drift": 1,
        "resolved_verified_exact_copy_row_status": 1,
        "verified_exact_copy_body_count_promotion": 1,
        "verified_exact_copy_relation_promotion": 2,
    }


def test_drift_settlement_receipt_promotes_aggregate_counters_per_organ() -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    verified_current = current["organ_substrate_dispositions"][0]
    verified_rebuilt = rebuilt["organ_substrate_dispositions"][0]
    verified_current.update(
        {
            "organ_id": "verified_exact_copy_organ",
            "digest_relation_status": "blocked",
            "real_body_count": 0,
            "supporting_body_count": 0,
        }
    )
    verified_rebuilt.update(
        {
            "organ_id": "verified_exact_copy_organ",
            "digest_relation_status": PASS,
            "real_body_count": 1,
            "supporting_body_count": 1,
        }
    )
    verified_current_digest = verified_current["digest_relation"][0]
    verified_rebuilt_digest = verified_rebuilt["digest_relation"][0]
    for row in (verified_current_digest, verified_rebuilt_digest):
        row["source_ref"] = "system/lib/verified.py"
        row["target_ref"] = "examples/verified/source_modules/system/lib/verified.py"
        row["source_sha256"] = "sha256:verified"
        row["expected_sha256"] = "sha256:verified"
        row["actual_target_sha256"] = "sha256:verified"
        row["status"] = "blocked"
        row["counts_as_real_body"] = False
    verified_rebuilt_digest["source_to_target_relation"] = (
        "verified_exact_copy_inferred_from_matching_source_target_digest"
    )
    verified_rebuilt_digest["status"] = PASS
    verified_rebuilt_digest["counts_as_real_body"] = True

    blocker_current = deepcopy(verified_current)
    blocker_rebuilt = deepcopy(blocker_current)
    blocker_current["organ_id"] = "blocked_unverified_organ"
    blocker_rebuilt["organ_id"] = "blocked_unverified_organ"
    blocker_current_digest = blocker_current["digest_relation"][0]
    blocker_rebuilt_digest = blocker_rebuilt["digest_relation"][0]
    blocker_current_digest.clear()
    blocker_current_digest.update(
        {
            "module_id": "unverified",
            "counts_as_real_body": False,
        }
    )
    blocker_rebuilt_digest.clear()
    blocker_rebuilt_digest.update(
        {
            "module_id": "unverified",
            "counts_as_real_body": True,
        }
    )
    current["organ_substrate_dispositions"].append(blocker_current)
    rebuilt["organ_substrate_dispositions"].append(blocker_rebuilt)

    receipt = ledger_mod._settlement_receipt_from_payloads(
        current,
        rebuilt,
        write_scope="full",
    )

    assert receipt["status"] == "blocked_pending_drift_settlement"
    assert receipt["digest_relation_verdict_counts"][
        "derived_body_count_counter_from_verified_rows"
    ] == 3
    assert receipt["digest_relation_verdict_counts"][
        "body_count_disposition_requires_review"
    ] == 1
    assert receipt["blocked_bucket_counts"] == {"body_count_disposition_change": 1}
    blocked_rows = receipt["blocked_settlement_samples_by_bucket"][
        "body_count_disposition_change"
    ]
    assert [row["organ_id"] for row in blocked_rows] == ["blocked_unverified_organ"]


def test_write_ledger_blocks_confirmed_full_write_when_settlement_is_blocked(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    rebuilt["organ_substrate_dispositions"][0]["claim_ceiling"] = (
        "projection mechanics only, not domain correctness"
    )
    root = tmp_path / "microcosm-substrate"
    (root / LEDGER_REL.parent).mkdir(parents=True)
    (root / LEDGER_REL).write_text(
        json.dumps(current, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    writes: list[tuple[Path, dict[str, Any]]] = []
    monkeypatch.setattr(ledger_mod, "build_ledger", lambda _root: rebuilt)
    monkeypatch.setattr(
        ledger_mod,
        "write_json_atomic",
        lambda path, payload: writes.append((Path(path), payload)),
    )

    result = ledger_mod.write_ledger(
        root,
        write_scope="full",
        confirm_rebuild_drift=True,
    )

    assert result["status"] == "blocked_pending_drift_settlement"
    assert result["write_performed"] is False
    assert result["settlement_receipt"]["status"] == "blocked_pending_drift_settlement"
    assert writes == []


def test_write_ledger_organ_slice_merges_selected_row_without_broad_refresh(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    selected_row = deepcopy(current["organ_substrate_dispositions"][0])
    selected_row.update(
        {
            "organ_id": "new_source_open_capsule",
            "disposition": REAL_SUBSTRATE_CAPSULE,
            "real_body_count": 2,
            "supporting_body_count": 2,
            "receipt_body_count": 0,
            "digest_drift_disposition_count": 0,
            "name_promise": {
                "schema_version": "microcosm_name_promise_axis_v1",
                "policy_ref": "AP-15::mechanism_theater_name_promise",
                "status": "no_compute_name_promise",
                "name_promise_terms": [],
                "mechanism_theater_terms": [],
                "risky_evidence_class": False,
                "source_ref": "src/microcosm_core/organs/new_source_open_capsule.py",
                "source_exists": True,
                "compute_import_markers": [],
                "runtime_compute_markers": [],
                "source_inspection_found_runtime_compute": False,
                "scheduler_target": "maintain_current_disposition",
            },
        }
    )
    rebuilt["organ_substrate_dispositions"].append(selected_row)

    root = tmp_path / "microcosm-substrate"
    (root / LEDGER_REL.parent).mkdir(parents=True)
    (root / LEDGER_REL).write_text(
        json.dumps(current, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    writes: list[tuple[Path, dict[str, Any]]] = []
    monkeypatch.setattr(ledger_mod, "build_ledger", lambda _root: rebuilt)
    monkeypatch.setattr(
        ledger_mod,
        "_expected_accepted_ids_if_registry_exists",
        lambda _root: [
            "world_model_projection_drift_control_room",
            "new_source_open_capsule",
        ],
    )
    monkeypatch.setattr(
        ledger_mod,
        "_build_validation_context",
        lambda _root: {
            "public_root": root,
            "accepted_ids": [
                "world_model_projection_drift_control_room",
                "new_source_open_capsule",
            ],
            "source_compute_evidence_by_organ": {},
        },
    )
    monkeypatch.setattr(
        ledger_mod,
        "validate_ledger_payload",
        lambda payload, **_kwargs: {
            "schema_version": "microcosm_substrate_substitution_validation_v1",
            "checker_id": str(ledger_mod.CHECKER_ID),
            "status": PASS,
            "issue_count": 0,
            "issues": [],
            "accepted_organ_count": len(payload["organ_substrate_dispositions"]),
            "checked_row_count": len(payload["organ_substrate_dispositions"]),
            "fixture_only_authority_banned": True,
        },
    )
    monkeypatch.setattr(
        ledger_mod,
        "validate_ledger",
        lambda _root: {
            "schema_version": "microcosm_substrate_substitution_validation_v1",
            "status": PASS,
            "issue_count": 0,
            "issues": [],
        },
    )
    monkeypatch.setattr(
        ledger_mod,
        "write_json_atomic",
        lambda path, payload: writes.append((Path(path), payload)),
    )

    result = write_ledger_organ_slice(root, ["new_source_open_capsule"])

    assert result["write_result"]["status"] == PASS
    assert result["write_result"]["mutation_intent"] == "organ_slice_ledger_merge"
    assert result["write_result"]["selected_organ_ids"] == ["new_source_open_capsule"]
    assert len(writes) == 1
    written_rows = writes[0][1]["organ_substrate_dispositions"]
    assert [row["organ_id"] for row in written_rows] == [
        "world_model_projection_drift_control_room",
        "new_source_open_capsule",
    ]
    assert written_rows[0] == current["organ_substrate_dispositions"][0]
    assert written_rows[1] == selected_row
    assert writes[0][1]["summary"]["accepted_organ_count"] == 2
    assert writes[0][1]["validation"]["status"] == PASS


def test_write_ledger_records_applied_settlement_receipt(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    current = _minimal_writer_drift_payload()
    rebuilt = deepcopy(current)
    current_row = current["organ_substrate_dispositions"][0]
    rebuilt_row = rebuilt["organ_substrate_dispositions"][0]
    current_row["claim_ceiling"] = "validates declared public contract only"
    rebuilt_row["claim_ceiling"] = (
        "validates only public projection metadata fixtures; does not certify "
        "runtime behavior, release, publication, private-data equivalence, or "
        "whole-system correctness"
    )
    root = tmp_path / "microcosm-substrate"
    (root / LEDGER_REL.parent).mkdir(parents=True)
    (root / LEDGER_REL).write_text(
        json.dumps(current, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    writes: list[tuple[Path, dict[str, Any]]] = []
    monkeypatch.setattr(ledger_mod, "build_ledger", lambda _root: rebuilt)
    monkeypatch.setattr(
        ledger_mod,
        "write_json_atomic",
        lambda path, payload: writes.append((Path(path), payload)),
    )
    monkeypatch.setattr(
        ledger_mod,
        "validate_ledger",
        lambda _root: {
            "schema_version": "microcosm_substrate_substitution_validation_v1",
            "status": PASS,
            "issue_count": 0,
            "issues": [],
        },
    )

    result = ledger_mod.write_ledger(
        root,
        write_scope="full",
        confirm_rebuild_drift=True,
    )

    assert result["write_result"]["status"] == PASS
    assert result["write_result"]["write_performed"] is True
    applied = result["write_result"]["settlement_receipt"]
    assert applied["status"] == PASS
    assert applied["write_performed"] is True
    assert applied["post_write_check_status"] == PASS
    assert applied["mutation_intent"] == "reviewed_generated_ledger_refresh_applied"
    assert writes == [(root / LEDGER_REL, rebuilt)]


def test_fixture_origin_bodies_do_not_count_as_real_substrate() -> None:
    ledger = _ledger()

    formal_row = _row(ledger, "formal_math_lean_proof_witness")
    fixture_rows = [
        row
        for row in formal_row["digest_relation"]
        if str(row.get("source_ref") or "").startswith("fixtures/")
    ]
    assert fixture_rows
    assert all(row["counts_as_real_body"] is False for row in fixture_rows)
    assert all(row["source_authority_role"] == "fixture_regression_source" for row in fixture_rows)
    assert formal_row["real_body_count"] == 1
    assert any(
        row.get("counts_as_real_body") is True
        and row.get("source_ref")
        == "microcosm-substrate/src/microcosm_core/organs/formal_math_lean_proof_witness.py"
        and row.get("source_authority_role") == "public_substrate_source"
        for row in formal_row["digest_relation"]
    )

    execution_row = _row(ledger, "verifier_lab_execution_spine")
    assert execution_row["real_body_count"] == 2
    assert all(
        row["counts_as_real_body"] is False
        for row in execution_row["digest_relation"]
        if str(row.get("source_ref") or "").startswith("fixtures/")
    )


def test_generated_projection_slices_do_not_count_as_real_substrate() -> None:
    ledger = _ledger()

    row = _row(ledger, "research_replication_rubric_artifact_replay")
    projection_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if "::" in str(digest_row.get("source_ref") or "")
    ]
    assert projection_rows
    assert all(digest_row["counts_as_real_body"] is False for digest_row in projection_rows)
    assert all(
        digest_row["source_authority_role"] == "generated_projection_slice_source"
        for digest_row in projection_rows
    )
    assert row["real_body_count"] == 1
    assert any(
        digest_row.get("counts_as_real_body") is True
        and digest_row.get("source_ref")
        == "microcosm-substrate/src/microcosm_core/organs/research_replication_rubric_artifact_replay.py"
        and digest_row.get("source_authority_role") == "public_substrate_source"
        for digest_row in row["digest_relation"]
    )


def test_generated_microcosm_portfolio_sources_do_not_count_as_real_substrate() -> None:
    ledger = _ledger()

    row = _row(ledger, "pattern_binding_contract")
    generated_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if str(digest_row.get("source_ref") or "").startswith("state/microcosm_portfolio/")
    ]
    assert generated_rows
    assert all(digest_row["counts_as_real_body"] is False for digest_row in generated_rows)
    assert all(
        digest_row["source_authority_role"] == "generated_projection_source"
        for digest_row in generated_rows
        if "::" not in str(digest_row.get("source_ref") or "")
    )
    assert row["real_body_count"] == 2
    assert any(
        digest_row.get("counts_as_real_body") is True
        and digest_row.get("source_ref")
        == "tools/meta/factory/check_extracted_pattern_route_readiness.py"
        for digest_row in row["digest_relation"]
    )


def test_runtime_run_report_sources_do_not_count_as_real_substrate() -> None:
    ledger = _ledger()

    row = _row(ledger, "ring2_premise_retrieval_precision_recall_harness")
    runtime_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if str(digest_row.get("source_ref") or "").startswith("state/runs/")
    ]
    assert runtime_rows
    assert all(digest_row["counts_as_real_body"] is False for digest_row in runtime_rows)
    assert all(
        digest_row["source_authority_role"] == "runtime_receipt_source"
        for digest_row in runtime_rows
    )
    assert row["real_body_count"] == 1
    assert any(
        digest_row.get("counts_as_real_body") is True
        and digest_row.get("source_ref")
        == "tools/meta/factory/run_prover_graph_benchmark.py"
        and digest_row.get("source_authority_role") == "public_substrate_source"
        for digest_row in row["digest_relation"]
    )


def test_state_run_generated_json_sources_do_not_count_as_real_substrate() -> None:
    ledger = _ledger()
    generated_rows = []
    by_organ = {row["organ_id"]: row for row in ledger["organ_substrate_dispositions"]}
    for row in ledger["organ_substrate_dispositions"]:
        for digest_row in row["digest_relation"]:
            source_ref = str(digest_row.get("source_ref") or "")
            if (
                source_ref.startswith("state/runs/")
                and Path(source_ref).name in RUNTIME_GENERATED_JSON_BASENAMES
            ):
                generated_rows.append(digest_row)

    assert generated_rows
    assert all(digest_row["counts_as_real_body"] is False for digest_row in generated_rows)
    assert all(
        digest_row["source_authority_role"] == "runtime_generated_artifact_source"
        for digest_row in generated_rows
    )

    for organ_id in sorted(RUNTIME_GENERATED_JSON_BACKFILLED_ORGANS):
        row = by_organ[organ_id]
        assert row["disposition"] == REAL_SUBSTRATE_CAPSULE
        counted_rows = [
            digest_row
            for digest_row in row["digest_relation"]
            if digest_row.get("counts_as_real_body") is True
        ]
        assert counted_rows
        assert any(
            digest_row.get("source_ref")
            == f"src/microcosm_core/organs/{organ_id}.py"
            and digest_row.get("source_authority_role") == "public_substrate_source"
            and "source_body_floor/source_modules/microcosm_core/organs/"
            in str(digest_row.get("target_ref") or "")
            for digest_row in counted_rows
        )


def test_state_run_generated_lean_sources_do_not_count_as_real_substrate() -> None:
    ledger = _ledger()
    generated_rows = []
    by_organ = {row["organ_id"]: row for row in ledger["organ_substrate_dispositions"]}
    for row in ledger["organ_substrate_dispositions"]:
        for digest_row in row["digest_relation"]:
            source_ref = str(digest_row.get("source_ref") or "")
            if (
                source_ref.startswith("state/runs/")
                and Path(source_ref).name in RUNTIME_GENERATED_LEAN_BASENAMES
            ):
                generated_rows.append(digest_row)

    assert generated_rows
    assert all(digest_row["counts_as_real_body"] is False for digest_row in generated_rows)
    assert all(
        digest_row["source_authority_role"] == "runtime_generated_lean_artifact_source"
        for digest_row in generated_rows
    )

    for organ_id in sorted(RUNTIME_GENERATED_LEAN_BACKFILLED_ORGANS):
        row = by_organ[organ_id]
        assert row["disposition"] == REAL_SUBSTRATE_CAPSULE
        counted_rows = [
            digest_row
            for digest_row in row["digest_relation"]
            if digest_row.get("counts_as_real_body") is True
        ]
        assert counted_rows
        assert any(
            digest_row.get("source_ref")
            == f"src/microcosm_core/organs/{organ_id}.py"
            and digest_row.get("source_authority_role") == "public_substrate_source"
            and "source_body_floor/source_modules/microcosm_core/organs/"
            in str(digest_row.get("target_ref") or "")
            for digest_row in counted_rows
        )


def test_state_lean_diagnostic_sources_do_not_count_as_real_substrate() -> None:
    row = _row(_ledger(), "certificate_kernel_execution_lab")
    diagnostic_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if str(digest_row.get("source_ref") or "").startswith(
            RUNTIME_LEAN_DIAGNOSTIC_SOURCE_PREFIX
        )
    ]

    assert diagnostic_rows
    assert all(digest_row["counts_as_real_body"] is False for digest_row in diagnostic_rows)
    assert all(
        digest_row["source_authority_role"] == "runtime_lean_diagnostic_source"
        for digest_row in diagnostic_rows
    )
    assert row["disposition"] == REAL_SUBSTRATE_CAPSULE
    counted_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if digest_row.get("counts_as_real_body") is True
    ]
    assert counted_rows
    assert not any(
        str(digest_row.get("source_ref") or "").startswith(
            RUNTIME_LEAN_DIAGNOSTIC_SOURCE_PREFIX
        )
        for digest_row in counted_rows
    )
    assert any(
        str(digest_row.get("source_ref") or "").endswith(".lean")
        and str(digest_row.get("target_ref") or "").endswith(".lean")
        and digest_row.get("actual_target_sha256")
        for digest_row in counted_rows
    )


def test_formal_evidence_cell_state_sources_do_not_count_as_real_substrate() -> None:
    row = _row(_ledger(), "formal_evidence_cell_anchor_resolver")
    state_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if str(digest_row.get("source_ref") or "").startswith(
            FORMAL_EVIDENCE_CELL_STATE_SOURCE_PREFIX
        )
    ]

    assert state_rows
    assert all(digest_row["counts_as_real_body"] is False for digest_row in state_rows)
    assert all(
        digest_row["source_authority_role"] == "formal_evidence_cell_state_source"
        for digest_row in state_rows
    )
    assert row["disposition"] == REAL_SUBSTRATE_CAPSULE
    assert row["real_body_count"] == 4
    counted_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if digest_row.get("counts_as_real_body") is True
    ]
    assert not any(
        str(digest_row.get("source_ref") or "").startswith(
            FORMAL_EVIDENCE_CELL_STATE_SOURCE_PREFIX
        )
        for digest_row in counted_rows
    )
    assert any(
        digest_row.get("source_ref")
        == "tools/meta/factory/build_formal_math_evidence_cell_registry.py"
        and digest_row.get("source_authority_role") == "public_substrate_source"
        for digest_row in counted_rows
    )


def test_concurrency_seed_receipt_material_does_not_count_as_real_substrate() -> None:
    row = _row(_ledger(), CONCURRENCY_MISSION_CONTROL_ORGAN)
    seed_receipt_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if digest_row.get("source_authority_role")
        == "concurrency_mission_control_seed_receipt_source"
    ]

    assert seed_receipt_rows
    assert all(
        digest_row["counts_as_real_body"] is False
        for digest_row in seed_receipt_rows
    )
    assert all(
        digest_row["manifest_material_class"] == "public_macro_receipt_body"
        for digest_row in seed_receipt_rows
    )
    assert row["disposition"] == REAL_SUBSTRATE_CAPSULE
    assert row["real_body_count"] == 1
    counted_rows = [
        digest_row
        for digest_row in row["digest_relation"]
        if digest_row.get("counts_as_real_body") is True
    ]
    assert len(counted_rows) == 1
    assert counted_rows[0]["source_ref"].endswith(
        "concurrency_mission_control_specimen.py"
    )


def test_substrate_substitution_validator_rejects_fixture_only_authority() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "agent_benchmark_integrity_anti_gaming_replay")
    bad["disposition"] = REAL_SUBSTRATE_CAPSULE
    bad["microcosm_target_refs"] = []
    bad["public_exercise_commands"] = []
    bad["counts_as_real_substrate_progress"] = True

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "fixture_echo_not_demoted_to_regression_validator" in issue_ids
    assert "real_capsule_missing_public_exercise_command" in issue_ids


def test_substrate_substitution_validator_rejects_metadata_promoted_zero_body_capsule() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "engine_room_demo")
    bad["disposition"] = REAL_SUBSTRATE_CAPSULE
    bad["truth_accounting_bucket"] = "real_import_validation"
    bad["counts_as_real_substrate_progress"] = True
    bad["source_module_manifest_refs"] = []
    bad["macro_refs"] = []
    bad["microcosm_target_refs"] = []
    bad["digest_relation"] = []
    bad["real_body_count"] = 0
    bad["supporting_body_count"] = 0
    bad["body_support_class"] = "none_verified"

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_capsule_missing_verified_body_support" in issue_ids
    assert "real_capsule_missing_source_module_manifest" in issue_ids
    assert "real_capsule_missing_digest_relation" in issue_ids


def test_substrate_substitution_validator_rejects_disconnected_public_exercise() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "engine_room_demo")
    bad["public_exercise_commands"] = ["python -c 'pass'"]

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_capsule_public_exercise_not_connected_to_body" in issue_ids


def test_substrate_substitution_validator_rejects_real_body_count_drift() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "engine_room_demo")
    counted_rows = [
        row
        for row in bad["digest_relation"]
        if row.get("counts_as_real_body") is True
    ]
    bad["real_body_count"] = len(counted_rows) + 1
    bad["supporting_body_count"] = len(counted_rows) + 1
    bad["receipt_body_count"] = 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_capsule_real_body_count_diverges_from_digest_rows" in issue_ids
    assert "real_capsule_supporting_body_count_diverges_from_digest_rows" in issue_ids
    assert "real_capsule_receipt_body_count_diverges_from_digest_rows" in issue_ids


def test_substrate_substitution_validator_rejects_counted_body_without_digest_relation() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "engine_room_demo")
    counted_row = next(
        row
        for row in bad["digest_relation"]
        if row.get("counts_as_real_body") is True
    )
    counted_row["source_ref"] = ""
    counted_row["actual_target_sha256"] = ""
    counted_row["status"] = "blocked"
    bad["digest_relation_status"] = "blocked"

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_missing_target_digest_or_provenance" in issue_ids
    assert "real_body_digest_relation_status_not_pass" in issue_ids


def test_substrate_substitution_validator_rejects_counted_fixture_source_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "formal_math_lean_proof_witness")
    fixture_row = next(
        row
        for row in bad["digest_relation"]
        if str(row.get("source_ref") or "").startswith("fixtures/")
    )
    fixture_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_fixture_or_receipt_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_projection_slice_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "research_replication_rubric_artifact_replay")
    projection_row = next(
        row
        for row in bad["digest_relation"]
        if "::" in str(row.get("source_ref") or "")
    )
    projection_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_generated_projection_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_generated_projection_source_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "pattern_binding_contract")
    generated_row = next(
        row
        for row in bad["digest_relation"]
        if str(row.get("source_ref") or "").startswith("state/microcosm_portfolio/")
        and "::" not in str(row.get("source_ref") or "")
    )
    generated_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_generated_projection_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_runtime_receipt_source_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "ring2_premise_retrieval_precision_recall_harness")
    runtime_row = next(
        row
        for row in bad["digest_relation"]
        if str(row.get("source_ref") or "").startswith("state/runs/")
    )
    runtime_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_runtime_receipt_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_runtime_generated_json_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "lean_std_premise_index")
    generated_row = next(
        row
        for row in bad["digest_relation"]
        if str(row.get("source_ref") or "").startswith("state/runs/")
        and Path(str(row.get("source_ref") or "")).name in RUNTIME_GENERATED_JSON_BASENAMES
    )
    generated_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_runtime_generated_artifact_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_runtime_generated_lean_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "formal_math_readiness_gate")
    generated_row = next(
        row
        for row in bad["digest_relation"]
        if str(row.get("source_ref") or "").startswith("state/runs/")
        and Path(str(row.get("source_ref") or "")).name in RUNTIME_GENERATED_LEAN_BASENAMES
    )
    generated_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_runtime_generated_lean_artifact_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_runtime_lean_diagnostic_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "certificate_kernel_execution_lab")
    diagnostic_row = next(
        row
        for row in bad["digest_relation"]
        if str(row.get("source_ref") or "").startswith(
            RUNTIME_LEAN_DIAGNOSTIC_SOURCE_PREFIX
        )
    )
    diagnostic_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_runtime_lean_diagnostic_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_formal_evidence_cell_state_body() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, "formal_evidence_cell_anchor_resolver")
    state_row = next(
        row
        for row in bad["digest_relation"]
        if str(row.get("source_ref") or "").startswith(
            FORMAL_EVIDENCE_CELL_STATE_SOURCE_PREFIX
        )
    )
    state_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_formal_evidence_cell_state_source_counted_as_substrate" in issue_ids


def test_substrate_substitution_validator_rejects_counted_concurrency_seed_receipt() -> None:
    ledger = deepcopy(_ledger())
    bad = _row(ledger, CONCURRENCY_MISSION_CONTROL_ORGAN)
    seed_receipt_row = next(
        row
        for row in bad["digest_relation"]
        if row.get("source_authority_role")
        == "concurrency_mission_control_seed_receipt_source"
    )
    seed_receipt_row["counts_as_real_body"] = True
    bad["real_body_count"] += 1
    bad["supporting_body_count"] += 1

    validation = _validate_ledger_payload(ledger)

    assert validation["status"] == "blocked"
    issue_ids = {issue["issue_id"] for issue in validation["issues"]}
    assert "real_body_concurrency_seed_receipt_source_counted_as_substrate" in issue_ids
