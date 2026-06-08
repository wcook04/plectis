#!/usr/bin/env python3
"""Build the fail-closed release claim-language gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = Path("docs/dissemination/release_claim_language_gate_v0.json")
PUBLICATION_MANIFEST = Path("publication_manifest.yaml")

CLAIM_SURFACE_GROUPS = {
    "paper_modules",
    "standards",
    "documentation",
    "public_microcosm",
}
CLAIM_SURFACE_SUFFIXES = {
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
PUBLIC_MICROCOSM_DOC_NAMES = {
    "README.md",
    "pyproject.toml",
    "publication_gate.json",
    "artifact_manifest.json",
}
SKIP_OUTPUT_PATHS = {DEFAULT_OUTPUT.as_posix()}
FINGERPRINT_EXCLUDED_SCAN_PATHS = {
    DEFAULT_OUTPUT.as_posix(),
    "docs/dissemination/public_toggle_readiness_gate_v0.json",
    "docs/dissemination/release_public_toggle_closure_map_v0.json",
    "docs/dissemination/release_operator_action_matrix_v0.json",
}
RISKY_PHRASES = [
    {
        "id": "release_ready",
        "family": "claim_overreach",
        "pattern": r"\brelease[- ]ready\b|\bready to publish\b|\bpublication[- ]ready\b|\bpublish[- ]ready\b",
    },
    {
        "id": "open_source",
        "family": "claim_overreach",
        "pattern": r"\bopen[- ]source(?:d)?\b|\bopen sourced\b",
    },
    {
        "id": "source_available",
        "family": "claim_overreach",
        "pattern": r"\bsource[- ]available\b",
    },
    {
        "id": "clean_clone_proven",
        "family": "claim_overreach",
        "pattern": r"\bclean[- ]clone proven\b|\bclean clone proof\b",
    },
    {
        "id": "publicly_reproducible",
        "family": "claim_overreach",
        "pattern": r"\bpublicly reproducible\b|\bpublic reproduction\b",
    },
    {
        "id": "publicly_released",
        "family": "claim_overreach",
        "pattern": r"\bpublicly released\b|\bpublic release\b",
    },
    {
        "id": "production_ready",
        "family": "claim_overreach",
        "pattern": r"\bproduction[- ]ready\b|\binstall target\b",
    },
    {
        "id": "release_authorization_disclaimer",
        "family": "private_control_plane_leak",
        "pattern": (
            r"\b(?:does\s+not|doesn't|do\s+not|don't|cannot|not)\s+"
            r"(?:authorize|authorise|approve|grant)\s+"
            r"(?:a\s+)?(?:public\s+)?(?:release|publication|publishing|hosting|recipient\s+sends?)\b"
        ),
    },
    {
        "id": "release_authority_surface",
        "family": "private_control_plane_leak",
        "pattern": (
            r"\b(?:release|publication|publishing|hosting|recipient\s+sends?)\s+"
            r"(?:authority|authorization|authorisation|approval|gate|owner|decision)\b"
        ),
    },
    {
        "id": "internal_release_control_state",
        "family": "private_control_plane_leak",
        "pattern": (
            r"\b(?:public\s+toggle\s+remains\s+(?:red|no[- ]go)|"
            r"release\s+action:\s*none|release_action\"\s*:\s*\"none|"
            r"route\s+to\s+(?:the\s+)?(?:dissemination|release)\s+(?:owner|gate))\b"
        ),
    },
]
NEGATIVE_CONTEXT_MARKERS = [
    "not ",
    "not-",
    "banned framing",
    "banned framings",
    "blocked phrase",
    "blocked phrases",
    "do not",
    "do_not_assert",
    "must not",
    "must separate",
    "does not",
    "does not claim",
    "cannot",
    "never",
    "no ",
    "no-",
    "non-claim",
    "non-claims",
    "without",
    "forbidden",
    "forbidden current wording",
    "forbidden phrase",
    "incorrect wording",
    "blocks",
    "blocked",
    "red / not ready",
    "not ready",
    "not released",
    "not claimed",
    "not a",
    "do_not_claim",
    "no-go",
    "no_go",
    "does_not_authorize",
    "forbidden_current_wording",
    "claim_guard",
    "claim guard",
    "open_source_claim_allowed\": false",
    "source_available_claim_allowed\": false",
    "open-source claim allowed: no",
    "source-available claim allowed: no",
    "absent_blocks_open_source_claim",
    "absent phrase",
    "absent phrases",
    "required absent",
    "no public license",
    "release_action\": \"none\"",
    "release action: none",
    "critique and guidance only",
]
META_FORBIDDEN_CONTEXT_MARKERS = [
    "banned framing",
    "banned framings",
    "blocked phrase",
    "blocked phrases",
    "forbidden phrase",
    "forbidden current wording",
    "incorrect wording",
    "do_not_assert",
    "do_not_claim",
    "forbidden_current_wording",
]


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _repo_path(path: Path, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _short_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _artifact_class(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if path.endswith("search-index.json"):
        return "search_index"
    if path.startswith("sites/microcosm/") and suffix == ".html":
        return "rendered_html"
    if suffix == ".json":
        return "public_json"
    if suffix == ".md":
        return "source_markdown"
    if suffix in {".yaml", ".yml", ".toml"}:
        return "source_config"
    if suffix in {".ts", ".tsx", ".py"}:
        return "source_code"
    return "public_bound_artifact"


def _rendered_path_or_url(path: str) -> str | None:
    if path.startswith("sites/microcosm/"):
        return path
    if path.startswith("microcosm-substrate/"):
        return "sites/microcosm/<generated-from-source>"
    return None


def _owner_surface(hit: dict[str, Any], artifact_class: str) -> str:
    path = str(hit["path"])
    group_id = str(hit.get("group_id") or "")
    if path.startswith("sites/microcosm/"):
        return "microcosm_public_site_projection"
    if path.startswith("microcosm-substrate/"):
        return "microcosm_substrate_source"
    if artifact_class in {"public_json", "source_config"}:
        return f"publication_manifest:{group_id}:config"
    return f"publication_manifest:{group_id}:source"


def _generated_from(hit: dict[str, Any], artifact_class: str) -> str | None:
    path = str(hit["path"])
    group_id = str(hit.get("group_id") or "")
    if path.startswith("sites/microcosm/"):
        return "microcosm_public_site_builder"
    if artifact_class in {"search_index", "rendered_html"}:
        return "public_projection_builder"
    return f"publication_manifest:{group_id}"


def _audience(hit: dict[str, Any]) -> str:
    classification = str(hit["classification"])
    if classification == "boundary_or_negative_context":
        return "maintainer_or_meta_reader"
    if classification == "needs_review":
        return "public_reader_review"
    return "public_reader"


def _speech_act(hit: dict[str, Any]) -> str:
    classification = str(hit["classification"])
    phrase_family = str(hit["phrase_family"])
    phrase_id = str(hit["phrase_id"])
    if classification == "boundary_or_negative_context":
        return "meta_boundary_example"
    if classification == "needs_review":
        return "ambiguous_public_claim_label"
    if phrase_family == "private_control_plane_leak":
        if phrase_id == "release_authorization_disclaimer":
            return "private_release_authorization_disclaimer"
        if phrase_id == "internal_release_control_state":
            return "private_release_state_disclosure"
        return "private_release_authority_reference"
    return "public_capability_or_readiness_claim"


def _phrase_subtype(hit: dict[str, Any]) -> str:
    phrase_id = str(hit["phrase_id"])
    text = f"{hit.get('match', '')}\n{hit.get('line_text', '')}".lower()
    if phrase_id == "release_authorization_disclaimer":
        return "negative_authorization_disclaimer"
    if phrase_id == "internal_release_control_state":
        if "release_action" in text or "release action" in text:
            return "machine_release_state"
        if "route to" in text:
            return "private_owner_routing"
        return "public_toggle_state"
    if phrase_id == "release_authority_surface":
        if "owner" in text:
            return "private_owner_routing"
        if "gate" in text:
            return "private_gate_reference"
        return "authority_language"
    return phrase_id


def _triage_disposition(hit: dict[str, Any], artifact_class: str) -> str:
    classification = str(hit["classification"])
    if classification == "boundary_or_negative_context":
        return "test_or_meta_example_allowed"
    if classification == "needs_review":
        return "needs_operator_decision"
    if str(hit["phrase_family"]) == "private_control_plane_leak":
        if str(hit["phrase_id"]) == "internal_release_control_state" and artifact_class in {
            "public_json",
            "search_index",
        }:
            return "exclude_from_public_projection"
        if artifact_class in {"rendered_html", "search_index"}:
            return "claim_blocked_owner_reentry"
        return "source_rewrite"
    return "source_rewrite"


def _rewrite_strategy(hit: dict[str, Any], disposition: str) -> str:
    phrase_id = str(hit["phrase_id"])
    if disposition == "test_or_meta_example_allowed":
        return "Keep only as explicit forbidden-example or policy-test text."
    if disposition == "needs_operator_decision":
        return "Operator must decide whether this is public claim copy or a harmless label."
    if disposition == "exclude_from_public_projection":
        return "Remove private release state from public JSON/search projection or replace with public artifact limits."
    if phrase_id == "release_authorization_disclaimer":
        return "Replace release-authorization disclaimers with public artifact semantics and current evidence limits."
    if phrase_id == "release_authority_surface":
        return "Name the public evidence status without exposing release owners, gates, or authorization mechanics."
    if phrase_id == "internal_release_control_state":
        return "Move release-control state to private receipts; public copy should state only public-visible availability."
    return "Downgrade readiness/release wording to evidence-backed, non-release public description."


def _canonical_public_boundary_triage(hits: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    disposition_counts: dict[str, int] = {}
    for hit in sorted(
        hits,
        key=lambda row: (
            str(row["classification"]),
            str(row["path"]),
            int(row["line"]),
            str(row["phrase_id"]),
            str(row["match"]).lower(),
        ),
    ):
        artifact_class = _artifact_class(str(hit["path"]))
        disposition = _triage_disposition(hit, artifact_class)
        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
        line_text = str(hit.get("line_text") or "")
        rows.append(
            {
                "row_id": "rclg_"
                + _short_digest(
                    "|".join(
                        [
                            str(hit["path"]),
                            str(hit["line"]),
                            str(hit["phrase_id"]),
                            str(hit["match"]).lower(),
                            line_text,
                        ]
                    )
                ),
                "source_path": str(hit["path"]),
                "rendered_path_or_url": _rendered_path_or_url(str(hit["path"])),
                "artifact_class": artifact_class,
                "audience": _audience(hit),
                "speech_act": _speech_act(hit),
                "phrase_family": str(hit["phrase_family"]),
                "phrase_id": str(hit["phrase_id"]),
                "phrase_subtype": _phrase_subtype(hit),
                "line": int(hit["line"]),
                "line_text_or_redacted_excerpt": line_text[:280],
                "disposition": disposition,
                "rewrite_strategy": _rewrite_strategy(hit, disposition),
                "owner_surface": _owner_surface(hit, artifact_class),
                "claim_status": str(hit["classification"]),
                "generated_from": _generated_from(hit, artifact_class),
                "safe_to_autofix": False,
                "validation_ref": "./repo-python tools/meta/dissemination/release_claim_language_gate.py --check --assert-clear",
            }
        )
    return {
        "schema_version": "release_claim_language_gate_public_boundary_triage_v0",
        "canonical_occurrence_count": len(rows),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "rows": rows,
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return payload


def _entry_paths(manifest: dict[str, Any]) -> list[tuple[str, Path]]:
    include = manifest.get("include", {})
    if not isinstance(include, dict):
        return []
    rows: list[tuple[str, Path]] = []
    for group_id, group in include.items():
        if group_id not in CLAIM_SURFACE_GROUPS or not isinstance(group, dict):
            continue
        entries = group.get("entries", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                path_value = entry.get("path")
            else:
                path_value = entry
            if isinstance(path_value, str):
                rows.append((str(group_id), Path(path_value)))
    return rows


def _iter_claim_files(repo_root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group_id, rel_path in _entry_paths(manifest):
        source = repo_root / rel_path
        candidates: list[Path]
        if source.is_dir():
            if group_id == "public_microcosm":
                candidates = [
                    path
                    for path in source.rglob("*")
                    if path.is_file()
                    and path.name in PUBLIC_MICROCOSM_DOC_NAMES
                    and path.suffix in CLAIM_SURFACE_SUFFIXES
                ]
            else:
                candidates = [
                    path
                    for path in source.rglob("*")
                    if path.is_file() and path.suffix in CLAIM_SURFACE_SUFFIXES
                ]
        elif source.is_file() and source.suffix in CLAIM_SURFACE_SUFFIXES:
            candidates = [source]
        else:
            candidates = []

        for path in candidates:
            rel = _rel(path, repo_root)
            if rel in SKIP_OUTPUT_PATHS or rel in seen:
                continue
            seen.add(rel)
            rows.append({"group_id": group_id, "path": rel})
    return sorted(rows, key=lambda row: (row["group_id"], row["path"]))


def _line_context(lines: list[str], index: int) -> str:
    start = max(0, index - 8)
    end = min(len(lines), index + 4)
    return "\n".join(lines[start:end]).strip()


def _inside_fenced_block(lines: list[str], index: int) -> bool:
    in_block = False
    for line in lines[: index + 1]:
        if line.lstrip().startswith("```"):
            in_block = not in_block
    return in_block


def _classify_hit(
    line: str,
    context: str,
    *,
    phrase_family: str = "claim_overreach",
    in_fenced_block: bool = False,
) -> tuple[str, str]:
    normalized_context = context.lower()
    normalized_line = line.lower()
    context_has_negative_marker = any(
        marker in normalized_context for marker in NEGATIVE_CONTEXT_MARKERS
    )
    context_has_meta_marker = any(
        marker in normalized_context for marker in META_FORBIDDEN_CONTEXT_MARKERS
    )
    line_has_meta_marker = any(marker in normalized_line for marker in META_FORBIDDEN_CONTEXT_MARKERS)
    if phrase_family == "private_control_plane_leak":
        if line_has_meta_marker or (in_fenced_block and context_has_meta_marker):
            return (
                "boundary_or_negative_context",
                "private control-plane wording is present only as explicitly forbidden example text",
            )
        return (
            "active_claim_blocker",
            "public-reader copy must not expose release/publication authorization or private control-plane status language",
        )
    if any(marker in normalized_line for marker in NEGATIVE_CONTEXT_MARKERS):
        return (
            "boundary_or_negative_context",
            "line marks the phrase as forbidden, blocked, omitted, or explicitly not claimed",
        )
    if in_fenced_block and context_has_negative_marker:
        return (
            "boundary_or_negative_context",
            "fenced example is introduced by nearby forbidden, blocked, omitted, or not-claimed context",
        )
    if re.search(r"\b(is|are|has been|now|currently)\b", normalized_line):
        return (
            "active_claim_blocker",
            "risky phrase appears in affirmative wording without a nearby downgrade marker",
        )
    if context_has_negative_marker:
        return (
            "boundary_or_negative_context",
            "nearby text marks the phrase as forbidden, blocked, omitted, or explicitly not claimed",
        )
    return (
        "needs_review",
        "risky phrase lacks a deterministic negative-context marker",
    )


def _scan_file(repo_root: Path, file_row: dict[str, Any]) -> list[dict[str, Any]]:
    path = repo_root / file_row["path"]
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        for phrase in RISKY_PHRASES:
            pattern = re.compile(str(phrase["pattern"]), re.IGNORECASE)
            for match in pattern.finditer(line):
                context = _line_context(lines, line_number - 1)
                classification, reason = _classify_hit(
                    line,
                    context,
                    phrase_family=str(phrase.get("family") or "claim_overreach"),
                    in_fenced_block=_inside_fenced_block(lines, line_number - 1),
                )
                hits.append(
                    {
                        "phrase_id": phrase["id"],
                        "phrase_family": str(phrase.get("family") or "claim_overreach"),
                        "match": match.group(0),
                        "classification": classification,
                        "classification_reason": reason,
                        "path": file_row["path"],
                        "line": line_number,
                        "group_id": file_row["group_id"],
                        "line_text": line.strip(),
                        "context": context,
                    }
                )
    return hits


def build_gate(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest_path = repo_root / PUBLICATION_MANIFEST
    manifest = _read_manifest(manifest_path)
    claim_files = _iter_claim_files(repo_root, manifest)
    hits: list[dict[str, Any]] = []
    for file_row in claim_files:
        hits.extend(_scan_file(repo_root, file_row))

    classification_counts: dict[str, int] = {
        "active_claim_blocker": 0,
        "boundary_or_negative_context": 0,
        "needs_review": 0,
    }
    phrase_counts: dict[str, int] = {}
    for hit in hits:
        classification = str(hit["classification"])
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        phrase_id = str(hit["phrase_id"])
        phrase_counts[phrase_id] = phrase_counts.get(phrase_id, 0) + 1

    active_claim_count = classification_counts.get("active_claim_blocker", 0)
    needs_review_count = classification_counts.get("needs_review", 0)
    public_copy_clean = active_claim_count == 0 and needs_review_count == 0
    canonical_triage = _canonical_public_boundary_triage(hits)
    status = (
        "active_claim_blocked"
        if active_claim_count
        else "review_required"
        if needs_review_count
        else "clear_boundary_only"
    )
    return {
        "schema_version": "release_claim_language_gate_v0",
        "status": status,
        "receipt_fresh": True,
        "receipt_fresh_scope": "builder assertion for this rendered payload; --check is the live freshness authority",
        "public_copy_clean": public_copy_clean,
        "public_toggle": "red",
        "release_toggle": "red",
        "release_action": "none",
        "active_blocker_count": active_claim_count,
        "source_authority": "private_repo",
        "projection_authority": "manifest_driven_public_projection",
        "purpose": (
            "Deterministic claim-language scan for manifest claim-bearing surfaces. "
            "It inventories risky public-toggle phrases, classifies explicit negative "
            "or policy contexts, and keeps ambiguous affirmative wording in a no-go "
            "review queue without rewriting copy or authorizing release."
        ),
        "summary": {
            "claim_surface_file_count": len(claim_files),
            "risky_phrase_hit_count": len(hits),
            "active_claim_blocker_count": active_claim_count,
            "active_blocker_count": active_claim_count,
            "needs_review_count": needs_review_count,
            "boundary_or_negative_context_count": classification_counts.get(
                "boundary_or_negative_context", 0
            ),
            "public_copy_clean": public_copy_clean,
            "receipt_fresh": True,
            "does_not_authorize_release": True,
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "phrase_counts": dict(sorted(phrase_counts.items())),
        "canonical_public_boundary_triage": canonical_triage,
        "scan_policy": {
            "manifest": PUBLICATION_MANIFEST.as_posix(),
            "included_groups": sorted(CLAIM_SURFACE_GROUPS),
            "skipped_output_paths": sorted(SKIP_OUTPUT_PATHS),
            "fingerprint_excluded_scan_paths": sorted(FINGERPRINT_EXCLUDED_SCAN_PATHS),
            "risky_phrase_ids": [str(row["id"]) for row in RISKY_PHRASES],
            "negative_context_markers": NEGATIVE_CONTEXT_MARKERS,
            "meta_forbidden_context_markers": META_FORBIDDEN_CONTEXT_MARKERS,
            "does_not_modify_scanned_files": True,
        },
        "claim_surfaces": claim_files,
        "hits": hits,
        "claim_guard": {
            "allowed_current_wording": [
                "fixture-proven",
                "projection-green",
                "private-root evidence only",
                "controlled-review only",
                "not claimed yet",
                "public toggle remains red/no-go",
            ],
            "forbidden_current_wording": [
                "release ready",
                "ready to publish",
                "open source",
                "source available",
                "clean clone proven",
                "publicly reproducible",
                "publicly released",
                "production ready",
                "does not authorize release",
                "release authority",
                "publication authority",
                "release gate owner",
                "public toggle remains red/no-go",
            ],
        },
        "rerun_after_copy_or_manifest_change": [
            "./repo-python tools/meta/dissemination/release_claim_language_gate.py --check",
            "./repo-python tools/meta/dissemination/public_toggle_readiness_gate.py --portability-report <latest_green_report> --check",
        ],
        "source_fingerprints": {
            PUBLICATION_MANIFEST.as_posix(): _sha256(manifest_path),
            **{
                row["path"]: _sha256(repo_root / row["path"])
                for row in claim_files
                if row["path"] not in FINGERPRINT_EXCLUDED_SCAN_PATHS
                and (repo_root / row["path"]).exists()
            },
        },
    }


def write_gate(output_path: Path, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    payload = build_gate(repo_root)
    output = _repo_path(output_path, repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_canonical_json(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--assert-clear", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    output = _repo_path(args.output, repo_root)
    payload = build_gate(repo_root)
    rendered = _canonical_json(payload)
    if args.check:
        if not output.exists():
            print(
                json.dumps(
                    {
                        "ok": False,
                        "checked": True,
                        "receipt_fresh": False,
                        "public_copy_clean": payload["public_copy_clean"],
                        "missing": _rel(output, repo_root),
                    },
                    sort_keys=True,
                )
            )
            return 1
        current = output.read_text(encoding="utf-8")
        if current != rendered:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "checked": True,
                        "receipt_fresh": False,
                        "public_copy_clean": payload["public_copy_clean"],
                        "mismatch": _rel(output, repo_root),
                    },
                    sort_keys=True,
                )
            )
            return 1

    if not args.check:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    result = {
        "ok": True,
        "checked": bool(args.check),
        "receipt_fresh": True,
        "public_copy_clean": payload["public_copy_clean"],
        "path": _rel(output, repo_root),
        "status": payload["status"],
        "public_toggle": payload["public_toggle"],
        "release_toggle": payload["release_toggle"],
        "risky_phrase_hit_count": payload["summary"]["risky_phrase_hit_count"],
        "active_claim_blocker_count": payload["summary"]["active_claim_blocker_count"],
        "active_blocker_count": payload["summary"]["active_blocker_count"],
        "needs_review_count": payload["summary"]["needs_review_count"],
        "canonical_public_boundary_occurrence_count": payload[
            "canonical_public_boundary_triage"
        ]["canonical_occurrence_count"],
    }
    if args.assert_clear and not payload["public_copy_clean"]:
        result["ok"] = False
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
