from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from . import secret_exclusion_scan
from .organs import macro_projection_import_protocol
from .receipts import utc_now, write_json_atomic
from .schemas import StrictJsonError, read_json_strict
from .validators.evidence_truth_floor import audit_evidence_truth_floor


ARTIFACT_DIR_NAME = "microcosm-substrate"
RELEASE_RECEIPT_REF = "receipts/release/release_export_receipt.json"
PROJECTION_FRESHNESS_RECEIPT_REF = (
    "receipts/first_wave/macro_projection_import_protocol/"
    "exported_projection_import_bundle_validation_result.json"
)
RELEASE_AUTHORIZATION_GATE_ID = "explicit_release_authorization_gate"
RELEASE_CANDIDATE_INVALIDATION_SCHEMA_VERSION = (
    "microcosm_release_candidate_invalidation_v1"
)
RELEASE_ASSURANCE_SCHEMA_VERSION = "microcosm_release_assurance_v2"
DEFAULT_INCLUDE_REFS = (
    ".github",
    ".gitignore",
    "AGENTS.md",
    "AGENT_ROUTES.md",
    "ANTI_PRINCIPLES.md",
    "ARCHITECTURE.md",
    "AXIOMS.md",
    "CLAUDE.md",
    "CONSTITUTION.md",
    "CONTRIBUTING.md",
    "CODEX.md",
    "CURSOR.md",
    "FIRST_ACTION.md",
    "LICENSE",
    "MANIFEST.in",
    "Makefile",
    "NOTICE",
    "ORGANS.md",
    "PRINCIPLES.md",
    "PROVENANCE.md",
    "QUICKSTART.md",
    "RELEASE_DISCIPLINE.md",
    "RELEASE_REVIEW.md",
    "README.md",
    "SECURITY.md",
    "atlas",
    "bootstrap.sh",
    "core",
    "examples",
    "fixtures",
    "paper_modules",
    "pyproject.toml",
    "receipts",
    "scripts",
    "skills",
    "src",
    "standards",
    "tests",
)
STANDALONE_REQUIRED_PUBLIC_REFS = (
    "README.md",
    "LICENSE",
    "NOTICE",
    "PROVENANCE.md",
    "CLAUDE.md",
    "CODEX.md",
    "CURSOR.md",
    "AGENTS.md",
    "AGENT_ROUTES.md",
    "ANTI_PRINCIPLES.md",
    "ARCHITECTURE.md",
    "AXIOMS.md",
    "CONSTITUTION.md",
    "FIRST_ACTION.md",
    "ORGANS.md",
    "PRINCIPLES.md",
    "MANIFEST.in",
    "pyproject.toml",
    "src",
    "tests",
    "Makefile",
    "bootstrap.sh",
    ".github",
    "CONTRIBUTING.md",
    "QUICKSTART.md",
    "RELEASE_DISCIPLINE.md",
    "RELEASE_REVIEW.md",
    "SECURITY.md",
)
LICENSE_NOTICE_REQUIRED_REFS = (
    "LICENSE",
    "NOTICE",
    "PROVENANCE.md",
    "README.md",
    "pyproject.toml",
    "MANIFEST.in",
)
CLAIM_LANGUAGE_REVIEW_PATTERNS = (
    {
        "pattern_id": "private_root_repo_link",
        "category": "source_boundary",
        "pattern": r"github\.com/wcook04/zenith",
        "release_candidate_blocking_if_positive": True,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "whole_system_released",
        "category": "release_boundary",
        "pattern": r"\bthe whole system is released\b",
        "release_candidate_blocking_if_positive": True,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "macro_system_released",
        "category": "release_boundary",
        "pattern": r"\bthe macro system is released\b",
        "release_candidate_blocking_if_positive": True,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "private_root_source_public",
        "category": "source_boundary",
        "pattern": r"\bprivate root source is public\b",
        "release_candidate_blocking_if_positive": True,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "provider_or_institution_affiliation",
        "category": "affiliation_boundary",
        "pattern": r"\b(?:provider-approved|university-backed|affiliated with OpenAI|affiliated with Anthropic|affiliated with Cursor|affiliated with Bristol)\b",
        "release_candidate_blocking_if_positive": False,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "hosted_or_production_security_claim",
        "category": "product_claim_boundary",
        "pattern": r"\b(?:hosted service|hosted product|production security product)\b",
        "release_candidate_blocking_if_positive": False,
        "release_authorization_blocking_if_positive": True,
    },
)
FINANCE_PROMOTION_REVIEW_PATTERNS = (
    {
        "pattern_id": "investment_recommendation",
        "category": "financial_promotion_boundary",
        "pattern": r"\binvestment recommendations?\b",
        "release_candidate_blocking_if_positive": False,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "financial_or_investment_advice",
        "category": "financial_promotion_boundary",
        "pattern": r"\bfinancial or investment advice\b",
        "release_candidate_blocking_if_positive": False,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "trading_system_or_strategy",
        "category": "financial_promotion_boundary",
        "pattern": r"\b(?:trading system|trading strategy)\b",
        "release_candidate_blocking_if_positive": False,
        "release_authorization_blocking_if_positive": True,
    },
    {
        "pattern_id": "buy_sell_hold_trade_recommendation",
        "category": "financial_promotion_boundary",
        "pattern": r"\b(?:recommend(?:s|ed|ing)?|should)\b.{0,80}\b(?:buy|sell|hold|trade)\b",
        "release_candidate_blocking_if_positive": False,
        "release_authorization_blocking_if_positive": True,
    },
)
PUBLICATION_REVIEW_CHECKLISTS = {
    "github_repository": [
        "initialize_public_repo_from_generated_artifact_not_private_root_history",
        "verify_public_remote_points_to_github.com/wcook04/microcosm-substrate",
        "enable_secret_scanning_and_push_protection_where_available",
        "protect_default_branch_and_require_public_ci",
        "publish_SECURITY_md_and_issue_reporting_policy",
        "verify_pages_source_custom_domain_and_https_before_site_launch",
    ],
    "package_registry": [
        "build_from_generated_standalone_artifact",
        "generate_sdist_and_wheel_from_clean_export",
        "run_package_smoke_from_outside_source_root",
        "verify_LICENSE_NOTICE_PROVENANCE_in_package_payload",
        "prefer_trusted_publishing_or_scoped_api_token",
        "generate_or_attach_sbom_before_registry_publication_when_required",
    ],
    "site_and_video": [
        "site_links_resolve_to_standalone_public_repo",
        "site_copy_keeps_research_prototype_and_no_advice_boundaries",
        "walkthrough_media_hides_private_paths_accounts_and_provider_sessions",
        "walkthrough_media_has_rights_or_originality_for_all_visual_audio_assets",
        "platform_ai_or_synthetic_disclosures_completed_when_applicable",
    ],
}
SKIPPED_DIR_NAMES = {
    ".git",
    ".microcosm",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
SKIPPED_ROOT_NAMES = {
    ".DS_Store",
    ".microcosm",
    ".pytest_cache",
    ARTIFACT_DIR_NAME,
}
SKIPPED_FILE_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".lean",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ROOT_FORBIDDEN_PREFIXES = (
    ".codex/",
    ".claude/",
    "obsidian/",
    "state/",
    "tools/",
)
STRONG_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*=\s*['\"][^'\"]{12,}['\"]"),
)
HOST_TEMP_ROOT_NEEDLE = "/private/" + "var/folders/"
HOST_TEMP_SYNTHETIC_EXAMPLE_NEEDLE = HOST_TEMP_ROOT_NEEDLE + "wn/example/"
PUBLIC_EXAMPLE_HOME = "/Users/example"
CONCRETE_HOME_PATH_RE = re.compile(r"/Users/(?!example(?:/|$))[A-Za-z0-9_.-]+")
EXTERNAL_WARNING_CLASSIFICATION_ROWS = (
    {
        "warning_id": "historical_evidence_durability_backlog",
        "classification": "release_candidate_disclosed",
        "release_blocking": False,
        "release_authorization_blocking": False,
        "public_artifact_claim_impact": [],
        "reason": (
            "Historical evidence durability backlog is outside the generated "
            "public artifact claims for inventory, exclusion, runnable smoke, "
            "projection freshness, install mode, and authority."
        ),
    },
    {
        "warning_id": "cap_cartography.json",
        "classification": "macro_governance_backlog_nonblocking",
        "release_blocking": False,
        "release_authorization_blocking": False,
        "public_artifact_claim_impact": [],
        "reason": (
            "Task Ledger cartography view drift is a macro-governance projection "
            "backlog; it does not alter this export's included files, excluded "
            "private state, smoke result, projection freshness, install mode, "
            "or authority ceiling."
        ),
    },
    {
        "warning_id": "cap_census.json",
        "classification": "macro_governance_backlog_nonblocking",
        "release_blocking": False,
        "release_authorization_blocking": False,
        "public_artifact_claim_impact": [],
        "reason": (
            "Task Ledger census view drift is a macro-governance projection "
            "backlog; it does not alter this export's included files, excluded "
            "private state, smoke result, projection freshness, install mode, "
            "or authority ceiling."
        ),
    },
)
RELEASE_STATUS_PROJECTION_PREFIXES = (
    "state/task_ledger/",
    "tools/meta/observability/cli_prompt_trace.py",
    "tools/agent_trace_structurer/",
    "system/server/tests/test_cli_prompt_trace_capsule.py",
    "tools/agent_trace_structurer/trace_size_smoke.py",
)
MACRO_ASSIMILATION_REL_PREFIXES = (
    "examples/macro_projection_import_protocol/",
    "receipts/first_wave/macro_projection_import_protocol/",
    "src/microcosm_core/organs/macro_projection_import_protocol.py",
)
PROJECTION_FINDING_SUBJECT_ID_SAMPLE_LIMIT = 50
PROJECTION_FINDING_SAMPLE_LIMIT = 12


def _sha256_bytes(data: bytes) -> str:
    """
    - Teleology: canonical in-memory digest helper so artifact-payload hashing is reproducible.
    - Guarantee: returns the lowercase hex SHA-256 of the given bytes.
    - Fails: never raises for bytes input; propagates TypeError only if a non-bytes-like object is passed.
    """
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    """
    - Teleology: streaming file digest so per-file inventory sha256 does not load whole files into memory.
    - Guarantee: returns the lowercase hex SHA-256 of the file at path, read in 1 MiB chunks.
    - Fails: missing/unreadable path -> OSError from path.open.
    - Reads: the bytes of the file at the given path.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, possible_parent: Path) -> bool:
    """
    - Teleology: containment test used to keep exports out of the source root and detect escaping symlinks.
    - Guarantee: returns True iff path is relative_to possible_parent, else False; never raises on a non-relative path.
    - Fails: never raises; ValueError from relative_to is caught and folded to False.
    """
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True


def _public_role(rel: str) -> str:
    """
    - Teleology: assign each exported public path a coarse role label for the inventory receipt.
    - Guarantee: returns a stable role string (e.g. public_entry_document, runtime_source, receipt_evidence) for the given posix rel path; unknown tops fall back to public_artifact_member.
    - Fails: never raises; always returns one of the fixed role strings.
    """
    top = rel.split("/", 1)[0]
    if top == ".github":
        return "ci_workflow"
    if rel == "Makefile":
        return "command_surface"
    if rel == "MANIFEST.in":
        return "package_manifest"
    if rel.endswith("pyproject.toml"):
        return "package_metadata"
    if rel in {
        "README.md",
        "AGENTS.md",
        "AGENT_ROUTES.md",
        "ANTI_PRINCIPLES.md",
        "ARCHITECTURE.md",
        "AXIOMS.md",
        "CLAUDE.md",
        "CONSTITUTION.md",
        "CONTRIBUTING.md",
        "CODEX.md",
        "CURSOR.md",
        "PRINCIPLES.md",
        "ORGANS.md",
        "QUICKSTART.md",
        "SECURITY.md",
        "LICENSE",
        "NOTICE",
        "PROVENANCE.md",
    }:
        return "public_entry_document"
    if top == "atlas":
        return "entry_packet"
    if top == "core":
        return "authority_or_registry"
    if top == "examples":
        return "example_evidence"
    if top == "fixtures":
        return "fixture"
    if top == "paper_modules":
        return "public_paper_module"
    if top == "receipts":
        return "receipt_evidence"
    if top == "scripts":
        return "utility_script"
    if top == "skills":
        return "public_skill"
    if top == "src":
        return "runtime_source"
    if top == "standards":
        return "public_standard"
    if top == "tests":
        return "test_or_regression_guard"
    return "public_artifact_member"


def _skip_reason(rel: Path, *, is_dir: bool) -> str | None:
    """
    - Teleology: single source of truth for why a tree entry is excluded from the export (caches, residue, bytecode, OS metadata).
    - Guarantee: returns a reason string when the rel path matches a skip rule, else None; pure path classification with no I/O.
    - Fails: never raises; returns None for paths that are not skip candidates.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness.
    """
    parts = rel.parts
    if not parts:
        return None
    if parts[0] in SKIPPED_ROOT_NAMES:
        return "root_local_or_nested_release_residue"
    if any(part in SKIPPED_DIR_NAMES for part in parts):
        return "cache_or_build_directory"
    if any(part.endswith(".egg-info") for part in parts):
        return "package_build_metadata"
    if not is_dir and rel.suffix in SKIPPED_FILE_SUFFIXES:
        return "bytecode_cache"
    if not is_dir and rel.name == ".DS_Store":
        return "os_metadata_file"
    return None


def _source_residue_rows(root: Path) -> list[dict[str, str]]:
    """
    - Teleology: pre-seed the exclusion ledger with local/nested-release residue roots that must never be exported.
    - Guarantee: returns excluded-row dicts (status=excluded, reason=root_local_or_nested_release_residue) for each SKIPPED_ROOT_NAMES entry that exists under root.
    - Fails: never raises; returns [] when no residue roots exist.
    - Reads: existence of SKIPPED_ROOT_NAMES entries directly under root.
    """
    rows: list[dict[str, str]] = []
    for name in sorted(SKIPPED_ROOT_NAMES):
        candidate = root / name
        if candidate.exists():
            rows.append(
                {
                    "path": name,
                    "status": "excluded",
                    "reason": "root_local_or_nested_release_residue",
                }
            )
    return rows


def _iter_allowed_files(root: Path) -> tuple[list[Path], list[dict[str, str]], list[str]]:
    """
    - Teleology: walk the source root under the public allowlist, deciding per-entry keep/exclude so only public-safe material reaches the artifact.
    - Guarantee: returns (kept files, excluded rows, missing include refs); symlinks, skip-rule matches, and receipt private-path content are excluded with a reason, not copied.
    - Fails: never raises for normal trees; OS errors from os.walk on an unreadable subtree propagate.
    - Reads: DEFAULT_INCLUDE_REFS under root plus per-file content for receipt private-path exclusion.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond its skip/exclusion checks, release, or whole-system correctness.
    - When-needed: tracing why a file is included or excluded from the generated export.
    - Escalates-to: _skip_reason / _source_receipt_private_path_exclusion and build_release_export inventory_receipt.
    """
    files: list[Path] = []
    excluded: list[dict[str, str]] = _source_residue_rows(root)
    missing: list[str] = []
    for include_ref in DEFAULT_INCLUDE_REFS:
        source = root / include_ref
        if not source.exists():
            missing.append(include_ref)
            continue
        if source.is_symlink():
            excluded.append(
                {
                    "path": include_ref,
                    "status": "excluded",
                    "reason": "symlink_not_exported",
                }
            )
            continue
        if source.is_file():
            reason = _skip_reason(Path(include_ref), is_dir=False)
            content_reason = (
                _source_receipt_private_path_exclusion(source, root)
                if reason is None
                else None
            )
            if content_reason is not None:
                excluded.append(
                    {"path": include_ref, "status": "excluded", "reason": content_reason}
                )
            elif reason is None:
                files.append(source)
            else:
                excluded.append({"path": include_ref, "status": "excluded", "reason": reason})
            continue
        for current_dir, dirnames, filenames in os.walk(source):
            current = Path(current_dir)
            kept_dirnames: list[str] = []
            for dirname in sorted(dirnames):
                path = current / dirname
                rel = path.relative_to(root)
                if path.is_symlink():
                    excluded.append(
                        {
                            "path": rel.as_posix(),
                            "status": "excluded",
                            "reason": "symlink_not_exported",
                        }
                    )
                    continue
                reason = _skip_reason(rel, is_dir=True)
                if reason is not None:
                    excluded.append(
                        {
                            "path": rel.as_posix(),
                            "status": "excluded",
                            "reason": reason,
                        }
                    )
                    continue
                kept_dirnames.append(dirname)
            dirnames[:] = kept_dirnames

            for filename in sorted(filenames):
                path = current / filename
                rel = path.relative_to(root)
                if path.is_symlink():
                    excluded.append(
                        {
                            "path": rel.as_posix(),
                            "status": "excluded",
                            "reason": "symlink_not_exported",
                        }
                    )
                    continue
                reason = _skip_reason(rel, is_dir=False)
                if reason is not None:
                    excluded.append(
                        {
                            "path": rel.as_posix(),
                            "status": "excluded",
                            "reason": reason,
                        }
                    )
                    continue
                content_reason = _source_receipt_private_path_exclusion(path, root)
                if content_reason is not None:
                    excluded.append(
                        {
                            "path": rel.as_posix(),
                            "status": "excluded",
                            "reason": content_reason,
                        }
                    )
                    continue
                files.append(path)
    return files, excluded, missing


def _copy_allowed_files(
    files: list[Path],
    *,
    root: Path,
    target: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    - Teleology: materialize the kept files into the artifact tree and build the per-file inventory, redacting concrete home paths in source_modules.
    - Guarantee: each allowed file is copied to target/<rel>; text files under a source_modules path get concrete /Users/<name> rewritten to /Users/example; returns sorted inventory rows (path/role/size/sha256) and sorted home-redaction rows.
    - Fails: unwritable destination or unreadable source -> OSError; binary/large files are copied verbatim without redaction.
    - Reads: the source files in `files`; Writes: redacted-or-verbatim copies under target.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond home-path redaction, release, or whole-system correctness.
    """
    inventory: list[dict[str, Any]] = []
    home_redaction_rows: list[dict[str, Any]] = []
    for source in files:
        rel = source.relative_to(root).as_posix()
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = _read_text_if_small(source)
        if text is not None and "source_modules" in Path(rel).parts:
            redacted_text, redaction_count = CONCRETE_HOME_PATH_RE.subn(
                PUBLIC_EXAMPLE_HOME,
                text,
            )
            destination.write_text(redacted_text, encoding="utf-8")
            shutil.copystat(source, destination)
            if redaction_count:
                home_redaction_rows.append(
                    {
                        "path": rel,
                        "concrete_home_path_replacement_count": redaction_count,
                        "replacement": PUBLIC_EXAMPLE_HOME,
                        "body_in_receipt": False,
                    }
                )
        else:
            shutil.copy2(source, destination)
        stat = destination.stat()
        inventory.append(
            {
                "path": rel,
                "role": _public_role(rel),
                "size_bytes": stat.st_size,
                "sha256": _sha256_file(destination),
            }
        )
    return (
        sorted(inventory, key=lambda row: row["path"]),
        sorted(home_redaction_rows, key=lambda row: row["path"]),
    )


