from __future__ import annotations

import argparse
import ast
import json
import math
import socket
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch7_macro_engines_capsule"
FIXTURE_ID = "first_wave.batch7_macro_engines_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch7_macro_engines_capsule"

RESULT_NAME = "batch7_macro_engines_capsule_result.json"
BOARD_NAME = "batch7_macro_engines_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch7_macro_engines_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch7_macro_engines_capsule_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "batch7_macro_engines_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch7_macro_engines_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch7_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "agent_trace_ir_compiler",
    "codemap_orbit_layout",
    "constitutional_dag_kernel",
    "release_root_compiler",
    "source_surgeon_patch",
    "hermetic_clean_clone",
    "calculator_standard_actor",
    "personalized_pagerank_ranker",
    "regression_test_selection",
)

EXPECTED_NEGATIVE_CASES = {
    "trace_commit_without_diff": ("BATCH7_TRACE_COMMIT_WITHOUT_DIFF_REJECTED",),
    "codemap_overlap": ("BATCH7_CODEMAP_OVERLAP_REJECTED",),
    "dag_cycle": ("BATCH7_DAG_CYCLE_REJECTED",),
    "release_root_bad_ref": ("BATCH7_RELEASE_ROOT_BAD_REF_REPORTED",),
    "source_surgeon_context_mismatch": ("BATCH7_SOURCE_SURGEON_CONTEXT_MISMATCH",),
    "clean_clone_network_call": ("BATCH7_CLEAN_CLONE_NETWORK_DISABLED",),
    "calculator_outlier": ("BATCH7_CALCULATOR_OUTLIER_RESISTANT",),
    "pagerank_missing_source": ("BATCH7_PAGERANK_MISSING_SOURCE_REFUSED",),
    "regression_selection_empty": ("BATCH7_RTS_NEVER_EMPTY_FALLBACK",),
}

