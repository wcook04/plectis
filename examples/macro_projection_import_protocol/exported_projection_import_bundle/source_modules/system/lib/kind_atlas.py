"""
Build the rung-0 artifact-kind atlas for Russian-doll navigation.

The atlas answers "what kinds can I browse?" before the agent guesses a
keyword or a per-kind command. It is a projection, not source authority.

Rosetta routing header (std_navigation_rosetta_grammar.json::noun_shape):
  kind: python_module
  role: rung-0 kind atlas builder; emits one browse row per artifact kind
        (paper_modules, standards, task_ledger, prompt_shelf_metadata, python_files, python_scopes, frontend_views,
        frontend_components, skills, system_terms, principles, concepts, mechanisms, axiom_candidates,
        raw_seed_shards, type_a_autonomous_seeds, compression_profiles, annex_patterns,
        external_benchmark_calibration, annex_distillation_patterns) before any
        keyword query, with support_status / option_surface_command / profile_gap
        per std_kind_atlas.json.
  depends_on:
    - codex/standards/std_kind_atlas.json: governs - row contract (required_row_fields, support_status_enum, band_contracts) authoritative here.
    - codex/standards/std_navigation_rosetta_grammar.json: governs - the rung-0 atlas row IS a noun in the Rosetta grammar (noun_kind=artifact_kind).
    - codex/doctrine/paper_modules/_index.json: feeds - row_count and freshness for the paper_modules kind row.
    - codex/standards/std_python_scope_index.json: feeds - row_count metadata for python_files / python_scopes kind rows (currently support_status=projection_gap; this module is the projection that names that gap).
    - system/lib/standard_option_surface.py: routes_to - the rung-1 drilldown for kinds whose support_status=option_surface_supported.
    - system/lib/navigation_context_rosetta.py: evidences - the rung-2 representative-row Rosetta packet consumes this atlas as its kind enumeration.
  governed_by:
    - codex/standards/std_kind_atlas.json
    - codex/standards/std_navigation_rosetta_grammar.json
  code_loci:
    - build_kind_atlas: top-level constructor; takes repo_root + band, returns the deterministic atlas dict with rows + selection + summary + navigation_boundary.
    - _build_rows: enumerates every governed kind into a row_shape; THIS is the place to add a kind when a new artifact class earns rung-0 visibility.
    - _row: assembles one kind row per std_kind_atlas.json::required_row_fields.
    - _card_extra: card-band rung_support / known_next_moves / omission_receipt enrichment per std_kind_atlas.json::band_contracts.card.
    - _currentness: fills the currentness contract (status + generated_at + source_refs_checked + source_mtimes).
  evidence_command: ./repo-python kernel.py --kind-atlas --band flag
  source_authority: self for the projection shape; codex/standards/std_kind_atlas.json for the row contract.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib import prompt_ledger_events

from system.lib.navigation_surface_contracts import ATLAS_PROJECTION, ENTRY_REPLACEMENT


PAPER_MODULE_INDEX = Path("codex/doctrine/paper_modules/_index.json")
PAPER_MODULE_STANDARD = Path("codex/standards/std_paper_module.json")
STANDARDS_ROOT = Path("codex/standards")
KIND_ATLAS_STANDARD = Path("codex/standards/std_kind_atlas.json")
STANDARDS_REGISTRY_STANDARD = Path("codex/standards/std_standards_registry.json")
SYSTEM_ATLAS_GRAPH = Path("state/system_atlas/system_atlas.graph.json")
SYSTEM_ATLAS_STANDARD = Path("codex/standards/std_system_atlas.json")
SYSTEM_ATLAS_BUILDER = Path("tools/meta/factory/build_system_atlas.py")
FACT_NAVIGATION_CACHE = Path("codex/hologram/facts/navigation_cache.json")
FACT_LEDGER = Path("codex/hologram/facts/ledger.json")
FACT_AUDIT = Path("codex/hologram/facts/audit.json")
FACT_REGISTRY = Path("codex/doctrine/facts/fact_registry.json")
FACT_STANDARD = Path("codex/standards/std_derived_fact.json")
FACT_BUILDER = Path("tools/meta/factory/build_fact_hologram.py")
PYTHON_STANDARD = Path("codex/standards/std_python.py")
PYTHON_SCOPE_INDEX = Path("codex/standards/std_python_scope_index.json")
PYTHON_SYMBOLS = Path("codex/hologram/system/symbols.json")
FRONTEND_NAV_GRAPH = Path("state/frontend_navigation/navigation_graph.json")
FRONTEND_UI_SRC = Path("system/server/ui/src")
FRONTEND_COMPONENT_INDEX = Path("state/frontend_navigation/component_index.json")
FRONTEND_COMPONENT_STANDARD = Path("codex/standards/std_frontend_component_index.json")
FRONTEND_COMPONENT_EXTRACTOR = Path("tools/meta/observability/frontend_component_index.py")
SKILL_REGISTRY = Path("codex/doctrine/skills/skill_registry.json")
SYSTEM_TERM_REGISTRY = Path("codex/doctrine/system_vocabulary/term_registry.json")
SYSTEM_TERM_STANDARD = Path("codex/standards/std_system_term.json")
TASK_LEDGER_LEDGER = Path("state/task_ledger/ledger.json")
TASK_LEDGER_EVENTS = Path("state/task_ledger/events.jsonl")
TASK_LEDGER_STANDARD = Path("codex/standards/std_task_ledger.json")
TASK_LEDGER_SKILL = Path("codex/doctrine/skills/task_ledger/task_ledger.md")
PROMPT_LEDGER_EVENTS = prompt_ledger_events.EVENTS_REL
PROMPT_LEDGER_LEDGER = prompt_ledger_events.LEDGER_REL
PROMPT_LEDGER_VIEWS_ROOT = prompt_ledger_events.VIEWS_REL
PROMPT_LEDGER_STANDARD = Path("codex/standards/std_prompt_ledger.json")
PROMPT_LEDGER_TOOL = Path("tools/meta/observability/prompt_ledger.py")
PROMPT_SHELF_RUNS_INDEX = Path("state/prompt_shelf/prompt_shelf_runs_index.json")
PROMPT_SHELF_RUNS_INDEX_TOOL = Path("tools/meta/observability/prompt_shelf_runs_index.py")
PROMPT_SHELF_LEDGER = Path("obsidian/prompt_shelf/B2 Continue Ledger.md")
COMPRESSION_PROFILES = Path("codex/doctrine/compression_profiles.json")
ANNEX_ROOT = Path("annexes")
ANNEX_DISTILLATION_FILE_NAME = "distillation.json"
MICROCOSM_EXTRACTED_PATTERN_LEDGER = Path("state/microcosm_portfolio/extracted_patterns_ledger.jsonl")
MICROCOSM_EXTRACTED_PATTERN_README = Path("state/microcosm_portfolio/extracted_patterns_ledger_README.md")
MICROCOSM_EXTRACTED_PATTERN_BINDINGS = Path("state/microcosm_portfolio/extracted_pattern_substrate_bindings.json")
MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT = Path(
    "state/microcosm_portfolio/extracted_pattern_route_readiness_audit.json"
)
MICROCOSM_EXTRACTED_PATTERN_SUBSTRATE_STANDARD = Path(
    "codex/standards/std_extracted_pattern_substrate_bindings.json"
)
MICROCOSM_EXTRACTED_PATTERN_ROUTE_STANDARD = Path(
    "codex/standards/std_extracted_pattern_route_readiness.json"
)
NAVIGATION_THEORY = Path("codex/doctrine/paper_modules/navigation_hologram_theory.md")
PROFILE_SKILL = Path("codex/doctrine/skills/compression/profile_governed_compression.md")
TYPE_A_AUTONOMOUS_SEED_ROOT = Path("state/meta_missions/type_a_autonomous_seed_loop/seeds")
TYPE_A_AUTONOMOUS_SEED_STANDARD = Path("codex/standards/std_autonomous_seed_prompt.json")
TYPE_A_AUTONOMOUS_SEED_SKILL = Path("codex/doctrine/skills/kernel/type_a_autonomous_seed_loop.md")
TYPE_A_AUTONOMOUS_SEED_MISSION = Path(
    "codex/standards/observe/mission_templates/meta_missions/type_a_autonomous_seed_loop/mission.json"
)
EXTERNAL_BENCHMARK_CALIBRATION_ROOT = Path(
    "state/benchmarks/external_calibration/verisoftbench_micro_10_v0"
)
EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD = EXTERNAL_BENCHMARK_CALIBRATION_ROOT / "result_board.json"
EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST = EXTERNAL_BENCHMARK_CALIBRATION_ROOT / "slice_manifest.json"
EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD = Path(
    "docs/benchmarks/generated_verisoftbench_micro_10_scorecard.md"
)
EXTERNAL_BENCHMARK_CALIBRATION_BUILDER = Path(
    "tools/meta/factory/build_external_benchmark_calibration_spine.py"
)
EXTERNAL_BENCHMARK_C_ARM_PROVIDER_REPAIR = Path(
    "tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py"
)

RAW_SEED_ROOT = Path("obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed")
RAW_SEED_PRINCIPLES = RAW_SEED_ROOT / "raw_seed_principles.json"
RAW_SEED_SHARDS = RAW_SEED_ROOT / "raw_seed_shards.json"
SYSTEM_AXIOM_CANDIDATES = RAW_SEED_ROOT / "system_axiom_candidates.json"
TELEOLOGY_NODES = Path("codex/doctrine/teleology_nodes.json")
TELEOLOGY_NODE_STANDARD = Path("codex/standards/principles/std_teleology_node.json")
CONCEPT_DIR = Path("codex/doctrine/concepts")
CONCEPT_STANDARD = Path("codex/standards/principles/std_concept.json")
MECHANISM_DIR = Path("codex/doctrine/mechanisms")
MECHANISM_STANDARD = Path("codex/standards/principles/std_mechanism.json")
CONCEPT_MECHANISM_CANDIDATES = Path("codex/doctrine/concept_mechanism_candidates.json")
CONCEPT_MECHANISM_CANDIDATE_CURATION = Path("codex/doctrine/concept_mechanism_candidate_curation.json")
IMAGINATION_INDEX = Path("codex/doctrine/imaginations/_index.json")
IMAGINATION_STANDARD = Path("codex/standards/std_imagination.json")
CONFIG_AUTHORITY_REGISTRY = Path("codex/derived/config_authority_registry.json")
CONFIG_AUTHORITY_STANDARD = Path("codex/standards/std_config_authority_registry.json")
CONFIG_AUTHORITY_BUILDER = Path("tools/meta/factory/build_config_authority_registry.py")
COGNITIVE_OPERATOR_REGISTRY = Path("codex/doctrine/cognitive_operators.json")
COGNITIVE_OPERATOR_STANDARD = Path("codex/standards/std_cognitive_operator.json")
COGNITIVE_OPERATOR_LIBRARY = Path("codex/doctrine/paper_modules/cognitive_operator_library.md")


SUPPORTED_BANDS = {"flag", "card"}
FAST_KIND_ORDER = (
    "paper_modules",
    "standards",
    "task_ledger",
    "prompt_ledger",
    "prompt_shelf_metadata",
    "system_atlas",
    "derived_facts",
    "python_files",
    "python_scopes",
    "frontend_views",
    "frontend_components",
    "skills",
    "system_terms",
    "principles",
    "teleologies",
    "principles_by_teleology",
    "anti_principles",
    "anti_axioms",
    "concepts",
    "mechanisms",
    "concept_mechanism_candidates",
    "concept_mechanism_candidate_curations",
    "axiom_candidates",
    "axioms_by_teleology",
    "imaginations",
    "raw_seed_shards",
    "type_a_autonomous_seeds",
    "external_benchmark_calibration",
    "compression_profiles",
    "microcosm_extracted_patterns",
    "annex_patterns",
    "annex_distillation_patterns",
    "config_authorities",
    "transform_job_receipts",
    "row_patches",
    "compliance_ledger",
    "standard_skill_map",
    "renderer_passports",
    "navigation_type_plane",
    "agent_observations",
    "navigation_training_emissions",
    "navigation_mechanism_candidates",
    "skill_compression_debt",
    "standard_projection_gaps",
    "artifact_projection_debt",
    "system_microcosm",
    "cognitive_operators",
    "github_import_candidates",
    "authoring_contracts",
)
FAST_KIND_ORDER_INDEX = {kind_id: index for index, kind_id in enumerate(FAST_KIND_ORDER)}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _load_prefixed_top_level_dict(path: Path, key: str, *, prefix_bytes: int = 262_144) -> dict[str, Any]:
    """Read a top-level object value near the start of a large JSON file.

    Some first-contact atlas rows need projection metadata, not the full
    browse index body. `std_python_scope_index.json` is tens of MB and keeps
    `__meta` first, so parsing only that object prevents a cold navigation
    route from paying to deserialize every file and symbol row.
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            prefix = handle.read(prefix_bytes)
    except FileNotFoundError:
        return {}

    marker = json.dumps(key)
    key_index = prefix.find(marker)
    if key_index < 0:
        return {}
    colon_index = prefix.find(":", key_index + len(marker))
    if colon_index < 0:
        return {}

    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(prefix[colon_index + 1 :].lstrip())
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _standard_count(root: Path) -> int:
    standards_root = root / STANDARDS_ROOT
    if not standards_root.exists():
        return 0
    return sum(
        1
        for path in standards_root.rglob("std_*.json")
        if path.is_file() and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts
    )