def _artifact_payload_hash(inventory: list[dict[str, Any]]) -> str:
    """
    - Teleology: bind the whole inventory to one digest so the candidate artifact is hash-identifiable.
    - Guarantee: returns the SHA-256 of the JSON-serialized inventory (ascii, sorted keys); identical inventories yield identical hashes.
    - Fails: non-JSON-serializable inventory contents -> TypeError from json.dumps.
    """
    serialized = json.dumps(inventory, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return _sha256_bytes(serialized)


def _inventory_covers_ref(inventory_paths: set[str], ref: str) -> bool:
    """
    - Teleology: decide whether a required public ref is present in the exported inventory (file or directory prefix).
    - Guarantee: returns True iff the normalized ref equals an inventory path or is a directory prefix of one.
    - Fails: never raises; returns False when no inventory path covers the ref.
    - Reads: the set of exported inventory paths.
    """
    normalized = ref.rstrip("/")
    return normalized in inventory_paths or any(
        path.startswith(f"{normalized}/") for path in inventory_paths
    )


def _read_text_if_small(path: Path, *, max_bytes: int = 2_000_000) -> str | None:
    """
    - Teleology: bounded text reader so content scans skip binaries and oversized files.
    - Guarantee: returns decoded UTF-8 text for files with a TEXT_SUFFIXES suffix and size <= max_bytes, else None.
    - Fails: never raises on decode failure (UnicodeDecodeError -> None); OSError from stat on a vanished path propagates.
    - Reads: the text of the candidate path when small and text-suffixed.
    """
    if path.suffix not in TEXT_SUFFIXES:
        return None
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _iter_artifact_paths(target: Path) -> Iterator[Path]:
    """Yield artifact paths deterministically without materializing the tree.

    - Teleology: deterministic recursive walk of the artifact so residue/secret/symlink scans see a stable order without materializing a list.
    - Guarantee: yields every path under target in sorted-name, parent-before-child order; symlinked dirs are not descended (follow_symlinks=False).
    - Fails: never raises; an unreadable directory yields nothing for that subtree (OSError swallowed).
    - Reads: directory entries under target.
    """

    try:
        entries = sorted(os.scandir(target), key=lambda entry: entry.name)
    except OSError:
        return

    for entry in entries:
        path = Path(entry.path)
        yield path
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError:
            is_dir = False
        if is_dir:
            yield from _iter_artifact_paths(path)


def _iter_artifact_files(target: Path) -> Iterator[Path]:
    """
    - Teleology: file-only view of the artifact walk for content scans.
    - Guarantee: yields only non-symlink regular files under target, in _iter_artifact_paths order.
    - Fails: never raises; non-files and symlinks are skipped.
    - Reads: the artifact tree under target.
    """
    for path in _iter_artifact_paths(target):
        if path.is_symlink():
            continue
        if path.is_file():
            yield path


def _source_receipt_private_path_exclusion(path: Path, root: Path) -> str | None:
    """
    - Teleology: source-custody guard that keeps receipts carrying the absolute source root or non-synthetic host temp paths out of the export.
    - Guarantee: returns receipt_absolute_source_root_excluded or receipt_host_temp_path_excluded when a receipts/* text file leaks those needles, else None.
    - Fails: never raises; non-receipt paths, binaries, and clean receipts return None.
    - Reads: the text body of the candidate receipts/* file and the source root posix string.
    - Non-goal: does not authorize source-body export, public-safe equivalence beyond this needle check, release, or whole-system correctness.
    """
    rel = path.relative_to(root)
    if not rel.parts or rel.parts[0] != "receipts":
        return None
    text = _read_text_if_small(path)
    if text is None:
        return None
    if root.as_posix() in text:
        return "receipt_absolute_source_root_excluded"
    if HOST_TEMP_ROOT_NEEDLE in text and HOST_TEMP_SYNTHETIC_EXAMPLE_NEEDLE not in text:
        return "receipt_host_temp_path_excluded"
    return None


def _strong_private_path_hits(target: Path, *, source_root: Path) -> list[dict[str, str]]:
    """
    - Teleology: post-copy private-path leak detector over the materialized artifact (source root, source parent, operator home, host temp).
    - Guarantee: returns hit rows (path + public-redacted needle + kind) for every artifact text file containing a private needle; needle values in the receipt are already redacted placeholders.
    - Fails: never raises; binaries and clean files contribute no hits.
    - Reads: every artifact text file plus source_root, its parent, and Path.home() posix strings.
    - Non-goal: does not authorize release; absence of hits is a bounded scan, not a complete privacy audit.
    """
    hits: list[dict[str, str]] = []
    private_needles: list[tuple[str, str, str]] = []
    source_root_text = source_root.as_posix()
    if source_root_text:
        private_needles.append(
            (source_root_text, "<source-root>", "absolute_source_root")
        )
    source_parent_text = source_root.parent.as_posix()
    if source_parent_text and source_parent_text not in {"/", source_root_text}:
        private_needles.append(
            (source_parent_text, "<source-parent>", "absolute_source_parent")
        )
    home_text = Path.home().as_posix()
    if home_text and home_text not in {"/", source_root_text, source_parent_text}:
        private_needles.append(
            (home_text, "<operator-home>", "operator_home_root")
        )
    for path in _iter_artifact_files(target):
        rel = path.relative_to(target).as_posix()
        text = _read_text_if_small(path)
        if text is None:
            continue
        for needle, public_needle, kind in private_needles:
            if needle in text:
                hits.append({"path": rel, "needle": public_needle, "kind": kind})
        if HOST_TEMP_ROOT_NEEDLE in text and HOST_TEMP_SYNTHETIC_EXAMPLE_NEEDLE not in text:
            hits.append({"path": rel, "needle": HOST_TEMP_ROOT_NEEDLE, "kind": "host_temp_root"})
    return hits


def _strong_secret_hits(target: Path) -> list[dict[str, str]]:
    """
    - Teleology: bounded strong-secret pattern scan (private keys, inline api/secret assignments) over the artifact.
    - Guarantee: returns rows (path + matched pattern, body_in_receipt=False) for every artifact text file matching a STRONG_SECRET_PATTERNS regex.
    - Fails: never raises; raw secret bodies are never placed in the returned rows.
    - Reads: every artifact text file.
    - Non-goal: does not authorize release and is not a complete secret audit; it is a bounded pattern pass.
    """
    hits: list[dict[str, str]] = []
    for path in _iter_artifact_files(target):
        rel = path.relative_to(target).as_posix()
        text = _read_text_if_small(path)
        if text is None:
            continue
        for pattern in STRONG_SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(
                    {
                        "path": rel,
                        "pattern": pattern.pattern,
                        "body_in_receipt": False,
                    }
                )
    return hits


def _artifact_residue_violations(target: Path) -> list[dict[str, str]]:
    """
    - Teleology: prove the materialized artifact carries no forbidden private-root, generated-state, nested-self-export, cache, or bytecode residue.
    - Guarantee: returns a violation row (path + reason) for every artifact path matching a residue rule; empty list means no residue found.
    - Fails: never raises; pure path classification over the artifact walk.
    - Reads: the artifact tree under target.
    """
    violations: list[dict[str, str]] = []
    for path in _iter_artifact_paths(target):
        rel = path.relative_to(target)
        rel_text = rel.as_posix()
        parts = rel.parts
        if not parts:
            continue
        if any(rel_text.startswith(prefix) for prefix in ROOT_FORBIDDEN_PREFIXES):
            violations.append({"path": rel_text, "reason": "forbidden_private_root"})
        if ".microcosm" in parts:
            violations.append({"path": rel_text, "reason": "generated_microcosm_state"})
        if parts[0] == ARTIFACT_DIR_NAME:
            violations.append({"path": rel_text, "reason": "nested_self_export"})
        if rel.name == ".DS_Store":
            violations.append({"path": rel_text, "reason": "os_metadata_file"})
        if any(part in {".pytest_cache", "__pycache__"} for part in parts):
            violations.append({"path": rel_text, "reason": "cache_or_bytecode"})
        if rel.suffix in SKIPPED_FILE_SUFFIXES:
            violations.append({"path": rel_text, "reason": "bytecode_cache"})
        if any(part.endswith(".egg-info") for part in parts):
            violations.append({"path": rel_text, "reason": "package_build_metadata"})
    return violations


def _artifact_symlink_refs(target: Path) -> list[dict[str, Any]]:
    """
    - Teleology: enumerate symlinks in the artifact and whether each resolves inside the artifact, for the standalone-severance gate.
    - Guarantee: returns one row per symlink (path + target_within_artifact bool + body_in_receipt=False); any symlink at all is later treated as a severance blocker.
    - Fails: target.resolve(strict=True) on a missing artifact root -> FileNotFoundError; per-link resolve errors fold target_within_artifact to False.
    - Reads: symlink entries under target and their resolved targets.
    """
    rows: list[dict[str, Any]] = []
    target_root = target.resolve(strict=True)
    for path in _iter_artifact_paths(target):
        if not path.is_symlink():
            continue
        rel = path.relative_to(target).as_posix()
        try:
            resolved = path.resolve(strict=False)
            target_within_artifact = _is_relative_to(resolved, target_root)
        except OSError:
            target_within_artifact = False
        rows.append(
            {
                "path": rel,
                "target_within_artifact": target_within_artifact,
                "body_in_receipt": False,
            }
        )
    return rows


def _standalone_severance_receipt(
    target: Path,
    *,
    inventory: list[dict[str, Any]],
    missing_include_refs: list[str],
    exclusion_receipt: dict[str, Any],
    authority_receipt: dict[str, Any],
    runnable_receipt: dict[str, Any],
    install_smoke_receipt: dict[str, Any],
    projection_freshness_receipt: dict[str, Any],
) -> dict[str, Any]:
    """
    - Teleology: source-custody receipt proving the generated tree is a self-contained public folder (required refs present, no residue/symlink/private/secret leak, gates pass).
    - Guarantee: returns a microcosm_standalone_severance_receipt_v1 dict with status pass iff blocking_codes is empty; claim_level is install-verified only when install smoke passed.
    - Fails: never raises; defects surface as blocking_codes and status=blocked, not exceptions.
    - Reads: inventory, exclusion/authority/runnable/install/projection receipts, and the artifact symlink set.
    - Non-goal: per its own anti_claim, proves only bounded standalone shape; not publication authority or private-macro equivalence.
    - Escalates-to: build_release_export receipt['standalone_severance_receipt'] and the standalone test guards.
    """
    inventory_paths = {str(row["path"]) for row in inventory}
    required_missing = [
        ref
        for ref in STANDALONE_REQUIRED_PUBLIC_REFS
        if not _inventory_covers_ref(inventory_paths, ref)
    ]
    required_present = [
        ref
        for ref in STANDALONE_REQUIRED_PUBLIC_REFS
        if _inventory_covers_ref(inventory_paths, ref)
    ]
    artifact_residue_violations = list(
        exclusion_receipt.get("artifact_residue_violations") or []
    )
    forbidden_root_prefix_hits = [
        row
        for row in artifact_residue_violations
        if row.get("reason") == "forbidden_private_root"
    ]
    artifact_symlink_refs = _artifact_symlink_refs(target)
    escaping_symlink_refs = [
        row
        for row in artifact_symlink_refs
        if row.get("target_within_artifact") is not True
    ]
    private_path_hits = list(exclusion_receipt.get("private_path_hits") or [])
    strong_secret_hits = list(exclusion_receipt.get("strong_secret_hits") or [])
    bounded_secret = exclusion_receipt.get("bounded_secret_exclusion_scan") or {}

    blocking_codes: list[str] = []
    if required_missing:
        blocking_codes.append("STANDALONE_REQUIRED_PUBLIC_REFS_MISSING")
    if missing_include_refs:
        blocking_codes.append("STANDALONE_INCLUDE_REFS_MISSING")
    if artifact_residue_violations:
        blocking_codes.append("STANDALONE_ARTIFACT_RESIDUE_PRESENT")
    if forbidden_root_prefix_hits:
        blocking_codes.append("STANDALONE_FORBIDDEN_ROOT_PREFIX_PRESENT")
    if artifact_symlink_refs:
        blocking_codes.append("STANDALONE_ARTIFACT_SYMLINK_PRESENT")
    if escaping_symlink_refs:
        blocking_codes.append("STANDALONE_ARTIFACT_SYMLINK_ESCAPE")
    if private_path_hits:
        blocking_codes.append("STANDALONE_PRIVATE_PATH_PRESENT")
    if strong_secret_hits:
        blocking_codes.append("STANDALONE_STRONG_SECRET_PATTERN_PRESENT")
    if bounded_secret.get("status") != "pass":
        blocking_codes.append("STANDALONE_SECRET_SCAN_BLOCKED")
    if projection_freshness_receipt.get("status") != "pass":
        blocking_codes.append("STANDALONE_PROJECTION_FRESHNESS_BLOCKED")
    if runnable_receipt.get("status") not in {"pass", "not_run"}:
        blocking_codes.append("STANDALONE_RUNNABLE_SMOKE_BLOCKED")
    if install_smoke_receipt.get("status") not in {"pass", "not_run"}:
        blocking_codes.append("STANDALONE_INSTALL_SMOKE_BLOCKED")

    install_verified = install_smoke_receipt.get("status") == "pass"
    return {
        "schema_version": "microcosm_standalone_severance_receipt_v1",
        "status": "pass" if not blocking_codes else "blocked",
        "artifact_dir": ARTIFACT_DIR_NAME,
        "mode": "generated_standalone_folder",
        "claim_level": (
            "standalone_install_verified"
            if install_verified
            else "standalone_shape_verified_without_install_claim"
        ),
        "required_public_entry_refs": list(STANDALONE_REQUIRED_PUBLIC_REFS),
        "required_public_entry_refs_present": required_present,
        "required_public_entry_refs_missing": required_missing,
        "missing_include_refs": list(missing_include_refs),
        "forbidden_root_prefix_hits": forbidden_root_prefix_hits,
        "artifact_residue_violations": artifact_residue_violations,
        "artifact_symlink_refs": artifact_symlink_refs,
        "escaping_symlink_refs": escaping_symlink_refs,
        "private_path_hit_count": len(private_path_hits),
        "strong_secret_hit_count": len(strong_secret_hits),
        "bounded_secret_scan_status": bounded_secret.get("status"),
        "projection_freshness_status": projection_freshness_receipt.get("status"),
        "runnable_smoke_status": runnable_receipt.get("status"),
        "install_smoke_status": install_smoke_receipt.get("status"),
        "install_smoke_supports_standalone_run": install_verified,
        "authority_boundary": {
            "release_authorized": authority_receipt.get("release_authorized"),
            "publish_authorized": authority_receipt.get("publish_authorized"),
            "hosted_launch_authorized": authority_receipt.get(
                "hosted_launch_authorized"
            ),
            "provider_calls_authorized": authority_receipt.get(
                "provider_calls_authorized"
            ),
            "source_files_mutation_authorized": authority_receipt.get(
                "source_files_mutation_authorized"
            ),
            "private_data_equivalence_authorized": authority_receipt.get(
                "private_data_equivalence_authorized"
            ),
            "supported_public_mode": authority_receipt.get("supported_public_mode"),
        },
        "blocking_codes": blocking_codes,
        "anti_claim": (
            "This receipt proves only that the generated artifact has the bounded "
            "standalone public-tree shape described here. It is not publication "
            "authority or proof of equivalence to private macro-system state."
        ),
    }


def _flatten_data_file_refs(pyproject: dict[str, Any]) -> set[str]:
    """
    - Teleology: collect declared setuptools data-file refs so LICENSE/NOTICE/PROVENANCE packaging coverage can be checked.
    - Guarantee: returns the set of string data-file patterns declared under tool.setuptools.data-files; missing/malformed tables yield an empty set.
    - Fails: never raises; non-dict/non-list shapes are skipped defensively.
    - Reads: the parsed pyproject tool.setuptools.data-files mapping.
    """
    tool = pyproject.get("tool") if isinstance(pyproject.get("tool"), dict) else {}
    setuptools = tool.get("setuptools") if isinstance(tool.get("setuptools"), dict) else {}
    data_files = (
        setuptools.get("data-files")
        if isinstance(setuptools.get("data-files"), dict)
        else {}
    )
    refs: set[str] = set()
    for patterns in data_files.values():
        if not isinstance(patterns, list):
            continue
        for pattern in patterns:
            if isinstance(pattern, str):
                refs.add(pattern)
    return refs


def _pyproject_payload(target: Path) -> dict[str, Any]:
    """
    - Teleology: tolerant loader for the exported pyproject so materials/license checks have its metadata.
    - Guarantee: returns the parsed pyproject.toml dict, or {} when the file is absent or fails to parse.
    - Fails: never raises; OSError and TOMLDecodeError are caught and folded to {}.
    - Reads: target/pyproject.toml.
    """
    path = target / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _materials_ledger(
    target: Path,
    *,
    inventory: list[dict[str, Any]],
    artifact: dict[str, Any],
) -> dict[str, Any]:
    """
    - Teleology: source-custody/materials receipt binding LICENSE-NOTICE-PROVENANCE chain, license expression, dependency summary, and SBOM status.
    - Guarantee: returns a microcosm_public_materials_ledger_v1 dict; license_notice status passes only when required refs are present, license is Apache-2.0, and LICENSE/NOTICE/PROVENANCE are export-or-data covered.
    - Fails: never raises; missing material or wrong license -> status=blocked; SBOM is reported not_generated, never claimed complete.
    - Reads: inventory paths and target/pyproject.toml metadata.
    - Non-goal: does not authorize release or claim a complete dependency SBOM / transitive license review.
    - Escalates-to: _pyproject_payload / _flatten_data_file_refs and the publication package-registry checklist.
    """
    inventory_paths = {str(row["path"]) for row in inventory}
    required_missing = [
        ref
        for ref in LICENSE_NOTICE_REQUIRED_REFS
        if not _inventory_covers_ref(inventory_paths, ref)
    ]
    required_present = [
        ref
        for ref in LICENSE_NOTICE_REQUIRED_REFS
        if _inventory_covers_ref(inventory_paths, ref)
    ]
    pyproject = _pyproject_payload(target)
    project = (
        pyproject.get("project") if isinstance(pyproject.get("project"), dict) else {}
    )
    build_system = (
        pyproject.get("build-system")
        if isinstance(pyproject.get("build-system"), dict)
        else {}
    )
    optional_dependencies = (
        project.get("optional-dependencies")
        if isinstance(project.get("optional-dependencies"), dict)
        else {}
    )
    data_file_refs = _flatten_data_file_refs(pyproject)
    license_expression = project.get("license")
    if isinstance(license_expression, dict):
        license_expression = license_expression.get("text") or license_expression.get("file")
    license_notice_data_refs = {
        ref: ref in data_file_refs or _inventory_covers_ref(inventory_paths, ref)
        for ref in ("LICENSE", "NOTICE", "PROVENANCE.md")
    }
    license_notice_status = (
        "pass"
        if not required_missing
        and str(license_expression or "") == "Apache-2.0"
        and all(license_notice_data_refs.values())
        else "blocked"
    )
    role_counts = Counter(str(row["role"]) for row in inventory)
    top_level_counts = Counter(str(row["path"]).split("/", 1)[0] for row in inventory)
    runtime_dependencies = project.get("dependencies")
    if not isinstance(runtime_dependencies, list):
        runtime_dependencies = []
    build_requires = build_system.get("requires")
    if not isinstance(build_requires, list):
        build_requires = []
    optional_dependency_counts = {
        str(group): len(values) if isinstance(values, list) else 0
        for group, values in optional_dependencies.items()
    }
    return {
        "schema_version": "microcosm_public_materials_ledger_v1",
        "status": "pass" if license_notice_status == "pass" else "blocked",
        "artifact_payload_hash_sha256": artifact.get("artifact_payload_hash_sha256"),
        "required_license_notice_refs": list(LICENSE_NOTICE_REQUIRED_REFS),
        "required_license_notice_refs_present": required_present,
        "required_license_notice_refs_missing": required_missing,
        "license_notice_chain": {
            "status": license_notice_status,
            "license_expression": license_expression,
            "license_files": project.get("license-files") or [],
            "required_refs_in_export_or_package_data": license_notice_data_refs,
            "copyright_notice_ref": "NOTICE",
            "authorship_and_no_affiliation_ref": "PROVENANCE.md",
        },
        "inventory_role_counts": dict(sorted(role_counts.items())),
        "top_level_material_counts": dict(sorted(top_level_counts.items())),
        "dependency_summary": {
            "runtime_dependency_count": len(runtime_dependencies),
            "runtime_dependencies": sorted(str(dep) for dep in runtime_dependencies),
            "optional_dependency_group_counts": dict(
                sorted(optional_dependency_counts.items())
            ),
            "build_requires": sorted(str(dep) for dep in build_requires),
            "dependency_scope": (
                "pyproject metadata only; transitive dependency license review "
                "and SBOM are separate publication checks."
            ),
        },
        "sbom": {
            "status": "not_generated",
            "required_before_registry_publication": "when operator chooses package registry publication or downstream policy requires it",
            "anti_claim": "This export receipt does not claim a complete dependency SBOM.",
        },
        "body_in_receipt": False,
    }


def _artifact_publication_history_receipt(target: Path) -> dict[str, Any]:
    """
    - Teleology: source-custody guard that the artifact carries no private git history (.git/.gitmodules) and must seed a fresh public repo.
    - Guarantee: returns a microcosm_publication_history_receipt_v1 dict; status passes iff no git metadata refs are found in the artifact.
    - Fails: never raises; any .git/.gitmodules ref -> status=blocked with source_private_history_exported True (first 20 refs sampled).
    - Reads: the artifact path tree for git-metadata refs.
    - Non-goal: does not authorize publication; it only names the fresh-public-repo rule.
    """
    git_metadata_refs: list[str] = []
    for path in _iter_artifact_paths(target):
        rel = path.relative_to(target).as_posix()
        if rel == ".git" or rel.startswith(".git/") or rel == ".gitmodules":
            git_metadata_refs.append(rel)
    return {
        "schema_version": "microcosm_publication_history_receipt_v1",
        "status": "pass" if not git_metadata_refs else "blocked",
        "artifact_contains_git_metadata": bool(git_metadata_refs),
        "git_metadata_refs": git_metadata_refs[:20],
        "git_metadata_ref_overflow_count": max(0, len(git_metadata_refs) - 20),
        "source_private_history_exported": bool(git_metadata_refs),
        "fresh_public_repository_required": True,
        "required_publication_rule": (
            "Initialize the public repository from the generated standalone "
            "artifact or an equivalent clean export, not by pushing the private "
            "macro-root repository history."
        ),
        "recommended_fresh_repo_sequence": [
            "generate_standalone_export",
            "scan_exported_artifact",
            "initialize_new_public_repository_from_artifact",
            "set_public_remote_to_github.com/wcook04/microcosm-substrate",
            "push_clean_initial_history_after_operator_release_authorization",
        ],
        "body_in_receipt": False,
    }


def _hit_boundary_context(text: str, *, start: int, end: int) -> str:
    """
    - Teleology: classify a review-pattern match as a suspect positive claim or an explicit boundary/anti-claim context, to suppress false positives.
    - Guarantee: returns boundary_or_anti_claim_context when a negation/boundary marker precedes or surrounds the match, else suspect_positive_claim.
    - Fails: never raises; pure substring window classification.
    - Reads: the surrounding text window of the matched span.
    """
    before = text[max(0, start - 120) : start].lower()
    window = text[max(0, start - 120) : min(len(text), end + 120)].lower()
    boundary_markers = (
        "not",
        "no ",
        "never",
        "without",
        "does not",
        "do not",
        "cannot",
        "anti_claim",
        "forbidden",
        "boundary",
    )
    if any(marker in before for marker in boundary_markers):
        return "boundary_or_anti_claim_context"
    if "not a" in window or "not an" in window:
        return "boundary_or_anti_claim_context"
    return "suspect_positive_claim"


def _scan_review_patterns(
    target: Path,
    patterns: tuple[dict[str, Any], ...],
    *,
    schema_version: str,
    scan_id: str,
) -> dict[str, Any]:
    """
    - Teleology: scan the artifact for claim-language or finance-promotion patterns and split hits into release-candidate vs authorization blocking.
    - Guarantee: returns a scan dict (given schema/scan_id) with status pass iff release_candidate_blocking_hit_count is zero; boundary-context hits are reported but non-blocking, bodies excluded.
    - Fails: never raises; matches in anti-claim context do not block; hits list is capped at 50 with an overflow count.
    - Reads: every artifact text file against the supplied pattern rows.
    - Non-goal: does not authorize release; per its anti_claim, boundary-context hits neither authorize nor block by themselves.
    """
    hits: list[dict[str, Any]] = []
    for path in _iter_artifact_files(target):
        rel = path.relative_to(target).as_posix()
        text = _read_text_if_small(path)
        if text is None:
            continue
        for pattern_row in patterns:
            regex = re.compile(str(pattern_row["pattern"]), flags=re.IGNORECASE)
            for match in regex.finditer(text):
                context = _hit_boundary_context(
                    text,
                    start=match.start(),
                    end=match.end(),
                )
                positive = context == "suspect_positive_claim"
                hits.append(
                    {
                        "path": rel,
                        "line": text.count("\n", 0, match.start()) + 1,
                        "pattern_id": pattern_row["pattern_id"],
                        "category": pattern_row["category"],
                        "context": context,
                        "release_candidate_blocking": (
                            positive
                            and pattern_row.get(
                                "release_candidate_blocking_if_positive"
                            )
                            is True
                        ),
                        "release_authorization_blocking": (
                            positive
                            and pattern_row.get(
                                "release_authorization_blocking_if_positive"
                            )
                            is True
                        ),
                        "body_in_receipt": False,
                    }
                )
    release_candidate_blocking_count = sum(
        1 for row in hits if row["release_candidate_blocking"] is True
    )
    release_authorization_blocking_count = sum(
        1 for row in hits if row["release_authorization_blocking"] is True
    )
    suspect_positive_count = sum(
        1 for row in hits if row["context"] == "suspect_positive_claim"
    )
    return {
        "schema_version": schema_version,
        "scan_id": scan_id,
        "status": "pass" if release_candidate_blocking_count == 0 else "blocked",
        "suspect_positive_hit_count": suspect_positive_count,
        "boundary_context_hit_count": len(hits) - suspect_positive_count,
        "release_candidate_blocking_hit_count": release_candidate_blocking_count,
        "release_authorization_blocking_hit_count": (
            release_authorization_blocking_count
        ),
        "hit_count": len(hits),
        "hits": hits[:50],
        "hit_overflow_count": max(0, len(hits) - 50),
        "anti_claim": (
            "Pattern hits in explicit boundary or anti-claim contexts are "
            "reported for review but do not by themselves authorize or block "
            "the export candidate."
        ),
        "body_in_receipt": False,
    }


def _privacy_review_receipt(
    *,
    exclusion_receipt: dict[str, Any],
    authority_receipt: dict[str, Any],
) -> dict[str, Any]:
    """
    - Teleology: fold the exclusion receipt into a bounded artifact privacy review for the release-assurance bundle.
    - Guarantee: returns a microcosm_privacy_release_review_receipt_v1 dict; status passes iff no private-path hits, no strong-secret hits, and bounded secret scan passed.
    - Fails: never raises; any of those conditions -> status=blocked with the matching PRIVACY_* code.
    - Reads: exclusion_receipt private-path/secret hit lists and authority_receipt flags.
    - Non-goal: bounded artifact scan only; not a complete personal-data audit of any private workspace.
    """
    bounded_secret = exclusion_receipt.get("bounded_secret_exclusion_scan") or {}
    private_path_hits = list(exclusion_receipt.get("private_path_hits") or [])
    strong_secret_hits = list(exclusion_receipt.get("strong_secret_hits") or [])
    blocking_codes: list[str] = []
    if private_path_hits:
        blocking_codes.append("PRIVACY_PRIVATE_PATH_HIT")
    if strong_secret_hits:
        blocking_codes.append("PRIVACY_STRONG_SECRET_PATTERN")
    if bounded_secret.get("status") != "pass":
        blocking_codes.append("PRIVACY_BOUNDED_SECRET_SCAN_BLOCKED")
    return {
        "schema_version": "microcosm_privacy_release_review_receipt_v1",
        "status": "pass" if not blocking_codes else "blocked",
        "private_path_hit_count": len(private_path_hits),
        "strong_secret_hit_count": len(strong_secret_hits),
        "bounded_secret_scan_status": bounded_secret.get("status"),
        "private_data_equivalence_authorized": authority_receipt.get(
            "private_data_equivalence_authorized"
        ),
        "hosted_service_privacy_policy_required": (
            authority_receipt.get("hosted_launch_authorized") is True
        ),
        "operator_review_required_before_hosted_launch": True,
        "blocking_codes": blocking_codes,
        "anti_claim": (
            "This is a bounded artifact privacy scan over the generated export. "
            "It is not a complete personal-data audit of any private workspace."
        ),
        "body_in_receipt": False,
    }


def _operator_publication_checklists() -> dict[str, Any]:
    """
    - Teleology: surface the operator-review publication checklists (github/package/site) as not-yet-run gates.
    - Guarantee: returns a microcosm_operator_publication_checklists_v1 dict with release_authorized/publish_authorized False and every checklist marked not_run_operator_review_required.
    - Fails: never raises; constant projection of PUBLICATION_REVIEW_CHECKLISTS.
    - Non-goal: checklist presence does not mean any publication surface was reviewed or launched.
    """
    return {
        "schema_version": "microcosm_operator_publication_checklists_v1",
        "status": "operator_review_required",
        "release_authorized": False,
        "publish_authorized": False,
        "checklists": {
            key: {
                "status": "not_run_operator_review_required",
                "required_before_publication": True,
                "items": list(items),
            }
            for key, items in PUBLICATION_REVIEW_CHECKLISTS.items()
        },
        "anti_claim": (
            "Checklist presence does not mean the public GitHub repository, "
            "package registry release, site, or walkthrough media has been "
            "reviewed or launched."
        ),
    }


def _release_substance_selector(target: Path) -> dict[str, Any]:
    """
    - Teleology: make the evidence truth floor a release-candidate substance gate for the assurance bundle.
    - Guarantee: returns a microcosm_release_substance_selector_v1 dict echoing the truth-floor status/counts and embedding the full truth-floor receipt.
    - Fails: never raises here; status mirrors audit_evidence_truth_floor(target) and is blocked when that floor is blocked.
    - Reads: audit_evidence_truth_floor over the artifact.
    - Non-goal: does not promote fixture evidence, authorize publication, or replace owner review of candidate rows.
    - Escalates-to: validators/evidence_truth_floor.py (audit_evidence_truth_floor) and its source/registry refs.
    """
    truth_floor = audit_evidence_truth_floor(target)
    return {
        "schema_version": "microcosm_release_substance_selector_v1",
        "selector_id": "evidence_truth_floor",
        "status": truth_floor.get("status"),
        "evidence_truth_floor_status": truth_floor.get("status"),
        "candidate_count": truth_floor.get("candidate_count"),
        "blocking_issue_count": truth_floor.get("blocking_issue_count"),
        "advisory_only": truth_floor.get("advisory_only"),
        "source_ref": truth_floor.get("source_ref"),
        "registry_ref": truth_floor.get("registry_ref"),
        "receipt_root_ref": truth_floor.get("receipt_root_ref"),
        "truth_floor_receipt": truth_floor,
        "required_for_release_candidate": True,
        "body_in_receipt": False,
        "anti_claim": (
            "This selector makes the evidence truth floor a release-candidate "
            "substance gate. It does not promote fixture evidence, authorize "
            "publication, or replace owner review of candidate rows."
        ),
    }


def _release_assurance_receipt(
    target: Path,
    *,
    inventory: list[dict[str, Any]],
    artifact: dict[str, Any],
    exclusion_receipt: dict[str, Any],
    authority_receipt: dict[str, Any],
) -> dict[str, Any]:
    """
    - Teleology: Release Assurance v2 aggregator binding materials, publication-history, claim/finance scans, privacy, and the substance selector into one candidate verdict.
    - Guarantee: returns a RELEASE_ASSURANCE_SCHEMA_VERSION dict; status/release_candidate_status pass iff no candidate blocking code; release/publish/hosted authorized are hard False with operator_review_required.
    - Fails: never raises; sub-receipt failures surface as release_candidate_blocking_codes; review work surfaces as release_authorization_blocking_codes.
    - Reads: inventory, artifact, exclusion and authority receipts plus the artifact tree.
    - Non-goal: validates the candidate and names review work; does not publish, authorize release, or prove complete legal/privacy/security review.
    - Escalates-to: build_release_export receipt['release_assurance_v2'] and the operator publication gate.
    """
    materials = _materials_ledger(target, inventory=inventory, artifact=artifact)
    publication_history = _artifact_publication_history_receipt(target)
    claim_language = _scan_review_patterns(
        target,
        CLAIM_LANGUAGE_REVIEW_PATTERNS,
        schema_version="microcosm_claim_language_scan_v1",
        scan_id="public_claim_language_scan",
    )
    finance_promotion = _scan_review_patterns(
        target,
        FINANCE_PROMOTION_REVIEW_PATTERNS,
        schema_version="microcosm_finance_promotion_scan_v1",
        scan_id="finance_promotion_language_scan",
    )
    privacy = _privacy_review_receipt(
        exclusion_receipt=exclusion_receipt,
        authority_receipt=authority_receipt,
    )
    release_substance_selector = _release_substance_selector(target)
    publication_checklists = _operator_publication_checklists()
    candidate_blocking_codes: list[str] = []
    if materials.get("status") != "pass":
        candidate_blocking_codes.append("RELEASE_ASSURANCE_MATERIALS_LEDGER_BLOCKED")
    if publication_history.get("status") != "pass":
        candidate_blocking_codes.append(
            "RELEASE_ASSURANCE_PUBLICATION_HISTORY_BLOCKED"
        )
    if claim_language.get("status") != "pass":
        candidate_blocking_codes.append("RELEASE_ASSURANCE_CLAIM_LANGUAGE_BLOCKED")
    if privacy.get("status") != "pass":
        candidate_blocking_codes.append("RELEASE_ASSURANCE_PRIVACY_SCAN_BLOCKED")
    if release_substance_selector.get("status") != "pass":
        candidate_blocking_codes.append(
            "RELEASE_ASSURANCE_EVIDENCE_TRUTH_FLOOR_BLOCKED"
        )
    release_authorization_blocking_codes: list[str] = []
    if claim_language.get("release_authorization_blocking_hit_count"):
        release_authorization_blocking_codes.append(
            "RELEASE_ASSURANCE_CLAIM_LANGUAGE_REVIEW_REQUIRED"
        )
    if finance_promotion.get("release_authorization_blocking_hit_count"):
        release_authorization_blocking_codes.append(
            "RELEASE_ASSURANCE_FINANCE_PROMOTION_REVIEW_REQUIRED"
        )
    release_authorization_blocking_codes.extend(
        [
            "GITHUB_PUBLICATION_SETTINGS_REVIEW_REQUIRED",
            "PACKAGE_PUBLICATION_REVIEW_REQUIRED",
            "SITE_AND_VIDEO_MEDIA_REVIEW_REQUIRED",
        ]
    )
    return {
        "schema_version": RELEASE_ASSURANCE_SCHEMA_VERSION,
        "status": "pass" if not candidate_blocking_codes else "blocked",
        "release_candidate_status": (
            "pass" if not candidate_blocking_codes else "blocked"
        ),
        "operator_publication_status": "operator_review_required",
        "release_authorized": False,
        "publish_authorized": False,
        "hosted_launch_authorized": False,
        "materials_ledger": materials,
        "publication_history_receipt": publication_history,
        "claim_language_scan": claim_language,
        "finance_promotion_scan": finance_promotion,
        "privacy_review_receipt": privacy,
        "release_substance_selector": release_substance_selector,
        "operator_publication_checklists": publication_checklists,
        "release_candidate_blocking_codes": candidate_blocking_codes,
        "release_authorization_blocking_codes": release_authorization_blocking_codes,
        "publication_gate": {
            "status": "operator_review_required",
            "release_authorization_allowed_now": False,
            "required_before_publication": [
                "operator_reviews_github_repository_settings",
                "operator_reviews_package_registry_and_sbom_requirements",
                "operator_reviews_public_site_and_walkthrough_media",
                "operator_records_explicit_release_authorization_receipt",
            ],
        },
        "anti_claim": (
            "Release Assurance v2 validates the generated artifact as a "
            "candidate and names publication review work. It does not publish, "
            "authorize release, or prove complete legal/privacy/security review."
        ),
        "body_in_receipt": False,
    }


def _expected_sentinel_fixture_path(path_ref: object) -> bool:
    """
    - Teleology: whitelist the known sentinel/fixture paths that legitimately contain forbidden-term examples.
    - Guarantee: returns True for the forbidden-classes policy file, any tests/* path, forbidden-terms fixtures, and the pattern-binding reference capsule.
    - Fails: never raises; any other path returns False.
    """
    path = str(path_ref)
    return (
        path == "core/private_state_forbidden_classes.json"
        or path.startswith("tests/")
        or "private_state_forbidden_terms.json" in path
        or path.endswith("fixtures/first_wave/pattern_binding_contract/input/reference_capsules.json")
    )


def _expected_bounded_secret_scan_hit(hit: dict[str, Any]) -> bool:
    """
    - Teleology: decide whether a bounded-secret-scan hit is an expected sentinel/target-only case rather than a real leak.
    - Guarantee: returns True when the hit is forbidden_class target_only_not_source or lands on an expected sentinel fixture path.
    - Fails: never raises; unexpected hits return False and become blocking.
    """
    if hit.get("forbidden_class") == "target_only_not_source":
        return True
    return _expected_sentinel_fixture_path(hit.get("path"))


def _secret_scan(target: Path) -> dict[str, Any]:
    """
    - Teleology: run the bounded forbidden-class secret-exclusion scan over the artifact, separating expected sentinels from real leaks.
    - Guarantee: returns the scan dict with status pass iff there are no unexpected hits; otherwise status=blocked with unexpected hit count/paths.
    - Fails: missing core/private_state_forbidden_classes.json -> status=blocked MISSING_SECRET_EXCLUSION_POLICY; never raises for present policy.
    - Reads: target/core/private_state_forbidden_classes.json and every artifact file.
    - Non-goal: bounded policy-driven scan only; does not authorize release or claim a complete secret audit.
    """
    policy_path = target / "core/private_state_forbidden_classes.json"
    if not policy_path.is_file():
        return {
            "status": "blocked",
            "blocking_codes": ["MISSING_SECRET_EXCLUSION_POLICY"],
            "blocking_hit_count": 1,
            "body_in_receipt": False,
        }
    forbidden_classes = secret_exclusion_scan.load_forbidden_classes(policy_path)
    scan = secret_exclusion_scan.scan_paths(
        _iter_artifact_files(target),
        forbidden_classes=forbidden_classes,
        source_context="release_artifact",
        display_root=target,
    )
    hits = scan.get("hits") if isinstance(scan.get("hits"), list) else []
    unexpected_hits = [
        hit
        for hit in hits
        if isinstance(hit, dict)
        and not _expected_bounded_secret_scan_hit(hit)
    ]
    if not unexpected_hits:
        return {
            **scan,
            "status": "pass",
            "blocking_hit_count": 0,
            "expected_bounded_hit_count": len(hits),
            "expected_sentinel_hit_count": sum(
                1
                for hit in hits
                if isinstance(hit, dict)
                and _expected_sentinel_fixture_path(hit.get("path"))
            ),
            "unexpected_hit_count": 0,
            "unexpected_hit_paths": [],
        }
    return {
        **scan,
        "status": "blocked",
        "blocking_hit_count": len(unexpected_hits),
        "expected_bounded_hit_count": len(hits) - len(unexpected_hits),
        "expected_sentinel_hit_count": sum(
            1
            for hit in hits
            if isinstance(hit, dict)
            and _expected_sentinel_fixture_path(hit.get("path"))
        ),
        "unexpected_hit_count": len(unexpected_hits),
        "unexpected_hit_paths": sorted(
            str(hit.get("path")) for hit in unexpected_hits if isinstance(hit, dict)
        ),
    }


def _projection_finding_diagnostics(
    findings: object,
    *,
    target: Path,
    temp_root: Path,
) -> dict[str, Any]:
    """
    - Teleology: summarize projection-bundle negative-case findings with private paths redacted, for the freshness receipt.
    - Guarantee: returns redacted error-code counts, subject-id sample, and a capped finding sample; artifact/temp/host-temp paths are rewritten to placeholders.
    - Fails: never raises; non-list findings are treated as empty; samples are bounded by the module limits.
    - Reads: the in-memory findings list (no file I/O).
    """
    if not isinstance(findings, list):
        findings = []
    rows = [row for row in findings if isinstance(row, dict)]

    def _safe_string(value: object) -> str:
        """
        - Teleology: redact artifact/temp/host-temp absolute paths out of one projection-finding string.
        - Guarantee: returns the string with target, temp_root, and host-temp roots rewritten to placeholders; empty/None -> empty string.
        - Fails: never raises; non-string values are coerced via str().
        """
        text = str(value or "")
        if not text:
            return ""
        text = text.replace(target.as_posix(), "<release-artifact>")
        text = text.replace(temp_root.as_posix(), "<projection-check-temp>")
        if HOST_TEMP_ROOT_NEEDLE in text:
            text = text.replace(HOST_TEMP_ROOT_NEEDLE, "<host-temp>/")
        return text

    error_code_counts = Counter(
        _safe_string(row.get("error_code")) for row in rows if row.get("error_code")
    )
    subject_ids = sorted(
        {
            subject_id
            for subject_id in (
                _safe_string(row.get("subject_id")) for row in rows
            )
            if subject_id
        }
    )
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _safe_string(row.get("negative_case_id")),
            _safe_string(row.get("subject_kind")),
            _safe_string(row.get("subject_id")),
            _safe_string(row.get("error_code")),
        ),
    )
    finding_sample: list[dict[str, Any]] = []
    for row in sorted_rows[:PROJECTION_FINDING_SAMPLE_LIMIT]:
        finding_sample.append(
            {
                "error_code": _safe_string(row.get("error_code")),
                "negative_case_id": _safe_string(row.get("negative_case_id")),
                "subject_kind": _safe_string(row.get("subject_kind")),
                "subject_id": _safe_string(row.get("subject_id")),
                "body_in_receipt": False,
            }
        )
    return {
        "finding_error_code_counts": dict(sorted(error_code_counts.items())),
        "finding_subject_id_count": len(subject_ids),
        "finding_subject_ids": subject_ids[
            :PROJECTION_FINDING_SUBJECT_ID_SAMPLE_LIMIT
        ],
        "finding_subject_id_overflow_count": max(
            len(subject_ids) - PROJECTION_FINDING_SUBJECT_ID_SAMPLE_LIMIT,
            0,
        ),
        "finding_sample": finding_sample,
        "finding_sample_limit": PROJECTION_FINDING_SAMPLE_LIMIT,
        "body_in_receipt": False,
    }


