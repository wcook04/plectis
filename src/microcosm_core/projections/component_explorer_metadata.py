"""Bounded, build-time reader metadata from public component owners.

No request-time I/O, execution, review inference or filesystem timestamp inference.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from microcosm_core.doctrine_lattice import _principle_source_rows, _anti_principle_source_rows


MAX_SOURCE_BYTES = 2_000_000


def _read_public(root: Path, ref: str) -> bytes:
    """Read a bounded regular public file, rejecting traversal and symlink ancestry."""
    relative = Path(ref)
    if not ref or relative.is_absolute() or any(part in {".", ".."} for part in ref.split("/")):
        raise ValueError("invalid public source reference")
    base = root.resolve(strict=True)
    path = base
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink public source reference")
    if not path.resolve(strict=True).is_relative_to(base) or not path.is_file():
        raise ValueError("nonregular public source reference")
    with path.open("rb") as stream:
        source = stream.read(MAX_SOURCE_BYTES + 1)
    if len(source) > MAX_SOURCE_BYTES:
        raise ValueError("public source exceeds byte limit")
    return source


def _load(root: Path, ref: str) -> Any:
    return json.loads(_read_public(root, ref))


def _bounded(value: Any, limit: int = 500) -> str:
    return " ".join(str(value).split())[:limit]


def _source_revision(root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True, timeout=10).stdout.strip()
    result = {"status": "unknown", "commit": None, "dirty": None,
              "repository": None, "exact_source_links": False}
    try:
        # Refuse an enclosing repository's identity for an exported directory.
        if Path(git("rev-parse", "--show-toplevel")).resolve() != root.resolve():
            return result
        result.update(status="recorded", commit=git("rev-parse", "HEAD"),
                      dirty=bool(git("status", "--porcelain", "--untracked-files=normal")))
        # Remotes may contain credentials/local paths; only publish canonical HTTPS URLs.
        remote = git("remote", "get-url", "origin")
        if re.fullmatch(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", remote):
            remote = "https://github.com/" + remote.split(":", 1)[1]
        if re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", remote):
            result["repository"] = remote.removesuffix(".git")
        result["exact_source_links"] = result["dirty"] is False and result["repository"] is not None
    except (subprocess.SubprocessError, OSError):
        pass
    return result


def _doctrine(root: Path) -> dict[str, Any]:
    nodes, edges = [], []
    text = _read_public(root, "AXIOMS.md").decode("utf-8")
    # Existing doctrine parsers own the syntax; admit their source files first.
    for ref in ("PRINCIPLES.md", "ANTI_PRINCIPLES.md"):
        _read_public(root, ref)
    matches = list(re.finditer(r"^## (AX-\d+) (.+)$", text, re.MULTILINE))
    for i, match in enumerate(matches):
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        plain = body.strip().split("\n\n", 1)[0]
        nodes.append({"id": match[1], "title": match[2].strip(), "plain": _bounded(plain),
                      "kind": "axiom", "source_ref": f"AXIOMS.md::{match[1]}"})
    for kind, rows in (("principle", _principle_source_rows(root)),
                       ("anti_principle", _anti_principle_source_rows(root))):
        for row in rows:
            nodes.append({"id": row["id"], "title": row["title"], "kind": kind,
                          "plain": _bounded(row.get("body_markdown", row.get("failure_statement", ""))),
                          "source_ref": row["source_ref"]})
            for target in row["axiom_refs"]:
                edges.append({"from_id": row["id"], "to_id": target,
                              "kind": "rests_on" if kind == "principle" else "violates",
                              "source_ref": row["source_ref"]})
    return {"nodes": nodes, "edges": edges}


def _receipt_summary(root: Path, ref: str) -> dict[str, Any]:
    result = {"ref": ref, "availability": "unavailable", "created_at": None,
              "date_status": "unrecorded", "recorded_fields": {}}
    result["artifact_sha256"] = None
    result["availability_reason"] = "source_unavailable"
    try:
        source = _read_public(root, ref)
    except FileNotFoundError:
        return result
    except (ValueError, OSError):
        result["availability_reason"] = "source_rejected"
        return result
    result["availability"] = "available"
    result["availability_reason"] = None
    result["artifact_sha256"] = hashlib.sha256(source).hexdigest()
    try:
        body = json.loads(source)
    except (ValueError, UnicodeError):
        return result
    if not isinstance(body, dict):
        return result
    date = body.get("created_at")
    # Only source-declared ISO date/time values. Never manufacture dates from names/mtime.
    if isinstance(date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[0-9:.+Z-]+)?", date):
        try:
            datetime.fromisoformat(date.replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            result.update(created_at=date, date_status="recorded")
    for key in ("status", "result", "fixture_id", "case_count", "passed_count", "failed_count",
                "positive_case_count", "negative_case_count", "error_count", "warning_count"):
        value = body.get(key)
        if isinstance(value, (bool, int)) or isinstance(value, str) and len(value) <= 160:
            result["recorded_fields"][key] = value
    return result


def _typed_relations(root: Path, organs: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract lexical runner imports; this establishes no execution/call relation."""
    modules = {row["runner"]: row["organ_id"] for row in organs if row.get("runner")}
    edges, unavailable = [], []
    for module, component_id in sorted(modules.items()):
        ref = "src/" + module.replace(".", "/") + ".py"
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module):
            raise ValueError("invalid registered runner module")
        try:
            source = _read_public(root, ref)
        except (ValueError, OSError):
            unavailable.append(component_id)
            continue
        try:
            tree = ast.parse(source, filename=ref)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"invalid runner Python source: {component_id}") from exc
        digest = hashlib.sha256(source).hexdigest()
        found = set()
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = importlib.util.resolve_name("." * node.level + base, module.rpartition(".")[0])
                targets = [base, *(base + "." + alias.name for alias in node.names)]
            for target in targets:
                if target in modules and target != module and (target, node.lineno) not in found:
                    found.add((target, node.lineno))
                    edges.append({"from_id": component_id, "to_id": modules[target],
                                  "kind": "imports_runner", "source_ref": f"{ref}#L{node.lineno}",
                                  "line": node.lineno, "source_sha256": digest})
    return {"status": "observed" if not unavailable else "partially_observed", "edges": edges,
            "unavailable_component_ids": sorted(unavailable),
            "reason": "Lexical Python imports between registered runner modules only; no runtime call, execution or causality inferred."}