def _paper_module_count(root: Path) -> tuple[int, dict[str, Any]]:
    index = _load_json(root / PAPER_MODULE_INDEX)
    modules = index.get("modules") if isinstance(index.get("modules"), list) else []
    return len(modules), index


def _system_atlas_meta(root: Path) -> dict[str, Any]:
    graph = _load_json(root / SYSTEM_ATLAS_GRAPH)
    summary = graph.get("summary") if isinstance(graph.get("summary"), dict) else {}
    entities = graph.get("entities") if isinstance(graph.get("entities"), list) else []
    return {
        "entity_count": int(summary.get("entity_count") or len(entities)),
        "generated_at": graph.get("generated_at"),
        "available": bool(graph),
    }


def _system_atlas_currentness(system_atlas_meta: dict[str, Any]) -> dict[str, Any]:
    artifact_available = bool(system_atlas_meta.get("available"))
    currentness = _currentness(
        source_refs=[str(SYSTEM_ATLAS_GRAPH), str(SYSTEM_ATLAS_STANDARD), str(SYSTEM_ATLAS_BUILDER)],
        generated_at=str(system_atlas_meta.get("generated_at") or ""),
        status="source_coupling_check_required" if artifact_available else "system_atlas_graph_missing",
    )
    currentness["graph_status"] = "system_atlas_graph_available" if artifact_available else "system_atlas_graph_missing"
    currentness["graph_generated_at"] = system_atlas_meta.get("generated_at")
    currentness["source_coupling_status"] = (
        "not_evaluated_in_kind_atlas_hot_path" if artifact_available else "source_coupling_unavailable"
    )
    currentness["freshness_command"] = f"./repo-python {SYSTEM_ATLAS_BUILDER} --check"
    currentness["trust_boundary"] = "artifact_presence_does_not_prove_source_coupling"
    currentness["recommended_action"] = (
        "run owner check before trusting atlas-backed freshness or generated sidecars"
        if artifact_available
        else "run owner builder to create the System Atlas graph"
    )
    return currentness


def _fact_navigation_meta(root: Path) -> dict[str, Any]:
    cache = _load_json(root / FACT_NAVIGATION_CACHE)
    ledger: Mapping[str, Any] = {}
    audit: Mapping[str, Any] = {}
    source = "generated_outputs"
    if not cache:
        try:
            from system.lib.derived_fact_hologram import build_fact_hologram
        except ImportError:
            build_fact_hologram = None  # type: ignore[assignment]
        if build_fact_hologram is not None:
            payload = build_fact_hologram(repo_root=root)
            cache = payload.get("navigation_cache") if isinstance(payload.get("navigation_cache"), dict) else {}
            ledger = payload.get("ledger") if isinstance(payload.get("ledger"), dict) else {}
            audit = payload.get("audit") if isinstance(payload.get("audit"), dict) else {}
            source = "facts_owner_live_read_model"
    summary = cache.get("summary") if isinstance(cache.get("summary"), dict) else {}
    if not summary and isinstance(ledger.get("summary"), dict):
        summary = ledger.get("summary") or {}
    audit_summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    missing_outputs = [
        str(path)
        for path in (FACT_LEDGER, FACT_AUDIT, FACT_NAVIGATION_CACHE)
        if not (root / path).is_file()
    ]
    if cache and missing_outputs:
        status = "live_fact_surface_available_generated_outputs_missing"
    elif cache:
        status = str(cache.get("artifact_role") or "generated_state_axis_artifact")
    else:
        status = "fact_navigation_cache_missing"
    return {
        "available": bool(cache),
        "generated_at": cache.get("generated_at"),
        "artifact_role": cache.get("artifact_role") or "generated_state_axis_artifact",
        "currentness_status": status,
        "fact_count": int(summary.get("fact_count") or 0),
        "tag_count": int(summary.get("tag_count") or len(cache.get("tag_index") or [])),
        "facet_count": int(summary.get("facet_count") or len(cache.get("facet_index") or [])),
        "fact_family_count": int(summary.get("fact_family_count") or len(cache.get("fact_family_index") or [])),
        "source": source,
        "missing_generated_outputs": missing_outputs,
        "provider_error_count": int(summary.get("error_count") or audit_summary.get("provider_error_count") or 0),
    }


def _python_scope_meta(root: Path) -> dict[str, Any]:
    path = root / PYTHON_SCOPE_INDEX
    meta = _load_prefixed_top_level_dict(path, "__meta")
    if meta:
        return meta
    return _load_json(path).get("__meta", {}) or {}


def _frontend_view_count(root: Path) -> tuple[int, dict[str, Any]]:
    graph = _load_json(root / FRONTEND_NAV_GRAPH)
    views = graph.get("views")
    if isinstance(views, list):
        count = len(views)
    elif isinstance(views, dict):
        count = len(views)
    else:
        count = int((graph.get("counts") or {}).get("pages") or 0) if isinstance(graph.get("counts"), dict) else 0
    return count, graph


def _frontend_component_meta(root: Path) -> dict[str, Any]:
    """Read the frontend component index projection metadata.

    Returns counts split by classification confidence so Atlas can name the
    primary option-surface row count distinctly from the candidate-count and
    omitted-low-confidence-count published by the adapter.
    """
    index = _load_json(root / FRONTEND_COMPONENT_INDEX)
    components = index.get("components") if isinstance(index.get("components"), list) else []
    primary = 0
    omitted = 0
    candidate = 0
    for component in components:
        if not isinstance(component, dict):
            continue
        candidate += 1
        confidence = str(component.get("classification_confidence") or "")
        if confidence in {"high", "medium"}:
            primary += 1
        elif confidence == "low":
            omitted += 1
    meta = index.get("__meta") if isinstance(index.get("__meta"), dict) else {}
    return {
        "available": bool(components),
        "primary_count": primary,
        "candidate_count": candidate,
        "omitted_low_confidence_count": omitted,
        "file_count": meta.get("file_count"),
        "generated_at": meta.get("generated_at"),
    }


def _skill_count(root: Path) -> int:
    registry = _load_json(root / SKILL_REGISTRY)
    families = registry.get("families")
    if not isinstance(families, list):
        return 0
    total = 0
    for family in families:
        if isinstance(family, dict) and isinstance(family.get("skills"), list):
            total += len(family["skills"])
    return total


def _config_authority_meta(root: Path) -> dict[str, Any]:
    try:
        from system.lib.config_authority_registry import load_config_authority_registry
    except ImportError:
        return {"available": False, "row_count": 0, "generated_at": None, "diagnostic_count": None}
    payload = load_config_authority_registry(repo_root=root)
    return {
        "available": bool(payload),
        "row_count": int(payload.get("row_count") or 0),
        "generated_at": payload.get("generated_at"),
        "diagnostic_count": payload.get("diagnostic_count"),
    }


def _task_ledger_count(root: Path) -> tuple[int, dict[str, Any]]:
    ledger = _load_json(root / TASK_LEDGER_LEDGER)
    work_items = ledger.get("work_items")
    return len(work_items) if isinstance(work_items, list) else 0, ledger


def _prompt_ledger_meta(root: Path) -> dict[str, Any]:
    ledger = _load_json(root / PROMPT_LEDGER_LEDGER)
    views = [
        prompt_ledger_events.ADOPTION_POSTURE_REL,
        prompt_ledger_events.RECENT_PROMPT_TRACES_REL,
        prompt_ledger_events.UNLINKED_PROMPT_TRACES_REL,
        prompt_ledger_events.WORKITEM_PROMPT_LINKS_REL,
        prompt_ledger_events.SOURCE_STREAM_CURSORS_REL,
        prompt_ledger_events.SOURCE_IDEMPOTENCY_KEYS_REL,
        prompt_ledger_events.SOURCE_DRIFT_REL,
    ]
    available_views = [path for path in views if (root / path).exists()]
    try:
        projection_check = prompt_ledger_events.check_projection_files(root)
    except Exception as exc:  # pragma: no cover - atlas should degrade to a row, not hide the kind
        projection_check = {"ok": False, "error": str(exc)}
    return {
        "ledger": ledger,
        "trace_count": _int(ledger.get("trace_count")),
        "event_count": _int(ledger.get("event_count")),
        "view_count": len(available_views),
        "projection_ok": bool(projection_check.get("ok")),
        "projection_check": projection_check,
    }


def _prompt_shelf_metadata_meta(root: Path) -> dict[str, Any]:
    meta = _load_prefixed_top_level_dict(root / PROMPT_SHELF_RUNS_INDEX, "__meta")
    return {
        "available": bool(meta),
        "run_count": _int(meta.get("run_count")),
        "receipt_present_count": _int(meta.get("receipt_present_count")),
        "issues_total": _int(meta.get("issues_total")),
        "generated_at": meta.get("generated_at"),
        "schema_version": meta.get("schema_version"),
        "projection_exists": (root / PROMPT_SHELF_RUNS_INDEX).exists(),
    }


def _type_a_autonomous_seed_meta(root: Path) -> dict[str, Any]:
    seeds_root = root / TYPE_A_AUTONOMOUS_SEED_ROOT
    if not seeds_root.exists():
        return {
            "available": False,
            "seed_count": 0,
            "markdown_count": 0,
            "navigation_map_count": 0,
            "latest_seed_mtime": None,
        }

    seed_count = 0
    markdown_count = 0
    navigation_map_count = 0
    mtimes: list[str] = []
    for json_path in sorted(seeds_root.glob("*_autonomous_seed.json")):
        payload = _load_json(json_path)
        seed_id = str(payload.get("seed_id") or "").strip()
        if not seed_id and json_path.name.endswith("_autonomous_seed.json"):
            seed_id = json_path.name[: -len("_autonomous_seed.json")]
        if not seed_id:
            continue
        seed_count += 1
        markdown_path = seeds_root / f"{seed_id}_autonomous_seed.md"
        navigation_map_path = seeds_root / f"{seed_id}_navigation_map.json"
        markdown_count += int(markdown_path.exists())
        navigation_map_count += int(navigation_map_path.exists())
        for candidate in (json_path, markdown_path, navigation_map_path):
            mtime = _mtime(candidate)
            if mtime:
                mtimes.append(mtime)

    return {
        "available": seed_count > 0,
        "seed_count": seed_count,
        "markdown_count": markdown_count,
        "navigation_map_count": navigation_map_count,
        "latest_seed_mtime": max(mtimes) if mtimes else None,
    }