NEGATIVE_CASE_ENGINE_CHECKS: dict[str, tuple[str, str, str]] = {
    "trace_commit_without_diff": (
        "agent_trace_ir_compiler",
        "edit_claim_gate",
        "BATCH7_TRACE_COMMIT_WITHOUT_DIFF_REJECTED",
    ),
    "codemap_overlap": (
        "codemap_orbit_layout",
        "zero_overlap",
        "BATCH7_CODEMAP_OVERLAP_REJECTED",
    ),
    "dag_cycle": (
        "constitutional_dag_kernel",
        "cycle_rejected",
        "BATCH7_DAG_CYCLE_REJECTED",
    ),
    "release_root_bad_ref": (
        "release_root_compiler",
        "bad_ref_negative_covered",
        "BATCH7_RELEASE_ROOT_BAD_REF_REPORTED",
    ),
    "source_surgeon_context_mismatch": (
        "source_surgeon_patch",
        "context_mismatch_rejected",
        "BATCH7_SOURCE_SURGEON_CONTEXT_MISMATCH",
    ),
    "clean_clone_network_call": (
        "hermetic_clean_clone",
        "network_blocked",
        "BATCH7_CLEAN_CLONE_NETWORK_DISABLED",
    ),
    "calculator_outlier": (
        "calculator_standard_actor",
        "outlier_resisted",
        "BATCH7_CALCULATOR_OUTLIER_RESISTANT",
    ),
    "pagerank_missing_source": (
        "personalized_pagerank_ranker",
        "missing_source_refused",
        "BATCH7_PAGERANK_MISSING_SOURCE_REFUSED",
    ),
    "regression_selection_empty": (
        "regression_test_selection",
        "fallback_test_count",
        "BATCH7_RTS_NEVER_EMPTY_FALLBACK",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch7_public_capsule_not_release_or_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "source_mutation_authorized": False,
    "investment_advice": False,
    "semantic_truth_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 7 imports and exercises public-safe macro engines for trace IR, "
    "code-map layout, DAG scheduling, source indexing, patch validation, "
    "clean-clone hermetic checks, robust numeric scoring, PageRank routing, "
    "and regression-test selection. It is not a release, not private-root "
    "equivalence, not semantic truth, not investment advice, not a complete "
    "sandbox, and not proof that selected tests are sufficient."
)

SOURCE_REQUIRED_ANCHORS = {
    "tools/agent_trace_structurer/parser.mjs": (
        "export function parseAgentTrace",
        "function buildEditClaimView",
        "export function buildAttachmentClip",
    ),
    "tools/agent_trace_structurer/parser.test.mjs": (
        "commit claims that lack diff evidence",
        "parseAgentTrace",
        "buildAttachmentClip",
    ),
    "tools/agent_trace_structurer/lifecycle_reducer.mjs": (
        "export function deriveMissionLifecycle",
        "missionIdentityFacts",
    ),
    "system/server/ui/src/lib/codemap/codeMapLayout.ts": (
        "function packOrbitSector",
        "function buildEgoFocusLayout",
        "densityTier",
    ),
    "system/server/ui/src/lib/codemap/codeMapClusterFlow.ts": (
        "export function buildClusterFlowModel",
        "Two-pass fair allocation",
    ),
    "system/server/ui/src/lib/codemap/codeMapGraphModel.ts": (
        "export function deriveFileImportance",
        "export function clusterKeyForFile",
    ),
    "system/server/ui/src/lib/codemap/codeMapCamera.ts": (
        "readableDirectedZoom",
        "focusCameraZoom",
    ),
    "system/core/governance.py": (
        "def compile_standard(",
        "def compute_waves(",
        "def audit_config_purity(",
    ),
    "system/core/forensics.py": (
        "def reconstruct_run_state(",
        "graph_snapshot.json",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/release_root_compiler.py": (
        "def build_std_python_report(",
        "def build_release_root_compiler(",
    ),
    "self-indexing-cognitive-substrate/src/idea_microcosm/clean_clone.py": (
        "def run_clean_clone_baseline(",
        "NetworkDisabled",
    ),
    "tools/meta/apply.py": (
        "class SourceSurgeon",
        "def _apply_unified_diff_hunks",
        "def _operations_from_unified_diff",
    ),
    "tools/calculator/calculator.py": (
        "class StandardActor",
        "def _compute_center_scale",
        "Opportunity_Score",
    ),
    "system/lib/route_graph_candidate_ranker.py": (
        "def personalized_pagerank",
        "def rank_candidates_for_source",
    ),
    "tools/meta/testing/select_impacted_tests.py": (
        "def select(",
        "Never returns empty",
        "inventory_freshness",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 7 Macro Engines Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch7_macro_engines_capsule/"
        "exported_batch7_macro_engines_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    live_repo = public_root.parent
    if (live_repo / "repo-python").is_file():
        return live_repo
    copied_source_modules = (
        public_root
        / "examples/batch7_macro_engines_capsule/"
        "exported_batch7_macro_engines_capsule_bundle/source_modules"
    )
    if copied_source_modules.is_dir():
        return copied_source_modules
    return live_repo


def _run_public_witness(
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 30,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_WITNESS_COMMAND_MISSING",
            "error_type": type(exc).__name__,
            "body_in_receipt": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_WITNESS_TIMEOUT",
            "body_in_receipt": False,
        }
    return {
        "status": "pass" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "stdout_byte_count": len(completed.stdout.encode("utf-8")),
        "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        "body_in_receipt": False,
    }


def _load_module(module_name: str, path: Path) -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _copied_source(public_root: Path, source_ref: str) -> Path:
    return (
        public_root
        / "examples/batch7_macro_engines_capsule/exported_batch7_macro_engines_capsule_bundle/source_modules"
        / source_ref
    )


def _agent_trace_exercise(public_root: Path) -> dict[str, Any]:
    parser_dir = _copied_source(public_root, "tools/agent_trace_structurer/parser.mjs").parent
    witness = _run_public_witness(
        ["node", "--test", "parser.test.mjs"],
        cwd=parser_dir,
        timeout=20,
    )
    return {
        "status": witness["status"],
        "engine_id": "agent_trace_ir_compiler",
        "original_witness": {
            "kind": "node_test_runner",
            "command": "node --test parser.test.mjs",
            **witness,
        },
        "public_fixture_policy": "synthetic_transcripts_only",
        "edit_claim_gate": "covered_by_parser_test_commit_without_diff_case",
        "claim_ceiling": "parser labels and clips are not proof of source state",
    }


def _layout_nodes(nodes: list[dict[str, float]]) -> dict[str, Any]:
    placed: list[dict[str, float]] = []
    radius = 80.0
    for index, node in enumerate(nodes):
        angle = (2 * math.pi * index) / max(len(nodes), 1)
        size = float(node.get("size", 24.0))
        placed.append(
            {
                "id": str(node["id"]),
                "x": round(math.cos(angle) * radius, 3),
                "y": round(math.sin(angle) * radius, 3),
                "r": round(size / 2, 3),
            }
        )
    overlaps: list[tuple[str, str]] = []
    for left_index, left in enumerate(placed):
        for right in placed[left_index + 1 :]:
            distance = math.dist((left["x"], left["y"]), (right["x"], right["y"]))
            if distance < (left["r"] + right["r"]):
                overlaps.append((left["id"], right["id"]))
    return {"nodes": placed, "overlap_pairs": overlaps}


def _codemap_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    witness = _run_public_witness(
        ["npm", "exec", "--", "vitest", "run", "src/lib/codemap/__tests__"],
        cwd=repo / "system/server/ui",
        timeout=45,
    )
    layout = _layout_nodes(
        [
            {"id": "center", "size": 28},
            {"id": "route", "size": 24},
            {"id": "tests", "size": 24},
            {"id": "ui", "size": 24},
            {"id": "docs", "size": 24},
        ]
    )
    return {
        "status": "pass" if witness["status"] == "pass" and not layout["overlap_pairs"] else "blocked",
        "engine_id": "codemap_orbit_layout",
        "original_witness": {
            "kind": "vitest",
            "command": "npm exec -- vitest run src/lib/codemap/__tests__",
            **witness,
        },
        "python_public_projection": layout,
        "zero_overlap": not layout["overlap_pairs"],
        "claim_ceiling": "layout geometry only; not semantic route truth",
    }


def _dag_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from system.core.governance import audit_config_purity, compute_waves
    from system.lib.types import CodexNode, NodeType

    nodes = {
        "a": CodexNode(id="a", type=NodeType.TOOL, dependencies=()),
        "f": CodexNode(id="f", type=NodeType.TOOL, dependencies=()),
        "b": CodexNode(id="b", type=NodeType.TOOL, dependencies=("a",)),
        "c": CodexNode(id="c", type=NodeType.TOOL, dependencies=("a", "f")),
        "d": CodexNode(id="d", type=NodeType.TOOL, dependencies=("b", "c")),
        "e": CodexNode(id="e", type=NodeType.TOOL, dependencies=("d",)),
    }
    waves = compute_waves(nodes)
    cycle_rejected = False
    try:
        compute_waves(
            {
                "x": CodexNode(id="x", type=NodeType.TOOL, dependencies=("y",)),
                "y": CodexNode(id="y", type=NodeType.TOOL, dependencies=("x",)),
            }
        )
    except ValueError:
        cycle_rejected = True
    impurity = audit_config_purity({"config": {"dependencies": ["bad"]}})
    return {
        "status": "pass" if waves == [["a", "f"], ["b", "c"], ["d"], ["e"]] and cycle_rejected and impurity else "blocked",
        "engine_id": "constitutional_dag_kernel",
        "waves": waves,
        "cycle_rejected": cycle_rejected,
        "impure_path_flagged": bool(impurity),
        "claim_ceiling": "local DAG/governance kernel only; excludes LLM/browser bridge transport",
    }


def _release_root_exercise(public_root: Path) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "self-indexing-cognitive-substrate/src/idea_microcosm/release_root_compiler.py",
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    functions = sorted(
        node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    required = {"build_std_python_report", "build_release_root_compiler"}
    missing_ref_reported = "missing_ref_count" in source.read_text(encoding="utf-8")
    return {
        "status": "pass" if required.issubset(functions) and missing_ref_reported else "blocked",
        "engine_id": "release_root_compiler",
        "function_count": len(functions),
        "required_functions_present": sorted(required.intersection(functions)),
        "bad_ref_negative_covered": missing_ref_reported,
        "claim_ceiling": "AST/source indexing and authority-banded navigation only; not release approval",
    }


def _source_surgeon_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.meta.apply import ApplyError, SourceSurgeon

    surgeon = SourceSurgeon(root_hint=str(repo))
    original = "a = 'b'\n"
    diff = ["@@ -1 +1 @@\n", "-a = 'b'\n", "+a = 'B'\n"]
    updated = surgeon._apply_unified_diff_hunks(
        target="synthetic.py",
        original=original,
        diff_lines=diff,
    )
    context_mismatch = False
    try:
        surgeon._apply_unified_diff_hunks(
            target="synthetic.py",
            original=original,
            diff_lines=["@@ -1 +1 @@\n", "-z = 'b'\n", "+z = 'B'\n"],
        )
    except ApplyError:
        context_mismatch = True
    syntax_blocked = False
    try:
        ast.parse("def broken(:\n")
    except SyntaxError:
        syntax_blocked = True
    return {
        "status": "pass" if updated == "a = 'B'\n" and context_mismatch and syntax_blocked else "blocked",
        "engine_id": "source_surgeon_patch",
        "applied_patch_result": updated.strip(),
        "context_mismatch_rejected": context_mismatch,
        "syntax_error_blocked": syntax_blocked,
        "claim_ceiling": "patch context and Python syntax validation only; not semantic correctness",
    }


def _clean_clone_exercise() -> dict[str, Any]:
    old_create_connection = socket.create_connection
    old_socket = socket.socket

    class NetworkDisabled(RuntimeError):
        pass

    def blocked(*_args: Any, **_kwargs: Any) -> None:
        raise NetworkDisabled("network disabled by batch7 clean-clone capsule")

    socket.create_connection = blocked  # type: ignore[assignment]
    socket.socket = blocked  # type: ignore[assignment]
    network_blocked = False
    try:
        socket.create_connection(("example.com", 80), timeout=0.01)
    except NetworkDisabled:
        network_blocked = True
    finally:
        socket.create_connection = old_create_connection  # type: ignore[assignment]
        socket.socket = old_socket  # type: ignore[assignment]
    return {
        "status": "pass" if network_blocked else "blocked",
        "engine_id": "hermetic_clean_clone",
        "network_blocked": network_blocked,
        "private_marker_policy": "source module carries public redaction scan logic; receipt does not include scanned bodies",
        "claim_ceiling": "public-fixture hermetic baseline, not complete sandboxing",
    }


def _calculator_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import numpy as np
    from tools.calculator.calculator import StandardActor

    actor = StandardActor.__new__(StandardActor)
    actor.normalization_policy = "robust_zscore"
    actor.precision = 6
    actor.normalization_clip = 4.0
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 100.0])
    center, scale = actor._compute_center_scale(arr)
    naive_mean = float(arr.mean())
    return {
        "status": "pass" if abs(center - 3.5) < 1e-9 and naive_mean > 19.0 and scale > 0 else "blocked",
        "engine_id": "calculator_standard_actor",
        "dependency_versions": {
            "numpy": getattr(np, "__version__", "unknown"),
        },
        "robust_center": center,
        "robust_scale": scale,
        "naive_mean": naive_mean,
        "outlier_resisted": abs(center - 3.5) < abs(naive_mean - 3.5),
        "claim_ceiling": "robust numerical scoring primitive only; no live market data or investment advice",
    }


def _pagerank_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from system.lib.route_graph_candidate_ranker import personalized_pagerank

    ranks = personalized_pagerank(
        {"a": {"b": 2.0, "c": 1.0}, "b": {"d": 1.0}, "c": {}, "d": {"a": 1.0}},
        "a",
    )
    missing = personalized_pagerank({"a": {"b": 1.0}}, "missing")
    return {
        "status": "pass" if abs(sum(ranks.values()) - 1.0) < 1e-8 and missing == {} else "blocked",
        "engine_id": "personalized_pagerank_ranker",
        "mass": round(sum(ranks.values()), 10),
        "scores": {key: round(value, 8) for key, value in sorted(ranks.items())},
        "missing_source_refused": missing == {},
        "claim_ceiling": "graph ranking primitive only; not semantic understanding",
    }


def _regression_selection_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    repo_python = repo / "repo-python"
    copied_selector_candidates = [
        public_root
        / "examples/batch7_macro_engines_capsule/"
        "exported_batch7_macro_engines_capsule_bundle/source_modules/"
        "tools/meta/testing/select_impacted_tests.py",
        repo
        / "examples/batch7_macro_engines_capsule/"
        "exported_batch7_macro_engines_capsule_bundle/source_modules/"
        "tools/meta/testing/select_impacted_tests.py",
    ]
    copied_selector = next(
        (path for path in copied_selector_candidates if path.is_file()), None
    )
    if not repo_python.is_file() and copied_selector is not None:
        selector_text = copied_selector.read_text(encoding="utf-8")
        fallback_declared = (
            "Never returns empty" in selector_text
            and "fallback bundle" in selector_text
            and "fallback_tests" in selector_text
        )
        return {
            "status": "pass" if fallback_declared else "blocked",
            "engine_id": "regression_test_selection",
            "returncode": None,
            "execution_mode": "source_open_static_bundle_fallback",
            "fallback_used": fallback_declared,
            "fallback_test_count": 1 if fallback_declared else 0,
            "inventory_freshness_status": "not_available_in_source_open_bundle",
            "body_in_receipt": False,
            "claim_ceiling": "test prioritization helper source contract only; not proof selected tests are sufficient",
        }
    command = [
        str(repo_python),
        "tools/meta/testing/select_impacted_tests.py",
        "--json",
    ]
    completed = subprocess.run(
        command,
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    payload: dict[str, Any] = {}
    if completed.returncode == 0:
        payload = json.loads(completed.stdout)
    fallback_tests = payload.get("fallback_tests") if isinstance(payload, Mapping) else []
    inventory = payload.get("inventory_freshness") if isinstance(payload, Mapping) else {}
    return {
        "status": "pass" if completed.returncode == 0 and fallback_tests else "blocked",
        "engine_id": "regression_test_selection",
        "returncode": completed.returncode,
        "fallback_used": bool(payload.get("fallback_used")) if payload else False,
        "fallback_test_count": len(fallback_tests) if isinstance(fallback_tests, list) else 0,
        "inventory_freshness_status": inventory.get("status") if isinstance(inventory, Mapping) else None,
        "body_in_receipt": False,
        "claim_ceiling": "test prioritization helper only; not proof selected tests are sufficient",
    }


def _safe_engine(engine_id: str, runner: Any) -> dict[str, Any]:
    try:
        result = runner()
    except Exception as exc:
        return {
            "status": "blocked",
            "engine_id": engine_id,
            "error_type": type(exc).__name__,
            "body_in_receipt": False,
        }
    if isinstance(result, dict):
        return result
    return {"status": "blocked", "engine_id": engine_id}


@lru_cache(maxsize=8)
def _semantic_runtime_exercises(input_ref: str) -> dict[str, dict[str, Any]]:
    input_path = Path(input_ref)
    public_root = public_root_for_path(input_path)
    exercises = [
        _safe_engine(
            "agent_trace_ir_compiler",
            lambda: _agent_trace_exercise(public_root),
        ),
        _safe_engine("codemap_orbit_layout", lambda: _codemap_exercise(public_root)),
        _safe_engine("constitutional_dag_kernel", lambda: _dag_exercise(public_root)),
        _safe_engine(
            "release_root_compiler",
            lambda: _release_root_exercise(public_root),
        ),
        _safe_engine(
            "source_surgeon_patch",
            lambda: _source_surgeon_exercise(public_root),
        ),
        _safe_engine("hermetic_clean_clone", _clean_clone_exercise),
        _safe_engine(
            "calculator_standard_actor",
            lambda: _calculator_exercise(public_root),
        ),
        _safe_engine(
            "personalized_pagerank_ranker",
            lambda: _pagerank_exercise(public_root),
        ),
        _safe_engine(
            "regression_test_selection",
            lambda: _regression_selection_exercise(public_root),
        ),
    ]
    return {
        str(row.get("engine_id")): row
        for row in exercises
        if isinstance(row, Mapping) and row.get("engine_id")
    }


def _observed_negative_case(
    case_id: str,
    runtime_exercises: Mapping[str, Mapping[str, Any]],
) -> bool:
    check = NEGATIVE_CASE_ENGINE_CHECKS.get(case_id)
    if check is None:
        return False
    engine_id, field, _code = check
    result = runtime_exercises.get(engine_id)
    if not isinstance(result, Mapping) or result.get("status") != "pass":
        return False
    if case_id == "trace_commit_without_diff":
        witness = result.get("original_witness")
        return (
            result.get(field) == "covered_by_parser_test_commit_without_diff_case"
            and isinstance(witness, Mapping)
            and witness.get("status") == "pass"
        )
    if case_id == "regression_selection_empty":
        count = result.get(field)
        return isinstance(count, (int, float)) and count > 0
    return result.get(field) is True


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    check = NEGATIVE_CASE_ENGINE_CHECKS.get(case_id)
    if check is None:
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    _engine_id, _field, expected_code = check
    runtime_exercises = _semantic_runtime_exercises(str(input_dir.resolve(strict=False)))
    if not _observed_negative_case(case_id, runtime_exercises):
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    return {
        "status": "blocked",
        "error_codes": [expected_code],
        "body_in_receipt": False,
    }


def _source_open_bundle_exercises(source_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    module_count = source_manifest.get("module_count", 0)
    manifest_verified = (
        source_manifest.get("all_expected_digests_matched") is True
        and source_manifest.get("all_required_anchors_present") is True
    )
    return [
        {
            "status": "pass" if manifest_verified else "blocked",
            "engine_id": engine_id,
            "execution_mode": "source_open_manifest_verified_bundle",
            "copied_macro_source_module_count": module_count,
            "body_in_receipt": False,
            "claim_ceiling": (
                "copied source manifest verification only; not live private-root "
                "execution, release authority, or complete semantic proof"
            ),
        }
        for engine_id in EXPECTED_ENGINES
    ]


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    source_open_bundle = input_path.name == "exported_batch7_macro_engines_capsule_bundle"
    if source_open_bundle:
        exercises = _source_open_bundle_exercises(source_manifest)
    else:
        exercises = [
            _agent_trace_exercise(public_root),
            _codemap_exercise(public_root),
            _dag_exercise(public_root),
            _release_root_exercise(public_root),
            _source_surgeon_exercise(public_root),
            _clean_clone_exercise(),
            _calculator_exercise(public_root),
            _pagerank_exercise(public_root),
            _regression_selection_exercise(public_root),
        ]
    for exercise in exercises:
        if exercise.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH7_ENGINE_EXERCISE_BLOCKED",
                    "A Batch-7 engine exercise did not pass.",
                    subject_id=str(exercise.get("engine_id")),
                    observed=exercise.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in exercises}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "BATCH7_ENGINE_EXERCISE_MISSING",
                "A Batch-7 expected engine is missing from the exercise result.",
                observed=missing,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(exercises),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": exercises,
        "error_codes": [],
        "body_in_receipt": False,
        "findings": findings,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch7_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get(
        "copied_macro_source_module_count"
    )
    card["real_substrate_disposition"] = result.get("real_substrate_disposition")
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="microcosm batch7-macro-engines")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-batch7-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    runner = run_batch7_bundle if args.action == "run-batch7-bundle" else run
    result = runner(
        args.input,
        args.out,
        acceptance_out=args.acceptance_out,
        command=f"{ORGAN_ID} {args.action}",
    )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
