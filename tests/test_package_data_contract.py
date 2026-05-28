from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import tomllib

from microcosm_core import resource_root
from microcosm_core import runtime_shell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = MICROCOSM_ROOT / "MANIFEST.in"


def test_source_distribution_manifest_keeps_public_repo_entry_surface() -> None:
    lines = set(MANIFEST.read_text(encoding="utf-8").splitlines())

    for required in (
        "include AGENTS.md",
        "include CONTRIBUTING.md",
        "include Makefile",
        "include QUICKSTART.md",
        "include SECURITY.md",
        "include bootstrap.sh",
        "graft .github/workflows",
        "graft atlas",
        "graft fixtures",
        "graft paper_modules",
        "graft scripts",
        "graft skills",
        "graft tests",
    ):
        assert required in lines

    for forbidden in (
        "prune .microcosm",
        "prune .pytest_cache",
        "prune .venv",
        "prune build",
        "prune dist",
        "prune examples/*/.microcosm",
        "prune examples/*/*/.microcosm",
        "prune microcosm-substrate",
        "global-exclude *.py[cod]",
    ):
        assert forbidden in lines


def test_package_data_contract_includes_first_screen_runtime_evidence() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]

    assert data_files["share/microcosm-substrate"] == [
        "AGENTS.md",
        "ANTI_PRINCIPLES.md",
        "AXIOMS.md",
        "CONSTITUTION.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "MANIFEST.in",
        "Makefile",
        "PRINCIPLES.md",
        "QUICKSTART.md",
        "README.md",
        "SECURITY.md",
        "bootstrap.sh",
        "pyproject.toml",
    ]
    assert data_files["share/microcosm-substrate/core"] == ["core/*.json"]
    assert data_files["share/microcosm-substrate/.github/workflows"] == [
        ".github/workflows/*.yml"
    ]
    assert data_files["share/microcosm-substrate/atlas"] == ["atlas/*.json"]
    assert data_files["share/microcosm-substrate/core/preflight_support"] == [
        "core/preflight_support/*.json"
    ]
    assert data_files["share/microcosm-substrate/paper_modules"] == [
        "paper_modules/*.md"
    ]
    assert data_files["share/microcosm-substrate/scripts"] == ["scripts/*.py"]
    assert data_files["share/microcosm-substrate/skills"] == ["skills/*.md"]
    assert data_files["share/microcosm-substrate/standards"] == ["standards/*.json"]
    assert data_files["share/microcosm-substrate/receipts/acceptance"] == [
        "receipts/acceptance/*.json",
        "receipts/acceptance/pattern_assimilation_step",
    ]
    assert data_files["share/microcosm-substrate/receipts/acceptance/first_wave"] == [
        "receipts/acceptance/first_wave/*.json"
    ]
    assert data_files["share/microcosm-substrate/receipts/runtime_shell"] == [
        "receipts/runtime_shell/*.json"
    ]
    for receipt_dir in (
        "agent_route_observability_runtime",
        "executable_doctrine_grammar",
        "mission_transaction_work_spine",
        "navigation_hologram_route_plane",
        "pattern_assimilation_step",
        "pattern_binding_contract",
        "proof_diagnostic_evidence_spine",
    ):
        assert data_files[f"share/microcosm-substrate/receipts/first_wave/{receipt_dir}"] == [
            f"receipts/first_wave/{receipt_dir}/*.json"
        ]
    for receipt_dir in (
        "corpus_readiness_mathlib_absence_gate",
        "formal_evidence_cell_anchor_resolver",
        "formal_math_lean_proof_witness",
        "formal_math_premise_retrieval",
        "formal_math_readiness_gate",
        "formal_math_verifier_trace_repair_loop",
        "lean_std_premise_index",
        "ring2_premise_retrieval_precision_recall_harness",
        "tactic_portfolio_availability_probe",
        "target_shape_tactic_routing_gate",
        "verifier_lab_execution_spine",
    ):
        assert data_files[f"share/microcosm-substrate/receipts/first_wave/{receipt_dir}"] == [
            f"receipts/first_wave/{receipt_dir}/*.json"
        ]
    assert data_files[
        "share/microcosm-substrate/receipts/first_wave/verifier_lab_kernel"
    ] == ["receipts/first_wave/verifier_lab_kernel/*.json"]
    for receipt_dir in (
        "prediction_oracle_reconciliation",
        "spatial_world_model_counterfactual_simulation_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "standards_meta_diagnostics",
    ):
        assert data_files[f"share/microcosm-substrate/receipts/first_wave/{receipt_dir}"] == [
            f"receipts/first_wave/{receipt_dir}/*.json"
        ]

    proof_loop_example_data = {
        "examples/corpus_readiness_mathlib_absence_gate/"
        "exported_corpus_readiness_bundle": [
            "examples/corpus_readiness_mathlib_absence_gate/"
            "exported_corpus_readiness_bundle/*.json"
        ],
        "examples/formal_math_readiness_gate/"
        "exported_formal_math_readiness_bundle": [
            "examples/formal_math_readiness_gate/"
            "exported_formal_math_readiness_bundle/*.json"
        ],
        "examples/lean_std_premise_index/exported_lean_std_premise_index_bundle": [
            "examples/lean_std_premise_index/"
            "exported_lean_std_premise_index_bundle/*.json"
        ],
        "examples/lean_std_premise_index/"
        "exported_lean_std_premise_index_bundle/source_modules/ring2_runs/"
        "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0": [
            "examples/lean_std_premise_index/"
            "exported_lean_std_premise_index_bundle/source_modules/ring2_runs/"
            "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/*.json"
        ],
        "examples/formal_math_premise_retrieval/"
        "exported_premise_retrieval_bundle": [
            "examples/formal_math_premise_retrieval/"
            "exported_premise_retrieval_bundle/*.json"
        ],
        "examples/ring2_premise_retrieval_precision_recall_harness/"
        "exported_ring2_precision_recall_bundle": [
            "examples/ring2_premise_retrieval_precision_recall_harness/"
            "exported_ring2_precision_recall_bundle/*.json"
        ],
        "examples/tactic_portfolio_availability_probe/"
        "exported_tactic_portfolio_availability_bundle": [
            "examples/tactic_portfolio_availability_probe/"
            "exported_tactic_portfolio_availability_bundle/*.json"
        ],
        "examples/tactic_portfolio_availability_probe/"
        "exported_tactic_portfolio_availability_bundle/source_artifacts/"
        "tactic_affordance_probe": [
            "examples/tactic_portfolio_availability_probe/"
            "exported_tactic_portfolio_availability_bundle/source_artifacts/"
            "tactic_affordance_probe/*.lean"
        ],
        "examples/tactic_portfolio_availability_probe/"
        "exported_tactic_portfolio_availability_bundle/source_artifacts/"
        "tactic_affordance_probe/portfolio_core_v0": [
            "examples/tactic_portfolio_availability_probe/"
            "exported_tactic_portfolio_availability_bundle/source_artifacts/"
            "tactic_affordance_probe/portfolio_core_v0/*.lean"
        ],
        "examples/target_shape_tactic_routing_gate/"
        "exported_target_shape_tactic_routing_bundle": [
            "examples/target_shape_tactic_routing_gate/"
            "exported_target_shape_tactic_routing_bundle/*.json"
        ],
        "examples/formal_math_verifier_trace_repair_loop/"
        "exported_verifier_trace_repair_bundle": [
            "examples/formal_math_verifier_trace_repair_loop/"
            "exported_verifier_trace_repair_bundle/*.json"
        ],
        "examples/formal_math_verifier_trace_repair_loop/"
        "exported_verifier_trace_repair_bundle/source_modules/ring2_runs/"
        "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0": [
            "examples/formal_math_verifier_trace_repair_loop/"
            "exported_verifier_trace_repair_bundle/source_modules/ring2_runs/"
            "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/*.json"
        ],
        "examples/formal_math_verifier_trace_repair_loop/"
        "exported_verifier_trace_repair_bundle/source_modules/ring2_runs/"
        "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0": [
            "examples/formal_math_verifier_trace_repair_loop/"
            "exported_verifier_trace_repair_bundle/source_modules/ring2_runs/"
            "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "premise_retrieval_graph_v0/*.json"
        ],
        "examples/formal_math_verifier_trace_repair_loop/"
        "exported_verifier_trace_repair_bundle/source_modules/ring2_runs/"
        "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "oracle_repair_graph_v0": [
            "examples/formal_math_verifier_trace_repair_loop/"
            "exported_verifier_trace_repair_bundle/source_modules/ring2_runs/"
            "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "oracle_repair_graph_v0/*.json"
        ],
        "examples/formal_evidence_cell_anchor_resolver/"
        "exported_evidence_cell_anchor_bundle": [
            "examples/formal_evidence_cell_anchor_resolver/"
            "exported_evidence_cell_anchor_bundle/*.json"
        ],
        "examples/formal_evidence_cell_anchor_resolver/"
        "exported_evidence_cell_anchor_bundle/source_modules/codex/standards": [
            "examples/formal_evidence_cell_anchor_resolver/"
            "exported_evidence_cell_anchor_bundle/source_modules/codex/standards/*.json"
        ],
        "examples/formal_evidence_cell_anchor_resolver/"
        "exported_evidence_cell_anchor_bundle/source_modules/state_sidecars/"
        "formal_math_research_operations": [
            "examples/formal_evidence_cell_anchor_resolver/"
            "exported_evidence_cell_anchor_bundle/source_modules/state_sidecars/"
            "formal_math_research_operations/*.json"
        ],
        "examples/formal_evidence_cell_anchor_resolver/"
        "exported_evidence_cell_anchor_bundle/source_modules/system/lib": [
            "examples/formal_evidence_cell_anchor_resolver/"
            "exported_evidence_cell_anchor_bundle/source_modules/system/lib/*.py"
        ],
        "examples/formal_math_lean_proof_witness/"
        "exported_lean_proof_witness_bundle": [
            "examples/formal_math_lean_proof_witness/"
            "exported_lean_proof_witness_bundle/*.json"
        ],
        "examples/formal_math_lean_proof_witness/"
        "exported_lean_proof_witness_bundle/lake_project": [
            "examples/formal_math_lean_proof_witness/"
            "exported_lean_proof_witness_bundle/lake_project/*.lean"
        ],
        "examples/formal_math_lean_proof_witness/"
        "exported_lean_proof_witness_bundle/lake_project/MicrocosmProofWitness": [
            "examples/formal_math_lean_proof_witness/"
            "exported_lean_proof_witness_bundle/lake_project/"
            "MicrocosmProofWitness/*.lean"
        ],
    }
    for rel, patterns in proof_loop_example_data.items():
        assert data_files[f"share/microcosm-substrate/{rel}"] == patterns

    public_registry_lens_example_data = {
        "examples/prediction_oracle_reconciliation/"
        "exported_prediction_oracle_bundle": [
            "examples/prediction_oracle_reconciliation/"
            "exported_prediction_oracle_bundle/*.json"
        ],
        "examples/prediction_oracle_reconciliation/"
        "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
        "codex/substrate/contracts": [
            "examples/prediction_oracle_reconciliation/"
            "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
            "codex/substrate/contracts/*.json"
        ],
        "examples/prediction_oracle_reconciliation/"
        "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
        "codex/substrate/nodes/lab": [
            "examples/prediction_oracle_reconciliation/"
            "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
            "codex/substrate/nodes/lab/*.json"
        ],
        "examples/prediction_oracle_reconciliation/"
        "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
        "codex/substrate/nodes/oracle": [
            "examples/prediction_oracle_reconciliation/"
            "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
            "codex/substrate/nodes/oracle/*.json"
        ],
        "examples/prediction_oracle_reconciliation/"
        "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
        "tools/oracle": [
            "examples/prediction_oracle_reconciliation/"
            "exported_prediction_oracle_bundle/source_artifacts/macro_source/"
            "tools/oracle/*.py"
        ],
        "examples/prediction_oracle_reconciliation/"
        "exported_prediction_oracle_bundle/source_artifacts/macro_state/"
        "microcosm_portfolio": [
            "examples/prediction_oracle_reconciliation/"
            "exported_prediction_oracle_bundle/source_artifacts/macro_state/"
            "microcosm_portfolio/*.json"
        ],
        "examples/prediction_oracle_reconciliation/"
        "exported_prediction_oracle_bundle/source_artifacts/macro_state/"
        "microcosm_portfolio/extracted_patterns_ledger": [
            "examples/prediction_oracle_reconciliation/"
            "exported_prediction_oracle_bundle/source_artifacts/macro_state/"
            "microcosm_portfolio/extracted_patterns_ledger/*.json"
        ],
        "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle": [
            "examples/spatial_world_model_counterfactual_simulation_replay/"
            "exported_spatial_world_model_simulation_bundle/*.json"
        ],
        "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle/source_modules/system/"
        "server/tests": [
            "examples/spatial_world_model_counterfactual_simulation_replay/"
            "exported_spatial_world_model_simulation_bundle/source_modules/system/"
            "server/tests/*.py"
        ],
        "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle/source_modules/system/"
        "server/ui": [
            "examples/spatial_world_model_counterfactual_simulation_replay/"
            "exported_spatial_world_model_simulation_bundle/source_modules/system/"
            "server/ui/*.json"
        ],
        "examples/spatial_world_model_counterfactual_simulation_replay/"
        "exported_spatial_world_model_simulation_bundle/source_modules/tools/meta/"
        "factory": [
            "examples/spatial_world_model_counterfactual_simulation_replay/"
            "exported_spatial_world_model_simulation_bundle/source_modules/tools/meta/"
            "factory/*.py"
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/*.json"
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle/source_modules/codex/nodes/oracle": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/codex/nodes/oracle/"
            "*.json"
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle/source_modules/codex/standards": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/codex/standards/*.json"
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle/source_modules/codex/substrate/nodes/"
        "oracle": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/codex/substrate/nodes/"
            "oracle/*.json"
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle/source_modules/macro_state/"
        "microcosm_portfolio": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/macro_state/"
            "microcosm_portfolio/*.jsonl"
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle/source_modules/macro_state/"
        "microcosm_portfolio/reconstruction": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/macro_state/"
            "microcosm_portfolio/reconstruction/*.json",
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/macro_state/"
            "microcosm_portfolio/reconstruction/*.py",
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle/source_modules/system/lib": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/system/lib/*.py"
        ],
        "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle/source_modules/tools/meta/control": [
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle/source_modules/tools/meta/control/*.py"
        ],
        "examples/standards_meta_diagnostics/"
        "exported_standards_meta_diagnostics_bundle": [
            "examples/standards_meta_diagnostics/"
            "exported_standards_meta_diagnostics_bundle/*.json"
        ],
        "examples/standards_meta_diagnostics/"
        "exported_standards_meta_diagnostics_bundle/source_modules/"
        "self-indexing-cognitive-substrate/microcosms/"
        "meta_diagnostics_workbench": [
            "examples/standards_meta_diagnostics/"
            "exported_standards_meta_diagnostics_bundle/source_modules/"
            "self-indexing-cognitive-substrate/microcosms/"
            "meta_diagnostics_workbench/*.json"
        ],
        "examples/standards_meta_diagnostics/"
        "exported_standards_meta_diagnostics_bundle/source_modules/"
        "self-indexing-cognitive-substrate/src/idea_microcosm": [
            "examples/standards_meta_diagnostics/"
            "exported_standards_meta_diagnostics_bundle/source_modules/"
            "self-indexing-cognitive-substrate/src/idea_microcosm/*.py"
        ],
        "examples/standards_meta_diagnostics/"
        "exported_standards_meta_diagnostics_bundle/source_modules/"
        "self-indexing-cognitive-substrate/tests": [
            "examples/standards_meta_diagnostics/"
            "exported_standards_meta_diagnostics_bundle/source_modules/"
            "self-indexing-cognitive-substrate/tests/*.py"
        ],
    }
    for rel, patterns in public_registry_lens_example_data.items():
        assert data_files[f"share/microcosm-substrate/{rel}"] == patterns

    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_kernel/"
        "exported_verifier_lab_kernel_bundle"
    ] == ["examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/*.json"]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_kernel/"
        "exported_verifier_lab_kernel_bundle/source_modules/microcosm_core/organs"
    ] == [
        "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/"
        "source_modules/microcosm_core/organs/*.py"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/*.json"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project/*.lean"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project/"
        "MicrocosmProofWitness"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project/"
        "MicrocosmProofWitness/*.lean"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/source_modules/"
        "microcosm_core/organs"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/source_modules/"
        "microcosm_core/organs/*.py"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/public_reveal_walkthrough/"
        "exported_public_reveal_bundle"
    ] == [
        "examples/public_reveal_walkthrough/exported_public_reveal_bundle/*.json"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle"
    ] == [
        "examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/*.json",
        "examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/*.jsonl",
    ]
    assert data_files[
        "share/microcosm-substrate/examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/source_modules/system/lib"
    ] == [
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules/system/lib/*.py"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/source_modules/tools/meta/observability"
    ] == [
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules/tools/meta/observability/*.py"
    ]


def test_installed_proof_lab_cache_freshness_ignores_install_mtimes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    venv = tmp_path / "venv"
    installed_root = venv / "share/microcosm-substrate"
    receipt_path = installed_root / runtime_shell.PROOF_LAB_RECEIPT_REF
    input_root = installed_root / runtime_shell.PROOF_LAB_BUNDLE_REF
    receipt_path.parent.mkdir(parents=True)
    input_root.mkdir(parents=True)
    receipt_path.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    input_file = input_root / "bundle_manifest.json"
    input_file.write_text(json.dumps({"schema_version": "fixture"}), encoding="utf-8")
    os.utime(receipt_path, (1, 1))
    os.utime(input_file, (2, 2))

    monkeypatch.setattr(resource_root.sys, "prefix", str(venv))

    freshness = runtime_shell._proof_lab_cache_freshness(installed_root, receipt_path)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "packaged_public_data"
    assert freshness["tracked_input_count"] == 1
    assert freshness["stale_input_count"] == 0


def test_cli_proof_lab_defaults_follow_installed_data_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    venv = tmp_path / "venv"
    installed_root = venv / "share/microcosm-substrate"
    receipt_path = installed_root / runtime_shell.PROOF_LAB_RECEIPT_REF
    input_root = installed_root / runtime_shell.PROOF_LAB_BUNDLE_REF

    for rel in (
        "standards/std_microcosm_first_screen_composition_root.json",
        "core/organ_evidence_classes.json",
        "core/organ_registry.json",
    ):
        target = installed_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"schema_version": "fixture"}), encoding="utf-8")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    input_root.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    (input_root / "proof_lab_route.json").write_text(
        json.dumps({"route_id": "fixture"}),
        encoding="utf-8",
    )

    real_has_public_data = resource_root._has_public_data
    installed_root_resolved = installed_root.resolve(strict=False)

    def fake_has_public_data(root: Path) -> bool:
        root_resolved = Path(root).resolve(strict=False)
        if root_resolved == installed_root_resolved:
            return real_has_public_data(root)
        return False

    cli_module = importlib.import_module("microcosm_core.cli")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(resource_root.sys, "prefix", str(venv))
            patch.setattr(resource_root, "_has_public_data", fake_has_public_data)

            reloaded = importlib.reload(cli_module)

            assert reloaded.MICROCOSM_ROOT == installed_root
            assert reloaded.DEFAULT_PROOF_LAB_INPUT == input_root
            assert reloaded._canonical_proof_lab_receipt_path() == receipt_path
            freshness = reloaded._proof_lab_cache_freshness(
                str(input_root),
                receipt_path,
            )
            assert freshness["status"] == "current"
            assert freshness["input_status"] == "packaged_public_data"
            assert freshness["stale_input_count"] == 0
    finally:
        importlib.reload(cli_module)
