"""Read-only quotes for expensive repo control-plane actions.

The quote plane is deliberately not a scheduler. It composes existing owner
surfaces so an agent can decide whether to run, attach, defer, or use a cheaper
read model before paying command cost.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.command_run_singleflight import (
    _active_pending,
    _pid_alive,
    _short_hash,
    _state_paths,
    build_command_key,
)
from system.lib.admission_consumer import ADMISSION_CONSUMER_SCHEMA, ADMISSION_TEMPFAIL
from system.lib.latency_seed_digest import (
    build_git_maintenance_status,
    build_latency_seed_digest,
)
from system.lib import work_ledger_runtime
from system.lib.work_ledger_commands import (
    WORK_LEDGER_CLAIM_CARDS_COMMAND,
    WORK_LEDGER_FULL_CLAIMS_COMMAND,
    WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
)


SCHEMA_VERSION = "action_quote_v0"
CATALOG_SCHEMA_VERSION = "action_quote_catalog_v0"
SPEEDBOARD_REL = Path("state/performance/latency_speedboard.json")
PROCESS_SUMMARY_REL = Path("codex/hologram/process/summary.json")
ACTIVE_CLAIMS_REL = Path("state/work_ledger/active_claims_snapshot.json")
SESSION_YIELD_REQUESTS_REL = Path("state/performance/session_yield_requests.jsonl")
SESSION_YIELD_RESULTS_REL = Path("state/performance/session_yield_results.jsonl")
SESSION_YIELD_CONTROL_COMMAND = "./repo-python tools/meta/factory/work_ledger.py session-yield-control --limit 20"
SESSION_YIELD_PROCESSLESS_RANK_STATUSES = {
    "no_candidate_from_cached_claims",
    "pending_request_already_recorded",
}
LATENCY_SEED_DIGEST_COMMAND = "./repo-python kernel.py --latency-seed-digest"
LATENCY_SEED_DIGEST_NO_GIT_COMMAND = (
    "./repo-python kernel.py --latency-seed-digest --latency-seed-no-git"
)
GIT_MAINTENANCE_CHECK_COMMAND = "./repo-python tools/meta/control/git_gc_maintenance.py --check"
GIT_MAINTENANCE_REPAIR_COMMAND = (
    "./repo-python tools/meta/control/git_gc_maintenance.py --repair --min-tmp-age-seconds 120"
)
RUN_TEST_SLICE_REL = Path("tools/meta/testing/run_test_slice.py")
SELECT_IMPACTED_TESTS_REL = Path("tools/meta/testing/select_impacted_tests.py")
TEST_INVENTORY_TOOL_REL = Path("tools/meta/testing/test_inventory.py")
TEST_INVENTORY_REL = Path("state/testing/test_inventory.json")
TEST_IMPACT_MAP_REL = Path("codex/testing/test_impact_map.json")
FRONTEND_UI_DIR_REL = Path("system/server/ui")
FRONTEND_UI_PACKAGE_REL = FRONTEND_UI_DIR_REL / "package.json"
FRONTEND_UI_VITEST_CONFIG_REL = FRONTEND_UI_DIR_REL / "vitest.config.ts"
FRONTEND_VITEST_TOOL_REL = Path("tools/meta/testing/frontend_vitest.py")
ROOT_NAVIGATOR_TEST_REL = FRONTEND_UI_DIR_REL / "src/pages/__tests__/RootNavigator.test.tsx"
STATION_RENDER_TOOL_REL = Path("tools/meta/observability/station_render.py")
STATION_RENDER_MANIFEST_REL = Path("tools/meta/observability/station_views.json")
STATION_RENDER_LOAD_INDEX_REL = Path("state/observability/render_load_index.json")
PAPER_MODULE_INDEX_TOOL_REL = Path("tools/meta/factory/build_paper_module_index.py")
PAPER_MODULE_INDEX_REL = Path("codex/doctrine/paper_modules/_index.json")
PAPER_MODULE_VALIDATION_REL = Path("codex/doctrine/paper_modules/_validation_report.json")
PAPER_MODULE_ROUTE_COVERAGE_REL = Path("codex/doctrine/paper_modules/_route_coverage.json")
PAPER_MODULE_README_REL = Path("codex/doctrine/paper_modules/README.md")
GENERATED_STATE_DRAINER_REL = Path("tools/meta/control/generated_state_drainer.py")
TASK_LEDGER_APPLY_REL = Path("tools/meta/factory/task_ledger_apply.py")
TASK_LEDGER_VALIDATE_COMMAND = "./repo-python tools/meta/factory/task_ledger_apply.py validate"
TASK_LEDGER_VALIDATE_ALLOW_WARNINGS_COMMAND = f"{TASK_LEDGER_VALIDATE_COMMAND} --allow-warnings"
TASK_LEDGER_AUTHORITY_HEALTH_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py authority-health"
)
TASK_LEDGER_AUTHORITY_HEALTH_PROJECTION_CHECK_COMMAND = (
    f"{TASK_LEDGER_AUTHORITY_HEALTH_COMMAND} --projection-check"
)
TASK_LEDGER_REBUILD_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --ignore-host-pressure"
)
TASK_LEDGER_REBUILD_STATUS_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress"
)
TASK_LEDGER_QUICK_CAPTURE_COMMAND_SHAPE = (
    "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
    "--title '<title>' --summary '<summary>' --problem '<problem>' "
    "--impact '<impact>' --acceptance '<acceptance>' --created-by <agent> "
    "--confidence 0.85 --tag <tag> --projection-rebuild-policy off --compact"
)
STORAGE_DOCTOR_STATUS_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor scan --top 0 --format card"
)
STORAGE_DOCTOR_SAFE_CLEAN_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor clean --scope all --level safe "
    "--apply --yes --format card"
)
GENERATED_STATE_SETTLEMENT_OWNER_IDS = (
    "task_ledger_projection",
    "work_ledger_index_projection",
    "system_atlas_projection",
)
GENERATED_STATE_SETTLEMENT_REFRESH_ACTIONS = {
    "task_ledger_projection": "task_ledger_projection_refresh",
    "work_ledger_index_projection": "work_ledger_projection_refresh",
    "system_atlas_projection": "system_atlas_projection_refresh",
}
GENERATED_STATE_SETTLEMENT_OWNER_COMMAND = (
    "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --fast --compact"
)
GENERATED_STATE_SETTLEMENT_DRY_RUN_COMMAND = (
    "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run --fast-plan"
)
SCOPED_COMMIT_TOOL_REL = Path("tools/meta/control/scoped_commit.py")
SCOPED_COMMIT_MIN_FREE_BYTES_ENV = "AIW_SCOPED_COMMIT_MIN_FREE_BYTES"
SCOPED_COMMIT_MIN_FREE_BYTES_DEFAULT = 512 * 1024 * 1024
SCOPED_COMMIT_WRITE_ESTIMATE_FLOOR_BYTES = 64 * 1024 * 1024
SCOPED_COMMIT_WRITE_AMPLIFICATION = 2
SCOPED_COMMIT_STORAGE_SCAN_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor scan --top 20 --format card"
)
SCOPED_COMMIT_STORAGE_SAFE_CLEAN_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor clean --scope all --level safe "
    "--apply --yes --top 20 --format json"
)
ARTIFACT_DISCOVERY_ROOTS = (
    "docs/dissemination",
    "docs",
    "tools/meta/dissemination",
    "tools/meta",
    "tools/meta/control/market_snapshot.py",
    "tools/polymarket",
    "codex/configs",
    "codex/substrate/configs",
    "codex/standards",
    "codex/doctrine",
    "codex/doctrine/skills/dissemination",
    "codex/doctrine/paper_modules",
    "state/reports/market_feeds",
    "state/metabolism",
    "microcosm-substrate/atlas",
    "microcosm-substrate/core",
    "microcosm-substrate/organs",
    "microcosm-substrate/src",
    "microcosm-substrate/scripts",
    "microcosm-substrate/tests",
    "formal_math",
    "system",
    "system/lib/market_fusion_readiness.py",
    "system/lib/metabolism_market_clock.py",
    ".agents",
    "repo-python",
    "repo-pytest",
)
ARTIFACT_DISCOVERY_PRUNE_DIRS = {
    ".git",
    ".lake",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "raw_outputs",
    "tool-results",
    "paragraph_packets",
    "codex/hologram/raw",
    "tools/meta/control/runtime_hook_agent_observability.jsonl",
    "state/observability/agent_trace/events.jsonl",
    "state/runs",
    "state/observability/renders",
    "codex/doctrine/paper_modules/_index.json",
    "codex/doctrine/paper_modules/_route_coverage.json",
    "codex/doctrine/paper_modules/_validation_report.json",
}
ARTIFACT_DISCOVERY_RUNTIME_METADATA_FALLBACK_ROOTS = (
    "state/runs",
    "state/command_runs",
    "state/observability/agent_trace",
)
ARTIFACT_DISCOVERY_CONTENT_SUFFIXES = {
    ".json",
    ".js",
    ".jsx",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
ARTIFACT_DISCOVERY_CONTENT_MAX_BYTES = 512_000
ARTIFACT_DISCOVERY_CONTENT_LINE_PREVIEW_LIMIT = 5
ARTIFACT_DISCOVERY_SCAN_BUDGET_MS = 500
ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS = 100
ARTIFACT_DISCOVERY_DEFAULT_ROW_LIMIT = 24
ARTIFACT_DISCOVERY_DEFAULT_ROW_PREVIEW_LIMIT = 5
ARTIFACT_DISCOVERY_PATH_SCOPE_ROW_LIMIT = 12
ARTIFACT_DISCOVERY_COMMON_SCOPE_TERMS = {
    "codex",
    "data",
    "doc",
    "docs",
    "file",
    "files",
    "json",
    "lib",
    "log",
    "logs",
    "md",
    "meta",
    "py",
    "schema",
    "state",
    "system",
    "test",
    "tests",
    "tool",
    "tools",
}
ARTIFACT_DISCOVERY_PROSE_SCOPE_TERMS = {
    "a",
    "about",
    "above",
    "after",
    "an",
    "and",
    "around",
    "as",
    "before",
    "between",
    "by",
    "for",
    "from",
    "in",
    "into",
    "near",
    "of",
    "on",
    "or",
    "over",
    "the",
    "through",
    "to",
    "under",
    "with",
    "without",
}
ARTIFACT_DISCOVERY_WORKSPACE_PARENT_NAMES = {"src"}
ARTIFACT_DISCOVERY_WORKSPACE_FILENAME_SENTINELS = {
    "lake-manifest.json",
    "lakefile",
    "lakefile.lean",
    "lakefile.toml",
    "lean-toolchain",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pyproject.toml",
    "yarn.lock",
}
ARTIFACT_DISCOVERY_FILENAME_SHORT_CIRCUIT_TERMS = {
    "lake-manifest.json",
    "lakefile",
    "lakefile.lean",
    "lakefile.toml",
    "lean-toolchain",
}
ARTIFACT_DISCOVERY_KNOWN_CONTENT_OWNER_HINTS = {
    "raw_body_before_selection": (
        "system/lib/agent_execution_trace.py",
        "codex/standards/std_agent_execution_trace.json",
    ),
}
PROCESS_BOTTLENECK_OWNER_COMMAND = "./repo-python kernel.py --process-bottlenecks"
PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND = "./repo-python kernel.py --process-bottlenecks --force"
PROCESS_BOTTLENECK_REFRESH_COMMAND = "./repo-python tools/meta/factory/build_agent_execution_trace.py"
PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND = (
    "./repo-python tools/meta/factory/build_agent_execution_trace.py --limit 6"
)
PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND = (
    "./repo-python tools/meta/factory/build_agent_execution_trace.py --cached-summary --limit 6"
)
PROCESS_BOTTLENECK_CACHED_SUMMARY_CHECK_COMMAND = (
    "./repo-python tools/meta/factory/build_agent_execution_trace.py --cached-summary --check --limit 6"
)
CACHED_PROCESS_SUMMARY_PROBE_EXIT_CODE = 0
CACHED_PROCESS_SUMMARY_MISSING_EXIT_CODE = 1
PROCESS_SUMMARY_OWNER_COMMAND = "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"
PROCESS_SUMMARY_FORCE_LIVE_COMMAND = (
    "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest> --force --limit 6"
)
PROCESS_SUMMARY_REFRESH_COMMAND = "./repo-python tools/meta/factory/build_agent_execution_trace.py"
HOST_PRESSURE_FAST_COMMAND = (
    "./repo-python kernel.py --host-pressure --host-pressure-no-processes "
    "--host-pressure-compact --host-pressure-admission-only --host-pressure-event-limit 500"
)
HOST_PRESSURE_PROCESS_COMMAND = (
    "./repo-python kernel.py --host-pressure --host-pressure-event-limit 500"
)
HOST_PRESSURE_PROFILE_COMMAND = "./repo-python kernel.py --command-profile host-pressure"
HOST_PRESSURE_EVENT_LIMIT = 500
HOST_PRESSURE_PROCESS_AWARE_MODES = {
    "heavy_run",
    "projection",
    "helper_lease",
    "resident_relief",
    "resident_relief_escalation",
    "accepted_resident_relief",
}
GIT_STATE_SNAPSHOT_COMMAND = (
    "./repo-python tools/meta/control/git_state_snapshot.py "
    "--path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact"
)
GIT_DIFF_REVIEW_COMMAND = (
    "./repo-python tools/meta/control/git_state_snapshot.py --diff-review "
    "--path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact"
)
PROCESS_BOTTLENECK_STALE_AFTER_S = 600
WAIT_TAX_STALE_AFTER_S = 600
COMMAND_SURFACE_INVENTORY_ROOTS = (
    "tools/meta",
    "codex/hologram/process",
    "codex/standards",
    "codex/doctrine",
    "state/performance",
    "state/work_ledger",
    "state/command_runs",
    "state/agent_telemetry/process",
    "system/server/tests",
    "system/lib",
    ".agents",
    "docs",
    "repo-python",
    "repo-pytest",
)
COMMAND_SURFACE_INVENTORY_PATTERN = (
    r"agent_execution_trace|process[-_]?bottleneck|command[-_]?profile|"
    r"command_startup_profile|latency_speedboard|command_run_singleflight|"
    r"latency_seed_digest|navigation_metabolism_ledger|generated[-_]?state|"
    r"singleflight|action_quote|admission[-_]?consumer|host[-_]?pressure[-_]?admission|"
    r"admission[-_]?coverage|git_state_snapshot|git[-_]?gc[-_]?maintenance|compute_throughput|"
    r"command_trace|command[-_]?output[-_]?projection|process_summary|task_ledger_apply|"
    r"work_ledger|mission[-_]?transaction[-_]?preflight|observability|telemetry|proof|"
    r"portability_gate|test_inventory|frontend_vitest|build_system_atlas|build_paper_module_index|"
    r"paper_module_index|paper_modules/_index|paper_modules/_validation_report|"
    r"paper_modules/_route_coverage|station_render|render_load_index|run_test_slice|"
    r"diff[-_]?review|git[-_]?diff|scoped[-_]?commit|private[-_]?index"
    r"|select_impacted_tests|storage[-_]?doctor"
)
COMMAND_SURFACE_PRUNE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "raw_outputs",
    "tool-results",
    "paragraph_packets",
}
COMMAND_SURFACE_CANDIDATE_PATHS = (
    "tools/meta/control/action_quote.py",
    "tools/meta/control/git_state_snapshot.py",
    "tools/meta/control/git_gc_maintenance.py",
    "tools/meta/control/generated_state_drainer.py",
    "tools/meta/control/mission_transaction_preflight.py",
    "tools/meta/control/scoped_commit.py",
    "tools/meta/control/task_ledger_apply.py",
    "tools/meta/control/work_ledger.py",
    "tools/meta/storage_doctor.py",
    "tools/meta/factory/build_agent_execution_trace.py",
    "tools/meta/factory/build_compute_throughput_ledger.py",
    "tools/meta/factory/build_paper_module_index.py",
    "tools/meta/factory/build_system_atlas.py",
    "tools/meta/factory/task_ledger_apply.py",
    "tools/meta/factory/work_ledger.py",
    "tools/meta/observability/latency_speedboard.py",
    "tools/meta/observability/command_startup_profile.py",
    "tools/meta/observability/station_render.py",
    "tools/meta/observability/station_views.json",
    "tools/meta/testing/test_inventory.py",
    "tools/meta/testing/frontend_vitest.py",
    "tools/meta/testing/run_test_slice.py",
    "tools/meta/testing/select_impacted_tests.py",
    "tools/meta/dissemination/portability_gate.py",
    "tools/meta/dissemination/refresh_preflight_receipts.py",
    "tools/meta/dissemination/push_ai_workflow_proof_private.sh",
    "system/lib/action_quote.py",
    "system/lib/admission_consumer.py",
    "system/lib/command_run_singleflight.py",
    "system/lib/command_startup_profile.py",
    "system/lib/generated_state_drainer.py",
    "system/lib/latency_seed_digest.py",
    "system/lib/latency_speedboard.py",
    "system/lib/navigation_metabolism_ledger.py",
    "system/lib/mission_transaction_landing_preflight.py",
    "system/server/tests/test_action_quote.py",
    "system/server/tests/test_command_run_singleflight.py",
    "system/server/tests/test_command_startup_profile.py",
    "system/server/tests/test_latency_seed_digest.py",
    "system/server/tests/test_latency_speedboard.py",
    "system/server/tests/test_station_render.py",
    "system/server/tests/test_system_atlas.py",
    "codex/standards/std_agent_execution_trace.json",
    "codex/standards/std_command_output_projection.json",
    "codex/standards/std_paper_module.json",
    "codex/doctrine/paper_modules/_index.json",
    "codex/doctrine/paper_modules/_validation_report.json",
    "codex/doctrine/paper_modules/_route_coverage.json",
    "codex/hologram/process/summary.json",
    "codex/hologram/process/audit.json",
    "codex/hologram/process/ledger.json",
    "codex/hologram/process/patterns.json",
    "state/performance/latency_speedboard.json",
    "state/performance/latency_speedboard_measurements.jsonl",
    "state/observability/render_load_index.json",
    "state/work_ledger/active_claims_snapshot.json",
    "state/command_runs",
    "repo-python",
    "repo-pytest",
)
COMMAND_SURFACE_INVENTORY_RE = re.compile(COMMAND_SURFACE_INVENTORY_PATTERN, re.IGNORECASE)
COMMAND_SURFACE_MATCHING_CANDIDATE_PATHS = tuple(
    rel_text
    for rel_text in COMMAND_SURFACE_CANDIDATE_PATHS
    if COMMAND_SURFACE_INVENTORY_RE.search(rel_text)
)
COMMAND_SURFACE_INVENTORY_DEFAULT_LIMIT = 18
COMMAND_SURFACE_INVENTORY_FULL_LIMIT = 80
COMMAND_SURFACE_SCOPED_COMPACT_COMMANDS = (
    {
        "surface_id": "task_ledger_rebuild_check_status",
        "match_terms": (
            "task_ledger_apply.py rebuild",
            "task_ledger_apply rebuild",
            "rebuild --ignore-host-pressure",
        ),
        "canonical_command": (
            "./repo-python tools/meta/factory/task_ledger_apply.py rebuild "
            "--ignore-host-pressure"
        ),
        "compact_command": (
            "./repo-python tools/meta/factory/task_ledger_apply.py rebuild "
            "--status-only --quiet-progress"
        ),
        "replacement_command": (
            "./repo-python tools/meta/factory/task_ledger_apply.py rebuild "
            "--status-only --quiet-progress"
        ),
        "output_profile": "projection_freshness_check",
        "evidence_paths": (
            "tools/meta/factory/task_ledger_apply.py",
            "state/task_ledger/projection_manifest.json",
        ),
        "reason": (
            "Use the Task Ledger status-only projection check before paying for a full "
            "rebuild; avoid nonzero check exits and piped rebuild output for first-contact status."
        ),
    },
    {
        "surface_id": "microcosm_circuit_attribution_card",
        "match_terms": (
            "microcosm circuit-attribution",
            "microcosm_core circuit-attribution",
            "circuit-attribution",
        ),
        "canonical_command": (
            "cd microcosm-substrate && PYTHONPATH=src python3 -m microcosm_core "
            "circuit-attribution"
        ),
        "compact_command": (
            "cd microcosm-substrate && PYTHONPATH=src python3 -m microcosm_core "
            "circuit-attribution --card"
        ),
        "replacement_command": (
            "cd microcosm-substrate && PYTHONPATH=src python3 -m microcosm_core "
            "circuit-attribution --card"
        ),
        "output_profile": "command_card",
        "evidence_paths": (
            "microcosm-substrate/src/microcosm_core/runtime_shell.py",
            "microcosm-substrate/tests/test_cli.py",
        ),
        "reason": (
            "The runtime shell already exposes a compact card for the repeated "
            "circuit-attribution command; use it instead of piping full JSON through tail."
        ),
    },
    {
        "surface_id": "microcosm_doctrine_lattice_metadata_inventory",
        "match_terms": (
            "core/doctrine_lattice_coverage.json",
            "core/organ_atlas.json",
            "doctrine_lattice_coverage",
            "organ_atlas",
        ),
        "canonical_command": (
            "cd microcosm-substrate && python3 -c '<inline doctrine_lattice JSON probe>'"
        ),
        "compact_command": (
            "./repo-python kernel.py --artifact-discovery-inventory "
            "doctrine_lattice organ_atlas"
        ),
        "replacement_command": (
            "./repo-python kernel.py --artifact-discovery-inventory "
            "doctrine_lattice organ_atlas"
        ),
        "output_profile": "metadata_inventory",
        "evidence_paths": (
            "microcosm-substrate/core/doctrine_lattice_coverage.json",
            "microcosm-substrate/core/organ_atlas.json",
            "system/lib/action_quote.py",
        ),
        "reason": (
            "The artifact inventory route now covers Microcosm lattice and organ atlas "
            "metadata, so first-contact JSON probing should select rows there before "
            "opening bodies or assembling inline scripts."
        ),
    },
    {
        "surface_id": "process_summary_task_output_polling",
        "match_terms": (
            "task_output",
            "task-output",
            "tmp_task_output",
            "tmp task-output",
            "tool-result",
            "tool_result",
            "background_poll",
        ),
        "canonical_command": "grep/head/tail/read transient task-output or tool-result files",
        "compact_command": PROCESS_SUMMARY_OWNER_COMMAND,
        "replacement_command": PROCESS_SUMMARY_OWNER_COMMAND,
        "output_profile": "session_scoped_process_summary",
        "evidence_paths": (
            "codex/hologram/process/summary.json",
            "codex/hologram/process/audit.json",
            "system/lib/action_quote.py",
        ),
        "reason": (
            "Use the process-summary owner packet before polling or reading "
            "transient task-output/tool-result bodies; it exposes timing and output "
            "pressure without carrying raw stdout/stderr."
        ),
    },
    {
        "surface_id": "artifact_discovery_broad_raw_search",
        "match_terms": (
            "grep -r",
            "grep -i",
            "rg -n",
            "rg --files",
            "find ",
        ),
        "required_terms": (
            "state",
            "codex",
        ),
        "canonical_command": "grep/rg/find broad repo artifact roots before selecting owner route",
        "compact_command": "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
        "replacement_command": "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
        "output_profile": "artifact_metadata_inventory",
        "evidence_paths": (
            "system/lib/action_quote.py",
            "system/lib/kernel/commands/navigate.py",
        ),
        "reason": (
            "Use artifact-discovery-inventory before broad raw discovery across "
            "state/codex roots; it emits bounded metadata rows without opening "
            "artifact bodies."
        ),
    },
    {
        "surface_id": "artifact_discovery_generated_standard_raw_search",
        "match_terms": (
            "grep -r",
            "grep -i",
            "rg -n",
            "rg --files",
            "find ",
        ),
        "required_terms": ("codex/standards",),
        "canonical_command": "grep/rg/find generated standard projections before selecting owner route",
        "compact_command": "./repo-python kernel.py --artifact-discovery-inventory codex/standards",
        "replacement_command": "./repo-python kernel.py --artifact-discovery-inventory codex/standards",
        "output_profile": "artifact_metadata_inventory",
        "evidence_paths": (
            "system/lib/action_quote.py",
            "system/lib/kernel/commands/navigate.py",
        ),
        "reason": (
            "Use artifact-discovery-inventory before raw discovery across generated "
            "codex/standards projections; it emits bounded metadata rows instead of "
            "dumping generated projection bodies."
        ),
    },
    {
        "surface_id": "artifact_discovery_microcosm_raw_search",
        "match_terms": (
            "grep -r",
            "grep -i",
            "rg -n",
            "rg --files",
            "find ",
        ),
        "required_terms": ("microcosm-substrate",),
        "canonical_command": "grep/rg/find Microcosm artifact roots before selecting owner route",
        "compact_command": "./repo-python kernel.py --artifact-discovery-inventory microcosm-substrate",
        "replacement_command": "./repo-python kernel.py --artifact-discovery-inventory microcosm-substrate",
        "output_profile": "artifact_metadata_inventory",
        "evidence_paths": (
            "system/lib/action_quote.py",
            "system/lib/kernel/commands/navigate.py",
        ),
        "reason": (
            "Use artifact-discovery-inventory before raw Microcosm root scans; "
            "the inventory covers Microcosm roots and keeps first-contact output "
            "to path metadata."
        ),
    },
)
COMMAND_SURFACE_SCOPED_KERNEL_SURFACES = (
    {
        "surface_id": "kernel_session_diagnostics_summary",
        "surface": "session-diagnostics",
        "match_terms": (
            "session-diagnostics",
            "session diagnostics",
            "--session-diagnostics",
            "diagnostics-summary",
            "diagnostics summary",
        ),
        "scoped_help_command": "./repo-python kernel.py --session-diagnostics --help",
        "summary_command": (
            "./repo-python kernel.py --session-diagnostics --lens all --last 5 "
            "--store codex --json --diagnostics-summary"
        ),
        "full_fallback_command": (
            "./repo-python kernel.py --session-diagnostics --lens all --last 10 "
            "--store both --json"
        ),
        "output_profile": "summary_first_kernel_diagnostic",
        "evidence_paths": (
            "kernel.py",
            "tools/meta/observability/session_analyzer.py",
            "system/lib/kernel/commands/navigate.py",
        ),
        "reason": (
            "Session diagnostics has a summary-first route and scoped help; use "
            "--diagnostics-summary before paying for the full diagnostics payload."
        ),
    },
)
COMMAND_SURFACE_ACTION_HANDOFF_PREVIEW_IDS = (
    "repo_pytest_validation",
    "work_ledger_session_preflight",
    "work_ledger_heartbeat",
    "work_ledger_claim_read",
    "task_ledger_validate",
    "task_ledger_rebuild_status",
    "task_ledger_quick_capture",
    "storage_doctor_status",
    "process_bottleneck_triage",
    "process_summary_status",
    "document_read_economy",
    "kernel_output_economy",
    "destructive_shell_guard",
    "command_surface_inventory",
    "artifact_discovery_inventory",
    "git_object_store_status",
    "git_state_snapshot_status",
    "git_diff_review_context",
    "generated_state_settlement",
    "scoped_commit_private_index",
)
COMMAND_SURFACE_ACTION_HANDOFF_FULL_IDS = COMMAND_SURFACE_ACTION_HANDOFF_PREVIEW_IDS + (
    "helper_lease_admission",
    "resident_pressure_relief",
    "session_yield_request",
    "session_yield_result",
)
COMMAND_SURFACE_TRACE_REPAIR_ALIAS_IDS = (
    "test_or_build_command",
    "repo_tool_command",
    "quick-capture",
    "kernel_command",
    "bash_cat",
    "bash_grep",
    "bash_find",
    "bash_other",
    "unknown_tool",
    "task_tool",
    "exec_session_io",
    "git_state_shell_chain",
    "read_file",
)
HOST_PRESSURE_QUOTE_SOURCE = (
    "system/lib/host_pressure.py::build_progress_pressure_packet_from_store"
)
REPO_PYTEST_DISK_PRESSURE_QUOTE_SOURCE = "repo-pytest::disk_pressure_admission_gate"
REPO_PYTEST_MIN_TMP_FREE_BYTES_ENV_VAR = "AIW_REPO_PYTEST_MIN_TMP_FREE_BYTES"
REPO_PYTEST_HEAVY_MIN_TMP_FREE_BYTES_ENV_VAR = "AIW_REPO_PYTEST_HEAVY_MIN_TMP_FREE_BYTES"
REPO_PYTEST_DEFAULT_MIN_TMP_FREE_BYTES = 2 * 1024 * 1024 * 1024
REPO_PYTEST_DEFAULT_HEAVY_MIN_TMP_FREE_BYTES = 8 * 1024 * 1024 * 1024
REPO_PYTEST_STORAGE_SCAN_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor scan --top 6 --format card"
)
REPO_PYTEST_STORAGE_FULL_REPORT_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor scan --top 0 "
    "--include-inspect-only --format json --write-report"
)
REPO_PYTEST_STORAGE_SAFE_CLEAN_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor clean --scope all --level safe --apply --yes"
)
REPO_PYTEST_STORAGE_OWNER_CHECKED_REPO_CACHE_DRY_RUN_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor clean --scope repo --level caution "
    "--id repo_node_modules --owner-check-completed --format card"
)
REPO_PYTEST_STORAGE_OWNER_CHECKED_REPO_CACHE_APPLY_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor clean --scope repo --level caution "
    "--id repo_node_modules --owner-check-completed --apply --yes --format json"
)
REPO_PYTEST_STORAGE_OWNER_CHECKED_ANNEX_CLONE_DRY_RUN_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor clean --scope repo --level caution "
    "--id repo_annex_source_clones --owner-check-completed --format card"
)
REPO_PYTEST_STORAGE_OWNER_CHECKED_ANNEX_CLONE_APPLY_COMMAND = (
    "./repo-python -m tools.meta.storage_doctor clean --scope repo --level caution "
    "--id repo_annex_source_clones --owner-check-completed --apply --yes --format json"
)
REPO_PYTEST_STORAGE_OUTPUT_PROFILE = "first_contact_top6_use_full_report_for_owner_policy"
REPO_PYTEST_SINGLE_FILE_SINGLEFLIGHT_MIN_SECONDS = 30.0
HOST_PRESSURE_ADMISSION_BY_ACTION: dict[str, dict[str, str]] = {
    "repo_pytest_validation": {
        "workload_class": "test_build",
        "mode": "heavy_run",
        "shed_recommendation": "queue_validation_until_host_pressure_clears",
        "pressure_recheck_command": HOST_PRESSURE_FAST_COMMAND,
    },
    "frontend_vitest_validation": {
        "workload_class": "test_build",
        "mode": "heavy_run",
        "shed_recommendation": "queue_validation_until_host_pressure_clears",
        "pressure_recheck_command": HOST_PRESSURE_FAST_COMMAND,
    },
    "latency_seed_preflight": {
        "workload_class": "mixed_realistic",
        "mode": "coordination",
        "shed_recommendation": "use_summary_first_and_defer_new_parallel_work",
        "pressure_safe_suggested_command": LATENCY_SEED_DIGEST_NO_GIT_COMMAND,
        "pressure_safe_action": "use_pressure_safe_latency_seed_digest",
    },
    "process_bottleneck_triage": {
        "workload_class": "repo_wide_search",
        "mode": "diagnostic_drilldown",
        "shed_recommendation": "use_cached_summary_defer_force_live_until_pressure_clears",
        "pressure_safe_fallback_command": LATENCY_SEED_DIGEST_NO_GIT_COMMAND,
        "pressure_safe_fallback_action": (
            "use_pressure_safe_latency_seed_digest_if_process_summary_missing"
        ),
    },
    "process_summary_status": {
        "workload_class": "repo_wide_search",
        "mode": "diagnostic_drilldown",
        "shed_recommendation": "use_cached_summary_defer_force_live_until_pressure_clears",
        "pressure_safe_fallback_command": LATENCY_SEED_DIGEST_NO_GIT_COMMAND,
        "pressure_safe_fallback_action": (
            "use_pressure_safe_latency_seed_digest_if_process_summary_missing"
        ),
    },
    "exec_session_wait_tax": {
        "workload_class": "repo_wide_search",
        "mode": "diagnostic_drilldown",
        "shed_recommendation": "use_cached_summary_defer_force_live_until_pressure_clears",
        "pressure_safe_fallback_command": LATENCY_SEED_DIGEST_NO_GIT_COMMAND,
        "pressure_safe_fallback_action": (
            "use_pressure_safe_latency_seed_digest_if_process_summary_missing"
        ),
    },
    "station_render_capture": {
        "workload_class": "test_build",
        "mode": "heavy_run",
        "shed_recommendation": "queue_capture_until_host_pressure_clears",
        "pressure_recheck_command": HOST_PRESSURE_FAST_COMMAND,
    },
    "paper_module_index": {
        "workload_class": "background_projection",
        "mode": "projection",
        "shed_recommendation": "queue_projection_until_host_pressure_clears",
        "pressure_recheck_command": HOST_PRESSURE_FAST_COMMAND,
    },
    "generated_state_settlement": {
        "workload_class": "background_projection",
        "mode": "projection",
        "shed_recommendation": "queue_generated_state_settlement_until_host_pressure_clears",
        "pressure_recheck_command": HOST_PRESSURE_FAST_COMMAND,
    },
    "helper_lease_admission": {
        "workload_class": "mixed_realistic",
        "mode": "helper_lease",
        "shed_recommendation": "queue_helper_lease_until_pressure_clears",
    },
    "resident_pressure_relief": {
        "workload_class": "mixed_realistic",
        "mode": "resident_relief",
        "shed_recommendation": "request_owner_release_or_background_downshift",
    },
    "session_yield_request": {
        "workload_class": "mixed_realistic",
        "mode": "resident_relief_escalation",
        "shed_recommendation": "request_session_yield_or_tool_release",
    },
    "session_yield_result": {
        "workload_class": "mixed_realistic",
        "mode": "accepted_resident_relief",
        "shed_recommendation": "close_owner_yield_with_accepted_or_unsupported_result",
    },
}

ADMISSION_CONSUMER_COVERAGE: dict[str, dict[str, Any]] = {
    "repo_pytest_validation": {
        "status": "protected_launcher",
        "consumer_surface": "./repo-pytest",
        "action_class": "new_heavy_work",
        "policy_surface": "--host-pressure-policy / --ignore-host-pressure",
        "override_surfaces": ["--host-pressure-policy=warn", "--ignore-host-pressure"],
        "receipt_schema": "command_admission_receipt_v1",
        "helper_surface": "repo-pytest local guard",
    },
    "station_render_capture": {
        "status": "protected_shared_launcher",
        "consumer_surface": "./repo-python -m tools.meta.observability.station_render render",
        "action_class": "new_heavy_work",
        "policy_surface": "--host-pressure-policy / --ignore-host-pressure / AIW_STATION_RENDER_HOST_PRESSURE_POLICY",
        "override_surfaces": ["--host-pressure-policy=warn", "--ignore-host-pressure"],
        "receipt_schema": ADMISSION_CONSUMER_SCHEMA,
        "helper_surface": "system/lib/admission_consumer.py",
    },
    "frontend_vitest_validation": {
        "status": "protected_shared_launcher",
        "consumer_surface": "./repo-python tools/meta/testing/frontend_vitest.py",
        "action_class": "new_heavy_work",
        "policy_surface": "--host-pressure-policy / --ignore-host-pressure / AIW_FRONTEND_VITEST_HOST_PRESSURE_POLICY",
        "override_surfaces": ["--host-pressure-policy=warn", "--ignore-host-pressure"],
        "receipt_schema": ADMISSION_CONSUMER_SCHEMA,
        "helper_surface": "system/lib/admission_consumer.py",
        "admission_action": "queue_until_pressure_clears",
    },
    "latency_seed_preflight": {
        "status": "advisory_read_model",
        "consumer_surface": "./repo-python kernel.py --latency-seed-digest",
        "action_class": "coordination",
        "policy_surface": None,
        "override_surfaces": [],
        "receipt_schema": None,
        "helper_surface": None,
        "admission_action": "defer_new_parallel_work",
    },
    "process_bottleneck_triage": {
        "status": "summary_first_diagnostic",
        "consumer_surface": "./repo-python kernel.py --process-bottlenecks",
        "action_class": "force_live_drilldown",
        "policy_surface": None,
        "override_surfaces": [],
        "receipt_schema": None,
        "helper_surface": None,
        "admission_action": "use_cached_summary",
    },
    "process_summary_status": {
        "status": "summary_first_diagnostic",
        "consumer_surface": PROCESS_SUMMARY_OWNER_COMMAND,
        "action_class": "force_live_drilldown",
        "policy_surface": None,
        "override_surfaces": [],
        "receipt_schema": None,
        "helper_surface": None,
        "admission_action": "use_cached_summary",
    },
    "exec_session_wait_tax": {
        "status": "summary_first_diagnostic",
        "consumer_surface": "./repo-python kernel.py --process-bottlenecks",
        "action_class": "force_live_drilldown",
        "policy_surface": None,
        "override_surfaces": [],
        "receipt_schema": None,
        "helper_surface": None,
        "admission_action": "use_cached_summary",
    },
    "paper_module_index": {
        "status": "protected_projection_builder",
        "consumer_surface": "./repo-python tools/meta/factory/build_paper_module_index.py",
        "action_class": "projection_builder",
        "policy_surface": "--host-pressure-policy / --ignore-host-pressure / AIW_PAPER_MODULE_INDEX_HOST_PRESSURE_POLICY",
        "override_surfaces": ["--host-pressure-policy=warn", "--ignore-host-pressure"],
        "receipt_schema": ADMISSION_CONSUMER_SCHEMA,
        "helper_surface": "system/lib/admission_consumer.py",
        "admission_action": "queue_until_pressure_clears",
    },
    "generated_state_settlement": {
        "status": "protected_generated_state_settlement",
        "consumer_surface": "./repo-python tools/meta/control/generated_state_drainer.py settle",
        "action_class": "generated_projection_owner_settlement",
        "policy_surface": "action_quote before generated_state_drainer settlement; owner drainer singleflight for execution",
        "override_surfaces": [],
        "receipt_schema": "generated_projection_settlement_v0",
        "helper_surface": "tools/meta/control/generated_state_drainer.py",
        "admission_action": "queue_until_pressure_clears",
    },
    "helper_lease_admission": {
        "status": "protected_helper_lease_budget",
        "consumer_surface": "./repo-python tools/meta/factory/work_ledger.py helper-lease-admission",
        "action_class": "persistent_helper_lease",
        "policy_surface": "--host-pressure-policy / AIW_HELPER_LEASE_HOST_PRESSURE_POLICY",
        "override_surfaces": ["--host-pressure-policy=warn", "--host-pressure-policy=off"],
        "receipt_schema": "helper_lease_admission_receipt_v1",
        "helper_surface": "system/lib/work_admission.py",
        "admission_action": "queue_until_pressure_clears",
    },
    "resident_pressure_relief": {
        "status": "protected_resident_relief_request",
        "consumer_surface": "./repo-python tools/meta/factory/work_ledger.py resident-pressure-relief",
        "action_class": "resident_pressure_relief",
        "policy_surface": "resident-pressure-relief owner-release/background-downshift receipts",
        "override_surfaces": [],
        "receipt_schema": "resident_pressure_relief_window_v1",
        "helper_surface": "system/lib/work_admission.py",
        "admission_action": "owner_release_or_background_downshift",
    },
    "session_yield_request": {
        "status": "protected_owner_yield_request_bus",
        "consumer_surface": "./repo-python tools/meta/factory/work_ledger.py session-yield-request",
        "action_class": "resident_pressure_relief",
        "policy_surface": "session-yield-request owner-visible JSONL request bus",
        "override_surfaces": [],
        "receipt_schema": "session_yield_request_receipt_v1",
        "helper_surface": "system/lib/work_admission.py",
        "admission_action": "owner_visible_yield_or_tool_release_request",
    },
    "session_yield_result": {
        "status": "protected_owner_yield_result_bus",
        "consumer_surface": "./repo-python tools/meta/factory/work_ledger.py session-yield-result",
        "action_class": "accepted_resident_relief",
        "policy_surface": "session-yield-result accepted/applied owner result bus",
        "override_surfaces": [],
        "receipt_schema": "owner_yield_result_receipt_v1",
        "helper_surface": "system/lib/work_admission.py",
        "admission_action": "accepted_or_applied_resident_relief",
    },
}

ACTION_ALIASES = {
    "pytest": "repo_pytest_validation",
    "repo-pytest": "repo_pytest_validation",
    "repo_pytest": "repo_pytest_validation",
    "build_command": "repo_pytest_validation",
    "test_build_command": "repo_pytest_validation",
    "test_or_build_command": "repo_pytest_validation",
    "validation_or_build": "repo_pytest_validation",
    "latency": "latency_seed_preflight",
    "latency_seed": "latency_seed_preflight",
    "latency_speedboard": "latency_seed_preflight",
    "latency-speedboard": "latency_seed_preflight",
    "claims": "work_ledger_claim_read",
    "work_ledger_claims": "work_ledger_claim_read",
    "work_ledger": "work_ledger_session_preflight",
    "work-ledger": "work_ledger_session_preflight",
    "work_ledger_session": "work_ledger_session_preflight",
    "work-ledger-session": "work_ledger_session_preflight",
    "work_ledger_preflight": "work_ledger_session_preflight",
    "work-ledger-preflight": "work_ledger_session_preflight",
    "session_preflight": "work_ledger_session_preflight",
    "session-preflight": "work_ledger_session_preflight",
    "session_start": "work_ledger_session_preflight",
    "session-start": "work_ledger_session_preflight",
    "session_bootstrap": "work_ledger_session_preflight",
    "session-bootstrap": "work_ledger_session_preflight",
    "heartbeat": "work_ledger_heartbeat",
    "session_heartbeat": "work_ledger_heartbeat",
    "session-heartbeat": "work_ledger_heartbeat",
    "work_ledger_heartbeat": "work_ledger_heartbeat",
    "work-ledger-heartbeat": "work_ledger_heartbeat",
    "current_pass": "work_ledger_heartbeat",
    "current-pass": "work_ledger_heartbeat",
    "task_ledger_validate": "task_ledger_validate",
    "task-ledger-validate": "task_ledger_validate",
    "validate_task_ledger": "task_ledger_validate",
    "validate-task-ledger": "task_ledger_validate",
    "task_ledger_validation": "task_ledger_validate",
    "task-ledger-validation": "task_ledger_validate",
    "task_ledger_rebuild": "task_ledger_rebuild_status",
    "task-ledger-rebuild": "task_ledger_rebuild_status",
    "task_ledger_rebuild_status": "task_ledger_rebuild_status",
    "task-ledger-rebuild-status": "task_ledger_rebuild_status",
    "task_ledger_capture": "task_ledger_quick_capture",
    "task-ledger-capture": "task_ledger_quick_capture",
    "task_ledger_quick_capture": "task_ledger_quick_capture",
    "task-ledger-quick-capture": "task_ledger_quick_capture",
    "quick_capture": "task_ledger_quick_capture",
    "quick-capture": "task_ledger_quick_capture",
    "capture": "task_ledger_quick_capture",
    "task_capture": "task_ledger_quick_capture",
    "task-capture": "task_ledger_quick_capture",
    "storage_doctor": "storage_doctor_status",
    "storage-doctor": "storage_doctor_status",
    "storage_doctor_status": "storage_doctor_status",
    "storage-doctor-status": "storage_doctor_status",
    "storage_cleanup": "storage_doctor_status",
    "storage-cleanup": "storage_doctor_status",
    "repo_tool": "task_ledger_rebuild_status",
    "repo_tool_command": "task_ledger_rebuild_status",
    "process": "process_bottleneck_triage",
    "process_bottlenecks": "process_bottleneck_triage",
    "process_summary": "process_summary_status",
    "process-summary": "process_summary_status",
    "process_status": "process_summary_status",
    "task_output": "process_summary_status",
    "task_output_poll": "process_summary_status",
    "task_tool": "process_summary_status",
    "tool_result": "process_summary_status",
    "tool-result": "process_summary_status",
    "tmp_task_output": "process_summary_status",
    "background_poll": "process_summary_status",
    "unknown_tool": "process_summary_status",
    "bash_cat": "document_read_economy",
    "read_file": "document_read_economy",
    "readfile": "document_read_economy",
    "full_doc_read": "document_read_economy",
    "full_document_read": "document_read_economy",
    "whole_file_read": "document_read_economy",
    "whole_doc_read": "document_read_economy",
    "document_read": "document_read_economy",
    "doc_read": "document_read_economy",
    "kernel_command": "kernel_output_economy",
    "kernel_output": "kernel_output_economy",
    "kernel_output_limiter": "kernel_output_economy",
    "kernel_limiter": "kernel_output_economy",
    "entry_limiter": "kernel_output_economy",
    "context_pack_limiter": "kernel_output_economy",
    "truncated_kernel": "kernel_output_economy",
    "configured_wait": "exec_session_wait_tax",
    "exec_session": "exec_session_wait_tax",
    "exec_session_io": "exec_session_wait_tax",
    "session_wait": "exec_session_wait_tax",
    "write_stdin": "exec_session_wait_tax",
    "vitest": "frontend_vitest_validation",
    "frontend_test": "frontend_vitest_validation",
    "frontend_validation": "frontend_vitest_validation",
    "rootnavigator": "frontend_vitest_validation",
    "station_render": "station_render_capture",
    "station-render": "station_render_capture",
    "render": "station_render_capture",
    "screenshot": "station_render_capture",
    "paper_module": "paper_module_index",
    "paper_modules": "paper_module_index",
    "paper-module-index": "paper_module_index",
    "paper_module_builder": "paper_module_index",
    "build_paper_module_index": "paper_module_index",
    "generated_state": "generated_state_settlement",
    "generated-state": "generated_state_settlement",
    "generated_state_settlement": "generated_state_settlement",
    "generated-state-settlement": "generated_state_settlement",
    "generated_projection_settlement": "generated_state_settlement",
    "projection_settlement": "generated_state_settlement",
    "generated_state_drainer": "generated_state_settlement",
    "generated-state-drainer": "generated_state_settlement",
    "task_ledger_projection": "generated_state_settlement",
    "work_ledger_index_projection": "generated_state_settlement",
    "system_atlas_projection": "generated_state_settlement",
    "scoped_commit": "scoped_commit_private_index",
    "scoped-commit": "scoped_commit_private_index",
    "private_index_commit": "scoped_commit_private_index",
    "private-index-commit": "scoped_commit_private_index",
    "scoped_commit_disk": "scoped_commit_private_index",
    "commit_headroom": "scoped_commit_private_index",
    "scoped_commit_full_paths": "scoped_commit_private_index",
    "helper_lease": "helper_lease_admission",
    "helper_lease_admission": "helper_lease_admission",
    "tool_lease": "helper_lease_admission",
    "playwright_mcp": "helper_lease_admission",
    "codex_stdio_app_server": "helper_lease_admission",
    "mcp_helper": "helper_lease_admission",
    "resident_pressure": "resident_pressure_relief",
    "resident_pressure_relief": "resident_pressure_relief",
    "owner_release": "resident_pressure_relief",
    "background_downshift": "resident_pressure_relief",
    "relief_window": "resident_pressure_relief",
    "session_yield": "session_yield_request",
    "session_yield_request": "session_yield_request",
    "yield_request": "session_yield_request",
    "tool_release": "session_yield_request",
    "owner_yield": "session_yield_request",
    "session_yield_result": "session_yield_result",
    "yield_result": "session_yield_result",
    "owner_yield_result": "session_yield_result",
    "accepted_resident_relief": "session_yield_result",
    "diff": "git_diff_review_context",
    "git_diff": "git_diff_review_context",
    "git-diff": "git_diff_review_context",
    "full_diff": "git_diff_review_context",
    "diff_review": "git_diff_review_context",
    "review_diff": "git_diff_review_context",
    "diff_context": "git_diff_review_context",
    "git_diff_review": "git_diff_review_context",
    "git_status": "git_state_snapshot_status",
    "git_state": "git_state_snapshot_status",
    "git_state_shell_chain": "git_state_snapshot_status",
    "dirty_tree": "git_state_snapshot_status",
    "git_snapshot": "git_state_snapshot_status",
    "bash_other": "bash_other_economy",
    "destructive_shell": "destructive_shell_guard",
    "destructive-shell": "destructive_shell_guard",
    "destructive_shell_guard": "destructive_shell_guard",
    "destructive-shell-guard": "destructive_shell_guard",
    "rm_rf": "destructive_shell_guard",
    "rm-rf": "destructive_shell_guard",
    "command_surfaces": "command_surface_inventory",
    "command_surface": "command_surface_inventory",
    "command_telemetry": "command_surface_inventory",
    "inline_python": "command_surface_inventory",
    "inline_python_data_probe": "command_surface_inventory",
    "python_inline": "command_surface_inventory",
    "python_inline_data_probe": "command_surface_inventory",
    "telemetry_inventory": "command_surface_inventory",
    "artifact_discovery": "artifact_discovery_inventory",
    "artifact_inventory": "artifact_discovery_inventory",
    "artifact_surfaces": "artifact_discovery_inventory",
    "bounded_search": "artifact_discovery_inventory",
    "bounded_grep": "artifact_discovery_inventory",
    "broad_discovery": "artifact_discovery_inventory",
    "broad_search": "artifact_discovery_inventory",
    "content_search": "artifact_discovery_inventory",
    "file_discovery": "artifact_discovery_inventory",
    "find_files": "artifact_discovery_inventory",
    "grep": "artifact_discovery_inventory",
    "bash_grep": "artifact_discovery_inventory",
    "bash_find": "artifact_discovery_inventory",
    "raw_grep": "artifact_discovery_inventory",
    "raw_find": "artifact_discovery_inventory",
    "raw_rg": "artifact_discovery_inventory",
    "raw_search": "artifact_discovery_inventory",
    "recursive_grep": "artifact_discovery_inventory",
    "repo_grep": "artifact_discovery_inventory",
    "repo_search": "artifact_discovery_inventory",
    "rg": "artifact_discovery_inventory",
    "rg_search": "artifact_discovery_inventory",
    "ripgrep": "artifact_discovery_inventory",
    "text_search": "artifact_discovery_inventory",
    "dissemination_artifacts": "artifact_discovery_inventory",
    "market_artifacts": "artifact_discovery_inventory",
    "polymarket": "artifact_discovery_inventory",
    "type_census": "artifact_discovery_inventory",
}

ACTION_CATALOG: dict[str, dict[str, Any]] = {
    "repo_pytest_validation": {
        "purpose": "validate",
        "owner_surface": "./repo-pytest",
        "resource_class": "pytest",
        "authority_level": "focused_validation",
        "quote_sources": [
            "system/lib/command_run_singleflight.py",
            "tools/meta/testing/run_test_slice.py",
            "tools/meta/testing/select_impacted_tests.py",
            "tools/meta/testing/test_inventory.py",
            "codex/testing/test_impact_map.json",
            "state/testing/test_inventory.json",
            "state/command_runs/",
            "state/performance/latency_speedboard.json",
            "repo-pytest::host_pressure_admission_gate",
            REPO_PYTEST_DISK_PRESSURE_QUOTE_SOURCE,
            "tools/meta/storage_doctor.py",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "latency_seed_preflight": {
        "purpose": "coordinate_latency_seed",
        "owner_surface": "./repo-python kernel.py --latency-seed-digest",
        "resource_class": "latency_coordination",
        "authority_level": "coordination_read_model",
        "quote_sources": [
            "state/performance/latency_speedboard.json",
            "codex/hologram/process/summary.json",
            "state/work_ledger/active_claims_snapshot.json",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "work_ledger_claim_read": {
        "purpose": "coordination_claim_read",
        "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-claims",
        "resource_class": "ledger_projection",
        "authority_level": "coordination_read_model",
        "quote_sources": ["state/work_ledger/active_claims_snapshot.json"],
    },
    "work_ledger_session_preflight": {
        "purpose": "coordination_session_preflight",
        "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-preflight",
        "resource_class": "ledger_lifecycle_command",
        "authority_level": "cli_contract",
        "quote_sources": [
            "tools/meta/factory/work_ledger.py::session-preflight --help",
            "state/work_ledger/runtime_status.json metadata only",
        ],
    },
    "work_ledger_heartbeat": {
        "purpose": "coordination_heartbeat_update",
        "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-heartbeat",
        "resource_class": "ledger_lifecycle_command",
        "authority_level": "cli_contract",
        "quote_sources": [
            "tools/meta/factory/work_ledger.py::session-heartbeat --help",
            "state/work_ledger/runtime_status.json metadata only",
        ],
    },
    "task_ledger_validate": {
        "purpose": "task_ledger_projection_validation",
        "owner_surface": TASK_LEDGER_AUTHORITY_HEALTH_PROJECTION_CHECK_COMMAND,
        "resource_class": "ledger_validation",
        "authority_level": "read_only_event_projection_validation",
        "quote_sources": [
            "tools/meta/factory/task_ledger_apply.py::authority-health",
            "tools/meta/factory/task_ledger_apply.py::validate",
            "system/lib/task_ledger_events.py::validate_event_log",
            "state/task_ledger/events.jsonl metadata only",
            "state/task_ledger/ledger.json metadata only",
            "state/task_ledger/views/*.json metadata only",
            "codex/standards/std_task_ledger.json",
        ],
    },
    "task_ledger_rebuild_status": {
        "purpose": "task_ledger_projection_rebuild_status",
        "owner_surface": TASK_LEDGER_REBUILD_STATUS_COMMAND,
        "resource_class": "projection_builder_status",
        "authority_level": "status_only_projection_freshness_check",
        "quote_sources": [
            "tools/meta/factory/task_ledger_apply.py::rebuild",
            "state/task_ledger/projection_manifest.json metadata only",
            "codex/hologram/process/summary.json::repo_tool_command",
            "codex/hologram/process/audit.json::repair_hints",
        ],
    },
    "task_ledger_quick_capture": {
        "purpose": "append_only_task_ledger_capture",
        "owner_surface": "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture",
        "resource_class": "ledger_mutation_command",
        "authority_level": "cli_contract_append_only",
        "quote_sources": [
            "tools/meta/factory/task_ledger_apply.py::quick-capture --help",
            "AGENTS.override.md::Task Ledger capture reflex",
            "state/task_ledger/events.jsonl append authority",
            "codex/hologram/process/summary.json::repo_tool_command",
        ],
    },
    "storage_doctor_status": {
        "purpose": "storage_pressure_status_route",
        "owner_surface": STORAGE_DOCTOR_STATUS_COMMAND,
        "resource_class": "storage_doctor",
        "authority_level": "read_only_storage_pressure_card",
        "quote_sources": [
            "tools/meta/storage_doctor.py::scan --format card",
            "system.lib.resource_pressure::owner_lanes.disk",
            "codex/hologram/process/summary.json::repo_tool_command",
        ],
    },
    "process_bottleneck_triage": {
        "purpose": "diagnostic_read_model",
        "owner_surface": "./repo-python kernel.py --process-bottlenecks",
        "resource_class": "process_trace",
        "authority_level": "materialized_diagnostic",
        "quote_sources": [
            "codex/hologram/process/summary.json",
            "state/performance/latency_speedboard.json::remaining_bottlenecks",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "process_summary_status": {
        "purpose": "selected_process_status_route",
        "owner_surface": PROCESS_SUMMARY_OWNER_COMMAND,
        "resource_class": "process_trace",
        "authority_level": "session_scoped_read_model",
        "quote_sources": [
            "codex/hologram/process/summary.json",
            "codex/hologram/process/ledger.json",
            "codex/hologram/process/audit.json",
            "system/lib/agent_execution_trace.py::build_process_summary_route_packet",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "document_read_economy": {
        "purpose": "bounded_document_read_selection",
        "owner_surface": "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
        "resource_class": "read_file",
        "authority_level": "navigation_read_model",
        "quote_sources": [
            "codex/hologram/process/summary.json::read_file",
            "AGENTS.override.md::First Moves",
            "kernel.py --entry",
            "kernel.py --context-pack",
            "system/lib/navigation_context_pack.py",
        ],
    },
    "kernel_output_economy": {
        "purpose": "bounded_kernel_output_selection",
        "owner_surface": "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
        "resource_class": "kernel_command",
        "authority_level": "navigation_read_model",
        "quote_sources": [
            "codex/hologram/process/summary.json::kernel_command",
            "kernel.py --entry",
            "kernel.py --context-pack",
            "kernel.py --latency-seed-digest --latency-seed-no-git",
            "tools/meta/control/action_quote.py::command_surface_inventory",
            "system/lib/navigation_context_pack.py",
        ],
    },
    "exec_session_wait_tax": {
        "purpose": "exec_session_wait_triage",
        "owner_surface": "./repo-python kernel.py --process-bottlenecks",
        "resource_class": "exec_session_io",
        "authority_level": "materialized_diagnostic",
        "quote_sources": [
            "codex/hologram/process/summary.json::exec_session_io",
            "state/performance/latency_speedboard.json::remaining_bottlenecks",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "frontend_vitest_validation": {
        "purpose": "frontend_validation",
        "owner_surface": "./repo-python tools/meta/testing/frontend_vitest.py",
        "resource_class": "vitest",
        "authority_level": "focused_frontend_validation",
        "quote_sources": [
            "system/server/ui/package.json",
            "system/server/ui/vitest.config.ts",
            "tools/meta/testing/frontend_vitest.py",
            "system/server/ui/src/pages/__tests__/",
            "codex/hologram/process/summary.json::test_or_build_command",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "command_surface_inventory": {
        "purpose": "bounded_command_surface_discovery",
        "owner_surface": "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory",
        "resource_class": "command_metadata_inventory",
        "authority_level": "path_metadata_read_model",
        "quote_sources": [
            "tools/meta/",
            "system/lib/admission_consumer.py",
            "codex/hologram/process/",
            "codex/standards/",
            "codex/doctrine/",
            "state/performance/ metadata only",
            "state/work_ledger/ metadata only",
            "state/command_runs/ metadata only",
            "state/agent_telemetry/process/ metadata only",
            "system/server/tests/",
            "system/lib/",
            ".agents/",
            "docs/",
            "repo-python",
            "repo-pytest",
        ],
    },
    "bash_other_economy": {
        "purpose": "unclassified_bash_output_router",
        "owner_surface": "./repo-python tools/meta/control/action_quote.py --action bash_other --scope <path-or-owner>",
        "resource_class": "bash_other",
        "authority_level": "scope_classified_owner_route",
        "quote_sources": [
            "codex/hologram/process/summary.json::bash_other",
            "codex/hologram/process/audit.json::context_yield_attribution",
            "tools/meta/control/action_quote.py::artifact_discovery_inventory",
            "tools/meta/control/action_quote.py::command_surface_inventory",
            "tools/meta/control/git_state_snapshot.py",
        ],
    },
    "destructive_shell_guard": {
        "purpose": "destructive_shell_owner_guard",
        "owner_surface": "./repo-python tools/meta/control/action_quote.py --action destructive_shell --scope <command>",
        "resource_class": "destructive_shell",
        "authority_level": "non_destructive_owner_route",
        "quote_sources": [
            "codex/hologram/process/summary.json::bash_other",
            "tools/meta/storage_doctor.py::destructive gates",
            "tools/meta/dissemination/build_microcosm_public_site.py::check --validate",
        ],
    },
    "artifact_discovery_inventory": {
        "purpose": "bounded_artifact_file_discovery",
        "owner_surface": "./repo-python tools/meta/control/action_quote.py --action artifact_discovery_inventory --scope <term-or-root>",
        "resource_class": "artifact_path_and_content_metadata_inventory",
        "authority_level": "path_and_content_metadata_read_model",
        "quote_sources": [
            "system/ path and content metadata only",
            "tools/meta/ path and content metadata only",
            "codex/standards/ path and content metadata only",
            "codex/doctrine/ path and content metadata only",
            ".agents/ path and content metadata only",
            "docs/ path and content metadata only",
            "docs/dissemination/ path metadata only",
            "tools/meta/dissemination/ path metadata only",
            "tools/polymarket/ path metadata only",
            "state/reports/market_feeds/ path metadata only",
            "state/metabolism/ path metadata only",
            "microcosm-substrate/ path and content metadata only",
            "codex/doctrine/paper_modules/ path metadata only",
            "codex/doctrine/skills/dissemination/ path metadata only",
        ],
    },
    "git_object_store_status": {
        "purpose": "git_object_store_scan_replacement",
        "owner_surface": "./repo-python tools/meta/control/git_gc_maintenance.py --tmp-object-status",
        "resource_class": "git_object_store_metadata",
        "authority_level": "git_maintenance_status",
        "quote_sources": [
            "tools/meta/control/git_gc_maintenance.py --tmp-object-status",
            "tools/meta/control/git_gc_maintenance.py --check",
            "codex/hologram/process/summary.json::bash_find",
        ],
    },
    "host_filesystem_discovery": {
        "purpose": "bounded_host_filesystem_discovery",
        "owner_surface": "./repo-python tools/meta/control/action_quote.py --action host_filesystem_discovery --scope <host-path-or-term>",
        "resource_class": "host_filesystem_metadata_probe",
        "authority_level": "host_scope_classification",
        "quote_sources": [
            "codex/hologram/process/summary.json::bash_find",
            "codex/hologram/process/audit.json::raw_find_scan",
            "macOS mdfind metadata command shape",
            "bounded find first-result command shape",
        ],
    },
    "station_render_capture": {
        "purpose": "station_visual_capture",
        "owner_surface": "./repo-python -m tools.meta.observability.station_render",
        "resource_class": "frontend_render_capture",
        "authority_level": "manifest_and_timing_metadata",
        "quote_sources": [
            "tools/meta/observability/station_render.py",
            "system/lib/admission_consumer.py",
            "tools/meta/observability/station_views.json",
            "state/observability/render_load_index.json metadata only",
            "codex/hologram/process/summary.json::station_render",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "paper_module_index": {
        "purpose": "paper_module_projection_and_output_economy",
        "owner_surface": "./repo-python tools/meta/factory/build_paper_module_index.py",
        "resource_class": "projection_builder",
        "authority_level": "cached_projection_metadata",
        "quote_sources": [
            "./repo-python kernel.py --option-surface paper_modules",
            "./repo-python kernel.py --paper-module <slug>",
            "tools/meta/factory/build_paper_module_index.py",
            "system/lib/admission_consumer.py",
            "codex/doctrine/paper_modules/_index.json metadata only",
            "codex/doctrine/paper_modules/_validation_report.json metadata only",
            "codex/doctrine/paper_modules/_route_coverage.json metadata only",
            "codex/standards/std_paper_module.json",
            "codex/hologram/process/summary.json::kernel_command",
            "codex/hologram/process/summary.json::repo_tool_command",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "git_diff_review_context": {
        "purpose": "diff_review_context_admission",
        "owner_surface": "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
        "resource_class": "git_diff_review",
        "authority_level": "path_and_diff_metadata_read_model",
        "quote_sources": [
            "system/lib/git_state_snapshot.py",
            "tools/meta/control/git_state_snapshot.py",
            "codex/standards/std_command_output_projection.json::diff_review_context_contract",
            "codex/hologram/process/summary.json::bash_other",
            "codex/hologram/process/audit.json::repair_hints",
        ],
    },
    "git_state_snapshot_status": {
        "purpose": "git_state_snapshot_status",
        "owner_surface": "./repo-python tools/meta/control/git_state_snapshot.py --compact",
        "resource_class": "git_state",
        "authority_level": "path_and_git_metadata_read_model",
        "quote_sources": [
            "system/lib/git_state_snapshot.py",
            "tools/meta/control/git_state_snapshot.py",
            "codex/hologram/process/summary.json::bash_cat",
            "codex/hologram/process/audit.json::repair_hints",
        ],
    },
    "generated_state_settlement": {
        "purpose": "generated_projection_settlement_admission",
        "owner_surface": "./repo-python tools/meta/control/generated_state_drainer.py",
        "resource_class": "generated_state_projection",
        "authority_level": "owner_settlement_plan",
        "quote_sources": [
            "tools/meta/control/generated_state_drainer.py",
            "system/lib/generated_state_drainer.py",
            "state/generated_projection_landing/*.json metadata only",
            "state/task_ledger/events.jsonl metadata only",
            "codex/ledger/*/work_ledger.jsonl metadata only",
            "state/system_atlas/*.json metadata only",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "scoped_commit_private_index": {
        "purpose": "private_index_scoped_commit_admission",
        "owner_surface": "./repo-python tools/meta/control/scoped_commit.py",
        "resource_class": "scoped_git_commit",
        "authority_level": "disk_and_claim_preflight",
        "quote_sources": [
            "tools/meta/control/scoped_commit.py",
            "tools/meta/control/mission_transaction_preflight.py",
            "tools/meta/factory/work_ledger.py session-preflight",
            "tools/meta/storage_doctor.py",
            "state/work_ledger/active_claims_snapshot.json",
        ],
    },
    "helper_lease_admission": {
        "purpose": "helper_tool_lease_pressure_budget",
        "owner_surface": "./repo-python tools/meta/factory/work_ledger.py helper-lease-admission",
        "resource_class": "helper_tool_lease",
        "authority_level": "pressure_budget_gate",
        "quote_sources": [
            "system/lib/work_admission.py::build_helper_lease_admission_decision",
            "tools/meta/factory/work_ledger.py::cmd_helper_lease_admission",
            "tools/meta/control/orphan_reaper.py::tool_server_pressure_inventory_v1 metadata only",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "resident_pressure_relief": {
        "purpose": "resident_pressure_relief",
        "owner_surface": "./repo-python tools/meta/factory/work_ledger.py resident-pressure-relief",
        "resource_class": "resident_pressure_budget",
        "authority_level": "resident_relief_request_and_receipt",
        "quote_sources": [
            "system/lib/work_admission.py::build_resident_pressure_relief_window",
            "system/lib/work_admission.py::build_owner_release_result_receipt",
            "system/lib/work_admission.py::build_background_loop_downshift_receipt",
            "tools/meta/factory/work_ledger.py::cmd_resident_pressure_relief",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "session_yield_request": {
        "purpose": "owner_visible_resident_pressure_yield_request",
        "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-yield-request",
        "resource_class": "resident_pressure_budget",
        "authority_level": "owner_visible_request_bus",
        "quote_sources": [
            "system/lib/work_admission.py::build_session_pressure_rank",
            "system/lib/work_admission.py::build_session_yield_request_receipt",
            "system/lib/work_admission.py::build_resident_relief_escalation_window",
            "tools/meta/factory/work_ledger.py::cmd_session_yield_request",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
    "session_yield_result": {
        "purpose": "accepted_resident_pressure_yield_result",
        "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-yield-result",
        "resource_class": "resident_pressure_budget",
        "authority_level": "owner_visible_result_bus",
        "quote_sources": [
            "system/lib/work_admission.py::build_owner_yield_result_receipt",
            "system/lib/work_admission.py::build_accepted_resident_relief_window",
            "tools/meta/factory/work_ledger.py::cmd_session_yield_result",
            "tools/meta/factory/work_ledger.py::cmd_session_yield_control",
            HOST_PRESSURE_QUOTE_SOURCE,
        ],
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(value: Any) -> float | None:
    parsed = _parse_iso(value)
    if parsed is None:
        return None
    return round((datetime.now(timezone.utc) - parsed).total_seconds(), 3)


def _freshness_age_seconds(generated_at: Any, cached_age_s: Any = None) -> Any:
    computed = _age_seconds(generated_at)
    return computed if computed is not None else cached_age_s


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _host_pressure_admission_quote(
    repo_root: Path,
    workload_class: str,
    include_processes: bool = False,
    *,
    full: bool = False,
) -> dict[str, Any]:
    trace_path = repo_root / "state/observability/agent_trace/events.jsonl"
    quote_command = HOST_PRESSURE_PROCESS_COMMAND if include_processes else HOST_PRESSURE_FAST_COMMAND
    base: dict[str, Any] = {
        "schema": "action_quote_host_pressure_admission_v0",
        "status": "missing_trace_store" if not trace_path.is_file() else "available",
        "quote_command": quote_command,
        "profile_command": HOST_PRESSURE_PROFILE_COMMAND,
        "requested_workload_class": workload_class,
        "source": {
            "trace_path": str(trace_path.relative_to(repo_root))
            if trace_path.is_relative_to(repo_root)
            else str(trace_path),
            "event_limit": HOST_PRESSURE_EVENT_LIMIT,
            "include_processes": include_processes,
            "include_resident_relief": False,
            "process_rows_policy": "sampled_for_launch_gate" if include_processes else "omitted_by_default",
        },
    }
    if not trace_path.is_file():
        base["recommendation_effect"] = "no_admission_change"
        base["should_block_run"] = False
        return base
    try:
        from system.lib.agent_observability import AgentTraceStore
        from system.lib.host_pressure import build_progress_pressure_packet_from_store

        store = AgentTraceStore(
            repo_root,
            max_history=HOST_PRESSURE_EVENT_LIMIT,
        )
        packet = build_progress_pressure_packet_from_store(
            store,
            repo_root,
            event_limit=HOST_PRESSURE_EVENT_LIMIT,
            include_processes=include_processes,
            include_resident_relief=False,
            requested_workload_class=workload_class,
        )
    except Exception as exc:  # pragma: no cover - defensive boundary for local host adapters.
        base.update(
            {
                "status": "unavailable",
                "error_class": type(exc).__name__,
                "recommendation_effect": "no_admission_change",
                "should_block_run": False,
            }
        )
        return base

    summary = _as_mapping(packet.get("summary"))
    governor = _as_mapping(packet.get("mac_throttle_relief_governor"))
    admission = _as_mapping(governor.get("admission"))
    calibration = _as_mapping(governor.get("admission_calibration_contract"))
    calibration_window = _as_mapping(packet.get("admission_calibration_window"))
    policy_promotion = _as_mapping(packet.get("host_pressure_policy_promotion"))
    policy_application = _as_mapping(packet.get("host_pressure_policy_application"))
    safe_policy = _as_mapping(packet.get("safe_parallelism_policy"))
    load_shed_actions = _as_list(packet.get("load_shed_action_receipts"))
    decision = str(admission.get("decision") or summary.get("admission_default_decision") or "unknown")
    load_shed_recommended = bool(
        summary.get("load_shed_recommended")
        or admission.get("local_load_shed_recommended")
        or load_shed_actions
    )
    if decision == "queue_until_pressure_clears":
        recommendation_effect = "defer_or_use_cheaper_summary"
    elif decision == "require_operator_override":
        recommendation_effect = "operator_override_required"
    elif load_shed_recommended:
        recommendation_effect = "prefer_cheaper_summary"
    elif decision == "allow_with_warning":
        recommendation_effect = "allow_with_warning"
    else:
        recommendation_effect = "allow"
    selected_group = _as_mapping(calibration_window.get("selected_group"))
    tuple_scope = _as_mapping(policy_promotion.get("tuple_scope"))
    policy_evidence = _as_mapping(policy_promotion.get("evidence"))
    base.update(
        {
            "status": "available",
            "decision": decision,
            "recommendation_effect": recommendation_effect,
            "should_block_run": decision in {
                "queue_until_pressure_clears",
                "require_operator_override",
            },
            "summary": {
                "active_agents": summary.get("active_agents"),
                "pressure_index": summary.get("pressure_index"),
                "bottleneck_class": summary.get("bottleneck_class"),
                "governor_decision": summary.get("governor_decision"),
                "admission_default_decision": summary.get("admission_default_decision"),
                "load_shed_action_count": summary.get("load_shed_action_count"),
                "load_shed_recommended": summary.get("load_shed_recommended"),
            },
            "admission": {
                "requested_workload_class": admission.get("requested_workload_class"),
                "decision": decision,
                "reason": admission.get("reason"),
                "active_agents": admission.get("active_agents"),
                "heuristic_cap": admission.get("heuristic_cap"),
                "over_heuristic_cap": admission.get("over_heuristic_cap"),
                "next_action": admission.get("next_action"),
                "local_load_shed_recommended": admission.get("local_load_shed_recommended"),
                "operator_override_required": admission.get("operator_override_required"),
            },
            "admission_calibration_contract": {
                "schema_version": calibration.get("schema_version"),
                "status": calibration.get("status"),
                "calibration_status": calibration.get("calibration_status"),
                "next_receipt": calibration.get("next_receipt"),
                "recheck_command": calibration.get("recheck_command"),
                "outcome_receipt_field_count": len(_as_list(calibration.get("outcome_receipt_fields"))),
            },
            "admission_calibration_window": {
                "schema_version": calibration_window.get("schema_version"),
                "status": calibration_window.get("status"),
                "policy_state": calibration_window.get("policy_state"),
                "sample_count": calibration_window.get("sample_count"),
                "latest_verdict": calibration_window.get("latest_verdict"),
                "current_decision_tuple": dict(_as_mapping(calibration_window.get("current_decision_tuple"))),
                "selected_group_matches_current_decision": calibration_window.get(
                    "selected_group_matches_current_decision"
                ),
                "selected_group_summary": {
                    "workload_class": selected_group.get("workload_class"),
                    "bottleneck_class": selected_group.get("bottleneck_class"),
                    "admission_decision": selected_group.get("admission_decision"),
                    "sample_count": selected_group.get("sample_count"),
                    "success_count": selected_group.get("success_count"),
                    "failure_count": selected_group.get("failure_count"),
                    "slow_count": selected_group.get("slow_count"),
                    "latest_verdict": selected_group.get("latest_verdict"),
                    "latest_suggested_calibration_action": selected_group.get(
                        "latest_suggested_calibration_action"
                    ),
                },
            },
            "host_pressure_policy_promotion": {
                "schema_version": policy_promotion.get("schema_version"),
                "status": policy_promotion.get("status"),
                "promotion_state": policy_promotion.get("promotion_state"),
                "admission_policy_action": policy_promotion.get("admission_policy_action"),
                "required_next_receipt": policy_promotion.get("required_next_receipt"),
                "selected_group_matches_current_decision": policy_promotion.get(
                    "selected_group_matches_current_decision"
                ),
                "tuple_scope_summary": {
                    "workload_class": tuple_scope.get("workload_class"),
                    "bottleneck_class": tuple_scope.get("bottleneck_class"),
                    "admission_decision": tuple_scope.get("admission_decision"),
                },
                "evidence_summary": {
                    "sample_count": policy_evidence.get("sample_count"),
                    "success_count": policy_evidence.get("success_count"),
                    "failure_count": policy_evidence.get("failure_count"),
                    "slow_count": policy_evidence.get("slow_count"),
                    "latest_verdict": policy_evidence.get("latest_verdict"),
                    "latest_receipt_ref": policy_evidence.get("latest_receipt_ref"),
                },
            },
            "host_pressure_policy_application": {
                "schema_version": policy_application.get("schema_version"),
                "status": policy_application.get("status"),
                "source_promotion_state": policy_application.get("source_promotion_state"),
                "source_promotion_action": policy_application.get("source_promotion_action"),
                "selected_group_matches_current_decision": policy_application.get(
                    "selected_group_matches_current_decision"
                ),
                "control_action": policy_application.get("control_action"),
                "actuation_mode": policy_application.get("actuation_mode"),
                "bounded_control_authorized": policy_application.get("bounded_control_authorized"),
                "tuple_policy_change_authorized": policy_application.get(
                    "tuple_policy_change_authorized"
                ),
                "cap_mutation_authorized": policy_application.get("cap_mutation_authorized"),
                "global_cap_change_authorized": policy_application.get(
                    "global_cap_change_authorized"
                ),
                "automatic_scheduler_mutation_authorized": policy_application.get(
                    "automatic_scheduler_mutation_authorized"
                ),
                "required_next_receipt": policy_application.get("required_next_receipt"),
                "queue_sojourn_policy_status": _as_mapping(
                    policy_application.get("queue_sojourn_policy")
                ).get("status"),
            },
            "safe_parallelism": _as_mapping(safe_policy.get("default_parallelism")),
            "load_shed_actions": [
                {
                    "action_id": _as_mapping(row).get("action_id"),
                    "target_class": _as_mapping(row).get("target_class"),
                    "action": _as_mapping(row).get("action"),
                }
                for row in load_shed_actions[:3]
            ],
        }
    )
    if full:
        base["admission_calibration_contract"]["decision_trace"] = dict(
            _as_mapping(calibration.get("decision_trace"))
        )
        base["admission_calibration_contract"]["outcome_receipt_fields"] = (
            calibration.get("outcome_receipt_fields") or []
        )
        base["admission_calibration_window"]["policy_recommendation"] = (
            calibration_window.get("policy_recommendation")
        )
        base["admission_calibration_window"]["policy_reason"] = calibration_window.get(
            "policy_reason"
        )
        base["admission_calibration_window"]["minimum_samples_required"] = (
            calibration_window.get("minimum_samples_required")
        )
        base["admission_calibration_window"]["latest_receipt_ref"] = (
            calibration_window.get("latest_receipt_ref")
        )
        base["admission_calibration_window"]["selected_group"] = dict(selected_group)
        base["admission_calibration_window"]["guardrails"] = dict(
            _as_mapping(calibration_window.get("guardrails"))
        )
        base["host_pressure_policy_promotion"]["operator_summary"] = policy_promotion.get(
            "operator_summary"
        )
        base["host_pressure_policy_promotion"]["current_decision_tuple"] = dict(
            _as_mapping(policy_promotion.get("current_decision_tuple"))
        )
        base["host_pressure_policy_promotion"]["tuple_scope"] = dict(tuple_scope)
        base["host_pressure_policy_promotion"]["evidence"] = dict(policy_evidence)
        base["host_pressure_policy_promotion"]["source_window_ref"] = dict(
            _as_mapping(policy_promotion.get("source_window_ref"))
        )
        base["host_pressure_policy_promotion"]["guardrails"] = dict(
            _as_mapping(policy_promotion.get("guardrails"))
        )
        base["host_pressure_policy_application"]["current_decision_tuple"] = dict(
            _as_mapping(policy_application.get("current_decision_tuple"))
        )
        base["host_pressure_policy_application"]["tuple_scope"] = dict(
            _as_mapping(policy_application.get("tuple_scope"))
        )
        base["host_pressure_policy_application"]["assay_request"] = dict(
            _as_mapping(policy_application.get("assay_request"))
        )
        base["host_pressure_policy_application"]["queue_sojourn_policy"] = dict(
            _as_mapping(policy_application.get("queue_sojourn_policy"))
        )
        base["host_pressure_policy_application"]["guardrails"] = dict(
            _as_mapping(policy_application.get("guardrails"))
        )
    else:
        base["compact_evidence_receipt"] = {
            "schema": "action_quote_host_pressure_compact_evidence_v0",
            "status": "full_evidence_omitted",
            "full_quote_flag": "--full",
            "omitted_field_count": 17,
        }
    return base


def _host_pressure_load_shed_note(
    admission: Mapping[str, Any],
    *,
    recheck_command: str | None = None,
) -> dict[str, Any]:
    admission_quote_command = str(admission.get("quote_command") or HOST_PRESSURE_FAST_COMMAND)
    quote_command = recheck_command or admission_quote_command
    note = {
        "lane": "host_pressure_load_shed",
        "reason": (
            _as_mapping(admission.get("admission")).get("reason")
            or "Host pressure governor recommends delaying this workload class."
        ),
        "requested_workload_class": admission.get("requested_workload_class"),
        "decision": admission.get("decision"),
        "quote_command": quote_command,
        "profile_command": HOST_PRESSURE_PROFILE_COMMAND,
    }
    if admission_quote_command != quote_command:
        note["process_gate_command"] = admission_quote_command
    return note


def _prepend_recommended_next(
    rows: Sequence[Any],
    *,
    action: str,
    reason: str | None,
    command: str | None = None,
) -> list[Any]:
    return [
        {
            "action": action,
            "reason": reason or "Host pressure governor recommends cheaper work first.",
            "command": command or HOST_PRESSURE_FAST_COMMAND,
        },
        *_as_list(rows),
    ]


def _parse_byte_floor(env_var: str, default: int) -> int:
    raw = os.environ.get(env_var)
    if raw is None or not raw.strip():
        return default
    text = raw.strip().lower()
    multipliers = {
        "k": 1024,
        "kb": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
        "t": 1024**4,
        "tb": 1024**4,
    }
    number = text
    multiplier = 1
    for suffix in sorted(multipliers, key=len, reverse=True):
        if text.endswith(suffix):
            number = text[: -len(suffix)]
            multiplier = multipliers[suffix]
            break
    try:
        return max(0, int(float(number.strip()) * multiplier))
    except ValueError:
        return default


def _format_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(amount)}B"
            return f"{amount:.1f}{unit}"
        amount /= 1024
    return f"{value}B"


def _repo_pytest_heavy_scope(repo_root: Path, scopes: Sequence[str]) -> bool:
    if not scopes:
        return True
    if len(scopes) > 1:
        return True
    path = Path(scopes[0])
    candidate = path if path.is_absolute() else repo_root / path
    return candidate.exists() and candidate.is_dir()


def _repo_pytest_disk_pressure_quote(
    repo_root: Path,
    scopes: Sequence[str],
    *,
    full: bool = False,
) -> dict[str, Any]:
    tmpdir = Path(tempfile.gettempdir())
    heavy_scope = _repo_pytest_heavy_scope(repo_root, scopes)
    min_free = _parse_byte_floor(
        REPO_PYTEST_MIN_TMP_FREE_BYTES_ENV_VAR,
        REPO_PYTEST_DEFAULT_MIN_TMP_FREE_BYTES,
    )
    heavy_min_free = _parse_byte_floor(
        REPO_PYTEST_HEAVY_MIN_TMP_FREE_BYTES_ENV_VAR,
        REPO_PYTEST_DEFAULT_HEAVY_MIN_TMP_FREE_BYTES,
    )
    required_free = heavy_min_free if heavy_scope else min_free
    usage_rows: list[dict[str, Any]] = []
    seen_devices: set[int | str] = set()
    for role, path in (("tmpdir", tmpdir), ("repo_root", repo_root)):
        try:
            stat = path.stat()
            device_key: int | str = stat.st_dev
            if device_key in seen_devices:
                continue
            seen_devices.add(device_key)
            usage = shutil.disk_usage(path)
        except OSError as exc:
            return {
                "schema": "repo_pytest_disk_pressure_quote_v0",
                "status": "unavailable",
                "source": REPO_PYTEST_DISK_PRESSURE_QUOTE_SOURCE,
                "role": role,
                "path": str(path),
                "error_class": type(exc).__name__,
                "should_block_run": False,
                "decision": "allow",
                "reason": "disk_usage_unavailable",
            }
        usage_rows.append(
            {
                "role": role,
                "path": str(path),
                "free_bytes": usage.free,
                "free_human": _format_bytes(usage.free),
                "total_bytes": usage.total,
                "total_human": _format_bytes(usage.total),
            }
        )
    min_free_row = min(usage_rows, key=lambda row: int(row.get("free_bytes") or 0))
    free_bytes = int(min_free_row.get("free_bytes") or 0)
    should_block = free_bytes < required_free
    payload = {
        "schema": "repo_pytest_disk_pressure_quote_v0",
        "status": "available",
        "source": REPO_PYTEST_DISK_PRESSURE_QUOTE_SOURCE,
        "tmpdir": str(tmpdir),
        "heavy_scope": heavy_scope,
        "min_tmp_free_bytes": min_free,
        "heavy_min_tmp_free_bytes": heavy_min_free,
        "required_free_bytes": required_free,
        "required_free_human": _format_bytes(required_free),
        "free_bytes": free_bytes,
        "free_human": _format_bytes(free_bytes),
        "limiting_path": min_free_row.get("path"),
        "usage_rows": usage_rows,
        "should_block_run": should_block,
        "decision": "queue_until_disk_pressure_clears" if should_block else "allow",
        "reason": (
            "free_space_below_repo_pytest_floor"
            if should_block
            else "free_space_meets_repo_pytest_floor"
        ),
        "storage_doctor_command": REPO_PYTEST_STORAGE_SCAN_COMMAND,
        "storage_doctor_output_profile": REPO_PYTEST_STORAGE_OUTPUT_PROFILE,
        "safe_cleanup_command": REPO_PYTEST_STORAGE_SAFE_CLEAN_COMMAND,
        "owner_checked_repo_cache_dry_run_command": (
            REPO_PYTEST_STORAGE_OWNER_CHECKED_REPO_CACHE_DRY_RUN_COMMAND
        ),
        "owner_checked_annex_clone_dry_run_command": (
            REPO_PYTEST_STORAGE_OWNER_CHECKED_ANNEX_CLONE_DRY_RUN_COMMAND
        ),
        "policy_surface": (
            "--disk-pressure-policy / --ignore-disk-pressure / "
            "AIW_REPO_PYTEST_MIN_TMP_FREE_BYTES / AIW_REPO_PYTEST_HEAVY_MIN_TMP_FREE_BYTES"
        ),
    }
    if full:
        payload.update(
            {
                "storage_doctor_full_report_command": REPO_PYTEST_STORAGE_FULL_REPORT_COMMAND,
                "owner_checked_repo_cache_apply_command": (
                    REPO_PYTEST_STORAGE_OWNER_CHECKED_REPO_CACHE_APPLY_COMMAND
                ),
                "owner_checked_repo_cache_policy": (
                    "Use only for explicitly selected rebuildable repo dependency caches after "
                    "storage_doctor records liveness, git-status, reinstall-cost, and bytes receipts."
                ),
                "owner_checked_annex_clone_apply_command": (
                    REPO_PYTEST_STORAGE_OWNER_CHECKED_ANNEX_CLONE_APPLY_COMMAND
                ),
                "owner_checked_annex_clone_policy": (
                    "Use only for clean reconstructable annex source clones after storage_doctor "
                    "records liveness, outer git-status, bytes, and annex_import restore-command receipts."
                ),
            }
        )
    else:
        payload["compact_evidence_receipt"] = {
            "schema": "repo_pytest_disk_pressure_compact_evidence_v0",
            "status": "full_cleanup_policy_omitted",
            "full_quote_flag": "--full",
            "omitted_field_count": 5,
        }
    return payload


def _repo_pytest_disk_pressure_note(admission: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lane": "disk_pressure_load_shed",
        "reason": admission.get("reason") or "TMPDIR free space is below the repo-pytest floor.",
        "tmpdir": admission.get("tmpdir"),
        "free_human": admission.get("free_human"),
        "required_free_human": admission.get("required_free_human"),
        "heavy_scope": admission.get("heavy_scope"),
        "command": admission.get("storage_doctor_command") or REPO_PYTEST_STORAGE_SCAN_COMMAND,
    }


def _apply_repo_pytest_disk_pressure(
    repo_root: Path,
    detail: dict[str, Any],
    *,
    full: bool = False,
) -> dict[str, Any]:
    admission = _repo_pytest_disk_pressure_quote(
        repo_root,
        _as_list(detail.get("scope_paths")),
        full=full,
    )
    shaped = dict(detail)
    shaped["disk_pressure_admission"] = admission
    if not admission.get("should_block_run"):
        return shaped
    if shaped.get("recommendation") == "attach_to_running_singleflight":
        shaped["disk_pressure_attach_allowed"] = True
        shaped["disk_pressure_attach_reason"] = (
            "Existing singleflight attachment does not create a new pytest temp tree."
        )
        return shaped

    original_recommendation = shaped.get("recommendation")
    original_suggested_command = shaped.get("suggested_command")
    storage_command = str(
        admission.get("storage_doctor_command") or REPO_PYTEST_STORAGE_SCAN_COMMAND
    )
    shaped["disk_pressure_original_recommendation"] = original_recommendation
    shaped["disk_pressure_original_suggested_command"] = original_suggested_command
    shaped["recommendation"] = "queue_validation_until_disk_pressure_clears"
    shaped["current_status"] = "disk_pressure_queue_until_free_space_clears"
    shaped["deferred_suggested_command"] = original_suggested_command
    shaped["suggested_command"] = storage_command
    shaped["drilldown_command"] = storage_command
    shaped["do_not_touch"] = [
        *_as_list(shaped.get("do_not_touch")),
        _repo_pytest_disk_pressure_note(admission),
    ]
    shaped["recommended_next"] = [
        {
            "action": "recheck_disk_pressure_before_pytest",
            "reason": admission.get("reason") or "TMPDIR free space is below the repo-pytest floor.",
            "command": storage_command,
        },
        {
            "action": "review_owner_checked_annex_clone_cleanup_if_safe_cleanup_insufficient",
            "reason": (
                "Safe cleanup may not recover enough space; clean annex source clones "
                "are reconstructable only after owner-check receipts and restore commands."
            ),
            "command": admission.get("owner_checked_annex_clone_dry_run_command"),
        },
        {
            "action": "review_owner_checked_repo_cache_cleanup_if_safe_cleanup_insufficient",
            "reason": "Safe cleanup may not recover enough space; owner-checked repo caches require explicit selection.",
            "command": admission.get("owner_checked_repo_cache_dry_run_command"),
        },
        *_as_list(shaped.get("recommended_next")),
    ]
    return shaped


def _compact_git_maintenance_status(
    row: Mapping[str, Any],
    *,
    full: bool = False,
) -> dict[str, Any]:
    payload = {
        "status": row.get("status") or "missing",
        "object_store_status": row.get("object_store_status"),
        "maintenance_admission": row.get("maintenance_admission"),
        "repair_status": row.get("repair_status"),
        "tmp_object_count": row.get("tmp_object_count"),
        "tmp_object_bytes": row.get("tmp_object_bytes"),
        "recent_tmp_object_count": row.get("recent_tmp_object_count"),
        "min_tmp_age_seconds": row.get("min_tmp_age_seconds"),
        "lockfile_count": row.get("lockfile_count"),
        "blocking_lockfile_count": row.get("blocking_lockfile_count"),
        "stale_gc_pid_count": row.get("stale_gc_pid_count"),
        "blocking_git_process_count": row.get("blocking_git_process_count"),
        "blocking_process_family_count": row.get("blocking_process_family_count"),
        "blocking_process_families": row.get("blocking_process_families"),
        "repair_command": row.get("repair_command"),
        "check_command": row.get("check_command"),
        "owner": row.get("owner"),
    }
    repair_reentry = _as_mapping(row.get("repair_reentry"))
    if repair_reentry:
        payload["repair_reentry_summary"] = {
            "ready_to_repair": repair_reentry.get("ready_to_repair"),
            "blocked_by": repair_reentry.get("blocked_by"),
            "wait_ready_repair_command": repair_reentry.get("wait_ready_repair_command"),
        }
    if full:
        payload["maintenance_admission_detail"] = row.get("maintenance_admission_detail")
        payload["repair_reentry"] = row.get("repair_reentry")
    elif row.get("maintenance_admission_detail") or row.get("repair_reentry"):
        payload["compact_evidence_receipt"] = {
            "schema": "git_maintenance_compact_evidence_v0",
            "status": "full_admission_detail_omitted",
            "full_quote_flag": "--full",
            "omitted_field_count": 2,
        }
    return payload


def _repo_pytest_git_maintenance_recommendation(
    row: Mapping[str, Any],
) -> dict[str, Any] | None:
    repair_status = str(row.get("repair_status") or "")
    if repair_status in {
        "blocked_recent_tmp_objects",
        "blocked_git_lockfile",
        "blocked_git_lockfile_or_process",
    }:
        reentry = _as_mapping(row.get("repair_reentry"))
        return {
            "action": "wait_or_recheck_git_maintenance_before_pytest",
            "reason": (
                "Git maintenance is not currently safe to repair; wait for the named "
                "admission gates or recheck before launching validation."
            ),
            "command": (
                reentry.get("wait_ready_repair_command")
                or row.get("check_command")
                or GIT_MAINTENANCE_CHECK_COMMAND
            ),
            "check_command": row.get("check_command") or GIT_MAINTENANCE_CHECK_COMMAND,
            "blocked_by": reentry.get("blocked_by"),
        }
    if row.get("status") == "attention":
        check_command = row.get("check_command") or GIT_MAINTENANCE_CHECK_COMMAND
        return {
            "action": "repair_git_maintenance_before_pytest_if_slow",
            "reason": (
                "Stale Git maintenance state can add avoidable wait tax before validation "
                "or commit; re-run the check immediately before repair."
            ),
            "command": row.get("repair_command") or GIT_MAINTENANCE_REPAIR_COMMAND,
            "precheck_command": check_command,
            "guard": "Skip repair if the precheck reports blocking processes, lockfiles, or recent tmp objects.",
        }
    return None


def _compact_embedded_host_pressure_admission(admission: Mapping[str, Any]) -> dict[str, Any]:
    if "compact_evidence_receipt" not in admission:
        return dict(admission)
    summary = _as_mapping(admission.get("summary"))
    admission_row = _as_mapping(admission.get("admission"))
    compact: dict[str, Any] = {
        "schema": admission.get("schema"),
        "status": admission.get("status"),
        "quote_command": admission.get("quote_command"),
        "profile_command": admission.get("profile_command"),
        "requested_workload_class": admission.get("requested_workload_class"),
        "source": dict(_as_mapping(admission.get("source"))),
        "decision": admission.get("decision"),
        "recommendation_effect": admission.get("recommendation_effect"),
        "should_block_run": admission.get("should_block_run"),
        "summary": {
            "active_agents": summary.get("active_agents"),
            "pressure_index": summary.get("pressure_index"),
            "bottleneck_class": summary.get("bottleneck_class"),
            "governor_decision": summary.get("governor_decision"),
            "admission_default_decision": summary.get("admission_default_decision"),
            "load_shed_action_count": summary.get("load_shed_action_count"),
            "load_shed_recommended": summary.get("load_shed_recommended"),
        },
        "admission": {
            "requested_workload_class": admission_row.get("requested_workload_class"),
            "decision": admission.get("decision"),
            "reason": admission_row.get("reason"),
            "active_agents": admission_row.get("active_agents"),
            "heuristic_cap": admission_row.get("heuristic_cap"),
            "over_heuristic_cap": admission_row.get("over_heuristic_cap"),
            "next_action": admission_row.get("next_action"),
            "operator_override_required": admission_row.get("operator_override_required"),
        },
        "safe_parallelism": dict(_as_mapping(admission.get("safe_parallelism"))),
    }
    receipt = dict(_as_mapping(admission.get("compact_evidence_receipt")))
    if receipt:
        receipt["embedded_payload_compacted"] = True
        compact["compact_evidence_receipt"] = receipt
    return {
        key: value
        for key, value in compact.items()
        if value is not None and value not in ("", [], {})
    }


def _apply_host_pressure_admission(
    action_id: str,
    detail: dict[str, Any],
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    config = HOST_PRESSURE_ADMISSION_BY_ACTION.get(action_id)
    if not config:
        return detail
    shaped = dict(detail)
    shaped["host_pressure_admission"] = _compact_embedded_host_pressure_admission(admission)
    if admission.get("status") != "available":
        return shaped

    decision = str(admission.get("decision") or "")
    if decision not in {"queue_until_pressure_clears", "require_operator_override"}:
        return shaped

    mode = config.get("mode")
    quote_command = str(admission.get("quote_command") or HOST_PRESSURE_FAST_COMMAND)
    pressure_recheck_command = str(config.get("pressure_recheck_command") or "").strip()
    recheck_command = pressure_recheck_command or quote_command
    original_recommendation = shaped.get("recommendation")
    original_suggested_command = shaped.get("suggested_command")
    if mode == "heavy_run" and original_recommendation == "attach_to_running_singleflight":
        shaped["host_pressure_attach_allowed"] = True
        shaped["host_pressure_attach_reason"] = (
            "Existing singleflight attachment does not create a new heavy workload."
        )
        return shaped
    shaped["host_pressure_original_recommendation"] = original_recommendation
    shaped["host_pressure_original_suggested_command"] = original_suggested_command
    if action_id == "session_yield_request":
        ranked_status = _as_mapping(shaped.get("ranked_candidate")).get("status")
        if ranked_status == "pending_request_already_recorded":
            shaped["recommendation"] = "wait_for_pending_session_yield_result"
        elif ranked_status != "candidate_available":
            shaped["recommendation"] = "inspect_claim_cards_before_session_yield_request"
        else:
            shaped["recommendation"] = config["shed_recommendation"]
    else:
        shaped["recommendation"] = config["shed_recommendation"]
    shaped["current_status"] = f"host_pressure_{decision}"
    if recheck_command != quote_command:
        shaped["host_pressure_recheck_command"] = recheck_command
        shaped["host_pressure_process_gate_command"] = quote_command
    shaped["do_not_touch"] = [
        *_as_list(shaped.get("do_not_touch")),
        _host_pressure_load_shed_note(admission, recheck_command=recheck_command),
    ]

    admission_reason = _as_mapping(admission.get("admission")).get("reason")
    if mode in {"heavy_run", "projection"}:
        shaped["deferred_suggested_command"] = original_suggested_command
        shaped["suggested_command"] = recheck_command
        shaped["drilldown_command"] = recheck_command
        shaped["recommended_next"] = _prepend_recommended_next(
            shaped.get("recommended_next"),
            action="recheck_host_pressure_before_heavy_work",
            reason=admission_reason,
            command=recheck_command,
        )
    elif mode == "diagnostic_drilldown":
        force_live = shaped.get("force_live_command") or shaped.get("drilldown_command")
        source_freshness = _as_mapping(shaped.get("source_freshness"))
        source_missing = source_freshness.get("status") == "missing"
        shaped["deferred_drilldown_command"] = force_live
        shaped["drilldown_command"] = quote_command if source_missing else (
            shaped.get("owner_check_command")
            or shaped.get("suggested_command")
            or HOST_PRESSURE_FAST_COMMAND
        )
        shaped["force_live_command_deferred_until_host_pressure_clears"] = force_live
        if source_missing:
            pressure_safe_command = shaped.get("safe_first_command") or shaped.get(
                "cache_check_command"
            )
            bounded_materialize_command = str(
                shaped.get("bounded_materialize_command") or ""
            ).strip()
            full_materialize_command = str(shaped.get("refresh_command") or "").strip()
            shaped["current_status"] = "host_pressure_missing_cached_summary_deferred"
            shaped["recommendation"] = "defer_process_summary_build_until_host_pressure_clears"
            deferred_suggested_command = original_suggested_command
            if bounded_materialize_command and original_suggested_command in {
                bounded_materialize_command,
                full_materialize_command,
            }:
                deferred_suggested_command = bounded_materialize_command
            shaped["deferred_suggested_command"] = deferred_suggested_command
            if bounded_materialize_command:
                shaped["deferred_bounded_materialize_command"] = bounded_materialize_command
            if (
                full_materialize_command
                and full_materialize_command != bounded_materialize_command
            ):
                shaped["deferred_full_materialize_command"] = full_materialize_command
            if shaped.get("owner_check_command"):
                shaped["deferred_owner_check_command"] = shaped.get("owner_check_command")
            if pressure_safe_command:
                shaped["suggested_command"] = pressure_safe_command
                shaped["drilldown_command"] = pressure_safe_command
                shaped["host_pressure_check_command"] = quote_command
                fallback_command = str(config.get("pressure_safe_fallback_command") or "")
                check_command = str(shaped.get("safe_first_check_command") or "").strip()
                exit_policy = {
                    "schema": "action_quote_safe_first_command_exit_policy_v0",
                    "command": pressure_safe_command,
                    "expected_exit_codes": [CACHED_PROCESS_SUMMARY_PROBE_EXIT_CODE],
                    "missing_cache_exit_code": CACHED_PROCESS_SUMMARY_PROBE_EXIT_CODE,
                    "missing_cache_status": "missing_cached_summary",
                    "missing_cache_meaning": (
                        "plain_probe_exits_zero_with_ok_false; "
                        "check_command_returns_missing_cache_exit_code"
                    ),
                    "next_command_when_missing": fallback_command or quote_command,
                }
                if check_command:
                    exit_policy.update(
                        {
                            "check_command": check_command,
                            "check_expected_exit_codes": [
                                CACHED_PROCESS_SUMMARY_PROBE_EXIT_CODE,
                                CACHED_PROCESS_SUMMARY_MISSING_EXIT_CODE,
                            ],
                            "check_missing_cache_exit_code": CACHED_PROCESS_SUMMARY_MISSING_EXIT_CODE,
                        }
                    )
                shaped["safe_first_command_exit_policy"] = exit_policy
                recommended = _prepend_recommended_next(
                    _prepend_recommended_next(
                        shaped.get("recommended_next"),
                        action="recheck_host_pressure_before_process_summary_rebuild",
                        reason=admission_reason,
                        command=quote_command,
                    ),
                    action="confirm_cached_process_summary_before_rebuild",
                    reason=(
                        "Cached-summary check is metadata-only; defer live process parsing "
                        "until host pressure clears."
                    ),
                    command=pressure_safe_command,
                )
                if fallback_command:
                    fallback_row = {
                        "action": str(
                            config.get("pressure_safe_fallback_action")
                            or "use_pressure_safe_summary_if_process_summary_missing"
                        ),
                        "reason": (
                            "If the cached process summary is still missing under host "
                            "pressure, stay on the no-git latency digest instead of "
                            "widening into live process parsing."
                        ),
                        "command": fallback_command,
                    }
                    if recommended:
                        recommended = [recommended[0], fallback_row, *recommended[1:]]
                    else:
                        recommended = [fallback_row]
                    shaped["pressure_safe_fallback_command"] = fallback_command
                if bounded_materialize_command:
                    bounded_row = {
                        "action": "materialize_bounded_process_summary_after_pressure_clears",
                        "reason": (
                            "After pressure clears, rebuild the process summary with a bounded "
                            "trace window before escalating to the full trace builder."
                        ),
                        "command": bounded_materialize_command,
                    }
                    if (
                        full_materialize_command
                        and full_materialize_command != bounded_materialize_command
                    ):
                        bounded_row["full_materialize_command"] = full_materialize_command
                    recommended = (
                        [*recommended, bounded_row] if recommended else [bounded_row]
                    )
                shaped["recommended_next"] = recommended
                return shaped
            shaped["suggested_command"] = quote_command
            shaped["recommended_next"] = _prepend_recommended_next(
                shaped.get("recommended_next"),
                action="recheck_host_pressure_before_process_summary_rebuild",
                reason=admission_reason,
                command=quote_command,
            )
        else:
            shaped["recommended_next"] = _prepend_recommended_next(
                shaped.get("recommended_next"),
                action="use_cached_summary_and_defer_force_live",
                reason=admission_reason,
                command=quote_command,
            )
    elif mode == "coordination":
        pressure_safe_command = str(config.get("pressure_safe_suggested_command") or "")
        if pressure_safe_command:
            shaped["deferred_suggested_command"] = original_suggested_command
            shaped["pressure_safe_suggested_command"] = pressure_safe_command
            shaped["host_pressure_command_roles"] = {
                "schema": "action_quote_host_pressure_command_roles_v0",
                "pressure_safe_now": pressure_safe_command,
                "deferred_after_pressure_clears": original_suggested_command,
                "pressure_recheck_command": quote_command,
            }
            shaped["suggested_command"] = pressure_safe_command
            shaped["drilldown_command"] = pressure_safe_command
            shaped["recommended_next"] = [
                {
                    "action": str(config.get("pressure_safe_action") or "use_pressure_safe_summary"),
                    "reason": (
                        "Host pressure is high; use the cheapest cached latency summary before "
                        "any git-probing or parallel work."
                    ),
                    "command": pressure_safe_command,
                },
                *_prepend_recommended_next(
                    shaped.get("recommended_next"),
                    action="defer_new_parallel_work",
                    reason=admission_reason,
                    command=quote_command,
                ),
            ]
        else:
            shaped["recommended_next"] = _prepend_recommended_next(
                shaped.get("recommended_next"),
                action="defer_new_parallel_work",
                reason=admission_reason,
                command=quote_command,
            )
    return shaped


def _host_pressure_include_processes_for_action(
    action_id: str,
    detail: Mapping[str, Any],
    config: Mapping[str, str],
) -> bool:
    include_processes = str(config.get("mode") or "") in HOST_PRESSURE_PROCESS_AWARE_MODES
    if not include_processes:
        return False
    if action_id == "session_yield_request":
        ranked_status = _as_mapping(detail.get("ranked_candidate")).get("status")
        if ranked_status in SESSION_YIELD_PROCESSLESS_RANK_STATUSES:
            return False
    return True


def _with_host_pressure_admission(
    repo_root: Path,
    action_id: str,
    detail: dict[str, Any],
    *,
    full: bool = False,
) -> dict[str, Any]:
    config = HOST_PRESSURE_ADMISSION_BY_ACTION.get(action_id)
    if not config:
        return detail
    include_processes = _host_pressure_include_processes_for_action(action_id, detail, config)
    admission_kwargs: dict[str, Any] = {"include_processes": include_processes}
    if full:
        admission_kwargs["full"] = True
    admission = _host_pressure_admission_quote(
        repo_root,
        config["workload_class"],
        **admission_kwargs,
    )
    return _apply_host_pressure_admission(action_id, detail, admission)


def _host_pressure_blocks_new_work(admission: Mapping[str, Any]) -> bool:
    return (
        admission.get("status") == "available"
        and admission.get("decision")
        in {"queue_until_pressure_clears", "require_operator_override"}
    )


def _with_deferred_host_pressure_admission(
    repo_root: Path,
    action_id: str,
    detail: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    config = HOST_PRESSURE_ADMISSION_BY_ACTION.get(action_id)
    if not config:
        return detail
    include_processes = _host_pressure_include_processes_for_action(action_id, detail, config)
    trace_path = repo_root / "state/observability/agent_trace/events.jsonl"
    quote_command = HOST_PRESSURE_PROCESS_COMMAND if include_processes else HOST_PRESSURE_FAST_COMMAND
    admission = {
        "schema": "action_quote_host_pressure_admission_v0",
        "status": "deferred_by_metadata_profile",
        "quote_command": quote_command,
        "profile_command": HOST_PRESSURE_PROFILE_COMMAND,
        "requested_workload_class": config["workload_class"],
        "decision": None,
        "recommendation_effect": "metadata_profile_only",
        "should_block_run": False,
        "deferred_reason": reason,
        "source": {
            "trace_path": str(trace_path.relative_to(repo_root))
            if trace_path.is_relative_to(repo_root)
            else str(trace_path),
            "event_limit": HOST_PRESSURE_EVENT_LIMIT,
            "include_processes": include_processes,
            "process_rows_policy": "sampled_for_launch_gate"
            if include_processes
            else "omitted_by_default",
        },
    }
    return _apply_host_pressure_admission(action_id, detail, admission)


def normalize_action_id(action_id: str) -> str:
    key = action_id.strip().replace("-", "_")
    return ACTION_ALIASES.get(key, key)


def _scope_paths(scope_paths: Sequence[str]) -> list[str]:
    return sorted({str(path).strip() for path in scope_paths if str(path).strip()})


def _path_overlaps(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def _active_claims_snapshot(repo_root: Path, *, limit: int = 50, allow_stale: bool = False) -> dict[str, Any]:
    return work_ledger_runtime.load_active_claims_snapshot(
        repo_root,
        limit=limit,
        allow_stale=allow_stale,
    )


def _claim_conflicts(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    limit: int = 8,
    snapshot: Mapping[str, Any] | None = None,
    current_session_id: str | None = None,
) -> list[dict[str, Any]]:
    scopes = _scope_paths(scope_paths)
    if not scopes:
        return []
    snapshot = snapshot or _active_claims_snapshot(repo_root, limit=max(limit, 50))
    rows: list[dict[str, Any]] = []
    for claim in (_as_mapping(row) for row in _as_list(snapshot.get("active_claims"))):
        if current_session_id and claim.get("session_id") == current_session_id:
            continue
        claim_path = str(claim.get("path") or "")
        if not claim_path:
            continue
        if not any(_path_overlaps(claim_path, scope) for scope in scopes):
            continue
        rows.append(
            {
                "claim_id": claim.get("claim_id"),
                "path": claim_path,
                "scope_kind": claim.get("scope_kind"),
                "session_id": claim.get("session_id"),
                "actor": claim.get("actor"),
                "leased_until": claim.get("leased_until"),
                "note": claim.get("note"),
            }
        )
    return rows[:limit]


def _wait_tax_match(
    repo_root: Path,
    *,
    owner_surface: str,
    resource_class: str,
    scope_paths: Sequence[str],
    full: bool = False,
) -> dict[str, Any]:
    speedboard = _read_json(repo_root / SPEEDBOARD_REL)
    generated_at = speedboard.get("generated_at")
    age_s = _age_seconds(generated_at)
    source_status = (
        "stale"
        if isinstance(age_s, (int, float)) and age_s > WAIT_TAX_STALE_AFTER_S
        else ("fresh" if isinstance(age_s, (int, float)) else "unknown")
    )
    scopes = _scope_paths(scope_paths)
    best: Mapping[str, Any] = {}
    for row in (_as_mapping(item) for item in _as_list(speedboard.get("ranked_wait_taxes"))):
        if owner_surface and row.get("owner_surface") != owner_surface:
            continue
        if resource_class and row.get("resource_class") != resource_class:
            continue
        argv_text = " ".join(str(arg) for arg in _as_list(row.get("example_argv")))
        if scopes and not any(scope in argv_text for scope in scopes):
            continue
        best = row
        break
    if not best:
        return {"status": "missing"}
    row_status = str(best.get("status") or "")
    status = "stale_match" if source_status == "stale" else "matched"
    actionability = (
        "advisory_only_stale_source"
        if source_status == "stale"
        else (
            "advisory_only_fixed_owner"
            if row_status == "fixed"
            else "actionable_wait_tax_signal"
        )
    )
    payload = {
        "status": status,
        "command_key": best.get("command_key"),
        "row_status": best.get("status"),
        "actionability": actionability,
        "should_block_run": False,
        "median_seconds": best.get("median_seconds"),
        "p95_seconds": best.get("p95_seconds"),
        "max_seconds": best.get("max_seconds"),
        "cumulative_seconds_24h": best.get("cumulative_seconds_24h"),
        "run_count_24h": best.get("run_count_24h"),
        "duplicate_run_count_24h": best.get("duplicate_run_count_24h"),
        "fresh_reusable_count_24h": best.get("fresh_reusable_count_24h"),
        "next_action": best.get("next_action"),
        "source_freshness": {
            "status": source_status,
            "generated_at": generated_at,
            "age_s": age_s,
            "stale_after_s": WAIT_TAX_STALE_AFTER_S,
            "refresh_command": "./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
            "mutation_status": "read_only_generated_projection",
        },
    }
    if full:
        payload["example_argv"] = best.get("example_argv")
    else:
        payload["compact_evidence_receipt"] = {
            "schema": "wait_tax_match_compact_evidence_v0",
            "status": "example_argv_omitted",
            "full_quote_flag": "--full",
            "omitted_field_count": 1,
        }
    return payload


def _pytest_has_option(args: Sequence[str], option: str) -> bool:
    return any(arg == option or str(arg).startswith(f"{option}=") for arg in args)


def _pytest_args_with_defaults(args: Sequence[str]) -> list[str]:
    values = [str(arg) for arg in args]
    if not _pytest_has_option(values, "--durations"):
        values.append("--durations=20")
    if not _pytest_has_option(values, "--durations-min"):
        values.append("--durations-min=0.1")
    return values


def _pytest_scope_paths(repo_root: Path, pytest_args: Sequence[str], explicit_scope: Sequence[str]) -> list[str]:
    paths = list(_scope_paths(explicit_scope))
    skip_next = False
    for arg in pytest_args:
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            break
        if arg in {"-k", "-m", "--maxfail", "--tb", "--durations", "--durations-min"}:
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        token = arg.split("::", 1)[0]
        candidate = Path(token)
        resolved = candidate if candidate.is_absolute() else repo_root / candidate
        if resolved.exists():
            paths.append(str(candidate))
    return _scope_paths(paths)


def _strip_wrapper_token(args: Sequence[str]) -> list[str]:
    values = [str(arg) for arg in args]
    if values and Path(values[0]).name == "repo-pytest":
        return values[1:]
    return values


def _is_direct_pytest_scope(scope: str) -> bool:
    token = str(scope).split("::", 1)[0]
    return token.startswith("system/server/tests/") and token.endswith(".py")


def _load_test_impact_selection(repo_root: Path, changed_paths: Sequence[str]) -> dict[str, Any] | None:
    selector_path = repo_root / "tools" / "meta" / "testing" / "select_impacted_tests.py"
    if not selector_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("_aiw_action_quote_select_impacted_tests", selector_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        payload = module.select(list(changed_paths))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _load_test_inventory_freshness(repo_root: Path) -> dict[str, Any]:
    inventory_path = repo_root / TEST_INVENTORY_REL
    tool_path = repo_root / TEST_INVENTORY_TOOL_REL
    payload: dict[str, Any] = {
        "projection_path": str(TEST_INVENTORY_REL),
        "owner_tool": str(TEST_INVENTORY_TOOL_REL),
        "check_command": "./repo-python tools/meta/testing/test_inventory.py --check",
        "refresh_command": "./repo-python tools/meta/testing/test_inventory.py --write --force-refresh",
        "status": "missing_projection",
    }
    existing = _read_json(inventory_path)
    if existing:
        summary = _as_mapping(existing.get("summary"))
        pytest_meta = _as_mapping(existing.get("pytest"))
        timings = _as_mapping(existing.get("timings"))
        source_fingerprint = _as_mapping(existing.get("source_fingerprint"))
        payload.update(
            {
                "status": "projection_available_freshness_unknown",
                "generated_at": existing.get("generated_at"),
                "age_s": _age_seconds(existing.get("generated_at")),
                "inventory_digest": summary.get("inventory_digest"),
                "test_file_count": summary.get("test_file_count"),
                "test_item_count": summary.get("test_item_count"),
                "collection_error_count": summary.get("collection_error_count"),
                "pytest_result_classification": pytest_meta.get("result_classification"),
                "pytest_collection_s": timings.get("pytest_collection_s"),
                "source_fingerprint_digest": source_fingerprint.get("digest"),
                "source_fingerprint_path_count": source_fingerprint.get("path_count"),
            }
        )
    if not tool_path.exists():
        payload["status"] = "owner_tool_missing" if existing else "missing_projection_and_owner_tool"
        return payload

    spec = importlib.util.spec_from_file_location("_aiw_action_quote_test_inventory", tool_path)
    if spec is None or spec.loader is None:
        payload["status"] = "owner_tool_unloadable"
        return payload
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        current_fingerprint = module.build_source_fingerprint()
    except Exception as exc:
        payload.update({"status": "freshness_check_failed", "error": str(exc)})
        return payload
    if not isinstance(current_fingerprint, dict):
        payload["status"] = "freshness_check_invalid"
        return payload
    existing_fingerprint = _as_mapping(existing.get("source_fingerprint")) if existing else {}
    try:
        fingerprints_match = bool(module._fingerprints_match(existing_fingerprint, current_fingerprint))
    except Exception:
        fingerprints_match = (
            existing_fingerprint.get("schema") == current_fingerprint.get("schema")
            and existing_fingerprint.get("digest") == current_fingerprint.get("digest")
            and existing_fingerprint.get("path_count") == current_fingerprint.get("path_count")
        )
    payload.update(
        {
            "status": "fresh" if existing and fingerprints_match else "stale",
            "current_source_fingerprint_digest": current_fingerprint.get("digest"),
            "current_source_fingerprint_path_count": current_fingerprint.get("path_count"),
            "fingerprints_match": bool(existing and fingerprints_match),
            "cache": _as_mapping(current_fingerprint.get("cache")),
        }
    )
    return payload


def _selector_route_for_source_scopes(repo_root: Path, scope_paths: Sequence[str]) -> dict[str, Any] | None:
    scopes = _scope_paths(scope_paths)
    if not scopes or all(_is_direct_pytest_scope(scope) for scope in scopes):
        return None
    selection = _load_test_impact_selection(repo_root, scopes)
    if selection is None:
        return None
    selected_tests = [
        str(item)
        for item in _as_list(selection.get("selected_test_items"))
        if str(item).strip()
    ]
    fallback_tests = [
        str(item)
        for item in _as_list(selection.get("fallback_tests"))
        if str(item).strip()
    ]
    validators = _as_list(selection.get("selected_validators"))
    if not selected_tests and not fallback_tests and not validators:
        return None
    provenance = _as_mapping(selection.get("provenance"))
    args: list[str] = []
    for scope in scopes:
        args.extend(["--changed", scope])
    args.append("--ci-strict")
    command = "./repo-python tools/meta/testing/run_test_slice.py " + shlex.join(args)
    return {
        "command": command,
        "argv": [str(repo_root / "repo-python"), "tools/meta/testing/run_test_slice.py", *args],
        "selected_test_count": len(selected_tests),
        "fallback_test_count": len(fallback_tests),
        "validator_count": len(validators),
        "fallback_used": bool(selection.get("fallback_used")),
        "fallback_bundle": selection.get("fallback_bundle"),
        "matched_selectors": [
            row.get("selector_id")
            for row in (_as_mapping(item) for item in _as_list(selection.get("matched_selectors")))
            if row.get("selector_id")
        ],
        "selection_reason": _as_list(selection.get("selection_reason"))[:8],
        "source_contract": {
            "entry_surface": str(RUN_TEST_SLICE_REL),
            "selector_owner": str(SELECT_IMPACTED_TESTS_REL),
            "declared_policy": str(TEST_IMPACT_MAP_REL),
            "inventory_projection": str(TEST_INVENTORY_REL),
            "inventory_owner_tool": str(TEST_INVENTORY_TOOL_REL),
            "inventory_check_route": "./repo-python tools/meta/testing/test_inventory.py --check",
            "full_inventory_authority_route": "./repo-python tools/meta/testing/test_inventory.py --write --force-refresh",
        },
        "inventory_projection": _load_test_inventory_freshness(repo_root),
        "provenance": {
            "graph_digest": provenance.get("graph_digest"),
            "inventory_digest": provenance.get("inventory_digest"),
            "impact_map_digest": provenance.get("impact_map_digest"),
            "selector_version": provenance.get("selector_version"),
        },
    }


def _parse_repo_pytest_args(args: Sequence[str]) -> tuple[list[str], str, bool, bool]:
    pytest_args: list[str] = []
    singleflight_policy = "auto"
    reuse_completed = False
    enable_plugin_autoload = False
    index = 0
    while index < len(args):
        arg = str(args[index])
        if arg == "--no-singleflight":
            singleflight_policy = "never"
        elif arg == "--reuse-completed":
            reuse_completed = True
        elif arg == "--enable-plugin-autoload":
            enable_plugin_autoload = True
        elif arg == "--singleflight-policy":
            if index + 1 < len(args):
                singleflight_policy = str(args[index + 1])
                index += 1
        elif arg.startswith("--singleflight-policy="):
            singleflight_policy = arg.split("=", 1)[1]
        else:
            pytest_args.append(arg)
        index += 1
    if singleflight_policy not in {"auto", "always", "never"}:
        singleflight_policy = "auto"
    return pytest_args, singleflight_policy, reuse_completed, enable_plugin_autoload


def _repo_pytest_singleflight_enabled(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    singleflight_policy: str,
    reuse_completed: bool,
    wait_tax: Mapping[str, Any] | None = None,
) -> bool:
    if os.environ.get("COMMAND_RUN_SINGLEFLIGHT_DISABLE"):
        return False
    if singleflight_policy == "always":
        return True
    if singleflight_policy == "never":
        return False
    if reuse_completed:
        return True
    scopes = _scope_paths(scope_paths)
    if len(scopes) != 1:
        return True
    candidate = Path(scopes[0])
    resolved = candidate if candidate.is_absolute() else repo_root / candidate
    if resolved.is_file():
        return _repo_pytest_single_file_wait_tax_slow(wait_tax)
    return True


def _repo_pytest_wait_tax_seconds(wait_tax: Mapping[str, Any] | None) -> float:
    row = _as_mapping(wait_tax)
    for key in ("p95_seconds", "max_seconds", "median_seconds"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return 0.0


def _repo_pytest_single_file_wait_tax_slow(
    wait_tax: Mapping[str, Any] | None,
) -> bool:
    row = _as_mapping(wait_tax)
    if row.get("status") not in {"matched", "stale_match"}:
        return False
    return (
        _repo_pytest_wait_tax_seconds(row)
        >= REPO_PYTEST_SINGLE_FILE_SINGLEFLIGHT_MIN_SECONDS
    )


def _repo_pytest_direct_slice_recommendation(
    scope_paths: Sequence[str],
    raw_repo_pytest_args: Sequence[str],
    *,
    inferred_from_scope: bool,
) -> dict[str, Any] | None:
    scopes = _scope_paths(scope_paths)
    if not inferred_from_scope or not scopes:
        return None
    if not all(_is_direct_pytest_scope(scope) for scope in scopes):
        return None
    if any("::" in scope for scope in scopes):
        return None
    args = [str(arg) for arg in raw_repo_pytest_args]
    if any(arg == "-k" or arg.startswith("-k") for arg in args):
        return None
    first_scope = scopes[0]
    return {
        "action": "prefer_node_or_keyword_slice_before_full_test_file",
        "reason": (
            "Recent test/build bottlenecks are focused-test shaped; use a node id "
            "or keyword slice when the changed behavior is narrower than the whole file."
        ),
        "command": f"./repo-pytest {shlex.quote(first_scope)}::<test_name> -q",
        "fallback_command": (
            f"./repo-pytest {shlex.quote(first_scope)} -q -k '<keyword>'"
        ),
        "full_file_command": "./repo-pytest " + " ".join(args),
        "applies_when": "test behavior is localized to a known test or keyword",
    }


def _singleflight_bypass_status(
    *,
    singleflight_policy: str,
    reuse_completed: bool,
    enable_plugin_autoload: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "available": False,
        "status": "bypassed",
        "policy": singleflight_policy,
        "reuse_completed": reuse_completed,
        "enable_plugin_autoload": enable_plugin_autoload,
        "reason": reason,
    }


def _singleflight_deferred_broad_status(
    *,
    singleflight_policy: str,
    reuse_completed: bool,
    enable_plugin_autoload: bool,
) -> dict[str, Any]:
    return {
        "available": True,
        "status": "deferred_broad_scope",
        "policy": singleflight_policy,
        "reuse_completed": reuse_completed,
        "enable_plugin_autoload": enable_plugin_autoload,
        "reason": "broad_scope_quote_defers_full_repo_dirty_fingerprint",
        "full_profile_required_for_key": True,
        "full_profile_command": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action repo_pytest_validation --full"
        ),
        "run_authority": "repo-pytest computes the exact singleflight key when launched",
    }


def _singleflight_status(
    repo_root: Path,
    *,
    argv: Sequence[str],
    resource_class: str,
    scope_paths: Sequence[str],
    singleflight_policy: str = "auto",
    reuse_completed: bool = False,
    enable_plugin_autoload: bool = False,
) -> dict[str, Any]:
    key = build_command_key(
        repo_root,
        argv=[str(arg) for arg in argv],
        cwd=repo_root,
        resource_class=resource_class,
        scope_paths=scope_paths,
        env=os.environ.copy(),
    )
    key_hash = _short_hash(key)
    paths = _state_paths(repo_root, key_hash)
    active = _read_json(paths["active"])
    latest = _read_json(paths["latest"])
    payload: dict[str, Any] = {
        "available": True,
        "key_hash": key_hash,
        "active_path": str(paths["active"].relative_to(repo_root)) if paths["active"].is_relative_to(repo_root) else str(paths["active"]),
        "latest_path": str(paths["latest"].relative_to(repo_root)) if paths["latest"].is_relative_to(repo_root) else str(paths["latest"]),
        "status": "cold",
        "policy": singleflight_policy,
        "reuse_completed": reuse_completed,
        "enable_plugin_autoload": enable_plugin_autoload,
    }
    if active.get("status") == "running" and (_pid_alive(active.get("pid")) or _active_pending(active)):
        payload.update(
            {
                "status": "running",
                "run_id": active.get("run_id"),
                "pid": active.get("pid"),
                "started_at": active.get("started_at"),
                "stdout_path": active.get("stdout_path"),
                "stderr_path": active.get("stderr_path"),
            }
        )
    elif active.get("status") == "completed":
        payload.update(
            {
                "status": "fresh_reusable",
                "run_id": active.get("run_id"),
                "exit_code": active.get("exit_code"),
                "duration_s": active.get("duration_s"),
                "completed_result_reuse_default": False,
            }
        )
    elif latest.get("status") == "completed":
        payload.update(
            {
                "status": "fresh_reusable",
                "run_id": latest.get("run_id"),
                "exit_code": latest.get("exit_code"),
                "duration_s": latest.get("duration_s"),
                "completed_result_reuse_default": False,
            }
        )
    return payload


def _quote_repo_pytest(
    repo_root: Path,
    scope_paths: Sequence[str],
    extra_args: Sequence[str],
    *,
    current_session_id: str | None = None,
    full: bool = False,
) -> dict[str, Any]:
    raw_repo_pytest_args = _strip_wrapper_token(extra_args)
    args_were_inferred_from_scope = not raw_repo_pytest_args
    if not raw_repo_pytest_args:
        raw_repo_pytest_args = [*scope_paths, "-q"] if scope_paths else ["-q"]
    raw_pytest_args, singleflight_policy, reuse_completed, enable_plugin_autoload = _parse_repo_pytest_args(raw_repo_pytest_args)
    pytest_args = _pytest_args_with_defaults(raw_pytest_args)
    scopes = _pytest_scope_paths(repo_root, pytest_args, scope_paths)
    selector_route = (
        _selector_route_for_source_scopes(repo_root, scopes)
        if args_were_inferred_from_scope
        else None
    )
    if selector_route is not None:
        claims_snapshot = _active_claims_snapshot(repo_root, limit=50)
        claim_conflicts = _claim_conflicts(
            repo_root,
            scopes,
            snapshot=claims_snapshot,
            current_session_id=current_session_id,
        )
        wait_tax = _wait_tax_match(
            repo_root,
            owner_surface="repo-pytest",
            resource_class="pytest",
            scope_paths=scopes,
            full=full,
        )
        raw_git_maintenance = build_git_maintenance_status(repo_root)
        git_maintenance = _compact_git_maintenance_status(
            raw_git_maintenance,
            full=full,
        )
        git_maintenance_recommendation = _repo_pytest_git_maintenance_recommendation(
            raw_git_maintenance
        )
        do_not_touch: list[dict[str, Any]] = []
        if claim_conflicts:
            do_not_touch.append(
                {
                    "lane": "claimed_scope",
                    "reason": "Work Ledger active claims overlap the requested validation scope.",
                    "paths": [row.get("path") for row in claim_conflicts if row.get("path")],
                    "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-claims",
                }
            )
        source_freshness = _as_mapping(claims_snapshot.get("source_freshness"))
        if source_freshness.get("status") == "stale":
            do_not_touch.append(
                {
                    "lane": "work_ledger_claims",
                    "reason": "Active-claims snapshot is stale; refresh before using claims as mutation authority.",
                    "command": source_freshness.get("refresh_command")
                    or "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
                }
            )
        return {
            "current_status": "selector_available",
            "recommendation": "run_focused_selector",
            "freshness": "selector_read_model",
            "authority_level": "focused_validation_selector",
            "drilldown_command": selector_route["command"],
            "suggested_command": selector_route["command"],
            "underlying_argv": selector_route["argv"],
            "scope_paths": scopes,
            "selector": selector_route,
            "singleflight": _singleflight_bypass_status(
                singleflight_policy=singleflight_policy,
                reuse_completed=reuse_completed,
                enable_plugin_autoload=enable_plugin_autoload,
                reason="selector_route_uses_run_test_slice",
            ),
            "wait_tax": wait_tax,
            "git_maintenance": git_maintenance,
            "recommended_next": [git_maintenance_recommendation]
            if git_maintenance_recommendation
            else [],
            "claim_conflicts": claim_conflicts,
            "claim_snapshot": {
                "status": claims_snapshot.get("status"),
                "source_freshness": source_freshness,
            },
            "current_session_id": current_session_id,
            "do_not_touch": do_not_touch,
        }
    argv = [str(repo_root / "repo-python"), "-m", "pytest", *pytest_args]
    wait_tax = _wait_tax_match(
        repo_root,
        owner_surface="repo-pytest",
        resource_class="pytest",
        scope_paths=scopes,
        full=full,
    )
    singleflight_enabled = _repo_pytest_singleflight_enabled(
        repo_root,
        scopes,
        singleflight_policy=singleflight_policy,
        reuse_completed=reuse_completed,
        wait_tax=wait_tax,
    )
    broad_scope_key_deferred = bool(singleflight_enabled and not scopes and not reuse_completed and not full)
    if broad_scope_key_deferred:
        singleflight = _singleflight_deferred_broad_status(
            singleflight_policy=singleflight_policy,
            reuse_completed=reuse_completed,
            enable_plugin_autoload=enable_plugin_autoload,
        )
    elif singleflight_enabled:
        singleflight = _singleflight_status(
            repo_root,
            argv=argv,
            resource_class="pytest",
            scope_paths=scopes,
            singleflight_policy=singleflight_policy,
            reuse_completed=reuse_completed,
            enable_plugin_autoload=enable_plugin_autoload,
        )
    else:
        if os.environ.get("COMMAND_RUN_SINGLEFLIGHT_DISABLE"):
            reason = "env_disables_singleflight"
        elif singleflight_policy == "never":
            reason = "repo_pytest_singleflight_policy_never"
        else:
            reason = "repo_pytest_auto_policy_skips_single_file"
        singleflight = _singleflight_bypass_status(
            singleflight_policy=singleflight_policy,
            reuse_completed=reuse_completed,
            enable_plugin_autoload=enable_plugin_autoload,
            reason=reason,
        )
    claims_snapshot = _active_claims_snapshot(repo_root, limit=50)
    claim_conflicts = _claim_conflicts(
        repo_root,
        scopes,
        snapshot=claims_snapshot,
        current_session_id=current_session_id,
    )
    raw_git_maintenance = build_git_maintenance_status(repo_root)
    git_maintenance = _compact_git_maintenance_status(
        raw_git_maintenance,
        full=full,
    )
    git_maintenance_recommendation = _repo_pytest_git_maintenance_recommendation(
        raw_git_maintenance
    )
    do_not_touch: list[dict[str, Any]] = []
    if claim_conflicts:
        do_not_touch.append(
            {
                "lane": "claimed_scope",
                "reason": "Work Ledger active claims overlap the requested validation scope.",
                "paths": [row.get("path") for row in claim_conflicts if row.get("path")],
                "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-claims",
            }
        )
    source_freshness = _as_mapping(claims_snapshot.get("source_freshness"))
    if source_freshness.get("status") == "stale":
        do_not_touch.append(
            {
                "lane": "work_ledger_claims",
                "reason": "Active-claims snapshot is stale; refresh before using claims as mutation authority.",
                "command": source_freshness.get("refresh_command")
                or "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
            }
        )
    if claim_conflicts:
        recommendation = "defer_or_resolve_claim_conflict"
    elif singleflight["status"] == "running":
        recommendation = "attach_to_running_singleflight"
    elif singleflight["status"] == "fresh_reusable":
        recommendation = "run_or_reuse_completed_explicitly"
    else:
        recommendation = "run_through_repo_pytest"
    freshness = "live" if singleflight["status"] == "running" else ("fresh" if singleflight["status"] == "fresh_reusable" else "unknown")
    current_status = singleflight["status"] if singleflight["status"] != "bypassed" else "cold"
    direct_slice_recommendation = _repo_pytest_direct_slice_recommendation(
        scopes,
        raw_repo_pytest_args,
        inferred_from_scope=args_were_inferred_from_scope,
    )
    recommended_next = [
        row
        for row in (git_maintenance_recommendation, direct_slice_recommendation)
        if row
    ]
    return {
        "current_status": current_status,
        "recommendation": recommendation,
        "freshness": freshness,
        "authority_level": "focused_validation",
        "drilldown_command": "./repo-pytest " + " ".join(raw_repo_pytest_args),
        "suggested_command": "./repo-pytest " + " ".join(raw_repo_pytest_args),
        "underlying_argv": argv,
        "scope_paths": scopes,
        "singleflight": singleflight,
        "output_profile": "fast_broad_default" if broad_scope_key_deferred else "full_or_scoped",
        "full_profile_command": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action repo_pytest_validation --full"
        )
        if broad_scope_key_deferred
        else None,
        "wait_tax": wait_tax,
        "git_maintenance": git_maintenance,
        "recommended_next": recommended_next,
        "claim_conflicts": claim_conflicts,
        "claim_snapshot": {
            "status": claims_snapshot.get("status"),
            "source_freshness": source_freshness,
        },
        "current_session_id": current_session_id,
        "do_not_touch": do_not_touch,
    }


def _quote_latency_seed_preflight(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    current_session_id: str | None = None,
    include_git: bool = True,
) -> dict[str, Any]:
    digest = build_latency_seed_digest(repo_root, include_git=include_git, top_n=8)
    speedboard = _as_mapping(digest.get("speedboard"))
    process_summary = _as_mapping(digest.get("process_summary"))
    claims = _as_mapping(digest.get("active_claims"))
    git_maintenance = _as_mapping(digest.get("git_maintenance"))
    claim_conflicts = _claim_conflicts(repo_root, scope_paths, current_session_id=current_session_id)
    dirty_lanes = [
        row
        for row in (_as_mapping(item) for item in _as_list(digest.get("latency_lanes")))
        if row.get("dirty_path_count")
    ]
    claimed_lanes = [
        row
        for row in (_as_mapping(item) for item in _as_list(claims.get("claimed_latency_lanes")))
        if not current_session_id or current_session_id not in set(str(session) for session in _as_list(row.get("sessions")))
    ]
    status = "read_models_available" if any(
        row.get("status") == "available" for row in (speedboard, process_summary, claims)
    ) else "missing_read_models"
    recommendation = "use_latency_seed_digest"
    if claim_conflicts:
        recommendation = "avoid_claimed_scope"
    elif dirty_lanes or claimed_lanes:
        recommendation = "use_digest_then_avoid_claimed_or_dirty_lanes"
    stale_sources = [
        name
        for name, row in (
            ("speedboard", speedboard),
            ("process_summary", process_summary),
            ("active_claims", claims),
        )
        if row.get("status") in {"stale", "stale_allowed"} or row.get("age_s", 0) and row.get("age_s", 0) > 600
    ]
    freshness = "stale" if stale_sources else ("fresh" if status == "read_models_available" else "unknown")
    do_not_touch = [
        {
            "lane": row.get("lane_id"),
            "reason": "Latency owner lane already has dirty paths.",
            "paths": [path.get("path") for path in _as_list(row.get("dirty_paths"))],
            "owner": row.get("owner"),
        }
        for row in dirty_lanes
    ]
    do_not_touch.extend(
        {
            "lane": row.get("lane_id"),
            "reason": "Latency owner lane has active Work Ledger claims.",
            "claim_ids": row.get("claim_ids"),
            "claimed_paths": row.get("claimed_paths"),
            "owner": row.get("owner"),
        }
        for row in (_as_mapping(item) for item in claimed_lanes)
    )
    return {
        "current_status": status,
        "recommendation": recommendation,
        "freshness": freshness,
        "authority_level": "cached_read_model",
        "drilldown_command": f"{LATENCY_SEED_DIGEST_COMMAND} --latency-seed-top 8",
        "suggested_command": LATENCY_SEED_DIGEST_COMMAND,
        "scope_paths": _scope_paths(scope_paths),
        "claim_conflicts": claim_conflicts,
        "current_session_id": current_session_id,
        "do_not_touch": do_not_touch,
        "stale_sources": stale_sources,
        "recommended_next": _as_list(digest.get("recommended_next")),
        "read_models": {
            "speedboard": {
                "path": speedboard.get("path") or str(SPEEDBOARD_REL),
                "status": speedboard.get("status") or "missing",
                "generated_at": speedboard.get("generated_at"),
                "measurement_count": speedboard.get("measurement_count"),
                "age_s": speedboard.get("age_s"),
                "ranked_wait_tax_count": speedboard.get("ranked_wait_tax_count"),
                "top_wait_tax": speedboard.get("top_wait_tax"),
            },
            "process_summary": {
                "path": process_summary.get("path") or str(PROCESS_SUMMARY_REL),
                "status": process_summary.get("status") or "missing",
                "generated_at": process_summary.get("generated_at"),
                "age_s": _age_seconds(process_summary.get("generated_at")),
                "top_bottlenecks": _as_list(process_summary.get("top_bottlenecks")),
                "top_output_producers": _as_list(process_summary.get("top_output_producers")),
            },
            "active_claims": {
                "path": claims.get("path") or str(ACTIVE_CLAIMS_REL),
                "status": claims.get("status") or "missing",
                "generated_at": claims.get("generated_at"),
                "active_claims": _as_mapping(claims.get("counts")).get("active_claims"),
                "latency_relevant_claim_count": claims.get("latency_relevant_claim_count"),
                "active_seed_first_action": claims.get("active_seed_first_action"),
            },
            "git_maintenance": {
                "status": git_maintenance.get("status") or "missing",
                "object_store_status": git_maintenance.get("object_store_status"),
                "maintenance_admission": git_maintenance.get("maintenance_admission"),
                "repair_status": git_maintenance.get("repair_status"),
                "repair_reentry": git_maintenance.get("repair_reentry"),
                "tmp_object_count": git_maintenance.get("tmp_object_count"),
                "recent_tmp_object_count": git_maintenance.get("recent_tmp_object_count"),
                "min_tmp_age_seconds": git_maintenance.get("min_tmp_age_seconds"),
                "lockfile_count": git_maintenance.get("lockfile_count"),
                "blocking_lockfile_count": git_maintenance.get("blocking_lockfile_count"),
                "stale_gc_pid_count": git_maintenance.get("stale_gc_pid_count"),
                "blocking_git_process_count": git_maintenance.get("blocking_git_process_count"),
                "blocking_process_family_count": git_maintenance.get("blocking_process_family_count"),
                "repair_command": git_maintenance.get("repair_command"),
                "check_command": git_maintenance.get("check_command"),
                "owner": git_maintenance.get("owner"),
            },
        },
        "speedboard_summary_available": bool(speedboard.get("measurement_count")),
    }


def _quote_work_ledger_claim_read(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    current_session_id: str | None = None,
) -> dict[str, Any]:
    snapshot = _active_claims_snapshot(repo_root, limit=50)
    conflicts = _claim_conflicts(
        repo_root,
        scope_paths,
        snapshot=snapshot,
        current_session_id=current_session_id,
    )
    status = snapshot.get("status") or ("available" if snapshot else "missing")
    recommendation = "use_active_claims_snapshot" if status in {"fresh", "stale_allowed"} else "refresh_session_claims"
    freshness = "fresh" if status == "fresh" else ("stale" if status in {"stale", "stale_allowed"} else "unknown")
    source_freshness = _as_mapping(snapshot.get("source_freshness"))
    do_not_touch = []
    if conflicts:
        do_not_touch.append(
            {
                "lane": "claimed_scope",
                "reason": "Requested scope overlaps active Work Ledger claims.",
                "paths": [row.get("path") for row in conflicts if row.get("path")],
                "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-claims",
            }
        )
    if freshness == "stale":
        do_not_touch.append(
            {
                "lane": "work_ledger_claims",
                "reason": "Claim snapshot is stale and must be refreshed before mutation decisions.",
                "command": source_freshness.get("refresh_command") or WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
            }
        )
    return {
        "current_status": status,
        "recommendation": recommendation,
        "freshness": freshness,
        "authority_level": "cached_read_model",
        "drilldown_command": WORK_LEDGER_CLAIM_CARDS_COMMAND,
        "suggested_command": WORK_LEDGER_CLAIM_CARDS_COMMAND,
        "full_claims_command": WORK_LEDGER_FULL_CLAIMS_COMMAND,
        "refresh_command": WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
        "mutation_check_command": "./repo-python tools/meta/factory/work_ledger.py mutation-check --path <path> --require-exclusive",
        "scope_paths": _scope_paths(scope_paths),
        "claim_conflicts": conflicts,
        "current_session_id": current_session_id,
        "do_not_touch": do_not_touch,
        "counts": _as_mapping(snapshot.get("counts")),
        "source_freshness": source_freshness,
        "source_generated_at": snapshot.get("generated_at"),
    }


def _quote_work_ledger_session_preflight(
    scope_paths: Sequence[str],
    *,
    current_session_id: str | None = None,
) -> dict[str, Any]:
    scopes = _scope_paths(scope_paths)
    session_arg = (
        f"--session-id {shlex.quote(current_session_id)} "
        if current_session_id
        else "--session-slug <slug> "
    )
    path_args = " ".join(f"--path {shlex.quote(path)}" for path in scopes)
    heartbeat_scope_args = " ".join(
        f"--heartbeat-scope-ref {shlex.quote(path)}" for path in scopes
    )
    suggested_parts = [
        "./repo-python tools/meta/factory/work_ledger.py session-preflight",
        session_arg.strip(),
        "--actor <actor>",
        "--phase-id <phase-id>",
        "--family-id <family-id>",
        path_args,
        "--work-admission-class edit_light_patch",
        "--require-exclusive",
        "--heartbeat-state inspecting",
        "--heartbeat-current-pass-line '<public current pass>'",
        heartbeat_scope_args,
    ]
    suggested_command = " ".join(part for part in suggested_parts if part).strip()
    return {
        "current_status": "session_preflight_command_template_available",
        "recommendation": "use_serial_session_preflight_for_bootstrap_claim_and_heartbeat",
        "freshness": "live_cli_contract",
        "authority_level": "cli_contract",
        "suggested_command": suggested_command,
        "replacement_command": suggested_command,
        "drilldown_command": "./repo-python tools/meta/factory/work_ledger.py session-preflight --help",
        "help_command": "./repo-python tools/meta/factory/work_ledger.py session-preflight --help",
        "scope_paths": scopes,
        "current_session_id": current_session_id,
        "claim_flags": ["--path", "--td-id", "--write-profile"],
        "heartbeat_flags": [
            "--heartbeat-state",
            "--heartbeat-current-pass-line",
            "--heartbeat-last-pass-result-line",
            "--heartbeat-scope-ref",
        ],
        "closeout_rule": (
            "Finalize only after a Work Ledger append, or use session-finalize "
            "--append-exempt-* for commit-only/projection-only sessions."
        ),
        "do_not_touch": [
            {
                "lane": "parallel_session_bootstrap_then_claim",
                "reason": "session-preflight serializes bootstrap, claims, optional imports, and heartbeat in one lane.",
                "replacement": suggested_command,
            },
            {
                "lane": "guessed_session_start_metadata_flags",
                "reason": "session-start is session-bootstrap and does not accept title/body/scope-ref flags.",
                "avoid": "session-start --title ... --body ... --scope-ref ...",
                "replacement": suggested_command,
            },
            {
                "lane": "bare_finalize_without_append_or_append_exempt",
                "reason": "touched sessions must append Work Ledger evidence or record an append-exempt closeout before finalize releases claims.",
                "replacement": (
                    "./repo-python tools/meta/factory/work_ledger.py session-finalize "
                    "--session-id <session-id> --read-receipt-id <receipt> "
                    "--append-exempt-reason '<commit-or-projection-closeout>' "
                    "--append-exempt-ref '<commit-or-receipt-ref>'"
                ),
            },
        ],
        "output_economy": {
            "emits_runtime_status_full_body": False,
            "full_diagnostics_flag": "--full",
            "raw_full_guard": "Use --raw-full only for selected lifecycle diagnostics.",
        },
    }


def _quote_work_ledger_heartbeat(
    scope_paths: Sequence[str],
    *,
    current_session_id: str | None = None,
) -> dict[str, Any]:
    scopes = _scope_paths(scope_paths)
    session = current_session_id or "<session-id>"
    scope_ref = scopes[0] if scopes else "<path-or-claim>"
    suggested_command = (
        "./repo-python tools/meta/factory/work_ledger.py session-heartbeat "
        f"--session-id {shlex.quote(session)} "
        "--state inspecting "
        "--current-pass-line '<public current pass>' "
        "--last-pass-result-line '<public previous result>' "
        f"--scope-ref {shlex.quote(scope_ref)}"
    )
    return {
        "current_status": "heartbeat_command_template_available",
        "recommendation": "use_session_heartbeat_state_flag_not_pass_state",
        "freshness": "live_cli_contract",
        "authority_level": "cli_contract",
        "suggested_command": suggested_command,
        "drilldown_command": "./repo-python tools/meta/factory/work_ledger.py session-heartbeat --help",
        "help_command": "./repo-python tools/meta/factory/work_ledger.py session-heartbeat --help",
        "scope_paths": scopes,
        "current_session_id": current_session_id,
        "accepted_state_values": [
            "blocked",
            "closing",
            "done",
            "editing",
            "idle",
            "inspecting",
            "landing",
            "mutating",
            "orienting",
            "validate",
            "validating",
            "validation",
        ],
        "required_flags": ["--session-id"],
        "public_line_flags": ["--current-pass-line", "--last-pass-result-line"],
        "repeatable_flags": ["--scope-ref"],
        "do_not_touch": [
            {
                "lane": "guessed_heartbeat_state_flag",
                "reason": "session-heartbeat accepts --state; --pass-state is not a valid flag.",
                "avoid": "--pass-state",
                "replacement": "--state",
            },
            {
                "lane": "raw_transcript_heartbeat_text",
                "reason": "Heartbeat text is public coordination metadata, not a transcript summary.",
                "replacement": "--current-pass-line '<public current pass>'",
            },
        ],
        "output_economy": {
            "emits_runtime_status_full_body": False,
            "full_runtime_after_help_only": True,
            "stores_stdout_stderr_bodies": False,
        },
    }


def _quote_task_ledger_validate(repo_root: Path) -> dict[str, Any]:
    owner_exists = (repo_root / TASK_LEDGER_APPLY_REL).is_file()
    routine_command = TASK_LEDGER_AUTHORITY_HEALTH_PROJECTION_CHECK_COMMAND
    strict_command = TASK_LEDGER_VALIDATE_COMMAND
    allow_warnings_command = TASK_LEDGER_VALIDATE_ALLOW_WARNINGS_COMMAND
    return {
        "current_status": "owner_surface_available" if owner_exists else "owner_surface_missing",
        "recommendation": "run_fast_authority_projection_health_for_routine_closeout",
        "freshness": "live_on_invocation",
        "authority_level": "read_only_event_projection_validation",
        "drilldown_command": routine_command,
        "suggested_command": routine_command,
        "routine_check_command": routine_command,
        "deep_validate_command": allow_warnings_command,
        "strict_command": strict_command,
        "allow_warnings_command": allow_warnings_command,
        "valid_options": ["authority-health --projection-check", "validate --allow-warnings"],
        "unsupported_flags": ["--subject-id", "--quiet-progress", "--rebuild"],
        "warning_policy": {
            "default": "strict_payload_exit_code",
            "closeout_recommended": "authority_health_projection_check_first",
            "allow_warnings_semantics": (
                "Exit 0 for valid_with_warnings when error_count is 0; payload ok is preserved."
            ),
        },
        "recommended_sequence": [
            {
                "action": "routine_authority_projection_health",
                "command": routine_command,
            },
            {
                "action": "deep_validate_if_health_fails_or_strict_evidence_needed",
                "command": allow_warnings_command,
                "condition": "authority health reports projection or event integrity drift",
            },
            {
                "action": "inspect_strict_payload_if_exit_behavior_matters",
                "command": strict_command,
                "condition": "warnings need triage or strict exit behavior matters",
            },
        ],
        "do_not_touch": [
            {
                "lane": "subject_scoped_validate",
                "reason": "Task Ledger validate has no --subject-id flag; validation is global event/projection integrity.",
                "unsupported_command_shape": f"{strict_command} --subject-id <id>",
                "replacement": routine_command,
            },
            {
                "lane": "quiet_progress_validate",
                "reason": "The validate subcommand does not define --quiet-progress; that flag belongs to mutation commands.",
                "unsupported_command_shape": f"{strict_command} --quiet-progress",
                "replacement": routine_command,
            },
        ],
        "source": {
            "owner_surface": str(TASK_LEDGER_APPLY_REL),
            "owner_surface_exists": owner_exists,
            "routine_function": "tools/meta/factory/task_ledger_apply.py::authority_health",
            "validation_function": "system/lib/task_ledger_events.py::validate_event_log",
            "parser_source": "tools/meta/factory/task_ledger_apply.py::build_parser",
        },
        "output_economy": {
            "routine_check_reads_projection_manifest_fast_path": True,
            "deep_validate_reads_event_log": True,
            "mutates_task_ledger": False,
            "rebuilds_views": False,
            "scope": "global_task_ledger_projection",
            "routine_check_command_profile": (
                "./repo-python kernel.py --command-profile task-ledger-exact"
            ),
        },
    }


def _quote_task_ledger_rebuild_status(repo_root: Path) -> dict[str, Any]:
    owner_exists = (repo_root / TASK_LEDGER_APPLY_REL).is_file()
    return {
        "current_status": "owner_surface_available" if owner_exists else "owner_surface_missing",
        "recommendation": "check_task_ledger_projection_status_before_full_rebuild",
        "freshness": "live_on_invocation",
        "authority_level": "status_only_projection_freshness_check",
        "drilldown_command": TASK_LEDGER_REBUILD_STATUS_COMMAND,
        "suggested_command": TASK_LEDGER_REBUILD_STATUS_COMMAND,
        "status_only_command": TASK_LEDGER_REBUILD_STATUS_COMMAND,
        "full_rebuild_command": TASK_LEDGER_REBUILD_COMMAND,
        "append_first_command_shape": (
            "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
            "--projection-rebuild-policy off ..."
        ),
        "valid_options": [
            "rebuild --status-only --quiet-progress",
            "quick-capture --projection-rebuild-policy off",
            "rebuild --ignore-host-pressure",
        ],
        "rebuild_priority_model": {
            "small_active_delta": (
                "authority-only closeout can continue; rebuild only for card/projection visibility"
            ),
            "medium_or_high_delta": "run owner rebuild or drain queued rebuild when projection visibility matters",
            "status_source": "rebuild --status-only --quiet-progress :: rebuild_priority",
        },
        "full_rebuild_allowed_when": [
            "status-only check reports medium/high rebuild_priority",
            "status-only check reports low rebuild_priority but card/projection visibility is required",
            "operator explicitly asks to rebuild Task Ledger projections",
        ],
        "do_not_touch": [
            {
                "lane": "full_rebuild_first_contact",
                "reason": (
                    "Full Task Ledger rebuilds are expensive and noisy; run the status-only "
                    "projection check before rebuilding."
                ),
                "avoid": TASK_LEDGER_REBUILD_COMMAND,
                "replacement": TASK_LEDGER_REBUILD_STATUS_COMMAND,
            },
            {
                "lane": "piped_rebuild_tail",
                "reason": (
                    "Piping rebuild output through tail hides wait tax and drops the structured "
                    "status fields needed for routing."
                ),
                "avoid": f"{TASK_LEDGER_REBUILD_COMMAND} 2>&1 | tail -20",
                "replacement": TASK_LEDGER_REBUILD_STATUS_COMMAND,
            },
        ],
        "source": {
            "owner_surface": str(TASK_LEDGER_APPLY_REL),
            "owner_surface_exists": owner_exists,
            "parser_source": "tools/meta/factory/task_ledger_apply.py::build_parser",
            "process_hint_source": "codex/hologram/process/summary.json::repo_tool_command",
        },
        "output_economy": {
            "mutates_task_ledger": False,
            "status_only_first": True,
            "full_rebuild_mutates_projection": True,
            "append_authority_before_projection_rebuild": True,
            "scope": "global_task_ledger_projection",
        },
    }


def _quote_storage_doctor_status(repo_root: Path) -> dict[str, Any]:
    owner_exists = (repo_root / "tools/meta/storage_doctor.py").is_file()
    return {
        "current_status": "owner_surface_available" if owner_exists else "owner_surface_missing",
        "recommendation": "check_storage_doctor_card_before_applying_cleanup",
        "freshness": "live_on_invocation",
        "authority_level": "read_only_storage_pressure_card",
        "drilldown_command": STORAGE_DOCTOR_STATUS_COMMAND,
        "suggested_command": STORAGE_DOCTOR_STATUS_COMMAND,
        "status_command": STORAGE_DOCTOR_STATUS_COMMAND,
        "safe_cleanup_command": STORAGE_DOCTOR_SAFE_CLEAN_COMMAND,
        "valid_options": [
            "scan --top 0 --format card",
            "clean --scope all --level safe --apply --yes --format card",
            "clean --scope all --level caution --smart --format card",
        ],
        "safe_cleanup_allowed_when": [
            "storage card shows nonzero safe_human or cleanup_candidate_human",
            "disk pressure is active and the storage card identifies safe cleanup candidates",
            "operator explicitly requests safe cleanup",
        ],
        "do_not_touch": [
            {
                "lane": "safe_cleanup_first_contact",
                "reason": (
                    "Safe cleanup still walks storage candidates and may delete scratch; check "
                    "the compact card first so low-value cleanup is skipped."
                ),
                "avoid": STORAGE_DOCTOR_SAFE_CLEAN_COMMAND,
                "replacement": STORAGE_DOCTOR_STATUS_COMMAND,
            },
            {
                "lane": "piped_storage_cleanup_tail",
                "reason": (
                    "Redirecting storage cleanup to /tmp and tailing it hides the structured "
                    "cleanup summary and repeats a costly scan."
                ),
                "avoid": f"{STORAGE_DOCTOR_SAFE_CLEAN_COMMAND} > /tmp/storage_safe_clean.log",
                "replacement": STORAGE_DOCTOR_STATUS_COMMAND,
            },
        ],
        "source": {
            "owner_surface": "tools/meta/storage_doctor.py",
            "owner_surface_exists": owner_exists,
            "parser_source": "tools/meta/storage_doctor.py::main",
            "process_hint_source": "codex/hologram/process/summary.json::repo_tool_command",
        },
        "output_economy": {
            "mutates_storage": False,
            "status_card_first": True,
            "safe_cleanup_mutates_storage": True,
            "scope": "host_and_repo_storage_pressure",
        },
    }


def _quote_task_ledger_quick_capture(repo_root: Path) -> dict[str, Any]:
    owner_exists = (repo_root / TASK_LEDGER_APPLY_REL).is_file()
    return {
        "current_status": "owner_surface_available" if owner_exists else "owner_surface_missing",
        "recommendation": "append_capture_authority_without_projection_rebuild_first",
        "freshness": "live_cli_contract",
        "authority_level": "cli_contract_append_only",
        "drilldown_command": "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --help",
        "suggested_command": TASK_LEDGER_QUICK_CAPTURE_COMMAND_SHAPE,
        "replacement_command": TASK_LEDGER_QUICK_CAPTURE_COMMAND_SHAPE,
        "append_only_command_shape": TASK_LEDGER_QUICK_CAPTURE_COMMAND_SHAPE,
        "summary_file_command_shape": (
            "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
            "--title '<title>' --summary-file <unique-file> --problem-file <unique-file> "
            "--impact-file <unique-file> --acceptance-file <unique-file> --created-by <agent> "
            "--confidence 0.85 --tag <tag> --projection-rebuild-policy off --compact"
        ),
        "stdin_command_shape": (
            "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
            "--title '<title>' --summary-stdin --created-by <agent> "
            "--confidence 0.85 --tag <tag> --projection-rebuild-policy off --compact"
        ),
        "valid_options": [
            "--title",
            "--summary/--statement/--note/--problem/--impact/--acceptance",
            "--summary-file/--statement-file/--note-file/--problem-file/--impact-file/--acceptance-file",
            "--summary-stdin/--statement-stdin/--note-stdin/--problem-stdin/--impact-stdin/--acceptance-stdin",
            "--evidence",
            "--tag",
            "--confidence",
            "--created-by",
            "--projection-rebuild-policy off",
            "--compact",
        ],
        "unsupported_flags": [
            "--description",
            "--body",
            "--scope-ref",
            "--quiet",
        ],
        "recommended_sequence": [
            {
                "action": "append_authority_event",
                "command": TASK_LEDGER_QUICK_CAPTURE_COMMAND_SHAPE,
            },
            {
                "action": "defer_projection_visibility_until_needed",
                "command": TASK_LEDGER_REBUILD_STATUS_COMMAND,
                "condition": "card/projection visibility matters after append",
            },
            {
                "action": "rebuild_or_drain_projection_only_when_needed",
                "command": TASK_LEDGER_REBUILD_COMMAND,
                "condition": "status-only check reports required/medium/high rebuild priority",
            },
        ],
        "do_not_touch": [
            {
                "lane": "unsupported_description_flag",
                "reason": "quick-capture has --summary/--statement/--note fields, not --description.",
                "unsupported_command_shape": "quick-capture --description '<text>'",
                "replacement": TASK_LEDGER_QUICK_CAPTURE_COMMAND_SHAPE,
            },
            {
                "lane": "capture_plus_projection_rebuild_by_default",
                "reason": "Capture authority first; projection/card visibility can be rebuilt later when needed.",
                "avoid": "quick-capture --rebuild",
                "replacement": TASK_LEDGER_QUICK_CAPTURE_COMMAND_SHAPE,
            },
            {
                "lane": "parallel_task_ledger_mutation",
                "reason": "Task Ledger mutations are single-writer operations; run captures sequentially.",
                "replacement": "Run one quick-capture at a time or use the batch lane for one logical closeout.",
            },
        ],
        "source": {
            "owner_surface": str(TASK_LEDGER_APPLY_REL),
            "owner_surface_exists": owner_exists,
            "parser_source": "tools/meta/factory/task_ledger_apply.py::build_parser",
            "authority": "state/task_ledger/events.jsonl",
        },
        "output_economy": {
            "mutates_task_ledger_authority": True,
            "projection_rebuild_default": "off",
            "emits_full_projection": False,
            "compact_output_preferred": True,
            "single_writer_required": True,
            "visibility_receipt_expected": True,
        },
    }


def _scope_mentions_task_ledger_quick_capture(scope_paths: Sequence[str]) -> bool:
    scope_text = " ".join(_scope_paths(scope_paths)).lower().replace("_", "-")
    if not scope_text:
        return False
    return any(
        term in scope_text
        for term in (
            "quick-capture",
            "quick capture",
            "task-ledger-capture",
            "task ledger capture",
        )
    )


def _scope_mentions_storage_doctor(scope_paths: Sequence[str]) -> bool:
    scope_text = " ".join(_scope_paths(scope_paths)).lower()
    return (
        "storage_doctor" in scope_text
        or "storage-doctor" in scope_text
        or "tools.meta.storage_doctor" in scope_text
        or "tools/meta/storage_doctor.py" in scope_text
    )


def _process_bottleneck_top_row(
    row: Mapping[str, Any],
    *,
    include_repair_hints: bool = True,
    selected_action_kind: str | None = None,
) -> dict[str, Any] | None:
    if not row:
        return None
    repair_hints = _as_list(row.get("repair_hints"))
    action_kind = row.get("action_kind")
    shaped = {
        "action_kind": row.get("action_kind"),
        "count": row.get("count"),
        "p95_ms": row.get("p95_ms"),
        "max_ms": row.get("max_ms"),
        "slow_count": row.get("slow_count"),
        "threshold_ms": row.get("threshold_ms"),
        "total_duration_ms": row.get("total_duration_ms"),
        "first_hint": (
            _as_mapping(repair_hints[0]).get("hint_id")
            if repair_hints
            else None
        ),
    }
    if include_repair_hints:
        shaped["repair_hints"] = repair_hints
    if selected_action_kind:
        shaped["same_as_selected"] = str(action_kind or "") == selected_action_kind
    return shaped


def _process_bottleneck_shape_repair(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    action_kind = str(row.get("action_kind") or "")
    repair_hints = _as_list(row.get("repair_hints"))
    hint_ids = {
        str(_as_mapping(hint).get("hint_id") or "")
        for hint in repair_hints
        if _as_mapping(hint).get("hint_id")
    }
    if "replace_python_module_tail_with_compact_cli_mode" in hint_ids:
        return {
            "status": "replacement_route_available",
            "action_kind": action_kind,
            "primary_replacement": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action command_surface --scope <module-or-command>"
            ),
            "recommended_sequence": [
                (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action command_surface --scope <module-or-command>"
                ),
                "python -m <module> --help",
                "Use or add the compact/json/status mode exposed by the owning module CLI.",
            ],
            "do_not_use": [
                "python -m <module> 2>&1 | tail/head",
                "cat/tail of full Python module CLI output as the only status surface",
            ],
            "why": (
                "Python module CLI bottlenecks should route through command-surface discovery "
                "or a compact module flag, not through generic git-state snapshots."
            ),
        }
    if "replace_inline_python_data_probe_with_owner_tool" in hint_ids:
        return {
            "status": "replacement_route_available",
            "action_kind": action_kind,
            "primary_replacement": (
                "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>"
            ),
            "recommended_sequence": [
                "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
                (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action command_surface --scope <path-or-owner>"
                ),
                "Create or reuse a checked ./repo-python tools/... owner command with compact JSON output.",
            ],
            "do_not_use": [
                "python -c JSON/data probes over selected artifacts as recurring status checks",
                "inline scripts that re-open large data files before selecting an owner route",
            ],
            "why": (
                "Inline data probes repeatedly pay parsing and output tax; select the artifact or "
                "command owner first, then use or add a compact owner packet."
            ),
        }
    if "replace_git_shell_chain_with_state_snapshot" in hint_ids:
        return {
            "status": "replacement_route_available",
            "action_kind": action_kind,
            "primary_replacement": GIT_STATE_SNAPSHOT_COMMAND,
            "recommended_sequence": [
                GIT_STATE_SNAPSHOT_COMMAND,
                GIT_DIFF_REVIEW_COMMAND,
            ],
            "do_not_use": [
                "git status --short | head",
                "git diff --stat | head",
                "git log -1 --oneline",
                "git rev-parse HEAD shell chains",
            ],
            "why": "Git state and diff review already have bounded owner packets; raw shell chains repeatedly hit output and wait tax.",
        }
    if action_kind in {"bash_grep", "bash_find"}:
        return {
            "status": "replacement_route_available",
            "action_kind": action_kind,
            "primary_replacement": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action artifact_discovery_inventory --scope <term-or-root>"
            ),
            "recommended_sequence": [
                (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action artifact_discovery_inventory --scope <term-or-root>"
                ),
                "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
            ],
            "do_not_use": [
                "broad rg over system tools codex state",
                "find over repo root before a stable owner surface exists",
                "grep/head/tail over generated trace bodies",
            ],
            "why": "Broad shell search should route through bounded path/content metadata before opening raw bodies.",
        }
    if action_kind in {"exec_session_io", "task_tool", "unknown_tool"}:
        return {
            "status": "replacement_route_available",
            "action_kind": action_kind,
            "primary_replacement": PROCESS_SUMMARY_OWNER_COMMAND,
            "recommended_sequence": [
                PROCESS_BOTTLENECK_OWNER_COMMAND,
                PROCESS_SUMMARY_OWNER_COMMAND,
                (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action exec_session_wait_tax"
                ),
            ],
            "do_not_use": [
                "long blind TaskOutput or exec_session waits",
                "tail/head polling of temporary tool-result files",
                "raw process ledger grep",
            ],
            "why": "Session-scoped owner summaries carry completion and output-shape state without replaying raw tool output.",
        }
    if action_kind == "test_or_build_command":
        return {
            "status": "replacement_route_available",
            "action_kind": action_kind,
            "primary_replacement": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action repo_pytest_validation -- <focused test args>"
            ),
            "recommended_sequence": [
                (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action repo_pytest_validation -- <focused test args>"
                ),
                "./repo-pytest <focused test args>",
            ],
            "do_not_use": [
                "broad test command piped through tail/head",
                "masked vitest/pytest output grep as the only proof",
            ],
            "why": "Validation should route through focused test selection and concise reporter paths before broad runs.",
        }
    return None


def _stale_process_bottleneck_shape_repair(
    row: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "status": "stale_cached_read_model",
        "action_kind": row.get("action_kind"),
        "primary_replacement": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "recommended_sequence": [
            PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
            "Use the fresh live ranking before selecting a source patch.",
        ],
        "do_not_use": [
            "cached top_bottleneck repair_hints as patch-selection authority",
            "cached selected_shape_repair without a live force route when stale",
        ],
        "why": (
            "The cached summary is useful as a cheap read model, but stale repair "
            "ordering must not outrank the force-live process bottleneck route."
        ),
    }


def _process_bottleneck_action_quote_command(action_kind: Any) -> str:
    selected = str(action_kind or "").strip()
    if not selected:
        return (
            "./repo-python tools/meta/control/action_quote.py "
            "--action process_bottleneck_triage --action-kind <action-kind>"
        )
    return (
        "./repo-python tools/meta/control/action_quote.py "
        f"--action process_bottleneck_triage --action-kind {shlex.quote(selected)}"
    )


def _process_bottleneck_selected_quote_command(
    row: Mapping[str, Any] | None,
    action_kind: Any,
) -> str:
    for hint in _as_list(_as_mapping(row).get("repair_hints")):
        hint_map = _as_mapping(hint)
        for key in ("quote_surface", "preferred_next", "owner_surface"):
            command = str(hint_map.get(key) or "").strip()
            if command.startswith("./repo-python tools/meta/control/action_quote.py"):
                return command
    return _process_bottleneck_action_quote_command(action_kind)


def _process_bottleneck_recommended_sequence(
    *,
    stale_summary: bool,
    selected_action_quote_command: str,
    selected_shape_repair: Mapping[str, Any] | None,
) -> list[str]:
    sequence = (
        [
            PROCESS_BOTTLENECK_CACHED_SUMMARY_CHECK_COMMAND,
            PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
            selected_action_quote_command,
        ]
        if stale_summary
        else [
            PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND,
            selected_action_quote_command,
        ]
    )
    primary_replacement = str(
        _as_mapping(selected_shape_repair).get("primary_replacement") or ""
    ).strip()
    if primary_replacement and primary_replacement not in sequence:
        sequence.append(primary_replacement)
    sequence.append("Use the selected scoped owner quote before opening raw trace bodies.")
    return sequence


def _process_bottleneck_selector_payload(
    rows: Sequence[Any],
    selection: Mapping[str, Any],
    *,
    limit: int = 12,
) -> dict[str, Any]:
    if selection.get("status") != "requested_action_kind_not_found_global_top_returned":
        return {}
    compact_rows: list[dict[str, Any]] = []
    for row in (_as_mapping(item) for item in rows[:limit]):
        top_row = _process_bottleneck_top_row(row)
        if not top_row or not top_row.get("action_kind"):
            continue
        compact_rows.append(
            {
                "action_kind": top_row.get("action_kind"),
                "count": top_row.get("count"),
                "p95_ms": top_row.get("p95_ms"),
                "max_ms": top_row.get("max_ms"),
                "slow_count": top_row.get("slow_count"),
                "threshold_ms": top_row.get("threshold_ms"),
                "first_hint": top_row.get("first_hint"),
                "quote_command": (
                    "./repo-python tools/meta/control/action_quote.py "
                    f"--action process_bottleneck_triage --action-kind {top_row.get('action_kind')}"
                ),
            }
        )
    return {
        "action_kind_selector": {
            "status": "available_for_requested_action_kind_not_found",
            "requested_action_kind": selection.get("requested_action_kind"),
            "row_count": len(rows),
            "emitted_row_count": len(compact_rows),
            "truncated": len(rows) > limit,
            "rows": compact_rows,
            "omission_receipt": {
                "omitted": [
                    "repair_hints",
                    "example_spans",
                    "stdout",
                    "stderr",
                    "private_output",
                ],
                "reason": "Missing action-kind recovery needs selectable metadata rows, not raw process bodies or full repair narratives.",
                "drilldown": PROCESS_BOTTLENECK_OWNER_COMMAND,
            },
        }
    }


def _process_output_top_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "action_kind": row.get("action_kind"),
        "total_output_bytes": row.get("total_output_bytes"),
        "max_output_bytes": row.get("max_output_bytes"),
        "p95_output_bytes": row.get("p95_output_bytes"),
        "span_count": row.get("count"),
    }


def _find_process_row(rows: Sequence[Any], action_kind: str) -> Mapping[str, Any]:
    for row in (_as_mapping(item) for item in rows):
        if row.get("action_kind") == action_kind:
            return row
    return {}


def _process_bottleneck_action_kind_from_scopes(
    scope_paths: Sequence[str],
    rows: Sequence[Any],
) -> str | None:
    scopes = _scope_paths(scope_paths)
    if not scopes:
        return None
    action_kinds = sorted(
        {
            str(row.get("action_kind") or "").strip()
            for row in (_as_mapping(item) for item in rows)
            if str(row.get("action_kind") or "").strip()
        },
        key=len,
        reverse=True,
    )
    if not action_kinds:
        return None
    for scope in scopes:
        normalized = re.sub(
            r"[^a-z0-9_]+",
            " ",
            str(scope).lower().replace("-", "_"),
        )
        tokens = set(normalized.split())
        padded = f" {normalized} "
        for action_kind in action_kinds:
            normalized_kind = action_kind.lower().replace("-", "_")
            spaced_kind = normalized_kind.replace("_", " ")
            if (
                normalized_kind in tokens
                or f" {normalized_kind} " in padded
                or f" {spaced_kind} " in padded
            ):
                return action_kind
    return None


def _process_bottleneck_do_not_touch(*, refresh_command: str | None = None) -> list[dict[str, Any]]:
    refresh = refresh_command or PROCESS_BOTTLENECK_REFRESH_COMMAND
    return [
        {
            "lane": "raw_process_trace_body_grep",
            "reason": "Process bottleneck triage is a metadata projection; raw command or output bodies are not the decision entry.",
            "replacement": PROCESS_BOTTLENECK_OWNER_COMMAND,
        },
        {
            "lane": "direct_process_projection_edit",
            "reason": "Process summaries are generated read models; refresh through the trace builder or force-live route.",
            "replacement": refresh,
        },
    ]


def _process_bottleneck_source_freshness(
    *,
    status: str,
    generated_at: Any = None,
    age_s: Any = None,
    refresh_command: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "generated_at": generated_at,
        "age_s": age_s,
        "stale_after_s": PROCESS_BOTTLENECK_STALE_AFTER_S,
        "owner_route": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "refresh_command": refresh_command or PROCESS_BOTTLENECK_REFRESH_COMMAND,
        "bounded_materialize_command": PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
        "force_live_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "mutation_status": "read_only_generated_projection",
    }


def _process_summary_target_from_scope(scope_paths: Sequence[str]) -> str | None:
    scopes = _scope_paths(scope_paths)
    if len(scopes) != 1:
        return None
    candidate = scopes[0].strip()
    if not candidate:
        return None
    if any(char in candidate for char in " \t\n|;&<>"):
        return None
    if "/" in candidate or candidate.endswith(".json"):
        return None
    if candidate in {"latest", "codex:latest", "claude:latest"}:
        return candidate
    if re.match(r"^(?:codex|claude):[A-Za-z0-9_.:-]+$", candidate):
        return candidate
    if re.match(r"^[A-Za-z0-9_.:-]{8,128}$", candidate):
        return candidate
    return None


def _process_summary_owner_command(target: str | None = None, *, force: bool = False) -> str:
    if not target:
        return PROCESS_SUMMARY_FORCE_LIVE_COMMAND if force else PROCESS_SUMMARY_OWNER_COMMAND
    command = f"./repo-python kernel.py --process-summary {shlex.quote(target)}"
    return f"{command} --force --limit 6" if force else command


def _process_summary_do_not_touch(owner_command: str = PROCESS_SUMMARY_OWNER_COMMAND) -> list[dict[str, Any]]:
    return [
        {
            "lane": "raw_tmp_task_output_polling",
            "reason": "Polling /tmp task-output or tool-result files by grep/head/tail burns IO and can expose raw command bodies.",
            "replacement": owner_command,
        },
        {
            "lane": "raw_process_trace_body_grep",
            "reason": "Process-summary packets expose selected-session counts, output byte pressure, and route compliance without raw stdout/stderr bodies.",
            "replacement": owner_command,
        },
        {
            "lane": "ambiguous_latest_alias_as_self_trace",
            "reason": "latest aliases select the newest completed trace for an agent family, not necessarily the current live wake.",
            "replacement": "./repo-python kernel.py --process-summary <explicit_session_id>",
        },
    ]


def _process_summary_source_freshness(
    *,
    status: str,
    generated_at: Any = None,
    age_s: Any = None,
    owner_command: str = PROCESS_SUMMARY_OWNER_COMMAND,
    force_command: str = PROCESS_SUMMARY_FORCE_LIVE_COMMAND,
) -> dict[str, Any]:
    return {
        "status": status,
        "generated_at": generated_at,
        "age_s": age_s,
        "stale_after_s": PROCESS_BOTTLENECK_STALE_AFTER_S,
        "owner_route": owner_command,
        "refresh_command": PROCESS_SUMMARY_REFRESH_COMMAND,
        "bounded_materialize_command": PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
        "force_live_command": force_command,
        "mutation_status": "read_only_generated_projection",
    }


def _select_process_bottleneck_row(
    rows: Sequence[Any],
    *,
    action_kind: str | None = None,
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    compact_rows = [_as_mapping(row) for row in rows]
    requested_action_kind = str(action_kind or "").strip()
    available_action_kinds = [
        str(row.get("action_kind") or "")
        for row in compact_rows
        if row.get("action_kind")
    ]
    global_top = compact_rows[0] if compact_rows else {}
    if not requested_action_kind:
        return global_top, {
            "mode": "global_top",
            "status": "unscoped_global_top",
            "requested_action_kind": None,
            "selected_action_kind": global_top.get("action_kind"),
            "available_action_kinds": available_action_kinds[:8],
        }

    matched = _find_process_row(compact_rows, requested_action_kind)
    if matched:
        return matched, {
            "mode": "action_kind",
            "status": "matched_action_kind",
            "requested_action_kind": requested_action_kind,
            "selected_action_kind": matched.get("action_kind"),
            "available_action_kinds": available_action_kinds[:8],
        }

    return global_top, {
        "mode": "action_kind",
        "status": "requested_action_kind_not_found_global_top_returned",
        "requested_action_kind": requested_action_kind,
        "selected_action_kind": global_top.get("action_kind"),
        "available_action_kinds": available_action_kinds[:8],
    }


def _process_bottleneck_speedboard_fallback(
    repo_root: Path,
    *,
    action_kind: str | None = None,
) -> dict[str, Any] | None:
    speedboard = _read_json(repo_root / SPEEDBOARD_REL)
    source = _as_mapping(speedboard.get("remaining_bottlenecks_source"))
    rows = _as_list(speedboard.get("remaining_bottlenecks"))
    top, selection = _select_process_bottleneck_row(rows, action_kind=action_kind)
    if not source or not top:
        return _process_bottleneck_wait_tax_fallback(
            speedboard,
            action_kind=action_kind,
        )
    source_status = str(source.get("status") or "unknown")
    source_generated_at = source.get("generated_at")
    source_age_s = _freshness_age_seconds(source_generated_at, source.get("age_s"))
    quote_status = (
        "speedboard_fallback_available"
        if source_status == "fresh"
        else "stale_speedboard_fallback_available"
    )
    return {
        "current_status": quote_status,
        "recommendation": "use_process_bottleneck_cached_fallback_then_force_live_only_if_needed",
        "freshness": "fresh" if source_status == "fresh" else "stale",
        "authority_level": "cached_read_model",
        "owner_check_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "drilldown_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "suggested_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "force_live_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "refresh_command": source.get("refresh_command")
        or "./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
        "do_not_touch": _process_bottleneck_do_not_touch(
            refresh_command=source.get("refresh_command")
            or "./repo-python tools/meta/observability/latency_speedboard.py show --live-process"
        ),
        "source_freshness": _process_bottleneck_source_freshness(
            status=source_status,
            generated_at=source_generated_at,
            age_s=source_age_s,
            refresh_command=source.get("refresh_command")
            or "./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
        ),
        "source": {
            "path": str(SPEEDBOARD_REL),
            "fallback_source": "latency_speedboard.remaining_bottlenecks",
            "canonical_process_summary_path": str(PROCESS_SUMMARY_REL),
            "canonical_process_summary_status": "missing",
            "generated_at": source_generated_at,
            "age_s": source_age_s,
            "source_status": source_status,
            "mutation_status": "read_only_fallback_no_projection_write",
        },
        "selection": selection,
        **_process_bottleneck_selector_payload(rows, selection),
        "top_bottleneck": _process_bottleneck_top_row(top),
        "global_top_bottleneck": _process_bottleneck_top_row(
            _as_mapping((rows or [{}])[0]),
            include_repair_hints=False,
            selected_action_kind=str(top.get("action_kind") or ""),
        ),
    }


def _wait_tax_to_process_bottleneck_row(row: Mapping[str, Any]) -> dict[str, Any]:
    p95_s = row.get("p95_seconds")
    max_s = row.get("max_seconds") or p95_s
    repair_hint = row.get("next_action")
    repair_hints = (
        [{"hint_id": repair_hint}]
        if isinstance(repair_hint, str) and repair_hint.strip()
        else []
    )
    return {
        "action_kind": row.get("resource_class")
        or row.get("owner_surface")
        or "wait_tax_command",
        "count": row.get("run_count_24h"),
        "p95_ms": round(float(p95_s) * 1000, 3)
        if isinstance(p95_s, (int, float))
        else None,
        "max_ms": round(float(max_s) * 1000, 3)
        if isinstance(max_s, (int, float))
        else None,
        "slow_count": row.get("run_count_24h"),
        "repair_hints": repair_hints,
        "owner_surface": row.get("owner_surface"),
        "command_key": row.get("command_key"),
        "next_action": row.get("next_action"),
        "next_command": row.get("next_command"),
        "source_status": row.get("status"),
    }


def _process_bottleneck_wait_tax_fallback(
    speedboard: Mapping[str, Any],
    *,
    action_kind: str | None = None,
) -> dict[str, Any] | None:
    source_rows = [
        row
        for row in (_as_mapping(item) for item in _as_list(speedboard.get("ranked_wait_taxes")))
        if row
    ]
    unresolved_rows = [
        row for row in source_rows if str(row.get("status") or "").lower() != "fixed"
    ]
    fixed_wait_tax_count = len(source_rows) - len(unresolved_rows)
    wait_rows = [
        _wait_tax_to_process_bottleneck_row(row)
        for row in unresolved_rows
    ]
    generated_at = speedboard.get("generated_at")
    age_s = _age_seconds(generated_at)
    freshness = (
        "stale"
        if isinstance(age_s, (int, float)) and age_s > PROCESS_BOTTLENECK_STALE_AFTER_S
        else "fresh"
    )
    if not wait_rows and source_rows:
        return {
            "current_status": (
                "speedboard_wait_tax_clear"
                if freshness == "fresh"
                else "stale_speedboard_wait_tax_clear"
            ),
            "recommendation": "use_process_bottleneck_status_without_wait_tax_fallback",
            "freshness": freshness,
            "authority_level": "cached_read_model",
            "owner_check_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
            "drilldown_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
            "suggested_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
            "force_live_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
            "refresh_command": "./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
            "do_not_touch": _process_bottleneck_do_not_touch(
                refresh_command="./repo-python tools/meta/observability/latency_speedboard.py show --live-process"
            ),
            "source_freshness": _process_bottleneck_source_freshness(
                status=freshness,
                generated_at=generated_at,
                age_s=age_s,
                refresh_command="./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
            ),
            "source": {
                "path": str(SPEEDBOARD_REL),
                "fallback_source": "latency_speedboard.ranked_wait_taxes",
                "canonical_process_summary_path": str(PROCESS_SUMMARY_REL),
                "canonical_process_summary_status": "missing",
                "generated_at": generated_at,
                "age_s": age_s,
                "source_status": freshness,
                "mutation_status": "read_only_fallback_no_projection_write",
                "ranked_wait_tax_row_count": len(source_rows),
                "fixed_wait_tax_rows_omitted": fixed_wait_tax_count,
                "unresolved_wait_tax_count": 0,
                "advisory_status": "all_ranked_wait_tax_rows_fixed",
            },
            "selection": {
                "mode": "global_top" if not action_kind else "action_kind",
                "status": "no_unresolved_wait_tax_rows",
                "requested_action_kind": str(action_kind or "").strip() or None,
                "selected_action_kind": None,
                "available_action_kinds": [],
            },
            "top_bottleneck": None,
            "global_top_bottleneck": None,
        }
    top, selection = _select_process_bottleneck_row(wait_rows, action_kind=action_kind)
    if not top:
        return None
    quote_status = (
        "speedboard_wait_tax_fallback_available"
        if freshness == "fresh"
        else "stale_speedboard_wait_tax_fallback_available"
    )
    return {
        "current_status": quote_status,
        "recommendation": "use_speedboard_wait_tax_fallback_then_force_live_only_if_needed",
        "freshness": freshness,
        "authority_level": "cached_read_model",
        "owner_check_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "drilldown_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "suggested_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "force_live_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "refresh_command": "./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
        "do_not_touch": _process_bottleneck_do_not_touch(
            refresh_command="./repo-python tools/meta/observability/latency_speedboard.py show --live-process"
        ),
        "source_freshness": _process_bottleneck_source_freshness(
            status=freshness,
            generated_at=generated_at,
            age_s=age_s,
            refresh_command="./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
        ),
        "source": {
            "path": str(SPEEDBOARD_REL),
            "fallback_source": "latency_speedboard.ranked_wait_taxes",
            "canonical_process_summary_path": str(PROCESS_SUMMARY_REL),
            "canonical_process_summary_status": "missing",
            "generated_at": generated_at,
            "age_s": age_s,
            "source_status": freshness,
            "mutation_status": "read_only_fallback_no_projection_write",
            "ranked_wait_tax_row_count": len(source_rows),
            "fixed_wait_tax_rows_omitted": fixed_wait_tax_count,
            "unresolved_wait_tax_count": len(unresolved_rows),
        },
        "selection": selection,
        **_process_bottleneck_selector_payload(wait_rows, selection),
        "top_bottleneck": _process_bottleneck_top_row(top),
        "global_top_bottleneck": _process_bottleneck_top_row(
            _as_mapping((wait_rows or [{}])[0]),
            include_repair_hints=False,
            selected_action_kind=str(top.get("action_kind") or ""),
        ),
    }


def _quote_process_bottleneck_triage(
    repo_root: Path,
    *,
    action_kind: str | None = None,
    scope_paths: Sequence[str] = (),
) -> dict[str, Any]:
    summary = _read_json(repo_root / PROCESS_SUMMARY_REL)
    bottleneck_rows = _as_list(summary.get("top_bottlenecks"))
    scoped_action_kind = action_kind or _process_bottleneck_action_kind_from_scopes(
        scope_paths,
        bottleneck_rows,
    )
    top, selection = _select_process_bottleneck_row(
        bottleneck_rows,
        action_kind=scoped_action_kind,
    )
    top_output = _as_mapping((_as_list(summary.get("top_output_producers")) or [{}])[0])
    age_s = _age_seconds(summary.get("generated_at"))
    status = "cached_summary_available" if summary else "missing_cached_summary"
    if summary and isinstance(age_s, (int, float)) and age_s > PROCESS_BOTTLENECK_STALE_AFTER_S:
        status = "stale_cached_summary_available"
    if not summary:
        fallback = _process_bottleneck_speedboard_fallback(
            repo_root,
            action_kind=scoped_action_kind,
        )
        if fallback is not None:
            return fallback
    freshness = "stale" if status == "stale_cached_summary_available" else ("fresh" if status == "cached_summary_available" else "unknown")
    source_status = "missing" if not summary else freshness
    stale_summary = freshness == "stale"
    top_bottleneck = _process_bottleneck_top_row(top)
    if top_bottleneck and stale_summary:
        top_bottleneck["advisory_only"] = True
        top_bottleneck["authority_warning"] = (
            "stale_cached_ranking_run_force_live_before_patch_selection"
        )
    selected_shape_repair = (
        _stale_process_bottleneck_shape_repair(top)
        if stale_summary
        else _process_bottleneck_shape_repair(top)
    )
    suggested_command = (
        PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND
        if stale_summary
        else PROCESS_BOTTLENECK_OWNER_COMMAND
    )
    safe_first_command = (
        PROCESS_BOTTLENECK_CACHED_SUMMARY_CHECK_COMMAND
        if stale_summary
        else PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND
    )
    selected_action_kind = selection.get("selected_action_kind") or (
        top.get("action_kind") if top else None
    )
    selected_action_quote_command = _process_bottleneck_selected_quote_command(
        top,
        selected_action_kind,
    )
    return {
        "current_status": status,
        "recommendation": (
            "force_live_before_patch_selection"
            if stale_summary
            else "use_cached_summary_then_force_live_only_if_needed"
            if summary
            else "build_process_summary"
        ),
        "freshness": freshness,
        "authority_level": "cached_read_model",
        "owner_check_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "drilldown_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "suggested_command": suggested_command,
        "cache_check_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND,
        "safe_first_command": safe_first_command,
        "safe_first_check_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_CHECK_COMMAND,
        "force_live_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "selected_action_quote_command": selected_action_quote_command,
        "recommended_sequence": _process_bottleneck_recommended_sequence(
            stale_summary=stale_summary,
            selected_action_quote_command=selected_action_quote_command,
            selected_shape_repair=selected_shape_repair,
        ),
        "bounded_materialize_command": PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
        "refresh_command": PROCESS_BOTTLENECK_REFRESH_COMMAND,
        "do_not_touch": _process_bottleneck_do_not_touch(),
        "source_freshness": _process_bottleneck_source_freshness(
            status=source_status,
            generated_at=summary.get("generated_at"),
            age_s=age_s,
        ),
        "source": {
            "path": str(PROCESS_SUMMARY_REL),
            "generated_at": summary.get("generated_at"),
            "age_s": age_s,
            "source_status": source_status,
            "mutation_status": "read_only_generated_projection",
        },
        "selection": selection,
        "selection_policy": {
            "status": (
                "stale_cached_ranking_advisory"
                if stale_summary
                else "cached_ranking_selectable"
            ),
            "patch_selection_authority": (
                "force_live_command" if stale_summary else "cached_read_model"
            ),
            "safe_cached_probe": PROCESS_BOTTLENECK_CACHED_SUMMARY_CHECK_COMMAND,
            "safe_cached_probe_role": (
                "read_model_availability_only"
                if stale_summary
                else "cheap_cached_summary_probe"
            ),
            "force_live_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        },
        **_process_bottleneck_selector_payload(bottleneck_rows, selection),
        "top_bottleneck": top_bottleneck,
        "selected_shape_repair": selected_shape_repair,
        "global_top_bottleneck": _process_bottleneck_top_row(
            _as_mapping((bottleneck_rows or [{}])[0]),
            include_repair_hints=False,
            selected_action_kind=str(top.get("action_kind") or "") if top else None,
        ),
        "top_output_producer": {
            **(_process_output_top_row(top_output) or {}),
        }
        if top_output
        else None,
    }


def _quote_process_summary_status(repo_root: Path, scope_paths: Sequence[str] = ()) -> dict[str, Any]:
    summary = _read_json(repo_root / PROCESS_SUMMARY_REL)
    top = _as_mapping((_as_list(summary.get("top_bottlenecks")) or [{}])[0])
    top_output = _as_mapping((_as_list(summary.get("top_output_producers")) or [{}])[0])
    requested_target = _process_summary_target_from_scope(scope_paths)
    owner_command = _process_summary_owner_command(requested_target)
    force_command = _process_summary_owner_command(requested_target, force=True)
    age_s = _age_seconds(summary.get("generated_at"))
    freshness = "unknown"
    current_status = "missing_process_summary_projection"
    recommendation = "refresh_process_summary_read_model_before_polling_outputs"
    suggested_command = PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND
    recommended_sequence = [
        PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND,
        LATENCY_SEED_DIGEST_NO_GIT_COMMAND,
        HOST_PRESSURE_FAST_COMMAND,
        PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
        PROCESS_SUMMARY_REFRESH_COMMAND,
        "./repo-python kernel.py --process-summary <explicit_session_id>",
        force_command,
    ]
    if summary:
        freshness = (
            "stale"
            if isinstance(age_s, (int, float)) and age_s > PROCESS_BOTTLENECK_STALE_AFTER_S
            else "fresh"
        )
        current_status = (
            "stale_cached_process_summary_available"
            if freshness == "stale"
            else "cached_process_summary_available"
        )
        recommendation = "use_process_summary_route_for_selected_session_before_polling_outputs"
        suggested_command = owner_command
        recommended_sequence = [
            owner_command,
            "./repo-python kernel.py --process-summary <explicit_session_id>",
            PROCESS_BOTTLENECK_OWNER_COMMAND,
            PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
            PROCESS_SUMMARY_REFRESH_COMMAND,
            force_command,
        ]
    return {
        "current_status": current_status,
        "recommendation": recommendation,
        "freshness": freshness,
        "authority_level": "session_scoped_read_model",
        "owner_check_command": owner_command,
        "drilldown_command": owner_command,
        "suggested_command": suggested_command,
        "cache_check_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND,
        "safe_first_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND,
        "safe_first_check_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_CHECK_COMMAND,
        "force_live_command": force_command,
        "bounded_materialize_command": PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
        "refresh_command": PROCESS_SUMMARY_REFRESH_COMMAND,
        "replacement_command": owner_command,
        "requested_process_summary_target": requested_target,
        "do_not_touch": _process_summary_do_not_touch(owner_command),
        "recommended_sequence": recommended_sequence,
        "identity_guidance": {
            "prefer_explicit_session_id": True,
            "latest_alias_boundary": "agent-family latest aliases are evidence selectors, not self-identity claims",
            "safe_trace_drilldown": "./repo-python kernel.py --process-trace <explicit_session_id>",
        },
        "source_freshness": _process_summary_source_freshness(
            status="missing" if not summary else freshness,
            generated_at=summary.get("generated_at"),
            age_s=age_s,
            owner_command=owner_command,
            force_command=force_command,
        ),
        "source": {
            "path": str(PROCESS_SUMMARY_REL),
            "generated_at": summary.get("generated_at"),
            "age_s": age_s,
            "source_status": "missing" if not summary else freshness,
            "mutation_status": "read_only_generated_projection",
            "privacy": "metadata_only_no_stdout_stderr_bodies",
        },
        "top_bottleneck": _process_bottleneck_top_row(top),
        "top_output_producer": _process_output_top_row(top_output),
        "polling_replacements": [
            {
                "slow_shape": "grep/head/tail over task output or tmp artifacts",
                "prefer": owner_command,
            },
            {
                "slow_shape": "raw process ledger or trace grep",
                "prefer": PROCESS_BOTTLENECK_OWNER_COMMAND,
            },
            {
                "slow_shape": "repeated completion polling for a selected session",
                "prefer": "./repo-python kernel.py --process-summary <explicit_session_id>",
            },
        ],
        "privacy": {
            "stores_stdout_stderr_bodies": False,
            "stores_file_contents": False,
            "emits": "session/process metadata, counts, timings, byte counts, and route guidance only",
        },
    }


DOCUMENT_READ_SCOPE_SUFFIXES = {".adoc", ".md", ".rst", ".txt"}
STRUCTURED_READ_SCOPE_SUFFIXES = {".json"}
DOCUMENT_READ_KNOWN_SCOPE_OWNER_ROUTES: dict[str, dict[str, Any]] = {
    "tools/meta/dissemination/build_microcosm_public_site.py": {
        "route_kind": "paper_module_card",
        "owner_slug": "tools_meta_dissemination_index",
        "route_command": (
            "./repo-python kernel.py --option-surface paper_modules --band card "
            "--ids tools_meta_dissemination_index"
        ),
        "source_evidence_command": (
            "./repo-python kernel.py --paper-module tools_meta_dissemination_index"
        ),
        "supporting_card_command": (
            "./repo-python kernel.py --option-surface paper_modules --band card "
            "--ids microcosm_public_export_type_plane,graph_scene_core"
        ),
        "focused_validation_command": (
            "./repo-python tools/meta/dissemination/build_microcosm_public_site.py "
            "--check --validate"
        ),
        "why": (
            "Session diagnostics shows repeated rereads of the public-site builder; "
            "use the dissemination tooling card before opening source unless exact "
            "renderer/helper behavior or a focused validation failure requires it."
        ),
    }
}


def _document_read_candidate_rel_text(
    repo_root: Path,
    raw_candidate: str,
) -> tuple[str, str] | None:
    candidate = raw_candidate.strip().strip("'\"`;,()")
    if not candidate:
        return None
    path_part, _, _line_part = candidate.partition(":")
    path = Path(path_part).expanduser()
    suffix = path.suffix.lower()
    if path.is_absolute():
        try:
            rel_path = path.resolve().relative_to(repo_root.resolve())
        except ValueError:
            return None
    else:
        rel_path = path
    rel_text = rel_path.as_posix()
    if not rel_text or rel_text.startswith(".."):
        return None
    return rel_text, suffix


def _document_read_scope_route(
    repo_root: Path,
    scope_paths: Sequence[str],
) -> dict[str, Any] | None:
    for scope in _scope_paths(scope_paths):
        candidate_texts = [scope, *scope.split()]
        rel_candidates: list[tuple[str, str]] = []
        for raw_candidate in candidate_texts:
            rel_candidate = _document_read_candidate_rel_text(repo_root, raw_candidate)
            if not rel_candidate:
                continue
            rel_candidates.append(rel_candidate)
        for rel_text, _suffix in rel_candidates:
            known_owner_route = DOCUMENT_READ_KNOWN_SCOPE_OWNER_ROUTES.get(rel_text)
            if known_owner_route:
                return {
                    "status": "scoped_known_owner_route",
                    "path": rel_text,
                    **known_owner_route,
                    "privacy": {
                        "stores_file_contents": False,
                        "scope_matching": "path_metadata_only_known_owner_route",
                    },
                }
        for rel_text, suffix in rel_candidates:
            if suffix not in DOCUMENT_READ_SCOPE_SUFFIXES | STRUCTURED_READ_SCOPE_SUFFIXES:
                continue
            quoted = shlex.quote(rel_text)
            if suffix in STRUCTURED_READ_SCOPE_SUFFIXES:
                structure_command = f"jq 'keys_unsorted' {quoted}"
                return {
                    "status": "scoped_json_structure_path",
                    "path": rel_text,
                    "route_command": structure_command,
                    "structure_command": structure_command,
                    "bounded_value_command": f"jq '<filter>' {quoted}",
                    "privacy": {
                        "stores_file_contents": False,
                        "scope_matching": "path_metadata_only_no_json_body_read",
                    },
                }
            return {
                "status": "scoped_document_path",
                "path": rel_text,
                "route_command": f"./repo-python kernel.py --docs-route {quoted}",
                "bounded_section_command": f"sed -n '<start>,<end>p' {quoted}",
                "privacy": {
                    "stores_file_contents": False,
                    "scope_matching": "path_metadata_only_no_document_body_read",
                },
            }
    return None


def _scope_mentions_document_read_known_owner_route(
    repo_root: Path,
    scope_paths: Sequence[str],
) -> bool:
    route = _document_read_scope_route(repo_root, scope_paths)
    return bool(route and route.get("status") == "scoped_known_owner_route")


def _quote_document_read_economy(
    repo_root: Path,
    scope_paths: Sequence[str] = (),
) -> dict[str, Any]:
    summary = _read_json(repo_root / PROCESS_SUMMARY_REL)
    age_s = _age_seconds(summary.get("generated_at"))
    freshness = "unknown"
    if summary:
        freshness = (
            "stale"
            if isinstance(age_s, (int, float)) and age_s > PROCESS_BOTTLENECK_STALE_AFTER_S
            else "fresh"
        )
    read_row = _find_process_row(_as_list(summary.get("top_bottlenecks")), "read_file")
    output_row = _find_process_row(_as_list(summary.get("top_output_producers")), "read_file")
    pressure_detected = bool(read_row or output_row)
    scoped_route = _document_read_scope_route(repo_root, scope_paths)
    scoped_status = str(scoped_route.get("status") or "") if scoped_route else ""
    scoped_json_route = scoped_status == "scoped_json_structure_path"
    scoped_known_owner_route = scoped_status == "scoped_known_owner_route"
    suggested_command = (
        str(scoped_route.get("route_command"))
        if scoped_route
        else './repo-python kernel.py --entry "<task>" --context-budget 12000'
    )
    recommendation = (
        (
            "use_known_owner_card_for_scoped_source_before_full_read"
            if scoped_known_owner_route
            else (
                "use_json_structure_probe_for_scoped_json_before_full_read"
                if scoped_json_route
                else "use_docs_route_for_scoped_document_before_full_read"
            )
        )
        if scoped_route
        else (
            "route_through_entry_or_context_pack_before_full_read"
            if pressure_detected
            else "use_entry_or_context_pack_for_first_contact"
        )
    )
    first_sequence = (
        {
            "action": (
                "open_scoped_known_owner_card"
                if scoped_known_owner_route
                else (
                    "open_scoped_json_structure"
                    if scoped_json_route
                    else "open_scoped_document_route"
                )
            ),
            "command": suggested_command,
        }
        if scoped_route
        else {
            "action": "route_task_first",
            "command": './repo-python kernel.py --entry "<task>" --context-budget 12000',
        }
    )
    return {
        "current_status": (
            (
                "scoped_known_owner_route_available"
                if scoped_known_owner_route
                else (
                    "scoped_json_structure_route_available"
                    if scoped_json_route
                    else "scoped_document_route_available"
                )
            )
            if scoped_route
            else (
                "read_file_pressure_detected"
                if pressure_detected and freshness != "stale"
                else (
                    "stale_read_file_pressure_detected"
                    if pressure_detected
                    else "no_cached_read_file_pressure"
                )
            )
        ),
        "recommendation": recommendation,
        "freshness": freshness,
        "authority_level": "cached_read_model",
        "owner_check_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "suggested_command": suggested_command,
        "context_pack_command": './repo-python kernel.py --context-pack "<task>" --context-budget 12000',
        "section_read_fallback": "Use sed -n '<start>,<end>p' <path> or rg with an exact identifier after the route names a target.",
        **({"scope_resolution": scoped_route} if scoped_route else {}),
        "source_freshness": _process_bottleneck_source_freshness(
            status="missing" if not summary else freshness,
            generated_at=summary.get("generated_at"),
            age_s=age_s,
            refresh_command=PROCESS_BOTTLENECK_REFRESH_COMMAND,
        ),
        "source": {
            "path": str(PROCESS_SUMMARY_REL),
            "source_status": "missing" if not summary else freshness,
            "mutation_status": "read_only_generated_projection",
            "privacy": "metadata_only_no_file_bodies",
        },
        "read_pressure": _process_bottleneck_top_row(read_row),
        "output_pressure": _process_output_top_row(output_row),
        "recommended_sequence": [
            first_sequence,
            {
                "action": "open_subsystem_context_pack_if_existing_surface",
                "command": './repo-python kernel.py --context-pack "<task>" --context-budget 12000',
            },
            {
                "action": "read_named_section_or_exact_identifier",
                "command": "sed -n '<start>,<end>p' <path>",
            },
            {
                "action": "refresh_process_read_model_if_read_pressure_decision_is_stale",
                "command": PROCESS_BOTTLENECK_REFRESH_COMMAND,
                "condition": "cached read_file pressure is stale and current rankings matter",
            },
        ],
        "do_not_touch": [
            {
                "lane": "whole_document_first_contact",
                "reason": "Large whole-file reads dominate read_file output and should follow a route or selected section.",
                "replacement": suggested_command,
            },
            {
                "lane": "generated_projection_full_read",
                "reason": "Generated projections usually have owner status or card routes; read the route/card before opening the full projection.",
                "replacement": "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>",
            },
        ],
        "output_economy": {
            "observed_action_kind": "read_file",
            "owner_route_first": True,
            "full_file_read_after_route": True,
            "emits_file_contents": False,
        },
    }


def _kernel_output_scope_route(scope_paths: Sequence[str]) -> dict[str, Any] | None:
    scopes = _scope_paths(scope_paths)
    if not scopes:
        return None
    surface = " ".join(scopes)
    surface_tokens = [
        token.strip().strip("'\"`;,()")
        for scope in scopes
        for token in scope.split()
        if token.strip().strip("'\"`;,()")
    ]
    normalized_tokens = {token.replace("_", "-").lower() for token in surface_tokens}
    if (
        "process-bottlenecks" in normalized_tokens
        or "--process-bottlenecks" in normalized_tokens
    ) and "--process-action-kind" in normalized_tokens:
        action_kind = "<action-kind>"
        for index, token in enumerate(surface_tokens[:-1]):
            if token.replace("_", "-").lower() == "--process-action-kind":
                action_kind = surface_tokens[index + 1]
                break
        action_arg = action_kind if action_kind == "<action-kind>" else shlex.quote(action_kind)
        route_command = (
            f"./repo-python kernel.py --process-bottlenecks --process-action-kind {action_arg}"
        )
        force_command = (
            f"./repo-python kernel.py --process-bottlenecks --force --process-action-kind {action_arg}"
        )
        return {
            "status": "scoped_filtered_process_bottlenecks_route",
            "surface": surface,
            "action_kind": action_kind,
            "route_command": route_command,
            "safe_first_command": route_command,
            "force_live_command": force_command,
            "scope_count": len(scopes),
            "privacy": {
                "scope_matching": "metadata_only",
                "stores_stdout_stderr_bodies": False,
            },
        }
    if "process-summary" in normalized_tokens or "--process-summary" in normalized_tokens:
        target = "<session_id|claude:latest|codex:latest>"
        for index, token in enumerate(surface_tokens[:-1]):
            if token.replace("_", "-").lower() in {
                "process-summary",
                "--process-summary",
            }:
                target = surface_tokens[index + 1]
                break
        target_arg = target if target.startswith("<") else shlex.quote(target)
        route_command = f"./repo-python kernel.py --process-summary {target_arg}"
        force_command = f"{route_command} --force --limit 6"
        return {
            "status": "scoped_process_summary_status_route",
            "surface": surface,
            "target": target,
            "route_command": route_command,
            "safe_first_command": route_command,
            "force_live_command": force_command,
            "scope_count": len(scopes),
            "privacy": {
                "scope_matching": "metadata_only",
                "stores_stdout_stderr_bodies": False,
            },
        }
    if "option-surface" in normalized_tokens:
        kind_candidates = [
            token
            for token in surface_tokens
            if token.replace("_", "-").lower() != "option-surface"
        ]
        kind_id = kind_candidates[0] if kind_candidates else "<kind_id>"
        kind_arg = kind_id if kind_id == "<kind_id>" else shlex.quote(kind_id)
        route_command = f"./repo-python kernel.py --option-surface {kind_arg} --band cluster_flag"
        return {
            "status": "scoped_option_surface_cluster_route",
            "surface": surface,
            "kind_id": kind_id,
            "route_command": route_command,
            "card_drilldown_command": (
                f"./repo-python kernel.py --option-surface {kind_arg} --band card --ids <id>"
            ),
            "scope_count": len(scopes),
            "privacy": {
                "scope_matching": "metadata_only",
                "stores_stdout_stderr_bodies": False,
            },
        }
    route_command = (
        "./repo-python tools/meta/control/action_quote.py "
        f"--action command_surface_inventory --scope {shlex.quote(surface)}"
    )
    return {
        "status": "scoped_kernel_surface",
        "surface": surface,
        "route_command": route_command,
        "scope_count": len(scopes),
        "privacy": {
            "scope_matching": "metadata_only",
            "stores_stdout_stderr_bodies": False,
        },
    }


def _quote_kernel_output_economy(repo_root: Path, scope_paths: Sequence[str] = ()) -> dict[str, Any]:
    summary = _read_json(repo_root / PROCESS_SUMMARY_REL)
    age_s = _age_seconds(summary.get("generated_at"))
    freshness = "unknown"
    if summary:
        freshness = (
            "stale"
            if isinstance(age_s, (int, float)) and age_s > PROCESS_BOTTLENECK_STALE_AFTER_S
            else "fresh"
        )
    kernel_row = _find_process_row(_as_list(summary.get("top_bottlenecks")), "kernel_command")
    output_row = _find_process_row(_as_list(summary.get("top_output_producers")), "kernel_command")
    pressure_detected = bool(kernel_row or output_row)
    scoped_route = _kernel_output_scope_route(scope_paths)
    scoped_status = str(scoped_route.get("status") or "") if scoped_route else ""
    scoped_option_surface = scoped_status == "scoped_option_surface_cluster_route"
    scoped_filtered_process = (
        scoped_status == "scoped_filtered_process_bottlenecks_route"
    )
    scoped_process_summary = scoped_status == "scoped_process_summary_status_route"
    suggested_command = (
        str(scoped_route["route_command"])
        if scoped_route
        else './repo-python kernel.py --entry "<task>" --context-budget 12000'
    )
    recommended_sequence = [
        {
            "action": "use_task_entry_when_task_is_unrouted",
            "command": './repo-python kernel.py --entry "<task>" --context-budget 12000',
        },
        {
            "action": "use_context_pack_for_existing_subsystem",
            "command": './repo-python kernel.py --context-pack "<task>" --context-budget 12000',
        },
        {
            "action": "use_pressure_safe_latency_seed_for_latency_work",
            "command": LATENCY_SEED_DIGEST_NO_GIT_COMMAND,
        },
        {
            "action": "inspect_command_surface_for_compact_mode",
            "command": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action command_surface_inventory --scope <kernel-surface>"
            ),
        },
        {
            "action": "force_full_kernel_output_only_after_compact_route",
            "command": "./repo-python kernel.py --<surface> --full",
            "condition": "compact route names the specific full evidence needed",
        },
    ]
    if scoped_route:
        recommended_sequence.insert(
            0,
            {
                "action": (
                    "open_scoped_option_surface_cluster"
                    if scoped_option_surface
                    else (
                        "use_filtered_process_bottleneck_cached_status_first"
                        if scoped_filtered_process
                        else (
                            "use_scoped_process_summary_status_first"
                            if scoped_process_summary
                            else "inspect_scoped_kernel_surface_first"
                        )
                    )
                ),
                "command": suggested_command,
            },
        )
        if scoped_option_surface and scoped_route.get("card_drilldown_command"):
            recommended_sequence.insert(
                1,
                {
                    "action": "open_selected_option_surface_card",
                    "command": str(scoped_route["card_drilldown_command"]),
                    "condition": "cluster route names a specific id needed for drilldown",
                },
            )
    recommendation = (
        (
            "use_option_surface_cluster_flag_before_full_inventory"
            if scoped_option_surface
            else (
                "use_cached_filtered_process_bottleneck_status_before_force_live"
                if scoped_filtered_process
                else (
                    "use_process_summary_status_before_tmp_output_polling"
                    if scoped_process_summary
                    else "use_command_surface_for_scoped_kernel_output_before_limiter"
                )
            )
        )
        if scoped_route
        else (
            "use_compact_kernel_route_or_selected_lens_before_output_limiter"
            if pressure_detected
            else "use_bounded_kernel_entry_or_context_pack"
        )
    )
    return {
        "current_status": (
            (
                "scoped_option_surface_cluster_route_available"
                if scoped_option_surface
                else (
                    "scoped_filtered_process_bottleneck_route_available"
                    if scoped_filtered_process
                    else (
                        "scoped_process_summary_status_route_available"
                        if scoped_process_summary
                        else "scoped_kernel_surface_quote_available"
                    )
                )
            )
            if scoped_route
            else (
                "kernel_output_pressure_detected"
                if pressure_detected and freshness != "stale"
                else (
                    "stale_kernel_output_pressure_detected"
                    if pressure_detected
                    else "no_cached_kernel_output_pressure"
                )
            )
        ),
        "recommendation": recommendation,
        "freshness": freshness,
        "authority_level": "cached_read_model",
        "owner_check_command": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "suggested_command": suggested_command,
        "safe_first_command": (
            str(scoped_route["safe_first_command"])
            if (scoped_filtered_process or scoped_process_summary) and scoped_route
            else suggested_command
        ),
        "force_live_command": (
            str(scoped_route["force_live_command"])
            if (scoped_filtered_process or scoped_process_summary) and scoped_route
            else PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND
        ),
        "context_pack_command": './repo-python kernel.py --context-pack "<task>" --context-budget 12000',
        "latency_seed_command": LATENCY_SEED_DIGEST_NO_GIT_COMMAND,
        "command_surface_inventory": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action command_surface_inventory --scope <kernel-surface>"
        ),
        "source_freshness": _process_bottleneck_source_freshness(
            status="missing" if not summary else freshness,
            generated_at=summary.get("generated_at"),
            age_s=age_s,
            refresh_command=PROCESS_BOTTLENECK_REFRESH_COMMAND,
        ),
        "source": {
            "path": str(PROCESS_SUMMARY_REL),
            "source_status": "missing" if not summary else freshness,
            "mutation_status": "read_only_generated_projection",
            "privacy": "metadata_only_no_kernel_payload_bodies",
        },
        "scope_resolution": scoped_route or {"status": "unscoped_kernel_surface"},
        "kernel_pressure": _process_bottleneck_top_row(kernel_row),
        "output_pressure": _process_output_top_row(output_row),
        "recommended_sequence": recommended_sequence,
        "do_not_touch": [
            {
                "lane": "tail_head_masked_kernel_output",
                "reason": "Output limiters hide route shape problems and still pay full command cost.",
                "replacement": suggested_command,
            },
            {
                "lane": "force_full_kernel_first_contact",
                "reason": "Full kernel packets are drilldowns; first-contact should use compact routes or selected lenses.",
                "replacement": (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action command_surface_inventory --scope <kernel-surface>"
                ),
            },
        ],
        "output_economy": {
            "observed_action_kind": "kernel_command",
            "compact_route_first": True,
            "full_kernel_output_after_route": True,
            "emits_kernel_payload_bodies": False,
        },
    }


def _quote_exec_session_wait_tax(
    repo_root: Path,
    scope_paths: Sequence[str] = (),
) -> dict[str, Any]:
    summary = _read_json(repo_root / PROCESS_SUMMARY_REL)
    speedboard = _read_json(repo_root / SPEEDBOARD_REL)
    requested_target = _process_summary_target_from_scope(scope_paths)
    scoped_summary_command = _process_summary_owner_command(requested_target)
    scoped_force_command = _process_summary_owner_command(requested_target, force=True)
    has_process_scope = bool(requested_target)
    age_s = _age_seconds(summary.get("generated_at"))
    freshness = "unknown"
    source_status = "missing"
    source_path = str(PROCESS_SUMMARY_REL)
    refresh_command = PROCESS_BOTTLENECK_REFRESH_COMMAND
    fallback_generated_at = None
    exec_row = _find_process_row(_as_list(summary.get("top_bottlenecks")), "exec_session_io")
    output_row = _find_process_row(_as_list(summary.get("top_output_producers")), "exec_session_io")
    if summary:
        freshness = "stale" if isinstance(age_s, (int, float)) and age_s > PROCESS_BOTTLENECK_STALE_AFTER_S else "fresh"
        source_status = freshness
    else:
        source = _as_mapping(speedboard.get("remaining_bottlenecks_source"))
        exec_row = _find_process_row(_as_list(speedboard.get("remaining_bottlenecks")), "exec_session_io")
        source_status = str(source.get("status") or "missing")
        freshness = "fresh" if source_status == "fresh" else ("stale" if source_status != "missing" else "unknown")
        fallback_generated_at = source.get("generated_at")
        age_s = _freshness_age_seconds(fallback_generated_at, source.get("age_s"))
        source_path = str(SPEEDBOARD_REL)
        refresh_command = source.get("refresh_command") or "./repo-python tools/meta/observability/latency_speedboard.py show --live-process"

    wait_pressure_detected = bool(exec_row)
    output_pressure_detected = bool(output_row)
    pressure_detected = wait_pressure_detected or output_pressure_detected
    if wait_pressure_detected:
        current_status = "exec_session_wait_pressure_detected"
    elif output_pressure_detected:
        current_status = "exec_session_output_pressure_detected"
    else:
        current_status = "no_cached_exec_session_pressure"
    if freshness == "stale" and wait_pressure_detected:
        current_status = "stale_exec_session_wait_pressure_detected"
    elif freshness == "stale" and output_pressure_detected:
        current_status = "stale_exec_session_output_pressure_detected"
    owner_check_command = scoped_summary_command if has_process_scope else PROCESS_BOTTLENECK_OWNER_COMMAND
    drilldown_command = scoped_force_command if has_process_scope else PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND
    suggested_command = owner_check_command
    recommendation = (
        "use_scoped_process_summary_before_another_exec_session_poll"
        if has_process_scope
        else (
            "use_process_bottleneck_route_then_owner_status_packet"
            if pressure_detected
            else "refresh_process_bottlenecks_if_wait_tax_suspected"
        )
    )
    return {
        "current_status": current_status,
        "recommendation": recommendation,
        "freshness": freshness,
        "authority_level": "cached_read_model",
        "owner_check_command": owner_check_command,
        "drilldown_command": drilldown_command,
        "suggested_command": suggested_command,
        "cache_check_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND,
        "safe_first_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_COMMAND,
        "safe_first_check_command": PROCESS_BOTTLENECK_CACHED_SUMMARY_CHECK_COMMAND,
        "force_live_command": drilldown_command,
        "refresh_command": refresh_command,
        "replacement_command": (
            scoped_summary_command
            if has_process_scope
            else (
            "Prefer the long-running command's compact owner status/check packet; for generic exec sessions, "
            "poll with a short yield_time_ms and bounded max_output_tokens before another long write_stdin wait."
            )
        ),
        "requested_process_summary_target": requested_target,
        "do_not_touch": _process_bottleneck_do_not_touch(refresh_command=refresh_command),
        "source_freshness": _process_bottleneck_source_freshness(
            status=source_status,
            generated_at=summary.get("generated_at") or fallback_generated_at,
            age_s=age_s,
            refresh_command=refresh_command,
        ),
        "source": {
            "path": source_path,
            "canonical_process_summary_path": str(PROCESS_SUMMARY_REL),
            "source_status": source_status,
            "mutation_status": "read_only_generated_projection",
            "privacy": "metadata_only_no_stdout_stderr_bodies",
        },
        "wait_tax": _process_bottleneck_top_row(exec_row),
        "output_pressure": _process_output_top_row(output_row),
        "agent_guidance": [
            {
                "when": "an explicit session or latest alias is supplied",
                "prefer": scoped_summary_command,
            },
            {
                "when": "write_stdin has configured_wait or exec_session_poll tags",
                "prefer": "inspect the preceding exec_command shape and use its owner status/check packet",
            },
            {
                "when": "the session is only being polled for completion",
                "prefer": "short bounded polls instead of 60-180s configured waits",
            },
            {
                "when": "the underlying command lacks a compact status route",
                "prefer": "add the owner status packet before normalizing repeated long waits",
            },
        ],
    }


def _frontend_vitest_scope_paths(repo_root: Path, scope_paths: Sequence[str], extra_args: Sequence[str]) -> tuple[list[str], list[str]]:
    explicit_scopes = _scope_paths(scope_paths)
    test_args = [str(arg) for arg in extra_args if str(arg).strip()]
    if not explicit_scopes and not test_args:
        explicit_scopes = [str(ROOT_NAVIGATOR_TEST_REL)]
    ui_dir = repo_root / FRONTEND_UI_DIR_REL
    ui_rel_parts = FRONTEND_UI_DIR_REL.parts
    scopes: list[str] = []
    for scope in explicit_scopes:
        token = scope.split("::", 1)[0]
        resolved = Path(token)
        if not resolved.is_absolute():
            if resolved.parts[: len(ui_rel_parts)] == ui_rel_parts:
                resolved = repo_root / resolved
            elif resolved.parts[:1] == ("src",):
                resolved = ui_dir / resolved
            else:
                resolved = repo_root / resolved
        try:
            rel_to_ui = resolved.relative_to(ui_dir)
        except ValueError:
            scopes.append(token)
            continue
        scopes.append(str(FRONTEND_UI_DIR_REL / rel_to_ui))
        test_rel = rel_to_ui
        if test_rel.suffix in {".ts", ".tsx"} and "__tests__" not in test_rel.parts:
            candidate = test_rel.parent / "__tests__" / f"{test_rel.stem}.test{test_rel.suffix}"
            if (ui_dir / candidate).is_file():
                test_rel = candidate
        if str(test_rel) not in test_args:
            test_args.append(str(test_rel))
    if not any(arg == "--reporter" or arg.startswith("--reporter=") for arg in test_args):
        test_args.insert(0, "--reporter=basic")
    return _scope_paths(scopes), test_args


def _frontend_vitest_process_evidence(repo_root: Path) -> dict[str, Any]:
    summary = _read_json(repo_root / PROCESS_SUMMARY_REL)
    top_rows = _as_list(summary.get("top_bottlenecks"))
    matching = {}
    for row in (_as_mapping(item) for item in top_rows):
        if row.get("action_kind") != "test_or_build_command":
            continue
        examples = _as_list(row.get("example_spans"))
        if not any("RootNavigator" in str(example.get("normalized_command") or "") for example in (_as_mapping(item) for item in examples)):
            continue
        matching = row
        break
    age_s = _age_seconds(summary.get("generated_at"))
    freshness = (
        "stale"
        if isinstance(age_s, (int, float)) and age_s > PROCESS_BOTTLENECK_STALE_AFTER_S
        else ("fresh" if summary else "missing")
    )
    return {
        "source": str(PROCESS_SUMMARY_REL),
        "status": "matched_rootnavigator_bottleneck" if matching else ("summary_available" if summary else "missing_summary"),
        "generated_at": summary.get("generated_at"),
        "age_s": age_s,
        "freshness": freshness,
        "owner_route": PROCESS_BOTTLENECK_OWNER_COMMAND,
        "force_live_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "top_bottleneck": _process_bottleneck_top_row(matching) if matching else None,
        "privacy": "metadata_only_no_stdout_stderr_bodies",
    }


def _quote_frontend_vitest(
    repo_root: Path,
    scope_paths: Sequence[str],
    extra_args: Sequence[str],
    *,
    current_session_id: str | None = None,
) -> dict[str, Any]:
    scopes, test_args = _frontend_vitest_scope_paths(repo_root, scope_paths, extra_args)
    package_path = repo_root / FRONTEND_UI_PACKAGE_REL
    config_path = repo_root / FRONTEND_UI_VITEST_CONFIG_REL
    status = "ready" if package_path.is_file() and config_path.is_file() else "missing_frontend_test_surface"
    direct_vitest_command = f"cd {FRONTEND_UI_DIR_REL} && npm test -- {shlex.join(test_args)}"
    command = f"./repo-python {FRONTEND_VITEST_TOOL_REL} -- {shlex.join(test_args)}"
    claim_snapshot = _active_claims_snapshot(repo_root, limit=50)
    claim_conflicts = _claim_conflicts(
        repo_root,
        scopes or [str(FRONTEND_UI_DIR_REL)],
        snapshot=claim_snapshot,
        current_session_id=current_session_id,
    )
    do_not_touch: list[dict[str, Any]] = [
        {
            "lane": "tmp_redirect_and_grep_masked_vitest",
            "reason": "Process diagnostics show slow frontend tests hidden behind /tmp output files and grep filters, which loses failure authority.",
            "replacement": command,
        },
        {
            "lane": "repo_root_npx_or_npm_test_without_ui_cwd",
            "reason": "The frontend owner script lives under system/server/ui; run from that cwd so config, aliases, and jsdom setup are explicit.",
            "replacement": command,
        },
    ]
    if claim_conflicts:
        do_not_touch.append(
            {
                "lane": "claimed_frontend_scope",
                "reason": "Work Ledger active claims overlap the requested frontend validation scope.",
                "paths": [row.get("path") for row in claim_conflicts if row.get("path")],
                "owner_surface": "./repo-python tools/meta/factory/work_ledger.py session-claims",
            }
        )
    return {
        "current_status": status if not claim_conflicts else "claim_conflict",
        "recommendation": "run_frontend_vitest_guarded_launcher" if not claim_conflicts else "defer_or_resolve_claim_conflict",
        "freshness": "live_path_metadata",
        "authority_level": "focused_frontend_validation",
        "drilldown_command": command,
        "suggested_command": command,
        "underlying_argv": ["./repo-python", str(FRONTEND_VITEST_TOOL_REL), "--", *test_args],
        "direct_vitest_command": direct_vitest_command,
        "vitest_argv": ["npm", "test", "--", *test_args],
        "cwd": str(FRONTEND_UI_DIR_REL),
        "scope_paths": scopes,
        "test_args": test_args,
        "claim_conflicts": claim_conflicts,
        "claim_snapshot": {
            "status": claim_snapshot.get("status"),
            "source_freshness": _as_mapping(claim_snapshot.get("source_freshness")),
        },
        "current_session_id": current_session_id,
        "do_not_touch": do_not_touch,
        "process_evidence": _frontend_vitest_process_evidence(repo_root),
        "source": {
            "package_json": str(FRONTEND_UI_PACKAGE_REL),
            "vitest_config": str(FRONTEND_UI_VITEST_CONFIG_REL),
            "mutation_status": "read_only_path_metadata",
        },
    }


def _station_render_manifest_summary(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / STATION_RENDER_MANIFEST_REL
    manifest = _read_json(manifest_path)
    if not manifest:
        return {
            "status": "missing_or_unreadable",
            "path": str(STATION_RENDER_MANIFEST_REL),
        }
    views = _as_list(manifest.get("views"))
    viewport_profiles = _as_list(manifest.get("viewport_profiles"))
    capture_defaults = _as_mapping(manifest.get("capture_defaults"))
    return {
        "status": "available",
        "path": str(STATION_RENDER_MANIFEST_REL),
        "schema_version": manifest.get("schema_version"),
        "default_backend": manifest.get("default_backend"),
        "default_engines": _as_list(manifest.get("default_engines")),
        "viewport_count": len(viewport_profiles),
        "view_count": len(views),
        "capture_defaults": {
            "headless": capture_defaults.get("headless"),
            "timeout_ms": capture_defaults.get("timeout_ms"),
            "stabilize_ms": capture_defaults.get("stabilize_ms"),
            "full_page": capture_defaults.get("full_page"),
        },
        "view_preview": [
            {
                "slug": row.get("slug"),
                "route": row.get("route"),
                "capture_group": row.get("capture_group"),
            }
            for row in (_as_mapping(item) for item in views[:8])
            if row.get("slug")
        ],
    }


def _station_render_timing_summary(repo_root: Path) -> dict[str, Any]:
    index_path = repo_root / STATION_RENDER_LOAD_INDEX_REL
    index = _read_json(index_path)
    if not index:
        return {
            "status": "missing_or_unreadable",
            "path": str(STATION_RENDER_LOAD_INDEX_REL),
            "owner_command": "./repo-python -m tools.meta.observability.station_render timings --json",
        }
    views = _as_mapping(index.get("views"))
    timing_rows: list[dict[str, Any]] = []
    for row in (_as_mapping(item) for item in views.values()):
        timing_rows.append(
            {
                "view_slug": row.get("view_slug"),
                "latest_status": row.get("latest_status"),
                "latest_load_ms": row.get("latest_load_ms"),
                "p95_load_ms": row.get("p95_load_ms"),
                "max_load_ms": row.get("max_load_ms"),
                "sample_count": row.get("sample_count"),
            }
        )
    timing_rows.sort(
        key=lambda row: int(row.get("p95_load_ms") or row.get("max_load_ms") or 0),
        reverse=True,
    )
    return {
        "status": "available",
        "path": str(STATION_RENDER_LOAD_INDEX_REL),
        "generated_at": index.get("generated_at"),
        "age_s": _age_seconds(index.get("generated_at")),
        "totals": _as_mapping(index.get("totals")),
        "slow_views_preview": timing_rows[:8],
        "owner_command": "./repo-python -m tools.meta.observability.station_render timings --json",
    }


def _paper_module_index_metadata(repo_root: Path) -> dict[str, Any]:
    index = _read_json(repo_root / PAPER_MODULE_INDEX_REL)
    report = _read_json(repo_root / PAPER_MODULE_VALIDATION_REL)
    route_coverage = _read_json(repo_root / PAPER_MODULE_ROUTE_COVERAGE_REL)
    if not index and not report and not route_coverage:
        return {
            "status": "missing_projection_sidecars",
            "index_path": str(PAPER_MODULE_INDEX_REL),
            "validation_report_path": str(PAPER_MODULE_VALIDATION_REL),
            "route_coverage_path": str(PAPER_MODULE_ROUTE_COVERAGE_REL),
        }
    report_summary = _as_mapping(report.get("summary"))
    route_summary = _as_mapping(route_coverage.get("summary"))
    freshness = _as_mapping((report or index or route_coverage).get("freshness"))
    source_manifest = _as_mapping((report or index or route_coverage).get("source_manifest"))
    return {
        "status": "available",
        "index_path": str(PAPER_MODULE_INDEX_REL),
        "validation_report_path": str(PAPER_MODULE_VALIDATION_REL),
        "route_coverage_path": str(PAPER_MODULE_ROUTE_COVERAGE_REL),
        "generated_at": report.get("generated_at") or index.get("generated_at") or route_coverage.get("generated_at"),
        "age_s": _age_seconds(report.get("generated_at") or index.get("generated_at") or route_coverage.get("generated_at")),
        "schema_version": report.get("schema_version") or index.get("schema_version"),
        "module_count": report_summary.get("module_count") or index.get("module_count"),
        "candidate_count": report_summary.get("candidate_count") or index.get("candidate_count"),
        "status_counts": _as_mapping(report_summary.get("status_counts") or index.get("status_counts")),
        "queue_counts": _as_mapping(report_summary.get("queue_counts")),
        "severity_counts": _as_mapping(report_summary.get("severity_counts")),
        "fact_audit": _as_mapping(report_summary.get("fact_audit")),
        "freshness": {
            "sync_status": freshness.get("sync_status"),
            "generated_at": freshness.get("generated_at"),
            "authored_module_count": freshness.get("authored_module_count"),
            "generated_module_count": freshness.get("generated_module_count"),
            "missing_from_index": freshness.get("missing_from_index"),
            "missing_from_report": freshness.get("missing_from_report"),
        },
        "route_coverage": {
            "module_count": route_summary.get("module_count"),
            "routed_module_count": route_summary.get("routed_module_count"),
            "unrouted_module_count": route_summary.get("unrouted_module_count"),
            "route_health_attention_count": route_summary.get("route_health_attention_count"),
            "metabolism_worklist_count": len(_as_list(route_coverage.get("metabolism_worklist"))),
        },
        "source_manifest": {
            "schema_version": source_manifest.get("schema_version"),
            "standard": source_manifest.get("standard"),
            "module_count": _as_mapping(source_manifest.get("modules")).get("count"),
            "source_fingerprint": _as_mapping(source_manifest.get("source_fingerprint")).get("digest"),
        },
    }


def _quote_paper_module_index(repo_root: Path) -> dict[str, Any]:
    metadata = _paper_module_index_metadata(repo_root)
    tool_exists = (repo_root / PAPER_MODULE_INDEX_TOOL_REL).is_file()
    return {
        "current_status": "cached_sidecars_available" if tool_exists and metadata.get("status") == "available" else "owner_or_sidecars_missing",
        "recommendation": "use_cluster_or_cached_metadata_before_builder",
        "freshness": "cached_projection_metadata",
        "authority_level": "cached_projection_metadata",
        "drilldown_command": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
        "suggested_command": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
        "check_command": "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
        "write_command": "./repo-python tools/meta/factory/build_paper_module_index.py",
        "post_write_projection_command": "./repo-python tools/meta/factory/build_agent_bootstrap_projection.py",
        "replacement_command": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
        "compact_module_card_command": "./repo-python kernel.py --option-surface paper_modules --band card --ids <slug>",
        "full_module_read_command": "./repo-python kernel.py --paper-module <slug>",
        "recommended_sequence": [
            "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            "./repo-python kernel.py --option-surface paper_modules --band card --ids <slug>",
            "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
        ],
        "avoid_command_shape": (
            "./repo-python tools/meta/factory/build_paper_module_index.py 2>&1 | head/tail/grep"
        ),
        "avoid_command_shapes": [
            "./repo-python tools/meta/factory/build_paper_module_index.py 2>&1 | head/tail/grep",
            "./repo-python kernel.py --paper-module <slug> 2>&1 | head/tail/sed/grep",
        ],
        "output_economy": {
            "routine_first_route": "./repo-python kernel.py --option-surface paper_modules --band card --ids <slug>",
            "full_body_route": "./repo-python kernel.py --paper-module <slug>",
            "full_body_use": "Only after a stable slug is selected and the module prose itself is needed.",
            "privacy": "metadata_and_route_fields_only_no_module_bodies_or_stdout_stderr_bodies",
        },
        "do_not_touch": [
            {
                "lane": "full_builder_for_discovery",
                "reason": "The paper-module builder is corpus-wide and can be slow; use cluster/card routes or cached sidecar metadata before write-mode regeneration.",
                "replacement": "./repo-python tools/meta/control/action_quote.py --action paper_module_index",
            },
            {
                "lane": "builder_output_limiter",
                "reason": "Shell head/tail hides freshness and source-coupling fields after paying the builder cost.",
                "replacement": "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
            },
            {
                "lane": "paper_module_output_limiter",
                "reason": "Direct --paper-module reads through head/tail/sed/grep pay the full module body cost and hide the compact route/currentness fields.",
                "replacement": "./repo-python kernel.py --option-surface paper_modules --band card --ids <slug>",
            },
            {
                "lane": "direct_generated_sidecar_edit",
                "reason": "Paper-module sidecars and README regions are generated projections; refresh through the owner builder.",
                "replacement": "./repo-python tools/meta/factory/build_paper_module_index.py",
            },
        ],
        "metadata": metadata,
        "source": {
            "privacy": "metadata_only_no_paper_module_bodies_or_stdout_stderr_bodies",
            "mutation_status": "read_only_projection_sidecars",
            "owner_tool": str(PAPER_MODULE_INDEX_TOOL_REL),
            "generated_sidecars": [
                str(PAPER_MODULE_INDEX_REL),
                str(PAPER_MODULE_VALIDATION_REL),
                str(PAPER_MODULE_ROUTE_COVERAGE_REL),
                str(PAPER_MODULE_README_REL),
            ],
            "full_authority_commands": [
                "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
                "./repo-python tools/meta/factory/build_paper_module_index.py",
            ],
        },
    }


def _generated_state_scope_owner_ids(scope_paths: Sequence[str]) -> list[str]:
    matched: set[str] = set()
    for raw in scope_paths:
        normalized = re.sub(r"[^a-z0-9]+", "_", str(raw).strip().lower()).strip("_")
        if not normalized:
            continue
        if normalized in GENERATED_STATE_SETTLEMENT_OWNER_IDS:
            matched.add(normalized)
        elif "task_ledger" in normalized:
            matched.add("task_ledger_projection")
        elif "work_ledger" in normalized:
            matched.add("work_ledger_index_projection")
        elif "system_atlas" in normalized:
            matched.add("system_atlas_projection")
    return [owner_id for owner_id in GENERATED_STATE_SETTLEMENT_OWNER_IDS if owner_id in matched]


def _generated_state_owner_args(owner_ids: Sequence[str]) -> str:
    return "".join(f" --owner-id {owner_id}" for owner_id in owner_ids)


def _quote_generated_state_settlement(repo_root: Path, scope_paths: Sequence[str]) -> dict[str, Any]:
    scopes = _scope_paths(scope_paths)
    owner_ids = _generated_state_scope_owner_ids(scope_paths)
    selected_owner_id = owner_ids[0] if len(owner_ids) == 1 else None
    owner_args = _generated_state_owner_args(owner_ids)
    tool_exists = (repo_root / GENERATED_STATE_DRAINER_REL).is_file()
    owner_check_command = f"{GENERATED_STATE_SETTLEMENT_OWNER_COMMAND}{owner_args}"
    status_command = (
        "./repo-python tools/meta/control/generated_state_drainer.py status --compact"
        f"{owner_args}"
    )
    dry_run_command = (
        f"./repo-python tools/meta/control/generated_state_drainer.py settle{owner_args} --dry-run --fast-plan"
        if owner_ids
        else GENERATED_STATE_SETTLEMENT_DRY_RUN_COMMAND
    )
    refresh_commands_by_owner = {
        owner_id: (
            "./repo-python tools/meta/control/generated_state_drainer.py apply --only "
            f"{refresh_action}"
        )
        for owner_id, refresh_action in GENERATED_STATE_SETTLEMENT_REFRESH_ACTIONS.items()
    }
    direct_land_commands_by_owner = {
        owner_id: (
            "./repo-python tools/meta/control/generated_state_drainer.py land "
            f"--owner-id {owner_id} --mode append-exempt --dry-run"
        )
        for owner_id in GENERATED_STATE_SETTLEMENT_OWNER_IDS
    }
    refresh_command = refresh_commands_by_owner.get(selected_owner_id) if selected_owner_id else None
    direct_land_dry_run_command = (
        direct_land_commands_by_owner.get(selected_owner_id) if selected_owner_id else None
    )
    recommended_next: list[dict[str, Any]] = [
        {
            "action": "inspect_generated_state_settlement_plan",
            "reason": "Use the owner settlement read model before running any projection refresh or landing.",
            "command": owner_check_command,
        },
        {
            "action": "run_generated_state_settlement_dry_run",
            "reason": "Fast dry-run reports cached-status owner bundles and required actions without committing.",
            "command": dry_run_command,
        },
    ]
    if selected_owner_id and refresh_command:
        recommended_next.append(
            {
                "action": "refresh_selected_owner_if_required",
                "reason": "Only run the owner refresh when the dry-run reports projection_not_fresh.",
                "command": refresh_command,
            }
        )
    if selected_owner_id and direct_land_dry_run_command:
        recommended_next.append(
            {
                "action": "direct_land_selected_owner_after_fresh_dry_run",
                "reason": "Prefer owner-specific append-exempt landing when one projection owner is known.",
                "command": direct_land_dry_run_command,
            }
        )
    return {
        "current_status": "owner_tool_available" if tool_exists else "owner_tool_missing",
        "recommendation": (
            "run_generated_state_settlement_owner_dry_run"
            if owner_ids
            else "run_generated_state_settlement_plan_before_loop"
        ),
        "freshness": "owner_plan_required",
        "authority_level": "owner_settlement_plan",
        "drilldown_command": owner_check_command,
        "suggested_command": dry_run_command,
        "replacement_command": dry_run_command,
        "status_command": status_command,
        "owner_check_command": owner_check_command,
        "dry_run_command": dry_run_command,
        "refresh_command": refresh_command,
        "refresh_commands_by_owner": refresh_commands_by_owner,
        "direct_land_dry_run_command": direct_land_dry_run_command,
        "direct_land_commands_by_owner": direct_land_commands_by_owner,
        "supported_owner_ids": list(GENERATED_STATE_SETTLEMENT_OWNER_IDS),
        "selected_owner_ids": owner_ids,
        "selected_owner_id": selected_owner_id,
        "scope_paths": scopes,
        "recommended_next": recommended_next,
        "do_not_touch": [
            {
                "lane": "manual_generated_projection_staging",
                "reason": "Generated projection bundles must move through generated_state_drainer owner plans, not broad git add.",
                "replacement": dry_run_command,
            },
            {
                "lane": "unbounded_generated_state_settle_loop",
                "reason": "Concurrent event ledgers can advance after a successful landing; stop after a bounded owner attempt and capture churn instead of looping.",
                "replacement": owner_check_command,
            },
            {
                "lane": "eventful_closeout_before_settlement",
                "reason": "Task Ledger or Work Ledger event writes can self-invalidate projection landing; capture required events before quoting settlement.",
                "replacement": status_command,
            },
        ],
        "output_economy": {
            "routine_first_route": owner_check_command,
            "dry_run_route": dry_run_command,
            "owner_specific_landing_route": "./repo-python tools/meta/control/generated_state_drainer.py land --owner-id <owner_id> --mode append-exempt --dry-run",
            "privacy": "metadata_and_owner_status_only_no_event_bodies_or_projection_bodies",
        },
        "source": {
            "privacy": "metadata_only_no_event_jsonl_bodies_or_generated_projection_bodies",
            "mutation_status": "quote_is_read_only",
            "owner_tool": str(GENERATED_STATE_DRAINER_REL),
            "owner_library": "system/lib/generated_state_drainer.py",
            "full_authority_commands": [
                status_command,
                owner_check_command,
                dry_run_command,
            ],
        },
    }


def _configured_scoped_commit_min_free_bytes() -> int:
    raw = os.environ.get(SCOPED_COMMIT_MIN_FREE_BYTES_ENV)
    if raw is None or not raw.strip():
        return SCOPED_COMMIT_MIN_FREE_BYTES_DEFAULT
    try:
        return max(0, int(raw.strip()))
    except ValueError:
        return SCOPED_COMMIT_MIN_FREE_BYTES_DEFAULT


def _scoped_commit_path_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return int(path.stat().st_size)
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        try:
            total += int(child.stat().st_size)
        except OSError:
            continue
    return total


def _scoped_commit_disk_headroom_quote(repo_root: Path, scope_paths: Sequence[str]) -> dict[str, Any]:
    scopes = _scope_paths(scope_paths)
    usage = shutil.disk_usage(str(repo_root))
    estimated_bytes = sum(_scoped_commit_path_size_bytes(repo_root / rel) for rel in scopes)
    configured_floor = _configured_scoped_commit_min_free_bytes()
    required_bytes = max(
        configured_floor,
        SCOPED_COMMIT_WRITE_ESTIMATE_FLOOR_BYTES
        + (estimated_bytes * SCOPED_COMMIT_WRITE_AMPLIFICATION),
    )
    return {
        "schema": "scoped_commit_disk_headroom_v0",
        "ok": int(usage.free) >= int(required_bytes),
        "usage_path": str(repo_root),
        "free_bytes": int(usage.free),
        "required_bytes": int(required_bytes),
        "configured_min_free_bytes": int(configured_floor),
        "estimated_declared_path_bytes": int(estimated_bytes),
        "write_amplification": SCOPED_COMMIT_WRITE_AMPLIFICATION,
        "checked_paths": scopes,
        "env_var": SCOPED_COMMIT_MIN_FREE_BYTES_ENV,
        "storage_scan_command": SCOPED_COMMIT_STORAGE_SCAN_COMMAND,
        "storage_safe_clean_command": SCOPED_COMMIT_STORAGE_SAFE_CLEAN_COMMAND,
    }


def _scoped_commit_path_args(scope_paths: Sequence[str]) -> str:
    return " ".join(f"--path {shlex.quote(path)}" for path in _scope_paths(scope_paths))


def _quote_scoped_commit_private_index(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    current_session_id: str | None = None,
) -> dict[str, Any]:
    scopes = _scope_paths(scope_paths)
    path_args = _scoped_commit_path_args(scopes)
    scope_args = " ".join(f"--scope {shlex.quote(path)}" for path in scopes)
    owned_path_args = " ".join(f"--owned-path {shlex.quote(path)}" for path in scopes)
    tool_exists = (repo_root / SCOPED_COMMIT_TOOL_REL).is_file()
    headroom = _scoped_commit_disk_headroom_quote(repo_root, scopes)
    claims_snapshot = _active_claims_snapshot(repo_root, limit=50)
    claim_conflicts = _claim_conflicts(
        repo_root,
        scopes,
        snapshot=claims_snapshot,
        current_session_id=current_session_id,
    )
    def _scoped_commit_command_for(session_id: str | None) -> str:
        session_arg = (
            f" --work-ledger-session-id {shlex.quote(session_id)}"
            if session_id
            else ""
        )
        return (
            "./repo-python tools/meta/control/scoped_commit.py full-paths "
            f"{path_args} --expected-parent $(git rev-parse HEAD){session_arg} "
            '--message "<scope>: <what landed>"'
        ).strip()

    def _preflight_command_for(session_id: str | None) -> str:
        session_arg = f"--session-id {shlex.quote(session_id)} " if session_id else ""
        return (
            "./repo-python tools/meta/control/mission_transaction_preflight.py "
            f"{session_arg}{owned_path_args} --fail-on-status blocked"
        ).strip()

    scoped_commit_command = _scoped_commit_command_for(current_session_id)
    dry_run_command = f"{scoped_commit_command} --dry-run"
    preflight_command = _preflight_command_for(current_session_id)
    claim_command = (
        "./repo-python tools/meta/factory/work_ledger.py session-preflight "
        "--session-slug <slug> "
        f"{path_args} --work-admission-class edit_light_patch"
    ).strip()
    owner_session_ids = {
        str(row.get("session_id") or "")
        for row in claim_conflicts
        if row.get("session_id")
    }
    single_owner_session_id = (
        next(iter(owner_session_ids))
        if len(owner_session_ids) == 1
        and all(str(row.get("session_id") or "") in owner_session_ids for row in claim_conflicts)
        else None
    )
    owner_session_handoff = None
    if single_owner_session_id:
        owner_commit_command = _scoped_commit_command_for(single_owner_session_id)
        owner_dry_run_command = f"{owner_commit_command} --dry-run"
        owner_quote_command = (
            "./repo-python tools/meta/control/action_quote.py "
            f"--action scoped_commit_private_index {scope_args} "
            f"--session-id {shlex.quote(single_owner_session_id)}"
        ).strip()
        owner_session_handoff = {
            "status": "single_session_claim_match",
            "session_id": single_owner_session_id,
            "guard": "Use only when this actor owns the active Work Ledger session claims.",
            "quote_command": owner_quote_command,
            "preflight_command": _preflight_command_for(single_owner_session_id),
            "dry_run_command": owner_dry_run_command,
            "scoped_commit_command": owner_commit_command,
        }
    do_not_touch: list[dict[str, Any]] = [
        {
            "lane": "shared_index_git_add_commit",
            "reason": "In this repo, normal git add/commit can stage unrelated shared-tree dirt; use scoped_commit.py private-index paths.",
            "replacement": scoped_commit_command,
        },
        {
            "lane": "lower_scoped_commit_disk_floor_first",
            "reason": "Lower AIW_SCOPED_COMMIT_MIN_FREE_BYTES only for an explicitly safe emergency write after safe cleanup has been considered.",
            "replacement": SCOPED_COMMIT_STORAGE_SCAN_COMMAND,
        },
    ]
    if not scopes:
        current_status = "missing_scope_paths"
        recommendation = "select_exact_paths_before_scoped_commit"
        suggested_command = "./repo-python tools/meta/control/action_quote.py --action scoped_commit --scope <path>"
    elif not tool_exists:
        current_status = "owner_tool_missing"
        recommendation = "restore_scoped_commit_owner_tool"
        suggested_command = "rg -n 'scoped_commit.py' tools/meta/control system/lib"
    elif not bool(headroom.get("ok")):
        current_status = "disk_headroom_blocked"
        recommendation = "run_storage_doctor_safe_cleanup_before_scoped_commit"
        suggested_command = SCOPED_COMMIT_STORAGE_SAFE_CLEAN_COMMAND
        do_not_touch.append(
            {
                "lane": "private_index_commit_without_disk_headroom",
                "reason": "scoped_commit.py refuses private-index writes below its free-space floor.",
                "free_bytes": headroom.get("free_bytes"),
                "required_bytes": headroom.get("required_bytes"),
                "replacement": SCOPED_COMMIT_STORAGE_SAFE_CLEAN_COMMAND,
            }
        )
    elif claim_conflicts:
        current_status = "claim_conflict"
        if owner_session_handoff:
            recommendation = "rerun_with_owner_session_id_if_current_actor_owns_claims"
            suggested_command = str(owner_session_handoff["quote_command"])
        else:
            recommendation = "claim_or_defer_scoped_commit"
            suggested_command = claim_command
        do_not_touch.append(
            {
                "lane": "claimed_scope",
                "reason": "Work Ledger active claims overlap the requested commit scope.",
                "paths": [row.get("path") for row in claim_conflicts if row.get("path")],
                "replacement": (
                    owner_session_handoff["quote_command"]
                    if owner_session_handoff
                    else claim_command
                ),
            }
        )
    else:
        current_status = "ready"
        recommendation = "run_private_index_scoped_commit_after_preflight"
        suggested_command = scoped_commit_command
    return {
        "current_status": current_status,
        "recommendation": recommendation,
        "freshness": "live_disk_and_claim_metadata",
        "authority_level": "disk_and_claim_preflight",
        "drilldown_command": dry_run_command,
        "suggested_command": suggested_command,
        "replacement_command": scoped_commit_command,
        "dry_run_command": dry_run_command,
        "preflight_command": preflight_command,
        "claim_command": claim_command,
        "expected_parent_command": "./repo-git rev-parse HEAD",
        "storage_scan_command": SCOPED_COMMIT_STORAGE_SCAN_COMMAND,
        "storage_safe_clean_command": SCOPED_COMMIT_STORAGE_SAFE_CLEAN_COMMAND,
        "scope_paths": scopes,
        "disk_headroom": headroom,
        "claim_conflicts": claim_conflicts,
        "owner_session_handoff": owner_session_handoff,
        "claim_snapshot": {
            "status": claims_snapshot.get("status"),
            "source_freshness": _as_mapping(claims_snapshot.get("source_freshness")),
        },
        "current_session_id": current_session_id,
        "do_not_touch": do_not_touch,
        "recommended_next": (
            [
                {
                    "action": "rerun_quote_with_owner_session_id",
                    "reason": "All overlapping claims resolve to one session; bind the quote to that session only if this actor owns it.",
                    "command": owner_session_handoff["quote_command"],
                    "guard": owner_session_handoff["guard"],
                },
                {
                    "action": "run_transaction_preflight_with_owner_session_id",
                    "reason": "Preflight can treat that session's active claims as owned.",
                    "command": owner_session_handoff["preflight_command"],
                    "guard": owner_session_handoff["guard"],
                },
                {
                    "action": "dry_run_private_index_commit_with_owner_session_id",
                    "reason": "Dry-run the private-index commit with the owner session id before mutating HEAD.",
                    "command": owner_session_handoff["dry_run_command"],
                    "guard": owner_session_handoff["guard"],
                },
                {
                    "action": "run_private_index_scoped_commit_with_owner_session_id",
                    "reason": "Commit only after the session-bound dry run succeeds.",
                    "command": owner_session_handoff["scoped_commit_command"],
                    "guard": owner_session_handoff["guard"],
                },
            ]
            if owner_session_handoff and claim_conflicts
            else [
                {
                    "action": "claim_scope_if_needed",
                    "reason": "Path claims prevent same-scope edits from racing in the shared tree.",
                    "command": claim_command,
                },
                {
                    "action": "run_transaction_preflight",
                    "reason": "Mission preflight checks generated ownership, claims, staged index, and dirty-tree pressure.",
                    "command": preflight_command,
                },
                {
                    "action": "dry_run_private_index_commit",
                    "reason": "Dry-run checks pathset, disk headroom, multi-hunk guard, and expected parent before update-ref.",
                    "command": dry_run_command,
                },
            ]
        ),
        "source": {
            "privacy": "path_metadata_claim_metadata_and_disk_counts_only_no_diff_bodies",
            "mutation_status": "quote_is_read_only",
            "owner_tool": str(SCOPED_COMMIT_TOOL_REL),
        },
    }


def _quote_helper_lease_admission(_repo_root: Path) -> dict[str, Any]:
    suggested = (
        "./repo-python tools/meta/factory/work_ledger.py helper-lease-admission "
        "--lease-kind <playwright_mcp|codex_stdio_app_server|chrome_devtools_mcp|vite_dev_server|other_tool_bridge> "
        "--requested-by <session_id> --owner-status <active_session|unknown_parent>"
    )
    return {
        "current_status": "helper_lease_gate_available",
        "recommendation": "gate_helper_lease_before_start",
        "freshness": "live_host_pressure_gate",
        "authority_level": "pressure_budget_gate",
        "drilldown_command": suggested,
        "suggested_command": suggested,
        "replacement_command": suggested,
        "receipt_schema": "helper_lease_admission_receipt_v1",
        "owner_release_receipt_schema": "helper_owner_release_request_v1",
        "guardrails": {
            "no_unknown_owner_killed": True,
            "no_process_signal_sent": True,
            "no_active_session_terminated": True,
        },
        "recommended_next": [
            {
                "action": "gate_new_helper_lease",
                "command": suggested,
                "reason": "Persistent helpers add resident RSS; allocate new helper leases through the pressure budget under degraded host pressure.",
            }
        ],
    }


def _quote_resident_pressure_relief(_repo_root: Path) -> dict[str, Any]:
    suggested = (
        "./repo-python tools/meta/factory/work_ledger.py resident-pressure-relief "
        "--process-kind <playwright_mcp|codex_stdio_app_server|chrome_devtools_mcp|vite_dev_server|other_tool_bridge> "
        "--owner-status <active_session|unknown_parent> "
        "--owner-release-result <accepted|unsupported|owner_unresolved> "
        "--background-loop-kind <agent_observability_sampler|projection_rebuild_loop> "
        "--background-loop-result <applied|unsupported>"
    )
    return {
        "current_status": "resident_relief_request_available",
        "recommendation": "route_existing_pressure_to_owner_release_or_downshift",
        "freshness": "live_pressure_budget_receipt_surface",
        "authority_level": "resident_relief_request_and_receipt",
        "drilldown_command": suggested,
        "suggested_command": suggested,
        "replacement_command": suggested,
        "receipt_schema": "resident_pressure_relief_window_v1",
        "owner_release_result_schema": "owner_release_result_receipt_v1",
        "background_downshift_schema": "background_loop_downshift_receipt_v1",
        "guardrails": {
            "front_door_blocks_not_counted_as_resident_relief": True,
            "no_unknown_owner_killed": True,
            "no_process_signal_sent": True,
            "no_active_session_terminated": True,
        },
        "recommended_next": [
            {
                "action": "request_owner_release_or_downshift",
                "command": suggested,
                "reason": "Existing helper/session pressure needs an accepted owner release or applied downshift before a recovery window can claim relief.",
            }
        ],
    }


def _session_yield_placeholder_command() -> str:
    return (
        "./repo-python tools/meta/factory/work_ledger.py session-yield-request "
        "--target-session-id <session_id> "
        "--target-class <idle_session|low_progress_session|high_helper_footprint_session> "
        "--requested-action <yield|hibernate|release_tool_lease|lower_poll_rate> "
        "--owner-status <active_session|unknown_parent> "
        "--helper-rss-mb <mb>"
    )


def _nonnegative_int(value: Any, *, default: int = 0) -> int:
    try:
        return max(0, int(float(str(value))))
    except (TypeError, ValueError):
        return default


def _session_yield_request_command(candidate: Mapping[str, Any]) -> str:
    parts = [
        "./repo-python",
        "tools/meta/factory/work_ledger.py",
        "session-yield-request",
        "--target-session-id",
        str(candidate.get("target_session_id") or ""),
        "--target-class",
        str(candidate.get("target_class") or "low_progress_session"),
        "--requested-action",
        str(candidate.get("requested_action") or "lower_poll_rate"),
        "--owner-status",
        str(candidate.get("owner_status") or "unknown_parent"),
        "--helper-rss-mb",
        str(candidate.get("helper_rss_mb") or 0),
        "--active-claim-count",
        str(candidate.get("active_claim_count") or 0),
        "--result",
        "requested",
    ]
    return " ".join(shlex.quote(part) for part in parts)


def _jsonl_tail(path: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                lines.append(line)
    records: list[dict[str, Any]] = []
    for line in lines[-max(1, int(limit or 1)) :]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _session_yield_payload(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    nested = row.get(key)
    if isinstance(nested, dict):
        return dict(nested)
    if key == "session_yield_request" and row.get("schema") == "session_yield_request_receipt_v1":
        return dict(row)
    if key == "session_yield_result" and row.get("schema") == "owner_yield_result_receipt_v1":
        return dict(row)
    return {}


def _pending_session_yield_request(repo_root: Path, target_session_id: str) -> dict[str, Any] | None:
    if not target_session_id:
        return None
    request_log = repo_root / SESSION_YIELD_REQUESTS_REL
    result_log = repo_root / SESSION_YIELD_RESULTS_REL
    closed_request_ids: set[str] = set()
    for row in _jsonl_tail(result_log, limit=200):
        result = _session_yield_payload(row, "session_yield_result")
        request_id = str(result.get("request_id") or "").strip()
        if request_id:
            closed_request_ids.add(request_id)
    for row in reversed(_jsonl_tail(request_log, limit=200)):
        request = _session_yield_payload(row, "session_yield_request")
        if str(request.get("target_id") or "").strip() != target_session_id:
            continue
        request_id = str(request.get("request_id") or "").strip()
        if request_id and request_id in closed_request_ids:
            continue
        if str(request.get("result") or "").strip().lower() != "requested":
            continue
        return {
            "request_id": request_id or None,
            "target_id": request.get("target_id"),
            "requested_action": request.get("requested_action"),
            "result": request.get("result"),
            "issued_at": request.get("issued_at"),
            "request_log_path": str(SESSION_YIELD_REQUESTS_REL),
            "result_log_path": str(SESSION_YIELD_RESULTS_REL),
        }
    return None


def _session_yield_cached_candidate(repo_root: Path) -> dict[str, Any]:
    snapshot = _active_claims_snapshot(repo_root, limit=50, allow_stale=True)
    seed_hint = _as_mapping(snapshot.get("seed_speed_hint"))
    rows = [
        _as_mapping(row)
        for row in _as_list(seed_hint.get("heartbeat_gap_claim_sessions"))
        if _as_mapping(row).get("session_id")
    ]
    if not rows:
        return {
            "status": "no_candidate_from_cached_claims",
            "source": "active_claims_snapshot.seed_speed_hint.heartbeat_gap_claim_sessions",
            "source_path": str(ACTIVE_CLAIMS_REL),
            "source_status": snapshot.get("status") or "unknown",
            "counts": dict(_as_mapping(snapshot.get("counts"))),
            "source_command": WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "refresh_command": WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
        }

    row = max(rows, key=lambda item: _nonnegative_int(item.get("active_claim_count")))
    candidate: dict[str, Any] = {
        "status": "candidate_available",
        "source": "active_claims_snapshot.seed_speed_hint.heartbeat_gap_claim_sessions",
        "source_path": str(ACTIVE_CLAIMS_REL),
        "source_status": snapshot.get("status") or "unknown",
        "rank": 1,
        "target_session_id": row.get("session_id"),
        "target_class": "low_progress_session",
        "requested_action": "lower_poll_rate",
        "owner_status": "active_session",
        "helper_rss_mb": 0,
        "active_claim_count": _nonnegative_int(row.get("active_claim_count")),
        "heartbeat_source": row.get("heartbeat_source"),
        "freshness_state": row.get("freshness_state"),
        "scope_ref": row.get("scope_ref"),
    }
    request_command = _session_yield_request_command(candidate)
    pending_request = _pending_session_yield_request(
        repo_root,
        str(candidate.get("target_session_id") or ""),
    )
    if pending_request:
        candidate["status"] = "pending_request_already_recorded"
        candidate["pending_request"] = pending_request
        candidate["suppressed_command"] = request_command
        candidate["control_command"] = SESSION_YIELD_CONTROL_COMMAND
        candidate["source_command"] = WORK_LEDGER_CLAIM_CARDS_COMMAND
    else:
        candidate["command"] = request_command
    return candidate


def _quote_session_yield_request(repo_root: Path) -> dict[str, Any]:
    placeholder = _session_yield_placeholder_command()
    ranked_candidate = _session_yield_cached_candidate(repo_root)
    candidate_available = ranked_candidate.get("status") == "candidate_available"
    suggested = str(
        ranked_candidate.get("command")
        or ranked_candidate.get("control_command")
        or ranked_candidate.get("source_command")
        or placeholder
    )
    if candidate_available:
        recommendation = "rank_resident_pressure_then_request_owner_yield"
        next_action = "request_owner_visible_session_yield"
        next_reason = (
            "A partial resident downshift requires the next safe owner-visible yield "
            "or tool-release request before claiming another recovery window."
        )
    else:
        if ranked_candidate.get("status") == "pending_request_already_recorded":
            recommendation = "wait_for_pending_session_yield_result"
            next_action = "inspect_pending_session_yield_result"
            next_reason = (
                "A pending owner-visible yield request already exists for this target; "
                "inspect yield control or claim cards instead of writing a duplicate request."
            )
        else:
            recommendation = "inspect_claim_cards_before_session_yield_request"
            next_action = "inspect_claim_cards_for_yield_candidate"
            next_reason = (
                "No cached yield candidate is available; inspect current claim cards before "
                "issuing an owner-visible request."
            )
    return {
        "current_status": "owner_yield_request_bus_available",
        "recommendation": recommendation,
        "freshness": "live_pressure_budget_request_surface",
        "authority_level": "owner_visible_request_bus",
        "drilldown_command": suggested,
        "suggested_command": suggested,
        "replacement_command": suggested,
        "placeholder_command": placeholder,
        "ranked_candidate": ranked_candidate,
        "ranked_candidate_status": ranked_candidate.get("status"),
        "receipt_schema": "session_yield_request_receipt_v1",
        "rank_schema": "session_pressure_rank_v1",
        "escalation_window_schema": "resident_relief_escalation_window_v1",
        "guardrails": {
            "session_yield_not_process_kill": True,
            "no_unknown_owner_killed": True,
            "no_process_signal_sent": True,
            "no_active_session_terminated": True,
        },
        "recommended_next": [
            {
                "action": next_action,
                "command": suggested,
                "reason": next_reason,
            }
        ],
    }


def _quote_session_yield_result(_repo_root: Path) -> dict[str, Any]:
    suggested = (
        "./repo-python tools/meta/factory/work_ledger.py session-yield-result "
        "--request-id <session_yield_request_id> "
        "--result <accepted|declined|unsupported|unreachable|owner_unresolved> "
        "--applied-action <none|yielded|hibernated|released_tool_lease|lowered_poll_rate>"
    )
    control = "./repo-python tools/meta/factory/work_ledger.py session-yield-control --limit 20"
    return {
        "current_status": "owner_yield_result_bus_available",
        "recommendation": "close_owner_yield_with_visible_result_before_recovery_claim",
        "freshness": "live_pressure_budget_result_surface",
        "authority_level": "owner_visible_result_bus",
        "drilldown_command": suggested,
        "suggested_command": suggested,
        "replacement_command": suggested,
        "control_surface_command": control,
        "receipt_schema": "owner_yield_result_receipt_v1",
        "accepted_window_schema": "accepted_resident_relief_window_v1",
        "guardrails": {
            "requested_is_not_accepted": True,
            "accepted_without_applied_action_is_not_relief": True,
            "unsupported_is_not_relief": True,
            "owner_yield_not_process_kill": True,
            "no_unknown_owner_killed": True,
            "no_process_signal_sent": True,
            "no_active_session_terminated": True,
        },
        "recommended_next": [
            {
                "action": "close_owner_yield_request_with_result",
                "command": suggested,
                "reason": "Resident relief is not applied until the owner accepts and an action such as lower_poll_rate or release_tool_lease is recorded.",
            },
            {
                "action": "inspect_pending_and_applied_yield_state",
                "command": control,
                "reason": "Station and operators need pending, accepted, unsupported, and applied relief split before recovery can be attributed.",
            },
        ],
    }


def _quote_station_render_capture(repo_root: Path, scope_paths: Sequence[str]) -> dict[str, Any]:
    manifest = _station_render_manifest_summary(repo_root)
    timings = _station_render_timing_summary(repo_root)
    tool_exists = (repo_root / STATION_RENDER_TOOL_REL).is_file()
    requested_views = [
        Path(scope).stem
        for scope in _scope_paths(scope_paths)
        if scope.endswith(".png") or scope.endswith(".json") or scope.startswith("state/observability/")
    ]
    suggested_view = requested_views[0] if requested_views else "<view>"
    narrow_render = (
        "./repo-python -m tools.meta.observability.station_render render "
        f"--view {shlex.quote(suggested_view)} --viewport fhd_landscape --engine chromium"
    )
    return {
        "current_status": "metadata_available" if tool_exists else "owner_tool_missing",
        "recommendation": "use_list_preflight_timings_before_broad_render",
        "freshness": "live_manifest_metadata",
        "authority_level": "manifest_and_timing_metadata",
        "drilldown_command": "./repo-python -m tools.meta.observability.station_render list",
        "suggested_command": "./repo-python -m tools.meta.observability.station_render list",
        "preflight_command": "./repo-python -m tools.meta.observability.station_render preflight --engine chromium",
        "timings_command": "./repo-python -m tools.meta.observability.station_render timings --limit 20 --json",
        "narrow_render_command": narrow_render,
        "replacement_command": "./repo-python -m tools.meta.observability.station_render list",
        "recommended_sequence": [
            "./repo-python -m tools.meta.observability.station_render list",
            "./repo-python -m tools.meta.observability.station_render timings --limit 20 --json",
            "./repo-python -m tools.meta.observability.station_render render --view <view> --viewport fhd_landscape --engine chromium",
        ],
        "avoid_command_shape": (
            "./repo-python -m tools.meta.observability.station_render render --view ... 2>&1 | head/tail/grep"
        ),
        "do_not_touch": [
            {
                "lane": "broad_station_render_matrix",
                "reason": "The default render matrix can multiply views, viewports, and engines; inspect manifest/timings and narrow view/engine/viewport first.",
                "replacement": "./repo-python tools/meta/control/action_quote.py --action station_render",
            },
            {
                "lane": "render_artifact_body_read",
                "reason": "Screenshot artifacts and render logs are evidence bodies, not routine command-routing metadata.",
                "replacement": "./repo-python -m tools.meta.observability.station_render timings --limit 20 --json",
            },
        ],
        "manifest": manifest,
        "timings": timings,
        "source": {
            "privacy": "metadata_only_no_screenshot_or_stdout_stderr_bodies",
            "mutation_status": "read_only_manifest_and_timing_index",
            "full_authority_commands": [
                "./repo-python -m tools.meta.observability.station_render render --view <view> --viewport <viewport> --engine <engine>",
                "./repo-python -m tools.meta.observability.station_render diff --help",
            ],
        },
    }


def _admission_consumer_coverage(_repo_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for action_id, config in HOST_PRESSURE_ADMISSION_BY_ACTION.items():
        consumer = dict(ADMISSION_CONSUMER_COVERAGE.get(action_id) or {})
        status = str(consumer.get("status") or "quote_only_unclassified")
        rows.append(
            {
                "action_id": action_id,
                "consumer_status": status,
                "consumer_surface": consumer.get("consumer_surface"),
                "action_class": consumer.get("action_class"),
                "policy_surface": consumer.get("policy_surface"),
                "override_surfaces": _as_list(consumer.get("override_surfaces")),
                "receipt_schema": consumer.get("receipt_schema"),
                "helper_surface": consumer.get("helper_surface"),
                "admission_action": consumer.get("admission_action"),
                "residual_id": consumer.get("residual_id"),
                "reentry_condition": consumer.get("reentry_condition"),
                "queue_exit_code": ADMISSION_TEMPFAIL if status.startswith("protected") else None,
                "workload_class": config.get("workload_class"),
                "admission_mode": config.get("mode"),
                "load_shed_recommendation": config.get("shed_recommendation"),
            }
        )
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("consumer_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    blocking_gap_statuses = {
        "quote_only_unbound",
        "quote_only_unclassified",
        "unbound_heavy_launcher",
        "owner_unknown",
    }
    blocking_gap_rows = [
        row
        for row in rows
        if str(row.get("consumer_status") or "") in blocking_gap_statuses
    ]
    return {
        "schema": "admission_consumer_coverage_v0",
        "source": "HOST_PRESSURE_ADMISSION_BY_ACTION + ADMISSION_CONSUMER_COVERAGE",
        "policy": {
            "boundary": "coverage map only; action_quote remains advisory and does not schedule work",
            "consumer_contract": ADMISSION_CONSUMER_SCHEMA,
            "protected_status_prefix": "protected",
            "blocking_gap_statuses": sorted(blocking_gap_statuses),
            "closed_statuses": [
                "protected_launcher",
                "protected_shared_launcher",
                "protected_projection_builder",
                "protected_generated_state_settlement",
                "protected_helper_lease_budget",
                "protected_resident_relief_request",
                "summary_first_diagnostic",
                "advisory_read_model",
                "attach_existing_only",
                "owner_routed_residual",
            ],
        },
        "summary": {
            "host_pressure_action_count": len(rows),
            "protected_count": sum(
                1 for row in rows if str(row.get("consumer_status") or "").startswith("protected")
            ),
            "summary_first_count": sum(
                1 for row in rows if row.get("consumer_status") == "summary_first_diagnostic"
            ),
            "advisory_read_model_count": sum(
                1 for row in rows if row.get("consumer_status") == "advisory_read_model"
            ),
            "owner_routed_residual_count": sum(
                1 for row in rows if row.get("consumer_status") == "owner_routed_residual"
            ),
            "quote_only_count": sum(
                1 for row in rows if str(row.get("consumer_status") or "").startswith("quote_only")
            ),
            "unbound_count": sum(
                1 for row in rows if str(row.get("consumer_status") or "").endswith("_unbound")
            ),
            "blocking_gap_count": len(blocking_gap_rows),
            "blocking_gap_action_ids": [
                str(row.get("action_id")) for row in blocking_gap_rows if row.get("action_id")
            ],
            "coverage_closure_status": "closed" if not blocking_gap_rows else "open",
            "status_counts": status_counts,
        },
        "rows": rows,
    }


def _admission_consumer_coverage_summary(
    coverage: Mapping[str, Any], *, include_status_counts: bool = False
) -> dict[str, Any]:
    summary = _as_mapping(coverage.get("summary"))
    slim_keys = (
        "host_pressure_action_count",
        "protected_count",
        "summary_first_count",
        "advisory_read_model_count",
        "owner_routed_residual_count",
        "quote_only_count",
        "unbound_count",
        "blocking_gap_count",
        "coverage_closure_status",
    )
    payload = {key: summary.get(key) for key in slim_keys if key in summary}
    blocking_gap_action_ids = _as_list(summary.get("blocking_gap_action_ids"))
    if blocking_gap_action_ids:
        payload["blocking_gap_action_ids"] = blocking_gap_action_ids
    if include_status_counts and isinstance(summary.get("status_counts"), Mapping):
        payload["status_counts"] = dict(summary["status_counts"])
    elif isinstance(summary.get("status_counts"), Mapping):
        payload["status_counts_omitted"] = len(summary["status_counts"])
    return payload


def _compact_admission_consumer_coverage(coverage: Mapping[str, Any]) -> dict[str, Any]:
    rows = _as_list(coverage.get("rows"))
    return {
        "schema": coverage.get("schema"),
        "summary": _admission_consumer_coverage_summary(coverage),
        "rows_omitted": True,
        "row_count": len(rows),
        "full_rows_command_ref": "action_quote_catalog",
    }


def _command_surface_trace_repair_alias_handoffs(
    alias_ids: Sequence[str] = COMMAND_SURFACE_TRACE_REPAIR_ALIAS_IDS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for alias in alias_ids:
        action_id = ACTION_ALIASES.get(alias)
        metadata = ACTION_CATALOG.get(str(action_id)) if action_id else None
        if not action_id or not metadata:
            continue
        rows.append(
            {
                "alias": alias,
                "action_id": action_id,
                "quote_command": f"./repo-python tools/meta/control/action_quote.py --action {alias}",
                "canonical_quote_command": (
                    f"./repo-python tools/meta/control/action_quote.py --action {action_id}"
                ),
                "purpose": metadata["purpose"],
                "resource_class": metadata["resource_class"],
                "owner_surface": metadata["owner_surface"],
            }
        )
    return rows


def _command_surface_action_handoffs(
    repo_root: Path | None = None,
    *,
    admission_coverage: Mapping[str, Any] | None = None,
    preview_ids: Sequence[str] = COMMAND_SURFACE_ACTION_HANDOFF_PREVIEW_IDS,
    alias_preview_limit: int = 6,
    profile: str = "compact_alias_preview",
    include_rows: bool = True,
) -> dict[str, Any]:
    aliases_by_action: dict[str, list[str]] = {action_id: [] for action_id in ACTION_CATALOG}
    for alias, action_id in ACTION_ALIASES.items():
        aliases_by_action.setdefault(action_id, []).append(alias)
    coverage = admission_coverage or (_admission_consumer_coverage(repo_root) if repo_root is not None else {})
    coverage_by_action = {
        str(row.get("action_id")): row
        for row in _as_list(coverage.get("rows"))
        if _as_mapping(row).get("action_id")
    }

    all_rows: list[dict[str, Any]] = []
    for action_id, metadata in ACTION_CATALOG.items():
        aliases = sorted(aliases_by_action.get(action_id, []))
        alias_preview = aliases[:alias_preview_limit]
        all_rows.append(
            {
                "action_id": action_id,
                "purpose": metadata["purpose"],
                "resource_class": metadata["resource_class"],
                "authority_level": metadata["authority_level"],
                "owner_surface": metadata["owner_surface"],
                "quote_command": f"./repo-python tools/meta/control/action_quote.py --action {action_id}",
                "alias_count": len(aliases),
                "aliases_preview": alias_preview,
                "aliases_omitted": max(0, len(aliases) - len(alias_preview)),
                "host_pressure_consumer_status": _as_mapping(
                    coverage_by_action.get(action_id)
                ).get("consumer_status"),
            }
        )
    rows_by_action = {row["action_id"]: row for row in all_rows}
    rows = [
        rows_by_action[action_id]
        for action_id in preview_ids
        if action_id in rows_by_action
    ]
    trace_alias_handoffs = _command_surface_trace_repair_alias_handoffs()
    coverage_summary = _admission_consumer_coverage_summary(
        coverage,
        include_status_counts=include_rows,
    )
    payload: dict[str, Any] = {
        "privacy": {
            "stores_file_contents": False,
            "stores_stdout_stderr_bodies": False,
        },
        "rows_profile": profile,
        "available_action_ids": [row["action_id"] for row in all_rows],
        "preview_action_ids": [row["action_id"] for row in rows],
        "summary": {
            "action_count": len(all_rows),
            "emitted_count": len(rows),
            "rows_omitted": max(0, len(all_rows) - len(rows)),
            "alias_count": sum(row["alias_count"] for row in all_rows),
            "host_pressure_protected_count": _as_mapping(
                coverage.get("summary")
            ).get("protected_count"),
            "host_pressure_unbound_count": _as_mapping(coverage.get("summary")).get(
                "unbound_count"
            ),
            "host_pressure_blocking_gap_count": _as_mapping(
                coverage.get("summary")
            ).get("blocking_gap_count"),
            "trace_repair_alias_count": len(trace_alias_handoffs),
        },
        "trace_repair_alias_handoffs": trace_alias_handoffs,
        "full_action_rows_command": "./repo-python tools/meta/control/action_quote.py --catalog",
        "full_admission_consumer_coverage_command": (
            "./repo-python tools/meta/control/action_quote.py --catalog"
        ),
    }
    if include_rows:
        payload["source"] = "ACTION_CATALOG + ACTION_ALIASES"
        payload["safe_decision_supported"] = (
            "select an existing quote action before broad command or artifact discovery"
        )
        payload["privacy"]["emits"] = (
            "action id, alias previews/counts, owner surface, resource class, and quote command metadata only"
        )
        payload["rows_omission_reason"] = (
            "command_surface_inventory is a first-contact route; preview rows keep common handoffs visible "
            "while the full action catalog remains the drilldown."
        )
        payload["admission_consumer_coverage_summary"] = coverage_summary
    if include_rows:
        payload["rows"] = rows
    else:
        payload["rows_omitted"] = True
        payload["row_detail_profile"] = "omitted_from_default_first_contact"
    return payload


def _iter_command_surface_inventory(
    repo_root: Path,
    *,
    limit: int = 120,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    match_count = len(COMMAND_SURFACE_MATCHING_CANDIDATE_PATHS)
    for rel_text in COMMAND_SURFACE_MATCHING_CANDIDATE_PATHS:
        if len(rows) >= limit:
            continue
        path = repo_root / rel_text
        try:
            stat = path.stat()
            size_bytes: int | None = stat.st_size
            status = "available"
        except OSError:
            size_bytes = None
            status = "missing"
        rows.append(
            {
                "path": rel_text,
                "status": status,
                "size_bytes": size_bytes,
                "surface_hint": "curated_command_surface_candidate",
            }
        )
    summary = {
        "root_count": len(COMMAND_SURFACE_INVENTORY_ROOTS),
        "candidate_count": len(COMMAND_SURFACE_CANDIDATE_PATHS),
        "match_count": match_count,
        "emitted_count": len(rows),
        "truncated": match_count > len(rows),
        "limit": limit,
        "scan_policy": "curated_path_metadata_only_no_content_walk",
        "raw_body_prune_dirs": sorted(COMMAND_SURFACE_PRUNE_DIRS),
    }
    return rows, summary


def _command_surface_scope_resolution(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    full: bool = False,
) -> dict[str, Any] | None:
    scopes = _scope_paths(scope_paths)
    if not scopes:
        return None
    haystack = " ".join(scopes).lower().replace("_", "-")

    def normalized_term(term: str) -> str:
        return str(term).lower().replace("_", "-")

    def term_matches(term: str) -> bool:
        if not term:
            return False
        if term in haystack:
            return True
        parts = [part for part in term.split() if part]
        return len(parts) > 1 and all(part in haystack for part in parts)

    matches: list[dict[str, Any]] = []
    for row in COMMAND_SURFACE_SCOPED_KERNEL_SURFACES:
        terms = [normalized_term(term) for term in row.get("match_terms", ())]
        matched_terms = [term for term in terms if term_matches(term)]
        if not matched_terms:
            continue
        evidence_paths = [str(path) for path in row.get("evidence_paths", ())]
        summary_command = str(row["summary_command"])
        match = {
            "surface_id": row["surface_id"],
            "surface": row["surface"],
            "matched_terms": matched_terms[:5],
            "canonical_command": summary_command,
            "compact_command": summary_command,
            "replacement_command": summary_command,
            "scoped_help_command": row["scoped_help_command"],
            "summary_command": summary_command,
            "full_fallback_command": row["full_fallback_command"],
            "output_profile": row["output_profile"],
            "reason": row["reason"],
            "evidence_paths": evidence_paths,
        }
        if full:
            match["evidence"] = [
                {
                    "path": path,
                    "status": "available" if (repo_root / path).exists() else "missing",
                }
                for path in evidence_paths
            ]
        matches.append(match)
    for row in COMMAND_SURFACE_SCOPED_COMPACT_COMMANDS:
        terms = [normalized_term(term) for term in row.get("match_terms", ())]
        required_terms = [
            normalized_term(term) for term in row.get("required_terms", ())
        ]
        if required_terms and not all(term and term in haystack for term in required_terms):
            continue
        matched_terms = [term for term in terms if term_matches(term)]
        if not matched_terms:
            continue
        evidence_paths = [str(path) for path in row.get("evidence_paths", ())]
        match: dict[str, Any] = {
            "surface_id": row["surface_id"],
            "matched_terms": matched_terms[:5],
            "canonical_command": row["canonical_command"],
            "compact_command": row["compact_command"],
            "replacement_command": row["replacement_command"],
            "output_profile": row["output_profile"],
            "reason": row["reason"],
            "evidence_paths": evidence_paths,
        }
        if required_terms:
            match["required_terms"] = required_terms
        if full:
            match["evidence"] = [
                {
                    "path": path,
                    "status": "available" if (repo_root / path).exists() else "missing",
                }
                for path in evidence_paths
            ]
        matches.append(match)
    aliases_by_action: dict[str, list[str]] = {action_id: [] for action_id in ACTION_CATALOG}
    for alias, action_id in ACTION_ALIASES.items():
        aliases_by_action.setdefault(action_id, []).append(alias)

    action_matches: list[tuple[int, str, dict[str, Any]]] = []
    for action_id, metadata in ACTION_CATALOG.items():
        terms = {
            normalized_term(action_id),
            normalized_term(action_id).replace("-", "_"),
            *(normalized_term(alias) for alias in aliases_by_action.get(action_id, [])),
        }
        matched_terms = sorted({term for term in terms if term_matches(term)}, key=len, reverse=True)
        if not matched_terms:
            continue
        quote_command = f"./repo-python tools/meta/control/action_quote.py --action {action_id}"
        match = {
            "surface_id": f"action_quote_{action_id}",
            "action_id": action_id,
            "matched_terms": matched_terms[:5],
            "canonical_command": quote_command,
            "compact_command": quote_command,
            "replacement_command": quote_command,
            "output_profile": "action_quote_handoff",
            "purpose": metadata["purpose"],
            "resource_class": metadata["resource_class"],
            "authority_level": metadata["authority_level"],
            "owner_surface": metadata["owner_surface"],
            "reason": (
                "Scope names an existing action_quote handoff; use the quote action "
                "before falling back to artifact discovery or raw command search."
            ),
            "evidence_paths": [],
        }
        if full:
            match["quote_sources"] = list(metadata.get("quote_sources", ()))
            match["aliases"] = sorted(aliases_by_action.get(action_id, []))
        action_matches.append((len(matched_terms[0]), action_id, match))
    for _, _, match in sorted(action_matches, key=lambda row: (-row[0], row[1])):
        matches.append(match)
    has_compact_command = any(
        _as_mapping(match).get("output_profile") != "action_quote_handoff"
        for match in matches
    )
    kernel_surface_matches = [
        _as_mapping(match)
        for match in matches
        if _as_mapping(match).get("output_profile") == "summary_first_kernel_diagnostic"
    ]
    has_action_handoff = any(
        _as_mapping(match).get("output_profile") == "action_quote_handoff"
        for match in matches
    )
    status = "scope_unmatched"
    if kernel_surface_matches:
        status = "scoped_kernel_surface"
    elif has_compact_command:
        status = "matched_compact_command"
    elif has_action_handoff:
        status = "matched_action_handoff"
    payload: dict[str, Any] = {
        "status": status,
        "scope_paths": scopes,
        "match_count": len(matches),
        "matches": matches,
        "privacy": {
            "stores_file_contents": False,
            "stores_stdout_stderr_bodies": False,
            "scope_matching": "curated_command_metadata_only_no_content_walk",
        },
        "fallback": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action artifact_discovery_inventory --scope <term-or-root>"
        ),
    }
    if kernel_surface_matches:
        primary_kernel_surface = kernel_surface_matches[0]
        payload.update(
            {
                "surface": primary_kernel_surface.get("surface"),
                "scoped_help_command": primary_kernel_surface.get("scoped_help_command"),
                "summary_command": primary_kernel_surface.get("summary_command"),
                "full_fallback_command": primary_kernel_surface.get("full_fallback_command"),
            }
        )
    return payload


def _quote_command_surface_inventory(
    repo_root: Path,
    scope_paths: Sequence[str] = (),
    *,
    full: bool = False,
) -> dict[str, Any]:
    profile = "full_metadata" if full else "compact_metadata"
    limit = COMMAND_SURFACE_INVENTORY_FULL_LIMIT if full else COMMAND_SURFACE_INVENTORY_DEFAULT_LIMIT
    rows, summary = _iter_command_surface_inventory(
        repo_root,
        limit=limit,
    )
    admission_coverage = _admission_consumer_coverage(repo_root)
    quote_command = "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory"
    full_quote_command = f"{quote_command} --full"
    fallback_path_metadata_command = (
        "rg --files tools/meta codex/hologram/process codex/standards codex/doctrine "
        "state/performance state/work_ledger state/command_runs state/agent_telemetry/process "
        "system/server/tests system/lib .agents docs repo-python repo-pytest "
        f"| rg '{COMMAND_SURFACE_INVENTORY_PATTERN}' | head -120"
    )
    avoid_command_shapes = [
        "rg -n '<command telemetry terms>' .",
        (
            "rg -n '<command telemetry terms>' system tools codex .agents docs state "
            "repo-python repo-pytest"
        ),
    ]
    inventory: dict[str, Any] = {
        "privacy": {
            "stores_file_contents": False,
            "stores_stdout_stderr_bodies": False,
            "emits": "path, size_bytes, and match metadata only",
        },
        "summary": summary,
    }
    if full:
        inventory.update(
            {
                "rows": rows,
                "roots": list(COMMAND_SURFACE_INVENTORY_ROOTS),
                "pattern": COMMAND_SURFACE_INVENTORY_PATTERN,
                "full_path_metadata_command": fallback_path_metadata_command,
            }
        )
    else:
        roots_preview_limit = 4
        rows_preview_limit = 5
        row_preview_count = len(rows[:rows_preview_limit])
        source_emitted_count = int(summary.get("emitted_count") or len(rows))
        summary.update(
            {
                "source_emitted_count": source_emitted_count,
                "emitted_count": row_preview_count,
                "payload_row_preview_count": row_preview_count,
                "payload_rows_omitted": max(0, source_emitted_count - row_preview_count),
            }
        )
        inventory.update(
            {
                "rows_preview": [
                    {
                        "path": row.get("path"),
                        "status": row.get("status"),
                        "size_bytes": row.get("size_bytes"),
                    }
                    for row in rows[:rows_preview_limit]
                ],
                "rows_omitted": max(0, source_emitted_count - row_preview_count),
                "roots_preview": list(COMMAND_SURFACE_INVENTORY_ROOTS[:roots_preview_limit]),
                "roots_omitted": max(0, len(COMMAND_SURFACE_INVENTORY_ROOTS) - roots_preview_limit),
                "pattern_ref": "system/lib/action_quote.py::COMMAND_SURFACE_INVENTORY_PATTERN",
                "full_profile_command": full_quote_command,
                "omission_receipt": {
                    "omitted": [
                        "full roots list",
                        "raw regex pattern",
                        "raw fallback rg command",
                        "overflow inventory rows",
                    ],
                    "reason": "command_surface_inventory is a first-contact selector; full evidence belongs behind --full.",
                    "drilldown": full_quote_command,
                },
            }
        )
    handoffs = _command_surface_action_handoffs(
        repo_root,
        admission_coverage=admission_coverage,
        preview_ids=COMMAND_SURFACE_ACTION_HANDOFF_FULL_IDS
        if full
        else COMMAND_SURFACE_ACTION_HANDOFF_PREVIEW_IDS,
        profile="full_alias_preview" if full else "summary_only_action_id_preview",
        include_rows=full,
    )
    scope_resolution = _command_surface_scope_resolution(repo_root, scope_paths, full=full)
    scoped_matches = _as_list(_as_mapping(scope_resolution).get("matches")) if scope_resolution else []
    primary_scope_match = _as_mapping(scoped_matches[0]) if scoped_matches else {}
    primary_scope_profile = str(primary_scope_match.get("output_profile") or "")
    scoped_action_handoff = primary_scope_profile == "action_quote_handoff"
    scoped_kernel_surface = primary_scope_profile == "summary_first_kernel_diagnostic"
    do_not_touch_rows = [
        {
            "lane": "raw_telemetry_body_grep",
            "reason": (
                "Generated process spans, raw outputs, and tool-result files can contain megabytes "
                "of command bodies; inventory must use path metadata first."
            ),
            "replacement": quote_command,
        },
        {
            "lane": "repo_root_content_grep_for_command_surface",
            "reason": (
                "Repo-root content grep can traverse oversized Obsidian, generated state, and "
                "telemetry bodies; use curated path metadata or route catalogs first."
            ),
            "replacement": fallback_path_metadata_command,
        },
    ]
    if not full:
        do_not_touch_rows = [
            {
                "lane": "raw_telemetry_body_grep",
                "reason_class": "raw_command_body_risk",
                "replacement": quote_command,
            },
            {
                "lane": "repo_root_content_grep_for_command_surface",
                "reason_class": "oversized_generated_state_and_telemetry_risk",
                "replacement_ref": "full_profile_command::fallback_path_metadata_command",
            },
        ]
    fallback_handle = {
        "status": "available_in_full_profile",
        "command_ref": "full_profile_command::fallback_path_metadata_command",
        "why_omitted": (
            "The literal rg fallback repeats long curated roots; default first-contact keeps the handle."
        ),
    }
    return {
        "output_profile": profile,
        "current_status": (
            "scoped_action_handoff_available"
            if scoped_action_handoff
            else "scoped_kernel_surface_available"
            if scoped_kernel_surface
            else "scoped_compact_command_available"
            if primary_scope_match
            else "inventory_available"
        ),
        "recommendation": (
            "use_action_quote_handoff"
            if scoped_action_handoff
            else "use_scoped_kernel_summary_route"
            if scoped_kernel_surface
            else "use_scoped_compact_command"
            if primary_scope_match
            else "use_bounded_inventory_not_raw_grep"
        ),
        "freshness": "live_path_metadata",
        "authority_level": "path_metadata_read_model",
        "drilldown_command": quote_command,
        "suggested_command": primary_scope_match.get("compact_command") or quote_command,
        "replacement_command": primary_scope_match.get("replacement_command") or quote_command,
        "full_profile_command": full_quote_command,
        **(
            {"safe_fallback_path_metadata_command": fallback_path_metadata_command}
            if full
            else {"safe_fallback_path_metadata_command_ref": fallback_handle}
        ),
        **({"fallback_path_metadata_command": fallback_path_metadata_command} if full else {}),
        "avoid_command_shape": avoid_command_shapes[-1],
        "avoid_command_shapes": avoid_command_shapes,
        "do_not_touch": do_not_touch_rows,
        "inventory": inventory,
        "action_handoffs": handoffs,
        "admission_consumer_coverage": _compact_admission_consumer_coverage(admission_coverage),
        **({"scope_resolution": scope_resolution} if scope_resolution else {}),
        "output_economy": {
            "default_profile": "compact_metadata",
            "current_profile": profile,
            "inventory_rows_default_limit": COMMAND_SURFACE_INVENTORY_DEFAULT_LIMIT,
            "inventory_rows_full_limit": COMMAND_SURFACE_INVENTORY_FULL_LIMIT,
            "full_action_catalog_command": "./repo-python tools/meta/control/action_quote.py --catalog",
            "full_inventory_command": full_quote_command,
            "full_path_metadata_command_in_full_profile": True,
            "safe_fallback_path_metadata_command_in_full_profile": True,
            "full_coverage_rows_default_omitted": True,
        },
    }


def _quote_git_diff_review_context(repo_root: Path) -> dict[str, Any]:
    owner_command = (
        "./repo-python tools/meta/control/git_state_snapshot.py "
        "--diff-review --path-limit 40 --recent-limit 3 "
        "--skip-git-metadata-write-probe --compact"
    )
    return {
        "current_status": "owner_surface_available"
        if (repo_root / "tools/meta/control/git_state_snapshot.py").is_file()
        else "owner_surface_missing",
        "recommendation": "use_diff_review_context_before_raw_global_patch",
        "freshness": "live_on_invocation",
        "authority_level": "path_and_diff_metadata_read_model",
        "drilldown_command": owner_command,
        "suggested_command": owner_command,
        "replacement_command": owner_command,
        "fallback_commands": [
            "./repo-git status --short",
            "./repo-git diff --name-status",
            "./repo-git diff --stat",
            "./repo-git diff --numstat",
        ],
        "raw_patch_allowed_when": [
            "specific path selected",
            "semantic hunk review required",
            "scoped commit preflight asks for patch proof",
            "safety or authority review requires the patch body",
        ],
        "do_not_touch": [
            {
                "lane": "raw_global_diff_first_contact",
                "reason": "A global raw patch can consume active context before path, risk, and ownership are selected.",
                "replacement": owner_command,
            },
            {
                "lane": "diff_plus_full_file_double_spend",
                "reason": "Raw diff hunks and full file reads for the same path duplicate semantic code in active context.",
                "replacement": "./repo-git diff -- <path> only after the ladder selects that path",
            },
        ],
        "output_economy": {
            "routine_first_route": owner_command,
            "full_body_route": "./repo-git diff -- <path>",
            "privacy": "path_and_diff_metadata_only_no_raw_global_patch_body",
        },
        "source": {
            "owner_surface": "system/lib/git_state_snapshot.py",
            "standard": "codex/standards/std_command_output_projection.json::diff_review_context_contract",
        },
    }


def _quote_git_state_snapshot_status(repo_root: Path) -> dict[str, Any]:
    owner_command = (
        "./repo-python tools/meta/control/git_state_snapshot.py "
        "--path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact"
    )
    diff_review_command = (
        "./repo-python tools/meta/control/git_state_snapshot.py "
        "--diff-review --path-limit 40 --recent-limit 3 "
        "--skip-git-metadata-write-probe --compact"
    )
    return {
        "current_status": "owner_surface_available"
        if (repo_root / "tools/meta/control/git_state_snapshot.py").is_file()
        else "owner_surface_missing",
        "recommendation": "use_compact_git_state_snapshot_before_shell_chains",
        "freshness": "live_on_invocation",
        "authority_level": "path_and_git_metadata_read_model",
        "drilldown_command": owner_command,
        "suggested_command": owner_command,
        "replacement_command": owner_command,
        "diff_review_command": diff_review_command,
        "fallback_commands": [
            "./repo-git status --short",
            "./repo-git log --oneline -n 3",
            "./repo-git diff --name-status",
        ],
        "do_not_touch": [
            {
                "lane": "git_log_status_shell_chain",
                "reason": (
                    "Chained git log/status/diff snippets repeat branch, dirty-path, "
                    "lock, and HEAD-CAS metadata across turns."
                ),
                "replacement": owner_command,
            },
            {
                "lane": "raw_global_diff_first_contact",
                "reason": "Use the diff-review lens only when patch metadata is needed.",
                "replacement": diff_review_command,
            },
        ],
        "output_economy": {
            "routine_first_route": owner_command,
            "patch_review_route": diff_review_command,
            "full_body_route": "./repo-git diff -- <path>",
            "privacy": "path_and_git_metadata_only_no_raw_diff_body",
        },
        "source": {
            "owner_surface": "system/lib/git_state_snapshot.py",
            "process_hint": "replace_git_shell_chain_with_state_snapshot",
        },
    }


def _bash_other_scope_text(scope_paths: Sequence[str]) -> str:
    return " ".join(_scope_paths(scope_paths)).strip()


def _quote_destructive_shell_guard(
    repo_root: Path,
    scope_paths: Sequence[str] = (),
) -> dict[str, Any]:
    scope_text = _bash_other_scope_text(scope_paths)
    lowered = scope_text.lower()
    public_site_scope = "microcosm-substrate/receipts/public_site" in lowered or (
        "public_site" in lowered and "microcosm-substrate" in lowered
    )
    owner_card_command = (
        "./repo-python kernel.py --option-surface paper_modules --band card "
        "--ids tools_meta_dissemination_index"
    )
    public_site_check_command = (
        "./repo-python tools/meta/dissemination/build_microcosm_public_site.py "
        "--check --validate"
    )
    fallback_command = STORAGE_DOCTOR_STATUS_COMMAND
    suggested_command = owner_card_command if public_site_scope else fallback_command
    owner_check_command = public_site_check_command if public_site_scope else fallback_command
    return {
        "current_status": "destructive_shell_scope_detected",
        "recommendation": (
            "route_public_site_delete_through_owner_card"
            if public_site_scope
            else "route_destructive_shell_through_owner_status"
        ),
        "freshness": "live_scope_classification",
        "authority_level": "non_destructive_owner_route",
        "drilldown_command": suggested_command,
        "suggested_command": suggested_command,
        "replacement_command": suggested_command,
        "owner_check_command": owner_check_command,
        "public_site_owner_card_command": owner_card_command,
        "public_site_check_command": public_site_check_command,
        "storage_status_command": fallback_command,
        "raw_command_scope": scope_text,
        "destructive_command_class": "rm_rf_delete",
        "do_not_touch": [
            {
                "lane": "raw_rm_rf_first_contact",
                "reason": (
                    "Raw recursive deletion can spend minutes walking generated trees and "
                    "bypasses owner freshness checks."
                ),
                "avoid": scope_text or "rm -rf <path>",
                "replacement": suggested_command,
            },
            {
                "lane": "raw_delete_public_site_receipts",
                "reason": (
                    "Public-site receipt trees are governed by the dissemination builder; "
                    "check the owner card/validator before deleting generated output."
                ),
                "avoid": "rm -rf microcosm-substrate/receipts/public_site",
                "replacement": owner_card_command,
            },
        ],
        "recommended_sequence": [
            {
                "action": "open_owner_card",
                "command": suggested_command,
            },
            {
                "action": "run_owner_check_if_public_site_scope",
                "command": owner_check_command,
            },
            {
                "action": "use_storage_doctor_for_generic_cleanup",
                "command": fallback_command,
            },
        ],
        "scope_classification": {
            "public_site_scope": public_site_scope,
            "destructive_terms_detected": bool(scope_text),
        },
        "source": {
            "public_site_owner": "tools/meta/dissemination/build_microcosm_public_site.py",
            "storage_owner": "tools/meta/storage_doctor.py",
            "process_hint_source": "codex/hologram/process/summary.json::bash_other",
            "owner_surface_exists": (
                repo_root / "tools/meta/dissemination/build_microcosm_public_site.py"
            ).is_file(),
        },
        "output_economy": {
            "mutates_files": False,
            "prevents_raw_recursive_delete": True,
            "owner_status_first": True,
        },
    }


def _bash_other_scope_route(scope_paths: Sequence[str]) -> tuple[str, str]:
    scope_text = _bash_other_scope_text(scope_paths)
    lowered = scope_text.lower()
    destructive_delete = bool(
        re.search(r"(?<![A-Za-z0-9_-])rm\s+-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*(?![A-Za-z0-9_-])", lowered)
        or re.search(r"(?<![A-Za-z0-9_-])rm\s+-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*(?![A-Za-z0-9_-])", lowered)
    )
    raw_process_signal = bool(
        re.match(
            r"^\s*(?:sudo\s+)?kill(?:\s+-[A-Za-z0-9]+|\s+-s\s+[A-Za-z0-9_+-]+)?"
            r"(?:\s+--)?(?:\s+\d+)+\s*$",
            lowered,
        )
    )
    git_terms = {
        "git",
        "status",
        "diff",
        "log",
        "rev-parse",
        "show",
        "branch",
        "commit",
        "cached",
        "staged",
    }
    search_terms = {
        "rg",
        "grep",
        "find",
        "search",
        "recursive",
        "files",
        "path",
        "artifact",
        "inventory",
    }
    explicit_search_terms = search_terms - {"inventory"}
    process_terms = {
        "--process-audit",
        "--process-summary",
        "agent_trace",
        "agent-trace",
        "agent_trace/events.jsonl",
        "codex/hologram/process",
        "codex/hologram/process/audit.json",
        "codex/hologram/process/summary.json",
        "process-audit",
        "process-summary",
        "process_summary",
        "process trace",
        "process_trace",
        "taskoutput",
        "task output",
        "tool-result",
        "tool_result",
        "state/observability/agent_trace",
        "state/observability/agent_trace/events.jsonl",
        "tmp",
        "poll",
        "background",
        "tail",
        "head",
    }
    document_terms = {
        "cat",
        "sed",
        "read",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".txt",
    }
    command_surface_terms = {
        "action quote",
        "action-quote",
        "action_quote",
        "python -c",
        "python3 -c",
        "inline python",
        "jq",
        "command",
        "command telemetry",
        "command-surface",
        "command_surface",
        "command-surface-inventory",
        "command_surface_inventory",
        "surface",
        "module",
    }
    command_surface_scoped_terms: set[str] = set()
    for row in (*COMMAND_SURFACE_SCOPED_KERNEL_SURFACES, *COMMAND_SURFACE_SCOPED_COMPACT_COMMANDS):
        for term in row.get("match_terms", ()):
            command_surface_scoped_terms.add(str(term).lower())

    def has_any(terms: set[str]) -> bool:
        for term in terms:
            if " " in term:
                if term in lowered:
                    return True
                continue
            if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])", lowered):
                return True
        return False

    if destructive_delete:
        return "destructive_shell_guard", "destructive_shell_delete_scope_terms"
    if raw_process_signal:
        return "session_yield_request", "raw_process_signal_scope_terms"
    if has_any(git_terms):
        return "git_state_snapshot_status", "git_scope_terms"
    if (
        ("task_ledger_apply.py" in lowered or "task_ledger_apply" in lowered)
        and re.search(r"(?<![A-Za-z0-9_-])rebuild(?![A-Za-z0-9_-])", lowered)
    ):
        return "task_ledger_rebuild_status", "task_ledger_rebuild_scope_terms"
    if has_any(process_terms):
        return "process_summary_status", "process_or_tool_result_scope_terms"
    if has_any(explicit_search_terms):
        return "artifact_discovery_inventory", "search_or_artifact_scope_terms"
    if has_any(command_surface_terms) or has_any(command_surface_scoped_terms):
        return "command_surface_inventory", "command_surface_scope_terms"
    if has_any(search_terms):
        return "artifact_discovery_inventory", "search_or_artifact_scope_terms"
    if has_any(document_terms):
        return "document_read_economy", "document_read_scope_terms"
    if scope_text:
        return "artifact_discovery_inventory", "nonempty_scope_default_artifact_inventory"
    return "command_surface_inventory", "empty_scope_fallback_command_surface_inventory"


def _bash_other_artifact_scope_paths(repo_root: Path, scope_paths: Sequence[str]) -> Sequence[str]:
    scope_text = _bash_other_scope_text(scope_paths)
    if not scope_text:
        return scope_paths
    raw_tokens = [
        token.strip().strip("'\"`;,()")
        for token in re.split(r"\s+", scope_text)
        if token.strip().strip("'\"`;,()")
    ]
    command_or_flag_terms = {
        "rg",
        "grep",
        "find",
        "fd",
        "ack",
        "-n",
        "-name",
        "-iname",
        "--line-number",
        "-maxdepth",
        "-mindepth",
        "-o",
        "-or",
        "-path",
        "-type",
        "-r",
        "-R",
        "-i",
        "-l",
        "--files",
        "--hidden",
    }
    find_noise_flags_with_values = {
        "-maxdepth",
        "-mindepth",
        "-type",
    }
    selected_roots = set(_artifact_discovery_existing_scope_roots(repo_root, raw_tokens))
    rare_tokens: list[str] = []
    skip_next_value = False
    for token in raw_tokens:
        normalized = token.lower().strip("/")
        if skip_next_value:
            skip_next_value = False
            continue
        if normalized in find_noise_flags_with_values:
            skip_next_value = True
            continue
        if "*" in normalized:
            normalized = "_".join(part for part in normalized.split("*") if part)
        normalized = normalized.strip("/")
        if not normalized or normalized in command_or_flag_terms:
            continue
        if not re.search(r"[a-z0-9]", normalized):
            continue
        if normalized.isdigit():
            continue
        if normalized in ARTIFACT_DISCOVERY_COMMON_SCOPE_TERMS:
            continue
        if token.strip("/").replace(os.sep, "/") in selected_roots:
            continue
        if token.startswith("-"):
            continue
        if normalized not in rare_tokens:
            rare_tokens.append(normalized)
    if not rare_tokens:
        return scope_paths
    return [" ".join(rare_tokens[:3])]


HOST_FILESYSTEM_FIND_ALIASES = {
    "bash_find",
    "find",
    "raw_find",
}
GIT_OBJECT_STORE_SCOPE_MARKERS = (
    ".git/objects",
    "git/objects",
    "git object",
    "git objects",
    "git-object",
    "git-objects",
    "loose object",
    "loose objects",
    "tmp_obj",
)
HOST_FILESYSTEM_CLOUD_DRIVE_TERMS = (
    "google drive",
    "googledrive",
    "google-drive",
    "icloud drive",
    "icloud-drive",
    "onedrive",
    "one drive",
    "dropbox",
)
HOST_FILESYSTEM_SCOPE_MARKERS = (
    "host-filesystem",
    "host_filesystem",
    "host filesystem",
    "host.filesystem",
    "host/filesystem",
    "host path",
    "host root",
)
HOST_FILESYSTEM_FIND_SKIP_TERMS = {
    "find",
    "filesystem",
    "host",
    "host-filesystem",
    "host_filesystem",
    "host.filesystem",
    "host/filesystem",
    "users",
    "user",
    "willcook",
    "maxdepth",
    "depth",
    "type",
    "iname",
    "name",
    "print",
    "head",
    "tail",
    "o",
    "or",
    "and",
    "d",
    "f",
    "4",
    "3",
    "2",
    "1",
}
HOST_FILESYSTEM_SHELL_TOKEN_CHARS = frozenset("|&;<>")


def _scope_mentions_git_object_store(scope_paths: Sequence[str]) -> bool:
    scope_text = _bash_other_scope_text(scope_paths).lower()
    if not scope_text:
        return False
    return any(marker in scope_text for marker in GIT_OBJECT_STORE_SCOPE_MARKERS)


def _host_filesystem_find_scope_resolution(
    repo_root: Path,
    scope_paths: Sequence[str],
) -> dict[str, Any] | None:
    scope_text = _bash_other_scope_text(scope_paths)
    if not scope_text:
        return None
    lowered = scope_text.lower()
    cloud_terms = [
        term for term in HOST_FILESYSTEM_CLOUD_DRIVE_TERMS if term in lowered
    ]
    scope_markers = [
        marker for marker in HOST_FILESYSTEM_SCOPE_MARKERS if marker in lowered
    ]
    tokens = [
        token.strip().strip("'\"`;,()")
        for token in re.split(r"\s+", scope_text)
        if token.strip().strip("'\"`;,()")
    ]
    home = Path.home()
    repo = repo_root.resolve()
    host_roots: list[str] = []
    for token in tokens:
        expanded = token
        if token == "~":
            expanded = str(home)
        elif token.startswith("~/"):
            expanded = str(home / token[2:])
        elif token.startswith("$HOME/"):
            expanded = str(home / token[len("$HOME/") :])
        elif token == "$HOME":
            expanded = str(home)
        if not expanded.startswith("/"):
            continue
        path = Path(expanded).resolve()
        try:
            path.relative_to(repo)
            continue
        except ValueError:
            pass
        root = str(path)
        if root not in host_roots:
            host_roots.append(root)
    if not host_roots and not cloud_terms and not scope_markers:
        return None
    rare_terms: list[str] = []
    for token in tokens:
        cleaned = token.strip("*[]{}").replace("\\ ", " ")
        lowered_token = cleaned.lower().strip("-/")
        if not lowered_token or lowered_token in HOST_FILESYSTEM_FIND_SKIP_TERMS:
            continue
        if lowered_token.isdigit():
            continue
        if any(char in cleaned for char in HOST_FILESYSTEM_SHELL_TOKEN_CHARS):
            continue
        if not any(char.isalnum() for char in cleaned):
            continue
        if cleaned.startswith("-") or cleaned.startswith("/"):
            continue
        if lowered_token in {"google", "drive"} and any(
            term in cloud_terms for term in {"google drive", "googledrive", "google-drive"}
        ):
            continue
        if cleaned not in rare_terms:
            rare_terms.append(cleaned)
    return {
        "status": "host_filesystem_scope",
        "scope_paths": list(_scope_paths(scope_paths)),
        "host_roots": host_roots[:4],
        "host_roots_omitted": max(0, len(host_roots) - 4),
        "matched_cloud_terms": cloud_terms,
        "matched_scope_markers": scope_markers,
        "rare_terms": rare_terms[:5],
        "privacy": {
            "stores_file_contents": False,
            "stores_stdout_stderr_bodies": False,
            "scope_matching": "scope_text_only_no_host_walk",
        },
    }


def _host_filesystem_find_predicate(terms: Sequence[str]) -> str:
    predicates = [f"-iname {shlex.quote(f'*{term}*')}" for term in terms[:4]]
    if not predicates:
        predicates = ["-iname '*'"]
    if len(predicates) == 1:
        return predicates[0]
    return r"\( " + " -o ".join(predicates) + r" \)"


def _quote_git_object_store_status(
    repo_root: Path,
    scope_paths: Sequence[str],
) -> dict[str, Any]:
    scope_text = _bash_other_scope_text(scope_paths).lower()
    bounded_size_fallback = (
        "objects_dir=$(git rev-parse --git-path objects) && "
        "find \"$objects_dir\" -type f -path '*/??/*' "
        "-exec stat -f '%z %N' {} + | sort -nr | head -40"
    )
    return {
        "freshness": "live_git_object_store_status_on_invocation",
        "drilldown_command": (
            "./repo-python tools/meta/control/git_gc_maintenance.py --tmp-object-status"
        ),
        "do_not_touch": [
            {
                "lane": "raw_git_object_find_scan",
                "reason": (
                    "Raw find/stat/sort scans over .git/objects pay object-store traversal "
                    "cost before checking whether the Git maintenance owner already has the needed status."
                ),
                "avoid": (
                    "find .git/objects -type f -path '.git/objects/??/*' "
                    "-exec stat -f '%z %N' {} + | sort -nr | head -40"
                ),
                "replacement": (
                    "./repo-python tools/meta/control/git_gc_maintenance.py --tmp-object-status"
                ),
            },
            {
                "lane": "generic_artifact_inventory_for_git_objects",
                "reason": (
                    ".git/objects is a Git maintenance surface, not a repo artifact "
                    "inventory surface; generic artifact inventory prunes it by design."
                ),
                "replacement": "./repo-python tools/meta/control/git_gc_maintenance.py --check",
            },
        ],
        "current_status": "git_object_store_scope_detected",
        "recommendation": "use_git_maintenance_status_before_raw_object_find",
        "suggested_command": (
            "./repo-python tools/meta/control/git_gc_maintenance.py --tmp-object-status"
        ),
        "replacement_command": (
            "./repo-python tools/meta/control/git_gc_maintenance.py --tmp-object-status"
        ),
        "status_command": GIT_MAINTENANCE_CHECK_COMMAND,
        "repair_command": GIT_MAINTENANCE_REPAIR_COMMAND,
        "prune_candidate_status_command": (
            "./repo-python tools/meta/control/git_gc_maintenance.py --prune-candidate-status"
        ),
        "object_dir_command": "git rev-parse --git-path objects",
        "bounded_size_fallback_command": bounded_size_fallback,
        "scope_resolution": {
            "status": "git_object_store_scope",
            "scope_paths": list(_scope_paths(scope_paths)),
            "matched_markers": [
                marker
                for marker in GIT_OBJECT_STORE_SCOPE_MARKERS
                if marker in scope_text
            ],
            "privacy": {
                "stores_file_contents": False,
                "stores_stdout_stderr_bodies": False,
                "scope_matching": "scope_text_only_no_git_object_walk",
            },
        },
        "output_economy": {
            "default_profile": "git_maintenance_status_first",
            "emits_git_object_contents": False,
            "avoids_repo_artifact_inventory": True,
            "avoids_raw_object_store_walk": True,
            "bounded_size_fallback_is_last_resort": True,
        },
        "source": {
            "privacy": "scope_metadata_only_no_git_object_walk_no_stdout_stderr_bodies",
            "process_hint": "replace_git_object_find_scan_with_git_gc_maintenance_status",
            "repo_root": str(repo_root),
        },
    }


def _quote_host_filesystem_discovery(
    repo_root: Path,
    scope_paths: Sequence[str],
) -> dict[str, Any]:
    resolution = _host_filesystem_find_scope_resolution(repo_root, scope_paths) or {
        "status": "host_filesystem_scope",
        "scope_paths": list(_scope_paths(scope_paths)),
        "host_roots": [],
        "matched_cloud_terms": [],
        "rare_terms": [],
        "privacy": {
            "stores_file_contents": False,
            "stores_stdout_stderr_bodies": False,
            "scope_matching": "scope_text_only_no_host_walk",
        },
    }
    cloud_terms = _as_list(resolution.get("matched_cloud_terms"))
    rare_terms = [str(term) for term in _as_list(resolution.get("rare_terms"))]
    if any(term in {"google drive", "googledrive", "google-drive"} for term in cloud_terms):
        spotlight_query = (
            "kMDItemFSName == '*Google Drive*'cdw || "
            "kMDItemFSName == '*GoogleDrive*'cdw || "
            "kMDItemFSName == '*googledrive*'cdw"
        )
        suggested = f"mdfind -onlyin \"$HOME\" {shlex.quote(spotlight_query)} | head -20"
        bounded_find = (
            "find \"$HOME\" -maxdepth 3 "
            r"\( -iname '*Google Drive*' -o -iname '*GoogleDrive*' -o "
            r"-iname '*googledrive*' \) -print -quit"
        )
    else:
        terms = rare_terms or ["<name-fragment>"]
        predicate = _host_filesystem_find_predicate(terms)
        bounded_find = f"find \"$HOME\" -maxdepth 3 {predicate} -print -quit"
        suggested = bounded_find
    return {
        "freshness": "live_scope_classification",
        "drilldown_command": suggested,
        "do_not_touch": [
            {
                "lane": "broad_home_find_scan",
                "reason": "Broad host find scans over /Users or $HOME are slow and usually only need the first matching directory.",
                "replacement": suggested,
            },
            {
                "lane": "repo_artifact_inventory_for_host_path",
                "reason": "Host filesystem targets such as cloud-drive folders are outside the repo artifact inventory authority.",
                "replacement": suggested,
            },
        ],
        "current_status": "host_filesystem_scope_detected",
        "recommendation": "use_spotlight_or_single_result_bounded_find",
        "suggested_command": suggested,
        "replacement_command": suggested,
        "bounded_find_fallback_command": bounded_find,
        "scope_resolution": resolution,
        "output_economy": {
            "default_profile": "host_metadata_command_shape_only",
            "emits_host_file_contents": False,
            "avoids_repo_artifact_inventory": True,
            "fallback_prints_first_match_only": True,
        },
        "source": {
            "privacy": "scope_metadata_only_no_host_walk_no_stdout_stderr_bodies",
            "process_hint": "replace_broad_host_find_scan_with_spotlight_or_single_result_find",
        },
    }


def _quote_bash_other_economy(
    repo_root: Path,
    scope_paths: Sequence[str] = (),
    *,
    full: bool = False,
) -> dict[str, Any]:
    routed_action_id, reason = _bash_other_scope_route(scope_paths)
    if routed_action_id == "git_state_snapshot_status":
        detail = _quote_git_state_snapshot_status(repo_root)
    elif routed_action_id == "task_ledger_rebuild_status":
        detail = _quote_task_ledger_rebuild_status(repo_root)
    elif routed_action_id == "process_summary_status":
        detail = _quote_process_summary_status(repo_root, scope_paths)
    elif routed_action_id == "destructive_shell_guard":
        detail = _quote_destructive_shell_guard(repo_root, scope_paths)
    elif routed_action_id == "session_yield_request":
        detail = _quote_session_yield_request(repo_root)
        raw_scope = _bash_other_scope_text(scope_paths)
        detail = {
            **detail,
            "raw_command_scope": raw_scope,
            "process_control_class": "raw_process_signal",
            "do_not_touch": [
                {
                    "lane": "raw_kill_first_contact",
                    "reason": (
                        "Raw process signals can terminate another owner session or helper "
                        "without a visible yield/result receipt."
                    ),
                    "avoid": raw_scope or "kill <pid>",
                    "replacement": detail.get("suggested_command"),
                },
                {
                    "lane": "unknown_owner_process_signal",
                    "reason": (
                        "Process pressure is coordinated through Work Ledger yield and "
                        "resident-relief receipts before any manual signal is considered."
                    ),
                    "replacement": detail.get("suggested_command"),
                },
            ],
        }
    elif routed_action_id == "artifact_discovery_inventory":
        scope_paths = _bash_other_artifact_scope_paths(repo_root, scope_paths)
        detail = _quote_artifact_discovery_inventory(repo_root, scope_paths, full=full)
    elif routed_action_id == "document_read_economy":
        detail = _quote_document_read_economy(repo_root, scope_paths)
    else:
        detail = _quote_command_surface_inventory(repo_root, scope_paths, full=full)
    routed_quote_command = (
        f"./repo-python tools/meta/control/action_quote.py --action {routed_action_id}"
    )
    if scope_paths:
        routed_quote_command += "".join(
            f" --scope {shlex.quote(scope)}" for scope in _scope_paths(scope_paths)
        )
    return {
        **detail,
        "current_status": f"routed_to_{routed_action_id}",
        "recommendation": "use_scope_classified_bash_owner_route",
        "freshness": detail.get("freshness") or "live_scope_classification",
        "authority_level": detail.get("authority_level") or "scope_classified_owner_route",
        "routed_action_id": routed_action_id,
        "route_reason": reason,
        "routed_quote_command": routed_quote_command,
        "scope_classification": {
            "status": "classified",
            "route_reason": reason,
            "scope_paths": _scope_paths(scope_paths),
            "fallback_action_id": "command_surface_inventory",
            "privacy": {
                "stores_file_contents": False,
                "stores_stdout_stderr_bodies": False,
            },
        },
        "do_not_touch": [
            {
                "lane": "unclassified_bash_output_without_owner_quote",
                "reason": (
                    "Trace data shows output-heavy bash often has a cheaper owner route; "
                    "classify the scope through bash_other before opening raw bodies."
                ),
                "replacement": (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action bash_other --scope <path-or-owner>"
                ),
            },
            *_as_list(detail.get("do_not_touch")),
        ],
        "output_economy": {
            **_as_mapping(detail.get("output_economy")),
            "scope_classified_bash_other": True,
            "routed_action_id": routed_action_id,
        },
    }


def _artifact_discovery_existing_scope_roots(repo_root: Path, scope_paths: Sequence[str]) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for raw in _scope_paths(scope_paths):
        if not raw or raw.startswith("-"):
            continue
        candidate = (repo_root / raw).resolve()
        try:
            candidate.relative_to(repo_root)
        except ValueError:
            continue
        if not candidate.exists():
            continue
        normalized = raw.strip().strip("/").replace(os.sep, "/")
        if normalized and normalized not in seen:
            selected.append(normalized)
            seen.add(normalized)
    return selected


def _artifact_discovery_path_scope_only(repo_root: Path, scope_paths: Sequence[str]) -> bool:
    scopes = _scope_paths(scope_paths)
    if not scopes:
        return False
    selected = _artifact_discovery_existing_scope_roots(repo_root, scopes)
    return len(selected) == len(scopes)


def _artifact_discovery_leaf_terms(raw: str) -> list[str]:
    leaf = Path(raw.strip().strip("/")).name.strip().lower()
    if not leaf:
        return []
    terms = [leaf]
    stem = Path(leaf).stem.strip().lower()
    if stem and stem != leaf:
        terms.append(stem)
    return terms


def _artifact_discovery_root_path(repo_root: Path, root_text: str) -> Path:
    root = Path(root_text)
    return root if root.is_absolute() else repo_root / root


def _artifact_discovery_rel_text(repo_root: Path, path: Path) -> str | None:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        pass
    workspace_root = repo_root.parent
    try:
        path.relative_to(workspace_root)
    except ValueError:
        return None
    return os.path.relpath(path, repo_root).replace(os.sep, "/")


def _artifact_discovery_terms(repo_root: Path, scope_paths: Sequence[str]) -> list[str]:
    selected_roots = set(_artifact_discovery_existing_scope_roots(repo_root, scope_paths))
    terms: list[str] = []
    for raw in _scope_paths(scope_paths):
        if raw.strip().strip("/").replace(os.sep, "/") in selected_roots:
            terms.extend(_artifact_discovery_leaf_terms(raw))
            continue
        for term in re.split(r"[^A-Za-z0-9_.-]+", raw):
            cleaned = term.strip().lower()
            if cleaned:
                terms.extend(_artifact_discovery_term_variants(cleaned))
    return sorted(set(terms))


def _artifact_discovery_term_variants(term: str) -> list[str]:
    cleaned = term.strip().lower()
    if not cleaned:
        return []
    variants = [cleaned]
    if cleaned in ARTIFACT_DISCOVERY_WORKSPACE_FILENAME_SENTINELS:
        return variants
    if "/" in cleaned or "\\" in cleaned:
        return variants
    parts = [part for part in re.split(r"[_\-.]+", cleaned) if part]
    if len(parts) < 2:
        return variants
    for separator in ("_", "-", ".", "/", " "):
        variants.append(separator.join(parts))
    return variants


def _artifact_discovery_runtime_timestamp_terms(terms: Sequence[str]) -> list[str]:
    timestamp_terms: list[str] = []
    seen: set[str] = set()
    for raw in terms:
        term = str(raw).strip().lower()
        if not term or term in seen:
            continue
        if not re.search(r"(?:^|[^0-9])20\d{6}t\d{4,6}z?", term):
            continue
        seen.add(term)
        timestamp_terms.append(term)
    return timestamp_terms


def _artifact_discovery_runtime_metadata_fallback_command(terms: Sequence[str]) -> str:
    timestamp_terms = _artifact_discovery_runtime_timestamp_terms(terms)
    if not timestamp_terms:
        return ""
    roots = " ".join(
        shlex.quote(root)
        for root in ARTIFACT_DISCOVERY_RUNTIME_METADATA_FALLBACK_ROOTS
    )
    query = "|".join(re.escape(term) for term in timestamp_terms)
    return f"rg --files {roots} | rg -i {shlex.quote(query)}"


def _artifact_discovery_workspace_filename_terms(terms: Sequence[str]) -> list[str]:
    cleaned_terms = [
        str(term).strip().lower()
        for term in terms
        if str(term).strip() and "/" not in str(term) and "\\" not in str(term)
    ]
    if len(set(cleaned_terms)) != 1:
        return []
    cleaned = cleaned_terms[0]
    if cleaned in ARTIFACT_DISCOVERY_WORKSPACE_FILENAME_SENTINELS:
        return [cleaned]
    return []


def _artifact_discovery_workspace_scope_roots(repo_root: Path, terms: Sequence[str]) -> list[str]:
    if not _artifact_discovery_workspace_filename_terms(terms):
        return []
    workspace_root = repo_root.parent.resolve()
    if workspace_root == repo_root.resolve() or workspace_root.name not in ARTIFACT_DISCOVERY_WORKSPACE_PARENT_NAMES:
        return []
    if not workspace_root.exists() or not workspace_root.is_dir():
        return []
    return [workspace_root.as_posix()]


def _artifact_discovery_roots(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    selected_scope_roots: Sequence[str] | None = None,
) -> list[str]:
    terms = _artifact_discovery_terms(repo_root, scope_paths)
    roots = list(
        selected_scope_roots
        or _artifact_discovery_existing_scope_roots(repo_root, scope_paths)
    )
    roots.extend(_artifact_discovery_workspace_scope_roots(repo_root, terms))
    roots.extend(ARTIFACT_DISCOVERY_ROOTS)
    seen: set[str] = set()
    ordered: list[str] = []
    for root in roots:
        if root not in seen:
            ordered.append(root)
            seen.add(root)
    return ordered


def _prioritize_artifact_discovery_roots(roots: Sequence[str], terms: Sequence[str]) -> list[str]:
    term_set = {str(term).lower() for term in terms}
    dissemination_builder_markers = (
        "build_microcosm_public_site",
        "microcosm_public_site",
        "public_site",
        "site_packet",
        "site-packet",
        "content_graph",
        "content-graph",
    )
    code_terms = {
        "action",
        "action_quote",
        "bottleneck",
        "command",
        "diff",
        "git",
        "git_state_snapshot",
        "latency",
        "process",
        "snapshot",
        "trace",
    }
    code_markers = (
        "action_quote",
        "bottleneck",
        "command",
        "diff",
        "git",
        "git_state_snapshot",
        "latency",
        "process",
        "snapshot",
        "trace",
    )
    market_terms = {"feed", "feeds", "market", "polymarket", "report"}
    lean_terms = {"lake-manifest.json", "lakefile", "lakefile.lean", "lakefile.toml", "lean-toolchain"}
    metabolism_terms = {
        "metabolism",
        "metabolism sqlite",
        "metabolism-sqlite",
        "metabolism.sqlite",
        "metabolism/sqlite",
        "metabolism_sqlite",
        "metabolismd",
    }
    microcosm_terms = {
        "doctrine_lattice",
        "lattice",
        "microcosm",
        "organ",
        "organ_atlas",
        "substrate",
    }
    named_code_surface_match = bool(term_set & code_terms) or any(
        marker in term for term in term_set for marker in code_markers
    )
    dissemination_builder_match = any(
        marker in term for term in term_set for marker in dissemination_builder_markers
    )
    code_shape_term_match = any(
        bool(re.search(r"[a-z][a-z0-9]+_[a-z0-9_]+", term))
        for term in term_set
    )
    if dissemination_builder_match:
        priority_roots = [
            "tools/meta/dissemination",
            "docs/dissemination",
            "sites/microcosm",
            "tools/meta",
            "docs",
            "microcosm-substrate/atlas",
            "microcosm-substrate/core",
        ]
    elif term_set & market_terms:
        priority_roots = [
            "state/reports/market_feeds",
            "tools/polymarket",
            "tools/meta/dissemination",
            "docs/dissemination",
            "docs",
        ]
    elif term_set & lean_terms:
        priority_roots = [
            "formal_math",
            "codex/doctrine/paper_modules",
            "codex/doctrine",
        ]
    elif term_set & metabolism_terms:
        priority_roots = [
            "state/metabolism",
            "tools/meta",
            "system",
            "codex/standards",
            "codex/doctrine",
        ]
    elif term_set & microcosm_terms:
        priority_roots = [
            "microcosm-substrate/atlas",
            "microcosm-substrate/core",
            "microcosm-substrate/organs",
            "microcosm-substrate/src",
            "microcosm-substrate/scripts",
            "microcosm-substrate/tests",
        ]
    elif named_code_surface_match:
        priority_roots = [
            "tools/meta",
            "system",
            "codex/standards",
            "codex/doctrine",
            ".agents",
        ]
    elif code_shape_term_match:
        priority_roots = [
            "system",
            "codex/standards",
            "codex/doctrine",
            "tools/meta",
            ".agents",
            "docs",
        ]
    else:
        priority_roots = []
    priority_index = {root: index for index, root in enumerate(priority_roots)}
    return sorted(
        list(roots),
        key=lambda root: (
            priority_index.get(root, len(priority_index)),
            0 if any(term and term in root.lower() for term in term_set) else 1,
            list(roots).index(root),
        ),
    )


def _is_pruned_artifact_path(rel_text: str) -> bool:
    normalized = rel_text.replace(os.sep, "/")
    parts = normalized.split("/")
    for prune in ARTIFACT_DISCOVERY_PRUNE_DIRS:
        prune_parts = prune.split("/")
        if len(prune_parts) == 1:
            if prune in parts:
                return True
            continue
        for index in range(0, len(parts) - len(prune_parts) + 1):
            if parts[index : index + len(prune_parts)] == prune_parts:
                return True
    return False


def _artifact_discovery_under_selected_scope(
    rel_text: str,
    selected_scope_roots: Sequence[str],
) -> bool:
    return any(rel_text == root or rel_text.startswith(f"{root}/") for root in selected_scope_roots)


def _iter_artifact_candidate_files(
    repo_root: Path,
    root: Path,
    *,
    pruned_directory_count: list[int],
):
    if root.is_file():
        yield root
        return
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            rel_text = _artifact_discovery_rel_text(repo_root, current_path / dirname)
            if rel_text is not None and _is_pruned_artifact_path(rel_text):
                pruned_directory_count[0] += 1
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames
        for filename in sorted(filenames):
            yield current_path / filename


def _content_metadata_match(path: Path, terms: Sequence[str]) -> dict[str, Any] | None:
    if not terms or path.suffix not in ARTIFACT_DISCOVERY_CONTENT_SUFFIXES:
        return None
    try:
        size_bytes = path.stat().st_size
    except OSError:
        return None
    if size_bytes > ARTIFACT_DISCOVERY_CONTENT_MAX_BYTES:
        return {
            "skipped": True,
            "reason": "content_metadata_size_limit",
            "size_bytes": size_bytes,
        }
    matched_terms: set[str] = set()
    line_numbers: list[int] = []
    match_count = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line_number, line in enumerate(handle, start=1):
                haystack = line.lower()
                line_matched = False
                for term in terms:
                    if term in haystack:
                        matched_terms.add(term)
                        line_matched = True
                if line_matched:
                    match_count += 1
                    if len(line_numbers) < ARTIFACT_DISCOVERY_CONTENT_LINE_PREVIEW_LIMIT:
                        line_numbers.append(line_number)
    except OSError:
        return None
    if not matched_terms:
        return None
    return {
        "matched_terms": sorted(matched_terms),
        "match_count": match_count,
        "line_numbers_preview": line_numbers,
        "size_bytes": size_bytes,
    }


def _artifact_discovery_known_owner_hits(
    repo_root: Path,
    terms: Sequence[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    matched_keys = [
        key for key in ARTIFACT_DISCOVERY_KNOWN_CONTENT_OWNER_HINTS if key in set(terms)
    ]
    if not matched_keys:
        return [], []
    rows: list[dict[str, Any]] = []
    for key in matched_keys:
        for rel_text in ARTIFACT_DISCOVERY_KNOWN_CONTENT_OWNER_HINTS[key]:
            path = repo_root / rel_text
            if not path.exists():
                continue
            content_match = _content_metadata_match(path, [key])
            if not content_match or content_match.get("skipped"):
                continue
            rows.append(
                {
                    "path": rel_text,
                    "root": _artifact_discovery_root_for_rel_path(rel_text),
                    "size_bytes": content_match.get("size_bytes"),
                    "suffix": path.suffix or "<none>",
                    "matched_terms": content_match.get("matched_terms") or [],
                    "match_kind": "content_metadata",
                    "match_count": content_match.get("match_count"),
                    "line_numbers_preview": content_match.get("line_numbers_preview") or [],
                    "surface_hint": "curated_artifact_known_owner_hint_no_body",
                }
            )
    return rows, matched_keys


def _artifact_discovery_root_for_rel_path(rel_text: str) -> str:
    best_root = ""
    for root in ARTIFACT_DISCOVERY_ROOTS:
        if rel_text == root or rel_text.startswith(f"{root}/"):
            if len(root) > len(best_root):
                best_root = root
    return best_root or rel_text.split("/", 1)[0]


def _artifact_discovery_known_owner_short_circuit(
    terms: Sequence[str],
    matched_keys: Sequence[str],
) -> bool:
    if not matched_keys:
        return False
    owner_terms = set()
    for key in matched_keys:
        owner_terms.update(_artifact_discovery_term_variants(key))
    return set(terms).issubset(owner_terms)


def _artifact_discovery_row_rank(row: Mapping[str, Any], terms: Sequence[str]) -> tuple[int, int, str]:
    path = str(row.get("path") or "")
    path_obj = Path(path)
    basename = path_obj.name.lower()
    stem = path_obj.stem.lower()
    matched_terms = [str(term).lower() for term in row.get("matched_terms") or []]
    exact_filename_match = any(term == basename or term == stem for term in terms)
    path_metadata = row.get("match_kind") == "path_metadata"
    if path_metadata and exact_filename_match:
        class_rank = 0
    elif path_metadata:
        class_rank = 1
    else:
        class_rank = 2
    return (class_rank, -len(matched_terms), path)


def _iter_artifact_discovery_inventory(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    limit: int = ARTIFACT_DISCOVERY_DEFAULT_ROW_LIMIT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    scan_deadline = started + (ARTIFACT_DISCOVERY_SCAN_BUDGET_MS / 1000.0)
    content_deadline = started + (ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS / 1000.0)
    selected_scope_roots = _artifact_discovery_existing_scope_roots(repo_root, scope_paths)
    path_scope_only = _artifact_discovery_path_scope_only(repo_root, scope_paths)
    if path_scope_only and limit == ARTIFACT_DISCOVERY_DEFAULT_ROW_LIMIT:
        limit = ARTIFACT_DISCOVERY_PATH_SCOPE_ROW_LIMIT
    terms = _artifact_discovery_terms(repo_root, scope_paths)
    filename_terms = _artifact_discovery_workspace_filename_terms(terms)
    short_circuit_filename_terms = sorted(
        set(filename_terms) & ARTIFACT_DISCOVERY_FILENAME_SHORT_CIRCUIT_TERMS
    )
    workspace_scope_roots = _artifact_discovery_workspace_scope_roots(repo_root, terms)
    root_candidates = (
        list(selected_scope_roots)
        if path_scope_only
        else _artifact_discovery_roots(
            repo_root,
            scope_paths,
            selected_scope_roots=selected_scope_roots,
        )
    )
    selected_set = set(selected_scope_roots)
    workspace_set = set(workspace_scope_roots)
    roots = list(selected_scope_roots)
    if not path_scope_only:
        roots.extend(
            root
            for root in _prioritize_artifact_discovery_roots(
                [root for root in root_candidates if root not in selected_set],
                terms,
            )
            if root not in selected_set and root not in roots
        )
    if not terms:
        return [], {
            "roots": roots,
            "root_count": len(roots),
            "selected_scope_roots": selected_scope_roots,
            "workspace_scope_roots": workspace_scope_roots,
            "path_scope_mode": (
                "selected_root_only"
                if path_scope_only
                else "selected_roots_first" if selected_scope_roots else "term_only"
            ),
            "missing_roots": [
                root for root in roots if not _artifact_discovery_root_path(repo_root, root).exists()
            ],
            "match_terms": terms,
            "scanned_path_count": 0,
            "matched_path_count": 0,
            "matched_content_path_count": 0,
            "matched_total_count": 0,
            "emitted_count": 0,
            "rows_omitted_count": 0,
            "truncated": False,
            "limit": limit,
            "row_output_policy": (
                "compact_path_scope_metadata_rows"
                if path_scope_only
                else "compact_default_metadata_rows"
            ),
            "scan_policy": (
                "terms_required_selected_path_scope_metadata_no_body"
                if path_scope_only
                else "terms_required_curated_path_and_content_metadata_no_body"
            ),
            "scan_budget_ms": ARTIFACT_DISCOVERY_SCAN_BUDGET_MS,
            "content_budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
            "scan_wall_ms": round((time.perf_counter() - started) * 1000.0),
            "scan_truncated_by_time_budget": False,
            "filename_match_short_circuit": False,
            "filename_match_short_circuit_terms": short_circuit_filename_terms,
            "selected_scope_duplicate_skip_count": 0,
            "workspace_scope_skipped_after_curated_match_count": 0,
            "pruned_path_count": 0,
            "raw_body_prune_dirs": sorted(ARTIFACT_DISCOVERY_PRUNE_DIRS),
            "content_metadata": {
                "status": "terms_required",
                "emits_file_bodies": False,
                "suffixes": sorted(ARTIFACT_DISCOVERY_CONTENT_SUFFIXES),
                "max_file_bytes": ARTIFACT_DISCOVERY_CONTENT_MAX_BYTES,
                "budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
                "scanned_path_count": 0,
                "skipped_size_limit_count": 0,
                "skipped_suffix_count": 0,
                "skipped_time_budget_count": 0,
            },
            "root_counts": {},
            "suffix_counts": {},
        }
    rows: list[dict[str, Any]] = []
    scanned_count = 0
    matched_count = 0
    content_scanned_count = 0
    content_matched_count = 0
    content_skipped_size_count = 0
    content_skipped_suffix_count = 0
    content_skipped_time_budget_count = 0
    content_time_budget_exhausted = False
    skipped_pruned_count = 0
    missing_roots: list[str] = []
    root_counts: dict[str, int] = {}
    suffix_counts: dict[str, int] = {}
    scan_truncated_by_time_budget = False
    filename_match_short_circuit = False
    selected_scope_duplicate_skip_count = 0
    duplicate_path_skip_count = 0
    workspace_scope_skipped_after_curated_match_count = 0
    pruned_directory_count = [0]
    seen_rel_paths: set[str] = set()
    known_owner_rows, known_owner_keys = _artifact_discovery_known_owner_hits(
        repo_root,
        terms,
    )
    known_owner_short_circuit = (
        not path_scope_only
        and bool(known_owner_rows)
        and _artifact_discovery_known_owner_short_circuit(terms, known_owner_keys)
    )
    for row in known_owner_rows:
        rel_text = str(row.get("path") or "")
        if not rel_text or rel_text in seen_rel_paths:
            continue
        seen_rel_paths.add(rel_text)
        rows.append(row)
        content_scanned_count += 1
        content_matched_count += 1
        root_text = str(row.get("root") or "")
        suffix = str(row.get("suffix") or "<none>")
        if root_text:
            root_counts[root_text] = root_counts.get(root_text, 0) + 1
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1

    if known_owner_short_circuit:
        rows = sorted(rows, key=lambda row: _artifact_discovery_row_rank(row, terms))[:limit]
        matched_total_count = content_matched_count
        summary = {
            "roots": roots,
            "root_count": len(roots),
            "selected_scope_roots": selected_scope_roots,
            "workspace_scope_roots": workspace_scope_roots,
            "path_scope_mode": "term_only",
            "missing_roots": missing_roots,
            "match_terms": terms,
            "scanned_path_count": len(seen_rel_paths),
            "matched_path_count": 0,
            "matched_content_path_count": content_matched_count,
            "matched_total_count": matched_total_count,
            "emitted_count": len(rows),
            "rows_omitted_count": max(matched_total_count - len(rows), 0),
            "truncated": matched_total_count > len(rows),
            "limit": limit,
            "row_output_policy": "compact_default_metadata_rows",
            "scan_policy": "known_owner_content_metadata_no_body",
            "scan_budget_ms": ARTIFACT_DISCOVERY_SCAN_BUDGET_MS,
            "content_budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
            "scan_wall_ms": round((time.perf_counter() - started) * 1000.0),
            "scan_truncated_by_time_budget": False,
            "filename_match_short_circuit": False,
            "filename_match_short_circuit_terms": short_circuit_filename_terms,
            "known_owner_hint_short_circuit": True,
            "known_owner_hint_keys": known_owner_keys,
            "known_owner_hint_count": len(rows),
            "selected_scope_duplicate_skip_count": selected_scope_duplicate_skip_count,
            "workspace_scope_skipped_after_curated_match_count": workspace_scope_skipped_after_curated_match_count,
            "duplicate_path_skip_count": duplicate_path_skip_count,
            "pruned_path_count": 0,
            "pruned_file_count": 0,
            "pruned_directory_count": 0,
            "raw_body_prune_dir_count": len(ARTIFACT_DISCOVERY_PRUNE_DIRS),
            "content_metadata": {
                "status": "known_owner_hint_short_circuit",
                "emits_file_bodies": False,
                "scanned_path_count": content_scanned_count,
                "skipped_size_limit_count": 0,
                "skipped_suffix_count": 0,
                "skipped_time_budget_count": 0,
                "suffixes": sorted(ARTIFACT_DISCOVERY_CONTENT_SUFFIXES),
                "max_file_bytes": ARTIFACT_DISCOVERY_CONTENT_MAX_BYTES,
                "budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
                "line_number_preview_limit": ARTIFACT_DISCOVERY_CONTENT_LINE_PREVIEW_LIMIT,
            },
            "root_counts": dict(sorted(root_counts.items())),
            "suffix_counts": dict(sorted(suffix_counts.items())),
            "raw_body_prune_dirs": sorted(ARTIFACT_DISCOVERY_PRUNE_DIRS),
        }
        return rows, summary

    for root_text in roots:
        if time.perf_counter() > scan_deadline:
            scan_truncated_by_time_budget = True
            break
        if root_text in workspace_set and (matched_count + content_matched_count) > 0:
            workspace_scope_skipped_after_curated_match_count += 1
            continue
        root = _artifact_discovery_root_path(repo_root, root_text)
        if not root.exists():
            missing_roots.append(root_text)
            continue
        for path in _iter_artifact_candidate_files(
            repo_root,
            root,
            pruned_directory_count=pruned_directory_count,
        ):
            if time.perf_counter() > scan_deadline:
                scan_truncated_by_time_budget = True
                break
            rel_text = _artifact_discovery_rel_text(repo_root, path)
            if rel_text is None:
                continue
            if rel_text in seen_rel_paths:
                duplicate_path_skip_count += 1
                continue
            seen_rel_paths.add(rel_text)
            if root_text not in selected_set and _artifact_discovery_under_selected_scope(
                rel_text,
                selected_scope_roots,
            ):
                selected_scope_duplicate_skip_count += 1
                continue
            if _is_pruned_artifact_path(rel_text):
                skipped_pruned_count += 1
                continue
            scanned_count += 1
            haystack = rel_text.lower()
            matched_terms = [term for term in terms if term in haystack]
            suffix = path.suffix or "<none>"
            if matched_terms:
                matched_count += 1
                root_counts[root_text] = root_counts.get(root_text, 0) + 1
                suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
                try:
                    size_bytes: int | None = path.stat().st_size
                except OSError:
                    size_bytes = None
                rows.append(
                    {
                        "path": rel_text,
                        "root": root_text,
                        "size_bytes": size_bytes,
                        "suffix": suffix,
                        "matched_terms": matched_terms,
                        "match_kind": "path_metadata",
                        "surface_hint": "curated_artifact_path_metadata",
                    }
                )
                if short_circuit_filename_terms:
                    filename_match_short_circuit = True
                    break
                continue

            if suffix not in ARTIFACT_DISCOVERY_CONTENT_SUFFIXES:
                content_skipped_suffix_count += 1
                continue
            if content_time_budget_exhausted or time.perf_counter() > content_deadline:
                content_time_budget_exhausted = True
                content_skipped_time_budget_count += 1
                continue
            content_scanned_count += 1
            content_match = _content_metadata_match(path, terms)
            if not content_match:
                continue
            if content_match.get("skipped"):
                if content_match.get("reason") == "content_metadata_size_limit":
                    content_skipped_size_count += 1
                continue
            content_matched_count += 1
            root_counts[root_text] = root_counts.get(root_text, 0) + 1
            suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
            rows.append(
                {
                    "path": rel_text,
                    "root": root_text,
                    "size_bytes": content_match.get("size_bytes"),
                    "suffix": suffix,
                    "matched_terms": content_match.get("matched_terms") or [],
                    "match_kind": "content_metadata",
                    "match_count": content_match.get("match_count"),
                    "line_numbers_preview": content_match.get("line_numbers_preview") or [],
                    "surface_hint": "curated_artifact_content_metadata_no_body",
                }
            )
        if scan_truncated_by_time_budget:
            break
        if filename_match_short_circuit:
            break

    matched_total_count = matched_count + content_matched_count
    total_pruned_count = skipped_pruned_count + pruned_directory_count[0]
    rows = sorted(rows, key=lambda row: _artifact_discovery_row_rank(row, terms))[:limit]
    content_metadata = {
        "status": "omitted_path_scope_only"
        if path_scope_only
        else "omitted_time_budget"
        if content_time_budget_exhausted
        else "bounded_scan_completed",
        "emits_file_bodies": False,
        "scanned_path_count": 0 if path_scope_only else content_scanned_count,
        "skipped_size_limit_count": 0 if path_scope_only else content_skipped_size_count,
        "skipped_suffix_count": 0 if path_scope_only else content_skipped_suffix_count,
        "skipped_time_budget_count": 0 if path_scope_only else content_skipped_time_budget_count,
    }
    if not path_scope_only:
        content_metadata.update(
            {
                "suffixes": sorted(ARTIFACT_DISCOVERY_CONTENT_SUFFIXES),
                "max_file_bytes": ARTIFACT_DISCOVERY_CONTENT_MAX_BYTES,
                "budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
                "line_number_preview_limit": ARTIFACT_DISCOVERY_CONTENT_LINE_PREVIEW_LIMIT,
            }
        )
    summary = {
        "roots": roots,
        "root_count": len(roots),
        "selected_scope_roots": selected_scope_roots,
        "workspace_scope_roots": workspace_scope_roots,
        "path_scope_mode": (
            "selected_root_only"
            if path_scope_only
            else "selected_roots_first" if selected_scope_roots else "term_only"
        ),
        "missing_roots": missing_roots,
        "match_terms": terms,
        "scanned_path_count": scanned_count,
        "matched_path_count": matched_count,
        "matched_content_path_count": content_matched_count,
        "matched_total_count": matched_total_count,
        "emitted_count": len(rows),
        "rows_omitted_count": max(matched_total_count - len(rows), 0),
        "truncated": matched_total_count > len(rows) or scan_truncated_by_time_budget,
        "limit": limit,
        "row_output_policy": (
            "compact_path_scope_metadata_rows"
            if path_scope_only
            else "compact_default_metadata_rows"
        ),
        "scan_policy": (
            "selected_path_scope_metadata_no_body"
            if path_scope_only
            else "curated_path_and_content_metadata_no_body"
        ),
        "scan_budget_ms": ARTIFACT_DISCOVERY_SCAN_BUDGET_MS,
        "content_budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
        "scan_wall_ms": round((time.perf_counter() - started) * 1000.0),
        "scan_truncated_by_time_budget": scan_truncated_by_time_budget,
        "filename_match_short_circuit": filename_match_short_circuit,
        "filename_match_short_circuit_terms": short_circuit_filename_terms,
        "known_owner_hint_short_circuit": False,
        "known_owner_hint_keys": known_owner_keys,
        "known_owner_hint_count": len(known_owner_rows),
        "selected_scope_duplicate_skip_count": selected_scope_duplicate_skip_count,
        "workspace_scope_skipped_after_curated_match_count": workspace_scope_skipped_after_curated_match_count,
        "duplicate_path_skip_count": duplicate_path_skip_count,
        "pruned_path_count": total_pruned_count,
        "pruned_file_count": skipped_pruned_count,
        "pruned_directory_count": pruned_directory_count[0],
        "raw_body_prune_dir_count": len(ARTIFACT_DISCOVERY_PRUNE_DIRS),
        "content_metadata": content_metadata,
        "root_counts": dict(sorted(root_counts.items())),
        "suffix_counts": dict(sorted(suffix_counts.items())),
    }
    if not path_scope_only:
        summary["raw_body_prune_dirs"] = sorted(ARTIFACT_DISCOVERY_PRUNE_DIRS)
    return rows, summary


def _artifact_discovery_scope_quality(
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    terms = [str(term) for term in _as_list(summary.get("match_terms")) if str(term)]
    matched_total_count = _nonnegative_int(summary.get("matched_total_count"), default=0)
    rows_omitted_count = _nonnegative_int(summary.get("rows_omitted_count"), default=0)
    scan_truncated = bool(summary.get("scan_truncated_by_time_budget"))
    high_volume = (
        matched_total_count > max(ARTIFACT_DISCOVERY_DEFAULT_ROW_LIMIT * 4, 100)
        or rows_omitted_count > ARTIFACT_DISCOVERY_DEFAULT_ROW_LIMIT * 2
        or (scan_truncated and matched_total_count > ARTIFACT_DISCOVERY_DEFAULT_ROW_LIMIT)
    )
    if not high_volume or len(terms) < 3:
        return {
            "status": "acceptable_scope",
            "high_volume": high_volume,
            "match_term_count": len(terms),
        }

    common_terms = [
        term for term in terms if term.lower() in ARTIFACT_DISCOVERY_COMMON_SCOPE_TERMS
    ]
    rare_terms = _artifact_discovery_scope_rare_terms(terms)
    if not rare_terms:
        return {
            "status": "broad_scope_no_rare_terms_detected",
            "high_volume": True,
            "match_term_count": len(terms),
            "common_terms": common_terms[:8],
            "matched_total_count": summary.get("matched_total_count"),
            "rows_omitted_count": summary.get("rows_omitted_count"),
        }

    narrowed_scope = " ".join(rare_terms)
    narrowed_quote_command = (
        "./repo-python tools/meta/control/action_quote.py "
        f"--action artifact_discovery_inventory --scope {shlex.quote(narrowed_scope)}"
    )
    narrowed_kernel_command = (
        f"./repo-python kernel.py --artifact-discovery-inventory {shlex.quote(narrowed_scope)}"
    )
    return {
        "status": "scope_too_broad_narrow_first",
        "high_volume": True,
        "match_term_count": len(terms),
        "common_terms": common_terms[:8],
        "rare_terms": rare_terms,
        "narrowed_scope": narrowed_scope,
        "narrowed_quote_command": narrowed_quote_command,
        "narrowed_kernel_command": narrowed_kernel_command,
        "matched_total_count": summary.get("matched_total_count"),
        "rows_omitted_count": summary.get("rows_omitted_count"),
        "scan_truncated_by_time_budget": summary.get("scan_truncated_by_time_budget"),
    }


def _artifact_discovery_scope_rare_terms(
    terms: Sequence[str],
    *,
    limit: int = 3,
) -> list[str]:
    rare_terms: list[str] = []
    for term in terms:
        normalized = str(term).lower()
        if normalized in ARTIFACT_DISCOVERY_COMMON_SCOPE_TERMS:
            continue
        if normalized in ARTIFACT_DISCOVERY_PROSE_SCOPE_TERMS:
            continue
        if "_" in term and term not in rare_terms:
            rare_terms.append(term)
    for term in terms:
        normalized = str(term).lower()
        if (
            normalized in ARTIFACT_DISCOVERY_COMMON_SCOPE_TERMS
            or normalized in ARTIFACT_DISCOVERY_PROSE_SCOPE_TERMS
            or term in rare_terms
        ):
            continue
        if len(term) >= 8 and not any(separator in term for separator in (" ", "-", "/", ".")):
            rare_terms.append(term)
    return rare_terms[:limit]


def _artifact_discovery_scope_preflight_narrowing(
    repo_root: Path,
    scope_paths: Sequence[str],
) -> dict[str, Any] | None:
    scopes = _scope_paths(scope_paths)
    if not scopes:
        return None
    if _artifact_discovery_existing_scope_roots(repo_root, scopes):
        return None
    raw_terms = [
        token.strip().strip("'\"`;,()")
        for raw in scopes
        for token in re.split(r"[^A-Za-z0-9_.-]+", raw)
        if token.strip().strip("'\"`;,()")
    ]
    if len(raw_terms) < 5:
        return None
    terms = _artifact_discovery_terms(repo_root, scopes)
    if len(terms) < 5:
        return None
    common_terms = [
        term for term in terms if term.lower() in ARTIFACT_DISCOVERY_COMMON_SCOPE_TERMS
    ]
    prose_terms = [
        term for term in terms if term.lower() in ARTIFACT_DISCOVERY_PROSE_SCOPE_TERMS
    ]
    if not prose_terms and len(common_terms) < 2:
        return None
    rare_terms = _artifact_discovery_scope_rare_terms(terms)
    if not rare_terms:
        return None
    narrowed_scope = " ".join(rare_terms)
    narrowed_terms = set(_artifact_discovery_terms(repo_root, [narrowed_scope]))
    dropped_terms = [term for term in terms if term not in narrowed_terms]
    if not dropped_terms:
        return None
    narrowed_quote_command = (
        "./repo-python tools/meta/control/action_quote.py "
        f"--action artifact_discovery_inventory --scope {shlex.quote(narrowed_scope)}"
    )
    narrowed_kernel_command = (
        f"./repo-python kernel.py --artifact-discovery-inventory {shlex.quote(narrowed_scope)}"
    )
    return {
        "status": "scope_too_broad_narrow_first",
        "preflight_only": True,
        "scan_skipped": True,
        "high_volume": True,
        "match_term_count": len(terms),
        "raw_term_count": len(raw_terms),
        "common_terms": common_terms[:8],
        "prose_terms": prose_terms[:8],
        "rare_terms": rare_terms,
        "dropped_terms": dropped_terms[:12],
        "narrowed_scope": narrowed_scope,
        "narrowed_quote_command": narrowed_quote_command,
        "narrowed_kernel_command": narrowed_kernel_command,
        "skipped_scan_budget_ms": ARTIFACT_DISCOVERY_SCAN_BUDGET_MS,
        "skipped_content_budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
    }


def _quote_artifact_discovery_scope_preflight(
    scope_paths: Sequence[str],
    scope_quality: Mapping[str, Any],
) -> dict[str, Any]:
    command_scopes = _scope_paths(scope_paths)
    term_arg = " ".join(f"--scope {shlex.quote(scope)}" for scope in command_scopes)
    broad_quote_command = "./repo-python tools/meta/control/action_quote.py --action artifact_discovery_inventory"
    if term_arg:
        broad_quote_command = f"{broad_quote_command} {term_arg}"
    full_profile_command = f"{broad_quote_command} --full"
    narrowed_quote_command = str(scope_quality.get("narrowed_quote_command") or broad_quote_command)
    narrowed_kernel_command = str(scope_quality.get("narrowed_kernel_command") or "")
    rare_terms = [str(term) for term in _as_list(scope_quality.get("rare_terms"))]
    root_args = " ".join(shlex.quote(root) for root in ARTIFACT_DISCOVERY_ROOTS)
    query = "|".join(re.escape(term) for term in rare_terms) or "<term>"
    return {
        "current_status": "scope_needs_narrowing_before_inventory",
        "recommendation": "narrow_scope_to_rare_terms_before_inventory",
        "freshness": "scope_text_preflight",
        "authority_level": "scope_text_read_model",
        "drilldown_command": narrowed_quote_command,
        "suggested_command": narrowed_quote_command,
        "replacement_command": narrowed_quote_command,
        "full_profile_command": full_profile_command,
        "fallback_path_metadata_command": f"rg --files {root_args} | rg {shlex.quote(query)}",
        "avoid_command_shapes": [
            "find docs/dissemination state -name '*<term>*' 2>/dev/null | head/tail",
            "grep -rli '<term>' tools system docs state",
            "rg -n '<term>' system tools codex docs state before an owner/root is selected",
            "rg -n '<term>' codex tools when codex/hologram/raw or runtime hook logs can match",
            "find state/runs -name '*global_polymarket_feed*' | head",
        ],
        "do_not_touch": [
            {
                "lane": "raw_artifact_find_scan",
                "reason": "Broad find scans over artifact trees produce path floods and often miss owner indexes.",
                "replacement": narrowed_quote_command,
            },
            {
                "lane": "raw_recursive_artifact_grep",
                "reason": "Recursive content grep over docs/state/tool artifacts risks huge output and raw-body exposure.",
                "replacement": narrowed_quote_command,
            },
            {
                "lane": "raw_hologram_or_runtime_hook_grep",
                "reason": "Raw hologram and runtime hook observability files can contain copied command bodies and transcript-sized payloads.",
                "replacement": narrowed_quote_command,
            },
        ],
        "recommended_sequence": [
            "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
            narrowed_kernel_command,
            narrowed_quote_command,
            "Open exact matched paths only when the metadata row is the selected evidence.",
        ],
        "scope_guidance": {
            "first_contact_route": "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
            "owner_quote_route": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action artifact_discovery_inventory --scope <term-or-root>"
            ),
            "use_for": [
                "path fragment discovery",
                "root or artifact family discovery",
                "broad file discovery before recursive find/grep/rg",
            ],
            "does_not_replace": [
                "scoped low-output rg/find after a target file or root is selected",
                "python symbol/card routes when a code symbol is already known",
                "full owner content reads after the metadata row is selected",
            ],
        },
        "scope_quality": dict(scope_quality),
        "inventory": {
            "privacy": {
                "stores_file_contents": False,
                "stores_stdout_stderr_bodies": False,
                "emits": "scope terms and narrowing commands only; no artifact roots are walked",
            },
            "summary": {
                "scan_policy": "scope_text_preflight_no_walk",
                "scan_wall_ms": 0,
                "scan_budget_ms": ARTIFACT_DISCOVERY_SCAN_BUDGET_MS,
                "content_budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
                "match_terms": list(scope_quality.get("dropped_terms") or []) + rare_terms,
                "matched_total_count": None,
                "emitted_count": 0,
                "rows_omitted_count": 0,
                "preflight_only": True,
            },
        },
        "output_economy": {
            "default_profile": "scope_preflight_no_walk",
            "current_profile": "scope_preflight_no_walk",
            "skipped_broad_scan_budget_ms": ARTIFACT_DISCOVERY_SCAN_BUDGET_MS,
            "skipped_content_budget_ms": ARTIFACT_DISCOVERY_CONTENT_BUDGET_MS,
            "full_inventory_command": full_profile_command,
            "direct_kernel_inventory_command": narrowed_kernel_command,
            "broad_quote_command": broad_quote_command,
        },
        "source": {
            "privacy": "scope_text_only_no_artifact_bodies_or_stdout_stderr_bodies",
            "excluded_high_volume_roots": ["state/runs", "state/observability/renders"],
        },
    }


def _quote_artifact_discovery_inventory(
    repo_root: Path,
    scope_paths: Sequence[str],
    *,
    full: bool = False,
) -> dict[str, Any]:
    if not full:
        preflight_narrowing = _artifact_discovery_scope_preflight_narrowing(
            repo_root,
            scope_paths,
        )
        if preflight_narrowing is not None:
            return _quote_artifact_discovery_scope_preflight(scope_paths, preflight_narrowing)
    rows, summary = _iter_artifact_discovery_inventory(repo_root, scope_paths)
    command_scopes = _scope_paths(scope_paths) or list(summary["match_terms"])
    term_arg = " ".join(f"--scope {shlex.quote(scope)}" for scope in command_scopes)
    suggested = "./repo-python tools/meta/control/action_quote.py --action artifact_discovery_inventory"
    if term_arg:
        suggested = f"{suggested} {term_arg}"
    kernel_terms = " ".join(shlex.quote(scope) for scope in command_scopes) or "<term-or-root>"
    kernel_inventory_command = f"./repo-python kernel.py --artifact-discovery-inventory {kernel_terms}"
    root_args = " ".join(shlex.quote(root) for root in ARTIFACT_DISCOVERY_ROOTS)
    query = "|".join(re.escape(term) for term in summary["match_terms"]) or "<term>"
    runtime_timestamp_terms = _artifact_discovery_runtime_timestamp_terms(
        summary["match_terms"]
    )
    runtime_metadata_fallback_command = (
        _artifact_discovery_runtime_metadata_fallback_command(summary["match_terms"])
    )
    if runtime_timestamp_terms:
        summary["runtime_timestamp_scope_terms"] = runtime_timestamp_terms
        summary["runtime_metadata_fallback_roots"] = list(
            ARTIFACT_DISCOVERY_RUNTIME_METADATA_FALLBACK_ROOTS
        )
        summary["runtime_metadata_fallback_available"] = bool(
            runtime_metadata_fallback_command
        )
    scope_quality = _artifact_discovery_scope_quality(summary)
    narrowed_quote_command = str(scope_quality.get("narrowed_quote_command") or "")
    narrowed_kernel_command = str(scope_quality.get("narrowed_kernel_command") or "")
    current_status = "matches_available" if rows else "no_matches_or_terms"
    if summary.get("scan_truncated_by_time_budget"):
        current_status = "matches_available_bounded_partial" if rows else "no_matches_before_time_budget"
    if scope_quality.get("status") == "scope_too_broad_narrow_first":
        current_status = "matches_available_but_scope_too_broad"
    privacy = {
        "stores_file_contents": False,
        "stores_stdout_stderr_bodies": False,
        "emits": "path, root, suffix, size_bytes, matched_terms, match_kind, match_count, and line_numbers_preview only",
    }
    if summary.get("path_scope_mode") == "selected_root_only":
        return {
            "current_status": current_status,
            "recommendation": "use_selected_path_scope_inventory_before_raw_find",
            "freshness": "live_path_metadata",
            "authority_level": "path_metadata_read_model",
            "drilldown_command": suggested,
            "suggested_command": suggested,
            "replacement_command": suggested,
            "fallback_path_metadata_command": (
                f"rg --files {' '.join(shlex.quote(root) for root in summary['selected_scope_roots'])}"
            ),
            "path_scope_profile": {
                "mode": "selected_root_only",
                "scan_behavior": "selected_existing_scope_roots_only",
                "broad_curated_roots_scanned": False,
                "full_broad_inventory_command": (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action artifact_discovery_inventory --scope <term>"
                ),
            },
            "do_not_touch": [
                {
                    "lane": "raw_selected_root_find_scan",
                    "reason": "The selected-root inventory already emits bounded path metadata and omission counts.",
                    "replacement": suggested,
                }
            ],
            "inventory": {
                "privacy": privacy,
                "summary": summary,
                "rows": rows,
            },
            "source": {
                "privacy": "metadata_only_no_artifact_bodies_or_stdout_stderr_bodies",
                "excluded_high_volume_roots": ["state/runs", "state/observability/renders"],
            },
        }
    full_profile_command = f"{suggested} --full"
    inventory: dict[str, Any] = {
        "privacy": {
            "stores_file_contents": False,
            "stores_stdout_stderr_bodies": False,
            "emits": "path, root, suffix, size_bytes, matched_terms, match_kind, match_count, and line_numbers_preview only",
        },
        "summary": summary,
    }
    if full:
        inventory.update(
            {
                "rows": rows,
                "row_profile": "full_metadata_rows",
            }
        )
    else:
        rows_preview = rows[:ARTIFACT_DISCOVERY_DEFAULT_ROW_PREVIEW_LIMIT]
        inventory.update(
            {
                "rows_preview": rows_preview,
                "row_profile": "summary_first_metadata_preview",
                "rows_omitted": max(0, len(rows) - len(rows_preview)),
                "matched_rows_omitted": summary.get("rows_omitted_count", 0),
                "full_profile_command": full_profile_command,
                "omission_receipt": {
                    "omitted": [
                        "artifact metadata rows beyond preview",
                        "full broad inventory rows",
                    ],
                    "reason": "artifact_discovery_inventory quote is a first-contact handoff; full row evidence belongs behind --full or the direct kernel route.",
                    "drilldown": full_profile_command,
                },
            }
        )
    recommendation = "use_metadata_inventory_before_artifact_scan"
    if scope_quality.get("status") == "scope_too_broad_narrow_first":
        recommendation = "narrow_scope_to_rare_terms_before_inventory"
    first_inventory_command = narrowed_quote_command or suggested
    first_kernel_inventory_command = narrowed_kernel_command or kernel_inventory_command
    recommended_sequence = [
        "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
        first_kernel_inventory_command,
        first_inventory_command,
    ]
    if runtime_metadata_fallback_command:
        recommended_sequence.append(runtime_metadata_fallback_command)
    recommended_sequence.append(
        "Open exact matched paths only when the metadata row is the selected evidence."
    )
    do_not_touch = [
        {
            "lane": "raw_artifact_find_scan",
            "reason": "Broad find scans over artifact trees produce path floods and often miss owner indexes.",
            "replacement": first_inventory_command,
        },
        {
            "lane": "raw_recursive_artifact_grep",
            "reason": "Recursive content grep over docs/state/tool artifacts risks huge output and raw-body exposure.",
            "replacement": first_inventory_command,
        },
        {
            "lane": "raw_hologram_or_runtime_hook_grep",
            "reason": "Raw hologram and runtime hook observability files can contain copied command bodies and transcript-sized payloads.",
            "replacement": first_inventory_command,
        },
        {
            "lane": "state_runs_market_feed_scan",
            "reason": "Historical run artifacts can contain many feed snapshots; use current market/report roots or the market snapshot owner before scanning state/runs.",
            "replacement": "./repo-python tools/meta/control/market_snapshot.py --help",
        },
    ]
    if runtime_metadata_fallback_command:
        do_not_touch.insert(
            0,
            {
                "lane": "runtime_timestamp_artifact_find_scan",
                "reason": "Timestamp-shaped runtime artifact searches should use metadata-only runtime roots before any broad find over / or state trees.",
                "replacement": runtime_metadata_fallback_command,
            },
        )
    return {
        "current_status": current_status,
        "recommendation": recommendation,
        "freshness": "live_path_and_content_metadata",
        "authority_level": "path_and_content_metadata_read_model",
        "drilldown_command": first_inventory_command,
        "suggested_command": first_inventory_command,
        "replacement_command": first_inventory_command,
        "full_profile_command": full_profile_command,
        "fallback_path_metadata_command": f"rg --files {root_args} | rg {shlex.quote(query)}",
        **(
            {"runtime_artifact_metadata_fallback_command": runtime_metadata_fallback_command}
            if runtime_metadata_fallback_command
            else {}
        ),
        "avoid_command_shapes": [
            "find docs/dissemination state -name '*<term>*' 2>/dev/null | head/tail",
            "grep -rli '<term>' tools system docs state",
            "rg -n '<term>' system tools codex docs state before an owner/root is selected",
            "rg -n '<term>' codex tools when codex/hologram/raw or runtime hook logs can match",
            "find state/runs -name '*global_polymarket_feed*' | head",
        ],
        "do_not_touch": do_not_touch,
        "recommended_sequence": recommended_sequence,
        "scope_guidance": {
            "first_contact_route": "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
            "owner_quote_route": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action artifact_discovery_inventory --scope <term-or-root>"
            ),
            "use_for": [
                "path fragment discovery",
                "root or artifact family discovery",
                "broad file discovery before recursive find/grep/rg",
            ],
            "does_not_replace": [
                "scoped low-output rg/find after a target file or root is selected",
                "python symbol/card routes when a code symbol is already known",
                "full owner content reads after the metadata row is selected",
            ],
        },
        "scope_quality": scope_quality,
        "inventory": inventory,
        "output_economy": {
            "default_profile": "summary_first_metadata_preview",
            "current_profile": "full_metadata_rows" if full else "summary_first_metadata_preview",
            "rows_preview_limit": ARTIFACT_DISCOVERY_DEFAULT_ROW_PREVIEW_LIMIT,
            "rows_full_limit": ARTIFACT_DISCOVERY_DEFAULT_ROW_LIMIT,
            "full_inventory_command": full_profile_command,
            "direct_kernel_inventory_command": first_kernel_inventory_command,
            "broad_kernel_inventory_command": kernel_inventory_command,
            **(
                {"runtime_metadata_fallback_command": runtime_metadata_fallback_command}
                if runtime_metadata_fallback_command
                else {}
            ),
        },
        "source": {
            "privacy": "metadata_only_no_artifact_bodies_or_stdout_stderr_bodies",
            "excluded_high_volume_roots": ["state/runs", "state/observability/renders"],
            **(
                {
                    "runtime_metadata_fallback_roots": list(
                        ARTIFACT_DISCOVERY_RUNTIME_METADATA_FALLBACK_ROOTS
                    )
                }
                if runtime_metadata_fallback_command
                else {}
            ),
        },
    }


def build_action_catalog(repo_root: Path | str) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    aliases_by_action: dict[str, list[str]] = {action_id: [] for action_id in ACTION_CATALOG}
    for alias, action_id in ACTION_ALIASES.items():
        aliases_by_action.setdefault(action_id, []).append(alias)
    return {
        "schema": CATALOG_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "actions": [
            {
                "action_id": action_id,
                **metadata,
                "quote_command": f"./repo-python tools/meta/control/action_quote.py --action {action_id}",
                "aliases": sorted(aliases_by_action.get(action_id, [])),
            }
            for action_id, metadata in ACTION_CATALOG.items()
        ],
        "admission_consumer_coverage": _admission_consumer_coverage(repo),
        "source_status": {
            "speedboard": "available" if (repo / SPEEDBOARD_REL).is_file() else "missing",
            "process_summary": "available" if (repo / PROCESS_SUMMARY_REL).is_file() else "missing",
            "active_claims": "available" if (repo / ACTIVE_CLAIMS_REL).is_file() else "missing",
            "command_runs": "available" if (repo / "state/command_runs").exists() else "missing",
            "run_test_slice": "available" if (repo / RUN_TEST_SLICE_REL).is_file() else "missing",
            "select_impacted_tests": "available" if (repo / SELECT_IMPACTED_TESTS_REL).is_file() else "missing",
            "test_inventory": "available" if (repo / TEST_INVENTORY_REL).is_file() else "missing",
            "test_impact_map": "available" if (repo / TEST_IMPACT_MAP_REL).is_file() else "missing",
            "frontend_package": "available" if (repo / FRONTEND_UI_PACKAGE_REL).is_file() else "missing",
            "frontend_vitest_config": "available" if (repo / FRONTEND_UI_VITEST_CONFIG_REL).is_file() else "missing",
            "station_render": "available" if (repo / STATION_RENDER_TOOL_REL).is_file() else "missing",
            "station_render_manifest": "available" if (repo / STATION_RENDER_MANIFEST_REL).is_file() else "missing",
            "station_render_timing_index": "available" if (repo / STATION_RENDER_LOAD_INDEX_REL).is_file() else "missing",
            "paper_module_index_tool": "available" if (repo / PAPER_MODULE_INDEX_TOOL_REL).is_file() else "missing",
            "paper_module_index": "available" if (repo / PAPER_MODULE_INDEX_REL).is_file() else "missing",
            "paper_module_validation_report": "available" if (repo / PAPER_MODULE_VALIDATION_REL).is_file() else "missing",
            "paper_module_route_coverage": "available" if (repo / PAPER_MODULE_ROUTE_COVERAGE_REL).is_file() else "missing",
            "task_ledger_apply": "available" if (repo / TASK_LEDGER_APPLY_REL).is_file() else "missing",
            "generated_state_drainer": "available" if (repo / GENERATED_STATE_DRAINER_REL).is_file() else "missing",
            "scoped_commit": "available" if (repo / SCOPED_COMMIT_TOOL_REL).is_file() else "missing",
            "artifact_discovery_roots": {
                root: "available" if (repo / root).exists() else "missing"
                for root in ARTIFACT_DISCOVERY_ROOTS
            },
        },
    }


def build_action_quote(
    repo_root: Path | str,
    *,
    action_id: str,
    scope_paths: Sequence[str] = (),
    extra_args: Sequence[str] = (),
    current_session_id: str | None = None,
    action_kind: str | None = None,
    include_host_pressure: bool = True,
    latency_seed_include_git: bool = True,
    full: bool = False,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    requested_action_id = str(action_id).strip().lower().replace("-", "_")
    normalized = normalize_action_id(action_id)
    if normalized not in ACTION_CATALOG:
        raise ValueError(f"unknown action_id: {action_id}")
    if normalized in {
        "task_ledger_rebuild_status",
        "kernel_output_economy",
    } and _scope_mentions_task_ledger_quick_capture(scope_paths):
        normalized = "task_ledger_quick_capture"
    if (
        normalized == "task_ledger_rebuild_status"
        and requested_action_id in {"repo_tool", "repo_tool_command"}
        and _scope_mentions_storage_doctor(scope_paths)
    ):
        normalized = "storage_doctor_status"
    if (
        normalized == "task_ledger_rebuild_status"
        and requested_action_id in {"repo_tool", "repo_tool_command"}
        and _scope_mentions_document_read_known_owner_route(repo, scope_paths)
    ):
        normalized = "document_read_economy"
    if normalized == "document_read_economy" and requested_action_id == "bash_cat":
        routed_action_id, _reason = _bash_other_scope_route(scope_paths)
        if routed_action_id in {"git_state_snapshot_status", "process_summary_status"}:
            normalized = "bash_other_economy"
    if (
        normalized == "artifact_discovery_inventory"
        and requested_action_id in HOST_FILESYSTEM_FIND_ALIASES
        and _scope_mentions_git_object_store(scope_paths)
    ):
        normalized = "git_object_store_status"
    if (
        normalized == "artifact_discovery_inventory"
        and requested_action_id in HOST_FILESYSTEM_FIND_ALIASES
        and _host_filesystem_find_scope_resolution(repo, scope_paths) is not None
    ):
        normalized = "host_filesystem_discovery"
    shell_search_aliases = {
        "bash_find",
        "bash_grep",
        "find",
        "grep",
        "raw_find",
        "raw_grep",
        "raw_rg",
        "recursive_grep",
        "repo_grep",
        "repo_search",
        "rg",
        "rg_search",
        "ripgrep",
        "text_search",
    }
    if normalized == "artifact_discovery_inventory" and requested_action_id in shell_search_aliases:
        routed_action_id, _route_reason = _bash_other_scope_route(scope_paths)
        if routed_action_id == "process_summary_status":
            normalized = "bash_other_economy"
    command_scope_resolution = _command_surface_scope_resolution(repo, scope_paths, full=full)
    if (
        normalized == "artifact_discovery_inventory"
        and requested_action_id in shell_search_aliases
        and command_scope_resolution is not None
        and command_scope_resolution.get("status") == "scoped_kernel_surface"
    ):
        normalized = "command_surface_inventory"
    base = ACTION_CATALOG[normalized]
    pre_admission: dict[str, Any] | None = None
    if include_host_pressure and normalized == "latency_seed_preflight":
        config = HOST_PRESSURE_ADMISSION_BY_ACTION[normalized]
        admission_kwargs: dict[str, Any] = {"include_processes": False}
        if full:
            admission_kwargs["full"] = True
        pre_admission = _host_pressure_admission_quote(
            repo,
            config["workload_class"],
            **admission_kwargs,
        )
        if latency_seed_include_git and _host_pressure_blocks_new_work(pre_admission):
            latency_seed_include_git = False
    if normalized == "repo_pytest_validation":
        detail = _quote_repo_pytest(
            repo,
            scope_paths,
            extra_args,
            current_session_id=current_session_id,
            full=full,
        )
    elif normalized == "latency_seed_preflight":
        detail = _quote_latency_seed_preflight(
            repo,
            scope_paths,
            current_session_id=current_session_id,
            include_git=latency_seed_include_git,
        )
    elif normalized == "work_ledger_session_preflight":
        detail = _quote_work_ledger_session_preflight(
            scope_paths,
            current_session_id=current_session_id,
        )
    elif normalized == "work_ledger_heartbeat":
        detail = _quote_work_ledger_heartbeat(
            scope_paths,
            current_session_id=current_session_id,
        )
    elif normalized == "work_ledger_claim_read":
        detail = _quote_work_ledger_claim_read(repo, scope_paths, current_session_id=current_session_id)
    elif normalized == "task_ledger_validate":
        detail = _quote_task_ledger_validate(repo)
    elif normalized == "task_ledger_rebuild_status":
        detail = _quote_task_ledger_rebuild_status(repo)
    elif normalized == "task_ledger_quick_capture":
        detail = _quote_task_ledger_quick_capture(repo)
    elif normalized == "storage_doctor_status":
        detail = _quote_storage_doctor_status(repo)
    elif normalized == "process_bottleneck_triage":
        detail = _quote_process_bottleneck_triage(
            repo,
            action_kind=action_kind,
            scope_paths=scope_paths,
        )
    elif normalized == "process_summary_status":
        detail = _quote_process_summary_status(repo, scope_paths)
    elif normalized == "destructive_shell_guard":
        detail = _quote_destructive_shell_guard(repo, scope_paths)
    elif normalized == "document_read_economy":
        detail = _quote_document_read_economy(repo, scope_paths)
    elif normalized == "kernel_output_economy":
        detail = _quote_kernel_output_economy(repo, scope_paths)
    elif normalized == "exec_session_wait_tax":
        detail = _quote_exec_session_wait_tax(repo, scope_paths)
    elif normalized == "frontend_vitest_validation":
        detail = _quote_frontend_vitest(repo, scope_paths, extra_args, current_session_id=current_session_id)
    elif normalized == "station_render_capture":
        detail = _quote_station_render_capture(repo, scope_paths)
    elif normalized == "paper_module_index":
        detail = _quote_paper_module_index(repo)
    elif normalized == "generated_state_settlement":
        detail = _quote_generated_state_settlement(repo, scope_paths)
    elif normalized == "scoped_commit_private_index":
        detail = _quote_scoped_commit_private_index(
            repo,
            scope_paths,
            current_session_id=current_session_id,
        )
    elif normalized == "helper_lease_admission":
        detail = _quote_helper_lease_admission(repo)
    elif normalized == "resident_pressure_relief":
        detail = _quote_resident_pressure_relief(repo)
    elif normalized == "session_yield_request":
        detail = _quote_session_yield_request(repo)
    elif normalized == "session_yield_result":
        detail = _quote_session_yield_result(repo)
    elif normalized == "bash_other_economy":
        detail = _quote_bash_other_economy(repo, scope_paths, full=full)
    elif normalized == "command_surface_inventory":
        detail = _quote_command_surface_inventory(repo, scope_paths, full=full)
    elif normalized == "artifact_discovery_inventory":
        if requested_action_id in HOST_FILESYSTEM_FIND_ALIASES:
            scope_paths = _bash_other_artifact_scope_paths(repo, scope_paths)
        detail = _quote_artifact_discovery_inventory(repo, scope_paths, full=full)
    elif normalized == "git_object_store_status":
        detail = _quote_git_object_store_status(repo, scope_paths)
    elif normalized == "host_filesystem_discovery":
        detail = _quote_host_filesystem_discovery(repo, scope_paths)
    elif normalized == "git_state_snapshot_status":
        detail = _quote_git_state_snapshot_status(repo)
    elif normalized == "git_diff_review_context":
        detail = _quote_git_diff_review_context(repo)
    else:
        raise ValueError(f"unknown action_id: {action_id}")
    if include_host_pressure:
        if pre_admission is not None:
            detail = _apply_host_pressure_admission(normalized, detail, pre_admission)
        else:
            detail = _with_host_pressure_admission(repo, normalized, detail, full=full)
    else:
        detail = _with_deferred_host_pressure_admission(
            repo,
            normalized,
            detail,
            reason="command_profile_metadata_only",
        )
    if normalized == "repo_pytest_validation":
        detail = _apply_repo_pytest_disk_pressure(repo, detail, full=full)
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "action_id": normalized,
        "purpose": base["purpose"],
        "owner_surface": base["owner_surface"],
        "resource_class": base["resource_class"],
        "authority_level": detail.get("authority_level") or base["authority_level"],
        "quote_sources": base["quote_sources"],
        "freshness": detail.get("freshness") or "unknown",
        "drilldown_command": detail.get("drilldown_command") or detail.get("suggested_command"),
        "do_not_touch": _as_list(detail.get("do_not_touch")),
        **detail,
    }


def render_action_quote_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Action Quote",
        "",
        f"- action: `{payload.get('action_id')}`",
        f"- status: `{payload.get('current_status')}`",
        f"- recommendation: `{payload.get('recommendation')}`",
        f"- owner: `{payload.get('owner_surface')}`",
        f"- resource: `{payload.get('resource_class')}`",
        f"- authority: `{payload.get('authority_level')}`",
        f"- freshness: `{payload.get('freshness')}`",
    ]
    command = payload.get("suggested_command")
    if command:
        lines.append(f"- suggested command: `{command}`")
    host_admission = _as_mapping(payload.get("host_pressure_admission"))
    if host_admission.get("status") == "available":
        admission = _as_mapping(host_admission.get("admission"))
        lines.append(f"- host pressure decision: `{host_admission.get('decision')}`")
        if admission.get("reason"):
            lines.append(f"- host pressure reason: `{admission.get('reason')}`")
    conflicts = _as_list(payload.get("claim_conflicts"))
    if conflicts:
        lines.append(f"- claim conflicts: `{len(conflicts)}`")
    avoid = _as_list(payload.get("do_not_touch"))
    if avoid:
        lines.append(f"- do not touch lanes: `{len(avoid)}`")
    return "\n".join(lines) + "\n"
