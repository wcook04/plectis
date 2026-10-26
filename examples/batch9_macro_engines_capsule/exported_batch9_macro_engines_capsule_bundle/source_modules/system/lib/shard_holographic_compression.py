"""
[PURPOSE]
- Teleology: Provide TLDR, density, and full compression layers for raw-seed shard browsing.
- Mechanism: Derive local text layers and optional paper-context evidence into a generated per-shard sidecar.

[INTERFACE]
- Exports default_sidecar_path, build_shard_holographic_compression, load_shard_holographic_compression, and selection helpers.

[FLOW]
- Reads: Shard envelope and paper-module coverage JSON.
- Mechanism: Build each shard layer, aggregate length/coverage statistics, then optionally write sidecar; selectors read existing rows by shard ID.

[DEPENDENCIES]
- Reads: Caller-selected shard/coverage files and default generated compression sidecar; no model calls.

[CONSTRAINTS]
- Writes: build_shard_holographic_compression writes output JSON by default (write=True).
- Warns: Missing sidecar yields missing_sidecar with rebuild command and zero covered items.
- Non-goal: Editing raw seed or promoting compression text to source authority.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DEFAULT_SOURCE_PATH = (
    Path("obsidian/okay lets do this")
    / "09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine"
    / "extracted_shards.json"
)
DEFAULT_COVERAGE_PATH = Path("codex/hologram/raw_seed_projection/shard_paper_module_coverage.json")
DEFAULT_SIDECAR_PATH = Path("codex/hologram/raw_seed_projection/shard_holographic_compression.json")
SCHEMA_VERSION = "shard_holographic_compression_v1"
LOCAL_METHOD = "local_template_v1"


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_string(item) for item in value if _string(item)]
    token = _string(value)
    return [token] if token else []


def _clip(text: Any, *, limit: int) -> str:
    token = re.sub(r"\s+", " ", _string(text)).strip()
    if len(token) <= limit:
        return token
    return token[: max(0, limit - 1)].rstrip() + "..."


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def default_sidecar_path(repo_root: Path | str) -> Path:
    return Path(repo_root) / DEFAULT_SIDECAR_PATH


def _source_path(repo_root: Path | str, source_path: Path | str | None = None) -> Path:
    path = Path(source_path) if source_path is not None else DEFAULT_SOURCE_PATH
    return path if path.is_absolute() else Path(repo_root) / path


def _coverage_path(repo_root: Path | str, coverage_path: Path | str | None = None) -> Path:
    path = Path(coverage_path) if coverage_path is not None else DEFAULT_COVERAGE_PATH
    return path if path.is_absolute() else Path(repo_root) / path


def _statement(shard: Mapping[str, Any]) -> str:
    return (
        _string(shard.get("clarified_statement"))
        or _string(shard.get("statement"))
        or _string(shard.get("summary"))
        or _string(shard.get("voice_anchor"))
    )


def _shard_id(shard: Mapping[str, Any]) -> str:
    return _string(shard.get("id") or shard.get("shard_id"))


def _coverage_for_shard(coverage: Mapping[str, Any], shard_id: str) -> dict[str, Any]:
    rows = coverage.get("shards")
    if not isinstance(rows, Mapping):
        return {}
    value = rows.get(shard_id)
    return value if isinstance(value, dict) else {}


def _module_context(coverage_row: Mapping[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for module in coverage_row.get("top_modules") or []:
        if not isinstance(module, Mapping):
            continue
        slug = _string(module.get("slug"))
        if not slug:
            continue
        modules.append(
            {
                "slug": slug,
                "title": _string(module.get("title")),
                "rank": int(module.get("rank") or len(modules) + 1),
                "score": round(float(module.get("score") or 0.0), 6),
                "confidence": _string(module.get("confidence")),
            }
        )
        if len(modules) >= limit:
            break
    return modules


def _module_phrase(modules: list[Mapping[str, Any]]) -> str:
    slugs = [_string(module.get("slug")) for module in modules if _string(module.get("slug"))]
    if not slugs:
        return "no named paper-module context"
    return ", ".join(slugs[:3])


def _build_layers(shard: Mapping[str, Any], modules: list[Mapping[str, Any]]) -> dict[str, str]:
    statement = _statement(shard)
    voice_anchor = _string(shard.get("voice_anchor"))
    support_excerpt = _string(shard.get("support_excerpt"))
    parent = _string(shard.get("parent_paragraph_id"))
    groups = _string_list(shard.get("idea_group_ids"))
    gestures = _string_list(shard.get("gestures_towards"))
    routing_state = _string(shard.get("routing_state")) or "unknown"
    coverage_state = _string(shard.get("coverage_state")) or "unknown"
    review_plane = _string(shard.get("primary_review_plane")) or "unclassified"
    synthesis_role = _string(shard.get("synthesis_role")) or "unclassified"
    module_phrase = _module_phrase(list(modules))

    tldr = _clip(statement, limit=220)
    density_parts = [
        f"Shard reads as {review_plane}/{synthesis_role} in {module_phrase}.",
        _clip(statement, limit=260),
    ]
    if voice_anchor:
        density_parts.append(f"Voice anchor: {_clip(voice_anchor, limit=180)}")
    density_parts.append(f"State: routing={routing_state}, coverage={coverage_state}.")

    full_parts = [
        f"Statement: {_clip(statement, limit=420)}",
        f"Paper-module context: {module_phrase}.",
        f"Review role: primary_review_plane={review_plane}, synthesis_role={synthesis_role}.",
        f"Authority: parent_paragraph_id={parent or 'unknown'}, idea_group_ids={groups[:4]}.",
        f"State: routing_state={routing_state}, coverage_state={coverage_state}.",
    ]
    if voice_anchor:
        full_parts.append(f"Voice anchor: {_clip(voice_anchor, limit=260)}")
    if support_excerpt:
        full_parts.append(f"Support excerpt: {_clip(support_excerpt, limit=320)}")
    if gestures:
        full_parts.append(f"Gestures towards: {gestures[:4]}.")

    return {
        "tldr": tldr,
        "density": " ".join(part for part in density_parts if part),
        "full": " ".join(part for part in full_parts if part),
    }


def _build_one(shard: Mapping[str, Any], coverage_row: Mapping[str, Any]) -> dict[str, Any]:
    shard_id = _shard_id(shard)
    modules = _module_context(coverage_row)
    layers = _build_layers(shard, modules)
    return {
        "shard_id": shard_id,
        "schema_version": SCHEMA_VERSION,
        "method": LOCAL_METHOD,
        "layers": layers,
        "paper_module_context": modules,
        "source": {
            "parent_paragraph_id": _string(shard.get("parent_paragraph_id")),
            "raw_seed_anchor": _string(shard.get("raw_seed_anchor")),
            "idea_group_ids": _string_list(shard.get("idea_group_ids"))[:6],
            "routing_state": _string(shard.get("routing_state")),
            "coverage_state": _string(shard.get("coverage_state")),
            "primary_review_plane": _string(shard.get("primary_review_plane")),
            "synthesis_role": _string(shard.get("synthesis_role")),
        },
        "lengths": {name: len(text) for name, text in layers.items()},
        "guardrail": "Generated compression aid only; read against par_* evidence and paper_module_context before routing.",
    }


def build_shard_holographic_compression(
    *,
    repo_root: Path | str,
    source_path: Path | str | None = None,
    coverage_path: Path | str | None = None,
    output_path: Path | str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root)
    source_abs = _source_path(root, source_path)
    coverage_abs = _coverage_path(root, coverage_path)
    output_abs = Path(output_path) if output_path is not None else default_sidecar_path(root)
    if not output_abs.is_absolute():
        output_abs = root / output_abs

    envelope = _load_json(source_abs)
    shard_rows = [row for row in envelope.get("shards") or [] if isinstance(row, Mapping)]
    coverage = _load_json(coverage_abs)
    compressed: dict[str, Any] = {}
    module_covered = 0
    length_totals = {"tldr": 0, "density": 0, "full": 0}

    for shard in shard_rows:
        shard_id = _shard_id(shard)
        if not shard_id:
            continue
        coverage_row = _coverage_for_shard(coverage, shard_id)
        row = _build_one(shard, coverage_row)
        if row["paper_module_context"]:
            module_covered += 1
        for name, size in row["lengths"].items():
            length_totals[name] += int(size)
        compressed[shard_id] = row

    count = len(compressed)
    summary = {
        "shard_count": len(shard_rows),
        "compressed_shard_count": count,
        "paper_context_shard_count": module_covered,
        "layer_names": ["tldr", "density", "full"],
        "avg_lengths": {
            name: round(total / count, 2) if count else 0.0 for name, total in length_totals.items()
        },
        "method": LOCAL_METHOD,
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "shards_path": str(source_abs.relative_to(root)) if source_abs.is_relative_to(root) else str(source_abs),
            "paper_module_coverage_path": str(coverage_abs.relative_to(root))
            if coverage_abs.is_relative_to(root)
            else str(coverage_abs),
        },
        "summary": summary,
        "shards": compressed,
    }
    if write:
        _write_json(output_abs, payload)
    return payload


def load_shard_holographic_compression(
    *,
    repo_root: Path | str,
    sidecar_path: Path | str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    path = Path(sidecar_path) if sidecar_path is not None else default_sidecar_path(root)
    if not path.is_absolute():
        path = root / path
    return _load_json(path)


def holographic_compressions_for_shards(
    shards: list[Mapping[str, Any]],
    *,
    repo_root: Path | str,
    sidecar_path: Path | str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    path = Path(sidecar_path) if sidecar_path is not None else default_sidecar_path(root)
    if not path.is_absolute():
        path = root / path
    payload = _load_json(path)
    rows = payload.get("shards")
    if not isinstance(rows, Mapping):
        return {
            "schema_version": "shard_holographic_compression_selection_v1",
            "status": "missing_sidecar",
            "sidecar_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "selected_shard_count": len(shards),
            "covered_shard_count": 0,
            "items": [],
            "rebuild_command": "./repo-python tools/meta/factory/build_shard_holographic_compression.py",
        }

    items: list[dict[str, Any]] = []
    for shard in shards:
        shard_id = _shard_id(shard)
        if not shard_id:
            continue
        row = rows.get(shard_id)
        if not isinstance(row, Mapping):
            continue
        items.append(
            {
                "shard_id": shard_id,
                "method": _string(row.get("method")),
                "layers": dict(row.get("layers") or {}),
                "paper_module_context": list(row.get("paper_module_context") or [])[:3],
            }
        )
    return {
        "schema_version": "shard_holographic_compression_selection_v1",
        "status": "available",
        "sidecar_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        "source_generated_at": _string(payload.get("generated_at")),
        "method": _string((payload.get("summary") or {}).get("method")),
        "selected_shard_count": len(shards),
        "covered_shard_count": len(items),
        "layer_names": list((payload.get("summary") or {}).get("layer_names") or ["tldr", "density", "full"]),
        "items": items,
        "guardrail": "Read TLDR/density/full against paper_module_context before using the compression as routing evidence.",
    }


__all__ = [
    "SCHEMA_VERSION",
    "build_shard_holographic_compression",
    "default_sidecar_path",
    "holographic_compressions_for_shards",
    "load_shard_holographic_compression",
]