def _external_benchmark_calibration_meta(root: Path) -> dict[str, Any]:
    try:
        result_board = _load_json(root / EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD)
    except (FileNotFoundError, json.JSONDecodeError):
        result_board = {}
    try:
        slice_manifest = _load_json(root / EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST)
    except (FileNotFoundError, json.JSONDecodeError):
        slice_manifest = {}
    root_path = root / EXTERNAL_BENCHMARK_CALIBRATION_ROOT
    c_arm_receipts = 0
    if root_path.exists():
        c_arm_receipts = sum(
            1
            for path in root_path.glob("c_arm_provider_repair/*/c_arm_provider_repair_receipt.json")
            if path.is_file()
        )
    generated_at = (
        result_board.get("created_from_source_receipts_at")
        or _mtime(root / EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD)
        or _mtime(root / EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST)
    )
    return {
        "available": bool(result_board) and bool(slice_manifest),
        "planned_task_count": _int(
            result_board.get("planned_task_count") or slice_manifest.get("planned_task_count")
        ),
        "evaluated_task_count": _int(result_board.get("evaluated_task_count")),
        "solved_count": _int(result_board.get("solved_count")),
        "c_arm_provider_repair_receipt_count": c_arm_receipts,
        "generated_at": generated_at,
        "public_claim_allowed": bool(result_board.get("public_claim_allowed")),
        "official_leaderboard_submission": bool(result_board.get("official_leaderboard_submission")),
        "scorecard_exists": (root / EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD).exists(),
    }


def _list_count(root: Path, path: Path, key: str) -> int:
    data = _load_json(root / path)
    value = data.get(key)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    return 0


def _concept_count(root: Path) -> int:
    concepts_root = root / CONCEPT_DIR
    if not concepts_root.exists():
        return 0
    return sum(1 for path in concepts_root.glob("con_*.json") if path.is_file())


def _mechanism_count(root: Path) -> int:
    mechanisms_root = root / MECHANISM_DIR
    if not mechanisms_root.exists():
        return 0
    return sum(1 for path in mechanisms_root.glob("mech_*.json") if path.is_file())


def _concept_mechanism_candidate_count(root: Path) -> int:
    data = _load_json(root / CONCEPT_MECHANISM_CANDIDATES)
    candidates = data.get("candidates")
    return len(candidates) if isinstance(candidates, list) else 0


def _concept_mechanism_candidate_curation_count(root: Path) -> int:
    data = _load_json(root / CONCEPT_MECHANISM_CANDIDATE_CURATION)
    packets = data.get("packets")
    return len(packets) if isinstance(packets, list) else 0


def _teleology_node_count(root: Path) -> int:
    data = _load_json(root / TELEOLOGY_NODES)
    rows = data.get("teleology_nodes")
    if rows is None:
        rows = data.get("desire_nodes")
    if isinstance(rows, list):
        return len(rows)
    if isinstance(rows, dict):
        return len(rows)
    return 0


def _rows_with_string_list(root: Path, path: Path, key: str, field: str) -> int:
    data = _load_json(root / path)
    rows = data.get(key)
    if not isinstance(rows, list):
        return 0
    return sum(
        1
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get(field), list)
        and any(str(item).strip() for item in row.get(field) or [])
    )


def _rows_with_object(root: Path, path: Path, key: str, field: str) -> int:
    data = _load_json(root / path)
    rows = data.get(key)
    if not isinstance(rows, list):
        return 0
    return sum(1 for row in rows if isinstance(row, dict) and isinstance(row.get(field), dict))


def _compression_profile_count(root: Path) -> int:
    data = _load_json(root / COMPRESSION_PROFILES)
    profiles = data.get("profiles")
    if isinstance(profiles, list):
        return len(profiles)
    if isinstance(profiles, dict):
        return len(profiles)
    return 0


