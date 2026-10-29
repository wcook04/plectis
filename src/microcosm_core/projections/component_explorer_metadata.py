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


def _read_public(root: Path, ref: str, *, limit: int = MAX_SOURCE_BYTES) -> bytes:
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
        source = stream.read(limit + 1)
    if len(source) > limit:
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


DOCTRINE_SCHEMA = "plectis_explorer_doctrine_v2"
DOCTRINE_SOURCES = ("AXIOMS.md", "PRINCIPLES.md", "ANTI_PRINCIPLES.md", "core/axiom_organ_routing.json",
                    "core/doctrine_enrichment.json")
MAX_READER_BYTES = 1200
MAX_STATEMENT_BYTES = 4000
_SUPPORT_CACHE: dict[str, dict[str, Any]] = {}


def _sections(text: str, pattern: str) -> dict[str, str]:
    """Return each matching level-two section body, ending at the next level-two heading."""
    headings = list(re.finditer(r"^## .*$", text, re.MULTILINE))
    result = {}
    for i, heading in enumerate(headings):
        match = re.fullmatch(pattern, heading[0])
        if match:
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            result[match[1]] = text[heading.end():end].strip()
    return result


def _anti_principle_statements(text: str) -> dict[str, str]:
    """Quote each failure-mode row under the table's own header and separator lines."""
    lines = text.splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith("| ID |"))
    if not lines[header + 1].startswith("| ---"):
        raise ValueError("anti-principle table has no separator")
    return {line.split("|")[1].strip().split(" ", 1)[0]: "\n".join([lines[header], lines[header + 1], line])
            for line in lines if line.startswith("| AP-")}