def collect_explorer_metadata(root: str | Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Collect public owner metadata once while building the validated snapshot."""
    root = Path(root)
    organs = _load(root, "core/organ_registry.json")["implemented_organs"]
    profiles = _load(root, "core/organ_evidence_classes.json")["class_profiles"]
    families = _load(root, "core/organ_families.json")["families"]
    classification_rows = (payload["nodes"]["organ"] if payload is not None else
                           _load(root, "core/organ_atlas.json")["organs"])
    organ_ids = {row["organ_id"] for row in organs}
    family_counts = Counter(row["family"] for row in classification_rows if row["organ_id"] in organ_ids)
    filters = {"family": [{"value": row["family_id"], "label": row["label"],
                            "description": row["blurb"], "component_count": family_counts[row["family_id"]],
                            "label_basis": "authored_owner"} for row in families]}
    for field in ("evidence_class", "truth_accounting_bucket", "real_substrate_disposition"):
        counts = Counter(row[field] for row in organs)
        filters[field] = []
        for value, count in sorted(counts.items()):
            member_classes = {row["evidence_class"] for row in organs if row[field] == value}
            descriptions = sorted({profiles[name]["claim_ceiling"] for name in member_classes})
            filters[field].append({"value": value, "label": value.replace("_", " ").capitalize(),
                                   "description": _bounded("; ".join(descriptions), 1200),
                                   "component_count": count, "label_basis": "identifier_words"})
    refs = sorted({ref for row in organs for ref in
                   [row.get("current_authority_receipt"), row.get("historical_source_authority_receipt"),
                    *row.get("generated_receipts", [])]
                   if isinstance(ref, str)})
    return {"component_filters": filters, "doctrine": _doctrine(root),
            "source_revision": _source_revision(root),
            "typed_relations": _typed_relations(root, organs),
            "receipt_summaries": [_receipt_summary(root, ref) for ref in refs]}