def _invalid_projection_freshness_receipt() -> dict[str, Any]:
    """
    - Teleology: canonical blocked receipt when the projection-freshness receipt JSON is unreadable/invalid.
    - Guarantee: returns a blocked dict with source_status invalid_json, INVALID_PROJECTION_FRESHNESS_RECEIPT codes, runtime check not_run, release_authorized False.
    - Fails: never raises; constant blocked envelope.
    """
    invalid_code = "INVALID_PROJECTION_FRESHNESS_RECEIPT"
    return {
        "status": "blocked",
        "receipt_ref": PROJECTION_FRESHNESS_RECEIPT_REF,
        "source_status": "invalid_json",
        "error_codes": [invalid_code],
        "blocking_codes": [invalid_code],
        "runtime_shape_validation": {
            "status": "not_run",
            "reason": "invalid_projection_freshness_receipt",
        },
        "release_authorized": False,
        "body_in_receipt": False,
    }


def _projection_freshness(target: Path) -> dict[str, Any]:
    """
    - Teleology: source-custody freshness gate proving the exported macro-projection bundle receipt is present, valid, and re-runs to a passing shape.
    - Guarantee: returns a dict with status pass iff the receipt status is pass, no error codes, and the runtime re-run is pass/not_run; release_authorized is always False.
    - Fails: missing receipt -> blocked MISSING_PROJECTION_FRESHNESS_RECEIPT; unreadable/non-dict JSON -> _invalid_projection_freshness_receipt; never raises.
    - Reads: target/<PROJECTION_FRESHNESS_RECEIPT_REF> and the exported_projection_import_bundle (re-run in a temp dir).
    - Non-goal: does not authorize release or assert macro-system equivalence beyond projection-shape freshness.
    - Escalates-to: organs/macro_projection_import_protocol.run_projection_bundle and the freshness receipt ref.
    """
    receipt_path = target / PROJECTION_FRESHNESS_RECEIPT_REF
    if not receipt_path.is_file():
        return {
            "status": "blocked",
            "receipt_ref": PROJECTION_FRESHNESS_RECEIPT_REF,
            "blocking_codes": ["MISSING_PROJECTION_FRESHNESS_RECEIPT"],
            "release_authorized": False,
        }
    try:
        payload = read_json_strict(receipt_path)
    except (OSError, StrictJsonError):
        return _invalid_projection_freshness_receipt()
    if not isinstance(payload, dict):
        return _invalid_projection_freshness_receipt()
    error_codes = payload.get("error_codes")
    if not isinstance(error_codes, list):
        error_codes = []
    bundle_dir = (
        target / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
    )
    runtime_shape: dict[str, Any]
    if bundle_dir.is_dir():
        with tempfile.TemporaryDirectory(prefix="microcosm-projection-freshness-") as tmp:
            temp_root = Path(tmp)
            validation = macro_projection_import_protocol.run_projection_bundle(
                bundle_dir,
                temp_root / "macro_projection_import_protocol",
                command="release-export projection freshness check",
            )
        validation_error_codes = validation.get("error_codes")
        if not isinstance(validation_error_codes, list):
            validation_error_codes = []
        findings = validation.get("findings")
        runtime_shape = {
            "status": "pass"
            if validation.get("status") == "pass" and not validation_error_codes
            else "blocked",
            "source_status": validation.get("status"),
            "error_codes": validation_error_codes,
            "finding_count": len(validation.get("findings") or []),
            "runtime_severance_status": validation.get("runtime_severance_status"),
            "dependency_preflight_gate_status": validation.get(
                "dependency_preflight_gate_status"
            ),
            "organ_lifecycle_coverage_status": validation.get(
                "organ_lifecycle_coverage_status"
            ),
            "macro_runtime_dependency_count": validation.get(
                "macro_runtime_dependency_count"
            ),
            **_projection_finding_diagnostics(
                findings,
                target=target,
                temp_root=temp_root,
            ),
        }
    else:
        runtime_shape = {
            "status": "not_run",
            "reason": "exported_projection_import_bundle_not_present",
        }
    status = (
        "pass"
        if payload.get("status") == "pass"
        and not error_codes
        and runtime_shape.get("status") in {"pass", "not_run"}
        else "blocked"
    )
    return {
        "status": status,
        "receipt_ref": PROJECTION_FRESHNESS_RECEIPT_REF,
        "source_status": payload.get("status"),
        "error_codes": error_codes,
        "runtime_shape_validation": runtime_shape,
        "runtime_severance_status": payload.get("runtime_severance_status"),
        "dependency_preflight_gate_status": payload.get("dependency_preflight_gate_status"),
        "organ_lifecycle_coverage_status": payload.get("organ_lifecycle_coverage_status"),
        "macro_runtime_dependency_count": payload.get("macro_runtime_dependency_count"),
        "release_authorized": False,
        "body_in_receipt": False,
    }