def _statement(value: str) -> dict[str, str]:
    from microcosm_core.component_index import _safe
    from microcosm_core.component_explorer_validation import _text
    if len(value.encode("utf-8")) > MAX_STATEMENT_BYTES:
        raise ValueError("doctrine statement exceeds byte limit")
    _text(value, MAX_STATEMENT_BYTES)
    _safe(value)
    return {"statement": value, "statement_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest()}


def _reader_text(value: Any) -> str:
    from microcosm_core.component_index import _safe
    from microcosm_core.component_explorer_validation import _text
    if type(value) is not str or not value.strip():
        raise ValueError("doctrine reader text is missing")
    value = " ".join(value.split())
    if len(value.encode("utf-8")) > MAX_READER_BYTES:
        raise ValueError("doctrine reader text exceeds byte limit")
    _text(value, MAX_READER_BYTES)
    _safe(value)
    return value


def _reader(record: dict[str, Any], component_ids: set[str]) -> dict[str, Any]:
    """Authored reader content; never support evidence or a test result."""
    ladder, analogy = record["reader_ladder"], record["reader_ladder"]["analogy"]
    maps = analogy["maps"]
    if type(maps) is not list or len(maps) > 16:
        raise ValueError("invalid doctrine reader analogy map")
    return {"basis": "authored_reader_enrichment", "source_ref": "core/doctrine_enrichment.json",
            "plain": _reader_text(ladder["plain"]),
            "analogy": {"text": _reader_text(analogy["text"]),
                        "maps": [{"doctrine": _reader_text(row["doctrine"]), "analogy": _reader_text(row["analogy"])}
                                 for row in maps],
                        "boundary": _reader_text(analogy["boundary"])},
            "why_it_matters": _reader_text(ladder["why_it_matters"]),
            "potential_misread": _reader_text(ladder["potential_misread"]),
            "governs": _reader_text(record["governs"]), "requires": _reader_text(record["requires"]),
            "refuses": _reader_text(record["refuses"]),
            "example": {"text": _reader_text(record["example"]["text"]),
                        "component_ids": _witness_ids(record["example"]["refs"], component_ids)},
            "counterexample": _reader_text(record["counterexample"]["text"]),
            "enforced_in_component_ids": _witness_ids(record["enforced_in"], component_ids),
            "does_not_prove": _reader_text(record["does_not_prove"])}


def _axiom_support(root: Path) -> dict[str, Any]:
    """Run the existing support checker once per build root; its errors fail the build."""
    key = str(root.resolve())
    if key not in _SUPPORT_CACHE:
        from microcosm_core.validators.axiom_support_cover import evaluate_axiom_support_cover
        result = evaluate_axiom_support_cover(root)
        if type(result) is not dict or type(result.get("support_frontiers")) is not dict \
                or type(result.get("checker_id")) is not str:
            raise ValueError("axiom support checker returned no support frontiers")
        _SUPPORT_CACHE[key] = result
    return _SUPPORT_CACHE[key]


def _strings(value: Any, limit: int = 500, count: int = 32) -> list[str]:
    if value is None:
        return []
    if type(value) is not list or len(value) > count or any(type(item) is not str for item in value):
        raise ValueError("invalid doctrine string list")
    return [_bounded(item, limit) for item in value]


def _witness_ids(value: Any, component_ids: set[str]) -> list[str]:
    ids = _strings(value, 200)
    unknown = sorted(set(ids) - component_ids)
    if unknown:
        raise ValueError("unknown witness component id: " + ", ".join(unknown))
    return ids


def _axiom_detail(row: dict[str, Any], frontier: dict[str, Any], checker_id: str,
                  component_ids: set[str]) -> dict[str, Any]:
    axiom_id = row["axiom_id"]
    computed = {item["obligation_id"]: item for item in frontier["obligations"]}
    declared = [item["obligation_id"] for item in row["obligations"]]
    if len(declared) != len(set(declared)) or set(declared) != set(computed):
        raise ValueError("support checker obligations do not match routing: " + axiom_id)
    obligations = []
    for item in row["obligations"]:
        result = computed[item["obligation_id"]]
        binding = item.get("binding", {})
        if result["declared_status"] != item["coverage_status"] or type(item["required"]) is not bool:
            raise ValueError("support checker declared status mismatch: " + item["obligation_id"])
        obligations.append({
            "obligation_id": item["obligation_id"], "predicate": _bounded(item["predicate"], 1000),
            "required": item["required"], "declared_status": _bounded(item["coverage_status"], 200),
            "computed_status": _bounded(result["computed"], 200),
            "witness_component_ids": _witness_ids(binding.get("witness_organs"), component_ids),
            "witness_surfaces": _strings(binding.get("witness_surfaces")),
            "negative_case_codes": _strings(binding.get("negative_case_codes"), 200),
            "witness_gaps": [_bounded(gap["gap_id"], 200) for gap in result["witness_gaps"][:16]]})
    verdict = frontier["verdict"]
    if type(verdict) is not str or type(frontier["hand_stamped_strong_not_certifiable"]) is not bool:
        raise ValueError("support checker verdict is malformed: " + axiom_id)
    return {"formal_clause": _bounded(row["formal_clause"], 1000), "lineage": _strings(row["lineage"], 200),
            "anti_axiom": _bounded(row["anti_axiom"], 200),
            "routing": {"basis": "authored_routing_registry",
                        "source_ref": f"core/axiom_organ_routing.json::rows[{axiom_id}]",
                        "witness_strength": _bounded(row["witness_strength"], 100),
                        "witness_component_ids": _witness_ids(row["witness_organs"], component_ids),
                        "witness_surfaces": _strings(row["witness_surfaces"]),
                        "negative_case_codes": _strings(row["negative_case_codes"], 200)},
            "obligations": obligations,
            "support": {"basis": "index_time_computed", "checker_id": _bounded(checker_id, 200),
                        "verdict": _bounded(verdict, 200),
                        "hand_stamped_witness_strength": _bounded(frontier["hand_stamped_witness_strength"], 100),
                        "hand_stamped_strong_not_certifiable": frontier["hand_stamped_strong_not_certifiable"],
                        "strong_blocked_reasons": _strings(frontier["strong_blocked_reasons"][:16], 500)}}


def _doctrine(root: Path, component_ids: set[str], support: dict[str, Any] | None = None) -> dict[str, Any]:
    nodes, edges = [], []
    raw = {ref: _read_public(root, ref) for ref in DOCTRINE_SOURCES}
    sources = [{"ref": ref, "sha256": hashlib.sha256(raw[ref]).hexdigest()} for ref in DOCTRINE_SOURCES]
    text = raw["AXIOMS.md"].decode("utf-8")
    axiom_text = _sections(text, r"## (AX-\d+) .+")
    principle_text = _sections(raw["PRINCIPLES.md"].decode("utf-8"), r"## (P-\d+) .+")
    anti_text = _anti_principle_statements(raw["ANTI_PRINCIPLES.md"].decode("utf-8"))
    routing = {row["axiom_id"]: row for row in json.loads(raw["core/axiom_organ_routing.json"])["rows"]}
    records = json.loads(raw["core/doctrine_enrichment.json"])["records"]
    enrichment = {row["id"]: row for row in records}
    if len(enrichment) != len(records):
        raise ValueError("duplicate doctrine reader record")
    support = support if support is not None else _axiom_support(root)
    frontiers = support["support_frontiers"]
    matches = list(re.finditer(r"^## (AX-\d+) (.+)$", text, re.MULTILINE))
    axiom_ids = [match[1] for match in matches]
    if set(axiom_ids) != set(routing) or set(axiom_ids) != set(frontiers) or len(axiom_ids) != len(set(axiom_ids)):
        raise ValueError("axiom sources, routing rows and support frontiers disagree")
    for i, match in enumerate(matches):
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        plain = body.strip().split("\n\n", 1)[0]
        nodes.append({"id": match[1], "title": match[2].strip(), "plain": _bounded(plain),
                      "kind": "axiom", "source_ref": f"AXIOMS.md::{match[1]}",
                      **_statement(axiom_text[match[1]]),
                      "reader": _reader(_record(enrichment, match[1], "axiom"), component_ids),
                      "axiom": _axiom_detail(routing[match[1]], frontiers[match[1]],
                                             support["checker_id"], component_ids)})
    for kind, rows, statements in (("principle", _principle_source_rows(root), principle_text),
                                   ("anti_principle", _anti_principle_source_rows(root), anti_text)):
        for row in rows:
            nodes.append({"id": row["id"], "title": row["title"], "kind": kind,
                          "plain": _bounded(row.get("body_markdown", row.get("failure_statement", ""))),
                          "source_ref": row["source_ref"], **_statement(statements[row["id"]]),
                          "reader": _reader(_record(enrichment, row["id"], kind), component_ids)})
            for target in row["axiom_refs"]:
                edges.append({"from_id": row["id"], "to_id": target,
                              "kind": "rests_on" if kind == "principle" else "violates",
                              "source_ref": row["source_ref"]})
    if set(enrichment) != {row["id"] for row in nodes}:
        raise ValueError("doctrine reader records do not match the rules")
    return {"schema_version": DOCTRINE_SCHEMA, "sources": sources, "nodes": nodes, "edges": edges}


def _record(enrichment: dict[str, Any], identity: str, kind: str) -> dict[str, Any]:
    record = enrichment.get(identity)
    if record is None or record.get("kind") != kind:
        raise ValueError("doctrine rule has no reader record: " + identity)
    return record


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
    return {"component_filters": filters, "doctrine": _doctrine(root, organ_ids),
            "source_revision": _source_revision(root),
            "typed_relations": _typed_relations(root, organs),
            "receipt_summaries": [_receipt_summary(root, ref) for ref in refs]}


def collect_reader_guides(root: Path, component_refs: set[str], bindings: dict[str, str]) -> dict:
    """Retain complete, bounded Markdown only when it matches the indexed source."""
    from microcosm_core.component_api_contract import MAX_GUIDE_BYTES, MAX_GUIDES_BYTES
    from microcosm_core.component_explorer_validation import plain_lead, _text
    result = {}
    for ref, digest in sorted(bindings.items()):
        data = _read_public(Path(root), ref, limit=MAX_GUIDE_BYTES)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('guide source changed during collection: ' + ref)
        text = data.decode('utf-8')
        _text(text, MAX_GUIDE_BYTES)
        plain = plain_lead(text)
        if ref in component_refs and plain is None:
            raise ValueError('component guide missing plain lead: ' + ref)
        result[ref] = {'ref': ref, 'sha256': digest, 'text': text, 'availability': 'available',
                       'plain': plain, 'plain_availability': 'available' if plain else 'unrecorded'}
    if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_GUIDES_BYTES:
        raise ValueError('guide manifest byte limit')
    return result
