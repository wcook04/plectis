from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shlex
from collections import Counter
from pathlib import Path
from typing import Any

from microcosm_core.projections.concept_mechanism_read_model import (
    build_organ_doctrine_rows,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import read_json_strict


SCHEMA_VERSION = "microcosm_organ_surface_contract_v0"
CARD_PREVIEW_LIMIT = 5
AUTHORITY_POSTURE = "derived_surface_audit_not_source_authority"
ENTRY_ROUTE_REF = "atlas/entry_packet.json::concept_mechanism_entry_route"
CONCEPT_STANDARD_REF = "standards/std_microcosm_concept.json"
MECHANISM_STANDARD_REF = "standards/std_microcosm_mechanism.json"
ACCEPTANCE_PLAN_REF = "core/acceptance/first_wave_acceptance.json"
ALLOWED_SYNTHETIC_ACCEPTANCE_DISPOSITIONS = frozenset(
    {
        "real_substrate_capsule",
        "retained_regression_validator",
        "deleted_or_demoted_historical_artifact",
        "blocked_secret_only",
    }
)
REAL_SUBSTRATE_DISPOSITION = "real_substrate_capsule"
RETAINED_REGRESSION_VALIDATOR_DISPOSITION = "retained_regression_validator"
SYNTHETIC_EVIDENCE_CLASSES = frozenset({"fixture_echo_smoke"})
SYNTHETIC_TRUTH_BUCKETS = frozenset({"regression_negative_fixture"})
ACCEPTANCE_REGISTRY_PARITY_FIELDS = (
    "evidence_class",
    "counts_as_real_substrate_progress",
    "truth_accounting_bucket",
)
SOURCE_LANGUAGE_BY_EXTENSION = {
    ".cjs": "javascript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".json": "json",
    ".jsonl": "jsonl",
    ".lean": "lean",
    ".md": "markdown",
    ".mjs": "javascript",
    ".py": "python",
    ".swift": "swift",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
}
ORGAN_RELATIONSHIP_TOPOLOGY_AUTHORITY = (
    "organ_surface_contract_rows_plus_source_language_adjacency_plus_"
    "source_module_manifest_ref_edges_only_not_"
    "duplicate_source_scan_not_lattice_authority_not_source_semantics_"
    "api_compatibility_comment_standard_or_release_claim"
)
SOURCE_MODULE_FILE_GRAPH_AUTHORITY = ORGAN_RELATIONSHIP_TOPOLOGY_AUTHORITY
RELATION_TYPE_ALIASES = {
    "wires_to": "organ.wires_to.organ",
    "file_to_file": "source_file.copied_to_public_target",
    "file_validated_by": "source_file.validated_by_ref",
    "target_peer": "target_file.shares_macro_source_with_target_file",
    "target_validated_by": "target_file.validated_by_ref",
    "shard_to_shard": "source_shard.retained_as_public_target_shard",
    "shard_validated_by": "source_shard.validated_by_ref",
    "target_shard_validated_by": "target_shard.validated_by_ref",
}

MISSING_SURFACE_KEYS = (
    "registry_rows",
    "runner_source_files",
    "validator_commands",
    "current_authority_receipts",
    "acceptance_plan_rows",
    "synthetic_acceptance_dispositions",
    "fixture_manifests",
    "atlas_cards",
    "paper_modules",
    "standard_files",
    "standards_registry_rows",
    "runtime_steps",
    "cli_commands",
    "concept_projection_rows",
    "mechanism_projection_rows",
)


def _repo_root(root: Path) -> Path:
    """Resolve the repo root one level above the microcosm-substrate root.

    - Teleology: lets ref resolution reach codex/state/system/tools siblings outside the substrate root.
    - Guarantee: returns root.parent (a Path); pure, no filesystem access.
    - Fails: never raises; a wrong/relative root yields a wrong parent Path, not an error.
    - When-needed: tracing how a non-substrate ref (codex/, state/) is anchored.
    """
    return root.parent


def _as_list(value: Any) -> list[Any]:
    """Coerce an arbitrary JSON value to a list, defaulting non-lists to empty.

    - Teleology: defensive read shim so malformed/missing registry fields never crash the audit.
    - Guarantee: returns value unchanged when it is a list, else a new empty list.
    - Fails: never raises; non-list input silently degrades to [].
    - When-needed: understanding why an absent/wrong-typed manifest field is treated as zero rows.
    """
    return value if isinstance(value, list) else []


def _accepted_registry_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Select organ-registry rows whose status is accepted_current_authority.

    - Teleology: defines the accepted-organ population the entire surface audit ranges over.
    - Guarantee: returns the dict rows of implemented_organs with status == "accepted_current_authority"; non-dicts and other statuses are dropped.
    - Reads: the in-memory organ_registry.json::implemented_organs payload passed in.
    - Fails: never raises; missing/empty implemented_organs yields [].
    - Non-goal: does not authorize source-body export, release, or whole-system correctness; presence of a row is acceptance bookkeeping only.
    """
    return [
        row
        for row in _as_list(registry.get("implemented_organs"))
        if isinstance(row, dict) and row.get("status") == "accepted_current_authority"
    ]


def _is_synthetic_acceptance_row(row: dict[str, Any]) -> bool:
    """Decide whether a registry row was accepted on synthetic (fixture) evidence.

    - Teleology: separates real-substrate organs from regression-fixture organs so progress is not over-claimed.
    - Guarantee: returns True iff evidence_class is a synthetic class, OR truth_accounting_bucket is a synthetic bucket, OR counts_as_real_substrate_progress is explicitly False.
    - Reads: the row's evidence_class / truth_accounting_bucket / counts_as_real_substrate_progress fields.
    - Fails: never raises; absent fields read as None and yield False.
    - Non-goal: does not authorize treating synthetic acceptance as real substrate progress, release, or public-safe equivalence.
    """
    return (
        row.get("evidence_class") in SYNTHETIC_EVIDENCE_CLASSES
        or row.get("truth_accounting_bucket") in SYNTHETIC_TRUTH_BUCKETS
        or row.get("counts_as_real_substrate_progress") is False
    )


def _synthetic_disposition_value(row: dict[str, Any]) -> str:
    """Normalize a row's synthetic_acceptance_disposition to a flat string.

    - Teleology: tolerates both the dict-wrapped and bare-string shapes of the disposition field across registry/acceptance sources.
    - Guarantee: returns the inner "disposition" string for a dict value, the string itself for a string value, else "".
    - Reads: the row's synthetic_acceptance_disposition field.
    - Fails: never raises; unexpected types collapse to "".
    - Non-goal: does not validate the disposition against the allowed set; that is the audit's job.
    """
    value = row.get("synthetic_acceptance_disposition")
    if isinstance(value, dict):
        return str(value.get("disposition") or "")
    if isinstance(value, str):
        return value
    return ""


def _disposition_audit_for_row(
    registry_row: dict[str, Any],
    acceptance_plan_row: dict[str, Any],
) -> dict[str, Any]:
    """Audit real-substrate vs synthetic disposition parity for one organ.

    - Teleology: the truth-accounting gate that stops a fixture-backed organ from being booked as real substrate progress.
    - Guarantee: returns an audit dict with organ_id, the registry/acceptance dispositions, and missing/invalid/mismatch/fixture_authority_mismatch lists; "ok" is True iff all three lists are empty.
    - Reads: registry_row + acceptance_plan_row real_substrate_disposition / synthetic_acceptance_disposition / counts_as_real_substrate_progress fields (against ALLOWED_SYNTHETIC_ACCEPTANCE_DISPOSITIONS).
    - Fails: never raises; reports defects as populated missing/invalid/mismatch lists with "ok": False, never an exception.
    - Non-goal: does not authorize release or claim source-body correctness; only checks disposition bookkeeping consistency.
    - Escalates-to: codex/standards std_microcosm acceptance plan + core/acceptance/first_wave_acceptance.json as the disposition authority.
    """
    organ_id = str(registry_row.get("organ_id") or "")
    disposition = str(registry_row.get("real_substrate_disposition") or "")
    acceptance_disposition = str(
        acceptance_plan_row.get("real_substrate_disposition") or ""
    )
    synthetic_disposition = _synthetic_disposition_value(registry_row)
    acceptance_synthetic_disposition = _synthetic_disposition_value(
        acceptance_plan_row
    )
    is_synthetic = _is_synthetic_acceptance_row(registry_row)
    counts_as_progress = registry_row.get("counts_as_real_substrate_progress") is True

    missing: list[str] = []
    invalid: list[str] = []
    mismatch: list[str] = []
    if not disposition:
        missing.append("registry.real_substrate_disposition")
    if acceptance_plan_row and not acceptance_disposition:
        missing.append("acceptance.real_substrate_disposition")
    if is_synthetic and not synthetic_disposition:
        missing.append("registry.synthetic_acceptance_disposition")
    if is_synthetic and acceptance_plan_row and not acceptance_synthetic_disposition:
        missing.append("acceptance.synthetic_acceptance_disposition")

    if disposition and disposition not in ALLOWED_SYNTHETIC_ACCEPTANCE_DISPOSITIONS:
        invalid.append("registry.real_substrate_disposition")
    if (
        acceptance_disposition
        and acceptance_disposition not in ALLOWED_SYNTHETIC_ACCEPTANCE_DISPOSITIONS
    ):
        invalid.append("acceptance.real_substrate_disposition")
    if (
        synthetic_disposition
        and synthetic_disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION
    ):
        invalid.append("registry.synthetic_acceptance_disposition")
    if (
        acceptance_synthetic_disposition
        and acceptance_synthetic_disposition
        != RETAINED_REGRESSION_VALIDATOR_DISPOSITION
    ):
        invalid.append("acceptance.synthetic_acceptance_disposition")

    if is_synthetic:
        if counts_as_progress:
            mismatch.append("synthetic_row_counts_as_real_substrate_progress")
        if disposition and disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION:
            mismatch.append("synthetic_row_real_substrate_disposition")
        if (
            acceptance_disposition
            and acceptance_disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION
        ):
            mismatch.append("acceptance_synthetic_row_real_substrate_disposition")
    if disposition and acceptance_disposition and disposition != acceptance_disposition:
        mismatch.append("registry_acceptance_disposition_mismatch")
    elif counts_as_progress and disposition and disposition != REAL_SUBSTRATE_DISPOSITION:
        mismatch.append("real_progress_row_disposition")
    if (
        counts_as_progress
        and acceptance_disposition
        and acceptance_disposition != REAL_SUBSTRATE_DISPOSITION
    ):
        mismatch.append("real_progress_acceptance_disposition")
    elif not counts_as_progress and disposition == REAL_SUBSTRATE_DISPOSITION:
        mismatch.append("non_progress_row_claims_real_substrate_capsule")

    fixture_authority_mismatch = [
        reason
        for reason in mismatch
        if reason
        not in {
            "registry_acceptance_disposition_mismatch",
            "real_progress_acceptance_disposition",
        }
    ]

    return {
        "organ_id": organ_id,
        "is_synthetic_acceptance": is_synthetic,
        "counts_as_real_substrate_progress": counts_as_progress,
        "real_substrate_disposition": disposition,
        "acceptance_plan_real_substrate_disposition": acceptance_disposition,
        "synthetic_acceptance_disposition": synthetic_disposition,
        "acceptance_plan_synthetic_acceptance_disposition": (
            acceptance_synthetic_disposition
        ),
        "missing": missing,
        "invalid": invalid,
        "mismatch": mismatch,
        "fixture_authority_mismatch": fixture_authority_mismatch,
        "ok": not missing and not invalid and not mismatch,
    }


def _acceptance_metadata_audit_for_row(
    registry_row: dict[str, Any],
    acceptance_plan_row: dict[str, Any],
) -> dict[str, Any]:
    """Audit field-for-field parity between a registry row and its acceptance plan row.

    - Teleology: ensures the acceptance plan mirrors the registry's evidence-class / progress / truth-bucket fields so the two sources cannot silently diverge.
    - Guarantee: returns an audit dict with per-field registry/acceptance values plus missing/mismatch lists over ACCEPTANCE_REGISTRY_PARITY_FIELDS; "ok" is True iff both lists empty. A missing acceptance row short-circuits to ok=True with skipped_reason="acceptance_plan_row_missing".
    - Reads: registry_row and acceptance_plan_row evidence_class / counts_as_real_substrate_progress / truth_accounting_bucket fields.
    - Fails: never raises; divergence is reported via missing/mismatch with "ok": False.
    - Non-goal: does not authorize release; only checks registry/acceptance metadata parity, not substrate truth.
    """
    organ_id = str(registry_row.get("organ_id") or "")
    if not acceptance_plan_row:
        return {
            "organ_id": organ_id,
            "checked_fields": list(ACCEPTANCE_REGISTRY_PARITY_FIELDS),
            "fields": {},
            "missing": [],
            "mismatch": [],
            "skipped_reason": "acceptance_plan_row_missing",
            "ok": True,
        }

    missing: list[str] = []
    mismatch: list[str] = []
    fields: dict[str, dict[str, Any]] = {}

    for field in ACCEPTANCE_REGISTRY_PARITY_FIELDS:
        registry_value = registry_row.get(field)
        acceptance_has_field = field in acceptance_plan_row
        acceptance_value = acceptance_plan_row.get(field)
        fields[field] = {
            "registry": registry_value,
            "acceptance": acceptance_value if acceptance_has_field else None,
        }
        if not acceptance_has_field:
            missing.append(field)
        elif acceptance_value != registry_value:
            mismatch.append(field)

    return {
        "organ_id": organ_id,
        "checked_fields": list(ACCEPTANCE_REGISTRY_PARITY_FIELDS),
        "fields": fields,
        "missing": missing,
        "mismatch": mismatch,
        "ok": not missing and not mismatch,
    }


def _runner_source_ref(runner: str) -> str:
    """Map a microcosm_core runner dotted-path to its source file ref.

    - Teleology: turns a registry runner symbol into a checkable on-disk source path for the runner_source_file surface.
    - Guarantee: returns "src/<dotted/path>.py" for a microcosm_core.* runner, else "" (no path claimed).
    - Reads: nothing on disk; pure string transform of the runner name.
    - Fails: never raises; non-microcosm_core runners yield "" and downstream marks the surface absent.
    - Non-goal: does not verify the file exists (caller does) nor authorize the runner's source body.
    """
    if not runner.startswith("microcosm_core."):
        return ""
    return f"src/{runner.replace('.', '/')}.py"


def _resolve_ref(root: Path, ref: str) -> Path:
    """Resolve a possibly-fragmented ref string to an absolute Path under the right root.

    - Teleology: single anchoring rule so receipt refs (some substrate-local, some repo-sibling like codex/state/system/tools) resolve consistently.
    - Guarantee: returns an absolute Path: the ref as-is if absolute, repo-root-anchored for codex/state/system/tools first segments, else substrate-root-anchored; the "#fragment" suffix is stripped first; empty ref returns root.
    - Reads: nothing on disk; pure path arithmetic (caller does .is_file()).
    - Fails: never raises; an unrecognized shape still returns a (possibly non-existent) Path.
    - Non-goal: does not check existence or authorize the referenced artifact.
    """
    ref_path = ref.split("#", 1)[0]
    if not ref_path:
        return root
    path = Path(ref_path)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] in {"codex", "state", "system", "tools"}:
        return _repo_root(root) / path
    return root / path


def _paper_module_ref(root: Path, organ_id: str, atlas_row: dict[str, Any]) -> str:
    """Resolve the paper-module ref for an organ, preferring the declared then conventional path.

    - Teleology: locates the per-organ paper module so the paper_module surface can be checked present.
    - Guarantee: returns the atlas-declared paper_module_ref if that file exists; else "paper_modules/<organ_id>.md" if it exists; else the declared string unchanged (possibly "").
    - Reads: atlas_row.paper_module_ref and the on-disk files root/<declared> and root/paper_modules/<organ_id>.md.
    - Fails: never raises; when nothing resolves it returns the (possibly empty) declared value and the caller marks the surface absent.
    - Non-goal: does not validate paper-module content or authorize it as doctrine authority.
    """
    declared = str(atlas_row.get("paper_module_ref") or "").strip()
    if declared and (root / declared).is_file():
        return declared
    direct = Path("paper_modules") / f"{organ_id}.md"
    if (root / direct).is_file():
        return direct.as_posix()
    return declared


def _atlas_rows_by_organ(root: Path) -> dict[str, dict[str, Any]]:
    """Index the organ atlas into an organ_id -> atlas-row dict.

    - Teleology: gives the audit O(1) access to each organ's atlas card (wiring, first_command, paper_module_ref).
    - Guarantee: returns a dict keyed by organ_id over the dict rows of organ_atlas.json::organs that carry an organ_id.
    - Reads: core/organ_atlas.json (strict-parsed; the generated organ atlas, not source authority).
    - Fails: raises whatever read_json_strict raises when core/organ_atlas.json is missing or invalid JSON.
    - Non-goal: does not authorize the atlas as release or source authority; it is a generated discoverability surface.
    """
    atlas = read_json_strict(root / "core/organ_atlas.json")
    return {
        str(row.get("organ_id")): row
        for row in _as_list(atlas.get("organs"))
        if isinstance(row, dict) and row.get("organ_id")
    }


def _standards_registry_by_id(root: Path) -> dict[str, dict[str, Any]]:
    """Index the standards registry into a standard_id -> registry-row dict.

    - Teleology: lets the audit check that each organ's std_microcosm_<id> standard has a registry row.
    - Guarantee: returns a dict keyed by standard_id over the dict rows of standards_registry.json::standards that carry a standard_id.
    - Reads: core/standards_registry.json (strict-parsed).
    - Fails: raises whatever read_json_strict raises when core/standards_registry.json is missing or invalid JSON.
    - Non-goal: does not verify standard file bodies or authorize them as release authority.
    """
    registry = read_json_strict(root / "core/standards_registry.json")
    return {
        str(row.get("standard_id")): row
        for row in _as_list(registry.get("standards"))
        if isinstance(row, dict) and row.get("standard_id")
    }


def _source_language_for_ref(ref: str) -> tuple[str, str]:
    """Classify a source-file ref into a language family and a normalized extension.

    - Teleology: feeds the body-free language inventory so organs can be grouped by source language without reading bodies.
    - Guarantee: returns (language, extension): language from SOURCE_LANGUAGE_BY_EXTENSION, or "extensionless" when no suffix, or "other" for an unmapped suffix; extension is the lowercased suffix or "<none>".
    - Reads: only the ref string's suffix; no file content.
    - Fails: never raises; any ref yields a 2-tuple.
    - Non-goal: does not read or authorize source bodies; extension is a path signal, not a language/API/comment-standard claim.
    """
    suffix = Path(ref).suffix.lower()
    language = SOURCE_LANGUAGE_BY_EXTENSION.get(
        suffix,
        "extensionless" if not suffix else "other",
    )
    return language, suffix or "<none>"


def _root_relative_ref(root: Path, ref: str) -> str:
    """Normalize a source/target ref to a substrate-root-relative posix path.

    - Teleology: canonical-izes manifest refs (absolute, or "microcosm-substrate/"-prefixed) so they can be joined to root and de-duplicated.
    - Guarantee: returns the path relative to root for an absolute ref under root; strips a leading "microcosm-substrate/" prefix; returns "" for an absolute ref that is NOT under root; otherwise returns the ref unchanged.
    - Reads: nothing on disk; pure path arithmetic.
    - Fails: never raises; an out-of-root absolute ref degrades to "" rather than erroring.
    - Non-goal: does not check existence or authorize the referenced source body.
    """
    path = Path(ref)
    if path.is_absolute():
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return ""
    if ref.startswith("microcosm-substrate/"):
        return ref.removeprefix("microcosm-substrate/")
    return ref


def _mechanism_source_module_manifest_refs(root: Path, organ_id: str) -> list[str]:
    """Collect source-module-manifest refs reachable via this organ's mechanisms.

    - Teleology: lets organs that own no direct examples still surface their source-module manifests through mechanism input_refs.
    - Guarantee: returns a sorted de-duplicated list of root-relative refs that end in "source_module_manifest.json" AND exist on disk, drawn from mechanisms whose runs_in includes organ_id.
    - Reads: core/mechanism_sources.json::mechanisms[].input_refs (and each candidate manifest path's existence).
    - Fails: returns [] when core/mechanism_sources.json is absent; otherwise raises whatever read_json_strict raises on invalid JSON.
    - Non-goal: does not read manifest bodies here, nor authorize export of any referenced source.
    """
    path = root / "core/mechanism_sources.json"
    if not path.is_file():
        return []
    payload = read_json_strict(path)
    refs: set[str] = set()
    for row in _as_list(payload.get("mechanisms")):
        if not isinstance(row, dict):
            continue
        if organ_id not in {str(item) for item in _as_list(row.get("runs_in"))}:
            continue
        for ref in _as_list(row.get("input_refs")):
            if not isinstance(ref, str):
                continue
            normalized = _root_relative_ref(root, ref.strip())
            if (
                normalized
                and Path(normalized).name.endswith("source_module_manifest.json")
                and (root / normalized).is_file()
            ):
                refs.add(normalized)
    return sorted(refs)


def _source_module_refs(root: Path, organ_id: str) -> list[str]:
    """Enumerate the existing source-module file refs for an organ (body-free).

    - Teleology: builds the per-organ source-file set that the language inventory counts and classifies.
    - Guarantee: returns a sorted de-duplicated list of root-relative refs that exist on disk: files under examples/<organ>/**/source_modules/**, plus declared manifest target_refs that resolve to existing files.
    - Reads: examples/<organ_id>/** paths and each referenced source_module_manifest.json::modules[].target_ref/path.
    - Fails: raises whatever read_json_strict raises on an invalid manifest; missing examples dir simply contributes nothing.
    - Non-goal: collects paths only — never reads or authorizes source bodies, language standards, or comment contracts.
    """
    examples_root = root / "examples" / organ_id
    refs: set[str] = set()
    if examples_root.is_dir():
        for path in examples_root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if "source_modules" not in relative.parts:
                continue
            refs.add(relative.as_posix())
    for manifest_ref in _source_module_manifest_refs(root, organ_id):
        manifest_path = root / manifest_ref
        payload = read_json_strict(manifest_path)
        if not isinstance(payload, dict):
            continue
        for module in _as_list(payload.get("modules")):
            if not isinstance(module, dict):
                continue
            target_ref = _root_relative_ref(
                root,
                _declared_target_ref(root, manifest_path, module),
            )
            if target_ref and (root / target_ref).is_file():
                refs.add(target_ref)
    return sorted(set(refs))


def _source_module_manifest_refs(root: Path, organ_id: str) -> list[str]:
    """Enumerate all source-module-manifest refs for an organ (direct + mechanism).

    - Teleology: the single entry point for "which manifests describe this organ's imported source" feeding the file graph and records.
    - Guarantee: returns a sorted de-duplicated list of root-relative refs to *source_module_manifest.json files: the mechanism-reachable set unioned with examples/<organ>/**/*source_module_manifest.json that exist on disk.
    - Reads: core/mechanism_sources.json (via the mechanism helper) and examples/<organ_id>/** manifest paths.
    - Fails: propagates read_json_strict errors from the mechanism helper on invalid JSON; a missing examples dir contributes nothing.
    - Non-goal: lists manifest paths only; does not parse module rows or authorize source export.
    """
    examples_root = root / "examples" / organ_id
    refs: set[str] = set(_mechanism_source_module_manifest_refs(root, organ_id))
    if examples_root.is_dir():
        for path in examples_root.rglob("*source_module_manifest.json"):
            if path.is_file():
                refs.add(path.relative_to(root).as_posix())
    return sorted(refs)


def _edge_ref_token(*refs: str) -> str:
    """Derive a stable short hash token from a tuple of ref strings.

    - Teleology: produces deterministic, collision-resistant edge_id suffixes so file-graph edges are stable across rebuilds.
    - Guarantee: returns the first 16 hex chars of the SHA-1 of the NUL-joined refs; identical inputs always yield the identical token.
    - Reads: only the passed ref strings; no filesystem, no source bodies.
    - Fails: never raises for string inputs.
    - Non-goal: this is an identity digest for edge keys, NOT a content-integrity or source-equivalence digest.
    """
    payload = "\0".join(refs).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:16]


def _declared_target_ref(
    root: Path,
    manifest_path: Path,
    module: dict[str, Any],
) -> str:
    """Compute a manifest module's declared public target ref.

    - Teleology: normalizes the source->target copy destination so the file graph can key edges on a stable target ref.
    - Guarantee: returns module.target_ref when present; else derives "microcosm-substrate/<manifest-dir>/<path>" from a relative path; returns an absolute/already-prefixed path unchanged; returns "" when neither target_ref nor path is set.
    - Reads: module.target_ref and module.path plus the manifest_path location relative to root.
    - Fails: never raises for well-formed inputs; absent fields yield "".
    - Non-goal: states where a body was copied TO; it does not authorize that the body may be exported or is public-safe.
    """
    target_ref = str(module.get("target_ref") or "").strip()
    if target_ref:
        return target_ref
    path_ref = str(module.get("path") or "").strip()
    if not path_ref:
        return ""
    if Path(path_ref).is_absolute() or path_ref.startswith("microcosm-substrate/"):
        return path_ref
    relative_target = manifest_path.parent.relative_to(root) / path_ref
    return (Path("microcosm-substrate") / relative_target).as_posix()


def _source_module_manifest_records(
    root: Path,
    accepted_organ_ids: list[str],
) -> list[dict[str, Any]]:
    """Flatten every accepted organ's source-module manifests into normalized records.

    - Teleology: the body-free row table that all source-module file-graph edges are computed from.
    - Guarantee: returns a list of per-module dict records carrying organ_id, manifest_ref/schema/bundle, module_id, source_ref, declared target_ref, material/import class, body_copied/body_in_receipt flags, required_anchors, and validation_refs.
    - Reads: each examples/<organ>/**/source_module_manifest.json::modules[] (via the manifest-ref helpers); non-dict payloads/modules are skipped.
    - Fails: raises whatever read_json_strict raises on an invalid manifest JSON.
    - Non-goal: records declared metadata only — body_copied is a manifest claim, NOT proof the body was exported or is public-safe; no release authority.
    """
    records: list[dict[str, Any]] = []
    for organ_id in sorted(accepted_organ_ids):
        for manifest_ref in _source_module_manifest_refs(root, organ_id):
            manifest_path = root / manifest_ref
            payload = read_json_strict(manifest_path)
            if not isinstance(payload, dict):
                continue
            modules = _as_list(payload.get("modules"))
            for module_index, module in enumerate(modules):
                if not isinstance(module, dict):
                    continue
                module_id = str(
                    module.get("module_id")
                    or module.get("material_id")
                    or f"module_{module_index}"
                )
                source_ref = str(module.get("source_ref") or "").strip()
                target_ref = _declared_target_ref(root, manifest_path, module)
                required_anchors = [
                    str(anchor).strip()
                    for anchor in _as_list(module.get("required_anchors"))
                    if str(anchor).strip()
                ]
                validation_refs = [
                    str(ref).strip()
                    for ref in _as_list(module.get("validation_refs"))
                    if str(ref).strip()
                ]
                source_import_class = str(
                    module.get("source_import_class")
                    or module.get("classification")
                    or payload.get("source_import_class")
                    or payload.get("classification")
                    or ""
                )
                records.append(
                    {
                        "organ_id": organ_id,
                        "manifest_ref": manifest_ref,
                        "manifest_schema_version": str(
                            payload.get("schema_version") or ""
                        ),
                        "manifest_bundle_id": str(
                            payload.get("bundle_id")
                            or payload.get("manifest_id")
                            or ""
                        ),
                        "module_index": module_index,
                        "module_id": module_id,
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "path": str(module.get("path") or ""),
                        "material_class": str(module.get("material_class") or ""),
                        "source_import_class": source_import_class,
                        "source_to_target_relation": str(
                            module.get("source_to_target_relation") or ""
                        ),
                        "source_role": str(module.get("source_role") or ""),
                        "body_copied": module.get("body_copied") is True,
                        "body_in_receipt": module.get("body_in_receipt") is True,
                        "required_anchors": required_anchors,
                        "required_anchor_count": len(required_anchors),
                        "validation_refs": validation_refs,
                    }
                )
    return records


def _file_relationship_edge(
    *,
    edge_id: str,
    organ_id: str,
    relation_type: str,
    source_id: str,
    target_id: str,
    evidence_class: str,
    source_projection: str,
    **metadata: Any,
) -> dict[str, Any]:
    """Construct one typed source-module file-graph edge dict.

    - Teleology: the single factory that stamps every file-graph edge with id/relation/source/target/evidence/projection and the file-graph authority string.
    - Guarantee: returns a dict with the six required fields plus authority == SOURCE_MODULE_FILE_GRAPH_AUTHORITY, with any extra **metadata merged in (metadata can override defaults).
    - Reads: only its arguments; no filesystem.
    - Fails: never raises.
    - Non-goal: an edge asserts a declared/typed relation between refs — not source-body semantics, API compatibility, or release/proof authority.
    """
    edge = {
        "edge_id": edge_id,
        "organ_id": organ_id,
        "relation_type": relation_type,
        "source_id": source_id,
        "target_id": target_id,
        "evidence_class": evidence_class,
        "source_projection": source_projection,
        "authority": SOURCE_MODULE_FILE_GRAPH_AUTHORITY,
    }
    edge.update(metadata)
    return edge


def _shard_ref(file_ref: str, anchor: str) -> str:
    """Format a per-anchor shard ref for a source/target file.

    - Teleology: gives required-anchor sub-spans of a file a stable addressable id for shard-level edges.
    - Guarantee: returns "<file_ref>::required_anchor[<anchor>]"; pure string interpolation.
    - Reads: only the two string arguments.
    - Fails: never raises.
    - Non-goal: names a declared anchor span; does not verify the anchor exists in the body or authorize the body.
    """
    return f"{file_ref}::required_anchor[{anchor}]"


def _source_module_file_graph(
    root: Path,
    accepted_organ_ids: list[str],
) -> dict[str, Any]:
    """Build the typed source-module file/shard relationship graph projection.

    - Teleology: projects manifest records into a queryable evidence graph of source->target copies, validation refs, anchor shards, and shared-macro-source peers.
    - Guarantee: returns a dict with schema_version "microcosm_source_module_file_graph_v0", the file-graph authority, counts (manifests/modules/source/target/validation/anchors/edges), relation_type_counts, query_affordances, by_organ, and the full edges list — all derived purely from declared manifest fields.
    - Reads: source_module_manifest records (transitively core/mechanism_sources.json + examples/<organ>/**/*source_module_manifest.json).
    - Fails: propagates read_json_strict errors from record collection on invalid manifest JSON; otherwise never raises.
    - Escalates-to: the per-organ source_module_manifest.json files (and this builder) regenerate it; it is not source-of-truth.
    - Non-goal: typed declared edges only — not source-body semantics, API compatibility, comment standard, or release/proof authority.
    """
    records = _source_module_manifest_records(root, accepted_organ_ids)
    edges: list[dict[str, Any]] = []
    edges_by_organ: dict[str, list[dict[str, Any]]] = {}

    def append_edge(edge: dict[str, Any]) -> None:
        edges.append(edge)
        edges_by_organ.setdefault(str(edge["organ_id"]), []).append(edge)

    records_by_source_ref: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        organ_id = str(record["organ_id"])
        source_ref = str(record.get("source_ref") or "")
        target_ref = str(record.get("target_ref") or "")
        if not source_ref or not target_ref:
            continue
        records_by_source_ref.setdefault(source_ref, {}).setdefault(
            target_ref,
            record,
        )
        append_edge(
            _file_relationship_edge(
                edge_id=(
                    f"{organ_id}:source_file.copied_to_public_target:"
                    f"{_edge_ref_token(record['manifest_ref'], source_ref, target_ref)}"
                ),
                organ_id=organ_id,
                relation_type="source_file.copied_to_public_target",
                source_id=f"source_file:{source_ref}",
                target_id=f"target_file:{target_ref}",
                evidence_class="source_module_manifest_declared_source_target_ref",
                source_projection="source_module_manifest.modules[].source_ref/target_ref",
                manifest_ref=record["manifest_ref"],
                manifest_schema_version=record["manifest_schema_version"],
                manifest_bundle_id=record["manifest_bundle_id"],
                module_index=record["module_index"],
                module_id=record["module_id"],
                source_ref=source_ref,
                target_ref=target_ref,
                material_class=record["material_class"],
                source_import_class=record["source_import_class"],
                source_to_target_relation=record["source_to_target_relation"],
                body_copied=record["body_copied"],
                body_in_receipt=record["body_in_receipt"],
                required_anchor_count=record["required_anchor_count"],
                validation_refs=record["validation_refs"],
            )
        )
        for validation_ref in record["validation_refs"]:
            append_edge(
                _file_relationship_edge(
                    edge_id=(
                        f"{organ_id}:source_file.validated_by_ref:"
                        f"{_edge_ref_token(record['manifest_ref'], source_ref, validation_ref)}"
                    ),
                    organ_id=organ_id,
                    relation_type="source_file.validated_by_ref",
                    source_id=f"source_file:{source_ref}",
                    target_id=f"validation_ref:{validation_ref}",
                    evidence_class="source_module_manifest_validation_ref",
                    source_projection="source_module_manifest.modules[].validation_refs",
                    manifest_ref=record["manifest_ref"],
                    manifest_schema_version=record["manifest_schema_version"],
                    module_index=record["module_index"],
                    module_id=record["module_id"],
                    source_ref=source_ref,
                    target_ref=target_ref,
                    validation_ref=validation_ref,
                    material_class=record["material_class"],
                    source_import_class=record["source_import_class"],
                )
            )
            append_edge(
                _file_relationship_edge(
                    edge_id=(
                        f"{organ_id}:target_file.validated_by_ref:"
                        f"{_edge_ref_token(record['manifest_ref'], target_ref, validation_ref)}"
                    ),
                    organ_id=organ_id,
                    relation_type="target_file.validated_by_ref",
                    source_id=f"target_file:{target_ref}",
                    target_id=f"validation_ref:{validation_ref}",
                    evidence_class="source_module_manifest_validation_ref",
                    source_projection="source_module_manifest.modules[].validation_refs",
                    manifest_ref=record["manifest_ref"],
                    manifest_schema_version=record["manifest_schema_version"],
                    module_index=record["module_index"],
                    module_id=record["module_id"],
                    source_ref=source_ref,
                    target_ref=target_ref,
                    validation_ref=validation_ref,
                    material_class=record["material_class"],
                    source_import_class=record["source_import_class"],
                )
            )
        for anchor_index, anchor in enumerate(record["required_anchors"]):
            source_shard_ref = _shard_ref(source_ref, anchor)
            target_shard_ref = _shard_ref(target_ref, anchor)
            shard_edge_token = _edge_ref_token(
                record["manifest_ref"],
                source_ref,
                target_ref,
                str(anchor_index),
            )
            append_edge(
                _file_relationship_edge(
                    edge_id=(
                        f"{organ_id}:source_shard.retained_as_public_target_shard:"
                        f"{shard_edge_token}"
                    ),
                    organ_id=organ_id,
                    relation_type="source_shard.retained_as_public_target_shard",
                    source_id=f"source_shard:{source_shard_ref}",
                    target_id=f"target_shard:{target_shard_ref}",
                    evidence_class="source_module_manifest_required_anchor_ref",
                    source_projection="source_module_manifest.modules[].required_anchors",
                    manifest_ref=record["manifest_ref"],
                    manifest_schema_version=record["manifest_schema_version"],
                    module_index=record["module_index"],
                    module_id=record["module_id"],
                    source_ref=source_ref,
                    target_ref=target_ref,
                    source_shard_ref=source_shard_ref,
                    target_shard_ref=target_shard_ref,
                    required_anchor=anchor,
                    required_anchor_index=anchor_index,
                    material_class=record["material_class"],
                    source_import_class=record["source_import_class"],
                )
            )
            for validation_ref in record["validation_refs"]:
                source_validation_edge_token = _edge_ref_token(
                    record["manifest_ref"],
                    source_shard_ref,
                    validation_ref,
                )
                target_validation_edge_token = _edge_ref_token(
                    record["manifest_ref"],
                    target_shard_ref,
                    validation_ref,
                )
                append_edge(
                    _file_relationship_edge(
                        edge_id=(
                            f"{organ_id}:source_shard.validated_by_ref:"
                            f"{source_validation_edge_token}"
                        ),
                        organ_id=organ_id,
                        relation_type="source_shard.validated_by_ref",
                        source_id=f"source_shard:{source_shard_ref}",
                        target_id=f"validation_ref:{validation_ref}",
                        evidence_class="source_module_manifest_anchor_validation_ref",
                        source_projection="source_module_manifest.modules[].required_anchors/validation_refs",
                        manifest_ref=record["manifest_ref"],
                        manifest_schema_version=record["manifest_schema_version"],
                        module_index=record["module_index"],
                        module_id=record["module_id"],
                        source_ref=source_ref,
                        target_ref=target_ref,
                        source_shard_ref=source_shard_ref,
                        target_shard_ref=target_shard_ref,
                        required_anchor=anchor,
                        required_anchor_index=anchor_index,
                        validation_ref=validation_ref,
                        material_class=record["material_class"],
                        source_import_class=record["source_import_class"],
                    )
                )
                append_edge(
                    _file_relationship_edge(
                        edge_id=(
                            f"{organ_id}:target_shard.validated_by_ref:"
                            f"{target_validation_edge_token}"
                        ),
                        organ_id=organ_id,
                        relation_type="target_shard.validated_by_ref",
                        source_id=f"target_shard:{target_shard_ref}",
                        target_id=f"validation_ref:{validation_ref}",
                        evidence_class="source_module_manifest_anchor_validation_ref",
                        source_projection="source_module_manifest.modules[].required_anchors/validation_refs",
                        manifest_ref=record["manifest_ref"],
                        manifest_schema_version=record["manifest_schema_version"],
                        module_index=record["module_index"],
                        module_id=record["module_id"],
                        source_ref=source_ref,
                        target_ref=target_ref,
                        source_shard_ref=source_shard_ref,
                        target_shard_ref=target_shard_ref,
                        required_anchor=anchor,
                        required_anchor_index=anchor_index,
                        validation_ref=validation_ref,
                        material_class=record["material_class"],
                        source_import_class=record["source_import_class"],
                    )
                )

    for source_ref, target_record_by_ref in sorted(records_by_source_ref.items()):
        if len(target_record_by_ref) < 2:
            continue
        target_records = [
            target_record_by_ref[target_ref]
            for target_ref in sorted(target_record_by_ref)
        ]
        for record in target_records:
            for peer_record in target_records:
                if peer_record["target_ref"] == record["target_ref"]:
                    continue
                peer_edge_token = _edge_ref_token(
                    source_ref,
                    record["target_ref"],
                    peer_record["target_ref"],
                )
                append_edge(
                    _file_relationship_edge(
                        edge_id=(
                            f"{record['organ_id']}:"
                            "target_file.shares_macro_source_with_target_file:"
                            f"{peer_edge_token}"
                        ),
                        organ_id=str(record["organ_id"]),
                        relation_type=(
                            "target_file.shares_macro_source_with_target_file"
                        ),
                        source_id=f"target_file:{record['target_ref']}",
                        target_id=f"target_file:{peer_record['target_ref']}",
                        evidence_class=(
                            "source_module_manifest_shared_macro_source_ref"
                        ),
                        source_projection=(
                            "source_module_manifest.modules[].source_ref"
                        ),
                        source_ref=source_ref,
                        target_ref=record["target_ref"],
                        peer_target_ref=peer_record["target_ref"],
                        peer_organ_id=peer_record["organ_id"],
                        manifest_ref=record["manifest_ref"],
                        peer_manifest_ref=peer_record["manifest_ref"],
                        module_id=record["module_id"],
                        peer_module_id=peer_record["module_id"],
                    )
                )

    relation_type_counts = Counter(str(edge["relation_type"]) for edge in edges)
    manifest_refs = sorted({str(record["manifest_ref"]) for record in records})
    source_refs = sorted(
        {str(record["source_ref"]) for record in records if record.get("source_ref")}
    )
    target_refs = sorted(
        {str(record["target_ref"]) for record in records if record.get("target_ref")}
    )
    validation_refs = sorted(
        {
            str(validation_ref)
            for record in records
            for validation_ref in record.get("validation_refs", [])
            if validation_ref
        }
    )
    shared_source_refs = sorted(
        source_ref
        for source_ref, target_record_by_ref in records_by_source_ref.items()
        if len(target_record_by_ref) > 1
    )
    validation_ref_counts = Counter(
        str(validation_ref)
        for record in records
        for validation_ref in record.get("validation_refs", [])
        if validation_ref
    )
    top_validation_refs = [
        {
            "validation_ref": validation_ref,
            "module_ref_count": count,
        }
        for validation_ref, count in validation_ref_counts.most_common(25)
    ]
    top_shared_source_refs = [
        {
            "source_ref": source_ref,
            "target_ref_count": len(records_by_source_ref[source_ref]),
        }
        for source_ref in sorted(
            shared_source_refs,
            key=lambda ref: (-len(records_by_source_ref[ref]), ref),
        )[:25]
    ]
    by_organ: dict[str, dict[str, Any]] = {}
    for organ_id in sorted(accepted_organ_ids):
        organ_records = [
            record for record in records if record.get("organ_id") == organ_id
        ]
        by_organ[organ_id] = {
            "manifest_count": len(
                {str(record["manifest_ref"]) for record in organ_records}
            ),
            "module_count": len(organ_records),
            "required_anchor_count": sum(
                int(record["required_anchor_count"]) for record in organ_records
            ),
            "source_ref_count": len(
                {
                    str(record["source_ref"])
                    for record in organ_records
                    if record.get("source_ref")
                }
            ),
            "target_ref_count": len(
                {
                    str(record["target_ref"])
                    for record in organ_records
                    if record.get("target_ref")
                }
            ),
        }

    return {
        "schema_version": "microcosm_source_module_file_graph_v0",
        "source": (
            "examples/<organ>/**/*source_module_manifest.json::modules plus "
            "core/mechanism_sources.json::mechanisms[].input_refs source-module manifests"
        ),
        "authority": SOURCE_MODULE_FILE_GRAPH_AUTHORITY,
        "accepted_organ_count": len(accepted_organ_ids),
        "manifest_count": len(manifest_refs),
        "module_count": len(records),
        "source_ref_count": len(source_refs),
        "target_ref_count": len(target_refs),
        "validation_ref_count": len(validation_refs),
        "module_validation_ref_count": sum(
            len(record.get("validation_refs", [])) for record in records
        ),
        "required_anchor_count": sum(
            int(record["required_anchor_count"]) for record in records
        ),
        "edge_count": len(edges),
        "relation_type_counts": dict(sorted(relation_type_counts.items())),
        "query_affordances": {
            "organs_with_source_module_manifests": sorted(
                organ_id
                for organ_id, counts in by_organ.items()
                if counts["manifest_count"] > 0
            ),
            "shared_source_ref_count": len(shared_source_refs),
            "top_shared_source_refs": top_shared_source_refs,
            "top_validation_refs": top_validation_refs,
            "relation_aliases": dict(sorted(RELATION_TYPE_ALIASES.items())),
        },
        "by_organ": by_organ,
        "edges": edges,
        "edges_by_organ": dict(sorted(edges_by_organ.items())),
    }


def _source_language_inventory(
    root: Path,
    accepted_organ_ids: list[str],
) -> dict[str, Any]:
    """Build the body-free source-language inventory across accepted organs.

    - Teleology: answers "what source languages does each accepted organ carry" using path extensions alone, never reading bodies.
    - Guarantee: returns a dict with schema_version "microcosm_source_language_inventory_v0", language/extension counts, organs_by_language, accepted_without_source_modules, and a by_organ breakdown.
    - Reads: examples/<organ>/**/source_modules/** plus manifest target refs (via _source_module_refs), classifying each by extension only.
    - Fails: propagates read_json_strict errors from ref collection on invalid manifest JSON.
    - Escalates-to: the source_module manifests + this builder regenerate it; authority is "body_free_source_path_inventory_only".
    - Non-goal: extension counting only — not a language standard, source-body authority, or comment contract.
    """
    language_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    organs_by_language: dict[str, list[str]] = {}
    by_organ: dict[str, dict[str, Any]] = {}
    source_module_organ_ids: list[str] = []

    for organ_id in sorted(accepted_organ_ids):
        source_refs = _source_module_refs(root, organ_id)
        organ_language_counts: Counter[str] = Counter()
        organ_extension_counts: Counter[str] = Counter()
        for ref in source_refs:
            language, extension = _source_language_for_ref(ref)
            organ_language_counts[language] += 1
            organ_extension_counts[extension] += 1
        if source_refs:
            source_module_organ_ids.append(organ_id)
        for language in organ_language_counts:
            organs_by_language.setdefault(language, []).append(organ_id)
        language_counts.update(organ_language_counts)
        extension_counts.update(organ_extension_counts)
        by_organ[organ_id] = {
            "source_module_file_count": len(source_refs),
            "language_families": sorted(organ_language_counts),
            "language_counts": dict(sorted(organ_language_counts.items())),
            "extension_counts": dict(sorted(organ_extension_counts.items())),
        }

    accepted_without_source_modules = sorted(
        set(accepted_organ_ids) - set(source_module_organ_ids)
    )
    return {
        "schema_version": "microcosm_source_language_inventory_v0",
        "source": (
            "examples/<organ>/**/source_modules/** plus source-module manifest "
            "target refs from direct examples and mechanism input_refs"
        ),
        "authority": (
            "body_free_source_path_inventory_only_not_language_standard_"
            "source_body_authority_or_comment_contract"
        ),
        "accepted_organ_count": len(accepted_organ_ids),
        "source_module_organ_count": len(source_module_organ_ids),
        "accepted_without_source_modules": accepted_without_source_modules,
        "language_counts": dict(sorted(language_counts.items())),
        "extension_counts": dict(sorted(extension_counts.items())),
        "organs_by_language": {
            language: sorted(organs)
            for language, organs in sorted(organs_by_language.items())
        },
        "by_organ": by_organ,
    }


def _source_language_adjacency(
    source_language_inventory: dict[str, Any],
) -> dict[str, Any]:
    """Derive per-organ source-language peer adjacency from the language inventory.

    - Teleology: turns the flat inventory into "which organs share a source language with me", surfacing mixed-language and python/ts/js organs.
    - Guarantee: returns a dict with schema_version "microcosm_source_language_adjacency_v0", language_family_organ_counts, mixed_language_organs, query_affordances, and per-organ rows of shared-language peers.
    - Reads: only the in-memory source_language_inventory (by_organ + organs_by_language); no filesystem.
    - Fails: raises KeyError if the inventory dict is missing the expected keys; otherwise never raises.
    - Escalates-to: coverage.source_language_inventory (its sole input) and this builder regenerate it.
    - Non-goal: language-family path adjacency only — not source semantics, API compatibility, comment standard, or lattice authority.
    """
    by_organ = source_language_inventory["by_organ"]
    organs_by_language = source_language_inventory["organs_by_language"]
    language_family_organ_counts = {
        language: len(organs)
        for language, organs in sorted(organs_by_language.items())
    }

    rows: dict[str, dict[str, Any]] = {}
    mixed_language_organs: list[dict[str, Any]] = []
    python_typescript_javascript_organs: list[str] = []
    for organ_id, inventory in sorted(by_organ.items()):
        language_families = list(inventory.get("language_families") or [])
        if not language_families:
            continue

        peer_organs_by_language: dict[str, list[str]] = {}
        shared_language_peer_organs: set[str] = set()
        for language in language_families:
            peers = [
                peer_organ_id
                for peer_organ_id in organs_by_language.get(language, [])
                if peer_organ_id != organ_id
            ]
            peer_organs_by_language[language] = peers
            shared_language_peer_organs.update(peers)

        row = {
            "organ_id": organ_id,
            "source_module_file_count": inventory["source_module_file_count"],
            "language_families": language_families,
            "language_counts": inventory["language_counts"],
            "peer_organs_by_language": peer_organs_by_language,
            "shared_language_peer_organ_count": len(shared_language_peer_organs),
            "shared_language_peer_organs": sorted(shared_language_peer_organs),
        }
        rows[organ_id] = row
        if len(language_families) > 1:
            mixed_language_organs.append(
                {
                    "organ_id": organ_id,
                    "language_families": language_families,
                    "source_module_file_count": inventory[
                        "source_module_file_count"
                    ],
                }
            )
        if {"python", "typescript", "javascript"}.issubset(language_families):
            python_typescript_javascript_organs.append(organ_id)

    return {
        "schema_version": "microcosm_source_language_adjacency_v0",
        "source_inventory_schema_version": source_language_inventory[
            "schema_version"
        ],
        "source": "coverage.source_language_inventory",
        "authority": (
            "body_free_source_language_family_adjacency_only_not_source_"
            "semantics_api_compatibility_comment_standard_or_not_lattice_authority"
        ),
        "accepted_organ_count": source_language_inventory["accepted_organ_count"],
        "source_module_organ_count": source_language_inventory[
            "source_module_organ_count"
        ],
        "language_family_organ_counts": language_family_organ_counts,
        "mixed_language_organs": sorted(
            mixed_language_organs,
            key=lambda row: str(row["organ_id"]),
        ),
        "query_affordances": {
            "typescript_bearing_organs": organs_by_language.get("typescript", []),
            "javascript_bearing_organs": organs_by_language.get("javascript", []),
            "python_bearing_organs": organs_by_language.get("python", []),
            "python_typescript_javascript_organs": sorted(
                python_typescript_javascript_organs
            ),
            "accepted_without_source_modules": source_language_inventory[
                "accepted_without_source_modules"
            ],
        },
        "rows": rows,
    }


def _relationship_edge(
    *,
    organ_id: str,
    relation_type: str,
    target_id: str,
    evidence_class: str,
    source_projection: str,
    **metadata: Any,
) -> dict[str, Any]:
    """Construct one typed organ-relationship topology edge dict.

    - Teleology: the factory that stamps each organ-topology edge with a deterministic id and the organ-relationship authority string.
    - Guarantee: returns a dict whose edge_id is "<organ_id>:<relation_type>:<target_id>", carrying organ_id/relation_type/target_id/evidence_class/source_projection and authority == ORGAN_RELATIONSHIP_TOPOLOGY_AUTHORITY, with **metadata merged in.
    - Reads: only its arguments; no filesystem.
    - Fails: never raises.
    - Non-goal: a typed evidence edge — not source-body semantics, API compatibility, comment standard, runtime order, or release authority.
    """
    edge = {
        "edge_id": f"{organ_id}:{relation_type}:{target_id}",
        "organ_id": organ_id,
        "relation_type": relation_type,
        "target_id": target_id,
        "evidence_class": evidence_class,
        "source_projection": source_projection,
        "authority": ORGAN_RELATIONSHIP_TOPOLOGY_AUTHORITY,
    }
    edge.update(metadata)
    return edge


def _standard_id_from_ref(ref: str) -> str:
    """Extract the standard_id stem from a standard file ref.

    - Teleology: turns a "standards/std_microcosm_<id>.json::..." ref into the bare standard_id used as an edge target.
    - Guarantee: returns the filename stem of the pre-"::" portion of the ref; returns "" for an empty ref.
    - Reads: only the ref string.
    - Fails: never raises.
    - Non-goal: derives an id token only; does not verify the standard file or registry row exists.
    """
    if not ref:
        return ""
    return Path(ref.split("::", 1)[0]).stem


def _organ_relationship_topology(
    rows: list[dict[str, Any]],
    source_language_adjacency: dict[str, Any],
    source_module_file_graph: dict[str, Any],
) -> dict[str, Any]:
    """Build the unified organ relationship topology projection.

    - Teleology: the one graph that joins organ rows, language-family adjacency, declared atlas wiring, standards/registry/concept/mechanism refs, and the source-module file graph into typed edges.
    - Guarantee: returns a dict with schema_version "microcosm_organ_relationship_topology_v0", the organ-relationship authority, an explicit anti_claims list, edge_count, relation_type_counts, query_affordances, and edges/edges_by_organ — folding in the source_module_file_graph edges.
    - Reads: only the in-memory rows + source_language_adjacency + source_module_file_graph arguments; no filesystem.
    - Fails: raises KeyError if an input projection lacks expected keys; otherwise never raises.
    - Escalates-to: rows[] + coverage.source_language_adjacency + coverage.source_module_file_graph regenerate it via build_organ_surface_contract.
    - Non-goal: typed evidence edges only — not source semantics, API compatibility, comment standard, runtime invocation order, or release/proof authority.
    """
    adjacency_rows = source_language_adjacency.get("rows", {})
    query_affordances = source_language_adjacency.get("query_affordances", {})
    accepted_organ_ids = {str(row.get("organ_id") or "") for row in rows}
    edges: list[dict[str, Any]] = []
    edges_by_organ: dict[str, list[dict[str, Any]]] = {}

    def append_edge(edge: dict[str, Any]) -> None:
        edges.append(edge)
        edges_by_organ.setdefault(str(edge["organ_id"]), []).append(edge)

    for row in sorted(rows, key=lambda item: str(item.get("organ_id") or "")):
        organ_id = str(row.get("organ_id") or "")
        source_language_inventory = row.get("source_language_inventory") or {}
        language_families = list(
            source_language_inventory.get("language_families") or []
        )
        source_module_file_count = int(
            source_language_inventory.get("source_module_file_count") or 0
        )
        language_counts = source_language_inventory.get("language_counts") or {}

        for language_family in language_families:
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.has_source_language_family",
                    target_id=f"source_language_family:{language_family}",
                    evidence_class="body_free_path_extension_inventory",
                    source_projection="rows[].source_language_inventory",
                    language_family=language_family,
                    source_module_file_count=source_module_file_count,
                    language_file_count=int(language_counts.get(language_family) or 0),
                )
            )

        if source_module_file_count == 0:
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.has_no_source_modules",
                    target_id="source_modules:none",
                    evidence_class="body_free_path_extension_inventory_absence",
                    source_projection="rows[].source_language_inventory",
                )
            )

        if len(language_families) > 1:
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.has_mixed_source_language_families",
                    target_id=(
                        "source_language_family_set:"
                        + ",".join(sorted(language_families))
                    ),
                    evidence_class="body_free_path_extension_inventory",
                    source_projection="rows[].source_language_inventory",
                    language_families=sorted(language_families),
                    source_module_file_count=source_module_file_count,
                )
            )

        adjacency_row = adjacency_rows.get(organ_id, {})
        peer_organs_by_language = adjacency_row.get("peer_organs_by_language") or {}
        for peer_organ_id in adjacency_row.get("shared_language_peer_organs") or []:
            shared_language_families = [
                language_family
                for language_family, peer_ids in sorted(
                    peer_organs_by_language.items()
                )
                if peer_organ_id in peer_ids
            ]
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.shares_source_language_family_with",
                    target_id=f"organ:{peer_organ_id}",
                    evidence_class="source_language_family_peer_adjacency",
                    source_projection="coverage.source_language_adjacency",
                    peer_organ_id=peer_organ_id,
                    shared_language_families=shared_language_families,
                )
            )

        standard_ref = str(row.get("standard_ref") or "")
        standard_id = _standard_id_from_ref(standard_ref)
        if standard_id:
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.has_microcosm_standard",
                    target_id=f"standard:{standard_id}",
                    evidence_class="standard_file_presence",
                    source_projection="rows[].standard_ref",
                    target_ref=standard_ref,
                )
            )

        standards_registry_ref = str(row.get("standards_registry_ref") or "")
        if standard_id and standards_registry_ref:
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.has_standards_registry_row",
                    target_id=f"standards_registry:{standard_id}",
                    evidence_class="standards_registry_row_presence",
                    source_projection="rows[].standards_registry_ref",
                    target_ref=standards_registry_ref,
                )
            )

        concept_projection_ref = str(row.get("concept_projection_ref") or "")
        if concept_projection_ref:
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.has_concept_route_ref",
                    target_id=concept_projection_ref,
                    evidence_class="concept_mechanism_projection_ref",
                    source_projection="rows[].concept_projection_ref",
                    target_ref=concept_projection_ref,
                    concept_mechanism_route_ref=row.get("concept_mechanism_route_ref"),
                )
            )

        mechanism_projection_ref = str(row.get("mechanism_projection_ref") or "")
        if mechanism_projection_ref:
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.has_mechanism_route_ref",
                    target_id=mechanism_projection_ref,
                    evidence_class="concept_mechanism_projection_ref",
                    source_projection="rows[].mechanism_projection_ref",
                    target_ref=mechanism_projection_ref,
                    concept_mechanism_route_ref=row.get("concept_mechanism_route_ref"),
                )
            )

        for target_organ_id in row.get("wires_to") or []:
            target_organ_id = str(target_organ_id or "").strip()
            if not target_organ_id:
                continue
            append_edge(
                _relationship_edge(
                    organ_id=organ_id,
                    relation_type="organ.wires_to.organ",
                    target_id=f"organ:{target_organ_id}",
                    evidence_class="organ_atlas_declared_wiring",
                    source_projection="rows[].wires_to",
                    target_organ_id=target_organ_id,
                    target_ref=(
                        f"core/organ_atlas.json::organs[organ_id={target_organ_id}]"
                    ),
                    target_status=(
                        "accepted_current_authority"
                        if target_organ_id in accepted_organ_ids
                        else "unresolved_organ_id"
                    ),
                )
            )

    for edge in source_module_file_graph.get("edges") or []:
        if isinstance(edge, dict):
            append_edge(edge)

    relation_type_counts = Counter(str(edge["relation_type"]) for edge in edges)
    mixed_language_organs = [
        str(row.get("organ_id"))
        for row in source_language_adjacency.get("mixed_language_organs", [])
        if row.get("organ_id")
    ]
    return {
        "schema_version": "microcosm_organ_relationship_topology_v0",
        "source": {
            "organ_rows": "rows",
            "source_language_adjacency": "coverage.source_language_adjacency",
            "organ_atlas_wiring": "rows[].wires_to",
            "source_module_file_graph": "coverage.source_module_file_graph",
        },
        "source_adjacency_schema_version": source_language_adjacency[
            "schema_version"
        ],
        "source_module_file_graph_schema_version": source_module_file_graph[
            "schema_version"
        ],
        "authority": ORGAN_RELATIONSHIP_TOPOLOGY_AUTHORITY,
        "anti_claims": [
            "typed evidence edges only",
            "not source-body semantics",
            "not API compatibility",
            "not comment standard",
            "not lattice or public graph authority",
            "not runtime invocation order",
            "not release or proof-correctness authority",
        ],
        "accepted_organ_count": len(rows),
        "edge_count": len(edges),
        "relation_type_counts": dict(sorted(relation_type_counts.items())),
        "query_affordances": {
            "typescript_bearing_organs": query_affordances.get(
                "typescript_bearing_organs",
                [],
            ),
            "javascript_bearing_organs": query_affordances.get(
                "javascript_bearing_organs",
                [],
            ),
            "python_bearing_organs": query_affordances.get(
                "python_bearing_organs",
                [],
            ),
            "python_typescript_javascript_organs": query_affordances.get(
                "python_typescript_javascript_organs",
                [],
            ),
            "accepted_without_source_modules": query_affordances.get(
                "accepted_without_source_modules",
                [],
            ),
            "mixed_language_organs": sorted(mixed_language_organs),
            "source_module_manifest_organs": source_module_file_graph[
                "query_affordances"
            ]["organs_with_source_module_manifests"],
            "top_shared_source_refs": source_module_file_graph[
                "query_affordances"
            ]["top_shared_source_refs"],
            "top_validation_refs": source_module_file_graph[
                "query_affordances"
            ]["top_validation_refs"],
            "relation_aliases": dict(sorted(RELATION_TYPE_ALIASES.items())),
        },
        "edges": edges,
        "edges_by_organ": edges_by_organ,
    }


def _acceptance_plan_rows(root: Path) -> list[dict[str, Any]]:
    """Read the first-wave acceptance plan's accepted-organ rows.

    - Teleology: supplies the acceptance-side rows that disposition/metadata audits compare the registry against.
    - Guarantee: returns the dict rows of first_wave_acceptance.json::accepted_current_authority_organs that carry an organ_id; returns [] when the file is absent.
    - Reads: core/acceptance/first_wave_acceptance.json (ACCEPTANCE_PLAN_REF).
    - Fails: returns [] on a missing file; otherwise raises whatever read_json_strict raises on invalid JSON.
    - Non-goal: does not authorize acceptance/release; provides comparison rows only.
    """
    path = root / ACCEPTANCE_PLAN_REF
    if not path.is_file():
        return []
    payload = read_json_strict(path)
    return [
        row
        for row in _as_list(payload.get("accepted_current_authority_organs"))
        if isinstance(row, dict) and row.get("organ_id")
    ]


def _runtime_step_ids() -> set[str]:
    """Collect the organ_ids that have a wired runtime-shell step.

    - Teleology: lets the audit check that each accepted organ appears as a runtime step (the runtime_step surface).
    - Guarantee: returns the set of str organ_id values over runtime_shell.RUNTIME_STEPS.
    - Reads: microcosm_core.runtime_shell.RUNTIME_STEPS (lazily imported to avoid an import cycle).
    - Fails: raises ImportError/AttributeError if runtime_shell or RUNTIME_STEPS is unavailable.
    - Non-goal: presence is a wiring signal, not proof a step runs correctly or is released.
    """
    from microcosm_core import runtime_shell

    return {str(step.organ_id) for step in runtime_shell.RUNTIME_STEPS}


def _cli_command_names(root: Path) -> set[str]:
    """Statically extract the set of registered CLI subcommand names.

    - Teleology: lets the audit check each organ has a CLI command without importing/executing the CLI module.
    - Guarantee: returns the set of string literals passed to subparser.add_parser(...) and to _add_bundle_parser(_, name, ...) found by AST-walking cli.py.
    - Reads: src/microcosm_core/cli.py source text (parsed with ast, never executed).
    - Fails: raises FileNotFoundError if cli.py is absent, or SyntaxError if it does not parse.
    - Non-goal: detects declared command names by static shape only; does not run commands or authorize their behavior.
    """
    source = root / "src/microcosm_core/cli.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    commands: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            commands.add(node.args[0].value)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "_add_bundle_parser"
            and len(node.args) > 1
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            commands.add(node.args[1].value)
    return commands


def _cli_command_from_first_command(first_command: str) -> str:
    """Extract the subcommand token from an atlas 'microcosm <cmd> ...' string.

    - Teleology: maps an organ's declared first_command to the CLI subcommand it should resolve to.
    - Guarantee: returns parts[1] when the shell-split command starts with "microcosm" and has >= 2 tokens; else "".
    - Reads: only the first_command string.
    - Fails: never raises; an unparsable command (shlex ValueError) or non-microcosm command returns "".
    - Non-goal: parses the declared token only; does not verify the command is registered (caller checks against cli_command_names).
    """
    try:
        parts = shlex.split(first_command)
    except ValueError:
        return ""
    if len(parts) < 2 or parts[0] != "microcosm":
        return ""
    return parts[1]


def _expected_cli_command(
    *, organ_id: str, atlas_row: dict[str, Any], cli_command_names: set[str]
) -> str:
    """Resolve the CLI subcommand expected for an organ, preferring a registered name.

    - Teleology: picks the single command the audit should require for an organ, reconciling declared command vs the organ-id slug.
    - Guarantee: returns the atlas-declared command if it is in cli_command_names; else the "<organ_id with - for _>" slug if that is registered; else the declared command, or the slug as final fallback.
    - Reads: atlas_row.first_command and the in-memory cli_command_names set.
    - Fails: never raises.
    - Non-goal: chooses an expected name; does not assert the command runs or is released (caller marks presence).
    """
    first_command = str(atlas_row.get("first_command") or "")
    declared_command = _cli_command_from_first_command(first_command)
    if declared_command in cli_command_names:
        return declared_command
    slug_command = organ_id.replace("_", "-")
    if slug_command in cli_command_names:
        return slug_command
    return declared_command or slug_command


def _validator_command_module(command: str) -> str:
    """Extract the `-m <module>` target from a validator command string.

    - Teleology: lets the audit confirm a registry validator_command actually invokes the organ's own runner module.
    - Guarantee: returns the token following the first "-m" in the shell-split command; else "".
    - Reads: only the command string.
    - Fails: never raises; an unparsable command (shlex ValueError) or no "-m" returns "".
    - Non-goal: extracts the declared module token only; does not run the validator or prove it passes.
    """
    try:
        parts = shlex.split(command)
    except ValueError:
        return ""
    for index, part in enumerate(parts[:-1]):
        if part == "-m":
            return parts[index + 1]
    return ""


def _global_doctrine_surfaces(root: Path) -> dict[str, Any]:
    """Audit the global concept/mechanism entry-route + standards presence.

    - Teleology: the repo-wide discoverability gate (one entry route + two standards) that must hold independent of any single organ.
    - Guarantee: returns a status dict; status == "pass" iff the entry route is present with >0 population specimens AND >0 activation receipts AND both concept and mechanism standard files exist, else "blocked".
    - Reads: atlas/entry_packet.json::concept_mechanism_entry_route plus standards/std_microcosm_concept.json and std_microcosm_mechanism.json existence.
    - Fails: raises whatever read_json_strict raises if atlas/entry_packet.json is missing or invalid; otherwise reports "blocked" rather than raising.
    - Non-goal: gates concept/mechanism discoverability only — not per-organ completion or release.
    """
    entry_packet = read_json_strict(root / "atlas/entry_packet.json")
    route = entry_packet.get("concept_mechanism_entry_route")
    route_present = isinstance(route, dict)
    specimen_count = len(_as_list(route.get("population_specimens"))) if route_present else 0
    activation_count = len(_as_list(route.get("activation_receipts"))) if route_present else 0
    concept_standard_present = (root / CONCEPT_STANDARD_REF).is_file()
    mechanism_standard_present = (root / MECHANISM_STANDARD_REF).is_file()
    status = (
        "pass"
        if route_present
        and specimen_count > 0
        and activation_count > 0
        and concept_standard_present
        and mechanism_standard_present
        else "blocked"
    )
    return {
        "status": status,
        "entry_route_ref": ENTRY_ROUTE_REF,
        "entry_route_present": route_present,
        "population_specimen_count": specimen_count,
        "activation_receipt_count": activation_count,
        "concept_standard_ref": CONCEPT_STANDARD_REF,
        "concept_standard_present": concept_standard_present,
        "mechanism_standard_ref": MECHANISM_STANDARD_REF,
        "mechanism_standard_present": mechanism_standard_present,
        "authority": "global_doctrine_entry_route_for_concept_mechanism_discoverability_not_per_organ_completion",
    }


def build_organ_surface_contract(root: str | Path | None = None) -> dict[str, Any]:
    """Build the full organ-surface-contract audit projection for the substrate.

    - Teleology: the central derived audit asserting every accepted organ exposes its 14 discoverability surfaces plus the global doctrine surfaces, with truth-accounting on synthetic vs real acceptance.
    - Guarantee: returns a payload dict with schema_version SCHEMA_VERSION, authority_posture AUTHORITY_POSTURE, status "pass" iff errors is empty else "blocked", an errors list of {code,surface,organ_ids}, full coverage block, and per-organ rows; deterministic for a fixed substrate tree.
    - Reads: core/organ_registry.json, organ_atlas.json, standards_registry.json, acceptance plan, source-module manifests, runtime_shell.RUNTIME_STEPS, cli.py, entry_packet.json (root defaults to microcosm_root()).
    - Fails: raises read_json_strict / ImportError / SyntaxError if a required registry/source input is missing or malformed; surface absences are reported as errors with status "blocked", not raised.
    - Escalates-to: the source registries it reads are authority; this output is regenerated by re-running the builder/`microcosm organ-surface-contract`.
    - Non-goal: authority_posture is "derived_surface_audit_not_source_authority" — surface presence proves discoverability/wiring only, NOT release, proof correctness, private-root equivalence, provider execution, or source authority.
    """
    root = Path(root) if root is not None else microcosm_root()
    root = root.resolve()
    registry = read_json_strict(root / "core/organ_registry.json")
    registry_rows = _accepted_registry_rows(registry)
    registry_by_id = {str(row.get("organ_id")): row for row in registry_rows}
    registry_order_ids = [str(row.get("organ_id")) for row in registry_rows]
    source_language_inventory = _source_language_inventory(root, registry_order_ids)
    source_language_adjacency = _source_language_adjacency(source_language_inventory)
    source_module_file_graph = _source_module_file_graph(root, registry_order_ids)
    acceptance_rows = _acceptance_plan_rows(root)
    acceptance_plan_by_id = {
        str(row.get("organ_id")): row for row in acceptance_rows if row.get("organ_id")
    }
    acceptance_plan_ids = [str(row.get("organ_id")) for row in acceptance_rows]
    atlas_by_id = _atlas_rows_by_organ(root)
    standards_by_id = _standards_registry_by_id(root)
    organ_doctrine_by_id = {
        str(row.get("organ_id")): row
        for row in build_organ_doctrine_rows(root)
        if isinstance(row, dict) and row.get("organ_id")
    }
    runtime_step_ids = _runtime_step_ids()
    cli_command_names = _cli_command_names(root)
    global_doctrine_surfaces = _global_doctrine_surfaces(root)

    missing: dict[str, list[str]] = {key: [] for key in MISSING_SURFACE_KEYS}
    disposition_audits: list[dict[str, Any]] = []
    acceptance_metadata_audits: list[dict[str, Any]] = []
    invalid_disposition_organs: list[str] = []
    disposition_mismatch_organs: list[str] = []
    registry_acceptance_disposition_mismatch_organs: list[str] = []
    missing_acceptance_metadata_organs: list[str] = []
    registry_acceptance_metadata_mismatch_organs: list[str] = []
    disposition_counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for organ_id in sorted(registry_by_id):
        registry_row = registry_by_id[organ_id]
        runner = str(registry_row.get("runner") or "")
        validator_command = str(registry_row.get("validator_command") or "")
        runner_source_ref = _runner_source_ref(runner)
        runner_source_present = bool(runner_source_ref) and (
            root / runner_source_ref
        ).is_file()
        validator_module = _validator_command_module(validator_command)
        validator_command_ok = bool(validator_command) and validator_module == runner

        current_authority_receipt_ref = str(
            registry_row.get("current_authority_receipt") or ""
        )
        current_authority_receipt_present = bool(
            current_authority_receipt_ref
        ) and _resolve_ref(root, current_authority_receipt_ref).is_file()
        acceptance_plan_row = acceptance_plan_by_id.get(organ_id, {})
        acceptance_plan_row_present = (
            bool(acceptance_plan_row)
            and acceptance_plan_row.get("status") == "accepted_current_authority"
        )
        disposition_audit = _disposition_audit_for_row(
            registry_row,
            acceptance_plan_row,
        )
        acceptance_metadata_audit = _acceptance_metadata_audit_for_row(
            registry_row,
            acceptance_plan_row,
        )
        disposition_audits.append(disposition_audit)
        acceptance_metadata_audits.append(acceptance_metadata_audit)
        disposition_counts[
            str(
                disposition_audit.get("real_substrate_disposition")
                or "missing"
            )
        ] += 1
        fixture_manifest_ref = (
            f"core/fixture_manifests/{organ_id}.fixture_manifest.json"
        )
        fixture_manifest_present = (root / fixture_manifest_ref).is_file()

        atlas_row = atlas_by_id.get(organ_id, {})
        cli_command = _expected_cli_command(
            organ_id=organ_id,
            atlas_row=atlas_row,
            cli_command_names=cli_command_names,
        )
        cli_command_present = bool(cli_command) and cli_command in cli_command_names
        paper_module_ref = _paper_module_ref(root, organ_id, atlas_row)
        paper_module_present = bool(paper_module_ref) and (
            root / paper_module_ref
        ).is_file()

        standard_id = f"std_microcosm_{organ_id}"
        standard_ref = f"standards/{standard_id}.json"
        standard_present = (root / standard_ref).is_file()
        standards_registry_present = standard_id in standards_by_id
        runtime_step_present = organ_id in runtime_step_ids
        organ_doctrine_row = organ_doctrine_by_id.get(organ_id, {})
        concept_projection_present = bool(organ_doctrine_row.get("concept_binding"))
        mechanism_projection_present = bool(organ_doctrine_row.get("mechanism_binding"))

        checks = {
            "runner_source_file": runner_source_present,
            "validator_command": validator_command_ok,
            "current_authority_receipt": current_authority_receipt_present,
            "acceptance_plan_row": acceptance_plan_row_present,
            "acceptance_metadata": acceptance_metadata_audit["ok"],
            "synthetic_acceptance_disposition": disposition_audit["ok"],
            "fixture_manifest": fixture_manifest_present,
            "atlas_card": bool(atlas_row),
            "paper_module": paper_module_present,
            "standard_file": standard_present,
            "standards_registry_row": standards_registry_present,
            "runtime_step": runtime_step_present,
            "cli_command": cli_command_present,
            "concept_projection_row": concept_projection_present,
            "mechanism_projection_row": mechanism_projection_present,
        }

        if not runner_source_present:
            missing["runner_source_files"].append(organ_id)
        if not validator_command_ok:
            missing["validator_commands"].append(organ_id)
        if not current_authority_receipt_present:
            missing["current_authority_receipts"].append(organ_id)
        if not acceptance_plan_row_present:
            missing["acceptance_plan_rows"].append(organ_id)
        if disposition_audit["missing"]:
            missing["synthetic_acceptance_dispositions"].append(organ_id)
        if disposition_audit["invalid"]:
            invalid_disposition_organs.append(organ_id)
        if disposition_audit["fixture_authority_mismatch"]:
            disposition_mismatch_organs.append(organ_id)
        if "registry_acceptance_disposition_mismatch" in disposition_audit["mismatch"]:
            registry_acceptance_disposition_mismatch_organs.append(organ_id)
        if acceptance_metadata_audit["missing"]:
            missing_acceptance_metadata_organs.append(organ_id)
        if acceptance_metadata_audit["mismatch"]:
            registry_acceptance_metadata_mismatch_organs.append(organ_id)
        if not fixture_manifest_present:
            missing["fixture_manifests"].append(organ_id)
        if not atlas_row:
            missing["atlas_cards"].append(organ_id)
        if not paper_module_present:
            missing["paper_modules"].append(organ_id)
        if not standard_present:
            missing["standard_files"].append(organ_id)
        if not standards_registry_present:
            missing["standards_registry_rows"].append(organ_id)
        if not runtime_step_present:
            missing["runtime_steps"].append(organ_id)
        if not cli_command_present:
            missing["cli_commands"].append(organ_id)
        if not concept_projection_present:
            missing["concept_projection_rows"].append(organ_id)
        if not mechanism_projection_present:
            missing["mechanism_projection_rows"].append(organ_id)
        wires_to = sorted(
            {
                str(target).strip()
                for target in _as_list(atlas_row.get("wires_to"))
                if str(target).strip()
            }
        )

        rows.append(
            {
                "organ_id": organ_id,
                "registry_ref": (
                    "core/organ_registry.json::implemented_organs"
                    f"[organ_id={organ_id}]"
                ),
                "runner": runner,
                "runner_source_ref": runner_source_ref,
                "validator_command": validator_command,
                "real_substrate_disposition": disposition_audit[
                    "real_substrate_disposition"
                ],
                "synthetic_acceptance_disposition": disposition_audit[
                    "synthetic_acceptance_disposition"
                ],
                "disposition_audit": disposition_audit,
                "acceptance_metadata_audit": acceptance_metadata_audit,
                "current_authority_receipt_ref": current_authority_receipt_ref,
                "acceptance_plan_ref": (
                    f"{ACCEPTANCE_PLAN_REF}::accepted_current_authority_organs"
                    f"[organ_id={organ_id}]"
                ),
                "fixture_manifest_ref": fixture_manifest_ref,
                "atlas_card_ref": f"core/organ_atlas.json::organs[organ_id={organ_id}]",
                "paper_module_ref": paper_module_ref,
                "standard_ref": standard_ref,
                "standards_registry_ref": (
                    f"core/standards_registry.json::standards[standard_id={standard_id}]"
                ),
                "runtime_step_ref": (
                    f"microcosm_core.runtime_shell.RUNTIME_STEPS::{organ_id}"
                ),
                "cli_command": cli_command,
                "concept_projection_ref": (
                    f"concept_mechanism_projection_read_model.organ_doctrine_rows"
                    f"[organ_id={organ_id}].concept_binding"
                ),
                "mechanism_projection_ref": (
                    f"concept_mechanism_projection_read_model.organ_doctrine_rows"
                    f"[organ_id={organ_id}].mechanism_binding"
                ),
                "concept_mechanism_route_ref": ENTRY_ROUTE_REF,
                "wires_to": wires_to,
                "source_language_inventory": source_language_inventory[
                    "by_organ"
                ].get(
                    organ_id,
                    {
                        "source_module_file_count": 0,
                        "language_families": [],
                        "language_counts": {},
                        "extension_counts": {},
                    },
                ),
                "checks": checks,
            }
        )

    if not registry_rows:
        missing["registry_rows"].append("accepted_current_authority")

    missing = {key: sorted(values) for key, values in missing.items()}
    blocking_missing = {key: values for key, values in missing.items() if values}
    unexpected_acceptance_plan_rows = sorted(set(acceptance_plan_ids) - set(registry_order_ids))
    acceptance_plan_order_matches_registry = acceptance_plan_ids == registry_order_ids
    errors = [
        {
            "code": f"missing_{key}",
            "surface": key,
            "organ_ids": values,
        }
        for key, values in blocking_missing.items()
    ]
    if unexpected_acceptance_plan_rows:
        errors.append(
            {
                "code": "unexpected_acceptance_plan_rows",
                "surface": "acceptance_plan_rows",
                "organ_ids": unexpected_acceptance_plan_rows,
            }
        )
    if acceptance_plan_ids and not acceptance_plan_order_matches_registry:
        errors.append(
            {
                "code": "acceptance_plan_order_mismatch",
                "surface": "acceptance_plan_rows",
                "organ_ids": acceptance_plan_ids,
            }
        )
    if invalid_disposition_organs:
        errors.append(
            {
                "code": "invalid_synthetic_acceptance_disposition",
                "surface": "synthetic_acceptance_dispositions",
                "organ_ids": sorted(invalid_disposition_organs),
            }
        )
    if disposition_mismatch_organs:
        errors.append(
            {
                "code": "synthetic_acceptance_progress_flag_mismatch",
                "surface": "synthetic_acceptance_dispositions",
                "organ_ids": sorted(disposition_mismatch_organs),
            }
        )
    if registry_acceptance_disposition_mismatch_organs:
        errors.append(
            {
                "code": "registry_acceptance_disposition_mismatch",
                "surface": "real_substrate_disposition",
                "organ_ids": sorted(registry_acceptance_disposition_mismatch_organs),
            }
        )
    if missing_acceptance_metadata_organs:
        errors.append(
            {
                "code": "missing_acceptance_metadata_fields",
                "surface": "acceptance_plan_rows",
                "organ_ids": sorted(missing_acceptance_metadata_organs),
            }
        )
    if registry_acceptance_metadata_mismatch_organs:
        errors.append(
            {
                "code": "registry_acceptance_metadata_mismatch",
                "surface": "acceptance_plan_rows",
                "organ_ids": sorted(registry_acceptance_metadata_mismatch_organs),
            }
        )
    if global_doctrine_surfaces["status"] != "pass":
        errors.append(
            {
                "code": "global_concept_mechanism_surface_blocked",
                "surface": "concept_mechanism_entry_route",
                "organ_ids": [],
            }
        )
    organ_relationship_topology = _organ_relationship_topology(
        rows,
        source_language_adjacency,
        source_module_file_graph,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if not errors else "blocked",
        "authority_posture": AUTHORITY_POSTURE,
        "root": str(root),
        "accepted_organ_count": len(registry_rows),
        "surface_contract": {
            "source": "core/organ_registry.json::implemented_organs[status=accepted_current_authority]",
            "required_per_organ_surfaces": [
                "runner_source_file",
                "validator_command",
                "current_authority_receipt",
                "acceptance_plan_row",
                "synthetic_acceptance_disposition",
                "fixture_manifest",
                "atlas_card",
                "paper_module",
                "standard_file",
                "standards_registry_row",
                "runtime_step",
                "cli_command",
                "concept_projection_row",
                "mechanism_projection_row",
            ],
            "global_doctrine_surfaces": [
                ENTRY_ROUTE_REF,
                CONCEPT_STANDARD_REF,
                MECHANISM_STANDARD_REF,
            ],
            "anti_claim": (
                "Surface presence proves discoverability and wiring only; it does "
                "not claim release, proof correctness, private-root equivalence, "
                "provider execution, product completeness, or source authority."
            ),
        },
        "global_doctrine_surfaces": global_doctrine_surfaces,
        "coverage": {
            "missing": missing,
            "runtime_step_count": len(runtime_step_ids),
            "cli_command_count": len(cli_command_names),
            "atlas_card_count": len(atlas_by_id),
            "standards_registry_row_count": len(standards_by_id),
            "acceptance_plan_row_count": len(acceptance_plan_by_id),
            "acceptance_plan_order_matches_registry": acceptance_plan_order_matches_registry,
            "unexpected_acceptance_plan_rows": unexpected_acceptance_plan_rows,
            "acceptance_plan_ref": ACCEPTANCE_PLAN_REF,
            "organ_doctrine_row_count": len(organ_doctrine_by_id),
            "disposition_coverage": {
                "schema_version": "microcosm_real_substrate_disposition_coverage_v1",
                "allowed_dispositions": sorted(
                    ALLOWED_SYNTHETIC_ACCEPTANCE_DISPOSITIONS
                ),
                "required_registry_field": "real_substrate_disposition",
                "required_acceptance_field": "real_substrate_disposition",
                "required_synthetic_field": "synthetic_acceptance_disposition",
                "accepted_organ_count": len(registry_rows),
                "covered_count": sum(
                    1 for audit in disposition_audits if audit["ok"]
                ),
                "synthetic_accepted_count": sum(
                    1
                    for audit in disposition_audits
                    if audit["is_synthetic_acceptance"]
                ),
                "retained_regression_validator_count": disposition_counts.get(
                    RETAINED_REGRESSION_VALIDATOR_DISPOSITION,
                    0,
                ),
                "real_substrate_capsule_count": disposition_counts.get(
                    REAL_SUBSTRATE_DISPOSITION,
                    0,
                ),
                "disposition_counts": dict(sorted(disposition_counts.items())),
                "missing_synthetic_acceptance_dispositions": sorted(
                    missing["synthetic_acceptance_dispositions"]
                ),
                "invalid_synthetic_acceptance_disposition": sorted(
                    invalid_disposition_organs
                ),
                "synthetic_acceptance_progress_flag_mismatch": sorted(
                    disposition_mismatch_organs
                ),
                "registry_acceptance_disposition_mismatch": sorted(
                    registry_acceptance_disposition_mismatch_organs
                ),
                "audits": sorted(
                    disposition_audits,
                    key=lambda audit: str(audit["organ_id"]),
                ),
            },
            "acceptance_metadata_coverage": {
                "schema_version": "microcosm_acceptance_metadata_coverage_v1",
                "checked_fields": list(ACCEPTANCE_REGISTRY_PARITY_FIELDS),
                "accepted_organ_count": len(registry_rows),
                "covered_count": sum(
                    1 for audit in acceptance_metadata_audits if audit["ok"]
                ),
                "missing_acceptance_metadata_fields": sorted(
                    missing_acceptance_metadata_organs
                ),
                "registry_acceptance_metadata_mismatch": sorted(
                    registry_acceptance_metadata_mismatch_organs
                ),
                "audits": sorted(
                    acceptance_metadata_audits,
                    key=lambda audit: str(audit["organ_id"]),
                ),
            },
            "source_language_inventory": {
                key: value
                for key, value in source_language_inventory.items()
                if key != "by_organ"
            },
            "source_language_adjacency": source_language_adjacency,
            "source_module_file_graph": source_module_file_graph,
            "organ_relationship_topology": organ_relationship_topology,
        },
        "errors": errors,
        "rows": rows,
    }


def build_card(payload: dict[str, Any]) -> dict[str, Any]:
    """Project a full audit payload into a compact counts-only card.

    - Teleology: the first-screen summary surface — missing-surface counts and coverage rollups without the per-organ rows.
    - Guarantee: returns a dict with schema_version "microcosm_organ_surface_contract_card_v0", echoing status/authority_posture/accepted_organ_count, missing_surface_counts, the coverage rollups, and previewed (CARD_PREVIEW_LIMIT) shared-source/validation/mixed-language lists with omitted counts.
    - Reads: only the in-memory payload from build_organ_surface_contract; no filesystem.
    - Fails: raises KeyError if the payload is not a build_organ_surface_contract output (missing expected keys).
    - Escalates-to: the full payload (drilldown "microcosm organ-surface-contract") and the builder that produced it.
    - Non-goal: a generated summary view — carries forward the same anti_claim; not release or source authority.
    """
    missing = payload["coverage"]["missing"]
    disposition_coverage = payload["coverage"]["disposition_coverage"]
    acceptance_metadata_coverage = payload["coverage"][
        "acceptance_metadata_coverage"
    ]
    source_language_inventory = payload["coverage"]["source_language_inventory"]
    source_language_adjacency = payload["coverage"]["source_language_adjacency"]
    source_module_file_graph = payload["coverage"]["source_module_file_graph"]
    organ_relationship_topology = payload["coverage"][
        "organ_relationship_topology"
    ]
    query_affordances = source_language_adjacency["query_affordances"]
    topology_query_affordances = organ_relationship_topology["query_affordances"]
    top_shared_source_refs = source_module_file_graph["query_affordances"][
        "top_shared_source_refs"
    ]
    top_validation_refs = source_module_file_graph["query_affordances"][
        "top_validation_refs"
    ]
    mixed_language_organs = topology_query_affordances["mixed_language_organs"]
    return {
        "schema_version": "microcosm_organ_surface_contract_card_v0",
        "status": payload["status"],
        "authority_posture": payload["authority_posture"],
        "accepted_organ_count": payload["accepted_organ_count"],
        "missing_surface_counts": {
            key: len(values) for key, values in missing.items() if values
        },
        "disposition_coverage": {
            "covered_count": disposition_coverage["covered_count"],
            "accepted_organ_count": disposition_coverage["accepted_organ_count"],
            "synthetic_accepted_count": disposition_coverage[
                "synthetic_accepted_count"
            ],
            "missing_synthetic_acceptance_dispositions": disposition_coverage[
                "missing_synthetic_acceptance_dispositions"
            ],
            "invalid_synthetic_acceptance_disposition": disposition_coverage[
                "invalid_synthetic_acceptance_disposition"
            ],
            "synthetic_acceptance_progress_flag_mismatch": disposition_coverage[
                "synthetic_acceptance_progress_flag_mismatch"
            ],
            "registry_acceptance_disposition_mismatch": disposition_coverage[
                "registry_acceptance_disposition_mismatch"
            ],
        },
        "acceptance_metadata_coverage": {
            "covered_count": acceptance_metadata_coverage["covered_count"],
            "accepted_organ_count": acceptance_metadata_coverage[
                "accepted_organ_count"
            ],
            "checked_fields": acceptance_metadata_coverage["checked_fields"],
            "missing_acceptance_metadata_fields": acceptance_metadata_coverage[
                "missing_acceptance_metadata_fields"
            ],
            "registry_acceptance_metadata_mismatch": acceptance_metadata_coverage[
                "registry_acceptance_metadata_mismatch"
            ],
        },
        "source_language_inventory": {
            "schema_version": source_language_inventory["schema_version"],
            "source_module_organ_count": source_language_inventory[
                "source_module_organ_count"
            ],
            "accepted_organ_count": source_language_inventory["accepted_organ_count"],
            "accepted_without_source_modules_count": len(
                source_language_inventory["accepted_without_source_modules"]
            ),
            "language_counts": source_language_inventory["language_counts"],
            "authority": source_language_inventory["authority"],
        },
        "source_language_adjacency": {
            "schema_version": source_language_adjacency["schema_version"],
            "source_inventory_schema_version": source_language_adjacency[
                "source_inventory_schema_version"
            ],
            "source_module_organ_count": source_language_adjacency[
                "source_module_organ_count"
            ],
            "accepted_organ_count": source_language_adjacency[
                "accepted_organ_count"
            ],
            "language_family_organ_counts": source_language_adjacency[
                "language_family_organ_counts"
            ],
            "mixed_language_organ_count": len(
                source_language_adjacency["mixed_language_organs"]
            ),
            "typescript_bearing_organs": query_affordances[
                "typescript_bearing_organs"
            ],
            "python_typescript_javascript_organs": query_affordances[
                "python_typescript_javascript_organs"
            ],
            "accepted_without_source_modules": query_affordances[
                "accepted_without_source_modules"
            ],
            "authority": source_language_adjacency["authority"],
        },
        "source_module_file_graph": {
            "schema_version": source_module_file_graph["schema_version"],
            "source": source_module_file_graph["source"],
            "accepted_organ_count": source_module_file_graph[
                "accepted_organ_count"
            ],
            "manifest_count": source_module_file_graph["manifest_count"],
            "module_count": source_module_file_graph["module_count"],
            "source_ref_count": source_module_file_graph["source_ref_count"],
            "target_ref_count": source_module_file_graph["target_ref_count"],
            "validation_ref_count": source_module_file_graph[
                "validation_ref_count"
            ],
            "module_validation_ref_count": source_module_file_graph[
                "module_validation_ref_count"
            ],
            "required_anchor_count": source_module_file_graph[
                "required_anchor_count"
            ],
            "edge_count": source_module_file_graph["edge_count"],
            "relation_type_counts": source_module_file_graph[
                "relation_type_counts"
            ],
            "shared_source_ref_count": source_module_file_graph[
                "query_affordances"
            ]["shared_source_ref_count"],
            "top_shared_source_refs": top_shared_source_refs[:CARD_PREVIEW_LIMIT],
            "top_shared_source_refs_omitted_count": max(
                0, len(top_shared_source_refs) - CARD_PREVIEW_LIMIT
            ),
            "top_validation_refs": top_validation_refs[:CARD_PREVIEW_LIMIT],
            "top_validation_refs_omitted_count": max(
                0, len(top_validation_refs) - CARD_PREVIEW_LIMIT
            ),
            "preview_limit": CARD_PREVIEW_LIMIT,
            "authority": source_module_file_graph["authority"],
        },
        "organ_relationship_topology": {
            "schema_version": organ_relationship_topology["schema_version"],
            "source": organ_relationship_topology["source"],
            "source_adjacency_schema_version": organ_relationship_topology[
                "source_adjacency_schema_version"
            ],
            "source_module_file_graph_schema_version": (
                organ_relationship_topology[
                    "source_module_file_graph_schema_version"
                ]
            ),
            "accepted_organ_count": organ_relationship_topology[
                "accepted_organ_count"
            ],
            "edge_count": organ_relationship_topology["edge_count"],
            "relation_type_counts": organ_relationship_topology[
                "relation_type_counts"
            ],
            "typescript_bearing_organs": topology_query_affordances[
                "typescript_bearing_organs"
            ],
            "python_typescript_javascript_organs": topology_query_affordances[
                "python_typescript_javascript_organs"
            ],
            "accepted_without_source_modules": topology_query_affordances[
                "accepted_without_source_modules"
            ],
            "mixed_language_organs": mixed_language_organs[:CARD_PREVIEW_LIMIT],
            "mixed_language_organs_omitted_count": max(
                0, len(mixed_language_organs) - CARD_PREVIEW_LIMIT
            ),
            "preview_limit": CARD_PREVIEW_LIMIT,
            "authority": organ_relationship_topology["authority"],
            "anti_claims": organ_relationship_topology["anti_claims"],
        },
        "global_doctrine_surfaces": payload["global_doctrine_surfaces"],
        "drilldown": "microcosm organ-surface-contract",
        "anti_claim": payload["surface_contract"]["anti_claim"],
    }


def build_organ_relationship_topology_card(
    payload: dict[str, Any],
    *,
    organ_id: str | None = None,
    relation_type: str | None = None,
    source_ref: str | None = None,
    target_ref: str | None = None,
    manifest_ref: str | None = None,
    shard_ref: str | None = None,
    validation_ref: str | None = None,
) -> dict[str, Any]:
    """Project a filtered slice of the organ relationship topology into a query card.

    - Teleology: the shell-queryable lens over topology edges, filterable by organ/relation/source/target/manifest/shard/validation ref.
    - Guarantee: returns a dict with schema_version "microcosm_organ_relationship_topology_card_v0", the resolved filters (relation_type alias-expanded via RELATION_TYPE_ALIASES), filtered edges/edges_by_organ, filtered + total relation_type_counts, available_relation_types, query examples, and the topology authority/anti_claims.
    - Reads: only payload["coverage"]["organ_relationship_topology"]; no filesystem.
    - Fails: raises KeyError if payload lacks the topology coverage block; None filters simply match all edges (never raises).
    - Escalates-to: the full topology in the payload and build_organ_surface_contract that regenerates it.
    - Non-goal: a generated typed-edge query view — not source semantics, API compatibility, runtime order, or release/proof authority.
    """
    topology = payload["coverage"]["organ_relationship_topology"]
    relation_type_filter = RELATION_TYPE_ALIASES.get(
        relation_type or "",
        relation_type,
    )

    def edge_matches(edge: dict[str, Any]) -> bool:
        if organ_id is not None and edge["organ_id"] != organ_id:
            return False
        if (
            relation_type_filter is not None
            and edge["relation_type"] != relation_type_filter
        ):
            return False
        if source_ref is not None and edge.get("source_ref") != source_ref:
            return False
        if target_ref is not None and target_ref not in {
            edge.get("target_ref"),
            edge.get("peer_target_ref"),
        }:
            return False
        if manifest_ref is not None and manifest_ref not in {
            edge.get("manifest_ref"),
            edge.get("peer_manifest_ref"),
        }:
            return False
        if shard_ref is not None and shard_ref not in {
            edge.get("source_shard_ref"),
            edge.get("target_shard_ref"),
        }:
            return False
        if validation_ref is not None and edge.get("validation_ref") != validation_ref:
            return False
        return True

    filtered_edges = [
        edge
        for edge in topology["edges"]
        if edge_matches(edge)
    ]
    relation_type_counts = Counter(
        str(edge["relation_type"]) for edge in filtered_edges
    )
    edges_by_organ: dict[str, list[dict[str, Any]]] = {}
    for edge in filtered_edges:
        edges_by_organ.setdefault(str(edge["organ_id"]), []).append(edge)

    return {
        "schema_version": "microcosm_organ_relationship_topology_card_v0",
        "status": payload["status"],
        "authority_posture": payload["authority_posture"],
        "topology_schema_version": topology["schema_version"],
        "source": topology["source"],
        "source_adjacency_schema_version": topology[
            "source_adjacency_schema_version"
        ],
        "accepted_organ_count": topology["accepted_organ_count"],
        "total_edge_count": topology["edge_count"],
        "edge_count": len(filtered_edges),
        "total_relation_type_counts": topology["relation_type_counts"],
        "relation_type_counts": dict(sorted(relation_type_counts.items())),
        "available_relation_types": sorted(topology["relation_type_counts"]),
        "filters": {
            "organ_id": organ_id,
            "relation_type": relation_type_filter,
            "requested_relation_type": relation_type,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "manifest_ref": manifest_ref,
            "shard_ref": shard_ref,
            "validation_ref": validation_ref,
        },
        "query_affordances": topology["query_affordances"],
        "query_examples": [
            "microcosm organ-topology --organ batch7_macro_engines_capsule",
            (
                "microcosm organ-topology --relation-type "
                "organ.has_source_language_family"
            ),
            (
                "microcosm organ-topology --organ "
                "batch7_macro_engines_capsule --relation-type "
                "organ.has_source_language_family"
            ),
            (
                "microcosm organ-topology --relation-type file_to_file "
                "--source-ref system/lib/agent_execution_trace.py"
            ),
            (
                "microcosm organ-topology --relation-type shard_to_shard "
                "--source-ref system/lib/agent_execution_trace.py"
            ),
            (
                "microcosm organ-topology --relation-type file_validated_by "
                "--source-ref system/lib/agent_execution_trace.py"
            ),
            (
                "microcosm organ-topology --validation-ref "
                "microcosm-substrate/tests/test_agent_route_observability_runtime.py::"
                "test_agent_trace_route_repair_imports_public_macro_body_refactor"
            ),
        ],
        "edges": filtered_edges,
        "edges_by_organ": dict(sorted(edges_by_organ.items())),
        "authority": topology["authority"],
        "anti_claims": topology["anti_claims"],
        "drilldown": "microcosm organ-surface-contract",
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry: audit accepted Microcosm organ discoverability surfaces.

    - Teleology: command-line front door to the organ-surface contract audit and its topology query surface.
    - Guarantee: prints the full audit payload, the card, or a filtered relationship-topology card as JSON; returns 0 iff payload status is "pass".
    - Reads: --root microcosm-substrate via build_organ_surface_contract.
    - Writes: optional --out JSON file via write_json_atomic.
    - When-needed: auditing organ surface completeness or querying organ relationship edges from the shell.
    - Fails: payload status != "pass" -> nonzero exit -> return code 1.
    """
    parser = argparse.ArgumentParser(
        prog="organ-surface-contract",
        description="Audit accepted Microcosm organ discoverability surfaces.",
    )
    parser.add_argument(
        "--root",
        default=str(microcosm_root()),
        help="microcosm-substrate root; defaults to installed/public root",
    )
    parser.add_argument("--out", help="optional JSON output path")
    parser.add_argument(
        "--card",
        action="store_true",
        help="emit compact counts instead of the full per-organ rows",
    )
    parser.add_argument(
        "--topology",
        action="store_true",
        help="emit the direct organ relationship topology query surface",
    )
    parser.add_argument(
        "--organ",
        help="filter topology edges to one organ_id; implies --topology",
    )
    parser.add_argument(
        "--relation-type",
        help="filter topology edges to one relation_type; implies --topology",
    )
    parser.add_argument(
        "--source-ref",
        help="filter topology edges to one source_ref; implies --topology",
    )
    parser.add_argument(
        "--target-ref",
        help="filter topology edges to one target_ref or peer_target_ref; implies --topology",
    )
    parser.add_argument(
        "--manifest-ref",
        help="filter topology edges to one source-module manifest ref; implies --topology",
    )
    parser.add_argument(
        "--shard-ref",
        help=(
            "filter topology edges to one source_shard_ref or target_shard_ref; "
            "implies --topology"
        ),
    )
    parser.add_argument(
        "--validation-ref",
        help="filter topology edges to one authored validation_ref; implies --topology",
    )
    args = parser.parse_args(argv)

    payload = build_organ_surface_contract(args.root)
    if (
        args.topology
        or args.organ
        or args.relation_type
        or args.source_ref
        or args.target_ref
        or args.manifest_ref
        or args.shard_ref
        or args.validation_ref
    ):
        output = build_organ_relationship_topology_card(
            payload,
            organ_id=args.organ,
            relation_type=args.relation_type,
            source_ref=args.source_ref,
            target_ref=args.target_ref,
            manifest_ref=args.manifest_ref,
            shard_ref=args.shard_ref,
            validation_ref=args.validation_ref,
        )
    elif args.card:
        output = build_card(payload)
    else:
        output = payload
    if args.out:
        write_json_atomic(Path(args.out), output)
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