def _redact_local(text: str, *, target: Path, source_root: Path) -> str:
    """
    - Teleology: strip local artifact and source-root absolute paths from captured command output.
    - Guarantee: returns text with target -> <release-artifact> and source_root -> <source-root> substituted.
    - Fails: never raises; non-matching text is returned unchanged.
    """
    redacted = text.replace(target.as_posix(), "<release-artifact>")
    redacted = redacted.replace(source_root.as_posix(), "<source-root>")
    return redacted


def _display_argv(argv: list[str | Path]) -> list[str]:
    """
    - Teleology: stringify a display argv so receipts never embed Path objects.
    - Guarantee: returns a list of str for each argv element.
    - Fails: never raises for str/Path elements.
    """
    return [str(part) for part in argv]


def _command_receipt_row(
    command_id: str,
    completed: subprocess.CompletedProcess[str],
    *,
    display_argv: list[str | Path],
    cwd: str,
    target: Path,
    source_root: Path,
) -> dict[str, Any]:
    """
    - Teleology: capture one smoke/install subprocess result as a privacy-redacted receipt row.
    - Guarantee: returns a row with status pass iff return_code is 0, redacted stdout/stderr byte counts, and private-path-hit flags; raw bodies are excluded (body_in_receipt False).
    - Fails: never raises; a non-zero return code yields status=blocked rather than an exception.
    - Reads: the CompletedProcess stdout/stderr (redacted against target and source_root).
    """
    stdout = _redact_local(completed.stdout, target=target, source_root=source_root)
    stderr = _redact_local(completed.stderr, target=target, source_root=source_root)
    return {
        "command_id": command_id,
        "argv": _display_argv(display_argv),
        "cwd": cwd,
        "return_code": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "blocked",
        "stdout_bytes": len(completed.stdout.encode("utf-8")),
        "stderr_bytes": len(completed.stderr.encode("utf-8")),
        "stdout_private_path_hit": (
            "<source-root>" in stdout or "<release-artifact>" in stdout
        ),
        "stderr_private_path_hit": (
            "<source-root>" in stderr or "<release-artifact>" in stderr
        ),
        "body_in_receipt": False,
    }