def _annex_pattern_count(root: Path) -> int:
    """Count annex pattern rows as one row per stable note.

    The annex_patterns option-surface adapter emits one row per `<slug>:<note_id>`
    entry across `annexes/<slug>/annex_notes.json`. Atlas row_count must agree
    with adapter total_available, so this counter walks the same files and sums
    the per-annex `notes` arrays.
    """
    annex_root = root / ANNEX_ROOT
    if not annex_root.exists():
        return 0
    total = 0
    counted = False
    for notes_path in annex_root.glob("*/annex_notes.json"):
        try:
            data = json.loads(notes_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        notes = data.get("notes")
        if isinstance(notes, list):
            counted = True
            for note in notes:
                if isinstance(note, dict) and str(note.get("id") or "").strip():
                    total += 1
    if counted:
        return total
    return sum(1 for path in annex_root.iterdir() if path.is_dir() and not path.name.startswith("."))


def _annex_distillation_pattern_count(root: Path) -> int:
    annex_root = root / ANNEX_ROOT
    if not annex_root.exists():
        return 0
    total = 0
    for distillation_path in annex_root.glob(f"*/{ANNEX_DISTILLATION_FILE_NAME}"):
        try:
            data = json.loads(distillation_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        patterns = data.get("patterns")
        if isinstance(patterns, list):
            total += sum(
                1
                for pattern in patterns
                if isinstance(pattern, dict) and str(pattern.get("id") or "").strip()
            )
    return total


def _microcosm_extracted_pattern_count(root: Path) -> int:
    ledger_path = root / MICROCOSM_EXTRACTED_PATTERN_LEDGER
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return 0
    total = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and str(row.get("pattern_id") or "").strip():
            total += 1
    return total


def _currentness(*, source_refs: list[str], generated_at: str | None = None, status: str = "live_probe") -> dict[str, Any]:
    mtimes: dict[str, str | None] = {}
    for ref in source_refs:
        path = Path(ref)
        mtimes[ref] = _mtime(path if path.is_absolute() else Path.cwd() / path)
    return {
        "status": status,
        "generated_at": generated_at,
        "source_refs_checked": source_refs,
        "source_mtimes": {key: value for key, value in mtimes.items() if value is not None},
    }


def _row(
    *,
    kind_id: str,
    title: str,
    flag: str,
    row_count: int,
    governing_standard_refs: list[str],
    projection_refs: list[str],
    bands: list[str],
    support_status: str,
    option_surface_command: str | None,
    card_command: str | None,
    evidence_command: str,
    currentness: dict[str, Any],
    cluster_command: str | None = None,
    profile_gap: dict[str, Any] | None = None,
    card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Governance fields (surface_role, first_contact_allowed, control_replacement,
    # allowed_callers, banned_callers) are static across all rows — they describe
    # the atlas-projection contract for the whole packet, not per-kind state. They
    # already live on the top-level `navigation_boundary` field. Carrying them on
    # every row produces ~14KB of redundant bytes for a 41-row atlas (analyzed
    # iter 7 of autonomous bug sweep) and confuses consumers about whether the
    # row is the authority for the boundary contract or merely re-stating it.
    # The boundary contract IS authority on the top-level packet only.
    base = {
        "kind_id": kind_id,
        "title": title,
        "flag": flag,
        "row_count": row_count,
        "governing_standard_refs": governing_standard_refs,
        "projection_refs": projection_refs,
        "bands": bands,
        "support_status": support_status,
        "option_surface_command": option_surface_command,
        "cluster_command": cluster_command
        or (
            option_surface_command
            if option_surface_command and "--band cluster_flag" in option_surface_command
            else None
        ),
        "card_command": card_command,
        "evidence_command": evidence_command,
        "currentness": currentness,
        "profile_gap": profile_gap,
    }
    if card:
        base.update(card)
    return base


def _card_extra(*, rung1: str, rung2: str = "generic_row_not_implemented", rung3: str = "source_command_available", next_moves: list[str], omissions: list[str]) -> dict[str, Any]:
    return {
        "rung_support": {
            "rung_0_kind_atlas": "supported",
            "rung_1_kind_option_surface": rung1,
            "rung_2_row_at_band": rung2,
            "rung_3_source_evidence": rung3,
        },
        "known_next_moves": next_moves,
        "omission_receipt": {
            "omitted": omissions,
            "reason": "The kind card is a rung-0/rung-1 selection surface. It names the next surface rather than replacing kind-specific source evidence.",
        },
    }


def _kind_id_from_system_atlas_entity(entity: Mapping[str, Any]) -> str:
    metrics = entity.get("metrics") if isinstance(entity.get("metrics"), Mapping) else {}
    kind_id = str(metrics.get("kind_id") or "").strip()
    if kind_id:
        return kind_id
    entity_id = str(entity.get("id") or "").strip()
    if entity_id.startswith("kind_"):
        return entity_id.removeprefix("kind_")
    return entity_id


FAST_CLUSTER_FIRST_COMMAND_OVERRIDES: dict[str, str] = {
    # Routine context-packs use System Atlas fast rows; keep source-owned
    # cluster promotions effective before the next generated Atlas refresh.
    "frontend_views": "./repo-python kernel.py --option-surface frontend_views --band cluster_flag",
    "type_a_autonomous_seeds": "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag",
}


def _fast_kind_command(kind_id: str, metrics: Mapping[str, Any]) -> tuple[str | None, str | None]:
    override_command = FAST_CLUSTER_FIRST_COMMAND_OVERRIDES.get(kind_id)
    if override_command:
        return override_command, override_command

    cluster_summary = metrics.get("cluster_summary") if isinstance(metrics.get("cluster_summary"), Mapping) else {}
    standard_type_plane = (
        metrics.get("standard_type_plane") if isinstance(metrics.get("standard_type_plane"), Mapping) else {}
    )
    cluster_command = str(metrics.get("cluster_command") or cluster_summary.get("cluster_command") or "").strip()
    option_surface_command = str(
        metrics.get("option_surface_command") or standard_type_plane.get("option_surface_command") or ""
    ).strip()
    bands = {str(item) for item in list(metrics.get("bands") or [])}
    if not cluster_command and "--band cluster_flag" in option_surface_command:
        cluster_command = option_surface_command
    if not option_surface_command:
        if cluster_command:
            option_surface_command = cluster_command
        elif "cluster_flag" in bands:
            option_surface_command = f"./repo-python kernel.py --option-surface {kind_id} --band cluster_flag"
        elif "flag" in bands or "card" in bands:
            option_surface_command = f"./repo-python kernel.py --option-surface {kind_id} --band flag"
    return option_surface_command or None, cluster_command or None


def _fast_cognitive_operator_count(repo_root: Path) -> int:
    payload = _load_json(repo_root / COGNITIVE_OPERATOR_REGISTRY)
    operators = payload.get("operators") if isinstance(payload.get("operators"), list) else []
    return len(operators)


def _fast_cognitive_operator_row(repo_root: Path) -> dict[str, Any]:
    return {
        "kind_id": "cognitive_operators",
        "title": "Cognitive Operators",
        "flag": "Reusable thinking operators with governed affordance passports and dogfood receipts.",
        "row_count": _fast_cognitive_operator_count(repo_root),
        "governing_standard_refs": [str(COGNITIVE_OPERATOR_STANDARD)],
        "projection_refs": [
            str(COGNITIVE_OPERATOR_REGISTRY),
            str(COGNITIVE_OPERATOR_LIBRARY),
            "state/cognitive_operators/dogfood",
        ],
        "bands": ["flag", "card"],
        "support_status": "option_surface_supported",
        "option_surface_command": "./repo-python kernel.py --option-surface cognitive_operators --band flag",
        "cluster_command": None,
        "card_command": "./repo-python kernel.py --row cognitive_operators:<operator_id> --band card",
        "evidence_command": "./repo-python tools/meta/factory/validate_cognitive_operator_registry.py --json",
        "currentness": {
            "status": "cognitive_operator_registry_available",
            "source_refs_checked": [
                str(COGNITIVE_OPERATOR_REGISTRY),
                str(COGNITIVE_OPERATOR_STANDARD),
                str(COGNITIVE_OPERATOR_LIBRARY),
            ],
        },
        "profile_gap": None,
    }


def _fast_type_a_autonomous_seed_count(repo_root: Path) -> int:
    seeds_root = repo_root / TYPE_A_AUTONOMOUS_SEED_ROOT
    if not seeds_root.exists():
        return 0
    return sum(1 for _path in seeds_root.glob("*_autonomous_seed.json"))


def _fast_type_a_autonomous_seed_row(repo_root: Path) -> dict[str, Any]:
    return {
        "kind_id": "type_a_autonomous_seeds",
        "title": "Type A Autonomous Seeds",
        "flag": (
            "Saved Type A autonomous seed JSON/markdown bundles are browseable by lane cluster, "
            "then seed id, with owner, validation, currentness, and private-root disclosure routes."
        ),
        "row_count": _fast_type_a_autonomous_seed_count(repo_root),
        "governing_standard_refs": [
            str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
            str(TYPE_A_AUTONOMOUS_SEED_SKILL),
            str(TYPE_A_AUTONOMOUS_SEED_MISSION),
        ],
        "projection_refs": [str(TYPE_A_AUTONOMOUS_SEED_ROOT)],
        "bands": ["cluster_flag", "flag", "card"],
        "support_status": "option_surface_supported",
        "option_surface_command": "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag",
        "cluster_command": "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag",
        "card_command": "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band card --ids <seed_id>",
        "evidence_command": "./repo-python kernel.py --raw-seed-autonomous-seed-bundle <seed_id>",
        "currentness": _currentness(
            source_refs=[
                str(TYPE_A_AUTONOMOUS_SEED_ROOT),
                str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
                str(TYPE_A_AUTONOMOUS_SEED_SKILL),
                str(TYPE_A_AUTONOMOUS_SEED_MISSION),
            ],
            status="type_a_autonomous_seed_bundles_available",
        ),
        "profile_gap": None,
    }


def _apply_fast_live_count_overlay(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    kind_id = str(row.get("kind_id") or "")
    if kind_id != "paper_modules":
        return row

    live_count, _index = _paper_module_count(root)
    system_atlas_count = _int(row.get("row_count"))
    if live_count == system_atlas_count:
        return row

    row = dict(row)
    row["row_count"] = live_count
    currentness = (
        dict(row.get("currentness") or {})
        if isinstance(row.get("currentness"), Mapping)
        else {}
    )
    source_refs = [
        str(item)
        for item in list(currentness.get("source_refs_checked") or [])
        if str(item).strip()
    ]
    paper_index_ref = str(PAPER_MODULE_INDEX)
    if paper_index_ref not in source_refs:
        source_refs.append(paper_index_ref)
    source_mtimes = (
        dict(currentness.get("source_mtimes") or {})
        if isinstance(currentness.get("source_mtimes"), Mapping)
        else {}
    )
    index_mtime = _mtime(root / PAPER_MODULE_INDEX)
    if index_mtime:
        source_mtimes[paper_index_ref] = index_mtime
    currentness.update(
        {
            "source_refs_checked": source_refs,
            "source_mtimes": source_mtimes,
            "fast_live_overlay": {
                "status": "applied",
                "field": "row_count",
                "previous_system_atlas_count": system_atlas_count,
                "live_source_count": live_count,
                "source_ref": paper_index_ref,
                "reason": (
                    "routine kind-atlas fast rows use System Atlas for breadth, "
                    "but paper-module corpus size is authoritative in the module index"
                ),
            },
        }
    )
    row["currentness"] = currentness
    return row


def _fast_rows_from_system_atlas(root: Path) -> list[dict[str, Any]]:
    graph = _load_json(root / SYSTEM_ATLAS_GRAPH)
    entities = graph.get("entities") if isinstance(graph.get("entities"), list) else []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entity in entities:
        if not isinstance(entity, Mapping) or str(entity.get("kind") or "") != "ArtifactKind":
            continue
        metrics = entity.get("metrics") if isinstance(entity.get("metrics"), Mapping) else {}
        kind_id = _kind_id_from_system_atlas_entity(entity)
        if not kind_id:
            continue
        option_surface_command, cluster_command = _fast_kind_command(kind_id, metrics)
        bands = [str(item) for item in list(metrics.get("bands") or []) if str(item).strip()]
        if kind_id in FAST_CLUSTER_FIRST_COMMAND_OVERRIDES and "cluster_flag" not in bands:
            bands = ["cluster_flag", *bands]
        support_status = str(metrics.get("support_status") or "").strip()
        if not support_status:
            support_status = "option_surface_supported" if option_surface_command else "projection_gap"
        row = {
            "kind_id": kind_id,
            "title": str(entity.get("title") or kind_id.replace("_", " ").title()),
            "flag": str(entity.get("summary") or kind_id.replace("_", " ").title()),
            "row_count": _int(metrics.get("kind_atlas_row_count")),
            "governing_standard_refs": list(metrics.get("governing_standard_refs") or []),
            "projection_refs": list(metrics.get("projection_refs") or []),
            "bands": bands,
            "support_status": support_status,
            "option_surface_command": option_surface_command,
            "cluster_command": cluster_command,
            "card_command": metrics.get("card_command")
            or (
                f"./repo-python kernel.py --option-surface {kind_id} --band card --ids <row_id>"
                if "card" in bands
                else None
            ),
            "evidence_command": metrics.get("evidence_command") or option_surface_command,
            "currentness": metrics.get("currentness") if isinstance(metrics.get("currentness"), Mapping) else {},
            "profile_gap": metrics.get("profile_gap"),
        }
        if isinstance(metrics.get("row_count_semantics"), Mapping):
            row["row_count_semantics"] = dict(metrics.get("row_count_semantics") or {})
        row = _apply_fast_live_count_overlay(root, row)
        rows.append(row)
        seen.add(kind_id)
    if "cognitive_operators" not in seen:
        rows.append(_fast_cognitive_operator_row(root))
    if "type_a_autonomous_seeds" not in seen:
        rows.append(_fast_type_a_autonomous_seed_row(root))
    rows.sort(key=lambda row: (FAST_KIND_ORDER_INDEX.get(str(row.get("kind_id") or ""), 10_000), str(row.get("kind_id") or "")))
    return rows


def _build_rows(root: Path, *, band: str, include_generated: bool = True) -> list[dict[str, Any]]:
    paper_count, paper_index = _paper_module_count(root)
    python_meta = _python_scope_meta(root)
    frontend_view_count, frontend_graph = _frontend_view_count(root)
    frontend_graph_exists = (root / FRONTEND_NAV_GRAPH).exists()
    frontend_component_meta = _frontend_component_meta(root)
    task_ledger_count, task_ledger = _task_ledger_count(root)
    prompt_ledger_meta = _prompt_ledger_meta(root)
    prompt_shelf_metadata_meta = _prompt_shelf_metadata_meta(root)
    type_a_autonomous_seed_meta = _type_a_autonomous_seed_meta(root)
    external_benchmark_calibration_meta = _external_benchmark_calibration_meta(root)
    system_atlas_meta = _system_atlas_meta(root)
    fact_navigation_meta = _fact_navigation_meta(root)
    config_authority_meta = _config_authority_meta(root)
    card_band = band == "card"

    rows: list[dict[str, Any]] = [
        _row(
            kind_id="paper_modules",
            title="Paper Modules",
            flag="Subsystem theory projections with standard-owned TLDR, dependency, and currentness bands.",
            row_count=paper_count,
            governing_standard_refs=[str(PAPER_MODULE_STANDARD)],
            projection_refs=[str(PAPER_MODULE_INDEX)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface paper_modules --band card --ids <slug>",
            evidence_command="./repo-python kernel.py --paper-module <slug>",
            currentness=_currentness(
                source_refs=[str(PAPER_MODULE_INDEX), str(PAPER_MODULE_STANDARD)],
                generated_at=str(paper_index.get("generated_at") or ""),
                status=str((paper_index.get("freshness") or {}).get("status") or "projection_available"),
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
                    "./repo-python kernel.py --option-surface paper_modules --band flag --ids navigation_hologram_theory",
                    "./repo-python kernel.py --option-surface paper_modules --band card --ids navigation_hologram_theory",
                ],
                omissions=["full module markdown bodies", "transitive dependency closure"],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="standards",
            title="Standards",
            flag="Machine-readable grammar surfaces that tell agents how artifact classes should be written and read.",
            row_count=_standard_count(root),
            governing_standard_refs=[str(STANDARDS_REGISTRY_STANDARD)],
            projection_refs=["codex/standards/standards_registry.json", "codex/standards/core_authority_index.json"],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface standards --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface standards --band card --ids <standard_id>",
            evidence_command="jq '.' codex/standards/<std_file>.json",
            currentness=_currentness(
                source_refs=["codex/standards/standards_registry.json", "codex/standards/core_authority_index.json"],
                status="source_walk_live",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface standards --band cluster_flag",
                    "./repo-python kernel.py --option-surface standards --band flag --ids std_semantic_naming",
                    "./repo-python kernel.py --option-surface standards --band card --ids std_semantic_naming",
                ],
                omissions=[
                    "full standard JSON bodies",
                    "markdown companion drift findings",
                    "row-level standard flags unless explicit --ids are supplied",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="task_ledger",
            title="Task Ledger WorkItems",
            flag="WorkItem backlog, capture triage, execution menu, and signoff queues are browseable before raw JSON.",
            row_count=task_ledger_count,
            governing_standard_refs=[str(TASK_LEDGER_STANDARD)],
            projection_refs=[str(TASK_LEDGER_LEDGER), "state/task_ledger/views"],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface task_ledger --band card --ids <work_item_id>",
            evidence_command="jq '.work_items[] | select(.id==\"<work_item_id>\")' state/task_ledger/ledger.json",
            currentness=_currentness(
                source_refs=[str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER), str(TASK_LEDGER_STANDARD)],
                generated_at=str(task_ledger.get("generated_at") or task_ledger.get("updated_at") or ""),
                status="task_ledger_projection_available" if task_ledger_count else "task_ledger_projection_missing_or_empty",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                    "./repo-python kernel.py --option-surface task_ledger --band flag --ids cap_035",
                    "./repo-python kernel.py --option-surface task_ledger --band card --ids cap_035",
                ],
                omissions=["raw event payload chain", "full source docs behind source refs"],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="prompt_ledger",
            title="Prompt Ledger",
            flag="Prompt trace provenance, adoption posture, and prompt-shelf/operator-thread evidence projections are browseable before raw event logs.",
            row_count=int(prompt_ledger_meta.get("trace_count") or 0),
            governing_standard_refs=[str(PROMPT_LEDGER_STANDARD)],
            projection_refs=[str(PROMPT_LEDGER_LEDGER), str(PROMPT_LEDGER_VIEWS_ROOT)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface prompt_ledger --band flag",
            card_command="./repo-python kernel.py --option-surface prompt_ledger --band card --ids <view_id>",
            evidence_command="./repo-python tools/meta/observability/prompt_ledger.py validate",
            currentness=_currentness(
                source_refs=[
                    str(PROMPT_LEDGER_EVENTS),
                    str(PROMPT_LEDGER_LEDGER),
                    str(PROMPT_LEDGER_VIEWS_ROOT),
                    str(PROMPT_LEDGER_STANDARD),
                ],
                status=(
                    "prompt_ledger_projection_available"
                    if prompt_ledger_meta.get("projection_ok")
                    else "prompt_ledger_projection_stale_or_missing"
                ),
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface prompt_ledger --band flag",
                    "./repo-python kernel.py --option-surface prompt_ledger --band card --ids adoption_posture",
                    "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
                ],
                omissions=[
                    "raw Type B/operator thread bodies",
                    "raw prompt/response text",
                    "full Prompt Ledger event chain",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="prompt_shelf_metadata",
            title="Prompt Shelf Metadata",
            flag=(
                "Metadata-only prompt-shelf run index for Type B extraction, receipt coverage, "
                "and private reasoning handles before opening raw prompt bodies."
            ),
            row_count=int(prompt_shelf_metadata_meta.get("run_count") or 0),
            governing_standard_refs=[
                "codex/standards/std_agent_entry_surface.json::type_b_to_type_a_handoff_framing_contract"
            ],
            projection_refs=[str(PROMPT_SHELF_RUNS_INDEX), str(PROMPT_SHELF_LEDGER)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface prompt_shelf_metadata --band cluster_flag",
            cluster_command="./repo-python kernel.py --option-surface prompt_shelf_metadata --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface prompt_shelf_metadata --band card --ids prompt_shelf_runs_index_v1",
            evidence_command="./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
            currentness=_currentness(
                source_refs=[
                    str(PROMPT_SHELF_RUNS_INDEX),
                    str(PROMPT_SHELF_RUNS_INDEX_TOOL),
                    str(PROMPT_SHELF_LEDGER),
                ],
                generated_at=str(prompt_shelf_metadata_meta.get("generated_at") or ""),
                status=(
                    "prompt_shelf_metadata_projection_available"
                    if prompt_shelf_metadata_meta.get("available")
                    else "prompt_shelf_metadata_projection_missing_or_empty"
                ),
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface prompt_shelf_metadata --band cluster_flag",
                    "./repo-python kernel.py --option-surface prompt_shelf_metadata --band card --ids prompt_shelf_runs_index_v1",
                    "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                    "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
                    "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
                ],
                omissions=[
                    "raw Type B/operator thread bodies",
                    "raw prompt/provider text",
                    "raw event JSON",
                    "full run markdown",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="system_atlas",
            title="System Atlas",
            flag="Generated substrate coverage/control-plane graph over domains, evidence, risk, disclosure, freshness, and agent drilldowns.",
            row_count=int(system_atlas_meta.get("entity_count") or 0),
            governing_standard_refs=[str(SYSTEM_ATLAS_STANDARD)],
            projection_refs=[str(SYSTEM_ATLAS_GRAPH), "docs/system_atlas/generated_system_atlas_snapshot.md"],
            bands=["cluster_flag", "flag", "card", "stale", "unknowns"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface system_atlas --band card --ids <entity_id>",
            evidence_command="./repo-python tools/meta/factory/build_system_atlas.py --check",
            currentness=_system_atlas_currentness(system_atlas_meta),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python tools/meta/factory/build_system_atlas.py",
                    "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                    "./repo-python kernel.py --option-surface system_atlas --band card --ids dom_system_atlas",
                    "./repo-python kernel.py --option-surface system_atlas --band unknowns",
                ],
                omissions=[
                    "raw seed text",
                    "provider prompt/output bodies",
                    "browser session state",
                    "finance artifact contents",
                    "private logs and correspondence",
                    "full state artifact bodies",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="derived_facts",
            title="Derived Facts / State Axes",
            flag=(
                "Generated fact ledger and compressed state-axis artifact over subject/facet/value rows; "
                "use for questions like what states exist, what is banned, and what is stale."
            ),
            row_count=int(fact_navigation_meta.get("fact_count") or 0),
            governing_standard_refs=[str(FACT_STANDARD)],
            projection_refs=[str(FACT_LEDGER), str(FACT_AUDIT), str(FACT_NAVIGATION_CACHE)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --facts --band cluster_flag",
            cluster_command="./repo-python kernel.py --facts --band cluster_flag",
            card_command="./repo-python kernel.py --fact <fact_id>",
            evidence_command="./repo-python tools/meta/factory/build_fact_hologram.py --check",
            currentness={
                **_currentness(
                    source_refs=[
                        str(FACT_NAVIGATION_CACHE),
                        str(FACT_LEDGER),
                        str(FACT_AUDIT),
                        str(FACT_REGISTRY),
                        str(FACT_STANDARD),
                        str(FACT_BUILDER),
                    ],
                    generated_at=str(fact_navigation_meta.get("generated_at") or ""),
                    status=str(fact_navigation_meta.get("currentness_status") or "fact_navigation_cache_missing"),
                ),
                "owner_surface_command": "./repo-python kernel.py --facts --band cluster_flag",
                "check_command": "./repo-python tools/meta/factory/build_fact_hologram.py --check",
                "refresh_command": "./repo-python tools/meta/factory/build_fact_hologram.py",
                "meta_source": fact_navigation_meta.get("source"),
                "missing_generated_outputs": list(fact_navigation_meta.get("missing_generated_outputs") or []),
                "provider_error_count": int(fact_navigation_meta.get("provider_error_count") or 0),
            },
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                rung2="facts_command_supported",
                next_moves=[
                    "./repo-python kernel.py --facts --band cluster_flag",
                    "./repo-python kernel.py --facts --facts-tag banned --band flag",
                    "./repo-python kernel.py --facts --facts-tag stale --band flag",
                    "./repo-python kernel.py --fact-audit",
                ],
                omissions=[
                    "full fact ledger rows",
                    "raw provider payloads",
                    "private source bodies",
                    "mechanism execution semantics; mechanism refs are doctrine references only",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="python_files",
            title="Python Files",
            flag="Python files are selectable through flag/card rows backed by the existing std_python_scope_index.json projection; one row per repo-relative path.",
            row_count=int(python_meta.get("file_count") or 0),
            governing_standard_refs=[str(PYTHON_STANDARD), str(PYTHON_SCOPE_INDEX)],
            projection_refs=[str(PYTHON_SCOPE_INDEX), str(PYTHON_SYMBOLS)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface python_files --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface python_files --band card --ids <file_id>",
            evidence_command="./repo-python kernel.py --compile <file_id>",
            currentness=_currentness(
                source_refs=[str(PYTHON_SCOPE_INDEX), str(PYTHON_SYMBOLS)],
                generated_at=str(python_meta.get("generated_at") or ""),
                status="python_scope_index_option_surface_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface python_files --band cluster_flag",
                    "./repo-python kernel.py --option-surface python_files --band flag --ids codex/standards/std_python.py",
                    "./repo-python kernel.py --option-surface python_files --band card --ids codex/standards/std_python.py",
                    "./repo-python kernel.py --compile codex/standards/std_python.py",
                ],
                omissions=[
                    "full Python source bodies",
                    "all source spans and line-bounded body content",
                    "row-level file flags unless explicit --ids are supplied",
                    "native module_docs/file_card/symbol_capsule/graph_context/source_span bands are profile data, not option-surface adapter support",
                    "python_scopes expansion (per-symbol cards live on the python_scopes adapter when it lands)",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="python_scopes",
            title="Python Scopes",
            flag="Python functions, classes, and methods are selectable through flag/card rows backed by the existing std_python_scope_index.json projection; one row per scope keyed by symbol_id.",
            row_count=int(python_meta.get("scope_count") or 0),
            governing_standard_refs=[str(PYTHON_STANDARD), str(PYTHON_SCOPE_INDEX)],
            projection_refs=[str(PYTHON_SCOPE_INDEX), str(PYTHON_SYMBOLS)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface python_scopes --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface python_scopes --band card --ids <symbol_id>",
            evidence_command="jq --arg sid '<symbol_id>' '.scopes[] | select(.symbol_id==$sid)' codex/standards/std_python_scope_index.json",
            currentness=_currentness(
                source_refs=[str(PYTHON_SCOPE_INDEX), str(PYTHON_SYMBOLS)],
                generated_at=str(python_meta.get("generated_at") or ""),
                status="python_scope_index_option_surface_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface python_scopes --band cluster_flag",
                    "./repo-python kernel.py --option-surface python_scopes --band flag --ids codex/standards/std_python.py::StandardReference",
                    "./repo-python kernel.py --option-surface python_scopes --band card --ids codex/standards/std_python.py::StandardReference",
                    "./repo-python kernel.py --option-surface python_files --band card --ids codex/standards/std_python.py",
                ],
                omissions=[
                    "full Python source bodies",
                    "all source spans and line-bounded body content",
                    "row-level scope flags unless explicit --ids are supplied",
                    "complete callers/callees graph closure",
                    "cross-file dependency closure",
                    "native module_docs/file_card/symbol_capsule/graph_context/source_span bands are profile data, not option-surface adapter support",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="frontend_views",
            title="Frontend Views",
            flag="Frontend pages and view routes are selectable through cluster/flag/card rows backed by the existing navigation graph.",
            row_count=frontend_view_count,
            governing_standard_refs=["codex/doctrine/paper_modules/frontend_navigation_plane.md"],
            projection_refs=[str(FRONTEND_NAV_GRAPH)] if frontend_graph_exists else [],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface frontend_views --band cluster_flag",
            cluster_command="./repo-python kernel.py --option-surface frontend_views --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface frontend_views --band card --ids <view_id>",
            evidence_command="./repo-python kernel.py --view-graph",
            currentness=_currentness(
                source_refs=[str(FRONTEND_NAV_GRAPH)] if frontend_graph_exists else [],
                generated_at=str(frontend_graph.get("generated_at") or ""),
                status="frontend_navigation_graph_option_surface_available"
                if frontend_graph_exists
                else "frontend_navigation_graph_missing",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface frontend_views --band cluster_flag",
                    "./repo-python kernel.py --option-surface frontend_views --band flag --ids station,rootNavigator",
                    "./repo-python kernel.py --option-surface frontend_views --band card --ids station",
                    "./repo-python kernel.py --view station",
                ],
                omissions=[
                    "row-level frontend view flags outside selected clusters",
                    "full UI source bodies",
                    "full navigation graph edge list",
                    "render/capture artifact bodies and screenshots",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="frontend_components",
            title="Frontend Components",
            flag=(
                "React components extracted from system/server/ui/src are selectable through flag/card"
                " rows; row_count tracks high+medium-confidence primaries, with low-confidence candidates"
                " preserved as omitted receipts."
            ),
            row_count=int(frontend_component_meta.get("primary_count") or 0),
            governing_standard_refs=[str(FRONTEND_COMPONENT_STANDARD)],
            projection_refs=[str(FRONTEND_COMPONENT_INDEX), str(FRONTEND_COMPONENT_EXTRACTOR)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface frontend_components --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface frontend_components --band card --ids <component_id>",
            evidence_command=(
                "jq --arg cid '<component_id>' '.components[] | select(.component_id==$cid)' "
                "state/frontend_navigation/component_index.json"
            ),
            currentness=_currentness(
                source_refs=[str(FRONTEND_COMPONENT_INDEX), str(FRONTEND_COMPONENT_STANDARD)],
                generated_at=str(frontend_component_meta.get("generated_at") or ""),
                status="frontend_component_index_option_surface_available"
                if frontend_component_meta.get("available")
                else "frontend_component_index_missing",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface frontend_components --band cluster_flag",
                    "./repo-python kernel.py --option-surface frontend_components --band flag --ids system/server/ui/src/components/ArtifactViewer.tsx::ArtifactViewer",
                    "./repo-python kernel.py --option-surface frontend_components --band card --ids system/server/ui/src/components/ArtifactViewer.tsx::ArtifactViewer",
                    "./repo-python tools/meta/observability/frontend_component_index.py --check",
                ],
                omissions=[
                    "full TSX source bodies",
                    "complete prop and state contracts",
                    "view ownership / route attachment edges",
                    "low-confidence helper / constant exports (preserved as omitted candidates with receipts, not first-class component rows)",
                    "row-level component flags unless explicit --ids are supplied",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="skills",
            title="Skills",
            flag="Typed agent capabilities are selectable through a family-grouped flag/card option surface before legacy skill-find evidence drilldown.",
            row_count=_skill_count(root),
            governing_standard_refs=["codex/standards/std_skill.json", "codex/doctrine/skills/skill_registry.json"],
            projection_refs=[str(SKILL_REGISTRY)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface skills --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface skills --band card --ids <skill_id>",
            evidence_command="./repo-python kernel.py --skill-find profile_governed_compression --debug",
            currentness=_currentness(source_refs=[str(SKILL_REGISTRY)], status="registry_plus_file_mtime"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface skills --band cluster_flag",
                    "./repo-python kernel.py --option-surface skills --band flag --ids profile_governed_compression",
                    "./repo-python kernel.py --option-surface skills --band card --ids profile_governed_compression",
                    "./repo-python kernel.py --skill-find profile_governed_compression --debug",
                ],
                omissions=[
                    "native triggers/workflow/evidence skill bands are card data or source drilldown, not option-surface adapter support",
                    "full skill markdown bodies",
                    "transitive composes_with and doctrine-edge neighborhoods",
                ],
            ) if card_band else None,
        ),
        _row(
            kind_id="system_terms",
            title="System Terms",
            flag="Vocabulary rows expose authored definition ladders through a standard-owned flag/card option surface.",
            row_count=_list_count(root, SYSTEM_TERM_REGISTRY, "terms"),
            governing_standard_refs=[str(SYSTEM_TERM_STANDARD)],
            projection_refs=[str(SYSTEM_TERM_REGISTRY)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface system_terms --band flag",
            card_command="./repo-python kernel.py --option-surface system_terms --band card --ids <term_id>",
            evidence_command="./repo-python kernel.py --term living_system_posture --term-band context",
            currentness=_currentness(source_refs=[str(SYSTEM_TERM_REGISTRY)], status="authored_registry"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface system_terms --band flag",
                    "./repo-python kernel.py --option-surface system_terms --band card --ids living_system_posture",
                    "./repo-python kernel.py --term living_system_posture --term-band context",
                ],
                omissions=[
                    "native word/phrase/context/deep term bands are card data, not option-surface adapter support",
                    "full source bodies behind source_refs",
                    "second-order relationship closure",
                ],
            ) if card_band else None,
        ),
        _row(
            kind_id="principles",
            title="Principles",
            flag="Principle rows are browsable by native type with one-sentence descriptions before opening source authority.",
            row_count=_list_count(root, RAW_SEED_PRINCIPLES, "principles"),
            governing_standard_refs=["codex/standards/principles/std_raw_seed_principles.json"],
            projection_refs=[str(RAW_SEED_PRINCIPLES)],
            bands=["cluster_flag", "flag", "card", "tape"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface principles --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface principles --band card --ids <pri_id>",
            evidence_command="./repo-python kernel.py --docs-route raw_seed_principles",
            currentness=_currentness(source_refs=[str(RAW_SEED_PRINCIPLES)], status="authority_row_registry_available"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface principles --band cluster_flag",
                    "./repo-python kernel.py --option-surface principles --band flag --ids pri_014",
                    "./repo-python kernel.py --option-surface principles --band card --ids pri_014",
                    "./repo-python kernel.py --option-surface principles --band tape --ids pri_014",
                ],
                omissions=[
                    "full raw_seed_principles registry",
                    "raw-seed paragraph bodies",
                    "full reference_groups",
                    "row-level principle flags unless explicit --ids are supplied",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="teleologies",
            title="Shared Desire / Teleology Nodes",
            flag="Fewer shared desired-world nodes that many principles, anti-principles, axiom candidates, and anti-axioms point to.",
            row_count=_teleology_node_count(root),
            governing_standard_refs=[str(TELEOLOGY_NODE_STANDARD)],
            projection_refs=[str(TELEOLOGY_NODES), str(RAW_SEED_PRINCIPLES), str(SYSTEM_AXIOM_CANDIDATES)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface teleologies --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface teleologies --band card --ids <tel_id>",
            evidence_command="jq '.teleology_nodes[] | .id' codex/doctrine/teleology_nodes.json",
            currentness=_currentness(
                source_refs=[str(TELEOLOGY_NODES), str(TELEOLOGY_NODE_STANDARD)],
                status="shared_desire_registry_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface teleologies --band cluster_flag",
                    "./repo-python kernel.py --option-surface teleologies --band flag",
                    "./repo-python kernel.py --option-surface teleologies --band card --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface principles_by_teleology --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface anti_principles --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface anti_axioms --band flag --ids tel_navigation_orientation",
                ],
                omissions=[
                    "full principle and axiom cards",
                    "raw-seed paragraph bodies",
                    "source evidence bodies behind evidence_refs",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="principles_by_teleology",
            title="Principles By Teleology",
            flag="Crosswalk from shared desire nodes to positive principles and their anti-principle failure profiles.",
            row_count=_rows_with_string_list(root, RAW_SEED_PRINCIPLES, "principles", "teleology_refs"),
            governing_standard_refs=[str(TELEOLOGY_NODE_STANDARD), "codex/standards/principles/std_raw_seed_principles.json"],
            projection_refs=[str(TELEOLOGY_NODES), str(RAW_SEED_PRINCIPLES)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface principles_by_teleology --band flag",
            card_command="./repo-python kernel.py --option-surface principles_by_teleology --band card --ids <tel_id>",
            evidence_command="./repo-python kernel.py --option-surface teleologies --band card --ids <tel_id>",
            currentness=_currentness(
                source_refs=[str(TELEOLOGY_NODES), str(RAW_SEED_PRINCIPLES)],
                status="teleology_principle_crosswalk_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface principles_by_teleology --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface anti_principles --band flag --ids tel_navigation_orientation",
                ],
                omissions=["full raw_seed_principles registry", "full teleology node bodies outside selected ids"],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="anti_principles",
            title="Anti-Principles",
            flag="Negative-space failure profiles that share the parent principle teleology_refs exactly.",
            row_count=_rows_with_object(root, RAW_SEED_PRINCIPLES, "principles", "anti_principle"),
            governing_standard_refs=[str(TELEOLOGY_NODE_STANDARD), "codex/standards/principles/std_raw_seed_principles.json"],
            projection_refs=[str(RAW_SEED_PRINCIPLES), str(TELEOLOGY_NODES)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface anti_principles --band flag",
            card_command="./repo-python kernel.py --option-surface anti_principles --band card --ids <anti_principle_id>",
            evidence_command="./repo-python kernel.py --option-surface principles_by_teleology --band flag --ids <tel_id>",
            currentness=_currentness(
                source_refs=[str(RAW_SEED_PRINCIPLES), str(TELEOLOGY_NODES)],
                status="anti_principle_crosswalk_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface anti_principles --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface teleologies --band card --ids tel_navigation_orientation",
                ],
                omissions=["full positive principle cards", "raw-seed paragraph bodies"],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="anti_axioms",
            title="Anti-Axioms",
            flag="Constitutional failure profiles that share the parent axiom candidate teleology_refs exactly and route recovery.",
            row_count=_rows_with_object(root, SYSTEM_AXIOM_CANDIDATES, "axiom_candidates", "anti_axiom"),
            governing_standard_refs=[str(TELEOLOGY_NODE_STANDARD), "codex/standards/principles/std_system_axiom_candidate.json"],
            projection_refs=[str(SYSTEM_AXIOM_CANDIDATES), str(TELEOLOGY_NODES)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface anti_axioms --band flag",
            card_command="./repo-python kernel.py --option-surface anti_axioms --band card --ids <anti_axiom_id>",
            evidence_command="./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids <tel_id>",
            currentness=_currentness(
                source_refs=[str(SYSTEM_AXIOM_CANDIDATES), str(TELEOLOGY_NODES)],
                status="anti_axiom_crosswalk_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface anti_axioms --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface anti_axioms --band card --ids anti_axiom_candidate_availability_before_invention",
                    "./repo-python kernel.py --option-surface teleologies --band card --ids tel_navigation_orientation",
                ],
                omissions=["full positive axiom candidate tape rows", "raw-seed paragraph bodies"],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="concepts",
            title="Concepts",
            flag="Doctrine concepts are browsable through flag/card rows from codex/doctrine/concepts/*.json before opening source JSON.",
            row_count=_concept_count(root),
            governing_standard_refs=[str(CONCEPT_STANDARD)],
            projection_refs=[str(CONCEPT_DIR)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface concepts --band flag",
            card_command="./repo-python kernel.py --option-surface concepts --band card --ids <con_id>",
            evidence_command="jq '.' codex/doctrine/concepts/<con_file>.json",
            currentness=_currentness(source_refs=[str(CONCEPT_DIR), str(CONCEPT_STANDARD)], status="concept_json_option_surface_available"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface concepts --band flag",
                    "./repo-python kernel.py --option-surface concepts --band card --ids con_001",
                ],
                omissions=[
                    "full synthesis body",
                    "full reference_groups",
                    "transitive principle/mechanism neighborhoods",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="mechanisms",
            title="Mechanisms",
            flag="Doctrine mechanisms are browsable through flag/card rows from codex/doctrine/mechanisms/*.json before opening source JSON.",
            row_count=_mechanism_count(root),
            governing_standard_refs=[str(MECHANISM_STANDARD)],
            projection_refs=[str(MECHANISM_DIR)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface mechanisms --band flag",
            card_command="./repo-python kernel.py --option-surface mechanisms --band card --ids <mech_id>",
            evidence_command="jq '.' codex/doctrine/mechanisms/<mech_file>.json",
            currentness=_currentness(
                source_refs=[str(MECHANISM_DIR), str(MECHANISM_STANDARD)],
                status="mechanism_json_option_surface_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface mechanisms --band flag",
                    "./repo-python kernel.py --option-surface mechanisms --band card --ids mech_005",
                ],
                omissions=[
                    "full reference_groups",
                    "transitive concept/mechanism neighborhoods",
                    "full code context for code_loci",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="concept_mechanism_candidates",
            title="Concept/Mechanism Candidates",
            flag="Coverage metabolism rows route missing, stale, duplicated, or underconnected concept/mechanism work before authoring doctrine.",
            row_count=_concept_mechanism_candidate_count(root),
            governing_standard_refs=[
                str(CONCEPT_STANDARD),
                str(MECHANISM_STANDARD),
            ],
            projection_refs=[str(CONCEPT_MECHANISM_CANDIDATES)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface concept_mechanism_candidates --band flag",
            card_command="./repo-python kernel.py --option-surface concept_mechanism_candidates --band card --ids <candidate_id>",
            evidence_command="jq '.candidates[] | .candidate_id' codex/doctrine/concept_mechanism_candidates.json",
            currentness=_currentness(
                source_refs=[str(CONCEPT_MECHANISM_CANDIDATES), str(CONCEPT_DIR), str(MECHANISM_DIR)],
                status="coverage_metabolism_report_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python tools/meta/factory/build_concept_mechanism_candidates.py --report",
                    "./repo-python kernel.py --option-surface concept_mechanism_candidates --band flag",
                    "./repo-python kernel.py --option-surface concept_mechanism_candidates --band card --ids <candidate_id>",
                ],
                omissions=[
                    "final doctrine row content",
                    "full source artifact bodies",
                    "semantic embedding scores",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="concept_mechanism_candidate_curations",
            title="Concept/Mechanism Candidate Curations",
            flag="Completed concept/mechanism candidate decisions are browsable as curation receipts before reopening packet JSON.",
            row_count=_concept_mechanism_candidate_curation_count(root),
            governing_standard_refs=[
                str(CONCEPT_STANDARD),
                str(MECHANISM_STANDARD),
            ],
            projection_refs=[str(CONCEPT_MECHANISM_CANDIDATE_CURATION), str(CONCEPT_MECHANISM_CANDIDATES)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface concept_mechanism_candidate_curations --band flag",
            card_command="./repo-python kernel.py --option-surface concept_mechanism_candidate_curations --band card --ids <candidate_id>",
            evidence_command="jq '.packets[] | .candidate_id' codex/doctrine/concept_mechanism_candidate_curation.json",
            currentness=_currentness(
                source_refs=[str(CONCEPT_MECHANISM_CANDIDATE_CURATION), str(CONCEPT_MECHANISM_CANDIDATES)],
                status="curation_receipt_packet_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface concept_mechanism_candidate_curations --band flag",
                    "./repo-python kernel.py --option-surface concept_mechanism_candidate_curations --band card --ids cmc_concept_c05ecd7566",
                    "./repo-python tools/meta/factory/build_concept_mechanism_candidates.py --report",
                ],
                omissions=[
                    "full reopened evidence bodies",
                    "full source diff",
                    "unselected candidate report rows",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="axiom_candidates",
            title="Axiom Candidates",
            flag="Candidate constitutional compressions are browsable; tape surfaces per-layer budgets and population debt; not active doctrine.",
            row_count=_list_count(root, SYSTEM_AXIOM_CANDIDATES, "axiom_candidates"),
            governing_standard_refs=["codex/standards/principles/std_system_axiom_candidate.json"],
            projection_refs=[str(SYSTEM_AXIOM_CANDIDATES)],
            bands=["flag", "card", "tape", "context"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface axiom_candidates --band flag",
            card_command="./repo-python kernel.py --option-surface axiom_candidates --band card --ids <axiom_candidate_id>",
            evidence_command="jq '.axiom_candidates[].slug' 'obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json'",
            currentness=_currentness(source_refs=[str(SYSTEM_AXIOM_CANDIDATES)], status="candidate_registry_available"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface axiom_candidates --band flag",
                    "./repo-python kernel.py --option-surface axiom_candidates --band tape --ids axiom_candidate_operator_gesture_seed",
                ],
                omissions=["full Russian-doll chain in one packet", "full violation predicate set"],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="axioms_by_teleology",
            title="Axiom Candidates By Teleology",
            flag="Crosswalk from shared desire nodes to candidate axioms and anti-axiom failure profiles.",
            row_count=_rows_with_string_list(root, SYSTEM_AXIOM_CANDIDATES, "axiom_candidates", "teleology_refs"),
            governing_standard_refs=[str(TELEOLOGY_NODE_STANDARD), "codex/standards/principles/std_system_axiom_candidate.json"],
            projection_refs=[str(TELEOLOGY_NODES), str(SYSTEM_AXIOM_CANDIDATES)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface axioms_by_teleology --band flag",
            card_command="./repo-python kernel.py --option-surface axioms_by_teleology --band card --ids <tel_id>",
            evidence_command="./repo-python kernel.py --option-surface teleologies --band card --ids <tel_id>",
            currentness=_currentness(
                source_refs=[str(TELEOLOGY_NODES), str(SYSTEM_AXIOM_CANDIDATES)],
                status="teleology_axiom_crosswalk_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface anti_axioms --band flag --ids tel_navigation_orientation",
                    "./repo-python kernel.py --option-surface teleologies --band card --ids tel_navigation_orientation",
                ],
                omissions=["full axiom candidate tape rows", "raw-seed paragraph bodies"],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="imaginations",
            title="Imaginations",
            flag="Governed counterfactual affordance scenes (std_imagination_v1, field-set frozen). Rows expose status, migration lineage, and primary substrate seam; the source teleological_deliverables[] arrays are preserved per row contract.",
            row_count=_list_count(root, IMAGINATION_INDEX, "imaginations"),
            governing_standard_refs=["codex/standards/std_imagination.json"],
            projection_refs=[str(IMAGINATION_INDEX), "codex/doctrine/imaginations/_validation_report.json"],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface imaginations --band flag",
            card_command="./repo-python kernel.py --option-surface imaginations --band card --ids <imagination_id>",
            evidence_command="./repo-python kernel.py --imagination <imagination_id_or_slug>",
            currentness=_currentness(source_refs=[str(IMAGINATION_INDEX)], status="imagination_v1_field_set_frozen"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface imaginations --band flag",
                    "./repo-python kernel.py --option-surface imaginations --band card --ids imn_006_type_a_local_to_general_routing",
                    "./repo-python kernel.py --imagination-list",
                    "./repo-python kernel.py --imagination imn_006_type_a_local_to_general_routing",
                    "./repo-python kernel.py --imagination-find availability ladder",
                ],
                omissions=[
                    "full present-tense scene body (card emits a bounded excerpt)",
                    "full conversion_paths arrays (summarized at flag, listed in source markdown)",
                    "tape band (not implemented for imaginations v1; consider after operator review of v1)",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="raw_seed_shards",
            title="Raw Seed Shards",
            flag="Operator voice shard bins are selectable through flag/card rows backed by the generated raw_seed_shards projection.",
            row_count=_list_count(root, RAW_SEED_SHARDS, "shards"),
            governing_standard_refs=["codex/standards/observe_apply/std_raw_seed.md"],
            projection_refs=[str(RAW_SEED_SHARDS)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface raw_seed_shards --band flag",
            card_command="./repo-python kernel.py --option-surface raw_seed_shards --band card --ids <shard_id>",
            evidence_command="./repo-python kernel.py --shard <shard_id> --shards-source raw_seed",
            currentness=_currentness(source_refs=[str(RAW_SEED_SHARDS)], status="raw_seed_shards_option_surface_available"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface raw_seed_shards --band flag",
                    "./repo-python kernel.py --option-surface raw_seed_shards --band card --ids sh_00da19772a638cba",
                    "./repo-python kernel.py --shard sh_00da19772a638cba --shards-source raw_seed",
                ],
                omissions=[
                    "raw voice paragraph bodies",
                    "native context/deep profile bands are source drilldown data, not option-surface adapter support",
                    "full shard neighborhoods and route-review context",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="type_a_autonomous_seeds",
            title="Type A Autonomous Seeds",
            flag=(
                "Saved Type A autonomous seed JSON/markdown bundles are browseable by seed id, "
                "with owner, validation, currentness, and private-root disclosure routes."
            ),
            row_count=int(type_a_autonomous_seed_meta.get("seed_count") or 0),
            governing_standard_refs=[
                str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
                str(TYPE_A_AUTONOMOUS_SEED_SKILL),
                str(TYPE_A_AUTONOMOUS_SEED_MISSION),
            ],
            projection_refs=[str(TYPE_A_AUTONOMOUS_SEED_ROOT)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag",
            cluster_command="./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface type_a_autonomous_seeds --band card --ids <seed_id>",
            evidence_command="./repo-python kernel.py --raw-seed-autonomous-seed-bundle <seed_id>",
            currentness=_currentness(
                source_refs=[
                    str(TYPE_A_AUTONOMOUS_SEED_ROOT),
                    str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
                    str(TYPE_A_AUTONOMOUS_SEED_SKILL),
                    str(TYPE_A_AUTONOMOUS_SEED_MISSION),
                ],
                generated_at=str(type_a_autonomous_seed_meta.get("latest_seed_mtime") or ""),
                status=(
                    "type_a_autonomous_seed_bundles_available"
                    if type_a_autonomous_seed_meta.get("available")
                    else "type_a_autonomous_seed_bundles_missing"
                ),
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag",
                    "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band flag",
                    (
                        "./repo-python kernel.py --option-surface type_a_autonomous_seeds "
                        "--band card --ids system_atlas_crystal_architecture_comprehension"
                    ),
                    (
                        "./repo-python kernel.py --raw-seed-autonomous-seed-bundle "
                        "system_atlas_crystal_architecture_comprehension"
                    ),
                    "./repo-python kernel.py --raw-seed-autonomous-seeds 09",
                ],
                omissions=[
                    "raw_seed.md bodies",
                    "row-level autonomous seed flags outside selected clusters",
                    "full autonomous seed markdown bodies",
                    "operator chat and raw proof bodies",
                    "generated Atlas/Crystal/root coverage refresh output",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="external_benchmark_calibration",
            title="External Benchmark Calibration",
            flag=(
                "Formal-math external benchmark calibration routes are browseable through a compact owner card "
                "for VeriSoftBench micro-10, generated board/scorecard boundaries, provider-repair receipts, "
                "and disclosure posture."
            ),
            row_count=1 if external_benchmark_calibration_meta.get("available") else 0,
            governing_standard_refs=[
                "codex/doctrine/teleology_nodes.json::tel_ai_native_formal_math_laboratory",
                "codex/standards/std_compute_provider.json",
                "codex/standards/std_microcosm.json",
                str(SYSTEM_ATLAS_STANDARD),
            ],
            projection_refs=[
                str(EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD),
                str(EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST),
                str(EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD),
            ],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface external_benchmark_calibration --band flag",
            card_command=(
                "./repo-python kernel.py --option-surface external_benchmark_calibration "
                "--band card --ids verisoftbench_micro_10_calibration_spine_v1"
            ),
            evidence_command="./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check",
            currentness=_currentness(
                source_refs=[
                    str(EXTERNAL_BENCHMARK_CALIBRATION_BUILDER),
                    str(EXTERNAL_BENCHMARK_C_ARM_PROVIDER_REPAIR),
                    str(EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD),
                    str(EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST),
                    str(EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD),
                ],
                generated_at=str(external_benchmark_calibration_meta.get("generated_at") or ""),
                status=(
                    "external_benchmark_calibration_board_available_owner_check_required"
                    if external_benchmark_calibration_meta.get("available")
                    else "external_benchmark_calibration_board_missing"
                ),
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface external_benchmark_calibration --band flag",
                    (
                        "./repo-python kernel.py --option-surface external_benchmark_calibration "
                        "--band card --ids verisoftbench_micro_10_calibration_spine_v1"
                    ),
                    "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check",
                    (
                        "./repo-python tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py "
                        "--check --json"
                    ),
                ],
                omissions=[
                    "raw provider outputs",
                    "truth-side proof bodies",
                    "full Lean stdout/stderr bodies",
                    "official benchmark submission claims",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="compression_profiles",
            title="Compression Profiles",
            flag="Profiles declare creator/navigator band contracts and are selectable through a standard-owned flag/card option surface.",
            row_count=_compression_profile_count(root),
            governing_standard_refs=[str(COMPRESSION_PROFILES), str(PROFILE_SKILL)],
            projection_refs=[str(COMPRESSION_PROFILES)],
            bands=["flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface compression_profiles --band flag",
            card_command="./repo-python kernel.py --option-surface compression_profiles --band card --ids <profile_id>",
            evidence_command="./repo-python kernel.py --option-surface compression_profiles --band flag",
            currentness=_currentness(source_refs=[str(COMPRESSION_PROFILES)], status="profile_registry_available"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface compression_profiles --band flag",
                    "./repo-python kernel.py --option-surface compression_profiles --band card --ids raw_seed_voice_context_v1",
                ],
                omissions=[
                    "native context/deep profile bands are card data, not option-surface adapter support",
                    "full profile registry body",
                    "future profile rows if added later",
                ],
            ) if card_band else None,
        ),
        _row(
            kind_id="microcosm_extracted_patterns",
            title="Microcosm Extracted Patterns",
            flag=(
                "Macro-side distilled pattern rows for Microcosm reconstruction are selectable "
                "through cluster/flag/card rows backed by state/microcosm_portfolio/extracted_patterns_ledger.jsonl."
            ),
            row_count=_microcosm_extracted_pattern_count(root),
            governing_standard_refs=[
                str(MICROCOSM_EXTRACTED_PATTERN_SUBSTRATE_STANDARD),
                str(MICROCOSM_EXTRACTED_PATTERN_ROUTE_STANDARD),
            ],
            projection_refs=[
                str(MICROCOSM_EXTRACTED_PATTERN_LEDGER),
                str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
                str(MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT),
            ],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface microcosm_extracted_patterns --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface microcosm_extracted_patterns --band card --ids <pattern_id>",
            evidence_command="./repo-python kernel.py --option-surface microcosm_extracted_patterns --band flag",
            currentness=_currentness(
                source_refs=[
                    str(MICROCOSM_EXTRACTED_PATTERN_LEDGER),
                    str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
                    str(MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT),
                ],
                status="microcosm_extracted_pattern_option_surface_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface microcosm_extracted_patterns --band cluster_flag",
                    "./repo-python kernel.py --option-surface microcosm_extracted_patterns --band flag --ids navigation_hologram_unified_route_plane",
                    "./repo-python kernel.py --option-surface microcosm_extracted_patterns --band card --ids navigation_hologram_unified_route_plane",
                    "./repo-python tools/meta/factory/check_extracted_pattern_route_readiness.py",
                ],
                omissions=[
                    "full macro-private source bodies",
                    "public release or leaf projection authorization",
                    "full sidecar binding and readiness payloads",
                    "future reconstruction-pass output",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="annex_patterns",
            title="Annex Patterns",
            flag="Local annex annotations are selectable through flag/card rows backed by annex_notes.json files; one row per stable <slug>:<note_id>.",
            row_count=_annex_pattern_count(root),
            governing_standard_refs=["codex/standards/annex/annex_authority_index.json"],
            projection_refs=[str(ANNEX_ROOT), "annexes/annex_catalog.json"],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface annex_patterns --band card --ids <slug>:<note_id>",
            evidence_command="./repo-python kernel.py --option-surface annex_patterns --band flag --ids <slug>:<note_id>",
            currentness=_currentness(source_refs=[str(ANNEX_ROOT)], status="annex_notes_option_surface_available"),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
                    "./repo-python kernel.py --option-surface annex_patterns --band flag --ids llm-wiki:n001",
                    "./repo-python kernel.py --option-surface annex_patterns --band card --ids llm-wiki:n001",
                    "./repo-python kernel.py --annex-search llm-wiki",
                ],
                omissions=[
                    "external source repository bodies",
                    "row-level annex note flags unless explicit --ids are supplied",
                    "full annex_notes.json prose beyond bounded card excerpt",
                    "native family/contents/pattern_notes/source bands are profile data, not option-surface adapter support",
                    "transitive local transfer closure and runtime adoption decisions",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="annex_distillation_patterns",
            title="Annex Distillation Patterns",
            flag="Extracted annex adoption metadata is selectable through flag/card rows backed by distillation.json files; one row per stable <slug>:<pNNN>.",
            row_count=_annex_distillation_pattern_count(root),
            governing_standard_refs=["codex/standards/annex/annex_authority_index.json"],
            projection_refs=[str(ANNEX_ROOT)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface annex_distillation_patterns --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface annex_distillation_patterns --band card --ids <slug>:<pNNN>",
            evidence_command="./repo-python kernel.py --option-surface annex_distillation_patterns --band flag",
            currentness=_currentness(
                source_refs=[str(ANNEX_ROOT)],
                status="annex_distillation_option_surface_available",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python kernel.py --option-surface annex_distillation_patterns --band cluster_flag",
                    "./repo-python kernel.py --option-surface annex_distillation_patterns --band flag --ids agentic-stack:p001",
                    "./repo-python kernel.py --option-surface annex_distillation_patterns --band card --ids agentic-stack:p001",
                    "./repo-python kernel.py --annex-search agentic-stack",
                ],
                omissions=[
                    "external source repository bodies",
                    "row-level distillation flags unless explicit --ids are supplied",
                    "full distillation.json sibling metadata outside selected pattern rows",
                    "runtime proof that the local target still matches the extracted pattern",
                    "adoption status mutation or pattern landing",
                ],
            )
            if card_band
            else None,
        ),
        _row(
            kind_id="config_authorities",
            title="Config Authorities",
            flag=(
                "Federated read-only config plane over master_config, domain config files, "
                "runtime state, generated projections, host adapters, API routes, Settings, and config_ref consumers."
            ),
            row_count=int(config_authority_meta.get("row_count") or 0),
            governing_standard_refs=[str(CONFIG_AUTHORITY_STANDARD)],
            projection_refs=[str(CONFIG_AUTHORITY_REGISTRY)],
            bands=["cluster_flag", "flag", "card"],
            support_status="option_surface_supported",
            option_surface_command="./repo-python kernel.py --option-surface config_authorities --band cluster_flag",
            card_command="./repo-python kernel.py --option-surface config_authorities --band card --ids <config_id>",
            evidence_command="./repo-python tools/meta/factory/build_config_authority_registry.py --check",
            currentness=_currentness(
                source_refs=[str(CONFIG_AUTHORITY_REGISTRY), str(CONFIG_AUTHORITY_STANDARD), str(CONFIG_AUTHORITY_BUILDER)],
                generated_at=str(config_authority_meta.get("generated_at") or ""),
                status="config_authority_registry_available"
                if config_authority_meta.get("available")
                else "config_authority_registry_missing_or_unbuilt",
            ),
            profile_gap=None,
            card=_card_extra(
                rung1="option_surface_supported",
                next_moves=[
                    "./repo-python tools/meta/factory/build_config_authority_registry.py --check",
                    "./repo-python kernel.py --option-surface config_authorities --band cluster_flag",
                    "./repo-python kernel.py --option-surface config_authorities --band card --ids master_config.bridge",
                    "./repo-python kernel.py --docs-route \"master_config settings config authority registry config_ref effective config\"",
                ],
                omissions=[
                    "raw config values for host/private/secret-bearing surfaces",
                    "mutation routes",
                    "full file bodies outside selected card rows",
                ],
            )
            if card_band
            else None,
        ),
    ]
    if include_generated:
        # Wave_003B: append generated-artifact-surface rows from the small adapter
        # module so transform_job_receipts / row_patches / compliance_ledger /
        # standard_skill_map become first-class kind-atlas rows without sprawling
        # this builder. Per pri_133 and operator handoff 2026-04-28.
        try:
            from system.lib.kernel.commands.generated_artifact_surfaces import extra_kind_atlas_rows
            rows.extend(extra_kind_atlas_rows(root, band=band))
        except ImportError:
            pass
    return rows


def build_kind_atlas(
    repo_root: Path | str,
    *,
    band: str = "flag",
    ids: str | list[str] | tuple[str, ...] | None = None,
    query: str | None = None,
    fast: bool = False,
) -> dict[str, Any]:
    """Build a deterministic atlas of artifact kinds before keyword routing."""
    root = Path(repo_root)
    normalized_band = str(band or "flag").strip().lower()
    if normalized_band not in SUPPORTED_BANDS:
        normalized_band = "flag"
    normalized_query = str(query or "").strip()
    selected_ids: list[str] = []
    if isinstance(ids, str):
        selected_ids = [part for part in ids.replace(",", " ").split() if part]
    elif ids:
        selected_ids = [str(item).strip() for item in ids if str(item).strip()]

    fast_path = bool(fast and normalized_band == "flag")
    rows = _fast_rows_from_system_atlas(root) if fast_path else _build_rows(root, band=normalized_band)
    if fast_path and not rows:
        fast_path = False
        rows = _build_rows(root, band=normalized_band)
    rows_by_id = {row["kind_id"]: row for row in rows}
    if selected_ids:
        selected = [rows_by_id[item] for item in selected_ids if item in rows_by_id]
        missing_ids = [item for item in selected_ids if item not in rows_by_id]
    else:
        selected = rows
        missing_ids = []

    supported = [row for row in rows if row["support_status"] == "option_surface_supported"]
    gaps = [row for row in rows if row["support_status"] in {"projection_gap", "candidate_projection"}]
    legacy = [row for row in rows if row["support_status"] == "legacy_command_only"]
    next_moves = [
        {
            "command": "./repo-python kernel.py --kind-atlas --band flag",
            "reason": "Start from all visible artifact kinds without guessing a keyword.",
        },
        {
            "command": "./repo-python kernel.py --option-surface <kind_id> --band flag",
            "reason": "Drill into a supported kind's row set by kind id.",
        },
    ]
    if normalized_query:
        next_moves.insert(
            0,
            {
                "command": f"./repo-python kernel.py --context-pack {json.dumps(normalized_query)} --context-budget 12000",
                "reason": "Use task-conditioned context-pack for keyword or natural-language discovery.",
            },
        )

    return {
        "kind": "kind_atlas",
        "schema_version": "kind_atlas_v0",
        "generated_at": _utc_now(),
        "band": normalized_band,
        "selection": {
            "mode": "ids" if selected_ids else "all",
            "ids": selected_ids,
            "missing_ids": missing_ids,
            "query": normalized_query or None,
        },
        "profile_status": "supported",
        "projection_profile": "system_atlas_fast_rows" if fast_path else "live_source_rows",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {"ref": str(KIND_ATLAS_STANDARD), "owned_bands": ["flag", "card"]},
        "source_refs": [
            str(KIND_ATLAS_STANDARD),
            str(NAVIGATION_THEORY),
            str(PROFILE_SKILL),
            str(PAPER_MODULE_INDEX),
            str(STANDARDS_ROOT),
            str(PYTHON_SCOPE_INDEX),
            str(FRONTEND_NAV_GRAPH),
            str(SKILL_REGISTRY),
            str(SYSTEM_TERM_REGISTRY),
            str(SYSTEM_TERM_STANDARD),
            str(RAW_SEED_PRINCIPLES),
            str(SYSTEM_AXIOM_CANDIDATES),
            str(CONCEPT_MECHANISM_CANDIDATES),
            str(CONCEPT_MECHANISM_CANDIDATE_CURATION),
            str(RAW_SEED_SHARDS),
            str(FACT_STANDARD),
            str(FACT_NAVIGATION_CACHE),
            str(FACT_LEDGER),
            str(FACT_AUDIT),
            str(COMPRESSION_PROFILES),
            str(MICROCOSM_EXTRACTED_PATTERN_LEDGER),
            str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
            str(MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT),
            str(ANNEX_ROOT),
            str(ANNEX_ROOT / "*" / ANNEX_DISTILLATION_FILE_NAME),
        ],
        "summary": {
            "row_count": len(selected),
            "total_available": len(rows),
            "query_used": False,
            "query_received": bool(normalized_query),
            "query_handling": (
                "query accepted for CLI compatibility only; kind_atlas remains artifact-kind enumeration, "
                "not keyword search"
            )
            if normalized_query
            else "no query supplied; kind_atlas enumerates artifact kinds",
            "selection_method": "artifact_kind_enumeration",
            "supported_option_surface_count": len(supported),
            "legacy_command_only_count": len(legacy),
            "profile_gap_count": len(gaps),
            "fast_path": fast_path,
            "fast_path_source": str(SYSTEM_ATLAS_GRAPH) if fast_path else None,
        },
        "navigation_boundary": {
            "rung": 0,
            "surface_role": ATLAS_PROJECTION,
            "first_contact_allowed": False,
            "control_replacement": ENTRY_REPLACEMENT,
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "query_handling": "use --context-pack <query> for keyword discovery; then drill into --option-surface rows",
            "next_rung": "./repo-python kernel.py --option-surface <kind_id> --band flag",
            "non_goal": "This does not implement generic --row KIND:ID --band BAND.",
        },
        "rows": selected,
        "next": next_moves,
    }