def _receipt_status_from_rows(rows: list[dict[str, Any]]) -> str:
    """
    - Teleology: roll command rows up to a single pass/blocked status, treating any private-path hit as blocking.
    - Guarantee: returns pass iff every row has status pass and no stdout/stderr private-path hit, else blocked.
    - Fails: never raises; expects rows shaped by _command_receipt_row.
    """
    blocked = [
        row
        for row in rows
        if row["status"] != "pass"
        or row["stdout_private_path_hit"]
        or row["stderr_private_path_hit"]
    ]
    return "pass" if not blocked else "blocked"


def _git_output(root: Path, args: list[str]) -> str | None:
    """
    - Teleology: best-effort git stdout reader for source-identity and commit-diff queries.
    - Guarantee: returns stripped stdout on a zero-exit git command, else None.
    - Fails: never raises; OSError/SubprocessError/timeout and non-zero exit all fold to None.
    - Reads: git output for the given args under root.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _git_success(root: Path, args: list[str]) -> bool:
    """
    - Teleology: boolean git predicate (e.g. ancestor check) for the invalidation assessment.
    - Guarantee: returns True iff the git command exits zero, else False.
    - Fails: never raises; subprocess errors/timeout fold to False.
    - Reads: git exit status for the given args under root.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _source_identity(root: Path) -> dict[str, Any]:
    """
    - Teleology: source-custody fingerprint binding the candidate to a git HEAD and reporting worktree dirtiness.
    - Guarantee: returns status available with git_head, source_root_ref, clean-vs-worktree-delta kind, and a bounded dirty-path sample; status unavailable when not a git tree.
    - Fails: never raises; missing HEAD/toplevel -> status unavailable with null head and empty samples.
    - Reads: git rev-parse HEAD/--show-toplevel and git status --short for root.
    - Non-goal: does not authorize release; clean HEAD is a gate input, not authorization.
    """
    head = _git_output(root, ["rev-parse", "HEAD"])
    git_root_text = _git_output(root, ["rev-parse", "--show-toplevel"])
    if not head or not git_root_text:
        return {
            "status": "unavailable",
            "source_root_ref": ARTIFACT_DIR_NAME,
            "source_tree_state_kind": "not_git_or_git_unavailable",
            "git_head": None,
            "dirty_source_path_count": None,
            "dirty_source_path_sample": [],
            "dirty_source_path_overflow_count": 0,
            "body_in_receipt": False,
        }

    git_root = Path(git_root_text)
    try:
        source_root_ref = root.relative_to(git_root).as_posix()
    except ValueError:
        source_root_ref = ARTIFACT_DIR_NAME
    status_text = _git_output(root, ["status", "--short", "--", str(root)])
    dirty_paths: list[str] = []
    if status_text:
        for line in status_text.splitlines():
            if len(line) > 3 and line[2] == " ":
                path_text = line[3:]
            elif len(line) > 2 and line[1] == " ":
                path_text = line[2:]
            else:
                path_text = line
            dirty_paths.append(path_text.strip())
    dirty_paths = sorted(path for path in dirty_paths if path)
    return {
        "status": "available",
        "source_root_ref": source_root_ref,
        "source_tree_state_kind": (
            "git_head_clean" if not dirty_paths else "git_head_with_worktree_delta"
        ),
        "git_head": head,
        "dirty_source_path_count": len(dirty_paths),
        "dirty_source_path_sample": dirty_paths[:20],
        "dirty_source_path_overflow_count": max(0, len(dirty_paths) - 20),
        "body_in_receipt": False,
    }


def _release_material_path_cone(source_root_ref: str | None) -> dict[str, Any]:
    """
    - Teleology: define which path prefixes are release material vs status-projection-only, for invalidation classification.
    - Guarantee: returns a microcosm_release_material_path_cone_v1 dict with release-material, macro-assimilation, and status-projection-only prefixes plus the materiality rules.
    - Fails: never raises; a null source_root_ref falls back to the artifact dir name.
    """
    source_root = (source_root_ref or ARTIFACT_DIR_NAME).strip("/")
    release_material_prefixes = [f"{source_root}/"] if source_root else []
    macro_assimilation_prefixes = [
        f"{source_root}/{prefix}" for prefix in MACRO_ASSIMILATION_REL_PREFIXES
    ]
    return {
        "schema_version": "microcosm_release_material_path_cone_v1",
        "release_material_prefixes": release_material_prefixes,
        "macro_assimilation_material_prefixes": macro_assimilation_prefixes,
        "release_status_projection_only_prefixes": list(RELEASE_STATUS_PROJECTION_PREFIXES),
        "release_material_rule": (
            "A later commit invalidates the frozen candidate when it changes "
            "included public artifact material or release-claim dependencies."
        ),
        "status_projection_rule": (
            "A later trace, Task Ledger, or display-only projection change may "
            "require status receipt refresh, but it does not force artifact "
            "regeneration unless it changes the public artifact or gate logic."
        ),
    }


def _path_has_prefix(path: str, prefixes: list[str] | tuple[str, ...]) -> bool:
    """
    - Teleology: prefix-membership test used to classify changed paths against the materiality cone.
    - Guarantee: returns True iff the normalized path equals or is prefixed by any supplied prefix.
    - Fails: never raises; empty prefixes yield False.
    """
    normalized = path.strip("/")
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in prefixes
    )


def _classify_release_candidate_path(path: str, *, source_root_ref: str | None) -> str:
    """
    - Teleology: classify one changed path into a materiality class for candidate invalidation.
    - Guarantee: returns macro_assimilation_material_change / release_material_change / release_status_projection_only_change / unrelated_macro_mainline_change by first-match precedence.
    - Fails: never raises; unmatched paths classify as unrelated_macro_mainline_change.
    """
    cone = _release_material_path_cone(source_root_ref)
    if _path_has_prefix(path, cone["macro_assimilation_material_prefixes"]):
        return "macro_assimilation_material_change"
    if _path_has_prefix(path, cone["release_material_prefixes"]):
        return "release_material_change"
    if _path_has_prefix(path, cone["release_status_projection_only_prefixes"]):
        return "release_status_projection_only_change"
    return "unrelated_macro_mainline_change"


def _git_commits_after(
    root: Path,
    *,
    frozen_head: str,
    compare_ref: str,
) -> list[dict[str, Any]]:
    """
    - Teleology: list commits (with changed paths) between the frozen candidate head and a compare ref.
    - Guarantee: returns ordered commit dicts (commit/subject/sorted changed_paths) from git log frozen..compare; empty list when git output is unavailable.
    - Fails: never raises; null git output -> [].
    - Reads: git log --name-only between frozen_head and compare_ref under root.
    """
    raw = _git_output(
        root,
        [
            "log",
            "--reverse",
            "--format=commit:%H%x1f%s",
            "--name-only",
            f"{frozen_head}..{compare_ref}",
        ],
    )
    if raw is None:
        return []
    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in raw.splitlines():
        if line.startswith("commit:"):
            if current is not None:
                current["changed_paths"] = sorted(set(current["changed_paths"]))
                commits.append(current)
            header = line[len("commit:") :]
            if "\x1f" in header:
                commit_hash, subject = header.split("\x1f", 1)
            else:
                commit_hash, subject = header, ""
            current = {
                "commit": commit_hash,
                "subject": subject,
                "changed_paths": [],
            }
            continue
        stripped = line.strip()
        if stripped and current is not None:
            current["changed_paths"].append(stripped)
    if current is not None:
        current["changed_paths"] = sorted(set(current["changed_paths"]))
        commits.append(current)
    return commits


def assess_candidate_invalidation(
    release_candidate_packet: dict[str, Any],
    source_root: str | Path,
    *,
    compare_ref: str = "HEAD",
) -> dict[str, Any]:
    """
    - Teleology: public re-validation entrypoint deciding whether commits after a frozen release candidate invalidate it.
    - Guarantee: returns a RELEASE_CANDIDATE_INVALIDATION_SCHEMA_VERSION dict; candidate_validity_result is stale_requires_rehearsal on material change, gate_eligible when gate-ready and non-material, else historical_only.
    - Fails: source_root resolve(strict=True) on a missing path -> FileNotFoundError; missing frozen/compare head or non-ancestor -> assessment_status unavailable/not_ancestor with historical_only, never raises.
    - Reads: the candidate packet identity plus git rev-parse/merge-base/log under source_root.
    - When-needed: checking whether a previously generated release candidate is still promotable.
    - Escalates-to: _git_commits_after / _classify_release_candidate_path and the release_candidate_packet it was derived from.
    """
    source_root_path = Path(source_root).expanduser().resolve(strict=True)
    identity = release_candidate_packet.get("candidate_identity") or {}
    source = identity.get("source") or {}
    artifact = identity.get("artifact") or {}
    gate_decision = release_candidate_packet.get("release_authorization_gate_decision") or {}
    authority = release_candidate_packet.get("authority_state") or {}
    frozen_head = source.get("git_head")
    source_root_ref = source.get("source_root_ref")
    cone = _release_material_path_cone(
        str(source_root_ref) if source_root_ref else ARTIFACT_DIR_NAME
    )
    base = {
        "schema_version": RELEASE_CANDIDATE_INVALIDATION_SCHEMA_VERSION,
        "frozen_candidate": {
            "git_head": frozen_head,
            "source_root_ref": source_root_ref,
            "source_tree_state_kind": source.get("source_tree_state_kind"),
            "artifact_hash": artifact.get("artifact_payload_hash_sha256"),
            "file_count": artifact.get("file_count"),
            "payload_bytes": artifact.get("payload_bytes"),
            "release_receipt_ref": identity.get("release_receipt_ref"),
        },
        "materiality_policy": cone,
        "gate_state": gate_decision.get("decision"),
        "release_authorized": authority.get("release_authorized") is True,
    }
    compare_head = _git_output(source_root_path, ["rev-parse", compare_ref])
    if not frozen_head or not compare_head:
        return {
            **base,
            "assessment_status": "unavailable",
            "candidate_validity_result": "historical_only",
            "comparison": {
                "compare_ref": compare_ref,
                "compare_head": compare_head,
                "commits_after_candidate_count": None,
                "observed_commits": [],
            },
            "path_classification": {
                "material_change_intersection": None,
                "release_status_projection_only_intersection": None,
                "changed_path_count": None,
                "changed_paths_by_class": {},
            },
            "disclosure": "candidate_source_identity_or_compare_head_unavailable",
        }
    if not _git_success(source_root_path, ["merge-base", "--is-ancestor", frozen_head, compare_head]):
        return {
            **base,
            "assessment_status": "not_ancestor",
            "candidate_validity_result": "historical_only",
            "comparison": {
                "compare_ref": compare_ref,
                "compare_head": compare_head,
                "commits_after_candidate_count": None,
                "observed_commits": [],
            },
            "path_classification": {
                "material_change_intersection": None,
                "release_status_projection_only_intersection": None,
                "changed_path_count": None,
                "changed_paths_by_class": {},
            },
            "disclosure": "frozen_candidate_commit_is_not_an_ancestor_of_compare_head",
        }

    commits = _git_commits_after(
        source_root_path,
        frozen_head=str(frozen_head),
        compare_ref=str(compare_ref),
    )
    changed_paths_by_class: dict[str, list[str]] = {
        "macro_assimilation_material_change": [],
        "release_material_change": [],
        "release_status_projection_only_change": [],
        "unrelated_macro_mainline_change": [],
    }
    observed_commits: list[dict[str, Any]] = []
    for commit in commits:
        commit_classes: set[str] = set()
        path_sample: list[str] = []
        for path in commit.get("changed_paths", []):
            classification = _classify_release_candidate_path(
                str(path),
                source_root_ref=str(source_root_ref) if source_root_ref else None,
            )
            commit_classes.add(classification)
            changed_paths_by_class.setdefault(classification, []).append(str(path))
            if len(path_sample) < 20:
                path_sample.append(str(path))
        observed_commits.append(
            {
                "commit": commit.get("commit"),
                "subject": commit.get("subject"),
                "changed_path_count": len(commit.get("changed_paths", [])),
                "materiality_classes": sorted(commit_classes),
                "changed_path_sample": path_sample,
            }
        )

    changed_paths_by_class = {
        key: sorted(set(paths)) for key, paths in changed_paths_by_class.items()
    }
    material_paths = (
        changed_paths_by_class.get("macro_assimilation_material_change", [])
        + changed_paths_by_class.get("release_material_change", [])
    )
    status_projection_paths = changed_paths_by_class.get(
        "release_status_projection_only_change", []
    )
    material_intersection = bool(material_paths)
    status_projection_intersection = bool(status_projection_paths)
    gate_ready = gate_decision.get("decision") == "ready_pending_operator_authorization"
    if material_intersection:
        validity = "stale_requires_rehearsal"
        disclosure = "release_material_commits_after_candidate"
    elif gate_ready:
        validity = "gate_eligible"
        disclosure = (
            "newer_non_material_commits_exist"
            if commits
            else "no_newer_commits_after_frozen_candidate"
        )
    else:
        validity = "historical_only"
        disclosure = "candidate_is_not_gate_ready"

    return {
        **base,
        "assessment_status": "pass",
        "candidate_validity_result": validity,
        "comparison": {
            "compare_ref": compare_ref,
            "compare_head": compare_head,
            "commits_after_candidate_count": len(commits),
            "observed_commits": observed_commits,
        },
        "path_classification": {
            "material_change_intersection": material_intersection,
            "release_status_projection_only_intersection": status_projection_intersection,
            "changed_path_count": sum(
                len(paths) for paths in changed_paths_by_class.values()
            ),
            "changed_paths_by_class": {
                key: paths[:50] for key, paths in changed_paths_by_class.items()
            },
            "changed_path_overflow_count_by_class": {
                key: max(0, len(paths) - 50)
                for key, paths in changed_paths_by_class.items()
            },
        },
        "status_receipt_refresh_recommended": (
            status_projection_intersection and not material_intersection
        ),
        "disclosure": disclosure,
    }


def _release_candidate_warning_rows(
    source_identity: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    - Teleology: assemble the external-warning rows (governance-backlog + dirty-source) that feed the authorization gate.
    - Guarantee: returns the base EXTERNAL_WARNING_CLASSIFICATION_ROWS plus a source_tree_dirty_at_export authorization-blocking row when dirty_source_path_count > 0.
    - Fails: never raises; non-positive/absent dirty count adds no extra row.
    - Reads: source_identity dirty_source_path_count.
    """
    rows = [dict(row) for row in EXTERNAL_WARNING_CLASSIFICATION_ROWS]
    dirty_count = source_identity.get("dirty_source_path_count")
    if isinstance(dirty_count, int) and dirty_count > 0:
        rows.append(
            {
                "warning_id": "source_tree_dirty_at_export",
                "classification": "release_authority_gate_input",
                "release_blocking": False,
                "release_authorization_blocking": True,
                "public_artifact_claim_impact": ["source_material_identity"],
                "dirty_source_path_count": dirty_count,
                "reason": (
                    "The artifact is hash-bound, but the source root has "
                    "uncommitted material. Promotion must either consume a clean "
                    "source-root candidate or explicitly authorize the dirty "
                    "material fingerprint."
                ),
            }
        )
    return rows


def _release_authorization_gate(
    *,
    release_authorization_blocking_warning_count: int,
    source_identity_status: str,
) -> dict[str, Any]:
    """
    - Teleology: describe the (never auto-invoked) explicit release-authorization gate and its additional required inputs.
    - Guarantee: returns a gate dict with invoked False and release_authorized_after_gate False, listing requirements and any additional inputs (source identity, clean/authorized dirty source).
    - Fails: never raises; constant projection conditioned on the two integer/str inputs.
    - Non-goal: does not authorize release; it only names what an explicit operator gate would require.
    """
    additional_inputs: list[str] = []
    if source_identity_status != "available":
        additional_inputs.append("source_identity_available")
    if release_authorization_blocking_warning_count:
        additional_inputs.append("clean_source_root_or_explicit_dirty_material_authorization")
    return {
        "gate_id": RELEASE_AUTHORIZATION_GATE_ID,
        "invoked": False,
        "release_authorized_after_gate": False,
        "promotion_action": "record_explicit_release_authorization_receipt",
        "requires": [
            "operator_invokes_release_authorization_gate",
            "candidate_head_artifact_hash_and_receipt_identity_match",
            "release_blocking_warning_count_is_zero",
            "inventory_exclusion_runnable_projection_and_install_mode_statuses_pass",
            "release_authority_state_is_promoted_by_gate_receipt_not_by_export_validation",
        ],
        "additional_gate_input_count": len(additional_inputs),
        "additional_gate_inputs": additional_inputs,
    }


def _release_authorization_gate_decision(
    candidate_packet: dict[str, Any],
) -> dict[str, Any]:
    """
    - Teleology: dry-run decision (deny/defer/ready) over a candidate packet for whether operator release authorization is eligible.
    - Guarantee: returns a microcosm_release_authorization_gate_decision_v1 dict with dry_run True and release_authorization_allowed_now False; decision is deny on hard codes, defer on source-identity codes, else ready_pending_operator_authorization.
    - Fails: never raises; all defects surface as blocking_codes/required_actions, never exceptions.
    - Reads: candidate packet validation_summary, authority_state, warning classification, and source identity.
    - Non-goal: never promotes release; only the explicit operator gate receipt can authorize.
    """
    validation = candidate_packet.get("validation_summary") or {}
    authority = candidate_packet.get("authority_state") or {}
    gate = authority.get("release_authorization_gate") or {}
    warning_classification = (
        candidate_packet.get("external_warning_classification") or {}
    )
    identity = candidate_packet.get("candidate_identity") or {}
    source = identity.get("source") or {}
    artifact = identity.get("artifact") or {}
    warning_rows = warning_classification.get("warnings") or []
    warning_ids = {
        row.get("warning_id")
        for row in warning_rows
        if isinstance(row, dict) and row.get("warning_id")
    }
    dirty_count = source.get("dirty_source_path_count")
    hard_denial_codes: list[str] = []
    deferred_codes: list[str] = []
    blocking_inputs: list[str] = []
    required_actions: list[str] = []

    gate_invoked = gate.get("invoked") is True
    release_authorized = authority.get("release_authorized") is True
    if release_authorized and not gate_invoked:
        hard_denial_codes.append("RELEASE_AUTHORIZED_WITHOUT_EXPLICIT_GATE_RECEIPT")
        blocking_inputs.append("release_authorization_authority_state")
        required_actions.append("repair_authority_receipt_before_promotion")

    validation_blocking_codes = list(validation.get("blocking_codes") or [])
    if validation.get("export_status") != "pass" or validation_blocking_codes:
        hard_denial_codes.append("RELEASE_CANDIDATE_VALIDATION_NOT_PASSING")
        blocking_inputs.append("candidate_validation_status")
        required_actions.append("return_to_failing_validator_or_residual_owner")

    if warning_classification.get("release_blocking_warning_count", 0):
        hard_denial_codes.append("RELEASE_BLOCKING_WARNING_PRESENT")
        blocking_inputs.append("release_blocking_warning_count")
        required_actions.append("clear_release_blocking_warning_before_promotion")

    if source.get("status") != "available" or not source.get("git_head"):
        deferred_codes.append("RELEASE_AUTHORIZATION_SOURCE_IDENTITY_UNAVAILABLE")
        blocking_inputs.append("source_identity")
        required_actions.append("regenerate_candidate_from_git_source_root")
    elif (
        source.get("source_tree_state_kind") == "git_head_with_worktree_delta"
        or "source_tree_dirty_at_export" in warning_ids
        or (isinstance(dirty_count, int) and dirty_count > 0)
    ):
        deferred_codes.append("RELEASE_AUTHORIZATION_DIRTY_SOURCE_TREE")
        blocking_inputs.append("source_tree_dirty_at_export")
        required_actions.append(
            "regenerate_from_clean_source_tree_or_authorize_dirty_material_fingerprint"
        )
    elif warning_classification.get("release_authorization_blocking_warning_count", 0):
        deferred_codes.append("RELEASE_AUTHORIZATION_BLOCKING_WARNING_PRESENT")
        blocking_inputs.append("release_authorization_blocking_warnings")
        required_actions.append("satisfy_release_authorization_blocking_warning")

    if hard_denial_codes:
        decision = "deny"
        decision_reason = (
            "Release authorization is denied because the candidate has a "
            "validator, warning, or authority defect that must return to its "
            "owning lane before promotion."
        )
    elif deferred_codes:
        decision = "defer"
        decision_reason = (
            "Release authorization is deferred because the candidate is export-"
            "shape validated but its source identity is not clean enough for "
            "public promotion."
        )
    else:
        decision = "ready_pending_operator_authorization"
        decision_reason = (
            "The candidate is gate-eligible, but release remains unauthorized "
            "until the operator explicitly invokes the release authorization "
            "gate and records its receipt."
        )

    unique_inputs = list(dict.fromkeys(blocking_inputs))
    unique_actions = list(dict.fromkeys(required_actions))
    return {
        "schema_version": "microcosm_release_authorization_gate_decision_v1",
        "gate_id": RELEASE_AUTHORIZATION_GATE_ID,
        "dry_run": True,
        "gate_invoked": gate_invoked,
        "decision": decision,
        "decision_reason": decision_reason,
        "release_authorization_allowed_now": False,
        "release_authorized_after_dry_run": False,
        "operator_authorization_gate_eligible": (
            decision == "ready_pending_operator_authorization"
        ),
        "blocking_codes": hard_denial_codes + deferred_codes,
        "blocking_promotion_inputs": unique_inputs,
        "required_actions": unique_actions,
        "clean_source_requirement": (
            "An authorized public release must bind the artifact to a clean "
            "git HEAD unless a separate dirty-material authorization rule is "
            "explicitly invoked."
        ),
        "dirty_material_authorization_rule": (
            "Dirty-source promotion requires a stable dirty-diff/material "
            "fingerprint, path classification, and an explicit authorization "
            "receipt. This exporter does not promote dirty material by default."
        ),
        "evaluated_inputs": {
            "candidate_status": candidate_packet.get("status"),
            "candidate_state": candidate_packet.get("candidate_state"),
            "export_status": validation.get("export_status"),
            "validation_blocking_codes": validation_blocking_codes,
            "release_blocking_warning_count": warning_classification.get(
                "release_blocking_warning_count"
            ),
            "release_authorization_blocking_warning_count": (
                warning_classification.get(
                    "release_authorization_blocking_warning_count"
                )
            ),
            "source_status": source.get("status"),
            "source_tree_state_kind": source.get("source_tree_state_kind"),
            "git_head": source.get("git_head"),
            "dirty_source_path_count": dirty_count,
            "dirty_source_path_sample": source.get("dirty_source_path_sample", []),
            "artifact_payload_hash_sha256": artifact.get(
                "artifact_payload_hash_sha256"
            ),
            "release_receipt_ref": identity.get("release_receipt_ref"),
            "release_authorized": authority.get("release_authorized"),
        },
    }


def _release_candidate_packet(
    *,
    source_root: Path,
    command: str,
    artifact: dict[str, Any],
    exclusion_receipt: dict[str, Any],
    authority_receipt: dict[str, Any],
    runnable_receipt: dict[str, Any],
    install_smoke_receipt: dict[str, Any],
    standalone_severance_receipt: dict[str, Any],
    projection_freshness_receipt: dict[str, Any],
    release_assurance_receipt: dict[str, Any],
    blocking_codes: list[str],
) -> dict[str, Any]:
    """
    - Teleology: assemble the full validated-candidate packet (identity, validation summary, authority, warnings, gate decision, invalidation) under the no-authorization ceiling.
    - Guarantee: returns a microcosm_release_candidate_packet_v1 dict; status blocked on blocking_codes/release-blocking warnings else pass[_with_external_warnings]; embeds the dry-run gate decision and invalidation assessment.
    - Fails: never raises here; source identity comes from git and degrades to unavailable rather than raising.
    - Reads: source identity via git plus the supplied artifact and sub-receipts.
    - Non-goal: describes a candidate boundary; does not authorize publication (only the explicit gate can).
    - Escalates-to: _release_authorization_gate_decision and assess_candidate_invalidation.
    """
    source = _source_identity(source_root)
    warning_rows = _release_candidate_warning_rows(source)
    release_blocking_warning_count = sum(
        1 for row in warning_rows if row.get("release_blocking") is True
    )
    release_authorization_blocking_warning_count = sum(
        1
        for row in warning_rows
        if row.get("release_authorization_blocking") is True
    )
    validation_status = (
        "blocked"
        if blocking_codes or release_blocking_warning_count
        else "pass_with_external_warnings"
        if warning_rows
        else "pass"
    )
    candidate_state = (
        "not_candidate_blocked"
        if validation_status == "blocked"
        else "validated_release_candidate_pending_explicit_authorization"
    )
    promotion_gate = _release_authorization_gate(
        release_authorization_blocking_warning_count=(
            release_authorization_blocking_warning_count
        ),
        source_identity_status=str(source.get("status") or "unavailable"),
    )
    packet = {
        "schema_version": "microcosm_release_candidate_packet_v1",
        "status": validation_status,
        "candidate_state": candidate_state,
        "candidate_identity": {
            "source": source,
            "artifact": {
                "artifact_dir": artifact.get("artifact_dir"),
                "mode": artifact.get("mode"),
                "artifact_payload_hash_sha256": artifact.get(
                    "artifact_payload_hash_sha256"
                ),
                "file_count": artifact.get("file_count"),
                "payload_bytes": artifact.get("payload_bytes"),
            },
            "release_receipt_ref": RELEASE_RECEIPT_REF,
            "export_command": command,
        },
        "validation_summary": {
            "export_status": "pass" if not blocking_codes else "blocked",
            "blocking_codes": list(blocking_codes),
            "exclusion_status": exclusion_receipt.get("status"),
            "private_path_hit_count": len(
                exclusion_receipt.get("private_path_hits") or []
            ),
            "runnable_smoke_status": runnable_receipt.get("status"),
            "install_smoke_status": install_smoke_receipt.get("status"),
            "standalone_severance_status": standalone_severance_receipt.get("status"),
            "standalone_claim_level": standalone_severance_receipt.get("claim_level"),
            "standalone_required_public_entry_refs_missing_count": len(
                standalone_severance_receipt.get(
                    "required_public_entry_refs_missing"
                )
                or []
            ),
            "standalone_escaping_symlink_ref_count": len(
                standalone_severance_receipt.get("escaping_symlink_refs") or []
            ),
            "projection_freshness_status": projection_freshness_receipt.get("status"),
            "projection_freshness_receipt_ref": projection_freshness_receipt.get(
                "receipt_ref"
            ),
            "release_assurance_v2_status": release_assurance_receipt.get("status"),
            "release_assurance_v2_candidate_status": (
                release_assurance_receipt.get("release_candidate_status")
            ),
            "release_assurance_v2_publication_status": (
                release_assurance_receipt.get("operator_publication_status")
            ),
            "materials_ledger_status": (
                (release_assurance_receipt.get("materials_ledger") or {}).get(
                    "status"
                )
            ),
            "publication_history_status": (
                (
                    release_assurance_receipt.get("publication_history_receipt")
                    or {}
                ).get("status")
            ),
            "claim_language_scan_status": (
                (release_assurance_receipt.get("claim_language_scan") or {}).get(
                    "status"
                )
            ),
            "finance_promotion_scan_status": (
                (release_assurance_receipt.get("finance_promotion_scan") or {}).get(
                    "status"
                )
            ),
            "privacy_review_status": (
                (release_assurance_receipt.get("privacy_review_receipt") or {}).get(
                    "status"
                )
            ),
            "release_substance_selector_status": (
                (
                    release_assurance_receipt.get("release_substance_selector")
                    or {}
                ).get("status")
            ),
            "evidence_truth_floor_status": (
                (
                    release_assurance_receipt.get("release_substance_selector")
                    or {}
                ).get("evidence_truth_floor_status")
            ),
            "evidence_truth_floor_blocking_issue_count": (
                (
                    release_assurance_receipt.get("release_substance_selector")
                    or {}
                ).get("blocking_issue_count")
            ),
            "evidence_truth_floor_candidate_count": (
                (
                    release_assurance_receipt.get("release_substance_selector")
                    or {}
                ).get("candidate_count")
            ),
            "install_mode": authority_receipt.get("supported_public_mode"),
            "wheel_install_supported": authority_receipt.get("wheel_install_supported"),
        },
        "authority_state": {
            "release_authorized": authority_receipt.get("release_authorized"),
            "publish_authorized": authority_receipt.get("publish_authorized"),
            "hosted_launch_authorized": authority_receipt.get(
                "hosted_launch_authorized"
            ),
            "release_authorization_gate": promotion_gate,
        },
        "external_warning_classification": {
            "release_blocking_rule": (
                "A warning blocks release only if it changes public artifact "
                "claims for included or excluded files, private-state absence, "
                "runnable first-screen behavior, projection freshness, "
                "source/material digest correspondence, install-mode support, "
                "authority ceiling, or cold-reader documentation."
            ),
            "warning_count": len(warning_rows),
            "release_blocking_warning_count": release_blocking_warning_count,
            "release_authorization_blocking_warning_count": (
                release_authorization_blocking_warning_count
            ),
            "warnings": warning_rows,
        },
        "anti_claim": (
            "This packet describes a validated release candidate boundary. "
            "It does not authorize publication; only the explicit release "
            "authorization gate can do that."
        ),
    }
    packet["release_authorization_gate_decision"] = (
        _release_authorization_gate_decision(packet)
    )
    packet["candidate_invalidation_assessment"] = assess_candidate_invalidation(
        packet,
        source_root,
    )
    return packet


def _run_smoke(target: Path, *, source_root: Path, timeout_seconds: int = 30) -> dict[str, Any]:
    """
    - Teleology: prove the exported package runs hello/first-screen from outside the source root via -m microcosm_core.
    - Guarantee: returns a status (pass iff all command rows pass with no private-path leak) plus per-command redacted rows, asserting release-artifact PYTHONPATH (not source tree) was used.
    - Fails: a smoke command exceeding timeout_seconds -> subprocess.TimeoutExpired; non-zero exits yield status=blocked rather than raising.
    - Reads: runs python -m microcosm_core against a temp scratch project using target/src on PYTHONPATH.
    - When-needed: confirming the generated artifact is runnable as a standalone module.
    - Escalates-to: build_release_export runnable_receipt and the runnable-smoke blocking code.
    """
    commands = [
        ("hello", ["hello", "<smoke-project>"]),
        ("first_screen", ["first-screen", "<smoke-project>"]),
    ]
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="microcosm-release-smoke-") as tmp:
        tmp_root = Path(tmp)
        project = tmp_root / "scratch_project"
        project.mkdir()
        (project / "README.md").write_text("# Smoke Project\n", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(target / "src")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for command_id, display_args in commands:
            runtime_args = [
                sys.executable,
                "-m",
                "microcosm_core",
                display_args[0],
                str(project),
            ]
            completed = subprocess.run(
                runtime_args,
                cwd=tmp_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            rows.append(
                _command_receipt_row(
                    command_id,
                    completed,
                    display_argv=["python3", "-m", "microcosm_core", *display_args],
                    cwd="<temp-smoke-root>",
                    target=target,
                    source_root=source_root,
                )
            )
    return {
        "status": _receipt_status_from_rows(rows),
        "mode": "outside_source_root_py_module",
        "command_count": len(rows),
        "commands": rows,
        "source_tree_cwd_used": False,
        "source_tree_pythonpath_used": False,
        "release_artifact_cwd_used": False,
        "release_artifact_pythonpath_used": True,
        "bytecode_write_suppressed": True,
        "body_in_receipt": False,
    }


def _venv_bin_path(venv: Path, name: str) -> Path:
    """
    - Teleology: resolve the console-script path inside an install prefix across OSes.
    - Guarantee: returns <venv>/(bin|Scripts)/<name>[.exe] for the current platform.
    - Fails: never raises; pure path construction, existence not checked here.
    """
    bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return bin_dir / f"{name}{suffix}"


def _install_smoke_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    - Teleology: roll install-smoke command rows into a summary asserting installed-package (not source-tree) execution.
    - Guarantee: returns a status (pass iff every row passes with no private-path leak) plus mode/flags marking installed-prefix and isolated-artifact-copy usage.
    - Fails: never raises; failing rows yield status=blocked.
    """
    return {
        "status": _receipt_status_from_rows(rows),
        "mode": "outside_source_root_package_prefix_install",
        "command_count": len(rows),
        "commands": rows,
        "console_entrypoint_used": True,
        "installed_package_used": True,
        "source_tree_cwd_used": False,
        "source_tree_pythonpath_used": False,
        "release_artifact_cwd_used": False,
        "release_artifact_pythonpath_used": False,
        "installed_prefix_pythonpath_used": True,
        "isolated_artifact_copy_used": True,
        "install_artifact_source": "isolated_release_artifact_copy",
        "bytecode_write_suppressed": True,
        "body_in_receipt": False,
    }


def _run_install_smoke(
    target: Path,
    *,
    source_root: Path,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """
    - Teleology: pip-install the isolated artifact copy into a temp prefix and run console-script commands to prove a real install path works.
    - Guarantee: returns an install-smoke summary (status pass iff install plus all console commands pass with no leak); a failed install or missing prefix short-circuits to a blocked summary.
    - Fails: install or a command exceeding timeout_seconds -> subprocess.TimeoutExpired; non-zero exits/missing console script yield status=blocked, not exceptions.
    - Reads: copies target into a temp dir; runs pip install --prefix and the installed `microcosm` console script.
    - When-needed: confirming wheel/console-script install support before claiming installed-mode.
    - Escalates-to: build_release_export install_smoke_receipt and wheel_install_supported authority.
    """
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="microcosm-release-install-smoke-") as tmp:
        tmp_root = Path(tmp)
        install_prefix = tmp_root / "install-prefix"
        smoke_artifact = tmp_root / ARTIFACT_DIR_NAME
        shutil.copytree(
            target,
            smoke_artifact,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                "build",
                "*.egg-info",
            ),
        )
        project = tmp_root / "scratch_project"
        project.mkdir()
        (project / "README.md").write_text("# Smoke Project\n", encoding="utf-8")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env["PIP_NO_INPUT"] = "1"

        install = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--no-compile",
                "-q",
                "--prefix",
                str(install_prefix),
                str(smoke_artifact),
            ],
            cwd=tmp_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        rows.append(
            _command_receipt_row(
                "install_artifact",
                install,
                display_argv=[
                    "python3",
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-input",
                    "--no-compile",
                    "-q",
                    "--prefix",
                    "<isolated-install-prefix>",
                    "<isolated-release-artifact-copy>",
                ],
                cwd="<temp-smoke-root>",
                target=smoke_artifact,
                source_root=source_root,
            )
        )
        if install.returncode != 0:
            return _install_smoke_summary(rows)

        site_packages = next(install_prefix.glob("lib/python*/site-packages"), None)
        microcosm_exe = _venv_bin_path(install_prefix, "microcosm")
        if site_packages is None or not microcosm_exe.is_file():
            missing_install = subprocess.CompletedProcess(
                args=["microcosm", "--installed-prefix-check"],
                returncode=1,
                stdout="",
                stderr="installed prefix did not expose site-packages or console script",
            )
            rows.append(
                _command_receipt_row(
                    "installed_prefix_check",
                    missing_install,
                    display_argv=["microcosm", "--installed-prefix-check"],
                    cwd="<temp-smoke-root>",
                    target=target,
                    source_root=source_root,
                )
            )
            return _install_smoke_summary(rows)

        runtime_env = dict(env)
        runtime_env["PYTHONPATH"] = str(site_packages)
        command_specs = (
            ("hello", ["hello", str(project)], ["microcosm", "hello", "<smoke-project>"]),
            (
                "tour_card",
                ["tour", "--card", str(project)],
                ["microcosm", "tour", "--card", "<smoke-project>"],
            ),
            (
                "first_screen",
                ["first-screen", str(project)],
                ["microcosm", "first-screen", "<smoke-project>"],
            ),
            (
                "authority_card",
                ["authority", "--card"],
                ["microcosm", "authority", "--card"],
            ),
        )
        for command_id, runtime_args, display_args in command_specs:
            completed = subprocess.run(
                [str(microcosm_exe), *runtime_args],
                cwd=tmp_root,
                env=runtime_env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            rows.append(
                _command_receipt_row(
                    command_id,
                    completed,
                    display_argv=display_args,
                    cwd="<temp-smoke-root>",
                    target=target,
                    source_root=source_root,
                )
            )
    return _install_smoke_summary(rows)


def _prepare_target(root: Path, out: Path, *, force: bool) -> Path:
    """
    - Teleology: create the artifact target directory while refusing to write inside or over the source root.
    - Guarantee: returns target=<out>/microcosm-substrate, freshly created; with force it replaces an existing target.
    - Fails: output inside source root or target == source root -> ValueError; existing target without force -> FileExistsError; missing root -> FileNotFoundError from resolve(strict=True).
    - Reads: resolves root and out; Writes: creates (and with force removes) the target directory.
    """
    source_root = root.resolve(strict=True)
    output_root = out.expanduser().resolve(strict=False)
    if _is_relative_to(output_root, source_root):
        raise ValueError("release export output must not be inside the source root")
    target = output_root / ARTIFACT_DIR_NAME
    if target.resolve(strict=False) == source_root:
        raise ValueError("release export target must not be the source root")
    if target.exists():
        if not force:
            raise FileExistsError(f"{target} already exists; pass --force to replace it")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    return target


def build_release_export(
    root: str | Path,
    out: str | Path,
    *,
    force: bool = False,
    run_smoke: bool = True,
    command: str = "release-export",
) -> dict[str, Any]:
    """
    - Teleology: top-level release-export builder: materialize the public artifact, run every gate, and write the bounded release receipt.
    - Guarantee: returns the microcosm_release_export_receipt_v1 dict (status pass iff blocking_codes empty) and writes it to target/<RELEASE_RECEIPT_REF>; every authority flag (release/publish/hosted/provider/source-mutation/equivalence) is hard False.
    - Fails: out inside/equal source root -> ValueError; existing target without force -> FileExistsError; smoke timeouts propagate; gate failures surface as blocking_codes + status=blocked, not exceptions.
    - Reads: the allowlisted source tree under root; Writes: the <out>/microcosm-substrate artifact and its release receipt.
    - When-needed: generating a public release artifact and its evidence receipt.
    - Non-goal: does not authorize release, publication, hosted launch, private-root equivalence, or claim a complete secret audit.
    - Escalates-to: RELEASE_RECEIPT_REF on disk, release_export_summary, and the standalone/assurance/candidate sub-receipts.
    """
    source_root = Path(root).expanduser().resolve(strict=True)
    target = _prepare_target(source_root, Path(out), force=force)
    allowed_files, excluded_rows, missing_include_refs = _iter_allowed_files(source_root)
    inventory, home_redaction_rows = _copy_allowed_files(
        allowed_files,
        root=source_root,
        target=target,
    )
    artifact_payload_hash = _artifact_payload_hash(inventory)
    private_path_hits = _strong_private_path_hits(target, source_root=source_root)
    strong_secret_hits = _strong_secret_hits(target)
    bounded_secret_scan = _secret_scan(target)
    projection_freshness = _projection_freshness(target)
    runnable_receipt = (
        _run_smoke(target, source_root=source_root) if run_smoke else {"status": "not_run"}
    )
    install_smoke_receipt = (
        _run_install_smoke(target, source_root=source_root)
        if run_smoke
        else {"status": "not_run"}
    )
    residue_violations = _artifact_residue_violations(target)
    blocking_codes: list[str] = []
    if missing_include_refs:
        blocking_codes.append("RELEASE_EXPORT_INCLUDE_REFS_MISSING")
    if residue_violations:
        blocking_codes.append("RELEASE_EXPORT_ARTIFACT_RESIDUE_PRESENT")
    if private_path_hits:
        blocking_codes.append("RELEASE_EXPORT_PRIVATE_PATH_LEAK")
    if strong_secret_hits:
        blocking_codes.append("RELEASE_EXPORT_STRONG_SECRET_PATTERN")
    if bounded_secret_scan.get("status") != "pass":
        blocking_codes.append("RELEASE_EXPORT_SECRET_EXCLUSION_SCAN_BLOCKED")
    if projection_freshness.get("status") != "pass":
        blocking_codes.append("RELEASE_EXPORT_PROJECTION_FRESHNESS_BLOCKED")
    if runnable_receipt.get("status") not in {"pass", "not_run"}:
        blocking_codes.append("RELEASE_EXPORT_RUNNABLE_SMOKE_BLOCKED")
    if install_smoke_receipt.get("status") not in {"pass", "not_run"}:
        blocking_codes.append("RELEASE_EXPORT_INSTALL_SMOKE_BLOCKED")

    wheel_install_supported = install_smoke_receipt.get("status") == "pass"
    wheel_install_authority = (
        "outside_source_root_package_install_smoke_pass"
        if wheel_install_supported
        else "unsupported_until_outside_source_root_package_install_smoke_pass"
    )

    receipt = {
        "schema_version": "microcosm_release_export_receipt_v1",
        "receipt_id": "microcosm_release_export_receipt",
        "generated_at": utc_now(),
        "status": "pass" if not blocking_codes else "blocked",
        "command": command,
        "artifact": {
            "artifact_dir": ARTIFACT_DIR_NAME,
            "mode": "generated_standalone_folder",
            "artifact_payload_hash_sha256": artifact_payload_hash,
            "file_count": len(inventory),
            "payload_bytes": sum(int(row["size_bytes"]) for row in inventory),
            "release_receipt_ref": RELEASE_RECEIPT_REF,
            "receipt_generated_after_inventory": True,
        },
        "inventory_receipt": {
            "status": "pass",
            "manifest_policy": "allowlisted_public_tree",
            "include_refs": list(DEFAULT_INCLUDE_REFS),
            "missing_include_refs": missing_include_refs,
            "file_count": len(inventory),
            "role_counts": {
                role: sum(1 for row in inventory if row["role"] == role)
                for role in sorted({str(row["role"]) for row in inventory})
            },
            "files": inventory,
        },
        "exclusion_receipt": {
            "status": (
                "pass"
                if not residue_violations and not private_path_hits and not strong_secret_hits
                else "blocked"
            ),
            "source_residue_excluded": excluded_rows,
            "artifact_residue_violations": residue_violations,
            "private_path_hits": private_path_hits,
            "strong_secret_hits": strong_secret_hits,
            "bounded_secret_exclusion_scan": {
                "status": bounded_secret_scan.get("status"),
                "blocking_hit_count": bounded_secret_scan.get("blocking_hit_count"),
                "expected_sentinel_hit_count": bounded_secret_scan.get(
                    "expected_sentinel_hit_count"
                ),
                "expected_bounded_hit_count": bounded_secret_scan.get(
                    "expected_bounded_hit_count"
                ),
                "unexpected_hit_count": bounded_secret_scan.get("unexpected_hit_count"),
                "unexpected_hit_paths": bounded_secret_scan.get("unexpected_hit_paths"),
                "body_in_receipt": bounded_secret_scan.get("body_in_receipt"),
                "scan_purpose": bounded_secret_scan.get("scan_purpose"),
                "anti_claim": bounded_secret_scan.get("anti_claim"),
            },
            "source_module_home_redaction": {
                "status": "pass",
                "policy": (
                    "concrete_non_example_home_paths_in_text_source_modules_are_"
                    "rewritten_to_public_example_home"
                ),
                "replacement": PUBLIC_EXAMPLE_HOME,
                "redacted_file_count": len(home_redaction_rows),
                "concrete_home_path_replacement_count": sum(
                    int(row["concrete_home_path_replacement_count"])
                    for row in home_redaction_rows
                ),
                "redacted_files": home_redaction_rows,
                "body_in_receipt": False,
            },
            "body_in_receipt": False,
        },
        "authority_receipt": {
            "status": "pass",
            "release_authorized": False,
            "publish_authorized": False,
            "hosted_launch_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutation_authorized": False,
            "private_data_equivalence_authorized": False,
            "supported_public_mode": "generated_standalone_folder",
            "wheel_install_supported": wheel_install_supported,
            "wheel_install_authority": wheel_install_authority,
            "standalone_run_command": (
                "PYTHONPATH=src python3 -m microcosm_core hello <project>"
            ),
            "installed_run_command": "microcosm hello <project>",
        },
        "runnable_receipt": runnable_receipt,
        "install_smoke_receipt": install_smoke_receipt,
        "projection_freshness_receipt": projection_freshness,
        "blocking_codes": blocking_codes,
        "anti_claim": (
            "This receipt validates export shape for a generated public folder. "
            "It is not release, publication, hosted launch, private-root equivalence, "
            "or complete secret-audit authority."
        ),
        "receipt_paths": [RELEASE_RECEIPT_REF],
    }
    standalone_severance_receipt = _standalone_severance_receipt(
        target,
        inventory=inventory,
        missing_include_refs=missing_include_refs,
        exclusion_receipt=receipt["exclusion_receipt"],
        authority_receipt=receipt["authority_receipt"],
        runnable_receipt=receipt["runnable_receipt"],
        install_smoke_receipt=receipt["install_smoke_receipt"],
        projection_freshness_receipt=receipt["projection_freshness_receipt"],
    )
    receipt["standalone_severance_receipt"] = standalone_severance_receipt
    if standalone_severance_receipt.get("status") != "pass":
        blocking_codes.append("RELEASE_EXPORT_STANDALONE_SEVERANCE_BLOCKED")
    receipt["release_assurance_v2"] = _release_assurance_receipt(
        target,
        inventory=inventory,
        artifact=receipt["artifact"],
        exclusion_receipt=receipt["exclusion_receipt"],
        authority_receipt=receipt["authority_receipt"],
    )
    if receipt["release_assurance_v2"].get("status") != "pass":
        blocking_codes.append("RELEASE_EXPORT_ASSURANCE_V2_BLOCKED")
    receipt["status"] = "pass" if not blocking_codes else "blocked"
    receipt["blocking_codes"] = blocking_codes
    receipt["release_candidate_packet"] = _release_candidate_packet(
        source_root=source_root,
        command=command,
        artifact=receipt["artifact"],
        exclusion_receipt=receipt["exclusion_receipt"],
        authority_receipt=receipt["authority_receipt"],
        runnable_receipt=receipt["runnable_receipt"],
        install_smoke_receipt=receipt["install_smoke_receipt"],
        standalone_severance_receipt=receipt["standalone_severance_receipt"],
        projection_freshness_receipt=receipt["projection_freshness_receipt"],
        release_assurance_receipt=receipt["release_assurance_v2"],
        blocking_codes=blocking_codes,
    )
    write_json_atomic(target / RELEASE_RECEIPT_REF, receipt)
    return receipt


def release_export_summary(receipt: dict[str, Any], target: str | Path) -> dict[str, Any]:
    """
    - Teleology: project the full release receipt into a compact stdout summary for the CLI --summary path.
    - Guarantee: returns a microcosm_release_export_summary_v1 dict echoing status, candidate/authorization blocking codes, artifact identity, validation/authority/gate slices; the full receipt on disk stays authoritative.
    - Fails: never raises; missing nested keys degrade to None via defensive `or {}` lookups.
    - Reads: the in-memory release receipt and the target path.
    - Non-goal: compact projection only; does not authorize release, publication, hosting, provider calls, or private-root equivalence.
    - Escalates-to: the full receipt at release_receipt_path (RELEASE_RECEIPT_REF).
    """
    artifact = receipt.get("artifact") or {}
    authority = receipt.get("authority_receipt") or {}
    candidate = receipt.get("release_candidate_packet") or {}
    assurance = receipt.get("release_assurance_v2") or {}
    validation = candidate.get("validation_summary") or {}
    warnings = candidate.get("external_warning_classification") or {}
    gate = candidate.get("release_authorization_gate_decision") or {}
    target_path = Path(target)
    candidate_blocking_codes = list(receipt.get("blocking_codes") or [])
    authorization_blocking_codes = list(gate.get("blocking_codes") or [])

    return {
        "schema_version": "microcosm_release_export_summary_v1",
        "status": receipt.get("status"),
        "blocking_codes": candidate_blocking_codes,
        "release_candidate_blocking_codes": candidate_blocking_codes,
        "release_authorization_blocking_codes": authorization_blocking_codes,
        "artifact_path": str(target_path),
        "release_receipt_path": str(target_path / RELEASE_RECEIPT_REF),
        "release_receipt_ref": RELEASE_RECEIPT_REF,
        "artifact": {
            "artifact_dir": artifact.get("artifact_dir"),
            "file_count": artifact.get("file_count"),
            "payload_bytes": artifact.get("payload_bytes"),
            "artifact_payload_hash_sha256": artifact.get(
                "artifact_payload_hash_sha256"
            ),
        },
        "validation_summary": {
            "candidate_status": candidate.get("status"),
            "candidate_state": candidate.get("candidate_state"),
            "runnable_smoke_status": validation.get("runnable_smoke_status"),
            "install_smoke_status": validation.get("install_smoke_status"),
            "standalone_severance_status": validation.get(
                "standalone_severance_status"
            ),
            "projection_freshness_status": validation.get(
                "projection_freshness_status"
            ),
            "release_assurance_v2_status": assurance.get("status"),
            "release_assurance_v2_publication_status": assurance.get(
                "operator_publication_status"
            ),
            "release_substance_selector_status": validation.get(
                "release_substance_selector_status"
            ),
            "release_blocking_warning_count": warnings.get(
                "release_blocking_warning_count"
            ),
            "release_authorization_blocking_warning_count": warnings.get(
                "release_authorization_blocking_warning_count"
            ),
        },
        "authority": {
            "release_authorized": authority.get("release_authorized"),
            "publish_authorized": authority.get("publish_authorized"),
            "hosted_launch_authorized": authority.get("hosted_launch_authorized"),
            "provider_calls_authorized": authority.get("provider_calls_authorized"),
            "source_files_mutation_authorized": authority.get(
                "source_files_mutation_authorized"
            ),
        },
        "release_authorization_gate": {
            "decision": gate.get("decision"),
            "release_authorization_allowed_now": gate.get(
                "release_authorization_allowed_now"
            ),
            "operator_authorization_gate_eligible": gate.get(
                "operator_authorization_gate_eligible"
            ),
            "blocking_codes": authorization_blocking_codes,
            "required_actions": gate.get("required_actions") or [],
        },
        "anti_claim": (
            "Compact stdout summary only; the full receipt remains the authority "
            "at release_receipt_path and this summary does not authorize release, "
            "publication, hosting, provider calls, or private-root equivalence."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry: generate a public Microcosm export, or assess an existing release receipt.

    - Teleology: command-line front door to the release-export pipeline and its candidate-invalidation check.
    - Guarantee: with --out, writes the standalone microcosm-substrate/ export and prints the release receipt (or summary); with --assess-candidate, prints a re-validation assessment instead.
    - Reads: --root source tree, and --assess-candidate receipt JSON / --compare-ref git ref.
    - Writes: --out/<microcosm-substrate> export directory and bounded receipts via build_release_export.
    - When-needed: producing or re-validating a public release artifact.
    - Fails: --out and --assess-candidate both absent -> parser.error; export status != "pass" or assessment not gate_eligible -> return code 1.
    """
    parser = argparse.ArgumentParser(
        prog="python -m microcosm_core.release_export",
        description="Generate a standalone public Microcosm folder with a bounded release-export receipt.",
    )
    parser.add_argument("--root", default=".", help="microcosm-substrate source root")
    parser.add_argument("--out", help="output directory that will receive microcosm-substrate/")
    parser.add_argument(
        "--assess-candidate",
        help="read an existing release receipt and assess whether later commits invalidate it",
    )
    parser.add_argument(
        "--compare-ref",
        default="HEAD",
        help="git ref used by --assess-candidate (default: HEAD)",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing generated artifact directory")
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="write the export and receipts without running the outside-root first-screen smoke",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print a compact export summary instead of the full release receipt",
    )
    args = parser.parse_args(argv)
    if args.assess_candidate:
        receipt_path = Path(args.assess_candidate).expanduser().resolve(strict=True)
        payload = read_json_strict(receipt_path)
        candidate_packet = payload.get("release_candidate_packet") or payload
        assessment = assess_candidate_invalidation(
            candidate_packet,
            args.root,
            compare_ref=args.compare_ref,
        )
        print(json.dumps(assessment, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if assessment.get("candidate_validity_result") == "gate_eligible" else 1
    if not args.out:
        parser.error("--out is required unless --assess-candidate is supplied")
    command_parts = [
        "python",
        "-m",
        "microcosm_core.release_export",
        "--root",
        "<microcosm-root>",
        "--out",
        "<release-out>",
    ]
    if args.force:
        command_parts.append("--force")
    if args.skip_smoke:
        command_parts.append("--skip-smoke")
    if args.summary:
        command_parts.append("--summary")
    command = " ".join(command_parts)
    receipt = build_release_export(
        args.root,
        args.out,
        force=args.force,
        run_smoke=not args.skip_smoke,
        command=command,
    )
    target = Path(args.out).expanduser().resolve() / ARTIFACT_DIR_NAME
    output = release_export_summary(receipt, target) if args.summary else receipt
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if receipt.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
